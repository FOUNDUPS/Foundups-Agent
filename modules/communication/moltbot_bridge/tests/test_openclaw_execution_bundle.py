"""Tests for OpenClaw execution bundle (WSP 87/97 compliance).

Validates bounded HoloIndex-guided context retrieval before execution.
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch


class TestExecutionBundleDataclass:
    """Test ExecutionBundle dataclass behavior."""

    def test_empty_bundle_has_defaults(self):
        """ExecutionBundle initializes with expected defaults."""
        from modules.communication.moltbot_bridge.src.openclaw_execution_bundle import (
            ExecutionBundle,
        )

        bundle = ExecutionBundle(query="test query")
        assert bundle.query == "test query"
        assert bundle.route == ""
        assert bundle.docs == []
        assert bundle.patterns == []
        assert bundle.candidate_paths == []
        assert bundle.constraints == []
        assert bundle.verification_hints == []
        assert bundle.confidence == 0.0
        assert bundle.code_hits == []
        assert bundle.wsp_hits == []

    def test_is_actionable_with_high_confidence(self):
        """Bundle is actionable when confidence >= 0.3."""
        from modules.communication.moltbot_bridge.src.openclaw_execution_bundle import (
            ExecutionBundle,
        )

        bundle = ExecutionBundle(query="test", confidence=0.5)
        assert bundle.is_actionable() is True

    def test_is_actionable_with_candidate_paths(self):
        """Bundle is actionable when candidate_paths present."""
        from modules.communication.moltbot_bridge.src.openclaw_execution_bundle import (
            ExecutionBundle,
        )

        bundle = ExecutionBundle(
            query="test",
            confidence=0.1,
            candidate_paths=["src/foo.py"],
        )
        assert bundle.is_actionable() is True

    def test_not_actionable_low_confidence_no_paths(self):
        """Bundle not actionable when low confidence and no paths."""
        from modules.communication.moltbot_bridge.src.openclaw_execution_bundle import (
            ExecutionBundle,
        )

        bundle = ExecutionBundle(query="test", confidence=0.1)
        assert bundle.is_actionable() is False

    def test_to_compact_dict_structure(self):
        """to_compact_dict returns expected structure."""
        from modules.communication.moltbot_bridge.src.openclaw_execution_bundle import (
            ExecutionBundle,
        )

        bundle = ExecutionBundle(
            query="find all pytest fixtures" * 10,  # Long query
            route="holo_index",
            docs=["README.md", "INTERFACE.md"],
            patterns=[{"action": "test"}],
            candidate_paths=["a.py", "b.py", "c.py"],
            constraints=["WSP: Test Coverage"],
            confidence=0.85,
            code_hits=[{"file": "a.py"}],
            wsp_hits=[{"title": "WSP 5"}],
        )
        compact = bundle.to_compact_dict()

        assert len(compact["query"]) <= 100  # Truncated
        assert compact["route"] == "holo_index"
        assert compact["docs_count"] == 2
        assert compact["patterns_count"] == 1
        assert compact["candidates_count"] == 3
        assert compact["constraints_count"] == 1
        assert compact["confidence"] == 0.85

    def test_code_hits_and_wsp_hits_stored(self):
        """Bundle stores raw HoloIndex hits for route consumption."""
        from modules.communication.moltbot_bridge.src.openclaw_execution_bundle import (
            ExecutionBundle,
        )

        code_hits = [{"file": "test.py", "content": "def test()"}]
        wsp_hits = [{"title": "WSP 5", "content": "Test coverage"}]

        bundle = ExecutionBundle(
            query="test",
            code_hits=code_hits,
            wsp_hits=wsp_hits,
        )
        assert bundle.code_hits == code_hits
        assert bundle.wsp_hits == wsp_hits


class TestBuildExecutionBundle:
    """Test build_execution_bundle function."""

    def test_build_bundle_without_holoindex(self):
        """Bundle builds gracefully when HoloIndex unavailable."""
        from modules.communication.moltbot_bridge.src.openclaw_execution_bundle import (
            build_execution_bundle,
        )

        with patch.dict("sys.modules", {"holo_index.core.holo_index": None}):
            bundle = build_execution_bundle("test query", route="test")

        assert bundle.query == "test query"
        assert bundle.route == "test"
        # No crash, bundle created with defaults

    def test_build_bundle_infers_docs_for_known_routes(self):
        """Bundle includes docs for known routes."""
        from modules.communication.moltbot_bridge.src.openclaw_execution_bundle import (
            build_execution_bundle,
        )

        bundle = build_execution_bundle("status check", route="holo_index")
        assert "holo_index/README.md" in bundle.docs

    def test_build_bundle_includes_verification_hints(self):
        """Bundle includes verification hints based on query."""
        from modules.communication.moltbot_bridge.src.openclaw_execution_bundle import (
            build_execution_bundle,
        )

        bundle = build_execution_bundle("search for tests", route="holo_index")
        assert any("results" in hint.lower() for hint in bundle.verification_hints)

    def test_build_bundle_stores_raw_holoindex_hits(self):
        """Bundle stores raw code_hits and wsp_hits from HoloIndex."""
        from modules.communication.moltbot_bridge.src.openclaw_execution_bundle import (
            build_execution_bundle,
        )

        mock_code_hits = [{"file": "src/test.py", "content": "test code", "score": 0.8}]
        mock_wsp_hits = [{"title": "WSP 5", "content": "Test coverage"}]
        mock_results = {"code": mock_code_hits, "wsps": mock_wsp_hits}

        with patch(
            "holo_index.core.holo_index.HoloIndex"
        ) as MockHolo:
            mock_holo = MagicMock()
            mock_holo.search.return_value = mock_results
            MockHolo.return_value = mock_holo

            bundle = build_execution_bundle("find tests", route="holo_index", limit=5)

        assert len(bundle.code_hits) == 1
        assert bundle.code_hits[0]["file"] == "src/test.py"
        assert len(bundle.wsp_hits) == 1
        assert bundle.wsp_hits[0]["title"] == "WSP 5"


class TestMemoryQueryBundle:
    """Test retrieve_bundle_for_memory_query function."""

    def test_memory_bundle_has_high_confidence(self):
        """Memory query bundles have deterministic high confidence."""
        from modules.communication.moltbot_bridge.src.openclaw_execution_bundle import (
            retrieve_bundle_for_memory_query,
        )

        bundle = retrieve_bundle_for_memory_query("decisions", topic="architecture")
        assert bundle.confidence == 0.9
        assert bundle.route == "memory_query"
        assert "memory:decisions:architecture" in bundle.query

    def test_memory_bundle_includes_constraints(self):
        """Memory bundles include WSP constraints."""
        from modules.communication.moltbot_bridge.src.openclaw_execution_bundle import (
            retrieve_bundle_for_memory_query,
        )

        bundle = retrieve_bundle_for_memory_query("sessions")
        assert any("WSP" in c for c in bundle.constraints)

    def test_memory_bundle_verification_hints(self):
        """Memory bundles have verification hints."""
        from modules.communication.moltbot_bridge.src.openclaw_execution_bundle import (
            retrieve_bundle_for_memory_query,
        )

        bundle = retrieve_bundle_for_memory_query("unresolved")
        assert len(bundle.verification_hints) >= 1


class TestExecutionRouteIntegration:
    """Test execute_query uses execution bundle data."""

    @pytest.mark.asyncio
    async def test_execute_query_uses_bundle_hits_not_separate_search(self):
        """execute_query uses bundle's code_hits/wsp_hits, not a second search."""
        from modules.communication.moltbot_bridge.src.openclaw_execution_routes import (
            execute_query,
        )
        from modules.communication.moltbot_bridge.src.openclaw_execution_bundle import (
            ExecutionBundle,
        )

        mock_dae = MagicMock()
        mock_dae._is_token_usage_query.return_value = False
        mock_dae._is_identity_query.return_value = False

        mock_intent = MagicMock()
        mock_intent.raw_message = "find test fixtures"
        mock_intent.extracted_task = "find test fixtures"

        # Create bundle with code_hits that should appear in response
        test_bundle = ExecutionBundle(
            query="find test fixtures",
            route="holo_index",
            confidence=0.8,
            code_hits=[{"file": "src/unique_test_file.py", "content": "unique content here"}],
            wsp_hits=[{"title": "WSP 99 Unique", "content": "unique wsp content"}],
            verification_hints=["Verify unique hint"],
            candidate_paths=["src/unique_test_file.py"],
        )

        with patch(
            "modules.communication.moltbot_bridge.src.openclaw_execution_routes.build_execution_bundle"
        ) as mock_build:
            mock_build.return_value = test_bundle
            with patch(
                "modules.communication.moltbot_bridge.src.openclaw_execution_routes._try_memory_query",
                return_value=None,
            ):
                with patch(
                    "modules.communication.moltbot_bridge.src.openclaw_execution_routes._try_schedule_command",
                    return_value=None,
                ):
                    response = await execute_query(mock_dae, mock_intent)

        # Bundle was called once
        mock_build.assert_called_once()

        # Response contains bundle's code_hits data
        assert "src/unique_test_file.py" in response
        assert "unique content" in response

        # Response contains bundle's wsp_hits data
        assert "WSP 99 Unique" in response
        assert "unique wsp content" in response

        # Response contains verification hints from bundle
        assert "Verify unique hint" in response

    @pytest.mark.asyncio
    async def test_execute_query_no_duplicate_holoindex_search(self):
        """execute_query does NOT call HoloIndex directly - only via bundle."""
        from modules.communication.moltbot_bridge.src.openclaw_execution_routes import (
            execute_query,
        )
        from modules.communication.moltbot_bridge.src.openclaw_execution_bundle import (
            ExecutionBundle,
        )

        mock_dae = MagicMock()
        mock_dae._is_token_usage_query.return_value = False
        mock_dae._is_identity_query.return_value = False

        mock_intent = MagicMock()
        mock_intent.raw_message = "search query"
        mock_intent.extracted_task = "search query"

        test_bundle = ExecutionBundle(
            query="search query",
            route="holo_index",
            confidence=0.5,
            code_hits=[{"file": "test.py", "content": "test"}],
            wsp_hits=[],
        )

        with patch(
            "modules.communication.moltbot_bridge.src.openclaw_execution_routes.build_execution_bundle"
        ) as mock_build:
            mock_build.return_value = test_bundle
            with patch(
                "modules.communication.moltbot_bridge.src.openclaw_execution_routes._try_memory_query",
                return_value=None,
            ):
                with patch(
                    "modules.communication.moltbot_bridge.src.openclaw_execution_routes._try_schedule_command",
                    return_value=None,
                ):
                    # Patch HoloIndex to track if it's called directly
                    with patch(
                        "holo_index.core.HoloIndex"
                    ) as mock_holo_class:
                        await execute_query(mock_dae, mock_intent)

                        # HoloIndex should NOT be instantiated in execute_query
                        # (it's only called inside build_execution_bundle)
                        mock_holo_class.assert_not_called()

    @pytest.mark.asyncio
    async def test_bundle_candidate_paths_used_when_no_holoindex_hits(self):
        """When bundle has no code_hits but has candidate_paths, paths appear in response."""
        from modules.communication.moltbot_bridge.src.openclaw_execution_routes import (
            execute_query,
        )
        from modules.communication.moltbot_bridge.src.openclaw_execution_bundle import (
            ExecutionBundle,
        )

        mock_dae = MagicMock()
        mock_dae._is_token_usage_query.return_value = False
        mock_dae._is_identity_query.return_value = False

        mock_intent = MagicMock()
        mock_intent.raw_message = "obscure query"
        mock_intent.extracted_task = "obscure query"

        # Bundle with no HoloIndex hits but candidate paths from breadcrumbs
        test_bundle = ExecutionBundle(
            query="obscure query",
            route="holo_index",
            confidence=0.2,
            code_hits=[],  # No HoloIndex results
            wsp_hits=[],
            candidate_paths=["src/fallback_path.py", "src/another_path.py"],
        )

        with patch(
            "modules.communication.moltbot_bridge.src.openclaw_execution_routes.build_execution_bundle"
        ) as mock_build:
            mock_build.return_value = test_bundle
            with patch(
                "modules.communication.moltbot_bridge.src.openclaw_execution_routes._try_memory_query",
                return_value=None,
            ):
                with patch(
                    "modules.communication.moltbot_bridge.src.openclaw_execution_routes._try_schedule_command",
                    return_value=None,
                ):
                    response = await execute_query(mock_dae, mock_intent)

        # Response should include candidate paths as fallback
        assert "Related paths from prior work" in response
        assert "src/fallback_path.py" in response
