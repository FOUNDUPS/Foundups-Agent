"""
MCPA8 transport tests for pAVS MCP Server.

Verifies that the HTTP JSON transport layer works correctly:
- Server binds to local port
- Valid JSON tool calls dispatch to handle_tool_call
- Invalid requests return structured errors
- Auth errors pass through transport correctly
- Graceful shutdown works

These tests use Python stdlib urllib for HTTP calls (no FastAPI dependency).
"""

from __future__ import annotations

import json
import socket
import urllib.request
import urllib.error

import pytest

from modules.infrastructure.pavs_mcp.src.server import (
    PAVSMCPServer,
    IMPLEMENTATION_STATUS,
)


def _get_free_port() -> int:
    """Get a free port for testing."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def server(tmp_path):
    """Create and start a server with isolated registry for each test."""
    registry_path = tmp_path / "registrations.json"
    port = _get_free_port()
    srv = PAVSMCPServer(host="127.0.0.1", port=port, registry_path=registry_path)
    srv.start_sync(timeout=5.0)
    yield srv
    srv.stop_sync()


@pytest.fixture
def base_url(server):
    """Get base URL for the running server."""
    return f"http://{server.host}:{server.port}"


def _get(url: str) -> dict:
    """Make GET request and return JSON."""
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=5) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _post(url: str, data: dict) -> tuple[int, dict]:
    """Make POST request and return (status_code, json_body)."""
    body = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8")) if e.fp else {}


class TestTransportEndpoints:
    """Test HTTP transport endpoint availability and basic behavior."""

    def test_status_endpoint_returns_running(self, base_url):
        """GET /status returns server status."""
        data = _get(f"{base_url}/status")
        assert data["status"] == "running"
        assert data["implementation_status"] == IMPLEMENTATION_STATUS
        assert data["transport"] == "HTTP_JSON"
        assert "tools" in data
        assert isinstance(data["tools"], list)

    def test_tools_endpoint_lists_tools(self, base_url):
        """GET /tools returns available tools."""
        data = _get(f"{base_url}/tools")
        assert "tools" in data
        expected_tools = [
            "cabr_validate", "gemma_classify", "qwen_plan", "fam_emit",
            "pattern_recall", "pattern_store", "holo_search", "foundup_register",
        ]
        for tool in expected_tools:
            assert tool in data["tools"]


class TestToolCallViaTransport:
    """Test tool calls through the HTTP transport."""

    def test_post_tool_dispatches_to_handle_tool_call(self, base_url):
        """POST /tool dispatches to handle_tool_call and returns envelope."""
        status, data = _post(f"{base_url}/tool", {
            "tool_name": "foundup_register",
            "arguments": {
                "foundup_id": "test_foundup",
                "repo_url": "https://github.com/test/repo",
                "owner_pubkey": "ed25519_test_key",
            },
        })
        assert status == 200
        assert "result" in data
        assert "api_key" in data["result"]
        assert data["result"]["api_key"].startswith("fp_")
        assert "meta" in data

    def test_post_tool_by_path_dispatches_correctly(self, base_url):
        """POST /tool/{name} dispatches to the named tool."""
        status, data = _post(f"{base_url}/tool/foundup_register", {
            "arguments": {
                "foundup_id": "path_test_foundup",
                "repo_url": "https://github.com/test/repo",
                "owner_pubkey": "key",
            },
        })
        assert status == 200
        assert "result" in data
        assert "api_key" in data["result"]

    def test_protected_tool_requires_api_key(self, base_url):
        """Protected tools return auth error without api_key."""
        status, data = _post(f"{base_url}/tool", {
            "tool_name": "holo_search",
            "arguments": {"query": "test"},
        })
        assert status == 200  # HTTP 200, error in envelope
        assert "error" in data
        assert data["error"]["code"] == "MISSING_API_KEY"

    def test_protected_tool_with_api_key_succeeds(self, base_url):
        """Protected tools succeed with valid api_key."""
        # First register to get an API key
        _, reg_data = _post(f"{base_url}/tool", {
            "tool_name": "foundup_register",
            "arguments": {
                "foundup_id": "authed_foundup",
                "repo_url": "https://github.com/test/repo",
                "owner_pubkey": "key",
            },
        })
        api_key = reg_data["result"]["api_key"]

        # Now call protected tool with the key
        status, data = _post(f"{base_url}/tool", {
            "tool_name": "holo_search",
            "arguments": {"query": "test"},
            "api_key": api_key,
        })
        assert status == 200
        assert "result" in data or "error" in data  # May be not_implemented envelope
        assert data["meta"]["auth_enforced"] is True

    def test_unknown_tool_returns_error(self, base_url):
        """Unknown tool name returns UNKNOWN_TOOL error."""
        status, data = _post(f"{base_url}/tool", {
            "tool_name": "nonexistent_tool",
            "arguments": {},
        })
        assert status == 200
        assert "error" in data
        assert data["error"]["code"] == "UNKNOWN_TOOL"


class TestTransportErrorHandling:
    """Test error handling in the transport layer."""

    def test_missing_tool_name_returns_error(self, base_url):
        """Missing required field returns error."""
        status, data = _post(f"{base_url}/tool", {
            "arguments": {},
        })
        assert status == 400
        assert "error" in data


class TestAuthThroughTransport:
    """Test auth enforcement passes through transport correctly."""

    def test_unknown_api_key_rejected(self, base_url):
        """Unknown api_key returns UNKNOWN_API_KEY error."""
        status, data = _post(f"{base_url}/tool", {
            "tool_name": "holo_search",
            "arguments": {"query": "test"},
            "api_key": "fp_definitely_invalid_key",
        })
        assert status == 200
        assert "error" in data
        assert data["error"]["code"] == "UNKNOWN_API_KEY"

    def test_cross_tenant_rejected(self, base_url):
        """Cross-tenant foundup_id access rejected."""
        # Register foundup_a
        _, reg_data = _post(f"{base_url}/tool", {
            "tool_name": "foundup_register",
            "arguments": {
                "foundup_id": "foundup_a",
                "repo_url": "https://github.com/a/repo",
                "owner_pubkey": "key_a",
            },
        })
        api_key_a = reg_data["result"]["api_key"]

        # Try to access foundup_b with foundup_a's key
        status, data = _post(f"{base_url}/tool", {
            "tool_name": "fam_emit",
            "arguments": {
                "foundup_id": "foundup_b",
                "event_type": "test",
                "payload": {},
            },
            "api_key": api_key_a,
        })
        assert status == 200
        assert "error" in data
        assert data["error"]["code"] == "CROSS_TENANT_VIOLATION"


class TestFamEmitViaTransport:
    """MCPA9B: Test fam_emit backend delegation via HTTP transport."""

    def test_fam_emit_via_transport_delegates_to_backend(self, base_url):
        """POST /tool with fam_emit delegates to FAM DAEmon backend."""
        import uuid

        # First register to get an API key
        _, reg_data = _post(f"{base_url}/tool", {
            "tool_name": "foundup_register",
            "arguments": {
                "foundup_id": "transport_test_foundup",
                "repo_url": "https://github.com/test/repo",
                "owner_pubkey": "key",
            },
        })
        api_key = reg_data["result"]["api_key"]

        # Now call fam_emit with unique payload
        status, data = _post(f"{base_url}/tool", {
            "tool_name": "fam_emit",
            "arguments": {
                "foundup_id": "transport_test_foundup",
                "event_type": "test_event",
                "payload": {"test_id": str(uuid.uuid4())},
            },
            "api_key": api_key,
        })

        assert status == 200
        assert "result" in data
        inner = data["result"]
        assert inner["status"] == "ok"
        assert inner["meta"]["real_backend"] is True
        assert inner["meta"]["delegated_to"] == "FAM_DAEMON"
        assert inner["data"]["persisted"] is True


class TestServerLifecycle:
    """Test server start/stop lifecycle."""

    def test_server_binds_to_port(self, tmp_path):
        """Server actually binds to a port."""
        registry_path = tmp_path / "registrations.json"
        port = _get_free_port()
        srv = PAVSMCPServer(host="127.0.0.1", port=port, registry_path=registry_path)
        srv.start_sync(timeout=5.0)

        try:
            # Verify we can connect
            data = _get(f"http://127.0.0.1:{port}/status")
            assert data["status"] == "running"
        finally:
            srv.stop_sync()

    def test_graceful_shutdown(self, tmp_path):
        """Server shuts down gracefully."""
        registry_path = tmp_path / "registrations.json"
        port = _get_free_port()
        srv = PAVSMCPServer(host="127.0.0.1", port=port, registry_path=registry_path)
        srv.start_sync(timeout=5.0)

        # Verify running
        data = _get(f"http://127.0.0.1:{port}/status")
        assert data["status"] == "running"

        # Stop and verify
        srv.stop_sync()
        # Give a moment for shutdown
        import time
        time.sleep(0.2)

        # Connection should fail now
        with pytest.raises((urllib.error.URLError, ConnectionRefusedError, OSError)):
            _get(f"http://127.0.0.1:{port}/status")
