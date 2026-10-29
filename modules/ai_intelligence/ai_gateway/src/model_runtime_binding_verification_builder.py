"""Build durable receipts from canonically verified model evidence."""

from __future__ import annotations

from typing import Any

from .model_intelligence_selection import ModelSelectionReceipt, SelectionMode
from .model_panel_signed_evidence import VerifiedModelPanelEvidence
from .model_runtime_binding import (
    ModelRuntimeBindingDecision,
    RedDogModelRuntimeBindingReceipt,
)
from .model_runtime_binding_verification_receipt import (
    SCHEMA_VERSION,
    ModelRuntimeBindingVerificationReceipt,
    canonical_digest,
    prefixed_digest,
    required_digest,
)
from .model_signed_evidence import VerifiedModelProductionEvidence


VerifiedEvidence = VerifiedModelProductionEvidence | VerifiedModelPanelEvidence


def build_runtime_binding_verification_receipt(
    *,
    binding: RedDogModelRuntimeBindingReceipt,
    selection: ModelSelectionReceipt,
    evidence: VerifiedEvidence,
    catalog_snapshot_digest: str,
    runtime_policy_digest: str,
    evidence_bundle_digest: str,
    trusted_keys_digest: str,
    verified_at: int,
) -> ModelRuntimeBindingVerificationReceipt:
    """Build durable evidence after the canonical signature verifier succeeds."""

    _validate_binding(binding, selection)
    entries = _verified_entries(selection, evidence)
    projection = _evidence_projection(entries)
    _assert_evidence_ids(binding, projection)
    valid_until = _valid_until(entries, evidence)
    if verified_at <= 0 or valid_until < verified_at:
        raise ValueError("runtime_binding_evidence_expired")
    body = _receipt_body(
        binding=binding,
        selection=selection,
        evidence=evidence,
        projection=projection,
        catalog_snapshot_digest=catalog_snapshot_digest,
        runtime_policy_digest=runtime_policy_digest,
        evidence_bundle_digest=evidence_bundle_digest,
        trusted_keys_digest=trusted_keys_digest,
        verified_at=verified_at,
        valid_until=valid_until,
    )
    return ModelRuntimeBindingVerificationReceipt(
        receipt_id=prefixed_digest("model_runtime_binding_verification", body),
        **body,
    )


def _receipt_body(
    *,
    binding: RedDogModelRuntimeBindingReceipt,
    selection: ModelSelectionReceipt,
    evidence: VerifiedEvidence,
    projection: tuple[dict[str, Any], ...],
    catalog_snapshot_digest: str,
    runtime_policy_digest: str,
    evidence_bundle_digest: str,
    trusted_keys_digest: str,
    verified_at: int,
    valid_until: int,
) -> dict[str, Any]:
    panel_id, panel_digest = _panel_fields(evidence)
    return {
        "schema_version": SCHEMA_VERSION,
        "runtime_binding_receipt_id": binding.receipt_id,
        "runtime_binding_digest": canonical_digest(binding.to_dict()),
        "selection_receipt_id": selection.receipt_id,
        "selection_receipt_digest": canonical_digest(selection.to_dict()),
        "catalog_snapshot_digest": required_digest(
            catalog_snapshot_digest, "catalog_snapshot_digest"
        ),
        "runtime_policy_digest": required_digest(
            runtime_policy_digest, "runtime_policy_digest"
        ),
        "evidence_bundle_digest": required_digest(
            evidence_bundle_digest, "evidence_bundle_digest"
        ),
        "trusted_keys_digest": required_digest(
            trusted_keys_digest, "trusted_keys_digest"
        ),
        "evidence_projection_digest": canonical_digest(projection),
        "selection_mode": selection.requirements.selection_mode.value,
        "model_ids": tuple(sorted(item["model_id"] for item in projection)),
        "benchmark_evidence_receipt_ids": tuple(
            binding.benchmark_evidence_receipt_ids
        ),
        "promotion_evidence_receipt_ids": tuple(
            binding.promotion_evidence_receipt_ids
        ),
        "signed_promotion_receipt_ids": tuple(binding.signed_promotion_receipt_ids),
        "verified_at": int(verified_at),
        "valid_until": valid_until,
        "panel_aggregate_receipt_id": panel_id,
        "panel_aggregate_receipt_digest": panel_digest,
    }


def _validate_binding(
    binding: RedDogModelRuntimeBindingReceipt,
    selection: ModelSelectionReceipt,
) -> None:
    if binding.decision != ModelRuntimeBindingDecision.BOUND:
        raise ValueError("runtime_binding_not_bound")
    if binding.selection_receipt_id != selection.receipt_id:
        raise ValueError("runtime_binding_selection_mismatch")


def _verified_entries(
    selection: ModelSelectionReceipt,
    evidence: VerifiedEvidence,
) -> tuple[Any, ...]:
    if selection.requirements.selection_mode == SelectionMode.PANEL:
        if not isinstance(evidence, VerifiedModelPanelEvidence):
            raise ValueError("verified_panel_evidence_required")
        if evidence.panel_signed_evidence_verified is not True:
            raise ValueError("verified_panel_evidence_required")
        return evidence.member_entries
    if not isinstance(evidence, VerifiedModelProductionEvidence):
        raise ValueError("verified_model_evidence_required")
    if evidence.signed_evidence_verified is not True:
        raise ValueError("verified_model_evidence_required")
    return evidence.entries


def _evidence_projection(entries: tuple[Any, ...]) -> tuple[dict[str, Any], ...]:
    return tuple(
        {
            "model_id": item.model_id,
            "benchmark": item.benchmark_receipt.to_dict(),
            "promotion": item.promotion_receipt.to_dict(),
            "benchmark_signature": item.benchmark_signature_receipt.to_dict(),
            "promotion_signature": item.promotion_signature_receipt.to_dict(),
        }
        for item in entries
    )


def _assert_evidence_ids(
    binding: RedDogModelRuntimeBindingReceipt,
    projection: tuple[dict[str, Any], ...],
) -> None:
    expected = (
        tuple(sorted(item["benchmark"]["receipt_id"] for item in projection)),
        tuple(sorted(item["promotion"]["receipt_id"] for item in projection)),
        tuple(
            sorted(
                item["promotion"]["signed_promotion_receipt_id"]
                for item in projection
            )
        ),
    )
    actual = (
        tuple(binding.benchmark_evidence_receipt_ids),
        tuple(binding.promotion_evidence_receipt_ids),
        tuple(binding.signed_promotion_receipt_ids),
    )
    if actual != expected:
        raise ValueError("runtime_binding_evidence_ids_mismatch")


def _valid_until(entries: tuple[Any, ...], evidence: VerifiedEvidence) -> int:
    expiries = [
        int(receipt.expires_at)
        for entry in entries
        for receipt in (
            entry.benchmark_signature_receipt,
            entry.promotion_signature_receipt,
        )
    ]
    if isinstance(evidence, VerifiedModelPanelEvidence):
        expiries.append(int(evidence.aggregate_receipt.expires_at))
    return min(expiries)


def _panel_fields(evidence: VerifiedEvidence) -> tuple[str | None, str | None]:
    if not isinstance(evidence, VerifiedModelPanelEvidence):
        return None, None
    receipt = evidence.aggregate_receipt
    return receipt.receipt_id, canonical_digest(receipt.to_dict())


__all__ = ["build_runtime_binding_verification_receipt"]
