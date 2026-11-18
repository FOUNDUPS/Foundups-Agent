"""Scheduled-claim adapter for one read-only resident FoundUp reconciliation.

Idle Automation owns cadence and durable claims. This module owns only the
resident routine's exact claim validation, default-off activation, RedDog
handoff, and bounded result projection.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any, Mapping

from modules.infrastructure.idle_automation.src.schedule_claim_state import (
    ScheduleClaim,
)

RESIDENT_RECONCILE_ROUTINE = "resident_reconcile"


def valid_resident_reconcile_claim(claim: object) -> bool:
    return (
        type(claim) is ScheduleClaim
        and claim.routine == RESIDENT_RECONCILE_ROUTINE
        and claim.cadence == "daily"
        and bool(claim.schedule_id)
        and bool(claim.execution_id)
        and bool(claim.window_start)
        and bool(claim.window_end)
        and bool(claim.token)
    )


async def dispatch_resident_reconcile_claim(
    claim: ScheduleClaim,
    *,
    module_path: Path | str,
    environ: Mapping[str, str] | None = None,
    runner: Any = None,
) -> Mapping[str, Any]:
    env = os.environ if environ is None else environ
    if not valid_resident_reconcile_claim(claim):
        return _blocked("scheduled_resident_claim_invalid")
    if not _truthy(env.get("AUTO_REDDOG_RESIDENT_RECONCILE")):
        return _blocked("scheduled_resident_reconcile_disabled")

    if runner is None:
        from modules.communication.moltbot_bridge.src.reddog_scheduled_resident_reconcile import (
            run_scheduled_resident_reconcile,
        )

        runner = run_scheduled_resident_reconcile
    repo_root = Path(module_path).resolve().parents[2]
    return await asyncio.to_thread(runner, claim, repo_root=repo_root)


def project_resident_reconcile_dispatch_outcome(
    response: Mapping[str, Any],
) -> dict[str, Any]:
    success = response.get("success") is True
    rejections = response.get("rejection_reasons")
    reasons = rejections if isinstance(rejections, (list, tuple)) else ()
    resident = response.get("resident_response")
    resident_intent_id = (
        resident.get("intent_id")
        if isinstance(resident, Mapping)
        else None
    )
    return {
        "success": success,
        "outcome": "resident_reconcile_failed",
        "error": None if success else ",".join(str(item) for item in reasons),
        "receipt_id": response.get("receipt_id"),
        "resident_intent_id": resident_intent_id,
    }


def _truthy(value: Any) -> bool:
    return str(value or "").strip().lower() in {"true", "1", "yes", "on"}


def _blocked(reason: str) -> dict[str, Any]:
    return {"success": False, "rejection_reasons": [reason]}


__all__ = [
    "RESIDENT_RECONCILE_ROUTINE",
    "dispatch_resident_reconcile_claim",
    "project_resident_reconcile_dispatch_outcome",
    "valid_resident_reconcile_claim",
]
