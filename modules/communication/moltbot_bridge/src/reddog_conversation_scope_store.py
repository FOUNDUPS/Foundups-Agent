"""AgentDB CAS storage for authenticated RedDog conversation scopes."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any, Callable, Mapping, Optional

from modules.communication.moltbot_bridge.src.reddog_conversation_scope_contract import (
    IMMUTABLE_FIELDS,
    MUTABLE_FIELDS,
    validate_record,
    with_record_digest,
)


class AgentDbConversationScopeStore:
    """Store conversation state in AgentDB without adding a second database."""

    def __init__(self, agent_db_factory: Optional[Callable[[], Any]] = None) -> None:
        self._agent_db_factory = agent_db_factory

    def create(self, record: Mapping[str, Any]) -> Mapping[str, Any]:
        value = with_record_digest(record)
        if validate_record(value):
            return _result(False, "conversation_scope_record_invalid")
        try:
            db = self._agent_db()
            self._ensure_table(db)
            with db.db.get_connection() as conn:
                cursor = conn.execute(
                    """
                    INSERT INTO reddog_conversation_scopes
                    (conversation_id, principal_id, foundup_id, revision, scope_json, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(conversation_id) DO NOTHING
                    """,
                    (
                        value["conversation_id"], value["principal_id"],
                        value["authorized_foundup_id"], value["conversation_revision"],
                        _json(value), _now_iso(),
                    ),
                )
        except Exception:
            return _result(False, "conversation_scope_store_unavailable")
        return _result(cursor.rowcount == 1, "" if cursor.rowcount == 1 else "conversation_scope_exists", value)

    def load(self, conversation_id: str) -> Mapping[str, Any]:
        try:
            db = self._agent_db()
            self._ensure_table(db)
            rows = db.db.execute_query(
                "SELECT revision, scope_json FROM reddog_conversation_scopes WHERE conversation_id = ?",
                (conversation_id,),
            )
        except Exception:
            return _result(False, "conversation_scope_store_unavailable")
        if not rows:
            return _result(False, "conversation_scope_missing")
        row = rows[0]
        try:
            revision = int(row["revision"] if isinstance(row, Mapping) else row[0])
            raw = row["scope_json"] if isinstance(row, Mapping) else row[1]
            record = json.loads(raw)
        except (TypeError, ValueError, json.JSONDecodeError, KeyError, IndexError):
            return _result(False, "conversation_scope_store_invalid")
        if (
            not isinstance(record, Mapping)
            or int(record.get("conversation_revision", -1)) != revision
            or validate_record(record)
        ):
            return _result(False, "conversation_scope_store_invalid")
        return _result(True, "", dict(record))

    def compare_and_swap(
        self,
        conversation_id: str,
        *,
        expected_revision: int,
        next_record: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        value = with_record_digest(next_record)
        if validate_record(value):
            return _result(False, "conversation_scope_record_invalid")
        try:
            return self._compare_and_swap(conversation_id, expected_revision, value)
        except Exception:
            return _result(False, "conversation_scope_store_unavailable")

    def _compare_and_swap(
        self, conversation_id: str, expected_revision: int, value: Mapping[str, Any]
    ) -> Mapping[str, Any]:
        db = self._agent_db()
        self._ensure_table(db)
        with db.db.get_connection() as conn:
            row = conn.execute(
                "SELECT revision, scope_json FROM reddog_conversation_scopes WHERE conversation_id = ?",
                (conversation_id,),
            ).fetchone()
            if row is None:
                return _result(False, "conversation_scope_missing")
            current_revision = int(row["revision"] if isinstance(row, Mapping) else row[0])
            current = json.loads(row["scope_json"] if isinstance(row, Mapping) else row[1])
            reason = _cas_reason(current, value, current_revision, expected_revision)
            if reason:
                return _result(False, reason)
            cursor = conn.execute(
                """
                UPDATE reddog_conversation_scopes
                SET principal_id = ?, foundup_id = ?, revision = ?, scope_json = ?, updated_at = ?
                WHERE conversation_id = ? AND revision = ?
                """,
                (
                    value["principal_id"], value["authorized_foundup_id"],
                    value["conversation_revision"], _json(value), _now_iso(),
                    conversation_id, expected_revision,
                ),
            )
        return _result(cursor.rowcount == 1, "" if cursor.rowcount == 1 else "conversation_scope_revision_conflict", value)

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
                CREATE TABLE IF NOT EXISTS reddog_conversation_scopes (
                    conversation_id TEXT PRIMARY KEY,
                    principal_id TEXT NOT NULL,
                    foundup_id TEXT NOT NULL,
                    revision INTEGER NOT NULL,
                    scope_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_reddog_conversation_scope_owner
                ON reddog_conversation_scopes(principal_id, foundup_id, updated_at)
                """
            )


def _result(ok: bool, reason: str, record: Mapping[str, Any] | None = None) -> Mapping[str, Any]:
    return {"ok": ok, "reason": reason, "record": dict(record) if record is not None else None}


def _cas_reason(
    current: Any, value: Mapping[str, Any], current_revision: int, expected_revision: int
) -> str:
    if not isinstance(current, Mapping) or validate_record(current):
        return "conversation_scope_store_invalid"
    if current_revision != expected_revision:
        return "conversation_scope_revision_conflict"
    if any(value.get(field) != current.get(field) for field in IMMUTABLE_FIELDS):
        return "conversation_scope_immutable_binding_changed"
    if set(value) != IMMUTABLE_FIELDS | MUTABLE_FIELDS:
        return "conversation_scope_record_invalid"
    if int(value["conversation_revision"]) != current_revision + 1:
        return "conversation_scope_revision_invalid"
    return ""


def _json(value: Mapping[str, Any]) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


__all__ = ["AgentDbConversationScopeStore"]
