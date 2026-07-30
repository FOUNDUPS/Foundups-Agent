"""Canonical model topology for bounded artifact-generation provider calls."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

from modules.ai_intelligence.ai_gateway.src.model_runtime_binding_digest import (
    canonical_model_runtime_binding_digest,
)
from modules.ai_intelligence.ai_gateway.src.model_runtime_binding_verification_receipt import (
    ModelRuntimeBindingVerificationReceipt,
    verification_receipt_digest,
)
from modules.ai_intelligence.ai_gateway.src.model_signed_evidence import (
    rehydrate_model_runtime_binding_receipt,
    rehydrate_model_selection_receipt,
)


def artifact_generation_digest(value: Any) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=str,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def verified_artifact_generation_binding(
    *,
    invocation_binding: Mapping[str, Any],
    runtime_binding: Mapping[str, Any],
    selection: Mapping[str, Any],
    verification: ModelRuntimeBindingVerificationReceipt,
) -> dict[str, Any] | None:
    """Return a normalized binding only when its topology is independently derived."""

    try:
        runtime = rehydrate_model_runtime_binding_receipt(runtime_binding)
        selected = rehydrate_model_selection_receipt(selection)
        normalized = _normalized_mapping(invocation_binding)
    except Exception:
        return None
    expected = _expected_selection(runtime, selected, selection, verification)
    supplied = normalized.get("model_selection")
    if not isinstance(supplied, Mapping):
        return None
    return (
        normalized
        if artifact_generation_digest(supplied)
        == artifact_generation_digest(expected)
        else None
    )


def _expected_selection(
    runtime: Any,
    selected: Any,
    selection: Mapping[str, Any],
    verification: ModelRuntimeBindingVerificationReceipt,
) -> dict[str, Any]:
    payload = runtime.to_reddog_bridge_payload()
    return {
        "receipt_id": runtime.selection_receipt_id,
        "digest": artifact_generation_digest(selection),
        "catalog_snapshot_id": runtime.catalog_snapshot_id,
        "task_family": runtime.task_family,
        "purpose": "production",
        "selected_model_ids": [runtime.principal_model, *runtime.panel_models],
        "role_assignments": [
            {
                "role": item.role,
                "canonical_model_id": item.canonical_model_id,
                "provider": item.provider,
            }
            for item in selected.role_assignments
        ],
        "panel_topology_digest": selected.panel_topology_digest or "",
        "lead_model": str(payload.get("lead_model") or ""),
        "panel_models": [str(item) for item in payload.get("panel_models") or ()],
        "model_runtime_binding_receipt_id": runtime.receipt_id,
        "model_runtime_binding_digest": canonical_model_runtime_binding_digest(runtime),
        "model_runtime_binding_verification_receipt_id": verification.receipt_id,
        "model_runtime_binding_verification_digest": verification_receipt_digest(
            verification
        ),
        "runtime_surface": runtime.runtime_surface,
    }


def _normalized_mapping(value: Mapping[str, Any]) -> dict[str, Any]:
    normalized = json.loads(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            default=str,
        )
    )
    return normalized if isinstance(normalized, dict) else {}


__all__ = [
    "artifact_generation_digest",
    "verified_artifact_generation_binding",
]
