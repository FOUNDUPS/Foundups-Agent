#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Proof-of-Compute Receipt — FAM-Side Compute Evidence Seam

Records completed, blocked, or failed FoundUpJob execution as evidence receipts
that can later be consumed by pAVS verification and CABR/PoB consensus.

WSP 97 TRUTH BOUNDARIES:
  ✓ DOES:
    - Accept FoundUpJob final states (SUCCEEDED, BLOCKED, FAILED)
    - Generate receipt_id for evidence correlation
    - Preserve job identity (job_id, tenant_id, foundup_id, intent_id)
    - Record compute_used/compute_summary from job payload
    - Preserve evidence_refs from job execution
    - Set truthful verification_status based on job outcome
    - Set payout_status = NOT_EVALUATED (no payout engine exists yet)
    - Set cabr_status = NOT_SUBMITTED (no CABR consensus exists yet)

  ✗ DOES NOT:
    - Issue tokens or UPS
    - Allocate rewards
    - Write to wallet
    - Run CABR consensus
    - Run pAVS verification engine
    - Accept non-terminal job states (QUEUED, RUNNING)

Architecture:
  W4 (Hermes) executes FoundUpJob -> job reaches terminal state
  W6 (this slice) creates ProofOfComputeReceipt from terminal job
  W7/W10 (future) consume receipts for pAVS verification / CABR scoring

WSP Compliance:
  WSP 11  : Interface contract (explicit, typed)
  WSP 97  : System Execution Prompting (truth boundaries)
  WSP 91  : Observability (timestamps, audit fields)

NAVIGATION:
  -> Consumed by: future pAVS verifier, CABR consensus engine
  -> Produces from: FoundUpJob (foundup_job_contract.py)
  -> Related: modules/foundups/agent_market/src/models.py (Proof, Verification)
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from .foundup_job_contract import (
    FoundUpJob,
    JobStatus,
    StatusReasonCode,
    is_terminal_status,
)

logger = logging.getLogger("proof_of_compute_receipt")


def _utc_now() -> datetime:
    """Return current UTC timestamp."""
    return datetime.now(timezone.utc)


def _utc_iso(dt: Optional[datetime]) -> Optional[str]:
    """Convert datetime to ISO string or None."""
    return dt.isoformat() if dt else None


# ---------------------------------------------------------------------------
# Verification Status (pre-pAVS)
# ---------------------------------------------------------------------------


class VerificationStatus(str, Enum):
    """
    Receipt verification status — truth-surface for pAVS pipeline.

    WSP 97: These statuses describe WHAT WE KNOW, not what we claim.
    """

    PENDING_PAVS = "pending_pavs"
    """Receipt accepted, awaiting pAVS verification. Normal success path."""

    NOT_REQUIRED = "not_required"
    """Receipt does not require verification (e.g., dry-run, query-only)."""

    BLOCKED = "blocked"
    """Job was blocked; receipt records blocking evidence."""

    FAILED_INPUT = "failed_input"
    """Job failed due to input/validation; receipt records failure evidence."""


class PayoutStatus(str, Enum):
    """Payout status — always NOT_EVALUATED until payout engine exists."""

    NOT_EVALUATED = "not_evaluated"
    """No payout engine has evaluated this receipt."""


class CABRStatus(str, Enum):
    """CABR consensus status — always NOT_SUBMITTED until consensus exists."""

    NOT_SUBMITTED = "not_submitted"
    """Receipt not submitted to CABR consensus."""


# ---------------------------------------------------------------------------
# Receipt Result (factory output)
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class ReceiptResult:
    """Result of receipt creation attempt."""

    success: bool
    """True if receipt was created."""

    receipt: Optional["ProofOfComputeReceipt"] = None
    """The created receipt, if successful."""

    error_code: Optional[str] = None
    """Machine-readable error code if failed."""

    error_message: Optional[str] = None
    """Human-readable error message if failed."""


# ---------------------------------------------------------------------------
# Proof-of-Compute Receipt
# ---------------------------------------------------------------------------


@dataclass
class ProofOfComputeReceipt:
    """
    Evidence receipt for completed FoundUpJob execution.

    Created ONLY from terminal job states (SUCCEEDED, BLOCKED, FAILED).
    Records compute evidence without claiming payout, CABR, or pAVS happened.

    Identity fields link back to the originating job and FoundUp.
    Status fields reflect truthful pre-pAVS state.
    Evidence fields preserve execution artifacts.
    """

    # === Receipt Identity ===
    receipt_id: str
    """Unique receipt identifier. Format: rcpt_{job_id_suffix}_{timestamp_hex}"""

    job_id: str
    """Source FoundUpJob identifier."""

    tenant_id: str
    """Actor scope / owner from job."""

    # === Optional Job Context ===
    foundup_id: Optional[str] = None
    """Target FoundUp (if job was foundup-scoped)."""

    intent_id: Optional[str] = None
    """Source request correlation (if present on job)."""

    # === Execution Summary ===
    requested_action: str = ""
    """Action that was requested (from job)."""

    job_status: JobStatus = JobStatus.SUCCEEDED
    """Terminal status of the job that produced this receipt."""

    status_reason_code: StatusReasonCode = StatusReasonCode.UNKNOWN
    """Machine-readable reason from job."""

    status_reason_human: str = ""
    """Operator-readable explanation from job."""

    # === Compute Evidence ===
    compute_used: int = 0
    """Compute units consumed (from job)."""

    compute_summary: Optional[Dict[str, Any]] = None
    """
    Extended compute metadata if present in job payload.
    Example: {"model": "sonnet", "tokens_in": 1000, "tokens_out": 500}
    """

    evidence_refs: List[str] = field(default_factory=list)
    """Paths/IDs proving execution outcome (from job)."""

    # === Worker Identity ===
    worker_id: Optional[str] = None
    """Worker that executed the job (from job)."""

    # === Timestamps ===
    created_at: datetime = field(default_factory=_utc_now)
    """Receipt creation timestamp (now)."""

    job_created_at: Optional[datetime] = None
    """When the source job was created."""

    job_completed_at: Optional[datetime] = None
    """When the source job reached terminal state."""

    # === Truth-Status Fields (WSP 97) ===
    verification_status: VerificationStatus = VerificationStatus.PENDING_PAVS
    """Pre-pAVS verification state. Set based on job outcome."""

    payout_status: PayoutStatus = PayoutStatus.NOT_EVALUATED
    """Always NOT_EVALUATED — no payout engine exists."""

    cabr_status: CABRStatus = CABRStatus.NOT_SUBMITTED
    """Always NOT_SUBMITTED — no CABR consensus exists."""

    # === Internal ===
    _source_job_snapshot: Optional[Dict[str, Any]] = None
    """Optional: full job dict for audit trail."""

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """Serialize receipt to dict."""
        return {
            "receipt_id": self.receipt_id,
            "job_id": self.job_id,
            "tenant_id": self.tenant_id,
            "foundup_id": self.foundup_id,
            "intent_id": self.intent_id,
            "requested_action": self.requested_action,
            "job_status": self.job_status.value,
            "status_reason_code": self.status_reason_code.value,
            "status_reason_human": self.status_reason_human,
            "compute_used": self.compute_used,
            "compute_summary": self.compute_summary,
            "evidence_refs": self.evidence_refs,
            "worker_id": self.worker_id,
            "created_at": _utc_iso(self.created_at),
            "job_created_at": _utc_iso(self.job_created_at),
            "job_completed_at": _utc_iso(self.job_completed_at),
            "verification_status": self.verification_status.value,
            "payout_status": self.payout_status.value,
            "cabr_status": self.cabr_status.value,
        }

    def to_json(self, indent: int = 2) -> str:
        """Serialize receipt to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, default=str)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProofOfComputeReceipt":
        """Deserialize receipt from dict."""
        receipt = cls(
            receipt_id=data["receipt_id"],
            job_id=data["job_id"],
            tenant_id=data["tenant_id"],
            foundup_id=data.get("foundup_id"),
            intent_id=data.get("intent_id"),
            requested_action=data.get("requested_action", ""),
            job_status=JobStatus(data.get("job_status", "succeeded")),
            status_reason_code=_parse_reason_code(
                data.get("status_reason_code", "UNKNOWN")
            ),
            status_reason_human=data.get("status_reason_human", ""),
            compute_used=data.get("compute_used", 0),
            compute_summary=data.get("compute_summary"),
            evidence_refs=data.get("evidence_refs", []),
            worker_id=data.get("worker_id"),
            verification_status=VerificationStatus(
                data.get("verification_status", "pending_pavs")
            ),
            payout_status=PayoutStatus(
                data.get("payout_status", "not_evaluated")
            ),
            cabr_status=CABRStatus(
                data.get("cabr_status", "not_submitted")
            ),
        )

        # Restore timestamps
        for ts_field in ("created_at", "job_created_at", "job_completed_at"):
            ts_value = data.get(ts_field)
            if ts_value:
                setattr(receipt, ts_field, datetime.fromisoformat(ts_value))

        return receipt


def _parse_reason_code(value: str) -> StatusReasonCode:
    """Parse reason code string, falling back to UNKNOWN if invalid."""
    try:
        return StatusReasonCode(value)
    except ValueError:
        return StatusReasonCode.UNKNOWN


# ---------------------------------------------------------------------------
# Receipt ID Generation
# ---------------------------------------------------------------------------


def generate_receipt_id(job_id: str) -> str:
    """
    Generate unique receipt ID from job ID.

    Format: rcpt_{job_id_suffix}_{timestamp_hex}_{random_hex}
    Example: rcpt_extract_18a3b2c1_f4e5d6_abc123
    """
    import secrets

    # Extract meaningful suffix from job_id (e.g., j_extract_18a3b2c1_f4e5d6 -> extract_18a3b2c1)
    parts = job_id.split("_")
    if len(parts) >= 3:
        suffix = f"{parts[1]}_{parts[2]}"[:20]
    else:
        suffix = job_id[:20]

    timestamp_hex = hex(int(_utc_now().timestamp()))[2:][:8]
    random_hex = secrets.token_hex(3)
    return f"rcpt_{suffix}_{timestamp_hex}_{random_hex}"


# ---------------------------------------------------------------------------
# Factory: Create Receipt from Job
# ---------------------------------------------------------------------------


def _map_job_status_to_verification(
    job_status: JobStatus,
    reason_code: StatusReasonCode,
    is_dry_run: bool,
) -> VerificationStatus:
    """
    Map FoundUpJob terminal status to VerificationStatus.

    WSP 97 mapping:
      SUCCEEDED + not dry-run -> PENDING_PAVS (needs verification)
      SUCCEEDED + dry-run     -> NOT_REQUIRED (no real execution)
      BLOCKED                 -> BLOCKED (blocked evidence)
      FAILED                  -> FAILED_INPUT (failure evidence)
    """
    if job_status == JobStatus.SUCCEEDED:
        if is_dry_run or reason_code == StatusReasonCode.OK_DRY_RUN_PASSED:
            return VerificationStatus.NOT_REQUIRED
        return VerificationStatus.PENDING_PAVS
    elif job_status == JobStatus.BLOCKED:
        return VerificationStatus.BLOCKED
    elif job_status == JobStatus.FAILED:
        return VerificationStatus.FAILED_INPUT
    else:
        # Should not reach here for terminal states
        return VerificationStatus.FAILED_INPUT


def create_receipt_from_job(
    job: FoundUpJob,
    include_job_snapshot: bool = False,
) -> ReceiptResult:
    """
    Create a Proof-of-Compute receipt from a terminal FoundUpJob.

    Args:
        job: The FoundUpJob to create a receipt for
        include_job_snapshot: If True, include full job dict in receipt

    Returns:
        ReceiptResult with success=True and receipt, or success=False with error

    WSP 97 behavior:
        - SUCCEEDED job -> receipt with verification_status=PENDING_PAVS
        - BLOCKED job   -> receipt with verification_status=BLOCKED
        - FAILED job    -> receipt with verification_status=FAILED_INPUT
        - QUEUED/RUNNING -> error (non-terminal, no proof yet)
    """
    # Validate: only accept terminal states
    if not is_terminal_status(job.status) and job.status != JobStatus.BLOCKED:
        # BLOCKED is technically non-terminal but represents evidence state
        if job.status == JobStatus.QUEUED:
            return ReceiptResult(
                success=False,
                error_code="JOB_NOT_STARTED",
                error_message=(
                    f"Job {job.job_id} is QUEUED; no proof exists until execution completes. "
                    "Submit receipt after job reaches SUCCEEDED, FAILED, or BLOCKED."
                ),
            )
        elif job.status == JobStatus.RUNNING:
            return ReceiptResult(
                success=False,
                error_code="JOB_IN_PROGRESS",
                error_message=(
                    f"Job {job.job_id} is RUNNING; no final proof exists yet. "
                    "Submit receipt after job reaches SUCCEEDED, FAILED, or BLOCKED."
                ),
            )

    # Validate: job must have identity
    if not job.job_id or not job.job_id.strip():
        return ReceiptResult(
            success=False,
            error_code="MISSING_JOB_ID",
            error_message="Job has no job_id; cannot create receipt without identity.",
        )

    if not job.tenant_id or not job.tenant_id.strip():
        return ReceiptResult(
            success=False,
            error_code="MISSING_TENANT_ID",
            error_message="Job has no tenant_id; cannot create receipt without actor scope.",
        )

    # Extract compute summary from payload if present
    compute_summary = None
    payload = job.payload or {}
    if "compute_summary" in payload:
        compute_summary = payload["compute_summary"]
    elif any(k in payload for k in ("model", "tokens_in", "tokens_out", "duration_ms")):
        # Build compute summary from known fields
        compute_summary = {
            k: payload[k]
            for k in ("model", "tokens_in", "tokens_out", "duration_ms", "tier")
            if k in payload
        }

    # Check dry-run mode
    is_dry_run = getattr(job.policy_flags, "dry_run_mode", False)

    # Map status to verification
    verification_status = _map_job_status_to_verification(
        job.status,
        job.status_reason_code,
        is_dry_run,
    )

    # Create receipt
    receipt = ProofOfComputeReceipt(
        receipt_id=generate_receipt_id(job.job_id),
        job_id=job.job_id,
        tenant_id=job.tenant_id,
        foundup_id=job.foundup_id,
        intent_id=job.intent_id,
        requested_action=job.requested_action,
        job_status=job.status,
        status_reason_code=job.status_reason_code,
        status_reason_human=job.status_reason_human,
        compute_used=job.compute_used,
        compute_summary=compute_summary,
        evidence_refs=list(job.evidence_refs),  # Copy to avoid mutation
        worker_id=job.worker_id,
        job_created_at=job.created_at,
        job_completed_at=job.completed_at,
        verification_status=verification_status,
        payout_status=PayoutStatus.NOT_EVALUATED,
        cabr_status=CABRStatus.NOT_SUBMITTED,
    )

    if include_job_snapshot:
        receipt._source_job_snapshot = job.to_dict()

    logger.info(
        "[RECEIPT] Created %s from job %s (status=%s, verification=%s)",
        receipt.receipt_id,
        job.job_id,
        job.status.value,
        verification_status.value,
    )

    return ReceiptResult(success=True, receipt=receipt)


# ---------------------------------------------------------------------------
# Convenience: Direct Receipt Creation
# ---------------------------------------------------------------------------


def create_receipt(
    job_id: str,
    tenant_id: str,
    job_status: JobStatus,
    status_reason_code: StatusReasonCode,
    status_reason_human: str,
    foundup_id: Optional[str] = None,
    intent_id: Optional[str] = None,
    requested_action: str = "",
    compute_used: int = 0,
    compute_summary: Optional[Dict[str, Any]] = None,
    evidence_refs: Optional[List[str]] = None,
    worker_id: Optional[str] = None,
) -> ReceiptResult:
    """
    Convenience factory to create a receipt without a full FoundUpJob object.

    Useful for W4/W5 workers that may not have a materialized FoundUpJob.
    Same WSP 97 rules apply: only accepts terminal states.
    """
    # Validate terminal status
    if not is_terminal_status(job_status) and job_status != JobStatus.BLOCKED:
        return ReceiptResult(
            success=False,
            error_code="NON_TERMINAL_STATUS",
            error_message=(
                f"Status {job_status.value} is not terminal; "
                "receipt requires SUCCEEDED, FAILED, or BLOCKED."
            ),
        )

    if not job_id or not job_id.strip():
        return ReceiptResult(
            success=False,
            error_code="MISSING_JOB_ID",
            error_message="job_id is required.",
        )

    if not tenant_id or not tenant_id.strip():
        return ReceiptResult(
            success=False,
            error_code="MISSING_TENANT_ID",
            error_message="tenant_id is required.",
        )

    # Map status to verification
    is_dry_run = status_reason_code == StatusReasonCode.OK_DRY_RUN_PASSED
    verification_status = _map_job_status_to_verification(
        job_status,
        status_reason_code,
        is_dry_run,
    )

    receipt = ProofOfComputeReceipt(
        receipt_id=generate_receipt_id(job_id),
        job_id=job_id,
        tenant_id=tenant_id,
        foundup_id=foundup_id,
        intent_id=intent_id,
        requested_action=requested_action,
        job_status=job_status,
        status_reason_code=status_reason_code,
        status_reason_human=status_reason_human,
        compute_used=compute_used,
        compute_summary=compute_summary,
        evidence_refs=list(evidence_refs or []),
        worker_id=worker_id,
        verification_status=verification_status,
        payout_status=PayoutStatus.NOT_EVALUATED,
        cabr_status=CABRStatus.NOT_SUBMITTED,
    )

    logger.info(
        "[RECEIPT] Created %s for job %s (status=%s, verification=%s)",
        receipt.receipt_id,
        job_id,
        job_status.value,
        verification_status.value,
    )

    return ReceiptResult(success=True, receipt=receipt)
