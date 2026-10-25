"""Fail-closed directory durability for configured AutoResearch evidence."""

from __future__ import annotations

import os
import stat
from pathlib import Path


def _fsync_directory(path: Path) -> None:
    """Persist one directory entry set or fail closed on this platform."""

    if os.name == "nt":
        _flush_windows_directory(path)
        return
    flags = (
        os.O_RDONLY
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    descriptor = os.open(str(path), flags)
    try:
        opened = os.fstat(descriptor)
        expected = os.stat(path, follow_symlinks=False)
        if (
            not stat.S_ISDIR(opened.st_mode)
            or (opened.st_dev, opened.st_ino) != (expected.st_dev, expected.st_ino)
        ):
            raise OSError("configured_gateway_directory_identity_changed")
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _flush_windows_directory(path: Path) -> None:
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    create_file = kernel32.CreateFileW
    create_file.argtypes = [
        wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID,
        wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE,
    ]
    create_file.restype = wintypes.HANDLE
    handle = create_file(
        _windows_api_path(path),
        0x40000000,
        0x00000001 | 0x00000002 | 0x00000004,
        None,
        3,
        0x02000000 | 0x00200000,
        None,
    )
    invalid = ctypes.c_void_p(-1).value
    if handle in (0, -1, invalid):
        raise OSError(ctypes.get_last_error(), "configured_gateway_directory_open_failed")
    try:
        attributes = _windows_handle_attributes(kernel32, handle)
    except BaseException:
        _close_windows_handle(kernel32, handle)
        raise
    if not attributes & 0x00000010 or attributes & 0x00000400:
        _close_windows_handle(kernel32, handle)
        raise OSError("configured_gateway_directory_identity_invalid")
    flush = _windows_bool_handle_function(kernel32, "FlushFileBuffers")
    flushed = bool(flush(handle))
    flush_error = ctypes.get_last_error()
    _close_windows_handle(kernel32, handle)
    if not flushed:
        raise OSError(flush_error, "configured_gateway_directory_fsync_failed")


def _windows_handle_attributes(kernel32: object, handle: object) -> int:
    import ctypes
    from ctypes import wintypes

    class _ByHandleFileInformation(ctypes.Structure):
        _fields_ = [
            ("attributes", wintypes.DWORD),
            ("creation_time", wintypes.FILETIME),
            ("access_time", wintypes.FILETIME),
            ("write_time", wintypes.FILETIME),
            ("volume_serial", wintypes.DWORD),
            ("size_high", wintypes.DWORD),
            ("size_low", wintypes.DWORD),
            ("links", wintypes.DWORD),
            ("index_high", wintypes.DWORD),
            ("index_low", wintypes.DWORD),
        ]

    info = _ByHandleFileInformation()
    get_info = kernel32.GetFileInformationByHandle
    get_info.argtypes = [wintypes.HANDLE, ctypes.POINTER(_ByHandleFileInformation)]
    get_info.restype = wintypes.BOOL
    if not get_info(handle, ctypes.byref(info)):
        raise OSError(ctypes.get_last_error(), "configured_gateway_directory_identity_failed")
    return int(info.attributes)


def _close_windows_handle(kernel32: object, handle: object) -> None:
    import ctypes

    close_handle = _windows_bool_handle_function(kernel32, "CloseHandle")
    if not close_handle(handle):
        raise OSError(ctypes.get_last_error(), "configured_gateway_directory_close_failed")


def _windows_bool_handle_function(kernel32: object, name: str) -> object:
    from ctypes import wintypes

    function = getattr(kernel32, name)
    function.argtypes = [wintypes.HANDLE]
    function.restype = wintypes.BOOL
    return function


def _windows_api_path(path: Path) -> str:
    value = str(path.resolve())
    if value.startswith("\\\\?\\"):
        return value
    if value.startswith("\\\\"):
        return "\\\\?\\UNC\\" + value[2:]
    return "\\\\?\\" + value


def _fsync_store_lineage(parent: Path, root: Path) -> None:
    if parent != root and not parent.is_relative_to(root):
        raise OSError("configured_gateway_directory_outside_store")
    boundary = root.parent
    current = parent
    while True:
        _fsync_directory(current)
        if current == boundary:
            return
        if current == current.parent:
            raise OSError("configured_gateway_directory_lineage_invalid")
        current = current.parent
