"""Crash-safe non-replacing creation for immutable gateway records."""

from __future__ import annotations

import hashlib
import os
import stat
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .model_autoresearch_configured_gateway_durability import _fsync_store_lineage
from .model_autoresearch_configured_gateway_posix_recovery import (
    repair_interrupted_posix_commit,
)
from .model_provider_catalog_atomic_io import (
    _open_windows_publication_descriptor,
    _read_descriptor,
    _rename_windows_descriptor,
)


@dataclass(frozen=True)
class _OwnedTemporary:
    path: Path
    device: int
    inode: int
    size: int
    digest: str


def atomic_create_bytes(path: Path, payload: bytes, *, root: Path) -> bool:
    """Create one complete immutable file or report an existing destination.

    The temporary is same-directory and fully flushed before a non-replacing
    commit. A process crash may orphan a hidden temporary, but cannot expose a
    partial destination record. Foreign/ambiguous temporaries are preserved.
    """

    path.parent.mkdir(parents=True, exist_ok=True)
    repair_interrupted_posix_commit(path, payload)
    descriptor, raw = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".pending", dir=path.parent
    )
    owned: _OwnedTemporary | None = None
    try:
        owned = _write_temporary(descriptor, Path(raw), payload)
        created = _commit_nonreplacing(owned, path)
        links = 2 if created and os.name != "nt" else 1
        _remove_owned_temporary(owned, allowed_links=links)
        _fsync_store_lineage(path.parent, root)
        return created
    except BaseException:
        if owned is None:
            try:
                os.close(descriptor)
            except OSError:
                pass
        _remove_owned_temporary(owned, allowed_links=1)
        raise


def _write_temporary(descriptor: int, path: Path, payload: bytes) -> _OwnedTemporary:
    try:
        opened, named = os.fstat(descriptor), os.lstat(path)
        if not _same_regular(opened, named) or opened.st_nlink != 1:
            raise OSError("configured_gateway_temporary_identity_invalid")
        with os.fdopen(descriptor, "w+b", closefd=True) as stream:
            descriptor = -1
            written = stream.write(payload)
            if written != len(payload):
                raise OSError("configured_gateway_temporary_write_incomplete")
            stream.flush()
            os.fsync(stream.fileno())
            stream.seek(0)
            if stream.read(len(payload) + 1) != payload:
                raise OSError("configured_gateway_temporary_content_invalid")
            metadata = os.fstat(stream.fileno())
        return _OwnedTemporary(
            path,
            metadata.st_dev,
            metadata.st_ino,
            len(payload),
            hashlib.sha256(payload).hexdigest(),
        )
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _commit_nonreplacing(owned: _OwnedTemporary, target: Path) -> bool:
    _verify_owned_path(owned)
    if os.name == "nt":
        descriptor = _open_windows_publication_descriptor(owned.path)
        try:
            _verify_owned_descriptor(descriptor, owned)
            try:
                _rename_windows_descriptor(descriptor, target, replace_existing=False)
            except FileExistsError:
                return False
            except OSError as error:
                if getattr(error, "winerror", None) in {80, 183}:
                    return False
                raise
            _verify_owned_descriptor(descriptor, owned)
        finally:
            os.close(descriptor)
        return True
    try:
        os.link(owned.path, target, follow_symlinks=False)
    except FileExistsError:
        return False
    _verify_owned_path_at(target, owned, allowed_links=2)
    return True


def _verify_owned_path(owned: _OwnedTemporary) -> None:
    _verify_owned_path_at(owned.path, owned, allowed_links=1)


def _verify_owned_path_at(
    path: Path, owned: _OwnedTemporary, *, allowed_links: int
) -> None:
    metadata = os.lstat(path)
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_nlink != allowed_links
        or (metadata.st_dev, metadata.st_ino) != (owned.device, owned.inode)
        or metadata.st_size != owned.size
    ):
        raise OSError("configured_gateway_temporary_identity_invalid")


def _verify_owned_descriptor(descriptor: int, owned: _OwnedTemporary) -> None:
    metadata = os.fstat(descriptor)
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_nlink != 1
        or (metadata.st_dev, metadata.st_ino) != (owned.device, owned.inode)
        or metadata.st_size != owned.size
    ):
        raise OSError("configured_gateway_temporary_identity_invalid")
    content = _read_descriptor(descriptor, owned.size + 1)
    if hashlib.sha256(content).hexdigest() != owned.digest:
        raise OSError("configured_gateway_temporary_content_invalid")


def _remove_owned_temporary(
    owned: _OwnedTemporary | None, *, allowed_links: int
) -> None:
    if owned is None:
        return
    try:
        _verify_owned_path_at(owned.path, owned, allowed_links=allowed_links)
    except (FileNotFoundError, OSError):
        return
    owned.path.unlink()


def _same_regular(first: os.stat_result, second: os.stat_result) -> bool:
    return (
        stat.S_ISREG(first.st_mode)
        and stat.S_ISREG(second.st_mode)
        and first.st_ino > 0
        and (first.st_dev, first.st_ino) == (second.st_dev, second.st_ino)
    )


__all__ = ["atomic_create_bytes"]
