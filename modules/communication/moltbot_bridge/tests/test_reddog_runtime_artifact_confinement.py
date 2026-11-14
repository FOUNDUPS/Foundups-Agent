"""Runtime artifact confinement tests for resident RedDog receipts."""

from __future__ import annotations

import json
import multiprocessing
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.src import openclaw_supervisor
from modules.communication.moltbot_bridge.src.reddog_resident_control_loop_receipt_store import (
    append_resident_control_loop_receipt,
    build_resident_control_loop_receipt,
    verify_resident_control_loop_receipt,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_binding_profile import (
    PROFILE_SIGNED_0102_BOUNDED_CODE,
    resident_queue_runtime_file_path,
)


def _claim_evidence(task_id: str, receipt_id: str) -> dict[str, object]:
    return openclaw_supervisor._signed_worker_claim_result(
        accepted=True,
        status=openclaw_supervisor.SIGNED_WORKER_OPENCLAW_CLAIM_ACCEPT,
        task_id=task_id,
        receipt_id=receipt_id,
    )


def _result() -> dict[str, object]:
    evidence = _claim_evidence("task-1", "receipt-1")
    evidence_digest = str(evidence["execution_result_digest"])
    return {
        "accepted": True,
        "status": "complete",
        "rounds": 1,
        "serial_progress": 1,
        "claim_progress": 1,
        "worker_claim_count": 1,
        "worker_completion_count": 1,
        "worker_requeue_count": 0,
        "worker_failure_count": 0,
        "receipt_ids": ["receipt-1"],
        "child_execution_receipt_ids": ["receipt-1"],
        "child_execution_evidence_digests": [evidence_digest],
        "child_execution_outcomes": [
            {
                "task_id": "task-1", "status": "completed",
                "receipt_id": "receipt-1", "evidence_digest": evidence_digest,
                "worker_execution_performed": False,
                "effect_evidence_complete": True,
                "worker_process_spawn_count": 0,
                "shell_command_count": 0,
            }
        ],
        "child_execution_evidence": [evidence],
        "rejection_reasons": [],
    }


def _set_child_outcomes(
    result: dict[str, object], receipts: list[str]
) -> None:
    evidence = [
        _claim_evidence(f"task-{index}", receipt_id)
        for index, receipt_id in enumerate(receipts, start=1)
    ]
    digests = [str(item["execution_result_digest"]) for item in evidence]
    result["receipt_ids"] = list(receipts)
    result["child_execution_receipt_ids"] = list(receipts)
    result["child_execution_evidence_digests"] = list(digests)
    result["child_execution_outcomes"] = [
        {
            "task_id": f"task-{index}", "status": "completed",
            "receipt_id": receipt_id, "evidence_digest": digest,
            "worker_execution_performed": False,
            "effect_evidence_complete": True,
            "worker_process_spawn_count": 0,
            "shell_command_count": 0,
        }
        for index, (receipt_id, digest) in enumerate(zip(receipts, digests), start=1)
    ]
    result["child_execution_evidence"] = evidence


def _append_receipt_process(args: tuple[str, str, int]) -> str:
    repo, target, index = args
    result = _result()
    _set_child_outcomes(result, [f"process-receipt-{index}"])
    receipt = append_resident_control_loop_receipt(
        path=target,
        result=result,
        repo_root=repo,
        created_at=f"2026-07-18T00:01:{index:02d}+00:00",
    )
    return receipt.receipt_id


def test_receipt_store_rejects_write_inside_repository(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    target = repo / "modules" / "receipt.jsonl"

    with pytest.raises(ValueError, match="inside_repo"):
        append_resident_control_loop_receipt(
            path=target,
            result=_result(),
            repo_root=repo,
            created_at="2026-07-18T00:00:00+00:00",
        )

    assert not target.exists()


def test_receipt_store_allows_outside_repository_runtime_path(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    target = tmp_path / "runtime" / "receipt.jsonl"

    receipt = append_resident_control_loop_receipt(
        path=target,
        result=_result(),
        repo_root=repo,
        created_at="2026-07-18T00:00:00+00:00",
    )

    assert receipt.accepted is True
    assert target.read_text(encoding="utf-8").count("\n") == 1


def test_profile_path_rejects_explicit_override_outside_runtime_root(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    runtime = tmp_path / "runtime"
    repo.mkdir()
    runtime.mkdir()
    env = {
        "REDDOG_RESIDENT_QUEUE_BINDING_PROFILE": PROFILE_SIGNED_0102_BOUNDED_CODE,
        "REDDOG_RESIDENT_RUNTIME_ROOT": str(runtime),
        "REDDOG_RESIDENT_QUEUE_CONTROL_LOOP_RECEIPTS_PATH": str(
            tmp_path / "other" / "receipt.jsonl"
        ),
    }

    with pytest.raises(ValueError, match="outside_runtime_root"):
        resident_queue_runtime_file_path(
            env,
            repo,
            "REDDOG_RESIDENT_QUEUE_CONTROL_LOOP_RECEIPTS_PATH",
        )


def test_profile_path_ignores_unknown_runtime_file_environment_name(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    env = {"REDDOG_UNKNOWN_RUNTIME_PATH": str(repo / "main.py")}

    assert resident_queue_runtime_file_path(
        env,
        repo,
        "REDDOG_UNKNOWN_RUNTIME_PATH",
    ) == ""


def test_receipt_store_rejects_existing_non_receipt_content_unchanged(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    target = tmp_path / "runtime" / "receipt.jsonl"
    target.parent.mkdir()
    target.write_text("not-json\n", encoding="utf-8")

    with pytest.raises(ValueError, match="invalid_json"):
        append_resident_control_loop_receipt(
            path=target,
            result=_result(),
            repo_root=repo,
            created_at="2026-07-18T00:00:00+00:00",
        )

    assert target.read_text(encoding="utf-8") == "not-json\n"


def test_receipt_store_serializes_concurrent_appends_as_valid_jsonl(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    target = tmp_path / "runtime" / "receipt.jsonl"

    def append(index: int) -> None:
        result = _result()
        _set_child_outcomes(result, [f"receipt-{index}"])
        append_resident_control_loop_receipt(
            path=target,
            result=result,
            repo_root=repo,
            created_at=f"2026-07-18T00:00:{index:02d}+00:00",
        )

    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(append, range(24)))

    rows = [json.loads(line) for line in target.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 24
    assert {row["receipt_ids"][0] for row in rows} == {
        f"receipt-{index}" for index in range(24)
    }


def test_receipt_store_serializes_cross_process_appends(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    target = tmp_path / "runtime" / "receipt.jsonl"
    jobs = [(str(repo), str(target), index) for index in range(8)]

    with ProcessPoolExecutor(
        max_workers=4,
        mp_context=multiprocessing.get_context("spawn"),
    ) as executor:
        receipt_ids = list(executor.map(_append_receipt_process, jobs))

    rows = [json.loads(line) for line in target.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 8
    assert len(set(receipt_ids)) == 8
    assert {row["receipt_ids"][0] for row in rows} == {
        f"process-receipt-{index}" for index in range(8)
    }


def test_receipt_effect_claims_are_derived_from_stages_and_claim_progress(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    result = _result()
    _set_child_outcomes(result, ["receipt-1", "receipt-2"])
    result.update(
        {
            "claim_progress": 2,
            "worker_claim_count": 2,
            "worker_completion_count": 2,
            "dispatched_stages": ["authority_runtime", "bounded_worker_pilot"],
        }
    )

    receipt = build_resident_control_loop_receipt(
        result=result,
        repo_root=repo,
        created_at="2026-07-18T00:00:00+00:00",
    )

    assert receipt.authority_issued is True
    assert receipt.worker_claim_performed is True
    assert receipt.worker_execution_performed is True
    assert receipt.bounded_file_edit_observed is True
    assert receipt.shell_command_execution_observed is False
    assert receipt.shell_command_count == 0
    assert receipt.worker_process_spawn_observed is False
    assert receipt.worker_process_spawn_count == 0


def test_receipt_builder_rejects_caller_effect_claim_conflict(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    result = _result()
    result.update(
        {
            "dispatched_stages": ["authority_runtime"],
            "authority_issued": False,
        }
    )

    with pytest.raises(ValueError, match="effect_claim_conflict:authority_issued"):
        build_resident_control_loop_receipt(
            result=result,
            repo_root=repo,
            created_at="2026-07-18T00:00:00+00:00",
        )


def test_receipt_verifier_rejects_tampered_serialized_mapping(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    receipt = build_resident_control_loop_receipt(
        result=_result(),
        repo_root=repo,
        created_at="2026-07-18T00:00:00+00:00",
    ).to_dict()
    receipt["status"] = "FORGED_PASS"

    with pytest.raises(ValueError, match="digest_invalid"):
        verify_resident_control_loop_receipt(receipt, expected_repo_root=repo)


def test_receipt_store_rejects_tampered_existing_receipt_unchanged(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    target = tmp_path / "runtime" / "receipt.jsonl"
    target.parent.mkdir()
    receipt = build_resident_control_loop_receipt(
        result=_result(),
        repo_root=repo,
        created_at="2026-07-18T00:00:00+00:00",
    ).to_dict()
    receipt["accepted"] = False
    original = json.dumps(receipt, sort_keys=True) + "\n"
    target.write_text(original, encoding="utf-8")

    with pytest.raises(ValueError, match="digest_invalid"):
        append_resident_control_loop_receipt(
            path=target,
            result=_result(),
            repo_root=repo,
            created_at="2026-07-18T00:00:01+00:00",
        )

    assert target.read_text(encoding="utf-8") == original
