"""Crash-recovery evidence tests for atomic signer provisioning."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.src.reddog_signer_runtime_atomic_provisioning import (
    SignerRuntimeAtomicProvisioningContext,
)
from modules.communication.moltbot_bridge.tests.test_reddog_signed_runtime_artifact_manifest import (
    NOW,
)
from modules.communication.moltbot_bridge.tests.test_reddog_signer_runtime_atomic_provisioning import (
    _context,
    _provision,
    _test_only_activation_lease,
)


@pytest.fixture(autouse=True)
def _fixed_clock(monkeypatch: pytest.MonkeyPatch) -> None:
    import modules.communication.moltbot_bridge.src.reddog_signer_runtime_atomic_provisioning as target

    monkeypatch.setattr(target, "_trusted_now", lambda: NOW)


def test_tampered_manifest_path_is_not_reported_as_preserved(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness, anchor, context = _context(tmp_path)
    import modules.communication.moltbot_bridge.src.reddog_signer_runtime_atomic_provisioning as target

    monkeypatch.setattr(
        target,
        "runtime_artifact_activation_lease",
        _test_only_activation_lease,
    )

    def tamper_and_reject(*_args, **_kwargs):
        manifest = next(harness.manifest_directory.glob("*.json"))
        manifest.write_text("{}", encoding="utf-8")
        raise RuntimeError("generation_anchor_revision_conflict")

    monkeypatch.setattr(anchor, "activate", tamper_and_reject)
    result = _provision(context)

    assert result.accepted is False
    assert Path(str(result.manifest_path)).is_file()
    assert result.inactive_artifacts_preserved is False
    assert anchor.load() is None


def test_tampered_manifest_signature_is_not_reported_as_preserved(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness, anchor, context = _context(tmp_path)
    import modules.communication.moltbot_bridge.src.reddog_signer_runtime_atomic_provisioning as target

    monkeypatch.setattr(
        target,
        "runtime_artifact_activation_lease",
        _test_only_activation_lease,
    )

    def tamper_and_reject(*_args, **_kwargs):
        path = next(harness.manifest_directory.glob("*.json"))
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["signature"] = "ed25519:" + ("A" * 86)
        path.write_text(
            json.dumps(payload, sort_keys=True, separators=(",", ":")),
            encoding="utf-8",
        )
        raise RuntimeError("generation_anchor_revision_conflict")

    monkeypatch.setattr(anchor, "activate", tamper_and_reject)
    result = _provision(context)

    assert result.accepted is False
    assert Path(str(result.manifest_path)).is_file()
    assert result.inactive_artifacts_preserved is False
    assert anchor.load() is None


def test_tampered_artifact_bytes_are_not_reported_as_preserved(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness, anchor, context = _context(tmp_path)
    import modules.communication.moltbot_bridge.src.reddog_signer_runtime_atomic_provisioning as target

    monkeypatch.setattr(
        target,
        "runtime_artifact_activation_lease",
        _test_only_activation_lease,
    )

    def tamper_and_reject(*_args, **_kwargs):
        target_path = harness.runtime_root / "signer_service_config.json"
        target_path.write_text("{}", encoding="utf-8")
        raise RuntimeError("generation_anchor_revision_conflict")

    monkeypatch.setattr(anchor, "activate", tamper_and_reject)
    result = _provision(context)

    assert result.accepted is False
    assert result.inactive_artifacts_preserved is False
    assert anchor.load() is None


def test_committed_witness_interruption_rolls_forward_before_return(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, anchor, context = _context(tmp_path)
    store = anchor._high_water_store
    original = store.commit_prepared
    interrupted = [False]

    def fail_once(anchor_id: str, transaction_id: str) -> None:
        if not interrupted[0]:
            interrupted[0] = True
            raise RuntimeError("high_water_interrupted")
        original(anchor_id, transaction_id)

    monkeypatch.setattr(store, "commit_prepared", fail_once)
    result = _provision(context)

    assert result.accepted is True
    assert result.recovered_existing_activation is True
    assert store.pending(anchor._anchor_id) is None
    assert anchor.load().revision == result.activation_revision


def test_expired_committed_witness_recovers_after_process_gap(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness, anchor, context = _context(tmp_path)
    store = anchor._high_water_store
    original = store.commit_prepared

    monkeypatch.setattr(
        store,
        "commit_prepared",
        lambda _anchor_id, _transaction_id: (_ for _ in ()).throw(
            RuntimeError("high_water_interrupted")
        ),
    )
    import modules.communication.moltbot_bridge.src.reddog_signer_runtime_atomic_provisioning as target

    monkeypatch.setattr(target, "_recover_new_commit", lambda *_a, **_k: None)
    _provision(context)
    assert store.pending(anchor._anchor_id) is not None
    monkeypatch.setattr(store, "commit_prepared", original)
    monkeypatch.undo()
    monkeypatch.setattr(target, "_trusted_now", lambda: NOW + 121)
    recovered = _provision(
        SignerRuntimeAtomicProvisioningContext(
            manifest_signing=harness.fresh_context(),
            generation_anchor=anchor,
        )
    )

    assert recovered.accepted is True
    assert recovered.recovered_existing_activation is True
    assert store.pending(anchor._anchor_id) is None
    assert anchor.load().revision == recovered.activation_revision
