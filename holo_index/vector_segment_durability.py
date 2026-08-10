"""Pinned Chroma HNSW persistence policy and read-only artifact proof."""

from __future__ import annotations

import json
import sqlite3
import uuid
from pathlib import Path
from typing import Iterable, Mapping

from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    _contains_link_component,
)


HNSW_BATCH_SIZE = 2
HNSW_SYNC_THRESHOLD = 3
MAX_SCHEMA_BYTES = 256_000
HNSW_SEGMENT_TYPE = "urn:chroma:segment/vector/hnsw-local-persisted"
HNSW_ARTIFACTS = frozenset(
    {
        "data_level0.bin",
        "header.bin",
        "index_metadata.pickle",
        "length.bin",
        "link_lists.bin",
    }
)


def durable_hnsw_configuration() -> dict[str, dict[str, int]]:
    """Return a fresh copy of the collection persistence policy."""

    return {
        "hnsw": {
            "batch_size": HNSW_BATCH_SIZE,
            "sync_threshold": HNSW_SYNC_THRESHOLD,
        }
    }


def collection_uses_durable_hnsw_policy(collection: object) -> bool:
    """Return whether a pinned Chroma collection exposes the complete policy."""

    model = getattr(collection, "_model", None)
    schema = getattr(model, "serialized_schema", None)
    if not isinstance(schema, Mapping):
        return False
    return _schema_hnsw_policy_matches(schema)


def _schema_hnsw_policy_matches(schema: Mapping[str, object]) -> bool:
    try:
        hnsw = schema["keys"]["#embedding"]["float_list"]["vector_index"][
            "config"
        ]["hnsw"]
    except (KeyError, TypeError):
        return False
    return bool(
        isinstance(hnsw, Mapping)
        and hnsw.get("batch_size") == HNSW_BATCH_SIZE
        and hnsw.get("sync_threshold") == HNSW_SYNC_THRESHOLD
    )


def _hnsw_policy_matches(schema_text: str) -> bool:
    if not schema_text or len(schema_text.encode("utf-8")) > MAX_SCHEMA_BYTES:
        return False
    try:
        schema = json.loads(schema_text)
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return False
    return isinstance(schema, Mapping) and _schema_hnsw_policy_matches(schema)


def _segment_rows(vector_path: Path) -> dict[str, tuple[str, str]]:
    database = vector_path / "chroma.sqlite3"
    if _contains_link_component(database) or not database.is_file():
        return {}
    try:
        if database.stat(follow_symlinks=False).st_nlink != 1:
            return {}
    except OSError:
        return {}
    connection = sqlite3.connect(
        database.resolve(strict=True).as_uri() + "?mode=ro",
        uri=True,
        timeout=1.0,
    )
    try:
        connection.execute("PRAGMA query_only=ON")
        rows = connection.execute(
            "SELECT c.name, c.schema_str, s.id "
            "FROM collections AS c JOIN segments AS s ON s.collection = c.id "
            "WHERE s.type = ?",
            (HNSW_SEGMENT_TYPE,),
        ).fetchall()
    finally:
        connection.close()
    result: dict[str, tuple[str, str]] = {}
    for name, schema_text, segment_id in rows:
        if not all(isinstance(value, str) for value in (name, schema_text, segment_id)):
            return {}
        if name in result:
            return {}
        result[name] = (schema_text, segment_id)
    return result


def _segment_artifacts_complete(vector_path: Path, segment_id: str) -> bool:
    try:
        parsed = uuid.UUID(segment_id)
    except (ValueError, AttributeError):
        return False
    if str(parsed) != segment_id.lower():
        return False
    root = vector_path.resolve(strict=True)
    segment_entry = root / segment_id
    if _contains_link_component(segment_entry):
        return False
    segment = segment_entry.resolve(strict=True)
    if not segment.is_dir() or not segment.is_relative_to(root):
        return False
    for filename in HNSW_ARTIFACTS:
        artifact = segment / filename
        if _contains_link_component(artifact) or not artifact.is_file():
            return False
        metadata = artifact.stat(follow_symlinks=False)
        if metadata.st_nlink != 1 or metadata.st_size <= 0:
            return False
    return True


def _path_components_safe(path: Path) -> bool:
    return path.is_absolute() and path.exists() and not _contains_link_component(path)


def non_durable_vector_segments(
    ssd_path: Path | str,
    *,
    collection_names: Iterable[str],
) -> tuple[str, ...]:
    """Return collections missing policy-bound complete HNSW artifacts."""

    names = tuple(sorted(set(collection_names)))
    ssd = Path(ssd_path)
    vector_path = ssd / "vectors"
    if not _path_components_safe(vector_path):
        return names
    try:
        rows = _segment_rows(vector_path)
        return tuple(
            name
            for name in names
            if name not in rows
            or not _hnsw_policy_matches(rows[name][0])
            or not _segment_artifacts_complete(vector_path, rows[name][1])
        )
    except (OSError, sqlite3.Error, ValueError):
        return names


__all__ = [
    "HNSW_BATCH_SIZE",
    "HNSW_SYNC_THRESHOLD",
    "collection_uses_durable_hnsw_policy",
    "durable_hnsw_configuration",
    "non_durable_vector_segments",
]
