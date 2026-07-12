"""Tests for RedDog operator-loop wardrobe selection dry-run."""

from __future__ import annotations

import ast
import json
from pathlib import Path

from modules.communication.moltbot_bridge.src.reddog_operator_loop_wardrobe_selection import (
    AUTHORITY_DRAFT_PR_ONLY,
    AUTHORITY_NONE,
    AUTHORITY_SIGNED_VALVE_REQUIRED,
    AUTHORITY_SOVEREIGN_TOKEN_REQUIRED,
    EXECUTION_ADVISORY_ONLY,
    EXECUTION_AUDIT_ONLY,
    EXECUTION_GROUNDING_BLOCKED,
    EXECUTION_GOVERNED_CANDIDATE,
    EXECUTION_WORKER_DRAFT_PR,
    FRESHNESS_FRESH,
    FRESHNESS_INDEX_GAP,
    IMPLEMENTATION_STATUS_SPECIFIED_NOT_IMPLEMENTED,
    WARDROBE_ARCHITECT_AUDIT,
    WARDROBE_IMPLEMENTATION_SLICE,
    WARDROBE_NO_ACTION_PLANE,
    WARDROBE_SELECTION_ACCEPT,
    WARDROBE_SELECTION_REJECT,
    WARDROBE_SOLO_RETRIEVAL,
    WARDROBE_SOVEREIGN_EXECUTION,
    select_reddog_operator_loop_wardrobe_dryrun,
)

REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "reddog_operator_loop_wardrobe_selection.py"
)


def _holo(**overrides):
    payload = {
        "holoindex_query": "RedDog operator loop wardrobe selection",
        "holoindex_status": "bundle_json_ok",
        "code_hits": [{"path": "extensions/foundups_advisory_workers/extension.js"}],
        "wsp_hits": [{"path": "WSP_knowledge/src/WSP_97_System_Execution_Prompting_Protocol.md"}],
        "skill_hits": [{"skill_name": "autonomous_slice_worker"}],
        "index_gap_detected": False,
    }
    payload.update(overrides)
    return payload


def test_simple_exploration_selects_solo_retrieval() -> None:
    result = select_reddog_operator_loop_wardrobe_dryrun(
        "Explain what RedDog does at a high level.",
        holoindex_evidence=_holo(),
    )
    assert result.decision == WARDROBE_SELECTION_ACCEPT
    assert result.receipt.selected_wardrobe == WARDROBE_SOLO_RETRIEVAL
    assert result.receipt.execution_plane == EXECUTION_ADVISORY_ONLY
    assert result.receipt.authority_boundary == AUTHORITY_NONE
    assert result.receipt.selected_context_mode == "wsp_holo"
    assert result.receipt.selected_model_mode == "openrouter_single"
    assert result.receipt.selected_effort == "regular"


def test_architecture_audit_selects_architect_audit() -> None:
    result = select_reddog_operator_loop_wardrobe_dryrun(
        "Audit RedDog WSP_97 operator loop and HoloIndex evidence.",
        holoindex_evidence=_holo(),
    )
    assert result.decision == WARDROBE_SELECTION_ACCEPT
    assert result.receipt.selected_wardrobe == WARDROBE_ARCHITECT_AUDIT
    assert result.receipt.execution_plane == EXECUTION_AUDIT_ONLY
    assert result.receipt.selected_context_mode == "wsp_holo_skillz"
    assert result.receipt.selected_model_mode == "foundups_fusion"
    assert result.receipt.selected_effort == "high"
    assert "WSP_97" in result.governing_wsps


def test_implementation_request_selects_draft_pr_plane() -> None:
    result = select_reddog_operator_loop_wardrobe_dryrun(
        "Implement a scoped fix and open a draft PR.",
        authority_request="draft_pr",
        holoindex_evidence=_holo(),
        required_targets=["modules/communication/moltbot_bridge/src/foo.py"],
        target_recall_ok=True,
    )
    assert result.decision == WARDROBE_SELECTION_ACCEPT
    assert result.receipt.selected_wardrobe == WARDROBE_IMPLEMENTATION_SLICE
    assert result.receipt.execution_plane == EXECUTION_WORKER_DRAFT_PR
    assert result.receipt.authority_boundary == AUTHORITY_DRAFT_PR_ONLY
    assert result.receipt.wre_required is True
    assert result.receipt.direct_read_required is True
    assert result.receipt.grounding_preflight_applied is False
    assert result.receipt.grounding_preflight_passed is True


def test_passed_grounding_preflight_is_bound_into_receipt() -> None:
    result = select_reddog_operator_loop_wardrobe_dryrun(
        "Implement a scoped fix and open a draft PR.",
        authority_request="draft_pr",
        holoindex_evidence=_holo(),
        required_targets=["modules/communication/moltbot_bridge/src/foo.py"],
        target_recall_ok=True,
        grounding_preflight={
            "applied": True,
            "passed": True,
            "rejection_reasons": [],
            "repo_file_targets_count": 1,
            "semantic_targets_count": 0,
            "external_research_targets_count": 0,
            "quoted_reference_blocks_count": 0,
        },
    )
    assert result.decision == WARDROBE_SELECTION_ACCEPT
    assert result.receipt.selected_wardrobe == WARDROBE_IMPLEMENTATION_SLICE
    assert result.receipt.grounding_preflight_applied is True
    assert result.receipt.grounding_preflight_passed is True
    assert len(result.receipt.grounding_preflight_digest) == 64
    assert result.receipt.grounding_preflight_rejection_reasons == []


def test_failed_grounding_preflight_blocks_action_plane_selection() -> None:
    result = select_reddog_operator_loop_wardrobe_dryrun(
        "Implement a slice using an ungrounded external paper.",
        authority_request="draft_pr",
        holoindex_evidence=_holo(),
        grounding_preflight={
            "applied": True,
            "passed": False,
            "rejection_reasons": ["external_research_retrieval_not_implemented"],
            "repo_file_targets_count": 0,
            "semantic_targets_count": 0,
            "external_research_targets_count": 1,
            "quoted_reference_blocks_count": 0,
        },
    )
    assert result.decision == WARDROBE_SELECTION_REJECT
    assert result.receipt.selected_wardrobe == WARDROBE_NO_ACTION_PLANE
    assert result.receipt.execution_plane == EXECUTION_GROUNDING_BLOCKED
    assert result.receipt.wre_required is False
    assert result.receipt.authority_boundary == AUTHORITY_NONE
    assert result.receipt.grounding_preflight_applied is True
    assert result.receipt.grounding_preflight_passed is False
    assert result.receipt.grounding_preflight_rejection_reasons == [
        "external_research_retrieval_not_implemented"
    ]
    assert "grounding_preflight_not_passed" in result.receipt.rejection_reasons
    assert "grounding:external_research_retrieval_not_implemented" in result.receipt.rejection_reasons


def test_live_enqueue_request_selects_sovereign_execution_candidate() -> None:
    result = select_reddog_operator_loop_wardrobe_dryrun(
        "Invoke RedDog live enqueue for the next worker.",
        authority_request="live_enqueue",
        holoindex_evidence=_holo(),
    )
    assert result.decision == WARDROBE_SELECTION_ACCEPT
    assert result.receipt.selected_wardrobe == WARDROBE_SOVEREIGN_EXECUTION
    assert result.receipt.execution_plane == EXECUTION_GOVERNED_CANDIDATE
    assert result.receipt.authority_boundary == AUTHORITY_SIGNED_VALVE_REQUIRED
    assert result.receipt.rejection_reasons == []


def test_shell_or_merge_request_requires_sovereign_token_boundary() -> None:
    for authority_request in ("shell", "merge", "worktree_write", "reward"):
        result = select_reddog_operator_loop_wardrobe_dryrun(
            "Run governed shell work for RedDog.",
            authority_request=authority_request,
            holoindex_evidence=_holo(),
        )
        assert result.receipt.selected_wardrobe == WARDROBE_SOVEREIGN_EXECUTION
        assert result.receipt.authority_boundary == AUTHORITY_SOVEREIGN_TOKEN_REQUIRED


def test_index_gap_rejects_write_sensitive_selection() -> None:
    result = select_reddog_operator_loop_wardrobe_dryrun(
        "Implement RedDog extension to live enqueue.",
        authority_request="draft_pr",
        holoindex_evidence=_holo(index_gap_detected=True, retrieval_quality="INDEX_GAP"),
        required_targets=["extensions/foundups_advisory_workers/extension.js"],
        target_recall_ok=True,
    )
    assert result.decision == WARDROBE_SELECTION_REJECT
    assert result.receipt.holoindex_freshness_label == FRESHNESS_INDEX_GAP
    assert result.receipt.index_gap_detected is True
    assert "write_sensitive_index_gap" in result.receipt.rejection_reasons


def test_target_recall_failure_is_fail_closed_and_direct_read_required() -> None:
    result = select_reddog_operator_loop_wardrobe_dryrun(
        "Audit current work ledger artifacts.",
        holoindex_evidence=_holo(),
        required_targets=["docs/0102_session_briefings/ACTIVE_SLICE_LEDGER.md"],
        target_recall_ok=False,
    )
    assert result.decision == WARDROBE_SELECTION_REJECT
    assert result.receipt.direct_read_required is True
    assert "required_target_recall_not_ok" in result.receipt.rejection_reasons


def test_repo_work_without_holoindex_evidence_rejects() -> None:
    result = select_reddog_operator_loop_wardrobe_dryrun(
        "Audit the RedDog codebase routing module.",
        holoindex_evidence=None,
    )
    assert result.decision == WARDROBE_SELECTION_REJECT
    assert "holoindex_evidence_missing_for_repo_work" in result.receipt.rejection_reasons


def test_skillz_candidates_and_lane_refs_are_preserved() -> None:
    result = select_reddog_operator_loop_wardrobe_dryrun(
        "Use WSP_95 wardrobe Skillz to plan worker orchestration.",
        authority_request="worker_orchestration",
        holoindex_evidence=_holo(
            skill_hits=[
                {"skill_name": "autonomous_slice_worker"},
                {"skill_name": "foundup_genesis_intake"},
            ]
        ),
        lane_refs=["#954", "#953"],
    )
    assert result.receipt.skillz_candidates[:2] == [
        "autonomous_slice_worker",
        "foundup_genesis_intake",
    ]
    assert "wsp95_wardrobe_selection" in result.receipt.skillz_candidates
    assert result.receipt.lane_refs == ["#954", "#953"]


def test_manual_mode_overrides_are_respected() -> None:
    result = select_reddog_operator_loop_wardrobe_dryrun(
        "Audit RedDog architecture.",
        selected_context_mode="wsp_holo_git_skillz",
        selected_model_mode="openrouter_single",
        selected_effort="ultra",
        holoindex_evidence=_holo(),
    )
    assert result.receipt.selected_context_mode == "wsp_holo_git_skillz"
    assert result.receipt.selected_model_mode == "openrouter_single"
    assert result.receipt.selected_effort == "ultra"


def test_receipt_digest_is_deterministic_for_same_inputs() -> None:
    kwargs = {
        "work_focus": "Audit RedDog WSP_97 operator loop.",
        "holoindex_evidence": _holo(),
        "wsp_refs": ["WSP_97", "WSP_95"],
    }
    first = select_reddog_operator_loop_wardrobe_dryrun(**kwargs)
    second = select_reddog_operator_loop_wardrobe_dryrun(**kwargs)
    assert first.receipt.selection_id == second.receipt.selection_id
    assert len(first.receipt.selection_id) == 64


def test_receipt_json_serializable_and_no_execution_flags() -> None:
    result = select_reddog_operator_loop_wardrobe_dryrun(
        "Implement a scoped fix.",
        authority_request="draft_pr",
        holoindex_evidence=_holo(),
    )
    encoded = json.dumps(result.to_dict(), sort_keys=True)
    assert "RedDogOperatorLoopWardrobeSelectionReceipt" not in encoded
    assert result.receipt.no_execution_performed is True
    assert result.receipt.no_enqueue_performed is True
    assert result.receipt.implementation_status == IMPLEMENTATION_STATUS_SPECIFIED_NOT_IMPLEMENTED


def test_fresh_holoindex_label_when_bundle_ok() -> None:
    result = select_reddog_operator_loop_wardrobe_dryrun(
        "Explain RedDog.",
        holoindex_evidence=_holo(),
    )
    assert result.receipt.holoindex_freshness_label == FRESHNESS_FRESH


def test_ast_denylist_for_runtime_authority_surfaces() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    banned_imports = {
        "subprocess",
        "os",
        "git",
        "gh",
        "openclaw_supervisor",
        "hermes_job_executor",
        "agent_db",
        "wre_core",
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported = {alias.name.split(".")[0] for alias in node.names}
            assert imported.isdisjoint(banned_imports)
        if isinstance(node, ast.ImportFrom):
            module = (node.module or "").split(".")[0]
            assert module not in banned_imports
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                assert node.func.id not in {"eval", "exec", "open"}
            if isinstance(node.func, ast.Attribute):
                assert node.func.attr not in {"system", "popen", "run", "Popen"}
