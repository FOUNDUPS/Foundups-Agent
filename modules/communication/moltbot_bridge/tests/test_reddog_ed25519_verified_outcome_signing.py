"""Verified-outcome domain tests for the Ed25519 signer backend."""

from __future__ import annotations

from dataclasses import asdict, replace
from types import SimpleNamespace

import pytest

from modules.communication.moltbot_bridge.src import (
    foundup_memex_verified_outcome_signing as outcome_signing,
    foundup_verified_outcome_root_authority_state as outcome_state,
    reddog_ed25519_signer_backend as signer_backend_module,
)
from modules.communication.moltbot_bridge.src.reddog_authority_runtime_store import (
    AtomicJsonAuthorityRuntimeStore,
)
from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_authority_wire_codec import (
    MAX_MESSAGE_BYTES, canonical_bytes, decode_message, digest_mapping, encode_message,
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


@pytest.fixture
def outcome_response_record_inputs(tmp_path, monkeypatch):
    values, backend, request, peer, counts = _root_outcome_backend(tmp_path, monkeypatch)
    descriptor, grant, state, *_stores, current, authority = values
    captured = {}
    finalize = signer_backend_module._finalize_signing

    def capture_reservation(*args, **kwargs):
        captured["reservation"] = args[4]
        return finalize(*args, **kwargs)

    monkeypatch.setattr(signer_backend_module, "_finalize_signing", capture_reservation)
    response = backend.sign(request, peer)
    assert response.accepted is True
    binding = outcome_signing.VerifiedOutcomeResponseBinding(
        descriptor_id=descriptor["descriptor_id"],
        owner_config_id=current["snapshot"].owner_config_id,
        authorization_id=grant["authorization_id"],
        reservation_id=captured["reservation"].reservation_id,
    )
    return SimpleNamespace(
        request=request, response=response, descriptor=descriptor, binding=binding,
        verifier=Ed25519SignatureVerifier(), counts=counts, state=state, grant=grant,
        authority=authority, backend=backend, peer=peer,
    )


def _build_outcome_record(values, **overrides):
    arguments = dict(
        request=values.request, response=values.response,
        descriptor=values.descriptor, binding=values.binding,
        signature_verifier=values.verifier,
    )
    arguments.update(overrides)
    return outcome_signing.build_verified_outcome_response_record(**arguments)


def _parse_outcome_record(values, raw, **overrides):
    arguments = dict(
        expected_binding=values.binding,
        expected_record_digest=decode_message(raw)["record_digest"],
        signature_verifier=values.verifier,
    )
    arguments.update(overrides)
    return outcome_signing.parse_verified_outcome_response_record(raw, **arguments)


def _repack_outcome_record(data):
    # Deliberately recompute untrusted hashes to exercise checks beyond integrity.
    data["response_digest"] = digest_mapping(data["response"])
    data["record_digest"] = digest_mapping(
        {key: value for key, value in data.items() if key != "record_digest"}
    )
    return encode_message(data)


def test_outcome_response_record_preserves_exact_response_without_new_authority(
    outcome_response_record_inputs,
) -> None:
    values = outcome_response_record_inputs
    marker = values.state.load(authorization_binding(values.grant["authorization_id"]))
    raw = _build_outcome_record(values)
    data = decode_message(raw)
    assert type(raw) is bytes and len(raw) < MAX_MESSAGE_BYTES
    assert raw == canonical_bytes(data) + b"\n"
    assert data["request"] == values.request.to_dict()
    assert data["response"] == values.response.to_dict()
    assert data["authority_descriptor"] == values.descriptor
    assert data["binding"] == asdict(values.binding)
    assert data["response_digest"] == digest_mapping(values.response.to_dict())
    assert data["record_digest"] == digest_mapping(
        {key: value for key, value in data.items() if key != "record_digest"}
    )
    assert _parse_outcome_record(values, raw) == (values.request, values.response)
    assert _build_outcome_record(values) == raw
    # Caller mutation cannot change already returned immutable bytes.
    values.descriptor["foundup_id"] = "changed-after-build"
    assert _parse_outcome_record(values, raw) == (values.request, values.response)
    assert values.state.load(authorization_binding(values.grant["authorization_id"])) == marker
    assert marker.sequence == 2 and values.counts["outcome_signatures"] == 1
    with pytest.raises(ValueError, match="root_service_reservation_invalid"):
        values.authority.commit(asdict(values.binding), data["response_digest"], "")
    assert values.state.load(authorization_binding(values.grant["authorization_id"])) == marker


@pytest.mark.parametrize("field", [
    "descriptor_id", "owner_config_id", "authorization_id", "reservation_id",
])
def test_outcome_response_record_rejects_foreign_expected_binding(
    outcome_response_record_inputs, field,
) -> None:
    values = outcome_response_record_inputs
    raw = _build_outcome_record(values)
    changed = replace(values.binding, **{field: "sha256:" + "f" * 64})
    with pytest.raises(ValueError):
        _parse_outcome_record(values, raw, expected_binding=changed)


@pytest.mark.parametrize("target", ["request", "response", "binding", "authority_descriptor"])
def test_outcome_response_record_rejects_extra_fields_at_every_boundary(
    outcome_response_record_inputs, target,
) -> None:
    values = outcome_response_record_inputs
    data = decode_message(_build_outcome_record(values))
    data[target]["runtime_path"] = "untrusted-path"
    with pytest.raises(ValueError):
        _parse_outcome_record(values, _repack_outcome_record(data))


@pytest.mark.parametrize("target,field,value", [
    ("response", "accepted", 1),
    ("response", "boundary_attested", "false"),
    ("response", "requester_identity_attested", False),
    ("response", "signer_loads_no_untrusted_code", 1),
    ("response", "no_secret_material_returned", "true"),
    ("response", "rejection_code", "contradiction"),
    ("response", "audit_mac", 123),
    ("response", "audit_mac", "tampered"),
    ("response", "signature", "tampered"),
    ("response", "audit_attestation_signature", "tampered"),
    ("response", "key_epoch", "another-epoch"),
    ("response", "key_fingerprint", "sha256:" + "e" * 64),
    ("request", "nonce", 123),
    ("request", "requester_principal_id", "another-principal"),
    ("request", "consensus_receipt_digest", "sha256:" + "e" * 64),
    ("request", "requested_operation", "another-operation"),
    ("request", "elevated_consensus_proof", {}),
    ("request", "payload_digest", "sha256:" + "e" * 64),
])
def test_outcome_response_record_rejects_malformed_or_resigned_hash_claims(
    outcome_response_record_inputs, target, field, value,
) -> None:
    values = outcome_response_record_inputs
    data = decode_message(_build_outcome_record(values))
    data[target][field] = value
    with pytest.raises(ValueError):
        _parse_outcome_record(values, _repack_outcome_record(data))


@pytest.mark.parametrize("field,value", [
    ("work_order_id", "foreign-work"), ("reddog_id", "foreign-reddog"),
    ("issued_at", True), ("issued_at", root_fixture.NOW + 1),
    ("covered_action_digest", "sha256:" + "e" * 64),
])
def test_outcome_response_record_rejects_changed_canonical_signing_input(
    outcome_response_record_inputs, field, value,
) -> None:
    values = outcome_response_record_inputs
    data = decode_message(_build_outcome_record(values))
    payload = decode_message(data["request"]["signing_input"][len(PREFIX_RECEIPT) + 1:].encode())
    payload[field] = value
    data["request"]["signing_input"] = canonical_signing_input(payload, PREFIX_RECEIPT)
    data["request"]["payload_digest"] = _request_digest(data["request"]["signing_input"])
    with pytest.raises(ValueError):
        _parse_outcome_record(values, _repack_outcome_record(data))


@pytest.mark.parametrize("field", ["snapshot_content_digest", "runtime_binding_digest", "held_out_signature"])
def test_outcome_response_record_rejects_grant_tampering_after_rehash(
    outcome_response_record_inputs, field,
) -> None:
    values = outcome_response_record_inputs
    data = decode_message(_build_outcome_record(values))
    descriptor = data["authority_descriptor"]
    descriptor["grants"][0][field] = "sha256:" + "e" * 64
    descriptor["grants"][0]["authorization_id"] = root_fixture.authorization_id_for(
        descriptor["grants"][0]
    )
    descriptor["descriptor_id"] = root_fixture.descriptor_id_for(descriptor)
    data["binding"]["descriptor_id"] = descriptor["descriptor_id"]
    data["binding"]["authorization_id"] = descriptor["grants"][0]["authorization_id"]
    changed = replace(values.binding, **data["binding"])
    with pytest.raises(ValueError):
        _parse_outcome_record(values, _repack_outcome_record(data), expected_binding=changed)


@pytest.mark.parametrize("mutation", ["top-extra", "missing", "duplicate", "noncanonical", "version", "digest", "response-digest", "oversize", "deep"])
def test_outcome_response_record_rejects_wire_and_digest_faults(
    outcome_response_record_inputs, mutation,
) -> None:
    values = outcome_response_record_inputs
    raw = _build_outcome_record(values)
    data = decode_message(raw)
    expected = data["record_digest"]
    if mutation == "top-extra":
        data["client_seal"] = "not-authority"
    elif mutation == "missing":
        data["response"].pop("rejection_code")
    elif mutation == "version":
        data["schema_version"] = "unknown.v2"
    elif mutation == "digest":
        data["record_digest"] = "sha256:" + "e" * 64
    elif mutation == "response-digest":
        data["response_digest"] = "sha256:" + "e" * 64
    raw = encode_message(data)
    if mutation == "duplicate":
        raw = b'{"record_digest":"duplicate",' + raw[1:]
    elif mutation == "noncanonical":
        raw = b" " + raw
    elif mutation == "oversize":
        raw = b" " * (MAX_MESSAGE_BYTES + 1)
    elif mutation == "deep":
        raw = b'{' + b'"nested":{' * 1500 + b'"value":0' + b'}' * 1501
    with pytest.raises(ValueError):
        outcome_signing.parse_verified_outcome_response_record(
            raw, expected_binding=values.binding, expected_record_digest=expected,
            signature_verifier=values.verifier,
        )


def test_outcome_response_record_requires_independent_digest_pin(outcome_response_record_inputs):
    values = outcome_response_record_inputs
    data = decode_message(_build_outcome_record(values))
    old_digest = data["record_digest"]
    data["binding"]["owner_config_id"] = "sha256:" + "e" * 64
    changed = replace(values.binding, owner_config_id=data["binding"]["owner_config_id"])
    with pytest.raises(ValueError):
        _parse_outcome_record(
            values, _repack_outcome_record(data), expected_binding=changed,
            expected_record_digest=old_digest,
        )


def test_outcome_response_record_builder_rejects_oversize_and_optional_capability(
    outcome_response_record_inputs,
) -> None:
    values = outcome_response_record_inputs
    for request in (
        replace(values.request, signing_input="x" * MAX_MESSAGE_BYTES),
        replace(values.request, elevated_consensus_proof={"untrusted": "claim"}),
    ):
        with pytest.raises(ValueError):
            _build_outcome_record(values, request=request)


@pytest.mark.parametrize("field,value", [
    ("replay_anchor_sequence", True), ("replay_anchor_binding_digest", "bad"),
    ("replay_anchor_revision", "bad"),
])
def test_outcome_response_record_rejects_malformed_cosigned_anchor_identifiers(
    outcome_response_record_inputs, tmp_path, field, value,
) -> None:
    values = outcome_response_record_inputs
    descriptor, grant, _store = root_fixture._descriptor(
        tmp_path / "co-signed-malformed-descriptor",
        descriptor_overrides={field: value},
        signer_key=root_fixture._SIGNER_KEYS[values.request.signer_public_key],
    )
    # Public co-signature checks alone do not validate mutable replay-store fields.
    outcome_signing.validate_root_verified_outcome_descriptor_public(
        descriptor, now_epoch=root_fixture.NOW,
    )
    binding = replace(values.binding, descriptor_id=descriptor["descriptor_id"],
                      authorization_id=grant["authorization_id"])
    with pytest.raises(ValueError):
        _build_outcome_record(values, descriptor=descriptor, binding=binding)


def test_outcome_response_record_bounds_complete_wire_including_newline(
    outcome_response_record_inputs,
) -> None:
    values = outcome_response_record_inputs
    original = _build_outcome_record(values)
    padding = MAX_MESSAGE_BYTES - len(original)
    mac = values.response.audit_mac + "x" * padding

    def with_mac(value):
        audit = outcome_signing.canonical_signer_audit_attestation_input(
            signing_input=values.request.signing_input, signature=values.response.signature,
            audit_mac=value, signer_public_key=values.request.signer_public_key,
            key_epoch=values.request.key_epoch,
            requester_principal_id=values.request.requester_principal_id,
            domain_prefix=outcome_signing.VERIFIED_OUTCOME_AUDIT_ATTESTATION_PREFIX,
        )
        return replace(values.response, audit_mac=value, audit_attestation_signature=
                       root_fixture._sign(root_fixture._SIGNER_KEYS[values.request.signer_public_key], audit))

    exact_response = with_mac(mac)
    exact = _build_outcome_record(values, response=exact_response)
    assert len(exact) == MAX_MESSAGE_BYTES and exact.endswith(b"\n")
    assert _parse_outcome_record(values, exact) == (values.request, exact_response)
    with pytest.raises(ValueError, match="message_too_large"):
        _build_outcome_record(values, response=with_mac(mac + "x"))


def test_outcome_response_record_history_does_not_renew_ordinary_signing(
    outcome_response_record_inputs,
) -> None:
    values = outcome_response_record_inputs
    raw = _build_outcome_record(values)
    later = replace(values.backend, proposal_clock=lambda: root_fixture.NOW + 61)
    rejected = later.sign(values.request, values.peer)
    assert rejected.accepted is False and rejected.rejection_code == REJECT_ED25519_SIGNER_REQUEST_INVALID
    assert _parse_outcome_record(values, raw) == (values.request, values.response)
    assert values.counts["outcome_signatures"] == 1


@pytest.fixture
def pending_response_inputs(tmp_path, monkeypatch):
    values, backend, request, peer, counts = _root_outcome_backend(tmp_path, monkeypatch)
    descriptor, grant, state, *_stores, current, authority = values
    captured = {}

    def hold_before_terminal_commit(*args, **kwargs):
        captured["reservation"] = args[4]
        return args[1]

    # Capture real signed bytes before v1 finalization; this is not a live RPC.
    monkeypatch.setattr(signer_backend_module, "_finalize_signing", hold_before_terminal_commit)
    response = backend.sign(request, peer)
    assert response.accepted is True
    binding = outcome_signing.VerifiedOutcomeResponseBinding(
        descriptor_id=descriptor["descriptor_id"],
        owner_config_id=current["snapshot"].owner_config_id,
        authorization_id=grant["authorization_id"],
        reservation_id=captured["reservation"].reservation_id,
    )
    pending = SimpleNamespace(
        descriptor=descriptor, grant=grant, state=state, request=request,
        response=response, binding=binding, verifier=Ed25519SignatureVerifier(),
        counts=counts, authority=authority, current=current, backend=backend, peer=peer,
    )
    pending.raw = _build_outcome_record(pending)
    pending.digest = decode_message(pending.raw)["record_digest"]
    pending.path = state.rollback_domain_root / "verified-outcome-pending-responses.json"
    pending.store = AtomicJsonAuthorityRuntimeStore(
        pending.path, allowed_root=state.rollback_domain_root, repo_root=root_fixture.REPO_ROOT,
    )
    return pending


def _persist_pending_response(values, **overrides):
    arguments = dict(
        raw=values.raw, expected_binding=values.binding,
        expected_record_digest=values.digest, now_epoch=root_fixture.NOW,
    )
    arguments.update(overrides)
    return values.state.persist_pending_response(**arguments)


def _alternate_pending_response(values, audit_suffix="-different-response"):
    mac = values.response.audit_mac + audit_suffix
    audit = outcome_signing.canonical_signer_audit_attestation_input(
        signing_input=values.request.signing_input, signature=values.response.signature,
        audit_mac=mac, signer_public_key=values.request.signer_public_key,
        key_epoch=values.request.key_epoch,
        requester_principal_id=values.request.requester_principal_id,
        domain_prefix=outcome_signing.VERIFIED_OUTCOME_AUDIT_ATTESTATION_PREFIX,
    )
    altered = replace(values.response, audit_mac=mac, audit_attestation_signature=
                      root_fixture._sign(root_fixture._SIGNER_KEYS[values.request.signer_public_key], audit))
    raw = _build_outcome_record(values, response=altered)
    return raw, decode_message(raw)["record_digest"]


def test_pending_response_storage_roundtrip_preserves_reservation_and_exact_bytes(
    pending_response_inputs, tmp_path,
) -> None:
    values = pending_response_inputs
    grant_binding = authorization_binding(values.grant["authorization_id"])
    before = values.state.load(grant_binding)
    assert before.sequence == 1
    assert _persist_pending_response(values) == values.digest
    snapshot = values.store.load()
    assert snapshot["records"] == {values.grant["authorization_id"]: values.raw.decode("ascii")}
    raw_snapshot = values.path.read_bytes()
    marker = values.state.load(outcome_state.pending_response_binding(values.grant["authorization_id"]))
    assert marker.sequence == 1 and marker.state_revision == values.digest[7:]
    rebuilt, *_stores = service_fixture._state(tmp_path, values.descriptor)
    values.state = rebuilt
    assert _persist_pending_response(values) == values.digest
    assert values.path.read_bytes() == raw_snapshot
    assert rebuilt.load(grant_binding) == before and values.counts["outcome_signatures"] == 1


@pytest.mark.parametrize("after_write", [False, True], ids=["before-write", "lost-ack"])
def test_pending_response_storage_retries_exact_bytes_after_write_error(
    pending_response_inputs, monkeypatch, after_write,
) -> None:
    values = pending_response_inputs
    commit = AtomicJsonAuthorityRuntimeStore.commit

    def interrupted(store, *args, **kwargs):
        if store.path != values.path:
            return commit(store, *args, **kwargs)
        if after_write:
            commit(store, *args, **kwargs)
        raise OSError("test_pending_write_interrupted")

    monkeypatch.setattr(AtomicJsonAuthorityRuntimeStore, "commit", interrupted)
    if after_write:
        assert _persist_pending_response(values) == values.digest
    else:
        with pytest.raises(OSError, match="pending_write_interrupted"):
            _persist_pending_response(values)
        assert not values.path.exists()
    marker = values.state.load(outcome_state.pending_response_binding(values.grant["authorization_id"]))
    assert marker.state_revision == values.digest[7:]
    monkeypatch.setattr(AtomicJsonAuthorityRuntimeStore, "commit", commit)
    assert _persist_pending_response(values) == values.digest
    assert values.store.load()["records"][values.grant["authorization_id"]] == values.raw.decode("ascii")
    assert values.counts["outcome_signatures"] == 1


def test_pending_response_storage_cancellation_keeps_selection_consumed(
    pending_response_inputs, monkeypatch,
) -> None:
    values = pending_response_inputs
    commit = AtomicJsonAuthorityRuntimeStore.commit

    def cancelled(*args, **kwargs):
        raise SystemExit("test_pending_cancelled")

    monkeypatch.setattr(AtomicJsonAuthorityRuntimeStore, "commit", cancelled)
    with pytest.raises(SystemExit, match="pending_cancelled"):
        _persist_pending_response(values)
    marker = values.state.load(outcome_state.pending_response_binding(values.grant["authorization_id"]))
    assert marker.state_revision == values.digest[7:] and not values.path.exists()
    monkeypatch.setattr(AtomicJsonAuthorityRuntimeStore, "commit", commit)
    assert _persist_pending_response(values) == values.digest


@pytest.mark.parametrize("missing_file", [False, True], ids=["existing", "lost-file"])
def test_pending_response_storage_rejects_replacement_even_after_file_loss(
    pending_response_inputs, missing_file,
) -> None:
    values = pending_response_inputs
    assert _persist_pending_response(values) == values.digest
    original = values.path.read_bytes()
    alternate, alternate_digest = _alternate_pending_response(values)
    if missing_file:
        values.path.unlink()
    with pytest.raises((ValueError, RuntimeError)):
        _persist_pending_response(values, raw=alternate, expected_record_digest=alternate_digest)
    assert not values.path.exists() if missing_file else values.path.read_bytes() == original
    assert _persist_pending_response(values) == values.digest
    assert values.path.read_bytes() == original
    assert values.counts["outcome_signatures"] == 1


@pytest.mark.parametrize("loss", ["primary", "both"])
def test_pending_response_storage_reconstructs_one_replica_but_rejects_dual_reset(
    pending_response_inputs, tmp_path, loss,
) -> None:
    values = pending_response_inputs
    assert _persist_pending_response(values) == values.digest
    original = values.path.read_bytes()
    values.state._primary.path.unlink()
    if loss == "both":
        values.state._witness.path.unlink()
    rebuilt, *_stores = service_fixture._state(tmp_path, values.descriptor)
    values.state = rebuilt
    if loss == "both":
        with pytest.raises((ValueError, RuntimeError)):
            _persist_pending_response(values)
    else:
        assert _persist_pending_response(values) == values.digest
    assert values.path.read_bytes() == original and values.counts["outcome_signatures"] == 1


@pytest.mark.parametrize("drift", ["expired", "generation", "reservation", "digest", "terminal"])
def test_pending_response_storage_requires_current_exact_reserved_context(
    pending_response_inputs, drift,
) -> None:
    values = pending_response_inputs
    arguments = {}
    if drift == "expired":
        arguments["now_epoch"] = root_fixture.NOW + 301
    elif drift == "generation":
        values.state.observe_generation(2, root_fixture._sha("new-owner"))
    elif drift == "reservation":
        arguments["expected_binding"] = replace(values.binding, reservation_id=root_fixture._sha("wrong"))
    elif drift == "digest":
        arguments["expected_record_digest"] = root_fixture._sha("wrong")
    else:
        grant_binding = authorization_binding(values.grant["authorization_id"])
        before = values.state.load(grant_binding)
        values.state.advance(grant_binding, expected=before,
                             next_value=replace(before, sequence=2))
    with pytest.raises((ValueError, RuntimeError)):
        _persist_pending_response(values, **arguments)
    assert not values.path.exists()


def test_pending_response_storage_preserves_conflicting_durable_bytes(pending_response_inputs):
    values = pending_response_inputs
    assert _persist_pending_response(values) == values.digest
    alternate, _digest = _alternate_pending_response(values)
    snapshot = values.store.load()
    snapshot["records"][values.grant["authorization_id"]] = alternate.decode("ascii")
    values.store.commit(snapshot, expected_revision=snapshot["revision"])
    conflicting = values.path.read_bytes()
    with pytest.raises((ValueError, RuntimeError)):
        _persist_pending_response(values)
    assert values.path.read_bytes() == conflicting


def _many_pending_responses(tmp_path, monkeypatch):
    original = service_fixture._descriptor

    def descriptor_with_nine_grants(*args, **kwargs):
        descriptor, first, store = original(*args, **kwargs)
        for index in range(1, 9):
            verifier_key, held_out_key = _private_key(), _private_key()
            grant = dict(first, receipt_id=f"verified-outcome-capacity-{index}",
                         work_order_id=f"work-order-{index}",
                         evidence_digest=root_fixture._sha(f"evidence-{index}"),
                         verifier_public_key=_public_text(verifier_key),
                         held_out_verifier_public_key=_public_text(held_out_key))
            grant["authorization_id"] = root_fixture.authorization_id_for(grant)
            grant["verification_signature"] = root_fixture._sign(
                verifier_key, root_fixture.canonical_verifier_authorization_input(grant))
            grant["held_out_signature"] = root_fixture._sign(
                held_out_key, root_fixture.canonical_held_out_authorization_input(grant))
            descriptor["grants"].append(grant)
        descriptor["descriptor_id"] = root_fixture.descriptor_id_for(descriptor)
        return descriptor, first, store

    monkeypatch.setattr(service_fixture, "_descriptor", descriptor_with_nine_grants)
    values, backend, template, peer, counts = _root_outcome_backend(tmp_path, monkeypatch)
    descriptor, _grant, state, *_stores, current, _authority = values
    captured = {}

    def hold(*args, **kwargs):
        captured["reservation"] = args[4]
        return args[1]

    monkeypatch.setattr(signer_backend_module, "_finalize_signing", hold)
    results = []
    for grant in descriptor["grants"]:
        payload = build_receipt_payload_for_signing(
            receipt_id=grant["receipt_id"], work_order_id=grant["work_order_id"],
            reddog_id=descriptor["reddog_id"], prev_receipt_hash=None,
            covered_action_digest=grant["evidence_digest"], reward_account=None,
            issued_at=root_fixture.NOW)
        signing_input = canonical_signing_input(payload, PREFIX_RECEIPT)
        request = replace(template, signing_input=signing_input,
                          payload_digest=_request_digest(signing_input), nonce=grant["receipt_id"])
        response = backend.sign(request, peer)
        assert response.accepted is True
        item = SimpleNamespace(
            request=request, response=response, descriptor=descriptor, grant=grant,
            state=state, verifier=Ed25519SignatureVerifier(), counts=counts,
            binding=outcome_signing.VerifiedOutcomeResponseBinding(
                descriptor["descriptor_id"], current["snapshot"].owner_config_id,
                grant["authorization_id"], captured["reservation"].reservation_id))
        item.raw = _build_outcome_record(item)
        item.digest = decode_message(item.raw)["record_digest"]
        item.path = state.rollback_domain_root / "verified-outcome-pending-responses.json"
        item.store = AtomicJsonAuthorityRuntimeStore(
            item.path, allowed_root=state.rollback_domain_root, repo_root=root_fixture.REPO_ROOT)
        results.append(item)
    return results


def test_pending_response_storage_enforces_real_eight_record_capacity(tmp_path, monkeypatch):
    values = _many_pending_responses(tmp_path, monkeypatch)
    for item in values[:8]:
        assert _persist_pending_response(item) == item.digest
    original = values[0].path.read_bytes()
    assert len(values[0].store.load()["records"]) == 8
    with pytest.raises(ValueError, match="capacity_exceeded"):
        _persist_pending_response(values[8])
    assert values[0].path.read_bytes() == original
    assert values[8].state.load(outcome_state.pending_response_binding(values[8].grant["authorization_id"])) is None
    assert values[8].state.load(authorization_binding(values[8].grant["authorization_id"])).sequence == 1
    assert values[0].counts["outcome_signatures"] == 9


def test_pending_response_storage_bounds_complete_pretty_printed_snapshot(tmp_path, monkeypatch):
    values = _many_pending_responses(tmp_path, monkeypatch)
    accepted = 0
    for item in values:
        raw, digest = _alternate_pending_response(item, "x" * (MAX_MESSAGE_BYTES - len(item.raw)))
        assert len(raw) == MAX_MESSAGE_BYTES
        before = item.path.read_bytes() if item.path.exists() else None
        try:
            _persist_pending_response(item, raw=raw, expected_record_digest=digest)
        except ValueError as exc:
            assert "store_too_large" in str(exc)
            assert item.path.read_bytes() == before
            break
        accepted += 1
        assert len(item.path.read_bytes()) <= 512 * 1024
    else:
        pytest.fail("Complete pending snapshot byte limit was not exercised")
    assert 0 < accepted < 8


def test_pending_response_storage_concurrent_instances_keep_one_record(
    pending_response_inputs, tmp_path,
) -> None:
    from concurrent.futures import ThreadPoolExecutor
    values = pending_response_inputs
    rebuilt, *_stores = service_fixture._state(tmp_path, values.descriptor)
    second = SimpleNamespace(**vars(values))
    second.state = rebuilt
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(_persist_pending_response, (values, second)))
    assert results == [values.digest, values.digest]
    assert values.store.load()["records"] == {values.grant["authorization_id"]: values.raw.decode("ascii")}
    assert values.state.load(authorization_binding(values.grant["authorization_id"])).sequence == 1
    assert values.counts["outcome_signatures"] == 1


@pytest.mark.parametrize("after_advance", [False, True], ids=["partial-mirror", "lost-mirror-ack"])
def test_pending_response_storage_retains_selection_across_mirror_failure(
    pending_response_inputs, monkeypatch, after_advance,
) -> None:
    values = pending_response_inputs
    binding = outcome_state.pending_response_binding(values.grant["authorization_id"])
    advance = values.state._witness.advance

    def failed(digest, *args, **kwargs):
        if digest != binding:
            return advance(digest, *args, **kwargs)
        if after_advance:
            advance(digest, *args, **kwargs)
        raise RuntimeError("test_pending_witness_failure")

    monkeypatch.setattr(values.state._witness, "advance", failed)
    if after_advance:
        assert _persist_pending_response(values) == values.digest
    else:
        with pytest.raises(RuntimeError, match="pending_witness_failure"):
            _persist_pending_response(values)
        assert not values.path.exists()
        assert values.state._witness.load(binding) is None
    assert values.state._primary.load(binding).state_revision == values.digest[7:]
    monkeypatch.setattr(values.state._witness, "advance", advance)
    assert _persist_pending_response(values) == values.digest


@pytest.mark.parametrize("fail_on_call", [1, 2], ids=["before-write", "before-ack"])
def test_pending_response_storage_rechecks_file_ownership(
    pending_response_inputs, monkeypatch, fail_on_call,
) -> None:
    values = pending_response_inputs
    values.state._require_ownership = True
    checks = []
    monkeypatch.setattr(outcome_state, "_require_root_owned", lambda *_args: None)

    def check(*paths):
        if values.path in paths:
            checks.append(paths)
            if len(checks) == fail_on_call:
                raise ValueError("test_pending_owner_changed")
        else:
            assert set(paths) == {
                values.state._primary.path, values.state._witness.path,
                values.state._installation.path,
            }

    # This injects the ownership decision, not production Linux UID evidence.
    monkeypatch.setattr(outcome_state, "_require_root_files", check)
    with pytest.raises(ValueError, match="pending_owner_changed"):
        _persist_pending_response(values)
    assert values.path.exists() is (fail_on_call == 2)
    assert values.state.load(authorization_binding(values.grant["authorization_id"])).sequence == 1


def test_pending_response_storage_rejects_unanchored_unrelated_row(pending_response_inputs):
    values = pending_response_inputs
    assert _persist_pending_response(values) == values.digest
    snapshot = values.store.load()
    snapshot["records"]["verified-outcome-authorization-unanchored"] = values.raw.decode("ascii")
    values.store.commit(snapshot, expected_revision=snapshot["revision"])
    original = values.path.read_bytes()
    with pytest.raises(ValueError, match="selection_missing"):
        _persist_pending_response(values)
    assert values.path.read_bytes() == original
