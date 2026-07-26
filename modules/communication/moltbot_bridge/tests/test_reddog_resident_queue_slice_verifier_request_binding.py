"""Tests for REDDOG_RESIDENT_QUEUE_SLICE_VERIFIER_REQUEST_BINDING_PHASE1."""

from __future__ import annotations

import ast
from pathlib import Path

from modules.communication.moltbot_bridge.src.reddog_resident_queue_slice_verifier_request_binding import (
    FAIL_BOUNDED_WORKER_PILOT_REJECTED,
    FAIL_SIGNED_RECEIPT_CHAIN_MISSING,
    FAIL_SLICE_VERIFIER_PLAN_MISSING,
    SLICE_VERIFIER_REQUEST_BINDING_ACCEPT,
    SLICE_VERIFIER_REQUEST_BINDING_REJECT,
    build_resident_queue_slice_verifier_request,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_bounded_worker_pilot_invoke import (
    QUEUE_AUTHORIZED_BOUNDED_WORKER_PILOT_INVOKE_REJECT,
)
from modules.communication.moltbot_bridge.tests.test_reddog_wre_queue_authorized_slice_verifier_invoke import (
    ARTIFACT,
    WORK_ORDER_ID,
    _queue_pilot_result,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "reddog_resident_queue_slice_verifier_request_binding.py"
)


def _digest(ch: str) -> str:
    return "sha256:" + ch * 64


def _reservation() -> dict[str, object]:
    return {
        "reservation_id": "assurance-reservation-" + "1" * 20,
        "reservation_digest": _digest("0"),
        "admission_reservation_digest": _digest("0"),
        "status": "reserved",
        "work_order_id": WORK_ORDER_ID,
        "author_task_id": "reddog-worker-dispatch-" + "1" * 16,
        "author_principal_id": "worker:author",
        "verifier_task_id": "reddog-worker-dispatch-" + "2" * 16,
        "verifier_principal_id": "worker:verifier",
    }


class _ReservationStore:
    def get_independent_assurance_reservation(self, reservation_id: str):
        assert reservation_id == _reservation()["reservation_id"]
        return _reservation()


class _RenewedReservationStore:
    def get_independent_assurance_reservation(self, reservation_id: str):
        assert reservation_id == _reservation()["reservation_id"]
        return {
            **_reservation(),
            "reservation_digest": _digest("1"),
            "renewal_count": 1,
        }


def _signed_receipt_chain() -> dict[str, object]:
    return {
        "accepted": True,
        "terminal_receipt_hash": _digest("a"),
    }


def _slice_verifier_plan(**overrides: object) -> dict[str, object]:
    payload = {
        "slice_name": "REDDOG_RESIDENT_QUEUE_SLICE_VERIFIER_REQUEST_BINDING_PHASE1",
        "worker_id": "worker:author",
        "verifier_id": "worker:verifier",
        "base_sha": "b" * 40,
        "head_sha": "a" * 40,
        "allowed_path_patterns": [
            "modules/communication/moltbot_bridge/tests/fixtures/reddog_queue_pilot/**"
        ],
        "expected_changed_paths": [ARTIFACT],
        "forbidden_path_patterns": ["**/.env", "**/secrets/**"],
        "required_checks": [
            {
                "name": "pytest",
                "argv": ["python", "-m", "pytest", "modules/communication/moltbot_bridge/tests", "-q"],
                "timeout_s": 30,
            }
        ],
        "signed_receipt_chain": _signed_receipt_chain(),
    }
    payload.update(overrides)
    return payload


def _work_order(**overrides: object) -> dict[str, object]:
    payload = {
        "work_order_id": WORK_ORDER_ID,
        "allowed_paths": [
            "modules/communication/moltbot_bridge/tests/fixtures/reddog_queue_pilot/**"
        ],
        "denied_paths": ["**/.env", "**/secrets/**"],
        "slice_verifier_plan": _slice_verifier_plan(),
        "holoindex_evidence": {
            "index_gap_detected": False,
            "holoindex_freshness_receipt_digest": _digest("b"),
        },
    }
    payload.update(overrides)
    return payload


def _stage_results(tmp_path: Path, **overrides: object) -> dict[str, object]:
    payload = {
        "authority_runtime": {
            "authority_result": {
                "accepted": True,
                "work_authority": {
                    "authority_id": "authority-1",
                    "work_order_id": WORK_ORDER_ID,
                },
                "receipt": {
                    "receipt_id": _digest("8"),
                    "work_authority_digest": _digest("9"),
                },
            }
        },
        "authority_verification": {
            "verification_result": {
                "accepted": True,
                "receipt_id": _digest("c"),
            }
        },
        "worktree_create": {
            "worktree_create_result": {
                "worktree_path": str(tmp_path / "resident-worktree"),
            }
        },
        "assurance_capacity_admission": {
            "decision": "ASSURANCE_CAPACITY_ADMISSION_ACCEPT",
            "reservation": _reservation(),
        },
        "bounded_worker_pilot": _queue_pilot_result(),
    }
    payload.update(overrides)
    return payload


def test_builds_evidence_producer_request_from_queue_chain_state(tmp_path: Path) -> None:
    result = build_resident_queue_slice_verifier_request(
        work_order=_work_order(),
        stage_results=_stage_results(tmp_path),
        repo_root=tmp_path / "repo",
        assurance_reservation_store=_ReservationStore(),
    )

    assert result.accepted is True
    assert result.decision == SLICE_VERIFIER_REQUEST_BINDING_ACCEPT
    assert result.rejection_reasons == []
    request = result.evidence_producer_request
    assert request["explicit_evidence_production_requested"] is True
    assert request["work_order_id"] == WORK_ORDER_ID
    assert request["expected_changed_paths"] == [ARTIFACT]
    assert request["signed_authority"]["accepted"] is True
    assert request["signed_authority"]["signature_gate_digest"] == _digest("9")
    assert request["signed_receipt_chain"] == _signed_receipt_chain()
    assert request["worktree_receipt"]["receipt_id"] == "bounded_wt_pilot_1234"
    assert request["bounded_worker_pilot_receipt"]["written_artifacts"] == [ARTIFACT]
    assert request["pattern_memory_write_performed"] is False
    assert request["draft_pr_published"] is False
    assert request["merge_performed"] is False
    assert result.no_command_execution_performed is True
    assert result.no_github_call_performed is True
    assert result.no_pr_publish_performed is True
    assert result.no_merge_performed is True
    assert result.no_pattern_memory_write_performed is True
    assert result.no_reward_settlement_performed is True
    assert result.no_openclaw_enqueue_performed is True
    assert result.no_hermes_dispatch_performed is True
    assert result.no_holoindex_reindex_performed is True


def test_renewed_lease_preserves_original_admission_digest(tmp_path: Path) -> None:
    result = build_resident_queue_slice_verifier_request(
        work_order=_work_order(),
        stage_results=_stage_results(tmp_path),
        repo_root=tmp_path / "repo",
        assurance_reservation_store=_RenewedReservationStore(),
    )

    assert result.accepted is True
    assert (
        result.evidence_producer_request["assurance_reservation_digest"]
        == _digest("0")
    )


def test_missing_slice_verifier_plan_rejects_before_request(tmp_path: Path) -> None:
    result = build_resident_queue_slice_verifier_request(
        work_order=_work_order(slice_verifier_plan={}),
        stage_results=_stage_results(tmp_path),
        repo_root=tmp_path / "repo",
        assurance_reservation_store=_ReservationStore(),
    )

    assert result.accepted is False
    assert result.decision == SLICE_VERIFIER_REQUEST_BINDING_REJECT
    assert FAIL_SLICE_VERIFIER_PLAN_MISSING in result.rejection_reasons
    assert result.evidence_producer_request == {}


def test_rejected_bounded_worker_pilot_blocks_request(tmp_path: Path) -> None:
    result = build_resident_queue_slice_verifier_request(
        work_order=_work_order(),
        stage_results=_stage_results(
            tmp_path,
            bounded_worker_pilot=_queue_pilot_result(
                decision=QUEUE_AUTHORIZED_BOUNDED_WORKER_PILOT_INVOKE_REJECT
            ),
        ),
        repo_root=tmp_path / "repo",
        assurance_reservation_store=_ReservationStore(),
    )

    assert result.accepted is False
    assert FAIL_BOUNDED_WORKER_PILOT_REJECTED in result.rejection_reasons


def test_missing_signed_receipt_chain_blocks_request(tmp_path: Path) -> None:
    plan = _slice_verifier_plan(signed_receipt_chain={})
    result = build_resident_queue_slice_verifier_request(
        work_order=_work_order(slice_verifier_plan=plan, bounded_worker_plan={}),
        stage_results=_stage_results(tmp_path),
        repo_root=tmp_path / "repo",
        assurance_reservation_store=_ReservationStore(),
    )

    assert result.accepted is False
    assert FAIL_SIGNED_RECEIPT_CHAIN_MISSING in result.rejection_reasons


def test_uses_pilot_written_artifacts_when_plan_expected_paths_are_absent(tmp_path: Path) -> None:
    plan = _slice_verifier_plan(expected_changed_paths=[])
    result = build_resident_queue_slice_verifier_request(
        work_order=_work_order(slice_verifier_plan=plan),
        stage_results=_stage_results(tmp_path),
        repo_root=tmp_path / "repo",
        assurance_reservation_store=_ReservationStore(),
    )

    assert result.accepted is True
    assert result.evidence_producer_request["expected_changed_paths"] == [ARTIFACT]


def test_module_has_no_shell_network_git_holoindex_or_worker_authority() -> None:
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
        "\ngh ",
        "openclaw_supervisor",
        "hermes_job_executor",
        "publish_verified_draft_pr(",
        "PatternMemory(",
        "store_outcome",
        "settle_reward",
        "holo_index.py --index",
    )
    for token in forbidden_tokens:
        assert token not in source
