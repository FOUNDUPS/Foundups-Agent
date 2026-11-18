"""Synthetic checks for the Gmail provider endpoint and response boundary."""

import base64
import io
import json
from collections import deque
from urllib.parse import parse_qs, urlsplit

import pytest

from modules.infrastructure.foundups_mcp_bridge.src import draft_gmail


ACCOUNT = "draft-owner@example.invalid"
ALIAS = "draft-alias@example.invalid"
ROOT = "/gmail/v1/users/me"
DRAFT = "r-104"
THREAD = "thread-1"
BEFORE = "message-1"
AFTER = "message-2"
RAW = b"From: draft-owner@example.invalid\r\n\r\nSynthetic MIME\r\n"
PROFILE = {"emailAddress": ACCOUNT}
EXPECTED = draft_gmail.GmailDraft(DRAFT, BEFORE, THREAD, RAW)


def raw_payload(*, raw=RAW, message_id=BEFORE, thread_id=THREAD):
    return {"id": DRAFT, "message": {"id": message_id, "threadId": thread_id,
                                     "raw": base64.urlsafe_b64encode(raw).decode().rstrip("=")}}


class Response(io.BytesIO):
    def __init__(self, status, content, headers):
        data = content if isinstance(content, bytes) else json.dumps(content).encode("utf-8")
        super().__init__(data)
        self.status = status
        self.headers = {
            "Content-Type": "application/json; charset=UTF-8",
            "Content-Length": str(len(data)),
            **headers,
        }

    def getheader(self, key, default=None):
        return self.headers.get(key, default)

    def read1(self, size):
        assert size <= 64 * 1024
        return self.read(size)


@pytest.fixture
def transport(monkeypatch):
    responses = deque()
    calls = []

    class Connection:
        def __init__(self, host, *, timeout, context):
            assert host == "gmail.googleapis.com"
            assert timeout == 10.0
            assert context.check_hostname

        def request(self, method, path, *, body, headers):
            parsed = urlsplit(path)
            assert not parsed.scheme and not parsed.netloc and not parsed.fragment
            assert headers["Cache-Control"] == "no-store"
            calls.append((method, parsed.path, parse_qs(parsed.query), body, headers))

        def getresponse(self):
            result = responses.popleft()
            if isinstance(result, Exception):
                raise result
            return Response(*result)

        def close(self):
            pass

    monkeypatch.setattr(draft_gmail, "HTTPSConnection", Connection)

    def add(content, *, status=200, headers=None):
        responses.append((status, content, headers or {}))

    return add, calls, responses


def adapter(token_provider=lambda: "synthetic-access"):
    return draft_gmail.GmailDraftAdapter(ACCOUNT, token_provider)


def test_fixed_provider_routes_and_underlying_message_id_change(transport):
    add, calls, _ = transport
    add(PROFILE)
    assert adapter().get_account() == ACCOUNT

    add(PROFILE)
    add({"sendAs": [
        {"sendAsEmail": ACCOUNT.upper(), "isPrimary": True},
        {"sendAsEmail": ALIAS, "verificationStatus": "accepted"},
        {"sendAsEmail": "pending@example.invalid", "verificationStatus": "pending"},
        {"sendAsEmail": "mismatch@example.invalid", "verificationStatus": "accepted",
         "replyToAddress": "different@example.invalid"},
    ]})
    assert adapter().list_send_as() == frozenset({ACCOUNT, ALIAS})

    add(PROFILE)
    add({"drafts": [{"id": DRAFT}], "nextPageToken": "opaque+/= & token"})
    add({"drafts": [{"id": "r-105"}]})
    assert adapter().list_draft_ids() == (DRAFT, "r-105")
    assert calls[-1][2]["pageToken"] == ["opaque+/= & token"]

    add(PROFILE)
    add(raw_payload())
    draft = adapter().get_draft(DRAFT)
    assert (draft.draft_id, draft.message_id, draft.thread_id, draft.raw) == (DRAFT, BEFORE, THREAD, RAW)
    assert "Synthetic MIME" not in repr(draft)
    assert calls[-1][2]["format"] == ["raw"]

    add(PROFILE)
    add(raw_payload())
    add({"id": DRAFT, "message": {"id": AFTER, "threadId": THREAD}})
    assert adapter().update_draft(DRAFT, RAW, THREAD, expected=draft) == AFTER
    assert [(method, path) for method, path, *_ in calls[-3:]] == [
        ("GET", f"{ROOT}/profile"),
        ("GET", f"{ROOT}/drafts/{DRAFT}"),
        ("PUT", f"{ROOT}/drafts/{DRAFT}"),
    ]
    assert len({call[4]["Authorization"] for call in calls[-3:]}) == 1
    assert json.loads(calls[-1][3]) == {
        "message": {"raw": base64.urlsafe_b64encode(RAW).decode(), "threadId": THREAD},
    }
    assert {(method, path) for method, path, *_ in calls} == {
        ("GET", f"{ROOT}/profile"),
        ("GET", f"{ROOT}/settings/sendAs"),
        ("GET", f"{ROOT}/drafts"),
        ("GET", f"{ROOT}/drafts/{DRAFT}"),
        ("PUT", f"{ROOT}/drafts/{DRAFT}"),
    }


@pytest.mark.parametrize("draft_id", ["send", "SEND", "r/other", "r%2Fother", "..", "r-1?x=2",
                                      "r-1\r\n", "r" * 129])
def test_other_provider_effects_cannot_be_selected(transport, draft_id):
    _, calls, _ = transport
    gmail = adapter()
    for method in (gmail.get_draft, lambda value: gmail.update_draft(value, RAW, THREAD, expected=EXPECTED)):
        with pytest.raises(draft_gmail.GmailError, match="^invalid_draft_id$"):
            method(draft_id)
    assert calls == []


def test_credential_is_refetched_and_matched_before_each_operation(transport):
    add, calls, _ = transport
    tokens = iter(("synthetic-first", "synthetic-wrong-account"))
    gmail = adapter(lambda: next(tokens))
    add(PROFILE)
    add({})
    assert gmail.list_draft_ids() == ()
    add({"emailAddress": "other-owner@example.invalid"})
    with pytest.raises(draft_gmail.GmailError, match="^wrong_account$"):
        gmail.update_draft(DRAFT, RAW, THREAD, expected=EXPECTED)
    assert [call[4]["Authorization"] for call in calls] == [
        "Bearer synthetic-first", "Bearer synthetic-first", "Bearer synthetic-wrong-account",
    ]
    assert all(method == "GET" for method, *_ in calls)


@pytest.mark.parametrize("status", [401, 403])
def test_expired_and_revoked_credential_errors_do_not_expose_provider_data(transport, status):
    add, calls, _ = transport
    add({"error": "sensitive synthetic response"}, status=status)
    with pytest.raises(draft_gmail.GmailError, match="^provider_auth$") as failure:
        adapter().get_draft(DRAFT)
    assert failure.value.code == "provider_auth"
    assert len(calls) == 1 and calls[0][1] == f"{ROOT}/profile"


def test_invalid_credential_never_leaves_host(transport):
    _, calls, _ = transport
    with pytest.raises(draft_gmail.GmailError, match="^provider_auth$"):
        adapter(lambda: "line one\r\nline two").get_account()
    assert calls == []


@pytest.mark.parametrize("result", [
    (307, {"message": "redirected"}, {"Location": "https://other.example.invalid"}),
    (500, {"message": "failed"}, {}),
    (200, b'{"id":"wrong-draft","message":{}}', {}),
    (200, b'{"id":"r-104","message":{"id":"message-2","threadId":"changed"}}', {}),
    TimeoutError("sensitive synthetic timeout"),
])
def test_uncertain_put_never_retries_or_follows_redirect(transport, result):
    add, calls, responses = transport
    add(PROFILE)
    add(raw_payload())
    responses.append(result)
    with pytest.raises(draft_gmail.GmailError, match="^mutation_uncertain$") as failure:
        adapter().update_draft(DRAFT, RAW, THREAD, expected=EXPECTED)
    assert failure.value.code == "mutation_uncertain"
    assert [(method, path) for method, path, *_ in calls] == [
        ("GET", f"{ROOT}/profile"),
        ("GET", f"{ROOT}/drafts/{DRAFT}"),
        ("PUT", f"{ROOT}/drafts/{DRAFT}"),
    ]


@pytest.mark.parametrize("changed", [
    {"raw": RAW + b"edit"},
    {"message_id": AFTER},
    {"thread_id": "new-thread"},
])
def test_last_provider_read_detects_concurrent_edit_without_put(transport, changed):
    add, calls, _ = transport
    add(PROFILE)
    add(raw_payload(**changed))
    with pytest.raises(draft_gmail.GmailError, match="^concurrent_edit$"):
        adapter().update_draft(DRAFT, RAW, THREAD, expected=EXPECTED)
    assert [(method, path) for method, path, *_ in calls] == [
        ("GET", f"{ROOT}/profile"),
        ("GET", f"{ROOT}/drafts/{DRAFT}"),
    ]


def test_missing_draft_is_distinct_from_provider_failure(transport):
    add, _, _ = transport
    add(PROFILE)
    add({}, status=404)
    with pytest.raises(draft_gmail.GmailError, match="^draft_missing$"):
        adapter().get_draft(DRAFT)


@pytest.mark.parametrize("raw_response", [
    {"message": {"raw": "eA==!", "id": BEFORE, "threadId": THREAD}, "id": DRAFT},
    {"message": {"raw": "eA=", "id": BEFORE, "threadId": THREAD}, "id": DRAFT},
    {"message": {"raw": "eA==", "id": BEFORE}, "id": DRAFT},
    b'{"id":"r-104","id":"r-104","message":{}}',
])
def test_malformed_provider_mime_responses_are_held(transport, raw_response):
    add, _, _ = transport
    add(PROFILE)
    add(raw_response)
    with pytest.raises(draft_gmail.GmailError, match="^provider_response$"):
        adapter().get_draft(DRAFT)


@pytest.mark.parametrize("headers", [
    {"Content-Length": "131073"},
    {"Content-Length": "5"},
    {"Content-Encoding": "gzip"},
    {"Content-Type": "text/html"},
])
def test_response_size_and_encoding_limits(transport, headers):
    add, _, _ = transport
    add(PROFILE, headers=headers)
    with pytest.raises(draft_gmail.GmailError, match="^provider_response$"):
        adapter().get_account()


def test_pagination_limit_and_duplicate_pages_fail_closed(transport, monkeypatch):
    add, _, _ = transport
    monkeypatch.setattr(draft_gmail, "_MAX_PAGES", 2)
    add(PROFILE)
    add({"drafts": [{"id": DRAFT}], "nextPageToken": "a"})
    add({"drafts": [{"id": "r-105"}], "nextPageToken": "b"})
    with pytest.raises(draft_gmail.GmailError, match="^draft_scan_limit$"):
        adapter().list_draft_ids()

    add(PROFILE)
    add({"drafts": [{"id": DRAFT}], "nextPageToken": "a"})
    add({"drafts": [{"id": DRAFT}]})
    with pytest.raises(draft_gmail.GmailError, match="^provider_response$"):
        adapter().list_draft_ids()
