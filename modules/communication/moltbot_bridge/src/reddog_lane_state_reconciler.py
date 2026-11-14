"""RedDog lane-state reconciler dry-run.

This module reconciles existing work-state sources before RedDog assigns or
spawns workers. It is intentionally read-only: callers provide source text and
receive a deterministic report plus the ACTIVE_SLICE_LEDGER prework packet.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


STATUS_CLOSED = {"MERGED", "CLOSED", "SUPERSEDED", "ABANDONED"}
STATUS_OPEN = {
    "PROPOSED",
    "ASSIGNED",
    "IN_PROGRESS",
    "STAGED_FOR_W10",
    "PR_OPEN",
    "BLOCKED",
    "PARKED",
}
PRIORITY_RANK = {"P0": 0, "P1": 1, "P2": 2, "P3": 3, "P4": 4}
SLICE_ID_RE = re.compile(r"`?([A-Za-z][A-Za-z0-9_]{2,})`?")


@dataclass(frozen=True)
class LaneSliceRecord:
    """Single slice state extracted from one source."""

    slice_id: str
    status: str
    source_id: str
    source_type: str
    priority: Optional[str] = None
    wsp15_total: Optional[int] = None
    owner_worker: Optional[str] = None
    lane: Optional[str] = None
    branch: Optional[str] = None
    pr_number: Optional[int] = None
    commit: Optional[str] = None
    source_order: Optional[int] = None
    evidence: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class LaneSourceSnapshot:
    """Parsed work-state source."""

    source_id: str
    source_type: str
    last_updated: Optional[str]
    records: Tuple[LaneSliceRecord, ...]
    parse_warnings: Tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["records"] = [record.to_dict() for record in self.records]
        return payload


@dataclass(frozen=True)
class LaneStateConflict:
    """Cross-source disagreement that must block worker assignment."""

    slice_id: str
    statuses: Tuple[str, ...]
    source_ids: Tuple[str, ...]
    reason: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RedDogPreworkPacket:
    """ACTIVE_SLICE_LEDGER-style packet RedDog should emit before mutation."""

    closed_groundwork: Tuple[str, ...]
    open_target: Tuple[str, ...]
    chosen_slice: Optional[str]
    not_this_slice: Tuple[str, ...]
    reason: str
    no_assignment_performed: bool = True
    no_execution_performed: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class LaneReconciliationReport:
    """Deterministic dry-run reconciliation result."""

    report_id: str
    generated_at: str
    sources_checked: Tuple[str, ...]
    records_total: int
    stale_sources: Tuple[str, ...]
    conflicts: Tuple[LaneStateConflict, ...]
    open_slices: Tuple[LaneSliceRecord, ...]
    closed_slices: Tuple[LaneSliceRecord, ...]
    next_wsp15_queue: Tuple[str, ...]
    recommended_action: str
    prework_packet: RedDogPreworkPacket
    no_ledger_mutation_performed: bool = True
    no_agentdb_mutation_performed: bool = True
    no_holoindex_mutation_performed: bool = True
    no_worker_assignment_performed: bool = True
    no_execution_performed: bool = True

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["conflicts"] = [conflict.to_dict() for conflict in self.conflicts]
        payload["open_slices"] = [record.to_dict() for record in self.open_slices]
        payload["closed_slices"] = [record.to_dict() for record in self.closed_slices]
        payload["prework_packet"] = self.prework_packet.to_dict()
        return payload


def _canonical_digest(payload: Dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _normalize_cell(cell: str) -> str:
    text = cell.strip()
    if text in {"-", "_(none)_"}:
        return ""
    if text and not any(ch.isalnum() or ch in "#`_/" for ch in text):
        return ""
    return text.strip("`").strip()


def _split_markdown_row(line: str) -> List[str]:
    stripped = line.strip()
    if not stripped.startswith("|") or not stripped.endswith("|"):
        return []
    cells = [cell.strip() for cell in stripped.strip("|").split("|")]
    if not cells or all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells):
        return []
    return cells


def _extract_slice_id(text: str) -> Optional[str]:
    match = SLICE_ID_RE.search(text or "")
    if not match:
        return None
    slice_id = match.group(1).upper()
    if slice_id in {"NONE", "NO", "NOT", "N/A", "NA"}:
        return None
    return slice_id


def _normalize_status(status: str) -> str:
    upper = (status or "").strip().upper()
    aliases = {
        "DONE": "MERGED",
        "LANDED": "MERGED",
        "OPEN": "PROPOSED",
        "DRAFT": "PR_OPEN",
        "READY": "PR_OPEN",
        "DEFERRED": "PARKED",
    }
    return aliases.get(upper, upper)


def _status_is_closed(status: str) -> bool:
    return _normalize_status(status) in STATUS_CLOSED


def _status_is_open(status: str) -> bool:
    return _normalize_status(status) in STATUS_OPEN


def _priority_key(record: LaneSliceRecord) -> Tuple[int, int, str]:
    if record.source_order is not None:
        return (0, record.source_order, record.slice_id)
    priority_rank = PRIORITY_RANK.get(record.priority or "P4", 9)
    score_rank = -(record.wsp15_total or 0)
    return (1 + priority_rank, score_rank, record.slice_id)


def _parse_iso(value: Optional[str]) -> Optional[datetime]:
    if not value:
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


def parse_active_slice_ledger(markdown: str, *, source_id: str = "ACTIVE_SLICE_LEDGER") -> LaneSourceSnapshot:
    """Parse the human ACTIVE_SLICE_LEDGER projection into slice records."""

    text = markdown if isinstance(markdown, str) else ""
    warnings: List[str] = []
    records: List[LaneSliceRecord] = []
    order_hints: Dict[str, int] = {}
    last_updated = None
    section = ""

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if line.startswith("**Updated**:"):
            last_updated = line.split(":", 1)[1].strip().split(" ", 1)[0]
        if line.startswith("## "):
            section = line[3:].strip().lower()
            continue

        if section == "next priority order":
            order_match = re.match(r"\s*(\d+)\.\s+(?:\*\*)?([A-Za-z0-9_-]+)", line)
            if order_match:
                token = order_match.group(2).replace("-", "_").upper()
                order_hints[token] = int(order_match.group(1))
            continue

        row = _split_markdown_row(line)
        if not row or row[0].lower() in {"slice", "pr", "track"}:
            continue

        if section == "closed slices" and len(row) >= 3:
            slice_id = _extract_slice_id(row[0])
            if not slice_id:
                continue
            commit = _normalize_cell(row[1])
            status = "MERGED" if re.fullmatch(r"[a-f0-9]{7,40}", commit) else "CLOSED"
            records.append(
                LaneSliceRecord(
                    slice_id=slice_id,
                    status=status,
                    source_id=source_id,
                    source_type="active_slice_ledger",
                    commit=commit or None,
                    evidence=_normalize_cell(row[2]),
                )
            )
        elif section == "open slices" and len(row) >= 4:
            slice_id = _extract_slice_id(row[0])
            if not slice_id:
                continue
            priority = _normalize_cell(row[1])
            blocked_by = _normalize_cell(row[2])
            status = "BLOCKED" if blocked_by else "PROPOSED"
            records.append(
                LaneSliceRecord(
                    slice_id=slice_id,
                    status=status,
                    source_id=source_id,
                    source_type="active_slice_ledger",
                    priority=priority if priority else None,
                    evidence=_normalize_cell(row[3]),
                )
            )
        elif section == "blocked slices" and len(row) >= 2:
            slice_id = _extract_slice_id(row[0])
            if slice_id:
                records.append(
                    LaneSliceRecord(
                        slice_id=slice_id,
                        status="BLOCKED",
                        source_id=source_id,
                        source_type="active_slice_ledger",
                        evidence=_normalize_cell(row[1]),
                    )
                )
        elif section == "deferred slices" and len(row) >= 2:
            slice_id = _extract_slice_id(row[0])
            if slice_id:
                records.append(
                    LaneSliceRecord(
                        slice_id=slice_id,
                        status="PARKED",
                        source_id=source_id,
                        source_type="active_slice_ledger",
                        evidence=_normalize_cell(row[1]),
                    )
                )

    if order_hints:
        ordered_records: List[LaneSliceRecord] = []
        for record in records:
            source_order = None
            for token, order in order_hints.items():
                if record.slice_id == token or record.slice_id.startswith(f"{token}_"):
                    source_order = order
                    break
            if source_order is None:
                ordered_records.append(record)
            else:
                ordered_records.append(
                    LaneSliceRecord(
                        slice_id=record.slice_id,
                        status=record.status,
                        source_id=record.source_id,
                        source_type=record.source_type,
                        priority=record.priority,
                        wsp15_total=record.wsp15_total,
                        owner_worker=record.owner_worker,
                        lane=record.lane,
                        branch=record.branch,
                        pr_number=record.pr_number,
                        commit=record.commit,
                        source_order=source_order,
                        evidence=record.evidence,
                    )
                )
        records = ordered_records

    if not records:
        warnings.append("no_slice_records_parsed")
    return LaneSourceSnapshot(
        source_id=source_id,
        source_type="active_slice_ledger",
        last_updated=last_updated,
        records=tuple(records),
        parse_warnings=tuple(warnings),
    )


def parse_work_ledger_json(json_text: str, *, source_id: str = "work_ledger.example.json") -> LaneSourceSnapshot:
    """Parse the typed work ledger schema/example without validating externally."""

    warnings: List[str] = []
    records: List[LaneSliceRecord] = []
    try:
        payload = json.loads(json_text if isinstance(json_text, str) else "")
    except json.JSONDecodeError:
        return LaneSourceSnapshot(
            source_id=source_id,
            source_type="work_ledger_json",
            last_updated=None,
            records=(),
            parse_warnings=("invalid_json",),
        )

    if not isinstance(payload, dict):
        return LaneSourceSnapshot(
            source_id=source_id,
            source_type="work_ledger_json",
            last_updated=None,
            records=(),
            parse_warnings=("json_root_not_object",),
        )

    for idx, item in enumerate(payload.get("slices") or []):
        if not isinstance(item, dict):
            warnings.append(f"slice_{idx}_not_object")
            continue
        slice_id = str(item.get("slice_id") or "").strip()
        if not slice_id:
            warnings.append(f"slice_{idx}_missing_id")
            continue
        score = item.get("wsp15_score")
        total = score.get("total") if isinstance(score, dict) else None
        records.append(
            LaneSliceRecord(
                slice_id=slice_id,
                status=_normalize_status(str(item.get("status") or "PROPOSED")),
                source_id=source_id,
                source_type="work_ledger_json",
                priority=item.get("priority"),
                wsp15_total=total if isinstance(total, int) else None,
                owner_worker=item.get("owner_worker"),
                lane=item.get("lane"),
                branch=item.get("branch"),
                pr_number=item.get("pr_number"),
                commit=item.get("merge_commit") or item.get("head_commit") or item.get("base_commit"),
                evidence=";".join(item.get("evidence_docs") or []),
            )
        )

    if not records:
        warnings.append("no_slice_records_parsed")
    return LaneSourceSnapshot(
        source_id=source_id,
        source_type="work_ledger_json",
        last_updated=payload.get("last_updated"),
        records=tuple(records),
        parse_warnings=tuple(warnings),
    )


def reconcile_lane_sources(
    sources: Sequence[LaneSourceSnapshot],
    *,
    requested_slice: Optional[str] = None,
    now_iso: Optional[str] = None,
    stale_after_days: int = 30,
) -> LaneReconciliationReport:
    """Reconcile source snapshots into a fail-closed RedDog lane-state report."""

    now = _parse_iso(now_iso) or datetime.now(timezone.utc)
    stale_sources: List[str] = []
    records: List[LaneSliceRecord] = []
    for source in sources:
        records.extend(source.records)
        updated = _parse_iso(source.last_updated)
        if updated is None:
            stale_sources.append(f"{source.source_id}:last_updated_missing_or_invalid")
        elif (now - updated).days > stale_after_days:
            stale_sources.append(f"{source.source_id}:stale:{source.last_updated}")

    by_slice: Dict[str, List[LaneSliceRecord]] = {}
    for record in records:
        by_slice.setdefault(record.slice_id, []).append(record)

    conflicts: List[LaneStateConflict] = []
    for slice_id, grouped in sorted(by_slice.items()):
        closed_seen = any(_status_is_closed(record.status) for record in grouped)
        open_seen = any(_status_is_open(record.status) for record in grouped)
        if closed_seen and open_seen:
            conflicts.append(
                LaneStateConflict(
                    slice_id=slice_id,
                    statuses=tuple(sorted({_normalize_status(record.status) for record in grouped})),
                    source_ids=tuple(record.source_id for record in grouped),
                    reason="closed_vs_open_status_conflict",
                )
            )

    closed_records = tuple(
        sorted((record for record in records if _status_is_closed(record.status)), key=lambda item: item.slice_id)
    )
    open_records = tuple(sorted((record for record in records if _status_is_open(record.status)), key=_priority_key))
    next_queue = tuple(dict.fromkeys(record.slice_id for record in open_records))

    if conflicts:
        recommended_action = "RECONCILE_LEDGER_BEFORE_WORK"
    elif stale_sources:
        recommended_action = "VERIFY_STALE_LEDGER_BEFORE_WORK"
    elif next_queue:
        recommended_action = "CLAIM_NEXT_SLICE"
    else:
        recommended_action = "NO_OPEN_WORK"

    prework = build_reddog_prework_packet(
        closed_records,
        open_records,
        conflicts=tuple(conflicts),
        requested_slice=requested_slice,
        recommended_action=recommended_action,
    )

    report_payload = {
        "generated_at": now.isoformat(),
        "sources_checked": [source.source_id for source in sources],
        "records_total": len(records),
        "stale_sources": stale_sources,
        "conflicts": [conflict.to_dict() for conflict in conflicts],
        "next_wsp15_queue": list(next_queue),
        "recommended_action": recommended_action,
        "prework_packet": prework.to_dict(),
    }
    report_id = _canonical_digest(report_payload)

    return LaneReconciliationReport(
        report_id=report_id,
        generated_at=now.isoformat(),
        sources_checked=tuple(source.source_id for source in sources),
        records_total=len(records),
        stale_sources=tuple(stale_sources),
        conflicts=tuple(conflicts),
        open_slices=open_records,
        closed_slices=closed_records,
        next_wsp15_queue=next_queue,
        recommended_action=recommended_action,
        prework_packet=prework,
    )


def build_reddog_prework_packet(
    closed_records: Sequence[LaneSliceRecord],
    open_records: Sequence[LaneSliceRecord],
    *,
    conflicts: Sequence[LaneStateConflict] = (),
    requested_slice: Optional[str] = None,
    recommended_action: str = "CLAIM_NEXT_SLICE",
) -> RedDogPreworkPacket:
    """Build the exact prework packet RedDog should emit before work."""

    requested = requested_slice.strip() if isinstance(requested_slice, str) and requested_slice.strip() else None
    closed_ids = tuple(dict.fromkeys(record.slice_id for record in closed_records))
    open_ids = tuple(dict.fromkeys(record.slice_id for record in open_records))

    if conflicts:
        return RedDogPreworkPacket(
            closed_groundwork=closed_ids[:10],
            open_target=open_ids[:10],
            chosen_slice=None,
            not_this_slice=tuple(conflict.slice_id for conflict in conflicts),
            reason="ledger_conflict_blocks_worker_assignment",
        )

    if requested and requested in closed_ids:
        next_open = open_ids[0] if open_ids else None
        return RedDogPreworkPacket(
            closed_groundwork=(requested,),
            open_target=open_ids[:10],
            chosen_slice=next_open,
            not_this_slice=(requested,),
            reason="requested_slice_already_closed_redirected_to_next_open",
        )

    if requested and requested in open_ids:
        return RedDogPreworkPacket(
            closed_groundwork=closed_ids[:10],
            open_target=(requested,),
            chosen_slice=requested,
            not_this_slice=tuple(slice_id for slice_id in open_ids[:10] if slice_id != requested),
            reason="requested_slice_open_and_selected",
        )

    chosen = open_ids[0] if open_ids and recommended_action in {
        "CLAIM_NEXT_SLICE",
        "VERIFY_STALE_LEDGER_BEFORE_WORK",
    } else None
    return RedDogPreworkPacket(
        closed_groundwork=closed_ids[:10],
        open_target=open_ids[:10],
        chosen_slice=chosen,
        not_this_slice=tuple(open_ids[1:10]) if chosen else open_ids[:10],
        reason=recommended_action.lower(),
    )


def reconcile_active_and_json_ledgers(
    active_slice_ledger_markdown: str,
    work_ledger_json: str,
    *,
    requested_slice: Optional[str] = None,
    now_iso: Optional[str] = None,
    stale_after_days: int = 30,
) -> LaneReconciliationReport:
    """Convenience entrypoint for the current two canonical lane sources."""

    return reconcile_lane_sources(
        [
            parse_active_slice_ledger(active_slice_ledger_markdown),
            parse_work_ledger_json(work_ledger_json),
        ],
        requested_slice=requested_slice,
        now_iso=now_iso,
        stale_after_days=stale_after_days,
    )


__all__ = [
    "LaneReconciliationReport",
    "LaneSliceRecord",
    "LaneSourceSnapshot",
    "LaneStateConflict",
    "RedDogPreworkPacket",
    "build_reddog_prework_packet",
    "parse_active_slice_ledger",
    "parse_work_ledger_json",
    "reconcile_active_and_json_ledgers",
    "reconcile_lane_sources",
]
