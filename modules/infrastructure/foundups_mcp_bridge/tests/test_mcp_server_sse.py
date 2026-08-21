"""
Tests for FoundUps MCP Bridge FastMCP HTTP Server.
==================================================

WSP References:
- WSP 96: Model Context Protocol Governance and Consensus
- WSP 97: Truthful Verification (explicit perception boundary & protocol canary)
- WSP 34: Test Coverage Standards
"""

import asyncio
import json
import pytest
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import MagicMock

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
    MCPRuntimeHandle,
    _terminate_runtime,
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


def registered_tool_names(server):
    """Project registered names across the supported FastMCP 2/3 APIs."""
    if hasattr(server, "list_tools"):
        tools = asyncio.run(server.list_tools())
        return {tool.name for tool in tools}
    tools = asyncio.run(server.get_tools())
    return set(tools)


class TestMCPServerSSE:
    """Test canonical HTTP server plus deprecated launcher-name compatibility."""

    def test_mcp_server_registers_only_allowlisted_read_tools(self, mcp_server):
        """Verify only the current transitive-safe allowlist is registered."""
        tool_names = registered_tool_names(mcp_server)

        for allowlisted_tool in REMOTE_READ_ONLY_ALLOWLIST:
            assert allowlisted_tool in tool_names, f"Expected allowlisted tool {allowlisted_tool} to be registered"

        assert len(tool_names) == len(REMOTE_READ_ONLY_ALLOWLIST)
        assert "holo_query_bundle" in tool_names
        assert not tool_names.intersection({
            "holo_search", "holo_related", "holo_failure_memory",
            "holo_pattern_search", "holo_task_packet", "search_repo",
            "get_recent_changes", "get_file_diff", "get_diff_summary",
            "get_change_impact_score", "get_reddog_state",
            "get_reddog_analysis_context", "get_overseer_summary",
            "get_hot_modules", "get_repeated_failures", "get_active_risks",
            "get_recommended_focus", "get_prompt_context_packet",
        })

    def test_remote_tools_have_conservative_annotations(self, mcp_server):
        for name in REMOTE_READ_ONLY_ALLOWLIST:
            tool = asyncio.run(mcp_server.get_tool(name)).to_mcp_tool()
            assert tool.annotations.readOnlyHint is True
            assert tool.annotations.destructiveHint is False
            assert tool.annotations.idempotentHint is True
            assert tool.annotations.openWorldHint is False

    def test_mutation_and_dispatch_tools_are_completely_absent(self, mcp_server):
        """
        P0 Security Boundary:
        Verify mutation/execution tools are strictly ABSENT from remote registration
        (not merely returning disabled_in_v1).
        """
        tool_names = registered_tool_names(mcp_server)

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
        holo = asyncio.run(mcp_server.get_tool("holo_query_bundle")).to_mcp_tool()
        schema = holo.inputSchema["properties"]
        assert "repo_root" not in schema
        assert schema["query"]["minLength"] == 1
        assert schema["query"]["maxLength"] == 16000
        assert schema["limit"]["minimum"] == 1
        assert schema["limit"]["maximum"] == 20
        assert schema["retrieval_mode"]["enum"] == ["semantic", "lexical"]
        paths = schema["must_include"]["anyOf"][0]
        assert paths["maxItems"] == 40
        assert paths["items"]["maxLength"] == 1024

    def test_local_bridge_tools_are_not_remotely_registered(self, mcp_server):
        """Legacy local perception APIs do not inherit remote authority."""
        assert registered_tool_names(mcp_server) == {"holo_query_bundle"}

    def test_governed_holo_bundle_through_fastmcp(self, mcp_server):
        """Verify the only remotely exposed Holo surface is store-free on canary."""
        tool = asyncio.run(mcp_server.get_tool("holo_query_bundle"))
        response = tool.fn(
            query="WSP memory bundle", limit=1,
            retrieval_mode="lexical", bundle_only=True,
        )
        assert response.get("status") == "ok"
        data = response.get("data", {})
        assert data.get("schema_version") == "reddog_holo_query_bundle_mcp.v1"
        assert data.get("ok") is True
        assert data.get("owner_attempts") == 0
        assert data.get("no_holoindex_reindex_performed") is True
        assert data.get("public_projection_bounded") is True
        assert 0 < data.get("public_projection_bytes", 0) <= 256 * 1024

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

        # 1. Unauthenticated request to canonical /mcp -> 401
        try:
            req = urllib.request.Request(f"http://127.0.0.1:{port}/mcp")
            urllib.request.urlopen(req, timeout=2.0)
            pytest.fail("Unauthenticated request should have failed with 401")
        except urllib.error.HTTPError as exc:
            assert exc.code == 401

        # 2. URL query token (?token=...) MUST BE REJECTED with 401 (P0: prevent secret logging)
        try:
            req = urllib.request.Request(f"http://127.0.0.1:{port}/mcp?token={auth_token}")
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

    def test_build_asgi_app_refuses_empty_token_when_auth_required(self, repo_root):
        """P0 Server Boundary: build_asgi_app raises ValueError if require_auth=True and token is empty."""
        with pytest.raises(ValueError, match="auth_token is required when require_auth=True"):
            build_asgi_app(repo_root=repo_root, auth_token="", require_auth=True)

        with pytest.raises(ValueError, match="auth_token is required when require_auth=True"):
            build_asgi_app(repo_root=repo_root, auth_token="   ", require_auth=True)

    def test_build_asgi_app_is_loopback_only(self, repo_root):
        with pytest.raises(ValueError, match="loopback-only"):
            build_asgi_app(
                repo_root=repo_root, auth_token="dev-token",
                require_auth=False, host="0.0.0.0",
            )

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

    def test_failed_termination_retains_runtime_and_lock(self):
        """P0 Concurrency: If termination times out, _terminate_runtime retains lock and returns failure."""
        mock_lock = MagicMock()
        mock_thread = MagicMock()
        mock_thread.is_alive.return_value = True  # Simulates thread hanging

        handle = MCPRuntimeHandle(
            mode="in_process",
            host="127.0.0.1",
            port=8999,
            started_at=time.time(),
            lock=mock_lock,
            server=MagicMock(),
            thread=mock_thread,
        )

        success, err = _terminate_runtime(handle, timeout_sec=0.1)
        assert success is False
        assert err == "stop_timeout_still_running"
        # Verify lock was NOT released
        mock_lock.release.assert_not_called()
        assert handle.lock is not None
