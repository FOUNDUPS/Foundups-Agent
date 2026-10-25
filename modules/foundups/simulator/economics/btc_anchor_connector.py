"""Content-bound, process-local mock BTC anchoring; no real publisher is implemented.

The SQLite fence below covers pure mock work only, not future external I/O or
broadcast recovery. Legacy rows remain visible and unclassified. Replay identity
proves neither source authenticity, Merkle entitlement nor financial settlement.
"""
from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from enum import Enum
from pathlib import Path
from threading import RLock
from typing import Any, Dict, List, Optional
import hashlib
import json
import math
import os
import sqlite3
import time

LAYER_D_ENABLED = os.getenv("LAYER_D_ENABLED", "0") == "1"
DEFAULT_ANCHOR_DB = Path("modules/foundups/simulator/memory/anchor_state.db")
FORMAT_VERSION = "foundups.epoch.v2"
MOCK_REALM = "bitcoin:mock:v1"
MAX_SQL_INT = 2**63 - 1
FIELDS = frozenset(("format_version", "status", "wsp_78_layer", "requires", "foundup_id",
    "epoch", "anchor_hex", "merkle_root", "entry_hash", "total_distributed",
    "participant_count", "timestamp"))
IDENTITY_COLUMNS = ("format_version", "anchor_realm", "commitment_digest", "commitment_json")


class AnchorMode(Enum):
    MOCK = "mock"
    TESTNET = "testnet"
    MAINNET = "mainnet"


class AnchorStatus(Enum):
    PENDING = "pending"
    PUBLISHED = "published"
    CONFIRMED = "confirmed"
    FAILED = "failed"


def _now():
    return datetime.now(timezone.utc).isoformat()


def _text(value):
    return type(value) is str and bool(value.strip())


def _integer(value, maximum=None):
    return type(value) is int and value >= 0 and (maximum is None or value <= maximum)


def _hex(value, size):
    return type(value) is str and len(value) == size and all(c in "0123456789abcdef" for c in value)


def _utc(value):
    if not _text(value):
        return False
    try:
        parsed = datetime.fromisoformat(value)
        return parsed.tzinfo is not None and parsed.utcoffset() == timedelta(0)
    except ValueError:
        return False


def _payload(value):
    if type(value) is not dict:
        raise ValueError("commitment must be a dictionary")
    value = dict(value)
    if any(type(key) is not str for key in value):
        raise ValueError("commitment field names must be built-in strings")
    if type(value.get("status")) is not str or value["status"] != "pre_settlement":
        raise ValueError("expected pre_settlement status")
    if not _hex(value.get("anchor_hex"), 40):
        raise ValueError("invalid anchor_hex")
    if (set(value) != FIELDS or type(value.get("format_version")) is not str
            or value["format_version"] != FORMAT_VERSION):
        raise ValueError("expected complete known v2 commitment fields")
    if (type(value["wsp_78_layer"]) is not str or value["wsp_78_layer"] != "D_pending"
            or type(value["requires"]) is not str or value["requires"] != "external_btc_anchor_connector"
            or not _text(value["foundup_id"]) or not _integer(value["epoch"], MAX_SQL_INT)
            or not _integer(value["participant_count"]) or not _utc(value["timestamp"])):
        raise ValueError("invalid commitment identity, pending labels or UTC timestamp")
    if not all(_hex(value[key], 64) for key in ("merkle_root", "entry_hash")):
        raise ValueError("invalid commitment hash")
    amount = value["total_distributed"]
    if type(amount) not in (int, float) or (type(amount) is float and not math.isfinite(amount)) or amount < 0:
        raise ValueError("invalid commitment amount")
    value["total_distributed"] = int(amount) if type(amount) is float and amount.is_integer() else amount
    return value


def _binding(value):
    payload = _payload(value)
    canonical = json.dumps({"anchor_realm": MOCK_REALM, "commitment": payload},
        sort_keys=True, separators=(",", ":"), allow_nan=False)
    return payload, canonical, hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass
class AnchorRecord:
    foundup_id: str
    epoch: int
    anchor_hex: str
    merkle_root: str
    entry_hash: str
    status: str
    tx_ref: Optional[str] = None
    confirmations: int = 0
    published_at: Optional[str] = None
    confirmed_at: Optional[str] = None
    created_at: str = ""
    format_version: Optional[str] = None
    anchor_realm: Optional[str] = None
    commitment_digest: Optional[str] = None
    commitment_json: Optional[str] = None

    def __post_init__(self):
        if not self.created_at:
            self.created_at = _now()


def _valid_record(record):
    try:
        stored = json.loads(record.commitment_json)
        if type(stored) is not dict or set(stored) != {"anchor_realm", "commitment"}:
            return False
        payload, canonical, digest = _binding(stored["commitment"])
        return (stored["anchor_realm"] == record.anchor_realm == MOCK_REALM
            and record.format_version == FORMAT_VERSION and record.commitment_json == canonical
            and record.commitment_digest == digest and all(getattr(record, key) == payload[key]
                for key in ("foundup_id", "epoch", "anchor_hex", "merkle_root", "entry_hash")))
    except (ValueError, TypeError, OverflowError):
        return False


def _mock_ref(record):
    return hashlib.sha256((MOCK_REALM + ":" + record.commitment_digest).encode("utf-8")).hexdigest()


def _published(record):
    return (_valid_record(record) and record.status in ("published", "confirmed")
        and record.tx_ref == _mock_ref(record) and _utc(record.published_at)
        and _integer(record.confirmations, MAX_SQL_INT)
        and (record.confirmed_at is None if record.status == "published"
             else record.confirmations > 0 and _utc(record.confirmed_at)))


def _failure(reason, **context):
    return {"success": False, "error": reason, "idempotent_hit": False, "mode": "mock", **context}


def _load(conn, foundup_id, epoch):
    row = conn.execute("SELECT * FROM anchor_records WHERE foundup_id=? AND epoch=?",
        (foundup_id, epoch)).fetchone()
    if row is None:
        return None
    return AnchorRecord(**{key: row[key] for key in AnchorRecord.__dataclass_fields__})


def _insert(conn, record):
    values = asdict(record)
    columns = ",".join(values)
    marks = ",".join("?" for _ in values)
    conn.execute(f"INSERT INTO anchor_records ({columns}) VALUES ({marks})", tuple(values.values()))


def _enable_wal(conn):
    """Journal-mode changes can report BUSY without honoring busy_timeout."""
    deadline = time.monotonic() + 5
    while True:
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            return
        except sqlite3.OperationalError as exc:
            if getattr(exc, "sqlite_errorcode", None) not in (sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED) or time.monotonic() >= deadline:
                raise
            time.sleep(0.01)


def _validate_schema(conn):
    """Accept the owned legacy/current shape, never silently repair constraints."""
    columns = {row["name"]: row for row in conn.execute("PRAGMA table_info(anchor_records)")}
    integers = {"id", "epoch", "confirmations"}
    required = {"id", "foundup_id", "epoch", "anchor_hex", "merkle_root", "entry_hash",
        "status", "tx_ref", "confirmations", "published_at", "confirmed_at", "created_at"}
    if not required.issubset(columns) or any(
            columns[key]["type"].upper() != ("INTEGER" if key in integers else "TEXT")
            for key in required | (set(IDENTITY_COLUMNS) & columns.keys())):
        raise ValueError("unsupported anchor schema columns or declared types")
    if columns["id"]["pk"] != 1 or any(not columns[key]["notnull"] for key in
            ("foundup_id", "epoch", "anchor_hex", "merkle_root", "entry_hash", "status", "created_at")):
        raise ValueError("unsupported anchor schema primary key or nullability")
    for index in conn.execute("PRAGMA index_list(anchor_records)"):
        if index["unique"] and not index["partial"]:
            names = tuple(row["name"] for row in conn.execute(
                "SELECT name FROM pragma_index_info(?) ORDER BY seqno", (index["name"],)))
            if names == ("foundup_id", "epoch"):
                return
    raise ValueError("unsupported anchor schema: exact FoundUp/epoch uniqueness required")


class BTCAnchorConnector:
    """One fixed mock realm and DB; neither a signer nor a real confirmation source."""

    def __init__(self, mode: AnchorMode = AnchorMode.MOCK, db_path: Optional[Path] = None,
                 btc_rpc_url: Optional[str] = None) -> None:
        if type(mode) is not AnchorMode or mode is not AnchorMode.MOCK:
            raise ValueError("Only explicit mock anchoring is implemented; non-mock selection is unsupported")
        if type(db_path) is str and not db_path.strip():
            raise ValueError("anchor database path must not be empty")
        self._mode = mode
        self._db_path = Path(DEFAULT_ANCHOR_DB if db_path is None else db_path).resolve()
        self.btc_rpc_url = btc_rpc_url  # Retained constructor input; never used by mock work.
        self._stats_lock = RLock()
        self._stats = dict(total_published=0, total_confirmed=0, total_failed=0, replay_guards_triggered=0)
        self._init_db()

    @property
    def mode(self):
        return self._mode

    @property
    def db_path(self):
        return self._db_path

    @property
    def anchor_realm(self):
        return MOCK_REALM

    def _connect(self):
        conn = sqlite3.connect(str(self.db_path), timeout=5)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout=5000")
        return conn

    def _init_db(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as conn:
            _enable_wal(conn)
            with conn:
                conn.execute("BEGIN IMMEDIATE")
                conn.execute("""CREATE TABLE IF NOT EXISTS anchor_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, foundup_id TEXT NOT NULL,
                    epoch INTEGER NOT NULL, anchor_hex TEXT NOT NULL, merkle_root TEXT NOT NULL,
                    entry_hash TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending', tx_ref TEXT,
                    confirmations INTEGER DEFAULT 0, published_at TEXT, confirmed_at TEXT,
                    created_at TEXT NOT NULL, UNIQUE(foundup_id,epoch))""")
                _validate_schema(conn)
                columns = {row["name"] for row in conn.execute("PRAGMA table_info(anchor_records)")}
                for column in IDENTITY_COLUMNS:
                    if column not in columns:
                        conn.execute(f"ALTER TABLE anchor_records ADD COLUMN {column} TEXT")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_anchor_foundup_epoch ON anchor_records(foundup_id,epoch)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_anchor_status ON anchor_records(status)")

    def publish_commitment(self, commitment: Dict[str, Any], force: bool = False) -> Dict[str, Any]:
        """Admit an immutable v2 identity; exact force reruns only pure mock work."""
        try:
            if type(force) is not bool:
                raise ValueError("force must be a boolean")
            payload, canonical, digest = _binding(commitment)
            with closing(self._connect()) as conn:
                with conn:
                    conn.execute("BEGIN IMMEDIATE")
                    result, counter = self._publish_locked(conn, payload, canonical, digest, force)
            if counter:
                with self._stats_lock:
                    self._stats[counter] += 1
            return result
        except (ValueError, TypeError, OverflowError, sqlite3.Error) as exc:
            return _failure("anchor admission rejected: " + str(exc))

    def _publish_locked(self, conn, payload, canonical, digest, force):
        record = _load(conn, payload["foundup_id"], payload["epoch"])
        context = dict(foundup_id=payload["foundup_id"], epoch=payload["epoch"])
        if record is not None:
            if not _published(record) or record.commitment_digest != digest or record.commitment_json != canonical:
                return _failure("conflicting, unclassified or unresolved anchor record", **context), None
            if not force:
                return self._receipt(record, True), "replay_guards_triggered"
            result = self._mock_publish(record)
            if result.get("success") is not True or result.get("tx_ref") != record.tx_ref or result.get("mode") != "mock":
                return _failure("invalid mock publication result", **context), None
            return self._receipt(record, False), "total_published"
        record = AnchorRecord(**{key: payload[key] for key in
            ("foundup_id", "epoch", "anchor_hex", "merkle_root", "entry_hash")}, status="pending",
            format_version=FORMAT_VERSION, anchor_realm=MOCK_REALM,
            commitment_json=canonical, commitment_digest=digest)
        result = self._mock_publish(record)
        valid = result.get("success") is True and result.get("tx_ref") == _mock_ref(record) and result.get("mode") == "mock"
        record.status = "published" if valid else "failed"
        if valid:
            record.tx_ref, record.published_at = result["tx_ref"], _now()
        _insert(conn, record)
        if not valid:
            return _failure("mock publication failed", **context), "total_failed"
        return self._receipt(record, False), "total_published"

    def _receipt(self, record, hit):
        return dict(success=True, tx_ref=record.tx_ref, status=record.status, idempotent_hit=hit,
            foundup_id=record.foundup_id, epoch=record.epoch, confirmations=record.confirmations,
            mode="mock", message="Mock transaction - no real BTC published",
            format_version=record.format_version, anchor_realm=record.anchor_realm,
            commitment_digest=record.commitment_digest)

    def _mock_publish(self, record):
        """Pure deterministic simulation; no node, wallet, RPC or signer call."""
        return dict(success=True, tx_ref=_mock_ref(record), mode="mock")

    def check_confirmation(self, foundup_id: str, epoch: int, min_confirmations: int = 6) -> Dict[str, Any]:
        """Advance bound mock receipts only; never attest real chain finality."""
        context = dict(foundup_id=foundup_id, epoch=epoch, confirmed=False, mode="mock")
        if (not _text(foundup_id) or not _integer(epoch, MAX_SQL_INT)
                or not _integer(min_confirmations, MAX_SQL_INT) or min_confirmations == 0):
            return dict(context, found=False, error="invalid confirmation identity or threshold")
        try:
            with closing(self._connect()) as conn:
                with conn:
                    conn.execute("BEGIN IMMEDIATE")
                    record = _load(conn, foundup_id, epoch)
                    if record is None:
                        return dict(context, found=False)
                    if not _published(record) or record.confirmations == MAX_SQL_INT:
                        return dict(context, found=True, status=record.status, error="record is not a bound published mock receipt")
                    was_confirmed = record.status == "confirmed"
                    record.confirmations += 1
                    confirmed = record.confirmations >= min_confirmations
                    if confirmed and not was_confirmed:
                        record.status, record.confirmed_at = "confirmed", _now()
                    self._confirm_locked(conn, record)
            if confirmed and not was_confirmed:
                with self._stats_lock:
                    self._stats["total_confirmed"] += 1
            return dict(context, found=True, status=record.status, confirmed=confirmed,
                confirmations=record.confirmations, min_required=min_confirmations, tx_ref=record.tx_ref)
        except (ValueError, TypeError, OverflowError, sqlite3.Error) as exc:
            return dict(context, found=False, error="confirmation rejected: " + str(exc))

    def _confirm_locked(self, conn, record):
        updated = conn.execute("""UPDATE anchor_records SET status=?,confirmations=?,confirmed_at=?
            WHERE foundup_id=? AND epoch=? AND commitment_digest=? AND anchor_realm=? AND format_version=? AND tx_ref=?""",
            (record.status, record.confirmations, record.confirmed_at, record.foundup_id,
             record.epoch, record.commitment_digest, record.anchor_realm, record.format_version, record.tx_ref))
        if updated.rowcount != 1:
            raise ValueError("anchor identity changed during confirmation")

    def get_anchor_status(self, foundup_id: str, epoch: Optional[int] = None) -> List[Dict[str, Any]]:
        with closing(self._connect()) as conn:
            query, args = "SELECT * FROM anchor_records WHERE foundup_id=?", [foundup_id]
            if epoch is not None:
                query, args = query + " AND epoch=?", args + [epoch]
            rows = [dict(row) for row in conn.execute(query + " ORDER BY epoch", args)]
        for row in rows:
            record = AnchorRecord(**{key: row[key] for key in AnchorRecord.__dataclass_fields__})
            row["identity_status"] = ("legacy_unclassified" if any(row[key] is None for key in IDENTITY_COLUMNS)
                else "current" if _valid_record(record) else "invalid")
        return rows

    def get_stats(self) -> Dict[str, Any]:
        with self._stats_lock:
            return dict(mode="mock", anchor_realm=MOCK_REALM, layer_d_enabled=LAYER_D_ENABLED,
                real_publishing_implemented=False, **self._stats)


_connector_instance: Optional[BTCAnchorConnector] = None
_connector_lock = RLock()


def get_anchor_connector(mode: Optional[AnchorMode] = None, db_path: Optional[Path] = None) -> BTCAnchorConnector:
    global _connector_instance
    if mode is not None and (type(mode) is not AnchorMode or mode is not AnchorMode.MOCK):
        raise ValueError("Only mock anchoring is implemented")
    if type(db_path) is str and not db_path.strip():
        raise ValueError("anchor database path must not be empty")
    selected_path = Path(db_path).resolve() if db_path is not None else None
    with _connector_lock:
        if _connector_instance is None:
            _connector_instance = BTCAnchorConnector(mode=AnchorMode.MOCK, db_path=selected_path)
        elif selected_path is not None and selected_path != _connector_instance.db_path:
            raise ValueError("explicit anchor database path conflicts with existing singleton")
        return _connector_instance


def reset_anchor_connector() -> None:
    global _connector_instance
    with _connector_lock:
        _connector_instance = None


__all__ = ["AnchorMode", "AnchorStatus", "AnchorRecord", "BTCAnchorConnector",
    "get_anchor_connector", "reset_anchor_connector", "LAYER_D_ENABLED"]
