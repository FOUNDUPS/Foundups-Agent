"""Canonical model topology for bounded artifact-generation provider calls."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Mapping, Sequence

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

_ROUTE_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}")


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


def signed_principal_model_route(binding: object) -> tuple[str, str] | None:
    """Extract the one signed principal model/provider route, or fail closed."""

    selection = binding.get("model_selection") if isinstance(binding, Mapping) else None
    assignments = selection.get("role_assignments") if isinstance(selection, Mapping) else None
    lead = str(selection.get("lead_model") or "") if isinstance(selection, Mapping) else ""
    rows = [row for row in assignments or () if isinstance(row, Mapping)]
    principals = [row for row in rows if row.get("role") == "principal"]
    if len(principals) != 1 or principals[0].get("canonical_model_id") != lead:
        return None
    provider = str(principals[0].get("provider") or "")
    if _ROUTE_IDENTIFIER.fullmatch(lead) is None or _ROUTE_IDENTIFIER.fullmatch(provider) is None:
        return None
    return lead, provider


def resolved_model_topology(
    binding: object,
) -> tuple[tuple[str, str, str], ...] | None:
    """Return only the resolver-consumed role/provider/model endpoints."""

    endpoints = (
        binding.get("resolved_runtime_topology")
        if isinstance(binding, Mapping)
        else None
    )
    if not isinstance(endpoints, Sequence) or isinstance(endpoints, (str, bytes)):
        return None
    rows: list[tuple[str, str, str]] = []
    for endpoint in endpoints:
        if not isinstance(endpoint, Mapping):
            return None
        row = (
            str(endpoint.get("role") or ""),
            str(endpoint.get("provider") or ""),
            str(endpoint.get("model_id") or ""),
        )
        if any(_ROUTE_IDENTIFIER.fullmatch(value) is None for value in row):
            return None
        rows.append(row)
    if not rows or len({row[0] for row in rows}) != len(rows):
        return None
    return tuple(rows)


def resolved_principal_model_route(binding: object) -> tuple[str, str] | None:
    """Return the exact principal route from consumed resolver authority."""

    topology = resolved_model_topology(binding)
    principals = [row for row in topology or () if row[0] == "principal"]
    if len(principals) != 1:
        return None
    _, provider, model = principals[0]
    return model, provider


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
    "resolved_model_topology",
    "resolved_principal_model_route",
    "signed_principal_model_route",
    "verified_artifact_generation_binding",
]
