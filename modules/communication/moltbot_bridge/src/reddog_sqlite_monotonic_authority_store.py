"""SQLite-backed monotonic authority for a separately administered principal."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from time import sleep
from typing import Any, Iterator

from modules.communication.moltbot_bridge.src.reddog_proposal_authenticity_nonce_store import (
    ProposalReplayHighWater,
)
from modules.communication.moltbot_bridge.src.reddog_runtime_artifact_manifest_contract import (
    is_sha256,
)
from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    validate_runtime_artifact_path,
    validate_runtime_root_path,
)


class SqliteMonotonicAuthorityStore:
    """CAS high-water store; ownership must belong to the signer principal."""

    def __init__(
        self,
        path: Path | str,
        *,
        allowed_root: Path | str,
        repo_root: Path | str,
        store_id: str,
        durability_receipt_id: str,
    ) -> None:
        root = validate_runtime_root_path(allowed_root, repo_root=repo_root)
        target = validate_runtime_artifact_path(
            path,
            allowed_root=root,
            repo_root=repo_root,
        )
        if target.parent != root:
            raise ValueError("monotonic_authority_path_invalid")
        if (
            not isinstance(store_id, str)
            or not store_id.strip()
            or not store_id.isascii()
            or not is_sha256(durability_receipt_id)
        ):
            raise ValueError("monotonic_authority_identity_invalid")
        root.mkdir(parents=True, exist_ok=True)
        self._path = target
        self._repo_root = Path(repo_root).resolve()
        self._allowed_root = root
        self._store_id = store_id.strip()
        self._durability_receipt_id = durability_receipt_id
        self._initialize()

    @property
    def store_id(self) -> str:
        return self._store_id

    @property
    def durable(self) -> bool:
        return True

    @property
    def durability_receipt_id(self) -> str:
        return self._durability_receipt_id

    @property
    def rollback_domain_root(self) -> Path:
        return self._allowed_root

    def load(self, binding_digest: str) -> ProposalReplayHighWater | None:
        binding = _digest(binding_digest, "binding")
        with self._connect() as connection:
            row = connection.execute(
                "SELECT sequence, state_revision FROM high_water "
                "WHERE binding_digest = ?",
                (binding,),
            ).fetchone()
        if row is None:
            return None
        value = ProposalReplayHighWater(
            sequence=int(row[0]),
            state_revision=str(row[1]),
        )
        _validate_value(value)
        return value

    def advance(
        self,
        binding_digest: str,
        *,
        expected: ProposalReplayHighWater | None,
        next_value: ProposalReplayHighWater,
    ) -> None:
        binding = _digest(binding_digest, "binding")
        _validate_optional(expected)
        _validate_value(next_value)
        expected_sequence = 1 if expected is None else expected.sequence + 1
        if next_value.sequence != expected_sequence:
            raise ValueError("monotonic_authority_not_monotonic")
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            current = _read_current(connection, binding)
            if current != expected:
                connection.rollback()
                raise RuntimeError("monotonic_authority_conflict")
            connection.execute(
                "INSERT INTO high_water(binding_digest, sequence, "
                "state_revision) VALUES (?, ?, ?) "
                "ON CONFLICT(binding_digest) DO UPDATE SET "
                "sequence=excluded.sequence, "
                "state_revision=excluded.state_revision",
                (binding, next_value.sequence, next_value.state_revision),
            )
            connection.commit()
        if self.load(binding) != next_value:
            raise RuntimeError("monotonic_authority_commit_unverified")

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        target = validate_runtime_artifact_path(
            self._path,
            allowed_root=self._allowed_root,
            repo_root=self._repo_root,
        )
        connection = _open_configured_connection(target)
        try:
            yield connection
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                connection.execute(
                    "CREATE TABLE IF NOT EXISTS metadata "
                    "(store_id TEXT PRIMARY KEY, "
                    "durability_receipt_id TEXT NOT NULL)"
                )
                connection.execute(
                    "CREATE TABLE IF NOT EXISTS high_water "
                    "(binding_digest TEXT PRIMARY KEY, sequence INTEGER NOT NULL, "
                    "state_revision TEXT NOT NULL)"
                )
                _initialize_identity(
                    connection,
                    store_id=self._store_id,
                    durability_receipt_id=self._durability_receipt_id,
                )
                connection.commit()
            except Exception:
                connection.rollback()
                raise


def _open_configured_connection(target: Path) -> sqlite3.Connection:
    for attempt in range(5):
        connection = sqlite3.connect(
            target,
            timeout=30.0,
            isolation_level=None,
        )
        try:
            connection.execute("PRAGMA busy_timeout=30000")
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("PRAGMA synchronous=FULL")
            return connection
        except sqlite3.OperationalError as exc:
            connection.close()
            if "locked" not in str(exc).lower() or attempt == 4:
                raise
            sleep(0.05 * (attempt + 1))
    raise RuntimeError("monotonic_authority_connection_unavailable")


def _initialize_identity(
    connection: sqlite3.Connection,
    *,
    store_id: str,
    durability_receipt_id: str,
) -> None:
    rows = connection.execute(
        "SELECT store_id, durability_receipt_id FROM metadata"
    ).fetchall()
    expected = (store_id, durability_receipt_id)
    if not rows:
        connection.execute(
            "INSERT INTO metadata(store_id, durability_receipt_id) "
            "VALUES (?, ?)",
            expected,
        )
    elif rows != [expected]:
        raise ValueError("monotonic_authority_identity_mismatch")


def _read_current(
    connection: sqlite3.Connection,
    binding: str,
) -> ProposalReplayHighWater | None:
    row = connection.execute(
        "SELECT sequence, state_revision FROM high_water "
        "WHERE binding_digest = ?",
        (binding,),
    ).fetchone()
    if row is None:
        return None
    return ProposalReplayHighWater(
        sequence=int(row[0]),
        state_revision=str(row[1]),
    )


def _validate_optional(value: ProposalReplayHighWater | None) -> None:
    if value is not None:
        _validate_value(value)


def _validate_value(value: Any) -> None:
    if (
        not isinstance(value, ProposalReplayHighWater)
        or type(value.sequence) is not int
        or value.sequence < 1
        or not isinstance(value.state_revision, str)
        or len(value.state_revision) != 64
        or any(char not in "0123456789abcdef" for char in value.state_revision)
    ):
        raise ValueError("monotonic_authority_value_invalid")


def _digest(value: Any, name: str) -> str:
    if not is_sha256(value):
        raise ValueError(f"monotonic_authority_{name}_invalid")
    return str(value)


__all__ = ["SqliteMonotonicAuthorityStore"]
