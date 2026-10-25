"""Canonical rehydration for resident RedDog Memex supply receipts.

This module proves structural integrity only. Producer authenticity is supplied
by the existing signed architect-proposal attestation, which binds the complete
canonical receipt digest before promotion can mutate authoritative state.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.reddog_operational_memex_supply_freshness import (
    DEFAULT_MAX_AGE_SECONDS,
    DEFAULT_MAX_TTL_SECONDS,
    validate_operational_memex_supply_freshness,
)


SCHEMA_VERSION = "reddog_operational_memex_snapshot_supply_receipt.v1"
_SEQUENCE_FIELDS = (
    "assignment_ids",
    "lane_ids",
    "task_ids",
    "assignment_receipt_ids",
)
_INTEGER_FIELDS = ("assignment_count", "max_records")
_BOOLEAN_FIELDS = (
    "no_memex_write_performed",
    "no_holoindex_reindex_performed",
    "no_repo_mutation_performed",
)


@dataclass(frozen=True)
class OperationalMemexSupplyReceipt:
    schema_version: str
    foundup_id: str
    principal_id: str
    snapshot_receipt_id: str
    snapshot_content_digest: str
    memex_view_id: str
    holoindex_generation_id: str
    source_revision: str
    policy_issued_at: str
    policy_expires_at: str
    assignment_count: int
    assignment_ids: tuple[str, ...]
    lane_ids: tuple[str, ...]
    task_ids: tuple[str, ...]
    assignment_receipt_ids: tuple[str, ...]
    max_records: int
    no_memex_write_performed: bool
    no_holoindex_reindex_performed: bool
    no_repo_mutation_performed: bool
    receipt_id: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def canonical_operational_memex_supply_digest(value: Mapping[str, Any]) -> str:
    """Digest the complete serialized receipt for signed authority binding."""

    return _digest(dict(value))


def operational_memex_supply_receipt_id(value: Mapping[str, Any]) -> str:
    """Compute the self-integrity ID over the exact receipt body."""

    return _digest({key: item for key, item in value.items() if key != "receipt_id"})


def rehydrate_operational_memex_supply_receipt(
    value: Mapping[str, Any],
    *,
    expected_foundup_id: str,
    expected_principal_id: str,
    expected_snapshot_receipt_id: str,
    expected_snapshot_content_digest: str,
    expected_holoindex_generation_id: str,
    expected_source_revision: str,
    now_iso: str,
    max_age_seconds: int = DEFAULT_MAX_AGE_SECONDS,
    max_ttl_seconds: int = DEFAULT_MAX_TTL_SECONDS,
) -> OperationalMemexSupplyReceipt:
    """Return an exact typed receipt or fail closed on any mismatch."""

    if not isinstance(value, Mapping):
        raise ValueError("memex_supply_receipt_not_mapping")
    raw = dict(value)
    expected_fields = set(OperationalMemexSupplyReceipt.__dataclass_fields__)
    if set(raw) != expected_fields:
        raise ValueError("memex_supply_receipt_fields_invalid")
    if raw.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("memex_supply_receipt_schema_invalid")
    normalized = _normalize(raw)
    receipt = OperationalMemexSupplyReceipt(**normalized)
    _validate_integrity(receipt)
    _validate_bindings(
        receipt,
        expected_foundup_id=expected_foundup_id,
        expected_principal_id=expected_principal_id,
        expected_snapshot_receipt_id=expected_snapshot_receipt_id,
        expected_snapshot_content_digest=expected_snapshot_content_digest,
        expected_holoindex_generation_id=expected_holoindex_generation_id,
        expected_source_revision=expected_source_revision,
    )
    validate_operational_memex_supply_freshness(
        receipt,
        now_iso=now_iso,
        max_age_seconds=max_age_seconds,
        max_ttl_seconds=max_ttl_seconds,
    )
    return receipt


def _normalize(raw: Mapping[str, Any]) -> dict[str, Any]:
    values = dict(raw)
    special_fields = set(_SEQUENCE_FIELDS + _INTEGER_FIELDS + _BOOLEAN_FIELDS)
    for field in set(values) - special_fields:
        if not isinstance(values[field], str) or not values[field].strip():
            raise ValueError(f"memex_supply_receipt_{field}_invalid")
        values[field] = values[field].strip()
    for field in _SEQUENCE_FIELDS:
        items = values.get(field)
        if not isinstance(items, (list, tuple)):
            raise ValueError(f"memex_supply_receipt_{field}_invalid")
        if any(not isinstance(item, str) or not item.strip() for item in items):
            raise ValueError(f"memex_supply_receipt_{field}_invalid")
        values[field] = tuple(item.strip() for item in items)
    for field in _INTEGER_FIELDS:
        if isinstance(values.get(field), bool) or not isinstance(values.get(field), int):
            raise ValueError(f"memex_supply_receipt_{field}_invalid")
    for field in _BOOLEAN_FIELDS:
        if not isinstance(values.get(field), bool):
            raise ValueError(f"memex_supply_receipt_{field}_invalid")
    return values


def _validate_integrity(receipt: OperationalMemexSupplyReceipt) -> None:
    payload = receipt.to_dict()
    if receipt.receipt_id != operational_memex_supply_receipt_id(payload):
        raise ValueError("memex_supply_receipt_id_mismatch")
    if receipt.assignment_count <= 0 or receipt.max_records <= 0:
        raise ValueError("memex_supply_receipt_count_invalid")
    sequences = (
        receipt.assignment_ids,
        receipt.lane_ids,
        receipt.task_ids,
        receipt.assignment_receipt_ids,
    )
    if any(len(items) != receipt.assignment_count for items in sequences):
        raise ValueError("memex_supply_receipt_assignment_count_mismatch")
    if any(not item for items in sequences for item in items):
        raise ValueError("memex_supply_receipt_assignment_value_missing")
    if any(len(set(items)) != len(items) for items in sequences):
        raise ValueError("memex_supply_receipt_assignment_duplicate")
    if not all((
        receipt.no_memex_write_performed,
        receipt.no_holoindex_reindex_performed,
        receipt.no_repo_mutation_performed,
    )):
        raise ValueError("memex_supply_receipt_boundary_invalid")


def _validate_bindings(receipt: OperationalMemexSupplyReceipt, **expected: str) -> None:
    observed = {
        "expected_foundup_id": receipt.foundup_id,
        "expected_principal_id": receipt.principal_id,
        "expected_snapshot_receipt_id": receipt.snapshot_receipt_id,
        "expected_snapshot_content_digest": receipt.snapshot_content_digest,
        "expected_holoindex_generation_id": receipt.holoindex_generation_id,
        "expected_source_revision": receipt.source_revision,
    }
    if any(not value or observed[key] != str(value).strip() for key, value in expected.items()):
        raise ValueError("memex_supply_receipt_authority_binding_mismatch")


def _digest(value: Any) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


__all__ = [
    "OperationalMemexSupplyReceipt",
    "SCHEMA_VERSION",
    "DEFAULT_MAX_AGE_SECONDS",
    "DEFAULT_MAX_TTL_SECONDS",
    "canonical_operational_memex_supply_digest",
    "operational_memex_supply_receipt_id",
    "rehydrate_operational_memex_supply_receipt",
]
