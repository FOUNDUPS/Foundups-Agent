"""Resident RedDog authority-runtime stage handler.

Slice: REDDOG_RESIDENT_QUEUE_AUTHORITY_RUNTIME_HANDLER_PHASE1

This module adapts the existing queue authority-runtime explicit invoke guard
to the resident queue next-stage dispatcher. It reads the already-recorded
`authority_request` stage result from the chain-results store and invokes the
runtime guard with injected signer, resolver, snapshot, and authority-store
boundaries.

It may produce signed delegated-authority records through those injected
boundaries. It does not verify signatures for execution, open valves, spawn
workers, create worktrees, execute shell commands, enqueue OpenClaw, dispatch
Hermes, publish PRs, settle rewards, mutate repository files, or re-index
HoloIndex.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Optional

from modules.communication.moltbot_bridge.src.reddog_architect_fix_publication_effect_binding import (
    committed_publication_effect_binding,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_chain_results_store import (
    ResidentQueueChainResultsStore,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_next_stage_dispatch import (
    ResidentQueueStageDispatchRequest,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_orchestration_plan import (
    NEXT_QUEUE_AUTHORITY_RUNTIME_INVOKE,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authority_runtime_invoke import (
    QUEUE_AUTHORITY_RUNTIME_INVOKE_REJECT,
    invoke_reddog_wre_queue_authority_runtime,
)
from modules.communication.moltbot_bridge.src.reddog_queue_authority_admission import (
    _admit_current_queue_authority,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authority_request_integrity import (
    rehydrate_delegated_authority_request,
)


AUTHORITY_RUNTIME_STAGE_KEY = "authority_runtime"
AUTHORITY_REQUEST_STAGE_KEY = "authority_request"

FAIL_DISPATCH_STAGE_MISMATCH = "FAIL_DISPATCH_STAGE_MISMATCH"
FAIL_DISPATCH_NEXT_ACTION_MISMATCH = "FAIL_DISPATCH_NEXT_ACTION_MISMATCH"
FAIL_AUTHORITY_REQUEST_STAGE_MISSING = "FAIL_AUTHORITY_REQUEST_STAGE_MISSING"
FAIL_ARCHITECT_FIX_PUBLICATION_NOT_COMMITTED = (
    "FAIL_ARCHITECT_FIX_PUBLICATION_NOT_COMMITTED"
)


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
        "decision": QUEUE_AUTHORITY_RUNTIME_INVOKE_REJECT,
        "rejection_reasons": list(dict.fromkeys(reason for reason in reasons if reason)),
        "authority_result": None,
        "explicit_queue_authority_runtime_requested": False,
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


def _publication_binding_valid(
    state: Mapping[str, Any],
    profile: Mapping[str, Any],
    authority_request: Mapping[str, Any],
) -> bool:
    receipt = _mapping(authority_request.get("receipt"))
    payload = _mapping(authority_request.get("delegated_authority_request"))
    queue_item_id = str(receipt.get("queue_item_id") or "")
    queue_item = next(
        (
            item
            for item in state.get("wre_queue_items") or ()
            if isinstance(item, Mapping)
            and str(item.get("queue_item_id") or "") == queue_item_id
        ),
        {},
    )
    claim_id = str(_mapping(queue_item).get("claim_id") or "")
    try:
        expected = committed_publication_effect_binding(
            state,
            profile,
            queue_item_id=queue_item_id,
            claim_id=claim_id,
        )
    except (RuntimeError, ValueError):
        return False
    actual_id = str(
        payload.get("architect_fix_publication_receipt_id") or ""
    )
    actual_digest = str(
        payload.get("architect_fix_publication_binding_digest") or ""
    )
    if expected is None:
        return not actual_id and not actual_digest
    return (
        actual_id == expected["publication_id"]
        and actual_digest == expected["binding_digest"]
    )


def _authoritative_queue_item(
    state: Mapping[str, Any], authority_request: Mapping[str, Any]
) -> Mapping[str, Any]:
    receipt = _mapping(authority_request.get("receipt"))
    queue_item_id = str(receipt.get("queue_item_id") or "")
    return next(
        (
            item
            for item in state.get("wre_queue_items") or ()
            if isinstance(item, Mapping)
            and str(item.get("queue_item_id") or "") == queue_item_id
        ),
        {},
    )


def _queue_authority_admission(
    state: Mapping[str, Any], authority_request: Mapping[str, Any]
):
    payload = _mapping(authority_request.get("delegated_authority_request"))
    try:
        request = rehydrate_delegated_authority_request(payload)
    except (TypeError, ValueError):
        return None
    return _admit_current_queue_authority(
        request=request,
        authoritative_queue_item=_authoritative_queue_item(
            state, authority_request
        ),
    )


@dataclass(frozen=True)
class ResidentQueueAuthorityRuntimeStageHandler:
    """Callable handler for the resident queue `authority_runtime` stage."""

    chain_results_store: ResidentQueueChainResultsStore
    authority_store: Any
    signer: Any
    principal_resolver: Any
    snapshot_resolver: Any
    now: int
    leeway_s: int = 60
    work_state_snapshot: Mapping[str, Any] = field(default_factory=dict)
    authority_profile: Mapping[str, Any] = field(default_factory=dict)
    work_state_supplier: Optional[Callable[[], Mapping[str, Any]]] = None

    def __call__(self, request: ResidentQueueStageDispatchRequest) -> Mapping[str, Any]:
        if request.stage_key != AUTHORITY_RUNTIME_STAGE_KEY:
            return _reject(
                FAIL_DISPATCH_STAGE_MISMATCH,
                f"expected:{AUTHORITY_RUNTIME_STAGE_KEY}",
                f"actual:{request.stage_key}",
            )
        if request.next_action != NEXT_QUEUE_AUTHORITY_RUNTIME_INVOKE:
            return _reject(
                FAIL_DISPATCH_NEXT_ACTION_MISMATCH,
                f"expected:{NEXT_QUEUE_AUTHORITY_RUNTIME_INVOKE}",
                f"actual:{request.next_action}",
            )

        stage_results = _stage_results(_mapping(self.chain_results_store.load()))
        authority_request = _mapping(stage_results.get(AUTHORITY_REQUEST_STAGE_KEY))
        if not authority_request:
            return _reject(FAIL_AUTHORITY_REQUEST_STAGE_MISSING)
        try:
            current_state = (
                self.work_state_supplier()
                if self.work_state_supplier is not None
                else _mapping(self.work_state_snapshot)
            )
        except Exception:
            return _reject(FAIL_ARCHITECT_FIX_PUBLICATION_NOT_COMMITTED)
        if not _publication_binding_valid(
            current_state,
            _mapping(self.authority_profile),
            authority_request,
        ):
            return _reject(FAIL_ARCHITECT_FIX_PUBLICATION_NOT_COMMITTED)

        return invoke_reddog_wre_queue_authority_runtime(
            explicit_queue_authority_runtime_requested=True,
            queue_authority_request_dryrun=authority_request,
            queue_authority_admission=_queue_authority_admission(
                current_state,
                authority_request,
            ),
            store=self.authority_store,
            signer=self.signer,
            principal_resolver=self.principal_resolver,
            snapshot_resolver=self.snapshot_resolver,
            now=self.now,
            leeway_s=self.leeway_s,
        ).to_dict()


def build_reddog_resident_queue_authority_runtime_stage_handler(
    *,
    chain_results_store: ResidentQueueChainResultsStore,
    authority_store: Any,
    signer: Any,
    principal_resolver: Any,
    snapshot_resolver: Any,
    now: int,
    leeway_s: int = 60,
    work_state_snapshot: Mapping[str, Any] | None = None,
    authority_profile: Mapping[str, Any] | None = None,
    work_state_supplier: Optional[
        Callable[[], Mapping[str, Any]]
    ] = None,
) -> ResidentQueueAuthorityRuntimeStageHandler:
    """Build the injected handler for the resident queue dispatcher."""

    return ResidentQueueAuthorityRuntimeStageHandler(
        chain_results_store=chain_results_store,
        authority_store=authority_store,
        signer=signer,
        principal_resolver=principal_resolver,
        snapshot_resolver=snapshot_resolver,
        now=now,
        leeway_s=leeway_s,
        work_state_snapshot=work_state_snapshot or {},
        authority_profile=authority_profile or {},
        work_state_supplier=work_state_supplier,
    )


__all__ = [
    "AUTHORITY_REQUEST_STAGE_KEY",
    "AUTHORITY_RUNTIME_STAGE_KEY",
    "FAIL_AUTHORITY_REQUEST_STAGE_MISSING",
    "FAIL_ARCHITECT_FIX_PUBLICATION_NOT_COMMITTED",
    "FAIL_DISPATCH_NEXT_ACTION_MISMATCH",
    "FAIL_DISPATCH_STAGE_MISMATCH",
    "ResidentQueueAuthorityRuntimeStageHandler",
    "build_reddog_resident_queue_authority_runtime_stage_handler",
]
