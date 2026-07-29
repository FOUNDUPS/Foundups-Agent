"""Durable OpenClaw repair seam for start-operations Holo grounding."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Mapping

from modules.communication.moltbot_bridge.src.reddog_start_operations_holo_repair_contract import (
    SCHEMA_VERSION,
    SOURCE,
    TASK_PREFIX,
    StartOperationsHoloRepairResult,
    repairable_grounding_failure,
    validate_holo_repair_task_binding,
)
from modules.communication.moltbot_bridge.src.reddog_start_operations_holo_repair_support import (
    execute_repair,
    prepare_task,
    runtime_dependencies,
)


def _current_owner(
    root: Path,
    repo_head_sha: str,
    env: Mapping[str, str],
    ensure_operational: Callable[..., Any],
) -> Any:
    try:
        result = ensure_operational(
            repo_root=root,
            requested=True,
            auto_maintenance=False,
            environ=env,
        )
    except Exception:
        return None
    return (
        result
        if result.ready
        and result.repo_head_sha == repo_head_sha
        and result.generation_id
        and result.freshness_receipt_digest
        else None
    )


def _result_from_owner(owner: Any, *, status: str, maintenance: bool, **ids: str):
    return StartOperationsHoloRepairResult(
        True,
        status,
        repo_head_sha=str(owner.repo_head_sha),
        generation_id=str(owner.generation_id),
        freshness_receipt_digest=str(owner.freshness_receipt_digest),
        maintenance_performed=maintenance,
        **ids,
    )


def _verified_execution(
    execution: Mapping[str, Any],
    *,
    owner: Any,
    repo_head_sha: str,
    task_id: str,
    repair_request_id: str,
) -> bool:
    structured = execution.get("structured_result")
    proof = structured if isinstance(structured, Mapping) else {}
    return bool(
        execution.get("ok") is True
        and execution.get("executor") == "startup:holo_index"
        and proof.get("ready") is True
        and proof.get("repo_head_sha") == repo_head_sha
        and proof.get("repair_task_id") == task_id
        and proof.get("repair_request_id") == repair_request_id
        and owner is not None
        and proof.get("generation_id") == owner.generation_id
        and proof.get("freshness_receipt_digest")
        == owner.freshness_receipt_digest
    )


def _execution_refreshed(execution: Mapping[str, Any]) -> bool:
    structured = execution.get("structured_result")
    return bool(
        isinstance(structured, Mapping)
        and structured.get("refreshed") is True
    )


def repair_start_operations_holoindex(
    *,
    repo_root: Path | str,
    repo_head_sha: str,
    control_request_id: str,
    environ: Mapping[str, str],
    db: Any | None = None,
    ensure_operational: Callable[..., Any] | None = None,
    task_executor: Callable[..., Mapping[str, Any]] | None = None,
) -> StartOperationsHoloRepairResult:
    """Restore one exact-HEAD owner through a durable OpenClaw task."""

    root = Path(repo_root).resolve(strict=False)
    try:
        db, ensure_operational = runtime_dependencies(db, ensure_operational)
    except Exception:
        return _rejected("holo_repair_runtime_dependencies_unavailable")
    owner = _current_owner(root, repo_head_sha, environ, ensure_operational)
    if owner is not None:
        return _result_from_owner(owner, status="OWNER_READY", maintenance=False)
    return _run_repair(
        root=root, repo_head_sha=repo_head_sha,
        control_request_id=control_request_id, environ=environ, db=db,
        ensure_operational=ensure_operational, task_executor=task_executor,
    )


def _run_repair(
    *,
    root: Path,
    repo_head_sha: str,
    control_request_id: str,
    environ: Mapping[str, str],
    db: Any,
    ensure_operational: Callable[..., Any],
    task_executor: Callable[..., Mapping[str, Any]] | None,
) -> StartOperationsHoloRepairResult:
    task_id, context, task_error = prepare_task(
        root=root, repo_head_sha=repo_head_sha,
        control_request_id=control_request_id, db=db,
    )
    if task_error:
        return _rejected(task_error, task_id=task_id)
    execution = execute_repair(
        root=root, task_id=task_id, db=db, task_executor=task_executor)
    if execution is None:
        return _rejected(
            "holo_repair_task_claim_rejected", status="DEFERRED", task_id=task_id
        )
    owner = _current_owner(root, repo_head_sha, environ, ensure_operational)
    repair_id = str(context["repair_request_id"])
    if not _verified_execution(
        execution,
        owner=owner,
        repo_head_sha=repo_head_sha,
        task_id=task_id,
        repair_request_id=repair_id,
    ):
        return _rejected(
            "holo_repair_operational_proof_invalid",
            status="FAILED",
            task_id=task_id,
            repair_request_id=repair_id,
            repo_head_sha=repo_head_sha,
            maintenance_performed=_execution_refreshed(execution),
        )
    return _result_from_owner(
        owner,
        status="REPAIRED",
        maintenance=_execution_refreshed(execution),
        task_id=task_id,
        repair_request_id=repair_id,
    )


def _rejected(
    reason: str,
    *,
    status: str = "REJECTED",
    **values: Any,
) -> StartOperationsHoloRepairResult:
    return StartOperationsHoloRepairResult(
        False, status, rejection_reasons=(reason,), **values
    )


__all__ = [
    "SCHEMA_VERSION",
    "SOURCE",
    "TASK_PREFIX",
    "StartOperationsHoloRepairResult",
    "repair_start_operations_holoindex",
    "repairable_grounding_failure",
    "validate_holo_repair_task_binding",
]
