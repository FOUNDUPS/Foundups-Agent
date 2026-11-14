"""Narrow idle-schedule adapter for guarded OpenRouter catalog discovery."""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from modules.ai_intelligence.ai_gateway.src.model_openrouter_scheduled_discovery import (
    ScheduledDiscoveryResult,
    discover_scheduled_openrouter_model_catalog,
)
from modules.ai_intelligence.ai_gateway.src.model_provider_catalog_snapshot import (
    DiscoveryInvocation,
    DiscoveryReceipt,
    ProviderCatalogCandidateSnapshot,
    build_discovery_invocation,
    rehydrate_candidate_snapshot,
    rehydrate_discovery_receipt,
)
from modules.infrastructure.idle_automation.src.schedule_claim_state import (
    ScheduleClaim,
    build_execution_id,
)
from modules.infrastructure.idle_automation.src.schedule_claim_codec import (
    MAX_ATTEMPTS,
)

_ROUTINE = "openrouter_catalog_refresh"
_SCHEDULE_ID = "e324884d66c4"
_RESULT_KEYS = ("success", "status", "reason", "replayed", "receipt_id",
                "candidate_snapshot_id")
_NONCOMPLETED = {
    "FAILED": ("FAILED", "scheduled_discovery_failed"),
    "INDETERMINATE": ("INDETERMINATE", "scheduled_discovery_indeterminate"),
    "BLOCKED_PRECALL": ("BLOCKED_PRECALL", "scheduled_discovery_blocked"),
}


async def run_openrouter_catalog_schedule_claim(
    claim: ScheduleClaim,
    *,
    repo_root: Path | str,
    runtime_root: Path | str,
    transport: object | None = None,
) -> dict[str, Any]:
    """Validate one exact daily claim and invoke only the guarded API."""

    invocation = _derive_invocation(claim)
    if invocation is None:
        return _result("BLOCKED_PRECALL", "claim_invalid")
    try:
        guarded = await discover_scheduled_openrouter_model_catalog(
            invocation,
            repo_root=repo_root,
            runtime_root=runtime_root,
            transport=transport,
        )
    except Exception:
        return _result("INDETERMINATE", "scheduled_discovery_adapter_failed")
    return _project_guarded(guarded, invocation)


def _derive_invocation(claim: object) -> DiscoveryInvocation | None:
    if (
        type(claim) is not ScheduleClaim
        or claim.schedule_id != _SCHEDULE_ID
        or claim.routine != _ROUTINE
        or claim.cadence != "daily"
        or not _bounded_claim_fields(claim)
    ):
        return None
    try:
        expected = build_execution_id(
            claim.schedule_id,
            claim.routine,
            claim.cadence,
            claim.window_start,
            claim.window_end,
        )
        if not secrets.compare_digest(claim.execution_id, expected):
            return None
        bounds = _daily_bounds(claim.window_start, claim.window_end)
        if bounds is None:
            return None
        start_ms, end_ms = bounds
        return build_discovery_invocation(
            mode="scheduled", schedule_id=f"idle:{claim.execution_id}",
            scheduled_for_ms=start_ms, expires_at_ms=end_ms - 1,
        )
    except (TypeError, ValueError):
        return None


def _bounded_claim_fields(claim: ScheduleClaim) -> bool:
    if (
        type(claim.token) is not str
        or not 0 < len(claim.token) <= 256
        or type(claim.claimant_id) is not str
        or not 0 < len(claim.claimant_id) <= 256
        or type(claim.attempt) is not int
        or not 1 <= claim.attempt <= MAX_ATTEMPTS
    ):
        return False
    try:
        lease = datetime.fromisoformat(claim.lease_expires_at)
    except (TypeError, ValueError):
        return False
    return (
        lease.tzinfo is not None
        and lease.utcoffset() == timedelta(0)
        and lease.isoformat() == claim.lease_expires_at
    )


def _daily_bounds(start_text: str, end_text: str) -> tuple[int, int] | None:
    try:
        start = datetime.fromisoformat(start_text)
        end = datetime.fromisoformat(end_text)
    except (TypeError, ValueError):
        return None
    if (
        start.tzinfo is None
        or end.tzinfo is None
        or start.utcoffset() != timedelta(0)
        or end.utcoffset() != timedelta(0)
        or start.isoformat() != start_text
        or end.isoformat() != end_text
        or start
        != start.astimezone(UTC).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        or end - start != timedelta(days=1)
    ):
        return None
    return _epoch_ms(start), _epoch_ms(end)


def _epoch_ms(value: datetime) -> int:
    delta = value.astimezone(UTC) - datetime(1970, 1, 1, tzinfo=UTC)
    return (
        delta.days * 86_400_000
        + delta.seconds * 1_000
        + delta.microseconds // 1_000
    )


def _project_guarded(
    guarded: object, invocation: DiscoveryInvocation
) -> dict[str, Any]:
    if type(guarded) is not ScheduledDiscoveryResult:
        return _result(
            "INDETERMINATE", "scheduled_discovery_result_invalid"
        )
    if guarded.status != "COMPLETED":
        projection = (
            _NONCOMPLETED.get(guarded.status)
            if type(guarded.status) is str
            else None
        )
        if projection is None:
            projection = (
                "INDETERMINATE",
                "scheduled_discovery_result_invalid",
            )
        return _result(
            *projection,
            replayed=guarded.replayed is True,
        )
    evidence, invalid_reason = _canonical_completed_evidence(guarded)
    if evidence is None:
        return _result("INDETERMINATE", invalid_reason)
    receipt, candidate = evidence
    if not _completed_lineage(receipt, candidate, invocation):
        return _result("INDETERMINATE", "completed_lineage_invalid")
    return _result(
        "COMPLETED",
        "completed",
        success=True,
        replayed=guarded.replayed is True,
        receipt_id=receipt.receipt_id,
        candidate_snapshot_id=candidate.snapshot_id,
    )


def _canonical_completed_evidence(
    guarded: ScheduledDiscoveryResult,
) -> tuple[tuple[DiscoveryReceipt, ProviderCatalogCandidateSnapshot] | None, str]:
    receipt, candidate = guarded.receipt, guarded.candidate
    if type(receipt) is not DiscoveryReceipt:
        return None, "completed_receipt_invalid"
    try:
        canonical_receipt = rehydrate_discovery_receipt(receipt.to_dict())
    except (AttributeError, KeyError, TypeError, ValueError, OverflowError,
            RecursionError):
        return None, "completed_receipt_invalid"
    if type(candidate) is not ProviderCatalogCandidateSnapshot:
        return None, "completed_candidate_invalid"
    try:
        canonical_candidate = rehydrate_candidate_snapshot(
            candidate.to_dict(),
            now_ms=candidate.observed_at_ms,
        )
    except (AttributeError, KeyError, TypeError, ValueError, OverflowError,
            RecursionError):
        return None, "completed_candidate_invalid"
    return (canonical_receipt, canonical_candidate), ""


def _completed_lineage(
    receipt: DiscoveryReceipt,
    candidate: ProviderCatalogCandidateSnapshot,
    invocation: DiscoveryInvocation,
) -> bool:
    return (
        receipt.outcome == "COMPLETED"
        and receipt.invocation == invocation
        and candidate.observation_receipt == receipt
        and candidate.snapshot_id == receipt.candidate_snapshot_id
    )


def _result(
    status: str,
    reason: str,
    *,
    success: bool = False,
    replayed: bool = False,
    receipt_id: str | None = None,
    candidate_snapshot_id: str | None = None,
) -> dict[str, Any]:
    values = (success, status, reason, replayed, receipt_id,
              candidate_snapshot_id)
    return dict(zip(_RESULT_KEYS, values))


__all__ = ["run_openrouter_catalog_schedule_claim"]
