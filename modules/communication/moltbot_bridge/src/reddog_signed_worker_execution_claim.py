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
SIGNED_WORKER_TASK_PREFIX = "reddog-worker-dispatch-"


@dataclass(frozen=True)
class SignedWorkerExecutionAdmission:
    """Receipts produced by the single winning execution CAS."""

    claim_receipt: Mapping[str, Any]
    use_receipt: Mapping[str, Any]
    claimed_context: Mapping[str, Any]
    required_skills: tuple[str, ...]
    discovered_by: str


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
                SELECT status, assigned_to, context, required_skills, discovered_by
                FROM agents_autonomous_tasks
                WHERE task_id = ?
                """,
                (task_id,),
            ).fetchone()
            inputs = _claim_inputs(row, task_id=task_id, token=token, now_iso=now_iso)
            if inputs is None:
                return None
            (
                raw_context,
                raw_skills,
                assigned_to,
                context,
                required_skills,
                discovered_by,
                claim_receipt,
                use_receipt,
            ) = inputs
            updated_context = dict(context)
            updated_context["signed_worker_execution_claim"] = claim_receipt
            updated_context["signed_worker_execution_use"] = use_receipt
            changed = conn.execute(
                """
                UPDATE agents_autonomous_tasks
                SET status = 'executing', context = ?
                WHERE task_id = ? AND status = 'assigned'
                  AND assigned_to = ? AND context = ?
                  AND required_skills = ? AND discovered_by = ?
                """,
                (
                    _canonical_json(updated_context),
                    task_id,
                    assigned_to,
                    raw_context,
                    raw_skills,
                    discovered_by,
                ),
            ).rowcount
            if changed != 1:
                return None
    except Exception:
        return None
    return SignedWorkerExecutionAdmission(
        claim_receipt=claim_receipt,
        use_receipt=use_receipt,
        claimed_context=dict(context),
        required_skills=required_skills,
        discovered_by=discovered_by,
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


_ClaimInputs = tuple[
    str,
    str,
    str,
    Mapping[str, Any],
    tuple[str, ...],
    str,
    Mapping[str, Any],
    Mapping[str, Any],
] | None


def _claim_inputs(
    row: Any, *, task_id: str, token: str, now_iso: str
) -> _ClaimInputs:
    if row is None or not task_id.startswith(SIGNED_WORKER_TASK_PREFIX):
        return None
    parsed = _parse_claim_row(row)
    if parsed is None:
        return None
    raw_context, raw_skills, assigned_to, context, required_skills, discovered_by = parsed
    claim, use = _execution_receipts(
        task_id=task_id,
        assigned_to=assigned_to,
        context=context,
        required_skills=required_skills,
        discovered_by=discovered_by,
        token=token,
        now_iso=now_iso,
    )
    return (
        raw_context, raw_skills, assigned_to, context, required_skills,
        discovered_by, claim, use,
    )


def _parse_claim_row(
    row: Any,
) -> tuple[str, str, str, Mapping[str, Any], tuple[str, ...], str] | None:
    payload = dict(row)
    assigned_to = str(payload.get("assigned_to") or "").strip()
    raw_context = str(payload.get("context") or "")
    raw_skills = str(payload.get("required_skills") or "")
    discovered_by = str(payload.get("discovered_by") or "").strip()
    if (
        payload.get("status") != "assigned"
        or not assigned_to
        or not raw_context
        or not raw_skills
        or not discovered_by
    ):
        return None
    try:
        context = json.loads(raw_context)
        parsed_skills = json.loads(raw_skills)
    except (TypeError, ValueError):
        return None
    if (
        not isinstance(context, Mapping)
        or not isinstance(parsed_skills, list)
        or any(not isinstance(skill, str) or not skill for skill in parsed_skills)
    ):
        return None
    context = dict(context)
    context.pop("signed_worker_execution_claim", None)
    context.pop("signed_worker_execution_use", None)
    return (
        raw_context, raw_skills, assigned_to, context,
        tuple(parsed_skills), discovered_by,
    )


def _execution_receipts(
    *,
    task_id: str,
    assigned_to: str,
    context: Mapping[str, Any],
    required_skills: tuple[str, ...],
    discovered_by: str,
    token: str,
    now_iso: str,
) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
    token_digest = _digest_text(token)
    claim = _receipt(
        {
            "schema_version": CLAIM_SCHEMA,
            "task_id": task_id,
            "assigned_to": assigned_to,
            "context_digest": _digest(context),
            "required_skills_digest": _digest(list(required_skills)),
            "discovered_by": discovered_by,
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
    return claim, use


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
    "SIGNED_WORKER_TASK_PREFIX",
    "USE_SCHEMA",
    "SignedWorkerExecutionAdmission",
    "admit_signed_worker_execution_once",
    "bind_execution_admission",
]
