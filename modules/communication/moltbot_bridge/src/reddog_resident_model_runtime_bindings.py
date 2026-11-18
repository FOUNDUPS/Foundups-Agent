"""Shared loader for resident RedDog audit and architect model bindings."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Mapping

from modules.ai_intelligence.ai_gateway.src.model_signed_evidence import (
    rehydrate_model_runtime_binding_receipt,
)
from modules.communication.moltbot_bridge.src.reddog_runtime_json_read import (
    read_reddog_runtime_json_mapping,
)
from modules.communication.moltbot_bridge.src.reddog_model_runtime_binding_query import (
    runtime_binding_rejections,
)


AUDIT_SURFACE = "reddog_readonly_audit_worker"
ARCHITECT_SURFACE = "reddog_backend_architect"
AUDIT_EXPECTED_ID_ENV = (
    "REDDOG_READONLY_AUDIT_MODEL_RUNTIME_BINDING_EXPECTED_RECEIPT_ID"
)
ARCHITECT_EXPECTED_ID_ENV = (
    "REDDOG_BACKEND_ARCHITECT_MODEL_RUNTIME_BINDING_EXPECTED_RECEIPT_ID"
)


def load_resident_model_runtime_bindings(
    repo_root: Path | str,
    *,
    environ: Mapping[str, str] | None = None,
) -> tuple[Mapping[str, Any] | None, Mapping[str, Any] | None, str]:
    """Load distinct, out-of-repo BOUND receipts or return one stable reason."""

    env = environ if environ is not None else os.environ
    paths, reason = _binding_paths(env, Path(repo_root))
    if reason:
        return None, None, reason
    expected_ids, reason = _expected_receipt_ids(env)
    if reason:
        return None, None, reason
    runtime, audit_path, architect_path = paths
    try:
        audit = read_reddog_runtime_json_mapping(audit_path, allowed_root=runtime)
        architect = read_reddog_runtime_json_mapping(architect_path, allowed_root=runtime)
        audit_receipt = rehydrate_model_runtime_binding_receipt(audit)
        architect_receipt = rehydrate_model_runtime_binding_receipt(architect)
    except Exception:
        return None, None, "model_runtime_binding_artifact_invalid"
    reason = _binding_reason(audit_receipt, AUDIT_SURFACE, "audit")
    if reason:
        return None, None, reason
    reason = _binding_reason(architect_receipt, ARCHITECT_SURFACE, "architect")
    if reason:
        return None, None, reason
    if audit_receipt.receipt_id != expected_ids[0]:
        return None, None, "audit_model_runtime_binding_receipt_id_mismatch"
    if architect_receipt.receipt_id != expected_ids[1]:
        return None, None, "architect_model_runtime_binding_receipt_id_mismatch"
    return audit_receipt.to_dict(), architect_receipt.to_dict(), ""


def _expected_receipt_ids(
    env: Mapping[str, str],
) -> tuple[tuple[str, str], str]:
    audit = str(env.get(AUDIT_EXPECTED_ID_ENV) or "").strip()
    architect = str(env.get(ARCHITECT_EXPECTED_ID_ENV) or "").strip()
    if not audit:
        return ("", ""), "missing_audit_model_runtime_binding_expected_receipt_id"
    if not architect:
        return ("", ""), "missing_architect_model_runtime_binding_expected_receipt_id"
    return (audit, architect), ""


def _binding_paths(
    env: Mapping[str, str], repo_root: Path
) -> tuple[tuple[Path, ...], str]:
    root_value = str(env.get("REDDOG_RESIDENT_MODEL_RUNTIME_BINDING_ROOT") or "").strip()
    audit_value = str(
        env.get("REDDOG_READONLY_AUDIT_MODEL_RUNTIME_BINDING_RECEIPT_PATH") or ""
    ).strip()
    architect_value = str(
        env.get("REDDOG_BACKEND_ARCHITECT_MODEL_RUNTIME_BINDING_RECEIPT_PATH") or ""
    ).strip()
    if not root_value:
        return (), "missing_model_runtime_binding_root"
    if not audit_value:
        return (), "missing_audit_model_runtime_binding_path"
    if not architect_value:
        return (), "missing_architect_model_runtime_binding_path"

    runtime_root = Path(root_value)
    audit_path = Path(audit_value)
    architect_path = Path(architect_value)
    if not all(path.is_absolute() for path in (runtime_root, audit_path, architect_path)):
        return (), "model_runtime_binding_path_not_absolute"

    repo = Path(repo_root).resolve()
    runtime = runtime_root.resolve()
    if _inside(runtime, repo):
        return (), "model_runtime_binding_root_inside_repo"
    if _inside(audit_path.resolve(), repo) or _inside(architect_path.resolve(), repo):
        return (), "model_runtime_binding_artifact_inside_repo"
    if not _inside(audit_path.resolve(), runtime) or not _inside(
        architect_path.resolve(), runtime
    ):
        return (), "model_runtime_binding_artifact_outside_runtime_root"
    if os.path.normcase(str(audit_path.resolve())) == os.path.normcase(
        str(architect_path.resolve())
    ):
        return (), "model_runtime_binding_artifacts_not_distinct"
    return (runtime, audit_path, architect_path), ""


def _binding_reason(receipt: Any, surface: str, role: str) -> str:
    reasons = runtime_binding_rejections(receipt, expected_surface=surface)
    if not reasons:
        return ""
    if "model_runtime_binding_surface_invalid" in reasons:
        return f"{role}_model_runtime_binding_surface_invalid"
    return f"{role}_model_runtime_binding_evidence_invalid"


def _inside(child: Path, parent: Path) -> bool:
    resolved_child = child.resolve()
    resolved_parent = parent.resolve()
    return resolved_child == resolved_parent or resolved_parent in resolved_child.parents


__all__ = [
    "ARCHITECT_EXPECTED_ID_ENV",
    "ARCHITECT_SURFACE",
    "AUDIT_EXPECTED_ID_ENV",
    "AUDIT_SURFACE",
    "load_resident_model_runtime_bindings",
]
