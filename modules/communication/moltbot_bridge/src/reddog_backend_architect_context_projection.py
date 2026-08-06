"""Bounded prompt projection for backend RedDog architect determination."""

from __future__ import annotations

import json
import hashlib
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Mapping, Sequence

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
from modules.communication.moltbot_bridge.src.reddog_principal_memex_resident_admission import (
    AuthenticatedPrincipalMemexContext,
    consume_authenticated_principal_memex_context,
    validate_principal_memex_admission_output,
)

MAX_PRINCIPAL_MEMEX_MODEL_OUTPUT_CHARS = 64_000
MAX_PRINCIPAL_MEMEX_DECODED_TEXT_CHARS = 64_000


@dataclass(frozen=True)
class ArchitectRuntimeBindingMetadata:
    model_selection: Mapping[str, Any]
    model_selection_receipt_id: str | None
    model_selection_digest: str | None
    runtime_binding_receipt_id: str | None
    runtime_binding_digest: str | None
    rejection_reasons: tuple[str, ...]


@dataclass(frozen=True)
class ArchitectPrincipalMemexAdmission:
    context_view: Mapping[str, Any] | None
    receipt: Mapping[str, Any] | None
    rejection_reasons: tuple[str, ...]


def resolve_principal_memex_cycle(
    *, blocked: bool, context: AuthenticatedPrincipalMemexContext | None,
    runtime_binding_receipt_id: str | None, runtime_binding_digest: str | None,
    observed_at: str, rejection_reason: str,
    snapshot: OperationalContextSnapshot | None, report_bundle_id: str | None,
    report_digests: Sequence[str], wsp15_allocation_digest: str | None,
    model_selection_digest: str | None,
    conversation_binding: Mapping[str, Any] | None,
    now_epoch: Callable[[], int] | None = None,
) -> tuple[ArchitectPrincipalMemexAdmission, str | None]:
    admission = ArchitectPrincipalMemexAdmission(None, None, ())
    if not blocked and context is not None:
        try:
            admission = resolve_principal_memex_context(
                context=context, runtime_binding_receipt_id=runtime_binding_receipt_id,
                runtime_binding_digest=runtime_binding_digest,
                now_epoch=_trusted_epoch(now_epoch, _iso_epoch(observed_at)),
                rejection_reason=rejection_reason,
            )
        except Exception:
            admission = ArchitectPrincipalMemexAdmission(
                None, None, (rejection_reason,)
            )
    cycle_id = architect_cycle_id(
        snapshot=snapshot, report_bundle_id=report_bundle_id,
        report_digests=report_digests,
        wsp15_allocation_digest=wsp15_allocation_digest,
        model_selection_digest=model_selection_digest,
        conversation_binding=conversation_binding,
        principal_memex_receipt=admission.receipt,
    )
    return admission, cycle_id


def architect_model_binding(
    *, base: Mapping[str, Any], cycle_id: str,
    model_selection: Mapping[str, Any],
    conversation_binding: Mapping[str, Any] | None,
    principal_memex_receipt: Mapping[str, Any] | None,
) -> Mapping[str, Any]:
    binding = {**base, "cycle_id": cycle_id}
    if model_selection:
        binding = {**binding, "model_selection": dict(model_selection)}
    if conversation_binding:
        binding = {**binding, "conversation_work_binding": dict(conversation_binding)}
    if principal_memex_receipt:
        binding = {
            **binding,
            "principal_memex_admission_receipt_id": str(
                principal_memex_receipt.get("receipt_id") or ""
            ),
            "principal_memex_admission_digest": _digest(principal_memex_receipt),
        }
    return binding


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


def resolve_principal_memex_context(
    *, context: AuthenticatedPrincipalMemexContext | None,
    runtime_binding_receipt_id: str | None,
    runtime_binding_digest: str | None,
    now_epoch: int,
    rejection_reason: str,
) -> ArchitectPrincipalMemexAdmission:
    if context is None:
        return ArchitectPrincipalMemexAdmission(None, None, ())
    result = consume_authenticated_principal_memex_context(
        context,
        model_runtime_binding_receipt_id=str(runtime_binding_receipt_id or ""),
        model_runtime_binding_digest=str(runtime_binding_digest or ""),
        now_epoch=int(now_epoch),
    )
    if not result.accepted:
        return ArchitectPrincipalMemexAdmission(None, None, (rejection_reason,))
    validated = validate_principal_memex_admission_output(
        result.admission_receipt, result.context_view
    )
    if validated is None:
        return ArchitectPrincipalMemexAdmission(None, None, (rejection_reason,))
    receipt, context_view = validated
    return ArchitectPrincipalMemexAdmission(context_view, receipt, ())


def run_principal_memex_guarded_architect_model(
    runner: Any, prompt: str, context: Mapping[str, Any], binding: Mapping[str, Any],
    timeout_seconds: int, receipt: Mapping[str, Any] | None,
    principal_memex_view: Mapping[str, Any] | None, observed_at: str,
    now_epoch: Callable[[], int] | None,
) -> tuple[Any | None, str | None]:
    """Recheck Principal Memex freshness immediately before the model call."""
    try:
        if receipt is not None:
            expires_at = receipt.get("expires_at")
            current_epoch = _trusted_epoch(now_epoch, _iso_epoch(observed_at))
            if type(expires_at) is not int or current_epoch >= expires_at:
                return None, "principal_memex"
        result = runner.run_architect_determination(
            prompt=prompt, context=context, binding=binding,
            timeout_seconds=timeout_seconds,
        )
        if not _principal_memex_output_safe(result, principal_memex_view):
            return None, "principal_memex"
        return result, None
    except TimeoutError:
        return None, "timeout"
    except Exception:
        return None, "failure"


def architect_cycle_id(
    *, snapshot: OperationalContextSnapshot | None,
    report_bundle_id: str | None, report_digests: Sequence[str],
    wsp15_allocation_digest: str | None, model_selection_digest: str | None,
    conversation_binding: Mapping[str, Any] | None = None,
    principal_memex_receipt: Mapping[str, Any] | None = None,
) -> str | None:
    if snapshot is None or not report_bundle_id or not wsp15_allocation_digest:
        return None
    return _digest({
        "snapshot_receipt_id": snapshot.snapshot_receipt_id,
        "snapshot_content_digest": snapshot.snapshot_content_digest,
        "report_bundle_id": report_bundle_id,
        "report_digests": tuple(report_digests),
        "wsp15_allocation_digest": wsp15_allocation_digest,
        "model_selection_digest": model_selection_digest,
        "conversation_binding_digest": str(
            (conversation_binding or {}).get("conversation_binding_digest") or ""
        ),
        "principal_memex_context_digest": _principal_memex_cycle_digest(
            principal_memex_receipt
        ),
    })


def _principal_memex_cycle_digest(receipt: Mapping[str, Any] | None) -> str:
    if not receipt:
        return ""
    stable_fields = (
        "principal_id", "conversation_id", "conversation_revision",
        "conversation_record_digest", "projection_id", "projection_manifest_digest",
        "context_view_digest", "source_decision_item_ids", "admitted_item_ids",
    )
    return _digest({field: receipt.get(field) for field in stable_fields})


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
    principal_memex_view: Mapping[str, Any] | None = None,
) -> str:
    payload = {
        "context_view_id": context_view.context_view_id,
        "snapshot_receipt_id": context_view.snapshot_receipt_id,
        "evidence_bundle_id": evidence_bundle.evidence_bundle_id,
        "context_view_text": _bound_text(context_view.text, 6000),
        "audit_reports": [report_prompt_view(report) for report in reports],
        "conversation_work_binding": dict(conversation_binding or {}),
        "principal_memex_context": dict(principal_memex_view or {}),
        "principal_memex_output_policy": "private_context_must_not_be_reproduced",
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


def principal_memex_durable_determination_fields(
    *, parsed: Mapping[str, Any], reports: Sequence[Mapping[str, Any]],
    proposal_admission: Any, principal_memex_view: Mapping[str, Any] | None,
) -> tuple[str, str | None, str, tuple[str, ...], Any]:
    """Remove every model-authored free-text field from durable Memex results."""

    action = str(parsed["action"]).upper()
    next_slice = str(parsed.get("next_slice_name") or "").strip() or None
    if not principal_memex_view:
        return (
            action, next_slice, str(parsed.get("summary") or "").strip(),
            _normalize_text_list(parsed.get("decision_reasons")), proposal_admission,
        )
    supported = {
        str(finding.get("next_slice_name") or "").strip()
        for report in reports if isinstance(report, Mapping)
        for finding in report.get("findings", ()) if isinstance(finding, Mapping)
    }
    next_slice = next_slice if next_slice in supported else None
    if action != "STOP" and next_slice is None:
        action = "STOP"
    return (
        action, next_slice,
        "Principal Memex informed an advisory determination; model-authored text was not persisted.",
        ("principal_memex_advisory_only",), None,
    )


def _principal_memex_output_safe(
    result: Any, principal_memex_view: Mapping[str, Any] | None,
) -> bool:
    if not principal_memex_view:
        return True
    output_tokens = _decoded_output_tokens(getattr(result, "content", ""))
    if not output_tokens:
        return False
    for item in principal_memex_view.get("items", ()):
        if not isinstance(item, Mapping):
            return False
        tokens = re.findall(r"[a-z0-9]+", str(item.get("statement") or "").casefold())
        if not tokens:
            return False
        output_counts = Counter(output_tokens)
        if not (Counter(tokens) - output_counts):
            return False
    return True


def _decoded_output_tokens(content: Any) -> list[str]:
    if not isinstance(content, str):
        return []
    raw_content = content
    if len(raw_content) > MAX_PRINCIPAL_MEMEX_MODEL_OUTPUT_CHARS:
        return []
    try:
        stack = [json.loads(raw_content)]
    except (TypeError, ValueError):
        return []
    texts: list[str] = []
    text_chars = 0
    visited = 0
    while stack and visited < 1024:
        value = stack.pop()
        visited += 1
        if isinstance(value, str):
            texts.append(value)
            text_chars += len(value)
            if text_chars > MAX_PRINCIPAL_MEMEX_DECODED_TEXT_CHARS:
                return []
        elif isinstance(value, Mapping):
            for key, item in reversed(tuple(value.items())):
                stack.extend((item, str(key)))
        elif not isinstance(value, (str, bytes)) and isinstance(value, Sequence):
            stack.extend(reversed(tuple(value)))
    if stack:
        return []
    if any(
        unicodedata.category(character).startswith("C")
        for text in texts for character in text
    ):
        return []
    normalized = unicodedata.normalize("NFKC", " ".join(texts))
    if any(ord(character) > 127 for character in normalized):
        return []
    return re.findall(r"[a-z0-9]+", normalized.casefold())


def _canonical_json(value: Mapping[str, Any]) -> str:
    return json.dumps(
        dict(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True
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


def _iso_epoch(value: str) -> int:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return 0
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return int(parsed.timestamp())


def _trusted_epoch(
    now_epoch: Callable[[], int] | None, fallback_epoch: int,
) -> int:
    value = fallback_epoch if now_epoch is None else now_epoch()
    if type(value) is not int or value < 0:
        raise ValueError("principal_memex_clock_invalid")
    return value


__all__ = [
    "ArchitectPrincipalMemexAdmission",
    "architect_model_binding",
    "architect_cycle_id",
    "build_architect_context",
    "conversation_snapshot_matches",
    "model_runtime_binding",
    "principal_memex_durable_determination_fields",
    "report_prompt_view",
    "resolve_architect_runtime_binding",
    "resolve_conversation_context",
    "resolve_principal_memex_context",
    "resolve_principal_memex_cycle",
    "run_principal_memex_guarded_architect_model",
]
