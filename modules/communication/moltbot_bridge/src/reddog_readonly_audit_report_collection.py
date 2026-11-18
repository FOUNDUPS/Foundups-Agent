"""Persist and collect RedDog read-only audit reports.

Slice: REDDOG_READONLY_AUDIT_REPORT_COLLECTION_PHASE1

This module stores accepted read-only audit task reports in AgentDB and
collects them back into the existing read-only audit swarm report validator.
It performs no model calls, shell commands, task execution, repository writes,
worktree operations, OpenClaw enqueue, Hermes/WRE dispatch, or HoloIndex
mutation/re-index.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Mapping, Optional, Protocol, Sequence

from modules.communication.moltbot_bridge.src.reddog_openclaw_readonly_audit_swarm_enqueue import (
    READONLY_AUDIT_TASK_SOURCE,
)
from modules.communication.moltbot_bridge.src.reddog_openclaw_readonly_audit_swarm_runtime import (
    ReadOnlyAuditReportValidationResult,
    ReadOnlyAuditSwarmPlan,
    validate_reddog_openclaw_readonly_audit_reports,
)


READONLY_AUDIT_REPORT_PERSIST_ACCEPT = "READONLY_AUDIT_REPORT_PERSIST_ACCEPT"
READONLY_AUDIT_REPORT_PERSIST_REJECT = "READONLY_AUDIT_REPORT_PERSIST_REJECT"
READONLY_AUDIT_REPORT_COLLECTION_ACCEPT = "READONLY_AUDIT_REPORT_COLLECTION_ACCEPT"
READONLY_AUDIT_REPORT_COLLECTION_REJECT = "READONLY_AUDIT_REPORT_COLLECTION_REJECT"


class ReadOnlyAuditReportReason:
    WRONG_SOURCE = "REJECT_READONLY_AUDIT_REPORT_WRONG_SOURCE"
    TASK_NOT_ACCEPTED = "REJECT_READONLY_AUDIT_REPORT_TASK_NOT_ACCEPTED"
    MISSING_STRUCTURED_RESULT = "REJECT_READONLY_AUDIT_REPORT_MISSING_STRUCTURED_RESULT"
    REPORT_NOT_ACCEPTED = "REJECT_READONLY_AUDIT_REPORT_NOT_ACCEPTED"
    MISSING_SWARM_RECEIPT = "REJECT_READONLY_AUDIT_REPORT_MISSING_SWARM_RECEIPT"
    MISSING_ASSIGNMENT = "REJECT_READONLY_AUDIT_REPORT_MISSING_ASSIGNMENT"
    MISSING_REPORT = "REJECT_READONLY_AUDIT_REPORT_MISSING_REPORT"
    REPORT_BINDING_MISMATCH = "REJECT_READONLY_AUDIT_REPORT_BINDING_MISMATCH"
    REPORT_CLAIMS_MUTATION = "REJECT_READONLY_AUDIT_REPORT_CLAIMS_MUTATION"
    REPORT_MISSING_EVIDENCE = "REJECT_READONLY_AUDIT_REPORT_MISSING_EVIDENCE"
    STORE_REJECTED = "REJECT_READONLY_AUDIT_REPORT_STORE_REJECTED"


@dataclass(frozen=True)
class ReadOnlyAuditReportRecord:
    task_id: str
    swarm_id: str
    assignment_id: str
    lane_id: str
    snapshot_receipt_id: str
    report_digest: str
    report: Mapping[str, Any]
    stored_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "swarm_id": self.swarm_id,
            "assignment_id": self.assignment_id,
            "lane_id": self.lane_id,
            "snapshot_receipt_id": self.snapshot_receipt_id,
            "report_digest": self.report_digest,
            "report": dict(self.report),
            "stored_at": self.stored_at,
        }


@dataclass(frozen=True)
class ReadOnlyAuditReportPersistResult:
    accepted: bool
    status: str
    task_id: str
    swarm_id: Optional[str]
    assignment_id: Optional[str]
    report_digest: Optional[str]
    rejection_reasons: tuple[str, ...]
    no_model_call_performed: bool = True
    no_shell_command_executed: bool = True
    no_repo_mutation_performed: bool = True
    no_holoindex_reindex_performed: bool = True
    no_openclaw_enqueue_performed: bool = True
    no_hermes_dispatch_performed: bool = True
    no_worktree_operation_performed: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ReadOnlyAuditReportCollectionResult:
    accepted: bool
    status: str
    swarm_id: str
    report_count: int
    validation: ReadOnlyAuditReportValidationResult
    rejection_reasons: tuple[str, ...]
    no_model_call_performed: bool = True
    no_shell_command_executed: bool = True
    no_repo_mutation_performed: bool = True
    no_holoindex_reindex_performed: bool = True
    no_openclaw_enqueue_performed: bool = True
    no_hermes_dispatch_performed: bool = True
    no_worktree_operation_performed: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "accepted": self.accepted,
            "status": self.status,
            "swarm_id": self.swarm_id,
            "report_count": self.report_count,
            "validation": self.validation.to_dict(),
            "rejection_reasons": list(self.rejection_reasons),
            "no_model_call_performed": self.no_model_call_performed,
            "no_shell_command_executed": self.no_shell_command_executed,
            "no_repo_mutation_performed": self.no_repo_mutation_performed,
            "no_holoindex_reindex_performed": self.no_holoindex_reindex_performed,
            "no_openclaw_enqueue_performed": self.no_openclaw_enqueue_performed,
            "no_hermes_dispatch_performed": self.no_hermes_dispatch_performed,
            "no_worktree_operation_performed": self.no_worktree_operation_performed,
        }


class ReadOnlyAuditReportStore(Protocol):
    def store_readonly_audit_report(self, record: ReadOnlyAuditReportRecord) -> Mapping[str, Any]: ...

    def load_readonly_audit_reports(self, swarm_id: str) -> Sequence[Mapping[str, Any]]: ...


class AgentDbReadOnlyAuditReportStore:
    """AgentDB-backed store for read-only audit report records."""

    def __init__(self, agent_db_factory: Optional[Any] = None) -> None:
        self._agent_db_factory = agent_db_factory

    def store_readonly_audit_report(self, record: ReadOnlyAuditReportRecord) -> Mapping[str, Any]:
        db = self._agent_db()
        self._ensure_table(db)
        report_json = _canonical_json(record.report)
        with db.db.get_connection() as conn:
            existing = conn.execute(
                """
                SELECT report_digest FROM reddog_readonly_audit_reports
                WHERE assignment_id = ?
                """,
                (record.assignment_id,),
            ).fetchone()
            if existing:
                existing_digest = existing["report_digest"] if hasattr(existing, "keys") else existing[0]
                if existing_digest == record.report_digest:
                    return {"ok": True, "stored": False, "idempotent": True}
                return {"ok": False, "reason": "conflicting_assignment_report"}

            conn.execute(
                """
                INSERT INTO reddog_readonly_audit_reports
                (assignment_id, task_id, swarm_id, lane_id, snapshot_receipt_id,
                 report_digest, report_json, stored_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.assignment_id,
                    record.task_id,
                    record.swarm_id,
                    record.lane_id,
                    record.snapshot_receipt_id,
                    record.report_digest,
                    report_json,
                    record.stored_at,
                ),
            )
        return {"ok": True, "stored": True}

    def load_readonly_audit_reports(self, swarm_id: str) -> Sequence[Mapping[str, Any]]:
        db = self._agent_db()
        self._ensure_table(db)
        rows = db.db.execute_query(
            """
            SELECT report_json FROM reddog_readonly_audit_reports
            WHERE swarm_id = ?
            ORDER BY lane_id ASC, assignment_id ASC
            """,
            (swarm_id,),
        )
        reports: list[Mapping[str, Any]] = []
        for row in rows:
            value = row["report_json"] if isinstance(row, Mapping) else row[0]
            reports.append(json.loads(value))
        return tuple(reports)

    def _agent_db(self) -> Any:
        factory = self._agent_db_factory
        if factory is None:
            from modules.infrastructure.database.src.agent_db import AgentDB

            factory = AgentDB
        return factory()

    @staticmethod
    def _ensure_table(db: Any) -> None:
        with db.db.get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS reddog_readonly_audit_reports (
                    assignment_id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL,
                    swarm_id TEXT NOT NULL,
                    lane_id TEXT NOT NULL,
                    snapshot_receipt_id TEXT NOT NULL,
                    report_digest TEXT NOT NULL,
                    report_json TEXT NOT NULL,
                    stored_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_reddog_readonly_audit_reports_swarm
                ON reddog_readonly_audit_reports(swarm_id)
                """
            )


def persist_reddog_readonly_audit_task_report(
    *,
    task_id: str,
    task_context: Mapping[str, Any],
    task_result: Mapping[str, Any],
    store: ReadOnlyAuditReportStore | None = None,
    now: datetime | None = None,
) -> ReadOnlyAuditReportPersistResult:
    """Persist an accepted RedDog read-only audit task report."""

    reasons: list[str] = []
    if task_context.get("source") != READONLY_AUDIT_TASK_SOURCE:
        reasons.append(ReadOnlyAuditReportReason.WRONG_SOURCE)
    if task_result.get("ok") is not True:
        reasons.append(ReadOnlyAuditReportReason.TASK_NOT_ACCEPTED)

    structured = task_result.get("structured_result")
    if not isinstance(structured, Mapping):
        reasons.append(ReadOnlyAuditReportReason.MISSING_STRUCTURED_RESULT)
        structured = {}
    elif structured.get("accepted") is not True:
        reasons.append(ReadOnlyAuditReportReason.REPORT_NOT_ACCEPTED)

    swarm_receipt = task_context.get("swarm_receipt")
    if not isinstance(swarm_receipt, Mapping):
        reasons.append(ReadOnlyAuditReportReason.MISSING_SWARM_RECEIPT)
        swarm_receipt = {}
    assignment = task_context.get("assignment")
    if not isinstance(assignment, Mapping):
        reasons.append(ReadOnlyAuditReportReason.MISSING_ASSIGNMENT)
        assignment = {}
    report = structured.get("report") if isinstance(structured, Mapping) else None
    if not isinstance(report, Mapping):
        reasons.append(ReadOnlyAuditReportReason.MISSING_REPORT)
        report = {}

    swarm_id = str(swarm_receipt.get("swarm_id") or "").strip()
    assignment_id = str(assignment.get("assignment_id") or "").strip()
    lane_id = str(assignment.get("lane_id") or "").strip()
    snapshot_receipt_id = str(assignment.get("snapshot_receipt_id") or "").strip()
    report_digest = str(report.get("report_digest") or "").strip()

    if not _report_matches_assignment(
        report=report,
        assignment_id=assignment_id,
        lane_id=lane_id,
        snapshot_receipt_id=snapshot_receipt_id,
    ):
        reasons.append(ReadOnlyAuditReportReason.REPORT_BINDING_MISMATCH)
    if report.get("repo_mutation_performed") is True or report.get("execution_performed") is True:
        reasons.append(ReadOnlyAuditReportReason.REPORT_CLAIMS_MUTATION)
    if report.get("openclaw_enqueue_performed") is True:
        reasons.append(ReadOnlyAuditReportReason.REPORT_CLAIMS_MUTATION)
    evidence_refs = report.get("evidence_refs")
    if not isinstance(evidence_refs, Sequence) or isinstance(evidence_refs, (str, bytes)) or not evidence_refs:
        reasons.append(ReadOnlyAuditReportReason.REPORT_MISSING_EVIDENCE)
    if not swarm_id or not assignment_id or not lane_id or not snapshot_receipt_id or not report_digest:
        reasons.append(ReadOnlyAuditReportReason.REPORT_BINDING_MISMATCH)

    deduped = _dedupe(reasons)
    if deduped:
        return _persist_result(
            accepted=False,
            task_id=task_id,
            swarm_id=swarm_id or None,
            assignment_id=assignment_id or None,
            report_digest=report_digest or None,
            reasons=deduped,
        )

    writer = store if store is not None else AgentDbReadOnlyAuditReportStore()
    record = ReadOnlyAuditReportRecord(
        task_id=str(task_id),
        swarm_id=swarm_id,
        assignment_id=assignment_id,
        lane_id=lane_id,
        snapshot_receipt_id=snapshot_receipt_id,
        report_digest=report_digest,
        report=report,
        stored_at=_iso8601(now),
    )
    try:
        write_result = writer.store_readonly_audit_report(record)
    except Exception:
        write_result = {"ok": False, "reason": "store_exception"}
    if not isinstance(write_result, Mapping) or write_result.get("ok") is not True:
        return _persist_result(
            accepted=False,
            task_id=task_id,
            swarm_id=swarm_id,
            assignment_id=assignment_id,
            report_digest=report_digest,
            reasons=(ReadOnlyAuditReportReason.STORE_REJECTED,),
        )

    return _persist_result(
        accepted=True,
        task_id=task_id,
        swarm_id=swarm_id,
        assignment_id=assignment_id,
        report_digest=report_digest,
        reasons=(),
    )


def collect_reddog_readonly_audit_report_bundle(
    *,
    plan: ReadOnlyAuditSwarmPlan,
    store: ReadOnlyAuditReportStore | None = None,
) -> ReadOnlyAuditReportCollectionResult:
    """Load persisted reports for a swarm plan and validate the bundle."""

    reader = store if store is not None else AgentDbReadOnlyAuditReportStore()
    reports = tuple(reader.load_readonly_audit_reports(plan.receipt.swarm_id))
    validation = validate_reddog_openclaw_readonly_audit_reports(plan=plan, reports=reports)
    status = READONLY_AUDIT_REPORT_COLLECTION_ACCEPT if validation.accepted else READONLY_AUDIT_REPORT_COLLECTION_REJECT
    return ReadOnlyAuditReportCollectionResult(
        accepted=validation.accepted,
        status=status,
        swarm_id=plan.receipt.swarm_id,
        report_count=len(reports),
        validation=validation,
        rejection_reasons=validation.rejection_reasons,
    )


def _report_matches_assignment(
    *,
    report: Mapping[str, Any],
    assignment_id: str,
    lane_id: str,
    snapshot_receipt_id: str,
) -> bool:
    return (
        str(report.get("assignment_id") or "").strip() == assignment_id
        and str(report.get("lane_id") or "").strip() == lane_id
        and str(report.get("snapshot_receipt_id") or "").strip() == snapshot_receipt_id
    )


def _persist_result(
    *,
    accepted: bool,
    task_id: str,
    swarm_id: Optional[str],
    assignment_id: Optional[str],
    report_digest: Optional[str],
    reasons: Sequence[str],
) -> ReadOnlyAuditReportPersistResult:
    return ReadOnlyAuditReportPersistResult(
        accepted=accepted,
        status=READONLY_AUDIT_REPORT_PERSIST_ACCEPT if accepted else READONLY_AUDIT_REPORT_PERSIST_REJECT,
        task_id=str(task_id),
        swarm_id=swarm_id,
        assignment_id=assignment_id,
        report_digest=report_digest,
        rejection_reasons=tuple(reasons),
    )


def _iso8601(now: datetime | None = None) -> str:
    value = now or datetime.now(timezone.utc)
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)


def _dedupe(values: Sequence[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(str(value) for value in values if str(value).strip()))


__all__ = [
    "AgentDbReadOnlyAuditReportStore",
    "READONLY_AUDIT_REPORT_COLLECTION_ACCEPT",
    "READONLY_AUDIT_REPORT_COLLECTION_REJECT",
    "READONLY_AUDIT_REPORT_PERSIST_ACCEPT",
    "READONLY_AUDIT_REPORT_PERSIST_REJECT",
    "ReadOnlyAuditReportCollectionResult",
    "ReadOnlyAuditReportPersistResult",
    "ReadOnlyAuditReportReason",
    "ReadOnlyAuditReportRecord",
    "ReadOnlyAuditReportStore",
    "collect_reddog_readonly_audit_report_bundle",
    "persist_reddog_readonly_audit_task_report",
]
