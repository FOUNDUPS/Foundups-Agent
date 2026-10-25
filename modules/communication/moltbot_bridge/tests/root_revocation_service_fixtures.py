"""Integrated fixtures for the root revocation-anchor service tests."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Mapping

from modules.communication.moltbot_bridge.src import (
    foundup_verified_outcome_root_authority_client as root_client_module,
)
from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_authority_client import (
    _create_service_backed_outcome_authority,
    build_root_authority_socket_exchange,
)
from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_authority_service import (
    RootAuthoritySnapshot,
    initialize_root_authority_state,
)
from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_revocation_authority import (
    _create_root_revocation_service_authority,
)
from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_revocation_client import (
    _create_root_revocation_anchor_authority,
)
from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_revocation_service import (
    handle_root_revocation_request,
)
from modules.communication.moltbot_bridge.src.reddog_signer_secret_grant_revocation_authority_binding import (
    revocation_authority_binding_from_policy,
)
from modules.communication.moltbot_bridge.src.reddog_signer_secret_grant_revocation_authority_store import (
    SignerGrantRevocationAuthorityStore,
)
from modules.communication.moltbot_bridge.src.reddog_signer_socket_peer_credential_attestor import (
    KernelPeerIdentity,
)
from modules.communication.moltbot_bridge.tests import (
    test_reddog_signer_owner_controlled_e0_admission as e0,
)
from modules.communication.moltbot_bridge.tests.test_foundup_verified_outcome_root_authority import (
    _descriptor,
    _sha,
    _sign,
)
from modules.communication.moltbot_bridge.tests.test_foundup_verified_outcome_root_authority_service import (
    _peer,
)
from modules.communication.moltbot_bridge.tests.root_revocation_service_topology_fixture import (
    bind_selection_loader,
    root_state,
    witness_store,
)
from modules.communication.moltbot_bridge.tests.root_revocation_snapshot_fixture import (
    signed_snapshot,
    stage,
)


def runtime(
    tmp_path: Path, monkeypatch: Any, *, overlap_root: bool = False,
) -> dict[str, Any]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    e0_root = tmp_path / "e0"
    e0_root.mkdir()
    fixture = e0._fixture(e0_root)
    bind_selection_loader(monkeypatch)
    policy = fixture["policy"]
    repo = Path(str(fixture["selection"]["repo_root"])).resolve()
    root_base = (
        Path(str(policy["revocation_root"])) / "root-service"
        if overlap_root else tmp_path / "root"
    )
    state = root_state(root_base, policy, repo)
    policy["revocation_anchor_state_binding_digest"] = state.state_binding_digest
    e0._rebind_config_and_sign(fixture, fixture["grant_private"])
    binding = revocation_authority_binding_from_policy(
        policy,
        repo_root=repo,
        signer_runtime_root=Path(str(fixture["config"]["signer_runtime_root"])),
    )
    now, descriptor, snapshot = _descriptor_snapshot(
        tmp_path, fixture, policy, state
    )
    initialize_root_authority_state(state, snapshot, now_epoch=now)
    server_authority = _create_root_revocation_service_authority(
        owner_config_path=fixture["owner_config_path"], repo_root=repo,
    )
    store = SignerGrantRevocationAuthorityStore(binding, repo_root=repo)
    witness = witness_store(binding, repo)
    client, exchange = _client_transport(
        tmp_path, monkeypatch, fixture, policy, binding, repo, state,
        snapshot, server_authority, descriptor, now,
    )
    return {
        **fixture, "repo": repo, "state": state, "binding": binding,
        "store": store, "witness": witness, "snapshot": snapshot,
        "server_authority": server_authority, "client": client,
        "exchange": exchange,
    }


def _descriptor_snapshot(tmp_path, fixture, policy, state):
    now = int(time.time())
    descriptor, _grant, _legacy = _descriptor(
        tmp_path / "descriptor",
        signer_key=fixture["target_private"],
        grant_overrides={"issued_at": now - 1, "expires_at": now + 120},
        descriptor_overrides={
            "issued_at": now - 2,
            "expires_at": now + 300,
            "replay_store_id": policy["revocation_anchor_store_id"],
            "replay_store_durability_receipt_id": policy[
                "revocation_anchor_store_durability_receipt_id"
            ],
        },
    )
    snapshot = RootAuthoritySnapshot(
        owner_config_id=str(policy["owner_config_id"]),
        authority_generation_sequence=descriptor["authority_generation_sequence"],
        state_binding_digest=state.state_binding_digest,
        signer_principal_id="reddog-e0-signer",
        signer_uid=1001,
        signer_gid=1001,
        descriptor=descriptor,
    )
    return now, descriptor, snapshot


def _client_transport(
    tmp_path, monkeypatch, fixture, policy, binding, repo, state, snapshot,
    server_authority, descriptor, now,
):

    def exchange(raw: bytes) -> bytes:
        return handle_root_revocation_request(
            raw, peer=_peer(), state=state, snapshot_supplier=lambda: snapshot,
            revocation_authority=server_authority, now_epoch=int(time.time()),
        )

    monkeypatch.setattr(root_client_module, "_require_protected_socket", lambda *_: None)
    monkeypatch.setattr(
        root_client_module, "_root_socket_roundtrip",
        lambda _path, raw, _uid, _timeout: exchange(raw),
    )
    transport = build_root_authority_socket_exchange(
        repo_root=repo, socket_path=tmp_path / "root-authority.sock",
    )
    client = _create_root_revocation_anchor_authority(
        descriptor, owner_config_id=str(policy["owner_config_id"]),
        policy=policy, binding=binding, exchange=transport,
        request_signer=lambda value: _sign(fixture["target_private"], value),
        now_epoch=now,
    )
    return client, exchange


def legacy_roundtrip(values, exchange) -> bool:
    """Exercise legacy reserve/commit through a composed root router."""

    now = int(time.time())
    descriptor = values["snapshot"].descriptor
    grant = descriptor["grants"][0]
    authority = _create_service_backed_outcome_authority(
        descriptor, owner_config_id=str(values["policy"]["owner_config_id"]),
        exchange=exchange, now_epoch=now,
    )
    request = {
        "receipt_id": grant["receipt_id"], "work_order_id": grant["work_order_id"],
        "evidence_digest": grant["evidence_digest"], "issued_at": now,
    }
    request["signer_instance_signature"] = _sign(
        values["target_private"], authority.reserve_proof_input(**request)
    )
    reservation = authority.reserve(**request)
    if reservation is None:
        return False
    signature_digest = _sha("linux-router-signature")
    proof = _sign(
        values["target_private"],
        authority.commit_proof_input(reservation, signature_digest),
    )
    authority.commit(reservation, signature_digest, proof)
    return True


__all__ = ["legacy_roundtrip", "runtime", "signed_snapshot", "stage"]
