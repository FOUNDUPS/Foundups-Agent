"""RedDog runtime work-ledger source projection supplier.

Slice: REDDOG_WORK_LEDGER_SOURCE_PROJECTION_SUPPLY_PHASE1

This module turns already-supplied GitHub PR and W10 source-record files into
fresh active/work ledger source projections for the authoritative work-state
refresh runtime. It writes outside-repo projection files only. It does not edit
the canonical docs, commit work state, spawn workers, enqueue OpenClaw, dispatch
Hermes, execute shell commands, mutate HoloIndex, or update PatternMemory.
"""

from __future__ import annotations

import hashlib
import json
import re
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence, Tuple


WORK_LEDGER_PROJECTION_APPLIED = "WORK_LEDGER_PROJECTION_APPLIED"
WORK_LEDGER_PROJECTION_NOT_READY = "WORK_LEDGER_PROJECTION_NOT_READY"

_SLICE_ID_RE = re.compile(r"[A-Z][A-Z0-9]+(?:_[A-Z0-9]+){2,}_PHASE[0-9]+")
_OPEN_STATUSES = {"PROPOSED", "ASSIGNED", "IN_PROGRESS", "STAGED_FOR_W10", "PR_OPEN", "BLOCKED", "PARKED"}
_CLOSED_STATUSES = {"MERGED", "CLOSED", "SUPERSEDED", "ABANDONED"}
_PRIORITY_RANK = {"P0": 0, "P1": 1, "P2": 2, "P3": 3, "P4": 4}


@dataclass(frozen=True)
class WorkLedgerProjectionSupplyReceipt:
    """Receipt for runtime ledger projection generation."""

    receipt_id: str
    generated_at: str
    active_slice_ledger_path: str
    work_ledger_json_path: str
    source_record_count: int
    projected_slice_count: int
    open_slice_count: int
    closed_slice_count: int
    rejection_reasons: Tuple[str, ...]
    no_canonical_ledger_mutation_performed: bool = True
    no_repo_mutation_performed: bool = True
    no_holoindex_reindex_performed: bool = True
    no_worker_spawn_performed: bool = True
    no_openclaw_enqueue_performed: bool = True
    no_hermes_dispatch_performed: bool = True
    no_execution_performed: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class WorkLedgerProjectionSupplyResult:
    """Result for runtime ledger projection supply."""

    accepted: bool
    status: str
    receipt: WorkLedgerProjectionSupplyReceipt
    active_slice_ledger_path: str | None = None
    work_ledger_json_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "accepted": self.accepted,
            "status": self.status,
            "receipt": self.receipt.to_dict(),
            "active_slice_ledger_path": self.active_slice_ledger_path,
            "work_ledger_json_path": self.work_ledger_json_path,
        }


def supply_work_ledger_source_projection(
    *,
    repo_root: Path | str,
    github_pr_records_path: Path | str,
    w10_report_records_path: Path | str,
    active_slice_ledger_output_path: Path | str,
    work_ledger_json_output_path: Path | str,
    now_iso: str | None = None,
) -> WorkLedgerProjectionSupplyResult:
    """Write fresh active/work ledger projections from source-record files."""

    root = Path(repo_root).resolve()
    now = now_iso or datetime.now(timezone.utc).isoformat()
    github_path = Path(github_pr_records_path).resolve()
    w10_path = Path(w10_report_records_path).resolve()
    active_output = Path(active_slice_ledger_output_path).resolve()
    work_output = Path(work_ledger_json_output_path).resolve()
    reasons: list[str] = []

    if _is_inside(active_output, root):
        reasons.append("active_slice_ledger_output_inside_repo")
    if _is_inside(work_output, root):
        reasons.append("work_ledger_json_output_inside_repo")
    if active_output == work_output:
        reasons.append("ledger_projection_outputs_must_be_distinct")

    github_records = _read_records(github_path, "github_pr_records", reasons)
    w10_records = _read_records(w10_path, "w10_report_records", reasons)
    source_records = (*github_records, *w10_records)
    projected = _project_records(source_records)
    if not github_records:
        reasons.append("missing_github_pr_records")
    if not w10_records:
        reasons.append("missing_w10_report_records")
    if not projected:
        reasons.append("no_projectable_slice_records")

    open_records = tuple(record for record in projected if record["status"] in _OPEN_STATUSES)
    closed_records = tuple(record for record in projected if record["status"] in _CLOSED_STATUSES)
    if reasons:
        return _result(
            accepted=False,
            status=WORK_LEDGER_PROJECTION_NOT_READY,
            now_iso=now,
            active_output=active_output,
            work_output=work_output,
            source_count=len(source_records),
            projected_count=len(projected),
            open_count=len(open_records),
            closed_count=len(closed_records),
            reasons=tuple(dict.fromkeys(reasons)),
        )

    _atomic_write_text(active_output, _render_active_slice_ledger(projected, now_iso=now))
    _atomic_write_json(work_output, _render_work_ledger_json(projected, now_iso=now))
    return _result(
        accepted=True,
        status=WORK_LEDGER_PROJECTION_APPLIED,
        now_iso=now,
        active_output=active_output,
        work_output=work_output,
        source_count=len(source_records),
        projected_count=len(projected),
        open_count=len(open_records),
        closed_count=len(closed_records),
        reasons=(),
    )


def _read_records(path: Path, source_name: str, reasons: list[str]) -> tuple[Mapping[str, Any], ...]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError:
        reasons.append(f"missing_{source_name}")
        return ()
    except json.JSONDecodeError:
        reasons.append(f"malformed_{source_name}")
        return ()
    if not isinstance(payload, list):
        reasons.append(f"{source_name}_not_array")
        return ()
    return tuple(item for item in payload if isinstance(item, Mapping))


def _project_records(records: Sequence[Mapping[str, Any]]) -> tuple[dict[str, Any], ...]:
    by_slice: dict[str, dict[str, Any]] = {}
    for item in records:
        slice_id = _slice_id(item.get("slice_id"))
        if not slice_id:
            continue
        candidate = _project_record(item, slice_id=slice_id)
        current = by_slice.get(slice_id)
        if current is None or _record_rank(candidate) < _record_rank(current):
            by_slice[slice_id] = candidate
    return tuple(sorted(by_slice.values(), key=_sort_key))


def _project_record(item: Mapping[str, Any], *, slice_id: str) -> dict[str, Any]:
    score = item.get("wsp15_score")
    total = score.get("total") if isinstance(score, Mapping) else item.get("wsp15_total")
    evidence_refs = tuple(str(ref) for ref in (item.get("evidence_refs") or ()) if ref)
    return {
        "slice_id": slice_id,
        "title": _title_from_slice(slice_id),
        "status": _status(item.get("status") or item.get("state")),
        "priority": _priority(item.get("priority")),
        "source": "runtime_projection",
        "lane": str(item.get("lane") or "").strip() or None,
        "owner_worker": str(item.get("owner_worker") or item.get("worker_id") or "").strip() or None,
        "branch": str(item.get("branch") or "").strip() or None,
        "pr_number": item.get("pr_number") if isinstance(item.get("pr_number"), int) else None,
        "head_commit": str(item.get("head_commit") or item.get("commit") or "").strip() or None,
        "merge_commit": str(item.get("merge_commit") or "").strip() or None,
        "wsp15_score": {"total": total} if isinstance(total, int) else {},
        "evidence_refs": evidence_refs,
    }


def _render_active_slice_ledger(records: Sequence[Mapping[str, Any]], *, now_iso: str) -> str:
    open_records = [record for record in records if record["status"] in _OPEN_STATUSES]
    closed_records = [record for record in records if record["status"] in _CLOSED_STATUSES]
    lines = [
        "# Active Slice Ledger",
        "",
        "**Authority**: RedDog runtime projection",
        f"**Updated**: {now_iso}",
        "**Rule**: Runtime projection generated outside the repo from supplied source records.",
        "",
        "## Open Slices",
        "",
        "| Slice | Priority | Blocked By | Notes |",
        "|-------|----------|------------|-------|",
    ]
    for record in open_records:
        blocked = "-" if record["status"] != "BLOCKED" else "runtime projection blocked"
        notes = _notes(record)
        lines.append(f"| `{record['slice_id']}` | {record.get('priority') or 'P4'} | {blocked} | {notes} |")
    if not open_records:
        lines.append("| `NONE` | P4 | - | no open runtime-projected slices |")
    lines.extend(["", "## Closed Slices", "", "| Slice | Commit | Evidence |", "|-------|--------|----------|"])
    for record in closed_records:
        commit = record.get("merge_commit") or record.get("head_commit") or "closed"
        lines.append(f"| `{record['slice_id']}` | `{commit}` | {_notes(record)} |")
    if not closed_records:
        lines.append("| `NONE` | `none` | no closed runtime-projected slices |")
    lines.extend(["", "## Next Priority Order", ""])
    for index, record in enumerate(open_records, start=1):
        lines.append(f"{index}. **{record['slice_id']}** - {_notes(record)}")
    if not open_records:
        lines.append("1. **NONE** - no open runtime-projected slices")
    lines.append("")
    return "\n".join(lines)


def _render_work_ledger_json(records: Sequence[Mapping[str, Any]], *, now_iso: str) -> dict[str, Any]:
    slices = []
    for record in records:
        slices.append(
            {
                "slice_id": record["slice_id"],
                "title": record["title"],
                "status": record["status"],
                "priority": record.get("priority") or "P4",
                "source": "runtime_projection",
                "lane": record.get("lane"),
                "owner_worker": record.get("owner_worker"),
                "branch": record.get("branch"),
                "pr_number": record.get("pr_number"),
                "head_commit": record.get("head_commit"),
                "merge_commit": record.get("merge_commit"),
                "evidence_docs": list(record.get("evidence_refs") or ()),
                "wsp15_score": record.get("wsp15_score") or {},
                "created_at": now_iso,
                "updated_at": now_iso,
                "last_verified_at": now_iso,
                "wsp_97_labels": [
                    "RUNTIME_PROJECTION",
                    "NO_CANONICAL_LEDGER_MUTATION",
                    "NO_HOLOINDEX_MUTATION",
                    "NO_WORKER_SPAWN",
                ],
            }
        )
    return {
        "schema_version": "1.0.0",
        "last_updated": now_iso,
        "ledger_authority": "RedDog runtime projection",
        "slices": slices,
    }


def _result(
    *,
    accepted: bool,
    status: str,
    now_iso: str,
    active_output: Path,
    work_output: Path,
    source_count: int,
    projected_count: int,
    open_count: int,
    closed_count: int,
    reasons: Tuple[str, ...],
) -> WorkLedgerProjectionSupplyResult:
    payload = {
        "generated_at": now_iso,
        "active_slice_ledger_path": str(active_output),
        "work_ledger_json_path": str(work_output),
        "source_record_count": source_count,
        "projected_slice_count": projected_count,
        "open_slice_count": open_count,
        "closed_slice_count": closed_count,
        "rejection_reasons": reasons,
    }
    receipt = WorkLedgerProjectionSupplyReceipt(
        receipt_id=_digest(payload),
        generated_at=now_iso,
        active_slice_ledger_path=str(active_output),
        work_ledger_json_path=str(work_output),
        source_record_count=source_count,
        projected_slice_count=projected_count,
        open_slice_count=open_count,
        closed_slice_count=closed_count,
        rejection_reasons=reasons,
    )
    return WorkLedgerProjectionSupplyResult(
        accepted=accepted,
        status=status,
        receipt=receipt,
        active_slice_ledger_path=str(active_output) if accepted else None,
        work_ledger_json_path=str(work_output) if accepted else None,
    )


def _sort_key(record: Mapping[str, Any]) -> tuple[int, int, str]:
    priority = str(record.get("priority") or "P4").upper()
    score = record.get("wsp15_score") or {}
    total = score.get("total") if isinstance(score, Mapping) else None
    return (_PRIORITY_RANK.get(priority, 9), -(total if isinstance(total, int) else 0), str(record["slice_id"]))


def _record_rank(record: Mapping[str, Any]) -> tuple[int, int]:
    status = str(record.get("status") or "")
    source_score = 0 if status == "PR_OPEN" else 1
    return (source_score, _sort_key(record)[0])


def _notes(record: Mapping[str, Any]) -> str:
    refs = tuple(str(ref) for ref in (record.get("evidence_refs") or ()) if ref)
    if refs:
        return "; ".join(refs[:3])
    if record.get("pr_number"):
        return f"github:pr:{record['pr_number']}"
    return "runtime projection"


def _title_from_slice(slice_id: str) -> str:
    return slice_id.replace("_", " ").title()


def _slice_id(value: object) -> str:
    match = _SLICE_ID_RE.search(str(value or "").upper())
    return match.group(0) if match else ""


def _status(value: object) -> str:
    text = str(value or "PROPOSED").strip().upper()
    aliases = {"OPEN": "PR_OPEN", "DRAFT": "PR_OPEN", "READY": "PR_OPEN", "DONE": "MERGED", "LANDED": "MERGED"}
    return aliases.get(text, text)


def _priority(value: object) -> str | None:
    text = str(value or "").strip().upper()
    return text if text in _PRIORITY_RANK else None


def _is_inside(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=str(path.parent), delete=False) as handle:
        handle.write(text)
        tmp_name = handle.name
    Path(tmp_name).replace(path)


def _atomic_write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=str(path.parent), delete=False) as handle:
        json.dump(payload, handle, sort_keys=True, indent=2)
        handle.write("\n")
        tmp_name = handle.name
    Path(tmp_name).replace(path)


def _digest(payload: Mapping[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


__all__ = [
    "WORK_LEDGER_PROJECTION_APPLIED",
    "WORK_LEDGER_PROJECTION_NOT_READY",
    "WorkLedgerProjectionSupplyReceipt",
    "WorkLedgerProjectionSupplyResult",
    "supply_work_ledger_source_projection",
]
