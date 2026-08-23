"""Build an exact canonical generation plan for one narrow query replica."""

from __future__ import annotations

import os
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

from holo_index.embedding_space import (
    SENTENCE_TRANSFORMER_MODEL_ID,
    resolve_sentence_transformer_snapshot,
)
from holo_index.freshness_receipt import freshness_receipt_path
from holo_index.query_admission import rehydrate_canonical_freshness_proof
from holo_index.repository_state import read_repository_state, repository_root_digest
from holo_index.storage_contract import storage_path_identity

from modules.infrastructure.shared_utilities.runtime_artifact_confined_byte_reader import (
    ConfinedFileIdentity,
    confined_file_identity,
    secure_digest_confined_file_impl,
)

from .reddog_holoindex_acceptance_guards import _reject_link_components
from .reddog_holoindex_artifact_manifest import (
    ArtifactSnapshot,
    ExpectedArtifactFile,
    ModelCopyLimits,
    snapshot_artifact_files,
)
from .reddog_holoindex_query_replica_manifest import (
    ArtifactTreeManifest,
    CanonicalGenerationBinding,
    QueryReplicaLimits,
    validate_generation_binding,
    validate_query_replica_manifests,
)


class QueryReplicaPlanError(RuntimeError):
    """Stable fail-closed activation-plan error."""


def _fail(code: str) -> None:
    raise QueryReplicaPlanError(code)


@dataclass(frozen=True)
class QueryReplicaActivationPlan:
    binding: CanonicalGenerationBinding
    manifests: tuple[ArtifactTreeManifest, ...]


@dataclass(frozen=True)
class _PlanDependencies:
    state_reader: Callable[[Path], Any] = read_repository_state
    admission: Callable[..., Any] = rehydrate_canonical_freshness_proof
    model_resolver: Callable[..., Path | None] = (
        resolve_sentence_transformer_snapshot
    )
    snapshotter: Callable[[Path, ModelCopyLimits], ArtifactSnapshot] = (
        snapshot_artifact_files
    )
    digester: Callable[..., Any] = secure_digest_confined_file_impl
    binding_validator: Callable[..., Any] = validate_generation_binding
    manifest_validator: Callable[..., Any] = validate_query_replica_manifests


def _exact_head(value: object) -> str:
    if type(value) is not str or value != value.strip().lower():
        _fail("QUERY_REPLICA_PLAN_HEAD_INVALID")
    head = value
    if len(head) != 40 or any(character not in "0123456789abcdef" for character in head):
        _fail("QUERY_REPLICA_PLAN_HEAD_INVALID")
    return head


def _strict_directory(value: object, code: str) -> Path:
    if not (type(value) is str or isinstance(value, Path)):
        _fail(code)
    raw = str(value)
    if (
        not raw
        or raw != raw.strip()
        or unicodedata.normalize("NFC", raw) != raw
        or "\x00" in raw
    ):
        _fail(code)
    path = Path(raw)
    if not path.is_absolute():
        _fail(code)
    path = Path(os.path.abspath(path))
    _reject_link_components(path)
    if not path.is_dir():
        _fail(code)
    return path


def _relative_root(source: Path, canonical: Path) -> str:
    try:
        relative = source.relative_to(canonical).as_posix()
    except ValueError:
        _fail("QUERY_REPLICA_PLAN_SOURCE_OUTSIDE_CANONICAL")
    if not relative or relative == ".":
        _fail("QUERY_REPLICA_PLAN_SOURCE_INVALID")
    return relative


def _metadata_identity(metadata: os.stat_result) -> ConfinedFileIdentity:
    return confined_file_identity(metadata)


def _snapshot_identity(
    snapshot: ArtifactSnapshot, source: Path,
) -> tuple[tuple[object, ...], ...]:
    directories = tuple(
        (
            "directory",
            directory.relative_to(source).as_posix(),
            _metadata_identity(metadata),
        )
        for directory, metadata in sorted(
            snapshot.directories.items(), key=lambda item: item[0].as_posix().casefold()
        )
    )
    files = tuple(
        ("file", relative, _metadata_identity(metadata))
        for relative, _path, metadata in snapshot.files
    )
    return directories + files


def _digest_snapshot(
    snapshot: ArtifactSnapshot, canonical: Path, limits: QueryReplicaLimits,
    dependencies: _PlanDependencies,
) -> tuple[ExpectedArtifactFile, ...]:
    files: list[ExpectedArtifactFile] = []
    for relative, path, metadata in snapshot.files:
        proof = dependencies.digester(
            path,
            allowed_root=canonical,
            expected_identity=_metadata_identity(metadata),
            max_bytes=limits.max_file_bytes,
        )
        if (
            type(proof.size) is not int
            or type(proof.digest) is not str
            or proof.size != int(metadata.st_size)
            or proof.identity != _metadata_identity(metadata)
        ):
            _fail("QUERY_REPLICA_PLAN_SOURCE_CHANGED")
        files.append(ExpectedArtifactFile(relative, proof.size, proof.digest))
    return tuple(files)


def _revalidate_manifest_files(
    snapshot: ArtifactSnapshot, files: tuple[ExpectedArtifactFile, ...],
    canonical: Path, limits: QueryReplicaLimits, dependencies: _PlanDependencies,
) -> None:
    expected = {item.relative_path: item for item in files}
    for relative, path, metadata in snapshot.files:
        proof = dependencies.digester(
            path,
            allowed_root=canonical,
            expected_identity=_metadata_identity(metadata),
            max_bytes=limits.max_file_bytes,
        )
        item = expected.get(relative)
        if (
            item is None
            or type(proof.size) is not int
            or type(proof.digest) is not str
            or proof.identity != _metadata_identity(metadata)
            or proof.size != item.size
            or proof.digest != item.sha256
        ):
            _fail("QUERY_REPLICA_PLAN_SOURCE_CHANGED")


def _manifest_files(
    source: Path, *, canonical: Path, limits: QueryReplicaLimits,
    dependencies: _PlanDependencies,
) -> tuple[ExpectedArtifactFile, ...]:
    copy_limits = ModelCopyLimits(
        max_files=limits.max_files,
        max_file_bytes=limits.max_file_bytes,
        max_total_bytes=limits.max_total_bytes,
    )
    before = dependencies.snapshotter(source, copy_limits)
    files = _digest_snapshot(before, canonical, limits, dependencies)
    after = dependencies.snapshotter(source, copy_limits)
    if _snapshot_identity(before, source) != _snapshot_identity(after, source):
        _fail("QUERY_REPLICA_PLAN_SOURCE_CHANGED")
    _revalidate_manifest_files(after, files, canonical, limits, dependencies)
    try:
        final = dependencies.snapshotter(source, copy_limits)
    except Exception:
        _fail("QUERY_REPLICA_PLAN_SOURCE_CHANGED")
    if _snapshot_identity(after, source) != _snapshot_identity(final, source):
        _fail("QUERY_REPLICA_PLAN_SOURCE_CHANGED")
    return files


def _current_binding(
    repo: Path,
    canonical: Path,
    expected_head: str,
    dependencies: _PlanDependencies,
) -> tuple[CanonicalGenerationBinding, dict[str, str]]:
    state = dependencies.state_reader(repo)
    if getattr(state, "proven_clean", False) is not True:
        _fail("QUERY_REPLICA_PLAN_REPOSITORY_DIRTY")
    if type(getattr(state, "head_sha", None)) is not str or state.head_sha != expected_head:
        _fail("QUERY_REPLICA_PLAN_REPOSITORY_HEAD_MISMATCH")
    admitted = dependencies.admission(
        repo_root=repo,
        ssd_path=canonical,
        expected_repo_head_sha=expected_head,
    )
    raw_binding = getattr(admitted, "binding", None)
    if (
        getattr(admitted, "allowed", False) is not True
        or getattr(admitted, "freshness", "") != "CURRENT"
        or not isinstance(raw_binding, Mapping)
    ):
        _fail("QUERY_REPLICA_PLAN_FRESHNESS_NOT_CURRENT")
    field_names = (
        "freshness_generation_id",
        "freshness_receipt_digest",
        "repo_head_sha",
        "repo_root_digest",
    )
    if any(type(raw_binding.get(key)) is not str for key in field_names):
        _fail("QUERY_REPLICA_PLAN_FRESHNESS_BINDING_INVALID")
    fields = {key: raw_binding[key] for key in field_names}
    if fields["repo_head_sha"] != expected_head:
        _fail("QUERY_REPLICA_PLAN_FRESHNESS_BINDING_MISMATCH")
    binding = CanonicalGenerationBinding(
        repo_root=repo,
        repo_root_digest=repository_root_digest(repo),
        repo_head_sha=expected_head,
        receipt_path=freshness_receipt_path(canonical).resolve(strict=False),
        receipt_digest=fields["freshness_receipt_digest"],
        generation_id=fields["freshness_generation_id"],
        canonical_storage_identity=storage_path_identity(canonical),
    )
    dependencies.binding_validator(binding, canonical)
    if fields["repo_root_digest"] != binding.repo_root_digest:
        _fail("QUERY_REPLICA_PLAN_FRESHNESS_BINDING_MISMATCH")
    return binding, fields


def _resolve_plan_sources(
    canonical: Path, model_name: str, dependencies: _PlanDependencies,
) -> tuple[Path, Path]:
    model = dependencies.model_resolver(
        canonical / "models", model_name, preserve_source_path=True
    )
    if model is None:
        _fail("QUERY_REPLICA_PLAN_MODEL_UNAVAILABLE")
    return (
        _strict_directory(model, "QUERY_REPLICA_PLAN_MODEL_SOURCE_INVALID"),
        _strict_directory(
            canonical / "vectors" / "query_snapshots",
            "QUERY_REPLICA_PLAN_SNAPSHOT_SOURCE_INVALID",
        ),
    )


def _build_plan_manifests(
    model: Path, snapshots: Path, canonical: Path, limits: QueryReplicaLimits,
    dependencies: _PlanDependencies,
) -> tuple[ArtifactTreeManifest, ...]:
    return (
        ArtifactTreeManifest(
            "model", model, _relative_root(model, canonical),
            _manifest_files(
                model, canonical=canonical, limits=limits,
                dependencies=dependencies,
            ),
        ),
        ArtifactTreeManifest(
            "snapshots", snapshots, "vectors/query_snapshots",
            _manifest_files(
                snapshots, canonical=canonical, limits=limits,
                dependencies=dependencies,
            ),
        ),
    )


def _build_query_replica_activation_plan_for_test(
    *,
    canonical_repo_root: Path | str,
    canonical_store: Path | str,
    expected_repo_head_sha: str,
    model_name: str = SENTENCE_TRANSFORMER_MODEL_ID,
    limits: QueryReplicaLimits = QueryReplicaLimits(),
    dependencies: _PlanDependencies = _PlanDependencies(),
) -> QueryReplicaActivationPlan:
    repo = _strict_directory(
        canonical_repo_root, "QUERY_REPLICA_PLAN_REPOSITORY_ROOT_INVALID"
    )
    canonical = _strict_directory(
        canonical_store, "QUERY_REPLICA_PLAN_CANONICAL_ROOT_INVALID"
    )
    head = _exact_head(expected_repo_head_sha)
    if type(model_name) is not str or model_name != SENTENCE_TRANSFORMER_MODEL_ID:
        _fail("QUERY_REPLICA_PLAN_MODEL_NAME_INVALID")
    if type(limits) is not QueryReplicaLimits:
        _fail("QUERY_REPLICA_PLAN_LIMITS_INVALID")
    limits.validate()
    binding, original_fields = _current_binding(
        repo, canonical, head, dependencies
    )
    model, snapshots = _resolve_plan_sources(canonical, model_name, dependencies)
    manifests = _build_plan_manifests(
        model, snapshots, canonical, limits, dependencies
    )
    dependencies.manifest_validator(
        manifests,
        canonical,
        limits,
        generation_id=binding.generation_id,
    )
    final_binding, final_fields = _current_binding(
        repo, canonical, head, dependencies
    )
    if final_binding != binding or final_fields != original_fields:
        _fail("QUERY_REPLICA_PLAN_FRESHNESS_CHANGED")
    return QueryReplicaActivationPlan(binding=binding, manifests=manifests)


def build_query_replica_activation_plan(
    *,
    canonical_repo_root: Path | str,
    canonical_store: Path | str,
    expected_repo_head_sha: str,
    model_name: str = SENTENCE_TRANSFORMER_MODEL_ID,
    limits: QueryReplicaLimits = QueryReplicaLimits(),
) -> QueryReplicaActivationPlan:
    """Build and revalidate one exact model-plus-snapshot materialization plan."""

    try:
        return _build_query_replica_activation_plan_for_test(
            canonical_repo_root=canonical_repo_root,
            canonical_store=canonical_store,
            expected_repo_head_sha=expected_repo_head_sha,
            model_name=model_name,
            limits=limits,
        )
    except QueryReplicaPlanError:
        raise
    except Exception as exc:
        raise QueryReplicaPlanError("QUERY_REPLICA_PLAN_BUILD_FAILED") from exc


__all__ = [
    "QueryReplicaActivationPlan",
    "QueryReplicaPlanError",
    "build_query_replica_activation_plan",
]
