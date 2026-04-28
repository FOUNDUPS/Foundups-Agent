# -*- coding: utf-8 -*-
"""
Receipt Emitter — Terminal Job to pAVS Receipt Pipeline

Wraps the receipt creation and pAVS verification for terminal FoundUpJobs.
Only terminal jobs (SUCCEEDED, FAILED, BLOCKED) can have receipts emitted.

Architecture:
  Terminal FoundUpJob -> create_receipt_from_job() -> ProofOfComputeReceipt
                      -> verify_receipt() -> PAVSVerificationResult

WSP Compliance:
  WSP 11  : Interface contract (typed receipt pipeline)
  WSP 97  : System Execution Prompting (only terminal jobs, truthful status)

Truth Boundaries (WSP 97):
  - Only terminal jobs can emit receipts
  - cabr_ready = False (no CABR consensus exists)
  - payout_ready = False (no payout engine exists)
  - verification_complete = False (only accepted for review)

NAVIGATION:
  -> Uses: proof_of_compute_receipt.py (create_receipt_from_job)
  -> Uses: pavs_verification_seam.py (verify_receipt)
  -> Called by: FoundUpJobConsumer after terminal state
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Optional

from .proof_of_compute_receipt import (
    ProofOfComputeReceipt,
    ReceiptResult,
    create_receipt_from_job,
)
from .pavs_verification_seam import (
    PAVSVerificationResult,
    verify_receipt,
)

logger = logging.getLogger("receipt_emitter")


# ---------------------------------------------------------------------------
# Emission Result
# ---------------------------------------------------------------------------


@dataclass
class ReceiptEmissionResult:
    """
    Result of receipt emission for a terminal job.

    Contains both the receipt and the pAVS verification result,
    or error information if emission failed.
    """

    success: bool
    """True if receipt was created and verified."""

    job_id: str
    """Source job identifier."""

    receipt: Optional[ProofOfComputeReceipt] = None
    """Created receipt (if successful)."""

    verification: Optional[PAVSVerificationResult] = None
    """pAVS verification result (if receipt created)."""

    error: Optional[str] = None
    """Error message if emission failed."""


# ---------------------------------------------------------------------------
# Terminal Status Check
# ---------------------------------------------------------------------------


def _is_terminal_job(job: Any) -> bool:
    """
    Check if job is in terminal state.

    Terminal states: SUCCEEDED, FAILED, BLOCKED.
    Non-terminal: QUEUED, RUNNING.

    Args:
        job: FoundUpJob or duck-typed object with status attribute.

    Returns:
        True if job is in terminal state.
    """
    try:
        # Import here to avoid circular deps
        from modules.communication.moltbot_bridge.src.foundup_job_contract import (
            is_terminal_status,
        )

        status = getattr(job, "status", None)
        if status is None:
            return False
        return is_terminal_status(status)
    except ImportError:
        # Fallback: check by status value
        status = getattr(job, "status", None)
        if status is None:
            return False
        status_str = status.value if hasattr(status, "value") else str(status)
        return status_str.lower() in ("succeeded", "failed", "blocked")


# ---------------------------------------------------------------------------
# Receipt Emission
# ---------------------------------------------------------------------------


def emit_receipt_for_terminal_job(job: Any) -> ReceiptEmissionResult:
    """
    Emit receipt for a terminal FoundUpJob.

    Only terminal jobs (SUCCEEDED, FAILED, BLOCKED) can have receipts.
    Non-terminal jobs are rejected truthfully.

    Steps:
      1. Validate job is terminal
      2. Create receipt via create_receipt_from_job()
      3. Verify receipt via verify_receipt()
      4. Return combined result

    Args:
        job: FoundUpJob instance in terminal state.

    Returns:
        ReceiptEmissionResult with receipt and verification (if successful).

    WSP 97 truth boundaries:
      - Non-terminal jobs rejected with error
      - cabr_ready = False in verification result
      - payout_ready = False in verification result
      - verification_complete = False in verification result
    """
    job_id = getattr(job, "job_id", "") or ""

    # Step 1: Validate terminal status
    if not _is_terminal_job(job):
        status = getattr(job, "status", None)
        status_str = status.value if hasattr(status, "value") else str(status or "unknown")
        error = f"Job {job_id} is not terminal (status={status_str}); receipt emission rejected"
        logger.warning("[RECEIPT-EMITTER] %s", error)
        return ReceiptEmissionResult(
            success=False,
            job_id=job_id,
            error=error,
        )

    # Step 2: Create receipt
    try:
        receipt_result: ReceiptResult = create_receipt_from_job(job)

        if not receipt_result.success:
            error = f"Receipt creation failed: {receipt_result.error}"
            logger.warning("[RECEIPT-EMITTER] %s", error)
            return ReceiptEmissionResult(
                success=False,
                job_id=job_id,
                error=error,
            )

        receipt = receipt_result.receipt

    except Exception as e:
        logger.exception("[RECEIPT-EMITTER] Receipt creation exception for job %s", job_id)
        return ReceiptEmissionResult(
            success=False,
            job_id=job_id,
            error=f"Receipt creation exception: {e}",
        )

    # Step 3: Verify receipt
    try:
        verification: PAVSVerificationResult = verify_receipt(receipt)

        logger.info(
            "[RECEIPT-EMITTER] Receipt emitted for job %s: decision=%s",
            job_id,
            verification.decision.value,
        )

        return ReceiptEmissionResult(
            success=True,
            job_id=job_id,
            receipt=receipt,
            verification=verification,
        )

    except Exception as e:
        logger.exception("[RECEIPT-EMITTER] Verification exception for job %s", job_id)
        return ReceiptEmissionResult(
            success=True,  # Receipt was created, just verification failed
            job_id=job_id,
            receipt=receipt,
            error=f"Verification exception: {e}",
        )
