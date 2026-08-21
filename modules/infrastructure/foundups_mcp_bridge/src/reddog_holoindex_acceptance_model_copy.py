"""Bounded, link-free model snapshot copying for isolated acceptance."""

from __future__ import annotations

import os
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from holo_index.embedding_space import embedding_artifact_digest

from .reddog_holoindex_acceptance_guards import (
    AcceptanceGuardError,
    StoreProof,
    _fail,
    _is_link_or_reparse,
    _normalized,
    _reject_link_components,
    _relative_to,
    verify_store_proof,
)
from .reddog_holoindex_acceptance_model_descriptors import (
    DescriptorCopyProof,
    copy_descriptors,
    copy_one_posix,
    descriptor_artifact_digest,
    file_identity,
)
from .reddog_holoindex_artifact_manifest import (
    ArtifactSnapshot,
    ArtifactFileProof,
    ExpectedArtifactFile,
    ModelCopyLimits,
    ModelCopyProof,
    build_file_proof,
    snapshot_artifact_files,
    validate_expected_manifest,
)
from .reddog_holoindex_acceptance_windows import (
    WindowsDirectoryLease,
    create_windows_destination_file,
    open_windows_directory_lease,
    open_windows_source_file,
    validate_windows_directory_lease,
    validate_windows_file_descriptor,
)


@dataclass
class _WindowsCopySession:
    source_directories: dict[str, WindowsDirectoryLease]
    destination_directories: dict[str, WindowsDirectoryLease]
    source_files: list[tuple[Path, int, tuple[int, int, int, int, int]]]
    destination_files: list[tuple[Path, int]]
    total_bytes: int = 0
    file_proofs: list[ArtifactFileProof] | None = None

    @classmethod
    def create(cls) -> "_WindowsCopySession":
        return cls({}, {}, [], [], 0, [])


def _before_windows_source_component_open(_path: Path) -> None:
    """Trusted no-op seam for deterministic parent-swap tests."""


def _before_windows_destination_component_open(_path: Path) -> None:
    """Trusted no-op seam for deterministic parent-swap tests."""


def _directory_identity(metadata: os.stat_result) -> tuple[int, int]:
    return int(metadata.st_dev), int(metadata.st_ino)


def _lease_key(path: Path) -> str:
    return os.path.normcase(os.path.abspath(os.fspath(path)))


def _source_directory_lease(
    source_root: Path,
    parent: Path,
    snapshot: ArtifactSnapshot,
    leases: dict[str, WindowsDirectoryLease],
) -> WindowsDirectoryLease:
    relative = parent.relative_to(source_root)
    current = source_root
    for component in (Path(), *relative.parts):
        if component != Path():
            current /= component
        key = _lease_key(current)
        if key in leases:
            validate_windows_directory_lease(leases[key])
            continue
        expected = snapshot.directories.get(current)
        if expected is None:
            _fail("MODEL_SOURCE_DIRECTORY_CHANGED")
        try:
            _before_windows_source_component_open(current)
            leases[key] = open_windows_directory_lease(
                current, expected_identity=_directory_identity(expected)
            )
        except (OSError, ValueError) as exc:
            raise AcceptanceGuardError("MODEL_SOURCE_DIRECTORY_CHANGED") from exc
    return leases[_lease_key(parent)]


def _destination_directory_lease(
    store_root: Path,
    parent: Path,
    leases: dict[str, WindowsDirectoryLease],
) -> WindowsDirectoryLease:
    relative = parent.relative_to(store_root)
    current = store_root
    for component in relative.parts:
        current /= component
        key = _lease_key(current)
        if key in leases:
            validate_windows_directory_lease(leases[key])
            continue
        parent_lease = leases[_lease_key(current.parent)]
        validate_windows_directory_lease(parent_lease)
        try:
            current.mkdir(mode=0o700)
            metadata = os.lstat(current)
        except OSError as exc:
            raise AcceptanceGuardError("MODEL_DESTINATION_DIRECTORY_CREATE_FAILED") from exc
        if not stat.S_ISDIR(metadata.st_mode) or _is_link_or_reparse(current, metadata):
            _fail("MODEL_DESTINATION_DIRECTORY_INVALID")
        try:
            _before_windows_destination_component_open(current)
            lease = open_windows_directory_lease(
                current, expected_identity=_directory_identity(metadata)
            )
            validate_windows_directory_lease(parent_lease)
        except (OSError, ValueError) as exc:
            # Retain a handle to our unchanged directory so finalization closes
            # every capability. The directory and any bytes remain preserved.
            try:
                recovered = open_windows_directory_lease(
                    current, expected_identity=_directory_identity(metadata)
                )
            except (OSError, ValueError):
                pass
            else:
                leases[key] = recovered
            raise AcceptanceGuardError("MODEL_DESTINATION_DIRECTORY_CHANGED") from exc
        leases[key] = lease
    return leases[_lease_key(parent)]


def _close_windows_copy(
    source_files: list[tuple[Path, int, tuple[int, int, int, int, int]]],
    destination_files: list[tuple[Path, int]],
    source_directories: dict[str, WindowsDirectoryLease],
    destination_directories: dict[str, WindowsDirectoryLease],
) -> None:
    for _path, descriptor, _identity_proof in source_files:
        try:
            os.close(descriptor)
        except OSError:
            pass
    source_files.clear()
    for _path, descriptor in destination_files:
        try:
            os.close(descriptor)
        except OSError:
            pass
    destination_files.clear()
    for lease in reversed(list(source_directories.values())):
        lease.close()
    source_directories.clear()
    for lease in reversed(list(destination_directories.values())):
        lease.close()
    destination_directories.clear()


def _open_windows_store_lease(
    store_proof: StoreProof, session: _WindowsCopySession
) -> None:
    try:
        lease = open_windows_directory_lease(
            store_proof.path,
            expected_identity=(store_proof.device, store_proof.inode),
        )
    except (OSError, ValueError) as exc:
        raise AcceptanceGuardError("STORE_IDENTITY_CHANGED") from exc
    session.destination_directories[_lease_key(store_proof.path)] = lease


def _open_windows_copy_descriptors(
    source_file: Path,
    target: Path,
    expected: os.stat_result,
    source_parent: WindowsDirectoryLease,
    destination_parent: WindowsDirectoryLease,
    session: _WindowsCopySession,
) -> tuple[int, int]:
    source_fd = -1
    target_fd = -1
    try:
        source_fd = open_windows_source_file(
            source_file, source_parent, expected_identity=file_identity(expected)
        )
        session.source_files.append((source_file, source_fd, file_identity(expected)))
        target_fd = create_windows_destination_file(target, destination_parent)
        session.destination_files.append((target, target_fd))
        return source_fd, target_fd
    except (OSError, ValueError) as exc:
        if source_fd >= 0 and not any(
            descriptor == source_fd
            for _path, descriptor, _proof in session.source_files
        ):
            os.close(source_fd)
        if target_fd >= 0 and not any(
            descriptor == target_fd
            for _path, descriptor in session.destination_files
        ):
            os.close(target_fd)
        raise AcceptanceGuardError("MODEL_WINDOWS_HANDLE_OPEN_FAILED") from exc


def _copy_one_windows_snapshot_file(
    source_root: Path,
    destination_root: Path,
    relative: str,
    source_file: Path,
    expected: os.stat_result,
    snapshot: ArtifactSnapshot,
    store_proof: StoreProof,
    limits: ModelCopyLimits,
    session: _WindowsCopySession,
    expected_file: ExpectedArtifactFile | None,
) -> None:
    source_parent = _source_directory_lease(
        source_root, source_file.parent, snapshot, session.source_directories
    )
    target = destination_root / Path(relative)
    destination_parent = _destination_directory_lease(
        store_proof.path,
        target.parent,
        session.destination_directories,
    )
    source_fd, target_fd = _open_windows_copy_descriptors(
        source_file,
        target,
        expected,
        source_parent,
        destination_parent,
        session,
    )
    descriptor_proof = copy_descriptors(
        source_fd,
        target_fd,
        expected,
        limits=limits,
        total_before=session.total_bytes,
    )
    session.total_bytes += descriptor_proof.copied_bytes
    assert session.file_proofs is not None
    session.file_proofs.append(build_file_proof(relative, descriptor_proof, expected_file))
    validate_windows_file_descriptor(
        source_fd, source_file, expected_identity=file_identity(expected)
    )
    validate_windows_file_descriptor(target_fd, target)
    validate_windows_directory_lease(source_parent)
    validate_windows_directory_lease(destination_parent)


def _validate_windows_copy_session(session: _WindowsCopySession) -> None:
    for path, descriptor, identity_proof in session.source_files:
        validate_windows_file_descriptor(
            descriptor, path, expected_identity=identity_proof
        )
    for path, descriptor in session.destination_files:
        validate_windows_file_descriptor(descriptor, path)
    for lease in session.source_directories.values():
        validate_windows_directory_lease(lease)
    for lease in session.destination_directories.values():
        validate_windows_directory_lease(lease)


def _prove_model_copy(
    source_root: Path,
    destination_root: Path,
    snapshot: ArtifactSnapshot,
    total_bytes: int,
) -> ModelCopyProof:
    source_digest = embedding_artifact_digest(source_root)
    destination_digest = embedding_artifact_digest(destination_root)
    if not source_digest or source_digest != destination_digest:
        _fail("MODEL_DIGEST_MISMATCH")
    return ModelCopyProof(
        source_digest=source_digest,
        destination_digest=destination_digest,
        file_count=len(snapshot.files),
        total_bytes=total_bytes,
        relative_files=tuple(relative for relative, _, _ in snapshot.files),
    )


def _prove_windows_model_copy(
    snapshot: ArtifactSnapshot, session: _WindowsCopySession
) -> ModelCopyProof:
    relative_files = tuple(relative for relative, _, _ in snapshot.files)
    source_digest = descriptor_artifact_digest(
        relative_files, [descriptor for _, descriptor, _ in session.source_files]
    )
    destination_digest = descriptor_artifact_digest(
        relative_files, [descriptor for _, descriptor in session.destination_files]
    )
    if source_digest != destination_digest:
        _fail("MODEL_DIGEST_MISMATCH")
    return ModelCopyProof(
        source_digest=source_digest,
        destination_digest=destination_digest,
        file_count=len(snapshot.files),
        total_bytes=session.total_bytes,
        relative_files=relative_files,
        files=tuple(session.file_proofs or ()),
    )


def _copy_model_snapshot_windows(
    source_root: Path,
    destination_root: Path,
    snapshot: ArtifactSnapshot,
    *,
    store_proof: StoreProof,
    canonical_store: Path | str,
    repo_roots: Iterable[Path | str],
    limits: ModelCopyLimits,
    expected_files: dict[str, ExpectedArtifactFile],
) -> ModelCopyProof:
    session = _WindowsCopySession.create()
    try:
        _source_directory_lease(source_root, source_root, snapshot, session.source_directories)
        _open_windows_store_lease(store_proof, session)
        for relative, source_file, expected in snapshot.files:
            _copy_one_windows_snapshot_file(
                source_root,
                destination_root,
                relative,
                source_file,
                expected,
                snapshot,
                store_proof,
                limits,
                session,
                expected_files.get(relative),
            )
        verify_store_proof(
            store_proof, canonical_store=canonical_store, repo_roots=repo_roots
        )
        proof = _prove_windows_model_copy(snapshot, session)
        _validate_windows_copy_session(session)
        verify_store_proof(
            store_proof, canonical_store=canonical_store, repo_roots=repo_roots
        )
        return proof
    finally:
        _close_windows_copy(
            session.source_files,
            session.destination_files,
            session.source_directories,
            session.destination_directories,
        )


def _copy_model_snapshot_posix(
    source_root: Path,
    destination_root: Path,
    snapshot: ArtifactSnapshot,
    *,
    store_proof: StoreProof,
    canonical_store: Path | str,
    repo_roots: Iterable[Path | str],
    limits: ModelCopyLimits,
    expected_files: dict[str, ExpectedArtifactFile],
) -> ModelCopyProof:
    total = 0
    file_proofs: list[ArtifactFileProof] = []
    for relative, source_file, metadata in snapshot.files:
        verify_store_proof(
            store_proof, canonical_store=canonical_store, repo_roots=repo_roots
        )
        target = destination_root / Path(relative)
        target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        _reject_link_components(target.parent)
        try:
            descriptor_proof = copy_one_posix(
                source_file, target, metadata, limits=limits, total_before=total
            )
            total += descriptor_proof.copied_bytes
            file_proofs.append(
                build_file_proof(relative, descriptor_proof, expected_files.get(relative))
            )
        except OSError as exc:
            raise AcceptanceGuardError("MODEL_COPY_FAILED") from exc
    verify_store_proof(
        store_proof, canonical_store=canonical_store, repo_roots=repo_roots
    )
    proof = _prove_model_copy(source_root, destination_root, snapshot, total)
    return ModelCopyProof(
        source_digest=proof.source_digest,
        destination_digest=proof.destination_digest,
        file_count=proof.file_count,
        total_bytes=proof.total_bytes,
        relative_files=proof.relative_files,
        files=tuple(file_proofs),
    )


def copy_model_snapshot(
    source: Path | str,
    destination: Path | str,
    *,
    store_proof: StoreProof,
    canonical_store: Path | str,
    repo_roots: Iterable[Path | str],
    limits: ModelCopyLimits,
    expected_manifest: tuple[ExpectedArtifactFile, ...] | None = None,
) -> ModelCopyProof:
    """Copy a sorted, bounded snapshot and prove its content identity."""

    verify_store_proof(
        store_proof, canonical_store=canonical_store, repo_roots=repo_roots
    )
    source_root = _normalized(source)
    destination_root = _normalized(destination)
    if not _relative_to(destination_root, store_proof.path) or destination_root == store_proof.path:
        _fail("MODEL_DESTINATION_OUTSIDE_STORE")
    if destination_root.exists():
        _fail("MODEL_DESTINATION_EXISTS")
    snapshot = snapshot_artifact_files(source_root, limits)
    expected_files = validate_expected_manifest(snapshot.files, expected_manifest)
    if os.name == "nt":
        return _copy_model_snapshot_windows(
            source_root,
            destination_root,
            snapshot,
            store_proof=store_proof,
            canonical_store=canonical_store,
            repo_roots=repo_roots,
            limits=limits,
            expected_files=expected_files,
        )
    return _copy_model_snapshot_posix(
        source_root,
        destination_root,
        snapshot,
        store_proof=store_proof,
        canonical_store=canonical_store,
        repo_roots=repo_roots,
        limits=limits,
        expected_files=expected_files,
    )
__all__ = ["ArtifactFileProof", "ExpectedArtifactFile", "ModelCopyLimits", "ModelCopyProof", "copy_model_snapshot"]
