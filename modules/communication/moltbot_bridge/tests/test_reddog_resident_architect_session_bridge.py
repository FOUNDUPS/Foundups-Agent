"""Tests for REDDOG_EXTENSION_TO_RESIDENT_ARCHITECT_SESSION_RUNTIME_PHASE1."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

from modules.communication.moltbot_bridge.src.reddog_grounded_target_assignment_continuity import (
    SCHEMA_VERSION as GROUNDING_SCHEMA_VERSION,
    canonical_digest as grounding_digest,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
BRIDGE_PATH = REPO_ROOT / "scripts" / "reddog_resident_architect_session_once.py"
SPEC = importlib.util.spec_from_file_location("reddog_resident_architect_session_once", BRIDGE_PATH)
assert SPEC and SPEC.loader
bridge = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bridge)


def _grounding_receipt(work_focus: str) -> dict:
    typed = {
        "repo_file_targets": ["modules/communication/moltbot_bridge/src/reddog_operational_context_snapshot.py"],
        "semantic_targets": [],
        "external_research_targets": [],
        "quoted_reference_blocks_count": 0,
        "quoted_reference_blocks_digest": grounding_digest([]),
    }
    value = {
        "schema_version": GROUNDING_SCHEMA_VERSION,
        "source_surface": "editor_thin_client",
        "work_focus_digest": grounding_digest({"work_focus": work_focus}),
        "typed_targets": typed,
        "typed_targets_digest": grounding_digest(typed),
        "grounding_preflight_applied": True,
        "grounding_preflight_passed": True,
        "grounding_preflight_rejection_reasons": [],
        "grounding_target_universe_required": True,
        "repo_file_targets_count": 1,
        "semantic_targets_count": 0,
        "external_research_targets_count": 0,
        "quoted_reference_blocks_count": 0,
        "semantic_target_coverage": [],
        "semantic_target_coverage_digest": grounding_digest({"semantic_target_coverage": []}),
        "target_recall_ok": True,
        "required_targets_missing": [],
        "direct_read_paths": [],
        "holoindex_owner_query_ok": False,
        "holoindex_freshness": "UNKNOWN",
        "holoindex_generation_id": "",
        "holoindex_freshness_receipt_digest": "",
        "holoindex_repo_head_sha": "",
        "holoindex_query_receipt_id": "",
        "holoindex_index_gap_detected": False,
        "no_holoindex_reindex_performed": True,
    }
    value["receipt_id"] = grounding_digest(value)
    return value


def _accepted_result():
    return SimpleNamespace(
        accepted=True,
        status="DETERMINED",
        canonical_resident_cycle_used=True,
        intent_id="sha256:intent",
        cycle_id="sha256:cycle",
        snapshot_id="sha256:snapshot",
        swarm_id="sha256:swarm",
        task_ids=("task-a", "task-b"),
        task_status_counts={"completed": 2},
        openclaw_claim_count=2,
        duplicate_intent_reused=False,
        recovered_existing_cycle=False,
        architect_action="FIX",
        architect_next_slice="REDDOG_NEXT_PHASE1",
        determination_id="sha256:architect",
        queue_candidate_count=1,
        record_revision=7,
        intent_digest="sha256:intent-digest",
        rejection_reasons=(),
        client_no_shell_command_executed=True,
        client_no_repo_mutation_performed=True,
        client_no_holoindex_reindex_performed=True,
        client_no_hermes_execution_performed=True,
        client_no_worktree_operation_performed=True,
        client_no_pr_created=True,
    )


def _bound_model_runtime_receipts() -> tuple[dict, dict, str]:
    return (
        {"receipt_id": "sha256:audit-bound", "binding_state": "BOUND"},
        {"receipt_id": "sha256:architect-bound", "binding_state": "BOUND"},
        "",
    )


def test_resident_architect_session_requires_explicit_request() -> None:
    result = bridge._result({})

    assert result["decision"] == bridge.RESIDENT_ARCHITECT_SESSION_REJECT
    assert result["resident_backend_invoked"] is False
    assert result["rejection_reasons"] == ["explicit_resident_architect_session_request_missing"]
    assert result["no_repo_mutation_performed"] is True
    assert result["no_holoindex_reindex_performed"] is True


def test_resident_architect_session_summarizes_durable_cycle_runtime(monkeypatch) -> None:
    calls = []
    grounding = _grounding_receipt("audit resident loop")

    class _Client:
        def __init__(self, **kwargs):
            calls.append({"init": kwargs})

        def submit(self, intent):
            calls.append({"intent": dict(intent)})
            return _accepted_result()

    monkeypatch.setenv("REDDOG_AUTHENTICATED_PRINCIPAL_ID", "principal-012")
    monkeypatch.setenv("REDDOG_AUTHORIZED_FOUNDUP_IDS", "foundups_agent")
    monkeypatch.setattr(
        bridge,
        "load_resident_model_runtime_bindings",
        lambda _repo_root: _bound_model_runtime_receipts(),
    )
    monkeypatch.setattr(bridge, "RedDogResidentArchitectClient", _Client)
    result = bridge._result(
        {
            "explicit_resident_architect_session_requested": True,
            "red_dog_intent": {
                "schema_version": "reddog_intent.v2",
                "intent_id": "sha256:intent",
                "origin": "extension",
                "source_surface": "editor_thin_client",
                "principal_ref": "principal-012",
                "foundup_id": "foundups_agent",
                "work_focus": "audit resident loop",
                "grounding_receipt": grounding,
                "submits_executable_authority": False,
            },
            "grounding_receipt_id": grounding["receipt_id"],
            "repo_root": ".",
            "work_focus": "audit resident loop",
            "work_state_path": "O:/state/work_state.json",
            "holoindex_receipt_path": "O:/state/holo.json",
            "holoindex_ssd_path": "E:/HoloIndex",
            "timeout_seconds": 13,
            "breadcrumbs": [{"breadcrumb_id": "crumb-1"}],
            "brain_state": {"available": True, "signature_digest": "sha256:brain"},
            "workspace_memory_notes": [{"note_id": "note-1"}],
            "memex_snapshot_supply": {
                "foundup_id": "foundups_agent",
                "identity": {"foundup_id": "foundups_agent", "name": "Foundups Agent"},
                "roadmap_state": {"foundup_id": "foundups_agent", "roadmap_id": "r1"},
            },
        }
    )

    runtime = calls[0]["init"]["runtime_defaults"]
    assert calls[0]["init"]["authenticated_principal_id"] == "principal-012"
    assert calls[0]["init"]["authorized_foundup_ids"] == ("foundups_agent",)
    assert calls[0]["init"]["transport"] == "editor"
    assert calls[1]["intent"]["intent_id"] == "sha256:intent"
    assert runtime["requested_operation"] == "extension_resident_architect_session"
    assert runtime["prompt_text"] == "audit resident loop"
    assert runtime["timeout_seconds"] == 13
    assert runtime["breadcrumbs"] == ({"breadcrumb_id": "crumb-1"},)
    assert runtime["brain_state"] == {"available": True, "signature_digest": "sha256:brain"}
    assert runtime["workspace_memory_notes"] == ({"note_id": "note-1"},)
    assert runtime["memex_snapshot_supply_config"]["foundup_id"] == "foundups_agent"
    assert (
        runtime["audit_model_runtime_binding_receipt"]["receipt_id"]
        == "sha256:audit-bound"
    )
    assert (
        runtime["architect_model_runtime_binding_receipt"]["receipt_id"]
        == "sha256:architect-bound"
    )
    assert result["decision"] == bridge.RESIDENT_ARCHITECT_SESSION_ACCEPT
    assert result["accepted"] is True
    assert result["resident_backend_invoked"] is True
    assert result["durable_agentdb_cycle"] is True
    assert result["cycle_id"] == "sha256:cycle"
    assert result["snapshot_id"] == "sha256:snapshot"
    assert result["swarm_id"] == "sha256:swarm"
    assert result["task_count"] == 2
    assert result["reports_persisted"] == 2
    assert result["openclaw_claim_count"] == 2
    assert result["architect_action"] == "FIX"
    assert result["architect_next_slice"] == "REDDOG_NEXT_PHASE1"
    assert result["queue_candidate_count"] == 1
    assert result["no_repo_mutation_performed"] is True
    assert result["no_holoindex_reindex_performed"] is True
    assert result["coding_worker_spawned"] is False


def test_resident_architect_session_bridge_failure_fails_closed(monkeypatch) -> None:
    class _Client:
        def __init__(self, **kwargs):
            pass

        def submit(self, intent):
            raise RuntimeError("boom")

    monkeypatch.setenv("REDDOG_AUTHENTICATED_PRINCIPAL_ID", "principal-012")
    monkeypatch.setenv("REDDOG_AUTHORIZED_FOUNDUP_IDS", "foundups_agent")
    monkeypatch.setattr(
        bridge,
        "load_resident_model_runtime_bindings",
        lambda _repo_root: _bound_model_runtime_receipts(),
    )
    monkeypatch.setattr(bridge, "RedDogResidentArchitectClient", _Client)
    grounding = _grounding_receipt("audit resident loop")
    result = bridge._result(
        {
            "explicit_resident_architect_session_requested": True,
            "red_dog_intent": {
                "schema_version": "reddog_intent.v2",
                "intent_id": "sha256:intent",
                "origin": "extension",
                "source_surface": "editor_thin_client",
                "principal_ref": "principal-012",
                "foundup_id": "foundups_agent",
                "work_focus": "audit resident loop",
                "grounding_receipt": grounding,
                "submits_executable_authority": False,
            },
            "grounding_receipt_id": grounding["receipt_id"],
            "work_focus": "audit resident loop",
        }
    )

    assert result["decision"] == bridge.RESIDENT_ARCHITECT_SESSION_REJECT
    assert result["resident_backend_invoked"] is True
    assert result["no_repo_mutation_performed"] is True
    assert result["no_holoindex_reindex_performed"] is True


def test_resident_architect_session_rejects_unbound_models_before_client(monkeypatch) -> None:
    client_calls = []

    class _Client:
        def __init__(self, **kwargs):
            client_calls.append(kwargs)

    monkeypatch.setenv("REDDOG_AUTHENTICATED_PRINCIPAL_ID", "principal-012")
    monkeypatch.setenv("REDDOG_AUTHORIZED_FOUNDUP_IDS", "foundups_agent")
    monkeypatch.setattr(
        bridge,
        "load_resident_model_runtime_bindings",
        lambda _repo_root: (
            None,
            None,
            "audit_model_runtime_binding_receipt_id_mismatch",
        ),
    )
    monkeypatch.setattr(bridge, "RedDogResidentArchitectClient", _Client)
    grounding = _grounding_receipt("audit resident loop")

    result = bridge._result(
        {
            "explicit_resident_architect_session_requested": True,
            "red_dog_intent": {
                "schema_version": "reddog_intent.v2",
                "intent_id": "sha256:intent",
                "origin": "extension",
                "source_surface": "editor_thin_client",
                "principal_ref": "principal-012",
                "foundup_id": "foundups_agent",
                "work_focus": "audit resident loop",
                "grounding_receipt": grounding,
                "submits_executable_authority": False,
            },
            "grounding_receipt_id": grounding["receipt_id"],
            "work_focus": "audit resident loop",
        }
    )

    assert result["accepted"] is False
    assert result["resident_backend_invoked"] is False
    assert result["rejection_reasons"] == [
        "audit_model_runtime_binding_receipt_id_mismatch"
    ]
    assert client_calls == []


def test_resident_architect_session_rejects_binding_loader_failure_before_client(
    monkeypatch,
) -> None:
    client_calls = []

    class _Client:
        def __init__(self, **kwargs):
            client_calls.append(kwargs)

    def _raise(_repo_root):
        raise OSError("private path detail")

    monkeypatch.setenv("REDDOG_AUTHENTICATED_PRINCIPAL_ID", "principal-012")
    monkeypatch.setenv("REDDOG_AUTHORIZED_FOUNDUP_IDS", "foundups_agent")
    monkeypatch.setattr(bridge, "load_resident_model_runtime_bindings", _raise)
    monkeypatch.setattr(bridge, "RedDogResidentArchitectClient", _Client)
    grounding = _grounding_receipt("audit resident loop")

    result = bridge._result(
        {
            "explicit_resident_architect_session_requested": True,
            "red_dog_intent": {
                "schema_version": "reddog_intent.v2",
                "intent_id": "sha256:intent",
                "origin": "extension",
                "source_surface": "editor_thin_client",
                "principal_ref": "principal-012",
                "foundup_id": "foundups_agent",
                "work_focus": "audit resident loop",
                "grounding_receipt": grounding,
                "submits_executable_authority": False,
            },
            "grounding_receipt_id": grounding["receipt_id"],
            "work_focus": "audit resident loop",
        }
    )

    assert result["accepted"] is False
    assert result["resident_backend_invoked"] is False
    assert result["rejection_reasons"] == ["model_runtime_binding_artifact_invalid"]
    assert client_calls == []


def test_resident_architect_session_requires_host_authenticated_scope(monkeypatch) -> None:
    monkeypatch.delenv("REDDOG_AUTHENTICATED_PRINCIPAL_ID", raising=False)
    monkeypatch.delenv("REDDOG_AUTHORIZED_FOUNDUP_IDS", raising=False)
    grounding = _grounding_receipt("audit resident loop")

    result = bridge._result(
        {
            "explicit_resident_architect_session_requested": True,
            "red_dog_intent": {
                "schema_version": "reddog_intent.v2",
                "intent_id": "sha256:intent",
                "origin": "extension",
                "source_surface": "editor_thin_client",
                "principal_ref": "principal-012",
                "foundup_id": "foundups_agent",
                "work_focus": "audit resident loop",
                "grounding_receipt": grounding,
                "submits_executable_authority": False,
            },
            "grounding_receipt_id": grounding["receipt_id"],
            "work_focus": "audit resident loop",
        }
    )

    assert result["accepted"] is False
    assert result["resident_backend_invoked"] is False
    assert result["rejection_reasons"] == ["resident_architect_authenticated_scope_missing"]
