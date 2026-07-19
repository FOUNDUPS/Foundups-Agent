"""RedDog authoritative work-state refresh runtime.

This module is the mutating successor to
``reddog_work_ledger_refresh_plan_dryrun``.  It does not fetch GitHub, call W10,
spawn workers, mutate HoloIndex, or execute WRE work.  Callers provide already
observed GitHub/W10/ledger state, and this module atomically commits a single
authoritative work-state snapshot containing:

* a freshness receipt for the observed inputs,
* conflict-free reconciled slice state,
* a durable worker claim for the selected open slice, and
* a synchronized WRE queue item bound to that claim.

The runtime writes only through an explicit store implementation.  The default
JSON store writes one caller-selected file with an atomic replace.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional, Protocol, Sequence, Tuple

from modules.communication.moltbot_bridge.src.reddog_lane_state_reconciler import (
    LaneReconciliationReport,
    LaneSliceRecord,
    LaneSourceSnapshot,
    parse_active_slice_ledger,
    parse_work_ledger_json,
    reconcile_lane_sources,
)
from modules.communication.moltbot_bridge.src.reddog_wsp15_allocation_receipt import (
    allocate_reddog_wsp15_receipt,
)
from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    runtime_operation_lock,
)


AUTHORITATIVE_REFRESH_APPLIED = "AUTHORITATIVE_REFRESH_APPLIED"
AUTHORITATIVE_REFRESH_REJECTED = "AUTHORITATIVE_REFRESH_REJECTED"
WRE_QUEUE_SYNCED = "WRE_QUEUE_SYNCED"
WRE_QUEUE_NOT_REQUIRED = "WRE_QUEUE_NOT_REQUIRED"
WORK_STATE_SCHEMA_VERSION = "reddog_authoritative_work_state.v1"

_OPEN_STATUSES = {"PROPOSED", "ASSIGNED", "IN_PROGRESS", "STAGED_FOR_W10", "PR_OPEN", "BLOCKED", "PARKED"}
_CLOSED_STATUSES = {"MERGED", "CLOSED", "SUPERSEDED", "ABANDONED"}
_STATUS_ALIASES = {
    "OPEN": "PR_OPEN",
    "DRAFT": "PR_OPEN",
    "READY": "PR_OPEN",
    "LANDED": "MERGED",
    "DONE": "MERGED",
    "DEFERRED": "PARKED",
}
_SOURCE_PRECEDENCE = {
    "github_pr": 0,
    "w10_report": 1,
    "work_ledger_json": 2,
    "active_slice_ledger": 3,
}


@dataclass(frozen=True)
class WorkStateSourceBundle:
    """Observed source plus the time this runtime received it."""

    snapshot: LaneSourceSnapshot
    observed_at: str
    required: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot": self.snapshot.to_dict(),
            "observed_at": self.observed_at,
            "required": self.required,
        }


@dataclass(frozen=True)
class WorkStateFreshnessReceipt:
    """Freshness receipt for all inputs consumed by the refresh runtime."""

    receipt_id: str
    generated_at: str
    max_source_age_seconds: int
    source_ids: Tuple[str, ...]
    source_digests: Dict[str, str]
    stale_source_ids: Tuple[str, ...]
    missing_source_ids: Tuple[str, ...]
    fresh: bool

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DurableWorkerClaim:
    """Durable claim written into the authoritative work-state snapshot."""

    claim_id: str
    slice_id: str
    worker_id: str
    lane_id: Optional[str]
    claimed_at: str
    expires_at: str
    reconciliation_report_id: str
    freshness_receipt_id: str
    status: str = "ACTIVE"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class WREQueueItem:
    """Queue item synchronized for WRE consumption; it does not execute work."""

    queue_item_id: str
    slice_id: str
    claim_id: str
    worker_id: str
    status: str
    enqueued_at: str
    evidence_refs: Tuple[str, ...]
    wsp15_allocation_receipt: Mapping[str, Any]
    no_execution_performed: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class WREQueueSyncReceipt:
    """Receipt proving queue synchronization was included in the atomic commit."""

    sync_id: str
    status: str
    queue_item_ids: Tuple[str, ...]
    selected_slice: Optional[str]
    rejection_reasons: Tuple[str, ...]
    no_execution_performed: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AuthoritativeWorkStateRefreshReceipt:
    """Top-level runtime receipt."""

    refresh_id: str
    status: str
    generated_at: str
    reconciliation_report_id: Optional[str]
    freshness_receipt_id: Optional[str]
    selected_slice: Optional[str]
    durable_claim_id: Optional[str]
    queue_sync_id: Optional[str]
    rejection_reasons: Tuple[str, ...]
    committed_revision: Optional[str]
    no_holoindex_mutation_performed: bool = True
    no_worker_spawn_performed: bool = True
    no_execution_performed: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AuthoritativeWorkStateRefreshResult:
    """Result wrapper returned by refresh_authoritative_work_state_runtime."""

    accepted: bool
    receipt: AuthoritativeWorkStateRefreshReceipt
    freshness_receipt: Optional[WorkStateFreshnessReceipt] = None
    queue_sync_receipt: Optional[WREQueueSyncReceipt] = None
    snapshot: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "accepted": self.accepted,
            "receipt": self.receipt.to_dict(),
            "freshness_receipt": self.freshness_receipt.to_dict() if self.freshness_receipt else None,
            "queue_sync_receipt": self.queue_sync_receipt.to_dict() if self.queue_sync_receipt else None,
            "snapshot": self.snapshot,
        }


class AuthoritativeWorkStateStore(Protocol):
    """Atomic store interface for authoritative work-state snapshots."""

    def load(self) -> Dict[str, Any]:
        """Return the current snapshot, or an empty dict."""

    def commit(self, snapshot: Mapping[str, Any], *, expected_revision: Optional[str]) -> str:
        """Atomically commit snapshot and return the committed revision."""


class InMemoryAuthoritativeWorkStateStore:
    """Test/runtime helper implementing optimistic atomic commits in memory."""

    def __init__(self, initial: Optional[Mapping[str, Any]] = None, *, fail_commit: bool = False) -> None:
        self._state: Dict[str, Any] = dict(initial or {})
        self.fail_commit = fail_commit

    def load(self) -> Dict[str, Any]:
        return json.loads(json.dumps(self._state, sort_keys=True))

    def commit(self, snapshot: Mapping[str, Any], *, expected_revision: Optional[str]) -> str:
        if self.fail_commit:
            raise RuntimeError("commit_failed")
        current_revision = self._state.get("revision")
        if current_revision != expected_revision:
            raise RuntimeError("revision_conflict")
        committed = json.loads(json.dumps(snapshot, sort_keys=True))
        revision = _canonical_digest(committed)
        committed["revision"] = revision
        self._state = committed
        return revision


class AtomicJsonAuthoritativeWorkStateStore:
    """Single-file JSON store using atomic replace."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def load(self) -> Dict[str, Any]:
        with runtime_operation_lock(str(self.path) + ".operation"):
            return self._load_unlocked()

    def _load_unlocked(self) -> Dict[str, Any]:
        if not self.path.exists():
            return {}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def commit(self, snapshot: Mapping[str, Any], *, expected_revision: Optional[str]) -> str:
        with runtime_operation_lock(str(self.path) + ".operation"):
            return self._commit_unlocked(snapshot, expected_revision=expected_revision)

    def _commit_unlocked(self, snapshot: Mapping[str, Any], *, expected_revision: Optional[str]) -> str:
        current = self._load_unlocked()
        if current.get("revision") != expected_revision:
            raise RuntimeError("revision_conflict")
        committed = json.loads(json.dumps(snapshot, sort_keys=True))
        revision = _canonical_digest(committed)
        committed["revision"] = revision
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(prefix=f".{self.path.name}.", suffix=".tmp", dir=str(self.path.parent))
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                json.dump(committed, handle, sort_keys=True, indent=2)
                handle.write("\n")
            os.replace(tmp_name, self.path)
        finally:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)
        return revision


def _canonical_digest(payload: Mapping[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _parse_iso(value: str) -> Optional[datetime]:
    if not isinstance(value, str) or not value.strip():
        return None
    cleaned = value.strip()
    if cleaned.endswith("Z"):
        cleaned = cleaned[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(cleaned)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _normalize_status(value: Any) -> str:
    status = str(value or "PROPOSED").strip().upper()
    return _STATUS_ALIASES.get(status, status)


def _coerce_slice_id(value: Any) -> Optional[str]:
    text = str(value or "").strip().upper()
    if not text:
        return None
    if not all(ch.isalnum() or ch == "_" for ch in text):
        return None
    if len(text) < 3:
        return None
    return text


def _record_commit(record: Mapping[str, Any]) -> Optional[str]:
    for key in ("merge_commit", "head_commit", "base_commit", "commit", "sha"):
        value = record.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def build_runtime_source_snapshot(
    *,
    source_id: str,
    source_type: str,
    records: Sequence[Mapping[str, Any]],
    observed_at: str,
) -> WorkStateSourceBundle:
    """Build a reconciler-compatible source snapshot from runtime records."""

    parsed_records = []
    warnings = []
    for idx, item in enumerate(records):
        if not isinstance(item, Mapping):
            warnings.append(f"record_{idx}_not_object")
            continue
        slice_id = _coerce_slice_id(item.get("slice_id"))
        if not slice_id:
            warnings.append(f"record_{idx}_missing_or_invalid_slice_id")
            continue
        score = item.get("wsp15_score")
        total = score.get("total") if isinstance(score, Mapping) else item.get("wsp15_total")
        parsed_records.append(
            LaneSliceRecord(
                slice_id=slice_id,
                status=_normalize_status(item.get("status") or item.get("state")),
                source_id=source_id,
                source_type=source_type,
                priority=item.get("priority"),
                wsp15_total=total if isinstance(total, int) else None,
                owner_worker=item.get("owner_worker") or item.get("worker_id"),
                lane=item.get("lane"),
                branch=item.get("branch"),
                pr_number=item.get("pr_number") if isinstance(item.get("pr_number"), int) else None,
                commit=_record_commit(item),
                evidence=";".join(str(ref) for ref in (item.get("evidence_refs") or []) if ref),
            )
        )
    if not parsed_records:
        warnings.append("no_slice_records_parsed")
    snapshot = LaneSourceSnapshot(
        source_id=source_id,
        source_type=source_type,
        last_updated=observed_at,
        records=tuple(parsed_records),
        parse_warnings=tuple(warnings),
    )
    return WorkStateSourceBundle(snapshot=snapshot, observed_at=observed_at)


def build_freshness_receipt(
    bundles: Sequence[WorkStateSourceBundle],
    *,
    now_iso: str,
    max_source_age_seconds: int = 3600,
) -> WorkStateFreshnessReceipt:
    """Build and evaluate the source freshness receipt."""

    now = _parse_iso(now_iso)
    if now is None:
        raise ValueError("now_iso must be an ISO timestamp")
    source_digests: Dict[str, str] = {}
    stale = []
    missing = []
    source_ids = []
    for bundle in bundles:
        source_id = bundle.snapshot.source_id
        source_ids.append(source_id)
        source_digests[source_id] = _canonical_digest(bundle.to_dict())
        if bundle.required and not bundle.snapshot.records:
            missing.append(source_id)
        observed = _parse_iso(bundle.observed_at)
        if observed is None:
            stale.append(f"{source_id}:observed_at_missing_or_invalid")
        elif observed > now + timedelta(seconds=60):
            stale.append(f"{source_id}:observed_at_in_future")
        elif (now - observed).total_seconds() > max_source_age_seconds:
            stale.append(f"{source_id}:stale:{bundle.observed_at}")
    payload = {
        "generated_at": now_iso,
        "max_source_age_seconds": max_source_age_seconds,
        "source_ids": source_ids,
        "source_digests": source_digests,
        "stale_source_ids": stale,
        "missing_source_ids": missing,
    }
    fresh = not stale and not missing
    return WorkStateFreshnessReceipt(
        receipt_id=_canonical_digest(payload),
        generated_at=now_iso,
        max_source_age_seconds=max_source_age_seconds,
        source_ids=tuple(source_ids),
        source_digests=source_digests,
        stale_source_ids=tuple(stale),
        missing_source_ids=tuple(missing),
        fresh=fresh,
    )


def _source_precedence(record: LaneSliceRecord) -> int:
    return _SOURCE_PRECEDENCE.get(record.source_type, 99)


def _authoritative_records(report: LaneReconciliationReport) -> Tuple[LaneSliceRecord, ...]:
    by_slice: Dict[str, LaneSliceRecord] = {}
    records = (*report.closed_slices, *report.open_slices)
    for record in sorted(records, key=lambda item: (_source_precedence(item), item.slice_id)):
        by_slice.setdefault(record.slice_id, record)
    return tuple(by_slice[key] for key in sorted(by_slice))


def _active_claims(state: Mapping[str, Any]) -> Tuple[Mapping[str, Any], ...]:
    claims = state.get("worker_claims") or []
    if not isinstance(claims, list):
        return ()
    return tuple(claim for claim in claims if isinstance(claim, Mapping) and claim.get("status") == "ACTIVE")


def _claim_exists(state: Mapping[str, Any], slice_id: str) -> bool:
    for claim in _active_claims(state):
        if claim.get("slice_id") == slice_id:
            return True
    return False


def _build_claim(
    *,
    selected_slice: str,
    worker_id: str,
    lane_id: Optional[str],
    now_iso: str,
    claim_ttl_seconds: int,
    report: LaneReconciliationReport,
    freshness: WorkStateFreshnessReceipt,
) -> DurableWorkerClaim:
    now = _parse_iso(now_iso)
    if now is None:
        raise ValueError("now_iso must be an ISO timestamp")
    expires_at = (now + timedelta(seconds=claim_ttl_seconds)).isoformat()
    payload = {
        "slice_id": selected_slice,
        "worker_id": worker_id,
        "lane_id": lane_id,
        "claimed_at": now_iso,
        "expires_at": expires_at,
        "reconciliation_report_id": report.report_id,
        "freshness_receipt_id": freshness.receipt_id,
    }
    return DurableWorkerClaim(
        claim_id=_canonical_digest(payload),
        slice_id=selected_slice,
        worker_id=worker_id,
        lane_id=lane_id,
        claimed_at=now_iso,
        expires_at=expires_at,
        reconciliation_report_id=report.report_id,
        freshness_receipt_id=freshness.receipt_id,
    )


def _selected_record(report: LaneReconciliationReport, selected_slice: str) -> Optional[LaneSliceRecord]:
    for record in _authoritative_records(report):
        if record.slice_id == selected_slice:
            return record
    return None


def _allocation_receipt_for_selected_slice(
    *,
    selected_slice: str,
    record: Optional[LaneSliceRecord],
) -> Mapping[str, Any]:
    evidence_targets: tuple[str, ...] = ()
    if record and record.evidence:
        evidence_targets = tuple(ref.strip() for ref in record.evidence.split(";") if ref.strip())
    prompt_parts = [selected_slice]
    if record and record.priority:
        prompt_parts.append(f"priority={record.priority}")
    if record and record.wsp15_total is not None:
        prompt_parts.append(f"source_wsp15_total={record.wsp15_total}")
    if record and record.status:
        prompt_parts.append(f"status={record.status}")
    return allocate_reddog_wsp15_receipt(
        requested_operation=f"authoritative_work_state_queue:{selected_slice}",
        prompt_text=" ".join(prompt_parts),
        changed_paths=evidence_targets,
        allowed_read_targets=evidence_targets,
    ).to_dict()


def _build_queue_item(
    claim: DurableWorkerClaim,
    *,
    now_iso: str,
    wsp15_allocation_receipt: Mapping[str, Any],
) -> WREQueueItem:
    allocation_receipt_id = str(wsp15_allocation_receipt.get("receipt_id") or "")
    payload = {
        "slice_id": claim.slice_id,
        "claim_id": claim.claim_id,
        "worker_id": claim.worker_id,
        "enqueued_at": now_iso,
        "wsp15_allocation_receipt_id": allocation_receipt_id,
    }
    return WREQueueItem(
        queue_item_id=_canonical_digest(payload),
        slice_id=claim.slice_id,
        claim_id=claim.claim_id,
        worker_id=claim.worker_id,
        status="QUEUED",
        enqueued_at=now_iso,
        evidence_refs=(
            f"claim:{claim.claim_id}",
            f"freshness:{claim.freshness_receipt_id}",
            f"wsp15_allocation:{allocation_receipt_id}",
        ),
        wsp15_allocation_receipt=dict(wsp15_allocation_receipt),
    )


def _reject(
    *,
    now_iso: str,
    reasons: Iterable[str],
    report: Optional[LaneReconciliationReport] = None,
    freshness: Optional[WorkStateFreshnessReceipt] = None,
    queue_sync: Optional[WREQueueSyncReceipt] = None,
) -> AuthoritativeWorkStateRefreshResult:
    reason_tuple = tuple(dict.fromkeys(reasons))
    payload = {
        "status": AUTHORITATIVE_REFRESH_REJECTED,
        "generated_at": now_iso,
        "reconciliation_report_id": report.report_id if report else None,
        "freshness_receipt_id": freshness.receipt_id if freshness else None,
        "rejection_reasons": reason_tuple,
    }
    receipt = AuthoritativeWorkStateRefreshReceipt(
        refresh_id=_canonical_digest(payload),
        status=AUTHORITATIVE_REFRESH_REJECTED,
        generated_at=now_iso,
        reconciliation_report_id=report.report_id if report else None,
        freshness_receipt_id=freshness.receipt_id if freshness else None,
        selected_slice=None,
        durable_claim_id=None,
        queue_sync_id=queue_sync.sync_id if queue_sync else None,
        rejection_reasons=reason_tuple,
        committed_revision=None,
    )
    return AuthoritativeWorkStateRefreshResult(
        accepted=False,
        receipt=receipt,
        freshness_receipt=freshness,
        queue_sync_receipt=queue_sync,
    )


def refresh_authoritative_work_state_runtime(
    *,
    active_slice_ledger_markdown: str,
    work_ledger_json: str,
    github_pr_records: Sequence[Mapping[str, Any]],
    w10_report_records: Sequence[Mapping[str, Any]],
    store: AuthoritativeWorkStateStore,
    worker_id: str,
    now_iso: str,
    requested_slice: Optional[str] = None,
    source_observed_at: Optional[Mapping[str, str]] = None,
    claim_ttl_seconds: int = 3600,
    max_source_age_seconds: int = 3600,
) -> AuthoritativeWorkStateRefreshResult:
    """Refresh authoritative work state and synchronize one WRE queue item.

    This is a runtime commit, not a planner.  It fails closed before committing
    on malformed freshness, lane-state conflicts, duplicate active claims, or
    store revision conflicts.
    """

    if not isinstance(worker_id, str) or not worker_id.strip():
        raise ValueError("worker_id is required")
    if claim_ttl_seconds <= 0:
        raise ValueError("claim_ttl_seconds must be positive")
    if max_source_age_seconds <= 0:
        raise ValueError("max_source_age_seconds must be positive")
    now = _parse_iso(now_iso)
    if now is None:
        raise ValueError("now_iso must be an ISO timestamp")

    observed = dict(source_observed_at or {})
    default_observed = now_iso
    active = WorkStateSourceBundle(
        snapshot=parse_active_slice_ledger(active_slice_ledger_markdown),
        observed_at=observed.get("ACTIVE_SLICE_LEDGER", default_observed),
    )
    ledger = WorkStateSourceBundle(
        snapshot=parse_work_ledger_json(work_ledger_json),
        observed_at=observed.get("work_ledger.example.json", default_observed),
    )
    github = build_runtime_source_snapshot(
        source_id="GITHUB_PULL_REQUESTS",
        source_type="github_pr",
        records=github_pr_records,
        observed_at=observed.get("GITHUB_PULL_REQUESTS", default_observed),
    )
    w10 = build_runtime_source_snapshot(
        source_id="W10_GATE_REPORTS",
        source_type="w10_report",
        records=w10_report_records,
        observed_at=observed.get("W10_GATE_REPORTS", default_observed),
    )
    bundles = (active, ledger, github, w10)
    freshness = build_freshness_receipt(
        bundles,
        now_iso=now_iso,
        max_source_age_seconds=max_source_age_seconds,
    )
    if not freshness.fresh:
        return _reject(
            now_iso=now_iso,
            reasons=(
                *(f"stale_source:{item}" for item in freshness.stale_source_ids),
                *(f"missing_source:{item}" for item in freshness.missing_source_ids),
            ),
            freshness=freshness,
        )

    report = reconcile_lane_sources(
        [bundle.snapshot for bundle in bundles],
        requested_slice=requested_slice,
        now_iso=now_iso,
    )
    if report.conflicts:
        return _reject(
            now_iso=now_iso,
            reasons=("lane_state_conflict", *(f"conflict:{conflict.slice_id}" for conflict in report.conflicts)),
            report=report,
            freshness=freshness,
        )

    current = store.load()
    selected = report.prework_packet.chosen_slice
    if not selected:
        queue_sync = WREQueueSyncReceipt(
            sync_id=_canonical_digest({"status": WRE_QUEUE_NOT_REQUIRED, "report_id": report.report_id}),
            status=WRE_QUEUE_NOT_REQUIRED,
            queue_item_ids=(),
            selected_slice=None,
            rejection_reasons=("no_selected_slice",),
        )
        durable_claim = None
        queue_items: Tuple[WREQueueItem, ...] = ()
    else:
        if _claim_exists(current, selected):
            return _reject(
                now_iso=now_iso,
                reasons=("durable_worker_claim_already_exists", f"slice:{selected}"),
                report=report,
                freshness=freshness,
            )
        lane_id = None
        for record in report.open_slices:
            if record.slice_id == selected:
                lane_id = record.lane
                break
        durable_claim = _build_claim(
            selected_slice=selected,
            worker_id=worker_id.strip(),
            lane_id=lane_id,
            now_iso=now_iso,
            claim_ttl_seconds=claim_ttl_seconds,
            report=report,
            freshness=freshness,
        )
        allocation_receipt = _allocation_receipt_for_selected_slice(
            selected_slice=selected,
            record=_selected_record(report, selected),
        )
        queue_item = _build_queue_item(
            durable_claim,
            now_iso=now_iso,
            wsp15_allocation_receipt=allocation_receipt,
        )
        queue_items = (queue_item,)
        queue_sync = WREQueueSyncReceipt(
            sync_id=_canonical_digest(
                {
                    "status": WRE_QUEUE_SYNCED,
                    "queue_item_ids": [queue_item.queue_item_id],
                    "selected_slice": selected,
                    "claim_id": durable_claim.claim_id,
                }
            ),
            status=WRE_QUEUE_SYNCED,
            queue_item_ids=(queue_item.queue_item_id,),
            selected_slice=selected,
            rejection_reasons=(),
        )

    records = _authoritative_records(report)
    previous_claims = [dict(claim) for claim in (current.get("worker_claims") or []) if isinstance(claim, Mapping)]
    previous_queue = [dict(item) for item in (current.get("wre_queue_items") or []) if isinstance(item, Mapping)]
    snapshot = {
        "schema_version": WORK_STATE_SCHEMA_VERSION,
        "updated_at": now_iso,
        "refresh_receipt_id": freshness.receipt_id,
        "reconciliation_report_id": report.report_id,
        "sources_checked": report.sources_checked,
        "stale_ledger_sources_reported": report.stale_sources,
        "next_wsp15_queue": report.next_wsp15_queue,
        "recommended_action": report.recommended_action,
        "selected_slice": selected,
        "slices": [record.to_dict() for record in records],
        "freshness_receipts": [freshness.to_dict()],
        "worker_claims": previous_claims + ([durable_claim.to_dict()] if durable_claim else []),
        "wre_queue_items": previous_queue + [item.to_dict() for item in queue_items],
        "queue_sync_receipts": [queue_sync.to_dict()],
        "no_holoindex_mutation_performed": True,
        "no_worker_spawn_performed": True,
        "no_execution_performed": True,
    }

    try:
        revision = store.commit(snapshot, expected_revision=current.get("revision"))
    except Exception as exc:  # noqa: BLE001 - commit backend errors are fail-closed.
        return _reject(
            now_iso=now_iso,
            reasons=("atomic_commit_failed", exc.__class__.__name__),
            report=report,
            freshness=freshness,
            queue_sync=queue_sync,
        )

    payload = {
        "status": AUTHORITATIVE_REFRESH_APPLIED,
        "generated_at": now_iso,
        "reconciliation_report_id": report.report_id,
        "freshness_receipt_id": freshness.receipt_id,
        "selected_slice": selected,
        "durable_claim_id": durable_claim.claim_id if durable_claim else None,
        "queue_sync_id": queue_sync.sync_id,
        "committed_revision": revision,
    }
    receipt = AuthoritativeWorkStateRefreshReceipt(
        refresh_id=_canonical_digest(payload),
        status=AUTHORITATIVE_REFRESH_APPLIED,
        generated_at=now_iso,
        reconciliation_report_id=report.report_id,
        freshness_receipt_id=freshness.receipt_id,
        selected_slice=selected,
        durable_claim_id=durable_claim.claim_id if durable_claim else None,
        queue_sync_id=queue_sync.sync_id,
        rejection_reasons=(),
        committed_revision=revision,
    )
    committed_snapshot = store.load()
    return AuthoritativeWorkStateRefreshResult(
        accepted=True,
        receipt=receipt,
        freshness_receipt=freshness,
        queue_sync_receipt=queue_sync,
        snapshot=committed_snapshot,
    )


__all__ = [
    "AUTHORITATIVE_REFRESH_APPLIED",
    "AUTHORITATIVE_REFRESH_REJECTED",
    "WRE_QUEUE_NOT_REQUIRED",
    "WRE_QUEUE_SYNCED",
    "AtomicJsonAuthoritativeWorkStateStore",
    "AuthoritativeWorkStateRefreshReceipt",
    "AuthoritativeWorkStateRefreshResult",
    "DurableWorkerClaim",
    "InMemoryAuthoritativeWorkStateStore",
    "WREQueueItem",
    "WREQueueSyncReceipt",
    "WorkStateFreshnessReceipt",
    "WorkStateSourceBundle",
    "build_freshness_receipt",
    "build_runtime_source_snapshot",
    "refresh_authoritative_work_state_runtime",
]
