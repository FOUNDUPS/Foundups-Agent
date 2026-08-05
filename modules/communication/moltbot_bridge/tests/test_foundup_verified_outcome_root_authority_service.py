"""Adversarial tests for the independent root outcome-authority service."""

from __future__ import annotations

import copy
import os
import shutil
import stat
import tempfile
import threading
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace

import pytest

from modules.communication.moltbot_bridge.src import (
    foundup_verified_outcome_root_authority as authority_module,
    foundup_verified_outcome_root_authority_client as client_module,
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


def _advance_root_state_process(values: tuple[str, ...]) -> bool:
    (
        primary_path,
        primary_root,
        primary_id,
        primary_receipt,
        witness_path,
        witness_root,
        witness_id,
        witness_receipt,
        installation_path,
        installation_root,
        installation_id,
        installation_receipt,
        binding,
    ) = values
    stores = tuple(
        SqliteMonotonicAuthorityStore(
            path,
            allowed_root=root,
            repo_root=REPO_ROOT,
            store_id=store_id,
            durability_receipt_id=receipt,
        )
        for path, root, store_id, receipt in (
            (primary_path, primary_root, primary_id, primary_receipt),
            (witness_path, witness_root, witness_id, witness_receipt),
            (
                installation_path,
                installation_root,
                installation_id,
                installation_receipt,
            ),
        )
    )
    state = RootVerifiedOutcomeAuthorityState(
        *stores, repo_root=REPO_ROOT, require_root_ownership=False
    )
    try:
        state.advance(
            binding,
            expected=None,
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
    descriptor, grant, _state_value, primary, witness, installation, *_rest = (
        _runtime(tmp_path, monkeypatch)
    )
    values = (
        str(primary.path),
        str(primary.rollback_domain_root),
        primary.store_id,
        primary.durability_receipt_id,
        str(witness.path),
        str(witness.rollback_domain_root),
        witness.store_id,
        witness.durability_receipt_id,
        str(installation.path),
        str(installation.rollback_domain_root),
        installation.store_id,
        installation.durability_receipt_id,
        authorization_binding(grant["authorization_id"]),
    )
    with ProcessPoolExecutor(max_workers=4) as pool:
        results = tuple(pool.map(_advance_root_state_process, (values,) * 8))
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


def test_one_sided_state_loss_repairs_from_witness(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    descriptor, _grant, state, primary, witness, installation, *_rest = _runtime(
        tmp_path, monkeypatch
    )
    binding = descriptor["replay_anchor_binding_digest"]
    expected = state.load(binding)
    primary_path = (
        primary.rollback_domain_root / "verified-outcome-authority.sqlite3"
    )
    primary_path.unlink()
    fresh_primary = SqliteMonotonicAuthorityStore(
        primary_path,
        allowed_root=primary.rollback_domain_root,
        repo_root=REPO_ROOT,
        store_id=primary.store_id,
        durability_receipt_id=primary.durability_receipt_id,
    )
    repaired = RootVerifiedOutcomeAuthorityState(
        fresh_primary,
        witness,
        installation,
        repo_root=REPO_ROOT,
        require_root_ownership=False,
    )
    assert repaired.load(binding) == expected
    assert fresh_primary.load(binding) == expected


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
