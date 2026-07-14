"""RedDog main authoritative work-state refresh bootstrap.

This adapter wires ``main.py`` to the existing authoritative work-state refresh
runtime in a controlled way. It reads already-present source artifacts and
commits a work-state JSON only outside the repository checkout. It does not
fetch GitHub, create W10 reports, spawn workers, enqueue OpenClaw, dispatch
Hermes, execute work, mutate HoloIndex, or write repository files.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

from modules.communication.moltbot_bridge.src.reddog_authoritative_work_state_refresh_runtime import (
    AUTHORITATIVE_REFRESH_APPLIED,
    AtomicJsonAuthoritativeWorkStateStore,
    AuthoritativeWorkStateRefreshResult,
    refresh_authoritative_work_state_runtime,
)
from modules.communication.moltbot_bridge.src.reddog_lane_state_reconciler import (
    reconcile_active_and_json_ledgers,
)
from modules.communication.moltbot_bridge.src.reddog_readonly_audit_decision_persistence import (
    AgentDbReadOnlyAuditDecisionStore,
    ReadOnlyAuditDecisionStore,
)
from modules.communication.moltbot_bridge.src.reddog_worker_claim_gate_dryrun import (
    evaluate_reddog_worker_claim_dryrun,
)


REDDOG_WORK_STATE_BOOTSTRAP_APPLIED = "REDDOG_WORK_STATE_BOOTSTRAP_APPLIED"
REDDOG_WORK_STATE_BOOTSTRAP_NOT_READY = "REDDOG_WORK_STATE_BOOTSTRAP_NOT_READY"
REDDOG_WORK_STATE_BOOTSTRAP_DISABLED = "REDDOG_WORK_STATE_BOOTSTRAP_DISABLED"

DEFAULT_ACTIVE_SLICE_LEDGER = "docs/0102_session_briefings/ACTIVE_SLICE_LEDGER.md"
DEFAULT_WORK_LEDGER_JSON = "docs/0102_session_briefings/work_ledger.example.json"
DEFAULT_RUNTIME_RELATIVE_PATH = "Foundups-Agent/reddog/authoritative_work_state.json"


@dataclass(frozen=True)
class RedDogMainWorkStateRefreshBootstrapResult:
    """Result emitted by the main-startup work-state refresh adapter."""

    accepted: bool
    status: str
    work_state_path: Optional[str]
    refresh_id: Optional[str]
    committed_revision: Optional[str]
    selected_slice: Optional[str]
    queue_item_count: int
    rejection_reasons: tuple[str, ...]
    latest_decision_attempted: bool = False
    latest_decision_id: Optional[str] = None
    latest_decision_action: Optional[str] = None
    latest_decision_next_slice: Optional[str] = None
    latest_decision_claim_gate_decision: Optional[str] = None
    latest_decision_rejection_reasons: tuple[str, ...] = ()
    no_github_fetch_performed: bool = True
    no_w10_fetch_performed: bool = True
    no_worker_spawn_performed: bool = True
    no_openclaw_enqueue_performed: bool = True
    no_hermes_dispatch_performed: bool = True
    no_holoindex_reindex_performed: bool = True
    no_execution_performed: bool = True
    no_repo_mutation_performed: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def run_reddog_main_authoritative_work_state_refresh_bootstrap(
    *,
    repo_root: Path | str,
    active_slice_ledger_path: Path | str | None = None,
    work_ledger_json_path: Path | str | None = None,
    github_pr_records_path: Path | str | None = None,
    w10_report_records_path: Path | str | None = None,
    work_state_output_path: Path | str | None = None,
    worker_id: str = "reddog-main-bootstrap",
    now_iso: str | None = None,
    requested_slice: str | None = None,
    use_latest_readonly_audit_decision: bool = False,
    decision_store: ReadOnlyAuditDecisionStore | None = None,
    max_source_age_seconds: int = 3600,
    stale_after_days: int = 30,
) -> RedDogMainWorkStateRefreshBootstrapResult:
    """Refresh authoritative work state from existing source artifacts."""

    root = Path(repo_root).resolve()
    now = now_iso or datetime.now(timezone.utc).isoformat()
    active_path = _resolve_read_path(root, active_slice_ledger_path or DEFAULT_ACTIVE_SLICE_LEDGER)
    ledger_path = _resolve_read_path(root, work_ledger_json_path or DEFAULT_WORK_LEDGER_JSON)
    output_path = _resolve_output_path(root, work_state_output_path)
    github_path = _resolve_optional_read_path(root, github_pr_records_path)
    w10_path = _resolve_optional_read_path(root, w10_report_records_path)
    reasons: list[str] = []

    if output_path is None:
        reasons.append("missing_work_state_output_path")
    elif _is_inside(output_path, root):
        reasons.append("work_state_output_inside_repo")

    active_text = _read_required_text(active_path, "missing_active_slice_ledger", reasons)
    ledger_text = _read_required_text(ledger_path, "missing_work_ledger_json", reasons)
    github_records = _read_required_records(github_path, "missing_github_pr_records", reasons)
    w10_records = _read_required_records(w10_path, "missing_w10_report_records", reasons)
    latest_decision: Mapping[str, Any] | None = None
    latest_decision_claim_gate_decision: Optional[str] = None
    effective_requested_slice = requested_slice

    if active_text and ledger_text:
        ledger_report = reconcile_active_and_json_ledgers(
            active_text,
            ledger_text,
            now_iso=now,
            stale_after_days=stale_after_days,
        )
        if ledger_report.stale_sources:
            reasons.extend(f"stale_ledger_source:{source}" for source in ledger_report.stale_sources)
        if ledger_report.conflicts:
            reasons.extend(f"ledger_conflict:{conflict.slice_id}" for conflict in ledger_report.conflicts)
        if use_latest_readonly_audit_decision and requested_slice is None:
            latest_decision, decision_reasons = _load_latest_decision(decision_store)
            reasons.extend(decision_reasons)
            if latest_decision and not decision_reasons and not ledger_report.stale_sources and not ledger_report.conflicts:
                effective_requested_slice = str(latest_decision.get("next_slice_name") or "").strip().upper()
                claim_gate = evaluate_reddog_worker_claim_dryrun(
                    ledger_report,
                    requested_slice=effective_requested_slice,
                    worker_id=worker_id,
                )
                latest_decision_claim_gate_decision = claim_gate.receipt.decision
                if not claim_gate.accepted:
                    reasons.append("persisted_decision_claim_gate_rejected")
                    reasons.extend(f"persisted_decision_claim_gate:{reason}" for reason in claim_gate.receipt.rejection_reasons)

    if reasons:
        return _not_ready(
            reasons=reasons,
            output_path=output_path,
            latest_decision=latest_decision,
            latest_decision_attempted=use_latest_readonly_audit_decision and requested_slice is None,
            latest_decision_claim_gate_decision=latest_decision_claim_gate_decision,
        )

    assert output_path is not None
    assert active_text is not None and ledger_text is not None
    store = AtomicJsonAuthoritativeWorkStateStore(output_path)
    result = refresh_authoritative_work_state_runtime(
        active_slice_ledger_markdown=active_text,
        work_ledger_json=ledger_text,
        github_pr_records=github_records,
        w10_report_records=w10_records,
        store=store,
        worker_id=worker_id,
        now_iso=now,
        requested_slice=effective_requested_slice,
        max_source_age_seconds=max_source_age_seconds,
    )
    if not result.accepted or result.receipt.status != AUTHORITATIVE_REFRESH_APPLIED:
        return _not_ready(
            reasons=result.receipt.rejection_reasons or ("authoritative_refresh_rejected",),
            output_path=output_path,
            runtime_result=result,
            latest_decision=latest_decision,
            latest_decision_attempted=use_latest_readonly_audit_decision and requested_slice is None,
            latest_decision_claim_gate_decision=latest_decision_claim_gate_decision,
        )

    queue_count = 0
    if result.snapshot:
        queue_items = result.snapshot.get("wre_queue_items") or ()
        queue_count = len(queue_items) if isinstance(queue_items, Sequence) else 0
    return RedDogMainWorkStateRefreshBootstrapResult(
        accepted=True,
        status=REDDOG_WORK_STATE_BOOTSTRAP_APPLIED,
        work_state_path=str(output_path),
        refresh_id=result.receipt.refresh_id,
        committed_revision=result.receipt.committed_revision,
        selected_slice=result.receipt.selected_slice,
        queue_item_count=queue_count,
        rejection_reasons=(),
        latest_decision_attempted=use_latest_readonly_audit_decision and requested_slice is None,
        latest_decision_id=_decision_text(latest_decision, "decision_id"),
        latest_decision_action=_decision_text(latest_decision, "action"),
        latest_decision_next_slice=_decision_text(latest_decision, "next_slice_name"),
        latest_decision_claim_gate_decision=latest_decision_claim_gate_decision,
        latest_decision_rejection_reasons=(),
    )


def default_work_state_output_path() -> Path:
    base = os.getenv("LOCALAPPDATA") or os.getenv("APPDATA") or str(Path.home() / ".foundups")
    return Path(base) / DEFAULT_RUNTIME_RELATIVE_PATH


def _resolve_read_path(repo_root: Path, value: Path | str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = repo_root / path
    return path.resolve()


def _resolve_optional_read_path(repo_root: Path, value: Path | str | None) -> Path | None:
    if not value:
        return None
    return _resolve_read_path(repo_root, value)


def _resolve_output_path(repo_root: Path, value: Path | str | None) -> Path | None:
    if value:
        path = Path(value)
        if not path.is_absolute():
            path = repo_root / path
        return path.resolve()
    return default_work_state_output_path().resolve()


def _read_required_text(path: Path, missing_reason: str, reasons: list[str]) -> Optional[str]:
    if not path.exists() or not path.is_file():
        reasons.append(missing_reason)
        return None
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        reasons.append(f"{missing_reason}:unreadable")
        return None
    if not text.strip():
        reasons.append(f"{missing_reason}:empty")
        return None
    return text


def _read_required_records(
    path: Path | None,
    missing_reason: str,
    reasons: list[str],
) -> tuple[Mapping[str, Any], ...]:
    if path is None:
        reasons.append(missing_reason)
        return ()
    if not path.exists() or not path.is_file():
        reasons.append(missing_reason)
        return ()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        reasons.append(f"{missing_reason}:malformed_json")
        return ()
    if isinstance(payload, Mapping):
        raw_records = payload.get("records", ())
    else:
        raw_records = payload
    if not isinstance(raw_records, Sequence) or isinstance(raw_records, (str, bytes)):
        reasons.append(f"{missing_reason}:records_not_array")
        return ()
    records = tuple(record for record in raw_records if isinstance(record, Mapping))
    if not records:
        reasons.append(missing_reason)
    return records


def _load_latest_decision(
    store: ReadOnlyAuditDecisionStore | None,
) -> tuple[Mapping[str, Any] | None, tuple[str, ...]]:
    reader = store if store is not None else AgentDbReadOnlyAuditDecisionStore()
    try:
        decision = reader.load_latest_readonly_audit_decision()
    except Exception:
        return None, ("latest_readonly_audit_decision_load_failed",)
    if decision is None:
        return None, ("latest_readonly_audit_decision_missing",)
    reasons: list[str] = []
    if decision.get("accepted") is not True:
        reasons.append("latest_readonly_audit_decision_not_accepted")
    action = str(decision.get("action") or "").strip().upper()
    if action not in {"FIX", "REVISE", "RESEARCH_MORE"}:
        reasons.append("latest_readonly_audit_decision_action_not_work")
    if not str(decision.get("decision_id") or "").strip():
        reasons.append("latest_readonly_audit_decision_missing_id")
    if not str(decision.get("next_slice_name") or "").strip():
        reasons.append("latest_readonly_audit_decision_missing_next_slice")
    return decision, tuple(reasons)


def _decision_text(decision: Mapping[str, Any] | None, key: str) -> Optional[str]:
    if not decision:
        return None
    value = str(decision.get(key) or "").strip()
    return value or None


def _is_inside(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _not_ready(
    *,
    reasons: Sequence[str],
    output_path: Path | None,
    runtime_result: AuthoritativeWorkStateRefreshResult | None = None,
    latest_decision: Mapping[str, Any] | None = None,
    latest_decision_attempted: bool = False,
    latest_decision_claim_gate_decision: Optional[str] = None,
) -> RedDogMainWorkStateRefreshBootstrapResult:
    latest_reasons = tuple(
        reason
        for reason in reasons
        if str(reason).startswith("latest_readonly_audit_decision")
        or str(reason).startswith("persisted_decision_claim_gate")
    )
    return RedDogMainWorkStateRefreshBootstrapResult(
        accepted=False,
        status=REDDOG_WORK_STATE_BOOTSTRAP_NOT_READY,
        work_state_path=str(output_path) if output_path else None,
        refresh_id=runtime_result.receipt.refresh_id if runtime_result else None,
        committed_revision=runtime_result.receipt.committed_revision if runtime_result else None,
        selected_slice=runtime_result.receipt.selected_slice if runtime_result else None,
        queue_item_count=0,
        rejection_reasons=tuple(dict.fromkeys(str(reason) for reason in reasons if str(reason).strip())),
        latest_decision_attempted=latest_decision_attempted,
        latest_decision_id=_decision_text(latest_decision, "decision_id"),
        latest_decision_action=_decision_text(latest_decision, "action"),
        latest_decision_next_slice=_decision_text(latest_decision, "next_slice_name"),
        latest_decision_claim_gate_decision=latest_decision_claim_gate_decision,
        latest_decision_rejection_reasons=latest_reasons,
    )


__all__ = [
    "DEFAULT_ACTIVE_SLICE_LEDGER",
    "DEFAULT_RUNTIME_RELATIVE_PATH",
    "DEFAULT_WORK_LEDGER_JSON",
    "REDDOG_WORK_STATE_BOOTSTRAP_APPLIED",
    "REDDOG_WORK_STATE_BOOTSTRAP_DISABLED",
    "REDDOG_WORK_STATE_BOOTSTRAP_NOT_READY",
    "RedDogMainWorkStateRefreshBootstrapResult",
    "default_work_state_output_path",
    "run_reddog_main_authoritative_work_state_refresh_bootstrap",
]
