"""Resident RedDog authority-verification stage handler.

Slice: REDDOG_RESIDENT_QUEUE_AUTHORITY_VERIFICATION_HANDLER_PHASE1

This module adapts the existing queue authority-verification explicit invoke
guard to the resident queue next-stage dispatcher. It reads the already-
recorded `authority_runtime` stage result from the chain-results store and
invokes verification through injected verifier, resolver, nonce, snapshot, and
revocation boundaries.

It verifies signed authority as evidence for later gates. It does not open
valves, spawn workers, create worktrees, execute shell commands, enqueue
OpenClaw, dispatch Hermes, publish PRs, settle rewards, mutate repository
files, or re-index HoloIndex.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from modules.communication.moltbot_bridge.src.reddog_resident_queue_chain_results_store import (
    ResidentQueueChainResultsStore,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_next_stage_dispatch import (
    ResidentQueueStageDispatchRequest,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_orchestration_plan import (
    NEXT_QUEUE_AUTHORITY_VERIFICATION_INVOKE,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authority_verification_invoke import (
    QUEUE_AUTHORITY_VERIFICATION_INVOKE_REJECT,
    invoke_reddog_wre_queue_authority_verification,
)


AUTHORITY_RUNTIME_STAGE_KEY = "authority_runtime"
AUTHORITY_VERIFICATION_STAGE_KEY = "authority_verification"

FAIL_DISPATCH_STAGE_MISMATCH = "FAIL_DISPATCH_STAGE_MISMATCH"
FAIL_DISPATCH_NEXT_ACTION_MISMATCH = "FAIL_DISPATCH_NEXT_ACTION_MISMATCH"
FAIL_AUTHORITY_RUNTIME_STAGE_MISSING = "FAIL_AUTHORITY_RUNTIME_STAGE_MISSING"


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


def _reject(*reasons: str) -> dict[str, Any]:
    return {
        "decision": QUEUE_AUTHORITY_VERIFICATION_INVOKE_REJECT,
        "rejection_reasons": list(dict.fromkeys(reason for reason in reasons if reason)),
        "verification_result": None,
        "explicit_queue_authority_verification_requested": False,
        "no_signing_performed": True,
        "no_authority_issued": True,
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
class ResidentQueueAuthorityVerificationStageHandler:
    """Callable handler for the resident queue `authority_verification` stage."""

    chain_results_store: ResidentQueueChainResultsStore
    signature_verifier: Any
    principal_key_resolver: Any
    nonce_store: Any
    snapshot_resolver: Any
    revocation_oracle: Any
    now: int
    required_valve_state: str
    forbidden_operations: Sequence[str] = ()
    revoked_key_epochs: Sequence[str] = ()
    leeway_s: int = 60

    def __call__(self, request: ResidentQueueStageDispatchRequest) -> Mapping[str, Any]:
        if request.stage_key != AUTHORITY_VERIFICATION_STAGE_KEY:
            return _reject(
                FAIL_DISPATCH_STAGE_MISMATCH,
                f"expected:{AUTHORITY_VERIFICATION_STAGE_KEY}",
                f"actual:{request.stage_key}",
            )
        if request.next_action != NEXT_QUEUE_AUTHORITY_VERIFICATION_INVOKE:
            return _reject(
                FAIL_DISPATCH_NEXT_ACTION_MISMATCH,
                f"expected:{NEXT_QUEUE_AUTHORITY_VERIFICATION_INVOKE}",
                f"actual:{request.next_action}",
            )

        stage_results = _stage_results(_mapping(self.chain_results_store.load()))
        authority_runtime = _mapping(stage_results.get(AUTHORITY_RUNTIME_STAGE_KEY))
        if not authority_runtime:
            return _reject(FAIL_AUTHORITY_RUNTIME_STAGE_MISSING)

        return invoke_reddog_wre_queue_authority_verification(
            explicit_queue_authority_verification_requested=True,
            queue_authority_runtime_result=authority_runtime,
            signature_verifier=self.signature_verifier,
            principal_key_resolver=self.principal_key_resolver,
            nonce_store=self.nonce_store,
            snapshot_resolver=self.snapshot_resolver,
            revocation_oracle=self.revocation_oracle,
            now=self.now,
            required_valve_state=self.required_valve_state,
            forbidden_operations=self.forbidden_operations,
            revoked_key_epochs=self.revoked_key_epochs,
            leeway_s=self.leeway_s,
        ).to_dict()


def build_reddog_resident_queue_authority_verification_stage_handler(
    *,
    chain_results_store: ResidentQueueChainResultsStore,
    signature_verifier: Any,
    principal_key_resolver: Any,
    nonce_store: Any,
    snapshot_resolver: Any,
    revocation_oracle: Any,
    now: int,
    required_valve_state: str,
    forbidden_operations: Sequence[str] = (),
    revoked_key_epochs: Sequence[str] = (),
    leeway_s: int = 60,
) -> ResidentQueueAuthorityVerificationStageHandler:
    """Build the injected handler for the resident queue dispatcher."""

    return ResidentQueueAuthorityVerificationStageHandler(
        chain_results_store=chain_results_store,
        signature_verifier=signature_verifier,
        principal_key_resolver=principal_key_resolver,
        nonce_store=nonce_store,
        snapshot_resolver=snapshot_resolver,
        revocation_oracle=revocation_oracle,
        now=now,
        required_valve_state=required_valve_state,
        forbidden_operations=forbidden_operations,
        revoked_key_epochs=revoked_key_epochs,
        leeway_s=leeway_s,
    )


__all__ = [
    "AUTHORITY_RUNTIME_STAGE_KEY",
    "AUTHORITY_VERIFICATION_STAGE_KEY",
    "FAIL_AUTHORITY_RUNTIME_STAGE_MISSING",
    "FAIL_DISPATCH_NEXT_ACTION_MISMATCH",
    "FAIL_DISPATCH_STAGE_MISMATCH",
    "ResidentQueueAuthorityVerificationStageHandler",
    "build_reddog_resident_queue_authority_verification_stage_handler",
]
