"""Private draft MCP authorization with a synthetic introspection provider."""

import asyncio
import json
from urllib.parse import parse_qs

import httpx
import pytest

from modules.infrastructure.foundups_mcp_bridge.src import draft_auth


ISSUER = "https://auth.example.test"
INTROSPECTION_URL = ISSUER + "/introspect"
RESOURCE = "https://mcp.example.test/drafts"
SUBJECT = "fixture-caller"
CALLER_CLIENT = "fixture-chatgpt"
INTROSPECTION_CLIENT = "fixture-introspector"
INTROSPECTION_SECRET = "fixture-only-credential"
BEARER = "fixture-bearer.123"
READ = draft_auth.DRAFT_READ_SCOPE
WRITE = draft_auth.DRAFT_WRITE_SCOPE


def _verifier(**overrides):
    return draft_auth.DraftTokenVerifier(**({
        "issuer": ISSUER,
        "introspection_url": INTROSPECTION_URL,
        "resource_url": RESOURCE,
        "subject": SUBJECT,
        "client_id": CALLER_CLIENT,
        "introspection_client_id": INTROSPECTION_CLIENT,
        "introspection_client_secret": INTROSPECTION_SECRET,
    } | overrides))


def _claims(**overrides):
    return {
        "active": True, "iss": ISSUER, "aud": RESOURCE, "sub": SUBJECT,
        "client_id": CALLER_CLIENT, "scope": READ, "exp": 4_000_000_000,
        "token_type": "Bearer",
    } | overrides


def _response(body=None, *, status=200, headers=None):
    content = body if isinstance(body, bytes) else json.dumps(body).encode()
    return httpx.Response(
        status,
        headers={"content-type": "application/json"} | (headers or {}),
        stream=httpx.ByteStream(content),
    )


def _mock_http(monkeypatch, handler):
    real_client = httpx.AsyncClient
    requests = []

    async def dispatch(request):
        requests.append(request)
        return await handler(request) if asyncio.iscoroutinefunction(handler) else handler(request)

    def client(**kwargs):
        assert kwargs["trust_env"] is False
        assert kwargs["follow_redirects"] is False
        assert 0 < kwargs["timeout"] <= 5
        return real_client(transport=httpx.MockTransport(dispatch), **kwargs)

    monkeypatch.setattr(draft_auth.httpx, "AsyncClient", client)
    return requests


@pytest.mark.parametrize("scope", [READ, f"{READ} {WRITE}"])
def test_introspection_bound_to_configured_resource_and_scope(monkeypatch, scope):
    requests = _mock_http(monkeypatch, lambda _: _response(_claims(aud=[RESOURCE], scope=scope)))
    verified = asyncio.run(_verifier().verify_token(BEARER))

    assert verified is not None
    assert verified.resource == RESOURCE and verified.client_id == CALLER_CLIENT
    assert verified.scopes == scope.split(" ")
    assert len(requests) == 1
    request = requests[0]
    assert str(request.url) == INTROSPECTION_URL and request.method == "POST"
    assert request.headers["authorization"].startswith("Basic ")
    assert parse_qs(request.content.decode()) == {"token": [BEARER], "token_type_hint": ["access_token"]}


@pytest.mark.parametrize("overrides", [
    {"active": False}, {"active": 1}, {"iss": "https://other.example.test"},
    {"aud": [RESOURCE, "https://other.example.test/drafts"]}, {"aud": ISSUER},
    {"sub": "different-caller"}, {"client_id": INTROSPECTION_CLIENT},
    {"token_type": "Refresh"}, {"token_type": None}, {"token_use": "refresh"},
    {"exp": 1}, {"exp": True}, {"exp": "4000000000"}, {"nbf": 4_000_000_000},
    {"scope": WRITE}, {"scope": f"{READ} {READ}"}, {"scope": f"{READ} other"},
])
def test_unbound_revoked_or_expired_token_denied(monkeypatch, overrides):
    _mock_http(monkeypatch, lambda _: _response(_claims(**overrides)))
    assert asyncio.run(_verifier().verify_token(BEARER)) is None


def test_revocation_is_checked_again_on_next_request(monkeypatch):
    results = iter([_claims(), {"active": False}])
    requests = _mock_http(monkeypatch, lambda _: _response(next(results)))
    verifier = _verifier()

    async def verify():
        assert await verifier.verify_token(BEARER) is not None
        assert await verifier.verify_token(BEARER) is None

    asyncio.run(verify())
    assert len(requests) == 2


@pytest.mark.parametrize("status,body,headers", [
    (307, None, {"location": "https://elsewhere.example.test"}),
    (500, BEARER.encode(), {}),
    (200, b"{malformed", {}),
    (200, b'{"active":false,"active":true}', {}),
    (200, b" " * 9000, {}),
    (200, b"{}", {"content-encoding": "gzip"}),
    (200, b"{}", {"content-type": "text/html"}),
])
def test_introspection_response_fails_closed(monkeypatch, caplog, status, body, headers):
    requests = _mock_http(monkeypatch, lambda _: _response(body, status=status, headers=headers))
    assert asyncio.run(_verifier().verify_token(BEARER)) is None
    assert len(requests) == 1
    assert BEARER not in caplog.text and INTROSPECTION_SECRET not in caplog.text


def test_invalid_bearer_and_timeout(monkeypatch):
    async def timed_out(request):
        raise httpx.ReadTimeout("fixture timeout", request=request)

    requests = _mock_http(monkeypatch, timed_out)
    verifier = _verifier()
    assert asyncio.run(verifier.verify_token("invalid token")) is None
    assert asyncio.run(verifier.verify_token("a" * 9000)) is None
    assert not requests
    assert asyncio.run(verifier.verify_token(BEARER)) is None
    assert len(requests) == 1


@pytest.mark.parametrize("overrides", [
    {"introspection_url": "http://auth.example.test/introspect"},
    {"introspection_url": "https://user@auth.example.test/introspect"},
    {"introspection_url": "https://auth.example.test/introspect?forward=fixture"},
    {"introspection_url": "https://auth.example.test:99999/introspect"},
    {"resource_url": ""}, {"subject": ""}, {"introspection_client_secret": ""},
    {"introspection_client_id": CALLER_CLIENT},
])
def test_insecure_or_incomplete_configuration_rejected(overrides):
    with pytest.raises(ValueError, match=r"^INVALID_DRAFT_"):
        _verifier(**overrides)
