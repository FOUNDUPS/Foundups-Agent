"""Tests for signed signer-runtime generation publication and activation."""

from __future__ import annotations

import json
import multiprocessing
import os
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event, Thread

import pytest
from cryptography.hazmat.primitives import serialization

from modules.communication.moltbot_bridge.src.reddog_atomic_signer_runtime_generation_high_water import (
    AtomicSignerRuntimeGenerationHighWaterStore,
)
from modules.communication.moltbot_bridge.src.reddog_signer_runtime_atomic_provisioning import (
    SignerRuntimeAtomicProvisioningContext,
    provision_signer_runtime_generation,
)
from modules.communication.moltbot_bridge.src.reddog_signed_runtime_artifact_manifest import (
    SignedRuntimeArtifactManifestResult,
)
from modules.communication.moltbot_bridge.src.reddog_signer_runtime_generation_anchor import (
    DurableSignerRuntimeGenerationAnchor,
)
from modules.communication.moltbot_bridge.tests.reddog_signer_generation_test_support import (
    GenerationSigner,
    HighWaterBoundary,
    generation_witness_binding,
)
from modules.communication.moltbot_bridge.tests.reddog_signer_runtime_provisioning_process_test_support import (
    process_provision as _process_provision,
)
from modules.communication.moltbot_bridge.tests.test_reddog_signed_runtime_artifact_manifest import (
    NOW,
    _build_harness,
)
from modules.communication.moltbot_bridge.src.reddog_sqlite_monotonic_authority_store import (
    SqliteMonotonicAuthorityStore,
)
from modules.infrastructure.shared_utilities.reddog_runtime_artifact_generation import (
    reddog_runtime_artifact_generation_lock,
)


@pytest.fixture(autouse=True)
def _fixed_provisioning_clock(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import modules.communication.moltbot_bridge.src.reddog_signer_runtime_atomic_provisioning as target

    monkeypatch.setattr(target, "_trusted_now", lambda: NOW)
    if os.name != "nt":
        monkeypatch.setattr(
            target,
            "runtime_artifact_activation_lease",
            _test_only_activation_lease,
        )


@contextmanager
def _test_only_activation_lease(*_args, **_kwargs):
    """Exercise coordinator logic where the OS lease is unavailable."""

    yield


def _private_key_bytes(private_key) -> bytes:
    return private_key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )


def _context(tmp_path: Path):
    harness = _build_harness(tmp_path)
    authority_root = tmp_path / "generation-authority"
    anchor_root = tmp_path / "generation-anchor"
    witness_root = tmp_path / "generation-witness"
    authority_root.mkdir()
    anchor_root.mkdir()
    witness_root.mkdir()
    signing = GenerationSigner()
    witness = SqliteMonotonicAuthorityStore(
        witness_root / "generation.sqlite3",
        allowed_root=witness_root,
        repo_root=harness.repo_root,
        store_id="signer-generation-witness:v1",
        durability_receipt_id="sha256:" + "7" * 64,
    )
    high_water = AtomicSignerRuntimeGenerationHighWaterStore(
        authority_root / "high-water.json",
        allowed_root=authority_root,
        repo_root=harness.repo_root,
        store_id="signer-high-water:v1",
        durability_receipt_id="sha256:" + "8" * 64,
        signer=signing,
        verifier=signing.verifier,
        generation_witness_store=witness,
        generation_witness_binding=generation_witness_binding(
            authenticator_id=signing.authenticator_id,
            runtime_root=harness.runtime_root,
            high_water_store_id="signer-high-water:v1",
            high_water_durability_receipt_id="sha256:" + "8" * 64,
            witness_store_id=witness.store_id,
            witness_durability_receipt_id=witness.durability_receipt_id,
        ),
    )
    boundary = HighWaterBoundary(high_water)
    anchor = DurableSignerRuntimeGenerationAnchor(
        anchor_root / "generation-anchor.json",
        allowed_root=anchor_root,
        repo_root=harness.repo_root,
        anchor_id="reddog-signer:production",
        signer=signing,
        verifier=signing.verifier,
        high_water_authority=boundary.capability,
        high_water_authority_boundary=boundary,
    )
    context = SignerRuntimeAtomicProvisioningContext(
        manifest_signing=harness.context,
        generation_anchor=anchor,
    )
    return harness, anchor, context


def _provision(context):
    return provision_signer_runtime_generation(
        nonce="provision-generation-1",
        ttl_seconds=120,
        context=context,
    )


def test_valid_final_root_is_signed_and_activated_last(
    tmp_path: Path,
) -> None:
    harness, anchor, context = _context(tmp_path)

    result = _provision(context)

    assert result.accepted is True
    assert result.generation == 1
    assert result.no_service_start_performed_by_coordinator is True
    assert Path(str(result.manifest_path)).is_file()
    activation = anchor.load()
    assert activation is not None
    assert activation.manifest_id == result.manifest_id
    assert activation.revision == result.activation_revision
    assert harness.repo_root not in Path(str(result.manifest_path)).parents


def test_generation_root_is_used_in_place_without_copy(
    tmp_path: Path,
) -> None:
    harness, _, context = _context(tmp_path)
    original_paths = {
        path.name: path.resolve()
        for path in harness.runtime_root.glob("*.json")
    }

    result = _provision(context)

    assert result.accepted is True
    final_paths = {
        path.name: path.resolve()
        for path in harness.runtime_root.glob("*.json")
        if not path.name.startswith(".reddog-runtime-artifact-generation-seal")
    }
    assert final_paths == original_paths


def test_manifest_failure_never_activates(tmp_path: Path) -> None:
    harness, anchor, context = _context(tmp_path)
    (harness.runtime_root / "execution_valve_env.json").unlink()

    result = _provision(context)

    assert result.accepted is False
    assert anchor.load() is None
    assert result.no_service_start_performed_by_coordinator is True


def test_manifest_tamper_before_reverification_rejects(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness, anchor, context = _context(tmp_path)
    module = (
        "modules.communication.moltbot_bridge.src."
        "reddog_signer_runtime_atomic_provisioning"
    )
    import importlib

    target = importlib.import_module(module)
    original = target.read_reddog_runtime_json_mapping

    def tamper_then_read(path, *, allowed_root):
        config = harness.runtime_root / "signer_service_config.json"
        config.write_text("{}", encoding="utf-8")
        return original(path, allowed_root=allowed_root)

    monkeypatch.setattr(
        target, "read_reddog_runtime_json_mapping", tamper_then_read
    )
    result = _provision(context)

    assert result.accepted is False
    assert anchor.load() is None
    assert result.inactive_artifacts_preserved is False


def test_anchor_must_be_outside_candidate_generation(
    tmp_path: Path,
) -> None:
    harness, _, context = _context(tmp_path)
    signing = GenerationSigner()
    outside = tmp_path / "alternate-high-water"
    witness = tmp_path / "alternate-witness"
    outside.mkdir()
    witness.mkdir()
    witness_store = SqliteMonotonicAuthorityStore(
        witness / "generation.sqlite3",
        allowed_root=witness,
        repo_root=harness.repo_root,
        store_id="alternate-generation-witness:v1",
        durability_receipt_id="sha256:" + "6" * 64,
    )
    store = AtomicSignerRuntimeGenerationHighWaterStore(
        outside / "high-water.json",
        allowed_root=outside,
        repo_root=harness.repo_root,
        store_id="alternate-high-water:v1",
        durability_receipt_id="sha256:" + "7" * 64,
        signer=signing,
        verifier=signing.verifier,
        generation_witness_store=witness_store,
        generation_witness_binding=generation_witness_binding(
            authenticator_id=signing.authenticator_id,
            runtime_root=harness.runtime_root,
            high_water_store_id="alternate-high-water:v1",
            high_water_durability_receipt_id="sha256:" + "7" * 64,
            witness_store_id=witness_store.store_id,
            witness_durability_receipt_id=(
                witness_store.durability_receipt_id
            ),
        ),
    )
    boundary = HighWaterBoundary(store)
    bad_anchor = DurableSignerRuntimeGenerationAnchor(
        harness.runtime_root / "anchor.json",
        allowed_root=harness.runtime_root,
        repo_root=harness.repo_root,
        anchor_id="reddog-signer:bad",
        signer=signing,
        verifier=signing.verifier,
        high_water_authority=boundary.capability,
        high_water_authority_boundary=boundary,
    )

    result = _provision(
        SignerRuntimeAtomicProvisioningContext(
            manifest_signing=context.manifest_signing,
            generation_anchor=bad_anchor,
        )
    )

    assert result.accepted is False
    assert "not_independent" in result.rejection_reasons[0]
    assert not harness.manifest_directory.exists()


def test_replayed_artifact_generation_does_not_advance_anchor(
    tmp_path: Path,
) -> None:
    harness, anchor, context = _context(tmp_path)
    first = _provision(context)
    assert first.accepted is True

    second = provision_signer_runtime_generation(
        nonce="provision-generation-2",
        ttl_seconds=120,
        context=SignerRuntimeAtomicProvisioningContext(
            manifest_signing=harness.fresh_context(),
            generation_anchor=anchor,
        ),
    )

    assert second.accepted is False
    assert any(
        token in second.rejection_reasons[0]
        for token in ("replay", "sealed")
    )
    assert anchor.load().generation == 1


def test_manifest_publication_is_create_only_under_concurrency(
    tmp_path: Path,
) -> None:
    harness, anchor, context = _context(tmp_path)
    first = _provision(context)
    assert first.accepted is True

    duplicate = _provision(
        SignerRuntimeAtomicProvisioningContext(
            manifest_signing=harness.fresh_context(),
            generation_anchor=anchor,
        )
    )

    assert duplicate.accepted is True
    assert duplicate.recovered_existing_activation is True
    assert len(tuple(harness.manifest_directory.glob("*.json"))) == 1
    assert anchor.load().generation == 1


def test_uncertain_return_retry_recovers_active_generation(
    tmp_path: Path,
) -> None:
    harness, anchor, context = _context(tmp_path)
    first = _provision(context)
    assert first.accepted is True

    retried = _provision(
        SignerRuntimeAtomicProvisioningContext(
            manifest_signing=harness.fresh_context(),
            generation_anchor=anchor,
        )
    )

    assert retried.accepted is True
    assert retried.recovered_existing_activation is True
    assert retried.activation_revision == first.activation_revision
    assert retried.manifest_id == first.manifest_id


def test_two_provisioners_converge_on_one_activation(
    tmp_path: Path,
) -> None:
    harness, anchor, context = _context(tmp_path)
    contexts = (
        context,
        SignerRuntimeAtomicProvisioningContext(
            manifest_signing=harness.fresh_context(),
            generation_anchor=anchor,
        ),
    )

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = tuple(pool.map(_provision, contexts))

    assert all(item.accepted for item in results)
    assert sum(item.recovered_existing_activation for item in results) == 1
    assert {item.activation_revision for item in results} == {
        anchor.load().revision
    }
    assert anchor.load().generation == 1


def test_two_process_provisioners_converge_on_one_activation(
    tmp_path: Path,
) -> None:
    harness = _build_harness(tmp_path)
    authority_root = tmp_path / "process-authority"
    anchor_root = tmp_path / "process-anchor"
    witness_root = tmp_path / "process-witness"
    authority_root.mkdir()
    anchor_root.mkdir()
    witness_root.mkdir()
    generation_signer = GenerationSigner()
    authority = harness.authority_boundary.require(harness.authority)
    values = {
        "repo_root": str(harness.repo_root),
        "runtime_root": str(harness.runtime_root),
        "authority_root": str(authority_root),
        "anchor_root": str(anchor_root),
        "witness_root": str(witness_root),
        "reddog_private": _private_key_bytes(harness.reddog_private_key),
        "generation_private": _private_key_bytes(
            generation_signer.private_key
        ),
        "principal_public": harness.principal_public_key,
        "reddog_public": harness.reddog_public_key,
        "identity": harness.identity,
        "work_authority": harness.work_authority,
        "work_state": harness.work_state,
        "queue_item_id": authority["queue_item_id"],
    }
    process_context = multiprocessing.get_context("spawn")
    output = process_context.Queue()
    processes = tuple(
        process_context.Process(
            target=_process_provision,
            args=(values, output),
        )
        for _ in range(2)
    )

    for process in processes:
        process.start()
    results = tuple(output.get(timeout=30) for _ in processes)
    for process in processes:
        process.join(timeout=30)

    assert all(process.exitcode == 0 for process in processes)
    assert all(result["accepted"] for result in results)
    assert {result["generation"] for result in results} == {1}
    assert len(
        tuple(harness.manifest_directory.glob("*.json"))
    ) == 1


def test_activation_cas_failure_preserves_inactive_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, anchor, context = _context(tmp_path)

    def reject_activate(*args, **kwargs):
        del args, kwargs
        raise RuntimeError("generation_anchor_revision_conflict")

    monkeypatch.setattr(anchor, "activate", reject_activate)
    result = _provision(context)

    assert result.accepted is False
    assert result.inactive_artifacts_preserved is True
    assert Path(str(result.manifest_path)).is_file()
    assert anchor.load() is None


def test_published_inactive_manifest_recovers_after_restart(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness, anchor, context = _context(tmp_path)
    original = anchor.activate

    def crash_after_publication(*args, **kwargs):
        del args, kwargs
        raise RuntimeError("simulated_process_crash")

    monkeypatch.setattr(anchor, "activate", crash_after_publication)
    first = _provision(context)
    assert first.accepted is False
    assert Path(str(first.manifest_path)).is_file()
    monkeypatch.setattr(anchor, "activate", original)

    retried = _provision(
        SignerRuntimeAtomicProvisioningContext(
            manifest_signing=harness.fresh_context(),
            generation_anchor=anchor,
        )
    )

    assert retried.accepted is True
    assert retried.recovered_existing_activation is True
    assert anchor.load().revision == retried.activation_revision


def test_stale_work_state_rejects_before_manifest_signing(
    tmp_path: Path,
) -> None:
    harness, anchor, context = _context(tmp_path)
    snapshot = harness.work_state_store.load()
    expected = str(snapshot.pop("revision"))
    snapshot["concurrent_refresh_marker"] = "advanced"
    harness.work_state_store.commit(
        snapshot,
        expected_revision=expected,
    )

    result = _provision(context)

    assert result.accepted is False
    assert any(
        token in result.rejection_reasons[0]
        for token in ("stale", "binding")
    )
    assert anchor.load() is None
    assert not harness.manifest_directory.exists()


def test_concurrent_work_state_refresh_cannot_overtake_activation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness, anchor, context = _context(tmp_path)
    original = anchor.activate
    started = Event()
    completed = Event()
    failures = []
    worker = None

    def refresh() -> None:
        try:
            started.set()
            snapshot = harness.work_state_store.load()
            expected = str(snapshot.pop("revision"))
            snapshot["concurrent_refresh_marker"] = "after-activation"
            harness.work_state_store.commit(
                snapshot,
                expected_revision=expected,
            )
        except Exception as exc:
            failures.append(exc)
        finally:
            completed.set()

    def activate_then_release(*args, **kwargs):
        nonlocal worker
        worker = Thread(target=refresh)
        worker.start()
        assert started.wait(timeout=2)
        assert not completed.wait(timeout=0.2)
        return original(*args, **kwargs)

    monkeypatch.setattr(anchor, "activate", activate_then_release)
    result = _provision(context)
    assert worker is not None
    worker.join(timeout=5)

    assert result.accepted is True
    assert completed.is_set()
    assert failures == []
    assert harness.work_state_store.load()[
        "concurrent_refresh_marker"
    ] == "after-activation"


def test_authority_expiry_after_durable_activation_reports_commit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness, anchor, context = _context(tmp_path)
    clock = [NOW]
    original = anchor.activate
    import modules.communication.moltbot_bridge.src.reddog_runtime_artifact_manifest_authority as authority_module

    monkeypatch.setattr(
        authority_module,
        "_locked_now",
        lambda _settings, minimum: max(minimum, clock[0]),
    )

    def activate_then_expire(*args, **kwargs):
        activation = original(*args, **kwargs)
        clock[0] = NOW + 1_000
        return activation

    monkeypatch.setattr(anchor, "activate", activate_then_expire)
    result = _provision(context)

    assert result.accepted is True
    assert result.recovered_existing_activation is True
    assert anchor.load().revision == result.activation_revision
    assert harness.work_state_store.load()["revision"]


def test_expired_manifest_is_not_recovered_with_historical_time(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness, anchor, context = _context(tmp_path)
    first = _provision(context)
    assert first.accepted is True

    import modules.communication.moltbot_bridge.src.reddog_signer_runtime_atomic_provisioning as target

    monkeypatch.setattr(target, "_trusted_now", lambda: NOW + 121)
    retried = _provision(
        SignerRuntimeAtomicProvisioningContext(
            manifest_signing=harness.fresh_context(),
            generation_anchor=anchor,
        )
    )

    assert retried.accepted is False
    assert retried.recovered_existing_activation is False
    assert anchor.load().revision == first.activation_revision


def test_sealed_generation_blocks_governed_artifact_writers(
    tmp_path: Path,
) -> None:
    harness, anchor, context = _context(tmp_path)
    result = _provision(context)

    assert result.accepted is True
    with pytest.raises(RuntimeError, match="generation_sealed"):
        with reddog_runtime_artifact_generation_lock(
            harness.runtime_root,
            repo_root=harness.repo_root,
        ):
            raise AssertionError("sealed writer entered")
    socket_path = harness.runtime_root / "signer.sock.placeholder"
    socket_path.write_text("lifecycle-owned", encoding="utf-8")
    assert socket_path.is_file()
    assert anchor.load() is not None


def test_preseeded_self_hashed_manifest_cannot_recover(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness, anchor, context = _context(tmp_path)
    harness.manifest_directory.mkdir()
    (harness.manifest_directory / ("a" * 64 + ".json")).write_text(
        json.dumps({"nonce": "provision-generation-1"}),
        encoding="utf-8",
    )
    module = (
        "modules.communication.moltbot_bridge.src."
        "reddog_signer_runtime_atomic_provisioning"
    )
    import importlib

    target = importlib.import_module(module)
    monkeypatch.setattr(
        target,
        "produce_signed_runtime_artifact_manifest",
        lambda **kwargs: SignedRuntimeArtifactManifestResult(
            accepted=False,
            output_path=None,
            manifest_id=None,
            rejection_reasons=("simulated_signing_failure",),
        ),
    )

    result = _provision(context)

    assert result.accepted is False
    assert anchor.load() is None


def test_result_contains_no_execution_or_service_authority(
    tmp_path: Path,
) -> None:
    _, _, context = _context(tmp_path)

    result = _provision(context).to_dict()

    assert result["accepted"] is True
    assert result["no_service_start_performed_by_coordinator"] is True
    assert result["no_work_execution_performed_by_coordinator"] is True
    assert result["no_repo_mutation_performed_by_coordinator"] is True
    assert "token" not in json.dumps(result).lower()


def test_fake_anchor_is_rejected_before_manifest_publication(
    tmp_path: Path,
) -> None:
    harness, _, context = _context(tmp_path)

    class FakeAnchor:
        path = tmp_path / "fake-anchor.json"

    fake_context = SignerRuntimeAtomicProvisioningContext(
        manifest_signing=context.manifest_signing,
        generation_anchor=FakeAnchor(),  # type: ignore[arg-type]
    )
    result = _provision(fake_context)

    assert result.accepted is False
    assert "anchor_invalid" in result.rejection_reasons[0]
    assert not harness.manifest_directory.exists()
