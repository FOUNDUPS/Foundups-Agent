"""Linux transport proof for peer-authenticated isolated signer clients."""

from __future__ import annotations

import json
import os
import socket
import sys
import threading
from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.src.reddog_isolated_signer_socket_client import (
    FAIL_SIGNER_SOCKET_LINK_COMPONENT,
    REJECT_SIGNER_SOCKET_CONNECT_FAILED,
    build_reddog_isolated_signer_socket_client,
)
from modules.communication.moltbot_bridge.tests.test_reddog_isolated_signer_socket_client import (
    _request,
)


pytestmark = pytest.mark.skipif(
    not sys.platform.startswith("linux"), reason="Linux SO_PEERCRED contract"
)


def test_real_unix_socket_owner_and_connected_peer_are_verified(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    runtime = tmp_path / "grant-authority"
    runtime.mkdir(mode=0o700)
    runtime.chmod(0o700)
    socket_path = runtime / "grant-authority.sock"
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(str(socket_path))
    server.listen(1)
    response = {
        "accepted": True,
        "signature": "sig:grant",
        "signer_public_key": "pub:grant",
        "key_fingerprint": "sha256:fingerprint",
        "key_epoch": "grant-epoch-1",
        "audit_mac": "audit:grant",
        "boundary_attested": True,
        "requester_identity_attested": True,
        "signer_loads_no_untrusted_code": True,
        "no_secret_material_returned": True,
    }

    def serve() -> None:
        connection, _address = server.accept()
        with connection:
            connection.recv(32768)
            connection.sendall(
                (json.dumps(response, sort_keys=True) + "\n").encode("ascii")
            )

    worker = threading.Thread(target=serve)
    worker.start()
    try:
        built = build_reddog_isolated_signer_socket_client(
            repo_root=repo,
            socket_path=socket_path,
            expected_server_uid=os.getuid(),
            expected_server_gid=os.getgid(),
            trusted_socket_root=runtime,
        )
        assert built.accepted is True and built.client is not None
        assert built.client.sign(_request()).accepted is True
    finally:
        server.close()
        worker.join(5)


def test_configured_socket_symlink_is_rejected(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    runtime = tmp_path / "grant-authority"
    runtime.mkdir(mode=0o700)
    runtime.chmod(0o700)
    target = runtime / "real.sock"
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(str(target))
    alias = runtime / "grant-authority.sock"
    alias.symlink_to(target)
    try:
        built = build_reddog_isolated_signer_socket_client(
            repo_root=repo,
            socket_path=alias,
            trusted_socket_root=runtime,
            expected_server_uid=os.getuid(),
            expected_server_gid=os.getgid(),
        )
        assert built.accepted is False
        assert built.rejection_reasons == (FAIL_SIGNER_SOCKET_LINK_COMPONENT,)
    finally:
        server.close()


def test_socket_inode_replacement_rejects_before_use(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    runtime = tmp_path / "grant-authority"
    runtime.mkdir(mode=0o700)
    runtime.chmod(0o700)
    socket_path = runtime / "grant-authority.sock"
    original = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    original.bind(str(socket_path))
    built = build_reddog_isolated_signer_socket_client(
        repo_root=repo,
        socket_path=socket_path,
        trusted_socket_root=runtime,
        expected_server_uid=os.getuid(),
        expected_server_gid=os.getgid(),
    )
    assert built.accepted is True and built.client is not None
    original.close()
    socket_path.unlink()
    replacement = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    replacement.bind(str(socket_path))
    try:
        response = built.client.sign(_request())
        assert response.accepted is False
        assert response.rejection_code == REJECT_SIGNER_SOCKET_CONNECT_FAILED
    finally:
        replacement.close()
