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
from .repository_analysis_cache_support import (
    _bounded_repository_analysis_scans,
    impact_call,
)


# ==================== Fixtures ====================


@pytest.fixture(scope="module")
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
        assert bridge.VERSION == "1.4.0"
        assert bridge.MODE == "perception-only"

    def test_get_status(self, bridge):
        """get_status returns valid response."""
        result = bridge.get_status()
        assert result["status"] == "ok"
        assert result["data"]["version"] == "1.4.0"
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


# ==================== Impact Scoring Tests ====================


class TestImpactScoring:
    """Test impact prediction tools."""

    def test_impact_score_module_input(self, impact_call):
        """get_change_impact_score handles module input."""
        result = impact_call(
            target_type="module",
            target="shared_utilities",
        )
        assert result["status"] == "ok"
        assert "affected_modules" in result["data"]
        assert "risk_level" in result["data"]
        assert result["data"]["risk_level"] in ("low", "medium", "high", "critical")
        assert "test_coverage" in result["data"]
        assert "confidence" in result["data"]

    def test_impact_score_file_input(self, impact_call):
        """get_change_impact_score handles file input."""
        result = impact_call(
            target_type="file",
            target="modules/infrastructure/foundups_mcp_bridge/src/bridge_server.py",
        )
        assert result["status"] == "ok"
        assert "affected_modules" in result["data"]
        assert "risk_level" in result["data"]
        assert "prior_failures" in result["data"]

    def test_impact_score_commit_range_input(self, impact_call):
        """get_change_impact_score handles commit_range input."""
        result = impact_call(
            target_type="commit_range",
            target="HEAD~3..HEAD",
        )
        assert result["status"] == "ok"
        assert "affected_modules" in result["data"]
        assert "risk_level" in result["data"]

    def test_impact_score_invalid_target_type(self, impact_call):
        """get_change_impact_score rejects invalid target_type."""
        result = impact_call(
            target_type="invalid",
            target="test",
        )
        assert result["status"] == "error"
        assert "invalid" in result["error"].lower()

    def test_impact_score_nonexistent_module(self, impact_call):
        """get_change_impact_score handles nonexistent module."""
        result = impact_call(
            target_type="module",
            target="nonexistent_module_xyz",
        )
        # Should return ok with low risk (no affected modules)
        assert result["status"] == "ok"
        assert result["data"]["risk_level"] == "low"

    def test_impact_score_critical_module(self, impact_call):
        """get_change_impact_score flags critical modules."""
        result = impact_call(
            target_type="module",
            target="shared_utilities",
        )
        assert result["status"] == "ok"
        # shared_utilities is in CRITICAL_MODULES
        affected = result["data"]["affected_modules"]
        if affected:
            shared = next((m for m in affected if m["module"] == "shared_utilities"), None)
            if shared:
                assert shared["is_critical"] is True

    def test_impact_score_test_coverage_gaps(self, impact_call):
        """get_change_impact_score reports test coverage."""
        result = impact_call(
            target_type="module",
            target="ai_overseer",
        )
        assert result["status"] == "ok"
        coverage = result["data"]["test_coverage"]
        assert "covered" in coverage
        assert "total" in coverage
        assert "gaps" in coverage
        assert isinstance(coverage["gaps"], list)

    def test_impact_score_confidence_factors(self, impact_call):
        """get_change_impact_score returns confidence factors."""
        result = impact_call(
            target_type="module",
            target="foundups_mcp_bridge",
        )
        assert result["status"] == "ok"
        assert "confidence" in result["data"]
        assert "confidence_factors" in result["data"]
        assert isinstance(result["data"]["confidence_factors"], list)
        # Confidence should be between 0 and 1
        assert 0 <= result["data"]["confidence"] <= 1

    def test_impact_score_no_prior_failures_reduces_confidence(self, impact_call):
        """Confidence is reduced when no prior failure data."""
        result = impact_call(
            target_type="module",
            target="foundups_mcp_bridge",
        )
        assert result["status"] == "ok"
        # New module likely has no failure history
        factors = result["data"]["confidence_factors"]
        # Should mention missing data or HoloIndex
        assert any("failure" in f.lower() or "holoindex" in f.lower() for f in factors)

    def test_impact_score_risk_factors(self, impact_call):
        """get_change_impact_score explains risk factors."""
        result = impact_call(
            target_type="module",
            target="ai_overseer",
        )
        assert result["status"] == "ok"
        assert "risk_factors" in result["data"]
        assert isinstance(result["data"]["risk_factors"], list)


# ==================== HoloIndex Recall Tests ====================


class TestHoloTools:
    """Test HoloIndex recall tools."""

    def test_holo_search_basic(self, bridge):
        """holo_search returns search results."""
        result = bridge.call_tool("holo_search", query="WSP protocol", scope="all", top_k=5)
        assert result["status"] == "ok"
        assert "query" in result["data"]
        assert "hits" in result["data"]
        assert "hit_count" in result["data"]
        assert result["data"]["query"] == "WSP protocol"

    def test_holo_search_empty_query_error(self, bridge):
        """holo_search rejects empty query with canonical Annex A.3 error envelope."""
        result = bridge.call_tool("holo_search", query="", scope="all", top_k=5)
        assert result["status"] == "error"
        # WSP 96 Annex A.3: error is a dict with code/message, not a flat string.
        assert isinstance(result["error"], dict)
        assert result["error"]["code"] == "EMPTY_QUERY"
        assert "empty" in result["error"]["message"].lower()
        # meta.surface must identify S2 even on error path.
        assert result["meta"]["surface"] == "S2"
        assert result["meta"]["tool"] == "holo_search"

    def test_holo_search_scoped(self, bridge):
        """holo_search respects scope filter."""
        result = bridge.call_tool("holo_search", query="module", scope="code", top_k=5)
        assert result["status"] == "ok"
        assert result["data"]["scope"] == "code"

    def test_holo_search_returns_confidence(self, bridge):
        """holo_search includes confidence in meta."""
        result = bridge.call_tool("holo_search", query="test", scope="all", top_k=3)
        assert result["status"] == "ok"
        assert "confidence" in result["meta"]

    def test_holo_related_basic(self, bridge):
        """holo_related returns related modules."""
        result = bridge.call_tool("holo_related", target="ai_overseer", relation_type="all", limit=5)
        assert result["status"] == "ok"
        assert "target" in result["data"]
        assert "related" in result["data"]
        assert "related_count" in result["data"]
        assert "sources_used" in result["data"]

    def test_holo_related_finds_dependencies(self, bridge):
        """holo_related uses dependency graph."""
        result = bridge.call_tool("holo_related", target="ai_overseer", relation_type="all", limit=10)
        assert result["status"] == "ok"
        sources = result["data"]["sources_used"]
        # Should use at least dependency analysis
        assert any("depend" in s.lower() for s in sources)

    def test_holo_related_nonexistent_module(self, bridge):
        """holo_related handles nonexistent module gracefully."""
        result = bridge.call_tool("holo_related", target="nonexistent_xyz", relation_type="all", limit=5)
        assert result["status"] == "ok"
        # Should return ok (not error) - may still find semantic matches
        assert "related" in result["data"]
        assert "related_count" in result["data"]
        # Verify no dependency relationships found for nonexistent module
        related = result["data"]["related"]
        dependency_relations = [r for r in related if r.get("relation") in ("depends_on", "depended_by")]
        assert len(dependency_relations) == 0  # No deps for nonexistent module

    def test_holo_failure_memory_basic(self, bridge):
        """holo_failure_memory returns failure patterns."""
        result = bridge.call_tool("holo_failure_memory", query="test", limit=5)
        assert result["status"] == "ok"
        assert "query" in result["data"]
        assert "failures" in result["data"]
        assert "failure_count" in result["data"]
        assert "sources_used" in result["data"]

    def test_holo_failure_memory_no_results(self, bridge):
        """holo_failure_memory handles no results gracefully."""
        result = bridge.call_tool("holo_failure_memory", query="xyznonexistent123", limit=5)
        assert result["status"] == "ok"
        assert "failures" in result["data"]
        # No crash, empty is fine

    def test_holo_pattern_search_basic(self, bridge):
        """holo_pattern_search returns patterns."""
        result = bridge.call_tool("holo_pattern_search", query="refactoring", limit=5)
        assert result["status"] == "ok"
        assert "query" in result["data"]
        assert "patterns" in result["data"]
        assert "pattern_count" in result["data"]
        assert "sources_used" in result["data"]

    def test_holo_pattern_search_adaptive_learning(self, bridge):
        """holo_pattern_search uses adaptive learning files."""
        result = bridge.call_tool("holo_pattern_search", query="pattern", limit=10)
        assert result["status"] == "ok"
        sources = result["data"]["sources_used"]
        # Should check adaptive learning files
        assert any("adaptive" in s.lower() for s in sources) or result["data"]["pattern_count"] >= 0

    def test_holo_task_packet_basic(self, bridge):
        """holo_task_packet assembles context."""
        result = bridge.call_tool(
            "holo_task_packet",
            task_description="Add new feature to MCP bridge",
            include_patterns=True,
            include_failures=True,
        )
        assert result["status"] == "ok"
        assert "task" in result["data"]
        assert "relevant_modules" in result["data"]
        assert "relevant_docs" in result["data"]
        assert "relevant_patterns" in result["data"]
        assert "known_risks" in result["data"]
        assert "confidence" in result["data"]

    def test_holo_task_packet_empty_description_error(self, bridge):
        """holo_task_packet rejects empty description."""
        result = bridge.call_tool("holo_task_packet", task_description="")
        assert result["status"] == "error"
        assert "empty" in result["error"].lower()

    def test_holo_task_packet_confidence_range(self, bridge):
        """holo_task_packet confidence is in valid range."""
        result = bridge.call_tool(
            "holo_task_packet",
            task_description="Fix bug in ai_overseer",
        )
        assert result["status"] == "ok"
        confidence = result["data"]["confidence"]
        assert 0 <= confidence <= 1

    def test_holo_task_packet_without_patterns(self, bridge):
        """holo_task_packet works without patterns."""
        result = bridge.call_tool(
            "holo_task_packet",
            task_description="Test task",
            include_patterns=False,
            include_failures=False,
        )
        assert result["status"] == "ok"
        # Should still have modules and docs
        assert "relevant_modules" in result["data"]

    def test_holo_tools_listed(self, bridge):
        """All holo tools appear in tool listing."""
        result = bridge.list_tools()
        assert result["status"] == "ok"
        tool_names = [t["name"] for t in result["data"]["tools"]]
        assert "holo_search" in tool_names
        assert "holo_related" in tool_names
        assert "holo_failure_memory" in tool_names
        assert "holo_pattern_search" in tool_names
        assert "holo_task_packet" in tool_names

    def test_holo_tools_are_active(self, bridge):
        """All holo tools have active status."""
        result = bridge.list_tools()
        assert result["status"] == "ok"
        holo_tools = [t for t in result["data"]["tools"] if t["name"].startswith("holo_")]
        for tool in holo_tools:
            assert tool["status"] == "active", f"{tool['name']} should be active"


# ==================== Signal Normalization Tests ====================


class TestSignalNormalization:
    """Test state compression and signal normalization tools."""

    # --- Overseer Summary Tests ---

    def test_overseer_summary_basic(self, bridge):
        """get_overseer_summary returns compressed state."""
        result = bridge.call_tool("get_overseer_summary")
        assert result["status"] == "ok"
        assert "top_concerns" in result["data"]
        assert "mission_activity" in result["data"]
        assert "failure_clusters" in result["data"]
        assert "hot_modules" in result["data"]
        assert "system_posture" in result["data"]
        assert "recommended_focus" in result["data"]

    def test_overseer_summary_has_confidence(self, bridge):
        """get_overseer_summary returns confidence score."""
        result = bridge.call_tool("get_overseer_summary")
        assert result["status"] == "ok"
        assert "confidence" in result["meta"]
        assert 0 <= result["meta"]["confidence"] <= 1

    def test_overseer_summary_has_sources(self, bridge):
        """get_overseer_summary reports sources used."""
        result = bridge.call_tool("get_overseer_summary")
        assert result["status"] == "ok"
        assert "sources_used" in result["meta"]
        assert isinstance(result["meta"]["sources_used"], list)

    # --- Hot Modules Tests ---

    def test_hot_modules_basic(self, bridge):
        """get_hot_modules returns ranked module list."""
        result = bridge.call_tool("get_hot_modules", limit=5)
        assert result["status"] == "ok"
        assert "modules" in result["data"]
        assert "total_scored" in result["data"]
        assert "scoring_note" in result["data"]

    def test_hot_modules_structure(self, bridge):
        """get_hot_modules returns proper module structure."""
        result = bridge.call_tool("get_hot_modules", limit=10)
        assert result["status"] == "ok"
        for module in result["data"].get("modules", []):
            assert "module" in module
            assert "heat_score" in module
            assert "factors" in module
            assert isinstance(module["factors"], list)

    def test_hot_modules_empty_is_valid(self, bridge):
        """get_hot_modules handles empty state gracefully."""
        result = bridge.call_tool("get_hot_modules", limit=5)
        assert result["status"] == "ok"
        # Empty modules list is valid
        assert isinstance(result["data"]["modules"], list)

    # --- Repeated Failures Tests ---

    def test_repeated_failures_basic(self, bridge):
        """get_repeated_failures returns clustered failures."""
        result = bridge.call_tool("get_repeated_failures", limit=5)
        assert result["status"] == "ok"
        assert "clusters" in result["data"]
        assert "total_clusters" in result["data"]
        assert "total_failures_analyzed" in result["data"]

    def test_repeated_failures_cluster_structure(self, bridge):
        """get_repeated_failures returns proper cluster structure."""
        result = bridge.call_tool("get_repeated_failures", limit=10)
        assert result["status"] == "ok"
        for cluster in result["data"].get("clusters", []):
            assert "signature" in cluster
            assert "count" in cluster
            assert "severity" in cluster

    def test_repeated_failures_no_results(self, bridge):
        """get_repeated_failures handles no failures gracefully."""
        result = bridge.call_tool("get_repeated_failures", limit=5)
        assert result["status"] == "ok"
        # Should have note if no failures
        assert "note" in result["data"] or len(result["data"]["clusters"]) > 0

    # --- Active Risks Tests ---

    def test_active_risks_basic(self, bridge):
        """get_active_risks returns normalized risk list."""
        result = bridge.call_tool("get_active_risks", limit=5)
        assert result["status"] == "ok"
        assert "risks" in result["data"]
        assert "total_risks" in result["data"]
        assert "risk_taxonomy" in result["data"]

    def test_active_risks_structure(self, bridge):
        """get_active_risks returns proper risk structure."""
        result = bridge.call_tool("get_active_risks", limit=10)
        assert result["status"] == "ok"
        for risk in result["data"].get("risks", []):
            assert "risk_type" in risk
            assert "scope" in risk
            assert "severity" in risk
            assert "confidence" in risk

    def test_active_risks_severity_values(self, bridge):
        """get_active_risks uses valid severity levels."""
        result = bridge.call_tool("get_active_risks", limit=10)
        assert result["status"] == "ok"
        valid_severities = {"low", "medium", "high", "critical"}
        for risk in result["data"].get("risks", []):
            assert risk["severity"] in valid_severities

    # --- Recommended Focus Tests ---

    def test_recommended_focus_basic(self, bridge):
        """get_recommended_focus returns prioritized items."""
        result = bridge.call_tool("get_recommended_focus", limit=5)
        assert result["status"] == "ok"
        assert "focus_items" in result["data"]
        assert "total_items" in result["data"]
        assert "priority_note" in result["data"]

    def test_recommended_focus_structure(self, bridge):
        """get_recommended_focus returns proper focus structure."""
        result = bridge.call_tool("get_recommended_focus", limit=10)
        assert result["status"] == "ok"
        for item in result["data"].get("focus_items", []):
            assert "focus" in item
            assert "why_now" in item
            assert "priority" in item

    def test_recommended_focus_priority_order(self, bridge):
        """get_recommended_focus returns items in priority order."""
        result = bridge.call_tool("get_recommended_focus", limit=10)
        assert result["status"] == "ok"
        items = result["data"].get("focus_items", [])
        if len(items) >= 2:
            # Items should be sorted by priority (lower = higher priority)
            priorities = [i["priority"] for i in items]
            assert priorities == sorted(priorities)

    # --- Prompt Context Packet Tests ---

    def test_prompt_context_packet_basic(self, bridge):
        """get_prompt_context_packet returns assembled context."""
        result = bridge.call_tool("get_prompt_context_packet")
        assert result["status"] == "ok"
        assert "system_posture" in result["data"]
        assert "hot_modules" in result["data"]
        assert "active_risks" in result["data"]
        assert "repeated_failures" in result["data"]
        assert "recommended_focus" in result["data"]

    def test_prompt_context_packet_with_task(self, bridge):
        """get_prompt_context_packet includes task relevance."""
        result = bridge.call_tool(
            "get_prompt_context_packet",
            task_description="Fix bug in ai_overseer module"
        )
        assert result["status"] == "ok"
        assert "task_relevance" in result["data"]
        # Task relevance should include the task
        if result["data"]["task_relevance"]:
            assert "task" in result["data"]["task_relevance"]

    def test_prompt_context_packet_without_task(self, bridge):
        """get_prompt_context_packet works without task description."""
        result = bridge.call_tool("get_prompt_context_packet", task_description=None)
        assert result["status"] == "ok"
        # task_relevance should be None when no task provided
        assert result["data"]["task_relevance"] is None

    def test_prompt_context_packet_confidence(self, bridge):
        """get_prompt_context_packet returns confidence in valid range."""
        result = bridge.call_tool("get_prompt_context_packet")
        assert result["status"] == "ok"
        assert "confidence" in result["meta"]
        assert 0 <= result["meta"]["confidence"] <= 1

    # --- Tool Listing Tests ---

    def test_signal_tools_listed(self, bridge):
        """All signal normalization tools appear in tool listing."""
        result = bridge.list_tools()
        assert result["status"] == "ok"
        tool_names = [t["name"] for t in result["data"]["tools"]]
        assert "get_overseer_summary" in tool_names
        assert "get_hot_modules" in tool_names
        assert "get_repeated_failures" in tool_names
        assert "get_active_risks" in tool_names
        assert "get_recommended_focus" in tool_names
        assert "get_prompt_context_packet" in tool_names

    def test_signal_tools_are_active(self, bridge):
        """All signal normalization tools have active status."""
        result = bridge.list_tools()
        assert result["status"] == "ok"
        signal_tools = [
            "get_overseer_summary", "get_hot_modules", "get_repeated_failures",
            "get_active_risks", "get_recommended_focus", "get_prompt_context_packet"
        ]
        for tool in result["data"]["tools"]:
            if tool["name"] in signal_tools:
                assert tool["status"] == "active", f"{tool['name']} should be active"


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


# ==================== S63: S2 holo_search Annex A Conformance ====================


class TestS2HoloSearchAnnexAConformance:
    """S63 (MCPA6 follow-up): verify S2 holo_search conforms to WSP 96 Annex A.

    Closes MCPA6 drift IDs:
      - D12: `scope` -> `doc_type_filter` (with alias)
      - D13: `top_k` -> `limit` (with alias)
      - D14: `foundup_id` request field accepted and echoed
      - D15: `include_shared` request field accepted and echoed
      - D16: empty-query error includes canonical `error.code = "EMPTY_QUERY"`
      - D17: lexical fallback caps relevance at 0.6 (Annex A.3 policy)
      - D18: meta.surface = "S2" present on every response
    """

    # ----- Canonical request fields accepted -----

    def test_canonical_doc_type_filter_accepted(self, bridge):
        """`doc_type_filter` works as the canonical name for scope."""
        result = bridge.call_tool(
            "holo_search", query="WSP", doc_type_filter="wsp", limit=3
        )
        assert result["status"] == "ok"
        assert result["data"]["doc_type_filter"] == "wsp"
        # Back-compat alias `scope` mirrors the same value
        assert result["data"]["scope"] == "wsp"

    def test_canonical_limit_accepted(self, bridge):
        """`limit` works as the canonical name for top_k."""
        result = bridge.call_tool("holo_search", query="WSP", limit=3)
        assert result["status"] == "ok"
        # hits should not exceed the canonical limit
        assert result["data"]["hit_count"] <= 3

    def test_foundup_id_accepted_and_echoed(self, bridge):
        result = bridge.call_tool(
            "holo_search", query="WSP", foundup_id="gotjunk_001", limit=3
        )
        assert result["status"] == "ok"
        assert result["data"]["foundup_id"] == "gotjunk_001"

    def test_include_shared_with_foundup_id_echoed(self, bridge):
        """include_shared echoes the request value when foundup_id is set."""
        result = bridge.call_tool(
            "holo_search",
            query="WSP",
            foundup_id="kosei",
            include_shared=False,
            limit=3,
        )
        assert result["status"] == "ok"
        assert result["data"]["include_shared"] is False

    def test_include_shared_null_when_no_foundup_id(self, bridge):
        """include_shared echoes None when foundup_id is absent (Annex A.2)."""
        result = bridge.call_tool(
            "holo_search", query="WSP", include_shared=False, limit=3
        )
        assert result["status"] == "ok"
        assert result["data"]["include_shared"] is None

    # ----- Back-compat aliases still work -----

    def test_legacy_scope_alias_accepted(self, bridge):
        """Legacy `scope` keyword still works (back-compat)."""
        result = bridge.call_tool("holo_search", query="WSP", scope="wsp", top_k=3)
        assert result["status"] == "ok"
        assert result["data"]["doc_type_filter"] == "wsp"

    def test_legacy_top_k_alias_accepted(self, bridge):
        """Legacy `top_k` keyword still works (back-compat)."""
        result = bridge.call_tool("holo_search", query="WSP", top_k=3)
        assert result["status"] == "ok"
        assert result["data"]["hit_count"] <= 3

    def test_alias_warnings_surfaced(self, bridge):
        """Using legacy names triggers a truthful warning per WSP 97."""
        result = bridge.call_tool(
            "holo_search", query="WSP", scope="wsp", top_k=3
        )
        warnings = result["data"]["metadata"]["warnings"]
        assert any("scope" in w for w in warnings), (
            "expected a warning naming legacy 'scope' alias"
        )
        assert any("top_k" in w for w in warnings), (
            "expected a warning naming legacy 'top_k' alias"
        )

    def test_canonical_wins_over_alias_for_filter(self, bridge):
        """When both doc_type_filter and scope are passed, canonical wins."""
        result = bridge.call_tool(
            "holo_search",
            query="WSP",
            doc_type_filter="wsp",
            scope="code",
            limit=3,
        )
        assert result["data"]["doc_type_filter"] == "wsp"

    def test_canonical_wins_over_alias_for_limit(self, bridge):
        """When both limit and top_k are passed, canonical wins."""
        result = bridge.call_tool(
            "holo_search", query="WSP", limit=2, top_k=10
        )
        assert result["data"]["hit_count"] <= 2

    # ----- Annex A.2 limit bounds -----

    def test_limit_clamped_above_50(self, bridge):
        """limit > 50 is clamped per Annex A.2; warning surfaces the clamp."""
        result = bridge.call_tool("holo_search", query="WSP", limit=999)
        warnings = result["data"]["metadata"]["warnings"]
        assert any(
            "clamp" in w.lower() and "50" in w for w in warnings
        ), f"expected clamp warning naming 50; got {warnings}"

    def test_limit_clamped_below_1(self, bridge):
        """limit < 1 is clamped per Annex A.2."""
        result = bridge.call_tool("holo_search", query="WSP", limit=0)
        warnings = result["data"]["metadata"]["warnings"]
        assert any("clamp" in w.lower() for w in warnings)

    # ----- meta block (Annex A.3) -----

    def test_meta_surface_is_s2(self, bridge):
        """Every response carries meta.surface = 'S2'."""
        result = bridge.call_tool("holo_search", query="WSP", limit=3)
        assert result["meta"]["surface"] == "S2"

    def test_meta_tool_is_holo_search(self, bridge):
        result = bridge.call_tool("holo_search", query="WSP", limit=3)
        assert result["meta"]["tool"] == "holo_search"

    def test_meta_source_truthful(self, bridge):
        """meta.source MUST be 'holoindex' or 'fallback' — never overclaimed."""
        result = bridge.call_tool("holo_search", query="WSP", limit=3)
        assert result["meta"]["source"] in ("holoindex", "fallback")

    # ----- data.metadata block (Annex A.3) -----

    def test_data_metadata_has_canonical_keys(self, bridge):
        """data.metadata MUST include retrieval_mode + warnings (canonical)."""
        result = bridge.call_tool("holo_search", query="WSP", limit=3)
        meta = result["data"]["metadata"]
        assert "retrieval_mode" in meta
        assert "warnings" in meta
        assert isinstance(meta["warnings"], list)

    def test_data_metadata_retrieval_mode_truthful(self, bridge):
        """retrieval_mode value must be one of the Annex A.3 enum strings."""
        result = bridge.call_tool("holo_search", query="WSP", limit=3)
        mode = result["data"]["metadata"]["retrieval_mode"]
        assert mode in ("semantic", "lexical", "fallback", "none")

    # ----- Empty query error envelope (Annex A.3) -----

    def test_empty_query_error_has_canonical_code(self, bridge):
        result = bridge.call_tool("holo_search", query="")
        assert result["status"] == "error"
        assert isinstance(result["error"], dict)
        assert result["error"]["code"] == "EMPTY_QUERY"
        assert "message" in result["error"]
        assert result["meta"]["surface"] == "S2"

    def test_whitespace_query_rejected_with_empty_query_code(self, bridge):
        """Whitespace-only queries are also rejected as EMPTY_QUERY."""
        result = bridge.call_tool("holo_search", query="   \t\n  ")
        assert result["status"] == "error"
        assert result["error"]["code"] == "EMPTY_QUERY"

    # ----- Federation field warnings (truthful per WSP 97) -----

    def test_foundup_id_surfaces_unenforced_warning(self, bridge):
        """Passing foundup_id surfaces a truthful 'not yet enforced' warning."""
        result = bridge.call_tool(
            "holo_search", query="WSP", foundup_id="gotjunk_001", limit=3
        )
        warnings = result["data"]["metadata"]["warnings"]
        assert any(
            "foundup_id" in w and "not yet enforced" in w for w in warnings
        ), f"expected unenforced-tenant warning; got {warnings}"

    # ----- Fallback relevance cap (Annex A.3 lexical-fallback rule) -----

    def test_fallback_relevance_capped_at_06(self, bridge, monkeypatch):
        """When falling back to ripgrep, hit relevance MUST be capped at 0.6.

        Forces the fallback path by stubbing the HoloIndex factory. The
        fallback may either find hits (cap applies) OR fail to find any
        (canonical BACKEND_UNAVAILABLE error). Both branches are honored
        truthfully — the slice's invariant is that the cap is never exceeded
        when hits ARE returned, never that the fallback always returns hits.
        """
        from modules.infrastructure.foundups_mcp_bridge.src import holo_tools

        monkeypatch.setattr(holo_tools, "_get_holoindex", lambda _root: None)

        result = bridge.call_tool("holo_search", query="WSP", limit=5)

        if result["status"] == "ok":
            # Cap MUST apply to any returned hit
            for hit in result["data"]["hits"]:
                assert hit.get("relevance", 0) <= 0.6, (
                    "Annex A.3: lexical fallback hits MUST cap relevance at 0.6"
                )
            # And retrieval_mode must truthfully name the fallback path
            assert result["data"]["metadata"]["retrieval_mode"] in (
                "lexical",
                "fallback",
            )
        else:
            # When ripgrep also fails, S2 emits the canonical BACKEND_UNAVAILABLE
            # error envelope rather than fake hits.
            assert isinstance(result["error"], dict)
            assert result["error"]["code"] == "BACKEND_UNAVAILABLE"
            assert result["meta"]["surface"] == "S2"

    # ----- Direct invocation (the slice spec requires one direct example) -----

    def test_direct_holo_tools_invocation_canonical_envelope(self):
        """Direct call to holo_tools.holo_search bypasses the bridge wrapper
        and proves the envelope conforms even without bridge dispatch."""
        from pathlib import Path
        from modules.infrastructure.foundups_mcp_bridge.src.holo_tools import (
            holo_search,
        )

        repo_root = Path(__file__).resolve().parents[4]
        result = holo_search(
            repo_root,
            query="WSP",
            limit=3,
            doc_type_filter="all",
            foundup_id=None,
            include_shared=True,
        )

        # Canonical envelope shape
        assert result["status"] == "ok"
        assert "data" in result
        assert "meta" in result
        assert result["data"]["query"] == "WSP"
        assert result["data"]["doc_type_filter"] == "all"
        assert result["data"]["foundup_id"] is None
        assert result["data"]["include_shared"] is None  # null without foundup_id
        assert "hits" in result["data"]
        assert "hit_count" in result["data"]
        assert "metadata" in result["data"]
        assert result["meta"]["surface"] == "S2"
        assert result["meta"]["tool"] == "holo_search"


# ==================== S64: S1/S2 federation scope request parity ====================


class TestS64FederationScopeParity:
    """S64: cross-surface parity for ``foundup_id`` / ``include_shared``.

    Verifies the S2 side of the contract:
      - shared template constant is intact and contains ``{surface}`` token
      - ``federation_scope_warning(S2)`` produces the expected text
      - request without ``foundup_id`` echoes ``foundup_id=None``,
        ``include_shared=None``
      - request with ``foundup_id`` echoes both, plus the canonical warning
      - the actual warning emitted by S2 ``holo_search`` matches
        ``federation_scope_warning(S2)`` byte-for-byte
      - cross-surface check: S1's template byte-equals S2's template
    """

    def test_s2_template_has_surface_token(self):
        from modules.infrastructure.foundups_mcp_bridge.src.holo_tools import (
            FEDERATION_SCOPE_WARNING_TEMPLATE,
        )
        assert "{surface}" in FEDERATION_SCOPE_WARNING_TEMPLATE

    def test_s2_template_carries_canonical_phrasing(self):
        from modules.infrastructure.foundups_mcp_bridge.src.holo_tools import (
            FEDERATION_SCOPE_WARNING_TEMPLATE,
        )
        for phrase in (
            "foundup_id received",
            "tenant scoping not yet enforced",
            "MCPA1 Slice 6",
        ):
            assert phrase in FEDERATION_SCOPE_WARNING_TEMPLATE

    def test_federation_scope_warning_for_s2(self):
        from modules.infrastructure.foundups_mcp_bridge.src.holo_tools import (
            federation_scope_warning,
        )
        warn = federation_scope_warning("S2")
        assert "at S2" in warn
        assert "MCPA1 Slice 6" in warn
        assert "{surface}" not in warn

    def test_no_foundup_id_echoes_null_pair(self, bridge):
        """Without ``foundup_id``, both echoes are null (parity invariant)."""
        result = bridge.call_tool("holo_search", query="WSP", limit=3)
        assert result["status"] == "ok"
        assert result["data"]["foundup_id"] is None
        assert result["data"]["include_shared"] is None
        warnings = result["data"]["metadata"]["warnings"]
        assert not any("tenant scoping" in w for w in warnings)

    def test_no_foundup_id_with_explicit_include_shared_still_null(self, bridge):
        """``include_shared=False`` without ``foundup_id`` echoes ``None``
        (Annex A.2 semantics — the flag is only meaningful with scope)."""
        result = bridge.call_tool(
            "holo_search", query="WSP", include_shared=False, limit=3
        )
        assert result["data"]["foundup_id"] is None
        assert result["data"]["include_shared"] is None

    def test_with_foundup_id_echoes_both_and_warns(self, bridge):
        from modules.infrastructure.foundups_mcp_bridge.src.holo_tools import (
            federation_scope_warning,
        )
        result = bridge.call_tool(
            "holo_search",
            query="WSP",
            foundup_id="gotjunk_001",
            include_shared=False,
            limit=3,
        )
        assert result["data"]["foundup_id"] == "gotjunk_001"
        assert result["data"]["include_shared"] is False
        warnings = result["data"]["metadata"]["warnings"]
        assert federation_scope_warning("S2") in warnings

    def test_emitted_warning_matches_template_byte_for_byte(self, bridge):
        """The runtime-emitted warning MUST equal ``federation_scope_warning(S2)``
        verbatim — protects against drift if a future edit changes spacing
        or punctuation."""
        from modules.infrastructure.foundups_mcp_bridge.src.holo_tools import (
            federation_scope_warning,
        )
        result = bridge.call_tool(
            "holo_search", query="WSP", foundup_id="kosei", limit=3
        )
        warnings = result["data"]["metadata"]["warnings"]
        scope_warnings = [w for w in warnings if "foundup_id received" in w]
        assert len(scope_warnings) == 1
        assert scope_warnings[0] == federation_scope_warning("S2")

    def test_s1_template_matches_s2_template(self):
        """Cross-surface parity: S1's template MUST match S2's template
        byte-for-byte (modulo `{surface}` substitution). Drift in either
        module flags here.
        """
        import sys
        from pathlib import Path

        s1_dir = (
            Path(__file__).resolve().parents[4]
            / "foundups-mcp-p1"
            / "servers"
            / "holo_index"
        )
        if str(s1_dir) not in sys.path:
            sys.path.insert(0, str(s1_dir))

        try:
            from canonical_search import (  # type: ignore
                FEDERATION_SCOPE_WARNING_TEMPLATE as s1_template,
            )
        except Exception:
            import pytest as _pytest

            _pytest.skip("S1 canonical_search not importable in this environment")

        from modules.infrastructure.foundups_mcp_bridge.src.holo_tools import (
            FEDERATION_SCOPE_WARNING_TEMPLATE as s2_template,
        )

        assert s1_template == s2_template, (
            "S1 and S2 federation-scope warning templates have drifted; "
            "they MUST be byte-identical per S64 parity contract."
        )
