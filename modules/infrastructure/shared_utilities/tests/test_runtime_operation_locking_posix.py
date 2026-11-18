"""POSIX lock-root confinement falsifiers for shared runtime locks."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from modules.infrastructure.shared_utilities import runtime_operation_locking
from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    runtime_operation_lock,
)


pytestmark = pytest.mark.skipif(os.name == "nt", reason="POSIX lock-root contract")


def _redirect_temp(monkeypatch: pytest.MonkeyPatch, root: Path) -> None:
    monkeypatch.setattr(
        runtime_operation_locking.tempfile, "gettempdir", lambda: str(root)
    )


def test_posix_lock_rejects_symlinked_lock_root(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    target = tmp_path / "target"
    target.mkdir(mode=0o700)
    (tmp_path / "foundups-runtime-locks").symlink_to(
        target, target_is_directory=True
    )
    _redirect_temp(monkeypatch, tmp_path)

    with pytest.raises(PermissionError, match="lock_root_not_private"):
        with runtime_operation_lock("hostile-root"):
            pass


def test_posix_lock_rejects_broad_lock_root(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    lock_root = tmp_path / "foundups-runtime-locks"
    lock_root.mkdir(mode=0o700)
    lock_root.chmod(0o755)
    _redirect_temp(monkeypatch, tmp_path)

    with pytest.raises(PermissionError, match="lock_root_not_private"):
        with runtime_operation_lock("broad-root"):
            pass


def test_posix_lock_accepts_private_owned_root(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    _redirect_temp(monkeypatch, tmp_path)
    with runtime_operation_lock("private-root"):
        assert (tmp_path / "foundups-runtime-locks").is_dir()
