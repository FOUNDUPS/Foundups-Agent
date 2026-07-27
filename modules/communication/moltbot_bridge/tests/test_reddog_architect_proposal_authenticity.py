"""Tests for REDDOG_ARCHITECT_PROPOSAL_AUTHENTICITY_ATTESTATION_PHASE1."""

from __future__ import annotations

import hashlib
import json
import time

import pytest

from modules.communication.moltbot_bridge.src.reddog_architect_proposal_authenticity import (
    ArchitectProposalAuthenticityPayload,
    ArchitectProposalIntegrityContext,
    ArchitectProposalSignerPolicy,
    ArchitectProposalSigningContext,
    InMemoryProposalAuthenticityNonceStore,
    PROPOSAL_AUTHENTICITY_SIGNING_OPERATION,
    PROPOSAL_AUTHENTICITY_SIGNING_PREFIX,
    attest_architect_proposal,
    build_architect_proposal_authenticity_payload,
    canonical_architect_proposal_signing_input,
    verify_architect_proposal_attestation_integrity,
)
from modules.communication.moltbot_bridge.src.reddog_ed25519_signature_verifier_backend import (
    Ed25519SignatureVerifier,
    encode_ed25519_public_key,
    encode_ed25519_signature,
)
from modules.communication.moltbot_bridge.src.reddog_ed25519_signer_backend import (
    Ed25519SignerBackend,
    REJECT_ED25519_SIGNER_DOMAIN_MISMATCH,
    REJECT_ED25519_SIGNER_PROPOSAL_AUTHORITY_POLICY_MISMATCH,
    REJECT_ED25519_SIGNER_PROPOSAL_AUTHORITY_POLICY_MISSING,
    REJECT_ED25519_SIGNER_PROPOSAL_NONCE_REPLAY,
)
from modules.communication.moltbot_bridge.src.reddog_isolated_signer_socket_protocol import (
    SignerPeerAttestation,
)
from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    SigningRequest,
)


pytest.importorskip("cryptography")

NOW = int(time.time())
SHA = "sha256:" + "a" * 64


class _AuditMac:
    def build(
        self,
        request: SigningRequest,
        signature: str,
        peer: SignerPeerAttestation,
    ) -> str:
        return "audit:" + request.nonce + ":" + peer.peer_principal_id


class _EmptyAuditMac:
    def build(
        self,
        request: SigningRequest,
        signature: str,
        peer: SignerPeerAttestation,
    ) -> str:
        return ""


class _DirectClient:
    def __init__(self, backend: Ed25519SignerBackend) -> None:
        self.backend = backend

    def sign(self, request: SigningRequest):
        return self.backend.sign(request, _peer())


def _private_key():
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    return Ed25519PrivateKey.generate()


def _public_text(private_key) -> str:
    from cryptography.hazmat.primitives import serialization

    return encode_ed25519_public_key(
        private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
    )


def _peer() -> SignerPeerAttestation:
    return SignerPeerAttestation(
        peer_principal_id="github:012",
        transport="unix_socket",
        credential_source="kernel_peer_credential",
        boundary_attested=True,
    )


def _proposal() -> dict:
    return {
        "receipt_id": "sha256:" + "1" * 64,
        "snapshot_receipt_id": "snapshot-1",
        "snapshot_content_digest": "sha256:" + "2" * 64,
        "repo_head_sha": "a" * 40,
        "work_state_revision": "revision-1",
        "report_bundle_id": "report-bundle-1",
        "wsp15_allocation_receipt_id": "wsp15-1",
        "wsp15_allocation_digest": "sha256:" + "3" * 64,
        "holoindex_generation_id": "generation-1",
        "holoindex_freshness_receipt_digest": "sha256:" + "4" * 64,
        "policy_digest": "sha256:" + "5" * 64,
        "allowed_paths": ["modules/communication/moltbot_bridge/src/example.py"],
        "denied_paths": [".github/workflows/**", ".env"],
        "required_tests": ["pytest focused"],
        "required_policy_gates": ["WSP_50", "WSP_97"],
        "target_effect_plane": "REPOSITORY_CODE_CHANGE",
    }


def _candidate() -> dict:
    return {
        "queue_candidate_id": "sha256:" + "6" * 64,
        "status": "BLOCKED_CANDIDATE",
        "slice_id": "REDDOG_EXAMPLE_PHASE1",
    }


def _determination(candidate: dict | None = None) -> dict:
    return {
        "determination_receipt_id": "sha256:" + "7" * 64,
        "action": "FIX",
        "next_slice_name": "REDDOG_EXAMPLE_PHASE1",
        "queue_candidate": candidate or _candidate(),
    }


def _payload(public_key: str, *, nonce: str = "proposal-nonce-1"):
    candidate = _candidate()
    determination = _determination(candidate)
    payload = build_architect_proposal_authenticity_payload(
        proposal_admission=_proposal(),
        determination=determination,
        queue_candidate=candidate,
        requester_principal_id="github:012",
        reddog_id="reddog-0102",
        signer_public_key=public_key,
        key_epoch="epoch-1",
        consensus_receipt_digest="sha256:" + "8" * 64,
        authority_profile_source_receipt_id="sha256:" + "9" * 64,
        nonce=nonce,
        issued_at=NOW - 5,
        expires_at=NOW + 120,
    )
    return payload, determination, candidate


def _backend(private_key, payload, **overrides):
    values = {
        "private_key": private_key,
        "public_key": payload.signer_public_key,
        "key_epoch": "epoch-1",
        "audit_mac_builder": _AuditMac(),
        "proposal_authority_policy": ArchitectProposalSignerPolicy(
            expected_payload=payload,
        ),
        "proposal_nonce_store": InMemoryProposalAuthenticityNonceStore(),
        "proposal_clock": lambda: NOW,
    }
    values.update(overrides)
    return Ed25519SignerBackend(**values)


def _attestation():
    private_key = _private_key()
    payload, determination, candidate = _payload(_public_text(private_key))
    backend = _backend(private_key, payload)
    context = ArchitectProposalSigningContext(
        signer=_DirectClient(backend),
        signature_verifier=Ed25519SignatureVerifier(),
        requester_principal_id="github:012",
        signer_public_key=payload.signer_public_key,
        key_epoch="epoch-1",
        authority_tier="ULTRA",
        consensus_receipt_digest=payload.consensus_receipt_digest,
    )
    return (
        attest_architect_proposal(payload, context),
        determination,
        candidate,
    )


def _integrity_verified(attestation, *, now_epoch: int = NOW, revoked=()):
    return verify_architect_proposal_attestation_integrity(
        attestation.to_dict(),
        context=ArchitectProposalIntegrityContext(
            expected_payload=attestation.payload,
            now_epoch=now_epoch,
            revoked_key_epochs=frozenset(revoked),
        ),
    )


def test_exact_policy_signs_and_integrity_verifier_rehydrates() -> None:
    attestation, _, _ = _attestation()

    verified = _integrity_verified(attestation)

    assert verified == attestation
    assert not hasattr(verified, "accepted")
    assert not hasattr(verified, "verified")


def test_serialized_attestation_has_no_authority_marker() -> None:
    attestation, _, _ = _attestation()

    serialized = attestation.to_dict()

    assert "accepted" not in serialized
    assert "verified" not in serialized
    assert "authority_granted" not in serialized


@pytest.mark.parametrize("operation,prefix", [
    ("create_foundup", PROPOSAL_AUTHENTICITY_SIGNING_PREFIX),
    (PROPOSAL_AUTHENTICITY_SIGNING_OPERATION, "reddog-workauth.v1."),
])
def test_proposal_domain_confusion_is_rejected(operation: str, prefix: str) -> None:
    private_key = _private_key()
    public_key = _public_text(private_key)
    payload, _, _ = _payload(public_key)
    backend = _backend(private_key, payload)
    response = backend.sign(
        SigningRequest(
            signing_input=prefix + "{}",
            payload_digest=SHA,
            signer_role="reddog_architect",
            signer_public_key=public_key,
            requester_principal_id="github:012",
            nonce="n",
            key_epoch="epoch-1",
            requested_operation=operation,
            authority_tier="ULTRA",
            consensus_receipt_digest=payload.consensus_receipt_digest,
        ),
        _peer(),
    )

    assert response.accepted is False
    assert response.rejection_code == REJECT_ED25519_SIGNER_DOMAIN_MISMATCH


def test_signer_requires_policy_and_exact_payload() -> None:
    private_key = _private_key()
    payload, _, _ = _payload(_public_text(private_key))
    context = ArchitectProposalSigningContext(
        signer=_DirectClient(
            _backend(private_key, payload, proposal_authority_policy=None)
        ),
        signature_verifier=Ed25519SignatureVerifier(),
        requester_principal_id="github:012",
        signer_public_key=payload.signer_public_key,
        key_epoch="epoch-1",
        authority_tier="ULTRA",
        consensus_receipt_digest=payload.consensus_receipt_digest,
    )
    with pytest.raises(ValueError):
        attest_architect_proposal(payload, context)
    request = SigningRequest(
        signing_input=PROPOSAL_AUTHENTICITY_SIGNING_PREFIX + json.dumps(
            {**payload.to_dict(), "repo_head_sha": "b" * 40},
            sort_keys=True,
            separators=(",", ":"),
        ),
        payload_digest=SHA,
        signer_role="reddog_architect",
        signer_public_key=payload.signer_public_key,
        requester_principal_id="github:012",
        nonce=payload.nonce,
        key_epoch="epoch-1",
        requested_operation=PROPOSAL_AUTHENTICITY_SIGNING_OPERATION,
        authority_tier="ULTRA",
        consensus_receipt_digest=payload.consensus_receipt_digest,
    )
    response = _backend(private_key, payload).sign(request, _peer())
    assert response.accepted is False
    assert response.rejection_code in {
        REJECT_ED25519_SIGNER_PROPOSAL_AUTHORITY_POLICY_MISMATCH,
        REJECT_ED25519_SIGNER_PROPOSAL_AUTHORITY_POLICY_MISSING,
    }
    malformed_policy_backend = _backend(
        private_key,
        payload,
        proposal_authority_policy=ArchitectProposalSignerPolicy(  # type: ignore[arg-type]
            expected_payload={}
        ),
    )
    malformed_response = malformed_policy_backend.sign(request, _peer())
    assert malformed_response.accepted is False
    assert (
        malformed_response.rejection_code
        == REJECT_ED25519_SIGNER_PROPOSAL_AUTHORITY_POLICY_MISMATCH
    )


def test_signer_consumes_nonce_once() -> None:
    private_key = _private_key()
    payload, _, _ = _payload(_public_text(private_key))
    backend = _backend(private_key, payload)
    context = ArchitectProposalSigningContext(
        signer=_DirectClient(backend),
        signature_verifier=Ed25519SignatureVerifier(),
        requester_principal_id="github:012",
        signer_public_key=payload.signer_public_key,
        key_epoch="epoch-1",
        authority_tier="ULTRA",
        consensus_receipt_digest=payload.consensus_receipt_digest,
    )

    attest_architect_proposal(payload, context)
    response = backend.sign(
        SigningRequest(
            signing_input=PROPOSAL_AUTHENTICITY_SIGNING_PREFIX
            + json.dumps(payload.to_dict(), sort_keys=True, separators=(",", ":")),
            payload_digest=_digest(
                {
                    "signing_input": PROPOSAL_AUTHENTICITY_SIGNING_PREFIX
                    + json.dumps(
                        payload.to_dict(),
                        sort_keys=True,
                        separators=(",", ":"),
                    )
                }
            ),
            signer_role="reddog_architect",
            signer_public_key=payload.signer_public_key,
            requester_principal_id="github:012",
            nonce=payload.nonce,
            key_epoch="epoch-1",
            requested_operation=PROPOSAL_AUTHENTICITY_SIGNING_OPERATION,
            authority_tier="ULTRA",
            consensus_receipt_digest=payload.consensus_receipt_digest,
        ),
        _peer(),
    )
    assert response.accepted is False
    assert response.rejection_code == REJECT_ED25519_SIGNER_PROPOSAL_NONCE_REPLAY


def test_signer_rolls_back_nonce_reservation_when_audit_mac_fails() -> None:
    private_key = _private_key()
    payload, _, _ = _payload(_public_text(private_key))
    nonce_store = InMemoryProposalAuthenticityNonceStore()
    failing = _backend(
        private_key,
        payload,
        audit_mac_builder=_EmptyAuditMac(),
        proposal_nonce_store=nonce_store,
    )
    succeeding = _backend(
        private_key,
        payload,
        audit_mac_builder=_AuditMac(),
        proposal_nonce_store=nonce_store,
    )
    context_values = {
        "signature_verifier": Ed25519SignatureVerifier(),
        "requester_principal_id": "github:012",
        "signer_public_key": payload.signer_public_key,
        "key_epoch": "epoch-1",
        "authority_tier": "ULTRA",
        "consensus_receipt_digest": payload.consensus_receipt_digest,
    }

    with pytest.raises(ValueError):
        attest_architect_proposal(
            payload,
            ArchitectProposalSigningContext(
                signer=_DirectClient(failing),
                **context_values,
            ),
        )
    accepted = attest_architect_proposal(
        payload,
        ArchitectProposalSigningContext(
            signer=_DirectClient(succeeding),
            **context_values,
        ),
    )

    assert accepted.signature


@pytest.mark.parametrize(
    "field,value",
    [
        ("repo_head_sha", "b" * 40),
        ("wsp15_allocation_digest", "sha256:" + "b" * 64),
        ("holoindex_generation_id", "generation-2"),
        ("key_epoch", "epoch-2"),
        ("requester_principal_id", "github:attacker"),
    ],
)
def test_tampered_signed_field_fails_verification(field: str, value: object) -> None:
    attestation, _, _ = _attestation()
    serialized = attestation.to_dict()
    serialized[field] = value

    with pytest.raises(ValueError):
        verify_architect_proposal_attestation_integrity(
            serialized,
            context=ArchitectProposalIntegrityContext(
                expected_payload=attestation.payload,
                now_epoch=NOW,
            ),
        )


def test_verifier_rejects_non_typed_integrity_context() -> None:
    attestation, _, _ = _attestation()

    with pytest.raises(ValueError, match="trust_context_invalid"):
        verify_architect_proposal_attestation_integrity(
            attestation.to_dict(),
            context={},  # type: ignore[arg-type]
        )


def test_expiry_and_revocation_fail_closed() -> None:
    attestation, _, _ = _attestation()
    with pytest.raises(ValueError):
        _integrity_verified(attestation, now_epoch=NOW + 121)
    with pytest.raises(ValueError):
        _integrity_verified(attestation, revoked=("epoch-1",))


def test_verifier_rejects_ttl_above_policy_maximum() -> None:
    private_key = _private_key()
    payload, _, _ = _payload(_public_text(private_key))
    extended = build_architect_proposal_authenticity_payload(
        proposal_admission=_proposal(),
        determination=_determination(),
        queue_candidate=_candidate(),
        requester_principal_id="github:012",
        reddog_id="reddog-0102",
        signer_public_key=payload.signer_public_key,
        key_epoch="epoch-1",
        consensus_receipt_digest="sha256:" + "8" * 64,
        authority_profile_source_receipt_id="sha256:" + "9" * 64,
        nonce="long-lived-proposal",
        issued_at=NOW - 5,
        expires_at=NOW + 601,
    )
    attestation = attest_architect_proposal(
        extended,
        ArchitectProposalSigningContext(
            signer=_DirectClient(
                _backend(
                    private_key,
                    extended,
                    proposal_authority_policy=ArchitectProposalSignerPolicy(
                        expected_payload=extended,
                        max_ttl_seconds=700,
                    ),
                )
            ),
            signature_verifier=Ed25519SignatureVerifier(),
            requester_principal_id="github:012",
            signer_public_key=extended.signer_public_key,
            key_epoch="epoch-1",
            authority_tier="ULTRA",
            consensus_receipt_digest=extended.consensus_receipt_digest,
        ),
    )

    with pytest.raises(ValueError, match="expired"):
        verify_architect_proposal_attestation_integrity(
            attestation.to_dict(),
            context=ArchitectProposalIntegrityContext(
                expected_payload=extended,
                now_epoch=NOW,
                max_ttl_seconds=600,
            ),
        )


def test_verifier_rejects_non_string_identity_scalar() -> None:
    private_key = _private_key()
    payload, _, _ = _payload(_public_text(private_key))
    malformed = payload.to_dict()
    malformed["reddog_id"] = 123
    malformed["attestation_id"] = (
        "reddog_architect_proposal_attestation_"
        + _digest(
            {
                key: value
                for key, value in malformed.items()
                if key != "attestation_id"
            }
        )[7:39]
    )
    malformed_payload = ArchitectProposalAuthenticityPayload(**malformed)
    serialized = {
        **malformed,
        "signature": encode_ed25519_signature(
            private_key.sign(
                canonical_architect_proposal_signing_input(
                    malformed_payload
                ).encode("utf-8")
            )
        ),
    }

    with pytest.raises(ValueError, match="value_missing"):
        verify_architect_proposal_attestation_integrity(
            serialized,
            context=ArchitectProposalIntegrityContext(
                expected_payload=malformed_payload,
                now_epoch=NOW,
            ),
        )


def _digest(value: object) -> str:
    raw = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()
