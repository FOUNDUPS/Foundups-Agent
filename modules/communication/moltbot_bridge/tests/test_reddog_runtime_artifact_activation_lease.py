"""Activation-window race tests for signer runtime artifact generations."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.tests.test_reddog_signer_runtime_atomic_provisioning import (
    _context,
    _provision,
)
from modules.communication.moltbot_bridge.tests.test_reddog_signed_runtime_artifact_manifest import (
    NOW,
)


@pytest.fixture(autouse=True)
def _fixed_clock(monkeypatch: pytest.MonkeyPatch) -> None:
    import modules.communication.moltbot_bridge.src.reddog_signer_runtime_atomic_provisioning as target

    monkeypatch.setattr(target, "_trusted_now", lambda: NOW)


def test_direct_write_during_anchor_activation_is_denied(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness, anchor, context = _context(tmp_path)
    original = anchor.activate

    def mutate_then_activate(*args, **kwargs):
        config = harness.runtime_root / "signer_service_config.json"
        config.write_text("{}", encoding="utf-8")
        return original(*args, **kwargs)

    monkeypatch.setattr(anchor, "activate", mutate_then_activate)
    result = _provision(context)

    assert result.accepted is False
    assert anchor.load() is None
    assert result.inactive_artifacts_preserved is True


def test_preopened_writer_cannot_leave_failed_generation_active(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness, anchor, context = _context(tmp_path)
    config = harness.runtime_root / "signer_service_config.json"
    descriptor = os.open(config, os.O_WRONLY)
    original = anchor.activate

    def mutate_then_activate(*args, **kwargs):
        os.lseek(descriptor, 0, os.SEEK_SET)
        os.write(descriptor, b"{}")
        os.ftruncate(descriptor, 2)
        os.fsync(descriptor)
        return original(*args, **kwargs)

    monkeypatch.setattr(anchor, "activate", mutate_then_activate)
    try:
        result = _provision(context)
    finally:
        os.close(descriptor)

    assert result.accepted is False
    assert anchor.load() is None
    assert result.inactive_artifacts_preserved is True


def test_path_replacement_cannot_leave_failed_generation_active(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness, anchor, context = _context(tmp_path)
    config = harness.runtime_root / "signer_service_config.json"
    displaced = harness.runtime_root / "signer_service_config.displaced"
    original = anchor.activate

    def replace_then_activate(*args, **kwargs):
        config.replace(displaced)
        config.write_text("{}", encoding="utf-8")
        return original(*args, **kwargs)

    monkeypatch.setattr(anchor, "activate", replace_then_activate)
    result = _provision(context)

    assert result.accepted is False
    assert anchor.load() is None
    assert result.inactive_artifacts_preserved is True
