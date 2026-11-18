from concurrent.futures import ThreadPoolExecutor
import io
import json
import ssl
from urllib.parse import parse_qs

import pytest

from modules.infrastructure.foundups_mcp_bridge.src.draft_google_oauth import (
    GOOGLE_DRAFT_SCOPES,
    GoogleOAuthError,
    GoogleTokenProvider,
)

_CLIENT_ID = "synthetic-client"
_CLIENT_SECRET = "synthetic-client-proof"
_REFRESH = "synthetic-offline-grant"
_ACCESS = "synthetic-access"


class _Response:
    def __init__(self, body: dict | bytes, *, status: int = 200, headers: dict | None = None):
        if isinstance(body, dict):
            body = json.dumps(body).encode("utf-8")
        self.status = status
        self.headers = {"Content-Type": "application/json; charset=utf-8", **(headers or {})}
        self.stream = io.BytesIO(body)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.stream.close()

    def getheader(self, name, default=None):
        return self.headers.get(name, default)

    def read1(self, limit):
        return self.stream.read1(limit)


def _valid(**overrides):
    return {
        "access_token": _ACCESS,
        "token_type": "Bearer",
        "expires_in": 3600,
        "scope": " ".join(sorted(GOOGLE_DRAFT_SCOPES)),
        **overrides,
    }


def _provider(*responses):
    calls, closed = [], []
    timestamp = [1.0]
    responses = iter(responses)

    class Connection:
        def __init__(self, host, *, port, timeout, context):
            assert (host, port, timeout) == ("oauth2.googleapis.com", 443, 10.0)
            assert context.verify_mode == ssl.CERT_REQUIRED
            assert context.check_hostname
            self.response = next(responses)

        def request(self, method, path, *, body, headers):
            calls.append((method, path, parse_qs(body.decode("ascii")), headers))

        def getresponse(self):
            if isinstance(self.response, Exception):
                raise self.response
            return self.response

        def close(self):
            closed.append(True)

    provider = GoogleTokenProvider(
        _CLIENT_ID, _CLIENT_SECRET, _REFRESH,
        connection_factory=Connection, clock=lambda: timestamp[0],
    )
    return provider, calls, closed, timestamp


def test_refresh_uses_fixed_tls_destination_exact_scopes_and_private_form():
    provider, calls, closed, _ = _provider(_Response(_valid()))

    assert provider() == _ACCESS
    assert provider() == _ACCESS
    assert len(calls) == len(closed) == 1
    method, path, form, headers = calls[0]
    assert (method, path) == ("POST", "/token")
    assert form == {
        "client_id": [_CLIENT_ID],
        "client_secret": [_CLIENT_SECRET],
        "refresh_token": [_REFRESH],
        "grant_type": ["refresh_token"],
        "scope": [" ".join(sorted(GOOGLE_DRAFT_SCOPES))],
    }
    assert headers["Content-Type"] == "application/x-www-form-urlencoded"
    assert headers["Accept-Encoding"] == "identity"
    assert all(value not in repr(provider) for value in (_CLIENT_SECRET, _REFRESH, _ACCESS))


def test_concurrent_calls_share_refresh_and_stop_using_expiring_token():
    next_access = "synthetic-access-next"
    provider, calls, _, timestamp = _provider(
        _Response(_valid(expires_in=10)),
        _Response(_valid(access_token=next_access)),
    )
    with ThreadPoolExecutor(max_workers=6) as workers:
        assert set(workers.map(lambda _: provider(), range(12))) == {_ACCESS}
        timestamp[0] = 10.0
        assert set(workers.map(lambda _: provider(), range(12))) == {next_access}
    assert len(calls) == 2


def test_scope_can_be_omitted_when_request_already_specifies_exact_scopes():
    response = _valid()
    response.pop("scope")
    provider, _, _, _ = _provider(_Response(response))
    assert provider() == _ACCESS


@pytest.mark.parametrize("scopes", (
    "https://www.googleapis.com/auth/gmail.compose",
    " ".join(sorted(GOOGLE_DRAFT_SCOPES | {"https://www.googleapis.com/auth/gmail.send"})),
    None,
))
def test_rejects_narrower_or_broader_returned_scope(scopes):
    provider, calls, _, _ = _provider(_Response(_valid(scope=scopes)))
    with pytest.raises(GoogleOAuthError, match="^GOOGLE_OAUTH_SCOPE_MISMATCH$"):
        provider()
    assert len(calls) == 1


@pytest.mark.parametrize(("response", "code"), (
    (_Response({"error": "invalid_grant", "error_description": _REFRESH}, status=400),
     "GOOGLE_OAUTH_REJECTED"),
    (_Response({}, status=302, headers={"Location": "https://redirect.example.test/token"}),
     "GOOGLE_OAUTH_UNAVAILABLE"),
    (_Response({}, status=503), "GOOGLE_OAUTH_UNAVAILABLE"),
    (OSError(_REFRESH), "GOOGLE_OAUTH_UNAVAILABLE"),
    (_Response(b"x" * (16 * 1024 + 1)), "GOOGLE_OAUTH_INVALID_RESPONSE"),
    (_Response(_valid(), headers={"Content-Length": "1"}), "GOOGLE_OAUTH_INVALID_RESPONSE"),
    (_Response(_valid(), headers={"Content-Encoding": "gzip"}), "GOOGLE_OAUTH_INVALID_RESPONSE"),
    (_Response(b'{"access_token":"one","access_token":"two"}'), "GOOGLE_OAUTH_INVALID_RESPONSE"),
    (_Response(_valid(access_token="unsafe\r\nnew-header")), "GOOGLE_OAUTH_INVALID_RESPONSE"),
    (_Response(_valid(expires_in=True)), "GOOGLE_OAUTH_INVALID_RESPONSE"),
))
def test_failure_is_redacted_closed_and_never_retried(response, code):
    provider, calls, closed, _ = _provider(response)
    with pytest.raises(GoogleOAuthError) as caught:
        provider()
    assert caught.value.code == str(caught.value) == code
    assert all(value not in repr(caught.value) for value in (_CLIENT_SECRET, _REFRESH, _ACCESS))
    assert len(calls) == len(closed) == 1
