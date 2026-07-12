"""Tests for REDDOG_WRE_GOVERNED_SHELL_RUNNER_DRYRUN_PHASE1."""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.src.reddog_generic_agent_worktree_writer_dryrun import (
    GENERIC_WRITER_DRYRUN_ACCEPT,
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
    FAIL_ARGV_INVALID,
    FAIL_ARGV_PREFIX,
    FAIL_ARG_NOT_ALLOWED,
    FAIL_CONSENSUS_REQUIRED,
    FAIL_CWD_GUARD,
    FAIL_DENIED_ARG,
    FAIL_GENERIC_WRITER_RECEIPT,
    FAIL_HOLOINDEX_FRESHNESS_RECEIPT,
    FAIL_HOLOINDEX_INDEX_GAP,
    FAIL_OUTPUT_CAP_INVALID,
    FAIL_PROFILE_INVALID,
    FAIL_RECEIPT_CHAIN,
    FAIL_SECRET_IN_REQUEST,
    FAIL_SELECTION_RECEIPT,
    FAIL_SHELL_METACHARACTER,
    FAIL_SIGNED_AUTHORITY,
    FAIL_TIMEOUT_INVALID,
    FAIL_VALVE_DECISION,
    GOVERNED_SHELL_DRYRUN_ACCEPT,
    GOVERNED_SHELL_DRYRUN_REJECT,
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
    / "reddog_wre_governed_shell_runner_dryrun.py"
)


@pytest.fixture()
def pytest_profile() -> GovernedShellCommandProfile:
    return GovernedShellCommandProfile(
        profile_id="pytest_scoped",
        command_kind="test",
        argv_prefix=["python", "-m", "pytest"],
        allowed_arg_patterns=[
            r"modules/[A-Za-z0-9_./-]+",
            r"tests/[A-Za-z0-9_./-]+",
            r"-q",
            r"--maxfail=\d+",
        ],
        denied_arg_patterns=[
            r".*--index-all.*",
            r".*--reindex.*",
            r".*\.env.*",
            r".*WSP_framework.*",
        ],
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


def valid_request(tmp_path: Path, profile: GovernedShellCommandProfile) -> dict:
    worktree = tmp_path / "governed-shell-worktree"
    return {
        "work_order_id": "wo-shell-1",
        "profile": profile,
        "argv": ["python", "-m", "pytest", "modules/foundups/tests", "-q"],
        "operation_cwd": str(worktree),
        "worktree_path": str(worktree),
        "repo_root": str(REPO_ROOT),
        "selection_receipt": {
            "decision": WARDROBE_SELECTION_ACCEPT,
            "selected_wardrobe": WARDROBE_SOVEREIGN_EXECUTION,
            "execution_plane": EXECUTION_GOVERNED_CANDIDATE,
            "no_execution_performed": True,
        },
        "signed_authority": {
            "accepted": True,
            "signature_gate_status": SIGNATURE_GATE_ACCEPTED,
            "work_order_id": "wo-shell-1",
            "permission_snapshot_digest": "sha256:perm",
            "signature_gate_digest": "sha256:signed-authority",
        },
        "signed_receipt_chain": {
            "accepted": True,
            "decision": SIGNED_RECEIPT_CHAIN_ACCEPT,
            "terminal_receipt_hash": "sha256:terminal",
            "no_execution_performed": True,
            "no_reward_settlement_performed": True,
        },
        "execution_valve_decision": {
            "valve_state": VALVE_OPEN_WORKTREE_CREATE,
            "decision_digest": "sha256:valve",
            "rejection_reasons": [],
            "no_execution_performed": True,
        },
        "generic_writer_dryrun_receipt": {
            "decision": GENERIC_WRITER_DRYRUN_ACCEPT,
            "receipt_id": "generic_wt_dryrun_1234",
            "canonical_root_digest": "sha256:root",
            "artifact_manifest_digest": "sha256:artifacts",
            "no_write_performed": True,
            "no_worktree_created": True,
            "no_shell_performed": True,
        },
        "permission_snapshot_digest": "sha256:perm",
        "consensus_receipt_digest": None,
        "stdin_policy": "none",
        "env_policy": {"scrubbed": True},
        "holoindex_evidence": {
            "index_gap_detected": False,
            "holoindex_freshness_receipt_digest": "sha256:holo-fresh",
        },
    }


def assert_reject(req: dict, code: str) -> None:
    result = plan_governed_shell_runner_dry_run(req)
    assert result.decision == GOVERNED_SHELL_DRYRUN_REJECT
    assert result.accepted is False
    assert code in result.rejection_reasons
    assert result.receipt is None
    assert result.no_execution_performed is True
    assert result.no_command_executed is True


def test_governed_shell_dryrun_accepts_valid_pytest_request(
    tmp_path: Path,
    pytest_profile: GovernedShellCommandProfile,
) -> None:
    result = plan_governed_shell_runner_dry_run(valid_request(tmp_path, pytest_profile))

    assert result.decision == GOVERNED_SHELL_DRYRUN_ACCEPT
    assert result.accepted is True
    assert result.rejection_reasons == []
    assert result.cwd_guard is not None
    assert result.cwd_guard.ok is True
    assert result.receipt is not None
    receipt = result.receipt
    assert receipt.work_order_id == "wo-shell-1"
    assert receipt.profile_id == "pytest_scoped"
    assert receipt.signed_authority_digest == "sha256:signed-authority"
    assert receipt.receipt_chain_terminal_hash == "sha256:terminal"
    assert receipt.execution_valve_decision_digest == "sha256:valve"
    assert receipt.holoindex_freshness_receipt_digest == "sha256:holo-fresh"
    assert receipt.no_command_executed is True
    assert receipt.no_subprocess_performed is True
    assert receipt.no_merge_performed is True
    assert receipt.no_reward_settlement_performed is True
    assert receipt.no_holoindex_reindex_performed is True
    assert receipt.exit_code is None


def test_accepts_mapping_profile(tmp_path: Path, pytest_profile: GovernedShellCommandProfile) -> None:
    req = valid_request(tmp_path, pytest_profile)
    req["profile"] = pytest_profile.to_dict()

    result = plan_governed_shell_runner_dry_run(req)

    assert result.accepted is True
    assert result.receipt is not None
    assert result.receipt.profile_id == "pytest_scoped"


def test_rejects_profile_not_draft_pr_only(tmp_path: Path, pytest_profile: GovernedShellCommandProfile) -> None:
    req = valid_request(tmp_path, pytest_profile)
    req["profile"] = {**pytest_profile.to_dict(), "draft_pr_only": False}

    assert_reject(req, FAIL_PROFILE_INVALID)


def test_rejects_invalid_timeout_and_output_caps(
    tmp_path: Path,
    pytest_profile: GovernedShellCommandProfile,
) -> None:
    req = valid_request(tmp_path, pytest_profile)
    req["profile"] = {**pytest_profile.to_dict(), "timeout_seconds": 0, "max_stdout_bytes": 0}

    result = plan_governed_shell_runner_dry_run(req)

    assert result.accepted is False
    assert FAIL_TIMEOUT_INVALID in result.rejection_reasons
    assert FAIL_OUTPUT_CAP_INVALID in result.rejection_reasons


def test_rejects_empty_or_non_string_argv(tmp_path: Path, pytest_profile: GovernedShellCommandProfile) -> None:
    req = valid_request(tmp_path, pytest_profile)
    req["argv"] = []
    assert_reject(req, FAIL_ARGV_INVALID)

    req = valid_request(tmp_path, pytest_profile)
    req["argv"] = ["python", 1]
    assert_reject(req, FAIL_ARGV_INVALID)


def test_rejects_prefix_mismatch(tmp_path: Path, pytest_profile: GovernedShellCommandProfile) -> None:
    req = valid_request(tmp_path, pytest_profile)
    req["argv"] = ["pytest", "modules/foundups/tests"]

    assert_reject(req, FAIL_ARGV_PREFIX)


@pytest.mark.parametrize("bad_arg", ["modules/foundups/tests; rm -rf .", "modules/a && whoami", "$(whoami)", "x\ny"])
def test_rejects_shell_metacharacters(
    tmp_path: Path,
    pytest_profile: GovernedShellCommandProfile,
    bad_arg: str,
) -> None:
    req = valid_request(tmp_path, pytest_profile)
    req["argv"] = ["python", "-m", "pytest", bad_arg]

    assert_reject(req, FAIL_SHELL_METACHARACTER)


def test_rejects_denied_arg_pattern(tmp_path: Path, pytest_profile: GovernedShellCommandProfile) -> None:
    req = valid_request(tmp_path, pytest_profile)
    req["argv"] = ["python", "-m", "pytest", "modules/foundups/tests", "--index-all"]

    assert_reject(req, FAIL_DENIED_ARG)


def test_rejects_trailing_arg_not_allowed(tmp_path: Path, pytest_profile: GovernedShellCommandProfile) -> None:
    req = valid_request(tmp_path, pytest_profile)
    req["argv"] = ["python", "-m", "pytest", "--capture=sys"]

    assert_reject(req, FAIL_ARG_NOT_ALLOWED)


def test_rejects_secret_like_argv_or_env(tmp_path: Path, pytest_profile: GovernedShellCommandProfile) -> None:
    req = valid_request(tmp_path, pytest_profile)
    req["argv"] = ["python", "-m", "pytest", "modules/foundups/tests", "token=abc"]
    assert_reject(req, FAIL_SECRET_IN_REQUEST)

    req = valid_request(tmp_path, pytest_profile)
    req["env_policy"] = {"API_KEY": "abc"}
    assert_reject(req, FAIL_SECRET_IN_REQUEST)


def test_rejects_bad_selection_receipt(tmp_path: Path, pytest_profile: GovernedShellCommandProfile) -> None:
    req = valid_request(tmp_path, pytest_profile)
    req["selection_receipt"]["selected_wardrobe"] = "wsp97_architect_audit"

    assert_reject(req, FAIL_SELECTION_RECEIPT)


def test_rejects_unsigned_authority(tmp_path: Path, pytest_profile: GovernedShellCommandProfile) -> None:
    req = valid_request(tmp_path, pytest_profile)
    req["signed_authority"] = {"accepted": False, "signature_gate_status": "SIGNATURE_GATE_REJECTED"}

    assert_reject(req, FAIL_SIGNED_AUTHORITY)


def test_rejects_authority_work_order_mismatch(
    tmp_path: Path,
    pytest_profile: GovernedShellCommandProfile,
) -> None:
    req = valid_request(tmp_path, pytest_profile)
    req["signed_authority"]["work_order_id"] = "wo-other"

    assert_reject(req, FAIL_SIGNED_AUTHORITY)


def test_rejects_receipt_chain_failure(tmp_path: Path, pytest_profile: GovernedShellCommandProfile) -> None:
    req = valid_request(tmp_path, pytest_profile)
    req["signed_receipt_chain"] = {"accepted": False, "decision": "SIGNED_RECEIPT_CHAIN_REJECT"}

    assert_reject(req, FAIL_RECEIPT_CHAIN)


def test_rejects_closed_valve(tmp_path: Path, pytest_profile: GovernedShellCommandProfile) -> None:
    req = valid_request(tmp_path, pytest_profile)
    req["execution_valve_decision"] = {
        "valve_state": "VALVE_CLOSED",
        "decision_digest": "sha256:valve",
        "rejection_reasons": ["explicit_valve_flag_missing"],
        "no_execution_performed": True,
    }

    assert_reject(req, FAIL_VALVE_DECISION)


def test_rejects_missing_generic_writer_receipt_when_worktree_required(
    tmp_path: Path,
    pytest_profile: GovernedShellCommandProfile,
) -> None:
    req = valid_request(tmp_path, pytest_profile)
    req["generic_writer_dryrun_receipt"] = {}

    assert_reject(req, FAIL_GENERIC_WRITER_RECEIPT)


def test_rejects_generic_writer_receipt_that_performed_shell(
    tmp_path: Path,
    pytest_profile: GovernedShellCommandProfile,
) -> None:
    req = valid_request(tmp_path, pytest_profile)
    req["generic_writer_dryrun_receipt"]["no_shell_performed"] = False

    assert_reject(req, FAIL_GENERIC_WRITER_RECEIPT)


def test_rejects_consensus_required_missing(
    tmp_path: Path,
    pytest_profile: GovernedShellCommandProfile,
) -> None:
    profile = GovernedShellCommandProfile(**{**pytest_profile.to_dict(), "consensus_required": True})
    req = valid_request(tmp_path, profile)

    assert_reject(req, FAIL_CONSENSUS_REQUIRED)


def test_accepts_consensus_when_required_and_present(
    tmp_path: Path,
    pytest_profile: GovernedShellCommandProfile,
) -> None:
    profile = GovernedShellCommandProfile(**{**pytest_profile.to_dict(), "consensus_required": True})
    req = valid_request(tmp_path, profile)
    req["consensus_receipt_digest"] = "sha256:consensus"

    result = plan_governed_shell_runner_dry_run(req)

    assert result.accepted is True


def test_rejects_holoindex_index_gap_and_missing_freshness(
    tmp_path: Path,
    pytest_profile: GovernedShellCommandProfile,
) -> None:
    req = valid_request(tmp_path, pytest_profile)
    req["holoindex_evidence"] = {"index_gap_detected": True}

    result = plan_governed_shell_runner_dry_run(req)

    assert result.accepted is False
    assert FAIL_HOLOINDEX_INDEX_GAP in result.rejection_reasons
    assert FAIL_HOLOINDEX_FRESHNESS_RECEIPT in result.rejection_reasons


def test_rejects_worktree_inside_repo(tmp_path: Path, pytest_profile: GovernedShellCommandProfile) -> None:
    req = valid_request(tmp_path, pytest_profile)
    req["worktree_path"] = str(REPO_ROOT / ".worktrees" / "bad")
    req["operation_cwd"] = req["worktree_path"]

    assert_reject(req, FAIL_CWD_GUARD)


def test_rejects_relative_operation_cwd(tmp_path: Path, pytest_profile: GovernedShellCommandProfile) -> None:
    req = valid_request(tmp_path, pytest_profile)
    req["operation_cwd"] = "relative/cwd"

    assert_reject(req, FAIL_CWD_GUARD)


def test_readonly_probe_can_skip_worktree_receipt(tmp_path: Path, pytest_profile: GovernedShellCommandProfile) -> None:
    profile = GovernedShellCommandProfile(
        **{
            **pytest_profile.to_dict(),
            "profile_id": "readonly_probe",
            "command_kind": "readonly_probe",
            "argv_prefix": ["python", "--version"],
            "allowed_arg_patterns": [],
            "requires_cwd_guard": False,
            "requires_worktree": False,
            "repo_sensitive": False,
        }
    )
    req = valid_request(tmp_path, profile)
    req["argv"] = ["python", "--version"]
    req["generic_writer_dryrun_receipt"] = {}
    req["holoindex_evidence"] = {}

    result = plan_governed_shell_runner_dry_run(req)

    assert result.accepted is True
    assert result.receipt is not None
    assert result.receipt.generic_writer_dryrun_receipt_digest is None


def test_result_is_json_serializable(tmp_path: Path, pytest_profile: GovernedShellCommandProfile) -> None:
    result = plan_governed_shell_runner_dry_run(valid_request(tmp_path, pytest_profile))

    payload = result.to_dict()

    json.dumps(payload, sort_keys=True)
    assert payload["accepted"] is True
    assert payload["receipt"]["no_command_executed"] is True


def test_governed_shell_dryrun_module_ast_forbids_execution_and_file_write() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    banned_imports = {"subprocess", "os", "shutil"}
    banned_calls = {
        "open",
        "exec",
        "eval",
        "mkdir",
        "write_text",
        "write_bytes",
        "create_worktree",
        "commit_all",
        "push_branch",
        "create_draft_pr",
        "run",
        "Popen",
        "call",
        "check_call",
        "check_output",
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported = {alias.name.split(".")[0] for alias in node.names}
            assert imported.isdisjoint(banned_imports)
        if isinstance(node, ast.ImportFrom) and node.module:
            assert node.module.split(".")[0] not in banned_imports
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                assert node.func.id not in banned_calls
            if isinstance(node.func, ast.Attribute):
                assert node.func.attr not in banned_calls


def test_governed_shell_dryrun_module_ascii_only() -> None:
    text = MODULE_PATH.read_text(encoding="utf-8")
    assert [hex(ord(ch)) for ch in text if ord(ch) > 127] == []
