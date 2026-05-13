#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CABR Lifecycle Query Phase 7 -- Read-Only Store Query Integration

Provides read-only lifecycle query helpers that integrate CABRConsensusStore
with Phase 6 lifecycle correlation for end-to-end pipeline tracing.

This is OBSERVABILITY ONLY -- lifecycle query does NOT mean:
  - automatic state progression
  - verification_complete=True
  - cabr_ready=True
  - payout_ready=True
  - Payout approval
  - DAO activation
  - Token issuance
  - External settlement

WSP 97 TRUTH BOUNDARIES:
  * DOES:
    - Read-only queries over CABRConsensusStore
    - Apply optional time range and limit deterministically
    - Correlate persisted records with supplied receipt/pAVS/score/quorum data
    - Report missing supplied receipt data as gaps (not inferred)
    - Handle invalid time range by failing closed
    - Propagate truth-boundary anomalies from Phase 6
    - Export deterministic JSON (pure string output)
    - Support partial pipelines (some stages missing)

  X DOES NOT:
    - Mutate records in store
    - Issue tokens or UPS
    - Allocate rewards
    - Write to wallet
    - Trigger payouts
    - Activate DAO transitions
    - Make network calls
    - Infer payout readiness from query results
    - Infer DAO activation from query results
    - Use any default DB path
    - Write to filesystem (unless caller requests export path)

Architecture:
  Phase 1 -> CABRConsensusRecord (in-memory decision)
  Phase 2 -> CABRConsensusStore (SQLite persistence)
  Phase 3 -> Auto-persist integration (optional persistence)
  Phase 4 -> CABRConsensusReporting -> read-only aggregation
  Phase 5 -> Time-range and receipt correlation
  Phase 6 -> Lifecycle correlation (full pipeline tracing)
  Phase 7 -> Lifecycle Query (this) -> store + lifecycle integration

WSP Compliance:
  WSP 11  : Interface contract (explicit, typed)
  WSP 91  : Observability (timestamps, audit fields)
  WSP 97  : System Execution Prompting (truth boundaries)

Slice: CABR_CONSENSUS_FINALIZATION_PHASE7_LIFECYCLE_QUERY_INTEGRATION
Worker: W1
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .cabr_lifecycle_correlation import (
    CABRLifecycleCorrelationResult,
    CABRLifecycleGapSummary,
    CABRLifecycleStage,
    LIFECYCLE_STAGE_ORDER,
    correlate_cabr_lifecycle,
    summarize_lifecycle_gaps,
)

logger = logging.getLogger("cabr_lifecycle_query")


def _utc_now() -> datetime:
    """Return current UTC timestamp."""
    return datetime.now(timezone.utc)


def _utc_iso(dt: Optional[datetime]) -> Optional[str]:
    """Convert datetime to ISO string or None."""
    return dt.isoformat() if dt else None


# ---------------------------------------------------------------------------
# Lifecycle Query Filter
# ---------------------------------------------------------------------------


@dataclass
class CABRLifecycleQueryFilter:
    """
    Filter for lifecycle query over CABRConsensusStore.

    WSP 97: Query filtering is observability only. It does NOT mean:
      - verification_complete=True
      - cabr_ready=True
      - payout_ready=True
      - Payout approval
      - DAO activation

    Usage:
        filter = CABRLifecycleQueryFilter(
            start_time=datetime(2026, 1, 1, tzinfo=timezone.utc),
            end_time=datetime(2026, 12, 31, tzinfo=timezone.utc),
            limit=100
        )
        result = query_lifecycle_from_store(store, filter=filter)
    """

    start_time: Optional[datetime] = None
    """Start of time range (inclusive). None for no lower bound."""

    end_time: Optional[datetime] = None
    """End of time range (inclusive). None for no upper bound."""

    limit: Optional[int] = None
    """Maximum records to return. None for no limit."""

    decision_filter: Optional[str] = None
    """Optional decision value to filter by."""

    def validate(self) -> bool:
        """
        Return True if filter is valid (start <= end if both set).

        Returns:
            True if filter constraints are valid.
        """
        if self.start_time and self.end_time:
            return self.start_time <= self.end_time
        return True

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict."""
        return {
            "start_time": _utc_iso(self.start_time),
            "end_time": _utc_iso(self.end_time),
            "limit": self.limit,
            "decision_filter": self.decision_filter,
        }


# ---------------------------------------------------------------------------
# Lifecycle Query Result
# ---------------------------------------------------------------------------


@dataclass
class CABRLifecycleQueryResult:
    """
    Result of lifecycle query from store with correlation.

    WSP 97 Critical:
      This result is for OBSERVABILITY ONLY. It does NOT mean:
        - verification_complete=True
        - cabr_ready=True
        - payout_ready=True
        - Payout approval
        - DAO activation
        - Token issuance
        - External settlement
        - Automatic state progression
    """

    query_filter: Optional[CABRLifecycleQueryFilter] = None
    """Query filter applied, if any."""

    persisted_record_count: int = 0
    """Number of records retrieved from store."""

    correlation_result: Optional[CABRLifecycleCorrelationResult] = None
    """Lifecycle correlation result from Phase 6."""

    gap_summary: Optional[CABRLifecycleGapSummary] = None
    """Gap summary from lifecycle correlation."""

    generated_at: datetime = field(default_factory=_utc_now)
    """When this result was generated."""

    wsp97_compliance_note: str = (
        "WSP 97: Lifecycle query is observability only. "
        "No payout, DAO activation, or state progression is implied."
    )
    """WSP 97 compliance reminder embedded in result."""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict (sorted for determinism)."""
        return {
            "correlation_result": (
                self.correlation_result.to_dict()
                if self.correlation_result
                else None
            ),
            "gap_summary": (
                self.gap_summary.to_dict() if self.gap_summary else None
            ),
            "generated_at": _utc_iso(self.generated_at),
            "persisted_record_count": self.persisted_record_count,
            "query_filter": (
                self.query_filter.to_dict() if self.query_filter else None
            ),
            "wsp97_compliance_note": self.wsp97_compliance_note,
        }


# ---------------------------------------------------------------------------
# Store Type Alias
# ---------------------------------------------------------------------------

# Forward reference for type hints (avoid circular import)
CABRConsensusStoreType = Any  # Will be CABRConsensusStore when provided


# ---------------------------------------------------------------------------
# Public API: Query Lifecycle from Store
# ---------------------------------------------------------------------------


def query_lifecycle_from_store(
    store: CABRConsensusStoreType,
    receipts: Optional[List[Dict[str, Any]]] = None,
    pavs_results: Optional[List[Dict[str, Any]]] = None,
    score_results: Optional[List[Dict[str, Any]]] = None,
    quorum_results: Optional[List[Dict[str, Any]]] = None,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    limit: Optional[int] = None,
) -> CABRLifecycleQueryResult:
    """
    Query persisted records from store and correlate with pipeline stages.

    This function reads records from CABRConsensusStore and correlates them
    with optionally supplied receipt, pAVS, score, and quorum data using
    Phase 6 correlation logic.

    If supplemental receipt data is missing, gaps are reported rather than
    inferred. Invalid time range fails closed (raises ValueError).

    WSP 97 Critical:
      This query is for OBSERVABILITY ONLY. It does NOT mean:
        - verification_complete=True
        - cabr_ready=True
        - payout_ready=True
        - Payout approval
        - DAO activation
        - Token issuance
        - Automatic state progression

    Args:
        store: CABRConsensusStore instance (caller must provide, no default).
        receipts: Optional list of ProofOfComputeReceipt dicts.
        pavs_results: Optional list of PAVSVerificationResult dicts.
        score_results: Optional list of CABRScoreResult dicts.
        quorum_results: Optional list of QuorumVerificationResult dicts.
        start: Optional start time (inclusive).
        end: Optional end time (inclusive).
        limit: Optional maximum records to retrieve.

    Returns:
        CABRLifecycleQueryResult with correlation and gap summary.

    Raises:
        ValueError: If time range is invalid (start > end).
    """
    # Build and validate filter
    query_filter = CABRLifecycleQueryFilter(
        start_time=start,
        end_time=end,
        limit=limit,
    )

    if not query_filter.validate():
        raise ValueError(
            f"Invalid time range: start_time ({start}) "
            f"must be <= end_time ({end})"
        )

    # Query persisted records from store
    # Note: We fetch all records (high limit) and apply time filtering + limit in-memory
    # to ensure deterministic behavior with time range + limit combinations.
    list_result = store.list_records(
        limit=100000,  # Fetch all, apply limit after time filtering
        offset=0,
    )

    if list_result.status.value not in ("success",):
        logger.warning(
            "[CABR-LIFECYCLE-QUERY] Store read returned status=%s: %s",
            list_result.status.value,
            list_result.message,
        )
        # Return empty result on read error
        return CABRLifecycleQueryResult(
            query_filter=query_filter,
            persisted_record_count=0,
        )

    persisted_records = list_result.records or []

    # Apply time filtering in-memory
    if start or end:
        filtered_records = []
        for record in persisted_records:
            finalized_at_str = record.get("finalized_at")
            if not finalized_at_str:
                continue

            try:
                if finalized_at_str.endswith("Z"):
                    finalized_at_str = finalized_at_str[:-1] + "+00:00"
                finalized_at = datetime.fromisoformat(finalized_at_str)
            except (ValueError, TypeError):
                logger.warning(
                    "[CABR-LIFECYCLE-QUERY] Could not parse finalized_at: %s",
                    finalized_at_str,
                )
                continue

            if start is not None and finalized_at < start:
                continue
            if end is not None and finalized_at > end:
                continue

            filtered_records.append(record)

        persisted_records = filtered_records

    # Sort by finalized_at descending
    def _sort_key(r: Dict[str, Any]) -> str:
        return r.get("finalized_at", "") or ""

    persisted_records.sort(key=_sort_key, reverse=True)

    # Apply limit after filtering
    if limit is not None:
        persisted_records = persisted_records[:limit]

    # Correlate with Phase 6 lifecycle correlation
    # Persisted records become both consensus_records and persisted_records
    correlation_result = correlate_cabr_lifecycle(
        receipts=receipts,
        pavs_results=pavs_results,
        score_results=score_results,
        quorum_results=quorum_results,
        consensus_records=persisted_records,
        persisted_records=persisted_records,
        reported_records=None,  # Not reported yet
    )

    # Build gap summary
    gap_summary = summarize_lifecycle_gaps(correlation_result)

    logger.info(
        "[CABR-LIFECYCLE-QUERY] Queried %d persisted records, "
        "%d correlations, %d gaps, %d anomalies",
        len(persisted_records),
        len(correlation_result.correlations),
        correlation_result.total_gaps,
        correlation_result.total_anomalies,
    )

    return CABRLifecycleQueryResult(
        query_filter=query_filter,
        persisted_record_count=len(persisted_records),
        correlation_result=correlation_result,
        gap_summary=gap_summary,
    )


# ---------------------------------------------------------------------------
# Public API: Query Lifecycle Gaps from Store
# ---------------------------------------------------------------------------


def query_lifecycle_gaps_from_store(
    store: CABRConsensusStoreType,
    receipts: Optional[List[Dict[str, Any]]] = None,
    pavs_results: Optional[List[Dict[str, Any]]] = None,
    score_results: Optional[List[Dict[str, Any]]] = None,
    quorum_results: Optional[List[Dict[str, Any]]] = None,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    limit: Optional[int] = None,
) -> CABRLifecycleGapSummary:
    """
    Query lifecycle gaps from store with optional pipeline stage data.

    Convenience function that returns only the gap summary.

    WSP 97 Critical:
      Gap summary is for OBSERVABILITY ONLY. Gaps do NOT imply:
        - Failure
        - Retry needed
        - Payout blocked
        - DAO issues
        - verification_complete=True
        - cabr_ready=True
        - payout_ready=True

    Args:
        store: CABRConsensusStore instance (caller must provide, no default).
        receipts: Optional list of ProofOfComputeReceipt dicts.
        pavs_results: Optional list of PAVSVerificationResult dicts.
        score_results: Optional list of CABRScoreResult dicts.
        quorum_results: Optional list of QuorumVerificationResult dicts.
        start: Optional start time (inclusive).
        end: Optional end time (inclusive).
        limit: Optional maximum records to retrieve.

    Returns:
        CABRLifecycleGapSummary with gap statistics.

    Raises:
        ValueError: If time range is invalid (start > end).
    """
    result = query_lifecycle_from_store(
        store=store,
        receipts=receipts,
        pavs_results=pavs_results,
        score_results=score_results,
        quorum_results=quorum_results,
        start=start,
        end=end,
        limit=limit,
    )

    return result.gap_summary or CABRLifecycleGapSummary()


# ---------------------------------------------------------------------------
# Public API: Export Lifecycle Query JSON
# ---------------------------------------------------------------------------


def export_lifecycle_query_json(
    result: CABRLifecycleQueryResult,
    indent: int = 2,
) -> str:
    """
    Export lifecycle query result as deterministic JSON string.

    This is a pure function that produces a JSON string from a result.
    It does NOT write to filesystem (caller handles file output if needed).

    WSP 97: The JSON output includes the WSP 97 compliance note. Presence
    of complete correlations in the JSON does NOT indicate payout readiness
    or DAO activation.

    Args:
        result: CABRLifecycleQueryResult to export.
        indent: JSON indentation level (default 2 for readability).

    Returns:
        Deterministic JSON string (sorted keys for reproducibility).
    """
    result_dict = result.to_dict()

    # Ensure deterministic output with sorted keys
    json_output = json.dumps(
        result_dict,
        indent=indent,
        sort_keys=True,
        ensure_ascii=False,
        default=str,  # Handle datetime and other non-serializable types
    )

    return json_output
