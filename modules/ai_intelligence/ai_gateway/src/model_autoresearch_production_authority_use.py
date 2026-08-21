"""Use-time authentication for campaign promotion authority receipts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, Protocol

from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import (
    SignatureVerifier,
    constant_time_compare,
)

from .model_autoresearch_authenticated_promotion_authority import (
    CampaignPromotionAuthorityKeyResolver,
    MAX_RECEIPT_TTL_SECONDS,
    SIGNER_ROLE,
    VerifiedCampaignPromotionAuthority,
    _campaign_authority_publication_binding,
)
from .model_autoresearch_configured_gateway_evidence import (
    DurableExactPublicationStore,
    digest_payload,
)


class DurableCampaignAuthorityReceiptStore(Protocol):
    @property
    def durable(self) -> bool: ...

    @property
    def store_id(self) -> str: ...

    def load(self, receipt_id: str) -> Mapping[str, Any]: ...


@dataclass(frozen=True)
class CampaignPromotionAuthorityUseContext:
    """External trust, durable state, and trusted time for production use."""

    key_resolver: CampaignPromotionAuthorityKeyResolver
    signature_verifier: SignatureVerifier
    receipt_store: DurableCampaignAuthorityReceiptStore
    publication_store: DurableExactPublicationStore
    trusted_now_epoch: Callable[[], int]
    revoked_key_epochs: tuple[str, ...] = ()


def trusted_campaign_authority_time(
    context: CampaignPromotionAuthorityUseContext,
) -> int:
    if type(context) is not CampaignPromotionAuthorityUseContext:
        raise ValueError("campaign_promotion_authority_use_context_required")
    try:
        now = context.trusted_now_epoch()
    except Exception:
        raise ValueError("campaign_promotion_authority_trusted_time_failed") from None
    if type(now) is not int or now < 0:
        raise ValueError("campaign_promotion_authority_trusted_time_invalid")
    return now


def validate_campaign_promotion_authority_use(
    authority: VerifiedCampaignPromotionAuthority,
    context: CampaignPromotionAuthorityUseContext,
    *,
    now: int,
) -> None:
    reasons = _authority_trust_reasons(authority, context, now=now)
    reasons.extend(_authority_store_reasons(authority, context))
    if reasons:
        raise ValueError(
            "campaign_promotion_authority_use_rejected:"
            + ",".join(sorted(set(reasons)))
        )
    _require_applied_authority_publication(authority, context)


def _authority_trust_reasons(
    authority: VerifiedCampaignPromotionAuthority,
    context: CampaignPromotionAuthorityUseContext,
    *,
    now: int,
) -> list[str]:
    receipt = authority.receipt
    revoked = _validated_revocations(context.revoked_key_epochs)
    reasons: list[str] = []
    if receipt.signer_role != SIGNER_ROLE:
        reasons.append("signer_role_mismatch")
    if receipt.key_epoch in revoked:
        reasons.append("key_epoch_revoked")
    epochs_valid = (
        type(receipt.issued_at) is int
        and receipt.issued_at >= 0
        and type(receipt.expires_at) is int
        and receipt.expires_at >= 0
    )
    if not epochs_valid:
        reasons.append("epoch_invalid")
    else:
        if receipt.expires_at <= receipt.issued_at:
            reasons.append("ttl_invalid")
        elif receipt.expires_at - receipt.issued_at > MAX_RECEIPT_TTL_SECONDS:
            reasons.append("ttl_exceeded")
        if now < receipt.issued_at:
            reasons.append("issued_in_future")
        if now > receipt.expires_at:
            reasons.append("authority_expired")
    trusted = _resolve_key(context, receipt.signer_key_fingerprint, receipt.key_epoch)
    if not trusted or not constant_time_compare(trusted, receipt.signer_public_key):
        reasons.append("signer_key_untrusted")
    if not _signature_valid(authority, context):
        reasons.append("signature_invalid")
    return reasons


def _authority_store_reasons(
    authority: VerifiedCampaignPromotionAuthority,
    context: CampaignPromotionAuthorityUseContext,
) -> list[str]:
    receipt_id = authority.receipt.receipt_id
    first = str(getattr(context.receipt_store, "store_id", "") or "")
    second = str(getattr(context.publication_store, "store_id", "") or "")
    if (
        getattr(context.receipt_store, "durable", None) is not True
        or getattr(context.publication_store, "durable", None) is not True
        or not first
        or not second
        or not constant_time_compare(first, second)
    ):
        return ["durable_store_identity_invalid"]
    try:
        stored = context.receipt_store.load(receipt_id)
    except Exception:
        return ["durable_receipt_mismatch"]
    if digest_payload(stored) != digest_payload(authority.receipt.to_dict()):
        return ["durable_receipt_mismatch"]
    return []


def _require_applied_authority_publication(
    authority: VerifiedCampaignPromotionAuthority,
    context: CampaignPromotionAuthorityUseContext,
) -> None:
    operation = getattr(context.publication_store, "publication_status", None)
    if not callable(operation):
        raise ValueError("campaign_promotion_authority_publication_not_applied")
    binding = _campaign_authority_publication_binding(
        authority.request, authority.receipt
    )
    try:
        status = operation(
            "campaign-promotion-signature:" + authority.receipt.nonce, binding
        )
    except Exception:
        status = None
    if status != "APPLIED":
        raise ValueError("campaign_promotion_authority_publication_not_applied")


def _validated_revocations(values: tuple[str, ...]) -> set[str]:
    revoked = tuple(str(value).strip() for value in values)
    if any(not value for value in revoked) or len(revoked) != len(set(revoked)):
        raise ValueError("campaign_promotion_authority_revocation_policy_invalid")
    return set(revoked)


def _resolve_key(
    context: CampaignPromotionAuthorityUseContext,
    fingerprint: str,
    epoch: str,
) -> str | None:
    try:
        value = context.key_resolver.resolve(SIGNER_ROLE, fingerprint, epoch)
    except Exception:
        return None
    return str(value) if value else None


def _signature_valid(
    authority: VerifiedCampaignPromotionAuthority,
    context: CampaignPromotionAuthorityUseContext,
) -> bool:
    receipt = authority.receipt
    try:
        return context.signature_verifier.verify(
            receipt.signer_public_key, receipt.signing_input(), receipt.signature
        ) is True
    except Exception:
        return False


__all__ = [
    "CampaignPromotionAuthorityUseContext",
    "DurableCampaignAuthorityReceiptStore",
    "trusted_campaign_authority_time",
    "validate_campaign_promotion_authority_use",
]
