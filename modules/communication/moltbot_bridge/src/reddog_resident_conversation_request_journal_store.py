"""AgentDB storage for durable resident conversation request reservations."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from time import time
from typing import Any, Callable, Mapping, Optional

from modules.communication.moltbot_bridge.src.reddog_conversation_scope_contract import (
    canonical_digest,
    validate_record,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_capability import (
    consume_resident_conversation_request_journal_authority,
)
from modules.communication.moltbot_bridge.src.reddog_resident_conversation_request_reservation_contract import (
    digest_shaped,
    reservation_identity,
    reservation_record_reasons,
)
from modules.communication.moltbot_bridge.src.reddog_resident_conversation_first_turn_contract import (
    SCHEMA_VERSION as FIRST_TURN_SCHEMA_VERSION,
    first_turn_reservation_identity,
    first_turn_reservation_record_reasons,
)


MAX_REQUESTS_PER_CONVERSATION = 4096
MAX_REQUESTS_TOTAL = 65536
_STATE_ID = "global"


class AgentDbResidentConversationRequestJournal:
    """Persist replay evidence in AgentDB; grant no admission authority."""

    def __init__(
        self,
        agent_db_factory: Optional[Callable[[], Any]] = None,
        clock: Optional[Callable[[], int]] = None,
    ) -> None:
        self._agent_db_factory = agent_db_factory
        self._clock = clock or _system_epoch

    def reserve(
        self, record: Mapping[str, Any], *, admission_authority: Any = None
    ) -> Mapping[str, Any]:
        value = dict(record) if isinstance(record, Mapping) else {}
        if _record_reasons(value):
            return _store_result(False, "resident_conversation_request_reservation_invalid")
        try:
            observed_at = self._observed_epoch()
        except Exception:
            return _store_result(
                False, "resident_conversation_request_journal_unavailable"
            )
        authorized = consume_resident_conversation_request_journal_authority(
            admission_authority,
            reservation_id=value["reservation_id"],
            reserved_at=value["reserved_at"],
            observed_at=observed_at,
        )
        if not authorized or observed_at >= value["expires_at"]:
            return _store_result(
                False, "resident_conversation_request_journal_admission_invalid"
            )
        try:
            return self._reserve(value, observed_at)
        except Exception:
            recovered = self._recover_after_store_error(value)
            return recovered or _store_result(
                False, "resident_conversation_request_journal_unavailable"
            )

    def load(self, conversation_id: str, idempotency_key: str) -> Mapping[str, Any]:
        if not digest_shaped(conversation_id) or not digest_shaped(idempotency_key):
            return _store_result(False, "resident_conversation_request_reservation_invalid")
        try:
            db = self._agent_db()
            _backend_engine(db)
            self._ensure_tables(db)
            rows = db.db.execute_query(
                "SELECT conversation_id, idempotency_key, request_id, client_nonce, "
                "reservation_json, reservation_digest "
                "FROM reddog_conversation_request_journal "
                "WHERE conversation_id = ? AND idempotency_key = ?",
                (conversation_id, idempotency_key),
            )
            return _loaded_result(rows, conversation_id, idempotency_key)
        except Exception:
            return _store_result(False, "resident_conversation_request_journal_unavailable")

    def load_related(
        self, *, conversation_id: str, idempotency_key: str,
        request_id: str, client_nonce: str,
    ) -> Mapping[str, Any]:
        """Return a row only when all authenticated resolution keys match."""

        values = (conversation_id, idempotency_key, request_id, client_nonce)
        if not all(digest_shaped(value) for value in values):
            return _store_result(
                False, "resident_conversation_request_reservation_invalid"
            )
        try:
            db = self._agent_db()
            _backend_engine(db)
            self._ensure_tables(db)
            with db.db.get_connection() as connection:
                rows = _related_rows(
                    connection,
                    {
                        "idempotency_key": idempotency_key,
                        "request_id": request_id,
                        "client_nonce": client_nonce,
                    },
                )
            return _loaded_related_result(rows, values)
        except Exception:
            return _store_result(
                False, "resident_conversation_request_journal_unavailable"
            )

    def _reserve(
        self, value: Mapping[str, Any], observed_at: int
    ) -> Mapping[str, Any]:
        db = self._agent_db()
        engine = _backend_engine(db)
        self._ensure_tables(db)
        with db.db.get_connection() as connection:
            _begin_write(connection, engine)
            existing = _related_rows(connection, value)
            if existing:
                return _existing_result(existing, value)
            if not _current_scope_matches(connection, value, engine, observed_at):
                return _store_result(False, "resident_conversation_request_scope_changed")
            reason, total = _capacity_state(connection, value["conversation_id"], engine)
            if reason:
                return _store_result(False, reason)
            cursor = connection.execute(
                """
                INSERT INTO reddog_conversation_request_journal
                (conversation_id, idempotency_key, request_id, client_nonce,
                 reservation_json, reservation_digest, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT DO NOTHING
                """,
                (
                    value["conversation_id"], value["idempotency_key"],
                    value["request_id"], value["client_nonce"], _json(value),
                    canonical_digest(value), datetime.now(UTC).isoformat(),
                ),
            )
            if cursor.rowcount == 1:
                _advance_total(connection, total)
                return _store_result(True, "", value, stored=True)
            return _existing_result(_related_rows(connection, value), value)

    def _recover_after_store_error(
        self, value: Mapping[str, Any]
    ) -> Mapping[str, Any] | None:
        try:
            db = self._agent_db()
            _backend_engine(db)
            self._ensure_tables(db)
            with db.db.get_connection() as connection:
                rows = _related_rows(connection, value)
            return _existing_result(rows, value) if rows else None
        except Exception:
            return None

    def _agent_db(self) -> Any:
        if self._agent_db_factory is not None:
            return self._agent_db_factory()
        from modules.infrastructure.database.src.agent_db import AgentDB

        return AgentDB()

    def _observed_epoch(self) -> int:
        value = self._clock()
        if type(value) is not int or value < 0:
            raise ValueError("resident_conversation_request_journal_clock_invalid")
        return value

    @staticmethod
    def _ensure_tables(db: Any) -> None:
        with db.db.get_connection() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS reddog_conversation_request_journal (
                    conversation_id TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL,
                    request_id TEXT NOT NULL,
                    client_nonce TEXT NOT NULL,
                    reservation_json TEXT NOT NULL,
                    reservation_digest TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (idempotency_key),
                    UNIQUE (request_id),
                    UNIQUE (client_nonce)
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS reddog_conversation_request_journal_state (
                    state_id TEXT PRIMARY KEY,
                    total_requests INTEGER NOT NULL
                )
                """
            )
            connection.execute(
                "INSERT INTO reddog_conversation_request_journal_state "
                "(state_id, total_requests) VALUES (?, ?) ON CONFLICT DO NOTHING",
                (_STATE_ID, 0),
            )


def _backend_engine(db: Any) -> str:
    info = db.db.backend_info()
    engine = info.get("engine") if isinstance(info, Mapping) else None
    if engine not in {"sqlite", "postgres"}:
        raise RuntimeError("resident_conversation_request_journal_backend_unsupported")
    return str(engine)


def _begin_write(connection: Any, engine: str) -> None:
    if engine == "sqlite":
        connection.execute("BEGIN IMMEDIATE")


def _related_rows(connection: Any, record: Mapping[str, Any]) -> list[Any]:
    return list(connection.execute(
        "SELECT conversation_id, idempotency_key, request_id, client_nonce, "
        "reservation_json, reservation_digest "
        "FROM reddog_conversation_request_journal WHERE "
        "idempotency_key = ? OR request_id = ? OR client_nonce = ?",
        (
            record["idempotency_key"], record["request_id"], record["client_nonce"],
        ),
    ).fetchall())


def _current_scope_matches(
    connection: Any, record: Mapping[str, Any], engine: str, observed_at: int
) -> bool:
    query = (
        "SELECT revision, scope_json FROM reddog_conversation_scopes "
        "WHERE conversation_id = ?" + (" FOR UPDATE" if engine == "postgres" else "")
    )
    try:
        row = connection.execute(query, (record["conversation_id"],)).fetchone()
        revision = int(_row_value(row, "revision", 0))
        current = json.loads(_row_value(row, "scope_json", 1))
        receipts = current.get("revision_receipts") if isinstance(current, Mapping) else None
    except (TypeError, ValueError, KeyError, IndexError, json.JSONDecodeError):
        return False
    return bool(
        isinstance(current, Mapping)
        and not validate_record(current)
        and revision == int(record["expected_revision"])
        and current.get("conversation_revision") == revision
        and current.get("record_digest") == record["scope_record_digest"]
        and type(current.get("expires_at")) is int
        and current["expires_at"] > observed_at
        and isinstance(receipts, list) and bool(receipts)
        and isinstance(receipts[-1], Mapping)
        and receipts[-1].get("receipt_id") == record["revision_receipt_id"]
    )


def _capacity_state(
    connection: Any, conversation_id: str, engine: str
) -> tuple[str, int]:
    suffix = " FOR UPDATE" if engine == "postgres" else ""
    state = connection.execute(
        "SELECT total_requests FROM reddog_conversation_request_journal_state "
        "WHERE state_id = ?" + suffix, (_STATE_ID,),
    ).fetchone()
    recorded_total = _integer_row(state, "total_requests")
    actual_total = _integer_row(connection.execute(
        "SELECT COUNT(*) AS count FROM reddog_conversation_request_journal"
    ).fetchone(), "count")
    if recorded_total != actual_total:
        return "resident_conversation_request_journal_integrity", actual_total
    if actual_total >= MAX_REQUESTS_TOTAL:
        return "resident_conversation_request_journal_capacity", actual_total
    scoped = _integer_row(connection.execute(
        "SELECT COUNT(*) AS count FROM reddog_conversation_request_journal "
        "WHERE conversation_id = ?", (conversation_id,),
    ).fetchone(), "count")
    reason = (
        "resident_conversation_request_conversation_capacity"
        if scoped >= MAX_REQUESTS_PER_CONVERSATION else ""
    )
    return reason, actual_total


def _advance_total(connection: Any, expected_total: int) -> None:
    cursor = connection.execute(
        "UPDATE reddog_conversation_request_journal_state "
        "SET total_requests = ? WHERE state_id = ? AND total_requests = ?",
        (expected_total + 1, _STATE_ID, expected_total),
    )
    if cursor.rowcount != 1:
        raise RuntimeError("resident_conversation_request_journal_counter_conflict")


def _existing_result(rows: list[Any], candidate: Mapping[str, Any]) -> Mapping[str, Any]:
    if len(rows) != 1:
        return _store_result(False, "resident_conversation_request_idempotency_conflict")
    existing = _stored_record(rows[0])
    if existing is None or _record_identity(existing) != _record_identity(candidate):
        return _store_result(False, "resident_conversation_request_idempotency_conflict")
    return _store_result(True, "", existing, stored=False, idempotent_replay=True)


def _loaded_result(
    rows: list[Any], conversation_id: str, idempotency_key: str
) -> Mapping[str, Any]:
    if len(rows) != 1:
        return _store_result(False, "resident_conversation_request_reservation_missing")
    record = _stored_record(rows[0])
    if (
        record is None or record.get("conversation_id") != conversation_id
        or record.get("idempotency_key") != idempotency_key
    ):
        return _store_result(False, "resident_conversation_request_idempotency_conflict")
    return _store_result(True, "", record, stored=False)


def _loaded_related_result(
    rows: list[Any], values: tuple[str, str, str, str],
) -> Mapping[str, Any]:
    if not rows:
        return _store_result(False, "resident_conversation_request_reservation_missing")
    if len(rows) != 1:
        return _store_result(False, "resident_conversation_request_idempotency_conflict")
    record = _stored_record(rows[0])
    actual = tuple(
        record.get(name) if record else None
        for name in ("conversation_id", "idempotency_key", "request_id", "client_nonce")
    )
    if actual != values:
        return _store_result(False, "resident_conversation_request_idempotency_conflict")
    return _store_result(True, "", record, stored=False)


def _stored_record(row: Any) -> dict[str, Any] | None:
    try:
        columns = {
            "conversation_id": _row_value(row, "conversation_id", 0),
            "idempotency_key": _row_value(row, "idempotency_key", 1),
            "request_id": _row_value(row, "request_id", 2),
            "client_nonce": _row_value(row, "client_nonce", 3),
        }
        raw = _row_value(row, "reservation_json", 4)
        digest = _row_value(row, "reservation_digest", 5)
        record = json.loads(raw)
    except (TypeError, ValueError, KeyError, IndexError, json.JSONDecodeError):
        return None
    return (
        record if isinstance(record, dict)
        and not _record_reasons(record)
        and canonical_digest(record) == digest
        and all(record.get(key) == value for key, value in columns.items())
        else None
    )


def _record_reasons(record: Mapping[str, Any]) -> tuple[str, ...]:
    return (
        first_turn_reservation_record_reasons(record)
        if record.get("schema_version") == FIRST_TURN_SCHEMA_VERSION
        else reservation_record_reasons(record)
    )


def _record_identity(record: Mapping[str, Any]) -> Mapping[str, Any]:
    return (
        first_turn_reservation_identity(record)
        if record.get("schema_version") == FIRST_TURN_SCHEMA_VERSION
        else reservation_identity(record)
    )


def _row_value(row: Any, name: str, index: int) -> Any:
    if isinstance(row, Mapping):
        return row[name]
    return row[index]


def _integer_row(row: Any, name: str) -> int:
    value = _row_value(row, name, 0)
    if type(value) is not int or value < 0:
        raise ValueError("resident_conversation_request_journal_count_invalid")
    return value


def _store_result(
    ok: bool, reason: str, record: Mapping[str, Any] | None = None, *,
    stored: bool = False, idempotent_replay: bool = False,
) -> Mapping[str, Any]:
    return {
        "ok": ok, "reason": reason, "record": dict(record) if record else None,
        "stored": stored, "idempotent_replay": idempotent_replay,
    }


def _json(value: Mapping[str, Any]) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _system_epoch() -> int:
    return int(time())


__all__ = [
    "AgentDbResidentConversationRequestJournal", "MAX_REQUESTS_PER_CONVERSATION",
    "MAX_REQUESTS_TOTAL",
]
