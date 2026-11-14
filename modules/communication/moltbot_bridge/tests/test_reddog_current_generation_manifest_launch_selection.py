"""Security tests for current-generation external signer launch selection."""

from __future__ import annotations

import ast
import copy
import json
from dataclasses import replace
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import pytest

from modules.communication.moltbot_bridge.src.reddog_current_generation_manifest_launch_selection import (
    create_current_generation_manifest_launch_selection_boundary,
)
from modules.communication.moltbot_bridge.src import (
    reddog_current_generation_manifest_launch_selection as selection_module,
    reddog_runtime_artifact_manifest_contract as manifest_contract,
)
from modules.communication.moltbot_bridge.src.reddog_ed25519_signature_verifier_backend import (
    Ed25519SignatureVerifier,
)
from modules.communication.moltbot_bridge.src.reddog_runtime_artifact_manifest_contract import (
    RuntimeArtifactManifestError,
)
from modules.communication.moltbot_bridge.src.reddog_runtime_artifact_manifest_launch_selection import (
    create_runtime_artifact_manifest_launch_selection_boundary,
)
from modules.communication.moltbot_bridge.tests.reddog_signer_generation_test_support import (
    create_lifecycle_generation_authority,
)
from modules.communication.moltbot_bridge.src.reddog_signer_runtime_generation_reader import (
    require_signer_runtime_generation_reader_authority,
)
from modules.communication.moltbot_bridge.src.reddog_signer_runtime_generation_contract import (
    SignerRuntimeGenerationBinding,
)
from modules.communication.moltbot_bridge.tests.test_reddog_signed_runtime_artifact_manifest import (
    NOW,
    ManifestHarness,
    _build_harness,
    _sign,
)

OWNER_CONFIG_ID = "sha256:" + "6" * 64


@pytest.fixture(autouse=True)
def _trusted_clock(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(selection_module, "_now_epoch", lambda: NOW)


def _prepared(
    tmp_path: Path,
    *,
    generation_overrides: dict[str, Any] | None = None,
):
    harness = _build_harness(tmp_path)
    produced = harness.produce()
    assert produced.accepted is True
    manifest = harness.read_manifest()
    legacy = create_runtime_artifact_manifest_launch_selection_boundary(
        authority=harness.authority,
        authority_boundary=harness.authority_boundary,
        signature_verifier=Ed25519SignatureVerifier(),
    )
    values = dict(
        legacy.consume(legacy.select(manifest, now_epoch=NOW))
    )
    values.update(generation_overrides or {})
    authority, boundary = create_lifecycle_generation_authority(
        harness.repo_root, values
    )
    activation = require_signer_runtime_generation_reader_authority(
        authority, boundary
    ).load()
    assert activation is not None
    owner_authority, owner_boundary = _owner_authority(
        harness, activation
    )
    subject = create_current_generation_manifest_launch_selection_boundary(
        owner_authority=owner_authority,
        owner_authority_boundary=owner_boundary,
        generation_reader_authority=authority,
        generation_reader_authority_boundary=boundary,
    )
    return harness, manifest, subject


def test_current_generation_mints_one_shot_selection(tmp_path: Path) -> None:
    harness, _manifest, subject = _prepared(tmp_path)

    capability = subject.select({}, now_epoch=NOW + 86_400)
    selected = subject.consume(capability)

    assert selected["runtime_root"] == str(harness.runtime_root.resolve())
    assert selected["config_path"].endswith("signer_service_config.json")
    assert selected["run_packet_path"].endswith(
        "signer_service_run_packet.json"
    )
    assert selected["generation"] == 1
    with pytest.raises(
        RuntimeArtifactManifestError,
        match="manifest_launch_selection_unverified",
    ):
        subject.consume(capability)


def test_trusted_consumer_runs_inside_generation_fence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _harness, _manifest, subject = _prepared(tmp_path)
    state = {"active": False}

    @contextmanager
    def fence(*_args: object, **_kwargs: object):
        state["active"] = True
        try:
            yield
        finally:
            state["active"] = False

    monkeypatch.setattr(
        selection_module, "reddog_runtime_artifact_generation_lock", fence
    )
    capability = subject.select({}, now_epoch=NOW)

    with subject._lease_current(capability) as _selected:
        assert state["active"] is True
    assert state["active"] is False


def test_selection_expires_before_consumption(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _harness, _manifest, subject = _prepared(tmp_path)
    monkeypatch.setattr(selection_module, "_now_epoch", lambda: NOW)
    capability = subject.select({}, now_epoch=NOW)
    monkeypatch.setattr(selection_module, "_now_epoch", lambda: NOW + 31)

    with pytest.raises(
        RuntimeArtifactManifestError,
        match="manifest_launch_selection_expired",
    ):
        subject.consume(capability)


def test_selection_freshness_rechecks_after_generation_lock_wait(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _harness, _manifest, subject = _prepared(tmp_path)
    monkeypatch.setattr(selection_module, "_now_epoch", lambda: NOW)
    capability = subject.select({}, now_epoch=NOW)
    times = iter((NOW, NOW + 31))
    monkeypatch.setattr(selection_module, "_now_epoch", lambda: next(times))

    with pytest.raises(
        RuntimeArtifactManifestError,
        match="manifest_launch_selection_expired",
    ):
        subject.consume(capability)


def test_expired_manifest_rejects_at_selection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _harness, _manifest, subject = _prepared(tmp_path)
    monkeypatch.setattr(selection_module, "_now_epoch", lambda: NOW + 121)

    with pytest.raises(
        RuntimeArtifactManifestError, match="manifest_expired"
    ):
        subject.select({}, now_epoch=NOW)


def test_future_manifest_rejects_at_selection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _harness, _manifest, subject = _prepared(tmp_path)
    monkeypatch.setattr(selection_module, "_now_epoch", lambda: NOW - 1)

    with pytest.raises(
        RuntimeArtifactManifestError, match="manifest_expired"
    ):
        subject.select({}, now_epoch=NOW)


def test_caller_manifest_is_never_trusted(tmp_path: Path) -> None:
    _harness, manifest, subject = _prepared(tmp_path)
    attacker = dict(manifest)
    attacker["manifest_id"] = "sha256:" + "f" * 64

    selected = subject.consume(subject.select(attacker, now_epoch=NOW))

    assert selected["manifest_id"] == manifest["manifest_id"]


def test_generation_manifest_binding_mismatch_rejects(tmp_path: Path) -> None:
    _harness, _manifest, subject = _prepared(
        tmp_path,
        generation_overrides={"config_digest": "sha256:" + "9" * 64},
    )

    with pytest.raises(
        RuntimeArtifactManifestError,
        match="current_generation_manifest_binding_mismatch",
    ):
        subject.select({}, now_epoch=NOW)


def test_expected_generation_trust_mismatch_rejects(tmp_path: Path) -> None:
    harness = _build_harness(tmp_path)
    assert harness.produce().accepted is True
    values = _legacy_values(harness)
    authority, boundary = create_lifecycle_generation_authority(
        harness.repo_root, values
    )
    activation = require_signer_runtime_generation_reader_authority(
        authority, boundary
    ).load()
    assert activation is not None
    owner_authority, owner_boundary = _owner_authority(
        harness,
        activation,
        authenticator_id="attacker-generation",
    )
    subject = create_current_generation_manifest_launch_selection_boundary(
        owner_authority=owner_authority,
        owner_authority_boundary=owner_boundary,
        generation_reader_authority=authority,
        generation_reader_authority_boundary=boundary,
    )

    with pytest.raises(
        RuntimeArtifactManifestError,
        match="current_generation_trust_anchor_mismatch",
    ):
        subject.select({}, now_epoch=NOW)


def test_generation_raw_artifact_binding_mismatch_rejects(
    tmp_path: Path,
) -> None:
    _harness, _manifest, subject = _prepared(
        tmp_path,
        generation_overrides={"config_raw_digest": "sha256:" + "8" * 64},
    )

    with pytest.raises(
        RuntimeArtifactManifestError,
        match="current_generation_artifact_binding_mismatch",
    ):
        subject.select({}, now_epoch=NOW)


def test_tampered_manifest_signature_rejects(tmp_path: Path) -> None:
    harness, manifest, subject = _prepared(tmp_path)
    manifest["signature"] = _tamper(str(manifest["signature"]))
    _replace_manifest(harness, manifest)

    with pytest.raises(
        RuntimeArtifactManifestError, match="manifest_signature_invalid"
    ):
        subject.select({}, now_epoch=NOW)


def test_tampered_manifest_attestation_rejects(tmp_path: Path) -> None:
    harness, manifest, subject = _prepared(tmp_path)
    manifest["signer_audit_attestation_signature"] = _tamper(
        str(manifest["signer_audit_attestation_signature"])
    )
    _replace_manifest(harness, manifest)

    with pytest.raises(
        RuntimeArtifactManifestError,
        match="manifest_audit_attestation_invalid",
    ):
        subject.select({}, now_epoch=NOW)


def test_tampered_runtime_artifact_rejects(tmp_path: Path) -> None:
    harness, _manifest, subject = _prepared(tmp_path)
    target = harness.runtime_root / "signer_service_config.json"
    target.write_bytes(target.read_bytes() + b" ")

    with pytest.raises(
        RuntimeArtifactManifestError, match="manifest_artifacts_changed"
    ):
        subject.select({}, now_epoch=NOW)


def test_missing_content_addressed_manifest_rejects(tmp_path: Path) -> None:
    harness, _manifest, subject = _prepared(tmp_path)
    next(harness.manifest_directory.glob("*.json")).unlink()

    with pytest.raises(
        RuntimeArtifactManifestError,
        match="current_generation_manifest_missing",
    ):
        subject.select({}, now_epoch=NOW)


def test_forged_capability_rejects(tmp_path: Path) -> None:
    _harness, _manifest, subject = _prepared(tmp_path)

    with pytest.raises(
        RuntimeArtifactManifestError,
        match="manifest_launch_selection_unverified",
    ):
        subject.consume(object())


def test_forged_owner_authority_rejects(tmp_path: Path) -> None:
    harness = _build_harness(tmp_path)
    assert harness.produce().accepted is True
    authority, reader_boundary = create_lifecycle_generation_authority(
        harness.repo_root, _legacy_values(harness)
    )
    activation = require_signer_runtime_generation_reader_authority(
        authority, reader_boundary
    ).load()
    assert activation is not None
    _owner, owner_boundary = _owner_authority(harness, activation)

    with pytest.raises(
        RuntimeArtifactManifestError,
        match="launch_owner_authority_unverified",
    ):
        create_current_generation_manifest_launch_selection_boundary(
            owner_authority=object(),
            owner_authority_boundary=owner_boundary,
            generation_reader_authority=authority,
            generation_reader_authority_boundary=reader_boundary,
        )


def test_forged_owner_boundary_rejects(tmp_path: Path) -> None:
    harness = _build_harness(tmp_path)
    assert harness.produce().accepted is True
    authority, reader_boundary = create_lifecycle_generation_authority(
        harness.repo_root, _legacy_values(harness)
    )

    with pytest.raises(
        RuntimeArtifactManifestError,
        match="launch_owner_boundary_invalid",
    ):
        create_current_generation_manifest_launch_selection_boundary(
            owner_authority=object(),
            owner_authority_boundary=object(),  # type: ignore[arg-type]
            generation_reader_authority=authority,
            generation_reader_authority_boundary=reader_boundary,
        )


def test_capability_cannot_be_copied_or_pickled(tmp_path: Path) -> None:
    _harness, _manifest, subject = _prepared(tmp_path)
    capability = subject.select({}, now_epoch=NOW)

    with pytest.raises(TypeError, match="not_copyable"):
        copy.copy(capability)
    with pytest.raises(TypeError, match="not_copyable"):
        copy.deepcopy(capability)


def test_only_one_concurrent_consumer_succeeds(tmp_path: Path) -> None:
    _harness, _manifest, subject = _prepared(tmp_path)
    capability = subject.select({}, now_epoch=NOW)

    def consume() -> bool:
        try:
            subject.consume(capability)
            return True
        except RuntimeArtifactManifestError:
            return False

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = tuple(pool.map(lambda _value: consume(), range(2)))

    assert sorted(outcomes) == [False, True]


def test_generation_advance_before_consumption_rejects(
    tmp_path: Path,
) -> None:
    harness = _build_harness(tmp_path)
    assert harness.produce().accepted is True
    first_values = _legacy_values(harness)
    authority, boundary, writer = create_lifecycle_generation_authority(
        harness.repo_root, first_values, return_writer=True
    )
    first = require_signer_runtime_generation_reader_authority(
        authority, boundary
    ).load()
    assert first is not None
    owner_authority, owner_boundary = _owner_authority(harness, first)
    subject = create_current_generation_manifest_launch_selection_boundary(
        owner_authority=owner_authority,
        owner_authority_boundary=owner_boundary,
        generation_reader_authority=authority,
        generation_reader_authority_boundary=boundary,
    )
    capability = subject.select({}, now_epoch=NOW)
    _change_unbound_artifact(harness)
    produced = harness.produce(nonce="manifest-nonce-2")
    assert produced.accepted is True
    second_values = _legacy_values(harness, Path(str(produced.output_path)))
    writer.activate(
        SignerRuntimeGenerationBinding(
            generation=2,
            manifest_id=str(second_values["manifest_id"]),
            artifact_generation_digest=str(
                second_values["artifact_generation_digest"]
            ),
            config_digest=str(second_values["config_digest"]),
            config_raw_digest=str(second_values["config_raw_digest"]),
            run_packet_digest=str(second_values["run_packet_digest"]),
        ),
        expected_revision=first.revision,
    )

    with pytest.raises(
        RuntimeArtifactManifestError,
        match="manifest_launch_selection_stale",
    ):
        subject.consume(capability)


def test_module_has_no_process_or_mutation_authority() -> None:
    source = Path(
        "modules/communication/moltbot_bridge/src/"
        "reddog_current_generation_manifest_launch_selection.py"
    ).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }

    assert imported.isdisjoint(
        {"subprocess", "socket", "multiprocessing", "shutil"}
    )
    assert ".write_" not in source
    assert "Popen" not in source
    assert "system(" not in source


def _replace_manifest(
    harness: ManifestHarness, manifest: dict[str, Any]
) -> None:
    target = next(harness.manifest_directory.glob("*.json"))
    target.write_text(
        json.dumps(manifest, sort_keys=True, separators=(",", ":")),
        encoding="utf-8",
    )


def _tamper(value: str) -> str:
    return ("B" if value.startswith("A") else "A") + value[1:]


def _legacy_values(
    harness: ManifestHarness, path: Path | None = None
) -> dict[str, Any]:
    manifest = harness.read_manifest(path)
    boundary = create_runtime_artifact_manifest_launch_selection_boundary(
        authority=harness.authority,
        authority_boundary=harness.authority_boundary,
        signature_verifier=Ed25519SignatureVerifier(),
    )
    return dict(
        boundary.consume(boundary.select(manifest, now_epoch=NOW))
    )


def _owner_authority(
    harness: ManifestHarness,
    activation: Any,
    *,
    authenticator_id: str | None = None,
):
    return selection_module._issue_current_generation_launch_owner_authority(
        repo_root=harness.repo_root,
        runtime_root=harness.runtime_root,
        anchor_id=activation.anchor_id,
        authenticator_id=(
            authenticator_id or activation.authenticator_id
        ),
        high_water_store_id=activation.high_water_store_id,
        high_water_durability_receipt_id=(
            activation.high_water_durability_receipt_id
        ),
        owner_config_id=OWNER_CONFIG_ID,
        generation_public_key="public-key-v1:generation-authority",
    )


def _change_unbound_artifact(harness: ManifestHarness) -> None:
    target = harness.runtime_root / "permission_snapshots.json"
    payload = json.loads(target.read_text(encoding="utf-8"))
    payload["generation_test_marker"] = "second-generation"
    target.write_text(
        json.dumps(payload, sort_keys=True, separators=(",", ":")),
        encoding="utf-8",
    )


def _initial_manifest(harness: ManifestHarness) -> dict[str, Any]:
    """Build only a signed test fixture, without claiming enrollment authority."""
    manifest = {
        key: value for key, value in harness.read_manifest().items()
        if key in manifest_contract.UNSIGNED_FIELDS_INITIAL
    }
    manifest.update(
        schema_version=manifest_contract.SCHEMA_VERSION_INITIAL,
        enrollment_approval_digest="sha256:" + "a" * 64,
        source_commit_sha="b" * 40,
    )
    _initial_id(manifest)
    manifest["signature"] = _sign(
        harness.reddog_private_key,
        manifest_contract.canonical_signing_input(manifest),
    )
    return manifest


def _initial_id(manifest: dict[str, Any]) -> None:
    manifest["manifest_id"] = manifest_contract.manifest_id_for(manifest)
    manifest["revision"] = manifest["manifest_id"][7:]


@pytest.fixture
def initial_manifest(tmp_path: Path):
    harness = _build_harness(tmp_path)
    assert harness.produce().accepted is True
    return harness, _initial_manifest(harness)


@pytest.mark.parametrize("commit_length", (40, 64))
def test_initial_codec_has_distinct_domain_and_complete_artifacts(
    initial_manifest, commit_length: int,
) -> None:
    _harness, manifest = initial_manifest
    manifest["source_commit_sha"] = "b" * commit_length
    _initial_id(manifest)
    assert manifest_contract.validate_signed_payload(manifest) == manifest
    assert manifest_contract.canonical_signing_input(manifest).startswith(
        manifest_contract.SIGNING_PREFIX_INITIAL
    )
    assert tuple(item["filename"] for item in manifest["artifacts"]) == (
        manifest_contract.REQUIRED_RUNTIME_ARTIFACTS
    )
    assert set(manifest) == manifest_contract.UNSIGNED_FIELDS_INITIAL | {"signature"}


@pytest.mark.parametrize("field", (
    "queue_item_id", "work_state_revision", "work_authority_digest",
    "publication_receipt_id", "publication_binding_digest",
    "consensus_receipt_digest", "authority_profile_source_receipt_id",
    "signer_audit_mac", "signer_audit_attestation_signature", "runtime_profile",
))
def test_initial_codec_rejects_legacy_authority_and_audit_fields(
    initial_manifest, field: str,
) -> None:
    _harness, manifest = initial_manifest
    manifest[field] = "sha256:" + "c" * 64
    _initial_id(manifest)
    with pytest.raises(RuntimeArtifactManifestError, match="manifest_fields_invalid"):
        manifest_contract.validate_signed_payload(manifest)
    with pytest.raises(RuntimeArtifactManifestError, match="manifest_fields_invalid"):
        manifest_contract.canonical_signing_input(manifest)


@pytest.mark.parametrize("schema", (
    manifest_contract.SCHEMA_VERSION,
    manifest_contract.SCHEMA_VERSION_V2,
    manifest_contract.SCHEMA_VERSION_V3,
))
def test_initial_codec_cannot_be_relabelled_legacy(initial_manifest, schema: str) -> None:
    _harness, manifest = initial_manifest
    manifest["schema_version"] = schema
    _initial_id(manifest)
    with pytest.raises(RuntimeArtifactManifestError, match="manifest_fields_invalid"):
        manifest_contract.validate_signed_payload(manifest)


@pytest.mark.parametrize("commit", (None, 123, "", "a" * 39, "a" * 41, "a" * 65, "A" * 40, "g" * 64))
def test_initial_codec_rejects_invalid_source_commit(initial_manifest, commit) -> None:
    _harness, manifest = initial_manifest
    manifest["source_commit_sha"] = commit
    _initial_id(manifest)
    with pytest.raises(RuntimeArtifactManifestError, match="manifest_source_commit_invalid"):
        manifest_contract.validate_signed_payload(manifest)


@pytest.mark.parametrize("field", ("enrollment_approval_digest", "source_commit_sha", "signature"))
def test_initial_codec_requires_enrollment_fields_and_signature(initial_manifest, field: str) -> None:
    _harness, manifest = initial_manifest
    manifest.pop(field)
    _initial_id(manifest)
    with pytest.raises(RuntimeArtifactManifestError):
        manifest_contract.validate_signed_payload(manifest)


@pytest.mark.parametrize("mutation", ("approval", "descriptor", "duplicate", "missing", "time", "id"))
def test_initial_codec_rejects_malformed_bound_values(initial_manifest, mutation: str) -> None:
    _harness, manifest = initial_manifest
    if mutation == "approval":
        manifest["enrollment_approval_digest"] = "not-a-digest"
    elif mutation == "descriptor":
        manifest["artifacts"][0]["filename"] = "../authority.json"
    elif mutation == "duplicate":
        manifest["artifacts"][1] = dict(manifest["artifacts"][0])
    elif mutation == "missing":
        manifest["artifacts"].pop()
        manifest["artifact_count"] -= 1
    elif mutation == "time":
        manifest["issued_at"] = True
    manifest["artifact_generation_digest"] = manifest_contract.digest(manifest["artifacts"])
    _initial_id(manifest)
    if mutation == "id":
        manifest["revision"] = "f" * 64
    with pytest.raises(RuntimeArtifactManifestError):
        manifest_contract.validate_signed_payload(manifest)


def test_initial_public_reader_requires_authenticated_generation(initial_manifest) -> None:
    harness, manifest = initial_manifest
    values = _legacy_values(harness)
    values["manifest_id"] = manifest["manifest_id"]
    target = harness.manifest_directory / f"{manifest['revision']}.json"
    target.write_text(json.dumps(manifest), encoding="utf-8")
    authority, boundary = create_lifecycle_generation_authority(harness.repo_root, values)
    activation = require_signer_runtime_generation_reader_authority(authority, boundary).load()
    assert activation is not None
    owner, owner_boundary = _owner_authority(harness, activation)
    subject = create_current_generation_manifest_launch_selection_boundary(
        owner_authority=owner, owner_authority_boundary=owner_boundary,
        generation_reader_authority=authority, generation_reader_authority_boundary=boundary,
    )
    selected = subject.consume(subject.select({}, now_epoch=NOW))
    assert selected["manifest_id"] == manifest["manifest_id"]
    assert selected["generation"] == 1
    with pytest.raises(RuntimeArtifactManifestError, match="initial_manifest_generation_invalid"):
        selection_module._verify_manifest(
            manifest, replace(activation, generation=2), harness.repo_root,
            harness.runtime_root, Ed25519SignatureVerifier(),
        )
    target.write_text(json.dumps({**manifest, "signature": _tamper(manifest["signature"])}), encoding="utf-8")
    with pytest.raises(RuntimeArtifactManifestError, match="manifest_signature_invalid"):
        subject.select({}, now_epoch=NOW)


def test_initial_self_signature_does_not_replace_generation_authority(tmp_path: Path) -> None:
    harness, _manifest, subject = _prepared(tmp_path)
    _replace_manifest(harness, _initial_manifest(harness))
    with pytest.raises(RuntimeArtifactManifestError, match="current_generation_manifest_binding_mismatch"):
        subject.select({}, now_epoch=NOW)


def test_initial_signature_cannot_reuse_legacy_signing_domain(initial_manifest) -> None:
    harness, manifest = initial_manifest
    unsigned = {key: value for key, value in manifest.items() if key != "signature"}
    manifest["signature"] = _sign(
        harness.reddog_private_key,
        manifest_contract.SIGNING_PREFIX + manifest_contract.canonical_json(unsigned),
    )
    with pytest.raises(RuntimeArtifactManifestError, match="manifest_signature_invalid"):
        selection_module._verify_signatures(manifest, Ed25519SignatureVerifier())
