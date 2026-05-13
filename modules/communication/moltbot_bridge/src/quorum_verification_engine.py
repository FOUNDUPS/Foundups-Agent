#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quorum Verification Engine Phase 1 -- Deterministic Quorum Enforcement for CABR Scoring

Implements internal sovereign quorum verification for CABR scoring eligibility,
building on the merged CABR Runtime Scoring Engine (PR #577).

WSP 97 TRUTH BOUNDARIES:
  * DOES:
    - Accept verifier attestations for quorum evaluation
    - Require min_validators default 3 (WSP 29)
    - Reject duplicate verifier IDs
    - Reject missing verifier IDs
    - Reject invalid/unsupported verifier signatures (Phase 1 = unsupported)
    - Count only unique valid dry-run attestations
    - Apply consensus threshold 0.382 deterministically
    - Accept only for review, never final consensus
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
    - Run cryptographic signature verification (Phase 1)
    - Claim final consensus

Architecture:
  W6 (receipt) -> ProofOfComputeReceipt
  W7 (pAVS)    -> PAVSVerificationResult
  W1 (CABR)    -> CABRScoreResult
  W1 (this)    -> QuorumVerificationResult (quorum enforcement layer)

WSP Compliance:
  WSP 11  : Interface contract (explicit, typed)
  WSP 29  : CABR Engine Framework (min_validators=3, consensus_threshold=0.382)
  WSP 97  : System Execution Prompting (truth boundaries)
  WSP 91  : Observability (timestamps, audit fields)

Slice: QUORUM_VERIFICATION_ENFORCEMENT_PHASE1
Worker: W1
"""

from __future__ import annotations

import logging
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger("quorum_verification_engine")


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

# WSP 29 Section 1.2: consensus_threshold
CONSENSUS_THRESHOLD: float = 0.382


# ---------------------------------------------------------------------------
# Quorum Decision Enum
# ---------------------------------------------------------------------------


class QuorumDecision(str, Enum):
    """
    Quorum verification decision -- deterministic outcome of quorum evaluation.

    WSP 97: These decisions describe WHAT WE EVALUATED, not claims of completion.
    """

    QUORUM_NOT_MET = "quorum_not_met"
    """Quorum requirements not satisfied. Cannot proceed to consensus."""

    QUORUM_MET_PENDING_CONSENSUS = "quorum_met_pending_consensus"
    """Quorum met but consensus score below threshold. Awaiting additional attestations."""

    CONSENSUS_ACCEPTED_FOR_REVIEW = "consensus_accepted_for_review"
    """Consensus threshold met. Accepted for human/operator review. NOT final consensus."""

    CONSENSUS_REJECTED = "consensus_rejected"
    """Consensus evaluation rejected due to input errors or threshold failures."""


class QuorumReasonCode(str, Enum):
    """Machine-readable reason codes for quorum decisions."""

    # Success reasons (accepted for review)
    OK_QUORUM_MET_THRESHOLD_MET = "ok_quorum_met_threshold_met"
    """Quorum met and consensus score >= 0.382. Accepted for review."""

    OK_QUORUM_MET_DRY_RUN = "ok_quorum_met_dry_run"
    """Quorum met in dry-run mode. Accepted for review only (not live consensus)."""

    # Pending reasons (quorum met but threshold not met)
    PENDING_THRESHOLD_NOT_MET = "pending_threshold_not_met"
    """Quorum met but consensus score below 0.382. Need more positive attestations."""

    # Quorum not met reasons
    QUORUM_ZERO_ATTESTATIONS = "quorum_zero_attestations"
    """No attestations provided. Cannot evaluate quorum."""

    QUORUM_INSUFFICIENT_ATTESTATIONS = "quorum_insufficient_attestations"
    """Attestation count below min_validators threshold."""

    QUORUM_INSUFFICIENT_UNIQUE_VERIFIERS = "quorum_insufficient_unique_verifiers"
    """Unique verifier count below min_validators after deduplication."""

    # Rejection reasons
    REJECTED_DUPLICATE_VERIFIER_IDS = "rejected_duplicate_verifier_ids"
    """Duplicate verifier IDs detected in attestations."""

    REJECTED_MISSING_VERIFIER_ID = "rejected_missing_verifier_id"
    """One or more attestations missing verifier_id."""

    REJECTED_INVALID_SIGNATURE = "rejected_invalid_signature"
    """Invalid verifier signature. Phase 1: All signatures unsupported/not verified."""

    REJECTED_MISSING_RECEIPT_ID = "rejected_missing_receipt_id"
    """Missing receipt_id in input."""

    REJECTED_MISSING_JOB_ID = "rejected_missing_job_id"
    """Missing job_id in input."""

    REJECTED_CONFLICTING_ATTESTATIONS = "rejected_conflicting_attestations"
    """Conflicting attestation decisions detected (handled deterministically)."""


# ---------------------------------------------------------------------------
# Attestation Status Enum (for individual attestations)
# ---------------------------------------------------------------------------


class AttestationStatus(str, Enum):
    """Status of individual verifier attestation."""

    VALID = "valid"
    """Attestation is valid and counted toward quorum."""

    APPROVE = "approve"
    """Verifier approves the CABR claim."""

    REJECT = "reject"
    """Verifier rejects the CABR claim."""

    ABSTAIN = "abstain"
    """Verifier abstains from voting."""

    INVALID_MISSING_ID = "invalid_missing_id"
    """Attestation invalid: missing verifier_id."""

    INVALID_DUPLICATE_ID = "invalid_duplicate_id"
    """Attestation invalid: duplicate verifier_id."""

    INVALID_SIGNATURE = "invalid_signature"
    """Attestation invalid: signature not verified (Phase 1 = all signatures unsupported)."""


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class VerifierAttestation:
    """
    Individual verifier attestation for quorum evaluation.

    In Phase 1, signature verification is unsupported -- all attestations
    with non-empty verifier_id and decision are counted as dry-run attestations.
    """

    verifier_id: str
    """Unique identifier of the verifying agent."""

    decision: AttestationStatus
    """Verifier's decision: APPROVE, REJECT, or ABSTAIN."""

    signature: Optional[str] = None
    """Cryptographic signature (Phase 1: unsupported, treated as None)."""

    timestamp: datetime = field(default_factory=_utc_now)
    """When this attestation was created."""

    is_dry_run: bool = False
    """True if this is a dry-run attestation (no real verification performed)."""

    reason: Optional[str] = None
    """Optional human-readable reason for the decision."""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize attestation to dict."""
        return {
            "verifier_id": self.verifier_id,
            "decision": self.decision.value,
            "signature": self.signature,
            "timestamp": _utc_iso(self.timestamp),
            "is_dry_run": self.is_dry_run,
            "reason": self.reason,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VerifierAttestation":
        """Deserialize attestation from dict."""
        attestation = cls(
            verifier_id=data.get("verifier_id", ""),
            decision=AttestationStatus(data.get("decision", "valid")),
            signature=data.get("signature"),
            is_dry_run=data.get("is_dry_run", False),
            reason=data.get("reason"),
        )
        timestamp = data.get("timestamp")
        if timestamp:
            attestation.timestamp = datetime.fromisoformat(timestamp)
        return attestation


@dataclass
class QuorumVerificationInput:
    """
    Input for quorum verification evaluation.

    Built from CABR scoring context with verifier attestations.
    """

    # === Identity Fields ===
    receipt_id: str
    """Receipt identifier from ProofOfComputeReceipt."""

    job_id: str
    """Source job identifier."""

    tenant_id: str
    """Actor scope / owner."""

    # === Attestations ===
    attestations: List[VerifierAttestation] = field(default_factory=list)
    """List of verifier attestations for quorum evaluation."""

    # === Configuration ===
    min_validators: int = MIN_VALIDATORS_DEFAULT
    """Minimum validators required for quorum (WSP 29 default: 3)."""

    consensus_threshold: float = CONSENSUS_THRESHOLD
    """Consensus threshold (WSP 29 default: 0.382)."""

    # === Execution Mode ===
    is_dry_run: bool = False
    """True if the source execution was dry-run/simulated."""

    # === Optional Context ===
    cabr_score_id: Optional[str] = None
    """Reference to associated CABRScoreResult if available."""

    foundup_id: Optional[str] = None
    """Target FoundUp ID if scoped."""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict."""
        return {
            "receipt_id": self.receipt_id,
            "job_id": self.job_id,
            "tenant_id": self.tenant_id,
            "attestations": [a.to_dict() for a in self.attestations],
            "min_validators": self.min_validators,
            "consensus_threshold": self.consensus_threshold,
            "is_dry_run": self.is_dry_run,
            "cabr_score_id": self.cabr_score_id,
            "foundup_id": self.foundup_id,
        }


@dataclass
class QuorumVerificationResult:
    """
    Result from quorum verification evaluation.

    Contains deterministic quorum decision with WSP 97 truth boundaries.
    """

    # === Quorum Identity ===
    quorum_id: str
    """Unique quorum evaluation identifier. Format: qv_{receipt_suffix}_{timestamp}_{random}."""

    receipt_id: str
    """Source receipt identifier."""

    job_id: str
    """Source job identifier."""

    tenant_id: str
    """Actor scope / owner."""

    # === Decision Fields ===
    decision: QuorumDecision
    """Quorum decision made."""

    reason_code: QuorumReasonCode
    """Machine-readable reason for decision."""

    reason_human: str
    """Operator-readable explanation."""

    # === Quorum Metrics ===
    total_attestations: int = 0
    """Total number of attestations provided."""

    valid_attestations: int = 0
    """Number of valid attestations after filtering."""

    unique_verifiers: int = 0
    """Number of unique verifier IDs."""

    min_validators: int = MIN_VALIDATORS_DEFAULT
    """Minimum validators threshold used."""

    quorum_met: bool = False
    """True if unique_verifiers >= min_validators."""

    # === Consensus Metrics ===
    approve_count: int = 0
    """Number of APPROVE attestations."""

    reject_count: int = 0
    """Number of REJECT attestations."""

    abstain_count: int = 0
    """Number of ABSTAIN attestations."""

    consensus_score: float = 0.0
    """Consensus score: approve_count / valid_attestations (0.0 if none)."""

    consensus_threshold: float = CONSENSUS_THRESHOLD
    """Consensus threshold used (WSP 29 default: 0.382)."""

    threshold_met: bool = False
    """True if consensus_score >= consensus_threshold."""

    # === Duplicate/Invalid Tracking ===
    duplicate_verifiers_detected: bool = False
    """True if duplicate verifier IDs were detected."""

    missing_verifier_ids_detected: bool = False
    """True if attestations with missing verifier_id were detected."""

    invalid_signatures_detected: bool = False
    """True if invalid signatures were detected (Phase 1: all signatures unsupported)."""

    # === Execution Mode ===
    is_dry_run: bool = False
    """True if source was dry-run execution."""

    # === WSP 97 Truth Fields (OUTPUT - always False in Phase 1) ===
    verification_complete: bool = False
    """Always False in Phase 1. No full verification performed."""

    cabr_ready: bool = False
    """Always False in Phase 1. No CABR consensus exists."""

    payout_ready: bool = False
    """Always False in Phase 1. No payout engine exists."""

    # === Timestamps ===
    evaluated_at: datetime = field(default_factory=_utc_now)
    """When this quorum evaluation was performed."""

    # === Audit Fields ===
    engine_version: str = "0.1.0"
    """Quorum verification engine version."""

    input_snapshot: Optional[Dict[str, Any]] = None
    """Optional: Input snapshot for audit trail."""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict."""
        return {
            "quorum_id": self.quorum_id,
            "receipt_id": self.receipt_id,
            "job_id": self.job_id,
            "tenant_id": self.tenant_id,
            "decision": self.decision.value,
            "reason_code": self.reason_code.value,
            "reason_human": self.reason_human,
            "total_attestations": self.total_attestations,
            "valid_attestations": self.valid_attestations,
            "unique_verifiers": self.unique_verifiers,
            "min_validators": self.min_validators,
            "quorum_met": self.quorum_met,
            "approve_count": self.approve_count,
            "reject_count": self.reject_count,
            "abstain_count": self.abstain_count,
            "consensus_score": self.consensus_score,
            "consensus_threshold": self.consensus_threshold,
            "threshold_met": self.threshold_met,
            "duplicate_verifiers_detected": self.duplicate_verifiers_detected,
            "missing_verifier_ids_detected": self.missing_verifier_ids_detected,
            "invalid_signatures_detected": self.invalid_signatures_detected,
            "is_dry_run": self.is_dry_run,
            "verification_complete": self.verification_complete,
            "cabr_ready": self.cabr_ready,
            "payout_ready": self.payout_ready,
            "evaluated_at": _utc_iso(self.evaluated_at),
            "engine_version": self.engine_version,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "QuorumVerificationResult":
        """Deserialize from dict."""
        result = cls(
            quorum_id=data["quorum_id"],
            receipt_id=data["receipt_id"],
            job_id=data["job_id"],
            tenant_id=data["tenant_id"],
            decision=QuorumDecision(data["decision"]),
            reason_code=QuorumReasonCode(data["reason_code"]),
            reason_human=data.get("reason_human", ""),
            total_attestations=data.get("total_attestations", 0),
            valid_attestations=data.get("valid_attestations", 0),
            unique_verifiers=data.get("unique_verifiers", 0),
            min_validators=data.get("min_validators", MIN_VALIDATORS_DEFAULT),
            quorum_met=data.get("quorum_met", False),
            approve_count=data.get("approve_count", 0),
            reject_count=data.get("reject_count", 0),
            abstain_count=data.get("abstain_count", 0),
            consensus_score=data.get("consensus_score", 0.0),
            consensus_threshold=data.get("consensus_threshold", CONSENSUS_THRESHOLD),
            threshold_met=data.get("threshold_met", False),
            duplicate_verifiers_detected=data.get("duplicate_verifiers_detected", False),
            missing_verifier_ids_detected=data.get("missing_verifier_ids_detected", False),
            invalid_signatures_detected=data.get("invalid_signatures_detected", False),
            is_dry_run=data.get("is_dry_run", False),
            verification_complete=data.get("verification_complete", False),
            cabr_ready=data.get("cabr_ready", False),
            payout_ready=data.get("payout_ready", False),
            engine_version=data.get("engine_version", "0.1.0"),
        )

        evaluated_at = data.get("evaluated_at")
        if evaluated_at:
            result.evaluated_at = datetime.fromisoformat(evaluated_at)

        return result


# ---------------------------------------------------------------------------
# Quorum ID Generation
# ---------------------------------------------------------------------------


def generate_quorum_id(receipt_id: str) -> str:
    """
    Generate unique quorum ID from receipt ID.

    Format: qv_{receipt_suffix}_{timestamp_hex}_{random_hex}
    Example: qv_extract_18a3b2c1_66d1a2b3_abc123
    """
    parts = receipt_id.split("_")
    if len(parts) >= 2:
        suffix = f"{parts[1]}"[:12]
    else:
        suffix = receipt_id[:12]

    timestamp_hex = hex(int(_utc_now().timestamp()))[2:][:8]
    random_hex = secrets.token_hex(3)
    return f"qv_{suffix}_{timestamp_hex}_{random_hex}"


# ---------------------------------------------------------------------------
# Core Quorum Logic
# ---------------------------------------------------------------------------


def _validate_identity(
    quorum_input: QuorumVerificationInput,
) -> Optional[QuorumVerificationResult]:
    """
    Validate required identity fields.

    Returns rejection result if invalid, None if valid.
    """
    if not quorum_input.receipt_id or not quorum_input.receipt_id.strip():
        return QuorumVerificationResult(
            quorum_id=f"qv_rejected_{secrets.token_hex(4)}",
            receipt_id="",
            job_id=quorum_input.job_id,
            tenant_id=quorum_input.tenant_id,
            decision=QuorumDecision.CONSENSUS_REJECTED,
            reason_code=QuorumReasonCode.REJECTED_MISSING_RECEIPT_ID,
            reason_human="Missing receipt_id. Cannot evaluate quorum without receipt identity.",
        )

    if not quorum_input.job_id or not quorum_input.job_id.strip():
        return QuorumVerificationResult(
            quorum_id=generate_quorum_id(quorum_input.receipt_id),
            receipt_id=quorum_input.receipt_id,
            job_id="",
            tenant_id=quorum_input.tenant_id,
            decision=QuorumDecision.CONSENSUS_REJECTED,
            reason_code=QuorumReasonCode.REJECTED_MISSING_JOB_ID,
            reason_human="Missing job_id. Cannot correlate quorum to source job.",
        )

    return None


def _validate_attestations(
    attestations: List[VerifierAttestation],
) -> tuple[List[VerifierAttestation], bool, bool, bool]:
    """
    Validate attestations and filter invalid ones.

    Returns:
        Tuple of (valid_attestations, duplicates_detected, missing_ids_detected, invalid_sigs_detected)
    """
    valid_attestations = []
    seen_verifier_ids = set()
    duplicates_detected = False
    missing_ids_detected = False
    invalid_sigs_detected = False

    for attestation in attestations:
        # Check for missing verifier_id
        if not attestation.verifier_id or not attestation.verifier_id.strip():
            missing_ids_detected = True
            continue

        # Check for duplicate verifier_id
        if attestation.verifier_id in seen_verifier_ids:
            duplicates_detected = True
            continue

        # Phase 1: Signature verification is unsupported
        # If signature is provided but non-empty, we note it but don't verify
        if attestation.signature is not None and attestation.signature.strip():
            # In Phase 1, we cannot verify signatures -- mark as detected but proceed
            # Real signature verification would reject here in Phase 2+
            invalid_sigs_detected = True
            # Still count the attestation for Phase 1 (dry-run behavior)

        # Valid attestation
        seen_verifier_ids.add(attestation.verifier_id)
        valid_attestations.append(attestation)

    return valid_attestations, duplicates_detected, missing_ids_detected, invalid_sigs_detected


def _calculate_consensus_metrics(
    valid_attestations: List[VerifierAttestation],
) -> tuple[int, int, int, float]:
    """
    Calculate consensus metrics from valid attestations.

    Returns:
        Tuple of (approve_count, reject_count, abstain_count, consensus_score)
    """
    approve_count = 0
    reject_count = 0
    abstain_count = 0

    for attestation in valid_attestations:
        if attestation.decision == AttestationStatus.APPROVE:
            approve_count += 1
        elif attestation.decision == AttestationStatus.REJECT:
            reject_count += 1
        elif attestation.decision == AttestationStatus.ABSTAIN:
            abstain_count += 1
        elif attestation.decision == AttestationStatus.VALID:
            # VALID counts as implicit approval in Phase 1
            approve_count += 1

    # Consensus score = approve / total (excluding abstains for scoring)
    voting_count = approve_count + reject_count
    if voting_count > 0:
        consensus_score = approve_count / voting_count
    else:
        # Only abstains or no attestations
        consensus_score = 0.0

    return approve_count, reject_count, abstain_count, consensus_score


# ---------------------------------------------------------------------------
# Public API: Evaluate Quorum
# ---------------------------------------------------------------------------


def evaluate_quorum(
    quorum_input: QuorumVerificationInput,
    include_input_snapshot: bool = False,
) -> QuorumVerificationResult:
    """
    Evaluate quorum verification for CABR scoring eligibility.

    Evaluates the input against quorum criteria and returns a deterministic
    quorum decision. Does NOT claim verification/CABR/payout completion.

    Decision tree:
      1. Validate identity fields
      2. Validate attestations (reject missing IDs, note duplicates)
      3. Check quorum met (unique_verifiers >= min_validators)
      4. Calculate consensus score
      5. Apply consensus threshold
      6. Determine acceptance decision

    Args:
        quorum_input: QuorumVerificationInput to evaluate
        include_input_snapshot: If True, include input dict in result

    Returns:
        QuorumVerificationResult with deterministic decision and WSP 97 truth fields

    WSP 97 Truth Fields (always False in Phase 1):
        verification_complete = False
        cabr_ready = False
        payout_ready = False
    """
    # Step 1: Validate identity
    identity_error = _validate_identity(quorum_input)
    if identity_error:
        logger.warning(
            "[QUORUM] Identity validation failed: %s",
            identity_error.reason_code.value,
        )
        return identity_error

    # Step 2: Validate and filter attestations
    attestations = quorum_input.attestations
    total_attestations = len(attestations)

    (
        valid_attestations,
        duplicates_detected,
        missing_ids_detected,
        invalid_sigs_detected,
    ) = _validate_attestations(attestations)

    valid_count = len(valid_attestations)
    unique_verifiers = len(set(a.verifier_id for a in valid_attestations))

    # Step 2a: Fail-closed on missing verifier IDs
    if missing_ids_detected:
        logger.warning(
            "[QUORUM] Missing verifier IDs detected in attestations",
        )
        return QuorumVerificationResult(
            quorum_id=generate_quorum_id(quorum_input.receipt_id),
            receipt_id=quorum_input.receipt_id,
            job_id=quorum_input.job_id,
            tenant_id=quorum_input.tenant_id,
            decision=QuorumDecision.CONSENSUS_REJECTED,
            reason_code=QuorumReasonCode.REJECTED_MISSING_VERIFIER_ID,
            reason_human=(
                "One or more attestations missing verifier_id. "
                "All attestations must have a valid verifier_id."
            ),
            total_attestations=total_attestations,
            valid_attestations=0,
            unique_verifiers=0,
            min_validators=quorum_input.min_validators,
            quorum_met=False,
            duplicate_verifiers_detected=duplicates_detected,
            missing_verifier_ids_detected=True,
            invalid_signatures_detected=invalid_sigs_detected,
            is_dry_run=quorum_input.is_dry_run,
            # WSP 97: Always False
            verification_complete=False,
            cabr_ready=False,
            payout_ready=False,
        )

    # Step 2b: Fail-closed on duplicate verifier IDs
    if duplicates_detected:
        logger.warning(
            "[QUORUM] Duplicate verifier IDs detected: %d total, %d unique",
            total_attestations,
            unique_verifiers,
        )
        return QuorumVerificationResult(
            quorum_id=generate_quorum_id(quorum_input.receipt_id),
            receipt_id=quorum_input.receipt_id,
            job_id=quorum_input.job_id,
            tenant_id=quorum_input.tenant_id,
            decision=QuorumDecision.CONSENSUS_REJECTED,
            reason_code=QuorumReasonCode.REJECTED_DUPLICATE_VERIFIER_IDS,
            reason_human=(
                f"Duplicate verifier IDs detected. "
                f"Provided {total_attestations} attestations but only "
                f"{unique_verifiers} have unique verifier IDs. "
                "Each verifier may only attest once."
            ),
            total_attestations=total_attestations,
            valid_attestations=valid_count,
            unique_verifiers=unique_verifiers,
            min_validators=quorum_input.min_validators,
            quorum_met=False,
            duplicate_verifiers_detected=True,
            missing_verifier_ids_detected=False,
            invalid_signatures_detected=invalid_sigs_detected,
            is_dry_run=quorum_input.is_dry_run,
            # WSP 97: Always False
            verification_complete=False,
            cabr_ready=False,
            payout_ready=False,
        )

    # Step 3: Check quorum
    quorum_met = unique_verifiers >= quorum_input.min_validators

    # Step 4: Calculate consensus metrics
    approve_count, reject_count, abstain_count, consensus_score = (
        _calculate_consensus_metrics(valid_attestations)
    )

    # Step 5: Apply consensus threshold
    threshold_met = consensus_score >= quorum_input.consensus_threshold

    # Build base result fields
    base_fields = {
        "quorum_id": generate_quorum_id(quorum_input.receipt_id),
        "receipt_id": quorum_input.receipt_id,
        "job_id": quorum_input.job_id,
        "tenant_id": quorum_input.tenant_id,
        "total_attestations": total_attestations,
        "valid_attestations": valid_count,
        "unique_verifiers": unique_verifiers,
        "min_validators": quorum_input.min_validators,
        "quorum_met": quorum_met,
        "approve_count": approve_count,
        "reject_count": reject_count,
        "abstain_count": abstain_count,
        "consensus_score": consensus_score,
        "consensus_threshold": quorum_input.consensus_threshold,
        "threshold_met": threshold_met,
        "duplicate_verifiers_detected": False,
        "missing_verifier_ids_detected": False,
        "invalid_signatures_detected": invalid_sigs_detected,
        "is_dry_run": quorum_input.is_dry_run,
        # WSP 97: Always False
        "verification_complete": False,
        "cabr_ready": False,
        "payout_ready": False,
    }

    # Step 6: Determine decision
    if total_attestations == 0:
        # Zero attestations
        result = QuorumVerificationResult(
            **base_fields,
            decision=QuorumDecision.QUORUM_NOT_MET,
            reason_code=QuorumReasonCode.QUORUM_ZERO_ATTESTATIONS,
            reason_human=(
                "No attestations provided. Cannot evaluate quorum. "
                f"Need at least {quorum_input.min_validators} verifier attestations."
            ),
        )
    elif not quorum_met:
        # Quorum not met
        result = QuorumVerificationResult(
            **base_fields,
            decision=QuorumDecision.QUORUM_NOT_MET,
            reason_code=QuorumReasonCode.QUORUM_INSUFFICIENT_UNIQUE_VERIFIERS,
            reason_human=(
                f"Quorum not met. {unique_verifiers} unique verifier(s) "
                f"(need {quorum_input.min_validators}). "
                "Awaiting additional verifier attestations."
            ),
        )
    elif quorum_input.is_dry_run:
        # Dry-run: Accept for review regardless of threshold
        result = QuorumVerificationResult(
            **base_fields,
            decision=QuorumDecision.CONSENSUS_ACCEPTED_FOR_REVIEW,
            reason_code=QuorumReasonCode.OK_QUORUM_MET_DRY_RUN,
            reason_human=(
                f"Dry-run quorum evaluation accepted for review. "
                f"{unique_verifiers} unique verifier(s), "
                f"consensus score {consensus_score:.3f}. "
                "Dry-run evaluations are recorded for audit but do not affect live consensus."
            ),
        )
    elif threshold_met:
        # Quorum met and threshold met
        result = QuorumVerificationResult(
            **base_fields,
            decision=QuorumDecision.CONSENSUS_ACCEPTED_FOR_REVIEW,
            reason_code=QuorumReasonCode.OK_QUORUM_MET_THRESHOLD_MET,
            reason_human=(
                f"Quorum met and consensus threshold satisfied. "
                f"{unique_verifiers} verifier(s), "
                f"consensus score {consensus_score:.3f} >= {quorum_input.consensus_threshold}. "
                "Accepted for review. WSP 97: cabr_ready=False, payout_ready=False."
            ),
        )
    else:
        # Quorum met but threshold not met
        result = QuorumVerificationResult(
            **base_fields,
            decision=QuorumDecision.QUORUM_MET_PENDING_CONSENSUS,
            reason_code=QuorumReasonCode.PENDING_THRESHOLD_NOT_MET,
            reason_human=(
                f"Quorum met but consensus threshold not satisfied. "
                f"{unique_verifiers} verifier(s), "
                f"consensus score {consensus_score:.3f} < {quorum_input.consensus_threshold}. "
                "Awaiting additional positive attestations."
            ),
        )

    if include_input_snapshot:
        result.input_snapshot = quorum_input.to_dict()

    logger.info(
        "[QUORUM] Evaluated receipt %s -> decision=%s, reason=%s, quorum=%s, threshold=%s",
        quorum_input.receipt_id,
        result.decision.value,
        result.reason_code.value,
        quorum_met,
        threshold_met,
    )

    return result


# ---------------------------------------------------------------------------
# Public API: Batch Evaluation
# ---------------------------------------------------------------------------


def evaluate_quorum_batch(
    inputs: List[QuorumVerificationInput],
) -> List[QuorumVerificationResult]:
    """
    Evaluate multiple quorum inputs in batch.

    Deterministic: Results are in same order as inputs.
    No network calls, no state mutation.

    Args:
        inputs: List of QuorumVerificationInput to evaluate

    Returns:
        List of QuorumVerificationResult in same order as inputs
    """
    return [evaluate_quorum(inp) for inp in inputs]


# ---------------------------------------------------------------------------
# Convenience: Build Input from CABR Result
# ---------------------------------------------------------------------------


def build_quorum_input_from_cabr_result(
    cabr_result: Dict[str, Any],
    attestations: List[VerifierAttestation],
    min_validators: int = MIN_VALIDATORS_DEFAULT,
    consensus_threshold: float = CONSENSUS_THRESHOLD,
) -> QuorumVerificationInput:
    """
    Build QuorumVerificationInput from CABRScoreResult dict and attestations.

    Args:
        cabr_result: CABRScoreResult.to_dict() output
        attestations: List of VerifierAttestation objects
        min_validators: Minimum validators threshold
        consensus_threshold: Consensus threshold

    Returns:
        QuorumVerificationInput ready for evaluation
    """
    return QuorumVerificationInput(
        receipt_id=cabr_result.get("receipt_id", ""),
        job_id=cabr_result.get("job_id", ""),
        tenant_id=cabr_result.get("tenant_id", ""),
        attestations=attestations,
        min_validators=min_validators,
        consensus_threshold=consensus_threshold,
        is_dry_run=cabr_result.get("is_dry_run", False),
        cabr_score_id=cabr_result.get("score_id"),
        foundup_id=None,  # Not in CABR result
    )
