"""Verified-outcome domain tests for the Ed25519 signer backend."""

from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace

import pytest

from modules.communication.moltbot_bridge.src import (
    reddog_ed25519_signer_backend as signer_backend_module,
)
from modules.communication.moltbot_bridge.src.foundup_memex_verified_outcome_publisher import (
    _validate_signer_response,
)
from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_authority_state import (
    authorization_binding,
)
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
from modules.communication.moltbot_bridge.tests import (
    test_foundup_verified_outcome_root_authority as root_fixture,
    test_foundup_verified_outcome_root_authority_service as service_fixture,
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


def _root_outcome_backend(tmp_path, monkeypatch):
    values = service_fixture._runtime(tmp_path, monkeypatch)
    descriptor, grant, _state, *_rest, authority = values
    public_key = descriptor["signer_public_key"]
    private_key = root_fixture._SIGNER_KEYS[public_key]
    payload = build_receipt_payload_for_signing(
        receipt_id=grant["receipt_id"], work_order_id=grant["work_order_id"],
        reddog_id=descriptor["reddog_id"], prev_receipt_hash=None,
        covered_action_digest=grant["evidence_digest"], reward_account=None,
        issued_at=root_fixture.NOW,
    )
    signing_input = canonical_signing_input(payload, PREFIX_RECEIPT)
    request = replace(
        _outcome_request(public_key)[0], signing_input=signing_input,
        payload_digest=_request_digest(signing_input),
        requester_principal_id=descriptor["issuer_principal_id"],
        consensus_receipt_digest=descriptor["consensus_receipt_digest"],
    )
    counts = {"outcome_signatures": 0}

    class CountingKey:
        def public_key(self):
            return private_key.public_key()

        def sign(self, value):
            if value.startswith((PREFIX_RECEIPT + ".").encode("utf-8")):
                counts["outcome_signatures"] += 1
            return private_key.sign(value)

    policy = replace(
        _outcome_policy(public_key),
        issuer_principal_id=descriptor["issuer_principal_id"],
        consensus_receipt_digest=descriptor["consensus_receipt_digest"],
    )
    backend = replace(
        _outcome_backend(CountingKey(), public_key),
        verified_outcome_signer_policy=policy,
        verified_outcome_signing_authority=authority,
    )
    peer = replace(_peer(), peer_principal_id=descriptor["issuer_principal_id"])
    return values, backend, request, peer, counts


def test_outcome_response_handoff_control_uses_real_root_state(
    tmp_path, monkeypatch
) -> None:
    values, backend, request, peer, counts = _root_outcome_backend(
        tmp_path, monkeypatch
    )
    _descriptor, grant, state, *_rest = values
    response = backend.sign(request, peer)
    assert response.accepted is True
    assert response.audit_attestation_signature
    assert Ed25519SignatureVerifier().verify(
        backend.public_key, request.signing_input, response.signature
    ) is True
    assert state.load(authorization_binding(grant["authorization_id"])).sequence == 2
    assert counts["outcome_signatures"] == 1


@pytest.mark.parametrize("after_commit", [False, True], ids=["before", "after"])
def test_outcome_response_handoff_interruption_never_reopens_root_grant(
    tmp_path, monkeypatch, after_commit
) -> None:
    values, backend, request, peer, counts = _root_outcome_backend(
        tmp_path, monkeypatch
    )
    descriptor, grant, state, *_rest = values
    finalize = signer_backend_module._finalize_signing

    def interrupted_handoff(*args, **kwargs):
        if after_commit:
            assert finalize(*args, **kwargs).accepted is True
        raise SystemExit("test_outcome_response_handoff_interrupted")

    monkeypatch.setattr(signer_backend_module, "_finalize_signing", interrupted_handoff)
    with pytest.raises(SystemExit, match="handoff_interrupted"):
        backend.sign(request, peer)
    marker = state.load(authorization_binding(grant["authorization_id"]))
    assert marker.sequence == (2 if after_commit else 1)
    assert counts["outcome_signatures"] == 1
    monkeypatch.setattr(signer_backend_module, "_finalize_signing", finalize)

    # Reopen the existing databases and mint a fresh process-local client seal.
    # This models reconstruction, not OS-process death or production UID proof.
    fresh_state, *_stores = service_fixture._state(tmp_path, descriptor)
    snapshot = service_fixture._snapshot(descriptor, state=fresh_state)
    fresh_authority = service_fixture._client_authority(
        monkeypatch, descriptor, snapshot.owner_config_id,
        lambda raw: service_fixture.handle_root_authority_request(
            raw, peer=service_fixture._peer(), state=fresh_state,
            snapshot_supplier=lambda: snapshot, now_epoch=root_fixture.NOW,
        ),
    )
    rebuilt = replace(backend, verified_outcome_signing_authority=fresh_authority)
    rejected = rebuilt.sign(request, peer)
    assert rejected.accepted is False
    assert rejected.rejection_code == REJECT_ED25519_SIGNER_OUTCOME_AUTHORITY_REJECTED
    assert not rejected.signature and not rejected.audit_attestation_signature
    assert fresh_state.load(authorization_binding(grant["authorization_id"])) == marker
    assert counts["outcome_signatures"] == 1


def test_outcome_response_handoff_retry_cannot_renew_issuance(
    tmp_path, monkeypatch
) -> None:
    values, backend, request, peer, counts = _root_outcome_backend(
        tmp_path, monkeypatch
    )
    descriptor, grant, state, *_rest = values
    assert backend.sign(request, peer).accepted is True
    marker = state.load(authorization_binding(grant["authorization_id"]))
    later = root_fixture.NOW + 61
    assert later < grant["expires_at"]
    backend = replace(backend, proposal_clock=lambda: later)
    stale = backend.sign(request, peer)
    assert stale.rejection_code == REJECT_ED25519_SIGNER_REQUEST_INVALID

    payload = build_receipt_payload_for_signing(
        receipt_id=grant["receipt_id"], work_order_id=grant["work_order_id"],
        reddog_id=descriptor["reddog_id"], prev_receipt_hash=None,
        covered_action_digest=grant["evidence_digest"], reward_account=None,
        issued_at=later,
    )
    renewed_input = canonical_signing_input(payload, PREFIX_RECEIPT)
    renewed = backend.sign(replace(
        request, signing_input=renewed_input,
        payload_digest=_request_digest(renewed_input),
    ), peer)
    assert renewed.rejection_code == REJECT_ED25519_SIGNER_OUTCOME_AUTHORITY_REJECTED
    assert not stale.accepted and not renewed.accepted
    assert not stale.signature and not renewed.signature
    assert state.load(authorization_binding(grant["authorization_id"])) == marker
    assert counts["outcome_signatures"] == 1


def _signed_outcome_response():
    private_key = _private_key()
    public_key = _public_text(private_key)
    request, signing_input, evidence_digest = _outcome_request(public_key)
    backend = replace(
        _outcome_backend(private_key, public_key),
        verified_outcome_signing_authority=OneUseOutcomeAuthority(evidence_digest),
    )
    response = backend.sign(request, _peer())
    assert response.accepted is True
    publisher = SimpleNamespace(
        signer_public_key=public_key, key_epoch=backend.key_epoch,
        issuer_principal_id=request.requester_principal_id,
        signature_verifier=Ed25519SignatureVerifier(),
    )
    return publisher, signing_input, response


def test_outcome_response_validation_accepts_real_signature_and_audit() -> None:
    publisher, signing_input, response = _signed_outcome_response()
    _validate_signer_response(publisher, response, signing_input)


@pytest.mark.parametrize("field", [
    "accepted", "boundary_attested", "requester_identity_attested",
    "signer_loads_no_untrusted_code", "no_secret_material_returned",
])
@pytest.mark.parametrize("value", [1, "false"])
def test_outcome_response_validation_rejects_truthy_boolean_claims(field, value) -> None:
    publisher, signing_input, response = _signed_outcome_response()
    malformed = replace(response, **{field: value})
    with pytest.raises(ValueError, match="verified_outcome_publish_signer_rejected"):
        _validate_signer_response(publisher, malformed, signing_input)


def test_outcome_response_validation_rejects_contradictory_rejection() -> None:
    publisher, signing_input, response = _signed_outcome_response()
    rejected = replace(response, rejection_code="test_rejection")
    with pytest.raises(ValueError, match="verified_outcome_publish_signer_rejected"):
        _validate_signer_response(publisher, rejected, signing_input)


@pytest.mark.parametrize("value", [1, "false"])
@pytest.mark.parametrize("verification", ["receipt", "audit"])
def test_outcome_response_validation_requires_boolean_verifier_result(
    value, verification
) -> None:
    publisher, signing_input, response = _signed_outcome_response()
    results = iter([value, True] if verification == "receipt" else [True, value])
    publisher.signature_verifier = SimpleNamespace(verify=lambda *_args: next(results))
    with pytest.raises(ValueError, match="verified_outcome_publish_signer_rejected"):
        _validate_signer_response(publisher, response, signing_input)
