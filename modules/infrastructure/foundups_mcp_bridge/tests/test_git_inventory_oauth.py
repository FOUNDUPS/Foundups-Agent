"""Private OAuth discovery, scope enforcement and tool inventory."""

import asyncio
import time

import httpx
import pytest

from modules.infrastructure.foundups_mcp_bridge.src import git_inventory_oauth as oauth
from modules.infrastructure.foundups_mcp_bridge.src.draft_auth import ScopedTokenVerifier


_CONFIG = {
    "issuer": "https://issuer.example.test",
    "resource_url": "https://tunnel.example.test/approved/pc-git",
    "introspection_url": "https://issuer.example.test/tenant/introspect",
    "subject": "approved-operator",
    "client_id": "approved-mcp-client",
    "introspection_client_id": "readback-client",
    "introspection_client_secret": "fixture-secret",
}
_PORT = 8128
_DISCOVERY = "/.well-known/oauth-protected-resource"


def _claims(**changes):
    return {
        "active": True, "token_type": "Bearer", "iss": _CONFIG["issuer"],
        "aud": [_CONFIG["resource_url"]], "exp": int(time.time()) + 60,
        "sub": _CONFIG["subject"], "client_id": _CONFIG["client_id"],
        "scope": "git:read", **changes,
    }


@pytest.mark.parametrize("changes", [
    {"scope": "draft:read"}, {"scope": "git:read draft:write"},
    {"aud": [_CONFIG["resource_url"], "https://other.example.test/"]},
    {"client_id": "different-client"}, {"sub": "different-operator"},
    {"exp": 0},
])
def test_git_oauth_rejects_claim_mismatch(monkeypatch, changes):
    async def introspect(self, _token):
        return _claims(**changes)

    monkeypatch.setattr(ScopedTokenVerifier, "_introspect", introspect)
    verifier = oauth._GitTokenVerifier(**_CONFIG)
    assert asyncio.run(verifier.verify_token("fixture-access")) is None


def test_git_oauth_exact_discovery_and_single_tool(tmp_path, monkeypatch):
    async def introspect(self, token):
        return _claims() if token == "fixture-access" else None

    monkeypatch.setattr(ScopedTokenVerifier, "_introspect", introspect)
    app = oauth.build_git_inventory_oauth_app(tmp_path, port=_PORT, **_CONFIG)

    async def probe():
        async with app.router.lifespan_context(app), httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url=f"http://127.0.0.1:{_PORT}",
        ) as client:
            arguments = {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
            headers = {"Accept": "application/json, text/event-stream"}
            for auth in ({}, {"Authorization": "Bearer fixture-denied"}):
                denied = await client.post("/mcp", json=arguments, headers={**headers, **auth})
                assert denied.status_code == 401
                assert f"{_DISCOVERY}/approved/pc-git" in denied.headers["www-authenticate"]
            for path in ("/mcp", "/approved/pc-git"):
                meta = await client.get(_DISCOVERY + path)
                assert meta.status_code == 200
                assert meta.json() == {
                    "resource": _CONFIG["resource_url"], "authorization_servers": [_CONFIG["issuer"]],
                    "scopes_supported": ["git:read"], "bearer_methods_supported": ["header"],
                }
            headers["Authorization"] = "Bearer fixture-access"
            allowed = await client.post("/mcp", json=arguments, headers=headers)
            assert allowed.status_code == 200
            tools = allowed.json()["result"]["tools"]
            assert [tool["name"] for tool in tools] == ["get_git_inventory"]
            assert set(tools[0]["inputSchema"]["properties"]) == {"request_id", "section", "offset"}
            assert tools[0]["_meta"]["securitySchemes"] == [{"type": "oauth2", "scopes": ["git:read"]}]
            bad_origin = await client.post(
                "/mcp", json=arguments, headers={**headers, "Origin": "https://other.example.test"},
            )
            assert bad_origin.status_code == 403
            query = await client.post("/mcp?access_token=fixture-access", json=arguments, headers=headers)
            assert query.status_code == 400
            duplicate = await client.post("/mcp", json=arguments, headers=[
                *headers.items(), ("Authorization", "Bearer fixture-denied"),
            ])
            assert duplicate.status_code == 400

    asyncio.run(probe())
