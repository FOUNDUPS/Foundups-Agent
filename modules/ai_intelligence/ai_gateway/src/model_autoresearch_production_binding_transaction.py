"""Durable publication identity and evidence reservations for production binding."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .model_autoresearch_authenticated_promotion_authority import (
    AuthenticatedCampaignPromotionSupplyResult,
)
from .model_autoresearch_configured_gateway_evidence import (
    DurableExactPublicationStore,
    digest_payload,
)
from .model_signed_evidence import ModelSignedEvidenceReceipt


@dataclass(frozen=True)
class ProductionPublicationIdentity:
    nonce: str
    binding_digest: str
    terminal_receipt_id: str


def production_publication_binding(
    *,
    authenticated_promotion: AuthenticatedCampaignPromotionSupplyResult,
    preview: Any,
    runtime_policy: Mapping[str, Any],
    trusted_keys: Mapping[str, Any],
    selection_output: Path,
    runtime_output: Path,
) -> str:
    return digest_payload(
        {
            "kind": "single_model_production_authority_use.v1",
            "authority_request": authenticated_promotion.authority.request.to_dict(),
            "authority_receipt": authenticated_promotion.authority.receipt.to_dict(),
            "preview": _preview_payload(preview),
            "runtime_policy": dict(runtime_policy),
            "trusted_keys": dict(trusted_keys),
            "selection_output_path": str(selection_output),
            "runtime_output_path": str(runtime_output),
        }
    )


def production_publication_identity(**values: Any) -> ProductionPublicationIdentity:
    authenticated = values["authenticated_promotion"]
    binding = production_publication_binding(**values)
    nonce = "single-model-production-authority-use:" + (
        authenticated.authority.receipt.receipt_id
    )
    return ProductionPublicationIdentity(
        nonce=nonce,
        binding_digest=binding,
        terminal_receipt_id="single-model-production-terminal:" + binding,
    )


def publication_status(
    store: DurableExactPublicationStore,
    identity: ProductionPublicationIdentity,
) -> str | None:
    if getattr(store, "durable", None) is not True:
        raise ValueError("single_model_production_durable_publication_store_required")
    operation = getattr(store, "publication_status", None)
    if not callable(operation):
        raise ValueError("single_model_production_durable_publication_store_required")
    try:
        return operation(identity.nonce, identity.binding_digest)
    except Exception:
        raise ValueError("single_model_production_authority_binding_conflict") from None


def advance_publication(
    store: DurableExactPublicationStore,
    *,
    nonce: str,
    binding_digest: str,
    target_status: str,
) -> str:
    if getattr(store, "durable", None) is not True:
        raise ValueError("single_model_production_durable_publication_store_required")
    operation = getattr(store, "advance_publication", None)
    if not callable(operation):
        raise ValueError("single_model_production_durable_publication_store_required")
    try:
        status = str(operation(nonce, binding_digest, target_status) or "")
    except Exception:
        raise ValueError("single_model_production_publication_failed") from None
    allowed = {
        "RESERVED": {"RESERVED", "AUTHORIZED", "APPLIED"},
        "AUTHORIZED": {"AUTHORIZED", "APPLIED"},
        "APPLIED": {"APPLIED"},
    }
    if target_status not in allowed or status not in allowed[target_status]:
        raise ValueError("single_model_production_publication_failed")
    return status


def reserve_evidence_publications(
    store: DurableExactPublicationStore,
    *receipts: ModelSignedEvidenceReceipt,
    use_binding_digest: str,
) -> tuple[tuple[str, str], ...]:
    result: list[tuple[str, str]] = []
    for receipt in receipts:
        nonce, binding = _evidence_publication(receipt, use_binding_digest)
        status = advance_publication(
            store,
            nonce=nonce,
            binding_digest=binding,
            target_status="RESERVED",
        )
        if status == "APPLIED":
            raise ValueError("single_model_production_evidence_replay")
        advance_publication(
            store,
            nonce=nonce,
            binding_digest=binding,
            target_status="AUTHORIZED",
        )
        result.append((nonce, binding))
    return tuple(result)


def _preview_payload(preview: Any) -> dict[str, Any]:
    return {
        "selection_receipt_id": preview.selection_receipt_id,
        "catalog_snapshot_id": preview.catalog_snapshot_id,
        "candidate_model_id": preview.candidate_model_id,
        "promotion_gate_receipt_id": preview.promotion_gate_receipt_id,
        "promotion_evidence_receipt_id": preview.promotion_evidence_receipt_id,
        "promotion_policy_digest": preview.promotion_policy_digest,
    }


def _evidence_publication(
    receipt: ModelSignedEvidenceReceipt,
    use_binding_digest: str,
) -> tuple[str, str]:
    nonce = "single-model-production-evidence:" + receipt.nonce
    binding = digest_payload(
        {
            "kind": "single_model_production_evidence_use.v1",
            "receipt_id": receipt.receipt_id,
            "receipt_digest": digest_payload(receipt.to_dict()),
            "use_binding_digest": use_binding_digest,
        }
    )
    return nonce, binding


__all__ = [
    "ProductionPublicationIdentity",
    "advance_publication",
    "production_publication_binding",
    "production_publication_identity",
    "publication_status",
    "reserve_evidence_publications",
]
