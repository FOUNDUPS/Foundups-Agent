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
    quarantine_unverified_signed_worker_assignment,
)
from modules.communication.moltbot_bridge.src import (
    reddog_signed_worker_agentdb_envelope as envelope_module,
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
    context: Mapping[str, Any],
    env: Mapping[str, str],
    authority_verification_context: Any | None,
) -> SignedWorkerSupervisorAdmission:
    """Verify authority, then CAS-admit only the exact verified task state."""

    authority, rejection = _resolve_supervisor_authority(
        repo_root=repo_root, db=db, task_id=task_id, context=context,
        env=env, authority_verification_context=authority_verification_context,
    )
    if rejection is not None:
        return rejection
    if authority is None:
        return SignedWorkerSupervisorAdmission(
            "REJECTED", context, "signed_worker_verification_missing"
        )
    admission = admit_signed_worker_execution_once(
        db=db, task_id=task_id, authority_context=authority
    )
    if admission is None:
        current = db.get_autonomous_task_by_id(task_id)
        if isinstance(current, Mapping) and current.get("status") == "quarantined":
            return SignedWorkerSupervisorAdmission(
                "REJECTED", context, "signed_worker_admission_rejected"
            )
        return SignedWorkerSupervisorAdmission("ALREADY_CLAIMED", {})
    return _validate_supervisor_admission(admission)


def _resolve_supervisor_authority(
    *,
    repo_root: Path,
    db: Any,
    task_id: str,
    context: Mapping[str, Any],
    env: Mapping[str, str],
    authority_verification_context: Any | None,
) -> tuple[Any | None, SignedWorkerSupervisorAdmission | None]:
    if (
        str(context.get("source") or "") != SIGNED_WORKER_DISPATCH_TASK_SOURCE
        or "signed_worker_agentdb_envelope" not in context
    ):
        return None, SignedWorkerSupervisorAdmission(
            "REJECTED", context, "signed_worker_task_routing_binding_mismatch",
        )
    try:
        authority = authority_verification_context
        if authority is None:
            authority = envelope_module.build_worker_dispatch_authority_context_from_env(
                repo_root=repo_root, env=env
            )
    except (TypeError, ValueError) as exc:
        quarantine_unverified_signed_worker_assignment(
            db=db, task_id=task_id,
            reason="signed_worker_agentdb_envelope_rejected"
        )
        return None, SignedWorkerSupervisorAdmission(
            "REJECTED", context, str(exc)[:160]
        )
    return authority, None


def _validate_supervisor_admission(
    admission: Any,
) -> SignedWorkerSupervisorAdmission:
    claimed = admission.claimed_context
    if (
        admission.discovered_by != SIGNED_WORKER_DISPATCH_TASK_SOURCE
        or SIGNED_WORKER_DISPATCH_TASK_SKILL not in admission.required_skills
    ):
        return SignedWorkerSupervisorAdmission(
            "REJECTED",
            bind_execution_admission(claimed, admission),
            "signed_worker_task_routing_binding_mismatch",
        )
    try:
        canonical = {
            **dict(admission.verified_envelope.canonical_context),
            **validated_result_history(claimed),
        }
    except ValueError as exc:
        return SignedWorkerSupervisorAdmission(
            "REJECTED", bind_execution_admission(claimed, admission), str(exc)
        )
    return SignedWorkerSupervisorAdmission(
        "ADMITTED", bind_execution_admission(canonical, admission)
    )

__all__ = [
    "SignedWorkerSupervisorAdmission",
    "admit_signed_worker_for_supervisor",
]
