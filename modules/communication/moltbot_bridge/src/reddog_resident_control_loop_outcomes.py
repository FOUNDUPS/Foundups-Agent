"""Exact child-outcome bindings for resident control-loop receipts."""

from __future__ import annotations

import re
import hashlib
import json
from typing import Any, Mapping


_SHA256_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
_CLAIM_STATUS_TO_OUTCOME = {
    "SIGNED_WORKER_OPENCLAW_CLAIM_ACCEPT": "completed",
    "SIGNED_WORKER_OPENCLAW_CLAIM_REQUEUED": "requeued",
    "SIGNED_WORKER_OPENCLAW_CLAIM_REJECT": "failed",
}
_NO_EFFECT_FIELDS = frozenset(
    {
        "no_shell_command_executed",
        "no_repo_mutation_performed",
        "no_holoindex_reindex_performed",
        "no_hermes_dispatch_performed",
        "no_worktree_operation_performed",
        "no_pr_created",
        "no_live_foundup_enqueue_performed",
        "no_pattern_memory_write_performed",
        "no_reward_settlement_performed",
    }
)
_CLAIM_EVIDENCE_FIELDS = frozenset(
    {
        "accepted",
        "status",
        "task_id",
        "worker_role",
        "worker_runtime",
        "capability",
        "receipt_id",
        "rejection_reasons",
        "detail",
        "execution_result_digest",
        "worker_execution_performed",
        "effect_evidence_complete",
        "worker_process_spawn_count",
        "shell_command_count",
        *_NO_EFFECT_FIELDS,
    }
)


def derive_child_outcome_projections(
    result: Mapping[str, Any],
) -> tuple[tuple[dict[str, Any], ...], tuple[str, ...], tuple[str, ...]]:
    outcomes = strict_child_outcomes(result.get("child_execution_outcomes", ()))
    verify_child_execution_evidence(
        result.get("child_execution_evidence", ()), outcomes
    )
    receipt_ids = tuple(
        outcome["receipt_id"]
        for outcome in outcomes
        if outcome["status"] in {"completed", "requeued"}
    )
    evidence_digests = tuple(outcome["evidence_digest"] for outcome in outcomes)
    _reject_projection_conflicts(result, receipt_ids, evidence_digests)
    return outcomes, receipt_ids, evidence_digests


def strict_child_outcomes(value: Any) -> tuple[dict[str, Any], ...]:
    if not isinstance(value, (list, tuple)) or len(value) > 128:
        raise ValueError("resident_control_loop_receipt_child_outcomes_invalid")
    outcomes: list[dict[str, Any]] = []
    for raw in value:
        if not isinstance(raw, Mapping) or set(raw) != {
            "task_id",
            "status",
            "receipt_id",
            "evidence_digest",
            "worker_execution_performed",
            "effect_evidence_complete",
            "worker_process_spawn_count",
            "shell_command_count",
        }:
            raise ValueError("resident_control_loop_receipt_child_outcomes_invalid")
        if not isinstance(raw.get("worker_execution_performed"), bool) or not isinstance(
            raw.get("effect_evidence_complete"), bool
        ):
            raise ValueError("resident_control_loop_receipt_child_outcomes_invalid")
        outcome = {
            "task_id": str(raw.get("task_id") or "").strip(),
            "status": str(raw.get("status") or "").strip(),
            "receipt_id": str(raw.get("receipt_id") or "").strip(),
            "evidence_digest": str(raw.get("evidence_digest") or "").strip(),
            "worker_execution_performed": raw["worker_execution_performed"],
            "effect_evidence_complete": raw["effect_evidence_complete"],
            "worker_process_spawn_count": raw["worker_process_spawn_count"],
            "shell_command_count": raw["shell_command_count"],
        }
        _validate_outcome(outcome)
        outcomes.append(outcome)
    _validate_task_attempt_order(outcomes)
    return tuple(outcomes)


def _validate_task_attempt_order(outcomes: list[dict[str, Any]]) -> None:
    terminal_tasks: set[str] = set()
    for outcome in outcomes:
        task_id = outcome["task_id"]
        if task_id in terminal_tasks:
            raise ValueError("resident_control_loop_receipt_child_task_replay")
        if outcome["status"] in {"completed", "failed"}:
            terminal_tasks.add(task_id)


def verify_child_execution_evidence(
    value: Any, outcomes: tuple[dict[str, Any], ...]
) -> None:
    """Recompute complete OpenClaw child evidence before parent signing."""

    if not isinstance(value, (list, tuple)) or len(value) > 128:
        raise ValueError("resident_control_loop_child_evidence_invalid")
    evidence = tuple(item for item in value if isinstance(item, Mapping))
    if len(evidence) != len(value):
        raise ValueError("resident_control_loop_child_evidence_invalid")
    task_evidence = tuple(item for item in evidence if str(item.get("task_id") or ""))
    if len(task_evidence) != len(outcomes):
        raise ValueError("resident_control_loop_child_evidence_count_invalid")
    for raw, outcome in zip(task_evidence, outcomes):
        _verify_one_child_evidence(raw, outcome)


def _verify_one_child_evidence(
    raw: Mapping[str, Any], outcome: Mapping[str, Any]
) -> None:
    if set(raw) != _CLAIM_EVIDENCE_FIELDS:
        raise ValueError("resident_control_loop_child_evidence_fields_invalid")
    evidence = dict(raw)
    supplied_digest = evidence.get("execution_result_digest")
    evidence["execution_result_digest"] = ""
    expected_digest = "sha256:" + hashlib.sha256(
        json.dumps(
            evidence,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            default=str,
        ).encode("utf-8")
    ).hexdigest()
    status = str(raw.get("status") or "")
    receipt_id = str(raw.get("receipt_id") or "")
    expected_outcome = {
        "task_id": str(raw.get("task_id") or ""),
        "status": _CLAIM_STATUS_TO_OUTCOME.get(status, ""),
        "receipt_id": "" if status.endswith("_REJECT") else receipt_id,
        "evidence_digest": supplied_digest,
        "worker_execution_performed": raw.get("worker_execution_performed"),
        "effect_evidence_complete": raw.get("effect_evidence_complete"),
        "worker_process_spawn_count": raw.get("worker_process_spawn_count"),
        "shell_command_count": raw.get("shell_command_count"),
    }
    if supplied_digest != expected_digest or dict(outcome) != expected_outcome:
        raise ValueError("resident_control_loop_child_evidence_digest_invalid")
    _verify_child_effect_fields(raw)


def _verify_child_effect_fields(raw: Mapping[str, Any]) -> None:
    if (
        not isinstance(raw.get("accepted"), bool)
        or not isinstance(raw.get("worker_execution_performed"), bool)
        or not isinstance(raw.get("effect_evidence_complete"), bool)
        or any(not isinstance(raw.get(field), bool) for field in _NO_EFFECT_FIELDS)
    ):
        raise ValueError("resident_control_loop_child_effects_invalid")
    process_count = raw.get("worker_process_spawn_count")
    shell_count = raw.get("shell_command_count")
    if any(
        isinstance(value, bool) or not isinstance(value, int) or value < 0
        for value in (process_count, shell_count)
    ):
        raise ValueError("resident_control_loop_child_effects_invalid")
    if (raw.get("no_shell_command_executed") is True) != (shell_count == 0):
        if raw.get("effect_evidence_complete") is True:
            raise ValueError("resident_control_loop_child_effects_invalid")
    if raw.get("effect_evidence_complete") is False and any(
        raw.get(field) is not False for field in _NO_EFFECT_FIELDS
    ):
        raise ValueError("resident_control_loop_child_effects_invalid")
    if raw.get("worker_execution_performed") is False and (
        process_count > 0 or shell_count > 0
    ):
        raise ValueError("resident_control_loop_child_effects_invalid")


def _validate_outcome(outcome: Mapping[str, Any]) -> None:
    status = outcome["status"]
    counts = (
        outcome["worker_process_spawn_count"],
        outcome["shell_command_count"],
    )
    if (
        not outcome["task_id"]
        or len(outcome["task_id"]) > 256
        or status not in {"completed", "requeued", "failed"}
        or len(outcome["receipt_id"]) > 256
        or _SHA256_DIGEST.fullmatch(outcome["evidence_digest"]) is None
        or (status == "failed" and outcome["receipt_id"])
        or (status in {"completed", "requeued"} and not outcome["receipt_id"])
        or (
            status in {"completed", "requeued"}
            and outcome["effect_evidence_complete"] is False
        )
        or any(
            isinstance(value, bool) or not isinstance(value, int) or value < 0
            for value in counts
        )
    ):
        raise ValueError("resident_control_loop_receipt_child_outcomes_invalid")


def _reject_projection_conflicts(
    result: Mapping[str, Any],
    receipt_ids: tuple[str, ...],
    evidence_digests: tuple[str, ...],
) -> None:
    supplied_receipts = _strings(result.get("child_execution_receipt_ids"), 256)
    supplied_digests = _strings(
        result.get("child_execution_evidence_digests"), 80
    )
    if supplied_receipts != receipt_ids or supplied_digests != evidence_digests:
        raise ValueError("resident_control_loop_receipt_child_projection_conflict")


def _strings(value: Any, max_chars: int) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        return ()
    return tuple(
        str(item or "").strip()[:max_chars]
        for item in value[:128]
        if str(item or "").strip()
    )


__all__ = ["derive_child_outcome_projections", "strict_child_outcomes"]
