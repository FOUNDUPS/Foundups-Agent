"""O(depth) Windows writer for exact in-memory packaging-wheel members."""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path
import stat

from modules.infrastructure.shared_utilities.runtime_artifact_windows_streams import (
    require_unnamed_data_stream_only,
    windows_extended_path,
)

from .reddog_holoindex_acceptance_windows import (
    WindowsDirectoryLease,
    create_windows_destination_file_lease,
    open_windows_directory_lease,
    open_windows_file_lease_descriptor,
    validate_windows_directory_lease,
    validate_windows_directory_lease_exact_path,
    validate_windows_file_descriptor_exact_path,
    validate_windows_file_lease,
)
from .reddog_holoindex_query_replica_orphans import OwnedDirectoryProof
from .reddog_holoindex_query_runtime_builder_packaging_source_contract import (
    BUILDER_PACKAGING_SOURCE_PUBLICATION_ORPHANS,
    BUILDER_PACKAGING_SOURCE_SITE_PACKAGES_DIRECTORY,
    BUILDER_PACKAGING_SOURCE_WHEEL_DIRECTORY,
    BuilderPackagingSourceLimits,
)
from .reddog_holoindex_strict_wheel_archive import StrictWheelMember


class BuilderPackagingSourceWriterError(RuntimeError):
    """Stable destination-writer error."""


def _fail(code: str) -> None:
    raise BuilderPackagingSourceWriterError(code)


@dataclass(frozen=True)
class BuilderPackagingSourceWriteResult:
    peak_retained_leases: int
    written_member_count: int
    written_member_bytes: int


@dataclass
class _DestinationState:
    staging: Path
    root: WindowsDirectoryLease
    site: WindowsDirectoryLease
    current: list[WindowsDirectoryLease]
    parts: list[str]
    peak: int = 0

    def observe(self, transient: int = 0) -> None:
        self.peak = max(self.peak, 2 + len(self.current) + transient)

    def close(self) -> None:
        for lease in reversed(self.current):
            lease.close()
        self.site.close()
        self.root.close()


def write_builder_packaging_source_windows(
    *, staging_root: Path, owned_root: OwnedDirectoryProof,
    wheel_filename: str, wheel_bytes: bytes,
    members: tuple[StrictWheelMember, ...],
    directories: tuple[str, ...], limits: BuilderPackagingSourceLimits,
) -> BuilderPackagingSourceWriteResult:
    """Write exact wheel and member bytes without pathname-source reopening."""

    if os.name != "nt":
        _fail("BUILDER_PACKAGING_SOURCE_WINDOWS_REQUIRED")
    limits.validate()
    _require_owned_root(staging_root, owned_root)
    state = _open_destination_state(staging_root, owned_root)
    try:
        wheel_parent = _create_child_directory(state.root, staging_root, BUILDER_PACKAGING_SOURCE_WHEEL_DIRECTORY)
        try:
            _write_file(wheel_parent, wheel_parent.path / wheel_filename, wheel_bytes)
            state.observe(transient=1)
        finally:
            wheel_parent.close()
        orphan = _create_child_directory(state.root, staging_root, BUILDER_PACKAGING_SOURCE_PUBLICATION_ORPHANS)
        orphan.close()
        _create_member_directories(state, directories)
        for member in members:
            _write_member(state, member)
        _reprove_state(state)
        return BuilderPackagingSourceWriteResult(
            peak_retained_leases=state.peak,
            written_member_count=len(members),
            written_member_bytes=sum(len(member.payload) for member in members),
        )
    except BuilderPackagingSourceWriterError:
        raise
    except Exception as exc:
        raise BuilderPackagingSourceWriterError(
            "BUILDER_PACKAGING_SOURCE_WRITE_UNAVAILABLE"
        ) from exc
    finally:
        state.close()


def _require_owned_root(path: Path, proof: OwnedDirectoryProof) -> None:
    try:
        metadata = os.lstat(windows_extended_path(path))
    except OSError as exc:
        raise BuilderPackagingSourceWriterError(
            "BUILDER_PACKAGING_SOURCE_STAGING_INVALID"
        ) from exc
    if (
        path != proof.path or int(metadata.st_dev) != proof.device
        or int(metadata.st_ino) != proof.inode or not stat.S_ISDIR(metadata.st_mode)
    ):
        _fail("BUILDER_PACKAGING_SOURCE_STAGING_INVALID")


def _open_destination_state(
    staging: Path, proof: OwnedDirectoryProof,
) -> _DestinationState:
    root = open_windows_directory_lease(
        staging, expected_identity=(proof.device, proof.inode),
    )
    site: WindowsDirectoryLease | None = None
    try:
        validate_windows_directory_lease_exact_path(root)
        require_unnamed_data_stream_only(staging)
        site = _create_child_directory(
            root, staging, BUILDER_PACKAGING_SOURCE_SITE_PACKAGES_DIRECTORY,
        )
        state = _DestinationState(staging, root, site, [], [])
        state.observe()
        return state
    except BaseException:
        if site is not None:
            site.close()
        root.close()
        raise


def _create_child_directory(
    parent: WindowsDirectoryLease, parent_path: Path, component: str,
) -> WindowsDirectoryLease:
    child = parent_path / component
    validate_windows_directory_lease(parent)
    os.mkdir(windows_extended_path(child), 0o700)
    metadata = os.lstat(windows_extended_path(child))
    if not stat.S_ISDIR(metadata.st_mode):
        _fail("BUILDER_PACKAGING_SOURCE_DIRECTORY_INVALID")
    lease = open_windows_directory_lease(
        child, expected_identity=(int(metadata.st_dev), int(metadata.st_ino)),
    )
    validate_windows_directory_lease(parent)
    validate_windows_directory_lease_exact_path(lease)
    require_unnamed_data_stream_only(child)
    return lease


def _create_member_directories(
    state: _DestinationState, directories: tuple[str, ...],
) -> None:
    created: set[tuple[str, ...]] = {()}
    for relative in directories:
        parts = tuple(Path(relative).parts)
        for depth in range(1, len(parts) + 1):
            prefix = parts[:depth]
            if prefix in created:
                continue
            _move_to_parent(state, prefix[:-1])
            parent = state.current[-1] if state.current else state.site
            lease = _create_child_directory(parent, parent.path, prefix[-1])
            lease.close()
            created.add(prefix)
    _move_to_parent(state, ())


def _common_prefix(left: list[str], right: tuple[str, ...]) -> int:
    count = 0
    for first, second in zip(left, right):
        if first != second:
            break
        count += 1
    return count


def _move_to_parent(state: _DestinationState, parts: tuple[str, ...]) -> None:
    common = _common_prefix(state.parts, parts)
    while len(state.parts) > common:
        state.current.pop().close()
        state.parts.pop()
    while len(state.parts) < len(parts):
        parent = state.current[-1] if state.current else state.site
        path = parent.path / parts[len(state.parts)]
        metadata = os.lstat(windows_extended_path(path))
        lease = open_windows_directory_lease(
            path, expected_identity=(int(metadata.st_dev), int(metadata.st_ino)),
        )
        validate_windows_directory_lease_exact_path(lease)
        state.current.append(lease)
        state.parts.append(path.name)
        state.observe()


def _write_member(state: _DestinationState, member: StrictWheelMember) -> None:
    parts = tuple(Path(member.path).parts)
    _move_to_parent(state, parts[:-1])
    parent = state.current[-1] if state.current else state.site
    _write_file(parent, parent.path / parts[-1], member.payload)
    state.observe(transient=1)


def _write_file(
    parent: WindowsDirectoryLease, path: Path, payload: bytes,
) -> None:
    lease = create_windows_destination_file_lease(path, parent)
    descriptor = -1
    try:
        descriptor = open_windows_file_lease_descriptor(lease)
        _write_all(descriptor, payload)
        os.fsync(descriptor)
        os.lseek(descriptor, 0, os.SEEK_SET)
        observed = _read_all(descriptor, len(payload))
        if observed != payload or hashlib.sha256(observed).digest() != hashlib.sha256(payload).digest():
            _fail("BUILDER_PACKAGING_SOURCE_WRITE_MISMATCH")
        validate_windows_file_descriptor_exact_path(descriptor, path)
        validate_windows_file_lease(lease)
        require_unnamed_data_stream_only(path)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        lease.close()


def _write_all(descriptor: int, payload: bytes) -> None:
    offset = 0
    while offset < len(payload):
        written = os.write(descriptor, payload[offset:])
        if written <= 0:
            _fail("BUILDER_PACKAGING_SOURCE_SHORT_WRITE")
        offset += written


def _read_all(descriptor: int, expected: int) -> bytes:
    chunks: list[bytes] = []
    total = 0
    while total < expected + 1:
        chunk = os.read(descriptor, min(64 * 1024, expected + 1 - total))
        if not chunk:
            break
        chunks.append(chunk)
        total += len(chunk)
    return b"".join(chunks)


def _reprove_state(state: _DestinationState) -> None:
    validate_windows_directory_lease_exact_path(state.root)
    validate_windows_directory_lease_exact_path(state.site)
    for lease in state.current:
        validate_windows_directory_lease_exact_path(lease)
    require_unnamed_data_stream_only(state.staging)


__all__ = [
    "BuilderPackagingSourceWriteResult", "BuilderPackagingSourceWriterError",
    "write_builder_packaging_source_windows",
]
