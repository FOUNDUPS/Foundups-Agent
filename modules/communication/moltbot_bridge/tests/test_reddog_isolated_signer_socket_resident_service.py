"""Tests for REDDOG_ISOLATED_SIGNER_SOCKET_RESIDENT_SERVICE_PHASE1."""

from __future__ import annotations

import os
import multiprocessing
import socket
import sys
import threading
from dataclasses import replace
from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.src import (
    reddog_isolated_signer_socket_resident_service as resident_service,
)
from modules.communication.moltbot_bridge.src.reddog_isolated_signer_socket_client import (
    build_reddog_isolated_signer_socket_client,
)
from modules.communication.moltbot_bridge.src.reddog_isolated_signer_socket_protocol import (
    SignerPeerAttestation,
)
from modules.communication.moltbot_bridge.src.reddog_isolated_signer_socket_resident_service import (
    FAIL_SIGNER_RESIDENT_SERVICE_MAX_REQUESTS_INVALID,
    FAIL_SIGNER_SERVICE_SOCKET_PARENT_UNSAFE,
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
    public_key_fingerprint,
)
from modules.communication.moltbot_bridge.src.reddog_signer_socket_peer_credential_attestor import (
    KernelPeerCredentialAttestor,
    PeerCredentialPolicy,
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
            key_fingerprint=public_key_fingerprint(request.signer_public_key),
            key_epoch=request.key_epoch,
            audit_mac=f"audit:{peer.peer_principal_id}:{request.nonce}",
            boundary_attested=True,
            requester_identity_attested=True,
            signer_loads_no_untrusted_code=True,
            no_secret_material_returned=True,
        )


def _kernel_attestor():
    uid = os.getuid() if hasattr(os, "getuid") else 0
    gid = os.getgid() if hasattr(os, "getgid") else 0
    return KernelPeerCredentialAttestor(PeerCredentialPolicy(
        {uid: "github:mjtrout"}, allowed_gids=(gid,),
    ))


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


def _assert_kernel_responses(first, second, backend):
    if hasattr(socket, "SO_PEERCRED") or hasattr(socket.socket, "getpeereid"):
        assert first.accepted is True
        assert first.signature == "sig:nonce-1"
        assert second.accepted is True
        assert second.signature == "sig:nonce-2"
        assert len(backend.requests) == 2
    else:
        assert first.rejection_code == "REJECT_SIGNER_SOCKET_PEER_NOT_ATTESTED"
        assert second.rejection_code == "REJECT_SIGNER_SOCKET_PEER_NOT_ATTESTED"
        assert backend.requests == []


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
            peer_attestor=_kernel_attestor(),
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

    _assert_kernel_responses(first, second, backend)
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


@pytest.mark.skipif(not hasattr(socket, "AF_UNIX"), reason="AF_UNIX required")
def test_cleanup_never_unlinks_a_substituted_socket(tmp_path: Path) -> None:
    socket_path = tmp_path / "signer.sock"
    original = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    replacement = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        original.bind(str(socket_path))
        identity = resident_service._socket_identity(socket_path)
        assert identity is not None
        original.close()
        socket_path.unlink()
        replacement.bind(str(socket_path))

        assert resident_service._cleanup_socket(socket_path, identity) is False
        assert socket_path.exists()
    finally:
        original.close()
        replacement.close()
        socket_path.unlink(missing_ok=True)


@pytest.mark.skipif(os.name != "posix", reason="POSIX ownership required")
def test_group_or_world_writable_socket_parent_is_rejected(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    runtime.chmod(0o777)

    result = serve_reddog_isolated_signer_socket_bounded(
        repo_root=repo,
        socket_path=runtime / "signer.sock",
    )

    assert result.accepted is False
    assert FAIL_SIGNER_SERVICE_SOCKET_PARENT_UNSAFE in result.rejection_reasons


@pytest.mark.skipif(not hasattr(socket, "AF_UNIX"), reason="AF_UNIX required")
def test_cleanup_rejects_reused_identity_with_different_change_time(tmp_path):
    path = tmp_path / "signer.sock"
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as server:
        server.bind(str(path))
        actual = resident_service._socket_identity(path)
        stale = replace(actual, change_time_ns=actual.change_time_ns - 1)
        assert resident_service._cleanup_socket(path, stale) is False
        assert path.exists()
        if os.name != "posix":
            server.close()
        assert resident_service._cleanup_socket(path, actual) is True


def _native_cleanup_server(repo, path, mode, pipe, resume):
    """Real transport; passive wrappers observe listener lifetime only."""
    bound, observations = [], []
    bind = resident_service._bound_server
    cleanup = resident_service._cleanup_socket

    def observed_bind(*args):
        server, identity = bind(*args)
        bound.append(server)
        return server, identity

    def observed_cleanup(*args):
        observations.append(bound[0].fileno() >= 0)
        return cleanup(*args)

    def ready():
        info = path.stat()
        pipe.send((os.getpid(), info.st_dev, info.st_ino))
        if not resume.wait(5):
            raise RuntimeError("test_parent_timeout")
        if mode != "success":
            raise RuntimeError("test_callback_failure")

    resident_service._bound_server = observed_bind
    resident_service._cleanup_socket = observed_cleanup
    result = serve_reddog_isolated_signer_socket_bounded(
        repo_root=repo, socket_path=path, backend=FakeBackend(),
        peer_attestor=_kernel_attestor(), max_requests=1, timeout_s=3,
        ready_callback=ready,
    )
    pipe.send((result.accepted, result.socket_removed, observations,
               bound[0].fileno() == -1))
    pipe.close()


@pytest.mark.skipif(sys.platform != "linux", reason="Linux inode and process qualification")
@pytest.mark.parametrize("mode", ["success", "exception", "replacement"])
def test_native_listener_pins_inode_through_cleanup(tmp_path, mode):
    repo = tmp_path / "repo"
    repo.mkdir()
    path = tmp_path / "signer.sock"
    context = multiprocessing.get_context("fork")
    parent, child = context.Pipe()
    resume = context.Event()
    process = context.Process(target=_native_cleanup_server,
                              args=(repo, path, mode, child, resume))
    replacement = None
    process.start()
    child.close()
    try:
        assert parent.poll(8)
        pid, device, inode = parent.recv()
        assert pid != os.getpid()
        if mode == "replacement":
            path.unlink()
            replacement = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            replacement.bind(str(path))
            assert (path.stat().st_dev, path.stat().st_ino) != (device, inode)
        resume.set()
        if mode == "success":
            client = build_reddog_isolated_signer_socket_client(
                repo_root=repo, socket_path=path, timeout_s=3)
            assert client.client.sign(_request("native-cleanup")).accepted
        assert parent.poll(8)
        accepted, removed, observations, closed = parent.recv()
        process.join(5)
        assert process.exitcode == 0 and closed and observations and all(observations)
        assert accepted is (mode == "success")
        assert removed is (mode == "success")
        assert path.exists() is (mode == "replacement")
    finally:
        resume.set()
        if process.is_alive():
            process.terminate()
        process.join(5)
        parent.close()
        if replacement is not None:
            replacement.close()
        path.unlink(missing_ok=True)
