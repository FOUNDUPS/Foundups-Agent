"""Bounded status/cancel compatibility for persisted main-host v1 intents."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Optional, Sequence

from modules.communication.moltbot_bridge.src.reddog_resident_architect_durable_agentdb_cycle import (
    RUNTIME_BOUNDARY_FIELDS,
    STATUS_CANCELLED,
    STATUS_ENQUEUED,
    STATUS_RUNNING,
    STATUS_SUBMITTED,
    TERMINAL_STATUSES,
    ResidentArchitectCycleStore,
    ResidentCycleReason,
    resident_intent_digest,
)


REQUEST_INVALID = "REJECT_REDDOG_RESIDENT_CLIENT_REQUEST_INVALID"
PRINCIPAL_MISMATCH = "REJECT_REDDOG_RESIDENT_CLIENT_PRINCIPAL_MISMATCH"
SOURCE_MISMATCH = "REJECT_REDDOG_RESIDENT_CLIENT_SOURCE_MISMATCH"
FOUNDUP_SCOPE_MISMATCH = "REJECT_REDDOG_RESIDENT_CLIENT_FOUNDUP_SCOPE_MISMATCH"
CYCLE_NOT_FOUND = "REJECT_REDDOG_RESIDENT_CLIENT_CYCLE_NOT_FOUND"
RUNTIME_FAILED = "REJECT_REDDOG_RESIDENT_CLIENT_RUNTIME_FAILED"


def authorize_legacy_main_record(
    store: ResidentArchitectCycleStore,
    intent_id: str,
    *,
    authenticated_principal_id: str,
    authorized_foundup_ids: Sequence[str],
    transport: str,
) -> tuple[Optional[Mapping[str, Any]], tuple[str, ...]]:
    """Authorize only the historical main.py read-only v1 shape."""

    value = str(intent_id or "").strip()
    record = store.load_cycle_by_intent(value) if value else None
    if not isinstance(record, Mapping):
        return None, (CYCLE_NOT_FOUND,)
    intent = _record_intent(record)
    reasons: list[str] = []
    if transport != "main":
        reasons.append(SOURCE_MISMATCH)
    cycle_schema = str(record.get("schema_version") or "")
    if (
        cycle_schema not in {
            "reddog_resident_architect_cycle.v1",
            "reddog_resident_architect_cycle.v2",
        }
        or intent.get("schema_version") != "reddog_intent.v1"
        or intent.get("origin") != "main.py"
        or intent.get("requested_authority") != "read_only_audit"
        or intent.get("submits_executable_authority") is not False
        or str(record.get("intent_id") or "") != value
        or _intent_id(intent) != value
    ):
        reasons.append(REQUEST_INVALID)
    if _principal_id(intent) != str(authenticated_principal_id or "").strip():
        reasons.append(PRINCIPAL_MISMATCH)
    if str(intent.get("foundup_id") or "").strip() not in {
        str(item).strip() for item in authorized_foundup_ids if str(item).strip()
    }:
        reasons.append(FOUNDUP_SCOPE_MISMATCH)
    if cycle_schema == "reddog_resident_architect_cycle.v2":
        if str(record.get("intent_digest") or "") != resident_intent_digest(intent):
            reasons.append(REQUEST_INVALID)
        if (
            record.get("_store_integrity_valid") is not True
            or not _runtime_boundary_is_safe(record)
        ):
            reasons.append(RUNTIME_FAILED)
    elif not _legacy_v1_integrity_is_acceptable(record):
        reasons.append(RUNTIME_FAILED)
    unique = tuple(dict.fromkeys(reasons))
    return (None, unique) if unique else (record, ())


def cancel_legacy_main_record(
    store: ResidentArchitectCycleStore,
    record: Mapping[str, Any],
    *,
    authorized_intent_id: str,
) -> tuple[Optional[Mapping[str, Any]], tuple[str, ...]]:
    """CAS-cancel an authorized nonterminal legacy record without resubmission."""

    intent_id = str(authorized_intent_id or "").strip()
    if (
        not intent_id
        or str(record.get("intent_id") or "") != intent_id
        or _intent_id(_record_intent(record)) != intent_id
    ):
        return None, (REQUEST_INVALID,)
    status = str(record.get("status") or "")
    if status == STATUS_CANCELLED:
        return record, ()
    if status in TERMINAL_STATUSES or status not in {
        STATUS_SUBMITTED,
        STATUS_ENQUEUED,
        STATUS_RUNNING,
    }:
        return None, (RUNTIME_FAILED,)
    transitioned = store.transition_cycle(
        intent_id,
        expected_revision=int(
            record.get("record_revision")
            if record.get("record_revision") is not None
            else record.get("_store_revision") or 0
        ),
        expected_statuses=(status,),
        updates={
            "status": STATUS_CANCELLED,
            "rejection_reasons": [ResidentCycleReason.CANCELLED],
        },
    )
    updated = transitioned.get("record") if isinstance(transitioned, Mapping) else None
    if (
        transitioned.get("ok") is not True
        or not isinstance(updated, Mapping)
        or str(updated.get("intent_id") or "") != intent_id
        or _intent_id(_record_intent(updated)) != intent_id
    ):
        return None, (RUNTIME_FAILED,)
    return updated, ()


def _record_intent(record: Mapping[str, Any]) -> Mapping[str, Any]:
    intent = record.get("intent")
    return dict(intent) if isinstance(intent, Mapping) else {}


def _intent_id(intent: Mapping[str, Any]) -> str:
    return str(intent.get("intent_id") or "")


def _principal_id(intent: Mapping[str, Any]) -> str:
    return str(
        intent.get("principal_id")
        or intent.get("principal_ref")
        or intent.get("origin_principal")
        or ""
    ).strip()


def _runtime_boundary_is_safe(record: Mapping[str, Any]) -> bool:
    return all(record.get(key) is True for key in RUNTIME_BOUNDARY_FIELDS)


def _legacy_v1_integrity_is_acceptable(record: Mapping[str, Any]) -> bool:
    """Recognize only the historical read-only row shape for status/cancel."""

    if (
        str(record.get("cycle_id") or "") == ""
        or record.get("read_only_authority_only") is not True
        or str(record.get("status") or "")
        not in {
            STATUS_SUBMITTED,
            STATUS_ENQUEUED,
            STATUS_RUNNING,
            *TERMINAL_STATUSES,
        }
        or "intent_digest" in record
    ):
        return False
    if any(record.get(field) is False for field in RUNTIME_BOUNDARY_FIELDS if field in record):
        return False
    if any(
        record.get(field) is True
        for field in (
            "shell_command_executed",
            "repo_mutation_performed",
            "holoindex_reindex_performed",
            "hermes_dispatch_performed",
            "worktree_operation_performed",
            "pr_created",
            "merge_performed",
        )
    ):
        return False
    if "record_revision" in record:
        return (
            record.get("_store_integrity_valid") is True
            or _legacy_cancel_transition_is_valid(record)
        )
    return int(record.get("_store_revision", -1)) >= 0 and not record.get(
        "transition_history"
    )


def _legacy_cancel_transition_is_valid(record: Mapping[str, Any]) -> bool:
    history = record.get("transition_history")
    if (
        record.get("status") != STATUS_CANCELLED
        or int(record.get("record_revision", -1)) != 1
        or int(record.get("_store_revision", -1)) != 1
        or not isinstance(history, list)
        or len(history) != 1
        or not isinstance(history[0], Mapping)
    ):
        return False
    entry = dict(history[0])
    receipt_id = str(entry.pop("receipt_id", ""))
    expected_updates = {
        "status": STATUS_CANCELLED,
        "rejection_reasons": [ResidentCycleReason.CANCELLED],
    }
    state_for_digest = dict(record)
    state_for_digest.pop("transition_history", None)
    state_for_digest.pop("_store_integrity_valid", None)
    state_for_digest.pop("_store_revision", None)
    return bool(
        entry.get("schema_version") == "reddog_resident_cycle_transition.v1"
        and entry.get("intent_id") == record.get("intent_id")
        and entry.get("cycle_id") == record.get("cycle_id")
        and entry.get("from_status")
        in {STATUS_SUBMITTED, STATUS_ENQUEUED, STATUS_RUNNING}
        and entry.get("to_status") == STATUS_CANCELLED
        and entry.get("from_revision") == 0
        and entry.get("to_revision") == 1
        and entry.get("previous_receipt_id") == ""
        and entry.get("authority") == "observational_internal_integrity_only"
        and entry.get("updates_digest") == _digest(expected_updates)
        and entry.get("result_state_digest") == _digest(state_for_digest)
        and receipt_id == _digest(entry)
    )


def _digest(payload: Any) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=str,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


__all__ = [
    "authorize_legacy_main_record",
    "cancel_legacy_main_record",
]
