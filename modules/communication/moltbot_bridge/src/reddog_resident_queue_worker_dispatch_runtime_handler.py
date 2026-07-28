"""Resident RedDog signed worker-dispatch runtime stage handler.

Slice: REDDOG_OPENCLAW_HERMES_0102_WORKER_DISPATCH_RUNTIME_PHASE1

This handler adapts the accepted `worker_dispatch_dryrun` chain result into the
runtime task publisher that writes pending AgentDB tasks. It does not start
workers, execute Hermes, create worktrees, run shell commands, mutate repository
files, create PRs, write PatternMemory, settle rewards, or re-index HoloIndex.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional

from modules.communication.moltbot_bridge.src.reddog_authoritative_work_state_refresh_runtime import (
    AuthoritativeWorkStateStore,
)

from modules.communication.moltbot_bridge.src.reddog_openclaw_hermes_0102_worker_dispatch_runtime import (
    SIGNED_AUTHORITY_WORKER_DISPATCH_RUNTIME_REJECT,
    SignedWorkerDispatchTaskWriter,
    publish_reddog_signed_worker_dispatch_runtime,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_chain_results_store import (
    ResidentQueueChainResultsStore,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_next_stage_dispatch import (
    ResidentQueueStageDispatchRequest,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_orchestration_plan import (
    NEXT_QUEUE_WORKER_DISPATCH_RUNTIME,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_worker_dispatch_dryrun_handler import (
    AUTHORITY_RUNTIME_STAGE_KEY,
    AUTHORITY_VERIFICATION_STAGE_KEY,
    WORKER_DISPATCH_DRYRUN_STAGE_KEY,
)
from modules.communication.moltbot_bridge.src.reddog_worker_dispatch_authority_binding import (
    WorkerDispatchAuthorityVerificationContext,
)


WORKER_DISPATCH_RUNTIME_STAGE_KEY = "worker_dispatch_runtime"

FAIL_DISPATCH_RUNTIME_STAGE_MISMATCH = "FAIL_DISPATCH_RUNTIME_STAGE_MISMATCH"
FAIL_DISPATCH_RUNTIME_NEXT_ACTION_MISMATCH = "FAIL_DISPATCH_RUNTIME_NEXT_ACTION_MISMATCH"
FAIL_WORKER_DISPATCH_DRYRUN_STAGE_MISSING = "FAIL_WORKER_DISPATCH_DRYRUN_STAGE_MISSING"
FAIL_AUTHORITY_RUNTIME_STAGE_MISSING = "FAIL_WORKER_DISPATCH_AUTHORITY_RUNTIME_STAGE_MISSING"
FAIL_AUTHORITY_VERIFICATION_STAGE_MISSING = (
    "FAIL_WORKER_DISPATCH_AUTHORITY_VERIFICATION_STAGE_MISSING"
)
FAIL_QUEUE_ITEM_MISSING = "FAIL_WORKER_DISPATCH_RUNTIME_QUEUE_ITEM_MISSING"
FAIL_WORKER_DISPATCH_WRITER_MISSING = "FAIL_WORKER_DISPATCH_RUNTIME_WRITER_MISSING"
FAIL_WORK_STATE_EFFECT_FENCE_MISSING = (
    "FAIL_WORKER_DISPATCH_RUNTIME_WORK_STATE_EFFECT_FENCE_MISSING"
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


def _queue_item(snapshot: Mapping[str, Any], queue_item_id: str | None) -> Mapping[str, Any]:
    items = snapshot.get("wre_queue_items")
    if not isinstance(items, list):
        return {}
    for item in items:
        candidate = _mapping(item)
        if str(candidate.get("queue_item_id") or "") == str(queue_item_id or ""):
            return candidate
    return {}


def _reject(*reasons: str) -> dict[str, Any]:
    return {
        "accepted": False,
        "decision": SIGNED_AUTHORITY_WORKER_DISPATCH_RUNTIME_REJECT,
        "receipt": None,
        "tasks": [],
        "rejection_reasons": list(dict.fromkeys(reason for reason in reasons if reason)),
        "no_worker_process_started": True,
        "no_worktree_created": True,
        "no_shell_command_executed": True,
        "no_hermes_execution_performed": True,
        "no_repo_mutation_performed": True,
        "no_holoindex_reindex_performed": True,
        "no_pr_created": True,
        "no_pattern_memory_write_performed": True,
        "no_reward_settlement_performed": True,
    }


@dataclass(frozen=True)
class ResidentQueueWorkerDispatchRuntimeStageHandler:
    """Callable handler for the resident queue `worker_dispatch_runtime` stage."""

    work_state_snapshot: Mapping[str, Any]
    chain_results_store: ResidentQueueChainResultsStore
    writer: Optional[SignedWorkerDispatchTaskWriter]
    authority_verification_context: WorkerDispatchAuthorityVerificationContext
    work_state_store: Optional[AuthoritativeWorkStateStore] = None

    def __call__(self, request: ResidentQueueStageDispatchRequest) -> Mapping[str, Any]:
        if request.stage_key != WORKER_DISPATCH_RUNTIME_STAGE_KEY:
            return _reject(
                FAIL_DISPATCH_RUNTIME_STAGE_MISMATCH,
                f"expected:{WORKER_DISPATCH_RUNTIME_STAGE_KEY}",
                f"actual:{request.stage_key}",
            )
        if request.next_action != NEXT_QUEUE_WORKER_DISPATCH_RUNTIME:
            return _reject(
                FAIL_DISPATCH_RUNTIME_NEXT_ACTION_MISMATCH,
                f"expected:{NEXT_QUEUE_WORKER_DISPATCH_RUNTIME}",
                f"actual:{request.next_action}",
            )
        if self.writer is None:
            return _reject(FAIL_WORKER_DISPATCH_WRITER_MISSING)
        if self.work_state_store is None:
            return _reject(FAIL_WORK_STATE_EFFECT_FENCE_MISSING)

        stage_results = _stage_results(_mapping(self.chain_results_store.load()))
        dryrun = _mapping(stage_results.get(WORKER_DISPATCH_DRYRUN_STAGE_KEY))
        if not dryrun:
            return _reject(FAIL_WORKER_DISPATCH_DRYRUN_STAGE_MISSING)
        authority_runtime = _mapping(stage_results.get(AUTHORITY_RUNTIME_STAGE_KEY))
        if not authority_runtime:
            return _reject(FAIL_AUTHORITY_RUNTIME_STAGE_MISSING)
        authority_verification = _mapping(
            stage_results.get(AUTHORITY_VERIFICATION_STAGE_KEY)
        )
        if not authority_verification:
            return _reject(FAIL_AUTHORITY_VERIFICATION_STAGE_MISSING)
        try:
            with self.work_state_store.locked_snapshot() as current_state:
                queue_item = _queue_item(_mapping(current_state), request.queue_item_id)
                if not queue_item:
                    return _reject(
                        FAIL_QUEUE_ITEM_MISSING,
                        f"queue_item_id:{request.queue_item_id}",
                    )
                return publish_reddog_signed_worker_dispatch_runtime(
                    worker_dispatch_dryrun_result=dryrun,
                    queue_authority_runtime_result=authority_runtime,
                    queue_authority_verification_result=authority_verification,
                    authority_verification_context=self.authority_verification_context,
                    work_state_snapshot=current_state,
                    queue_item_id=str(request.queue_item_id or ""),
                    writer=self.writer,
                ).to_dict()
        except Exception:
            return _reject(FAIL_QUEUE_ITEM_MISSING)


def build_reddog_resident_queue_worker_dispatch_runtime_stage_handler(
    *,
    work_state_snapshot: Mapping[str, Any],
    chain_results_store: ResidentQueueChainResultsStore,
    writer: SignedWorkerDispatchTaskWriter,
    authority_verification_context: WorkerDispatchAuthorityVerificationContext,
    work_state_store: Optional[AuthoritativeWorkStateStore] = None,
) -> ResidentQueueWorkerDispatchRuntimeStageHandler:
    """Build the injected signed worker-dispatch runtime handler."""

    return ResidentQueueWorkerDispatchRuntimeStageHandler(
        work_state_snapshot=work_state_snapshot,
        chain_results_store=chain_results_store,
        writer=writer,
        authority_verification_context=authority_verification_context,
        work_state_store=work_state_store,
    )


__all__ = [
    "FAIL_DISPATCH_RUNTIME_NEXT_ACTION_MISMATCH",
    "FAIL_DISPATCH_RUNTIME_STAGE_MISMATCH",
    "FAIL_AUTHORITY_RUNTIME_STAGE_MISSING",
    "FAIL_AUTHORITY_VERIFICATION_STAGE_MISSING",
    "FAIL_QUEUE_ITEM_MISSING",
    "FAIL_WORKER_DISPATCH_DRYRUN_STAGE_MISSING",
    "FAIL_WORKER_DISPATCH_WRITER_MISSING",
    "FAIL_WORK_STATE_EFFECT_FENCE_MISSING",
    "ResidentQueueWorkerDispatchRuntimeStageHandler",
    "WORKER_DISPATCH_RUNTIME_STAGE_KEY",
    "build_reddog_resident_queue_worker_dispatch_runtime_stage_handler",
]
