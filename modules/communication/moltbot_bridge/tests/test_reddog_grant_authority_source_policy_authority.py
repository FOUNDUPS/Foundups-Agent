"""Tests for root-owned grant-service source-policy authority."""

from __future__ import annotations

import ast
import copy
import inspect
import pickle
from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.src import (
    reddog_grant_authority_source_policy_authority as authority_module,
    reddog_signer_system_service_manifest_selection_loader as loader,
)
from modules.communication.moltbot_bridge.src.reddog_grant_authority_service_git_source_policy import (  # noqa: E501
    SOURCE_POLICY_SCHEMA,
    grant_service_git_source_policy_digest,
)
from modules.communication.moltbot_bridge.src.reddog_grant_authority_source_policy_authority import (  # noqa: E501
    load_grant_authority_source_policy_authority,
    validate_grant_authority_source_policy_owner_config,
)
from modules.communication.moltbot_bridge.src.reddog_runtime_artifact_manifest_contract import (
    RuntimeArtifactManifestError,
    digest,
    raw_digest,
)


SOURCES = {
    "reddog_grant_authority_service.py": (
        "modules/communication/moltbot_bridge/src/"
        "reddog_isolated_signer_socket_resident_service.py"
    ),
    "reddog_runtime_contract.py": (
        "modules/communication/moltbot_bridge/src/"
        "reddog_runtime_artifact_manifest_contract.py"
    ),
}


def _owner(repo: Path, sources: dict[str, str] | None = None) -> dict:
    selected = dict(sources or SOURCES)
    policy = {
        "schema_version": SOURCE_POLICY_SCHEMA,
        "repo_root_digest": raw_digest(str(repo.resolve()).encode("utf-8")),
        "sources": selected,
        "source_policy_digest": grant_service_git_source_policy_digest(selected),
    }
    owner = {
        "schema_version": loader.SCHEMA_VERSION_V4,
        "config_id": "",
        "grant_authority_source_policy": policy,
    }
    owner["config_id"] = digest(
        {key: value for key, value in owner.items() if key != "config_id"}
    )
    return owner


def _load(
    monkeypatch: pytest.MonkeyPatch, repo: Path, owner_ref: list[dict]
):
    monkeypatch.setattr(
        loader,
        "_load_owner_config",
        lambda _path, *, repo: owner_ref[0],
    )
    return load_grant_authority_source_policy_authority(
        owner_config_path=repo.parent / "owner.json",
        repo_root=repo,
    )


def test_root_owned_policy_issues_opaque_revalidatable_capability(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    owner_ref = [_owner(repo)]
    capability, boundary = _load(monkeypatch, repo, owner_ref)

    admitted = boundary.revalidate(capability)
    assert not hasattr(boundary, "consume")
    assert dict(admitted["sources"]) == SOURCES
    assert admitted["source_policy_digest"] == (
        grant_service_git_source_policy_digest(SOURCES)
    )
    assert boundary.revalidate(capability) == admitted


def test_current_root_policy_replacement_makes_capability_stale(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    owner_ref = [_owner(repo)]
    capability, boundary = _load(monkeypatch, repo, owner_ref)
    replacement = dict(SOURCES)
    replacement["reddog_runtime_contract.py"] = (
        "modules/communication/moltbot_bridge/src/"
        "reddog_runtime_json_read.py"
    )
    owner_ref[0] = _owner(repo, replacement)

    with pytest.raises(
        RuntimeArtifactManifestError, match="grant_source_policy_owner_stale"
    ):
        boundary.revalidate(capability)


@pytest.mark.parametrize("operation", [copy.copy, copy.deepcopy, pickle.dumps])
def test_capability_cannot_be_copied_or_serialized(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, operation
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    capability, _boundary = _load(monkeypatch, repo, [_owner(repo)])

    with pytest.raises(TypeError, match="not_(copyable|serializable)"):
        operation(capability)


def test_forged_object_and_other_boundary_capability_reject(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    capability, boundary = _load(monkeypatch, repo, [_owner(repo)])
    other_capability, _other = _load(monkeypatch, repo, [_owner(repo)])

    with pytest.raises(RuntimeArtifactManifestError, match="authority_unverified"):
        boundary.revalidate(object())
    with pytest.raises(RuntimeArtifactManifestError, match="authority_unverified"):
        boundary.revalidate(other_capability)
    assert boundary.revalidate(capability)


def test_v3_owner_cannot_issue_source_policy_authority(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    owner = _owner(repo)
    owner["schema_version"] = loader.SCHEMA_VERSION_V3

    with pytest.raises(RuntimeArtifactManifestError, match="owner_v4_required"):
        _load(monkeypatch, repo, [owner])


def test_wrong_repo_and_unknown_fields_reject(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    other = tmp_path / "other"
    repo.mkdir()
    other.mkdir()
    owner = _owner(repo)

    with pytest.raises(RuntimeArtifactManifestError, match="repo_binding_mismatch"):
        validate_grant_authority_source_policy_owner_config(owner, repo=other)
    owner["grant_authority_source_policy"]["unexpected"] = True
    with pytest.raises(RuntimeArtifactManifestError, match="owner_shape_invalid"):
        validate_grant_authority_source_policy_owner_config(owner, repo=repo)


def test_tampered_sources_or_digest_reject(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    owner = _owner(repo)
    owner["grant_authority_source_policy"]["sources"][
        "reddog_runtime_contract.py"
    ] = "modules/communication/moltbot_bridge/src/reddog_runtime_json_read.py"

    with pytest.raises(RuntimeArtifactManifestError, match="digest_mismatch"):
        validate_grant_authority_source_policy_owner_config(owner, repo=repo)
    owner = _owner(repo)
    owner["grant_authority_source_policy"]["source_policy_digest"] = (
        "sha256:" + "0" * 64
    )
    with pytest.raises(RuntimeArtifactManifestError, match="digest_mismatch"):
        validate_grant_authority_source_policy_owner_config(owner, repo=repo)


def test_loader_exposes_v4_and_public_source_policy_loader() -> None:
    assert loader.SCHEMA_VERSION_V4.endswith(".v4")
    assert "grant_authority_source_policy" in loader.V4_FIELDS


def test_authority_boundary_has_no_build_launch_or_write_surface() -> None:
    tree = ast.parse(inspect.getsource(authority_module))
    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    calls = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }

    assert not imported.intersection({"os", "socket", "subprocess"})
    assert not calls.intersection(
        {"write_bytes", "write_text", "mkdir", "unlink", "replace"}
    )
