"""Privileged Linux integration tests for signer owner-config admission."""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.src import (
    reddog_signer_system_service_manifest_selection_loader as loader_module,
)
from modules.communication.moltbot_bridge.src.reddog_runtime_artifact_manifest_contract import (
    RuntimeArtifactManifestError,
)
from modules.communication.moltbot_bridge.tests.test_reddog_signer_socket_service_runtime_cli import (
    CapturingBoundedService,
    CapturingResolverFactory,
    FakeResolver,
    _audit_secret,
    _private_key_secret,
)
from modules.communication.moltbot_bridge.tests.test_reddog_signer_system_service_manifest_selection_loader import (
    _prepare_real_cli_owner,
    _run_real_cli,
)


IS_ROOT_LINUX = bool(
    sys.platform.startswith("linux")
    and hasattr(os, "geteuid")
    and os.geteuid() == 0
)
pytestmark = pytest.mark.skipif(
    not IS_ROOT_LINUX,
    reason="requires root-owned Linux signer-service fixture",
)


def test_root_owned_owner_config_runs_cli_to_bootstrap() -> None:
    with tempfile.TemporaryDirectory(dir="/root") as raw:
        prepared = _prepare_real_cli_owner(Path(raw), None)
        resolver = FakeResolver(
            {
                "op://prod-vault/reddog-signing/private": (
                    _private_key_secret(
                        prepared["harness"].reddog_private_key
                    )
                ),
                "op://prod-vault/reddog-audit/mac": _audit_secret(),
            }
        )
        factory = CapturingResolverFactory(resolver)
        service = CapturingBoundedService()
        emitted: list[str] = []

        result = _run_real_cli(prepared, factory, service, emitted)

        assert result == 0, json.loads(emitted[0])
        assert len(factory.calls) == 1
        assert len(service.calls) == 1


def test_wrong_owner_uid_rejects() -> None:
    with tempfile.TemporaryDirectory(dir="/root") as raw:
        root, target = _owner_file(Path(raw), b"owner")
        os.chown(target, 1, 1)

        with pytest.raises(
            RuntimeArtifactManifestError,
            match="signer_owner_config_permissions_invalid",
        ):
            loader_module._read_root_owned_bytes(target, root)


@pytest.mark.parametrize(("root_mode", "file_mode"), [(0o722, 0o400), (0o700, 0o422)])
def test_writable_owner_directory_or_file_rejects(
    root_mode: int, file_mode: int
) -> None:
    with tempfile.TemporaryDirectory(dir="/root") as raw:
        root, target = _owner_file(Path(raw), b"owner")
        root.chmod(root_mode)
        target.chmod(file_mode)

        with pytest.raises(
            RuntimeArtifactManifestError,
            match="signer_owner_config_permissions_invalid",
        ):
            loader_module._read_root_owned_bytes(target, root)


def test_symlink_owner_config_rejects() -> None:
    with tempfile.TemporaryDirectory(dir="/root") as raw:
        root = Path(raw) / "owner"
        root.mkdir(mode=0o700)
        actual = root / "actual.json"
        actual.write_bytes(b"owner")
        actual.chmod(0o400)
        target = root / "owner.json"
        target.symlink_to(actual)

        with pytest.raises(
            RuntimeArtifactManifestError,
            match="signer_owner_config_descriptor_invalid",
        ):
            loader_module._read_root_owned_bytes(target, root)


def test_directory_replacement_does_not_switch_opened_owner_file(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with tempfile.TemporaryDirectory(dir="/root") as raw:
        base = Path(raw)
        root, target = _owner_file(base, b"legitimate")
        stale = base / "owner-opened"
        real_open = os.open

        def replacing_open(path, flags, mode=0o777, *, dir_fd=None):
            descriptor = real_open(path, flags, mode, dir_fd=dir_fd)
            if dir_fd is None and Path(path) == root:
                root.rename(stale)
                root.mkdir(mode=0o700)
                forged = root / target.name
                forged.write_bytes(b"forged")
                forged.chmod(0o400)
            return descriptor

        monkeypatch.setattr(loader_module.os, "open", replacing_open)

        assert loader_module._read_root_owned_bytes(
            target, root
        ) == b"legitimate"


def _owner_file(base: Path, content: bytes) -> tuple[Path, Path]:
    root = base / "owner"
    root.mkdir(mode=0o700)
    target = root / "owner.json"
    target.write_bytes(content)
    target.chmod(0o400)
    return root, target
