"""
Unified Response Schema for FoundUps MCP Bridge.

All tools return responses in this format for consistency.

WSP References:
- WSP 97: Truthful verification (no fake data)
- WSP 11: Public API documentation
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class MCPResponse:
    """Unified MCP tool response."""

    status: str  # "ok" | "error" | "disabled_in_v1"
    data: Any = None
    error: Optional[str] = None
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict."""
        result = {
            "status": self.status,
            "meta": {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                **self.meta,
            },
        }
        if self.status == "ok":
            result["data"] = self.data
        elif self.status == "error":
            result["error"] = self.error or "Unknown error"
        elif self.status == "disabled_in_v1":
            result["error"] = self.error or "This capability is disabled in v1 (perception-only mode)"
            result["data"] = self.data  # May contain schema info
        return result


def ok_response(data: Any, **meta) -> Dict[str, Any]:
    """Create successful response."""
    return MCPResponse(status="ok", data=data, meta=meta).to_dict()


def error_response(message: str, **meta) -> Dict[str, Any]:
    """Create error response."""
    return MCPResponse(status="error", error=message, meta=meta).to_dict()


def disabled_response(tool_name: str, schema: Optional[Dict] = None, **meta) -> Dict[str, Any]:
    """Create disabled-in-v1 response with schema hint."""
    return MCPResponse(
        status="disabled_in_v1",
        error=f"Tool '{tool_name}' is disabled in v1 (perception-only mode). Execution capabilities will be available in v2.",
        data={"tool": tool_name, "schema": schema} if schema else None,
        meta=meta,
    ).to_dict()
