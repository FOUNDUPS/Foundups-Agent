"""Actual version validators with explicitly inert root-byte provenance."""

import hashlib
import importlib
import pytest

from modules.communication.moltbot_bridge.tests.reddog_reviewer_authority_test_support import (
    ROOT, artifact, canonical, digest, fixture,
)


def owner_data(tmp_path):
    repo, root = tmp_path / "repo", tmp_path / "owner"
    repo.mkdir(); root.mkdir()
    roots = {n: tmp_path / n for n in ("runtime", "high_water", "witness", "state", "state_witness", "installation", "grant")}
    for path in roots.values():
        path.mkdir()
    authority, designation, _, _ = fixture()
    owner = dict(schema_version="reddog_signer_system_service_owner_config.v1", config_id="",
        repo_root_digest="sha256:" + hashlib.sha256(str(repo.resolve()).encode()).hexdigest(),
        runtime_root=str(roots["runtime"]), anchor_path=str(roots["runtime"] / "generation-anchor.json"),
        anchor_id="anchor:test", generation_public_key=authority["issuer_public_key"], generation_authenticator_id="generation:test",
        generation_key_epoch="generation-1", generation_signer_public_key_fingerprint="sha256:" + "a" * 64)
    for name, filename in (("high_water", "high-water.json"), ("witness", "generation.sqlite3")):
        owner.update({name + "_root": str(roots[name]), name + "_path": str(roots[name] / filename),
            name + "_store_id": "test:" + name, name + "_durability_receipt_id": "sha256:" + "b" * 64})
    outcome = dict(descriptor={}, authority_socket_path=str(tmp_path / "outcome.sock"), authority_service_uid=0,
        signer_uid=1201, signer_gid=1201, signer_principal_id="signer:test")
    for name, filename in (("state", "verified-outcome-authority.sqlite3"),
            ("state_witness", "verified-outcome-authority-witness.sqlite3"), ("installation", "verified-outcome-authority-installation.sqlite3")):
        outcome.update({name + "_root": str(roots[name]), name + "_path": str(roots[name] / filename),
            name + "_store_id": "test:" + name, name + "_durability_receipt_id": "sha256:" + "c" * 64})
    sources = {"reddog_grant_authority_service.py": "modules/communication/moltbot_bridge/src/reddog_isolated_signer_socket_resident_service.py"}
    schema = "reddog_grant_authority_service_git_source_policy.v1"
    additions = [outcome, dict(authority_root=str(roots["grant"]), authority_socket_path=str(roots["grant"] / "grant-authority.sock"),
        authority_service_uid=1202, authority_service_gid=1203), dict(schema_version=schema,
        repo_root_digest=owner["repo_root_digest"], sources=sources, source_policy_digest=digest(dict(schema_version=schema, sources=sources))), authority]
    return repo, root, owner, additions, designation


@pytest.mark.parametrize("case", ["v1", "v2", "v3", "v4", "v5", "v1_extra", "v2_extra",
    "v3_extra", "v4_extra", "v5_missing", "v5_duplicate", "v4_duplicate"])
def test_reviewer_owner_versions(monkeypatch, tmp_path, case):
    loader = importlib.import_module(ROOT + "reddog_signer_system_service_manifest_selection_loader")
    assert getattr(loader, "SCHEMA_VERSION_V5", None) == "reddog_signer_system_service_owner_config.v5", "reviewer_owner_v5_missing"
    repo, root, owner, additions, _ = owner_data(tmp_path)
    version = int(case[1])
    keys = ["verified_outcome_authority", "independent_grant_authority", "grant_authority_source_policy", "reviewer_designation_authority"]
    owner["schema_version"] = "reddog_signer_system_service_owner_config.v" + str(version)
    owner.update(dict(zip(keys[:version - 1], additions[:version - 1])))
    if case.endswith("extra"):
        owner["reviewer_designation_authority"] = additions[3]
    elif case == "v5_missing":
        owner.pop("reviewer_designation_authority")
    owner["config_id"] = digest({k: v for k, v in owner.items() if k != "config_id"})
    raw = canonical(owner)
    if case.endswith("duplicate"):
        raw = raw[:-1] + ',"config_id":' + canonical(owner["config_id"]) + '}'
    monkeypatch.setattr(loader, "_read_root_owned_bytes", lambda *args: raw.encode("ascii"))
    if case.endswith("extra") or case in {"v5_missing", "v5_duplicate"}:
        with pytest.raises(loader.RuntimeArtifactManifestError):
            loader._load_owner_config(root / "owner.json", repo=repo)
    else:
        assert loader._load_owner_config(root / "owner.json", repo=repo) == owner


@pytest.mark.parametrize("case", ["v2_principals", "permission_v2", "invalid_designation"])
def test_reviewer_readiness_versions(case):
    records = importlib.import_module(ROOT + "reddog_signer_owner_e0_principal_records")
    assert callable(getattr(records, "parse_principal_artifact", None)), "reviewer_principal_artifact_missing"
    readiness = importlib.import_module(ROOT + "reddog_resident_runtime_artifact_readiness")
    authority, grant, _, _ = fixture()
    principals = artifact(authority, grant)
    permissions = dict(schema_version="reddog_authority_runtime_resolver_supply.v1", snapshots={}, snapshot_count=0)
    if case == "permission_v2":
        permissions["schema_version"] = "reddog_authority_runtime_resolver_supply.v2"
    elif case == "invalid_designation":
        principals["reviewer_authorizations"][0]["verified"] = True
    reasons = {"permission_snapshots.json": [], "principal_authority_records.json": []}
    readiness._validate_resolver_schemas(permissions, principals, reasons)
    if case == "v2_principals":
        assert reasons == {"permission_snapshots.json": [], "principal_authority_records.json": []}
    elif case == "permission_v2":
        assert reasons["permission_snapshots.json"] == ["permission_store_schema_invalid"]
        assert not reasons["principal_authority_records.json"]
    else:
        assert reasons["principal_authority_records.json"] == ["principal_store_schema_invalid"]
        assert not reasons["permission_snapshots.json"]


@pytest.mark.parametrize("version", ["v4", "v5"])
def test_reviewer_v5_existing_owner_consumers(monkeypatch, tmp_path, version):
    loader = importlib.import_module(ROOT + "reddog_signer_system_service_manifest_selection_loader")
    binding = importlib.import_module(ROOT + "reddog_grant_authority_service_owner_binding")
    policy_api = importlib.import_module(ROOT + "reddog_grant_authority_source_policy_authority")
    repo, root, owner, additions, _ = owner_data(tmp_path)
    keys = ["verified_outcome_authority", "independent_grant_authority", "grant_authority_source_policy", "reviewer_designation_authority"]
    owner["schema_version"] = "reddog_signer_system_service_owner_config." + version
    count = 3 if version == "v4" else 4
    owner.update(dict(zip(keys[:count], additions[:count])))
    owner["config_id"] = digest({k: v for k, v in owner.items() if k != "config_id"})
    raw, reads = [canonical(owner).encode("ascii")], []

    def root_bytes(target, owner_root):
        reads.append((target, owner_root))
        return raw[0]

    monkeypatch.setattr(loader, "_read_root_owned_bytes", root_bytes)
    path = root / "owner.json"
    actual = binding.grant_authority_owner_runtime_root(path, repo, owner["config_id"])
    assert actual == (tmp_path / "grant").resolve()
    capability, boundary = policy_api.load_grant_authority_source_policy_authority(owner_config_path=path, repo_root=repo)
    admitted = boundary.revalidate(capability)
    assert admitted["owner_config_id"] == owner["config_id"]
    assert dict(admitted["sources"]) == owner["grant_authority_source_policy"]["sources"]
    assert admitted["source_policy_digest"] == owner["grant_authority_source_policy"]["source_policy_digest"]
    assert reads == [(path, root)] * 3
    with pytest.raises(loader.RuntimeArtifactManifestError, match="grant_authority_owner_binding_mismatch"):
        binding.grant_authority_owner_runtime_root(path, repo, "sha256:" + "0" * 64)
    owner["anchor_id"] = "anchor:changed"
    owner["config_id"] = digest({k: v for k, v in owner.items() if k != "config_id"})
    raw[0] = canonical(owner).encode("ascii")
    with pytest.raises(loader.RuntimeArtifactManifestError, match="grant_source_policy_owner_stale"):
        boundary.revalidate(capability)
