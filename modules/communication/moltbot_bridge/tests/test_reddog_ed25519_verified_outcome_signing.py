"""Verified-outcome domain tests for the Ed25519 signer backend."""

from __future__ import annotations

from dataclasses import replace

import pytest

from modules.communication.moltbot_bridge.src.foundup_memex_verified_outcome_signing import (
    VERIFIED_OUTCOME_SIGNER_ROLE,
    VERIFIED_OUTCOME_SIGNING_OPERATION,
    VerifiedOutcomeSignerPolicy,
)
from modules.communication.moltbot_bridge.src.reddog_ed25519_signature_verifier_backend import (
    Ed25519SignatureVerifier,
)
from modules.communication.moltbot_bridge.src.reddog_ed25519_signer_backend import (
    Ed25519SignerBackend,
    REJECT_ED25519_SIGNER_OUTCOME_AUTHORITY_MISSING,
    REJECT_ED25519_SIGNER_OUTCOME_AUTHORITY_REJECTED,
    REJECT_ED25519_SIGNER_REQUEST_INVALID,
)
from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    SigningRequest,
)
from modules.communication.moltbot_bridge.src.reddog_signed_receipt_chain import (
    build_receipt_payload_for_signing,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import (
    PREFIX_RECEIPT,
    canonical_signing_input,
)
from modules.communication.moltbot_bridge.tests.test_reddog_ed25519_signer_backend import (
    AuditMacBuilder,
    _peer,
    _private_key,
    _public_text,
    _request_digest,
)


pytest.importorskip("cryptography")


class OneUseOutcomeAuthority:
    def __init__(self, expected_digest: str) -> None:
        self.expected_digest = expected_digest
        self.reserved: set[str] = set()
        self.committed: set[str] = set()

    def reserve(self, **values: object) -> object | None:
        receipt_id = str(values.get("receipt_id") or "")
        if (
            values.get("evidence_digest") != self.expected_digest
            or not receipt_id
            or receipt_id in self.reserved
            or receipt_id in self.committed
        ):
            return None
        self.reserved.add(receipt_id)
        return receipt_id

    def reserve_proof_input(self, **values: object) -> str:
        return "test-reserve-proof:" + str(values.get("receipt_id") or "")

    def commit(
        self, reservation: object, signature_digest: str,
        signer_instance_signature: str,
    ) -> None:
        assert signature_digest.startswith("sha256:")
        assert signer_instance_signature.startswith("ed25519-sig-v1:")
        receipt_id = str(reservation)
        if receipt_id not in self.reserved:
            raise ValueError("outcome_reservation_missing")
        self.reserved.remove(receipt_id)
        self.committed.add(receipt_id)

    def commit_proof_input(
        self, reservation: object, signature_digest: str
    ) -> str:
        return f"test-commit-proof:{reservation}:{signature_digest}"

    def rollback(self, reservation: object) -> None:
        self.reserved.discard(str(reservation))


def _outcome_policy(public_key: str) -> VerifiedOutcomeSignerPolicy:
    return VerifiedOutcomeSignerPolicy(
        issuer_principal_id="github:mjtrout",
        reddog_id="reddog-0102",
        signer_public_key=public_key,
        key_epoch="epoch-1",
        authority_tier="HIGH",
        consensus_receipt_digest="sha256:" + "c" * 64,
    )


def _outcome_request(public_key: str) -> tuple[SigningRequest, str, str]:
    payload = build_receipt_payload_for_signing(
        receipt_id="verified-outcome-test",
        work_order_id="wo-1",
        reddog_id="reddog-0102",
        prev_receipt_hash=None,
        covered_action_digest="sha256:" + "d" * 64,
        reward_account=None,
        issued_at=1_800_000_000,
    )
    signing_input = canonical_signing_input(payload, PREFIX_RECEIPT)
    request = SigningRequest(
        signing_input=signing_input,
        payload_digest=_request_digest(signing_input),
        signer_role=VERIFIED_OUTCOME_SIGNER_ROLE,
        signer_public_key=public_key,
        requester_principal_id="github:mjtrout",
        nonce=payload["receipt_id"],
        key_epoch="epoch-1",
        requested_operation=VERIFIED_OUTCOME_SIGNING_OPERATION,
        authority_tier="HIGH",
        consensus_receipt_digest="sha256:" + "c" * 64,
    )
    return request, signing_input, payload["covered_action_digest"]


def _outcome_backend(private_key: object, public_key: str) -> Ed25519SignerBackend:
    return Ed25519SignerBackend(
        private_key=private_key,
        public_key=public_key,
        key_epoch="epoch-1",
        audit_mac_builder=AuditMacBuilder(),
        verified_outcome_signer_policy=_outcome_policy(public_key),
        proposal_clock=lambda: 1_800_000_000,
    )


def test_ed25519_backend_signs_only_exact_verified_outcome_domain() -> None:
    private_key = _private_key()
    public_key = _public_text(private_key)
    request, signing_input, evidence_digest = _outcome_request(public_key)
    missing_authority_backend = _outcome_backend(private_key, public_key)
    missing_authority = missing_authority_backend.sign(request, _peer())
    authority = OneUseOutcomeAuthority(evidence_digest)
    backend = replace(
        missing_authority_backend,
        verified_outcome_signing_authority=authority,
    )

    accepted = backend.sign(request, _peer())
    replay = backend.sign(request, _peer())
    wrong_digest = backend.sign(
        replace(request, payload_digest="sha256:" + "0" * 64),
        _peer(),
    )
    wrong_domain = backend.sign(
        replace(request, requested_operation="create_foundup"),
        _peer(),
    )

    assert missing_authority.accepted is False
    assert missing_authority.rejection_code == REJECT_ED25519_SIGNER_OUTCOME_AUTHORITY_MISSING
    assert accepted.accepted is True
    assert Ed25519SignatureVerifier().verify(
        public_key,
        signing_input,
        accepted.signature,
    ) is True
    assert wrong_digest.accepted is False
    assert wrong_digest.rejection_code == REJECT_ED25519_SIGNER_REQUEST_INVALID
    assert wrong_domain.accepted is False
    assert replay.accepted is False
    assert replay.rejection_code == REJECT_ED25519_SIGNER_OUTCOME_AUTHORITY_REJECTED
