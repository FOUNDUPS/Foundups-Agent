"""Full-byte verification for one inert Holo dependency-runtime generation."""

from __future__ import annotations

import json
import os
import stat
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from modules.infrastructure.shared_utilities.runtime_artifact_confined_byte_reader import (
    confined_file_identity,
    secure_digest_confined_file_impl,
)
from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    secure_read_confined_text,
    validate_runtime_artifact_path,
    validate_runtime_root_path,
)
from modules.infrastructure.shared_utilities.runtime_artifact_windows_streams import (
    require_unnamed_data_stream_only,
)

from .reddog_holoindex_acceptance_guards import (
    AcceptanceGuardError,
    StoreProof,
    prove_existing_isolated_store,
    verify_store_proof,
)
from .reddog_holoindex_acceptance_windows import (
    WindowsDirectoryLease,
    open_windows_directory_lease,
    validate_windows_directory_lease_exact_path,
)
from .reddog_holoindex_artifact_manifest import ModelCopyLimits, snapshot_artifact_files
from .reddog_holoindex_dependency_runtime_contract import (
    DESCRIPTOR_NAME,
    INVENTORY_NAME,
    SITE_PACKAGES_DIRECTORY,
    DependencyRuntimeBinding,
    DependencyRuntimeContractError,
    DependencyRuntimeLimits,
    canonical_json_bytes,
    dependency_tree_digest,
    digest_bytes,
    is_digest,
    validate_descriptor,
    validate_inventory,
)
from .reddog_holoindex_query_replica_orphans import OwnedDirectoryProof


class DependencyRuntimeDescriptorError(RuntimeError):
    """Stable inert-generation verification error."""


def _fail(code: str) -> None:
    raise DependencyRuntimeDescriptorError(code)


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if type(key) is not str or key in result:
            _fail("DEPENDENCY_RUNTIME_JSON_DUPLICATE_KEY")
        result[key] = value
    return result


def _parse_canonical(raw: str, *, code: str) -> dict[str, Any]:
    try:
        value = json.loads(
            raw, object_pairs_hook=_strict_object,
            parse_constant=lambda _value: _fail(code),
        )
    except DependencyRuntimeDescriptorError:
        raise
    except Exception:
        _fail(code)
    if type(value) is not dict or canonical_json_bytes(value).decode("ascii") != raw:
        _fail(code)
    return value


def _is_link_or_reparse(path: Path, metadata: os.stat_result) -> bool:
    attributes = int(getattr(metadata, "st_file_attributes", 0))
    return bool(
        stat.S_ISLNK(metadata.st_mode)
        or attributes & int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))
        or getattr(path, "is_junction", lambda: False)()
    )


def _validated_store(
    runtime_store_root: Path | str, canonical_store: Path | str,
    repo_roots: tuple[Path | str, ...],
) -> StoreProof:
    for repo_root in repo_roots:
        validate_runtime_root_path(runtime_store_root, repo_root=repo_root)
    store = prove_existing_isolated_store(
        runtime_store_root, canonical_store=canonical_store, repo_roots=repo_roots
    )
    verify_store_proof(store, canonical_store=canonical_store, repo_roots=repo_roots)
    return store


def _literal_generation_child(
    value: Path | str, store: StoreProof, repo_roots: tuple[Path | str, ...],
) -> tuple[Path, os.stat_result]:
    raw = str(value or "")
    if not raw or "\x00" in raw or not Path(raw).is_absolute():
        _fail("DEPENDENCY_RUNTIME_GENERATION_PATH_INVALID")
    for repo_root in repo_roots:
        validate_runtime_artifact_path(
            raw, repo_root=repo_root, allowed_root=store.path
        )
    generation = Path(os.path.abspath(raw))
    if os.path.normcase(str(generation.parent)) != os.path.normcase(str(store.path)):
        _fail("DEPENDENCY_RUNTIME_GENERATION_PATH_INVALID")
    try:
        metadata = os.lstat(generation)
    except OSError:
        _fail("DEPENDENCY_RUNTIME_GENERATION_UNAVAILABLE")
    if not stat.S_ISDIR(metadata.st_mode) or _is_link_or_reparse(generation, metadata):
        _fail("DEPENDENCY_RUNTIME_GENERATION_PATH_INVALID")
    return generation, metadata


@contextmanager
def _pinned_generation_root(
    generation: Path, metadata: os.stat_result,
) -> Iterator[None]:
    lease: WindowsDirectoryLease | None = None
    if os.name == "nt":
        try:
            lease = open_windows_directory_lease(
                generation,
                expected_identity=(int(metadata.st_dev), int(metadata.st_ino)),
            )
            validate_windows_directory_lease_exact_path(lease)
        except (OSError, ValueError) as exc:
            raise DependencyRuntimeDescriptorError(
                "DEPENDENCY_RUNTIME_GENERATION_PATH_INVALID"
            ) from exc
    try:
        yield
        if lease is not None:
            validate_windows_directory_lease_exact_path(lease)
    finally:
        if lease is not None:
            lease.close()


def _direct_generation_topology(root: Path) -> None:
    require_unnamed_data_stream_only(root)
    expected = {
        DESCRIPTOR_NAME, INVENTORY_NAME, SITE_PACKAGES_DIRECTORY,
        ".dependency-runtime-publication-orphans",
    }
    try:
        entries = tuple(os.scandir(root))
    except OSError:
        _fail("DEPENDENCY_RUNTIME_GENERATION_UNAVAILABLE")
    if {entry.name for entry in entries} != expected:
        _fail("DEPENDENCY_RUNTIME_GENERATION_TOPOLOGY_INVALID")
    for entry in entries:
        _validate_topology_entry(Path(entry.path), entry.name)
    orphan_root = root / ".dependency-runtime-publication-orphans"
    try:
        if tuple(os.scandir(orphan_root)):
            _fail("DEPENDENCY_RUNTIME_GENERATION_TOPOLOGY_INVALID")
    except OSError:
        _fail("DEPENDENCY_RUNTIME_GENERATION_TOPOLOGY_INVALID")


def _validate_topology_entry(path: Path, name: str) -> None:
    metadata = os.lstat(path)
    wanted_directory = name in {
        SITE_PACKAGES_DIRECTORY, ".dependency-runtime-publication-orphans",
    }
    if (
        _is_link_or_reparse(path, metadata)
        or stat.S_ISDIR(metadata.st_mode) is not wanted_directory
        or (not wanted_directory and not stat.S_ISREG(metadata.st_mode))
    ):
        _fail("DEPENDENCY_RUNTIME_GENERATION_TOPOLOGY_INVALID")
    require_unnamed_data_stream_only(path)


def _snapshot_identity(snapshot: Any, root: Path) -> tuple[tuple[Any, ...], ...]:
    directories = tuple(
        ("directory", path.relative_to(root).as_posix(), confined_file_identity(metadata))
        for path, metadata in sorted(
            snapshot.directories.items(), key=lambda item: item[0].as_posix().casefold()
        )
    )
    files = tuple(
        ("file", relative, confined_file_identity(metadata))
        for relative, _path, metadata in snapshot.files
    )
    return directories + files


def _verified_payload_rows(
    site_root: Path, expected_rows: list[dict[str, Any]],
    expected_directories: list[str], limits: DependencyRuntimeLimits,
) -> list[dict[str, Any]]:
    copy_limits = ModelCopyLimits(
        limits.max_files, limits.max_file_bytes, limits.max_total_bytes
    )
    before = snapshot_artifact_files(site_root, copy_limits)
    _verify_directory_streams(before)
    actual_shape = tuple(
        (relative, int(metadata.st_size)) for relative, _path, metadata in before.files
    )
    expected_shape = tuple((row["path"], row["size"]) for row in expected_rows)
    if actual_shape != expected_shape:
        _fail("DEPENDENCY_RUNTIME_INVENTORY_MISMATCH")
    actual_directories = tuple(sorted(
        (
            path.relative_to(site_root).as_posix()
            for path in before.directories if path != site_root
        ),
        key=str.casefold,
    ))
    if actual_directories != tuple(expected_directories):
        _fail("DEPENDENCY_RUNTIME_INVENTORY_MISMATCH")
    observed = _hash_payload_rows(site_root, before.files, expected_rows, limits)
    after = snapshot_artifact_files(site_root, copy_limits)
    _verify_directory_streams(after)
    if _snapshot_identity(before, site_root) != _snapshot_identity(after, site_root):
        _fail("DEPENDENCY_RUNTIME_PAYLOAD_CHANGED")
    return observed


def _verify_directory_streams(snapshot: Any) -> None:
    for directory in snapshot.directories:
        require_unnamed_data_stream_only(directory)


def _hash_payload_rows(
    site_root: Path, snapshot_files: list[tuple[str, Path, os.stat_result]],
    expected_rows: list[dict[str, Any]], limits: DependencyRuntimeLimits,
) -> list[dict[str, Any]]:
    observed: list[dict[str, Any]] = []
    for row, (_relative, path, metadata) in zip(expected_rows, snapshot_files):
        require_unnamed_data_stream_only(path)
        proof = secure_digest_confined_file_impl(
            path, allowed_root=site_root,
            expected_identity=confined_file_identity(metadata),
            max_bytes=limits.max_file_bytes,
        )
        require_unnamed_data_stream_only(path)
        if proof.size != row["size"] or proof.digest != row["sha256"]:
            _fail("DEPENDENCY_RUNTIME_PAYLOAD_DIGEST_MISMATCH")
        observed.append(dict(row))
    return observed


def _read_contracts(
    generation: Path, limits: DependencyRuntimeLimits,
) -> tuple[dict[str, Any], dict[str, Any], bytes, bytes]:
    descriptor_text = secure_read_confined_text(
        generation / DESCRIPTOR_NAME, allowed_root=generation,
        max_bytes=limits.max_descriptor_bytes,
    )
    inventory_text = secure_read_confined_text(
        generation / INVENTORY_NAME, allowed_root=generation,
        max_bytes=limits.max_inventory_bytes,
    )
    descriptor_raw = descriptor_text.encode("ascii")
    inventory_raw = inventory_text.encode("ascii")
    try:
        descriptor = validate_descriptor(
            _parse_canonical(descriptor_text, code="DEPENDENCY_RUNTIME_DESCRIPTOR_INVALID")
        )
        inventory = validate_inventory(
            _parse_canonical(inventory_text, code="DEPENDENCY_RUNTIME_INVENTORY_INVALID")
        )
    except DependencyRuntimeContractError as exc:
        _fail(str(exc))
    return descriptor, inventory, descriptor_raw, inventory_raw


def _binding_from_verified_payload(
    *, generation: Path, descriptor: dict[str, Any], descriptor_raw: bytes,
    rows: list[dict[str, Any]], directories: list[str],
) -> DependencyRuntimeBinding:
    tree_digest = dependency_tree_digest(directories, rows)
    if (
        tree_digest != descriptor["dependency_tree_digest"]
        or tree_digest != descriptor["generation_id"]
        or len(rows) != descriptor["file_count"]
        or len(directories) != descriptor["directory_count"]
        or sum(row["size"] for row in rows) != descriptor["total_bytes"]
    ):
        _fail("DEPENDENCY_RUNTIME_ARTIFACT_BINDING_INVALID")
    return DependencyRuntimeBinding(
        generation_root=generation,
        site_packages_root=generation / SITE_PACKAGES_DIRECTORY,
        descriptor_path=generation / DESCRIPTOR_NAME,
        descriptor_digest=digest_bytes(descriptor_raw),
        generation_id=descriptor["generation_id"],
        inventory_digest=descriptor["inventory_digest"],
        dependency_tree_digest=tree_digest,
        file_count=descriptor["file_count"],
        directory_count=descriptor["directory_count"],
        total_bytes=descriptor["total_bytes"],
        artifact_bytes_verified_at_publication=True,
        write_denial_verified=False, activation_eligible=False,
    )


def _verify_contents(
    generation: Path, *, expected_generation_id: str,
    bind_canonical_name: bool, limits: DependencyRuntimeLimits,
) -> DependencyRuntimeBinding:
    _direct_generation_topology(generation)
    descriptor, inventory, descriptor_raw, inventory_raw = _read_contracts(
        generation, limits
    )
    expected_name = expected_generation_id.removeprefix("sha256:")
    if (
        not is_digest(expected_generation_id)
        or descriptor["generation_id"] != expected_generation_id
        or (bind_canonical_name and generation.name != expected_name)
        or descriptor["inventory_digest"] != digest_bytes(inventory_raw)
        or descriptor["inventory_bytes"] != len(inventory_raw)
    ):
        _fail("DEPENDENCY_RUNTIME_DESCRIPTOR_BINDING_INVALID")
    _validate_inventory_limits(inventory, limits)
    rows = _verified_payload_rows(
        generation / SITE_PACKAGES_DIRECTORY, inventory["files"],
        inventory["directories"], limits,
    )
    return _binding_from_verified_payload(
        generation=generation, descriptor=descriptor,
        descriptor_raw=descriptor_raw, rows=rows,
        directories=inventory["directories"],
    )


def _validate_inventory_limits(
    inventory: dict[str, Any], limits: DependencyRuntimeLimits,
) -> None:
    directories = inventory["directories"]
    files = inventory["files"]
    paths = tuple(directories) + tuple(row["path"] for row in files)
    encoded_sizes = tuple(len(path.encode("utf-8")) for path in paths)
    if (
        len(files) > limits.max_files
        or len(directories) + 1 > limits.max_directories
        or any(len(Path(path).parts) > limits.max_directory_depth for path in paths)
        or any(size > limits.max_path_bytes for size in encoded_sizes)
        or sum(encoded_sizes) > limits.max_total_path_bytes
        or any(row["size"] > limits.max_file_bytes for row in files)
        or sum(row["size"] for row in files) > limits.max_total_bytes
    ):
        _fail("DEPENDENCY_RUNTIME_INVENTORY_BOUND_INVALID")


def _verify_generation(
    *, runtime_store_root: Path | str, generation_root: Path | str,
    expected_generation_id: str, bind_canonical_name: bool,
    canonical_store: Path | str, repo_roots: tuple[Path | str, ...],
    limits: DependencyRuntimeLimits, owned_root: OwnedDirectoryProof | None,
) -> DependencyRuntimeBinding:
    limits.validate()
    if not is_digest(expected_generation_id):
        _fail("DEPENDENCY_RUNTIME_DESCRIPTOR_BINDING_INVALID")
    store = _validated_store(runtime_store_root, canonical_store, repo_roots)
    generation, metadata = _literal_generation_child(
        generation_root, store, repo_roots
    )
    if owned_root is not None and (
        generation != owned_root.path
        or int(metadata.st_dev) != owned_root.device
        or int(metadata.st_ino) != owned_root.inode
    ):
        _fail("DEPENDENCY_RUNTIME_STAGING_IDENTITY_CHANGED")
    with _pinned_generation_root(generation, metadata):
        binding = _verify_contents(
            generation, expected_generation_id=expected_generation_id,
            bind_canonical_name=bind_canonical_name, limits=limits,
        )
        verify_store_proof(
            store, canonical_store=canonical_store, repo_roots=repo_roots
        )
        return binding


def verify_dependency_runtime_staging(
    *, runtime_store_root: Path | str, staging_root: Path | str,
    expected_generation_id: str, owned_root: OwnedDirectoryProof,
    canonical_store: Path | str, repo_roots: tuple[Path | str, ...],
    limits: DependencyRuntimeLimits = DependencyRuntimeLimits(),
) -> DependencyRuntimeBinding:
    """Fully verify unpublished process-owned staging bytes."""

    try:
        return _verify_generation(
            runtime_store_root=runtime_store_root, generation_root=staging_root,
            expected_generation_id=expected_generation_id,
            bind_canonical_name=False, canonical_store=canonical_store,
            repo_roots=repo_roots, limits=limits, owned_root=owned_root,
        )
    except DependencyRuntimeDescriptorError:
        raise
    except (
        AcceptanceGuardError, DependencyRuntimeContractError, OSError,
        TypeError, ValueError,
    ) as exc:
        raise DependencyRuntimeDescriptorError(str(exc)) from exc


def verify_dependency_runtime_generation(
    *, runtime_store_root: Path | str, generation_root: Path | str,
    canonical_store: Path | str, repo_roots: tuple[Path | str, ...],
    limits: DependencyRuntimeLimits = DependencyRuntimeLimits(),
    expected_generation_id: str | None = None,
) -> DependencyRuntimeBinding:
    """Verify a canonical inert generation through a stable error boundary."""

    try:
        raw_name = Path(str(generation_root)).name
        expected = expected_generation_id or f"sha256:{raw_name}"
        return _verify_generation(
            runtime_store_root=runtime_store_root,
            generation_root=generation_root, expected_generation_id=expected,
            bind_canonical_name=True, canonical_store=canonical_store,
            repo_roots=repo_roots, limits=limits, owned_root=None,
        )
    except DependencyRuntimeDescriptorError:
        raise
    except (
        AcceptanceGuardError, DependencyRuntimeContractError, OSError,
        TypeError, ValueError,
    ) as exc:
        raise DependencyRuntimeDescriptorError(str(exc)) from exc


__all__ = [
    "DependencyRuntimeDescriptorError",
    "verify_dependency_runtime_generation",
    "verify_dependency_runtime_staging",
]
