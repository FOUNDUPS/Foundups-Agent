"""Tests for REDDOG_BOUNDED_WORKTREE_WORKER_EXECUTION_PILOT_PHASE1."""

from __future__ import annotations

import ast
from pathlib import Path

from modules.communication.moltbot_bridge.src import (
    reddog_bounded_worktree_worker_execution_pilot as pilot,
)
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

REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "reddog_bounded_worktree_worker_execution_pilot.py"
)
BOUNDED_WORKTREE_PILOT_ACCEPT = pilot.BOUNDED_WORKTREE_PILOT_ACCEPT
BOUNDED_WORKTREE_PILOT_REJECT = pilot.BOUNDED_WORKTREE_PILOT_REJECT
FAIL_ARTIFACTS_MISMATCH = pilot.FAIL_ARTIFACTS_MISMATCH
FAIL_CWD_GUARD = pilot.FAIL_CWD_GUARD
FAIL_DENIED_ARTIFACT = pilot.FAIL_DENIED_ARTIFACT
FAIL_GOVERNED_SHELL_DRYRUN = pilot.FAIL_GOVERNED_SHELL_DRYRUN
FAIL_HOLOINDEX_INDEX_GAP = pilot.FAIL_HOLOINDEX_INDEX_GAP
FAIL_WORKTREE_SPINE = pilot.FAIL_WORKTREE_SPINE
run_bounded_worktree_worker_execution_pilot = (
    pilot.run_bounded_worktree_worker_execution_pilot
)


def _selection_receipt() -> dict:
    return {
        "decision": WARDROBE_SELECTION_ACCEPT,
        "selected_wardrobe": WARDROBE_SOVEREIGN_EXECUTION,
        "execution_plane": EXECUTION_GOVERNED_CANDIDATE,
        "no_execution_performed": True,
    }


def _signed_authority(work_order_id: str = "wo-pilot-1") -> dict:
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
        profile_id="pilot_docs_patch",
        operation="pilot_docs_patch",
        artifact_contract_type="text_patch",
        domain_id_pattern=r"[a-z][a-z0-9_]{2,49}",
        canonical_root_template="modules/communication/moltbot_bridge/tests/fixtures/{domain_id}",
        allowed_path_patterns=[
            "modules/communication/moltbot_bridge/tests/fixtures/{domain_id}/**"
        ],
        denied_path_patterns=["**/.env", "**/secrets/**"],
        required_tests=[
            "python -m pytest "
            "modules/communication/moltbot_bridge/tests/"
            "test_reddog_bounded_worktree_worker_execution_pilot.py -q"
        ],
        branch_prefix="feat/",
        draft_pr_only=True,
        consensus_required=False,
    )


def _shell_profile() -> GovernedShellCommandProfile:
    return GovernedShellCommandProfile(
        profile_id="pilot_pytest",
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


def _spine_result(work_order_id: str, worktree: Path) -> dict:
    return {
        "decision": "WORKTREE_SPINE_ACCEPT",
        "work_order_id": work_order_id,
        "result_digest": "sha256:spine",
        "no_task_execution_performed": True,
        "no_file_edit_performed": True,
        "no_pr_created": True,
        "no_live_openclaw_enqueue": True,
        "no_hermes_dispatch": True,
        "merge_performed": False,
        "worktree_create_result": {
            "decision": "WORKTREE_CREATE_ACCEPT",
            "work_order_id": work_order_id,
            "worktree_path": str(worktree),
            "branch_name": "feat/reddog-bounded-worker-pilot",
            "result_digest": "sha256:worktree-create",
            "no_task_execution_performed": True,
            "no_file_edit_performed": True,
            "no_pr_created": True,
            "merge_performed": False,
        },
    }


def _valid_request(tmp_path: Path) -> dict:
    repo = tmp_path / "repo"
    worktree = tmp_path / "isolated-worktree"
    repo.mkdir()
    worktree.mkdir()
    work_order_id = "wo-pilot-1"
    artifact = "modules/communication/moltbot_bridge/tests/fixtures/reddog_pilot/README.md"
    writer = plan_generic_agent_worktree_writer_dry_run(
        {
            "work_order_id": work_order_id,
            "operation": "pilot_docs_patch",
            "domain_id": "reddog_pilot",
            "domain_profile": _domain_profile(),
            "planned_artifacts": [artifact],
            "requested_allowed_paths": [
                "modules/communication/moltbot_bridge/tests/fixtures/reddog_pilot/**"
            ],
            "target_branch": "feat/reddog-bounded-worker-pilot",
            "repo_root": str(repo),
            "worktree_path": str(worktree),
            "operation_cwd": str(worktree),
            "selection_receipt": _selection_receipt(),
            "signed_authority": _signed_authority(work_order_id),
            "signed_receipt_chain": _receipt_chain(),
            "execution_valve_decision": _valve(),
            "permission_snapshot_digest": "sha256:perm",
            "holoindex_evidence": {"index_gap_detected": False},
        }
    )
    assert writer.decision == GENERIC_WRITER_DRYRUN_ACCEPT
    shell = plan_governed_shell_runner_dry_run(
        {
            "work_order_id": work_order_id,
            "profile": _shell_profile(),
            "argv": [
                "python",
                "-m",
                "pytest",
                "modules/communication/moltbot_bridge/tests/"
                "test_reddog_bounded_worktree_worker_execution_pilot.py",
                "-q",
            ],
            "operation_cwd": str(worktree),
            "worktree_path": str(worktree),
            "repo_root": str(repo),
            "selection_receipt": _selection_receipt(),
            "signed_authority": _signed_authority(work_order_id),
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
        "work_order_id": work_order_id,
        "repo_root": str(repo),
        "worktree_path": str(worktree),
        "operation_cwd": str(worktree),
        "canonical_root": "modules/communication/moltbot_bridge/tests/fixtures/reddog_pilot",
        "worktree_spine_result": _spine_result(work_order_id, worktree),
        "generic_writer_dryrun_result": writer.to_dict(),
        "governed_shell_dryrun_result": shell.to_dict(),
        "artifact_contents": {
            artifact: "# RedDog Pilot\n\nThis file exists only inside the isolated worktree.\n"
        },
        "holoindex_evidence": {
            "index_gap_detected": False,
            "holoindex_freshness_receipt_digest": "sha256:holo-fresh",
        },
    }


def test_pilot_materializes_one_bounded_artifact_inside_isolated_worktree(tmp_path: Path) -> None:
    req = _valid_request(tmp_path)

    result = run_bounded_worktree_worker_execution_pilot(req)

    assert result.decision == BOUNDED_WORKTREE_PILOT_ACCEPT
    assert result.accepted is True
    assert result.rejection_reasons == []
    assert result.task_execution_performed is True
    assert result.file_edit_performed is True
    assert result.shell_command_executed is False
    assert result.draft_pr_created is False
    assert result.merge_performed is False
    assert result.openclaw_enqueue_performed is False
    assert result.hermes_dispatch_performed is False
    assert result.holoindex_reindex_performed is False
    assert result.receipt is not None
    artifact = result.receipt.written_artifacts[0]
    assert (Path(req["worktree_path"]) / artifact).exists()
    assert not (Path(req["repo_root"]) / artifact).exists()
    assert result.receipt.validation_command_executed is False
    assert result.receipt.draft_pr_created is False
    assert result.receipt.merge_performed is False


def test_rejects_without_accepted_worktree_spine_before_writing(tmp_path: Path) -> None:
    req = _valid_request(tmp_path)
    req["worktree_spine_result"]["decision"] = "WORKTREE_SPINE_REJECT"

    result = run_bounded_worktree_worker_execution_pilot(req)

    assert result.decision == BOUNDED_WORKTREE_PILOT_REJECT
    assert FAIL_WORKTREE_SPINE in result.rejection_reasons
    artifact = next(iter(req["artifact_contents"]))
    assert not (Path(req["worktree_path"]) / artifact).exists()


def test_rejects_shared_repo_cwd_before_writing(tmp_path: Path) -> None:
    req = _valid_request(tmp_path)
    req["worktree_path"] = req["repo_root"]
    req["operation_cwd"] = req["repo_root"]

    result = run_bounded_worktree_worker_execution_pilot(req)

    assert result.accepted is False
    assert FAIL_CWD_GUARD in result.rejection_reasons
    artifact = next(iter(req["artifact_contents"]))
    assert not (Path(req["repo_root"]) / artifact).exists()


def test_rejects_missing_or_extra_artifact_content(tmp_path: Path) -> None:
    req = _valid_request(tmp_path)
    req["artifact_contents"] = {
        **req["artifact_contents"],
        "modules/communication/moltbot_bridge/tests/fixtures/reddog_pilot/EXTRA.md": "extra",
    }

    result = run_bounded_worktree_worker_execution_pilot(req)

    assert result.accepted is False
    assert FAIL_ARTIFACTS_MISMATCH in result.rejection_reasons


def test_rejects_denied_artifact_even_if_receipt_is_tampered(tmp_path: Path) -> None:
    req = _valid_request(tmp_path)
    denied = "modules/communication/moltbot_bridge/tests/fixtures/reddog_pilot/.env"
    req["generic_writer_dryrun_result"]["receipt"]["planned_artifacts"] = [denied]
    req["artifact_contents"] = {denied: "SAFE_PLACEHOLDER=1\n"}

    result = run_bounded_worktree_worker_execution_pilot(req)

    assert result.accepted is False
    assert FAIL_DENIED_ARTIFACT in result.rejection_reasons
    assert not (Path(req["worktree_path"]) / denied).exists()


def test_rejects_governed_shell_dryrun_failure(tmp_path: Path) -> None:
    req = _valid_request(tmp_path)
    req["governed_shell_dryrun_result"]["decision"] = "GOVERNED_SHELL_DRYRUN_REJECT"

    result = run_bounded_worktree_worker_execution_pilot(req)

    assert result.accepted is False
    assert FAIL_GOVERNED_SHELL_DRYRUN in result.rejection_reasons


def test_rejects_holoindex_index_gap_before_writing(tmp_path: Path) -> None:
    req = _valid_request(tmp_path)
    req["holoindex_evidence"] = {"index_gap_detected": True, "retrieval_quality": "INDEX_GAP"}

    result = run_bounded_worktree_worker_execution_pilot(req)

    assert result.accepted is False
    assert FAIL_HOLOINDEX_INDEX_GAP in result.rejection_reasons
    artifact = next(iter(req["artifact_contents"]))
    assert not (Path(req["worktree_path"]) / artifact).exists()


def test_rejects_secret_like_content(tmp_path: Path) -> None:
    req = _valid_request(tmp_path)
    artifact = next(iter(req["artifact_contents"]))
    req["artifact_contents"][artifact] = "api_key = 'abc'\n"

    result = run_bounded_worktree_worker_execution_pilot(req)

    assert result.accepted is False
    assert result.rejection_reasons == ["FAIL_CONTENT_INVALID"]
    assert not (Path(req["worktree_path"]) / artifact).exists()


def test_module_ast_has_no_shell_git_or_queue_authority() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    banned_imports = {"subprocess", "os", "shutil", "requests", "git", "gh"}
    banned_calls = {"eval", "exec", "open"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".")[0] not in banned_imports
        if isinstance(node, ast.ImportFrom):
            assert (node.module or "").split(".")[0] not in banned_imports
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in banned_calls
    source = MODULE_PATH.read_text(encoding="utf-8")
    assert "from modules.communication.moltbot_bridge.src.openclaw" not in source
    assert "from modules.foundups.agent.src.hermes" not in source
    assert "subprocess" not in source
    assert "gh pr" not in source
    assert "git push" not in source
