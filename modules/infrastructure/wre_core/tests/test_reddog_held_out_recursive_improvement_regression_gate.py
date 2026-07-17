"""Tests for REDDOG_HELD_OUT_RECURSIVE_IMPROVEMENT_REGRESSION_GATE_PHASE1."""

from __future__ import annotations

import ast
import json
from pathlib import Path

from modules.infrastructure.wre_core.src import (
    reddog_held_out_recursive_improvement_regression_gate as gate,
)
from modules.infrastructure.wre_core.src.reddog_verified_outcome_ratchet import (
    OUTCOME_RATCHET_RECORDED,
    OUTCOME_RATCHET_REJECT,
)
from modules.infrastructure.wre_core.src.wre_autonomous_slice_verifier_runtime import (
    AUTONOMOUS_SLICE_VERIFIER_ACCEPT,
    AUTONOMOUS_SLICE_VERIFIER_REJECT,
)

HEAD_SHA = "a" * 40


def _digest(ch: str) -> str:
    return "sha256:" + ch * 64


def valid_request() -> dict:
    return {
        "work_order_id": "wo-held-out-1",
        "slice_name": "REDDOG_HELD_OUT_RECURSIVE_IMPROVEMENT_REGRESSION_GATE_PHASE1",
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
                "receipt_id": "wre_slice_verify_1234",
                "work_order_id": "wo-held-out-1",
                "slice_name": "REDDOG_HELD_OUT_RECURSIVE_IMPROVEMENT_REGRESSION_GATE_PHASE1",
                "worker_id": "worker-0102",
                "verifier_id": "verifier-0102",
                "head_sha": HEAD_SHA,
            },
        },
        "ratchet_result": {
            "accepted": True,
            "decision": OUTCOME_RATCHET_RECORDED,
            "receipt": {
                "ratchet_id": "outcome_ratchet_1234",
                "work_order_id": "wo-held-out-1",
                "slice_name": "REDDOG_HELD_OUT_RECURSIVE_IMPROVEMENT_REGRESSION_GATE_PHASE1",
                "pattern_memory_write_performed": False,
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


def assert_reject(req: dict, code: str) -> gate.HeldOutRecursiveImprovementRegressionResult:
    result = gate.evaluate_held_out_recursive_improvement_regression_gate(req)
    assert result.accepted is False
    assert result.decision == gate.HELD_OUT_RECURSIVE_IMPROVEMENT_REGRESSION_GATE_REJECT
    assert code in result.rejection_reasons
    assert code in result.receipt.rejection_reasons
    assert result.pattern_memory_admission_allowed is False
    assert result.no_command_execution_performed is True
    assert result.no_test_execution_performed is True
    assert result.no_pattern_memory_write_performed is True
    assert result.no_pr_publish_performed is True
    assert result.no_merge_performed is True
    assert result.no_holoindex_reindex_performed is True
    return result


def test_accepts_independent_held_out_regression_after_verifier_and_ratchet() -> None:
    result = gate.evaluate_held_out_recursive_improvement_regression_gate(valid_request())

    assert result.accepted is True
    assert result.decision == gate.HELD_OUT_RECURSIVE_IMPROVEMENT_REGRESSION_GATE_ACCEPT
    assert result.pattern_memory_admission_allowed is True
    assert result.receipt.pattern_memory_admission_allowed is True
    assert result.receipt.pattern_memory_admission_requested is True
    assert result.receipt.regression_test_count == 12
    assert result.receipt.model_runtime_binding_receipt_id is None
    assert result.receipt.model_runtime_binding_digest == ""
    assert result.receipt.no_pattern_memory_write_performed is True
    assert result.receipt.no_test_execution_performed is True


def test_carries_model_runtime_binding_from_verifier_and_ratchet_receipts() -> None:
    req = valid_request()
    req["verification_result"]["receipt"]["model_runtime_binding_receipt_id"] = (
        "reddog_model_runtime_binding:test"
    )
    req["verification_result"]["receipt"]["model_runtime_binding_digest"] = _digest("5")
    req["ratchet_result"]["receipt"]["model_runtime_binding_receipt_id"] = (
        "reddog_model_runtime_binding:test"
    )
    req["ratchet_result"]["receipt"]["model_runtime_binding_digest"] = _digest("5")

    result = gate.evaluate_held_out_recursive_improvement_regression_gate(req)

    assert result.accepted is True
    assert (
        result.receipt.model_runtime_binding_receipt_id
        == "reddog_model_runtime_binding:test"
    )
    assert result.receipt.model_runtime_binding_digest == _digest("5")


def test_rejects_model_runtime_binding_mismatch() -> None:
    req = valid_request()
    req["verification_result"]["receipt"]["model_runtime_binding_receipt_id"] = (
        "reddog_model_runtime_binding:test"
    )
    req["verification_result"]["receipt"]["model_runtime_binding_digest"] = _digest("5")
    req["ratchet_result"]["receipt"]["model_runtime_binding_receipt_id"] = (
        "reddog_model_runtime_binding:test"
    )
    req["ratchet_result"]["receipt"]["model_runtime_binding_digest"] = _digest("6")

    assert_reject(req, gate.FAIL_MODEL_RUNTIME_BINDING)


def test_pattern_memory_admission_not_allowed_unless_requested() -> None:
    req = valid_request()
    req["enable_pattern_memory_admission"] = False

    result = gate.evaluate_held_out_recursive_improvement_regression_gate(req)

    assert result.accepted is True
    assert result.pattern_memory_admission_allowed is False
    assert result.receipt.pattern_memory_admission_requested is False


def test_rejects_improvement_job_that_is_not_pending_dry_run() -> None:
    req = valid_request()
    req["improvement_job"]["status"] = "approved"
    assert_reject(req, gate.FAIL_IMPROVEMENT_JOB_NOT_DRY_RUN_PENDING)

    req = valid_request()
    req["improvement_job"]["dry_run"] = False
    assert_reject(req, gate.FAIL_IMPROVEMENT_JOB_NOT_DRY_RUN_PENDING)


def test_rejects_missing_required_identity_fields() -> None:
    req = valid_request()
    req["work_order_id"] = ""
    req["verification_result"]["receipt"]["work_order_id"] = ""
    req["ratchet_result"]["receipt"]["work_order_id"] = ""
    assert_reject(req, gate.FAIL_REQUIRED_FIELD)


def test_rejects_unaccepted_verifier_result() -> None:
    req = valid_request()
    req["verification_result"]["accepted"] = False
    req["verification_result"]["decision"] = AUTONOMOUS_SLICE_VERIFIER_REJECT
    assert_reject(req, gate.FAIL_VERIFICATION_RECEIPT)


def test_rejects_bad_or_already_retained_ratchet_result() -> None:
    req = valid_request()
    req["ratchet_result"]["decision"] = OUTCOME_RATCHET_REJECT
    assert_reject(req, gate.FAIL_RATCHET_RECEIPT)

    req = valid_request()
    req["ratchet_result"]["receipt"]["pattern_memory_write_performed"] = True
    result = assert_reject(req, gate.FAIL_RATCHET_RECEIPT)
    assert gate.FAIL_PATTERN_MEMORY_ALREADY_WRITTEN in result.rejection_reasons


def test_rejects_non_held_out_or_non_independent_suite() -> None:
    req = valid_request()
    req["held_out_regression"]["is_held_out"] = False
    assert_reject(req, gate.FAIL_HELD_OUT_SUITE)

    req = valid_request()
    req["held_out_regression"]["independent"] = False
    assert_reject(req, gate.FAIL_HELD_OUT_SUITE)


def test_rejects_author_generated_suite_or_same_author_as_worker() -> None:
    req = valid_request()
    req["held_out_regression"]["generated_by_author"] = True
    assert_reject(req, gate.FAIL_AUTHOR_GENERATED_SUITE)

    req = valid_request()
    req["held_out_regression"]["evidence_author_id"] = "worker-0102"
    assert_reject(req, gate.FAIL_AUTHOR_GENERATED_SUITE)


def test_rejects_failed_empty_or_malformed_regression_counts() -> None:
    req = valid_request()
    req["held_out_regression"]["passed"] = False
    assert_reject(req, gate.FAIL_REGRESSION_FAILED)

    req = valid_request()
    req["held_out_regression"]["failure_count"] = 1
    assert_reject(req, gate.FAIL_REGRESSION_FAILED)

    req = valid_request()
    req["held_out_regression"]["test_count"] = "not-a-number"
    assert_reject(req, gate.FAIL_HELD_OUT_SUITE)


def test_rejects_missing_digest_or_candidate_head_mismatch() -> None:
    req = valid_request()
    req["held_out_regression"]["suite_digest"] = ""
    assert_reject(req, gate.FAIL_DIGEST_BINDING)

    req = valid_request()
    req["held_out_regression"]["candidate_head_sha"] = "b" * 40
    assert_reject(req, gate.FAIL_DIGEST_BINDING)


def test_rejects_holoindex_gap_or_missing_freshness_receipt() -> None:
    req = valid_request()
    req["holoindex_evidence"]["index_gap_detected"] = True
    assert_reject(req, gate.FAIL_HOLOINDEX_EVIDENCE)

    req = valid_request()
    req["holoindex_evidence"]["holoindex_freshness_receipt_digest"] = ""
    assert_reject(req, gate.FAIL_HOLOINDEX_EVIDENCE)


def test_rejects_secret_bearing_evidence_before_retention() -> None:
    req = valid_request()
    req["held_out_regression"]["note"] = "api_key = leak"
    assert_reject(req, gate.FAIL_SECRET_IN_EVIDENCE)


def test_receipt_is_deterministic_and_json_serializable() -> None:
    first = gate.evaluate_held_out_recursive_improvement_regression_gate(valid_request())
    second = gate.evaluate_held_out_recursive_improvement_regression_gate(valid_request())

    assert first.receipt.gate_id == second.receipt.gate_id
    dumped = json.dumps(first.to_dict(), sort_keys=True)
    assert "held_out_recursive_gate_" in dumped
    assert "HELD_OUT_RECURSIVE_IMPROVEMENT_REGRESSION_GATE_ACCEPT" in dumped


def test_ast_boundary_no_execution_persistence_or_index_mutation() -> None:
    path = Path(
        "modules/infrastructure/wre_core/src/"
        "reddog_held_out_recursive_improvement_regression_gate.py"
    )
    tree = ast.parse(path.read_text(encoding="utf-8"))

    banned_import_roots = {
        "agent_db",
        "github",
        "holo_index",
        "openclaw_supervisor",
        "pattern_memory",
        "requests",
        "subprocess",
        "wre_core",
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                assert root not in banned_import_roots
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            root = module.split(".")[0]
            assert root not in banned_import_roots

    banned_names = {
        "Popen",
        "call",
        "check_call",
        "check_output",
        "create_autonomous_task",
        "execute",
        "index",
        "merge",
        "open",
        "push",
        "run",
        "store_verified_outcome",
        "system",
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            target = node.func
            if isinstance(target, ast.Attribute):
                assert target.attr not in banned_names
            elif isinstance(target, ast.Name):
                assert target.id not in banned_names
