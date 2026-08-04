"""Publish one signer-attested verified-outcome evidence envelope."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Protocol

from modules.communication.moltbot_bridge.src.foundup_memex_verified_outcome_receipt_rehydration import (
    rehydrate_held_out_outcome_receipt,
    rehydrate_verified_slice_receipt,
    verified_outcome_evidence_bundle_digest,
)
from modules.communication.moltbot_bridge.src.foundup_memex_verified_outcome_runtime_store import (
    AuthorityRuntimeVerifiedOutcomeStore,
    build_outcome_evidence_envelope,
)
from modules.communication.moltbot_bridge.src.foundup_memex_verified_outcome_signing import (
    VERIFIED_OUTCOME_AUDIT_ATTESTATION_PREFIX,
    VERIFIED_OUTCOME_SIGNER_ROLE,
    VERIFIED_OUTCOME_SIGNING_OPERATION,
)
from modules.communication.moltbot_bridge.src.reddog_signer_audit_attestation import (
    canonical_signer_audit_attestation_input,
)
from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    IsolatedSignerClient,
    SigningRequest,
    public_key_fingerprint,
)
from modules.communication.moltbot_bridge.src.reddog_signed_receipt_chain import (
    build_receipt_payload_for_signing,
)
from modules.communication.moltbot_bridge.src.reddog_verified_pattern_memory_sink import (
    reddog_verified_pattern_memory_record_id,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import (
    PREFIX_RECEIPT,
    SignatureVerifier,
    canonical_signing_input,
)


class VerifiedOutcomeEvidencePublisher(Protocol):
    def publish(
        self,
        *,
        record_id: str,
        record: Mapping[str, Any],
        verification_receipt: Mapping[str, Any],
        held_out_receipt: Mapping[str, Any],
    ) -> str: ...


@dataclass(frozen=True)
class SignedVerifiedOutcomeEvidencePublisher:
    store: AuthorityRuntimeVerifiedOutcomeStore
    signer: IsolatedSignerClient
    signature_verifier: SignatureVerifier
    issuer_principal_id: str
    issuer_principal_provider: str
    reddog_id: str
    signer_public_key: str
    key_epoch: str
    authority_tier: str
    consensus_receipt_digest: str
    trusted_now_epoch: Callable[[], int]

    def publish(
        self,
        *,
        record_id: str,
        record: Mapping[str, Any],
        verification_receipt: Mapping[str, Any],
        held_out_receipt: Mapping[str, Any],
    ) -> str:
        _validate_dependencies(self)
        if reddog_verified_pattern_memory_record_id(record) != record_id:
            raise ValueError("verified_outcome_publish_record_id_mismatch")
        verifier, held_out, evidence_digest = _rehydrate_evidence(
            record, verification_receipt, held_out_receipt
        )
        now_epoch = self.trusted_now_epoch()
        if type(now_epoch) is not int:
            raise ValueError("verified_outcome_publish_clock_invalid")
        payload, signing_input = _signing_payload(
            publisher=self,
            record_id=record_id,
            work_order_id=str(record.get("work_order_id") or ""),
            evidence_digest=evidence_digest,
            now_epoch=now_epoch,
        )
        response = self.signer.sign(
            _signing_request(self, signing_input, payload["receipt_id"])
        )
        _validate_signer_response(self, response, signing_input)
        signed_receipt = {**payload, "signature": response.signature}
        envelope = build_outcome_evidence_envelope(
            record_id=record_id,
            record=record,
            verification_receipt=verifier,
            held_out_receipt=held_out,
            signed_receipt=signed_receipt,
            issuer_principal_id=self.issuer_principal_id,
            issuer_principal_provider=self.issuer_principal_provider,
            reddog_id=self.reddog_id,
            signer_key_fingerprint=response.key_fingerprint,
            key_epoch=self.key_epoch,
        )
        return self.store.publish(envelope)


def _rehydrate_evidence(
    record: Mapping[str, Any],
    verification_receipt: Mapping[str, Any],
    held_out_receipt: Mapping[str, Any],
) -> tuple[Mapping[str, Any], Mapping[str, Any], str]:
    verifier_receipt = rehydrate_verified_slice_receipt(verification_receipt)
    verifier = verifier_receipt.to_dict()
    held_out = rehydrate_held_out_outcome_receipt(
        held_out_receipt,
        verifier=verifier_receipt,
    ).to_dict()
    digest = verified_outcome_evidence_bundle_digest(
        record=record,
        verifier_receipt=verifier,
        held_out_receipt=held_out,
    )
    return verifier, held_out, digest


def _signing_request(
    publisher: SignedVerifiedOutcomeEvidencePublisher,
    signing_input: str,
    receipt_id: str,
) -> SigningRequest:
    return SigningRequest(
        signing_input=signing_input,
        payload_digest=_digest({"signing_input": signing_input}),
        signer_role=VERIFIED_OUTCOME_SIGNER_ROLE,
        signer_public_key=publisher.signer_public_key,
        requester_principal_id=publisher.issuer_principal_id,
        nonce=receipt_id,
        key_epoch=publisher.key_epoch,
        requested_operation=VERIFIED_OUTCOME_SIGNING_OPERATION,
        authority_tier=publisher.authority_tier,
        consensus_receipt_digest=publisher.consensus_receipt_digest,
    )


def _signing_payload(
    *,
    publisher: SignedVerifiedOutcomeEvidencePublisher,
    record_id: str,
    work_order_id: str,
    evidence_digest: str,
    now_epoch: int,
) -> tuple[dict[str, Any], str]:
    receipt_id = (
        "verified-outcome-"
        + _digest(
            {
                "record_id": record_id,
                "evidence_digest": evidence_digest,
                "reddog_id": publisher.reddog_id,
            }
        )[7:31]
    )
    payload = build_receipt_payload_for_signing(
        receipt_id=receipt_id,
        work_order_id=work_order_id,
        reddog_id=publisher.reddog_id,
        prev_receipt_hash=None,
        covered_action_digest=evidence_digest,
        reward_account=None,
        issued_at=now_epoch,
    )
    return payload, canonical_signing_input(payload, PREFIX_RECEIPT)


def _validate_dependencies(publisher: SignedVerifiedOutcomeEvidencePublisher) -> None:
    if (
        not callable(getattr(publisher.signer, "sign", None))
        or not callable(getattr(publisher.signature_verifier, "verify", None))
        or not callable(publisher.trusted_now_epoch)
        or any(
            not str(value or "").strip()
            for value in (
                publisher.issuer_principal_id,
                publisher.issuer_principal_provider,
                publisher.reddog_id,
                publisher.signer_public_key,
                publisher.key_epoch,
                publisher.authority_tier,
                publisher.consensus_receipt_digest,
            )
        )
    ):
        raise ValueError("verified_outcome_publish_dependency_invalid")


def _validate_signer_response(
    publisher: SignedVerifiedOutcomeEvidencePublisher,
    response: Any,
    signing_input: str,
) -> None:
    audit_input = canonical_signer_audit_attestation_input(
        signing_input=signing_input,
        signature=str(response.signature),
        audit_mac=str(response.audit_mac),
        signer_public_key=publisher.signer_public_key,
        key_epoch=publisher.key_epoch,
        requester_principal_id=publisher.issuer_principal_id,
        domain_prefix=VERIFIED_OUTCOME_AUDIT_ATTESTATION_PREFIX,
    )
    valid = bool(
        response.accepted
        and response.signer_public_key == publisher.signer_public_key
        and response.key_fingerprint
        == public_key_fingerprint(publisher.signer_public_key)
        and response.key_epoch == publisher.key_epoch
        and response.boundary_attested
        and response.requester_identity_attested
        and response.signer_loads_no_untrusted_code
        and response.no_secret_material_returned
        and response.signature
        and response.audit_mac
        and response.audit_attestation_signature
        and publisher.signature_verifier.verify(
            publisher.signer_public_key, signing_input, response.signature
        )
        and publisher.signature_verifier.verify(
            publisher.signer_public_key,
            audit_input,
            response.audit_attestation_signature,
        )
    )
    if not valid:
        raise ValueError("verified_outcome_publish_signer_rejected")


def _digest(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


__all__ = [
    "SignedVerifiedOutcomeEvidencePublisher",
    "VerifiedOutcomeEvidencePublisher",
]
