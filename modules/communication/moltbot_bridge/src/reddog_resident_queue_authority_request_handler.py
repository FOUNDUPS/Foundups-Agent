"""Resident RedDog authority-request stage handler.

Slice: REDDOG_RESIDENT_QUEUE_AUTHORITY_REQUEST_HANDLER_PHASE1

This module adapts the existing WRE queue authority-request dry-run planner to
the resident queue next-stage dispatcher. It is a concrete handler for the
first post-consumer queue stage only. It does not sign, verify signatures, open
valves, spawn workers, create worktrees, execute shell commands, enqueue
OpenClaw, dispatch Hermes, publish PRs, settle rewards, mutate the repository,
or re-index HoloIndex.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional, Protocol

from modules.communication.moltbot_bridge.src.reddog_resident_queue_next_stage_dispatch import (
    ResidentQueueStageDispatchRequest,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_orchestration_plan import (
    NEXT_QUEUE_AUTHORITY_REQUEST_DRYRUN,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authority_request_dryrun import (
    QUEUE_AUTHORITY_REQUEST_DRYRUN_REJECT,
    plan_reddog_wre_queue_authority_request_dry_run,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_consumer_dryrun import (
    WRE_QUEUE_CONSUMER_DRYRUN_READY,
    plan_reddog_wre_queue_consumer_dry_run,
)


FAIL_DISPATCH_STAGE_MISMATCH = "FAIL_DISPATCH_STAGE_MISMATCH"
FAIL_DISPATCH_NEXT_ACTION_MISMATCH = "FAIL_DISPATCH_NEXT_ACTION_MISMATCH"
FAIL_QUEUE_SELECTION_MISMATCH = "FAIL_QUEUE_SELECTION_MISMATCH"
FAIL_WORK_ORDER_MISSING = "FAIL_WORK_ORDER_MISSING"

AUTHORITY_REQUEST_STAGE_KEY = "authority_request"


class ResidentQueueAuthorityRequestWorkOrderResolver(Protocol):
    def resolve(
        self,
        *,
        work_order_id: str,
        queue_item_id: Optional[str],
        selected_slice: Optional[str],
    ) -> Mapping[str, Any]: ...


def _mapping(value: Any) -> Mapping[str, Any]:
    if hasattr(value, "to_dict"):
        candidate = value.to_dict()
        return candidate if isinstance(candidate, Mapping) else {}
    if isinstance(value, Mapping):
        return value
    return {}


def _reject(*reasons: str) -> Dict[str, Any]:
    clean = list(dict.fromkeys(reason for reason in reasons if reason))
    return {
        "accepted": False,
        "status": QUEUE_AUTHORITY_REQUEST_DRYRUN_REJECT,
        "rejection_reasons": clean,
        "receipt": None,
        "delegated_authority_request": None,
        "execution_ready": False,
        "signer_invoked": False,
        "no_signing_performed": True,
        "no_signer_state_mutation_performed": True,
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
class ResidentQueueAuthorityRequestStageHandler:
    """Callable handler for the resident queue `authority_request` stage."""

    work_state_snapshot: Mapping[str, Any]
    authority_profile: Mapping[str, Any]
    work_order_resolver: ResidentQueueAuthorityRequestWorkOrderResolver
    now_iso: str

    def __call__(self, request: ResidentQueueStageDispatchRequest) -> Mapping[str, Any]:
        if request.stage_key != AUTHORITY_REQUEST_STAGE_KEY:
            return _reject(
                FAIL_DISPATCH_STAGE_MISMATCH,
                f"expected:{AUTHORITY_REQUEST_STAGE_KEY}",
                f"actual:{request.stage_key}",
            )
        if request.next_action != NEXT_QUEUE_AUTHORITY_REQUEST_DRYRUN:
            return _reject(
                FAIL_DISPATCH_NEXT_ACTION_MISMATCH,
                f"expected:{NEXT_QUEUE_AUTHORITY_REQUEST_DRYRUN}",
                f"actual:{request.next_action}",
            )

        queue_consumer = plan_reddog_wre_queue_consumer_dry_run(
            self.work_state_snapshot,
            now_iso=self.now_iso,
            requested_queue_item_id=request.queue_item_id,
        ).to_dict()
        if (
            queue_consumer.get("accepted") is not True
            or queue_consumer.get("status") != WRE_QUEUE_CONSUMER_DRYRUN_READY
            or str(queue_consumer.get("selected_queue_item_id") or "") != str(request.queue_item_id or "")
            or str(queue_consumer.get("selected_slice") or "") != str(request.selected_slice or "")
        ):
            reasons = [
                FAIL_QUEUE_SELECTION_MISMATCH,
                *[str(reason) for reason in queue_consumer.get("rejection_reasons") or ()],
            ]
            return _reject(*reasons)

        queue_item_id = str(request.queue_item_id or "")
        work_order_id = str(self.authority_profile.get("work_order_id") or "") or (
            "wre-queue-" + hashlib.sha256(queue_item_id.encode("utf-8")).hexdigest()[:16]
        )
        work_order = _mapping(
            self.work_order_resolver.resolve(
                work_order_id=work_order_id,
                queue_item_id=request.queue_item_id,
                selected_slice=request.selected_slice,
            )
        )
        if not work_order:
            return _reject(FAIL_WORK_ORDER_MISSING, f"work_order_id:{work_order_id}")

        result = plan_reddog_wre_queue_authority_request_dry_run(
            queue_consumer_result=queue_consumer,
            authority_profile=_mapping(self.authority_profile),
            work_order=work_order,
        )
        return result.to_dict()


def build_reddog_resident_queue_authority_request_stage_handler(
    *,
    work_state_snapshot: Mapping[str, Any],
    authority_profile: Mapping[str, Any],
    work_order_resolver: ResidentQueueAuthorityRequestWorkOrderResolver,
    now_iso: str,
) -> ResidentQueueAuthorityRequestStageHandler:
    """Build the injected handler for the resident queue dispatcher."""

    return ResidentQueueAuthorityRequestStageHandler(
        work_state_snapshot=work_state_snapshot,
        authority_profile=authority_profile,
        work_order_resolver=work_order_resolver,
        now_iso=now_iso,
    )


__all__ = [
    "AUTHORITY_REQUEST_STAGE_KEY",
    "FAIL_DISPATCH_NEXT_ACTION_MISMATCH",
    "FAIL_DISPATCH_STAGE_MISMATCH",
    "FAIL_QUEUE_SELECTION_MISMATCH",
    "FAIL_WORK_ORDER_MISSING",
    "ResidentQueueAuthorityRequestStageHandler",
    "ResidentQueueAuthorityRequestWorkOrderResolver",
    "build_reddog_resident_queue_authority_request_stage_handler",
]
