"""Run one scheduled, read-only FoundUp resident reconciliation cycle.

Cadence ownership stays in idle_automation. This adapter consumes one already
claimed window, authenticated host identity/scope and the canonical resident
RedDog client. It performs no Gmail/LinkedIn mutation, shell, repository write,
worktree, PR, merge or arbitrary command execution.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.reddog_resident_architect_client import (
    RedDogResidentArchitectClient,
)
from modules.communication.moltbot_bridge.src.reddog_resident_foundup_memex_config import (
    build_resident_foundup_memex_supply_config,
)
from modules.communication.moltbot_bridge.src.reddog_resident_memory_context import (
    resident_breadcrumbs_from_runtime,
    resident_brain_state_from_artifacts,
    resident_workspace_memory_notes_from_env,
)
from modules.communication.moltbot_bridge.src.reddog_resident_model_runtime_bindings import (
    load_resident_model_runtime_bindings,
)
from modules.communication.moltbot_bridge.src.reddog_transport_neutral_grounding_service import (
    ground_transport_work_focus,
)

SCHEDULED_RESIDENT_RESULT_SCHEMA = "reddog_scheduled_resident_reconcile.v1"
SCHEDULED_RESIDENT_ROUTINE = "resident_reconcile"
SCHEDULED_RESIDENT_CADENCE = "daily"


def run_scheduled_resident_reconcile(
    claim: Any,
    *,
    repo_root: Path | str,
    environ: Mapping[str, str] | None = None,
    client_factory: Any = RedDogResidentArchitectClient,
    grounding_service: Any = ground_transport_work_focus,
) -> Mapping[str, Any]:
    env = os.environ if environ is None else environ
    reasons = _claim_rejections(claim)
    principal = str(env.get("REDDOG_AUTHENTICATED_PRINCIPAL_ID") or "").strip()
    scope = _authorized_foundups(env)
    configured_foundup = str(
        env.get("REDDOG_SCHEDULED_RESIDENT_FOUNDUP_ID") or ""
    ).strip()
    foundup_id = configured_foundup or (scope[0] if len(scope) == 1 else "")
    work_focus = str(
        env.get("REDDOG_SCHEDULED_RESIDENT_WORK_FOCUS") or ""
    ).strip()

    if not principal:
        reasons.append("authenticated_principal_missing")
    if len(scope) != 1:
        reasons.append("scheduled_resident_requires_exactly_one_foundup")
    if not foundup_id or foundup_id not in scope:
        reasons.append("scheduled_resident_foundup_scope_mismatch")
    if not work_focus:
        reasons.append("scheduled_resident_work_focus_missing")
    if reasons:
        return _result(False, claim, reasons=reasons)

    audit_binding, architect_binding, binding_reason = (
        load_resident_model_runtime_bindings(repo_root, environ=env)
    )
    if binding_reason:
        return _result(False, claim, reasons=(binding_reason,))

    brain = resident_brain_state_from_artifacts(env)
    breadcrumbs = resident_breadcrumbs_from_runtime(
        work_focus=work_focus,
        foundup_id=foundup_id,
        environ=env,
    )
    workspace_notes = resident_workspace_memory_notes_from_env(env)
    if not isinstance(brain, Mapping) or brain.get("available") is not True:
        return _result(False, claim, reasons=("resident_brain_context_unavailable",))
    if not breadcrumbs:
        return _result(False, claim, reasons=("resident_breadcrumbs_context_unavailable",))

    try:
        memex_config = build_resident_foundup_memex_supply_config(
            repo_root=repo_root,
            foundup_id=foundup_id,
            principal_id=principal,
            max_records=_positive_int(
                env.get("REDDOG_RESIDENT_MEMORY_MAX_RECORDS"), default=32
            ),
        )
    except (OSError, TypeError, ValueError) as exc:
        return _result(
            False,
            claim,
            reasons=(f"resident_foundup_memex_config_rejected:{exc}",),
        )

    request_id = _request_id(claim, foundup_id, principal, work_focus)
    try:
        grounded = grounding_service(
            repo_root=repo_root,
            work_focus=work_focus,
            foundup_id=foundup_id,
            authenticated_principal_id=principal,
            source_surface="api_thin_client",
            client_request_id=request_id,
        )
    except Exception:
        return _result(False, claim, reasons=("resident_grounding_failed",))
    if not grounded.accepted:
        return _result(
            False,
            claim,
            reasons=("resident_grounding_rejected", *grounded.rejection_reasons),
        )

    runtime_defaults = {
        "breadcrumbs": breadcrumbs,
        "brain_state": brain,
        "workspace_memory_notes": workspace_notes,
        "memex_snapshot_supply_config": memex_config,
        "audit_model_runtime_binding_receipt": audit_binding,
        "architect_model_runtime_binding_receipt": architect_binding,
        "requested_operation": "scheduled_resident_reconcile",
        "prompt_text": work_focus,
        "max_claims": _positive_int(
            env.get("REDDOG_SCHEDULED_RESIDENT_MAX_CLAIMS"), default=8
        ),
        "timeout_seconds": _positive_int(
            env.get("REDDOG_SCHEDULED_RESIDENT_TIMEOUT_SECONDS"), default=60
        ),
    }
    try:
        client = client_factory(
            repo_root=repo_root,
            authenticated_principal_id=principal,
            authorized_foundup_ids=scope,
            transport="api",
            runtime_defaults=runtime_defaults,
        )
        response = client.submit(grounded.intent)
    except Exception:
        return _result(False, claim, reasons=("resident_client_failed",))

    safe = bool(
        response.accepted
        and response.read_only_authority_only
        and response.client_no_shell_command_executed
        and response.client_no_repo_mutation_performed
        and response.client_no_holoindex_reindex_performed
        and response.client_no_hermes_execution_performed
        and response.client_no_worktree_operation_performed
        and response.client_no_pr_created
        and response.client_no_merge_performed
    )
    reasons = () if safe else tuple(response.rejection_reasons) or (
        "resident_readonly_boundary_rejected",
    )
    return _result(
        safe,
        claim,
        reasons=reasons,
        foundup_id=foundup_id,
        request_id=request_id,
        response=response.to_dict(),
        brain_record_count=int(brain.get("record_count") or 0),
        breadcrumb_count=len(breadcrumbs),
        workspace_note_count=len(workspace_notes),
        memex_configured=True,
    )


def _claim_rejections(claim: Any) -> list[str]:
    reasons: list[str] = []
    if str(getattr(claim, "routine", "") or "") != SCHEDULED_RESIDENT_ROUTINE:
        reasons.append("scheduled_resident_routine_invalid")
    if str(getattr(claim, "cadence", "") or "") != SCHEDULED_RESIDENT_CADENCE:
        reasons.append("scheduled_resident_cadence_invalid")
    for field in (
        "schedule_id", "execution_id", "window_start", "window_end", "token"
    ):
        if not str(getattr(claim, field, "") or "").strip():
            reasons.append(f"scheduled_resident_claim_{field}_missing")
    return reasons


def _authorized_foundups(env: Mapping[str, str]) -> tuple[str, ...]:
    raw = str(env.get("REDDOG_AUTHORIZED_FOUNDUP_IDS") or "")
    values = tuple(
        item.strip() for item in raw.split(",") if item.strip()
    )
    return tuple(dict.fromkeys(values))


def _request_id(claim: Any, foundup_id: str, principal: str, work_focus: str) -> str:
    payload = {
        "schedule_id": str(getattr(claim, "schedule_id", "") or ""),
        "execution_id": str(getattr(claim, "execution_id", "") or ""),
        "window_start": str(getattr(claim, "window_start", "") or ""),
        "window_end": str(getattr(claim, "window_end", "") or ""),
        "foundup_id": foundup_id,
        "principal": principal,
        "work_focus": work_focus,
    }
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return "scheduled-resident:" + digest


def _positive_int(value: Any, *, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def _result(
    success: bool,
    claim: Any,
    *,
    reasons: Any = (),
    foundup_id: str = "",
    request_id: str = "",
    response: Mapping[str, Any] | None = None,
    brain_record_count: int = 0,
    breadcrumb_count: int = 0,
    workspace_note_count: int = 0,
    memex_configured: bool = False,
) -> Mapping[str, Any]:
    body = {
        "schema_version": SCHEDULED_RESIDENT_RESULT_SCHEMA,
        "success": bool(success),
        "routine": str(getattr(claim, "routine", "") or ""),
        "cadence": str(getattr(claim, "cadence", "") or ""),
        "schedule_id": str(getattr(claim, "schedule_id", "") or ""),
        "execution_id": str(getattr(claim, "execution_id", "") or ""),
        "window_start": str(getattr(claim, "window_start", "") or ""),
        "window_end": str(getattr(claim, "window_end", "") or ""),
        "foundup_id": foundup_id,
        "request_id": request_id,
        "resident_response": dict(response or {}),
        "brain_record_count": int(brain_record_count),
        "breadcrumb_count": int(breadcrumb_count),
        "workspace_note_count": int(workspace_note_count),
        "foundup_memex_configured": bool(memex_configured),
        "rejection_reasons": list(dict.fromkeys(str(x) for x in reasons if str(x))),
        "read_only_cycle": True,
        "no_gmail_mutation_performed": True,
        "no_linkedin_mutation_performed": True,
        "no_external_publication_performed": True,
        "no_shell_command_executed": True,
        "no_repo_mutation_performed": True,
        "no_worktree_operation_performed": True,
        "no_pr_created": True,
        "no_merge_performed": True,
    }
    return {
        **body,
        "receipt_id": "sha256:"
        + hashlib.sha256(
            json.dumps(
                body, sort_keys=True, separators=(",", ":"), default=str
            ).encode("utf-8")
        ).hexdigest(),
    }


__all__ = [
    "SCHEDULED_RESIDENT_CADENCE",
    "SCHEDULED_RESIDENT_RESULT_SCHEMA",
    "SCHEDULED_RESIDENT_ROUTINE",
    "run_scheduled_resident_reconcile",
]
