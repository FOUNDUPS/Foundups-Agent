"""Read-only FoundUp Brain component for FoundUp Memex current-state assembly.

Canonical public terminology is FoundUp Memex. Brain remains the durable
consolidation component inside the complete Memex. This module is retained as
the proven compatibility implementation behind `foundup_memex_current_state`.

WSP_00 / WSP_97 boundary:
- OBSERVED inputs only: an accepted RedDog operational snapshot plus scoped
  FoundUp identity, roadmap metadata, and verified-outcome metadata.
- No Brain, Breadcrumb, roadmap, HoloIndex, queue, worker, repository, CABR,
  stakeholder, delegate, or governance write/authority.
- Historical Brain/Breadcrumb evidence cannot override current repo/work state.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Mapping, Sequence

from modules.communication.moltbot_bridge.src.foundup_memex_verified_outcome_authenticity import (
    consume_verified_foundup_memex_outcome,
    is_verified_foundup_memex_outcome_capability,
)

from modules.communication.moltbot_bridge.src.reddog_operational_context_snapshot import (
    FRESH,
    SOURCE_BRAIN,
    SOURCE_BREADCRUMBS,
    SOURCE_HOLOINDEX,
    SOURCE_REPO,
    SOURCE_WORK_STATE,
    SNAPSHOT_SCHEMA_VERSION,
    OperationalContextSnapshot,
)

FOUNDUP_BRAIN_VIEW_SCHEMA_VERSION = "foundup_brain_current_state.v1"
FOUNDUP_BRAIN_VIEW_ACCEPTED = "FOUNDUP_BRAIN_VIEW_ACCEPTED"
FOUNDUP_BRAIN_VIEW_REJECTED = "FOUNDUP_BRAIN_VIEW_REJECTED"

_REQUIRED_SNAPSHOT_SOURCES = (
    SOURCE_REPO,
    SOURCE_WORK_STATE,
    SOURCE_HOLOINDEX,
    SOURCE_BRAIN,
    SOURCE_BREADCRUMBS,
)
_SECRET_RE = re.compile(
    r"(?i)(api[_-]?key|secret|password|private[_-]?key|bearer\s+[A-Za-z0-9._-]+|sk-[A-Za-z0-9_-]+)"
)


@dataclass(frozen=True)
class FoundUpBrainView:
    """Deterministic read-only cognition view for one FoundUp."""

    schema_version: str
    foundup_brain_view_id: str
    foundup_id: str
    snapshot_id: str
    snapshot_content_digest: str
    identity: dict[str, Any]
    current_state: dict[str, Any]
    source_receipts: dict[str, dict[str, Any]]
    roadmap_state: dict[str, Any]
    verified_outcomes: tuple[dict[str, Any], ...]
    learning_candidates: tuple[dict[str, Any], ...] = ()
    roadmap_signals: tuple[dict[str, Any], ...] = ()
    assembly_receipt: dict[str, Any] | None = None
    invariants: dict[str, bool] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FoundUpBrainAssemblyResult:
    """Fail-closed result for FoundUp Brain component assembly."""

    accepted: bool
    status: str
    view: FoundUpBrainView | None
    rejection_reasons: tuple[str, ...]
    no_brain_write_performed: bool = True
    no_breadcrumb_write_performed: bool = True
    no_roadmap_mutation_performed: bool = True
    no_holoindex_mutation_performed: bool = True
    no_queue_mutation_performed: bool = True
    no_worker_spawn_performed: bool = True
    no_repo_mutation_performed: bool = True

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["view"] = self.view.to_dict() if self.view else None
        return data


def assemble_foundup_brain_current_state(
    *,
    foundup_id: str,
    snapshot: OperationalContextSnapshot,
    identity: Mapping[str, Any],
    roadmap_state: Mapping[str, Any] | None = None,
    verified_outcomes: Sequence[Any] = (),
    now_iso: str | None = None,
    resident_mode: bool = True,
    legacy_single_foundup_compatibility: bool = False,
    policy_foundup_scope: Sequence[str] | None = None,
) -> FoundUpBrainAssemblyResult:
    """Assemble one FoundUp's current cognition from existing receipts."""

    reasons: list[str] = []
    normalized_foundup_id = str(foundup_id).strip()
    if not normalized_foundup_id:
        reasons.append("missing_foundup_id")

    if snapshot.schema_version != SNAPSHOT_SCHEMA_VERSION:
        reasons.append("unsupported_snapshot_schema")
    if snapshot.rejection_reasons:
        reasons.append("snapshot_not_accepted")
    if not snapshot.snapshot_receipt_id or not snapshot.snapshot_content_digest:
        reasons.append("missing_snapshot_binding")
    if now_iso and _snapshot_expired(snapshot.valid_until, now_iso):
        reasons.append("snapshot_expired")

    receipts = {receipt.source: receipt.to_dict() for receipt in snapshot.source_receipts}
    for source in _REQUIRED_SNAPSHOT_SOURCES:
        receipt = receipts.get(source)
        if receipt is None:
            reasons.append(f"missing_source_receipt:{source}")
            continue
        if receipt.get("freshness") != FRESH:
            reasons.append(f"source_not_fresh:{source}")

    identity_clean = _normalize_identity(identity)
    if not identity_clean.get("name"):
        reasons.append("missing_identity_name")
    identity_foundup_id = str(identity_clean.get("foundup_id", "")).strip()
    if not identity_foundup_id:
        if resident_mode and not legacy_single_foundup_compatibility:
            reasons.append("identity_missing_foundup_id")
        elif legacy_single_foundup_compatibility:
            identity_clean["scope_origin"] = "legacy_single_foundup_compatibility"
    elif identity_foundup_id != normalized_foundup_id:
        reasons.append("identity_foundup_id_mismatch")
    identity_clean["foundup_id"] = normalized_foundup_id

    policy_scope = tuple(str(item).strip() for item in (policy_foundup_scope or ()) if str(item).strip())
    if resident_mode:
        if policy_scope != (normalized_foundup_id,):
            reasons.append("policy_foundup_scope_mismatch")

    roadmap_clean = _normalize_roadmap_state(
        roadmap_state,
        normalized_foundup_id,
        reasons,
        resident_mode=resident_mode,
        legacy_single_foundup_compatibility=legacy_single_foundup_compatibility,
    )
    outcomes_clean = _verified_outcome_projections(
        verified_outcomes,
        foundup_id=normalized_foundup_id,
        snapshot_id=snapshot.snapshot_receipt_id,
        snapshot_content_digest=snapshot.snapshot_content_digest,
        reasons=reasons,
        now_iso=now_iso,
        resident_mode=resident_mode,
        legacy_single_foundup_compatibility=legacy_single_foundup_compatibility,
    )
    active_work, excluded_active_work = _scope_work_records(
        snapshot.work_state.get("worker_claims", ()),
        normalized_foundup_id,
        "worker_claim",
        reasons,
        resident_mode=resident_mode,
        legacy_single_foundup_compatibility=legacy_single_foundup_compatibility,
    )
    queued_work, excluded_queued_work = _scope_work_records(
        snapshot.work_state.get("wre_queue_items", ()),
        normalized_foundup_id,
        "queue_item",
        reasons,
        resident_mode=resident_mode,
        legacy_single_foundup_compatibility=legacy_single_foundup_compatibility,
    )
    excluded_records = excluded_active_work + excluded_queued_work
    excluded_record_digest = _digest(excluded_records)
    assembly_receipt_payload = {
        "schema_version": "foundup_memex_assembly_receipt.v1",
        "foundup_id": normalized_foundup_id,
        "snapshot_id": snapshot.snapshot_receipt_id,
        "snapshot_content_digest": snapshot.snapshot_content_digest,
        "resident_mode": resident_mode is True,
        "legacy_single_foundup_compatibility": legacy_single_foundup_compatibility is True,
        "policy_foundup_scope": policy_scope,
        "included_worker_claims": len(active_work),
        "included_queue_items": len(queued_work),
        "excluded_record_count": len(excluded_records),
        "excluded_record_digest": excluded_record_digest,
        "no_brain_write_performed": True,
        "no_breadcrumb_write_performed": True,
        "no_holoindex_mutation_performed": True,
        "no_queue_mutation_performed": True,
    }
    assembly_receipt = {
        **assembly_receipt_payload,
        "receipt_id": _digest(assembly_receipt_payload),
    }

    candidate_payload = {
        "identity": identity_clean,
        "roadmap_state": roadmap_clean,
        "verified_outcomes": outcomes_clean,
        "active_work": active_work,
        "queued_work": queued_work,
    }
    if _contains_secret(candidate_payload):
        reasons.append("secret_bearing_input_rejected")

    if reasons:
        return FoundUpBrainAssemblyResult(
            accepted=False,
            status=FOUNDUP_BRAIN_VIEW_REJECTED,
            view=None,
            rejection_reasons=tuple(sorted(set(reasons))),
        )

    current_state = {
        "repo_head_sha": str(snapshot.repo_state.get("head_sha", "")),
        "work_state_revision": str(snapshot.work_state.get("revision", "")),
        "selected_slice": str(snapshot.work_state.get("selected_slice", "")),
        "active_work": active_work,
        "queued_work": queued_work,
        "breadcrumb_scope": str(snapshot.breadcrumbs_state.get("scope", "")),
        "breadcrumb_high_watermark": str(snapshot.breadcrumbs_state.get("high_watermark", "")),
        "breadcrumb_record_count": int(snapshot.breadcrumbs_state.get("record_count", 0)),
        "brain_signature_digest": str(snapshot.brain_state.get("signature_digest", "")),
        "holoindex_repo_head_sha": str(snapshot.holoindex_state.get("repo_head_sha", "")),
    }

    content = {
        "schema_version": FOUNDUP_BRAIN_VIEW_SCHEMA_VERSION,
        "foundup_id": normalized_foundup_id,
        "snapshot_id": snapshot.snapshot_receipt_id,
        "snapshot_content_digest": snapshot.snapshot_content_digest,
        "identity": identity_clean,
        "current_state": current_state,
        "source_receipts": receipts,
        "roadmap_state": roadmap_clean,
        "verified_outcomes": outcomes_clean,
        "learning_candidates": (),
        "roadmap_signals": (),
        "assembly_receipt": assembly_receipt,
    }
    view_id = _digest(content)
    view = FoundUpBrainView(
        schema_version=FOUNDUP_BRAIN_VIEW_SCHEMA_VERSION,
        foundup_brain_view_id=view_id,
        foundup_id=normalized_foundup_id,
        snapshot_id=snapshot.snapshot_receipt_id,
        snapshot_content_digest=snapshot.snapshot_content_digest,
        identity=identity_clean,
        current_state=current_state,
        source_receipts=receipts,
        roadmap_state=roadmap_clean,
        verified_outcomes=outcomes_clean,
        invariants={
            "read_only": True,
            "no_brain_write": True,
            "no_breadcrumb_write": True,
            "no_roadmap_mutation": True,
            "no_holoindex_mutation": True,
            "no_queue_mutation": True,
            "no_worker_spawn": True,
            "no_repo_mutation": True,
        },
        assembly_receipt=assembly_receipt,
    )
    return FoundUpBrainAssemblyResult(
        accepted=True,
        status=FOUNDUP_BRAIN_VIEW_ACCEPTED,
        view=view,
        rejection_reasons=(),
    )


def _normalize_identity(identity: Mapping[str, Any]) -> dict[str, Any]:
    allowed = ("foundup_id", "name", "stage", "purpose", "outcome", "solution", "pain")
    return {key: str(identity.get(key, "")).strip() for key in allowed}


def _normalize_roadmap_state(
    roadmap_state: Mapping[str, Any] | None,
    foundup_id: str,
    reasons: list[str],
    *,
    resident_mode: bool,
    legacy_single_foundup_compatibility: bool,
) -> dict[str, Any]:
    data = dict(roadmap_state or {})
    scoped_id = str(data.get("foundup_id", "")).strip()
    scope_origin = ""
    if not scoped_id:
        if resident_mode and not legacy_single_foundup_compatibility:
            reasons.append("roadmap_missing_foundup_id")
        elif legacy_single_foundup_compatibility:
            scope_origin = "legacy_single_foundup_compatibility"
    elif scoped_id != foundup_id:
        reasons.append("roadmap_foundup_id_mismatch")
    roadmap_id = str(data.get("roadmap_id", "")).strip()
    version = str(data.get("version", "")).strip()
    content_digest = str(data.get("content_digest", "")).strip()
    if not roadmap_id:
        reasons.append("missing_roadmap_id")
    if not version:
        reasons.append("missing_roadmap_version")
    if not content_digest:
        reasons.append("missing_roadmap_content_digest")
    return {
        "foundup_id": foundup_id,
        "roadmap_id": roadmap_id,
        "version": version,
        "content_digest": content_digest,
        "active_item_ids": tuple(str(value) for value in data.get("active_item_ids", ())),
        "blocked_item_ids": tuple(str(value) for value in data.get("blocked_item_ids", ())),
        "scope_origin": scope_origin,
    }


def _normalize_verified_outcome(
    outcome: Mapping[str, Any],
    foundup_id: str,
    reasons: list[str],
    *,
    resident_mode: bool,
    legacy_single_foundup_compatibility: bool,
) -> dict[str, Any]:
    scoped_id = str(outcome.get("foundup_id", "")).strip()
    scope_origin = ""
    if not scoped_id:
        if resident_mode and not legacy_single_foundup_compatibility:
            reasons.append("verified_outcome_missing_foundup_id")
        elif legacy_single_foundup_compatibility:
            scope_origin = "legacy_single_foundup_compatibility"
    elif scoped_id != foundup_id:
        reasons.append("verified_outcome_foundup_id_mismatch")
    accepted = bool(outcome.get("accepted", False))
    held_out_passed = bool(outcome.get("held_out_passed", False))
    if not accepted or not held_out_passed:
        reasons.append("unverified_outcome_rejected")
    required_ids = {
        "outcome_id": str(outcome.get("outcome_id", "")).strip(),
        "verification_receipt_id": str(outcome.get("verification_receipt_id", "")).strip(),
        "held_out_receipt_id": str(outcome.get("held_out_receipt_id", "")).strip(),
        "head_sha": str(outcome.get("head_sha", "")).strip(),
        "content_digest": str(outcome.get("content_digest", "")).strip(),
    }
    for key, value in required_ids.items():
        if not value:
            reasons.append(f"missing_verified_outcome_field:{key}")
    return {
        "foundup_id": foundup_id,
        **required_ids,
        "accepted": accepted,
        "held_out_passed": held_out_passed,
        "scope_origin": scope_origin,
    }


def _verified_outcome_projections(
    outcomes: Sequence[Any],
    *,
    foundup_id: str,
    snapshot_id: str,
    snapshot_content_digest: str,
    reasons: list[str],
    now_iso: str | None,
    resident_mode: bool,
    legacy_single_foundup_compatibility: bool,
) -> tuple[dict[str, Any], ...]:
    """Consume authenticated outcomes, or an explicit non-resident legacy form."""

    projected: list[dict[str, Any]] = []
    for outcome in outcomes:
        if resident_mode:
            if not is_verified_foundup_memex_outcome_capability(outcome):
                reasons.append("verified_outcome_runtime_binding_required")
                continue
            now_epoch = _iso_epoch(now_iso)
            if now_epoch is None:
                reasons.append("verified_outcome_trusted_clock_required")
                continue
            consumed = consume_verified_foundup_memex_outcome(
                outcome,
                expected_foundup_id=foundup_id,
                expected_snapshot_id=snapshot_id,
                expected_snapshot_content_digest=snapshot_content_digest,
                now_epoch=now_epoch,
            )
            if consumed is None:
                reasons.append("verified_outcome_capability_rejected")
                continue
            projected.append(dict(consumed))
            continue
        if not legacy_single_foundup_compatibility or not isinstance(outcome, Mapping):
            reasons.append("verified_outcome_legacy_compatibility_required")
            continue
        projected.append(
            _normalize_verified_outcome(
                outcome,
                foundup_id,
                reasons,
                resident_mode=False,
                legacy_single_foundup_compatibility=True,
            )
        )
    return tuple(projected)


def _iso_epoch(value: str | None) -> int | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return int(parsed.timestamp())


def _scope_work_records(
    records: Sequence[Mapping[str, Any]],
    foundup_id: str,
    record_kind: str,
    reasons: list[str],
    *,
    resident_mode: bool,
    legacy_single_foundup_compatibility: bool,
) -> tuple[tuple[dict[str, Any], ...], tuple[dict[str, Any], ...]]:
    scoped: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    for index, record in enumerate(records):
        data = dict(record)
        record_foundup_id = str(data.get("foundup_id", "")).strip()
        if record_foundup_id and record_foundup_id != foundup_id:
            excluded.append(
                _excluded_record_summary(
                    record_kind=record_kind,
                    record=data,
                    index=index,
                    foundup_id=record_foundup_id,
                    reason=f"{record_kind}_foundup_id_mismatch",
                )
            )
            continue
        if not record_foundup_id:
            if resident_mode and not legacy_single_foundup_compatibility:
                reasons.append(f"{record_kind}_missing_foundup_id")
                excluded.append(
                    _excluded_record_summary(
                        record_kind=record_kind,
                        record=data,
                        index=index,
                        foundup_id="",
                        reason=f"{record_kind}_missing_foundup_id",
                    )
                )
                continue
            data["foundup_id"] = foundup_id
            data["scope_origin"] = "legacy_single_foundup_compatibility"
        scoped.append(data)
    return tuple(scoped), tuple(excluded)


def _excluded_record_summary(
    *,
    record_kind: str,
    record: Mapping[str, Any],
    index: int,
    foundup_id: str,
    reason: str,
) -> dict[str, Any]:
    identifier = (
        record.get("claim_id")
        or record.get("queue_item_id")
        or record.get("work_order_id")
        or record.get("slice_name")
        or record.get("selected_slice")
        or f"{record_kind}:{index}"
    )
    return {
        "record_kind": record_kind,
        "record_ref": str(identifier),
        "foundup_id": str(foundup_id),
        "reason": reason,
    }


def _snapshot_expired(valid_until: str, now_iso: str) -> bool:
    try:
        return datetime.fromisoformat(now_iso) > datetime.fromisoformat(valid_until)
    except (TypeError, ValueError):
        return True


def _contains_secret(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(_contains_secret(key) or _contains_secret(item) for key, item in value.items())
    if isinstance(value, (list, tuple)):
        return any(_contains_secret(item) for item in value)
    return bool(_SECRET_RE.search(str(value)))


def _digest(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()
