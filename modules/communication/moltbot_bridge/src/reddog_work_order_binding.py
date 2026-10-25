"""Canonical immutable binding helpers for governed RedDog work orders."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping


WORK_ORDER_MATERIALIZATION_BINDING_SCHEMA = (
    "reddog_work_order_materialization_binding_seed.v1"
)
WORK_ORDER_MATERIALIZATION_BINDING_FIELDS = frozenset(
    {
        "schema_version",
        "work_order_id",
        "base_ref",
        "queue_consumer_receipt_digest",
    }
)


def canonical_full_work_order_digest(work_order: Mapping[str, Any]) -> str:
    """Digest every serialized work-order field with no permissive coercion."""

    raw = json.dumps(
        dict(work_order),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def build_work_order_materialization_binding(
    *,
    work_order_id: str,
    base_ref: str,
    queue_consumer_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    """Bind queue identity and freshness into the authority-signed work order."""

    return {
        "schema_version": WORK_ORDER_MATERIALIZATION_BINDING_SCHEMA,
        "work_order_id": str(work_order_id),
        "base_ref": str(base_ref),
        "queue_consumer_receipt_digest": canonical_full_work_order_digest(
            queue_consumer_receipt
        ),
    }


def canonical_work_order_base_ref(work_order: Mapping[str, Any]) -> str:
    """Return the exact explicit base ref or fail for an unbound work order."""

    value = work_order.get("base_ref")
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError("canonical_work_order_base_ref_invalid")
    if not value.isascii() or any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise ValueError("canonical_work_order_base_ref_invalid")
    return value


__all__ = [
    "WORK_ORDER_MATERIALIZATION_BINDING_FIELDS",
    "WORK_ORDER_MATERIALIZATION_BINDING_SCHEMA",
    "build_work_order_materialization_binding",
    "canonical_full_work_order_digest",
    "canonical_work_order_base_ref",
]
