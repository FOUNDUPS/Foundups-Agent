"""Linux-root socket proof for signer protected-use acquire/finish."""
from __future__ import annotations

import os
import select
import shutil
import time

import pytest

from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_authority_client import (
    build_root_authority_socket_exchange,
)
from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_protected_use_client import (
    _create_root_protected_use_authority,
)
from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_revocation_client import (
    _create_root_revocation_anchor_authority,
)
from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    confined_runtime_operation_lock,
)
from modules.communication.moltbot_bridge.src.reddog_proposal_authenticity_nonce_store import (
    ProposalReplayHighWater,
)
from modules.communication.moltbot_bridge.tests.test_foundup_verified_outcome_root_authority import (
    _sha,
    _sign,
)
from modules.communication.moltbot_bridge.tests.test_foundup_verified_outcome_root_revocation_linux import (
    SIGNER_GID,
    SIGNER_UID,
    _serve,
    _setup,
)
from modules.communication.moltbot_bridge.tests.root_revocation_snapshot_fixture import (
    signed_snapshot,
    stage,
)
pytestmark = pytest.mark.skipif(
    os.name != "posix" or not hasattr(os, "geteuid") or os.geteuid() != 0,
    reason="real root-owned protected-use service requires Linux root",
)


def test_real_linux_root_socket_authorizes_one_exact_callback(monkeypatch) -> None:
    base, values, candidate, snapshot, socket_path = _setup(monkeypatch)
    try:
        wanted = ProposalReplayHighWater(
            int(candidate["sequence"]), str(candidate["snapshot_id"])[7:]
        )
        values["state"].advance_revocation(
            values["binding"].anchor_binding_digest(),
            expected=None, next_value=wanted,
        )
        values["store"]._finalize_under_lock(candidate["snapshot_id"])
        results, server = _serve(values, snapshot, socket_path, max_requests=2)
        assert _run_child(values, socket_path) == b"PASS"
        server.join(timeout=10)
        assert len(results) == 1 and results[0].accepted is True
        assert results[0].requests_handled == 2
    finally:
        shutil.rmtree(base, ignore_errors=True)


def test_real_socket_publisher_lock_does_not_invert_with_acquire(monkeypatch) -> None:
    base, values, candidate, snapshot, socket_path = _setup(monkeypatch)
    try:
        current = ProposalReplayHighWater(1, str(candidate["snapshot_id"])[7:])
        values["state"].advance_revocation(
            values["binding"].anchor_binding_digest(),
            expected=None, next_value=current,
        )
        values["store"]._finalize_under_lock(candidate["snapshot_id"])
        next_value = signed_snapshot(values, sequence=2)
        results, server = _serve(values, snapshot, socket_path, max_requests=3)
        ready_r, ready_w = os.pipe()
        go_r, go_w = os.pipe()
        pub_r, pub_w = os.pipe()
        publisher = _fork_locked_publisher(
            values, socket_path, next_value,
            ready_r, ready_w, go_r, go_w, pub_r, pub_w,
        )
        os.close(ready_w); os.close(go_r); os.close(pub_w)
        assert os.read(ready_r, 1) == b"R"
        os.close(ready_r)
        acquire_r, acquire_w = os.pipe()
        acquirer = _fork_rejected_acquire(values, socket_path, acquire_r, acquire_w)
        os.close(acquire_w)
        completed_before_release = bool(select.select([acquire_r], [], [], 3.0)[0])
        os.write(go_w, b"G"); os.close(go_w)
        acquire_result = os.read(acquire_r, 4)
        publisher_result = os.read(pub_r, 128)
        os.close(acquire_r); os.close(pub_r)
        os.waitpid(acquirer, 0); os.waitpid(publisher, 0)
        server.join(timeout=10)
        assert completed_before_release
        assert acquire_result == b"PASS"
        assert publisher_result == b"PASS", publisher_result
        assert len(results) == 1 and results[0].accepted is True
        assert results[0].requests_handled == 3
    finally:
        shutil.rmtree(base, ignore_errors=True)


def _run_child(values, socket_path) -> bytes:
    client = _protected_client(values, socket_path)
    read_fd, write_fd = os.pipe()
    child = os.fork()
    if child == 0:
        try:
            os.close(read_fd)
            os.setgroups([])
            os.setgid(SIGNER_GID)
            os.setuid(SIGNER_UID)
            result = client.authorize_use(
                grant_id=_sha("grant"), key_epoch="epoch-1",
                signing_request_digest=_sha("request"),
                grant_expires_at=int(time.time()) + 120,
                action=lambda: "signed",
            )
            if result == "signed":
                os.write(write_fd, b"PASS")
        finally:
            os.close(write_fd)
            os._exit(0)
    os.close(write_fd)
    result = os.read(read_fd, 4)
    os.close(read_fd)
    os.waitpid(child, 0)
    return result


def _protected_client(values, socket_path):
    exchange = build_root_authority_socket_exchange(
        repo_root=values["repo"], socket_path=socket_path,
        expected_server_uid=0,
    )
    return _create_root_protected_use_authority(
        values["snapshot"].descriptor,
        owner_config_id=str(values["policy"]["owner_config_id"]),
        policy=values["policy"], binding=values["binding"], exchange=exchange,
        request_signer=lambda value: _sign(values["target_private"], value),
        now_epoch=int(time.time()),
    )


def _fork_locked_publisher(values, socket_path, candidate, *pipes):
    ready_r, ready_w, go_r, go_w, result_r, result_w = pipes
    child = os.fork()
    if child == 0:
        try:
            os.close(ready_r); os.close(go_w); os.close(result_r)
            exchange = build_root_authority_socket_exchange(
                repo_root=values["repo"], socket_path=socket_path,
                expected_server_uid=0,
            )
            client = _create_root_revocation_anchor_authority(
                values["snapshot"].descriptor,
                owner_config_id=str(values["policy"]["owner_config_id"]),
                policy=values["policy"], binding=values["binding"],
                exchange=exchange,
                request_signer=lambda value: _sign(values["target_private"], value),
                now_epoch=int(time.time()),
            )
            with confined_runtime_operation_lock(
                values["binding"].operation_lock_path,
                repo_root=values["repo"], allowed_root=values["binding"].primary_root,
            ):
                stage(values, candidate); os.write(ready_w, b"R"); os.read(go_r, 1)
                os.setgroups([]); os.setgid(SIGNER_GID); os.setuid(SIGNER_UID)
                if client.advance_snapshot(candidate["snapshot_id"]).sequence == 2:
                    os.write(result_w, b"PASS")
        except Exception as exc:
            os.write(result_w, (type(exc).__name__ + ":" + str(exc))[:128].encode("ascii"))
        finally:
            os._exit(0)
    return child


def _fork_rejected_acquire(values, socket_path, result_r, result_w):
    child = os.fork()
    if child == 0:
        try:
            os.close(result_r); os.setgroups([])
            os.setgid(SIGNER_GID); os.setuid(SIGNER_UID)
            called = []
            try:
                _protected_client(values, socket_path).authorize_use(
                    grant_id=_sha("grant-lock"), key_epoch="epoch-1",
                    signing_request_digest=_sha("request-lock"),
                    grant_expires_at=int(time.time()) + 120,
                    action=lambda: called.append(True),
                )
            except Exception:
                if not called:
                    os.write(result_w, b"PASS")
        finally:
            os._exit(0)
    return child
