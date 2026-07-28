"""Atomic one-use execution admission for signed AgentDB worker tasks."""

from __future__ import annotations

import hashlib
import json
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Mapping


CLAIM_SCHEMA = "reddog_signed_worker_execution_claim.v1"
USE_SCHEMA = "reddog_signed_worker_execution_use.v1"


@dataclass(frozen=True)
class SignedWorkerExecutionAdmission:
    """Receipts produced by the single winning execution CAS."""

    claim_receipt: Mapping[str, Any]
    use_receipt: Mapping[str, Any]


def admit_signed_worker_execution_once(
    *,
    db: Any,
    task_id: str,
    token_factory: Callable[[], str] | None = None,
    now_factory: Callable[[], datetime] | None = None,
) -> SignedWorkerExecutionAdmission | None:
    """Atomically consume one process-local token and enter executing state."""

    token = (token_factory or (lambda: secrets.token_urlsafe(32)))()
    if not task_id or not token:
        return None
    now = (now_factory or (lambda: datetime.now(timezone.utc)))()
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    return _commit_execution_admission(
        db=db,
        task_id=task_id,
        token=token,
        now_iso=now.astimezone(timezone.utc).isoformat(),
    )


def _commit_execution_admission(
    *,
    db: Any,
    task_id: str,
    token: str,
    now_iso: str,
) -> SignedWorkerExecutionAdmission | None:
    """Commit the one winning assigned-to-executing transition."""

    try:
        with db.db.get_connection() as conn:
            row = conn.execute(
                """
                SELECT status, assigned_to, context
                FROM agents_autonomous_tasks
                WHERE task_id = ?
                """,
                (task_id,),
            ).fetchone()
            inputs = _claim_inputs(row, task_id=task_id, token=token, now_iso=now_iso)
            if inputs is None:
                return None
            raw_context, assigned_to, context, claim_receipt, use_receipt = inputs
            updated_context = dict(context)
            updated_context["signed_worker_execution_claim"] = claim_receipt
            updated_context["signed_worker_execution_use"] = use_receipt
            changed = conn.execute(
                """
                UPDATE agents_autonomous_tasks
                SET status = 'executing', context = ?
                WHERE task_id = ? AND status = 'assigned'
                  AND assigned_to = ? AND context = ?
                """,
                (
                    _canonical_json(updated_context),
                    task_id,
                    assigned_to,
                    raw_context,
                ),
            ).rowcount
            if changed != 1:
                return None
    except Exception:
        return None
    return SignedWorkerExecutionAdmission(
        claim_receipt=claim_receipt,
        use_receipt=use_receipt,
    )


def bind_execution_admission(
    context: Mapping[str, Any],
    admission: SignedWorkerExecutionAdmission,
) -> Mapping[str, Any]:
    """Attach DB-authenticated execution receipts to verified task context."""

    bound = dict(context)
    bound["signed_worker_execution_claim"] = dict(admission.claim_receipt)
    bound["signed_worker_execution_use"] = dict(admission.use_receipt)
    return bound


def admit_verified_signed_worker_context(
    *,
    db: Any,
    task_id: str,
    verified_context: Mapping[str, Any],
) -> Mapping[str, Any] | None:
    """CAS-admit and bind one verified signed-worker context."""

    admission = admit_signed_worker_execution_once(db=db, task_id=task_id)
    if admission is None:
        return None
    return bind_execution_admission(verified_context, admission)


def _claim_inputs(
    row: Any,
    *,
    task_id: str,
    token: str,
    now_iso: str,
) -> tuple[str, str, Mapping[str, Any], Mapping[str, Any], Mapping[str, Any]] | None:
    if row is None:
        return None
    payload = dict(row)
    assigned_to = str(payload.get("assigned_to") or "").strip()
    raw_context = str(payload.get("context") or "")
    if payload.get("status") != "assigned" or not assigned_to or not raw_context:
        return None
    try:
        context = json.loads(raw_context)
    except (TypeError, ValueError):
        return None
    if not isinstance(context, Mapping) or "signed_worker_agentdb_envelope" not in context:
        return None
    token_digest = _digest_text(token)
    claim = _receipt(
        {
            "schema_version": CLAIM_SCHEMA,
            "task_id": task_id,
            "assigned_to": assigned_to,
            "context_digest": _digest(context),
            "token_digest": token_digest,
            "claimed_at": now_iso,
            "status": "CLAIMED",
        }
    )
    use = _receipt(
        {
            "schema_version": USE_SCHEMA,
            "task_id": task_id,
            "claim_receipt_id": claim["receipt_id"],
            "token_digest": token_digest,
            "consumed_at": now_iso,
            "status": "CONSUMED",
        }
    )
    return raw_context, assigned_to, context, claim, use


def _receipt(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    receipt = dict(payload)
    receipt["receipt_id"] = _digest(payload)
    return receipt


def _digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _digest_text(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )


__all__ = [
    "CLAIM_SCHEMA",
    "USE_SCHEMA",
    "SignedWorkerExecutionAdmission",
    "admit_signed_worker_execution_once",
    "admit_verified_signed_worker_context",
    "bind_execution_admission",
]
