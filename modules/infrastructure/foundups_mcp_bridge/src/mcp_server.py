#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FoundUps MCP Bridge Remote Server (FastMCP SSE Transport).
==========================================================

Exposes the private FoundUps MCP perception layer over standard Model Context
Protocol (MCP) transport (SSE and stdio) for remote agents such as ChatGPT
via secure tunnels (ngrok/cloudflared).

WSP References:
- WSP 96: Model Context Protocol Governance and Consensus
- WSP 97: Truthful Verification (perception-only read boundary)
- WSP 50: Pre-Action Verification (HoloIndex search prior to modification)
"""

from __future__ import annotations

import argparse
import inspect
import io
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Callable, Dict, Optional

# === UTF-8 ENFORCEMENT (WSP 90) ===
if __name__ == "__main__" and sys.platform.startswith("win"):
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    except (OSError, ValueError):
        pass
# === END UTF-8 ENFORCEMENT ===

from fastmcp import FastMCP
from fastmcp.server.http import create_sse_app
from starlette.responses import JSONResponse

from .bridge_server import FoundUpsMCPBridge

logger = logging.getLogger(__name__)

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8128


def get_original_function(wrapped_func: Callable) -> Callable:
    """Extract original unwrapped function from bridge wrapper closure if present."""
    if hasattr(wrapped_func, "__closure__") and wrapped_func.__closure__:
        for cell in wrapped_func.__closure__:
            val = cell.cell_contents
            if callable(val) and not isinstance(val, FoundUpsMCPBridge):
                return val
    return wrapped_func


class AuthMiddleware:
    """
    Enforce token-based authentication on remote MCP endpoints.

    Validates 'Authorization: Bearer <token>' header or '?token=<token>' query parameter.
    Fails closed (401 Unauthorized) when token is configured but invalid.
    """

    def __init__(
        self,
        app: Any,
        auth_token: Optional[str] = None,
        require_auth: bool = False,
        tools_count: int = 0,
    ):
        self.app = app
        self.auth_token = (auth_token or "").strip()
        self.require_auth = require_auth
        self.tools_count = tools_count

    async def __call__(self, scope: Dict[str, Any], receive: Callable, send: Callable) -> None:
        if scope["type"] == "http":
            path = scope.get("path", "")

            # Public unauthenticated health probe
            if path == "/health":
                resp = JSONResponse({
                    "status": "ok",
                    "service": "foundups_mcp_bridge",
                    "tools_count": self.tools_count,
                    "auth_required": bool(self.auth_token or self.require_auth),
                })
                await resp(scope, receive, send)
                return

            # Check authentication
            if self.auth_token:
                headers = dict(scope.get("headers", []))
                auth_header = headers.get(b"authorization", b"").decode("utf-8", errors="replace").strip()
                query_string = scope.get("query_string", b"").decode("utf-8", errors="replace")

                token_from_query = ""
                for param in query_string.split("&"):
                    if param.startswith("token=") or param.startswith("auth_token="):
                        token_from_query = param.split("=", 1)[1].strip()
                        break

                valid = False
                if auth_header.startswith("Bearer "):
                    token = auth_header[7:].strip()
                    if token == self.auth_token:
                        valid = True
                elif token_from_query == self.auth_token:
                    valid = True

                if not valid:
                    logger.warning("[MCP-AUTH] Rejected unauthenticated request to %s", path)
                    resp = JSONResponse(
                        {"error": "Unauthorized - valid Bearer token required"},
                        status_code=401,
                    )
                    await resp(scope, receive, send)
                    return

            elif self.require_auth:
                logger.error("[MCP-AUTH] Remote auth required but no FOUNDUPS_MCP_AUTH_TOKEN configured")
                resp = JSONResponse(
                    {"error": "Server misconfigured - auth required but no token configured"},
                    status_code=500,
                )
                await resp(scope, receive, send)
                return

        await self.app(scope, receive, send)


def build_mcp_server(
    repo_root: Optional[Path] = None,
    server_name: str = "FoundUps MCP Bridge",
) -> FastMCP:
    """
    Create and configure FastMCP server instance wrapping FoundUpsMCPBridge.

    Dynamically extracts signatures and type annotations from original functions,
    stripping the internal `repo_root` parameter and binding it to the bridge instance.

    Args:
        repo_root: Repository root path (auto-detected if None)
        server_name: MCP server name reported to connecting clients

    Returns:
        Configured FastMCP server instance
    """
    bridge = FoundUpsMCPBridge(repo_root=repo_root)
    mcp = FastMCP(name=server_name)

    for name, wrapped in bridge._tools.items():
        original_func = get_original_function(wrapped)

        sig = inspect.signature(original_func)
        params = list(sig.parameters.values())
        has_repo_root = bool(params and params[0].name == "repo_root")

        if has_repo_root:
            new_params = params[1:]
            new_sig = sig.replace(parameters=new_params)

            def _make_tool_fn(orig_fn):
                def _tool_fn(*args, **kwargs):
                    return orig_fn(bridge.repo_root, *args, **kwargs)
                return _tool_fn

            tool_callable = _make_tool_fn(original_func)
        else:
            new_sig = sig
            tool_callable = original_func

        tool_callable.__name__ = name
        tool_callable.__doc__ = (original_func.__doc__ or "").strip()
        tool_callable.__signature__ = new_sig

        annotations = getattr(original_func, "__annotations__", {}).copy()
        if "repo_root" in annotations:
            del annotations["repo_root"]
        tool_callable.__annotations__ = annotations

        # Register tool with FastMCP
        mcp.tool(name=name)(tool_callable)

    logger.info(f"[MCP-SERVER] FastMCP initialized with {len(bridge._tools)} tools")
    return mcp


def build_asgi_app(
    repo_root: Optional[Path] = None,
    server_name: str = "FoundUps MCP Bridge",
    auth_token: Optional[str] = None,
    require_auth: bool = False,
) -> Any:
    """
    Build Starlette ASGI application with FastMCP SSE transport and AuthMiddleware.
    """
    mcp = build_mcp_server(repo_root=repo_root, server_name=server_name)
    token = auth_token or os.getenv("FOUNDUPS_MCP_AUTH_TOKEN", "")
    req_auth = require_auth or (os.getenv("FOUNDUPS_MCP_REQUIRE_AUTH", "0") == "1")

    base_app = create_sse_app(mcp, message_path="/message/", sse_path="/sse")
    app = AuthMiddleware(
        app=base_app,
        auth_token=token,
        require_auth=req_auth,
        tools_count=len(mcp._tool_manager._tools) if hasattr(mcp, "_tool_manager") else 39,
    )
    return app


def main():
    """CLI entrypoint to run the FoundUps MCP server."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    parser = argparse.ArgumentParser(description="FoundUps MCP Bridge Server")
    parser.add_argument(
        "--transport",
        choices=["sse", "stdio"],
        default="sse",
        help="Transport type (default: sse)",
    )
    parser.add_argument(
        "--host",
        type=str,
        default=os.getenv("FOUNDUPS_MCP_HOST", DEFAULT_HOST),
        help=f"Host to bind SSE server (default: {DEFAULT_HOST})",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("FOUNDUPS_MCP_PORT", str(DEFAULT_PORT))),
        help=f"Port to bind SSE server (default: {DEFAULT_PORT})",
    )
    parser.add_argument(
        "--auth-token",
        type=str,
        default=os.getenv("FOUNDUPS_MCP_AUTH_TOKEN", ""),
        help="Optional auth token required for requests (Bearer token)",
    )
    parser.add_argument(
        "--repo-root",
        type=str,
        default=None,
        help="Repository root path override",
    )

    args = parser.parse_args()
    repo_root = Path(args.repo_root) if args.repo_root else None

    # Fail closed check for remote exposure
    is_loopback = args.host in ("127.0.0.1", "localhost", "::1")
    auth_token = (args.auth_token or "").strip()
    if not is_loopback and not auth_token:
        print("[MCP-SERVER-ERROR] Refusing to bind to non-loopback host without --auth-token or FOUNDUPS_MCP_AUTH_TOKEN (fail closed per WSP 97).", file=sys.stderr)
        sys.exit(1)

    if args.transport == "sse":
        import uvicorn
        asgi_app = build_asgi_app(
            repo_root=repo_root,
            auth_token=auth_token,
            require_auth=not is_loopback,
        )
        print(f"[MCP-SERVER] Starting SSE server on http://{args.host}:{args.port}/sse")
        if auth_token:
            print("[MCP-SERVER] Authentication enabled (Bearer token enforced)")
        else:
            print("[MCP-SERVER] Running unauthenticated (loopback only)")

        config = uvicorn.Config(
            asgi_app,
            host=args.host,
            port=args.port,
            log_level="info",
            access_log=False,
        )
        server = uvicorn.Server(config)
        server.run()
    else:
        app = build_mcp_server(repo_root=repo_root)
        print("[MCP-SERVER] Starting stdio server")
        app.run(transport="stdio")


if __name__ == "__main__":
    main()
