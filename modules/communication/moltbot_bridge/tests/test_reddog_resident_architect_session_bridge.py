"""Tests for REDDOG_EXTENSION_TO_RESIDENT_ARCHITECT_SESSION_RUNTIME_PHASE1."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace


REPO_ROOT = Path(__file__).resolve().parents[4]
BRIDGE_PATH = REPO_ROOT / "scripts" / "reddog_resident_architect_session_once.py"
SPEC = importlib.util.spec_from_file_location("reddog_resident_architect_session_once", BRIDGE_PATH)
assert SPEC and SPEC.loader
bridge = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bridge)


def _accepted_result():
    initial = SimpleNamespace(
        status="READY",
        snapshot_receipt_id="sha256:snapshot",
        swarm_id="sha256:swarm",
    )
    final = SimpleNamespace(
        status="READY",
        snapshot_receipt_id="sha256:final",
        backend_architect_determination_action="FIX",
        backend_architect_determination_next_slice="REDDOG_NEXT_PHASE1",
        backend_architect_determination_id="sha256:architect",
        backend_architect_determination_queue_candidate_count=1,
    )
    return SimpleNamespace(
        accepted=True,
        status="READONLY_AUDIT_RESEARCH_DECISION_E2E_ACCEPT",
        initial_bootstrap=initial,
        final_bootstrap=final,
        task_runs=(SimpleNamespace(persist_accepted=True), SimpleNamespace(persist_accepted=True)),
        readonly_audit_tasks_enqueued=True,
        readonly_audit_tasks_executed=True,
        rejection_reasons=(),
        no_shell_command_executed=True,
        no_repo_mutation_performed=True,
        no_holoindex_reindex_performed=True,
        no_hermes_dispatch_performed=True,
        no_worktree_operation_performed=True,
        no_pr_created=True,
        no_pattern_memory_promotion_performed=True,
        no_live_foundup_enqueue_performed=True,
        coding_worker_spawned=False,
    )


def test_resident_architect_session_requires_explicit_request() -> None:
    result = bridge._result({})

    assert result["decision"] == bridge.RESIDENT_ARCHITECT_SESSION_REJECT
    assert result["resident_backend_invoked"] is False
    assert result["rejection_reasons"] == ["explicit_resident_architect_session_request_missing"]
    assert result["no_repo_mutation_performed"] is True
    assert result["no_holoindex_reindex_performed"] is True


def test_resident_architect_session_summarizes_e2e_runtime(monkeypatch) -> None:
    calls = []

    def fake_e2e(**kwargs):
        calls.append(kwargs)
        return _accepted_result()

    monkeypatch.setattr(bridge, "run_reddog_readonly_audit_research_decision_e2e", fake_e2e)
    result = bridge._result(
        {
            "explicit_resident_architect_session_requested": True,
            "repo_root": ".",
            "work_focus": "audit resident loop",
            "work_state_path": "O:/state/work_state.json",
            "holoindex_receipt_path": "O:/state/holo.json",
            "holoindex_ssd_path": "E:/HoloIndex",
            "timeout_seconds": 13,
        }
    )

    assert calls and calls[0]["requested_operation"] == "extension_resident_architect_session"
    assert calls[0]["prompt_text"] == "audit resident loop"
    assert calls[0]["timeout_seconds"] == 13
    assert result["decision"] == bridge.RESIDENT_ARCHITECT_SESSION_ACCEPT
    assert result["accepted"] is True
    assert result["resident_backend_invoked"] is True
    assert result["snapshot_id"] == "sha256:snapshot"
    assert result["swarm_id"] == "sha256:swarm"
    assert result["task_count"] == 2
    assert result["reports_persisted"] == 2
    assert result["architect_action"] == "FIX"
    assert result["architect_next_slice"] == "REDDOG_NEXT_PHASE1"
    assert result["queue_candidate_count"] == 1
    assert result["no_repo_mutation_performed"] is True
    assert result["no_holoindex_reindex_performed"] is True
    assert result["coding_worker_spawned"] is False


def test_resident_architect_session_bridge_failure_fails_closed(monkeypatch) -> None:
    def fail_e2e(**kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(bridge, "run_reddog_readonly_audit_research_decision_e2e", fail_e2e)
    result = bridge._result({"explicit_resident_architect_session_requested": True})

    assert result["decision"] == bridge.RESIDENT_ARCHITECT_SESSION_REJECT
    assert result["resident_backend_invoked"] is True
    assert result["no_repo_mutation_performed"] is True
    assert result["no_holoindex_reindex_performed"] is True
