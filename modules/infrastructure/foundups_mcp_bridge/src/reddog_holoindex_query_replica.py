"""Materialize one immutable HoloIndex query replica from exact bindings.

No ambient SSD root is copied and no HoloIndex process is started.
"""

from __future__ import annotations

import hashlib
import json
import os
import secrets
from contextlib import ExitStack
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from holo_index.freshness_receipt import freshness_receipt_path
from holo_index.maintenance_lock import (
    MaintenanceLockError,
    acquire_existing_maintenance_lease,
    authority_update_lock_path,
    maintenance_lock_path,
)
from holo_index.repository_state import repository_root_digest
from holo_index.storage_contract import storage_path_identity

from .reddog_holoindex_acceptance_guards import (
    AcceptanceGuardError,
    ExpectedArtifactFile,
    ModelCopyLimits,
    StoreProof,
    PublishedPrivateJsonProof,
    QuarantinedPathProof,
    _normalized,
    _relative_to,
    atomic_publish_private_json_proven,
    copy_model_snapshot,
    create_isolated_store,
    verify_store_proof,
    quarantine_proven_private_json,
    verify_proven_private_json,
)
from .reddog_holoindex_acceptance_receipt_proof import open_freshness_receipt_proof
from .reddog_holoindex_query_replica_generation import (
    QueryReplicaGenerationError,
    publish_directory_no_replace,
)
from .reddog_holoindex_query_replica_orphans import (
    OwnedDirectoryProof,
    owned_directory,
    quarantine_owned_staging,
)
QUERY_REPLICA_SCHEMA_VERSION = "holoindex_query_replica.v1"
ACTIVE_DESCRIPTOR_NAME = "holoindex_query_replica.active.json"
_HEX = frozenset("0123456789abcdef")
class QueryReplicaError(RuntimeError):
    """Stable fail-closed materializer error."""

    def __init__(
        self, code: str, *, orphan_relative_path: str = "",
        unsafe_relative_path: str = "",
    ) -> None:
        super().__init__(code)
        self.orphan_relative_path = orphan_relative_path
        self.unsafe_relative_path = unsafe_relative_path


def _fail(code: str) -> None:
    raise QueryReplicaError(code)


@dataclass(frozen=True)
class CanonicalGenerationBinding:
    repo_root: Path
    repo_root_digest: str
    repo_head_sha: str
    receipt_path: Path
    receipt_digest: str
    generation_id: str
    canonical_storage_identity: str


@dataclass(frozen=True)
class ArtifactTreeManifest:
    logical_name: str
    source_root: Path
    replica_relative_root: str
    files: tuple[ExpectedArtifactFile, ...]


@dataclass(frozen=True)
class QueryReplicaLimits:
    max_files: int = 200_000
    max_file_bytes: int = 2_147_483_648
    max_total_bytes: int = 8_589_934_592
    max_path_bytes: int = 1024
    max_receipt_bytes: int = 262_144
    max_descriptor_bytes: int = 2_097_152

    def validate(self) -> None:
        values = (
            self.max_files, self.max_file_bytes, self.max_total_bytes,
            self.max_path_bytes, self.max_receipt_bytes,
            self.max_descriptor_bytes,
        )
        if any(type(value) is not int or value <= 0 for value in values):
            _fail("QUERY_REPLICA_LIMIT_INVALID")


@dataclass(frozen=True)
class QueryReplicaResult:
    generation_directory: Path
    active_descriptor: Path
    descriptor_digest: str
    file_count: int
    total_bytes: int


@dataclass(frozen=True)
class _QueryReplicaTestDependencies:
    open_receipt: Callable[..., Any] = open_freshness_receipt_proof
    acquire_lease: Callable[..., Any] = acquire_existing_maintenance_lease
    copy_tree: Callable[..., Any] = copy_model_snapshot
    publish_json: Callable[..., PublishedPrivateJsonProof] = atomic_publish_private_json_proven
    publish_directory: Callable[[Path, Path], None] | None = None
    now: Callable[[], datetime] = lambda: datetime.now(timezone.utc)
    orphan_token: Callable[[], str] = lambda: secrets.token_hex(16)


@dataclass(frozen=True)
class _MaterializationPaths:
    canonical: Path
    replica_root: Path
    orphans: Path
    active: Path
    generation: Path
    generation_name: str
    manifests: tuple[ArtifactTreeManifest, ...]


def _valid_digest(value: str) -> bool:
    return len(value) == 71 and value.startswith("sha256:") and set(value[7:]) <= _HEX


def _validate_binding(binding: CanonicalGenerationBinding, canonical_store: Path) -> None:
    repo_root = _normalized(binding.repo_root)
    receipt = _normalized(binding.receipt_path)
    if binding.repo_root_digest != repository_root_digest(repo_root):
        _fail("QUERY_REPLICA_REPO_ROOT_DIGEST_MISMATCH")
    if len(binding.repo_head_sha) != 40 or set(binding.repo_head_sha) > _HEX:
        _fail("QUERY_REPLICA_REPO_HEAD_INVALID")
    if not _valid_digest(binding.receipt_digest) or not _valid_digest(binding.generation_id):
        _fail("QUERY_REPLICA_GENERATION_BINDING_INVALID")
    if receipt != freshness_receipt_path(canonical_store).resolve(strict=False):
        _fail("QUERY_REPLICA_RECEIPT_PATH_NONCANONICAL")
    if binding.canonical_storage_identity != storage_path_identity(canonical_store):
        _fail("QUERY_REPLICA_STORAGE_IDENTITY_MISMATCH")


def _validate_manifests(
    manifests: tuple[ArtifactTreeManifest, ...],
    canonical_store: Path,
    limits: QueryReplicaLimits,
) -> tuple[ArtifactTreeManifest, ...]:
    if tuple(sorted(manifests, key=lambda item: item.logical_name)) != manifests:
        _fail("QUERY_REPLICA_MANIFEST_ORDER_INVALID")
    if tuple(item.logical_name for item in manifests) != ("model", "vectors"):
        _fail("QUERY_REPLICA_ARTIFACT_SET_INVALID")
    total_files = 0
    total_bytes = 0
    for manifest in manifests:
        relative_root = Path(manifest.replica_relative_root)
        if (
            relative_root.is_absolute()
            or ".." in relative_root.parts
            or not relative_root.parts
            or relative_root.parts[0] not in {"models", "vectors"}
        ):
            _fail("QUERY_REPLICA_ARTIFACT_ROOT_INVALID")
        source = _normalized(manifest.source_root)
        expected_source = canonical_store.joinpath(relative_root).resolve(strict=False)
        if source != expected_source or not _relative_to(source, canonical_store):
            _fail("QUERY_REPLICA_SOURCE_PATH_INVALID")
        if manifest.logical_name == "vectors":
            if relative_root.as_posix() != "vectors":
                _fail("QUERY_REPLICA_VECTOR_ROOT_INVALID")
            if "chroma.sqlite3" not in {item.relative_path for item in manifest.files}:
                _fail("QUERY_REPLICA_VECTOR_DATABASE_MISSING")
        elif relative_root.parts[0] != "models":
            _fail("QUERY_REPLICA_MODEL_ROOT_INVALID")
        else:
            model_paths = {item.relative_path for item in manifest.files}
            if not {"modules.json", "config.json", "model.safetensors"} <= model_paths or not (
                {"tokenizer.json", "vocab.txt"} & model_paths
            ):
                _fail("QUERY_REPLICA_MODEL_SNAPSHOT_INCOMPLETE")
        for item in manifest.files:
            if len(item.relative_path.encode("utf-8")) > limits.max_path_bytes:
                _fail("QUERY_REPLICA_PATH_BOUND")
            total_files += 1
            total_bytes += item.size
    if total_files > limits.max_files:
        _fail("QUERY_REPLICA_FILE_COUNT_BOUND")
    if total_bytes > limits.max_total_bytes:
        _fail("QUERY_REPLICA_TOTAL_SIZE_BOUND")
    return manifests


def _descriptor_payload(
    *, binding: CanonicalGenerationBinding, canonical_store: Path,
    replica_root: Path, generation_name: str, proofs: list[tuple[ArtifactTreeManifest, Any]],
    created_at: datetime,
) -> dict[str, Any]:
    files: list[dict[str, Any]] = []
    for manifest, proof in proofs:
        for item in proof.files:
            files.append(
                {
                    "path": f"{manifest.replica_relative_root}/{item.relative_path}",
                    "size": item.size,
                    "sha256": item.destination_sha256,
                    "source_before_sha256": item.source_before_sha256,
                    "source_after_sha256": item.source_after_sha256,
                }
            )
    files.sort(key=lambda item: item["path"])
    return {
        "schema_version": QUERY_REPLICA_SCHEMA_VERSION,
        "status": "CURRENT",
        "created_at": created_at.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        "generation_directory": f"generations/{generation_name}",
        "canonical": {
            "repo_root_digest": binding.repo_root_digest,
            "repo_head_sha": binding.repo_head_sha,
            "receipt_path": str(binding.receipt_path),
            "receipt_digest": binding.receipt_digest,
            "generation_id": binding.generation_id,
            "storage_identity": storage_path_identity(canonical_store),
        },
        "replica": {"storage_identity": storage_path_identity(replica_root)},
        "files": files,
    }


def _prepare_materialization(
    canonical_store: Path | str,
    replica_root_proof: StoreProof,
    binding: CanonicalGenerationBinding,
    manifests: tuple[ArtifactTreeManifest, ...],
    limits: QueryReplicaLimits,
) -> _MaterializationPaths:
    canonical = _normalized(canonical_store)
    replica_root = _normalized(replica_root_proof.path)
    limits.validate()
    verify_store_proof(
        replica_root_proof, canonical_store=canonical, repo_roots=(binding.repo_root,)
    )
    _validate_binding(binding, canonical)
    ordered = _validate_manifests(manifests, canonical, limits)
    active = replica_root / ACTIVE_DESCRIPTOR_NAME
    generation_name = binding.generation_id.removeprefix("sha256:")
    generation = replica_root / "generations" / generation_name
    if active.exists():
        _fail("QUERY_REPLICA_ACTIVE_DESCRIPTOR_EXISTS")
    if generation.exists():
        _fail("QUERY_REPLICA_GENERATION_EXISTS")
    try:
        existing = tuple(os.scandir(replica_root))
    except OSError as exc:
        raise QueryReplicaError("QUERY_REPLICA_ROOT_UNAVAILABLE") from exc
    if existing:
        _fail("QUERY_REPLICA_ROOT_NOT_EMPTY")
    (replica_root / "generations").mkdir(mode=0o700)
    orphans = replica_root / ".query-replica-orphans"
    orphans.mkdir(mode=0o700)
    return _MaterializationPaths(
        canonical, replica_root, orphans, active, generation, generation_name, ordered
    )


def _copy_manifest_trees(
    *, paths: _MaterializationPaths, staging: Path, staging_proof: StoreProof,
    binding: CanonicalGenerationBinding, limits: QueryReplicaLimits,
    dependencies: _QueryReplicaTestDependencies, receipt: Any,
) -> list[tuple[ArtifactTreeManifest, Any]]:
    proofs: list[tuple[ArtifactTreeManifest, Any]] = []
    for manifest in paths.manifests:
        used_files = sum(proof.file_count for _, proof in proofs)
        used_bytes = sum(proof.total_bytes for _, proof in proofs)
        proof = dependencies.copy_tree(
            manifest.source_root,
            staging / manifest.replica_relative_root,
            store_proof=staging_proof,
            canonical_store=paths.canonical,
            repo_roots=(binding.repo_root,),
            limits=ModelCopyLimits(
                max_files=limits.max_files - used_files,
                max_file_bytes=limits.max_file_bytes,
                max_total_bytes=limits.max_total_bytes - used_bytes,
            ),
            expected_manifest=manifest.files,
        )
        proofs.append((manifest, proof))
        receipt.revalidate()
    return proofs


def _copy_and_publish_generation(
    *, paths: _MaterializationPaths, staging: Path, staging_proof: StoreProof,
    binding: CanonicalGenerationBinding, limits: QueryReplicaLimits,
    dependencies: _QueryReplicaTestDependencies, receipt: Any,
) -> tuple[dict[str, Any], list[tuple[ArtifactTreeManifest, Any]]]:
    receipt.revalidate()
    proofs = _copy_manifest_trees(
        paths=paths, staging=staging, staging_proof=staging_proof,
        binding=binding, limits=limits, dependencies=dependencies, receipt=receipt,
    )
    receipt.revalidate()
    payload = _descriptor_payload(
        binding=binding, canonical_store=paths.canonical,
        replica_root=paths.replica_root, generation_name=paths.generation_name,
        proofs=proofs, created_at=dependencies.now(),
    )
    publisher = dependencies.publish_directory or publish_directory_no_replace
    publisher(staging, paths.generation)
    receipt.revalidate()
    return payload, proofs


def _open_bound_receipt(
    paths: _MaterializationPaths,
    binding: CanonicalGenerationBinding,
    limits: QueryReplicaLimits,
    dependencies: _QueryReplicaTestDependencies,
) -> Any:
    return dependencies.open_receipt(
        path=binding.receipt_path, allowed_root=paths.canonical,
        expected_ssd_path=paths.canonical, expected_repo_root=binding.repo_root,
        expected_repo_head_sha=binding.repo_head_sha,
        expected_generation_id=binding.generation_id,
        expected_receipt_digest=binding.receipt_digest,
        max_bytes=limits.max_receipt_bytes,
    )


def _revalidate_retained_leases(leases: tuple[Any, Any]) -> None:
    for lease in leases:
        revalidate = getattr(lease, "revalidate_sentinel", None)
        if not callable(revalidate):
            _fail("QUERY_REPLICA_LEASE_CAPABILITY_INVALID")
        revalidate()


def _quarantine_failed_active(
    proof: PublishedPrivateJsonProof, limits: QueryReplicaLimits,
    dependencies: _QueryReplicaTestDependencies, cause: BaseException,
) -> None:
    try:
        orphan = quarantine_proven_private_json(
            proof, label="active", token=dependencies.orphan_token(),
            max_bytes=limits.max_descriptor_bytes,
        )
    except BaseException as exc:
        partial = getattr(exc, "orphan_proof", None)
        raise QueryReplicaError(
            "QUERY_REPLICA_ACTIVE_QUARANTINE_FAILED",
            orphan_relative_path=(
                partial.relative_path
                if type(partial) is QuarantinedPathProof else ""
            ),
            unsafe_relative_path=(
                partial.relative_path
                if type(partial) is QuarantinedPathProof else ACTIVE_DESCRIPTOR_NAME
            ),
        ) from exc
    raise QueryReplicaError(
        "QUERY_REPLICA_ACTIVE_QUARANTINED",
        orphan_relative_path=orphan.relative_path,
    ) from cause


def _materialize_under_retained_proofs(
    *, paths: _MaterializationPaths, staging: Path, staging_store: StoreProof,
    binding: CanonicalGenerationBinding, limits: QueryReplicaLimits,
    dependencies: _QueryReplicaTestDependencies,
) -> tuple[dict[str, Any], list[tuple[ArtifactTreeManifest, Any]], PublishedPrivateJsonProof]:
    published: PublishedPrivateJsonProof | None = None
    payload: dict[str, Any] | None = None
    try:
        with ExitStack() as stack:
            authority = stack.enter_context(
                dependencies.acquire_lease(authority_update_lock_path(paths.canonical))
            )
            maintenance = stack.enter_context(
                dependencies.acquire_lease(maintenance_lock_path(paths.canonical))
            )
            receipt = stack.enter_context(
                _open_bound_receipt(paths, binding, limits, dependencies)
            )
            payload, proofs = _copy_and_publish_generation(
                paths=paths, staging=staging, staging_proof=staging_store,
                binding=binding, limits=limits, dependencies=dependencies,
                receipt=receipt,
            )
            _revalidate_retained_leases((authority, maintenance))
            published = dependencies.publish_json(
                paths.active, payload, allowed_root=paths.replica_root,
                canonical_store=paths.canonical, repo_roots=(binding.repo_root,),
                max_bytes=limits.max_descriptor_bytes,
                expected_schema=QUERY_REPLICA_SCHEMA_VERSION,
                reject_absolute_paths=False,
                orphan_root=paths.orphans,
            )
            if not verify_proven_private_json(
                published, expected_payload=payload,
                max_bytes=limits.max_descriptor_bytes,
                expected_schema=QUERY_REPLICA_SCHEMA_VERSION,
            ):
                _fail("QUERY_REPLICA_ACTIVE_PROOF_INVALID")
            receipt.revalidate()
            _revalidate_retained_leases((authority, maintenance))
            return payload, proofs, published
    except BaseException as exc:
        if published is not None:
            _quarantine_failed_active(published, limits, dependencies, exc)
        raise


def _materialize_query_replica_for_test(
    *, canonical_store: Path | str, replica_root_proof: StoreProof,
    binding: CanonicalGenerationBinding, manifests: tuple[ArtifactTreeManifest, ...],
    limits: QueryReplicaLimits = QueryReplicaLimits(),
    dependencies: _QueryReplicaTestDependencies = _QueryReplicaTestDependencies(),
) -> QueryReplicaResult:
    """Internal dependency seam; production callers use sealed defaults."""

    paths = _prepare_materialization(
        canonical_store, replica_root_proof, binding, manifests, limits
    )
    staging_proof: OwnedDirectoryProof | None = None
    orphan_token = dependencies.orphan_token()
    try:
        staging = paths.replica_root / f".query-replica-stage-{orphan_token}"
        staging_store = create_isolated_store(
            staging, canonical_store=paths.canonical, repo_roots=(binding.repo_root,)
        )
        staging_proof = owned_directory(staging)
        payload, proofs, _ = _materialize_under_retained_proofs(
            paths=paths, staging=staging, staging_store=staging_store,
            binding=binding, limits=limits, dependencies=dependencies,
        )
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return QueryReplicaResult(
            generation_directory=paths.generation,
            active_descriptor=paths.active,
            descriptor_digest="sha256:" + hashlib.sha256(encoded + b"\n").hexdigest(),
            file_count=sum(proof.file_count for _, proof in proofs),
            total_bytes=sum(proof.total_bytes for _, proof in proofs),
        )
    except QueryReplicaError:
        raise
    except (
        AcceptanceGuardError, MaintenanceLockError, QueryReplicaGenerationError,
        OSError, ValueError,
    ) as exc:
        raise QueryReplicaError(str(exc)) from exc
    finally:
        try:
            quarantine_owned_staging(
                staging_proof, allowed_root=paths.replica_root,
                orphan_root=paths.orphans, token=orphan_token,
            )
        except BaseException as exc:
            raise QueryReplicaError(
                "QUERY_REPLICA_STAGING_QUARANTINE_FAILED",
                unsafe_relative_path=staging_proof.path.name if staging_proof else "",
            ) from exc


def materialize_query_replica(
    *, canonical_store: Path | str, replica_root_proof: StoreProof,
    binding: CanonicalGenerationBinding, manifests: tuple[ArtifactTreeManifest, ...],
    limits: QueryReplicaLimits = QueryReplicaLimits(),
) -> QueryReplicaResult:
    """Materialize one generation using only sealed verified primitives."""

    return _materialize_query_replica_for_test(
        canonical_store=canonical_store, replica_root_proof=replica_root_proof,
        binding=binding, manifests=manifests, limits=limits,
    )


__all__ = [
    "ACTIVE_DESCRIPTOR_NAME", "ArtifactTreeManifest", "CanonicalGenerationBinding",
    "QUERY_REPLICA_SCHEMA_VERSION", "QueryReplicaError", "QueryReplicaLimits",
    "QueryReplicaResult", "materialize_query_replica",
]
