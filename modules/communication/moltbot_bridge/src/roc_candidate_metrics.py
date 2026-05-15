#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ROC Candidate Metrics -- Observability-Only Counter for ROC_CANDIDATE Records

Counts REVIEW-ONLY ROC_CANDIDATE-eligible consensus records from CABR Phase 10
pipeline outputs. This is a PURE FUNCTION observability helper with NO state
mutation, NO filesystem writes, and NO runtime progression triggers.

WSP 97 TRUTH BOUNDARIES:
  * DOES:
    - Accept CABRConsensusRecord list or CABRConsensusPipelineResult
    - Count records meeting ROC_CANDIDATE criteria
    - Count anomalies (malformed/invalid records)
    - Return metric snapshot with required WSP 97 labels
    - Document forbidden consumers in result metadata
    - Generate deterministic JSON export

  X DOES NOT:
    - Mutate any state
    - Write to filesystem
    - Trigger daemon actions
    - Imply ROC_VALIDATED
    - Imply CABR_READY
    - Imply PAYOUT_READY
    - Imply DAE_MATURE
    - Imply DAO_CANDIDATE or DAO_ACTIVATED
    - Trigger payouts or token issuance
    - Make network calls
    - Perform external attestation

ROC_CANDIDATE Criteria (from ROC_CANDIDATE_DERIVATION_AUDIT_PHASE1.md):
  - decision == ACCEPTED_FOR_REVIEW
  - quorum_met == True
  - threshold_met == True
  - evidence_present == True
  - verification_complete == False (WSP 97 truth boundary)
  - cabr_ready == False (WSP 97 truth boundary)
  - payout_ready == False (WSP 97 truth boundary)

Forbidden Consumers (must NOT use this metric for):
  - Payout engine eligibility gate
  - DAO transition trigger
  - Token issuance gate
  - CABR_READY flag setting
  - Automatic state promotion
  - External attestation trigger

WSP Compliance:
  WSP 91  : Observability (metric semantics, no state mutation)
  WSP 97  : System Execution Prompting (truth boundaries)
  WSP 100 : ROC_CANDIDATE derivation (Section 12 annex)

Slice: ROC_CANDIDATE_METRIC_IMPL_PHASE1
Worker: W1
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger("roc_candidate_metrics")


def _utc_now() -> datetime:
    """Return current UTC timestamp."""
    return datetime.now(timezone.utc)


def _utc_iso(dt: Optional[datetime]) -> Optional[str]:
    """Convert datetime to ISO string or None."""
    return dt.isoformat() if dt else None


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# WSP 97 required labels for this metric
WSP97_REQUIRED_LABELS: List[str] = [
    "OBSERVABILITY_ONLY",
    "REVIEW_ONLY",
    "ROC_CANDIDATE_ONLY",
    "NOT_ROC_VALIDATED",
    "NOT_CABR_READY",
    "NOT_PAYOUT_READY",
    "NO_DAE_MATURITY",
    "NO_DAO_ACTIVATION",
    "NO_RUNTIME_PROGRESSION",
    "NO_DAEMON_TRIGGER",
]

# Forbidden consumers of this metric
FORBIDDEN_CONSUMERS: List[str] = [
    "payout_engine",
    "dao_transition",
    "token_issuance",
    "cabr_ready_gate",
    "automatic_state_promotion",
    "external_attestation_trigger",
]

# Required decision for ROC_CANDIDATE
ROC_CANDIDATE_DECISION = "accepted_for_review"

# Metric version
METRIC_VERSION = "0.1.0"


# ---------------------------------------------------------------------------
# Input/Output Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class ROCCandidateMetricInput:
    """
    Input for ROC candidate metric counting.

    Accepts either raw CABRConsensusRecord dicts or pipeline result dict.
    """

    records: List[Dict[str, Any]] = field(default_factory=list)
    """List of CABRConsensusRecord dicts to evaluate."""

    pipeline_result: Optional[Dict[str, Any]] = None
    """Optional: CABRConsensusPipelineResult dict to extract records from."""

    tenant_filter: Optional[str] = None
    """Optional: Filter counts by tenant_id."""

    include_record_ids: bool = False
    """If True, include record_ids in snapshot for debugging."""


@dataclass
class ROCCandidateMetricSnapshot:
    """
    Observability-only metric snapshot for ROC_CANDIDATE counts.

    This snapshot is for MONITORING and DASHBOARDS only. It does NOT
    imply any readiness, eligibility, or progression state.
    """

    # === Metric Identity ===
    snapshot_id: str = ""
    """Unique snapshot identifier."""

    # === Counts ===
    total_records: int = 0
    """Total records evaluated."""

    roc_candidate_count: int = 0
    """Records meeting ROC_CANDIDATE criteria (OBSERVABILITY ONLY)."""

    rejected_count: int = 0
    """Records with REJECTED decision."""

    pending_quorum_count: int = 0
    """Records with PENDING_QUORUM decision."""

    anomaly_count: int = 0
    """Malformed or invalid records."""

    # === Breakdown by Tenant (optional) ===
    by_tenant: Dict[str, int] = field(default_factory=dict)
    """ROC_CANDIDATE count by tenant_id."""

    # === Record IDs (optional, for debugging) ===
    candidate_record_ids: List[str] = field(default_factory=list)
    """Record IDs that qualified as ROC_CANDIDATE (if requested)."""

    anomaly_record_ids: List[str] = field(default_factory=list)
    """Record IDs that were anomalies (if requested)."""

    # === WSP 97 Labels (always included) ===
    wsp97_labels: List[str] = field(default_factory=lambda: list(WSP97_REQUIRED_LABELS))
    """Required WSP 97 compliance labels."""

    # === Forbidden Consumers (always included) ===
    forbidden_consumers: List[str] = field(default_factory=lambda: list(FORBIDDEN_CONSUMERS))
    """Consumers that must NOT use this metric for gate decisions."""

    # === Truth Boundary Fields (always False) ===
    roc_validated: bool = False
    """Always False. This metric does NOT validate ROC."""

    cabr_ready: bool = False
    """Always False. This metric does NOT imply CABR readiness."""

    payout_ready: bool = False
    """Always False. This metric does NOT imply payout eligibility."""

    dae_mature: bool = False
    """Always False. This metric does NOT imply DAE maturity."""

    dao_activated: bool = False
    """Always False. This metric does NOT imply DAO activation."""

    # === Metadata ===
    metric_version: str = METRIC_VERSION
    """Metric implementation version."""

    evaluated_at: datetime = field(default_factory=_utc_now)
    """When this snapshot was created."""

    compliance_note: str = (
        "This metric is OBSERVABILITY ONLY. It does NOT imply readiness, "
        "eligibility, or progression. See forbidden_consumers for prohibited uses."
    )
    """Compliance note for consumers."""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict."""
        return {
            "snapshot_id": self.snapshot_id,
            "total_records": self.total_records,
            "roc_candidate_count": self.roc_candidate_count,
            "rejected_count": self.rejected_count,
            "pending_quorum_count": self.pending_quorum_count,
            "anomaly_count": self.anomaly_count,
            "by_tenant": self.by_tenant,
            "candidate_record_ids": self.candidate_record_ids,
            "anomaly_record_ids": self.anomaly_record_ids,
            "wsp97_labels": self.wsp97_labels,
            "forbidden_consumers": self.forbidden_consumers,
            "roc_validated": self.roc_validated,
            "cabr_ready": self.cabr_ready,
            "payout_ready": self.payout_ready,
            "dae_mature": self.dae_mature,
            "dao_activated": self.dao_activated,
            "metric_version": self.metric_version,
            "evaluated_at": _utc_iso(self.evaluated_at),
            "compliance_note": self.compliance_note,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ROCCandidateMetricSnapshot":
        """Deserialize from dict."""
        snapshot = cls(
            snapshot_id=data.get("snapshot_id", ""),
            total_records=data.get("total_records", 0),
            roc_candidate_count=data.get("roc_candidate_count", 0),
            rejected_count=data.get("rejected_count", 0),
            pending_quorum_count=data.get("pending_quorum_count", 0),
            anomaly_count=data.get("anomaly_count", 0),
            by_tenant=data.get("by_tenant", {}),
            candidate_record_ids=data.get("candidate_record_ids", []),
            anomaly_record_ids=data.get("anomaly_record_ids", []),
            wsp97_labels=data.get("wsp97_labels", list(WSP97_REQUIRED_LABELS)),
            forbidden_consumers=data.get("forbidden_consumers", list(FORBIDDEN_CONSUMERS)),
            metric_version=data.get("metric_version", METRIC_VERSION),
            compliance_note=data.get("compliance_note", ""),
        )

        evaluated_at = data.get("evaluated_at")
        if evaluated_at:
            snapshot.evaluated_at = datetime.fromisoformat(evaluated_at)

        return snapshot


# ---------------------------------------------------------------------------
# Core Counting Logic
# ---------------------------------------------------------------------------


def _generate_snapshot_id() -> str:
    """Generate unique snapshot ID."""
    import secrets
    timestamp_hex = hex(int(_utc_now().timestamp()))[2:][:8]
    random_hex = secrets.token_hex(4)
    return f"rocm_{timestamp_hex}_{random_hex}"


def _is_roc_candidate(record: Dict[str, Any]) -> bool:
    """
    Check if a CABRConsensusRecord meets ROC_CANDIDATE criteria.

    Criteria (all must be True):
      - decision == "accepted_for_review"
      - quorum_met == True
      - threshold_met == True
      - evidence_present == True
      - verification_complete == False (WSP 97 truth boundary)
      - cabr_ready == False (WSP 97 truth boundary)
      - payout_ready == False (WSP 97 truth boundary)

    Returns False if any field is missing or criteria not met.
    Missing data does NOT infer candidacy.
    """
    # Required fields for candidacy
    decision = record.get("decision", "")
    quorum_met = record.get("quorum_met")
    threshold_met = record.get("threshold_met")
    evidence_present = record.get("evidence_present")
    verification_complete = record.get("verification_complete")
    cabr_ready = record.get("cabr_ready")
    payout_ready = record.get("payout_ready")

    # Check decision
    if decision != ROC_CANDIDATE_DECISION:
        return False

    # Check quorum criteria (must be explicitly True, not missing)
    if quorum_met is not True:
        return False
    if threshold_met is not True:
        return False
    if evidence_present is not True:
        return False

    # Check WSP 97 truth boundaries (must be explicitly False)
    if verification_complete is not False:
        return False
    if cabr_ready is not False:
        return False
    if payout_ready is not False:
        return False

    return True


def _is_anomaly(record: Dict[str, Any]) -> bool:
    """
    Check if a record is malformed/invalid.

    A record is an anomaly if:
      - Missing record_id
      - Missing decision field
      - decision is not a recognized value
    """
    if not record.get("record_id"):
        return True
    if "decision" not in record:
        return True

    # Recognized decisions
    valid_decisions = {
        "not_finalized",
        "rejected",
        "accepted_for_review",
        "pending_quorum",
        "blocked_truth_boundary",
    }

    decision = record.get("decision", "")
    if decision not in valid_decisions:
        return True

    return False


def _is_rejected(record: Dict[str, Any]) -> bool:
    """Check if record has REJECTED decision."""
    return record.get("decision") == "rejected"


def _is_pending_quorum(record: Dict[str, Any]) -> bool:
    """Check if record has PENDING_QUORUM decision."""
    return record.get("decision") == "pending_quorum"


def count_roc_candidates(
    records_or_result: Union[List[Dict[str, Any]], Dict[str, Any], "ROCCandidateMetricInput"],
    tenant_filter: Optional[str] = None,
    include_record_ids: bool = False,
) -> ROCCandidateMetricSnapshot:
    """
    Count ROC_CANDIDATE-eligible records from consensus records or pipeline result.

    This is a PURE FUNCTION with NO side effects. It:
      - Does NOT mutate any state
      - Does NOT write to filesystem
      - Does NOT trigger daemon actions
      - Does NOT imply any readiness or eligibility

    Args:
        records_or_result: One of:
            - List of CABRConsensusRecord dicts
            - CABRConsensusPipelineResult dict (extracts consensus_records)
            - ROCCandidateMetricInput object
        tenant_filter: Optional tenant_id to filter counts
        include_record_ids: If True, include record IDs in snapshot

    Returns:
        ROCCandidateMetricSnapshot with counts and required WSP 97 labels.
        The snapshot has all readiness flags set to False.
    """
    # Normalize input
    records: List[Dict[str, Any]] = []

    if isinstance(records_or_result, ROCCandidateMetricInput):
        records = records_or_result.records
        if records_or_result.pipeline_result:
            records = records_or_result.pipeline_result.get("consensus_records", [])
        if records_or_result.tenant_filter:
            tenant_filter = records_or_result.tenant_filter
        include_record_ids = records_or_result.include_record_ids
    elif isinstance(records_or_result, dict):
        # Assume pipeline result
        records = records_or_result.get("consensus_records", [])
    else:
        # Assume list of records
        records = records_or_result

    # Initialize counters
    total = 0
    candidate_count = 0
    rejected_count = 0
    pending_quorum_count = 0
    anomaly_count = 0
    by_tenant: Dict[str, int] = {}
    candidate_ids: List[str] = []
    anomaly_ids: List[str] = []

    # Process records
    for record in records:
        if not isinstance(record, dict):
            anomaly_count += 1
            continue

        total += 1
        record_id = record.get("record_id", "")
        tenant_id = record.get("tenant_id", "")

        # Apply tenant filter if specified
        if tenant_filter and tenant_id != tenant_filter:
            continue

        # Check for anomalies first
        if _is_anomaly(record):
            anomaly_count += 1
            if include_record_ids and record_id:
                anomaly_ids.append(record_id)
            continue

        # Categorize by decision
        if _is_roc_candidate(record):
            candidate_count += 1
            if include_record_ids:
                candidate_ids.append(record_id)
            # Track by tenant
            if tenant_id:
                by_tenant[tenant_id] = by_tenant.get(tenant_id, 0) + 1
        elif _is_rejected(record):
            rejected_count += 1
        elif _is_pending_quorum(record):
            pending_quorum_count += 1

    # Build snapshot
    snapshot = ROCCandidateMetricSnapshot(
        snapshot_id=_generate_snapshot_id(),
        total_records=total,
        roc_candidate_count=candidate_count,
        rejected_count=rejected_count,
        pending_quorum_count=pending_quorum_count,
        anomaly_count=anomaly_count,
        by_tenant=by_tenant,
        candidate_record_ids=candidate_ids if include_record_ids else [],
        anomaly_record_ids=anomaly_ids if include_record_ids else [],
        wsp97_labels=list(WSP97_REQUIRED_LABELS),
        forbidden_consumers=list(FORBIDDEN_CONSUMERS),
        # Truth boundaries - all False
        roc_validated=False,
        cabr_ready=False,
        payout_ready=False,
        dae_mature=False,
        dao_activated=False,
    )

    logger.info(
        "[ROC_METRIC] Counted %d ROC_CANDIDATE from %d records (anomalies=%d)",
        candidate_count,
        total,
        anomaly_count,
    )

    return snapshot


# ---------------------------------------------------------------------------
# Export Functions
# ---------------------------------------------------------------------------


def export_roc_candidate_metric_json(
    snapshot: ROCCandidateMetricSnapshot,
    indent: int = 2,
) -> str:
    """
    Export metric snapshot to deterministic JSON.

    JSON output includes:
      - All metric counts
      - WSP 97 required labels
      - Forbidden consumers list
      - Truth boundary fields (all False)
      - Compliance note

    The JSON is deterministic (sorted keys) for reproducibility.
    """
    return json.dumps(snapshot.to_dict(), indent=indent, sort_keys=True, default=str)


def export_roc_candidate_metric_markdown(
    snapshot: ROCCandidateMetricSnapshot,
) -> str:
    """
    Export metric snapshot to human-readable Markdown.

    Markdown output includes:
      - WSP 97 compliance header
      - Metric counts table
      - Truth boundary table
      - Forbidden consumers list
    """
    lines = [
        "# ROC Candidate Metric Snapshot",
        "",
        "**WARNING**: This metric is OBSERVABILITY ONLY.",
        "It does NOT imply readiness, eligibility, or progression.",
        "",
        "## WSP 97 Labels",
        "",
    ]

    for label in snapshot.wsp97_labels:
        lines.append(f"- {label}")

    lines.extend([
        "",
        "## Counts",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Total Records | {snapshot.total_records} |",
        f"| ROC_CANDIDATE Count | {snapshot.roc_candidate_count} |",
        f"| Rejected Count | {snapshot.rejected_count} |",
        f"| Pending Quorum Count | {snapshot.pending_quorum_count} |",
        f"| Anomaly Count | {snapshot.anomaly_count} |",
        "",
        "## Truth Boundary Fields",
        "",
        "| Field | Value |",
        "|-------|-------|",
        f"| roc_validated | {snapshot.roc_validated} |",
        f"| cabr_ready | {snapshot.cabr_ready} |",
        f"| payout_ready | {snapshot.payout_ready} |",
        f"| dae_mature | {snapshot.dae_mature} |",
        f"| dao_activated | {snapshot.dao_activated} |",
        "",
        "## Forbidden Consumers",
        "",
        "The following consumers MUST NOT use this metric for gate decisions:",
        "",
    ])

    for consumer in snapshot.forbidden_consumers:
        lines.append(f"- {consumer}")

    lines.extend([
        "",
        "---",
        "",
        f"*Snapshot ID*: {snapshot.snapshot_id}",
        f"*Evaluated At*: {_utc_iso(snapshot.evaluated_at)}",
        f"*Metric Version*: {snapshot.metric_version}",
    ])

    return "\n".join(lines)
