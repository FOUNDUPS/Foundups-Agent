"""Main bootstrap for RedDog work-state source-record supply."""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from modules.communication.moltbot_bridge.src.reddog_authoritative_work_state_source_record_supply import (
    GitHubPullRequestSourceProvider,
    GitHubRestPullRequestSourceProvider,
    SOURCE_RECORD_SUPPLY_NOT_READY,
    SourceRecordSupplyResult,
    W10ReportSourceProvider,
    WorkLedgerProjectionW10ReportProvider,
    supply_authoritative_work_state_source_records,
)
from modules.communication.moltbot_bridge.src.reddog_main_authoritative_work_state_refresh_bootstrap import (
    DEFAULT_WORK_LEDGER_JSON,
)


@dataclass(frozen=True)
class RedDogWorkStateSourceRecordSupplyBootstrapResult:
    """Result returned to main.py after source-record supply."""

    accepted: bool
    status: str
    github_pr_records_path: Optional[str]
    w10_report_records_path: Optional[str]
    receipt_id: Optional[str]
    github_record_count: int
    w10_record_count: int
    rejection_reasons: tuple[str, ...]
    no_repo_mutation_performed: bool = True
    no_holoindex_reindex_performed: bool = True
    no_worker_spawn_performed: bool = True
    no_openclaw_enqueue_performed: bool = True
    no_hermes_dispatch_performed: bool = True
    no_execution_performed: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def run_reddog_authoritative_work_state_source_record_supply_bootstrap(
    *,
    repo_root: Path | str,
    github_pr_records_output_path: Path | str | None,
    w10_report_records_output_path: Path | str | None,
    work_ledger_json_path: Path | str | None = None,
    github_repo_full_name: str = "FOUNDUPS/Foundups-Agent",
    github_state: str = "open",
    now_iso: str | None = None,
    github_provider: GitHubPullRequestSourceProvider | None = None,
    w10_provider: W10ReportSourceProvider | None = None,
) -> RedDogWorkStateSourceRecordSupplyBootstrapResult:
    """Materialize GitHub and W10 source-record files for work-state refresh."""

    root = Path(repo_root).resolve()
    now = now_iso or datetime.now(timezone.utc).isoformat()
    reasons: list[str] = []
    github_path = _resolve_required_output(github_pr_records_output_path, "missing_github_pr_records_output_path", reasons)
    w10_path = _resolve_required_output(w10_report_records_output_path, "missing_w10_report_records_output_path", reasons)
    ledger_path = _resolve_read_path(root, work_ledger_json_path or DEFAULT_WORK_LEDGER_JSON)

    if github_provider is None:
        github_provider = GitHubRestPullRequestSourceProvider(
            repo_full_name=github_repo_full_name,
            state=github_state,
            token=os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN") or "",
        )
    if w10_provider is None:
        w10_provider = WorkLedgerProjectionW10ReportProvider(work_ledger_json_path=ledger_path)

    if reasons:
        return _not_ready(reasons=tuple(reasons), github_path=github_path, w10_path=w10_path)

    assert github_path is not None and w10_path is not None
    result = supply_authoritative_work_state_source_records(
        repo_root=root,
        github_pr_records_output_path=github_path,
        w10_report_records_output_path=w10_path,
        github_provider=github_provider,
        w10_provider=w10_provider,
        now_iso=now,
    )
    return _from_supply_result(result)


def _resolve_read_path(repo_root: Path, value: Path | str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = repo_root / path
    return path.resolve()


def _resolve_required_output(
    value: Path | str | None,
    reason: str,
    reasons: list[str],
) -> Path | None:
    raw = str(value or "").strip()
    if not raw:
        reasons.append(reason)
        return None
    return Path(raw).resolve()


def _from_supply_result(result: SourceRecordSupplyResult) -> RedDogWorkStateSourceRecordSupplyBootstrapResult:
    return RedDogWorkStateSourceRecordSupplyBootstrapResult(
        accepted=result.accepted,
        status=result.status,
        github_pr_records_path=result.github_pr_records_path,
        w10_report_records_path=result.w10_report_records_path,
        receipt_id=result.receipt.receipt_id if result.receipt else None,
        github_record_count=result.receipt.github_record_count,
        w10_record_count=result.receipt.w10_record_count,
        rejection_reasons=result.receipt.rejection_reasons,
    )


def _not_ready(
    *,
    reasons: tuple[str, ...],
    github_path: Path | None,
    w10_path: Path | None,
) -> RedDogWorkStateSourceRecordSupplyBootstrapResult:
    return RedDogWorkStateSourceRecordSupplyBootstrapResult(
        accepted=False,
        status=SOURCE_RECORD_SUPPLY_NOT_READY,
        github_pr_records_path=str(github_path) if github_path else None,
        w10_report_records_path=str(w10_path) if w10_path else None,
        receipt_id=None,
        github_record_count=0,
        w10_record_count=0,
        rejection_reasons=reasons,
    )


__all__ = [
    "RedDogWorkStateSourceRecordSupplyBootstrapResult",
    "run_reddog_authoritative_work_state_source_record_supply_bootstrap",
]
