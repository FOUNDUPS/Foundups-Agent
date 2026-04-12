import pytest
from unittest.mock import AsyncMock, patch
from holo_index.foundup_adapter.bridge_stub import HoloIndexBridgeAdapter

@pytest.fixture
def adapter():
    return HoloIndexBridgeAdapter(use_mcp_client=False)

@pytest.mark.asyncio
async def test_metadata_shape(adapter):
    result = await adapter.get_metadata()
    assert result["foundup_id"] == "holoindex_prod_01"
    assert result["name"] == "HoloIndex"
    assert "version" in result

@pytest.mark.asyncio
async def test_status_online(adapter):
    result = await adapter.get_status()
    assert result["status"] == "online"
    assert result["indexer_health"] == "ok"

@pytest.mark.asyncio
async def test_tasks_list(adapter):
    result = await adapter.get_tasks()
    assert "semantic_search" in result
    assert "wsp_lookup" in result
    assert "health" in result

@pytest.mark.asyncio
async def test_unsupported_action(adapter):
    result = await adapter.handle_agent_request({"action": "unknown_action"})
    assert result["type"] == "agent_response"
    assert result["status"] == "error"
    assert "Unsupported action" in result["error"]

@pytest.mark.asyncio
async def test_health_action(adapter):
    result = await adapter.handle_agent_request({"action": "health"})
    assert result["type"] == "agent_response"
    assert result["status"] == "success"
    assert "results" in result["data"]
    assert len(result["data"]["results"]) == 1
    assert result["data"]["results"][0]["status"] == "online"
    assert result["data"]["quantum_coherence"] == 1.0

@pytest.mark.asyncio
@patch.object(HoloIndexBridgeAdapter, 'get_mcp_client')
async def test_semantic_search_mapping(mock_get_mcp, adapter):
    # Mocking the MCP client return shape
    mock_client = AsyncMock()
    mock_client.semantic_code_search.return_value = {
        "code_results": [{"path": "/foo.py", "content": "bar"}],
        "quantum_coherence": 0.85
    }
    mock_get_mcp.return_value = mock_client
    
    result = await adapter.handle_agent_request({
        "action": "semantic_search",
        "query": "test query",
        "limit": 1
    })
    
    assert result["type"] == "agent_response"
    assert result["status"] == "success"
    data = result["data"]
    assert "results" in data
    assert len(data["results"]) == 1
    assert data["results"][0]["path"] == "/foo.py"
    assert data["quantum_coherence"] == 0.85

@pytest.mark.asyncio
@patch.object(HoloIndexBridgeAdapter, 'get_mcp_client')
async def test_wsp_lookup_mapping(mock_get_mcp, adapter):
    # Mocking the MCP client return shape
    mock_client = AsyncMock()
    mock_client.wsp_protocol_lookup.return_value = {
        "protocol_number": "97",
        "content": "WSP 97 Protocol",
        "quantum_coherence": 0.99
    }
    mock_get_mcp.return_value = mock_client
    
    result = await adapter.handle_agent_request({
        "action": "wsp_lookup",
        "protocol_number": "97"
    })
    
    assert result["type"] == "agent_response"
    assert result["status"] == "success"
    data = result["data"]
    assert "results" in data
    assert len(data["results"]) == 1
    assert data["results"][0]["protocol_number"] == "97"
    assert data["quantum_coherence"] == 0.99
