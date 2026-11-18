"""Identity/grant separation tests for root revocation availability."""

from __future__ import annotations

import copy
from dataclasses import replace

import pytest

from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_authority import (
    descriptor_id_for,
)
from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_authority_service import (
    validated_root_authority_snapshot,
)
from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_protected_use_client import (
    RootProtectedUseAuthority,
)
from modules.communication.moltbot_bridge.src import (
    foundup_verified_outcome_root_authority_client as root_client_module,
    reddog_signer_system_service_manifest_selection_loader as loader_module,
)
from modules.communication.moltbot_bridge.src import (
    reddog_signer_system_service_root_protected_use_loader as protected_loader,
)
from modules.communication.moltbot_bridge.tests.root_revocation_service_fixtures import (
    runtime,
)
from modules.communication.moltbot_bridge.tests.test_foundup_verified_outcome_root_authority import (
    _sign,
)
from modules.communication.moltbot_bridge.tests.test_foundup_verified_outcome_root_revocation_service import (
    _handle,
    _request,
)


@pytest.mark.parametrize("grant_state", ["expired", "revoked", "empty"])
def test_outcome_grant_state_does_not_control_revocation_liveness(
    tmp_path, monkeypatch, grant_state
) -> None:
    values = runtime(tmp_path, monkeypatch)
    descriptor = copy.deepcopy(values["snapshot"].descriptor)
    grant = descriptor["grants"][0]
    if grant_state == "expired":
        grant["issued_at"] = descriptor["issued_at"]
        grant["expires_at"] = descriptor["issued_at"] + 1
    elif grant_state == "revoked":
        descriptor["revoked_authorization_ids"] = [grant["authorization_id"]]
    else:
        descriptor["grants"] = []
    descriptor["descriptor_id"] = descriptor_id_for(descriptor)
    values["snapshot"] = replace(values["snapshot"], descriptor=descriptor)

    assert _handle(values, _request(values)).accepted is True
    with pytest.raises(ValueError):
        validated_root_authority_snapshot(
            values["state"], snapshot_supplier=lambda: values["snapshot"],
            now_epoch=values["policy"]["issued_at"] + 20,
        )


def test_identity_validation_still_rejects_descriptor_rehash_attack(
    tmp_path, monkeypatch
) -> None:
    values = runtime(tmp_path, monkeypatch)
    descriptor = copy.deepcopy(values["snapshot"].descriptor)
    descriptor["signer_public_key"] = descriptor["grants"][0][
        "verifier_public_key"
    ]
    descriptor["descriptor_id"] = descriptor_id_for(descriptor)
    values["snapshot"] = replace(values["snapshot"], descriptor=descriptor)
    assert _handle(values, _request(values)).accepted is False


def test_public_owner_loader_mints_only_service_backed_client(
    tmp_path, monkeypatch
) -> None:
    values = runtime(tmp_path, monkeypatch)
    owner = {
        "config_id": values["policy"]["owner_config_id"],
        "verified_outcome_authority": {
            "descriptor": values["snapshot"].descriptor,
            "authority_socket_path": str(tmp_path / "root.sock"),
            "authority_service_uid": 0,
        },
    }
    monkeypatch.setattr(loader_module, "_load_owner_config", lambda *_a, **_k: owner)
    monkeypatch.setattr(protected_loader, "_load_owner_config", lambda *_a, **_k: owner)
    monkeypatch.setattr(root_client_module, "_require_protected_socket", lambda *_: None)
    monkeypatch.setattr(
        root_client_module, "_root_socket_roundtrip",
        lambda _path, raw, _uid, _timeout: values["exchange"](raw),
    )
    client = loader_module.load_system_service_revocation_anchor_authority(
        owner_config_path=tmp_path / "owner.json", repo_root=values["repo"],
        policy=values["policy"], binding=values["binding"],
        request_signer=lambda value: _sign(values["target_private"], value),
    )
    assert client.load() is None
    protected = protected_loader.load_system_service_root_protected_use_authority(
        owner_config_path=tmp_path / "owner.json", repo_root=values["repo"],
        policy=values["policy"], binding=values["binding"],
        request_signer=lambda value: _sign(values["target_private"], value),
    )
    assert type(protected) is RootProtectedUseAuthority
