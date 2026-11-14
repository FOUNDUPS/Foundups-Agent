"""OAuth profile for the existing bridge's private PC Git inventory tool."""

from __future__ import annotations

import os
from pathlib import Path

from fastmcp import FastMCP
from fastmcp.server.auth import AccessToken, RemoteAuthProvider, TokenVerifier
from mcp.server.auth.routes import build_resource_metadata_url
from pydantic import AnyHttpUrl
from starlette.middleware import Middleware
from starlette.responses import JSONResponse
from starlette.routing import Route

from .draft_auth import ScopedTokenVerifier
from .mcp_server import _register_git_inventory


GIT_READ_SCOPE = "git:read"
_PREFIX = "FOUNDUPS_MCP_GIT_OAUTH_"


class _GitTokenVerifier(TokenVerifier):
    def __init__(self, **configuration):
        super().__init__(required_scopes=[GIT_READ_SCOPE])
        self._verifier = ScopedTokenVerifier(
            **configuration, required_scope=GIT_READ_SCOPE,
            allowed_scopes=frozenset({GIT_READ_SCOPE}),
        )

    async def verify_token(self, token: str) -> AccessToken | None:
        verified = await self._verifier.verify_token(token)
        return AccessToken(**verified.model_dump(exclude_none=True)) if verified is not None else None


class _TunnelAuth(RemoteAuthProvider):
    """The external protected resource path can differ from the local /mcp."""

    def __init__(self, verifier: TokenVerifier, issuer: str, resource_url: str):
        self._exact_external_resource = AnyHttpUrl(resource_url)
        self._exact_issuer = issuer
        if str(self._exact_external_resource) != resource_url:
            raise ValueError("Git OAuth requires the exact canonical external resource URL")
        super().__init__(verifier, [AnyHttpUrl(issuer)], base_url=self._exact_external_resource)

    def _get_resource_url(self, path: str | None = None) -> AnyHttpUrl:
        return self._exact_external_resource

    def get_routes(self, mcp_path: str | None = None) -> list[Route]:
        self.set_mcp_path(mcp_path)
        metadata_path = build_resource_metadata_url(self._exact_external_resource).path

        async def discovery(_request):
            return JSONResponse({
                "resource": str(self._exact_external_resource),
                "authorization_servers": [self._exact_issuer],
                "scopes_supported": [GIT_READ_SCOPE], "bearer_methods_supported": ["header"],
            }, headers={"Cache-Control": "no-store"})

        return [Route(path, discovery, methods=["GET"]) for path in sorted({
            "/.well-known/oauth-protected-resource/mcp", metadata_path,
        })]


class _GitRequestBoundary:
    def __init__(self, app):
        self._app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            names = [name for name, _ in scope.get("headers", ())]
            if scope.get("query_string") or any(
                names.count(name) > 1 for name in (b"authorization", b"host", b"origin")
            ):
                return await JSONResponse({"error": "invalid_request"}, status_code=400)(
                    scope, receive, send,
                )
        return await self._app(scope, receive, send)


def build_git_inventory_oauth_app(
    repo_root: Path, *, port: int, issuer: str, resource_url: str,
    introspection_url: str, subject: str, client_id: str,
    introspection_client_id: str, introspection_client_secret: str,
):
    """Serve exactly Git inventory and RFC 9728 discovery for one OAuth caller."""
    verifier = _GitTokenVerifier(
        issuer=issuer, resource_url=resource_url, introspection_url=introspection_url,
        subject=subject, client_id=client_id, introspection_client_id=introspection_client_id,
        introspection_client_secret=introspection_client_secret,
    )
    server = FastMCP("FoundUps PC Git Inventory", auth=_TunnelAuth(verifier, issuer, resource_url))
    _register_git_inventory(server, repo_root, oauth_scope=GIT_READ_SCOPE)

    @server.custom_route("/health", methods=["GET"])
    async def health(_request):
        return JSONResponse({"status": "ok", "auth_required": True, "tool_count": 1})

    return server.http_app(
        path="/mcp", transport="streamable-http", stateless_http=True, json_response=True,
        host_origin_protection=True, allowed_hosts=[f"127.0.0.1:{port}"],
        allowed_origins=[f"http://127.0.0.1:{port}"],
        middleware=[Middleware(_GitRequestBoundary)],
    )


def load_git_inventory_oauth_app(repo_root: Path, port: int):
    return build_git_inventory_oauth_app(
        repo_root, port=port, issuer=os.environ[_PREFIX + "ISSUER"],
        resource_url=os.environ[_PREFIX + "RESOURCE"],
        introspection_url=os.environ[_PREFIX + "INTROSPECTION_URL"],
        subject=os.environ[_PREFIX + "SUBJECT"], client_id=os.environ[_PREFIX + "CLIENT_ID"],
        introspection_client_id=os.environ[_PREFIX + "INTROSPECTION_CLIENT_ID"],
        introspection_client_secret=os.environ[_PREFIX + "INTROSPECTION_CLIENT_SECRET"],
    )
