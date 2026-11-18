"""Resident queue exact-SHA commit stage.

Slice: REDDOG_RESIDENT_QUEUE_EXACT_SHA_COMMIT_STAGE_PHASE1

This handler connects the bounded worker's declared artifact receipt to the
existing injected ``commit_all`` Git runner. It validates live worktree state
before and after the commit and emits the exact base/head pair required by the
independent verifier. It never pushes, publishes or merges.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Optional, Protocol, Sequence

from modules.communication.moltbot_bridge.src.reddog_resident_queue_chain_results_store import (
    ResidentQueueChainResultsStore,
)
from modules.communication.moltbot_bridge.src.reddog_exact_sha_commit_receipt import (
    EXACT_SHA_COMMIT_RECEIPT_SCHEMA,
    validate_exact_sha_commit_receipt,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_next_stage_dispatch import (
    ResidentQueueStageDispatchRequest,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_orchestration_plan import (
    NEXT_QUEUE_EXACT_SHA_COMMIT,
    RESIDENT_QUEUE_EXACT_SHA_COMMIT_ACCEPT,
    RESIDENT_QUEUE_EXACT_SHA_COMMIT_REJECT,
)
from modules.communication.moltbot_bridge.src.reddog_wre_cwd_guard import (
    validate_wre_worker_operation_cwd,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_binding import (
    canonical_full_work_order_digest,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_bounded_worker_pilot_invoke import (
    QUEUE_AUTHORIZED_BOUNDED_WORKER_PILOT_INVOKE_ACCEPT,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_worktree_create_invoke import (
    QUEUE_AUTHORIZED_WORKTREE_CREATE_INVOKE_ACCEPT,
)


EXACT_SHA_COMMIT_STAGE_KEY = "exact_sha_commit"
BOUNDED_WORKER_PILOT_STAGE_KEY = "bounded_worker_pilot"
WORKTREE_CREATE_STAGE_KEY = "worktree_create"
EXECUTOR_PLAN_STAGE_KEY = "executor_plan"
FAIL_DISPATCH_STAGE_MISMATCH = "FAIL_DISPATCH_STAGE_MISMATCH"
FAIL_DISPATCH_NEXT_ACTION_MISMATCH = "FAIL_DISPATCH_NEXT_ACTION_MISMATCH"
FAIL_WORKTREE_CREATE_STAGE_MISSING = "FAIL_WORKTREE_CREATE_STAGE_MISSING"
FAIL_WORKTREE_CREATE_STAGE_REJECTED = "FAIL_WORKTREE_CREATE_STAGE_REJECTED"
FAIL_BOUNDED_WORKER_PILOT_MISSING = "FAIL_BOUNDED_WORKER_PILOT_MISSING"
FAIL_BOUNDED_WORKER_PILOT_REJECTED = "FAIL_BOUNDED_WORKER_PILOT_REJECTED"
FAIL_EXECUTOR_PLAN_MISSING = "FAIL_EXECUTOR_PLAN_MISSING"
FAIL_WORK_ORDER_DIGEST_MISMATCH = "FAIL_WORK_ORDER_DIGEST_MISMATCH"
FAIL_WORK_ORDER_ID_MISSING = "FAIL_WORK_ORDER_ID_MISSING"
FAIL_WORK_ORDER_MISSING = "FAIL_WORK_ORDER_MISSING"
FAIL_COMMIT_RUNNER_MISSING = "FAIL_COMMIT_RUNNER_MISSING"
FAIL_EVIDENCE_RUNNER_MISSING = "FAIL_EVIDENCE_RUNNER_MISSING"
FAIL_CWD_GUARD = "FAIL_CWD_GUARD"
FAIL_WORKTREE_BINDING_MISMATCH = "FAIL_WORKTREE_BINDING_MISMATCH"
FAIL_BRANCH_BINDING_MISMATCH = "FAIL_BRANCH_BINDING_MISMATCH"
FAIL_PROTECTED_BRANCH = "FAIL_PROTECTED_BRANCH"
FAIL_BASE_SHA_MISSING = "FAIL_BASE_SHA_MISSING"
FAIL_BASE_SHA_INVALID = "FAIL_BASE_SHA_INVALID"
FAIL_BASE_SHA_MISMATCH = "FAIL_BASE_SHA_MISMATCH"
FAIL_COMMIT_MESSAGE_INVALID = "FAIL_COMMIT_MESSAGE_INVALID"
FAIL_WRITTEN_ARTIFACTS_INVALID = "FAIL_WRITTEN_ARTIFACTS_INVALID"
FAIL_WRITTEN_ARTIFACT_DIGEST_MISMATCH = "FAIL_WRITTEN_ARTIFACT_DIGEST_MISMATCH"
FAIL_ARTIFACT_PATH_ESCAPE = "FAIL_ARTIFACT_PATH_ESCAPE"
FAIL_ARTIFACT_SYMLINK = "FAIL_ARTIFACT_SYMLINK"
FAIL_GIT_STATE_READ = "FAIL_GIT_STATE_READ"
FAIL_INDEX_NOT_CLEAN = "FAIL_INDEX_NOT_CLEAN"
FAIL_DIRTY_PATH_SET_MISMATCH = "FAIL_DIRTY_PATH_SET_MISMATCH"
FAIL_EMPTY_CHANGESET = "FAIL_EMPTY_CHANGESET"
FAIL_COMMIT_OPERATION = "FAIL_COMMIT_OPERATION"
FAIL_COMMIT_STATE_INDETERMINATE = "FAIL_COMMIT_STATE_INDETERMINATE"
FAIL_HEAD_SHA_INVALID = "FAIL_HEAD_SHA_INVALID"
FAIL_HEAD_SHA_UNCHANGED = "FAIL_HEAD_SHA_UNCHANGED"
FAIL_COMMIT_PARENT_MISMATCH = "FAIL_COMMIT_PARENT_MISMATCH"

EFFECT_NOT_ATTEMPTED = "NOT_ATTEMPTED"
EFFECT_COMMITTED = "COMMITTED"
EFFECT_NOT_COMMITTED = "NOT_COMMITTED"
EFFECT_INDETERMINATE = "INDETERMINATE"

_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_PROTECTED_BRANCHES = frozenset({"main", "master"})
_READ_TIMEOUT_S = 30


class ResidentQueueCommitWorkOrderResolver(Protocol):
    def resolve(
        self,
        *,
        work_order_id: str,
        queue_item_id: Optional[str],
        selected_slice: Optional[str],
    ) -> Mapping[str, Any]:
        """Return the signed work order bound to the queue item."""


@dataclass(frozen=True)
class ExactShaCommitReceipt:
    schema_version: str
    receipt_id: str
    work_order_id: str
    queue_item_id: str
    selected_slice: str
    base_sha: str
    head_sha: str
    parent_sha: str
    tree_sha: str
    branch_name: str
    worktree_path: str
    changed_paths: tuple[str, ...]
    bounded_worker_receipt_id: str
    bounded_worker_receipt_digest: str
    worktree_create_result_digest: str
    commit_message_digest: str
    work_order_digest: str
    commit_attempt_key: str
    chain_state_digest: str
    effect_commit_state: str = EFFECT_COMMITTED
    reconciliation_required: bool = False
    reconciled_existing_commit: bool = False
    main_checkout_untouched: bool = True
    no_push_performed: bool = True
    no_pr_created: bool = True
    no_merge_performed: bool = True
    no_holoindex_reindex_performed: bool = True
    no_pattern_memory_write_performed: bool = True
    no_reward_settlement_performed: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ResidentQueueExactShaCommitResult:
    decision: str
    accepted: bool
    rejection_reasons: list[str] = field(default_factory=list)
    commit_receipt: Optional[ExactShaCommitReceipt] = None
    effect_commit_state: str = EFFECT_NOT_ATTEMPTED
    reconciliation_required: bool = False
    commit_runner_invoked: bool = False
    no_push_performed: bool = True
    no_pr_created: bool = True
    no_merge_performed: bool = True
    no_holoindex_reindex_performed: bool = True
    no_pattern_memory_write_performed: bool = True
    no_reward_settlement_performed: bool = True

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["commit_receipt"] = (
            self.commit_receipt.to_dict() if self.commit_receipt else None
        )
        return payload


def _mapping(value: Any) -> Mapping[str, Any]:
    if hasattr(value, "to_dict"):
        candidate = value.to_dict()
        return candidate if isinstance(candidate, Mapping) else {}
    return value if isinstance(value, Mapping) else {}


def _stage_results(state: Mapping[str, Any]) -> Mapping[str, Mapping[str, Any]]:
    raw = (
        state.get("stage_results")
        if state.get("schema_version") == "reddog_resident_queue_chain_results.v1"
        else state
    )
    if not isinstance(raw, Mapping):
        return {}
    return {
        str(key): value for key, value in raw.items() if isinstance(value, Mapping)
    }


def _canonical_digest(value: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        dict(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("ascii")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _text_digest(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _artifact_digest(
    paths: Sequence[str],
    *,
    worktree_path: Path,
) -> str:
    written: dict[str, str] = {}
    for rel in paths:
        content = (worktree_path / rel).read_text(encoding="utf-8")
        encoded = json.dumps(
            content,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            default=str,
        ).encode("utf-8")
        written[rel] = "sha256:" + hashlib.sha256(encoded).hexdigest()
    return _canonical_digest({"written": written})


def _reject(
    *reasons: str,
    effect_commit_state: str = EFFECT_NOT_ATTEMPTED,
    reconciliation_required: bool = False,
    commit_runner_invoked: bool = False,
) -> ResidentQueueExactShaCommitResult:
    return ResidentQueueExactShaCommitResult(
        decision=RESIDENT_QUEUE_EXACT_SHA_COMMIT_REJECT,
        accepted=False,
        rejection_reasons=list(
            dict.fromkeys(reason for reason in reasons if str(reason).strip())
        ),
        effect_commit_state=effect_commit_state,
        reconciliation_required=reconciliation_required,
        commit_runner_invoked=commit_runner_invoked,
    )


def _command_result(value: Any) -> tuple[int, str, str, bool, bool, bool]:
    data = _mapping(value)
    if not data and value is not None:
        data = {
            "returncode": getattr(value, "returncode", -1),
            "stdout": getattr(value, "stdout", ""),
            "stderr": getattr(value, "stderr", ""),
            "timed_out": getattr(value, "timed_out", False),
            "stdout_truncated": getattr(value, "stdout_truncated", False),
            "stderr_truncated": getattr(value, "stderr_truncated", False),
        }
    return (
        int(data.get("returncode", -1)),
        str(data.get("stdout") or ""),
        str(data.get("stderr") or ""),
        data.get("timed_out") is True,
        data.get("stdout_truncated") is True,
        data.get("stderr_truncated") is True,
    )


def _read_git(
    runner: Any,
    *,
    worktree_path: Path,
    argv: Sequence[str],
) -> tuple[bool, str]:
    try:
        raw = runner.run(list(argv), cwd=worktree_path, timeout_s=_READ_TIMEOUT_S)
    except Exception:
        return False, ""
    returncode, stdout, _stderr, timed_out, stdout_truncated, stderr_truncated = (
        _command_result(raw)
    )
    if (
        returncode != 0
        or timed_out
        or stdout_truncated
        or stderr_truncated
    ):
        return False, ""
    return True, stdout.strip()


def _path_lines(stdout: str) -> tuple[str, ...]:
    values: list[str] = []
    for raw in stdout.splitlines():
        text = raw.strip().replace("\\", "/")
        if text:
            values.append(text)
    return tuple(dict.fromkeys(values))


def _validated_artifact_paths(
    raw_paths: Any,
    *,
    worktree_path: Path,
) -> tuple[tuple[str, ...], Optional[str]]:
    if not isinstance(raw_paths, (list, tuple)) or not raw_paths:
        return (), FAIL_WRITTEN_ARTIFACTS_INVALID
    normalized: list[str] = []
    worktree_resolved = worktree_path.resolve()
    for raw in raw_paths:
        text = str(raw or "").strip().replace("\\", "/")
        pure = PurePosixPath(text)
        if (
            not text
            or pure.is_absolute()
            or text.startswith("/")
            or any(part in ("", ".", "..", ".git") for part in pure.parts)
            or any(ord(ch) < 32 for ch in text)
        ):
            return (), FAIL_WRITTEN_ARTIFACTS_INVALID
        candidate = worktree_path.joinpath(*pure.parts)
        try:
            candidate_resolved = candidate.resolve()
            candidate_resolved.relative_to(worktree_resolved)
        except (OSError, ValueError):
            return (), FAIL_ARTIFACT_PATH_ESCAPE
        current = candidate
        while current != worktree_path:
            if current.is_symlink():
                return (), FAIL_ARTIFACT_SYMLINK
            current = current.parent
        normalized.append(pure.as_posix())
    if len(set(normalized)) != len(normalized):
        return (), FAIL_WRITTEN_ARTIFACTS_INVALID
    return tuple(sorted(normalized)), None


def _verify_existing_commit(
    *,
    runner: Any,
    worktree_path: Path,
    base_sha: str,
    head_sha: str,
    expected_paths: Sequence[str],
    expected_attempt_key: str,
) -> tuple[bool, str]:
    if not _SHA_RE.fullmatch(head_sha) or head_sha == base_sha:
        return False, ""
    ok, parent_line = _read_git(
        runner,
        worktree_path=worktree_path,
        argv=("git", "rev-list", "--parents", "-n", "1", head_sha),
    )
    if not ok or parent_line.split() != [head_sha, base_sha]:
        return False, ""
    ok, commit_message = _read_git(
        runner,
        worktree_path=worktree_path,
        argv=("git", "log", "-1", "--format=%B", head_sha),
    )
    if (
        not ok
        or f"RedDog-Commit-Attempt: {expected_attempt_key}"
        not in commit_message.splitlines()
    ):
        return False, ""
    ok, committed_output = _read_git(
        runner,
        worktree_path=worktree_path,
        argv=("git", "diff", "--name-only", base_sha, head_sha, "--"),
    )
    if not ok or set(_path_lines(committed_output)) != set(expected_paths):
        return False, ""
    for argv in (
        ("git", "diff", "--name-only"),
        ("git", "diff", "--cached", "--name-only"),
        ("git", "ls-files", "--others", "--exclude-standard"),
    ):
        ok, output = _read_git(
            runner,
            worktree_path=worktree_path,
            argv=argv,
        )
        if not ok or _path_lines(output):
            return False, ""
    ok, tree_sha = _read_git(
        runner,
        worktree_path=worktree_path,
        argv=("git", "rev-parse", f"{head_sha}^{{tree}}"),
    )
    if not ok or not _SHA_RE.fullmatch(tree_sha.lower()):
        return False, ""
    return True, tree_sha.lower()


def _commit_attempt_key(
    *,
    work_order: Mapping[str, Any],
    base_sha: str,
    branch_name: str,
    worktree_path: Path,
    expected_paths: Sequence[str],
    pilot_receipt: Mapping[str, Any],
) -> str:
    return _canonical_digest(
        {
            "work_order_digest": canonical_full_work_order_digest(work_order),
            "base_sha": base_sha,
            "branch_name": branch_name,
            "worktree_path": str(worktree_path.resolve()),
            "changed_paths": tuple(expected_paths),
            "bounded_worker_receipt_id": str(
                pilot_receipt.get("receipt_id") or ""
            ),
        }
    )


def _build_receipt(
    *,
    work_order_id: str,
    request: ResidentQueueStageDispatchRequest,
    base_sha: str,
    head_sha: str,
    tree_sha: str,
    branch_name: str,
    worktree_path: Path,
    expected_paths: Sequence[str],
    pilot_receipt: Mapping[str, Any],
    worktree_result: Mapping[str, Any],
    message: str,
    work_order: Mapping[str, Any],
    chain_state: Mapping[str, Any],
    reconciled_existing_commit: bool,
    commit_attempt_key: str,
) -> ExactShaCommitReceipt:
    work_order_digest = canonical_full_work_order_digest(work_order)
    payload = {
        "schema_version": EXACT_SHA_COMMIT_RECEIPT_SCHEMA,
        "work_order_id": work_order_id,
        "queue_item_id": str(request.queue_item_id or ""),
        "selected_slice": str(request.selected_slice or ""),
        "base_sha": base_sha,
        "head_sha": head_sha,
        "parent_sha": base_sha,
        "tree_sha": tree_sha,
        "branch_name": branch_name,
        "worktree_path": str(worktree_path.resolve()),
        "changed_paths": tuple(expected_paths),
        "bounded_worker_receipt_id": str(pilot_receipt.get("receipt_id") or ""),
        "bounded_worker_receipt_digest": _canonical_digest(pilot_receipt),
        "worktree_create_result_digest": _canonical_digest(worktree_result),
        "commit_message_digest": _text_digest(message),
        "work_order_digest": work_order_digest,
        "commit_attempt_key": commit_attempt_key,
        "chain_state_digest": _canonical_digest(chain_state),
        "effect_commit_state": EFFECT_COMMITTED,
        "reconciliation_required": False,
        "reconciled_existing_commit": reconciled_existing_commit,
        "main_checkout_untouched": True,
        "no_push_performed": True,
        "no_pr_created": True,
        "no_merge_performed": True,
        "no_holoindex_reindex_performed": True,
        "no_pattern_memory_write_performed": True,
        "no_reward_settlement_performed": True,
    }
    return ExactShaCommitReceipt(
        receipt_id=_canonical_digest(payload),
        **payload,
    )


def _commit_message(work_order: Mapping[str, Any], selected_slice: Optional[str]) -> str:
    value = str(work_order.get("task_summary") or "").strip()
    if not value and selected_slice:
        value = f"RedDog bounded slice: {selected_slice}"
    if (
        not value
        or len(value) > 200
        or "\n" in value
        or "\r" in value
        or any(ord(ch) < 32 and ch != "\t" for ch in value)
    ):
        return ""
    return value


@dataclass(frozen=True)
class ResidentQueueExactShaCommitStageHandler:
    chain_results_store: ResidentQueueChainResultsStore
    work_order_resolver: ResidentQueueCommitWorkOrderResolver
    commit_runner: Any
    evidence_command_runner: Any
    repo_root: Path

    def __call__(
        self, request: ResidentQueueStageDispatchRequest
    ) -> Mapping[str, Any]:
        if request.stage_key != EXACT_SHA_COMMIT_STAGE_KEY:
            return _reject(
                FAIL_DISPATCH_STAGE_MISMATCH,
                f"expected:{EXACT_SHA_COMMIT_STAGE_KEY}",
                f"actual:{request.stage_key}",
            ).to_dict()
        if request.next_action != NEXT_QUEUE_EXACT_SHA_COMMIT:
            return _reject(
                FAIL_DISPATCH_NEXT_ACTION_MISMATCH,
                f"expected:{NEXT_QUEUE_EXACT_SHA_COMMIT}",
                f"actual:{request.next_action}",
            ).to_dict()
        if self.commit_runner is None or not callable(
            getattr(self.commit_runner, "commit_all", None)
        ):
            return _reject(FAIL_COMMIT_RUNNER_MISSING).to_dict()
        if self.evidence_command_runner is None or not callable(
            getattr(self.evidence_command_runner, "run", None)
        ):
            return _reject(FAIL_EVIDENCE_RUNNER_MISSING).to_dict()

        chain_state = _mapping(self.chain_results_store.load())
        stages = _stage_results(chain_state)
        executor_stage = _mapping(stages.get(EXECUTOR_PLAN_STAGE_KEY))
        executor_result = _mapping(executor_stage.get("executor_plan_result"))
        executor_plan = _mapping(executor_result.get("plan"))
        if (
            executor_stage.get("decision")
            != "QUEUE_AUTHORIZED_EXECUTOR_PLAN_DRYRUN_ACCEPT"
            or not executor_plan
        ):
            return _reject(FAIL_EXECUTOR_PLAN_MISSING).to_dict()
        worktree_stage = _mapping(stages.get(WORKTREE_CREATE_STAGE_KEY))
        worktree_result = _mapping(worktree_stage.get("worktree_create_result"))
        if not worktree_stage or not worktree_result:
            return _reject(FAIL_WORKTREE_CREATE_STAGE_MISSING).to_dict()
        if (
            worktree_stage.get("decision")
            != QUEUE_AUTHORIZED_WORKTREE_CREATE_INVOKE_ACCEPT
        ):
            return _reject(FAIL_WORKTREE_CREATE_STAGE_REJECTED).to_dict()

        pilot_stage = _mapping(stages.get(BOUNDED_WORKER_PILOT_STAGE_KEY))
        pilot_result = _mapping(pilot_stage.get("pilot_result"))
        pilot_receipt = _mapping(pilot_result.get("receipt"))
        if not pilot_stage or not pilot_result or not pilot_receipt:
            return _reject(FAIL_BOUNDED_WORKER_PILOT_MISSING).to_dict()
        if (
            pilot_stage.get("decision")
            != QUEUE_AUTHORIZED_BOUNDED_WORKER_PILOT_INVOKE_ACCEPT
            or pilot_result.get("accepted") is not True
        ):
            return _reject(FAIL_BOUNDED_WORKER_PILOT_REJECTED).to_dict()

        work_order_id = str(pilot_receipt.get("work_order_id") or "").strip()
        if not work_order_id:
            return _reject(FAIL_WORK_ORDER_ID_MISSING).to_dict()
        if str(worktree_result.get("work_order_id") or "").strip() != work_order_id:
            return _reject(FAIL_WORKTREE_BINDING_MISMATCH).to_dict()
        work_order = _mapping(
            self.work_order_resolver.resolve(
                work_order_id=work_order_id,
                queue_item_id=request.queue_item_id,
                selected_slice=request.selected_slice,
            )
        )
        if not work_order:
            return _reject(
                FAIL_WORK_ORDER_MISSING, f"work_order_id:{work_order_id}"
            ).to_dict()
        try:
            work_order_digest = canonical_full_work_order_digest(work_order)
        except (TypeError, ValueError):
            return _reject(FAIL_WORK_ORDER_DIGEST_MISMATCH).to_dict()
        if str(executor_plan.get("work_order_digest") or "") != work_order_digest:
            return _reject(FAIL_WORK_ORDER_DIGEST_MISMATCH).to_dict()

        worktree_path = Path(
            str(worktree_result.get("worktree_path") or "").strip()
        )
        guard = validate_wre_worker_operation_cwd(
            repo_root=self.repo_root,
            worktree_path=worktree_path,
            operation_cwd=worktree_path,
        )
        if not guard.ok:
            return _reject(FAIL_CWD_GUARD, guard.code).to_dict()

        branch_name = str(worktree_result.get("branch_name") or "").strip()
        expected_branch = str(work_order.get("branch_name") or "").strip()
        if not branch_name or not expected_branch or branch_name != expected_branch:
            return _reject(FAIL_BRANCH_BINDING_MISMATCH).to_dict()
        if branch_name.lower() in _PROTECTED_BRANCHES:
            return _reject(FAIL_PROTECTED_BRANCH).to_dict()

        verifier_plan = _mapping(work_order.get("slice_verifier_plan"))
        planned_base_sha = str(verifier_plan.get("base_sha") or "").strip().lower()
        if not planned_base_sha:
            return _reject(FAIL_BASE_SHA_MISSING).to_dict()
        if not _SHA_RE.fullmatch(planned_base_sha):
            return _reject(FAIL_BASE_SHA_INVALID).to_dict()

        message = _commit_message(work_order, request.selected_slice)
        if not message:
            return _reject(FAIL_COMMIT_MESSAGE_INVALID).to_dict()

        expected_paths, path_error = _validated_artifact_paths(
            pilot_receipt.get("written_artifacts"),
            worktree_path=worktree_path,
        )
        if path_error:
            return _reject(path_error).to_dict()
        try:
            observed_artifact_digest = _artifact_digest(
                expected_paths,
                worktree_path=worktree_path,
            )
        except (OSError, UnicodeError):
            return _reject(FAIL_WRITTEN_ARTIFACT_DIGEST_MISMATCH).to_dict()
        if observed_artifact_digest != str(
            pilot_receipt.get("written_artifact_digest") or ""
        ):
            return _reject(FAIL_WRITTEN_ARTIFACT_DIGEST_MISMATCH).to_dict()

        ok, live_branch = _read_git(
            self.evidence_command_runner,
            worktree_path=worktree_path,
            argv=("git", "symbolic-ref", "--short", "HEAD"),
        )
        if not ok or not live_branch:
            return _reject(FAIL_GIT_STATE_READ, FAIL_BRANCH_BINDING_MISMATCH).to_dict()
        if live_branch != expected_branch or live_branch.lower() in _PROTECTED_BRANCHES:
            return _reject(FAIL_BRANCH_BINDING_MISMATCH).to_dict()

        ok, live_base_sha = _read_git(
            self.evidence_command_runner,
            worktree_path=worktree_path,
            argv=("git", "rev-parse", "HEAD"),
        )
        live_base_sha = live_base_sha.lower()
        if not ok or not _SHA_RE.fullmatch(live_base_sha):
            return _reject(FAIL_GIT_STATE_READ, FAIL_BASE_SHA_INVALID).to_dict()
        expected_base_sha = planned_base_sha
        if live_base_sha != expected_base_sha:
            attempt_key = _commit_attempt_key(
                work_order=work_order,
                base_sha=expected_base_sha,
                branch_name=branch_name,
                worktree_path=worktree_path,
                expected_paths=expected_paths,
                pilot_receipt=pilot_receipt,
            )
            reconciled, tree_sha = _verify_existing_commit(
                runner=self.evidence_command_runner,
                worktree_path=worktree_path,
                base_sha=expected_base_sha,
                head_sha=live_base_sha,
                expected_paths=expected_paths,
                expected_attempt_key=attempt_key,
            )
            if not reconciled:
                return _reject(FAIL_BASE_SHA_MISMATCH).to_dict()
            receipt = _build_receipt(
                work_order_id=work_order_id,
                request=request,
                base_sha=expected_base_sha,
                head_sha=live_base_sha,
                tree_sha=tree_sha,
                branch_name=branch_name,
                worktree_path=worktree_path,
                expected_paths=expected_paths,
                pilot_receipt=pilot_receipt,
                worktree_result=worktree_result,
                message=(
                    message + "\n\nRedDog-Commit-Attempt: " + attempt_key
                ),
                work_order=work_order,
                chain_state=chain_state,
                reconciled_existing_commit=True,
                commit_attempt_key=attempt_key,
            )
            return ResidentQueueExactShaCommitResult(
                decision=RESIDENT_QUEUE_EXACT_SHA_COMMIT_ACCEPT,
                accepted=True,
                rejection_reasons=[],
                commit_receipt=receipt,
                effect_commit_state=EFFECT_COMMITTED,
                reconciliation_required=False,
                commit_runner_invoked=False,
            ).to_dict()

        dirty_paths: set[str] = set()
        ok, cached_output = _read_git(
            self.evidence_command_runner,
            worktree_path=worktree_path,
            argv=("git", "diff", "--cached", "--name-only"),
        )
        if not ok:
            return _reject(FAIL_GIT_STATE_READ).to_dict()
        if _path_lines(cached_output):
            return _reject(FAIL_INDEX_NOT_CLEAN).to_dict()
        for argv in (
            ("git", "diff", "--name-only"),
            ("git", "ls-files", "--others", "--exclude-standard"),
        ):
            ok, output = _read_git(
                self.evidence_command_runner,
                worktree_path=worktree_path,
                argv=argv,
            )
            if not ok:
                return _reject(FAIL_GIT_STATE_READ).to_dict()
            dirty_paths.update(_path_lines(output))
        if not dirty_paths:
            return _reject(FAIL_EMPTY_CHANGESET).to_dict()
        if dirty_paths != set(expected_paths):
            return _reject(FAIL_DIRTY_PATH_SET_MISMATCH).to_dict()

        attempt_key = _commit_attempt_key(
            work_order=work_order,
            base_sha=live_base_sha,
            branch_name=branch_name,
            worktree_path=worktree_path,
            expected_paths=expected_paths,
            pilot_receipt=pilot_receipt,
        )
        commit_message = (
            message + "\n\nRedDog-Commit-Attempt: " + attempt_key
        )
        commit_runner_invoked = True
        try:
            raw_commit = self.commit_runner.commit_all(
                worktree_path=worktree_path,
                add_paths=list(expected_paths),
                message=commit_message,
            )
        except Exception:
            raw_commit = {"ok": False}

        ok, observed_head = _read_git(
            self.evidence_command_runner,
            worktree_path=worktree_path,
            argv=("git", "rev-parse", "HEAD"),
        )
        observed_head = observed_head.lower()
        commit_ok = _mapping(raw_commit).get("ok") is True
        if not commit_ok:
            if ok and _SHA_RE.fullmatch(observed_head) and observed_head != live_base_sha:
                return _reject(
                    FAIL_COMMIT_STATE_INDETERMINATE,
                    effect_commit_state=EFFECT_INDETERMINATE,
                    reconciliation_required=True,
                    commit_runner_invoked=commit_runner_invoked,
                ).to_dict()
            return _reject(
                FAIL_COMMIT_OPERATION,
                effect_commit_state=EFFECT_NOT_COMMITTED,
                commit_runner_invoked=commit_runner_invoked,
            ).to_dict()

        if not ok or not _SHA_RE.fullmatch(observed_head):
            return _reject(
                FAIL_HEAD_SHA_INVALID,
                effect_commit_state=EFFECT_INDETERMINATE,
                reconciliation_required=True,
                commit_runner_invoked=commit_runner_invoked,
            ).to_dict()
        if observed_head == live_base_sha:
            return _reject(
                FAIL_HEAD_SHA_UNCHANGED,
                effect_commit_state=EFFECT_NOT_COMMITTED,
                commit_runner_invoked=commit_runner_invoked,
            ).to_dict()

        verified, tree_sha = _verify_existing_commit(
            runner=self.evidence_command_runner,
            worktree_path=worktree_path,
            base_sha=live_base_sha,
            head_sha=observed_head,
            expected_paths=expected_paths,
            expected_attempt_key=attempt_key,
        )
        if not verified:
            return _reject(
                FAIL_COMMIT_PARENT_MISMATCH,
                effect_commit_state=EFFECT_INDETERMINATE,
                reconciliation_required=True,
                commit_runner_invoked=commit_runner_invoked,
            ).to_dict()
        receipt = _build_receipt(
            work_order_id=work_order_id,
            request=request,
            base_sha=live_base_sha,
            head_sha=observed_head,
            tree_sha=tree_sha,
            branch_name=branch_name,
            worktree_path=worktree_path,
            expected_paths=expected_paths,
            pilot_receipt=pilot_receipt,
            worktree_result=worktree_result,
            message=commit_message,
            work_order=work_order,
            chain_state=chain_state,
            reconciled_existing_commit=False,
            commit_attempt_key=attempt_key,
        )
        return ResidentQueueExactShaCommitResult(
            decision=RESIDENT_QUEUE_EXACT_SHA_COMMIT_ACCEPT,
            accepted=True,
            rejection_reasons=[],
            commit_receipt=receipt,
            effect_commit_state=EFFECT_COMMITTED,
            reconciliation_required=False,
            commit_runner_invoked=True,
        ).to_dict()


def build_reddog_resident_queue_exact_sha_commit_stage_handler(
    *,
    chain_results_store: ResidentQueueChainResultsStore,
    work_order_resolver: ResidentQueueCommitWorkOrderResolver,
    commit_runner: Any,
    evidence_command_runner: Any,
    repo_root: Path,
) -> ResidentQueueExactShaCommitStageHandler:
    return ResidentQueueExactShaCommitStageHandler(
        chain_results_store=chain_results_store,
        work_order_resolver=work_order_resolver,
        commit_runner=commit_runner,
        evidence_command_runner=evidence_command_runner,
        repo_root=repo_root,
    )


__all__ = [
    "BOUNDED_WORKER_PILOT_STAGE_KEY",
    "EXECUTOR_PLAN_STAGE_KEY",
    "EFFECT_COMMITTED",
    "EFFECT_INDETERMINATE",
    "EFFECT_NOT_ATTEMPTED",
    "EFFECT_NOT_COMMITTED",
    "EXACT_SHA_COMMIT_STAGE_KEY",
    "EXACT_SHA_COMMIT_RECEIPT_SCHEMA",
    "ExactShaCommitReceipt",
    "FAIL_ARTIFACT_PATH_ESCAPE",
    "FAIL_ARTIFACT_SYMLINK",
    "FAIL_BASE_SHA_MISMATCH",
    "FAIL_BASE_SHA_MISSING",
    "FAIL_BRANCH_BINDING_MISMATCH",
    "FAIL_COMMIT_OPERATION",
    "FAIL_COMMIT_PARENT_MISMATCH",
    "FAIL_COMMIT_STATE_INDETERMINATE",
    "FAIL_DIRTY_PATH_SET_MISMATCH",
    "FAIL_EMPTY_CHANGESET",
    "FAIL_EXECUTOR_PLAN_MISSING",
    "FAIL_HEAD_SHA_UNCHANGED",
    "FAIL_INDEX_NOT_CLEAN",
    "FAIL_WRITTEN_ARTIFACT_DIGEST_MISMATCH",
    "FAIL_WORK_ORDER_DIGEST_MISMATCH",
    "ResidentQueueCommitWorkOrderResolver",
    "ResidentQueueExactShaCommitResult",
    "ResidentQueueExactShaCommitStageHandler",
    "WORKTREE_CREATE_STAGE_KEY",
    "build_reddog_resident_queue_exact_sha_commit_stage_handler",
    "validate_exact_sha_commit_receipt",
]
