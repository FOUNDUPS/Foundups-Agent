"""Concrete AgentDB writer for signed worker-dispatch task publication."""

from __future__ import annotations

import json
from typing import Any, Mapping, Optional, Sequence

from modules.communication.moltbot_bridge.src.reddog_signed_worker_agentdb_envelope import (
    SIGNED_WORKER_DISPATCH_TASK_SOURCE,
)
from modules.communication.moltbot_bridge.src.reddog_signed_worker_dispatch_runtime_types import (
    SignedWorkerDispatchRuntimeReceipt,
    SignedWorkerDispatchTaskSpec,
)


class AgentDbSignedWorkerDispatchTaskWriter:
    """Atomically stage and activate signed worker-dispatch tasks."""

    def __init__(self, agent_db_factory: Optional[Any] = None) -> None:
        self._agent_db_factory = agent_db_factory

    def enqueue_signed_worker_dispatch_tasks(
        self,
        tasks: Sequence[SignedWorkerDispatchTaskSpec],
        receipt: SignedWorkerDispatchRuntimeReceipt,
    ) -> Mapping[str, Any]:
        db = self._database()
        task_ids = tuple(task.task_id for task in tasks)
        try:
            with db.db.get_connection() as connection:
                duplicate = _duplicate_task_id(connection, task_ids)
                if duplicate:
                    return _duplicate_result(duplicate)
                _insert_tasks(connection, tasks)
        except Exception as exc:
            return _write_failure(exc)
        return {
            "ok": True,
            "created_task_ids": list(task_ids),
            "source_dispatch_receipt_id": receipt.source_dispatch_receipt_id,
        }

    def recover_signed_worker_dispatch_tasks(
        self,
        tasks: Sequence[SignedWorkerDispatchTaskSpec],
        receipt: SignedWorkerDispatchRuntimeReceipt,
    ) -> Mapping[str, Any]:
        db = self._database()
        inserted = False
        try:
            with db.db.get_connection() as connection:
                recovery_state = _task_batch_recovery_state(connection, tasks)
                if recovery_state == "ABSENT":
                    _insert_tasks(connection, tasks)
                    inserted = True
                elif recovery_state != "EXACT_HELD":
                    return _duplicate_result(tasks[0].task_id if tasks else "")
        except Exception as exc:
            return _write_failure(exc)
        return {
            "ok": True,
            "created_task_ids": [task.task_id for task in tasks],
            "source_dispatch_receipt_id": receipt.source_dispatch_receipt_id,
            "idempotent_recovery": True,
            "recovery_inserted": inserted,
        }

    def recover_applied_signed_worker_dispatch_tasks(
        self,
        tasks: Sequence[SignedWorkerDispatchTaskSpec],
        receipt: SignedWorkerDispatchRuntimeReceipt,
    ) -> Mapping[str, Any]:
        db = self._database()
        try:
            with db.db.get_connection() as connection:
                if _task_batch_recovery_state(connection, tasks) not in {
                    "EXACT_HELD",
                    "EXACT_ACTIVE",
                }:
                    return _duplicate_result(tasks[0].task_id if tasks else "")
        except Exception as exc:
            return _write_failure(exc)
        return {
            "ok": True,
            "created_task_ids": [task.task_id for task in tasks],
            "source_dispatch_receipt_id": receipt.source_dispatch_receipt_id,
            "idempotent_recovery": True,
        }

    def activate_signed_worker_dispatch_tasks(
        self,
        tasks: Sequence[SignedWorkerDispatchTaskSpec],
        receipt: SignedWorkerDispatchRuntimeReceipt,
    ) -> Mapping[str, Any]:
        db = self._database()
        task_ids = tuple(task.task_id for task in tasks)
        try:
            with db.db.get_connection() as connection:
                recovery_state = _task_batch_recovery_state(connection, tasks)
                if recovery_state == "EXACT_ACTIVE":
                    return {
                        "ok": True,
                        "created_task_ids": list(task_ids),
                        "source_dispatch_receipt_id": (
                            receipt.source_dispatch_receipt_id
                        ),
                        "idempotent_recovery": True,
                    }
                if recovery_state != "EXACT_HELD":
                    return _duplicate_result(task_ids[0] if task_ids else "")
                changed = _activate_exact_tasks(connection, tasks)
                if changed != len(task_ids):
                    raise RuntimeError("signed_worker_activation_conflict")
        except Exception as exc:
            return _write_failure(exc)
        return {
            "ok": True,
            "created_task_ids": list(task_ids),
            "source_dispatch_receipt_id": receipt.source_dispatch_receipt_id,
        }

    def _database(self) -> Any:
        factory = self._agent_db_factory
        if factory is None:
            from modules.infrastructure.database.src.agent_db import AgentDB

            factory = AgentDB
        return factory()


def _duplicate_task_id(connection: Any, task_ids: Sequence[str]) -> str:
    for task_id in task_ids:
        existing = connection.execute(
            "SELECT task_id FROM agents_autonomous_tasks WHERE task_id = ?",
            (task_id,),
        ).fetchone()
        if existing:
            return task_id
    return ""


def _task_batch_recovery_state(
    connection: Any,
    tasks: Sequence[SignedWorkerDispatchTaskSpec],
) -> str:
    fields = (
        "description",
        "required_skills",
        "estimated_complexity",
        "priority_score",
        "discovered_by",
        "context",
        "origin_continuity_id",
        "status",
    )
    query = """
        SELECT description, required_skills, estimated_complexity,
               priority_score, discovered_by, context, origin_continuity_id,
               status
        FROM agents_autonomous_tasks WHERE task_id = ?
    """
    found = 0
    statuses: set[str] = set()
    for task in tasks:
        row = connection.execute(query, (task.task_id,)).fetchone()
        if row is None:
            continue
        found += 1
        expected = _task_row(task)[1:]
        actual = tuple(row[field] for field in fields[:-1])
        if actual != expected:
            return "CONFLICT"
        statuses.add(str(row["status"] or ""))
    if found == 0:
        return "ABSENT"
    if found == len(tasks) and statuses == {"publication_held"}:
        return "EXACT_HELD"
    if found == len(tasks) and statuses == {"pending"}:
        return "EXACT_ACTIVE"
    return "CONFLICT"


def _insert_tasks(
    connection: Any,
    tasks: Sequence[SignedWorkerDispatchTaskSpec],
) -> None:
    for task in tasks:
        connection.execute(
            """
            INSERT INTO agents_autonomous_tasks
            (task_id, description, required_skills, estimated_complexity,
             priority_score, discovered_by, context, origin_continuity_id, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'publication_held')
            """,
            _task_row(task),
        )


def _activate_exact_tasks(
    connection: Any,
    tasks: Sequence[SignedWorkerDispatchTaskSpec],
) -> int:
    changed = 0
    for task in tasks:
        changed += connection.execute(
            """
            UPDATE agents_autonomous_tasks SET status = 'pending'
            WHERE task_id = ? AND description = ? AND required_skills = ?
              AND estimated_complexity = ? AND priority_score = ?
              AND discovered_by = ? AND context = ?
              AND origin_continuity_id = ? AND status = 'publication_held'
            """,
            _task_row(task),
        ).rowcount
    return changed


def _task_row(task: SignedWorkerDispatchTaskSpec) -> tuple[Any, ...]:
    return (
        task.task_id,
        task.description,
        json.dumps(list(task.required_skills), sort_keys=True),
        float(task.estimated_complexity),
        float(task.priority_score),
        SIGNED_WORKER_DISPATCH_TASK_SOURCE,
        json.dumps(dict(task.context), sort_keys=True),
        task.origin_continuity_id,
    )


def _duplicate_result(task_id: str) -> dict[str, Any]:
    return {
        "ok": False,
        "reason": "task_already_exists",
        "task_id": task_id,
        "created_task_ids": [],
    }


def _write_failure(exc: Exception) -> dict[str, Any]:
    return {
        "ok": False,
        "reason": "agentdb_write_failed",
        "error": str(exc)[:200],
        "created_task_ids": [],
    }
