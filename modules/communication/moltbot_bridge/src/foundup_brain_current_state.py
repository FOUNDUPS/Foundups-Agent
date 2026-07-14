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
    verified_outcomes: Sequence[Mapping[str, Any]] = (),
    now_iso: str | None = None,
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
    identity_foundup_id = str(identity_clean.get("foundup_id", normalized_foundup_id)).strip()
    if identity_foundup_id and identity_foundup_id != normalized_foundup_id:
        reasons.append("identity_foundup_id_mismatch")
    identity_clean["foundup_id"] = normalized_foundup_id

    roadmap_clean = _normalize_roadmap_state(roadmap_state, normalized_foundup_id, reasons)
    outcomes_clean = tuple(
        _normalize_verified_outcome(outcome, normalized_foundup_id, reasons)
        for outcome in verified_outcomes
    )
    active_work = _scope_work_records(
        snapshot.work_state.get("worker_claims", ()),
        normalized_foundup_id,
        "worker_claim",
        reasons,
    )
    queued_work = _scope_work_records(
        snapshot.work_state.get("wre_queue_items", ()),
        normalized_foundup_id,
        "queue_item",
        reasons,
    )

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
) -> dict[str, Any]:
    data = dict(roadmap_state or {})
    scoped_id = str(data.get("foundup_id", foundup_id)).strip()
    if scoped_id and scoped_id != foundup_id:
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
    }


def _normalize_verified_outcome(
    outcome: Mapping[str, Any],
    foundup_id: str,
    reasons: list[str],
) -> dict[str, Any]:
    scoped_id = str(outcome.get("foundup_id", foundup_id)).strip()
    if scoped_id and scoped_id != foundup_id:
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
    }


def _scope_work_records(
    records: Sequence[Mapping[str, Any]],
    foundup_id: str,
    record_kind: str,
    reasons: list[str],
) -> tuple[dict[str, Any], ...]:
    scoped: list[dict[str, Any]] = []
    for record in records:
        data = dict(record)
        record_foundup_id = str(data.get("foundup_id", "")).strip()
        if record_foundup_id and record_foundup_id != foundup_id:
            reasons.append(f"{record_kind}_foundup_id_mismatch")
            continue
        if not record_foundup_id:
            data["foundup_id"] = foundup_id
            data["scope_origin"] = "legacy_single_foundup_poc"
        scoped.append(data)
    return tuple(scoped)


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
