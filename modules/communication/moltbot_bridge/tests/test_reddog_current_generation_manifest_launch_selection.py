"""Security tests for current-generation external signer launch selection."""

from __future__ import annotations

import ast
import copy
import json
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
