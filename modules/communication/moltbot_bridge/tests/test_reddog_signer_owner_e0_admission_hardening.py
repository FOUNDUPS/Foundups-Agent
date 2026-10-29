"""Tamper, rotation, and scope hardening for owner-controlled signer E0."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.src import (
    reddog_signer_owner_e0_current_selection as current_selection_module,
)
from modules.communication.moltbot_bridge.tests.test_reddog_signer_owner_controlled_e0_admission import (
    _CURRENT_SELECTION,
    _SelectionBoundary,
    _canonical_digest,
    _fixture,
    _resign,
)


@pytest.fixture(autouse=True)
def _root_owned_selection_loader(monkeypatch: pytest.MonkeyPatch) -> None:
    def load(**_kwargs: object) -> tuple[object, _SelectionBoundary]:
        capability = object()
        return capability, _SelectionBoundary(capability, _CURRENT_SELECTION)

    monkeypatch.setattr(
        current_selection_module, "load_system_service_manifest_selection", load
    )


def test_manifest_bound_principal_artifact_tamper_rejects(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    fixture["principal_payload"]["principals"][
        "github|principal:grant-admin"
    ]["principal_public_key"] = fixture["target_public"]
    fixture["principal_path"].write_text(
        json.dumps(fixture["principal_payload"], sort_keys=True), encoding="ascii"
    )
    assert fixture["boundary"].admit(
        fixture["owner_config_path"], fixture["policy"]
    ).accepted is False


def test_generation_rotation_during_validation_rejects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture = _fixture(tmp_path)
    original = current_selection_module.load_selected_signer_config

    def rotate(**kwargs: object) -> object:
        config = original(**kwargs)
        _CURRENT_SELECTION["generation_revision"] = "revision-5"
        return config

    monkeypatch.setattr(current_selection_module, "load_selected_signer_config", rotate)
    assert fixture["boundary"].admit(
        fixture["owner_config_path"], fixture["policy"]
    ).accepted is False


def test_selection_must_match_constructor_repo_root(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    _CURRENT_SELECTION["repo_root"] = str((tmp_path / "other-repo").resolve())
    assert fixture["boundary"].admit(
        fixture["owner_config_path"], fixture["policy"]
    ).accepted is False


def test_config_tampering_rejects_before_capability(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    config = fixture["config"]
    config["permission_snapshot_fresh"] = False
    fixture["config_path"].write_text(
        json.dumps(config, sort_keys=True), encoding="ascii"
    )
    assert fixture["boundary"].admit(
        fixture["owner_config_path"], fixture["policy"]
    ).accepted is False


def test_config_without_authority_binding_rejects(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    config = fixture["config"]
    config.pop("owner_e0_authority_binding_digest")
    fixture["config_path"].write_text(
        json.dumps(config, sort_keys=True), encoding="ascii"
    )
    fixture["selection"]["config_digest"] = _canonical_digest(config)
    fixture["policy"]["config_digest"] = fixture["selection"]["config_digest"]
    _resign(fixture)
    result = fixture["boundary"].admit(
        fixture["owner_config_path"], fixture["policy"]
    )
    assert result.accepted is False
    assert result.no_secret_resolution_performed is True
    assert result.no_socket_bound is True
    assert result.no_signer_started is True


def test_runtime_root_nested_under_signer_root_rejects(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    nested = Path(str(fixture["config"]["signer_runtime_root"])) / "replay"
    nested.mkdir()
    fixture["policy"]["replay_root"] = str(nested.resolve())
    fixture["policy"]["replay_path"] = str((nested / "nonces.db").resolve())
    _resign(fixture)
    assert fixture["boundary"].admit(
        fixture["owner_config_path"], fixture["policy"]
    ).accepted is False


def test_high_authority_without_consensus_policy_rejects(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    fixture["policy"]["consensus_required_tiers"] = ["HIGH"]
    _resign(fixture)
    assert fixture["boundary"].admit(
        fixture["owner_config_path"], fixture["policy"]
    ).accepted is False
