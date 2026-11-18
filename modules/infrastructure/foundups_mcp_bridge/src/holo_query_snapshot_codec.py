"""Deterministic path-free codec for one immutable Holo collection snapshot."""

from __future__ import annotations

import hashlib
import json
import math
import re
import unicodedata
from typing import Any, Mapping, Sequence

import numpy as np

from holo_index.freshness_receipt import _canonical_snapshot_value

from .holo_query_snapshot_contract import (
    EncodedCollectionSnapshot,
    METRICS,
    SCHEMA_VERSION,
    SnapshotCodecError,
    SnapshotLimits,
    fail,
)


_TOP_KEYS = frozenset({
    "schema_version", "collection_name", "collection_metadata", "row_count",
    "dimension", "metric", "embedding_identity", "rows", "vectors",
})
_IDENTITY_KEYS = frozenset({
    "backend", "model_id", "artifact_digest", "encoder_contract",
    "space_fingerprint",
})
_ROWS_KEYS = frozenset({"bytes", "sha256"})
_VECTOR_KEYS = frozenset({"bytes", "sha256", "dtype", "order"})
_ROW_KEYS = frozenset({"id", "document", "metadata"})
_DIGEST = re.compile(r"sha256:[0-9a-f]{64}")
_INT_MIN, _INT_MAX = -(2**63), 2**63 - 1


class _DuplicateKey(ValueError):
    pass


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateKey(key)
        result[key] = value
    return result


def _reject_constant(_value: str) -> None:
    raise ValueError("nonstandard JSON constant")


def _json_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError, OverflowError) as exc:
        raise SnapshotCodecError("HOLO_QUERY_SNAPSHOT_ROW_VALUE_INVALID") from exc


def _digest(payload: bytes) -> str:
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _valid_json(value: Any, *, depth: int = 0) -> bool:
    if depth > 64:
        return False
    if value is None or type(value) is bool:
        return True
    if type(value) is str:
        return _unicode_scalar_text(value) and unicodedata.normalize("NFC", value) == value
    if type(value) is int:
        return _INT_MIN <= value <= _INT_MAX
    if type(value) is float:
        return math.isfinite(value)
    if type(value) is list:
        return all(_valid_json(item, depth=depth + 1) for item in value)
    if type(value) is dict:
        return all(
            type(key) is str and _unicode_scalar_text(key)
            and unicodedata.normalize("NFC", key) == key
            and _valid_json(item, depth=depth + 1)
            for key, item in value.items()
        )
    return False


def _unicode_scalar_text(value: str) -> bool:
    return all(not 0xD800 <= ord(character) <= 0xDFFF for character in value)


def _valid_text(value: Any, *, max_bytes: int, require_nfc: bool = True) -> bool:
    if type(value) is not str or not value or not _unicode_scalar_text(value):
        return False
    if require_nfc and unicodedata.normalize("NFC", value) != value:
        return False
    try:
        return len(value.encode("utf-8")) <= max_bytes
    except UnicodeError:
        return False


def _validate_identity(value: Any, limits: SnapshotLimits) -> dict[str, str]:
    if type(value) is not dict or set(value) != _IDENTITY_KEYS:
        fail("EMBEDDING_IDENTITY_INVALID")
    if not all(
        _valid_text(value[key], max_bytes=limits.max_id_bytes) for key in value
    ):
        fail("EMBEDDING_IDENTITY_INVALID")
    for key in ("artifact_digest", "space_fingerprint"):
        if _DIGEST.fullmatch(value[key]) is None:
            fail("EMBEDDING_IDENTITY_INVALID")
    return dict(value)


def _validate_row(value: Any, limits: SnapshotLimits) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _ROW_KEYS:
        fail("ROW_INVALID")
    if not _valid_text(
        value["id"], max_bytes=limits.max_id_bytes, require_nfc=False,
    ):
        fail("ID_INVALID")
    if unicodedata.normalize("NFC", value["id"]) != value["id"]:
        fail("ID_NON_NFC")
    if not _valid_json(value["document"]) or not _valid_json(value["metadata"]):
        fail("ROW_VALUE_INVALID")
    try:
        document = _canonical_snapshot_value(value["document"])
        metadata = _canonical_snapshot_value(value["metadata"])
    except (TypeError, ValueError) as exc:
        raise SnapshotCodecError("HOLO_QUERY_SNAPSHOT_ROW_VALUE_INVALID") from exc
    return {"id": value["id"], "document": document, "metadata": metadata}


def _encode_rows(rows: Sequence[Mapping[str, Any]], limits: SnapshotLimits) -> tuple[bytes, list[dict[str, Any]]]:
    if type(rows) not in {list, tuple}:
        fail("ROWS_INVALID")
    if not 0 < len(rows) <= limits.max_rows:
        fail("ROW_COUNT_BOUND")
    canonical = [_validate_row(row, limits) for row in rows]
    ids = [row["id"] for row in canonical]
    if len(set(ids)) != len(ids):
        fail("DUPLICATE_ID")
    canonical.sort(key=lambda row: row["id"].encode("utf-8"))
    encoded: list[bytes] = []
    total = 0
    for row in canonical:
        line = _json_bytes(row) + b"\n"
        if len(line) > limits.max_row_bytes:
            fail("ROW_SIZE_BOUND")
        total += len(line)
        if total > limits.max_rows_bytes:
            fail("ROWS_SIZE_BOUND")
        encoded.append(line)
    return b"".join(encoded), canonical


def _encode_vectors(
    rows: Sequence[Mapping[str, Any]], canonical_rows: Sequence[Mapping[str, Any]],
    embeddings: Sequence[Sequence[float]], limits: SnapshotLimits,
) -> tuple[bytes, int]:
    if type(embeddings) not in {list, tuple}:
        fail("EMBEDDINGS_INVALID")
    if len(embeddings) != len(rows):
        fail("ROW_COUNT_MISMATCH")
    try:
        dimensions = [len(vector) for vector in embeddings]
    except TypeError as exc:
        raise SnapshotCodecError("HOLO_QUERY_SNAPSHOT_EMBEDDING_RAGGED") from exc
    if not dimensions or len(set(dimensions)) != 1:
        fail("EMBEDDING_RAGGED")
    dimension = dimensions[0]
    if not 0 < dimension <= limits.max_dimension:
        fail("DIMENSION_BOUND")
    expected_bytes = len(rows) * dimension * 4
    if expected_bytes > limits.max_vector_bytes:
        fail("VECTOR_SIZE_BOUND")
    for vector in embeddings:
        if type(vector) not in {list, tuple} or len(vector) != dimension:
            fail("EMBEDDING_RAGGED")
        for scalar in vector:
            if type(scalar) not in {int, float}:
                fail("EMBEDDING_SCALAR_INVALID")
            try:
                if not math.isfinite(float(scalar)):
                    fail("EMBEDDING_NONFINITE")
            except (OverflowError, ValueError):
                fail("EMBEDDING_NONFINITE")
    by_id = {row["id"]: vector for row, vector in zip(rows, embeddings)}
    try:
        with np.errstate(over="ignore", invalid="ignore"):
            matrix = np.asarray(
                [by_id[row["id"]] for row in canonical_rows], dtype="<f4"
            )
    except (TypeError, ValueError, OverflowError) as exc:
        raise SnapshotCodecError("HOLO_QUERY_SNAPSHOT_EMBEDDING_INVALID") from exc
    if matrix.shape != (len(rows), dimension):
        fail("EMBEDDING_RAGGED")
    if not bool(np.isfinite(matrix).all()):
        fail("EMBEDDING_NONFINITE")
    payload = matrix.tobytes(order="C")
    if not payload or len(payload) != expected_bytes:
        fail("VECTOR_SIZE_BOUND")
    return payload, dimension


def encode_collection_snapshot(
    *, collection_name: str, rows: Sequence[Mapping[str, Any]],
    embeddings: Sequence[Sequence[float]], metric: str,
    embedding_identity: Mapping[str, Any],
    collection_metadata: Mapping[str, Any] | None = None,
    limits: SnapshotLimits = SnapshotLimits(),
) -> EncodedCollectionSnapshot:
    """Return deterministic manifest, row, and little-endian float32 bytes."""

    limits.validate()
    if not _valid_text(collection_name, max_bytes=limits.max_id_bytes):
        fail("COLLECTION_NAME_INVALID")
    if type(metric) is not str or metric not in METRICS:
        fail("METRIC_INVALID")
    metadata = {} if collection_metadata is None else collection_metadata
    if type(metadata) is not dict or not _valid_json(metadata):
        fail("COLLECTION_METADATA_INVALID")
    row_bytes, canonical_rows = _encode_rows(rows, limits)
    vector_bytes, dimension = _encode_vectors(rows, canonical_rows, embeddings, limits)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "collection_name": collection_name,
        "collection_metadata": metadata,
        "row_count": len(canonical_rows),
        "dimension": dimension,
        "metric": metric,
        "embedding_identity": _validate_identity(embedding_identity, limits),
        "rows": {"bytes": len(row_bytes), "sha256": _digest(row_bytes)},
        "vectors": {
            "bytes": len(vector_bytes), "sha256": _digest(vector_bytes),
            "dtype": "<f4", "order": "C",
        },
    }
    manifest_bytes = _json_bytes(manifest) + b"\n"
    if len(manifest_bytes) > limits.max_manifest_bytes:
        fail("MANIFEST_SIZE_BOUND")
    return EncodedCollectionSnapshot(manifest_bytes, row_bytes, vector_bytes)


def _decode_manifest(payload: bytes, limits: SnapshotLimits) -> dict[str, Any]:
    if not payload or len(payload) > limits.max_manifest_bytes:
        fail("MANIFEST_SIZE_BOUND")
    try:
        value = json.loads(
            payload.decode("ascii"), object_pairs_hook=_strict_object,
            parse_constant=_reject_constant,
        )
    except (UnicodeError, ValueError, json.JSONDecodeError, _DuplicateKey, RecursionError) as exc:
        raise SnapshotCodecError("HOLO_QUERY_SNAPSHOT_MANIFEST_INVALID") from exc
    if type(value) is not dict:
        fail("MANIFEST_INVALID")
    try:
        canonical = _json_bytes(value) + b"\n"
    except SnapshotCodecError as exc:
        raise SnapshotCodecError("HOLO_QUERY_SNAPSHOT_MANIFEST_INVALID") from exc
    if canonical != payload:
        fail("MANIFEST_NONCANONICAL")
    return value


def _exact_int(value: Any, *, low: int, high: int, code: str) -> int:
    if type(value) is not int or not low <= value <= high:
        fail(code)
    return value


def _validate_artifact(value: Any, *, vector: bool, limits: SnapshotLimits) -> None:
    expected = _VECTOR_KEYS if vector else _ROWS_KEYS
    if type(value) is not dict or set(value) != expected:
        fail("MANIFEST_INVALID")
    ceiling = limits.max_vector_bytes if vector else limits.max_rows_bytes
    _exact_int(value["bytes"], low=1, high=ceiling, code="ARTIFACT_SIZE_BOUND")
    if type(value["sha256"]) is not str or _DIGEST.fullmatch(value["sha256"]) is None:
        fail("ARTIFACT_DIGEST_INVALID")
    if vector and (value["dtype"] != "<f4" or value["order"] != "C"):
        fail("VECTOR_FORMAT_INVALID")


def _validate_manifest(value: dict[str, Any], limits: SnapshotLimits) -> tuple[int, int]:
    if set(value) != _TOP_KEYS or value.get("schema_version") != SCHEMA_VERSION:
        fail("MANIFEST_SCHEMA_INVALID")
    if not _valid_text(value.get("collection_name"), max_bytes=limits.max_id_bytes):
        fail("COLLECTION_NAME_INVALID")
    if type(value.get("collection_metadata")) is not dict or not _valid_json(value["collection_metadata"]):
        fail("COLLECTION_METADATA_INVALID")
    count = _exact_int(value.get("row_count"), low=1, high=limits.max_rows, code="ROW_COUNT_BOUND")
    dimension = _exact_int(value.get("dimension"), low=1, high=limits.max_dimension, code="DIMENSION_BOUND")
    if type(value.get("metric")) is not str or value["metric"] not in METRICS:
        fail("METRIC_INVALID")
    _validate_identity(value.get("embedding_identity"), limits)
    _validate_artifact(value.get("rows"), vector=False, limits=limits)
    _validate_artifact(value.get("vectors"), vector=True, limits=limits)
    if value["vectors"]["bytes"] != count * dimension * 4:
        fail("VECTOR_LENGTH_MISMATCH")
    return count, dimension


def _decode_rows(payload: bytes, count: int, limits: SnapshotLimits) -> tuple[dict[str, Any], ...]:
    lines = payload.splitlines(keepends=True)
    if len(lines) != count or any(not line.endswith(b"\n") for line in lines):
        fail("ROWS_TRAILING_DATA")
    rows: list[dict[str, Any]] = []
    for line in lines:
        if len(line) > limits.max_row_bytes:
            fail("ROW_SIZE_BOUND")
        try:
            value = json.loads(
                line.decode("ascii"), object_pairs_hook=_strict_object,
                parse_constant=_reject_constant,
            )
        except (UnicodeError, ValueError, json.JSONDecodeError, _DuplicateKey, RecursionError) as exc:
            raise SnapshotCodecError("HOLO_QUERY_SNAPSHOT_ROW_INVALID") from exc
        row = _validate_row(value, limits)
        if _json_bytes(row) + b"\n" != line:
            fail("ROW_NONCANONICAL")
        rows.append(row)
    ids = [row["id"] for row in rows]
    if ids != sorted(ids, key=lambda value: value.encode("utf-8")):
        fail("ROW_ORDER_INVALID")
    if len(set(ids)) != len(ids):
        fail("DUPLICATE_ID")
    return tuple(rows)


def _buffer_size(value: Any, *, ceiling: int) -> int:
    if type(value) not in {bytes, bytearray, memoryview}:
        fail("BUFFER_INVALID")
    if type(value) is memoryview:
        try:
            valid = (
                value.ndim == 1 and value.c_contiguous and value.itemsize == 1
                and value.format in {"B", "b", "c"}
            )
            size = value.nbytes
        except ValueError:
            fail("BUFFER_INVALID")
        if not valid:
            fail("BUFFER_INVALID")
    else:
        size = len(value)
    if not 0 < size <= ceiling:
        fail("ARTIFACT_SIZE_BOUND")
    return size


def _buffer_bytes(value: Any) -> bytes:
    try:
        return bytes(value)
    except (TypeError, ValueError) as exc:
        raise SnapshotCodecError("HOLO_QUERY_SNAPSHOT_BUFFER_INVALID") from exc


def load_collection_snapshot(
    manifest: bytes | bytearray | memoryview,
    rows: bytes | bytearray | memoryview,
    vectors: bytes | bytearray | memoryview,
    *, limits: SnapshotLimits = SnapshotLimits(),
):
    """Load already-verified buffers without accepting or opening paths."""

    limits.validate()
    _buffer_size(manifest, ceiling=limits.max_manifest_bytes)
    manifest_bytes = _buffer_bytes(manifest)
    value = _decode_manifest(manifest_bytes, limits)
    count, dimension = _validate_manifest(value, limits)
    row_size = _buffer_size(rows, ceiling=limits.max_rows_bytes)
    vector_size = _buffer_size(vectors, ceiling=limits.max_vector_bytes)
    if row_size != value["rows"]["bytes"] or vector_size != value["vectors"]["bytes"]:
        fail("ARTIFACT_LENGTH_MISMATCH")
    row_bytes, vector_bytes = _buffer_bytes(rows), _buffer_bytes(vectors)
    for payload, entry in ((row_bytes, value["rows"]), (vector_bytes, value["vectors"])):
        if _digest(payload) != entry["sha256"]:
            fail("ARTIFACT_DIGEST_MISMATCH")
    parsed_rows = _decode_rows(row_bytes, count, limits)
    matrix = np.frombuffer(vector_bytes, dtype="<f4").reshape(count, dimension)
    if not bool(np.isfinite(matrix).all()):
        fail("EMBEDDING_NONFINITE")
    from .holo_query_snapshot_adapter import ImmutableSnapshotCollection

    return ImmutableSnapshotCollection(value, parsed_rows, matrix, limits)


__all__ = [
    "EncodedCollectionSnapshot", "SnapshotCodecError", "SnapshotLimits",
    "encode_collection_snapshot", "load_collection_snapshot",
]
