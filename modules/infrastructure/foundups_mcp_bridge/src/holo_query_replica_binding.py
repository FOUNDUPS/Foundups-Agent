"""Exact parsing for the four-field Holo query-replica capability."""

from __future__ import annotations

from .holo_query_binding import ExactBinding, parse_exact_binding


ReplicaBinding = ExactBinding


def parse_replica_binding(value: object) -> ReplicaBinding | None:
    """Return one normalized exact binding; reject every duck-typed shape."""

    return parse_exact_binding(value)


def replica_binding_is_complete(value: object) -> bool:
    """Return whether ``value`` is the exact admission capability shape."""

    return parse_replica_binding(value) is not None


__all__ = ["ReplicaBinding", "parse_replica_binding", "replica_binding_is_complete"]
