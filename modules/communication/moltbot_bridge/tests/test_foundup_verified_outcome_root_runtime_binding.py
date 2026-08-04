"""Root-owned loader and signer-runtime binding tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.src import (
    reddog_signer_system_service_manifest_selection_loader as loader_module,
)
from modules.communication.moltbot_bridge.src.foundup_memex_verified_outcome_signing import (
    VerifiedOutcomeSignerPolicy,
)
from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_authority import (
    descriptor_id_for,
    root_verified_outcome_authority_bindings,
)
from modules.communication.moltbot_bridge.src.foundup_verified_outcome_runtime_binding import (
    verified_outcome_authority_matches_runtime,
)
from modules.communication.moltbot_bridge.src.reddog_runtime_artifact_manifest_contract import (
    digest,
    raw_digest,
)
from modules.communication.moltbot_bridge.src.reddog_signer_mutual_peer_handshake import (
    SignerPeerInstanceBinding,
)
from modules.communication.moltbot_bridge.src.reddog_signer_system_service_manifest_selection_loader import (
    SCHEMA_VERSION_V2,
    load_system_service_verified_outcome_signing_authority,
)
from modules.communication.moltbot_bridge.tests.test_foundup_verified_outcome_root_authority import (
    NOW,
    REPO_ROOT,
    _authority,
    _descriptor,
    _reserve,
    _sha,
)


def _v2_owner_config(tmp_path: Path, descriptor) -> tuple[Path, dict]:
    roots = {name: tmp_path / name for name in ("runtime", "high", "witness", "owner")}
    for root in roots.values():
        root.mkdir(exist_ok=True)
    value = _owner_config_value(tmp_path, roots, descriptor)
    source = tmp_path / "replay-one" / "authority.sqlite3"
    source.replace(tmp_path / "replay-one" / "verified-outcome-replay.sqlite3")
    value["config_id"] = digest(
        {key: item for key, item in value.items() if key != "config_id"}
    )
    path = roots["owner"] / "owner.json"
    path.write_text(json.dumps(value, sort_keys=True, separators=(",", ":")))
    return path, value


def _owner_config_value(tmp_path: Path, roots: dict, descriptor) -> dict:
    return {
        "schema_version": SCHEMA_VERSION_V2,
        "config_id": "",
        "repo_root_digest": raw_digest(str(REPO_ROOT.resolve()).encode()),
        "runtime_root": str(roots["runtime"]),
        "anchor_path": str(roots["runtime"] / "generation-anchor.json"),
        "anchor_id": "reddog-signer:production",
        "generation_public_key": "generation-public-key",
        "generation_authenticator_id": "generation-authenticator",
        "generation_key_epoch": "generation-epoch-1",
        "generation_signer_public_key_fingerprint": _sha("generation-key"),
        "high_water_root": str(roots["high"]),
        "high_water_path": str(roots["high"] / "high-water.json"),
        "high_water_store_id": "high-water-store",
        "high_water_durability_receipt_id": _sha("high-durable"),
        "witness_root": str(roots["witness"]),
        "witness_path": str(roots["witness"] / "generation.sqlite3"),
        "witness_store_id": "witness-store",
        "witness_durability_receipt_id": _sha("witness-durable"),
        "verified_outcome_authority": {
            "descriptor": descriptor,
            "replay_root": str(tmp_path / "replay-one"),
            "replay_path": str(tmp_path / "replay-one" / "verified-outcome-replay.sqlite3"),
            "signer_uid": 1001,
        },
    }


def _allow_test_root_reads(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        loader_module, "_read_root_owned_bytes", lambda target, _root: target.read_bytes()
    )
    monkeypatch.setattr(
        loader_module, "_require_signer_replay_root", lambda *_args, **_kwargs: None
    )


def test_v2_root_owned_loader_mints_owner_bound_authority(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    descriptor, grant, _store = _descriptor(tmp_path)
    path, owner = _v2_owner_config(tmp_path, descriptor)
    _allow_test_root_reads(monkeypatch)
    authority = load_system_service_verified_outcome_signing_authority(
        owner_config_path=path, repo_root=REPO_ROOT, now_epoch=NOW
    )

    assert authority is not None
    assert root_verified_outcome_authority_bindings(authority)["owner_config_id"] == owner["config_id"]
    assert _reserve(authority, grant) is not None


def test_v2_root_owned_loader_rechecks_live_revocation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    descriptor, grant, _store = _descriptor(tmp_path)
    path, owner = _v2_owner_config(tmp_path, descriptor)
    _allow_test_root_reads(monkeypatch)
    authority = load_system_service_verified_outcome_signing_authority(
        owner_config_path=path, repo_root=REPO_ROOT, now_epoch=NOW
    )
    current = owner["verified_outcome_authority"]["descriptor"]
    current["revoked_authorization_ids"] = [grant["authorization_id"]]
    current["descriptor_id"] = descriptor_id_for(current)
    owner["config_id"] = digest(
        {key: item for key, item in owner.items() if key != "config_id"}
    )
    path.write_text(json.dumps(owner, sort_keys=True, separators=(",", ":")))

    assert authority is not None
    assert _reserve(authority, grant) is None


def test_v2_loader_rejects_replay_root_overlap_before_store_open(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    descriptor, _grant, _store = _descriptor(tmp_path)
    path, owner = _v2_owner_config(tmp_path, descriptor)
    owner["verified_outcome_authority"]["replay_root"] = owner["runtime_root"]
    owner["verified_outcome_authority"]["replay_path"] = str(
        Path(owner["runtime_root"]) / "verified-outcome-replay.sqlite3"
    )
    owner["config_id"] = digest(
        {key: item for key, item in owner.items() if key != "config_id"}
    )
    path.write_text(json.dumps(owner, sort_keys=True, separators=(",", ":")))
    _allow_test_root_reads(monkeypatch)
    with pytest.raises(Exception, match="root_overlap"):
        load_system_service_verified_outcome_signing_authority(
            owner_config_path=path, repo_root=REPO_ROOT, now_epoch=NOW
        )


def test_runtime_policy_requires_exact_root_owner_and_signer_binding(
    tmp_path: Path,
) -> None:
    descriptor, _grant, store = _descriptor(tmp_path)
    authority = _authority(descriptor, store)
    policy = _policy(descriptor)
    owner_config_id = _sha("owner-config")
    peer = _peer(descriptor)

    assert verified_outcome_authority_matches_runtime(
        policy, authority, expected_owner_config_id=owner_config_id,
        signer_peer_instance_binding=peer,
    )
    assert not verified_outcome_authority_matches_runtime(
        policy, authority, expected_owner_config_id=None,
        signer_peer_instance_binding=peer,
    )
    assert not verified_outcome_authority_matches_runtime(
        policy, authority, expected_owner_config_id=_sha("attacker-owner"),
        signer_peer_instance_binding=peer,
    )
    assert verified_outcome_authority_matches_runtime(
        policy, None, expected_owner_config_id=owner_config_id,
        signer_peer_instance_binding=peer,
    )
    assert not verified_outcome_authority_matches_runtime(
        policy, authority, expected_owner_config_id=owner_config_id,
        signer_peer_instance_binding=None,
    )
    assert not verified_outcome_authority_matches_runtime(
        policy, authority, expected_owner_config_id=owner_config_id,
        signer_peer_instance_binding=SignerPeerInstanceBinding(
            **{**peer.__dict__, "session_id": "attacker-session"}
        ),
    )
    assert not verified_outcome_authority_matches_runtime(
        VerifiedOutcomeSignerPolicy(**{**policy.__dict__, "reddog_id": "attacker"}),
        authority, expected_owner_config_id=owner_config_id,
        signer_peer_instance_binding=peer,
    )


def _policy(descriptor: dict) -> VerifiedOutcomeSignerPolicy:
    return VerifiedOutcomeSignerPolicy(
        issuer_principal_id="github:012",
        reddog_id="reddog-0102",
        signer_public_key=descriptor["signer_public_key"],
        key_epoch=descriptor["signer_key_epoch"],
        authority_tier="HIGH",
        consensus_receipt_digest=_sha("consensus"),
    )


def _peer(descriptor: dict) -> SignerPeerInstanceBinding:
    return SignerPeerInstanceBinding(
        run_packet_id=descriptor["signer_run_packet_id"],
        config_digest=descriptor["signer_config_digest"],
        session_id=descriptor["signer_session_id"],
        socket_path="/run/reddog/signer.sock",
        signer_profiles=(),
        manifest_id=descriptor["signer_manifest_id"],
        artifact_generation_digest=descriptor["signer_artifact_generation_digest"],
    )
