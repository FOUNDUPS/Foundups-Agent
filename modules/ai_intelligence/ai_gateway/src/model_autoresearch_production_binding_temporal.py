"""Pure final temporal checks after production trust callbacks return."""

from __future__ import annotations

from typing import Any, Mapping

from .model_autoresearch_authenticated_promotion_authority import (
    MAX_RECEIPT_TTL_SECONDS,
)
from .model_autoresearch_production_authority_use import (
    trusted_campaign_authority_time,
)
from .model_runtime_binding_verified_admission import verified_runtime_binding_receipt


def pure_recheck_production_time(
    inputs: Mapping[str, Any],
    evidence_values: tuple[Any, Any, Any, Any, Any],
    runtime_payload: Mapping[str, Any],
) -> int:
    now = trusted_campaign_authority_time(inputs["authority_use"])
    authority = inputs["authenticated_promotion"].authority.receipt
    _require_authority_time(authority, now)
    _benchmark, _promotion, benchmark_signature, promotion_signature = (
        evidence_values[1],
        evidence_values[2],
        evidence_values[3],
        evidence_values[4],
    )
    _require_signed_evidence_time(benchmark_signature, now)
    _require_signed_evidence_time(promotion_signature, now)
    receipt = verified_runtime_binding_receipt(runtime_payload)
    if receipt is None:
        raise ValueError("single_model_production_runtime_time_receipt_invalid")
    if now < receipt.verified_at:
        raise ValueError("single_model_production_runtime_verified_in_future")
    if now > receipt.valid_until:
        raise ValueError("single_model_production_runtime_evidence_expired")
    return now


def _require_authority_time(receipt: Any, now: int) -> None:
    valid_epochs = (
        type(receipt.issued_at) is int
        and receipt.issued_at >= 0
        and type(receipt.expires_at) is int
        and receipt.expires_at >= 0
    )
    if not valid_epochs or receipt.expires_at <= receipt.issued_at:
        raise ValueError("single_model_production_authority_time_invalid")
    if receipt.expires_at - receipt.issued_at > MAX_RECEIPT_TTL_SECONDS:
        raise ValueError("single_model_production_authority_ttl_exceeded")
    if now < receipt.issued_at:
        raise ValueError("single_model_production_authority_issued_in_future")
    if now > receipt.expires_at:
        raise ValueError("single_model_production_authority_expired")


def _require_signed_evidence_time(receipt: Any, now: int) -> None:
    if now < receipt.issued_at:
        raise ValueError("single_model_production_signed_evidence_issued_in_future")
    if now > receipt.expires_at:
        raise ValueError("single_model_production_signed_evidence_expired")


__all__ = ["pure_recheck_production_time"]
