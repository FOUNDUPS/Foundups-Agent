"""Tests for Memory Nudge Engine (P0: memory_nudge_engine)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.src import memory_nudge_engine
from modules.communication.moltbot_bridge.src.memory_nudge_engine import (
    MAX_SELF_AUDIT_ESCALATION_BYTES,
    MemoryNudgeEngine,
    NudgeEvent,
    _read_bounded_confined_text,
    emit_memory_nudges,
    scan_nudge_events,
)
from modules.infrastructure.wre_core.src.daemon_self_audit_loop import (
    resolve_daemon_self_audit_runtime_root,
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

    def test_reads_supervisor_escalations_from_external_runtime_root(
        self,
        tmp_workspace,
    ):
        runtime_root = tmp_workspace["repo_root"].parent / "daemon-runtime"
        runtime_root.mkdir()
        (runtime_root / "daemon_self_audit_escalations.jsonl").write_text(
            json.dumps(
                {
                    "signature": "repeated-provider-timeout",
                    "event_count": 5,
                    "recommended_fix": "inspect_provider_health",
                    "dispatch_result": "not_configured",
                }
            )
            + "\n",
            encoding="utf-8",
        )

        engine = MemoryNudgeEngine(
            repo_root=tmp_workspace["repo_root"],
            memory_dir=tmp_workspace["memory_dir"],
            reports_dir=tmp_workspace["reports_dir"],
            self_audit_runtime_root=runtime_root,
        )

        events = engine._scan_supervisor_escalations()

        assert len(events) == 1
        assert events[0].trigger_type == "supervisor_escalation"
        assert events[0].provenance == (
            "runtime:daemon_self_audit/daemon_self_audit_escalations.jsonl"
        )

    def test_ignores_obsolete_in_repo_supervisor_escalation_log(
        self,
        tmp_workspace,
    ):
        stale_root = (
            tmp_workspace["repo_root"]
            / "modules"
            / "infrastructure"
            / "wre_core"
            / "reports"
        )
        stale_root.mkdir(parents=True)
        (stale_root / "daemon_self_audit_escalations.jsonl").write_text(
            json.dumps(
                {
                    "signature": "stale-repository-event",
                    "event_count": 99,
                    "recommended_fix": "must_not_be_observed",
                    "dispatch_result": "legacy",
                }
            )
            + "\n",
            encoding="utf-8",
        )
        runtime_root = tmp_workspace["repo_root"].parent / "empty-runtime"

        engine = MemoryNudgeEngine(
            repo_root=tmp_workspace["repo_root"],
            memory_dir=tmp_workspace["memory_dir"],
            reports_dir=tmp_workspace["reports_dir"],
            self_audit_runtime_root=runtime_root,
        )

        assert engine._scan_supervisor_escalations() == []

    def test_rejects_self_audit_runtime_root_inside_repository(
        self,
        tmp_workspace,
    ):
        with pytest.raises(ValueError, match="inside_repo"):
            MemoryNudgeEngine(
                repo_root=tmp_workspace["repo_root"],
                memory_dir=tmp_workspace["memory_dir"],
                reports_dir=tmp_workspace["reports_dir"],
                self_audit_runtime_root=(
                    tmp_workspace["repo_root"] / "runtime" / "self-audit"
                ),
            )

    @pytest.mark.parametrize(
        ("explicit", "resident", "expected_suffix"),
        (
            ("", "", "daemon_self_audit"),
            ("", "resident-store", "resident-store/daemon_self_audit"),
            ("explicit-store", "resident-store", "explicit-store"),
        ),
    )
    def test_consumer_uses_shared_producer_runtime_root_resolution(
        self,
        tmp_workspace,
        monkeypatch,
        explicit,
        resident,
        expected_suffix,
    ):
        if explicit:
            monkeypatch.setenv("OPENCLAW_SELF_AUDIT_RUNTIME_ROOT", explicit)
        else:
            monkeypatch.delenv("OPENCLAW_SELF_AUDIT_RUNTIME_ROOT", raising=False)
        if resident:
            monkeypatch.setenv("REDDOG_RESIDENT_RUNTIME_ROOT", resident)
        else:
            monkeypatch.delenv("REDDOG_RESIDENT_RUNTIME_ROOT", raising=False)

        repo_root = tmp_workspace["repo_root"]
        producer_root = resolve_daemon_self_audit_runtime_root(repo_root)
        engine = MemoryNudgeEngine(
            repo_root=repo_root,
            memory_dir=tmp_workspace["memory_dir"],
            reports_dir=tmp_workspace["reports_dir"],
        )

        assert engine.self_audit_runtime_root == producer_root
        assert producer_root.as_posix().endswith(expected_suffix)

    def test_supervisor_escalation_read_is_bounded_and_fail_closed(
        self,
        tmp_workspace,
    ):
        runtime_root = tmp_workspace["repo_root"].parent / "bounded-runtime"
        runtime_root.mkdir()
        escalations_path = runtime_root / "daemon_self_audit_escalations.jsonl"
        with escalations_path.open("wb") as stream:
            stream.truncate(MAX_SELF_AUDIT_ESCALATION_BYTES + 1)
        engine = MemoryNudgeEngine(
            repo_root=tmp_workspace["repo_root"],
            memory_dir=tmp_workspace["memory_dir"],
            reports_dir=tmp_workspace["reports_dir"],
            self_audit_runtime_root=runtime_root,
        )

        assert engine._scan_supervisor_escalations() == []
        with pytest.raises(ValueError, match="size_limit"):
            _read_bounded_confined_text(
                escalations_path,
                allowed_root=runtime_root,
            )

    def test_supervisor_escalation_read_propagates_confined_reader_rejection(
        self,
        tmp_workspace,
        monkeypatch,
    ):
        runtime_root = tmp_workspace["repo_root"].parent / "changed-runtime"
        runtime_root.mkdir()
        escalations_path = runtime_root / "daemon_self_audit_escalations.jsonl"
        escalations_path.write_text('{"event_count": 5}\n', encoding="utf-8")
        monkeypatch.setattr(
            memory_nudge_engine,
            "secure_read_confined_text",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(
                ValueError("confined_read_target_changed")
            ),
        )

        with pytest.raises(ValueError, match="target_changed"):
            _read_bounded_confined_text(
                escalations_path,
                allowed_root=runtime_root,
            )

    def test_supervisor_escalation_scan_does_not_use_path_read_text(
        self,
        tmp_workspace,
        monkeypatch,
    ):
        runtime_root = tmp_workspace["repo_root"].parent / "descriptor-runtime"
        runtime_root.mkdir()
        (runtime_root / "daemon_self_audit_escalations.jsonl").write_text(
            json.dumps(
                {
                    "signature": "descriptor-confined",
                    "event_count": 5,
                }
            )
            + "\n",
            encoding="utf-8",
        )
        monkeypatch.setattr(
            Path,
            "read_text",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(
                AssertionError("unconfined Path.read_text must not be used")
            ),
        )
        engine = MemoryNudgeEngine(
            repo_root=tmp_workspace["repo_root"],
            memory_dir=tmp_workspace["memory_dir"],
            reports_dir=tmp_workspace["reports_dir"],
            self_audit_runtime_root=runtime_root,
        )

        assert len(engine._scan_supervisor_escalations()) == 1

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
        """Detects new autonomous tasks queued (live schema: list)."""
        reports_dir = tmp_workspace["reports_dir"]

        # Live schema: autonomous_tasks is a list
        status = {
            "update_candidates": [],
            "autonomous_tasks": [
                {"task_id": "task_1", "title": "Review grants", "created": True, "priority": "P1"},
                {"task_id": "task_2", "title": "Check ecosystem", "created": True, "priority": "P1"},
                {"task_id": "task_3", "title": "Stabilize errors", "created": True, "priority": "P2"},
            ],
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
        assert "3 autonomous task(s)" in events[0].title


class TestGrantWatchlistTrigger:
    """Tests for grant watchlist change detection."""

    def test_detects_changed_grants(self, tmp_workspace):
        """Detects changed grant pages requiring review."""
        reports_dir = tmp_workspace["reports_dir"]

        # Live schema: changed_count, changed_items at top level
        watchlist = {
            "generated_on": "2026-03-23T09:11:20.524604+00:00",
            "watch_count": 15,
            "changed_count": 3,
            "error_count": 0,
            "changed_items": ["BNB Chain Grants", "NEAR Ecosystem", "Starknet Grants"],
            "error_items": [],
            "items": [],
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
        assert "3 grant page(s) changed" in events[0].title
        assert events[0].priority == "P1"

    def test_detects_refresh_errors(self, tmp_workspace):
        """Detects watchlist refresh errors."""
        reports_dir = tmp_workspace["reports_dir"]

        watchlist = {
            "changed_count": 0,
            "error_count": 2,
            "changed_items": [],
            "error_items": ["Filecoin Grants", "Aleo Grants"],
            "items": [],
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
        assert "2 grant watchlist error(s)" in events[0].title
        assert events[0].priority == "P2"


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


class TestBreadcrumbRecording:
    """Tests for breadcrumb recording when nudges are emitted."""

    def test_emit_nudges_records_breadcrumb_when_enabled(self, tmp_workspace, monkeypatch):
        """When record_breadcrumbs=True, a breadcrumb is recorded for each nudge."""
        # Track breadcrumb calls
        breadcrumb_calls = []

        class MockAgentDB:
            def add_breadcrumb(self, **kwargs):
                breadcrumb_calls.append(kwargs)
                return 1

        # Patch AgentDB import
        import sys
        mock_module = type(sys)("mock_agent_db")
        mock_module.AgentDB = MockAgentDB
        monkeypatch.setitem(
            sys.modules,
            "modules.infrastructure.database.src.agent_db",
            mock_module,
        )

        engine = MemoryNudgeEngine(
            repo_root=tmp_workspace["repo_root"],
            memory_dir=tmp_workspace["memory_dir"],
            reports_dir=tmp_workspace["reports_dir"],
        )

        event = NudgeEvent(
            trigger_type="test_trigger",
            title="Test Event",
            summary="Test summary",
            provenance="test/source.json",
            priority="P1",
        )

        created = engine.emit_nudges([event], record_breadcrumbs=True)

        assert len(created) == 1
        assert len(breadcrumb_calls) == 1
        assert breadcrumb_calls[0]["action"] == "memory_nudge_emitted"
        assert breadcrumb_calls[0]["agent_id"] == "memory_nudge_engine"
        assert "test_trigger" in str(breadcrumb_calls[0]["data"])

    def test_emit_nudges_skips_breadcrumb_when_disabled(self, tmp_workspace, monkeypatch):
        """When record_breadcrumbs=False, no breadcrumb is recorded."""
        breadcrumb_calls = []

        class MockAgentDB:
            def add_breadcrumb(self, **kwargs):
                breadcrumb_calls.append(kwargs)
                return 1

        import sys
        mock_module = type(sys)("mock_agent_db")
        mock_module.AgentDB = MockAgentDB
        monkeypatch.setitem(
            sys.modules,
            "modules.infrastructure.database.src.agent_db",
            mock_module,
        )

        engine = MemoryNudgeEngine(
            repo_root=tmp_workspace["repo_root"],
            memory_dir=tmp_workspace["memory_dir"],
            reports_dir=tmp_workspace["reports_dir"],
        )

        event = NudgeEvent(
            trigger_type="test_trigger",
            title="Test Event",
            summary="Test summary",
            provenance="test/source.json",
        )

        created = engine.emit_nudges([event], record_breadcrumbs=False)

        assert len(created) == 1
        assert len(breadcrumb_calls) == 0

    def test_emit_memory_nudges_convenience_passes_breadcrumb_flag(self, tmp_workspace):
        """Convenience function passes record_breadcrumbs to engine."""
        # Create wre_core reports dir
        wre_reports = tmp_workspace["repo_root"] / "modules/infrastructure/wre_core/reports"
        wre_reports.mkdir(parents=True, exist_ok=True)

        # Create triggering condition
        status = {
            "update_candidates": [
                {"title": "Test", "mps": {"priority": "P0", "reasoning": "Test"}},
            ]
        }
        (tmp_workspace["reports_dir"] / "openclaw_self_research_status.json").write_text(
            json.dumps(status), encoding="utf-8"
        )

        # Just verify it doesn't error with record_breadcrumbs=True
        # (AgentDB import may fail in test environment, but that's OK - graceful degradation)
        result = emit_memory_nudges(
            repo_root=tmp_workspace["repo_root"],
            record_breadcrumbs=True,
        )
        assert isinstance(result, list)
