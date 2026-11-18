"""Cryptographic boundary for resident RedDog control-loop receipts."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.reddog_ed25519_signature_verifier_backend import (
    Ed25519SignatureVerifier,
)
from modules.communication.moltbot_bridge.src.reddog_ed25519_signer_backend import (
    CONTROL_LOOP_SIGNING_OPERATION,
    CONTROL_LOOP_SIGNING_PREFIX,
    canonical_control_audit_attestation_input,
)
from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    IsolatedSignerClient,
    SigningRequest,
    public_key_fingerprint,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import (
    SignatureVerifier,
)


CONTROL_LOOP_AUTHENTICATED = "AUTHENTICATED"
CONTROL_LOOP_DISPLAY_ONLY = "DISPLAY_ONLY"


@dataclass(frozen=True)
class ControlLoopReceiptSigningContext:
    signer: IsolatedSignerClient
    signature_verifier: SignatureVerifier
    issuer_principal_id: str
    signer_public_key: str
    key_epoch: str
    authority_tier: str
    consensus_receipt_digest: str
    authority_profile_digest: str
    authority_profile_source_receipt_id: str


def control_receipt_authentication_fields(
    context: ControlLoopReceiptSigningContext | None,
) -> dict[str, str]:
    if context is None:
        return {
            "issuer_principal_id": "", "signer_public_key": "",
            "signer_key_fingerprint": "", "key_epoch": "",
            "consensus_receipt_digest": "", "authority_profile_digest": "",
            "authority_profile_source_receipt_id": "",
            "signature": "", "signer_audit_mac": "",
            "signer_audit_attestation_signature": "",
            "authentication_status": CONTROL_LOOP_DISPLAY_ONLY,
        }
    return {
        "issuer_principal_id": _bounded(context.issuer_principal_id, 256),
        "signer_public_key": _bounded(context.signer_public_key, 512),
        "signer_key_fingerprint": public_key_fingerprint(context.signer_public_key),
        "key_epoch": _bounded(context.key_epoch, 160),
        "consensus_receipt_digest": _bounded(context.consensus_receipt_digest, 256),
        "authority_profile_digest": _bounded(context.authority_profile_digest, 80),
        "authority_profile_source_receipt_id": _bounded(
            context.authority_profile_source_receipt_id, 80
        ),
        "signature": "", "signer_audit_mac": "",
        "signer_audit_attestation_signature": "",
        "authentication_status": CONTROL_LOOP_AUTHENTICATED,
    }


def canonical_control_receipt_signing_input(payload: Mapping[str, Any]) -> str:
    canonical = {
        key: value for key, value in payload.items()
        if key not in {
            "signature",
            "signer_audit_mac",
            "signer_audit_attestation_signature",
        }
    }
    return CONTROL_LOOP_SIGNING_PREFIX + json.dumps(
        canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )


def attest_control_receipt(
    payload: dict[str, Any], context: ControlLoopReceiptSigningContext
) -> None:
    signing_input = canonical_control_receipt_signing_input(payload)
    response = context.signer.sign(
        SigningRequest(
            signing_input=signing_input,
            payload_digest="sha256:" + _digest({"signing_input": signing_input}),
            signer_role="reddog_control_loop",
            signer_public_key=context.signer_public_key,
            requester_principal_id=context.issuer_principal_id,
            nonce=str(payload["nonce"]), key_epoch=context.key_epoch,
            requested_operation=CONTROL_LOOP_SIGNING_OPERATION,
            authority_tier=context.authority_tier,
            consensus_receipt_digest=context.consensus_receipt_digest,
        )
    )
    valid = bool(
        response.accepted
        and response.signer_public_key == context.signer_public_key
        and response.key_fingerprint == public_key_fingerprint(context.signer_public_key)
        and response.key_epoch == context.key_epoch
        and response.signature and response.audit_mac
        and response.audit_attestation_signature
        and response.boundary_attested
        and response.requester_identity_attested and response.signer_loads_no_untrusted_code
        and response.no_secret_material_returned
        and context.signature_verifier.verify(
            context.signer_public_key, signing_input, response.signature
        )
        and context.signature_verifier.verify(
            context.signer_public_key,
            canonical_control_audit_attestation_input(
                signing_input=signing_input,
                signature=response.signature,
                audit_mac=response.audit_mac,
                signer_public_key=context.signer_public_key,
                key_epoch=context.key_epoch,
                requester_principal_id=context.issuer_principal_id,
            ),
            response.audit_attestation_signature,
        )
    )
    if not valid:
        raise ValueError("resident_control_loop_receipt_signing_rejected")
    payload["signature"] = response.signature
    payload["signer_audit_mac"] = response.audit_mac
    payload["signer_audit_attestation_signature"] = (
        response.audit_attestation_signature
    )


def verify_control_receipt_authentication(
    payload: Mapping[str, Any], *, expected_signer_public_key: str | None,
    expected_key_epoch: str | None, expected_consensus_receipt_digest: str | None,
    expected_authority_profile_digest: str | None,
    expected_authority_profile_source_receipt_id: str | None,
    expected_issuer_principal_id: str | None,
    require_authenticated: bool,
    signature_verifier: SignatureVerifier | None,
) -> None:
    if payload.get("authentication_status") == CONTROL_LOOP_DISPLAY_ONLY:
        _verify_display_only(payload, require_authenticated)
        return
    if payload.get("authentication_status") != CONTROL_LOOP_AUTHENTICATED:
        raise ValueError("resident_control_loop_receipt_authentication_status_invalid")
    _verify_expected_bindings(
        payload, expected_signer_public_key, expected_key_epoch,
        expected_consensus_receipt_digest, expected_authority_profile_digest,
        expected_authority_profile_source_receipt_id,
        expected_issuer_principal_id,
    )
    public_key = str(payload.get("signer_public_key") or "")
    if payload.get("signer_key_fingerprint") != public_key_fingerprint(public_key):
        raise ValueError("resident_control_loop_receipt_fingerprint_invalid")
    verifier = signature_verifier or Ed25519SignatureVerifier()
    signing_input = canonical_control_receipt_signing_input(payload)
    signature = str(payload.get("signature") or "")
    audit_mac = str(payload.get("signer_audit_mac") or "")
    audit_attestation_signature = str(
        payload.get("signer_audit_attestation_signature") or ""
    )
    if not verifier.verify(
        public_key, signing_input,
        signature,
    ):
        raise ValueError("resident_control_loop_receipt_signature_invalid")
    if not audit_mac or not audit_attestation_signature or not verifier.verify(
        public_key,
        canonical_control_audit_attestation_input(
            signing_input=signing_input,
            signature=signature,
            audit_mac=audit_mac,
            signer_public_key=public_key,
            key_epoch=str(payload.get("key_epoch") or ""),
            requester_principal_id=str(payload.get("issuer_principal_id") or ""),
        ),
        audit_attestation_signature,
    ):
        raise ValueError("resident_control_loop_receipt_audit_attestation_invalid")


def validate_control_receipt_child_evidence(
    payload: Mapping[str, Any],
    source_receipt_ids: tuple[str, ...],
    receipt_ids: tuple[str, ...],
    child_digests: tuple[str, ...],
    outcomes: tuple[dict[str, str], ...],
) -> None:
    """Bind each worker outcome to one digest and each success to one receipt."""

    completion = _nonnegative_int(payload.get("worker_completion_count"))
    requeue = _nonnegative_int(payload.get("worker_requeue_count"))
    failure = _nonnegative_int(payload.get("worker_failure_count"))
    statuses = tuple(outcome["status"] for outcome in outcomes)
    expected_counts = {
        "completed": completion,
        "requeued": requeue,
        "failed": failure,
    }
    if any(statuses.count(status) != count for status, count in expected_counts.items()):
        raise ValueError("resident_control_loop_receipt_child_outcome_count_invalid")
    projected_receipts = tuple(
        outcome["receipt_id"]
        for outcome in outcomes
        if outcome["status"] in {"completed", "requeued"}
    )
    projected_digests = tuple(outcome["evidence_digest"] for outcome in outcomes)
    if (
        receipt_ids != projected_receipts
        or any(receipt_id not in source_receipt_ids for receipt_id in projected_receipts)
        or len(set(receipt_ids)) != len(receipt_ids)
    ):
        raise ValueError("resident_control_loop_receipt_child_receipt_cardinality_invalid")
    if (
        child_digests != projected_digests
        or len(child_digests) != completion + requeue + failure
        or len(set(child_digests)) != len(child_digests)
        or any(not _is_sha256_digest(item) for item in child_digests)
    ):
        raise ValueError("resident_control_loop_receipt_child_evidence_cardinality_invalid")
    if payload.get("child_execution_evidence_count") != len(child_digests):
        raise ValueError("resident_control_loop_receipt_child_evidence_count_invalid")
    if payload.get("child_execution_evidence_digest") != "sha256:" + _digest(
        list(child_digests)
    ):
        raise ValueError("resident_control_loop_receipt_child_evidence_digest_invalid")


def _verify_display_only(payload: Mapping[str, Any], require_authenticated: bool) -> None:
    if require_authenticated:
        raise ValueError("resident_control_loop_receipt_authentication_required")
    fields = (
        "issuer_principal_id", "signer_public_key", "signer_key_fingerprint", "key_epoch",
        "consensus_receipt_digest", "authority_profile_digest",
        "authority_profile_source_receipt_id", "signature", "signer_audit_mac",
        "signer_audit_attestation_signature",
    )
    if any(payload.get(key) for key in fields):
        raise ValueError("resident_control_loop_receipt_display_auth_fields_invalid")


def _verify_expected_bindings(
    payload: Mapping[str, Any], public_key: str | None, key_epoch: str | None,
    consensus: str | None, profile_digest: str | None,
    profile_source_receipt_id: str | None,
    issuer_principal_id: str | None,
) -> None:
    checks = (
        (public_key, payload.get("signer_public_key"), "signer_invalid"),
        (key_epoch, payload.get("key_epoch"), "key_epoch_invalid"),
        (consensus, payload.get("consensus_receipt_digest"), "consensus_invalid"),
        (profile_digest, payload.get("authority_profile_digest"), "authority_profile_invalid"),
        (
            profile_source_receipt_id,
            payload.get("authority_profile_source_receipt_id"),
            "authority_profile_source_invalid",
        ),
        (issuer_principal_id, payload.get("issuer_principal_id"), "issuer_principal_invalid"),
    )
    for expected, observed, reason in checks:
        if expected is not None and observed != expected:
            raise ValueError("resident_control_loop_receipt_" + reason)


def _bounded(value: Any, limit: int) -> str:
    return str(value or "").strip()[:limit]


def _nonnegative_int(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError("resident_control_loop_receipt_integer_invalid")
    return value


def _is_sha256_digest(value: object) -> bool:
    text = str(value or "")
    return len(text) == 71 and text.startswith("sha256:") and all(
        char in "0123456789abcdef" for char in text[7:]
    )


def _digest(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


__all__ = [
    "CONTROL_LOOP_AUTHENTICATED", "CONTROL_LOOP_DISPLAY_ONLY",
    "ControlLoopReceiptSigningContext", "attest_control_receipt",
    "canonical_control_receipt_signing_input", "control_receipt_authentication_fields",
    "validate_control_receipt_child_evidence",
    "verify_control_receipt_authentication",
]
