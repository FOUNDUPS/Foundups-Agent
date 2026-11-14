"""Tests for REDDOG_RESIDENT_QUEUE_EXACT_SHA_COMMIT_STAGE_PHASE1."""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

from modules.communication.moltbot_bridge.src.reddog_resident_queue_exact_sha_commit_handler import (
    EFFECT_COMMITTED,
    EFFECT_INDETERMINATE,
    EFFECT_NOT_COMMITTED,
    EXACT_SHA_COMMIT_STAGE_KEY,
    FAIL_BASE_SHA_MISMATCH,
    FAIL_BASE_SHA_MISSING,
    FAIL_BRANCH_BINDING_MISMATCH,
    FAIL_COMMIT_OPERATION,
    FAIL_COMMIT_STATE_INDETERMINATE,
    FAIL_DIRTY_PATH_SET_MISMATCH,
    FAIL_INDEX_NOT_CLEAN,
    FAIL_WRITTEN_ARTIFACT_DIGEST_MISMATCH,
    FAIL_WORK_ORDER_DIGEST_MISMATCH,
    build_reddog_resident_queue_exact_sha_commit_stage_handler,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_next_stage_dispatch import (
    ResidentQueueStageDispatchRequest,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_orchestration_plan import (
    NEXT_QUEUE_EXACT_SHA_COMMIT,
    RESIDENT_QUEUE_EXACT_SHA_COMMIT_ACCEPT,
    RESIDENT_QUEUE_EXACT_SHA_COMMIT_REJECT,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_bounded_worker_pilot_invoke import (
    QUEUE_AUTHORIZED_BOUNDED_WORKER_PILOT_INVOKE_ACCEPT,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_worktree_create_invoke import (
    QUEUE_AUTHORIZED_WORKTREE_CREATE_INVOKE_ACCEPT,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_binding import (
    canonical_full_work_order_digest,
)
from modules.infrastructure.wre_core.src.wre_independent_evidence_producer_runtime import (
    CommandResult,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "reddog_resident_queue_exact_sha_commit_handler.py"
)
WORK_ORDER_ID = "wo-exact-sha-commit-1"
QUEUE_ITEM_ID = "queue-exact-sha-commit-1"
SLICE = "REDDOG_RESIDENT_QUEUE_EXACT_SHA_COMMIT_STAGE_PHASE1"
BRANCH = "feat/reddog-exact-sha-commit"
BASE_SHA = "b" * 40
HEAD_SHA = "a" * 40
TREE_SHA = "c" * 40
ARTIFACT = "modules/communication/moltbot_bridge/tests/fixtures/exact_sha/README.md"


def _digest(value: object) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=str,
    )
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _artifact_digest(worktree: Path) -> str:
    content = (worktree / ARTIFACT).read_text(encoding="utf-8")
    return _digest({"written": {ARTIFACT: _digest(content)}})


class _Store:
    def __init__(self, state: dict[str, object]) -> None:
        self.state = state

    def load(self):
        return self.state


class _Resolver:
    def __init__(self, work_order: dict[str, object]) -> None:
        self.work_order = work_order

    def resolve(self, *, work_order_id, queue_item_id, selected_slice):
        assert work_order_id == WORK_ORDER_ID
        assert queue_item_id == QUEUE_ITEM_ID
        assert selected_slice == SLICE
        return self.work_order


class _EvidenceRunner:
    def __init__(
        self,
        *,
        head: str = BASE_SHA,
        branch: str = BRANCH,
        unstaged: tuple[str, ...] = (ARTIFACT,),
        staged: tuple[str, ...] = (),
        untracked: tuple[str, ...] = (),
        committed: tuple[str, ...] = (ARTIFACT,),
        parent: str = BASE_SHA,
    ) -> None:
        self.head = head
        self.branch = branch
        self.unstaged = unstaged
        self.staged = staged
        self.untracked = untracked
        self.committed = committed
        self.parent = parent
        self.commit_message = ""
        self.calls: list[tuple[str, ...]] = []

    def run(self, argv, *, cwd, timeout_s):
        args = tuple(argv)
        self.calls.append(args)
        if args == ("git", "symbolic-ref", "--short", "HEAD"):
            return CommandResult(0, self.branch)
        if args == ("git", "rev-parse", "HEAD"):
            return CommandResult(0, self.head)
        if args == ("git", "rev-parse", f"{self.head}^"):
            return CommandResult(0, self.parent)
        if args == ("git", "diff", "--cached", "--name-only"):
            return CommandResult(0, "\n".join(self.staged))
        if args == ("git", "diff", "--name-only"):
            return CommandResult(0, "\n".join(self.unstaged))
        if args == ("git", "ls-files", "--others", "--exclude-standard"):
            return CommandResult(0, "\n".join(self.untracked))
        if args[:4] == ("git", "rev-list", "--parents", "-n"):
            return CommandResult(0, f"{self.head} {self.parent}")
        if args[:4] == ("git", "log", "-1", "--format=%B"):
            return CommandResult(0, self.commit_message)
        if args[:3] == ("git", "diff", "--name-only") and len(args) == 6:
            return CommandResult(0, "\n".join(self.committed))
        if args == ("git", "rev-parse", f"{self.head}^{{tree}}"):
            return CommandResult(0, TREE_SHA)
        raise AssertionError(f"unexpected command: {args}")


class _CommitRunner:
    def __init__(
        self,
        evidence: _EvidenceRunner,
        *,
        ok: bool = True,
        move_head_on_failure: bool = False,
    ) -> None:
        self.evidence = evidence
        self.ok = ok
        self.move_head_on_failure = move_head_on_failure
        self.calls: list[dict[str, object]] = []

    def commit_all(self, *, worktree_path, add_paths, message):
        self.calls.append(
            {
                "worktree_path": Path(worktree_path),
                "add_paths": tuple(add_paths),
                "message": message,
            }
        )
        if self.ok or self.move_head_on_failure:
            self.evidence.head = HEAD_SHA
            self.evidence.parent = BASE_SHA
            self.evidence.commit_message = message
            self.evidence.unstaged = ()
            self.evidence.staged = ()
            self.evidence.untracked = ()
        return {
            "ok": self.ok,
            "returncode": 0 if self.ok else 1,
            "stdout": "",
            "stderr": "",
        }


def _work_order(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "work_order_id": WORK_ORDER_ID,
        "branch_name": BRANCH,
        "task_summary": "feat(reddog): commit bounded exact-SHA slice",
        "slice_verifier_plan": {
            "slice_name": SLICE,
            "base_sha": BASE_SHA,
            "required_checks": [{"name": "pytest"}],
        },
    }
    payload.update(overrides)
    return payload


def _chain_state(
    worktree: Path,
    work_order: dict[str, object],
) -> dict[str, object]:
    pilot_receipt = {
        "receipt_id": "bounded_wt_pilot_exact_sha",
        "work_order_id": WORK_ORDER_ID,
        "worktree_path": str(worktree),
        "written_artifacts": [ARTIFACT],
        "written_artifact_digest": _artifact_digest(worktree),
    }
    return {
        "schema_version": "reddog_resident_queue_chain_results.v1",
        "chain_revision": 11,
        "stage_results": {
            "executor_plan": {
                "decision": "QUEUE_AUTHORIZED_EXECUTOR_PLAN_DRYRUN_ACCEPT",
                "executor_plan_result": {
                    "plan": {
                        "work_order_digest": canonical_full_work_order_digest(
                            work_order
                        ),
                    },
                },
            },
            "worktree_create": {
                "decision": QUEUE_AUTHORIZED_WORKTREE_CREATE_INVOKE_ACCEPT,
                "worktree_create_result": {
                    "decision": "WORKTREE_CREATE_ACCEPT",
                    "work_order_id": WORK_ORDER_ID,
                    "branch_name": BRANCH,
                    "worktree_path": str(worktree),
                    "result_digest": _digest({"worktree": str(worktree)}),
                },
            },
            "bounded_worker_pilot": {
                "decision": QUEUE_AUTHORIZED_BOUNDED_WORKER_PILOT_INVOKE_ACCEPT,
                "pilot_result": {
                    "accepted": True,
                    "receipt": pilot_receipt,
                },
            },
        },
    }


def _request() -> ResidentQueueStageDispatchRequest:
    return ResidentQueueStageDispatchRequest(
        stage_key=EXACT_SHA_COMMIT_STAGE_KEY,
        next_action=NEXT_QUEUE_EXACT_SHA_COMMIT,
        queue_item_id=QUEUE_ITEM_ID,
        selected_slice=SLICE,
        plan_id="plan-exact-sha-commit",
        accepted_stages=("bounded_worker_pilot",),
    )


def _setup(
    tmp_path: Path,
    *,
    evidence: _EvidenceRunner | None = None,
    work_order: dict[str, object] | None = None,
):
    repo_root = tmp_path / "shared-repo"
    worktree = tmp_path / "isolated-worktree"
    repo_root.mkdir(parents=True)
    target = worktree / ARTIFACT
    target.parent.mkdir(parents=True)
    target.write_text("bounded change\n", encoding="utf-8")
    evidence = evidence or _EvidenceRunner()
    commit = _CommitRunner(evidence)
    resolved_work_order = work_order or _work_order()
    handler = build_reddog_resident_queue_exact_sha_commit_stage_handler(
        chain_results_store=_Store(
            _chain_state(worktree, resolved_work_order)
        ),
        work_order_resolver=_Resolver(resolved_work_order),
        commit_runner=commit,
        evidence_command_runner=evidence,
        repo_root=repo_root,
    )
    return handler, commit, evidence, worktree


def test_commits_only_bounded_paths_and_emits_exact_sha_receipt(tmp_path: Path) -> None:
    handler, commit, _evidence, worktree = _setup(tmp_path)

    result = handler(_request())

    assert result["accepted"] is True
    assert result["decision"] == RESIDENT_QUEUE_EXACT_SHA_COMMIT_ACCEPT
    assert result["effect_commit_state"] == EFFECT_COMMITTED
    assert result["reconciliation_required"] is False
    assert len(commit.calls) == 1
    assert commit.calls[0]["worktree_path"] == worktree
    assert commit.calls[0]["add_paths"] == (ARTIFACT,)
    assert str(commit.calls[0]["message"]).startswith(
        "feat(reddog): commit bounded exact-SHA slice\n\n"
        "RedDog-Commit-Attempt: sha256:"
    )
    receipt = result["commit_receipt"]
    assert receipt["base_sha"] == BASE_SHA
    assert receipt["parent_sha"] == BASE_SHA
    assert receipt["head_sha"] == HEAD_SHA
    assert receipt["tree_sha"] == TREE_SHA
    assert receipt["changed_paths"] == (ARTIFACT,)
    assert receipt["reconciled_existing_commit"] is False
    assert receipt["main_checkout_untouched"] is True
    assert receipt["no_push_performed"] is True
    assert receipt["no_pr_created"] is True
    assert receipt["no_merge_performed"] is True
    assert receipt["receipt_id"].startswith("sha256:")


def test_extra_dirty_path_rejects_before_commit(tmp_path: Path) -> None:
    evidence = _EvidenceRunner(unstaged=(ARTIFACT, "outside.py"))
    handler, commit, _evidence, _worktree = _setup(tmp_path, evidence=evidence)

    result = handler(_request())

    assert result["decision"] == RESIDENT_QUEUE_EXACT_SHA_COMMIT_REJECT
    assert FAIL_DIRTY_PATH_SET_MISMATCH in result["rejection_reasons"]
    assert commit.calls == []


def test_prestaged_index_rejects_before_commit(tmp_path: Path) -> None:
    evidence = _EvidenceRunner(unstaged=(), staged=(ARTIFACT,))
    handler, commit, _evidence, _worktree = _setup(tmp_path, evidence=evidence)

    result = handler(_request())

    assert FAIL_INDEX_NOT_CLEAN in result["rejection_reasons"]
    assert commit.calls == []


def test_wrong_base_or_branch_rejects_before_commit(tmp_path: Path) -> None:
    wrong_base = _EvidenceRunner(head="d" * 40)
    handler, commit, _evidence, _worktree = _setup(tmp_path, evidence=wrong_base)
    result = handler(_request())
    assert FAIL_BASE_SHA_MISMATCH in result["rejection_reasons"]
    assert commit.calls == []

    other = tmp_path / "branch"
    wrong_branch = _EvidenceRunner(branch="feat/other")
    handler, commit, _evidence, _worktree = _setup(other, evidence=wrong_branch)
    result = handler(_request())
    assert FAIL_BRANCH_BINDING_MISMATCH in result["rejection_reasons"]
    assert commit.calls == []


def test_changed_artifact_after_pilot_rejects(tmp_path: Path) -> None:
    handler, commit, _evidence, worktree = _setup(tmp_path)
    (worktree / ARTIFACT).write_text("tampered\n", encoding="utf-8")

    result = handler(_request())

    assert FAIL_WRITTEN_ARTIFACT_DIGEST_MISMATCH in result["rejection_reasons"]
    assert commit.calls == []


def test_commit_failure_without_head_move_is_not_committed(tmp_path: Path) -> None:
    handler, _commit, evidence, _worktree = _setup(tmp_path)
    failing = _CommitRunner(evidence, ok=False)
    object.__setattr__(handler, "commit_runner", failing)

    result = handler(_request())

    assert FAIL_COMMIT_OPERATION in result["rejection_reasons"]
    assert result["effect_commit_state"] == EFFECT_NOT_COMMITTED
    assert result["reconciliation_required"] is False


def test_commit_failure_with_head_move_is_indeterminate(tmp_path: Path) -> None:
    handler, _commit, evidence, _worktree = _setup(tmp_path)
    failing = _CommitRunner(evidence, ok=False, move_head_on_failure=True)
    object.__setattr__(handler, "commit_runner", failing)

    result = handler(_request())

    assert FAIL_COMMIT_STATE_INDETERMINATE in result["rejection_reasons"]
    assert result["effect_commit_state"] == EFFECT_INDETERMINATE
    assert result["reconciliation_required"] is True


def test_retry_reconciles_existing_exact_commit_without_second_commit(tmp_path: Path) -> None:
    handler, first_commit, evidence, worktree = _setup(tmp_path)
    first = handler(_request())
    assert first["accepted"] is True
    retry_commit = _CommitRunner(evidence)
    retry_handler = build_reddog_resident_queue_exact_sha_commit_stage_handler(
        chain_results_store=handler.chain_results_store,
        work_order_resolver=handler.work_order_resolver,
        commit_runner=retry_commit,
        evidence_command_runner=evidence,
        repo_root=handler.repo_root,
    )

    result = retry_handler(_request())

    assert result["accepted"] is True
    assert result["commit_runner_invoked"] is False
    assert result["commit_receipt"]["reconciled_existing_commit"] is True
    assert result["commit_receipt"]["head_sha"] == HEAD_SHA
    assert len(first_commit.calls) == 1
    assert retry_commit.calls == []


def test_missing_planned_base_rejects_before_commit(tmp_path: Path) -> None:
    plan = dict(_work_order()["slice_verifier_plan"])
    plan.pop("base_sha")
    handler, first_commit, evidence, _worktree = _setup(
        tmp_path,
        work_order=_work_order(slice_verifier_plan=plan),
    )

    result = handler(_request())

    assert result["accepted"] is False
    assert FAIL_BASE_SHA_MISSING in result["rejection_reasons"]
    assert first_commit.calls == []
    assert evidence.head == BASE_SHA


def test_changed_work_order_rejects_against_executor_digest(tmp_path: Path) -> None:
    handler, commit, _evidence, _worktree = _setup(tmp_path)
    handler.work_order_resolver.work_order["required_tests"] = ["different"]

    result = handler(_request())

    assert result["accepted"] is False
    assert FAIL_WORK_ORDER_DIGEST_MISMATCH in result["rejection_reasons"]
    assert commit.calls == []


def test_module_uses_injected_runners_and_has_no_push_pr_or_merge_calls() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    banned_import_roots = {"subprocess", "git", "requests", "urllib", "socket"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".", 1)[0] not in banned_import_roots
        if isinstance(node, ast.ImportFrom) and node.module:
            assert node.module.split(".", 1)[0] not in banned_import_roots

    assert ".push_branch(" not in source
    assert ".create_draft_pr(" not in source
    assert "gh pr" not in source
    assert "git merge" not in source
