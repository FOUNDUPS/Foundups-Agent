"""Linux-root socket proof for signer protected-use acquire/finish."""

from __future__ import annotations

import os
import shutil
import time

import pytest

from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_authority_client import (
    build_root_authority_socket_exchange,
)
from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_protected_use_client import (
    _create_root_protected_use_authority,
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


def _run_child(values, socket_path) -> bytes:
    exchange = build_root_authority_socket_exchange(
        repo_root=values["repo"], socket_path=socket_path,
        expected_server_uid=0,
    )
    client = _create_root_protected_use_authority(
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
