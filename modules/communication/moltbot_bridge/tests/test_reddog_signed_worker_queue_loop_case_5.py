"""Focused queue-loop integration case."""

from __future__ import annotations

from modules.communication.moltbot_bridge.tests.test_reddog_signed_worker_dispatch_task_executor import (
    AgentDB,
    BOOTSTRAP_NOW,
    PILOT_ARTIFACT,
    PILOT_OPERATION,
    Path,
    REDDOG_SIGNATURE_VERIFIER_BACKEND_ED25519,
    SIGNED_WORKER_OPENCLAW_CLAIM_LOOP_REJECT,
    SIGNED_WORKER_OPENCLAW_CLAIM_REJECT,
    SIGNED_WORKER_OPENCLAW_CLAIM_REQUEUED,
    _FakeEnvDraftPrRunner,
    _FakeWorktreeRunner,
    _artifact_runtime_profile,
    _artifact_runtime_snapshot,
    _artifact_runtime_work_order,
    _assurance_store,
    _claim_reserved_author_and_verifier,
    _draft_pr_publish_request,
    _ed25519_signing_material,
    _pending_signed_task_id,
    _pilot_allowed_paths,
    _pilot_bounded_worker_plan,
    _pilot_path_overrides,
    _pilot_payloads,
    _pilot_worktree_path,
    _principals,
    _repo,
    _slice_verifier_request,
    _snapshots,
    _valve_environment,
    _write_runtime_json,
    claim_reddog_signed_worker_dispatch_tasks_until_idle,
    json,
    run_reddog_main_resident_queue_serial_loop_bootstrap,
    runtime,
    isolated_agent_db,  # noqa: F401
)


def test_openclaw_claim_loop_stops_before_pattern_memory_without_authority(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from modules.foundups.agent.src import worktree_pr_runner

    _FakeEnvDraftPrRunner.instances.clear()
    monkeypatch.setattr(worktree_pr_runner, "RealWorktreeRunner", _FakeEnvDraftPrRunner)
    repo = _repo(tmp_path)
    principal_public, reddog_public, connector = _ed25519_signing_material()
    pilot_overrides = _pilot_path_overrides()
    state = _write_runtime_json(
        tmp_path, "work_state.json", _artifact_runtime_snapshot()
    )
    profile = _write_runtime_json(
        tmp_path,
        "profile.json",
        _artifact_runtime_profile(
            principal_public_key=principal_public,
            reddog_public_key=reddog_public,
            requested_operation=PILOT_OPERATION,
            allowed_paths=_pilot_allowed_paths(),
            denied_paths=pilot_overrides["denied_paths"],
        ),
    )
    snapshots = _write_runtime_json(tmp_path, "snapshots.json", _snapshots())
    principals = _write_runtime_json(
        tmp_path, "principals.json", _principals(principal_public)
    )
    work_order = _artifact_runtime_work_order(
        **pilot_overrides,
        bounded_worker_plan=_pilot_bounded_worker_plan(),
    )
    work_orders = _write_runtime_json(
        tmp_path,
        "work_orders.json",
        {"work_orders": {str(work_order["work_order_id"]): work_order}},
    )
    valve_env = _write_runtime_json(tmp_path, "valve_env.json", _valve_environment())
    chain = tmp_path / "runtime" / "chain_results.json"
    authority_state = tmp_path / "runtime" / "authority_state.json"
    socket_path = tmp_path / "runtime" / "signer.sock"
    worktree_runner = _FakeWorktreeRunner()
    worktree = _pilot_worktree_path(repo, work_order)
    seed = run_reddog_main_resident_queue_serial_loop_bootstrap(
        repo_root=repo,
        runtime_allowed_root=tmp_path / "runtime",
        work_state_path=state,
        chain_results_path=chain,
        authority_profile_path=profile,
        work_orders_path=work_orders,
        valve_environment_path=valve_env,
        authority_state_path=authority_state,
        permission_snapshots_path=snapshots,
        principal_authority_records_path=principals,
        signer_socket_path=socket_path,
        signer_socket_connector=connector,
        signature_verifier_backend=REDDOG_SIGNATURE_VERIFIER_BACKEND_ED25519,
        worker_dispatch_writer=runtime.AgentDbSignedWorkerDispatchTaskWriter(),
        assurance_reservation_store=_assurance_store(),
        worktree_runner=worktree_runner,
        now_iso=BOOTSTRAP_NOW,
        now_epoch=1000,
        trusted_now_epoch=lambda: 1000,
        requested_queue_item_id="queue-1",
        max_steps=10,
    )
    assert seed.accepted is True
    assert seed.dispatched_stages[-1] == "assurance_capacity_admission"
    assert worktree.exists()
    assert not (worktree / PILOT_ARTIFACT).exists()
    pilot_payloads = _pilot_payloads(repo, worktree, work_order)
    generic_writer = _write_runtime_json(
        tmp_path,
        "generic_writer.json",
        pilot_payloads["generic_writer_dryrun_result"],
    )
    governed_shell = _write_runtime_json(
        tmp_path,
        "governed_shell.json",
        pilot_payloads["governed_shell_dryrun_result"],
    )
    artifacts = _write_runtime_json(
        tmp_path,
        "artifact_contents.json",
        pilot_payloads["artifact_contents"],
    )
    holoindex = _write_runtime_json(
        tmp_path,
        "holoindex_evidence.json",
        pilot_payloads["holoindex_evidence"],
    )
    verifier_request = _write_runtime_json(
        tmp_path,
        "verifier_request.json",
        _slice_verifier_request(),
    )
    publish_request = _write_runtime_json(
        tmp_path,
        "publish_request.json",
        _draft_pr_publish_request(worktree),
    )
    outcome_store = tmp_path / "runtime" / "outcomes" / "signed-worker-ratchet.jsonl"
    model_feedback_store = (
        tmp_path / "runtime" / "model_feedback" / "model_feedback.jsonl"
    )
    pattern_memory_db = tmp_path / "runtime" / "pattern_memory.db"
    _claim_reserved_author_and_verifier(
        monkeypatch=monkeypatch,
        repo=repo,
        state=state,
        chain=chain,
        profile=profile,
        work_orders=work_orders,
        generic_writer=generic_writer,
        governed_shell=governed_shell,
        holoindex=holoindex,
        verifier=verifier_request,
    )
    task_id = _pending_signed_task_id("queue_stage_progress")
    monkeypatch.setenv("WRE_MOCK_SKILLS", runtime.SIGNED_WORKER_DISPATCH_TASK_SKILL)
    monkeypatch.setenv("REDDOG_SIGNED_WORKER_QUEUE_LOOP_RUNNER", "1")
    monkeypatch.setenv("REDDOG_RESIDENT_RUNTIME_ROOT", str(tmp_path / "runtime"))
    monkeypatch.setenv("REDDOG_AUTHORITATIVE_WORK_STATE_PATH", str(state))
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_CHAIN_RESULTS_PATH", str(chain))
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_AUTHORITY_PROFILE_PATH", str(profile))
    monkeypatch.setenv("REDDOG_WORK_ORDERS_PATH", str(work_orders))
    monkeypatch.setenv("REDDOG_GENERIC_WRITER_DRYRUN_RESULT_PATH", str(generic_writer))
    monkeypatch.setenv("REDDOG_GOVERNED_SHELL_DRYRUN_RESULT_PATH", str(governed_shell))
    monkeypatch.setenv("REDDOG_ARTIFACT_CONTENTS_PATH", str(artifacts))
    monkeypatch.setenv("REDDOG_HOLOINDEX_EVIDENCE_PATH", str(holoindex))
    monkeypatch.setenv("REDDOG_SLICE_VERIFIER_REQUEST_PATH", str(verifier_request))
    monkeypatch.setenv("REDDOG_DRAFT_PR_PUBLISH_REQUEST_PATH", str(publish_request))
    monkeypatch.setenv("REDDOG_DRAFT_PR_RUNNER_MODE", "real")
    monkeypatch.setenv("REDDOG_DRAFT_PR_RUNNER_TIMEOUT_S", "88")
    monkeypatch.setenv("REDDOG_OUTCOME_RATCHET_REQUEST_BINDING", "1")
    monkeypatch.setenv("REDDOG_OUTCOME_RATCHET_STORE_PATH", str(outcome_store))
    monkeypatch.setenv(
        "REDDOG_MODEL_FEEDBACK_LEDGER_STORE_PATH", str(model_feedback_store)
    )
    monkeypatch.setenv("REDDOG_HELD_OUT_GATE_REQUEST_BINDING", "1")
    monkeypatch.setenv("REDDOG_PATTERN_MEMORY_ADMISSION_REQUEST_BINDING", "1")
    monkeypatch.setenv(
        "REDDOG_PATTERN_MEMORY_ADMISSION_DB_PATH", str(pattern_memory_db)
    )
    monkeypatch.setenv("REDDOG_SIGNED_WORKER_QUEUE_LOOP_MAX_STEPS", "1")
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_NOW_ISO", BOOTSTRAP_NOW)
    result = claim_reddog_signed_worker_dispatch_tasks_until_idle(
        repo_root=repo,
        max_claims=6,
    )
    assert result["accepted"] is False, json.dumps(result, sort_keys=True)
    assert result["status"] == SIGNED_WORKER_OPENCLAW_CLAIM_LOOP_REJECT, json.dumps(
        result, sort_keys=True
    )
    assert result["claimed_count"] == 5, json.dumps(result, sort_keys=True)
    assert result["requeued_task_ids"] == (
        task_id,
        task_id,
        task_id,
        task_id,
    )
    assert result["completed_task_ids"] == ()
    assert result["failed_task_ids"] == (task_id,)
    assert result["idle"] is False
    assert result["max_claims_reached"] is False
    assert "stage:pattern_memory_admission" in result["rejection_reasons"]
    assert len(result["receipt_ids"]) == 4
    assert len(result["child_execution_evidence_digests"]) == 5
    assert all(
        digest.startswith("sha256:")
        for digest in result["child_execution_evidence_digests"]
    )
    assert [claim["status"] for claim in result["claim_results"][:-1]] == [
        SIGNED_WORKER_OPENCLAW_CLAIM_REQUEUED,
        SIGNED_WORKER_OPENCLAW_CLAIM_REQUEUED,
        SIGNED_WORKER_OPENCLAW_CLAIM_REQUEUED,
        SIGNED_WORKER_OPENCLAW_CLAIM_REQUEUED,
    ]
    assert result["claim_results"][-1]["status"] == SIGNED_WORKER_OPENCLAW_CLAIM_REJECT
    assert AgentDB().get_autonomous_task_by_id(task_id)["status"] == "failed"
    stored = json.loads(chain.read_text(encoding="utf-8"))
    for stage_name in (
        "bounded_worker_pilot",
        "slice_verifier",
        "verified_draft_pr_publish",
        "verified_outcome_ratchet",
        "model_feedback_admission",
        "held_out_regression_gate",
    ):
        assert stage_name in stored["stage_results"]
    assert "pattern_memory_admission" not in stored["stage_results"]
    assert stored["receipts"][-1]["next_action"] == (
        "RUN_QUEUE_AUTHORIZED_PATTERN_MEMORY_ADMISSION_INVOKE"
    )
    assert (worktree / PILOT_ARTIFACT).exists()
    assert not (repo / PILOT_ARTIFACT).exists()
    draft_pr_calls = [
        call[0]
        for instance in _FakeEnvDraftPrRunner.instances
        for call in instance.calls
    ]
    assert draft_pr_calls == ["commit_all", "push_branch", "create_draft_pr"]
    assert outcome_store.exists()
    assert model_feedback_store.exists()
    assert not pattern_memory_db.exists()
    assert not (repo / "runtime" / "pattern_memory.db").exists()
