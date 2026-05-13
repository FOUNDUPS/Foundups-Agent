#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CABR Lifecycle Correlation Phase 6 -- Read-Only Pipeline Stage Correlation

Provides read-only lifecycle correlation across the full CABR consensus pipeline:
  Stage 1: ProofOfComputeReceipt (RECEIPT_CREATED)
  Stage 2: PAVSVerificationResult (PAVS_EVALUATED)
  Stage 3: CABRScoreResult (CABR_SCORED)
  Stage 4: QuorumVerificationResult (QUORUM_EVALUATED)
  Stage 5: CABRConsensusRecord (CONSENSUS_FINALIZED)
  Stage 6: Persisted (PERSISTED) -- detected via store presence
  Stage 7: Reported (REPORTED) -- detected via report inclusion

This is OBSERVABILITY ONLY -- lifecycle correlation does NOT mean:
  - Automatic state progression
  - verification_complete=True
  - cabr_ready=True
  - payout_ready=True
  - Payout approval
  - DAO activation
  - Token issuance
  - External settlement

WSP 97 TRUTH BOUNDARIES:
  * DOES:
    - Correlate items across stages by receipt_id, job_id, record_hash
    - Report missing downstream stages as gaps (not inferred)
    - Handle duplicates deterministically (first seen wins)
    - Flag truth-boundary anomalies (if any truth field is True)
    - Export deterministic JSON (pure string output)
    - Support partial pipelines (some stages missing)

  X DOES NOT:
    - Mutate any stage items
    - Issue tokens or UPS
    - Allocate rewards
    - Write to wallet
    - Trigger payouts
    - Activate DAO transitions
    - Make network calls
    - Infer missing stages
    - Use any default DB path
    - Write to filesystem

Architecture:
  Phase 1-5 -> Pipeline stages (receipt -> verification -> scoring -> quorum -> consensus)
  Phase 4   -> Reporting aggregation
  Phase 5   -> Time-range and receipt correlation
  Phase 6   -> Lifecycle correlation (this) -> full pipeline tracing

WSP Compliance:
  WSP 11  : Interface contract (explicit, typed)
  WSP 91  : Observability (timestamps, audit fields)
  WSP 97  : System Execution Prompting (truth boundaries)

Slice: CABR_CONSENSUS_FINALIZATION_PHASE6_RECEIPT_LIFECYCLE_CORRELATION
Worker: W1
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger("cabr_lifecycle_correlation")


def _utc_now() -> datetime:
    """Return current UTC timestamp."""
    return datetime.now(timezone.utc)


def _utc_iso(dt: Optional[datetime]) -> Optional[str]:
    """Convert datetime to ISO string or None."""
    return dt.isoformat() if dt else None


# ---------------------------------------------------------------------------
# Lifecycle Stage Enum
# ---------------------------------------------------------------------------


class CABRLifecycleStage(str, Enum):
    """
    CABR pipeline lifecycle stages in deterministic order.

    WSP 97: Stage presence is observability only. Reaching REPORTED does NOT mean:
      - verification_complete=True
      - cabr_ready=True
      - payout_ready=True
      - Payout approval
      - DAO activation
    """

    RECEIPT_CREATED = "receipt_created"
    """Stage 1: ProofOfComputeReceipt created from terminal job."""

    PAVS_EVALUATED = "pavs_evaluated"
    """Stage 2: PAVSVerificationResult from pAVS evaluation."""

    CABR_SCORED = "cabr_scored"
    """Stage 3: CABRScoreResult from CABR scoring engine."""

    QUORUM_EVALUATED = "quorum_evaluated"
    """Stage 4: QuorumVerificationResult from quorum verification."""

    CONSENSUS_FINALIZED = "consensus_finalized"
    """Stage 5: CABRConsensusRecord from consensus finalization."""

    PERSISTED = "persisted"
    """Stage 6: Record persisted to CABRConsensusStore."""

    REPORTED = "reported"
    """Stage 7: Record included in CABRConsensusReport."""


# Deterministic stage ordering for iteration
LIFECYCLE_STAGE_ORDER: List[CABRLifecycleStage] = [
    CABRLifecycleStage.RECEIPT_CREATED,
    CABRLifecycleStage.PAVS_EVALUATED,
    CABRLifecycleStage.CABR_SCORED,
    CABRLifecycleStage.QUORUM_EVALUATED,
    CABRLifecycleStage.CONSENSUS_FINALIZED,
    CABRLifecycleStage.PERSISTED,
    CABRLifecycleStage.REPORTED,
]


# ---------------------------------------------------------------------------
# Lifecycle Item
# ---------------------------------------------------------------------------


@dataclass
class CABRLifecycleItem:
    """
    A single item at a specific lifecycle stage.

    WSP 97: Item presence does NOT imply state progression.
    """

    stage: CABRLifecycleStage
    """The lifecycle stage of this item."""

    receipt_id: Optional[str] = None
    """Receipt ID for correlation."""

    job_id: Optional[str] = None
    """Job ID for fallback correlation."""

    record_hash: Optional[str] = None
    """Record hash for integrity correlation (where applicable)."""

    item_id: Optional[str] = None
    """Stage-specific item ID (receipt_id, verification_id, score_id, quorum_id, record_id)."""

    timestamp: Optional[datetime] = None
    """Timestamp of item creation (if available)."""

    decision: Optional[str] = None
    """Decision value (if applicable to stage)."""

    reason_code: Optional[str] = None
    """Reason code (if applicable to stage)."""

    # WSP 97 truth fields (if present in source item)
    verification_complete: bool = False
    """Truth field from source item."""

    cabr_ready: bool = False
    """Truth field from source item."""

    payout_ready: bool = False
    """Truth field from source item."""

    raw_data: Optional[Dict[str, Any]] = None
    """Optional: Raw item dict for audit trail."""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict."""
        return {
            "stage": self.stage.value,
            "receipt_id": self.receipt_id,
            "job_id": self.job_id,
            "record_hash": self.record_hash,
            "item_id": self.item_id,
            "timestamp": _utc_iso(self.timestamp),
            "decision": self.decision,
            "reason_code": self.reason_code,
            "verification_complete": self.verification_complete,
            "cabr_ready": self.cabr_ready,
            "payout_ready": self.payout_ready,
        }


# ---------------------------------------------------------------------------
# Lifecycle Gap
# ---------------------------------------------------------------------------


@dataclass
class CABRLifecycleGap:
    """
    A gap in the lifecycle indicating a missing downstream stage.

    WSP 97: Gaps are reported, not inferred. Gap presence does NOT imply:
      - Failure
      - Retry needed
      - State rollback
      - Payout blocked
    """

    correlation_key: str
    """Key used to correlate (receipt_id or job_id)."""

    correlation_value: str
    """Value of the correlation key."""

    present_stage: CABRLifecycleStage
    """The last stage present for this item."""

    missing_stage: CABRLifecycleStage
    """The missing downstream stage."""

    gap_type: str = "missing_downstream"
    """Type of gap: 'missing_downstream' or 'orphan'."""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict."""
        return {
            "correlation_key": self.correlation_key,
            "correlation_value": self.correlation_value,
            "present_stage": self.present_stage.value,
            "missing_stage": self.missing_stage.value,
            "gap_type": self.gap_type,
        }


# ---------------------------------------------------------------------------
# Lifecycle Correlation
# ---------------------------------------------------------------------------


@dataclass
class CABRLifecycleCorrelation:
    """
    Correlation of a single item across all lifecycle stages.

    WSP 97 Critical:
      This correlation is for OBSERVABILITY ONLY. It does NOT mean:
        - verification_complete=True
        - cabr_ready=True
        - payout_ready=True
        - Payout approval
        - DAO activation
        - Token issuance
        - External settlement
        - Automatic state progression
    """

    correlation_key: str
    """Key used to correlate (receipt_id, job_id, or record_hash)."""

    correlation_value: str
    """Value of the correlation key."""

    stages_present: List[CABRLifecycleStage] = field(default_factory=list)
    """Stages where this item was found."""

    stages_missing: List[CABRLifecycleStage] = field(default_factory=list)
    """Expected downstream stages not found."""

    items: Dict[str, CABRLifecycleItem] = field(default_factory=dict)
    """Map from stage name to item at that stage."""

    gaps: List[CABRLifecycleGap] = field(default_factory=list)
    """List of detected gaps."""

    has_truth_boundary_anomaly: bool = False
    """True if any item has a truth field set to True."""

    anomaly_details: List[str] = field(default_factory=list)
    """Details of truth boundary anomalies."""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict (sorted for determinism)."""
        return {
            "correlation_key": self.correlation_key,
            "correlation_value": self.correlation_value,
            "stages_present": sorted([s.value for s in self.stages_present]),
            "stages_missing": sorted([s.value for s in self.stages_missing]),
            "items": {k: v.to_dict() for k, v in sorted(self.items.items())},
            "gaps": [g.to_dict() for g in self.gaps],
            "has_truth_boundary_anomaly": self.has_truth_boundary_anomaly,
            "anomaly_details": sorted(self.anomaly_details),
        }


# ---------------------------------------------------------------------------
# Correlation Result
# ---------------------------------------------------------------------------


@dataclass
class CABRLifecycleCorrelationResult:
    """
    Result of lifecycle correlation across all provided items.

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

    correlations: List[CABRLifecycleCorrelation] = field(default_factory=list)
    """List of correlations, one per unique correlation key."""

    total_items: int = 0
    """Total items processed."""

    items_by_stage: Dict[str, int] = field(default_factory=dict)
    """Count of items per stage."""

    total_gaps: int = 0
    """Total gaps detected."""

    total_anomalies: int = 0
    """Total truth boundary anomalies detected."""

    generated_at: datetime = field(default_factory=_utc_now)
    """When this result was generated."""

    wsp97_compliance_note: str = (
        "WSP 97: Lifecycle correlation is observability only. "
        "No payout, DAO activation, or state progression is implied."
    )
    """WSP 97 compliance reminder embedded in result."""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict (sorted for determinism)."""
        return {
            "correlations": [c.to_dict() for c in self.correlations],
            "total_items": self.total_items,
            "items_by_stage": dict(sorted(self.items_by_stage.items())),
            "total_gaps": self.total_gaps,
            "total_anomalies": self.total_anomalies,
            "generated_at": _utc_iso(self.generated_at),
            "wsp97_compliance_note": self.wsp97_compliance_note,
        }


# ---------------------------------------------------------------------------
# Item Builders
# ---------------------------------------------------------------------------


def _build_item_from_receipt(receipt: Dict[str, Any]) -> CABRLifecycleItem:
    """Build lifecycle item from ProofOfComputeReceipt dict."""
    timestamp = None
    created_at = receipt.get("created_at")
    if created_at:
        try:
            if isinstance(created_at, str):
                if created_at.endswith("Z"):
                    created_at = created_at[:-1] + "+00:00"
                timestamp = datetime.fromisoformat(created_at)
            elif isinstance(created_at, datetime):
                timestamp = created_at
        except (ValueError, TypeError):
            pass

    return CABRLifecycleItem(
        stage=CABRLifecycleStage.RECEIPT_CREATED,
        receipt_id=receipt.get("receipt_id"),
        job_id=receipt.get("job_id"),
        item_id=receipt.get("receipt_id"),
        timestamp=timestamp,
        decision=receipt.get("verification_status"),
        reason_code=receipt.get("status_reason_code"),
        # Receipts don't have truth fields, always False
        verification_complete=False,
        cabr_ready=False,
        payout_ready=False,
        raw_data=receipt,
    )


def _build_item_from_pavs_result(result: Dict[str, Any]) -> CABRLifecycleItem:
    """Build lifecycle item from PAVSVerificationResult dict."""
    timestamp = None
    created_at = result.get("created_at")
    if created_at:
        try:
            if isinstance(created_at, str):
                if created_at.endswith("Z"):
                    created_at = created_at[:-1] + "+00:00"
                timestamp = datetime.fromisoformat(created_at)
            elif isinstance(created_at, datetime):
                timestamp = created_at
        except (ValueError, TypeError):
            pass

    return CABRLifecycleItem(
        stage=CABRLifecycleStage.PAVS_EVALUATED,
        receipt_id=result.get("receipt_id"),
        job_id=result.get("job_id"),
        item_id=result.get("verification_id"),
        timestamp=timestamp,
        decision=result.get("decision"),
        reason_code=result.get("reason_code"),
        verification_complete=result.get("verification_complete", False),
        cabr_ready=result.get("cabr_ready", False),
        payout_ready=result.get("payout_ready", False),
        raw_data=result,
    )


def _build_item_from_score_result(result: Dict[str, Any]) -> CABRLifecycleItem:
    """Build lifecycle item from CABRScoreResult dict."""
    timestamp = None
    scored_at = result.get("scored_at")
    if scored_at:
        try:
            if isinstance(scored_at, str):
                if scored_at.endswith("Z"):
                    scored_at = scored_at[:-1] + "+00:00"
                timestamp = datetime.fromisoformat(scored_at)
            elif isinstance(scored_at, datetime):
                timestamp = scored_at
        except (ValueError, TypeError):
            pass

    return CABRLifecycleItem(
        stage=CABRLifecycleStage.CABR_SCORED,
        receipt_id=result.get("receipt_id"),
        job_id=result.get("job_id"),
        item_id=result.get("score_id"),
        timestamp=timestamp,
        decision=result.get("decision"),
        reason_code=result.get("reason_code"),
        verification_complete=result.get("verification_complete", False),
        cabr_ready=result.get("cabr_ready", False),
        payout_ready=result.get("payout_ready", False),
        raw_data=result,
    )


def _build_item_from_quorum_result(result: Dict[str, Any]) -> CABRLifecycleItem:
    """Build lifecycle item from QuorumVerificationResult dict."""
    timestamp = None
    evaluated_at = result.get("evaluated_at")
    if evaluated_at:
        try:
            if isinstance(evaluated_at, str):
                if evaluated_at.endswith("Z"):
                    evaluated_at = evaluated_at[:-1] + "+00:00"
                timestamp = datetime.fromisoformat(evaluated_at)
            elif isinstance(evaluated_at, datetime):
                timestamp = evaluated_at
        except (ValueError, TypeError):
            pass

    return CABRLifecycleItem(
        stage=CABRLifecycleStage.QUORUM_EVALUATED,
        receipt_id=result.get("receipt_id"),
        job_id=result.get("job_id"),
        item_id=result.get("quorum_id"),
        timestamp=timestamp,
        decision=result.get("decision"),
        reason_code=result.get("reason_code"),
        verification_complete=result.get("verification_complete", False),
        cabr_ready=result.get("cabr_ready", False),
        payout_ready=result.get("payout_ready", False),
        raw_data=result,
    )


def _build_item_from_consensus_record(record: Dict[str, Any]) -> CABRLifecycleItem:
    """Build lifecycle item from CABRConsensusRecord dict."""
    timestamp = None
    finalized_at = record.get("finalized_at")
    if finalized_at:
        try:
            if isinstance(finalized_at, str):
                if finalized_at.endswith("Z"):
                    finalized_at = finalized_at[:-1] + "+00:00"
                timestamp = datetime.fromisoformat(finalized_at)
            elif isinstance(finalized_at, datetime):
                timestamp = finalized_at
        except (ValueError, TypeError):
            pass

    return CABRLifecycleItem(
        stage=CABRLifecycleStage.CONSENSUS_FINALIZED,
        receipt_id=record.get("receipt_id"),
        job_id=record.get("job_id"),
        record_hash=record.get("record_hash"),
        item_id=record.get("record_id"),
        timestamp=timestamp,
        decision=record.get("decision"),
        reason_code=record.get("reason_code"),
        verification_complete=record.get("verification_complete", False),
        cabr_ready=record.get("cabr_ready", False),
        payout_ready=record.get("payout_ready", False),
        raw_data=record,
    )


def _build_persisted_item(record: Dict[str, Any]) -> CABRLifecycleItem:
    """Build lifecycle item for persisted stage from stored record dict."""
    timestamp = None
    stored_at = record.get("stored_at")
    if stored_at:
        try:
            if isinstance(stored_at, str):
                if stored_at.endswith("Z"):
                    stored_at = stored_at[:-1] + "+00:00"
                timestamp = datetime.fromisoformat(stored_at)
            elif isinstance(stored_at, datetime):
                timestamp = stored_at
        except (ValueError, TypeError):
            pass

    return CABRLifecycleItem(
        stage=CABRLifecycleStage.PERSISTED,
        receipt_id=record.get("receipt_id"),
        job_id=record.get("job_id"),
        record_hash=record.get("record_hash"),
        item_id=record.get("record_id"),
        timestamp=timestamp,
        decision=record.get("decision"),
        reason_code=record.get("reason_code"),
        verification_complete=record.get("verification_complete", False),
        cabr_ready=record.get("cabr_ready", False),
        payout_ready=record.get("payout_ready", False),
        raw_data=record,
    )


def _build_reported_item(record: Dict[str, Any]) -> CABRLifecycleItem:
    """Build lifecycle item for reported stage from report record dict."""
    # Reported items use same data as persisted, just different stage
    item = _build_persisted_item(record)
    item.stage = CABRLifecycleStage.REPORTED
    return item


# ---------------------------------------------------------------------------
# Correlation Key Extraction
# ---------------------------------------------------------------------------


def _get_correlation_key(item: CABRLifecycleItem) -> tuple[str, str]:
    """
    Get correlation key for an item.

    Priority: receipt_id > job_id > record_hash

    Returns:
        Tuple of (key_type, key_value) or ("unknown", "unknown") if no key found.
    """
    if item.receipt_id:
        return ("receipt_id", item.receipt_id)
    if item.job_id:
        return ("job_id", item.job_id)
    if item.record_hash:
        return ("record_hash", item.record_hash)
    return ("unknown", "unknown")


# ---------------------------------------------------------------------------
# Truth Boundary Checking
# ---------------------------------------------------------------------------


def _check_truth_boundary(item: CABRLifecycleItem) -> List[str]:
    """
    Check item for truth boundary anomalies.

    Returns list of anomaly descriptions (empty if no anomalies).
    """
    anomalies = []

    if item.verification_complete:
        anomalies.append(
            f"Stage {item.stage.value}: verification_complete=True "
            f"(item_id={item.item_id})"
        )

    if item.cabr_ready:
        anomalies.append(
            f"Stage {item.stage.value}: cabr_ready=True "
            f"(item_id={item.item_id})"
        )

    if item.payout_ready:
        anomalies.append(
            f"Stage {item.stage.value}: payout_ready=True "
            f"(item_id={item.item_id})"
        )

    return anomalies


# ---------------------------------------------------------------------------
# Public API: Correlate CABR Lifecycle
# ---------------------------------------------------------------------------


def correlate_cabr_lifecycle(
    receipts: Optional[List[Dict[str, Any]]] = None,
    pavs_results: Optional[List[Dict[str, Any]]] = None,
    score_results: Optional[List[Dict[str, Any]]] = None,
    quorum_results: Optional[List[Dict[str, Any]]] = None,
    consensus_records: Optional[List[Dict[str, Any]]] = None,
    persisted_records: Optional[List[Dict[str, Any]]] = None,
    reported_records: Optional[List[Dict[str, Any]]] = None,
) -> CABRLifecycleCorrelationResult:
    """
    Correlate items across all CABR lifecycle stages.

    This function takes lists of items at each stage and produces correlations
    showing which items have progressed through the pipeline and which have gaps.

    Correlation is done by receipt_id, falling back to job_id, then record_hash.
    Duplicates are handled deterministically (first item at each stage is used).

    WSP 97 Critical:
      This correlation is for OBSERVABILITY ONLY. It does NOT mean:
        - verification_complete=True
        - cabr_ready=True
        - payout_ready=True
        - Payout approval
        - DAO activation
        - Token issuance
        - External settlement
        - Automatic state progression

    Args:
        receipts: List of ProofOfComputeReceipt dicts.
        pavs_results: List of PAVSVerificationResult dicts.
        score_results: List of CABRScoreResult dicts.
        quorum_results: List of QuorumVerificationResult dicts.
        consensus_records: List of CABRConsensusRecord dicts (in-memory).
        persisted_records: List of CABRConsensusRecord dicts (from store).
        reported_records: List of CABRConsensusRecord dicts (from report).

    Returns:
        CABRLifecycleCorrelationResult with correlations, gaps, and anomalies.
    """
    # Build items from each stage
    all_items: List[CABRLifecycleItem] = []

    for r in (receipts or []):
        all_items.append(_build_item_from_receipt(r))

    for r in (pavs_results or []):
        all_items.append(_build_item_from_pavs_result(r))

    for r in (score_results or []):
        all_items.append(_build_item_from_score_result(r))

    for r in (quorum_results or []):
        all_items.append(_build_item_from_quorum_result(r))

    for r in (consensus_records or []):
        all_items.append(_build_item_from_consensus_record(r))

    for r in (persisted_records or []):
        all_items.append(_build_persisted_item(r))

    for r in (reported_records or []):
        all_items.append(_build_reported_item(r))

    # Group items by correlation key
    # Key: (key_type, key_value), Value: dict of stage -> item
    correlations_map: Dict[tuple[str, str], Dict[str, CABRLifecycleItem]] = {}

    for item in all_items:
        key = _get_correlation_key(item)
        if key not in correlations_map:
            correlations_map[key] = {}

        stage_name = item.stage.value
        # First seen wins (deterministic duplicate handling)
        if stage_name not in correlations_map[key]:
            correlations_map[key][stage_name] = item

    # Build correlation results
    correlations: List[CABRLifecycleCorrelation] = []
    total_gaps = 0
    total_anomalies = 0
    items_by_stage: Dict[str, int] = {}

    # Sort keys for deterministic ordering
    sorted_keys = sorted(correlations_map.keys())

    for key in sorted_keys:
        key_type, key_value = key
        stage_items = correlations_map[key]

        correlation = CABRLifecycleCorrelation(
            correlation_key=key_type,
            correlation_value=key_value,
            items=stage_items,
        )

        # Determine present and missing stages
        for stage in LIFECYCLE_STAGE_ORDER:
            stage_name = stage.value
            if stage_name in stage_items:
                correlation.stages_present.append(stage)
                items_by_stage[stage_name] = items_by_stage.get(stage_name, 0) + 1
            else:
                # Only mark as missing if there's a present stage before it
                # (i.e., detect downstream gaps, not orphans)
                correlation.stages_missing.append(stage)

        # Build gaps for each missing downstream stage
        if correlation.stages_present:
            highest_present_idx = max(
                LIFECYCLE_STAGE_ORDER.index(s) for s in correlation.stages_present
            )
            highest_present = LIFECYCLE_STAGE_ORDER[highest_present_idx]

            # Check each stage after the highest present
            for stage in LIFECYCLE_STAGE_ORDER[highest_present_idx + 1:]:
                stage_name = stage.value
                if stage_name not in stage_items:
                    gap = CABRLifecycleGap(
                        correlation_key=key_type,
                        correlation_value=key_value,
                        present_stage=highest_present,
                        missing_stage=stage,
                        gap_type="missing_downstream",
                    )
                    correlation.gaps.append(gap)
                    total_gaps += 1

        # Check for truth boundary anomalies in all items
        for item in stage_items.values():
            anomalies = _check_truth_boundary(item)
            if anomalies:
                correlation.has_truth_boundary_anomaly = True
                correlation.anomaly_details.extend(anomalies)
                total_anomalies += len(anomalies)

        correlations.append(correlation)

    # Build result
    result = CABRLifecycleCorrelationResult(
        correlations=correlations,
        total_items=len(all_items),
        items_by_stage=items_by_stage,
        total_gaps=total_gaps,
        total_anomalies=total_anomalies,
    )

    logger.info(
        "[CABR-LIFECYCLE] Correlated %d items -> %d correlations, %d gaps, %d anomalies",
        len(all_items),
        len(correlations),
        total_gaps,
        total_anomalies,
    )

    return result


# ---------------------------------------------------------------------------
# Public API: Summarize Lifecycle Gaps
# ---------------------------------------------------------------------------


@dataclass
class CABRLifecycleGapSummary:
    """
    Summary of gaps across all correlations.

    WSP 97: Gap summary is observability only. Gaps do NOT imply:
      - Failure
      - Retry needed
      - Payout blocked
      - DAO issues
    """

    total_gaps: int = 0
    """Total gaps detected."""

    gaps_by_stage: Dict[str, int] = field(default_factory=dict)
    """Count of gaps per missing stage."""

    correlations_with_gaps: int = 0
    """Number of correlations with at least one gap."""

    correlations_complete: int = 0
    """Number of correlations with no downstream gaps after first stage."""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict."""
        return {
            "total_gaps": self.total_gaps,
            "gaps_by_stage": dict(sorted(self.gaps_by_stage.items())),
            "correlations_with_gaps": self.correlations_with_gaps,
            "correlations_complete": self.correlations_complete,
        }


def summarize_lifecycle_gaps(
    result: CABRLifecycleCorrelationResult,
) -> CABRLifecycleGapSummary:
    """
    Summarize gaps from a lifecycle correlation result.

    WSP 97: Gap summary is observability only. Gaps do NOT imply:
      - Failure
      - Retry needed
      - Payout blocked
      - DAO issues

    Args:
        result: CABRLifecycleCorrelationResult to summarize.

    Returns:
        CABRLifecycleGapSummary with gap statistics.
    """
    summary = CABRLifecycleGapSummary(total_gaps=result.total_gaps)

    for correlation in result.correlations:
        if correlation.gaps:
            summary.correlations_with_gaps += 1
            for gap in correlation.gaps:
                stage = gap.missing_stage.value
                summary.gaps_by_stage[stage] = summary.gaps_by_stage.get(stage, 0) + 1
        else:
            # No gaps means complete (for the stages that exist)
            if correlation.stages_present:
                summary.correlations_complete += 1

    return summary


# ---------------------------------------------------------------------------
# Public API: Export Lifecycle Correlation JSON
# ---------------------------------------------------------------------------


def export_lifecycle_correlation_json(
    result: CABRLifecycleCorrelationResult,
    indent: int = 2,
) -> str:
    """
    Export lifecycle correlation result as deterministic JSON string.

    This is a pure function that produces a JSON string from a result.
    It does NOT write to filesystem (caller handles file output if needed).

    WSP 97: The JSON output includes the WSP 97 compliance note. Presence
    of complete correlations in the JSON does NOT indicate payout readiness
    or DAO activation.

    Args:
        result: CABRLifecycleCorrelationResult to export.
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
