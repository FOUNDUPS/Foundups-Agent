"""Tests for REDDOG_WRE_QUEUE_AUTHORIZED_BOUNDED_WORKER_PILOT_INVOKE_PHASE1."""

from __future__ import annotations

import ast
import json
from pathlib import Path

from modules.communication.moltbot_bridge.src.reddog_generic_agent_worktree_writer_dryrun import (
    GENERIC_WRITER_DRYRUN_ACCEPT,
    GenericAgentWorktreeDomainProfile,
    plan_generic_agent_worktree_writer_dry_run,
)
from modules.communication.moltbot_bridge.src.reddog_operator_loop_wardrobe_selection import (
    EXECUTION_GOVERNED_CANDIDATE,
    WARDROBE_SELECTION_ACCEPT,
    WARDROBE_SOVEREIGN_EXECUTION,
)
from modules.communication.moltbot_bridge.src.reddog_openclaw_work_order_policy_gate import (
    SIGNATURE_GATE_ACCEPTED,
)
from modules.communication.moltbot_bridge.src.reddog_signed_receipt_chain import (
    SIGNED_RECEIPT_CHAIN_ACCEPT,
)
from modules.communication.moltbot_bridge.src.reddog_wre_execution_valve import (
    VALVE_OPEN_WORKTREE_CREATE,
)
from modules.communication.moltbot_bridge.src.reddog_wre_governed_shell_runner_dryrun import (
    GOVERNED_SHELL_DRYRUN_ACCEPT,
    GovernedShellCommandProfile,
    plan_governed_shell_runner_dry_run,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_bounded_worker_pilot_invoke import (
    QUEUE_AUTHORIZED_BOUNDED_WORKER_PILOT_INVOKE_ACCEPT,
    QUEUE_AUTHORIZED_BOUNDED_WORKER_PILOT_INVOKE_REJECT,
    QueueAuthorizedBoundedWorkerPilotInvokeReason,
    invoke_reddog_wre_queue_authorized_bounded_worker_pilot,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_worktree_create_invoke import (
    QUEUE_AUTHORIZED_WORKTREE_CREATE_INVOKE_ACCEPT,
    QUEUE_AUTHORIZED_WORKTREE_CREATE_INVOKE_REJECT,
)
from modules.communication.moltbot_bridge.src.reddog_wre_worktree_create import (
    WORKTREE_CREATE_ACCEPT,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "reddog_wre_queue_authorized_bounded_worker_pilot_invoke.py"
)
WORK_ORDER_ID = "wo-queue-bounded-pilot-1"
DOMAIN_ID = "reddog_queue_pilot"
ARTIFACT = (
    "modules/communication/moltbot_bridge/tests/fixtures/"
    f"{DOMAIN_ID}/README.md"
)


def _selection_receipt() -> dict:
    return {
        "decision": WARDROBE_SELECTION_ACCEPT,
        "selected_wardrobe": WARDROBE_SOVEREIGN_EXECUTION,
        "execution_plane": EXECUTION_GOVERNED_CANDIDATE,
        "no_execution_performed": True,
    }


def _signed_authority(work_order_id: str = WORK_ORDER_ID) -> dict:
    return {
        "accepted": True,
        "signature_gate_status": SIGNATURE_GATE_ACCEPTED,
        "work_order_id": work_order_id,
        "permission_snapshot_digest": "sha256:perm",
        "signature_gate_digest": "sha256:signed-authority",
    }


def _receipt_chain() -> dict:
    return {
        "accepted": True,
        "decision": SIGNED_RECEIPT_CHAIN_ACCEPT,
        "terminal_receipt_hash": "sha256:terminal",
        "no_execution_performed": True,
        "no_reward_settlement_performed": True,
    }


def _valve() -> dict:
    return {
        "valve_state": VALVE_OPEN_WORKTREE_CREATE,
        "decision_digest": "sha256:valve",
        "rejection_reasons": [],
        "no_execution_performed": True,
    }


def _domain_profile() -> GenericAgentWorktreeDomainProfile:
    return GenericAgentWorktreeDomainProfile(
        profile_id="queue_bounded_pilot_docs_patch",
        operation="queue_bounded_pilot_docs_patch",
        artifact_contract_type="text_patch",
        domain_id_pattern=r"[a-z][a-z0-9_]{2,49}",
        canonical_root_template=(
            "modules/communication/moltbot_bridge/tests/fixtures/{domain_id}"
        ),
        allowed_path_patterns=[
            "modules/communication/moltbot_bridge/tests/fixtures/{domain_id}/**"
        ],
        denied_path_patterns=["**/.env", "**/secrets/**"],
        required_tests=[
            "python -m pytest "
            "modules/communication/moltbot_bridge/tests/"
            "test_reddog_wre_queue_authorized_bounded_worker_pilot_invoke.py -q"
        ],
        branch_prefix="feat/",
        draft_pr_only=True,
        consensus_required=False,
    )


def _shell_profile() -> GovernedShellCommandProfile:
    return GovernedShellCommandProfile(
        profile_id="queue_bounded_pilot_pytest",
        command_kind="test",
        argv_prefix=["python", "-m", "pytest"],
        allowed_arg_patterns=[r"modules/[A-Za-z0-9_./-]+\.py", r"-q"],
        denied_arg_patterns=[r".*--index-all.*", r".*\.env.*", r".*WSP_framework.*"],
        requires_cwd_guard=True,
        requires_worktree=True,
        timeout_seconds=300,
        max_stdout_bytes=100000,
        max_stderr_bytes=100000,
        secret_env_refs=[],
        output_redaction_policy="strict",
        draft_pr_only=True,
        consensus_required=False,
        repo_sensitive=True,
    )


def _work_order() -> dict:
    return {
        "work_order_id": WORK_ORDER_ID,
        "repo_full_name": "FOUNDUPS/Foundups-Agent",
        "requested_operation": "queue_bounded_pilot_docs_patch",
        "allowed_paths": [
            f"modules/communication/moltbot_bridge/tests/fixtures/{DOMAIN_ID}/**"
        ],
        "denied_paths": [".env", ".git/**"],
        "holoindex_evidence": {
            "index_gap_detected": False,
            "retrieval_quality": "HIGH",
            "holoindex_freshness_receipt_digest": "sha256:holo-fresh",
        },
    }


def _queue_worktree_result(worktree: Path, *, decision: str | None = None) -> dict:
    return {
        "decision": decision or QUEUE_AUTHORIZED_WORKTREE_CREATE_INVOKE_ACCEPT,
        "rejection_reasons": [],
        "explicit_queue_authorized_worktree_create_requested": True,
        "worktree_create_result": {
            "decision": WORKTREE_CREATE_ACCEPT,
            "work_order_id": WORK_ORDER_ID,
            "branch_name": "feat/reddog-queue-bounded-pilot",
            "worktree_path": str(worktree),
            "plan_id": "plan-queue-bounded-pilot",
            "plan_digest": "sha256:plan",
            "valve_decision_digest": "sha256:valve",
            "rejection_reasons": [],
            "phase_receipts": [],
            "no_task_execution_performed": True,
            "no_file_edit_performed": True,
            "no_pr_created": True,
            "merge_performed": False,
            "main_checkout_untouched": True,
            "cleanup_plan": {"status": "cleanup_planned"},
            "result_digest": "sha256:worktree-create",
        },
        "no_task_execution_performed": True,
        "no_file_edit_performed": True,
        "no_shell_command_executed": True,
        "no_openclaw_enqueue_performed": True,
        "no_hermes_dispatch_performed": True,
        "no_pr_created": True,
        "no_reward_settlement_performed": True,
        "no_holoindex_reindex_performed": True,
    }


def _valid_bundle(tmp_path: Path) -> dict:
    repo = tmp_path / "repo"
    worktree = tmp_path / "isolated-worktree"
    repo.mkdir()
    worktree.mkdir()
    writer = plan_generic_agent_worktree_writer_dry_run(
        {
            "work_order_id": WORK_ORDER_ID,
            "operation": "queue_bounded_pilot_docs_patch",
            "domain_id": DOMAIN_ID,
            "domain_profile": _domain_profile(),
            "planned_artifacts": [ARTIFACT],
            "requested_allowed_paths": [
                f"modules/communication/moltbot_bridge/tests/fixtures/{DOMAIN_ID}/**"
            ],
            "target_branch": "feat/reddog-queue-bounded-pilot",
            "repo_root": str(repo),
            "worktree_path": str(worktree),
            "operation_cwd": str(worktree),
            "selection_receipt": _selection_receipt(),
            "signed_authority": _signed_authority(),
            "signed_receipt_chain": _receipt_chain(),
            "execution_valve_decision": _valve(),
            "permission_snapshot_digest": "sha256:perm",
            "holoindex_evidence": {"index_gap_detected": False},
        }
    )
    assert writer.decision == GENERIC_WRITER_DRYRUN_ACCEPT
    shell = plan_governed_shell_runner_dry_run(
        {
            "work_order_id": WORK_ORDER_ID,
            "profile": _shell_profile(),
            "argv": [
                "python",
                "-m",
                "pytest",
                "modules/communication/moltbot_bridge/tests/"
                "test_reddog_wre_queue_authorized_bounded_worker_pilot_invoke.py",
                "-q",
            ],
            "operation_cwd": str(worktree),
            "worktree_path": str(worktree),
            "repo_root": str(repo),
            "selection_receipt": _selection_receipt(),
            "signed_authority": _signed_authority(),
            "signed_receipt_chain": _receipt_chain(),
            "execution_valve_decision": _valve(),
            "generic_writer_dryrun_receipt": writer.receipt.to_dict(),
            "permission_snapshot_digest": "sha256:perm",
            "stdin_policy": "none",
            "env_policy": {"scrubbed": True},
            "holoindex_evidence": {
                "index_gap_detected": False,
                "holoindex_freshness_receipt_digest": "sha256:holo-fresh",
            },
        }
    )
    assert shell.decision == GOVERNED_SHELL_DRYRUN_ACCEPT
    return {
        "repo_root": repo,
        "worktree": worktree,
        "work_order": _work_order(),
        "queue_worktree_create_result": _queue_worktree_result(worktree),
        "generic_writer_dryrun_result": writer.to_dict(),
        "governed_shell_dryrun_result": shell.to_dict(),
        "artifact_contents": {
            ARTIFACT: (
                "# RedDog Queue Pilot\n\n"
                "This file exists only inside the queue-authorized worktree.\n"
            )
        },
    }


def _invoke(bundle: dict):
    return invoke_reddog_wre_queue_authorized_bounded_worker_pilot(
        explicit_queue_authorized_bounded_worker_pilot_requested=True,
        queue_worktree_create_result=bundle["queue_worktree_create_result"],
        generic_writer_dryrun_result=bundle["generic_writer_dryrun_result"],
        governed_shell_dryrun_result=bundle["governed_shell_dryrun_result"],
        artifact_contents=bundle["artifact_contents"],
        work_order=bundle["work_order"],
        repo_root=bundle["repo_root"],
    )


def test_queue_authorized_chain_materializes_declared_artifact_only(tmp_path: Path) -> None:
    bundle = _valid_bundle(tmp_path)

    result = _invoke(bundle)

    assert result.decision == QUEUE_AUTHORIZED_BOUNDED_WORKER_PILOT_INVOKE_ACCEPT
    assert result.rejection_reasons == []
    assert result.pilot_result is not None
    assert result.bounded_task_execution_performed is True
    assert result.bounded_file_edit_performed is True
    assert result.shell_command_executed is False
    assert result.draft_pr_created is False
    assert result.merge_performed is False
    assert result.openclaw_enqueue_performed is False
    assert result.hermes_dispatch_performed is False
    assert result.reward_settlement_performed is False
    assert result.holoindex_reindex_performed is False
    assert (bundle["worktree"] / ARTIFACT).exists()
    assert not (bundle["repo_root"] / ARTIFACT).exists()


def test_explicit_invoke_missing_rejects_before_write(tmp_path: Path) -> None:
    bundle = _valid_bundle(tmp_path)

    result = invoke_reddog_wre_queue_authorized_bounded_worker_pilot(
        explicit_queue_authorized_bounded_worker_pilot_requested=False,
        queue_worktree_create_result=bundle["queue_worktree_create_result"],
        generic_writer_dryrun_result=bundle["generic_writer_dryrun_result"],
        governed_shell_dryrun_result=bundle["governed_shell_dryrun_result"],
        artifact_contents=bundle["artifact_contents"],
        work_order=bundle["work_order"],
        repo_root=bundle["repo_root"],
    )

    assert result.decision == QUEUE_AUTHORIZED_BOUNDED_WORKER_PILOT_INVOKE_REJECT
    assert (
        QueueAuthorizedBoundedWorkerPilotInvokeReason.EXPLICIT_INVOKE_MISSING
        in result.rejection_reasons
    )
    assert not (bundle["worktree"] / ARTIFACT).exists()


def test_rejected_queue_worktree_blocks_before_write(tmp_path: Path) -> None:
    bundle = _valid_bundle(tmp_path)
    bundle["queue_worktree_create_result"] = _queue_worktree_result(
        bundle["worktree"], decision=QUEUE_AUTHORIZED_WORKTREE_CREATE_INVOKE_REJECT
    )

    result = _invoke(bundle)

    assert result.decision == QUEUE_AUTHORIZED_BOUNDED_WORKER_PILOT_INVOKE_REJECT
    assert (
        QueueAuthorizedBoundedWorkerPilotInvokeReason.WORKTREE_CREATE_NOT_ACCEPTED
        in result.rejection_reasons
    )
    assert not (bundle["worktree"] / ARTIFACT).exists()


def test_mutation_flag_in_worktree_create_payload_blocks_before_write(tmp_path: Path) -> None:
    bundle = _valid_bundle(tmp_path)
    bundle["queue_worktree_create_result"]["worktree_create_result"][
        "no_file_edit_performed"
    ] = False

    result = _invoke(bundle)

    assert result.decision == QUEUE_AUTHORIZED_BOUNDED_WORKER_PILOT_INVOKE_REJECT
    assert (
        QueueAuthorizedBoundedWorkerPilotInvokeReason.WORKTREE_CREATE_MUTATION_FLAGS_INVALID
        in result.rejection_reasons
    )
    assert not (bundle["worktree"] / ARTIFACT).exists()


def test_rejected_generic_writer_blocks_before_write(tmp_path: Path) -> None:
    bundle = _valid_bundle(tmp_path)
    bundle["generic_writer_dryrun_result"]["decision"] = "GENERIC_WRITER_DRYRUN_REJECT"

    result = _invoke(bundle)

    assert result.decision == QUEUE_AUTHORIZED_BOUNDED_WORKER_PILOT_INVOKE_REJECT
    assert (
        QueueAuthorizedBoundedWorkerPilotInvokeReason.GENERIC_WRITER_NOT_ACCEPTED
        in result.rejection_reasons
    )
    assert not (bundle["worktree"] / ARTIFACT).exists()


def test_rejected_governed_shell_blocks_before_write(tmp_path: Path) -> None:
    bundle = _valid_bundle(tmp_path)
    bundle["governed_shell_dryrun_result"]["decision"] = "GOVERNED_SHELL_DRYRUN_REJECT"

    result = _invoke(bundle)

    assert result.decision == QUEUE_AUTHORIZED_BOUNDED_WORKER_PILOT_INVOKE_REJECT
    assert (
        QueueAuthorizedBoundedWorkerPilotInvokeReason.GOVERNED_SHELL_NOT_ACCEPTED
        in result.rejection_reasons
    )
    assert not (bundle["worktree"] / ARTIFACT).exists()


def test_work_order_id_mismatch_blocks_before_write(tmp_path: Path) -> None:
    bundle = _valid_bundle(tmp_path)
    bundle["generic_writer_dryrun_result"]["receipt"]["work_order_id"] = "other-work"

    result = _invoke(bundle)

    assert result.decision == QUEUE_AUTHORIZED_BOUNDED_WORKER_PILOT_INVOKE_REJECT
    assert (
        QueueAuthorizedBoundedWorkerPilotInvokeReason.WORK_ORDER_ID_MISMATCH
        in result.rejection_reasons
    )
    assert not (bundle["worktree"] / ARTIFACT).exists()


def test_holoindex_gap_is_preserved_and_blocks_pilot_write(tmp_path: Path) -> None:
    bundle = _valid_bundle(tmp_path)
    bundle["work_order"]["holoindex_evidence"] = {
        "index_gap_detected": True,
        "retrieval_quality": "INDEX_GAP",
    }

    result = _invoke(bundle)

    assert result.decision == QUEUE_AUTHORIZED_BOUNDED_WORKER_PILOT_INVOKE_REJECT
    assert (
        QueueAuthorizedBoundedWorkerPilotInvokeReason.PILOT_NOT_ACCEPTED
        in result.rejection_reasons
    )
    assert "FAIL_HOLOINDEX_INDEX_GAP" in result.rejection_reasons
    assert not (bundle["worktree"] / ARTIFACT).exists()


def test_artifact_manifest_mismatch_is_preserved_and_blocks_write(tmp_path: Path) -> None:
    bundle = _valid_bundle(tmp_path)
    bundle["artifact_contents"] = {
        **bundle["artifact_contents"],
        (
            "modules/communication/moltbot_bridge/tests/fixtures/"
            f"{DOMAIN_ID}/EXTRA.md"
        ): "extra",
    }

    result = _invoke(bundle)

    assert result.decision == QUEUE_AUTHORIZED_BOUNDED_WORKER_PILOT_INVOKE_REJECT
    assert (
        QueueAuthorizedBoundedWorkerPilotInvokeReason.PILOT_NOT_ACCEPTED
        in result.rejection_reasons
    )
    assert "FAIL_ARTIFACTS_MISMATCH" in result.rejection_reasons
    assert not (bundle["worktree"] / ARTIFACT).exists()


def test_result_is_json_serializable(tmp_path: Path) -> None:
    bundle = _valid_bundle(tmp_path)

    result = _invoke(bundle)

    payload = result.to_dict()
    assert payload["decision"] == QUEUE_AUTHORIZED_BOUNDED_WORKER_PILOT_INVOKE_ACCEPT
    assert payload["pilot_result"]["decision"] == "BOUNDED_WORKTREE_PILOT_ACCEPT"
    json.dumps(payload)


def test_module_has_no_shell_git_openclaw_hermes_pr_reward_or_holoindex_authority() -> None:
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
        "create_reddog_wre_worktree(",
        "RealRedDogWorktreeRunner",
        "subprocess",
        "git ",
        "gh ",
        "openclaw_supervisor",
        "hermes_job_executor",
        "create_pull_request",
        "settle_reward",
        "holo_index.py --index",
    )
    for token in forbidden_tokens:
        assert token not in source
