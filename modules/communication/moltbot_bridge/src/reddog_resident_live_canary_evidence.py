"""Fail-closed evidence validation for the resident RedDog live canary."""

from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Optional

from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    runtime_operation_lock,
    secure_read_confined_bytes,
)

from modules.communication.moltbot_bridge.src.reddog_resident_control_loop_receipt_store import (
    CONTROL_LOOP_RECEIPT_SCHEMA_VERSION,
    verify_resident_control_loop_receipt,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_chain_results_store import (
    CHAIN_RESULTS_SCHEMA_VERSION,
    resident_queue_chain_receipt_id,
    resident_queue_chain_snapshot_is_canonical,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_pattern_memory_admission_handler import (
    PATTERN_MEMORY_ADMISSION_STAGE_KEY,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_orchestration_plan import (
    NEXT_QUEUE_CHAIN_COMPLETE,
    NEXT_QUEUE_PATTERN_MEMORY_ADMISSION_INVOKE,
    RESIDENT_QUEUE_ORCHESTRATION_PLAN_COMPLETE,
    RESIDENT_QUEUE_ORCHESTRATION_PLAN_READY,
    plan_reddog_resident_queue_orchestration,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_pattern_memory_admission_invoke import (
    QUEUE_AUTHORIZED_PATTERN_MEMORY_ADMISSION_INVOKE_ACCEPT,
    canonical_pattern_memory_admission_identity,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_verified_draft_pr_publish_invoke import (
    QUEUE_AUTHORIZED_VERIFIED_DRAFT_PR_PUBLISH_INVOKE_ACCEPT,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_worktree_create_invoke import (
    QUEUE_AUTHORIZED_WORKTREE_CREATE_INVOKE_ACCEPT,
)
from modules.communication.moltbot_bridge.src.reddog_wre_worktree_create import (
    WORKTREE_CREATE_ACCEPT,
)
from modules.infrastructure.wre_core.src.reddog_verified_draft_pr_publish import (
    VERIFIED_DRAFT_PR_PUBLISH_ACCEPT,
)
from modules.communication.moltbot_bridge.src.reddog_verified_pattern_memory_sink import (
    build_reddog_verified_pattern_memory_sink,
    reddog_verified_pattern_memory_record_digest,
)


@dataclass(frozen=True)
class CanaryInvocationEvidence:
    confirmed: bool
    invoked: bool
    blockers: tuple[str, ...]
    control_result: Mapping[str, Any]
    control_receipt: Mapping[str, Any]
    previous_revision: Optional[str]
    observed_revision: Optional[str]
    control_receipt_id: Optional[str]
    pre_chain_receipt_ids: frozenset[str]
    work_state: Mapping[str, Any]
    chain_state: Mapping[str, Any]


def read_control_receipts(
    path: Path,
    *,
    allowed_root: Path,
) -> tuple[Mapping[str, Any], ...]:
    """Read the complete confined JSONL stream or reject it fail-closed."""

    if not path.is_file():
        return ()
    receipts: list[Mapping[str, Any]] = []
    try:
        with runtime_operation_lock(str(path) + ".operation"):
            raw, _ = secure_read_confined_bytes(
                path,
                allowed_root=allowed_root,
                max_bytes=1024 * 1024,
            )
        lines = raw.decode("utf-8").splitlines()
    except (OSError, UnicodeError, ValueError) as exc:
        raise ValueError("control_receipt_stream_unreadable") from exc
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except (json.JSONDecodeError, TypeError) as exc:
            raise ValueError(f"control_receipt_stream_invalid_json:{line_number}") from exc
        if not isinstance(payload, Mapping):
            raise ValueError(f"control_receipt_stream_invalid_record:{line_number}")
        receipts.append(payload)
    return tuple(receipts)


def select_new_control_receipt(
    pre_receipts: tuple[Mapping[str, Any], ...],
    post_receipts: tuple[Mapping[str, Any], ...],
    receipt_id: Optional[str],
) -> Mapping[str, Any]:
    """Return exactly one newly persisted receipt matching the runner result."""

    if not receipt_id:
        return {}
    pre_ids = {_text(item.get("receipt_id")) for item in pre_receipts}
    if receipt_id in pre_ids:
        return {}
    matches = [
        item for item in post_receipts
        if _text(item.get("receipt_id")) == receipt_id
    ]
    return matches[0] if len(matches) == 1 else {}


def chain_receipt_ids(chain_state: Mapping[str, Any]) -> frozenset[str]:
    """Return non-empty receipt IDs only from the canonical chain envelope."""

    if chain_state.get("schema_version") != CHAIN_RESULTS_SCHEMA_VERSION:
        return frozenset()
    raw = chain_state.get("receipts")
    if not isinstance(raw, list):
        return frozenset()
    return frozenset(
        value for item in raw
        if isinstance(item, Mapping) and (value := _text(item.get("receipt_id")))
    )


def evaluate_live_proof(
    *,
    repo_root: Path,
    runtime_root: Path,
    queue_item_id: str,
    invocation: CanaryInvocationEvidence,
    now_iso: str,
) -> dict[str, Any]:
    """Evaluate one invocation against persisted causal and stage evidence."""

    stages = _mapping(invocation.chain_state.get("stage_results"))
    plan, chain_blockers = _chain_evidence(invocation, queue_item_id, now_iso)
    draft = _draft_pr_evidence(stages)
    worktree = _worktree_evidence(stages, repo_root)
    pattern = _pattern_memory_evidence(
        stages,
        repo_root,
        runtime_root,
        plan,
        draft,
        worktree,
    )
    blockers = [
        *_fresh_execution_blockers(invocation, repo_root, runtime_root),
        *chain_blockers,
        *draft["blockers"],
        *pattern["blockers"],
        *_lineage_blockers(stages, plan),
        *worktree["blockers"],
    ]
    return {
        "complete": not blockers,
        "blockers": list(dict.fromkeys(blockers)),
        "plan_id": plan.plan_id if plan else None,
        "accepted_stage_count": len(plan.accepted_stages) if plan else 0,
        "draft_pr_receipt_id": draft["receipt_id"],
        "draft_pr_url": draft["url"],
        "no_merge_performed": draft["no_merge"],
        "isolated_worktree_observed": not worktree["blockers"],
        "pattern_memory_admission_id": pattern["admission_id"],
        "pattern_memory_record_id": pattern["record_id"],
        "pattern_memory_record_digest": pattern["record_digest"],
    }


def _fresh_execution_blockers(
    invocation: CanaryInvocationEvidence,
    repo_root: Path,
    runtime_root: Path,
) -> tuple[str, ...]:
    blockers: list[str] = []
    if not invocation.invoked:
        blockers.append("control_loop_not_invoked")
    if invocation.control_result.get("accepted") is not True:
        blockers.append("control_loop_not_accepted")
    if invocation.control_result.get("status") != "PASS":
        blockers.append("control_loop_status_not_pass")
    if (
        not invocation.previous_revision
        or not invocation.observed_revision
        or invocation.observed_revision == invocation.previous_revision
    ):
        blockers.append("new_chain_revision_not_observed")
    blockers.extend(_control_receipt_blockers(invocation, repo_root, runtime_root))
    return tuple(blockers)


def _control_receipt_blockers(
    invocation: CanaryInvocationEvidence,
    repo_root: Path,
    runtime_root: Path,
) -> tuple[str, ...]:
    receipt = invocation.control_receipt
    if not receipt:
        return ("new_control_receipt_not_observed",)
    blockers: list[str] = []
    if receipt.get("schema_version") != CONTROL_LOOP_RECEIPT_SCHEMA_VERSION:
        blockers.append("control_receipt_schema_mismatch")
    if _text(receipt.get("receipt_id")) != invocation.control_receipt_id:
        blockers.append("control_receipt_id_mismatch")
    if receipt.get("accepted") is not True or receipt.get("status") != "PASS":
        blockers.append("control_receipt_not_accepted_pass")
    if receipt.get("control_lock_acquired") is not True:
        blockers.append("control_receipt_shared_lock_missing")
    if receipt.get("repo_root_digest") != _digest(str(repo_root.resolve())):
        blockers.append("control_receipt_repo_root_mismatch")
    progress = receipt.get("serial_progress")
    if isinstance(progress, bool) or not isinstance(progress, int) or progress <= 0:
        blockers.append("control_receipt_serial_progress_missing")
    try:
        authority_profile = _runtime_authority_profile(runtime_root)
        authority_profile_digest = "sha256:" + _digest(authority_profile)
        verify_resident_control_loop_receipt(
            receipt,
            expected_repo_root=repo_root,
            expected_signer_public_key=str(authority_profile["reddog_public_key"]),
            expected_key_epoch=str(authority_profile["key_epoch"]),
            expected_consensus_receipt_digest=str(
                authority_profile["consensus_receipt_digest"]
            ),
            expected_authority_profile_digest=authority_profile_digest,
            require_authenticated=True,
        )
    except (KeyError, TypeError, ValueError):
        blockers.append("control_receipt_auth_or_integrity_invalid")
    return tuple(blockers)


def _runtime_authority_profile(runtime_root: Path) -> Mapping[str, Any]:
    path = runtime_root / "authority_profile.json"
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 256 * 1024:
        raise ValueError("authority_profile_invalid")
    resolved = path.resolve()
    if not _is_inside(resolved, runtime_root):
        raise ValueError("authority_profile_outside_runtime_root")
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError("authority_profile_invalid")
    for key in (
        "principal_id",
        "reddog_public_key",
        "key_epoch",
        "consensus_receipt_digest",
    ):
        value = payload.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"authority_profile_{key}_missing")
    return payload


def _chain_evidence(
    invocation: CanaryInvocationEvidence,
    queue_item_id: str,
    now_iso: str,
) -> tuple[Any, tuple[str, ...]]:
    state = invocation.chain_state
    if state.get("schema_version") != CHAIN_RESULTS_SCHEMA_VERSION:
        return None, ("chain_results_schema_mismatch",)
    if not resident_queue_chain_snapshot_is_canonical(state):
        return None, ("chain_results_revision_invalid",)
    stages = _mapping(state.get("stage_results"))
    plan = plan_reddog_resident_queue_orchestration(
        invocation.work_state,
        chain_results={str(key): _mapping(value) for key, value in stages.items()},
        requested_queue_item_id=queue_item_id or None,
        now_iso=now_iso,
    )
    blockers: list[str] = []
    if plan.accepted is not True or plan.status != RESIDENT_QUEUE_ORCHESTRATION_PLAN_COMPLETE:
        blockers.append("resident_chain_not_complete")
    if (
        _text(state.get("queue_item_id")) != _text(plan.selected_queue_item_id)
        or _text(state.get("selected_slice")) != _text(plan.selected_slice)
    ):
        blockers.append("chain_envelope_plan_mismatch")
    previous_plan = _previous_chain_plan(invocation, queue_item_id, now_iso)
    blockers.extend(_new_chain_receipt_blockers(invocation, previous_plan, plan))
    return plan, tuple(blockers)


def _previous_chain_plan(
    invocation: CanaryInvocationEvidence,
    queue_item_id: str,
    now_iso: str,
) -> Any:
    stages = dict(_mapping(invocation.chain_state.get("stage_results")))
    stages.pop(PATTERN_MEMORY_ADMISSION_STAGE_KEY, None)
    return plan_reddog_resident_queue_orchestration(
        invocation.work_state,
        chain_results={str(key): _mapping(value) for key, value in stages.items()},
        requested_queue_item_id=queue_item_id or None,
        now_iso=now_iso,
    )


def _new_chain_receipt_blockers(
    invocation: CanaryInvocationEvidence,
    previous_plan: Any,
    final_plan: Any,
) -> tuple[str, ...]:
    state = invocation.chain_state
    raw = state.get("receipts")
    receipts = [item for item in raw if isinstance(item, Mapping)] if isinstance(raw, list) else []
    new = [
        item for item in receipts
        if (receipt_id := _text(item.get("receipt_id")))
        and receipt_id not in invocation.pre_chain_receipt_ids
    ]
    if not new:
        return ("new_chain_store_receipt_not_observed",)
    final = receipts[-1] if receipts else {}
    final_id = _text(final.get("receipt_id"))
    if final_id not in {_text(item.get("receipt_id")) for item in new}:
        return ("final_chain_store_receipt_not_new",)
    if not _chain_store_receipt_shape(final):
        return ("new_chain_store_receipt_malformed",)
    queue_id = _text(final_plan.selected_queue_item_id)
    selected_slice = _text(final_plan.selected_slice)
    if _text(final.get("queue_item_id")) != queue_id or _text(final.get("selected_slice")) != selected_slice:
        return ("new_chain_store_receipt_envelope_mismatch",)
    if _text(final.get("store_revision")) != invocation.observed_revision:
        return ("new_chain_store_receipt_revision_mismatch",)
    if not _final_receipt_transition_matches(final, previous_plan, final_plan):
        return ("final_chain_store_receipt_transition_mismatch",)
    return ()


def _final_receipt_transition_matches(
    receipt: Mapping[str, Any],
    previous_plan: Any,
    final_plan: Any,
) -> bool:
    expected_id = resident_queue_chain_receipt_id(
        queue_item_id=str(final_plan.selected_queue_item_id or ""),
        selected_slice=str(final_plan.selected_slice or ""),
        recorded_stage=PATTERN_MEMORY_ADMISSION_STAGE_KEY,
        previous_plan_id=str(previous_plan.plan_id or ""),
        next_plan_id=str(final_plan.plan_id or ""),
    )
    return (
        previous_plan.accepted is True
        and previous_plan.status == RESIDENT_QUEUE_ORCHESTRATION_PLAN_READY
        and previous_plan.current_stage == PATTERN_MEMORY_ADMISSION_STAGE_KEY
        and previous_plan.next_action == NEXT_QUEUE_PATTERN_MEMORY_ADMISSION_INVOKE
        and receipt.get("recorded_stage") == PATTERN_MEMORY_ADMISSION_STAGE_KEY
        and receipt.get("previous_plan_id") == previous_plan.plan_id
        and receipt.get("next_plan_id") == final_plan.plan_id
        and receipt.get("next_action") == NEXT_QUEUE_CHAIN_COMPLETE
        and receipt.get("receipt_id") == expected_id
    )


def _chain_store_receipt_shape(receipt: Mapping[str, Any]) -> bool:
    return (
        _is_sha256_digest(receipt.get("receipt_id"))
        and bool(_text(receipt.get("recorded_stage")))
        and bool(_text(receipt.get("previous_plan_id")))
        and bool(_text(receipt.get("next_plan_id")))
        and bool(_text(receipt.get("next_action")))
        and bool(_text(receipt.get("store_revision")))
    )


def _draft_pr_evidence(stages: Mapping[str, Any]) -> dict[str, Any]:
    stage = _mapping(stages.get("verified_draft_pr_publish"))
    result = _mapping(stage.get("publish_result"))
    receipt = _mapping(result.get("receipt"))
    url = _text(receipt.get("draft_pr_url"))
    receipt_id = _text(receipt.get("receipt_id"))
    blockers: list[str] = []
    accepted = (
        stage.get("decision") == QUEUE_AUTHORIZED_VERIFIED_DRAFT_PR_PUBLISH_INVOKE_ACCEPT
        and result.get("decision") == VERIFIED_DRAFT_PR_PUBLISH_ACCEPT
        and result.get("accepted") is True
        and receipt.get("accepted") is True
        and bool(receipt_id and url and url.startswith("https://github.com/") and "/pull/" in url)
    )
    if not accepted:
        blockers.append("accepted_verified_draft_pr_evidence_missing")
    no_merge = all(item.get("no_merge_performed") is True for item in (stage, result, receipt))
    no_ready = all(item.get("no_ready_performed") is True for item in (stage, result, receipt))
    if not no_merge:
        blockers.append("explicit_no_merge_evidence_missing")
    if not no_ready:
        blockers.append("explicit_draft_only_evidence_missing")
    return {
        "blockers": tuple(blockers),
        "receipt_id": receipt_id,
        "url": url,
        "no_merge": no_merge,
        "work_order_id": _text(receipt.get("work_order_id")),
        "slice_name": _text(receipt.get("slice_name")),
        "head": _text(receipt.get("verified_head_sha")),
    }


def _pattern_memory_evidence(
    stages: Mapping[str, Any],
    repo_root: Path,
    runtime_root: Path,
    plan: Any,
    draft: Mapping[str, Any],
    worktree: Mapping[str, Any],
) -> dict[str, Any]:
    stage = _mapping(stages.get("pattern_memory_admission"))
    receipt = _mapping(stage.get("receipt"))
    admission_id = _text(receipt.get("admission_id"))
    record_id = _text(receipt.get("pattern_memory_record_id"))
    record_digest = _text(receipt.get("record_digest"))
    record = _load_pattern_memory_record(repo_root, runtime_root, record_id)
    identity = canonical_pattern_memory_admission_identity(record, record_id) if record else ("", "")
    context_matches = _pattern_record_context_matches(record, plan, draft, worktree)
    accepted = (
        stage.get("decision") == QUEUE_AUTHORIZED_PATTERN_MEMORY_ADMISSION_INVOKE_ACCEPT
        and stage.get("pattern_memory_write_performed") is True
        and stage.get("no_merge_performed") is True
        and bool(admission_id and record_id and _is_sha256_digest(record_digest))
        and identity == (admission_id, record_digest)
        and reddog_verified_pattern_memory_record_digest(record) == record_digest
        and context_matches
    )
    blockers = () if accepted else ("highest_profile_completion_evidence_missing",)
    return {
        "blockers": blockers,
        "admission_id": admission_id,
        "record_id": record_id,
        "record_digest": record_digest,
    }


def _pattern_record_context_matches(
    record: Mapping[str, Any],
    plan: Any,
    draft: Mapping[str, Any],
    worktree: Mapping[str, Any],
) -> bool:
    if plan is None:
        return False
    work_order_id = _text(record.get("work_order_id"))
    selected_slice = _text(record.get("slice_name"))
    candidate_head = _text(record.get("candidate_head_sha"))
    return bool(
        work_order_id
        and work_order_id == draft.get("work_order_id")
        and selected_slice == _text(plan.selected_slice)
        and selected_slice == draft.get("slice_name")
        and candidate_head
        and candidate_head == draft.get("head")
        and candidate_head == worktree.get("head")
    )


def _load_pattern_memory_record(
    repo_root: Path,
    runtime_root: Path,
    record_id: Optional[str],
) -> Mapping[str, Any]:
    db_path = runtime_root / "pattern_memory.db"
    if not record_id or not db_path.is_file():
        return {}
    sink = build_reddog_verified_pattern_memory_sink(repo_root=repo_root, db_path=db_path)
    record = sink.load_verified_outcome(record_id) if sink is not None else None
    return record if isinstance(record, Mapping) else {}


def _worktree_evidence(stages: Mapping[str, Any], repo_root: Path) -> dict[str, Any]:
    stage = _mapping(stages.get("worktree_create"))
    result = _mapping(stage.get("worktree_create_result"))
    raw_path = _text(result.get("worktree_path"))
    if (
        stage.get("decision") != QUEUE_AUTHORIZED_WORKTREE_CREATE_INVOKE_ACCEPT
        or result.get("decision") != WORKTREE_CREATE_ACCEPT
        or not raw_path
    ):
        return {"blockers": ("isolated_worktree_evidence_missing",), "head": None}
    path = Path(raw_path)
    expected_head = _lineage_head(stages)
    observed_head = _registered_worktree_head(repo_root, path)
    valid = bool(
        path.is_absolute()
        and path.is_dir()
        and not _is_inside(path, repo_root)
        and expected_head
        and observed_head == expected_head
    )
    blockers = () if valid else ("isolated_worktree_evidence_missing",)
    return {"blockers": blockers, "head": observed_head}


def _registered_worktree_head(repo_root: Path, worktree_path: Path) -> Optional[str]:
    root = worktree_path.resolve()
    records = _git_output(repo_root, "worktree", "list", "--porcelain")
    registered = _registered_worktree_records(records)
    entry = registered.get(str(root))
    if not entry or not _valid_git_worktree(root):
        return None
    head = _git_output(root, "rev-parse", "HEAD")
    return head.strip() if head.strip() == entry else None


def _registered_worktree_records(output: str) -> dict[str, str]:
    records: dict[str, str] = {}
    path = ""
    for line in output.splitlines():
        if line.startswith("worktree "):
            path = str(Path(line.removeprefix("worktree ")).resolve())
        elif path and line.startswith("HEAD "):
            records[path] = line.removeprefix("HEAD ").strip()
        elif not line.strip():
            path = ""
    return records


def _valid_git_worktree(path: Path) -> bool:
    inside = _git_output(path, "rev-parse", "--is-inside-work-tree").strip()
    top = _git_output(path, "rev-parse", "--show-toplevel").strip()
    git_dir = _git_output(path, "rev-parse", "--git-dir").strip()
    return inside == "true" and Path(top).resolve() == path and bool(git_dir)


def _git_output(cwd: Path, *args: str) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(cwd), *args],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return result.stdout if result.returncode == 0 else ""


def _lineage_head(stages: Mapping[str, Any]) -> Optional[str]:
    draft = _mapping(_mapping(_mapping(stages.get("verified_draft_pr_publish")).get("publish_result")).get("receipt"))
    held = _mapping(_mapping(_mapping(stages.get("held_out_regression_gate")).get("gate_result")).get("receipt"))
    draft_head = _text(draft.get("verified_head_sha"))
    held_head = _text(held.get("candidate_head_sha"))
    return draft_head if draft_head and draft_head == held_head else None


def _lineage_blockers(stages: Mapping[str, Any], plan: Any) -> tuple[str, ...]:
    if plan is None:
        return ("key_receipt_lineage_missing",)
    draft = _mapping(_mapping(_mapping(stages.get("verified_draft_pr_publish")).get("publish_result")).get("receipt"))
    held = _mapping(_mapping(_mapping(stages.get("held_out_regression_gate")).get("gate_result")).get("receipt"))
    pattern = _mapping(_mapping(stages.get("pattern_memory_admission")).get("receipt"))
    work_ids = [_text(item.get("work_order_id")) for item in (draft, held, pattern)]
    slices = [_text(item.get("slice_name")) for item in (draft, held, pattern)]
    draft_head = _text(draft.get("verified_head_sha"))
    held_head = _text(held.get("candidate_head_sha"))
    if (
        not all(work_ids)
        or len(set(work_ids)) != 1
        or not all(slices)
        or len(set(slices)) != 1
        or slices[0] != _text(plan.selected_slice)
        or not draft_head
        or draft_head != held_head
    ):
        return ("key_receipt_lineage_mismatch",)
    return ()


def _mapping(value: Any) -> Mapping[str, Any]:
    if hasattr(value, "to_dict"):
        candidate = value.to_dict()
        return candidate if isinstance(candidate, Mapping) else {}
    return value if isinstance(value, Mapping) else {}


def _text(value: Any) -> Optional[str]:
    text = str(value or "").strip()
    return text or None


def _digest(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _is_sha256_digest(value: Any) -> bool:
    text = str(value or "")
    suffix = text.removeprefix("sha256:")
    return text.startswith("sha256:") and len(suffix) == 64 and all(ch in "0123456789abcdef" for ch in suffix)


def _is_inside(child: Path, parent: Path) -> bool:
    child_r = child.resolve()
    parent_r = parent.resolve()
    return child_r == parent_r or parent_r in child_r.parents


__all__ = [
    "CanaryInvocationEvidence",
    "chain_receipt_ids",
    "evaluate_live_proof",
    "read_control_receipts",
    "select_new_control_receipt",
]
