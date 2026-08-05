"""Tests for REDDOG_ED25519_SIGNER_BACKEND_PHASE1."""

from __future__ import annotations

import ast
import hashlib
import json
from dataclasses import replace
from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.src.reddog_ed25519_signature_verifier_backend import (
    Ed25519SignatureVerifier,
    encode_ed25519_public_key,
)
from modules.communication.moltbot_bridge.src.reddog_ed25519_signer_backend import (
    CONTROL_LOOP_SIGNING_OPERATION,
    CONTROL_LOOP_SIGNING_PREFIX,
    ControlLoopAuthorityPolicy,
    Ed25519SignerBackend,
    REJECT_ED25519_SIGNER_AUDIT_MAC_MISSING,
    REJECT_ED25519_SIGNER_DOMAIN_MISMATCH,
    REJECT_ED25519_SIGNER_CONTROL_AUTHORITY_POLICY_MISMATCH,
    REJECT_ED25519_SIGNER_CONTROL_AUTHORITY_POLICY_MISSING,
    REJECT_ED25519_SIGNER_CONTROL_ANCHOR_MISSING,
    REJECT_ED25519_SIGNER_KEY_EPOCH_MISMATCH,
    REJECT_ED25519_SIGNER_PUBLIC_KEY_MISMATCH,
    canonical_control_audit_attestation_input,
)
from modules.communication.moltbot_bridge.src.reddog_isolated_signer_socket_protocol import (
    SIGNER_SOCKET_REQUEST_SCHEMA_VERSION,
    SignerPeerAttestation,
    handle_reddog_isolated_signer_socket_request,
)
from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    SigningRequest,
)
from modules.communication.moltbot_bridge.src.reddog_signer_control_loop_anchor import (
    InMemorySignerControlLoopAnchorStore,
)
from modules.communication.moltbot_bridge.src.reddog_resident_control_loop_receipt_store import (
    ControlLoopReceiptSigningContext,
    build_resident_control_loop_receipt,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "reddog_ed25519_signer_backend.py"
)


pytest.importorskip("cryptography")


class AuditMacBuilder:
    def build(self, request: SigningRequest, signature: str, peer: SignerPeerAttestation) -> str:
        return "audit:" + request.nonce + ":" + peer.peer_principal_id


class EmptyAuditMacBuilder:
    def build(self, request: SigningRequest, signature: str, peer: SignerPeerAttestation) -> str:
        return ""


def _private_key():
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    return Ed25519PrivateKey.generate()


def _public_text(private_key) -> str:
    from cryptography.hazmat.primitives import serialization

    public_bytes = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return encode_ed25519_public_key(public_bytes)


def _peer() -> SignerPeerAttestation:
    return SignerPeerAttestation(
        peer_principal_id="github:mjtrout",
        transport="unix_socket",
        credential_source="kernel_peer_credential",
        boundary_attested=True,
    )


def _request(public_key: str, **overrides: object) -> SigningRequest:
    payload = {
        "signing_input": 'reddog-workauth.v1.{"work_order_id":"wo-1"}',
        "payload_digest": "sha256:payload",
        "signer_role": "reddog",
        "signer_public_key": public_key,
        "requester_principal_id": "github:mjtrout",
        "nonce": "nonce-1",
        "key_epoch": "epoch-1",
        "requested_operation": "create_foundup",
        "authority_tier": "HIGH",
        "consensus_receipt_digest": "sha256:consensus",
    }
    payload.update(overrides)
    return SigningRequest(**payload)


def _wire_payload(request: SigningRequest) -> bytes:
    return (
        json.dumps(
            {
                "schema_version": SIGNER_SOCKET_REQUEST_SCHEMA_VERSION,
                "request": request.to_dict(),
            },
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def _request_digest(signing_input: str) -> str:
    raw = json.dumps(
        {"signing_input": signing_input},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _control_policy(
    public_key: str, *, authority_profile_digest: str = "sha256:" + "a" * 64
) -> ControlLoopAuthorityPolicy:
    return ControlLoopAuthorityPolicy(
        issuer_principal_id="github:mjtrout",
        signer_public_key=public_key,
        key_epoch="epoch-1",
        consensus_receipt_digest="sha256:" + "c" * 64,
        authority_profile_digest=authority_profile_digest,
        authority_profile_source_receipt_id="sha256:" + "e" * 64,
    )


def _control_result() -> dict[str, object]:
    return {
        "accepted": True,
        "status": "PASS",
        "rounds": 1,
        "serial_progress": 1,
        "claim_progress": 0,
        "receipt_ids": (),
        "rejection_reasons": (),
        "control_lock_acquired": True,
        "dispatched_stages": (),
    }


def _control_signing_context(public_key: str, signer: object) -> ControlLoopReceiptSigningContext:
    return ControlLoopReceiptSigningContext(
        signer=signer,
        signature_verifier=Ed25519SignatureVerifier(),
        issuer_principal_id="github:mjtrout",
        signer_public_key=public_key,
        key_epoch="epoch-1",
        authority_tier="HIGH",
        consensus_receipt_digest="sha256:" + "c" * 64,
        authority_profile_digest="sha256:" + "a" * 64,
        authority_profile_source_receipt_id="sha256:" + "e" * 64,
    )


def _build_control_receipt(public_key: str, signer: object, *, suffix: str):
    return build_resident_control_loop_receipt(
        result=_control_result(),
        repo_root=Path.cwd(),
        created_at="2026-07-18T00:00:00Z",
        cycle_id="cycle-" + suffix,
        nonce="nonce-" + suffix,
        signing_context=_control_signing_context(public_key, signer),
    )


def _control_signing_input(receipt: object) -> str:
    payload = {
        key: value
        for key, value in receipt.to_dict().items()
        if key not in {"signature", "signer_audit_mac", "signer_audit_attestation_signature"}
    }
    return CONTROL_LOOP_SIGNING_PREFIX + json.dumps(
        payload, sort_keys=True, separators=(",", ":")
    )


def test_ed25519_signer_backend_signs_and_public_verifier_accepts() -> None:
    private_key = _private_key()
    public_key = _public_text(private_key)
    request = _request(public_key)
    backend = Ed25519SignerBackend(
        private_key=private_key,
        public_key=public_key,
        key_epoch="epoch-1",
        audit_mac_builder=AuditMacBuilder(),
    )

    response = backend.sign(request, _peer())

    assert response.accepted is True
    assert response.signer_public_key == public_key
    assert response.audit_mac == "audit:nonce-1:github:mjtrout"
    assert response.no_secret_material_returned is True
    assert Ed25519SignatureVerifier().verify(public_key, request.signing_input, response.signature) is True


def test_ed25519_signer_backend_round_trips_through_socket_protocol() -> None:
    private_key = _private_key()
    public_key = _public_text(private_key)
    request = _request(public_key)
    backend = Ed25519SignerBackend(
        private_key=private_key,
        public_key=public_key,
        key_epoch="epoch-1",
        audit_mac_builder=AuditMacBuilder(),
    )

    raw = handle_reddog_isolated_signer_socket_request(
        _wire_payload(request),
        peer=_peer(),
        backend=backend,
    )
    response = json.loads(raw.decode("utf-8"))

    assert response["accepted"] is True
    assert response["audit_mac"] == "audit:nonce-1:github:mjtrout"
    assert Ed25519SignatureVerifier().verify(
        public_key,
        request.signing_input,
        str(response["signature"]),
    ) is True


def test_ed25519_signer_backend_rejects_public_key_or_epoch_mismatch() -> None:
    private_key = _private_key()
    public_key = _public_text(private_key)
    other_public_key = _public_text(_private_key())
    backend = Ed25519SignerBackend(
        private_key=private_key,
        public_key=public_key,
        key_epoch="epoch-1",
        audit_mac_builder=AuditMacBuilder(),
    )

    wrong_key = backend.sign(_request(other_public_key), _peer())
    wrong_epoch = backend.sign(_request(public_key, key_epoch="epoch-2"), _peer())

    assert wrong_key.accepted is False
    assert wrong_key.rejection_code == REJECT_ED25519_SIGNER_PUBLIC_KEY_MISMATCH
    assert wrong_epoch.accepted is False
    assert wrong_epoch.rejection_code == REJECT_ED25519_SIGNER_KEY_EPOCH_MISMATCH


def test_ed25519_signer_backend_rejects_if_key_object_does_not_match_public_key() -> None:
    backend = Ed25519SignerBackend(
        private_key=_private_key(),
        public_key=_public_text(_private_key()),
        key_epoch="epoch-1",
        audit_mac_builder=AuditMacBuilder(),
    )
    response = backend.sign(_request(backend.public_key), _peer())

    assert response.accepted is False
    assert response.rejection_code == REJECT_ED25519_SIGNER_PUBLIC_KEY_MISMATCH


def test_ed25519_signer_backend_requires_audit_mac() -> None:
    private_key = _private_key()
    public_key = _public_text(private_key)
    backend = Ed25519SignerBackend(
        private_key=private_key,
        public_key=public_key,
        key_epoch="epoch-1",
        audit_mac_builder=EmptyAuditMacBuilder(),
    )

    response = backend.sign(_request(public_key), _peer())

    assert response.accepted is False
    assert response.rejection_code == REJECT_ED25519_SIGNER_AUDIT_MAC_MISSING


@pytest.mark.parametrize(
    ("requested_operation", "signing_input"),
    [
        (CONTROL_LOOP_SIGNING_OPERATION, 'reddog-workauth.v1.{"receipt_id":"r-1"}'),
        ("create_foundup", CONTROL_LOOP_SIGNING_PREFIX + '{"receipt_id":"r-1"}'),
    ],
)
def test_ed25519_signer_backend_rejects_control_receipt_domain_confusion(
    requested_operation: str,
    signing_input: str,
) -> None:
    private_key = _private_key()
    public_key = _public_text(private_key)
    backend = Ed25519SignerBackend(
        private_key=private_key,
        public_key=public_key,
        key_epoch="epoch-1",
        audit_mac_builder=AuditMacBuilder(),
    )

    response = backend.sign(
        _request(
            public_key,
            requested_operation=requested_operation,
            signing_input=signing_input,
        ),
        _peer(),
    )

    assert response.accepted is False
    assert response.rejection_code == REJECT_ED25519_SIGNER_DOMAIN_MISMATCH


def test_ed25519_signer_backend_signs_control_receipt_only_in_control_domain() -> None:
    private_key = _private_key()
    public_key = _public_text(private_key)
    backend = Ed25519SignerBackend(
        private_key=private_key,
        public_key=public_key,
        key_epoch="epoch-1",
        audit_mac_builder=AuditMacBuilder(),
        control_loop_anchor_store=InMemorySignerControlLoopAnchorStore(),
        control_loop_authority_policy=_control_policy(public_key),
    )
    class DirectClient:
        def sign(self, request: SigningRequest):
            return backend.sign(request, _peer())

    receipt = _build_control_receipt(public_key, DirectClient(), suffix="1")
    signing_input = _control_signing_input(receipt)

    assert receipt.authentication_status == "AUTHENTICATED"
    assert receipt.signer_audit_attestation_signature
    assert Ed25519SignatureVerifier().verify(
        public_key,
        signing_input,
        receipt.signature,
    ) is True
    assert Ed25519SignatureVerifier().verify(
        public_key,
        canonical_control_audit_attestation_input(
            signing_input=signing_input,
            signature=receipt.signature,
            audit_mac=receipt.signer_audit_mac,
            signer_public_key=public_key,
            key_epoch="epoch-1",
            requester_principal_id="github:mjtrout",
        ),
        receipt.signer_audit_attestation_signature,
    ) is True


def test_control_receipt_signer_requires_exact_signer_owned_authority_policy() -> None:
    private_key = _private_key()
    public_key = _public_text(private_key)
    trusted = Ed25519SignerBackend(
        private_key=private_key,
        public_key=public_key,
        key_epoch="epoch-1",
        audit_mac_builder=AuditMacBuilder(),
        control_loop_anchor_store=InMemorySignerControlLoopAnchorStore(),
        control_loop_authority_policy=_control_policy(public_key),
    )
    captured: list[SigningRequest] = []

    class CapturingClient:
        def sign(self, request: SigningRequest):
            captured.append(request)
            return trusted.sign(request, _peer())

    _build_control_receipt(public_key, CapturingClient(), suffix="policy")

    missing_policy = Ed25519SignerBackend(
        private_key=private_key,
        public_key=public_key,
        key_epoch="epoch-1",
        audit_mac_builder=AuditMacBuilder(),
        control_loop_anchor_store=InMemorySignerControlLoopAnchorStore(),
    ).sign(captured[0], _peer())
    mismatched_policy = Ed25519SignerBackend(
        private_key=private_key,
        public_key=public_key,
        key_epoch="epoch-1",
        audit_mac_builder=AuditMacBuilder(),
        control_loop_anchor_store=InMemorySignerControlLoopAnchorStore(),
        control_loop_authority_policy=replace(
            _control_policy(public_key),
            authority_profile_source_receipt_id="sha256:" + "f" * 64,
        ),
    ).sign(captured[0], _peer())
    missing_anchor = Ed25519SignerBackend(
        private_key=private_key,
        public_key=public_key,
        key_epoch="epoch-1",
        audit_mac_builder=AuditMacBuilder(),
        control_loop_authority_policy=_control_policy(public_key),
    ).sign(captured[0], _peer())

    assert missing_policy.rejection_code == (
        REJECT_ED25519_SIGNER_CONTROL_AUTHORITY_POLICY_MISSING
    )
    assert mismatched_policy.rejection_code == (
        REJECT_ED25519_SIGNER_CONTROL_AUTHORITY_POLICY_MISMATCH
    )
    assert missing_anchor.rejection_code == REJECT_ED25519_SIGNER_CONTROL_ANCHOR_MISSING


@pytest.mark.parametrize(
    ("authority_tier", "profile_digest"),
    [
        ("LOW", "sha256:" + "a" * 64),
        ("HIGH", "not-a-digest"),
    ],
)
def test_control_receipt_signer_rejects_invalid_tier_or_profile_digest(
    authority_tier: str, profile_digest: str
) -> None:
    private_key = _private_key()
    public_key = _public_text(private_key)
    backend = Ed25519SignerBackend(
        private_key=private_key,
        public_key=public_key,
        key_epoch="epoch-1",
        audit_mac_builder=AuditMacBuilder(),
        control_loop_anchor_store=InMemorySignerControlLoopAnchorStore(),
        control_loop_authority_policy=_control_policy(
            public_key, authority_profile_digest=profile_digest
        ),
    )

    class DirectClient:
        def sign(self, request: SigningRequest):
            return backend.sign(request, _peer())

    from modules.communication.moltbot_bridge.src.reddog_resident_control_loop_receipt_store import (
        ControlLoopReceiptSigningContext,
        build_resident_control_loop_receipt,
    )

    with pytest.raises(ValueError, match="signing_rejected"):
        build_resident_control_loop_receipt(
            result={
                "accepted": True,
                "status": "PASS",
                "rounds": 1,
                "serial_progress": 1,
                "claim_progress": 0,
                "receipt_ids": (),
                "rejection_reasons": (),
                "control_lock_acquired": True,
                "dispatched_stages": (),
            },
            repo_root=Path.cwd(),
            created_at="2026-07-18T00:00:00Z",
            signing_context=ControlLoopReceiptSigningContext(
                signer=DirectClient(),
                signature_verifier=Ed25519SignatureVerifier(),
                issuer_principal_id="github:mjtrout",
                signer_public_key=public_key,
                key_epoch="epoch-1",
                authority_tier=authority_tier,
                consensus_receipt_digest="sha256:" + "c" * 64,
                authority_profile_digest=profile_digest,
                authority_profile_source_receipt_id="sha256:" + "e" * 64,
            ),
        )


def test_control_receipt_signer_rejects_wrong_signer_role() -> None:
    private_key = _private_key()
    public_key = _public_text(private_key)
    backend = Ed25519SignerBackend(
        private_key=private_key,
        public_key=public_key,
        key_epoch="epoch-1",
        audit_mac_builder=AuditMacBuilder(),
        control_loop_anchor_store=InMemorySignerControlLoopAnchorStore(),
        control_loop_authority_policy=_control_policy(public_key),
    )
    captured: list[SigningRequest] = []

    class CapturingClient:
        def sign(self, request: SigningRequest):
            captured.append(request)
            return backend.sign(request, _peer())

    from modules.communication.moltbot_bridge.src.reddog_resident_control_loop_receipt_store import (
        ControlLoopReceiptSigningContext,
        build_resident_control_loop_receipt,
    )

    build_resident_control_loop_receipt(
        result={
            "accepted": True,
            "status": "PASS",
            "rounds": 1,
            "serial_progress": 1,
            "claim_progress": 0,
            "receipt_ids": (),
            "rejection_reasons": (),
            "control_lock_acquired": True,
            "dispatched_stages": (),
        },
        repo_root=Path.cwd(),
        created_at="2026-07-18T00:00:00Z",
        signing_context=ControlLoopReceiptSigningContext(
            signer=CapturingClient(),
            signature_verifier=Ed25519SignatureVerifier(),
            issuer_principal_id="github:mjtrout",
            signer_public_key=public_key,
            key_epoch="epoch-1",
            authority_tier="HIGH",
            consensus_receipt_digest="sha256:" + "c" * 64,
            authority_profile_digest="sha256:" + "a" * 64,
            authority_profile_source_receipt_id="sha256:" + "e" * 64,
        ),
    )
    rejected = backend.sign(replace(captured[0], signer_role="reddog"), _peer())
    assert rejected.accepted is False


def test_ed25519_signer_backend_rejects_malformed_control_receipt_payload() -> None:
    private_key = _private_key()
    public_key = _public_text(private_key)
    backend = Ed25519SignerBackend(
        private_key=private_key,
        public_key=public_key,
        key_epoch="epoch-1",
        audit_mac_builder=AuditMacBuilder(),
    )
    signing_input = CONTROL_LOOP_SIGNING_PREFIX + '{"receipt_id":"forged"}'

    response = backend.sign(
        _request(
            public_key,
            requested_operation=CONTROL_LOOP_SIGNING_OPERATION,
            signing_input=signing_input,
            payload_digest=_request_digest(signing_input),
        ),
        _peer(),
    )

    assert response.accepted is False


def test_signer_backend_module_has_no_key_loading_repo_shell_or_socket_surfaces() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    banned_import_roots = {
        "subprocess",
        "socket",
        "os",
        "requests",
        "urllib",
        "http",
        "holo_index",
        "git",
        "secrets",
    }
    banned_calls = {
        "eval",
        "exec",
        "compile",
        "__import__",
        "generate",
        "from_private_bytes",
    }
    banned_attrs = {
        "system",
        "popen",
        "spawn",
        "run",
        "Popen",
        "check_call",
        "check_output",
        "getenv",
        "environ",
        "private_bytes",
        "read_text",
        "read_bytes",
        "write_text",
        "write_bytes",
    }

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".", 1)[0] not in banned_import_roots
        if isinstance(node, ast.ImportFrom) and node.module:
            assert node.module.split(".", 1)[0] not in banned_import_roots
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                assert node.func.id not in banned_calls
            if isinstance(node.func, ast.Attribute):
                assert node.func.attr not in banned_attrs
