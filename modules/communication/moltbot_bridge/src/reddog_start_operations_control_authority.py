"""Authenticated scope, model bindings, and budgets for start operations."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

from modules.communication.moltbot_bridge.src.reddog_resident_model_runtime_bindings import (
    load_resident_model_runtime_bindings,
)
from modules.communication.moltbot_bridge.src.reddog_start_operations_profile import (
    StartOperationsProfile,
)


class StartOperationsRejected(ValueError):
    def __init__(self, reasons: Sequence[str]) -> None:
        self.reasons = tuple(str(reason) for reason in reasons if str(reason))
        super().__init__(",".join(self.reasons))


def authorized_scope(
    env: Mapping[str, str],
) -> tuple[str, tuple[str, ...], str]:
    principal = str(env.get("REDDOG_AUTHENTICATED_PRINCIPAL_ID") or "").strip()
    authorized = tuple(
        item.strip()
        for item in str(env.get("REDDOG_AUTHORIZED_FOUNDUP_IDS") or "").split(",")
        if item.strip()
    )
    foundup_id = str(env.get("REDDOG_RESIDENT_ARCHITECT_FOUNDUP_ID") or "").strip()
    if not foundup_id and len(authorized) == 1:
        foundup_id = authorized[0]
    if not principal or not authorized or foundup_id not in authorized:
        raise StartOperationsRejected(("start_operations_authenticated_scope_missing",))
    return principal, authorized, foundup_id


def load_bindings(
    repo_root: Path, env: Mapping[str, str]
) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
    audit, architect, reason = load_resident_model_runtime_bindings(
        repo_root, environ=env
    )
    if reason or audit is None or architect is None:
        raise StartOperationsRejected((reason or "model_runtime_binding_missing",))
    return audit, architect


def budgets(
    profile: StartOperationsProfile, env: Mapping[str, str]
) -> tuple[int, int]:
    max_claims = _bounded_int(
        env.get("REDDOG_START_OPERATIONS_MAX_CLAIMS"),
        profile.default_max_claims,
        profile.max_max_claims,
        "start_operations_max_claims_invalid",
    )
    timeout = _bounded_int(
        env.get("REDDOG_START_OPERATIONS_TIMEOUT_SECONDS"),
        profile.default_timeout_seconds,
        profile.max_timeout_seconds,
        "start_operations_timeout_invalid",
    )
    return max_claims, timeout


def _bounded_int(raw: Any, default: int, maximum: int, reason: str) -> int:
    value = default if raw in (None, "") else raw
    if isinstance(value, bool) or not str(value).isdigit():
        raise StartOperationsRejected((reason,))
    parsed = int(value)
    if parsed < 1 or parsed > maximum:
        raise StartOperationsRejected((reason,))
    return parsed


def runtime_defaults(
    env: Mapping[str, str],
    audit: Mapping[str, Any],
    architect: Mapping[str, Any],
    max_claims: int,
    timeout_seconds: int,
    profile: StartOperationsProfile,
    *,
    prompt_text: str | None = None,
    operations_skill_receipt: Mapping[str, Any] | None = None,
) -> Mapping[str, Any]:
    return {
        "work_state_path": str(env.get("REDDOG_AUTHORITATIVE_WORK_STATE_PATH") or ""),
        "holoindex_receipt_path": str(env.get("HOLOINDEX_FRESHNESS_RECEIPT") or ""),
        "holoindex_ssd_path": str(env.get("HOLOINDEX_SSD_PATH") or ""),
        "requested_operation": "start_operations_readonly_audit",
        "prompt_text": prompt_text or profile.work_focus,
        "operations_skill_receipt": dict(operations_skill_receipt or {}),
        "audit_lanes": profile.audit_lanes,
        "audit_model_runtime_binding_receipt": audit,
        "architect_model_runtime_binding_receipt": architect,
        "max_claims": max_claims,
        "timeout_seconds": timeout_seconds,
    }


__all__ = [
    "StartOperationsRejected",
    "authorized_scope",
    "budgets",
    "load_bindings",
    "runtime_defaults",
]
