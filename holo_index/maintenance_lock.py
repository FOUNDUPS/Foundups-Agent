"""Cross-process HoloIndex maintenance lease and read-only probe.

The maintenance owner acquires a non-blocking exclusive byte-range lease before
changing index state. Query workers only probe an existing lease file; probing
an absent path never creates the directory or file. Any probe uncertainty is
reported as unsafe so callers can fail closed.
"""

from __future__ import annotations

import errno
import os
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO


MAINTENANCE_LOCK_FILENAME = "holoindex_maintenance.lock"


class MaintenanceLockError(RuntimeError):
    """Base error for a maintenance lease operation."""


class MaintenanceLeaseBusy(MaintenanceLockError):
    """Raised when another process already owns the maintenance lease."""


@dataclass(frozen=True)
class MaintenanceLockProbe:
    """Read-only observation of the maintenance lease boundary."""

    path: str
    status: str
    clear: bool
    reason: str = ""

    @property
    def held(self) -> bool:
        return self.status == "held"


def maintenance_lock_path(ssd_path: Path | str) -> Path:
    """Return the canonical maintenance lease path for a storage root."""

    return Path(ssd_path) / "indexes" / MAINTENANCE_LOCK_FILENAME


def _is_contention_error(exc: OSError) -> bool:
    contention_errnos = {
        errno.EACCES,
        errno.EAGAIN,
        getattr(errno, "EWOULDBLOCK", errno.EAGAIN),
    }
    # Windows reports ERROR_LOCK_VIOLATION or ERROR_SHARING_VIOLATION through
    # winerror, depending on the filesystem and Python runtime.
    return exc.errno in contention_errnos or getattr(exc, "winerror", None) in {32, 33, 36}


def _lock_nonblocking(handle: BinaryIO) -> None:
    handle.seek(0)
    if os.name == "nt":
        import msvcrt

        try:
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError as exc:
            if _is_contention_error(exc):
                raise MaintenanceLeaseBusy("maintenance lease is already held") from exc
            raise MaintenanceLockError(f"maintenance lease acquisition failed: {exc}") from exc
        return

    import fcntl

    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError as exc:
        if _is_contention_error(exc):
            raise MaintenanceLeaseBusy("maintenance lease is already held") from exc
        raise MaintenanceLockError(f"maintenance lease acquisition failed: {exc}") from exc


def _unlock(handle: BinaryIO) -> None:
    handle.seek(0)
    if os.name == "nt":
        import msvcrt

        try:
            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        except OSError as exc:
            raise MaintenanceLockError(f"maintenance lease release failed: {exc}") from exc
        return

    import fcntl

    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    except OSError as exc:
        raise MaintenanceLockError(f"maintenance lease release failed: {exc}") from exc


class MaintenanceLease:
    """Owned non-blocking exclusive lease; use as a context manager."""

    def __init__(self, path: Path, handle: BinaryIO) -> None:
        self.path = path
        self._handle = handle
        self._released = False

    @property
    def released(self) -> bool:
        return self._released

    def release(self) -> None:
        if self._released:
            return
        try:
            _unlock(self._handle)
        finally:
            self._handle.close()
            self._released = True

    def __enter__(self) -> "MaintenanceLease":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.release()


def acquire_maintenance_lease(path: Path | str) -> MaintenanceLease:
    """Acquire the exclusive maintenance lease without waiting.

    This is the only operation in this module that may create the lease path.
    The persistent sentinel file is intentionally retained after release so no
    process can replace the locked inode during normal operation.
    """

    lock_path = Path(path)
    try:
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        handle = lock_path.open("a+b", buffering=0)
        if lock_path.stat().st_size < 1:
            handle.write(b"\0")
            handle.flush()
            os.fsync(handle.fileno())
        _lock_nonblocking(handle)
    except MaintenanceLockError:
        if "handle" in locals():
            handle.close()
        raise
    except OSError as exc:
        if "handle" in locals():
            handle.close()
        raise MaintenanceLockError(f"maintenance lease setup failed: {exc}") from exc
    return MaintenanceLease(lock_path, handle)


def probe_maintenance_lock(path: Path | str) -> MaintenanceLockProbe:
    """Probe an existing lease without creating or modifying filesystem data.

    ``clear`` is false both when maintenance is active and when the lease state
    cannot be proven. Callers must gate queries on ``clear`` rather than merely
    checking ``held``.
    """

    lock_path = Path(path)
    try:
        details = lock_path.stat()
    except FileNotFoundError:
        return MaintenanceLockProbe(str(lock_path), "absent", True)
    except OSError as exc:
        return MaintenanceLockProbe(str(lock_path), "error", False, f"lock_stat_failed:{exc}")

    if not stat.S_ISREG(details.st_mode) or details.st_size < 1:
        return MaintenanceLockProbe(
            str(lock_path),
            "error",
            False,
            "lock_file_invalid",
        )

    try:
        handle = lock_path.open("rb", buffering=0)
    except OSError as exc:
        return MaintenanceLockProbe(str(lock_path), "error", False, f"lock_open_failed:{exc}")

    try:
        _lock_nonblocking(handle)
    except MaintenanceLeaseBusy:
        return MaintenanceLockProbe(str(lock_path), "held", False, "maintenance_in_progress")
    except MaintenanceLockError as exc:
        return MaintenanceLockProbe(str(lock_path), "error", False, f"lock_probe_failed:{exc}")
    else:
        try:
            _unlock(handle)
        except MaintenanceLockError as exc:
            return MaintenanceLockProbe(
                str(lock_path),
                "error",
                False,
                f"lock_probe_release_failed:{exc}",
            )
        return MaintenanceLockProbe(str(lock_path), "idle", True)
    finally:
        handle.close()


__all__ = [
    "MAINTENANCE_LOCK_FILENAME",
    "MaintenanceLease",
    "MaintenanceLeaseBusy",
    "MaintenanceLockError",
    "MaintenanceLockProbe",
    "acquire_maintenance_lease",
    "maintenance_lock_path",
    "probe_maintenance_lock",
]
