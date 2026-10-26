"""Storage-backend and corruption tests for resident request reservations."""

from __future__ import annotations

import json
from contextlib import contextmanager
from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.src.reddog_resident_conversation_request_journal import (
    AgentDbResidentConversationRequestJournal,
    reserve_bound_resident_conversation_request,
)
from modules.communication.moltbot_bridge.src.reddog_resident_conversation_request_reservation_contract import (
    reservation_record,
)
from modules.communication.moltbot_bridge.tests.reddog_conversation_scope_test_support import (
    NOW,
    TestAgentDb,
    digest,
)
from modules.communication.moltbot_bridge.tests.test_reddog_resident_conversation_request_journal import (
    _journal,
    _reserve,
)
from modules.communication.moltbot_bridge.tests.test_reddog_resident_conversation_scope_binding import (
    _bind,
    _create,
    _request,
    _store,
)


def _distinct_request(conversation_id: str, label: str):
    return _request(
        conversation_id,
        request_id=digest({"request": label}),
        turn_id=digest({"turn": label}),
        client_nonce=digest({"nonce": label}),
        idempotency_key=digest({"idempotency": label}),
        operator_text=f"Distinct admitted request {label}.",
    )


def test_per_conversation_capacity_fails_closed(tmp_path: Path, monkeypatch) -> None:
    path = tmp_path / "capacity.sqlite"
    created = _create(path)
    assert _reserve(path, _request(created.conversation_id)).accepted is True
    monkeypatch.setattr(
        "modules.communication.moltbot_bridge.src."
        "reddog_resident_conversation_request_journal_store."
        "MAX_REQUESTS_PER_CONVERSATION",
        1,
    )

    rejected = _reserve(path, _distinct_request(created.conversation_id, "second"))

    assert rejected.rejection_reasons == (
        "resident_conversation_request_conversation_capacity",
    )


def test_global_capacity_fails_closed(tmp_path: Path, monkeypatch) -> None:
    path = tmp_path / "global-capacity.sqlite"
    created = _create(path)
    assert _reserve(path, _request(created.conversation_id)).accepted is True
    monkeypatch.setattr(
        "modules.communication.moltbot_bridge.src."
        "reddog_resident_conversation_request_journal_store.MAX_REQUESTS_TOTAL",
        1,
    )

    rejected = _reserve(path, _distinct_request(created.conversation_id, "global"))

    assert rejected.rejection_reasons == (
        "resident_conversation_request_journal_capacity",
    )


def test_tampered_stored_record_never_replays(tmp_path: Path) -> None:
    path = tmp_path / "tampered.sqlite"
    created = _create(path)
    request = _request(created.conversation_id)
    assert _reserve(path, request).accepted is True
    with TestAgentDb(path).db.get_connection() as connection:
        connection.execute(
            "UPDATE reddog_conversation_request_journal "
            "SET reservation_json = ? WHERE conversation_id = ?",
            ("{}", created.conversation_id),
        )

    rejected = _reserve(path, request)
    loaded = _journal(path).load(created.conversation_id, request.idempotency_key)

    assert rejected.rejection_reasons == (
        "resident_conversation_request_idempotency_conflict",
    )
    assert loaded["reason"] == "resident_conversation_request_idempotency_conflict"


def test_store_clock_rejects_backdated_scope_expiry(tmp_path: Path) -> None:
    path = tmp_path / "backdated-expiry.sqlite"
    created = _create(path, ttl_seconds=10)
    request = _request(created.conversation_id)
    binding = _bind(path, request)
    candidate = reservation_record(request, binding, NOW)
    journal = AgentDbResidentConversationRequestJournal(
        lambda: TestAgentDb(path), clock=lambda: NOW + 10
    )

    rejected = journal.reserve(
        candidate, admission_authority=binding._reservation_capability
    )

    assert rejected["reason"] == "resident_conversation_request_journal_admission_invalid"
    assert _journal(path).load(
        created.conversation_id, request.idempotency_key
    )["reason"] == "resident_conversation_request_reservation_missing"


@pytest.mark.parametrize(
    "column", ["conversation_id", "idempotency_key", "request_id", "client_nonce"]
)
def test_load_and_replay_reject_mismatched_index_columns(
    tmp_path: Path, column: str
) -> None:
    path = tmp_path / "column-tamper.sqlite"
    created = _create(path)
    request = _request(created.conversation_id)
    assert _reserve(path, request).accepted is True
    altered = digest({"altered-column": column})
    with TestAgentDb(path).db.get_connection() as connection:
        connection.execute(
            f"UPDATE reddog_conversation_request_journal SET {column} = ?",
            (altered,),
        )

    conversation_id = altered if column == "conversation_id" else created.conversation_id
    idempotency_key = altered if column == "idempotency_key" else request.idempotency_key
    loaded = _journal(path).load(conversation_id, idempotency_key)
    replayed = _reserve(path, request)

    assert loaded["reason"] == "resident_conversation_request_idempotency_conflict"
    assert replayed.rejection_reasons == (
        "resident_conversation_request_idempotency_conflict",
    )


def test_postgres_storage_path_uses_locked_portable_sql(tmp_path: Path) -> None:
    path = tmp_path / "postgres-contract.sqlite"
    created = _create(path)
    request = _request(created.conversation_id)
    binding = _bind(path, request)
    scope = _store(path).load(created.conversation_id)["record"]
    candidate = reservation_record(request, binding, NOW)
    statements: list[str] = []

    class Cursor:
        def __init__(self, *, one=None, many=None, rowcount=0):
            self.one, self.many, self.rowcount = one, many or [], rowcount

        def fetchone(self):
            return self.one

        def fetchall(self):
            return self.many

    class Connection:
        def execute(self, query, _params=()):
            normalized = " ".join(query.split())
            statements.append(normalized)
            if "SELECT conversation_id" in normalized:
                return Cursor(many=[])
            if "SELECT revision, scope_json" in normalized:
                return Cursor(one={"revision": 0, "scope_json": json.dumps(scope)})
            if "SELECT total_requests" in normalized:
                return Cursor(one={"total_requests": 0})
            if "SELECT COUNT(*)" in normalized:
                return Cursor(one={"count": 0})
            if normalized.startswith("INSERT INTO reddog_conversation_request_journal ("):
                return Cursor(rowcount=1)
            if normalized.startswith("UPDATE reddog_conversation_request_journal_state"):
                return Cursor(rowcount=1)
            return Cursor()

    class Layer:
        @contextmanager
        def get_connection(self):
            yield Connection()

        def backend_info(self):
            return {"engine": "postgres"}

    class PgAgentDb:
        db = Layer()

    journal = AgentDbResidentConversationRequestJournal(
        lambda: PgAgentDb(), clock=lambda: NOW
    )
    direct = journal.reserve(candidate)
    result = reserve_bound_resident_conversation_request(
        journal=journal, request=request, binding=binding, now_epoch=NOW,
    )

    assert direct["reason"] == "resident_conversation_request_journal_admission_invalid"
    assert result.accepted is True
    assert not any("BEGIN IMMEDIATE" in statement for statement in statements)
    assert any(statement.endswith("FOR UPDATE") for statement in statements)
    assert any("ON CONFLICT DO NOTHING" in statement for statement in statements)
