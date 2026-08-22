"""Verify the one active immutable HoloIndex query-replica descriptor.

The verifier never opens canonical vectors or model artifacts.  Canonical
authority is limited to repository state, cooperative leases, and the exact
freshness receipt.  Query artifacts are opened only below the proven replica
generation directory.
"""

from __future__ import annotations

import hashlib
import json
import os
import stat
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

from holo_index.freshness_receipt import freshness_receipt_path
from holo_index.maintenance_lock import (
    authority_update_lock_path,
    maintenance_lock_path,
    probe_maintenance_lock,
)
from holo_index.repository_state import (
    read_repository_state,
    repository_root_digest,
)
from holo_index.storage_contract import storage_path_identity

from .reddog_holoindex_acceptance_guards import (
    AcceptanceGuardError,
    StoreProof,
    _is_link_or_reparse,
    _normalized,
    _reject_link_components,
    _relative_to,
    prove_existing_isolated_store,
    verify_store_proof,
)
from .reddog_holoindex_acceptance_receipt_proof import (
    open_freshness_receipt_proof,
)
from .reddog_holoindex_acceptance_windows import (
    open_windows_directory_lease,
    open_windows_verified_regular_file,
    validate_windows_directory_lease_exact_path,
    validate_windows_file_descriptor,
    validate_windows_file_descriptor_exact_path,
)
from .reddog_holoindex_query_replica import (
    ACTIVE_DESCRIPTOR_NAME,
    QUERY_REPLICA_SCHEMA_VERSION,
    QueryReplicaLimits,
)


_HEX = frozenset("0123456789abcdef")
_DESCRIPTOR_KEYS = frozenset({
    "schema_version", "status", "created_at", "generation_directory",
    "canonical", "replica", "files",
})
_CANONICAL_KEYS = frozenset({
    "repo_root_digest", "repo_head_sha", "receipt_path", "receipt_digest",
    "generation_id", "storage_identity",
})
_REPLICA_KEYS = frozenset({"storage_identity"})
_FILE_KEYS = frozenset({
    "path", "size", "sha256", "source_before_sha256", "source_after_sha256",
})
_RUNTIME_ARTIFACT_PREFIXES = ("models/", "vectors/query_snapshots/")


class QueryReplicaDescriptorError(RuntimeError):
    """Stable fail-closed active-descriptor error."""


def _fail(code: str) -> None:
    raise QueryReplicaDescriptorError(code)


@dataclass(frozen=True)
class QueryReplicaArtifactBinding:
    relative_path: str
    size: int
    digest: str
    identity: tuple[int, int, int, int, int]


@dataclass(frozen=True)
class ActiveQueryReplicaBinding:
    descriptor_path: Path
    descriptor_digest: str
    descriptor_identity: tuple[int, int, int, int, int]
    generation_id: str
    generation_directory: Path
    replica_id: str
    path_identity_digest: str
    canonical_repo_head_sha: str
    canonical_repo_root_digest: str
    canonical_receipt_path: Path
    canonical_receipt_digest: str
    canonical_storage_identity: str
    query_storage_identity: str
    artifacts: tuple[QueryReplicaArtifactBinding, ...]

    @property
    def public_binding(self) -> Mapping[str, str]:
        return {
            "query_replica_descriptor_digest": self.descriptor_digest,
            "query_replica_generation_id": self.generation_id,
            "query_replica_id": self.replica_id,
            "query_replica_path_identity_digest": self.path_identity_digest,
        }

    @property
    def reuse_binding(self) -> tuple[str, str, str, str]:
        fields = self.public_binding
        return tuple(fields[key] for key in fields)  # type: ignore[return-value]


@dataclass(frozen=True)
class _DescriptorDependencies:
    state_reader: Callable[[Path], Any] = read_repository_state
    lock_probe: Callable[[Path], Any] = probe_maintenance_lock
    receipt_opener: Callable[..., Any] = open_freshness_receipt_proof


def _digest(payload: bytes) -> str:
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _valid_digest(value: Any) -> bool:
    return bool(
        type(value) is str and len(value) == 71
        and value.startswith("sha256:") and set(value[7:]) <= _HEX
    )


def _identity(metadata: os.stat_result) -> tuple[int, int, int, int, int]:
    return (
        int(metadata.st_dev), int(metadata.st_ino), int(metadata.st_size),
        int(metadata.st_mtime_ns), int(getattr(metadata, "st_nlink", 1)),
    )


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            _fail("QUERY_REPLICA_DESCRIPTOR_DUPLICATE_KEY")
        result[key] = value
    return result


def _decode_descriptor(payload: bytes) -> Mapping[str, Any]:
    try:
        value = json.loads(payload.decode("utf-8"), object_pairs_hook=_strict_object)
    except (UnicodeError, ValueError, json.JSONDecodeError) as exc:
        raise QueryReplicaDescriptorError("QUERY_REPLICA_DESCRIPTOR_INVALID_JSON") from exc
    if type(value) is not dict:
        _fail("QUERY_REPLICA_DESCRIPTOR_INVALID")
    return value


def _read_regular_file(path: Path, max_bytes: int) -> tuple[bytes, tuple[int, int, int, int, int]]:
    try:
        before = os.lstat(path)
    except OSError as exc:
        raise QueryReplicaDescriptorError("QUERY_REPLICA_FILE_UNAVAILABLE") from exc
    if (
        not stat.S_ISREG(before.st_mode) or _is_link_or_reparse(path, before)
        or int(getattr(before, "st_nlink", 1)) != 1
    ):
        _fail("QUERY_REPLICA_FILE_NOT_PRIVATE_REGULAR")
    descriptor = _open_regular_descriptor(path, _identity(before))
    try:
        payload = _read_descriptor_bytes(descriptor, max_bytes)
        after = _identity(os.fstat(descriptor))
        if after != _identity(before) or _identity(os.lstat(path)) != after:
            _fail("QUERY_REPLICA_FILE_IDENTITY_CHANGED")
        return payload, after
    finally:
        os.close(descriptor)


def _open_regular_descriptor(path: Path, expected: tuple[int, int, int, int, int]) -> int:
    try:
        if os.name == "nt":
            descriptor = open_windows_verified_regular_file(path, expected_identity=expected)
            validate_windows_file_descriptor_exact_path(descriptor, path)
            return descriptor
        descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        if _identity(os.fstat(descriptor)) != expected:
            os.close(descriptor)
            _fail("QUERY_REPLICA_FILE_IDENTITY_CHANGED")
        return descriptor
    except (OSError, ValueError) as exc:
        raise QueryReplicaDescriptorError("QUERY_REPLICA_FILE_OPEN_FAILED") from exc


def _read_descriptor_bytes(descriptor: int, max_bytes: int) -> bytes:
    chunks: list[bytes] = []
    total = 0
    os.lseek(descriptor, 0, os.SEEK_SET)
    while True:
        chunk = os.read(descriptor, min(1_048_576, max_bytes + 1 - total))
        if not chunk:
            break
        chunks.append(chunk)
        total += len(chunk)
        if total > max_bytes:
            _fail("QUERY_REPLICA_FILE_SIZE_BOUND")
    return b"".join(chunks)


def _validate_root_proof(
    proof: StoreProof, canonical: Path, repo_root: Path,
) -> Path:
    verify_store_proof(proof, canonical_store=canonical, repo_roots=(repo_root,))
    root = _normalized(proof.path)
    if os.name == "nt":
        try:
            lease = open_windows_directory_lease(
                root, expected_identity=(proof.device, proof.inode)
            )
            try:
                validate_windows_directory_lease_exact_path(lease)
            finally:
                lease.close()
        except (OSError, ValueError) as exc:
            raise QueryReplicaDescriptorError("QUERY_REPLICA_ROOT_ALIAS_REJECTED") from exc
    return root


def _require_clear_leases(
    canonical: Path, dependencies: _DescriptorDependencies,
) -> None:
    for path in (authority_update_lock_path(canonical), maintenance_lock_path(canonical)):
        try:
            proof = dependencies.lock_probe(path)
        except Exception as exc:
            raise QueryReplicaDescriptorError("QUERY_REPLICA_LEASE_UNPROVEN") from exc
        if getattr(proof, "clear", False) is not True:
            _fail(
                "QUERY_REPLICA_LEASE_ACTIVE"
                if getattr(proof, "held", False) is True else "QUERY_REPLICA_LEASE_UNPROVEN"
            )


def _validate_topology(
    payload: Mapping[str, Any], root: Path, canonical: Path, repo_root: Path,
) -> tuple[Mapping[str, Any], Mapping[str, Any], list[Any], Path]:
    if set(payload) != _DESCRIPTOR_KEYS:
        _fail("QUERY_REPLICA_DESCRIPTOR_SCHEMA_INVALID")
    if payload.get("schema_version") != QUERY_REPLICA_SCHEMA_VERSION or payload.get("status") != "CURRENT":
        _fail("QUERY_REPLICA_DESCRIPTOR_SCHEMA_INVALID")
    canonical_value, replica_value, files = (
        payload.get("canonical"), payload.get("replica"), payload.get("files")
    )
    if type(canonical_value) is not dict or set(canonical_value) != _CANONICAL_KEYS:
        _fail("QUERY_REPLICA_CANONICAL_BINDING_INVALID")
    if type(replica_value) is not dict or set(replica_value) != _REPLICA_KEYS:
        _fail("QUERY_REPLICA_STORAGE_BINDING_INVALID")
    if type(files) is not list or not files:
        _fail("QUERY_REPLICA_MANIFEST_INVALID")
    generation = _generation_path(root, payload.get("generation_directory"))
    if storage_path_identity(replica_value["storage_identity"]) != storage_path_identity(root):
        _fail("QUERY_REPLICA_STORAGE_BINDING_INVALID")
    if storage_path_identity(canonical_value["storage_identity"]) != storage_path_identity(canonical):
        _fail("QUERY_REPLICA_CANONICAL_BINDING_INVALID")
    if canonical_value["repo_root_digest"] != repository_root_digest(repo_root):
        _fail("QUERY_REPLICA_REPO_ROOT_DIGEST_MISMATCH")
    return canonical_value, replica_value, files, generation


def _generation_path(root: Path, value: Any) -> Path:
    if type(value) is not str or not value.startswith("generations/"):
        _fail("QUERY_REPLICA_GENERATION_PATH_INVALID")
    relative = Path(value)
    if relative.as_posix() != value or len(relative.parts) != 2 or ".." in relative.parts:
        _fail("QUERY_REPLICA_GENERATION_PATH_INVALID")
    generation = root / relative
    _reject_link_components(generation)
    if not generation.is_dir() or not _relative_to(generation, root):
        _fail("QUERY_REPLICA_GENERATION_PATH_INVALID")
    return generation


def _validate_canonical_binding(
    value: Mapping[str, Any], canonical: Path, repo_root: Path,
    dependencies: _DescriptorDependencies, limits: QueryReplicaLimits,
) -> None:
    head = value.get("repo_head_sha")
    generation = value.get("generation_id")
    if type(head) is not str or len(head) != 40 or set(head) > _HEX:
        _fail("QUERY_REPLICA_REPO_HEAD_INVALID")
    if not _valid_digest(generation) or not _valid_digest(value.get("receipt_digest")):
        _fail("QUERY_REPLICA_CANONICAL_BINDING_INVALID")
    if value.get("receipt_path") != str(freshness_receipt_path(canonical)):
        _fail("QUERY_REPLICA_RECEIPT_PATH_INVALID")
    state = dependencies.state_reader(repo_root)
    if not getattr(state, "proven_clean", False) or getattr(state, "head_sha", "") != head:
        _fail("QUERY_REPLICA_REPOSITORY_STATE_CHANGED")
    with dependencies.receipt_opener(
        path=value["receipt_path"], allowed_root=canonical,
        expected_ssd_path=canonical, expected_repo_root=repo_root,
        expected_repo_head_sha=head, expected_generation_id=generation,
        expected_receipt_digest=value["receipt_digest"],
        max_bytes=limits.max_receipt_bytes,
    ) as receipt:
        receipt.revalidate()


def _manifest_items(files: list[Any], generation: Path) -> tuple[tuple[str, int, str], ...]:
    items: list[tuple[str, int, str]] = []
    aliases: set[str] = set()
    for entry in files:
        if type(entry) is not dict or set(entry) != _FILE_KEYS:
            _fail("QUERY_REPLICA_MANIFEST_INVALID")
        relative, size = entry.get("path"), entry.get("size")
        digests = tuple(entry.get(key) for key in ("sha256", "source_before_sha256", "source_after_sha256"))
        if not _valid_manifest_path(relative) or type(size) is not int or size < 0:
            _fail("QUERY_REPLICA_MANIFEST_INVALID")
        if not all(_valid_digest(value) for value in digests) or len(set(digests)) != 1:
            _fail("QUERY_REPLICA_MANIFEST_DIGEST_INVALID")
        alias = unicodedata.normalize("NFC", relative).casefold()
        if alias in aliases:
            _fail("QUERY_REPLICA_MANIFEST_ALIAS")
        aliases.add(alias)
        items.append((relative, size, str(digests[0])))
    if tuple(items) != tuple(sorted(items)):
        _fail("QUERY_REPLICA_MANIFEST_ORDER_INVALID")
    if "vectors/chroma.sqlite3" not in {item[0] for item in items}:
        _fail("QUERY_REPLICA_VECTOR_DATABASE_MISSING")
    return tuple(items)


def _valid_manifest_path(value: Any) -> bool:
    if type(value) is not str or not value or "\\" in value:
        return False
    path = Path(value)
    return bool(
        not path.is_absolute() and ".." not in path.parts
        and path.as_posix() == value and len(path.parts) >= 2
        and path.parts[0] in {"models", "vectors"}
        and unicodedata.normalize("NFC", value) == value
    )


def _verify_artifacts(
    items: tuple[tuple[str, int, str], ...], generation: Path,
    limits: QueryReplicaLimits,
) -> tuple[QueryReplicaArtifactBinding, ...]:
    if len(items) > limits.max_files:
        _fail("QUERY_REPLICA_FILE_COUNT_BOUND")
    total = 0
    bindings: list[QueryReplicaArtifactBinding] = []
    for relative, size, expected_digest in items:
        if len(relative.encode("utf-8")) > limits.max_path_bytes or size > limits.max_file_bytes:
            _fail("QUERY_REPLICA_FILE_SIZE_BOUND")
        path = generation / Path(relative)
        if not _relative_to(path, generation):
            _fail("QUERY_REPLICA_FILE_PATH_ESCAPE")
        payload, identity = _read_regular_file(path, limits.max_file_bytes)
        if len(payload) != size or _digest(payload) != expected_digest:
            _fail("QUERY_REPLICA_ARTIFACT_DIGEST_MISMATCH")
        total += size
        if total > limits.max_total_bytes:
            _fail("QUERY_REPLICA_TOTAL_SIZE_BOUND")
        bindings.append(QueryReplicaArtifactBinding(relative, size, expected_digest, identity))
    _reject_unlisted_entries(generation, {item[0] for item in items})
    return tuple(bindings)


def _verify_runtime_artifacts(
    binding: ActiveQueryReplicaBinding,
    generation: Path,
    limits: QueryReplicaLimits,
) -> None:
    """Rehash only artifacts reachable by the sealed in-memory query backend."""

    selected = tuple(
        artifact for artifact in binding.artifacts
        if artifact.relative_path.startswith(_RUNTIME_ARTIFACT_PREFIXES)
    )
    roots = {
        "models" if artifact.relative_path.startswith("models/")
        else "query_snapshots"
        for artifact in selected
    }
    if roots != {"models", "query_snapshots"}:
        _fail("QUERY_REPLICA_RUNTIME_ARTIFACT_SET_INCOMPLETE")
    _reject_unlisted_runtime_entries(
        generation, {artifact.relative_path for artifact in selected}
    )
    total = 0
    for artifact in selected:
        relative = artifact.relative_path
        if len(relative.encode("utf-8")) > limits.max_path_bytes:
            _fail("QUERY_REPLICA_FILE_SIZE_BOUND")
        path = generation / Path(relative)
        if not _relative_to(path, generation):
            _fail("QUERY_REPLICA_FILE_PATH_ESCAPE")
        payload, identity = _read_regular_file(path, limits.max_file_bytes)
        if (
            identity != artifact.identity
            or len(payload) != artifact.size
            or _digest(payload) != artifact.digest
        ):
            _fail("QUERY_REPLICA_RUNTIME_ARTIFACT_CHANGED")
        total += artifact.size
        if total > limits.max_total_bytes:
            _fail("QUERY_REPLICA_TOTAL_SIZE_BOUND")


def _reject_unlisted_runtime_entries(
    generation: Path,
    expected: set[str],
) -> None:
    observed: set[str] = set()
    pending = [
        generation / "models",
        generation / "vectors" / "query_snapshots",
    ]
    while pending:
        directory = pending.pop()
        for entry in os.scandir(directory):
            path = Path(entry.path)
            metadata = os.lstat(path)
            if _is_link_or_reparse(path, metadata):
                _fail("QUERY_REPLICA_PATH_LINK_OR_REPARSE")
            if stat.S_ISDIR(metadata.st_mode):
                pending.append(path)
            elif stat.S_ISREG(metadata.st_mode):
                observed.add(path.relative_to(generation).as_posix())
            else:
                _fail("QUERY_REPLICA_SPECIAL_FILE")
    if observed != expected:
        _fail("QUERY_REPLICA_RUNTIME_ARTIFACT_SET_CHANGED")


def _reject_unlisted_entries(generation: Path, expected: set[str]) -> None:
    observed: set[str] = set()
    pending = [generation]
    while pending:
        directory = pending.pop()
        for entry in os.scandir(directory):
            path = Path(entry.path)
            metadata = os.lstat(path)
            if _is_link_or_reparse(path, metadata):
                _fail("QUERY_REPLICA_PATH_LINK_OR_REPARSE")
            if stat.S_ISDIR(metadata.st_mode):
                pending.append(path)
            elif stat.S_ISREG(metadata.st_mode):
                relative = path.relative_to(generation).as_posix()
                if unicodedata.normalize("NFC", relative) != relative:
                    _fail("QUERY_REPLICA_MANIFEST_ALIAS")
                observed.add(relative)
            else:
                _fail("QUERY_REPLICA_SPECIAL_FILE")
    if observed != expected:
        _fail("QUERY_REPLICA_MANIFEST_MISMATCH")


def _build_binding(
    descriptor: Path, descriptor_payload: bytes,
    descriptor_identity: tuple[int, int, int, int, int],
    canonical_value: Mapping[str, Any], root: Path, generation: Path,
    artifacts: tuple[QueryReplicaArtifactBinding, ...],
) -> ActiveQueryReplicaBinding:
    path_identity = storage_path_identity(root)
    path_digest = _digest(path_identity.encode("utf-8"))
    generation_id = str(canonical_value["generation_id"])
    replica_id = _digest(f"{path_digest}:{generation_id}".encode("utf-8"))
    return ActiveQueryReplicaBinding(
        descriptor, _digest(descriptor_payload), descriptor_identity,
        generation_id, generation, replica_id, path_digest,
        str(canonical_value["repo_head_sha"]),
        str(canonical_value["repo_root_digest"]),
        Path(str(canonical_value["receipt_path"])),
        str(canonical_value["receipt_digest"]),
        str(canonical_value["storage_identity"]), path_identity, artifacts,
    )


def _verify_active_query_replica_for_test(
    *, replica_root_proof: StoreProof, canonical_repo_root: Path | str,
    canonical_ssd_path: Path | str, limits: QueryReplicaLimits = QueryReplicaLimits(),
    dependencies: _DescriptorDependencies = _DescriptorDependencies(),
) -> ActiveQueryReplicaBinding:
    """Internal dependency seam; production callers use sealed defaults."""
    limits.validate()
    repo_root, canonical = _normalized(canonical_repo_root), _normalized(canonical_ssd_path)
    root = _validate_root_proof(replica_root_proof, canonical, repo_root)
    _require_clear_leases(canonical, dependencies)
    descriptor = root / ACTIVE_DESCRIPTOR_NAME
    payload_bytes, descriptor_identity = _read_regular_file(
        descriptor, limits.max_descriptor_bytes
    )
    payload = _decode_descriptor(payload_bytes)
    canonical_value, _, files, generation = _validate_topology(
        payload, root, canonical, repo_root
    )
    if generation.name != str(canonical_value.get("generation_id", "")).removeprefix("sha256:"):
        _fail("QUERY_REPLICA_GENERATION_PATH_INVALID")
    _validate_canonical_binding(canonical_value, canonical, repo_root, dependencies, limits)
    artifacts = _verify_artifacts(_manifest_items(files, generation), generation, limits)
    _require_clear_leases(canonical, dependencies)
    if dependencies.state_reader(repo_root).head_sha != canonical_value["repo_head_sha"]:
        _fail("QUERY_REPLICA_REPOSITORY_STATE_CHANGED")
    return _build_binding(
        descriptor, payload_bytes, descriptor_identity, canonical_value,
        root, generation, artifacts,
    )


def verify_active_query_replica(
    *, replica_root_proof: StoreProof, canonical_repo_root: Path | str,
    canonical_ssd_path: Path | str, limits: QueryReplicaLimits = QueryReplicaLimits(),
) -> ActiveQueryReplicaBinding:
    """Verify one exact active query replica with sealed production dependencies."""
    try:
        return _verify_active_query_replica_for_test(
            replica_root_proof=replica_root_proof,
            canonical_repo_root=canonical_repo_root,
            canonical_ssd_path=canonical_ssd_path,
            limits=limits,
        )
    except QueryReplicaDescriptorError:
        raise
    except (AcceptanceGuardError, OSError, TypeError, ValueError) as exc:
        raise QueryReplicaDescriptorError(str(exc)) from exc


def _require_admitted_repository_state(
    binding: ActiveQueryReplicaBinding,
    repo_root: Path,
    dependencies: _DescriptorDependencies,
) -> None:
    state = dependencies.state_reader(repo_root)
    if (
        getattr(state, "proven_clean", False) is not True
        or getattr(state, "head_sha", "") != binding.canonical_repo_head_sha
    ):
        _fail("QUERY_REPLICA_REPOSITORY_STATE_CHANGED")


def _revalidate_admitted_query_replica_for_test(
    *, admitted_binding: ActiveQueryReplicaBinding,
    replica_root_proof: StoreProof, canonical_repo_root: Path | str,
    canonical_ssd_path: Path | str, limits: QueryReplicaLimits = QueryReplicaLimits(),
    dependencies: _DescriptorDependencies = _DescriptorDependencies(),
) -> ActiveQueryReplicaBinding:
    """Reprove a fully admitted binding over the backend's reachable files."""

    limits.validate()
    repo_root = _normalized(canonical_repo_root)
    canonical = _normalized(canonical_ssd_path)
    root = _validate_root_proof(replica_root_proof, canonical, repo_root)
    _require_clear_leases(canonical, dependencies)
    descriptor = root / ACTIVE_DESCRIPTOR_NAME
    if _normalized(admitted_binding.descriptor_path) != descriptor:
        _fail("QUERY_REPLICA_BINDING_CHANGED")
    payload_bytes, descriptor_identity = _read_regular_file(
        descriptor, limits.max_descriptor_bytes
    )
    if (
        descriptor_identity != admitted_binding.descriptor_identity
        or _digest(payload_bytes) != admitted_binding.descriptor_digest
    ):
        _fail("QUERY_REPLICA_BINDING_CHANGED")
    payload = _decode_descriptor(payload_bytes)
    canonical_value, _, files, generation = _validate_topology(
        payload, root, canonical, repo_root
    )
    _validate_canonical_binding(
        canonical_value, canonical, repo_root, dependencies, limits
    )
    if generation != _normalized(admitted_binding.generation_directory):
        _fail("QUERY_REPLICA_BINDING_CHANGED")
    manifest = _manifest_items(files, generation)
    admitted_manifest = tuple(
        (artifact.relative_path, artifact.size, artifact.digest)
        for artifact in admitted_binding.artifacts
    )
    if manifest != admitted_manifest:
        _fail("QUERY_REPLICA_BINDING_CHANGED")
    rebuilt = _build_binding(
        descriptor, payload_bytes, descriptor_identity, canonical_value,
        root, generation, admitted_binding.artifacts,
    )
    if rebuilt != admitted_binding:
        _fail("QUERY_REPLICA_BINDING_CHANGED")
    _verify_runtime_artifacts(admitted_binding, generation, limits)
    _require_clear_leases(canonical, dependencies)
    _require_admitted_repository_state(admitted_binding, repo_root, dependencies)
    return admitted_binding


def revalidate_admitted_query_replica(
    *, admitted_binding: ActiveQueryReplicaBinding,
    replica_root_proof: StoreProof, canonical_repo_root: Path | str,
    canonical_ssd_path: Path | str, limits: QueryReplicaLimits = QueryReplicaLimits(),
) -> ActiveQueryReplicaBinding:
    """Revalidate an admitted replica without reopening unused vector storage."""

    try:
        return _revalidate_admitted_query_replica_for_test(
            admitted_binding=admitted_binding,
            replica_root_proof=replica_root_proof,
            canonical_repo_root=canonical_repo_root,
            canonical_ssd_path=canonical_ssd_path,
            limits=limits,
        )
    except QueryReplicaDescriptorError:
        raise
    except (AcceptanceGuardError, OSError, TypeError, ValueError) as exc:
        raise QueryReplicaDescriptorError(str(exc)) from exc


def prove_and_verify_active_query_replica(
    *, replica_root: Path | str, canonical_repo_root: Path | str,
    canonical_ssd_path: Path | str, limits: QueryReplicaLimits = QueryReplicaLimits(),
) -> tuple[StoreProof, ActiveQueryReplicaBinding]:
    """Open an existing owned root capability and verify its active descriptor."""
    proof = prove_existing_isolated_store(
        replica_root, canonical_store=canonical_ssd_path,
        repo_roots=(canonical_repo_root,),
    )
    binding = verify_active_query_replica(
        replica_root_proof=proof, canonical_repo_root=canonical_repo_root,
        canonical_ssd_path=canonical_ssd_path, limits=limits,
    )
    return proof, binding


__all__ = [
    "ActiveQueryReplicaBinding", "QueryReplicaArtifactBinding",
    "QueryReplicaDescriptorError", "prove_and_verify_active_query_replica",
    "revalidate_admitted_query_replica", "verify_active_query_replica",
]
