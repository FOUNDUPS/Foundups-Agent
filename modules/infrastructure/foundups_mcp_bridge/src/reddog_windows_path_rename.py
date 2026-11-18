"""Extended-path Windows no-replace rename for files and directories."""

from __future__ import annotations

import ctypes
import os
from ctypes import wintypes
from pathlib import Path


_MOVEFILE_WRITE_THROUGH = 0x00000008


def _api_path(path: Path) -> str:
    raw = os.path.abspath(os.fspath(path))
    if raw.startswith("\\\\?\\"):
        return raw
    if raw.startswith("\\\\"):
        return "\\\\?\\UNC\\" + raw[2:]
    return "\\\\?\\" + raw


def rename_windows_path_no_replace(source: Path, target: Path) -> None:
    """Move one file or directory with extended paths and no replacement."""

    if os.name != "nt":
        raise OSError("windows_path_rename_api_unavailable")
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    move = kernel32.MoveFileExW
    move.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD]
    move.restype = wintypes.BOOL
    if move(_api_path(source), _api_path(target), _MOVEFILE_WRITE_THROUGH):
        return
    error = ctypes.get_last_error()
    if error in {5, 32, 80, 183}:
        raise FileExistsError(error, "windows_path_target_exists")
    raise ctypes.WinError(error)


__all__ = ["rename_windows_path_no_replace"]
