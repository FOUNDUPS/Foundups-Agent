"""Real bounded file IO; synthetic approval/source metadata, no custody or grants."""
import json
import os
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from modules.communication.moltbot_bridge.src import (
    reddog_initial_runtime_manifest_authority as authority,
    reddog_signer_system_service_manifest_selection_loader as loader,
    reddog_grant_authority_service_artifact_contract as artifacts,
)
from modules.communication.moltbot_bridge.src.reddog_runtime_artifact_manifest_contract import (
    MAX_ARTIFACT_BYTES, RuntimeArtifactManifestError, canonical_json, raw_digest,
)
from modules.communication.moltbot_bridge.tests.test_reddog_grant_installed_source_contract import (
    _descriptor, _directories, _profile,
)


@pytest.fixture
def protected_root():
    if not sys.platform.startswith("linux") or os.geteuid() != 0:
        pytest.skip("requires real Linux root-owned ancestry")
    with tempfile.TemporaryDirectory(dir="/root") as raw:
        yield Path(raw)


def _file(root, name, content):
    path = root / name
    path.write_bytes(content)
    path.chmod(0o400)
    return path


@pytest.mark.parametrize("limit", [True, False, 0, -1, 1.5, "1048576", None, MAX_ARTIFACT_BYTES + 1])
def test_invalid_reader_limit_rejects_before_read(tmp_path, monkeypatch, limit):
    path = _file(tmp_path, "public-data", b"fixture")
    def unexpected_read(*args):
        pytest.fail("invalid limit reached byte reading")
    monkeypatch.setattr(loader.os, "read", unexpected_read)
    with path.open("rb") as handle, pytest.raises(RuntimeArtifactManifestError, match="read_limit_invalid"):
        loader._read_bounded_fd(handle.fileno(), max_bytes=limit)


@pytest.mark.parametrize("size", [182859, 685781, MAX_ARTIFACT_BYTES])
def test_explicit_artifact_bound_accepts_default_owner_bound_rejects(protected_root, size):
    body = b"x" * size
    path = _file(protected_root, "public-artifact", body)
    with pytest.raises(RuntimeArtifactManifestError, match="size_invalid"):
        loader._read_root_owned_bytes(path, protected_root)
    assert loader._read_root_owned_bytes(path, protected_root, max_bytes=MAX_ARTIFACT_BYTES) == body


def test_artifact_bound_plus_one_and_empty_reject(protected_root):
    path = _file(protected_root, "public-artifact", b"x" * (MAX_ARTIFACT_BYTES + 1))
    with pytest.raises(RuntimeArtifactManifestError, match="size_invalid"):
        loader._read_root_owned_bytes(path, protected_root, max_bytes=MAX_ARTIFACT_BYTES)
    path.write_bytes(b"")
    with pytest.raises(RuntimeArtifactManifestError, match="size_invalid"):
        loader._read_root_owned_bytes(path, protected_root, max_bytes=MAX_ARTIFACT_BYTES)
    assert loader._read_root_owned_bytes(path, protected_root,
        max_bytes=MAX_ARTIFACT_BYTES, allow_empty=True) == b""


@pytest.mark.parametrize("defect", ["writable", "owner", "symlink", "directory"])
def test_explicit_artifact_bound_keeps_protected_file_checks(protected_root, defect):
    path = _file(protected_root, "public-artifact", b"x" * 182859)
    if defect == "writable":
        path.chmod(0o422)
    elif defect == "owner":
        os.chown(path, 1, 1)
    elif defect == "symlink":
        actual = path.with_name("actual")
        path.rename(actual)
        path.symlink_to(actual)
    else:
        path.unlink()
        path.mkdir()
    with pytest.raises(RuntimeArtifactManifestError):
        loader._read_root_owned_bytes(path, protected_root, max_bytes=MAX_ARTIFACT_BYTES)


def test_approval_inventory_larger_than_owner_limit_reaches_policy_checks(protected_root):
    repo, runtime = protected_root / "repo", protected_root / "runtime"
    repo.mkdir()
    runtime.mkdir()
    owner = protected_root / "owner"
    owner.mkdir()
    sources = {f"modules/{number:04d}_{'x' * 80}.py": raw_digest(b"source") for number in range(1240)}
    policy = dict(schema_version=authority.SCHEMA_VERSION,
        repo_root_digest=raw_digest(str(repo).encode()), runtime_root=str(runtime),
        source_commit_sha="a" * 40, source_files=sources, manifest_spec={},
        credential_binding={}, permission={}, consumer_uids=[])
    body = canonical_json(policy).encode("ascii")
    assert 182859 < len(body) < MAX_ARTIFACT_BYTES
    path = _file(owner, "initial-approval.json", body)
    assert authority._read_policy(path, repo) == (body, policy, runtime)
    policy["repo_root_digest"] = raw_digest(b"wrong repo")
    path.write_bytes(canonical_json(policy).encode("ascii"))
    with pytest.raises(ValueError, match="repo_mismatch"):
        authority._read_policy(path, repo)


def test_large_installed_descriptor_reaches_existing_bundle_validator(protected_root):
    descriptor = _descriptor()
    descriptor["files"].extend({"path": f"usr/lib/{number:04d}_{'x' * 90}.py", "bytes": 7,
        "mode": 0o444, "sha256": raw_digest(b"fixture")[7:]} for number in range(3500))
    descriptor["files"].sort(key=lambda item: item["path"])
    descriptor["directories"] = _directories(descriptor["files"])
    repo = protected_root / "repo"
    repo.mkdir()
    repo_digest = raw_digest(str(repo).encode())
    bundle = artifacts.compose_installed_grant_service_artifacts(profile=_profile(),
        owner_config_id=raw_digest(b"owner"), repo_root_digest=repo_digest, source_descriptor=descriptor)
    checked = artifacts.validate_installed_grant_service_artifacts(bundle)
    assert 685781 < max(map(len, bundle.values())) < MAX_ARTIFACT_BYTES
    for name, body in bundle.items():
        _file(protected_root, name, body)
    policy = dict(schema_version=authority.SCHEMA_VERSION_V2, repo_root_digest=repo_digest,
        source_commit_sha=descriptor["source_commit_sha"], source_files=descriptor["source_files"])
    payload = dict(signer_service_config_digest=checked["config_digest"],
        grant_authority_installed_runtime_descriptor_digest=checked["installed_runtime_descriptor_digest"],
        owner_config_id=checked["config"]["owner_config_id"], signer_public_key="different-key")
    authority._check_installed_approval(repo, policy, protected_root, payload)
    payload["grant_authority_installed_runtime_descriptor_digest"] = raw_digest(b"changed")
    with pytest.raises(ValueError, match="binding_invalid"):
        authority._check_installed_approval(repo, policy, protected_root, payload)


def test_26_large_sources_and_empty_initializer_are_digest_checked(protected_root, monkeypatch):
    bodies = {f"source{number}.py": b"# fixture\n" * 15467 for number in range(26)}
    bodies["__init__.py"] = b""
    for name, body in bodies.items():
        _file(protected_root, name, body)
    sources = {name: raw_digest(body) for name, body in bodies.items()}
    monkeypatch.setattr(authority, "__file__", str(protected_root / "source0.py"))
    monkeypatch.setattr(authority, "sys", SimpleNamespace(modules={}))
    authority._check_sources(protected_root, sources)
    (protected_root / "source25.py").write_bytes(b"changed")
    with pytest.raises(ValueError, match="source_changed"):
        authority._check_sources(protected_root, sources)


def test_large_source_cannot_escape_per_file_bound(protected_root, monkeypatch):
    body = b"x" * (MAX_ARTIFACT_BYTES + 1)
    path = _file(protected_root, "source.py", body)
    monkeypatch.setattr(authority, "__file__", str(path))
    monkeypatch.setattr(authority, "sys", SimpleNamespace(modules={}))
    with pytest.raises(RuntimeArtifactManifestError, match="size_invalid"):
        authority._check_sources(protected_root, {path.name: raw_digest(body)})
