"""Persist RedDog read-only audit decision receipts.

Slice: REDDOG_READONLY_AUDIT_DECISION_PERSISTENCE_PHASE1

This module stores accepted read-only audit decision receipts in AgentDB so
RedDog can remember its selected next action across startup cycles. It does not
execute the decision, enqueue new work, call models, run shell commands, mutate
repository files, dispatch Hermes/WRE, create worktrees, or re-index HoloIndex.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Mapping, Optional, Protocol, Sequence

from modules.communication.moltbot_bridge.src.reddog_readonly_audit_decision_runtime import (
    ReadOnlyAuditDecisionReceipt,
)


READONLY_AUDIT_DECISION_PERSIST_ACCEPT = "READONLY_AUDIT_DECISION_PERSIST_ACCEPT"
READONLY_AUDIT_DECISION_PERSIST_REJECT = "READONLY_AUDIT_DECISION_PERSIST_REJECT"


class ReadOnlyAuditDecisionPersistReason:
    DECISION_NOT_ACCEPTED = "REJECT_READONLY_AUDIT_DECISION_NOT_ACCEPTED"
    MISSING_DECISION_ID = "REJECT_READONLY_AUDIT_DECISION_MISSING_DECISION_ID"
    MISSING_SWARM_ID = "REJECT_READONLY_AUDIT_DECISION_MISSING_SWARM_ID"
    MISSING_ACTION = "REJECT_READONLY_AUDIT_DECISION_MISSING_ACTION"
    MISSING_NEXT_SLICE = "REJECT_READONLY_AUDIT_DECISION_MISSING_NEXT_SLICE"
    DECISION_CLAIMS_SIDE_EFFECT = "REJECT_READONLY_AUDIT_DECISION_CLAIMS_SIDE_EFFECT"
    STORE_REJECTED = "REJECT_READONLY_AUDIT_DECISION_STORE_REJECTED"


@dataclass(frozen=True)
class ReadOnlyAuditDecisionRecord:
    decision_id: str
    swarm_id: str
    report_bundle_id: Optional[str]
    action: str
    next_slice_name: Optional[str]
    wsp15_priority: Optional[str]
    decision: Mapping[str, Any]
    stored_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "swarm_id": self.swarm_id,
            "report_bundle_id": self.report_bundle_id,
            "action": self.action,
            "next_slice_name": self.next_slice_name,
            "wsp15_priority": self.wsp15_priority,
            "decision": dict(self.decision),
            "stored_at": self.stored_at,
        }


@dataclass(frozen=True)
class ReadOnlyAuditDecisionPersistResult:
    accepted: bool
    status: str
    decision_id: Optional[str]
    swarm_id: Optional[str]
    action: Optional[str]
    next_slice_name: Optional[str]
    stored: bool
    idempotent: bool
    rejection_reasons: tuple[str, ...]
    no_model_call_performed: bool = True
    no_shell_command_executed: bool = True
    no_repo_mutation_performed: bool = True
    no_holoindex_reindex_performed: bool = True
    no_openclaw_enqueue_performed: bool = True
    no_hermes_dispatch_performed: bool = True
    no_worktree_operation_performed: bool = True
    no_decision_execution_performed: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ReadOnlyAuditDecisionStore(Protocol):
    def store_readonly_audit_decision(self, record: ReadOnlyAuditDecisionRecord) -> Mapping[str, Any]: ...

    def load_latest_readonly_audit_decision(self) -> Optional[Mapping[str, Any]]: ...

    def load_readonly_audit_decision(self, decision_id: str) -> Optional[Mapping[str, Any]]: ...


class AgentDbReadOnlyAuditDecisionStore:
    """AgentDB-backed store for read-only audit decision receipts."""

    def __init__(self, agent_db_factory: Optional[Any] = None) -> None:
        self._agent_db_factory = agent_db_factory

    def store_readonly_audit_decision(self, record: ReadOnlyAuditDecisionRecord) -> Mapping[str, Any]:
        db = self._agent_db()
        self._ensure_table(db)
        decision_json = _canonical_json(record.decision)
        with db.db.get_connection() as conn:
            existing_by_id = conn.execute(
                """
                SELECT decision_json FROM reddog_readonly_audit_decisions
                WHERE decision_id = ?
                """,
                (record.decision_id,),
            ).fetchone()
            if existing_by_id:
                existing_json = (
                    existing_by_id["decision_json"] if hasattr(existing_by_id, "keys") else existing_by_id[0]
                )
                if existing_json == decision_json:
                    return {"ok": True, "stored": False, "idempotent": True}
                return {"ok": False, "reason": "conflicting_decision_id"}

            existing_for_swarm = conn.execute(
                """
                SELECT decision_id FROM reddog_readonly_audit_decisions
                WHERE swarm_id = ?
                """,
                (record.swarm_id,),
            ).fetchone()
            if existing_for_swarm:
                return {"ok": False, "reason": "conflicting_swarm_decision"}

            conn.execute(
                """
                INSERT INTO reddog_readonly_audit_decisions
                (decision_id, swarm_id, report_bundle_id, action, next_slice_name,
                 wsp15_priority, decision_json, stored_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.decision_id,
                    record.swarm_id,
                    record.report_bundle_id,
                    record.action,
                    record.next_slice_name,
                    record.wsp15_priority,
                    decision_json,
                    record.stored_at,
                ),
            )
        return {"ok": True, "stored": True, "idempotent": False}

    def load_latest_readonly_audit_decision(self) -> Optional[Mapping[str, Any]]:
        db = self._agent_db()
        self._ensure_table(db)
        rows = db.db.execute_query(
            """
            SELECT decision_json FROM reddog_readonly_audit_decisions
            ORDER BY stored_at DESC, decision_id DESC
            LIMIT 1
            """
        )
        if not rows:
            return None
        value = rows[0]["decision_json"] if isinstance(rows[0], Mapping) else rows[0][0]
        return json.loads(value)

    def load_readonly_audit_decision(self, decision_id: str) -> Optional[Mapping[str, Any]]:
        db = self._agent_db()
        self._ensure_table(db)
        rows = db.db.execute_query(
            """
            SELECT decision_json FROM reddog_readonly_audit_decisions
            WHERE decision_id = ?
            """,
            (decision_id,),
        )
        if not rows:
            return None
        value = rows[0]["decision_json"] if isinstance(rows[0], Mapping) else rows[0][0]
        return json.loads(value)

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
                CREATE TABLE IF NOT EXISTS reddog_readonly_audit_decisions (
                    decision_id TEXT PRIMARY KEY,
                    swarm_id TEXT NOT NULL UNIQUE,
                    report_bundle_id TEXT,
                    action TEXT NOT NULL,
                    next_slice_name TEXT,
                    wsp15_priority TEXT,
                    decision_json TEXT NOT NULL,
                    stored_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_reddog_readonly_audit_decisions_action
                ON reddog_readonly_audit_decisions(action)
                """
            )


def persist_reddog_readonly_audit_decision(
    *,
    decision: ReadOnlyAuditDecisionReceipt | Mapping[str, Any],
    store: ReadOnlyAuditDecisionStore | None = None,
    now: datetime | None = None,
) -> ReadOnlyAuditDecisionPersistResult:
    """Persist an accepted read-only audit decision receipt."""

    decision_payload = decision.to_dict() if hasattr(decision, "to_dict") else dict(decision)
    reasons: list[str] = []
    accepted = bool(decision_payload.get("accepted") is True)
    decision_id = str(decision_payload.get("decision_id") or "").strip()
    swarm_id = str(decision_payload.get("swarm_id") or "").strip()
    action = str(decision_payload.get("action") or "").strip()
    next_slice = str(decision_payload.get("next_slice_name") or "").strip() or None
    priority = str(decision_payload.get("wsp15_priority") or "").strip() or None

    if not accepted:
        reasons.append(ReadOnlyAuditDecisionPersistReason.DECISION_NOT_ACCEPTED)
    if not decision_id:
        reasons.append(ReadOnlyAuditDecisionPersistReason.MISSING_DECISION_ID)
    if not swarm_id:
        reasons.append(ReadOnlyAuditDecisionPersistReason.MISSING_SWARM_ID)
    if not action:
        reasons.append(ReadOnlyAuditDecisionPersistReason.MISSING_ACTION)
    if action in {"FIX", "REVISE", "RESEARCH_MORE"} and not next_slice:
        reasons.append(ReadOnlyAuditDecisionPersistReason.MISSING_NEXT_SLICE)
    if _claims_side_effect(decision_payload):
        reasons.append(ReadOnlyAuditDecisionPersistReason.DECISION_CLAIMS_SIDE_EFFECT)

    deduped = _dedupe(reasons)
    if deduped:
        return _result(
            accepted=False,
            decision_id=decision_id or None,
            swarm_id=swarm_id or None,
            action=action or None,
            next_slice_name=next_slice,
            stored=False,
            idempotent=False,
            reasons=deduped,
        )

    writer = store if store is not None else AgentDbReadOnlyAuditDecisionStore()
    record = ReadOnlyAuditDecisionRecord(
        decision_id=decision_id,
        swarm_id=swarm_id,
        report_bundle_id=str(decision_payload.get("report_bundle_id") or "").strip() or None,
        action=action,
        next_slice_name=next_slice,
        wsp15_priority=priority,
        decision=decision_payload,
        stored_at=_iso8601(now),
    )
    try:
        write_result = writer.store_readonly_audit_decision(record)
    except Exception:
        write_result = {"ok": False, "reason": "store_exception"}

    if not isinstance(write_result, Mapping) or write_result.get("ok") is not True:
        return _result(
            accepted=False,
            decision_id=decision_id,
            swarm_id=swarm_id,
            action=action,
            next_slice_name=next_slice,
            stored=False,
            idempotent=False,
            reasons=(ReadOnlyAuditDecisionPersistReason.STORE_REJECTED,),
        )

    return _result(
        accepted=True,
        decision_id=decision_id,
        swarm_id=swarm_id,
        action=action,
        next_slice_name=next_slice,
        stored=bool(write_result.get("stored")),
        idempotent=bool(write_result.get("idempotent")),
        reasons=(),
    )


def _claims_side_effect(decision: Mapping[str, Any]) -> bool:
    return not (
        decision.get("no_model_call_performed") is True
        and decision.get("no_shell_command_executed") is True
        and decision.get("no_repo_mutation_performed") is True
        and decision.get("no_holoindex_reindex_performed") is True
        and decision.get("no_openclaw_enqueue_performed") is True
        and decision.get("no_hermes_dispatch_performed") is True
        and decision.get("no_worktree_operation_performed") is True
    )


def _result(
    *,
    accepted: bool,
    decision_id: Optional[str],
    swarm_id: Optional[str],
    action: Optional[str],
    next_slice_name: Optional[str],
    stored: bool,
    idempotent: bool,
    reasons: Sequence[str],
) -> ReadOnlyAuditDecisionPersistResult:
    return ReadOnlyAuditDecisionPersistResult(
        accepted=accepted,
        status=READONLY_AUDIT_DECISION_PERSIST_ACCEPT if accepted else READONLY_AUDIT_DECISION_PERSIST_REJECT,
        decision_id=decision_id,
        swarm_id=swarm_id,
        action=action,
        next_slice_name=next_slice_name,
        stored=stored,
        idempotent=idempotent,
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
    "AgentDbReadOnlyAuditDecisionStore",
    "READONLY_AUDIT_DECISION_PERSIST_ACCEPT",
    "READONLY_AUDIT_DECISION_PERSIST_REJECT",
    "ReadOnlyAuditDecisionPersistReason",
    "ReadOnlyAuditDecisionPersistResult",
    "ReadOnlyAuditDecisionRecord",
    "ReadOnlyAuditDecisionStore",
    "persist_reddog_readonly_audit_decision",
]
