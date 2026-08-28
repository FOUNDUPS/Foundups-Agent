"""Route authenticated HoloIndex owner incidents into existing WRE repair."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Mapping

from holo_index.authority_worktree import (
    AUTHORITY_ROOT_HEAD_MISMATCH,
    HoloIndexAuthoritySelection,
    resolve_holoindex_authority_root,
)
from modules.infrastructure.idle_automation.src.holoindex_postmerge_coordinator import (
    coordinate_holoindex_postmerge,
)
from modules.infrastructure.idle_automation.src.holoindex_postmerge_contract import (
    REPO_HEAD_MISMATCH,
    REQUEST_EVENT_PREFIX,
    TASK_PREFIX,
)
from modules.communication.moltbot_bridge.src.reddog_holoindex_incident_repair_contract import (
    DEFERRED_STATUSES,
    HoloIndexIncidentRepairReceipt,
    REPAIRABLE_ERRORS,
    SCHEMA_VERSION,
    authority_binding_rejection,
    canonical_digest,
    coordination_fields,
    escalated_receipt,
    rejected_receipt,
    seal_receipt,
)
from modules.communication.moltbot_bridge.src.reddog_holoindex_owner_result_verification import (
    CURRENT,
    REPAIRABLE,
    is_bound_preowner_repo_head_mismatch,
    query_and_classify_owner_result,
)


def _preowner_incident_fields(owner_failure: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "stale_repo_head_sha": owner_failure["repo_head_sha"],
        "stale_generation_id": owner_failure["freshness_generation_id"],
        "stale_freshness_receipt_digest": owner_failure["freshness_receipt_digest"],
        "stale_reasons": tuple(sorted(owner_failure["stale_reasons"])),
    }


def _same_preowner_failure(
    result: Mapping[str, Any], *, query: str,
    selection: HoloIndexAuthoritySelection, binding: Mapping[str, Any],
) -> bool:
    return bool(
        is_bound_preowner_repo_head_mismatch(
            result, query=query, selection=selection,
        )
        and _preowner_incident_fields(result)
        == {key: binding[key] for key in _preowner_incident_fields(result)}
    )


def _attempts_are_valid(error: object, owner_attempts: object) -> bool:
    if error in (AUTHORITY_ROOT_HEAD_MISMATCH, REPO_HEAD_MISMATCH):
        return type(owner_attempts) is int and owner_attempts == 0
    return type(owner_attempts) is int and owner_attempts >= 2


def _incident_binding(
    owner_failure: Mapping[str, Any], selection: HoloIndexAuthoritySelection,
    *, query: str,
) -> tuple[dict[str, Any], str]:
    error = owner_failure.get("error")
    owner_attempts = owner_failure.get("owner_attempts")
    stale_authority = error == AUTHORITY_ROOT_HEAD_MISMATCH
    preowner_head_mismatch = error == REPO_HEAD_MISMATCH
    if (
        owner_failure.get("ok") is not False
        or type(error) is not str
        or error not in REPAIRABLE_ERRORS
        or owner_failure.get("index_gap_detected") is not True
        or owner_failure.get("no_holoindex_reindex_performed") is not True
        or not _attempts_are_valid(error, owner_attempts)
    ):
        return {}, "holoindex_incident_failure_not_authenticated"
    if preowner_head_mismatch and not is_bound_preowner_repo_head_mismatch(
        owner_failure, query=query, selection=selection,
    ):
        return {}, "holoindex_incident_failure_not_authenticated"
    selection_valid = selection.accepted or (
        stale_authority
        and selection.error == AUTHORITY_ROOT_HEAD_MISMATCH
        and selection.workspace_head_sha != selection.authority_head_sha
        and bool(selection.authority_head_sha)
        and bool(selection.authority_root_digest)
    )
    if not selection_valid or not selection.selected_root:
        return {}, "holoindex_incident_authority_unavailable"
    expected = {
        "workspace_repo_head_sha": selection.workspace_head_sha,
        "authority_repo_head_sha": selection.authority_head_sha,
        "authority_repo_root_digest": selection.authority_root_digest,
    }
    if any(owner_failure.get(key) != value for key, value in expected.items()):
        return {}, "holoindex_incident_authority_binding_mismatch"
    if owner_failure.get("no_authority_worktree_mutation_performed") is not True:
        return {}, "holoindex_incident_authority_mutation_claim_missing"
    payload = {
        "schema_version": SCHEMA_VERSION,
        "owner_error": error,
        **expected,
    }
    if preowner_head_mismatch:
        payload.update(_preowner_incident_fields(owner_failure))
    return payload, ""


def _target_head(
    binding: Mapping[str, Any], selection: HoloIndexAuthoritySelection
) -> str:
    return (
        selection.workspace_head_sha
        if binding.get("owner_error") == AUTHORITY_ROOT_HEAD_MISMATCH
        else selection.authority_head_sha
    )


def _durable_incident_binding(
    binding: Mapping[str, Any], incident_id: str,
) -> dict[str, str]:
    return {
        "schema_version": binding["schema_version"],
        "incident_kind": binding["owner_error"],
        "incident_id": incident_id,
        "workspace_repo_head_sha": binding["workspace_repo_head_sha"],
        "observed_authority_head_sha": binding["authority_repo_head_sha"],
    }


def _query_runner(value: Callable[..., Mapping[str, Any]] | None) -> Callable:
    if value is not None:
        return value
    from scripts.reddog_holoindex_owner_query_once import query_once
    return query_once

def _current_owner_receipt(
    *,
    incident_id: str,
    selection: HoloIndexAuthoritySelection,
    result: Mapping[str, Any],
) -> HoloIndexIncidentRepairReceipt:
    return seal_receipt(HoloIndexIncidentRepairReceipt(
        True,
        "OWNER_READY",
        incident_kind="OWNER_CURRENT",
        incident_id=incident_id,
        target_repo_head_sha=selection.authority_head_sha,
        workspace_repo_head_sha=selection.workspace_head_sha,
        observed_authority_head_sha=selection.authority_head_sha,
        authority_root_digest=selection.authority_root_digest,
        generation_id=result["freshness_generation_id"],
        freshness_receipt_digest=result["freshness_receipt_digest"],
        owner_requery_performed=True,
    ))


def _coordination_receipt(
    *, coordinated: Any, incident_id: str, query: str, workspace_repo_root: Path,
    selection: HoloIndexAuthoritySelection, expected_target_head: str,
    binding: Mapping[str, Any], query_runner: Callable[..., Mapping[str, Any]] | None,
) -> HoloIndexIncidentRepairReceipt:
    fields = coordination_fields(coordinated)
    if fields is None:
        return rejected_receipt("holoindex_incident_coordinator_result_invalid")
    accepted, status, task_id, target_head, authority_digest, reasons = fields
    if (
        task_id != TASK_PREFIX + expected_target_head or target_head != expected_target_head
        or authority_digest != selection.authority_root_digest
    ):
        return authority_binding_rejection(
            incident_id=incident_id, task_id=task_id, target_head=target_head,
            authority_digest=authority_digest,
        )
    if accepted and status == "CURRENT":
        query_runner = _query_runner(query_runner)
        owner_status, result = query_and_classify_owner_result(
            query=query, selection=selection,
            workspace_repo_root=workspace_repo_root,
            query_runner=query_runner,
        )
        if owner_status == CURRENT:
            return _current_owner_receipt(
                incident_id=incident_id, selection=selection, result=result)
        return escalated_receipt(
            "holoindex_owner_failed_after_current_generation_proof",
            incident_id=incident_id, coding_candidate_required=True,
        )
    common = {
        "incident_kind": binding["owner_error"],
        "incident_id": incident_id,
        "task_id": task_id,
        "request_event_id": REQUEST_EVENT_PREFIX + expected_target_head,
        "target_repo_head_sha": expected_target_head,
        "workspace_repo_head_sha": binding["workspace_repo_head_sha"],
        "observed_authority_head_sha": binding["authority_repo_head_sha"],
        "authority_root_digest": selection.authority_root_digest,
    }
    if accepted and status in DEFERRED_STATUSES:
        receipt = HoloIndexIncidentRepairReceipt(True, status, maintenance_enqueued=True, **common)
        return seal_receipt(receipt)
    return seal_receipt(HoloIndexIncidentRepairReceipt(
        False, "ESCALATE",
        coding_candidate_required=True,
        rejection_reasons=reasons or ("holoindex_incident_repair_unavailable",),
        **common,
    ))


def _validate_query(query: object) -> str | None:
    if type(query) is not str:
        return None
    normalized = query.strip()
    return normalized if normalized and len(normalized) <= 16_000 else None


def _incident_recheck(
    *, query: str, workspace_repo_root: Path,
    selection: HoloIndexAuthoritySelection,
    query_runner: Callable[..., Mapping[str, Any]], incident_id: str,
    expected_binding: Mapping[str, Any],
) -> HoloIndexIncidentRepairReceipt | None:
    owner_status, result = query_and_classify_owner_result(
        query=query, selection=selection,
        workspace_repo_root=workspace_repo_root,
        query_runner=query_runner,
    )
    if owner_status == CURRENT:
        return _current_owner_receipt(
            incident_id=incident_id, selection=selection, result=result
        )
    expected_error = expected_binding["owner_error"]
    preowner_match = expected_error == REPO_HEAD_MISMATCH and _same_preowner_failure(
        result, query=query, selection=selection, binding=expected_binding,
    )
    status_valid = (
        preowner_match
        if expected_error == REPO_HEAD_MISMATCH
        else owner_status == REPAIRABLE
    )
    if not status_valid or result.get("error") != expected_error:
        return rejected_receipt("holoindex_incident_independent_recheck_failed")
    return None


def _refresh_stale_authority(
    *, root: Path, expected_head: str, original_digest: str,
    select_authority: Callable[[Path], HoloIndexAuthoritySelection],
    incident_id: str,
) -> tuple[HoloIndexAuthoritySelection | None, HoloIndexIncidentRepairReceipt | None]:
    selection = select_authority(root)
    valid = bool(
        selection.accepted
        and selection.workspace_head_sha == expected_head
        and selection.authority_head_sha == expected_head
        and selection.authority_root_digest == original_digest
    )
    if valid:
        return selection, None
    return None, escalated_receipt(
        "holoindex_authority_still_stale_after_current_proof",
        incident_id=incident_id,
        coding_candidate_required=True,
    )


def coordinate_holoindex_incident_repair(
    *, repo_root: Path | str, query: str,
    owner_failure: Mapping[str, Any], db: Any | None = None,
    environment: Mapping[str, str] | None = None,
    select_authority: Callable[[Path], HoloIndexAuthoritySelection] = resolve_holoindex_authority_root,
    coordinator: Callable[..., Any] = coordinate_holoindex_postmerge,
    query_runner: Callable[..., Mapping[str, Any]] | None = None,
) -> HoloIndexIncidentRepairReceipt:
    """Create/reconcile one exact-HEAD maintenance task for a proven incident."""
    normalized_query = _validate_query(query)
    if normalized_query is None:
        return rejected_receipt("holoindex_incident_query_invalid")
    root = Path(repo_root).resolve(strict=False)
    selection = select_authority(root)
    binding, reason = _incident_binding(owner_failure, selection, query=normalized_query)
    if reason:
        return rejected_receipt(reason)
    incident_id = canonical_digest(binding)
    query_runner = _query_runner(query_runner)
    stale_authority = binding["owner_error"] == AUTHORITY_ROOT_HEAD_MISMATCH
    if not stale_authority:
        recheck = _incident_recheck(
            query=normalized_query, workspace_repo_root=root, selection=selection,
            query_runner=query_runner, incident_id=incident_id, expected_binding=binding,
        )
        if recheck is not None:
            return recheck
    expected_target_head = _target_head(binding, selection)
    coordinated = coordinator(
        repo_root=root, db=db, environment=environment,
        incident_binding=_durable_incident_binding(binding, incident_id),
    )
    fields = coordination_fields(coordinated)
    if fields is not None and fields[1] == "CURRENT" and stale_authority:
        refreshed, failure = _refresh_stale_authority(
            root=root, expected_head=expected_target_head,
            original_digest=selection.authority_root_digest,
            select_authority=select_authority, incident_id=incident_id,
        )
        if failure is not None:
            return failure
        selection = refreshed
    return _coordination_receipt(
        coordinated=coordinated, incident_id=incident_id, query=normalized_query,
        workspace_repo_root=root,
        selection=selection,
        expected_target_head=expected_target_head,
        binding=binding,
        query_runner=query_runner,
    )


__all__ = [
    "HoloIndexIncidentRepairReceipt",
    "REPAIRABLE_ERRORS",
    "SCHEMA_VERSION",
    "coordinate_holoindex_incident_repair",
]
