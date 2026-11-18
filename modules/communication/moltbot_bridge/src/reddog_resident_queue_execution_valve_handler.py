"""Resident RedDog execution-valve stage handler.

Slice: REDDOG_RESIDENT_QUEUE_EXECUTION_VALVE_HANDLER_PHASE1

This module adapts the existing queue-authorized execution-valve explicit
invoke guard to the resident queue next-stage dispatcher. It reads the recorded
`work_order_invocation` and `executor_plan` stage results from the chain-results
store, resolves the bound work order through an injected resolver, and evaluates
the existing execution valve with an injected environment.

It emits only a valve decision. It does not create worktrees, spawn workers,
execute shell commands, enqueue OpenClaw, dispatch Hermes, publish PRs, settle
rewards, mutate repository files, or re-index HoloIndex.
"""

from __future__ import annotations

from dataclasses import dataclass
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Mapping, Optional, Protocol

from modules.communication.moltbot_bridge.src.reddog_resident_queue_chain_results_store import (
    ResidentQueueChainResultsStore,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_next_stage_dispatch import (
    ResidentQueueStageDispatchRequest,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_orchestration_plan import (
    NEXT_QUEUE_EXECUTION_VALVE_INVOKE,
)
from modules.communication.moltbot_bridge.src.reddog_wre_execution_valve import (
    INTAKE_FOUNDUP_JOB,
    VALVE_OPEN_WORKTREE_CREATE,
    GovernedExecutionValveEnvironment,
)
from modules.communication.moltbot_bridge.src.reddog_execution_valve_use_time_authority import (
    GovernedValveUseTimeAuthorityResolver,
)
from modules.communication.moltbot_bridge.src.reddog_worktree_admission_capability import (
    InMemoryWorktreeAdmissionRegistry,
)
from modules.communication.moltbot_bridge.src.reddog_external_signer_authoritative_use_lease import (
    ExternalSignerAuthoritativeUseLeaseIssuer,
)
from modules.communication.moltbot_bridge.src.reddog_authoritative_use_lease_contract import digest_mapping
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_execution_valve_invoke import (
    QUEUE_AUTHORIZED_EXECUTION_VALVE_INVOKE_ACCEPT,
    QUEUE_AUTHORIZED_EXECUTION_VALVE_INVOKE_REJECT,
    invoke_reddog_wre_queue_authorized_execution_valve,
)


EXECUTION_VALVE_STAGE_KEY = "execution_valve"
EXECUTOR_PLAN_STAGE_KEY = "executor_plan"
WORK_ORDER_INVOCATION_STAGE_KEY = "work_order_invocation"

FAIL_DISPATCH_STAGE_MISMATCH = "FAIL_DISPATCH_STAGE_MISMATCH"
FAIL_DISPATCH_NEXT_ACTION_MISMATCH = "FAIL_DISPATCH_NEXT_ACTION_MISMATCH"
FAIL_WORK_ORDER_INVOCATION_STAGE_MISSING = "FAIL_WORK_ORDER_INVOCATION_STAGE_MISSING"
FAIL_EXECUTOR_PLAN_STAGE_MISSING = "FAIL_EXECUTOR_PLAN_STAGE_MISSING"
FAIL_WORK_ORDER_ID_MISSING = "FAIL_WORK_ORDER_ID_MISSING"
FAIL_WORK_ORDER_MISSING = "FAIL_WORK_ORDER_MISSING"
FAIL_WORKTREE_ADMISSION_NOT_ISSUED = "FAIL_WORKTREE_ADMISSION_NOT_ISSUED"
FAIL_GOVERNED_EXECUTION_VALVE_ENVIRONMENT_REQUIRED = (
    "FAIL_GOVERNED_EXECUTION_VALVE_ENVIRONMENT_REQUIRED"
)


class ResidentQueueExecutionValveWorkOrderResolver(Protocol):
    """Injected resolver for the work order bound to queue invocation."""

    def resolve(
        self,
        *,
        work_order_id: str,
        queue_item_id: Optional[str],
        selected_slice: Optional[str],
    ) -> Mapping[str, Any]:
        """Return the work order mapping for an accepted invocation result."""


def _mapping(value: Any) -> Mapping[str, Any]:
    if hasattr(value, "to_dict"):
        candidate = value.to_dict()
        return candidate if isinstance(candidate, Mapping) else {}
    if isinstance(value, Mapping):
        return value
    return {}


def _stage_results(state: Mapping[str, Any]) -> Mapping[str, Mapping[str, Any]]:
    raw = state.get("stage_results") if state.get("schema_version") == "reddog_resident_queue_chain_results.v1" else state
    if not isinstance(raw, Mapping):
        return {}
    return {str(key): value for key, value in raw.items() if isinstance(value, Mapping)}


def _work_order_id_from_invocation(work_order_invocation: Mapping[str, Any]) -> str:
    invocation = _mapping(work_order_invocation.get("invocation_result"))
    return str(invocation.get("work_order_id") or "").strip()


def _reject(*reasons: str) -> dict[str, Any]:
    return {
        "decision": QUEUE_AUTHORIZED_EXECUTION_VALVE_INVOKE_REJECT,
        "rejection_reasons": list(dict.fromkeys(reason for reason in reasons if reason)),
        "valve_decision": None,
        "explicit_queue_authorized_execution_valve_requested": False,
        "no_worker_spawn_performed": True,
        "no_worktree_created": True,
        "no_shell_command_executed": True,
        "no_openclaw_enqueue_performed": True,
        "no_hermes_dispatch_performed": True,
        "no_repo_mutation_performed": True,
        "no_holoindex_reindex_performed": True,
        "no_pr_created": True,
        "no_reward_settlement_performed": True,
    }


@dataclass(frozen=True)
class ResidentQueueExecutionValveStageHandler:
    """Callable handler for the resident queue `execution_valve` stage."""

    chain_results_store: ResidentQueueChainResultsStore
    work_order_resolver: ResidentQueueExecutionValveWorkOrderResolver
    valve_environment: GovernedExecutionValveEnvironment
    governed_use_time_authority_resolver: Optional[GovernedValveUseTimeAuthorityResolver] = None
    worktree_admission_registry: Optional[InMemoryWorktreeAdmissionRegistry] = None
    now: Optional[datetime] = None
    intake_target: str = INTAKE_FOUNDUP_JOB
    expected_valve_state: str = VALVE_OPEN_WORKTREE_CREATE
    worktree_lease_issuer: Optional[ExternalSignerAuthoritativeUseLeaseIssuer] = None

    def __call__(self, request: ResidentQueueStageDispatchRequest) -> Mapping[str, Any]:
        if request.stage_key != EXECUTION_VALVE_STAGE_KEY:
            return _reject(
                FAIL_DISPATCH_STAGE_MISMATCH,
                f"expected:{EXECUTION_VALVE_STAGE_KEY}",
                f"actual:{request.stage_key}",
            )
        if request.next_action != NEXT_QUEUE_EXECUTION_VALVE_INVOKE:
            return _reject(
                FAIL_DISPATCH_NEXT_ACTION_MISMATCH,
                f"expected:{NEXT_QUEUE_EXECUTION_VALVE_INVOKE}",
                f"actual:{request.next_action}",
            )
        if not isinstance(self.valve_environment, GovernedExecutionValveEnvironment):
            return _reject(FAIL_GOVERNED_EXECUTION_VALVE_ENVIRONMENT_REQUIRED)

        chain_state = deepcopy(_mapping(self.chain_results_store.load()))
        stage_results = _stage_results(chain_state)
        work_order_invocation = _mapping(stage_results.get(WORK_ORDER_INVOCATION_STAGE_KEY))
        if not work_order_invocation:
            return _reject(FAIL_WORK_ORDER_INVOCATION_STAGE_MISSING)
        executor_plan = _mapping(stage_results.get(EXECUTOR_PLAN_STAGE_KEY))
        if not executor_plan:
            return _reject(FAIL_EXECUTOR_PLAN_STAGE_MISSING)

        work_order_id = _work_order_id_from_invocation(work_order_invocation)
        if not work_order_id:
            return _reject(FAIL_WORK_ORDER_ID_MISSING)
        work_order = _mapping(
            self.work_order_resolver.resolve(
                work_order_id=work_order_id,
                queue_item_id=request.queue_item_id,
                selected_slice=request.selected_slice,
            )
        )
        if not work_order:
            return _reject(FAIL_WORK_ORDER_MISSING, f"work_order_id:{work_order_id}")

        if self.governed_use_time_authority_resolver is None:
            return _reject("FAIL_GOVERNED_USE_TIME_AUTHORITY_RESOLVER_MISSING")
        use_time_resolution = self.governed_use_time_authority_resolver.resolve(
            chain_state=chain_state,
            work_order=work_order,
            queue_item_id=request.queue_item_id,
            selected_slice=request.selected_slice,
        )

        result = self._evaluate(chain_state, work_order, use_time_resolution, self.now)
        if result.decision == QUEUE_AUTHORIZED_EXECUTION_VALVE_INVOKE_ACCEPT:
            lease = use_time_resolution.authoritative_use_lease
            if self.worktree_lease_issuer is not None:
                lease = self._issue_checked_lease(
                    request, chain_state, work_order, executor_plan, result, use_time_resolution)
            issued = (
                self.worktree_admission_registry is not None
                and result.valve_decision is not None
                and self.worktree_admission_registry.issue(
                    queue_item_id=request.queue_item_id,
                    selected_slice=request.selected_slice,
                    work_order=work_order,
                    executor_plan_result=executor_plan,
                    valve_decision=result.valve_decision.to_dict(),
                    signed_authority_reverified=use_time_resolution.signed_authority_reverified,
                    authoritative_use_lease=lease,
                )
            )
            if not issued:
                return _reject(FAIL_WORKTREE_ADMISSION_NOT_ISSUED)
        return result.to_dict()

    def _evaluate(self, chain, order, resolution, now):
        stages = _stage_results(chain)
        authority = _mapping(_mapping(stages.get("authority_runtime")).get("authority_result"))
        return invoke_reddog_wre_queue_authorized_execution_valve(
            explicit_queue_authorized_execution_valve_requested=True,
            queue_work_order_invocation_result=_mapping(stages.get(WORK_ORDER_INVOCATION_STAGE_KEY)),
            queue_executor_plan_result=_mapping(stages.get(EXECUTOR_PLAN_STAGE_KEY)),
            work_order=order, signed_work_authority=_mapping(authority.get("work_authority")),
            verified_work_authority_digest=_mapping(stages.get("authority_verification")).get("verified_work_authority_digest"),
            valve_environment=self.valve_environment, governed_use_time_resolution=resolution,
            now=now, intake_target=self.intake_target, expected_valve_state=self.expected_valve_state)

    def _issue_checked_lease(self, request, chain, order, plan, result, resolution):
        """Issue only after acceptance; resample inputs before releasing admission."""
        try:
            if (type(self.worktree_lease_issuer) is not ExternalSignerAuthoritativeUseLeaseIssuer
                    or self.worktree_admission_registry is None
                    or result.valve_decision is None
                    or resolution.signed_authority_reverified is not True
                    or resolution.rejection_reasons):
                return None
            before_chain, before_order = digest_mapping(chain), digest_mapping(order)
            before_resolution = _resolution_digest(resolution)
            authority = _mapping(_mapping(_stage_results(chain).get("authority_runtime")).get("authority_result"))
            lease = self.worktree_lease_issuer.issue_for_worktree(
                queue_item_id=request.queue_item_id, selected_slice=request.selected_slice,
                work_order=order, executor_plan_result=plan,
                valve_decision=result.valve_decision.to_dict(),
                signed_work_authority=_mapping(authority.get("work_authority")),
                identity=_mapping(authority.get("identity")),
                expected_bindings=resolution.expected_bindings,
            )
            if lease is None:
                return None
            fresh_chain = _mapping(self.chain_results_store.load())
            fresh_order = _mapping(self.work_order_resolver.resolve(
                work_order_id=str(order.get("work_order_id") or ""),
                queue_item_id=request.queue_item_id, selected_slice=request.selected_slice))
            fresh = self.governed_use_time_authority_resolver.resolve(
                chain_state=fresh_chain, work_order=fresh_order,
                queue_item_id=request.queue_item_id, selected_slice=request.selected_slice)
            if (digest_mapping(fresh_chain) != before_chain or digest_mapping(fresh_order) != before_order
                    or digest_mapping(order) != before_order
                    or _resolution_digest(fresh) != before_resolution):
                return None
            fresh_now = self.governed_use_time_authority_resolver.trusted_now_epoch()
            if type(fresh_now) is not int or fresh_now < 0:
                return None
            rechecked = self._evaluate(fresh_chain, fresh_order, fresh,
                datetime.fromtimestamp(fresh_now, timezone.utc))
            if (rechecked.decision != QUEUE_AUTHORIZED_EXECUTION_VALVE_INVOKE_ACCEPT
                    or digest_mapping(rechecked.to_dict()) != digest_mapping(result.to_dict())):
                return None
            return lease
        except Exception:
            return None


def _resolution_digest(resolution):
    return digest_mapping(dict(
        environment=resolution.environment.to_dict(), expected_bindings=resolution.expected_bindings,
        permission_expires_at=resolution.permission_expires_at,
        signed_authority_reverified=resolution.signed_authority_reverified,
        rejection_reasons=list(resolution.rejection_reasons),
        signer_generation_binding_receipt_id=resolution.signer_generation_binding_receipt_id))


def build_reddog_resident_queue_execution_valve_stage_handler(
    *,
    chain_results_store: ResidentQueueChainResultsStore,
    work_order_resolver: ResidentQueueExecutionValveWorkOrderResolver,
    valve_environment: GovernedExecutionValveEnvironment,
    governed_use_time_authority_resolver: Optional[GovernedValveUseTimeAuthorityResolver] = None,
    worktree_admission_registry: Optional[InMemoryWorktreeAdmissionRegistry] = None,
    now: Optional[datetime] = None,
    intake_target: str = INTAKE_FOUNDUP_JOB,
    expected_valve_state: str = VALVE_OPEN_WORKTREE_CREATE,
    worktree_lease_issuer: Optional[ExternalSignerAuthoritativeUseLeaseIssuer] = None,
) -> ResidentQueueExecutionValveStageHandler:
    """Build the injected execution-valve handler for the dispatcher."""

    return ResidentQueueExecutionValveStageHandler(
        chain_results_store=chain_results_store,
        work_order_resolver=work_order_resolver,
        valve_environment=valve_environment,
        governed_use_time_authority_resolver=governed_use_time_authority_resolver,
        worktree_admission_registry=worktree_admission_registry,
        now=now,
        intake_target=intake_target,
        expected_valve_state=expected_valve_state,
        worktree_lease_issuer=worktree_lease_issuer,
    )


__all__ = [
    "EXECUTION_VALVE_STAGE_KEY",
    "EXECUTOR_PLAN_STAGE_KEY",
    "FAIL_DISPATCH_NEXT_ACTION_MISMATCH",
    "FAIL_DISPATCH_STAGE_MISMATCH",
    "FAIL_EXECUTOR_PLAN_STAGE_MISSING",
    "FAIL_GOVERNED_EXECUTION_VALVE_ENVIRONMENT_REQUIRED",
    "FAIL_WORK_ORDER_ID_MISSING",
    "FAIL_WORK_ORDER_INVOCATION_STAGE_MISSING",
    "FAIL_WORK_ORDER_MISSING",
    "FAIL_WORKTREE_ADMISSION_NOT_ISSUED",
    "ResidentQueueExecutionValveStageHandler",
    "ResidentQueueExecutionValveWorkOrderResolver",
    "WORK_ORDER_INVOCATION_STAGE_KEY",
    "build_reddog_resident_queue_execution_valve_stage_handler",
]
