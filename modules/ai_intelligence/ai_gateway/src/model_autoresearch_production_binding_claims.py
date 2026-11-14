"""Durable claim and provider-bundle records for restart-safe binding."""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .model_autoresearch_configured_gateway_evidence import digest_payload


@dataclass(frozen=True)
class ProductionBindingClaimReceipt:
    receipt_id: str
    binding_digest: str
    token: str
    selection_stage: str
    runtime_stage: str
    schema_version: str = "single_model_production_claim.v1"

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "receipt_id": self.receipt_id,
            "binding_digest": self.binding_digest,
            "token": self.token,
            "selection_stage": self.selection_stage,
            "runtime_stage": self.runtime_stage,
        }


@dataclass(frozen=True)
class ProductionBindingProviderReceipt:
    receipt_id: str
    binding_digest: str
    bundle: Mapping[str, Any]
    schema_version: str = "single_model_production_provider_bundle.v1"

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "receipt_id": self.receipt_id,
            "binding_digest": self.binding_digest,
            "bundle": dict(self.bundle),
        }


def load_or_create_claim(inputs: Mapping[str, Any]) -> ProductionBindingClaimReceipt:
    identity = inputs["publication_identity"]
    receipt_id = "single-model-production-claim:" + identity.binding_digest
    stored = _load_optional(inputs, receipt_id, "claim")
    if stored is not None:
        return _rehydrate_claim(stored, inputs)
    token = secrets.token_hex(16)
    receipt = ProductionBindingClaimReceipt(
        receipt_id=receipt_id,
        binding_digest=identity.binding_digest,
        token=token,
        selection_stage=str(_stage_path(inputs["selection_output"], token)),
        runtime_stage=str(_stage_path(inputs["runtime_output"], token)),
    )
    try:
        _append(inputs, receipt, "claim")
        return receipt
    except ValueError:
        winner = _load_optional(inputs, receipt_id, "claim")
        if winner is None:
            raise
        return _rehydrate_claim(winner, inputs)


def load_provider_bundle(inputs: Mapping[str, Any]) -> Mapping[str, Any] | None:
    identity = inputs["publication_identity"]
    receipt_id = "single-model-production-provider:" + identity.binding_digest
    payload = _load_optional(inputs, receipt_id, "provider")
    if payload is None:
        return None
    if (
        payload.get("schema_version") != "single_model_production_provider_bundle.v1"
        or payload.get("receipt_id") != receipt_id
        or payload.get("binding_digest") != identity.binding_digest
        or not isinstance(payload.get("bundle"), Mapping)
    ):
        raise ValueError("single_model_production_provider_receipt_invalid")
    return dict(payload["bundle"])


def persist_provider_bundle(
    inputs: Mapping[str, Any], bundle: Mapping[str, Any]
) -> Mapping[str, Any]:
    if not isinstance(bundle, Mapping):
        raise ValueError("single_model_production_evidence_bundle_invalid")
    identity = inputs["publication_identity"]
    receipt = ProductionBindingProviderReceipt(
        receipt_id="single-model-production-provider:" + identity.binding_digest,
        binding_digest=identity.binding_digest,
        bundle=dict(bundle),
    )
    _append(inputs, receipt, "provider")
    stored = load_provider_bundle(inputs)
    if stored is None or digest_payload(stored) != digest_payload(bundle):
        raise ValueError("single_model_production_provider_persistence_failed")
    return stored


def _rehydrate_claim(
    payload: Mapping[str, Any], inputs: Mapping[str, Any]
) -> ProductionBindingClaimReceipt:
    identity = inputs["publication_identity"]
    try:
        receipt = ProductionBindingClaimReceipt(
            receipt_id=str(payload["receipt_id"]),
            binding_digest=str(payload["binding_digest"]),
            token=str(payload["token"]),
            selection_stage=str(payload["selection_stage"]),
            runtime_stage=str(payload["runtime_stage"]),
            schema_version=str(payload["schema_version"]),
        )
    except (KeyError, TypeError):
        raise ValueError("single_model_production_claim_receipt_invalid") from None
    expected_id = "single-model-production-claim:" + identity.binding_digest
    if (
        receipt.schema_version != "single_model_production_claim.v1"
        or receipt.receipt_id != expected_id
        or receipt.binding_digest != identity.binding_digest
        or len(receipt.token) != 32
        or receipt.selection_stage
        != str(_stage_path(inputs["selection_output"], receipt.token))
        or receipt.runtime_stage
        != str(_stage_path(inputs["runtime_output"], receipt.token))
    ):
        raise ValueError("single_model_production_claim_receipt_invalid")
    return receipt


def _append(inputs: Mapping[str, Any], receipt: object, kind: str) -> None:
    operation = getattr(inputs["authority_use"].receipt_store, "append", None)
    if not callable(operation):
        raise ValueError(f"single_model_production_{kind}_store_invalid")
    expected = getattr(receipt, "receipt_id")
    try:
        stored = operation(receipt)
    except Exception:
        raise ValueError(f"single_model_production_{kind}_persistence_failed") from None
    if stored != expected:
        raise ValueError(f"single_model_production_{kind}_persistence_failed")


def _load_optional(
    inputs: Mapping[str, Any], receipt_id: str, kind: str
) -> Mapping[str, Any] | None:
    store = inputs["authority_use"].receipt_store
    try:
        payload = store.load(receipt_id)
    except Exception:
        contains = getattr(store, "contains_receipt", None)
        if not callable(contains):
            raise ValueError(
                f"single_model_production_{kind}_receipt_presence_unprovable"
            ) from None
        try:
            if contains(receipt_id) is False:
                return None
        except Exception:
            pass
        raise ValueError(f"single_model_production_{kind}_receipt_unreadable") from None
    if not isinstance(payload, Mapping):
        raise ValueError("single_model_production_claim_receipt_invalid")
    return payload


def _stage_path(output: Path, token: str) -> Path:
    return output.with_name(f".{output.name}.{token}.staging")


__all__ = [
    "ProductionBindingClaimReceipt",
    "load_or_create_claim",
    "load_provider_bundle",
    "persist_provider_bundle",
]
