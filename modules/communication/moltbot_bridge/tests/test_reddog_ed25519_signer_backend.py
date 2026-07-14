"""Tests for REDDOG_ED25519_SIGNER_BACKEND_PHASE1."""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.src.reddog_ed25519_signature_verifier_backend import (
    Ed25519SignatureVerifier,
    encode_ed25519_public_key,
)
from modules.communication.moltbot_bridge.src.reddog_ed25519_signer_backend import (
    Ed25519SignerBackend,
    REJECT_ED25519_SIGNER_AUDIT_MAC_MISSING,
    REJECT_ED25519_SIGNER_KEY_EPOCH_MISMATCH,
    REJECT_ED25519_SIGNER_PUBLIC_KEY_MISMATCH,
)
from modules.communication.moltbot_bridge.src.reddog_isolated_signer_socket_protocol import (
    SIGNER_SOCKET_REQUEST_SCHEMA_VERSION,
    SignerPeerAttestation,
    handle_reddog_isolated_signer_socket_request,
)
from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    SigningRequest,
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
