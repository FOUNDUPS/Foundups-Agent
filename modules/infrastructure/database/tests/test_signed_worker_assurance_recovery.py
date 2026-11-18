"""Independent-assurance recovery and quarantine regressions."""
# ruff: noqa: F405 - names are supplied by the shared split-test namespace.

from modules.infrastructure.database.tests.signed_worker_assurance_test_support import *  # noqa: F403, F405

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

    assert recovery["accepted"] is True
    assert recovery["quarantined_task_ids"] == [task_id]
    task = restarted.get_autonomous_task_by_id(task_id)
    assert task is not None and task["status"] == "quarantined"
    reservation = restarted.get_independent_assurance_reservation("assurance-1")
    assert reservation is not None
    assert reservation["reservation"]["status"] == "QUARANTINED"
    assert reservation["reservation"]["terminal_status"] == "INDETERMINATE"
    assert restarted.db.execute_query(
        "SELECT * FROM agents_signed_worker_result_history WHERE task_id = ?",
        (task_id,),
    ) == []
    repeated = recover_expired_signed_worker_executions(
        restarted,
        now_factory=lambda: (
            claimed_at + timedelta(seconds=EXECUTION_LEASE_SECONDS + 2)
        ),
    )
    assert repeated["quarantined_task_ids"] == []
    expiration = restarted.expire_independent_assurance_reservations(
        now_iso=(claimed_at + timedelta(days=1)).isoformat(),
    )
    assert expiration["accepted"] is True
    assert expiration["expired_reservation_ids"] == []

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

    assert recovery["accepted"] is True
    assert recovery["quarantined_task_ids"] == [task_id]
    task = restarted.get_autonomous_task_by_id(task_id)
    assert task is not None and task["status"] == "quarantined"
    reservation = restarted.get_independent_assurance_reservation("assurance-1")
    assert reservation is not None
    assert reservation["reservation"]["status"] == "QUARANTINED"
    assert reservation["reservation"]["terminal_status"] == "INDETERMINATE"
    assert restarted.db.execute_query(
        "SELECT * FROM agents_signed_worker_result_history WHERE task_id = ?",
        (task_id,),
    ) == []

def test_restart_quarantines_verifier_without_staged_completion(
    agent_db: AgentDB,
) -> None:
    task_id, claimed_at = _prepare_signed_verifier_recovery(
        agent_db,
        terminal_status="REJECT",
    )
    assert agent_db.db.execute_write(
        "UPDATE agents_independent_assurance_reservations "
        "SET staged_completion_json = NULL, staged_completion_digest = NULL, "
        "staged_at = NULL WHERE reservation_id = ?",
        ("assurance-1",),
    ) == 1

    recovery = recover_expired_signed_worker_executions(
        agent_db,
        now_factory=lambda: (
            claimed_at + timedelta(seconds=EXECUTION_LEASE_SECONDS + 1)
        ),
    )

    assert recovery["accepted"] is True
    assert recovery["quarantined_task_ids"] == [task_id]
    assert agent_db.get_autonomous_task_by_id(task_id)["status"] == "quarantined"
    reservation = agent_db.get_independent_assurance_reservation("assurance-1")
    assert reservation is not None
    assert reservation["reservation"]["status"] == "QUARANTINED"
    assert reservation["reservation"]["terminal_status"] == "INDETERMINATE"
    assert agent_db.db.execute_query(
        "SELECT * FROM agents_signed_worker_result_history WHERE task_id = ?",
        (task_id,),
    ) == []

def test_concurrent_verifier_quarantine_is_idempotent(
    agent_db: AgentDB,
) -> None:
    task_id, claimed_at = _prepare_signed_verifier_recovery(
        agent_db,
        terminal_status="VERIFIED",
    )
    recovered_at = claimed_at + timedelta(
        seconds=EXECUTION_LEASE_SECONDS + 1
    )

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(
                lambda _: recover_expired_signed_worker_executions(
                    AgentDB(),
                    now_factory=lambda: recovered_at,
                ),
                range(2),
            )
        )

    assert all(result["accepted"] is True for result in results)
    assert agent_db.get_autonomous_task_by_id(task_id)["status"] == "quarantined"
    reservation = agent_db.get_independent_assurance_reservation("assurance-1")
    assert reservation is not None
    assert reservation["reservation"]["status"] == "QUARANTINED"
    assert agent_db.db.execute_query(
        "SELECT * FROM agents_signed_worker_result_history WHERE task_id = ?",
        (task_id,),
    ) == []

def test_recomputed_quarantine_marker_cannot_reconcile_verifier_reservation(
    agent_db: AgentDB,
) -> None:
    task_id, claimed_at = _prepare_signed_verifier_recovery(
        agent_db,
        terminal_status="VERIFIED",
    )
    task = agent_db.get_autonomous_task_by_id(task_id)
    assert task is not None
    forged = {
        "schema_version": QUARANTINE_SCHEMA,
        "task_id": task_id,
        "reason": "attacker_selected",
        "quarantined_at": claimed_at.isoformat(),
        "effect_commit_state": "INDETERMINATE",
        "no_worker_effect_replayed": True,
    }
    encoded = json.dumps(
        forged,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("ascii")
    forged["receipt_id"] = "sha256:" + hashlib.sha256(encoded).hexdigest()
    context = dict(task["context"])
    context["signed_worker_execution_quarantine"] = forged
    assert agent_db.db.execute_write(
        "UPDATE agents_autonomous_tasks SET status = 'quarantined', context = ? "
        "WHERE task_id = ? AND status = 'executing'",
        (json.dumps(context, sort_keys=True), task_id),
    ) == 1

    outcome = quarantine_signed_worker_execution(
        agent_db,
        task_id=task_id,
        raw_context=task["context"],
        expected_status="executing",
        reason="reconcile_existing_quarantine",
        now_iso=(claimed_at + timedelta(seconds=1)).isoformat(),
    )

    assert outcome == "REJECTED"
    reservation = agent_db.get_independent_assurance_reservation("assurance-1")
    assert reservation is not None
    assert reservation["reservation"]["status"] == "RESERVED"
    assert reservation["reservation"]["terminal_status"] is None
    assert agent_db.db.execute_query(
        "SELECT * FROM agents_signed_worker_result_history WHERE task_id = ?",
        (task_id,),
    ) == []

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
