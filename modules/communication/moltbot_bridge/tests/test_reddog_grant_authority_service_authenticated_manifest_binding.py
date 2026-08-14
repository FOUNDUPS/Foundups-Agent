"""Adversarial coverage for E0-bound grant-service artifacts."""

from __future__ import annotations

import ast
import inspect
import json
from pathlib import Path
from typing import Any

import pytest

from modules.communication.moltbot_bridge.src import (
    reddog_grant_authority_service_archive_validation as archive_validation_module,
    reddog_grant_authority_service_manifest_verifier as verifier_module,
    reddog_signer_owner_e0_current_selection as current_selection_module,
)
from modules.communication.moltbot_bridge.src.reddog_grant_authority_service_artifact_contract import (
    CONFIG_SCHEMA,
    ENTRYPOINT,
    RUN_PACKET_SCHEMA,
    SERVICE_ID,
)
from modules.communication.moltbot_bridge.src.reddog_grant_authority_service_authenticated_manifest_binding import (
    bind_grant_authority_service_manifest,
)
from modules.communication.moltbot_bridge.src.reddog_grant_authority_service_archive_contract import (
    ARCHIVE_MAIN,
    build_grant_service_archive,
)
from modules.communication.moltbot_bridge.src.reddog_ed25519_signature_verifier_backend import (
    Ed25519SignatureVerifier,
)
from modules.communication.moltbot_bridge.src.reddog_runtime_artifact_manifest_contract import (
    GRANT_AUTHORITY_SERVICE_ARCHIVE,
    GRANT_AUTHORITY_SERVICE_CONFIG,
    GRANT_AUTHORITY_SERVICE_RUN_PACKET,
    MAX_SERVICE_ARCHIVE_BYTES,
    RUNTIME_PROFILE_GRANT_AUTHORITY_SERVICE,
    SIGNING_PREFIX,
    SIGNING_PREFIX_V2,
    RuntimeArtifactManifestError,
    canonical_json,
    digest,
    manifest_id_for,
    raw_digest,
    validate_unsigned_payload,
)
from modules.communication.moltbot_bridge.src.reddog_signed_runtime_artifact_manifest import (
    produce_signed_runtime_artifact_manifest,
    validate_runtime_artifact_manifest_signing_request,
)
from modules.communication.moltbot_bridge.src.reddog_runtime_artifact_manifest_launch_selection import (
    create_runtime_artifact_manifest_launch_selection_boundary,
)
from modules.communication.moltbot_bridge.src.reddog_signer_owner_e0_policy_contract import (
    POLICY_FIELDS_V5,
    POLICY_FIELDS_V6,
    POLICY_SCHEMA_V5,
)
from modules.communication.moltbot_bridge.tests.test_reddog_signed_runtime_artifact_manifest import (
    NOW,
    _build_harness,
    _self_sign_manifest,
)
from modules.communication.moltbot_bridge.tests.test_reddog_signer_independent_grant_authority_client_supply import (
    _owner,
)
from modules.communication.moltbot_bridge.tests.test_reddog_signer_owner_controlled_e0_admission import (
    _CURRENT_SELECTION,
    _SelectionBoundary,
    _fixture,
    _rebind_config_and_sign,
)


def test_current_e0_binds_exact_grant_artifacts_without_secrets(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    setup = _setup(tmp_path, monkeypatch)
    values = _bind(setup).to_dict()

    assert values["manifest_id"] == setup["manifest"]["manifest_id"]
    assert values["service_archive_digest"] == setup["archive_digest"]
    assert "ref" not in " ".join(values).lower()
    assert "op://" not in repr(values)


@pytest.mark.parametrize(
    "field",
    [
        "grant_authority_manifest_id",
        "grant_authority_artifact_generation_digest",
        "grant_authority_config_digest",
        "grant_authority_run_packet_digest",
        "grant_authority_permission_snapshot_digest",
    ],
)
def test_signed_policy_substitution_rejects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, field: str
) -> None:
    setup = _setup(tmp_path, monkeypatch)
    setup["e0"]["policy"][field] = "sha256:" + "f" * 64
    _rebind_config_and_sign(setup["e0"], setup["e0"]["grant_private"])

    with pytest.raises((RuntimeArtifactManifestError, ValueError)):
        _bind(setup)


@pytest.mark.parametrize(
    ("grant_field", "target_field"),
    [
        ("grant_authority_signing_key_ref_hash", "audit_mac_key_ref_hash"),
        ("grant_authority_audit_mac_key_ref_hash", "signing_key_ref_hash"),
    ],
)
def test_cross_role_key_reference_alias_rejects(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    grant_field: str,
    target_field: str,
) -> None:
    setup = _setup(tmp_path, monkeypatch)
    setup["e0"]["policy"][grant_field] = setup["e0"]["policy"][target_field]
    _rebind_config_and_sign(setup["e0"], setup["e0"]["grant_private"])

    with pytest.raises(ValueError, match="grant_service_binding_invalid"):
        _bind(setup)


def test_grant_and_manifest_signer_public_keys_must_differ(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    setup = _setup(tmp_path, monkeypatch)
    policy = setup["e0"]["policy"]
    policy["grant_authority_public_key"] = policy["target_signer_public_key"]
    policy["grant_authority_key_fingerprint"] = policy[
        "target_signer_key_fingerprint"
    ]
    _rebind_config_and_sign(setup["e0"], setup["e0"]["grant_private"])

    with pytest.raises(ValueError, match="grant_service_binding_invalid"):
        _bind(setup)


@pytest.mark.parametrize(
    "field",
    [
        "grant_authority_signer_agent_id",
        "grant_authority_signer_profile_id",
        "grant_authority_key_epoch",
        "target_signer_agent_id",
        "target_signer_profile_id",
        "target_signer_key_epoch",
    ],
)
def test_signed_e0_secret_reference_shaped_public_identity_rejects(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    field: str,
) -> None:
    setup = _setup(tmp_path, monkeypatch)
    setup["e0"]["policy"][field] = "op://vault/item/secret"
    _rebind_config_and_sign(setup["e0"], setup["e0"]["grant_private"])

    with pytest.raises(ValueError, match="grant_service_binding_invalid"):
        _bind(setup)


@pytest.mark.parametrize(
    "filename",
    [
        GRANT_AUTHORITY_SERVICE_CONFIG,
        GRANT_AUTHORITY_SERVICE_RUN_PACKET,
        GRANT_AUTHORITY_SERVICE_ARCHIVE,
    ],
)
def test_artifact_replacement_rejects_at_use_time(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    filename: str,
) -> None:
    setup = _setup(tmp_path, monkeypatch)
    assert _bind(setup).manifest_id == setup["manifest"]["manifest_id"]
    (setup["harness"].runtime_root / filename).write_bytes(b"attacker")

    with pytest.raises(RuntimeArtifactManifestError, match="artifact_changed"):
        _bind(setup)


def test_archive_tail_after_one_megabyte_is_signed_and_reverified(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    archive = _valid_archive()
    setup = _setup(tmp_path, monkeypatch, archive=archive)
    target = setup["harness"].runtime_root / GRANT_AUTHORITY_SERVICE_ARCHIVE
    target.write_bytes(archive[:-1] + b"X")

    with pytest.raises(RuntimeArtifactManifestError, match="artifact_changed"):
        _bind(setup)


def test_owner_grant_root_substitution_rejects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    setup = _setup(tmp_path, monkeypatch)
    attacker = tmp_path / "attacker"
    attacker.mkdir()
    setup["owner"]["independent_grant_authority"].update(
        {
            "authority_root": str(attacker.resolve()),
            "authority_socket_path": str(
                (attacker / "grant-authority.sock").resolve()
            ),
        }
    )

    with pytest.raises(RuntimeArtifactManifestError):
        _bind(setup)


@pytest.mark.parametrize(
    "field",
    ["repo_root_digest", "signer_service_config_digest"],
)
def test_resigned_manifest_current_authority_mismatch_rejects(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    field: str,
) -> None:
    setup = _setup(tmp_path, monkeypatch)
    _replace_signed_manifest_field(
        setup, field=field, value="sha256:" + "f" * 64
    )

    with pytest.raises(
        RuntimeArtifactManifestError,
        match="grant_service_manifest_binding_mismatch",
    ):
        _bind(setup)


def test_legacy_process_local_selector_rejects_v2_manifest(
    tmp_path: Path,
) -> None:
    manifest_root = tmp_path / "manifest"
    manifest_root.mkdir()
    harness = _build_harness(manifest_root)
    e0 = _fixture_at(tmp_path / "e0")
    archive = _valid_archive()
    archive_digest = raw_digest(archive)
    config = _config(e0, archive_digest)
    config_raw = canonical_json(config).encode("ascii")
    _write(harness.runtime_root / GRANT_AUTHORITY_SERVICE_ARCHIVE, archive)
    _write(harness.runtime_root / GRANT_AUTHORITY_SERVICE_CONFIG, config_raw)
    _write_json(
        harness.runtime_root / GRANT_AUTHORITY_SERVICE_RUN_PACKET,
        _run_packet(raw_digest(config_raw), archive_digest),
    )
    result = produce_signed_runtime_artifact_manifest(
        manifest_directory=harness.manifest_directory,
        nonce="legacy-selector-v2",
        issued_at=NOW,
        expires_at=NOW + 120,
        context=harness.context,
        runtime_profile=RUNTIME_PROFILE_GRANT_AUTHORITY_SERVICE,
    )
    assert result.accepted is True
    legacy = create_runtime_artifact_manifest_launch_selection_boundary(
        authority=harness.authority,
        authority_boundary=harness.authority_boundary,
        signature_verifier=Ed25519SignatureVerifier(),
    )

    with pytest.raises(
        RuntimeArtifactManifestError,
        match="manifest_launch_artifacts_missing",
    ):
        legacy.select(harness.read_manifest(), now_epoch=NOW)


def test_public_api_has_no_injected_manifest_or_profile_boundary() -> None:
    parameters = inspect.signature(
        bind_grant_authority_service_manifest
    ).parameters
    assert set(parameters) == {
        "owner_config_path", "repo_root", "owner_policy"
    }


def test_config_unknown_field_rejects_before_manifest_signing(
    tmp_path: Path
) -> None:
    harness = _build_harness(tmp_path)
    archive = _valid_archive()
    archive_digest = raw_digest(archive)
    config = _config(_fixture_at(tmp_path / "e0"), archive_digest)
    config["unexpected"] = "attacker"
    _write(harness.runtime_root / GRANT_AUTHORITY_SERVICE_ARCHIVE, archive)
    _write_json(harness.runtime_root / GRANT_AUTHORITY_SERVICE_CONFIG, config)
    _write_json(
        harness.runtime_root / GRANT_AUTHORITY_SERVICE_RUN_PACKET,
        _run_packet(raw_digest(canonical_json(config).encode("ascii")), archive_digest),
    )

    result = produce_signed_runtime_artifact_manifest(
        manifest_directory=harness.manifest_directory,
        nonce="grant-service-invalid-config",
        issued_at=NOW,
        expires_at=NOW + 120,
        context=harness.context,
        runtime_profile=RUNTIME_PROFILE_GRANT_AUTHORITY_SERVICE,
    )
    assert result.accepted is False


@pytest.mark.parametrize(
    "field", ["signer_agent_id", "signer_profile_id", "key_epoch"]
)
def test_secret_reference_shaped_config_rejects_before_manifest_signing(
    tmp_path: Path, field: str
) -> None:
    harness = _build_harness(tmp_path)
    archive = _valid_archive()
    archive_digest = raw_digest(archive)
    config = _config(_fixture_at(tmp_path / "e0"), archive_digest)
    config[field] = "op://vault/item/secret"
    config_raw = canonical_json(config).encode("ascii")
    _write(harness.runtime_root / GRANT_AUTHORITY_SERVICE_ARCHIVE, archive)
    _write(harness.runtime_root / GRANT_AUTHORITY_SERVICE_CONFIG, config_raw)
    _write_json(
        harness.runtime_root / GRANT_AUTHORITY_SERVICE_RUN_PACKET,
        _run_packet(raw_digest(config_raw), archive_digest),
    )

    result = produce_signed_runtime_artifact_manifest(
        manifest_directory=harness.manifest_directory,
        nonce="grant-service-secret-shaped-config",
        issued_at=NOW,
        expires_at=NOW + 120,
        context=harness.context,
        runtime_profile=RUNTIME_PROFILE_GRANT_AUTHORITY_SERVICE,
    )
    assert result.accepted is False


def test_run_packet_archive_substitution_rejects_before_signing(
    tmp_path: Path
) -> None:
    harness = _build_harness(tmp_path)
    e0 = _fixture_at(tmp_path / "e0")
    archive = _valid_archive()
    archive_digest = raw_digest(archive)
    config = _config(e0, archive_digest)
    config_digest = raw_digest(canonical_json(config).encode("ascii"))
    packet = _run_packet(config_digest, archive_digest)
    packet["archive_digest"] = "sha256:" + "f" * 64
    _write(harness.runtime_root / GRANT_AUTHORITY_SERVICE_ARCHIVE, archive)
    _write_json(harness.runtime_root / GRANT_AUTHORITY_SERVICE_CONFIG, config)
    _write_json(harness.runtime_root / GRANT_AUTHORITY_SERVICE_RUN_PACKET, packet)

    result = produce_signed_runtime_artifact_manifest(
        manifest_directory=harness.manifest_directory,
        nonce="grant-service-invalid-run-packet",
        issued_at=NOW,
        expires_at=NOW + 120,
        context=harness.context,
        runtime_profile=RUNTIME_PROFILE_GRANT_AUTHORITY_SERVICE,
    )
    assert result.accepted is False


def test_non_executable_archive_rejects_before_manifest_signing(
    tmp_path: Path,
) -> None:
    harness = _build_harness(tmp_path)
    e0 = _fixture_at(tmp_path / "e0")
    archive = b"attacker-controlled-not-a-zipapp"
    archive_digest = raw_digest(archive)
    config = _config(e0, archive_digest)
    config_raw = canonical_json(config).encode("ascii")
    _write(harness.runtime_root / GRANT_AUTHORITY_SERVICE_ARCHIVE, archive)
    _write(harness.runtime_root / GRANT_AUTHORITY_SERVICE_CONFIG, config_raw)
    _write_json(
        harness.runtime_root / GRANT_AUTHORITY_SERVICE_RUN_PACKET,
        _run_packet(raw_digest(config_raw), archive_digest),
    )

    result = produce_signed_runtime_artifact_manifest(
        manifest_directory=harness.manifest_directory,
        nonce="grant-service-non-executable-archive",
        issued_at=NOW,
        expires_at=NOW + 120,
        context=harness.context,
        runtime_profile=RUNTIME_PROFILE_GRANT_AUTHORITY_SERVICE,
    )

    assert result.accepted is False
    assert not harness.manifest_directory.exists()


def test_use_time_gate_rejects_archive_when_production_gate_is_bypassed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = archive_validation_module.validate_grant_service_archive
    monkeypatch.setattr(
        archive_validation_module,
        "validate_grant_service_archive",
        lambda _raw: {},
    )
    setup = _setup(
        tmp_path,
        monkeypatch,
        archive=b"attacker-controlled-not-a-zipapp",
    )
    monkeypatch.setattr(
        archive_validation_module,
        "validate_grant_service_archive",
        original,
    )

    with pytest.raises(RuntimeArtifactManifestError, match="archive_invalid"):
        _bind(setup)


def test_v1_manifest_downgrade_rejects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    setup = _setup(tmp_path, monkeypatch, runtime_profile=None)
    with pytest.raises(RuntimeArtifactManifestError):
        _bind(setup)


def test_legacy_v5_e0_admission_remains_compatible(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    e0 = _fixture(tmp_path)
    for field in POLICY_FIELDS_V6 - POLICY_FIELDS_V5:
        e0["policy"].pop(field)
    e0["policy"]["schema_version"] = POLICY_SCHEMA_V5
    _rebind_config_and_sign(e0, e0["grant_private"])
    _install_e0_selection(monkeypatch)

    assert e0["boundary"].admit(
        e0["owner_config_path"], e0["policy"]
    ).accepted is True


def test_v2_payload_under_v1_prefix_rejects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    setup = _setup(tmp_path, monkeypatch)
    harness = setup["harness"]
    original = harness.signer.requests[0]
    altered = original.signing_input.replace(SIGNING_PREFIX_V2, SIGNING_PREFIX, 1)
    from dataclasses import replace

    request = replace(
        original,
        signing_input=altered,
        payload_digest=digest({"signing_input": altered}),
    )
    assert validate_runtime_artifact_manifest_signing_request(
        request, harness.authority, harness.authority_boundary, now_epoch=NOW
    ) is None


def test_v2_archive_descriptor_is_bounded() -> None:
    payload = _unsigned_payload_stub()
    payload["artifacts"][-1]["byte_count"] = MAX_SERVICE_ARCHIVE_BYTES
    payload["artifact_generation_digest"] = digest(payload["artifacts"])
    payload["manifest_id"] = manifest_id_for(payload)
    payload["revision"] = payload["manifest_id"][7:]
    with pytest.raises(RuntimeArtifactManifestError, match="descriptor_invalid"):
        validate_unsigned_payload(payload)


def test_binding_modules_have_no_effect_plane_or_secret_refs() -> None:
    root = Path("modules/communication/moltbot_bridge/src")
    names = (
        "reddog_grant_authority_service_artifact_contract.py",
        "reddog_grant_authority_service_authenticated_manifest_binding.py",
        "reddog_grant_authority_service_manifest_verifier.py",
        "reddog_grant_authority_service_manifest_signature.py",
        "reddog_grant_authority_service_owner_binding.py",
    )
    for name in names:
        source = (root / name).read_text(encoding="ascii")
        tree = ast.parse(source)
        imports = {
            alias.name.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        }
        assert not imports.intersection({"subprocess", "socket", "shutil"})
        assert "op://" not in source


def _setup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    runtime_profile: str | None = RUNTIME_PROFILE_GRANT_AUTHORITY_SERVICE,
    archive: bytes | None = None,
) -> dict[str, Any]:
    archive = archive if archive is not None else _valid_archive()
    e0 = _fixture_at(tmp_path / "e0")
    grant_path = tmp_path / "grant"
    grant_path.mkdir()
    harness = _build_harness(grant_path)
    archive_digest = raw_digest(archive)
    config = _config(e0, archive_digest)
    config_raw = canonical_json(config).encode("ascii")
    packet = _run_packet(raw_digest(config_raw), archive_digest)
    _write(harness.runtime_root / GRANT_AUTHORITY_SERVICE_ARCHIVE, archive)
    _write(harness.runtime_root / GRANT_AUTHORITY_SERVICE_CONFIG, config_raw)
    _write_json(harness.runtime_root / GRANT_AUTHORITY_SERVICE_RUN_PACKET, packet)
    result = produce_signed_runtime_artifact_manifest(
        manifest_directory=harness.manifest_directory,
        nonce="grant-service-manifest-1",
        issued_at=NOW,
        expires_at=NOW + 120,
        context=harness.context,
        runtime_profile=runtime_profile,
    )
    assert result.accepted is True
    manifest = harness.read_manifest()
    _bind_target_signer(e0, manifest)
    _rebind_config_and_sign(e0, e0["grant_private"])
    _align_manifest_authority(e0, harness, manifest)
    _bind_policy(e0, manifest)
    _install_e0_selection(monkeypatch)
    monkeypatch.setattr(verifier_module, "_now_epoch", lambda: NOW)
    owner_root = tmp_path / "owner"
    owner_root.mkdir()
    owner = _owner(owner_root, config_id=str(e0["selection"]["owner_config_id"]))
    owner["independent_grant_authority"].update(
        {
            "authority_root": str(harness.runtime_root.resolve()),
            "authority_socket_path": str(
                (harness.runtime_root / "grant-authority.sock").resolve()
            ),
        }
    )
    _install_owner_config(monkeypatch, owner)
    return {
        "e0": e0, "harness": harness, "manifest": manifest,
        "owner": owner, "archive_digest": archive_digest,
    }


def _config(e0: dict[str, Any], archive_digest: str) -> dict[str, str]:
    policy = e0["policy"]
    return {
        "schema_version": CONFIG_SCHEMA,
        "service_id": SERVICE_ID,
        "signer_agent_id": str(policy["grant_authority_signer_agent_id"]),
        "signer_profile_id": str(policy["grant_authority_signer_profile_id"]),
        "public_key": str(policy["grant_authority_public_key"]),
        "key_fingerprint": str(policy["grant_authority_key_fingerprint"]),
        "key_epoch": str(policy["grant_authority_key_epoch"]),
        "signing_key_ref_hash": str(policy["grant_authority_signing_key_ref_hash"]),
        "audit_mac_key_ref_hash": str(policy["grant_authority_audit_mac_key_ref_hash"]),
        "permission_snapshot_digest": str(policy["grant_authority_permission_snapshot_digest"]),
        "permission_snapshot_receipt_id": str(policy["grant_authority_permission_snapshot_receipt_id"]),
        "archive_digest": archive_digest,
    }


def _fixture_at(path: Path) -> dict[str, Any]:
    path.mkdir(parents=True, exist_ok=True)
    return _fixture(path)


def _run_packet(config_digest: str, archive_digest: str) -> dict[str, str]:
    return {
        "schema_version": RUN_PACKET_SCHEMA,
        "service_id": SERVICE_ID,
        "config_filename": GRANT_AUTHORITY_SERVICE_CONFIG,
        "config_digest": config_digest,
        "archive_filename": GRANT_AUTHORITY_SERVICE_ARCHIVE,
        "archive_digest": archive_digest,
        "artifact_set_digest": digest(
            {"archive_digest": archive_digest, "config_digest": config_digest}
        ),
        "entrypoint": ENTRYPOINT,
    }


def _bind_policy(e0: dict[str, Any], manifest: dict[str, Any]) -> None:
    descriptors = {item["filename"]: item for item in manifest["artifacts"]}
    config = descriptors.get(GRANT_AUTHORITY_SERVICE_CONFIG)
    run_packet = descriptors.get(GRANT_AUTHORITY_SERVICE_RUN_PACKET)
    _bind_target_signer(e0, manifest)
    e0["policy"].update(
        {
            "grant_authority_manifest_id": manifest["manifest_id"],
            "grant_authority_artifact_generation_digest": manifest["artifact_generation_digest"],
            "grant_authority_config_digest": (
                config["content_digest"] if config else e0["policy"]["grant_authority_config_digest"]
            ),
            "grant_authority_run_packet_digest": (
                run_packet["content_digest"] if run_packet else e0["policy"]["grant_authority_run_packet_digest"]
            ),
        }
    )
    _rebind_config_and_sign(e0, e0["grant_private"])


def _align_manifest_authority(
    e0: dict[str, Any], harness: Any, manifest: dict[str, Any]
) -> None:
    old_path = next(harness.manifest_directory.glob("*.json"))
    manifest["repo_root_digest"] = raw_digest(
        str(e0["boundary"]._repo_root.resolve()).encode("utf-8")
    )
    manifest["signer_service_config_digest"] = e0["policy"]["config_digest"]
    manifest["manifest_id"] = manifest_id_for(manifest)
    manifest["revision"] = manifest["manifest_id"][7:]
    _self_sign_manifest(manifest, harness.reddog_private_key)
    new_path = harness.manifest_directory / (manifest["revision"] + ".json")
    _write_json(new_path, manifest)
    if old_path != new_path:
        old_path.unlink()


def _replace_signed_manifest_field(
    setup: dict[str, Any], *, field: str, value: str
) -> None:
    manifest = setup["manifest"]
    old_path = next(setup["harness"].manifest_directory.glob("*.json"))
    manifest[field] = value
    manifest["manifest_id"] = manifest_id_for(manifest)
    manifest["revision"] = manifest["manifest_id"][7:]
    _self_sign_manifest(manifest, setup["harness"].reddog_private_key)
    new_path = setup["harness"].manifest_directory / (
        manifest["manifest_id"][7:] + ".json"
    )
    _write_json(new_path, manifest)
    if old_path != new_path:
        old_path.unlink()
    _bind_policy(setup["e0"], manifest)


def _bind_target_signer(
    e0: dict[str, Any], manifest: dict[str, Any]
) -> None:
    policy = e0["policy"]
    policy["target_signer_public_key"] = manifest["signer_public_key"]
    policy["target_signer_key_fingerprint"] = manifest[
        "signer_key_fingerprint"
    ]
    policy["target_signer_key_epoch"] = manifest["key_epoch"]
    config = e0["config"]
    control = config["control_loop_authority_policy"]
    control["signer_public_key"] = manifest["signer_public_key"]
    control["key_epoch"] = manifest["key_epoch"]
    profile = config["key_provider_profiles"][0]
    profile["expected_public_key"] = manifest["signer_public_key"]
    profile["expected_key_fingerprint"] = manifest["signer_key_fingerprint"]
    profile["expected_key_epoch"] = manifest["key_epoch"]


def _bind(setup: dict[str, Any]):
    return bind_grant_authority_service_manifest(
        owner_config_path=setup["e0"]["owner_config_path"],
        repo_root=setup["e0"]["boundary"]._repo_root,
        owner_policy=setup["e0"]["policy"],
    )


def _write_json(path: Path, value: dict[str, Any]) -> None:
    _write(path, canonical_json(value).encode("ascii"))


def _write(path: Path, value: bytes) -> None:
    path.write_bytes(value)


def _valid_archive() -> bytes:
    return build_grant_service_archive(
        {
            "__main__.py": ARCHIVE_MAIN,
            "reddog_grant_authority_service.py": (
                b"import argparse\n\n"
                b"def main(argv=None):\n"
                b"    parser = argparse.ArgumentParser()\n"
                b"    parser.parse_args(argv)\n"
                b"    return 2\n"
            ),
        },
        source_commit_sha="1" * 40,
    )


def _install_e0_selection(monkeypatch: pytest.MonkeyPatch) -> None:
    def load(**_kwargs: object) -> tuple[object, _SelectionBoundary]:
        capability = object()
        return capability, _SelectionBoundary(capability, _CURRENT_SELECTION)

    monkeypatch.setattr(
        current_selection_module, "load_system_service_manifest_selection", load
    )


def _install_owner_config(
    monkeypatch: pytest.MonkeyPatch, owner: dict[str, Any]
) -> None:
    from modules.communication.moltbot_bridge.src import (
        reddog_signer_system_service_manifest_selection_loader as loader,
    )

    monkeypatch.setattr(loader, "_load_owner_config", lambda *_a, **_k: owner)


def _unsigned_payload_stub() -> dict[str, Any]:
    names = (
        GRANT_AUTHORITY_SERVICE_CONFIG,
        GRANT_AUTHORITY_SERVICE_RUN_PACKET,
        GRANT_AUTHORITY_SERVICE_ARCHIVE,
    )
    payload = {
        "schema_version": "reddog_signed_runtime_artifact_manifest.v2",
        "runtime_profile": RUNTIME_PROFILE_GRANT_AUTHORITY_SERVICE,
        "manifest_id": "", "revision": "",
        "repo_root_digest": "sha256:" + "1" * 64,
        "runtime_root_digest": "sha256:" + "2" * 64,
        "queue_item_id": "queue-1", "work_state_revision": "3" * 64,
        "work_authority_digest": "sha256:" + "4" * 64,
        "publication_receipt_id": "sha256:" + "5" * 64,
        "publication_binding_digest": "sha256:" + "6" * 64,
        "artifact_count": 3, "artifact_generation_digest": "",
        "artifacts": [
            {"filename": name, "byte_count": 1, "content_digest": "sha256:" + f"{i:x}" * 64}
            for i, name in enumerate(names, start=1)
        ],
        "issuer_principal_id": "principal:owner", "signer_public_key": "public-key",
        "signer_key_fingerprint": "sha256:" + "7" * 64, "key_epoch": "epoch-1",
        "consensus_receipt_digest": "sha256:" + "8" * 64,
        "authority_profile_digest": "sha256:" + "9" * 64,
        "authority_profile_source_receipt_id": "sha256:" + "a" * 64,
        "signer_service_config_digest": "sha256:" + "b" * 64,
        "nonce": "nonce-1", "issued_at": NOW, "expires_at": NOW + 120,
    }
    return payload
