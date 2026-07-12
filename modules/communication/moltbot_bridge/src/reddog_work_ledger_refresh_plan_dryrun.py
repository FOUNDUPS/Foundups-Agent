"""RedDog work-ledger refresh plan dry-run.

This module turns a stale/conflicted lane reconciliation report into an explicit
refresh plan. It does not update any ledger source; it only names the governed
steps required before worker claims can be trusted.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional, Tuple

from modules.communication.moltbot_bridge.src.reddog_lane_state_reconciler import (
    LaneReconciliationReport,
)


REFRESH_PLAN_READY = "REFRESH_PLAN_READY"
REFRESH_PLAN_BLOCKED = "REFRESH_PLAN_BLOCKED"


@dataclass(frozen=True)
class WorkLedgerRefreshPlanDryRun:
    """Dry-run plan for refreshing lane-state sources."""

    plan_id: str
    status: str
    source_report_id: str
    stale_sources: Tuple[str, ...]
    conflict_slice_ids: Tuple[str, ...]
    refresh_targets: Tuple[str, ...]
    refresh_steps: Tuple[str, ...]
    proposed_last_updated: str
    proposed_next_claim_slice: Optional[str]
    rejection_reasons: Tuple[str, ...]
    no_ledger_mutation_performed: bool = True
    no_agentdb_mutation_performed: bool = True
    no_holoindex_mutation_performed: bool = True
    no_worker_assignment_performed: bool = True
    no_execution_performed: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _canonical_digest(payload: Dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def build_work_ledger_refresh_plan_dryrun(
    report: LaneReconciliationReport,
    *,
    proposed_last_updated: str,
) -> WorkLedgerRefreshPlanDryRun:
    """Build a non-mutating plan to refresh stale work-ledger sources."""

    if not isinstance(report, LaneReconciliationReport):
        raise TypeError("report must be a LaneReconciliationReport")
    if not isinstance(proposed_last_updated, str) or not proposed_last_updated.strip():
        raise ValueError("proposed_last_updated is required")

    conflict_ids = tuple(conflict.slice_id for conflict in report.conflicts)
    rejection_reasons = []
    if conflict_ids:
        rejection_reasons.append("resolve_lane_state_conflicts_first")
    if not report.stale_sources and not conflict_ids:
        rejection_reasons.append("no_refresh_needed")

    refresh_targets = []
    for source in report.sources_checked:
        if source == "ACTIVE_SLICE_LEDGER":
            refresh_targets.append("docs/0102_session_briefings/ACTIVE_SLICE_LEDGER.md")
        elif source == "work_ledger.example.json":
            refresh_targets.append("docs/0102_session_briefings/work_ledger.example.json")
        else:
            refresh_targets.append(source)

    refresh_steps = (
        "read_current_repo_truth",
        "merge_closed_open_blocked_deferred_state",
        "preserve_active_ledger_next_priority_order",
        "update_typed_work_ledger_snapshot",
        "set_last_updated_to_proposed_timestamp",
        "rerun_lane_state_reconciler",
        "rerun_worker_claim_gate",
    )
    status = REFRESH_PLAN_BLOCKED if conflict_ids else REFRESH_PLAN_READY
    proposed_next = report.prework_packet.chosen_slice if status == REFRESH_PLAN_READY else None
    payload = {
        "status": status,
        "source_report_id": report.report_id,
        "stale_sources": report.stale_sources,
        "conflict_slice_ids": conflict_ids,
        "refresh_targets": refresh_targets,
        "refresh_steps": refresh_steps,
        "proposed_last_updated": proposed_last_updated,
        "proposed_next_claim_slice": proposed_next,
        "rejection_reasons": rejection_reasons,
    }
    return WorkLedgerRefreshPlanDryRun(
        plan_id=_canonical_digest(payload),
        status=status,
        source_report_id=report.report_id,
        stale_sources=report.stale_sources,
        conflict_slice_ids=conflict_ids,
        refresh_targets=tuple(refresh_targets),
        refresh_steps=refresh_steps,
        proposed_last_updated=proposed_last_updated,
        proposed_next_claim_slice=proposed_next,
        rejection_reasons=tuple(rejection_reasons),
    )


__all__ = [
    "REFRESH_PLAN_BLOCKED",
    "REFRESH_PLAN_READY",
    "WorkLedgerRefreshPlanDryRun",
    "build_work_ledger_refresh_plan_dryrun",
]
