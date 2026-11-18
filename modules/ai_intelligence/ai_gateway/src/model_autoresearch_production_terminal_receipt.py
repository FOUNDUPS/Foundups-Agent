"""Bounded durable terminal receipt for production-binding recovery."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .model_autoresearch_production_binding_transaction import (
    ProductionPublicationIdentity,
)


@dataclass(frozen=True)
class ProductionBindingTerminalReceipt:
    receipt_id: str
    nonce: str
    binding_digest: str
    selection_digest: str
    runtime_digest: str
    selection_proof: Mapping[str, Any]
    runtime_proof: Mapping[str, Any]
    selection_source: str | None
    runtime_source: str | None
    verified_evidence_bundle: Mapping[str, Any]
    schema_version: str = "single_model_production_terminal.v3"

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "receipt_id": self.receipt_id,
            "nonce": self.nonce,
            "binding_digest": self.binding_digest,
            "selection_digest": self.selection_digest,
            "runtime_digest": self.runtime_digest,
            "selection_proof": dict(self.selection_proof),
            "runtime_proof": dict(self.runtime_proof),
            "selection_source": self.selection_source,
            "runtime_source": self.runtime_source,
            "verified_evidence_bundle": dict(self.verified_evidence_bundle),
        }


def rehydrate_production_terminal_receipt(
    payload: Mapping[str, Any],
    identity: ProductionPublicationIdentity,
) -> ProductionBindingTerminalReceipt:
    try:
        receipt = ProductionBindingTerminalReceipt(
            receipt_id=str(payload["receipt_id"]),
            nonce=str(payload["nonce"]),
            binding_digest=str(payload["binding_digest"]),
            selection_digest=str(payload["selection_digest"]),
            runtime_digest=str(payload["runtime_digest"]),
            selection_proof=payload["selection_proof"],
            runtime_proof=payload["runtime_proof"],
            selection_source=(
                str(payload["selection_source"])
                if payload.get("selection_source") is not None
                else None
            ),
            runtime_source=(
                str(payload["runtime_source"])
                if payload.get("runtime_source") is not None
                else None
            ),
            verified_evidence_bundle=payload["verified_evidence_bundle"],
            schema_version=str(payload["schema_version"]),
        )
    except (KeyError, TypeError):
        raise ValueError("single_model_production_terminal_receipt_invalid") from None
    if (
        receipt.schema_version
        not in {
            "single_model_production_terminal.v2",
            "single_model_production_terminal.v3",
        }
        or receipt.receipt_id != identity.terminal_receipt_id
        or receipt.nonce != identity.nonce
        or receipt.binding_digest != identity.binding_digest
        or not isinstance(receipt.selection_proof, Mapping)
        or not isinstance(receipt.runtime_proof, Mapping)
        or not isinstance(receipt.verified_evidence_bundle, Mapping)
        or (
            receipt.schema_version == "single_model_production_terminal.v3"
            and (not receipt.selection_source or not receipt.runtime_source)
        )
    ):
        raise ValueError("single_model_production_terminal_receipt_invalid")
    return receipt


__all__ = [
    "ProductionBindingTerminalReceipt",
    "rehydrate_production_terminal_receipt",
]
