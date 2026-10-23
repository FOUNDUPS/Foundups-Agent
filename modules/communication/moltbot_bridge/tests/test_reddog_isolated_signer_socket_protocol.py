"""Tests for REDDOG_ISOLATED_SIGNER_SOCKET_PROTOCOL_PHASE1."""

from __future__ import annotations

import ast
import json
import struct
from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.src import (
    reddog_signer_socket_peer_credential_attestor as attestor_module,
)
from modules.communication.moltbot_bridge.src.reddog_isolated_signer_socket_protocol import (
    REJECT_SIGNER_SOCKET_BACKEND_EXCEPTION,
    REJECT_SIGNER_SOCKET_NON_ASCII,
    REJECT_SIGNER_SOCKET_PEER_MISMATCH,
    REJECT_SIGNER_SOCKET_PEER_NOT_ATTESTED,
    REJECT_SIGNER_SOCKET_REQUEST_INVALID,
    REJECT_SIGNER_SOCKET_REQUEST_TOO_LARGE,
    REJECT_SIGNER_SOCKET_RESPONSE_INVALID,
    REJECT_SIGNER_SOCKET_SCHEMA_INVALID,
    REJECT_SIGNER_SOCKET_SECRET_GRANT_UNSUPPORTED,
    SIGNER_SOCKET_REQUEST_SCHEMA_VERSION,
    SIGNER_SOCKET_REQUEST_SCHEMA_VERSION_V2,
    SignerPeerAttestation,
    handle_reddog_isolated_signer_socket_request,
)
from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    RuntimeRejectCode,
    SigningRequest,
    SigningResponse,
    public_key_fingerprint,
)
from modules.communication.moltbot_bridge.src.reddog_signer_socket_peer_credential_attestor import (
    KernelPeerCredentialAttestor,
    PeerCredentialPolicy,
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


class SecretRejectingBackend:
    def sign(self, request: SigningRequest, peer: SignerPeerAttestation) -> SigningResponse:
        return SigningResponse(
            accepted=False,
            signature="secret-value",
            audit_mac="secret-audit-key",
            rejection_code="REJECTED",
            no_secret_material_returned=True,
        )


class CodeSecretRejectingBackend:
    def sign(self, request: SigningRequest, peer: SignerPeerAttestation) -> SigningResponse:
        return SigningResponse(
            accepted=False,
            rejection_code="API_SECRET_ABC123",
            no_secret_material_returned=True,
        )


class SmugglingResponse(SigningResponse):
    def to_dict(self):
        return {
            **super().to_dict(),
            "exfiltrated_secret": "SECRET_MUST_NOT_ESCAPE",
        }


class SmugglingRejectingBackend:
    def sign(self, request: SigningRequest, peer: SignerPeerAttestation) -> SigningResponse:
        return SmugglingResponse(
            accepted=False,
            rejection_code=RuntimeRejectCode.SIGNER_NOT_CONFIGURED,
        )


class DeceptiveRejectionCode(str):
    def __hash__(self) -> int:
        return hash(RuntimeRejectCode.SIGNER_NOT_CONFIGURED)

    def __eq__(self, other: object) -> bool:
        return other == RuntimeRejectCode.SIGNER_NOT_CONFIGURED


class DeceptiveCodeRejectingBackend:
    def sign(self, request: SigningRequest, peer: SignerPeerAttestation) -> SigningResponse:
        return SigningResponse(
            accepted=False,
            rejection_code=DeceptiveRejectionCode("SECRET_MUST_NOT_ESCAPE"),
        )


class EncodeSpoof(str):
    def encode(self, *args, **kwargs):
        return b"github:mjtrout"


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


def test_protocol_accepts_real_kernel_source_and_rejects_forged_variants() -> None:
    real = (
        "kernel_peer_credential:kernel_so_peercred:"
        "pid=101:uid=1001:gid=1002"
    )
    accepted = _decode(
        handle_reddog_isolated_signer_socket_request(
            _request_payload(), peer=_peer(credential_source=real),
            backend=AcceptingBackend(),
        )
    )
    assert accepted["accepted"] is True

    for forged in (
        real + ":role=architect",
        real.replace("uid=1001", "uid=-1"),
        real.replace("kernel_so_peercred", "request_body"),
        "kernel_peer_credential:kernel_so_peercred:uid=1001:gid=1002",
    ):
        rejected = _decode(
            handle_reddog_isolated_signer_socket_request(
                _request_payload(), peer=_peer(credential_source=forged),
                backend=AcceptingBackend(),
            )
        )
        assert rejected["rejection_code"] == REJECT_SIGNER_SOCKET_PEER_NOT_ATTESTED


def test_kernel_peer_attestor_output_is_protocol_admissible(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Socket:
        def getsockopt(self, _level: int, _name: int, _length: int) -> bytes:
            return struct.pack("3i", 101, 1001, 1002)

    monkeypatch.setattr(attestor_module, "_SO_PEERCRED", 17)
    peer = KernelPeerCredentialAttestor(
        PeerCredentialPolicy(
            uid_to_principal={1001: "github:mjtrout"},
            allowed_gids=(1002,),
        )
    ).attest(Socket())

    response = _decode(
        handle_reddog_isolated_signer_socket_request(
            _request_payload(), peer=peer, backend=AcceptingBackend()
        )
    )
    assert response["accepted"] is True


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


def test_protocol_v2_requires_grant_aware_backend_and_exact_grant_shape() -> None:
    payload = json.loads(_request_payload())
    payload["schema_version"] = SIGNER_SOCKET_REQUEST_SCHEMA_VERSION_V2
    missing = _decode(
        handle_reddog_isolated_signer_socket_request(
            json.dumps(payload).encode("utf-8"), peer=_peer(), backend=AcceptingBackend()
        )
    )
    payload["secret_access_grant"] = {"schema_version": "grant-fixture"}
    unsupported = _decode(
        handle_reddog_isolated_signer_socket_request(
            json.dumps(payload).encode("utf-8"), peer=_peer(), backend=AcceptingBackend()
        )
    )

    assert missing["rejection_code"] == REJECT_SIGNER_SOCKET_REQUEST_INVALID
    assert unsupported["rejection_code"] == REJECT_SIGNER_SOCKET_SECRET_GRANT_UNSUPPORTED


def test_protocol_v1_rejects_smuggled_secret_grant() -> None:
    payload = json.loads(_request_payload())
    payload["secret_access_grant"] = {"schema_version": "grant-fixture"}

    response = _decode(
        handle_reddog_isolated_signer_socket_request(
            json.dumps(payload).encode("utf-8"), peer=_peer(), backend=AcceptingBackend()
        )
    )

    assert response["rejection_code"] == REJECT_SIGNER_SOCKET_REQUEST_INVALID


def test_protocol_v1_rejects_elevated_consensus_downgrade() -> None:
    payload = json.loads(
        _request_payload(elevated_consensus_proof={"schema_version": "proof"})
    )

    response = _decode(handle_reddog_isolated_signer_socket_request(
        json.dumps(payload).encode("utf-8"), peer=_peer(), backend=AcceptingBackend()
    ))

    assert response["rejection_code"] == REJECT_SIGNER_SOCKET_REQUEST_INVALID


def test_protocol_v2_accepts_proved_grant_authority_without_target_grant() -> None:
    payload = json.loads(_request_payload(
        requested_operation="issue_signer_secret_access_grant",
        elevated_consensus_proof={"schema_version": "proof"},
    ))
    payload["schema_version"] = SIGNER_SOCKET_REQUEST_SCHEMA_VERSION_V2
    payload["secret_access_grant"] = None
    backend = AcceptingBackend()

    response = _decode(handle_reddog_isolated_signer_socket_request(
        json.dumps(payload).encode("utf-8"), peer=_peer(), backend=backend
    ))

    assert response["accepted"] is True
    assert len(backend.requests) == 1


def test_protocol_v2_rejects_duplicate_unknown_or_coerced_fields() -> None:
    base = json.loads(_request_payload())
    base["schema_version"] = SIGNER_SOCKET_REQUEST_SCHEMA_VERSION_V2
    base["secret_access_grant"] = {"schema_version": "grant-fixture"}
    unknown = dict(base)
    unknown["unexpected"] = "smuggled"
    coerced = json.loads(json.dumps(base))
    coerced["request"]["nonce"] = 7
    duplicate = json.dumps(base).replace(
        '"schema_version": "reddog_signer_socket_request.v2"',
        '"schema_version": "reddog_signer_socket_request.v2", '
        '"schema_version": "reddog_signer_socket_request.v1"',
        1,
    )

    for payload in (json.dumps(unknown), json.dumps(coerced), duplicate):
        response = _decode(handle_reddog_isolated_signer_socket_request(
            payload.encode("utf-8"), peer=_peer(), backend=AcceptingBackend()
        ))
        assert response["rejection_code"] == REJECT_SIGNER_SOCKET_REQUEST_INVALID


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


def test_protocol_rejects_secret_bearing_backend_rejection() -> None:
    response = _decode(
        handle_reddog_isolated_signer_socket_request(
            _request_payload(),
            peer=_peer(),
            backend=SecretRejectingBackend(),
        )
    )

    assert response["rejection_code"] == REJECT_SIGNER_SOCKET_RESPONSE_INVALID
    serialized = json.dumps(response)
    assert "secret-value" not in serialized
    assert "secret-audit-key" not in serialized

    code_response = _decode(
        handle_reddog_isolated_signer_socket_request(
            _request_payload(),
            peer=_peer(),
            backend=CodeSecretRejectingBackend(),
        )
    )
    assert code_response["rejection_code"] == REJECT_SIGNER_SOCKET_RESPONSE_INVALID
    assert "API_SECRET_ABC123" not in json.dumps(code_response)

    subclass_response = _decode(
        handle_reddog_isolated_signer_socket_request(
            _request_payload(),
            peer=_peer(),
            backend=SmugglingRejectingBackend(),
        )
    )
    assert subclass_response["rejection_code"] == REJECT_SIGNER_SOCKET_RESPONSE_INVALID
    assert "exfiltrated_secret" not in subclass_response
    assert "SECRET_MUST_NOT_ESCAPE" not in json.dumps(subclass_response)

    deceptive_response = _decode(
        handle_reddog_isolated_signer_socket_request(
            _request_payload(),
            peer=_peer(),
            backend=DeceptiveCodeRejectingBackend(),
        )
    )
    assert deceptive_response["rejection_code"] == REJECT_SIGNER_SOCKET_RESPONSE_INVALID
    assert "SECRET_MUST_NOT_ESCAPE" not in json.dumps(deceptive_response)


def test_protocol_rejects_peer_identity_string_subclass_before_backend() -> None:
    backend = AcceptingBackend()
    response = _decode(
        handle_reddog_isolated_signer_socket_request(
            _request_payload(),
            peer=_peer(peer_principal_id=EncodeSpoof("attacker")),
            backend=backend,
        )
    )

    assert response["rejection_code"] == REJECT_SIGNER_SOCKET_PEER_NOT_ATTESTED
    assert backend.requests == []


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
