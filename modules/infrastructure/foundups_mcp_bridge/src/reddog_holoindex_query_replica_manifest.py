"""Exact generation-bound artifact policy for RedDog query replicas."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import unicodedata

from holo_index.freshness_receipt import BASELINE_QUERY_COLLECTIONS, freshness_receipt_path
from holo_index.repository_state import repository_root_digest
from holo_index.storage_contract import storage_path_identity

from .holo_query_snapshot_contract import SET_MANIFEST
from .reddog_holoindex_acceptance_guards import (
    ExpectedArtifactFile,
    _normalized,
    _relative_to,
)


_HEX = frozenset("0123456789abcdef")
_SNAPSHOT_SUFFIXES = ("manifest.json", "rows.jsonl", "vectors.f32")
_LEGACY_HNSW_CORE = frozenset({
    "data_level0.bin", "header.bin", "length.bin", "link_lists.bin",
})
_LEGACY_HNSW_MARKERS = _LEGACY_HNSW_CORE | {"index_metadata.pickle"}


class QueryReplicaError(RuntimeError):
    """Stable fail-closed materializer error."""

    def __init__(
        self, code: str, *, orphan_relative_path: str = "",
        unsafe_relative_path: str = "",
    ) -> None:
        super().__init__(code)
        self.orphan_relative_path = orphan_relative_path
        self.unsafe_relative_path = unsafe_relative_path


def fail_query_replica(code: str) -> None:
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
    max_descriptor_bytes: int = 4_194_304

    def validate(self) -> None:
        values = (
            self.max_files, self.max_file_bytes, self.max_total_bytes,
            self.max_path_bytes, self.max_receipt_bytes,
            self.max_descriptor_bytes,
        )
        if any(type(value) is not int or value <= 0 for value in values):
            fail_query_replica("QUERY_REPLICA_LIMIT_INVALID")


@dataclass(frozen=True)
class QueryReplicaResult:
    generation_directory: Path
    active_descriptor: Path
    descriptor_digest: str
    file_count: int
    total_bytes: int


def query_snapshot_artifact_names() -> tuple[str, ...]:
    names = {SET_MANIFEST}
    for collection in BASELINE_QUERY_COLLECTIONS:
        names.update(
            f"{collection}.{suffix}" for suffix in _SNAPSHOT_SUFFIXES
        )
    return tuple(sorted(names, key=str.casefold))


def _coherent_model_artifact_paths_complete(paths: set[str]) -> bool:
    model_paths = {path for path in paths if path.startswith("models/")}
    markers = tuple(
        path for path in model_paths
        if unicodedata.normalize("NFC", path.rsplit("/", 1)[-1]).casefold()
        == "modules.json"
    )
    if len(markers) != 1 or not markers[0].endswith("/modules.json"):
        return False
    root = markers[0].removesuffix("/modules.json")
    required = {
        f"{root}/modules.json", f"{root}/config.json",
        f"{root}/model.safetensors",
    }
    tokenizer = {f"{root}/tokenizer.json", f"{root}/vocab.txt"}
    return bool(required <= model_paths and tokenizer & model_paths and all(
        path.startswith(f"{root}/") for path in model_paths
    ))


def _legacy_hnsw_artifact_paths_complete(vector_paths: set[str]) -> bool:
    segments: dict[str, set[str]] = {}
    for path in vector_paths:
        parts = path.split("/")
        if (
            len(parts) == 3
            and parts[0] == "vectors"
            and parts[1] != "query_snapshots"
            and parts[2] in _LEGACY_HNSW_MARKERS
        ):
            segments.setdefault(parts[1], set()).add(parts[2])
    return bool(segments) and all(
        _LEGACY_HNSW_CORE <= artifacts for artifacts in segments.values()
    )


def query_snapshot_runtime_artifact_paths_complete(paths: set[str]) -> bool:
    """Require the exact model plus modern 22-file vector closure."""

    snapshots = {
        f"vectors/query_snapshots/{name}"
        for name in query_snapshot_artifact_names()
    }
    vector_paths = {path for path in paths if path.startswith("vectors/")}
    return bool(
        _coherent_model_artifact_paths_complete(paths)
        and vector_paths == snapshots
    )


def runtime_artifact_paths_complete(paths: set[str]) -> bool:
    """Admit the modern runtime or a complete former Chroma/HNSW closure."""

    vector_paths = {path for path in paths if path.startswith("vectors/")}
    return bool(
        query_snapshot_runtime_artifact_paths_complete(paths)
        or (
            _coherent_model_artifact_paths_complete(paths)
            and "vectors/chroma.sqlite3" in vector_paths
            and _legacy_hnsw_artifact_paths_complete(vector_paths)
        )
    )


def _valid_digest(value: str) -> bool:
    return (
        type(value) is str
        and len(value) == 71
        and value.startswith("sha256:")
        and set(value[7:]) <= _HEX
    )


def validate_generation_binding(
    binding: CanonicalGenerationBinding, canonical_store: Path,
) -> None:
    repo_root = _normalized(binding.repo_root)
    expected_receipt = freshness_receipt_path(canonical_store).resolve(strict=False)
    if not isinstance(binding.receipt_path, Path):
        fail_query_replica("QUERY_REPLICA_RECEIPT_PATH_NONCANONICAL")
    receipt = _normalized(binding.receipt_path)
    if binding.repo_root_digest != repository_root_digest(repo_root):
        fail_query_replica("QUERY_REPLICA_REPO_ROOT_DIGEST_MISMATCH")
    if (
        type(binding.repo_head_sha) is not str
        or len(binding.repo_head_sha) != 40
        or set(binding.repo_head_sha) > _HEX
    ):
        fail_query_replica("QUERY_REPLICA_REPO_HEAD_INVALID")
    if not _valid_digest(binding.receipt_digest) or not _valid_digest(binding.generation_id):
        fail_query_replica("QUERY_REPLICA_GENERATION_BINDING_INVALID")
    if (
        receipt != expected_receipt
        or binding.receipt_path != expected_receipt
        or str(binding.receipt_path) != str(expected_receipt)
    ):
        fail_query_replica("QUERY_REPLICA_RECEIPT_PATH_NONCANONICAL")
    if binding.canonical_storage_identity != storage_path_identity(canonical_store):
        fail_query_replica("QUERY_REPLICA_STORAGE_IDENTITY_MISMATCH")


def _validate_source(
    manifest: ArtifactTreeManifest, canonical_store: Path, relative_root: Path,
) -> None:
    source = _normalized(manifest.source_root)
    expected = canonical_store.joinpath(relative_root).resolve(strict=False)
    if source != expected or not _relative_to(source, canonical_store):
        fail_query_replica("QUERY_REPLICA_SOURCE_PATH_INVALID")


def _validate_model(manifest: ArtifactTreeManifest, relative_root: Path) -> None:
    if relative_root.parts[0] != "models":
        fail_query_replica("QUERY_REPLICA_MODEL_ROOT_INVALID")
    paths = {item.relative_path for item in manifest.files}
    markers = {
        path for path in paths
        if unicodedata.normalize("NFC", Path(path).name).casefold()
        == "modules.json"
    }
    if markers != {"modules.json"}:
        fail_query_replica("QUERY_REPLICA_MODEL_ROOT_AMBIGUOUS")
    required = {"modules.json", "config.json", "model.safetensors"}
    if not required <= paths or not ({"tokenizer.json", "vocab.txt"} & paths):
        fail_query_replica("QUERY_REPLICA_MODEL_SNAPSHOT_INCOMPLETE")


def _canonical_relative_root(raw_root: object) -> Path:
    if type(raw_root) is not str or not raw_root or "\\" in raw_root:
        fail_query_replica("QUERY_REPLICA_ARTIFACT_ROOT_INVALID")
    relative_root = Path(raw_root)
    if (
        unicodedata.normalize("NFC", raw_root) != raw_root
        or relative_root.drive
        or relative_root.is_absolute()
        or ".." in relative_root.parts
        or not relative_root.parts
        or relative_root.as_posix() != raw_root
    ):
        fail_query_replica("QUERY_REPLICA_ARTIFACT_ROOT_INVALID")
    return relative_root


def _canonical_artifact_path(raw_path: object) -> str:
    if type(raw_path) is not str or not raw_path or "\\" in raw_path:
        fail_query_replica("QUERY_REPLICA_ARTIFACT_PATH_INVALID")
    relative = Path(raw_path)
    if (
        unicodedata.normalize("NFC", raw_path) != raw_path
        or relative.drive
        or relative.is_absolute()
        or ".." in relative.parts
        or not relative.parts
        or relative.as_posix() != raw_path
    ):
        fail_query_replica("QUERY_REPLICA_ARTIFACT_PATH_INVALID")
    return raw_path


def _validate_manifest_files(
    manifest: ArtifactTreeManifest, relative_root: Path,
    limits: QueryReplicaLimits,
) -> tuple[int, int]:
    if type(manifest.files) is not tuple or not manifest.files:
        fail_query_replica("QUERY_REPLICA_ARTIFACT_MANIFEST_INVALID")
    keys: list[str] = []
    total_bytes = 0
    for item in manifest.files:
        if type(item) is not ExpectedArtifactFile:
            fail_query_replica("QUERY_REPLICA_ARTIFACT_MANIFEST_INVALID")
        relative = _canonical_artifact_path(item.relative_path)
        if (
            type(item.size) is not int
            or item.size < 0
            or not _valid_digest(item.sha256)
        ):
            fail_query_replica("QUERY_REPLICA_ARTIFACT_MANIFEST_INVALID")
        if item.size > limits.max_file_bytes:
            fail_query_replica("QUERY_REPLICA_FILE_SIZE_BOUND")
        full_relative = f"{relative_root.as_posix()}/{relative}"
        if len(full_relative.encode("utf-8")) > limits.max_path_bytes:
            fail_query_replica("QUERY_REPLICA_PATH_BOUND")
        keys.append(unicodedata.normalize("NFC", relative).casefold())
        total_bytes += item.size
        if total_bytes > limits.max_total_bytes:
            fail_query_replica("QUERY_REPLICA_TOTAL_SIZE_BOUND")
    if keys != sorted(keys):
        fail_query_replica("QUERY_REPLICA_ARTIFACT_MANIFEST_ORDER_INVALID")
    if len(set(keys)) != len(keys):
        fail_query_replica("QUERY_REPLICA_ARTIFACT_MANIFEST_ALIAS")
    return len(manifest.files), total_bytes


def _validate_snapshots(
    manifest: ArtifactTreeManifest, relative_root: Path, generation_id: str,
) -> None:
    # Materialization runs in the Holo maintenance environment. Keep its
    # NumPy-backed snapshot codec out of RedDog's stdlib-only query import path.
    from .holo_query_snapshot_store import (
        QuerySnapshotStoreError,
        validate_query_snapshot_set_manifest,
    )

    if relative_root.as_posix() != "vectors/query_snapshots":
        fail_query_replica("QUERY_REPLICA_SNAPSHOT_ROOT_INVALID")
    expected = query_snapshot_artifact_names()
    if {item.relative_path for item in manifest.files} != set(expected):
        fail_query_replica("QUERY_REPLICA_SNAPSHOT_SET_INCOMPLETE")
    try:
        expected_bindings = {
            item.relative_path: (item.size, item.sha256)
            for item in manifest.files
        }
        observed = validate_query_snapshot_set_manifest(
            manifest.source_root,
            expected_generation_id=generation_id,
            expected_artifact_bindings=expected_bindings,
        )
    except QuerySnapshotStoreError as exc:
        code = str(exc)
        if code.endswith("GENERATION_MISMATCH"):
            fail_query_replica("QUERY_REPLICA_SNAPSHOT_GENERATION_MISMATCH")
        fail_query_replica("QUERY_REPLICA_SNAPSHOT_SET_INVALID")
    if observed != expected:
        fail_query_replica("QUERY_REPLICA_SNAPSHOT_SET_INCOMPLETE")


def validate_query_replica_manifests(
    manifests: tuple[ArtifactTreeManifest, ...], canonical_store: Path,
    limits: QueryReplicaLimits, *, generation_id: str,
) -> tuple[ArtifactTreeManifest, ...]:
    if (
        type(manifests) is not tuple
        or any(type(manifest) is not ArtifactTreeManifest for manifest in manifests)
    ):
        fail_query_replica("QUERY_REPLICA_ARTIFACT_SET_INVALID")
    if tuple(sorted(manifests, key=lambda item: item.logical_name)) != manifests:
        fail_query_replica("QUERY_REPLICA_MANIFEST_ORDER_INVALID")
    if tuple(item.logical_name for item in manifests) != ("model", "snapshots"):
        fail_query_replica("QUERY_REPLICA_ARTIFACT_SET_INVALID")
    total_files = total_bytes = 0
    for manifest in manifests:
        relative_root = _canonical_relative_root(manifest.replica_relative_root)
        file_count, manifest_bytes = _validate_manifest_files(
            manifest, relative_root, limits
        )
        _validate_source(manifest, canonical_store, relative_root)
        if manifest.logical_name == "model":
            _validate_model(manifest, relative_root)
        else:
            _validate_snapshots(manifest, relative_root, generation_id)
        total_files += file_count
        total_bytes += manifest_bytes
    if total_files > limits.max_files:
        fail_query_replica("QUERY_REPLICA_FILE_COUNT_BOUND")
    if total_bytes > limits.max_total_bytes:
        fail_query_replica("QUERY_REPLICA_TOTAL_SIZE_BOUND")
    return manifests


__all__ = [
    "ArtifactTreeManifest", "CanonicalGenerationBinding", "QueryReplicaError",
    "QueryReplicaLimits", "QueryReplicaResult",
    "fail_query_replica", "query_snapshot_artifact_names",
    "query_snapshot_runtime_artifact_paths_complete",
    "runtime_artifact_paths_complete",
    "validate_generation_binding", "validate_query_replica_manifests",
]
