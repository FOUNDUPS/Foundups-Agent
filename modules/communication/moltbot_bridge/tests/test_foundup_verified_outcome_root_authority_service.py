"""Adversarial tests for the independent root outcome-authority service."""

from __future__ import annotations

import copy
import hashlib
import os
import shutil
import stat
import tempfile
import threading
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from dataclasses import asdict, replace
from multiprocessing import get_context
from pathlib import Path
from types import SimpleNamespace

import pytest

from modules.communication.moltbot_bridge.src import (
    foundup_verified_outcome_root_authority as authority_module,
    foundup_verified_outcome_root_authority_client as client_module,
    foundup_verified_outcome_root_authority_protocol as protocol,
)
from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_authority_wire_codec import (
    decode_message, encode_message,
)
from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_authority import (
    descriptor_id_for,
)
from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_authority_client import (
    _create_service_backed_outcome_authority,
    build_root_authority_socket_exchange,
)
from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_authority_protocol import (
    RootAuthorityResponse,
    request_from_bytes,
)
from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_authority_service import (
    RootAuthoritySnapshot,
    _current_snapshot,
    handle_root_authority_request,
    initialize_root_authority_state,
)
from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_authority_state import (
    GENERATION_BINDING,
    RootVerifiedOutcomeAuthorityState,
    authorization_binding,
)
from modules.communication.moltbot_bridge.src.reddog_isolated_signer_socket_protocol import (
    SignerPeerAttestation,
)
from modules.communication.moltbot_bridge.src.reddog_signer_socket_peer_credential_attestor import (
    KernelPeerCredentialAttestor,
    KernelPeerIdentity,
    PeerCredentialPolicy,
)
from modules.communication.moltbot_bridge.src.reddog_sqlite_monotonic_authority_store import (
    SqliteMonotonicAuthorityStore,
)
from modules.communication.moltbot_bridge.tests.test_foundup_verified_outcome_root_authority import (
    NOW,
    REPO_ROOT,
    _commit,
    _descriptor,
    _private_key,
    _reserve,
    _sha,
    _sign,
)
from modules.communication.moltbot_bridge.src import (
    foundup_verified_outcome_root_authority_state as state_module,
)
from modules.communication.moltbot_bridge.src.reddog_proposal_authenticity_nonce_store import (
    ProposalReplayHighWater,
)
from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_authority_socket_service import (
    serve_root_authority_bounded,
)


def _stores(
    tmp_path: Path, descriptor: dict
) -> tuple[
    SqliteMonotonicAuthorityStore,
    SqliteMonotonicAuthorityStore,
    SqliteMonotonicAuthorityStore,
]:
    primary_root = tmp_path / "root-primary"
    witness_root = tmp_path / "root-witness"
    primary = SqliteMonotonicAuthorityStore(
        primary_root / "verified-outcome-authority.sqlite3",
        allowed_root=primary_root,
        repo_root=REPO_ROOT,
        store_id=descriptor["replay_store_id"],
        durability_receipt_id=descriptor[
            "replay_store_durability_receipt_id"
        ],
    )
    witness = SqliteMonotonicAuthorityStore(
        witness_root / "verified-outcome-authority-witness.sqlite3",
        allowed_root=witness_root,
        repo_root=REPO_ROOT,
        store_id="verified-outcome-root-witness",
        durability_receipt_id=_sha("root-witness-durable"),
    )
    installation_root = tmp_path / "root-installation"
    installation = SqliteMonotonicAuthorityStore(
        installation_root / "verified-outcome-authority-installation.sqlite3",
        allowed_root=installation_root,
        repo_root=REPO_ROOT,
        store_id="verified-outcome-root-installation",
        durability_receipt_id=_sha("root-installation-durable"),
    )
    return primary, witness, installation


def _state(
    tmp_path: Path, descriptor: dict
) -> tuple[
    RootVerifiedOutcomeAuthorityState,
    SqliteMonotonicAuthorityStore,
    SqliteMonotonicAuthorityStore,
    SqliteMonotonicAuthorityStore,
]:
    primary, witness, installation = _stores(tmp_path, descriptor)
    state = RootVerifiedOutcomeAuthorityState(
        primary,
        witness,
        installation,
        repo_root=REPO_ROOT,
        require_root_ownership=False,
    )
    return state, primary, witness, installation


def _snapshot(
    descriptor: dict,
    owner_config_id: str | None = None,
    state: RootVerifiedOutcomeAuthorityState | None = None,
):
    return RootAuthoritySnapshot(
        owner_config_id=owner_config_id or _sha("owner-config"),
        authority_generation_sequence=descriptor[
            "authority_generation_sequence"
        ],
        state_binding_digest=(
            state.state_binding_digest if state is not None else _sha("state-binding")
        ),
        signer_principal_id="reddog-e0-signer",
        signer_uid=1001,
        signer_gid=1001,
        descriptor=descriptor,
    )


def _peer(
    principal: str = "reddog-e0-signer", *, uid: int = 1001, gid: int = 1001
) -> KernelPeerIdentity:
    attestation = SignerPeerAttestation(
        peer_principal_id=principal, transport="unix_socket",
        credential_source=f"kernel_so_peercred:uid={uid}:gid={gid}",
        boundary_attested=True,
    )
    return KernelPeerIdentity(attestation, 1234, uid, gid, "kernel_so_peercred")


def _advance_root_state_process(values: tuple[str, dict, str]) -> bool:
    path, descriptor, binding = values
    state, *_stores_value = _state(Path(path), descriptor)
    try:
        state.advance(
            binding, expected=None,
            next_value=ProposalReplayHighWater(1, "c" * 64),
        )
    except Exception:
        return False
    return True


def _client_authority(
    monkeypatch: pytest.MonkeyPatch,
    descriptor: dict,
    owner_config_id: str,
    exchange,
):
    monkeypatch.setattr(client_module, "_require_protected_socket", lambda *_args: None)
    monkeypatch.setattr(
        client_module,
        "_root_socket_roundtrip",
        lambda _path, raw, _uid, _timeout: exchange(raw),
    )
    transport = build_root_authority_socket_exchange(
        repo_root=REPO_ROOT,
        socket_path="C:/root-authority-test.sock",
    )
    return _create_service_backed_outcome_authority(
        descriptor,
        owner_config_id=owner_config_id,
        exchange=transport,
        now_epoch=NOW,
    )


def _runtime(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    descriptor, grant, _legacy_store = _descriptor(tmp_path / "descriptor")
    state, primary, witness, installation = _state(tmp_path, descriptor)
    current = {"snapshot": _snapshot(descriptor, state=state)}
    initialize_root_authority_state(state, current["snapshot"], now_epoch=NOW)

    def exchange(raw: bytes) -> bytes:
        return handle_root_authority_request(
            raw,
            peer=_peer(),
            state=state,
            snapshot_supplier=lambda: current["snapshot"],
            now_epoch=NOW,
        )

    authority = _client_authority(
        monkeypatch,
        descriptor,
        current["snapshot"].owner_config_id,
        exchange,
    )
    return (
        descriptor,
        grant,
        state,
        primary,
        witness,
        installation,
        current,
        authority,
    )


def test_root_service_reserve_commit_and_replay_reject(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _descriptor_value, grant, state, *_rest, authority = _runtime(
        tmp_path, monkeypatch
    )
    reservation = _reserve(authority, grant)

    assert reservation is not None
    _commit(authority, reservation, _sha("signature"))
    committed = state.load(authorization_binding(grant["authorization_id"]))
    assert committed is not None and committed.sequence == 2
    assert _reserve(authority, grant) is None


@pytest.mark.parametrize("loss", ["none", "primary", "witness"])
def test_root_commit_recovery_acknowledges_only_exact_committed_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, loss: str,
) -> None:
    descriptor, grant, state, *_rest, authority = _runtime(tmp_path, monkeypatch)
    reservation = _reserve(authority, grant)
    assert reservation is not None
    _commit(authority, reservation, _sha("signature"))
    binding = authorization_binding(grant["authorization_id"])
    committed = state.load(binding)
    if loss != "none":
        missing = state._primary if loss == "primary" else state._witness
        missing.path.unlink()
        reopened, *_rest = _state(tmp_path, descriptor)
        assert reopened.state_binding_digest == state.state_binding_digest
    _commit(authority, reservation, _sha("signature"))
    assert state.load(binding) == committed
    assert committed.sequence == 2
    assert _reserve(authority, grant) is None


@pytest.mark.parametrize("failure_type", [ConnectionResetError, TimeoutError])
@pytest.mark.parametrize("after_commit", [False, True], ids=["before", "after"])
def test_root_commit_recovery_retries_identical_transport_request(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    failure_type: type[Exception], after_commit: bool,
) -> None:
    _descriptor_value, grant, state, *_rest, authority = _runtime(tmp_path, monkeypatch)
    reservation = _reserve(authority, grant)
    assert reservation is not None
    roundtrip, attempts = client_module._root_socket_roundtrip, []

    def interrupted_roundtrip(path, payload, uid, timeout):
        attempts.append(hashlib.sha256(payload).hexdigest())
        if len(attempts) == 1:
            if after_commit:
                roundtrip(path, payload, uid, timeout)
            raise failure_type("test_commit_transport_interrupted")
        return roundtrip(path, payload, uid, timeout)

    monkeypatch.setattr(client_module, "_root_socket_roundtrip", interrupted_roundtrip)
    _commit(authority, reservation, _sha("signature"))
    assert len(attempts) == 2 and attempts[0] == attempts[1]
    committed = state.load(authorization_binding(grant["authorization_id"]))
    assert committed is not None and committed.sequence == 2
    monkeypatch.setattr(client_module, "_root_socket_roundtrip", roundtrip)
    assert _reserve(authority, grant) is None


def test_root_commit_recovery_concurrent_acknowledgments_share_one_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _descriptor_value, grant, state, *_rest, authority = _runtime(tmp_path, monkeypatch)
    reservation = _reserve(authority, grant)
    assert reservation is not None
    barrier = threading.Barrier(4)

    def complete(_index: int) -> None:
        barrier.wait(timeout=10)
        _commit(authority, reservation, _sha("signature"))

    with ThreadPoolExecutor(max_workers=4) as pool:
        assert list(pool.map(complete, range(4))) == [None] * 4
    marker = state.load(authorization_binding(grant["authorization_id"]))
    assert marker is not None and marker.sequence == 2
    assert _reserve(authority, grant) is None


@pytest.mark.parametrize("change", ["signature_digest", "reservation"])
def test_root_commit_recovery_rejects_changed_terminal_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, change: str,
) -> None:
    _descriptor_value, grant, state, *_rest, authority = _runtime(tmp_path, monkeypatch)
    reservation = _reserve(authority, grant)
    assert reservation is not None
    _commit(authority, reservation, _sha("signature"))
    binding = authorization_binding(grant["authorization_id"])
    before = state.load(binding)
    changed = replace(reservation, reservation_id=_sha("another-reservation")) if change == "reservation" else reservation
    digest = _sha("another-signature") if change == "signature_digest" else _sha("signature")
    with pytest.raises(ValueError, match="commit_rejected"):
        _commit(authority, changed, digest)
    assert state.load(binding) == before
    assert _reserve(authority, grant) is None


@pytest.mark.parametrize("invalidation", ["revocation", "expiry"])
def test_root_commit_recovery_revalidates_after_lost_reply(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, invalidation: str,
) -> None:
    descriptor, grant, state, _primary, _witness, _installation, current, authority = _runtime(tmp_path, monkeypatch)
    reservation = _reserve(authority, grant)
    assert reservation is not None
    attempts = []

    def changing_authority_roundtrip(_path, payload, _uid, _timeout):
        attempts.append(hashlib.sha256(payload).hexdigest())
        now = int(grant["expires_at"]) if invalidation == "expiry" and len(attempts) > 1 else NOW
        reply = handle_root_authority_request(
            payload, peer=_peer(), state=state,
            snapshot_supplier=lambda: current["snapshot"], now_epoch=now,
        )
        if len(attempts) == 1:
            if invalidation == "revocation":
                revoked = copy.deepcopy(descriptor)
                revoked["authority_generation_sequence"] = 2
                revoked["revoked_authorization_ids"] = [grant["authorization_id"]]
                revoked["descriptor_id"] = descriptor_id_for(revoked)
                current["snapshot"] = _snapshot(revoked, _sha("owner-config-2"), state)
            raise ConnectionResetError("test_commit_reply_lost")
        return reply

    monkeypatch.setattr(client_module, "_root_socket_roundtrip", changing_authority_roundtrip)
    with pytest.raises(ValueError, match="commit_rejected"):
        _commit(authority, reservation, _sha("signature"))
    assert len(attempts) == 2 and attempts[0] == attempts[1]
    committed = state.load(authorization_binding(grant["authorization_id"]))
    assert committed is not None and committed.sequence == 2


@pytest.mark.parametrize("failure", ["server_uid", "response_size", "malformed", "rejected"])
def test_root_commit_recovery_does_not_retry_authority_or_protocol_failures(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str,
) -> None:
    _descriptor_value, grant, state, _primary, _witness, _installation, current, authority = _runtime(tmp_path, monkeypatch)
    reservation = _reserve(authority, grant)
    assert reservation is not None
    attempts = []

    def rejected_roundtrip(_path, payload, _uid, _timeout):
        attempts.append(hashlib.sha256(payload).hexdigest())
        if failure == "server_uid":
            raise OSError("root_authority_server_uid_mismatch")
        if failure == "response_size":
            raise OSError("root_authority_response_size_invalid")
        if failure == "malformed":
            return b"{}"
        return handle_root_authority_request(
            payload, peer=_peer(uid=1002), state=state,
            snapshot_supplier=lambda: current["snapshot"], now_epoch=NOW,
        )

    monkeypatch.setattr(client_module, "_root_socket_roundtrip", rejected_roundtrip)
    with pytest.raises((OSError, ValueError)):
        _commit(authority, reservation, _sha("signature"))
    assert len(attempts) == 1
    burned = state.load(authorization_binding(grant["authorization_id"]))
    assert burned is not None and burned.sequence == 1


def test_root_commit_recovery_preserves_cancellation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _descriptor_value, grant, state, *_rest, authority = _runtime(tmp_path, monkeypatch)
    reservation = _reserve(authority, grant)
    assert reservation is not None
    attempts = []

    def cancelled_roundtrip(_path, payload, _uid, _timeout):
        attempts.append(hashlib.sha256(payload).hexdigest())
        raise KeyboardInterrupt()

    monkeypatch.setattr(client_module, "_root_socket_roundtrip", cancelled_roundtrip)
    with pytest.raises(KeyboardInterrupt):
        _commit(authority, reservation, _sha("signature"))
    assert len(attempts) == 1
    assert state.load(authorization_binding(grant["authorization_id"])).sequence == 1


@pytest.mark.parametrize("after_commit", [False, True], ids=["before", "after"])
def test_root_commit_recovery_transport_retry_is_bounded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, after_commit: bool,
) -> None:
    _descriptor_value, grant, state, *_rest, authority = _runtime(tmp_path, monkeypatch)
    reservation = _reserve(authority, grant)
    assert reservation is not None
    roundtrip, attempts = client_module._root_socket_roundtrip, []

    def failed_roundtrip(path, payload, uid, timeout):
        attempts.append(hashlib.sha256(payload).hexdigest())
        if after_commit:
            roundtrip(path, payload, uid, timeout)
        raise TimeoutError("test_commit_reply_unavailable")

    monkeypatch.setattr(client_module, "_root_socket_roundtrip", failed_roundtrip)
    with pytest.raises(TimeoutError):
        _commit(authority, reservation, _sha("signature"))
    assert len(attempts) == 2 and attempts[0] == attempts[1]
    marker = state.load(authorization_binding(grant["authorization_id"]))
    assert marker is not None and marker.sequence == (2 if after_commit else 1)
    monkeypatch.setattr(client_module, "_root_socket_roundtrip", roundtrip)
    assert _reserve(authority, grant) is None


@pytest.mark.skipif(
    os.name != "posix" or not hasattr(os, "geteuid") or os.geteuid() != 0,
    reason="real root-owned Unix service requires Linux root",
)
def test_real_linux_root_service_accepts_non_root_e0_signer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base = Path(tempfile.mkdtemp(prefix="reddog-root-authority-", dir="/var/lib"))
    try:
        os.chmod(base, 0o755)
        descriptor, grant, _legacy = _descriptor(base / "descriptor")
        state, _primary, _witness, _installation = _state(base, descriptor)
        snapshot = RootAuthoritySnapshot(
            **{
                **_snapshot(descriptor, state=state).__dict__,
                "signer_uid": 65534,
                "signer_gid": 65534,
            }
        )
        initialize_root_authority_state(state, snapshot, now_epoch=NOW)
        socket_root = base / "socket"
        socket_root.mkdir(mode=0o755)
        socket_path = socket_root / "authority.sock"
        monkeypatch.setattr(
            "modules.communication.moltbot_bridge.src."
            "foundup_verified_outcome_root_authority_socket_service._now_epoch",
            lambda: NOW,
        )
        results = []
        server = threading.Thread(
            target=lambda: results.append(
                serve_root_authority_bounded(
                    repo_root=REPO_ROOT,
                    socket_path=socket_path,
                    signer_gid=65534,
                    state=state,
                    snapshot_supplier=lambda: snapshot,
                    peer_attestor=KernelPeerCredentialAttestor(
                        PeerCredentialPolicy(
                            {65534: snapshot.signer_principal_id},
                            allowed_gids=(65534,),
                        )
                    ),
                    max_requests=2,
                    timeout_s=5.0,
                )
            ),
            daemon=True,
        )
        server.start()
        deadline = time.time() + 5
        while not socket_path.exists() and time.time() < deadline:
            time.sleep(0.01)
        read_fd, write_fd = os.pipe()
        child = os.fork()
        if child == 0:
            try:
                os.close(read_fd)
                os.setgid(65534)
                os.setuid(65534)
                exchange = build_root_authority_socket_exchange(
                    repo_root=REPO_ROOT,
                    socket_path=socket_path,
                    expected_server_uid=0,
                )
                authority = _create_service_backed_outcome_authority(
                    descriptor,
                    owner_config_id=snapshot.owner_config_id,
                    exchange=exchange,
                    now_epoch=NOW,
                )
                reservation = _reserve(authority, grant)
                if reservation is not None:
                    _commit(authority, reservation, _sha("linux-signature"))
                    os.write(write_fd, b"PASS")
            finally:
                os.close(write_fd)
                os._exit(0)
        os.close(write_fd)
        child_result = os.read(read_fd, 4)
        os.close(read_fd)
        _pid, child_status = os.waitpid(child, 0)
        server.join(timeout=10)
        assert child_status == 0
        assert child_result == b"PASS"
        assert len(results) == 1 and results[0].accepted is True
        assert results[0].requests_handled == 2
    finally:
        shutil.rmtree(base, ignore_errors=True)


def test_concurrent_root_service_reservation_has_one_winner(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _descriptor_value, grant, _state_value, *_rest, authority = _runtime(
        tmp_path, monkeypatch
    )
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = tuple(pool.map(lambda _item: _reserve(authority, grant), range(8)))
    assert sum(item is not None for item in results) == 1


def test_cross_process_root_state_reservation_has_one_winner(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from modules.communication.moltbot_bridge.tests.test_foundup_verified_outcome_root_authority_service import (
        _advance_root_state_process as advance_in_child,
    )
    descriptor, grant, *_rest = _runtime(tmp_path, monkeypatch)
    values = (str(tmp_path), descriptor, authorization_binding(grant["authorization_id"]))
    with ProcessPoolExecutor(max_workers=4) as pool:
        results = tuple(pool.map(advance_in_child, (values,) * 8))
    assert sum(results) == 1


def test_revocation_between_reserve_and_commit_burns_grant(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    descriptor, grant, state, _primary, _witness, _installation, current, authority = _runtime(
        tmp_path, monkeypatch
    )
    reservation = _reserve(authority, grant)
    assert reservation is not None
    revoked = copy.deepcopy(descriptor)
    revoked["authority_generation_sequence"] = 2
    revoked["revoked_authorization_ids"] = [grant["authorization_id"]]
    revoked["descriptor_id"] = descriptor_id_for(revoked)
    current["snapshot"] = _snapshot(revoked, _sha("owner-config-2"), state)

    with pytest.raises(ValueError, match="commit_rejected"):
        _commit(authority, reservation, _sha("signature"))
    burned = state.load(authorization_binding(grant["authorization_id"]))
    assert burned is not None and burned.sequence == 1


def test_authority_generation_rollback_rejects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    descriptor, grant, state, *_rest, current, authority = _runtime(
        tmp_path, monkeypatch
    )
    advanced = copy.deepcopy(descriptor)
    advanced["authority_generation_sequence"] = 2
    advanced["descriptor_id"] = descriptor_id_for(advanced)
    current["snapshot"] = _snapshot(advanced, _sha("owner-config-2"), state)
    assert _reserve(authority, grant) is None
    current["snapshot"] = _snapshot(descriptor, state=state)
    assert _reserve(authority, grant) is None


def test_invalid_descriptor_cannot_advance_generation_fence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    descriptor, _grant, state, *_rest = _runtime(tmp_path, monkeypatch)
    advanced = copy.deepcopy(descriptor)
    advanced["authority_generation_sequence"] = 2
    advanced["descriptor_id"] = descriptor_id_for(advanced)
    invalid = copy.deepcopy(advanced)
    invalid["schema_version"] = "attacker-schema"
    invalid["descriptor_id"] = descriptor_id_for(invalid)
    owner_config_id = _sha("owner-config-2")

    with pytest.raises(ValueError):
        _current_snapshot(
            state,
            snapshot_supplier=lambda: _snapshot(invalid, owner_config_id, state),
            now_epoch=NOW,
        )

    accepted = _current_snapshot(
        state,
        snapshot_supplier=lambda: _snapshot(advanced, owner_config_id, state),
        now_epoch=NOW,
    )
    assert accepted.authority_generation_sequence == 2


def test_rotated_state_binding_rejects_before_generation_fence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    descriptor, _grant, state, *_rest = _runtime(tmp_path, monkeypatch)
    advanced = copy.deepcopy(descriptor)
    advanced["authority_generation_sequence"] = 2
    advanced["descriptor_id"] = descriptor_id_for(advanced)
    snapshot = _snapshot(advanced, _sha("owner-config-2"), state)
    snapshot = RootAuthoritySnapshot(
        **{**snapshot.__dict__, "state_binding_digest": _sha("rotated-state")}
    )

    with pytest.raises(ValueError, match="snapshot_binding_invalid"):
        _current_snapshot(
            state, snapshot_supplier=lambda: snapshot, now_epoch=NOW
        )
    assert state.load(GENERATION_BINDING).sequence == 1


def test_wrong_kernel_peer_rejects_before_state_change(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    descriptor, grant, state, *_rest = _runtime(tmp_path, monkeypatch)
    snapshot = _snapshot(descriptor, state=state)
    good_authority = _client_authority(
        monkeypatch,
        descriptor,
        snapshot.owner_config_id,
        lambda raw: handle_root_authority_request(
            raw,
            peer=_peer("attacker"),
            state=state,
            snapshot_supplier=lambda: snapshot,
            now_epoch=NOW,
        ),
    )
    assert _reserve(good_authority, grant) is None
    assert state.load(authorization_binding(grant["authorization_id"])) is None


@pytest.mark.parametrize("peer", (_peer(uid=2002), _peer(gid=2002)))
def test_rotated_signer_uid_or_gid_rejects_current_request(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, peer: KernelPeerIdentity
) -> None:
    descriptor, grant, state, *_rest = _runtime(tmp_path, monkeypatch)
    snapshot = _snapshot(descriptor, state=state)
    authority = _client_authority(
        monkeypatch,
        descriptor,
        snapshot.owner_config_id,
        lambda raw: handle_root_authority_request(
            raw, peer=peer, state=state,
            snapshot_supplier=lambda: snapshot, now_epoch=NOW,
        ),
    )
    assert _reserve(authority, grant) is None
    assert state.load(authorization_binding(grant["authorization_id"])) is None


def test_same_uid_process_without_e0_key_cannot_reserve(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    descriptor, grant, state, *_rest, authority = _runtime(tmp_path, monkeypatch)
    values = {
        "receipt_id": grant["receipt_id"], "work_order_id": grant["work_order_id"],
        "evidence_digest": grant["evidence_digest"], "issued_at": NOW,
    }
    proof_input = authority.reserve_proof_input(**values)
    values["signer_instance_signature"] = _sign(_private_key(), proof_input)
    assert authority.reserve(**values) is None
    assert state.load(authorization_binding(grant["authorization_id"])) is None


def test_same_uid_process_cannot_false_commit_reserved_grant(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _descriptor_value, grant, state, *_rest, authority = _runtime(
        tmp_path, monkeypatch
    )
    reservation = _reserve(authority, grant)
    assert reservation is not None
    signature_digest = _sha("signature")
    forged = _sign(
        _private_key(), authority.commit_proof_input(reservation, signature_digest)
    )
    with pytest.raises(ValueError, match="commit_rejected"):
        authority.commit(reservation, signature_digest, forged)
    burned = state.load(authorization_binding(grant["authorization_id"]))
    assert burned is not None and burned.sequence == 1


def test_response_substitution_rejects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    descriptor, grant, _legacy_store = _descriptor(tmp_path / "descriptor")

    def substituted(raw: bytes) -> bytes:
        request = request_from_bytes(raw)
        return RootAuthorityResponse(
            status="ACCEPT",
            request_id=_sha("attacker-request"),
            descriptor_id=request.descriptor_id,
            owner_config_id=request.owner_config_id,
            authorization_id=request.authorization_id,
            reservation_id=_sha("attacker-reservation"),
            state="RESERVED_BURNED",
        ).to_bytes()

    authority = _client_authority(
        monkeypatch,
        descriptor,
        _sha("owner-config"),
        substituted,
    )
    assert _reserve(authority, grant) is None


@pytest.mark.parametrize("lost_side", ["primary", "witness"])
@pytest.mark.parametrize("sequence", [1, 2, 5])
def test_one_sided_state_loss_repairs_from_witness(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, lost_side: str, sequence: int,
) -> None:
    descriptor, _grant, state, primary, witness, installation, *_rest = _runtime(
        tmp_path, monkeypatch
    )
    binding = descriptor["replay_anchor_binding_digest"]
    expected = state.load(binding)
    for number in range(2, sequence + 1):
        next_value = ProposalReplayHighWater(number, str(number) * 64)
        state.advance(binding, expected=expected, next_value=next_value)
        expected = next_value
    missing = primary if lost_side == "primary" else witness
    missing.path.unlink()
    restored = SqliteMonotonicAuthorityStore(
        missing.path,
        allowed_root=missing.rollback_domain_root,
        repo_root=REPO_ROOT,
        store_id=missing.store_id,
        durability_receipt_id=missing.durability_receipt_id,
    )
    repaired = RootVerifiedOutcomeAuthorityState(
        restored if lost_side == "primary" else primary,
        restored if lost_side == "witness" else witness,
        installation,
        repo_root=REPO_ROOT,
        require_root_ownership=False,
    )
    assert repaired.load(binding) == expected
    assert restored.load(binding) == expected


def test_primary_commit_crash_repairs_exact_one_step_from_witness(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    descriptor, _grant, state, primary, witness, _installation, *_rest = _runtime(
        tmp_path, monkeypatch
    )
    binding = descriptor["replay_anchor_binding_digest"]
    current = state.load(binding)
    assert current is not None
    wanted = ProposalReplayHighWater(current.sequence + 1, "b" * 64)
    original = witness.advance
    monkeypatch.setattr(
        witness, "advance", lambda *_args, **_kwargs: (_ for _ in ()).throw(
            RuntimeError("simulated_witness_crash")
        ),
    )
    with pytest.raises(RuntimeError, match="simulated_witness_crash"):
        state.advance(binding, expected=current, next_value=wanted)
    monkeypatch.setattr(witness, "advance", original)
    assert primary.load(binding) == wanted
    assert state.load(binding) == wanted
    assert witness.load(binding) == wanted


def test_consumed_grant_rejects_after_both_state_files_are_reset(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (
        descriptor,
        grant,
        _state_value,
        primary,
        witness,
        installation,
        current,
        authority,
    ) = _runtime(
        tmp_path, monkeypatch
    )
    reservation = _reserve(authority, grant)
    assert reservation is not None
    _commit(authority, reservation, _sha("signature"))
    primary.path.unlink()
    witness.path.unlink()
    reset_primary, reset_witness, _reset_installation = _stores(
        tmp_path, descriptor
    )
    reset_state = RootVerifiedOutcomeAuthorityState(
        reset_primary,
        reset_witness,
        installation,
        repo_root=REPO_ROOT,
        require_root_ownership=False,
    )
    reset_authority = _client_authority(
        monkeypatch, descriptor, current["snapshot"].owner_config_id,
        lambda raw: handle_root_authority_request(
            raw, peer=_peer(), state=reset_state,
            snapshot_supplier=lambda: current["snapshot"], now_epoch=NOW,
        ),
    )
    assert _reserve(reset_authority, grant) is None
    assert reset_state.load(authorization_binding(grant["authorization_id"])) is None


def test_dual_store_reset_cannot_reinitialize_consumed_grant(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (
        descriptor,
        grant,
        _state_value,
        primary,
        witness,
        installation,
        current,
        authority,
    ) = _runtime(tmp_path, monkeypatch)
    reservation = _reserve(authority, grant)
    assert reservation is not None
    _commit(authority, reservation, _sha("signature"))
    primary.path.unlink()
    witness.path.unlink()
    reset_primary, reset_witness, _unused = _stores(tmp_path, descriptor)
    reset_state = RootVerifiedOutcomeAuthorityState(
        reset_primary,
        reset_witness,
        installation,
        repo_root=REPO_ROOT,
        require_root_ownership=False,
    )
    with pytest.raises(ValueError, match="already_initialized"):
        initialize_root_authority_state(
            reset_state, current["snapshot"], now_epoch=NOW
        )


def test_production_state_rejects_non_root_principal(tmp_path: Path) -> None:
    descriptor, _grant, _legacy_store = _descriptor(tmp_path / "descriptor")
    primary, witness, installation = _stores(tmp_path, descriptor)
    if __import__("os").name == "posix" and __import__("os").geteuid() == 0:
        pytest.skip("test runner is root")
    with pytest.raises(ValueError, match="service_principal_invalid"):
        RootVerifiedOutcomeAuthorityState(
            primary,
            witness,
            installation,
            repo_root=REPO_ROOT,
            require_root_ownership=True,
        )


def test_world_writable_root_ancestor_rejects(monkeypatch: pytest.MonkeyPatch) -> None:
    safe_mode = stat.S_IFDIR | 0o755
    unsafe_mode = stat.S_IFDIR | 0o777

    class FakePath:
        def __init__(self, name: str, mode: int, parents=()) -> None:
            self.name = name
            self.mode = mode
            self.parents = parents

        def lstat(self):
            return SimpleNamespace(st_mode=self.mode, st_uid=0)

        def is_symlink(self) -> bool:
            return False

    unsafe = FakePath("unsafe", unsafe_mode)
    leaf = FakePath("leaf", safe_mode, (unsafe,))
    monkeypatch.setattr(state_module.os, "name", "posix")
    monkeypatch.setattr(state_module.os, "geteuid", lambda: 0, raising=False)
    with pytest.raises(ValueError, match="state_root_invalid"):
        state_module._require_root_owned(leaf)


def test_local_authority_mint_is_not_public_api() -> None:
    assert "create_root_verified_outcome_signing_authority" not in authority_module.__all__
    assert not hasattr(
        authority_module, "create_root_verified_outcome_signing_authority"
    )
    assert not hasattr(authority_module, "_create_process_local_test_outcome_authority")


def test_non_root_exchange_cannot_mint_authority(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    descriptor, _grant, _legacy_store = _descriptor(tmp_path / "descriptor")
    monkeypatch.setattr(client_module, "_require_protected_socket", lambda *_args: None)
    exchange = build_root_authority_socket_exchange(
        repo_root=REPO_ROOT,
        socket_path="C:/non-root-authority-test.sock",
        expected_server_uid=1001,
    )
    with pytest.raises(ValueError, match="service_uid_invalid"):
        _create_service_backed_outcome_authority(
            descriptor,
            owner_config_id=_sha("owner-config"),
            exchange=exchange,
            now_epoch=NOW,
        )


@pytest.fixture
def record_commit_inputs(tmp_path, monkeypatch):
    from modules.communication.moltbot_bridge.tests.test_reddog_ed25519_verified_outcome_signing import (
        _pending_response_inputs,
    )
    return _pending_response_inputs(tmp_path, monkeypatch)


def _record_commit_request(values, raw=None, digest=None, **changes):
    raw, digest = (values.raw if raw is None else raw), (values.digest if digest is None else digest)
    request = client_module._response_record_request(
        values.authority, values.reservation, raw, digest, client_module._placeholder_signature(),
    )
    request = replace(request, **changes)
    from modules.communication.moltbot_bridge.tests.test_foundup_verified_outcome_root_authority import _SIGNER_KEYS
    signature = _sign(_SIGNER_KEYS[values.request.signer_public_key],
                      protocol.canonical_signer_instance_input(request))
    request = replace(request, signer_instance_signature=signature)
    return replace(request, request_id=protocol.request_id_for(asdict(request)))


def _record_reply(values, request, **overrides):
    from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_authority_router import (
        handle_root_authority_wire_request,
    )
    arguments = dict(peer=_peer(), state=values.state, now_epoch=NOW,
                     snapshot_supplier=lambda: values.current["snapshot"], revocation_authority=None)
    arguments.update(overrides)
    return handle_root_authority_wire_request(request.to_bytes(), **arguments)


@pytest.mark.parametrize("already_pending", [False, True])
def test_full_record_commit_stores_exact_bytes_before_terminal_ack(record_commit_inputs, already_pending):
    v = record_commit_inputs
    if already_pending:
        v.state.persist_pending_response(v.raw, expected_binding=v.binding,
                                         expected_record_digest=v.digest, now_epoch=NOW)
    request = _record_commit_request(v)
    assert client_module.commit_service_response_record_proof_input(
        v.authority, v.reservation, v.raw, v.digest,
    ) == protocol.canonical_signer_instance_input(request)
    assert client_module.commit_service_response_record(
        v.authority, v.reservation, v.raw, v.digest, request.signer_instance_signature,
    ) == v.digest
    assert v.state.load(authorization_binding(v.grant["authorization_id"])) == ProposalReplayHighWater(2, v.digest[7:])
    assert v.store.load()["records"] == {v.grant["authorization_id"]: v.raw.decode("ascii")}
    original = v.path.read_bytes()
    assert protocol.record_commit_response_from_bytes(_record_reply(v, request)).accepted
    assert v.path.read_bytes() == original and v.counts["outcome_signatures"] == 1
    assert _reserve(v.authority, v.grant) is None
    with pytest.raises(ValueError, match="commit_rejected"):
        _commit(v.authority, v.reservation, _sha("v1-signature"))
    with pytest.raises(RuntimeError, match="context_conflict"):
        v.state.persist_pending_response(v.raw, expected_binding=v.binding,
                                         expected_record_digest=v.digest, now_epoch=NOW)


def test_full_record_commit_keeps_v1_codec_and_proof_domain_separate(record_commit_inputs):
    v = record_commit_inputs
    first = v.reservation.request
    raw_v1 = first.to_bytes()
    assert decode_message(raw_v1) == {"schema_version": protocol.SCHEMA_VERSION, **asdict(first)}
    assert request_from_bytes(raw_v1) == first
    v2 = _record_commit_request(v)
    assert protocol.record_commit_request_from_bytes(v2.to_bytes()) == v2
    assert protocol.canonical_signer_instance_input(first).startswith(protocol.SIGNER_PROOF_PREFIX)
    assert protocol.canonical_signer_instance_input(v2).startswith(protocol.RECORD_COMMIT_PROOF_PREFIX)
    with pytest.raises(ValueError):
        request_from_bytes(v2.to_bytes())
    with pytest.raises(ValueError):
        protocol.record_commit_request_from_bytes(raw_v1)
    reply = _record_reply(v, v2)
    with pytest.raises(ValueError):
        protocol.response_from_bytes(reply)


@pytest.mark.parametrize("mutation", ["schema", "operation", "extra", "missing", "duplicate", "noncanonical", "id", "raw-type", "signature-digest", "issued-bool"])
def test_full_record_commit_rejects_malformed_wire_before_state(record_commit_inputs, mutation):
    v = record_commit_inputs
    request = _record_commit_request(v)
    data = decode_message(request.to_bytes())
    if mutation == "schema": data["schema_version"] = protocol.SCHEMA_VERSION
    elif mutation == "operation": data["operation"] = protocol.OP_COMMIT
    elif mutation == "extra": data["read_authority"] = "untrusted"
    elif mutation == "missing": data.pop("response_record")
    elif mutation == "id": data["request_id"] = _sha("other-request")
    elif mutation == "raw-type": data["response_record"] = {}
    elif mutation == "signature-digest": data["signature_digest"] = _sha("signature")
    elif mutation == "issued-bool": data["issued_at"] = True
    raw = encode_message(data)
    if mutation == "duplicate": raw = b'{"record_digest":"duplicate",' + raw[1:]
    elif mutation == "noncanonical": raw = b" " + raw
    before = v.state.load(authorization_binding(v.grant["authorization_id"]))
    with pytest.raises(ValueError):
        protocol.record_commit_request_from_bytes(raw)
    assert handle_root_authority_request(raw, peer=_peer(), state=v.state,
        snapshot_supplier=lambda: v.current["snapshot"], now_epoch=NOW) == b'{"status":"REJECT"}\n'
    assert not v.path.exists()
    assert v.state.load(authorization_binding(v.grant["authorization_id"])) == before


@pytest.mark.parametrize("after_commit", [False, True])
@pytest.mark.parametrize("fault", ["uid", "gid", "owner", "revocation", "expiry", "proof", "record-digest", "record-tamper", "issued-at", "reservation"])
def test_full_record_commit_requires_current_peer_proof_and_exact_record(record_commit_inputs, fault, after_commit):
    v = record_commit_inputs
    if after_commit:
        assert protocol.record_commit_response_from_bytes(_record_reply(v, _record_commit_request(v))).accepted
    original = v.path.read_bytes() if v.path.exists() else None
    changes, overrides = {}, {}
    if fault == "uid": overrides["peer"] = _peer(uid=1002)
    elif fault == "gid": overrides["peer"] = _peer(gid=1002)
    elif fault == "expiry": overrides["now_epoch"] = int(v.grant["expires_at"])
    elif fault == "owner": v.current["snapshot"] = replace(v.current["snapshot"], owner_config_id=_sha("changed-owner"))
    elif fault == "revocation":
        descriptor = copy.deepcopy(v.descriptor)
        descriptor["revoked_authorization_ids"] = [v.grant["authorization_id"]]
        descriptor["descriptor_id"] = descriptor_id_for(descriptor)
        v.current["snapshot"] = replace(v.current["snapshot"], descriptor=descriptor)
    elif fault == "record-digest": changes["record_digest"] = _sha("other-record")
    elif fault == "record-tamper": changes["response_record"] = v.raw.decode("ascii").replace('"accepted":true', '"accepted":false')
    elif fault == "issued-at": changes["issued_at"] = NOW + 1
    elif fault == "reservation": changes["reservation_id"] = _sha("other-reservation")
    request = _record_commit_request(v, **changes)
    if fault == "proof":
        request = replace(request, signer_instance_signature=_sign(_private_key(), "wrong-domain"))
        request = replace(request, request_id=protocol.request_id_for(asdict(request)))
    before = v.state.load(authorization_binding(v.grant["authorization_id"]))
    assert not protocol.record_commit_response_from_bytes(_record_reply(v, request, **overrides)).accepted
    assert v.state.load(authorization_binding(v.grant["authorization_id"])) == before
    assert (v.path.read_bytes() if v.path.exists() else None) == original


def test_full_record_commit_rejects_different_valid_response(record_commit_inputs):
    from modules.communication.moltbot_bridge.tests.test_reddog_ed25519_verified_outcome_signing import _alternate_pending_response
    v = record_commit_inputs
    request = _record_commit_request(v)
    assert protocol.record_commit_response_from_bytes(_record_reply(v, request)).accepted
    original = v.path.read_bytes()
    other_raw, other_digest = _alternate_pending_response(v)
    other = _record_commit_request(v, other_raw, other_digest)
    assert not protocol.record_commit_response_from_bytes(_record_reply(v, other)).accepted
    assert v.path.read_bytes() == original
    assert v.state.load(authorization_binding(v.grant["authorization_id"])) == ProposalReplayHighWater(2, v.digest[7:])


def test_full_record_commit_cannot_replace_v1_terminal_state(record_commit_inputs):
    v = record_commit_inputs
    _commit(v.authority, v.reservation, _sha("v1-signature"))
    before = v.state.load(authorization_binding(v.grant["authorization_id"]))
    assert not protocol.record_commit_response_from_bytes(_record_reply(v, _record_commit_request(v))).accepted
    assert not v.path.exists() and v.state.load(authorization_binding(v.grant["authorization_id"])) == before


def test_full_record_commit_lost_ack_has_no_hidden_retry_and_explicit_retry_is_exact(record_commit_inputs, monkeypatch):
    v = record_commit_inputs
    request = _record_commit_request(v)
    attempts = []
    def lost_ack(_path, raw, _uid, _timeout):
        attempts.append(raw)
        reply = _record_reply(v, protocol.record_commit_request_from_bytes(raw))
        if len(attempts) == 1: raise ConnectionResetError("fixture_lost_reply")
        return reply
    monkeypatch.setattr(client_module, "_root_socket_roundtrip", lost_ack)
    with pytest.raises(ConnectionResetError):
        client_module.commit_service_response_record(v.authority, v.reservation, v.raw, v.digest, request.signer_instance_signature)
    assert len(attempts) == 1
    assert client_module.commit_service_response_record(v.authority, v.reservation, v.raw, v.digest, request.signer_instance_signature) == v.digest
    assert attempts[0] == attempts[1] and v.counts["outcome_signatures"] == 1


@pytest.mark.parametrize("fault", ["write", "terminal-mirror", "cancel-after-persist"])
def test_full_record_commit_recovers_incomplete_write_without_reopening_grant(record_commit_inputs, monkeypatch, fault):
    v = record_commit_inputs
    request = _record_commit_request(v)
    original_commit = state_module.AtomicJsonAuthorityRuntimeStore.commit
    original_advance = v.state._advance_pair
    def broken_store(*args, **kwargs): raise OSError("fixture_before_write")
    def interrupted_advance(binding, expected, next_value):
        if binding == authorization_binding(v.grant["authorization_id"]):
            if fault == "cancel-after-persist": raise SystemExit("fixture_cancel")
            v.state._primary.advance(binding, expected=expected, next_value=next_value)
            raise RuntimeError("fixture_terminal_witness_missing")
        return original_advance(binding, expected, next_value)
    if fault == "write": monkeypatch.setattr(state_module.AtomicJsonAuthorityRuntimeStore, "commit", broken_store)
    else: monkeypatch.setattr(v.state, "_advance_pair", interrupted_advance)
    if fault == "cancel-after-persist":
        with pytest.raises(SystemExit): _record_reply(v, request)
        assert v.path.exists()
    else:
        assert not protocol.record_commit_response_from_bytes(_record_reply(v, request)).accepted
    marker = v.state.load(authorization_binding(v.grant["authorization_id"]))
    assert marker.sequence == (2 if fault == "terminal-mirror" else 1)
    monkeypatch.setattr(state_module.AtomicJsonAuthorityRuntimeStore, "commit", original_commit)
    monkeypatch.setattr(v.state, "_advance_pair", original_advance)
    assert protocol.record_commit_response_from_bytes(_record_reply(v, request)).accepted
    assert v.store.load()["records"][v.grant["authorization_id"]] == v.raw.decode("ascii")
    assert v.counts["outcome_signatures"] == 1 and _reserve(v.authority, v.grant) is None


def test_full_record_commit_concurrent_state_instances_preserve_one_valid_winner(record_commit_inputs, tmp_path):
    from modules.communication.moltbot_bridge.tests.test_reddog_ed25519_verified_outcome_signing import _alternate_pending_response
    v = record_commit_inputs
    other_raw, other_digest = _alternate_pending_response(v)
    candidates = [_record_commit_request(v), _record_commit_request(v, other_raw, other_digest)]
    second, *_stores_value = _state(tmp_path, v.descriptor)
    barrier = threading.Barrier(2)
    def compete(index):
        barrier.wait()
        return protocol.record_commit_response_from_bytes(_record_reply(v, candidates[index], state=[v.state, second][index]))
    with ThreadPoolExecutor(max_workers=2) as executor:
        replies = list(executor.map(compete, [0, 1]))
    assert sum(reply.accepted for reply in replies) == 1
    winner = next(reply.record_digest for reply in replies if reply.accepted)
    assert v.state.load(authorization_binding(v.grant["authorization_id"])) == ProposalReplayHighWater(2, winner[7:])
    stored = v.store.load()["records"][v.grant["authorization_id"]]
    assert decode_message(stored.encode("ascii"))["record_digest"] == winner


@pytest.mark.parametrize("loss", ["restart", "primary", "witness", "payload", "both-mirrors", "corrupt-payload"])
def test_full_record_commit_retry_requires_durable_binding_and_exact_retained_bytes(record_commit_inputs, tmp_path, loss):
    v = record_commit_inputs
    request = _record_commit_request(v)
    assert protocol.record_commit_response_from_bytes(_record_reply(v, request)).accepted
    if loss in {"primary", "both-mirrors"}: v.state._primary.path.unlink()
    if loss in {"witness", "both-mirrors"}: v.state._witness.path.unlink()
    if loss == "payload": v.path.unlink()
    if loss == "corrupt-payload": v.path.write_bytes(b'{"untrusted":true}\n')
    state, *_rest = _state(tmp_path, v.descriptor)
    reply = protocol.record_commit_response_from_bytes(_record_reply(v, request, state=state))
    assert reply.accepted is (loss not in {"both-mirrors", "corrupt-payload"})
    if reply.accepted:
        assert state.load(authorization_binding(v.grant["authorization_id"])) == ProposalReplayHighWater(2, v.digest[7:])
        assert v.store.load()["records"][v.grant["authorization_id"]] == v.raw.decode("ascii")
    assert v.counts["outcome_signatures"] == 1


def test_full_record_commit_bounds_enclosing_wire_before_proof_or_persistence(record_commit_inputs):
    from modules.communication.moltbot_bridge.tests.test_reddog_ed25519_verified_outcome_signing import _alternate_pending_response
    v = record_commit_inputs
    base_size = len(_record_commit_request(v).to_bytes())
    exact_raw, exact_digest = _alternate_pending_response(v, "x" * (protocol.MAX_MESSAGE_BYTES - base_size))
    request = _record_commit_request(v, exact_raw, exact_digest)
    assert len(request.to_bytes()) == protocol.MAX_MESSAGE_BYTES
    too_large, too_large_digest = _alternate_pending_response(v, "x" * (protocol.MAX_MESSAGE_BYTES - base_size + 1))
    assert len(too_large) < protocol.MAX_MESSAGE_BYTES  # Inner record alone still fits.
    with pytest.raises(ValueError, match="message_too_large"):
        client_module.commit_service_response_record_proof_input(v.authority, v.reservation, too_large, too_large_digest)
    assert not v.path.exists()
    assert protocol.record_commit_response_from_bytes(_record_reply(v, request)).accepted


@pytest.mark.parametrize("mutation", ["v1", "digest", "request", "reservation", "rejected", "noncanonical"])
def test_full_record_commit_client_rejects_substituted_ack_without_retry(record_commit_inputs, monkeypatch, mutation):
    v = record_commit_inputs
    request = _record_commit_request(v)
    attempts = []
    def substituted(_path, raw, _uid, _timeout):
        attempts.append(raw)
        data = decode_message(_record_reply(v, protocol.record_commit_request_from_bytes(raw)))
        if mutation == "v1":
            data["schema_version"] = protocol.SCHEMA_VERSION
            data.pop("record_digest")
        elif mutation == "digest": data["record_digest"] = _sha("other")
        elif mutation == "request": data["request_id"] = _sha("other")
        elif mutation == "reservation": data["reservation_id"] = _sha("other")
        elif mutation == "rejected":
            data.update(status="REJECT", state="REJECTED", reason="fixture_reject", reservation_id=None, record_digest="")
        reply = encode_message(data)
        return b" " + reply if mutation == "noncanonical" else reply
    monkeypatch.setattr(client_module, "_root_socket_roundtrip", substituted)
    with pytest.raises(ValueError):
        client_module.commit_service_response_record(v.authority, v.reservation, v.raw, v.digest, request.signer_instance_signature)
    assert len(attempts) == 1
    assert v.state.load(authorization_binding(v.grant["authorization_id"])) == ProposalReplayHighWater(2, v.digest[7:])


def test_full_record_commit_requires_original_process_reservation_before_exchange(record_commit_inputs):
    v = record_commit_inputs
    forged = replace(v.reservation, seal=object())
    with pytest.raises(ValueError, match="reservation_invalid"):
        client_module.commit_service_response_record_proof_input(v.authority, forged, v.raw, v.digest)
    assert not v.path.exists()


def _read_root_record(values, **overrides):
    arguments = dict(
        expected_binding=values.binding, expected_record_digest=values.digest,
        expected_generation=ProposalReplayHighWater(
            values.descriptor["authority_generation_sequence"], values.binding.owner_config_id[7:],
        ), now_epoch=NOW,
    )
    arguments.update(overrides)
    return values.state.load_committed_response_for_root(**arguments)


def test_root_record_read_returns_exact_commit_without_resigning(record_commit_inputs, tmp_path):
    v = record_commit_inputs
    assert protocol.record_commit_response_from_bytes(_record_reply(v, _record_commit_request(v))).accepted
    original = v.path.read_bytes()
    committed = v.state.load(authorization_binding(v.grant["authorization_id"]))
    assert _read_root_record(v) == v.raw
    v.state, *_stores_value = _state(tmp_path, v.descriptor)
    assert _read_root_record(v) == v.raw
    assert v.path.read_bytes() == original
    assert v.state.load(authorization_binding(v.grant["authorization_id"])) == committed
    assert v.counts["outcome_signatures"] == 1 and _reserve(v.authority, v.grant) is None


@pytest.mark.parametrize("pending", [False, True], ids=["signed-only", "pending-only"])
def test_root_record_read_never_discloses_uncommitted_bytes(record_commit_inputs, pending):
    v = record_commit_inputs
    if pending:
        v.state.persist_pending_response(v.raw, expected_binding=v.binding,
                                        expected_record_digest=v.digest, now_epoch=NOW)
    original = v.path.read_bytes() if pending else None
    with pytest.raises((ValueError, RuntimeError)):
        _read_root_record(v)
    assert (v.path.read_bytes() if v.path.exists() else None) == original
    assert v.state.load(authorization_binding(v.grant["authorization_id"])).sequence == 1


@pytest.mark.parametrize("field", ["descriptor_id", "owner_config_id", "authorization_id", "reservation_id"])
def test_root_record_read_rejects_each_foreign_binding(record_commit_inputs, field):
    v = record_commit_inputs
    assert protocol.record_commit_response_from_bytes(_record_reply(v, _record_commit_request(v))).accepted
    original = v.path.read_bytes()
    changed = "verified-outcome-authorization-" + "a" * 32 if field == "authorization_id" else _sha("other")
    with pytest.raises((ValueError, RuntimeError)):
        _read_root_record(v, expected_binding=replace(v.binding, **{field: changed}))
    assert v.path.read_bytes() == original and v.counts["outcome_signatures"] == 1


@pytest.mark.parametrize("fault", ["digest", "sequence", "revision", "bool-generation", "float-generation",
                                  "missing-generation", "expired", "bool-clock", "before-issuance"])
def test_root_record_read_requires_exact_generation_digest_and_time(record_commit_inputs, fault):
    v = record_commit_inputs
    assert protocol.record_commit_response_from_bytes(_record_reply(v, _record_commit_request(v))).accepted
    sequence, revision = v.descriptor["authority_generation_sequence"], v.binding.owner_config_id[7:]
    arguments = {
        "digest": {"expected_record_digest": _sha("other")},
        "sequence": {"expected_generation": ProposalReplayHighWater(sequence + 1, revision)},
        "revision": {"expected_generation": ProposalReplayHighWater(sequence, "a" * 64)},
        "bool-generation": {"expected_generation": ProposalReplayHighWater(True, revision)},
        "float-generation": {"expected_generation": ProposalReplayHighWater(float(sequence), revision)},
        "missing-generation": {"expected_generation": None},
        "expired": {"now_epoch": v.descriptor["expires_at"]},
        "bool-clock": {"now_epoch": True}, "before-issuance": {"now_epoch": 0},
    }[fault]
    with pytest.raises((ValueError, RuntimeError)):
        _read_root_record(v, **arguments)
    assert v.state.load(authorization_binding(v.grant["authorization_id"])) == ProposalReplayHighWater(2, v.digest[7:])


@pytest.mark.parametrize("current_pin", [False, True], ids=["historical-pin", "new-generation-pin"])
def test_root_record_read_does_not_turn_generation_rotation_into_read_authority(record_commit_inputs, current_pin):
    v = record_commit_inputs
    assert protocol.record_commit_response_from_bytes(_record_reply(v, _record_commit_request(v))).accepted
    next_generation = ProposalReplayHighWater(v.descriptor["authority_generation_sequence"] + 1, _sha("new-owner")[7:])
    v.state.observe_generation(next_generation.sequence, "sha256:" + next_generation.state_revision)
    arguments = {"expected_generation": next_generation} if current_pin else {}
    with pytest.raises(RuntimeError, match="committed_response_context_conflict"):
        _read_root_record(v, **arguments)
    assert v.counts["outcome_signatures"] == 1


@pytest.mark.parametrize("loss", ["primary", "witness"])
def test_root_record_read_uses_existing_one_sided_mirror_recovery(record_commit_inputs, tmp_path, loss):
    v = record_commit_inputs
    assert protocol.record_commit_response_from_bytes(_record_reply(v, _record_commit_request(v))).accepted
    getattr(v.state, "_" + loss).path.unlink()
    v.state, *_stores_value = _state(tmp_path, v.descriptor)
    assert _read_root_record(v) == v.raw
    binding = authorization_binding(v.grant["authorization_id"])
    assert v.state._primary.load(binding) == v.state._witness.load(binding) == ProposalReplayHighWater(2, v.digest[7:])


@pytest.mark.parametrize("fault", ["payload-missing", "corrupt-payload", "different-valid-record",
                                  "selection-missing", "terminal-changed", "both-mirrors"])
def test_root_record_read_rejects_missing_or_conflicting_durable_evidence(record_commit_inputs, tmp_path, fault):
    from modules.communication.moltbot_bridge.tests.test_reddog_ed25519_verified_outcome_signing import _alternate_pending_response
    v = record_commit_inputs
    assert protocol.record_commit_response_from_bytes(_record_reply(v, _record_commit_request(v))).accepted
    if fault == "payload-missing": v.path.unlink()
    elif fault == "corrupt-payload": v.path.write_bytes(b'{"untrusted":true}\n')
    elif fault == "different-valid-record":
        other_raw, _digest = _alternate_pending_response(v)
        snapshot = v.store.load()
        v.store.commit(state_module._pending_response_snapshot({v.grant["authorization_id"]: other_raw.decode("ascii")}),
                       expected_revision=snapshot["revision"])
    elif fault == "selection-missing":
        for store in (v.state._primary, v.state._witness):
            with store._connect() as connection:
                connection.execute("DELETE FROM high_water WHERE binding_digest = ?",
                                   (state_module.pending_response_binding(v.grant["authorization_id"]),))
                connection.commit()
    elif fault == "terminal-changed":
        v.state.advance(authorization_binding(v.grant["authorization_id"]),
                        expected=ProposalReplayHighWater(2, v.digest[7:]), next_value=ProposalReplayHighWater(3, "a" * 64))
    else:
        v.state._primary.path.unlink()
        v.state._witness.path.unlink()
        v.state, *_stores_value = _state(tmp_path, v.descriptor)
    original = v.path.read_bytes() if v.path.exists() else None
    with pytest.raises((ValueError, RuntimeError)):
        _read_root_record(v)
    assert (v.path.read_bytes() if v.path.exists() else None) == original and v.counts["outcome_signatures"] == 1


def test_root_record_read_requires_owner_before_loading_payload(record_commit_inputs, monkeypatch):
    v = record_commit_inputs
    assert protocol.record_commit_response_from_bytes(_record_reply(v, _record_commit_request(v))).accepted
    loads = []
    def deny_owner(): raise ValueError("fixture_root_owner_changed")
    def observe_load(_store): loads.append(True); raise AssertionError("payload read before owner")
    monkeypatch.setattr(v.state, "_require_current_ownership", deny_owner)
    monkeypatch.setattr(state_module.AtomicJsonAuthorityRuntimeStore, "load", observe_load)
    with pytest.raises(ValueError, match="root_owner_changed"):
        _read_root_record(v)
    assert not loads


def test_root_record_read_cancellation_does_not_reopen_commit(record_commit_inputs, monkeypatch):
    v = record_commit_inputs
    assert protocol.record_commit_response_from_bytes(_record_reply(v, _record_commit_request(v))).accepted
    def cancelled(*_args): raise SystemExit("fixture_read_cancelled")
    monkeypatch.setattr(state_module, "_pending_response_context", cancelled)
    with pytest.raises(SystemExit, match="read_cancelled"):
        _read_root_record(v)
    assert v.state.load(authorization_binding(v.grant["authorization_id"])) == ProposalReplayHighWater(2, v.digest[7:])
    assert v.counts["outcome_signatures"] == 1


def test_root_record_read_concurrent_retries_preserve_one_commit(record_commit_inputs):
    v = record_commit_inputs
    assert protocol.record_commit_response_from_bytes(_record_reply(v, _record_commit_request(v))).accepted
    with ThreadPoolExecutor(max_workers=4) as pool:
        assert list(pool.map(lambda _index: _read_root_record(v), range(8))) == [v.raw] * 8
    assert v.counts["outcome_signatures"] == 1


def test_root_record_storage_primitive_does_not_enable_a_read_rpc(record_commit_inputs):
    v = record_commit_inputs
    request = _record_commit_request(v)
    assert protocol.record_commit_response_from_bytes(_record_reply(v, request)).accepted
    wire = decode_message(request.to_bytes())
    wire["operation"] = "READ_COMMITTED_RECORD"
    reply = handle_root_authority_request(encode_message(wire), peer=_peer(), state=v.state,
                                          snapshot_supplier=lambda: v.current["snapshot"], now_epoch=NOW)
    assert decode_message(reply) == {"status": "REJECT"}
    assert v.raw not in reply and v.counts["outcome_signatures"] == 1


def _exit_root_record_writer(path, descriptor, snapshot, raw, phase):
    """Disposable child: exit at a real durable boundary without Python cleanup."""
    state, *_stores_value = _state(Path(path), descriptor)
    target = authorization_binding(descriptor["grants"][0]["authorization_id"])
    commit = state_module.AtomicJsonAuthorityRuntimeStore.commit
    advance = state._advance_pair

    def commit_then_exit(*args, **kwargs):
        result = commit(*args, **kwargs)
        if phase == "payload": os._exit(71)
        return result

    def advance_then_exit(binding, expected, next_value):
        if phase == "primary" and binding == target and next_value.sequence == 2:
            state._primary.advance(binding, expected=expected, next_value=next_value)
            os._exit(72)
        return advance(binding, expected, next_value)

    state_module.AtomicJsonAuthorityRuntimeStore.commit = commit_then_exit
    state._advance_pair = advance_then_exit
    reply = handle_root_authority_request(raw, peer=_peer(), state=state,
        snapshot_supplier=lambda: snapshot, now_epoch=NOW)
    assert protocol.record_commit_response_from_bytes(reply).accepted
    if phase == "reply": os._exit(73)


@pytest.mark.parametrize("phase,exitcode", [("clean", 0), ("payload", 71), ("primary", 72), ("reply", 73)])
def test_root_record_recovers_after_writer_process_exit(record_commit_inputs, tmp_path, phase, exitcode):
    from modules.communication.moltbot_bridge.tests.test_foundup_verified_outcome_root_authority_service import _exit_root_record_writer
    v = record_commit_inputs
    request = _record_commit_request(v)
    child = get_context("spawn").Process(target=_exit_root_record_writer,
        args=(str(tmp_path), v.descriptor, v.current["snapshot"], request.to_bytes(), phase))
    child.start()
    try:
        child.join(30)
        assert child.exitcode == exitcode
    finally:
        if child.is_alive():
            child.terminate()
            child.join(5)
        child.close()
    binding = authorization_binding(v.grant["authorization_id"])
    assert v.state._primary.load(binding).sequence == (1 if phase == "payload" else 2)
    assert v.state._witness.load(binding).sequence == (1 if phase in {"payload", "primary"} else 2)
    original = v.path.read_bytes()
    v.state, *_stores_value = _state(tmp_path, v.descriptor)
    for _attempt in range(2):
        reply = protocol.record_commit_response_from_bytes(_record_reply(v, request))
        assert reply.accepted and reply.record_digest == v.digest
        assert _read_root_record(v) == v.raw and v.path.read_bytes() == original
    assert v.state._primary.load(binding) == v.state._witness.load(binding) == ProposalReplayHighWater(2, v.digest[7:])
    assert _reserve(v.authority, v.grant) is None and v.counts["outcome_signatures"] == 1


def _race_root_record_writer(path, descriptor, snapshot, raw, barrier, output):
    state, *_stores_value = _state(Path(path), descriptor)
    barrier.wait(timeout=20)
    reply = handle_root_authority_request(raw, peer=_peer(), state=state,
        snapshot_supplier=lambda: snapshot, now_epoch=NOW)
    response = protocol.record_commit_response_from_bytes(reply)
    output.put((os.getpid(), response.accepted, response.record_digest))


@pytest.mark.parametrize("same_record", [False, True], ids=["conflicting", "identical"])
def test_root_record_process_race_preserves_one_durable_response(record_commit_inputs, tmp_path, same_record):
    from modules.communication.moltbot_bridge.tests.test_foundup_verified_outcome_root_authority_service import _race_root_record_writer
    from modules.communication.moltbot_bridge.tests.test_reddog_ed25519_verified_outcome_signing import _alternate_pending_response
    v = record_commit_inputs
    other_raw, other_digest = (v.raw, v.digest) if same_record else _alternate_pending_response(v)
    candidates = [_record_commit_request(v), _record_commit_request(v, other_raw, other_digest)]
    context = get_context("spawn")
    barrier, output = context.Barrier(2), context.Queue()
    children = [context.Process(target=_race_root_record_writer,
        args=(str(tmp_path), v.descriptor, v.current["snapshot"], request.to_bytes(), barrier, output))
        for request in candidates]
    try:
        for child in children: child.start()
        replies = [output.get(timeout=30) for _child in children]
        for child in children:
            child.join(10)
            assert child.exitcode == 0
    finally:
        for child in children:
            if child.is_alive():
                child.terminate()
                child.join(5)
            child.close()
        output.close()
        output.join_thread()
    assert len({pid for pid, _accepted, _digest in replies}) == 2
    assert all(pid != os.getpid() for pid, _accepted, _digest in replies)
    assert sum(accepted for _pid, accepted, _digest in replies) == (2 if same_record else 1)
    winners = {digest for _pid, accepted, digest in replies if accepted}
    assert len(winners) == 1 and winners <= {v.digest, other_digest}
    winner = winners.pop()
    original = v.path.read_bytes()
    v.state, *_stores_value = _state(tmp_path, v.descriptor)
    for candidate in candidates:
        replay = protocol.record_commit_response_from_bytes(_record_reply(v, candidate))
        assert replay.accepted == (candidate.record_digest == winner)
        assert v.path.read_bytes() == original
    expected_raw = v.raw if winner == v.digest else other_raw
    assert _read_root_record(v, expected_record_digest=winner) == expected_raw
    binding = authorization_binding(v.grant["authorization_id"])
    assert v.state._primary.load(binding) == v.state._witness.load(binding) == ProposalReplayHighWater(2, winner[7:])
    assert _reserve(v.authority, v.grant) is None and v.counts["outcome_signatures"] == 1
