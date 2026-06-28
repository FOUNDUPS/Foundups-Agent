"""RedDog governed work-order receipt layer (Hermes-compatible, pre-execution audit).

Slice: REDDOG_HERMES_WORK_ORDER_RECEIPT_PHASE1
Contract: docs/audits/architecture/REDDOG_GOVERNED_REPO_WORK_ORDER_CONTRACT_PHASE1.md

Persists or emits audit receipts from #893 PolicyGateReceipt records.
Pre-execution audit trail only — NOT Hermes queue dispatch, NOT WRE execution.

WSP 97 TRUTH BOUNDARIES:
  ✓ DOES:
    - Map PolicyGateReceipt -> RedDogWorkOrderReceipt (Hermes-compatible shape)
    - Append-only SQLite persistence when caller provides store path
    - Idempotent insert keyed by policy_gate_receipt_digest
    - Preserve digests/refs only (no raw prompts, tokens, or secrets)

  ✗ DOES NOT:
    - Create branches, PRs, commits, merges, or file writes to repos
    - Invoke WRE executor, live gh probe, or extension runtime
    - Dispatch to live Hermes queue
    - Claim execution occurred (no_execution_performed remains true)
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import sqlite3
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Union

from modules.communication.moltbot_bridge.src.reddog_openclaw_work_order_policy_gate import (
    POLICY_ACCEPT,
    POLICY_ACCEPT_WITH_RETRIEVAL_GAP,
    POLICY_REJECT,
    PolicyGateReceipt,
)

logger = logging.getLogger("reddog_work_order_receipt")

RECEIPT_SOURCE = "reddog_openclaw_policy_gate"
DEFAULT_RETENTION_DAYS = 90
SCHEMA_VERSION = 1

_SECRET_PATTERNS = (
    re.compile(r"ghp_[A-Za-z0-9_]+"),
    re.compile(r"github_pat_[A-Za-z0-9_]+"),
    re.compile(r"sk-[A-Za-z0-9_]+"),
    re.compile(r"gho_[A-Za-z0-9_]+"),
)


class ReceiptStoreStatus(str, Enum):
    SUCCESS = "success"
    ALREADY_EXISTS = "already_exists"
    VALIDATION_ERROR = "validation_error"
    SCHEMA_ERROR = "schema_error"
    WRITE_ERROR = "write_error"
    READ_ERROR = "read_error"


@dataclass
class RedDogWorkOrderReceipt:
    """Hermes-compatible pre-execution audit receipt for governed work orders."""

    receipt_id: str
    work_order_id: str
    policy_gate_decision: str
    policy_gate_receipt_digest: str
    dry_run_receipt_digest: str
    permission_snapshot_digest: str
    holoindex_evidence_digest: str
    permission_truth_label: str
    no_execution_performed: bool
    created_at: str
    expires_at: Optional[str]
    source: str
    retention_days: int
    receipt_digest: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))


@dataclass
class WorkOrderReceiptEmissionResult:
    success: bool
    receipt: Optional[RedDogWorkOrderReceipt]
    persisted: bool
    idempotent_replay: bool
    store_status: Optional[ReceiptStoreStatus] = None
    error: Optional[str] = None


@dataclass
class ReceiptStoreResult:
    status: ReceiptStoreStatus
    message: str
    receipt_id: Optional[str] = None
    receipt: Optional[RedDogWorkOrderReceipt] = None


def _utc_now(now: Optional[datetime] = None) -> datetime:
    value = now or datetime.now(timezone.utc)
    return value.astimezone(timezone.utc)


def _iso8601(dt: datetime) -> str:
    return dt.replace(microsecond=0).isoformat()


def _canonical_digest(payload: Mapping[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _sanitize_text(text: str) -> str:
    cleaned = text
    for pattern in _SECRET_PATTERNS:
        cleaned = pattern.sub("[REDACTED]", cleaned)
    return cleaned


def _sanitize_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    sanitized: Dict[str, Any] = {}
    for key, value in data.items():
        if isinstance(value, str):
            sanitized[key] = _sanitize_text(value)
        elif isinstance(value, list):
            sanitized[key] = [_sanitize_text(v) if isinstance(v, str) else v for v in value]
        else:
            sanitized[key] = value
    return sanitized


def build_reddog_work_order_receipt(
    policy_receipt: PolicyGateReceipt,
    *,
    now: Optional[datetime] = None,
    retention_days: int = DEFAULT_RETENTION_DAYS,
) -> RedDogWorkOrderReceipt:
    """Map a PolicyGateReceipt into a Hermes-compatible RedDogWorkOrderReceipt."""
    if not policy_receipt.no_execution_performed:
        raise ValueError("policy receipt must have no_execution_performed=true")

    created = _utc_now(now)
    retention = max(1, retention_days)
    retention_expires = created + timedelta(days=retention)

    expires_at = policy_receipt.expires_at
    if expires_at:
        try:
            policy_exp = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            if policy_exp.tzinfo is None:
                policy_exp = policy_exp.replace(tzinfo=timezone.utc)
            retention_expires = min(retention_expires, policy_exp.astimezone(timezone.utc))
        except ValueError:
            pass

    receipt_core = {
        "receipt_id": f"rdog-rcpt-{policy_receipt.work_order_id}-{policy_receipt.receipt_digest[:12]}",
        "work_order_id": policy_receipt.work_order_id,
        "policy_gate_decision": policy_receipt.decision,
        "policy_gate_receipt_digest": policy_receipt.receipt_digest,
        "dry_run_receipt_digest": policy_receipt.dry_run_receipt_digest,
        "permission_snapshot_digest": policy_receipt.permission_snapshot_digest,
        "holoindex_evidence_digest": policy_receipt.holoindex_evidence_digest,
        "permission_truth_label": policy_receipt.permission_truth_label,
        "no_execution_performed": True,
        "created_at": _iso8601(created),
        "expires_at": _iso8601(retention_expires),
        "source": RECEIPT_SOURCE,
        "retention_days": retention,
    }
    digest = _canonical_digest(receipt_core)
    return RedDogWorkOrderReceipt(receipt_digest=digest, **receipt_core)


_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS reddog_work_order_receipts (
    receipt_id TEXT PRIMARY KEY,
    work_order_id TEXT NOT NULL,
    policy_gate_receipt_digest TEXT NOT NULL UNIQUE,
    receipt_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT,
    source TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_rdog_receipt_work_order
    ON reddog_work_order_receipts(work_order_id);
CREATE INDEX IF NOT EXISTS idx_rdog_receipt_created
    ON reddog_work_order_receipts(created_at);
CREATE TABLE IF NOT EXISTS reddog_receipt_schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL
);
"""


class RedDogWorkOrderReceiptStore:
    """Append-only SQLite audit store for RedDogWorkOrderReceipt records."""

    def __init__(self, db_path: Union[str, Path]) -> None:
        self.db_path = Path(db_path)
        self._conn: Optional[sqlite3.Connection] = None
        self._schema_initialized = False

    def _get_connection(self) -> sqlite3.Connection:
        if self._conn is None:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(str(self.db_path))
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
        return self._conn

    def initialize_schema(self) -> ReceiptStoreResult:
        try:
            conn = self._get_connection()
            conn.executescript(_CREATE_TABLE_SQL)
            conn.execute(
                "INSERT OR IGNORE INTO reddog_receipt_schema_version (version, applied_at) VALUES (?, ?)",
                (SCHEMA_VERSION, _iso8601(_utc_now())),
            )
            conn.commit()
            self._schema_initialized = True
            return ReceiptStoreResult(status=ReceiptStoreStatus.SUCCESS, message="schema ready")
        except sqlite3.Error as exc:
            return ReceiptStoreResult(
                status=ReceiptStoreStatus.SCHEMA_ERROR,
                message=f"schema initialization failed: {exc}",
            )

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None
            self._schema_initialized = False

    def __enter__(self) -> "RedDogWorkOrderReceiptStore":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def get_by_policy_digest(self, policy_gate_receipt_digest: str) -> Optional[RedDogWorkOrderReceipt]:
        try:
            conn = self._get_connection()
            row = conn.execute(
                "SELECT receipt_json FROM reddog_work_order_receipts WHERE policy_gate_receipt_digest = ?",
                (policy_gate_receipt_digest,),
            ).fetchone()
            if row is None:
                return None
            payload = json.loads(row["receipt_json"])
            return RedDogWorkOrderReceipt(**payload)
        except (sqlite3.Error, json.JSONDecodeError, TypeError) as exc:
            logger.debug("receipt read failed: %s", _sanitize_text(str(exc)))
            return None

    def insert(self, receipt: RedDogWorkOrderReceipt) -> ReceiptStoreResult:
        if not self._schema_initialized:
            init = self.initialize_schema()
            if init.status != ReceiptStoreStatus.SUCCESS:
                return init

        if not receipt.no_execution_performed:
            return ReceiptStoreResult(
                status=ReceiptStoreStatus.VALIDATION_ERROR,
                message="no_execution_performed must be true",
            )

        existing = self.get_by_policy_digest(receipt.policy_gate_receipt_digest)
        if existing is not None:
            return ReceiptStoreResult(
                status=ReceiptStoreStatus.ALREADY_EXISTS,
                message="receipt already stored for policy_gate_receipt_digest",
                receipt_id=existing.receipt_id,
                receipt=existing,
            )

        safe_json = json.dumps(_sanitize_dict(receipt.to_dict()), sort_keys=True, separators=(",", ":"))
        try:
            conn = self._get_connection()
            conn.execute(
                """
                INSERT INTO reddog_work_order_receipts (
                    receipt_id, work_order_id, policy_gate_receipt_digest,
                    receipt_json, created_at, expires_at, source
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    receipt.receipt_id,
                    receipt.work_order_id,
                    receipt.policy_gate_receipt_digest,
                    safe_json,
                    receipt.created_at,
                    receipt.expires_at,
                    receipt.source,
                ),
            )
            conn.commit()
            return ReceiptStoreResult(
                status=ReceiptStoreStatus.SUCCESS,
                message="receipt stored",
                receipt_id=receipt.receipt_id,
                receipt=receipt,
            )
        except sqlite3.IntegrityError:
            existing = self.get_by_policy_digest(receipt.policy_gate_receipt_digest)
            if existing is not None:
                return ReceiptStoreResult(
                    status=ReceiptStoreStatus.ALREADY_EXISTS,
                    message="receipt already stored (race)",
                    receipt_id=existing.receipt_id,
                    receipt=existing,
                )
            return ReceiptStoreResult(
                status=ReceiptStoreStatus.WRITE_ERROR,
                message="integrity error without readable existing receipt",
            )
        except sqlite3.Error as exc:
            return ReceiptStoreResult(
                status=ReceiptStoreStatus.WRITE_ERROR,
                message=f"write failed: {exc}",
            )


def emit_work_order_receipt(
    policy_receipt: PolicyGateReceipt,
    *,
    store: Optional[RedDogWorkOrderReceiptStore] = None,
    now: Optional[datetime] = None,
    retention_days: int = DEFAULT_RETENTION_DAYS,
) -> WorkOrderReceiptEmissionResult:
    """Emit a RedDogWorkOrderReceipt from a policy gate receipt (optional persist)."""
    try:
        receipt = build_reddog_work_order_receipt(
            policy_receipt,
            now=now,
            retention_days=retention_days,
        )
    except ValueError as exc:
        return WorkOrderReceiptEmissionResult(
            success=False,
            receipt=None,
            persisted=False,
            idempotent_replay=False,
            error=str(exc),
        )

    if store is None:
        return WorkOrderReceiptEmissionResult(
            success=True,
            receipt=receipt,
            persisted=False,
            idempotent_replay=False,
        )

    result = store.insert(receipt)
    if result.status == ReceiptStoreStatus.SUCCESS:
        return WorkOrderReceiptEmissionResult(
            success=True,
            receipt=result.receipt or receipt,
            persisted=True,
            idempotent_replay=False,
            store_status=result.status,
        )
    if result.status == ReceiptStoreStatus.ALREADY_EXISTS:
        return WorkOrderReceiptEmissionResult(
            success=True,
            receipt=result.receipt or receipt,
            persisted=True,
            idempotent_replay=True,
            store_status=result.status,
        )

    return WorkOrderReceiptEmissionResult(
        success=False,
        receipt=receipt,
        persisted=False,
        idempotent_replay=False,
        store_status=result.status,
        error=result.message,
    )


__all__ = [
    "DEFAULT_RETENTION_DAYS",
    "RECEIPT_SOURCE",
    "RedDogWorkOrderReceipt",
    "RedDogWorkOrderReceiptStore",
    "ReceiptStoreResult",
    "ReceiptStoreStatus",
    "WorkOrderReceiptEmissionResult",
    "build_reddog_work_order_receipt",
    "emit_work_order_receipt",
]
