"""
Tests for FoundUps MCP Bridge.

Verifies:
- Response schema consistency
- Repo perception tools
- Doc access tools
- Overseer read hooks
- Execution stubs return disabled status
"""

import pytest
from pathlib import Path

from modules.infrastructure.foundups_mcp_bridge.src import (
    FoundUpsMCPBridge,
    ok_response,
    error_response,
    disabled_response,
)


# ==================== Fixtures ====================


@pytest.fixture
def bridge():
    """Create bridge with actual repo root."""
    return FoundUpsMCPBridge()


@pytest.fixture
def repo_root():
    """Get repo root path."""
    return Path(__file__).resolve().parent.parent.parent.parent.parent


# ==================== Response Schema Tests ====================


class TestResponseSchema:
    """Test unified response schema."""

    def test_ok_response_structure(self):
        """ok_response has required fields."""
        result = ok_response({"test": "data"}, source="test")
        assert result["status"] == "ok"
        assert result["data"] == {"test": "data"}
        assert "meta" in result
        assert "timestamp" in result["meta"]
        assert result["meta"]["source"] == "test"

    def test_error_response_structure(self):
        """error_response has required fields."""
        result = error_response("Test error", code=404)
        assert result["status"] == "error"
        assert result["error"] == "Test error"
        assert result["meta"]["code"] == 404

    def test_disabled_response_structure(self):
        """disabled_response has required fields."""
        result = disabled_response("test_tool", schema={"param": "type"})
        assert result["status"] == "disabled_in_v1"
        assert "disabled" in result["error"].lower()
        assert result["data"]["tool"] == "test_tool"
        assert result["data"]["schema"] == {"param": "type"}


# ==================== Bridge Status Tests ====================


class TestBridgeStatus:
    """Test bridge initialization and status."""

    def test_bridge_initialization(self, bridge):
        """Bridge initializes with repo root."""
        assert bridge.repo_root.exists()
        assert bridge.VERSION == "1.1.0"
        assert bridge.MODE == "perception-only"

    def test_get_status(self, bridge):
        """get_status returns valid response."""
        result = bridge.get_status()
        assert result["status"] == "ok"
        assert result["data"]["version"] == "1.1.0"
        assert result["data"]["mode"] == "perception-only"
        assert result["data"]["repo_exists"] is True
        assert result["data"]["capabilities"]["repo_perception"] is True
        assert result["data"]["capabilities"]["execution"] is False

    def test_list_tools(self, bridge):
        """list_tools returns tool listing."""
        result = bridge.list_tools()
        assert result["status"] == "ok"
        assert result["data"]["count"] > 10
        assert result["data"]["active_count"] > 0
        assert result["data"]["disabled_count"] > 0

        # Check tool structure
        tools = result["data"]["tools"]
        assert any(t["name"] == "get_repo_tree" for t in tools)
        assert any(t["name"] == "coordinate_mission" for t in tools)

        # Check status values
        active_tool = next(t for t in tools if t["name"] == "get_repo_tree")
        assert active_tool["status"] == "active"

        disabled_tool = next(t for t in tools if t["name"] == "coordinate_mission")
        assert disabled_tool["status"] == "disabled_in_v1"


# ==================== Repo Perception Tests ====================


class TestRepoTools:
    """Test repo perception tools."""

    def test_get_repo_tree(self, bridge):
        """get_repo_tree returns directory structure."""
        result = bridge.call_tool("get_repo_tree", path=".", depth=1)
        assert result["status"] == "ok"
        assert "name" in result["data"]
        assert "children" in result["data"]
        assert result["meta"]["depth"] == 1

    def test_get_repo_tree_modules(self, bridge):
        """get_repo_tree works on modules directory."""
        result = bridge.call_tool("get_repo_tree", path="modules", depth=2)
        assert result["status"] == "ok"
        # Check for expected domains
        children = result["data"].get("children", [])
        child_names = [c["name"] for c in children]
        assert "infrastructure" in child_names or "ai_intelligence" in child_names

    def test_read_file_exists(self, bridge):
        """read_file returns file content."""
        result = bridge.call_tool("read_file", path="README.md")
        if result["status"] == "ok":
            assert "content" in result["data"]
            assert "lines" in result["data"]

    def test_read_file_blocked_path(self, bridge):
        """read_file blocks sensitive paths."""
        result = bridge.call_tool("read_file", path=".env")
        assert result["status"] == "error"
        assert "not allowed" in result["error"].lower()

    def test_search_repo(self, bridge):
        """search_repo returns matches."""
        result = bridge.call_tool("search_repo", query="WSP", path=".", top_k=5)
        # May fail if ripgrep not installed
        if result["status"] == "ok":
            assert "matches" in result["data"]
            assert "total_found" in result["data"]

    def test_get_recent_changes(self, bridge):
        """get_recent_changes returns commits."""
        result = bridge.call_tool("get_recent_changes", limit=5)
        assert result["status"] == "ok"
        assert "commits" in result["data"]
        assert len(result["data"]["commits"]) <= 5


# ==================== Documentation Tests ====================


class TestDocTools:
    """Test documentation access tools."""

    def test_get_wsp_docs(self, bridge):
        """get_wsp_docs returns WSP listing."""
        result = bridge.call_tool("get_wsp_docs")
        assert result["status"] == "ok"
        assert "wsp_docs" in result["data"]
        assert result["data"]["count"] > 0

    def test_get_module_docs(self, bridge):
        """get_module_docs returns README."""
        result = bridge.call_tool("get_module_docs", module_name="ai_overseer")
        if result["status"] == "ok":
            assert "readme" in result["data"]
            assert result["data"]["module"] == "ai_overseer"

    def test_get_interface_doc(self, bridge):
        """get_interface_doc returns INTERFACE.md."""
        result = bridge.call_tool("get_interface_doc", module_name="ai_overseer")
        if result["status"] == "ok":
            assert "interface" in result["data"]

    def test_get_modlog(self, bridge):
        """get_modlog returns ModLog entries."""
        result = bridge.call_tool("get_modlog", limit=5)
        assert result["status"] == "ok"
        assert "modlogs" in result["data"]

    def test_get_violations(self, bridge):
        """get_violations returns violation records."""
        result = bridge.call_tool("get_violations", limit=10)
        assert result["status"] == "ok"
        assert "violations" in result["data"]


# ==================== Overseer Perception Tests ====================


class TestOverseerTools:
    """Test AI Overseer read hooks."""

    def test_get_mission_history(self, bridge):
        """get_mission_history returns missions."""
        result = bridge.call_tool("get_mission_history", limit=10)
        assert result["status"] == "ok"
        assert "missions" in result["data"]
        assert "sources" in result["data"]

    def test_get_pattern_memory(self, bridge):
        """get_pattern_memory returns patterns."""
        result = bridge.call_tool("get_pattern_memory", limit=20)
        assert result["status"] == "ok"
        assert "patterns" in result["data"]

    def test_get_overseer_status(self, bridge):
        """get_overseer_status returns status."""
        result = bridge.call_tool("get_overseer_status")
        assert result["status"] == "ok"
        assert "available" in result["data"]
        assert "db_exists" in result["data"]

    def test_get_coordination_state(self, bridge):
        """get_coordination_state returns state."""
        result = bridge.call_tool("get_coordination_state")
        assert result["status"] == "ok"
        assert "active_teams" in result["data"]
        assert "recent_phases" in result["data"]

    def test_get_known_failure_patterns(self, bridge):
        """get_known_failure_patterns returns failures."""
        result = bridge.call_tool("get_known_failure_patterns", limit=10)
        assert result["status"] == "ok"
        assert "failures" in result["data"]


# ==================== Dependency Tools Tests ====================


class TestDependencyTools:
    """Test dependency perception tools."""

    def test_get_module_dependencies_valid(self, bridge):
        """get_module_dependencies returns deps for valid module."""
        result = bridge.call_tool("get_module_dependencies", module_name="foundups_mcp_bridge")
        assert result["status"] == "ok"
        assert "module" in result["data"]
        assert "internal_dependencies" in result["data"]
        assert "external_dependencies" in result["data"]
        assert "files_analyzed" in result["data"]

    def test_get_module_dependencies_not_found(self, bridge):
        """get_module_dependencies returns error for nonexistent module."""
        result = bridge.call_tool("get_module_dependencies", module_name="nonexistent_module_xyz")
        assert result["status"] == "error"
        assert "not found" in result["error"].lower()

    def test_get_module_dependencies_with_internal(self, bridge):
        """get_module_dependencies identifies internal deps."""
        # Use a module known to have internal deps
        result = bridge.call_tool("get_module_dependencies", module_name="ai_overseer")
        if result["status"] == "ok":
            assert "internal_dependencies" in result["data"]
            assert isinstance(result["data"]["internal_dependencies"], list)

    def test_get_reverse_dependencies_valid(self, bridge):
        """get_reverse_dependencies returns dependents."""
        # Use a core module that others depend on
        result = bridge.call_tool("get_reverse_dependencies", module_name="shared_utilities")
        assert result["status"] == "ok"
        assert "dependents" in result["data"]
        assert "dependent_count" in result["data"]
        assert "blast_radius" in result["data"]

    def test_get_reverse_dependencies_isolated(self, bridge):
        """get_reverse_dependencies handles isolated module."""
        result = bridge.call_tool("get_reverse_dependencies", module_name="foundups_mcp_bridge")
        assert result["status"] == "ok"
        # New module likely has no dependents
        assert "dependents" in result["data"]
        assert isinstance(result["data"]["dependents"], list)

    def test_get_reverse_dependencies_not_found(self, bridge):
        """get_reverse_dependencies returns error for nonexistent module."""
        result = bridge.call_tool("get_reverse_dependencies", module_name="nonexistent_module_xyz")
        assert result["status"] == "error"
        assert "not found" in result["error"].lower()


# ==================== Diff Tools Tests ====================


class TestDiffTools:
    """Test diff perception tools."""

    def test_get_file_diff_no_changes(self, bridge):
        """get_file_diff handles file with no changes."""
        result = bridge.call_tool("get_file_diff", path="README.md")
        assert result["status"] == "ok"
        assert "has_changes" in result["data"]
        assert "path" in result["data"]

    def test_get_file_diff_blocked_path(self, bridge):
        """get_file_diff blocks sensitive files."""
        result = bridge.call_tool("get_file_diff", path=".env")
        assert result["status"] == "error"
        assert "not allowed" in result["error"].lower()

    def test_get_file_diff_with_range(self, bridge):
        """get_file_diff accepts commit range."""
        result = bridge.call_tool("get_file_diff", path="README.md", commit_range="HEAD~1..HEAD")
        # May or may not have changes depending on recent commits
        assert result["status"] == "ok"
        assert "commit_range" in result["data"]

    def test_get_diff_summary_valid(self, bridge):
        """get_diff_summary returns change summary."""
        result = bridge.call_tool("get_diff_summary", commit_range="HEAD~3..HEAD")
        assert result["status"] == "ok"
        assert "commit_range" in result["data"]
        assert "files_changed" in result["data"]
        assert "overall_stats" in result["data"]

    def test_get_diff_summary_with_grouping(self, bridge):
        """get_diff_summary groups by module."""
        result = bridge.call_tool(
            "get_diff_summary",
            commit_range="HEAD~5..HEAD",
            group_by_module=True,
        )
        assert result["status"] == "ok"
        assert "grouped_by_module" in result["data"]

    def test_get_diff_summary_scoped(self, bridge):
        """get_diff_summary respects path scope."""
        result = bridge.call_tool(
            "get_diff_summary",
            commit_range="HEAD~3..HEAD",
            path="modules/",
        )
        assert result["status"] == "ok"
        assert result["data"]["path_scope"] == "modules/"

    def test_get_diff_summary_invalid_range(self, bridge):
        """get_diff_summary handles invalid commit range."""
        result = bridge.call_tool("get_diff_summary", commit_range="invalid..range")
        assert result["status"] == "error"


# ==================== Execution Stub Tests ====================


class TestExecutionStubs:
    """Test that execution stubs return disabled status."""

    def test_coordinate_mission_disabled(self, bridge):
        """coordinate_mission is disabled in v1."""
        result = bridge.call_tool(
            "coordinate_mission",
            mission_description="Test mission",
            mission_type="code_analysis",
        )
        assert result["status"] == "disabled_in_v1"
        assert result["data"]["tool"] == "coordinate_mission"
        assert "schema" in result["data"]

    def test_spawn_agent_team_disabled(self, bridge):
        """spawn_agent_team is disabled in v1."""
        result = bridge.call_tool(
            "spawn_agent_team",
            mission_description="Test",
        )
        assert result["status"] == "disabled_in_v1"

    def test_trigger_skill_disabled(self, bridge):
        """trigger_skill is disabled in v1."""
        result = bridge.call_tool(
            "trigger_skill",
            skill_name="test_skill",
        )
        assert result["status"] == "disabled_in_v1"

    def test_write_file_disabled(self, bridge):
        """write_file is disabled in v1."""
        result = bridge.call_tool(
            "write_file",
            path="test.txt",
            content="test",
        )
        assert result["status"] == "disabled_in_v1"

    def test_create_branch_disabled(self, bridge):
        """create_branch is disabled in v1."""
        result = bridge.call_tool(
            "create_branch",
            branch_name="test-branch",
        )
        assert result["status"] == "disabled_in_v1"

    def test_create_pr_disabled(self, bridge):
        """create_pr is disabled in v1."""
        result = bridge.call_tool(
            "create_pr",
            title="Test PR",
            body="Test body",
            head="test-branch",
        )
        assert result["status"] == "disabled_in_v1"


# ==================== Error Handling Tests ====================


class TestErrorHandling:
    """Test error handling."""

    def test_unknown_tool(self, bridge):
        """Unknown tool returns error."""
        result = bridge.call_tool("nonexistent_tool")
        assert result["status"] == "error"
        assert "unknown tool" in result["error"].lower()

    def test_invalid_arguments(self, bridge):
        """Invalid arguments return error."""
        result = bridge.call_tool("get_repo_tree", invalid_param="test")
        assert result["status"] == "error"
        assert "invalid" in result["error"].lower() or "unexpected" in result["error"].lower()
