"""Runtime binding receipts for RedDog dynamic model selection.

This module is the production boundary after catalog, selection, benchmark,
promotion, and AutoResearch planning. It turns a production
``ModelSelectionReceipt`` into a RedDog/Fusion bridge payload only when every
selected model is backed by receipt-bound benchmark and signed promotion
evidence.

It does not call providers, run benchmarks, mutate catalogs, write
PatternMemory, re-index HoloIndex, or modify extension runtime state.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Mapping, Sequence

from .model_intelligence_catalog import ModelCatalogSnapshot, PromotionState
from .model_intelligence_outcomes import (
    ModelBenchmarkEvidenceReceipt,
    ModelPromotionEvidenceReceipt,
)
from .model_intelligence_selection import (
    RESERVED_PANEL_ROLES,
    ModelPanelRoleAssignment,
    ModelSelectionReceipt,
    SelectionDecision,
    SelectionMode,
    SelectionPurpose,
)


RUNTIME_BINDING_SCHEMA_VERSION = "reddog_model_runtime_binding_receipt.v1"
RUNTIME_BINDING_POLICY_SCHEMA_VERSION = "reddog_model_runtime_binding_policy.v1"


class ModelRuntimeBindingDecision(str, Enum):
    """Runtime binding decision."""

    BOUND = "bound"
    REJECTED = "rejected"


@dataclass(frozen=True)
class ModelRuntimeBindingPolicy:
    """Policy for admitting model selection receipts to RedDog runtime."""

    task_family: str
    runtime_surface: str
    min_verifier_pass_rate: float
    required_task_set_digest: str
    required_held_out_split_digest: str
    required_verifier_digest: str
    max_panel_models: int = 4
    required_panel_topology_digest: str | None = None
    authority_receipt_id: str | None = None
    schema_version: str = RUNTIME_BINDING_POLICY_SCHEMA_VERSION

    def normalized(self) -> "ModelRuntimeBindingPolicy":
        return ModelRuntimeBindingPolicy(
            task_family=_clean_token(_required("task_family", self.task_family)),
            runtime_surface=_clean_token(_required("runtime_surface", self.runtime_surface)),
            min_verifier_pass_rate=_threshold(self.min_verifier_pass_rate),
            required_task_set_digest=_required("required_task_set_digest", self.required_task_set_digest),
            required_held_out_split_digest=_required(
                "required_held_out_split_digest",
                self.required_held_out_split_digest,
            ),
            required_verifier_digest=_required("required_verifier_digest", self.required_verifier_digest),
            max_panel_models=max(0, min(int(self.max_panel_models), 8)),
            required_panel_topology_digest=_optional(self.required_panel_topology_digest),
            authority_receipt_id=_optional(self.authority_receipt_id),
        )

    def to_dict(self) -> dict[str, Any]:
        policy = self.normalized()
        return {
            "schema_version": policy.schema_version,
            "task_family": policy.task_family,
            "runtime_surface": policy.runtime_surface,
            "min_verifier_pass_rate": policy.min_verifier_pass_rate,
            "required_task_set_digest": policy.required_task_set_digest,
            "required_held_out_split_digest": policy.required_held_out_split_digest,
            "required_verifier_digest": policy.required_verifier_digest,
            "max_panel_models": policy.max_panel_models,
            "required_panel_topology_digest": policy.required_panel_topology_digest,
            "authority_receipt_id": policy.authority_receipt_id,
        }


@dataclass(frozen=True)
class RuntimeModelRoleBinding:
    """Role assignment admitted into the runtime payload."""

    role: str
    model_id: str
    provider: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RedDogModelRuntimeBindingReceipt:
    """Digest-bound runtime model binding receipt."""

    receipt_id: str
    decision: ModelRuntimeBindingDecision
    runtime_surface: str
    catalog_snapshot_id: str
    selection_receipt_id: str
    task_family: str
    principal_model: str | None
    panel_models: tuple[str, ...]
    role_bindings: tuple[RuntimeModelRoleBinding, ...]
    benchmark_evidence_receipt_ids: tuple[str, ...]
    promotion_evidence_receipt_ids: tuple[str, ...]
    signed_promotion_receipt_ids: tuple[str, ...]
    policy: ModelRuntimeBindingPolicy
    rejection_reasons: tuple[str, ...] = ()
    schema_version: str = RUNTIME_BINDING_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "receipt_id": self.receipt_id,
            "decision": self.decision.value,
            "runtime_surface": self.runtime_surface,
            "catalog_snapshot_id": self.catalog_snapshot_id,
            "selection_receipt_id": self.selection_receipt_id,
            "task_family": self.task_family,
            "principal_model": self.principal_model,
            "panel_models": list(self.panel_models),
            "role_bindings": [binding.to_dict() for binding in self.role_bindings],
            "benchmark_evidence_receipt_ids": list(self.benchmark_evidence_receipt_ids),
            "promotion_evidence_receipt_ids": list(self.promotion_evidence_receipt_ids),
            "signed_promotion_receipt_ids": list(self.signed_promotion_receipt_ids),
            "policy": self.policy.to_dict(),
            "rejection_reasons": list(self.rejection_reasons),
        }

    def to_reddog_bridge_payload(self) -> dict[str, Any]:
        """Return the minimal payload extension/bridge code may consume later."""

        if self.decision != ModelRuntimeBindingDecision.BOUND or not self.principal_model:
            raise ValueError("runtime_binding_not_bound")
        return {
            "lead_model": self.principal_model,
            "panel_models": list(self.panel_models),
            "model_runtime_binding_receipt_id": self.receipt_id,
            "model_runtime_surface": self.runtime_surface,
            "model_selection_receipt_id": self.selection_receipt_id,
            "model_catalog_snapshot_id": self.catalog_snapshot_id,
            "model_role_bindings": [binding.to_dict() for binding in self.role_bindings],
        }


def bind_reddog_runtime_models(
    *,
    catalog_snapshot: ModelCatalogSnapshot,
    selection_receipt: ModelSelectionReceipt,
    benchmark_evidence_receipts: Sequence[ModelBenchmarkEvidenceReceipt],
    promotion_evidence_receipts: Sequence[ModelPromotionEvidenceReceipt],
    policy: ModelRuntimeBindingPolicy,
) -> RedDogModelRuntimeBindingReceipt:
    """Validate and bind a production model selection for RedDog runtime."""

    normalized_policy = policy.normalized()
    benchmark_by_model = _unique_by_model(benchmark_evidence_receipts, "benchmark")
    promotion_by_model = _unique_by_model(promotion_evidence_receipts, "promotion")
    rejections = _runtime_binding_rejections(
        catalog_snapshot=catalog_snapshot,
        selection_receipt=selection_receipt,
        benchmark_by_model=benchmark_by_model,
        promotion_by_model=promotion_by_model,
        policy=normalized_policy,
    )
    role_bindings: tuple[RuntimeModelRoleBinding, ...] = ()
    principal_model: str | None = None
    panel_models: tuple[str, ...] = ()
    if not rejections:
        role_bindings = _role_bindings(selection_receipt)
        principal_model, panel_models = _runtime_models(selection_receipt, role_bindings)
        if len(panel_models) > normalized_policy.max_panel_models:
            rejections.append("panel_model_count_above_policy")
            principal_model = None
            panel_models = ()
            role_bindings = ()

    decision = ModelRuntimeBindingDecision.BOUND if not rejections else ModelRuntimeBindingDecision.REJECTED
    selected_ids = tuple(selection_receipt.selected_model_ids)
    benchmark_ids = tuple(
        sorted(benchmark_by_model[model_id].receipt_id for model_id in selected_ids if model_id in benchmark_by_model)
    )
    promotion_ids = tuple(
        sorted(promotion_by_model[model_id].receipt_id for model_id in selected_ids if model_id in promotion_by_model)
    )
    signed_ids = tuple(
        sorted(
            promotion_by_model[model_id].signed_promotion_receipt_id
            for model_id in selected_ids
            if model_id in promotion_by_model
        )
    )
    body = {
        "schema_version": RUNTIME_BINDING_SCHEMA_VERSION,
        "decision": decision.value,
        "runtime_surface": normalized_policy.runtime_surface,
        "catalog_snapshot_id": catalog_snapshot.snapshot_id,
        "selection_receipt_id": selection_receipt.receipt_id,
        "task_family": selection_receipt.requirements.task_family,
        "principal_model": principal_model,
        "panel_models": list(panel_models),
        "role_bindings": [binding.to_dict() for binding in role_bindings],
        "benchmark_evidence_receipt_ids": list(benchmark_ids),
        "promotion_evidence_receipt_ids": list(promotion_ids),
        "signed_promotion_receipt_ids": list(signed_ids),
        "policy": normalized_policy.to_dict(),
        "rejection_reasons": sorted(set(rejections)),
    }
    return RedDogModelRuntimeBindingReceipt(
        receipt_id=_digest_prefixed("reddog_model_runtime_binding", body),
        decision=decision,
        runtime_surface=normalized_policy.runtime_surface,
        catalog_snapshot_id=catalog_snapshot.snapshot_id,
        selection_receipt_id=selection_receipt.receipt_id,
        task_family=selection_receipt.requirements.task_family,
        principal_model=principal_model,
        panel_models=panel_models,
        role_bindings=role_bindings,
        benchmark_evidence_receipt_ids=benchmark_ids,
        promotion_evidence_receipt_ids=promotion_ids,
        signed_promotion_receipt_ids=signed_ids,
        policy=normalized_policy,
        rejection_reasons=tuple(sorted(set(rejections))),
    )


def _runtime_binding_rejections(
    *,
    catalog_snapshot: ModelCatalogSnapshot,
    selection_receipt: ModelSelectionReceipt,
    benchmark_by_model: Mapping[str, ModelBenchmarkEvidenceReceipt],
    promotion_by_model: Mapping[str, ModelPromotionEvidenceReceipt],
    policy: ModelRuntimeBindingPolicy,
) -> list[str]:
    reasons: list[str] = []
    selected_ids = tuple(selection_receipt.selected_model_ids)
    catalog_ids = {card.canonical_model_id for card in catalog_snapshot.cards}
    if selection_receipt.catalog_snapshot_id != catalog_snapshot.snapshot_id:
        reasons.append("catalog_snapshot_mismatch")
    if selection_receipt.decision != SelectionDecision.SELECTED:
        reasons.append("selection_not_selected")
    if selection_receipt.requirements.purpose != SelectionPurpose.PRODUCTION:
        reasons.append("selection_not_production")
    if selection_receipt.requirements.task_family != policy.task_family:
        reasons.append("task_family_mismatch")
    if not selected_ids:
        reasons.append("missing_selected_models")
    if selection_receipt.requirements.min_verifier_pass_rate is None:
        reasons.append("selection_verifier_threshold_missing")
    elif selection_receipt.requirements.min_verifier_pass_rate < policy.min_verifier_pass_rate:
        reasons.append("selection_threshold_below_runtime_policy")
    if selection_receipt.requirements.selection_mode == SelectionMode.PANEL:
        if not selection_receipt.panel_topology_digest:
            reasons.append("missing_panel_topology_digest")
        if policy.required_panel_topology_digest and selection_receipt.panel_topology_digest != policy.required_panel_topology_digest:
            reasons.append("panel_topology_digest_mismatch")
        role_errors = _panel_role_rejections(selection_receipt.role_assignments, selected_ids)
        reasons.extend(role_errors)
    elif selection_receipt.role_assignments:
        reasons.extend(_single_role_rejections(selection_receipt.role_assignments, selected_ids))
    for model_id in selected_ids:
        if model_id not in catalog_ids:
            reasons.append("selected_model_not_in_catalog")
        benchmark = benchmark_by_model.get(model_id)
        promotion = promotion_by_model.get(model_id)
        if benchmark is None:
            reasons.append("missing_benchmark_evidence")
            continue
        if promotion is None:
            reasons.append("missing_promotion_evidence")
            continue
        reasons.extend(_evidence_rejections(model_id, benchmark, promotion, policy, selection_receipt))
    return sorted(set(reasons))


def _evidence_rejections(
    model_id: str,
    benchmark: ModelBenchmarkEvidenceReceipt,
    promotion: ModelPromotionEvidenceReceipt,
    policy: ModelRuntimeBindingPolicy,
    selection_receipt: ModelSelectionReceipt,
) -> list[str]:
    reasons: list[str] = []
    if benchmark.model_id != model_id:
        reasons.append("benchmark_model_mismatch")
    if promotion.model_id != model_id:
        reasons.append("promotion_model_mismatch")
    if benchmark.task_family != policy.task_family or benchmark.task_family != selection_receipt.requirements.task_family:
        reasons.append("benchmark_task_family_mismatch")
    if promotion.task_family != policy.task_family:
        reasons.append("promotion_task_family_mismatch")
    if promotion.benchmark_evidence_receipt_id != benchmark.receipt_id:
        reasons.append("promotion_benchmark_mismatch")
    if promotion.promotion_state != PromotionState.CHAMPION:
        reasons.append("promotion_not_champion")
    if not promotion.signed_promotion_receipt_id:
        reasons.append("missing_signed_promotion_receipt")
    if benchmark.task_set_digest != policy.required_task_set_digest:
        reasons.append("task_set_digest_mismatch")
    if benchmark.held_out_split_digest != policy.required_held_out_split_digest:
        reasons.append("held_out_split_digest_mismatch")
    if benchmark.verifier_digest != policy.required_verifier_digest:
        reasons.append("verifier_digest_mismatch")
    if benchmark.verifier_pass_rate < policy.min_verifier_pass_rate:
        reasons.append("benchmark_below_runtime_threshold")
    if promotion.min_verifier_pass_rate < policy.min_verifier_pass_rate:
        reasons.append("promotion_threshold_below_runtime_policy")
    if selection_receipt.requirements.selection_mode == SelectionMode.PANEL:
        if benchmark.prompt_topology_digest != selection_receipt.panel_topology_digest:
            reasons.append("benchmark_topology_mismatch")
    return reasons


def _panel_role_rejections(
    role_assignments: tuple[ModelPanelRoleAssignment, ...],
    selected_ids: tuple[str, ...],
) -> list[str]:
    reasons: list[str] = []
    if not role_assignments:
        return ["missing_panel_role_assignments"]
    roles = [assignment.role for assignment in role_assignments]
    model_ids = [assignment.canonical_model_id for assignment in role_assignments]
    if "principal" not in roles:
        reasons.append("missing_principal_role")
    if any(role in RESERVED_PANEL_ROLES for role in roles):
        reasons.append("reserved_verifier_role_in_panel")
    if len(set(roles)) != len(roles):
        reasons.append("duplicate_panel_roles")
    if tuple(sorted(model_ids)) != tuple(sorted(selected_ids)):
        reasons.append("panel_role_model_mismatch")
    return reasons


def _single_role_rejections(
    role_assignments: tuple[ModelPanelRoleAssignment, ...],
    selected_ids: tuple[str, ...],
) -> list[str]:
    if len(role_assignments) != 1:
        return ["single_selection_role_count_invalid"]
    assignment = role_assignments[0]
    if assignment.role != "principal":
        return ["single_selection_role_not_principal"]
    if assignment.canonical_model_id not in selected_ids:
        return ["single_selection_role_model_mismatch"]
    return []


def _role_bindings(selection_receipt: ModelSelectionReceipt) -> tuple[RuntimeModelRoleBinding, ...]:
    if selection_receipt.requirements.selection_mode != SelectionMode.PANEL:
        model_id = selection_receipt.selected_model_ids[0]
        provider = _provider_for_model(selection_receipt, model_id)
        return (RuntimeModelRoleBinding(role="principal", model_id=model_id, provider=provider),)
    return tuple(
        RuntimeModelRoleBinding(
            role=assignment.role,
            model_id=assignment.canonical_model_id,
            provider=assignment.provider,
        )
        for assignment in selection_receipt.role_assignments
    )


def _runtime_models(
    selection_receipt: ModelSelectionReceipt,
    bindings: tuple[RuntimeModelRoleBinding, ...],
) -> tuple[str, tuple[str, ...]]:
    if selection_receipt.requirements.selection_mode == SelectionMode.SINGLE:
        return bindings[0].model_id, ()
    principal = next((binding.model_id for binding in bindings if binding.role == "principal"), "")
    panel = tuple(binding.model_id for binding in bindings if binding.role != "principal")
    return principal, panel


def _provider_for_model(selection_receipt: ModelSelectionReceipt, model_id: str) -> str:
    for ranking in selection_receipt.rankings:
        if ranking.canonical_model_id == model_id:
            return ranking.provider
    return "unknown"


def _unique_by_model(
    receipts: Sequence[ModelBenchmarkEvidenceReceipt] | Sequence[ModelPromotionEvidenceReceipt],
    receipt_type: str,
) -> dict[str, Any]:
    mapping: dict[str, Any] = {}
    for receipt in receipts:
        model_id = getattr(receipt, "model_id", "")
        if not model_id:
            raise ValueError(f"{receipt_type}_receipt_missing_model_id")
        if model_id in mapping:
            raise ValueError(f"duplicate_{receipt_type}_receipt_for_model")
        mapping[model_id] = receipt
    return mapping


def _required(name: str, value: Any) -> str:
    cleaned = str(value).strip()
    if not cleaned:
        raise ValueError(f"missing_{name}")
    return cleaned


def _optional(value: Any) -> str | None:
    cleaned = str(value).strip() if value is not None else ""
    return cleaned or None


def _threshold(value: float) -> float:
    parsed = float(value)
    if parsed <= 0 or parsed > 1:
        raise ValueError("invalid_verifier_threshold")
    return parsed


def _clean_token(value: Any) -> str:
    return str(value).strip().lower().replace(" ", "_")


def _digest_prefixed(prefix: str, value: Mapping[str, Any]) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return f"{prefix}:{hashlib.sha256(encoded).hexdigest()}"
