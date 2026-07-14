"""Tests for REDDOG_WRE_QUEUE_AUTHORIZED_VERIFIED_OUTCOME_RATCHET_INVOKE_PHASE1."""

from __future__ import annotations

import ast
import json
from pathlib import Path

from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_verified_draft_pr_publish_invoke import (
    QUEUE_AUTHORIZED_VERIFIED_DRAFT_PR_PUBLISH_INVOKE_ACCEPT,
    QUEUE_AUTHORIZED_VERIFIED_DRAFT_PR_PUBLISH_INVOKE_REJECT,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_verified_outcome_ratchet_invoke import (
    QUEUE_AUTHORIZED_VERIFIED_OUTCOME_RATCHET_INVOKE_ACCEPT,
    QUEUE_AUTHORIZED_VERIFIED_OUTCOME_RATCHET_INVOKE_REJECT,
    QueueAuthorizedVerifiedOutcomeRatchetInvokeReason,
    invoke_reddog_wre_queue_authorized_verified_outcome_ratchet,
)
from modules.infrastructure.wre_core.src import reddog_verified_outcome_ratchet as ratchet
from modules.infrastructure.wre_core.src.reddog_verified_draft_pr_publish import (
    VERIFIED_DRAFT_PR_PUBLISH_ACCEPT,
    VERIFIED_DRAFT_PR_PUBLISH_REJECT,
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
    / "reddog_wre_queue_authorized_verified_outcome_ratchet_invoke.py"
)
WORK_ORDER_ID = "wo-queue-ratchet-1"
SLICE_NAME = "REDDOG_WRE_QUEUE_AUTHORIZED_VERIFIED_OUTCOME_RATCHET_INVOKE_PHASE1"
VERIFIER_RECEIPT_ID = "wre_slice_verify_1234"
PUBLISH_RECEIPT_ID = "verified_draft_pr_1234"
HEAD_SHA = "a" * 40
ARTIFACT = "modules/communication/moltbot_bridge/tests/fixtures/reddog_queue_ratchet/README.md"


class FakePatternMemorySink:
    def __init__(self) -> None:
        self.records: list[dict] = []

    def store_verified_outcome(self, record):
        self.records.append(dict(record))
        return "pattern-memory-record-1"


def _digest(ch: str) -> str:
    return "sha256:" + ch * 64


def _queue_publish_result(*, accepted: bool = True, decision: str | None = None) -> dict:
    return {
        "decision": decision or QUEUE_AUTHORIZED_VERIFIED_DRAFT_PR_PUBLISH_INVOKE_ACCEPT,
        "rejection_reasons": [] if accepted else ["FAIL_PUSH_BRANCH"],
        "explicit_queue_authorized_verified_draft_pr_publish_requested": True,
        "publish_result": {
            "decision": (
                VERIFIED_DRAFT_PR_PUBLISH_ACCEPT
                if accepted
                else VERIFIED_DRAFT_PR_PUBLISH_REJECT
            ),
            "accepted": accepted,
            "rejection_reasons": [] if accepted else ["FAIL_PUSH_BRANCH"],
            "receipt": {
                "receipt_id": PUBLISH_RECEIPT_ID,
                "work_order_id": WORK_ORDER_ID,
                "slice_name": SLICE_NAME,
                "verifier_receipt_id": VERIFIER_RECEIPT_ID,
                "branch_name": "feat/reddog-queue-ratchet",
                "base_branch": "main",
                "verified_head_sha": HEAD_SHA,
                "draft_pr_url": "https://github.com/FOUNDUPS/Foundups-Agent/pull/3000",
                "changed_paths": [ARTIFACT],
                "accepted": accepted,
                "rejection_reasons": [] if accepted else ["FAIL_PUSH_BRANCH"],
            },
        },
    }


def _ratchet_request() -> dict:
    return {
        "work_order_id": WORK_ORDER_ID,
        "slice_name": SLICE_NAME,
        "outcome_status": "accepted",
        "request_receipt": {
            "request_id": "request-1",
            "principal_id": "012",
            "work_focus_digest": _digest("1"),
        },
        "execution_receipts": [
            {"step": "worktree_created", "receipt_id": "exec-1"},
            {"step": "bounded_worker_pilot", "receipt_id": "exec-2"},
            {"step": "draft_pr_published", "receipt_id": PUBLISH_RECEIPT_ID},
        ],
        "verification_result": {
            "accepted": True,
            "decision": AUTONOMOUS_SLICE_VERIFIER_ACCEPT,
            "receipt": {
                "receipt_id": VERIFIER_RECEIPT_ID,
                "work_order_id": WORK_ORDER_ID,
                "slice_name": SLICE_NAME,
                "worker_id": "worker:author",
                "verifier_id": "worker:verifier",
                "head_sha": HEAD_SHA,
                "changed_paths": [ARTIFACT],
            },
        },
        "publish_result": {
            "accepted": False,
            "decision": VERIFIED_DRAFT_PR_PUBLISH_REJECT,
            "receipt": {},
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
            "reason": "queue verifier and draft PR publish accepted",
        },
        "failure_receipt": None,
        "holoindex_evidence": {
            "index_gap_detected": False,
            "holoindex_freshness_receipt_digest": _digest("2"),
        },
        "enable_pattern_memory_write": False,
    }


def _invoke(
    *,
    queue_publish: dict | None = None,
    request: dict | None = None,
    store: ratchet.InMemoryOutcomeRatchetStore | None = None,
    explicit_pattern: bool = False,
    sink: FakePatternMemorySink | None = None,
):
    return invoke_reddog_wre_queue_authorized_verified_outcome_ratchet(
        explicit_queue_authorized_verified_outcome_ratchet_requested=True,
        queue_verified_draft_pr_publish_result=queue_publish or _queue_publish_result(),
        ratchet_request=request or _ratchet_request(),
        store=store or ratchet.InMemoryOutcomeRatchetStore(),
        explicit_pattern_memory_write_requested=explicit_pattern,
        pattern_memory_sink=sink,
    )


def test_records_outcome_from_accepted_queue_publish_result() -> None:
    store = ratchet.InMemoryOutcomeRatchetStore()

    result = _invoke(store=store)

    assert result.decision == QUEUE_AUTHORIZED_VERIFIED_OUTCOME_RATCHET_INVOKE_ACCEPT
    assert result.rejection_reasons == []
    assert result.ratchet_result is not None
    assert result.ratchet_result.decision == ratchet.OUTCOME_RATCHET_RECORDED
    assert result.ratchet_result.accepted is True
    assert result.ratchet_result.receipt.publish_receipt_id == PUBLISH_RECEIPT_ID
    assert result.ratchet_result.receipt.pattern_memory_write_performed is False
    assert len(store.records) == 1
    assert store.records[0]["publish_result"]["decision"] == VERIFIED_DRAFT_PR_PUBLISH_ACCEPT
    assert result.no_command_execution_performed is True
    assert result.no_pr_publish_performed is True
    assert result.no_ready_performed is True
    assert result.no_merge_performed is True
    assert result.no_reward_settlement_performed is True
    assert result.no_holoindex_reindex_performed is True


def test_explicit_invoke_missing_rejects_before_store() -> None:
    store = ratchet.InMemoryOutcomeRatchetStore()

    result = invoke_reddog_wre_queue_authorized_verified_outcome_ratchet(
        explicit_queue_authorized_verified_outcome_ratchet_requested=False,
        queue_verified_draft_pr_publish_result=_queue_publish_result(),
        ratchet_request=_ratchet_request(),
        store=store,
    )

    assert result.decision == QUEUE_AUTHORIZED_VERIFIED_OUTCOME_RATCHET_INVOKE_REJECT
    assert (
        QueueAuthorizedVerifiedOutcomeRatchetInvokeReason.EXPLICIT_INVOKE_MISSING
        in result.rejection_reasons
    )
    assert store.records == []


def test_store_required_rejects() -> None:
    result = invoke_reddog_wre_queue_authorized_verified_outcome_ratchet(
        explicit_queue_authorized_verified_outcome_ratchet_requested=True,
        queue_verified_draft_pr_publish_result=_queue_publish_result(),
        ratchet_request=_ratchet_request(),
        store=None,
    )

    assert result.decision == QUEUE_AUTHORIZED_VERIFIED_OUTCOME_RATCHET_INVOKE_REJECT
    assert QueueAuthorizedVerifiedOutcomeRatchetInvokeReason.STORE_REQUIRED in result.rejection_reasons


def test_unaccepted_queue_publish_rejects_before_store() -> None:
    store = ratchet.InMemoryOutcomeRatchetStore()

    result = _invoke(
        queue_publish=_queue_publish_result(
            accepted=False,
            decision=QUEUE_AUTHORIZED_VERIFIED_DRAFT_PR_PUBLISH_INVOKE_REJECT,
        ),
        store=store,
    )

    assert result.decision == QUEUE_AUTHORIZED_VERIFIED_OUTCOME_RATCHET_INVOKE_REJECT
    assert (
        QueueAuthorizedVerifiedOutcomeRatchetInvokeReason.PUBLISH_INVOKE_NOT_ACCEPTED
        in result.rejection_reasons
    )
    assert (
        QueueAuthorizedVerifiedOutcomeRatchetInvokeReason.PUBLISH_PAYLOAD_NOT_ACCEPTED
        in result.rejection_reasons
    )
    assert store.records == []


def test_verifier_receipt_mismatch_rejects_before_store() -> None:
    request = _ratchet_request()
    request["verification_result"]["receipt"]["receipt_id"] = "other-verifier"
    store = ratchet.InMemoryOutcomeRatchetStore()

    result = _invoke(request=request, store=store)

    assert result.decision == QUEUE_AUTHORIZED_VERIFIED_OUTCOME_RATCHET_INVOKE_REJECT
    assert (
        QueueAuthorizedVerifiedOutcomeRatchetInvokeReason.VERIFIER_RECEIPT_MISMATCH
        in result.rejection_reasons
    )
    assert store.records == []


def test_work_order_mismatch_rejects_before_store() -> None:
    request = _ratchet_request()
    request["work_order_id"] = "other-work-order"
    store = ratchet.InMemoryOutcomeRatchetStore()

    result = _invoke(request=request, store=store)

    assert result.decision == QUEUE_AUTHORIZED_VERIFIED_OUTCOME_RATCHET_INVOKE_REJECT
    assert (
        QueueAuthorizedVerifiedOutcomeRatchetInvokeReason.WORK_ORDER_ID_MISMATCH
        in result.rejection_reasons
    )
    assert store.records == []


def test_pattern_memory_requires_explicit_flag_and_sink() -> None:
    request = _ratchet_request()
    request["enable_pattern_memory_write"] = True
    store = ratchet.InMemoryOutcomeRatchetStore()

    result = _invoke(request=request, store=store)

    assert result.decision == QUEUE_AUTHORIZED_VERIFIED_OUTCOME_RATCHET_INVOKE_REJECT
    assert (
        QueueAuthorizedVerifiedOutcomeRatchetInvokeReason.PATTERN_MEMORY_EXPLICIT_MISSING
        in result.rejection_reasons
    )
    assert store.records == []

    result = _invoke(request=request, store=store, explicit_pattern=True)

    assert result.decision == QUEUE_AUTHORIZED_VERIFIED_OUTCOME_RATCHET_INVOKE_REJECT
    assert (
        QueueAuthorizedVerifiedOutcomeRatchetInvokeReason.PATTERN_MEMORY_SINK_REQUIRED
        in result.rejection_reasons
    )
    assert store.records == []


def test_pattern_memory_write_can_be_explicitly_allowed_after_verification() -> None:
    request = _ratchet_request()
    request["enable_pattern_memory_write"] = True
    store = ratchet.InMemoryOutcomeRatchetStore()
    sink = FakePatternMemorySink()

    result = _invoke(request=request, store=store, explicit_pattern=True, sink=sink)

    assert result.decision == QUEUE_AUTHORIZED_VERIFIED_OUTCOME_RATCHET_INVOKE_ACCEPT
    assert result.ratchet_result is not None
    assert result.ratchet_result.receipt.pattern_memory_write_performed is True
    assert result.ratchet_result.receipt.pattern_memory_record_id == "pattern-memory-record-1"
    assert len(store.records) == 1
    assert len(sink.records) == 1


def test_ratchet_rejection_is_preserved() -> None:
    request = _ratchet_request()
    request["holoindex_evidence"]["index_gap_detected"] = True
    store = ratchet.InMemoryOutcomeRatchetStore()

    result = _invoke(request=request, store=store)

    assert result.decision == QUEUE_AUTHORIZED_VERIFIED_OUTCOME_RATCHET_INVOKE_REJECT
    assert (
        QueueAuthorizedVerifiedOutcomeRatchetInvokeReason.RATCHET_NOT_ACCEPTED
        in result.rejection_reasons
    )
    assert ratchet.FAIL_HOLOINDEX_EVIDENCE in result.rejection_reasons
    assert result.ratchet_result is not None
    assert result.ratchet_result.decision == ratchet.OUTCOME_RATCHET_REJECT


def test_result_is_json_serializable() -> None:
    result = _invoke()

    payload = result.to_dict()
    assert payload["decision"] == QUEUE_AUTHORIZED_VERIFIED_OUTCOME_RATCHET_INVOKE_ACCEPT
    assert payload["ratchet_result"]["decision"] == ratchet.OUTCOME_RATCHET_RECORDED
    json.dumps(payload, sort_keys=True)


def test_module_has_no_direct_shell_git_gh_pr_publish_merge_reward_or_holoindex_authority() -> None:
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
    )
    for token in forbidden_tokens:
        assert token not in source
