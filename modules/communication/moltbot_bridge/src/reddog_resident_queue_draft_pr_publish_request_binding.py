"""Resident queue verified draft-PR publish request binding.

Slice: REDDOG_RESIDENT_QUEUE_DRAFT_PR_PUBLISH_REQUEST_BINDING_PHASE1

This module derives the verified draft-PR publish request from an explicit
`draft_pr_publish_plan` on the bound work order plus recorded slice-verifier
and worktree-create chain results. It emits request data only; it does not
push branches, create PRs, mark PRs ready, merge, run commands, write
PatternMemory, settle rewards, enqueue OpenClaw, dispatch Hermes, or re-index
HoloIndex.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Mapping


DRAFT_PR_PUBLISH_REQUEST_BINDING_ACCEPT = "DRAFT_PR_PUBLISH_REQUEST_BINDING_ACCEPT"
DRAFT_PR_PUBLISH_REQUEST_BINDING_REJECT = "DRAFT_PR_PUBLISH_REQUEST_BINDING_REJECT"

FAIL_DRAFT_PR_PUBLISH_PLAN_MISSING = "FAIL_DRAFT_PR_PUBLISH_PLAN_MISSING"
FAIL_DRAFT_PR_PUBLISH_PLAN_INVALID = "FAIL_DRAFT_PR_PUBLISH_PLAN_INVALID"
FAIL_SLICE_VERIFIER_MISSING = "FAIL_SLICE_VERIFIER_MISSING"
FAIL_SLICE_VERIFIER_REJECTED = "FAIL_SLICE_VERIFIER_REJECTED"
FAIL_VERIFIER_RECEIPT_MISSING = "FAIL_VERIFIER_RECEIPT_MISSING"
FAIL_WORKTREE_CREATE_MISSING = "FAIL_WORKTREE_CREATE_MISSING"


@dataclass(frozen=True)
class ResidentQueueDraftPrPublishRequestBindingResult:
    decision: str
    accepted: bool
    publish_request: Dict[str, Any] = field(default_factory=dict)
    rejection_reasons: list[str] = field(default_factory=list)
    no_git_push_performed: bool = True
    no_github_call_performed: bool = True
    no_pr_created: bool = True
    no_ready_performed: bool = True
    no_merge_performed: bool = True
    no_pattern_memory_write_performed: bool = True
    no_reward_settlement_performed: bool = True
    no_openclaw_enqueue_performed: bool = True
    no_hermes_dispatch_performed: bool = True
    no_holoindex_reindex_performed: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def build_resident_queue_draft_pr_publish_request(
    *,
    work_order: Mapping[str, Any],
    stage_results: Mapping[str, Mapping[str, Any]],
) -> ResidentQueueDraftPrPublishRequestBindingResult:
    """Build a verified draft-PR publish request from resident queue state."""

    plan = _mapping(work_order.get("draft_pr_publish_plan"))
    reasons: list[str] = []
    if not plan:
        reasons.append(FAIL_DRAFT_PR_PUBLISH_PLAN_MISSING)

    slice_stage = _mapping(stage_results.get("slice_verifier"))
    verifier_result = _mapping(slice_stage.get("verifier_result"))
    verifier_receipt = _mapping(verifier_result.get("receipt"))
    if not slice_stage:
        reasons.append(FAIL_SLICE_VERIFIER_MISSING)
    elif slice_stage.get("decision") != "QUEUE_AUTHORIZED_SLICE_VERIFIER_INVOKE_ACCEPT":
        reasons.append(FAIL_SLICE_VERIFIER_REJECTED)
    elif verifier_result.get("accepted") is not True:
        reasons.append(FAIL_SLICE_VERIFIER_REJECTED)
    if not verifier_receipt:
        reasons.append(FAIL_VERIFIER_RECEIPT_MISSING)

    worktree_stage = _mapping(stage_results.get("worktree_create"))
    worktree_create = _mapping(worktree_stage.get("worktree_create_result"))
    worktree_path = str(worktree_create.get("worktree_path") or "")
    if not worktree_stage or not worktree_path:
        reasons.append(FAIL_WORKTREE_CREATE_MISSING)

    for field_name in ("branch_name", "pr_title", "pr_body"):
        if field_name not in plan or not str(plan.get(field_name) or "").strip():
            reasons.append(f"{FAIL_DRAFT_PR_PUBLISH_PLAN_INVALID}:{field_name}")

    draft_pr_only = plan.get("draft_pr_only", True)
    mark_ready = plan.get("mark_ready", False)
    merge = plan.get("merge", False)
    if draft_pr_only is not True:
        reasons.append(f"{FAIL_DRAFT_PR_PUBLISH_PLAN_INVALID}:draft_pr_only")
    if mark_ready is not False:
        reasons.append(f"{FAIL_DRAFT_PR_PUBLISH_PLAN_INVALID}:mark_ready")
    if merge is not False:
        reasons.append(f"{FAIL_DRAFT_PR_PUBLISH_PLAN_INVALID}:merge")

    if reasons:
        return _reject(reasons)

    request = {
        "work_order_id": str(work_order.get("work_order_id") or verifier_receipt.get("work_order_id") or ""),
        "pre_publish_branch_head_sha": str(verifier_receipt.get("head_sha") or ""),
        "branch_name": str(plan.get("branch_name") or ""),
        "base_branch": str(plan.get("base_branch") or work_order.get("base_ref") or "main"),
        "pr_title": str(plan.get("pr_title") or ""),
        "pr_body": str(plan.get("pr_body") or ""),
        "worktree_path": worktree_path,
        "draft_pr_only": True,
        "mark_ready": False,
        "merge": False,
    }
    return ResidentQueueDraftPrPublishRequestBindingResult(
        decision=DRAFT_PR_PUBLISH_REQUEST_BINDING_ACCEPT,
        accepted=True,
        publish_request=request,
        rejection_reasons=[],
    )


def _reject(reasons: list[str]) -> ResidentQueueDraftPrPublishRequestBindingResult:
    return ResidentQueueDraftPrPublishRequestBindingResult(
        decision=DRAFT_PR_PUBLISH_REQUEST_BINDING_REJECT,
        accepted=False,
        rejection_reasons=_dedupe(reasons),
    )


def _mapping(value: Any) -> Mapping[str, Any]:
    if hasattr(value, "to_dict"):
        candidate = value.to_dict()
        return candidate if isinstance(candidate, Mapping) else {}
    return value if isinstance(value, Mapping) else {}


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in seen:
            seen.add(text)
            ordered.append(text)
    return ordered


__all__ = [
    "DRAFT_PR_PUBLISH_REQUEST_BINDING_ACCEPT",
    "DRAFT_PR_PUBLISH_REQUEST_BINDING_REJECT",
    "FAIL_DRAFT_PR_PUBLISH_PLAN_INVALID",
    "FAIL_DRAFT_PR_PUBLISH_PLAN_MISSING",
    "FAIL_SLICE_VERIFIER_MISSING",
    "FAIL_SLICE_VERIFIER_REJECTED",
    "FAIL_VERIFIER_RECEIPT_MISSING",
    "FAIL_WORKTREE_CREATE_MISSING",
    "ResidentQueueDraftPrPublishRequestBindingResult",
    "build_resident_queue_draft_pr_publish_request",
]
