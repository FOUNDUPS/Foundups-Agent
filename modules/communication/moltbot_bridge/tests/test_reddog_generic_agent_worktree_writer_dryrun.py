"""Tests for REDDOG_GENERIC_AGENT_WORKTREE_WRITER_DRYRUN_PHASE1."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.src.reddog_generic_agent_worktree_writer_dryrun import (
    FAIL_ARTIFACTS_INVALID,
    FAIL_CALLER_PATHS_WIDEN_PROFILE,
    FAIL_CONSENSUS_REQUIRED,
    FAIL_CWD_GUARD,
    FAIL_DENIED_PATH,
    FAIL_DOMAIN_ID_INVALID,
    FAIL_HOLOINDEX_INDEX_GAP,
    FAIL_OPERATION_MISMATCH,
    FAIL_PROFILE_INVALID,
    FAIL_PROTECTED_BRANCH,
    FAIL_RECEIPT_CHAIN,
    FAIL_SELECTION_RECEIPT,
    FAIL_SIGNED_AUTHORITY,
    FAIL_VALVE_DECISION,
    GENERIC_WRITER_DRYRUN_ACCEPT,
    GENERIC_WRITER_DRYRUN_REJECT,
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

REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "reddog_generic_agent_worktree_writer_dryrun.py"
)


@pytest.fixture()
def domain_profile() -> GenericAgentWorktreeDomainProfile:
    return GenericAgentWorktreeDomainProfile(
        profile_id="docs_patch",
        operation="write_docs",
        artifact_contract_type="docs_patch_contract",
        domain_id_pattern=r"[a-z][a-z0-9_]{2,49}",
        canonical_root_template="docs/audits/{domain_id}",
        allowed_path_patterns=["docs/audits/{domain_id}/**"],
        denied_path_patterns=["**/secrets/**", "**/.env"],
        required_tests=["pytest modules/communication/moltbot_bridge/tests/test_docs_patch.py"],
        branch_prefix="feat/",
        draft_pr_only=True,
        consensus_required=False,
    )


def valid_request(tmp_path: Path, domain_profile: GenericAgentWorktreeDomainProfile) -> dict:
    worktree = tmp_path / "generic-writer-worktree"
    return {
        "work_order_id": "wo-generic-1",
        "operation": "write_docs",
        "domain_id": "test_thing",
        "domain_profile": domain_profile,
        "planned_artifacts": [
            "docs/audits/test_thing/README.md",
            "docs/audits/test_thing/ModLog.md",
        ],
        "requested_allowed_paths": ["docs/audits/test_thing/**"],
        "target_branch": "feat/generic-agent-test-thing",
        "repo_root": str(REPO_ROOT),
        "worktree_path": str(worktree),
        "operation_cwd": str(worktree),
        "selection_receipt": {
            "decision": WARDROBE_SELECTION_ACCEPT,
            "selected_wardrobe": WARDROBE_SOVEREIGN_EXECUTION,
            "execution_plane": EXECUTION_GOVERNED_CANDIDATE,
            "no_execution_performed": True,
        },
        "signed_authority": {
            "accepted": True,
            "signature_gate_status": SIGNATURE_GATE_ACCEPTED,
            "work_order_id": "wo-generic-1",
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
        "permission_snapshot_digest": "sha256:perm",
        "consensus_receipt_digest": None,
        "holoindex_evidence": {"index_gap_detected": False},
    }


def assert_reject(req: dict, code: str) -> None:
    result = plan_generic_agent_worktree_writer_dry_run(req)
    assert result.decision == GENERIC_WRITER_DRYRUN_REJECT
    assert result.accepted is False
    assert code in result.rejection_reasons
    assert result.receipt is None
    assert result.no_execution_performed is True


def test_generic_writer_dryrun_accepts_valid_scoped_request(
    tmp_path: Path,
    domain_profile: GenericAgentWorktreeDomainProfile,
) -> None:
    result = plan_generic_agent_worktree_writer_dry_run(valid_request(tmp_path, domain_profile))

    assert result.decision == GENERIC_WRITER_DRYRUN_ACCEPT
    assert result.accepted is True
    assert result.rejection_reasons == []
    assert result.cwd_guard is not None
    assert result.cwd_guard.ok is True
    assert result.receipt is not None
    receipt = result.receipt
    assert receipt.canonical_root == "docs/audits/test_thing"
    assert receipt.planned_artifacts == [
        "docs/audits/test_thing/ModLog.md",
        "docs/audits/test_thing/README.md",
    ]
    assert receipt.no_write_performed is True
    assert receipt.no_worktree_created is True
    assert receipt.no_shell_performed is True
    assert receipt.no_merge_performed is True
    assert receipt.no_reward_settlement_performed is True
    assert receipt.no_holoindex_reindex_performed is True
    assert receipt.execution_valve_decision_digest == "sha256:valve"
    assert receipt.signed_authority_digest == "sha256:signed-authority"


def test_generic_writer_dryrun_accepts_mapping_profile(
    tmp_path: Path,
    domain_profile: GenericAgentWorktreeDomainProfile,
) -> None:
    req = valid_request(tmp_path, domain_profile)
    req["domain_profile"] = domain_profile.to_dict()

    result = plan_generic_agent_worktree_writer_dry_run(req)

    assert result.accepted is True
    assert result.receipt is not None
    assert result.receipt.domain_profile_id == "docs_patch"


def test_rejects_profile_not_draft_pr_only(
    tmp_path: Path,
    domain_profile: GenericAgentWorktreeDomainProfile,
) -> None:
    req = valid_request(tmp_path, domain_profile)
    req["domain_profile"] = {**domain_profile.to_dict(), "draft_pr_only": False}

    assert_reject(req, FAIL_PROFILE_INVALID)


def test_rejects_operation_mismatch(tmp_path: Path, domain_profile: GenericAgentWorktreeDomainProfile) -> None:
    req = valid_request(tmp_path, domain_profile)
    req["operation"] = "shell"

    assert_reject(req, FAIL_OPERATION_MISMATCH)


def test_rejects_invalid_domain_id(tmp_path: Path, domain_profile: GenericAgentWorktreeDomainProfile) -> None:
    req = valid_request(tmp_path, domain_profile)
    req["domain_id"] = "../escape"

    assert_reject(req, FAIL_DOMAIN_ID_INVALID)


def test_rejects_caller_allowed_path_widening(
    tmp_path: Path,
    domain_profile: GenericAgentWorktreeDomainProfile,
) -> None:
    req = valid_request(tmp_path, domain_profile)
    req["requested_allowed_paths"] = ["docs/**"]

    assert_reject(req, FAIL_CALLER_PATHS_WIDEN_PROFILE)


def test_rejects_artifact_outside_canonical_root(
    tmp_path: Path,
    domain_profile: GenericAgentWorktreeDomainProfile,
) -> None:
    req = valid_request(tmp_path, domain_profile)
    req["planned_artifacts"] = ["docs/audits/other/README.md"]

    assert_reject(req, FAIL_ARTIFACTS_INVALID)


def test_rejects_traversal_artifact(
    tmp_path: Path,
    domain_profile: GenericAgentWorktreeDomainProfile,
) -> None:
    req = valid_request(tmp_path, domain_profile)
    req["planned_artifacts"] = ["docs/audits/test_thing/../escape.md"]

    assert_reject(req, FAIL_ARTIFACTS_INVALID)


def test_rejects_pin_independent_denied_path(
    tmp_path: Path,
    domain_profile: GenericAgentWorktreeDomainProfile,
) -> None:
    req = valid_request(tmp_path, domain_profile)
    req["planned_artifacts"] = [
        "docs/audits/test_thing/README.md",
        "docs/audits/test_thing/.env",
    ]

    assert_reject(req, FAIL_DENIED_PATH)


def test_rejects_non_sovereign_selection_receipt(
    tmp_path: Path,
    domain_profile: GenericAgentWorktreeDomainProfile,
) -> None:
    req = valid_request(tmp_path, domain_profile)
    req["selection_receipt"] = {
        "decision": WARDROBE_SELECTION_ACCEPT,
        "selected_wardrobe": "wsp97_implementation_slice",
        "execution_plane": "worker_draft_pr",
        "no_execution_performed": True,
    }

    assert_reject(req, FAIL_SELECTION_RECEIPT)


def test_rejects_unsigned_authority(tmp_path: Path, domain_profile: GenericAgentWorktreeDomainProfile) -> None:
    req = valid_request(tmp_path, domain_profile)
    req["signed_authority"] = {"accepted": False, "signature_gate_status": "SIGNATURE_GATE_REJECTED"}

    assert_reject(req, FAIL_SIGNED_AUTHORITY)


def test_rejects_authority_bound_to_other_work_order(
    tmp_path: Path,
    domain_profile: GenericAgentWorktreeDomainProfile,
) -> None:
    req = valid_request(tmp_path, domain_profile)
    req["signed_authority"]["work_order_id"] = "wo-other"

    assert_reject(req, FAIL_SIGNED_AUTHORITY)


def test_rejects_receipt_chain_failure(tmp_path: Path, domain_profile: GenericAgentWorktreeDomainProfile) -> None:
    req = valid_request(tmp_path, domain_profile)
    req["signed_receipt_chain"] = {"accepted": False, "decision": "SIGNED_RECEIPT_CHAIN_REJECT"}

    assert_reject(req, FAIL_RECEIPT_CHAIN)


def test_rejects_closed_valve(tmp_path: Path, domain_profile: GenericAgentWorktreeDomainProfile) -> None:
    req = valid_request(tmp_path, domain_profile)
    req["execution_valve_decision"] = {
        "valve_state": "VALVE_CLOSED",
        "decision_digest": "sha256:valve",
        "rejection_reasons": ["explicit_valve_flag_missing"],
        "no_execution_performed": True,
    }

    assert_reject(req, FAIL_VALVE_DECISION)


def test_rejects_consensus_required_missing(
    tmp_path: Path,
    domain_profile: GenericAgentWorktreeDomainProfile,
) -> None:
    profile = GenericAgentWorktreeDomainProfile(
        **{**domain_profile.to_dict(), "consensus_required": True}
    )
    req = valid_request(tmp_path, profile)

    assert_reject(req, FAIL_CONSENSUS_REQUIRED)


def test_accepts_consensus_when_required_and_present(
    tmp_path: Path,
    domain_profile: GenericAgentWorktreeDomainProfile,
) -> None:
    profile = GenericAgentWorktreeDomainProfile(
        **{**domain_profile.to_dict(), "consensus_required": True}
    )
    req = valid_request(tmp_path, profile)
    req["consensus_receipt_digest"] = "sha256:consensus"

    result = plan_generic_agent_worktree_writer_dry_run(req)

    assert result.accepted is True
    assert result.receipt is not None
    assert result.receipt.consensus_receipt_digest == "sha256:consensus"


def test_rejects_holoindex_index_gap_on_write(
    tmp_path: Path,
    domain_profile: GenericAgentWorktreeDomainProfile,
) -> None:
    req = valid_request(tmp_path, domain_profile)
    req["holoindex_evidence"] = {"index_gap_detected": True}

    assert_reject(req, FAIL_HOLOINDEX_INDEX_GAP)


def test_rejects_worktree_inside_repo(
    tmp_path: Path,
    domain_profile: GenericAgentWorktreeDomainProfile,
) -> None:
    req = valid_request(tmp_path, domain_profile)
    req["worktree_path"] = str(REPO_ROOT / ".worktrees" / "bad")
    req["operation_cwd"] = req["worktree_path"]

    assert_reject(req, FAIL_CWD_GUARD)


def test_rejects_relative_worktree_path(
    tmp_path: Path,
    domain_profile: GenericAgentWorktreeDomainProfile,
) -> None:
    req = valid_request(tmp_path, domain_profile)
    req["worktree_path"] = "relative/worktree"
    req["operation_cwd"] = "relative/worktree"

    assert_reject(req, FAIL_CWD_GUARD)


def test_rejects_protected_branch(tmp_path: Path, domain_profile: GenericAgentWorktreeDomainProfile) -> None:
    req = valid_request(tmp_path, domain_profile)
    req["target_branch"] = "main"

    assert_reject(req, FAIL_PROTECTED_BRANCH)


def test_result_is_json_serializable(tmp_path: Path, domain_profile: GenericAgentWorktreeDomainProfile) -> None:
    result = plan_generic_agent_worktree_writer_dry_run(valid_request(tmp_path, domain_profile))

    payload = result.to_dict()

    assert payload["accepted"] is True
    assert payload["receipt"]["no_write_performed"] is True


def test_generic_writer_module_ast_forbids_execution_and_file_write() -> None:
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


def test_generic_writer_module_ascii_only() -> None:
    text = MODULE_PATH.read_text(encoding="utf-8")
    assert [hex(ord(ch)) for ch in text if ord(ch) > 127] == []
