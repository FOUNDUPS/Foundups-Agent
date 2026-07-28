"""Windows handle operations for confined authority runtime replacement."""

from __future__ import annotations

import ctypes
import hashlib
import json
import os
import re
import stat
from ctypes import wintypes
from pathlib import Path


def windows_atomic_replace(
    parent_handle: int,
    target: Path,
    payload: bytes,
    *,
    check_revision: bool,
    expected_revision: object,
) -> None:
    """Replace one target while the verified parent and temp handles stay open."""

    import secrets

    _recover_interrupted_files(
        target,
        check_revision=check_revision,
        expected_revision=expected_revision,
        restore_missing=False,
    )
    _require_target_revision(
        target,
        check_revision=check_revision,
        expected_revision=expected_revision,
    )
    temp_path = target.parent / f".{target.name}.{secrets.token_hex(16)}.tmp"
    backup_path = target.parent / f".{target.name}.{secrets.token_hex(16)}.bak"
    backup_created = False
    handle = _create_temp(temp_path)
    renamed = False
    verified = False
    try:
        _require_private_regular(handle)
        _write_handle(handle, payload)
        _verify_or_scrub(handle, len(payload))
        _require_target_revision(
            target,
            check_revision=check_revision,
            expected_revision=expected_revision,
        )
        if _path_exists(target):
            _create_backup_link(target, backup_path)
            backup_created = True
            _require_backup_identity(
                target,
                backup_path,
                check_revision=check_revision,
                expected_revision=expected_revision,
            )
        _rename_handle(
            handle,
            parent_handle,
            target.name,
            target=target,
            backup=backup_path if backup_created else None,
            check_revision=check_revision,
            expected_revision=expected_revision,
        )
        renamed = True
        if not _same_path(_handle_path(handle), target.absolute()):
            raise ValueError("authority_runtime_store_temp_identity_changed")
        _verify_or_scrub(handle, len(payload))
        verified = True
    finally:
        close_windows_handle(handle)
        if renamed and not verified:
            if backup_created:
                _replace_path(backup_path, target)
            else:
                _unlink_path(target, missing_ok=True)
        else:
            _unlink_path(temp_path, missing_ok=True)
            _unlink_path(backup_path, missing_ok=True)


def _recover_interrupted_files(
    target: Path,
    *,
    check_revision: bool,
    expected_revision: object,
    restore_missing: bool,
) -> None:
    pattern = re.compile(
        rf"^\.{re.escape(target.name)}\.[0-9a-f]{{32}}\.(tmp|bak)$"
    )
    backups: list[Path] = []
    for candidate in target.parent.iterdir():
        match = pattern.fullmatch(candidate.name)
        if match is None:
            continue
        metadata = _stat_path(candidate)
        if not stat.S_ISREG(metadata.st_mode):
            raise ValueError("authority_runtime_store_recovery_artifact_invalid")
        if match.group(1) == "tmp":
            if int(getattr(metadata, "st_nlink", 1)) != 1:
                raise ValueError("authority_runtime_store_recovery_artifact_linked")
            _unlink_path(candidate)
        else:
            backups.append(candidate)
    if len(backups) > 1:
        raise ValueError("authority_runtime_store_recovery_ambiguous")
    if not backups:
        return
    backup = backups[0]
    if _path_exists(target):
        target_metadata = _stat_path(target)
        backup_metadata = _stat_path(backup)
        if (
            target_metadata.st_dev,
            target_metadata.st_ino,
        ) == (
            backup_metadata.st_dev,
            backup_metadata.st_ino,
        ):
            _unlink_path(backup)
            return
        _require_private_regular_path(backup_metadata)
        _unlink_path(backup)
        return
    if not restore_missing:
        _unlink_path(backup)
        return
    if not check_revision or not isinstance(expected_revision, str):
        raise ValueError("authority_runtime_store_recovery_revision_required")
    _require_private_regular_path(_stat_path(backup))
    if not _authority_snapshot_valid(backup):
        raise ValueError("authority_runtime_store_recovery_snapshot_invalid")
    if _read_revision(backup) != expected_revision:
        raise RuntimeError("revision_conflict")
    _replace_path(backup, target)


def recover_windows_interrupted_files(
    target: Path,
    *,
    expected_revision: object,
) -> None:
    """Recover only exact internal artifacts before an authority-store read."""

    _recover_interrupted_files(
        target,
        check_revision=isinstance(expected_revision, str) and bool(expected_revision),
        expected_revision=expected_revision,
        restore_missing=True,
    )


def _require_target_revision(
    target: Path,
    *,
    check_revision: bool,
    expected_revision: object,
) -> None:
    if not _path_exists(target):
        if check_revision and expected_revision is not None:
            raise RuntimeError("revision_conflict")
        return
    metadata = _stat_path(target)
    _require_private_regular_path(metadata)
    if check_revision and _read_revision(target) != expected_revision:
        raise RuntimeError("revision_conflict")


def _require_backup_identity(
    target: Path,
    backup: Path,
    *,
    check_revision: bool,
    expected_revision: object,
) -> None:
    target_metadata = _stat_path(target)
    backup_metadata = _stat_path(backup)
    if not stat.S_ISREG(target_metadata.st_mode):
        raise ValueError("authority_runtime_store_target_not_regular")
    if (
        target_metadata.st_dev,
        target_metadata.st_ino,
    ) != (
        backup_metadata.st_dev,
        backup_metadata.st_ino,
    ):
        raise RuntimeError("revision_conflict")
    if int(getattr(target_metadata, "st_nlink", 1)) != 2:
        raise ValueError("authority_runtime_store_target_link_count")
    if check_revision and _read_revision(backup) != expected_revision:
        raise RuntimeError("revision_conflict")


def _read_revision(path: Path) -> object:
    metadata = _stat_path(path)
    if not stat.S_ISREG(metadata.st_mode):
        raise ValueError("authority_runtime_store_target_not_regular")
    if metadata.st_size > 8 * 1024 * 1024:
        raise ValueError("authority_runtime_store_target_too_large")
    raw = _read_path_bytes(path)
    if len(raw) != metadata.st_size:
        raise ValueError("authority_runtime_store_target_read_incomplete")
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("authority_runtime_store_target_invalid") from exc
    if not isinstance(payload, dict):
        raise ValueError("authority_runtime_store_target_invalid")
    return payload.get("revision")


def _authority_snapshot_valid(path: Path) -> bool:
    metadata = _stat_path(path)
    if (
        not stat.S_ISREG(metadata.st_mode)
        or int(getattr(metadata, "st_nlink", 1)) != 1
        or metadata.st_size > 8 * 1024 * 1024
    ):
        return False
    raw = _read_path_bytes(path)
    if len(raw) != metadata.st_size:
        return False
    try:
        payload = json.loads(raw.decode("utf-8"))
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


def _require_private_regular_path(metadata: os.stat_result) -> None:
    if not stat.S_ISREG(metadata.st_mode):
        raise ValueError("authority_runtime_store_target_not_regular")
    if int(getattr(metadata, "st_nlink", 1)) != 1:
        raise ValueError("authority_runtime_store_target_link_count")


def _create_temp(path: Path) -> int:
    create_file = ctypes.windll.kernel32.CreateFileW
    create_file.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.LPVOID,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    ]
    create_file.restype = wintypes.HANDLE
    handle = create_file(
        _windows_api_path(path),
        0x40000000 | 0x00010000 | 0x00100000,
        0,
        None,
        1,
        0x00000100 | 0x80000000 | 0x00200000,
        None,
    )
    if handle in (0, -1, ctypes.c_void_p(-1).value):
        raise OSError("authority_runtime_store_temp_create_failed")
    return int(handle)


def _create_backup_link(target: Path, backup: Path) -> None:
    create_hard_link = ctypes.windll.kernel32.CreateHardLinkW
    create_hard_link.argtypes = [
        wintypes.LPCWSTR,
        wintypes.LPCWSTR,
        wintypes.LPVOID,
    ]
    create_hard_link.restype = wintypes.BOOL
    if not create_hard_link(
        _windows_api_path(backup),
        _windows_api_path(target),
        None,
    ):
        raise OSError("authority_runtime_store_backup_create_failed")


def _windows_api_path(path: Path) -> str:
    raw = str(path.resolve(strict=False))
    if raw.startswith("\\\\?\\"):
        return raw
    if raw.startswith("\\\\"):
        return "\\\\?\\UNC\\" + raw[2:]
    return "\\\\?\\" + raw


def _stat_path(path: Path) -> os.stat_result:
    return os.stat(_windows_api_path(path), follow_symlinks=False)


def _read_path_bytes(path: Path) -> bytes:
    with open(_windows_api_path(path), "rb") as handle:
        return handle.read()


def _path_exists(path: Path) -> bool:
    return os.path.exists(_windows_api_path(path))


def _unlink_path(path: Path, *, missing_ok: bool = False) -> None:
    try:
        os.unlink(_windows_api_path(path))
    except FileNotFoundError:
        if not missing_ok:
            raise


def _replace_path(source: Path, target: Path) -> None:
    os.replace(_windows_api_path(source), _windows_api_path(target))


def _require_private_regular(handle: int) -> None:
    metadata = _stat_path(_handle_path(handle))
    if not stat.S_ISREG(metadata.st_mode):
        raise ValueError("authority_runtime_store_temp_not_regular")
    if int(getattr(metadata, "st_nlink", 1)) != 1:
        raise ValueError("authority_runtime_store_temp_link_count")


def _verify_or_scrub(handle: int, size: int) -> None:
    try:
        _require_private_regular(handle)
    except Exception:
        _scrub_handle(handle, size)
        raise


def _scrub_handle(handle: int, size: int) -> None:
    distance = ctypes.c_longlong(0)
    set_pointer = ctypes.windll.kernel32.SetFilePointerEx
    set_pointer.argtypes = [
        wintypes.HANDLE,
        ctypes.c_longlong,
        ctypes.POINTER(ctypes.c_longlong),
        wintypes.DWORD,
    ]
    set_pointer.restype = wintypes.BOOL
    if not set_pointer(handle, distance, None, 0):
        return
    try:
        _write_handle(handle, b"\x00" * max(size, 0))
    except OSError:
        pass


def _write_handle(handle: int, payload: bytes) -> None:
    write_file = ctypes.windll.kernel32.WriteFile
    write_file.argtypes = [
        wintypes.HANDLE,
        wintypes.LPCVOID,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
        wintypes.LPVOID,
    ]
    write_file.restype = wintypes.BOOL
    written = wintypes.DWORD()
    buffer = ctypes.create_string_buffer(payload)
    if not write_file(handle, buffer, len(payload), ctypes.byref(written), None):
        raise OSError("authority_runtime_store_write_failed")
    if int(written.value) != len(payload):
        raise OSError("authority_runtime_store_write_incomplete")
    if not ctypes.windll.kernel32.FlushFileBuffers(handle):
        raise OSError("authority_runtime_store_flush_failed")


def _rename_handle(
    handle: int,
    parent_handle: int,
    target_name: str,
    *,
    target: Path,
    backup: Path | None,
    check_revision: bool,
    expected_revision: object,
) -> None:
    if backup is None:
        if _path_exists(target):
            raise RuntimeError("revision_conflict")
    else:
        _require_backup_identity(
            target,
            backup,
            check_revision=check_revision,
            expected_revision=expected_revision,
        )

    class _FileRenameInfo(ctypes.Structure):
        _fields_ = [
            ("ReplaceIfExists", wintypes.BOOL),
            ("RootDirectory", wintypes.HANDLE),
            ("FileNameLength", wintypes.DWORD),
            ("FileName", wintypes.WCHAR * 1),
        ]

    target = _handle_path(parent_handle) / target_name
    encoded = _windows_api_path(target).encode("utf-16-le")
    size = ctypes.sizeof(_FileRenameInfo) + len(encoded)
    storage = ctypes.create_string_buffer(size)
    info = ctypes.cast(storage, ctypes.POINTER(_FileRenameInfo)).contents
    info.ReplaceIfExists = True
    info.RootDirectory = None
    info.FileNameLength = len(encoded)
    ctypes.memmove(
        ctypes.addressof(storage) + _FileRenameInfo.FileName.offset,
        encoded,
        len(encoded),
    )
    set_info = ctypes.windll.kernel32.SetFileInformationByHandle
    set_info.argtypes = [
        wintypes.HANDLE,
        ctypes.c_int,
        wintypes.LPVOID,
        wintypes.DWORD,
    ]
    set_info.restype = wintypes.BOOL
    if not set_info(handle, 3, storage, size):
        error = ctypes.windll.kernel32.GetLastError()
        raise OSError(int(error), "authority_runtime_store_atomic_replace_failed")


def open_windows_directory_without_delete_share(path: Path) -> int:
    """Open and verify a parent handle that prevents path replacement."""

    create_file = ctypes.windll.kernel32.CreateFileW
    create_file.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.LPVOID,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    ]
    create_file.restype = wintypes.HANDLE
    handle = create_file(
        _windows_api_path(path),
        0x80000000,
        0x00000001 | 0x00000002,
        None,
        3,
        0x02000000 | 0x00200000,
        None,
    )
    if handle in (0, -1, ctypes.c_void_p(-1).value):
        raise OSError("authority_runtime_store_parent_open_failed")
    try:
        if _same_path(_handle_path(handle), path.resolve(strict=True)):
            return int(handle)
    except Exception:
        close_windows_handle(handle)
        raise
    close_windows_handle(handle)
    raise ValueError("authority_runtime_store_parent_changed")


def _handle_path(handle: int) -> Path:
    buffer = ctypes.create_unicode_buffer(32768)
    get_path = ctypes.windll.kernel32.GetFinalPathNameByHandleW
    get_path.argtypes = [
        wintypes.HANDLE,
        wintypes.LPWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
    ]
    get_path.restype = wintypes.DWORD
    length = get_path(handle, buffer, len(buffer), 0)
    if length <= 0 or length >= len(buffer):
        raise OSError("authority_runtime_store_parent_path_unavailable")
    raw = buffer.value.replace("\\", "/")
    if raw.startswith("//?/UNC/"):
        raw = "//" + raw[8:]
    elif raw.startswith("//?/"):
        raw = raw[4:]
    return Path(raw)


def close_windows_handle(handle: int) -> None:
    close_handle = ctypes.windll.kernel32.CloseHandle
    close_handle.argtypes = [wintypes.HANDLE]
    close_handle.restype = wintypes.BOOL
    close_handle(handle)


def _same_path(left: Path, right: Path) -> bool:
    return os.path.normcase(str(left)) == os.path.normcase(str(right))


__all__ = [
    "close_windows_handle",
    "open_windows_directory_without_delete_share",
    "recover_windows_interrupted_files",
    "windows_atomic_replace",
]
