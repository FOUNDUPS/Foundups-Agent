# -*- coding: utf-8 -*-
"""Read-only FoundUp job projection of receipt-bound model capabilities."""

from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import asdict, dataclass
from types import MappingProxyType
from typing import Any, Mapping, Optional

from modules.ai_intelligence.ai_gateway.src.model_runtime_binding import (
    ModelRuntimeBindingDecision,
    RedDogModelRuntimeBindingReceipt,
    RuntimeModelRoleBinding,
)
from modules.ai_intelligence.ai_gateway.src.model_signed_evidence import (
    rehydrate_model_runtime_binding_receipt,
)

from .foundup_job_model_capability_receipt import normalize_exact_binding_receipt


PROFILE_SCHEMA_VERSION = "foundup_job_model_capability_profile.v1"
PROJECTION_SCHEMA_VERSION = "foundup_job_model_capability_projection.v1"
PROVIDER_CALL_ADMISSION_NOT_EVALUATED = "not_evaluated"
PROJECTION_REJECTION_REASONS: tuple[str, ...] = (
    "job_route_identity_mismatch",
    "profile_backend_mismatch",
    "binding_not_applicable",
    "binding_schema_invalid",
    "binding_decision_not_bound",
    "binding_surface_mismatch",
    "binding_task_family_mismatch",
    "binding_digest_mismatch",
    "binding_lineage_invalid",
    "live_binding_required",
)


@dataclass(frozen=True)
class FoundUpJobModelCapabilityProfile:
    """Canonical action capability facts; nullable fields remain unspecified."""

    profile_id: str
    requested_action: str
    target_backend: str
    runtime_surface: Optional[str]
    task_family: Optional[str]
    destructive_action_class: str
    provider_policy: str
    required_modalities: Optional[tuple[str, ...]]
    require_tools: Optional[bool]
    require_structured_output: Optional[bool]
    require_reasoning: Optional[bool]
    allowed_selection_modes: Optional[tuple[str, ...]]
    max_panel_models: Optional[int]
    schema_version: str = PROFILE_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        """Return the exact JSON-facing profile schema."""
        body = asdict(self)
        if self.required_modalities is not None:
            body["required_modalities"] = list(self.required_modalities)
        if self.allowed_selection_modes is not None:
            body["allowed_selection_modes"] = list(self.allowed_selection_modes)
        return body


@dataclass(frozen=True)
class FoundUpJobModelCapabilityProjection:
    """Receipt lineage projected for one routed FoundUp job."""

    projection_id: str
    profile_id: str
    decision: str
    rejection_reasons: tuple[str, ...]
    job_id: str
    tenant_id: str
    foundup_id: Optional[str]
    requested_action: str
    target_backend: str
    runtime_surface: Optional[str]
    task_family: Optional[str]
    dry_run_mode: bool
    compute_tier: str
    compute_budget: Optional[int]
    compute_used: int
    cost_class_preference: str
    catalog_snapshot_id: Optional[str]
    selection_receipt_id: Optional[str]
    model_runtime_binding_receipt_id: Optional[str]
    model_runtime_binding_digest: Optional[str]
    principal_model: Optional[str]
    panel_models: tuple[str, ...]
    role_bindings: tuple[RuntimeModelRoleBinding, ...]
    benchmark_evidence_receipt_ids: tuple[str, ...]
    promotion_evidence_receipt_ids: tuple[str, ...]
    signed_promotion_receipt_ids: tuple[str, ...]
    runtime_policy_digest: Optional[str]
    runtime_authority_receipt_id: Optional[str]
    provider_call_admission: str = PROVIDER_CALL_ADMISSION_NOT_EVALUATED
    schema_version: str = PROJECTION_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        """Return the exact JSON-facing projection schema."""
        body = asdict(self)
        body["rejection_reasons"] = list(self.rejection_reasons)
        body["panel_models"] = list(self.panel_models)
        body["role_bindings"] = [item.to_dict() for item in self.role_bindings]
        body["benchmark_evidence_receipt_ids"] = list(
            self.benchmark_evidence_receipt_ids
        )
        body["promotion_evidence_receipt_ids"] = list(
            self.promotion_evidence_receipt_ids
        )
        body["signed_promotion_receipt_ids"] = list(
            self.signed_promotion_receipt_ids
        )
        return body


def canonical_artifact_digest(value: Mapping[str, Any]) -> str:
    """Digest the exact JSON artifact using the repository canonical form."""
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _profile(
    action: str,
    backend: str,
    surface: Optional[str],
    task_family: Optional[str],
    destructive_class: str,
    provider_policy: str,
) -> FoundUpJobModelCapabilityProfile:
    not_applicable = provider_policy == "forbidden"
    body = {
        "schema_version": PROFILE_SCHEMA_VERSION,
        "requested_action": action,
        "target_backend": backend,
        "runtime_surface": surface,
        "task_family": task_family,
        "destructive_action_class": destructive_class,
        "provider_policy": provider_policy,
        "required_modalities": [] if not_applicable else None,
        "require_tools": False if not_applicable else None,
        "require_structured_output": False if not_applicable else None,
        "require_reasoning": False if not_applicable else None,
        "allowed_selection_modes": [] if not_applicable else None,
        "max_panel_models": 0 if not_applicable else None,
    }
    return FoundUpJobModelCapabilityProfile(
        profile_id=canonical_artifact_digest(body),
        requested_action=action,
        target_backend=backend,
        runtime_surface=surface,
        task_family=task_family,
        destructive_action_class=destructive_class,
        provider_policy=provider_policy,
        required_modalities=() if not_applicable else None,
        require_tools=False if not_applicable else None,
        require_structured_output=False if not_applicable else None,
        require_reasoning=False if not_applicable else None,
        allowed_selection_modes=() if not_applicable else None,
        max_panel_models=0 if not_applicable else None,
    )


FOUNDUP_JOB_MODEL_CAPABILITY_PROFILES = MappingProxyType(
    {
        "create_foundup": _profile(
            "create_foundup", "hermes_scaffold", None, None, "D2", "forbidden"
        ),
        "queue_foundup_job": _profile(
            "queue_foundup_job",
            "openclaw_queue",
            None,
            None,
            "deferred",
            "forbidden",
        ),
        "build_foundup": _profile(
            "build_foundup",
            "hermes_builder",
            "reddog_artifact_generation",
            "foundup_artifact_generation",
            "D3",
            "receipt_bound",
        ),
        "extract_foundup": _profile(
            "extract_foundup",
            "hermes_builder",
            "reddog_artifact_generation",
            "foundup_artifact_generation",
            "D3",
            "receipt_bound",
        ),
        "validate_foundup": _profile(
            "validate_foundup",
            "hermes_validator",
            "reddog_readonly_audit_worker",
            "foundup_validation",
            "D0",
            "receipt_bound",
        ),
    }
)


def get_foundup_job_model_capability_profile(
    requested_action: str,
) -> Optional[FoundUpJobModelCapabilityProfile]:
    """Return the immutable canonical profile for a supported action."""
    return FOUNDUP_JOB_MODEL_CAPABILITY_PROFILES.get(requested_action)


def resolve_foundup_job_model_capability_projection(
    *,
    job: Any,
    route_envelope: Any,
    dry_run_mode: bool,
    model_runtime_binding_receipt: Any = None,
    model_runtime_binding_digest: Any = None,
) -> FoundUpJobModelCapabilityProjection:
    """Resolve receipt lineage without selection, provider, or runtime calls."""
    action = getattr(job, "requested_action", None)
    profile = get_foundup_job_model_capability_profile(action)
    if profile is None:
        raise ValueError("unsupported_foundup_action")
    context = _projection_context(job, route_envelope, dry_run_mode)
    reasons = _route_rejection_reasons(job, route_envelope, profile)
    if reasons:
        return _build_projection(profile, context, "rejected", reasons, {})
    has_receipt = model_runtime_binding_receipt is not None
    has_digest = model_runtime_binding_digest not in (None, "")
    if profile.provider_policy == "forbidden":
        decision = "rejected" if has_receipt or has_digest else "not_applicable"
        reasons = ("binding_not_applicable",) if decision == "rejected" else ()
        return _build_projection(profile, context, decision, reasons, {})
    if not has_receipt and not has_digest:
        decision = "unbound_dry_run" if dry_run_mode else "rejected"
        reasons = () if dry_run_mode else ("live_binding_required",)
        return _build_projection(profile, context, decision, reasons, {})
    if not has_receipt or not has_digest:
        return _build_projection(
            profile, context, "rejected", ("binding_lineage_invalid",), {}
        )
    decision, reasons, lineage = _resolve_binding(
        profile,
        model_runtime_binding_receipt,
        model_runtime_binding_digest,
    )
    return _build_projection(profile, context, decision, reasons, lineage)


def _resolve_binding(
    profile: FoundUpJobModelCapabilityProfile,
    raw_receipt: Any,
    supplied_digest: Any,
) -> tuple[str, tuple[str, ...], dict[str, Any]]:
    normalized = normalize_exact_binding_receipt(raw_receipt)
    if normalized is None:
        return "rejected", ("binding_schema_invalid",), {}
    try:
        receipt = rehydrate_model_runtime_binding_receipt(normalized)
    except Exception:
        return "rejected", ("binding_schema_invalid",), {}
    exact_digest = canonical_artifact_digest(normalized)
    if not isinstance(supplied_digest, str) or not hmac.compare_digest(
        supplied_digest, exact_digest
    ):
        return "rejected", ("binding_digest_mismatch",), {}
    if receipt.decision != ModelRuntimeBindingDecision.BOUND:
        return "rejected", ("binding_decision_not_bound",), {}
    if receipt.runtime_surface != profile.runtime_surface:
        return "rejected", ("binding_surface_mismatch",), {}
    if receipt.task_family != profile.task_family:
        return "rejected", ("binding_task_family_mismatch",), {}
    try:
        bridge = receipt.to_reddog_bridge_payload()
    except Exception:
        return "rejected", ("binding_lineage_invalid",), {}
    if not _binding_lineage_valid(receipt, bridge):
        return "rejected", ("binding_lineage_invalid",), {}
    return "bound", (), _bound_lineage(receipt, bridge, exact_digest)


def _binding_lineage_valid(
    receipt: RedDogModelRuntimeBindingReceipt,
    bridge: Mapping[str, Any],
) -> bool:
    models = (receipt.principal_model, *receipt.panel_models)
    role_models = tuple(item.model_id for item in receipt.role_bindings)
    providers_match = all(
        "/" in item.model_id
        and item.provider == item.model_id.split("/", 1)[0]
        for item in receipt.role_bindings
    )
    evidence_sets = (
        receipt.benchmark_evidence_receipt_ids,
        receipt.promotion_evidence_receipt_ids,
        receipt.signed_promotion_receipt_ids,
    )
    return bool(
        receipt.principal_model
        and receipt.policy.runtime_surface == receipt.runtime_surface
        and receipt.policy.task_family == receipt.task_family
        and receipt.policy.authority_receipt_id
        and len(models) == len(set(models))
        and set(role_models) == set(models)
        and providers_match
        and all(len(items) == len(models) and all(items) for items in evidence_sets)
        and bridge.get("lead_model") == receipt.principal_model
        and bridge.get("panel_models") == list(receipt.panel_models)
        and bridge.get("model_runtime_binding_receipt_id") == receipt.receipt_id
        and bridge.get("model_runtime_surface") == receipt.runtime_surface
        and bridge.get("model_selection_receipt_id") == receipt.selection_receipt_id
        and bridge.get("model_catalog_snapshot_id") == receipt.catalog_snapshot_id
        and bridge.get("model_role_bindings")
        == [item.to_dict() for item in receipt.role_bindings]
    )


def _bound_lineage(
    receipt: RedDogModelRuntimeBindingReceipt,
    bridge: Mapping[str, Any],
    artifact_digest: str,
) -> dict[str, Any]:
    return {
        "catalog_snapshot_id": bridge["model_catalog_snapshot_id"],
        "selection_receipt_id": bridge["model_selection_receipt_id"],
        "model_runtime_binding_receipt_id": bridge[
            "model_runtime_binding_receipt_id"
        ],
        "model_runtime_binding_digest": artifact_digest,
        "principal_model": bridge["lead_model"],
        "panel_models": tuple(bridge["panel_models"]),
        "role_bindings": receipt.role_bindings,
        "benchmark_evidence_receipt_ids": (
            receipt.benchmark_evidence_receipt_ids
        ),
        "promotion_evidence_receipt_ids": (
            receipt.promotion_evidence_receipt_ids
        ),
        "signed_promotion_receipt_ids": receipt.signed_promotion_receipt_ids,
        "runtime_policy_digest": canonical_artifact_digest(
            receipt.policy.to_dict()
        ),
        "runtime_authority_receipt_id": receipt.policy.authority_receipt_id,
    }


def _projection_context(
    job: Any,
    route_envelope: Any,
    dry_run_mode: bool,
) -> dict[str, Any]:
    return {
        "job_id": str(getattr(job, "job_id", "") or ""),
        "tenant_id": str(getattr(job, "tenant_id", "") or ""),
        "foundup_id": getattr(job, "foundup_id", None),
        "requested_action": str(getattr(job, "requested_action", "") or ""),
        "target_backend": _enum_value(
            getattr(route_envelope, "target_backend", "")
        ),
        "runtime_surface": None,
        "task_family": None,
        "dry_run_mode": bool(dry_run_mode),
        "compute_tier": str(getattr(job, "compute_tier", "") or ""),
        "compute_budget": getattr(job, "compute_budget", None),
        "compute_used": int(getattr(job, "compute_used", 0) or 0),
        "cost_class_preference": str(
            getattr(job, "model_preference", "") or ""
        ),
    }


def _route_rejection_reasons(
    job: Any,
    route_envelope: Any,
    profile: FoundUpJobModelCapabilityProfile,
) -> tuple[str, ...]:
    job_identity = (
        getattr(job, "job_id", None),
        getattr(job, "tenant_id", None),
        getattr(job, "foundup_id", None),
        getattr(job, "requested_action", None),
    )
    route_identity = (
        getattr(route_envelope, "job_id", None),
        getattr(route_envelope, "tenant_id", None),
        getattr(route_envelope, "foundup_id", None),
        getattr(route_envelope, "requested_action", None),
    )
    reasons = []
    if job_identity != route_identity:
        reasons.append("job_route_identity_mismatch")
    if _enum_value(getattr(route_envelope, "target_backend", "")) != (
        profile.target_backend
    ):
        reasons.append("profile_backend_mismatch")
    return _stable_reasons(reasons)


def _build_projection(
    profile: FoundUpJobModelCapabilityProfile,
    context: Mapping[str, Any],
    decision: str,
    reasons: tuple[str, ...],
    lineage: Mapping[str, Any],
) -> FoundUpJobModelCapabilityProjection:
    empty = {
        "catalog_snapshot_id": None,
        "selection_receipt_id": None,
        "model_runtime_binding_receipt_id": None,
        "model_runtime_binding_digest": None,
        "principal_model": None,
        "panel_models": (),
        "role_bindings": (),
        "benchmark_evidence_receipt_ids": (),
        "promotion_evidence_receipt_ids": (),
        "signed_promotion_receipt_ids": (),
        "runtime_policy_digest": None,
        "runtime_authority_receipt_id": None,
    }
    values = {
        **context,
        "runtime_surface": profile.runtime_surface,
        "task_family": profile.task_family,
        **empty,
        **lineage,
        "schema_version": PROJECTION_SCHEMA_VERSION,
        "profile_id": profile.profile_id,
        "decision": decision,
        "rejection_reasons": _stable_reasons(reasons),
        "provider_call_admission": PROVIDER_CALL_ADMISSION_NOT_EVALUATED,
    }
    artifact = _projection_artifact(values)
    return FoundUpJobModelCapabilityProjection(
        projection_id=canonical_artifact_digest(artifact),
        **values,
    )


def _projection_artifact(values: Mapping[str, Any]) -> dict[str, Any]:
    artifact = dict(values)
    artifact["rejection_reasons"] = list(values["rejection_reasons"])
    artifact["panel_models"] = list(values["panel_models"])
    artifact["role_bindings"] = [
        item.to_dict() for item in values["role_bindings"]
    ]
    for field_name in (
        "benchmark_evidence_receipt_ids",
        "promotion_evidence_receipt_ids",
        "signed_promotion_receipt_ids",
    ):
        artifact[field_name] = list(values[field_name])
    return artifact


def _stable_reasons(reasons: Any) -> tuple[str, ...]:
    allowed = set(PROJECTION_REJECTION_REASONS)
    return tuple(sorted({str(reason) for reason in reasons if reason in allowed}))


def _enum_value(value: Any) -> str:
    return str(value.value if hasattr(value, "value") else value or "")


__all__ = [
    "FOUNDUP_JOB_MODEL_CAPABILITY_PROFILES",
    "FoundUpJobModelCapabilityProfile",
    "FoundUpJobModelCapabilityProjection",
    "PROFILE_SCHEMA_VERSION",
    "PROJECTION_REJECTION_REASONS",
    "PROJECTION_SCHEMA_VERSION",
    "canonical_artifact_digest",
    "get_foundup_job_model_capability_profile",
    "resolve_foundup_job_model_capability_projection",
]
