"""Route authenticated HoloIndex owner incidents into existing WRE repair."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Mapping

from holo_index.authority_worktree import (
    HoloIndexAuthoritySelection,
    resolve_holoindex_authority_root,
)
from modules.infrastructure.idle_automation.src.holoindex_postmerge_coordinator import (
    coordinate_holoindex_postmerge,
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
    query_and_classify_owner_result,
)


def _incident_binding(
    owner_failure: Mapping[str, Any], selection: HoloIndexAuthoritySelection
) -> tuple[dict[str, Any], str]:
    error = owner_failure.get("error")
    owner_attempts = owner_failure.get("owner_attempts")
    if (
        owner_failure.get("ok") is not False
        or type(error) is not str
        or error not in REPAIRABLE_ERRORS
        or owner_failure.get("index_gap_detected") is not True
        or owner_failure.get("no_holoindex_reindex_performed") is not True
        or type(owner_attempts) is not int
        or owner_attempts < 2
    ):
        return {}, "holoindex_incident_failure_not_authenticated"
    if not selection.accepted or not selection.selected_root:
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
    return payload, ""


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
        incident_id=incident_id,
        target_repo_head_sha=selection.authority_head_sha,
        authority_root_digest=selection.authority_root_digest,
        generation_id=result["freshness_generation_id"],
        freshness_receipt_digest=result["freshness_receipt_digest"],
        owner_requery_performed=True,
    ))


def _coordination_receipt(
    *,
    coordinated: Any,
    incident_id: str,
    query: str,
    selection: HoloIndexAuthoritySelection,
    query_runner: Callable[..., Mapping[str, Any]] | None,
) -> HoloIndexIncidentRepairReceipt:
    fields = coordination_fields(coordinated)
    if fields is None:
        return rejected_receipt("holoindex_incident_coordinator_result_invalid")
    accepted, status, task_id, target_head, authority_digest, reasons = fields
    if (
        target_head != selection.authority_head_sha
        or authority_digest != selection.authority_root_digest
    ):
        return authority_binding_rejection(
            incident_id=incident_id, task_id=task_id, target_head=target_head,
            authority_digest=authority_digest,
        )
    if accepted and status == "CURRENT":
        query_runner = _query_runner(query_runner)
        owner_status, result = query_and_classify_owner_result(
            query=query, selection=selection, query_runner=query_runner
        )
        if owner_status == CURRENT:
            return _current_owner_receipt(
                incident_id=incident_id, selection=selection, result=result)
        return escalated_receipt(
            "holoindex_owner_failed_after_current_generation_proof",
            incident_id=incident_id, coding_candidate_required=True,
        )
    common = {
        "incident_id": incident_id,
        "task_id": task_id,
        "target_repo_head_sha": selection.authority_head_sha,
        "authority_root_digest": selection.authority_root_digest,
    }
    if accepted and status in DEFERRED_STATUSES:
        receipt = HoloIndexIncidentRepairReceipt(True, status, maintenance_enqueued=True, **common)
        return seal_receipt(receipt)
    return seal_receipt(HoloIndexIncidentRepairReceipt(
        False,
        "ESCALATE",
        coding_candidate_required=True,
        rejection_reasons=reasons or ("holoindex_incident_repair_unavailable",),
        **common,
    ))


def coordinate_holoindex_incident_repair(
    *,
    repo_root: Path | str,
    query: str,
    owner_failure: Mapping[str, Any],
    db: Any | None = None,
    environment: Mapping[str, str] | None = None,
    select_authority: Callable[[Path], HoloIndexAuthoritySelection] = (
        resolve_holoindex_authority_root
    ),
    coordinator: Callable[..., Any] = coordinate_holoindex_postmerge,
    query_runner: Callable[..., Mapping[str, Any]] | None = None,
) -> HoloIndexIncidentRepairReceipt:
    """Create/reconcile one exact-HEAD maintenance task for a proven incident."""

    root = Path(repo_root).resolve(strict=False)
    if type(query) is not str:
        return rejected_receipt("holoindex_incident_query_invalid")
    normalized_query = query.strip()
    if not normalized_query or len(normalized_query) > 16_000:
        return rejected_receipt("holoindex_incident_query_invalid")
    selection = select_authority(root)
    binding, reason = _incident_binding(owner_failure, selection)
    if reason:
        return rejected_receipt(reason)
    incident_id = canonical_digest(binding)
    query_runner = _query_runner(query_runner)
    owner_status, result = query_and_classify_owner_result(
        query=normalized_query, selection=selection, query_runner=query_runner
    )
    if owner_status == CURRENT:
        return _current_owner_receipt(
            incident_id=incident_id, selection=selection, result=result
        )
    if owner_status != REPAIRABLE:
        return rejected_receipt("holoindex_incident_independent_recheck_failed")
    coordinated = coordinator(repo_root=root, db=db, environment=environment)
    return _coordination_receipt(
        coordinated=coordinated,
        incident_id=incident_id,
        query=normalized_query,
        selection=selection,
        query_runner=query_runner,
    )


__all__ = [
    "HoloIndexIncidentRepairReceipt",
    "REPAIRABLE_ERRORS",
    "SCHEMA_VERSION",
    "coordinate_holoindex_incident_repair",
]
