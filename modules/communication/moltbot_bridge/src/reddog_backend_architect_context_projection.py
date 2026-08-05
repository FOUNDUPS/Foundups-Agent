"""Bounded prompt projection for backend RedDog architect determination."""

from __future__ import annotations

import json
import hashlib
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from modules.ai_intelligence.ai_gateway.src.model_intelligence_selection import (
    SelectionPurpose,
)
from modules.ai_intelligence.ai_gateway.src.model_runtime_binding import (
    ModelRuntimeBindingDecision,
)
from modules.ai_intelligence.ai_gateway.src.model_runtime_binding_digest import (
    canonical_model_runtime_binding_digest,
)
from modules.ai_intelligence.ai_gateway.src.model_signed_evidence import (
    rehydrate_model_runtime_binding_receipt,
)

from modules.communication.moltbot_bridge.src.reddog_operational_context_snapshot import (
    ContextView,
    EvidenceBundle,
    OperationalContextSnapshot,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_work_promotion import (
    AuthenticatedConversationWorkContext,
    conversation_work_binding,
)


@dataclass(frozen=True)
class ArchitectRuntimeBindingMetadata:
    model_selection: Mapping[str, Any]
    model_selection_receipt_id: str | None
    model_selection_digest: str | None
    runtime_binding_receipt_id: str | None
    runtime_binding_digest: str | None
    rejection_reasons: tuple[str, ...]


def resolve_conversation_context(
    context: AuthenticatedConversationWorkContext | None,
    snapshot: OperationalContextSnapshot | None,
    rejection_reason: str,
) -> tuple[Mapping[str, Any] | None, tuple[str, ...]]:
    if context is None:
        return None, ()
    binding = conversation_work_binding(context)
    if binding is None or not conversation_snapshot_matches(binding, snapshot):
        return binding, (rejection_reason,)
    return binding, ()


def resolve_architect_runtime_binding(
    *,
    value: Any,
    wsp15_allocation_receipt: Mapping[str, Any],
    expected_surface: str,
    rejection_reason: str,
) -> ArchitectRuntimeBindingMetadata:
    reasons: list[str] = []
    selection = _runtime_binding(value, expected_surface, rejection_reason, reasons)
    expected_id = str(
        wsp15_allocation_receipt.get(
            "architect_model_runtime_binding_receipt_id"
        ) or ""
    )
    expected_digest = str(
        wsp15_allocation_receipt.get("architect_model_runtime_binding_digest") or ""
    )
    if not selection or (
        not expected_id
        or not expected_digest
        or selection.get("model_runtime_binding_receipt_id") != expected_id
        or selection.get("model_runtime_binding_digest") != expected_digest
    ):
        reasons.append(rejection_reason)
    return ArchitectRuntimeBindingMetadata(
        selection,
        _optional(selection.get("receipt_id")),
        _optional(selection.get("digest")),
        _optional(selection.get("model_runtime_binding_receipt_id")),
        _optional(selection.get("model_runtime_binding_digest")),
        tuple(dict.fromkeys(reasons)),
    )


def model_runtime_binding(
    value: Any,
    reasons: list[str],
    *,
    expected_surface: str,
) -> Mapping[str, Any]:
    return _runtime_binding(
        value,
        expected_surface,
        "REJECT_ARCHITECT_DETERMINATION_MODEL_RUNTIME_BINDING_RECEIPT",
        reasons,
    )


def build_architect_context(
    *,
    context_view: ContextView,
    evidence_bundle: EvidenceBundle,
    reports: Sequence[Mapping[str, Any]],
    conversation_binding: Mapping[str, Any] | None,
    max_chars: int,
) -> str:
    payload = {
        "context_view_id": context_view.context_view_id,
        "snapshot_receipt_id": context_view.snapshot_receipt_id,
        "evidence_bundle_id": evidence_bundle.evidence_bundle_id,
        "context_view_text": _bound_text(context_view.text, 6000),
        "audit_reports": [report_prompt_view(report) for report in reports],
        "conversation_work_binding": dict(conversation_binding or {}),
    }
    encoded = _canonical_json(payload)
    if len(encoded) > max_chars:
        raise ValueError("canonical_json_budget_exceeded")
    return encoded


def report_prompt_view(report: Mapping[str, Any]) -> Mapping[str, Any]:
    return {
        "assignment_id": report.get("assignment_id"),
        "lane_id": report.get("lane_id"),
        "summary": _bound_text(report.get("summary"), 1000),
        "report_digest": report.get("report_digest"),
        "evidence_refs": list(_normalize_text_list(report.get("evidence_refs")))[:32],
        "findings": _bounded_findings(report.get("findings")),
    }


def conversation_snapshot_matches(
    binding: Mapping[str, Any], snapshot: OperationalContextSnapshot | None
) -> bool:
    if snapshot is None:
        return False
    return all(
        (
            binding.get("snapshot_receipt_id") == snapshot.snapshot_receipt_id,
            binding.get("snapshot_content_digest") == snapshot.snapshot_content_digest,
            binding.get("repo_head_sha") == snapshot.repo_state.get("head_sha"),
            binding.get("holoindex_generation_id")
            == snapshot.holoindex_state.get("generation_id"),
            binding.get("holoindex_freshness_receipt_digest")
            == snapshot.holoindex_state.get("receipt_digest"),
        )
    )


def _bounded_findings(value: Any) -> list[Mapping[str, Any]]:
    if not isinstance(value, list):
        return []
    bounded: list[Mapping[str, Any]] = []
    for item in value[:12]:
        if isinstance(item, Mapping):
            bounded.append(_finding_view(item))
    return bounded


def _finding_view(item: Mapping[str, Any]) -> Mapping[str, Any]:
    return {
        "finding_id": _bound_text(item.get("finding_id"), 160),
        "claim": _bound_text(item.get("claim"), 800),
        "wsp97_label": _bound_text(item.get("wsp97_label"), 64),
        "recommended_action": _bound_text(item.get("recommended_action"), 64),
        "wsp15_priority": _bound_text(item.get("wsp15_priority"), 16),
        "severity": _bound_text(item.get("severity"), 32),
        "next_slice_name": _bound_text(item.get("next_slice_name"), 160),
        "evidence_refs": list(_normalize_text_list(item.get("evidence_refs")))[:16],
    }


def _normalize_text_list(value: Any) -> tuple[str, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        return ()
    return tuple(dict.fromkeys(str(item).strip() for item in value if str(item).strip()))


def _bound_text(value: Any, max_chars: int) -> str:
    return str(value or "")[:max_chars]


def _canonical_json(value: Mapping[str, Any]) -> str:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )


def _runtime_binding(
    value: Any, expected_surface: str, rejection_reason: str, reasons: list[str]
) -> Mapping[str, Any]:
    binding = _json_mapping(value)
    try:
        receipt = rehydrate_model_runtime_binding_receipt(binding)
    except Exception:
        reasons.append(rejection_reason)
        return {}
    if (
        receipt.decision != ModelRuntimeBindingDecision.BOUND
        or not receipt.principal_model
        or receipt.runtime_surface != expected_surface
    ):
        reasons.append(rejection_reason)
        return {}
    payload = receipt.to_reddog_bridge_payload()
    return {
        "receipt_id": receipt.selection_receipt_id,
        "digest": _digest(binding),
        "catalog_snapshot_id": receipt.catalog_snapshot_id,
        "task_family": receipt.task_family,
        "purpose": SelectionPurpose.PRODUCTION.value,
        "selected_model_ids": [receipt.principal_model, *receipt.panel_models],
        "role_assignments": list(payload.get("model_role_bindings") or ()),
        "panel_topology_digest": "",
        "lead_model": str(payload.get("lead_model") or ""),
        "panel_models": [str(item) for item in payload.get("panel_models") or ()],
        "model_runtime_binding_receipt_id": receipt.receipt_id,
        "model_runtime_binding_digest": canonical_model_runtime_binding_digest(binding),
        "runtime_surface": receipt.runtime_surface,
    }


def _json_mapping(value: Any) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    try:
        result = json.loads(_canonical_json(value))
    except (TypeError, ValueError):
        return {}
    return result if isinstance(result, Mapping) else {}


def _digest(value: Mapping[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(
        _canonical_json(value).encode("utf-8")
    ).hexdigest()


def _optional(value: Any) -> str | None:
    return str(value).strip() if str(value or "").strip() else None


__all__ = [
    "build_architect_context",
    "conversation_snapshot_matches",
    "model_runtime_binding",
    "report_prompt_view",
    "resolve_architect_runtime_binding",
    "resolve_conversation_context",
]
