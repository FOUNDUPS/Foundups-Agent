"""Tests for root-authorized independent grant signer client supply."""

from __future__ import annotations

import ast
import json
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from modules.communication.moltbot_bridge.src import (
    reddog_signer_independent_grant_authority_client_supply as supply_module,
)
from modules.communication.moltbot_bridge.src.reddog_isolated_signer_socket_client import (
    SIGNER_SOCKET_CLIENT_READY,
    SignerSocketClientBuildResult,
)
from modules.communication.moltbot_bridge.src.reddog_runtime_artifact_manifest_contract import (
    RuntimeArtifactManifestError,
    digest,
    raw_digest,
)
from modules.communication.moltbot_bridge.src.reddog_grant_authority_service_git_source_policy import (
    SOURCE_POLICY_SCHEMA,
    grant_service_git_source_policy_digest,
)
from modules.communication.moltbot_bridge.src.reddog_signer_independent_grant_authority_client_supply import (
    load_system_service_independent_grant_authority_client,
    validate_independent_grant_authority_owner_config,
)
from modules.communication.moltbot_bridge.src.reddog_signer_owner_e0_policy_contract import (
    signer_owner_e0_policy_id,
)
from modules.communication.moltbot_bridge.src.reddog_signer_system_service_manifest_selection_loader import (
    SCHEMA_VERSION_V3,
    SCHEMA_VERSION_V4,
    load_system_service_startup_selection,
)
from modules.communication.moltbot_bridge.tests.test_reddog_signer_independent_secret_grant_provider import (
    _GrantClient,
    _public,
)
from modules.communication.moltbot_bridge.tests.test_reddog_signer_owner_controlled_e0_admission import (
    _SelectionBoundary,
    _fixture,
    _policy,
)
from modules.communication.moltbot_bridge.tests.test_reddog_signer_system_service_entrypoint import (
    _upgrade_prepared_owner_to_v2,
)
from modules.communication.moltbot_bridge.tests.test_reddog_signer_system_service_manifest_selection_loader import (
    _prepare_real_cli_owner,
)
from modules.communication.moltbot_bridge.tests.test_reddog_signed_runtime_artifact_manifest import (
    NOW as MANIFEST_NOW,
)


def _owner(
    tmp_path: Path, *, config_id: str, schema_version: str = SCHEMA_VERSION_V3
) -> dict:
    grant_root = tmp_path / "grant-authority"
    grant_root.mkdir()
    return {
        "schema_version": schema_version,
        "config_id": config_id,
        "runtime_root": str((tmp_path / "owner-runtime").resolve()),
        "high_water_root": str((tmp_path / "owner-high-water").resolve()),
        "witness_root": str((tmp_path / "owner-witness").resolve()),
        "verified_outcome_authority": {
            "signer_uid": 1201,
            "authority_socket_path": str(
                (tmp_path / "outcome" / "outcome-authority.sock").resolve()
            ),
            "state_root": str((tmp_path / "outcome-state").resolve()),
            "state_witness_root": str((tmp_path / "outcome-witness").resolve()),
            "installation_root": str((tmp_path / "outcome-installation").resolve()),
        },
        "independent_grant_authority": {
            "authority_root": str(grant_root.resolve()),
            "authority_socket_path": str(
                (grant_root / "grant-authority.sock").resolve()
            ),
            "authority_service_uid": 1202,
            "authority_service_gid": 1203,
        },
    }


def _policy_value(tmp_path: Path, *, owner_config_id: str, grant_public: str) -> dict:
    tmp_path.mkdir(parents=True, exist_ok=True)
    roots = {
        name: tmp_path / name
        for name in ("signer", "replay", "revocation", "revocation-witness")
    }
    for root in roots.values():
        root.mkdir()
    selection = {
        "owner_config_id": owner_config_id,
        "manifest_id": "sha256:" + "1" * 64,
        "artifact_generation_digest": "sha256:" + "2" * 64,
        "config_digest": "sha256:" + "3" * 64,
        "generation": 1,
        "generation_revision": "rev-1",
    }
    target = Ed25519PrivateKey.generate()
    revocation = Ed25519PrivateKey.generate()
    value = _policy(
        selection=selection,
        signer=roots["signer"],
        replay=roots["replay"],
        revocation=roots["revocation"],
        revocation_witness=roots["revocation-witness"],
        target_public=_public(target),
        grant_public=grant_public,
        revocation_public=_public(revocation),
        signing_ref="op://reddog/signing-key",
        audit_ref="op://reddog/audit-key",
    )
    value["policy_id"] = signer_owner_e0_policy_id(value)
    return value


@pytest.mark.parametrize("owner_schema", [SCHEMA_VERSION_V3, SCHEMA_VERSION_V4])
def test_supply_binds_root_transport_to_signed_policy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, owner_schema: str
) -> None:
    admission_root = tmp_path / "admission"
    admission_root.mkdir()
    fixture = _fixture(admission_root)
    owner_id = str(fixture["selection"]["owner_config_id"])
    owner = _owner(tmp_path, config_id=owner_id, schema_version=owner_schema)
    grant_key = Ed25519PrivateKey.generate()
    client = _GrantClient(grant_key)
    observed = {}
    import modules.communication.moltbot_bridge.src.reddog_signer_system_service_manifest_selection_loader as loader
    import modules.communication.moltbot_bridge.src.reddog_signer_owner_e0_current_selection as selection

    monkeypatch.setattr(loader, "_load_owner_config", lambda *_args, **_kwargs: owner)

    def load_selection(**_kwargs):
        capability = object()
        return capability, _SelectionBoundary(capability, fixture["selection"])

    monkeypatch.setattr(selection, "load_system_service_manifest_selection", load_selection)

    def build(**kwargs):
        observed.update(kwargs)
        return SignerSocketClientBuildResult(
            True,
            SIGNER_SOCKET_CLIENT_READY,
            (),
            client=client,
            socket_path=str(kwargs["socket_path"]),
        )

    monkeypatch.setattr(
        supply_module, "build_reddog_isolated_signer_socket_client", build
    )
    policy = fixture["policy"]
    supplied = load_system_service_independent_grant_authority_client(
        owner_config_path=tmp_path / "owner" / "owner.json",
        repo_root=Path(fixture["selection"]["repo_root"]),
        owner_policy=policy,
    )

    assert supplied.owner_config_id == owner_id
    assert supplied.binding.client is client
    assert supplied.binding.key_epoch == "grant-epoch-1"
    assert observed["expected_server_uid"] == 1202
    assert observed["expected_server_gid"] == 1203
    assert client.calls == 0


def test_supply_rejects_owner_or_key_substitution_before_socket(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    called = []
    monkeypatch.setattr(
        supply_module,
        "build_reddog_isolated_signer_socket_client",
        lambda **_kwargs: called.append(True),
    )
    policy = _policy_value(tmp_path / "policy", owner_config_id="sha256:" + "5" * 64, grant_public="not-an-ed25519-key")

    @contextmanager
    def reject_untrusted(**_kwargs):
        raise ValueError("e0_policy_signature_invalid")
        yield SimpleNamespace()

    monkeypatch.setattr(
        supply_module, "lease_validated_owner_e0_current_admission", reject_untrusted
    )

    with pytest.raises(ValueError, match="signature_invalid"):
        load_system_service_independent_grant_authority_client(
            owner_config_path=tmp_path / "owner.json",
            repo_root=tmp_path / "repo",
            owner_policy=policy,
        )
    assert called == []


def test_attacker_rehashed_policy_without_valid_signature_rejects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    admission_root = tmp_path / "admission"
    admission_root.mkdir()
    fixture = _fixture(admission_root)
    owner = _owner(tmp_path, config_id=str(fixture["selection"]["owner_config_id"]))
    import modules.communication.moltbot_bridge.src.reddog_signer_system_service_manifest_selection_loader as loader
    import modules.communication.moltbot_bridge.src.reddog_signer_owner_e0_current_selection as selection

    monkeypatch.setattr(loader, "_load_owner_config", lambda *_args, **_kwargs: owner)

    def load_selection(**_kwargs):
        capability = object()
        return capability, _SelectionBoundary(capability, fixture["selection"])

    monkeypatch.setattr(selection, "load_system_service_manifest_selection", load_selection)
    called = []
    monkeypatch.setattr(
        supply_module,
        "build_reddog_isolated_signer_socket_client",
        lambda **_kwargs: called.append(True),
    )
    policy = dict(fixture["policy"])
    signature = str(policy["signature"])
    policy["signature"] = signature[:-1] + ("A" if signature[-1] != "A" else "B")

    with pytest.raises(ValueError, match="signature_invalid"):
        load_system_service_independent_grant_authority_client(
            owner_config_path=tmp_path / "owner" / "owner.json",
            repo_root=Path(fixture["selection"]["repo_root"]),
            owner_policy=policy,
        )
    assert called == []


def test_authenticated_policy_runtime_roots_cannot_alias_grant_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    owner_id = "sha256:" + "4" * 64
    owner = _owner(tmp_path, config_id=owner_id)
    policy = _policy_value(
        tmp_path / "policy", owner_config_id=owner_id,
        grant_public=_public(Ed25519PrivateKey.generate()),
    )
    owner["independent_grant_authority"]["authority_root"] = policy["replay_root"]
    owner["independent_grant_authority"]["authority_socket_path"] = str(
        Path(policy["replay_root"]) / "grant-authority.sock"
    )
    import modules.communication.moltbot_bridge.src.reddog_signer_system_service_manifest_selection_loader as loader

    monkeypatch.setattr(loader, "_load_owner_config", lambda *_args, **_kwargs: owner)

    @contextmanager
    def authenticated(**_kwargs):
        yield SimpleNamespace(policy=policy)

    monkeypatch.setattr(
        supply_module, "lease_validated_owner_e0_current_admission", authenticated
    )
    with pytest.raises(RuntimeArtifactManifestError, match="owner_root_overlap"):
        load_system_service_independent_grant_authority_client(
            owner_config_path=tmp_path / "owner" / "owner.json",
            repo_root=tmp_path / "repo",
            owner_policy=policy,
        )


def test_owner_v3_accepts_disjoint_grant_transport(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    prepared = _prepare_real_cli_owner(tmp_path, monkeypatch)
    owner = _upgrade_prepared_owner_to_v2(prepared, tmp_path)
    grant_root = tmp_path / "grant-authority"
    grant_root.mkdir()
    owner.update(
        schema_version=SCHEMA_VERSION_V3,
        independent_grant_authority={
            "authority_root": str(grant_root.resolve()),
            "authority_socket_path": str(
                (grant_root / "grant-authority.sock").resolve()
            ),
            "authority_service_uid": 1202,
            "authority_service_gid": 1203,
        },
    )
    owner["config_id"] = digest(
        {key: value for key, value in owner.items() if key != "config_id"}
    )
    Path(prepared["owner_path"]).write_text(
        json.dumps(owner, sort_keys=True, separators=(",", ":")),
        encoding="ascii",
    )
    import modules.communication.moltbot_bridge.src.reddog_current_generation_manifest_launch_selection as selection
    import modules.communication.moltbot_bridge.src.reddog_signer_system_service_manifest_selection_loader as loader

    monkeypatch.setattr(selection, "_now_epoch", lambda: MANIFEST_NOW)
    monkeypatch.setattr(loader.time, "time", lambda: MANIFEST_NOW)

    selected = load_system_service_startup_selection(
        owner_config_path=prepared["owner_path"],
        repo_root=prepared["harness"].repo_root,
    )

    assert selected.owner_config_id == owner["config_id"]


def test_owner_v4_accepts_root_bound_source_policy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    prepared = _prepare_real_cli_owner(tmp_path, monkeypatch)
    owner = _upgrade_prepared_owner_to_v2(prepared, tmp_path)
    grant_root = tmp_path / "grant-authority"
    grant_root.mkdir()
    sources = {
        "reddog_grant_authority_service.py": (
            "modules/communication/moltbot_bridge/src/"
            "reddog_isolated_signer_socket_resident_service.py"
        )
    }
    repo = prepared["harness"].repo_root.resolve()
    owner.update(
        schema_version=SCHEMA_VERSION_V4,
        independent_grant_authority={
            "authority_root": str(grant_root.resolve()),
            "authority_socket_path": str(
                (grant_root / "grant-authority.sock").resolve()
            ),
            "authority_service_uid": 1202,
            "authority_service_gid": 1203,
        },
        grant_authority_source_policy={
            "schema_version": SOURCE_POLICY_SCHEMA,
            "repo_root_digest": raw_digest(str(repo).encode("utf-8")),
            "sources": sources,
            "source_policy_digest": grant_service_git_source_policy_digest(
                sources
            ),
        },
    )
    owner["config_id"] = digest(
        {key: value for key, value in owner.items() if key != "config_id"}
    )
    Path(prepared["owner_path"]).write_text(
        json.dumps(owner, sort_keys=True, separators=(",", ":")),
        encoding="ascii",
    )
    import modules.communication.moltbot_bridge.src.reddog_current_generation_manifest_launch_selection as selection
    import modules.communication.moltbot_bridge.src.reddog_signer_system_service_manifest_selection_loader as loader

    monkeypatch.setattr(selection, "_now_epoch", lambda: MANIFEST_NOW)
    monkeypatch.setattr(loader.time, "time", lambda: MANIFEST_NOW)

    selected = load_system_service_startup_selection(
        owner_config_path=prepared["owner_path"],
        repo_root=repo,
    )

    assert selected.owner_config_id == owner["config_id"]


def test_owner_transport_rejects_signer_uid_or_root_overlap(tmp_path: Path) -> None:
    grant_root = tmp_path / "grant"
    grant_root.mkdir()
    outcome_root = tmp_path / "outcome"
    outcome_root.mkdir()
    value = {
        "runtime_root": str(grant_root),
        "high_water_root": str(tmp_path / "high"),
        "witness_root": str(tmp_path / "witness"),
        "verified_outcome_authority": {
            "signer_uid": 1202,
            "authority_socket_path": str(outcome_root / "outcome-authority.sock"),
            "state_root": str(outcome_root),
            "state_witness_root": str(tmp_path / "outcome-witness"),
            "installation_root": str(tmp_path / "outcome-installation"),
        },
        "independent_grant_authority": {
            "authority_root": str(grant_root),
            "authority_socket_path": str(grant_root / "grant-authority.sock"),
            "authority_service_uid": 1202,
            "authority_service_gid": 1203,
        },
    }

    with pytest.raises(RuntimeArtifactManifestError, match="owner_config_invalid"):
        validate_independent_grant_authority_owner_config(
            value, repo=tmp_path / "repo", owner_root=tmp_path / "owner"
        )

    value["independent_grant_authority"]["authority_service_uid"] = 1204
    with pytest.raises(RuntimeArtifactManifestError, match="owner_root_overlap"):
        validate_independent_grant_authority_owner_config(
            value, repo=tmp_path / "repo", owner_root=tmp_path / "owner"
        )


def test_owner_transport_rejects_outcome_socket_alias(tmp_path: Path) -> None:
    grant_root = tmp_path / "grant"
    grant_root.mkdir()
    shared_socket = grant_root / "grant-authority.sock"
    value = {
        "runtime_root": str(tmp_path / "runtime"),
        "high_water_root": str(tmp_path / "high"),
        "witness_root": str(tmp_path / "witness"),
        "verified_outcome_authority": {
            "signer_uid": 1201,
            "authority_socket_path": str(shared_socket),
            "state_root": str(tmp_path / "outcome"),
            "state_witness_root": str(tmp_path / "outcome-witness"),
            "installation_root": str(tmp_path / "outcome-installation"),
        },
        "independent_grant_authority": {
            "authority_root": str(grant_root),
            "authority_socket_path": str(shared_socket),
            "authority_service_uid": 1202,
            "authority_service_gid": 1203,
        },
    }

    with pytest.raises(RuntimeArtifactManifestError, match="owner_config_invalid"):
        validate_independent_grant_authority_owner_config(
            value, repo=tmp_path / "repo", owner_root=tmp_path / "owner"
        )


def test_owner_transport_rejects_malformed_path_types(tmp_path: Path) -> None:
    value = {
        "verified_outcome_authority": {"authority_socket_path": "outcome.sock"},
        "independent_grant_authority": {
            "authority_root": 7,
            "authority_socket_path": ["grant-authority.sock"],
            "authority_service_uid": 1202,
            "authority_service_gid": 1203,
        },
    }

    with pytest.raises(RuntimeArtifactManifestError, match="owner_config_invalid"):
        validate_independent_grant_authority_owner_config(
            value, repo=tmp_path / "repo", owner_root=tmp_path / "owner"
        )


def test_v3_transport_fields_are_bound_by_owner_config_id(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    prepared = _prepare_real_cli_owner(tmp_path, monkeypatch)
    owner = _upgrade_prepared_owner_to_v2(prepared, tmp_path)
    grant_root = tmp_path / "grant-authority"
    grant_root.mkdir()
    owner.update(
        schema_version=SCHEMA_VERSION_V3,
        independent_grant_authority={
            "authority_root": str(grant_root.resolve()),
            "authority_socket_path": str(
                (grant_root / "grant-authority.sock").resolve()
            ),
            "authority_service_uid": 1202,
            "authority_service_gid": 1203,
        },
    )
    owner["config_id"] = digest(
        {key: value for key, value in owner.items() if key != "config_id"}
    )
    owner["independent_grant_authority"]["authority_service_gid"] = 1303
    Path(prepared["owner_path"]).write_text(
        json.dumps(owner, sort_keys=True, separators=(",", ":")), encoding="ascii"
    )

    with pytest.raises(
        RuntimeArtifactManifestError, match="signer_owner_config_id_invalid"
    ):
        load_system_service_startup_selection(
            owner_config_path=prepared["owner_path"],
            repo_root=prepared["harness"].repo_root,
        )


def test_supply_module_has_no_effect_plane_or_secret_loading() -> None:
    source = Path(supply_module.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    denied = {"subprocess", "requests", "urllib", "holo_index", "git", "os", "socket"}
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".", 1)[0])
    assert imports.isdisjoint(denied)
    attributes = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    assert "sign" not in attributes
    assert "get_secret" not in attributes
    calls = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert {"sign", "get_secret"}.isdisjoint(calls)
    assert len(source.splitlines()) <= 200
