"""FoundUps Private MCP Bridge - Perception layer for AI-assisted execution."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .response_schema import ok_response, error_response, disabled_response, MCPResponse

if TYPE_CHECKING:
    from .bridge_server import FoundUpsMCPBridge as FoundUpsMCPBridge

__all__ = [
    "FoundUpsMCPBridge",
    "MCPResponse",
    "ok_response",
    "error_response",
    "disabled_response",
]


def __getattr__(name: str) -> Any:
    """Load the optional MCP runtime only when its bridge class is requested."""
    if name == "FoundUpsMCPBridge":
        from .bridge_server import FoundUpsMCPBridge

        globals()[name] = FoundUpsMCPBridge
        return FoundUpsMCPBridge
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
