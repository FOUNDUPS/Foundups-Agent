"""Resident RedDog slice-verifier stage handler.

Slice: REDDOG_RESIDENT_QUEUE_SLICE_VERIFIER_HANDLER_PHASE1

This module adapts the existing queue-authorized autonomous slice verifier
explicit invoke guard to the resident queue next-stage dispatcher. It reads the
recorded `bounded_worker_pilot` stage result from the chain-results store and
invokes the existing verifier guard with injected machine-derived verifier
evidence.

It verifies evidence only. It does not run commands, create or update PRs,
merge, enqueue OpenClaw, dispatch Hermes, write PatternMemory, settle rewards,
or re-index HoloIndex.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.reddog_resident_queue_chain_results_store import (
    ResidentQueueChainResultsStore,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_next_stage_dispatch import (
    ResidentQueueStageDispatchRequest,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_orchestration_plan import (
    NEXT_QUEUE_SLICE_VERIFIER_INVOKE,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_slice_verifier_invoke import (
    QUEUE_AUTHORIZED_SLICE_VERIFIER_INVOKE_REJECT,
    invoke_reddog_wre_queue_authorized_slice_verifier,
)
from modules.infrastructure.wre_core.src.wre_independent_evidence_producer_runtime import (
    produce_independent_slice_evidence,
)


SLICE_VERIFIER_STAGE_KEY = "slice_verifier"
BOUNDED_WORKER_PILOT_STAGE_KEY = "bounded_worker_pilot"

FAIL_DISPATCH_STAGE_MISMATCH = "FAIL_DISPATCH_STAGE_MISMATCH"
FAIL_DISPATCH_NEXT_ACTION_MISMATCH = "FAIL_DISPATCH_NEXT_ACTION_MISMATCH"
FAIL_BOUNDED_WORKER_PILOT_STAGE_MISSING = "FAIL_BOUNDED_WORKER_PILOT_STAGE_MISSING"
FAIL_VERIFIER_REQUEST_MISSING = "FAIL_VERIFIER_REQUEST_MISSING"
FAIL_EVIDENCE_COMMAND_RUNNER_MISSING = "FAIL_EVIDENCE_COMMAND_RUNNER_MISSING"
FAIL_EVIDENCE_PRODUCER_REJECTED = "FAIL_EVIDENCE_PRODUCER_REJECTED"


def _mapping(value: Any) -> Mapping[str, Any]:
    if hasattr(value, "to_dict"):
        candidate = value.to_dict()
        return candidate if isinstance(candidate, Mapping) else {}
    if isinstance(value, Mapping):
        return value
    return {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _stage_results(state: Mapping[str, Any]) -> Mapping[str, Mapping[str, Any]]:
    raw = state.get("stage_results") if state.get("schema_version") == "reddog_resident_queue_chain_results.v1" else state
    if not isinstance(raw, Mapping):
        return {}
    return {str(key): value for key, value in raw.items() if isinstance(value, Mapping)}


def _reject(*reasons: str) -> dict[str, Any]:
    return {
        "decision": QUEUE_AUTHORIZED_SLICE_VERIFIER_INVOKE_REJECT,
        "rejection_reasons": list(dict.fromkeys(reason for reason in reasons if reason)),
        "verifier_result": None,
        "explicit_queue_authorized_slice_verifier_requested": False,
        "no_command_execution_performed": True,
        "no_github_call_performed": True,
        "no_pr_publish_performed": True,
        "no_merge_performed": True,
        "no_pattern_memory_write_performed": True,
        "no_reward_settlement_performed": True,
        "no_holoindex_reindex_performed": True,
    }


@dataclass(frozen=True)
class ResidentQueueSliceVerifierStageHandler:
    """Callable handler for the resident queue `slice_verifier` stage."""

    chain_results_store: ResidentQueueChainResultsStore
    verifier_request: Mapping[str, Any] | None = None
    evidence_producer_request: Mapping[str, Any] | None = None
    evidence_command_runner: Any = None

    def __call__(self, request: ResidentQueueStageDispatchRequest) -> Mapping[str, Any]:
        if request.stage_key != SLICE_VERIFIER_STAGE_KEY:
            return _reject(
                FAIL_DISPATCH_STAGE_MISMATCH,
                f"expected:{SLICE_VERIFIER_STAGE_KEY}",
                f"actual:{request.stage_key}",
            )
        if request.next_action != NEXT_QUEUE_SLICE_VERIFIER_INVOKE:
            return _reject(
                FAIL_DISPATCH_NEXT_ACTION_MISMATCH,
                f"expected:{NEXT_QUEUE_SLICE_VERIFIER_INVOKE}",
                f"actual:{request.next_action}",
            )

        stage_results = _stage_results(_mapping(self.chain_results_store.load()))
        bounded_worker_pilot = _mapping(stage_results.get(BOUNDED_WORKER_PILOT_STAGE_KEY))
        if not bounded_worker_pilot:
            return _reject(FAIL_BOUNDED_WORKER_PILOT_STAGE_MISSING)

        verifier_request = _mapping(self.verifier_request)
        evidence_producer_result: Mapping[str, Any] | None = None
        if not verifier_request:
            evidence_producer_request = _mapping(self.evidence_producer_request)
            if not evidence_producer_request:
                return _reject(FAIL_VERIFIER_REQUEST_MISSING)
            if self.evidence_command_runner is None:
                return _reject(FAIL_EVIDENCE_COMMAND_RUNNER_MISSING)
            produced = produce_independent_slice_evidence(
                evidence_producer_request,
                runner=self.evidence_command_runner,
            )
            evidence_producer_result = produced.to_dict()
            if produced.accepted is not True:
                rejected = _reject(FAIL_EVIDENCE_PRODUCER_REJECTED, *produced.rejection_reasons)
                rejected["evidence_producer_result"] = evidence_producer_result
                rejected["bounded_evidence_command_execution_performed"] = bool(produced.command_results)
                rejected["no_shell_command_executed"] = True
                return rejected
            verifier_request = _verifier_request_from_evidence(
                request=evidence_producer_request,
                diff_evidence=produced.diff_evidence,
                test_evidence=produced.test_evidence,
            )

        result = invoke_reddog_wre_queue_authorized_slice_verifier(
            explicit_queue_authorized_slice_verifier_requested=True,
            queue_bounded_worker_pilot_result=bounded_worker_pilot,
            verifier_request=verifier_request,
        ).to_dict()
        if evidence_producer_result is not None:
            result["evidence_producer_result"] = evidence_producer_result
            command_results = evidence_producer_result.get("command_results")
            result["bounded_evidence_command_execution_performed"] = bool(command_results)
            result["no_command_execution_performed"] = False
            result["no_shell_command_executed"] = True
        return result


def _verifier_request_from_evidence(
    *,
    request: Mapping[str, Any],
    diff_evidence: Mapping[str, Any],
    test_evidence: Mapping[str, Any],
) -> dict[str, Any]:
    verifier_request = {
        "work_order_id": str(request.get("work_order_id") or ""),
        "slice_name": str(request.get("slice_name") or ""),
        "worker_id": str(request.get("worker_id") or ""),
        "verifier_id": str(request.get("verifier_id") or ""),
        "base_sha": str(request.get("base_sha") or ""),
        "head_sha": str(request.get("head_sha") or ""),
        "allowed_path_patterns": list(_list(request.get("allowed_path_patterns"))),
        "expected_changed_paths": list(_list(request.get("expected_changed_paths"))),
        "forbidden_path_patterns": list(_list(request.get("forbidden_path_patterns"))),
        "diff_evidence": dict(diff_evidence),
        "test_evidence": dict(test_evidence),
        "signed_authority": dict(_mapping(request.get("signed_authority"))),
        "signed_receipt_chain": dict(_mapping(request.get("signed_receipt_chain"))),
        "holoindex_evidence": dict(_mapping(request.get("holoindex_evidence"))),
        "pattern_memory_write_performed": bool(request.get("pattern_memory_write_performed")),
        "draft_pr_published": bool(request.get("draft_pr_published")),
        "merge_performed": bool(request.get("merge_performed")),
    }
    for optional in ("protected_surface_authorization_digest", "consensus_receipt_digest"):
        if request.get(optional):
            verifier_request[optional] = request[optional]
    return verifier_request


def build_reddog_resident_queue_slice_verifier_stage_handler(
    *,
    chain_results_store: ResidentQueueChainResultsStore,
    verifier_request: Mapping[str, Any] | None = None,
    evidence_producer_request: Mapping[str, Any] | None = None,
    evidence_command_runner: Any = None,
) -> ResidentQueueSliceVerifierStageHandler:
    """Build the injected slice-verifier handler for the dispatcher."""

    return ResidentQueueSliceVerifierStageHandler(
        chain_results_store=chain_results_store,
        verifier_request=verifier_request,
        evidence_producer_request=evidence_producer_request,
        evidence_command_runner=evidence_command_runner,
    )


__all__ = [
    "BOUNDED_WORKER_PILOT_STAGE_KEY",
    "FAIL_BOUNDED_WORKER_PILOT_STAGE_MISSING",
    "FAIL_DISPATCH_NEXT_ACTION_MISMATCH",
    "FAIL_DISPATCH_STAGE_MISMATCH",
    "FAIL_EVIDENCE_COMMAND_RUNNER_MISSING",
    "FAIL_EVIDENCE_PRODUCER_REJECTED",
    "FAIL_VERIFIER_REQUEST_MISSING",
    "ResidentQueueSliceVerifierStageHandler",
    "SLICE_VERIFIER_STAGE_KEY",
    "build_reddog_resident_queue_slice_verifier_stage_handler",
]
