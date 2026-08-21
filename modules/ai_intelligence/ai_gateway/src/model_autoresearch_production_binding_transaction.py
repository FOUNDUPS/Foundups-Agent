"""Durable publication and transactional output claims for production binding."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from .model_autoresearch_authenticated_promotion_authority import (
    AuthenticatedCampaignPromotionSupplyResult,
)
from .model_autoresearch_configured_gateway_evidence import (
    DurableExactPublicationStore,
    digest_payload,
)
from .model_signed_evidence import ModelSignedEvidenceReceipt


@dataclass(frozen=True)
class OutputClaim:
    path: Path


def claim_output_paths(*paths: Path) -> tuple[OutputClaim, ...]:
    claims: list[OutputClaim] = []
    try:
        for path in paths:
            path.parent.mkdir(parents=True, exist_ok=True)
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            os.close(fd)
            claims.append(OutputClaim(path))
    except Exception:
        cleanup_claimed_outputs(claims, expected_selection_receipt_id=None)
        raise ValueError("single_model_production_output_claim_failed") from None
    return tuple(claims)


def cleanup_claimed_outputs(
    claims: Sequence[OutputClaim],
    *,
    expected_selection_receipt_id: str | None,
) -> None:
    for claim in claims:
        _cleanup_owned_output(
            claim.path,
            expected_selection_receipt_id=expected_selection_receipt_id,
        )


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


def _cleanup_owned_output(
    path: Path,
    *,
    expected_selection_receipt_id: str | None,
) -> None:
    try:
        if not path.is_file():
            return
        if path.stat().st_size == 0:
            path.unlink()
            return
        if expected_selection_receipt_id is None:
            return
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, Mapping):
            return
        if (
            payload.get("receipt_id") == expected_selection_receipt_id
            or payload.get("selection_receipt_id") == expected_selection_receipt_id
        ):
            path.unlink()
    except (OSError, ValueError, json.JSONDecodeError):
        return


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
    "OutputClaim",
    "advance_publication",
    "claim_output_paths",
    "cleanup_claimed_outputs",
    "production_publication_binding",
    "reserve_evidence_publications",
]
