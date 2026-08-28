"""Handle-bounded copying for inert Holo dependency-runtime generations."""

from __future__ import annotations

import os
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .reddog_holoindex_acceptance_guards import (
    AcceptanceGuardError,
    StoreProof,
    verify_store_proof,
)
from .reddog_holoindex_acceptance_model_descriptors import copy_one_posix
from .reddog_holoindex_artifact_manifest import (
    ArtifactFileProof,
    ArtifactSnapshot,
    ExpectedArtifactFile,
    ModelCopyLimits,
    ModelCopyProof,
    build_file_proof,
    snapshot_artifact_files,
)
from modules.infrastructure.shared_utilities.runtime_artifact_confined_byte_reader import (
    confined_file_identity,
    secure_digest_confined_file_impl,
)
from modules.infrastructure.shared_utilities.runtime_artifact_windows_streams import (
    require_unnamed_data_stream_only,
)
from .reddog_holoindex_dependency_runtime_contract import (
    DependencyRuntimeLimits,
    INVENTORY_SCHEMA_VERSION,
    canonical_json_bytes,
    canonical_relative_path,
    dependency_tree_digest,
)
from .reddog_holoindex_dependency_runtime_copy_windows import (
    copy_windows_dependency_tree,
)


_PLACEHOLDER_DIGEST = "sha256:" + ("0" * 64)


def _fail(code: str) -> None:
    raise AcceptanceGuardError(code)


def _absolute(path: Path | str) -> Path:
    return Path(os.path.abspath(os.fspath(path)))


def _is_descendant(path: Path, root: Path) -> bool:
    try:
        return os.path.commonpath((path, root)) == os.path.commonpath((root, root))
    except ValueError:
        return False


def _metadata_identity(metadata: os.stat_result) -> tuple[int, ...]:
    return (
        int(metadata.st_dev), int(metadata.st_ino), int(metadata.st_mode),
        int(getattr(metadata, "st_nlink", 0)), int(metadata.st_size),
        int(metadata.st_mtime_ns), int(metadata.st_ctime_ns),
        int(getattr(metadata, "st_file_attributes", 0)),
    )


def _snapshot_identity(snapshot: ArtifactSnapshot, root: Path) -> tuple[tuple[object, ...], ...]:
    directories = tuple(
        ("directory", path.relative_to(root).as_posix(), _metadata_identity(metadata))
        for path, metadata in sorted(
            snapshot.directories.items(), key=lambda item: item[0].as_posix().casefold()
        )
    )
    files = tuple(
        ("file", relative, _metadata_identity(metadata))
        for relative, _path, metadata in snapshot.files
    )
    return directories + files


def _validated_relatives(
    snapshot: ArtifactSnapshot, limits: DependencyRuntimeLimits,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    relatives = tuple(canonical_relative_path(row[0]) for row in snapshot.files)
    keys = tuple(value.casefold() for value in relatives)
    if keys != tuple(sorted(keys)) or len(keys) != len(set(keys)):
        _fail("DEPENDENCY_RUNTIME_SOURCE_PATH_ALIAS")
    root = min(snapshot.directories, key=lambda path: len(path.parts))
    directory_relatives = tuple(sorted(
        (
            canonical_relative_path(path.relative_to(root).as_posix())
            for path in snapshot.directories if path != root
        ),
        key=str.casefold,
    ))
    all_paths = relatives + directory_relatives
    path_bytes = tuple(len(value.encode("utf-8")) for value in all_paths)
    if len(snapshot.directories) > limits.max_directories:
        _fail("DEPENDENCY_RUNTIME_SOURCE_DIRECTORY_BOUND")
    if any(len(Path(value).parts) > limits.max_directory_depth for value in all_paths):
        _fail("DEPENDENCY_RUNTIME_SOURCE_DEPTH_BOUND")
    if any(size > limits.max_path_bytes for size in path_bytes):
        _fail("DEPENDENCY_RUNTIME_SOURCE_PATH_BOUND")
    if sum(path_bytes) > limits.max_total_path_bytes:
        _fail("DEPENDENCY_RUNTIME_SOURCE_TOTAL_PATH_BOUND")
    directory_keys = tuple(value.casefold() for value in directory_relatives)
    if len(directory_keys) != len(set(directory_keys)) or set(directory_keys) & set(keys):
        _fail("DEPENDENCY_RUNTIME_SOURCE_PATH_ALIAS")
    return relatives, directory_relatives


@dataclass(frozen=True)
class DependencyRuntimeSourcePlan:
    source_root: Path
    generation_id: str
    file_count: int
    total_bytes: int
    directories: tuple[str, ...]
    files: tuple[ExpectedArtifactFile, ...]
    included_roots: tuple[str, ...] = ()
    excluded_roots: tuple[str, ...] = ()


def _projection_roots(values: Iterable[str]) -> tuple[str, ...]:
    roots = tuple(canonical_relative_path(value) for value in values)
    keys = tuple(value.casefold() for value in roots)
    if keys != tuple(sorted(keys)) or len(keys) != len(set(keys)):
        _fail("DEPENDENCY_RUNTIME_EXCLUSION_INVALID")
    for index, root in enumerate(roots):
        prefix = root.casefold() + "/"
        if any(other.casefold().startswith(prefix) for other in roots[index + 1 :]):
            _fail("DEPENDENCY_RUNTIME_EXCLUSION_INVALID")
    return roots


def _project_snapshot(
    snapshot: ArtifactSnapshot, source_root: Path,
    included_roots: tuple[str, ...],
    excluded_roots: tuple[str, ...],
) -> ArtifactSnapshot:
    if not included_roots and not excluded_roots:
        return snapshot
    included = tuple(value.casefold() for value in included_roots)
    excluded = tuple(value.casefold() for value in excluded_roots)

    def admitted(relative: str) -> bool:
        key = relative.casefold()
        selected = not included or any(
            key == root or key.startswith(root + "/") for root in included
        )
        omitted = any(key == root or key.startswith(root + "/") for root in excluded)
        return selected and not omitted

    def admitted_directory(relative: str) -> bool:
        key = relative.casefold()
        return admitted(relative) or any(root.startswith(key + "/") for root in included)

    present = {
        path.relative_to(source_root).as_posix().casefold()
        for path in snapshot.directories if path != source_root
    }
    present.update(row[0].casefold() for row in snapshot.files)
    if any(root not in present for root in included):
        _fail("DEPENDENCY_RUNTIME_PROJECTION_ROOT_MISSING")
    if included and any(
        not any(root == admitted_root or root.startswith(admitted_root + "/")
                for admitted_root in included)
        for root in excluded
    ):
        _fail("DEPENDENCY_RUNTIME_EXCLUSION_INVALID")
    directories = {
        path: metadata for path, metadata in snapshot.directories.items()
        if path == source_root
        or admitted_directory(path.relative_to(source_root).as_posix())
    }
    files = [row for row in snapshot.files if admitted(row[0])]
    if not files:
        _fail("DEPENDENCY_RUNTIME_PROJECTED_SOURCE_EMPTY")
    return ArtifactSnapshot(files=files, directories=directories)


def _preflight_inventory_bound(
    snapshot: ArtifactSnapshot, relatives: tuple[str, ...],
    directories: tuple[str, ...], max_bytes: int,
) -> None:
    rows = [
        {"path": relative, "size": int(item[2].st_size),
         "sha256": _PLACEHOLDER_DIGEST,
         "role": "dependency_payload"}
        for relative, item in zip(relatives, snapshot.files)
    ]
    projected = canonical_json_bytes(
        {"schema_version": INVENTORY_SCHEMA_VERSION,
         "directories": list(directories), "files": rows}
    )
    if len(projected) > max_bytes:
        _fail("DEPENDENCY_RUNTIME_INVENTORY_SIZE_BOUND")


def _source_plan(
    source_root: Path, snapshot: ArtifactSnapshot, limits: ModelCopyLimits,
    directories: tuple[str, ...], included_roots: tuple[str, ...],
    excluded_roots: tuple[str, ...],
) -> DependencyRuntimeSourcePlan:
    files: list[ExpectedArtifactFile] = []
    for directory in snapshot.directories:
        require_unnamed_data_stream_only(directory)
    for relative, path, metadata in snapshot.files:
        require_unnamed_data_stream_only(path)
        proof = secure_digest_confined_file_impl(
            path, allowed_root=source_root,
            expected_identity=confined_file_identity(metadata),
            max_bytes=limits.max_file_bytes,
        )
        require_unnamed_data_stream_only(path)
        files.append(ExpectedArtifactFile(relative, proof.size, proof.digest))
    for directory in snapshot.directories:
        require_unnamed_data_stream_only(directory)
    after = _project_snapshot(
        snapshot_artifact_files(source_root, limits), source_root,
        included_roots, excluded_roots,
    )
    if _snapshot_identity(snapshot, source_root) != _snapshot_identity(after, source_root):
        _fail("DEPENDENCY_RUNTIME_SOURCE_CHANGED")
    rows = [
        {"path": item.relative_path, "size": item.size, "sha256": item.sha256}
        for item in files
    ]
    return DependencyRuntimeSourcePlan(
        source_root=source_root,
        generation_id=dependency_tree_digest(directories, rows),
        file_count=len(files),
        total_bytes=sum(item.size for item in files),
        directories=directories,
        files=tuple(files),
        included_roots=included_roots,
        excluded_roots=excluded_roots,
    )


def plan_dependency_runtime_snapshot(
    source: Path | str, *, limits: DependencyRuntimeLimits,
    included_roots: Iterable[str] = (),
    excluded_roots: Iterable[str] = (),
) -> DependencyRuntimeSourcePlan:
    """Hash an exact source tree once so an existing generation can be reused."""

    limits.validate()
    source_root = _absolute(source)
    copy_limits = ModelCopyLimits(
        limits.max_files, limits.max_file_bytes, limits.max_total_bytes
    )
    inclusions = _projection_roots(included_roots)
    exclusions = _projection_roots(excluded_roots)
    snapshot = _project_snapshot(
        snapshot_artifact_files(source_root, copy_limits), source_root,
        inclusions, exclusions,
    )
    relatives, directories = _validated_relatives(snapshot, limits)
    _preflight_inventory_bound(
        snapshot, relatives, directories, limits.max_inventory_bytes
    )
    return _source_plan(
        source_root, snapshot, copy_limits, directories, inclusions, exclusions
    )


def _proof_digest(
    proofs: list[ArtifactFileProof], attribute: str,
    directories: tuple[str, ...],
) -> str:
    rows = [
        {"path": proof.relative_path, "size": proof.size,
         "sha256": getattr(proof, attribute)}
        for proof in proofs
    ]
    return dependency_tree_digest(directories, rows)


def _copy_proof(
    snapshot: ArtifactSnapshot, proofs: list[ArtifactFileProof], total: int,
    directories: tuple[str, ...],
) -> ModelCopyProof:
    source_digest = _proof_digest(proofs, "source_after_sha256", directories)
    destination_digest = _proof_digest(proofs, "destination_sha256", directories)
    if not source_digest or source_digest != destination_digest:
        _fail("MODEL_DIGEST_MISMATCH")
    return ModelCopyProof(
        source_digest=source_digest,
        destination_digest=destination_digest,
        file_count=len(snapshot.files),
        total_bytes=total,
        relative_files=tuple(row[0] for row in snapshot.files),
        files=tuple(proofs),
    )


def _copy_posix(
    source_root: Path, destination_root: Path, snapshot: ArtifactSnapshot,
    limits: ModelCopyLimits, expected_files: dict[str, ExpectedArtifactFile],
    directories: tuple[str, ...],
) -> tuple[list[ArtifactFileProof], int]:
    destination_root.mkdir(mode=0o700)
    proofs: list[ArtifactFileProof] = []
    total = 0
    for relative, source_file, expected in snapshot.files:
        target = destination_root / Path(relative)
        target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        copied = copy_one_posix(
            source_file, target, expected, limits=limits, total_before=total
        )
        total += copied.copied_bytes
        proofs.append(build_file_proof(relative, copied, expected_files[relative]))
    for relative in directories:
        (destination_root / Path(relative)).mkdir(mode=0o700, parents=True, exist_ok=True)
    return proofs, total


def _validate_final_shape(
    source_root: Path, destination_root: Path, before: ArtifactSnapshot,
    limits: ModelCopyLimits, proofs: list[ArtifactFileProof],
    directories: tuple[str, ...], included_roots: tuple[str, ...],
    excluded_roots: tuple[str, ...],
) -> None:
    source_after = _project_snapshot(
        snapshot_artifact_files(source_root, limits), source_root,
        included_roots, excluded_roots,
    )
    if _snapshot_identity(before, source_root) != _snapshot_identity(source_after, source_root):
        _fail("DEPENDENCY_RUNTIME_SOURCE_CHANGED")
    destination = snapshot_artifact_files(destination_root, limits)
    actual = tuple((row[0], int(row[2].st_size)) for row in destination.files)
    expected = tuple((proof.relative_path, proof.size) for proof in proofs)
    if actual != expected:
        _fail("DEPENDENCY_RUNTIME_DESTINATION_CHANGED")
    actual_directories = tuple(sorted(
        (
            path.relative_to(destination_root).as_posix()
            for path in destination.directories if path != destination_root
        ),
        key=str.casefold,
    ))
    if actual_directories != directories:
        _fail("DEPENDENCY_RUNTIME_DESTINATION_CHANGED")


def _validated_copy_plan(
    source_root: Path, snapshot: ArtifactSnapshot, copy_limits: ModelCopyLimits,
    limits: DependencyRuntimeLimits, expected_plan: DependencyRuntimeSourcePlan | None,
    included_roots: tuple[str, ...],
    excluded_roots: tuple[str, ...],
) -> tuple[DependencyRuntimeSourcePlan, tuple[str, ...]]:
    relatives, directories = _validated_relatives(snapshot, limits)
    _preflight_inventory_bound(
        snapshot, relatives, directories, limits.max_inventory_bytes
    )
    plan = expected_plan or _source_plan(
        source_root, snapshot, copy_limits, directories,
        included_roots, excluded_roots,
    )
    actual_shape = tuple((row[0], int(row[2].st_size)) for row in snapshot.files)
    planned_shape = tuple((row.relative_path, row.size) for row in plan.files)
    if (
        plan.source_root != source_root
        or actual_shape != planned_shape
        or directories != plan.directories
        or included_roots != plan.included_roots
        or excluded_roots != plan.excluded_roots
    ):
        _fail("DEPENDENCY_RUNTIME_SOURCE_PLAN_MISMATCH")
    return plan, directories


def _copy_platform_tree(
    source_root: Path, destination_root: Path, snapshot: ArtifactSnapshot,
    store_proof: StoreProof, copy_limits: ModelCopyLimits,
    plan: DependencyRuntimeSourcePlan, directories: tuple[str, ...],
) -> tuple[list[ArtifactFileProof], int, int]:
    expected_files = {row.relative_path: row for row in plan.files}
    if os.name == "nt":
        result = copy_windows_dependency_tree(
            source_root, destination_root, snapshot, store_proof, copy_limits,
            expected_files, directories,
        )
        return result.proofs, result.total_bytes, result.peak_retained_leases
    proofs, total = _copy_posix(
        source_root, destination_root, snapshot, copy_limits, expected_files,
        directories,
    )
    return proofs, total, 0


def _copy_dependency_snapshot(
    source: Path | str, destination: Path | str, *, store_proof: StoreProof,
    canonical_store: Path | str, repo_roots: Iterable[Path | str],
    limits: DependencyRuntimeLimits,
    expected_plan: DependencyRuntimeSourcePlan | None,
    included_roots: Iterable[str] = (),
    excluded_roots: Iterable[str] = (),
) -> tuple[ModelCopyProof, int]:
    verify_store_proof(
        store_proof, canonical_store=canonical_store, repo_roots=repo_roots
    )
    source_root, destination_root = _absolute(source), _absolute(destination)
    if not _is_descendant(destination_root, store_proof.path) or destination_root.exists():
        _fail("MODEL_DESTINATION_OUTSIDE_STORE")
    copy_limits = ModelCopyLimits(
        limits.max_files, limits.max_file_bytes, limits.max_total_bytes
    )
    inclusions = _projection_roots(included_roots)
    exclusions = _projection_roots(excluded_roots)
    snapshot = _project_snapshot(
        snapshot_artifact_files(source_root, copy_limits), source_root,
        inclusions, exclusions,
    )
    plan, directories = _validated_copy_plan(
        source_root, snapshot, copy_limits, limits, expected_plan,
        inclusions, exclusions,
    )
    proofs, total, peak = _copy_platform_tree(
        source_root, destination_root, snapshot, store_proof, copy_limits,
        plan, directories,
    )
    _validate_final_shape(
        source_root, destination_root, snapshot, copy_limits, proofs, directories,
        inclusions, exclusions,
    )
    verify_store_proof(
        store_proof, canonical_store=canonical_store, repo_roots=repo_roots
    )
    proof = _copy_proof(snapshot, proofs, total, directories)
    if proof.destination_digest != plan.generation_id:
        _fail("DEPENDENCY_RUNTIME_SOURCE_PLAN_MISMATCH")
    return proof, peak


def copy_dependency_runtime_snapshot(
    source: Path | str, destination: Path | str, *, store_proof: StoreProof,
    canonical_store: Path | str, repo_roots: Iterable[Path | str],
    limits: DependencyRuntimeLimits,
    expected_plan: DependencyRuntimeSourcePlan | None = None,
    included_roots: Iterable[str] = (),
    excluded_roots: Iterable[str] = (),
) -> ModelCopyProof:
    """Copy one exact dependency tree with handles bounded by path depth."""

    limits.validate()
    proof, _peak = _copy_dependency_snapshot(
        source, destination, store_proof=store_proof,
        canonical_store=canonical_store, repo_roots=repo_roots,
        limits=limits, expected_plan=expected_plan,
        included_roots=included_roots,
        excluded_roots=excluded_roots,
    )
    return proof


__all__ = [
    "DependencyRuntimeSourcePlan",
    "copy_dependency_runtime_snapshot",
    "plan_dependency_runtime_snapshot",
]
