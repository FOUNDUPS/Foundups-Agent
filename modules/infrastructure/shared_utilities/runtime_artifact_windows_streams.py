"""Fail-closed Windows stream enumeration for runtime artifacts."""

from __future__ import annotations

import ctypes
import os
import stat
import struct
from ctypes import wintypes
from pathlib import Path


_FILE_READ_ATTRIBUTES = 0x00000080
_FILE_SHARE_READ = 0x00000001
_OPEN_EXISTING = 3
_FILE_ATTRIBUTE_NORMAL = 0x00000080
_FILE_FLAG_BACKUP_SEMANTICS = 0x02000000
_FILE_FLAG_OPEN_REPARSE_POINT = 0x00200000
_FILE_STREAM_INFO_CLASS = 7
_INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value
_ERROR_MORE_DATA = 234
_ERROR_INSUFFICIENT_BUFFER = 122
_ERROR_HANDLE_EOF = 38
_MAX_STREAM_INFO_BYTES = 1024 * 1024
_UNNAMED_DATA_STREAM = "::$DATA"


def windows_extended_path(path: Path | str) -> str:
    """Return one absolute Windows API spelling without the MAX_PATH limit."""

    raw = os.path.abspath(os.fspath(path))
    if raw.startswith("\\\\?\\"):
        return raw
    if raw.startswith("\\\\"):
        return "\\\\?\\UNC\\" + raw[2:]
    return "\\\\?\\" + raw


def _kernel32() -> ctypes.WinDLL:
    if os.name != "nt":
        raise OSError("windows_stream_api_unavailable")
    return ctypes.WinDLL("kernel32", use_last_error=True)


def _open_artifact(path: Path) -> tuple[int, bool]:
    metadata = os.lstat(windows_extended_path(path))
    is_directory = stat.S_ISDIR(metadata.st_mode)
    if not (stat.S_ISREG(metadata.st_mode) or is_directory):
        raise ValueError("runtime_artifact_stream_target_invalid")
    kernel32 = _kernel32()
    create_file = kernel32.CreateFileW
    create_file.argtypes = [
        wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID,
        wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE,
    ]
    create_file.restype = wintypes.HANDLE
    flags = _FILE_ATTRIBUTE_NORMAL | _FILE_FLAG_OPEN_REPARSE_POINT
    if is_directory:
        flags |= _FILE_FLAG_BACKUP_SEMANTICS
    handle = create_file(
        windows_extended_path(path), _FILE_READ_ATTRIBUTES, _FILE_SHARE_READ, None,
        _OPEN_EXISTING, flags, None,
    )
    if handle in (0, -1, _INVALID_HANDLE_VALUE):
        raise OSError(ctypes.get_last_error(), "windows_stream_handle_unavailable")
    return int(handle), is_directory


def _close_handle(handle: int) -> None:
    kernel32 = _kernel32()
    close = kernel32.CloseHandle
    close.argtypes = [wintypes.HANDLE]
    close.restype = wintypes.BOOL
    close(wintypes.HANDLE(handle))


def _stream_info(handle: int) -> bytes:
    kernel32 = _kernel32()
    get_info = kernel32.GetFileInformationByHandleEx
    get_info.argtypes = [
        wintypes.HANDLE, ctypes.c_int, wintypes.LPVOID, wintypes.DWORD,
    ]
    get_info.restype = wintypes.BOOL
    size = 4096
    while size <= _MAX_STREAM_INFO_BYTES:
        buffer = ctypes.create_string_buffer(size)
        if get_info(handle, _FILE_STREAM_INFO_CLASS, buffer, size):
            return bytes(buffer)
        error = ctypes.get_last_error()
        if error == _ERROR_HANDLE_EOF:
            return b""
        if error not in {_ERROR_MORE_DATA, _ERROR_INSUFFICIENT_BUFFER}:
            raise OSError(error, "windows_stream_enumeration_failed")
        size *= 2
    raise ValueError("runtime_artifact_stream_enumeration_bound")


def _stream_names(raw: bytes) -> tuple[str, ...]:
    if not raw:
        return ()
    names: list[str] = []
    offset = 0
    while True:
        if offset + 24 > len(raw):
            raise ValueError("runtime_artifact_stream_metadata_invalid")
        next_offset, name_bytes = struct.unpack_from("<II", raw, offset)
        if name_bytes <= 0 or name_bytes % 2 or offset + 24 + name_bytes > len(raw):
            raise ValueError("runtime_artifact_stream_metadata_invalid")
        try:
            name = raw[offset + 24 : offset + 24 + name_bytes].decode("utf-16-le")
        except UnicodeDecodeError as exc:
            raise ValueError("runtime_artifact_stream_metadata_invalid") from exc
        names.append(name)
        if next_offset == 0:
            return tuple(names)
        if next_offset < 24 + name_bytes or next_offset % 8:
            raise ValueError("runtime_artifact_stream_metadata_invalid")
        offset += next_offset


def require_unnamed_data_stream_only(path: Path | str) -> None:
    """Reject named streams on a Windows regular file or directory."""

    if os.name != "nt":
        return
    handle, is_directory = _open_artifact(
        Path(os.path.abspath(os.fspath(path)))
    )
    try:
        names = _stream_names(_stream_info(handle))
    finally:
        _close_handle(handle)
    expected = () if is_directory else (_UNNAMED_DATA_STREAM,)
    if names != expected:
        raise ValueError("runtime_artifact_alternate_stream_rejected")


__all__ = ["require_unnamed_data_stream_only", "windows_extended_path"]
