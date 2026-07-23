# -*- coding: utf-8 -*-
"""Cohesive, behavior-preserving decision phases for ``route_foundup_job``."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Union

from .foundup_job_router import (
    _ACTION_BACKEND_MAP,
    RouteEnvelope,
    RouteReasonCode,
    RouteStatus,
    TargetBackend,
    _make_blocked_envelope,
    _sanitize_untrusted_policy_flags_dict,
)
from .foundup_scaffold_route_contract import (
    CreateScaffoldRequest,
    freeze_create_scaffold_request,
)


@dataclass(frozen=True)
class _RouteState:
    job_id: Any
    tenant_id: Any
    action: Any
    status: str


_StateOrEnvelope = Union[_RouteState, RouteEnvelope]
_PolicyOrEnvelope = Union[Dict[str, bool], RouteEnvelope]
_RequestOrEnvelope = Union[Optional[CreateScaffoldRequest], RouteEnvelope]


def _validate_identity_and_status(job: Any) -> _StateOrEnvelope:
    job_id = getattr(job, "job_id", None)
    if not job_id or not str(job_id).strip():
        return _make_blocked_envelope(
            job_id="",
            tenant_id=getattr(job, "tenant_id", "") or "",
            action=getattr(job, "requested_action", "") or "",
            reason_code=RouteReasonCode.BLOCKED_MISSING_JOB_ID,
            reason_human="Job ID is required for routing",
        )
    tenant_id = getattr(job, "tenant_id", None)
    if not tenant_id or not str(tenant_id).strip():
        return _make_blocked_envelope(
            job_id=job_id,
            tenant_id="",
            action=getattr(job, "requested_action", "") or "",
            reason_code=RouteReasonCode.BLOCKED_MISSING_TENANT_ID,
            reason_human="Tenant ID is required for routing",
        )
    action = getattr(job, "requested_action", None)
    if not action or not str(action).strip():
        return _make_blocked_envelope(
            job_id=job_id,
            tenant_id=tenant_id,
            action="",
            reason_code=RouteReasonCode.BLOCKED_MISSING_ACTION,
            reason_human="Requested action is required for routing",
        )
    job_status = getattr(job, "status", None)
    status = (
        job_status.value
        if hasattr(job_status, "value")
        else str(job_status or "")
    )
    try:
        from modules.communication.moltbot_bridge.src.foundup_job_contract import (
            is_terminal_status,
        )

        if job_status and is_terminal_status(job_status):
            return _make_blocked_envelope(
                job_id=job_id,
                tenant_id=tenant_id,
                action=action,
                reason_code=RouteReasonCode.BLOCKED_TERMINAL_STATUS,
                reason_human=f"Job is in terminal status: {status}",
                source_status=status,
                foundup_id=getattr(job, "foundup_id", None),
            )
    except ImportError:
        pass
    return _RouteState(job_id, tenant_id, action, status)


def _validate_policy(job: Any, state: _RouteState) -> _PolicyOrEnvelope:
    policy_flags = getattr(job, "policy_flags", None)
    policy_summary: Dict[str, bool] = {}
    dry_run_defaulted = True
    if policy_flags:
        if hasattr(policy_flags, "to_dict"):
            policy_summary = policy_flags.to_dict()
        elif isinstance(policy_flags, dict):
            policy_summary, dry_run_defaulted = (
                _sanitize_untrusted_policy_flags_dict(policy_flags)
            )
    is_live = (
        policy_summary.get("dry_run_mode") is False
        and not dry_run_defaulted
    )
    if is_live and policy_summary.get("security_gate_passed") is not True:
        return _make_blocked_envelope(
            job_id=state.job_id,
            tenant_id=state.tenant_id,
            action=state.action,
            reason_code=RouteReasonCode.BLOCKED_POLICY_GATE,
            reason_human="Live mode requires security gate passed (fail-closed)",
            source_status=state.status,
            foundup_id=getattr(job, "foundup_id", None),
            policy_summary=policy_summary,
        )
    return policy_summary


def _validate_create_request(
    job: Any,
    state: _RouteState,
    policy: Dict[str, bool],
) -> _RequestOrEnvelope:
    if state.action != "create_foundup":
        return None
    decision = freeze_create_scaffold_request(job, policy)
    if decision.ok and decision.request is not None:
        return decision.request
    return _make_blocked_envelope(
        job_id=state.job_id,
        tenant_id=state.tenant_id,
        action=state.action,
        reason_code=RouteReasonCode.BLOCKED_INVALID_CREATE_BINDING,
        reason_human=decision.error_human,
        source_status=state.status,
        foundup_id=getattr(job, "foundup_id", None),
        policy_summary=policy,
    )


def _route_to_backend(
    job: Any,
    state: _RouteState,
    policy: Dict[str, bool],
    request: Optional[CreateScaffoldRequest],
) -> RouteEnvelope:
    target = _ACTION_BACKEND_MAP.get(state.action)
    if target is None:
        return RouteEnvelope(
            job_id=state.job_id,
            tenant_id=state.tenant_id,
            target_backend=TargetBackend.NONE,
            requested_action=state.action,
            route_status=RouteStatus.UNSUPPORTED,
            reason_code=RouteReasonCode.UNSUPPORTED_ACTION,
            reason_human=f"Action '{state.action}' is not supported",
            policy_summary=policy,
            source_job_status=state.status,
            foundup_id=getattr(job, "foundup_id", None),
        )
    if state.action == "queue_foundup_job":
        return RouteEnvelope(
            job_id=state.job_id,
            tenant_id=state.tenant_id,
            target_backend=TargetBackend.OPENCLAW_QUEUE,
            requested_action=state.action,
            route_status=RouteStatus.QUEUED,
            reason_code=RouteReasonCode.OK_QUEUED,
            reason_human="Job queued for later processing",
            policy_summary=policy,
            source_job_status=state.status,
            foundup_id=getattr(job, "foundup_id", None),
        )
    return RouteEnvelope(
        job_id=state.job_id,
        tenant_id=state.tenant_id,
        target_backend=target,
        requested_action=state.action,
        route_status=RouteStatus.ROUTED,
        reason_code=RouteReasonCode.OK_ROUTED,
        reason_human=f"Job routed to {target.value}",
        policy_summary=policy,
        source_job_status=state.status,
        foundup_id=(
            request.foundup_id
            if request is not None
            else getattr(job, "foundup_id", None)
        ),
        creation_mode=request.creation_mode if request is not None else None,
        genesis_envelope_digest=(
            request.genesis_envelope_digest if request is not None else None
        ),
        scaffold_contract_digest=(
            request.scaffold_contract_digest if request is not None else None
        ),
        scaffold_request=request,
    )


def route_foundup_job_impl(job: Any) -> RouteEnvelope:
    """Run ordered route phases; the public wrapper owns fail-closed errors."""
    state = _validate_identity_and_status(job)
    if isinstance(state, RouteEnvelope):
        return state
    policy = _validate_policy(job, state)
    if isinstance(policy, RouteEnvelope):
        return policy
    request = _validate_create_request(job, state, policy)
    if isinstance(request, RouteEnvelope):
        return request
    return _route_to_backend(job, state, policy, request)
