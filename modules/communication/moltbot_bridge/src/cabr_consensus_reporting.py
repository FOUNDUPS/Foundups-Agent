#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CABR Consensus Reporting Phase 4 -- Read-Only Aggregation and Audit Trail Analysis

Provides read-only aggregation and reporting tools for persisted CABRConsensusRecord
audit trails. This is OBSERVABILITY ONLY -- reporting does NOT mean:
  - verification_complete=True
  - cabr_ready=True
  - payout_ready=True
  - Payout approval
  - DAO activation
  - Token issuance
  - External settlement
  - Automatic state progression

WSP 97 TRUTH BOUNDARIES:
  * DOES:
    - Read-only queries over CABRConsensusStore
    - Aggregate decision counts by decision type
    - Aggregate reason code counts
    - Summarize truth field states (assert all remain False)
    - Flag truth boundary anomalies if injected malformed rows exist
    - Deterministic JSON export (pure string output)
    - Summarize verifier/quorum metadata where available
    - Support filtering by decision type

  X DOES NOT:
    - Mutate records in store
    - Issue tokens or UPS
    - Allocate rewards
    - Write to wallet
    - Trigger payouts
    - Activate DAO transitions
    - Make network calls
    - Infer payout readiness from aggregated data
    - Infer DAO activation from aggregated data
    - Use any default DB path
    - Write to filesystem (unless caller requests export path)

Architecture:
  Phase 1 -> CABRConsensusRecord (in-memory decision)
  Phase 2 -> CABRConsensusStore (SQLite persistence)
  Phase 3 -> Auto-persist integration (optional persistence)
  Phase 4 -> CABRConsensusReporting (this) -> read-only aggregation

WSP Compliance:
  WSP 11  : Interface contract (explicit, typed)
  WSP 91  : Observability (timestamps, audit fields)
  WSP 97  : System Execution Prompting (truth boundaries)

Slice: CABR_CONSENSUS_FINALIZATION_PHASE4_AGGREGATION_REPORTING
Worker: W1
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger("cabr_consensus_reporting")


def _utc_now() -> datetime:
    """Return current UTC timestamp."""
    return datetime.now(timezone.utc)


def _utc_iso(dt: Optional[datetime]) -> Optional[str]:
    """Convert datetime to ISO string or None."""
    return dt.isoformat() if dt else None


# ---------------------------------------------------------------------------
# Decision and Reason Code Counts
# ---------------------------------------------------------------------------


@dataclass
class CABRDecisionCounts:
    """
    Counts of records by decision type.

    WSP 97: These counts are observability only. High counts of
    ACCEPTED_FOR_REVIEW do NOT indicate payout readiness or DAO activation.
    """

    not_finalized: int = 0
    """Count of NOT_FINALIZED records."""

    rejected: int = 0
    """Count of REJECTED records."""

    accepted_for_review: int = 0
    """Count of ACCEPTED_FOR_REVIEW records. WSP 97: Does NOT mean cabr_ready."""

    pending_quorum: int = 0
    """Count of PENDING_QUORUM records."""

    blocked_truth_boundary: int = 0
    """Count of BLOCKED_TRUTH_BOUNDARY records."""

    total: int = 0
    """Total record count."""

    def to_dict(self) -> Dict[str, int]:
        """Serialize to dict."""
        return {
            "not_finalized": self.not_finalized,
            "rejected": self.rejected,
            "accepted_for_review": self.accepted_for_review,
            "pending_quorum": self.pending_quorum,
            "blocked_truth_boundary": self.blocked_truth_boundary,
            "total": self.total,
        }


@dataclass
class CABRReasonCodeCounts:
    """
    Counts of records by reason code.

    Reason codes are machine-readable explanations for decisions.
    """

    counts: Dict[str, int] = field(default_factory=dict)
    """Map from reason_code to count."""

    def to_dict(self) -> Dict[str, int]:
        """Serialize to dict (sorted for determinism)."""
        return dict(sorted(self.counts.items()))


# ---------------------------------------------------------------------------
# Truth Boundary Summary
# ---------------------------------------------------------------------------


@dataclass
class CABRTruthBoundarySummary:
    """
    Summary of WSP 97 truth field states across records.

    All truth fields SHOULD be False in Phase 1-4 records. Any True values
    indicate potential data corruption or injected malformed rows.

    WSP 97: This summary is for observability. It does NOT assert consensus
    readiness or payout approval.
    """

    total_records: int = 0
    """Total records examined."""

    verification_complete_false: int = 0
    """Count where verification_complete=False (expected: all)."""

    verification_complete_true: int = 0
    """Count where verification_complete=True (expected: 0, anomaly if >0)."""

    cabr_ready_false: int = 0
    """Count where cabr_ready=False (expected: all)."""

    cabr_ready_true: int = 0
    """Count where cabr_ready=True (expected: 0, anomaly if >0)."""

    payout_ready_false: int = 0
    """Count where payout_ready=False (expected: all)."""

    payout_ready_true: int = 0
    """Count where payout_ready=True (expected: 0, anomaly if >0)."""

    has_anomaly: bool = False
    """True if any truth field has unexpected True value."""

    anomaly_record_ids: List[str] = field(default_factory=list)
    """Record IDs with truth boundary anomalies."""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict."""
        return {
            "total_records": self.total_records,
            "verification_complete": {
                "false": self.verification_complete_false,
                "true": self.verification_complete_true,
            },
            "cabr_ready": {
                "false": self.cabr_ready_false,
                "true": self.cabr_ready_true,
            },
            "payout_ready": {
                "false": self.payout_ready_false,
                "true": self.payout_ready_true,
            },
            "has_anomaly": self.has_anomaly,
            "anomaly_record_ids": self.anomaly_record_ids,
        }


# ---------------------------------------------------------------------------
# Quorum Metrics Summary
# ---------------------------------------------------------------------------


@dataclass
class CABRQuorumMetricsSummary:
    """
    Summary of quorum-related metrics across records.

    WSP 97: These metrics are observability only. High quorum rates do NOT
    indicate payout readiness or DAO activation.
    """

    total_with_quorum_met: int = 0
    """Count of records where quorum_met=True."""

    total_with_threshold_met: int = 0
    """Count of records where threshold_met=True."""

    total_verifiers_sum: int = 0
    """Sum of unique_verifiers across all records."""

    avg_unique_verifiers: float = 0.0
    """Average unique verifiers per record."""

    avg_consensus_score: float = 0.0
    """Average consensus score across records with non-zero score."""

    records_with_evidence: int = 0
    """Count of records with evidence_present=True."""

    total_evidence_count: int = 0
    """Sum of evidence_count across all records."""

    dry_run_count: int = 0
    """Count of dry-run records."""

    simulated_count: int = 0
    """Count of simulated records."""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict."""
        return {
            "total_with_quorum_met": self.total_with_quorum_met,
            "total_with_threshold_met": self.total_with_threshold_met,
            "total_verifiers_sum": self.total_verifiers_sum,
            "avg_unique_verifiers": round(self.avg_unique_verifiers, 3),
            "avg_consensus_score": round(self.avg_consensus_score, 3),
            "records_with_evidence": self.records_with_evidence,
            "total_evidence_count": self.total_evidence_count,
            "dry_run_count": self.dry_run_count,
            "simulated_count": self.simulated_count,
        }


# ---------------------------------------------------------------------------
# Report Summary
# ---------------------------------------------------------------------------


@dataclass
class CABRConsensusReportSummary:
    """
    Summary statistics from a consensus report.

    WSP 97: This is observability only. No payout, DAO, or state inference.
    """

    decision_counts: CABRDecisionCounts = field(default_factory=CABRDecisionCounts)
    """Counts by decision type."""

    reason_code_counts: CABRReasonCodeCounts = field(default_factory=CABRReasonCodeCounts)
    """Counts by reason code."""

    truth_boundary_summary: CABRTruthBoundarySummary = field(
        default_factory=CABRTruthBoundarySummary
    )
    """Truth field summary (all should be False)."""

    quorum_metrics: CABRQuorumMetricsSummary = field(
        default_factory=CABRQuorumMetricsSummary
    )
    """Quorum and evidence metrics."""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict."""
        return {
            "decision_counts": self.decision_counts.to_dict(),
            "reason_code_counts": self.reason_code_counts.to_dict(),
            "truth_boundary_summary": self.truth_boundary_summary.to_dict(),
            "quorum_metrics": self.quorum_metrics.to_dict(),
        }


# ---------------------------------------------------------------------------
# Full Report
# ---------------------------------------------------------------------------


@dataclass
class CABRConsensusReport:
    """
    Full consensus report including records and summary.

    WSP 97 Critical:
      This report is for OBSERVABILITY ONLY. It does NOT mean:
        - verification_complete=True
        - cabr_ready=True
        - payout_ready=True
        - Payout approval
        - DAO activation
        - Token issuance
        - External settlement
        - Automatic state progression

    Usage:
        report = generate_consensus_report(store, limit=100)
        summary = report.summary
        json_output = export_consensus_report_json(report)
    """

    records: List[Dict[str, Any]] = field(default_factory=list)
    """List of consensus records (read-only snapshot)."""

    summary: CABRConsensusReportSummary = field(
        default_factory=CABRConsensusReportSummary
    )
    """Aggregated summary statistics."""

    generated_at: datetime = field(default_factory=_utc_now)
    """When this report was generated."""

    report_version: str = "1.0.0"
    """Report format version."""

    decision_filter: Optional[str] = None
    """Decision filter applied, if any."""

    record_limit: Optional[int] = None
    """Limit applied, if any."""

    wsp97_compliance_note: str = (
        "WSP 97: This report is observability only. "
        "No payout, DAO activation, or state progression is implied."
    )
    """WSP 97 compliance reminder embedded in report."""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict."""
        return {
            "records": self.records,
            "summary": self.summary.to_dict(),
            "generated_at": _utc_iso(self.generated_at),
            "report_version": self.report_version,
            "decision_filter": self.decision_filter,
            "record_limit": self.record_limit,
            "wsp97_compliance_note": self.wsp97_compliance_note,
        }


# ---------------------------------------------------------------------------
# Summarization Functions
# ---------------------------------------------------------------------------


def summarize_consensus_records(
    records: List[Dict[str, Any]]
) -> CABRConsensusReportSummary:
    """
    Summarize a list of consensus records.

    This is a pure function that takes a list of record dicts and produces
    aggregated statistics. It does NOT mutate the input records.

    WSP 97: The summary is observability only. It does NOT indicate:
      - verification_complete=True
      - cabr_ready=True
      - payout_ready=True
      - Payout approval
      - DAO activation

    Args:
        records: List of CABRConsensusRecord dicts (from store or in-memory).

    Returns:
        CABRConsensusReportSummary with aggregated statistics.
    """
    summary = CABRConsensusReportSummary()

    if not records:
        return summary

    # Decision counts
    decision_counts = summary.decision_counts
    for record in records:
        decision = record.get("decision", "").lower()
        if decision == "not_finalized":
            decision_counts.not_finalized += 1
        elif decision == "rejected":
            decision_counts.rejected += 1
        elif decision == "accepted_for_review":
            decision_counts.accepted_for_review += 1
        elif decision == "pending_quorum":
            decision_counts.pending_quorum += 1
        elif decision == "blocked_truth_boundary":
            decision_counts.blocked_truth_boundary += 1
    decision_counts.total = len(records)

    # Reason code counts
    reason_code_counts = summary.reason_code_counts
    for record in records:
        reason_code = record.get("reason_code", "unknown")
        reason_code_counts.counts[reason_code] = (
            reason_code_counts.counts.get(reason_code, 0) + 1
        )

    # Truth boundary summary
    truth_summary = summary.truth_boundary_summary
    truth_summary.total_records = len(records)

    for record in records:
        record_id = record.get("record_id", "unknown")

        # Check verification_complete
        if record.get("verification_complete", False):
            truth_summary.verification_complete_true += 1
            truth_summary.has_anomaly = True
            if record_id not in truth_summary.anomaly_record_ids:
                truth_summary.anomaly_record_ids.append(record_id)
        else:
            truth_summary.verification_complete_false += 1

        # Check cabr_ready
        if record.get("cabr_ready", False):
            truth_summary.cabr_ready_true += 1
            truth_summary.has_anomaly = True
            if record_id not in truth_summary.anomaly_record_ids:
                truth_summary.anomaly_record_ids.append(record_id)
        else:
            truth_summary.cabr_ready_false += 1

        # Check payout_ready
        if record.get("payout_ready", False):
            truth_summary.payout_ready_true += 1
            truth_summary.has_anomaly = True
            if record_id not in truth_summary.anomaly_record_ids:
                truth_summary.anomaly_record_ids.append(record_id)
        else:
            truth_summary.payout_ready_false += 1

    # Sort anomaly record IDs for determinism
    truth_summary.anomaly_record_ids.sort()

    # Quorum metrics
    quorum_metrics = summary.quorum_metrics
    consensus_score_sum = 0.0
    consensus_score_count = 0

    for record in records:
        if record.get("quorum_met", False):
            quorum_metrics.total_with_quorum_met += 1
        if record.get("threshold_met", False):
            quorum_metrics.total_with_threshold_met += 1

        verifiers = record.get("unique_verifiers", 0) or 0
        quorum_metrics.total_verifiers_sum += verifiers

        score = record.get("consensus_score", 0.0) or 0.0
        if score > 0:
            consensus_score_sum += score
            consensus_score_count += 1

        if record.get("evidence_present", False):
            quorum_metrics.records_with_evidence += 1
        quorum_metrics.total_evidence_count += record.get("evidence_count", 0) or 0

        if record.get("is_dry_run", False):
            quorum_metrics.dry_run_count += 1
        if record.get("is_simulated", False):
            quorum_metrics.simulated_count += 1

    if len(records) > 0:
        quorum_metrics.avg_unique_verifiers = (
            quorum_metrics.total_verifiers_sum / len(records)
        )
    if consensus_score_count > 0:
        quorum_metrics.avg_consensus_score = consensus_score_sum / consensus_score_count

    return summary


# ---------------------------------------------------------------------------
# Report Generation
# ---------------------------------------------------------------------------


# Forward reference for type hints (avoid circular import)
# CABRConsensusStore is imported at runtime only when used
CABRConsensusStoreType = Any  # Will be CABRConsensusStore when provided


def generate_consensus_report(
    store: CABRConsensusStoreType,
    limit: Optional[int] = None,
    decision_filter: Optional[str] = None,
) -> CABRConsensusReport:
    """
    Generate a read-only consensus report from a CABRConsensusStore.

    This function reads records from the store and produces an aggregated
    report with summary statistics. It does NOT mutate any records.

    WSP 97 Critical:
      This report is for OBSERVABILITY ONLY. It does NOT mean:
        - verification_complete=True
        - cabr_ready=True
        - payout_ready=True
        - Payout approval
        - DAO activation
        - Token issuance
        - Automatic state progression

    Args:
        store: CABRConsensusStore instance (caller must provide, no default).
        limit: Maximum records to retrieve. None for all (up to store default).
        decision_filter: Optional decision value to filter by
            (e.g., "accepted_for_review", "rejected").

    Returns:
        CABRConsensusReport with records and summary statistics.

    Raises:
        CABRConsensusStoreError: If store read fails.
    """
    # Read records from store
    list_result = store.list_records(
        limit=limit or 10000,  # High default, but not unlimited
        decision_filter=decision_filter,
        offset=0,
    )

    if list_result.status.value not in ("success",):
        logger.warning(
            "[CABR-REPORT] Store read returned status=%s: %s",
            list_result.status.value,
            list_result.message,
        )
        # Return empty report on read error
        return CABRConsensusReport(
            decision_filter=decision_filter,
            record_limit=limit,
        )

    records = list_result.records or []

    # Generate summary
    summary = summarize_consensus_records(records)

    # Build report
    report = CABRConsensusReport(
        records=records,
        summary=summary,
        decision_filter=decision_filter,
        record_limit=limit,
    )

    logger.info(
        "[CABR-REPORT] Generated report: %d records, filter=%s",
        len(records),
        decision_filter,
    )

    return report


# ---------------------------------------------------------------------------
# JSON Export
# ---------------------------------------------------------------------------


def export_consensus_report_json(
    report: CABRConsensusReport,
    indent: int = 2,
) -> str:
    """
    Export consensus report to deterministic JSON string.

    This is a pure function that produces a JSON string from a report.
    It does NOT write to filesystem (caller handles file output if needed).

    WSP 97: The JSON output includes the WSP 97 compliance note. Presence
    of records in the JSON does NOT indicate payout readiness or DAO activation.

    Args:
        report: CABRConsensusReport to export.
        indent: JSON indentation level (default 2 for readability).

    Returns:
        Deterministic JSON string (sorted keys for reproducibility).
    """
    report_dict = report.to_dict()

    # Ensure deterministic output with sorted keys
    json_output = json.dumps(
        report_dict,
        indent=indent,
        sort_keys=True,
        ensure_ascii=False,
        default=str,  # Handle datetime and other non-serializable types
    )

    return json_output


# ---------------------------------------------------------------------------
# Convenience Functions
# ---------------------------------------------------------------------------


def count_decisions(
    store: CABRConsensusStoreType,
    limit: Optional[int] = None,
) -> CABRDecisionCounts:
    """
    Count records by decision type.

    Convenience function for quick decision breakdown without full report.

    Args:
        store: CABRConsensusStore instance.
        limit: Maximum records to count.

    Returns:
        CABRDecisionCounts with counts per decision type.
    """
    report = generate_consensus_report(store, limit=limit)
    return report.summary.decision_counts


def check_truth_boundary_anomalies(
    store: CABRConsensusStoreType,
    limit: Optional[int] = None,
) -> CABRTruthBoundarySummary:
    """
    Check for WSP 97 truth boundary anomalies.

    Convenience function to quickly verify all truth fields are False.

    Args:
        store: CABRConsensusStore instance.
        limit: Maximum records to check.

    Returns:
        CABRTruthBoundarySummary with anomaly detection results.
    """
    report = generate_consensus_report(store, limit=limit)
    return report.summary.truth_boundary_summary


def get_records_by_decision(
    store: CABRConsensusStoreType,
    decision: str,
    limit: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Get records filtered by decision type.

    Convenience function for retrieving specific decision outcomes.

    WSP 97: Retrieving "accepted_for_review" records does NOT mean
    cabr_ready=True or payout_ready=True.

    Args:
        store: CABRConsensusStore instance.
        decision: Decision value to filter by.
        limit: Maximum records to return.

    Returns:
        List of record dicts matching the decision filter.
    """
    report = generate_consensus_report(store, limit=limit, decision_filter=decision)
    return report.records
