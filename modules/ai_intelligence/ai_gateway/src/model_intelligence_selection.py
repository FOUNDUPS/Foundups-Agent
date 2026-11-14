"""Task-scoped model selection receipts for RedDog model intelligence.

The selector consumes a canonical model catalog snapshot and produces a
digest-bound receipt. It does not call a provider, benchmark a model, mutate
state, or bind RedDog runtime defaults. Production mode is intentionally stricter
than evaluation mode: unbenchmarked provider-catalog candidates can be selected
for evaluation, but not for production authority.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Iterable, Mapping

from .model_intelligence_catalog import (
    Availability,
    ModelCapabilityCard,
    ModelCatalogSnapshot,
    PromotionState,
)


SELECTION_SCHEMA_VERSION = "model_selection_receipt.v1"
DEFAULT_PANEL_ROLES = ("principal", "researcher", "critic", "implementer")
RESERVED_PANEL_ROLES = {"verifier"}


class SelectionMode(str, Enum):
    """Shape of requested model selection."""

    SINGLE = "single"
    PANEL = "panel"


class SelectionPurpose(str, Enum):
    """How the selected model(s) may be used."""

    EVALUATION = "evaluation"
    PRODUCTION = "production"


class SelectionDecision(str, Enum):
    """Selection result."""

    SELECTED = "selected"
    REJECTED = "rejected"


@dataclass(frozen=True)
class ModelTaskRequirements:
    """Task requirements supplied by RedDog/WSP_15, not model names."""

    task_family: str
    selection_mode: SelectionMode = SelectionMode.SINGLE
    purpose: SelectionPurpose = SelectionPurpose.EVALUATION
    required_modalities: tuple[str, ...] = ("text",)
    min_context_window: int | None = None
    require_tools: bool = False
    require_structured_output: bool = False
    require_reasoning: bool = False
    max_input_cost_per_million: float | None = None
    max_output_cost_per_million: float | None = None
    allowed_providers: tuple[str, ...] = ()
    denied_providers: tuple[str, ...] = ()
    max_candidates: int = 1
    min_verifier_pass_rate: float | None = None
    panel_roles: tuple[str, ...] = ()
    panel_topology_digest: str | None = None

    def normalized(self) -> "ModelTaskRequirements":
        max_candidates = max(1, min(int(self.max_candidates), 5))
        if self.selection_mode == SelectionMode.SINGLE:
            max_candidates = 1
        return ModelTaskRequirements(
            task_family=_clean_token(self.task_family),
            selection_mode=self.selection_mode,
            purpose=self.purpose,
            required_modalities=tuple(sorted({_clean_token(v) for v in self.required_modalities if str(v).strip()}))
            or ("text",),
            min_context_window=self.min_context_window if self.min_context_window and self.min_context_window > 0 else None,
            require_tools=bool(self.require_tools),
            require_structured_output=bool(self.require_structured_output),
            require_reasoning=bool(self.require_reasoning),
            max_input_cost_per_million=_non_negative_float_or_none(self.max_input_cost_per_million),
            max_output_cost_per_million=_non_negative_float_or_none(self.max_output_cost_per_million),
            allowed_providers=tuple(sorted({_clean_token(v) for v in self.allowed_providers if str(v).strip()})),
            denied_providers=tuple(sorted({_clean_token(v) for v in self.denied_providers if str(v).strip()})),
            max_candidates=max_candidates,
            min_verifier_pass_rate=_verifier_threshold_or_none(self.min_verifier_pass_rate),
            panel_roles=_normalize_panel_roles(self.panel_roles, max_candidates, self.selection_mode),
            panel_topology_digest=_clean_optional_digest(self.panel_topology_digest),
        )


@dataclass(frozen=True)
class ModelCandidateRanking:
    """Ranked candidate evidence included in the selection receipt."""

    canonical_model_id: str
    provider: str
    score: float
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class ModelPanelRoleAssignment:
    """Role-to-model assignment for panel selection receipts."""

    role: str
    canonical_model_id: str
    provider: str


@dataclass(frozen=True)
class ModelSelectionReceipt:
    """Digest-bound model selection result."""

    receipt_id: str
    catalog_snapshot_id: str
    requirements: ModelTaskRequirements
    decision: SelectionDecision
    selected_model_ids: tuple[str, ...]
    rankings: tuple[ModelCandidateRanking, ...]
    role_assignments: tuple[ModelPanelRoleAssignment, ...] = ()
    panel_topology_digest: str | None = None
    rejection_reasons: tuple[str, ...] = ()
    schema_version: str = SELECTION_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "receipt_id": self.receipt_id,
            "catalog_snapshot_id": self.catalog_snapshot_id,
            "requirements": _requirements_to_json(self.requirements),
            "decision": self.decision.value,
            "selected_model_ids": list(self.selected_model_ids),
            "rankings": [asdict(ranking) for ranking in self.rankings],
            "role_assignments": [asdict(assignment) for assignment in self.role_assignments],
            "panel_topology_digest": self.panel_topology_digest,
            "rejection_reasons": list(self.rejection_reasons),
        }


def select_models_for_task(
    snapshot: ModelCatalogSnapshot,
    requirements: ModelTaskRequirements,
    *,
    production_evidence: Any | None = None,
) -> ModelSelectionReceipt:
    """Select eligible model candidates from a catalog snapshot."""

    normalized_requirements = requirements.normalized()
    production_evidence_map, production_evidence_error = _production_evidence_map(
        production_evidence,
        normalized_requirements,
    )
    ranked: list[ModelCandidateRanking] = []
    rejection_counts: dict[str, int] = {}
    for card in snapshot.cards:
        ok, reasons = _eligible(card, normalized_requirements, production_evidence_map, production_evidence_error)
        if not ok:
            for reason in reasons:
                rejection_counts[reason] = rejection_counts.get(reason, 0) + 1
            continue
        ranked.append(_rank_candidate(card, normalized_requirements))

    ranked.sort(key=lambda item: (-item.score, item.provider, item.canonical_model_id))
    selected = _select_rankings(ranked, normalized_requirements)
    role_assignments = _build_role_assignments(selected, normalized_requirements)
    decision = SelectionDecision.SELECTED if selected else SelectionDecision.REJECTED
    rejection_reasons = tuple(
        sorted(f"{reason}:{count}" for reason, count in rejection_counts.items())
    ) if not selected else ()
    body = {
        "schema_version": SELECTION_SCHEMA_VERSION,
        "catalog_snapshot_id": snapshot.snapshot_id,
        "requirements": _requirements_to_json(normalized_requirements),
        "decision": decision.value,
        "selected_model_ids": [item.canonical_model_id for item in selected],
        "rankings": [asdict(item) for item in ranked],
        "role_assignments": [asdict(item) for item in role_assignments],
        "panel_topology_digest": _panel_topology_digest(normalized_requirements, selected),
        "rejection_reasons": list(rejection_reasons),
    }
    receipt_id = _digest_prefixed("model_selection_receipt", body)
    return ModelSelectionReceipt(
        receipt_id=receipt_id,
        catalog_snapshot_id=snapshot.snapshot_id,
        requirements=normalized_requirements,
        decision=decision,
        selected_model_ids=tuple(item.canonical_model_id for item in selected),
        rankings=tuple(ranked),
        role_assignments=role_assignments,
        panel_topology_digest=_panel_topology_digest(normalized_requirements, selected),
        rejection_reasons=rejection_reasons,
    )


def _eligible(
    card: ModelCapabilityCard,
    requirements: ModelTaskRequirements,
    production_evidence: Mapping[str, Mapping[str, Any]],
    production_evidence_error: str | None = None,
) -> tuple[bool, tuple[str, ...]]:
    reasons: list[str] = []
    provider = _clean_token(card.provider)
    if requirements.allowed_providers and provider not in requirements.allowed_providers:
        reasons.append("provider_not_allowed")
    if provider in requirements.denied_providers:
        reasons.append("provider_denied")
    if card.promotion_state in {PromotionState.BLOCKED, PromotionState.DEPRECATED}:
        reasons.append("promotion_state_not_eligible")
    if card.availability == Availability.UNAVAILABLE:
        reasons.append("unavailable")
    if requirements.task_family not in set(card.task_families):
        reasons.append("task_family_missing")
    if not set(requirements.required_modalities).issubset(set(card.modalities)):
        reasons.append("modality_missing")
    if requirements.min_context_window is not None:
        if card.context_window is None or card.context_window < requirements.min_context_window:
            reasons.append("context_window_too_small")
    if requirements.require_tools and not card.supports_tools:
        reasons.append("tools_missing")
    if requirements.require_structured_output and not card.supports_structured_output:
        reasons.append("structured_output_missing")
    if requirements.require_reasoning and not card.supports_reasoning:
        reasons.append("reasoning_missing")
    if requirements.max_input_cost_per_million is not None and card.input_cost_per_million is not None:
        if card.input_cost_per_million > requirements.max_input_cost_per_million:
            reasons.append("input_cost_too_high")
    if requirements.max_output_cost_per_million is not None and card.output_cost_per_million is not None:
        if card.output_cost_per_million > requirements.max_output_cost_per_million:
            reasons.append("output_cost_too_high")
    if requirements.purpose == SelectionPurpose.PRODUCTION:
        if requirements.min_verifier_pass_rate is None or requirements.min_verifier_pass_rate <= 0:
            reasons.append("production_verifier_threshold_missing")
        if card.promotion_state != PromotionState.CHAMPION:
            reasons.append("not_production_champion")
        if production_evidence_error:
            reasons.append(production_evidence_error)
        evidence = production_evidence.get(card.canonical_model_id)
        if not evidence:
            reasons.append("missing_production_evidence")
        else:
            reasons.extend(_production_evidence_rejections(card, requirements, evidence))
    return not reasons, tuple(sorted(set(reasons)))


def _production_evidence_map(
    production_evidence: Any | None,
    requirements: ModelTaskRequirements,
) -> tuple[Mapping[str, Mapping[str, Any]], str | None]:
    if requirements.purpose != SelectionPurpose.PRODUCTION:
        if production_evidence is None:
            return {}, None
        if isinstance(production_evidence, Mapping):
            return production_evidence, None
        if hasattr(production_evidence, "to_selection_mapping"):
            return production_evidence.to_selection_mapping(), None
        return {}, None
    if production_evidence is None:
        return {}, None
    try:
        from .model_signed_evidence import VerifiedModelProductionEvidence
    except Exception:
        VerifiedModelProductionEvidence = ()  # type: ignore[assignment]
    if not isinstance(production_evidence, VerifiedModelProductionEvidence):
        return {}, "production_evidence_not_authenticated"
    mapping = production_evidence.to_selection_mapping()
    if not isinstance(mapping, Mapping):
        return {}, "production_evidence_not_authenticated"
    return mapping, None


def _rank_candidate(card: ModelCapabilityCard, requirements: ModelTaskRequirements) -> ModelCandidateRanking:
    reasons: list[str] = []
    score = 0.0
    promotion_weight = {
        PromotionState.CHAMPION: 100.0,
        PromotionState.CANDIDATE: 50.0,
        PromotionState.CHALLENGER: 25.0,
    }.get(card.promotion_state, 0.0)
    score += promotion_weight
    reasons.append(f"promotion:{card.promotion_state.value}")

    benchmark_score = float(card.benchmark_scores.get(requirements.task_family, 0.0))
    if benchmark_score:
        score += benchmark_score * 100.0
        reasons.append("task_benchmark")
    if card.verifier_pass_rate is not None:
        score += float(card.verifier_pass_rate) * 50.0
        reasons.append("verifier_pass_rate")
    if card.availability == Availability.AVAILABLE:
        score += 10.0
        reasons.append("available")
    if requirements.min_context_window and card.context_window:
        score += min(card.context_window / requirements.min_context_window, 2.0)
        reasons.append("context_fit")
    score -= _cost_penalty(card.input_cost_per_million)
    score -= _cost_penalty(card.output_cost_per_million)
    return ModelCandidateRanking(
        canonical_model_id=card.canonical_model_id,
        provider=card.provider,
        score=round(score, 6),
        reasons=tuple(sorted(set(reasons))),
    )


def _select_rankings(
    ranked: Sequence[ModelCandidateRanking],
    requirements: ModelTaskRequirements,
) -> tuple[ModelCandidateRanking, ...]:
    if requirements.selection_mode == SelectionMode.SINGLE:
        return tuple(ranked[:1])

    selected: list[ModelCandidateRanking] = []
    used_providers: set[str] = set()
    for item in ranked:
        if item.provider in used_providers and len(ranked) >= requirements.max_candidates:
            continue
        selected.append(item)
        used_providers.add(item.provider)
        if len(selected) >= requirements.max_candidates:
            return tuple(selected)
    for item in ranked:
        if item not in selected:
            selected.append(item)
            if len(selected) >= requirements.max_candidates:
                break
    return tuple(selected)


def _build_role_assignments(
    selected: tuple[ModelCandidateRanking, ...],
    requirements: ModelTaskRequirements,
) -> tuple[ModelPanelRoleAssignment, ...]:
    if not selected:
        return ()
    roles = ("principal",) if requirements.selection_mode == SelectionMode.SINGLE else requirements.panel_roles
    return tuple(
        ModelPanelRoleAssignment(
            role=roles[index],
            canonical_model_id=item.canonical_model_id,
            provider=item.provider,
        )
        for index, item in enumerate(selected)
        if index < len(roles)
    )


def _panel_topology_digest(
    requirements: ModelTaskRequirements,
    selected: tuple[ModelCandidateRanking, ...],
) -> str | None:
    if requirements.selection_mode != SelectionMode.PANEL:
        return None
    if requirements.panel_topology_digest:
        return requirements.panel_topology_digest
    body = {
        "roles": list(requirements.panel_roles),
        "selected_model_ids": [item.canonical_model_id for item in selected],
        "providers": [item.provider for item in selected],
    }
    return _digest_prefixed("panel_topology", body)


def _production_evidence_rejections(
    card: ModelCapabilityCard,
    requirements: ModelTaskRequirements,
    evidence: Mapping[str, Any],
) -> list[str]:
    reasons: list[str] = []
    if str(evidence.get("model_id") or "") != card.canonical_model_id:
        reasons.append("evidence_model_mismatch")
    if str(evidence.get("task_family") or "") != requirements.task_family:
        reasons.append("evidence_task_mismatch")
    if not evidence.get("benchmark_evidence_receipt_id"):
        reasons.append("missing_benchmark_evidence_receipt")
    if not evidence.get("promotion_receipt_id"):
        reasons.append("missing_promotion_receipt")
    if not evidence.get("signed_promotion_receipt_id"):
        reasons.append("missing_signed_promotion_receipt")
    if not evidence.get("task_set_digest"):
        reasons.append("missing_task_set_digest")
    if not evidence.get("held_out_split_digest"):
        reasons.append("missing_held_out_split_digest")
    if not evidence.get("verifier_digest"):
        reasons.append("missing_verifier_digest")
    if not evidence.get("prompt_topology_digest"):
        reasons.append("missing_prompt_topology_digest")
    sample_count = _non_negative_int_or_none(evidence.get("sample_count"))
    if not sample_count:
        reasons.append("missing_sample_count")
    verifier_pass_rate = evidence.get("verifier_pass_rate")
    if verifier_pass_rate is None:
        reasons.append("missing_verifier_pass_rate")
    elif requirements.min_verifier_pass_rate is not None and float(verifier_pass_rate) < requirements.min_verifier_pass_rate:
        reasons.append("verifier_pass_rate_too_low")
    if str(evidence.get("promotion_state") or "").lower() != PromotionState.CHAMPION.value:
        reasons.append("promotion_receipt_not_champion")
    return reasons


def _cost_penalty(value: float | None) -> float:
    if value is None:
        return 0.0
    return min(max(value, 0.0), 100.0) / 100.0


def _requirements_to_json(requirements: ModelTaskRequirements) -> dict[str, Any]:
    normalized = requirements.normalized()
    return {
        "task_family": normalized.task_family,
        "selection_mode": normalized.selection_mode.value,
        "purpose": normalized.purpose.value,
        "required_modalities": list(normalized.required_modalities),
        "min_context_window": normalized.min_context_window,
        "require_tools": normalized.require_tools,
        "require_structured_output": normalized.require_structured_output,
        "require_reasoning": normalized.require_reasoning,
        "max_input_cost_per_million": normalized.max_input_cost_per_million,
        "max_output_cost_per_million": normalized.max_output_cost_per_million,
        "allowed_providers": list(normalized.allowed_providers),
        "denied_providers": list(normalized.denied_providers),
        "max_candidates": normalized.max_candidates,
        "min_verifier_pass_rate": normalized.min_verifier_pass_rate,
        "panel_roles": list(normalized.panel_roles),
        "panel_topology_digest": normalized.panel_topology_digest,
    }


def _normalize_panel_roles(
    value: tuple[str, ...],
    max_candidates: int,
    selection_mode: SelectionMode,
) -> tuple[str, ...]:
    if selection_mode == SelectionMode.SINGLE:
        return ("principal",)
    roles = tuple(_clean_token(role) for role in value if str(role).strip()) or DEFAULT_PANEL_ROLES
    if any(role in RESERVED_PANEL_ROLES for role in roles):
        raise ValueError("verifier_role_reserved_for_independent_verifier")
    if len(set(roles)) != len(roles):
        raise ValueError("duplicate_panel_roles")
    if len(roles) < max_candidates:
        raise ValueError("insufficient_panel_roles")
    return roles[:max_candidates]


def _non_negative_float_or_none(value: float | None) -> float | None:
    if value is None:
        return None
    parsed = float(value)
    return parsed if parsed >= 0 else None


def _non_negative_int_or_none(value: Any) -> int | None:
    if value is None:
        return None
    parsed = int(value)
    return parsed if parsed >= 0 else None


def _verifier_threshold_or_none(value: float | None) -> float | None:
    if value is None:
        return None
    return max(0.0, min(float(value), 1.0))


def _clean_optional_digest(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None


def _clean_token(value: Any) -> str:
    return str(value).strip().lower().replace(" ", "_")


def _digest_prefixed(prefix: str, value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return f"{prefix}:{hashlib.sha256(encoded).hexdigest()}"
