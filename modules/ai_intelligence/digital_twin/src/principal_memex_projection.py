"""Build and rehydrate structural 012 Principal Memex projections.

The projection is cognition data for the 0102 Digital Twin. It is not an
authenticated capability and is deliberately ineligible for resident model
context until a later authority-bound admission layer verifies every source.
"""

from __future__ import annotations

from dataclasses import fields
from typing import Any, Mapping, Sequence

from holo_index.query_receipt import digest_json
from modules.ai_intelligence.digital_twin.src.principal_memex_contract import (
    ITEM_SCHEMA_VERSION,
    MAX_ITEMS,
    PROJECTION_READY,
    PROJECTION_REJECTED,
    PROJECTION_SCHEMA_VERSION,
    SOURCE_CLASS_PRINCIPAL_MEMEX,
    STRUCTURAL_VERIFICATION,
    PrincipalMemexItem,
    PrincipalMemexProjection,
    PrincipalMemexProjectionResult,
    _create_principal_memex_projection,
    _create_principal_memex_projection_result,
    _principal_memex_item_reasons,
    _principal_memex_supersession_reasons,
    _principal_memex_valid_time,
)


_ITEM_FIELDS = frozenset(field.name for field in fields(PrincipalMemexItem))
_PROJECTION_FIELDS = frozenset(field.name for field in fields(PrincipalMemexProjection))
_PROJECTION_BOOLEAN_FIELDS = frozenset(
    {
        "runtime_admissible",
        "no_persistence_performed",
        "no_model_context_admission_performed",
        "no_foundup_projection_performed",
        "no_holoindex_write_performed",
        "no_work_authority_granted",
    }
)


def build_principal_memex_item(
    *, principal_id: str, category: str, statement: str, source_kind: str,
    source_receipt_id: str, source_revision: str, created_at: str,
    retention_state: str = "active", sensitivity: str = "private",
    supersedes_item_id: str = "",
) -> PrincipalMemexItem:
    values = (
        principal_id, category, statement, source_kind, source_receipt_id,
        source_revision, created_at, retention_state, sensitivity,
        supersedes_item_id,
    )
    if any(type(value) is not str for value in values):
        raise ValueError("principal_memex_item_type_invalid")
    payload = {
        "schema_version": ITEM_SCHEMA_VERSION,
        "principal_id": principal_id,
        "category": category,
        "statement": statement,
        "source_kind": source_kind,
        "source_receipt_id": source_receipt_id,
        "source_revision": source_revision,
        "created_at": created_at,
        "retention_state": retention_state,
        "sensitivity": sensitivity,
        "supersedes_item_id": supersedes_item_id,
        "content_digest": digest_json({"statement": statement}),
    }
    item = PrincipalMemexItem(item_id=digest_json(payload), **payload)
    reasons = _principal_memex_item_reasons(item)
    if reasons:
        raise ValueError(",".join(reasons))
    return item


def project_principal_memex_readonly(
    *, principal_id: str, items: Sequence[PrincipalMemexItem | Mapping[str, Any]],
    created_at: str,
) -> PrincipalMemexProjectionResult:
    reasons = _projection_input_reasons(principal_id, created_at, items)
    if (
        type(items) not in (list, tuple)
        or not items
        or len(items) > MAX_ITEMS
    ):
        return _rejected(*reasons)
    normalized: list[PrincipalMemexItem] = []
    for raw in items:
        item, item_reasons = _rehydrate_item(raw)
        reasons.extend(item_reasons)
        if item is not None:
            normalized.append(item)
    if normalized and any(item.principal_id != principal_id for item in normalized):
        reasons.append("principal_memex_cross_principal_item")
    reasons.extend(_principal_memex_supersession_reasons(normalized))
    item_ids = [item.item_id for item in normalized]
    if len(item_ids) != len(set(item_ids)):
        reasons.append("principal_memex_duplicate_item")
    if reasons:
        return _rejected(*reasons)
    projection = _build_projection(principal_id, normalized, created_at)
    return _create_principal_memex_projection_result(
        True, PROJECTION_READY, projection, ()
    )


def rehydrate_principal_memex_projection(
    raw: Mapping[str, Any] | PrincipalMemexProjection,
) -> PrincipalMemexProjectionResult:
    payload = raw.to_dict() if isinstance(raw, PrincipalMemexProjection) else raw
    if (
        type(payload) is not dict
        or len(payload) != len(_PROJECTION_FIELDS)
        or set(payload) != _PROJECTION_FIELDS
    ):
        return _rejected("principal_memex_projection_schema_fields_invalid")
    if not _serialized_projection_types_valid(payload):
        return _rejected("principal_memex_projection_type_invalid")
    item_result = project_principal_memex_readonly(
        principal_id=_strict_string(payload.get("principal_id")),
        items=_strict_sequence(payload.get("items")),
        created_at=_strict_string(payload.get("created_at")),
    )
    if not item_result.accepted or item_result.projection is None:
        return item_result
    expected = item_result.projection.to_dict()
    if any(payload.get(name) != expected[name] for name in _PROJECTION_FIELDS):
        return _rejected("principal_memex_projection_digest_or_boundary_mismatch")
    return item_result


def _build_projection(
    principal_id: str, items: Sequence[PrincipalMemexItem], created_at: str,
) -> PrincipalMemexProjection:
    ordered = tuple(sorted(items, key=lambda item: item.item_id))
    item_ids = tuple(item.item_id for item in ordered)
    source_ids = tuple(sorted({item.source_receipt_id for item in ordered}))
    manifest = digest_json(
        [{"item_id": item.item_id, "content_digest": item.content_digest} for item in ordered]
    )
    payload = {
        "schema_version": PROJECTION_SCHEMA_VERSION,
        "source_class": SOURCE_CLASS_PRINCIPAL_MEMEX,
        "principal_id": principal_id,
        "created_at": created_at,
        "item_ids": item_ids,
        "source_receipt_ids": source_ids,
        "manifest_digest": manifest,
        "verification": STRUCTURAL_VERIFICATION,
        "runtime_admissible": False,
        "no_persistence_performed": True,
        "no_model_context_admission_performed": True,
        "no_foundup_projection_performed": True,
        "no_holoindex_write_performed": True,
        "no_work_authority_granted": True,
    }
    return _create_principal_memex_projection(
        **payload, projection_id=digest_json(payload), items=ordered
    )


def _rehydrate_item(
    raw: PrincipalMemexItem | Mapping[str, Any],
) -> tuple[PrincipalMemexItem | None, list[str]]:
    payload = raw.to_dict() if isinstance(raw, PrincipalMemexItem) else raw
    if (
        type(payload) is not dict
        or len(payload) != len(_ITEM_FIELDS)
        or set(payload) != _ITEM_FIELDS
    ):
        return None, ["principal_memex_item_schema_fields_invalid"]
    if any(type(payload.get(name)) is not str for name in _ITEM_FIELDS):
        return None, ["principal_memex_item_type_invalid"]
    item = PrincipalMemexItem(**{name: payload[name] for name in _ITEM_FIELDS})
    return item, list(_principal_memex_item_reasons(item))


def _projection_input_reasons(
    principal_id: object, created_at: object, items: object,
) -> list[str]:
    reasons: list[str] = []
    if type(principal_id) is not str or not principal_id:
        reasons.append("principal_memex_principal_id_invalid")
    if type(created_at) is not str or not _principal_memex_valid_time(created_at):
        reasons.append("principal_memex_projection_created_at_invalid")
    if type(items) not in (list, tuple) or not items:
        reasons.append("principal_memex_items_missing")
    elif len(items) > MAX_ITEMS:
        reasons.append("principal_memex_item_limit_exceeded")
    return reasons


def _serialized_projection_types_valid(payload: Mapping[str, Any]) -> bool:
    string_fields = _PROJECTION_FIELDS - _PROJECTION_BOOLEAN_FIELDS - {
        "item_ids",
        "source_receipt_ids",
        "items",
    }
    if any(type(payload.get(name)) is not str for name in string_fields):
        return False
    if any(type(payload.get(name)) is not bool for name in _PROJECTION_BOOLEAN_FIELDS):
        return False
    for name in ("item_ids", "source_receipt_ids", "items"):
        if type(payload.get(name)) is not list:
            return False
    if (
        not 0 < len(payload["items"]) <= MAX_ITEMS
        or len(payload["item_ids"]) != len(payload["items"])
        or len(payload["source_receipt_ids"]) > MAX_ITEMS
    ):
        return False
    if any(
        type(item) is not str
        for name in ("item_ids", "source_receipt_ids")
        for item in payload[name]
    ):
        return False
    if any(type(item) is not dict for item in payload["items"]):
        return False
    return True


def _strict_string(value: object) -> str:
    return value if type(value) is str else ""


def _strict_sequence(value: object) -> Sequence[Any]:
    return value if type(value) is list else ()


def _rejected(*reasons: str) -> PrincipalMemexProjectionResult:
    return _create_principal_memex_projection_result(
        False, PROJECTION_REJECTED, None, tuple(dict.fromkeys(reasons))
    )


__all__ = [
    "build_principal_memex_item",
    "project_principal_memex_readonly",
    "rehydrate_principal_memex_projection",
]
