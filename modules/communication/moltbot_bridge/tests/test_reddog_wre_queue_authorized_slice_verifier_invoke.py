"""Tests for REDDOG_WRE_QUEUE_AUTHORIZED_SLICE_VERIFIER_INVOKE_PHASE1."""

from __future__ import annotations

import ast
import json
from pathlib import Path

from modules.communication.moltbot_bridge.src.reddog_bounded_worktree_worker_execution_pilot import (
    BOUNDED_WORKTREE_PILOT_ACCEPT,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_bounded_worker_pilot_invoke import (
    QUEUE_AUTHORIZED_BOUNDED_WORKER_PILOT_INVOKE_ACCEPT,
    QUEUE_AUTHORIZED_BOUNDED_WORKER_PILOT_INVOKE_REJECT,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_slice_verifier_invoke import (
    QUEUE_AUTHORIZED_SLICE_VERIFIER_INVOKE_ACCEPT,
    QUEUE_AUTHORIZED_SLICE_VERIFIER_INVOKE_REJECT,
    QueueAuthorizedSliceVerifierInvokeReason,
    invoke_reddog_wre_queue_authorized_slice_verifier,
)
from modules.infrastructure.wre_core.src.wre_autonomous_slice_verifier_runtime import (
    AUTONOMOUS_SLICE_VERIFIER_ACCEPT,
    AUTONOMOUS_SLICE_VERIFIER_REJECT,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "reddog_wre_queue_authorized_slice_verifier_invoke.py"
)
WORK_ORDER_ID = "wo-queue-slice-verifier-1"
BASE_SHA = "b" * 40
HEAD_SHA = "a" * 40
ARTIFACT = "modules/communication/moltbot_bridge/tests/fixtures/reddog_queue_pilot/README.md"


def _digest(ch: str) -> str:
    return "sha256:" + ch * 64


def _queue_pilot_result(*, decision: str | None = None, pilot_decision: str | None = None) -> dict:
    return {
        "decision": decision or QUEUE_AUTHORIZED_BOUNDED_WORKER_PILOT_INVOKE_ACCEPT,
        "rejection_reasons": [],
        "explicit_queue_authorized_bounded_worker_pilot_requested": True,
        "bounded_task_execution_performed": True,
        "bounded_file_edit_performed": True,
        "shell_command_executed": False,
        "draft_pr_created": False,
        "merge_performed": False,
        "openclaw_enqueue_performed": False,
        "hermes_dispatch_performed": False,
        "reward_settlement_performed": False,
        "holoindex_reindex_performed": False,
        "pilot_result": {
            "decision": pilot_decision or BOUNDED_WORKTREE_PILOT_ACCEPT,
            "accepted": True,
            "rejection_reasons": [],
            "task_execution_performed": True,
            "file_edit_performed": True,
            "shell_command_executed": False,
            "draft_pr_created": False,
            "merge_performed": False,
            "openclaw_enqueue_performed": False,
            "hermes_dispatch_performed": False,
            "reward_settlement_performed": False,
            "holoindex_reindex_performed": False,
            "receipt": {
                "receipt_id": "bounded_wt_pilot_1234",
                "work_order_id": WORK_ORDER_ID,
                "canonical_root": "modules/communication/moltbot_bridge/tests/fixtures/reddog_queue_pilot",
                "written_artifacts": [ARTIFACT],
                "artifact_manifest_digest": _digest("1"),
                "written_artifact_digest": _digest("2"),
                "worktree_spine_result_digest": _digest("3"),
                "generic_writer_receipt_digest": _digest("4"),
                "governed_shell_receipt_digest": _digest("5"),
                "cwd_guard_receipt_digest": _digest("6"),
            },
        },
    }


def _verifier_request() -> dict:
    return {
        "work_order_id": WORK_ORDER_ID,
        "slice_name": "REDDOG_WRE_QUEUE_AUTHORIZED_SLICE_VERIFIER_INVOKE_PHASE1",
        "worker_id": "worker:author",
        "verifier_id": "worker:verifier",
        "base_sha": BASE_SHA,
        "head_sha": HEAD_SHA,
        "allowed_path_patterns": [
            "modules/communication/moltbot_bridge/tests/fixtures/reddog_queue_pilot/**"
        ],
        "expected_changed_paths": [ARTIFACT],
        "forbidden_path_patterns": ["**/.env", "**/secrets/**"],
        "diff_evidence": {
            "source": "machine_derived",
            "red_dog_prose_source": False,
            "base_sha": BASE_SHA,
            "head_sha": HEAD_SHA,
            "diff_digest": _digest("7"),
            "changed_paths": [ARTIFACT],
            "added_lines": ["bounded pilot fixture update"],
        },
        "test_evidence": {
            "head_sha": HEAD_SHA,
            "test_evidence_digest": _digest("8"),
            "required_checks": [
                {"name": "pytest", "head_sha": HEAD_SHA, "conclusion": "success"},
                {"name": "security", "head_sha": HEAD_SHA, "conclusion": "pass"},
            ],
        },
        "signed_authority": {
            "accepted": True,
            "signature_gate_digest": _digest("9"),
        },
        "signed_receipt_chain": {
            "accepted": True,
            "terminal_receipt_hash": _digest("a"),
        },
        "holoindex_evidence": {
            "index_gap_detected": False,
            "holoindex_freshness_receipt_digest": _digest("b"),
        },
        "pattern_memory_write_performed": False,
        "draft_pr_published": False,
        "merge_performed": False,
    }


def _invoke(queue_pilot: dict | None = None, verifier_request: dict | None = None):
    return invoke_reddog_wre_queue_authorized_slice_verifier(
        explicit_queue_authorized_slice_verifier_requested=True,
        queue_bounded_worker_pilot_result=queue_pilot or _queue_pilot_result(),
        verifier_request=verifier_request or _verifier_request(),
    )


def test_invokes_autonomous_verifier_from_accepted_bounded_pilot() -> None:
    result = _invoke()

    assert result.decision == QUEUE_AUTHORIZED_SLICE_VERIFIER_INVOKE_ACCEPT
    assert result.rejection_reasons == []
    assert result.verifier_result is not None
    assert result.verifier_result.decision == AUTONOMOUS_SLICE_VERIFIER_ACCEPT
    assert result.verifier_result.receipt.changed_paths == [ARTIFACT]
    assert result.verifier_result.receipt.worktree_receipt_digest == "bounded_wt_pilot_1234"
    assert result.verifier_result.receipt.no_command_execution_performed is True
    assert result.no_command_execution_performed is True
    assert result.no_github_call_performed is True
    assert result.no_pr_publish_performed is True
    assert result.no_merge_performed is True
    assert result.no_pattern_memory_write_performed is True
    assert result.no_reward_settlement_performed is True
    assert result.no_holoindex_reindex_performed is True


def test_explicit_invoke_missing_rejects_before_verifier() -> None:
    result = invoke_reddog_wre_queue_authorized_slice_verifier(
        explicit_queue_authorized_slice_verifier_requested=False,
        queue_bounded_worker_pilot_result=_queue_pilot_result(),
        verifier_request=_verifier_request(),
    )

    assert result.decision == QUEUE_AUTHORIZED_SLICE_VERIFIER_INVOKE_REJECT
    assert (
        QueueAuthorizedSliceVerifierInvokeReason.EXPLICIT_INVOKE_MISSING
        in result.rejection_reasons
    )
    assert result.verifier_result is None


def test_rejected_queue_pilot_blocks_verifier() -> None:
    result = _invoke(
        queue_pilot=_queue_pilot_result(
            decision=QUEUE_AUTHORIZED_BOUNDED_WORKER_PILOT_INVOKE_REJECT
        )
    )

    assert result.decision == QUEUE_AUTHORIZED_SLICE_VERIFIER_INVOKE_REJECT
    assert (
        QueueAuthorizedSliceVerifierInvokeReason.BOUNDED_PILOT_NOT_ACCEPTED
        in result.rejection_reasons
    )
    assert result.verifier_result is None


def test_rejected_pilot_payload_blocks_verifier() -> None:
    result = _invoke(queue_pilot=_queue_pilot_result(pilot_decision="BOUNDED_WORKTREE_PILOT_REJECT"))

    assert result.decision == QUEUE_AUTHORIZED_SLICE_VERIFIER_INVOKE_REJECT
    assert (
        QueueAuthorizedSliceVerifierInvokeReason.PILOT_PAYLOAD_NOT_ACCEPTED
        in result.rejection_reasons
    )
    assert result.verifier_result is None


def test_pilot_side_effect_flags_block_verifier() -> None:
    queue_pilot = _queue_pilot_result()
    queue_pilot["pilot_result"]["shell_command_executed"] = True

    result = _invoke(queue_pilot=queue_pilot)

    assert result.decision == QUEUE_AUTHORIZED_SLICE_VERIFIER_INVOKE_REJECT
    assert (
        QueueAuthorizedSliceVerifierInvokeReason.PILOT_SIDE_EFFECT_FLAGS_INVALID
        in result.rejection_reasons
    )
    assert result.verifier_result is None


def test_work_order_id_mismatch_blocks_verifier() -> None:
    request = _verifier_request()
    request["work_order_id"] = "other-work-order"

    result = _invoke(verifier_request=request)

    assert result.decision == QUEUE_AUTHORIZED_SLICE_VERIFIER_INVOKE_REJECT
    assert (
        QueueAuthorizedSliceVerifierInvokeReason.WORK_ORDER_ID_MISMATCH
        in result.rejection_reasons
    )
    assert result.verifier_result is None


def test_diff_paths_must_match_pilot_written_artifacts() -> None:
    request = _verifier_request()
    request["diff_evidence"]["changed_paths"] = [
        "modules/communication/moltbot_bridge/tests/fixtures/reddog_queue_pilot/OTHER.md"
    ]

    result = _invoke(verifier_request=request)

    assert result.decision == QUEUE_AUTHORIZED_SLICE_VERIFIER_INVOKE_REJECT
    assert (
        QueueAuthorizedSliceVerifierInvokeReason.DIFF_PATHS_MISMATCH
        in result.rejection_reasons
    )
    assert result.verifier_result is None


def test_verifier_rejection_is_preserved() -> None:
    request = _verifier_request()
    request["holoindex_evidence"]["index_gap_detected"] = True

    result = _invoke(verifier_request=request)

    assert result.decision == QUEUE_AUTHORIZED_SLICE_VERIFIER_INVOKE_REJECT
    assert (
        QueueAuthorizedSliceVerifierInvokeReason.VERIFIER_NOT_ACCEPTED
        in result.rejection_reasons
    )
    assert "FAIL_HOLOINDEX_EVIDENCE" in result.rejection_reasons
    assert result.verifier_result is not None
    assert result.verifier_result.decision == AUTONOMOUS_SLICE_VERIFIER_REJECT


def test_result_is_json_serializable() -> None:
    result = _invoke()

    payload = result.to_dict()
    assert payload["decision"] == QUEUE_AUTHORIZED_SLICE_VERIFIER_INVOKE_ACCEPT
    assert payload["verifier_result"]["decision"] == AUTONOMOUS_SLICE_VERIFIER_ACCEPT
    json.dumps(payload)


def test_module_has_no_execution_publish_merge_memory_or_holoindex_authority() -> None:
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
        "gh ",
        "publish_verified_draft_pr(",
        "openclaw_supervisor",
        "hermes_job_executor",
        "PatternMemory(",
        "store_outcome",
        "settle_reward",
        "holo_index.py --index",
    )
    for token in forbidden_tokens:
        assert token not in source
