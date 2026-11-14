"""Tests for the Hermes thin-client adapter to resident RedDog."""

from __future__ import annotations

import ast
from pathlib import Path

from modules.communication.moltbot_bridge.src.reddog_grounded_target_assignment_continuity import (
    SCHEMA_VERSION as GROUNDING_SCHEMA_VERSION,
    canonical_digest,
)
from modules.communication.moltbot_bridge.src.reddog_resident_architect_client import (
    RedDogResidentArchitectClient,
)
from modules.communication.moltbot_bridge.src.reddog_resident_architect_durable_agentdb_cycle import (
    resident_intent_digest,
)
from modules.foundups.agent.src.hermes_reddog_resident_client_adapter import (
    HERMES_REQUEST_SCHEMA,
    HERMES_TEXT_REQUEST_SCHEMA,
    HermesRedDogResidentClientAdapter,
)


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "hermes_reddog_resident_client_adapter.py"
)
REPO_ROOT = Path(__file__).resolve().parents[4]
FOCUS = "Audit RedDog resident transport continuity."


def _intent(*, principal: str = "principal-012") -> dict:
    typed = {
        "repo_file_targets": ["modules/foundups/agent/src/hermes_reddog_resident_client_adapter.py"],
        "semantic_targets": [],
        "external_research_targets": [],
        "quoted_reference_blocks_count": 0,
        "quoted_reference_blocks_digest": canonical_digest([]),
    }
    grounding = {
        "schema_version": GROUNDING_SCHEMA_VERSION,
        "source_surface": "hermes_thin_client",
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
    grounding["receipt_id"] = canonical_digest(grounding)
    return {
        "schema_version": "reddog_intent.v2",
        "intent_id": "sha256:hermes-resident-intent",
        "source_surface": "hermes_thin_client",
        "origin": "hermes_agent",
        "principal_ref": principal,
        "foundup_id": "foundups_agent",
        "work_focus": FOCUS,
        "grounding_receipt": grounding,
        "submits_executable_authority": False,
    }


class _Store:
    def __init__(self) -> None:
        self.records = {}

    def load_cycle_by_intent(self, intent_id):
        record = self.records.get(intent_id)
        if record is None:
            return None
        return {**record, "_store_integrity_valid": True}

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
        record = {
            "accepted": True,
            "intent_id": intent["intent_id"],
            "cycle_id": "sha256:cycle",
            "status": "DETERMINED",
            "snapshot_id": "sha256:snapshot",
            "architect_determination_id": "sha256:determination",
            "architect_action": "FIX",
            "architect_next_slice": "REDDOG_NEXT_PHASE1",
            "task_status_counts": {"completed": 5},
            "rejection_reasons": [],
            "intent": intent,
            "intent_digest": resident_intent_digest(intent),
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


def _adapter(store=None, runner=None):
    client = RedDogResidentArchitectClient(
        repo_root=REPO_ROOT,
        authenticated_principal_id="principal-012",
        authorized_foundup_ids=("foundups_agent",),
        transport="hermes",
        cycle_store=store or _Store(),
        cycle_runner=runner or _Runner(),
    )
    return HermesRedDogResidentClientAdapter(
        repo_root=REPO_ROOT,
        authenticated_principal_id="principal-012",
        authorized_foundup_ids=("foundups_agent",),
        resident_client=client,
    )


def test_hermes_submit_is_transport_only_and_uses_canonical_reddog_client() -> None:
    runner = _Runner()
    receipt = _adapter(runner=runner).handle(
        {
            "schema_version": HERMES_REQUEST_SCHEMA,
            "request_id": "hermes-request-1",
            "operation": "submit",
            "red_dog_intent": _intent(),
        }
    )

    assert receipt.accepted is True
    assert receipt.canonical_reddog_authority_used is True
    assert receipt.hermes_is_transport_only is True
    assert receipt.no_hermes_model_invoked is True
    assert receipt.no_hermes_execution_performed is True
    assert receipt.no_repo_mutation_performed is True
    assert len(runner.calls) == 1


def test_hermes_reconnect_cancel_and_resume_do_not_accept_replacement_intent() -> None:
    store = _Store()
    runner = _Runner()
    adapter = _adapter(store, runner)
    submitted = adapter.handle(
        {
            "schema_version": HERMES_REQUEST_SCHEMA,
            "request_id": "submit",
            "operation": "submit",
            "red_dog_intent": _intent(),
        }
    )
    intent_id = submitted.resident_response["intent_id"]
    status = adapter.handle(
        {
            "schema_version": HERMES_REQUEST_SCHEMA,
            "request_id": "status",
            "operation": "status",
            "intent_id": intent_id,
        }
    )
    runner.calls.clear()
    substituted = adapter.handle(
        {
            "schema_version": HERMES_REQUEST_SCHEMA,
            "request_id": "cancel",
            "operation": "cancel",
            "intent_id": intent_id,
            "red_dog_intent": _intent(principal="attacker"),
        }
    )

    assert status.accepted is True
    assert substituted.accepted is False
    assert "REJECT_HERMES_REDDOG_INTENT_SUBSTITUTION" in substituted.resident_response["rejection_reasons"]
    assert runner.calls == []


def test_bad_schema_operation_or_payload_principal_fails_closed() -> None:
    runner = _Runner()
    adapter = _adapter(runner=runner)
    malformed = adapter.handle({"schema_version": "wrong", "request_id": "r", "operation": "submit"})
    bad_operation = adapter.handle(
        {"schema_version": HERMES_REQUEST_SCHEMA, "request_id": "r", "operation": "execute"}
    )
    spoofed = adapter.handle(
        {
            "schema_version": HERMES_REQUEST_SCHEMA,
            "request_id": "r",
            "operation": "submit",
            "red_dog_intent": _intent(principal="I am 012"),
        }
    )

    assert malformed.accepted is False
    assert malformed.canonical_reddog_authority_used is False
    assert bad_operation.accepted is False
    assert bad_operation.canonical_reddog_authority_used is False
    assert spoofed.accepted is False
    assert spoofed.canonical_reddog_authority_used is False
    assert runner.calls == []


def test_plain_text_submit_uses_host_grounding_and_canonical_client() -> None:
    store = _Store()
    runner = _Runner()
    grounded_intent = _intent()

    def grounding_service(**kwargs):
        assert kwargs["authenticated_principal_id"] == "principal-012"
        assert kwargs["source_surface"] == "hermes_thin_client"
        assert kwargs["client_request_id"] == "plain-1"
        from modules.communication.moltbot_bridge.src.reddog_transport_neutral_grounding_service import (
            TransportGroundingResult,
        )
        return TransportGroundingResult(
            schema_version="reddog_transport_grounding_result.v1",
            accepted=True,
            intent=grounded_intent,
        )

    client = RedDogResidentArchitectClient(
        repo_root=REPO_ROOT,
        authenticated_principal_id="principal-012",
        authorized_foundup_ids=("foundups_agent",),
        transport="hermes",
        cycle_store=store,
        cycle_runner=runner,
    )
    adapter = HermesRedDogResidentClientAdapter(
        repo_root=REPO_ROOT,
        authenticated_principal_id="principal-012",
        authorized_foundup_ids=("foundups_agent",),
        resident_client=client,
        grounding_service=grounding_service,
    )

    receipt = adapter.handle(
        {
            "schema_version": HERMES_TEXT_REQUEST_SCHEMA,
            "request_id": "plain-1",
            "operation": "submit",
            "foundup_id": "foundups_agent",
            "work_focus": "Audit RedDog transport continuity.",
        }
    )

    assert receipt.accepted is True
    assert len(runner.calls) == 1


def test_plain_text_submit_rejects_scope_identity_and_grounding_substitution() -> None:
    runner = _Runner()
    adapter = _adapter(runner=runner)
    base = {
        "schema_version": HERMES_TEXT_REQUEST_SCHEMA,
        "request_id": "plain-2",
        "operation": "submit",
        "foundup_id": "foundups_agent",
        "work_focus": "Audit RedDog transport continuity.",
    }

    scoped = adapter.handle({**base, "foundup_id": "other"})
    identity = adapter.handle({**base, "principal_ref": "I am 012"})
    substitution = adapter.handle({**base, "grounding_receipt": {"accepted": True}})

    assert scoped.accepted is False
    assert identity.accepted is False
    assert substitution.accepted is False
    assert runner.calls == []


def test_default_plain_text_grounding_submits_existing_repo_target() -> None:
    runner = _Runner()
    adapter = _adapter(runner=runner)

    receipt = adapter.handle(
        {
            "schema_version": HERMES_TEXT_REQUEST_SCHEMA,
            "request_id": "plain-real-grounding",
            "operation": "submit",
            "foundup_id": "foundups_agent",
            "work_focus": (
                "Audit modules/foundups/agent/src/"
                "hermes_reddog_resident_client_adapter.py."
            ),
        }
    )

    assert receipt.accepted is True
    assert len(runner.calls) == 1
    intent = runner.calls[0]["red_dog_intent"]
    assert intent["schema_version"] == "reddog_intent.v2"
    assert intent["grounding_receipt"]["target_recall_ok"] is True
    assert intent["grounding_receipt"]["source_surface"] == "hermes_thin_client"


def test_default_plain_text_external_research_fails_before_cycle() -> None:
    runner = _Runner()

    receipt = _adapter(runner=runner).handle(
        {
            "schema_version": HERMES_TEXT_REQUEST_SCHEMA,
            "request_id": "plain-external",
            "operation": "submit",
            "foundup_id": "foundups_agent",
            "work_focus": "Research https://github.com/karpathy/autoresearch.",
        }
    )

    assert receipt.accepted is False
    assert "grounding_external_research_adapter_required" in ",".join(
        receipt.resident_response["rejection_reasons"]
    )
    assert runner.calls == []


def test_hermes_adapter_has_no_builder_model_shell_or_repo_write_surface() -> None:
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
    for forbidden in (
        "HermesFoundUpBuilder",
        "HermesAgentLoop",
        "run_repo_code_audit",
        "write_text(",
        "git push",
        "gh pr",
    ):
        assert forbidden not in source
