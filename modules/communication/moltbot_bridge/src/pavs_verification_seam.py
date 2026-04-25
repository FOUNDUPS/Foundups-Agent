#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pAVS Verification Seam — Receipt Consumer Placeholder for pAVS Pipeline

Accepts ProofOfComputeReceipt from W6 and returns truthful verification decisions
without claiming full pAVS/CABR/PoB implementation.

WSP 97 TRUTH BOUNDARIES:
  ✓ DOES:
    - Accept ProofOfComputeReceipt or receipt-like dict
    - Validate identity fields (receipt_id, job_id, tenant_id)
    - Map verification_status to pAVS decision
    - Return truthful verification result with reason codes
    - Track evidence presence/absence for decision logic
    - Mark cabr_ready = False (no consensus exists)
    - Mark payout_ready = False (no payout engine exists)

  ✗ DOES NOT:
    - Issue tokens or UPS
    - Allocate rewards
    - Write to wallet
    - Run CABR consensus
    - Run cryptographic verification
    - Claim verification is complete (only ACCEPTED_FOR_REVIEW)

Architecture:
  W6 (receipt)  -> creates ProofOfComputeReceipt from terminal job
  W7 (this)     -> accepts receipt, returns verification decision (placeholder)
  W10 (future)  -> consumes verified receipts for CABR scoring / payout

WSP Compliance:
  WSP 11  : Interface contract (explicit, typed)
  WSP 97  : System Execution Prompting (truth boundaries)
  WSP 91  : Observability (timestamps, audit fields)

NAVIGATION:
  -> Consumes: ProofOfComputeReceipt from proof_of_compute_receipt.py
  -> Produces: PAVSVerificationResult for future CABR/payout consumers
  -> Related: modules/infrastructure/pavs_mcp/src/server.py (MCP tools)
"""

from __future__ import annotations

import hashlib
import logging
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from .proof_of_compute_receipt import (
    ProofOfComputeReceipt,
    VerificationStatus,
)

logger = logging.getLogger("pavs_verification_seam")


def _utc_now() -> datetime:
    """Return current UTC timestamp."""
    return datetime.now(timezone.utc)


def _utc_iso(dt: Optional[datetime]) -> Optional[str]:
    """Convert datetime to ISO string or None."""
    return dt.isoformat() if dt else None


# ---------------------------------------------------------------------------
# pAVS Decision Status
# ---------------------------------------------------------------------------


class PAVSDecision(str, Enum):
    """
    pAVS verification decision — truth-surface for downstream consumers.

    WSP 97: These statuses describe WHAT WE DECIDED, not what we claim happened.
    """

    ACCEPTED_FOR_REVIEW = "accepted_for_review"
    """Receipt accepted for pAVS review. Evidence present. Does NOT mean verified."""

    PENDING_VERIFICATION = "pending_verification"
    """Receipt accepted, awaiting deeper verification. Synonym for ACCEPTED_FOR_REVIEW."""

    NOT_REQUIRED = "not_required"
    """Receipt does not require verification (dry-run, query-only)."""

    BLOCKED_MISSING_EVIDENCE = "blocked_missing_evidence"
    """Receipt claims success but has no evidence. Cannot proceed without evidence."""

    BLOCKED_UPSTREAM = "blocked_upstream"
    """Upstream job was blocked. Receipt reflects blocking state."""

    FAILED_INPUT = "failed_input"
    """Upstream job failed due to input/validation. Receipt records failure evidence."""

    REJECTED_MISSING_IDENTITY = "rejected_missing_identity"
    """Receipt missing required identity fields (receipt_id, job_id, or tenant_id)."""

    REJECTED_INVALID_STATUS = "rejected_invalid_status"
    """Receipt has unsupported verification_status."""


class PAVSReasonCode(str, Enum):
    """Machine-readable reason codes for pAVS decisions."""

    OK_EVIDENCE_PRESENT = "ok_evidence_present"
    """Receipt has evidence refs; accepted for review."""

    OK_NOT_REQUIRED = "ok_not_required"
    """Receipt marked NOT_REQUIRED (dry-run); no verification needed."""

    BLOCKED_NO_EVIDENCE = "blocked_no_evidence"
    """Receipt claims PENDING_PAVS but evidence_refs is empty."""

    BLOCKED_JOB_BLOCKED = "blocked_job_blocked"
    """Upstream job was BLOCKED; cannot verify blocked work."""

    FAILED_JOB_FAILED = "failed_job_failed"
    """Upstream job FAILED; receipt records failure, not success."""

    REJECTED_NO_RECEIPT_ID = "rejected_no_receipt_id"
    """Receipt missing receipt_id."""

    REJECTED_NO_JOB_ID = "rejected_no_job_id"
    """Receipt missing job_id."""

    REJECTED_NO_TENANT_ID = "rejected_no_tenant_id"
    """Receipt missing tenant_id."""

    REJECTED_UNKNOWN_STATUS = "rejected_unknown_status"
    """Receipt has verification_status we don't recognize."""

    INTERNAL_ERROR = "internal_error"
    """Unexpected error during verification seam processing."""


# ---------------------------------------------------------------------------
# Verification Result
# ---------------------------------------------------------------------------


@dataclass
class PAVSVerificationResult:
    """
    pAVS verification result for a ProofOfComputeReceipt.

    Created by the verification seam to record what decision was made,
    without claiming cryptographic verification or consensus happened.
    """

    # === Verification Identity ===
    verification_id: str
    """Unique verification identifier. Format: pv_{receipt_suffix}_{timestamp_hex}_{random}"""

    receipt_id: str
    """Source receipt identifier."""

    job_id: str
    """Original job identifier (from receipt)."""

    tenant_id: str
    """Actor scope / owner (from receipt)."""

    # === Decision Fields ===
    decision: PAVSDecision
    """The verification decision made."""

    reason_code: PAVSReasonCode
    """Machine-readable reason for decision."""

    reason_human: str
    """Operator-readable explanation."""

    # === Evidence Tracking ===
    evidence_refs: List[str] = field(default_factory=list)
    """Evidence refs from the receipt (if any)."""

    evidence_count: int = 0
    """Number of evidence refs present."""

    # === Truth-Boundary Fields (WSP 97) ===
    cabr_ready: bool = False
    """Always False — no CABR consensus exists in this slice."""

    payout_ready: bool = False
    """Always False — no payout engine exists in this slice."""

    verification_complete: bool = False
    """Always False — this seam accepts for review, does not complete verification."""

    # === Timestamps ===
    created_at: datetime = field(default_factory=_utc_now)
    """When this verification result was created."""

    # === Internal ===
    _source_receipt_snapshot: Optional[Dict[str, Any]] = None
    """Optional: receipt dict for audit trail."""

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """Serialize verification result to dict."""
        return {
            "verification_id": self.verification_id,
            "receipt_id": self.receipt_id,
            "job_id": self.job_id,
            "tenant_id": self.tenant_id,
            "decision": self.decision.value,
            "reason_code": self.reason_code.value,
            "reason_human": self.reason_human,
            "evidence_refs": self.evidence_refs,
            "evidence_count": self.evidence_count,
            "cabr_ready": self.cabr_ready,
            "payout_ready": self.payout_ready,
            "verification_complete": self.verification_complete,
            "created_at": _utc_iso(self.created_at),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PAVSVerificationResult":
        """Deserialize verification result from dict."""
        result = cls(
            verification_id=data["verification_id"],
            receipt_id=data["receipt_id"],
            job_id=data["job_id"],
            tenant_id=data["tenant_id"],
            decision=PAVSDecision(data["decision"]),
            reason_code=PAVSReasonCode(data["reason_code"]),
            reason_human=data.get("reason_human", ""),
            evidence_refs=data.get("evidence_refs", []),
            evidence_count=data.get("evidence_count", 0),
            cabr_ready=data.get("cabr_ready", False),
            payout_ready=data.get("payout_ready", False),
            verification_complete=data.get("verification_complete", False),
        )

        created_at = data.get("created_at")
        if created_at:
            result.created_at = datetime.fromisoformat(created_at)

        return result


# ---------------------------------------------------------------------------
# Verification ID Generation
# ---------------------------------------------------------------------------


def generate_verification_id(receipt_id: str) -> str:
    """
    Generate unique verification ID from receipt ID.

    Format: pv_{receipt_suffix}_{timestamp_hex}_{random_hex}
    Example: pv_extract_18a3b2c1_66d1a2b3_abc123
    """
    parts = receipt_id.split("_")
    if len(parts) >= 2:
        suffix = f"{parts[1]}"[:12]
    else:
        suffix = receipt_id[:12]

    timestamp_hex = hex(int(_utc_now().timestamp()))[2:][:8]
    random_hex = secrets.token_hex(3)
    return f"pv_{suffix}_{timestamp_hex}_{random_hex}"


# ---------------------------------------------------------------------------
# Core Verification Logic
# ---------------------------------------------------------------------------


def _validate_receipt_identity(
    receipt_id: Optional[str],
    job_id: Optional[str],
    tenant_id: Optional[str],
) -> Optional[PAVSVerificationResult]:
    """
    Validate receipt has required identity fields.

    Returns None if valid, or a rejection result if invalid.
    """
    if not receipt_id or not receipt_id.strip():
        return PAVSVerificationResult(
            verification_id=f"pv_rejected_{secrets.token_hex(4)}",
            receipt_id="",
            job_id=job_id or "",
            tenant_id=tenant_id or "",
            decision=PAVSDecision.REJECTED_MISSING_IDENTITY,
            reason_code=PAVSReasonCode.REJECTED_NO_RECEIPT_ID,
            reason_human="Receipt missing receipt_id; cannot verify receipt without identity.",
        )

    if not job_id or not job_id.strip():
        return PAVSVerificationResult(
            verification_id=generate_verification_id(receipt_id),
            receipt_id=receipt_id,
            job_id="",
            tenant_id=tenant_id or "",
            decision=PAVSDecision.REJECTED_MISSING_IDENTITY,
            reason_code=PAVSReasonCode.REJECTED_NO_JOB_ID,
            reason_human="Receipt missing job_id; cannot correlate to source job.",
        )

    if not tenant_id or not tenant_id.strip():
        return PAVSVerificationResult(
            verification_id=generate_verification_id(receipt_id),
            receipt_id=receipt_id,
            job_id=job_id,
            tenant_id="",
            decision=PAVSDecision.REJECTED_MISSING_IDENTITY,
            reason_code=PAVSReasonCode.REJECTED_NO_TENANT_ID,
            reason_human="Receipt missing tenant_id; cannot scope verification to actor.",
        )

    return None  # Valid


def _map_verification_status_to_decision(
    verification_status: VerificationStatus,
    evidence_refs: List[str],
) -> tuple[PAVSDecision, PAVSReasonCode, str]:
    """
    Map receipt verification_status + evidence to pAVS decision.

    Mapping per architect:
      PENDING_PAVS + evidence    -> ACCEPTED_FOR_REVIEW
      PENDING_PAVS - evidence    -> BLOCKED_MISSING_EVIDENCE
      NOT_REQUIRED               -> NOT_REQUIRED
      BLOCKED                    -> BLOCKED_UPSTREAM
      FAILED_INPUT               -> FAILED_INPUT
    """
    has_evidence = len(evidence_refs) > 0

    if verification_status == VerificationStatus.PENDING_PAVS:
        if has_evidence:
            return (
                PAVSDecision.ACCEPTED_FOR_REVIEW,
                PAVSReasonCode.OK_EVIDENCE_PRESENT,
                f"Receipt accepted for pAVS review. {len(evidence_refs)} evidence ref(s) present.",
            )
        else:
            return (
                PAVSDecision.BLOCKED_MISSING_EVIDENCE,
                PAVSReasonCode.BLOCKED_NO_EVIDENCE,
                "Receipt claims PENDING_PAVS but has no evidence_refs. "
                "Cannot proceed to verification without execution evidence.",
            )

    elif verification_status == VerificationStatus.NOT_REQUIRED:
        return (
            PAVSDecision.NOT_REQUIRED,
            PAVSReasonCode.OK_NOT_REQUIRED,
            "Receipt marked NOT_REQUIRED (likely dry-run). No verification needed.",
        )

    elif verification_status == VerificationStatus.BLOCKED:
        return (
            PAVSDecision.BLOCKED_UPSTREAM,
            PAVSReasonCode.BLOCKED_JOB_BLOCKED,
            "Upstream job was BLOCKED. Receipt records blocking evidence, not success.",
        )

    elif verification_status == VerificationStatus.FAILED_INPUT:
        return (
            PAVSDecision.FAILED_INPUT,
            PAVSReasonCode.FAILED_JOB_FAILED,
            "Upstream job FAILED due to input/validation. Receipt records failure evidence.",
        )

    else:
        return (
            PAVSDecision.REJECTED_INVALID_STATUS,
            PAVSReasonCode.REJECTED_UNKNOWN_STATUS,
            f"Receipt has unrecognized verification_status: {verification_status}",
        )


# ---------------------------------------------------------------------------
# Public API: Verify Receipt
# ---------------------------------------------------------------------------


def verify_receipt(
    receipt: Union[ProofOfComputeReceipt, Dict[str, Any]],
    include_receipt_snapshot: bool = False,
) -> PAVSVerificationResult:
    """
    Verify a ProofOfComputeReceipt and return a pAVS decision.

    This is a PLACEHOLDER verification seam. It does NOT:
      - Run cryptographic verification
      - Run CABR consensus
      - Issue tokens or rewards
      - Complete verification (only accepts for review)

    Args:
        receipt: ProofOfComputeReceipt object or dict from receipt.to_dict()
        include_receipt_snapshot: If True, include receipt dict in result for audit

    Returns:
        PAVSVerificationResult with decision, reason, and truth boundaries.

    WSP 97 truth:
        cabr_ready = False (always)
        payout_ready = False (always)
        verification_complete = False (always)
    """
    try:
        # Normalize input
        if isinstance(receipt, dict):
            receipt_id = receipt.get("receipt_id", "")
            job_id = receipt.get("job_id", "")
            tenant_id = receipt.get("tenant_id", "")
            verification_status_str = receipt.get("verification_status", "")
            evidence_refs = receipt.get("evidence_refs", [])
            receipt_dict = receipt
        else:
            receipt_id = receipt.receipt_id
            job_id = receipt.job_id
            tenant_id = receipt.tenant_id
            verification_status_str = receipt.verification_status.value
            evidence_refs = list(receipt.evidence_refs)
            receipt_dict = receipt.to_dict()

        # Validate identity
        identity_error = _validate_receipt_identity(receipt_id, job_id, tenant_id)
        if identity_error:
            logger.warning(
                "[PAVS] Identity validation failed: %s",
                identity_error.reason_code.value,
            )
            return identity_error

        # Parse verification status
        try:
            verification_status = VerificationStatus(verification_status_str)
        except ValueError:
            logger.warning(
                "[PAVS] Unknown verification_status: %s",
                verification_status_str,
            )
            return PAVSVerificationResult(
                verification_id=generate_verification_id(receipt_id),
                receipt_id=receipt_id,
                job_id=job_id,
                tenant_id=tenant_id,
                decision=PAVSDecision.REJECTED_INVALID_STATUS,
                reason_code=PAVSReasonCode.REJECTED_UNKNOWN_STATUS,
                reason_human=f"Unrecognized verification_status: '{verification_status_str}'",
            )

        # Map to decision
        decision, reason_code, reason_human = _map_verification_status_to_decision(
            verification_status,
            evidence_refs,
        )

        # Build result
        result = PAVSVerificationResult(
            verification_id=generate_verification_id(receipt_id),
            receipt_id=receipt_id,
            job_id=job_id,
            tenant_id=tenant_id,
            decision=decision,
            reason_code=reason_code,
            reason_human=reason_human,
            evidence_refs=list(evidence_refs),
            evidence_count=len(evidence_refs),
            cabr_ready=False,  # WSP 97: no CABR exists
            payout_ready=False,  # WSP 97: no payout engine exists
            verification_complete=False,  # WSP 97: only accepted for review
        )

        if include_receipt_snapshot:
            result._source_receipt_snapshot = receipt_dict

        logger.info(
            "[PAVS] Verified receipt %s -> decision=%s, reason=%s",
            receipt_id,
            decision.value,
            reason_code.value,
        )

        return result

    except Exception as e:
        logger.exception("[PAVS] Unexpected error during verification")
        return PAVSVerificationResult(
            verification_id=f"pv_error_{secrets.token_hex(4)}",
            receipt_id=str(receipt.get("receipt_id", "") if isinstance(receipt, dict) else getattr(receipt, "receipt_id", "")),
            job_id="",
            tenant_id="",
            decision=PAVSDecision.REJECTED_INVALID_STATUS,
            reason_code=PAVSReasonCode.INTERNAL_ERROR,
            reason_human=f"Internal error during verification: {str(e)}",
        )


# ---------------------------------------------------------------------------
# Convenience: Batch Verification
# ---------------------------------------------------------------------------


def verify_receipts(
    receipts: List[Union[ProofOfComputeReceipt, Dict[str, Any]]],
) -> List[PAVSVerificationResult]:
    """
    Verify multiple receipts in batch.

    Returns a list of results in the same order as input.
    """
    return [verify_receipt(r) for r in receipts]
