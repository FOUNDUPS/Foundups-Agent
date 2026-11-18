"""External evidence preflight for one authenticated production candidate."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import (
    SignatureVerifier,
)

from .model_selection_artifact_supply import EVIDENCE_BUNDLE_SCHEMA_VERSION
from .model_signed_evidence import (
    ModelEvidenceKeyResolver,
    build_verified_model_production_evidence,
    rehydrate_model_benchmark_evidence_receipt,
    rehydrate_model_promotion_evidence_receipt,
    rehydrate_model_signed_evidence_receipt,
)


def verify_external_single_model_evidence_bundle(
    *,
    bundle: Mapping[str, Any],
    preview: Any,
    gate: Any,
    key_resolver: ModelEvidenceKeyResolver,
    signature_verifier: SignatureVerifier,
    revoked_key_epochs: Sequence[str],
    now: int,
) -> tuple[Any, Any, Any, Any, Any]:
    entry = _validated_entry(bundle, preview)
    benchmark = rehydrate_model_benchmark_evidence_receipt(
        _mapping(entry.get("benchmark_receipt"), "benchmark_receipt")
    )
    promotion = rehydrate_model_promotion_evidence_receipt(
        _mapping(entry.get("promotion_receipt"), "promotion_receipt"),
        benchmark_receipt=benchmark,
    )
    _require_gate_evidence(benchmark, promotion, preview, gate)
    benchmark_signature = rehydrate_model_signed_evidence_receipt(
        _mapping(entry.get("benchmark_signature_receipt"), "benchmark_signature_receipt")
    )
    promotion_signature = rehydrate_model_signed_evidence_receipt(
        _mapping(entry.get("promotion_signature_receipt"), "promotion_signature_receipt")
    )
    if promotion_signature.promotion_policy_digest != preview.promotion_policy_digest:
        raise ValueError("single_model_production_policy_signature_mismatch")
    verified = _verify_chain(
        bundle=bundle,
        preview=preview,
        benchmark=benchmark,
        promotion=promotion,
        benchmark_signature=benchmark_signature,
        promotion_signature=promotion_signature,
        key_resolver=key_resolver,
        signature_verifier=signature_verifier,
        revoked_key_epochs=revoked_key_epochs,
        now=now,
    )
    return verified, benchmark, promotion, benchmark_signature, promotion_signature


def _validated_entry(bundle: Mapping[str, Any], preview: Any) -> Mapping[str, Any]:
    if not isinstance(bundle, Mapping) or bundle.get(
        "schema_version"
    ) != EVIDENCE_BUNDLE_SCHEMA_VERSION:
        raise ValueError("single_model_production_evidence_bundle_invalid")
    if (
        bundle.get("catalog_snapshot_id") != preview.catalog_snapshot_id
        or bundle.get("selection_receipt_id") != preview.selection_receipt_id
    ):
        raise ValueError("single_model_production_evidence_preview_mismatch")
    entries = bundle.get("entries")
    if (
        not isinstance(entries, list)
        or len(entries) != 1
        or not isinstance(entries[0], Mapping)
    ):
        raise ValueError("single_model_production_evidence_entry_invalid")
    return entries[0]


def _require_gate_evidence(benchmark: Any, promotion: Any, preview: Any, gate: Any) -> None:
    if (
        benchmark.model_id != preview.candidate_model_id
        or benchmark.receipt_id != gate.benchmark_evidence_receipt_id
        or promotion.receipt_id != preview.promotion_evidence_receipt_id
        or promotion.to_dict() != gate.promotion_evidence_receipt.to_dict()
    ):
        raise ValueError("single_model_production_gate_evidence_mismatch")


def _verify_chain(**values: Any) -> Any:
    bundle = values["bundle"]
    return build_verified_model_production_evidence(
        catalog_snapshot_id=values["preview"].catalog_snapshot_id,
        selection_receipt_id=values["preview"].selection_receipt_id,
        benchmark_run_receipt_id=_required(
            bundle.get("benchmark_run_receipt_id"), "benchmark_run_receipt_id"
        ),
        benchmark_receipt=values["benchmark"],
        promotion_receipt=values["promotion"],
        benchmark_signature_receipt=values["benchmark_signature"],
        promotion_signature_receipt=values["promotion_signature"],
        key_resolver=values["key_resolver"],
        signature_verifier=values["signature_verifier"],
        now=values["now"],
        consume_nonces=False,
        revoked_key_epochs=values["revoked_key_epochs"],
    )


def _mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(name + "_invalid")
    return value


def _required(value: Any, name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(name + "_missing")
    return text


__all__ = ["verify_external_single_model_evidence_bundle"]
