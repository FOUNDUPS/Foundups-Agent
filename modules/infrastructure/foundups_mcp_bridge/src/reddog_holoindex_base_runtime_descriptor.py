"""Full-byte verification for one inert HoloIndex Python base runtime."""

from __future__ import annotations

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
from .reddog_holoindex_base_runtime_contract import (
    DESCRIPTOR_NAME,
    INVENTORY_NAME,
    PAYLOAD_DIRECTORY,
    BaseRuntimeBinding,
    BaseRuntimeContractError,
    BaseRuntimeLimits,
    base_runtime_tree_digest,
    canonical_json_bytes,
    digest_bytes,
    is_digest,
    parse_canonical_json,
    validate_descriptor,
    validate_inventory,
)
from .reddog_holoindex_query_replica_orphans import OwnedDirectoryProof


class BaseRuntimeDescriptorError(RuntimeError):
    """Stable inert base-runtime verification error."""


def _fail(code: str) -> None:
    raise BaseRuntimeDescriptorError(code)


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
        _fail("BASE_RUNTIME_GENERATION_PATH_INVALID")
    for repo_root in repo_roots:
        validate_runtime_artifact_path(raw, repo_root=repo_root, allowed_root=store.path)
    generation = Path(os.path.abspath(raw))
    if os.path.normcase(str(generation.parent)) != os.path.normcase(str(store.path)):
        _fail("BASE_RUNTIME_GENERATION_PATH_INVALID")
    try:
        metadata = os.lstat(generation)
    except OSError:
        _fail("BASE_RUNTIME_GENERATION_UNAVAILABLE")
    if not stat.S_ISDIR(metadata.st_mode) or _is_link_or_reparse(generation, metadata):
        _fail("BASE_RUNTIME_GENERATION_PATH_INVALID")
    return generation, metadata


@contextmanager
def _pinned_generation_root(
    generation: Path, metadata: os.stat_result,
) -> Iterator[None]:
    lease: WindowsDirectoryLease | None = None
    if os.name == "nt":
        try:
            lease = open_windows_directory_lease(
                generation, expected_identity=(int(metadata.st_dev), int(metadata.st_ino))
            )
            validate_windows_directory_lease_exact_path(lease)
        except (OSError, ValueError) as exc:
            raise BaseRuntimeDescriptorError(
                "BASE_RUNTIME_GENERATION_PATH_INVALID"
            ) from exc
    try:
        yield
        if lease is not None:
            validate_windows_directory_lease_exact_path(lease)
    finally:
        if lease is not None:
            lease.close()


def _validate_topology_entry(path: Path, name: str) -> None:
    metadata = os.lstat(path)
    directories = {PAYLOAD_DIRECTORY, ".base-runtime-publication-orphans"}
    wanted_directory = name in directories
    if (
        _is_link_or_reparse(path, metadata)
        or stat.S_ISDIR(metadata.st_mode) is not wanted_directory
        or (not wanted_directory and not stat.S_ISREG(metadata.st_mode))
    ):
        _fail("BASE_RUNTIME_GENERATION_TOPOLOGY_INVALID")
    require_unnamed_data_stream_only(path)


def _direct_generation_topology(root: Path) -> None:
    require_unnamed_data_stream_only(root)
    expected = {
        DESCRIPTOR_NAME, INVENTORY_NAME, PAYLOAD_DIRECTORY,
        ".base-runtime-publication-orphans",
    }
    try:
        entries = tuple(os.scandir(root))
    except OSError:
        _fail("BASE_RUNTIME_GENERATION_UNAVAILABLE")
    if {entry.name for entry in entries} != expected:
        _fail("BASE_RUNTIME_GENERATION_TOPOLOGY_INVALID")
    for entry in entries:
        _validate_topology_entry(Path(entry.path), entry.name)
    orphan_root = root / ".base-runtime-publication-orphans"
    try:
        if tuple(os.scandir(orphan_root)):
            _fail("BASE_RUNTIME_GENERATION_TOPOLOGY_INVALID")
    except OSError:
        _fail("BASE_RUNTIME_GENERATION_TOPOLOGY_INVALID")


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


def _verify_directory_streams(snapshot: Any) -> None:
    for directory in snapshot.directories:
        require_unnamed_data_stream_only(directory)


def _read_contracts(
    generation: Path, limits: BaseRuntimeLimits,
) -> tuple[dict[str, Any], dict[str, Any], bytes, bytes]:
    descriptor_text = secure_read_confined_text(
        generation / DESCRIPTOR_NAME, allowed_root=generation,
        max_bytes=limits.max_descriptor_bytes,
    )
    inventory_text = secure_read_confined_text(
        generation / INVENTORY_NAME, allowed_root=generation,
        max_bytes=limits.max_inventory_bytes,
    )
    try:
        descriptor = validate_descriptor(parse_canonical_json(descriptor_text))
        inventory = validate_inventory(parse_canonical_json(inventory_text), limits)
    except BaseRuntimeContractError as exc:
        _fail(str(exc))
    return (
        descriptor, inventory, descriptor_text.encode("ascii"),
        inventory_text.encode("ascii"),
    )


def _verified_payload_rows(
    payload_root: Path, inventory: dict[str, Any], limits: BaseRuntimeLimits,
) -> list[dict[str, Any]]:
    copy_limits = ModelCopyLimits(
        limits.max_files, limits.max_file_bytes, limits.max_total_bytes
    )
    before = snapshot_artifact_files(payload_root, copy_limits)
    _verify_directory_streams(before)
    rows = inventory["files"]
    actual_shape = tuple(
        (relative, int(metadata.st_size)) for relative, _path, metadata in before.files
    )
    if actual_shape != tuple((row["path"], row["size"]) for row in rows):
        _fail("BASE_RUNTIME_INVENTORY_MISMATCH")
    actual_directories = tuple(sorted(
        (path.relative_to(payload_root).as_posix()
         for path in before.directories if path != payload_root),
        key=str.casefold,
    ))
    if actual_directories != tuple(inventory["directories"]):
        _fail("BASE_RUNTIME_INVENTORY_MISMATCH")
    observed = _hash_payload_rows(payload_root, before.files, rows, limits)
    after = snapshot_artifact_files(payload_root, copy_limits)
    _verify_directory_streams(after)
    if _snapshot_identity(before, payload_root) != _snapshot_identity(after, payload_root):
        _fail("BASE_RUNTIME_PAYLOAD_CHANGED")
    return observed


def _hash_payload_rows(
    payload_root: Path, snapshot_files: list[tuple[str, Path, os.stat_result]],
    rows: list[dict[str, Any]], limits: BaseRuntimeLimits,
) -> list[dict[str, Any]]:
    observed: list[dict[str, Any]] = []
    for row, (_relative, path, metadata) in zip(rows, snapshot_files):
        require_unnamed_data_stream_only(path)
        proof = secure_digest_confined_file_impl(
            path, allowed_root=payload_root,
            expected_identity=confined_file_identity(metadata),
            max_bytes=limits.max_file_bytes,
        )
        require_unnamed_data_stream_only(path)
        if proof.size != row["size"] or proof.digest != row["sha256"]:
            _fail("BASE_RUNTIME_PAYLOAD_DIGEST_MISMATCH")
        observed.append(dict(row))
    return observed


def _binding(
    generation: Path, descriptor: dict[str, Any], descriptor_raw: bytes,
    inventory: dict[str, Any], rows: list[dict[str, Any]],
) -> BaseRuntimeBinding:
    tree_digest = base_runtime_tree_digest(inventory["directories"], rows)
    if (
        tree_digest != descriptor["base_runtime_tree_digest"]
        or tree_digest != descriptor["generation_id"]
        or len(rows) != descriptor["file_count"]
        or len(inventory["directories"]) != descriptor["directory_count"]
        or sum(row["size"] for row in rows) != descriptor["total_bytes"]
    ):
        _fail("BASE_RUNTIME_ARTIFACT_BINDING_INVALID")
    return BaseRuntimeBinding(
        generation_root=generation,
        base_prefix_root=generation / PAYLOAD_DIRECTORY,
        descriptor_path=generation / DESCRIPTOR_NAME,
        descriptor_digest=digest_bytes(descriptor_raw),
        generation_id=descriptor["generation_id"],
        inventory_digest=descriptor["inventory_digest"],
        base_runtime_tree_digest=tree_digest,
        file_count=descriptor["file_count"],
        directory_count=descriptor["directory_count"],
        total_bytes=descriptor["total_bytes"],
        artifact_bytes_verified_at_publication=True,
        native_loader_closure_verified=False,
        deterministic_effects_verified=False,
        signature_verified=False,
        write_denial_verified=False,
        activation_eligible=False,
        exact_runtime_closure_verified=False,
    )


def _verify_contents(
    generation: Path, expected_generation_id: str,
    bind_canonical_name: bool, limits: BaseRuntimeLimits,
) -> BaseRuntimeBinding:
    _direct_generation_topology(generation)
    descriptor, inventory, descriptor_raw, inventory_raw = _read_contracts(
        generation, limits
    )
    if (
        not is_digest(expected_generation_id)
        or descriptor["generation_id"] != expected_generation_id
        or (bind_canonical_name
            and generation.name != expected_generation_id.removeprefix("sha256:"))
        or descriptor["inventory_digest"] != digest_bytes(inventory_raw)
        or descriptor["inventory_bytes"] != len(inventory_raw)
    ):
        _fail("BASE_RUNTIME_DESCRIPTOR_BINDING_INVALID")
    rows = _verified_payload_rows(generation / PAYLOAD_DIRECTORY, inventory, limits)
    return _binding(generation, descriptor, descriptor_raw, inventory, rows)


def _verify_generation(
    *, runtime_store_root: Path | str, generation_root: Path | str,
    expected_generation_id: str, bind_canonical_name: bool,
    canonical_store: Path | str, repo_roots: tuple[Path | str, ...],
    limits: BaseRuntimeLimits, owned_root: OwnedDirectoryProof | None,
) -> BaseRuntimeBinding:
    limits.validate()
    store = _validated_store(runtime_store_root, canonical_store, repo_roots)
    generation, metadata = _literal_generation_child(generation_root, store, repo_roots)
    if owned_root is not None and (
        generation != owned_root.path
        or int(metadata.st_dev) != owned_root.device
        or int(metadata.st_ino) != owned_root.inode
    ):
        _fail("BASE_RUNTIME_STAGING_IDENTITY_CHANGED")
    with _pinned_generation_root(generation, metadata):
        binding = _verify_contents(
            generation, expected_generation_id, bind_canonical_name, limits
        )
        verify_store_proof(
            store, canonical_store=canonical_store, repo_roots=repo_roots
        )
        return binding


def verify_base_runtime_staging(
    *, runtime_store_root: Path | str, staging_root: Path | str,
    expected_generation_id: str, owned_root: OwnedDirectoryProof,
    canonical_store: Path | str, repo_roots: tuple[Path | str, ...],
    limits: BaseRuntimeLimits = BaseRuntimeLimits(),
) -> BaseRuntimeBinding:
    """Fully verify unpublished process-owned base-runtime staging bytes."""

    try:
        return _verify_generation(
            runtime_store_root=runtime_store_root, generation_root=staging_root,
            expected_generation_id=expected_generation_id,
            bind_canonical_name=False, canonical_store=canonical_store,
            repo_roots=repo_roots, limits=limits, owned_root=owned_root,
        )
    except BaseRuntimeDescriptorError:
        raise
    except (AcceptanceGuardError, BaseRuntimeContractError, OSError, TypeError, ValueError) as exc:
        raise BaseRuntimeDescriptorError(str(exc)) from exc


def verify_base_runtime_generation(
    *, runtime_store_root: Path | str, generation_root: Path | str,
    canonical_store: Path | str, repo_roots: tuple[Path | str, ...],
    limits: BaseRuntimeLimits = BaseRuntimeLimits(),
    expected_generation_id: str | None = None,
) -> BaseRuntimeBinding:
    """Verify one canonical inert base-runtime generation fail closed."""

    try:
        expected = expected_generation_id or f"sha256:{Path(str(generation_root)).name}"
        return _verify_generation(
            runtime_store_root=runtime_store_root, generation_root=generation_root,
            expected_generation_id=expected, bind_canonical_name=True,
            canonical_store=canonical_store, repo_roots=repo_roots,
            limits=limits, owned_root=None,
        )
    except BaseRuntimeDescriptorError:
        raise
    except (AcceptanceGuardError, BaseRuntimeContractError, OSError, TypeError, ValueError) as exc:
        raise BaseRuntimeDescriptorError(str(exc)) from exc


__all__ = [
    "BaseRuntimeDescriptorError",
    "verify_base_runtime_generation",
    "verify_base_runtime_staging",
]
