"""Tests for REDDOG_WRE_QUEUE_AUTHORIZED_VERIFIED_DRAFT_PR_PUBLISH_INVOKE_PHASE1."""

from __future__ import annotations

import ast
import json
from pathlib import Path

from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_slice_verifier_invoke import (
    QUEUE_AUTHORIZED_SLICE_VERIFIER_INVOKE_ACCEPT,
    QUEUE_AUTHORIZED_SLICE_VERIFIER_INVOKE_REJECT,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_verified_draft_pr_publish_invoke import (
    QUEUE_AUTHORIZED_VERIFIED_DRAFT_PR_PUBLISH_INVOKE_ACCEPT,
    QUEUE_AUTHORIZED_VERIFIED_DRAFT_PR_PUBLISH_INVOKE_REJECT,
    QueueAuthorizedVerifiedDraftPrPublishInvokeReason,
    invoke_reddog_wre_queue_authorized_verified_draft_pr_publish,
)
from modules.infrastructure.wre_core.src.reddog_verified_draft_pr_publish import (
    VERIFIED_DRAFT_PR_PUBLISH_ACCEPT,
    VERIFIED_DRAFT_PR_PUBLISH_REJECT,
)
from modules.infrastructure.wre_core.src.wre_autonomous_slice_verifier_runtime import (
    AUTONOMOUS_SLICE_VERIFIER_ACCEPT,
    AUTONOMOUS_SLICE_VERIFIER_REJECT,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "reddog_wre_queue_authorized_verified_draft_pr_publish_invoke.py"
)
WORK_ORDER_ID = "wo-queue-draft-pr-1"
HEAD_SHA = "a" * 40
ARTIFACT = "modules/communication/moltbot_bridge/tests/fixtures/reddog_queue_pilot/README.md"


class FakeDraftPrRunner:
    def __init__(self, *, push_ok: bool = True, pr_url: str | None = None) -> None:
        self.push_ok = push_ok
        self.pr_url = pr_url or "https://github.com/FOUNDUPS/Foundups-Agent/pull/2000"
        self.calls: list[tuple] = []

    def push_branch(self, *, worktree_path: Path, branch_name: str):
        self.calls.append(("push_branch", str(worktree_path), branch_name))
        return {"ok": self.push_ok, "stdout": "", "stderr": "" if self.push_ok else "push failed"}

    def create_draft_pr(self, *, branch_name: str, base_branch: str, title: str, body: str):
        self.calls.append(("create_draft_pr", branch_name, base_branch, title, body))
        if self.pr_url == "RAISE":
            raise RuntimeError("draft pr failed")
        return self.pr_url


def _queue_verifier_result(*, decision: str | None = None, verifier_decision: str | None = None) -> dict:
    accepted = (verifier_decision or AUTONOMOUS_SLICE_VERIFIER_ACCEPT) == AUTONOMOUS_SLICE_VERIFIER_ACCEPT
    return {
        "decision": decision or QUEUE_AUTHORIZED_SLICE_VERIFIER_INVOKE_ACCEPT,
        "rejection_reasons": [],
        "explicit_queue_authorized_slice_verifier_requested": True,
        "verifier_result": {
            "decision": verifier_decision or AUTONOMOUS_SLICE_VERIFIER_ACCEPT,
            "accepted": accepted,
            "rejection_reasons": [] if accepted else ["FAIL_TEST_EVIDENCE"],
            "receipt": {
                "receipt_id": "wre_slice_verify_1234",
                "work_order_id": WORK_ORDER_ID,
                "slice_name": "REDDOG_WRE_QUEUE_AUTHORIZED_VERIFIED_DRAFT_PR_PUBLISH_INVOKE_PHASE1",
                "worker_id": "worker:author",
                "verifier_id": "worker:verifier",
                "head_sha": HEAD_SHA,
                "changed_paths": [ARTIFACT],
            },
        },
    }


def _publish_request() -> dict:
    return {
        "work_order_id": WORK_ORDER_ID,
        "pre_publish_branch_head_sha": HEAD_SHA,
        "branch_name": "feat/reddog-queue-draft-pr-publish",
        "base_branch": "main",
        "pr_title": "feat(reddog): verified queue draft pr publish",
        "pr_body": "Verified by WRE autonomous slice verifier.",
        "worktree_path": "O:/tmp/reddog-worker",
        "draft_pr_only": True,
        "mark_ready": False,
        "merge": False,
    }


def _invoke(
    *,
    queue_verifier: dict | None = None,
    publish_request: dict | None = None,
    runner: FakeDraftPrRunner | None = None,
):
    return invoke_reddog_wre_queue_authorized_verified_draft_pr_publish(
        explicit_queue_authorized_verified_draft_pr_publish_requested=True,
        queue_slice_verifier_result=queue_verifier or _queue_verifier_result(),
        publish_request=publish_request or _publish_request(),
        runner=runner or FakeDraftPrRunner(),
    )


def test_invokes_verified_draft_pr_publish_from_accepted_verifier() -> None:
    runner = FakeDraftPrRunner()

    result = _invoke(runner=runner)

    assert result.decision == QUEUE_AUTHORIZED_VERIFIED_DRAFT_PR_PUBLISH_INVOKE_ACCEPT
    assert result.rejection_reasons == []
    assert result.publish_result is not None
    assert result.publish_result.decision == VERIFIED_DRAFT_PR_PUBLISH_ACCEPT
    assert result.publish_result.receipt.draft_pr_url.endswith("/pull/2000")
    assert result.publish_result.receipt.no_ready_performed is True
    assert result.publish_result.receipt.no_merge_performed is True
    assert result.no_ready_performed is True
    assert result.no_merge_performed is True
    assert result.no_pattern_memory_write_performed is True
    assert result.no_reward_settlement_performed is True
    assert result.no_holoindex_reindex_performed is True
    assert [call[0] for call in runner.calls] == ["push_branch", "create_draft_pr"]


def test_explicit_invoke_missing_rejects_before_runner() -> None:
    runner = FakeDraftPrRunner()

    result = invoke_reddog_wre_queue_authorized_verified_draft_pr_publish(
        explicit_queue_authorized_verified_draft_pr_publish_requested=False,
        queue_slice_verifier_result=_queue_verifier_result(),
        publish_request=_publish_request(),
        runner=runner,
    )

    assert result.decision == QUEUE_AUTHORIZED_VERIFIED_DRAFT_PR_PUBLISH_INVOKE_REJECT
    assert (
        QueueAuthorizedVerifiedDraftPrPublishInvokeReason.EXPLICIT_INVOKE_MISSING
        in result.rejection_reasons
    )
    assert result.publish_result is None
    assert runner.calls == []


def test_runner_required_rejects() -> None:
    result = invoke_reddog_wre_queue_authorized_verified_draft_pr_publish(
        explicit_queue_authorized_verified_draft_pr_publish_requested=True,
        queue_slice_verifier_result=_queue_verifier_result(),
        publish_request=_publish_request(),
        runner=None,
    )

    assert result.decision == QUEUE_AUTHORIZED_VERIFIED_DRAFT_PR_PUBLISH_INVOKE_REJECT
    assert QueueAuthorizedVerifiedDraftPrPublishInvokeReason.RUNNER_REQUIRED in result.rejection_reasons
    assert result.publish_result is None


def test_unaccepted_queue_verifier_rejects_before_runner() -> None:
    runner = FakeDraftPrRunner()
    result = _invoke(
        queue_verifier=_queue_verifier_result(
            decision=QUEUE_AUTHORIZED_SLICE_VERIFIER_INVOKE_REJECT
        ),
        runner=runner,
    )

    assert result.decision == QUEUE_AUTHORIZED_VERIFIED_DRAFT_PR_PUBLISH_INVOKE_REJECT
    assert (
        QueueAuthorizedVerifiedDraftPrPublishInvokeReason.SLICE_VERIFIER_NOT_ACCEPTED
        in result.rejection_reasons
    )
    assert runner.calls == []


def test_unaccepted_verifier_payload_rejects_before_runner() -> None:
    runner = FakeDraftPrRunner()
    result = _invoke(
        queue_verifier=_queue_verifier_result(verifier_decision=AUTONOMOUS_SLICE_VERIFIER_REJECT),
        runner=runner,
    )

    assert result.decision == QUEUE_AUTHORIZED_VERIFIED_DRAFT_PR_PUBLISH_INVOKE_REJECT
    assert (
        QueueAuthorizedVerifiedDraftPrPublishInvokeReason.VERIFIER_PAYLOAD_NOT_ACCEPTED
        in result.rejection_reasons
    )
    assert runner.calls == []


def test_work_order_id_mismatch_rejects_before_runner() -> None:
    request = _publish_request()
    request["work_order_id"] = "other-work-order"
    runner = FakeDraftPrRunner()

    result = _invoke(publish_request=request, runner=runner)

    assert result.decision == QUEUE_AUTHORIZED_VERIFIED_DRAFT_PR_PUBLISH_INVOKE_REJECT
    assert (
        QueueAuthorizedVerifiedDraftPrPublishInvokeReason.WORK_ORDER_ID_MISMATCH
        in result.rejection_reasons
    )
    assert runner.calls == []


def test_publish_rejection_is_preserved_without_pr_creation() -> None:
    request = _publish_request()
    request["pre_publish_branch_head_sha"] = "b" * 40
    runner = FakeDraftPrRunner()

    result = _invoke(publish_request=request, runner=runner)

    assert result.decision == QUEUE_AUTHORIZED_VERIFIED_DRAFT_PR_PUBLISH_INVOKE_REJECT
    assert (
        QueueAuthorizedVerifiedDraftPrPublishInvokeReason.PUBLISH_NOT_ACCEPTED
        in result.rejection_reasons
    )
    assert "FAIL_HEAD_MISMATCH" in result.rejection_reasons
    assert result.publish_result is not None
    assert result.publish_result.decision == VERIFIED_DRAFT_PR_PUBLISH_REJECT
    assert runner.calls == []


def test_push_failure_is_preserved() -> None:
    runner = FakeDraftPrRunner(push_ok=False)

    result = _invoke(runner=runner)

    assert result.decision == QUEUE_AUTHORIZED_VERIFIED_DRAFT_PR_PUBLISH_INVOKE_REJECT
    assert (
        QueueAuthorizedVerifiedDraftPrPublishInvokeReason.PUBLISH_NOT_ACCEPTED
        in result.rejection_reasons
    )
    assert "FAIL_PUSH_BRANCH" in result.rejection_reasons
    assert [call[0] for call in runner.calls] == ["push_branch"]


def test_result_is_json_serializable() -> None:
    result = _invoke()

    payload = result.to_dict()
    assert payload["decision"] == QUEUE_AUTHORIZED_VERIFIED_DRAFT_PR_PUBLISH_INVOKE_ACCEPT
    assert payload["publish_result"]["decision"] == VERIFIED_DRAFT_PR_PUBLISH_ACCEPT
    json.dumps(payload)


def test_module_has_no_direct_shell_git_gh_merge_memory_reward_or_holoindex_authority() -> None:
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
        "gh pr",
        "mark_ready",
        "merge_pr",
        "PatternMemory(",
        "store_outcome",
        "settle_reward",
        "holo_index.py --index",
    )
    for token in forbidden_tokens:
        assert token not in source
