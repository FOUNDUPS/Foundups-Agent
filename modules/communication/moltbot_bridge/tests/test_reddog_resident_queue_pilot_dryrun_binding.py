"""Tests for REDDOG_RESIDENT_QUEUE_PILOT_DRYRUN_BINDING_PHASE1."""

from __future__ import annotations

import ast
from pathlib import Path

from modules.communication.moltbot_bridge.src.reddog_resident_queue_pilot_dryrun_binding import (
    FAIL_AUTHORITY_VERIFICATION_MISSING,
    FAIL_BOUNDED_WORKER_PLAN_INVALID,
    FAIL_BOUNDED_WORKER_PLAN_MISSING,
    FAIL_GENERIC_WRITER_DRYRUN_REJECTED,
    PILOT_DRYRUN_BINDING_ACCEPT,
    PILOT_DRYRUN_BINDING_REJECT,
    build_resident_queue_pilot_dryruns,
)
from modules.communication.moltbot_bridge.tests.test_reddog_wre_queue_authorized_bounded_worker_pilot_invoke import (
    ARTIFACT,
    DOMAIN_ID,
    WORK_ORDER_ID,
    _domain_profile,
    _queue_worktree_result,
    _receipt_chain,
    _selection_receipt,
    _shell_profile,
    _signed_authority,
    _valid_bundle,
    _valve,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "reddog_resident_queue_pilot_dryrun_binding.py"
)


def _bounded_worker_plan() -> dict[str, object]:
    return {
        "operation": "queue_bounded_pilot_docs_patch",
        "domain_id": DOMAIN_ID,
        "domain_profile": _domain_profile().to_dict(),
        "planned_artifacts": [ARTIFACT],
        "requested_allowed_paths": [
            f"modules/communication/moltbot_bridge/tests/fixtures/{DOMAIN_ID}/**"
        ],
        "shell_profile": _shell_profile().to_dict(),
        "shell_argv": [
            "python",
            "-m",
            "pytest",
            "modules/communication/moltbot_bridge/tests/"
            "test_reddog_wre_queue_authorized_bounded_worker_pilot_invoke.py",
            "-q",
        ],
        "selection_receipt": _selection_receipt(),
        "signed_receipt_chain": _receipt_chain(),
        "stdin_policy": "none",
        "env_policy": {"scrubbed": True},
    }


def _work_order(bundle: dict[str, object]) -> dict[str, object]:
    work_order = dict(bundle["work_order"])
    work_order.update(
        {
            "branch_name": "feat/reddog-queue-bounded-pilot",
            "repo_permission_snapshot": {"digest": "sha256:perm"},
            "bounded_worker_plan": _bounded_worker_plan(),
        }
    )
    return work_order


def _stage_results(bundle: dict[str, object]) -> dict[str, object]:
    return {
        "authority_runtime": {
            "decision": "QUEUE_AUTHORITY_RUNTIME_INVOKE_ACCEPT",
            "authority_result": {
                "accepted": True,
                "receipt": {
                    "receipt_id": "authority-runtime-test",
                    "work_authority_digest": "sha256:signed-authority",
                },
                "work_authority": _signed_authority(WORK_ORDER_ID),
            },
        },
        "authority_verification": {
            "decision": "QUEUE_AUTHORITY_VERIFICATION_INVOKE_ACCEPT",
            "verification_result": {"accepted": True},
        },
        "execution_valve": {
            "decision": "QUEUE_AUTHORIZED_EXECUTION_VALVE_INVOKE_ACCEPT",
            "valve_decision": _valve(),
        },
        "worktree_create": _queue_worktree_result(bundle["worktree"]),
    }


def test_binding_derives_writer_and_shell_dryruns_from_chain_state(tmp_path: Path) -> None:
    bundle = _valid_bundle(tmp_path)

    result = build_resident_queue_pilot_dryruns(
        work_order=_work_order(bundle),
        stage_results=_stage_results(bundle),
        repo_root=bundle["repo_root"],
    )

    assert result.decision == PILOT_DRYRUN_BINDING_ACCEPT
    assert result.accepted is True
    assert result.rejection_reasons == []
    assert result.generic_writer_dryrun_result["accepted"] is True
    assert result.governed_shell_dryrun_result["accepted"] is True
    assert result.generic_writer_dryrun_result["receipt"]["work_order_id"] == WORK_ORDER_ID
    assert result.governed_shell_dryrun_result["receipt"]["work_order_id"] == WORK_ORDER_ID
    assert result.no_file_write_performed is True
    assert result.no_shell_command_executed is True
    assert result.no_worktree_created is True
    assert result.no_holoindex_reindex_performed is True
    assert not (bundle["worktree"] / ARTIFACT).exists()


def test_binding_rejects_without_explicit_bounded_worker_plan(tmp_path: Path) -> None:
    bundle = _valid_bundle(tmp_path)
    work_order = _work_order(bundle)
    work_order.pop("bounded_worker_plan")

    result = build_resident_queue_pilot_dryruns(
        work_order=work_order,
        stage_results=_stage_results(bundle),
        repo_root=bundle["repo_root"],
    )

    assert result.decision == PILOT_DRYRUN_BINDING_REJECT
    assert result.accepted is False
    assert FAIL_BOUNDED_WORKER_PLAN_MISSING in result.rejection_reasons
    assert result.generic_writer_dryrun_result == {}
    assert result.governed_shell_dryrun_result == {}
    assert not (bundle["worktree"] / ARTIFACT).exists()


def test_binding_rejects_malformed_bounded_worker_plan(tmp_path: Path) -> None:
    bundle = _valid_bundle(tmp_path)
    work_order = _work_order(bundle)
    plan = dict(work_order["bounded_worker_plan"])
    plan.pop("signed_receipt_chain")
    work_order["bounded_worker_plan"] = plan

    result = build_resident_queue_pilot_dryruns(
        work_order=work_order,
        stage_results=_stage_results(bundle),
        repo_root=bundle["repo_root"],
    )

    assert result.decision == PILOT_DRYRUN_BINDING_REJECT
    assert f"{FAIL_BOUNDED_WORKER_PLAN_INVALID}:signed_receipt_chain" in result.rejection_reasons
    assert not (bundle["worktree"] / ARTIFACT).exists()


def test_binding_rejects_when_authority_verification_is_not_accepted(tmp_path: Path) -> None:
    bundle = _valid_bundle(tmp_path)
    stages = _stage_results(bundle)
    stages["authority_verification"] = {"verification_result": {"accepted": False}}

    result = build_resident_queue_pilot_dryruns(
        work_order=_work_order(bundle),
        stage_results=stages,
        repo_root=bundle["repo_root"],
    )

    assert result.decision == PILOT_DRYRUN_BINDING_REJECT
    assert FAIL_AUTHORITY_VERIFICATION_MISSING in result.rejection_reasons
    assert not (bundle["worktree"] / ARTIFACT).exists()


def test_binding_preserves_holoindex_gap_as_writer_rejection(tmp_path: Path) -> None:
    bundle = _valid_bundle(tmp_path)
    work_order = _work_order(bundle)
    work_order["holoindex_evidence"] = {
        "index_gap_detected": True,
        "retrieval_quality": "INDEX_GAP",
    }

    result = build_resident_queue_pilot_dryruns(
        work_order=work_order,
        stage_results=_stage_results(bundle),
        repo_root=bundle["repo_root"],
    )

    assert result.decision == PILOT_DRYRUN_BINDING_REJECT
    assert FAIL_GENERIC_WRITER_DRYRUN_REJECTED in result.rejection_reasons
    assert "FAIL_HOLOINDEX_INDEX_GAP" in result.rejection_reasons
    assert not (bundle["worktree"] / ARTIFACT).exists()


def test_module_has_no_shell_git_network_openclaw_hermes_or_holoindex_authority() -> None:
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
        "create_pull_request",
        "settle_reward",
        "holo_index.py --index",
    )
    for token in forbidden_tokens:
        assert token not in source
