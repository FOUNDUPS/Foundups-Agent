"""Focused queue-loop integration case."""

from __future__ import annotations

from modules.communication.moltbot_bridge.tests.test_reddog_signed_worker_dispatch_task_executor import (
    AgentDB,
    BOOTSTRAP_NOW,
    PILOT_OPERATION,
    Path,
    REDDOG_SIGNATURE_VERIFIER_BACKEND_ED25519,
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
    _outcome_ratchet_request,
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
    claim_reddog_signed_worker_dispatch_task_once,
    json,
    run_reddog_main_resident_queue_serial_loop_bootstrap,
    runtime,
    isolated_agent_db,  # noqa: F401
)


def test_openclaw_claim_env_bound_queue_loop_runner_reaches_verified_outcome_ratchet(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from modules.foundups.agent.src import worktree_pr_runner

    _FakeEnvDraftPrRunner.instances.clear()
    monkeypatch.setattr(
        worktree_pr_runner,
        "RealWorktreeRunner",
        _FakeEnvDraftPrRunner,
    )
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
    verifier = _write_runtime_json(
        tmp_path,
        "verifier_request.json",
        _slice_verifier_request(),
    )
    publish_request = _write_runtime_json(
        tmp_path,
        "publish_request.json",
        _draft_pr_publish_request(worktree),
    )
    draft_runner = _FakeEnvDraftPrRunner(repo_root=repo, timeout_s=88)

    seed = run_reddog_main_resident_queue_serial_loop_bootstrap(
        repo_root=repo,
        runtime_allowed_root=tmp_path / "runtime",
        work_state_path=state,
        chain_results_path=chain,
        authority_profile_path=profile,
        work_orders_path=work_orders,
        valve_environment_path=valve_env,
        generic_writer_dryrun_result_path=generic_writer,
        governed_shell_dryrun_result_path=governed_shell,
        artifact_contents_path=artifacts,
        holoindex_evidence_path=holoindex,
        verifier_request_path=verifier,
        publish_request_path=publish_request,
        authority_state_path=authority_state,
        permission_snapshots_path=snapshots,
        principal_authority_records_path=principals,
        signer_socket_path=socket_path,
        signer_socket_connector=connector,
        signature_verifier_backend=REDDOG_SIGNATURE_VERIFIER_BACKEND_ED25519,
        worker_dispatch_writer=runtime.AgentDbSignedWorkerDispatchTaskWriter(),
        assurance_reservation_store=_assurance_store(),
        worktree_runner=worktree_runner,
        draft_pr_runner=draft_runner,
        now_iso=BOOTSTRAP_NOW,
        now_epoch=1000,
        trusted_now_epoch=lambda: 1000,
        requested_queue_item_id="queue-1",
        max_steps=13,
    )
    assert seed.accepted is True
    assert seed.dispatched_stages[-1] == "assurance_capacity_admission"
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
        verifier=verifier,
    )
    monkeypatch.setenv("REDDOG_DRAFT_PR_PUBLISH_REQUEST_PATH", str(publish_request))
    monkeypatch.setenv("REDDOG_DRAFT_PR_RUNNER_MODE", "real")
    monkeypatch.setenv("REDDOG_DRAFT_PR_RUNNER_TIMEOUT_S", "88")
    publish_result = claim_reddog_signed_worker_dispatch_task_once(
        repo_root=repo,
        agent_db_factory=_assurance_store,
    )
    assert publish_result["accepted"] is True, json.dumps(
        publish_result, sort_keys=True
    )
    assert publish_result["status"] == SIGNED_WORKER_OPENCLAW_CLAIM_REQUEUED
    seeded = json.loads(chain.read_text(encoding="utf-8"))
    verifier_stage = seeded["stage_results"]["slice_verifier"]
    publish_stage = seeded["stage_results"]["verified_draft_pr_publish"]
    assert (
        publish_stage["publish_result"]["decision"]
        == "VERIFIED_DRAFT_PR_PUBLISH_ACCEPT"
    )

    ratchet_request = _write_runtime_json(
        tmp_path,
        "ratchet_request.json",
        _outcome_ratchet_request(verifier_stage["verifier_result"]),
    )
    outcome_store = tmp_path / "runtime" / "outcomes" / "signed-worker-ratchet.jsonl"
    task_id = _pending_signed_task_id("queue_stage_progress")
    monkeypatch.setenv("WRE_MOCK_SKILLS", runtime.SIGNED_WORKER_DISPATCH_TASK_SKILL)
    monkeypatch.setenv("REDDOG_SIGNED_WORKER_QUEUE_LOOP_RUNNER", "1")
    monkeypatch.setenv("REDDOG_RESIDENT_RUNTIME_ROOT", str(tmp_path / "runtime"))
    monkeypatch.setenv("REDDOG_AUTHORITATIVE_WORK_STATE_PATH", str(state))
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_CHAIN_RESULTS_PATH", str(chain))
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_AUTHORITY_PROFILE_PATH", str(profile))
    monkeypatch.setenv("REDDOG_WORK_ORDERS_PATH", str(work_orders))
    monkeypatch.setenv("REDDOG_OUTCOME_RATCHET_REQUEST_PATH", str(ratchet_request))
    monkeypatch.setenv("REDDOG_OUTCOME_RATCHET_STORE_PATH", str(outcome_store))
    monkeypatch.setenv("REDDOG_SIGNED_WORKER_QUEUE_LOOP_MAX_STEPS", "1")
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_NOW_ISO", BOOTSTRAP_NOW)

    result = claim_reddog_signed_worker_dispatch_task_once(repo_root=repo)

    assert result["accepted"] is True, json.dumps(result, sort_keys=True)
    assert result["status"] == SIGNED_WORKER_OPENCLAW_CLAIM_REQUEUED
    assert result["task_id"] == task_id
    assert AgentDB().get_autonomous_task_by_id(task_id)["status"] == "pending"

    stored = json.loads(chain.read_text(encoding="utf-8"))
    stage = stored["stage_results"]["verified_outcome_ratchet"]
    assert (
        stage["decision"] == "QUEUE_AUTHORIZED_VERIFIED_OUTCOME_RATCHET_INVOKE_ACCEPT"
    )
    assert stage["ratchet_result"]["decision"] == "OUTCOME_RATCHET_RECORDED"
    assert stage["ratchet_result"]["receipt"]["pattern_memory_write_performed"] is False
    assert stage["no_command_execution_performed"] is True
    assert stage["no_pr_publish_performed"] is True
    assert stage["no_ready_performed"] is True
    assert stage["no_merge_performed"] is True
    assert stage["no_reward_settlement_performed"] is True
    assert stage["no_holoindex_reindex_performed"] is True
    assert "held_out_regression_gate" not in stored["stage_results"]

    records = [
        json.loads(line)
        for line in outcome_store.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(records) == 1
    assert records[0]["ratchet_receipt"]["work_order_id"] == work_order["work_order_id"]
    assert (
        records[0]["publish_result"]["decision"] == "VERIFIED_DRAFT_PR_PUBLISH_ACCEPT"
    )
    assert not (repo / "runtime" / "outcomes" / "signed-worker-ratchet.jsonl").exists()
