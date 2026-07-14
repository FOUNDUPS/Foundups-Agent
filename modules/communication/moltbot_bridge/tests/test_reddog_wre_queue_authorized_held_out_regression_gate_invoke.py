"""Tests for REDDOG_WRE_QUEUE_AUTHORIZED_HELD_OUT_REGRESSION_GATE_INVOKE_PHASE1."""

from __future__ import annotations

import ast
import json
from pathlib import Path

from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_held_out_regression_gate_invoke import (
    QUEUE_AUTHORIZED_HELD_OUT_REGRESSION_GATE_INVOKE_ACCEPT,
    QUEUE_AUTHORIZED_HELD_OUT_REGRESSION_GATE_INVOKE_REJECT,
    QueueAuthorizedHeldOutRegressionGateInvokeReason,
    invoke_reddog_wre_queue_authorized_held_out_regression_gate,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_verified_outcome_ratchet_invoke import (
    QUEUE_AUTHORIZED_VERIFIED_OUTCOME_RATCHET_INVOKE_ACCEPT,
    QUEUE_AUTHORIZED_VERIFIED_OUTCOME_RATCHET_INVOKE_REJECT,
)
from modules.infrastructure.wre_core.src import (
    reddog_held_out_recursive_improvement_regression_gate as gate,
)
from modules.infrastructure.wre_core.src.reddog_verified_outcome_ratchet import (
    OUTCOME_RATCHET_RECORDED,
    OUTCOME_RATCHET_REJECT,
)
from modules.infrastructure.wre_core.src.wre_autonomous_slice_verifier_runtime import (
    AUTONOMOUS_SLICE_VERIFIER_ACCEPT,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "reddog_wre_queue_authorized_held_out_regression_gate_invoke.py"
)
WORK_ORDER_ID = "wo-held-out-queue-1"
SLICE_NAME = "REDDOG_WRE_QUEUE_AUTHORIZED_HELD_OUT_REGRESSION_GATE_INVOKE_PHASE1"
VERIFIER_RECEIPT_ID = "wre_slice_verify_1234"
RATCHET_ID = "outcome_ratchet_1234"
HEAD_SHA = "a" * 40


def _digest(ch: str) -> str:
    return "sha256:" + ch * 64


def _queue_ratchet_result(*, accepted: bool = True, decision: str | None = None) -> dict:
    return {
        "decision": decision or QUEUE_AUTHORIZED_VERIFIED_OUTCOME_RATCHET_INVOKE_ACCEPT,
        "rejection_reasons": [] if accepted else ["FAIL_HOLOINDEX_EVIDENCE"],
        "explicit_queue_authorized_verified_outcome_ratchet_requested": True,
        "ratchet_result": {
            "decision": OUTCOME_RATCHET_RECORDED if accepted else OUTCOME_RATCHET_REJECT,
            "accepted": accepted,
            "rejection_reasons": [] if accepted else ["FAIL_HOLOINDEX_EVIDENCE"],
            "receipt": {
                "ratchet_id": RATCHET_ID,
                "work_order_id": WORK_ORDER_ID,
                "slice_name": SLICE_NAME,
                "outcome_status": "accepted",
                "verifier_receipt_id": VERIFIER_RECEIPT_ID,
                "publish_receipt_id": "verified_draft_pr_1234",
                "pattern_memory_eligible": accepted,
                "pattern_memory_write_performed": False,
                "pattern_memory_record_id": None,
                "rejection_reasons": [] if accepted else ["FAIL_HOLOINDEX_EVIDENCE"],
            },
        },
    }


def _gate_request() -> dict:
    return {
        "work_order_id": WORK_ORDER_ID,
        "slice_name": SLICE_NAME,
        "worker_id": "worker-0102",
        "enable_pattern_memory_admission": True,
        "improvement_job": {
            "job_id": "imp_wsp_violation_1234_abcd",
            "finding_id": "fmas-1",
            "improvement_type": "wsp_violation",
            "status": "pending",
            "dry_run": True,
        },
        "verification_result": {
            "accepted": True,
            "decision": AUTONOMOUS_SLICE_VERIFIER_ACCEPT,
            "receipt": {
                "receipt_id": VERIFIER_RECEIPT_ID,
                "work_order_id": WORK_ORDER_ID,
                "slice_name": SLICE_NAME,
                "worker_id": "worker-0102",
                "verifier_id": "verifier-0102",
                "head_sha": HEAD_SHA,
            },
        },
        "ratchet_result": {
            "accepted": False,
            "decision": OUTCOME_RATCHET_REJECT,
            "receipt": {
                "ratchet_id": "tampered-ratchet",
                "pattern_memory_write_performed": True,
            },
        },
        "held_out_regression": {
            "suite_id": "heldout-wre-recursive-001",
            "is_held_out": True,
            "independent": True,
            "generated_by_author": False,
            "evidence_author_id": "verifier-0102",
            "passed": True,
            "test_count": 12,
            "failure_count": 0,
            "suite_digest": _digest("1"),
            "baseline_digest": _digest("2"),
            "candidate_digest": _digest("3"),
            "candidate_head_sha": HEAD_SHA,
        },
        "holoindex_evidence": {
            "index_gap_detected": False,
            "holoindex_freshness_receipt_digest": _digest("4"),
        },
    }


def _invoke(*, queue_ratchet: dict | None = None, request: dict | None = None):
    return invoke_reddog_wre_queue_authorized_held_out_regression_gate(
        explicit_queue_authorized_held_out_regression_gate_requested=True,
        queue_verified_outcome_ratchet_result=queue_ratchet or _queue_ratchet_result(),
        held_out_gate_request=request or _gate_request(),
    )


def test_accepts_held_out_gate_after_queue_outcome_ratchet() -> None:
    result = _invoke()

    assert result.decision == QUEUE_AUTHORIZED_HELD_OUT_REGRESSION_GATE_INVOKE_ACCEPT
    assert result.rejection_reasons == []
    assert result.gate_result is not None
    assert result.gate_result.decision == gate.HELD_OUT_RECURSIVE_IMPROVEMENT_REGRESSION_GATE_ACCEPT
    assert result.gate_result.pattern_memory_admission_allowed is True
    assert result.gate_result.receipt.ratchet_id == RATCHET_ID
    assert result.gate_result.receipt.no_pattern_memory_write_performed is True
    assert result.no_command_execution_performed is True
    assert result.no_test_execution_performed is True
    assert result.no_pattern_memory_write_performed is True
    assert result.no_pr_publish_performed is True
    assert result.no_merge_performed is True
    assert result.no_reward_settlement_performed is True
    assert result.no_holoindex_reindex_performed is True


def test_explicit_invoke_missing_rejects() -> None:
    result = invoke_reddog_wre_queue_authorized_held_out_regression_gate(
        explicit_queue_authorized_held_out_regression_gate_requested=False,
        queue_verified_outcome_ratchet_result=_queue_ratchet_result(),
        held_out_gate_request=_gate_request(),
    )

    assert result.decision == QUEUE_AUTHORIZED_HELD_OUT_REGRESSION_GATE_INVOKE_REJECT
    assert (
        QueueAuthorizedHeldOutRegressionGateInvokeReason.EXPLICIT_INVOKE_MISSING
        in result.rejection_reasons
    )
    assert result.gate_result is None


def test_unaccepted_queue_ratchet_rejects_before_gate() -> None:
    result = _invoke(
        queue_ratchet=_queue_ratchet_result(
            accepted=False,
            decision=QUEUE_AUTHORIZED_VERIFIED_OUTCOME_RATCHET_INVOKE_REJECT,
        )
    )

    assert result.decision == QUEUE_AUTHORIZED_HELD_OUT_REGRESSION_GATE_INVOKE_REJECT
    assert (
        QueueAuthorizedHeldOutRegressionGateInvokeReason.RATCHET_INVOKE_NOT_ACCEPTED
        in result.rejection_reasons
    )
    assert (
        QueueAuthorizedHeldOutRegressionGateInvokeReason.RATCHET_PAYLOAD_NOT_RECORDED
        in result.rejection_reasons
    )
    assert result.gate_result is None


def test_missing_verification_payload_rejects_before_gate() -> None:
    request = _gate_request()
    request["verification_result"] = {}

    result = _invoke(request=request)

    assert result.decision == QUEUE_AUTHORIZED_HELD_OUT_REGRESSION_GATE_INVOKE_REJECT
    assert (
        QueueAuthorizedHeldOutRegressionGateInvokeReason.VERIFICATION_PAYLOAD_MISSING
        in result.rejection_reasons
    )
    assert result.gate_result is None


def test_verifier_receipt_mismatch_rejects_before_gate() -> None:
    request = _gate_request()
    request["verification_result"]["receipt"]["receipt_id"] = "other-verifier"

    result = _invoke(request=request)

    assert result.decision == QUEUE_AUTHORIZED_HELD_OUT_REGRESSION_GATE_INVOKE_REJECT
    assert (
        QueueAuthorizedHeldOutRegressionGateInvokeReason.VERIFIER_RECEIPT_MISMATCH
        in result.rejection_reasons
    )
    assert result.gate_result is None


def test_work_order_mismatch_rejects_before_gate() -> None:
    request = _gate_request()
    request["work_order_id"] = "other-work-order"

    result = _invoke(request=request)

    assert result.decision == QUEUE_AUTHORIZED_HELD_OUT_REGRESSION_GATE_INVOKE_REJECT
    assert (
        QueueAuthorizedHeldOutRegressionGateInvokeReason.WORK_ORDER_ID_MISMATCH
        in result.rejection_reasons
    )
    assert result.gate_result is None


def test_gate_rejection_is_preserved() -> None:
    request = _gate_request()
    request["held_out_regression"]["generated_by_author"] = True

    result = _invoke(request=request)

    assert result.decision == QUEUE_AUTHORIZED_HELD_OUT_REGRESSION_GATE_INVOKE_REJECT
    assert (
        QueueAuthorizedHeldOutRegressionGateInvokeReason.GATE_NOT_ACCEPTED
        in result.rejection_reasons
    )
    assert gate.FAIL_AUTHOR_GENERATED_SUITE in result.rejection_reasons
    assert result.gate_result is not None
    assert result.gate_result.decision == gate.HELD_OUT_RECURSIVE_IMPROVEMENT_REGRESSION_GATE_REJECT


def test_ratchet_with_prior_pattern_memory_write_is_rejected_by_gate() -> None:
    queue_ratchet = _queue_ratchet_result()
    queue_ratchet["ratchet_result"]["receipt"]["pattern_memory_write_performed"] = True

    result = _invoke(queue_ratchet=queue_ratchet)

    assert result.decision == QUEUE_AUTHORIZED_HELD_OUT_REGRESSION_GATE_INVOKE_REJECT
    assert gate.FAIL_RATCHET_RECEIPT in result.rejection_reasons
    assert gate.FAIL_PATTERN_MEMORY_ALREADY_WRITTEN in result.rejection_reasons


def test_result_is_json_serializable() -> None:
    result = _invoke()

    payload = result.to_dict()
    assert payload["decision"] == QUEUE_AUTHORIZED_HELD_OUT_REGRESSION_GATE_INVOKE_ACCEPT
    assert (
        payload["gate_result"]["decision"]
        == gate.HELD_OUT_RECURSIVE_IMPROVEMENT_REGRESSION_GATE_ACCEPT
    )
    json.dumps(payload, sort_keys=True)


def test_module_has_no_direct_shell_git_pr_test_memory_reward_or_holoindex_authority() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    banned_import_roots = {
        "subprocess",
        "os",
        "shutil",
        "requests",
        "urllib",
        "http",
        "socket",
        "sqlite3",
        "holo_index",
        "git",
        "pattern_memory",
    }
    banned_calls = {"eval", "exec", "compile", "__import__", "open"}

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".", 1)[0] not in banned_import_roots
        if isinstance(node, ast.ImportFrom) and node.module:
            assert node.module.split(".", 1)[0] not in banned_import_roots
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in banned_calls

    forbidden_tokens = (
        "subprocess",
        "git ",
        "gh pr",
        "pytest",
        "create_draft_pr",
        "push_branch",
        "mark_ready",
        "merge_pr",
        "store_verified_outcome",
        "settle_reward",
        "holo_index.py --index",
    )
    for token in forbidden_tokens:
        assert token not in source
