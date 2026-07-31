"""Adversarial tests for the RedDog signer mutual peer handshake."""

from __future__ import annotations

import ast
import socket
import threading
from dataclasses import replace
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from modules.communication.moltbot_bridge.src.reddog_ed25519_signature_verifier_backend import (
    encode_ed25519_public_key,
)
from modules.communication.moltbot_bridge.src.reddog_ed25519_signer_backend import (
    Ed25519SignerBackend,
    REJECT_ED25519_SIGNER_REQUEST_INVALID,
)
from modules.communication.moltbot_bridge.src.reddog_isolated_signer_socket_protocol import (
    SignerPeerAttestation,
)
from modules.communication.moltbot_bridge.src.reddog_isolated_signer_socket_client import (
    build_reddog_isolated_signer_socket_client,
)
from modules.communication.moltbot_bridge.src.reddog_isolated_signer_socket_resident_service import (
    serve_reddog_isolated_signer_socket_bounded,
)
from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    SigningRequest,
    SigningResponse,
    public_key_fingerprint,
)
from modules.communication.moltbot_bridge.src.reddog_signer_mutual_peer_handshake import (
    FAIL_HANDSHAKE_REQUEST_INVALID,
    FAIL_HANDSHAKE_SIGNATURE_INVALID,
    FAIL_HANDSHAKE_SIGNER_BINDING,
    SignerPeerInstanceBinding,
    SignerPeerProfileBinding,
    build_signer_peer_handshake_request,
    validate_signer_peer_handshake_request,
    verify_signer_peer_handshake_response,
)


NOW = 2_000_000_000
CHALLENGE = "a" * 64
WSP62_SLICE_FILES = (
    "src/reddog_external_signer_lifecycle_admission.py",
    "src/reddog_external_signer_os_observer.py",
    "src/reddog_isolated_signer_socket_resident_service.py",
    "src/reddog_runtime_artifact_manifest_launch_selection.py",
    "src/reddog_signer_mutual_peer_handshake.py",
    "src/reddog_signer_peer_instance_packet_validator.py",
    "src/reddog_signer_runtime_generation_anchor.py",
    "src/reddog_signer_socket_service_healthcheck.py",
    "tests/test_reddog_external_signer_lifecycle_admission.py",
    "tests/test_reddog_external_signer_os_observer.py",
    "tests/test_reddog_isolated_signer_socket_resident_service.py",
    "tests/test_reddog_signer_mutual_peer_handshake.py",
    "tests/test_reddog_signer_runtime_generation_anchor.py",
    "tests/test_reddog_signer_socket_service_healthcheck.py",
)


class _AuditMac:
    def build(
        self,
        request: SigningRequest,
        signature: str,
        peer: SignerPeerAttestation,
    ) -> str:
        return "audit:" + request.nonce + ":" + peer.peer_principal_id


def _private_key() -> Ed25519PrivateKey:
    return Ed25519PrivateKey.from_private_bytes(bytes(range(32)))


def _public_key(private_key: Ed25519PrivateKey) -> str:
    return encode_ed25519_public_key(
        private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
    )


def _binding() -> SignerPeerInstanceBinding:
    return SignerPeerInstanceBinding(
        run_packet_id="sha256:" + "1" * 64,
        config_digest="sha256:" + "2" * 64,
        session_id="session-1",
        socket_path=str(Path("C:/runtime/reddog.sock").resolve()),
        signer_profiles=(
            SignerPeerProfileBinding(
                signer_profile_id="reddog-work-authority",
                signer_public_key=_public_key(_private_key()),
                key_epoch="epoch-1",
            ),
        ),
        manifest_id="sha256:" + "3" * 64,
        artifact_generation_digest="sha256:" + "4" * 64,
    )


def _request(
    private_key: Ed25519PrivateKey,
    **overrides: object,
) -> SigningRequest:
    binding = _binding()
    values = {
        "run_packet_id": binding.run_packet_id,
        "manifest_id": binding.manifest_id,
        "artifact_generation_digest": binding.artifact_generation_digest,
        "config_digest": binding.config_digest,
        "session_id": binding.session_id,
        "socket_path": binding.socket_path,
        "signer_profile_id": "reddog-work-authority",
        "signer_public_key": _public_key(private_key),
        "key_epoch": "epoch-1",
        "requester_principal_id": "github:mjtrout",
        "now_epoch": NOW,
        "challenge_factory": lambda: CHALLENGE,
    }
    values.update(overrides)
    return build_signer_peer_handshake_request(**values)


def _peer() -> SignerPeerAttestation:
    return SignerPeerAttestation(
        peer_principal_id="github:mjtrout",
        transport="unix_socket",
        credential_source="kernel_peer_credential",
        boundary_attested=True,
    )


def _backend(private_key: Ed25519PrivateKey) -> Ed25519SignerBackend:
    return Ed25519SignerBackend(
        private_key=private_key,
        public_key=_public_key(private_key),
        key_epoch="epoch-1",
        audit_mac_builder=_AuditMac(),
        proposal_clock=lambda: NOW,
        signer_peer_instance_binding=_binding(),
    )


def test_fresh_bound_handshake_proves_signer_key_possession() -> None:
    private_key = _private_key()
    request = _request(private_key)
    response = _backend(private_key).sign(request, _peer())

    result = verify_signer_peer_handshake_response(
        request,
        response,
        now_epoch=NOW,
    )

    assert response.accepted is True
    assert result.accepted is True
    assert result.run_packet_id == _binding().run_packet_id
    assert result.challenge_digest.startswith("sha256:")
    assert result.no_signature_value_returned is True
    assert response.signature not in str(result.to_dict())


def test_backend_rejects_handshake_not_matching_signer_owned_instance() -> None:
    private_key = _private_key()
    request = _request(private_key, session_id="attacker-session")

    response = _backend(private_key).sign(request, _peer())

    assert response.accepted is False
    assert response.rejection_code == REJECT_ED25519_SIGNER_REQUEST_INVALID


@pytest.mark.parametrize(
    "changes",
    [
        {"manifest_id": "sha256:" + "5" * 64},
        {"artifact_generation_digest": "sha256:" + "6" * 64},
    ],
)
def test_manifest_generation_substitution_is_rejected(
    changes: dict[str, object],
) -> None:
    private_key = _private_key()
    response = _backend(private_key).sign(
        _request(private_key, **changes), _peer()
    )

    assert response.accepted is False
    assert response.rejection_code == REJECT_ED25519_SIGNER_REQUEST_INVALID


@pytest.mark.parametrize(
    "field",
    ["manifest_id", "artifact_generation_digest"],
)
def test_all_zero_manifest_bindings_cannot_build_a_request(field: str) -> None:
    with pytest.raises(ValueError, match=FAIL_HANDSHAKE_REQUEST_INVALID):
        _request(_private_key(), **{field: "sha256:" + "0" * 64})


def test_fabricated_acceptance_flags_and_key_text_do_not_authenticate() -> None:
    private_key = _private_key()
    request = _request(private_key)
    response = SigningResponse(
        accepted=True,
        signature="forged",
        signer_public_key=request.signer_public_key,
        key_fingerprint=public_key_fingerprint(request.signer_public_key),
        key_epoch=request.key_epoch,
        audit_mac="attacker-controlled",
        audit_attestation_signature="forged",
        boundary_attested=True,
        requester_identity_attested=True,
        signer_loads_no_untrusted_code=True,
        no_secret_material_returned=True,
    )

    result = verify_signer_peer_handshake_response(
        request,
        response,
        now_epoch=NOW,
    )

    assert result.accepted is False
    assert FAIL_HANDSHAKE_SIGNATURE_INVALID in result.rejection_reasons


def test_old_response_cannot_satisfy_a_new_challenge() -> None:
    private_key = _private_key()
    old_request = _request(private_key)
    old_response = _backend(private_key).sign(old_request, _peer())
    new_request = _request(
        private_key,
        challenge_factory=lambda: "b" * 64,
    )

    result = verify_signer_peer_handshake_response(
        new_request,
        old_response,
        now_epoch=NOW,
    )

    assert result.accepted is False
    assert FAIL_HANDSHAKE_SIGNATURE_INVALID in result.rejection_reasons


def test_expired_future_and_malformed_requests_fail_closed() -> None:
    private_key = _private_key()
    request = _request(private_key)
    expired = validate_signer_peer_handshake_request(
        request,
        now_epoch=NOW + 31,
        expected_binding=_binding(),
    )
    future = validate_signer_peer_handshake_request(
        request,
        now_epoch=NOW - 6,
        expected_binding=_binding(),
    )
    malformed = replace(request, nonce="signer-peer-handshake:" + "c" * 64)

    assert expired is None
    assert future is None
    assert validate_signer_peer_handshake_request(
        malformed,
        now_epoch=NOW,
        expected_binding=_binding(),
    ) is None
    result = verify_signer_peer_handshake_response(
        malformed,
        SigningResponse(accepted=False),
        now_epoch=NOW,
    )
    assert FAIL_HANDSHAKE_REQUEST_INVALID in result.rejection_reasons


def test_wrong_key_epoch_fingerprint_or_boundary_flags_fail_closed() -> None:
    private_key = _private_key()
    request = _request(private_key)
    response = _backend(private_key).sign(request, _peer())

    variants = (
        replace(response, key_epoch="epoch-2"),
        replace(response, key_fingerprint="sha256:" + "0" * 64),
        replace(response, boundary_attested=False),
        replace(response, requester_identity_attested=False),
        replace(response, signer_loads_no_untrusted_code=False),
    )

    for variant in variants:
        result = verify_signer_peer_handshake_response(
            request,
            variant,
            now_epoch=NOW,
        )
        assert result.accepted is False
        assert FAIL_HANDSHAKE_SIGNER_BINDING in result.rejection_reasons


def test_response_audit_metadata_is_covered_by_attestation_signature() -> None:
    private_key = _private_key()
    request = _request(private_key)
    response = _backend(private_key).sign(request, _peer())

    result = verify_signer_peer_handshake_response(
        request,
        replace(response, audit_mac="attacker-selected"),
        now_epoch=NOW,
    )

    assert result.accepted is False
    assert FAIL_HANDSHAKE_SIGNATURE_INVALID in result.rejection_reasons


def test_profile_claim_must_match_exact_key_and_epoch_tuple() -> None:
    private_key = _private_key()
    other_key = Ed25519PrivateKey.from_private_bytes(bytes(range(1, 33)))
    binding = replace(
        _binding(),
        signer_profiles=(
            _binding().signer_profiles[0],
            SignerPeerProfileBinding(
                signer_profile_id="profile-b",
                signer_public_key=_public_key(other_key),
                key_epoch="epoch-2",
            ),
        ),
    )
    backend = replace(
        _backend(private_key),
        signer_peer_instance_binding=binding,
    )
    request = _request(private_key, signer_profile_id="profile-b")

    response = backend.sign(request, _peer())

    assert response.accepted is False
    assert response.rejection_code == REJECT_ED25519_SIGNER_REQUEST_INVALID


@pytest.mark.skipif(not hasattr(socket, "AF_UNIX"), reason="AF_UNIX required")
def test_fresh_handshake_crosses_real_bounded_socket(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    runtime = tmp_path / "runtime"
    repo.mkdir()
    runtime.mkdir()
    socket_path = runtime / "signer.sock"
    private_key = _private_key()
    binding = replace(_binding(), socket_path=str(socket_path.resolve()))
    backend = replace(
        _backend(private_key),
        signer_peer_instance_binding=binding,
    )
    ready = threading.Event()
    holder: dict[str, object] = {}

    def serve() -> None:
        holder["result"] = serve_reddog_isolated_signer_socket_bounded(
            repo_root=repo,
            socket_path=socket_path,
            backend=backend,
            peer_attestor=_FixedPeerAttestor(),
            max_requests=1,
            timeout_s=5,
            ready_callback=ready.set,
        )

    thread = threading.Thread(target=serve, daemon=True)
    thread.start()
    assert ready.wait(5)
    built = build_reddog_isolated_signer_socket_client(
        repo_root=repo,
        socket_path=socket_path,
        timeout_s=5,
    )
    assert built.accepted is True and built.client is not None
    request = _request(private_key, socket_path=str(socket_path.resolve()))
    response = built.client.sign(request)
    thread.join(5)

    assert verify_signer_peer_handshake_response(
        request,
        response,
        now_epoch=NOW,
    ).accepted is True
    assert getattr(holder["result"], "accepted") is True


class _FixedPeerAttestor:
    def attest(self, connection: socket.socket) -> SignerPeerAttestation:
        del connection
        return _peer()


def test_handshake_modules_follow_wsp62_boundaries() -> None:
    bridge_root = Path(__file__).parents[1]
    for name in WSP62_SLICE_FILES:
        source = (bridge_root / name).read_text(encoding="utf-8")
        assert len(source.splitlines()) <= 675
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                assert node.end_lineno is not None
                assert node.end_lineno - node.lineno + 1 <= 60
            if isinstance(node, ast.ClassDef):
                assert node.end_lineno is not None
                assert node.end_lineno - node.lineno + 1 <= 200
