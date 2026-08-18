"""
Tests for FoundUps MCP Bridge FastMCP SSE Server.
=================================================

WSP References:
- WSP 96: Model Context Protocol Governance and Consensus
- WSP 97: Truthful Verification (explicit perception boundary & protocol canary)
- WSP 34: Test Coverage Standards
"""

import asyncio
import json
import pytest
import time
import urllib.error
import urllib.request
from pathlib import Path

# FastMCP may only be installed in foundups-mcp-env
pytest.importorskip("fastmcp")

from modules.infrastructure.foundups_mcp_bridge.src.mcp_server import (
    REMOTE_READ_ONLY_ALLOWLIST,
    build_mcp_server,
    build_asgi_app,
    get_original_function,
)
from modules.infrastructure.foundups_mcp_bridge.scripts.launch import (
    FORBIDDEN_CANARY_TOOLS,
    REQUIRED_CANARY_TOOLS,
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
    """Test FastMCP SSE server, read-only boundary, and authentication lifecycle."""

    def test_mcp_server_registers_only_allowlisted_read_tools(self, mcp_server):
        """Verify only allowlisted read-only tools are registered (33 tools)."""
        tools = asyncio.run(mcp_server.get_tools())
        tool_names = set(tools.keys())

        for allowlisted_tool in REMOTE_READ_ONLY_ALLOWLIST:
            assert allowlisted_tool in tool_names, f"Expected allowlisted tool {allowlisted_tool} to be registered"

        assert len(tools) == len(REMOTE_READ_ONLY_ALLOWLIST)

    def test_mutation_and_dispatch_tools_are_completely_absent(self, mcp_server):
        """
        P0 Security Boundary:
        Verify mutation/execution tools are strictly ABSENT from remote registration
        (not merely returning disabled_in_v1).
        """
        tools = asyncio.run(mcp_server.get_tools())
        tool_names = set(tools.keys())

        disallowed = [
            "coordinate_mission",
            "spawn_agent_team",
            "trigger_skill",
            "write_file",
            "create_branch",
            "create_pr",
        ]
        for forbidden in disallowed:
            assert forbidden not in tool_names, f"P0 Violation: Disallowed tool {forbidden} must not be exposed remotely"

    def test_tool_signatures_exclude_repo_root(self, mcp_server):
        """Verify repo_root is stripped from tool input schema."""
        tree_tool = asyncio.run(mcp_server.get_tool("get_repo_tree"))
        mcp_tree = tree_tool.to_mcp_tool()
        properties = mcp_tree.inputSchema.get("properties", {})
        assert "repo_root" not in properties
        assert "path" in properties
        assert "depth" in properties

    def test_tool_execution_through_fastmcp(self, mcp_server):
        """Verify executing read tool through FastMCP returns bridge result."""
        wsp_tool = asyncio.run(mcp_server.get_tool("get_wsp_docs"))
        result = wsp_tool.fn()
        assert isinstance(result, dict)
        assert result.get("status") == "ok"
        assert "wsp_docs" in result.get("data", {})

    def test_reddog_state_and_analysis_context(self, mcp_server):
        """Verify get_reddog_state and get_reddog_analysis_context through FastMCP."""
        state_tool = asyncio.run(mcp_server.get_tool("get_reddog_state"))
        state_res = state_tool.fn()
        assert isinstance(state_res, dict)
        assert state_res.get("status") == "ok"
        assert "git" in state_res.get("data", {})

        analyze_tool = asyncio.run(mcp_server.get_tool("get_reddog_analysis_context"))
        analyze_res = analyze_tool.fn(prompt="Verify RedDog live context perception")
        assert isinstance(analyze_res, dict)
        assert analyze_res.get("status") == "ok"
        assert analyze_res.get("meta", {}).get("source") == "reddog_context"
        assert "git_state" in analyze_res.get("data", {})

    def test_mcp_bridge_status_query(self):
        """Verify get_mcp_bridge_status returns dictionary."""
        status = get_mcp_bridge_status()
        assert isinstance(status, dict)
        assert "status" in status

    def test_protocol_readiness_canary_auth_and_concurrency_lifecycle(self, repo_root):
        """
        Test full start -> protocol canary handshake -> auth enforcement -> concurrency stop.
        """
        auth_token = "test-secret-token-123"
        port = 8139

        start_res = run_mcp_bridge_sse(
            host="127.0.0.1",
            port=port,
            auth_token=auth_token,
            require_auth=True,
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
            require_auth=True,
            repo_root=repo_root,
            blocking=False,
        )
        assert dup_res.get("status") == "running"
        assert dup_res.get("already_running") is True

        # 1. Unauthenticated request to /sse -> 401
        try:
            req = urllib.request.Request(f"http://127.0.0.1:{port}/sse")
            urllib.request.urlopen(req, timeout=2.0)
            pytest.fail("Unauthenticated request should have failed with 401")
        except urllib.error.HTTPError as exc:
            assert exc.code == 401

        # 2. URL query token (?token=...) MUST BE REJECTED with 401 (P0: prevent secret logging)
        try:
            req = urllib.request.Request(f"http://127.0.0.1:{port}/sse?token={auth_token}")
            urllib.request.urlopen(req, timeout=2.0)
            pytest.fail("URL query token request should have failed with 401 (Bearer header required)")
        except urllib.error.HTTPError as exc:
            assert exc.code == 401

        # 3. Unauthenticated request to /health -> 200 with auth_required: True
        health_req = urllib.request.Request(f"http://127.0.0.1:{port}/health")
        with urllib.request.urlopen(health_req, timeout=2.0) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode())
            assert data.get("status") == "ok"
            assert data.get("auth_required") is True
            assert data.get("tool_count") == len(REMOTE_READ_ONLY_ALLOWLIST)

        # 4. Authenticated protocol readiness canary
        canary = verify_mcp_readiness(
            host="127.0.0.1",
            port=port,
            auth_token=auth_token,
            timeout_sec=5.0,
        )
        assert canary.get("verified") is True
        assert canary.get("tools_count", 0) == len(REMOTE_READ_ONLY_ALLOWLIST)

        # 5. Stop server cleanly
        stop_res = stop_mcp_bridge_sse()
        assert stop_res.get("status") == "stopped"

        # 6. Verify idempotency of stop
        second_stop = stop_mcp_bridge_sse()
        assert second_stop.get("status") == "already_stopped"


class TestMCPServerFailureBoundaries:
    """Test fail-closed security and canary error rejection boundaries."""

    def test_fail_closed_without_token_when_auth_required(self, repo_root):
        """P0 Security: Server refuses to start without auth token when auth is required."""
        res = run_mcp_bridge_sse(
            host="127.0.0.1",
            port=8141,
            auth_token="",
            require_auth=True,
            repo_root=repo_root,
            blocking=False,
        )
        assert res.get("status") == "error"
        assert res.get("error") == "auth_token_required_for_remote_exposure"

    def test_canary_rejects_unauthenticated_connection(self, repo_root):
        """P1 Verification: Protocol canary fails closed if unauthorized."""
        auth_token = "valid-secret-token"
        port = 8142

        start_res = run_mcp_bridge_sse(
            host="127.0.0.1",
            port=port,
            auth_token=auth_token,
            require_auth=True,
            repo_root=repo_root,
            blocking=False,
        )
        assert start_res.get("status") == "running"

        try:
            # Canary with wrong token should fail
            bad_canary = verify_mcp_readiness(
                host="127.0.0.1",
                port=port,
                auth_token="wrong-token",
                timeout_sec=2.0,
            )
            assert bad_canary.get("verified") is False
            assert "401" in bad_canary.get("error", "") or "Failed to establish" in bad_canary.get("error", "")
        finally:
            stop_mcp_bridge_sse()
