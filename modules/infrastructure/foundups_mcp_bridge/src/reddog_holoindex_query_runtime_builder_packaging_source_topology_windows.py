"""Windows store, root-lease, and topology proof for packaging sources."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import os
from pathlib import Path
import stat
from typing import Iterator

from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    validate_runtime_artifact_path,
    validate_runtime_root_path,
)
from modules.infrastructure.shared_utilities.runtime_artifact_windows_streams import (
    require_unnamed_data_stream_only,
    windows_extended_path,
)

from .reddog_holoindex_acceptance_guards import (
    StoreProof,
    prove_existing_isolated_store,
    verify_store_proof,
)
from .reddog_holoindex_acceptance_windows import (
    WindowsDirectoryLease,
    WindowsFileLease,
    open_windows_directory_lease,
    open_windows_file_lease_descriptor,
    open_windows_source_file_lease,
    validate_windows_directory_lease_exact_path,
    validate_windows_file_descriptor_exact_path,
    validate_windows_file_lease,
)
from .reddog_holoindex_query_replica_orphans import OwnedDirectoryProof
from .reddog_holoindex_query_runtime_builder_packaging_source_contract import (
    BUILDER_PACKAGING_SOURCE_DESCRIPTOR_NAME,
    BUILDER_PACKAGING_SOURCE_INVENTORY_NAME,
    BUILDER_PACKAGING_SOURCE_PUBLICATION_ORPHANS,
    BUILDER_PACKAGING_SOURCE_SITE_PACKAGES_DIRECTORY,
    BUILDER_PACKAGING_SOURCE_WHEEL_DIRECTORY,
    BuilderPackagingSourceLimits,
    absolute_builder_packaging_source_store_path,
)


class BuilderPackagingSourceTopologyError(RuntimeError):
    """Stable path-free source-topology failure."""


def _fail(code: str) -> None:
    raise BuilderPackagingSourceTopologyError(code)


@dataclass(frozen=True)
class PinnedBuilderPackagingSourceGeneration:
    """One exact generation path plus its retained Windows root handle."""

    path: Path
    root_lease: WindowsDirectoryLease | None


@dataclass
class _RetainedSourceTopology:
    root: Path
    directory_leases: list[WindowsDirectoryLease]
    file_leases: list[WindowsFileLease]
    expected_directories: frozenset[str]
    expected_files: frozenset[str]

    def close(self) -> None:
        for lease in reversed(self.file_leases):
            lease.close()
        for lease in reversed(self.directory_leases):
            lease.close()


def _is_link_or_reparse(path: Path, metadata: os.stat_result) -> bool:
    attributes = int(getattr(metadata, "st_file_attributes", 0))
    return bool(
        stat.S_ISLNK(metadata.st_mode)
        or attributes & int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))
        or getattr(path, "is_junction", lambda: False)()
    )


def _validated_store(
    store_root: Path | str, canonical_store: Path | str,
    repo_roots: tuple[Path | str, ...],
) -> StoreProof:
    store_path = absolute_builder_packaging_source_store_path(store_root)
    for repo_root in repo_roots:
        validate_runtime_root_path(store_path, repo_root=repo_root)
    store = prove_existing_isolated_store(
        store_path, canonical_store=canonical_store, repo_roots=repo_roots,
    )
    verify_store_proof(store, canonical_store=canonical_store, repo_roots=repo_roots)
    return store


def _literal_generation_child(
    value: Path | str, store: StoreProof, repo_roots: tuple[Path | str, ...],
) -> tuple[Path, os.stat_result]:
    raw = str(value or "")
    if not raw or "\x00" in raw or not Path(raw).is_absolute():
        _fail("BUILDER_PACKAGING_SOURCE_GENERATION_PATH_INVALID")
    for repo_root in repo_roots:
        validate_runtime_artifact_path(raw, repo_root=repo_root, allowed_root=store.path)
    generation = Path(os.path.abspath(raw))
    if os.path.normcase(str(generation.parent)) != os.path.normcase(str(store.path)):
        _fail("BUILDER_PACKAGING_SOURCE_GENERATION_PATH_INVALID")
    try:
        metadata = os.lstat(generation)
    except OSError:
        _fail("BUILDER_PACKAGING_SOURCE_GENERATION_UNAVAILABLE")
    if not stat.S_ISDIR(metadata.st_mode) or _is_link_or_reparse(generation, metadata):
        _fail("BUILDER_PACKAGING_SOURCE_GENERATION_PATH_INVALID")
    return generation, metadata


@contextmanager
def _pinned_generation_root(
    generation: Path, metadata: os.stat_result,
) -> Iterator[WindowsDirectoryLease | None]:
    lease: WindowsDirectoryLease | None = None
    if os.name == "nt":
        lease = open_windows_directory_lease(
            generation, expected_identity=(int(metadata.st_dev), int(metadata.st_ino)),
        )
        validate_windows_directory_lease_exact_path(lease)
    try:
        yield lease
        if lease is not None:
            validate_windows_directory_lease_exact_path(lease)
    finally:
        if lease is not None:
            lease.close()


@contextmanager
def pinned_builder_packaging_source_generation(
    *, source_store_root: Path | str, generation_root: Path | str,
    canonical_store: Path | str, repo_roots: tuple[Path | str, ...],
    owned_root: OwnedDirectoryProof | None,
) -> Iterator[PinnedBuilderPackagingSourceGeneration]:
    """Hold one exact generation root through all content passes."""

    store = _validated_store(source_store_root, canonical_store, repo_roots)
    generation, metadata = _literal_generation_child(generation_root, store, repo_roots)
    if owned_root is not None and (
        generation != owned_root.path or int(metadata.st_dev) != owned_root.device
        or int(metadata.st_ino) != owned_root.inode
    ):
        _fail("BUILDER_PACKAGING_SOURCE_STAGING_IDENTITY_CHANGED")
    with _pinned_generation_root(generation, metadata) as root_lease:
        yield PinnedBuilderPackagingSourceGeneration(generation, root_lease)
        verify_store_proof(store, canonical_store=canonical_store, repo_roots=repo_roots)


def _exact_file_identity(metadata: os.stat_result) -> tuple[int, int, int, int, int]:
    return (
        int(metadata.st_dev), int(metadata.st_ino), int(metadata.st_size),
        int(metadata.st_mtime_ns), int(getattr(metadata, "st_nlink", 1)),
    )


def _validate_file_lease_exact_path(lease: WindowsFileLease) -> None:
    descriptor = open_windows_file_lease_descriptor(lease)
    try:
        validate_windows_file_descriptor_exact_path(descriptor, lease.path)
    finally:
        os.close(descriptor)


def _relative_name(root: Path, path: Path, limits: BuilderPackagingSourceLimits) -> str:
    try:
        relative = path.relative_to(root).as_posix()
    except ValueError:
        _fail("BUILDER_PACKAGING_SOURCE_TOPOLOGY_INVALID")
    encoded = relative.encode("utf-8")
    if not encoded or len(encoded) > limits.max_path_bytes + 32:
        _fail("BUILDER_PACKAGING_SOURCE_TOPOLOGY_BOUND_EXCEEDED")
    return relative


def _validate_retained_counts(
    *, file_count: int, directory_count: int, path_bytes: int,
    depth: int, limits: BuilderPackagingSourceLimits,
) -> None:
    if (
        file_count > limits.max_files + 3
        or directory_count > limits.max_directories + 3
        or path_bytes > limits.max_total_path_bytes + (4 * limits.max_path_bytes)
        or depth > limits.max_directory_depth + 2
    ):
        _fail("BUILDER_PACKAGING_SOURCE_TOPOLOGY_BOUND_EXCEEDED")


def _open_retained_child(
    *, root: Path, parent: WindowsDirectoryLease, path: Path,
    metadata: os.stat_result, limits: BuilderPackagingSourceLimits,
) -> tuple[str, WindowsDirectoryLease | WindowsFileLease, bool]:
    relative = _relative_name(root, path, limits)
    if _is_link_or_reparse(path, metadata):
        _fail("BUILDER_PACKAGING_SOURCE_TOPOLOGY_INVALID")
    require_unnamed_data_stream_only(path)
    if stat.S_ISDIR(metadata.st_mode):
        lease = open_windows_directory_lease(
            path, expected_identity=(int(metadata.st_dev), int(metadata.st_ino)),
        )
        validate_windows_directory_lease_exact_path(lease)
        return relative, lease, True
    if not stat.S_ISREG(metadata.st_mode) or int(getattr(metadata, "st_nlink", 1)) != 1:
        _fail("BUILDER_PACKAGING_SOURCE_TOPOLOGY_INVALID")
    file_lease = open_windows_source_file_lease(
        path, parent, expected_identity=_exact_file_identity(metadata),
    )
    _validate_file_lease_exact_path(file_lease)
    return relative, file_lease, False


def _acquire_retained_topology(
    pinned: PinnedBuilderPackagingSourceGeneration,
    limits: BuilderPackagingSourceLimits,
) -> _RetainedSourceTopology:
    if os.name != "nt" or pinned.root_lease is None:
        _fail("BUILDER_PACKAGING_SOURCE_WINDOWS_REQUIRED")
    directories: list[WindowsDirectoryLease] = []
    files: list[WindowsFileLease] = []
    directory_names: set[str] = set()
    file_names: set[str] = set()
    pending = [(pinned.path, pinned.root_lease, 0)]
    path_bytes = 0
    try:
        while pending:
            current, parent_lease, depth = pending.pop()
            entries = sorted(os.scandir(windows_extended_path(current)), key=lambda item: item.name)
            for entry in entries:
                path = current / entry.name
                metadata = os.lstat(windows_extended_path(path))
                relative, lease, is_directory = _open_retained_child(
                    root=pinned.path, parent=parent_lease, path=path,
                    metadata=metadata, limits=limits,
                )
                path_bytes += len(relative.encode("utf-8"))
                if is_directory:
                    directories.append(lease)
                    directory_names.add(relative)
                    pending.append((path, lease, depth + 1))
                else:
                    files.append(lease)
                    file_names.add(relative)
                _validate_retained_counts(
                    file_count=len(files), directory_count=len(directories),
                    path_bytes=path_bytes, depth=depth, limits=limits,
                )
        return _RetainedSourceTopology(
            pinned.path, directories, files,
            frozenset(directory_names), frozenset(file_names),
        )
    except BaseException:
        _RetainedSourceTopology(
            pinned.path, directories, files, frozenset(), frozenset(),
        ).close()
        raise


def _collect_live_topology(
    root: Path, limits: BuilderPackagingSourceLimits,
) -> tuple[frozenset[str], frozenset[str]]:
    directories: set[str] = set()
    files: set[str] = set()
    pending = [(root, 0)]
    path_bytes = 0
    while pending:
        current, depth = pending.pop()
        for entry in os.scandir(windows_extended_path(current)):
            path = current / entry.name
            metadata = os.lstat(windows_extended_path(path))
            relative = _relative_name(root, path, limits)
            if _is_link_or_reparse(path, metadata):
                _fail("BUILDER_PACKAGING_SOURCE_TOPOLOGY_INVALID")
            require_unnamed_data_stream_only(path)
            path_bytes += len(relative.encode("utf-8"))
            if stat.S_ISDIR(metadata.st_mode):
                directories.add(relative)
                pending.append((path, depth + 1))
            elif stat.S_ISREG(metadata.st_mode) and int(getattr(metadata, "st_nlink", 1)) == 1:
                files.add(relative)
            else:
                _fail("BUILDER_PACKAGING_SOURCE_TOPOLOGY_INVALID")
            _validate_retained_counts(
                file_count=len(files), directory_count=len(directories),
                path_bytes=path_bytes, depth=depth, limits=limits,
            )
    return frozenset(directories), frozenset(files)


def _terminal_reproof(
    topology: _RetainedSourceTopology, limits: BuilderPackagingSourceLimits,
) -> None:
    for lease in topology.file_leases:
        validate_windows_file_lease(lease)
        _validate_file_lease_exact_path(lease)
    for lease in topology.directory_leases:
        validate_windows_directory_lease_exact_path(lease)
    observed = _collect_live_topology(topology.root, limits)
    if observed != (topology.expected_directories, topology.expected_files):
        _fail("BUILDER_PACKAGING_SOURCE_VERIFICATION_CHANGED")


@contextmanager
def retained_builder_packaging_source_topology(
    pinned: PinnedBuilderPackagingSourceGeneration,
    limits: BuilderPackagingSourceLimits,
) -> Iterator[None]:
    """Pin every admitted child through the terminal topology proof boundary."""

    topology = _acquire_retained_topology(pinned, limits)
    try:
        yield
        _terminal_reproof(topology, limits)
    finally:
        topology.close()


def verify_builder_packaging_source_direct_topology(root: Path) -> None:
    expected = {
        BUILDER_PACKAGING_SOURCE_DESCRIPTOR_NAME,
        BUILDER_PACKAGING_SOURCE_INVENTORY_NAME,
        BUILDER_PACKAGING_SOURCE_WHEEL_DIRECTORY,
        BUILDER_PACKAGING_SOURCE_SITE_PACKAGES_DIRECTORY,
        BUILDER_PACKAGING_SOURCE_PUBLICATION_ORPHANS,
    }
    require_unnamed_data_stream_only(root)
    try:
        entries = tuple(os.scandir(root))
    except OSError:
        _fail("BUILDER_PACKAGING_SOURCE_GENERATION_UNAVAILABLE")
    if {entry.name for entry in entries} != expected:
        _fail("BUILDER_PACKAGING_SOURCE_TOPOLOGY_INVALID")
    for entry in entries:
        _validate_topology_entry(Path(entry.path), entry.name)
    orphan = root / BUILDER_PACKAGING_SOURCE_PUBLICATION_ORPHANS
    if tuple(os.scandir(orphan)):
        _fail("BUILDER_PACKAGING_SOURCE_TOPOLOGY_INVALID")


def verify_builder_packaging_source_regular_file(path: Path) -> None:
    _validate_topology_entry(path, path.name)


def _validate_topology_entry(path: Path, name: str) -> None:
    metadata = os.lstat(path)
    directory_names = {
        BUILDER_PACKAGING_SOURCE_WHEEL_DIRECTORY,
        BUILDER_PACKAGING_SOURCE_SITE_PACKAGES_DIRECTORY,
        BUILDER_PACKAGING_SOURCE_PUBLICATION_ORPHANS,
    }
    wanted_directory = name in directory_names
    if (
        _is_link_or_reparse(path, metadata)
        or stat.S_ISDIR(metadata.st_mode) is not wanted_directory
        or (not wanted_directory and not stat.S_ISREG(metadata.st_mode))
        or (stat.S_ISREG(metadata.st_mode) and int(getattr(metadata, "st_nlink", 1)) != 1)
    ):
        _fail("BUILDER_PACKAGING_SOURCE_TOPOLOGY_INVALID")
    require_unnamed_data_stream_only(path)


__all__ = [
    "BuilderPackagingSourceTopologyError",
    "PinnedBuilderPackagingSourceGeneration",
    "pinned_builder_packaging_source_generation",
    "retained_builder_packaging_source_topology",
    "verify_builder_packaging_source_direct_topology",
    "verify_builder_packaging_source_regular_file",
]
