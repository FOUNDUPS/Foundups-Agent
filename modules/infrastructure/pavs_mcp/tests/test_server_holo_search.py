# -*- coding: utf-8 -*-
"""
Tests for pAVS MCP Server holo_search tool.

HIA Phase 5: Verifies foundup_id/include_shared params are accepted
and echoed in placeholder response.

WSP 97: Tests verify truthful placeholder behavior.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from modules.infrastructure.pavs_mcp.src.server import PAVSMCPServer


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def server():
    """Create pAVS MCP server instance."""
    return PAVSMCPServer()


# =============================================================================
# holo_search Signature Tests
# =============================================================================


class TestHoloSearchSignature:
    """Test holo_search accepts HIA Phase 5 params."""

    @pytest.mark.asyncio
    async def test_basic_search(self, server):
        """holo_search returns placeholder matches."""
        result = await server.holo_search(query="test query")
        assert "matches" in result
        assert len(result["matches"]) > 0

    @pytest.mark.asyncio
    async def test_with_domain(self, server):
        """holo_search accepts domain param."""
        result = await server.holo_search(query="test", domain="code")
        assert "matches" in result

    @pytest.mark.asyncio
    async def test_with_limit(self, server):
        """holo_search accepts limit param."""
        result = await server.holo_search(query="test", limit=5)
        assert "matches" in result

    @pytest.mark.asyncio
    async def test_with_foundup_id(self, server):
        """holo_search accepts foundup_id param (HIA Phase 5)."""
        result = await server.holo_search(
            query="test",
            foundup_id="trade",
        )
        assert "matches" in result
        assert "scope" in result
        assert result["scope"]["foundup_id"] == "trade"

    @pytest.mark.asyncio
    async def test_with_include_shared_false(self, server):
        """holo_search accepts include_shared=False (HIA Phase 5)."""
        result = await server.holo_search(
            query="test",
            foundup_id="kosei",
            include_shared=False,
        )
        assert "matches" in result
        assert "scope" in result
        assert result["scope"]["foundup_id"] == "kosei"
        assert result["scope"]["include_shared"] is False

    @pytest.mark.asyncio
    async def test_with_all_params(self, server):
        """holo_search accepts all params together."""
        result = await server.holo_search(
            query="WSP protocol",
            domain="wsp",
            limit=10,
            foundup_id="gotjunk_001",
            include_shared=True,
        )
        assert "matches" in result
        assert "scope" in result
        assert result["scope"]["foundup_id"] == "gotjunk_001"
        assert result["scope"]["include_shared"] is True
        assert result["scope"]["domain"] == "wsp"


# =============================================================================
# Placeholder Truthfulness Tests (WSP 97)
# =============================================================================


class TestPlaceholderTruthfulness:
    """Test that placeholder response is truthful per WSP 97."""

    @pytest.mark.asyncio
    async def test_placeholder_flag_present(self, server):
        """Response includes _placeholder=True flag."""
        result = await server.holo_search(query="test")
        assert result.get("_placeholder") is True

    @pytest.mark.asyncio
    async def test_note_explains_not_live(self, server):
        """Response includes explanatory note."""
        result = await server.holo_search(query="test")
        assert "_note" in result
        assert "placeholder" in result["_note"].lower() or "not connected" in result["_note"].lower()

    @pytest.mark.asyncio
    async def test_scope_not_applied_note(self, server):
        """Response notes that scope is not applied."""
        result = await server.holo_search(query="test", foundup_id="trade")
        assert "_note" in result
        assert "not applied" in result["_note"].lower()


# =============================================================================
# Scope Echo Tests
# =============================================================================


class TestScopeEcho:
    """Test that scope params are echoed in response."""

    @pytest.mark.asyncio
    async def test_scope_echoes_foundup_id(self, server):
        """Scope block echoes foundup_id."""
        result = await server.holo_search(query="test", foundup_id="my_foundup")
        assert result["scope"]["foundup_id"] == "my_foundup"

    @pytest.mark.asyncio
    async def test_scope_echoes_include_shared(self, server):
        """Scope block echoes include_shared."""
        result = await server.holo_search(query="test", include_shared=False)
        assert result["scope"]["include_shared"] is False

    @pytest.mark.asyncio
    async def test_scope_echoes_domain(self, server):
        """Scope block echoes domain."""
        result = await server.holo_search(query="test", domain="docs")
        assert result["scope"]["domain"] == "docs"

    @pytest.mark.asyncio
    async def test_scope_defaults(self, server):
        """Scope block has correct defaults."""
        result = await server.holo_search(query="test")
        assert result["scope"]["foundup_id"] is None
        assert result["scope"]["include_shared"] is True
        assert result["scope"]["domain"] is None


# =============================================================================
# Tool Registration Tests
# =============================================================================


class TestToolRegistration:
    """Test that holo_search is properly registered."""

    def test_holo_search_in_tools(self, server):
        """holo_search is in registered tools."""
        assert "holo_search" in server._tools

    def test_holo_search_callable(self, server):
        """holo_search tool is callable."""
        tool = server._tools["holo_search"]
        assert callable(tool)


# =============================================================================
# handle_tool_call Integration Tests
# =============================================================================


class TestHandleToolCall:
    """Test holo_search via handle_tool_call."""

    @pytest.mark.asyncio
    async def test_handle_holo_search(self, server):
        """handle_tool_call routes to holo_search correctly."""
        result = await server.handle_tool_call(
            tool_name="holo_search",
            arguments={"query": "test"},
        )
        assert "result" in result
        assert "matches" in result["result"]

    @pytest.mark.asyncio
    async def test_handle_holo_search_with_scope(self, server):
        """handle_tool_call passes scope params correctly."""
        result = await server.handle_tool_call(
            tool_name="holo_search",
            arguments={
                "query": "test",
                "foundup_id": "trade",
                "include_shared": False,
            },
        )
        assert "result" in result
        assert result["result"]["scope"]["foundup_id"] == "trade"
        assert result["result"]["scope"]["include_shared"] is False
