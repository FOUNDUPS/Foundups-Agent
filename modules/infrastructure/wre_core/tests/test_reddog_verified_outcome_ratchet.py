"""Tests for REDDOG_VERIFIED_OUTCOME_RATCHET_PHASE1."""

from __future__ import annotations

import ast
import json
from pathlib import Path

from modules.infrastructure.wre_core.src import reddog_verified_outcome_ratchet as ratchet
from modules.infrastructure.wre_core.src.reddog_verified_draft_pr_publish import (
    VERIFIED_DRAFT_PR_PUBLISH_ACCEPT,
)
from modules.infrastructure.wre_core.src.wre_autonomous_slice_verifier_runtime import (
    AUTONOMOUS_SLICE_VERIFIER_ACCEPT,
    AUTONOMOUS_SLICE_VERIFIER_REJECT,
)


def _digest(ch: str) -> str:
    return "sha256:" + ch * 64


class FakePatternMemorySink:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.records: list = []

    def store_verified_outcome(self, record):
        if self.fail:
            raise RuntimeError("sink failed")
        self.records.append(dict(record))
        return "pattern-record-1"


class FailingStore:
    def append(self, record):
        raise RuntimeError("store failed")


def valid_request() -> dict:
    return {
        "work_order_id": "wo-ratchet-1",
        "slice_name": "REDDOG_VERIFIED_OUTCOME_RATCHET_PHASE1",
        "outcome_status": "accepted",
        "request_receipt": {
            "request_id": "req-1",
            "principal_id": "012",
            "work_focus_digest": _digest("1"),
        },
        "execution_receipts": [
            {"step": "worktree_created", "receipt_id": "exec-1"},
            {"step": "tests_run", "receipt_id": "exec-2"},
        ],
        "verification_result": {
            "accepted": True,
            "decision": AUTONOMOUS_SLICE_VERIFIER_ACCEPT,
            "receipt": {
                "receipt_id": "wre_slice_verify_1234",
                "work_order_id": "wo-ratchet-1",
                "slice_name": "REDDOG_VERIFIED_OUTCOME_RATCHET_PHASE1",
            },
        },
        "publish_result": {
            "accepted": True,
            "decision": VERIFIED_DRAFT_PR_PUBLISH_ACCEPT,
            "receipt": {
                "receipt_id": "verified_draft_pr_1234",
                "draft_pr_url": "https://github.com/FOUNDUPS/Foundups-Agent/pull/1000",
            },
        },
        "cost_receipt": {
            "total_tokens": 1234,
            "estimated_cost_usd": 0.12,
        },
        "latency_receipt": {
            "wall_time_ms": 1000,
            "queue_time_ms": 10,
        },
        "acceptance_receipt": {
            "accepted": True,
            "reason": "verifier and draft PR publish accepted",
        },
        "failure_receipt": None,
        "holoindex_evidence": {
            "index_gap_detected": False,
            "holoindex_freshness_receipt_digest": _digest("2"),
        },
        "enable_pattern_memory_write": False,
    }


def request_with_runtime_binding() -> dict:
    req = valid_request()
    req["verification_result"]["receipt"]["model_runtime_binding_receipt_id"] = (
        "reddog_model_runtime_binding:test"
    )
    req["verification_result"]["receipt"]["model_runtime_binding_digest"] = _digest("3")
    req["publish_result"]["receipt"]["model_runtime_binding_receipt_id"] = (
        "reddog_model_runtime_binding:test"
    )
    req["publish_result"]["receipt"]["model_runtime_binding_digest"] = _digest("3")
    return req


def assert_reject(req: dict, code: str) -> ratchet.VerifiedOutcomeRatchetResult:
    store = ratchet.InMemoryOutcomeRatchetStore()
    result = ratchet.ratchet_verified_outcome(req, store=store)
    assert result.accepted is False
    assert result.decision == ratchet.OUTCOME_RATCHET_REJECT
    assert code in result.rejection_reasons
    assert code in result.receipt.rejection_reasons
    assert result.no_command_execution_performed is True
    assert result.no_pr_publish_performed is True
    assert result.no_merge_performed is True
    assert result.no_reward_settlement_performed is True
    return result


def test_records_verified_outcome_without_pattern_memory_by_default() -> None:
    store = ratchet.InMemoryOutcomeRatchetStore()
    result = ratchet.ratchet_verified_outcome(valid_request(), store=store)

    assert result.accepted is True
    assert result.decision == ratchet.OUTCOME_RATCHET_RECORDED
    assert result.receipt.pattern_memory_eligible is True
    assert result.receipt.pattern_memory_write_performed is False
    assert result.receipt.pattern_memory_record_id is None
    assert result.receipt.model_runtime_binding_receipt_id is None
    assert result.receipt.model_runtime_binding_digest == ""
    assert result.store_record_id == result.receipt.ratchet_id
    assert len(store.records) == 1
    assert store.records[0]["ratchet_receipt"]["ratchet_id"] == result.receipt.ratchet_id


def test_ratchet_receipt_carries_model_runtime_binding_from_verification_chain() -> None:
    store = ratchet.InMemoryOutcomeRatchetStore()

    result = ratchet.ratchet_verified_outcome(request_with_runtime_binding(), store=store)

    assert result.accepted is True
    assert (
        result.receipt.model_runtime_binding_receipt_id
        == "reddog_model_runtime_binding:test"
    )
    assert result.receipt.model_runtime_binding_digest == _digest("3")
    assert (
        store.records[0]["ratchet_receipt"]["model_runtime_binding_receipt_id"]
        == "reddog_model_runtime_binding:test"
    )


def test_ratchet_rejects_model_runtime_binding_mismatch() -> None:
    req = request_with_runtime_binding()
    req["publish_result"]["receipt"]["model_runtime_binding_digest"] = _digest("4")

    assert_reject(req, ratchet.FAIL_MODEL_RUNTIME_BINDING)


def test_pattern_memory_sink_receives_only_verified_accepted_outcome() -> None:
    req = valid_request()
    req["enable_pattern_memory_write"] = True
    sink = FakePatternMemorySink()
    store = ratchet.InMemoryOutcomeRatchetStore()

    result = ratchet.ratchet_verified_outcome(req, store=store, pattern_memory_sink=sink)

    assert result.accepted is True
    assert result.receipt.pattern_memory_write_performed is True
    assert result.receipt.pattern_memory_record_id == "pattern-record-1"
    assert len(sink.records) == 1


def test_rejected_verification_records_failure_but_blocks_pattern_memory() -> None:
    req = valid_request()
    req["verification_result"]["accepted"] = False
    req["verification_result"]["decision"] = AUTONOMOUS_SLICE_VERIFIER_REJECT
    req["enable_pattern_memory_write"] = True
    store = ratchet.InMemoryOutcomeRatchetStore()
    result = ratchet.ratchet_verified_outcome(req, store=store)

    assert result.accepted is False
    assert ratchet.FAIL_VERIFICATION_RECEIPT in result.rejection_reasons
    assert ratchet.FAIL_PATTERN_MEMORY_UNVERIFIED in result.rejection_reasons
    assert len(store.records) == 1
    assert result.receipt.pattern_memory_write_performed is False


def test_accepted_outcome_requires_publish_receipt() -> None:
    req = valid_request()
    req["publish_result"]["accepted"] = False
    assert_reject(req, ratchet.FAIL_PUBLISH_RECEIPT)


def test_failed_outcome_can_be_recorded_without_publish_or_pattern_memory() -> None:
    req = valid_request()
    req["outcome_status"] = "failed"
    req["publish_result"] = {}
    req["acceptance_receipt"] = {}
    req["failure_receipt"] = {"failed": True, "reason": "tests failed"}
    store = ratchet.InMemoryOutcomeRatchetStore()

    result = ratchet.ratchet_verified_outcome(req, store=store)

    assert result.accepted is True
    assert result.receipt.pattern_memory_eligible is False
    assert result.receipt.failure_receipt_digest
    assert len(store.records) == 1


def test_rejects_missing_receipt_set() -> None:
    req = valid_request()
    req["execution_receipts"] = []
    assert_reject(req, ratchet.FAIL_RECEIPT_SET)

    req = valid_request()
    req["request_receipt"] = {}
    assert_reject(req, ratchet.FAIL_RECEIPT_SET)


def test_rejects_missing_or_negative_cost_latency() -> None:
    req = valid_request()
    req["cost_receipt"]["total_tokens"] = -1
    assert_reject(req, ratchet.FAIL_COST_LATENCY)

    req = valid_request()
    req["latency_receipt"]["wall_time_ms"] = -1
    assert_reject(req, ratchet.FAIL_COST_LATENCY)


def test_rejects_holoindex_gap_or_missing_freshness() -> None:
    req = valid_request()
    req["holoindex_evidence"]["index_gap_detected"] = True
    assert_reject(req, ratchet.FAIL_HOLOINDEX_EVIDENCE)

    req = valid_request()
    req["holoindex_evidence"]["holoindex_freshness_receipt_digest"] = ""
    assert_reject(req, ratchet.FAIL_HOLOINDEX_EVIDENCE)


def test_secret_receipt_rejects_and_is_not_persisted() -> None:
    req = valid_request()
    req["execution_receipts"][0]["detail"] = "api_key = leak"
    store = ratchet.InMemoryOutcomeRatchetStore()

    result = ratchet.ratchet_verified_outcome(req, store=store)

    assert result.accepted is False
    assert ratchet.FAIL_SECRET_IN_RECEIPT in result.rejection_reasons
    assert store.records == []


def test_store_failure_rejects() -> None:
    result = ratchet.ratchet_verified_outcome(valid_request(), store=FailingStore())

    assert result.accepted is False
    assert result.decision == ratchet.OUTCOME_RATCHET_REJECT
    assert result.rejection_reasons == [ratchet.FAIL_STORE_WRITE]
    assert result.store_record_id is None


def test_pattern_memory_sink_failure_rejects_after_store() -> None:
    req = valid_request()
    req["enable_pattern_memory_write"] = True
    store = ratchet.InMemoryOutcomeRatchetStore()
    sink = FakePatternMemorySink(fail=True)

    result = ratchet.ratchet_verified_outcome(req, store=store, pattern_memory_sink=sink)

    assert result.accepted is False
    assert result.rejection_reasons == [ratchet.FAIL_PATTERN_MEMORY_WRITE]
    assert len(store.records) == 1


def test_jsonl_store_appends_records(tmp_path: Path) -> None:
    path = tmp_path / "ratchet" / "outcomes.jsonl"
    store = ratchet.JsonlOutcomeRatchetStore(path)

    result = ratchet.ratchet_verified_outcome(valid_request(), store=store)

    assert result.accepted is True
    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["ratchet_receipt"]["ratchet_id"] == result.receipt.ratchet_id


def test_ratchet_receipt_is_deterministic_and_serializable() -> None:
    first = ratchet.ratchet_verified_outcome(
        valid_request(),
        store=ratchet.InMemoryOutcomeRatchetStore(),
    )
    second = ratchet.ratchet_verified_outcome(
        valid_request(),
        store=ratchet.InMemoryOutcomeRatchetStore(),
    )

    assert first.receipt.ratchet_id == second.receipt.ratchet_id
    dumped = json.dumps(first.to_dict(), sort_keys=True)
    assert "outcome_ratchet_" in dumped


def test_ast_boundary_no_commands_github_holoindex_or_pattern_memory_import() -> None:
    path = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "reddog_verified_outcome_ratchet.py"
    )
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports = set()
    calls = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                calls.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                calls.add(node.func.attr)

    forbidden_imports = {
        "os",
        "subprocess",
        "socket",
        "requests",
        "sqlite3",
        "modules.infrastructure.wre_core.src.pattern_memory",
        "holo_index",
    }
    forbidden_calls = {
        "eval",
        "exec",
        "system",
        "popen",
        "run",
        "check_call",
        "check_output",
        "merge",
        "create_draft_pr",
        "push_branch",
    }

    assert imports.isdisjoint(forbidden_imports)
    assert calls.isdisjoint(forbidden_calls)
