"""Authenticated campaign authority for AutoResearch promotion-gate supply.

The campaign and topology proposer are evidence, never signing authority.  An
external promotion authority signs the exact campaign/proposer/policy request;
this module verifies and durably stores that receipt before it can authorize
the existing promotion gate.  It owns no private key and performs no provider
call, model selection, production binding, or repository mutation.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Protocol, Sequence

from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import (
    SignatureVerifier,
    canonical_signing_input,
    constant_time_compare,
)

from .model_autoresearch_campaign_execution import (
    ModelAutoResearchCampaignExecutionReceipt,
    rehydrate_model_autoresearch_campaign_execution_receipt,
)
from .model_autoresearch_campaign_promotion_gate_supply import (
    ModelAutoResearchCampaignPromotionGateSupplyReason,
    ModelAutoResearchCampaignPromotionGateSupplyResult,
    _runtime_output_path,
    run_reddog_model_autoresearch_campaign_promotion_gate_supply,
)
from .model_autoresearch_configured_gateway_evidence import (
    ConfiguredGatewayReceiptStore,
    DurableExactPublicationStore,
    digest_payload,
)
from .model_promotion_gate import (
    ModelPromotionPolicy,
    rehydrate_model_promotion_policy,
)
from .model_topology_proposer_authenticated_provenance import (
    VerifiedTopologyProposerProvenance,
    complete_verified_topology_proposer_provenance_use,
    release_verified_topology_proposer_provenance_use,
    reserve_verified_topology_proposer_provenance_use,
    validate_verified_topology_proposer_provenance,
)


REQUEST_SCHEMA_VERSION = "model_autoresearch_promotion_authority_request.v1"
RECEIPT_SCHEMA_VERSION = "model_autoresearch_promotion_authority_receipt.v1"
SIGNING_PREFIX = "reddog-autoresearch-promotion-authority.v1"
SIGNER_ROLE = "promotion_authority"
MAX_RECEIPT_TTL_SECONDS = 900
MAX_VERIFICATION_LEEWAY_SECONDS = 60


class CampaignPromotionAuthorityKeyResolver(Protocol):
    def resolve(
        self, signer_role: str, signer_key_fingerprint: str, key_epoch: str
    ) -> str | None: ...


@dataclass(frozen=True)
class CampaignPromotionAuthorityRequest:
    request_id: str
    source_execution_receipt_id: str
    source_execution_digest: str
    proposer_provenance_receipt_id: str
    proposer_provenance_digest: str
    promotion_policy_digest: str
    candidate_ids: tuple[str, ...]
    schema_version: str = REQUEST_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["candidate_ids"] = list(self.candidate_ids)
        return value


@dataclass(frozen=True)
class SignedCampaignPromotionAuthorityReceipt:
    receipt_id: str
    request_id: str
    request_digest: str
    signer_role: str
    signer_public_key: str
    signer_key_fingerprint: str
    key_epoch: str
    issued_at: int
    expires_at: int
    nonce: str
    signature: str
    schema_version: str = RECEIPT_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def signing_input(self) -> str:
        return canonical_signing_input(
            {key: value for key, value in self.to_dict().items() if key != "receipt_id"},
            SIGNING_PREFIX,
        )


@dataclass(frozen=True)
class VerifiedCampaignPromotionAuthority:
    request: CampaignPromotionAuthorityRequest
    receipt: SignedCampaignPromotionAuthorityReceipt
    durable_store_receipt_id: str
    authenticated: bool = True
    nonce_consumed: bool = True


@dataclass(frozen=True)
class AuthenticatedCampaignPromotionSupplyResult:
    authority: VerifiedCampaignPromotionAuthority
    supply: ModelAutoResearchCampaignPromotionGateSupplyResult


def build_campaign_promotion_authority_request(
    *,
    campaign_execution_receipt: Mapping[str, Any] | ModelAutoResearchCampaignExecutionReceipt,
    promotion_policies: Sequence[Mapping[str, Any] | ModelPromotionPolicy],
    proposer_provenance: VerifiedTopologyProposerProvenance,
    now: int,
) -> CampaignPromotionAuthorityRequest:
    execution = _execution(campaign_execution_receipt)
    policies = _policies(promotion_policies)
    consumed_proposer = validate_verified_topology_proposer_provenance(
        proposer_provenance, now=int(now)
    )
    if consumed_proposer is None:
        raise ValueError("verified_topology_proposer_provenance_required")
    proposer_receipt, admission = consumed_proposer
    executed = tuple(sorted(execution.executed_candidate_ids))
    policy_candidates = tuple(sorted(policy.candidate_id for policy in policies))
    if policy_candidates != executed:
        raise ValueError("campaign_promotion_authority_candidate_mismatch")
    admitted = tuple(sorted(item.candidate_id for item in admission.accepted_candidates))
    if admitted != executed:
        raise ValueError("campaign_promotion_authority_admission_mismatch")
    policy_records = [policy.to_dict() for policy in policies]
    body = {
        "schema_version": REQUEST_SCHEMA_VERSION,
        "source_execution_receipt_id": execution.receipt_id,
        "source_execution_digest": digest_payload(execution.to_dict()),
        "proposer_provenance_receipt_id": proposer_receipt.receipt_id,
        "proposer_provenance_digest": digest_payload(
            proposer_receipt.to_dict()
        ),
        "promotion_policy_digest": digest_payload(policy_records),
        "candidate_ids": list(executed),
    }
    return CampaignPromotionAuthorityRequest(
        request_id="model_autoresearch_promotion_authority_request:" + _sha256(body),
        source_execution_receipt_id=execution.receipt_id,
        source_execution_digest=body["source_execution_digest"],
        proposer_provenance_receipt_id=body["proposer_provenance_receipt_id"],
        proposer_provenance_digest=body["proposer_provenance_digest"],
        promotion_policy_digest=body["promotion_policy_digest"],
        candidate_ids=executed,
    )


def build_signed_campaign_promotion_authority_receipt(
    *,
    request: CampaignPromotionAuthorityRequest,
    signer_public_key: str,
    signer_key_fingerprint: str,
    key_epoch: str,
    issued_at: int,
    expires_at: int,
    nonce: str,
    signature: str,
) -> SignedCampaignPromotionAuthorityReceipt:
    if type(request) is not CampaignPromotionAuthorityRequest:
        raise ValueError("campaign_promotion_authority_request_invalid")
    body = {
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "request_id": request.request_id,
        "request_digest": digest_payload(request.to_dict()),
        "signer_role": SIGNER_ROLE,
        "signer_public_key": _required(signer_public_key),
        "signer_key_fingerprint": _required(signer_key_fingerprint),
        "key_epoch": _required(key_epoch),
        "issued_at": _epoch(issued_at),
        "expires_at": _epoch(expires_at),
        "nonce": _required(nonce),
        "signature": _required(signature),
    }
    if body["expires_at"] <= body["issued_at"]:
        raise ValueError("campaign_promotion_authority_ttl_invalid")
    if body["expires_at"] - body["issued_at"] > MAX_RECEIPT_TTL_SECONDS:
        raise ValueError("campaign_promotion_authority_ttl_invalid")
    return SignedCampaignPromotionAuthorityReceipt(
        receipt_id="model_autoresearch_promotion_authority:" + _sha256(body),
        **body,
    )


def rehydrate_signed_campaign_promotion_authority_receipt(
    payload: Mapping[str, Any],
) -> SignedCampaignPromotionAuthorityReceipt:
    if not isinstance(payload, Mapping) or payload.get("schema_version") != RECEIPT_SCHEMA_VERSION:
        raise ValueError("campaign_promotion_authority_schema_invalid")
    receipt = SignedCampaignPromotionAuthorityReceipt(
        receipt_id=_required(payload.get("receipt_id")),
        request_id=_required(payload.get("request_id")),
        request_digest=_required(payload.get("request_digest")),
        signer_role=_required(payload.get("signer_role")),
        signer_public_key=_required(payload.get("signer_public_key")),
        signer_key_fingerprint=_required(payload.get("signer_key_fingerprint")),
        key_epoch=_required(payload.get("key_epoch")),
        issued_at=_epoch(payload.get("issued_at")),
        expires_at=_epoch(payload.get("expires_at")),
        nonce=_required(payload.get("nonce")),
        signature=_required(payload.get("signature")),
    )
    body = {key: value for key, value in receipt.to_dict().items() if key != "receipt_id"}
    expected = "model_autoresearch_promotion_authority:" + _sha256(body)
    if not hmac.compare_digest(receipt.receipt_id, expected):
        raise ValueError("campaign_promotion_authority_receipt_id_invalid")
    if receipt.expires_at <= receipt.issued_at:
        raise ValueError("campaign_promotion_authority_ttl_invalid")
    if receipt.expires_at - receipt.issued_at > MAX_RECEIPT_TTL_SECONDS:
        raise ValueError("campaign_promotion_authority_ttl_invalid")
    return receipt


def verify_and_store_campaign_promotion_authority(
    *,
    request: CampaignPromotionAuthorityRequest,
    signed_receipt: SignedCampaignPromotionAuthorityReceipt | Mapping[str, Any],
    key_resolver: CampaignPromotionAuthorityKeyResolver,
    signature_verifier: SignatureVerifier,
    publication_store: DurableExactPublicationStore,
    receipt_store: ConfiguredGatewayReceiptStore,
    now: int,
    revoked_key_epochs: Sequence[str] = (),
    leeway_seconds: int = 60,
) -> VerifiedCampaignPromotionAuthority:
    if type(request) is not CampaignPromotionAuthorityRequest:
        raise ValueError("campaign_promotion_authority_request_invalid")
    if not 0 <= int(leeway_seconds) <= MAX_VERIFICATION_LEEWAY_SECONDS:
        raise ValueError("campaign_promotion_authority_leeway_invalid")
    receipt = rehydrate_signed_campaign_promotion_authority_receipt(
        signed_receipt.to_dict()
        if isinstance(signed_receipt, SignedCampaignPromotionAuthorityReceipt)
        else signed_receipt
    )
    reasons: list[str] = []
    if receipt.request_id != request.request_id or not hmac.compare_digest(
        receipt.request_digest, digest_payload(request.to_dict())
    ):
        reasons.append("authority_request_mismatch")
    if receipt.signer_role != SIGNER_ROLE:
        reasons.append("signer_role_mismatch")
    if receipt.key_epoch in {str(value) for value in revoked_key_epochs}:
        reasons.append("key_epoch_revoked")
    if receipt.expires_at <= receipt.issued_at:
        reasons.append("ttl_invalid")
    elif receipt.expires_at - receipt.issued_at > MAX_RECEIPT_TTL_SECONDS:
        reasons.append("ttl_exceeded")
    try:
        trusted = key_resolver.resolve(
            SIGNER_ROLE, receipt.signer_key_fingerprint, receipt.key_epoch
        )
    except Exception:
        trusted = None
    if not trusted or not constant_time_compare(str(trusted), receipt.signer_public_key):
        reasons.append("signer_key_untrusted")
    if int(now) + int(leeway_seconds) < receipt.issued_at:
        reasons.append("issued_in_future")
    if int(now) > receipt.expires_at + int(leeway_seconds):
        reasons.append("authority_expired")
    try:
        valid_signature = signature_verifier.verify(
            receipt.signer_public_key, receipt.signing_input(), receipt.signature
        ) is True
    except Exception:
        valid_signature = False
    if not valid_signature:
        reasons.append("signature_invalid")
    if reasons:
        raise ValueError("campaign_promotion_authority_rejected:" + ",".join(sorted(set(reasons))))
    _matching_durable_store_id(publication_store, receipt_store)
    publication_binding = _campaign_authority_publication_binding(request, receipt)
    _advance_exact_publication(
        publication_store,
        nonce="campaign-promotion-signature:" + receipt.nonce,
        binding_digest=publication_binding,
        target_status="RESERVED",
        error="campaign_promotion_authority_nonce_replay",
    )
    try:
        stored = receipt_store.append(receipt)
    except Exception:
        raise ValueError("campaign_promotion_authority_store_failed") from None
    if stored != receipt.receipt_id:
        raise ValueError("campaign_promotion_authority_store_mismatch")
    _advance_exact_publication(
        publication_store,
        nonce="campaign-promotion-signature:" + receipt.nonce,
        binding_digest=publication_binding,
        target_status="AUTHORIZED",
        error="campaign_promotion_authority_publication_failed",
    )
    _advance_exact_publication(
        publication_store,
        nonce="campaign-promotion-signature:" + receipt.nonce,
        binding_digest=publication_binding,
        target_status="APPLIED",
        error="campaign_promotion_authority_publication_failed",
    )
    return VerifiedCampaignPromotionAuthority(request, receipt, stored)


def authorize_and_supply_campaign_promotion_gates(
    *,
    repo_root: Any,
    campaign_execution_receipt: Mapping[str, Any] | ModelAutoResearchCampaignExecutionReceipt,
    promotion_policies: Sequence[Mapping[str, Any] | ModelPromotionPolicy],
    proposer_provenance: VerifiedTopologyProposerProvenance,
    signed_receipt_provider: Callable[
        [CampaignPromotionAuthorityRequest],
        SignedCampaignPromotionAuthorityReceipt | Mapping[str, Any],
    ],
    key_resolver: CampaignPromotionAuthorityKeyResolver,
    signature_verifier: SignatureVerifier,
    publication_store: DurableExactPublicationStore,
    receipt_store: ConfiguredGatewayReceiptStore,
    now: int,
    output_path: Any,
    revoked_key_epochs: Sequence[str] = (),
) -> AuthenticatedCampaignPromotionSupplyResult:
    """Authenticate the exact campaign authority, persist it, then run gates."""
    execution = _execution(campaign_execution_receipt)
    policies = _policies(promotion_policies)
    resolved_output = _preflight_gate_output_path(
        repo_root=repo_root,
        output_path=output_path,
    )
    _assert_single_model_candidates(execution)
    request = build_campaign_promotion_authority_request(
        campaign_execution_receipt=execution,
        promotion_policies=policies,
        proposer_provenance=proposer_provenance,
        now=now,
    )
    verified = verify_and_store_campaign_promotion_authority(
        request=request,
        signed_receipt=signed_receipt_provider(request),
        key_resolver=key_resolver,
        signature_verifier=signature_verifier,
        publication_store=publication_store,
        receipt_store=receipt_store,
        now=now,
        revoked_key_epochs=revoked_key_epochs,
    )
    use_binding_digest = digest_payload(
        {
            "kind": "topology_proposer_campaign_use.v1",
            "request_id": verified.request.request_id,
            "request_digest": digest_payload(verified.request.to_dict()),
            "signed_authority_receipt_id": verified.receipt.receipt_id,
        }
    )
    reserved = reserve_verified_topology_proposer_provenance_use(
        proposer_provenance,
        publication_store=publication_store,
        use_binding_digest=use_binding_digest,
        now=now,
    )
    if reserved is None:
        raise ValueError("verified_topology_proposer_provenance_reservation_failed")
    try:
        supply = run_reddog_model_autoresearch_campaign_promotion_gate_supply(
            repo_root=repo_root,
            campaign_execution_receipt=execution,
            promotion_policies=policies,
            output_path=resolved_output,
            # The request is the exact deterministic authorization subject; the
            # distinct signed receipt authenticates that subject.  Post-gate model
            # signed evidence remains a separate production-binding requirement.
            promotion_authority_receipt_id=verified.request.request_id,
            signed_promotion_receipt_id=verified.receipt.receipt_id,
        )
    except Exception:
        release_verified_topology_proposer_provenance_use(
            proposer_provenance,
            use_binding_digest=use_binding_digest,
        )
        raise
    if supply.accepted:
        try:
            consumed = complete_verified_topology_proposer_provenance_use(
                proposer_provenance,
                publication_store=publication_store,
                use_binding_digest=use_binding_digest,
                now=now,
            )
        except Exception:
            release_verified_topology_proposer_provenance_use(
                proposer_provenance,
                use_binding_digest=use_binding_digest,
            )
            raise
        if consumed is None:
            raise ValueError("verified_topology_proposer_provenance_consumption_failed")
    else:
        release_verified_topology_proposer_provenance_use(
            proposer_provenance,
            use_binding_digest=use_binding_digest,
        )
    return AuthenticatedCampaignPromotionSupplyResult(verified, supply)


def _execution(value: Any) -> ModelAutoResearchCampaignExecutionReceipt:
    if isinstance(value, ModelAutoResearchCampaignExecutionReceipt):
        return value
    if isinstance(value, Mapping):
        return rehydrate_model_autoresearch_campaign_execution_receipt(value)
    raise ValueError("campaign_promotion_authority_execution_invalid")


def _policies(values: Sequence[Any]) -> tuple[ModelPromotionPolicy, ...]:
    policies = tuple(
        value.normalized() if isinstance(value, ModelPromotionPolicy)
        else rehydrate_model_promotion_policy(value)
        for value in values
    )
    if not policies or len({item.candidate_id for item in policies}) != len(policies):
        raise ValueError("campaign_promotion_authority_policies_invalid")
    return tuple(sorted(policies, key=lambda item: item.candidate_id))


def _preflight_gate_output_path(*, repo_root: Any, output_path: Any) -> Path:
    output, reasons = _runtime_output_path(
        output_path,
        Path(repo_root).resolve(),
        ModelAutoResearchCampaignPromotionGateSupplyReason.OUTPUT_PATH_INVALID,
    )
    if reasons or output is None:
        raise ValueError("campaign_promotion_authority_gate_preflight_failed")
    return output


def _assert_single_model_candidates(
    execution: ModelAutoResearchCampaignExecutionReceipt,
) -> None:
    for candidate in execution.benchmark_run_receipt.candidates:
        assignments = candidate.role_assignments
        if (
            len(assignments) != 1
            or assignments[0].role != "principal"
            or candidate.candidate_id != assignments[0].model_id
        ):
            raise ValueError("campaign_promotion_authority_panel_shadow_only")


def _campaign_authority_publication_binding(
    request: CampaignPromotionAuthorityRequest,
    receipt: SignedCampaignPromotionAuthorityReceipt,
) -> str:
    return digest_payload(
        {
            "kind": "campaign_promotion_authority_publication.v1",
            "request_id": request.request_id,
            "request_digest": digest_payload(request.to_dict()),
            "receipt_id": receipt.receipt_id,
            "receipt_digest": digest_payload(receipt.to_dict()),
        }
    )


def _advance_exact_publication(
    store: DurableExactPublicationStore,
    *,
    nonce: str,
    binding_digest: str,
    target_status: str,
    error: str,
) -> str:
    if getattr(store, "durable", None) is not True:
        raise ValueError("durable_exact_publication_store_required")
    operation = getattr(store, "advance_publication", None)
    if not callable(operation):
        raise ValueError("durable_exact_publication_store_required")
    try:
        status = str(operation(nonce, binding_digest, target_status) or "")
    except Exception:
        raise ValueError(error) from None
    allowed = {
        "RESERVED": {"RESERVED", "AUTHORIZED", "APPLIED"},
        "AUTHORIZED": {"AUTHORIZED", "APPLIED"},
        "APPLIED": {"APPLIED"},
    }
    if status not in allowed[target_status]:
        raise ValueError(error)
    return status


def _matching_durable_store_id(
    publication_store: DurableExactPublicationStore,
    receipt_store: ConfiguredGatewayReceiptStore,
) -> str:
    if getattr(publication_store, "durable", None) is not True:
        raise ValueError("durable_exact_publication_store_required")
    publication_store_id = str(getattr(publication_store, "store_id", "") or "")
    if not publication_store_id:
        raise ValueError("durable_exact_publication_store_required")
    if getattr(receipt_store, "durable", None) is not True:
        raise ValueError("campaign_promotion_authority_durable_receipt_store_required")
    receipt_store_id = str(getattr(receipt_store, "store_id", "") or "")
    if not receipt_store_id:
        raise ValueError("campaign_promotion_authority_durable_receipt_store_required")
    if not hmac.compare_digest(publication_store_id, receipt_store_id):
        raise ValueError("campaign_promotion_authority_store_identity_mismatch")
    return publication_store_id


def _sha256(value: Mapping[str, Any]) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _required(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError("campaign_promotion_authority_field_invalid")
    return text


def _epoch(value: Any) -> int:
    if type(value) is not int or value < 0:
        raise ValueError("campaign_promotion_authority_epoch_invalid")
    return value


__all__ = [
    "AuthenticatedCampaignPromotionSupplyResult",
    "CampaignPromotionAuthorityKeyResolver",
    "CampaignPromotionAuthorityRequest",
    "SignedCampaignPromotionAuthorityReceipt",
    "VerifiedCampaignPromotionAuthority",
    "authorize_and_supply_campaign_promotion_gates",
    "build_campaign_promotion_authority_request",
    "build_signed_campaign_promotion_authority_receipt",
    "rehydrate_signed_campaign_promotion_authority_receipt",
    "verify_and_store_campaign_promotion_authority",
]
