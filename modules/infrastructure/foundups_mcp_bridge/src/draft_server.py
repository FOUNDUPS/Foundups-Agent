"""Dedicated authenticated loopback MCP resource server; never a Holo tool."""

from __future__ import annotations

import argparse
from importlib.metadata import version
import os
from pathlib import Path
import stat
from typing import Annotated

from anyio import from_thread, to_thread
from cryptography.fernet import Fernet
from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.routes import create_protected_resource_routes
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.tools import Tool
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import CallToolResult, TextContent, ToolAnnotations
from pydantic import Field
from starlette.responses import JSONResponse
from starlette.routing import Route

from .draft_auth import DRAFT_READ_SCOPE, DRAFT_WRITE_SCOPE, DraftTokenVerifier
from .draft_correction import DraftCorrection, DraftJournal, DraftPolicy, ID, SHA
from .draft_gmail import GmailDraftAdapter
from .draft_google_oauth import GoogleTokenProvider

LOOPBACK = "127.0.0.1"
MAX_MCP_BODY = 16_384
TokenID = Annotated[str, Field(strict=True, pattern=f"^{ID.pattern}$")]
Digest = Annotated[str, Field(strict=True, pattern=f"^{SHA.pattern}$")]
Sender = Annotated[str, Field(strict=True, min_length=3, max_length=254)]


class DraftMCP(FastMCP):
    async def call_tool(self, name, arguments):
        # The SDK's FastMCP binder can coerce JSON strings and ignore extra
        # arguments. Admit only the original wire types and a closed key set.
        if name == "inspect_draft":
            valid = not arguments
        elif name == "set_draft_sender":
            required = {"draft_id": ID, "expected_digest": SHA, "request_id": ID}
            keys = {*required, "approved_sender"}
            valid = (
                set(arguments) in (keys, keys | {"dry_run"})
                and all(type(arguments[key]) is str and regex.fullmatch(arguments[key])
                        for key, regex in required.items())
                and type(arguments["approved_sender"]) is str
                and 3 <= len(arguments["approved_sender"]) <= 254
                and type(arguments.get("dry_run", True)) is bool
            )
        else:
            valid = False
        if not valid:
            return CallToolResult(isError=True, content=[
                TextContent(type="text", text="Unknown tool or invalid arguments.")
            ])
        return await super().call_tool(name, arguments)


def build_app(service: DraftCorrection, verifier, *, issuer: str, resource_url: str, port: int):
    async def inspect_draft() -> dict[str, object]:
        """Inspect the one approved draft. Returns metadata and digests, never message content."""
        return await to_thread.run_sync(service.inspect_draft)

    async def set_draft_sender(draft_id: TokenID, expected_digest: Digest,
                               approved_sender: Sender, request_id: TokenID,
                               dry_run: Annotated[bool, Field(strict=True)] = True) -> dict[str, object]:
        """Preview a From-only correction. A live update requires dry_run=false and a private approval."""
        auth = get_access_token()
        may_write = auth is not None and DRAFT_WRITE_SCOPE in auth.scopes

        async def confirm():
            current = await verifier.verify_token(auth.token) if auth is not None else None
            return current is not None and DRAFT_WRITE_SCOPE in current.scopes

        return await to_thread.run_sync(
            lambda: service.set_draft_sender(draft_id, expected_digest, approved_sender, request_id,
                                             dry_run=dry_run, allow_write=may_write,
                                             confirm_write=lambda: from_thread.run(confirm))
        )

    scopes = [DRAFT_READ_SCOPE, DRAFT_WRITE_SCOPE]
    tools = [
        Tool.from_function(inspect_draft,
                           annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True),
                           meta={"securitySchemes": [{"type": "oauth2", "scopes": scopes[:1]}]}),
        Tool.from_function(set_draft_sender,
                           annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True,
                                                       idempotentHint=False, openWorldHint=True),
                           meta={"securitySchemes": [{"type": "oauth2", "scopes": scopes}]}),
    ]
    for tool in tools:
        tool.parameters["additionalProperties"] = False

    auth = AuthSettings(issuer_url=issuer, resource_server_url=resource_url,
                        required_scopes=scopes[:1], validate_token_resource=True)
    mcp = DraftMCP(
        "FoundUps Private Draft Sender", tools=tools,
        instructions="Inspect the approved draft first. Preview by default. A live call can only "
                     "change From on the same existing draft. This service cannot send email.",
        token_verifier=verifier, auth=auth, stateless_http=True, json_response=True,
        max_request_body_size=MAX_MCP_BODY, streamable_http_path="/mcp",
        transport_security=TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=[f"{LOOPBACK}:{port}"],
            allowed_origins=[f"http://{LOOPBACK}:{port}"],
        ),
    )

    @mcp.custom_route("/health", methods=["GET"])
    async def health(_request):
        # Liveness only; never queries OAuth or Gmail.
        return JSONResponse({"status": "ok"}, headers={"Cache-Control": "no-store"})

    app = mcp.streamable_http_app()
    # Advertise the optional write scope without requiring it for initialization.
    metadata = create_protected_resource_routes(
        resource_url=auth.resource_server_url, authorization_servers=[auth.issuer_url],
        scopes_supported=scopes,
    )
    async def protected_resource(_request):
        return JSONResponse({
            "resource": resource_url, "authorization_servers": [issuer],
            "scopes_supported": scopes, "bearer_methods_supported": ["header"],
        })

    # The tunnel probes the path of the local /mcp target even when the
    # advertised external OAuth resource has a different path.
    metadata_paths = {"/.well-known/oauth-protected-resource/mcp", *(route.path for route in metadata)}
    app.router.routes[:] = [existing for existing in app.router.routes
                            if getattr(existing, "path", None) not in metadata_paths]
    for path in sorted(metadata_paths):
        app.router.routes.insert(0, Route(path, protected_resource, methods=["GET"]))

    host = f"{LOOPBACK}:{port}".encode("ascii")
    paths = {"/mcp", "/health", *metadata_paths}

    async def boundary(scope, receive, send):
        if scope["type"] == "websocket":
            await send({"type": "websocket.close", "code": 1008})
            return
        if scope["type"] != "http":
            await app(scope, receive, send)
            return
        if scope.get("path") not in paths:
            await JSONResponse({"error": "not_found"}, status_code=404)(scope, receive, send)
            return
        headers = scope.get("headers", ())
        hosts = [value for name, value in headers if name == b"host"]
        origins = [value for name, value in headers if name == b"origin"]
        if origins not in ([], [b"http://" + host]):
            await JSONResponse({"error": "origin_forbidden"}, status_code=403)(scope, receive, send)
            return
        if (scope.get("query_string") or hosts != [host]
                or sum(name == b"authorization" for name, _ in headers) > 1):
            await JSONResponse({"error": "invalid_request"}, status_code=400)(scope, receive, send)
            return

        async def no_cache(message):
            if message["type"] == "http.response.start":
                message = {**message, "headers": [*message.get("headers", ()),
                                                   (b"cache-control", b"no-store")]}
            await send(message)
        await app(scope, receive, no_cache)

    return boundary


def _private_journal(path_value: str) -> Path:
    directory = Path(path_value)
    if not directory.is_absolute() or directory != directory.resolve(strict=True) or not directory.is_dir():
        raise ValueError("invalid state directory")
    if os.name != "nt" and (directory.stat().st_uid != os.geteuid() or directory.stat().st_mode & 0o077):
        raise ValueError("state directory must be owned and private")
    if any((ancestor / ".git").exists() for ancestor in (directory, *directory.parents)):
        raise ValueError("state directory must be outside Git")
    for name in ("draft.sqlite3", "draft.sqlite3-journal", "draft.sqlite3-wal", "draft.sqlite3-shm"):
        path = directory / name
        try:
            info = path.lstat()
        except FileNotFoundError:
            continue
        if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
                or getattr(info, "st_file_attributes", 0) & 0x400):
            raise ValueError("invalid journal path")
    return directory / "draft.sqlite3"


def _secret(name: str) -> str:
    # systemd credential files are decrypted by the supervisor into its private
    # runtime credential mount. Windows can inject directly from its vault.
    directory = os.environ.get("CREDENTIALS_DIRECTORY")
    if directory is None:
        return os.environ[name]
    if name in os.environ:
        raise ValueError("ambiguous secret source")
    root = Path(directory)
    if not root.is_absolute():
        raise ValueError("invalid credential mount")
    with (root / name).open("rb") as source:
        data = source.read(8193)
    if not data or len(data) > 8192:
        raise ValueError("invalid credential size")
    return data.decode("ascii").rstrip("\r\n")


def load_app(port: int):
    env = os.environ
    prefix = "FOUNDUPS_DRAFT_"
    issuer = env[prefix + "MCP_ISSUER"]
    resource_url = env[prefix + "MCP_RESOURCE"]
    verifier = DraftTokenVerifier(
        issuer=issuer, introspection_url=env[prefix + "INTROSPECTION_URL"],
        resource_url=resource_url, subject=env[prefix + "MCP_SUBJECT"],
        client_id=env[prefix + "MCP_CLIENT_ID"],
        introspection_client_id=env[prefix + "INTROSPECTION_CLIENT_ID"],
        introspection_client_secret=_secret(prefix + "INTROSPECTION_CLIENT_SECRET"),
    )
    issued = env.get(prefix + "APPROVAL_ISSUED")
    expires = env.get(prefix + "APPROVAL_EXPIRES")
    policy = DraftPolicy(
        env[prefix + "GMAIL_ACCOUNT"], env[prefix + "APPROVED_SENDER"],
        env[prefix + "TARGET_SHA256"], env.get(prefix + "APPROVED_REQUEST_ID"),
        int(issued) if issued is not None else None,
        int(expires) if expires is not None else None,
    )
    gmail = GmailDraftAdapter(policy.account, GoogleTokenProvider(
        env[prefix + "GOOGLE_CLIENT_ID"], _secret(prefix + "GOOGLE_CLIENT_SECRET"),
        _secret(prefix + "GOOGLE_REFRESH_TOKEN"),
    ))
    journal = DraftJournal(
        _private_journal(env[prefix + "STATE_DIR"]),
        Fernet(_secret(prefix + "SNAPSHOT_KEY").encode("ascii")),
    )
    return build_app(DraftCorrection(policy, gmail, journal), verifier,
                     issuer=issuer, resource_url=resource_url, port=port)


def main():
    parser = argparse.ArgumentParser(description="Run the separate private draft MCP resource server.")
    parser.add_argument("--port", default=8178, type=int)
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error("invalid port")
    try:
        if version("mcp") != "1.30.0":
            raise ValueError("runtime not admitted")
        if os.name != "nt":
            os.umask(0o077)
        app = load_app(args.port)
    except Exception:
        parser.exit(2, "Private draft MCP startup refused: verify the admitted runtime and private configuration.\n")
    import uvicorn
    uvicorn.run(app, host=LOOPBACK, port=args.port, access_log=False, proxy_headers=False,
                log_level="warning", limit_concurrency=8, timeout_keep_alive=3,
                timeout_graceful_shutdown=20)


if __name__ == "__main__":
    main()
