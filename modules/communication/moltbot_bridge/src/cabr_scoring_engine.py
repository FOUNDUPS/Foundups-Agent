#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CABR Scoring Engine Phase 1 — Deterministic Internal Sovereign Consensus Scoring

Implements the first runtime scoring seam for CABR (Consensus-Driven Autonomous
Benefit Rate) per WSP 29 and the consensus infrastructure audit (PR #574).

This module provides DETERMINISTIC scoring decisions without:
  - Token issuance
  - Payout triggering
  - External attestation
  - Network calls
  - DAO activation
  - Live delegation

WSP 97 TRUTH BOUNDARIES:
  * DOES:
    - Accept ProofOfComputeReceipt or PAVSVerificationResult for scoring
    - Evaluate evidence presence/absence
    - Evaluate verifier count against min_validators threshold (WSP 29: default 3)
    - Detect duplicate verifier IDs
    - Map pAVS decision to scoring decision
    - Return deterministic reason codes
    - Preserve WSP 97 truth fields (verification_complete=False, cabr_ready=False, payout_ready=False)
    - Mark dry_run/simulated execution for review only

  X DOES NOT:
    - Issue tokens or UPS
    - Allocate rewards
    - Write to wallet
    - Run cryptographic verification
    - Claim verification is complete
    - Claim CABR is ready for consensus
    - Claim payout is ready
    - Make network calls
    - Mutate FAM/pAVS runtime state

Architecture:
  W6 (receipt) -> ProofOfComputeReceipt
  W7 (pAVS)    -> PAVSVerificationResult
  W1 (this)    -> CABRScoreResult (deterministic scoring decision)

WSP Compliance:
  WSP 11  : Interface contract (explicit, typed)
  WSP 29  : CABR Engine Framework (min_validators=3, quorum logic)
  WSP 97  : System Execution Prompting (truth boundaries)
  WSP 91  : Observability (timestamps, audit fields)

Slice: CABR_RUNTIME_SCORING_ENGINE_PHASE1
Worker: W1
"""

from __future__ import annotations

import logging
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger("cabr_scoring_engine")


def _utc_now() -> datetime:
    """Return current UTC timestamp."""
    return datetime.now(timezone.utc)


def _utc_iso(dt: Optional[datetime]) -> Optional[str]:
    """Convert datetime to ISO string or None."""
    return dt.isoformat() if dt else None


# ---------------------------------------------------------------------------
# WSP 29 Configuration
# ---------------------------------------------------------------------------

# WSP 29 Section 1.2: min_validators default
MIN_VALIDATORS_DEFAULT: int = 3

# Consensus threshold from WSP 29 Section 1.2
CONSENSUS_THRESHOLD: float = 0.382


# ---------------------------------------------------------------------------
# Scoring Decision Enum
# ---------------------------------------------------------------------------


class CABRScoreDecision(str, Enum):
    """
    CABR scoring decision — deterministic outcome of scoring evaluation.

    WSP 97: These decisions describe WHAT WE SCORED, not claims of completion.
    """

    NOT_EVALUATED = "not_evaluated"
    """Receipt/result has not been evaluated by CABR scoring."""

    ACCEPTED_FOR_REVIEW = "accepted_for_review"
    """Evidence present and valid, accepted for human/consensus review. NOT final."""

    ACCEPTED_FOR_REVIEW_PENDING_QUORUM = "accepted_for_review_pending_quorum"
    """Evidence valid but verifier count below quorum. Awaiting additional verifiers."""

    REJECTED_INSUFFICIENT_EVIDENCE = "rejected_insufficient_evidence"
    """Rejected: No evidence or evidence_refs empty. Cannot score without evidence."""

    REJECTED_TRUTH_BOUNDARY = "rejected_truth_boundary"
    """Rejected: Input claims verification_complete/cabr_ready/payout_ready = True.
    Phase 1 does not accept already-completed claims."""

    REJECTED_QUORUM_NOT_MET = "rejected_quorum_not_met"
    """Rejected: Verifier count below min_validators and no dry_run exemption."""

    REJECTED_DUPLICATE_VERIFIERS = "rejected_duplicate_verifiers"
    """Rejected: Duplicate verifier IDs detected. Unique verifiers required."""

    REJECTED_PAVS_FAILED = "rejected_pavs_failed"
    """Rejected: pAVS verification result indicates failure/blocked state."""

    REJECTED_MISSING_IDENTITY = "rejected_missing_identity"
    """Rejected: Required identity fields missing (receipt_id, job_id, tenant_id)."""


class CABRScoreReason(str, Enum):
    """Machine-readable reason codes for CABR scoring decisions."""

    # Acceptance reasons
    OK_EVIDENCE_PRESENT_QUORUM_MET = "ok_evidence_present_quorum_met"
    """Evidence present and verifier quorum met. Accepted for review."""

    OK_EVIDENCE_PRESENT_DRY_RUN = "ok_evidence_present_dry_run"
    """Evidence present, dry-run mode. Accepted for review only (not consensus)."""

    OK_EVIDENCE_PRESENT_PENDING_QUORUM = "ok_evidence_present_pending_quorum"
    """Evidence present but quorum not yet met. Accepted for review pending verifiers."""

    # Rejection reasons
    REJECTED_NO_EVIDENCE = "rejected_no_evidence"
    """No evidence_refs provided. Cannot score."""

    REJECTED_EMPTY_EVIDENCE = "rejected_empty_evidence"
    """evidence_refs is empty list. Cannot score."""

    REJECTED_VERIFICATION_COMPLETE_CLAIMED = "rejected_verification_complete_claimed"
    """Input claims verification_complete=True. Phase 1 does not accept."""

    REJECTED_CABR_READY_CLAIMED = "rejected_cabr_ready_claimed"
    """Input claims cabr_ready=True. Phase 1 does not accept."""

    REJECTED_PAYOUT_READY_CLAIMED = "rejected_payout_ready_claimed"
    """Input claims payout_ready=True. Phase 1 does not accept."""

    REJECTED_BELOW_MIN_VALIDATORS = "rejected_below_min_validators"
    """Verifier count below min_validators threshold."""

    REJECTED_DUPLICATE_VERIFIER_IDS = "rejected_duplicate_verifier_ids"
    """Duplicate verifier IDs detected."""

    REJECTED_PAVS_BLOCKED_MISSING_EVIDENCE = "rejected_pavs_blocked_missing_evidence"
    """pAVS returned BLOCKED_MISSING_EVIDENCE."""

    REJECTED_PAVS_BLOCKED_UPSTREAM = "rejected_pavs_blocked_upstream"
    """pAVS returned BLOCKED_UPSTREAM."""

    REJECTED_PAVS_FAILED_INPUT = "rejected_pavs_failed_input"
    """pAVS returned FAILED_INPUT."""

    REJECTED_PAVS_REJECTED_IDENTITY = "rejected_pavs_rejected_identity"
    """pAVS returned REJECTED_MISSING_IDENTITY."""

    REJECTED_PAVS_REJECTED_STATUS = "rejected_pavs_rejected_status"
    """pAVS returned REJECTED_INVALID_STATUS."""

    REJECTED_NO_RECEIPT_ID = "rejected_no_receipt_id"
    """Missing receipt_id in input."""

    REJECTED_NO_JOB_ID = "rejected_no_job_id"
    """Missing job_id in input."""

    REJECTED_NO_TENANT_ID = "rejected_no_tenant_id"
    """Missing tenant_id in input."""

    NOT_EVALUATED = "not_evaluated"
    """Scoring not performed (default state)."""


# ---------------------------------------------------------------------------
# Score Input / Result Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class CABRScoreInput:
    """
    Input for CABR scoring evaluation.

    Can be populated from ProofOfComputeReceipt, PAVSVerificationResult, or dict.
    """

    # === Identity Fields ===
    receipt_id: str
    """Receipt identifier from ProofOfComputeReceipt."""

    job_id: str
    """Source job identifier."""

    tenant_id: str
    """Actor scope / owner."""

    # === Evidence Fields ===
    evidence_refs: List[str] = field(default_factory=list)
    """Evidence references from receipt/verification."""

    evidence_count: int = 0
    """Convenience: len(evidence_refs)."""

    # === Verifier Fields ===
    verifier_ids: List[str] = field(default_factory=list)
    """List of verifier IDs who have attested to this receipt."""

    # === pAVS Decision (if available) ===
    pavs_decision: Optional[str] = None
    """pAVS decision value (e.g., 'accepted_for_review', 'blocked_missing_evidence')."""

    # === Execution Mode ===
    is_dry_run: bool = False
    """True if the source execution was dry-run/simulated."""

    is_simulated: bool = False
    """True if the execution was fully simulated (no real work)."""

    # === WSP 97 Truth Fields (from source) ===
    verification_complete: bool = False
    """From source: If True, indicates completed verification (Phase 1 rejects)."""

    cabr_ready: bool = False
    """From source: If True, indicates CABR is ready (Phase 1 rejects)."""

    payout_ready: bool = False
    """From source: If True, indicates payout is ready (Phase 1 rejects)."""

    # === Metadata ===
    foundup_id: Optional[str] = None
    """Target FoundUp ID if scoped."""

    intent_id: Optional[str] = None
    """Request correlation ID."""

    source_type: str = "unknown"
    """Source type: 'receipt', 'pavs_result', 'dict'."""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict."""
        return {
            "receipt_id": self.receipt_id,
            "job_id": self.job_id,
            "tenant_id": self.tenant_id,
            "evidence_refs": self.evidence_refs,
            "evidence_count": self.evidence_count,
            "verifier_ids": self.verifier_ids,
            "pavs_decision": self.pavs_decision,
            "is_dry_run": self.is_dry_run,
            "is_simulated": self.is_simulated,
            "verification_complete": self.verification_complete,
            "cabr_ready": self.cabr_ready,
            "payout_ready": self.payout_ready,
            "foundup_id": self.foundup_id,
            "intent_id": self.intent_id,
            "source_type": self.source_type,
        }


@dataclass
class CABRScoreResult:
    """
    Result from CABR scoring evaluation.

    Contains deterministic scoring decision with WSP 97 truth boundaries.
    """

    # === Score Identity ===
    score_id: str
    """Unique score identifier. Format: cabr_{receipt_suffix}_{timestamp}_{random}."""

    receipt_id: str
    """Source receipt identifier."""

    job_id: str
    """Source job identifier."""

    tenant_id: str
    """Actor scope / owner."""

    # === Decision Fields ===
    decision: CABRScoreDecision
    """Scoring decision made."""

    reason_code: CABRScoreReason
    """Machine-readable reason for decision."""

    reason_human: str
    """Operator-readable explanation."""

    # === Quorum Fields ===
    verifier_count: int = 0
    """Number of unique verifiers."""

    unique_verifier_count: int = 0
    """Number of unique verifier IDs (after dedup)."""

    min_validators: int = MIN_VALIDATORS_DEFAULT
    """Minimum validators threshold (WSP 29 default: 3)."""

    quorum_met: bool = False
    """True if unique_verifier_count >= min_validators."""

    duplicate_verifiers_detected: bool = False
    """True if duplicate verifier IDs were detected."""

    # === Evidence Fields ===
    evidence_count: int = 0
    """Number of evidence references."""

    evidence_present: bool = False
    """True if evidence_refs is non-empty."""

    # === Execution Mode ===
    is_dry_run: bool = False
    """True if source was dry-run execution."""

    is_simulated: bool = False
    """True if source was fully simulated."""

    # === WSP 97 Truth Fields (OUTPUT - always False in Phase 1) ===
    verification_complete: bool = False
    """Always False in Phase 1. No full verification performed."""

    cabr_ready: bool = False
    """Always False in Phase 1. No CABR consensus exists."""

    payout_ready: bool = False
    """Always False in Phase 1. No payout engine exists."""

    # === pAVS Integration ===
    pavs_decision: Optional[str] = None
    """pAVS decision if available."""

    pavs_passed: bool = False
    """True if pAVS decision indicates acceptance."""

    # === Timestamps ===
    scored_at: datetime = field(default_factory=_utc_now)
    """When this score was calculated."""

    # === Audit Fields ===
    scorer_version: str = "0.1.0"
    """CABR scorer version."""

    input_snapshot: Optional[Dict[str, Any]] = None
    """Optional: Input snapshot for audit trail."""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict."""
        return {
            "score_id": self.score_id,
            "receipt_id": self.receipt_id,
            "job_id": self.job_id,
            "tenant_id": self.tenant_id,
            "decision": self.decision.value,
            "reason_code": self.reason_code.value,
            "reason_human": self.reason_human,
            "verifier_count": self.verifier_count,
            "unique_verifier_count": self.unique_verifier_count,
            "min_validators": self.min_validators,
            "quorum_met": self.quorum_met,
            "duplicate_verifiers_detected": self.duplicate_verifiers_detected,
            "evidence_count": self.evidence_count,
            "evidence_present": self.evidence_present,
            "is_dry_run": self.is_dry_run,
            "is_simulated": self.is_simulated,
            "verification_complete": self.verification_complete,
            "cabr_ready": self.cabr_ready,
            "payout_ready": self.payout_ready,
            "pavs_decision": self.pavs_decision,
            "pavs_passed": self.pavs_passed,
            "scored_at": _utc_iso(self.scored_at),
            "scorer_version": self.scorer_version,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CABRScoreResult":
        """Deserialize from dict."""
        result = cls(
            score_id=data["score_id"],
            receipt_id=data["receipt_id"],
            job_id=data["job_id"],
            tenant_id=data["tenant_id"],
            decision=CABRScoreDecision(data["decision"]),
            reason_code=CABRScoreReason(data["reason_code"]),
            reason_human=data.get("reason_human", ""),
            verifier_count=data.get("verifier_count", 0),
            unique_verifier_count=data.get("unique_verifier_count", 0),
            min_validators=data.get("min_validators", MIN_VALIDATORS_DEFAULT),
            quorum_met=data.get("quorum_met", False),
            duplicate_verifiers_detected=data.get("duplicate_verifiers_detected", False),
            evidence_count=data.get("evidence_count", 0),
            evidence_present=data.get("evidence_present", False),
            is_dry_run=data.get("is_dry_run", False),
            is_simulated=data.get("is_simulated", False),
            verification_complete=data.get("verification_complete", False),
            cabr_ready=data.get("cabr_ready", False),
            payout_ready=data.get("payout_ready", False),
            pavs_decision=data.get("pavs_decision"),
            pavs_passed=data.get("pavs_passed", False),
            scorer_version=data.get("scorer_version", "0.1.0"),
        )

        scored_at = data.get("scored_at")
        if scored_at:
            result.scored_at = datetime.fromisoformat(scored_at)

        return result


# ---------------------------------------------------------------------------
# Score ID Generation
# ---------------------------------------------------------------------------


def generate_score_id(receipt_id: str) -> str:
    """
    Generate unique score ID from receipt ID.

    Format: cabr_{receipt_suffix}_{timestamp_hex}_{random_hex}
    Example: cabr_extract_18a3b2c1_66d1a2b3_abc123
    """
    parts = receipt_id.split("_")
    if len(parts) >= 2:
        suffix = f"{parts[1]}"[:12]
    else:
        suffix = receipt_id[:12]

    timestamp_hex = hex(int(_utc_now().timestamp()))[2:][:8]
    random_hex = secrets.token_hex(3)
    return f"cabr_{suffix}_{timestamp_hex}_{random_hex}"


# ---------------------------------------------------------------------------
# Input Builders
# ---------------------------------------------------------------------------


def build_score_input_from_receipt(
    receipt: Union["ProofOfComputeReceipt", Dict[str, Any]],
    verifier_ids: Optional[List[str]] = None,
) -> CABRScoreInput:
    """
    Build CABRScoreInput from ProofOfComputeReceipt.

    Args:
        receipt: ProofOfComputeReceipt object or dict
        verifier_ids: Optional list of verifier IDs for quorum evaluation

    Returns:
        CABRScoreInput ready for scoring
    """
    if isinstance(receipt, dict):
        return CABRScoreInput(
            receipt_id=receipt.get("receipt_id", ""),
            job_id=receipt.get("job_id", ""),
            tenant_id=receipt.get("tenant_id", ""),
            evidence_refs=receipt.get("evidence_refs", []),
            evidence_count=len(receipt.get("evidence_refs", [])),
            verifier_ids=verifier_ids or [],
            pavs_decision=None,
            is_dry_run=receipt.get("verification_status") == "not_required",
            is_simulated=False,
            verification_complete=False,  # Receipt never claims completion
            cabr_ready=False,  # Receipt always NOT_SUBMITTED
            payout_ready=False,  # Receipt always NOT_EVALUATED
            foundup_id=receipt.get("foundup_id"),
            intent_id=receipt.get("intent_id"),
            source_type="receipt",
        )
    else:
        # Assume ProofOfComputeReceipt object
        from .proof_of_compute_receipt import VerificationStatus

        is_dry_run = receipt.verification_status == VerificationStatus.NOT_REQUIRED
        return CABRScoreInput(
            receipt_id=receipt.receipt_id,
            job_id=receipt.job_id,
            tenant_id=receipt.tenant_id,
            evidence_refs=list(receipt.evidence_refs),
            evidence_count=len(receipt.evidence_refs),
            verifier_ids=verifier_ids or [],
            pavs_decision=None,
            is_dry_run=is_dry_run,
            is_simulated=False,
            verification_complete=False,
            cabr_ready=False,
            payout_ready=False,
            foundup_id=receipt.foundup_id,
            intent_id=receipt.intent_id,
            source_type="receipt",
        )


def build_score_input_from_pavs_result(
    result: Union["PAVSVerificationResult", Dict[str, Any]],
    verifier_ids: Optional[List[str]] = None,
) -> CABRScoreInput:
    """
    Build CABRScoreInput from PAVSVerificationResult.

    Args:
        result: PAVSVerificationResult object or dict
        verifier_ids: Optional list of verifier IDs for quorum evaluation

    Returns:
        CABRScoreInput ready for scoring
    """
    if isinstance(result, dict):
        return CABRScoreInput(
            receipt_id=result.get("receipt_id", ""),
            job_id=result.get("job_id", ""),
            tenant_id=result.get("tenant_id", ""),
            evidence_refs=result.get("evidence_refs", []),
            evidence_count=result.get("evidence_count", 0),
            verifier_ids=verifier_ids or [],
            pavs_decision=result.get("decision"),
            is_dry_run=result.get("decision") == "not_required",
            is_simulated=False,
            verification_complete=result.get("verification_complete", False),
            cabr_ready=result.get("cabr_ready", False),
            payout_ready=result.get("payout_ready", False),
            foundup_id=None,  # Not in PAVS result
            intent_id=None,
            source_type="pavs_result",
        )
    else:
        # Assume PAVSVerificationResult object
        from .pavs_verification_seam import PAVSDecision

        is_dry_run = result.decision == PAVSDecision.NOT_REQUIRED
        return CABRScoreInput(
            receipt_id=result.receipt_id,
            job_id=result.job_id,
            tenant_id=result.tenant_id,
            evidence_refs=list(result.evidence_refs),
            evidence_count=result.evidence_count,
            verifier_ids=verifier_ids or [],
            pavs_decision=result.decision.value,
            is_dry_run=is_dry_run,
            is_simulated=False,
            verification_complete=result.verification_complete,
            cabr_ready=result.cabr_ready,
            payout_ready=result.payout_ready,
            foundup_id=None,
            intent_id=None,
            source_type="pavs_result",
        )


# ---------------------------------------------------------------------------
# Core Scoring Logic
# ---------------------------------------------------------------------------


def _validate_identity(
    score_input: CABRScoreInput,
) -> Optional[CABRScoreResult]:
    """
    Validate required identity fields.

    Returns rejection result if invalid, None if valid.
    """
    if not score_input.receipt_id or not score_input.receipt_id.strip():
        return CABRScoreResult(
            score_id=f"cabr_rejected_{secrets.token_hex(4)}",
            receipt_id="",
            job_id=score_input.job_id,
            tenant_id=score_input.tenant_id,
            decision=CABRScoreDecision.REJECTED_MISSING_IDENTITY,
            reason_code=CABRScoreReason.REJECTED_NO_RECEIPT_ID,
            reason_human="Missing receipt_id. Cannot score without receipt identity.",
        )

    if not score_input.job_id or not score_input.job_id.strip():
        return CABRScoreResult(
            score_id=generate_score_id(score_input.receipt_id),
            receipt_id=score_input.receipt_id,
            job_id="",
            tenant_id=score_input.tenant_id,
            decision=CABRScoreDecision.REJECTED_MISSING_IDENTITY,
            reason_code=CABRScoreReason.REJECTED_NO_JOB_ID,
            reason_human="Missing job_id. Cannot correlate score to source job.",
        )

    if not score_input.tenant_id or not score_input.tenant_id.strip():
        return CABRScoreResult(
            score_id=generate_score_id(score_input.receipt_id),
            receipt_id=score_input.receipt_id,
            job_id=score_input.job_id,
            tenant_id="",
            decision=CABRScoreDecision.REJECTED_MISSING_IDENTITY,
            reason_code=CABRScoreReason.REJECTED_NO_TENANT_ID,
            reason_human="Missing tenant_id. Cannot scope score to actor.",
        )

    return None


def _validate_truth_boundaries(
    score_input: CABRScoreInput,
) -> Optional[CABRScoreResult]:
    """
    Validate WSP 97 truth boundaries.

    Phase 1 rejects inputs claiming verification/CABR/payout completion.

    Returns rejection result if boundaries violated, None if valid.
    """
    if score_input.verification_complete:
        return CABRScoreResult(
            score_id=generate_score_id(score_input.receipt_id),
            receipt_id=score_input.receipt_id,
            job_id=score_input.job_id,
            tenant_id=score_input.tenant_id,
            decision=CABRScoreDecision.REJECTED_TRUTH_BOUNDARY,
            reason_code=CABRScoreReason.REJECTED_VERIFICATION_COMPLETE_CLAIMED,
            reason_human=(
                "Input claims verification_complete=True. "
                "Phase 1 CABR scoring does not accept already-completed verification. "
                "WSP 97 requires truthful state transitions."
            ),
        )

    if score_input.cabr_ready:
        return CABRScoreResult(
            score_id=generate_score_id(score_input.receipt_id),
            receipt_id=score_input.receipt_id,
            job_id=score_input.job_id,
            tenant_id=score_input.tenant_id,
            decision=CABRScoreDecision.REJECTED_TRUTH_BOUNDARY,
            reason_code=CABRScoreReason.REJECTED_CABR_READY_CLAIMED,
            reason_human=(
                "Input claims cabr_ready=True. "
                "Phase 1 CABR scoring does not accept already-ready CABR state. "
                "WSP 97 requires truthful state transitions."
            ),
        )

    if score_input.payout_ready:
        return CABRScoreResult(
            score_id=generate_score_id(score_input.receipt_id),
            receipt_id=score_input.receipt_id,
            job_id=score_input.job_id,
            tenant_id=score_input.tenant_id,
            decision=CABRScoreDecision.REJECTED_TRUTH_BOUNDARY,
            reason_code=CABRScoreReason.REJECTED_PAYOUT_READY_CLAIMED,
            reason_human=(
                "Input claims payout_ready=True. "
                "Phase 1 CABR scoring does not accept payout-ready state. "
                "WSP 97 requires truthful state transitions."
            ),
        )

    return None


def _validate_evidence(
    score_input: CABRScoreInput,
) -> Optional[CABRScoreResult]:
    """
    Validate evidence presence.

    Returns rejection result if no evidence, None if valid.
    """
    if score_input.evidence_refs is None:
        return CABRScoreResult(
            score_id=generate_score_id(score_input.receipt_id),
            receipt_id=score_input.receipt_id,
            job_id=score_input.job_id,
            tenant_id=score_input.tenant_id,
            decision=CABRScoreDecision.REJECTED_INSUFFICIENT_EVIDENCE,
            reason_code=CABRScoreReason.REJECTED_NO_EVIDENCE,
            reason_human="No evidence_refs provided. Cannot score without execution evidence.",
        )

    if len(score_input.evidence_refs) == 0:
        return CABRScoreResult(
            score_id=generate_score_id(score_input.receipt_id),
            receipt_id=score_input.receipt_id,
            job_id=score_input.job_id,
            tenant_id=score_input.tenant_id,
            decision=CABRScoreDecision.REJECTED_INSUFFICIENT_EVIDENCE,
            reason_code=CABRScoreReason.REJECTED_EMPTY_EVIDENCE,
            reason_human=(
                "evidence_refs is empty. Cannot score without execution evidence. "
                "Provide at least one evidence reference."
            ),
        )

    return None


def _validate_pavs_decision(
    score_input: CABRScoreInput,
) -> Optional[CABRScoreResult]:
    """
    Validate pAVS decision if present.

    Returns rejection result if pAVS indicates failure, None if valid/absent.
    """
    if not score_input.pavs_decision:
        return None  # No pAVS decision to validate

    pavs = score_input.pavs_decision.lower()

    # Map pAVS failure states to CABR rejection
    rejection_mapping = {
        "blocked_missing_evidence": (
            CABRScoreReason.REJECTED_PAVS_BLOCKED_MISSING_EVIDENCE,
            "pAVS returned BLOCKED_MISSING_EVIDENCE. Cannot score without evidence.",
        ),
        "blocked_upstream": (
            CABRScoreReason.REJECTED_PAVS_BLOCKED_UPSTREAM,
            "pAVS returned BLOCKED_UPSTREAM. Upstream job was blocked.",
        ),
        "failed_input": (
            CABRScoreReason.REJECTED_PAVS_FAILED_INPUT,
            "pAVS returned FAILED_INPUT. Upstream job failed due to input/validation.",
        ),
        "rejected_missing_identity": (
            CABRScoreReason.REJECTED_PAVS_REJECTED_IDENTITY,
            "pAVS returned REJECTED_MISSING_IDENTITY. Receipt identity incomplete.",
        ),
        "rejected_invalid_status": (
            CABRScoreReason.REJECTED_PAVS_REJECTED_STATUS,
            "pAVS returned REJECTED_INVALID_STATUS. Receipt has invalid verification status.",
        ),
    }

    if pavs in rejection_mapping:
        reason_code, reason_human = rejection_mapping[pavs]
        return CABRScoreResult(
            score_id=generate_score_id(score_input.receipt_id),
            receipt_id=score_input.receipt_id,
            job_id=score_input.job_id,
            tenant_id=score_input.tenant_id,
            decision=CABRScoreDecision.REJECTED_PAVS_FAILED,
            reason_code=reason_code,
            reason_human=reason_human,
            pavs_decision=score_input.pavs_decision,
            pavs_passed=False,
        )

    return None


def _evaluate_quorum(
    verifier_ids: List[str],
    min_validators: int,
) -> tuple[int, int, bool, bool]:
    """
    Evaluate verifier quorum.

    Args:
        verifier_ids: List of verifier IDs
        min_validators: Minimum validators threshold

    Returns:
        Tuple of (verifier_count, unique_count, duplicates_detected, quorum_met)
    """
    verifier_count = len(verifier_ids)
    unique_ids = set(verifier_ids)
    unique_count = len(unique_ids)
    duplicates_detected = unique_count < verifier_count
    quorum_met = unique_count >= min_validators

    return verifier_count, unique_count, duplicates_detected, quorum_met


# ---------------------------------------------------------------------------
# Public API: Score CABR Receipt
# ---------------------------------------------------------------------------


def score_cabr_receipt(
    score_input: CABRScoreInput,
    min_validators: int = MIN_VALIDATORS_DEFAULT,
    include_input_snapshot: bool = False,
) -> CABRScoreResult:
    """
    Score a CABR receipt/verification result.

    Evaluates the input against CABR criteria and returns a deterministic
    scoring decision. Does NOT claim verification/CABR/payout completion.

    Decision tree:
      1. Validate identity fields
      2. Validate WSP 97 truth boundaries (reject if already completed)
      3. Validate evidence presence
      4. Validate pAVS decision (if present)
      5. Evaluate verifier quorum
      6. Determine acceptance decision

    Args:
        score_input: CABRScoreInput to score
        min_validators: Minimum validators threshold (WSP 29 default: 3)
        include_input_snapshot: If True, include input dict in result

    Returns:
        CABRScoreResult with deterministic decision and WSP 97 truth fields

    WSP 97 Truth Fields (always False in Phase 1):
        verification_complete = False
        cabr_ready = False
        payout_ready = False
    """
    # Step 1: Validate identity
    identity_error = _validate_identity(score_input)
    if identity_error:
        logger.warning(
            "[CABR-SCORE] Identity validation failed: %s",
            identity_error.reason_code.value,
        )
        return identity_error

    # Step 2: Validate truth boundaries
    truth_error = _validate_truth_boundaries(score_input)
    if truth_error:
        logger.warning(
            "[CABR-SCORE] Truth boundary violation: %s",
            truth_error.reason_code.value,
        )
        return truth_error

    # Step 3: Validate evidence
    evidence_error = _validate_evidence(score_input)
    if evidence_error:
        logger.warning(
            "[CABR-SCORE] Evidence validation failed: %s",
            evidence_error.reason_code.value,
        )
        return evidence_error

    # Step 4: Validate pAVS decision
    pavs_error = _validate_pavs_decision(score_input)
    if pavs_error:
        logger.warning(
            "[CABR-SCORE] pAVS validation failed: %s",
            pavs_error.reason_code.value,
        )
        return pavs_error

    # Step 5: Evaluate quorum
    verifier_count, unique_count, duplicates_detected, quorum_met = _evaluate_quorum(
        score_input.verifier_ids,
        min_validators,
    )

    # Step 5a: Check for duplicate verifiers (strict rejection)
    if duplicates_detected and len(score_input.verifier_ids) > 0:
        # Only reject if there were verifiers and duplicates were found
        # Empty verifier list is handled by quorum check
        logger.warning(
            "[CABR-SCORE] Duplicate verifiers detected: %d total, %d unique",
            verifier_count,
            unique_count,
        )
        return CABRScoreResult(
            score_id=generate_score_id(score_input.receipt_id),
            receipt_id=score_input.receipt_id,
            job_id=score_input.job_id,
            tenant_id=score_input.tenant_id,
            decision=CABRScoreDecision.REJECTED_DUPLICATE_VERIFIERS,
            reason_code=CABRScoreReason.REJECTED_DUPLICATE_VERIFIER_IDS,
            reason_human=(
                f"Duplicate verifier IDs detected. "
                f"Provided {verifier_count} verifier IDs but only {unique_count} are unique. "
                "Each verifier may only attest once."
            ),
            verifier_count=verifier_count,
            unique_verifier_count=unique_count,
            min_validators=min_validators,
            quorum_met=False,
            duplicate_verifiers_detected=True,
            evidence_count=len(score_input.evidence_refs),
            evidence_present=True,
            is_dry_run=score_input.is_dry_run,
            is_simulated=score_input.is_simulated,
            # WSP 97: Always False in Phase 1
            verification_complete=False,
            cabr_ready=False,
            payout_ready=False,
            pavs_decision=score_input.pavs_decision,
            pavs_passed=score_input.pavs_decision in ("accepted_for_review", "pending_verification", "not_required"),
        )

    # Step 6: Determine acceptance decision
    evidence_present = len(score_input.evidence_refs) > 0
    evidence_count = len(score_input.evidence_refs)

    # Determine pAVS pass state
    pavs_passed = score_input.pavs_decision in (
        "accepted_for_review",
        "pending_verification",
        "not_required",
        None,  # No pAVS decision means receipt-only scoring
    )

    # Build base result fields
    base_fields = {
        "score_id": generate_score_id(score_input.receipt_id),
        "receipt_id": score_input.receipt_id,
        "job_id": score_input.job_id,
        "tenant_id": score_input.tenant_id,
        "verifier_count": verifier_count,
        "unique_verifier_count": unique_count,
        "min_validators": min_validators,
        "quorum_met": quorum_met,
        "duplicate_verifiers_detected": duplicates_detected,
        "evidence_count": evidence_count,
        "evidence_present": evidence_present,
        "is_dry_run": score_input.is_dry_run,
        "is_simulated": score_input.is_simulated,
        # WSP 97: Always False in Phase 1
        "verification_complete": False,
        "cabr_ready": False,
        "payout_ready": False,
        "pavs_decision": score_input.pavs_decision,
        "pavs_passed": pavs_passed,
    }

    # Decision logic
    if score_input.is_dry_run or score_input.is_simulated:
        # Dry-run/simulated: Accept for review only, never consensus
        result = CABRScoreResult(
            **base_fields,
            decision=CABRScoreDecision.ACCEPTED_FOR_REVIEW,
            reason_code=CABRScoreReason.OK_EVIDENCE_PRESENT_DRY_RUN,
            reason_human=(
                f"Dry-run/simulated execution accepted for review. "
                f"{evidence_count} evidence ref(s) present. "
                "Dry-run receipts cannot achieve final consensus but are recorded for audit."
            ),
        )
    elif quorum_met:
        # Quorum met: Accept for review with eligibility noted
        result = CABRScoreResult(
            **base_fields,
            decision=CABRScoreDecision.ACCEPTED_FOR_REVIEW,
            reason_code=CABRScoreReason.OK_EVIDENCE_PRESENT_QUORUM_MET,
            reason_human=(
                f"Evidence present and verifier quorum met. "
                f"{evidence_count} evidence ref(s), {unique_count} unique verifier(s) "
                f"(min_validators={min_validators}). "
                "Accepted for review. WSP 97: cabr_ready=False, payout_ready=False."
            ),
        )
    elif verifier_count == 0:
        # No verifiers: Accept for review pending quorum
        result = CABRScoreResult(
            **base_fields,
            decision=CABRScoreDecision.ACCEPTED_FOR_REVIEW_PENDING_QUORUM,
            reason_code=CABRScoreReason.OK_EVIDENCE_PRESENT_PENDING_QUORUM,
            reason_human=(
                f"Evidence present but no verifiers yet. "
                f"{evidence_count} evidence ref(s), 0 verifiers "
                f"(need {min_validators} for quorum). "
                "Accepted for review pending verifier attestations."
            ),
        )
    else:
        # Some verifiers but below quorum: Accept for review pending
        result = CABRScoreResult(
            **base_fields,
            decision=CABRScoreDecision.ACCEPTED_FOR_REVIEW_PENDING_QUORUM,
            reason_code=CABRScoreReason.OK_EVIDENCE_PRESENT_PENDING_QUORUM,
            reason_human=(
                f"Evidence present but verifier quorum not met. "
                f"{evidence_count} evidence ref(s), {unique_count} verifier(s) "
                f"(need {min_validators} for quorum). "
                "Accepted for review pending additional verifiers."
            ),
        )

    if include_input_snapshot:
        result.input_snapshot = score_input.to_dict()

    logger.info(
        "[CABR-SCORE] Scored receipt %s -> decision=%s, reason=%s, quorum=%s",
        score_input.receipt_id,
        result.decision.value,
        result.reason_code.value,
        quorum_met,
    )

    return result


# ---------------------------------------------------------------------------
# Public API: Batch Scoring
# ---------------------------------------------------------------------------


def score_cabr_batch(
    inputs: List[CABRScoreInput],
    min_validators: int = MIN_VALIDATORS_DEFAULT,
) -> List[CABRScoreResult]:
    """
    Score multiple CABR inputs in batch.

    Deterministic: Results are in same order as inputs.
    No network calls, no state mutation.

    Args:
        inputs: List of CABRScoreInput to score
        min_validators: Minimum validators threshold

    Returns:
        List of CABRScoreResult in same order as inputs
    """
    return [
        score_cabr_receipt(inp, min_validators=min_validators)
        for inp in inputs
    ]


# ---------------------------------------------------------------------------
# Convenience: Direct Scoring Functions
# ---------------------------------------------------------------------------


def score_from_receipt(
    receipt: Union["ProofOfComputeReceipt", Dict[str, Any]],
    verifier_ids: Optional[List[str]] = None,
    min_validators: int = MIN_VALIDATORS_DEFAULT,
) -> CABRScoreResult:
    """
    Score a ProofOfComputeReceipt directly.

    Convenience wrapper that builds CABRScoreInput and scores.

    Args:
        receipt: ProofOfComputeReceipt or dict
        verifier_ids: Optional verifier IDs for quorum
        min_validators: Minimum validators threshold

    Returns:
        CABRScoreResult
    """
    score_input = build_score_input_from_receipt(receipt, verifier_ids)
    return score_cabr_receipt(score_input, min_validators=min_validators)


def score_from_pavs_result(
    result: Union["PAVSVerificationResult", Dict[str, Any]],
    verifier_ids: Optional[List[str]] = None,
    min_validators: int = MIN_VALIDATORS_DEFAULT,
) -> CABRScoreResult:
    """
    Score a PAVSVerificationResult directly.

    Convenience wrapper that builds CABRScoreInput and scores.

    Args:
        result: PAVSVerificationResult or dict
        verifier_ids: Optional verifier IDs for quorum
        min_validators: Minimum validators threshold

    Returns:
        CABRScoreResult
    """
    score_input = build_score_input_from_pavs_result(result, verifier_ids)
    return score_cabr_receipt(score_input, min_validators=min_validators)
