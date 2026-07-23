"""Canonical model catalog snapshots for RedDog model intelligence.

This module is the first runtime layer for measured model selection. It does
not choose a model, benchmark a model, call a provider, or trust "latest"
aliases as production-ready. It converts provider/local/static evidence into
immutable capability cards that later selection and benchmark slices can bind.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass, field, replace
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Iterable, Mapping, Sequence

from .model_registry import ALL_MODELS, RECOMMENDED_MODELS, ModelStatus


SCHEMA_VERSION = "model_catalog_snapshot.v1"
CARD_SCHEMA_VERSION = "model_capability_card.v1"


class Availability(str, Enum):
    """Observed availability state for a model candidate."""

    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


class PromotionState(str, Enum):
    """Governance state for using a model in production paths."""

    CANDIDATE = "candidate"
    CHALLENGER = "challenger"
    CHAMPION = "champion"
    DEPRECATED = "deprecated"
    BLOCKED = "blocked"


@dataclass(frozen=True)
class ModelCatalogRejectedRecord:
    """A catalog source record that could not be normalized."""

    source: str
    reason: str
    record_digest: str


@dataclass(frozen=True)
class ModelCapabilityCard:
    """Normalized capability evidence for a single model candidate."""

    provider: str
    model_id: str
    canonical_model_id: str
    source: str
    availability: Availability = Availability.UNKNOWN
    freshness: str = "unknown"
    promotion_state: PromotionState = PromotionState.CANDIDATE
    task_families: tuple[str, ...] = ()
    context_window: int | None = None
    input_cost_per_million: float | None = None
    output_cost_per_million: float | None = None
    supports_tools: bool = False
    supports_structured_output: bool = False
    supports_reasoning: bool = False
    modalities: tuple[str, ...] = ("text",)
    supported_parameters: tuple[str, ...] = ()
    privacy_policy: str = "unknown"
    verifier_pass_rate: float | None = None
    benchmark_scores: Mapping[str, float] = field(default_factory=dict)
    schema_version: str = CARD_SCHEMA_VERSION

    def normalized(self) -> "ModelCapabilityCard":
        """Return a deterministic representation for hashing and snapshots."""

        return replace(
            self,
            provider=_clean_token(self.provider),
            model_id=str(self.model_id).strip(),
            canonical_model_id=str(self.canonical_model_id).strip(),
            source=_clean_token(self.source),
            freshness=_clean_token(self.freshness),
            task_families=tuple(sorted({_clean_token(v) for v in self.task_families if str(v).strip()})),
            modalities=tuple(sorted({_clean_token(v) for v in self.modalities if str(v).strip()})) or ("text",),
            supported_parameters=tuple(
                sorted({_clean_token(v) for v in self.supported_parameters if str(v).strip()})
            ),
            benchmark_scores=dict(sorted((str(k), float(v)) for k, v in self.benchmark_scores.items())),
        )


@dataclass(frozen=True)
class ModelCatalogSnapshot:
    """Immutable catalog snapshot consumed by later selection/benchmark slices."""

    snapshot_id: str
    generated_at: str
    cards: tuple[ModelCapabilityCard, ...]
    source_receipts: tuple[str, ...] = ()
    rejected_records: tuple[ModelCatalogRejectedRecord, ...] = ()
    schema_version: str = SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-ready representation."""

        return {
            "schema_version": self.schema_version,
            "snapshot_id": self.snapshot_id,
            "generated_at": self.generated_at,
            "source_receipts": list(self.source_receipts),
            "cards": [_card_to_json(card) for card in self.cards],
            "rejected_records": [asdict(record) for record in self.rejected_records],
        }


def build_model_catalog_snapshot(
    cards: Iterable[ModelCapabilityCard],
    *,
    source_receipts: Sequence[str] | None = None,
    rejected_records: Sequence[ModelCatalogRejectedRecord] | None = None,
    generated_at: str | None = None,
) -> ModelCatalogSnapshot:
    """Build a digest-bound catalog snapshot from normalized cards."""

    generated = generated_at or datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    normalized_cards = tuple(
        sorted((card.normalized() for card in cards), key=lambda card: (card.provider, card.canonical_model_id))
    )
    normalized_receipts = tuple(sorted(str(v).strip() for v in (source_receipts or ()) if str(v).strip()))
    normalized_rejections = tuple(rejected_records or ())
    body = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": generated,
        "source_receipts": list(normalized_receipts),
        "cards": [_card_to_json(card) for card in normalized_cards],
        "rejected_records": [asdict(record) for record in normalized_rejections],
    }
    snapshot_id = _digest_prefixed("model_catalog_snapshot", body)
    return ModelCatalogSnapshot(
        snapshot_id=snapshot_id,
        generated_at=generated,
        cards=normalized_cards,
        source_receipts=normalized_receipts,
        rejected_records=normalized_rejections,
    )


def normalize_static_registry_cards(
    registry_models: Mapping[str, Any] | None = None,
    recommended_models: Mapping[str, Sequence[str]] | None = None,
) -> tuple[ModelCapabilityCard, ...]:
    """Normalize the existing static registry into candidate cards.

    Static registry entries are evidence, not proof of task fitness. Current
    models become candidates; legacy models become challengers; deprecated and
    sunset models are not eligible for production selection.
    """

    registry = registry_models or ALL_MODELS
    task_index = _task_index(recommended_models or RECOMMENDED_MODELS)
    cards: list[ModelCapabilityCard] = []
    for model_id, info in registry.items():
        status = getattr(info, "status", None)
        status_value = getattr(status, "value", str(status or "unknown"))
        cards.append(
            ModelCapabilityCard(
                provider=str(getattr(info, "provider", "unknown")),
                model_id=str(getattr(info, "model_id", model_id)),
                canonical_model_id=str(getattr(info, "model_id", model_id)),
                source="static_model_registry",
                availability=Availability.UNKNOWN,
                freshness=status_value,
                promotion_state=_promotion_from_registry_status(status),
                task_families=tuple(task_index.get(str(getattr(info, "model_id", model_id)), ())),
                privacy_policy="provider_policy_unknown",
            ).normalized()
        )
    return tuple(sorted(cards, key=lambda card: (card.provider, card.canonical_model_id)))


def normalize_openrouter_catalog(
    catalog_payload: Mapping[str, Any],
) -> tuple[tuple[ModelCapabilityCard, ...], tuple[ModelCatalogRejectedRecord, ...]]:
    """Normalize an OpenRouter-style model catalog payload.

    The OpenRouter catalog is provider evidence. Every normalized record starts
    as a candidate and must be benchmarked before becoming a champion.
    """

    records = catalog_payload.get("data", [])
    if not isinstance(records, list):
        return (), (
            ModelCatalogRejectedRecord(
                source="openrouter_catalog",
                reason="data_not_list",
                record_digest=_digest_prefixed("rejected_record", catalog_payload),
            ),
        )

    cards: list[ModelCapabilityCard] = []
    rejected: list[ModelCatalogRejectedRecord] = []
    for record in records:
        normalized = _normalize_openrouter_record(record)
        if isinstance(normalized, ModelCapabilityCard):
            cards.append(normalized)
        else:
            rejected.append(normalized)
    return tuple(sorted(cards, key=lambda card: card.canonical_model_id)), tuple(rejected)


def normalize_local_role_cards(selections: Mapping[str, Any]) -> tuple[ModelCapabilityCard, ...]:
    """Normalize local role resolution without leaking local filesystem paths."""

    cards: list[ModelCapabilityCard] = []
    for role, selection in selections.items():
        exists = bool(_read_attr_or_key(selection, "exists", False))
        source = str(_read_attr_or_key(selection, "source", "local_model_selection"))
        canonical_id = f"local/{_clean_token(role)}"
        cards.append(
            ModelCapabilityCard(
                provider="local",
                model_id=canonical_id,
                canonical_model_id=canonical_id,
                source=source or "local_model_selection",
                availability=Availability.AVAILABLE if exists else Availability.UNAVAILABLE,
                freshness="local_probe",
                promotion_state=PromotionState.CANDIDATE if exists else PromotionState.CHALLENGER,
                task_families=(_clean_token(role),),
                privacy_policy="local_runtime",
            ).normalized()
        )
    return tuple(sorted(cards, key=lambda card: card.canonical_model_id))


def build_canonical_model_catalog(
    *,
    static_registry: bool = True,
    openrouter_payload: Mapping[str, Any] | None = None,
    local_role_selections: Mapping[str, Any] | None = None,
    source_receipts: Sequence[str] | None = None,
    generated_at: str | None = None,
) -> ModelCatalogSnapshot:
    """Build a catalog snapshot from the supplied evidence sources."""

    cards: list[ModelCapabilityCard] = []
    rejected: list[ModelCatalogRejectedRecord] = []
    if static_registry:
        cards.extend(normalize_static_registry_cards())
    if openrouter_payload is not None:
        openrouter_cards, openrouter_rejected = normalize_openrouter_catalog(openrouter_payload)
        cards.extend(openrouter_cards)
        rejected.extend(openrouter_rejected)
    if local_role_selections is not None:
        cards.extend(normalize_local_role_cards(local_role_selections))
    return build_model_catalog_snapshot(
        cards,
        source_receipts=source_receipts,
        rejected_records=rejected,
        generated_at=generated_at,
    )


def _task_index(recommended_models: Mapping[str, Sequence[str]]) -> dict[str, tuple[str, ...]]:
    index: dict[str, set[str]] = {}
    for task, model_ids in recommended_models.items():
        for model_id in model_ids:
            index.setdefault(str(model_id), set()).add(str(task))
    return {model_id: tuple(sorted(tasks)) for model_id, tasks in index.items()}


def _promotion_from_registry_status(status: Any) -> PromotionState:
    if status == ModelStatus.CURRENT:
        return PromotionState.CANDIDATE
    if status == ModelStatus.LEGACY:
        return PromotionState.CHALLENGER
    if status == ModelStatus.DEPRECATED:
        return PromotionState.DEPRECATED
    if status == ModelStatus.SUNSET:
        return PromotionState.BLOCKED
    return PromotionState.CANDIDATE


def _modalities_from_openrouter(architecture: Mapping[str, Any]) -> tuple[str, ...]:
    values: list[str] = []
    values.extend(_string_tuple(architecture.get("input_modalities")))
    values.extend(_string_tuple(architecture.get("output_modalities")))
    return tuple(sorted(set(values))) or ("text",)


def _string_tuple(value: Any) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return ()
    return tuple(str(item).strip() for item in value if str(item).strip())


def _positive_int(value: Any) -> int | None:
    try:
        parsed = int(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return parsed if parsed > 0 else None


def _per_million(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    if not math.isfinite(parsed) or parsed < 0:
        return None
    return round(parsed * 1_000_000, 10)


def _read_attr_or_key(value: Any, name: str, default: Any) -> Any:
    if isinstance(value, Mapping):
        return value.get(name, default)
    return getattr(value, name, default)


def _clean_token(value: Any) -> str:
    return str(value).strip().lower().replace(" ", "_")


def _card_to_json(card: ModelCapabilityCard) -> dict[str, Any]:
    data = asdict(card.normalized())
    data["availability"] = card.availability.value
    data["promotion_state"] = card.promotion_state.value
    data["task_families"] = list(card.task_families)
    data["modalities"] = list(card.modalities)
    data["supported_parameters"] = list(card.supported_parameters)
    data["benchmark_scores"] = dict(sorted(card.benchmark_scores.items()))
    return data


def _reject_openrouter_record(record: Any, reason: str) -> ModelCatalogRejectedRecord:
    return ModelCatalogRejectedRecord(
        source="openrouter_catalog",
        reason=reason,
        record_digest=_digest_prefixed("rejected_record", record),
    )


def _normalize_openrouter_record(
    record: Any,
) -> ModelCapabilityCard | ModelCatalogRejectedRecord:
    if not isinstance(record, Mapping):
        return _reject_openrouter_record(record, "record_not_mapping")
    model_id = str(record.get("id") or "").strip()
    if not model_id:
        return _reject_openrouter_record(record, "missing_model_id")
    architecture = record.get("architecture")
    architecture = architecture if isinstance(architecture, Mapping) else {}
    pricing = record.get("pricing")
    pricing = pricing if isinstance(pricing, Mapping) else {}
    supported_parameters = _string_tuple(record.get("supported_parameters"))
    return ModelCapabilityCard(
        provider="openrouter",
        model_id=model_id,
        canonical_model_id=model_id,
        source="openrouter_catalog",
        availability=Availability.UNKNOWN,
        freshness="provider_catalog_listing",
        promotion_state=PromotionState.CANDIDATE,
        task_families=(),
        context_window=_positive_int(record.get("context_length")),
        input_cost_per_million=_per_million(pricing.get("prompt")),
        output_cost_per_million=_per_million(pricing.get("completion")),
        supports_tools=bool({"tools", "tool_choice"} & set(supported_parameters)),
        supports_structured_output=bool(
            {"response_format", "structured_outputs"} & set(supported_parameters)
        ),
        supports_reasoning="reasoning" in set(supported_parameters),
        modalities=_modalities_from_openrouter(architecture),
        supported_parameters=supported_parameters,
        privacy_policy="provider_policy_unknown",
    ).normalized()


def _digest_prefixed(prefix: str, value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return f"{prefix}:{hashlib.sha256(encoded).hexdigest()}"
