"""Focused queue-loop integration case."""

from __future__ import annotations

from modules.communication.moltbot_bridge.tests.test_reddog_signed_worker_dispatch_task_executor import (
    AgentDB,
    BOOTSTRAP_NOW,
    PILOT_ARTIFACT,
    PILOT_OPERATION,
    Path,
    REDDOG_SIGNATURE_VERIFIER_BACKEND_ED25519,
    SIGNED_WORKER_OPENCLAW_CLAIM_IDLE,
    _FakeWorktreeRunner,
    _artifact_runtime_profile,
    _artifact_runtime_snapshot,
    _artifact_runtime_work_order,
    _assurance_store,
    _ed25519_signing_material,
    _pending_signed_task_id,
    _pilot_allowed_paths,
    _pilot_bounded_worker_plan,
    _pilot_path_overrides,
    _pilot_worktree_path,
    _principals,
    _repo,
    _snapshots,
    _valve_environment,
    _write_runtime_json,
    claim_reddog_signed_worker_dispatch_task_once,
    json,
    run_reddog_main_resident_queue_serial_loop_bootstrap,
    runtime,
    isolated_agent_db,  # noqa: F401
)


def test_openclaw_queue_stage_does_not_materialize_bounded_artifact(
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
        max_steps=11,
    )
    assert seed.accepted is True, seed.rejection_reasons
    assert seed.dispatched_stages[-1] == "assurance_capacity_admission", (
        seed.queue_chain_requeue_required,
        seed.retry_at,
        seed.rejection_reasons,
    )
    assert (
        json.loads(chain.read_text(encoding="utf-8"))["stage_results"][
            "assurance_capacity_admission"
        ]["status"]
        == "ASSURANCE_CAPACITY_RESERVED"
    )
    assert worktree.exists()
    assert not (worktree / PILOT_ARTIFACT).exists()

    queue_task_id = _pending_signed_task_id("queue_stage_progress")
    monkeypatch.setenv("WRE_MOCK_SKILLS", runtime.SIGNED_WORKER_DISPATCH_TASK_SKILL)
    monkeypatch.setenv("REDDOG_SIGNED_WORKER_QUEUE_LOOP_RUNNER", "1")
    monkeypatch.setenv("REDDOG_RESIDENT_RUNTIME_ROOT", str(tmp_path / "runtime"))
    monkeypatch.setenv("REDDOG_AUTHORITATIVE_WORK_STATE_PATH", str(state))
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_CHAIN_RESULTS_PATH", str(chain))
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_AUTHORITY_PROFILE_PATH", str(profile))
    monkeypatch.setenv("REDDOG_WORK_ORDERS_PATH", str(work_orders))
    monkeypatch.setenv("REDDOG_SIGNED_WORKER_QUEUE_LOOP_MAX_STEPS", "1")
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_NOW_ISO", BOOTSTRAP_NOW)

    result = claim_reddog_signed_worker_dispatch_task_once(
        repo_root=repo,
        agent_db_factory=_assurance_store,
    )

    assert result["accepted"] is False
    assert result["status"] == SIGNED_WORKER_OPENCLAW_CLAIM_IDLE
    assert AgentDB().get_autonomous_task_by_id(queue_task_id)["status"] == "pending"
    assert (
        "bounded_worker_pilot"
        not in json.loads(chain.read_text(encoding="utf-8"))["stage_results"]
    )
    assert not (worktree / PILOT_ARTIFACT).exists()
    assert not (repo / PILOT_ARTIFACT).exists()
