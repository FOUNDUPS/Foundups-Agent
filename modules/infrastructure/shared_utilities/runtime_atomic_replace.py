"""Same-directory durable atomic replacement for validated runtime artifacts."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path


def atomic_replace_runtime_text(target: Path, text: str) -> None:
    """Publish complete UTF-8 bytes atomically; preserve the prior file on failure."""

    target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{target.name}.", suffix=".tmp", dir=target.parent
    )
    temporary = Path(temporary_name)
    published = False
    try:
        if os.name != "nt":
            os.fchmod(descriptor, 0o600)
        _write_all(descriptor, text.encode("utf-8"))
        os.fsync(descriptor)
        os.close(descriptor)
        descriptor = -1
        _atomic_replace_path(temporary, target)
        published = True
        _fsync_parent_directory(target.parent)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        if not published:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass


def _write_all(descriptor: int, payload: bytes) -> None:
    remaining = memoryview(payload)
    while remaining:
        written = os.write(descriptor, remaining)
        if written <= 0:
            raise OSError("runtime_atomic_replace_write_incomplete")
        remaining = remaining[written:]


def _atomic_replace_path(source: Path, target: Path) -> None:
    if os.name != "nt":
        os.replace(source, target)
        return
    import ctypes

    move_file = ctypes.windll.kernel32.MoveFileExW
    move_file.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint32]
    move_file.restype = ctypes.c_int
    replace_existing = 0x1
    write_through = 0x8
    if not move_file(str(source), str(target), replace_existing | write_through):
        raise ctypes.WinError()


def _fsync_parent_directory(parent: Path) -> None:
    if os.name == "nt":
        return
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    descriptor = os.open(parent, flags)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


__all__ = ["atomic_replace_runtime_text"]
