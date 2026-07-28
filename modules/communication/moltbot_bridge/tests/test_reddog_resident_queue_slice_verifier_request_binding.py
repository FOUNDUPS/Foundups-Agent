"""Tests for REDDOG_RESIDENT_QUEUE_SLICE_VERIFIER_REQUEST_BINDING_PHASE1."""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

from modules.communication.moltbot_bridge.src.reddog_resident_queue_slice_verifier_request_binding import (
    FAIL_BOUNDED_WORKER_PILOT_REJECTED,
    FAIL_EXACT_SHA_COMMIT_BINDING_MISMATCH,
    FAIL_EXACT_SHA_COMMIT_MISSING,
    FAIL_EXACT_SHA_COMMIT_RECEIPT_INVALID,
    FAIL_SIGNED_AUTHORITY_BINDING_MISMATCH,
    FAIL_SIGNED_RECEIPT_CHAIN_MISSING,
    FAIL_SLICE_VERIFIER_PLAN_MISSING,
    SLICE_VERIFIER_REQUEST_BINDING_ACCEPT,
    SLICE_VERIFIER_REQUEST_BINDING_REJECT,
    build_resident_queue_slice_verifier_request,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_bounded_worker_pilot_invoke import (
    QUEUE_AUTHORIZED_BOUNDED_WORKER_PILOT_INVOKE_REJECT,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_binding import (
    canonical_full_work_order_digest,
)
from modules.communication.moltbot_bridge.src.reddog_work_authority_digest import (
    canonical_work_authority_digest,
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


def _canonical_digest(value: object) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return "sha256:" + hashlib.sha256(raw.encode("ascii")).hexdigest()


def _exact_sha_commit_receipt(
    worktree_path: str,
    *,
    work_order_digest: str,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema_version": "reddog_resident_queue_exact_sha_commit_receipt.v1",
        "work_order_id": WORK_ORDER_ID,
        "queue_item_id": "queue-1",
        "selected_slice": "slice-1",
        "base_sha": "b" * 40,
        "head_sha": "a" * 40,
        "parent_sha": "b" * 40,
        "tree_sha": "c" * 40,
        "branch_name": "feat/reddog-exact-sha",
        "worktree_path": worktree_path,
        "changed_paths": [ARTIFACT],
        "bounded_worker_receipt_id": "bounded_wt_pilot_1234",
        "bounded_worker_receipt_digest": _digest("d"),
        "worktree_create_result_digest": _digest("e"),
        "commit_message_digest": _digest("f"),
        "work_order_digest": work_order_digest,
        "commit_attempt_key": _digest("2"),
        "chain_state_digest": _digest("3"),
        "effect_commit_state": "COMMITTED",
        "reconciliation_required": False,
        "reconciled_existing_commit": False,
        "main_checkout_untouched": True,
        "no_push_performed": True,
        "no_pr_created": True,
        "no_merge_performed": True,
        "no_holoindex_reindex_performed": True,
        "no_pattern_memory_write_performed": True,
        "no_reward_settlement_performed": True,
    }
    return {"receipt_id": _canonical_digest(payload), **payload}


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


def _stage_results(
    tmp_path: Path,
    *,
    bound_work_order: dict[str, object] | None = None,
    **overrides: object,
) -> dict[str, object]:
    worktree_path = str((tmp_path / "resident-worktree").resolve())
    work_order_digest = canonical_full_work_order_digest(
        bound_work_order or _work_order()
    )
    work_authority = {
        "authority_id": "authority-1",
        "work_order_id": WORK_ORDER_ID,
    }
    verified_work_authority_digest = canonical_work_authority_digest(
        work_authority
    )
    payload = {
        "authority_runtime": {
            "decision": "QUEUE_AUTHORITY_RUNTIME_INVOKE_ACCEPT",
            "authority_result": {
                "accepted": True,
                "work_authority": work_authority,
                "receipt": {
                    "receipt_id": _digest("8"),
                    "status": "DELEGATED_AUTHORITY_ISSUED",
                    "work_authority_digest": canonical_work_authority_digest(
                        work_authority
                    ),
                },
            }
        },
        "authority_verification": {
            "decision": "QUEUE_AUTHORITY_VERIFICATION_INVOKE_ACCEPT",
            "verified_work_authority_digest": verified_work_authority_digest,
            "verification_result": {
                "accepted": True,
                "receipt_id": _digest("c"),
            }
        },
        "worktree_create": {
            "worktree_create_result": {
                "worktree_path": worktree_path,
            }
        },
        "assurance_capacity_admission": {
            "decision": "ASSURANCE_CAPACITY_ADMISSION_ACCEPT",
            "reservation": _reservation(),
        },
        "bounded_worker_pilot": _queue_pilot_result(),
        "executor_plan": {
            "decision": "QUEUE_AUTHORIZED_EXECUTOR_PLAN_DRYRUN_ACCEPT",
            "executor_plan_result": {
                "plan": {
                    "work_order_digest": work_order_digest,
                },
            },
        },
        "exact_sha_commit": {
            "decision": "RESIDENT_QUEUE_EXACT_SHA_COMMIT_ACCEPT",
            "accepted": True,
            "effect_commit_state": "COMMITTED",
            "reconciliation_required": False,
            "commit_receipt": _exact_sha_commit_receipt(
                worktree_path,
                work_order_digest=work_order_digest,
            ),
        },
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
    assert request["signed_authority"]["signature_gate_digest"] == (
        canonical_work_authority_digest(
            {
                "authority_id": "authority-1",
                "work_order_id": WORK_ORDER_ID,
            }
        )
    )
    assert request["signed_receipt_chain"] == _signed_receipt_chain()
    assert request["worktree_receipt"]["receipt_id"] == "bounded_wt_pilot_1234"
    assert request["bounded_worker_pilot_receipt"]["written_artifacts"] == [ARTIFACT]
    assert request["exact_sha_commit_receipt"]["head_sha"] == "a" * 40
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


def test_post_signing_memex_substitution_cannot_reach_verifier(tmp_path: Path) -> None:
    stages = _stage_results(tmp_path)
    work_authority = stages["authority_runtime"]["authority_result"]["work_authority"]
    work_authority["memex_supply_receipt_id"] = "memex-supply-attacker"
    work_authority["memex_supply_digest"] = _digest("7")

    result = build_resident_queue_slice_verifier_request(
        work_order=_work_order(),
        stage_results=stages,
        repo_root=tmp_path / "repo",
        assurance_reservation_store=_ReservationStore(),
    )

    assert result.accepted is False
    assert FAIL_SIGNED_AUTHORITY_BINDING_MISMATCH in result.rejection_reasons
    assert result.evidence_producer_request == {}


def test_rehashed_signer_receipt_cannot_override_verified_authority(
    tmp_path: Path,
) -> None:
    stages = _stage_results(tmp_path)
    authority_result = stages["authority_runtime"]["authority_result"]
    work_authority = authority_result["work_authority"]
    work_authority["memex_supply_receipt_id"] = "memex-supply-attacker"
    work_authority["memex_supply_digest"] = _digest("7")
    authority_result["receipt"][
        "work_authority_digest"
    ] = canonical_work_authority_digest(work_authority)

    result = build_resident_queue_slice_verifier_request(
        work_order=_work_order(),
        stage_results=stages,
        repo_root=tmp_path / "repo",
        assurance_reservation_store=_ReservationStore(),
    )

    assert result.accepted is False
    assert FAIL_SIGNED_AUTHORITY_BINDING_MISMATCH in result.rejection_reasons
    assert result.evidence_producer_request == {}


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


def test_missing_exact_sha_commit_blocks_request(tmp_path: Path) -> None:
    result = build_resident_queue_slice_verifier_request(
        work_order=_work_order(),
        stage_results=_stage_results(tmp_path, exact_sha_commit={}),
        repo_root=tmp_path / "repo",
        assurance_reservation_store=_ReservationStore(),
    )

    assert result.accepted is False
    assert FAIL_EXACT_SHA_COMMIT_MISSING in result.rejection_reasons


def test_planned_head_cannot_override_actual_commit_receipt(tmp_path: Path) -> None:
    plan = _slice_verifier_plan(head_sha="d" * 40)
    result = build_resident_queue_slice_verifier_request(
        work_order=_work_order(slice_verifier_plan=plan),
        stage_results=_stage_results(tmp_path),
        repo_root=tmp_path / "repo",
        assurance_reservation_store=_ReservationStore(),
    )

    assert result.accepted is False
    assert FAIL_EXACT_SHA_COMMIT_BINDING_MISMATCH in result.rejection_reasons


def test_tampered_commit_receipt_cannot_reach_verifier(tmp_path: Path) -> None:
    stages = _stage_results(tmp_path)
    stages["exact_sha_commit"]["commit_receipt"]["head_sha"] = "d" * 40

    result = build_resident_queue_slice_verifier_request(
        work_order=_work_order(),
        stage_results=stages,
        repo_root=tmp_path / "repo",
        assurance_reservation_store=_ReservationStore(),
    )

    assert result.accepted is False
    assert FAIL_EXACT_SHA_COMMIT_RECEIPT_INVALID in result.rejection_reasons


def test_changed_executor_work_order_digest_cannot_reach_verifier(
    tmp_path: Path,
) -> None:
    stages = _stage_results(tmp_path)
    stages["executor_plan"]["executor_plan_result"]["plan"][
        "work_order_digest"
    ] = _digest("9")

    result = build_resident_queue_slice_verifier_request(
        work_order=_work_order(),
        stage_results=stages,
        repo_root=tmp_path / "repo",
        assurance_reservation_store=_ReservationStore(),
    )

    assert result.accepted is False
    assert FAIL_EXACT_SHA_COMMIT_BINDING_MISMATCH in result.rejection_reasons


def test_head_sha_is_not_required_in_pre_execution_plan(tmp_path: Path) -> None:
    plan = _slice_verifier_plan()
    plan.pop("head_sha")
    work_order = _work_order(slice_verifier_plan=plan)
    result = build_resident_queue_slice_verifier_request(
        work_order=work_order,
        stage_results=_stage_results(tmp_path, bound_work_order=work_order),
        repo_root=tmp_path / "repo",
        assurance_reservation_store=_ReservationStore(),
    )

    assert result.accepted is True
    assert result.evidence_producer_request["head_sha"] == "a" * 40


def test_uses_pilot_written_artifacts_when_plan_expected_paths_are_absent(tmp_path: Path) -> None:
    plan = _slice_verifier_plan(expected_changed_paths=[])
    work_order = _work_order(slice_verifier_plan=plan)
    result = build_resident_queue_slice_verifier_request(
        work_order=work_order,
        stage_results=_stage_results(tmp_path, bound_work_order=work_order),
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
