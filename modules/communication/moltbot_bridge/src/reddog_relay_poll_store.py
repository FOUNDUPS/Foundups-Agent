"""Private, single-host relay checkpoints using the existing ModuleDB owner.

No payloads, credentials or provider clients are stored. The caller holds the
shared runtime-operation lock while using this store. This is not a transport.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
from contextlib import contextmanager
from pathlib import Path

from modules.infrastructure.database.src.module_db import ModuleDB
from modules.infrastructure.shared_utilities.delay_utils import DelayUtils
from modules.infrastructure.shared_utilities.runtime_artifact_safety import validate_runtime_artifact_path


def digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=True).encode()).hexdigest()


def timestamp(value) -> float:
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        raise ValueError("relay_time_invalid")
    return float(value)


class RelayPollStore(ModuleDB):
    """Module-owned tables in an explicitly supplied durable SQLite manager."""

    def __init__(self, db, *, repo_root: Path, allowed_root: Path):
        info = db.backend_info()
        path = Path(info.get("db_path", ""))
        if (info.get("engine") != "sqlite" or not path.is_absolute()
                or not path.is_file() or path.is_symlink() or path.anchor.startswith("\\\\")):
            raise ValueError("relay_requires_explicit_local_sqlite_file")
        if os.name == "nt":
            import ctypes
            drive_type = ctypes.windll.kernel32.GetDriveTypeW
            drive_type.argtypes = [ctypes.c_wchar_p]
            drive_type.restype = ctypes.c_uint
            if drive_type(path.anchor) != 3:  # fixed local disk; never a mapped network share
                raise ValueError("relay_requires_fixed_local_disk")
        validate_runtime_artifact_path(path, repo_root=repo_root, allowed_root=allowed_root)
        self.db = db
        self.module_name = "reddog_relay"
        self.table_prefix = "modules_reddog_relay_"
        self.db_identity = str(path.resolve(strict=True))
        st = path.stat()
        self.file_identity = (st.st_dev, st.st_ino)
        self.verify_database_identity()
        self._init_tables()
        self.verify_database_identity()

    def verify_database_identity(self):
        info = self.db.backend_info()
        path = Path(info.get("db_path", ""))
        if (info.get("engine") != "sqlite" or not path.is_absolute()
                or path.is_symlink() or str(path.resolve(strict=True)) != self.db_identity):
            raise ValueError("relay_database_binding_changed")
        st = path.stat()
        if st.st_nlink != 1 or (st.st_dev, st.st_ino) != self.file_identity:
            raise ValueError("relay_database_identity_changed_or_linked")

    @contextmanager
    def _connection(self):
        self.verify_database_identity()
        with self.db.get_connection() as conn:
            self.verify_database_identity()
            yield conn
            self.verify_database_identity()

    def _read(self, sql, params):
        with self._connection() as conn:
            return conn.execute(sql, params).fetchall()

    def _write(self, sql, params):
        with self._connection() as conn:
            return conn.execute(sql, params).rowcount

    def _init_tables(self):
        self.create_table("checkpoints", """
            source_key TEXT PRIMARY KEY, binding TEXT NOT NULL,
            watermark TEXT NOT NULL, delay INTEGER NOT NULL,
            next_due REAL NOT NULL, observed_at REAL, last_attempt_at REAL NOT NULL,
            owner TEXT NOT NULL, generation INTEGER NOT NULL,
            last_error TEXT NOT NULL
        """)
        self.create_table("messages", """
            source_key TEXT NOT NULL, message_id TEXT NOT NULL,
            content_digest TEXT NOT NULL, observed_at REAL NOT NULL,
            PRIMARY KEY (source_key, message_id)
        """)
        self.create_table("operations", """
            operation_id TEXT PRIMARY KEY, source_key TEXT NOT NULL,
            message_id TEXT NOT NULL, phase TEXT NOT NULL,
            state TEXT NOT NULL, proof_id TEXT NOT NULL, attempt INTEGER NOT NULL,
            UNIQUE(source_key, message_id, phase)
        """)
        self.create_table("proofs", """
            operation_id TEXT NOT NULL, proof_id TEXT NOT NULL,
            outcome TEXT NOT NULL, observed_at REAL NOT NULL, attempt INTEGER NOT NULL,
            PRIMARY KEY(operation_id, attempt, proof_id)
        """)

    def initialize(self, key, binding, now):
        now = timestamp(now)
        encoded = json.dumps(binding, sort_keys=True, separators=(",", ":"))
        with self._connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute("""INSERT INTO modules_reddog_relay_checkpoints
                VALUES (?, ?, '', 60, ?, NULL, ?, '', 0, '')
                ON CONFLICT(source_key) DO NOTHING""", (key, encoded, now + 60, now))
            row = conn.execute("SELECT * FROM modules_reddog_relay_checkpoints WHERE source_key=?", (key,)).fetchone()
            if row["binding"] != encoded:
                raise ValueError("relay_source_binding_changed")
        return self.checkpoint(key)

    def checkpoint(self, key):
        rows = self._read("SELECT * FROM modules_reddog_relay_checkpoints WHERE source_key=?", (key,))
        if len(rows) != 1:
            raise ValueError("relay_checkpoint_missing")
        row = rows[0]
        DelayUtils.calculate_activity_poll_delay(row["delay"])
        timestamp(row["next_due"])
        if row["observed_at"] is not None:
            timestamp(row["observed_at"])
        timestamp(row["last_attempt_at"])
        return row

    def claim_local_owner(self, key, owner):
        # The process lock is the live lease; this generation is durable history
        # of ownership, not permission or evidence of a still-running worker.
        self._write("""UPDATE modules_reddog_relay_checkpoints
            SET owner=?, generation=generation+1 WHERE source_key=?""", (owner, key))

    def ingest(self, key, watermark, messages, now):
        """Commit all accepted IDs, operations, watermark and schedule together."""
        now = timestamp(now)
        with self._connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            state = conn.execute("SELECT * FROM modules_reddog_relay_checkpoints WHERE source_key=?", (key,)).fetchone()
            if now < state["last_attempt_at"]:
                raise ValueError("relay_clock_moved_backwards")
            activity = False
            for message in messages:
                existing = conn.execute("""SELECT content_digest FROM modules_reddog_relay_messages
                    WHERE source_key=? AND message_id=?""", (key, message.message_id)).fetchone()
                if existing:
                    if existing["content_digest"] != message.content_digest:
                        raise ValueError("relay_message_identity_conflict")
                    continue
                count = conn.execute("SELECT COUNT(*) AS n FROM modules_reddog_relay_messages WHERE source_key=?", (key,)).fetchone()["n"]
                if count >= 10000:
                    raise ValueError("relay_ledger_capacity_reached")
                conn.execute("INSERT INTO modules_reddog_relay_messages VALUES (?, ?, ?, ?)",
                             (key, message.message_id, message.content_digest, now))
                for phase in ("ack", "forward"):
                    operation_id = digest([key, state["binding"], message.message_id, message.content_digest, phase])
                    conn.execute("INSERT INTO modules_reddog_relay_operations VALUES (?, ?, ?, ?, 'READY', '', 0)",
                                 (operation_id, key, message.message_id, phase))
                activity = True
            delay = DelayUtils.calculate_activity_poll_delay(state["delay"], activity=activity)
            conn.execute("""UPDATE modules_reddog_relay_checkpoints SET watermark=?,
                delay=?, next_due=?, observed_at=?, last_attempt_at=?, last_error='' WHERE source_key=?""",
                         (watermark, delay, now + delay, now, now, key))
        return activity

    def defer_error(self, key, now, code, retry_after):
        now = timestamp(now)
        state = self.checkpoint(key)
        if now < state["last_attempt_at"]:
            raise ValueError("relay_clock_moved_backwards")
        # A provider error is not an empty read. Keep cursor and idle interval.
        self._write("""UPDATE modules_reddog_relay_checkpoints SET
            next_due=?, last_attempt_at=?, last_error=? WHERE source_key=?""",
                              (now + retry_after, now, code, key))

    def pending(self, key):
        return self._read("""SELECT o.*, m.content_digest FROM
            modules_reddog_relay_operations o JOIN modules_reddog_relay_messages m
            ON o.source_key=m.source_key AND o.message_id=m.message_id
            WHERE o.source_key=? AND o.state!='APPLIED'
            ORDER BY m.observed_at, o.message_id, o.phase""", (key,))

    def operation(self, operation_id):
        return self._read("SELECT * FROM modules_reddog_relay_operations WHERE operation_id=?", (operation_id,))[0]

    def ack_applied(self, key, message_id):
        rows = self._read("""SELECT state FROM modules_reddog_relay_operations
            WHERE source_key=? AND message_id=? AND phase='ack'""", (key, message_id))
        return bool(rows and rows[0]["state"] == "APPLIED")

    def start_operation(self, operation_id):
        with self._connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            cursor = conn.execute("""UPDATE modules_reddog_relay_operations SET
                state='INFLIGHT', proof_id='', attempt=attempt+1 WHERE operation_id=? AND state='READY'""", (operation_id,))
            if cursor.rowcount != 1:
                raise ValueError("relay_operation_not_ready")
            attempt = conn.execute("SELECT attempt FROM modules_reddog_relay_operations WHERE operation_id=?", (operation_id,)).fetchone()["attempt"]
        return attempt

    def record_proof(self, operation_id, attempt, outcome, proof_id, now):
        if outcome not in ("APPLIED", "TERMINAL_NOT_APPLIED"):
            raise ValueError("relay_proof_outcome_invalid")
        with self._connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            old = conn.execute("SELECT * FROM modules_reddog_relay_operations WHERE operation_id=?", (operation_id,)).fetchone()
            if old["state"] == "APPLIED":
                raise ValueError("relay_applied_operation_immutable")
            if old["state"] != "INFLIGHT" or old["attempt"] != attempt:
                raise ValueError("relay_proof_attempt_mismatch")
            known = conn.execute("SELECT outcome FROM modules_reddog_relay_proofs WHERE operation_id=? AND attempt=? AND proof_id=?", (operation_id, attempt, proof_id)).fetchone()
            if known and known["outcome"] != outcome:
                raise ValueError("relay_proof_identity_conflict")
            if not known:
                conn.execute("INSERT INTO modules_reddog_relay_proofs VALUES (?, ?, ?, ?, ?)", (operation_id, proof_id, outcome, timestamp(now), attempt))
            state = "APPLIED" if outcome == "APPLIED" else "READY"
            conn.execute("UPDATE modules_reddog_relay_operations SET state=?, proof_id=? WHERE operation_id=?", (state, proof_id, operation_id))
