"""Linux-root transport proof for the revocation-anchor route."""

from __future__ import annotations

import os
import shutil
import tempfile
import threading
import time
from dataclasses import replace
from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.src import (
    foundup_verified_outcome_root_authority_client as root_client_module,
)
from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_authority_client import (
    build_root_authority_socket_exchange,
)
from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_authority_socket_service import (
    serve_root_authority_bounded,
)
from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_revocation_client import (
    _create_root_revocation_anchor_authority,
)
from modules.communication.moltbot_bridge.src.reddog_signer_socket_peer_credential_attestor import (
    KernelPeerCredentialAttestor,
    PeerCredentialPolicy,
)
from modules.communication.moltbot_bridge.tests.root_revocation_service_fixtures import (
    legacy_roundtrip,
    runtime,
    signed_snapshot,
    stage,
)
from modules.communication.moltbot_bridge.tests.root_revocation_linux_socket_fixture import (
    exchange_before_non_root_listener_substitution,
    reap_listener,
)
from modules.communication.moltbot_bridge.tests.test_foundup_verified_outcome_root_authority import (
    _sign,
)

pytestmark = pytest.mark.skipif(
    os.name != "posix" or not hasattr(os, "geteuid") or os.geteuid() != 0,
    reason="real root-owned Unix revocation service requires Linux root",
)

SIGNER_UID = 65534
SIGNER_GID = 65534
_REAL_REQUIRE_SOCKET = root_client_module._require_protected_socket
_REAL_ROUNDTRIP = root_client_module._root_socket_roundtrip


def test_real_linux_root_router_serves_revocation_and_legacy(monkeypatch) -> None:
    base, values, candidate, snapshot, socket_path = _setup(monkeypatch)
    try:
        result, server = _serve(values, snapshot, socket_path, max_requests=4)
        child_result = _run_child(
            values, candidate["snapshot_id"], socket_path,
            uid=SIGNER_UID, gid=SIGNER_GID, include_legacy=True,
        )
        server.join(timeout=10)
        assert child_result == b"PASS"
        assert len(result) == 1 and result[0].accepted is True
        assert result[0].requests_handled == 4
    finally:
        shutil.rmtree(base, ignore_errors=True)


@pytest.mark.parametrize(
    ("uid", "gid", "supplementary", "expected"),
    (
        (65533, SIGNER_GID, (), b"PASS"),
        (SIGNER_UID, 65533, (SIGNER_GID,), b"PASS"),
        (SIGNER_UID, SIGNER_GID, (), b""),
    ),
)
def test_real_linux_root_revocation_peer_rejection_signal_is_exact(
    monkeypatch, uid: int, gid: int, supplementary: tuple[int, ...], expected: bytes
) -> None:
    base, values, candidate, snapshot, socket_path = _setup(monkeypatch)
    try:
        result, server = _serve(values, snapshot, socket_path, max_requests=1)
        child_result = _run_child(
            values, candidate["snapshot_id"], socket_path,
            uid=uid, gid=gid, supplementary=supplementary, expect_reject=True,
        )
        server.join(timeout=10)
        assert child_result == expected
        assert len(result) == 1 and result[0].accepted is True
        assert result[0].requests_handled == 1
    finally:
        shutil.rmtree(base, ignore_errors=True)


def test_real_linux_root_revocation_rejects_socket_substitution(monkeypatch) -> None:
    base, values, _candidate, _snapshot, socket_path = _setup(monkeypatch)
    try:
        exchange, child = exchange_before_non_root_listener_substitution(
            socket_path, repo_root=values["repo"],
            attacker_uid=65533, attacker_gid=65533,
        )
        with pytest.raises(OSError, match="server_uid_mismatch"):
            exchange.exchange(b"{}\n")
        reap_listener(child)
    finally:
        shutil.rmtree(base, ignore_errors=True)


def _setup(monkeypatch):
    base = Path(tempfile.mkdtemp(prefix="reddog-root-revocation-", dir="/var/lib"))
    os.chmod(base, 0o755)
    values = runtime(base / "fixture", monkeypatch)
    monkeypatch.setattr(root_client_module, "_require_protected_socket", _REAL_REQUIRE_SOCKET)
    monkeypatch.setattr(root_client_module, "_root_socket_roundtrip", _REAL_ROUNDTRIP)
    candidate = signed_snapshot(values)
    stage(values, candidate)
    snapshot = replace(
        values["snapshot"], signer_uid=SIGNER_UID, signer_gid=SIGNER_GID
    )
    socket_root = base / "socket"
    socket_root.mkdir(mode=0o755)
    return base, values, candidate, snapshot, socket_root / "authority.sock"


def _serve(values, snapshot, socket_path: Path, *, max_requests: int):
    results = []
    server = threading.Thread(
        target=lambda: results.append(serve_root_authority_bounded(
            repo_root=values["repo"], socket_path=socket_path,
            signer_gid=SIGNER_GID, state=values["state"],
            snapshot_supplier=lambda: snapshot,
            revocation_authority=values["server_authority"],
            peer_attestor=KernelPeerCredentialAttestor(PeerCredentialPolicy(
                {SIGNER_UID: snapshot.signer_principal_id},
                allowed_gids=(SIGNER_GID,),
            )),
            max_requests=max_requests, timeout_s=5.0,
        )),
        daemon=True,
    )
    server.start()
    deadline = time.time() + 5
    while not socket_path.exists() and time.time() < deadline:
        time.sleep(0.01)
    return results, server


def _run_child(
    values, snapshot_id: str, socket_path: Path, *, uid: int, gid: int,
    supplementary: tuple[int, ...] = (), expect_reject: bool = False,
    include_legacy: bool = False,
) -> bytes:
    exchange = build_root_authority_socket_exchange(
        repo_root=values["repo"], socket_path=socket_path,
        expected_server_uid=0,
    )
    client = _create_root_revocation_anchor_authority(
        values["snapshot"].descriptor,
        owner_config_id=str(values["policy"]["owner_config_id"]),
        policy=values["policy"], binding=values["binding"], exchange=exchange,
        request_signer=lambda value: _sign(values["target_private"], value),
        now_epoch=int(time.time()),
    )
    read_fd, write_fd = os.pipe()
    child = os.fork()
    if child == 0:
        try:
            os.close(read_fd)
            os.setgroups(list(supplementary))
            os.setgid(gid)
            os.setuid(uid)
            if expect_reject:
                client.load()
                accepted = True
            else:
                accepted = client.load() is None
                accepted = accepted and client.advance_snapshot(snapshot_id).sequence == 1
            if accepted and include_legacy:
                accepted = legacy_roundtrip(values, exchange)
            if accepted and not expect_reject:
                os.write(write_fd, b"PASS")
        except Exception:
            if expect_reject:
                os.write(write_fd, b"PASS")
        finally:
            os.close(write_fd)
            os._exit(0)
    os.close(write_fd)
    result = os.read(read_fd, 4)
    os.close(read_fd)
    os.waitpid(child, 0)
    return result
