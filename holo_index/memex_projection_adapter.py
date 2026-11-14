"""Governed Memex projection records for HoloIndex.

This adapter turns an accepted FoundUp Memex view into deterministic shadow
records that a later governed indexer may promote into HoloIndex. It does not
write HoloIndex, Memex, Brain, Breadcrumbs, repository state, or queues.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from holo_index.memex_access_policy_receipt import (
    MemexAccessPolicyReceipt,
    section_allowed_by_policy,
    validate_memex_access_policy_receipt,
)
from holo_index.query_receipt import SOURCE_CLASS_MEMEX, digest_json


SCHEMA_VERSION = "holoindex_memex_governed_projection_adapter.v1"
RECEIPT_SCHEMA_VERSION = "holoindex_memex_snapshot_projection_receipt.v1"
PROJECTION_ACCEPTED = "MEMEX_PROJECTION_READY"
PROJECTION_REJECTED = "MEMEX_PROJECTION_REJECTED"
DEFAULT_ACCESS_POLICY_DIGEST = (
    "sha256:1111111111111111111111111111111111111111111111111111111111111111"
)

_SECRET_RE = re.compile(
    r"(?i)(api[_-]?key|secret|password|private[_-]?key|bearer\s+[A-Za-z0-9._-]+|sk-[A-Za-z0-9_-]+)"
)


@dataclass(frozen=True)
class MemexProjectionRecord:
    """One shadow HoloIndex record derived from a Memex view."""

    record_id: str
    source_class: str
    foundup_id: str
    memex_snapshot_id: str
    source_scope: str
    source_revision: str
    title: str
    text: str
    metadata: dict[str, Any]
    content_digest: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MemexSnapshotProjectionReceipt:
    """Immutable receipt for one governed Memex projection."""

    schema_version: str
    memex_snapshot_id: str
    source_scope: str
    source_revision: str
    content_manifest_digest: str
    created_at: str
    access_policy_digest: str
    records_indexed: int
    records_rejected: int
    holoindex_generation_id: str
    verification: str
    rejected_reasons: tuple[str, ...] = ()
    no_holoindex_write_performed: bool = True
    no_memex_write_performed: bool = True
    no_brain_write_performed: bool = True
    no_breadcrumb_write_performed: bool = True
    receipt_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MemexProjectionResult:
    accepted: bool
    status: str
    records: tuple[MemexProjectionRecord, ...]
    receipt: MemexSnapshotProjectionReceipt | None
    rejection_reasons: tuple[str, ...]
    no_holoindex_write_performed: bool = True
    no_memex_write_performed: bool = True
    no_brain_write_performed: bool = True
    no_breadcrumb_write_performed: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "accepted": self.accepted,
            "status": self.status,
            "records": [record.to_dict() for record in self.records],
            "receipt": self.receipt.to_dict() if self.receipt else None,
            "rejection_reasons": list(self.rejection_reasons),
            "no_holoindex_write_performed": self.no_holoindex_write_performed,
            "no_memex_write_performed": self.no_memex_write_performed,
            "no_brain_write_performed": self.no_brain_write_performed,
            "no_breadcrumb_write_performed": self.no_breadcrumb_write_performed,
        }


def project_foundup_memex_to_holoindex_shadow(
    *,
    memex_view: Mapping[str, Any],
    source_scope: str,
    source_revision: str,
    allowed_foundup_ids: Sequence[str],
    access_policy_digest: str = DEFAULT_ACCESS_POLICY_DIGEST,
    access_policy_receipt: MemexAccessPolicyReceipt | Mapping[str, Any] | None = None,
    holoindex_generation_id: str = "",
    now_iso: str | None = None,
) -> MemexProjectionResult:
    """Build shadow HoloIndex records from an accepted FoundUp Memex view."""

    reasons: list[str] = []
    if not isinstance(memex_view, Mapping):
        return _reject("memex_view_not_mapping")
    foundup_id = _clean(memex_view.get("foundup_id"))
    if not foundup_id:
        reasons.append("missing_foundup_id")
    allowed = {_clean(item) for item in allowed_foundup_ids if _clean(item)}
    if foundup_id and foundup_id not in allowed:
        reasons.append("foundup_scope_not_authorized")
    memex_snapshot_id = _clean(
        memex_view.get("foundup_memex_view_id")
        or memex_view.get("foundup_brain_view_id")
        or memex_view.get("snapshot_id")
    )
    snapshot_id = _clean(memex_view.get("snapshot_id"))
    snapshot_digest = _clean(memex_view.get("snapshot_content_digest"))
    if not memex_snapshot_id or not snapshot_id or not snapshot_digest:
        reasons.append("missing_snapshot_binding")
    if not _clean(source_scope):
        reasons.append("missing_source_scope")
    if not _clean(source_revision):
        reasons.append("missing_source_revision")
    if not _clean(access_policy_digest).startswith("sha256:"):
        reasons.append("invalid_access_policy_digest")

    policy_receipt: MemexAccessPolicyReceipt | None = None
    if access_policy_receipt is not None:
        policy_validation = validate_memex_access_policy_receipt(
            access_policy_receipt,
            expected_foundup_id=foundup_id,
            expected_source_scope=_clean(source_scope),
            now_iso=now_iso,
        )
        if not policy_validation.accepted or policy_validation.receipt is None:
            reasons.extend(
                f"access_policy_receipt:{reason}"
                for reason in policy_validation.rejection_reasons
            )
        else:
            policy_receipt = policy_validation.receipt
            if (
                access_policy_digest != DEFAULT_ACCESS_POLICY_DIGEST
                and _clean(access_policy_digest) != policy_receipt.receipt_id
            ):
                reasons.append("access_policy_digest_mismatch")
            access_policy_digest = policy_receipt.receipt_id

    candidate_sections = _candidate_sections(memex_view)
    records: list[MemexProjectionRecord] = []
    rejected: list[str] = []
    for label, payload in candidate_sections:
        if policy_receipt is not None and not section_allowed_by_policy(label, policy_receipt):
            rejected.append(f"access_policy_denied_record:{label}")
            continue
        if policy_receipt is not None and len(records) >= policy_receipt.max_records:
            rejected.append(f"access_policy_max_records:{label}")
            continue
        if _contains_secret(payload):
            rejected.append(f"secret_bearing_record:{label}")
            continue
        record = _record_from_section(
            label=label,
            payload=payload,
            foundup_id=foundup_id,
            memex_snapshot_id=memex_snapshot_id,
            source_scope=_clean(source_scope),
            source_revision=_clean(source_revision),
            access_policy_digest=_clean(access_policy_digest),
            snapshot_id=snapshot_id,
            snapshot_digest=snapshot_digest,
        )
        records.append(record)

    if not records:
        reasons.append("no_projectable_memex_records")
    if reasons:
        return _reject(*reasons, *rejected)

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "records": [
            {
                "record_id": record.record_id,
                "content_digest": record.content_digest,
                "source_class": record.source_class,
            }
            for record in records
        ],
        "rejected": rejected,
    }
    content_manifest_digest = digest_json(manifest)
    receipt_payload = {
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "memex_snapshot_id": memex_snapshot_id,
        "source_scope": _clean(source_scope),
        "source_revision": _clean(source_revision),
        "content_manifest_digest": content_manifest_digest,
        "created_at": now_iso or datetime.now(timezone.utc).isoformat(),
        "access_policy_digest": _clean(access_policy_digest),
        "records_indexed": len(records),
        "records_rejected": len(rejected),
        "holoindex_generation_id": _clean(holoindex_generation_id),
        "verification": "PASS",
        "rejected_reasons": tuple(rejected),
        "no_holoindex_write_performed": True,
        "no_memex_write_performed": True,
        "no_brain_write_performed": True,
        "no_breadcrumb_write_performed": True,
    }
    receipt = MemexSnapshotProjectionReceipt(
        **receipt_payload,
        receipt_id=digest_json(receipt_payload),
    )
    return MemexProjectionResult(
        accepted=True,
        status=PROJECTION_ACCEPTED,
        records=tuple(records),
        receipt=receipt,
        rejection_reasons=(),
    )


def _candidate_sections(memex_view: Mapping[str, Any]) -> tuple[tuple[str, Any], ...]:
    sections: list[tuple[str, Any]] = []
    for key in ("identity", "current_state", "roadmap_state"):
        value = memex_view.get(key)
        if isinstance(value, Mapping) and value:
            sections.append((key, dict(value)))
    outcomes = memex_view.get("verified_outcomes")
    if isinstance(outcomes, Sequence) and not isinstance(outcomes, (str, bytes)):
        for index, outcome in enumerate(outcomes):
            if isinstance(outcome, Mapping):
                sections.append((f"verified_outcome:{index}", dict(outcome)))
    return tuple(sections)


def _record_from_section(
    *,
    label: str,
    payload: Any,
    foundup_id: str,
    memex_snapshot_id: str,
    source_scope: str,
    source_revision: str,
    access_policy_digest: str,
    snapshot_id: str,
    snapshot_digest: str,
) -> MemexProjectionRecord:
    text = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)
    content_digest = "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()
    record_payload = {
        "foundup_id": foundup_id,
        "label": label,
        "memex_snapshot_id": memex_snapshot_id,
        "source_revision": source_revision,
        "content_digest": content_digest,
        "access_policy_digest": access_policy_digest,
    }
    record_id = digest_json(record_payload)
    return MemexProjectionRecord(
        record_id=record_id,
        source_class=SOURCE_CLASS_MEMEX,
        foundup_id=foundup_id,
        memex_snapshot_id=memex_snapshot_id,
        source_scope=source_scope,
        source_revision=source_revision,
        title=f"{foundup_id} memex {label}",
        text=text,
        metadata={
            "source_class": SOURCE_CLASS_MEMEX,
            "foundup_id": foundup_id,
            "memex_snapshot_id": memex_snapshot_id,
            "snapshot_id": snapshot_id,
            "snapshot_content_digest": snapshot_digest,
            "section": label,
            "access_policy_digest": access_policy_digest,
            "source_scope": source_scope,
            "source_revision": source_revision,
        },
        content_digest=content_digest,
    )


def _reject(*reasons: str) -> MemexProjectionResult:
    clean_reasons = tuple(dict.fromkeys(reason for reason in reasons if reason))
    return MemexProjectionResult(
        accepted=False,
        status=PROJECTION_REJECTED,
        records=(),
        receipt=None,
        rejection_reasons=clean_reasons,
    )


def _contains_secret(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(_contains_secret(key) or _contains_secret(item) for key, item in value.items())
    if isinstance(value, (list, tuple)):
        return any(_contains_secret(item) for item in value)
    return bool(_SECRET_RE.search(str(value)))


def _clean(value: Any) -> str:
    return str(value or "").strip()


__all__ = [
    "DEFAULT_ACCESS_POLICY_DIGEST",
    "MemexProjectionRecord",
    "MemexProjectionResult",
    "MemexSnapshotProjectionReceipt",
    "PROJECTION_ACCEPTED",
    "PROJECTION_REJECTED",
    "RECEIPT_SCHEMA_VERSION",
    "SCHEMA_VERSION",
    "project_foundup_memex_to_holoindex_shadow",
]
