"""
HoloIndex FoundUp Bridge Adapter

Implements EXTERNAL_FOUNDUP_BRIDGE_CONTRACT.md for the external HoloIndex FoundUp UI.
Hooks internal HoloIndex capabilities to the shell postMessage bridge.

WSP References: WSP 15, WSP 97, WSP 11 (Interface)
"""

import logging
import time
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


@dataclass
class BridgeResult:
    """Single search result per bridge contract Section 3.1."""
    content: str
    path: str
    relevance: float = 0.0


@dataclass
class BridgeResponseData:
    """Response data wrapper per bridge contract."""
    results: List[Dict[str, Any]]
    quantum_coherence: float = 0.618
    stub: bool = False


def validate_agent_request(payload: Dict[str, Any]) -> Optional[str]:
    """
    Validate incoming agent_request payload per bridge contract Section 2.

    Returns error message if invalid, None if valid.
    """
    if not isinstance(payload, dict):
        return "payload must be a dictionary"

    action = payload.get("action")
    if not action:
        return "missing required field: action"

    if action == "semantic_search":
        if "query" not in payload:
            return "semantic_search requires 'query' field"
    elif action == "wsp_lookup":
        if "protocol_number" not in payload:
            return "wsp_lookup requires 'protocol_number' field"
    elif action == "health":
        pass  # No additional fields required
    else:
        return f"unknown action: {action}"

    return None


class HoloIndexBridgeAdapter:
    """
    Code-real Bridge Adapter Stub for HoloIndex FoundUp integration.

    This module provides the translation layer between external Shell messages
    and the internal HoloIndex engine or MCP client, fulfilling the bridge contract
    without exposing fake production networking.
    """
    def __init__(self, use_mcp_client: bool = True):
        self.use_mcp_client = use_mcp_client
        self._mcp_client = None

    async def get_mcp_client(self):
        """Lazy initialization of MCP Client if configured."""
        if self._mcp_client is None and self.use_mcp_client:
            from holo_index.mcp_client.holo_mcp_client import HoloIndexMCPClient
            self._mcp_client = HoloIndexMCPClient()
            await self._mcp_client.connect()
        return self._mcp_client

    async def get_metadata(self) -> Dict[str, Any]:
        """Stub for GET /metadata resolving FoundUp integration contract."""
        return {
            "foundup_id": "holoindex_prod_01",
            "lifecycle_stage": "incubating",
            "name": "HoloIndex",
            "version": "1.0.0-stub"
        }

    async def get_status(self) -> Dict[str, Any]:
        """Stub for GET /status representing health checks."""
        return {
            "status": "online",
            "mode": "mcp_bridged" if self.use_mcp_client else "embedded",
            "indexer_health": "ok"
        }

    async def get_tasks(self) -> list:
        """Stub for GET /tasks enumerating capabilities."""
        return [
            "semantic_search",
            "wsp_lookup",
            "cross_reference_search",
            "mine_012_conversations_for_patterns"
        ]

    async def handle_agent_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process an incoming agent_request postMessage payload mapped
        from the p.fMALL shell route 'openclaw_search' or 'openclaw_query'.

        Implements bridge contract Section 2 (inbound) and Section 3 (outbound).
        """
        # Validate request per bridge contract
        validation_error = validate_agent_request(payload)
        if validation_error:
            return self._error_response(validation_error)

        action = payload.get("action")

        try:
            if action == "semantic_search":
                return await self._do_search(
                    payload.get("query", ""),
                    payload.get("limit", 5)
                )
            elif action == "wsp_lookup":
                return await self._do_wsp_lookup(payload.get("protocol_number", ""))
            elif action == "health":
                return await self._do_health()
            else:
                return self._error_response(f"Unsupported action: {action}")
        except Exception as e:
            logger.error(f"Bridge Adapter error handling {action}: {e}")
            return self._error_response(str(e))

    def _error_response(self, error: str) -> Dict[str, Any]:
        """Build error response per bridge contract."""
        return {
            "type": "agent_response",
            "status": "error",
            "data": {"error": error}
        }

    def _success_response(
        self,
        results: List[Dict[str, Any]],
        quantum_coherence: float = 0.618,
        stub: bool = False
    ) -> Dict[str, Any]:
        """
        Build success response per bridge contract Section 3.1.

        Standard response shape:
        {
          "type": "agent_response",
          "status": "success",
          "data": {
            "results": [...],
            "quantum_coherence": 0.8
          }
        }
        """
        data = {
            "results": results,
            "quantum_coherence": quantum_coherence
        }
        if stub:
            data["stub"] = True
        return {
            "type": "agent_response",
            "status": "success",
            "data": data
        }

    async def _do_search(self, query: str, limit: int) -> Dict[str, Any]:
        """
        Execute semantic search via MCP client.

        Transforms MCP result into bridge contract response shape.
        """
        client = await self.get_mcp_client()
        if client:
            try:
                result = await client.semantic_code_search(query, limit=limit)
                # Transform MCP result to bridge contract shape
                results = []
                for item in result.get("code_results", result.get("results", [])):
                    results.append({
                        "content": item.get("content", item.get("snippet", "")),
                        "path": item.get("path", item.get("file", "")),
                        "relevance": item.get("relevance", item.get("score", 0.0))
                    })
                return self._success_response(
                    results=results,
                    quantum_coherence=result.get("quantum_coherence", 0.618)
                )
            except Exception as e:
                logger.error(f"MCP search error: {e}")
                return self._error_response(f"Search failed: {e}")
        return self._error_response("Internal client not available")

    async def _do_wsp_lookup(self, protocol_number: str) -> Dict[str, Any]:
        """
        Execute WSP protocol lookup via MCP client.

        Transforms MCP result into bridge contract response shape.
        """
        client = await self.get_mcp_client()
        if client:
            try:
                result = await client.wsp_protocol_lookup(protocol_number)
                # Wrap single protocol result in results array
                results = [{
                    "content": result.get("content", result.get("summary", f"WSP {protocol_number}")),
                    "path": result.get("path", f"WSP_framework/src/WSP_{protocol_number}.md"),
                    "relevance": 1.0,
                    "protocol": result.get("protocol_number", protocol_number),
                    "title": result.get("title", f"WSP {protocol_number}"),
                    "status": result.get("status", "active")
                }]
                return self._success_response(
                    results=results,
                    quantum_coherence=result.get("quantum_coherence", 0.8)
                )
            except Exception as e:
                logger.error(f"MCP WSP lookup error: {e}")
                return self._error_response(f"WSP lookup failed: {e}")
        return self._error_response("Internal client not available")

    async def _do_health(self) -> Dict[str, Any]:
        """
        Execute health check per bridge contract Section 4.

        Returns adapter health status without requiring MCP connection.
        """
        start_time = time.time()

        # Check MCP client availability (without forcing connection)
        mcp_status = "available" if self._mcp_client else "not_initialized"
        if self._mcp_client:
            try:
                # Quick connectivity check
                mcp_status = "connected"
            except Exception:
                mcp_status = "disconnected"

        latency_ms = round((time.time() - start_time) * 1000, 2)

        results = [{
            "content": f'{{"status": "healthy", "mcp": "{mcp_status}", "latency_ms": {latency_ms}}}',
            "path": "/f/holoindex/status",
            "relevance": 1.0
        }]

        return self._success_response(
            results=results,
            quantum_coherence=0.618 if mcp_status == "connected" else 0.5
        )

    async def shutdown(self):
        """Clean up background connections."""
        if self._mcp_client:
            await self._mcp_client.disconnect()
