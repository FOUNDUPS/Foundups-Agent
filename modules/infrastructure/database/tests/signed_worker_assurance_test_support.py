"""Shared fixtures and helpers for independent-assurance database regressions."""
# ruff: noqa: F401 - imported names form the split-test fixture namespace.

from __future__ import annotations

import hashlib

import json

import sqlite3

from concurrent.futures import ThreadPoolExecutor

from datetime import datetime, timedelta, timezone

from pathlib import Path

from typing import Any

import pytest

from modules.infrastructure.database.src.agent_db import AgentDB

from modules.infrastructure.database.src.signed_worker_assignment import (
    canonical_signed_worker_principal_id,
)

from modules.infrastructure.database.src.db_manager import DatabaseManager

from modules.infrastructure.database.src.signed_worker_assurance_completion import (
    build_assurance_completion_request,
)

from modules.infrastructure.database.src.signed_worker_execution_store import (
    finalize_signed_worker_execution,
)

from modules.infrastructure.database.src.signed_worker_execution_quarantine import (
    QUARANTINE_SCHEMA,
    quarantine_signed_worker_execution,
)

from modules.communication.moltbot_bridge.src.reddog_openclaw_assurance_capacity import (
    build_assurance_renewal_request,
)

from modules.communication.moltbot_bridge.src import (
    reddog_signed_worker_run_task_runtime as run_task_runtime,
)

from modules.communication.moltbot_bridge.src.reddog_signed_worker_execution_claim import (
    EXECUTION_LEASE_SECONDS,
)

from modules.infrastructure.database.src.signed_worker_execution_lease import (
    initialize_execution_lease,
)

from modules.communication.moltbot_bridge.src.reddog_signed_worker_execution_recovery import (
    recover_expired_signed_worker_executions,
)

from modules.communication.moltbot_bridge.src.reddog_signed_worker_result_receipt import (
    append_signed_worker_result_history,
    build_signed_worker_task_result_receipt,
)

@pytest.fixture()
def agent_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> AgentDB:
    db_path = tmp_path / "assurance.db"
    monkeypatch.setenv("FOUNDUPS_DB_ENGINE", "sqlite")
    monkeypatch.setenv("FOUNDUPS_DB_PATH", str(db_path))
    DatabaseManager.reset_for_tests()
    database = AgentDB()
    yield database
    DatabaseManager.reset_for_tests()

def _iso(delta_seconds: int = 0) -> str:
    return (
        datetime.now(timezone.utc) + timedelta(seconds=delta_seconds)
    ).isoformat().replace("+00:00", "Z")

def _create_task(
    database: AgentDB,
    *,
    task_id: str,
    role: str,
    principal_id: str,
    work_order_id: str = "work-1",
    queue_item_id: str = "queue-1",
    capability: str = "independent_diff_verification",
    worker_runtime: str = "openclaw",
    operational_snapshot_id: str = "snapshot-1",
    wsp15_allocation_receipt_id: str = "wsp15-1",
) -> None:
    assert database.create_autonomous_task(
        task_id=task_id,
        description=role,
        required_skills=[
            "reddog_signed_worker_dispatch",
            f"runtime:{worker_runtime}",
            f"capability:{capability}",
        ],
        estimated_complexity=0.5,
        priority_score=19.0,
        context={
            "worker_role": role,
            "worker_principal_id": principal_id,
            "queue_item_id": queue_item_id,
            "capability": capability,
            "worker_runtime": worker_runtime,
            "operational_snapshot_id": operational_snapshot_id,
            "signed_authority_worker_dispatch_receipt": {
                "work_order_id": work_order_id,
                "wsp15_allocation_receipt_id": wsp15_allocation_receipt_id,
            },
            "wsp15_allocation_receipt": {
                "receipt_id": wsp15_allocation_receipt_id,
            },
        },
    )

def _seed_tasks(
    database: AgentDB,
    *,
    author_task_id: str = "author-task",
    author_principal_id: str = "author-0102",
    verifier_task_id: str = "verifier-task",
    verifier_principal_id: str = "verifier-0201",
    **overrides: Any,
) -> None:
    _create_task(
        database,
        task_id=author_task_id,
        role="coding_worker",
        principal_id=author_principal_id,
        **overrides,
    )
    _create_task(
        database,
        task_id=verifier_task_id,
        role="independent_slice_verifier",
        principal_id=verifier_principal_id,
        **overrides,
    )

def _seed_signed_verifier_task(
    database: AgentDB,
    *,
    task_id: str,
) -> None:
    principal_id = canonical_signed_worker_principal_id(task_id)
    context = {
        "source": "reddog_signed_worker_dispatch_runtime",
        "schema_version": "reddog_worker_dispatch_runtime.v1",
        "worker_role": "independent_slice_verifier",
        "worker_principal_id": principal_id,
        "queue_item_id": "queue-1",
        "capability": "independent_slice_verification",
        "worker_runtime": "openclaw",
        "operational_snapshot_id": "snapshot-1",
        "signed_authority_worker_dispatch_receipt": {
            "work_order_id": "work-1",
            "wsp15_allocation_receipt_id": "wsp15-1",
        },
        "wsp15_allocation_receipt": {"receipt_id": "wsp15-1"},
        "signed_worker_agentdb_envelope": {
            "schema_version": "reddog_signed_worker_agentdb_envelope.v1",
            "agentdb_task_binding": {
                "source": "reddog_signed_worker_dispatch_runtime",
                "task_id": task_id,
            },
            "worker_dispatch_intent": {
                "role": "independent_slice_verifier",
                "worker_runtime": "openclaw",
                "capability": "independent_slice_verification",
            },
        },
    }
    assert database.db.execute_write(
        "INSERT INTO agents_autonomous_tasks "
        "(task_id, description, required_skills, estimated_complexity, "
        "priority_score, discovered_by, context, status) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')",
        (
            task_id,
            "signed verifier",
            json.dumps(
                [
                    "reddog_signed_worker_dispatch",
                    "runtime:openclaw",
                    "capability:independent_slice_verification",
                ]
            ),
            0.5,
            19.0,
            "reddog_signed_worker_dispatch_runtime",
            json.dumps(context, sort_keys=True),
        ),
    ) == 1

def _request(**overrides: Any) -> dict[str, Any]:
    request = {
        "schema_version": "reddog_assurance_capacity_request.v1",
        "reservation_id": "assurance-1",
        "work_order_id": "work-1",
        "queue_item_id": "queue-1",
        "author_task_id": "author-task",
        "author_principal_id": "author-0102",
        "verifier_task_id": "verifier-task",
        "verifier_principal_id": "verifier-0201",
        "capability": "independent_diff_verification",
        "worker_runtime": "openclaw",
        "operational_snapshot_id": "snapshot-1",
        "wsp15_allocation_receipt_id": "wsp15-1",
        "lease_id": "lease-1",
        "reserved_at": _iso(-1),
        "expires_at": _iso(300),
    }
    request.update(overrides)
    if "reservation_digest" not in overrides:
        canonical = json.dumps(
            request,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )
        request["reservation_digest"] = (
            "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        )
    return request

def _digest(payload: Any) -> str:
    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()

def _prepare_assurance_finalization(
    database: AgentDB,
    *,
    top_level_capability: str = "independent_slice_verification",
    envelope_capability: str = "",
    terminal_status: str = "VERIFIED",
) -> tuple[dict[str, Any], dict[str, Any]]:
    capability = "independent_slice_verification"
    _seed_tasks(database, capability=capability)
    reserved = database.reserve_independent_assurance(
        _request(capability=capability)
    )
    assert reserved["accepted"] is True
    reservation = dict(reserved["reservation"])
    task = database.get_autonomous_task_by_id("verifier-task")
    assert task is not None
    base_context = dict(task["context"])
    base_context["capability"] = top_level_capability
    if envelope_capability:
        base_context["signed_worker_agentdb_envelope"] = {
            "worker_dispatch_intent": {
                "role": "independent_slice_verifier",
                "worker_runtime": "openclaw",
                "capability": envelope_capability,
            }
        }
    token_digest = "sha256:" + "a" * 64
    claimed_at = datetime.now(timezone.utc)
    claim = {
        "task_id": "verifier-task",
        "assigned_to": "verifier-0201",
        "status": "CLAIMED",
        "token_digest": token_digest,
        "context_digest": _digest(base_context),
        "claimed_at": claimed_at.isoformat(),
        "lease_expires_at": (
            claimed_at + timedelta(seconds=EXECUTION_LEASE_SECONDS)
        ).isoformat(),
    }
    claim["receipt_id"] = _digest(claim)
    use = {
        "task_id": "verifier-task",
        "status": "CONSUMED",
        "claim_receipt_id": claim["receipt_id"],
        "token_digest": token_digest,
    }
    use["receipt_id"] = _digest(use)
    admitted_context = {
        **base_context,
        "signed_worker_execution_claim": claim,
        "signed_worker_execution_use": use,
    }
    with database.db.get_connection() as connection:
        assert connection.execute(
            "UPDATE agents_autonomous_tasks SET context = ?, status = 'executing' "
            "WHERE task_id = ? AND status = 'assigned'",
            (json.dumps(admitted_context, sort_keys=True), "verifier-task"),
        ).rowcount == 1
        assert initialize_execution_lease(
            connection,
            task_id="verifier-task",
            assigned_to="verifier-0201",
            claim=claim,
            use=use,
        )
    terminal_receipt = {
        "receipt_id": "verification-1",
        "receipt_digest": "sha256:" + "b" * 64,
    }
    completion = build_assurance_completion_request(
        reservation=reservation,
        terminal_receipt=terminal_receipt,
        terminal_status=terminal_status,
        completed_at=_iso(),
    )
    staged = database.stage_independent_assurance_completion(completion)
    assert staged["accepted"] is True
    runner_result = {
        "accepted": True,
        "bootstrap_result": {
            "assurance_completion_request": completion,
        },
    }
    receipt = build_signed_worker_task_result_receipt(
        base_context=admitted_context,
        claim_status="ACCEPT",
        result={
            "accepted": True,
            "decision": "VERIFIED",
            "receipt_id": "signed-worker-result-1",
            "capability": capability,
        },
        runner_result=runner_result,
    )
    result_context = append_signed_worker_result_history(
        admitted_context,
        receipt,
    )
    return admitted_context, result_context

def _prepare_signed_verifier_recovery(
    database: AgentDB,
    *,
    terminal_status: str,
) -> tuple[str, datetime]:
    task_id = "reddog-worker-dispatch-verifier-recovery"
    _create_task(
        database,
        task_id="author-task",
        role="coding_worker",
        principal_id="author-0102",
        capability="independent_slice_verification",
    )
    _seed_signed_verifier_task(database, task_id=task_id)
    reserved = database.reserve_independent_assurance(
        _request(
            verifier_task_id=task_id,
            verifier_principal_id=canonical_signed_worker_principal_id(
                task_id
            ),
            capability="independent_slice_verification",
        )
    )
    assert reserved["accepted"] is True
    claimed_at = datetime.fromisoformat(
        str(
            reserved["reservation"].get("admission_reserved_at")
            or reserved["reservation"]["reserved_at"]
        ).replace("Z", "+00:00")
    )
    _admit_seeded_verifier_for_recovery(database, task_id, claimed_at)
    completion = build_assurance_completion_request(
        reservation=reserved["reservation"],
        terminal_receipt={
            "receipt_id": "verification-recovery-1",
            "receipt_digest": "sha256:" + "c" * 64,
        },
        terminal_status=terminal_status,
        completed_at=(claimed_at + timedelta(seconds=10)).isoformat(),
    )
    assert database.stage_independent_assurance_completion(completion)[
        "accepted"
    ] is True
    return task_id, claimed_at

def _admit_seeded_verifier_for_recovery(
    database: AgentDB,
    task_id: str,
    claimed_at: datetime,
) -> None:
    """Seed the database-only recovery fixture without bypassing runtime admission."""

    task = database.get_autonomous_task_by_id(task_id)
    assert task is not None
    base_context = dict(task["context"])
    assigned_to = str(task["assigned_to"])
    skills = list(task["required_skills"])
    token_digest = "sha256:" + ("d" * 64)
    claim = {
        "schema_version": "reddog_signed_worker_execution_claim.v1",
        "task_id": task_id,
        "assigned_to": assigned_to,
        "context_digest": _digest(base_context),
        "required_skills_digest": _digest(skills),
        "discovered_by": "reddog_signed_worker_dispatch_runtime",
        "token_digest": token_digest,
        "claimed_at": claimed_at.isoformat(),
        "lease_expires_at": (
            claimed_at + timedelta(seconds=EXECUTION_LEASE_SECONDS)
        ).isoformat(),
        "status": "CLAIMED",
    }
    claim["receipt_id"] = _digest(claim)
    use = {
        "schema_version": "reddog_signed_worker_execution_use.v1",
        "task_id": task_id,
        "claim_receipt_id": claim["receipt_id"],
        "token_digest": token_digest,
        "consumed_at": claimed_at.isoformat(),
        "status": "CONSUMED",
    }
    use["receipt_id"] = _digest(use)
    context = {
        **base_context,
        "signed_worker_execution_claim": claim,
        "signed_worker_execution_use": use,
    }
    with database.db.get_connection() as connection:
        assert connection.execute(
            "UPDATE agents_autonomous_tasks SET status = 'executing', context = ? "
            "WHERE task_id = ? AND status = 'assigned' AND assigned_to = ?",
            (json.dumps(context, sort_keys=True), task_id, assigned_to),
        ).rowcount == 1
        assert initialize_execution_lease(
            connection,
            task_id=task_id,
            assigned_to=assigned_to,
            claim=claim,
            use=use,
        )

__all__ = [name for name in globals() if not name.startswith("__")]
