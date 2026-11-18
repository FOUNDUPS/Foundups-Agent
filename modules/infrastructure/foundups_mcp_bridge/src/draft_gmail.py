"""Narrow Gmail REST access for the private draft sender service."""

from __future__ import annotations

import base64
import binascii
import json
import re
import ssl
import time
from dataclasses import dataclass
from enum import Enum
from http.client import HTTPException, HTTPSConnection
from typing import Callable
from urllib.parse import urlencode


_HOST = "gmail.googleapis.com"
_ROOT = "/gmail/v1/users/me"
_TIMEOUT_SECONDS = 10.0
_PAGE_SIZE = 50
_MAX_PAGES = 4
_MAX_METADATA_BYTES = 128 * 1024
_MAX_RAW_BYTES = 32 * 1024 * 1024
_MAX_RAW_RESPONSE_BYTES = 4 * ((_MAX_RAW_BYTES + 2) // 3) + _MAX_METADATA_BYTES
_ID = re.compile(r"[A-Za-z0-9_-]{1,128}\Z")
_ACCOUNT = re.compile(r"[A-Za-z0-9][A-Za-z0-9._%+-]{0,63}@[A-Za-z0-9.-]{1,189}\Z")
_BEARER = re.compile(r"[A-Za-z0-9._~+/-]{1,4096}={0,2}\Z")
_RAW = re.compile(r"[A-Za-z0-9_-]+={0,2}\Z")


class GmailError(RuntimeError):
    """A fixed provider status code. Never includes a response or credential."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


@dataclass(frozen=True, repr=False)
class GmailDraft:
    draft_id: str
    message_id: str
    thread_id: str
    raw: bytes


class _Operation(Enum):
    PROFILE = "profile"
    SEND_AS = "send_as"
    LIST = "list"
    GET = "get"
    UPDATE = "update"


def _id(value: object, *, draft: bool = False, code: str = "provider_response") -> str:
    if (
        type(value) is not str
        or not _ID.fullmatch(value)
        or (draft and value.casefold() == "send")
    ):
        raise GmailError(code)
    return value


def _account(value: object) -> str:
    if type(value) is not str or not _ACCOUNT.fullmatch(value):
        raise GmailError("provider_response")
    return value.lower()


def _unique_object(items: list[tuple]) -> dict:
    result = dict(items)
    if len(result) != len(items):
        raise ValueError("duplicate JSON field")
    return result


def _decode_mime(value: object) -> bytes:
    if (
        type(value) is not str
        or len(value) > 4 * ((_MAX_RAW_BYTES + 2) // 3)
        or not _RAW.fullmatch(value)
        or ("=" in value and len(value) % 4)
    ):
        raise GmailError("provider_response")
    try:
        raw = base64.b64decode(value + "=" * (-len(value) % 4), altchars=b"-_", validate=True)
    except (ValueError, binascii.Error):
        raise GmailError("provider_response") from None
    if not raw or len(raw) > _MAX_RAW_BYTES:
        raise GmailError("provider_response")
    return raw


def _message(data: dict, draft_id: str, *, code: str) -> dict:
    message = data.get("message")
    if data.get("id") != draft_id or type(message) is not dict:
        raise GmailError(code)
    return message


def _read_json(response, max_bytes: int, deadline: float) -> dict:
    content_type = response.getheader("Content-Type", "").split(";", 1)[0].strip().lower()
    content_encoding = response.getheader("Content-Encoding", "identity").strip().lower()
    content_length = response.getheader("Content-Length")
    if content_type != "application/json" or content_encoding != "identity":
        raise ValueError("invalid provider content type")
    if content_length is not None and (
        not re.fullmatch(r"[0-9]{1,10}", content_length) or int(content_length) > max_bytes
    ):
        raise ValueError("invalid provider content length")

    data = bytearray()
    while True:
        if time.monotonic() >= deadline:
            raise TimeoutError
        chunk = response.read1(min(64 * 1024, max_bytes - len(data) + 1))
        if not chunk:
            break
        data.extend(chunk)
        if len(data) > max_bytes:
            raise ValueError("provider response exceeded limit")
    if content_length is not None and len(data) != int(content_length):
        raise ValueError("incomplete provider response")
    parsed = json.loads(data.decode("utf-8"), object_pairs_hook=_unique_object)
    if type(parsed) is not dict:
        raise ValueError("invalid provider object")
    return parsed


def _request(
    operation: _Operation,
    token: str,
    *,
    draft_id: str | None = None,
    page_token: str = "",
    raw: bytes | None = None,
    thread_id: str | None = None,
) -> dict:
    # No tool argument may supply a host, URL, HTTP method, or provider operation.
    method, body, max_bytes = "GET", None, _MAX_METADATA_BYTES
    if operation is _Operation.PROFILE:
        path = "/profile?fields=emailAddress"
    elif operation is _Operation.SEND_AS:
        path = "/settings/sendAs?" + urlencode(
            {"fields": "sendAs(sendAsEmail,isPrimary,verificationStatus,replyToAddress)"}
        )
    elif operation is _Operation.LIST:
        query = {"maxResults": _PAGE_SIZE, "fields": "drafts(id),nextPageToken"}
        if page_token:
            query["pageToken"] = page_token
        path = "/drafts?" + urlencode(query)
    elif operation in {_Operation.GET, _Operation.UPDATE}:
        path = "/drafts/" + _id(draft_id, draft=True, code="invalid_draft_id")
        if operation is _Operation.GET:
            path += "?" + urlencode({"format": "raw", "fields": "id,message(id,threadId,raw)"})
            max_bytes = _MAX_RAW_RESPONSE_BYTES
        else:
            thread_id = _id(thread_id, code="invalid_thread_id")
            if type(raw) is not bytes or not raw or len(raw) > _MAX_RAW_BYTES:
                raise GmailError("invalid_mime_size")
            method = "PUT"
            path += "?" + urlencode({"fields": "id,message(id,threadId)"})
            body = json.dumps({"message": {
                "raw": base64.urlsafe_b64encode(raw).decode("ascii"),
                "threadId": thread_id,
            }}).encode("ascii")
    else:
        raise GmailError("provider_operation_denied")

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Accept-Encoding": "identity",
        "Cache-Control": "no-store",
    }
    if body is not None:
        headers["Content-Type"] = "application/json"
    deadline = time.monotonic() + _TIMEOUT_SECONDS
    connection = None
    try:
        # Direct TLS to one host. http.client performs no redirects or retries here.
        connection = HTTPSConnection(_HOST, timeout=_TIMEOUT_SECONDS, context=ssl.create_default_context())
        connection.request(method, _ROOT + path, body=body, headers=headers)
        with connection.getresponse() as response:
            if response.status in {401, 403}:
                raise GmailError("provider_auth")
            if response.status == 404 and operation in {_Operation.GET, _Operation.UPDATE}:
                raise GmailError("draft_missing")
            if response.status != 200:
                raise GmailError("mutation_uncertain" if method == "PUT" else "provider_unavailable")
            return _read_json(response, max_bytes, deadline)
    except (OSError, HTTPException):
        raise GmailError("mutation_uncertain" if method == "PUT" else "provider_unavailable") from None
    except (ValueError, RecursionError):
        raise GmailError("mutation_uncertain" if method == "PUT" else "provider_response") from None
    finally:
        if connection is not None:
            connection.close()


class GmailDraftAdapter:
    """Fixed-account access using a separately consented Google credential."""

    def __init__(self, account: str, token_provider: Callable[[], str]):
        self._account = _account(account)
        self._token_provider = token_provider

    def _authenticated_token(self) -> str:
        try:
            token = self._token_provider()
        except Exception:
            raise GmailError("provider_auth") from None
        if type(token) is not str or not _BEARER.fullmatch(token):
            raise GmailError("provider_auth")
        profile = _request(_Operation.PROFILE, token)
        if _account(profile.get("emailAddress")) != self._account:
            raise GmailError("wrong_account")
        return token

    def get_account(self) -> str:
        self._authenticated_token()
        return self._account

    def list_send_as(self) -> frozenset[str]:
        token = self._authenticated_token()
        aliases = _request(_Operation.SEND_AS, token).get("sendAs")
        if type(aliases) is not list or not aliases:
            raise GmailError("provider_response")
        allowed: set[str] = set()
        seen: set[str] = set()
        primary = []
        for alias in aliases:
            if type(alias) is not dict:
                raise GmailError("provider_response")
            address = _account(alias.get("sendAsEmail"))
            if address in seen:
                raise GmailError("provider_response")
            seen.add(address)
            is_primary = alias.get("isPrimary", False)
            if type(is_primary) is not bool:
                raise GmailError("provider_response")
            if is_primary:
                primary.append(address)
            if is_primary or alias.get("verificationStatus") == "accepted":
                reply_to = alias.get("replyToAddress", "")
                if reply_to and _account(reply_to) != address:
                    continue
                allowed.add(address)
        if primary != [self._account]:
            raise GmailError("wrong_account")
        return frozenset(allowed)

    def list_draft_ids(self) -> tuple[str, ...]:
        token = self._authenticated_token()
        ids: dict[str, None] = {}
        page_tokens: set[str] = set()
        page_token = ""
        for _ in range(_MAX_PAGES):
            page = _request(_Operation.LIST, token, page_token=page_token)
            drafts = page.get("drafts", [])
            if type(drafts) is not list or len(drafts) > _PAGE_SIZE:
                raise GmailError("provider_response")
            for item in drafts:
                if type(item) is not dict:
                    raise GmailError("provider_response")
                draft_id = _id(item.get("id"), draft=True)
                if draft_id in ids:
                    raise GmailError("provider_response")
                ids[draft_id] = None
            page_token = page.get("nextPageToken", "")
            if (
                type(page_token) is not str or len(page_token) > 1024
                or (page_token and not (page_token.isascii() and page_token.isprintable()))
                or page_token in page_tokens
            ):
                raise GmailError("provider_response")
            if not page_token:
                return tuple(ids)
            page_tokens.add(page_token)
        raise GmailError("draft_scan_limit")

    @staticmethod
    def _get_draft(draft_id: str, token: str) -> GmailDraft:
        data = _request(_Operation.GET, token, draft_id=draft_id)
        message = _message(data, draft_id, code="provider_response")
        return GmailDraft(
            draft_id, _id(message.get("id")), _id(message.get("threadId")),
            _decode_mime(message.get("raw")),
        )

    def get_draft(self, draft_id: str) -> GmailDraft:
        draft_id = _id(draft_id, draft=True, code="invalid_draft_id")
        return self._get_draft(draft_id, self._authenticated_token())

    def update_draft(self, draft_id: str, raw: bytes, thread_id: str, *, expected: GmailDraft) -> str:
        draft_id = _id(draft_id, draft=True, code="invalid_draft_id")
        if type(expected) is not GmailDraft or (expected.draft_id, expected.thread_id) != (draft_id, thread_id):
            raise GmailError("concurrent_edit")
        token = self._authenticated_token()
        # Use the same authenticated token for the final GET and PUT. Gmail
        # does not document conditional PUT for this resource.
        if self._get_draft(draft_id, token) != expected:
            raise GmailError("concurrent_edit")
        data = _request(_Operation.UPDATE, token, draft_id=draft_id, raw=raw, thread_id=thread_id)
        message = _message(data, draft_id, code="mutation_uncertain")
        if message.get("threadId") != thread_id:
            raise GmailError("mutation_uncertain")
        return _id(message.get("id"), code="mutation_uncertain")
