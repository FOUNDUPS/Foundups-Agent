"""Main bootstrap for runtime work-ledger source projection supply."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from modules.communication.moltbot_bridge.src.reddog_work_ledger_source_projection_supply import (
    WORK_LEDGER_PROJECTION_NOT_READY,
    WorkLedgerProjectionSupplyResult,
    supply_work_ledger_source_projection,
)


@dataclass(frozen=True)
class RedDogWorkLedgerProjectionSupplyBootstrapResult:
    """Result returned to main.py after runtime ledger projection."""

    accepted: bool
    status: str
    active_slice_ledger_path: Optional[str]
    work_ledger_json_path: Optional[str]
    receipt_id: Optional[str]
    source_record_count: int
    projected_slice_count: int
    open_slice_count: int
    closed_slice_count: int
    rejection_reasons: tuple[str, ...]
    no_canonical_ledger_mutation_performed: bool = True
    no_repo_mutation_performed: bool = True
    no_holoindex_reindex_performed: bool = True
    no_worker_spawn_performed: bool = True
    no_openclaw_enqueue_performed: bool = True
    no_hermes_dispatch_performed: bool = True
    no_execution_performed: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def run_reddog_work_ledger_source_projection_supply_bootstrap(
    *,
    repo_root: Path | str,
    github_pr_records_path: Path | str | None,
    w10_report_records_path: Path | str | None,
    active_slice_ledger_output_path: Path | str | None,
    work_ledger_json_output_path: Path | str | None,
    now_iso: str | None = None,
) -> RedDogWorkLedgerProjectionSupplyBootstrapResult:
    """Materialize runtime active/work ledger projections for work-state refresh."""

    root = Path(repo_root).resolve()
    now = now_iso or datetime.now(timezone.utc).isoformat()
    reasons: list[str] = []
    github_path = _resolve_required_path(github_pr_records_path, "missing_github_pr_records_path", reasons)
    w10_path = _resolve_required_path(w10_report_records_path, "missing_w10_report_records_path", reasons)
    active_path = _resolve_required_path(
        active_slice_ledger_output_path,
        "missing_active_slice_ledger_output_path",
        reasons,
    )
    work_path = _resolve_required_path(work_ledger_json_output_path, "missing_work_ledger_json_output_path", reasons)
    if reasons:
        return _not_ready(
            reasons=tuple(reasons),
            active_path=active_path,
            work_path=work_path,
        )

    assert github_path is not None and w10_path is not None and active_path is not None and work_path is not None
    result = supply_work_ledger_source_projection(
        repo_root=root,
        github_pr_records_path=github_path,
        w10_report_records_path=w10_path,
        active_slice_ledger_output_path=active_path,
        work_ledger_json_output_path=work_path,
        now_iso=now,
    )
    return _from_projection_result(result)


def _resolve_required_path(value: Path | str | None, reason: str, reasons: list[str]) -> Path | None:
    raw = str(value or "").strip()
    if not raw:
        reasons.append(reason)
        return None
    return Path(raw).resolve()


def _from_projection_result(result: WorkLedgerProjectionSupplyResult) -> RedDogWorkLedgerProjectionSupplyBootstrapResult:
    return RedDogWorkLedgerProjectionSupplyBootstrapResult(
        accepted=result.accepted,
        status=result.status,
        active_slice_ledger_path=result.active_slice_ledger_path,
        work_ledger_json_path=result.work_ledger_json_path,
        receipt_id=result.receipt.receipt_id,
        source_record_count=result.receipt.source_record_count,
        projected_slice_count=result.receipt.projected_slice_count,
        open_slice_count=result.receipt.open_slice_count,
        closed_slice_count=result.receipt.closed_slice_count,
        rejection_reasons=result.receipt.rejection_reasons,
    )


def _not_ready(
    *,
    reasons: tuple[str, ...],
    active_path: Path | None,
    work_path: Path | None,
) -> RedDogWorkLedgerProjectionSupplyBootstrapResult:
    return RedDogWorkLedgerProjectionSupplyBootstrapResult(
        accepted=False,
        status=WORK_LEDGER_PROJECTION_NOT_READY,
        active_slice_ledger_path=str(active_path) if active_path else None,
        work_ledger_json_path=str(work_path) if work_path else None,
        receipt_id=None,
        source_record_count=0,
        projected_slice_count=0,
        open_slice_count=0,
        closed_slice_count=0,
        rejection_reasons=reasons,
    )


__all__ = [
    "RedDogWorkLedgerProjectionSupplyBootstrapResult",
    "run_reddog_work_ledger_source_projection_supply_bootstrap",
]
