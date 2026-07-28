"""Shared fixtures and helpers for signed-worker AgentDB regressions."""
# ruff: noqa: F401 - imported names form the split-test fixture namespace.

from __future__ import annotations

import hashlib

import json

import threading

from concurrent.futures import ThreadPoolExecutor

from contextlib import contextmanager

from dataclasses import replace

from datetime import datetime, timedelta, timezone

from pathlib import Path

from types import SimpleNamespace

import pytest

from modules.communication.moltbot_bridge.scripts.run_task import execute_task

from modules.communication.moltbot_bridge.src import (
    openclaw_supervisor as supervisor_module,
    reddog_openclaw_hermes_0102_worker_dispatch_runtime as runtime,
    reddog_signed_worker_execution_claim as execution_claim_module,
    reddog_signed_worker_execution_recovery as execution_recovery_module,
    reddog_signed_worker_run_task_runtime as run_task_runtime,
    reddog_signed_worker_supervisor_admission as supervisor_admission_module,
)

from modules.communication.moltbot_bridge.src.openclaw_supervisor import (
    SIGNED_WORKER_OPENCLAW_CLAIM_REJECT,
    SignedWorkerOpenClawClaimReason,
    claim_reddog_signed_worker_dispatch_task_once,
)

from modules.communication.moltbot_bridge.src.reddog_signed_worker_agentdb_envelope import (
    verify_reddog_signed_worker_agentdb_envelope,
)

from modules.communication.moltbot_bridge.src.reddog_signed_worker_execution_claim import (
    EXECUTION_LEASE_SECONDS,
    admit_signed_worker_execution_once as _admit_signed_worker_execution_once,
    bind_execution_admission,
)

from modules.communication.moltbot_bridge.src.reddog_signed_worker_execution_recovery import (
    recover_expired_signed_worker_executions,
)

from modules.communication.moltbot_bridge.src.reddog_signed_worker_result_receipt import (
    append_signed_worker_result_history,
    build_signed_worker_task_result_receipt,
)

from modules.communication.moltbot_bridge.tests.reddog_resident_queue_test_helpers import (
    worker_dispatch_authority_verification_context,
)

from modules.communication.moltbot_bridge.tests.test_reddog_signed_worker_dispatch_task_executor import (
    _FakeRunner,
    _publish_agentdb_task,
)

from modules.infrastructure.database.src.agent_db import AgentDB

from modules.infrastructure.database.src.db_manager import DatabaseManager

from modules.infrastructure.database.src import (
    signed_worker_execution_commit as execution_commit_module,
    signed_worker_execution_store as execution_store_module,
)

from modules.infrastructure.database.src.signed_worker_assignment import (
    canonical_signed_worker_principal_id,
)

from modules.infrastructure.database.src.signed_worker_execution_lease import (
    MAX_EXECUTION_LEASE_SECONDS,
    renew_signed_worker_execution_lease,
)

@pytest.fixture(autouse=True)
def isolated_agent_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("FOUNDUPS_DB_PATH", str(tmp_path / "foundups.db"))
    monkeypatch.setenv("OPENCLAW_SIGNED_QUEUE_STAGE_TASKS_ENABLED", "1")
    DatabaseManager.reset_for_tests()
    from modules.communication.moltbot_bridge.src import (
        reddog_signed_worker_agentdb_envelope as envelope_module,
    )

    monkeypatch.setattr(
        envelope_module,
        "build_worker_dispatch_authority_context_from_env",
        lambda **_: worker_dispatch_authority_verification_context(),
    )
    yield
    DatabaseManager.reset_for_tests()

def _rewrite_context(task_id: str, mutate) -> dict[str, object]:
    db = AgentDB()
    task = db.get_autonomous_task_by_id(task_id)
    assert task is not None
    context = json.loads(json.dumps(task["context"]))
    mutate(context)
    assert db.db.execute_write(
        "UPDATE agents_autonomous_tasks SET context = ? WHERE task_id = ?",
        (json.dumps(context, sort_keys=True), task_id),
    ) == 1
    return context

def admit_signed_worker_execution_once(*, db: AgentDB, task_id: str, **kwargs):
    """Exercise admission only through the canonical signed-envelope verifier."""

    task = db.get_autonomous_task_by_id(task_id)
    assert task is not None
    verified = verify_reddog_signed_worker_agentdb_envelope(
        envelope=task["context"]["signed_worker_agentdb_envelope"],
        task_id=task_id,
        authority_context=worker_dispatch_authority_verification_context(),
    )
    return _admit_signed_worker_execution_once(
        db=db,
        task_id=task_id,
        verified_envelope=verified,
        **kwargs,
    )

def _set_nested(
    mapping: dict[str, object],
    path: tuple[object, ...],
    value: object,
) -> None:
    cursor: object = mapping
    for key in path[:-1]:
        cursor = cursor[key]  # type: ignore[index]
    cursor[path[-1]] = value  # type: ignore[index]

def _test_digest(value: object) -> str:
    raw = json.dumps(
        value, sort_keys=True, separators=(",", ":"),
        ensure_ascii=True, default=str,
    )
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()

def _rechain_context_history(context: dict[str, object]) -> None:
    history = context["signed_worker_task_result_receipts"]
    assert isinstance(history, list)
    normalized: list[dict[str, object]] = []
    for raw in history:
        assert isinstance(raw, dict)
        sequence = int(raw.get("attempt_sequence") or 0)
        entry = {
            "attempt_sequence": sequence,
            "claim_status": str(raw.get("claim_status") or ""),
            "receipt_id": str(raw.get("receipt_id") or ""),
            "receipt_digest": str(raw.get("receipt_digest") or ""),
            "previous_history_digest": (
                str(normalized[-1]["history_entry_digest"])
                if normalized
                else (
                    _test_digest([])
                    if sequence == 1
                    else str(raw.get("previous_history_digest") or "")
                )
            ),
        }
        entry["history_entry_digest"] = _test_digest(entry)
        normalized.append(entry)
    context["signed_worker_task_result_receipts"] = normalized

__all__ = [name for name in globals() if not name.startswith("__")]
