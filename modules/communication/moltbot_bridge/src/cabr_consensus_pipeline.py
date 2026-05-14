#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CABR Consensus Pipeline Phase 10 -- Caller-Driven Review-Only Pipeline Composer

Provides a caller-driven orchestration helper that composes the full CABR
consensus pipeline in deterministic order:
  ProofOfComputeReceipt -> pAVS -> CABR scoring -> quorum -> consensus
  finalization -> optional persistence -> lifecycle query/export

This is REVIEW-ONLY ORCHESTRATION -- pipeline execution does NOT mean:
  - automatic state progression
  - verification_complete=True
  - cabr_ready=True
  - payout_ready=True
  - Payout approval
  - DAO activation
  - Token issuance
  - Final consensus readiness
  - External settlement

WSP 97 TRUTH BOUNDARIES -- All results MUST include:
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
    - Pure orchestration (composes existing APIs in deterministic order)
    - Caller must provide receipt(s) and verifier attestations
    - Caller optionally provides pAVS result or pipeline verifies receipt
    - No default DB path (store must be provided if persistence desired)
    - No filesystem writes (unless caller provides store)
    - No network calls
    - No secrets or credentials
    - No automatic runtime hooks (WRE/Hermes/FAM do not invoke this)
    - Preserves all required WSP 97 labels
    - Reports missing data as gaps (not inferred)
    - Stage failures fail closed (explicit error, stop pipeline)
    - Missing data becomes gaps in lifecycle export

  X DOES NOT:
    - Provide default DB path
    - Write to filesystem without caller-provided store
    - Auto-invoke from WRE/Hermes/FAM runtime
    - Mutate store/query/correlation/report semantics
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

Architecture:
  Phase 1-9 -> Individual pipeline stages
  Phase 10  -> Pipeline Composer (this) -> orchestrates 1-9 in deterministic order

WSP Compliance:
  WSP 11  : Interface contract (explicit, typed)
  WSP 91  : Observability (timestamps, audit fields)
  WSP 97  : System Execution Prompting (truth boundaries)

Slice: CABR_CONSENSUS_FINALIZATION_PHASE10_PIPELINE_INTEGRATION
Worker: W1
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from .proof_of_compute_receipt import (
    ProofOfComputeReceipt,
)
from .pavs_verification_seam import (
    PAVSDecision,
    PAVSVerificationResult,
    verify_receipt,
)
from .cabr_scoring_engine import (
    CABRScoreDecision,
    CABRScoreInput,
    CABRScoreResult,
    build_score_input_from_receipt,
    build_score_input_from_pavs_result,
    score_cabr_receipt,
    MIN_VALIDATORS_DEFAULT,
)
from .quorum_verification_engine import (
    AttestationStatus,
    QuorumDecision,
    QuorumVerificationInput,
    QuorumVerificationResult,
    VerifierAttestation,
    evaluate_quorum,
    CONSENSUS_THRESHOLD,
)
from .cabr_consensus_finalizer import (
    CABRConsensusDecision,
    CABRConsensusInput,
    CABRConsensusRecord,
    CABRConsensusFinalizeResult,
    finalize_cabr_consensus,
    finalize_cabr_consensus_with_result,
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

logger = logging.getLogger("cabr_consensus_pipeline")


def _utc_now() -> datetime:
    """Return current UTC timestamp."""
    return datetime.now(timezone.utc)


def _utc_iso(dt: Optional[datetime]) -> Optional[str]:
    """Convert datetime to ISO string or None."""
    return dt.isoformat() if dt else None


# ---------------------------------------------------------------------------
# Pipeline Stage Status
# ---------------------------------------------------------------------------


class CABRConsensusPipelineStageStatus(str, Enum):
    """
    Status of individual pipeline stages.

    WSP 97: Stage status describes execution outcome, not claim of completion.
    """

    NOT_EXECUTED = "not_executed"
    """Stage has not been executed yet."""

    SUCCESS = "success"
    """Stage completed successfully."""

    SKIPPED = "skipped"
    """Stage was skipped (caller provided result directly)."""

    FAILED = "failed"
    """Stage failed (pipeline stops here)."""

    BLOCKED = "blocked"
    """Stage blocked by upstream failure."""


class CABRConsensusPipelineStage(str, Enum):
    """Pipeline stage identifiers."""

    RECEIPT = "receipt"
    """ProofOfComputeReceipt stage."""

    PAVS = "pavs"
    """pAVS verification stage."""

    SCORING = "scoring"
    """CABR scoring stage."""

    QUORUM = "quorum"
    """Quorum verification stage."""

    FINALIZATION = "finalization"
    """Consensus finalization stage."""

    PERSISTENCE = "persistence"
    """Optional persistence stage."""

    EXPORT = "export"
    """Optional lifecycle export stage."""


# Pipeline stage execution order
PIPELINE_STAGE_ORDER: List[CABRConsensusPipelineStage] = [
    CABRConsensusPipelineStage.RECEIPT,
    CABRConsensusPipelineStage.PAVS,
    CABRConsensusPipelineStage.SCORING,
    CABRConsensusPipelineStage.QUORUM,
    CABRConsensusPipelineStage.FINALIZATION,
    CABRConsensusPipelineStage.PERSISTENCE,
    CABRConsensusPipelineStage.EXPORT,
]


# ---------------------------------------------------------------------------
# Stage Result Tracking
# ---------------------------------------------------------------------------


@dataclass
class CABRConsensusPipelineStageResult:
    """
    Result from a single pipeline stage.

    WSP 97: Stage results are review-only. Success does NOT mean:
      - verification_complete=True
      - cabr_ready=True
      - payout_ready=True
    """

    stage: CABRConsensusPipelineStage
    """Which stage this result is for."""

    status: CABRConsensusPipelineStageStatus
    """Stage execution status."""

    error_message: Optional[str] = None
    """Error message if failed."""

    error_code: Optional[str] = None
    """Machine-readable error code if failed."""

    result_data: Optional[Dict[str, Any]] = None
    """Stage result data (serialized)."""

    executed_at: datetime = field(default_factory=_utc_now)
    """When this stage was executed."""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict."""
        return {
            "error_code": self.error_code,
            "error_message": self.error_message,
            "executed_at": _utc_iso(self.executed_at),
            "result_data": self.result_data,
            "stage": self.stage.value,
            "status": self.status.value,
        }


# ---------------------------------------------------------------------------
# Pipeline Input
# ---------------------------------------------------------------------------


@dataclass
class CABRConsensusPipelineInput:
    """
    Input for running the CABR consensus pipeline.

    Caller provides receipt(s) and verifier attestations. Optionally,
    caller can provide pre-computed pAVS/score/quorum results to skip
    those stages.

    WSP 97 Critical:
      This input is for REVIEW ONLY pipeline execution. It does NOT enable:
        - automatic state progression
        - verification_complete=True
        - cabr_ready=True
        - payout_ready=True
        - Payout approval
        - DAO activation
        - Token issuance
    """

    # Required: Receipt(s) to process
    receipts: List[Union[ProofOfComputeReceipt, Dict[str, Any]]] = field(
        default_factory=list
    )
    """ProofOfComputeReceipt objects or dicts. At least one required."""

    # Required: Verifier attestations
    attestations: List[Union[VerifierAttestation, Dict[str, Any]]] = field(
        default_factory=list
    )
    """VerifierAttestation objects or dicts for quorum evaluation."""

    # Optional: Pre-computed pAVS results (skip pAVS stage if provided)
    pavs_results: Optional[
        List[Union[PAVSVerificationResult, Dict[str, Any]]]
    ] = None
    """Optional pre-computed pAVS results. If provided, pAVS stage is skipped."""

    # Optional: Pre-computed score results (skip scoring if provided)
    score_results: Optional[List[Union[CABRScoreResult, Dict[str, Any]]]] = None
    """Optional pre-computed score results. If provided, scoring stage is skipped."""

    # Optional: Pre-computed quorum results (skip quorum if provided)
    quorum_results: Optional[
        List[Union[QuorumVerificationResult, Dict[str, Any]]]
    ] = None
    """Optional pre-computed quorum results. If provided, quorum stage is skipped."""

    # Optional: Store for persistence (no default DB path)
    store: Optional[Any] = None
    """CABRConsensusStore instance for persistence. If None, no DB writes."""

    # Configuration
    min_validators: int = MIN_VALIDATORS_DEFAULT
    """Minimum validators for quorum (WSP 29 default: 3)."""

    consensus_threshold: float = CONSENSUS_THRESHOLD
    """Consensus threshold (WSP 29 default: 0.382)."""

    include_lifecycle_export: bool = False
    """If True, generate lifecycle export in result."""

    include_input_snapshot: bool = False
    """If True, include input snapshots in stage results."""

    def validate(self) -> tuple[bool, Optional[str]]:
        """
        Validate pipeline input.

        Returns:
            Tuple of (is_valid, error_message).
        """
        if not self.receipts:
            return (False, "At least one receipt is required")

        # Validate receipt structure
        for i, receipt in enumerate(self.receipts):
            if isinstance(receipt, dict):
                if not receipt.get("receipt_id"):
                    return (False, f"Receipt {i} missing receipt_id")
                if not receipt.get("job_id"):
                    return (False, f"Receipt {i} missing job_id")
                if not receipt.get("tenant_id"):
                    return (False, f"Receipt {i} missing tenant_id")
            elif isinstance(receipt, ProofOfComputeReceipt):
                if not receipt.receipt_id:
                    return (False, f"Receipt {i} missing receipt_id")
                if not receipt.job_id:
                    return (False, f"Receipt {i} missing job_id")
                if not receipt.tenant_id:
                    return (False, f"Receipt {i} missing tenant_id")
            else:
                return (False, f"Receipt {i} has invalid type: {type(receipt)}")

        return (True, None)


# ---------------------------------------------------------------------------
# Pipeline Result
# ---------------------------------------------------------------------------


@dataclass
class CABRConsensusPipelineResult:
    """
    Result from running the CABR consensus pipeline.

    WSP 97 Critical:
      This result is for REVIEW ONLY. It does NOT indicate:
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
    """True if pipeline completed (may have rejected records)."""

    error_message: Optional[str] = None
    """Error message if pipeline failed."""

    # Stage results (in execution order)
    stage_results: List[CABRConsensusPipelineStageResult] = field(
        default_factory=list
    )
    """Results from each stage in execution order."""

    failed_stage: Optional[CABRConsensusPipelineStage] = None
    """Which stage failed (if any)."""

    # Final consensus records
    consensus_records: List[CABRConsensusRecord] = field(default_factory=list)
    """Finalized consensus records (REVIEW ONLY)."""

    # Persistence result
    persistence_attempted: bool = False
    """True if persistence was attempted."""

    persistence_success: bool = False
    """True if all records persisted successfully."""

    persistence_failures: List[str] = field(default_factory=list)
    """Record IDs that failed to persist."""

    # Export result
    lifecycle_export: Optional[CABRLifecycleReportExport] = None
    """Lifecycle export if requested."""

    json_export: Optional[str] = None
    """JSON export string if lifecycle_export generated."""

    markdown_export: Optional[str] = None
    """Markdown export string if lifecycle_export generated."""

    # Metrics
    receipts_processed: int = 0
    """Number of receipts processed."""

    records_accepted: int = 0
    """Number of records accepted for review."""

    records_rejected: int = 0
    """Number of records rejected."""

    records_pending_quorum: int = 0
    """Number of records pending quorum."""

    # Timestamps
    started_at: datetime = field(default_factory=_utc_now)
    """When pipeline execution started."""

    completed_at: Optional[datetime] = None
    """When pipeline execution completed."""

    # WSP 97 Required Fields
    wsp97_labels: List[str] = field(default_factory=list)
    """Required WSP 97 labels (always present)."""

    truth_boundary: Dict[str, bool] = field(default_factory=dict)
    """Truth boundary fields (all must be False)."""

    wsp97_compliance_note: str = (
        "WSP 97: This pipeline result is REVIEW_ONLY and OBSERVABILITY_ONLY. "
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
            "completed_at": _utc_iso(self.completed_at),
            "consensus_records": [r.to_dict() for r in self.consensus_records],
            "error_message": self.error_message,
            "failed_stage": self.failed_stage.value if self.failed_stage else None,
            "json_export": self.json_export,
            "markdown_export": self.markdown_export,
            "persistence_attempted": self.persistence_attempted,
            "persistence_failures": sorted(self.persistence_failures),
            "persistence_success": self.persistence_success,
            "receipts_processed": self.receipts_processed,
            "records_accepted": self.records_accepted,
            "records_pending_quorum": self.records_pending_quorum,
            "records_rejected": self.records_rejected,
            "stage_results": [sr.to_dict() for sr in self.stage_results],
            "started_at": _utc_iso(self.started_at),
            "success": self.success,
            "truth_boundary": dict(sorted(self.truth_boundary.items())),
            "wsp97_compliance_note": self.wsp97_compliance_note,
            "wsp97_labels": sorted(self.wsp97_labels),
        }


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


def _to_receipt_dict(
    receipt: Union[ProofOfComputeReceipt, Dict[str, Any]]
) -> Dict[str, Any]:
    """Convert receipt to dict."""
    if isinstance(receipt, dict):
        return receipt
    return receipt.to_dict()


def _to_attestation(
    attestation: Union[VerifierAttestation, Dict[str, Any]]
) -> VerifierAttestation:
    """Convert attestation to VerifierAttestation object."""
    if isinstance(attestation, VerifierAttestation):
        return attestation
    return VerifierAttestation.from_dict(attestation)


def _to_pavs_dict(
    result: Union[PAVSVerificationResult, Dict[str, Any]]
) -> Dict[str, Any]:
    """Convert pAVS result to dict."""
    if isinstance(result, dict):
        return result
    return result.to_dict()


def _to_score_dict(
    result: Union[CABRScoreResult, Dict[str, Any]]
) -> Dict[str, Any]:
    """Convert score result to dict."""
    if isinstance(result, dict):
        return result
    return result.to_dict()


def _to_quorum_dict(
    result: Union[QuorumVerificationResult, Dict[str, Any]]
) -> Dict[str, Any]:
    """Convert quorum result to dict."""
    if isinstance(result, dict):
        return result
    return result.to_dict()


def _match_result_to_receipt(
    results: List[Dict[str, Any]],
    receipt_id: str,
) -> Optional[Dict[str, Any]]:
    """Find result matching receipt_id."""
    for result in results:
        if result.get("receipt_id") == receipt_id:
            return result
    return None


# ---------------------------------------------------------------------------
# Public API: Run Pipeline
# ---------------------------------------------------------------------------


def run_cabr_consensus_pipeline(
    pipeline_input: CABRConsensusPipelineInput,
) -> CABRConsensusPipelineResult:
    """
    Run the CABR consensus pipeline for provided receipts.

    This is a caller-driven, review-only pipeline composer. It executes
    the consensus pipeline stages in deterministic order:
      1. Receipt validation (caller provides)
      2. pAVS verification (or use caller-provided result)
      3. CABR scoring
      4. Quorum verification
      5. Consensus finalization
      6. Optional persistence (if store provided)
      7. Optional lifecycle export

    Stage failures fail closed -- the pipeline stops at the first failure
    and all downstream stages are marked as BLOCKED.

    WSP 97 Critical:
      This pipeline is for REVIEW ONLY. Completion does NOT mean:
        - verification_complete=True
        - cabr_ready=True
        - payout_ready=True
        - Payout approval
        - DAO activation
        - Token issuance
        - External settlement
        - Automatic state progression

    Args:
        pipeline_input: CABRConsensusPipelineInput with receipts and attestations.

    Returns:
        CABRConsensusPipelineResult with stage results and consensus records.
    """
    result = CABRConsensusPipelineResult()
    result.started_at = _utc_now()

    # Validate input
    is_valid, error_msg = pipeline_input.validate()
    if not is_valid:
        result.error_message = f"Input validation failed: {error_msg}"
        result.stage_results.append(
            CABRConsensusPipelineStageResult(
                stage=CABRConsensusPipelineStage.RECEIPT,
                status=CABRConsensusPipelineStageStatus.FAILED,
                error_message=error_msg,
                error_code="INVALID_INPUT",
            )
        )
        result.failed_stage = CABRConsensusPipelineStage.RECEIPT
        _mark_remaining_blocked(result, CABRConsensusPipelineStage.RECEIPT)
        result.completed_at = _utc_now()
        return result

    # Convert inputs to dicts
    receipt_dicts = [_to_receipt_dict(r) for r in pipeline_input.receipts]
    attestation_objs = [_to_attestation(a) for a in pipeline_input.attestations]

    result.receipts_processed = len(receipt_dicts)

    # Pre-convert optional results if provided
    pavs_dicts: Optional[List[Dict[str, Any]]] = None
    if pipeline_input.pavs_results:
        pavs_dicts = [_to_pavs_dict(r) for r in pipeline_input.pavs_results]

    score_dicts: Optional[List[Dict[str, Any]]] = None
    if pipeline_input.score_results:
        score_dicts = [_to_score_dict(r) for r in pipeline_input.score_results]

    quorum_dicts: Optional[List[Dict[str, Any]]] = None
    if pipeline_input.quorum_results:
        quorum_dicts = [_to_quorum_dict(r) for r in pipeline_input.quorum_results]

    # --- Stage 1: Receipt validation (already done above) ---
    result.stage_results.append(
        CABRConsensusPipelineStageResult(
            stage=CABRConsensusPipelineStage.RECEIPT,
            status=CABRConsensusPipelineStageStatus.SUCCESS,
            result_data={"receipt_count": len(receipt_dicts)},
        )
    )

    # --- Stage 2: pAVS verification ---
    pavs_results_computed: List[Dict[str, Any]] = []
    if pavs_dicts:
        # Caller provided pAVS results -- skip verification
        pavs_results_computed = pavs_dicts
        result.stage_results.append(
            CABRConsensusPipelineStageResult(
                stage=CABRConsensusPipelineStage.PAVS,
                status=CABRConsensusPipelineStageStatus.SKIPPED,
                result_data={"skipped_reason": "caller_provided"},
            )
        )
    else:
        # Run pAVS verification for each receipt
        try:
            for receipt_dict in receipt_dicts:
                pavs_result = verify_receipt(receipt_dict)
                pavs_results_computed.append(pavs_result.to_dict())

            result.stage_results.append(
                CABRConsensusPipelineStageResult(
                    stage=CABRConsensusPipelineStage.PAVS,
                    status=CABRConsensusPipelineStageStatus.SUCCESS,
                    result_data={"pavs_count": len(pavs_results_computed)},
                )
            )
        except Exception as e:
            result.error_message = f"pAVS verification failed: {e}"
            result.stage_results.append(
                CABRConsensusPipelineStageResult(
                    stage=CABRConsensusPipelineStage.PAVS,
                    status=CABRConsensusPipelineStageStatus.FAILED,
                    error_message=str(e),
                    error_code="PAVS_ERROR",
                )
            )
            result.failed_stage = CABRConsensusPipelineStage.PAVS
            _mark_remaining_blocked(result, CABRConsensusPipelineStage.PAVS)
            result.completed_at = _utc_now()
            return result

    # --- Stage 3: CABR Scoring ---
    score_results_computed: List[Dict[str, Any]] = []
    if score_dicts:
        # Caller provided score results -- skip scoring
        score_results_computed = score_dicts
        result.stage_results.append(
            CABRConsensusPipelineStageResult(
                stage=CABRConsensusPipelineStage.SCORING,
                status=CABRConsensusPipelineStageStatus.SKIPPED,
                result_data={"skipped_reason": "caller_provided"},
            )
        )
    else:
        # Run CABR scoring for each pAVS result
        try:
            # Extract verifier IDs from attestations
            verifier_ids = [a.verifier_id for a in attestation_objs if a.verifier_id]

            for pavs_dict in pavs_results_computed:
                # Build score input from pAVS result
                score_input = build_score_input_from_pavs_result(
                    pavs_dict,
                    verifier_ids=verifier_ids,
                )
                score_result = score_cabr_receipt(
                    score_input,
                    min_validators=pipeline_input.min_validators,
                )
                score_results_computed.append(score_result.to_dict())

            result.stage_results.append(
                CABRConsensusPipelineStageResult(
                    stage=CABRConsensusPipelineStage.SCORING,
                    status=CABRConsensusPipelineStageStatus.SUCCESS,
                    result_data={"score_count": len(score_results_computed)},
                )
            )
        except Exception as e:
            result.error_message = f"CABR scoring failed: {e}"
            result.stage_results.append(
                CABRConsensusPipelineStageResult(
                    stage=CABRConsensusPipelineStage.SCORING,
                    status=CABRConsensusPipelineStageStatus.FAILED,
                    error_message=str(e),
                    error_code="SCORING_ERROR",
                )
            )
            result.failed_stage = CABRConsensusPipelineStage.SCORING
            _mark_remaining_blocked(result, CABRConsensusPipelineStage.SCORING)
            result.completed_at = _utc_now()
            return result

    # --- Stage 4: Quorum verification ---
    quorum_results_computed: List[Dict[str, Any]] = []
    if quorum_dicts:
        # Caller provided quorum results -- skip quorum evaluation
        quorum_results_computed = quorum_dicts
        result.stage_results.append(
            CABRConsensusPipelineStageResult(
                stage=CABRConsensusPipelineStage.QUORUM,
                status=CABRConsensusPipelineStageStatus.SKIPPED,
                result_data={"skipped_reason": "caller_provided"},
            )
        )
    else:
        # Run quorum evaluation for each score result
        try:
            for score_dict in score_results_computed:
                quorum_input = QuorumVerificationInput(
                    receipt_id=score_dict.get("receipt_id", ""),
                    job_id=score_dict.get("job_id", ""),
                    tenant_id=score_dict.get("tenant_id", ""),
                    attestations=attestation_objs,
                    min_validators=pipeline_input.min_validators,
                    consensus_threshold=pipeline_input.consensus_threshold,
                    is_dry_run=score_dict.get("is_dry_run", False),
                    cabr_score_id=score_dict.get("score_id"),
                )
                quorum_result = evaluate_quorum(quorum_input)
                quorum_results_computed.append(quorum_result.to_dict())

            result.stage_results.append(
                CABRConsensusPipelineStageResult(
                    stage=CABRConsensusPipelineStage.QUORUM,
                    status=CABRConsensusPipelineStageStatus.SUCCESS,
                    result_data={"quorum_count": len(quorum_results_computed)},
                )
            )
        except Exception as e:
            result.error_message = f"Quorum verification failed: {e}"
            result.stage_results.append(
                CABRConsensusPipelineStageResult(
                    stage=CABRConsensusPipelineStage.QUORUM,
                    status=CABRConsensusPipelineStageStatus.FAILED,
                    error_message=str(e),
                    error_code="QUORUM_ERROR",
                )
            )
            result.failed_stage = CABRConsensusPipelineStage.QUORUM
            _mark_remaining_blocked(result, CABRConsensusPipelineStage.QUORUM)
            result.completed_at = _utc_now()
            return result

    # --- Stage 5: Consensus finalization ---
    try:
        for i, score_dict in enumerate(score_results_computed):
            quorum_dict = quorum_results_computed[i] if i < len(quorum_results_computed) else None

            consensus_input = CABRConsensusInput(
                score_result=score_dict,
                quorum_result=quorum_dict,
                receipt_id=score_dict.get("receipt_id"),
                job_id=score_dict.get("job_id"),
                tenant_id=score_dict.get("tenant_id"),
            )

            consensus_record = finalize_cabr_consensus(
                consensus_input,
                include_input_snapshot=pipeline_input.include_input_snapshot,
                store=None,  # Persistence handled separately
            )
            result.consensus_records.append(consensus_record)

            # Count outcomes
            if consensus_record.decision == CABRConsensusDecision.ACCEPTED_FOR_REVIEW:
                result.records_accepted += 1
            elif consensus_record.decision == CABRConsensusDecision.PENDING_QUORUM:
                result.records_pending_quorum += 1
            elif consensus_record.decision == CABRConsensusDecision.REJECTED:
                result.records_rejected += 1
            else:
                result.records_rejected += 1

        result.stage_results.append(
            CABRConsensusPipelineStageResult(
                stage=CABRConsensusPipelineStage.FINALIZATION,
                status=CABRConsensusPipelineStageStatus.SUCCESS,
                result_data={
                    "consensus_count": len(result.consensus_records),
                    "accepted": result.records_accepted,
                    "rejected": result.records_rejected,
                    "pending_quorum": result.records_pending_quorum,
                },
            )
        )
    except Exception as e:
        result.error_message = f"Consensus finalization failed: {e}"
        result.stage_results.append(
            CABRConsensusPipelineStageResult(
                stage=CABRConsensusPipelineStage.FINALIZATION,
                status=CABRConsensusPipelineStageStatus.FAILED,
                error_message=str(e),
                error_code="FINALIZATION_ERROR",
            )
        )
        result.failed_stage = CABRConsensusPipelineStage.FINALIZATION
        _mark_remaining_blocked(result, CABRConsensusPipelineStage.FINALIZATION)
        result.completed_at = _utc_now()
        return result

    # --- Stage 6: Optional persistence ---
    if pipeline_input.store is not None:
        result.persistence_attempted = True
        try:
            all_persisted = True
            for record in result.consensus_records:
                save_result = pipeline_input.store.save_record(record.to_dict())
                status_val = save_result.status.value
                if status_val not in ("success", "already_exists"):
                    all_persisted = False
                    result.persistence_failures.append(record.record_id)

            result.persistence_success = all_persisted
            result.stage_results.append(
                CABRConsensusPipelineStageResult(
                    stage=CABRConsensusPipelineStage.PERSISTENCE,
                    status=CABRConsensusPipelineStageStatus.SUCCESS,
                    result_data={
                        "persisted": len(result.consensus_records) - len(result.persistence_failures),
                        "failed": len(result.persistence_failures),
                    },
                )
            )
        except Exception as e:
            result.persistence_success = False
            result.stage_results.append(
                CABRConsensusPipelineStageResult(
                    stage=CABRConsensusPipelineStage.PERSISTENCE,
                    status=CABRConsensusPipelineStageStatus.FAILED,
                    error_message=str(e),
                    error_code="PERSISTENCE_ERROR",
                )
            )
            # Persistence failure does NOT fail the pipeline -- records are still returned
    else:
        result.stage_results.append(
            CABRConsensusPipelineStageResult(
                stage=CABRConsensusPipelineStage.PERSISTENCE,
                status=CABRConsensusPipelineStageStatus.SKIPPED,
                result_data={"skipped_reason": "no_store_provided"},
            )
        )

    # --- Stage 7: Optional lifecycle export ---
    if pipeline_input.include_lifecycle_export:
        try:
            # Build lifecycle export
            lifecycle_query_dict = {
                "persisted_record_count": len(result.consensus_records),
                "correlation_result": {
                    "correlations": [],
                    "items_by_stage": {
                        "receipt": len(receipt_dicts),
                        "pavs": len(pavs_results_computed),
                        "scoring": len(score_results_computed),
                        "quorum": len(quorum_results_computed),
                        "finalization": len(result.consensus_records),
                    },
                    "total_items": sum([
                        len(receipt_dicts),
                        len(pavs_results_computed),
                        len(score_results_computed),
                        len(quorum_results_computed),
                        len(result.consensus_records),
                    ]),
                    "total_anomalies": 0,
                },
                "gap_summary": {
                    "total_gaps": 0,
                    "correlations_with_gaps": 0,
                    "correlations_complete": len(result.consensus_records),
                    "gaps_by_stage": {},
                },
            }

            result.lifecycle_export = build_lifecycle_report_export(
                lifecycle_query_result=lifecycle_query_dict,
                consensus_report=None,
            )
            result.json_export = export_lifecycle_report_json(result.lifecycle_export)
            result.markdown_export = export_lifecycle_report_markdown(result.lifecycle_export)

            result.stage_results.append(
                CABRConsensusPipelineStageResult(
                    stage=CABRConsensusPipelineStage.EXPORT,
                    status=CABRConsensusPipelineStageStatus.SUCCESS,
                    result_data={"export_generated": True},
                )
            )
        except Exception as e:
            result.stage_results.append(
                CABRConsensusPipelineStageResult(
                    stage=CABRConsensusPipelineStage.EXPORT,
                    status=CABRConsensusPipelineStageStatus.FAILED,
                    error_message=str(e),
                    error_code="EXPORT_ERROR",
                )
            )
            # Export failure does NOT fail the pipeline -- records are still returned
    else:
        result.stage_results.append(
            CABRConsensusPipelineStageResult(
                stage=CABRConsensusPipelineStage.EXPORT,
                status=CABRConsensusPipelineStageStatus.SKIPPED,
                result_data={"skipped_reason": "not_requested"},
            )
        )

    # Pipeline completed successfully
    result.success = True
    result.completed_at = _utc_now()

    logger.info(
        "[CABR-PIPELINE] Pipeline completed: %d receipts, %d accepted, %d rejected, %d pending",
        result.receipts_processed,
        result.records_accepted,
        result.records_rejected,
        result.records_pending_quorum,
    )

    return result


def _mark_remaining_blocked(
    result: CABRConsensusPipelineResult,
    failed_stage: CABRConsensusPipelineStage,
) -> None:
    """Mark all stages after failed_stage as BLOCKED."""
    failed_idx = PIPELINE_STAGE_ORDER.index(failed_stage)
    executed_stages = {sr.stage for sr in result.stage_results}

    for stage in PIPELINE_STAGE_ORDER[failed_idx + 1:]:
        if stage not in executed_stages:
            result.stage_results.append(
                CABRConsensusPipelineStageResult(
                    stage=stage,
                    status=CABRConsensusPipelineStageStatus.BLOCKED,
                    error_message=f"Blocked by upstream failure at {failed_stage.value}",
                )
            )


# ---------------------------------------------------------------------------
# Public API: Export Pipeline Result JSON
# ---------------------------------------------------------------------------


def export_cabr_consensus_pipeline_json(
    result: CABRConsensusPipelineResult,
    indent: int = 2,
) -> str:
    """
    Export pipeline result as deterministic JSON string.

    This is a pure function that produces a JSON string from a result.
    It does NOT write to filesystem (caller handles file output if needed).

    WSP 97: The JSON output includes all required labels and truth boundary
    fields. Presence of data in the JSON does NOT indicate payout readiness,
    DAO activation, or CABR readiness.

    Args:
        result: CABRConsensusPipelineResult to export.
        indent: JSON indentation level (default 2 for readability).

    Returns:
        Deterministic JSON string (sorted keys for reproducibility).
    """
    result_dict = result.to_dict()

    return json.dumps(
        result_dict,
        indent=indent,
        sort_keys=True,
        ensure_ascii=False,
        default=str,
    )


# ---------------------------------------------------------------------------
# Public API: Export Pipeline Result Markdown
# ---------------------------------------------------------------------------


def export_cabr_consensus_pipeline_markdown(
    result: CABRConsensusPipelineResult,
) -> str:
    """
    Export pipeline result as readable Markdown string.

    This is a pure function that produces a Markdown string from a result.
    It does NOT write to filesystem (caller handles file output if needed).

    WSP 97: The Markdown output includes all required labels and truth boundary
    fields. Presence of data in the output does NOT indicate payout readiness,
    DAO activation, or CABR readiness.

    Args:
        result: CABRConsensusPipelineResult to export.

    Returns:
        Deterministic Markdown string.
    """
    lines: List[str] = []

    # Header
    lines.append("# CABR Consensus Pipeline Result")
    lines.append("")
    lines.append("## WSP 97 Compliance Notice")
    lines.append("")
    lines.append("**STATUS: REVIEW_ONLY | OBSERVABILITY_ONLY**")
    lines.append("")
    lines.append("This pipeline result is for observability purposes only and does NOT indicate:")
    lines.append("")
    for label in sorted(result.wsp97_labels):
        lines.append(f"- {label}")
    lines.append("")

    # Truth Boundary Section
    lines.append("## Truth Boundary Fields")
    lines.append("")
    lines.append("| Field | Value | Required |")
    lines.append("|-------|-------|----------|")
    for field_name, value in sorted(result.truth_boundary.items()):
        required = "False (WSP 97)"
        status = "PASS" if value is False else "**ANOMALY**"
        lines.append(f"| {field_name} | {value} ({status}) | {required} |")
    lines.append("")

    # Pipeline Summary
    lines.append("## Pipeline Summary")
    lines.append("")
    lines.append(f"- **Success**: {result.success}")
    lines.append(f"- **Receipts Processed**: {result.receipts_processed}")
    lines.append(f"- **Records Accepted**: {result.records_accepted}")
    lines.append(f"- **Records Rejected**: {result.records_rejected}")
    lines.append(f"- **Records Pending Quorum**: {result.records_pending_quorum}")
    lines.append(f"- **Started At**: {_utc_iso(result.started_at)}")
    lines.append(f"- **Completed At**: {_utc_iso(result.completed_at)}")
    lines.append("")

    if result.error_message:
        lines.append(f"**Error**: {result.error_message}")
        lines.append("")

    # Stage Results
    lines.append("## Stage Results")
    lines.append("")
    lines.append("| Stage | Status | Error |")
    lines.append("|-------|--------|-------|")
    for sr in result.stage_results:
        error = sr.error_message or "-"
        lines.append(f"| {sr.stage.value} | {sr.status.value} | {error} |")
    lines.append("")

    # Persistence Summary
    if result.persistence_attempted:
        lines.append("## Persistence Summary")
        lines.append("")
        lines.append(f"- **Attempted**: {result.persistence_attempted}")
        lines.append(f"- **Success**: {result.persistence_success}")
        if result.persistence_failures:
            lines.append(f"- **Failed Records**: {', '.join(result.persistence_failures)}")
        lines.append("")

    # Consensus Records Summary
    if result.consensus_records:
        lines.append("## Consensus Records")
        lines.append("")
        lines.append("| Record ID | Decision | Quorum Met | Threshold Met |")
        lines.append("|-----------|----------|------------|---------------|")
        for record in result.consensus_records:
            lines.append(
                f"| {record.record_id} | {record.decision.value} | "
                f"{record.quorum_met} | {record.threshold_met} |"
            )
        lines.append("")

    # Footer with WSP 97 compliance statement
    lines.append("---")
    lines.append("")
    lines.append("## WSP 97 Compliance Statement")
    lines.append("")
    lines.append(result.wsp97_compliance_note)
    lines.append("")

    return "\n".join(lines)
