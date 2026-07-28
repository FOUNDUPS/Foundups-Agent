"""Dedicated assignment CAS for protected RedDog signed-worker tasks."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Mapping


SIGNED_WORKER_TASK_PREFIX = "reddog-worker-dispatch-"
SIGNED_WORKER_SOURCE = "reddog_signed_worker_dispatch_runtime"
SIGNED_WORKER_SCHEMA = "reddog_worker_dispatch_runtime.v1"
SIGNED_WORKER_ENVELOPE_SCHEMA = "reddog_signed_worker_agentdb_envelope.v1"
SIGNED_WORKER_SKILL = "reddog_signed_worker_dispatch"


def canonical_signed_worker_principal_id(task_id: str) -> str:
    """Return the task-bound principal used for one protected assignment."""

    return f"agentdb-task:{task_id}"


def assign_signed_worker_task(connection: Any, task_id: str) -> bool:
    """Assign one exact pending signed task to its envelope-bound principal."""

    row = connection.execute(
        "SELECT status, discovered_by, context, required_skills, assigned_to "
        "FROM agents_autonomous_tasks WHERE task_id = ?",
        (task_id,),
    ).fetchone()
    parsed = _validated_row(row, task_id)
    if parsed is None:
        _quarantine_invalid_pending_task(connection, row=row, task_id=task_id)
        return False
    raw_context, raw_skills, principal_id = parsed
    changed = connection.execute(
        "UPDATE agents_autonomous_tasks "
        "SET assigned_to = ?, assigned_at = CURRENT_TIMESTAMP, status = 'assigned' "
        "WHERE task_id = ? AND status = 'pending' AND discovered_by = ? "
        "AND context = ? AND required_skills = ? "
        "AND (assigned_to IS NULL OR assigned_to = '')",
        (
            principal_id,
            task_id,
            SIGNED_WORKER_SOURCE,
            raw_context,
            raw_skills,
        ),
    ).rowcount
    return changed == 1


def _quarantine_invalid_pending_task(
    connection: Any,
    *,
    row: Any,
    task_id: str,
) -> None:
    """Remove one invalid protected task from the live claim namespace."""

    if row is None or not task_id.startswith(SIGNED_WORKER_TASK_PREFIX):
        return
    payload = dict(row)
    if payload.get("status") != "pending":
        return
    now = datetime.now(timezone.utc).isoformat()
    quarantine = {
        "schema_version": "reddog_signed_worker_assignment_quarantine.v1",
        "task_id": task_id,
        "reason": "invalid_signed_worker_assignment",
        "quarantined_at": now,
        "no_worker_effect_performed": True,
    }
    quarantine["receipt_id"] = _digest(quarantine)
    raw_context = str(payload.get("context") or "")
    context = _context(raw_context)
    context["signed_worker_assignment_quarantine"] = quarantine
    connection.execute(
        "UPDATE agents_autonomous_tasks "
        "SET status = 'quarantined', completed_at = ?, context = ? "
        "WHERE task_id = ? AND status = 'pending' "
        "AND discovered_by = ? AND context = ? AND required_skills = ? "
        "AND (assigned_to IS NULL OR assigned_to = '')",
        (
            now,
            json.dumps(context, sort_keys=True),
            task_id,
            str(payload.get("discovered_by") or ""),
            raw_context,
            str(payload.get("required_skills") or ""),
        ),
    )


def signed_worker_assignment_matches(
    task_id: str,
    assigned_to: str,
    context: Mapping[str, Any],
) -> bool:
    """Require execution ownership to match the protected task principal."""

    return (
        task_id.startswith(SIGNED_WORKER_TASK_PREFIX)
        and assigned_to == canonical_signed_worker_principal_id(task_id)
        and _valid_context(context, task_id)
    )


def _validated_row(
    row: Any,
    task_id: str,
) -> tuple[str, str, str] | None:
    if row is None or not task_id.startswith(SIGNED_WORKER_TASK_PREFIX):
        return None
    payload = dict(row)
    raw_context = str(payload.get("context") or "")
    raw_skills = str(payload.get("required_skills") or "")
    try:
        context = json.loads(raw_context)
        skills = json.loads(raw_skills)
    except (TypeError, ValueError):
        return None
    if (
        payload.get("status") != "pending"
        or payload.get("discovered_by") != SIGNED_WORKER_SOURCE
        or not isinstance(context, Mapping)
        or not isinstance(skills, list)
        or not _valid_context(context, task_id)
        or not _valid_skills(skills, context)
    ):
        return None
    return (
        raw_context,
        raw_skills,
        canonical_signed_worker_principal_id(task_id),
    )


def _valid_context(context: Mapping[str, Any], task_id: str) -> bool:
    envelope = context.get("signed_worker_agentdb_envelope")
    envelope = envelope if isinstance(envelope, Mapping) else {}
    binding = envelope.get("agentdb_task_binding")
    binding = binding if isinstance(binding, Mapping) else {}
    intent = envelope.get("worker_dispatch_intent")
    intent = intent if isinstance(intent, Mapping) else {}
    principal_id = canonical_signed_worker_principal_id(task_id)
    return (
        context.get("source") == SIGNED_WORKER_SOURCE
        and context.get("schema_version") == SIGNED_WORKER_SCHEMA
        and context.get("worker_principal_id") == principal_id
        and envelope.get("schema_version") == SIGNED_WORKER_ENVELOPE_SCHEMA
        and binding.get("source") == SIGNED_WORKER_SOURCE
        and binding.get("task_id") == task_id
        and bool(intent.get("worker_runtime"))
        and bool(intent.get("role"))
        and bool(intent.get("capability"))
    )


def _valid_skills(skills: list[Any], context: Mapping[str, Any]) -> bool:
    envelope = context.get("signed_worker_agentdb_envelope")
    envelope = envelope if isinstance(envelope, Mapping) else {}
    intent = envelope.get("worker_dispatch_intent")
    intent = intent if isinstance(intent, Mapping) else {}
    expected = {
        SIGNED_WORKER_SKILL,
        f"runtime:{intent.get('worker_runtime')}",
        f"capability:{intent.get('capability')}",
    }
    return (
        all(isinstance(value, str) and value for value in skills)
        and set(skills) == expected
    )


def _context(raw_context: str) -> dict[str, Any]:
    try:
        parsed = json.loads(raw_context)
    except (TypeError, ValueError):
        return {}
    return dict(parsed) if isinstance(parsed, Mapping) else {}


def _digest(value: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        dict(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("ascii")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


__all__ = [
    "assign_signed_worker_task",
    "canonical_signed_worker_principal_id",
    "signed_worker_assignment_matches",
]
