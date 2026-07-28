"""Typed progress and terminal receipts for start-operations controls."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any, Callable, Mapping, Sequence

from modules.communication.moltbot_bridge.src.reddog_grounded_target_assignment_continuity import (
    canonical_digest,
)
from modules.communication.moltbot_bridge.src.reddog_start_operations_profile import (
    PROFILE_ID,
    StartOperationsProfile,
)


RESULT_SCHEMA = "reddog_start_operations_control_result.v1"
PROGRESS_SCHEMA = "reddog_start_operations_progress.v1"
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


@dataclass(frozen=True)
class StartOperationsControlResult:
    schema_version: str
    response_id: str
    accepted: bool
    action: str
    operations_profile_id: str
    intent_id: str
    cycle_id: str
    status: str
    repo_head_sha: str
    architect_action: str
    architect_next_slice: str
    determination_id: str
    task_status_counts: Mapping[str, int]
    duplicate_intent_reused: bool
    recovered_existing_cycle: bool
    deferred_holo_maintenance: bool
    rejection_reasons: tuple[str, ...]
    no_extension_fusion_call_performed: bool = True
    no_maintenance_performed: bool = True
    no_repo_mutation_performed: bool = True
    no_shell_command_executed: bool = True
    no_hermes_dispatch_performed: bool = True
    no_worktree_operation_performed: bool = True
    no_pr_created: bool = True
    no_merge_performed: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def write_progress(
    writer: Callable[[Mapping[str, Any]], None] | None,
    intent: Mapping[str, Any],
    repo_state: Mapping[str, Any],
) -> None:
    if writer is None:
        return
    payload = {
        "schema_version": PROGRESS_SCHEMA,
        "stage": "resident_cycle_submitting",
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
) -> StartOperationsControlResult:
    reasons = tuple(str(item) for item in response.rejection_reasons if str(item))
    boundary_ok = _boundary_ok(response)
    payload = _base_payload(action, profile, repo_state)
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
) -> StartOperationsControlResult:
    payload = _base_payload(action, profile, repo_state)
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
) -> dict[str, Any]:
    return {
        "accepted": False,
        "action": action,
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
    body = {"schema_version": RESULT_SCHEMA, **dict(payload)}
    return StartOperationsControlResult(
        response_id=canonical_digest(body),
        **body,
    )


def result_json(result: StartOperationsControlResult) -> str:
    return json.dumps(result.to_dict(), sort_keys=True, separators=(",", ":"))


__all__ = [
    "PROGRESS_SCHEMA",
    "RESULT_SCHEMA",
    "StartOperationsControlResult",
    "from_client",
    "reject",
    "result_json",
    "write_progress",
]
