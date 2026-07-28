"""Signed-worker result-history and finalization regressions."""
# ruff: noqa: F405 - names are supplied by the shared split-test namespace.

from modules.communication.moltbot_bridge.tests.reddog_signed_worker_agentdb_test_support import *  # noqa: F403, F405

def test_supervisor_finalization_conflict_never_overwrites_owner(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task_id = _publish_agentdb_task()
    original_persist = (
        supervisor_module._persist_reddog_signed_worker_dispatch_task_result
    )

    def replace_owner_then_persist(db, selected_task_id, **kwargs):
        assert db.db.execute_write(
            "UPDATE agents_autonomous_tasks "
            "SET assigned_to = ?, context = ? "
            "WHERE task_id = ? AND status = 'executing'",
            ("other-worker", json.dumps({"owner": "other-worker"}), selected_task_id),
        ) == 1
        return original_persist(db, selected_task_id, **kwargs)

    monkeypatch.setattr(
        supervisor_module,
        "_persist_reddog_signed_worker_dispatch_task_result",
        replace_owner_then_persist,
    )
    result = claim_reddog_signed_worker_dispatch_task_once(
        repo_root=tmp_path,
        signed_worker_runner=_FakeRunner(),
        authority_verification_context=(
            worker_dispatch_authority_verification_context()
        ),
    )

    stored = AgentDB().get_autonomous_task_by_id(task_id)
    assert result["accepted"] is False
    assert (
        SignedWorkerOpenClawClaimReason.RESULT_PERSISTENCE_REJECTED
        in result["rejection_reasons"]
    )
    assert stored is not None and stored["status"] == "executing"
    assert stored["assigned_to"] == "other-worker"
    assert stored["context"] == {"owner": "other-worker"}

def test_supervisor_rejects_malformed_requeue_result_history(
    tmp_path: Path,
) -> None:
    task_id = _publish_agentdb_task()
    first = claim_reddog_signed_worker_dispatch_task_once(
        repo_root=tmp_path,
        signed_worker_runner=_FakeRunner(requeue_required=True),
        authority_verification_context=(
            worker_dispatch_authority_verification_context()
        ),
    )
    assert first["accepted"] is True
    second = claim_reddog_signed_worker_dispatch_task_once(
        repo_root=tmp_path,
        signed_worker_runner=_FakeRunner(requeue_required=True),
        authority_verification_context=(
            worker_dispatch_authority_verification_context()
        ),
    )
    assert second["accepted"] is True
    stored = AgentDB().get_autonomous_task_by_id(task_id)
    assert len(stored["context"]["signed_worker_task_result_receipts"]) == 2
    _rewrite_context(
        task_id,
        lambda context: context["signed_worker_task_last_result"].update(
            receipt_digest="sha256:" + ("0" * 64)
        ),
    )
    runner = _FakeRunner()
    rejected = claim_reddog_signed_worker_dispatch_task_once(
        repo_root=tmp_path,
        signed_worker_runner=runner,
        authority_verification_context=(
            worker_dispatch_authority_verification_context()
        ),
    )

    assert rejected["accepted"] is False
    assert runner.calls == []
    assert AgentDB().get_autonomous_task_by_id(task_id)["status"] == "failed"

def test_supervisor_rejects_tampered_earlier_requeue_result_history(
    tmp_path: Path,
) -> None:
    task_id = _publish_agentdb_task()
    for _ in range(2):
        result = claim_reddog_signed_worker_dispatch_task_once(
            repo_root=tmp_path,
            signed_worker_runner=_FakeRunner(requeue_required=True),
            authority_verification_context=(
                worker_dispatch_authority_verification_context()
            ),
        )
        assert result["accepted"] is True
    _rewrite_context(
        task_id,
        lambda context: context["signed_worker_task_result_receipts"][0].update(
            receipt_digest="sha256:not-a-digest"
        ),
    )
    runner = _FakeRunner()
    rejected = claim_reddog_signed_worker_dispatch_task_once(
        repo_root=tmp_path,
        signed_worker_runner=runner,
        authority_verification_context=(
            worker_dispatch_authority_verification_context()
        ),
    )

    assert rejected["accepted"] is False
    assert runner.calls == []
    assert AgentDB().get_autonomous_task_by_id(task_id)["status"] in {
        "failed",
        "pending",
    }

def test_supervisor_rejects_gapped_durable_result_ledger(
    tmp_path: Path,
) -> None:
    task_id = _publish_agentdb_task()
    for _ in range(2):
        assert claim_reddog_signed_worker_dispatch_task_once(
            repo_root=tmp_path,
            signed_worker_runner=_FakeRunner(requeue_required=True),
            authority_verification_context=(
                worker_dispatch_authority_verification_context()
            ),
        )["accepted"] is True
    db = AgentDB()
    assert db.db.execute_write(
        "UPDATE agents_signed_worker_result_history "
        "SET attempt_sequence = 3 WHERE task_id = ? AND attempt_sequence = 2",
        (task_id,),
    ) == 1
    runner = _FakeRunner()

    rejected = claim_reddog_signed_worker_dispatch_task_once(
        repo_root=tmp_path,
        signed_worker_runner=runner,
        authority_verification_context=(
            worker_dispatch_authority_verification_context()
        ),
    )

    assert rejected["accepted"] is False
    assert runner.calls == []
    assert AgentDB().get_autonomous_task_by_id(task_id)["status"] == "failed"

def test_supervisor_retains_ten_entry_tail_but_all_durable_attempts(
    tmp_path: Path,
) -> None:
    task_id = _publish_agentdb_task()
    for _ in range(11):
        assert claim_reddog_signed_worker_dispatch_task_once(
            repo_root=tmp_path,
            signed_worker_runner=_FakeRunner(requeue_required=True),
            authority_verification_context=(
                worker_dispatch_authority_verification_context()
            ),
        )["accepted"] is True
    db = AgentDB()
    stored = db.get_autonomous_task_by_id(task_id)
    assert stored is not None
    history = stored["context"]["signed_worker_task_result_receipts"]
    assert len(history) == 10
    assert history[0]["attempt_sequence"] == 2
    assert history[-1]["attempt_sequence"] == 11
    rows = db.db.execute_query(
        "SELECT attempt_sequence FROM agents_signed_worker_result_history "
        "WHERE task_id = ? ORDER BY attempt_sequence",
        (task_id,),
    )
    assert rows == [{"attempt_sequence": value} for value in range(1, 12)]

def test_preledger_context_history_is_quarantined_before_execution(
    tmp_path: Path,
) -> None:
    task_id = _publish_agentdb_task()
    db = AgentDB()
    task = db.get_autonomous_task_by_id(task_id)
    assert task is not None
    receipt = build_signed_worker_task_result_receipt(
        base_context=task["context"],
        claim_status="LEGACY_CONTEXT",
        result={"accepted": False, "decision": "legacy"},
    )
    forged = append_signed_worker_result_history(task["context"], receipt)
    assert db.db.execute_write(
        "UPDATE agents_autonomous_tasks SET context = ? WHERE task_id = ?",
        (json.dumps(forged, sort_keys=True), task_id),
    ) == 1
    runner = _FakeRunner()

    rejected = claim_reddog_signed_worker_dispatch_task_once(
        repo_root=tmp_path,
        signed_worker_runner=runner,
        authority_verification_context=(
            worker_dispatch_authority_verification_context()
        ),
    )

    assert rejected["accepted"] is False
    assert runner.calls == []
    assert db.get_autonomous_task_by_id(task_id)["status"] == "failed"
    assert db.db.execute_query(
        "SELECT task_id FROM agents_signed_worker_result_history "
        "WHERE task_id = ?",
        (task_id,),
    ) == []

def test_supervisor_rejects_fully_rehashed_result_history(
    tmp_path: Path,
) -> None:
    task_id = _publish_agentdb_task()
    for _ in range(2):
        assert claim_reddog_signed_worker_dispatch_task_once(
            repo_root=tmp_path,
            signed_worker_runner=_FakeRunner(requeue_required=True),
            authority_verification_context=(
                worker_dispatch_authority_verification_context()
            ),
        )["accepted"] is True

    def forge(context: dict[str, object]) -> None:
        history = context["signed_worker_task_result_receipts"]
        assert isinstance(history, list) and isinstance(history[0], dict)
        history[0]["receipt_digest"] = "sha256:" + ("f" * 64)
        _rechain_context_history(context)

    _rewrite_context(task_id, forge)
    runner = _FakeRunner()
    rejected = claim_reddog_signed_worker_dispatch_task_once(
        repo_root=tmp_path,
        signed_worker_runner=runner,
        authority_verification_context=(
            worker_dispatch_authority_verification_context()
        ),
    )

    assert rejected["accepted"] is False
    assert runner.calls == []
    assert AgentDB().get_autonomous_task_by_id(task_id)["status"] == "failed"

def test_direct_run_rejects_rehashed_truncated_result_history(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task_id = _publish_agentdb_task()
    for _ in range(2):
        assert claim_reddog_signed_worker_dispatch_task_once(
            repo_root=tmp_path,
            signed_worker_runner=_FakeRunner(requeue_required=True),
            authority_verification_context=(
                worker_dispatch_authority_verification_context()
            ),
        )["accepted"] is True

    def truncate(context: dict[str, object]) -> None:
        history = context["signed_worker_task_result_receipts"]
        assert isinstance(history, list)
        context["signed_worker_task_result_receipts"] = [history[-1]]
        _rechain_context_history(context)

    _rewrite_context(task_id, truncate)
    db = AgentDB()
    assert db.assign_signed_worker_task(task_id)
    monkeypatch.setenv("WRE_MOCK_SKILLS", runtime.SIGNED_WORKER_DISPATCH_TASK_SKILL)
    runner = _FakeRunner()
    result = execute_task(
        task_id,
        repo_root=tmp_path,
        signed_worker_runner=runner,
    )

    assert result["ok"] is False
    assert runner.calls == []
    assert AgentDB().get_autonomous_task_by_id(task_id)["status"] == "failed"

def test_direct_run_preserves_agentdb_anchored_result_history(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task_id = _publish_agentdb_task()
    assert claim_reddog_signed_worker_dispatch_task_once(
        repo_root=tmp_path,
        signed_worker_runner=_FakeRunner(requeue_required=True),
        authority_verification_context=(
            worker_dispatch_authority_verification_context()
        ),
    )["accepted"] is True
    db = AgentDB()
    assert db.assign_signed_worker_task(task_id)
    monkeypatch.setenv("WRE_MOCK_SKILLS", runtime.SIGNED_WORKER_DISPATCH_TASK_SKILL)

    result = execute_task(
        task_id,
        repo_root=tmp_path,
        signed_worker_runner=_FakeRunner(),
    )

    stored = AgentDB().get_autonomous_task_by_id(task_id)
    assert result["ok"] is True
    assert stored is not None and stored["status"] == "completed"
    assert len(stored["context"]["signed_worker_task_result_receipts"]) == 2
    rows = db.db.execute_query(
        "SELECT attempt_sequence FROM agents_signed_worker_result_history "
        "WHERE task_id = ?",
        (task_id,),
    )
    assert rows == [{"attempt_sequence": 1}, {"attempt_sequence": 2}]

def test_direct_result_ledger_failure_rolls_back_terminal_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task_id = _publish_agentdb_task()
    db = AgentDB()
    assert db.assign_signed_worker_task(task_id)
    monkeypatch.setenv("WRE_MOCK_SKILLS", runtime.SIGNED_WORKER_DISPATCH_TASK_SKILL)
    monkeypatch.setattr(
        execution_commit_module,
        "persist_result_history_ledger",
        lambda *_args, **_kwargs: False,
    )

    result = execute_task(
        task_id,
        repo_root=tmp_path,
        signed_worker_runner=_FakeRunner(),
    )

    stored = db.get_autonomous_task_by_id(task_id)
    assert result["ok"] is False
    assert result["detail"] == "reddog_signed_worker_finalization_conflict"
    assert stored is not None and stored["status"] == "executing"
    assert db.db.execute_query(
        "SELECT task_id FROM agents_signed_worker_result_history "
        "WHERE task_id = ?",
        (task_id,),
    ) == []

def test_public_finalizer_requires_exactly_one_new_result_entry() -> None:
    task_id = _publish_agentdb_task()
    db = AgentDB()
    assert db.assign_signed_worker_task(task_id)
    admission = admit_signed_worker_execution_once(db=db, task_id=task_id)
    assert admission is not None
    context = bind_execution_admission(admission.claimed_context, admission)

    with pytest.raises(TypeError):
        execution_store_module.finalize_signed_worker_execution(
            db,
            task_id,
            context=context,
            accepted=False,
        )
    assert execution_store_module.finalize_signed_worker_execution(
        db,
        task_id,
        context=context,
        accepted=False,
        result_context=context,
    ) is False

    stored = db.get_autonomous_task_by_id(task_id)
    assert stored is not None and stored["status"] == "executing"
    assert db.db.execute_query(
        "SELECT task_id FROM agents_signed_worker_result_history "
        "WHERE task_id = ?",
        (task_id,),
    ) == []

def test_public_finalizer_rejects_accepted_caller_selected_identity() -> None:
    task_id = _publish_agentdb_task()
    db = AgentDB()
    assert db.assign_signed_worker_task(task_id)
    admission = admit_signed_worker_execution_once(db=db, task_id=task_id)
    assert admission is not None
    authenticated = bind_execution_admission(
        admission.claimed_context,
        admission,
    )
    attacker_context = {
        **authenticated,
        "worker_role": "attacker_role",
        "worker_runtime": "hermes",
        "capability": "unbounded_repo_write",
    }
    receipt = build_signed_worker_task_result_receipt(
        base_context=attacker_context,
        claim_status="DIRECT_ACCEPT",
        result={
            "accepted": True,
            "decision": "ATTACKER_ACCEPT",
            "worker_role": "attacker_role",
            "worker_runtime": "hermes",
            "capability": "unbounded_repo_write",
        },
    )
    result_context = append_signed_worker_result_history(
        attacker_context,
        receipt,
    )

    assert execution_store_module.finalize_signed_worker_execution(
        db,
        task_id,
        context=authenticated,
        accepted=True,
        result_context=result_context,
    ) is False
    stored = db.get_autonomous_task_by_id(task_id)
    assert stored is not None and stored["status"] == "executing"
    assert stored["context"]["worker_role"] == authenticated["worker_role"]
    assert stored["context"]["worker_runtime"] == authenticated["worker_runtime"]
    assert stored["context"]["capability"] == authenticated["capability"]

def test_public_finalizer_rejects_non_genesis_first_history_link() -> None:
    task_id = _publish_agentdb_task()
    db = AgentDB()
    assert db.assign_signed_worker_task(task_id)
    admission = admit_signed_worker_execution_once(db=db, task_id=task_id)
    assert admission is not None
    context = bind_execution_admission(admission.claimed_context, admission)
    receipt = build_signed_worker_task_result_receipt(
        base_context=context,
        claim_status="FORGED_GENESIS",
        result={"accepted": False, "decision": "reject"},
    )
    result_context = append_signed_worker_result_history(context, receipt)
    entry = result_context["signed_worker_task_result_receipts"][0]
    entry["previous_history_digest"] = "sha256:" + ("f" * 64)
    entry_body = {
        key: value for key, value in entry.items()
        if key != "history_entry_digest"
    }
    entry["history_entry_digest"] = _test_digest(entry_body)

    assert execution_store_module.finalize_signed_worker_execution(
        db,
        task_id,
        context=context,
        accepted=False,
        result_context=result_context,
    ) is False

    stored = db.get_autonomous_task_by_id(task_id)
    assert stored is not None and stored["status"] == "executing"
    assert db.db.execute_query(
        "SELECT task_id FROM agents_signed_worker_result_history "
        "WHERE task_id = ?",
        (task_id,),
    ) == []

def test_supervisor_result_ledger_failure_rolls_back_terminal_state(
    tmp_path: Path,
) -> None:
    task_id = _publish_agentdb_task()
    db = AgentDB()
    with db.db.get_connection() as connection:
        connection.execute(
            """
            CREATE TRIGGER reject_signed_worker_result_insert
            BEFORE INSERT ON agents_signed_worker_result_history
            BEGIN
                SELECT RAISE(ABORT, 'injected ledger failure');
            END
            """
        )
    runner = _FakeRunner()

    result = claim_reddog_signed_worker_dispatch_task_once(
        repo_root=tmp_path,
        signed_worker_runner=runner,
        authority_verification_context=(
            worker_dispatch_authority_verification_context()
        ),
    )

    stored = db.get_autonomous_task_by_id(task_id)
    assert result["accepted"] is False
    assert (
        SignedWorkerOpenClawClaimReason.RESULT_PERSISTENCE_REJECTED
        in result["rejection_reasons"]
    )
    assert len(runner.calls) == 1
    assert stored is not None and stored["status"] == "executing"
    assert db.db.execute_query(
        "SELECT task_id FROM agents_signed_worker_result_history "
        "WHERE task_id = ?",
        (task_id,),
    ) == []
