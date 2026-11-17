"""Hold canonical runtime bytes stable during generation activation."""

from __future__ import annotations

import os
import stat
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Sequence

from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    validate_runtime_artifact_path,
)


@contextmanager
def runtime_artifact_activation_lease(
    paths: Sequence[Path | str],
    *,
    repo_root: Path | str,
    allowed_root: Path | str,
) -> Iterator[None]:
    """Deny ordinary writes while signed bytes become the active generation."""

    targets = _validated_targets(
        paths, repo_root=repo_root, allowed_root=allowed_root
    )
    if os.name == "nt":
        with _windows_activation_lease(targets):
            yield
        return
    if sys.platform.startswith("linux"):
        with _linux_immutable_activation_lease(targets):
            yield
        return
    raise RuntimeError(
        "runtime_artifact_activation_lease_external_owner_required"
    )


def _validated_targets(
    paths: Sequence[Path | str],
    *,
    repo_root: Path | str,
    allowed_root: Path | str,
) -> tuple[Path, ...]:
    targets = tuple(
        validate_runtime_artifact_path(
            path,
            repo_root=repo_root,
            allowed_root=allowed_root,
        )
        for path in paths
    )
    if not targets or len(set(targets)) != len(targets):
        raise ValueError("runtime_artifact_activation_lease_targets_invalid")
    for target in targets:
        metadata = target.lstat()
        if target.is_symlink() or not target.is_file() or metadata.st_nlink != 1:
            raise ValueError("runtime_artifact_activation_lease_target_invalid")
    return targets


@contextmanager
def _windows_activation_lease(paths: tuple[Path, ...]) -> Iterator[None]:
    from modules.communication.moltbot_bridge.src.reddog_authority_runtime_store_windows import (
        close_windows_handle,
        open_windows_file_without_write_delete_share,
    )

    handles: list[int] = []
    try:
        for path in paths:
            handles.append(open_windows_file_without_write_delete_share(path))
        yield
    finally:
        for handle in reversed(handles):
            close_windows_handle(handle)


def _linux_unprivileged_activation_process() -> None:
    """An installer may set immutable flags; the activation process cannot."""
    status = {}
    for line in Path("/proc/self/status").read_text(encoding="ascii").splitlines():
        key, separator, value = line.partition(":")
        if separator:
            status[key] = value.strip()
    if (os.geteuid() == 0 or status.get("NoNewPrivs") != "1"
            or any(int(status.get(name, "1"), 16) != 0 for name in
                   ("CapInh", "CapPrm", "CapEff", "CapAmb"))):
        raise RuntimeError("runtime_artifact_activation_lease_external_owner_required")


def _require_linux_immutable_file(path: Path, descriptor: int) -> None:
    import array
    import fcntl

    from .reddog_signer_system_service_manifest_selection_loader import _require_secure_ancestry

    _require_secure_ancestry(path.parent)
    metadata = os.fstat(descriptor)
    current = path.lstat()
    if (not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != 0
            or metadata.st_mode & 0o022 or metadata.st_nlink != 1
            or (metadata.st_dev, metadata.st_ino) != (current.st_dev, current.st_ino)):
        raise RuntimeError("runtime_artifact_activation_lease_external_owner_required")
    # Linux FS_IOC_GETFLAGS encodes sizeof(long); use the native ABI width.
    flags = array.array("L", [0])
    request = 0x80006601 | (flags.itemsize << 16)
    fcntl.ioctl(descriptor, request, flags, True)
    if flags[0] & 0x10 == 0:  # FS_IMMUTABLE_FL: also rejects pre-opened writers.
        raise RuntimeError("runtime_artifact_activation_lease_external_owner_required")


@contextmanager
def _linux_immutable_activation_lease(paths: tuple[Path, ...]) -> Iterator[None]:
    """Consume root-installed immutable files, never set flags or change owners.

    Root administration and privileged mount changes are outside this boundary.
    Root-protected ancestry prevents ordinary directory replacement; immutable
    inodes reject writes through existing descriptors as well as unlink/rename.
    Unsupported filesystems and unqualified processes fail closed.
    """
    from .reddog_signer_system_service_manifest_selection_loader import _require_secure_ancestry

    _linux_unprivileged_activation_process()
    handles: list[tuple[Path, int]] = []
    try:
        for path in paths:
            _require_secure_ancestry(path.parent)
            descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK)
            handles.append((path, descriptor))
            _require_linux_immutable_file(path, descriptor)
        yield
        _linux_unprivileged_activation_process()
        for path, descriptor in handles:
            _require_linux_immutable_file(path, descriptor)
    finally:
        for _, descriptor in reversed(handles):
            os.close(descriptor)

__all__ = ["runtime_artifact_activation_lease"]
