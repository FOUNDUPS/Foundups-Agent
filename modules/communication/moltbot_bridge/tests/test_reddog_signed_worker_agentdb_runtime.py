"""Signed-worker direct runtime, assignment, lease, and recovery regressions."""
# ruff: noqa: F405 - names are supplied by the shared split-test namespace.

from modules.communication.moltbot_bridge.tests.reddog_signed_worker_agentdb_test_support import *  # noqa: F403, F405

def test_run_task_rebuilds_canonical_context_before_runner_selection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task_id = _publish_agentdb_task()
    _rewrite_context(
        task_id,
        lambda context: context.update(
            {
                "worker_runtime": "hermes",
                "worker_role": "attacker",
                "capability": "unbounded_repo_write",
                "worker_dispatch_intent": {
                    **dict(context["worker_dispatch_intent"]),
                    "worker_runtime": "hermes",
                    "role": "attacker",
                    "capability": "unbounded_repo_write",
                },
            }
        ),
    )
    db = AgentDB()
    assert db.assign_signed_worker_task(task_id)
    monkeypatch.setenv("WRE_MOCK_SKILLS", runtime.SIGNED_WORKER_DISPATCH_TASK_SKILL)
    runner = _FakeRunner()

    result = execute_task(
        task_id,
        repo_root=tmp_path,
        signed_worker_runner=runner,
    )

    assert result["ok"] is True
    assert len(runner.calls) == 1
    canonical = runner.calls[0]["task_context"]
    assert canonical["worker_runtime"] == "openclaw"
    assert canonical["worker_role"] == "openclaw_candidate"
    assert canonical["capability"] == "candidate_queue_review"
    stored = AgentDB().get_autonomous_task_by_id(task_id)
    assert stored is not None and stored["status"] == "completed"
    assert stored["context"]["worker_runtime"] == "openclaw"
    assert stored["context"]["worker_role"] == "openclaw_candidate"
    assert stored["context"]["capability"] == "candidate_queue_review"

def test_run_task_signed_success_uses_exact_finalization_cas(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task_id = _publish_agentdb_task()
    db = AgentDB()
    assert db.assign_signed_worker_task(task_id)
    monkeypatch.setattr(
        AgentDB,
        "complete_autonomous_task",
        lambda *_args, **_kwargs: pytest.fail("generic finalizer used"),
    )
    runner = _FakeRunner()

    result = execute_task(
        task_id,
        repo_root=tmp_path,
        signed_worker_runner=runner,
    )

    stored = AgentDB().get_autonomous_task_by_id(task_id)
    assert result["ok"] is True
    assert result["finalization_owned"] is True
    assert stored is not None and stored["status"] == "completed"

def test_generic_completion_rejects_reserved_signed_worker_namespace() -> None:
    task_id = _publish_agentdb_task()
    db = AgentDB()

    assert db.complete_autonomous_task(task_id) is False

    stored = db.get_autonomous_task_by_id(task_id)
    assert stored is not None and stored["status"] == "pending"
    assert "signed_worker_execution_claim" not in stored["context"]

def test_direct_run_preserves_requeue_lifecycle(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task_id = _publish_agentdb_task()
    db = AgentDB()
    assert db.assign_signed_worker_task(task_id)
    monkeypatch.setenv("WRE_MOCK_SKILLS", runtime.SIGNED_WORKER_DISPATCH_TASK_SKILL)

    result = execute_task(
        task_id,
        repo_root=tmp_path,
        signed_worker_runner=_FakeRunner(requeue_required=True),
    )

    stored = db.get_autonomous_task_by_id(task_id)
    assert result["ok"] is True
    assert stored is not None and stored["status"] == "pending"
    assert stored["assigned_to"] is None
    receipt = stored["context"]["signed_worker_task_last_result"]
    assert receipt["claim_status"] == "DIRECT_REQUEUED"
    assert receipt["runner_result_summary"]["queue_chain_requeue_required"] is True
    assert db.db.execute_query(
        "SELECT attempt_sequence FROM agents_signed_worker_result_history "
        "WHERE task_id = ?",
        (task_id,),
    ) == [{"attempt_sequence": 1}]

def test_run_task_post_claim_exception_fails_through_exact_cas(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task_id = _publish_agentdb_task()
    db = AgentDB()
    assert db.assign_signed_worker_task(task_id)
    monkeypatch.setattr(
        run_task_runtime,
        "_runner",
        lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("binding-failed")),
    )

    result = execute_task(task_id, repo_root=tmp_path)

    stored = AgentDB().get_autonomous_task_by_id(task_id)
    assert result["ok"] is False
    assert result["finalization_owned"] is True
    assert "dispatch_error:RuntimeError" in result["detail"]
    assert stored is not None and stored["status"] == "failed"

def test_run_task_finalization_conflict_never_overwrites_concurrent_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task_id = _publish_agentdb_task()
    db = AgentDB()
    assert db.assign_signed_worker_task(task_id)
    original = run_task_runtime.finalize_signed_worker_execution

    def conflict(
        db, selected_task_id, *, context, accepted, result_context, **kwargs
    ):
        assert db.db.execute_write(
            "UPDATE agents_autonomous_tasks SET status = 'cancelled' "
            "WHERE task_id = ? AND status = 'executing'",
            (selected_task_id,),
        ) == 1
        return original(
            db,
            selected_task_id,
            context=context,
            accepted=accepted,
            result_context=result_context,
            **kwargs,
        )

    monkeypatch.setattr(
        run_task_runtime, "finalize_signed_worker_execution", conflict
    )
    result = execute_task(
        task_id,
        repo_root=tmp_path,
        signed_worker_runner=_FakeRunner(),
    )

    stored = AgentDB().get_autonomous_task_by_id(task_id)
    assert result["ok"] is False
    assert result["finalization_owned"] is True
    assert result["detail"] == "reddog_signed_worker_finalization_conflict"
    assert stored is not None and stored["status"] == "cancelled"
    rows = db.db.execute_query(
        "SELECT task_id FROM agents_signed_worker_result_history "
        "WHERE task_id = ?",
        (task_id,),
    )
    assert rows == []

def test_execution_claim_consumes_token_without_persisting_raw_value() -> None:
    task_id = _publish_agentdb_task()
    db = AgentDB()
    assert db.assign_signed_worker_task(task_id)

    admission = admit_signed_worker_execution_once(
        db=db,
        task_id=task_id,
        token_factory=lambda: "raw-use-token-must-not-persist",
    )

    assert admission is not None
    task = db.get_autonomous_task_by_id(task_id)
    assert task is not None and task["status"] == "executing"
    serialized = json.dumps(task["context"], sort_keys=True)
    assert "raw-use-token-must-not-persist" not in serialized
    assert admission.claim_receipt["status"] == "CLAIMED"
    assert admission.use_receipt["status"] == "CONSUMED"
    assert admission.claim_receipt["token_digest"].startswith("sha256:")
    assert admission.use_receipt["token_digest"] == (
        admission.claim_receipt["token_digest"]
    )
    assert admit_signed_worker_execution_once(db=db, task_id=task_id) is None

def test_restart_recovers_expired_execution_without_replaying_worker() -> None:
    task_id = _publish_agentdb_task()
    db = AgentDB()
    assert db.assign_signed_worker_task(task_id)
    claimed_at = datetime(2026, 7, 28, tzinfo=timezone.utc)
    admission = admit_signed_worker_execution_once(
        db=db,
        task_id=task_id,
        now_factory=lambda: claimed_at,
    )
    assert admission is not None
    assert admission.claim_receipt["lease_expires_at"] == (
        claimed_at + timedelta(seconds=EXECUTION_LEASE_SECONDS)
    ).isoformat()

    DatabaseManager.reset_for_tests()
    restarted = AgentDB()
    recovered = recover_expired_signed_worker_executions(
        restarted,
        now_factory=lambda: (
            claimed_at
            + timedelta(seconds=EXECUTION_LEASE_SECONDS + 1)
        ),
    )

    assert recovered["accepted"] is True
    assert recovered["recovered_task_ids"] == [task_id]
    assert recovered["no_worker_effect_replayed"] is True
    stored = restarted.get_autonomous_task_by_id(task_id)
    assert stored is not None and stored["status"] == "failed"
    receipt = stored["context"]["signed_worker_task_last_result"]
    assert receipt["decision"] == "EXECUTION_LEASE_RECOVERED"
    assert receipt["accepted"] is False
    assert receipt["effect_commit_state"] == "INDETERMINATE"
    assert receipt["no_source_repo_mutation_performed"] is False
    rows = restarted.db.execute_query(
        "SELECT attempt_sequence FROM agents_signed_worker_result_history "
        "WHERE task_id = ?",
        (task_id,),
    )
    assert rows == [{"attempt_sequence": 1}]

    repeated = recover_expired_signed_worker_executions(
        restarted,
        now_factory=lambda: (
            claimed_at
            + timedelta(seconds=EXECUTION_LEASE_SECONDS + 2)
        ),
    )
    assert repeated["accepted"] is True
    assert repeated["recovered_task_ids"] == []

def test_unexpired_execution_is_not_recovered() -> None:
    task_id = _publish_agentdb_task()
    db = AgentDB()
    assert db.assign_signed_worker_task(task_id)
    claimed_at = datetime(2026, 7, 28, tzinfo=timezone.utc)
    assert admit_signed_worker_execution_once(
        db=db,
        task_id=task_id,
        now_factory=lambda: claimed_at,
    ) is not None

    result = recover_expired_signed_worker_executions(
        db,
        now_factory=lambda: claimed_at + timedelta(seconds=30),
    )

    assert result["accepted"] is True
    assert result["recovered_task_ids"] == []
    stored = db.get_autonomous_task_by_id(task_id)
    assert stored is not None and stored["status"] == "executing"

def test_dedicated_assignment_uses_task_bound_principal() -> None:
    task_id = _publish_agentdb_task()
    db = AgentDB()
    before = db.get_autonomous_task_by_id(task_id)

    assert before is not None and before["status"] == "pending"
    assert not db.assign_autonomous_task(task_id, "attacker")
    assert db.get_autonomous_task_by_id(task_id) == before
    assert db.assign_signed_worker_task(task_id)

    assigned = db.get_autonomous_task_by_id(task_id)
    assert assigned is not None and assigned["status"] == "assigned"
    assert assigned["assigned_to"] == canonical_signed_worker_principal_id(
        task_id
    )

def test_restart_requeues_stale_assignment_before_execution_admission() -> None:
    task_id = _publish_agentdb_task()
    db = AgentDB()
    assert db.assign_signed_worker_task(task_id)
    assigned_at = datetime(2026, 7, 28, tzinfo=timezone.utc)
    assert db.db.execute_write(
        "UPDATE agents_autonomous_tasks SET assigned_at = ? WHERE task_id = ?",
        (assigned_at.isoformat(), task_id),
    ) == 1

    recovered = recover_expired_signed_worker_executions(
        db,
        now_factory=lambda: assigned_at + timedelta(seconds=301),
    )

    assert recovered["accepted"] is True
    assert recovered["requeued_assigned_task_ids"] == [task_id]
    task = db.get_autonomous_task_by_id(task_id)
    assert task is not None and task["status"] == "pending"
    assert task["assigned_to"] is None
    assert db.assign_signed_worker_task(task_id)
    assert admit_signed_worker_execution_once(db=db, task_id=task_id) is not None

def test_stale_assignment_with_active_verifier_reservation_is_not_requeued(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task_id = _publish_agentdb_task()
    db = AgentDB()
    assert db.assign_signed_worker_task(task_id)
    assigned_at = datetime(2026, 7, 28, tzinfo=timezone.utc)
    assert db.db.execute_write(
        "UPDATE agents_autonomous_tasks SET assigned_at = ? WHERE task_id = ?",
        (assigned_at.isoformat(), task_id),
    ) == 1
    monkeypatch.setattr(
        db,
        "get_independent_assurance_reservation_for_task",
        lambda *_, **__: {"reservation": {"status": "RESERVED"}},
    )

    recovered = recover_expired_signed_worker_executions(
        db,
        now_factory=lambda: assigned_at + timedelta(seconds=301),
    )

    assert recovered["accepted"] is True
    assert recovered["requeued_assigned_task_ids"] == []
    task = db.get_autonomous_task_by_id(task_id)
    assert task is not None and task["status"] == "assigned"

def test_renewed_execution_lease_survives_initial_timeout_then_expires() -> None:
    task_id = _publish_agentdb_task()
    db = AgentDB()
    assert db.assign_signed_worker_task(task_id)
    claimed_at = datetime(2026, 7, 28, tzinfo=timezone.utc)
    admission = admit_signed_worker_execution_once(
        db=db,
        task_id=task_id,
        now_factory=lambda: claimed_at,
    )
    assert admission is not None
    context = db.get_autonomous_task_by_id(task_id)["context"]
    assert renew_signed_worker_execution_lease(
        db,
        task_id=task_id,
        context=context,
        now=claimed_at + timedelta(seconds=600),
        extension_seconds=900,
    )

    initial_expiry = recover_expired_signed_worker_executions(
        db,
        now_factory=lambda: claimed_at
        + timedelta(seconds=EXECUTION_LEASE_SECONDS + 1),
    )
    assert initial_expiry["recovered_task_ids"] == []
    assert db.get_autonomous_task_by_id(task_id)["status"] == "executing"

    renewed_expiry = recover_expired_signed_worker_executions(
        db,
        now_factory=lambda: claimed_at + timedelta(seconds=1501),
    )
    assert renewed_expiry["recovered_task_ids"] == [task_id]
    assert db.get_autonomous_task_by_id(task_id)["status"] == "failed"

def test_execution_lease_cannot_renew_past_maximum_horizon() -> None:
    task_id = _publish_agentdb_task()
    db = AgentDB()
    assert db.assign_signed_worker_task(task_id)
    claimed_at = datetime(2026, 7, 28, tzinfo=timezone.utc)
    admission = admit_signed_worker_execution_once(
        db=db,
        task_id=task_id,
        now_factory=lambda: claimed_at,
    )
    assert admission is not None
    context = db.get_autonomous_task_by_id(task_id)["context"]
    assert renew_signed_worker_execution_lease(
        db,
        task_id=task_id,
        context=context,
        now=claimed_at + timedelta(seconds=1),
        extension_seconds=MAX_EXECUTION_LEASE_SECONDS * 2,
    )
    assert not renew_signed_worker_execution_lease(
        db,
        task_id=task_id,
        context=context,
        now=claimed_at + timedelta(seconds=MAX_EXECUTION_LEASE_SECONDS),
        extension_seconds=900,
    )

def test_execution_recovery_database_scan_failure_rejects() -> None:
    class _BrokenDatabase:
        def get_connection(self):
            raise RuntimeError("database unavailable")

    result = recover_expired_signed_worker_executions(
        SimpleNamespace(db=_BrokenDatabase()),
    )

    assert result["accepted"] is False
    assert result["rejected_task_ids"] == ["database_scan_failed"]
    assert result["no_worker_effect_replayed"] is True

def test_concurrent_expired_execution_recovery_commits_one_result() -> None:
    task_id = _publish_agentdb_task()
    db = AgentDB()
    assert db.assign_signed_worker_task(task_id)
    claimed_at = datetime(2026, 7, 28, tzinfo=timezone.utc)
    assert admit_signed_worker_execution_once(
        db=db,
        task_id=task_id,
        now_factory=lambda: claimed_at,
    ) is not None
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
    stored = db.get_autonomous_task_by_id(task_id)
    assert stored is not None and stored["status"] == "failed"
    rows = db.db.execute_query(
        "SELECT attempt_sequence FROM agents_signed_worker_result_history "
        "WHERE task_id = ?",
        (task_id,),
    )
    assert rows == [{"attempt_sequence": 1}]

def test_recovery_rejects_forged_terminal_marker_without_durable_ledger(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task_id = _publish_agentdb_task()
    db = AgentDB()
    assert db.assign_signed_worker_task(task_id)
    claimed_at = datetime(2026, 7, 28, tzinfo=timezone.utc)
    assert admit_signed_worker_execution_once(
        db=db,
        task_id=task_id,
        now_factory=lambda: claimed_at,
    ) is not None

    def forge_marker(
        database,
        selected_task_id,
        *,
        context,
        assurance_completion,
        **_kwargs,
    ):
        receipt = execution_recovery_module._lease_expiry_receipt(
            context,
            completion=assurance_completion,
        )
        forged = append_signed_worker_result_history(context, receipt)
        assert database.db.execute_write(
            "UPDATE agents_autonomous_tasks SET status = 'failed', context = ? "
            "WHERE task_id = ? AND status = 'executing'",
            (json.dumps(forged, sort_keys=True), selected_task_id),
        ) == 1
        return False

    monkeypatch.setattr(
        execution_recovery_module,
        "finalize_expired_signed_worker_execution_recovery",
        forge_marker,
    )
    result = recover_expired_signed_worker_executions(
        db,
        now_factory=lambda: (
            claimed_at + timedelta(seconds=EXECUTION_LEASE_SECONDS + 1)
        ),
    )

    assert result["accepted"] is True
    assert result["recovered_task_ids"] == []
    assert result["rejected_task_ids"] == []
    assert result["quarantined_task_ids"] == [task_id]
    stored = db.get_autonomous_task_by_id(task_id)
    assert stored is not None and stored["status"] == "quarantined"
    quarantine = stored["context"]["signed_worker_execution_quarantine"]
    assert quarantine["effect_commit_state"] == "INDETERMINATE"
    assert db.db.execute_query(
        "SELECT task_id FROM agents_signed_worker_result_history WHERE task_id = ?",
        (task_id,),
    ) == []

def test_concurrent_direct_run_task_executes_signed_worker_once(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task_id = _publish_agentdb_task()
    db = AgentDB()
    assert db.assign_signed_worker_task(task_id)
    monkeypatch.setenv("WRE_MOCK_SKILLS", runtime.SIGNED_WORKER_DISPATCH_TASK_SKILL)
    barrier = threading.Barrier(2)
    original_get = AgentDB.get_autonomous_tasks

    def synchronized_get(self, status="pending", limit=50):
        tasks = original_get(self, status=status, limit=limit)
        if status == "assigned":
            barrier.wait(timeout=5)
        return tasks

    monkeypatch.setattr(AgentDB, "get_autonomous_tasks", synchronized_get)
    runner = _FakeRunner()
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(
                lambda _: execute_task(
                    task_id,
                    repo_root=tmp_path,
                    signed_worker_runner=runner,
                ),
                range(2),
            )
        )

    assert sum(result["ok"] is True for result in results) == 1
    assert len(runner.calls) == 1
    loser = next(result for result in results if result["ok"] is False)
    assert loser["finalization_owned"] is True
    assert "execution_already_claimed" in loser["detail"]
    stored = AgentDB().get_autonomous_task_by_id(task_id)
    assert stored is not None and stored["status"] == "completed"
    assert stored["context"]["signed_worker_execution_use"]["status"] == "CONSUMED"
    rows = db.db.execute_query(
        "SELECT attempt_sequence FROM agents_signed_worker_result_history "
        "WHERE task_id = ?",
        (task_id,),
    )
    assert rows == [{"attempt_sequence": 1}]
