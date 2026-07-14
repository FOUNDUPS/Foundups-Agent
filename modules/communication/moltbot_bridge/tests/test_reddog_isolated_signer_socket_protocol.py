"""Tests for REDDOG_ISOLATED_SIGNER_SOCKET_PROTOCOL_PHASE1."""

from __future__ import annotations

import ast
import json
from pathlib import Path

from modules.communication.moltbot_bridge.src.reddog_isolated_signer_socket_protocol import (
    REJECT_SIGNER_SOCKET_BACKEND_EXCEPTION,
    REJECT_SIGNER_SOCKET_NON_ASCII,
    REJECT_SIGNER_SOCKET_PEER_MISMATCH,
    REJECT_SIGNER_SOCKET_PEER_NOT_ATTESTED,
    REJECT_SIGNER_SOCKET_REQUEST_INVALID,
    REJECT_SIGNER_SOCKET_REQUEST_TOO_LARGE,
    REJECT_SIGNER_SOCKET_RESPONSE_INVALID,
    REJECT_SIGNER_SOCKET_SCHEMA_INVALID,
    SIGNER_SOCKET_REQUEST_SCHEMA_VERSION,
    SignerPeerAttestation,
    handle_reddog_isolated_signer_socket_request,
)
from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    RuntimeRejectCode,
    SigningRequest,
    SigningResponse,
    public_key_fingerprint,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "reddog_isolated_signer_socket_protocol.py"
)


class AcceptingBackend:
    def __init__(self) -> None:
        self.requests: list[tuple[SigningRequest, SignerPeerAttestation]] = []

    def sign(self, request: SigningRequest, peer: SignerPeerAttestation) -> SigningResponse:
        self.requests.append((request, peer))
        return SigningResponse(
            accepted=True,
            signature="sig:" + request.nonce,
            signer_public_key=request.signer_public_key,
            key_fingerprint=public_key_fingerprint(request.signer_public_key),
            key_epoch=request.key_epoch,
            audit_mac="audit:" + request.payload_digest,
            boundary_attested=True,
            requester_identity_attested=True,
            signer_loads_no_untrusted_code=True,
            no_secret_material_returned=True,
        )


class RaisingBackend:
    def sign(self, request: SigningRequest, peer: SignerPeerAttestation) -> SigningResponse:
        raise RuntimeError("boom")


class InvalidBackend:
    def sign(self, request: SigningRequest, peer: SignerPeerAttestation) -> SigningResponse:
        return SigningResponse(
            accepted=True,
            signature="sig",
            signer_public_key=request.signer_public_key,
            key_fingerprint=public_key_fingerprint(request.signer_public_key),
            key_epoch=request.key_epoch,
            audit_mac="audit",
            boundary_attested=True,
            requester_identity_attested=True,
            signer_loads_no_untrusted_code=True,
            no_secret_material_returned=False,
        )


def _peer(**overrides: object) -> SignerPeerAttestation:
    payload = {
        "peer_principal_id": "github:mjtrout",
        "transport": "unix_socket",
        "credential_source": "kernel_peer_credential",
        "boundary_attested": True,
    }
    payload.update(overrides)
    return SignerPeerAttestation(**payload)


def _request_payload(**overrides: object) -> bytes:
    request = {
        "signing_input": "reddog-workauth.v1.{}",
        "payload_digest": "sha256:payload",
        "signer_role": "reddog",
        "signer_public_key": "pub:reddog",
        "requester_principal_id": "github:mjtrout",
        "nonce": "workauth-nonce-0001",
        "key_epoch": "epoch-1",
        "requested_operation": "create_foundup",
        "authority_tier": "HIGH",
        "consensus_receipt_digest": "sha256:consensus",
    }
    request.update(overrides)
    payload = {
        "schema_version": SIGNER_SOCKET_REQUEST_SCHEMA_VERSION,
        "request": request,
    }
    return (json.dumps(payload, sort_keys=True) + "\n").encode("utf-8")


def _decode(response: bytes) -> dict[str, object]:
    decoded = json.loads(response.decode("utf-8"))
    assert isinstance(decoded, dict)
    return decoded


def test_protocol_accepts_attested_peer_and_backend_response() -> None:
    backend = AcceptingBackend()

    response = _decode(
        handle_reddog_isolated_signer_socket_request(
            _request_payload(),
            peer=_peer(),
            backend=backend,
        )
    )

    assert response["accepted"] is True
    assert response["signature"] == "sig:workauth-nonce-0001"
    assert response["signer_public_key"] == "pub:reddog"
    assert response["no_secret_material_returned"] is True
    assert len(backend.requests) == 1
    assert backend.requests[0][1].peer_principal_id == "github:mjtrout"


def test_protocol_default_backend_fails_closed() -> None:
    response = _decode(
        handle_reddog_isolated_signer_socket_request(
            _request_payload(),
            peer=_peer(),
        )
    )

    assert response["accepted"] is False
    assert response["rejection_code"] == RuntimeRejectCode.SIGNER_NOT_CONFIGURED


def test_protocol_rejects_malformed_schema_and_oversized_request() -> None:
    malformed = _decode(
        handle_reddog_isolated_signer_socket_request(b"{", peer=_peer(), backend=AcceptingBackend())
    )
    wrong_schema = _decode(
        handle_reddog_isolated_signer_socket_request(
            json.dumps({"schema_version": "wrong", "request": {}}).encode("utf-8"),
            peer=_peer(),
            backend=AcceptingBackend(),
        )
    )
    too_large = _decode(
        handle_reddog_isolated_signer_socket_request(
            b"x" * 20,
            peer=_peer(),
            backend=AcceptingBackend(),
            max_request_bytes=8,
        )
    )

    assert malformed["rejection_code"] == REJECT_SIGNER_SOCKET_REQUEST_INVALID
    assert wrong_schema["rejection_code"] == REJECT_SIGNER_SOCKET_SCHEMA_INVALID
    assert too_large["rejection_code"] == REJECT_SIGNER_SOCKET_REQUEST_TOO_LARGE


def test_protocol_rejects_peer_spoofing_before_backend() -> None:
    backend = AcceptingBackend()

    response = _decode(
        handle_reddog_isolated_signer_socket_request(
            _request_payload(requester_principal_id="github:attacker"),
            peer=_peer(peer_principal_id="github:mjtrout"),
            backend=backend,
        )
    )

    assert response["accepted"] is False
    assert response["rejection_code"] == REJECT_SIGNER_SOCKET_PEER_MISMATCH
    assert backend.requests == []


def test_protocol_requires_peer_boundary_attestation() -> None:
    response = _decode(
        handle_reddog_isolated_signer_socket_request(
            _request_payload(),
            peer=_peer(boundary_attested=False),
            backend=AcceptingBackend(),
        )
    )

    assert response["accepted"] is False
    assert response["rejection_code"] == REJECT_SIGNER_SOCKET_PEER_NOT_ATTESTED


def test_protocol_rejects_non_ascii_request_or_peer() -> None:
    bad_request = _decode(
        handle_reddog_isolated_signer_socket_request(
            _request_payload(nonce="nonce-\u2603"),
            peer=_peer(),
            backend=AcceptingBackend(),
        )
    )
    bad_peer = _decode(
        handle_reddog_isolated_signer_socket_request(
            _request_payload(),
            peer=_peer(peer_principal_id="github:\u2603"),
            backend=AcceptingBackend(),
        )
    )

    assert bad_request["rejection_code"] == REJECT_SIGNER_SOCKET_NON_ASCII
    assert bad_peer["rejection_code"] == REJECT_SIGNER_SOCKET_NON_ASCII


def test_protocol_rejects_backend_exception_or_invalid_accepted_response() -> None:
    failed = _decode(
        handle_reddog_isolated_signer_socket_request(
            _request_payload(),
            peer=_peer(),
            backend=RaisingBackend(),
        )
    )
    invalid = _decode(
        handle_reddog_isolated_signer_socket_request(
            _request_payload(),
            peer=_peer(),
            backend=InvalidBackend(),
        )
    )

    assert failed["rejection_code"] == REJECT_SIGNER_SOCKET_BACKEND_EXCEPTION
    assert invalid["rejection_code"] == REJECT_SIGNER_SOCKET_RESPONSE_INVALID


def test_protocol_has_no_socket_subprocess_env_holoindex_or_private_key_imports() -> None:
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
        "hmac",
        "cryptography",
    }
    banned_calls = {"eval", "exec", "compile", "__import__"}
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
        "open",
        "unlink",
        "remove",
        "replace",
        "rename",
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
