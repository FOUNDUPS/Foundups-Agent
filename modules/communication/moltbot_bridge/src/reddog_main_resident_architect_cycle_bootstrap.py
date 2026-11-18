"""Main-host adapter for the canonical resident RedDog architect client."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping


@dataclass(frozen=True)
class MainResidentArchitectHooks:
    """Host-owned dependencies used by the resident bootstrap."""

    cycle_requested: Callable[[], bool]
    model_runtime_bindings: Callable[
        [Path],
        tuple[Mapping[str, Any] | None, Mapping[str, Any] | None, str],
    ]
    cycle_bucket: Callable[[], str]
    client_request_id: Callable[..., str]
    brain_state: Callable[[], Mapping[str, Any]]
    breadcrumbs: Callable[..., tuple[Mapping[str, Any], ...]]
    workspace_memory_notes: Callable[[], tuple[Mapping[str, Any], ...]]
    payload_digest: Callable[[Any], str]
    external_research_retriever: Callable[[], Any | None]
    positive_int_env: Callable[[str, int], int]
    auto_queue_profile: Callable[[Any], str]
    run_client: Callable[..., Any]


@dataclass(frozen=True)
class _AuthorizedScope:
    authenticated_principal: str
    authorized_foundups: tuple[str, ...]
    principal_ref: str
    foundup_id: str


@dataclass(frozen=True)
class _ResidentRequest:
    work_focus: str
    explicit_intent_id: str
    client_request_id: str
    memory_context: Mapping[str, Any]
    runtime_defaults: Mapping[str, Any]


def _require_authorized_runtime_scope(
    *,
    authenticated_principal: str,
    authorized_foundups: tuple[str, ...],
    foundup_id: str,
) -> None:
    normalized_principal = str(authenticated_principal or "").strip()
    normalized_foundup = str(foundup_id or "").strip()
    authorized_shape_valid = isinstance(authorized_foundups, tuple) and all(
        isinstance(value, str) and value == value.strip() and bool(value)
        for value in authorized_foundups
    )
    if (
        not normalized_principal
        or authenticated_principal != normalized_principal
        or not normalized_foundup
        or foundup_id != normalized_foundup
        or not authorized_shape_valid
        or len(set(authorized_foundups)) != len(authorized_foundups)
        or normalized_foundup not in authorized_foundups
    ):
        raise ValueError("resident_architect_authenticated_scope_missing_or_mismatched")


def _resident_client(
    *,
    repo_root: Path,
    authenticated_principal: str,
    foundup_id: str,
    runtime_defaults: Mapping[str, Any],
) -> Any:
    from modules.communication.moltbot_bridge.src.reddog_resident_architect_client import (
        RedDogResidentArchitectClient,
    )

    return RedDogResidentArchitectClient(
        repo_root=repo_root,
        authenticated_principal_id=authenticated_principal,
        authorized_foundup_ids=(foundup_id,),
        transport="main",
        runtime_defaults=runtime_defaults,
    )


def run_main_resident_client(
    *,
    repo_root: Path,
    authenticated_principal: str,
    authorized_foundups: tuple[str, ...],
    foundup_id: str,
    work_focus: str,
    client_request_id: str,
    explicit_intent_id: str,
    runtime_defaults: Mapping[str, Any],
    cancel_requested: bool,
    retry_requested: bool,
) -> Any:
    """Ground and route one main-host request through the canonical client."""

    _require_authorized_runtime_scope(
        authenticated_principal=authenticated_principal,
        authorized_foundups=authorized_foundups,
        foundup_id=foundup_id,
    )
    from modules.communication.moltbot_bridge.src.reddog_transport_neutral_grounding_service import (
        ground_transport_work_focus,
    )

    if cancel_requested and retry_requested:
        raise ValueError("resident_architect_cancel_retry_conflict")
    if (cancel_requested or retry_requested) and not explicit_intent_id:
        raise ValueError("resident_architect_control_intent_missing")
    if explicit_intent_id:
        client = _resident_client(
            repo_root=repo_root,
            authenticated_principal=authenticated_principal,
            foundup_id=foundup_id,
            runtime_defaults=runtime_defaults,
        )
        if cancel_requested:
            return client.cancel(explicit_intent_id)
        if retry_requested:
            return client.resume(explicit_intent_id)
        return client.status(explicit_intent_id)
    grounding = ground_transport_work_focus(
        repo_root=repo_root,
        work_focus=work_focus,
        foundup_id=foundup_id,
        authenticated_principal_id=authenticated_principal,
        source_surface="main_resident_host",
        client_request_id=client_request_id,
    )
    if not grounding.accepted:
        raise RuntimeError("grounding_rejected:" + ",".join(grounding.rejection_reasons))
    client = _resident_client(
        repo_root=repo_root,
        authenticated_principal=authenticated_principal,
        foundup_id=foundup_id,
        runtime_defaults=runtime_defaults,
    )
    return client.submit(grounding.intent)


def run_main_resident_architect_cycle_preflight(
    repo_root: Path,
    *,
    hooks: MainResidentArchitectHooks,
    logger: Any,
) -> bool:
    """Run one bounded resident cycle through the canonical client."""

    if not hooks.cycle_requested():
        logger.info("[REDDOG-RESIDENT-CYCLE] Startup preflight disabled")
        return True
    enforced = os.getenv("REDDOG_RESIDENT_ARCHITECT_DURABLE_CYCLE_ENFORCED", "0") != "0"
    audit_binding, architect_binding, binding_reason = hooks.model_runtime_bindings(repo_root)
    if binding_reason:
        log_binding_failure = logger.error if enforced else logger.warning
        log_binding_failure(
            "[REDDOG-RESIDENT-CYCLE] Runtime model binding preflight failed: %s",
            binding_reason,
        )
        status = "FAIL" if enforced else "WARN"
        print(f"[REDDOG-RESIDENT-CYCLE] preflight={status} reason={binding_reason}")
        return not enforced
    scope, scope_reason = _authorized_scope_from_env()
    if scope_reason:
        return _configuration_failure(scope_reason, enforced=enforced, logger=logger)
    assert scope is not None
    request = _resident_request_from_env(
        scope=scope,
        audit_binding=audit_binding,
        architect_binding=architect_binding,
        hooks=hooks,
    )
    try:
        result = _invoke_request(repo_root, scope=scope, request=request, hooks=hooks)
    except Exception as exc:
        logger.error("[REDDOG-RESIDENT-CYCLE] Startup runtime failed: %s", exc)
        if enforced:
            print(f"[REDDOG-RESIDENT-CYCLE] preflight=FAIL error={type(exc).__name__}")
            return False
        print(f"[REDDOG-RESIDENT-CYCLE] preflight=WARN error={type(exc).__name__}")
        return True
    return _report_result(
        result,
        request=request,
        enforced=enforced,
        auto_queue_profile=hooks.auto_queue_profile,
    )


def _authorized_scope_from_env() -> tuple[_AuthorizedScope | None, str]:
    authenticated = os.getenv("REDDOG_AUTHENTICATED_PRINCIPAL_ID", "").strip()
    authorized = tuple(
        item.strip()
        for item in os.getenv("REDDOG_AUTHORIZED_FOUNDUP_IDS", "").split(",")
        if item.strip()
    )
    principal_ref = (
        os.getenv("REDDOG_RESIDENT_ARCHITECT_PRINCIPAL_REF", "").strip()
        or authenticated
    )
    foundup_id = os.getenv("REDDOG_RESIDENT_ARCHITECT_FOUNDUP_ID", "").strip()
    if not foundup_id and len(authorized) == 1:
        foundup_id = authorized[0]
    if (
        not authenticated
        or not authorized
        or principal_ref != authenticated
        or foundup_id not in authorized
    ):
        return None, "resident_architect_authenticated_scope_missing_or_mismatched"
    return (
        _AuthorizedScope(
            authenticated_principal=authenticated,
            authorized_foundups=authorized,
            principal_ref=principal_ref,
            foundup_id=foundup_id,
        ),
        "",
    )


def _resident_request_from_env(
    *,
    scope: _AuthorizedScope,
    audit_binding: Mapping[str, Any] | None,
    architect_binding: Mapping[str, Any] | None,
    hooks: MainResidentArchitectHooks,
) -> _ResidentRequest:
    work_focus = os.getenv("REDDOG_RESIDENT_ARCHITECT_WORK_FOCUS", "").strip() or (
        "Audit modules/communication/moltbot_bridge/src/"
        "reddog_resident_architect_durable_agentdb_cycle.py for the main.py "
        "resident RedDog architect runtime."
    )
    explicit_intent_id = os.getenv("REDDOG_RESIDENT_ARCHITECT_INTENT_ID", "").strip()
    request_override = os.getenv(
        "REDDOG_RESIDENT_ARCHITECT_CLIENT_REQUEST_ID", ""
    ).strip()
    cycle_bucket = "" if request_override else hooks.cycle_bucket()
    client_request_id = hooks.client_request_id(
        principal_ref=scope.principal_ref,
        foundup_id=scope.foundup_id,
        work_focus=work_focus,
        cycle_bucket=cycle_bucket,
    )
    brain_state = hooks.brain_state()
    breadcrumbs = hooks.breadcrumbs(
        work_focus=work_focus,
        foundup_id=scope.foundup_id,
    )
    workspace_notes = hooks.workspace_memory_notes()
    memory_context = _memory_context(
        brain_state=brain_state,
        breadcrumbs=breadcrumbs,
        workspace_notes=workspace_notes,
        payload_digest=hooks.payload_digest,
    )
    runtime_defaults = _runtime_defaults(
        work_focus=work_focus,
        brain_state=brain_state,
        breadcrumbs=breadcrumbs,
        workspace_notes=workspace_notes,
        audit_binding=audit_binding,
        architect_binding=architect_binding,
        hooks=hooks,
    )
    return _ResidentRequest(
        work_focus=work_focus,
        explicit_intent_id=explicit_intent_id,
        client_request_id=client_request_id,
        memory_context=memory_context,
        runtime_defaults=runtime_defaults,
    )


def _runtime_defaults(
    *,
    work_focus: str,
    brain_state: Mapping[str, Any],
    breadcrumbs: tuple[Mapping[str, Any], ...],
    workspace_notes: tuple[Mapping[str, Any], ...],
    audit_binding: Mapping[str, Any] | None,
    architect_binding: Mapping[str, Any] | None,
    hooks: MainResidentArchitectHooks,
) -> Mapping[str, Any]:
    return {
        "work_state_path": os.getenv("REDDOG_AUTHORITATIVE_WORK_STATE_PATH", ""),
        "holoindex_receipt_path": os.getenv("HOLOINDEX_FRESHNESS_RECEIPT", ""),
        "holoindex_ssd_path": os.getenv("HOLOINDEX_SSD_PATH", ""),
        "requested_operation": "main_resident_architect_cycle",
        "prompt_text": work_focus,
        "breadcrumbs": breadcrumbs,
        "brain_state": brain_state,
        "workspace_memory_notes": workspace_notes,
        "external_research_retriever": hooks.external_research_retriever(),
        "audit_model_runtime_binding_receipt": audit_binding,
        "architect_model_runtime_binding_receipt": architect_binding,
        "max_claims": hooks.positive_int_env(
            "REDDOG_RESIDENT_ARCHITECT_MAX_CLAIMS", 8
        ),
        "timeout_seconds": hooks.positive_int_env(
            "REDDOG_RESIDENT_ARCHITECT_TIMEOUT_SECONDS", 60
        ),
    }


def _invoke_request(
    repo_root: Path,
    *,
    scope: _AuthorizedScope,
    request: _ResidentRequest,
    hooks: MainResidentArchitectHooks,
) -> Any:
    return hooks.run_client(
        repo_root=repo_root,
        authenticated_principal=scope.authenticated_principal,
        authorized_foundups=scope.authorized_foundups,
        foundup_id=scope.foundup_id,
        work_focus=request.work_focus,
        client_request_id=request.client_request_id,
        explicit_intent_id=request.explicit_intent_id,
        runtime_defaults=request.runtime_defaults,
        cancel_requested=os.getenv("REDDOG_RESIDENT_ARCHITECT_CANCEL", "0") != "0",
        retry_requested=os.getenv("REDDOG_RESIDENT_ARCHITECT_RETRY", "0") != "0",
    )


def _memory_context(
    *,
    brain_state: Mapping[str, Any],
    breadcrumbs: tuple[Mapping[str, Any], ...],
    workspace_notes: tuple[Mapping[str, Any], ...],
    payload_digest: Callable[[Any], str],
) -> Mapping[str, Any]:
    value = {
        "brain_available": bool(brain_state),
        "brain_record_count": int(brain_state.get("record_count", 0))
        if brain_state
        else 0,
        "breadcrumbs_count": len(breadcrumbs),
        "workspace_memory_notes_count": len(workspace_notes),
    }
    value["memory_context_digest"] = payload_digest(value)
    return value


def _configuration_failure(reason: str, *, enforced: bool, logger: Any) -> bool:
    logger.error("[REDDOG-RESIDENT-CYCLE] Startup runtime failed: %s", reason)
    if enforced:
        print(f"[REDDOG-RESIDENT-CYCLE] preflight=FAIL error={reason}")
        return False
    print(f"[REDDOG-RESIDENT-CYCLE] preflight=WARN error={reason}")
    return True


def _report_result(
    result: Any,
    *,
    request: _ResidentRequest,
    enforced: bool,
    auto_queue_profile: Callable[[Any], str],
) -> bool:
    reasons = ",".join(result.rejection_reasons) if result.rejection_reasons else "(none)"
    auto_fix = _auto_fix_handoff(result)
    queue_profile = auto_queue_profile(result) if result.operation == "submit" else ""
    print(
        f"[REDDOG-RESIDENT-CYCLE] preflight={'PASS' if result.accepted else 'WARN'} "
        f"status={result.status} intent={result.intent_id} cycle={result.cycle_id} "
        f"snapshot={result.snapshot_id or '(none)'} swarm={result.swarm_id or '(none)'} "
        f"tasks={len(result.task_ids)} completed={int(result.task_status_counts.get('completed', 0))} "
        f"claims={result.openclaw_claim_count} recovered={result.recovered_existing_cycle} "
        f"duplicate={result.duplicate_intent_reused} architect_action={result.architect_action or '(none)'} "
        f"architect_next_slice={result.architect_next_slice or '(none)'} "
        f"architect_determination={result.determination_id or '(none)'} "
        f"queue_candidates={result.queue_candidate_count} auto_fix_handoff={auto_fix} "
        f"auto_queue_profile={queue_profile or '(none)'} "
        f"brain_records={request.memory_context['brain_record_count']} "
        f"breadcrumbs={request.memory_context['breadcrumbs_count']} "
        f"workspace_memory={request.memory_context['workspace_memory_notes_count']} reasons={reasons}"
    )
    _report_runtime_boundary(result)
    if result.accepted:
        _persist_accepted_controls(result, auto_fix=auto_fix, queue_profile=queue_profile)
        return True
    if enforced:
        print(
            "[REDDOG-RESIDENT-CYCLE] Startup blocked by "
            "REDDOG_RESIDENT_ARCHITECT_DURABLE_CYCLE_ENFORCED=1"
        )
        return False
    return True


def _auto_fix_handoff(result: Any) -> bool:
    return bool(
        result.accepted
        and result.operation == "submit"
        and str(result.architect_action or "").strip().upper() == "FIX"
        and os.getenv("REDDOG_RESIDENT_ARCHITECT_AUTO_FIX_HANDOFF", "1") != "0"
        and "REDDOG_RESIDENT_FIX_PROMOTION_HANDOFF" not in os.environ
    )


def _report_runtime_boundary(result: Any) -> None:
    print(
        "[REDDOG-RESIDENT-CYCLE] "
        f"read_only_authority={result.read_only_authority_only} "
        f"no_shell={result.client_no_shell_command_executed} "
        f"no_repo_mutation={result.client_no_repo_mutation_performed} "
        f"no_holoindex_reindex={result.client_no_holoindex_reindex_performed} "
        f"no_hermes_dispatch={result.client_no_hermes_execution_performed} "
        f"no_worktree={result.client_no_worktree_operation_performed} "
        f"no_pr={result.client_no_pr_created} "
        "no_pattern_memory=True no_live_foundup_enqueue=True"
    )


def _persist_accepted_controls(
    result: Any,
    *,
    auto_fix: bool,
    queue_profile: str,
) -> None:
    os.environ["REDDOG_RESIDENT_ARCHITECT_INTENT_ID"] = result.intent_id
    if auto_fix:
        os.environ["REDDOG_RESIDENT_FIX_PROMOTION_HANDOFF"] = "1"
    if queue_profile:
        os.environ["REDDOG_RESIDENT_QUEUE_BINDING_PROFILE"] = queue_profile


__all__ = [
    "MainResidentArchitectHooks",
    "run_main_resident_architect_cycle_preflight",
    "run_main_resident_client",
]
