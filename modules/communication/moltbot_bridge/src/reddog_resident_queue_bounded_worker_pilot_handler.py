"""Resident RedDog bounded-worker-pilot stage handler.

Slice: REDDOG_RESIDENT_QUEUE_BOUNDED_WORKER_PILOT_HANDLER_PHASE1

This module adapts the existing queue-authorized bounded worker pilot explicit
invoke guard to the resident queue next-stage dispatcher. It reads the recorded
`worktree_create` stage result from the chain-results store, resolves the bound
work order through an injected resolver, and invokes the existing pilot guard
with injected generic-writer and governed-shell dry-run results plus declared
artifact contents.

It may materialize only declared artifacts inside the already-created isolated
worktree through the existing pilot guard. It does not run shell commands,
enqueue OpenClaw, dispatch Hermes, create PRs, merge, settle rewards, or
re-index HoloIndex.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Optional, Protocol

from modules.communication.moltbot_bridge.src.reddog_resident_queue_chain_results_store import (
    ResidentQueueChainResultsStore,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_next_stage_dispatch import (
    ResidentQueueStageDispatchRequest,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_orchestration_plan import (
    NEXT_QUEUE_BOUNDED_WORKER_PILOT_INVOKE,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_pilot_dryrun_binding import (
    build_resident_queue_pilot_dryruns,
)
from modules.communication.moltbot_bridge.src.reddog_bounded_artifact_generation_runtime import (
    generate_bounded_artifact_contents,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_bounded_worker_pilot_invoke import (
    QUEUE_AUTHORIZED_BOUNDED_WORKER_PILOT_INVOKE_REJECT,
    invoke_reddog_wre_queue_authorized_bounded_worker_pilot,
)


BOUNDED_WORKER_PILOT_STAGE_KEY = "bounded_worker_pilot"
WORKTREE_CREATE_STAGE_KEY = "worktree_create"

FAIL_DISPATCH_STAGE_MISMATCH = "FAIL_DISPATCH_STAGE_MISMATCH"
FAIL_DISPATCH_NEXT_ACTION_MISMATCH = "FAIL_DISPATCH_NEXT_ACTION_MISMATCH"
FAIL_WORKTREE_CREATE_STAGE_MISSING = "FAIL_WORKTREE_CREATE_STAGE_MISSING"
FAIL_WORK_ORDER_ID_MISSING = "FAIL_WORK_ORDER_ID_MISSING"
FAIL_WORK_ORDER_MISSING = "FAIL_WORK_ORDER_MISSING"
FAIL_GENERIC_WRITER_DRYRUN_MISSING = "FAIL_GENERIC_WRITER_DRYRUN_MISSING"
FAIL_GOVERNED_SHELL_DRYRUN_MISSING = "FAIL_GOVERNED_SHELL_DRYRUN_MISSING"
FAIL_ARTIFACT_CONTENTS_MISSING = "FAIL_ARTIFACT_CONTENTS_MISSING"
FAIL_ARTIFACT_GENERATOR_MISSING = "FAIL_ARTIFACT_GENERATOR_MISSING"
FAIL_ARTIFACT_GENERATION_REJECTED = "FAIL_ARTIFACT_GENERATION_REJECTED"
FAIL_PILOT_DRYRUN_BINDING_REJECTED = "FAIL_PILOT_DRYRUN_BINDING_REJECTED"
FAIL_PILOT_DRYRUN_BINDING_CONFLICT = "FAIL_PILOT_DRYRUN_BINDING_CONFLICT"


class ResidentQueueBoundedWorkerWorkOrderResolver(Protocol):
    """Injected resolver for the work order bound to worktree creation."""

    def resolve(
        self,
        *,
        work_order_id: str,
        queue_item_id: Optional[str],
        selected_slice: Optional[str],
    ) -> Mapping[str, Any]:
        """Return the work order mapping for an accepted worktree result."""


def _mapping(value: Any) -> Mapping[str, Any]:
    if hasattr(value, "to_dict"):
        candidate = value.to_dict()
        return candidate if isinstance(candidate, Mapping) else {}
    if isinstance(value, Mapping):
        return value
    return {}


def _list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return []


def _stage_results(state: Mapping[str, Any]) -> Mapping[str, Mapping[str, Any]]:
    raw = state.get("stage_results") if state.get("schema_version") == "reddog_resident_queue_chain_results.v1" else state
    if not isinstance(raw, Mapping):
        return {}
    return {str(key): value for key, value in raw.items() if isinstance(value, Mapping)}


def _work_order_id_from_worktree_create(worktree_create_stage: Mapping[str, Any]) -> str:
    worktree = _mapping(worktree_create_stage.get("worktree_create_result"))
    return str(worktree.get("work_order_id") or "").strip()


def _reject(*reasons: str) -> dict[str, Any]:
    return {
        "decision": QUEUE_AUTHORIZED_BOUNDED_WORKER_PILOT_INVOKE_REJECT,
        "rejection_reasons": list(dict.fromkeys(reason for reason in reasons if reason)),
        "pilot_result": None,
        "explicit_queue_authorized_bounded_worker_pilot_requested": False,
        "bounded_task_execution_performed": False,
        "bounded_file_edit_performed": False,
        "shell_command_executed": False,
        "draft_pr_created": False,
        "merge_performed": False,
        "openclaw_enqueue_performed": False,
        "hermes_dispatch_performed": False,
        "reward_settlement_performed": False,
        "holoindex_reindex_performed": False,
    }


@dataclass(frozen=True)
class ResidentQueueBoundedWorkerPilotStageHandler:
    """Callable handler for the resident queue `bounded_worker_pilot` stage."""

    chain_results_store: ResidentQueueChainResultsStore
    work_order_resolver: ResidentQueueBoundedWorkerWorkOrderResolver
    generic_writer_dryrun_result: Mapping[str, Any] | None
    governed_shell_dryrun_result: Mapping[str, Any] | None
    artifact_contents: Mapping[str, Any] | None
    repo_root: Path
    operation_cwd: Optional[Path] = None
    holoindex_evidence: Optional[Mapping[str, Any]] = None
    artifact_generation_request: Mapping[str, Any] | None = None
    artifact_generation_request_binding_enabled: bool = False
    artifact_generator: Any = None

    def __call__(self, request: ResidentQueueStageDispatchRequest) -> Mapping[str, Any]:
        if request.stage_key != BOUNDED_WORKER_PILOT_STAGE_KEY:
            return _reject(
                FAIL_DISPATCH_STAGE_MISMATCH,
                f"expected:{BOUNDED_WORKER_PILOT_STAGE_KEY}",
                f"actual:{request.stage_key}",
            )
        if request.next_action != NEXT_QUEUE_BOUNDED_WORKER_PILOT_INVOKE:
            return _reject(
                FAIL_DISPATCH_NEXT_ACTION_MISMATCH,
                f"expected:{NEXT_QUEUE_BOUNDED_WORKER_PILOT_INVOKE}",
                f"actual:{request.next_action}",
            )

        stage_results = _stage_results(_mapping(self.chain_results_store.load()))
        worktree_create = _mapping(stage_results.get(WORKTREE_CREATE_STAGE_KEY))
        if not worktree_create:
            return _reject(FAIL_WORKTREE_CREATE_STAGE_MISSING)

        work_order_id = _work_order_id_from_worktree_create(worktree_create)
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

        pilot_dryrun_binding_result: Mapping[str, Any] | None = None
        generic_writer = _mapping(self.generic_writer_dryrun_result)
        governed_shell = _mapping(self.governed_shell_dryrun_result)
        if not generic_writer or not governed_shell:
            bound = build_resident_queue_pilot_dryruns(
                work_order=work_order,
                stage_results=stage_results,
                repo_root=self.repo_root,
                operation_cwd=self.operation_cwd,
                holoindex_evidence=self.holoindex_evidence,
            )
            pilot_dryrun_binding_result = bound.to_dict()
            if bound.accepted is not True:
                rejected = _reject(FAIL_PILOT_DRYRUN_BINDING_REJECTED, *bound.rejection_reasons)
                rejected["pilot_dryrun_binding_result"] = pilot_dryrun_binding_result
                return rejected
            if generic_writer and dict(generic_writer) != dict(bound.generic_writer_dryrun_result):
                rejected = _reject(FAIL_PILOT_DRYRUN_BINDING_CONFLICT)
                rejected["pilot_dryrun_binding_result"] = pilot_dryrun_binding_result
                return rejected
            if governed_shell and dict(governed_shell) != dict(bound.governed_shell_dryrun_result):
                rejected = _reject(FAIL_PILOT_DRYRUN_BINDING_CONFLICT)
                rejected["pilot_dryrun_binding_result"] = pilot_dryrun_binding_result
                return rejected
            generic_writer = bound.generic_writer_dryrun_result
            governed_shell = bound.governed_shell_dryrun_result
        if not generic_writer:
            return _reject(FAIL_GENERIC_WRITER_DRYRUN_MISSING)
        if not governed_shell:
            return _reject(FAIL_GOVERNED_SHELL_DRYRUN_MISSING)
        artifact_contents = _mapping(self.artifact_contents)
        artifact_generation_result: Mapping[str, Any] | None = None
        if not artifact_contents:
            generation_request = _mapping(self.artifact_generation_request)
            if not generation_request and self.artifact_generation_request_binding_enabled:
                generation_request = _derive_artifact_generation_request(
                    work_order=work_order,
                    stage_results=stage_results,
                    repo_root=self.repo_root,
                    holoindex_evidence=self.holoindex_evidence,
                )
            if not generation_request:
                return _reject(FAIL_ARTIFACT_CONTENTS_MISSING)
            if self.artifact_generator is None:
                return _reject(FAIL_ARTIFACT_GENERATOR_MISSING)
            generated = generate_bounded_artifact_contents(
                generation_request,
                runner=self.artifact_generator,
            )
            artifact_generation_result = generated.to_dict()
            if generated.accepted is not True:
                rejected = _reject(FAIL_ARTIFACT_GENERATION_REJECTED, *generated.rejection_reasons)
                rejected["artifact_generation_result"] = artifact_generation_result
                return rejected
            artifact_contents = generated.artifact_contents

        result = invoke_reddog_wre_queue_authorized_bounded_worker_pilot(
            explicit_queue_authorized_bounded_worker_pilot_requested=True,
            queue_worktree_create_result=worktree_create,
            generic_writer_dryrun_result=generic_writer,
            governed_shell_dryrun_result=governed_shell,
            artifact_contents=artifact_contents,
            work_order=work_order,
            repo_root=self.repo_root,
            operation_cwd=self.operation_cwd,
            holoindex_evidence=self.holoindex_evidence,
        ).to_dict()
        if pilot_dryrun_binding_result is not None:
            result["pilot_dryrun_binding_result"] = pilot_dryrun_binding_result
        if artifact_generation_result is not None:
            result["artifact_generation_result"] = artifact_generation_result
        return result


def build_reddog_resident_queue_bounded_worker_pilot_stage_handler(
    *,
    chain_results_store: ResidentQueueChainResultsStore,
    work_order_resolver: ResidentQueueBoundedWorkerWorkOrderResolver,
    generic_writer_dryrun_result: Mapping[str, Any] | None = None,
    governed_shell_dryrun_result: Mapping[str, Any] | None = None,
    artifact_contents: Mapping[str, Any] | None = None,
    repo_root: Path,
    operation_cwd: Optional[Path] = None,
    holoindex_evidence: Optional[Mapping[str, Any]] = None,
    artifact_generation_request: Mapping[str, Any] | None = None,
    artifact_generation_request_binding_enabled: bool = False,
    artifact_generator: Any = None,
) -> ResidentQueueBoundedWorkerPilotStageHandler:
    """Build the injected bounded-worker-pilot handler for the dispatcher."""

    return ResidentQueueBoundedWorkerPilotStageHandler(
        chain_results_store=chain_results_store,
        work_order_resolver=work_order_resolver,
        generic_writer_dryrun_result=generic_writer_dryrun_result,
        governed_shell_dryrun_result=governed_shell_dryrun_result,
        artifact_contents=artifact_contents,
        repo_root=repo_root,
        operation_cwd=operation_cwd,
        holoindex_evidence=holoindex_evidence,
        artifact_generation_request=artifact_generation_request,
        artifact_generation_request_binding_enabled=artifact_generation_request_binding_enabled,
        artifact_generator=artifact_generator,
    )


def _derive_artifact_generation_request(
    *,
    work_order: Mapping[str, Any],
    stage_results: Mapping[str, Mapping[str, Any]],
    repo_root: Path,
    holoindex_evidence: Optional[Mapping[str, Any]],
) -> Mapping[str, Any]:
    plan = _mapping(work_order.get("bounded_worker_plan"))
    worktree_stage = _mapping(stage_results.get(WORKTREE_CREATE_STAGE_KEY))
    worktree_result = _mapping(worktree_stage.get("worktree_create_result"))
    authority_stage = _mapping(stage_results.get("authority_runtime"))
    authority_result = _mapping(authority_stage.get("authority_result"))
    work_authority = _mapping(authority_result.get("work_authority"))
    authority_receipt = _mapping(authority_result.get("receipt"))
    signed_receipt_chain = _mapping(plan.get("signed_receipt_chain"))
    model_selection_receipt = (
        _mapping(plan.get("model_selection_receipt"))
        or _mapping(work_order.get("model_selection_receipt"))
        or _mapping(_mapping(work_order.get("operational_context_binding")).get("model_selection_receipt"))
    )
    planned_artifacts = _list(plan.get("planned_artifacts"))
    task_summary = str(work_order.get("task_summary") or "")
    if (
        not plan
        or not planned_artifacts
        or not signed_receipt_chain
        or authority_result.get("accepted") is not True
        or not work_authority
        or not task_summary
        or not worktree_result.get("worktree_path")
    ):
        return {}
    evidence = (
        holoindex_evidence
        if isinstance(holoindex_evidence, Mapping)
        else _mapping(work_order.get("holoindex_evidence"))
    )
    signed_authority = {
        **dict(work_authority),
        "accepted": True,
        "signature_gate_digest": str(
            authority_receipt.get("work_authority_digest")
            or authority_receipt.get("receipt_id")
            or ""
        ),
    }
    return {
        "explicit_artifact_generation_requested": True,
        "work_order_id": str(work_order.get("work_order_id") or ""),
        "slice_name": str(work_order.get("requested_operation") or plan.get("operation") or ""),
        "task_summary": task_summary,
        "planned_artifacts": planned_artifacts,
        "evidence_context": json.dumps(
            {
                "task_summary": task_summary,
                "holoindex_evidence": dict(evidence),
                "holoindex_evidence_refs": _list(work_order.get("holoindex_evidence_refs")),
            },
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ),
        "repo_root": str(repo_root),
        "worktree_path": str(worktree_result.get("worktree_path") or ""),
        "holoindex_evidence": dict(evidence),
        "signed_authority": signed_authority,
        "signed_receipt_chain": dict(signed_receipt_chain),
        "model_selection_receipt": dict(model_selection_receipt),
        "timeout_seconds": 30,
    }


__all__ = [
    "BOUNDED_WORKER_PILOT_STAGE_KEY",
    "FAIL_ARTIFACT_GENERATION_REJECTED",
    "FAIL_ARTIFACT_GENERATOR_MISSING",
    "FAIL_ARTIFACT_CONTENTS_MISSING",
    "FAIL_DISPATCH_NEXT_ACTION_MISMATCH",
    "FAIL_DISPATCH_STAGE_MISMATCH",
    "FAIL_GENERIC_WRITER_DRYRUN_MISSING",
    "FAIL_GOVERNED_SHELL_DRYRUN_MISSING",
    "FAIL_PILOT_DRYRUN_BINDING_CONFLICT",
    "FAIL_PILOT_DRYRUN_BINDING_REJECTED",
    "FAIL_WORK_ORDER_ID_MISSING",
    "FAIL_WORK_ORDER_MISSING",
    "FAIL_WORKTREE_CREATE_STAGE_MISSING",
    "ResidentQueueBoundedWorkerPilotStageHandler",
    "ResidentQueueBoundedWorkerWorkOrderResolver",
    "WORKTREE_CREATE_STAGE_KEY",
    "build_reddog_resident_queue_bounded_worker_pilot_stage_handler",
]
