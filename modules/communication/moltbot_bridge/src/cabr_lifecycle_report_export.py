#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CABR Lifecycle Report Export Phase 8 -- Unified Export for Lifecycle and Consensus Reports

Provides unified report export that combines CABR lifecycle query output with
consensus reporting summaries into formatted JSON and Markdown outputs.

This is OBSERVABILITY ONLY -- report export does NOT mean:
  - verification_complete=True
  - cabr_ready=True
  - payout_ready=True
  - Payout approval
  - DAO activation
  - Token issuance
  - External settlement
  - Automatic state progression

WSP 97 TRUTH BOUNDARIES -- All exports MUST include:
  - REVIEW_ONLY
  - OBSERVABILITY_ONLY
  - verification_complete=False
  - cabr_ready=False
  - payout_ready=False
  - NOT_CABR_READY
  - NOT_PAYOUT_READY
  - NO_DAO_ACTIVATION
  - NO_EXTERNAL_ATTESTATION_REQUIRED

WSP 97 TRUTH BOUNDARIES -- Export DOES NOT mean:
  - automatic state progression
  - payout approval
  - DAO activation
  - token issuance
  - final consensus readiness
  - external settlement

WSP 97 TRUTH BOUNDARIES:
  * DOES:
    - Pure export/formatting helpers
    - Deterministic JSON output (sorted keys)
    - Deterministic Markdown output
    - Include lifecycle query summary
    - Include gap summary
    - Include consensus reporting summary if provided
    - Include truth-boundary section with explicit false fields
    - Include explicit review-only labels
    - Flag anomalies (does not correct them)

  X DOES NOT:
    - Mutate input data
    - Issue tokens or UPS
    - Allocate rewards
    - Write to wallet
    - Trigger payouts
    - Activate DAO transitions
    - Make network calls
    - Infer payout readiness
    - Infer DAO activation
    - Infer CABR readiness
    - Use any default DB path
    - Write to filesystem (caller handles file output if needed)

Architecture:
  Phase 1-7 -> Pipeline stages (receipt -> verification -> scoring -> quorum -> consensus -> persistence -> reporting)
  Phase 8   -> Lifecycle Report Export (this) -> unified export

WSP Compliance:
  WSP 11  : Interface contract (explicit, typed)
  WSP 91  : Observability (timestamps, audit fields)
  WSP 97  : System Execution Prompting (truth boundaries)

Slice: CABR_CONSENSUS_FINALIZATION_PHASE8_LIFECYCLE_REPORT_EXPORT_INTEGRATION
Worker: W1
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger("cabr_lifecycle_report_export")


def _utc_now() -> datetime:
    """Return current UTC timestamp."""
    return datetime.now(timezone.utc)


def _utc_iso(dt: Optional[datetime]) -> Optional[str]:
    """Convert datetime to ISO string or None."""
    return dt.isoformat() if dt else None


# ---------------------------------------------------------------------------
# WSP 97 Required Labels
# ---------------------------------------------------------------------------

# These labels MUST be present in all exports per WSP 97
WSP97_REQUIRED_LABELS: List[str] = [
    "REVIEW_ONLY",
    "OBSERVABILITY_ONLY",
    "NOT_CABR_READY",
    "NOT_PAYOUT_READY",
    "NO_DAO_ACTIVATION",
    "NO_EXTERNAL_ATTESTATION_REQUIRED",
]

# Truth boundary fields that MUST all be False
WSP97_TRUTH_FIELDS: Dict[str, bool] = {
    "verification_complete": False,
    "cabr_ready": False,
    "payout_ready": False,
}


# ---------------------------------------------------------------------------
# Export Format Enum
# ---------------------------------------------------------------------------


class CABRExportFormat(str, Enum):
    """
    Export format options for lifecycle reports.

    WSP 97: Export format choice is observability only. Neither format
    implies payout readiness or DAO activation.
    """

    JSON = "json"
    """Export as deterministic JSON."""

    MARKDOWN = "markdown"
    """Export as readable Markdown."""


# ---------------------------------------------------------------------------
# Export Metadata
# ---------------------------------------------------------------------------


@dataclass
class CABRExportMetadata:
    """
    Metadata for a lifecycle report export.

    WSP 97: Metadata is observability only. It does NOT indicate:
      - verification_complete=True
      - cabr_ready=True
      - payout_ready=True
      - Payout approval
      - DAO activation
    """

    export_format: CABRExportFormat = CABRExportFormat.JSON
    """The export format."""

    generated_at: datetime = field(default_factory=_utc_now)
    """When this export was generated."""

    export_version: str = "1.0.0"
    """Export format version."""

    wsp97_labels_present: bool = True
    """True if all required WSP 97 labels are present."""

    truth_fields_false: bool = True
    """True if all truth boundary fields are False."""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict."""
        return {
            "export_format": self.export_format.value,
            "export_version": self.export_version,
            "generated_at": _utc_iso(self.generated_at),
            "truth_fields_false": self.truth_fields_false,
            "wsp97_labels_present": self.wsp97_labels_present,
        }


# ---------------------------------------------------------------------------
# Lifecycle Report Export
# ---------------------------------------------------------------------------


@dataclass
class CABRLifecycleReportExport:
    """
    Unified export combining lifecycle query and consensus reporting.

    WSP 97 Critical:
      This export is for OBSERVABILITY ONLY. It does NOT mean:
        - verification_complete=True
        - cabr_ready=True
        - payout_ready=True
        - Payout approval
        - DAO activation
        - Token issuance
        - External settlement
        - Automatic state progression
    """

    metadata: CABRExportMetadata = field(default_factory=CABRExportMetadata)
    """Export metadata."""

    # Lifecycle query section
    lifecycle_query_summary: Optional[Dict[str, Any]] = None
    """Summary from lifecycle query result."""

    persisted_record_count: int = 0
    """Number of persisted records queried."""

    total_correlations: int = 0
    """Number of lifecycle correlations."""

    # Gap section
    gap_summary: Optional[Dict[str, Any]] = None
    """Gap summary from lifecycle correlation."""

    total_gaps: int = 0
    """Total gaps detected."""

    correlations_with_gaps: int = 0
    """Number of correlations with gaps."""

    correlations_complete: int = 0
    """Number of correlations without downstream gaps."""

    # Consensus reporting section (optional)
    consensus_report_summary: Optional[Dict[str, Any]] = None
    """Summary from consensus report, if provided."""

    # Anomaly section
    has_anomalies: bool = False
    """True if any truth boundary anomalies were detected."""

    anomaly_count: int = 0
    """Total anomalies detected."""

    anomaly_details: List[str] = field(default_factory=list)
    """Details of detected anomalies."""

    # WSP 97 Truth Boundary Section (all MUST be False)
    truth_boundary: Dict[str, Any] = field(default_factory=dict)
    """Truth boundary fields (all must be False)."""

    # WSP 97 Required Labels (all MUST be present)
    wsp97_labels: List[str] = field(default_factory=list)
    """Required WSP 97 labels."""

    wsp97_compliance_note: str = (
        "WSP 97: This export is REVIEW_ONLY and OBSERVABILITY_ONLY. "
        "No payout, DAO activation, or state progression is implied. "
        "verification_complete=False, cabr_ready=False, payout_ready=False. "
        "NOT_CABR_READY, NOT_PAYOUT_READY, NO_DAO_ACTIVATION, "
        "NO_EXTERNAL_ATTESTATION_REQUIRED."
    )
    """WSP 97 compliance statement."""

    def __post_init__(self):
        """Initialize truth boundary and WSP 97 labels."""
        if not self.truth_boundary:
            self.truth_boundary = WSP97_TRUTH_FIELDS.copy()
        if not self.wsp97_labels:
            self.wsp97_labels = WSP97_REQUIRED_LABELS.copy()

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict (sorted keys for determinism)."""
        return {
            "anomaly_count": self.anomaly_count,
            "anomaly_details": sorted(self.anomaly_details),
            "consensus_report_summary": self.consensus_report_summary,
            "correlations_complete": self.correlations_complete,
            "correlations_with_gaps": self.correlations_with_gaps,
            "gap_summary": self.gap_summary,
            "has_anomalies": self.has_anomalies,
            "lifecycle_query_summary": self.lifecycle_query_summary,
            "metadata": self.metadata.to_dict(),
            "persisted_record_count": self.persisted_record_count,
            "total_correlations": self.total_correlations,
            "total_gaps": self.total_gaps,
            "truth_boundary": dict(sorted(self.truth_boundary.items())),
            "wsp97_compliance_note": self.wsp97_compliance_note,
            "wsp97_labels": sorted(self.wsp97_labels),
        }


# ---------------------------------------------------------------------------
# Public API: Build Lifecycle Report Export
# ---------------------------------------------------------------------------


def build_lifecycle_report_export(
    lifecycle_query_result: Optional[Dict[str, Any]] = None,
    consensus_report: Optional[Dict[str, Any]] = None,
) -> CABRLifecycleReportExport:
    """
    Build a unified lifecycle report export from query and report data.

    This is a pure function that takes optional lifecycle query result and
    consensus report data and produces a unified export. It does NOT mutate
    input data or write to filesystem.

    WSP 97 Critical:
      This export is for OBSERVABILITY ONLY. It does NOT mean:
        - verification_complete=True
        - cabr_ready=True
        - payout_ready=True
        - Payout approval
        - DAO activation
        - Token issuance
        - External settlement
        - Automatic state progression

    Args:
        lifecycle_query_result: Optional dict from CABRLifecycleQueryResult.to_dict().
        consensus_report: Optional dict from CABRConsensusReport.to_dict().

    Returns:
        CABRLifecycleReportExport with unified data and WSP 97 compliance.
    """
    export = CABRLifecycleReportExport()

    # Process lifecycle query result
    if lifecycle_query_result:
        export.persisted_record_count = lifecycle_query_result.get(
            "persisted_record_count", 0
        )

        # Extract correlation result summary
        correlation_result = lifecycle_query_result.get("correlation_result")
        if correlation_result:
            export.total_correlations = len(
                correlation_result.get("correlations", [])
            )
            export.anomaly_count = correlation_result.get("total_anomalies", 0)
            export.has_anomalies = export.anomaly_count > 0

            # Build lifecycle query summary
            export.lifecycle_query_summary = {
                "items_by_stage": correlation_result.get("items_by_stage", {}),
                "total_anomalies": export.anomaly_count,
                "total_correlations": export.total_correlations,
                "total_items": correlation_result.get("total_items", 0),
            }

            # Extract anomaly details
            for corr in correlation_result.get("correlations", []):
                if corr.get("has_truth_boundary_anomaly"):
                    export.anomaly_details.extend(corr.get("anomaly_details", []))

        # Extract gap summary
        gap_summary = lifecycle_query_result.get("gap_summary")
        if gap_summary:
            export.total_gaps = gap_summary.get("total_gaps", 0)
            export.correlations_with_gaps = gap_summary.get(
                "correlations_with_gaps", 0
            )
            export.correlations_complete = gap_summary.get(
                "correlations_complete", 0
            )
            export.gap_summary = {
                "correlations_complete": export.correlations_complete,
                "correlations_with_gaps": export.correlations_with_gaps,
                "gaps_by_stage": gap_summary.get("gaps_by_stage", {}),
                "total_gaps": export.total_gaps,
            }

    # Process consensus report
    if consensus_report:
        summary = consensus_report.get("summary", {})
        export.consensus_report_summary = {
            "decision_counts": summary.get("decision_counts", {}),
            "quorum_metrics": summary.get("quorum_metrics", {}),
            "reason_code_counts": summary.get("reason_code_counts", {}),
            "truth_boundary_summary": summary.get("truth_boundary_summary", {}),
        }

        # Check for additional anomalies from consensus report
        truth_summary = summary.get("truth_boundary_summary", {})
        if truth_summary.get("has_anomaly", False):
            export.has_anomalies = True
            anomaly_ids = truth_summary.get("anomaly_record_ids", [])
            for record_id in anomaly_ids:
                # Check which fields had anomalies
                if truth_summary.get("verification_complete", {}).get("true", 0) > 0:
                    export.anomaly_details.append(
                        f"Consensus record {record_id}: verification_complete=True"
                    )
                if truth_summary.get("cabr_ready", {}).get("true", 0) > 0:
                    export.anomaly_details.append(
                        f"Consensus record {record_id}: cabr_ready=True"
                    )
                if truth_summary.get("payout_ready", {}).get("true", 0) > 0:
                    export.anomaly_details.append(
                        f"Consensus record {record_id}: payout_ready=True"
                    )

    # Ensure truth boundary fields are all False
    export.truth_boundary = WSP97_TRUTH_FIELDS.copy()

    # Ensure WSP 97 labels are present
    export.wsp97_labels = WSP97_REQUIRED_LABELS.copy()

    # Update metadata
    export.metadata.wsp97_labels_present = True
    export.metadata.truth_fields_false = all(
        v is False for v in export.truth_boundary.values()
    )

    logger.info(
        "[CABR-EXPORT] Built export: %d records, %d correlations, %d gaps, %d anomalies",
        export.persisted_record_count,
        export.total_correlations,
        export.total_gaps,
        export.anomaly_count,
    )

    return export


# ---------------------------------------------------------------------------
# Public API: Export to JSON
# ---------------------------------------------------------------------------


def export_lifecycle_report_json(
    export: CABRLifecycleReportExport,
    indent: int = 2,
) -> str:
    """
    Export lifecycle report as deterministic JSON string.

    This is a pure function that produces a JSON string from an export.
    It does NOT write to filesystem (caller handles file output if needed).

    WSP 97: The JSON output includes all required labels and truth boundary
    fields. Presence of data in the JSON does NOT indicate payout readiness,
    DAO activation, or CABR readiness.

    Args:
        export: CABRLifecycleReportExport to format.
        indent: JSON indentation level (default 2 for readability).

    Returns:
        Deterministic JSON string (sorted keys for reproducibility).
    """
    export_dict = export.to_dict()

    # Ensure deterministic output with sorted keys
    json_output = json.dumps(
        export_dict,
        indent=indent,
        sort_keys=True,
        ensure_ascii=False,
        default=str,  # Handle datetime and other non-serializable types
    )

    return json_output


# ---------------------------------------------------------------------------
# Public API: Export to Markdown
# ---------------------------------------------------------------------------


def export_lifecycle_report_markdown(
    export: CABRLifecycleReportExport,
) -> str:
    """
    Export lifecycle report as readable Markdown string.

    This is a pure function that produces a Markdown string from an export.
    It does NOT write to filesystem (caller handles file output if needed).

    WSP 97: The Markdown output includes all required labels and truth boundary
    fields. Presence of data in the output does NOT indicate payout readiness,
    DAO activation, or CABR readiness.

    Args:
        export: CABRLifecycleReportExport to format.

    Returns:
        Deterministic Markdown string.
    """
    lines: List[str] = []

    # Header
    lines.append("# CABR Lifecycle Report Export")
    lines.append("")
    lines.append("## WSP 97 Compliance Notice")
    lines.append("")
    lines.append("**STATUS: REVIEW_ONLY | OBSERVABILITY_ONLY**")
    lines.append("")
    lines.append("This report is for observability purposes only and does NOT indicate:")
    lines.append("")
    for label in sorted(export.wsp97_labels):
        lines.append(f"- {label}")
    lines.append("")

    # Truth Boundary Section
    lines.append("## Truth Boundary Fields")
    lines.append("")
    lines.append("| Field | Value | Required |")
    lines.append("|-------|-------|----------|")
    for field_name, value in sorted(export.truth_boundary.items()):
        required = "False (WSP 97)"
        status = "PASS" if value is False else "**ANOMALY**"
        lines.append(f"| {field_name} | {value} ({status}) | {required} |")
    lines.append("")

    # Metadata Section
    lines.append("## Export Metadata")
    lines.append("")
    lines.append(f"- **Generated At**: {_utc_iso(export.metadata.generated_at)}")
    lines.append(f"- **Export Version**: {export.metadata.export_version}")
    lines.append(f"- **Export Format**: {export.metadata.export_format.value}")
    lines.append(f"- **WSP 97 Labels Present**: {export.metadata.wsp97_labels_present}")
    lines.append(f"- **Truth Fields False**: {export.metadata.truth_fields_false}")
    lines.append("")

    # Lifecycle Query Summary
    lines.append("## Lifecycle Query Summary")
    lines.append("")
    lines.append(f"- **Persisted Record Count**: {export.persisted_record_count}")
    lines.append(f"- **Total Correlations**: {export.total_correlations}")
    lines.append("")

    if export.lifecycle_query_summary:
        lqs = export.lifecycle_query_summary
        lines.append("### Items by Stage")
        lines.append("")
        if lqs.get("items_by_stage"):
            lines.append("| Stage | Count |")
            lines.append("|-------|-------|")
            for stage, count in sorted(lqs["items_by_stage"].items()):
                lines.append(f"| {stage} | {count} |")
            lines.append("")
        else:
            lines.append("No items by stage data available.")
            lines.append("")

    # Gap Summary
    lines.append("## Gap Summary")
    lines.append("")
    lines.append(f"- **Total Gaps**: {export.total_gaps}")
    lines.append(f"- **Correlations With Gaps**: {export.correlations_with_gaps}")
    lines.append(f"- **Correlations Complete**: {export.correlations_complete}")
    lines.append("")

    if export.gap_summary and export.gap_summary.get("gaps_by_stage"):
        lines.append("### Gaps by Stage")
        lines.append("")
        lines.append("| Stage | Gap Count |")
        lines.append("|-------|-----------|")
        for stage, count in sorted(export.gap_summary["gaps_by_stage"].items()):
            lines.append(f"| {stage} | {count} |")
        lines.append("")

    # Consensus Report Summary (if present)
    if export.consensus_report_summary:
        lines.append("## Consensus Report Summary")
        lines.append("")

        # Decision Counts
        dc = export.consensus_report_summary.get("decision_counts", {})
        if dc:
            lines.append("### Decision Counts")
            lines.append("")
            lines.append("| Decision | Count |")
            lines.append("|----------|-------|")
            for decision, count in sorted(dc.items()):
                lines.append(f"| {decision} | {count} |")
            lines.append("")

        # Quorum Metrics
        qm = export.consensus_report_summary.get("quorum_metrics", {})
        if qm:
            lines.append("### Quorum Metrics")
            lines.append("")
            for metric, value in sorted(qm.items()):
                lines.append(f"- **{metric}**: {value}")
            lines.append("")

    # Anomaly Section
    lines.append("## Anomaly Report")
    lines.append("")
    lines.append(f"- **Has Anomalies**: {export.has_anomalies}")
    lines.append(f"- **Anomaly Count**: {export.anomaly_count}")
    lines.append("")

    if export.anomaly_details:
        lines.append("### Anomaly Details")
        lines.append("")
        for detail in sorted(export.anomaly_details):
            lines.append(f"- {detail}")
        lines.append("")

    # Footer with WSP 97 compliance statement
    lines.append("---")
    lines.append("")
    lines.append("## WSP 97 Compliance Statement")
    lines.append("")
    lines.append(export.wsp97_compliance_note)
    lines.append("")

    return "\n".join(lines)
