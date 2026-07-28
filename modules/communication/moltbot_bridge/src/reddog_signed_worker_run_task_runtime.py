"""Fail-closed direct run_task adapter for signed RedDog workers."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Mapping, Sequence

from modules.communication.moltbot_bridge.src.reddog_signed_worker_execution_claim import (
    SIGNED_WORKER_TASK_PREFIX,
    admit_signed_worker_execution_once,
    bind_execution_admission,
)
from modules.communication.moltbot_bridge.src.reddog_signed_worker_claim_admission import (
    quarantine_unverified_signed_worker_assignment,
)
from modules.communication.moltbot_bridge.src.reddog_signed_worker_result_receipt import (
    DIRECT_ACCEPT,
    DIRECT_REJECT,
    DIRECT_REQUEUED,
    append_signed_worker_result_history,
    build_signed_worker_task_result_receipt,
)
from modules.infrastructure.database.src.signed_worker_execution_store import (
    finalize_signed_worker_execution,
)
from modules.infrastructure.database.src.signed_worker_assurance_staging import (
    rehydrate_staged_assurance_completion,
)
from modules.infrastructure.database.src.signed_worker_result_ledger import (
    validated_result_history,
)
from modules.communication.moltbot_bridge.src.reddog_signed_worker_execution_heartbeat import (
    signed_worker_execution_heartbeat,
)


logger = logging.getLogger(__name__)
SIGNED_SOURCE = "reddog_signed_worker_dispatch_runtime"
SIGNED_SKILL = "reddog_signed_worker_dispatch"


def execute_signed_worker_from_agentdb(
    *,
    repo_root: Path,
    db: Any,
    task_id: str,
    context: Mapping[str, Any],
    required_skills: Sequence[str],
    source: str,
    discovered_by: str,
    signed_worker_runner: Any | None,
    env: Mapping[str, str],
) -> Mapping[str, Any] | None:
    """Verify, claim once, and execute one signed-origin AgentDB task."""
    has_signed_marker = _has_signed_marker(
        task_id,
        context,
        required_skills,
        source=source,
        discovered_by=discovered_by,
    )
    if not has_signed_marker:
        return None
    if not task_id.startswith(SIGNED_WORKER_TASK_PREFIX):
        rejection = _rejected("reddog_signed_worker_namespace_mismatch")
        rejection["finalization_owned"] = True
        return rejection
    verified, admission, rejection = _verify_and_admit(
        repo_root=repo_root, db=db, task_id=task_id, context=context,
        required_skills=required_skills, source=source,
        discovered_by=discovered_by, env=env,
    )
    if rejection is not None:
        return rejection
    if verified is None or admission is None:
        return _rejected("reddog_signed_worker_admission_missing")
    claimed_context = admission.claimed_context
    admitted_context = bind_execution_admission(claimed_context, admission)
    try:
        verified_context = {
            **dict(verified.canonical_context),
            **validated_result_history(claimed_context),
        }
    except ValueError as exc:
        return _finalize_owned_execution(
            db=db,
            task_id=task_id,
            context=admitted_context,
            result=_rejected(f"reddog_signed_worker_history_rejected: {exc}"),
        )
    return _claim_and_execute(
        repo_root=repo_root,
        db=db,
        task_id=task_id,
        verified_context=bind_execution_admission(verified_context, admission),
        signed_worker_runner=signed_worker_runner,
        env=env,
    )


def _verify_and_admit(
    *,
    repo_root: Path,
    db: Any,
    task_id: str,
    context: Mapping[str, Any],
    required_skills: Sequence[str],
    source: str,
    discovered_by: str,
    env: Mapping[str, str],
) -> tuple[Any | None, Any | None, Mapping[str, Any] | None]:
    try:
        authority = _verify_context(
            repo_root=repo_root, task_id=task_id, context=context,
            required_skills=required_skills, source=source,
            discovered_by=discovered_by, env=env,
        )
    except (ImportError, TypeError, ValueError) as exc:
        quarantine_unverified_signed_worker_assignment(
            db=db, task_id=task_id,
            reason="signed_worker_agentdb_envelope_rejected",
        )
        rejection = _rejected(
            f"reddog_signed_worker_authority_rejected: {exc}"
        )
        rejection["finalization_owned"] = True
        return None, None, rejection
    admission = admit_signed_worker_execution_once(
        db=db, task_id=task_id, authority_context=authority
    )
    if admission is not None:
        return admission.verified_envelope, admission, None
    result = _rejected("reddog_signed_worker_execution_already_claimed")
    result["finalization_owned"] = True
    return None, None, result


def _claim_and_execute(
    *,
    repo_root: Path,
    db: Any,
    task_id: str,
    verified_context: Mapping[str, Any],
    signed_worker_runner: Any | None,
    env: Mapping[str, str],
) -> Any:
    try:
        with signed_worker_execution_heartbeat(
            db=db,
            task_id=task_id,
            context=verified_context,
        ) as heartbeat:
            effective_runner, binding_reject = _runner(
                repo_root=repo_root,
                signed_worker_runner=signed_worker_runner,
                env=env,
            )
            result = (
                dict(binding_reject)
                if binding_reject is not None
                else dict(_execute(
                    repo_root=repo_root,
                    task_id=task_id,
                    context=verified_context,
                    runner=effective_runner,
                ))
            )
        if not heartbeat.healthy:
            result = {
                **_rejected("reddog_signed_worker_execution_lease_renewal_failed"),
                "effect_commit_state": "INDETERMINATE",
            }
    except Exception as exc:
        logger.warning("[RUN_TASK] RedDog signed-worker dispatch error: %s", exc)
        result = _rejected(
            f"reddog_signed_worker_dispatch_error:{type(exc).__name__}"
        )
    return _finalize_owned_execution(
        db=db, task_id=task_id, context=verified_context, result=result
    )


def _finalize_owned_execution(
    *,
    db: Any,
    task_id: str,
    context: Mapping[str, Any],
    result: Mapping[str, Any],
) -> Mapping[str, Any]:
    final = dict(result)
    final["finalization_owned"] = True
    try:
        runner_payload, nested = _runner_result_payload(final)
        requeue = final.get("ok") is True and (
            nested.get("queue_chain_requeue_required") is True
        )
        receipt = _build_result_receipt(
            db=db,
            task_id=task_id,
            context=context,
            final=final,
            requeue=requeue,
        )
        result_context = append_signed_worker_result_history(context, receipt)
        assurance_completion = receipt.get("assurance_completion_request")
        assurance_completion = (
            dict(assurance_completion)
            if isinstance(assurance_completion, Mapping)
            else None
        )
        finalized = finalize_signed_worker_execution(
            db,
            task_id,
            context=context,
            accepted=final.get("ok") is True,
            result_context=result_context,
            target_status="pending" if requeue else None,
            retry_not_before=str(nested.get("retry_at") or "") or None,
            assurance_completion=assurance_completion,
        )
    except Exception:
        finalized = False
    if finalized:
        return final
    return {
        **_rejected("reddog_signed_worker_finalization_conflict"),
        "finalization_owned": True,
    }


def _runner_result_payload(
    result: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    raw = result.get("structured_result")
    runner = dict(raw) if isinstance(raw, Mapping) else {}
    nested = runner.get("runner_result")
    return runner, dict(nested) if isinstance(nested, Mapping) else {}


def _build_result_receipt(
    *,
    db: Any,
    task_id: str,
    context: Mapping[str, Any],
    final: Mapping[str, Any],
    requeue: bool,
) -> Mapping[str, Any]:
    claim = context.get("signed_worker_execution_claim")
    claim = dict(claim) if isinstance(claim, Mapping) else {}
    durable_completion = rehydrate_staged_assurance_completion(
        db.db,
        task_id=task_id,
        assigned_to=str(claim.get("assigned_to") or ""),
    )
    return build_signed_worker_task_result_receipt(
        base_context=context,
        claim_status=(
            DIRECT_REQUEUED
            if requeue
            else DIRECT_ACCEPT if final.get("ok") is True else DIRECT_REJECT
        ),
        result=final,
        assurance_completion=durable_completion,
    )


def _verify_context(
    *,
    repo_root: Path,
    task_id: str,
    context: Mapping[str, Any],
    required_skills: Sequence[str],
    source: str,
    discovered_by: str,
    env: Mapping[str, str],
) -> Mapping[str, Any]:
    from modules.communication.moltbot_bridge.src.reddog_signed_worker_agentdb_envelope import (
        SignedWorkerAgentDbEnvelopeError,
        build_worker_dispatch_authority_context_from_env,
    )

    if (
        discovered_by != SIGNED_SOURCE
        or SIGNED_SKILL not in required_skills
        or source != SIGNED_SOURCE
        or "signed_worker_agentdb_envelope" not in context
    ):
        raise SignedWorkerAgentDbEnvelopeError(
            "signed_worker_task_routing_binding_mismatch"
        )
    return build_worker_dispatch_authority_context_from_env(
        repo_root=repo_root, env=env
    )


def _runner(
    *,
    repo_root: Path,
    signed_worker_runner: Any | None,
    env: Mapping[str, str],
) -> tuple[Any | None, Mapping[str, Any] | None]:
    if signed_worker_runner is not None:
        return signed_worker_runner, None
    from modules.communication.moltbot_bridge.src.reddog_signed_worker_openclaw_queue_loop_runtime_binding import (
        build_reddog_signed_worker_queue_loop_runner_from_env,
    )

    binding = build_reddog_signed_worker_queue_loop_runner_from_env(
        repo_root=repo_root, env=env
    )
    if getattr(binding, "accepted", False) is True:
        return getattr(binding, "runner", None), None
    if getattr(binding, "requested", False) is True:
        return None, _rejected(json.dumps(binding.to_dict(), default=str)[:1000])
    return None, None


def _execute(
    *,
    repo_root: Path,
    task_id: str,
    context: Mapping[str, Any],
    runner: Any | None,
) -> Mapping[str, Any]:
    from modules.communication.moltbot_bridge.src.reddog_signed_worker_dispatch_task_executor import (
        execute_reddog_signed_worker_dispatch_task,
    )

    execution = execute_reddog_signed_worker_dispatch_task(
        task_context=context, task_id=task_id,
        repo_root=repo_root, runner=runner,
    )
    payload = execution.to_dict()
    return {
        "ok": bool(execution.accepted),
        "detail": json.dumps(payload, default=str)[:1000],
        "executor": "reddog:signed_worker_dispatch",
        "structured_result": payload,
    }


def _has_signed_marker(
    task_id: str,
    context: Mapping[str, Any],
    required_skills: Sequence[str],
    *,
    source: str,
    discovered_by: str,
) -> bool:
    return (
        task_id.startswith(SIGNED_WORKER_TASK_PREFIX)
        or discovered_by == SIGNED_SOURCE
        or SIGNED_SKILL in required_skills
        or source == SIGNED_SOURCE
        or "signed_worker_agentdb_envelope" in context
    )


def _rejected(detail: str) -> dict[str, Any]:
    return {
        "ok": False,
        "detail": detail,
        "executor": "reddog:signed_worker_dispatch",
    }


__all__ = ["SIGNED_SKILL", "SIGNED_SOURCE", "execute_signed_worker_from_agentdb"]
