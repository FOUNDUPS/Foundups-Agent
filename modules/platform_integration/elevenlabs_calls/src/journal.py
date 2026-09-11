"""Local, transactional external-effect duplicate guard; never store message text."""
import json
import os
from contextlib import contextmanager
from pathlib import Path
import sqlite3


class CallJournal:
    def __init__(self, path: str | Path):
        self.path = Path(path).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(self.path, os.O_CREAT | os.O_WRONLY, 0o600)
        os.close(fd)
        with self.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS calls (request_id TEXT PRIMARY KEY, "
                       "fingerprint TEXT NOT NULL, receipt TEXT NOT NULL)")

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        try:
            with db:
                yield db
        finally:
            db.close()

    def reserve(self, request_id: str, fingerprint: str) -> tuple[bool, dict]:
        """Only the winning INSERT may dial. A crash leaves an uncertain reservation."""
        pending = {"request_id": request_id, "status": "submission_unknown",
                   "delivery": "unconfirmed", "conversation_id": None, "call_sid": None}
        with self.connect() as db:
            cursor = db.execute("INSERT OR IGNORE INTO calls VALUES (?, ?, ?)",
                                (request_id, fingerprint, json.dumps(pending)))
            row = db.execute("SELECT fingerprint, receipt FROM calls WHERE request_id=?",
                             (request_id,)).fetchone()
        if row[0] != fingerprint:
            raise ValueError("request_id was already used for different content or configuration")
        return cursor.rowcount == 1, json.loads(row[1])

    def get(self, request_id: str) -> dict:
        with self.connect() as db:
            row = db.execute("SELECT receipt FROM calls WHERE request_id=?", (request_id,)).fetchone()
        if row is None:
            raise ValueError("Unknown request_id in this journal")
        return json.loads(row[0])

    def save(self, receipt: dict) -> None:
        with self.connect() as db:
            db.execute("UPDATE calls SET receipt=? WHERE request_id=?",
                       (json.dumps(receipt), receipt["request_id"]))
