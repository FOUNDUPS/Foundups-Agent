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
from modules.communication.moltbot_bridge.src.reddog_artifact_generation_admission_capability import (
    _issue_artifact_generation_authority,
)
from modules.ai_intelligence.ai_gateway.src.model_runtime_binding_verified_admission import (
    discard_verified_runtime_binding_capability,
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
FAIL_MODEL_RUNTIME_VERIFIER_MISSING = "FAIL_MODEL_RUNTIME_VERIFIER_MISSING"
FAIL_MODEL_RUNTIME_VERIFICATION_REJECTED = (
    "FAIL_MODEL_RUNTIME_VERIFICATION_REJECTED"
)
FAIL_ARTIFACT_GENERATION_REQUEST_CONFLICT = "FAIL_ARTIFACT_GENERATION_REQUEST_CONFLICT"
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


class ModelRuntimeBindingUseTimeVerifier(Protocol):
    """Freshly verify the persisted model authority before model invocation."""

    def verify(
        self,
        *,
        binding: Mapping[str, Any],
        selection: Mapping[str, Any],
    ) -> Any: ...


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
    model_runtime_binding_verifier: Any = None

    def __call__(self, request: ResidentQueueStageDispatchRequest) -> Mapping[str, Any]:
        rejected = self._dispatch_rejection(request)
        if rejected:
            return rejected
        loaded = self._load_work(request)
        if isinstance(loaded, dict) and "decision" in loaded:
            return loaded
        stage_results, worktree_create, work_order = loaded
        dryruns = self._resolve_dryruns(work_order, stage_results)
        if isinstance(dryruns, dict) and "decision" in dryruns:
            return dryruns
        generic_writer, governed_shell, dryrun_receipt = dryruns
        artifacts = self._resolve_artifacts(work_order, stage_results)
        if isinstance(artifacts, dict) and "decision" in artifacts:
            return artifacts
        artifact_contents, generation_receipt = artifacts
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
        if dryrun_receipt is not None:
            result["pilot_dryrun_binding_result"] = dryrun_receipt
        if generation_receipt is not None:
            result["artifact_generation_result"] = generation_receipt
        return result

    def _dispatch_rejection(
        self, request: ResidentQueueStageDispatchRequest
    ) -> Mapping[str, Any]:
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
        return {}

    def _load_work(self, request: ResidentQueueStageDispatchRequest) -> Any:
        stages = _stage_results(_mapping(self.chain_results_store.load()))
        worktree = _mapping(stages.get(WORKTREE_CREATE_STAGE_KEY))
        if not worktree:
            return _reject(FAIL_WORKTREE_CREATE_STAGE_MISSING)
        work_order_id = _work_order_id_from_worktree_create(worktree)
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
        return stages, worktree, work_order

    def _resolve_dryruns(self, work_order: Mapping[str, Any], stages: Mapping[str, Any]) -> Any:
        generic = _mapping(self.generic_writer_dryrun_result)
        shell = _mapping(self.governed_shell_dryrun_result)
        if generic and shell:
            return generic, shell, None
        bound = build_resident_queue_pilot_dryruns(
            work_order=work_order,
            stage_results=stages,
            repo_root=self.repo_root,
            operation_cwd=self.operation_cwd,
            holoindex_evidence=self.holoindex_evidence,
        )
        receipt = bound.to_dict()
        if bound.accepted is not True:
            result = _reject(FAIL_PILOT_DRYRUN_BINDING_REJECTED, *bound.rejection_reasons)
            result["pilot_dryrun_binding_result"] = receipt
            return result
        if generic and dict(generic) != dict(bound.generic_writer_dryrun_result):
            return _rejection_with(FAIL_PILOT_DRYRUN_BINDING_CONFLICT, receipt)
        if shell and dict(shell) != dict(bound.governed_shell_dryrun_result):
            return _rejection_with(FAIL_PILOT_DRYRUN_BINDING_CONFLICT, receipt)
        return bound.generic_writer_dryrun_result, bound.governed_shell_dryrun_result, receipt

    def _resolve_artifacts(self, work_order: Mapping[str, Any], stages: Mapping[str, Any]) -> Any:
        contents = _mapping(self.artifact_contents)
        if contents:
            return contents, None
        request = self._generation_request(work_order, stages)
        if isinstance(request, dict) and "decision" in request:
            return request
        if self.artifact_generator is None:
            return _reject(FAIL_ARTIFACT_GENERATOR_MISSING)
        capability = self._model_capability(request)
        if isinstance(capability, dict):
            return capability
        authority = _issue_artifact_generation_authority(request)
        try:
            generated = generate_bounded_artifact_contents(
                request,
                runner=self.artifact_generator,
                authority_capability=authority,
                model_runtime_binding_capability=capability,
            )
        finally:
            discard_verified_runtime_binding_capability(capability)
        receipt = generated.to_dict()
        if generated.accepted is not True:
            result = _reject(FAIL_ARTIFACT_GENERATION_REJECTED, *generated.rejection_reasons)
            result["artifact_generation_result"] = receipt
            return result
        return generated.artifact_contents, receipt

    def _generation_request(self, work_order: Mapping[str, Any], stages: Mapping[str, Any]) -> Any:
        supplied = _mapping(self.artifact_generation_request)
        if not supplied and not self.artifact_generation_request_binding_enabled:
            return _reject(FAIL_ARTIFACT_CONTENTS_MISSING)
        derived = _derive_artifact_generation_request(
            work_order=work_order,
            stage_results=stages,
            repo_root=self.repo_root,
            holoindex_evidence=self.holoindex_evidence,
        )
        if supplied and _canonical(supplied) != _canonical(derived):
            return _reject(FAIL_ARTIFACT_GENERATION_REQUEST_CONFLICT)
        return derived

    def _model_capability(self, request: Mapping[str, Any]) -> Any:
        if self.model_runtime_binding_verifier is None:
            return _reject(FAIL_MODEL_RUNTIME_VERIFIER_MISSING)
        try:
            return self.model_runtime_binding_verifier.verify(
                binding=_mapping(request.get("model_runtime_binding_receipt")),
                selection=_mapping(request.get("model_selection_receipt")),
            )
        except Exception:
            return _reject(FAIL_MODEL_RUNTIME_VERIFICATION_REJECTED)


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
    model_runtime_binding_verifier: Any = None,
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
        model_runtime_binding_verifier=model_runtime_binding_verifier,
    )


def _rejection_with(reason: str, receipt: Mapping[str, Any]) -> dict[str, Any]:
    result = _reject(reason)
    result["pilot_dryrun_binding_result"] = dict(receipt)
    return result


def _derive_artifact_generation_request(
    *,
    work_order: Mapping[str, Any],
    stage_results: Mapping[str, Mapping[str, Any]],
    repo_root: Path,
    holoindex_evidence: Optional[Mapping[str, Any]],
) -> Mapping[str, Any]:
    inputs = _artifact_generation_inputs(work_order, stage_results)
    if inputs is None:
        return {}
    (
        plan,
        worktree_result,
        signed_receipt_chain,
        work_authority,
        authority_receipt,
        planned_artifacts,
    ) = inputs
    selection, runtime_binding = _artifact_model_receipts(work_order, plan)
    task_summary = str(work_order.get("task_summary") or "")
    if not task_summary:
        return {}
    evidence = (
        holoindex_evidence
        if isinstance(holoindex_evidence, Mapping)
        else _mapping(work_order.get("holoindex_evidence"))
    )
    signed_authority = _artifact_signed_authority(
        work_authority,
        authority_receipt,
    )
    request = _artifact_generation_request_payload(
        work_order=work_order,
        plan=plan,
        repo_root=repo_root,
        worktree_result=worktree_result,
        task_summary=task_summary,
        planned_artifacts=planned_artifacts,
        evidence=evidence,
        signed_authority=signed_authority,
        signed_receipt_chain=signed_receipt_chain,
        model_selection_receipt=selection,
    )
    if runtime_binding:
        request["model_runtime_binding_receipt"] = dict(runtime_binding)
    return request


def _artifact_generation_inputs(
    work_order: Mapping[str, Any],
    stages: Mapping[str, Mapping[str, Any]],
) -> Optional[tuple[Any, ...]]:
    plan = _mapping(work_order.get("bounded_worker_plan"))
    worktree = _mapping(_mapping(stages.get(WORKTREE_CREATE_STAGE_KEY)).get("worktree_create_result"))
    authority_result = _mapping(_mapping(stages.get("authority_runtime")).get("authority_result"))
    verification = _mapping(stages.get("authority_verification"))
    work_authority = _mapping(authority_result.get("work_authority"))
    authority_receipt = _mapping(authority_result.get("receipt"))
    chain = _mapping(plan.get("signed_receipt_chain"))
    artifacts = _list(plan.get("planned_artifacts"))
    valid = (
        bool(plan)
        and bool(artifacts)
        and bool(chain)
        and authority_result.get("accepted") is True
        and _authority_verification_matches(verification, authority_receipt)
        and bool(work_authority)
        and bool(worktree.get("worktree_path"))
    )
    if not valid:
        return None
    return plan, worktree, chain, work_authority, authority_receipt, artifacts


def _artifact_generation_request_payload(
    *,
    work_order: Mapping[str, Any],
    plan: Mapping[str, Any],
    repo_root: Path,
    worktree_result: Mapping[str, Any],
    task_summary: str,
    planned_artifacts: list[Any],
    evidence: Mapping[str, Any],
    signed_authority: Mapping[str, Any],
    signed_receipt_chain: Mapping[str, Any],
    model_selection_receipt: Mapping[str, Any],
) -> dict[str, Any]:
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


def _artifact_model_receipts(
    work_order: Mapping[str, Any],
    plan: Mapping[str, Any],
) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
    binding = _mapping(work_order.get("operational_context_binding"))
    selection = (
        _mapping(plan.get("model_selection_receipt"))
        or _mapping(work_order.get("model_selection_receipt"))
        or _mapping(binding.get("model_selection_receipt"))
    )
    runtime = (
        _mapping(plan.get("model_runtime_binding_receipt"))
        or _mapping(work_order.get("model_runtime_binding_receipt"))
        or _mapping(binding.get("model_runtime_binding_receipt"))
    )
    return selection, runtime


def _artifact_signed_authority(
    work_authority: Mapping[str, Any],
    authority_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        **dict(work_authority),
        "accepted": True,
        "signature_gate_digest": str(
            authority_receipt.get("work_authority_digest")
            or authority_receipt.get("receipt_id")
            or ""
        ),
    }


def _authority_verification_matches(
    verification_stage: Mapping[str, Any],
    authority_receipt: Mapping[str, Any],
) -> bool:
    result = _mapping(verification_stage.get("verification_result"))
    verified_digest = str(
        verification_stage.get("verified_work_authority_digest") or ""
    )
    expected_digest = str(authority_receipt.get("work_authority_digest") or "")
    return (
        verification_stage.get("decision")
        == "QUEUE_AUTHORITY_VERIFICATION_INVOKE_ACCEPT"
        and result.get("accepted") is True
        and bool(verified_digest)
        and verified_digest == expected_digest
    )


def _canonical(value: Mapping[str, Any]) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=str,
    )


__all__ = [
    "BOUNDED_WORKER_PILOT_STAGE_KEY",
    "FAIL_ARTIFACT_GENERATION_REJECTED",
    "FAIL_ARTIFACT_GENERATION_REQUEST_CONFLICT",
    "FAIL_ARTIFACT_GENERATOR_MISSING",
    "FAIL_MODEL_RUNTIME_VERIFIER_MISSING",
    "FAIL_MODEL_RUNTIME_VERIFICATION_REJECTED",
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
