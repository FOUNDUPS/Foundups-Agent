"""Exact-state execution admission for the OpenClaw signed-worker route."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.reddog_openclaw_hermes_0102_worker_dispatch_runtime import (
    SIGNED_WORKER_DISPATCH_TASK_SKILL,
    SIGNED_WORKER_DISPATCH_TASK_SOURCE,
)
from modules.communication.moltbot_bridge.src.reddog_signed_worker_claim_admission import (
    try_rehydrate_signed_worker_agentdb_context,
)
from modules.communication.moltbot_bridge.src.reddog_signed_worker_execution_claim import (
    admit_signed_worker_execution_once,
    bind_execution_admission,
)
from modules.infrastructure.database.src.signed_worker_result_ledger import (
    validated_result_history,
)


@dataclass(frozen=True)
class SignedWorkerSupervisorAdmission:
    """Result of claiming and verifying one exact AgentDB task state."""

    status: str
    context: Mapping[str, Any]
    error: str = ""


def admit_signed_worker_for_supervisor(
    *,
    repo_root: Path,
    db: Any,
    task_id: str,
    env: Mapping[str, str],
    authority_verification_context: Any | None,
) -> SignedWorkerSupervisorAdmission:
    """CAS-admit first, then verify only the state won by that CAS."""

    admission = admit_signed_worker_execution_once(db=db, task_id=task_id)
    if admission is None:
        return SignedWorkerSupervisorAdmission("ALREADY_CLAIMED", {})
    claimed = admission.claimed_context
    admitted = bind_execution_admission(claimed, admission)
    if (
        admission.discovered_by != SIGNED_WORKER_DISPATCH_TASK_SOURCE
        or SIGNED_WORKER_DISPATCH_TASK_SKILL not in admission.required_skills
        or str(claimed.get("source") or "") != SIGNED_WORKER_DISPATCH_TASK_SOURCE
    ):
        return SignedWorkerSupervisorAdmission(
            "REJECTED", admitted, "signed_worker_task_routing_binding_mismatch"
        )
    verified, error = try_rehydrate_signed_worker_agentdb_context(
        repo_root=repo_root,
        task_id=task_id,
        context=claimed,
        env=env,
        authority_verification_context=authority_verification_context,
    )
    if verified is None:
        return SignedWorkerSupervisorAdmission("REJECTED", admitted, error)
    try:
        verified = {
            **dict(verified),
            **validated_result_history(claimed),
        }
    except ValueError as exc:
        return SignedWorkerSupervisorAdmission("REJECTED", admitted, str(exc))
    return SignedWorkerSupervisorAdmission(
        "ADMITTED", bind_execution_admission(verified, admission)
    )

__all__ = [
    "SignedWorkerSupervisorAdmission",
    "admit_signed_worker_for_supervisor",
]
