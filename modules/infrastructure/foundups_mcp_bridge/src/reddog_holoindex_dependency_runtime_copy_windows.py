"""Windows depth-bounded copy engine for Holo dependency-runtime trees."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from .reddog_holoindex_acceptance_guards import AcceptanceGuardError, StoreProof
from .reddog_holoindex_acceptance_model_descriptors import copy_descriptors, file_identity
from .reddog_holoindex_acceptance_windows import (
    WindowsDirectoryLease,
    create_windows_destination_file_lease,
    open_windows_directory_lease,
    open_windows_file_lease_descriptor,
    open_windows_source_file_lease,
    validate_windows_directory_lease,
    validate_windows_file_descriptor,
    validate_windows_file_lease,
)
from .reddog_holoindex_artifact_manifest import (
    ArtifactFileProof,
    ArtifactSnapshot,
    ExpectedArtifactFile,
    ModelCopyLimits,
    build_file_proof,
)
from modules.infrastructure.shared_utilities.runtime_artifact_windows_streams import (
    windows_extended_path,
)


def _fail(code: str) -> None:
    raise AcceptanceGuardError(code)


@dataclass(frozen=True)
class WindowsDependencyTreeCopyResult:
    proofs: list[ArtifactFileProof]
    total_bytes: int
    peak_retained_leases: int


@dataclass
class _WindowsTreeLeases:
    source_root: Path
    destination_root: Path
    snapshot: ArtifactSnapshot
    source: list[WindowsDirectoryLease]
    destination: list[WindowsDirectoryLease]
    relative_parts: list[str]
    created_relative_dirs: set[tuple[str, ...]]
    peak_retained_leases: int = 0

    def observe(self, transient: int = 0) -> None:
        current = len(self.source) + len(self.destination) + transient
        self.peak_retained_leases = max(self.peak_retained_leases, current)

    def close(self) -> None:
        for lease in reversed(self.source):
            lease.close()
        for lease in reversed(self.destination):
            lease.close()
        self.source.clear()
        self.destination.clear()


def _directory_identity(metadata: os.stat_result) -> tuple[int, int]:
    return int(metadata.st_dev), int(metadata.st_ino)


def _open_initial_leases(
    source_root: Path, destination_root: Path, snapshot: ArtifactSnapshot,
    store_proof: StoreProof,
) -> _WindowsTreeLeases:
    source = open_windows_directory_lease(
        source_root, expected_identity=_directory_identity(snapshot.directories[source_root])
    )
    store: WindowsDirectoryLease | None = None
    destination: WindowsDirectoryLease | None = None
    try:
        store = open_windows_directory_lease(
            store_proof.path, expected_identity=(store_proof.device, store_proof.inode)
        )
        validate_windows_directory_lease(store)
        os.mkdir(windows_extended_path(destination_root), 0o700)
        metadata = os.lstat(windows_extended_path(destination_root))
        destination = open_windows_directory_lease(
            destination_root, expected_identity=_directory_identity(metadata)
        )
        validate_windows_directory_lease(store)
        state = _WindowsTreeLeases(
            source_root, destination_root, snapshot, [source], [store, destination],
            [], {()},
        )
        state.observe()
        return state
    except BaseException:
        source.close()
        if destination is not None:
            destination.close()
        if store is not None:
            store.close()
        raise


def _common_prefix(left: list[str], right: tuple[str, ...]) -> int:
    common = 0
    for first, second in zip(left, right):
        if first != second:
            break
        common += 1
    return common


def _close_to_common(state: _WindowsTreeLeases, common: int) -> None:
    while len(state.relative_parts) > common:
        state.source.pop().close()
        state.destination.pop().close()
        state.relative_parts.pop()


def _open_next_directory(state: _WindowsTreeLeases, component: str) -> None:
    source_parent = state.source[-1]
    destination_parent = state.destination[-1]
    source_path = source_parent.path / component
    destination_path = destination_parent.path / component
    expected = state.snapshot.directories.get(source_path)
    if expected is None:
        _fail("MODEL_SOURCE_DIRECTORY_CHANGED")
    validate_windows_directory_lease(source_parent)
    source = open_windows_directory_lease(
        source_path, expected_identity=_directory_identity(expected)
    )
    try:
        destination = _open_destination_directory(
            state, destination_parent, destination_path, component
        )
    except BaseException:
        source.close()
        raise
    state.source.append(source)
    state.destination.append(destination)
    state.relative_parts.append(component)
    state.observe()


def _open_destination_directory(
    state: _WindowsTreeLeases, parent: WindowsDirectoryLease,
    path: Path, component: str,
) -> WindowsDirectoryLease:
    validate_windows_directory_lease(parent)
    relative = tuple((*state.relative_parts, component))
    if relative not in state.created_relative_dirs:
        os.mkdir(windows_extended_path(path), 0o700)
        state.created_relative_dirs.add(relative)
    metadata = os.lstat(windows_extended_path(path))
    lease = open_windows_directory_lease(
        path, expected_identity=_directory_identity(metadata)
    )
    validate_windows_directory_lease(parent)
    return lease


def _move_parents(state: _WindowsTreeLeases, parts: tuple[str, ...]) -> None:
    common = _common_prefix(state.relative_parts, parts)
    _close_to_common(state, common)
    for component in parts[common:]:
        _open_next_directory(state, component)


def _copy_one(
    state: _WindowsTreeLeases, relative: str, source_file: Path,
    expected: os.stat_result, limits: ModelCopyLimits, total: int,
    expected_file: ExpectedArtifactFile,
) -> ArtifactFileProof:
    target = state.destination_root / Path(relative)
    source_lease = open_windows_source_file_lease(
        source_file, state.source[-1], expected_identity=file_identity(expected)
    )
    destination_lease = None
    source_fd = target_fd = -1
    try:
        destination_lease = create_windows_destination_file_lease(
            target, state.destination[-1]
        )
        state.observe(transient=2)
        source_fd = open_windows_file_lease_descriptor(source_lease)
        target_fd = open_windows_file_lease_descriptor(destination_lease)
        copied = copy_descriptors(
            source_fd, target_fd, expected, limits=limits, total_before=total
        )
        _validate_copied_handles(
            source_fd, target_fd, source_file, target, expected,
            source_lease, destination_lease,
        )
        return build_file_proof(relative, copied, expected_file)
    finally:
        if target_fd >= 0:
            os.close(target_fd)
        if source_fd >= 0:
            os.close(source_fd)
        if destination_lease is not None:
            destination_lease.close()
        source_lease.close()


def _validate_copied_handles(
    source_fd: int, target_fd: int, source_file: Path, target: Path,
    expected: os.stat_result, source_lease, destination_lease,
) -> None:
    validate_windows_file_descriptor(
        source_fd, source_file, expected_identity=file_identity(expected)
    )
    validate_windows_file_descriptor(target_fd, target)
    validate_windows_file_lease(source_lease)
    validate_windows_file_lease(destination_lease)


def copy_windows_dependency_tree(
    source_root: Path, destination_root: Path, snapshot: ArtifactSnapshot,
    store_proof: StoreProof, limits: ModelCopyLimits,
    expected_files: dict[str, ExpectedArtifactFile], directories: tuple[str, ...],
) -> WindowsDependencyTreeCopyResult:
    """Copy with retained raw handles bounded by current directory depth."""

    state = _open_initial_leases(source_root, destination_root, snapshot, store_proof)
    proofs: list[ArtifactFileProof] = []
    total = 0
    try:
        for relative, source_file, expected in snapshot.files:
            _move_parents(state, Path(relative).parent.parts)
            proof = _copy_one(
                state, relative, source_file, expected, limits, total,
                expected_files[relative],
            )
            total += proof.size
            proofs.append(proof)
        for relative in directories:
            _move_parents(state, Path(relative).parts)
        return WindowsDependencyTreeCopyResult(
            proofs, total, state.peak_retained_leases
        )
    finally:
        state.close()


__all__ = ["WindowsDependencyTreeCopyResult", "copy_windows_dependency_tree"]
