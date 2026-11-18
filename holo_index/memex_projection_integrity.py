"""Integrity gate for serialized Memex projection receipts.

This module rehydrates a caller-supplied Memex projection only after
recomputing every digest and binding that the projection adapter emitted. It is
read-only and never trusts an ``accepted: true`` field from serialized input.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from holo_index.memex_projection_adapter import (
    DEFAULT_ACCESS_POLICY_DIGEST,
    MemexProjectionRecord,
    MemexProjectionResult,
    MemexSnapshotProjectionReceipt,
    PROJECTION_ACCEPTED,
    PROJECTION_REJECTED,
    RECEIPT_SCHEMA_VERSION,
    SCHEMA_VERSION,
)
from holo_index.query_receipt import SOURCE_CLASS_MEMEX, digest_json


INTEGRITY_GATE_SCHEMA_VERSION = "holoindex_memex_projection_integrity_gate.v1"
DEFAULT_RUNTIME_MAX_AGE_SECONDS = 7 * 24 * 60 * 60


@dataclass(frozen=True)
class MemexProjectionIntegrityResult:
    """Result of rehydrating and verifying a Memex projection."""

    accepted: bool
    status: str
    projection: MemexProjectionResult | None
    rejection_reasons: tuple[str, ...]
    receipt_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": INTEGRITY_GATE_SCHEMA_VERSION,
            "accepted": self.accepted,
            "status": self.status,
            "projection": self.projection.to_dict() if self.projection else None,
            "rejection_reasons": list(self.rejection_reasons),
            "receipt_id": self.receipt_id,
        }


def verify_and_rehydrate_memex_projection(
    projection: MemexProjectionResult | Mapping[str, Any],
    *,
    runtime_mode: bool = False,
    now_iso: str | None = None,
    max_age_seconds: int | None = None,
    seen_receipt_ids: Sequence[str] = (),
    revoked_snapshot_ids: Sequence[str] = (),
    expected_foundup_id: str | None = None,
    expected_memex_snapshot_id: str | None = None,
    expected_source_scope: str | None = None,
    expected_source_revision: str | None = None,
    expected_access_policy_digest: str | None = None,
    expected_holoindex_generation_id: str | None = None,
    expected_operational_snapshot_id: str | None = None,
    expected_operational_snapshot_content_digest: str | None = None,
) -> MemexProjectionIntegrityResult:
    """Return a typed verified projection or fail closed.

    ``runtime_mode`` adds operational checks that are too strict for static unit
    fixtures: placeholder access policies are rejected, replay/revocation inputs
    are honored, and receipt age is bounded.
    """

    raw = _projection_to_mapping(projection)
    if raw is None:
        return _reject("projection_not_mapping")
    prior_reasons = _prior_rejection_reasons(raw)

    records_value = raw.get("records")
    if not isinstance(records_value, Sequence) or isinstance(records_value, (str, bytes)):
        return _reject(*prior_reasons, "projection_records_not_sequence")
    receipt_value = raw.get("receipt")
    if not isinstance(receipt_value, Mapping):
        return _reject(*prior_reasons, "missing_projection_receipt")

    records: list[MemexProjectionRecord] = []
    reasons: list[str] = []
    for index, item in enumerate(records_value):
        record, record_reasons = _record_from_mapping(item, index=index)
        reasons.extend(record_reasons)
        if record is not None:
            records.append(record)

    receipt, receipt_reasons = _receipt_from_mapping(receipt_value)
    reasons.extend(receipt_reasons)
    if receipt is None:
        return _reject(*prior_reasons, *reasons, "malformed_projection_receipt")

    if not records:
        reasons.append("no_projection_records")
    if receipt.schema_version != RECEIPT_SCHEMA_VERSION:
        reasons.append("schema_version_mismatch")
    if receipt.verification != "PASS":
        reasons.append("projection_verification_not_pass")
    if not receipt.holoindex_generation_id:
        reasons.append("missing_holoindex_generation_id")

    seen = {_clean(item) for item in seen_receipt_ids if _clean(item)}
    revoked = {_clean(item) for item in revoked_snapshot_ids if _clean(item)}
    if runtime_mode and receipt.receipt_id in seen:
        reasons.append("projection_receipt_replayed")
    if runtime_mode and receipt.memex_snapshot_id in revoked:
        reasons.append("projection_snapshot_revoked")

    if runtime_mode and receipt.access_policy_digest == DEFAULT_ACCESS_POLICY_DIGEST:
        reasons.append("placeholder_access_policy_digest")
    if not _is_sha256(receipt.access_policy_digest):
        reasons.append("invalid_access_policy_digest")

    age_reason = _expiry_reason(
        created_at=receipt.created_at,
        now_iso=now_iso,
        max_age_seconds=max_age_seconds if max_age_seconds is not None else (
            DEFAULT_RUNTIME_MAX_AGE_SECONDS if runtime_mode else None
        ),
    )
    if age_reason:
        reasons.append(age_reason)

    if receipt.records_indexed != len(records):
        reasons.append("records_indexed_count_mismatch")
    if receipt.records_rejected != len(receipt.rejected_reasons):
        reasons.append("records_rejected_count_mismatch")

    foundup_ids = {record.foundup_id for record in records if record.foundup_id}
    snapshot_ids = {record.memex_snapshot_id for record in records if record.memex_snapshot_id}
    scopes = {record.source_scope for record in records if record.source_scope}
    revisions = {record.source_revision for record in records if record.source_revision}
    policy_digests = {
        str(record.metadata.get("access_policy_digest") or "").strip()
        for record in records
        if isinstance(record.metadata, Mapping)
    }
    operational_snapshot_ids = {
        str(record.metadata.get("snapshot_id") or "").strip()
        for record in records
        if isinstance(record.metadata, Mapping)
    }
    operational_snapshot_content_digests = {
        str(record.metadata.get("snapshot_content_digest") or "").strip()
        for record in records
        if isinstance(record.metadata, Mapping)
    }

    if len(foundup_ids) != 1:
        reasons.append("mixed_foundup_records")
    if len(snapshot_ids) != 1 or (snapshot_ids and next(iter(snapshot_ids)) != receipt.memex_snapshot_id):
        reasons.append("mixed_snapshot_ids")
    if len(scopes) != 1 or (scopes and next(iter(scopes)) != receipt.source_scope):
        reasons.append("mixed_source_scope")
    if len(revisions) != 1 or (revisions and next(iter(revisions)) != receipt.source_revision):
        reasons.append("mixed_source_revision")
    if len(policy_digests) != 1 or (
        policy_digests and next(iter(policy_digests)) != receipt.access_policy_digest
    ):
        reasons.append("mixed_policy_digests")
    if len(operational_snapshot_ids) != 1 or not next(iter(operational_snapshot_ids or {""})):
        reasons.append("mixed_operational_snapshot_ids")
    if len(operational_snapshot_content_digests) != 1 or not next(
        iter(operational_snapshot_content_digests or {""})
    ):
        reasons.append("mixed_operational_snapshot_content_digests")

    if expected_foundup_id and foundup_ids != {_clean(expected_foundup_id)}:
        reasons.append("expected_foundup_mismatch")
    if expected_memex_snapshot_id and receipt.memex_snapshot_id != _clean(expected_memex_snapshot_id):
        reasons.append("expected_snapshot_mismatch")
    if expected_source_scope and receipt.source_scope != _clean(expected_source_scope):
        reasons.append("expected_source_scope_mismatch")
    if expected_source_revision and receipt.source_revision != _clean(expected_source_revision):
        reasons.append("expected_source_revision_mismatch")
    if expected_access_policy_digest and receipt.access_policy_digest != _clean(expected_access_policy_digest):
        reasons.append("expected_access_policy_mismatch")
    if expected_holoindex_generation_id and receipt.holoindex_generation_id != _clean(
        expected_holoindex_generation_id
    ):
        reasons.append("expected_generation_mismatch")
    if expected_operational_snapshot_id and operational_snapshot_ids != {
        _clean(expected_operational_snapshot_id)
    }:
        reasons.append("expected_operational_snapshot_id_mismatch")
    if expected_operational_snapshot_content_digest and operational_snapshot_content_digests != {
        _clean(expected_operational_snapshot_content_digest)
    }:
        reasons.append("expected_operational_snapshot_content_digest_mismatch")

    for record in records:
        reasons.extend(_record_integrity_reasons(record, receipt=receipt))

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
        "rejected": list(receipt.rejected_reasons),
    }
    if digest_json(manifest) != receipt.content_manifest_digest:
        reasons.append("content_manifest_digest_mismatch")

    receipt_payload = {
        "schema_version": receipt.schema_version,
        "memex_snapshot_id": receipt.memex_snapshot_id,
        "source_scope": receipt.source_scope,
        "source_revision": receipt.source_revision,
        "content_manifest_digest": receipt.content_manifest_digest,
        "created_at": receipt.created_at,
        "access_policy_digest": receipt.access_policy_digest,
        "records_indexed": receipt.records_indexed,
        "records_rejected": receipt.records_rejected,
        "holoindex_generation_id": receipt.holoindex_generation_id,
        "verification": receipt.verification,
        "rejected_reasons": tuple(receipt.rejected_reasons),
        "no_holoindex_write_performed": receipt.no_holoindex_write_performed,
        "no_memex_write_performed": receipt.no_memex_write_performed,
        "no_brain_write_performed": receipt.no_brain_write_performed,
        "no_breadcrumb_write_performed": receipt.no_breadcrumb_write_performed,
    }
    if digest_json(receipt_payload) != receipt.receipt_id:
        reasons.append("receipt_id_mismatch")

    if reasons:
        return _reject(*prior_reasons, *reasons)

    verified = MemexProjectionResult(
        accepted=True,
        status=PROJECTION_ACCEPTED,
        records=tuple(records),
        receipt=receipt,
        rejection_reasons=(),
    )
    gate_payload = {
        "schema_version": INTEGRITY_GATE_SCHEMA_VERSION,
        "projection_receipt_id": receipt.receipt_id,
        "record_ids": [record.record_id for record in records],
        "runtime_mode": runtime_mode is True,
    }
    return MemexProjectionIntegrityResult(
        accepted=True,
        status="MEMEX_PROJECTION_INTEGRITY_VERIFIED",
        projection=verified,
        rejection_reasons=(),
        receipt_id=digest_json(gate_payload),
    )


def _record_integrity_reasons(
    record: MemexProjectionRecord,
    *,
    receipt: MemexSnapshotProjectionReceipt,
) -> tuple[str, ...]:
    reasons: list[str] = []
    if record.source_class != SOURCE_CLASS_MEMEX:
        reasons.append("record_source_class_not_memex")
    if record.metadata.get("source_class") != SOURCE_CLASS_MEMEX:
        reasons.append("metadata_source_class_not_memex")
    if record.metadata.get("foundup_id") != record.foundup_id:
        reasons.append("metadata_foundup_mismatch")
    if record.metadata.get("memex_snapshot_id") != record.memex_snapshot_id:
        reasons.append("metadata_snapshot_mismatch")
    if record.metadata.get("source_scope") != record.source_scope:
        reasons.append("metadata_source_scope_mismatch")
    if record.metadata.get("source_revision") != record.source_revision:
        reasons.append("metadata_source_revision_mismatch")
    if record.metadata.get("access_policy_digest") != receipt.access_policy_digest:
        reasons.append("metadata_access_policy_mismatch")
    if not str(record.metadata.get("snapshot_id") or "").strip():
        reasons.append("metadata_snapshot_id_missing")
    if not str(record.metadata.get("snapshot_content_digest") or "").strip():
        reasons.append("metadata_snapshot_content_digest_missing")
    section = str(record.metadata.get("section") or "").strip()
    if not section:
        reasons.append("missing_record_section")
    computed_digest = _content_digest(record.text)
    if computed_digest != record.content_digest:
        reasons.append("record_content_digest_mismatch")
    record_payload = {
        "foundup_id": record.foundup_id,
        "label": section,
        "memex_snapshot_id": record.memex_snapshot_id,
        "source_revision": record.source_revision,
        "content_digest": record.content_digest,
        "access_policy_digest": receipt.access_policy_digest,
    }
    if digest_json(record_payload) != record.record_id:
        reasons.append("record_id_mismatch")
    return tuple(reasons)


def _projection_to_mapping(value: MemexProjectionResult | Mapping[str, Any]) -> Mapping[str, Any] | None:
    if isinstance(value, MemexProjectionResult):
        return value.to_dict()
    if isinstance(value, Mapping):
        return value
    return None


def _prior_rejection_reasons(value: Mapping[str, Any]) -> tuple[str, ...]:
    reasons = value.get("rejection_reasons")
    if not isinstance(reasons, Sequence) or isinstance(reasons, (str, bytes)):
        return ()
    return tuple(_text(item) for item in reasons if _text(item))


def _record_from_mapping(value: Any, *, index: int) -> tuple[MemexProjectionRecord | None, tuple[str, ...]]:
    if isinstance(value, MemexProjectionRecord):
        return value, ()
    if not isinstance(value, Mapping):
        return None, (f"record_not_mapping:{index}",)
    try:
        metadata = value.get("metadata")
        if not isinstance(metadata, Mapping):
            return None, (f"record_metadata_not_mapping:{index}",)
        record = MemexProjectionRecord(
            record_id=_clean(value.get("record_id")),
            source_class=_clean(value.get("source_class")),
            foundup_id=_clean(value.get("foundup_id")),
            memex_snapshot_id=_clean(value.get("memex_snapshot_id")),
            source_scope=_clean(value.get("source_scope")),
            source_revision=_clean(value.get("source_revision")),
            title=_clean(value.get("title")),
            text=_text(value.get("text")),
            metadata={str(key): item for key, item in dict(metadata).items()},
            content_digest=_clean(value.get("content_digest")),
        )
    except Exception:
        return None, (f"record_malformed:{index}",)
    required = (
        record.record_id,
        record.source_class,
        record.foundup_id,
        record.memex_snapshot_id,
        record.source_scope,
        record.source_revision,
        record.text,
        record.content_digest,
    )
    if any(not item for item in required):
        return record, (f"record_missing_required_field:{index}",)
    return record, ()


def _receipt_from_mapping(value: Mapping[str, Any]) -> tuple[MemexSnapshotProjectionReceipt | None, tuple[str, ...]]:
    try:
        receipt = MemexSnapshotProjectionReceipt(
            schema_version=_clean(value.get("schema_version")),
            memex_snapshot_id=_clean(value.get("memex_snapshot_id")),
            source_scope=_clean(value.get("source_scope")),
            source_revision=_clean(value.get("source_revision")),
            content_manifest_digest=_clean(value.get("content_manifest_digest")),
            created_at=_clean(value.get("created_at")),
            access_policy_digest=_clean(value.get("access_policy_digest")),
            records_indexed=int(value.get("records_indexed")),
            records_rejected=int(value.get("records_rejected")),
            holoindex_generation_id=_clean(value.get("holoindex_generation_id")),
            verification=_clean(value.get("verification")),
            rejected_reasons=tuple(_text(item) for item in value.get("rejected_reasons") or ()),
            no_holoindex_write_performed=bool(value.get("no_holoindex_write_performed")),
            no_memex_write_performed=bool(value.get("no_memex_write_performed")),
            no_brain_write_performed=bool(value.get("no_brain_write_performed")),
            no_breadcrumb_write_performed=bool(value.get("no_breadcrumb_write_performed")),
            receipt_id=_clean(value.get("receipt_id")),
        )
    except Exception:
        return None, ("receipt_malformed",)
    required = (
        receipt.schema_version,
        receipt.memex_snapshot_id,
        receipt.source_scope,
        receipt.source_revision,
        receipt.content_manifest_digest,
        receipt.created_at,
        receipt.access_policy_digest,
        receipt.holoindex_generation_id,
        receipt.verification,
        receipt.receipt_id,
    )
    if any(not item for item in required):
        return receipt, ("receipt_missing_required_field",)
    if not (
        receipt.no_holoindex_write_performed
        and receipt.no_memex_write_performed
        and receipt.no_brain_write_performed
        and receipt.no_breadcrumb_write_performed
    ):
        return receipt, ("side_effect_attestation_missing",)
    return receipt, ()


def _expiry_reason(*, created_at: str, now_iso: str | None, max_age_seconds: int | None) -> str:
    if max_age_seconds is None:
        return ""
    try:
        created = _parse_time(created_at)
        now = _parse_time(now_iso) if now_iso else datetime.now(timezone.utc)
    except Exception:
        return "projection_timestamp_malformed"
    if created > now:
        return "projection_created_in_future"
    if (now - created).total_seconds() > int(max_age_seconds):
        return "projection_expired"
    return ""


def _parse_time(value: str | None) -> datetime:
    text = _clean(value)
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _content_digest(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def _is_sha256(value: str) -> bool:
    text = _clean(value)
    if not text.startswith("sha256:") or len(text) != 71:
        return False
    return all(char in "0123456789abcdef" for char in text.removeprefix("sha256:"))


def _reject(*reasons: str) -> MemexProjectionIntegrityResult:
    clean_reasons = tuple(dict.fromkeys(reason for reason in reasons if reason))
    payload = {
        "schema_version": INTEGRITY_GATE_SCHEMA_VERSION,
        "accepted": False,
        "rejection_reasons": clean_reasons,
    }
    return MemexProjectionIntegrityResult(
        accepted=False,
        status=PROJECTION_REJECTED,
        projection=None,
        rejection_reasons=clean_reasons,
        receipt_id=digest_json(payload),
    )


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)


__all__ = [
    "DEFAULT_RUNTIME_MAX_AGE_SECONDS",
    "INTEGRITY_GATE_SCHEMA_VERSION",
    "MemexProjectionIntegrityResult",
    "verify_and_rehydrate_memex_projection",
]
