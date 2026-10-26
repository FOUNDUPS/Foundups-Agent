"""Focused queue-loop integration case."""

from __future__ import annotations

from modules.communication.moltbot_bridge.tests.test_reddog_signed_worker_dispatch_task_executor import (
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
    _pilot_allowed_paths,
    _pilot_bounded_worker_plan,
    _pilot_path_overrides,
    _principals,
    _repo,
    _snapshots,
    _valve_environment,
    claim_reddog_signed_worker_dispatch_task_once,
    json,
    resident_queue_runtime_file_path,
    run_reddog_main_resident_queue_serial_loop_bootstrap,
    runtime,
    isolated_agent_db,  # noqa: F401
)


def test_openclaw_claim_uses_profile_paths_for_bounded_code_readiness(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo = _repo(tmp_path)
    profile_env = {
        "REDDOG_RESIDENT_QUEUE_BINDING_PROFILE": "signed_0102_bounded_code_fusion",
        "REDDOG_RESIDENT_RUNTIME_ROOT": str(tmp_path / "resident-runtime"),
        "REDDOG_RESIDENT_QUEUE_NOW_ISO": BOOTSTRAP_NOW,
        "REDDOG_SIGNATURE_VERIFIER_BACKEND": REDDOG_SIGNATURE_VERIFIER_BACKEND_ED25519,
    }

    def _write_profile_file(env_name: str, payload: object) -> Path:
        path = Path(resident_queue_runtime_file_path(profile_env, repo, env_name))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
        return path

    principal_public, reddog_public, connector = _ed25519_signing_material()
    pilot_overrides = _pilot_path_overrides()
    state = _write_profile_file(
        "REDDOG_AUTHORITATIVE_WORK_STATE_PATH", _artifact_runtime_snapshot()
    )
    profile = _write_profile_file(
        "REDDOG_RESIDENT_QUEUE_AUTHORITY_PROFILE_PATH",
        _artifact_runtime_profile(
            principal_public_key=principal_public,
            reddog_public_key=reddog_public,
            requested_operation=PILOT_OPERATION,
            allowed_paths=_pilot_allowed_paths(),
            denied_paths=pilot_overrides["denied_paths"],
        ),
    )
    snapshots = _write_profile_file("REDDOG_PERMISSION_SNAPSHOTS_PATH", _snapshots())
    principals = _write_profile_file(
        "REDDOG_PRINCIPAL_AUTHORITY_RECORDS_PATH",
        _principals(principal_public),
    )
    valve_env = _write_profile_file(
        "REDDOG_EXECUTION_VALVE_ENV_PATH", _valve_environment()
    )
    work_order = _artifact_runtime_work_order(
        **pilot_overrides,
        bounded_worker_plan=_pilot_bounded_worker_plan(),
    )
    work_order["holoindex_evidence"] = {
        **dict(work_order["holoindex_evidence"]),
        "holoindex_freshness_receipt_digest": "sha256:holo-fresh",
    }
    work_orders_path = tmp_path / "resident-runtime" / "work_orders.json"
    work_orders_path.parent.mkdir(parents=True, exist_ok=True)
    work_orders_path.write_text(
        json.dumps(
            {"work_orders": {str(work_order["work_order_id"]): work_order}},
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    chain = Path(
        resident_queue_runtime_file_path(
            profile_env,
            repo,
            "REDDOG_RESIDENT_QUEUE_CHAIN_RESULTS_PATH",
        )
    )
    authority_state = Path(
        resident_queue_runtime_file_path(
            profile_env,
            repo,
            "REDDOG_AUTHORITY_RUNTIME_STATE_PATH",
        )
    )
    socket_path = Path(
        resident_queue_runtime_file_path(
            profile_env,
            repo,
            "REDDOG_SIGNER_SOCKET_PATH",
        )
    )

    seed = run_reddog_main_resident_queue_serial_loop_bootstrap(
        repo_root=repo,
        runtime_allowed_root=tmp_path / "resident-runtime",
        work_state_path=state,
        chain_results_path=chain,
        authority_profile_path=profile,
        work_orders_path=work_orders_path,
        valve_environment_path=valve_env,
        authority_state_path=authority_state,
        permission_snapshots_path=snapshots,
        principal_authority_records_path=principals,
        signer_socket_path=socket_path,
        signer_socket_connector=connector,
        signature_verifier_backend=REDDOG_SIGNATURE_VERIFIER_BACKEND_ED25519,
        worker_dispatch_writer=runtime.AgentDbSignedWorkerDispatchTaskWriter(),
        assurance_reservation_store=_assurance_store(),
        worktree_runner=_FakeWorktreeRunner(),
        now_iso=BOOTSTRAP_NOW,
        now_epoch=1000,
        trusted_now_epoch=lambda: 1000,
        requested_queue_item_id="queue-1",
        max_steps=10,
    )
    assert seed.accepted is True
    assert seed.dispatched_stages[-1] == "assurance_capacity_admission"

    _patch_exact_sha_commit_runtime(
        monkeypatch,
        branch_name=str(work_order["branch_name"]),
    )
    pending = [
        task
        for task in AgentDB().get_autonomous_tasks(status="pending", limit=10)
        if task.get("discovered_by") == runtime.SIGNED_WORKER_DISPATCH_TASK_SOURCE
    ]
    assert len(pending) == 2
    coding_task_id = next(
        task["task_id"]
        for task in pending
        if task["context"]["worker_runtime"] == "0102"
        and task["context"]["capability"] == "bounded_code_change"
    )

    from modules.communication.moltbot_bridge.src import (
        reddog_bounded_artifact_generation_runtime as artifact_runtime,
    )

    fusion_calls: list[dict[str, object]] = []

    def _fake_fusion(api_key, user_payload, messages, payload):
        fusion_calls.append(
            {
                "api_key": api_key,
                "user_payload": user_payload,
                "messages": messages,
                "payload": payload,
            }
        )
        return {
            "ok": True,
            "content": json.dumps(
                {
                    "artifact_contents": {
                        PILOT_ARTIFACT: "# Generated By Fusion\n\nprofile path claim\n"
                    }
                },
                sort_keys=True,
            ),
            "review_packet": {"receipt_id": "fusion-artifact-receipt-profile-path"},
        }

    monkeypatch.setattr(
        artifact_runtime,
        "_load_foundups_fusion_runner",
        lambda: _fake_fusion,
    )
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-openrouter-key")
    for env_name in (
        "REDDOG_AUTHORITATIVE_WORK_STATE_PATH",
        "REDDOG_RESIDENT_QUEUE_CHAIN_RESULTS_PATH",
        "REDDOG_RESIDENT_QUEUE_AUTHORITY_PROFILE_PATH",
        "REDDOG_WORK_ORDERS_PATH",
        "REDDOG_ARTIFACT_GENERATION_REQUEST_PATH",
        "REDDOG_ARTIFACT_CONTENTS_PATH",
    ):
        monkeypatch.delenv(env_name, raising=False)
    for key, value in profile_env.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv("REDDOG_WORK_ORDERS_PATH", str(work_orders_path))
    monkeypatch.setenv("WRE_MOCK_SKILLS", runtime.SIGNED_WORKER_DISPATCH_TASK_SKILL)

    result = claim_reddog_signed_worker_dispatch_task_once(repo_root=repo)

    assert result["accepted"] is True, json.dumps(result, sort_keys=True)
    assert result["status"] == SIGNED_WORKER_OPENCLAW_CLAIM_ACCEPT
    assert result["task_id"] == coding_task_id
    assert result["worker_runtime"] == "0102"
    assert result["capability"] == "bounded_code_change"
    assert AgentDB().get_autonomous_task_by_id(coding_task_id)["status"] == "completed"
    assert fusion_calls
    stored = json.loads(chain.read_text(encoding="utf-8"))
    assert stored["stage_results"]["bounded_worker_pilot"]["decision"] == (
        "QUEUE_AUTHORIZED_BOUNDED_WORKER_PILOT_INVOKE_ACCEPT"
    )
