"""Trusted execution adapter for exact-SHA post-merge HoloIndex maintenance."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Callable, Mapping

from holo_index.authority_worktree import resolve_holoindex_runtime_root

from .holoindex_postmerge_contract import (
    CLAIM_AGENT_ID,
    COMPLETION_EVENT_PREFIX,
    REQUEST_EVENT_PREFIX,
    SCHEMA_VERSION,
    SOURCE,
    TASK_PREFIX,
    AgentDbPort,
    _authority_root,
    _event_payload,
    _event_payload_valid,
    _load_db,
    _SHA_RE,
)


EXECUTOR_ID = "wre:holoindex_postmerge"


def _result(
    *,
    ok: bool,
    detail: str,
    structured_result: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "ok": ok,
        "detail": detail[:1000],
        "executor": EXECUTOR_ID,
        "structured_result": dict(structured_result),
        "finalization_owned": True,
    }


def _validate_task_binding(
    task_id: str,
    context: Mapping[str, Any],
) -> tuple[str, str]:
    target_sha = str(context.get("target_repo_head_sha") or "").lower()
    valid = (
        context.get("schema_version") == SCHEMA_VERSION
        and context.get("source") == SOURCE
        and _SHA_RE.fullmatch(target_sha) is not None
        and task_id == TASK_PREFIX + target_sha
    )
    return target_sha, "" if valid else "postmerge_task_binding_invalid"


def _fail_claimed_task(
    database: AgentDbPort,
    *,
    task_id: str,
    context: Mapping[str, Any],
    status: str,
    reasons: list[str],
    superseded_by: str = "",
) -> dict[str, Any]:
    finalized = database.fail_holoindex_postmerge_task(
        task_id,
        CLAIM_AGENT_ID,
        claim_id=str(context.get("claim_id") or ""),
        claim_binding_digest=str(
            context.get("claim_binding_digest") or ""
        ),
        status=status,
    )
    normalized = reasons or ["postmerge_unknown_failure"]
    if not finalized:
        normalized.append("task_failure_finalization_failed")
    structured = {
        "ready": False,
        "status": status.upper(),
        "rejection_reasons": normalized,
    }
    if superseded_by:
        structured["superseded_by"] = superseded_by
    return _result(
        ok=False,
        detail=",".join(normalized),
        structured_result=structured,
    )


def _validate_request_event(
    *,
    database: AgentDbPort,
    context: Mapping[str, Any],
    target_sha: str,
    authority_digest: str,
) -> tuple[str, str]:
    request_event_id = str(context.get("request_event_id") or "")
    if request_event_id != REQUEST_EVENT_PREFIX + target_sha:
        return "", "request_event_binding_invalid"
    request_event = database.get_coordination_event_by_id(request_event_id)
    if not _event_payload_valid(
        request_event,
        target_repo_head_sha=target_sha,
        authority_root_digest=authority_digest,
        expected_status="REQUESTED",
    ):
        return "", "request_event_invalid"
    payload = request_event.get("payload")
    return str(payload.get("payload_digest") or ""), ""


def _persist_completion(
    *,
    database: AgentDbPort,
    task_id: str,
    context: Mapping[str, Any],
    target_sha: str,
    authority_digest: str,
    transaction_result: Any,
) -> tuple[str, str]:
    request_digest, request_error = _validate_request_event(
        database=database,
        context=context,
        target_sha=target_sha,
        authority_digest=authority_digest,
    )
    if request_error:
        return "", request_error
    completion_payload = _event_payload(
        target_repo_head_sha=target_sha,
        authority_root_digest=authority_digest,
        status="COMPLETED",
        generation_id=transaction_result.generation_id,
        freshness_receipt_digest=transaction_result.freshness_receipt_digest,
    )
    completion_event_id = COMPLETION_EVENT_PREFIX + target_sha
    committed = database.commit_holoindex_postmerge_completion(
        task_id=task_id,
        agent_id=CLAIM_AGENT_ID,
        request_event_id=REQUEST_EVENT_PREFIX + target_sha,
        request_payload_digest=request_digest,
        completion_event_id=completion_event_id,
        completion_payload=completion_payload,
        claim_id=str(context.get("claim_id") or ""),
        claim_binding_digest=str(
            context.get("claim_binding_digest") or ""
        ),
    )
    return (
        (completion_event_id, "")
        if committed
        else ("", "completion_transaction_failed")
    )


def _run_authority_transaction(
    *,
    authority_transaction: Callable[..., Any] | None,
    workspace: Path,
    authority: Path,
    target_sha: str,
    authority_digest: str,
    env: Mapping[str, str],
) -> tuple[Any | None, str]:
    """Resolve the dependency root and enter the sealed authority boundary."""
    if authority_transaction is None:
        from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_authority_transaction import (
            advance_reddog_holoindex_authority,
        )

        authority_transaction = advance_reddog_holoindex_authority
    try:
        runtime_root = resolve_holoindex_runtime_root(workspace)
    except (OSError, RuntimeError, ValueError):
        return None, "postmerge_runtime_root_resolution_failed"
    return authority_transaction(
        workspace_root=runtime_root,
        repo_root=authority,
        target_repo_head_sha=target_sha,
        expected_authority_root_digest=authority_digest,
        environ=env,
    ), ""


def _execute_holoindex_postmerge_task_for_test(
    *,
    repo_root: Path | str,
    task_id: str,
    context: Mapping[str, Any],
    execution_claim: Mapping[str, str] | None = None,
    db: AgentDbPort | None = None,
    environment: Mapping[str, str] | None = None,
    authority_transaction: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """Internal dependency seam; production callers use sealed defaults."""
    database = _load_db(db)
    workspace = Path(repo_root).resolve(strict=False)
    env = os.environ if environment is None else environment
    persisted = database.get_autonomous_task_by_id(task_id)
    persisted_context = (
        persisted.get("context") if isinstance(persisted, Mapping) else None
    )
    if (
        not isinstance(persisted_context, Mapping)
        or dict(persisted_context) != dict(context)
    ):
        return _result(
            ok=False,
            detail="postmerge_persisted_context_mismatch",
            structured_result={
                "ready": False,
                "status": "REJECTED",
                "rejection_reasons": [
                    "postmerge_persisted_context_mismatch"
                ],
            },
        )
    context = persisted_context
    claim = execution_claim if isinstance(execution_claim, Mapping) else {}
    if (
        str(claim.get("claim_id") or "")
        != str(context.get("claim_id") or "")
        or str(claim.get("claim_binding_digest") or "")
        != str(context.get("claim_binding_digest") or "")
    ):
        return _result(
            ok=False,
            detail="postmerge_execution_claim_missing_or_mismatched",
            structured_result={
                "ready": False,
                "status": "REJECTED",
                "rejection_reasons": [
                    "postmerge_execution_claim_missing_or_mismatched"
                ],
            },
        )
    target_sha, binding_error = _validate_task_binding(task_id, context)
    if binding_error:
        return _fail_claimed_task(
            database,
            task_id=task_id,
            context=context,
            status="failed",
            reasons=[binding_error],
        )
    authority, authority_error = _authority_root(workspace, env)
    authority_digest = str(context.get("authority_root_digest") or "")
    if authority is None:
        return _fail_claimed_task(
            database,
            task_id=task_id,
            context=context,
            status="failed",
            reasons=[authority_error],
        )
    if not authority_digest:
        return _fail_claimed_task(
            database,
            task_id=task_id,
            context=context,
            status="failed",
            reasons=["authority_root_digest_missing"],
        )

    _, request_error = _validate_request_event(
        database=database,
        context=context,
        target_sha=target_sha,
        authority_digest=authority_digest,
    )
    if request_error:
        return _fail_claimed_task(
            database,
            task_id=task_id,
            context=context,
            status="failed",
            reasons=[request_error],
        )
    claim_id = str(context.get("claim_id") or "")
    claim_binding_digest = str(context.get("claim_binding_digest") or "")
    if not database.start_holoindex_postmerge_execution(
        task_id,
        CLAIM_AGENT_ID,
        claim_id=claim_id,
        claim_binding_digest=claim_binding_digest,
    ):
        return _result(
            ok=False,
            detail="postmerge_execution_claim_rejected",
            structured_result={
                "ready": False,
                "status": "REJECTED",
                "rejection_reasons": [
                    "postmerge_execution_claim_rejected"
                ],
            },
        )

    transaction, transaction_setup_error = _run_authority_transaction(
        authority_transaction=authority_transaction, workspace=workspace,
        authority=authority, target_sha=target_sha,
        authority_digest=authority_digest, env=env,
    )
    if transaction_setup_error:
        return _fail_claimed_task(
            database, task_id=task_id, context=context, status="failed",
            reasons=[transaction_setup_error],
        )
    if not transaction.ready:
        status = "superseded" if transaction.status == "SUPERSEDED" else "failed"
        result = _fail_claimed_task(
            database,
            task_id=task_id,
            context=context,
            status=status,
            reasons=[transaction.error or "authority_transaction_failed"],
            superseded_by=str(transaction.observed_origin_main_sha or ""),
        )
        if (
            transaction.observed_origin_main_sha
            and transaction.observed_origin_main_sha != target_sha
        ):
            from .holoindex_postmerge_coordinator import (
                coordinate_holoindex_postmerge,
            )

            follow_up = coordinate_holoindex_postmerge(
                repo_root=workspace,
                db=database,
                environment=env,
            )
            result["structured_result"]["follow_up"] = follow_up.to_dict()
        return result

    completion_event_id, persistence_error = _persist_completion(
        database=database,
        task_id=task_id,
        context=context,
        target_sha=target_sha,
        authority_digest=authority_digest,
        transaction_result=transaction,
    )
    if persistence_error:
        return _fail_claimed_task(
            database,
            task_id=task_id,
            context=context,
            status="failed",
            reasons=[persistence_error],
        )

    structured = {
        "ready": True,
        "status": transaction.status,
        "refreshed": transaction.refreshed,
        "repo_head_sha": target_sha,
        "generation_id": transaction.generation_id,
        "freshness_receipt_digest": transaction.freshness_receipt_digest,
        "completion_event_id": completion_event_id,
    }
    return _result(
        ok=True,
        detail=json.dumps(structured, sort_keys=True),
        structured_result=structured,
    )


def execute_holoindex_postmerge_task(
    *,
    repo_root: Path | str,
    task_id: str,
    context: Mapping[str, Any],
    execution_claim: Mapping[str, str] | None = None,
    db: AgentDbPort | None = None,
    environment: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Execute one claimed task through sealed production dependencies."""

    return _execute_holoindex_postmerge_task_for_test(
        repo_root=repo_root,
        task_id=task_id,
        context=context,
        execution_claim=execution_claim,
        db=db,
        environment=environment,
    )


__all__ = [
    "CLAIM_AGENT_ID",
    "EXECUTOR_ID",
    "execute_holoindex_postmerge_task",
]
