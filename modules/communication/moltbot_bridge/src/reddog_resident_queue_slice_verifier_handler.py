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
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Optional, Protocol

from modules.communication.moltbot_bridge.src.reddog_openclaw_assurance_capacity import (
    canonical_digest,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_chain_results_store import (
    ResidentQueueChainResultsStore,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_next_stage_dispatch import (
    ResidentQueueStageDispatchRequest,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_orchestration_plan import (
    NEXT_QUEUE_SLICE_VERIFIER_INVOKE,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_slice_verifier_request_binding import (
    FAIL_SIGNED_AUTHORITY_BINDING_MISMATCH,
    build_resident_queue_slice_verifier_request,
    verified_signed_authority_from_stage_results,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_slice_verifier_invoke import (
    QUEUE_AUTHORIZED_SLICE_VERIFIER_INVOKE_REJECT,
    invoke_reddog_wre_queue_authorized_slice_verifier,
)
from modules.communication.moltbot_bridge.src.reddog_worker_dispatch_authority_binding import (
    recorded_authority_verification_binding,
)
from modules.infrastructure.wre_core.src.wre_independent_evidence_producer_runtime import (
    produce_independent_slice_evidence,
)
from modules.infrastructure.database.src.signed_worker_assurance_completion import (
    build_assurance_completion_request,
)


SLICE_VERIFIER_STAGE_KEY = "slice_verifier"
BOUNDED_WORKER_PILOT_STAGE_KEY = "bounded_worker_pilot"

FAIL_DISPATCH_STAGE_MISMATCH = "FAIL_DISPATCH_STAGE_MISMATCH"
FAIL_DISPATCH_NEXT_ACTION_MISMATCH = "FAIL_DISPATCH_NEXT_ACTION_MISMATCH"
FAIL_BOUNDED_WORKER_PILOT_STAGE_MISSING = "FAIL_BOUNDED_WORKER_PILOT_STAGE_MISSING"
FAIL_VERIFIER_REQUEST_MISSING = "FAIL_VERIFIER_REQUEST_MISSING"
FAIL_EVIDENCE_COMMAND_RUNNER_MISSING = "FAIL_EVIDENCE_COMMAND_RUNNER_MISSING"
FAIL_EVIDENCE_PRODUCER_REJECTED = "FAIL_EVIDENCE_PRODUCER_REJECTED"
FAIL_WORK_ORDER_ID_MISSING = "FAIL_WORK_ORDER_ID_MISSING"
FAIL_WORK_ORDER_MISSING = "FAIL_WORK_ORDER_MISSING"
FAIL_SLICE_VERIFIER_REQUEST_BINDING_REJECTED = "FAIL_SLICE_VERIFIER_REQUEST_BINDING_REJECTED"
FAIL_ASSURANCE_RESERVATION_MISSING = "FAIL_ASSURANCE_RESERVATION_MISSING"
FAIL_ASSURANCE_RESERVATION_MISMATCH = "FAIL_ASSURANCE_RESERVATION_MISMATCH"
FAIL_ASSURANCE_RESERVATION_TERMINAL_BINDING = (
    "FAIL_ASSURANCE_RESERVATION_TERMINAL_BINDING"
)


class ResidentQueueSliceVerifierWorkOrderResolver(Protocol):
    """Injected resolver for the work order bound to the bounded pilot."""

    def resolve(
        self,
        *,
        work_order_id: str,
        queue_item_id: Optional[str],
        selected_slice: Optional[str],
    ) -> Mapping[str, Any]:
        """Return the queue-bound work order mapping."""


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


def _work_order_id_from_bounded_worker_pilot(bounded_worker_pilot: Mapping[str, Any]) -> str:
    pilot = _mapping(bounded_worker_pilot.get("pilot_result"))
    receipt = _mapping(pilot.get("receipt"))
    return str(receipt.get("work_order_id") or "").strip()


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
    work_order_resolver: ResidentQueueSliceVerifierWorkOrderResolver | None = None
    repo_root: Path | None = None
    slice_verifier_request_binding_enabled: bool = False
    holoindex_evidence: Mapping[str, Any] | None = None
    assurance_reservation_store: Any = None
    trusted_now: datetime | None = None

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
        recorded_authority_binding = recorded_authority_verification_binding(
            _mapping(stage_results.get("authority_runtime")),
            _mapping(stage_results.get("authority_verification")),
        )
        recorded_signed_authority = (
            verified_signed_authority_from_stage_results(stage_results)
        )
        if not recorded_authority_binding or not recorded_signed_authority:
            return _reject(FAIL_SIGNED_AUTHORITY_BINDING_MISMATCH)
        bounded_worker_pilot = _mapping(stage_results.get(BOUNDED_WORKER_PILOT_STAGE_KEY))
        if not bounded_worker_pilot:
            return _reject(FAIL_BOUNDED_WORKER_PILOT_STAGE_MISSING)
        reservation, reservation_reason = _verified_assurance_reservation(
            stage_results=stage_results,
            reservation_store=self.assurance_reservation_store,
        )
        if reservation_reason:
            return _reject(reservation_reason)

        verifier_request = _mapping(self.verifier_request)
        evidence_producer_request = _mapping(self.evidence_producer_request)
        evidence_producer_result: Mapping[str, Any] | None = None
        slice_verifier_request_binding_result: Mapping[str, Any] | None = None
        if (
            not verifier_request
            and not evidence_producer_request
            and self.slice_verifier_request_binding_enabled
        ):
            if self.work_order_resolver is None:
                return _reject(FAIL_WORK_ORDER_MISSING, "missing_dependency:work_order_resolver")
            if self.repo_root is None:
                return _reject(FAIL_WORK_ORDER_MISSING, "missing_dependency:repo_root")
            work_order_id = _work_order_id_from_bounded_worker_pilot(bounded_worker_pilot)
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
            bound = build_resident_queue_slice_verifier_request(
                work_order=work_order,
                stage_results=stage_results,
                repo_root=self.repo_root,
                holoindex_evidence=self.holoindex_evidence,
                assurance_reservation_store=self.assurance_reservation_store,
            )
            slice_verifier_request_binding_result = bound.to_dict()
            if bound.accepted is not True:
                rejected = _reject(
                    FAIL_SLICE_VERIFIER_REQUEST_BINDING_REJECTED,
                    *bound.rejection_reasons,
                )
                rejected["slice_verifier_request_binding_result"] = (
                    slice_verifier_request_binding_result
                )
                return rejected
            evidence_producer_request = bound.evidence_producer_request
        if not verifier_request:
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
                test_differential_capability=produced.test_differential_capability,
            )
        verifier_request = {
            **dict(verifier_request),
            "signed_authority": recorded_signed_authority,
            "worker_id": str(reservation.get("author_principal_id") or ""),
            "verifier_id": str(
                reservation.get("verifier_principal_id") or ""
            ),
            "assurance_reservation_id": str(
                reservation.get("reservation_id") or ""
            ),
            "assurance_reservation_digest": str(
                reservation.get("admission_reservation_digest")
                or reservation.get("reservation_digest")
                or ""
            ),
            "verifier_task_id": str(
                reservation.get("verifier_task_id") or ""
            ),
        }

        result = invoke_reddog_wre_queue_authorized_slice_verifier(
            explicit_queue_authorized_slice_verifier_requested=True,
            queue_bounded_worker_pilot_result=bounded_worker_pilot,
            verifier_request=verifier_request,
            trusted_work_authority_digest=str(
                recorded_authority_binding["verified_work_authority_digest"]
            ),
        ).to_dict()
        terminal_receipt = _mapping(
            _mapping(result.get("verifier_result")).get("receipt")
        )
        if terminal_receipt:
            if not _terminal_receipt_matches_reservation(
                terminal_receipt,
                reservation=reservation,
            ):
                return _reject(
                    FAIL_ASSURANCE_RESERVATION_TERMINAL_BINDING
                )
            normalized_receipt = {
                **dict(terminal_receipt),
                "receipt_digest": str(
                    terminal_receipt.get("receipt_digest")
                    or canonical_digest(terminal_receipt)
                ),
            }
            completion_request = build_assurance_completion_request(
                reservation=reservation,
                terminal_receipt=normalized_receipt,
                terminal_status=(
                    "ACCEPT"
                    if terminal_receipt.get("accepted") is True
                    else "REJECT"
                ),
                completed_at=(self.trusted_now or datetime.now(timezone.utc))
                .astimezone(timezone.utc)
                .isoformat(),
            )
            staged = _mapping(
                self.assurance_reservation_store
                .stage_independent_assurance_completion(completion_request)
            )
            if staged.get("accepted") is not True:
                return _reject(FAIL_ASSURANCE_RESERVATION_TERMINAL_BINDING)
            result["assurance_completion_request"] = completion_request
            result["assurance_completion_stage_result"] = staged
        if evidence_producer_result is not None:
            result["evidence_producer_result"] = evidence_producer_result
            command_results = evidence_producer_result.get("command_results")
            result["bounded_evidence_command_execution_performed"] = bool(command_results)
            result["no_command_execution_performed"] = False
            result["no_shell_command_executed"] = True
        if slice_verifier_request_binding_result is not None:
            result["slice_verifier_request_binding_result"] = slice_verifier_request_binding_result
        return result


def _verifier_request_from_evidence(
    *,
    request: Mapping[str, Any],
    diff_evidence: Mapping[str, Any],
    test_evidence: Mapping[str, Any],
    test_differential_capability: object | None = None,
) -> dict[str, Any]:
    verifier_request = {
        "work_order_id": str(request.get("work_order_id") or ""),
        "slice_name": str(request.get("slice_name") or ""),
        "worker_id": str(request.get("worker_id") or ""),
        "verifier_id": str(request.get("verifier_id") or ""),
        "assurance_reservation_id": str(
            request.get("assurance_reservation_id") or ""
        ),
        "assurance_reservation_digest": str(
            request.get("assurance_reservation_digest") or ""
        ),
        "verifier_task_id": str(request.get("verifier_task_id") or ""),
        "base_sha": str(request.get("base_sha") or ""),
        "head_sha": str(request.get("head_sha") or ""),
        "allowed_path_patterns": list(_list(request.get("allowed_path_patterns"))),
        "expected_changed_paths": list(_list(request.get("expected_changed_paths"))),
        "forbidden_path_patterns": list(_list(request.get("forbidden_path_patterns"))),
        "diff_evidence": dict(diff_evidence),
        "test_evidence": dict(test_evidence),
        "signed_authority": dict(_mapping(request.get("signed_authority"))),
        "signed_receipt_chain": dict(_mapping(request.get("signed_receipt_chain"))),
        "worktree_receipt": dict(_mapping(request.get("worktree_receipt"))),
        "bounded_worker_pilot_receipt": dict(
            _mapping(request.get("bounded_worker_pilot_receipt"))
        ),
        "exact_sha_commit_receipt": dict(
            _mapping(request.get("exact_sha_commit_receipt"))
        ),
        "bound_work_order": dict(_mapping(request.get("bound_work_order"))),
        "test_impact_policy": dict(_mapping(request.get("test_impact_policy"))),
        "test_differential_capability": test_differential_capability,
        "holoindex_evidence": dict(_mapping(request.get("holoindex_evidence"))),
        "pattern_memory_write_performed": bool(request.get("pattern_memory_write_performed")),
        "draft_pr_published": bool(request.get("draft_pr_published")),
        "merge_performed": bool(request.get("merge_performed")),
    }
    for optional in ("protected_surface_authorization_digest", "consensus_receipt_digest"):
        if request.get(optional):
            verifier_request[optional] = request[optional]
    return verifier_request


def _verified_assurance_reservation(
    *,
    stage_results: Mapping[str, Mapping[str, Any]],
    reservation_store: Any,
) -> tuple[Mapping[str, Any], str]:
    admission = _mapping(stage_results.get("assurance_capacity_admission"))
    recorded = _mapping(admission.get("reservation"))
    reservation_id = str(recorded.get("reservation_id") or "")
    if (
        admission.get("decision") != "ASSURANCE_CAPACITY_ADMISSION_ACCEPT"
        or not reservation_id
        or reservation_store is None
    ):
        return {}, FAIL_ASSURANCE_RESERVATION_MISSING
    durable = _mapping(
        reservation_store.get_independent_assurance_reservation(
            reservation_id
        )
    )
    if _mapping(durable.get("reservation")):
        durable = _mapping(durable.get("reservation"))
    if (
        not durable
        or str(durable.get("status") or "").lower() != "reserved"
        or str(
            durable.get("admission_reservation_digest")
            or durable.get("reservation_digest")
            or ""
        )
        != str(recorded.get("reservation_digest") or "")
        or str(durable.get("author_task_id") or "")
        == str(durable.get("verifier_task_id") or "")
        or str(durable.get("author_principal_id") or "")
        == str(durable.get("verifier_principal_id") or "")
    ):
        return {}, FAIL_ASSURANCE_RESERVATION_MISMATCH
    return durable, ""


def _terminal_receipt_matches_reservation(
    receipt: Mapping[str, Any],
    *,
    reservation: Mapping[str, Any],
) -> bool:
    admission_digest = str(
        reservation.get("admission_reservation_digest")
        or reservation.get("reservation_digest")
        or ""
    )
    expected = {
        "assurance_reservation_id": str(
            reservation.get("reservation_id") or ""
        ),
        "assurance_reservation_digest": admission_digest,
        "verifier_task_id": str(reservation.get("verifier_task_id") or ""),
        "worker_id": str(reservation.get("author_principal_id") or ""),
        "verifier_id": str(reservation.get("verifier_principal_id") or ""),
        "work_order_id": str(reservation.get("work_order_id") or ""),
    }
    return all(
        expected_value
        and str(receipt.get(field_name) or "") == expected_value
        for field_name, expected_value in expected.items()
    )


def build_reddog_resident_queue_slice_verifier_stage_handler(
    *,
    chain_results_store: ResidentQueueChainResultsStore,
    verifier_request: Mapping[str, Any] | None = None,
    evidence_producer_request: Mapping[str, Any] | None = None,
    evidence_command_runner: Any = None,
    work_order_resolver: ResidentQueueSliceVerifierWorkOrderResolver | None = None,
    repo_root: Path | None = None,
    slice_verifier_request_binding_enabled: bool = False,
    holoindex_evidence: Mapping[str, Any] | None = None,
    assurance_reservation_store: Any = None,
    trusted_now: datetime | None = None,
) -> ResidentQueueSliceVerifierStageHandler:
    """Build the injected slice-verifier handler for the dispatcher."""

    return ResidentQueueSliceVerifierStageHandler(
        chain_results_store=chain_results_store,
        verifier_request=verifier_request,
        evidence_producer_request=evidence_producer_request,
        evidence_command_runner=evidence_command_runner,
        work_order_resolver=work_order_resolver,
        repo_root=repo_root,
        slice_verifier_request_binding_enabled=slice_verifier_request_binding_enabled,
        holoindex_evidence=holoindex_evidence,
        assurance_reservation_store=assurance_reservation_store,
        trusted_now=trusted_now,
    )


__all__ = [
    "BOUNDED_WORKER_PILOT_STAGE_KEY",
    "FAIL_BOUNDED_WORKER_PILOT_STAGE_MISSING",
    "FAIL_ASSURANCE_RESERVATION_MISMATCH",
    "FAIL_ASSURANCE_RESERVATION_MISSING",
    "FAIL_ASSURANCE_RESERVATION_TERMINAL_BINDING",
    "FAIL_DISPATCH_NEXT_ACTION_MISMATCH",
    "FAIL_DISPATCH_STAGE_MISMATCH",
    "FAIL_EVIDENCE_COMMAND_RUNNER_MISSING",
    "FAIL_EVIDENCE_PRODUCER_REJECTED",
    "FAIL_SLICE_VERIFIER_REQUEST_BINDING_REJECTED",
    "FAIL_VERIFIER_REQUEST_MISSING",
    "FAIL_WORK_ORDER_ID_MISSING",
    "FAIL_WORK_ORDER_MISSING",
    "ResidentQueueSliceVerifierStageHandler",
    "ResidentQueueSliceVerifierWorkOrderResolver",
    "SLICE_VERIFIER_STAGE_KEY",
    "build_reddog_resident_queue_slice_verifier_stage_handler",
]
