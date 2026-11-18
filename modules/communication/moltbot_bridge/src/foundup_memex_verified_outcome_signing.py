"""Signer-owned policy for verified FoundUp outcome receipts."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any, Mapping, Protocol

from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    SigningRequest,
    SigningResponse,
    public_key_fingerprint,
)
from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_authority import (
    validate_root_verified_outcome_descriptor_public,
)
from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_authority_wire_codec import (
    decode_message,
    digest_mapping,
    encode_message,
)
from modules.communication.moltbot_bridge.src.reddog_signer_audit_attestation import (
    VERIFIED_OUTCOME_AUDIT_ATTESTATION_PREFIX,
    canonical_signer_audit_attestation_input,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import (
    PREFIX_RECEIPT,
    SignatureVerifier,
    canonical_signing_input,
)


VERIFIED_OUTCOME_SIGNING_OPERATION = "attest_verified_foundup_outcome"
VERIFIED_OUTCOME_SIGNER_ROLE = "verified_foundup_outcome_authority"
VERIFIED_OUTCOME_SIGNING_PREFIX = PREFIX_RECEIPT + "."
_RECEIPT_FIELDS = {
    "receipt_id",
    "work_order_id",
    "reddog_id",
    "prev_receipt_hash",
    "covered_action_digest",
    "reward_account",
    "issued_at",
}
VERIFIED_OUTCOME_RESPONSE_RECORD_SCHEMA = "foundup_verified_outcome_response_record.v1"
_RECORD_FIELDS = {
    "schema_version", "authority_descriptor", "binding", "request", "response",
    "response_digest", "record_digest",
}
_REQUEST_RECORD_FIELDS = {
    "signing_input", "payload_digest", "signer_role", "signer_public_key",
    "requester_principal_id", "nonce", "key_epoch", "requested_operation",
    "authority_tier", "consensus_receipt_digest",
}
_RESPONSE_RECORD_FLAGS = {
    "accepted", "boundary_attested", "requester_identity_attested",
    "signer_loads_no_untrusted_code", "no_secret_material_returned",
}
_RESPONSE_RECORD_TEXT = {
    "signature", "signer_public_key", "key_fingerprint", "key_epoch", "audit_mac",
    "audit_attestation_signature", "rejection_code",
}


@dataclass(frozen=True)
class VerifiedOutcomeSignerPolicy:
    issuer_principal_id: str
    reddog_id: str
    signer_public_key: str
    key_epoch: str
    authority_tier: str
    consensus_receipt_digest: str
    max_future_skew_seconds: int = 60


@dataclass(frozen=True)
class VerifiedOutcomeResponseBinding:
    """Public historical identifiers, never a root reservation capability."""

    descriptor_id: str
    owner_config_id: str
    authorization_id: str
    reservation_id: str


class VerifiedOutcomeSigningAuthority(Protocol):
    """Signer-side durable authority for one exact verified evidence bundle."""

    def reserve(
        self,
        *,
        receipt_id: str,
        work_order_id: str,
        evidence_digest: str,
        issued_at: int,
        signer_instance_signature: str,
    ) -> object | None: ...

    def reserve_proof_input(
        self, *, receipt_id: str, work_order_id: str,
        evidence_digest: str, issued_at: int,
    ) -> str: ...

    def commit(
        self, reservation: object, signature_digest: str,
        signer_instance_signature: str,
    ) -> None: ...

    def commit_proof_input(
        self, reservation: object, signature_digest: str
    ) -> str: ...

    def rollback(self, reservation: object) -> None: ...


def validate_verified_outcome_signing_request(
    request: SigningRequest,
    policy: VerifiedOutcomeSignerPolicy,
    *,
    now_epoch: int,
) -> Mapping[str, Any] | None:
    if (
        request.requested_operation != VERIFIED_OUTCOME_SIGNING_OPERATION
        or request.signer_role != VERIFIED_OUTCOME_SIGNER_ROLE
        or request.requester_principal_id != policy.issuer_principal_id
        or request.signer_public_key != policy.signer_public_key
        or request.key_epoch != policy.key_epoch
        or request.authority_tier != policy.authority_tier
        or request.consensus_receipt_digest != policy.consensus_receipt_digest
        or request.nonce == ""
        or request.payload_digest != _digest({"signing_input": request.signing_input})
        or policy.max_future_skew_seconds < 0
    ):
        return None
    payload = _parse_payload(request.signing_input)
    if payload is None or set(payload) != _RECEIPT_FIELDS:
        return None
    if (
        not str(payload.get("receipt_id") or "").startswith("verified-outcome-")
        or payload.get("receipt_id") != request.nonce
        or payload.get("reddog_id") != policy.reddog_id
        or payload.get("prev_receipt_hash") is not None
        or payload.get("reward_account") is not None
        or not str(payload.get("work_order_id") or "").strip()
        or not _sha256(payload.get("covered_action_digest"))
        or type(payload.get("issued_at")) is not int
        or payload["issued_at"] > now_epoch + policy.max_future_skew_seconds
        or payload["issued_at"] < now_epoch - policy.max_future_skew_seconds
        or canonical_signing_input(payload, PREFIX_RECEIPT) != request.signing_input
    ):
        return None
    return payload


def validate_verified_outcome_signing_response(
    response: Any,
    signing_input: str,
    *,
    signer_public_key: str,
    key_epoch: str,
    requester_principal_id: str,
    signature_verifier: SignatureVerifier,
) -> bool:
    """Verify the original response; this grants no replay or recovery authority."""
    audit_input = canonical_signer_audit_attestation_input(
        signing_input=signing_input,
        signature=str(response.signature),
        audit_mac=str(response.audit_mac),
        signer_public_key=signer_public_key,
        key_epoch=key_epoch,
        requester_principal_id=requester_principal_id,
        domain_prefix=VERIFIED_OUTCOME_AUDIT_ATTESTATION_PREFIX,
    )
    return bool(
        response.accepted is True
        and getattr(response, "rejection_code", "") == ""
        and response.signer_public_key == signer_public_key
        and response.key_fingerprint == public_key_fingerprint(signer_public_key)
        and response.key_epoch == key_epoch
        and response.boundary_attested is True
        and response.requester_identity_attested is True
        and response.signer_loads_no_untrusted_code is True
        and response.no_secret_material_returned is True
        and response.signature
        and response.audit_mac
        and response.audit_attestation_signature
        and signature_verifier.verify(
            signer_public_key, signing_input, response.signature
        ) is True
        and signature_verifier.verify(
            signer_public_key, audit_input, response.audit_attestation_signature
        ) is True
    )


def build_verified_outcome_response_record(
    request: SigningRequest,
    response: SigningResponse,
    *,
    descriptor: Mapping[str, Any],
    binding: VerifiedOutcomeResponseBinding,
    signature_verifier: SignatureVerifier,
) -> bytes:
    """Snapshot validated historical bytes; no persistence or authority is issued.

    V1 admits only the existing outcome request with no elevated-consensus proof.
    The complete record (including its newline) must fit the root codec's 64 KiB.
    """
    if (
        type(request) is not SigningRequest or type(response) is not SigningResponse
        or request.elevated_consensus_proof is not None
    ):
        raise ValueError("verified_outcome_response_record_input_invalid")
    data = decode_message(encode_message({
        "schema_version": VERIFIED_OUTCOME_RESPONSE_RECORD_SCHEMA,
        "authority_descriptor": descriptor,
        "binding": _response_binding_payload(binding),
        "request": request.to_dict(), "response": response.to_dict(),
    }))
    data["response_digest"] = digest_mapping(data["response"])
    data["record_digest"] = digest_mapping(data)
    raw = encode_message(data)
    parse_verified_outcome_response_record(
        raw, expected_binding=binding, expected_record_digest=data["record_digest"],
        signature_verifier=signature_verifier,
    )
    return raw


def parse_verified_outcome_response_record(
    raw: bytes,
    *,
    expected_binding: VerifiedOutcomeResponseBinding,
    expected_record_digest: str,
    signature_verifier: SignatureVerifier,
) -> tuple[SigningRequest, SigningResponse]:
    """Check immutable history against externally supplied context and digest.

    Expected values must come from an independent owner, not this record. This
    pure parser does not authenticate that owner, current read rights, revocation,
    root commitment or storage. Historical grant validation uses original issuance;
    successful parsing neither renews it nor authorizes signing/publication/replay.
    """
    try:
        data = decode_message(raw)
        binding = _response_binding_payload(expected_binding)
        if (
            set(data) != _RECORD_FIELDS
            or data["schema_version"] != VERIFIED_OUTCOME_RESPONSE_RECORD_SCHEMA
            or encode_message(data) != raw
            or data["binding"] != binding
            or type(expected_record_digest) is not str
            or not _sha256(expected_record_digest)
            or data["record_digest"] != expected_record_digest
            or digest_mapping({key: value for key, value in data.items()
                               if key != "record_digest"}) != expected_record_digest
            or data["response_digest"] != digest_mapping(data["response"])
        ):
            raise ValueError("verified_outcome_response_record_binding_invalid")
        request, response = _response_record_signed_pair(data)
        _validate_response_record_context(data, request, binding)
        if not validate_verified_outcome_signing_response(
            response, request.signing_input, signer_public_key=request.signer_public_key,
            key_epoch=request.key_epoch, requester_principal_id=request.requester_principal_id,
            signature_verifier=signature_verifier,
        ):
            raise ValueError("verified_outcome_response_record_signature_invalid")
        return request, response
    except (KeyError, TypeError, RecursionError) as exc:
        raise ValueError("verified_outcome_response_record_invalid") from exc


def _response_binding_payload(binding: VerifiedOutcomeResponseBinding) -> dict[str, str]:
    if type(binding) is not VerifiedOutcomeResponseBinding:
        raise ValueError("verified_outcome_response_record_binding_invalid")
    data = asdict(binding)
    if (
        any(type(value) is not str or not value for value in data.values())
        or any(not _sha256(data[name]) for name in (
            "descriptor_id", "owner_config_id", "reservation_id",
        ))
        or not binding.authorization_id.startswith("verified-outcome-authorization-")
    ):
        raise ValueError("verified_outcome_response_record_binding_invalid")
    return data


def _response_record_signed_pair(data: Mapping[str, Any]) -> tuple[SigningRequest, SigningResponse]:
    request, response = data["request"], data["response"]
    if (
        type(request) is not dict or set(request) != _REQUEST_RECORD_FIELDS
        or any(type(value) is not str for value in request.values())
        or type(response) is not dict
        or set(response) != _RESPONSE_RECORD_TEXT | _RESPONSE_RECORD_FLAGS
        or any(type(response[name]) is not str for name in _RESPONSE_RECORD_TEXT)
        or any(type(response[name]) is not bool for name in _RESPONSE_RECORD_FLAGS)
    ):
        raise ValueError("verified_outcome_response_record_shape_invalid")
    return SigningRequest(**request), SigningResponse(**response)


def _validate_response_record_context(
    data: Mapping[str, Any], request: SigningRequest, binding: Mapping[str, str],
) -> None:
    payload = _parse_payload(request.signing_input)
    if payload is None or type(payload.get("issued_at")) is not int:
        raise ValueError("verified_outcome_response_record_issuance_invalid")
    issued_at = payload["issued_at"]
    descriptor = validate_root_verified_outcome_descriptor_public(
        data["authority_descriptor"], now_epoch=issued_at,
    )
    _validate_response_record_anchor_shape(descriptor)
    policy = VerifiedOutcomeSignerPolicy(
        issuer_principal_id=descriptor["issuer_principal_id"],
        reddog_id=descriptor["reddog_id"], signer_public_key=descriptor["signer_public_key"],
        key_epoch=descriptor["signer_key_epoch"], authority_tier=descriptor["authority_tier"],
        consensus_receipt_digest=descriptor["consensus_receipt_digest"],
    )
    grant = next((item for item in descriptor["grants"]
                  if item["authorization_id"] == binding["authorization_id"]), None)
    if (
        descriptor["descriptor_id"] != binding["descriptor_id"]
        or validate_verified_outcome_signing_request(request, policy, now_epoch=issued_at) is None
        or grant is None
        or grant["receipt_id"] != payload["receipt_id"]
        or grant["work_order_id"] != payload["work_order_id"]
        or grant["evidence_digest"] != payload["covered_action_digest"]
    ):
        raise ValueError("verified_outcome_response_record_context_invalid")


def _validate_response_record_anchor_shape(descriptor: Mapping[str, Any]) -> None:
    # The root's mutable store binding checks these separately from public
    # descriptor verification. Here only historical identifier shape is checked.
    revision = descriptor["replay_anchor_revision"]
    if (
        type(descriptor["replay_anchor_sequence"]) is not int
        or descriptor["replay_anchor_sequence"] < 1
        or type(descriptor["replay_anchor_binding_digest"]) is not str
        or not _sha256(descriptor["replay_anchor_binding_digest"])
        or type(revision) is not str or len(revision) != 64
        or any(char not in "0123456789abcdef" for char in revision)
    ):
        raise ValueError("verified_outcome_response_record_anchor_shape_invalid")


def _parse_payload(signing_input: str) -> Mapping[str, Any] | None:
    if not isinstance(signing_input, str) or not signing_input.startswith(
        VERIFIED_OUTCOME_SIGNING_PREFIX
    ):
        return None
    try:
        payload = json.loads(signing_input[len(VERIFIED_OUTCOME_SIGNING_PREFIX) :])
    except (json.JSONDecodeError, TypeError):
        return None
    return payload if isinstance(payload, Mapping) else None


def _sha256(value: Any) -> bool:
    text = str(value or "")
    return (
        len(text) == 71
        and text.startswith("sha256:")
        and all(char in "0123456789abcdef" for char in text[7:])
    )


def _digest(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


__all__ = [
    "VERIFIED_OUTCOME_AUDIT_ATTESTATION_PREFIX",
    "VERIFIED_OUTCOME_SIGNER_ROLE",
    "VERIFIED_OUTCOME_SIGNING_OPERATION",
    "VERIFIED_OUTCOME_SIGNING_PREFIX",
    "VERIFIED_OUTCOME_RESPONSE_RECORD_SCHEMA",
    "VerifiedOutcomeResponseBinding",
    "VerifiedOutcomeSigningAuthority",
    "VerifiedOutcomeSignerPolicy",
    "validate_verified_outcome_signing_request",
    "validate_verified_outcome_signing_response",
    "build_verified_outcome_response_record",
    "parse_verified_outcome_response_record",
]
