"""Pinned Chroma HNSW persistence policy and read-only artifact proof."""

from __future__ import annotations

import json
import math
import sqlite3
import uuid
from itertools import chain
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


class UnsafeCollectionSettingsError(ValueError):
    """Fixed refusal for untrusted stored collection settings."""

    def __init__(self) -> None:
        super().__init__("HOLOINDEX_UNSAFE_COLLECTION_SETTINGS")


def _validate_raw_json(value: object, depth: int, active: set[int],
                       totals: list[int]) -> None:
    totals[0] += 1
    if depth > 16 or totals[0] > 4096:
        raise UnsafeCollectionSettingsError()
    kind = type(value)
    if kind is str:
        totals[1] += len(value)
        if totals[1] > MAX_SCHEMA_BYTES:
            raise UnsafeCollectionSettingsError()
    elif kind is int:
        if value.bit_length() > 2048:
            raise UnsafeCollectionSettingsError()
    elif kind is float:
        if not math.isfinite(value):
            raise UnsafeCollectionSettingsError()
    elif kind is bool or value is None:
        return
    elif kind is dict or kind is list:
        identity = id(value)
        if identity in active:
            raise UnsafeCollectionSettingsError()
        active.add(identity)
        try:
            if kind is dict:
                for key, item in value.items():
                    if type(key) is not str:
                        raise UnsafeCollectionSettingsError()
                    _validate_raw_json(key, depth + 1, active, totals)
                    _validate_raw_json(item, depth + 1, active, totals)
            else:
                for item in value:
                    _validate_raw_json(item, depth + 1, active, totals)
        finally:
            active.remove(identity)
    else:
        raise UnsafeCollectionSettingsError()


def _validate_embedding_spec(spec: object, *, dense: bool,
                             allow_none: bool = False) -> None:
    if allow_none and spec is None:
        return
    if type(spec) is not dict:
        raise UnsafeCollectionSettingsError()
    if spec == {"type": "legacy"}:
        return
    if not dense and spec == {"type": "unknown"}:
        return
    if dense and spec == {"type": "known", "name": "default", "config": {}}:
        return
    raise UnsafeCollectionSettingsError()


def _validate_schema_embedding_functions(schema: object) -> None:
    if schema is None:
        return
    if type(schema) is not dict:
        raise UnsafeCollectionSettingsError()
    defaults, keys = schema.get("defaults", {}), schema.get("keys", {})
    if type(defaults) is not dict or type(keys) is not dict:
        raise UnsafeCollectionSettingsError()
    for value in chain((defaults,), keys.values()):
        if type(value) is not dict:
            raise UnsafeCollectionSettingsError()
        for type_name, index_name, dense in (
            ("float_list", "vector_index", True),
            ("sparse_vector", "sparse_vector_index", False),
        ):
            if type_name not in value:
                continue
            shape = value[type_name]
            if type(shape) is not dict:
                raise UnsafeCollectionSettingsError()
            if index_name not in shape:
                continue
            index = shape[index_name]
            if type(index) is not dict:
                raise UnsafeCollectionSettingsError()
            config = index.get("config", {})
            if type(config) is not dict:
                raise UnsafeCollectionSettingsError()
            if "embedding_function" in config:
                _validate_embedding_spec(config["embedding_function"], dense=dense)


def validate_collection_raw_settings(collection: object) -> str:
    """Admit inert captured settings under the serialized maintenance owner."""
    model = getattr(collection, "_model", None)
    try:
        configuration = model.configuration_json
        schema = model.serialized_schema
    except AttributeError:
        raise UnsafeCollectionSettingsError() from None
    totals: list[int] = [0, 0]
    for root in (configuration, schema):
        _validate_raw_json(root, 0, set(), totals)
    encoded_size = sum(
        len(json.dumps(root, ensure_ascii=True, allow_nan=False,
                       separators=(",", ":")).encode("ascii"))
        for root in (configuration, schema)
    )
    if encoded_size > MAX_SCHEMA_BYTES or type(configuration) is not dict:
        raise UnsafeCollectionSettingsError()
    hnsw = configuration.get("hnsw")
    if type(hnsw) is not dict:
        raise UnsafeCollectionSettingsError()
    metric = hnsw.get("space")
    if type(metric) is not str or metric not in {"l2", "cosine", "ip"}:
        raise UnsafeCollectionSettingsError()
    if "embedding_function" in configuration:
        _validate_embedding_spec(configuration["embedding_function"],
                                 dense=True, allow_none=True)
    _validate_schema_embedding_functions(schema)
    return metric


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
    "UnsafeCollectionSettingsError",
    "validate_collection_raw_settings",
    "collection_uses_durable_hnsw_policy",
    "durable_hnsw_configuration",
    "non_durable_vector_segments",
]
