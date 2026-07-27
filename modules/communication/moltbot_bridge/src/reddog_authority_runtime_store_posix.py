"""Linux descriptor operations for confined authority runtime replacement.

The durable replacement path requires ``O_TMPFILE`` and fails closed when the
host filesystem cannot provide an unnamed inode. No pathname temp fallback is
used for authority state.
"""

from __future__ import annotations

import ctypes
import hashlib
import json
import os
import secrets
import stat
from pathlib import Path


_AT_EMPTY_PATH = 0x1000


def posix_atomic_replace(
    parent_fd: int,
    parent_path: Path,
    target_name: str,
    payload: bytes,
    *,
    check_revision: bool,
    expected_revision: object,
) -> None:
    """Replace one target from an unnamed inode with descriptor rollback."""

    _recover_interrupted_files(
        parent_fd,
        target_name,
        restore_missing=False,
        expected_revision=None,
    )
    old_fd, old_mode = _open_target_witness(
        parent_fd,
        target_name,
        check_revision=check_revision,
        expected_revision=expected_revision,
    )
    descriptor = _open_unnamed_temp(parent_fd)
    temp_name = f".{target_name}.{secrets.token_hex(16)}.tmp"
    backup_name = f".{target_name}.{secrets.token_hex(16)}.bak"
    linked = False
    backup_created = False
    renamed = False
    verified = False
    try:
        _write_descriptor(descriptor, payload)
        _require_unnamed_private_regular(os.fstat(descriptor))
        os.fchmod(descriptor, 0)
        _require_parent_identity(parent_fd, parent_path)
        _link_descriptor(descriptor, parent_fd, temp_name)
        linked = True
        expected_temp = os.fstat(descriptor)
        _require_entry_identity(parent_fd, temp_name, expected_temp, mode=0)
        _require_target_witness(
            parent_fd,
            target_name,
            old_fd,
            check_revision=check_revision,
            expected_revision=expected_revision,
        )
        if old_fd is not None:
            _link_descriptor(old_fd, parent_fd, backup_name)
            backup_created = True
            os.fchmod(old_fd, 0)
            _require_backup_identity(
                parent_fd,
                target_name,
                backup_name,
                old_fd,
                check_revision=check_revision,
                expected_revision=expected_revision,
            )
        _require_parent_identity(parent_fd, parent_path)
        _replace_entry(
            parent_fd,
            temp_name,
            target_name,
            old_fd=old_fd,
            backup_name=backup_name if backup_created else None,
            check_revision=check_revision,
            expected_revision=expected_revision,
        )
        linked = False
        renamed = True
        _require_entry_identity(parent_fd, target_name, expected_temp, mode=0)
        _require_parent_identity(parent_fd, parent_path)
        os.fsync(parent_fd)
        _require_parent_identity(parent_fd, parent_path)
        os.fchmod(descriptor, 0o600)
        os.fsync(descriptor)
        _require_entry_identity(parent_fd, target_name, os.fstat(descriptor), mode=0o600)
        _require_parent_identity(parent_fd, parent_path)
        verified = True
    finally:
        if renamed and not verified:
            _restore_previous(
                parent_fd,
                target_name,
                old_fd=old_fd,
                old_mode=old_mode,
                backup_name=backup_name,
                backup_created=backup_created,
            )
        else:
            if linked:
                _unlink(parent_fd, temp_name)
            if backup_created:
                if old_fd is not None:
                    os.fchmod(old_fd, old_mode)
                _unlink(parent_fd, backup_name)
        os.close(descriptor)
        if old_fd is not None:
            os.close(old_fd)


def _open_unnamed_temp(parent_fd: int) -> int:
    flags = os.O_RDWR | getattr(os, "O_TMPFILE", 0)
    if not getattr(os, "O_TMPFILE", 0):
        raise OSError("authority_runtime_store_unnamed_temp_unavailable")
    try:
        return os.open(".", flags, 0o600, dir_fd=parent_fd)
    except OSError as exc:
        raise OSError("authority_runtime_store_unnamed_temp_unavailable") from exc


def _open_target_witness(
    parent_fd: int,
    target_name: str,
    *,
    check_revision: bool,
    expected_revision: object,
) -> tuple[int | None, int]:
    try:
        descriptor = os.open(
            target_name,
            os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0),
            dir_fd=parent_fd,
        )
    except FileNotFoundError:
        if check_revision and expected_revision is not None:
            raise RuntimeError("revision_conflict")
        return None, 0o600
    try:
        metadata = os.fstat(descriptor)
        _require_private_regular(metadata)
        if check_revision and _read_revision(descriptor) != expected_revision:
            raise RuntimeError("revision_conflict")
        return descriptor, stat.S_IMODE(metadata.st_mode)
    except Exception:
        os.close(descriptor)
        raise


def _require_target_witness(
    parent_fd: int,
    target_name: str,
    old_fd: int | None,
    *,
    check_revision: bool,
    expected_revision: object,
) -> None:
    try:
        observed = os.stat(target_name, dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        if old_fd is not None or (check_revision and expected_revision is not None):
            raise RuntimeError("revision_conflict")
        return
    if old_fd is None:
        raise RuntimeError("revision_conflict")
    opened = os.fstat(old_fd)
    if (observed.st_dev, observed.st_ino) != (opened.st_dev, opened.st_ino):
        raise RuntimeError("revision_conflict")
    _require_private_regular(observed)
    if check_revision and _read_revision(old_fd) != expected_revision:
        raise RuntimeError("revision_conflict")


def _restore_previous(
    parent_fd: int,
    target_name: str,
    *,
    old_fd: int | None,
    old_mode: int,
    backup_name: str,
    backup_created: bool,
) -> None:
    _unlink(parent_fd, target_name)
    if old_fd is not None and backup_created:
        os.fchmod(old_fd, old_mode)
        os.fsync(old_fd)
        os.replace(
            backup_name,
            target_name,
            src_dir_fd=parent_fd,
            dst_dir_fd=parent_fd,
        )
    os.fsync(parent_fd)


def _recover_interrupted_files(
    parent_fd: int,
    target_name: str,
    *,
    restore_missing: bool,
    expected_revision: str | None,
) -> None:
    prefix = f".{target_name}."
    backups: list[str] = []
    for name in os.listdir(parent_fd):
        if not name.startswith(prefix):
            continue
        suffix = name[len(prefix) :]
        token, separator, kind = suffix.partition(".")
        if (
            separator != "."
            or len(token) != 32
            or any(char not in "0123456789abcdef" for char in token)
            or kind not in {"tmp", "bak"}
        ):
            continue
        metadata = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        if not stat.S_ISREG(metadata.st_mode):
            raise ValueError("authority_runtime_store_recovery_artifact_invalid")
        if kind == "tmp":
            if metadata.st_nlink != 1:
                raise ValueError("authority_runtime_store_recovery_artifact_invalid")
            _unlink(parent_fd, name)
        else:
            backups.append(name)
    if len(backups) > 1:
        raise ValueError("authority_runtime_store_recovery_ambiguous")
    if not backups:
        return
    backup = backups[0]
    try:
        target_metadata = os.stat(
            target_name,
            dir_fd=parent_fd,
            follow_symlinks=False,
        )
    except FileNotFoundError:
        if not restore_missing:
            _unlink(parent_fd, backup)
            return
        if expected_revision is None:
            raise ValueError("authority_runtime_store_recovery_revision_required")
        os.chmod(backup, 0o600, dir_fd=parent_fd, follow_symlinks=False)
        _fsync_named_file(parent_fd, backup)
        if not _authority_snapshot_valid(parent_fd, backup):
            raise ValueError("authority_runtime_store_recovery_snapshot_invalid")
        if _read_named_revision(parent_fd, backup) != expected_revision:
            raise RuntimeError("revision_conflict")
        os.replace(
            backup,
            target_name,
            src_dir_fd=parent_fd,
            dst_dir_fd=parent_fd,
        )
        os.fsync(parent_fd)
        return
    backup_metadata = os.stat(backup, dir_fd=parent_fd, follow_symlinks=False)
    if backup_metadata.st_nlink not in {1, 2}:
        raise ValueError("authority_runtime_store_recovery_artifact_invalid")
    if not stat.S_ISREG(target_metadata.st_mode):
        raise ValueError("authority_runtime_store_target_not_regular")
    os.chmod(target_name, 0o600, dir_fd=parent_fd, follow_symlinks=False)
    _fsync_named_file(parent_fd, target_name)
    _unlink(parent_fd, backup)
    os.fsync(parent_fd)


def recover_posix_interrupted_files(
    parent_fd: int,
    target_name: str,
    *,
    expected_revision: object,
) -> None:
    """Recover only exact internal artifacts before an authority-store read."""

    _recover_interrupted_files(
        parent_fd,
        target_name,
        restore_missing=True,
        expected_revision=(
            expected_revision
            if isinstance(expected_revision, str) and expected_revision
            else None
        ),
    )


def _authority_snapshot_valid(parent_fd: int, name: str) -> bool:
    descriptor = os.open(
        name,
        os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0),
        dir_fd=parent_fd,
    )
    try:
        metadata = os.fstat(descriptor)
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_nlink != 1
            or metadata.st_size > 8 * 1024 * 1024
        ):
            return False
        os.lseek(descriptor, 0, os.SEEK_SET)
        raw = bytearray()
        while len(raw) < metadata.st_size:
            chunk = os.read(descriptor, metadata.st_size - len(raw))
            if not chunk:
                break
            raw.extend(chunk)
    finally:
        os.close(descriptor)
    if len(raw) != metadata.st_size:
        return False
    try:
        payload = json.loads(bytes(raw).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return False
    if not isinstance(payload, dict):
        return False
    revision = payload.pop("revision", None)
    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return (
        isinstance(revision, str)
        and revision
        == hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    )


def _read_named_revision(parent_fd: int, name: str) -> object:
    descriptor = os.open(
        name,
        os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0),
        dir_fd=parent_fd,
    )
    try:
        return _read_revision(descriptor)
    finally:
        os.close(descriptor)


def _fsync_named_file(parent_fd: int, name: str) -> None:
    descriptor = os.open(
        name,
        os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0),
        dir_fd=parent_fd,
    )
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _require_backup_identity(
    parent_fd: int,
    target_name: str,
    backup_name: str,
    old_fd: int,
    *,
    check_revision: bool,
    expected_revision: object,
) -> None:
    opened = os.fstat(old_fd)
    target = os.stat(target_name, dir_fd=parent_fd, follow_symlinks=False)
    backup = os.stat(backup_name, dir_fd=parent_fd, follow_symlinks=False)
    expected_identity = (opened.st_dev, opened.st_ino)
    if (
        (target.st_dev, target.st_ino) != expected_identity
        or (backup.st_dev, backup.st_ino) != expected_identity
        or opened.st_nlink != 2
        or stat.S_IMODE(opened.st_mode) != 0
    ):
        raise RuntimeError("revision_conflict")
    if check_revision and _read_revision(old_fd) != expected_revision:
        raise RuntimeError("revision_conflict")


def _link_descriptor(descriptor: int, parent_fd: int, name: str) -> None:
    libc = ctypes.CDLL(None, use_errno=True)
    linkat = libc.linkat
    linkat.argtypes = [
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
    ]
    linkat.restype = ctypes.c_int
    if linkat(
        descriptor,
        ctypes.c_char_p(b""),
        parent_fd,
        os.fsencode(name),
        _AT_EMPTY_PATH,
    ) != 0:
        proc_path = f"/proc/self/fd/{descriptor}".encode("ascii")
        if linkat(
            -100,
            proc_path,
            parent_fd,
            os.fsencode(name),
            0x400,
        ) != 0:
            error = ctypes.get_errno()
            raise OSError(
                error,
                "authority_runtime_store_unnamed_temp_link_failed",
            )


def _replace_entry(
    parent_fd: int,
    source_name: str,
    target_name: str,
    *,
    old_fd: int | None,
    backup_name: str | None,
    check_revision: bool,
    expected_revision: object,
) -> None:
    if old_fd is None:
        try:
            os.stat(target_name, dir_fd=parent_fd, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            raise RuntimeError("revision_conflict")
    else:
        if backup_name is None:
            raise RuntimeError("revision_conflict")
        _require_backup_identity(
            parent_fd,
            target_name,
            backup_name,
            old_fd,
            check_revision=check_revision,
            expected_revision=expected_revision,
        )
    libc = ctypes.CDLL(None, use_errno=True)
    renameat = libc.renameat
    renameat.argtypes = [
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_char_p,
    ]
    renameat.restype = ctypes.c_int
    if renameat(
        parent_fd,
        os.fsencode(source_name),
        parent_fd,
        os.fsencode(target_name),
    ) != 0:
        error = ctypes.get_errno()
        raise OSError(error, "authority_runtime_store_atomic_replace_failed")


def _write_descriptor(descriptor: int, payload: bytes) -> None:
    os.lseek(descriptor, 0, os.SEEK_SET)
    remaining = memoryview(payload)
    while remaining:
        written = os.write(descriptor, remaining)
        if written <= 0:
            raise OSError("authority_runtime_store_write_incomplete")
        remaining = remaining[written:]
    os.ftruncate(descriptor, len(payload))
    os.fsync(descriptor)


def _read_revision(descriptor: int) -> object:
    metadata = os.fstat(descriptor)
    if metadata.st_size > 8 * 1024 * 1024:
        raise ValueError("authority_runtime_store_target_too_large")
    os.lseek(descriptor, 0, os.SEEK_SET)
    raw = bytearray()
    while len(raw) < metadata.st_size:
        chunk = os.read(descriptor, metadata.st_size - len(raw))
        if not chunk:
            break
        raw.extend(chunk)
    if len(raw) != metadata.st_size:
        raise ValueError("authority_runtime_store_target_read_incomplete")
    try:
        payload = json.loads(bytes(raw).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("authority_runtime_store_target_invalid") from exc
    if not isinstance(payload, dict):
        raise ValueError("authority_runtime_store_target_invalid")
    return payload.get("revision")


def _require_unnamed_private_regular(metadata: os.stat_result) -> None:
    if not stat.S_ISREG(metadata.st_mode):
        raise ValueError("authority_runtime_store_temp_not_regular")
    if metadata.st_nlink != 0:
        raise ValueError("authority_runtime_store_temp_link_count")


def _require_private_regular(metadata: os.stat_result) -> None:
    if not stat.S_ISREG(metadata.st_mode):
        raise ValueError("authority_runtime_store_target_not_regular")
    if metadata.st_nlink != 1:
        raise ValueError("authority_runtime_store_target_link_count")


def _require_entry_identity(
    parent_fd: int,
    name: str,
    expected: os.stat_result,
    *,
    mode: int,
) -> None:
    observed = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    if (observed.st_dev, observed.st_ino) != (expected.st_dev, expected.st_ino):
        raise ValueError("authority_runtime_store_temp_identity_changed")
    if not stat.S_ISREG(observed.st_mode) or observed.st_nlink != 1:
        raise ValueError("authority_runtime_store_temp_link_count")
    if stat.S_IMODE(observed.st_mode) != mode:
        raise ValueError("authority_runtime_store_temp_mode_changed")


def _require_parent_identity(parent_fd: int, parent_path: Path) -> None:
    opened = os.fstat(parent_fd)
    expected = os.stat(parent_path, follow_symlinks=False)
    if (opened.st_dev, opened.st_ino) != (expected.st_dev, expected.st_ino):
        raise ValueError("authority_runtime_store_parent_changed")


def _unlink(parent_fd: int, name: str) -> None:
    try:
        os.unlink(name, dir_fd=parent_fd)
    except FileNotFoundError:
        pass


__all__ = ["posix_atomic_replace", "recover_posix_interrupted_files"]
