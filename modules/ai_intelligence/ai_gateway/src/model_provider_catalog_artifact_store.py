"""Atomic outside-repository storage for provider catalog runtime artifacts."""

from __future__ import annotations

import os
import stat
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, Callable

from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    runtime_operation_lock,
    validate_runtime_artifact_path,
    validate_runtime_root_path,
)


def _write_all(stream: BinaryIO, payload: bytes) -> None:
    written = stream.write(payload)
    if written != len(payload):
        raise OSError("runtime_artifact_temp_write_incomplete")


@dataclass(frozen=True)
class AtomicArtifactOps:
    """Injectable low-level seams used by offline durability tests."""

    writer: Callable[[BinaryIO, bytes], None] = _write_all
    fsync: Callable[[int], None] = os.fsync
    replacer: Callable[[Path, Path], None] = os.replace


@dataclass(frozen=True)
class ProviderCatalogArtifactStore:
    repo_root: Path
    runtime_root: Path
    ops: AtomicArtifactOps = AtomicArtifactOps()

    @classmethod
    def create(
        cls,
        *,
        repo_root: Path | str,
        runtime_root: Path | str,
        ops: AtomicArtifactOps | None = None,
    ) -> "ProviderCatalogArtifactStore":
        root = validate_runtime_root_path(runtime_root, repo_root=repo_root)
        return cls(Path(repo_root).resolve(), root, ops or AtomicArtifactOps())

    def replace_text(self, path: Path | str, text: str) -> Path:
        """Atomically replace one confined regular artifact with exact UTF-8."""

        if type(text) is not str:
            raise ValueError("runtime_artifact_text_invalid")
        target = self._target(path, create_parent=True)
        payload = text.encode("utf-8", errors="strict")
        with runtime_operation_lock(target):
            target = self._target(target)
            mode = self._existing_mode(target)
            temporary: Path | None = None
            try:
                descriptor, raw_temp = tempfile.mkstemp(
                    prefix=f".{target.name}.", suffix=".tmp", dir=target.parent
                )
                temporary = Path(raw_temp)
                self._write_temp(descriptor, temporary, payload, mode)
                target = self._target(target)
                temporary = self._validated_temp(temporary, target.parent)
                self.ops.replacer(temporary, target)
                temporary = None
                _fsync_parent(target.parent, self.ops.fsync)
            except Exception:
                _remove_temp(temporary)
                raise
        return target

    def _target(self, path: Path | str, *, create_parent: bool = False) -> Path:
        target = validate_runtime_artifact_path(
            path, repo_root=self.repo_root, allowed_root=self.runtime_root
        )
        if create_parent:
            target.parent.mkdir(parents=True, exist_ok=True)
            target = validate_runtime_artifact_path(
                target, repo_root=self.repo_root, allowed_root=self.runtime_root
            )
        return target

    def _write_temp(
        self, descriptor: int, temporary: Path, payload: bytes, mode: int | None
    ) -> None:
        try:
            opened, named = os.fstat(descriptor), os.lstat(temporary)
            if (
                not stat.S_ISREG(opened.st_mode)
                or (opened.st_dev, opened.st_ino) != (named.st_dev, named.st_ino)
            ):
                raise ValueError("runtime_artifact_temp_descriptor_mismatch")
            if mode is not None and hasattr(os, "fchmod"):
                os.fchmod(descriptor, mode)
            with os.fdopen(descriptor, "wb", closefd=True) as stream:
                descriptor = -1
                self.ops.writer(stream, payload)
                stream.flush()
                if os.fstat(stream.fileno()).st_size != len(payload):
                    raise OSError("runtime_artifact_temp_size_mismatch")
                self.ops.fsync(stream.fileno())
        finally:
            if descriptor >= 0:
                os.close(descriptor)
        self._validated_temp(temporary, temporary.parent)

    def _validated_temp(self, temporary: Path, parent: Path) -> Path:
        value = validate_runtime_artifact_path(
            temporary, repo_root=self.repo_root, allowed_root=self.runtime_root
        )
        metadata = os.lstat(value)
        if value.parent != parent or not stat.S_ISREG(metadata.st_mode):
            raise ValueError("runtime_artifact_temp_invalid")
        return value

    @staticmethod
    def _existing_mode(target: Path) -> int | None:
        try:
            metadata = os.lstat(target)
        except FileNotFoundError:
            return None
        if not stat.S_ISREG(metadata.st_mode):
            raise ValueError("runtime_artifact_target_not_regular")
        return stat.S_IMODE(metadata.st_mode)


def _remove_temp(path: Path | None) -> None:
    if path is None:
        return
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass


def _fsync_parent(parent: Path, fsync: Callable[[int], None]) -> None:
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    try:
        descriptor = os.open(parent, flags)
    except (OSError, NotImplementedError):
        return
    try:
        fsync(descriptor)
    except (OSError, NotImplementedError):
        pass
    finally:
        os.close(descriptor)


__all__ = ["AtomicArtifactOps", "ProviderCatalogArtifactStore"]
