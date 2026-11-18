"""SQLite codec helpers for the durable revocation authority store."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.reddog_signer_secret_grant_revocation_authority_binding import (
    STORE_SCHEMA,
    SignerGrantRevocationAuthorityBinding,
)
from modules.communication.moltbot_bridge.src.reddog_signer_secret_grant_revocation_contract import (
    signer_grant_revocation_snapshot_id,
)


def open_revocation_db(path: Path, *, read_only: bool) -> sqlite3.Connection:
    target = f"{path.as_uri()}?mode=ro" if read_only else str(path)
    connection = sqlite3.connect(
        target, uri=read_only, timeout=30, isolation_level=None
    )
    connection.execute("PRAGMA busy_timeout=30000")
    if read_only:
        connection.execute("PRAGMA query_only=ON")
    else:
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=FULL")
    return connection


def metadata(binding: SignerGrantRevocationAuthorityBinding) -> tuple[str, ...]:
    return (
        STORE_SCHEMA, binding.primary_store_id,
        binding.primary_durability_receipt_id, binding.context_digest(),
    )


def require_metadata(
    connection: sqlite3.Connection, binding: SignerGrantRevocationAuthorityBinding
) -> None:
    if connection.execute("SELECT * FROM metadata").fetchall() != [metadata(binding)]:
        raise ValueError("revocation_store_identity_mismatch")


def state_row(connection: sqlite3.Connection) -> tuple[str | None, str | None]:
    rows = connection.execute(
        "SELECT current_snapshot_id,pending_snapshot_id FROM state WHERE singleton=1"
    ).fetchall()
    if len(rows) != 1:
        raise ValueError("revocation_store_state_invalid")
    return rows[0]


def payload(
    connection: sqlite3.Connection,
    snapshot_id: str | None,
    *,
    expected_status: str,
) -> dict[str, Any] | None:
    if snapshot_id is None:
        return None
    row = connection.execute(
        "SELECT payload_json,status FROM snapshots WHERE snapshot_id=?", (snapshot_id,)
    ).fetchone()
    if row is None or row[1] != expected_status:
        raise ValueError("revocation_store_snapshot_missing")
    try:
        value = json.loads(str(row[0]))
        valid = (
            isinstance(value, dict)
            and value.get("snapshot_id") == snapshot_id
            and signer_grant_revocation_snapshot_id(value) == snapshot_id
        )
    except Exception:
        valid = False
    if not valid:
        raise ValueError("revocation_store_snapshot_invalid")
    return dict(value)


def require_authority_graph(
    connection: sqlite3.Connection,
    current_id: str | None,
    pending_id: str | None,
) -> None:
    rows = connection.execute(
        "SELECT snapshot_id,sequence,payload_json,status FROM snapshots "
        "ORDER BY sequence"
    ).fetchall()
    expected_count = 0
    if current_id is not None:
        current = payload(connection, current_id, expected_status="COMMITTED")
        expected_count = int(current["sequence"])
    if pending_id is not None:
        pending = payload(connection, pending_id, expected_status="PREPARED")
        if int(pending["sequence"]) != expected_count + 1:
            raise ValueError("revocation_store_graph_invalid")
        expected_count += 1
    if len(rows) != expected_count:
        raise ValueError("revocation_store_graph_invalid")
    for expected_sequence, row in enumerate(rows, start=1):
        expected_status = "PREPARED" if row[0] == pending_id else "COMMITTED"
        if row[1] != expected_sequence or row[3] != expected_status:
            raise ValueError("revocation_store_graph_invalid")
        payload(connection, str(row[0]), expected_status=expected_status)


def candidate(value: Mapping[str, Any]) -> dict[str, Any]:
    result = dict(value)
    if type(result.get("sequence")) is not int or type(result.get("snapshot_id")) is not str:
        raise ValueError("revocation_store_snapshot_invalid")
    return result


def next_sequence(current: Mapping[str, Any] | None) -> int:
    return 1 if current is None else int(current["sequence"]) + 1


def require_monotonic(
    current: Mapping[str, Any] | None, candidate_value: Mapping[str, Any]
) -> None:
    if current is None:
        return
    for name in ("revoked_grant_ids", "revoked_key_epochs"):
        if not set(current[name]).issubset(candidate_value[name]):
            raise ValueError("revocation_store_unrevocation_rejected")


def canonical_payload(value: Mapping[str, Any]) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


__all__ = [
    "candidate", "canonical_payload", "metadata", "next_sequence",
    "open_revocation_db", "payload", "require_authority_graph",
    "require_metadata", "require_monotonic", "state_row",
]
