"""Focused queue-loop integration case."""

from __future__ import annotations

from modules.communication.moltbot_bridge.tests.test_reddog_signed_worker_dispatch_task_executor import (
    AUTONOMOUS_SLICE_VERIFIER_ACCEPT,
    AgentDB,
    BOOTSTRAP_NOW,
    PILOT_ARTIFACT,
    PILOT_OPERATION,
    Path,
    REDDOG_SIGNATURE_VERIFIER_BACKEND_ED25519,
    SIGNED_WORKER_OPENCLAW_CLAIM_ACCEPT,
    _FakeWorktreeRunner,
    _artifact_runtime_profile,
    _artifact_runtime_snapshot,
    _artifact_runtime_work_order,
    _assurance_store,
    _ed25519_signing_material,
    _patch_exact_sha_commit_runtime,
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
    configure_signed_worker_claim_authority_env,
    json,
    run_reddog_main_resident_queue_serial_loop_bootstrap,
    runtime,
    isolated_agent_db,  # noqa: F401
)


def test_openclaw_claim_env_bound_queue_loop_runner_reaches_slice_verifier(
    tmp_path: Path,
    monkeypatch,
) -> None:
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
    work_order["holoindex_evidence"] = {
        **dict(work_order["holoindex_evidence"]),
        "holoindex_freshness_receipt_digest": "sha256:holo-fresh",
    }
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
        holoindex_evidence_path=holoindex,
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
        max_steps=11,
    )
    assert seed.accepted is True
    assert seed.dispatched_stages[-1] == "assurance_capacity_admission"
    assert (
        json.loads(chain.read_text(encoding="utf-8"))["stage_results"][
            "assurance_capacity_admission"
        ]["status"]
        == "ASSURANCE_CAPACITY_RESERVED"
    )
    assert not (worktree / PILOT_ARTIFACT).exists()

    queue_task_id = _pending_signed_task_id("queue_stage_progress")
    coding_task_id = _pending_signed_task_id("bounded_code_change")
    verifier_task_id = next(
        str(task.get("task_id") or "")
        for task in AgentDB().get_autonomous_tasks(status="assigned", limit=20)
        if task.get("discovered_by") == runtime.SIGNED_WORKER_DISPATCH_TASK_SOURCE
        and isinstance(task.get("context"), dict)
        and task["context"].get("capability") == "independent_slice_verification"
    )
    _patch_exact_sha_commit_runtime(
        monkeypatch,
        branch_name=str(work_order["branch_name"]),
    )
    monkeypatch.setenv("WRE_MOCK_SKILLS", runtime.SIGNED_WORKER_DISPATCH_TASK_SKILL)
    monkeypatch.setenv("REDDOG_SIGNED_WORKER_QUEUE_LOOP_RUNNER", "1")
    monkeypatch.setenv("REDDOG_RESIDENT_RUNTIME_ROOT", str(tmp_path / "runtime"))
    monkeypatch.setenv("REDDOG_AUTHORITATIVE_WORK_STATE_PATH", str(state))
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_CHAIN_RESULTS_PATH", str(chain))
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_AUTHORITY_PROFILE_PATH", str(profile))
    monkeypatch.setenv("REDDOG_WORK_ORDERS_PATH", str(work_orders))
    monkeypatch.setenv("REDDOG_SLICE_VERIFIER_REQUEST_PATH", str(verifier))
    monkeypatch.setenv("REDDOG_GENERIC_WRITER_DRYRUN_RESULT_PATH", str(generic_writer))
    monkeypatch.setenv("REDDOG_GOVERNED_SHELL_DRYRUN_RESULT_PATH", str(governed_shell))
    monkeypatch.setenv("REDDOG_HOLOINDEX_EVIDENCE_PATH", str(holoindex))
    monkeypatch.setenv("REDDOG_ARTIFACT_GENERATION_REQUEST_BINDING", "1")
    monkeypatch.setenv("REDDOG_ARTIFACT_GENERATOR_MODE", "foundups_fusion")
    monkeypatch.setenv("OPENCLAW_SIGNED_0102_BOUNDED_CODE_TASKS_ENABLED", "1")
    monkeypatch.setenv("REDDOG_SIGNED_WORKER_QUEUE_LOOP_MAX_STEPS", "2")
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_NOW_ISO", BOOTSTRAP_NOW)
    configure_signed_worker_claim_authority_env(
        monkeypatch,
        chain_path=chain,
        signature_backend=REDDOG_SIGNATURE_VERIFIER_BACKEND_ED25519,
    )
    from modules.communication.moltbot_bridge.src import (
        reddog_bounded_artifact_generation_runtime as artifact_runtime,
    )

    monkeypatch.setattr(
        artifact_runtime,
        "_load_foundups_fusion_runner",
        lambda: (
            lambda _api_key, _user_payload, _messages, _payload: {
                "ok": True,
                "content": json.dumps(
                    {
                        "artifact_contents": {
                            PILOT_ARTIFACT: "# Generated By Independent Author\n"
                        }
                    },
                    sort_keys=True,
                ),
                "review_packet": {"receipt_id": "fusion-artifact-receipt"},
            }
        ),
    )
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-openrouter-key")

    author_result = claim_reddog_signed_worker_dispatch_task_once(
        repo_root=repo,
        agent_db_factory=_assurance_store,
    )
    assert author_result["accepted"] is True, json.dumps(author_result, sort_keys=True)
    assert author_result["task_id"] == coding_task_id
    assert author_result["capability"] == "bounded_code_change"
    assert AgentDB().get_autonomous_task_by_id(coding_task_id)["status"] == "completed"
    assert (worktree / PILOT_ARTIFACT).exists()

    result = claim_reddog_signed_worker_dispatch_task_once(
        repo_root=repo,
        agent_db_factory=_assurance_store,
    )
    assert result["accepted"] is True, json.dumps(result, sort_keys=True)
    assert result["status"] == SIGNED_WORKER_OPENCLAW_CLAIM_ACCEPT
    assert result["task_id"] == verifier_task_id
    assert result["worker_runtime"] == "openclaw"
    assert result["capability"] == "independent_slice_verification"
    assert (
        AgentDB().get_autonomous_task_by_id(verifier_task_id)["status"] == "completed"
    )
    assert AgentDB().get_autonomous_task_by_id(queue_task_id)["status"] == "pending"

    stored = json.loads(chain.read_text(encoding="utf-8"))
    stage = stored["stage_results"]["slice_verifier"]
    assert stage["decision"] == "QUEUE_AUTHORIZED_SLICE_VERIFIER_INVOKE_ACCEPT"
    assert stage["verifier_result"]["decision"] == AUTONOMOUS_SLICE_VERIFIER_ACCEPT
    assert stage["verifier_result"]["receipt"]["changed_paths"] == [PILOT_ARTIFACT]
    assert stage["no_command_execution_performed"] is True
    assert stage["no_github_call_performed"] is True
    assert stage["no_pr_publish_performed"] is True
    assert stage["no_merge_performed"] is True
    assert stage["no_pattern_memory_write_performed"] is True
    assert stage["no_reward_settlement_performed"] is True
    assert stage["no_holoindex_reindex_performed"] is True
    assert (worktree / PILOT_ARTIFACT).exists()
    assert not (repo / PILOT_ARTIFACT).exists()
