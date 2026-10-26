"""Cross-process HoloIndex maintenance lease and read-only probe.

The maintenance owner acquires a non-blocking exclusive byte-range lease before
changing index state. Query workers only probe an existing lease file; probing
an absent path never creates the directory or file. Any probe uncertainty is
reported as unsafe so callers can fail closed.
"""

from __future__ import annotations

import errno
import hashlib
import os
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO


MAINTENANCE_LOCK_FILENAME = "holoindex_maintenance.lock"
AUTHORITY_UPDATE_LOCK_FILENAME = "holoindex_authority_update.lock"
AUTHORITY_BLOCK_MARKER_FILENAME = ".holoindex_authority_blocked"
AUTHORITY_BLOCK_MARKER_CONTENT = b"holoindex_authority_blocked_v1\n"


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


@dataclass(frozen=True)
class MaintenanceSentinelProof:
    """Identity and exact-byte proof for a retained existing sentinel."""

    path: Path
    device: int
    inode: int
    mode: int
    attributes: int
    size: int
    sha256: str


def maintenance_lock_path(ssd_path: Path | str) -> Path:
    """Return the canonical maintenance lease path for a storage root."""

    return Path(ssd_path) / "indexes" / MAINTENANCE_LOCK_FILENAME


def authority_update_lock_path(ssd_path: Path | str) -> Path:
    """Return the separate cross-process authority-checkout lease path."""
    return Path(ssd_path) / "indexes" / AUTHORITY_UPDATE_LOCK_FILENAME


def authority_block_marker_path(repo_root: Path | str) -> Path:
    """Return the fixed fail-closed marker in the authority worktree."""
    return Path(repo_root) / AUTHORITY_BLOCK_MARKER_FILENAME


def authority_block_marker_valid(repo_root: Path | str) -> bool:
    """Accept only the exact regular marker published by trusted WRE."""
    marker = authority_block_marker_path(repo_root)
    try:
        metadata = marker.lstat()
        return bool(
            stat.S_ISREG(metadata.st_mode)
            and marker.read_bytes() == AUTHORITY_BLOCK_MARKER_CONTENT
        )
    except (FileNotFoundError, OSError):
        return False


def acquire_authority_update_lease(
    ssd_path: Path | str,
) -> MaintenanceLease:
    """Acquire the outer authority lease without nesting the SSD writer lease."""
    return acquire_maintenance_lease(authority_update_lock_path(ssd_path))


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


class ExistingMaintenanceLease(MaintenanceLease):
    """Non-creating lease that retains and revalidates an exact sentinel."""

    def __init__(
        self, path: Path, handle: BinaryIO, proof: MaintenanceSentinelProof,
        max_bytes: int,
    ) -> None:
        super().__init__(path, handle)
        self.sentinel_proof = proof
        self._max_bytes = max_bytes

    def revalidate_sentinel(self) -> None:
        """Prove the retained object identity and bytes are unchanged."""

        if not _path_matches_sentinel_proof(self.sentinel_proof):
            raise MaintenanceLockError("maintenance sentinel path identity changed")
        current = _sentinel_proof(
            self.path, os.fstat(self._handle.fileno()), self._handle,
            self._max_bytes,
        )
        if current != self.sentinel_proof:
            raise MaintenanceLockError("maintenance sentinel changed while leased")

    def release(self) -> None:
        if self._released:
            return
        error: BaseException | None = None
        try:
            self.revalidate_sentinel()
        except BaseException as exc:
            error = exc
        try:
            _unlock(self._handle)
        except BaseException as exc:
            if error is None:
                error = exc
        finally:
            self._handle.close()
            self._released = True
        if error is not None:
            raise error


def _link_or_reparse(metadata: os.stat_result) -> bool:
    attributes = int(getattr(metadata, "st_file_attributes", 0))
    reparse_flag = int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))
    return stat.S_ISLNK(metadata.st_mode) or bool(attributes & reparse_flag)


def _valid_existing_sentinel_metadata(
    metadata: os.stat_result, max_bytes: int,
) -> bool:
    return bool(
        stat.S_ISREG(metadata.st_mode)
        and not _link_or_reparse(metadata)
        and int(getattr(metadata, "st_nlink", 1)) == 1
        and int(metadata.st_ino) > 0
        and 1 <= int(metadata.st_size) <= max_bytes
    )


def _path_matches_sentinel_proof(proof: MaintenanceSentinelProof) -> bool:
    try:
        metadata = os.lstat(proof.path)
    except OSError:
        return False
    return bool(
        _valid_existing_sentinel_metadata(metadata, proof.size)
        and int(metadata.st_dev) == proof.device
        and int(metadata.st_ino) == proof.inode
        and int(metadata.st_mode) == proof.mode
        and int(getattr(metadata, "st_file_attributes", 0)) == proof.attributes
        and int(metadata.st_size) == proof.size
    )


def _sentinel_proof(
    path: Path, metadata: os.stat_result, handle: BinaryIO, max_bytes: int,
) -> MaintenanceSentinelProof:
    if not _valid_existing_sentinel_metadata(metadata, max_bytes):
        raise MaintenanceLockError("existing maintenance sentinel is invalid")
    handle.seek(0)
    content = handle.read(max_bytes + 1)
    if len(content) != int(metadata.st_size) or len(content) > max_bytes:
        raise MaintenanceLockError("existing maintenance sentinel bytes are unproven")
    return MaintenanceSentinelProof(
        path=path,
        device=int(metadata.st_dev),
        inode=int(metadata.st_ino),
        mode=int(metadata.st_mode),
        attributes=int(getattr(metadata, "st_file_attributes", 0)),
        size=len(content),
        sha256="sha256:" + hashlib.sha256(content).hexdigest(),
    )


def acquire_existing_maintenance_lease(
    path: Path | str, *, max_bytes: int = 4096,
) -> ExistingMaintenanceLease:
    """Exclusively lease an exact existing sentinel without creating or writing."""

    if type(max_bytes) is not int or max_bytes <= 0:
        raise MaintenanceLockError("existing maintenance sentinel bound is invalid")
    lock_path = Path(path)
    handle: BinaryIO | None = None
    locked = False
    try:
        before = os.lstat(lock_path)
        if not _valid_existing_sentinel_metadata(before, max_bytes):
            raise MaintenanceLockError("existing maintenance sentinel is invalid")
        handle = lock_path.open("rb", buffering=0)
        opened = os.fstat(handle.fileno())
        if (int(before.st_dev), int(before.st_ino)) != (
            int(opened.st_dev), int(opened.st_ino)
        ):
            raise MaintenanceLockError("existing maintenance sentinel identity changed")
        _lock_nonblocking(handle)
        locked = True
        proof = _sentinel_proof(lock_path, os.fstat(handle.fileno()), handle, max_bytes)
        return ExistingMaintenanceLease(lock_path, handle, proof, max_bytes)
    except FileNotFoundError as exc:
        raise MaintenanceLockError("existing maintenance sentinel is absent") from exc
    except BaseException:
        if handle is not None:
            if locked:
                _unlock(handle)
            handle.close()
        raise


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
    "AUTHORITY_UPDATE_LOCK_FILENAME",
    "AUTHORITY_BLOCK_MARKER_CONTENT",
    "AUTHORITY_BLOCK_MARKER_FILENAME",
    "MAINTENANCE_LOCK_FILENAME",
    "ExistingMaintenanceLease",
    "MaintenanceLease",
    "MaintenanceLeaseBusy",
    "MaintenanceLockError",
    "MaintenanceLockProbe",
    "MaintenanceSentinelProof",
    "acquire_existing_maintenance_lease",
    "acquire_authority_update_lease",
    "authority_block_marker_path",
    "authority_block_marker_valid",
    "acquire_maintenance_lease",
    "authority_update_lock_path",
    "maintenance_lock_path",
    "probe_maintenance_lock",
]
