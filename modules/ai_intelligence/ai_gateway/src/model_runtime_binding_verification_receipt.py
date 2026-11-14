"""Durable structural receipt for a verified model-runtime binding."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping

from .model_intelligence_selection import SelectionMode
from .model_runtime_binding import RedDogModelRuntimeBindingReceipt
from .model_runtime_binding_digest import (
    canonical_digest,
    canonical_model_runtime_binding_digest,
    prefixed_digest,
    required_digest,
)
from .model_signed_evidence import rehydrate_model_runtime_binding_receipt


SCHEMA_VERSION = "model_runtime_binding_verification_receipt.v1"


@dataclass(frozen=True)
class ModelRuntimeBindingVerificationReceipt:
    schema_version: str
    receipt_id: str
    runtime_binding_receipt_id: str
    runtime_binding_digest: str
    selection_receipt_id: str
    selection_receipt_digest: str
    catalog_snapshot_digest: str
    runtime_policy_digest: str
    evidence_bundle_digest: str
    trusted_keys_digest: str
    evidence_projection_digest: str
    selection_mode: str
    model_ids: tuple[str, ...]
    benchmark_evidence_receipt_ids: tuple[str, ...]
    promotion_evidence_receipt_ids: tuple[str, ...]
    signed_promotion_receipt_ids: tuple[str, ...]
    verified_at: int
    valid_until: int
    panel_aggregate_receipt_id: str | None = None
    panel_aggregate_receipt_digest: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def rehydrate_runtime_binding_verification_receipt(
    value: Mapping[str, Any],
) -> ModelRuntimeBindingVerificationReceipt:
    if value.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("runtime_binding_verification_schema_invalid")
    body = _receipt_body(value)
    expected_id = prefixed_digest("model_runtime_binding_verification", body)
    if value.get("receipt_id") != expected_id:
        raise ValueError("runtime_binding_verification_receipt_id_invalid")
    _validate_body(body)
    return ModelRuntimeBindingVerificationReceipt(receipt_id=expected_id, **body)


def verification_receipt_digest(
    receipt: ModelRuntimeBindingVerificationReceipt,
) -> str:
    return canonical_digest(receipt.to_dict())


def verified_runtime_binding_receipt(
    binding: RedDogModelRuntimeBindingReceipt | Mapping[str, Any],
) -> ModelRuntimeBindingVerificationReceipt | None:
    """Validate the embedded receipt structurally without granting authority."""

    if isinstance(binding, RedDogModelRuntimeBindingReceipt):
        return None
    raw = binding.get("verification_receipt")
    if not isinstance(raw, Mapping):
        return None
    try:
        receipt = rehydrate_runtime_binding_verification_receipt(raw)
        canonical_binding = rehydrate_model_runtime_binding_receipt(binding)
    except Exception:
        return None
    expected = (
        canonical_binding.receipt_id,
        canonical_digest(canonical_binding.to_dict()),
        canonical_binding.selection_receipt_id,
    )
    actual = (
        receipt.runtime_binding_receipt_id,
        receipt.runtime_binding_digest,
        receipt.selection_receipt_id,
    )
    return receipt if actual == expected else None


def _receipt_body(value: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "runtime_binding_receipt_id": _required(value, "runtime_binding_receipt_id"),
        "runtime_binding_digest": required_digest(
            value.get("runtime_binding_digest"), "runtime_binding_digest"
        ),
        "selection_receipt_id": _required(value, "selection_receipt_id"),
        "selection_receipt_digest": required_digest(
            value.get("selection_receipt_digest"), "selection_receipt_digest"
        ),
        "catalog_snapshot_digest": required_digest(
            value.get("catalog_snapshot_digest"), "catalog_snapshot_digest"
        ),
        "runtime_policy_digest": required_digest(
            value.get("runtime_policy_digest"), "runtime_policy_digest"
        ),
        "evidence_bundle_digest": required_digest(
            value.get("evidence_bundle_digest"), "evidence_bundle_digest"
        ),
        "trusted_keys_digest": required_digest(
            value.get("trusted_keys_digest"), "trusted_keys_digest"
        ),
        "evidence_projection_digest": required_digest(
            value.get("evidence_projection_digest"), "evidence_projection_digest"
        ),
        "selection_mode": SelectionMode(str(value.get("selection_mode"))).value,
        "model_ids": _string_tuple(value, "model_ids"),
        "benchmark_evidence_receipt_ids": _string_tuple(
            value, "benchmark_evidence_receipt_ids"
        ),
        "promotion_evidence_receipt_ids": _string_tuple(
            value, "promotion_evidence_receipt_ids"
        ),
        "signed_promotion_receipt_ids": _string_tuple(
            value, "signed_promotion_receipt_ids"
        ),
        "verified_at": int(value.get("verified_at") or 0),
        "valid_until": int(value.get("valid_until") or 0),
        "panel_aggregate_receipt_id": _optional(value.get("panel_aggregate_receipt_id")),
        "panel_aggregate_receipt_digest": _optional_digest(
            value.get("panel_aggregate_receipt_digest")
        ),
    }


def _validate_body(body: Mapping[str, Any]) -> None:
    if body["verified_at"] <= 0 or body["valid_until"] < body["verified_at"]:
        raise ValueError("runtime_binding_verification_time_invalid")
    if bool(body["panel_aggregate_receipt_id"]) != bool(
        body["panel_aggregate_receipt_digest"]
    ):
        raise ValueError("runtime_binding_panel_evidence_incomplete")


def _required(value: Mapping[str, Any], name: str) -> str:
    text = str(value.get(name) or "").strip()
    if not text:
        raise ValueError(f"{name}_missing")
    return text


def _string_tuple(value: Mapping[str, Any], name: str) -> tuple[str, ...]:
    raw = value.get(name)
    if not isinstance(raw, (list, tuple)) or not raw:
        raise ValueError(f"{name}_invalid")
    result = tuple(str(item).strip() for item in raw)
    if any(not item for item in result) or len(result) != len(set(result)):
        raise ValueError(f"{name}_invalid")
    return result


def _optional_digest(value: Any) -> str | None:
    text = _optional(value)
    return required_digest(text, "optional_digest") if text else None


def _optional(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


__all__ = ["ModelRuntimeBindingVerificationReceipt", "SCHEMA_VERSION",
           "canonical_digest", "canonical_model_runtime_binding_digest",
           "prefixed_digest", "rehydrate_runtime_binding_verification_receipt",
           "required_digest", "verification_receipt_digest",
           "verified_runtime_binding_receipt"]
