"""Read-only Chroma-shaped adapter over an immutable collection snapshot."""

from __future__ import annotations

import copy
import json
import math
import unicodedata
from typing import Any, Mapping, Sequence

import numpy as np

from .holo_query_snapshot_contract import (
    GET_INCLUDES,
    QUERY_INCLUDES,
    SnapshotCodecError,
    SnapshotLimits,
    fail,
)


def _include(value: Any, allowed: frozenset[str], default: tuple[str, ...]) -> tuple[str, ...]:
    if value is None:
        return default
    if type(value) not in {list, tuple} or any(
        type(item) is not str or item not in allowed for item in value
    ):
        fail("INCLUDE_INVALID")
    if len(set(value)) != len(value):
        fail("INCLUDE_INVALID")
    return tuple(value)


def _bound_int(
    value: Any, *, minimum: int, code: str, maximum: int | None = None,
) -> int:
    if (
        type(value) is not int or value < minimum
        or (maximum is not None and value > maximum)
    ):
        fail(code)
    return value


def _valid_id(value: Any, limits: SnapshotLimits) -> bool:
    if type(value) is not str or not value:
        return False
    if any(0xD800 <= ord(character) <= 0xDFFF for character in value):
        return False
    if unicodedata.normalize("NFC", value) != value:
        return False
    try:
        return len(value.encode("utf-8")) <= limits.max_id_bytes
    except UnicodeError:
        return False


def _validated_queries(
    query_embeddings: Any, dimension: int, limits: SnapshotLimits,
) -> np.ndarray:
    if type(query_embeddings) not in {list, tuple} or not (
        0 < len(query_embeddings) <= limits.max_queries
    ):
        fail("QUERY_EMBEDDINGS_INVALID")
    for query in query_embeddings:
        if type(query) not in {list, tuple} or len(query) != dimension:
            fail("QUERY_DIMENSION_INVALID")
        for scalar in query:
            if type(scalar) not in {int, float}:
                fail("QUERY_SCALAR_INVALID")
            try:
                if not math.isfinite(float(scalar)):
                    fail("QUERY_EMBEDDINGS_NONFINITE")
            except (OverflowError, ValueError):
                fail("QUERY_EMBEDDINGS_NONFINITE")
    if len(query_embeddings) * dimension * 4 > limits.max_query_workspace_bytes:
        fail("QUERY_WORKSPACE_BOUND")
    try:
        with np.errstate(over="ignore", invalid="ignore"):
            queries = np.asarray(query_embeddings, dtype="<f4")
    except (TypeError, ValueError, OverflowError) as exc:
        raise SnapshotCodecError(
            "HOLO_QUERY_SNAPSHOT_QUERY_EMBEDDINGS_INVALID"
        ) from exc
    if not bool(np.isfinite(queries).all()):
        fail("QUERY_EMBEDDINGS_NONFINITE")
    return queries


def _workspace_chunk_rows(
    limits: SnapshotLimits, metric: str, dimension: int, count: int,
    batch_query_bytes: int, retained_match_bytes: int, requested_rows: int,
) -> int:
    fixed_bytes = (
        batch_query_bytes + retained_match_bytes + dimension * 8 + count * 64
    )
    if metric == "l2":
        # Chunk, delta, squared delta, and reduction scratch coexist; the row
        # margin covers the reduction output and alignment slack.
        distance_bytes = dimension * 32 + 32
    elif metric == "cosine":
        # Chunk, norm-square product, and reduction scratch coexist; the row
        # margin covers dots/norm/result/mask/selections/similarity/clip output.
        distance_bytes = dimension * 24 + 96
    else:
        # Float64 chunk plus dot and subtraction outputs.
        distance_bytes = dimension * 8 + 16
    per_row_bytes = max(distance_bytes, 40)
    available = limits.max_query_workspace_bytes - fixed_bytes
    if available < per_row_bytes:
        fail("QUERY_WORKSPACE_BOUND")
    return min(requested_rows, max(1, available // per_row_bytes))


def _json_wire_scalar_bytes(value: Any) -> int:
    try:
        return len(json.dumps(
            value, separators=(",", ":"), ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii"))
    except (TypeError, ValueError, OverflowError, UnicodeError) as exc:
        raise SnapshotCodecError("HOLO_QUERY_SNAPSHOT_RESULT_VALUE_INVALID") from exc


def _json_wire_value_bytes(value: Any) -> int:
    if type(value) is list:
        return _json_wire_array_bytes(
            _json_wire_value_bytes(item) for item in value
        )
    if type(value) is dict:
        pairs = (
            _json_wire_scalar_bytes(key) + 1 + _json_wire_value_bytes(item)
            for key, item in value.items()
        )
        return _json_wire_array_bytes(pairs)
    return _json_wire_scalar_bytes(value)


def _json_wire_array_bytes(item_sizes) -> int:
    total = 2
    count = 0
    for size in item_sizes:
        total += size
        count += 1
    return total + max(0, count - 1)


def _result_group_wire_bytes(
    field: str, rows: tuple[dict[str, Any], ...], vectors: np.ndarray,
    indices: Sequence[int], distances: Sequence[float] | None,
) -> int:
    if field == "ids":
        sizes = (_json_wire_scalar_bytes(rows[index]["id"]) for index in indices)
    elif field == "documents":
        sizes = (_json_wire_value_bytes(rows[index]["document"]) for index in indices)
    elif field == "metadatas":
        sizes = (_json_wire_value_bytes(rows[index]["metadata"]) for index in indices)
    elif field == "embeddings":
        sizes = (
            _json_wire_array_bytes(
                _json_wire_scalar_bytes(float(value)) for value in vectors[index]
            ) for index in indices
        )
    else:
        source = () if distances is None else distances
        sizes = (
            _json_wire_scalar_bytes(float(value)) for value in source
        )
    return _json_wire_array_bytes(sizes)


def _ensure_result_items(row_count: int, fields: Sequence[str], limits: SnapshotLimits) -> None:
    if row_count * (1 + len(fields)) > limits.max_result_items:
        fail("RESULT_ITEM_BOUND")


def _ensure_result_wire_bytes(
    rows: tuple[dict[str, Any], ...], vectors: np.ndarray,
    groups: Sequence[Sequence[int]], distance_groups: Sequence[Sequence[float]] | None,
    fields: Sequence[str], nested: bool, limits: SnapshotLimits,
) -> None:
    total = 2
    names = ("ids",) + tuple(fields)
    for position, field in enumerate(names):
        total += _json_wire_scalar_bytes(field) + 1
        group_sizes = (
            _result_group_wire_bytes(
                field, rows, vectors, indices,
                None if distance_groups is None else distance_groups[group_index],
            ) for group_index, indices in enumerate(groups)
        )
        total += _json_wire_array_bytes(group_sizes) if nested else next(group_sizes)
        if position:
            total += 1
    if total > limits.max_result_bytes:
        fail("RESULT_WIRE_SIZE_BOUND")


class ImmutableSnapshotCollection:
    """The exact read subset Holo search uses from one Chroma collection."""

    def __init__(
        self, manifest: Mapping[str, Any], rows: tuple[dict[str, Any], ...],
        vectors: np.ndarray, limits: SnapshotLimits,
    ) -> None:
        self.name = manifest["collection_name"]
        self._metadata = copy.deepcopy(manifest["collection_metadata"])
        self._embedding_identity = dict(manifest["embedding_identity"])
        self.metric = manifest["metric"]
        self._rows = rows
        self._vectors = vectors
        self._dimension = int(vectors.shape[1])
        self._limits = limits
        self._query_chunk_rows = limits.query_chunk_rows
        self._id_to_index = {row["id"]: index for index, row in enumerate(rows)}
        self._path_to_indices = self._build_path_index(rows)

    @property
    def metadata(self) -> dict[str, Any]:
        return copy.deepcopy(self._metadata)

    @property
    def embedding_identity(self) -> dict[str, str]:
        return dict(self._embedding_identity)

    @staticmethod
    def _build_path_index(rows: tuple[dict[str, Any], ...]) -> dict[str, tuple[int, ...]]:
        values: dict[str, list[int]] = {}
        for index, row in enumerate(rows):
            metadata = row["metadata"]
            path = metadata.get("path") if type(metadata) is dict else None
            if type(path) is str:
                values.setdefault(path, []).append(index)
        return {key: tuple(indices) for key, indices in values.items()}

    def count(self) -> int:
        return len(self._rows)

    def _selected_indices(self, ids: Any, where: Any) -> list[int]:
        if ids is not None and where is not None:
            fail("GET_FILTER_CONFLICT")
        if ids is not None:
            requested = [ids] if type(ids) is str else ids
            if type(requested) is not list or not requested:
                fail("GET_IDS_INVALID")
            if len(requested) > self._limits.max_rows:
                fail("GET_IDS_BOUND")
            if any(not _valid_id(item, self._limits) for item in requested):
                fail("GET_ID_INVALID")
            if len(set(requested)) != len(requested):
                fail("GET_IDS_INVALID")
            return [
                self._id_to_index[item]
                for item in requested
                if item in self._id_to_index
            ]
        if where is not None:
            if (
                type(where) is not dict or set(where) != {"path"}
                or not _valid_id(where["path"], self._limits)
            ):
                fail("GET_WHERE_INVALID")
            return list(self._path_to_indices.get(where["path"], ()))
        return list(range(len(self._rows)))

    def get(
        self, ids: str | list[str] | None = None,
        *, include: Sequence[str] | None = None, limit: int | None = None,
        offset: int = 0, where: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Return flat Chroma-compatible read results."""

        fields = _include(include, GET_INCLUDES, ("documents", "metadatas"))
        start = _bound_int(offset, minimum=0, code="GET_OFFSET_INVALID")
        size = None if limit is None else _bound_int(limit, minimum=1, code="GET_LIMIT_INVALID")
        indices = self._selected_indices(ids, where)
        selected = indices[start:] if size is None else indices[start:start + size]
        _ensure_result_items(len(selected), fields, self._limits)
        _ensure_result_wire_bytes(
            self._rows, self._vectors, (selected,), None, fields, False,
            self._limits,
        )
        return self._result(selected, fields, nested=False)

    def _result(
        self, indices: Sequence[int], fields: Sequence[str], *, nested: bool,
        distances: Sequence[float] | None = None,
    ) -> dict[str, Any]:
        ids = [self._rows[index]["id"] for index in indices]
        result: dict[str, Any] = {"ids": [ids] if nested else ids}
        for field in fields:
            if field == "documents":
                value = [
                    copy.deepcopy(self._rows[index]["document"])
                    for index in indices
                ]
            elif field == "metadatas":
                value = [
                    copy.deepcopy(self._rows[index]["metadata"])
                    for index in indices
                ]
            elif field == "embeddings":
                value = [self._vectors[index].tolist() for index in indices]
            else:
                value = [] if distances is None else [float(item) for item in distances]
            result[field] = [value] if nested else value
        return result

    def _distance_chunk(self, query: np.ndarray, start: int, end: int) -> np.ndarray:
        chunk = np.asarray(self._vectors[start:end], dtype=np.float64)
        if self.metric == "l2":
            delta = chunk - query
            return np.sum(delta * delta, axis=1)
        dots = chunk @ query
        if self.metric == "ip":
            return 1.0 - dots
        chunk_norms = np.linalg.norm(chunk, axis=1)
        query_norm = float(np.linalg.norm(query))
        distances = np.ones(end - start, dtype=np.float64)
        nonzero = (chunk_norms > 0.0) & (query_norm > 0.0)
        if bool(nonzero.any()):
            similarity = dots[nonzero] / (chunk_norms[nonzero] * query_norm)
            distances[nonzero] = np.clip(1.0 - similarity, 0.0, 2.0)
        return distances

    def _nearest(
        self, query: np.ndarray, count: int, batch_query_bytes: int,
        retained_match_bytes: int,
    ) -> tuple[np.ndarray, np.ndarray]:
        best_indices = np.empty(0, dtype=np.int64)
        best_distances = np.empty(0, dtype=np.float64)
        chunk_rows = _workspace_chunk_rows(
            self._limits, self.metric, self._dimension, count,
            batch_query_bytes, retained_match_bytes, self._query_chunk_rows,
        )
        for start in range(0, len(self._rows), chunk_rows):
            end = min(start + chunk_rows, len(self._rows))
            chunk_distances = np.asarray(self._distance_chunk(query, start, end))
            if not bool(np.isfinite(chunk_distances).all()):
                fail("QUERY_DISTANCE_NONFINITE")
            chunk_indices = np.arange(start, end, dtype=np.int64)
            candidates_i = np.concatenate((best_indices, chunk_indices))
            candidates_d = np.concatenate((best_distances, chunk_distances))
            order = np.lexsort((candidates_i, candidates_d))[:count]
            best_indices, best_distances = candidates_i[order], candidates_d[order]
        return best_indices, best_distances

    def query(
        self, *, query_embeddings: Sequence[Sequence[float]], n_results: int,
        include: Sequence[str] | None = None,
    ) -> dict[str, Any]:
        """Return nested Chroma-compatible exact vector results."""

        fields = _include(
            include, QUERY_INCLUDES, ("documents", "metadatas", "distances")
        )
        if type(n_results) is int and n_results > self._limits.max_rows:
            fail("QUERY_LIMIT_BOUND")
        wanted = _bound_int(
            n_results, minimum=1, code="QUERY_LIMIT_INVALID",
        )
        queries = _validated_queries(
            query_embeddings, self._dimension, self._limits,
        )
        result_rows = len(queries) * min(wanted, len(self._rows))
        _ensure_result_items(result_rows, fields, self._limits)
        matches: list[tuple[np.ndarray, np.ndarray]] = []
        retained_match_bytes = 0
        for query in queries:
            query64 = np.asarray(query, dtype=np.float64)
            match = self._nearest(
                query64, min(wanted, len(self._rows)), queries.nbytes,
                retained_match_bytes,
            )
            matches.append(match)
            retained_match_bytes += match[0].nbytes + match[1].nbytes
        _ensure_result_wire_bytes(
            self._rows, self._vectors,
            tuple(indices for indices, _distances in matches),
            tuple(distances for _indices, distances in matches),
            fields, True, self._limits,
        )
        combined: dict[str, list[Any]] = {"ids": []}
        for field in fields:
            combined[field] = []
        for indices, distances in matches:
            result = self._result(indices, fields, nested=True, distances=distances)
            combined["ids"].append(result["ids"][0])
            for field in fields:
                combined[field].append(result[field][0])
        return combined


__all__ = ["ImmutableSnapshotCollection"]
