"""Crash-safe AgentDB staging for E0-authenticated conversation revisions."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any, Callable, Mapping, Optional

from modules.communication.moltbot_bridge.src.reddog_conversation_scope_contract import (
    IMMUTABLE_FIELDS,
    canonical_digest,
    validate_record,
    validate_unsigned_record,
    with_record_digest,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_signing import (
    unsigned_conversation_scope_record,
)


MAX_PENDING_SCOPES = 4096
RECOVERY_VOLATILE_FIELDS = frozenset(
    {"created_at", "updated_at", "expires_at", "record_auth_nonce", "revision_receipts"}
)


class AgentDbConversationScopePendingStore:
    def __init__(self, factory: Optional[Callable[[], Any]] = None) -> None:
        self._factory = factory

    def stage(
        self, record: Mapping[str, Any], *, expected_revision: int
    ) -> Mapping[str, Any]:
        value = dict(record)
        if validate_unsigned_record(value) or int(value.get("conversation_revision", -2)) != expected_revision + 1:
            return _result(False, "conversation_scope_pending_invalid")
        digest = canonical_digest(value)
        recovery = _recovery_digest(value)
        try:
            db = self._agent_db()
            self._ensure(db)
            with db.db.get_connection() as conn:
                existing = conn.execute(
                    "SELECT unsigned_json, unsigned_digest, recovery_digest FROM reddog_conversation_scope_pending WHERE conversation_id = ?",
                    (value["conversation_id"],),
                ).fetchone()
                if existing is not None:
                    raw, stored_digest, existing_recovery = existing
                    stored = json.loads(raw)
                    if (
                        not isinstance(stored, Mapping)
                        or validate_unsigned_record(stored)
                        or canonical_digest(stored) != stored_digest
                        or _recovery_digest(stored) != existing_recovery
                    ):
                        return _result(False, "conversation_scope_pending_conflict")
                    if stored_digest == digest and existing_recovery == recovery:
                        return _result(
                            True, "conversation_scope_pending_recovered", stored
                        )
                    if existing_recovery == recovery:
                        return _result(
                            True,
                            "conversation_scope_pending_recovery_required",
                            stored,
                            recovery_only=True,
                        )
                    return _result(False, "conversation_scope_pending_conflict")
                active = conn.execute(
                    "SELECT revision FROM reddog_conversation_scopes WHERE conversation_id = ?",
                    (value["conversation_id"],),
                ).fetchone()
                if not _active_matches(active, expected_revision):
                    return _result(False, "conversation_scope_revision_conflict")
                count = conn.execute(
                    "SELECT COUNT(*) FROM reddog_conversation_scope_pending"
                ).fetchone()[0]
                if int(count) >= MAX_PENDING_SCOPES:
                    return _result(False, "conversation_scope_pending_capacity")
                conn.execute(
                    "INSERT INTO reddog_conversation_scope_pending VALUES (?, ?, ?, ?, ?, ?)",
                    (value["conversation_id"], expected_revision, _json(value), digest,
                     recovery, datetime.now(UTC).isoformat()),
                )
        except Exception:
            return _result(False, "conversation_scope_store_unavailable")
        return _result(True, "", value)

    def cancel(self, record: Mapping[str, Any], *, expected_revision: int) -> None:
        try:
            db = self._agent_db()
            self._ensure(db)
            with db.db.get_connection() as conn:
                conn.execute(
                    "DELETE FROM reddog_conversation_scope_pending WHERE conversation_id = ? AND expected_revision = ? AND unsigned_digest = ?",
                    (record["conversation_id"], expected_revision, canonical_digest(record)),
                )
        except Exception:
            return

    def finalize(
        self, record: Mapping[str, Any], *, expected_revision: int
    ) -> Mapping[str, Any]:
        value = with_record_digest(record)
        if validate_record(value):
            return _result(False, "conversation_scope_record_invalid")
        unsigned = unsigned_conversation_scope_record(value)
        try:
            return self._finalize(value, unsigned, expected_revision)
        except Exception:
            return _result(False, "conversation_scope_store_unavailable")

    def _finalize(
        self, value: Mapping[str, Any], unsigned: Mapping[str, Any], expected: int
    ) -> Mapping[str, Any]:
        db = self._agent_db()
        self._ensure(db)
        with db.db.get_connection() as conn:
            pending = conn.execute(
                "SELECT expected_revision, unsigned_digest FROM reddog_conversation_scope_pending WHERE conversation_id = ?",
                (value["conversation_id"],),
            ).fetchone()
            if pending is None or int(pending[0]) != expected or pending[1] != canonical_digest(unsigned):
                return _result(False, "conversation_scope_pending_mismatch")
            if expected < 0:
                cursor = _insert_active(conn, value)
            else:
                cursor = _update_active(conn, value, expected)
            if cursor.rowcount != 1:
                return _result(False, "conversation_scope_revision_conflict")
            conn.execute(
                "DELETE FROM reddog_conversation_scope_pending WHERE conversation_id = ?",
                (value["conversation_id"],),
            )
        return _result(True, "", value)

    def _agent_db(self) -> Any:
        if self._factory is not None:
            return self._factory()
        from modules.infrastructure.database.src.agent_db import AgentDB
        return AgentDB()

    @staticmethod
    def _ensure(db: Any) -> None:
        from modules.communication.moltbot_bridge.src.reddog_conversation_scope_store import (
            AgentDbConversationScopeStore,
        )
        AgentDbConversationScopeStore._ensure_table(db)
        with db.db.get_connection() as conn:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS reddog_conversation_scope_pending (
                conversation_id TEXT PRIMARY KEY, expected_revision INTEGER NOT NULL,
                unsigned_json TEXT NOT NULL, unsigned_digest TEXT NOT NULL,
                recovery_digest TEXT NOT NULL, created_at TEXT NOT NULL)"""
            )


def _active_matches(row: Any, expected: int) -> bool:
    return (row is None and expected < 0) or (
        row is not None and int(row[0]) == expected
    )


def _insert_active(conn: Any, value: Mapping[str, Any]) -> Any:
    return conn.execute(
        "INSERT INTO reddog_conversation_scopes VALUES (?, ?, ?, ?, ?, ?)",
        (value["conversation_id"], value["principal_id"],
         value["authorized_foundup_id"], value["conversation_revision"],
         _json(value), datetime.now(UTC).isoformat()),
    )


def _update_active(conn: Any, value: Mapping[str, Any], expected: int) -> Any:
    current = conn.execute(
        "SELECT scope_json FROM reddog_conversation_scopes WHERE conversation_id = ? AND revision = ?",
        (value["conversation_id"], expected),
    ).fetchone()
    if current is None:
        return _NoChange()
    prior = json.loads(current[0])
    if any(value.get(name) != prior.get(name) for name in IMMUTABLE_FIELDS):
        return _NoChange()
    return conn.execute(
        "UPDATE reddog_conversation_scopes SET revision = ?, scope_json = ?, updated_at = ? WHERE conversation_id = ? AND revision = ?",
        (value["conversation_revision"], _json(value), datetime.now(UTC).isoformat(),
         value["conversation_id"], expected),
    )


class _NoChange:
    rowcount = 0


def _recovery_digest(record: Mapping[str, Any]) -> str:
    return canonical_digest(
        {key: value for key, value in record.items() if key not in RECOVERY_VOLATILE_FIELDS}
    )


def _json(value: Mapping[str, Any]) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _result(
    ok: bool,
    reason: str,
    record: Mapping[str, Any] | None = None,
    *,
    recovery_only: bool = False,
) -> Mapping[str, Any]:
    return {
        "ok": ok,
        "reason": reason,
        "record": dict(record) if record else None,
        "recovery_only": recovery_only,
    }


__all__ = [
    "AgentDbConversationScopePendingStore", "MAX_PENDING_SCOPES",
    "RECOVERY_VOLATILE_FIELDS",
]
