"""Service-owned Google OAuth token refresh for the Gmail draft adapter."""

from __future__ import annotations

import json
import re
import ssl
import time
from http.client import HTTPException, HTTPSConnection
from threading import Lock
from typing import Callable
from urllib.parse import urlencode

GOOGLE_DRAFT_SCOPES = frozenset({
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.settings.basic",
})
_HOST = "oauth2.googleapis.com"
_PATH = "/token"
_TIMEOUT_SECONDS = 10.0
_MAX_RESPONSE_BYTES = 16 * 1024
_CREDENTIAL = re.compile(r"[\x21-\x7e]{1,2048}")
_BEARER = re.compile(r"[A-Za-z0-9._~+/-]{1,4096}={0,2}")


class GoogleOAuthError(RuntimeError):
    """A fixed status code without token endpoint data."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _unique_object(pairs: list[tuple]) -> dict:
    result = dict(pairs)
    if len(result) != len(pairs):
        raise ValueError("duplicate OAuth response field")
    return result


def _read_token_json(response, clock: Callable[[], float], deadline: float) -> dict:
    content_type = response.getheader("Content-Type", "").split(";", 1)[0].strip().lower()
    encoding = response.getheader("Content-Encoding", "identity").strip().lower()
    content_length = response.getheader("Content-Length")
    if content_type != "application/json" or encoding != "identity":
        raise GoogleOAuthError("GOOGLE_OAUTH_INVALID_RESPONSE")
    if content_length is not None and (
        not re.fullmatch(r"[0-9]{1,5}", content_length)
        or int(content_length) > _MAX_RESPONSE_BYTES
    ):
        raise GoogleOAuthError("GOOGLE_OAUTH_INVALID_RESPONSE")

    data = bytearray()
    while True:
        if clock() >= deadline:
            raise TimeoutError
        chunk = response.read1(_MAX_RESPONSE_BYTES - len(data) + 1)
        if not chunk:
            break
        data.extend(chunk)
        if len(data) > _MAX_RESPONSE_BYTES:
            raise GoogleOAuthError("GOOGLE_OAUTH_INVALID_RESPONSE")
    if content_length is not None and len(data) != int(content_length):
        raise GoogleOAuthError("GOOGLE_OAUTH_INVALID_RESPONSE")
    parsed = json.loads(data.decode("utf-8"), object_pairs_hook=_unique_object)
    if type(parsed) is not dict:
        raise GoogleOAuthError("GOOGLE_OAUTH_INVALID_RESPONSE")
    return parsed


class GoogleTokenProvider:
    """Refresh a separately consented grant with the draft service's exact scopes."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        refresh_token: str,
        *,
        connection_factory: Callable[..., HTTPSConnection] = HTTPSConnection,
        clock: Callable[[], float] = time.monotonic,
    ):
        if any(
            type(value) is not str or not _CREDENTIAL.fullmatch(value)
            for value in (client_id, client_secret, refresh_token)
        ):
            raise GoogleOAuthError("GOOGLE_OAUTH_INVALID_CONFIGURATION")
        self._form = urlencode({
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
            "scope": " ".join(sorted(GOOGLE_DRAFT_SCOPES)),
        }).encode("ascii")
        self._connection_factory = connection_factory
        self._clock = clock
        self._lock = Lock()
        self._token = ""
        self._cache_until = 0.0

    def _refresh(self, started: float) -> tuple[str, int]:
        connection = None
        try:
            # HTTPSConnection does not use environment proxies or follow redirects.
            connection = self._connection_factory(
                _HOST, port=443, timeout=_TIMEOUT_SECONDS,
                context=ssl.create_default_context(),
            )
            connection.request("POST", _PATH, body=self._form, headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
                "Accept-Encoding": "identity",
                "Connection": "close",
            })
            with connection.getresponse() as response:
                if response.status in (400, 401, 403):
                    raise GoogleOAuthError("GOOGLE_OAUTH_REJECTED")
                if response.status != 200:
                    raise GoogleOAuthError("GOOGLE_OAUTH_UNAVAILABLE")
                payload = _read_token_json(response, self._clock, started + _TIMEOUT_SECONDS)
        except (OSError, HTTPException):
            raise GoogleOAuthError("GOOGLE_OAUTH_UNAVAILABLE") from None
        except (ValueError, RecursionError):
            raise GoogleOAuthError("GOOGLE_OAUTH_INVALID_RESPONSE") from None
        finally:
            if connection is not None:
                try:
                    connection.close()
                except OSError:
                    pass

        token, token_type, expires = (
            payload.get("access_token"), payload.get("token_type"), payload.get("expires_in"),
        )
        if (
            type(token) is not str or not _BEARER.fullmatch(token)
            or type(token_type) is not str or token_type.lower() != "bearer"
            or type(expires) is not int or not 1 <= expires <= 86400
            or "error" in payload
        ):
            raise GoogleOAuthError("GOOGLE_OAUTH_INVALID_RESPONSE")
        if "scope" in payload:
            scopes = payload["scope"]
            if type(scopes) is not str or set(scopes.split()) != GOOGLE_DRAFT_SCOPES:
                raise GoogleOAuthError("GOOGLE_OAUTH_SCOPE_MISMATCH")
        return token, expires

    def __call__(self) -> str:
        with self._lock:
            started = self._clock()
            if self._token and started < self._cache_until:
                return self._token
            self._token = ""
            token, expires = self._refresh(started)
            cache_until = started + expires - min(60, expires * 0.1)
            if self._clock() >= cache_until:
                raise GoogleOAuthError("GOOGLE_OAUTH_INVALID_RESPONSE")
            self._token = token
            self._cache_until = cache_until
            return token
