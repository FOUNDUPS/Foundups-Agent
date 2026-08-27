"""Bounded machine-wide runtime operation locks for shared utilities."""

from __future__ import annotations

import hashlib
import os
import stat
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


@contextmanager
def exclusive_runtime_lock(
    path: Path, *, timeout_seconds: float | None = None
) -> Iterator[None]:
    """Acquire one cross-process lock, optionally with a bounded wait."""

    lock_key = hashlib.sha256(os.path.normcase(str(path)).encode("utf-8")).hexdigest()
    if os.name == "nt":
        with _windows_lock(lock_key, timeout_seconds):
            yield
        return
    with _posix_lock(lock_key, timeout_seconds):
        yield


def validated_lock_timeout(value: float | None) -> float | None:
    if value is None:
        return None
    timeout = float(value)
    if not 0.01 <= timeout <= 600.0:
        raise ValueError("runtime_operation_lock_timeout_invalid")
    return timeout


def windows_runtime_mutex_name(lock_key: str) -> str:
    """Return one machine-global mutex name for cross-session serialization."""

    return f"Global\\FoundupsRuntime-{lock_key}"


@contextmanager
def _windows_lock(
    lock_key: str, timeout_seconds: float | None
) -> Iterator[None]:
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.windll.kernel32
    create_mutex = kernel32.CreateMutexW
    create_mutex.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
    create_mutex.restype = wintypes.HANDLE
    wait_for_single = kernel32.WaitForSingleObject
    wait_for_single.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    wait_for_single.restype = wintypes.DWORD
    release_mutex = kernel32.ReleaseMutex
    release_mutex.argtypes = [wintypes.HANDLE]
    release_mutex.restype = wintypes.BOOL
    close_handle = kernel32.CloseHandle
    close_handle.argtypes = [wintypes.HANDLE]
    close_handle.restype = wintypes.BOOL
    handle = create_mutex(None, False, windows_runtime_mutex_name(lock_key))
    if not handle:
        raise OSError("runtime_artifact_mutex_create_failed")
    wait_ms = (
        0xFFFFFFFF
        if timeout_seconds is None
        else max(1, min(int(timeout_seconds * 1000), 0xFFFFFFFE))
    )
    wait_result = wait_for_single(handle, wait_ms)
    if wait_result == 0x00000102:
        close_handle(handle)
        raise TimeoutError("runtime_operation_lock_timeout")
    if wait_result not in (0x00000000, 0x00000080):
        close_handle(handle)
        raise OSError("runtime_artifact_mutex_wait_failed")
    try:
        yield
    finally:
        release_mutex(handle)
        close_handle(handle)


@contextmanager
def _posix_lock(
    lock_key: str, timeout_seconds: float | None
) -> Iterator[None]:
    import fcntl

    root_descriptor = _open_private_lock_root()
    try:
        descriptor = os.open(
            f"{lock_key}.lock",
            os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0),
            0o600,
            dir_fd=root_descriptor,
        )
        try:
            _require_private_regular_file(os.fstat(descriptor))
            _acquire_posix_lock(descriptor, timeout_seconds)
            try:
                yield
            finally:
                fcntl.flock(descriptor, fcntl.LOCK_UN)
        finally:
            os.close(descriptor)
    finally:
        os.close(root_descriptor)


def _open_private_lock_root() -> int:
    lock_root = Path(tempfile.gettempdir()) / "foundups-runtime-locks"
    try:
        lock_root.mkdir(mode=0o700)
    except FileExistsError:
        pass
    metadata = os.lstat(lock_root)
    _require_private_directory(metadata)
    descriptor = os.open(
        lock_root,
        os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_NOFOLLOW", 0),
    )
    opened = os.fstat(descriptor)
    if (opened.st_dev, opened.st_ino) != (metadata.st_dev, metadata.st_ino):
        os.close(descriptor)
        raise OSError("runtime_artifact_lock_root_changed")
    return descriptor


def _require_private_directory(value: os.stat_result) -> None:
    if (
        not stat.S_ISDIR(value.st_mode)
        or stat.S_IMODE(value.st_mode) != 0o700
        or value.st_uid != os.geteuid()
    ):
        raise PermissionError("runtime_artifact_lock_root_not_private")


def _acquire_posix_lock(descriptor: int, timeout_seconds: float | None) -> None:
    import fcntl

    if timeout_seconds is None:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        return
    deadline = time.monotonic() + timeout_seconds
    while True:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return
        except BlockingIOError:
            if time.monotonic() >= deadline:
                raise TimeoutError("runtime_operation_lock_timeout") from None
            time.sleep(min(0.05, max(0.0, deadline - time.monotonic())))


def _require_private_regular_file(value: os.stat_result) -> None:
    if not stat.S_ISREG(value.st_mode):
        raise ValueError("runtime_artifact_not_regular_file")
    if os.name != "nt" and (
        stat.S_IMODE(value.st_mode) & 0o077
        or value.st_uid != os.geteuid()
        or value.st_nlink != 1
    ):
        raise PermissionError("runtime_artifact_permissions_too_broad")


__all__ = [
    "exclusive_runtime_lock",
    "validated_lock_timeout",
    "windows_runtime_mutex_name",
]
