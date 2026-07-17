"""Tests for REDDOG_SIGNED_AUTHORITY_WORKER_DISPATCH_DRYRUN_PHASE1."""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

from modules.communication.moltbot_bridge.src import (
    reddog_signed_authority_worker_dispatch_dryrun as dispatch,
)
from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    AUTHORITY_ISSUED,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authority_runtime_invoke import (
    QUEUE_AUTHORITY_RUNTIME_INVOKE_ACCEPT,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authority_verification_invoke import (
    QUEUE_AUTHORITY_VERIFICATION_INVOKE_ACCEPT,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "reddog_signed_authority_worker_dispatch_dryrun.py"
)


def _digest(value: dict) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _allocation(**overrides):
    payload = {
        "schema_version": "reddog_wsp15_allocation_receipt.v1",
        "receipt_id": "sha256:wsp15-allocation",
        "mps_total": 20,
        "priority": "P0",
        "reasoning_tier": "ULTRA",
        "worker_plan": {
            "schema_version": "reddog_wsp15_worker_plan.v1",
            "fusion_required": True,
            "reasoning_tier": "ULTRA",
            "critic_count": 2,
            "coding_worker_count": 2,
            "independent_verifier_required": True,
            "openclaw_candidate": True,
            "hermes_execution_allowed": False,
            "queue_mutation_allowed": False,
            "mode_selection_source": "reddog_wsp15_allocation_receipt.v1",
        },
    }
    payload.update(overrides)
    return payload


def _work_authority(allocation=None, **overrides):
    allocation = allocation or _allocation()
    payload = {
        "work_order_id": "wo-1",
        "principal_id": "github:mjtrout",
        "reddog_id": "reddog:abc123",
        "repo_full_name": "FOUNDUPS/Foundups-Agent",
        "foundup_id": "paccess_001",
        "allowed_paths": ["modules/foundups/paccess_001/src/app.py"],
        "denied_paths": [],
        "requested_operation": "create_foundup",
        "permission_snapshot_digest": "sha256:permission-snapshot",
        "wsp15_allocation_receipt_id": allocation["receipt_id"],
        "wsp15_allocation_digest": _digest(allocation),
        "wsp15_priority": allocation["priority"],
        "wsp15_mps_total": allocation["mps_total"],
        "wsp15_reasoning_tier": allocation["reasoning_tier"],
        "nonce": "nonce-1",
        "issued_at": 1000,
        "expires_at": 1100,
        "valve_state_required": "VALVE_OPEN_WORKTREE_CREATE",
        "key_epoch": "epoch-1",
        "signature": "sig-work",
    }
    payload.update(overrides)
    return payload


def _verification_result(**overrides):
    payload = {
        "decision": QUEUE_AUTHORITY_VERIFICATION_INVOKE_ACCEPT,
        "verification_result": {
            "accepted": True,
            "reason_codes": [],
            "work_order_id": "wo-1",
        },
    }
    payload.update(overrides)
    return payload


def _runtime_result(allocation=None, **overrides):
    allocation = allocation or _allocation()
    payload = {
        "decision": QUEUE_AUTHORITY_RUNTIME_INVOKE_ACCEPT,
        "authority_result": {
            "accepted": True,
            "receipt": {"status": AUTHORITY_ISSUED, "receipt_id": "auth-1"},
            "work_authority": _work_authority(allocation),
        },
    }
    payload.update(overrides)
    return payload


def _plan(allocation=None, **overrides):
    allocation = allocation or _allocation()
    args = {
        "explicit_signed_authority_worker_dispatch_dryrun_requested": True,
        "queue_authority_verification_result": _verification_result(),
        "queue_authority_runtime_result": _runtime_result(allocation),
        "wsp15_allocation_receipt": allocation,
    }
    args.update(overrides)
    return dispatch.plan_reddog_signed_authority_worker_dispatch_dry_run(**args)


def test_accepts_verified_signed_authority_and_emits_wsp15_worker_intents() -> None:
    result = _plan()

    assert result.accepted is True
    assert result.decision == dispatch.SIGNED_AUTHORITY_WORKER_DISPATCH_DRYRUN_ACCEPT
    assert result.receipt is not None
    assert result.receipt.dispatch_intent_count == 2
    roles = [intent.role for intent in result.receipt.dispatch_intents]
    assert roles == [
        "coding_worker_1",
        "queue_stage_worker",
    ]
    assert roles.count("coding_worker_1") == 1
    assert "coding_worker_2" not in roles
    assert result.receipt.dispatch_intents[-1].worker_runtime == "openclaw"
    assert result.receipt.dispatch_intents[-1].capability == "queue_stage_progress"
    assert {intent.worker_runtime for intent in result.receipt.dispatch_intents} == {"0102", "openclaw"}
    assert result.receipt.wsp15_allocation_digest == _digest(_allocation())
    assert result.receipt.no_worker_spawn_performed is True
    assert result.receipt.no_openclaw_enqueue_performed is True
    assert result.receipt.no_hermes_dispatch_performed is True


def test_carries_model_runtime_binding_from_signed_authority() -> None:
    allocation = _allocation()
    runtime = _runtime_result(
        allocation,
        authority_result={
            "accepted": True,
            "receipt": {"status": AUTHORITY_ISSUED, "receipt_id": "auth-1"},
            "work_authority": _work_authority(
                allocation,
                model_runtime_binding_receipt_id="reddog_model_runtime_binding:abc123",
                model_runtime_binding_digest="sha256:model-runtime-binding",
            ),
        },
    )

    result = _plan(allocation=allocation, queue_authority_runtime_result=runtime)

    assert result.accepted is True
    assert result.receipt is not None
    assert result.receipt.model_runtime_binding_receipt_id == "reddog_model_runtime_binding:abc123"
    assert result.receipt.model_runtime_binding_digest == "sha256:model-runtime-binding"
    assert {
        intent.model_runtime_binding_receipt_id
        for intent in result.receipt.dispatch_intents
    } == {"reddog_model_runtime_binding:abc123"}
    assert {
        intent.model_runtime_binding_digest
        for intent in result.receipt.dispatch_intents
    } == {"sha256:model-runtime-binding"}


def test_rejects_one_sided_model_runtime_binding_in_signed_authority() -> None:
    allocation = _allocation()
    runtime = _runtime_result(
        allocation,
        authority_result={
            "accepted": True,
            "receipt": {"status": AUTHORITY_ISSUED, "receipt_id": "auth-1"},
            "work_authority": _work_authority(
                allocation,
                model_runtime_binding_receipt_id="reddog_model_runtime_binding:abc123",
                model_runtime_binding_digest="",
            ),
        },
    )

    result = _plan(allocation=allocation, queue_authority_runtime_result=runtime)

    assert result.accepted is False
    assert (
        dispatch.SignedAuthorityWorkerDispatchDryRunReason.MODEL_RUNTIME_BINDING_MISMATCH
        in result.rejection_reasons
    )


def test_preserves_legacy_openclaw_candidate_for_non_code_worker_plan() -> None:
    allocation = _allocation()
    allocation["worker_plan"] = dict(allocation["worker_plan"], coding_worker_count=0)

    result = _plan(allocation=allocation, queue_authority_runtime_result=_runtime_result(allocation))

    assert result.accepted is True
    assert result.receipt is not None
    roles = [intent.role for intent in result.receipt.dispatch_intents]
    assert "openclaw_candidate" in roles
    assert "queue_stage_worker" not in roles
    intent = next(value for value in result.receipt.dispatch_intents if value.role == "openclaw_candidate")
    assert intent.worker_runtime == "openclaw"
    assert intent.capability == "candidate_queue_review"


def test_explicit_request_is_required() -> None:
    result = _plan(explicit_signed_authority_worker_dispatch_dryrun_requested=False)

    assert result.accepted is False
    assert dispatch.SignedAuthorityWorkerDispatchDryRunReason.EXPLICIT_REQUEST_MISSING in result.rejection_reasons


def test_rejects_unaccepted_authority_verification() -> None:
    result = _plan(
        queue_authority_verification_result={
            "decision": "QUEUE_AUTHORITY_VERIFICATION_INVOKE_REJECT",
            "verification_result": {"accepted": False},
        }
    )

    assert result.accepted is False
    assert (
        dispatch.SignedAuthorityWorkerDispatchDryRunReason.AUTHORITY_VERIFICATION_NOT_ACCEPTED
        in result.rejection_reasons
    )


def test_rejects_unaccepted_authority_runtime() -> None:
    result = _plan(queue_authority_runtime_result={"decision": "QUEUE_AUTHORITY_RUNTIME_INVOKE_REJECT"})

    assert result.accepted is False
    assert dispatch.SignedAuthorityWorkerDispatchDryRunReason.AUTHORITY_RUNTIME_NOT_ACCEPTED in result.rejection_reasons


def test_rejects_missing_allocation() -> None:
    result = _plan(wsp15_allocation_receipt={})

    assert result.accepted is False
    assert dispatch.SignedAuthorityWorkerDispatchDryRunReason.WSP15_ALLOCATION_MISSING in result.rejection_reasons


def test_rejects_allocation_digest_tamper_after_signing() -> None:
    allocation = _allocation()
    runtime = _runtime_result(allocation)
    tampered = _allocation()
    tampered["mps_total"] = 19

    result = _plan(
        allocation=tampered,
        queue_authority_runtime_result=runtime,
        wsp15_allocation_receipt=tampered,
    )

    assert result.accepted is False
    assert dispatch.SignedAuthorityWorkerDispatchDryRunReason.WSP15_DIGEST_MISMATCH in result.rejection_reasons
    assert dispatch.SignedAuthorityWorkerDispatchDryRunReason.WSP15_MPS_TOTAL_MISMATCH in result.rejection_reasons


def test_rejects_receipt_id_mismatch() -> None:
    allocation = _allocation()
    runtime = _runtime_result(allocation)
    runtime["authority_result"]["work_authority"]["wsp15_allocation_receipt_id"] = "sha256:other"

    result = _plan(queue_authority_runtime_result=runtime)

    assert result.accepted is False
    assert dispatch.SignedAuthorityWorkerDispatchDryRunReason.WSP15_RECEIPT_ID_MISMATCH in result.rejection_reasons


def test_rejects_if_worker_plan_allows_hermes_execution() -> None:
    allocation = _allocation()
    allocation["worker_plan"] = dict(allocation["worker_plan"], hermes_execution_allowed=True)

    result = _plan(allocation=allocation, queue_authority_runtime_result=_runtime_result(allocation))

    assert result.accepted is False
    assert dispatch.SignedAuthorityWorkerDispatchDryRunReason.HERMES_EXECUTION_NOT_ALLOWED in result.rejection_reasons


def test_rejects_if_worker_plan_allows_queue_mutation() -> None:
    allocation = _allocation()
    allocation["worker_plan"] = dict(allocation["worker_plan"], queue_mutation_allowed=True)

    result = _plan(allocation=allocation, queue_authority_runtime_result=_runtime_result(allocation))

    assert result.accepted is False
    assert dispatch.SignedAuthorityWorkerDispatchDryRunReason.QUEUE_MUTATION_NOT_ALLOWED in result.rejection_reasons


def test_rejects_malformed_mps_priority_relationship() -> None:
    allocation = _allocation(priority="P4")

    result = _plan(allocation=allocation, queue_authority_runtime_result=_runtime_result(allocation))

    assert result.accepted is False
    assert dispatch.SignedAuthorityWorkerDispatchDryRunReason.WSP15_ALLOCATION_MALFORMED in result.rejection_reasons


def test_rejects_empty_worker_plan() -> None:
    allocation = _allocation()
    allocation["worker_plan"] = {
        "schema_version": "reddog_wsp15_worker_plan.v1",
        "hermes_execution_allowed": False,
        "queue_mutation_allowed": False,
    }

    result = _plan(allocation=allocation, queue_authority_runtime_result=_runtime_result(allocation))

    assert result.accepted is False
    assert dispatch.SignedAuthorityWorkerDispatchDryRunReason.WORKER_PLAN_EMPTY in result.rejection_reasons


def test_result_is_json_serializable_and_truth_flags_are_false_for_side_effects() -> None:
    payload = _plan().to_dict()

    json.dumps(payload, sort_keys=True)
    assert payload["no_worker_spawn_performed"] is True
    assert payload["no_queue_mutation_performed"] is True
    assert payload["no_worktree_created"] is True
    assert payload["no_shell_command_executed"] is True
    assert payload["no_openclaw_enqueue_performed"] is True
    assert payload["no_hermes_dispatch_performed"] is True
    assert payload["no_repo_mutation_performed"] is True
    assert payload["no_holoindex_reindex_performed"] is True
    assert payload["no_pr_created"] is True
    assert payload["no_reward_settlement_performed"] is True


def test_module_has_no_runtime_dispatch_or_execution_imports() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    banned_import_roots = {
        "subprocess",
        "os",
        "requests",
        "urllib",
        "http",
        "socket",
        "git",
        "gh",
    }
    banned_import_fragments = {
        "openclaw_supervisor",
        "hermes_job_executor",
        "worker_assignment_protocol",
        "swarm_dispatch_integration",
        "worktree_pr_runner",
        "pattern_memory",
    }
    banned_calls = {"eval", "exec", "compile", "__import__", "open"}

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                assert root not in banned_import_roots
                assert not any(fragment in alias.name for fragment in banned_import_fragments)
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            root = module.split(".")[0]
            assert root not in banned_import_roots
            assert not any(fragment in module for fragment in banned_import_fragments)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in banned_calls
