"""Tests for the transport-neutral resident RedDog client."""

from __future__ import annotations

import ast
from pathlib import Path

from modules.communication.moltbot_bridge.src.reddog_grounded_target_assignment_continuity import (
    SCHEMA_VERSION as GROUNDING_SCHEMA_VERSION,
    canonical_digest,
)
from modules.communication.moltbot_bridge.src.reddog_resident_architect_client import (
    RedDogResidentArchitectClient,
    ResidentClientReason,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "reddog_resident_architect_client.py"
)
FOCUS = "Audit RedDog resident transport continuity."


def _grounding_receipt(*, source: str = "hermes_thin_client") -> dict:
    typed = {
        "repo_file_targets": ["modules/communication/moltbot_bridge/src/reddog_resident_architect_client.py"],
        "semantic_targets": [],
        "external_research_targets": [],
        "quoted_reference_blocks_count": 0,
        "quoted_reference_blocks_digest": canonical_digest([]),
    }
    value = {
        "schema_version": GROUNDING_SCHEMA_VERSION,
        "source_surface": source,
        "work_focus_digest": canonical_digest({"work_focus": FOCUS}),
        "typed_targets": typed,
        "typed_targets_digest": canonical_digest(typed),
        "grounding_preflight_applied": True,
        "grounding_preflight_passed": True,
        "grounding_preflight_rejection_reasons": [],
        "grounding_target_universe_required": True,
        "repo_file_targets_count": 1,
        "semantic_targets_count": 0,
        "external_research_targets_count": 0,
        "quoted_reference_blocks_count": 0,
        "semantic_target_coverage": [],
        "semantic_target_coverage_digest": canonical_digest({"semantic_target_coverage": []}),
        "target_recall_ok": True,
        "required_targets_missing": [],
        "direct_read_paths": typed["repo_file_targets"],
        "holoindex_owner_query_ok": False,
        "holoindex_freshness": "UNKNOWN",
        "holoindex_generation_id": "",
        "holoindex_freshness_receipt_digest": "",
        "holoindex_repo_head_sha": "",
        "holoindex_query_receipt_id": "",
        "holoindex_index_gap_detected": False,
        "no_holoindex_reindex_performed": True,
    }
    value["receipt_id"] = canonical_digest(value)
    return value


def _intent(*, principal: str = "principal-012", source: str = "hermes_thin_client") -> dict:
    return {
        "schema_version": "reddog_intent.v2",
        "intent_id": "sha256:hermes-resident-intent",
        "source_surface": source,
        "origin": "hermes_agent",
        "principal_ref": principal,
        "foundup_id": "foundups_agent",
        "work_focus": FOCUS,
        "grounding_receipt": _grounding_receipt(source=source),
        "submits_executable_authority": False,
    }


class _Store:
    def __init__(self) -> None:
        self.records = {}

    def load_cycle_by_intent(self, intent_id):
        return self.records.get(intent_id)

    def upsert_cycle(self, record):
        self.records[str(record["intent_id"])] = dict(record)
        return {"ok": True}

    def update_cycle(self, intent_id, updates):
        record = dict(self.records[intent_id])
        record.update(dict(updates))
        self.records[intent_id] = record
        return {"ok": True}

    def load_task_ids(self, determination_id):
        return ()

    def load_task_status_counts(self, task_ids):
        return {}

    def delete_cycle_tasks(self, task_ids):
        return None


class _Runner:
    def __init__(self) -> None:
        self.calls = []

    def __call__(self, **kwargs):
        self.calls.append(dict(kwargs))
        intent = dict(kwargs["red_dog_intent"])
        status = "CANCELLED" if kwargs["cancel_requested"] else "DETERMINED"
        record = {
            "accepted": not kwargs["cancel_requested"],
            "intent_id": intent["intent_id"],
            "cycle_id": "sha256:cycle",
            "status": status,
            "snapshot_id": "sha256:snapshot",
            "architect_determination_id": "sha256:determination",
            "architect_action": "FIX",
            "architect_next_slice": "REDDOG_NEXT_PHASE1",
            "task_status_counts": {"completed": 5},
            "rejection_reasons": ["REJECT_RESIDENT_CYCLE_CANCELLED"] if status == "CANCELLED" else [],
            "intent": intent,
            "read_only_authority_only": True,
            "no_shell_command_executed": True,
            "no_repo_mutation_performed": True,
            "no_holoindex_reindex_performed": True,
            "no_hermes_dispatch_performed": True,
            "no_worktree_operation_performed": True,
            "no_pr_created": True,
            "no_pattern_memory_promotion_performed": True,
            "no_live_foundup_enqueue_performed": True,
        }
        kwargs["cycle_store"].upsert_cycle(record)
        return record


def _client(store=None, runner=None) -> RedDogResidentArchitectClient:
    return RedDogResidentArchitectClient(
        repo_root=REPO_ROOT,
        authenticated_principal_id="principal-012",
        authorized_foundup_ids=("foundups_agent",),
        transport="hermes",
        cycle_store=store or _Store(),
        cycle_runner=runner or _Runner(),
    )


def test_submit_calls_canonical_cycle_and_returns_readonly_receipt() -> None:
    store = _Store()
    runner = _Runner()
    result = _client(store, runner).submit(_intent())

    assert result.accepted is True
    assert result.status == "DETERMINED"
    assert result.canonical_resident_cycle_used is True
    assert result.read_only_authority_only is True
    assert result.client_no_shell_command_executed is True
    assert result.client_no_repo_mutation_performed is True
    assert len(runner.calls) == 1
    assert runner.calls[0]["red_dog_intent"]["grounding_receipt"]["source_surface"] == "hermes_thin_client"
    assert runner.calls[0]["cancel_requested"] is False
    assert runner.calls[0]["retry_requested"] is False


def test_status_is_reconnect_only_and_does_not_run_cycle() -> None:
    store = _Store()
    runner = _Runner()
    client = _client(store, runner)
    submitted = client.submit(_intent())
    runner.calls.clear()

    status = client.status(submitted.intent_id)

    assert status.accepted is True
    assert status.status == "DETERMINED"
    assert runner.calls == []


def test_cancel_and_failed_resume_use_persisted_intent_only() -> None:
    store = _Store()
    runner = _Runner()
    client = _client(store, runner)
    submitted = client.submit(_intent())

    cancelled = client.cancel(submitted.intent_id)
    resumed = client.resume(submitted.intent_id)

    assert cancelled.status == "CANCELLED"
    assert runner.calls[-2]["cancel_requested"] is True
    assert runner.calls[-1]["retry_requested"] is True
    assert resumed.status == "DETERMINED"


def test_payload_principal_and_wrong_transport_never_reach_cycle() -> None:
    runner = _Runner()
    client = _client(runner=runner)

    wrong_principal = client.submit(_intent(principal="payload-claims-012"))
    wrong_surface = client.submit(_intent(source="editor_thin_client"))

    assert ResidentClientReason.PRINCIPAL_MISMATCH in wrong_principal.rejection_reasons
    assert ResidentClientReason.SOURCE_MISMATCH in wrong_surface.rejection_reasons
    assert runner.calls == []


def test_tampered_cycle_owner_or_authority_rejects_reconnect() -> None:
    store = _Store()
    runner = _Runner()
    client = _client(store, runner)
    submitted = client.submit(_intent())
    record = dict(store.records[submitted.intent_id])
    record["read_only_authority_only"] = False
    record["intent"] = dict(record["intent"])
    record["intent"]["intent_id"] = "sha256:substituted"
    store.records[submitted.intent_id] = record
    runner.calls.clear()

    result = client.status(submitted.intent_id)

    assert result.accepted is False
    assert ResidentClientReason.REQUEST_INVALID in result.rejection_reasons
    assert ResidentClientReason.RUNTIME_FAILED in result.rejection_reasons
    assert runner.calls == []


def test_runtime_defaults_cannot_override_canonical_cycle_inputs() -> None:
    for key in ("repo_root", "red_dog_intent", "cycle_store", "cancel_requested", "retry_requested"):
        try:
            RedDogResidentArchitectClient(
                repo_root=REPO_ROOT,
                authenticated_principal_id="principal-012",
                authorized_foundup_ids=("foundups_agent",),
                transport="hermes",
                runtime_defaults={key: "attacker"},
            )
        except ValueError as exc:
            assert str(exc) == ResidentClientReason.RUNTIME_CONFIGURATION
        else:
            raise AssertionError(f"reserved runtime key accepted: {key}")

    try:
        RedDogResidentArchitectClient(
            repo_root=REPO_ROOT,
            authenticated_principal_id="principal-012",
            authorized_foundup_ids="foundups_agent",
            transport="hermes",
        )
    except ValueError as exc:
        assert str(exc) == ResidentClientReason.RUNTIME_CONFIGURATION
    else:
        raise AssertionError("string FoundUp scope accepted as a sequence of characters")


def test_runtime_boundary_contradiction_is_not_reported_as_safe() -> None:
    class UnsafeRunner(_Runner):
        def __call__(self, **kwargs):
            result = super().__call__(**kwargs)
            result["no_repo_mutation_performed"] = False
            return result

    result = _client(runner=UnsafeRunner()).submit(_intent())

    assert result.accepted is False
    assert result.canonical_resident_cycle_used is True
    assert ResidentClientReason.RUNTIME_FAILED in result.rejection_reasons


def test_foundup_outside_host_authorized_scope_never_reaches_cycle() -> None:
    runner = _Runner()
    intent = _intent()
    intent["foundup_id"] = "attacker_foundup"

    result = _client(runner=runner).submit(intent)

    assert result.accepted is False
    assert ResidentClientReason.FOUNDUP_SCOPE_MISMATCH in result.rejection_reasons
    assert runner.calls == []


def test_missing_runtime_boundary_attestation_fails_closed() -> None:
    class IncompleteRunner(_Runner):
        def __call__(self, **kwargs):
            result = super().__call__(**kwargs)
            result.pop("no_live_foundup_enqueue_performed")
            return result

    result = _client(runner=IncompleteRunner()).submit(_intent())

    assert result.accepted is False
    assert ResidentClientReason.RUNTIME_FAILED in result.rejection_reasons


def test_client_module_has_no_execution_or_second_model_authority() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    assert "subprocess" not in imported
    assert "os" not in imported
    for forbidden in ("HermesFoundUpBuilder", "run_repo_code_audit", "git push", "gh pr", "worktree add"):
        assert forbidden not in source
