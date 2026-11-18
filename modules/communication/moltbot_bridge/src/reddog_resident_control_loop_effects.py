"""Derive resident control-loop effect claims from observed stage evidence."""

from __future__ import annotations

from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.reddog_resident_control_loop_outcomes import (
    strict_child_outcomes,
)


_AUTHORITY_ISSUING_STAGES = frozenset({"authority_runtime"})
_WORKER_EXECUTION_STAGES = frozenset({"bounded_worker_pilot"})
_WORKTREE_CREATION_STAGES = frozenset({"worktree_create"})
_BOUNDED_FILE_EDIT_STAGES = frozenset({"bounded_worker_pilot"})
_SLICE_VERIFICATION_STAGES = frozenset({"slice_verifier"})
_DRAFT_PR_PUBLISH_STAGES = frozenset({"verified_draft_pr_publish"})
_PATTERN_MEMORY_ADMISSION_STAGES = frozenset({"pattern_memory_admission"})


def derive_control_loop_effects(
    dispatched_stages: tuple[str, ...],
    claim_progress: int,
    result: Mapping[str, Any],
) -> dict[str, Any]:
    authority_count = sum(stage in _AUTHORITY_ISSUING_STAGES for stage in dispatched_stages)
    bounded_worker_count = sum(stage in _WORKER_EXECUTION_STAGES for stage in dispatched_stages)
    worktree_count = sum(stage in _WORKTREE_CREATION_STAGES for stage in dispatched_stages)
    bounded_edit_count = sum(stage in _BOUNDED_FILE_EDIT_STAGES for stage in dispatched_stages)
    verification_count = sum(stage in _SLICE_VERIFICATION_STAGES for stage in dispatched_stages)
    draft_pr_count = sum(stage in _DRAFT_PR_PUBLISH_STAGES for stage in dispatched_stages)
    pattern_memory_count = sum(
        stage in _PATTERN_MEMORY_ADMISSION_STAGES for stage in dispatched_stages
    )
    outcomes = strict_child_outcomes(result.get("child_execution_outcomes", ()))
    counts = _worker_counts(result, claim_progress, bounded_worker_count, outcomes)
    process_spawn_count = sum(
        outcome["worker_process_spawn_count"] for outcome in outcomes
    )
    shell_count = sum(outcome["shell_command_count"] for outcome in outcomes)
    unverified_count = sum(
        outcome["effect_evidence_complete"] is False for outcome in outcomes
    )
    if result.get("accepted") is True and unverified_count:
        raise ValueError("resident_control_loop_accepted_effects_unverified")
    return {
        "authority_issuance_count": authority_count,
        **counts,
        "worktree_creation_count": worktree_count,
        "bounded_file_edit_count": bounded_edit_count,
        "slice_verification_count": verification_count,
        "draft_pr_publish_count": draft_pr_count,
        "pattern_memory_admission_count": pattern_memory_count,
        "worker_process_spawn_count": process_spawn_count,
        "shell_command_count": shell_count,
        "worker_effects_unverified_count": unverified_count,
        "authority_issued": authority_count > 0,
        "worker_claim_performed": counts["worker_claim_count"] > 0,
        "worker_execution_performed": counts["worker_execution_count"] > 0,
        "worktree_creation_observed": worktree_count > 0,
        "bounded_file_edit_observed": bounded_edit_count > 0,
        "slice_verification_observed": verification_count > 0,
        "draft_pr_publish_observed": draft_pr_count > 0,
        "pattern_memory_admission_observed": pattern_memory_count > 0,
        "worker_process_spawn_observed": process_spawn_count > 0,
        "shell_command_execution_observed": shell_count > 0,
    }


def reject_contradictory_effect_claims(
    result: Mapping[str, Any], effects: Mapping[str, Any]
) -> None:
    for key, expected in effects.items():
        if key in result and result.get(key) != expected:
            raise ValueError(f"resident_control_loop_effect_claim_conflict:{key}")


def _worker_counts(
    result: Mapping[str, Any],
    claim_progress: int,
    bounded_worker_count: int,
    outcomes: tuple[dict[str, Any], ...],
) -> dict[str, int]:
    claim_count = _integer(result.get("worker_claim_count", claim_progress))
    if claim_count != claim_progress:
        raise ValueError("resident_control_loop_worker_claim_count_conflict")
    completion = _integer(result.get("worker_completion_count"))
    requeue = _integer(result.get("worker_requeue_count"))
    failure = _integer(result.get("worker_failure_count"))
    if completion + requeue + failure != claim_count:
        raise ValueError("resident_control_loop_worker_outcome_count_invalid")
    if len(outcomes) != claim_count:
        raise ValueError("resident_control_loop_worker_outcome_count_invalid")
    child_execution_count = sum(
        outcome["worker_execution_performed"] is True for outcome in outcomes
    )
    return {
        "worker_claim_count": claim_count,
        "worker_execution_count": child_execution_count + bounded_worker_count,
        "worker_completion_count": completion,
        "worker_requeue_count": requeue,
        "worker_failure_count": failure,
    }


def _integer(value: Any) -> int:
    try:
        return max(int(value or 0), 0)
    except (TypeError, ValueError):
        return 0


__all__ = ["derive_control_loop_effects", "reject_contradictory_effect_claims"]
