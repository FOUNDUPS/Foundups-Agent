"""RedDog worker-claim gate dry-run.

This is the layer between lane reconciliation and future worker assignment. It
turns a LaneReconciliationReport into a claim-ready receipt only when the work
state is fresh, non-contradictory, and the selected slice is actually open.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

from modules.communication.moltbot_bridge.src.reddog_lane_state_reconciler import (
    LaneReconciliationReport,
    LaneSliceRecord,
)


CLAIM_READY_DRYRUN = "CLAIM_READY_DRYRUN"
CLAIM_REJECTED = "CLAIM_REJECTED"


@dataclass(frozen=True)
class RedDogWorkerClaimDryRunReceipt:
    """Dry-run claim receipt. No durable claim or worker assignment is made."""

    claim_id: str
    decision: str
    selected_slice: Optional[str]
    worker_id: Optional[str]
    lane_id: Optional[str]
    reconciliation_report_id: str
    recommended_action: str
    rejection_reasons: Tuple[str, ...]
    stale_sources: Tuple[str, ...]
    conflict_slice_ids: Tuple[str, ...]
    closed_groundwork: Tuple[str, ...]
    open_target: Tuple[str, ...]
    not_this_slice: Tuple[str, ...]
    no_ledger_mutation_performed: bool = True
    no_agentdb_mutation_performed: bool = True
    no_holoindex_mutation_performed: bool = True
    no_worker_assignment_performed: bool = True
    no_worker_spawn_performed: bool = True
    no_execution_performed: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RedDogWorkerClaimDryRunDecision:
    """Decision wrapper returned by the claim gate."""

    accepted: bool
    receipt: RedDogWorkerClaimDryRunReceipt

    def to_dict(self) -> Dict[str, Any]:
        return {
            "accepted": self.accepted,
            "receipt": self.receipt.to_dict(),
        }


def _canonical_digest(payload: Dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _open_slice_ids(report: LaneReconciliationReport) -> Tuple[str, ...]:
    return tuple(dict.fromkeys(record.slice_id for record in report.open_slices))


def _closed_slice_ids(report: LaneReconciliationReport) -> Tuple[str, ...]:
    return tuple(dict.fromkeys(record.slice_id for record in report.closed_slices))


def _slice_by_id(records: Sequence[LaneSliceRecord], slice_id: str) -> Optional[LaneSliceRecord]:
    for record in records:
        if record.slice_id == slice_id:
            return record
    return None


def evaluate_reddog_worker_claim_dryrun(
    report: LaneReconciliationReport,
    *,
    requested_slice: Optional[str] = None,
    worker_id: Optional[str] = None,
    lane_id: Optional[str] = None,
    allow_stale_sources: bool = False,
) -> RedDogWorkerClaimDryRunDecision:
    """Evaluate whether a future worker claim would be allowed.

    The default is fail-closed on stale sources. `allow_stale_sources=True` is
    reserved for a future verification-only caller and still performs no claim.
    """

    rejection_reasons: List[str] = []
    if not isinstance(report, LaneReconciliationReport):
        raise TypeError("report must be a LaneReconciliationReport")

    if not report.no_ledger_mutation_performed:
        rejection_reasons.append("reconciliation_report_mutated_ledger")
    if not report.no_agentdb_mutation_performed:
        rejection_reasons.append("reconciliation_report_mutated_agentdb")
    if not report.no_holoindex_mutation_performed:
        rejection_reasons.append("reconciliation_report_mutated_holoindex")
    if not report.no_worker_assignment_performed:
        rejection_reasons.append("reconciliation_report_already_assigned_worker")
    if not report.no_execution_performed:
        rejection_reasons.append("reconciliation_report_executed")

    if report.conflicts:
        rejection_reasons.append("lane_state_conflict")
    if report.recommended_action == "RECONCILE_LEDGER_BEFORE_WORK":
        rejection_reasons.append("reconcile_ledger_before_claim")
    if report.stale_sources and not allow_stale_sources:
        rejection_reasons.append("ledger_sources_stale")
    if report.recommended_action == "NO_OPEN_WORK":
        rejection_reasons.append("no_open_work")

    open_ids = _open_slice_ids(report)
    closed_ids = _closed_slice_ids(report)
    requested = requested_slice.strip().upper() if isinstance(requested_slice, str) and requested_slice.strip() else None
    selected = requested or report.prework_packet.chosen_slice

    if requested and requested in closed_ids:
        rejection_reasons.append("requested_slice_already_closed")
    elif requested and requested not in open_ids:
        rejection_reasons.append("requested_slice_not_in_open_queue")

    if not selected:
        rejection_reasons.append("no_selected_slice")
    elif selected in report.prework_packet.not_this_slice and selected != requested:
        rejection_reasons.append("selected_slice_marked_not_this_slice")
    elif selected not in open_ids:
        rejection_reasons.append("selected_slice_not_open")

    selected_record = _slice_by_id(report.open_slices, selected) if selected else None
    if selected and selected_record is None:
        rejection_reasons.append("selected_slice_record_missing")

    reasons = tuple(dict.fromkeys(rejection_reasons))
    accepted = not reasons
    decision = CLAIM_READY_DRYRUN if accepted else CLAIM_REJECTED
    payload = {
        "decision": decision,
        "selected_slice": selected if accepted else None,
        "worker_id": worker_id,
        "lane_id": lane_id or (selected_record.lane if selected_record else None),
        "reconciliation_report_id": report.report_id,
        "recommended_action": report.recommended_action,
        "rejection_reasons": reasons,
        "stale_sources": report.stale_sources,
        "conflict_slice_ids": [conflict.slice_id for conflict in report.conflicts],
    }

    receipt = RedDogWorkerClaimDryRunReceipt(
        claim_id=_canonical_digest(payload),
        decision=decision,
        selected_slice=selected if accepted else None,
        worker_id=worker_id,
        lane_id=lane_id or (selected_record.lane if selected_record else None),
        reconciliation_report_id=report.report_id,
        recommended_action=report.recommended_action,
        rejection_reasons=reasons,
        stale_sources=report.stale_sources,
        conflict_slice_ids=tuple(conflict.slice_id for conflict in report.conflicts),
        closed_groundwork=report.prework_packet.closed_groundwork,
        open_target=report.prework_packet.open_target,
        not_this_slice=report.prework_packet.not_this_slice,
    )
    return RedDogWorkerClaimDryRunDecision(accepted=accepted, receipt=receipt)


__all__ = [
    "CLAIM_READY_DRYRUN",
    "CLAIM_REJECTED",
    "RedDogWorkerClaimDryRunDecision",
    "RedDogWorkerClaimDryRunReceipt",
    "evaluate_reddog_worker_claim_dryrun",
]
