"""Read-only query proof for persisted Chroma vector segments."""

from __future__ import annotations

import math
import numbers
from pathlib import Path
from typing import Any, Iterable, Mapping

from holo_index.freshness_receipt import CollectionFreshness
from holo_index.vector_segment_durability import non_durable_vector_segments


MAX_EMBEDDING_DIMENSIONS = 8192
MAX_SELF_DISTANCE = 1e-6


def _list_value(value: Any) -> list[Any]:
    if hasattr(value, "tolist"):
        value = value.tolist()
    return value if isinstance(value, list) else []


def _sample_embedding(collection: Any) -> tuple[str, list[float]]:
    try:
        sample = collection.get(include=["embeddings"], limit=1, offset=0)
    except Exception as exc:
        raise ValueError("sample_embedding_unavailable") from exc
    ids = _list_value(sample.get("ids") if isinstance(sample, Mapping) else None)
    rows = _list_value(
        sample.get("embeddings") if isinstance(sample, Mapping) else None
    )
    vector = _list_value(rows[0]) if rows else []
    if (
        len(ids) != 1
        or not isinstance(ids[0], str)
        or not ids[0]
        or not vector
        or len(vector) > MAX_EMBEDDING_DIMENSIONS
        or any(
            isinstance(value, bool)
            or not isinstance(value, numbers.Real)
            or not math.isfinite(float(value))
            for value in vector
        )
    ):
        raise ValueError("sample_embedding_unavailable")
    return ids[0], [float(value) for value in vector]


def _queryable(collection: Any, *, count: int) -> bool:
    if count <= 0:
        return True
    try:
        sample_id, embedding = _sample_embedding(collection)
        result = collection.query(
            query_embeddings=[embedding],
            n_results=1,
            include=["distances"],
        )
    except Exception:
        return False
    id_rows = _list_value(
        result.get("ids") if isinstance(result, Mapping) else None
    )
    distance_rows = _list_value(
        result.get("distances") if isinstance(result, Mapping) else None
    )
    ids = _list_value(id_rows[0]) if id_rows else []
    distances = _list_value(distance_rows[0]) if distance_rows else []
    return bool(
        ids == [sample_id]
        and len(distances) == 1
        and isinstance(distances[0], numbers.Real)
        and not isinstance(distances[0], bool)
        and math.isfinite(float(distances[0]))
        and 0.0 <= float(distances[0]) <= MAX_SELF_DISTANCE
    )


def unqueryable_vector_segments(
    client: Any,
    entries: Mapping[str, CollectionFreshness],
    *,
    ssd_path: Path | str,
    collection_names: Iterable[str],
) -> tuple[str, ...]:
    """Return collections lacking durable files or a valid self-query."""

    names = tuple(sorted(collection_names))
    failures = set(
        non_durable_vector_segments(ssd_path, collection_names=names)
    )
    for name in names:
        try:
            collection = client.get_collection(name, embedding_function=None)
            queryable = _queryable(collection, count=entries[name].count)
        except Exception:
            queryable = False
        if not queryable:
            failures.add(name)
    return tuple(sorted(failures))


__all__ = ["unqueryable_vector_segments"]
