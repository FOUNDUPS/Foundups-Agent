"""Tests for REDDOG_RESIDENT_QUEUE_DRAFT_PR_PUBLISH_REQUEST_BINDING_PHASE1."""

from __future__ import annotations

import ast
from pathlib import Path

from modules.communication.moltbot_bridge.src.reddog_resident_queue_draft_pr_publish_request_binding import (
    DRAFT_PR_PUBLISH_REQUEST_BINDING_ACCEPT,
    DRAFT_PR_PUBLISH_REQUEST_BINDING_REJECT,
    FAIL_DRAFT_PR_PUBLISH_PLAN_INVALID,
    FAIL_DRAFT_PR_PUBLISH_PLAN_MISSING,
    FAIL_SLICE_VERIFIER_REJECTED,
    FAIL_WORKTREE_CREATE_MISSING,
    build_resident_queue_draft_pr_publish_request,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_slice_verifier_invoke import (
    QUEUE_AUTHORIZED_SLICE_VERIFIER_INVOKE_REJECT,
)
from modules.communication.moltbot_bridge.tests.test_reddog_wre_queue_authorized_verified_draft_pr_publish_invoke import (
    HEAD_SHA,
    WORK_ORDER_ID,
    _queue_verifier_result,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "reddog_resident_queue_draft_pr_publish_request_binding.py"
)


def _plan(**overrides: object) -> dict[str, object]:
    payload = {
        "branch_name": "feat/reddog-queue-draft-pr-publish",
        "base_branch": "main",
        "pr_title": "feat(reddog): verified queue draft pr publish",
        "pr_body": "Verified by WRE autonomous slice verifier.",
        "draft_pr_only": True,
        "mark_ready": False,
        "merge": False,
    }
    payload.update(overrides)
    return payload


def _work_order(**overrides: object) -> dict[str, object]:
    payload = {
        "work_order_id": WORK_ORDER_ID,
        "base_ref": "main",
        "draft_pr_publish_plan": _plan(),
    }
    payload.update(overrides)
    return payload


def _stage_results(tmp_path: Path, **overrides: object) -> dict[str, object]:
    payload = {
        "slice_verifier": _queue_verifier_result(),
        "worktree_create": {
            "worktree_create_result": {
                "worktree_path": str(tmp_path / "resident-worktree"),
            }
        },
    }
    payload.update(overrides)
    return payload


def test_builds_publish_request_from_verified_chain_state(tmp_path: Path) -> None:
    result = build_resident_queue_draft_pr_publish_request(
        work_order=_work_order(),
        stage_results=_stage_results(tmp_path),
    )

    assert result.accepted is True
    assert result.decision == DRAFT_PR_PUBLISH_REQUEST_BINDING_ACCEPT
    assert result.rejection_reasons == []
    request = result.publish_request
    assert request["work_order_id"] == WORK_ORDER_ID
    assert request["pre_publish_branch_head_sha"] == HEAD_SHA
    assert request["branch_name"] == "feat/reddog-queue-draft-pr-publish"
    assert request["base_branch"] == "main"
    assert request["draft_pr_only"] is True
    assert request["mark_ready"] is False
    assert request["merge"] is False
    assert result.no_git_push_performed is True
    assert result.no_github_call_performed is True
    assert result.no_pr_created is True
    assert result.no_ready_performed is True
    assert result.no_merge_performed is True
    assert result.no_pattern_memory_write_performed is True
    assert result.no_reward_settlement_performed is True
    assert result.no_openclaw_enqueue_performed is True
    assert result.no_hermes_dispatch_performed is True
    assert result.no_holoindex_reindex_performed is True


def test_missing_publish_plan_rejects(tmp_path: Path) -> None:
    result = build_resident_queue_draft_pr_publish_request(
        work_order=_work_order(draft_pr_publish_plan={}),
        stage_results=_stage_results(tmp_path),
    )

    assert result.accepted is False
    assert result.decision == DRAFT_PR_PUBLISH_REQUEST_BINDING_REJECT
    assert FAIL_DRAFT_PR_PUBLISH_PLAN_MISSING in result.rejection_reasons
    assert result.publish_request == {}


def test_rejected_slice_verifier_blocks_publish_request(tmp_path: Path) -> None:
    result = build_resident_queue_draft_pr_publish_request(
        work_order=_work_order(),
        stage_results=_stage_results(
            tmp_path,
            slice_verifier=_queue_verifier_result(
                decision=QUEUE_AUTHORIZED_SLICE_VERIFIER_INVOKE_REJECT
            ),
        ),
    )

    assert result.accepted is False
    assert FAIL_SLICE_VERIFIER_REJECTED in result.rejection_reasons


def test_missing_worktree_create_blocks_publish_request(tmp_path: Path) -> None:
    result = build_resident_queue_draft_pr_publish_request(
        work_order=_work_order(),
        stage_results=_stage_results(tmp_path, worktree_create={}),
    )

    assert result.accepted is False
    assert FAIL_WORKTREE_CREATE_MISSING in result.rejection_reasons


def test_ready_or_merge_plan_rejects(tmp_path: Path) -> None:
    result = build_resident_queue_draft_pr_publish_request(
        work_order=_work_order(
            draft_pr_publish_plan=_plan(draft_pr_only=False, mark_ready=True, merge=True)
        ),
        stage_results=_stage_results(tmp_path),
    )

    assert result.accepted is False
    assert f"{FAIL_DRAFT_PR_PUBLISH_PLAN_INVALID}:draft_pr_only" in result.rejection_reasons
    assert f"{FAIL_DRAFT_PR_PUBLISH_PLAN_INVALID}:mark_ready" in result.rejection_reasons
    assert f"{FAIL_DRAFT_PR_PUBLISH_PLAN_INVALID}:merge" in result.rejection_reasons


def test_module_has_no_shell_network_git_holoindex_or_publish_authority() -> None:
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
        "push_branch(",
        "create_draft_pr(",
        "mark_ready(",
        "merge_pr",
        "PatternMemory(",
        "store_outcome",
        "settle_reward",
        "holo_index.py --index",
    )
    for token in forbidden_tokens:
        assert token not in source
