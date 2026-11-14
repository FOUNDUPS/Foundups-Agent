"""Focused OpenClaw claim-loop integration cases."""

from __future__ import annotations

from modules.communication.moltbot_bridge.tests.reddog_resident_queue_test_helpers import (
    configure_signed_worker_claim_test_authority,
)

from modules.communication.moltbot_bridge.tests.test_reddog_main_openclaw_signed_worker_claim_loop_preflight import (
    AgentDB,
    BOOTSTRAP_NOW,
    CLAIM_LOOP,
    PILOT_ARTIFACT,
    PILOT_OPERATION,
    PROFILE_SIGNED_0102_BOUNDED_CODE_FUSION_WORKTREE,
    Path,
    REDDOG_SIGNATURE_VERIFIER_BACKEND_ED25519,
    _FakeEnvCommitDraftPrRunner,
    _FakeEnvDraftPrRunner,
    _FakeExactShaEvidenceRunner,
    _FakeWorktreeRunner,
    _assurance_store,
    _bootstrap_profile,
    _bootstrap_snapshot,
    _draft_pr_publish_request,
    _ed25519_signing_material,
    _patch_fusion_artifact_generator,
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
    _write_json,
    _write_runtime_json,
    json,
    isolated_agent_db,  # noqa: F401
    model_bound_queue_inputs,
    os,
    patch,
    resident_queue_runtime_file_path,
    run_reddog_main_resident_queue_serial_loop_bootstrap,
    runtime,
)


def test_main_resident_control_loop_enforced_fails_closed_when_profile_signer_socket_missing(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    import main

    repo = _repo(tmp_path)
    runtime_root = tmp_path / "resident-runtime"
    runtime_root.mkdir(parents=True)
    principal_public, reddog_public, _connector = _ed25519_signing_material()
    pilot_overrides = _pilot_path_overrides()
    profile_env = {
        "REDDOG_RESIDENT_QUEUE_BINDING_PROFILE": PROFILE_SIGNED_0102_BOUNDED_CODE_FUSION_WORKTREE,
        "REDDOG_RESIDENT_RUNTIME_ROOT": str(runtime_root),
    }
    state_payload = _bootstrap_snapshot(requested_operation=PILOT_OPERATION)
    state_payload["worker_claims"][0]["expires_at"] = "2099-01-01T00:00:00+00:00"
    state = _write_json(
        Path(
            resident_queue_runtime_file_path(
                profile_env, repo, "REDDOG_AUTHORITATIVE_WORK_STATE_PATH"
            )
        ),
        state_payload,
    )
    profile = _write_json(
        Path(
            resident_queue_runtime_file_path(
                profile_env,
                repo,
                "REDDOG_RESIDENT_QUEUE_AUTHORITY_PROFILE_PATH",
            )
        ),
        _bootstrap_profile(
            principal_public_key=principal_public,
            reddog_public_key=reddog_public,
            requested_operation=PILOT_OPERATION,
            allowed_paths=_pilot_allowed_paths(),
            denied_paths=pilot_overrides["denied_paths"],
            bounded_worker_plan=_pilot_bounded_worker_plan(),
        ),
    )
    snapshots = _write_json(
        Path(
            resident_queue_runtime_file_path(
                profile_env, repo, "REDDOG_PERMISSION_SNAPSHOTS_PATH"
            )
        ),
        _snapshots(),
    )
    principals = _write_json(
        Path(
            resident_queue_runtime_file_path(
                profile_env,
                repo,
                "REDDOG_PRINCIPAL_AUTHORITY_RECORDS_PATH",
            )
        ),
        _principals(principal_public),
    )
    authority_state = Path(
        resident_queue_runtime_file_path(
            profile_env, repo, "REDDOG_AUTHORITY_RUNTIME_STATE_PATH"
        )
    )
    valve_env = _write_json(
        Path(
            resident_queue_runtime_file_path(
                profile_env, repo, "REDDOG_EXECUTION_VALVE_ENV_PATH"
            )
        ),
        _valve_environment(),
    )
    socket_path = Path(
        resident_queue_runtime_file_path(profile_env, repo, "REDDOG_SIGNER_SOCKET_PATH")
    )
    chain = Path(
        resident_queue_runtime_file_path(
            profile_env,
            repo,
            "REDDOG_RESIDENT_QUEUE_CHAIN_RESULTS_PATH",
        )
    )
    assert not socket_path.exists()

    monkeypatch.setenv(
        "REDDOG_RESIDENT_QUEUE_BINDING_PROFILE",
        PROFILE_SIGNED_0102_BOUNDED_CODE_FUSION_WORKTREE,
    )
    monkeypatch.setenv("REDDOG_RESIDENT_RUNTIME_ROOT", str(runtime_root))
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_CONTROL_LOOP", "1")
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_CONTROL_LOOP_ENFORCED", "1")
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_CONTROL_LOOP_MAX_ROUNDS", "1")
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_SERIAL_LOOP_MAX_STEPS", "1")
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_NOW_ISO", BOOTSTRAP_NOW)
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_NOW_EPOCH", "1000")
    monkeypatch.setenv("REDDOG_AUTHORITATIVE_WORK_STATE_PATH", str(state))
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_AUTHORITY_PROFILE_PATH", str(profile))
    monkeypatch.setenv("REDDOG_PERMISSION_SNAPSHOTS_PATH", str(snapshots))
    monkeypatch.setenv("REDDOG_PRINCIPAL_AUTHORITY_RECORDS_PATH", str(principals))
    monkeypatch.setenv("REDDOG_EXECUTION_VALVE_ENV_PATH", str(valve_env))
    monkeypatch.setenv("REDDOG_AUTHORITY_RUNTIME_STATE_PATH", str(authority_state))
    monkeypatch.setenv("REDDOG_AUTHORITY_RUNTIME_RESOLVER_ARTIFACT_SUPPLY", "0")
    monkeypatch.delenv("REDDOG_WORK_ORDERS_PATH", raising=False)

    with patch(
        CLAIM_LOOP,
        side_effect=AssertionError("claim loop must not run after signer reject"),
    ):
        assert main.run_reddog_resident_queue_control_loop_preflight(repo) is False

    captured = capsys.readouterr().out
    assert "governed_execution_valve_environment_required" in captured
    assert "[REDDOG-QUEUE-CONTROL] preflight=FAIL" in captured
    assert (
        main.run_reddog_resident_queue_serial_loop_preflight.last_result["accepted"]
        is False
    )
    assert authority_state.exists() is False
    assert chain.exists() is False


def test_main_openclaw_signed_0102_bounded_code_uses_fusion_artifact_generation(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    import main
    from modules.communication.moltbot_bridge.src import (
        reddog_main_resident_queue_serial_loop_bootstrap as bootstrap_module,
    )
    from modules.foundups.agent.src import worktree_pr_runner

    repo = _repo(tmp_path)
    principal_public, reddog_public, connector = _ed25519_signing_material()
    pilot_overrides = _pilot_path_overrides()
    snapshot, profile_payload, work_order = model_bound_queue_inputs(
        principal_public,
        reddog_public,
        pilot_overrides,
    )
    state = _write_runtime_json(
        tmp_path,
        "work_state.json",
        snapshot,
    )
    profile = _write_runtime_json(tmp_path, "profile.json", profile_payload)
    snapshots = _write_runtime_json(tmp_path, "snapshots.json", _snapshots())
    principals = _write_runtime_json(
        tmp_path, "principals.json", _principals(principal_public)
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

    evidence_runner = _FakeExactShaEvidenceRunner(
        branch_name=str(work_order["branch_name"])
    )
    _FakeEnvCommitDraftPrRunner.evidence_runner = evidence_runner
    monkeypatch.setattr(
        worktree_pr_runner,
        "RealWorktreeRunner",
        _FakeEnvCommitDraftPrRunner,
    )
    monkeypatch.setattr(
        bootstrap_module,
        "_build_evidence_command_runner",
        lambda *args, **kwargs: (evidence_runner, ()),
    )
    calls = _patch_fusion_artifact_generator(monkeypatch, PILOT_ARTIFACT)
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
    task_id = next(
        task["task_id"]
        for task in AgentDB().get_autonomous_tasks(status="pending", limit=10)
        if task.get("discovered_by") == runtime.SIGNED_WORKER_DISPATCH_TASK_SOURCE
        and task["context"].get("capability") == "bounded_code_change"
    )
    monkeypatch.setenv("REDDOG_OPENCLAW_SIGNED_WORKER_CLAIM_LOOP", "1")
    monkeypatch.setenv("OPENCLAW_SIGNED_0102_BOUNDED_CODE_TASKS_ENABLED", "1")
    monkeypatch.setenv("REDDOG_SIGNED_WORKER_QUEUE_LOOP_RUNNER", "1")
    monkeypatch.setenv("REDDOG_RESIDENT_RUNTIME_ROOT", str(tmp_path / "runtime"))
    monkeypatch.setenv("REDDOG_PILOT_DRYRUN_BINDING", "1")
    monkeypatch.setenv("REDDOG_ARTIFACT_GENERATION_REQUEST_BINDING", "1")
    monkeypatch.setenv("REDDOG_ARTIFACT_GENERATOR_MODE", "foundups_fusion")
    monkeypatch.setenv("OPENCLAW_SIGNED_WORKER_TASK_MAX_CLAIMS", "1")
    monkeypatch.setenv("WRE_MOCK_SKILLS", runtime.SIGNED_WORKER_DISPATCH_TASK_SKILL)
    monkeypatch.setenv("REDDOG_AUTHORITATIVE_WORK_STATE_PATH", str(state))
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_CHAIN_RESULTS_PATH", str(chain))
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_AUTHORITY_PROFILE_PATH", str(profile))
    monkeypatch.setenv("REDDOG_WORK_ORDERS_PATH", str(work_orders))
    monkeypatch.setenv(
        "REDDOG_GENERIC_WRITER_DRYRUN_RESULT_PATH",
        str(generic_writer),
    )
    monkeypatch.setenv(
        "REDDOG_GOVERNED_SHELL_DRYRUN_RESULT_PATH",
        str(governed_shell),
    )
    monkeypatch.setenv("REDDOG_HOLOINDEX_EVIDENCE_PATH", str(holoindex))
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_NOW_ISO", BOOTSTRAP_NOW)
    monkeypatch.setenv("REDDOG_SIGNED_WORKER_QUEUE_LOOP_MAX_STEPS", "2")
    monkeypatch.setenv("REDDOG_DRAFT_PR_RUNNER_MODE", "real")
    configure_signed_worker_claim_test_authority(
        monkeypatch,
        chain_path=chain,
        signature_backend=REDDOG_SIGNATURE_VERIFIER_BACKEND_ED25519,
    )
    assert main.run_reddog_openclaw_signed_worker_claim_loop_preflight(repo) is True

    captured = capsys.readouterr().out
    assert "[REDDOG-OPENCLAW-CLAIM-LOOP] preflight=PASS" in captured
    assert "status=SIGNED_WORKER_OPENCLAW_CLAIM_LOOP_ACCEPT" in captured
    assert "claimed_count=1" in captured
    assert f"completed={task_id}" in captured
    assert "requeued=(none)" in captured
    assert "receipts=signed_worker_task_execution_" in captured
    assert str(
        main.run_reddog_openclaw_signed_worker_claim_loop_preflight.last_result[
            "receipt_ids"
        ][0]
    ).startswith("signed_worker_task_execution_")
    assert AgentDB().get_autonomous_task_by_id(task_id)["status"] == "completed"
    assert calls
    assert calls[0]["api_key"] == "test-openrouter-key"
    payload = calls[0]["payload"]
    assert isinstance(payload, dict)
    assert payload["mode"] == "foundups_fusion"
    assert payload["response_contract"] == "strict_json_bounded_artifact_contents.v1"
    assert "artifact_generation_binding" in payload["bridge_meta"]

    stored = json.loads(chain.read_text(encoding="utf-8"))
    stage = stored["stage_results"]["bounded_worker_pilot"]
    assert stage["decision"] == "QUEUE_AUTHORIZED_BOUNDED_WORKER_PILOT_INVOKE_ACCEPT"
    generation = stage["artifact_generation_result"]
    assert generation["accepted"] is True
    assert generation["receipt"]["model_receipt_id"] == "fusion-artifact-receipt-1"
    assert generation["model_result"]["made_network_call"] is True
    assert (
        (worktree / PILOT_ARTIFACT)
        .read_text(encoding="utf-8")
        .startswith("# Generated By Fusion")
    )
    assert not (repo / PILOT_ARTIFACT).exists()
    assert "REDDOG_ARTIFACT_CONTENTS_PATH" not in os.environ


def test_main_openclaw_signed_worker_claim_loop_stops_before_unauthorized_pattern_memory(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    import main
    from modules.communication.moltbot_bridge.src import (
        reddog_main_resident_queue_serial_loop_bootstrap as bootstrap_module,
    )
    from modules.foundups.agent.src import worktree_pr_runner

    _FakeEnvDraftPrRunner.instances.clear()
    repo = _repo(tmp_path)
    principal_public, reddog_public, connector = _ed25519_signing_material()
    pilot_overrides = _pilot_path_overrides()
    snapshot, profile_payload, work_order = model_bound_queue_inputs(
        principal_public,
        reddog_public,
        pilot_overrides,
    )
    state = _write_runtime_json(
        tmp_path,
        "work_state.json",
        snapshot,
    )
    profile = _write_runtime_json(tmp_path, "profile.json", profile_payload)
    snapshots = _write_runtime_json(tmp_path, "snapshots.json", _snapshots())
    principals = _write_runtime_json(
        tmp_path, "principals.json", _principals(principal_public)
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

    evidence_runner = _FakeExactShaEvidenceRunner(
        branch_name=str(work_order["branch_name"])
    )
    _FakeEnvCommitDraftPrRunner.evidence_runner = evidence_runner
    monkeypatch.setattr(
        worktree_pr_runner,
        "RealWorktreeRunner",
        _FakeEnvCommitDraftPrRunner,
    )
    monkeypatch.setattr(
        bootstrap_module,
        "_build_evidence_command_runner",
        lambda *args, **kwargs: (evidence_runner, ()),
    )
    calls = _patch_fusion_artifact_generator(monkeypatch, PILOT_ARTIFACT)
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
    pattern_memory_db = tmp_path / "runtime" / "pattern_memory.db"

    pending = AgentDB().get_autonomous_tasks(status="pending", limit=10)
    signed_tasks = [
        task
        for task in pending
        if task.get("discovered_by") == runtime.SIGNED_WORKER_DISPATCH_TASK_SOURCE
    ]
    assert len(signed_tasks) == 2
    assigned_verifiers = [
        task
        for task in AgentDB().get_autonomous_tasks(status="assigned", limit=10)
        if task.get("discovered_by") == runtime.SIGNED_WORKER_DISPATCH_TASK_SOURCE
        and task["context"].get("capability") == "independent_slice_verification"
    ]
    assert len(assigned_verifiers) == 1
    coding_task_id = next(
        task["task_id"]
        for task in signed_tasks
        if task["context"]["worker_runtime"] == "0102"
        and task["context"]["capability"] == "bounded_code_change"
    )
    queue_stage_task_id = next(
        task["task_id"]
        for task in signed_tasks
        if task["context"]["worker_runtime"] == "openclaw"
        and task["context"]["capability"] == "queue_stage_progress"
    )
    monkeypatch.setenv("REDDOG_OPENCLAW_SIGNED_WORKER_CLAIM_LOOP", "1")
    monkeypatch.setenv("OPENCLAW_SIGNED_0102_BOUNDED_CODE_TASKS_ENABLED", "1")
    monkeypatch.setenv("OPENCLAW_SIGNED_QUEUE_STAGE_TASKS_ENABLED", "1")
    monkeypatch.setenv("OPENCLAW_SIGNED_WORKER_TASK_MAX_CLAIMS", "8")
    monkeypatch.setenv("WRE_MOCK_SKILLS", runtime.SIGNED_WORKER_DISPATCH_TASK_SKILL)
    monkeypatch.setenv("REDDOG_SIGNED_WORKER_QUEUE_LOOP_RUNNER", "1")
    monkeypatch.setenv("REDDOG_RESIDENT_RUNTIME_ROOT", str(tmp_path / "runtime"))
    monkeypatch.setenv("REDDOG_AUTHORITATIVE_WORK_STATE_PATH", str(state))
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_CHAIN_RESULTS_PATH", str(chain))
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_AUTHORITY_PROFILE_PATH", str(profile))
    monkeypatch.setenv("REDDOG_WORK_ORDERS_PATH", str(work_orders))
    monkeypatch.setenv(
        "REDDOG_GENERIC_WRITER_DRYRUN_RESULT_PATH",
        str(generic_writer),
    )
    monkeypatch.setenv(
        "REDDOG_GOVERNED_SHELL_DRYRUN_RESULT_PATH",
        str(governed_shell),
    )
    monkeypatch.setenv("REDDOG_HOLOINDEX_EVIDENCE_PATH", str(holoindex))
    monkeypatch.setenv("REDDOG_PILOT_DRYRUN_BINDING", "1")
    monkeypatch.setenv("REDDOG_ARTIFACT_GENERATION_REQUEST_BINDING", "1")
    monkeypatch.setenv("REDDOG_ARTIFACT_GENERATOR_MODE", "foundups_fusion")
    monkeypatch.setenv("REDDOG_SLICE_VERIFIER_REQUEST_PATH", str(verifier_request))
    monkeypatch.setenv("REDDOG_DRAFT_PR_PUBLISH_REQUEST_PATH", str(publish_request))
    monkeypatch.setenv("REDDOG_DRAFT_PR_RUNNER_MODE", "real")
    monkeypatch.setenv("REDDOG_DRAFT_PR_RUNNER_TIMEOUT_S", "88")
    monkeypatch.setenv("REDDOG_OUTCOME_RATCHET_REQUEST_BINDING", "1")
    monkeypatch.setenv("REDDOG_OUTCOME_RATCHET_STORE_PATH", str(outcome_store))
    monkeypatch.setenv(
        "REDDOG_MODEL_FEEDBACK_LEDGER_STORE_PATH",
        str(tmp_path / "runtime" / "model_feedback" / "model_feedback.jsonl"),
    )
    monkeypatch.setenv("REDDOG_HELD_OUT_GATE_REQUEST_BINDING", "1")
    monkeypatch.setenv("REDDOG_PATTERN_MEMORY_ADMISSION_REQUEST_BINDING", "1")
    monkeypatch.setenv(
        "REDDOG_PATTERN_MEMORY_ADMISSION_DB_PATH", str(pattern_memory_db)
    )
    monkeypatch.setenv("REDDOG_SIGNED_WORKER_QUEUE_LOOP_MAX_STEPS", "2")
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_NOW_ISO", BOOTSTRAP_NOW)
    configure_signed_worker_claim_test_authority(
        monkeypatch,
        chain_path=chain,
        signature_backend=REDDOG_SIGNATURE_VERIFIER_BACKEND_ED25519,
    )
    with patch(
        "modules.infrastructure.database.src.agent_db.AgentDB",
        _assurance_store,
    ):
        assert main.run_reddog_openclaw_signed_worker_claim_loop_preflight(repo) is True

    captured = capsys.readouterr().out
    assert "[REDDOG-OPENCLAW-CLAIM-LOOP] preflight=WARN" in captured
    assert "status=SIGNED_WORKER_OPENCLAW_CLAIM_LOOP_REJECT" in captured
    assert "claimed_count=7" in captured
    assert "FAIL_HANDLER_MISSING,stage:pattern_memory_admission" in captured
    assert coding_task_id in captured
    assert queue_stage_task_id in captured
    assert AgentDB().get_autonomous_task_by_id(coding_task_id)["status"] == "completed"
    assert (
        AgentDB().get_autonomous_task_by_id(queue_stage_task_id)["status"] == "failed"
    )
    remaining_signed = [
        task
        for task in AgentDB().get_autonomous_tasks(status="pending", limit=10)
        if task.get("discovered_by") == runtime.SIGNED_WORKER_DISPATCH_TASK_SOURCE
    ]
    assert remaining_signed == []
    assert calls
    assert calls[0]["api_key"] == "test-openrouter-key"

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
    generation = stored["stage_results"]["bounded_worker_pilot"][
        "artifact_generation_result"
    ]
    assert generation["accepted"] is True
    assert generation["receipt"]["model_receipt_id"] == "fusion-artifact-receipt-1"
    assert (
        (worktree / PILOT_ARTIFACT)
        .read_text(encoding="utf-8")
        .startswith("# Generated By Fusion")
    )
    assert not (repo / PILOT_ARTIFACT).exists()
    assert "REDDOG_ARTIFACT_CONTENTS_PATH" not in os.environ
    draft_pr_calls = [
        call[0]
        for instance in _FakeEnvDraftPrRunner.instances
        for call in instance.calls
    ]
    assert draft_pr_calls == ["commit_all", "push_branch", "create_draft_pr"]
    assert outcome_store.exists()
    assert not pattern_memory_db.exists()
    assert not (repo / "runtime" / "pattern_memory.db").exists()
