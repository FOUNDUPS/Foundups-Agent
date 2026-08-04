"""Root-owned loader and signer-runtime binding tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.src import (
    foundup_verified_outcome_root_authority_dependency as dependency_module,
    foundup_verified_outcome_root_authority_client as client_module,
    foundup_verified_outcome_root_authority_state as state_module,
    reddog_signer_system_service_manifest_selection_loader as loader_module,
)
from modules.communication.moltbot_bridge.src.foundup_memex_verified_outcome_signing import (
    VerifiedOutcomeSignerPolicy,
)
from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_authority import (
    root_verified_outcome_authority_bindings,
)
from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_authority_protocol import (
    RootAuthorityResponse,
    request_from_bytes,
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
    load_root_authority_service_dependencies,
    load_system_service_verified_outcome_signing_authority,
)
from modules.communication.moltbot_bridge.tests.test_foundup_verified_outcome_root_authority import (
    NOW,
    REPO_ROOT,
    _descriptor,
    _reserve,
    _sha,
)
from modules.communication.moltbot_bridge.tests.test_foundup_verified_outcome_root_authority_service import (
    _client_authority,
)


def _v2_owner_config(tmp_path: Path, descriptor) -> tuple[Path, dict]:
    roots = {name: tmp_path / name for name in ("runtime", "high", "witness", "owner")}
    for root in roots.values():
        root.mkdir(exist_ok=True)
    value = _owner_config_value(tmp_path, roots, descriptor)
    source = tmp_path / "replay-one" / "authority.sqlite3"
    source.replace(
        tmp_path / "replay-one" / "verified-outcome-authority.sqlite3"
    )
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
            "authority_socket_path": str(tmp_path / "root-authority.sock"),
            "authority_service_uid": 0,
            "signer_uid": 1001,
            "signer_gid": 1001,
            "signer_principal_id": "reddog-e0-signer",
            "state_root": str(tmp_path / "replay-one"),
            "state_path": str(
                tmp_path / "replay-one" / "verified-outcome-authority.sqlite3"
            ),
            "state_store_id": descriptor["replay_store_id"],
            "state_durability_receipt_id": descriptor[
                "replay_store_durability_receipt_id"
            ],
            "state_witness_root": str(tmp_path / "replay-witness"),
            "state_witness_path": str(
                tmp_path
                / "replay-witness"
                / "verified-outcome-authority-witness.sqlite3"
            ),
            "state_witness_store_id": "verified-outcome-replay-witness",
            "state_witness_durability_receipt_id": _sha("witness-durable"),
            "installation_root": str(tmp_path / "replay-installation"),
            "installation_path": str(
                tmp_path
                / "replay-installation"
                / "verified-outcome-authority-installation.sqlite3"
            ),
            "installation_store_id": (
                "verified-outcome-replay-installation"
            ),
            "installation_durability_receipt_id": _sha(
                "installation-durable"
            ),
        },
    }


def _allow_test_root_reads(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        loader_module, "_read_root_owned_bytes", lambda target, _root: target.read_bytes()
    )
    monkeypatch.setattr(client_module, "_require_protected_socket", lambda *_args: None)
    monkeypatch.setattr(
        client_module,
        "_root_socket_roundtrip",
        lambda _path, raw, _uid, _timeout: _exchange_builder()(raw),
    )


def _exchange_builder(**_kwargs):
    def exchange(raw: bytes) -> bytes:
        request = request_from_bytes(raw)
        return RootAuthorityResponse(
            status="REJECT",
            request_id=request.request_id,
            descriptor_id=request.descriptor_id,
            owner_config_id=request.owner_config_id,
            authorization_id=request.authorization_id,
            reservation_id=None,
            state="REJECTED",
            reason="test_root_service_rejected",
        ).to_bytes()

    return exchange


def test_v2_root_owned_loader_mints_only_service_backed_authority(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    descriptor, grant, _store = _descriptor(tmp_path)
    path, owner = _v2_owner_config(tmp_path, descriptor)
    _allow_test_root_reads(monkeypatch)
    authority = load_system_service_verified_outcome_signing_authority(
        owner_config_path=path,
        repo_root=REPO_ROOT,
        now_epoch=NOW,
    )

    assert authority is not None
    assert root_verified_outcome_authority_bindings(authority)["owner_config_id"] == owner["config_id"]
    assert _reserve(authority, grant) is None


def test_v2_root_owned_loader_rejects_missing_root_service_response(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    descriptor, grant, _store = _descriptor(tmp_path)
    path, owner = _v2_owner_config(tmp_path, descriptor)
    _allow_test_root_reads(monkeypatch)
    authority = load_system_service_verified_outcome_signing_authority(
        owner_config_path=path,
        repo_root=REPO_ROOT,
        now_epoch=NOW,
    )

    assert authority is not None
    assert _reserve(authority, grant) is None


def test_v2_loader_rejects_state_root_overlap_before_service_connect(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    descriptor, _grant, _store = _descriptor(tmp_path)
    path, owner = _v2_owner_config(tmp_path, descriptor)
    owner["verified_outcome_authority"]["state_root"] = owner["runtime_root"]
    owner["verified_outcome_authority"]["state_path"] = str(
        Path(owner["runtime_root"]) / "verified-outcome-authority.sqlite3"
    )
    owner["config_id"] = digest(
        {key: item for key, item in owner.items() if key != "config_id"}
    )
    path.write_text(json.dumps(owner, sort_keys=True, separators=(",", ":")))
    _allow_test_root_reads(monkeypatch)
    with pytest.raises(Exception, match="root_overlap"):
        load_system_service_verified_outcome_signing_authority(
            owner_config_path=path,
            repo_root=REPO_ROOT,
            now_epoch=NOW,
        )


def test_state_ancestry_rejects_before_any_sqlite_open(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    descriptor, _grant, _store = _descriptor(tmp_path)
    path, owner = _v2_owner_config(tmp_path, descriptor)
    raw = owner["verified_outcome_authority"]
    targets = tuple(
        Path(raw[name])
        for name in (
            "state_path",
            "state_witness_path",
            "installation_path",
        )
    )
    for target in targets:
        target.unlink(missing_ok=True)
    _allow_test_root_reads(monkeypatch)
    monkeypatch.setattr(
        dependency_module,
        "validate_root_authority_state_paths",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            ValueError("root_authority_state_root_invalid")
        ),
    )

    with pytest.raises(ValueError, match="state_root_invalid"):
        load_root_authority_service_dependencies(
            owner_config_path=path,
            repo_root=REPO_ROOT,
        )

    assert all(not target.exists() for target in targets)


@pytest.mark.parametrize(
    "field",
    tuple(
        f"{prefix}_{suffix}"
        for prefix in ("state", "state_witness", "installation")
        for suffix in ("root", "path", "store_id", "durability_receipt_id")
    ),
)
def test_live_owner_reload_cannot_rotate_open_state_store_binding(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, field: str
) -> None:
    descriptor, _grant, _store = _descriptor(tmp_path)
    path, owner = _v2_owner_config(tmp_path, descriptor)
    _allow_test_root_reads(monkeypatch)
    monkeypatch.setattr(
        dependency_module, "validate_root_authority_state_paths", lambda *_a, **_k: None
    )
    monkeypatch.setattr(state_module, "_require_root_owned", lambda *_a: None)
    dependencies = load_root_authority_service_dependencies(
        owner_config_path=path, repo_root=REPO_ROOT
    )
    raw = owner["verified_outcome_authority"]
    prefix, suffix = _store_field_parts(field)
    if suffix == "root":
        root = tmp_path / f"rotated-{prefix}"
        root.mkdir()
        raw[field] = str(root)
        raw[f"{prefix}_path"] = str(root / _store_filename(prefix))
    elif suffix == "path":
        raw[field] = str(Path(raw[f"{prefix}_root"]) / "rotated.sqlite3")
    elif suffix == "durability_receipt_id":
        raw[field] = _sha(f"rotated-{prefix}-durability")
    else:
        raw[field] = f"rotated-{prefix}-store"
    owner["config_id"] = digest(
        {key: item for key, item in owner.items() if key != "config_id"}
    )
    path.write_text(json.dumps(owner, sort_keys=True, separators=(",", ":")))

    try:
        snapshot = dependencies.snapshot_supplier()
    except Exception:
        return
    assert snapshot.state_binding_digest != dependencies.state.state_binding_digest


def _store_field_parts(field: str) -> tuple[str, str]:
    for prefix in ("state_witness", "installation", "state"):
        marker = prefix + "_"
        if field.startswith(marker):
            return prefix, field[len(marker):]
    raise AssertionError("unknown store field")


def _store_filename(prefix: str) -> str:
    return {
        "state": "verified-outcome-authority.sqlite3",
        "state_witness": "verified-outcome-authority-witness.sqlite3",
        "installation": "verified-outcome-authority-installation.sqlite3",
    }[prefix]


def test_runtime_policy_requires_exact_root_owner_and_signer_binding(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    descriptor, _grant, _store = _descriptor(tmp_path)
    owner_config_id = _sha("owner-config")
    authority = _client_authority(
        monkeypatch,
        descriptor,
        owner_config_id,
        lambda _raw: b'{"status":"REJECT"}\n',
    )
    policy = _policy(descriptor)
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
    assert not verified_outcome_authority_matches_runtime(
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
