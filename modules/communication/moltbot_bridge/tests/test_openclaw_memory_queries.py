"""Tests for OpenClaw memory queries (P0: openclaw_memory_queries)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from modules.communication.moltbot_bridge.src.openclaw_execution_routes import (
    _try_memory_query,
    _query_decisions,
    _query_unresolved_work,
    _query_recent_sessions,
)


@pytest.fixture
def mock_dae(tmp_path):
    """Create a mock DAE with workspace directory."""
    dae = MagicMock()
    dae.repo_root = tmp_path

    # Create workspace structure
    workspace = tmp_path / "modules/communication/moltbot_bridge/workspace"
    memory_dir = workspace / "memory"
    reports_dir = workspace / "reports"
    memory_dir.mkdir(parents=True)
    reports_dir.mkdir(parents=True)

    return dae


class TestDecisionQuery:
    """Tests for 'what did we decide about X' queries."""

    def test_decision_query_finds_matching_memory(self, mock_dae, tmp_path):
        """Decision query returns matches with provenance."""
        memory_dir = tmp_path / "modules/communication/moltbot_bridge/workspace/memory"
        memory_dir.mkdir(parents=True, exist_ok=True)

        # Create a memory note about hermes
        (memory_dir / "2026-03-23-hermes-decision.md").write_text(
            "# Hermes Native Roadmap\n\n"
            "Decision:\n"
            "- do not adopt Hermes runtime ownership\n"
            "- do adopt Hermes patterns natively\n",
            encoding="utf-8",
        )

        result = _try_memory_query(mock_dae, "what did we decide about hermes?")

        assert result is not None
        assert "hermes" in result.lower()
        assert "Decision" in result or "decision" in result.lower()
        # Handle both Unix and Windows path separators
        assert "2026-03-23-hermes-decision.md" in result

    def test_decision_query_insufficient_evidence(self, mock_dae, tmp_path):
        """Decision query returns explicit insufficient-evidence response."""
        memory_dir = tmp_path / "modules/communication/moltbot_bridge/workspace/memory"
        memory_dir.mkdir(parents=True, exist_ok=True)

        # Create unrelated memory note
        (memory_dir / "2026-03-23-unrelated.md").write_text(
            "# Unrelated Topic\n\nSome other content.\n",
            encoding="utf-8",
        )

        result = _try_memory_query(mock_dae, "what did we decide about blockchain layer?")

        assert result is not None
        assert "No decisions found" in result
        assert "blockchain layer" in result
        assert "insufficient" in result.lower() or "no matching" in result.lower()


class TestUnresolvedWorkQuery:
    """Tests for 'show unresolved work' queries."""

    def test_unresolved_work_from_queue(self, mock_dae, tmp_path):
        """Unresolved work query reads from native queue."""
        reports_dir = tmp_path / "modules/communication/moltbot_bridge/workspace/reports"
        reports_dir.mkdir(parents=True, exist_ok=True)

        queue_status = {
            "next_ready": [
                {"title": "Expose memory queries", "priority": "P0"}
            ],
            "next_audit": [
                {"title": "Session recall search", "priority": "P0"}
            ],
        }
        (reports_dir / "openclaw_native_execution_queue_status.json").write_text(
            json.dumps(queue_status), encoding="utf-8"
        )

        result = _try_memory_query(mock_dae, "show unresolved work")

        assert result is not None
        assert "Unresolved Work" in result
        assert "Expose memory queries" in result
        assert "P0" in result
        assert "native_queue" in result

    def test_unresolved_work_from_self_research(self, mock_dae, tmp_path):
        """Unresolved work includes self-research update candidates."""
        reports_dir = tmp_path / "modules/communication/moltbot_bridge/workspace/reports"
        reports_dir.mkdir(parents=True, exist_ok=True)

        # Empty queue
        (reports_dir / "openclaw_native_execution_queue_status.json").write_text(
            json.dumps({"next_ready": [], "next_audit": []}), encoding="utf-8"
        )

        # Self-research with candidates
        research_status = {
            "update_candidates": [
                {"title": "Review grant changes", "mps": {"priority": "P1"}}
            ]
        }
        (reports_dir / "openclaw_self_research_status.json").write_text(
            json.dumps(research_status), encoding="utf-8"
        )

        result = _try_memory_query(mock_dae, "show pending work")

        assert result is not None
        assert "Review grant changes" in result
        assert "self_research" in result

    def test_unresolved_work_empty(self, mock_dae, tmp_path):
        """Unresolved work returns explicit empty response when nothing pending."""
        reports_dir = tmp_path / "modules/communication/moltbot_bridge/workspace/reports"
        reports_dir.mkdir(parents=True, exist_ok=True)

        # Empty queue and research
        (reports_dir / "openclaw_native_execution_queue_status.json").write_text(
            json.dumps({"next_ready": [], "next_audit": []}), encoding="utf-8"
        )
        (reports_dir / "openclaw_self_research_status.json").write_text(
            json.dumps({"update_candidates": []}), encoding="utf-8"
        )

        result = _try_memory_query(mock_dae, "what unresolved work is left?")

        assert result is not None
        assert "No unresolved work found" in result


class TestRecentSessionsQuery:
    """Tests for 'show recent sessions' queries."""

    def test_recent_sessions_lists_memory_notes(self, mock_dae, tmp_path):
        """Recent sessions query lists workspace memory notes."""
        memory_dir = tmp_path / "modules/communication/moltbot_bridge/workspace/memory"
        memory_dir.mkdir(parents=True, exist_ok=True)

        (memory_dir / "2026-03-23-hermes.md").write_text(
            "# Hermes Evaluation\n\nContent.\n", encoding="utf-8"
        )
        (memory_dir / "2026-03-22-supervisor.md").write_text(
            "# Supervisor Unification\n\nContent.\n", encoding="utf-8"
        )

        result = _try_memory_query(mock_dae, "show recent sessions")

        assert result is not None
        assert "Recent Sessions" in result
        assert "2026-03-23" in result
        assert "2026-03-22" in result
        assert "hermes" in result.lower()

    def test_recent_sessions_empty_memory(self, mock_dae, tmp_path):
        """Recent sessions returns explicit message when memory empty."""
        memory_dir = tmp_path / "modules/communication/moltbot_bridge/workspace/memory"
        memory_dir.mkdir(parents=True, exist_ok=True)
        # Empty directory

        result = _try_memory_query(mock_dae, "show high-value sessions")

        assert result is not None
        assert "No recent sessions found" in result


class TestMemoryQueryIntentDetection:
    """Tests for memory query intent detection patterns."""

    def test_detects_decision_query_variants(self, mock_dae, tmp_path):
        """Various decision query phrasings are detected."""
        memory_dir = tmp_path / "modules/communication/moltbot_bridge/workspace/memory"
        memory_dir.mkdir(parents=True, exist_ok=True)

        variants = [
            "what did we decide about hermes",
            "what did we decide on blockchain",
            "what did we decide for the architecture",
            "what did we decide regarding memory",
        ]

        for query in variants:
            result = _try_memory_query(mock_dae, query)
            assert result is not None, f"Failed to detect: {query}"
            assert "No decisions found" in result or "Decisions related to" in result

    def test_detects_unresolved_work_variants(self, mock_dae, tmp_path):
        """Various unresolved work phrasings are detected."""
        reports_dir = tmp_path / "modules/communication/moltbot_bridge/workspace/reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        (reports_dir / "openclaw_native_execution_queue_status.json").write_text(
            json.dumps({"next_ready": [], "next_audit": []}), encoding="utf-8"
        )

        variants = [
            "show unresolved work",
            "list pending tasks",
            "what remaining work is there",
            "show open items",
        ]

        for query in variants:
            result = _try_memory_query(mock_dae, query)
            assert result is not None, f"Failed to detect: {query}"

    def test_non_memory_query_returns_none(self, mock_dae):
        """Non-memory queries return None for fallthrough."""
        queries = [
            "search for test files",
            "what is the weather",
            "explain WSP 97",
        ]

        for query in queries:
            result = _try_memory_query(mock_dae, query)
            assert result is None, f"Should not match: {query}"
