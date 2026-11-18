"""Typed read-only contract for 012 Principal Memex projections."""

from __future__ import annotations

import re
from dataclasses import InitVar, asdict, dataclass
from datetime import datetime
from typing import Any

from holo_index.query_receipt import digest_json
from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    redact_runtime_text,
)


ITEM_SCHEMA_VERSION = "principal_memex_item.v1"
PROJECTION_SCHEMA_VERSION = "principal_memex_projection.v1"
SOURCE_CLASS_PRINCIPAL_MEMEX = "principal_memex"
PROJECTION_READY = "PRINCIPAL_MEMEX_PROJECTION_READY"
PROJECTION_REJECTED = "PRINCIPAL_MEMEX_PROJECTION_REJECTED"
STRUCTURAL_VERIFICATION = "STRUCTURAL_ONLY"
_CONSTRUCTION_TOKEN = object()
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
MAX_ITEMS = 128
MAX_STATEMENT_CHARS = 4096
MAX_PRINCIPAL_ID_CHARS = 160
MAX_SOURCE_REVISION_CHARS = 256

ITEM_CATEGORIES = frozenset(
    {
        "accepted_terminology",
        "architectural_principle",
        "communication_preference",
        "decision_history",
        "identity_statement",
        "long_term_objective",
        "rejected_strategy",
        "stable_preference",
        "unresolved_hypothesis",
    }
)
SOURCE_KINDS = frozenset(
    {
        "accepted_decision",
        "governed_import",
        "principal_statement",
        "verified_observation",
    }
)
RETENTION_STATES = frozenset({"active", "superseded"})
SENSITIVITY_CLASSES = frozenset({"private", "public", "restricted"})


@dataclass(frozen=True)
class PrincipalMemexItem:
    schema_version: str
    item_id: str
    principal_id: str
    category: str
    statement: str
    source_kind: str
    source_receipt_id: str
    source_revision: str
    created_at: str
    retention_state: str
    sensitivity: str
    supersedes_item_id: str
    content_digest: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PrincipalMemexProjection:
    schema_version: str
    source_class: str
    principal_id: str
    created_at: str
    item_ids: tuple[str, ...]
    source_receipt_ids: tuple[str, ...]
    manifest_digest: str
    verification: str
    runtime_admissible: bool
    no_persistence_performed: bool
    no_model_context_admission_performed: bool
    no_foundup_projection_performed: bool
    no_holoindex_write_performed: bool
    no_work_authority_granted: bool
    projection_id: str
    items: tuple[PrincipalMemexItem, ...]
    _construction_token: InitVar[object] = None

    def __post_init__(self, _construction_token: object) -> None:
        if (
            _construction_token is not _CONSTRUCTION_TOKEN
            or type(self.schema_version) is not str
            or type(self.source_class) is not str
            or type(self.verification) is not str
            or self.schema_version != PROJECTION_SCHEMA_VERSION
            or self.source_class != SOURCE_CLASS_PRINCIPAL_MEMEX
            or self.verification != STRUCTURAL_VERIFICATION
            or type(self.runtime_admissible) is not bool
            or self.runtime_admissible is not False
            or not _projection_binding_valid(self)
            or any(
                type(value) is not bool or value is not True
                for value in (
                    self.no_persistence_performed,
                    self.no_model_context_admission_performed,
                    self.no_foundup_projection_performed,
                    self.no_holoindex_write_performed,
                    self.no_work_authority_granted,
                )
            )
        ):
            raise ValueError("principal_memex_projection_boundary_invalid")

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["item_ids"] = list(self.item_ids)
        payload["source_receipt_ids"] = list(self.source_receipt_ids)
        payload["items"] = [item.to_dict() for item in self.items]
        return payload


@dataclass(frozen=True)
class PrincipalMemexProjectionResult:
    accepted: bool
    status: str
    projection: PrincipalMemexProjection | None
    rejection_reasons: tuple[str, ...]
    _construction_token: InitVar[object] = None

    def __post_init__(self, _construction_token: object) -> None:
        if (
            _construction_token is not _CONSTRUCTION_TOKEN
            or type(self.accepted) is not bool
            or type(self.status) is not str
            or type(self.rejection_reasons) is not tuple
            or any(type(reason) is not str for reason in self.rejection_reasons)
        ):
            raise ValueError("principal_memex_projection_result_invalid")
        accepted_valid = (
            self.accepted is True
            and self.status == PROJECTION_READY
            and type(self.projection) is PrincipalMemexProjection
            and not self.rejection_reasons
        )
        rejected_valid = (
            self.accepted is False
            and self.status == PROJECTION_REJECTED
            and self.projection is None
            and bool(self.rejection_reasons)
        )
        if not accepted_valid and not rejected_valid:
            raise ValueError("principal_memex_projection_result_invalid")

    def to_dict(self) -> dict[str, Any]:
        return {
            "accepted": self.accepted,
            "status": self.status,
            "projection": self.projection.to_dict() if self.projection else None,
            "rejection_reasons": list(self.rejection_reasons),
        }


def _projection_binding_valid(projection: PrincipalMemexProjection) -> bool:
    if (
        type(projection.principal_id) is not str
        or type(projection.created_at) is not str
        or not _principal_memex_valid_time(projection.created_at)
        or type(projection.item_ids) is not tuple
        or type(projection.source_receipt_ids) is not tuple
        or type(projection.manifest_digest) is not str
        or type(projection.projection_id) is not str
        or type(projection.items) is not tuple
        or not 0 < len(projection.items) <= MAX_ITEMS
        or len(projection.item_ids) != len(projection.items)
        or len(projection.source_receipt_ids) > len(projection.items)
        or any(type(item) is not PrincipalMemexItem for item in projection.items)
        or any(_principal_memex_item_reasons(item) for item in projection.items)
        or _principal_memex_supersession_reasons(projection.items)
    ):
        return False
    expected_item_ids = tuple(item.item_id for item in projection.items)
    if (
        projection.items != tuple(sorted(projection.items, key=lambda item: item.item_id))
        or projection.item_ids != expected_item_ids
        or len(expected_item_ids) != len(set(expected_item_ids))
    ):
        return False
    expected_sources = tuple(sorted({item.source_receipt_id for item in projection.items}))
    if projection.source_receipt_ids != expected_sources:
        return False
    if any(item.principal_id != projection.principal_id for item in projection.items):
        return False
    expected_manifest = digest_json(
        [
            {"item_id": item.item_id, "content_digest": item.content_digest}
            for item in projection.items
        ]
    )
    return (
        projection.manifest_digest == expected_manifest
        and projection.projection_id == digest_json(_projection_id_payload(projection))
    )


def _principal_memex_item_reasons(item: PrincipalMemexItem) -> tuple[str, ...]:
    reasons: list[str] = []
    if any(type(value) is not str for value in item.to_dict().values()):
        return ("principal_memex_item_type_invalid",)
    if item.schema_version != ITEM_SCHEMA_VERSION:
        reasons.append("principal_memex_item_schema_invalid")
    for value, allowed, reason in (
        (item.category, ITEM_CATEGORIES, "principal_memex_category_invalid"),
        (item.source_kind, SOURCE_KINDS, "principal_memex_source_kind_invalid"),
        (item.retention_state, RETENTION_STATES, "principal_memex_retention_invalid"),
        (item.sensitivity, SENSITIVITY_CLASSES, "principal_memex_sensitivity_invalid"),
    ):
        if value not in allowed:
            reasons.append(reason)
    reasons.extend(_principal_memex_item_value_reasons(item))
    expected_content = digest_json({"statement": item.statement})
    payload = item.to_dict()
    payload.pop("item_id")
    payload["content_digest"] = expected_content
    if item.content_digest != expected_content or item.item_id != digest_json(payload):
        reasons.append("principal_memex_item_digest_mismatch")
    return tuple(reasons)


def _principal_memex_item_value_reasons(item: PrincipalMemexItem) -> list[str]:
    reasons: list[str] = []
    if not item.principal_id or not item.statement.strip() or not item.source_revision:
        reasons.append("principal_memex_required_value_missing")
    for value, limit, field in (
        (item.principal_id, MAX_PRINCIPAL_ID_CHARS, "principal_id"),
        (item.source_revision, MAX_SOURCE_REVISION_CHARS, "source_revision"),
        (item.statement, MAX_STATEMENT_CHARS, "statement"),
    ):
        reasons.extend(_principal_memex_text_reasons(value, limit, field))
    if not _principal_memex_valid_time(item.created_at):
        reasons.append("principal_memex_created_at_invalid")
    if not _SHA256_RE.fullmatch(item.source_receipt_id):
        reasons.append("principal_memex_source_receipt_id_invalid")
    if item.supersedes_item_id and not _SHA256_RE.fullmatch(item.supersedes_item_id):
        reasons.append("principal_memex_supersedes_item_id_invalid")
    return reasons


def _principal_memex_text_reasons(value: str, limit: int, field: str) -> list[str]:
    redaction = redact_runtime_text(value, max_chars=limit)
    reasons: list[str] = []
    if redaction.replacements:
        reasons.append("principal_memex_secret_material_forbidden")
    if redaction.truncated:
        reasons.append(f"principal_memex_{field}_too_long")
    if not redaction.replacements and redaction.text != value:
        reasons.append(f"principal_memex_{field}_not_canonical")
    return reasons


def _principal_memex_valid_time(value: str) -> bool:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return False
    return bool(value and parsed.tzinfo is not None and parsed.utcoffset() is not None)


def _principal_memex_supersession_reasons(
    items: tuple[PrincipalMemexItem, ...] | list[PrincipalMemexItem],
) -> tuple[str, ...]:
    by_id = {item.item_id: item for item in items}
    target_counts: dict[str, int] = {}
    reasons: list[str] = []
    for item in items:
        if not item.supersedes_item_id:
            continue
        target = by_id.get(item.supersedes_item_id)
        if target is None:
            reasons.append("principal_memex_supersession_target_missing")
            continue
        if target.retention_state != "superseded":
            reasons.append("principal_memex_supersession_target_state_invalid")
        target_counts[target.item_id] = target_counts.get(target.item_id, 0) + 1
    for item in items:
        expected = 1 if item.retention_state == "superseded" else 0
        if target_counts.get(item.item_id, 0) != expected:
            reasons.append("principal_memex_supersession_target_count_invalid")
    return tuple(reasons)


def _projection_id_payload(projection: PrincipalMemexProjection) -> dict[str, Any]:
    payload = projection.to_dict()
    payload.pop("projection_id")
    payload.pop("items")
    payload["item_ids"] = projection.item_ids
    payload["source_receipt_ids"] = projection.source_receipt_ids
    return payload


def _create_principal_memex_projection(
    **values: Any,
) -> PrincipalMemexProjection:
    return PrincipalMemexProjection(**values, _construction_token=_CONSTRUCTION_TOKEN)


def _create_principal_memex_projection_result(
    accepted: bool,
    status: str,
    projection: PrincipalMemexProjection | None,
    rejection_reasons: tuple[str, ...],
) -> PrincipalMemexProjectionResult:
    return PrincipalMemexProjectionResult(
        accepted,
        status,
        projection,
        rejection_reasons,
        _construction_token=_CONSTRUCTION_TOKEN,
    )


__all__ = [
    "ITEM_CATEGORIES",
    "ITEM_SCHEMA_VERSION",
    "PROJECTION_READY",
    "PROJECTION_REJECTED",
    "PROJECTION_SCHEMA_VERSION",
    "RETENTION_STATES",
    "SENSITIVITY_CLASSES",
    "SOURCE_CLASS_PRINCIPAL_MEMEX",
    "SOURCE_KINDS",
    "STRUCTURAL_VERIFICATION",
    "PrincipalMemexItem",
    "PrincipalMemexProjection",
    "PrincipalMemexProjectionResult",
]
