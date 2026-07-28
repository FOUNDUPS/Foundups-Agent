#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Focused tests for durable independent-assurance reservations."""

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
from modules.infrastructure.database.src.db_manager import DatabaseManager
from modules.infrastructure.database.src.signed_worker_assurance_completion import (
    build_assurance_completion_request,
)
from modules.infrastructure.database.src.signed_worker_execution_store import (
    finalize_signed_worker_execution,
)
from modules.communication.moltbot_bridge.src.reddog_openclaw_assurance_capacity import (
    build_assurance_renewal_request,
)
from modules.communication.moltbot_bridge.src import (
    reddog_signed_worker_run_task_runtime as run_task_runtime,
)
from modules.communication.moltbot_bridge.src.reddog_signed_worker_execution_claim import (
    EXECUTION_LEASE_SECONDS,
    admit_signed_worker_execution_once,
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
    context = {
        "worker_role": "independent_slice_verifier",
        "worker_principal_id": "verifier-0201",
        "queue_item_id": "queue-1",
        "capability": "independent_slice_verification",
        "worker_runtime": "openclaw",
        "operational_snapshot_id": "snapshot-1",
        "signed_authority_worker_dispatch_receipt": {
            "work_order_id": "work-1",
            "wsp15_allocation_receipt_id": "wsp15-1",
        },
        "wsp15_allocation_receipt": {"receipt_id": "wsp15-1"},
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
    claim = {
        "task_id": "verifier-task",
        "assigned_to": "verifier-0201",
        "status": "CLAIMED",
        "token_digest": token_digest,
        "context_digest": _digest(base_context),
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
    assert database.db.execute_write(
        "UPDATE agents_autonomous_tasks SET context = ?, status = 'executing' "
        "WHERE task_id = ? AND status = 'assigned'",
        (json.dumps(admitted_context, sort_keys=True), "verifier-task"),
    ) == 1
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
    assert admit_signed_worker_execution_once(
        db=database,
        task_id=task_id,
        now_factory=lambda: claimed_at,
    ) is not None
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


def test_negative_verifier_completion_rehydrates_from_durable_stage(
    agent_db: AgentDB,
) -> None:
    admitted, _ = _prepare_assurance_finalization(
        agent_db,
        terminal_status="REJECT",
    )

    result = run_task_runtime._finalize_owned_execution(
        db=agent_db,
        task_id="verifier-task",
        context=admitted,
        result={
            "ok": False,
            "detail": "independent_verifier_rejected",
            "executor": "reddog:signed_worker_dispatch",
        },
    )

    assert result["ok"] is False
    assert result["detail"] == "independent_verifier_rejected"
    task = agent_db.get_autonomous_task_by_id("verifier-task")
    assert task is not None and task["status"] == "failed"
    receipt = task["context"]["signed_worker_task_last_result"]
    assert receipt["assurance_completion_request"]["terminal_status"] == "REJECT"
    reservation = agent_db.get_independent_assurance_reservation("assurance-1")
    assert reservation is not None
    assert reservation["reservation"]["status"] == "REJECT"


def test_restart_rolls_forward_durable_negative_verifier_stage(
    agent_db: AgentDB,
) -> None:
    task_id, claimed_at = _prepare_signed_verifier_recovery(
        agent_db,
        terminal_status="REJECT",
    )

    DatabaseManager.reset_for_tests()
    restarted = AgentDB()
    recovery = recover_expired_signed_worker_executions(
        restarted,
        now_factory=lambda: (
            claimed_at
            + timedelta(seconds=EXECUTION_LEASE_SECONDS + 1)
        ),
    )

    assert recovery["accepted"] is True
    assert recovery["recovered_task_ids"] == [task_id]
    task = restarted.get_autonomous_task_by_id(task_id)
    assert task is not None and task["status"] == "failed"
    assert task["context"]["signed_worker_task_last_result"][
        "assurance_completion_request"
    ]["terminal_status"] == "REJECT"
    reservation = restarted.get_independent_assurance_reservation("assurance-1")
    assert reservation is not None
    assert reservation["reservation"]["status"] == "REJECT"


def test_restart_refuses_digest_only_positive_verifier_stage(
    agent_db: AgentDB,
) -> None:
    task_id, claimed_at = _prepare_signed_verifier_recovery(
        agent_db,
        terminal_status="VERIFIED",
    )

    DatabaseManager.reset_for_tests()
    restarted = AgentDB()
    recovery = recover_expired_signed_worker_executions(
        restarted,
        now_factory=lambda: (
            claimed_at
            + timedelta(seconds=EXECUTION_LEASE_SECONDS + 1)
        ),
    )

    assert recovery["accepted"] is False
    assert recovery["rejected_task_ids"] == [task_id]
    task = restarted.get_autonomous_task_by_id(task_id)
    assert task is not None and task["status"] == "executing"
    reservation = restarted.get_independent_assurance_reservation("assurance-1")
    assert reservation is not None
    assert reservation["reservation"]["status"] == "RESERVED"


def test_restart_rejects_corrupt_durable_verifier_stage(
    agent_db: AgentDB,
) -> None:
    task_id, claimed_at = _prepare_signed_verifier_recovery(
        agent_db,
        terminal_status="REJECT",
    )
    assert agent_db.db.execute_write(
        "UPDATE agents_independent_assurance_reservations "
        "SET staged_completion_digest = ? WHERE reservation_id = ?",
        ("sha256:" + "f" * 64, "assurance-1"),
    ) == 1

    DatabaseManager.reset_for_tests()
    restarted = AgentDB()
    recovery = recover_expired_signed_worker_executions(
        restarted,
        now_factory=lambda: (
            claimed_at
            + timedelta(seconds=EXECUTION_LEASE_SECONDS + 1)
        ),
    )

    assert recovery["accepted"] is False
    assert recovery["rejected_task_ids"] == [task_id]
    task = restarted.get_autonomous_task_by_id(task_id)
    assert task is not None and task["status"] == "executing"
    reservation = restarted.get_independent_assurance_reservation("assurance-1")
    assert reservation is not None
    assert reservation["reservation"]["status"] == "RESERVED"


def test_post_rehydration_runner_rejection_persists_canonical_identity(
    agent_db: AgentDB,
) -> None:
    admitted, _ = _prepare_assurance_finalization(
        agent_db,
        top_level_capability="candidate_queue_review",
        envelope_capability="independent_slice_verification",
        terminal_status="REJECT",
    )
    canonical = {
        **admitted,
        "worker_role": "independent_slice_verifier",
        "worker_runtime": "openclaw",
        "capability": "independent_slice_verification",
        "worker_dispatch_intent": {
            "role": "independent_slice_verifier",
            "worker_runtime": "openclaw",
            "capability": "independent_slice_verification",
        },
    }

    result = run_task_runtime._finalize_owned_execution(
        db=agent_db,
        task_id="verifier-task",
        context=canonical,
        result={
            "ok": False,
            "detail": "runner_rejected_after_rehydration",
            "executor": "reddog:signed_worker_dispatch",
        },
    )

    assert result["ok"] is False
    assert result["detail"] == "runner_rejected_after_rehydration"
    task = agent_db.get_autonomous_task_by_id("verifier-task")
    assert task is not None and task["status"] == "failed"
    assert task["context"]["worker_role"] == "independent_slice_verifier"
    assert task["context"]["worker_runtime"] == "openclaw"
    assert task["context"]["capability"] == "independent_slice_verification"


def test_reserve_claims_pending_verifier_and_rehydrates_after_restart(
    agent_db: AgentDB,
) -> None:
    _seed_tasks(agent_db)

    result = agent_db.reserve_independent_assurance(_request())

    assert result["accepted"] is True
    assert result["status"] == "RESERVED"
    reservation = result["reservation"]
    assert reservation["reservation_id"] == "assurance-1"
    assert reservation["reservation_digest"].startswith("sha256:")
    assert len(reservation["reservation_digest"]) == 71
    task = agent_db.get_autonomous_task_by_id("verifier-task")
    assert task is not None
    assert task["status"] == "assigned"
    assert task["assigned_to"] == "verifier-0201"

    DatabaseManager.reset_for_tests()
    restarted = AgentDB()
    rehydrated = restarted.get_independent_assurance_reservation("assurance-1")
    assert rehydrated is not None
    assert rehydrated["accepted"] is True
    assert rehydrated["reservation"]["reservation_digest"] == reservation["reservation_digest"]


def test_concurrent_reservations_allow_exactly_one_winner(agent_db: AgentDB) -> None:
    _seed_tasks(agent_db)

    first = _request(reservation_id="assurance-a", lease_id="lease-a")
    second = _request(reservation_id="assurance-b", lease_id="lease-b")
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(
            executor.map(agent_db.reserve_independent_assurance, (first, second))
        )

    assert sum(result["accepted"] is True for result in results) == 1
    assert sum(result["accepted"] is False for result in results) == 1
    rows = agent_db.db.execute_query(
        "SELECT reservation_id FROM agents_independent_assurance_reservations"
    )
    assert len(rows) == 1


def test_concurrent_author_work_order_reservations_rollback_losing_verifier_claim(
    agent_db: AgentDB,
) -> None:
    _seed_tasks(agent_db)
    _create_task(
        agent_db,
        task_id="verifier-task-2",
        role="independent_slice_verifier",
        principal_id="verifier-0302",
    )
    first = _request(reservation_id="assurance-a", lease_id="lease-a")
    second = _request(
        reservation_id="assurance-b",
        verifier_task_id="verifier-task-2",
        verifier_principal_id="verifier-0302",
        lease_id="lease-b",
    )

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(
            executor.map(agent_db.reserve_independent_assurance, (first, second))
        )

    accepted = [result for result in results if result["accepted"] is True]
    rejected = [result for result in results if result["accepted"] is False]
    assert len(accepted) == 1
    assert len(rejected) == 1
    winner_task_id = accepted[0]["reservation"]["verifier_task_id"]
    loser_task_id = (
        "verifier-task-2" if winner_task_id == "verifier-task" else "verifier-task"
    )
    assert agent_db.get_autonomous_task_by_id(winner_task_id)["status"] == "assigned"
    assert agent_db.get_autonomous_task_by_id(loser_task_id)["status"] == "pending"


@pytest.mark.parametrize(
    ("request_changes", "expected_reason"),
    [
        (
            {
                "verifier_task_id": "author-task",
                "verifier_principal_id": "verifier-0201",
            },
            "author_verifier_task_equality",
        ),
        (
            {"verifier_principal_id": "author-0102"},
            "author_verifier_principal_equality",
        ),
    ],
)
def test_reserve_rejects_author_or_principal_equality(
    agent_db: AgentDB,
    request_changes: dict[str, str],
    expected_reason: str,
) -> None:
    _seed_tasks(agent_db)

    result = agent_db.reserve_independent_assurance(_request(**request_changes))

    assert result["accepted"] is False
    assert expected_reason in result["rejection_reasons"]
    assert agent_db.get_autonomous_task_by_id("verifier-task")["status"] == "pending"


@pytest.mark.parametrize(
    ("task_override", "request_override", "expected_reason"),
    [
        ({"role": "coding_worker"}, {}, "verifier_task_role_mismatch"),
        ({"capability": "other"}, {}, "verifier_task_capability_mismatch"),
        ({"worker_runtime": "hermes"}, {}, "verifier_task_worker_runtime_mismatch"),
        (
            {"operational_snapshot_id": "snapshot-other"},
            {},
            "verifier_task_operational_snapshot_id_mismatch",
        ),
        (
            {"wsp15_allocation_receipt_id": "wsp15-other"},
            {},
            "verifier_task_wsp15_allocation_receipt_id_mismatch",
        ),
        ({}, {"expires_at": _iso(-10)}, "reservation_expired"),
        ({}, {"reserved_at": _iso(600)}, "reserved_at_in_future"),
    ],
)
def test_reserve_rejects_malformed_expired_or_mismatched_requests(
    agent_db: AgentDB,
    task_override: dict[str, str],
    request_override: dict[str, str],
    expected_reason: str,
) -> None:
    _create_task(
        agent_db,
        task_id="author-task",
        role="coding_worker",
        principal_id="author-0102",
    )
    verifier = {
        "role": "independent_slice_verifier",
        "capability": "independent_diff_verification",
        "worker_runtime": "openclaw",
        "operational_snapshot_id": "snapshot-1",
        "wsp15_allocation_receipt_id": "wsp15-1",
    }
    verifier.update(task_override)
    _create_task(
        agent_db,
        task_id="verifier-task",
        role=verifier["role"],
        principal_id="verifier-0201",
        capability=verifier["capability"],
        worker_runtime=verifier["worker_runtime"],
        operational_snapshot_id=verifier["operational_snapshot_id"],
        wsp15_allocation_receipt_id=verifier["wsp15_allocation_receipt_id"],
    )

    result = agent_db.reserve_independent_assurance(
        _request(**request_override)
    )

    assert result["accepted"] is False
    assert expected_reason in result["rejection_reasons"]
    assert agent_db.get_autonomous_task_by_id("verifier-task")["status"] == "pending"


def test_reserve_rejects_forged_digest(agent_db: AgentDB) -> None:
    _seed_tasks(agent_db)

    result = agent_db.reserve_independent_assurance(
        _request(reservation_digest="0" * 64)
    )

    assert result["accepted"] is False
    assert result["rejection_reasons"] == ["reservation_digest_mismatch"]


def test_reserve_accepts_bridge_canonical_prefixed_digest(agent_db: AgentDB) -> None:
    _seed_tasks(agent_db)
    request = _request()

    result = agent_db.reserve_independent_assurance(request)

    assert result["accepted"] is True
    assert (
        result["reservation"]["reservation_digest"]
        == request["reservation_digest"]
    )


def test_reserve_rejects_author_snapshot_mismatch(agent_db: AgentDB) -> None:
    _create_task(
        agent_db,
        task_id="author-task",
        role="coding_worker",
        principal_id="author-0102",
        operational_snapshot_id="snapshot-other",
    )
    _create_task(
        agent_db,
        task_id="verifier-task",
        role="independent_slice_verifier",
        principal_id="verifier-0201",
    )

    result = agent_db.reserve_independent_assurance(_request())

    assert result["accepted"] is False
    assert result["rejection_reasons"] == [
        "author_task_operational_snapshot_id_mismatch"
    ]


def test_reserve_rejects_terminal_author_task(agent_db: AgentDB) -> None:
    _seed_tasks(agent_db)
    assert agent_db.complete_autonomous_task("author-task")

    result = agent_db.reserve_independent_assurance(_request())

    assert result["accepted"] is False
    assert result["rejection_reasons"] == ["author_task_not_pending"]
    assert agent_db.get_autonomous_task_by_id("verifier-task")["status"] == "pending"


def test_reserve_rejects_author_already_claimed_before_assurance(
    agent_db: AgentDB,
) -> None:
    _seed_tasks(agent_db)
    updated = agent_db.db.execute_write(
        """
        UPDATE agents_autonomous_tasks
        SET status = 'assigned', assigned_to = 'worker:unexpected'
        WHERE task_id = 'author-task'
        """
    )
    assert updated == 1

    result = agent_db.reserve_independent_assurance(_request())

    assert result["accepted"] is False
    assert result["rejection_reasons"] == ["author_task_not_pending"]
    assert agent_db.get_autonomous_task_by_id("verifier-task")["status"] == "pending"


def test_detached_terminal_completion_is_rejected_without_mutation(
    agent_db: AgentDB,
) -> None:
    _seed_tasks(agent_db)
    assert agent_db.reserve_independent_assurance(_request())["accepted"] is True
    reservation = agent_db.get_independent_assurance_reservation("assurance-1")[
        "reservation"
    ]

    completed = agent_db.complete_independent_assurance(
        "assurance-1",
        admission_reservation_digest=reservation[
            "admission_reservation_digest"
        ],
        terminal_receipt_id="verification-1",
        terminal_receipt_digest="sha256:" + "a" * 64,
        status="VERIFIED",
        now_iso=_iso(),
    )
    assert completed["accepted"] is False
    assert completed["rejection_reasons"] == [
        "completion_owned_by_signed_worker_finalizer"
    ]
    assert agent_db.get_autonomous_task_by_id("verifier-task")["status"] == "assigned"
    persisted = agent_db.get_independent_assurance_reservation("assurance-1")
    assert persisted is not None
    assert persisted["reservation"]["status"] == "RESERVED"


def test_detached_completion_rejects_before_digest_interpretation(
    agent_db: AgentDB,
) -> None:
    _seed_tasks(agent_db)
    assert agent_db.reserve_independent_assurance(_request())["accepted"] is True

    completed = agent_db.complete_independent_assurance(
        "assurance-1",
        admission_reservation_digest="sha256:" + "f" * 64,
        terminal_receipt_id="verification-1",
        terminal_receipt_digest="sha256:" + "a" * 64,
        status="VERIFIED",
        now_iso=_iso(),
    )

    assert completed["accepted"] is False
    assert completed["rejection_reasons"] == [
        "completion_owned_by_signed_worker_finalizer"
    ]
    reservation = agent_db.get_independent_assurance_reservation("assurance-1")
    assert reservation["reservation"]["status"] == "RESERVED"


def test_signed_worker_finalization_atomically_completes_assurance_and_ledger(
    agent_db: AgentDB,
) -> None:
    admitted, result_context = _prepare_assurance_finalization(agent_db)
    completion = result_context["signed_worker_task_last_result"][
        "assurance_completion_request"
    ]

    finalized = finalize_signed_worker_execution(
        agent_db,
        "verifier-task",
        context=admitted,
        accepted=True,
        result_context=result_context,
        assurance_completion=completion,
    )

    assert finalized is True
    task = agent_db.get_autonomous_task_by_id("verifier-task")
    assert task is not None and task["status"] == "completed"
    reservation = agent_db.get_independent_assurance_reservation("assurance-1")
    assert reservation is not None
    assert reservation["reservation"]["status"] == "VERIFIED"
    rows = agent_db.db.execute_query(
        "SELECT attempt_sequence FROM agents_signed_worker_result_history "
        "WHERE task_id = ?",
        ("verifier-task",),
    )
    assert [row["attempt_sequence"] for row in rows] == [1]


def test_assurance_and_task_roll_back_when_result_ledger_rejects(
    agent_db: AgentDB,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    admitted, result_context = _prepare_assurance_finalization(agent_db)
    completion = result_context["signed_worker_task_last_result"][
        "assurance_completion_request"
    ]
    monkeypatch.setattr(
        "modules.infrastructure.database.src.signed_worker_execution_store."
        "persist_result_history_ledger",
        lambda *_args, **_kwargs: False,
    )

    finalized = finalize_signed_worker_execution(
        agent_db,
        "verifier-task",
        context=admitted,
        accepted=True,
        result_context=result_context,
        assurance_completion=completion,
    )

    assert finalized is False
    task = agent_db.get_autonomous_task_by_id("verifier-task")
    assert task is not None and task["status"] == "executing"
    reservation = agent_db.get_independent_assurance_reservation("assurance-1")
    assert reservation is not None
    assert reservation["reservation"]["status"] == "RESERVED"
    rows = agent_db.db.execute_query(
        "SELECT task_id FROM agents_signed_worker_result_history "
        "WHERE task_id = ?",
        ("verifier-task",),
    )
    assert rows == []


def test_assurance_task_rejects_missing_or_tampered_completion_request(
    agent_db: AgentDB,
) -> None:
    admitted, result_context = _prepare_assurance_finalization(agent_db)
    completion = dict(
        result_context["signed_worker_task_last_result"][
            "assurance_completion_request"
        ]
    )

    assert finalize_signed_worker_execution(
        agent_db,
        "verifier-task",
        context=admitted,
        accepted=True,
        result_context=result_context,
    ) is False
    completion["terminal_receipt_digest"] = "sha256:" + "f" * 64
    assert finalize_signed_worker_execution(
        agent_db,
        "verifier-task",
        context=admitted,
        accepted=True,
        result_context=result_context,
        assurance_completion=completion,
    ) is False
    exact = dict(
        result_context["signed_worker_task_last_result"][
            "assurance_completion_request"
        ]
    )
    assert agent_db.db.execute_write(
        "UPDATE agents_independent_assurance_reservations "
        "SET staged_completion_json = NULL, staged_completion_digest = NULL "
        "WHERE reservation_id = ?",
        ("assurance-1",),
    ) == 1
    assert finalize_signed_worker_execution(
        agent_db,
        "verifier-task",
        context=admitted,
        accepted=True,
        result_context=result_context,
        assurance_completion=exact,
    ) is False
    reservation = agent_db.get_independent_assurance_reservation("assurance-1")
    assert reservation is not None
    assert reservation["reservation"]["status"] == "RESERVED"


def test_attacker_recomputed_result_cannot_replace_staged_assurance(
    agent_db: AgentDB,
) -> None:
    admitted, legitimate_context = _prepare_assurance_finalization(agent_db)
    forged = dict(
        legitimate_context["signed_worker_task_last_result"][
            "assurance_completion_request"
        ]
    )
    forged["terminal_receipt_digest"] = "sha256:" + "f" * 64
    forged_receipt = build_signed_worker_task_result_receipt(
        base_context=admitted,
        claim_status="ACCEPT",
        result={
            "accepted": True,
            "decision": "VERIFIED",
            "receipt_id": "attacker-recomputed-result",
            "capability": "independent_slice_verification",
        },
        runner_result={
            "accepted": True,
            "bootstrap_result": {
                "assurance_completion_request": forged,
            },
        },
    )
    forged_context = append_signed_worker_result_history(
        admitted,
        forged_receipt,
    )

    finalized = finalize_signed_worker_execution(
        agent_db,
        "verifier-task",
        context=admitted,
        accepted=True,
        result_context=forged_context,
        assurance_completion=forged,
    )

    assert finalized is False
    task = agent_db.get_autonomous_task_by_id("verifier-task")
    assert task is not None and task["status"] == "executing"
    reservation = agent_db.get_independent_assurance_reservation("assurance-1")
    assert reservation is not None
    assert reservation["reservation"]["status"] == "RESERVED"


def test_finalizer_rejects_authenticated_capability_reclassification(
    agent_db: AgentDB,
) -> None:
    admitted, _legitimate_context = _prepare_assurance_finalization(agent_db)
    reclassified = {
        **admitted,
        "capability": "candidate_queue_review",
    }
    receipt = build_signed_worker_task_result_receipt(
        base_context=reclassified,
        claim_status="ACCEPT",
        result={
            "accepted": True,
            "decision": "COMPLETE",
            "receipt_id": "reclassified-result",
            "capability": "candidate_queue_review",
        },
    )
    result_context = append_signed_worker_result_history(
        reclassified,
        receipt,
    )

    assert finalize_signed_worker_execution(
        agent_db,
        "verifier-task",
        context=admitted,
        accepted=True,
        result_context=result_context,
    ) is False
    task = agent_db.get_autonomous_task_by_id("verifier-task")
    assert task is not None and task["status"] == "executing"
    assert task["context"]["capability"] == "independent_slice_verification"
    reservation = agent_db.get_independent_assurance_reservation("assurance-1")
    assert reservation is not None
    assert reservation["reservation"]["status"] == "RESERVED"
    rows = agent_db.db.execute_query(
        "SELECT task_id FROM agents_signed_worker_result_history "
        "WHERE task_id = ?",
        ("verifier-task",),
    )
    assert rows == []


def test_signed_envelope_assurance_cannot_be_hidden_by_top_level_context(
    agent_db: AgentDB,
) -> None:
    admitted, result_context = _prepare_assurance_finalization(
        agent_db,
        top_level_capability="candidate_queue_review",
        envelope_capability="independent_slice_verification",
    )

    assert finalize_signed_worker_execution(
        agent_db,
        "verifier-task",
        context=admitted,
        accepted=True,
        result_context=result_context,
    ) is False
    task = agent_db.get_autonomous_task_by_id("verifier-task")
    assert task is not None and task["status"] == "executing"
    reservation = agent_db.get_independent_assurance_reservation("assurance-1")
    assert reservation is not None
    assert reservation["reservation"]["status"] == "RESERVED"


@pytest.mark.parametrize(
    ("accepted", "target_status", "terminal_status"),
    (
        (True, "pending", "VERIFIED"),
        (False, "failed", "VERIFIED"),
        (True, "completed", "REJECT"),
    ),
)
def test_finalizer_rejects_contradictory_assurance_terminal_state(
    agent_db: AgentDB,
    accepted: bool,
    target_status: str,
    terminal_status: str,
) -> None:
    admitted, result_context = _prepare_assurance_finalization(agent_db)
    completion = dict(
        result_context["signed_worker_task_last_result"][
            "assurance_completion_request"
        ]
    )
    completion["terminal_status"] = terminal_status

    assert finalize_signed_worker_execution(
        agent_db,
        "verifier-task",
        context=admitted,
        accepted=accepted,
        result_context=result_context,
        target_status=target_status,
        assurance_completion=completion,
    ) is False
    task = agent_db.get_autonomous_task_by_id("verifier-task")
    assert task is not None and task["status"] == "executing"
    reservation = agent_db.get_independent_assurance_reservation("assurance-1")
    assert reservation is not None
    assert reservation["reservation"]["status"] == "RESERVED"


def test_finalizer_rejects_receipt_status_contradiction(
    agent_db: AgentDB,
) -> None:
    admitted, result_context = _prepare_assurance_finalization(agent_db)
    completion = result_context["signed_worker_task_last_result"][
        "assurance_completion_request"
    ]
    result_context["signed_worker_task_last_result"] = {
        **result_context["signed_worker_task_last_result"],
        "accepted": False,
        "claim_status": "REJECT",
    }

    assert finalize_signed_worker_execution(
        agent_db,
        "verifier-task",
        context=admitted,
        accepted=True,
        result_context=result_context,
        assurance_completion=completion,
    ) is False
    task = agent_db.get_autonomous_task_by_id("verifier-task")
    assert task is not None and task["status"] == "executing"
    reservation = agent_db.get_independent_assurance_reservation("assurance-1")
    assert reservation is not None
    assert reservation["reservation"]["status"] == "RESERVED"


def test_revoked_reservation_is_terminal_and_verifier_is_cancelled(
    agent_db: AgentDB,
) -> None:
    _seed_tasks(agent_db)
    assert agent_db.reserve_independent_assurance(_request())["accepted"] is True

    revoked = agent_db.revoke_independent_assurance(
        "assurance-1",
        reason="authority_revoked",
        now_iso=_iso(),
    )
    loaded = agent_db.get_independent_assurance_reservation("assurance-1")

    assert revoked["accepted"] is True
    assert revoked["status"] == "REVOKED"
    assert loaded is not None
    assert loaded["accepted"] is False
    assert loaded["status"] == "REVOKED"
    assert agent_db.get_autonomous_task_by_id("verifier-task")["status"] == "cancelled"


def test_revocation_cancels_an_executing_signed_verifier(
    agent_db: AgentDB,
) -> None:
    task_id, _ = _prepare_signed_verifier_recovery(
        agent_db,
        terminal_status="REJECT",
    )

    revoked = agent_db.revoke_independent_assurance(
        "assurance-1",
        reason="authority_revoked_during_execution",
        now_iso=_iso(),
    )

    assert revoked["accepted"] is True
    task = agent_db.get_autonomous_task_by_id(task_id)
    assert task is not None and task["status"] == "cancelled"
    reservation = agent_db.get_independent_assurance_reservation("assurance-1")
    assert reservation is not None
    assert reservation["reservation"]["status"] == "REVOKED"


def test_get_expires_elapsed_reservation_and_verifier_task(
    agent_db: AgentDB,
) -> None:
    _seed_tasks(agent_db)
    assert agent_db.reserve_independent_assurance(
        _request(expires_at=_iso(1))
    )["accepted"] is True
    agent_db.db.execute_write(
        "UPDATE agents_independent_assurance_reservations SET expires_at = ? "
        "WHERE reservation_id = ?",
        (_iso(-1), "assurance-1"),
    )

    loaded = agent_db.get_independent_assurance_reservation("assurance-1")

    assert loaded is not None
    assert loaded["accepted"] is False
    assert loaded["status"] == "EXPIRED"
    assert agent_db.get_autonomous_task_by_id("verifier-task")["status"] == "expired"


def test_expired_reservation_renews_after_author_completes(
    agent_db: AgentDB,
) -> None:
    _seed_tasks(agent_db)
    admitted = agent_db.reserve_independent_assurance(_request())
    assert admitted["accepted"] is True
    admission_digest = admitted["reservation"]["reservation_digest"]
    assert agent_db.complete_autonomous_task("author-task")
    agent_db.db.execute_write(
        "UPDATE agents_independent_assurance_reservations SET expires_at = ? "
        "WHERE reservation_id = ?",
        (_iso(-1), "assurance-1"),
    )
    expired = agent_db.get_independent_assurance_reservation("assurance-1")
    assert expired is not None
    assert expired["status"] == "EXPIRED"

    renewal = build_assurance_renewal_request(
        expired["reservation"],
        now=datetime.now(timezone.utc),
    )
    renewed = agent_db.renew_independent_assurance(renewal)

    assert renewed["accepted"] is True
    reservation = renewed["reservation"]
    assert reservation["status"] == "RESERVED"
    assert reservation["renewal_count"] == 1
    assert reservation["admission_reservation_digest"] == admission_digest
    assert reservation["reservation_digest"] != admission_digest
    verifier = agent_db.get_autonomous_task_by_id("verifier-task")
    assert verifier is not None
    assert verifier["status"] == "assigned"
    assert verifier["completed_at"] is None


def test_renewal_cannot_extend_beyond_total_admission_horizon(
    agent_db: AgentDB,
) -> None:
    _seed_tasks(agent_db)
    assert agent_db.reserve_independent_assurance(_request())["accepted"] is True
    assert agent_db.complete_autonomous_task("author-task")
    agent_db.db.execute_write(
        """
        UPDATE agents_independent_assurance_reservations
        SET expires_at = ?, admission_reserved_at = ?
        WHERE reservation_id = ?
        """,
        (_iso(-1), _iso(-7201), "assurance-1"),
    )
    expired = agent_db.get_independent_assurance_reservation("assurance-1")
    assert expired is not None

    renewed = agent_db.renew_independent_assurance(
        build_assurance_renewal_request(
            expired["reservation"],
            now=datetime.now(timezone.utc),
        )
    )

    assert renewed["accepted"] is False
    assert renewed["rejection_reasons"] == [
        "renewal_horizon_exceeds_maximum"
    ]
    assert agent_db.get_autonomous_task_by_id("verifier-task")["status"] == "expired"


def test_expired_reservation_cannot_renew_before_author_completes(
    agent_db: AgentDB,
) -> None:
    _seed_tasks(agent_db)
    assert agent_db.reserve_independent_assurance(_request())["accepted"] is True
    agent_db.db.execute_write(
        "UPDATE agents_independent_assurance_reservations SET expires_at = ? "
        "WHERE reservation_id = ?",
        (_iso(-1), "assurance-1"),
    )
    expired = agent_db.get_independent_assurance_reservation("assurance-1")
    assert expired is not None

    renewed = agent_db.renew_independent_assurance(
        build_assurance_renewal_request(
            expired["reservation"],
            now=datetime.now(timezone.utc),
        )
    )

    assert renewed["accepted"] is False
    assert renewed["rejection_reasons"] == ["author_task_not_completed"]
    assert agent_db.get_autonomous_task_by_id("verifier-task")["status"] == "expired"


def test_renewal_rejects_forged_digest(agent_db: AgentDB) -> None:
    _seed_tasks(agent_db)
    assert agent_db.reserve_independent_assurance(_request())["accepted"] is True
    assert agent_db.complete_autonomous_task("author-task")
    agent_db.db.execute_write(
        "UPDATE agents_independent_assurance_reservations SET expires_at = ? "
        "WHERE reservation_id = ?",
        (_iso(-1), "assurance-1"),
    )
    expired = agent_db.get_independent_assurance_reservation("assurance-1")
    assert expired is not None
    request = build_assurance_renewal_request(
        expired["reservation"],
        now=datetime.now(timezone.utc),
    )
    request["reservation_digest"] = "sha256:" + "0" * 64

    renewed = agent_db.renew_independent_assurance(request)

    assert renewed["accepted"] is False
    assert renewed["rejection_reasons"] == ["reservation_digest_mismatch"]


def test_reservation_rejects_lease_longer_than_six_hours(
    agent_db: AgentDB,
) -> None:
    _seed_tasks(agent_db)

    result = agent_db.reserve_independent_assurance(
        _request(expires_at=_iso((6 * 60 * 60) + 60))
    )

    assert result["accepted"] is False
    assert result["rejection_reasons"] == [
        "reservation_window_exceeds_maximum"
    ]


def test_expiry_rolls_back_if_verifier_task_state_was_tampered(
    agent_db: AgentDB,
) -> None:
    _seed_tasks(agent_db)
    assert agent_db.reserve_independent_assurance(_request())["accepted"] is True
    agent_db.db.execute_write(
        "UPDATE agents_independent_assurance_reservations SET expires_at = ? "
        "WHERE reservation_id = ?",
        (_iso(-1), "assurance-1"),
    )
    agent_db.db.execute_write(
        "UPDATE agents_autonomous_tasks SET status = 'completed' WHERE task_id = ?",
        ("verifier-task",),
    )

    loaded = agent_db.get_independent_assurance_reservation("assurance-1")

    assert loaded is not None
    assert loaded["accepted"] is False
    assert loaded["rejection_reasons"] == [
        "verifier_task_expiration_transition_failed"
    ]
    row = agent_db.db.execute_query(
        "SELECT status FROM agents_independent_assurance_reservations "
        "WHERE reservation_id = ?",
        ("assurance-1",),
    )
    assert row[0]["status"] == "RESERVED"


def test_legacy_autonomous_tasks_gain_nullable_retry_not_before(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = tmp_path / "legacy-assurance.db"
    connection = sqlite3.connect(db_path)
    connection.execute(
        """
        CREATE TABLE agents_autonomous_tasks (
            task_id TEXT PRIMARY KEY,
            description TEXT,
            required_skills JSON,
            estimated_complexity REAL,
            priority_score REAL,
            discovered_by TEXT DEFAULT 'autonomous_discovery',
            discovered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            context JSON,
            assigned_to TEXT,
            assigned_at DATETIME
        )
        """
    )
    connection.execute(
        """
        INSERT INTO agents_autonomous_tasks (
            task_id, description, required_skills, estimated_complexity, priority_score
        ) VALUES ('legacy-task', 'legacy', '[]', 0.1, 1.0)
        """
    )
    connection.commit()
    connection.close()

    monkeypatch.setenv("FOUNDUPS_DB_ENGINE", "sqlite")
    monkeypatch.setenv("FOUNDUPS_DB_PATH", str(db_path))
    DatabaseManager.reset_for_tests()
    migrated = AgentDB()

    column_info = migrated.db.get_table_info("agents_autonomous_tasks")
    columns = {row["name"] for row in column_info}
    assert "retry_not_before" in columns
    retry_column = next(
        row for row in column_info if row["name"] == "retry_not_before"
    )
    assert retry_column["type"].upper() == "TIMESTAMP"
    task = migrated.get_autonomous_task_by_id("legacy-task")
    assert task is not None
    assert task["retry_not_before"] is None


def test_legacy_assurance_table_gains_staging_columns(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = tmp_path / "legacy-assurance-staging.db"
    connection = sqlite3.connect(db_path)
    connection.execute(
        """
        CREATE TABLE agents_independent_assurance_reservations (
            reservation_id TEXT PRIMARY KEY,
            status TEXT NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            reservation_digest TEXT NOT NULL,
            reserved_at TIMESTAMP NOT NULL
        )
        """
    )
    connection.commit()
    connection.close()

    monkeypatch.setenv("FOUNDUPS_DB_ENGINE", "sqlite")
    monkeypatch.setenv("FOUNDUPS_DB_PATH", str(db_path))
    DatabaseManager.reset_for_tests()
    migrated = AgentDB()

    columns = {
        row["name"]
        for row in migrated.db.get_table_info(
            "agents_independent_assurance_reservations"
        )
    }
    assert {
        "admission_reservation_digest",
        "admission_reserved_at",
        "renewal_count",
        "staged_completion_json",
        "staged_completion_digest",
        "staged_at",
    } <= columns


def test_fresh_schema_contains_dedicated_assurance_table(agent_db: AgentDB) -> None:
    columns = {
        row["name"]
        for row in agent_db.db.get_table_info(
            "agents_independent_assurance_reservations"
        )
    }
    assert {
        "reservation_id",
        "request_schema_version",
        "work_order_id",
        "queue_item_id",
        "author_task_id",
        "author_principal_id",
        "verifier_task_id",
        "verifier_principal_id",
        "capability",
        "worker_runtime",
        "operational_snapshot_id",
        "wsp15_allocation_receipt_id",
        "lease_id",
        "reserved_at",
        "expires_at",
        "reservation_digest",
        "admission_reservation_digest",
        "admission_reserved_at",
        "renewal_count",
        "status",
        "terminal_receipt_id",
        "terminal_receipt_digest",
        "terminal_status",
        "staged_completion_json",
        "staged_completion_digest",
        "staged_at",
        "completed_at",
        "revoked_at",
        "revocation_reason",
    } <= columns
    autonomous_columns = agent_db.db.get_table_info("agents_autonomous_tasks")
    retry_column = next(
        row for row in autonomous_columns if row["name"] == "retry_not_before"
    )
    assert retry_column["type"].upper() == "TIMESTAMP"
