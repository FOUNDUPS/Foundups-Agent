#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CABR Consensus Finalizer Phase 1 -- Deterministic Review Decision Record

Combines CABRScoreResult and QuorumVerificationResult into a consensus record
for internal review. This is a REVIEW-ONLY seam that does NOT:
  - Set verification_complete=True
  - Set cabr_ready=True
  - Set payout_ready=True
  - Trigger payouts
  - Activate DAO transitions
  - Make network calls
  - Issue tokens
  - Perform external attestation

WSP 97 TRUTH BOUNDARIES:
  * DOES:
    - Accept CABRScoreResult + QuorumVerificationResult as inputs
    - Validate presence and consistency of both inputs
    - Produce deterministic consensus decision for REVIEW ONLY
    - Detect truth boundary violations (inputs claiming completion)
    - Generate deterministic record IDs/hashes from input fields
    - Preserve WSP 97 truth fields:
      * verification_complete=False
      * cabr_ready=False
      * payout_ready=False

  X DOES NOT:
    - Issue tokens or UPS
    - Allocate rewards
    - Write to wallet
    - Trigger payouts
    - Activate DAO transitions
    - Make network calls
    - Run cryptographic verification
    - Claim consensus is final
    - Mutate pAVS/proof receipt runtime

Architecture:
  W6 (receipt) -> ProofOfComputeReceipt
  W7 (pAVS)    -> PAVSVerificationResult
  W1 (CABR)    -> CABRScoreResult (scoring decision)
  W1 (quorum)  -> QuorumVerificationResult (quorum enforcement)
  W1 (this)    -> CABRConsensusRecord (combined review decision)

WSP Compliance:
  WSP 11  : Interface contract (explicit, typed)
  WSP 29  : CABR Engine Framework (min_validators=3, consensus logic)
  WSP 97  : System Execution Prompting (truth boundaries)
  WSP 91  : Observability (timestamps, audit fields)

Slice: CABR_CONSENSUS_FINALIZATION_PHASE1
Worker: W1
"""

from __future__ import annotations

import hashlib
import logging
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger("cabr_consensus_finalizer")


def _utc_now() -> datetime:
    """Return current UTC timestamp."""
    return datetime.now(timezone.utc)


def _utc_iso(dt: Optional[datetime]) -> Optional[str]:
    """Convert datetime to ISO string or None."""
    return dt.isoformat() if dt else None


# ---------------------------------------------------------------------------
# Consensus Decision Enum
# ---------------------------------------------------------------------------


class CABRConsensusDecision(str, Enum):
    """
    CABR consensus finalization decision -- deterministic outcome for REVIEW ONLY.

    WSP 97: These decisions describe the REVIEW STATE, not claims of completion.
    """

    NOT_FINALIZED = "not_finalized"
    """Consensus record not finalized. Missing required inputs."""

    REJECTED = "rejected"
    """Consensus rejected. Scoring or quorum failed."""

    ACCEPTED_FOR_REVIEW = "accepted_for_review"
    """Consensus accepted for REVIEW ONLY. Both scoring and quorum passed.
    WSP 97: This does NOT mean cabr_ready=True or payout_ready=True."""

    PENDING_QUORUM = "pending_quorum"
    """Scoring accepted but quorum not yet met. Awaiting additional verifiers."""

    BLOCKED_TRUTH_BOUNDARY = "blocked_truth_boundary"
    """Input claims completion states (verification_complete/cabr_ready/payout_ready=True).
    Phase 1 blocks such inputs as truth boundary violations."""


class CABRConsensusReasonCode(str, Enum):
    """Machine-readable reason codes for consensus decisions."""

    # NOT_FINALIZED reasons
    MISSING_SCORE_RESULT = "missing_score_result"
    """No CABRScoreResult provided. Cannot finalize without scoring."""

    MISSING_QUORUM_RESULT = "missing_quorum_result"
    """No QuorumVerificationResult provided. Cannot finalize without quorum."""

    MISSING_BOTH_RESULTS = "missing_both_results"
    """Both scoring and quorum results missing."""

    # REJECTED reasons (from scoring)
    SCORE_REJECTED_INSUFFICIENT_EVIDENCE = "score_rejected_insufficient_evidence"
    """Scoring rejected: insufficient evidence."""

    SCORE_REJECTED_MISSING_IDENTITY = "score_rejected_missing_identity"
    """Scoring rejected: missing identity fields."""

    SCORE_REJECTED_DUPLICATE_VERIFIERS = "score_rejected_duplicate_verifiers"
    """Scoring rejected: duplicate verifier IDs."""

    SCORE_REJECTED_PAVS_FAILED = "score_rejected_pavs_failed"
    """Scoring rejected: pAVS failure state."""

    SCORE_REJECTED_TRUTH_BOUNDARY = "score_rejected_truth_boundary"
    """Scoring rejected: input claimed completion states."""

    SCORE_REJECTED_OTHER = "score_rejected_other"
    """Scoring rejected: other reason."""

    # REJECTED reasons (from quorum)
    QUORUM_REJECTED_DUPLICATE_VERIFIERS = "quorum_rejected_duplicate_verifiers"
    """Quorum rejected: duplicate verifier IDs in attestations."""

    QUORUM_REJECTED_MISSING_VERIFIER_ID = "quorum_rejected_missing_verifier_id"
    """Quorum rejected: attestation missing verifier_id."""

    QUORUM_REJECTED_INVALID_SIGNATURE = "quorum_rejected_invalid_signature"
    """Quorum rejected: invalid verifier signature (Phase 1: unsupported)."""

    QUORUM_REJECTED_MISSING_IDENTITY = "quorum_rejected_missing_identity"
    """Quorum rejected: missing identity fields."""

    QUORUM_REJECTED_OTHER = "quorum_rejected_other"
    """Quorum rejected: other reason."""

    # PENDING_QUORUM reasons
    QUORUM_NOT_MET_ZERO_ATTESTATIONS = "quorum_not_met_zero_attestations"
    """Quorum not met: no attestations provided."""

    QUORUM_NOT_MET_INSUFFICIENT_VERIFIERS = "quorum_not_met_insufficient_verifiers"
    """Quorum not met: verifier count below min_validators."""

    QUORUM_MET_THRESHOLD_NOT_MET = "quorum_met_threshold_not_met"
    """Quorum met but consensus score below threshold."""

    SCORE_PENDING_QUORUM = "score_pending_quorum"
    """Scoring accepted but marked pending quorum."""

    # ACCEPTED_FOR_REVIEW reasons
    OK_SCORE_ACCEPTED_QUORUM_MET = "ok_score_accepted_quorum_met"
    """Scoring accepted, quorum met, threshold met. Accepted for review."""

    OK_SCORE_ACCEPTED_DRY_RUN = "ok_score_accepted_dry_run"
    """Scoring accepted (dry-run), quorum met (dry-run). Accepted for review only."""

    # BLOCKED_TRUTH_BOUNDARY reasons
    INPUT_VERIFICATION_COMPLETE_TRUE = "input_verification_complete_true"
    """Input score result has verification_complete=True. Blocked."""

    INPUT_CABR_READY_TRUE = "input_cabr_ready_true"
    """Input score result has cabr_ready=True. Blocked."""

    INPUT_PAYOUT_READY_TRUE = "input_payout_ready_true"
    """Input score result has payout_ready=True. Blocked."""

    QUORUM_VERIFICATION_COMPLETE_TRUE = "quorum_verification_complete_true"
    """Input quorum result has verification_complete=True. Blocked."""

    QUORUM_CABR_READY_TRUE = "quorum_cabr_ready_true"
    """Input quorum result has cabr_ready=True. Blocked."""

    QUORUM_PAYOUT_READY_TRUE = "quorum_payout_ready_true"
    """Input quorum result has payout_ready=True. Blocked."""


# ---------------------------------------------------------------------------
# Input/Record Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class CABRConsensusInput:
    """
    Input for consensus finalization.

    Combines CABRScoreResult and QuorumVerificationResult.
    """

    # === Required Fields ===
    score_result: Optional[Dict[str, Any]] = None
    """CABRScoreResult as dict (from to_dict())."""

    quorum_result: Optional[Dict[str, Any]] = None
    """QuorumVerificationResult as dict (from to_dict())."""

    # === Optional Context ===
    receipt_id: Optional[str] = None
    """Receipt ID for correlation (auto-extracted from results if not provided)."""

    job_id: Optional[str] = None
    """Job ID for correlation (auto-extracted from results if not provided)."""

    tenant_id: Optional[str] = None
    """Tenant ID for correlation (auto-extracted from results if not provided)."""

    foundup_id: Optional[str] = None
    """FoundUp ID if scoped."""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict."""
        return {
            "score_result": self.score_result,
            "quorum_result": self.quorum_result,
            "receipt_id": self.receipt_id,
            "job_id": self.job_id,
            "tenant_id": self.tenant_id,
            "foundup_id": self.foundup_id,
        }


@dataclass
class CABRConsensusRecord:
    """
    Consensus record for CABR finalization -- REVIEW ONLY.

    Contains deterministic consensus decision with WSP 97 truth boundaries.
    This record does NOT represent final consensus or payout approval.
    """

    # === Record Identity ===
    record_id: str
    """Unique record identifier. Format: ccr_{receipt_suffix}_{timestamp}_{random}."""

    record_hash: str
    """Deterministic hash of input fields for integrity verification."""

    # === Source Identity ===
    receipt_id: str
    """Source receipt identifier."""

    job_id: str
    """Source job identifier."""

    tenant_id: str
    """Actor scope / owner."""

    # === Score Reference ===
    score_id: Optional[str] = None
    """Reference to CABRScoreResult.score_id."""

    score_decision: Optional[str] = None
    """CABRScoreResult.decision value."""

    score_reason_code: Optional[str] = None
    """CABRScoreResult.reason_code value."""

    # === Quorum Reference ===
    quorum_id: Optional[str] = None
    """Reference to QuorumVerificationResult.quorum_id."""

    quorum_decision: Optional[str] = None
    """QuorumVerificationResult.decision value."""

    quorum_reason_code: Optional[str] = None
    """QuorumVerificationResult.reason_code value."""

    # === Consensus Decision ===
    decision: CABRConsensusDecision = CABRConsensusDecision.NOT_FINALIZED
    """Finalization decision for REVIEW ONLY."""

    reason_code: CABRConsensusReasonCode = CABRConsensusReasonCode.MISSING_BOTH_RESULTS
    """Machine-readable reason for decision."""

    reason_human: str = ""
    """Operator-readable explanation."""

    # === Quorum Metrics ===
    quorum_met: bool = False
    """True if quorum was met (from quorum result)."""

    threshold_met: bool = False
    """True if consensus threshold was met (from quorum result)."""

    unique_verifiers: int = 0
    """Number of unique verifiers (from quorum result)."""

    consensus_score: float = 0.0
    """Consensus score (from quorum result)."""

    # === Evidence Metrics ===
    evidence_present: bool = False
    """True if evidence was present (from score result)."""

    evidence_count: int = 0
    """Number of evidence refs (from score result)."""

    # === Execution Mode ===
    is_dry_run: bool = False
    """True if source execution was dry-run."""

    is_simulated: bool = False
    """True if source execution was simulated."""

    # === WSP 97 Truth Fields (OUTPUT - always False in Phase 1) ===
    verification_complete: bool = False
    """Always False in Phase 1. No full verification performed."""

    cabr_ready: bool = False
    """Always False in Phase 1. No CABR consensus finalized."""

    payout_ready: bool = False
    """Always False in Phase 1. No payout engine exists."""

    # === Timestamps ===
    finalized_at: datetime = field(default_factory=_utc_now)
    """When this consensus record was created."""

    # === Audit Fields ===
    finalizer_version: str = "0.1.0"
    """CABR consensus finalizer version."""

    input_snapshot: Optional[Dict[str, Any]] = None
    """Optional: Input snapshot for audit trail."""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict."""
        return {
            "record_id": self.record_id,
            "record_hash": self.record_hash,
            "receipt_id": self.receipt_id,
            "job_id": self.job_id,
            "tenant_id": self.tenant_id,
            "score_id": self.score_id,
            "score_decision": self.score_decision,
            "score_reason_code": self.score_reason_code,
            "quorum_id": self.quorum_id,
            "quorum_decision": self.quorum_decision,
            "quorum_reason_code": self.quorum_reason_code,
            "decision": self.decision.value,
            "reason_code": self.reason_code.value,
            "reason_human": self.reason_human,
            "quorum_met": self.quorum_met,
            "threshold_met": self.threshold_met,
            "unique_verifiers": self.unique_verifiers,
            "consensus_score": self.consensus_score,
            "evidence_present": self.evidence_present,
            "evidence_count": self.evidence_count,
            "is_dry_run": self.is_dry_run,
            "is_simulated": self.is_simulated,
            "verification_complete": self.verification_complete,
            "cabr_ready": self.cabr_ready,
            "payout_ready": self.payout_ready,
            "finalized_at": _utc_iso(self.finalized_at),
            "finalizer_version": self.finalizer_version,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CABRConsensusRecord":
        """Deserialize from dict."""
        record = cls(
            record_id=data["record_id"],
            record_hash=data["record_hash"],
            receipt_id=data["receipt_id"],
            job_id=data["job_id"],
            tenant_id=data["tenant_id"],
            score_id=data.get("score_id"),
            score_decision=data.get("score_decision"),
            score_reason_code=data.get("score_reason_code"),
            quorum_id=data.get("quorum_id"),
            quorum_decision=data.get("quorum_decision"),
            quorum_reason_code=data.get("quorum_reason_code"),
            decision=CABRConsensusDecision(data["decision"]),
            reason_code=CABRConsensusReasonCode(data["reason_code"]),
            reason_human=data.get("reason_human", ""),
            quorum_met=data.get("quorum_met", False),
            threshold_met=data.get("threshold_met", False),
            unique_verifiers=data.get("unique_verifiers", 0),
            consensus_score=data.get("consensus_score", 0.0),
            evidence_present=data.get("evidence_present", False),
            evidence_count=data.get("evidence_count", 0),
            is_dry_run=data.get("is_dry_run", False),
            is_simulated=data.get("is_simulated", False),
            verification_complete=data.get("verification_complete", False),
            cabr_ready=data.get("cabr_ready", False),
            payout_ready=data.get("payout_ready", False),
            finalizer_version=data.get("finalizer_version", "0.1.0"),
        )

        finalized_at = data.get("finalized_at")
        if finalized_at:
            record.finalized_at = datetime.fromisoformat(finalized_at)

        return record


# ---------------------------------------------------------------------------
# Record ID and Hash Generation
# ---------------------------------------------------------------------------


def generate_record_id(receipt_id: str) -> str:
    """
    Generate unique record ID from receipt ID.

    Format: ccr_{receipt_suffix}_{timestamp_hex}_{random_hex}
    Example: ccr_extract_18a3b2c1_66d1a2b3_abc123
    """
    parts = receipt_id.split("_")
    if len(parts) >= 2:
        suffix = f"{parts[1]}"[:12]
    else:
        suffix = receipt_id[:12] if receipt_id else "unknown"

    timestamp_hex = hex(int(_utc_now().timestamp()))[2:][:8]
    random_hex = secrets.token_hex(3)
    return f"ccr_{suffix}_{timestamp_hex}_{random_hex}"


def generate_record_hash(
    receipt_id: str,
    job_id: str,
    tenant_id: str,
    score_id: Optional[str],
    quorum_id: Optional[str],
    score_decision: Optional[str],
    quorum_decision: Optional[str],
) -> str:
    """
    Generate deterministic hash from input fields.

    This hash is stable for the same inputs and can be used for
    integrity verification and deduplication.
    """
    hash_input = (
        f"receipt:{receipt_id}|"
        f"job:{job_id}|"
        f"tenant:{tenant_id}|"
        f"score_id:{score_id or 'none'}|"
        f"quorum_id:{quorum_id or 'none'}|"
        f"score_decision:{score_decision or 'none'}|"
        f"quorum_decision:{quorum_decision or 'none'}"
    )
    return hashlib.sha256(hash_input.encode("utf-8")).hexdigest()[:32]


# ---------------------------------------------------------------------------
# Core Finalization Logic
# ---------------------------------------------------------------------------


def _extract_identity(
    consensus_input: CABRConsensusInput,
) -> tuple[str, str, str]:
    """
    Extract identity fields from input or nested results.

    Returns (receipt_id, job_id, tenant_id).
    """
    receipt_id = consensus_input.receipt_id or ""
    job_id = consensus_input.job_id or ""
    tenant_id = consensus_input.tenant_id or ""

    # Try to extract from score_result if not provided
    if consensus_input.score_result:
        if not receipt_id:
            receipt_id = consensus_input.score_result.get("receipt_id", "")
        if not job_id:
            job_id = consensus_input.score_result.get("job_id", "")
        if not tenant_id:
            tenant_id = consensus_input.score_result.get("tenant_id", "")

    # Try to extract from quorum_result if still not found
    if consensus_input.quorum_result:
        if not receipt_id:
            receipt_id = consensus_input.quorum_result.get("receipt_id", "")
        if not job_id:
            job_id = consensus_input.quorum_result.get("job_id", "")
        if not tenant_id:
            tenant_id = consensus_input.quorum_result.get("tenant_id", "")

    return receipt_id, job_id, tenant_id


def _check_truth_boundaries(
    score_result: Optional[Dict[str, Any]],
    quorum_result: Optional[Dict[str, Any]],
) -> Optional[tuple[CABRConsensusDecision, CABRConsensusReasonCode, str]]:
    """
    Check for WSP 97 truth boundary violations in inputs.

    Returns (decision, reason_code, reason_human) if violated, None if clean.
    """
    # Check score result truth boundaries
    if score_result:
        if score_result.get("verification_complete", False):
            return (
                CABRConsensusDecision.BLOCKED_TRUTH_BOUNDARY,
                CABRConsensusReasonCode.INPUT_VERIFICATION_COMPLETE_TRUE,
                "Input score result has verification_complete=True. "
                "Phase 1 finalization does not accept already-completed verification claims.",
            )
        if score_result.get("cabr_ready", False):
            return (
                CABRConsensusDecision.BLOCKED_TRUTH_BOUNDARY,
                CABRConsensusReasonCode.INPUT_CABR_READY_TRUE,
                "Input score result has cabr_ready=True. "
                "Phase 1 finalization does not accept cabr_ready claims.",
            )
        if score_result.get("payout_ready", False):
            return (
                CABRConsensusDecision.BLOCKED_TRUTH_BOUNDARY,
                CABRConsensusReasonCode.INPUT_PAYOUT_READY_TRUE,
                "Input score result has payout_ready=True. "
                "Phase 1 finalization does not accept payout_ready claims.",
            )

    # Check quorum result truth boundaries
    if quorum_result:
        if quorum_result.get("verification_complete", False):
            return (
                CABRConsensusDecision.BLOCKED_TRUTH_BOUNDARY,
                CABRConsensusReasonCode.QUORUM_VERIFICATION_COMPLETE_TRUE,
                "Input quorum result has verification_complete=True. "
                "Phase 1 finalization does not accept already-completed verification claims.",
            )
        if quorum_result.get("cabr_ready", False):
            return (
                CABRConsensusDecision.BLOCKED_TRUTH_BOUNDARY,
                CABRConsensusReasonCode.QUORUM_CABR_READY_TRUE,
                "Input quorum result has cabr_ready=True. "
                "Phase 1 finalization does not accept cabr_ready claims.",
            )
        if quorum_result.get("payout_ready", False):
            return (
                CABRConsensusDecision.BLOCKED_TRUTH_BOUNDARY,
                CABRConsensusReasonCode.QUORUM_PAYOUT_READY_TRUE,
                "Input quorum result has payout_ready=True. "
                "Phase 1 finalization does not accept payout_ready claims.",
            )

    return None


def _evaluate_score_rejection(
    score_decision: str,
) -> Optional[CABRConsensusReasonCode]:
    """
    Map scoring rejection decisions to consensus reason codes.

    Returns reason code if rejected, None if not rejected.
    """
    rejection_mapping = {
        "rejected_insufficient_evidence": CABRConsensusReasonCode.SCORE_REJECTED_INSUFFICIENT_EVIDENCE,
        "rejected_missing_identity": CABRConsensusReasonCode.SCORE_REJECTED_MISSING_IDENTITY,
        "rejected_duplicate_verifiers": CABRConsensusReasonCode.SCORE_REJECTED_DUPLICATE_VERIFIERS,
        "rejected_pavs_failed": CABRConsensusReasonCode.SCORE_REJECTED_PAVS_FAILED,
        "rejected_truth_boundary": CABRConsensusReasonCode.SCORE_REJECTED_TRUTH_BOUNDARY,
    }

    decision_lower = score_decision.lower()
    if decision_lower.startswith("rejected"):
        return rejection_mapping.get(decision_lower, CABRConsensusReasonCode.SCORE_REJECTED_OTHER)

    return None


def _evaluate_quorum_rejection(
    quorum_decision: str,
    quorum_reason_code: str,
) -> Optional[CABRConsensusReasonCode]:
    """
    Map quorum rejection decisions to consensus reason codes.

    Returns reason code if rejected, None if not rejected.
    """
    if quorum_decision.lower() == "consensus_rejected":
        reason_mapping = {
            "rejected_duplicate_verifier_ids": CABRConsensusReasonCode.QUORUM_REJECTED_DUPLICATE_VERIFIERS,
            "rejected_missing_verifier_id": CABRConsensusReasonCode.QUORUM_REJECTED_MISSING_VERIFIER_ID,
            "rejected_invalid_signature": CABRConsensusReasonCode.QUORUM_REJECTED_INVALID_SIGNATURE,
            "rejected_missing_receipt_id": CABRConsensusReasonCode.QUORUM_REJECTED_MISSING_IDENTITY,
            "rejected_missing_job_id": CABRConsensusReasonCode.QUORUM_REJECTED_MISSING_IDENTITY,
        }
        return reason_mapping.get(
            quorum_reason_code.lower(),
            CABRConsensusReasonCode.QUORUM_REJECTED_OTHER,
        )

    return None


def _evaluate_pending_quorum(
    score_decision: str,
    quorum_decision: str,
    quorum_reason_code: str,
) -> Optional[CABRConsensusReasonCode]:
    """
    Determine if consensus should be PENDING_QUORUM.

    Returns reason code if pending, None if not pending.
    """
    # Check if scoring is pending quorum
    if score_decision.lower() == "accepted_for_review_pending_quorum":
        return CABRConsensusReasonCode.SCORE_PENDING_QUORUM

    # Check if quorum is not met
    if quorum_decision.lower() == "quorum_not_met":
        if quorum_reason_code.lower() == "quorum_zero_attestations":
            return CABRConsensusReasonCode.QUORUM_NOT_MET_ZERO_ATTESTATIONS
        else:
            return CABRConsensusReasonCode.QUORUM_NOT_MET_INSUFFICIENT_VERIFIERS

    # Check if quorum met but threshold not met
    if quorum_decision.lower() == "quorum_met_pending_consensus":
        return CABRConsensusReasonCode.QUORUM_MET_THRESHOLD_NOT_MET

    return None


# ---------------------------------------------------------------------------
# Public API: Finalize Consensus
# ---------------------------------------------------------------------------


def finalize_cabr_consensus(
    consensus_input: CABRConsensusInput,
    include_input_snapshot: bool = False,
) -> CABRConsensusRecord:
    """
    Finalize CABR consensus from scoring and quorum results.

    Combines CABRScoreResult and QuorumVerificationResult into a single
    consensus record for REVIEW ONLY. Does NOT claim final consensus,
    payout readiness, or verification completion.

    Decision tree (fail-closed):
      1. Missing both results -> NOT_FINALIZED
      2. Missing score result -> NOT_FINALIZED (fail closed)
      3. Missing quorum result -> PENDING_QUORUM (need quorum to finalize)
      4. Truth boundary violation in inputs -> BLOCKED_TRUTH_BOUNDARY
      5. Scoring rejected -> REJECTED
      6. Quorum rejected -> REJECTED
      7. Scoring pending quorum or quorum not met -> PENDING_QUORUM
      8. Scoring accepted + quorum accepted -> ACCEPTED_FOR_REVIEW

    Args:
        consensus_input: CABRConsensusInput with score_result and quorum_result
        include_input_snapshot: If True, include input dict in record

    Returns:
        CABRConsensusRecord with deterministic decision and WSP 97 truth fields

    WSP 97 Truth Fields (always False in Phase 1):
        verification_complete = False
        cabr_ready = False
        payout_ready = False
    """
    # Extract identity
    receipt_id, job_id, tenant_id = _extract_identity(consensus_input)

    # Get references
    score_result = consensus_input.score_result
    quorum_result = consensus_input.quorum_result

    # Extract IDs for hash
    score_id = score_result.get("score_id") if score_result else None
    quorum_id = quorum_result.get("quorum_id") if quorum_result else None
    score_decision = score_result.get("decision") if score_result else None
    quorum_decision = quorum_result.get("decision") if quorum_result else None
    quorum_reason_code = quorum_result.get("reason_code") if quorum_result else None

    # Generate record ID and hash
    record_id = generate_record_id(receipt_id)
    record_hash = generate_record_hash(
        receipt_id=receipt_id,
        job_id=job_id,
        tenant_id=tenant_id,
        score_id=score_id,
        quorum_id=quorum_id,
        score_decision=score_decision,
        quorum_decision=quorum_decision,
    )

    # Build base fields
    base_fields = {
        "record_id": record_id,
        "record_hash": record_hash,
        "receipt_id": receipt_id,
        "job_id": job_id,
        "tenant_id": tenant_id,
        "score_id": score_id,
        "score_decision": score_decision,
        "score_reason_code": score_result.get("reason_code") if score_result else None,
        "quorum_id": quorum_id,
        "quorum_decision": quorum_decision,
        "quorum_reason_code": quorum_reason_code,
        # WSP 97: Always False
        "verification_complete": False,
        "cabr_ready": False,
        "payout_ready": False,
    }

    # Step 1: Check for missing inputs (fail closed)
    if not score_result and not quorum_result:
        logger.warning("[CABR-CONSENSUS] Missing both score and quorum results")
        record = CABRConsensusRecord(
            **base_fields,
            decision=CABRConsensusDecision.NOT_FINALIZED,
            reason_code=CABRConsensusReasonCode.MISSING_BOTH_RESULTS,
            reason_human="Both scoring and quorum results missing. Cannot finalize consensus.",
        )
        if include_input_snapshot:
            record.input_snapshot = consensus_input.to_dict()
        return record

    if not score_result:
        logger.warning("[CABR-CONSENSUS] Missing score result, failing closed")
        record = CABRConsensusRecord(
            **base_fields,
            decision=CABRConsensusDecision.NOT_FINALIZED,
            reason_code=CABRConsensusReasonCode.MISSING_SCORE_RESULT,
            reason_human="CABRScoreResult missing. Cannot finalize without scoring decision.",
            # Extract quorum metrics if available
            quorum_met=quorum_result.get("quorum_met", False) if quorum_result else False,
            threshold_met=quorum_result.get("threshold_met", False) if quorum_result else False,
            unique_verifiers=quorum_result.get("unique_verifiers", 0) if quorum_result else 0,
            consensus_score=quorum_result.get("consensus_score", 0.0) if quorum_result else 0.0,
        )
        if include_input_snapshot:
            record.input_snapshot = consensus_input.to_dict()
        return record

    if not quorum_result:
        logger.warning("[CABR-CONSENSUS] Missing quorum result, returning pending quorum")
        record = CABRConsensusRecord(
            **base_fields,
            decision=CABRConsensusDecision.PENDING_QUORUM,
            reason_code=CABRConsensusReasonCode.MISSING_QUORUM_RESULT,
            reason_human="QuorumVerificationResult missing. Pending quorum evaluation.",
            # Extract score metrics
            evidence_present=score_result.get("evidence_present", False),
            evidence_count=score_result.get("evidence_count", 0),
            is_dry_run=score_result.get("is_dry_run", False),
            is_simulated=score_result.get("is_simulated", False),
        )
        if include_input_snapshot:
            record.input_snapshot = consensus_input.to_dict()
        return record

    # Step 2: Check truth boundaries
    truth_violation = _check_truth_boundaries(score_result, quorum_result)
    if truth_violation:
        decision, reason_code, reason_human = truth_violation
        logger.warning("[CABR-CONSENSUS] Truth boundary violation: %s", reason_code.value)
        record = CABRConsensusRecord(
            **base_fields,
            decision=decision,
            reason_code=reason_code,
            reason_human=reason_human,
            # Extract metrics
            quorum_met=quorum_result.get("quorum_met", False),
            threshold_met=quorum_result.get("threshold_met", False),
            unique_verifiers=quorum_result.get("unique_verifiers", 0),
            consensus_score=quorum_result.get("consensus_score", 0.0),
            evidence_present=score_result.get("evidence_present", False),
            evidence_count=score_result.get("evidence_count", 0),
            is_dry_run=score_result.get("is_dry_run", False),
            is_simulated=score_result.get("is_simulated", False),
        )
        if include_input_snapshot:
            record.input_snapshot = consensus_input.to_dict()
        return record

    # Step 3: Check for scoring rejection
    score_rejection = _evaluate_score_rejection(score_decision or "")
    if score_rejection:
        logger.info("[CABR-CONSENSUS] Scoring rejected: %s", score_rejection.value)
        record = CABRConsensusRecord(
            **base_fields,
            decision=CABRConsensusDecision.REJECTED,
            reason_code=score_rejection,
            reason_human=f"Scoring rejected: {score_result.get('reason_human', 'Unknown reason')}",
            quorum_met=quorum_result.get("quorum_met", False),
            threshold_met=quorum_result.get("threshold_met", False),
            unique_verifiers=quorum_result.get("unique_verifiers", 0),
            consensus_score=quorum_result.get("consensus_score", 0.0),
            evidence_present=score_result.get("evidence_present", False),
            evidence_count=score_result.get("evidence_count", 0),
            is_dry_run=score_result.get("is_dry_run", False),
            is_simulated=score_result.get("is_simulated", False),
        )
        if include_input_snapshot:
            record.input_snapshot = consensus_input.to_dict()
        return record

    # Step 4: Check for quorum rejection
    quorum_rejection = _evaluate_quorum_rejection(
        quorum_decision or "",
        quorum_reason_code or "",
    )
    if quorum_rejection:
        logger.info("[CABR-CONSENSUS] Quorum rejected: %s", quorum_rejection.value)
        record = CABRConsensusRecord(
            **base_fields,
            decision=CABRConsensusDecision.REJECTED,
            reason_code=quorum_rejection,
            reason_human=f"Quorum rejected: {quorum_result.get('reason_human', 'Unknown reason')}",
            quorum_met=False,
            threshold_met=False,
            unique_verifiers=quorum_result.get("unique_verifiers", 0),
            consensus_score=quorum_result.get("consensus_score", 0.0),
            evidence_present=score_result.get("evidence_present", False),
            evidence_count=score_result.get("evidence_count", 0),
            is_dry_run=score_result.get("is_dry_run", False),
            is_simulated=score_result.get("is_simulated", False),
        )
        if include_input_snapshot:
            record.input_snapshot = consensus_input.to_dict()
        return record

    # Step 5: Check for pending quorum
    pending_reason = _evaluate_pending_quorum(
        score_decision or "",
        quorum_decision or "",
        quorum_reason_code or "",
    )
    if pending_reason:
        logger.info("[CABR-CONSENSUS] Pending quorum: %s", pending_reason.value)
        record = CABRConsensusRecord(
            **base_fields,
            decision=CABRConsensusDecision.PENDING_QUORUM,
            reason_code=pending_reason,
            reason_human=f"Consensus pending: {quorum_result.get('reason_human', 'Awaiting quorum')}",
            quorum_met=quorum_result.get("quorum_met", False),
            threshold_met=quorum_result.get("threshold_met", False),
            unique_verifiers=quorum_result.get("unique_verifiers", 0),
            consensus_score=quorum_result.get("consensus_score", 0.0),
            evidence_present=score_result.get("evidence_present", False),
            evidence_count=score_result.get("evidence_count", 0),
            is_dry_run=score_result.get("is_dry_run", False),
            is_simulated=score_result.get("is_simulated", False),
        )
        if include_input_snapshot:
            record.input_snapshot = consensus_input.to_dict()
        return record

    # Step 6: Both accepted -> ACCEPTED_FOR_REVIEW
    is_dry_run = score_result.get("is_dry_run", False) or quorum_result.get("is_dry_run", False)

    if is_dry_run:
        reason_code = CABRConsensusReasonCode.OK_SCORE_ACCEPTED_DRY_RUN
        reason_human = (
            f"Dry-run consensus accepted for review. "
            f"{score_result.get('evidence_count', 0)} evidence ref(s), "
            f"{quorum_result.get('unique_verifiers', 0)} verifier(s). "
            "WSP 97: cabr_ready=False, payout_ready=False."
        )
    else:
        reason_code = CABRConsensusReasonCode.OK_SCORE_ACCEPTED_QUORUM_MET
        reason_human = (
            f"Consensus accepted for review. "
            f"Scoring: {score_decision}, Quorum: {quorum_decision}. "
            f"{quorum_result.get('unique_verifiers', 0)} verifier(s), "
            f"consensus score {quorum_result.get('consensus_score', 0.0):.3f}. "
            "WSP 97: cabr_ready=False, payout_ready=False."
        )

    logger.info(
        "[CABR-CONSENSUS] Finalized receipt %s -> ACCEPTED_FOR_REVIEW, reason=%s",
        receipt_id,
        reason_code.value,
    )

    record = CABRConsensusRecord(
        **base_fields,
        decision=CABRConsensusDecision.ACCEPTED_FOR_REVIEW,
        reason_code=reason_code,
        reason_human=reason_human,
        quorum_met=quorum_result.get("quorum_met", False),
        threshold_met=quorum_result.get("threshold_met", False),
        unique_verifiers=quorum_result.get("unique_verifiers", 0),
        consensus_score=quorum_result.get("consensus_score", 0.0),
        evidence_present=score_result.get("evidence_present", False),
        evidence_count=score_result.get("evidence_count", 0),
        is_dry_run=is_dry_run,
        is_simulated=score_result.get("is_simulated", False),
    )

    if include_input_snapshot:
        record.input_snapshot = consensus_input.to_dict()

    return record


# ---------------------------------------------------------------------------
# Public API: Batch Finalization
# ---------------------------------------------------------------------------


def finalize_cabr_consensus_batch(
    inputs: List[CABRConsensusInput],
) -> List[CABRConsensusRecord]:
    """
    Finalize multiple consensus inputs in batch.

    Deterministic: Results are in same order as inputs.
    No network calls, no state mutation.

    Args:
        inputs: List of CABRConsensusInput to finalize

    Returns:
        List of CABRConsensusRecord in same order as inputs
    """
    return [finalize_cabr_consensus(inp) for inp in inputs]
