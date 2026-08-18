"""
FastMCP Server for FoundUps Perception Bridge.
==============================================

Domain: infrastructure
Module: foundups_mcp_bridge

Exposes FoundUps MCP perception tools via FastMCP over SSE and stdio transports.
Enforces:
1. Strict Remote Read-Only Allowlist (mutation/execution tools strictly excluded).
2. Fail-closed Token Authentication (Bearer token header only; URL tokens prohibited).
   Refuses construction/startup if require_auth=True but token is empty.
3. Public /health probe for tunnel monitoring.

WSP References:
- WSP 96: Model Context Protocol Governance and Consensus
- WSP 97: Truthful Verification (explicit read-only perception boundary & fail-closed auth)
- WSP 80: Cube-Level DAE Orchestration
"""

from __future__ import annotations

import argparse
import asyncio
import hmac
import inspect
import io
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

# === UTF-8 ENFORCEMENT (WSP 90) ===
if __name__ == "__main__" and sys.platform.startswith("win"):
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    except (OSError, ValueError):
        pass
# === END UTF-8 ENFORCEMENT ===

logger = logging.getLogger(__name__)

# Explicit Remote Read-Only Allowlist per WSP 97
# Mutation, execution, or dispatch tools are strictly prohibited from remote registration.
REMOTE_READ_ONLY_ALLOWLIST: Tuple[str, ...] = (
    # Repo Perception
    "get_repo_tree",
    "read_file",
    "search_repo",
    "get_recent_changes",
    # Documentation Access
    "get_wsp_docs",
    "get_module_docs",
    "get_interface_doc",
    "get_test_docs",
    "get_modlog",
    "get_violations",
    # AI Overseer Perception
    "get_mission_history",
    "get_pattern_memory",
    "get_overseer_status",
    "get_coordination_state",
    "get_known_failure_patterns",
    # Dependency Analysis
    "get_module_dependencies",
    "get_reverse_dependencies",
    # Diff and Verification
    "get_file_diff",
    "get_diff_summary",
    "get_change_impact_score",
    # HoloIndex Recall
    "holo_search",
    "holo_related",
    "holo_failure_memory",
    "holo_pattern_search",
    "holo_task_packet",
    # Signal Normalization (State Compression)
    "get_overseer_summary",
    "get_hot_modules",
    "get_repeated_failures",
    "get_active_risks",
    "get_recommended_focus",
    "get_prompt_context_packet",
    # RedDog State & Context
    "get_reddog_state",
    "get_reddog_analysis_context",
)


def _get_repo_root() -> Path:
    """Resolve repository root."""
    return Path(__file__).resolve().parent.parent.parent.parent.parent


def get_original_function(wrapped_func: Any) -> Any:
    """Extract underlying original function from closures or wrappers."""
    if hasattr(wrapped_func, "__wrapped__"):
        return get_original_function(wrapped_func.__wrapped__)
    if hasattr(wrapped_func, "__closure__") and wrapped_func.__closure__:
        for cell in wrapped_func.__closure__:
            try:
                contents = cell.cell_contents
                if callable(contents) and contents is not wrapped_func:
                    return get_original_function(contents)
            except ValueError:
                pass
    return wrapped_func


def _make_tool_wrapper(bridge_func: Callable, orig_func: Callable) -> Callable:
    """
    Create a clean tool wrapper without repo_root in its signature.

    Dynamically matches original parameter types and default values so FastMCP
    generates accurate JSON Schemas for MCP clients.
    """
    orig_sig = inspect.signature(orig_func)
    clean_params = [
        p for name, p in orig_sig.parameters.items()
        if name != "repo_root"
    ]
    clean_sig = orig_sig.replace(parameters=clean_params)

    def tool_impl(*args, **kwargs):
        bound = clean_sig.bind_partial(*args, **kwargs)
        bound.apply_defaults()
        return bridge_func(**bound.arguments)

    tool_impl.__name__ = orig_func.__name__
    tool_impl.__doc__ = orig_func.__doc__ or bridge_func.__doc__
    tool_impl.__signature__ = clean_sig
    tool_impl.__annotations__ = {
        name: p.annotation
        for name, p in clean_sig.parameters.items()
        if p.annotation != inspect.Parameter.empty
    }
    if orig_sig.return_annotation != inspect.Signature.empty:
        tool_impl.__annotations__["return"] = orig_sig.return_annotation

    return tool_impl


def build_mcp_server(repo_root: Optional[Path] = None) -> Any:
    """
    Build FastMCP server with strictly allowlisted FoundUps perception tools.

    Args:
        repo_root: Optional repository root path

    Returns:
        FastMCP server instance.
    """
    try:
        from fastmcp import FastMCP
    except ImportError as exc:
        raise ImportError(
            "fastmcp is required to build the FastMCP server. "
            "Please run within foundups-mcp-env or install fastmcp."
        ) from exc

    from .bridge_server import FoundUpsMCPBridge

    root = Path(repo_root or _get_repo_root()).resolve()
    bridge = FoundUpsMCPBridge(repo_root=root)

    mcp = FastMCP(
        name="FoundUps Perception Bridge",
        instructions=(
            "FoundUps Perception MCP Bridge provides read-only repository, "
            "architecture, documentation, and RedDog context awareness to 0102."
        ),
    )

    # Register ONLY allowlisted read-only tools
    for tool_name in REMOTE_READ_ONLY_ALLOWLIST:
        if tool_name not in bridge._tools:
            logger.warning(f"[MCP-SERVER] Allowlisted tool '{tool_name}' not found in bridge._tools")
            continue

        bridge_func = bridge._tools[tool_name]
        orig_func = get_original_function(bridge_func)
        wrapper = _make_tool_wrapper(bridge_func, orig_func)
        mcp.tool(name=tool_name, description=orig_func.__doc__ or tool_name)(wrapper)

    return mcp


class AuthMiddleware:
    """
    ASGI Middleware enforcing Authorization: Bearer <token> for remote access.

    Public endpoints:
    - /health: unauthenticated health check probe

    Protected endpoints:
    - /sse, /message/: strictly require Authorization: Bearer <token> header.
      (?token= query parameter is deliberately rejected to prevent logging secrets).
    """

    def __init__(self, app: Any, auth_token: str = "", require_auth: bool = True):
        self.app = app
        if require_auth:
            token_clean = auth_token.strip() if auth_token else ""
            if not token_clean:
                raise ValueError(
                    "auth_token is required when require_auth=True (fail-closed per WSP 97)"
                )
            self.auth_token = token_clean
            self.require_auth = True
        else:
            self.auth_token = ""
            self.require_auth = False

    async def __call__(self, scope: Dict[str, Any], receive: Any, send: Any):
        if scope.get("type") not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if path in ("/health", "/health/"):
            await self._handle_health(scope, receive, send)
            return

        if self.require_auth:
            headers = dict(scope.get("headers", []))
            auth_header = headers.get(b"authorization", b"").decode("utf-8", errors="replace")

            authenticated = False
            if auth_header.startswith("Bearer "):
                token = auth_header[7:].strip()
                if hmac.compare_digest(token, self.auth_token):
                    authenticated = True

            if not authenticated:
                await self._send_response(
                    send,
                    status=401,
                    headers=[(b"content-type", b"application/json")],
                    body=json.dumps({"error": "Unauthorized", "detail": "Valid Bearer token required"}).encode("utf-8"),
                )
                return

        await self.app(scope, receive, send)

    async def _handle_health(self, scope: Dict[str, Any], receive: Any, send: Any):
        """Unauthenticated health probe reporting service and auth status."""
        body = json.dumps({
            "status": "ok",
            "service": "foundups_mcp_bridge_sse",
            "auth_required": self.require_auth,
            "tool_count": len(REMOTE_READ_ONLY_ALLOWLIST),
        }).encode("utf-8")
        await self._send_response(
            send,
            status=200,
            headers=[(b"content-type", b"application/json")],
            body=body,
        )

    async def _send_response(self, send: Any, status: int, headers: List[Tuple[bytes, bytes]], body: bytes):
        """Helper to send ASGI HTTP response."""
        await send({
            "type": "http.response.start",
            "status": status,
            "headers": headers,
        })
        await send({
            "type": "http.response.body",
            "body": body,
        })


def build_asgi_app(
    repo_root: Optional[Path] = None,
    auth_token: Optional[str] = None,
    require_auth: bool = True,
) -> Any:
    """
    Build Starlette ASGI application for FastMCP SSE server wrapped with AuthMiddleware.

    Fails closed: raises ValueError if require_auth=True and auth_token is empty.

    Args:
        repo_root: Optional repository root path
        auth_token: Bearer auth token string
        require_auth: Whether auth is enforced

    Returns:
        ASGI application.
    """
    token = auth_token if auth_token is not None else os.getenv("FOUNDUPS_MCP_AUTH_TOKEN", "")
    if require_auth and not (token and token.strip()):
        raise ValueError("auth_token is required when require_auth=True (fail-closed per WSP 97)")

    mcp = build_mcp_server(repo_root=repo_root)

    try:
        from fastmcp.server.http import create_sse_app
        raw_app = create_sse_app(mcp, message_path="/message/", sse_path="/sse")
    except (ImportError, TypeError):
        raw_app = mcp.sse_app()

    return AuthMiddleware(raw_app, auth_token=token, require_auth=require_auth)


def main():
    """CLI entrypoint for running FastMCP server."""
    parser = argparse.ArgumentParser(description="FoundUps MCP Bridge FastMCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse"],
        default="sse",
        help="Transport protocol (default: sse)",
    )
    parser.add_argument(
        "--host",
        default=os.getenv("FOUNDUPS_MCP_HOST", "127.0.0.1"),
        help="Host to bind for SSE transport (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("FOUNDUPS_MCP_PORT", "8128")),
        help="Port to bind for SSE transport (default: 8128)",
    )
    args = parser.parse_args()

    root = _get_repo_root()
    token = os.getenv("FOUNDUPS_MCP_AUTH_TOKEN", "")
    is_loopback = args.host in ("127.0.0.1", "localhost", "::1")
    is_tunnel_mode = os.getenv("FOUNDUPS_MCP_TUNNEL_MODE", "0") == "1"
    require_auth = bool(os.getenv("FOUNDUPS_MCP_REQUIRE_AUTH", "1" if (token or is_tunnel_mode or not is_loopback) else "0") == "1")

    if require_auth and not token:
        logger.error("[MCP-SERVER] Refusing to start: auth_token required when require_auth=True (fail-closed per WSP 97).")
        print("[MCP-SERVER] Error: auth_token required when require_auth=True (fail-closed per WSP 97).", file=sys.stderr)
        sys.exit(1)

    if args.transport == "stdio":
        mcp = build_mcp_server(repo_root=root)
        mcp.run(transport="stdio")
    else:
        import uvicorn
        asgi_app = build_asgi_app(repo_root=root, auth_token=token, require_auth=require_auth)
        uvicorn.run(asgi_app, host=args.host, port=args.port, log_level="info", access_log=False)


if __name__ == "__main__":
    main()
