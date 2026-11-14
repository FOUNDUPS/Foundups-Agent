"""Append-only SQLite primary store for signed grant-revocation snapshots."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator, Mapping

from modules.communication.moltbot_bridge.src.reddog_signer_secret_grant_revocation_authority_binding import (
    SignerGrantRevocationAuthorityBinding,
)
from modules.communication.moltbot_bridge.src.reddog_signer_secret_grant_revocation_store_codec import (
    candidate as _candidate,
    canonical_payload as _json,
    metadata as _metadata,
    next_sequence as _next,
    open_revocation_db as _open,
    payload as _payload,
    require_authority_graph as _require_graph,
    require_metadata as _require_metadata,
    require_monotonic as _require_monotonic,
    state_row as _state_row,
)
from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    validate_runtime_artifact_path,
    validate_runtime_root_path,
)


@dataclass(frozen=True)
class RevocationAuthorityStoreState:
    current: Mapping[str, Any] | None
    pending: Mapping[str, Any] | None


class SignerGrantRevocationAuthorityStore:
    """Writer-side append log; publication ordering belongs to the supply."""

    def __init__(
        self, binding: SignerGrantRevocationAuthorityBinding, *, repo_root: Path | str,
    ) -> None:
        if type(binding) is not SignerGrantRevocationAuthorityBinding:
            raise ValueError("revocation_store_binding_invalid")
        self.binding = binding
        self.repo_root = Path(repo_root).resolve()
        self.allowed_root = validate_runtime_root_path(
            binding.primary_root, repo_root=self.repo_root
        )
        self.path = validate_runtime_artifact_path(
            binding.primary_path, allowed_root=self.allowed_root, repo_root=self.repo_root
        )
        if self.path.parent != self.allowed_root:
            raise ValueError("revocation_store_path_invalid")
        self.allowed_root.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def reader(self) -> object:
        from modules.communication.moltbot_bridge.src.reddog_signer_secret_grant_revocation_authority_reader import (
            SignerGrantRevocationAuthorityReader,
        )

        return SignerGrantRevocationAuthorityReader(
            self.binding, repo_root=self.repo_root
        )

    def state(self) -> RevocationAuthorityStoreState:
        with self._connect(read_only=True) as connection:
            connection.execute("BEGIN")
            _require_metadata(connection, self.binding)
            state = _state_row(connection)
            _require_graph(connection, *state)
            result = RevocationAuthorityStoreState(
                _payload(connection, state[0], expected_status="COMMITTED"),
                _payload(connection, state[1], expected_status="PREPARED"),
            )
            connection.commit()
            return result

    def _prepare_under_lock(self, snapshot: Mapping[str, Any]) -> None:
        """Stage one candidate; caller must hold the signed topology lock."""
        candidate = _candidate(snapshot)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            _require_metadata(connection, self.binding)
            current_id, pending_id = _state_row(connection)
            _require_graph(connection, current_id, pending_id)
            current = _payload(connection, current_id, expected_status="COMMITTED")
            if pending_id is not None or candidate["sequence"] != _next(current):
                connection.rollback()
                raise RuntimeError("revocation_store_prepare_conflict")
            _require_monotonic(current, candidate)
            try:
                connection.execute(
                    "INSERT INTO snapshots(snapshot_id, sequence, payload_json, status) "
                    "VALUES (?, ?, ?, 'PREPARED')",
                    (candidate["snapshot_id"], candidate["sequence"], _json(candidate)),
                )
                connection.execute(
                    "UPDATE state SET pending_snapshot_id=? WHERE singleton=1",
                    (candidate["snapshot_id"],),
                )
                connection.commit()
            except Exception:
                connection.rollback()
                raise

    def _finalize_under_lock(self, snapshot_id: str) -> None:
        """Commit one staged candidate; caller must hold the topology lock."""
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            _require_metadata(connection, self.binding)
            _current, pending = _state_row(connection)
            _require_graph(connection, _current, pending)
            if pending != snapshot_id or _payload(
                connection, pending, expected_status="PREPARED"
            ) is None:
                connection.rollback()
                raise RuntimeError("revocation_store_finalize_conflict")
            changed = connection.execute(
                "UPDATE snapshots SET status='COMMITTED' WHERE snapshot_id=? "
                "AND status='PREPARED'", (snapshot_id,),
            ).rowcount
            if changed != 1:
                connection.rollback()
                raise RuntimeError("revocation_store_finalize_conflict")
            connection.execute(
                "UPDATE state SET current_snapshot_id=?, pending_snapshot_id=NULL "
                "WHERE singleton=1", (snapshot_id,),
            )
            connection.commit()

    @contextmanager
    def _connect(self, *, read_only: bool = False) -> Iterator[sqlite3.Connection]:
        target = validate_runtime_artifact_path(
            self.path, allowed_root=self.allowed_root, repo_root=self.repo_root
        )
        connection = _open(target, read_only=read_only)
        try:
            yield connection
        finally:
            connection.close()

    def _initialize(self) -> None:
        with _open(self.path, read_only=False) as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "CREATE TABLE IF NOT EXISTS metadata(schema_version TEXT NOT NULL, "
                "store_id TEXT NOT NULL, durability_receipt_id TEXT NOT NULL, "
                "binding_digest TEXT NOT NULL)"
            )
            connection.execute(
                "CREATE TABLE IF NOT EXISTS snapshots(snapshot_id TEXT PRIMARY KEY, "
                "sequence INTEGER UNIQUE NOT NULL, payload_json TEXT NOT NULL, "
                "status TEXT NOT NULL CHECK(status IN ('PREPARED','COMMITTED')))"
            )
            connection.execute(
                "CREATE TABLE IF NOT EXISTS state(singleton INTEGER PRIMARY KEY "
                "CHECK(singleton=1), current_snapshot_id TEXT, pending_snapshot_id TEXT)"
            )
            expected = _metadata(self.binding)
            rows = connection.execute("SELECT * FROM metadata").fetchall()
            if not rows:
                connection.execute("INSERT INTO metadata VALUES (?,?,?,?)", expected)
                connection.execute("INSERT INTO state VALUES (1,NULL,NULL)")
            elif rows != [expected]:
                connection.rollback()
                raise ValueError("revocation_store_identity_mismatch")
            connection.commit()


__all__ = [
    "RevocationAuthorityStoreState", "SignerGrantRevocationAuthorityStore",
]
