"""Publish and load generation-bound immutable Holo collection snapshots."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import stat
import tempfile
import unicodedata
from pathlib import Path
from typing import Any, Mapping

from holo_index.embedding_space import (
    CANONICAL_INDEX_BACKEND,
    SENTENCE_TRANSFORMER_CONTRACT,
    SENTENCE_TRANSFORMER_MODEL_ID,
    embedding_artifact_digest,
    embedding_space_fingerprint,
    resolve_sentence_transformer_snapshot,
)
from holo_index.freshness_receipt import (
    BASELINE_QUERY_COLLECTIONS,
    COLLECTION_ATTRS,
    HoloIndexFreshnessReceipt,
    paged_collection_snapshot,
)

from .holo_query_snapshot_codec import (
    EncodedCollectionSnapshot,
    SnapshotLimits,
    encode_collection_snapshot,
    load_collection_snapshot,
)
from .holo_query_snapshot_contract import SET_MANIFEST


SCHEMA_VERSION = "holoindex_query_snapshot_set.v1"
SNAPSHOT_DIRECTORY = "query_snapshots"
MAX_SNAPSHOT_SET_BYTES = 384 * 1024 * 1024
_ARTIFACT_KEYS = ("manifest", "rows", "vectors")
_ARTIFACT_SUFFIXES = {
    "manifest": "manifest.json", "rows": "rows.jsonl", "vectors": "vectors.f32",
}
_DIGEST = re.compile(r"sha256:[0-9a-f]{64}")
_WINDOWS_REPARSE_POINT = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)


class QuerySnapshotStoreError(RuntimeError):
    """Stable fail-closed snapshot publication/loading error."""


def _fail(code: str) -> None:
    raise QuerySnapshotStoreError(f"HOLO_QUERY_SNAPSHOT_SET_{code}")


def _json_bytes(value: Any) -> bytes:
    try:
        return (
            json.dumps(
                value, sort_keys=True, separators=(",", ":"),
                ensure_ascii=True, allow_nan=False,
            ).encode("ascii")
            + b"\n"
        )
    except (TypeError, ValueError, OverflowError) as exc:
        raise QuerySnapshotStoreError(
            "HOLO_QUERY_SNAPSHOT_SET_MANIFEST_INVALID"
        ) from exc


def _digest(payload: bytes) -> str:
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _is_link(path: Path, metadata: os.stat_result) -> bool:
    attributes = int(getattr(metadata, "st_file_attributes", 0) or 0)
    return stat.S_ISLNK(metadata.st_mode) or bool(
        attributes & _WINDOWS_REPARSE_POINT
    )


def _validated_directory(path: Path | str) -> Path:
    """Return one absolute directory only when every component is non-link."""

    target = Path(path).absolute()
    current = Path(target.anchor)
    metadata: os.stat_result | None = None
    try:
        for component in target.parts:
            if component == target.anchor:
                continue
            current /= component
            metadata = os.lstat(current)
            if _is_link(current, metadata):
                _fail("ROOT_INVALID")
    except OSError:
        _fail("ROOT_INVALID")
    if metadata is None or not stat.S_ISDIR(metadata.st_mode):
        _fail("ROOT_INVALID")
    return target


def _identity(metadata: os.stat_result) -> tuple[int, int, int, int]:
    return (
        int(metadata.st_dev), int(metadata.st_ino),
        int(metadata.st_size), int(metadata.st_mtime_ns),
    )


def _artifact_name(collection: str, kind: str) -> str:
    return f"{collection}.{_ARTIFACT_SUFFIXES[kind]}"


def _write_bytes(path: Path, payload: bytes) -> None:
    with path.open("xb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())


def _artifact_entry(path: Path, payload: bytes) -> dict[str, Any]:
    return {"path": path.name, "bytes": len(payload), "sha256": _digest(payload)}


def _collection_metric(collection: Any) -> str:
    configuration = getattr(collection, "configuration", None)
    hnsw = configuration.get("hnsw") if isinstance(configuration, Mapping) else None
    metric = hnsw.get("space") if isinstance(hnsw, Mapping) else None
    if metric not in {"l2", "cosine", "ip"}:
        _fail("METRIC_INVALID")
    return str(metric)


def _embedding_identity(
    entry: Any, *, models_path: Path,
) -> dict[str, str]:
    snapshot = resolve_sentence_transformer_snapshot(
        models_path, "all-MiniLM-L6-v2"
    )
    artifact_digest = embedding_artifact_digest(snapshot)
    fingerprint = embedding_space_fingerprint(
        backend=CANONICAL_INDEX_BACKEND,
        model_id=SENTENCE_TRANSFORMER_MODEL_ID,
        artifact_digest=artifact_digest,
        encoder_contract=SENTENCE_TRANSFORMER_CONTRACT,
    )
    if (
        entry.embedding_backend != CANONICAL_INDEX_BACKEND
        or entry.embedding_model != SENTENCE_TRANSFORMER_MODEL_ID
        or entry.embedding_space_fingerprint != fingerprint
    ):
        _fail("EMBEDDING_IDENTITY_MISMATCH")
    return {
        "backend": CANONICAL_INDEX_BACKEND,
        "model_id": SENTENCE_TRANSFORMER_MODEL_ID,
        "artifact_digest": artifact_digest,
        "encoder_contract": SENTENCE_TRANSFORMER_CONTRACT,
        "space_fingerprint": fingerprint,
    }


def _nfc_snapshot_value(value: Any, *, depth: int = 0) -> Any:
    """Normalize persisted text while rejecting key collisions fail closed."""
    if depth > 64:
        return value
    if type(value) is str:
        return unicodedata.normalize("NFC", value)
    if type(value) is list:
        return [_nfc_snapshot_value(item, depth=depth + 1) for item in value]
    if type(value) is dict:
        normalized: dict[Any, Any] = {}
        for key, item in value.items():
            normalized_key = (
                unicodedata.normalize("NFC", key) if type(key) is str else key
            )
            if normalized_key in normalized:
                _fail("NORMALIZATION_COLLISION")
            normalized[normalized_key] = _nfc_snapshot_value(
                item, depth=depth + 1
            )
        return normalized
    return value


def _encode_collection(
    holo: Any, entry: Any, *, limits: SnapshotLimits,
) -> EncodedCollectionSnapshot:
    collection = getattr(holo, COLLECTION_ATTRS[entry.name], None)
    if collection is None or entry.verification != "PASS" or entry.count <= 0:
        _fail("COLLECTION_UNAVAILABLE")
    snapshot = paged_collection_snapshot(collection, count=entry.count)
    ids = snapshot["ids"]
    documents = snapshot["documents"]
    metadatas = snapshot["metadatas"]
    embeddings = snapshot["embeddings"]
    if not all(len(values) == entry.count for values in snapshot.values()):
        _fail("COLLECTION_COUNT_MISMATCH")
    rows = [
        {
            "id": str(item_id),
            "document": _nfc_snapshot_value(document),
            "metadata": _nfc_snapshot_value(metadata),
        }
        for item_id, document, metadata in zip(ids, documents, metadatas)
    ]
    metadata = getattr(collection, "metadata", None)
    return encode_collection_snapshot(
        collection_name=entry.name,
        rows=rows,
        embeddings=embeddings,
        metric=_collection_metric(collection),
        embedding_identity=_embedding_identity(entry, models_path=holo.models_path),
        collection_metadata=metadata if isinstance(metadata, dict) else {},
        limits=limits,
    )


def _stage_snapshot_set(
    holo: Any, receipt: HoloIndexFreshnessReceipt, staging: Path,
    *, limits: SnapshotLimits,
) -> tuple[dict[str, Any], set[str]]:
    baseline = [
        entry for entry in receipt.collections
        if entry.name in BASELINE_QUERY_COLLECTIONS
    ]
    entries = {entry.name: entry for entry in baseline}
    if len(baseline) != len(BASELINE_QUERY_COLLECTIONS) or set(entries) != set(
        BASELINE_QUERY_COLLECTIONS
    ):
        _fail("BASELINE_INCOMPLETE")
    collections: dict[str, Any] = {}
    filenames: set[str] = {SET_MANIFEST}
    total_bytes = 0
    for name in sorted(BASELINE_QUERY_COLLECTIONS):
        encoded = _encode_collection(holo, entries[name], limits=limits)
        payloads = {
            "manifest": encoded.manifest,
            "rows": encoded.rows,
            "vectors": encoded.vectors,
        }
        artifacts: dict[str, Any] = {}
        for kind in _ARTIFACT_KEYS:
            path = staging / _artifact_name(name, kind)
            total_bytes += len(payloads[kind])
            if total_bytes > MAX_SNAPSHOT_SET_BYTES:
                _fail("TOTAL_SIZE_BOUND")
            _write_bytes(path, payloads[kind])
            artifacts[kind] = _artifact_entry(path, payloads[kind])
            filenames.add(path.name)
        collections[name] = artifacts
    payload = {
        "schema_version": SCHEMA_VERSION,
        "generation_id": receipt.generation_id,
        "collections": collections,
    }
    _write_bytes(staging / SET_MANIFEST, _json_bytes(payload))
    return payload, filenames


def _prepare_target(target: Path, expected: set[str]) -> None:
    target.mkdir(mode=0o700, exist_ok=True)
    metadata = os.lstat(target)
    if not stat.S_ISDIR(metadata.st_mode) or _is_link(target, metadata):
        _fail("ROOT_INVALID")
    observed = {entry.name for entry in os.scandir(target)}
    if not observed.issubset(expected):
        _fail("UNEXPECTED_ARTIFACT")


def publish_query_snapshot_set(
    holo: Any,
    receipt: HoloIndexFreshnessReceipt,
    *,
    ssd_path: Path | str,
    limits: SnapshotLimits = SnapshotLimits(),
) -> Path:
    """Publish all baseline collection snapshots before the PASS receipt."""

    limits.validate()
    if _DIGEST.fullmatch(receipt.generation_id) is None:
        _fail("GENERATION_INVALID")
    ssd = Path(ssd_path).resolve(strict=True)
    staging = Path(tempfile.mkdtemp(prefix=".query-snapshot-", dir=ssd))
    target = ssd / "vectors" / SNAPSHOT_DIRECTORY
    try:
        _payload, filenames = _stage_snapshot_set(
            holo, receipt, staging, limits=limits
        )
        _prepare_target(target, filenames)
        for filename in sorted(filenames.difference({SET_MANIFEST})):
            os.replace(staging / filename, target / filename)
        os.replace(staging / SET_MANIFEST, target / SET_MANIFEST)
        return target
    except QuerySnapshotStoreError:
        raise
    except (OSError, TypeError, ValueError) as exc:
        raise QuerySnapshotStoreError(
            "HOLO_QUERY_SNAPSHOT_SET_PUBLICATION_FAILED"
        ) from exc
    finally:
        shutil.rmtree(staging, ignore_errors=True)


class _DuplicateKey(ValueError):
    pass


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateKey(key)
        result[key] = value
    return result


def _read_regular(path: Path, *, ceiling: int) -> bytes:
    before = os.lstat(path)
    if (
        not stat.S_ISREG(before.st_mode)
        or _is_link(path, before)
        or before.st_nlink != 1
        or not 0 < before.st_size <= ceiling
    ):
        _fail("ARTIFACT_INVALID")
    payload = path.read_bytes()
    after = os.lstat(path)
    if _identity(before) != _identity(after) or len(payload) != before.st_size:
        _fail("ARTIFACT_CHANGED")
    return payload


def _decode_set_manifest(payload: bytes, *, limits: SnapshotLimits) -> dict[str, Any]:
    try:
        value = json.loads(
            payload.decode("ascii"), object_pairs_hook=_strict_object,
            parse_constant=lambda _value: (_ for _ in ()).throw(ValueError()),
        )
    except (UnicodeError, ValueError, json.JSONDecodeError, RecursionError) as exc:
        raise QuerySnapshotStoreError(
            "HOLO_QUERY_SNAPSHOT_SET_MANIFEST_INVALID"
        ) from exc
    if type(value) is not dict or _json_bytes(value) != payload:
        _fail("MANIFEST_INVALID")
    if (
        set(value) != {"schema_version", "generation_id", "collections"}
        or value["schema_version"] != SCHEMA_VERSION
        or _DIGEST.fullmatch(value["generation_id"]) is None
        or type(value["collections"]) is not dict
        or set(value["collections"]) != set(BASELINE_QUERY_COLLECTIONS)
    ):
        _fail("MANIFEST_SCHEMA_INVALID")
    return value


def _validated_artifact(
    root: Path, collection: str, kind: str, value: Any,
    *, limits: SnapshotLimits,
) -> bytes:
    expected, expected_bytes, expected_digest = _artifact_descriptor(
        collection, kind, value, limits=limits
    )
    ceiling = {
        "manifest": limits.max_manifest_bytes,
        "rows": limits.max_rows_bytes,
        "vectors": limits.max_vector_bytes,
    }[kind]
    payload = _read_regular(root / expected, ceiling=ceiling)
    if len(payload) != expected_bytes or _digest(payload) != expected_digest:
        _fail("ARTIFACT_BINDING_MISMATCH")
    return payload


def _artifact_descriptor(
    collection: str, kind: str, value: Any, *, limits: SnapshotLimits,
) -> tuple[str, int, str]:
    expected = _artifact_name(collection, kind)
    ceiling = {
        "manifest": limits.max_manifest_bytes,
        "rows": limits.max_rows_bytes,
        "vectors": limits.max_vector_bytes,
    }[kind]
    if (
        type(value) is not dict
        or set(value) != {"path", "bytes", "sha256"}
        or value.get("path") != expected
        or type(value.get("bytes")) is not int
        or not 0 < value["bytes"] <= ceiling
        or type(value.get("sha256")) is not str
        or _DIGEST.fullmatch(value["sha256"]) is None
    ):
        _fail("ARTIFACT_BINDING_INVALID")
    return expected, value["bytes"], value["sha256"]


def _preflight_set_size(manifest: Mapping[str, Any], limits: SnapshotLimits) -> None:
    total = 0
    ceilings = {
        "manifest": limits.max_manifest_bytes,
        "rows": limits.max_rows_bytes,
        "vectors": limits.max_vector_bytes,
    }
    for name in BASELINE_QUERY_COLLECTIONS:
        artifacts = manifest["collections"].get(name)
        if type(artifacts) is not dict or set(artifacts) != set(_ARTIFACT_KEYS):
            _fail("ARTIFACT_SET_INVALID")
        for kind, ceiling in ceilings.items():
            value = artifacts[kind]
            size = value.get("bytes") if type(value) is dict else None
            if type(size) is not int or not 0 < size <= ceiling:
                _fail("ARTIFACT_BINDING_INVALID")
            total += size
            if total > MAX_SNAPSHOT_SET_BYTES:
                _fail("TOTAL_SIZE_BOUND")


class _EmptyCollection:
    name = "navigation_work_ledger"
    metadata: dict[str, Any] = {}

    def count(self) -> int:
        return 0

    def get(self, *args: Any, include: Any = None, **kwargs: Any) -> dict[str, Any]:
        fields = tuple(include or ("documents", "metadatas"))
        return {"ids": [], **{field: [] for field in fields}}

    def query(self, *args: Any, include: Any = None, **kwargs: Any) -> dict[str, Any]:
        fields = tuple(include or ("documents", "metadatas", "distances"))
        return {"ids": [[]], **{field: [[]] for field in fields}}


class ImmutableSnapshotClient:
    """Minimal Chroma client surface backed only by verified snapshot bytes."""

    def __init__(self, generation_id: str, collections: Mapping[str, Any]) -> None:
        self.generation_id = generation_id
        self._collections = dict(collections)

    def get_collection(self, name: str) -> Any:
        if name == "navigation_work_ledger":
            return _EmptyCollection()
        try:
            return self._collections[name]
        except KeyError as exc:
            raise KeyError("HOLO_QUERY_SNAPSHOT_SET_COLLECTION_MISSING") from exc

    def close(self) -> None:
        """Release owned resources; immutable snapshots retain no open handles."""


def validate_query_snapshot_set_manifest(
    snapshot_root: Path | str,
    *,
    expected_generation_id: str,
    expected_artifact_bindings: Mapping[str, tuple[int, str]] | None = None,
    limits: SnapshotLimits = SnapshotLimits(),
) -> tuple[str, ...]:
    """Validate the sealed set topology and generation without loading vectors."""

    limits.validate()
    if (
        type(expected_generation_id) is not str
        or _DIGEST.fullmatch(expected_generation_id) is None
    ):
        _fail("GENERATION_INVALID")
    root = _validated_directory(snapshot_root)
    payload = _read_regular(root / SET_MANIFEST, ceiling=limits.max_manifest_bytes)
    manifest = _decode_set_manifest(payload, limits=limits)
    _preflight_set_size(manifest, limits)
    if manifest["generation_id"] != expected_generation_id:
        _fail("GENERATION_MISMATCH")
    expected = {SET_MANIFEST}
    observed_bindings = {SET_MANIFEST: (len(payload), _digest(payload))}
    for name in sorted(BASELINE_QUERY_COLLECTIONS):
        artifacts = manifest["collections"].get(name)
        if type(artifacts) is not dict or set(artifacts) != set(_ARTIFACT_KEYS):
            _fail("ARTIFACT_SET_INVALID")
        for kind in _ARTIFACT_KEYS:
            artifact, size, digest = _artifact_descriptor(
                name, kind, artifacts[kind], limits=limits
            )
            expected.add(artifact)
            observed_bindings[artifact] = (size, digest)
    if {entry.name for entry in os.scandir(root)} != expected:
        _fail("UNEXPECTED_ARTIFACT")
    if expected_artifact_bindings is not None:
        if (
            not isinstance(expected_artifact_bindings, Mapping)
            or any(
                type(path) is not str
                or type(binding) is not tuple
                or len(binding) != 2
                or type(binding[0]) is not int
                or type(binding[1]) is not str
                for path, binding in expected_artifact_bindings.items()
            )
            or dict(expected_artifact_bindings) != observed_bindings
        ):
            _fail("ARTIFACT_BINDING_MISMATCH")
    return tuple(sorted(expected, key=lambda value: unicodedata.normalize("NFC", value).casefold()))


def open_query_snapshot_client(
    vector_path: Path | str,
    *,
    limits: SnapshotLimits = SnapshotLimits(),
) -> ImmutableSnapshotClient:
    """Load the exact immutable query set without opening Chroma or SQLite."""

    limits.validate()
    root = _validated_directory(Path(vector_path).absolute() / SNAPSHOT_DIRECTORY)
    manifest_bytes = _read_regular(root / SET_MANIFEST, ceiling=limits.max_manifest_bytes)
    manifest = _decode_set_manifest(manifest_bytes, limits=limits)
    _preflight_set_size(manifest, limits)
    expected = {SET_MANIFEST}
    collections: dict[str, Any] = {}
    for name in sorted(BASELINE_QUERY_COLLECTIONS):
        artifacts = manifest["collections"][name]
        if type(artifacts) is not dict or set(artifacts) != set(_ARTIFACT_KEYS):
            _fail("ARTIFACT_SET_INVALID")
        buffers = {
            kind: _validated_artifact(
                root, name, kind, artifacts[kind], limits=limits
            )
            for kind in _ARTIFACT_KEYS
        }
        expected.update(value["path"] for value in artifacts.values())
        collection = load_collection_snapshot(
            buffers["manifest"], buffers["rows"], buffers["vectors"],
            limits=limits,
        )
        if collection.name != name:
            _fail("COLLECTION_NAME_MISMATCH")
        collections[name] = collection
    if {entry.name for entry in os.scandir(root)} != expected:
        _fail("UNEXPECTED_ARTIFACT")
    return ImmutableSnapshotClient(manifest["generation_id"], collections)


__all__ = [
    "ImmutableSnapshotClient", "QuerySnapshotStoreError",
    "open_query_snapshot_client", "publish_query_snapshot_set",
    "validate_query_snapshot_set_manifest",
]
