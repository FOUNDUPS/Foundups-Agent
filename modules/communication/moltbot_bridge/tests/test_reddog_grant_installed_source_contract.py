"""Inert installed issuer bundle tests; synthetic inventories are not admission."""
from __future__ import annotations

from pathlib import PurePosixPath

import pytest

from modules.communication.moltbot_bridge.src import (
    reddog_grant_authority_installed_source_contract as source,
    reddog_grant_authority_service_artifact_contract as artifacts,
)
from modules.communication.moltbot_bridge.src.reddog_ed25519_signature_verifier_backend import (
    encode_ed25519_public_key,
)
from modules.communication.moltbot_bridge.src.reddog_runtime_artifact_manifest_contract import (
    GRANT_AUTHORITY_SERVICE_CONFIG, GRANT_AUTHORITY_SERVICE_RUN_PACKET,
    RuntimeArtifactManifestError, raw_digest, validate_unsigned_payload,
)
from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    public_key_fingerprint,
)


def _descriptor():
    # No on-disk runtime, keys, signatures, permission receipts or grants exist.
    names = ["modules/__init__.py"] + [
        name.split(":")[0].replace(".", "/") + ".py"
        for name in (source.INSTALLED_ENTRYPOINT, source.INSTALLED_DEPENDENCY_LOADER)]
    sources = {name: raw_digest(b"" if name.endswith("__init__.py") else b"fixture") for name in names}
    files = [{"path": source.SOURCE_DIRECTORY + "/" + name,
        "bytes": 0 if name.endswith("__init__.py") else 7,
        "mode": 0o444, "sha256": value[7:]} for name, value in sources.items()]
    for name in ("usr/bin/python3.12", "usr/lib/python3.12/abc.py",
                 "usr/lib/python3.12/lib-dynload/_struct.so", "usr/lib/python3/dist-packages/package.py"):
        files.append({"path": name, "bytes": 7,
            "mode": 0o555 if name == "usr/bin/python3.12" else 0o444,
            "sha256": raw_digest(b"fixture")[7:]})
    return {"schema_version": source.INSTALLED_SOURCE_SCHEMA,
        "installed_root": "/var/lib/foundups/isolated-issuer", "source_commit_sha": "a" * 40,
        "source_object_format": "sha1", "source_directory": source.SOURCE_DIRECTORY,
        "files": sorted(files, key=lambda item: item["path"]), "source_files": sources,
        "directories": _directories(files), "python_launch": list(source.PYTHON_LAUNCH),
        "explicit_sys_path": list(source.EXPLICIT_SYS_PATH), "entrypoint": source.INSTALLED_ENTRYPOINT,
        "dependency_loader": source.INSTALLED_DEPENDENCY_LOADER}


def _directories(files):
    return sorted({str(parent) for item in files for parent in PurePosixPath(item["path"]).parents
                   if str(parent) != "."})


def _profile():
    public = encode_ed25519_public_key(bytes(range(32)))
    return dict(signer_agent_id="signer:grant", signer_profile_id="grant-profile", public_key=public,
        key_fingerprint=public_key_fingerprint(public), key_epoch="epoch-1",
        **{name: raw_digest(name.encode()) for name in ("signing_key_ref_hash", "audit_mac_key_ref_hash",
            "permission_snapshot_digest", "permission_snapshot_receipt_id")})


def _bundle():
    return artifacts.compose_installed_grant_service_artifacts(profile=_profile(),
        owner_config_id=raw_digest(b"owner"), repo_root_digest=raw_digest(b"repo"),
        source_descriptor=_descriptor())


def test_complete_bundle_roundtrip_binds_grant_config_not_target_config():
    bundle = _bundle()
    result = artifacts.validate_installed_grant_service_artifacts(bundle)
    assert result["config_digest"] == raw_digest(bundle[GRANT_AUTHORITY_SERVICE_CONFIG])
    assert result["run_packet"]["config_digest"] == result["config_digest"]
    assert result["installed_runtime_descriptor_digest"] == source.installed_grant_source_digest(_descriptor())
    with pytest.raises(RuntimeArtifactManifestError):
        artifacts.validate_installed_grant_service_run_packet(result["run_packet"],
            config_digest=raw_digest(b"target config"),
            installed_runtime_descriptor_digest=result["installed_runtime_descriptor_digest"])


def test_inert_new_shapes_are_not_accepted_by_legacy_runtime_admission():
    result = artifacts.validate_installed_grant_service_artifacts(_bundle())
    with pytest.raises(RuntimeArtifactManifestError):
        artifacts.validate_grant_service_config(result["config"])
    with pytest.raises(RuntimeArtifactManifestError):
        artifacts.validate_grant_service_run_packet(result["run_packet"],
            config_digest=result["config_digest"], archive_digest=raw_digest(b"archive"))
    with pytest.raises(RuntimeArtifactManifestError):
        validate_unsigned_payload({"schema_version": "reddog_initial_runtime_artifact_manifest.v2",
            "runtime_profile": "grant_authority_service_installed_source"})


@pytest.mark.parametrize("field,value", [
    ("schema_version", "disposable_qualification_inventory_not_authority"),
    ("installed_root", "/"), ("installed_root", "/var/../tmp"), ("installed_root", "/var//lib"),
    ("installed_root", "relative"), ("installed_root", "/tmp/\x00bad"),
    ("installed_root", "/var/lib/"), ("installed_root", True), ("installed_root", "//var/lib"),
    ("source_object_format", []), ("source_object_format", "sha512"),
    ("source_commit_sha", "A" * 40), ("source_commit_sha", "a" * 64),
    ("source_directory", "opt/attacker"), ("source_commit_sha", True),
    ("python_launch", ["/bin/sh", "-c", "echo"]),
    ("python_launch", ["/usr/bin/python3.12", "-I", "-B"]),
    ("python_launch", list(source.PYTHON_LAUNCH) + ["-c", "print(1)"]),
    ("explicit_sys_path", ["."] + list(source.EXPLICIT_SYS_PATH)),
    ("explicit_sys_path", list(source.EXPLICIT_SYS_PATH)[::-1]),
    ("entrypoint", "evil:main"), ("dependency_loader", "evil:main"),
    ("files", []), ("directories", []), ("source_files", []),
])
def test_reject_malformed_or_unfixed_descriptor(field, value):
    descriptor = _descriptor()
    descriptor[field] = value
    with pytest.raises(RuntimeArtifactManifestError):
        source.validate_installed_grant_source(descriptor)


@pytest.mark.parametrize("field,value", [
    ("path", "../escape"), ("path", "/absolute"), ("path", "usr//ambiguous"),
    ("path", "usr\\escape"), ("path", "usr/with\nnewline"), ("path", True),
    ("bytes", True), ("bytes", -1), ("bytes", 64 * 1024 * 1024 + 1),
    ("mode", True), ("mode", 0o644), ("mode", 0o4755),
    ("sha256", "sha256:" + "a" * 64), ("sha256", "A" * 64), ("sha256", 0),
])
def test_reject_inventory_member_violation(field, value):
    descriptor = _descriptor()
    descriptor["files"][0][field] = value
    with pytest.raises(RuntimeArtifactManifestError):
        source.validate_installed_grant_source(descriptor)


@pytest.mark.parametrize("case", ["extra", "missing", "duplicate_file", "reorder_files",
    "missing_directory", "duplicate_directory", "file_directory_overlap", "source_missing",
    "source_added", "source_hash_changed", "executable_not_executable", "source_executable",
    "empty_wrong_hash", "missing_callable", "empty_interpreter"])
def test_complete_declared_membership_and_role_invariants(case):
    d = _descriptor()
    if case == "extra": d["permission"] = "not authority"
    elif case == "missing": del d["source_files"]
    elif case == "duplicate_file": d["files"].append(d["files"][0])
    elif case == "reorder_files": d["files"].reverse()
    elif case == "missing_directory": d["directories"].remove("usr/lib")
    elif case == "duplicate_directory": d["directories"].append(d["directories"][0])
    elif case == "file_directory_overlap": d["directories"].append(d["files"][0]["path"])
    elif case == "source_missing": d["source_files"].pop("modules/__init__.py")
    elif case == "source_added": d["source_files"]["unbound.py"] = raw_digest(b"extra")
    elif case == "source_hash_changed": d["source_files"]["modules/__init__.py"] = raw_digest(b"different")
    elif case == "executable_not_executable":
        next(x for x in d["files"] if x["path"] == "usr/bin/python3.12")["mode"] = 0o444
    elif case == "source_executable": d["files"][0]["mode"] = 0o555
    elif case == "empty_wrong_hash":
        item = next(x for x in d["files"] if x["bytes"] == 0)
        item["sha256"] = raw_digest(b"nonempty")[7:]
    elif case == "missing_callable":
        name = source.INSTALLED_DEPENDENCY_LOADER.split(":")[0].replace(".", "/") + ".py"
        del d["source_files"][name]
        d["files"] = [x for x in d["files"] if x["path"] != source.SOURCE_DIRECTORY + "/" + name]
        d["directories"] = _directories(d["files"])
    elif case == "empty_interpreter":
        item = next(x for x in d["files"] if x["path"] == "usr/bin/python3.12")
        item.update(bytes=0, sha256=raw_digest(b"")[7:])
    with pytest.raises(RuntimeArtifactManifestError):
        source.validate_installed_grant_source(d)


def test_descriptor_is_detached_and_stable_without_future_permission():
    descriptor = _descriptor()
    accepted = source.validate_installed_grant_source(descriptor)
    before = source.installed_grant_source_digest(descriptor)
    descriptor["files"][0]["bytes"] = 42
    assert accepted["files"][0]["bytes"] != 42
    assert source.installed_grant_source_digest(accepted) == before
    for key in ("permission_snapshot_digest", "manifest_id", "full_e0_policy_digest"):
        changed = dict(accepted, **{key: raw_digest(b"future")})
        with pytest.raises(RuntimeArtifactManifestError):
            source.validate_installed_grant_source(changed)


@pytest.mark.parametrize("name", [GRANT_AUTHORITY_SERVICE_CONFIG, GRANT_AUTHORITY_SERVICE_RUN_PACKET,
                                  source.INSTALLED_SOURCE_FILENAME])
@pytest.mark.parametrize("case", ["missing", "wrong_type", "oversize", "noncanonical", "duplicate_json", "mutation"])
def test_bundle_requires_exact_canonical_bytes_and_cross_bindings(name, case):
    bundle = _bundle()
    if case == "missing": del bundle[name]
    elif case == "wrong_type": bundle[name] = bytearray(bundle[name])
    elif case == "oversize": bundle[name] = b" " * (1024 * 1024 + 1)
    elif case == "noncanonical": bundle[name] += b"\n"
    elif case == "duplicate_json": bundle[name] = b'{"schema_version":"x",' + bundle[name][1:]
    elif case == "mutation": bundle[name] = bundle[name].replace(b"sha256:", b"sha512:", 1)
    with pytest.raises(RuntimeArtifactManifestError):
        artifacts.validate_installed_grant_service_artifacts(bundle)


def test_profile_and_config_cannot_add_authority_or_plain_secret_references():
    for field in ("secret_reference", "self_signed", "native_admitted"):
        with pytest.raises(RuntimeArtifactManifestError):
            artifacts.compose_installed_grant_service_artifacts(profile=dict(_profile(), **{field: "yes"}),
                owner_config_id=raw_digest(b"owner"), repo_root_digest=raw_digest(b"repo"),
                source_descriptor=_descriptor())
    config = artifacts.validate_installed_grant_service_artifacts(_bundle())["config"]
    for field in ("owner_config_id", "repo_root_digest", "installed_runtime_descriptor_digest", "public_key"):
        with pytest.raises(RuntimeArtifactManifestError):
            artifacts.validate_installed_grant_service_config(dict(config, **{field: "invalid"}))


def test_source_sha256_commit_and_zero_byte_initializer_are_supported():
    descriptor = _descriptor()
    descriptor.update(source_object_format="sha256", source_commit_sha="b" * 64)
    assert source.validate_installed_grant_source(descriptor) == descriptor


def test_empty_installed_directories_are_bound_but_cannot_skip_ancestors():
    descriptor = _descriptor()
    descriptor["directories"].append("opt/qualification")
    descriptor["directories"].sort()
    assert source.validate_installed_grant_source(descriptor) == descriptor
    descriptor["directories"].remove("opt")
    with pytest.raises(RuntimeArtifactManifestError):
        source.validate_installed_grant_source(descriptor)


def test_stable_descriptor_excludes_config_permission_changes():
    first = artifacts.validate_installed_grant_service_artifacts(_bundle())
    profile = _profile()
    profile["permission_snapshot_receipt_id"] = raw_digest(b"later permission")
    second = artifacts.validate_installed_grant_service_artifacts(
        artifacts.compose_installed_grant_service_artifacts(profile=profile,
            owner_config_id=raw_digest(b"owner"), repo_root_digest=raw_digest(b"repo"),
            source_descriptor=_descriptor()))
    assert first["installed_runtime_descriptor_digest"] == second["installed_runtime_descriptor_digest"]
    assert first["config_digest"] != second["config_digest"]


@pytest.mark.parametrize("field", ["MAX_INSTALLED_FILES", "MAX_INSTALLED_FILE_BYTES", "MAX_INSTALLED_TOTAL_BYTES"])
def test_inventory_resource_limits_are_enforced(field, monkeypatch):
    monkeypatch.setattr(source, field, 1)
    with pytest.raises(RuntimeArtifactManifestError):
        source.validate_installed_grant_source(_descriptor())
