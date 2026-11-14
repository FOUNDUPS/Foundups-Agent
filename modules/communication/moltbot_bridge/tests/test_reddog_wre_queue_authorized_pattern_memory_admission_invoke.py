"""Tests for REDDOG_WRE_QUEUE_AUTHORIZED_PATTERN_MEMORY_ADMISSION_INVOKE_PHASE1."""

from __future__ import annotations

import ast
import copy
import json
from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_held_out_regression_gate_invoke import (
    QUEUE_AUTHORIZED_HELD_OUT_REGRESSION_GATE_INVOKE_ACCEPT,
    QUEUE_AUTHORIZED_HELD_OUT_REGRESSION_GATE_INVOKE_REJECT,
    invoke_reddog_wre_queue_authorized_held_out_regression_gate,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_pattern_memory_admission_invoke import (
    QUEUE_AUTHORIZED_PATTERN_MEMORY_ADMISSION_INVOKE_ACCEPT,
    QUEUE_AUTHORIZED_PATTERN_MEMORY_ADMISSION_INVOKE_REJECT,
    QueueAuthorizedPatternMemoryAdmissionInvokeReason,
    invoke_reddog_wre_queue_authorized_pattern_memory_admission,
)
from modules.infrastructure.wre_core.src import (
    reddog_held_out_recursive_improvement_regression_gate as gate,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_verified_outcome_ratchet_invoke import (
    QUEUE_AUTHORIZED_VERIFIED_OUTCOME_RATCHET_INVOKE_ACCEPT,
    QUEUE_AUTHORIZED_VERIFIED_OUTCOME_RATCHET_INVOKE_REJECT,
)
from modules.infrastructure.wre_core.tests.test_reddog_held_out_recursive_improvement_regression_gate import (
    record_gate_fixture,
    valid_request as retention_request,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "reddog_wre_queue_authorized_pattern_memory_admission_invoke.py"
)
WORK_ORDER_ID = "wo-pattern-admission-1"
SLICE_NAME = "REDDOG_WRE_QUEUE_AUTHORIZED_PATTERN_MEMORY_ADMISSION_INVOKE_PHASE1"
GATE_ID = "held_out_recursive_gate_1234"
RATCHET_ID = "outcome_ratchet_1234"
VERIFIER_RECEIPT_ID = "wre_slice_verify_1234"
HEAD_SHA = "a" * 40


class FakePatternMemorySink:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.records: list[dict] = []

    def store_verified_outcome(self, record):
        if self.fail:
            raise RuntimeError("sink failed")
        self.records.append(dict(record))
        return "pattern-memory-record-1"


def _digest(ch: str) -> str:
    return "sha256:" + ch * 64


def _queue_gate_result(*, accepted: bool = True, decision: str | None = None) -> dict:
    return {
        "decision": decision or QUEUE_AUTHORIZED_HELD_OUT_REGRESSION_GATE_INVOKE_ACCEPT,
        "rejection_reasons": [] if accepted else [gate.FAIL_REGRESSION_FAILED],
        "explicit_queue_authorized_held_out_regression_gate_requested": True,
        "gate_result": {
            "decision": (
                gate.HELD_OUT_RECURSIVE_IMPROVEMENT_REGRESSION_GATE_ACCEPT
                if accepted
                else gate.HELD_OUT_RECURSIVE_IMPROVEMENT_REGRESSION_GATE_REJECT
            ),
            "accepted": accepted,
            "rejection_reasons": [] if accepted else [gate.FAIL_REGRESSION_FAILED],
            "pattern_memory_admission_allowed": accepted,
            "receipt": {
                "gate_id": GATE_ID,
                "work_order_id": WORK_ORDER_ID,
                "slice_name": SLICE_NAME,
                "improvement_job_id": "imp_wsp_violation_1234_abcd",
                "verifier_receipt_id": VERIFIER_RECEIPT_ID,
                "ratchet_id": RATCHET_ID,
                "held_out_suite_id": "heldout-wre-recursive-001",
                "held_out_suite_digest": _digest("1"),
                "baseline_digest": _digest("2"),
                "candidate_digest": _digest("3"),
                "candidate_head_sha": HEAD_SHA,
                "regression_test_count": 12,
                "pattern_memory_admission_requested": accepted,
                "pattern_memory_admission_allowed": accepted,
                "rejection_reasons": [] if accepted else [gate.FAIL_REGRESSION_FAILED],
            },
        },
    }


def _queue_gate_result_with_runtime_binding() -> dict:
    result = _queue_gate_result()
    receipt = result["gate_result"]["receipt"]
    receipt["model_runtime_binding_receipt_id"] = "reddog_model_runtime_binding:test"
    receipt["model_runtime_binding_digest"] = _digest("5")
    return result


def _admission_request() -> dict:
    return {
        "work_order_id": WORK_ORDER_ID,
        "admission_metadata": {
            "source": "held_out_regression_gate",
            "retention_policy": "verified_recursive_improvement_only",
        },
    }


def _invoke(
    *,
    queue_gate: dict | None = None,
    request: dict | None = None,
    sink: FakePatternMemorySink | None = None,
):
    return invoke_reddog_wre_queue_authorized_pattern_memory_admission(
        explicit_queue_authorized_pattern_memory_admission_requested=True,
        queue_held_out_gate_result=queue_gate or _queue_gate_result(),
        admission_request=request or _admission_request(),
        sink=sink or FakePatternMemorySink(),
    )


def test_admits_verified_held_out_outcome_to_injected_sink() -> None:
    sink = FakePatternMemorySink()

    result = _invoke(sink=sink)

    assert result.decision == QUEUE_AUTHORIZED_PATTERN_MEMORY_ADMISSION_INVOKE_ACCEPT
    assert result.rejection_reasons == []
    assert result.pattern_memory_write_performed is True
    assert result.receipt is not None
    assert result.receipt.pattern_memory_record_id == "pattern-memory-record-1"
    assert result.receipt.gate_id == GATE_ID
    assert result.receipt.ratchet_id == RATCHET_ID
    assert result.receipt.model_runtime_binding_receipt_id is None
    assert result.receipt.model_runtime_binding_digest == ""
    assert result.receipt.no_command_execution_performed is True
    assert result.receipt.no_pr_publish_performed is True
    assert result.receipt.no_merge_performed is True
    assert result.receipt.no_reward_settlement_performed is True
    assert result.receipt.no_holoindex_reindex_performed is True
    assert len(sink.records) == 1
    assert sink.records[0]["record_type"] == "reddog_verified_recursive_improvement_outcome"
    assert sink.records[0]["work_order_id"] == WORK_ORDER_ID


@pytest.mark.parametrize("ack", [None, "", "   ", False])
def test_sink_without_record_acknowledgment_is_not_admitted(ack):
    class InvalidAckSink:
        def store_verified_outcome(self, record):
            return ack

    result = _invoke(sink=InvalidAckSink())
    assert result.decision == QUEUE_AUTHORIZED_PATTERN_MEMORY_ADMISSION_INVOKE_REJECT
    assert QueueAuthorizedPatternMemoryAdmissionInvokeReason.SINK_WRITE_FAILED in result.rejection_reasons
    assert result.pattern_memory_write_performed is False


def test_sink_cannot_mutate_admission_receipt_or_request():
    request = _admission_request()
    original = copy.deepcopy(request)
    expected_digest = _invoke(request=copy.deepcopy(request)).receipt.record_digest

    class MutatingSink:
        def store_verified_outcome(self, record):
            record["work_order_id"] = "foreign-work"
            record["candidate_digest"] = _digest("9")
            return "pattern-record-1"

    result = _invoke(request=request, sink=MutatingSink())
    assert result.decision == QUEUE_AUTHORIZED_PATTERN_MEMORY_ADMISSION_INVOKE_ACCEPT
    assert result.receipt.work_order_id == WORK_ORDER_ID
    assert result.receipt.record_digest == expected_digest
    assert request == original


@pytest.mark.parametrize("case", ["accepted", "invalid-cost", "failed-outcome", "changed-verifier"])
def test_recording_through_retention_to_memory_sink(case):
    request = retention_request()
    recorded = record_gate_fixture(
        request, invalid_cost=case == "invalid-cost", failed_outcome=case == "failed-outcome",
    )
    if case == "changed-verifier":
        request["verification_result"]["receipt"]["head_sha"] = "b" * 40
        request["held_out_regression"]["candidate_head_sha"] = "b" * 40
    queue_retention = invoke_reddog_wre_queue_authorized_held_out_regression_gate(
        explicit_queue_authorized_held_out_regression_gate_requested=True,
        queue_verified_outcome_ratchet_result={
            "decision": (QUEUE_AUTHORIZED_VERIFIED_OUTCOME_RATCHET_INVOKE_ACCEPT
                         if recorded.accepted else QUEUE_AUTHORIZED_VERIFIED_OUTCOME_RATCHET_INVOKE_REJECT),
            "ratchet_result": recorded.to_dict(),
        },
        held_out_gate_request=request,
    )
    sink = FakePatternMemorySink()
    result = _invoke(
        queue_gate=queue_retention.to_dict(),
        request={"work_order_id": request["work_order_id"]}, sink=sink,
    )
    accepted = case == "accepted"
    assert result.pattern_memory_write_performed is accepted
    assert len(sink.records) == int(accepted)
    assert (result.decision == QUEUE_AUTHORIZED_PATTERN_MEMORY_ADMISSION_INVOKE_ACCEPT) is accepted
    if accepted:
        assert sink.records[0]["ratchet_id"] == recorded.receipt.ratchet_id
        assert sink.records[0]["gate_id"] == queue_retention.gate_result.receipt.gate_id


def test_admission_record_carries_model_runtime_binding_from_gate() -> None:
    sink = FakePatternMemorySink()

    result = _invoke(queue_gate=_queue_gate_result_with_runtime_binding(), sink=sink)

    assert result.decision == QUEUE_AUTHORIZED_PATTERN_MEMORY_ADMISSION_INVOKE_ACCEPT
    assert result.receipt is not None
    assert (
        result.receipt.model_runtime_binding_receipt_id
        == "reddog_model_runtime_binding:test"
    )
    assert result.receipt.model_runtime_binding_digest == _digest("5")
    assert (
        sink.records[0]["model_runtime_binding_receipt_id"]
        == "reddog_model_runtime_binding:test"
    )
    assert sink.records[0]["model_runtime_binding_digest"] == _digest("5")


def test_admission_request_cannot_override_model_runtime_binding() -> None:
    request = _admission_request()
    request["model_runtime_binding_receipt_id"] = "reddog_model_runtime_binding:test"
    request["model_runtime_binding_digest"] = _digest("6")
    sink = FakePatternMemorySink()

    result = _invoke(
        queue_gate=_queue_gate_result_with_runtime_binding(),
        request=request,
        sink=sink,
    )

    assert result.decision == QUEUE_AUTHORIZED_PATTERN_MEMORY_ADMISSION_INVOKE_REJECT
    assert (
        QueueAuthorizedPatternMemoryAdmissionInvokeReason.MODEL_RUNTIME_BINDING_MISMATCH
        in result.rejection_reasons
    )
    assert sink.records == []


def test_explicit_invoke_missing_rejects_before_sink() -> None:
    sink = FakePatternMemorySink()

    result = invoke_reddog_wre_queue_authorized_pattern_memory_admission(
        explicit_queue_authorized_pattern_memory_admission_requested=False,
        queue_held_out_gate_result=_queue_gate_result(),
        admission_request=_admission_request(),
        sink=sink,
    )

    assert result.decision == QUEUE_AUTHORIZED_PATTERN_MEMORY_ADMISSION_INVOKE_REJECT
    assert (
        QueueAuthorizedPatternMemoryAdmissionInvokeReason.EXPLICIT_INVOKE_MISSING
        in result.rejection_reasons
    )
    assert sink.records == []


def test_sink_required_rejects() -> None:
    result = invoke_reddog_wre_queue_authorized_pattern_memory_admission(
        explicit_queue_authorized_pattern_memory_admission_requested=True,
        queue_held_out_gate_result=_queue_gate_result(),
        admission_request=_admission_request(),
        sink=None,
    )

    assert result.decision == QUEUE_AUTHORIZED_PATTERN_MEMORY_ADMISSION_INVOKE_REJECT
    assert QueueAuthorizedPatternMemoryAdmissionInvokeReason.SINK_REQUIRED in result.rejection_reasons


def test_unaccepted_held_out_gate_rejects_before_sink() -> None:
    sink = FakePatternMemorySink()

    result = _invoke(
        queue_gate=_queue_gate_result(
            accepted=False,
            decision=QUEUE_AUTHORIZED_HELD_OUT_REGRESSION_GATE_INVOKE_REJECT,
        ),
        sink=sink,
    )

    assert result.decision == QUEUE_AUTHORIZED_PATTERN_MEMORY_ADMISSION_INVOKE_REJECT
    assert (
        QueueAuthorizedPatternMemoryAdmissionInvokeReason.HELD_OUT_INVOKE_NOT_ACCEPTED
        in result.rejection_reasons
    )
    assert (
        QueueAuthorizedPatternMemoryAdmissionInvokeReason.GATE_PAYLOAD_NOT_ACCEPTED
        in result.rejection_reasons
    )
    assert sink.records == []


def test_gate_without_admission_allowed_rejects() -> None:
    queue_gate = _queue_gate_result()
    queue_gate["gate_result"]["pattern_memory_admission_allowed"] = False
    queue_gate["gate_result"]["receipt"]["pattern_memory_admission_allowed"] = False
    sink = FakePatternMemorySink()

    result = _invoke(queue_gate=queue_gate, sink=sink)

    assert result.decision == QUEUE_AUTHORIZED_PATTERN_MEMORY_ADMISSION_INVOKE_REJECT
    assert (
        QueueAuthorizedPatternMemoryAdmissionInvokeReason.PATTERN_MEMORY_NOT_ALLOWED
        in result.rejection_reasons
    )
    assert sink.records == []


def test_work_order_mismatch_rejects_before_sink() -> None:
    request = _admission_request()
    request["work_order_id"] = "other-work-order"
    sink = FakePatternMemorySink()

    result = _invoke(request=request, sink=sink)

    assert result.decision == QUEUE_AUTHORIZED_PATTERN_MEMORY_ADMISSION_INVOKE_REJECT
    assert (
        QueueAuthorizedPatternMemoryAdmissionInvokeReason.WORK_ORDER_ID_MISMATCH
        in result.rejection_reasons
    )
    assert sink.records == []


def test_secret_in_record_rejects_before_sink() -> None:
    request = _admission_request()
    request["admission_metadata"]["note"] = "api_key = leak"
    sink = FakePatternMemorySink()

    result = _invoke(request=request, sink=sink)

    assert result.decision == QUEUE_AUTHORIZED_PATTERN_MEMORY_ADMISSION_INVOKE_REJECT
    assert QueueAuthorizedPatternMemoryAdmissionInvokeReason.SECRET_IN_RECORD in result.rejection_reasons
    assert sink.records == []


def test_sink_failure_rejects_with_receipt() -> None:
    sink = FakePatternMemorySink(fail=True)

    result = _invoke(sink=sink)

    assert result.decision == QUEUE_AUTHORIZED_PATTERN_MEMORY_ADMISSION_INVOKE_REJECT
    assert QueueAuthorizedPatternMemoryAdmissionInvokeReason.SINK_WRITE_FAILED in result.rejection_reasons
    assert result.receipt is not None
    assert result.receipt.pattern_memory_record_id is None
    assert result.pattern_memory_write_performed is False


def test_result_is_json_serializable_and_deterministic() -> None:
    first = _invoke()
    second = _invoke()

    assert first.receipt is not None
    assert second.receipt is not None
    assert first.receipt.admission_id == second.receipt.admission_id
    payload = first.to_dict()
    assert payload["decision"] == QUEUE_AUTHORIZED_PATTERN_MEMORY_ADMISSION_INVOKE_ACCEPT
    json.dumps(payload, sort_keys=True)


def test_module_has_no_direct_shell_git_pr_merge_reward_or_holoindex_authority() -> None:
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
        "create_draft_pr",
        "push_branch",
        "mark_ready",
        "merge_pr",
        "settle_reward",
        "holo_index.py --index",
        "PatternMemory(",
    )
    for token in forbidden_tokens:
        assert token not in source
