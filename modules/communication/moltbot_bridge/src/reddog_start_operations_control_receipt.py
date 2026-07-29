"""Typed progress and terminal receipts for start-operations controls."""

from __future__ import annotations

from typing import Any, Callable, Mapping, Sequence

from modules.communication.moltbot_bridge.src.reddog_grounded_target_assignment_continuity import (
    canonical_digest,
)
from modules.communication.moltbot_bridge.src.reddog_start_operations_profile import (
    PROFILE_ID,
    StartOperationsProfile,
)
from modules.communication.moltbot_bridge.src.reddog_start_operations_result import (
    EFFECT_EVIDENCE_LEVEL,
    PROGRESS_SCHEMA,
    RESULT_SCHEMA,
    StartOperationsControlResult,
    result_json,
)
HOLO_REASON_TOKENS = ("holoindex", "grounding_holo")
CLIENT_BOUNDARY_FIELDS = (
    ("no_maintenance_performed", "client_no_holoindex_reindex_performed"),
    ("no_repo_mutation_performed", "client_no_repo_mutation_performed"),
    ("no_shell_command_executed", "client_no_shell_command_executed"),
    ("no_hermes_dispatch_performed", "client_no_hermes_execution_performed"),
    ("no_worktree_operation_performed", "client_no_worktree_operation_performed"),
    ("no_pr_created", "client_no_pr_created"),
    ("no_merge_performed", "client_no_merge_performed"),
)


def write_progress(
    writer: Callable[[Mapping[str, Any]], None] | None,
    intent: Mapping[str, Any],
    repo_state: Mapping[str, Any],
    action: str,
    control_request_id: str,
) -> None:
    if writer is None:
        return
    payload = {
        "schema_version": PROGRESS_SCHEMA,
        "stage": "resident_cycle_submitting",
        "action": action,
        "control_request_id": control_request_id,
        "intent_id": str(intent.get("intent_id") or ""),
        "repo_head_sha": str(repo_state.get("head_sha") or ""),
        "operations_profile_id": PROFILE_ID,
    }
    writer({**payload, "progress_id": canonical_digest(payload)})


def from_client(
    action: str,
    profile: StartOperationsProfile,
    repo_state: Mapping[str, Any],
    response: Any,
    control_request_id: str,
) -> StartOperationsControlResult:
    reasons = tuple(str(item) for item in response.rejection_reasons if str(item))
    boundary_ok = _boundary_ok(response)
    payload = _base_payload(action, profile, repo_state, control_request_id)
    payload.update(
        {
            "accepted": bool(response.accepted) and boundary_ok,
            "intent_id": str(response.intent_id or ""),
            "cycle_id": str(response.cycle_id or ""),
            "status": str(response.status or ""),
            "architect_action": str(response.architect_action or ""),
            "architect_next_slice": str(response.architect_next_slice or ""),
            "determination_id": str(response.determination_id or ""),
            "task_status_counts": dict(response.task_status_counts or {}),
            "duplicate_intent_reused": bool(response.duplicate_intent_reused),
            "recovered_existing_cycle": bool(response.recovered_existing_cycle),
            "deferred_holo_maintenance": _holo_deferred(reasons),
            "rejection_reasons": reasons
            if boundary_ok
            else (*reasons, "runtime_boundary_invalid"),
            **_client_boundary_payload(response),
        }
    )
    return _result(payload)


def reject(
    action: str,
    profile: StartOperationsProfile,
    repo_state: Mapping[str, Any],
    reasons: Sequence[str],
    *,
    intent_id: str = "",
    control_request_id: str = "",
) -> StartOperationsControlResult:
    payload = _base_payload(action, profile, repo_state, control_request_id)
    payload.update(
        {
            "accepted": False,
            "intent_id": intent_id,
            "status": "DEFERRED" if _holo_deferred(reasons) else "REJECTED",
            "deferred_holo_maintenance": _holo_deferred(reasons),
            "rejection_reasons": tuple(reasons),
        }
    )
    return _result(payload)


def _base_payload(
    action: str,
    profile: StartOperationsProfile,
    repo_state: Mapping[str, Any],
    control_request_id: str,
) -> dict[str, Any]:
    return {
        "accepted": False,
        "action": action,
        "control_request_id": control_request_id,
        "operations_profile_id": profile.profile_id,
        "intent_id": "",
        "cycle_id": "",
        "status": "",
        "repo_head_sha": str(repo_state.get("head_sha") or ""),
        "architect_action": "",
        "architect_next_slice": "",
        "determination_id": "",
        "task_status_counts": {},
        "duplicate_intent_reused": False,
        "recovered_existing_cycle": False,
        "deferred_holo_maintenance": False,
        "rejection_reasons": (),
    }


def _boundary_ok(response: Any) -> bool:
    return all(
        bool(getattr(response, source, False))
        for _, source in CLIENT_BOUNDARY_FIELDS
    )


def _client_boundary_payload(response: Any) -> dict[str, bool]:
    return {
        target: bool(getattr(response, source, False))
        for target, source in CLIENT_BOUNDARY_FIELDS
    }


def _holo_deferred(reasons: Sequence[str]) -> bool:
    return any(
        token in str(reason).lower()
        for reason in reasons
        for token in HOLO_REASON_TOKENS
    )


def _result(payload: Mapping[str, Any]) -> StartOperationsControlResult:
    body = {
        "schema_version": RESULT_SCHEMA,
        "effect_evidence_level": EFFECT_EVIDENCE_LEVEL,
        "no_extension_fusion_call_performed": True,
        "no_maintenance_performed": True,
        "no_repo_mutation_performed": True,
        "no_shell_command_executed": True,
        "no_hermes_dispatch_performed": True,
        "no_worktree_operation_performed": True,
        "no_pr_created": True,
        "no_merge_performed": True,
        **dict(payload),
    }
    return StartOperationsControlResult(
        response_id=canonical_digest(body),
        **body,
    )


__all__ = [
    "PROGRESS_SCHEMA",
    "RESULT_SCHEMA",
    "StartOperationsControlResult",
    "from_client",
    "reject",
    "result_json",
    "write_progress",
]
