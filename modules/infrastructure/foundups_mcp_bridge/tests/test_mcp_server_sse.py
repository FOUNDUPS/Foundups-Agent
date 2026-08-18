"""
Tests for FoundUps MCP Bridge FastMCP SSE Server.
=================================================

WSP References:
- WSP 96: Model Context Protocol Governance and Consensus
- WSP 97: Truthful Verification (perception-only read boundary + protocol canary)
- WSP 34: Test Coverage Standards
"""

import asyncio
import json
import pytest
import time
import urllib.request
from pathlib import Path

# FastMCP may only be installed in foundups-mcp-env
pytest.importorskip("fastmcp")

from modules.infrastructure.foundups_mcp_bridge.src.mcp_server import (
    build_mcp_server,
    build_asgi_app,
    get_original_function,
)
from modules.infrastructure.foundups_mcp_bridge.scripts.launch import (
    get_mcp_bridge_status,
    verify_mcp_readiness,
    run_mcp_bridge_sse,
    stop_mcp_bridge_sse,
)


@pytest.fixture
def repo_root():
    """Get repo root path."""
    return Path(__file__).resolve().parent.parent.parent.parent.parent


@pytest.fixture
def mcp_server(repo_root):
    """Build test FastMCP server instance."""
    return build_mcp_server(repo_root=repo_root)


class TestMCPServerSSE:
    """Test FastMCP SSE server and tool extraction."""

    def test_mcp_server_builds_all_tools(self, mcp_server):
        """Verify all 39 bridge tools are registered on FastMCP."""
        tools = asyncio.run(mcp_server.get_tools())
        assert len(tools) == 39
        assert "get_repo_tree" in tools
        assert "read_file" in tools
        assert "holo_search" in tools
        assert "get_wsp_docs" in tools
        assert "get_overseer_summary" in tools
        assert "coordinate_mission" in tools
        assert "get_reddog_state" in tools
        assert "reddog_analyze" in tools

    def test_tool_signatures_exclude_repo_root(self, mcp_server):
        """Verify repo_root is stripped from tool input schema."""
        tree_tool = asyncio.run(mcp_server.get_tool("get_repo_tree"))
        mcp_tree = tree_tool.to_mcp_tool()
        properties = mcp_tree.inputSchema.get("properties", {})
        assert "repo_root" not in properties
        assert "path" in properties
        assert "depth" in properties

    def test_tool_execution_through_fastmcp(self, mcp_server):
        """Verify executing tool through FastMCP returns bridge result."""
        wsp_tool = asyncio.run(mcp_server.get_tool("get_wsp_docs"))
        result = wsp_tool.fn()
        assert isinstance(result, dict)
        assert result.get("status") == "ok"
        assert "wsp_docs" in result.get("data", {})

    def test_reddog_state_and_analyze_through_fastmcp(self, mcp_server):
        """Verify executing get_reddog_state and reddog_analyze through FastMCP."""
        state_tool = asyncio.run(mcp_server.get_tool("get_reddog_state"))
        state_res = state_tool.fn()
        assert isinstance(state_res, dict)
        assert state_res.get("status") == "ok"
        assert "git" in state_res.get("data", {})

        analyze_tool = asyncio.run(mcp_server.get_tool("reddog_analyze"))
        analyze_res = analyze_tool.fn(prompt="Verify RedDog live perception")
        assert isinstance(analyze_res, dict)
        assert analyze_res.get("status") == "ok"
        assert "git_state" in analyze_res.get("data", {})

    def test_disabled_tool_schema_and_execution(self, mcp_server):
        """Verify disabled stubs return disabled_in_v1 response."""
        stub_tool = asyncio.run(mcp_server.get_tool("coordinate_mission"))
        result = stub_tool.fn(mission_description="Audit WSP")
        assert isinstance(result, dict)
        assert result.get("status") == "disabled_in_v1"

    def test_mcp_bridge_status_query(self):
        """Verify get_mcp_bridge_status returns dictionary."""
        status = get_mcp_bridge_status()
        assert isinstance(status, dict)
        assert "status" in status

    def test_protocol_readiness_canary_and_auth_lifecycle(self, repo_root):
        """Test full start -> protocol canary handshake -> auth enforcement -> stop lifecycle."""
        auth_token = "test-secret-token-123"
        port = 8139

        start_res = run_mcp_bridge_sse(
            host="127.0.0.1",
            port=port,
            auth_token=auth_token,
            repo_root=repo_root,
            blocking=False,
        )
        assert start_res.get("status") == "running"
        assert start_res.get("readiness", {}).get("verified") is True

        # Test duplicate start protection
        dup_res = run_mcp_bridge_sse(
            host="127.0.0.1",
            port=port,
            auth_token=auth_token,
            repo_root=repo_root,
            blocking=False,
        )
        assert dup_res.get("status") == "running"
        assert dup_res.get("already_running") is True

        # Test unauthenticated request to /sse -> 401
        try:
            req = urllib.request.Request(f"http://127.0.0.1:{port}/sse")
            urllib.request.urlopen(req, timeout=2.0)
            pytest.fail("Unauthenticated request should have failed with 401")
        except urllib.error.HTTPError as exc:
            assert exc.code == 401

        # Test unauthenticated request to /health -> 200
        health_req = urllib.request.Request(f"http://127.0.0.1:{port}/health")
        with urllib.request.urlopen(health_req, timeout=2.0) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode())
            assert data.get("status") == "ok"
            assert data.get("auth_required") is True

        # Test authenticated protocol readiness
        canary = verify_mcp_readiness(
            host="127.0.0.1",
            port=port,
            auth_token=auth_token,
            timeout_sec=5.0,
        )
        assert canary.get("verified") is True
        assert canary.get("tools_count", 0) >= 30

        # Stop server cleanly
        stop_res = stop_mcp_bridge_sse()
        assert stop_res.get("status") == "stopped"

        # Verify idempotency of stop
        second_stop = stop_mcp_bridge_sse()
        assert second_stop.get("status") == "already_stopped"
