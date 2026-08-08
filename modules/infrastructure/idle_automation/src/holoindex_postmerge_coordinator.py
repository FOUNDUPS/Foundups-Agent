"""Durable exact-SHA HoloIndex maintenance coordination.

The coordinator is a WRE-owned control-plane adapter. It detects the current
``origin/main`` SHA, creates one idempotent AgentDB maintenance task for that
SHA, and lets OpenClaw execute the existing trusted HoloIndex maintenance
handshake in a dedicated clean authority worktree.

It never indexes during a query and never creates an authority worktree.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Mapping

from .holoindex_postmerge_contract import (
    ASSIGNMENT_LEASE_SECONDS,
    AUTHORITY_REPO_ROOT_ENV,
    CLAIM_AGENT_ID,
    COMPLETION_EVENT_PREFIX,
    MAX_RETRIES,
    REQUEST_EVENT_PREFIX,
    RETRY_DELAY_SECONDS,
    SCHEMA_VERSION,
    SOURCE,
    TASK_PREFIX,
    AgentDbPort,
    GitRunner,
    HoloIndexPostMergeCoordinationResult,
    _authority_root,
    _default_git_runner,
    _event_payload,
    _event_payload_valid,
    _fetch_origin_main,
    _load_db,
    normalize_holoindex_incident_binding,
    _validate_authority_root,
)


def _utc_now() -> datetime:
    return datetime.now(UTC)


def coordinate_holoindex_postmerge(
    *,
    repo_root: Path | str,
    db: AgentDbPort | None = None,
    environment: Mapping[str, str] | None = None,
    git_runner: GitRunner = _default_git_runner,
    now: Callable[[], datetime] = _utc_now,
    prove_operational: Callable[..., Any] | None = None,
    incident_binding: Mapping[str, Any] | None = None,
) -> HoloIndexPostMergeCoordinationResult:
    """Queue or reconcile one exact-``origin/main`` maintenance task."""

    workspace = Path(repo_root).resolve(strict=False)
    env = os.environ if environment is None else environment
    authority, authority_error = _authority_root(workspace, env)
    if authority is None:
        return HoloIndexPostMergeCoordinationResult(
            False, "REJECTED", rejection_reasons=(authority_error,)
        )
    authority_digest, authority_reasons = _validate_authority_root(
        workspace, authority, git_runner
    )
    if authority_reasons:
        return HoloIndexPostMergeCoordinationResult(
            False,
            "REJECTED",
            rejection_reasons=authority_reasons,
        )
    target_sha, target_error = _fetch_origin_main(git_runner, authority)
    if target_error:
        return HoloIndexPostMergeCoordinationResult(
            False,
            "REJECTED",
            authority_root_digest=authority_digest,
            rejection_reasons=(target_error,),
        )
    normalized_incident = None
    if incident_binding is not None:
        normalized_incident = normalize_holoindex_incident_binding(
            incident_binding, target_sha
        )
        if normalized_incident is None:
            return HoloIndexPostMergeCoordinationResult(
                False, "REJECTED", target_repo_head_sha=target_sha,
                authority_root_digest=authority_digest,
                rejection_reasons=("incident_binding_invalid",),
            )

    database = _load_db(db)
    task_id = TASK_PREFIX + target_sha
    request_event_id = REQUEST_EVENT_PREFIX + target_sha
    completion_event_id = COMPLETION_EVENT_PREFIX + target_sha
    completion = database.get_coordination_event_by_id(completion_event_id)
    if completion is not None:
        if not _event_payload_valid(
            completion,
            target_repo_head_sha=target_sha,
            authority_root_digest=authority_digest,
                expected_status="COMPLETED",
                expected_incident_binding=normalized_incident,
        ):
            return HoloIndexPostMergeCoordinationResult(
                False,
                "REJECTED",
                target_repo_head_sha=target_sha,
                task_id=task_id,
                authority_root_digest=authority_digest,
                rejection_reasons=("completion_event_invalid",),
            )
        task = database.get_autonomous_task_by_id(task_id)
        request = database.get_coordination_event_by_id(request_event_id)
        if (
            task is None
            or str(task.get("status") or "") != "completed"
            or str(task.get("assigned_to") or "") != CLAIM_AGENT_ID
            or not _event_payload_valid(
                request,
                target_repo_head_sha=target_sha,
                authority_root_digest=authority_digest,
                expected_status="REQUESTED",
                expected_incident_binding=normalized_incident,
            )
            or str(request.get("resolution_status") or "") != "completed"
        ):
            return HoloIndexPostMergeCoordinationResult(
                False,
                "REJECTED",
                target_repo_head_sha=target_sha,
                task_id=task_id,
                authority_root_digest=authority_digest,
                rejection_reasons=("completion_transaction_incomplete",),
            )
        payload = completion["payload"]
        from holo_index.storage_contract import resolve_holoindex_ssd_path

        if prove_operational is None:
            from holo_index.query_admission import (
                rehydrate_canonical_freshness_proof,
            )

            prove_operational = rehydrate_canonical_freshness_proof
        ssd_path = resolve_holoindex_ssd_path(environ=env)
        proof = prove_operational(
            repo_root=authority,
            ssd_path=ssd_path,
            expected_repo_head_sha=target_sha,
        )
        proof_binding = getattr(proof, "binding", {})
        binding = proof_binding if isinstance(proof_binding, Mapping) else {}
        if (
            getattr(proof, "allowed", False) is not True
            or binding.get("repo_head_sha") != target_sha
            or binding.get("freshness_generation_id")
            != payload.get("generation_id")
            or binding.get("freshness_receipt_digest")
            != payload.get("freshness_receipt_digest")
        ):
            return HoloIndexPostMergeCoordinationResult(
                False,
                "REJECTED",
                target_repo_head_sha=target_sha,
                task_id=task_id,
                authority_root_digest=authority_digest,
                rejection_reasons=("completion_operational_proof_invalid",),
            )
        return HoloIndexPostMergeCoordinationResult(
            True,
            "CURRENT",
            target_repo_head_sha=target_sha,
            task_id=task_id,
            authority_root_digest=authority_digest,
            generation_id=str(payload.get("generation_id") or ""),
            freshness_receipt_digest=str(
                payload.get("freshness_receipt_digest") or ""
            ),
        )

    request = database.get_coordination_event_by_id(request_event_id)
    if request is None:
        request_payload = _event_payload(
            target_repo_head_sha=target_sha,
            authority_root_digest=authority_digest,
            status="REQUESTED",
            incident_binding=normalized_incident,
        )
        if not database.create_coordination_event(
            request_event_id,
            "holoindex_postmerge_maintenance",
            "wre",
            ["openclaw_supervisor"],
            request_payload,
        ):
            request = database.get_coordination_event_by_id(request_event_id)
            if not _event_payload_valid(
                request,
                target_repo_head_sha=target_sha,
                authority_root_digest=authority_digest,
                expected_status="REQUESTED",
                expected_incident_binding=normalized_incident,
            ):
                return HoloIndexPostMergeCoordinationResult(
                    False,
                    "REJECTED",
                    target_repo_head_sha=target_sha,
                    task_id=task_id,
                    authority_root_digest=authority_digest,
                    rejection_reasons=("request_event_conflict",),
                )
    elif not _event_payload_valid(
        request,
        target_repo_head_sha=target_sha,
        authority_root_digest=authority_digest,
        expected_status="REQUESTED",
        expected_incident_binding=normalized_incident,
    ):
        return HoloIndexPostMergeCoordinationResult(
            False,
            "REJECTED",
            target_repo_head_sha=target_sha,
            task_id=task_id,
            authority_root_digest=authority_digest,
            rejection_reasons=("request_event_invalid",),
        )

    task = database.get_autonomous_task_by_id(task_id)
    if task is None:
        context = {
            "schema_version": SCHEMA_VERSION,
            "source": SOURCE,
            "target_repo_head_sha": target_sha,
            "authority_root_digest": authority_digest,
            "request_event_id": request_event_id,
            "retry_count": 0,
        }
        if normalized_incident is not None:
            context["incident_binding"] = normalized_incident
        created = database.create_holoindex_postmerge_task_if_absent(
            task_id=task_id,
            description=f"Refresh canonical HoloIndex for origin/main {target_sha}",
            required_skills=["holo-search"],
            estimated_complexity=3.0,
            priority_score=19.0,
            context=context,
        )
        if not created:
            task = database.get_autonomous_task_by_id(task_id)
            if task is None:
                return HoloIndexPostMergeCoordinationResult(
                    False,
                    "REJECTED",
                    target_repo_head_sha=target_sha,
                    task_id=task_id,
                    authority_root_digest=authority_digest,
                    rejection_reasons=("maintenance_task_create_failed",),
                )
        status = "QUEUED" if created else str(task.get("status") or "pending").upper()
    if task is not None:
        status = str(task.get("status") or "pending")
        context = task.get("context")
        if (
            not isinstance(context, Mapping)
            or context.get("target_repo_head_sha") != target_sha
            or context.get("authority_root_digest") != authority_digest
            or context.get("source") != SOURCE
            or (
                normalized_incident is not None
                and context.get("incident_binding") != normalized_incident
            )
        ):
            return HoloIndexPostMergeCoordinationResult(
                False,
                "REJECTED",
                target_repo_head_sha=target_sha,
                task_id=task_id,
                authority_root_digest=authority_digest,
                rejection_reasons=("maintenance_task_binding_invalid",),
            )
        retry_count = int(context.get("retry_count") or 0)
        if status in {"assigned", "executing"}:
            assigned_at_raw = str(task.get("assigned_at") or "")
            try:
                assigned_at = datetime.fromisoformat(
                    assigned_at_raw.replace("Z", "+00:00")
                )
                if assigned_at.tzinfo is None:
                    assigned_at = assigned_at.replace(tzinfo=UTC)
                lease_expired = now() >= assigned_at + timedelta(
                    seconds=ASSIGNMENT_LEASE_SECONDS
                )
            except ValueError:
                lease_expired = True
            if lease_expired:
                reclaimed = database.reclaim_expired_holoindex_postmerge_task(
                    task_id,
                    CLAIM_AGENT_ID,
                    expected_assigned_at=assigned_at_raw,
                )
                if reclaimed:
                    status = "failed"
                else:
                    concurrent = database.get_autonomous_task_by_id(task_id)
                    concurrent_status = str(
                        (concurrent or {}).get("status") or ""
                    )
                    if concurrent_status not in {
                        "failed",
                        "pending",
                        "retry_wait",
                        "completed",
                    }:
                        return HoloIndexPostMergeCoordinationResult(
                            False,
                            "REJECTED",
                            target_repo_head_sha=target_sha,
                            task_id=task_id,
                            authority_root_digest=authority_digest,
                            rejection_reasons=(
                                "maintenance_assignment_reclaim_failed",
                            ),
                        )
                    status = concurrent_status
        if status == "failed":
            if retry_count >= MAX_RETRIES:
                return HoloIndexPostMergeCoordinationResult(
                    False,
                    "RETRY_EXHAUSTED",
                    target_repo_head_sha=target_sha,
                    task_id=task_id,
                    authority_root_digest=authority_digest,
                    rejection_reasons=("maintenance_retry_exhausted",),
                )
            retry_at = now() + timedelta(seconds=RETRY_DELAY_SECONDS)
            retry_context = dict(context)
            retry_context["retry_count"] = retry_count + 1
            retry_context["retry_not_before"] = retry_at.isoformat()
            if not database.schedule_holoindex_postmerge_task_retry(
                task_id,
                context=retry_context,
                retry_not_before=retry_at.isoformat(),
            ):
                concurrent = database.get_autonomous_task_by_id(task_id)
                if not concurrent or concurrent.get("status") != "retry_wait":
                    return HoloIndexPostMergeCoordinationResult(
                        False,
                        "REJECTED",
                        target_repo_head_sha=target_sha,
                        task_id=task_id,
                        authority_root_digest=authority_digest,
                        rejection_reasons=("maintenance_retry_schedule_failed",),
                    )
            status = "RETRY_WAIT"
        elif status == "retry_wait":
            raw_retry = str(context.get("retry_not_before") or "")
            try:
                retry_at = datetime.fromisoformat(raw_retry.replace("Z", "+00:00"))
                if retry_at.tzinfo is None:
                    retry_at = retry_at.replace(tzinfo=UTC)
            except ValueError:
                return HoloIndexPostMergeCoordinationResult(
                    False,
                    "REJECTED",
                    target_repo_head_sha=target_sha,
                    task_id=task_id,
                    authority_root_digest=authority_digest,
                    rejection_reasons=("retry_schedule_invalid",),
                )
            if now() >= retry_at:
                if not database.requeue_holoindex_postmerge_task(
                    task_id,
                    expected_status="retry_wait",
                ):
                    concurrent = database.get_autonomous_task_by_id(task_id)
                    if not concurrent or concurrent.get("status") != "pending":
                        return HoloIndexPostMergeCoordinationResult(
                            False,
                            "REJECTED",
                            target_repo_head_sha=target_sha,
                            task_id=task_id,
                            authority_root_digest=authority_digest,
                            rejection_reasons=("maintenance_requeue_failed",),
                        )
                status = "REQUEUED"
            else:
                status = "RETRY_WAIT"
        elif status == "completed":
            status = "WAITING_COMPLETION_RECEIPT"
        else:
            status = status.upper()

    return HoloIndexPostMergeCoordinationResult(
        True,
        status,
        target_repo_head_sha=target_sha,
        task_id=task_id,
        authority_root_digest=authority_digest,
    )


def execute_holoindex_postmerge_task(
    *,
    repo_root: Path | str,
    task_id: str,
    context: Mapping[str, Any],
    execution_claim: Mapping[str, str] | None = None,
    db: AgentDbPort | None = None,
    environment: Mapping[str, str] | None = None,
    authority_transaction: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """Compatibility import for the separately owned effect adapter."""
    from .holoindex_postmerge_executor import (
        execute_holoindex_postmerge_task as execute,
    )

    return execute(
        repo_root=repo_root,
        task_id=task_id,
        context=context,
        execution_claim=execution_claim,
        db=db,
        environment=environment,
        authority_transaction=authority_transaction,
    )


__all__ = [
    "AUTHORITY_REPO_ROOT_ENV",
    "COMPLETION_EVENT_PREFIX",
    "HoloIndexPostMergeCoordinationResult",
    "REQUEST_EVENT_PREFIX",
    "SCHEMA_VERSION",
    "SOURCE",
    "TASK_PREFIX",
    "coordinate_holoindex_postmerge",
    "execute_holoindex_postmerge_task",
]
