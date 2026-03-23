"""Tests for Memory Nudge Engine (P0: memory_nudge_engine)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from modules.communication.moltbot_bridge.src.memory_nudge_engine import (
    MemoryNudgeEngine,
    NudgeEvent,
    emit_memory_nudges,
    scan_nudge_events,
)


@pytest.fixture
def tmp_workspace(tmp_path):
    """Create temporary workspace structure."""
    memory_dir = tmp_path / "modules/communication/moltbot_bridge/workspace/memory"
    reports_dir = tmp_path / "modules/communication/moltbot_bridge/workspace/reports"
    memory_dir.mkdir(parents=True)
    reports_dir.mkdir(parents=True)
    return {
        "repo_root": tmp_path,
        "memory_dir": memory_dir,
        "reports_dir": reports_dir,
    }


class TestNudgeEvent:
    """Tests for NudgeEvent dataclass."""

    def test_signature_auto_generated(self):
        """Signature is computed from trigger_type, title, provenance."""
        event = NudgeEvent(
            trigger_type="test_trigger",
            title="Test Title",
            summary="Test summary",
            provenance="test/path.json",
        )
        assert event.signature
        assert len(event.signature) == 16

    def test_signature_stable(self):
        """Same inputs produce same signature."""
        event1 = NudgeEvent(
            trigger_type="test_trigger",
            title="Test Title",
            summary="Summary 1",
            provenance="test/path.json",
        )
        event2 = NudgeEvent(
            trigger_type="test_trigger",
            title="Test Title",
            summary="Summary 2",  # Different summary
            provenance="test/path.json",
        )
        assert event1.signature == event2.signature

    def test_signature_differs_on_different_inputs(self):
        """Different trigger/title/provenance produces different signature."""
        event1 = NudgeEvent(
            trigger_type="trigger_a",
            title="Title",
            summary="Summary",
            provenance="path.json",
        )
        event2 = NudgeEvent(
            trigger_type="trigger_b",
            title="Title",
            summary="Summary",
            provenance="path.json",
        )
        assert event1.signature != event2.signature


class TestMemoryNudgeEngine:
    """Tests for MemoryNudgeEngine."""

    def test_creates_note_on_qualifying_event(self, tmp_workspace):
        """Engine creates note for high-value event."""
        engine = MemoryNudgeEngine(
            repo_root=tmp_workspace["repo_root"],
            memory_dir=tmp_workspace["memory_dir"],
            reports_dir=tmp_workspace["reports_dir"],
        )

        event = NudgeEvent(
            trigger_type="test_trigger",
            title="Test Event",
            summary="A test event summary.",
            provenance="test/source.json",
            priority="P1",
        )

        created = engine.emit_nudges([event])

        assert len(created) == 1
        assert created[0].exists()
        content = created[0].read_text(encoding="utf-8")
        assert "Test Event" in content
        assert "test_trigger" in content
        assert "test/source.json" in content
        assert "P1" in content

    def test_dedupes_repeated_event(self, tmp_workspace):
        """Engine does not duplicate notes for same event signature."""
        engine = MemoryNudgeEngine(
            repo_root=tmp_workspace["repo_root"],
            memory_dir=tmp_workspace["memory_dir"],
            reports_dir=tmp_workspace["reports_dir"],
        )

        event = NudgeEvent(
            trigger_type="test_trigger",
            title="Duplicate Event",
            summary="This should only create one note.",
            provenance="test/source.json",
        )

        # First emission
        created1 = engine.emit_nudges([event])
        assert len(created1) == 1

        # Second emission (same signature)
        created2 = engine.emit_nudges([event])
        assert len(created2) == 0

        # Verify only one file exists
        notes = list(tmp_workspace["memory_dir"].glob("*-nudge-*.md"))
        assert len(notes) == 1

    def test_dedupes_from_existing_files(self, tmp_workspace):
        """Engine loads existing signatures and dedupes against them."""
        # Pre-create a nudge note
        existing_sig = "abcd1234abcd1234"
        existing_note = tmp_workspace["memory_dir"] / f"2026-03-23-nudge-{existing_sig}.md"
        existing_note.write_text("# Existing Note\n", encoding="utf-8")

        engine = MemoryNudgeEngine(
            repo_root=tmp_workspace["repo_root"],
            memory_dir=tmp_workspace["memory_dir"],
            reports_dir=tmp_workspace["reports_dir"],
        )

        # Event with same signature should be skipped
        event = NudgeEvent(
            trigger_type="test",
            title="Test",
            summary="Test",
            provenance="test",
            signature=existing_sig,
        )

        created = engine.emit_nudges([event])
        assert len(created) == 0

    def test_ignores_low_signal_event(self, tmp_workspace):
        """Engine ignores events with P3/P4 priority from self-research."""
        reports_dir = tmp_workspace["reports_dir"]

        # Create self-research status with low-priority candidates
        status = {
            "update_candidates": [
                {"title": "Low priority item", "mps": {"priority": "P3", "reasoning": "Not urgent"}},
            ]
        }
        (reports_dir / "openclaw_self_research_status.json").write_text(
            json.dumps(status), encoding="utf-8"
        )

        engine = MemoryNudgeEngine(
            repo_root=tmp_workspace["repo_root"],
            memory_dir=tmp_workspace["memory_dir"],
            reports_dir=reports_dir,
        )

        events = engine.scan_all()

        # Should not include P3 items
        assert not any(e.trigger_type == "self_research_change" for e in events)

    def test_note_includes_provenance(self, tmp_workspace):
        """Created note includes provenance field."""
        engine = MemoryNudgeEngine(
            repo_root=tmp_workspace["repo_root"],
            memory_dir=tmp_workspace["memory_dir"],
            reports_dir=tmp_workspace["reports_dir"],
        )

        event = NudgeEvent(
            trigger_type="grant_watchlist_change",
            title="Test Grant",
            summary="Grant requires review.",
            provenance="reports/web3_grants_0102_watchlist_status.json",
            priority="P0",
        )

        created = engine.emit_nudges([event])
        assert len(created) == 1

        content = created[0].read_text(encoding="utf-8")
        assert "**Provenance**:" in content
        assert "reports/web3_grants_0102_watchlist_status.json" in content


class TestSelfResearchTrigger:
    """Tests for self-research change detection."""

    def test_detects_high_priority_update_candidate(self, tmp_workspace):
        """Detects P0/P1 update candidates from self-research."""
        reports_dir = tmp_workspace["reports_dir"]

        status = {
            "update_candidates": [
                {
                    "title": "Critical update needed",
                    "mps": {"priority": "P0", "reasoning": "Security fix", "total_mps": 18},
                },
            ]
        }
        (reports_dir / "openclaw_self_research_status.json").write_text(
            json.dumps(status), encoding="utf-8"
        )

        engine = MemoryNudgeEngine(
            repo_root=tmp_workspace["repo_root"],
            memory_dir=tmp_workspace["memory_dir"],
            reports_dir=reports_dir,
        )

        events = engine._scan_self_research_changes()

        assert len(events) == 1
        assert events[0].trigger_type == "self_research_change"
        assert "Critical update" in events[0].title
        assert events[0].priority == "P0"

    def test_detects_new_autonomous_tasks(self, tmp_workspace):
        """Detects new autonomous tasks queued."""
        reports_dir = tmp_workspace["reports_dir"]

        status = {
            "update_candidates": [],
            "autonomous_tasks": {"new_tasks_queued": 3},
        }
        (reports_dir / "openclaw_self_research_status.json").write_text(
            json.dumps(status), encoding="utf-8"
        )

        engine = MemoryNudgeEngine(
            repo_root=tmp_workspace["repo_root"],
            memory_dir=tmp_workspace["memory_dir"],
            reports_dir=reports_dir,
        )

        events = engine._scan_self_research_changes()

        assert len(events) == 1
        assert "3 new autonomous task(s)" in events[0].title


class TestGrantWatchlistTrigger:
    """Tests for grant watchlist change detection."""

    def test_detects_human_gate_required(self, tmp_workspace):
        """Detects items requiring human gate."""
        reports_dir = tmp_workspace["reports_dir"]

        watchlist = {
            "items": [
                {
                    "id": "grant_001",
                    "title": "Web3 Foundation Grant",
                    "human_gate_required": True,
                    "deadline": "2026-04-01",
                },
            ]
        }
        (reports_dir / "web3_grants_0102_watchlist_status.json").write_text(
            json.dumps(watchlist), encoding="utf-8"
        )

        engine = MemoryNudgeEngine(
            repo_root=tmp_workspace["repo_root"],
            memory_dir=tmp_workspace["memory_dir"],
            reports_dir=reports_dir,
        )

        events = engine._scan_grant_watchlist_changes()

        assert len(events) == 1
        assert events[0].trigger_type == "grant_watchlist_change"
        assert "Human gate required" in events[0].title
        assert events[0].priority == "P0"


class TestWorktreePressureTrigger:
    """Tests for worktree pressure detection."""

    def test_detects_high_audit_backlog(self, tmp_workspace):
        """Detects queue backlog pressure."""
        reports_dir = tmp_workspace["reports_dir"]

        queue_status = {
            "queue_count": 8,
            "audit_required_count": 6,
        }
        (reports_dir / "openclaw_native_execution_queue_status.json").write_text(
            json.dumps(queue_status), encoding="utf-8"
        )

        engine = MemoryNudgeEngine(
            repo_root=tmp_workspace["repo_root"],
            memory_dir=tmp_workspace["memory_dir"],
            reports_dir=reports_dir,
        )

        events = engine._scan_worktree_pressure()

        assert len(events) == 1
        assert events[0].trigger_type == "worktree_pressure"
        assert "6 items need audit" in events[0].title

    def test_ignores_low_audit_count(self, tmp_workspace):
        """Does not trigger on low audit counts."""
        reports_dir = tmp_workspace["reports_dir"]

        queue_status = {
            "queue_count": 3,
            "audit_required_count": 2,
        }
        (reports_dir / "openclaw_native_execution_queue_status.json").write_text(
            json.dumps(queue_status), encoding="utf-8"
        )

        engine = MemoryNudgeEngine(
            repo_root=tmp_workspace["repo_root"],
            memory_dir=tmp_workspace["memory_dir"],
            reports_dir=reports_dir,
        )

        events = engine._scan_worktree_pressure()

        assert len(events) == 0


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    def test_scan_nudge_events_returns_list(self, tmp_workspace):
        """scan_nudge_events returns a list of events."""
        # Create wre_core reports dir (for escalations scanner)
        wre_reports = tmp_workspace["repo_root"] / "modules/infrastructure/wre_core/reports"
        wre_reports.mkdir(parents=True, exist_ok=True)

        events = scan_nudge_events(repo_root=tmp_workspace["repo_root"])
        assert isinstance(events, list)

    def test_emit_memory_nudges_returns_paths(self, tmp_workspace):
        """emit_memory_nudges returns list of created paths."""
        # Create wre_core reports dir (for escalations scanner)
        wre_reports = tmp_workspace["repo_root"] / "modules/infrastructure/wre_core/reports"
        wre_reports.mkdir(parents=True, exist_ok=True)

        # Create a triggering condition
        reports_dir = tmp_workspace["reports_dir"]
        status = {
            "update_candidates": [
                {"title": "Test item", "mps": {"priority": "P0", "reasoning": "Test"}},
            ]
        }
        (reports_dir / "openclaw_self_research_status.json").write_text(
            json.dumps(status), encoding="utf-8"
        )

        result = emit_memory_nudges(repo_root=tmp_workspace["repo_root"])
        assert isinstance(result, list)
        # Should have created one note for the P0 item
        assert len(result) >= 1
