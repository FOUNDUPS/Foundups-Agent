"""Tests for REDDOG_ISOLATED_SIGNER_SOCKET_RESIDENT_SERVICE_PHASE1."""

from __future__ import annotations

import socket
import threading
from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.src.reddog_isolated_signer_socket_client import (
    build_reddog_isolated_signer_socket_client,
)
from modules.communication.moltbot_bridge.src.reddog_isolated_signer_socket_protocol import (
    SignerPeerAttestation,
)
from modules.communication.moltbot_bridge.src.reddog_isolated_signer_socket_resident_service import (
    FAIL_SIGNER_RESIDENT_SERVICE_MAX_REQUESTS_INVALID,
    SIGNER_SOCKET_RESIDENT_SERVICE_SERVED,
    serve_reddog_isolated_signer_socket_bounded,
)
from modules.communication.moltbot_bridge.src.reddog_isolated_signer_socket_service import (
    FAIL_SIGNER_SERVICE_SOCKET_PATH_INSIDE_REPO,
    FAIL_SIGNER_SERVICE_SOCKET_PATH_RELATIVE,
)
from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    SigningRequest,
    SigningResponse,
)


class FakeBackend:
    def __init__(self) -> None:
        self.requests: list[SigningRequest] = []

    def sign(self, request: SigningRequest, peer: SignerPeerAttestation) -> SigningResponse:
        self.requests.append(request)
        return SigningResponse(
            accepted=True,
            signature=f"sig:{request.nonce}",
            signer_public_key=request.signer_public_key,
            key_fingerprint="fingerprint:abc",
            key_epoch=request.key_epoch,
            audit_mac=f"audit:{peer.peer_principal_id}:{request.nonce}",
            boundary_attested=True,
            requester_identity_attested=True,
            signer_loads_no_untrusted_code=True,
            no_secret_material_returned=True,
        )


class FixedPeerAttestor:
    def attest(self, connection: socket.socket) -> SignerPeerAttestation:
        return SignerPeerAttestation(
            peer_principal_id="github:mjtrout",
            transport="unix_socket",
            credential_source="test_peer",
            boundary_attested=True,
        )


def _request(nonce: str) -> SigningRequest:
    return SigningRequest(
        signing_input=f'reddog-workauth.v1.{{"nonce":"{nonce}"}}',
        payload_digest=f"sha256:{nonce}",
        signer_role="reddog",
        signer_public_key="ed25519:public",
        requester_principal_id="github:mjtrout",
        nonce=nonce,
        key_epoch="epoch-1",
        requested_operation="bounded_code_change",
        authority_tier="HIGH",
        consensus_receipt_digest="sha256:consensus",
    )


@pytest.mark.skipif(not hasattr(socket, "AF_UNIX"), reason="AF_UNIX required")
def test_bounded_resident_service_handles_multiple_client_requests(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    socket_path = runtime / "signer.sock"
    ready = threading.Event()
    result_holder: dict[str, object] = {}
    backend = FakeBackend()

    def _serve() -> None:
        result_holder["result"] = serve_reddog_isolated_signer_socket_bounded(
            repo_root=repo,
            socket_path=socket_path,
            backend=backend,
            peer_attestor=FixedPeerAttestor(),
            max_requests=2,
            timeout_s=5,
            ready_callback=ready.set,
        )

    thread = threading.Thread(target=_serve, daemon=True)
    thread.start()
    assert ready.wait(5)

    client_result = build_reddog_isolated_signer_socket_client(
        repo_root=repo,
        socket_path=socket_path,
        timeout_s=5,
    )
    assert client_result.accepted is True
    assert client_result.client is not None

    first = client_result.client.sign(_request("nonce-1"))
    second = client_result.client.sign(_request("nonce-2"))
    thread.join(5)

    assert first.accepted is True
    assert first.signature == "sig:nonce-1"
    assert second.accepted is True
    assert second.signature == "sig:nonce-2"
    assert len(backend.requests) == 2
    result = result_holder["result"]
    assert result.accepted is True
    assert result.status == SIGNER_SOCKET_RESIDENT_SERVICE_SERVED
    assert result.requests_handled == 2
    assert len(result.response_digests) == 2
    assert result.socket_removed is True
    assert not socket_path.exists()
    assert result.no_private_key_loaded is True
    assert result.no_vault_secret_resolved is True
    assert result.no_holoindex_reindex_performed is True


def test_bounded_resident_service_rejects_unsafe_paths_and_limits(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()

    relative = serve_reddog_isolated_signer_socket_bounded(
        repo_root=repo,
        socket_path="relative.sock",
    )
    inside_repo = serve_reddog_isolated_signer_socket_bounded(
        repo_root=repo,
        socket_path=repo / "signer.sock",
    )
    bad_count = serve_reddog_isolated_signer_socket_bounded(
        repo_root=repo,
        socket_path=tmp_path / "outside.sock",
        max_requests=0,
    )

    assert relative.accepted is False
    assert FAIL_SIGNER_SERVICE_SOCKET_PATH_RELATIVE in relative.rejection_reasons
    assert inside_repo.accepted is False
    assert FAIL_SIGNER_SERVICE_SOCKET_PATH_INSIDE_REPO in inside_repo.rejection_reasons
    assert bad_count.accepted is False
    assert FAIL_SIGNER_RESIDENT_SERVICE_MAX_REQUESTS_INVALID in bad_count.rejection_reasons
