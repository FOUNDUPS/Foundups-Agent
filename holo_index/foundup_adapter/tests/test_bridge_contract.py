"""
Tests for HoloIndex FoundUp Bridge Contract

Verifies request/response shapes match EXTERNAL_FOUNDUP_BRIDGE_CONTRACT.md

WSP References: WSP 15, WSP 97, WSP 5 (Test Coverage)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from holo_index.foundup_adapter.bridge_stub import (
    HoloIndexBridgeAdapter,
    validate_agent_request,
    BridgeResult,
    BridgeResponseData,
)


class TestRequestValidation:
    """Test request validation per bridge contract Section 2."""

    def test_validate_missing_action(self):
        """Reject payloads without action field."""
        result = validate_agent_request({})
        assert result == "missing required field: action"

    def test_validate_semantic_search_missing_query(self):
        """semantic_search requires query field."""
        result = validate_agent_request({"action": "semantic_search"})
        assert result == "semantic_search requires 'query' field"

    def test_validate_semantic_search_valid(self):
        """Valid semantic_search payload passes."""
        result = validate_agent_request({
            "action": "semantic_search",
            "query": "WSP 97",
            "limit": 5
        })
        assert result is None

    def test_validate_wsp_lookup_missing_protocol(self):
        """wsp_lookup requires protocol_number field."""
        result = validate_agent_request({"action": "wsp_lookup"})
        assert result == "wsp_lookup requires 'protocol_number' field"

    def test_validate_wsp_lookup_valid(self):
        """Valid wsp_lookup payload passes."""
        result = validate_agent_request({
            "action": "wsp_lookup",
            "protocol_number": "97"
        })
        assert result is None

    def test_validate_health_valid(self):
        """Health check needs no additional fields."""
        result = validate_agent_request({"action": "health"})
        assert result is None

    def test_validate_unknown_action(self):
        """Reject unknown actions."""
        result = validate_agent_request({"action": "unknown_action"})
        assert "unknown action" in result


class TestResponseShapes:
    """Test response shapes per bridge contract Section 3."""

    @pytest.fixture
    def adapter(self):
        """Create adapter with MCP disabled for unit testing."""
        return HoloIndexBridgeAdapter(use_mcp_client=False)

    def test_error_response_shape(self, adapter):
        """Error response matches contract structure."""
        response = adapter._error_response("test error")

        assert response["type"] == "agent_response"
        assert response["status"] == "error"
        assert "data" in response
        assert response["data"]["error"] == "test error"

    def test_success_response_shape(self, adapter):
        """Success response matches contract Section 3.1."""
        results = [{"content": "test", "path": "/test.py", "relevance": 0.9}]
        response = adapter._success_response(results, quantum_coherence=0.8)

        assert response["type"] == "agent_response"
        assert response["status"] == "success"
        assert "data" in response
        assert "results" in response["data"]
        assert "quantum_coherence" in response["data"]
        assert response["data"]["quantum_coherence"] == 0.8
        assert len(response["data"]["results"]) == 1

    def test_success_response_stub_marker(self, adapter):
        """Stub marker included when specified."""
        response = adapter._success_response([], stub=True)

        assert response["data"]["stub"] is True


class TestAdapterActions:
    """Test adapter action handlers."""

    @pytest.fixture
    def adapter(self):
        """Create adapter with MCP disabled."""
        return HoloIndexBridgeAdapter(use_mcp_client=False)

    @pytest.mark.asyncio
    async def test_handle_invalid_request(self, adapter):
        """Invalid request returns error response."""
        response = await adapter.handle_agent_request({})

        assert response["status"] == "error"
        assert "missing required field" in response["data"]["error"]

    @pytest.mark.asyncio
    async def test_handle_health_no_mcp(self, adapter):
        """Health check works without MCP client."""
        response = await adapter.handle_agent_request({"action": "health"})

        assert response["type"] == "agent_response"
        assert response["status"] == "success"
        assert "results" in response["data"]
        assert len(response["data"]["results"]) == 1
        assert "/f/holoindex/status" in response["data"]["results"][0]["path"]

    @pytest.mark.asyncio
    async def test_handle_search_no_mcp(self, adapter):
        """Semantic search without MCP returns error."""
        response = await adapter.handle_agent_request({
            "action": "semantic_search",
            "query": "test query"
        })

        assert response["status"] == "error"
        assert "not available" in response["data"]["error"]

    @pytest.mark.asyncio
    async def test_handle_wsp_lookup_no_mcp(self, adapter):
        """WSP lookup without MCP returns error."""
        response = await adapter.handle_agent_request({
            "action": "wsp_lookup",
            "protocol_number": "97"
        })

        assert response["status"] == "error"
        assert "not available" in response["data"]["error"]


class TestAdapterWithMCP:
    """Test adapter with mocked MCP client."""

    @pytest.fixture
    def mock_mcp_client(self):
        """Create mock MCP client."""
        client = AsyncMock()
        client.semantic_code_search = AsyncMock(return_value={
            "code_results": [
                {"content": "def foo():", "path": "/test.py", "score": 0.95}
            ],
            "quantum_coherence": 0.8
        })
        client.wsp_protocol_lookup = AsyncMock(return_value={
            "protocol_number": "97",
            "title": "WSP 97",
            "content": "Test protocol content",
            "path": "WSP_framework/src/WSP_97.md",
            "quantum_coherence": 0.85
        })
        return client

    @pytest.fixture
    def adapter_with_mcp(self, mock_mcp_client):
        """Create adapter with mock MCP client."""
        adapter = HoloIndexBridgeAdapter(use_mcp_client=True)
        adapter._mcp_client = mock_mcp_client
        return adapter

    @pytest.mark.asyncio
    async def test_search_transforms_mcp_result(self, adapter_with_mcp):
        """Semantic search transforms MCP results to bridge contract shape."""
        response = await adapter_with_mcp.handle_agent_request({
            "action": "semantic_search",
            "query": "test query",
            "limit": 5
        })

        assert response["status"] == "success"
        assert "results" in response["data"]
        assert response["data"]["quantum_coherence"] == 0.8
        result = response["data"]["results"][0]
        assert "content" in result
        assert "path" in result
        assert "relevance" in result

    @pytest.mark.asyncio
    async def test_wsp_lookup_transforms_mcp_result(self, adapter_with_mcp):
        """WSP lookup transforms MCP results to bridge contract shape."""
        response = await adapter_with_mcp.handle_agent_request({
            "action": "wsp_lookup",
            "protocol_number": "97"
        })

        assert response["status"] == "success"
        assert "results" in response["data"]
        result = response["data"]["results"][0]
        assert "content" in result
        assert "path" in result
        assert "protocol" in result
        assert result["protocol"] == "97"


class TestMetadataEndpoints:
    """Test metadata/status/tasks endpoints per bridge contract Section 4."""

    @pytest.fixture
    def adapter(self):
        return HoloIndexBridgeAdapter(use_mcp_client=False)

    @pytest.mark.asyncio
    async def test_get_metadata(self, adapter):
        """GET /metadata returns FoundUp identity."""
        metadata = await adapter.get_metadata()

        assert metadata["foundup_id"] == "holoindex_prod_01"
        assert metadata["name"] == "HoloIndex"
        assert "version" in metadata
        assert "lifecycle_stage" in metadata

    @pytest.mark.asyncio
    async def test_get_status(self, adapter):
        """GET /status returns health information."""
        status = await adapter.get_status()

        assert "status" in status
        assert "mode" in status
        assert status["mode"] == "embedded"  # No MCP configured

    @pytest.mark.asyncio
    async def test_get_tasks(self, adapter):
        """GET /tasks returns capability list."""
        tasks = await adapter.get_tasks()

        assert isinstance(tasks, list)
        assert "semantic_search" in tasks
        assert "wsp_lookup" in tasks


class TestBridgeDataClasses:
    """Test bridge contract data classes."""

    def test_bridge_result(self):
        """BridgeResult captures search result shape."""
        result = BridgeResult(
            content="def test():",
            path="/test.py",
            relevance=0.95
        )
        assert result.content == "def test():"
        assert result.path == "/test.py"
        assert result.relevance == 0.95

    def test_bridge_response_data(self):
        """BridgeResponseData captures response wrapper."""
        data = BridgeResponseData(
            results=[{"content": "test"}],
            quantum_coherence=0.8,
            stub=True
        )
        assert data.quantum_coherence == 0.8
        assert data.stub is True
