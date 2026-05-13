#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CABR Store Export Phase 9 -- Caller-Driven Store-to-Export Integration

Provides a pure orchestration helper that composes:
  CABRConsensusStore -> lifecycle query -> lifecycle report export

This is OBSERVABILITY ONLY -- store-export integration does NOT mean:
  - automatic state progression
  - verification_complete=True
  - cabr_ready=True
  - payout_ready=True
  - Payout approval
  - DAO activation
  - Token issuance
  - External settlement
  - Final consensus readiness

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

WSP 97 TRUTH BOUNDARIES:
  * DOES:
    - Pure orchestration (composes existing APIs)
    - Caller must provide store object (no default DB path)
    - No filesystem writes (returns strings only)
    - No network calls
    - No secrets or credentials
    - No implicit side effects
    - Preserves all required WSP 97 labels
    - Reports missing supplemental data as gaps (not inferred)
    - Flags truth-boundary anomalies (does not correct them)
    - Fails closed on invalid query params

  X DOES NOT:
    - Provide default DB path
    - Write to filesystem
    - Mutate store
    - Issue tokens or UPS
    - Allocate rewards
    - Write to wallet
    - Trigger payouts
    - Activate DAO transitions
    - Make network calls
    - Infer payout readiness
    - Infer DAO activation
    - Infer CABR readiness
    - Cause automatic state progression
    - Alter store/query/correlation/report/export semantics

Architecture:
  Phase 1-6 -> Pipeline stages (receipt -> verification -> scoring -> quorum -> consensus -> persistence)
  Phase 7   -> Lifecycle Query (store + lifecycle integration)
  Phase 8   -> Lifecycle Report Export (unified export)
  Phase 9   -> Store Export (this) -> orchestration helper composing 7 + 8

WSP Compliance:
  WSP 11  : Interface contract (explicit, typed)
  WSP 91  : Observability (timestamps, audit fields)
  WSP 97  : System Execution Prompting (truth boundaries)

Slice: CABR_CONSENSUS_FINALIZATION_PHASE9_STORE_EXPORT_INTEGRATION
Worker: W1
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .cabr_lifecycle_query import (
    query_lifecycle_from_store,
)
from .cabr_lifecycle_report_export import (
    CABRExportFormat,
    CABRLifecycleReportExport,
    WSP97_REQUIRED_LABELS,
    WSP97_TRUTH_FIELDS,
    build_lifecycle_report_export,
    export_lifecycle_report_json,
    export_lifecycle_report_markdown,
)

logger = logging.getLogger("cabr_store_export")


def _utc_now() -> datetime:
    """Return current UTC timestamp."""
    return datetime.now(timezone.utc)


def _utc_iso(dt: Optional[datetime]) -> Optional[str]:
    """Convert datetime to ISO string or None."""
    return dt.isoformat() if dt else None


# ---------------------------------------------------------------------------
# Request Dataclass
# ---------------------------------------------------------------------------


@dataclass
class CABRStoreExportRequest:
    """
    Request for store-to-export integration.

    WSP 97 Critical:
      This request is for OBSERVABILITY ONLY. It does NOT enable:
        - automatic state progression
        - verification_complete=True
        - cabr_ready=True
        - payout_ready=True
        - Payout approval
        - DAO activation
        - Token issuance
        - External settlement
    """

    # Store reference (caller MUST provide)
    store: Any = None
    """CABRConsensusStore instance. MUST be provided by caller."""

    # Supplemental pipeline data (optional)
    receipts: Optional[List[Dict[str, Any]]] = None
    """Optional list of ProofOfComputeReceipt dicts."""

    pavs_results: Optional[List[Dict[str, Any]]] = None
    """Optional list of PAVSVerificationResult dicts."""

    score_results: Optional[List[Dict[str, Any]]] = None
    """Optional list of CABRScoreResult dicts."""

    quorum_results: Optional[List[Dict[str, Any]]] = None
    """Optional list of QuorumVerificationResult dicts."""

    # Query parameters
    start: Optional[datetime] = None
    """Optional start time filter (inclusive)."""

    end: Optional[datetime] = None
    """Optional end time filter (inclusive)."""

    limit: Optional[int] = None
    """Optional maximum records to query."""

    # Export options
    include_markdown: bool = True
    """Include Markdown export in result."""

    include_json: bool = True
    """Include JSON export in result."""

    def validate(self) -> bool:
        """
        Validate request parameters.

        Returns:
            True if valid, False otherwise.
        """
        # Store is required
        if self.store is None:
            return False

        # Time range validation
        if self.start is not None and self.end is not None:
            if self.start > self.end:
                return False

        return True


# ---------------------------------------------------------------------------
# Result Dataclass
# ---------------------------------------------------------------------------


@dataclass
class CABRStoreExportResult:
    """
    Result from store-to-export integration.

    WSP 97 Critical:
      This result is for OBSERVABILITY ONLY. It does NOT indicate:
        - verification_complete=True
        - cabr_ready=True
        - payout_ready=True
        - Payout approval
        - DAO activation
        - Token issuance
        - External settlement
        - Automatic state progression
    """

    success: bool = False
    """True if export completed successfully."""

    error_message: Optional[str] = None
    """Error message if not successful."""

    # Lifecycle data
    persisted_record_count: int = 0
    """Number of persisted records queried."""

    total_correlations: int = 0
    """Number of lifecycle correlations."""

    total_gaps: int = 0
    """Total gaps detected."""

    has_anomalies: bool = False
    """True if truth boundary anomalies detected."""

    anomaly_count: int = 0
    """Number of anomalies detected."""

    # Export outputs (strings only, no file writes)
    json_export: Optional[str] = None
    """JSON export string (if include_json=True)."""

    markdown_export: Optional[str] = None
    """Markdown export string (if include_markdown=True)."""

    # Internal export reference (for advanced use)
    export: Optional[CABRLifecycleReportExport] = None
    """Full export dataclass (for additional processing)."""

    generated_at: datetime = field(default_factory=_utc_now)
    """When this result was generated."""

    # WSP 97 Required Fields
    wsp97_labels: List[str] = field(default_factory=list)
    """Required WSP 97 labels (always present)."""

    truth_boundary: Dict[str, bool] = field(default_factory=dict)
    """Truth boundary fields (all must be False)."""

    wsp97_compliance_note: str = (
        "WSP 97: This store export is REVIEW_ONLY and OBSERVABILITY_ONLY. "
        "No payout, DAO activation, or state progression is implied. "
        "verification_complete=False, cabr_ready=False, payout_ready=False. "
        "NOT_CABR_READY, NOT_PAYOUT_READY, NO_DAO_ACTIVATION, "
        "NO_EXTERNAL_ATTESTATION_REQUIRED."
    )
    """WSP 97 compliance statement."""

    def __post_init__(self):
        """Initialize WSP 97 fields."""
        if not self.wsp97_labels:
            self.wsp97_labels = WSP97_REQUIRED_LABELS.copy()
        if not self.truth_boundary:
            self.truth_boundary = WSP97_TRUTH_FIELDS.copy()

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict (sorted keys for determinism)."""
        return {
            "anomaly_count": self.anomaly_count,
            "error_message": self.error_message,
            "generated_at": _utc_iso(self.generated_at),
            "has_anomalies": self.has_anomalies,
            "json_export": self.json_export,
            "markdown_export": self.markdown_export,
            "persisted_record_count": self.persisted_record_count,
            "success": self.success,
            "total_correlations": self.total_correlations,
            "total_gaps": self.total_gaps,
            "truth_boundary": dict(sorted(self.truth_boundary.items())),
            "wsp97_compliance_note": self.wsp97_compliance_note,
            "wsp97_labels": sorted(self.wsp97_labels),
        }


# ---------------------------------------------------------------------------
# Public API: Build Store Export
# ---------------------------------------------------------------------------


def build_store_export(
    store: Any,
    receipts: Optional[List[Dict[str, Any]]] = None,
    pavs_results: Optional[List[Dict[str, Any]]] = None,
    score_results: Optional[List[Dict[str, Any]]] = None,
    quorum_results: Optional[List[Dict[str, Any]]] = None,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    limit: Optional[int] = None,
    include_markdown: bool = True,
    include_json: bool = True,
) -> CABRStoreExportResult:
    """
    Build store export by composing lifecycle query and report export.

    This is a pure orchestration helper. It:
      1. Queries lifecycle from store (Phase 7)
      2. Builds lifecycle report export (Phase 8)
      3. Returns JSON/Markdown strings (no file writes)

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
        store: CABRConsensusStore instance. MUST be provided by caller.
               No default DB path is used.
        receipts: Optional list of ProofOfComputeReceipt dicts.
        pavs_results: Optional list of PAVSVerificationResult dicts.
        score_results: Optional list of CABRScoreResult dicts.
        quorum_results: Optional list of QuorumVerificationResult dicts.
        start: Optional start time filter (inclusive).
        end: Optional end time filter (inclusive).
        limit: Optional maximum records to query.
        include_markdown: Include Markdown export in result (default True).
        include_json: Include JSON export in result (default True).

    Returns:
        CABRStoreExportResult with export strings and WSP 97 compliance.

    Raises:
        ValueError: If store is None or time range is invalid.
    """
    # Fail closed: store is required
    if store is None:
        raise ValueError(
            "store is required. No default DB path is used. "
            "Caller must provide CABRConsensusStore instance."
        )

    # Fail closed: invalid time range
    if start is not None and end is not None and start > end:
        raise ValueError(
            f"Invalid time range: start ({start}) must be <= end ({end})"
        )

    try:
        # Step 1: Query lifecycle from store (Phase 7)
        lifecycle_query_result = query_lifecycle_from_store(
            store=store,
            receipts=receipts,
            pavs_results=pavs_results,
            score_results=score_results,
            quorum_results=quorum_results,
            start=start,
            end=end,
            limit=limit,
        )

        # Step 2: Build lifecycle report export (Phase 8)
        export = build_lifecycle_report_export(
            lifecycle_query_result=lifecycle_query_result.to_dict(),
            consensus_report=None,  # No consensus report in basic store export
        )

        # Step 3: Build result
        result = CABRStoreExportResult(
            success=True,
            persisted_record_count=lifecycle_query_result.persisted_record_count,
            total_correlations=export.total_correlations,
            total_gaps=export.total_gaps,
            has_anomalies=export.has_anomalies,
            anomaly_count=export.anomaly_count,
            export=export,
        )

        # Step 4: Generate export strings (no file writes)
        if include_json:
            result.json_export = export_lifecycle_report_json(export)

        if include_markdown:
            result.markdown_export = export_lifecycle_report_markdown(export)

        logger.info(
            "[CABR-STORE-EXPORT] Built export: %d records, %d correlations, "
            "%d gaps, %d anomalies, json=%s, md=%s",
            result.persisted_record_count,
            result.total_correlations,
            result.total_gaps,
            result.anomaly_count,
            include_json,
            include_markdown,
        )

        return result

    except ValueError:
        # Re-raise validation errors
        raise
    except Exception as e:
        # Wrap other errors
        logger.error("[CABR-STORE-EXPORT] Export failed: %s", e)
        return CABRStoreExportResult(
            success=False,
            error_message=f"Export failed: {e}",
        )


# ---------------------------------------------------------------------------
# Public API: Build Store Export JSON
# ---------------------------------------------------------------------------


def build_store_export_json(
    store: Any,
    receipts: Optional[List[Dict[str, Any]]] = None,
    pavs_results: Optional[List[Dict[str, Any]]] = None,
    score_results: Optional[List[Dict[str, Any]]] = None,
    quorum_results: Optional[List[Dict[str, Any]]] = None,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    limit: Optional[int] = None,
    indent: int = 2,
) -> str:
    """
    Build store export and return JSON string only.

    Convenience function that returns only the JSON export string.
    Raises on error (no result object returned).

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
        store: CABRConsensusStore instance. MUST be provided by caller.
        receipts: Optional list of ProofOfComputeReceipt dicts.
        pavs_results: Optional list of PAVSVerificationResult dicts.
        score_results: Optional list of CABRScoreResult dicts.
        quorum_results: Optional list of QuorumVerificationResult dicts.
        start: Optional start time filter (inclusive).
        end: Optional end time filter (inclusive).
        limit: Optional maximum records to query.
        indent: JSON indentation level (default 2).

    Returns:
        Deterministic JSON string.

    Raises:
        ValueError: If store is None, time range is invalid, or export fails.
    """
    result = build_store_export(
        store=store,
        receipts=receipts,
        pavs_results=pavs_results,
        score_results=score_results,
        quorum_results=quorum_results,
        start=start,
        end=end,
        limit=limit,
        include_json=True,
        include_markdown=False,
    )

    if not result.success:
        raise ValueError(result.error_message or "Export failed")

    # Re-export with custom indent if needed
    if indent != 2 and result.export:
        return export_lifecycle_report_json(result.export, indent=indent)

    return result.json_export or ""


# ---------------------------------------------------------------------------
# Public API: Build Store Export Markdown
# ---------------------------------------------------------------------------


def build_store_export_markdown(
    store: Any,
    receipts: Optional[List[Dict[str, Any]]] = None,
    pavs_results: Optional[List[Dict[str, Any]]] = None,
    score_results: Optional[List[Dict[str, Any]]] = None,
    quorum_results: Optional[List[Dict[str, Any]]] = None,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    limit: Optional[int] = None,
) -> str:
    """
    Build store export and return Markdown string only.

    Convenience function that returns only the Markdown export string.
    Raises on error (no result object returned).

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
        store: CABRConsensusStore instance. MUST be provided by caller.
        receipts: Optional list of ProofOfComputeReceipt dicts.
        pavs_results: Optional list of PAVSVerificationResult dicts.
        score_results: Optional list of CABRScoreResult dicts.
        quorum_results: Optional list of QuorumVerificationResult dicts.
        start: Optional start time filter (inclusive).
        end: Optional end time filter (inclusive).
        limit: Optional maximum records to query.

    Returns:
        Deterministic Markdown string.

    Raises:
        ValueError: If store is None, time range is invalid, or export fails.
    """
    result = build_store_export(
        store=store,
        receipts=receipts,
        pavs_results=pavs_results,
        score_results=score_results,
        quorum_results=quorum_results,
        start=start,
        end=end,
        limit=limit,
        include_json=False,
        include_markdown=True,
    )

    if not result.success:
        raise ValueError(result.error_message or "Export failed")

    return result.markdown_export or ""
