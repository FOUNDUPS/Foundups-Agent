"""Narrow immutable collection-snapshot value contracts."""

from __future__ import annotations

from dataclasses import dataclass


SCHEMA_VERSION = "holoindex_exact_collection_snapshot.v1"
METRICS = frozenset({"l2", "cosine", "ip"})
GET_INCLUDES = frozenset({"documents", "metadatas", "embeddings"})
QUERY_INCLUDES = GET_INCLUDES | {"distances"}


class SnapshotCodecError(ValueError):
    """Stable fail-closed snapshot or read-adapter error."""


def fail(code: str) -> None:
    raise SnapshotCodecError(f"HOLO_QUERY_SNAPSHOT_{code}")


@dataclass(frozen=True)
class SnapshotLimits:
    """Resource ceilings enforced at both encoding and loading."""

    max_manifest_bytes: int = 1_048_576
    max_rows: int = 100_000
    max_dimension: int = 4_096
    max_id_bytes: int = 4_096
    max_row_bytes: int = 1_048_576
    max_rows_bytes: int = 536_870_912
    max_vector_bytes: int = 1_073_741_824
    max_queries: int = 64
    query_chunk_rows: int = 8_192
    max_query_workspace_bytes: int = 67_108_864
    max_result_items: int = 500_000
    max_result_bytes: int = 536_870_912

    def validate(self) -> None:
        values = tuple(self.__dict__.values())
        if any(type(value) is not int or value <= 0 for value in values):
            fail("LIMIT_INVALID")


@dataclass(frozen=True)
class EncodedCollectionSnapshot:
    """Three path-free byte artifacts ready for external verification."""

    manifest: bytes
    rows: bytes
    vectors: bytes


__all__ = [
    "EncodedCollectionSnapshot", "GET_INCLUDES", "METRICS", "QUERY_INCLUDES",
    "SCHEMA_VERSION", "SnapshotCodecError", "SnapshotLimits", "fail",
]
