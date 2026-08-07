"""One-use admission binding for a Holo-blocked RedDog editor request."""

from __future__ import annotations

import re
import time
from dataclasses import fields, replace
from pathlib import Path
from typing import Any, Callable, Mapping

from holo_index.authority_worktree import resolve_holoindex_authority_root
from modules.communication.moltbot_bridge.src.reddog_holoindex_incident_repair_contract import (
    DEFERRED_STATUSES,
    HoloIndexIncidentRepairReceipt,
    canonical_digest,
    seal_receipt,
)
from modules.communication.moltbot_bridge.src.reddog_holoindex_owner_result_verification import (
    CURRENT,
    query_and_classify_owner_result,
)
from modules.communication.moltbot_bridge.src.reddog_holoindex_blocked_request_recovery_events import (
    admit_ready,
    build_stage_payload,
    stage_matches,
    stage_once,
)
from modules.infrastructure.idle_automation.src.holoindex_postmerge_contract import (
    TASK_PREFIX,
    validate_holoindex_postmerge_completion,
)


READY = "READY"
WAITING = "WAITING"
REJECTED = "REJECTED"
STAGED = "STAGED"
INCIDENT_FIELDS = frozenset(item.name for item in fields(HoloIndexIncidentRepairReceipt))
DIGEST_RE = re.compile(r"sha256:[0-9a-f]{64}\Z")
GIT_SHA_RE = re.compile(r"[0-9a-f]{40}\Z")
REQUEST_SCHEMA = "reddog_holoindex_blocked_request_recovery.v1"
MAX_AGE_MS = 30 * 60 * 1000
REQUEST_FIELDS = frozenset(
    {"command", "text", "contextMode", "workerType", "effort", "mode", "useLastPacket"}
)


def _incident_types_valid(value: Mapping[str, Any]) -> bool:
    bool_fields = (
        "accepted", "maintenance_enqueued", "owner_requery_performed",
        "coding_candidate_required",
    )
    str_fields = (
        "status", "incident_id", "task_id", "target_repo_head_sha",
        "authority_root_digest", "generation_id", "freshness_receipt_digest",
        "receipt_id",
    )
    reasons = value.get("rejection_reasons")
    return bool(
        all(type(value.get(name)) is bool for name in bool_fields)
        and all(type(value.get(name)) is str for name in str_fields)
        and isinstance(reasons, (list, tuple))
        and all(type(reason) is str for reason in reasons)
    )


def _rehydrate_incident(value: Mapping[str, Any]) -> HoloIndexIncidentRepairReceipt | None:
    if set(value) != INCIDENT_FIELDS or not _incident_types_valid(value):
        return None
    try:
        receipt = HoloIndexIncidentRepairReceipt(
            **{**value, "rejection_reasons": tuple(value["rejection_reasons"])}
        )
        expected = seal_receipt(replace(receipt, receipt_id=""))
    except (TypeError, ValueError):
        return None
    return receipt if receipt.receipt_id == expected.receipt_id else None


def _incident_valid(receipt: HoloIndexIncidentRepairReceipt | None) -> bool:
    return bool(
        receipt
        and receipt.accepted
        and receipt.status in DEFERRED_STATUSES
        and receipt.maintenance_enqueued
        and DIGEST_RE.fullmatch(receipt.incident_id)
        and DIGEST_RE.fullmatch(receipt.receipt_id)
        and DIGEST_RE.fullmatch(receipt.authority_root_digest)
        and GIT_SHA_RE.fullmatch(receipt.target_repo_head_sha)
        and receipt.task_id == TASK_PREFIX + receipt.target_repo_head_sha
    )


def _query_runner(value: Callable[..., Mapping[str, Any]] | None) -> Callable:
    if value is not None:
        return value
    from scripts.reddog_holoindex_owner_query_once import query_once

    return query_once


def _request_binding_valid(
    *, request: Mapping[str, Any], query: str, request_digest: str,
    query_digest: str, recovery_id: str, incident_receipt_id: str,
    created_at_epoch_ms: int, expires_at_epoch_ms: int, now_epoch_ms: int,
) -> bool:
    string_fields = REQUEST_FIELDS - {"useLastPacket"}
    if (
        set(request) != REQUEST_FIELDS
        or type(created_at_epoch_ms) is not int
        or type(expires_at_epoch_ms) is not int
        or not all(
        type(request.get(name)) is str for name in string_fields
        )
    ):
        return False
    expected_recovery = canonical_digest({
        "request_digest": request_digest, "incident_receipt_id": incident_receipt_id,
    })
    return bool(
        request.get("command") == "ask" and request.get("text") == query
        and request.get("useLastPacket") is False
        and request_digest == canonical_digest({"schema_version": REQUEST_SCHEMA, "request": dict(request)})
        and query_digest == canonical_digest({"query": query})
        and recovery_id == expected_recovery
        and expires_at_epoch_ms == created_at_epoch_ms + MAX_AGE_MS
        and created_at_epoch_ms <= now_epoch_ms < expires_at_epoch_ms
    )


def _result(status: str, reason: str = "", **values: Any) -> Mapping[str, Any]:
    return {"ok": status in {READY, STAGED}, "status": status, "reason": reason, **values}


def _authority_selection(
    repo_root: Path | str, receipt: HoloIndexIncidentRepairReceipt
) -> tuple[Any, bool]:
    selection = resolve_holoindex_authority_root(Path(repo_root).resolve(strict=False))
    matched = bool(
        selection.accepted
        and selection.authority_head_sha == receipt.target_repo_head_sha
        and selection.authority_root_digest == receipt.authority_root_digest
    )
    return selection, matched


def _completion_state(
    database: Any, receipt: HoloIndexIncidentRepairReceipt
) -> tuple[str, Mapping[str, Any] | None]:
    task = database.get_autonomous_task_by_id(receipt.task_id)
    if not isinstance(task, Mapping) or task.get("status") != "completed":
        return WAITING, None
    completion = validate_holoindex_postmerge_completion(
        database,
        task_id=receipt.task_id,
        target_repo_head_sha=receipt.target_repo_head_sha,
        authority_root_digest=receipt.authority_root_digest,
    )
    return (READY, completion) if completion is not None else (REJECTED, None)


def _load_database(database: Any | None) -> Any:
    if database is not None:
        return database
    from modules.infrastructure.database.src.agent_db import AgentDB

    return AgentDB()


def _stage_payload(
    *, receipt: HoloIndexIncidentRepairReceipt, recovery_id: str,
    request_digest: str, query_digest: str, created_at_epoch_ms: int,
    expires_at_epoch_ms: int,
) -> dict[str, Any]:
    return build_stage_payload(
        schema_version=REQUEST_SCHEMA, recovery_id=recovery_id,
        request_digest=request_digest, query_digest=query_digest,
        incident_id=receipt.incident_id, incident_receipt_id=receipt.receipt_id,
        task_id=receipt.task_id, target_repo_head_sha=receipt.target_repo_head_sha,
        authority_root_digest=receipt.authority_root_digest,
        created_at_epoch_ms=created_at_epoch_ms,
        expires_at_epoch_ms=expires_at_epoch_ms,
    )


def _owner_matches_completion(
    *,
    query: str,
    selection: Any,
    completion: Mapping[str, Any],
    query_runner: Callable[..., Mapping[str, Any]] | None,
) -> tuple[bool, Mapping[str, Any]]:
    status, owner = query_and_classify_owner_result(
        query=query, selection=selection, query_runner=_query_runner(query_runner)
    )
    matches = bool(
        status == CURRENT
        and owner.get("freshness_generation_id") == completion.get("generation_id")
        and owner.get("freshness_receipt_digest")
        == completion.get("freshness_receipt_digest")
    )
    return matches, owner


def stage_holo_blocked_request_recovery(
    *, repo_root: Path | str, query: str, request: Mapping[str, Any],
    recovery_id: str, request_digest: str, query_digest: str,
    created_at_epoch_ms: int, expires_at_epoch_ms: int,
    incident_receipt: Mapping[str, Any], db: Any | None = None,
    now_epoch_ms: int | None = None,
) -> Mapping[str, Any]:
    """Persist one immutable request commitment without raw prompt material."""
    receipt = _rehydrate_incident(incident_receipt)
    now = int(time.time() * 1000) if now_epoch_ms is None else now_epoch_ms
    if type(query) is not str or not query.strip() or len(query) > 16_000:
        return _result(REJECTED, "recovery_query_invalid")
    if not _incident_valid(receipt) or not _request_binding_valid(
        request=request, query=query, request_digest=request_digest,
        query_digest=query_digest, recovery_id=recovery_id,
        incident_receipt_id=receipt.receipt_id if receipt else "",
        created_at_epoch_ms=created_at_epoch_ms,
        expires_at_epoch_ms=expires_at_epoch_ms, now_epoch_ms=now,
    ):
        return _result(REJECTED, "recovery_stage_binding_invalid")
    _selection, matched = _authority_selection(repo_root, receipt)
    if not matched:
        return _result(REJECTED, "recovery_authority_binding_changed")
    payload = _stage_payload(
        receipt=receipt, recovery_id=recovery_id, request_digest=request_digest,
        query_digest=query_digest, created_at_epoch_ms=created_at_epoch_ms,
        expires_at_epoch_ms=expires_at_epoch_ms,
    )
    status, event_id = stage_once(_load_database(db), payload)
    reason = "" if status == STAGED else "recovery_stage_conflict"
    return _result(status, reason, stage_event_id=event_id,
                   stage_payload_digest=payload["payload_digest"],
                   authority_effect="none")


def admit_holo_blocked_request_recovery(
    *, repo_root: Path | str, query: str, request: Mapping[str, Any],
    recovery_id: str, request_digest: str, query_digest: str,
    created_at_epoch_ms: int, expires_at_epoch_ms: int,
    incident_receipt: Mapping[str, Any],
    db: Any | None = None,
    query_runner: Callable[..., Mapping[str, Any]] | None = None,
    now_epoch_ms: int | None = None,
) -> Mapping[str, Any]:
    """Admit one retry after exact maintenance and owner-generation proof."""

    if type(query) is not str or not query.strip() or len(query) > 16_000:
        return _result(REJECTED, "recovery_query_invalid")
    receipt = _rehydrate_incident(incident_receipt)
    if not _incident_valid(receipt):
        return _result(REJECTED, "recovery_incident_receipt_invalid")
    if not _request_binding_valid(
        request=request, query=query, request_digest=request_digest,
        query_digest=query_digest, recovery_id=recovery_id,
        incident_receipt_id=receipt.receipt_id,
        created_at_epoch_ms=created_at_epoch_ms,
        expires_at_epoch_ms=expires_at_epoch_ms,
        now_epoch_ms=int(time.time() * 1000) if now_epoch_ms is None else now_epoch_ms,
    ):
        return _result(REJECTED, "recovery_request_binding_invalid")
    selection, authority_matched = _authority_selection(repo_root, receipt)
    if not authority_matched:
        return _result(REJECTED, "recovery_authority_binding_changed")
    database = _load_database(db)
    stage_payload = _stage_payload(
        receipt=receipt, recovery_id=recovery_id, request_digest=request_digest,
        query_digest=query_digest, created_at_epoch_ms=created_at_epoch_ms,
        expires_at_epoch_ms=expires_at_epoch_ms,
    )
    if not stage_matches(database, stage_payload):
        return _result(REJECTED, "recovery_stage_binding_missing")
    completion_status, completion = _completion_state(database, receipt)
    if completion_status == REJECTED:
        return _result(REJECTED, "recovery_maintenance_completion_invalid")
    if completion_status == WAITING or completion is None:
        return _result(WAITING, "recovery_maintenance_not_completed")
    matched, _owner = _owner_matches_completion(
        query=query.strip(), selection=selection, completion=completion,
        query_runner=query_runner,
    )
    if not matched:
        return _result(WAITING, "recovery_completion_generation_not_active")
    return admit_ready(
        database, receipt, completion, stage_payload
    )


__all__ = [
    "READY", "REJECTED", "STAGED", "WAITING",
    "admit_holo_blocked_request_recovery", "stage_holo_blocked_request_recovery",
]
