"""Focused extraction from the inherited integration matrix."""

from __future__ import annotations

from datetime import datetime
import socket

import pytest

from modules.communication.moltbot_bridge.tests.test_reddog_main_resident_queue_serial_loop_bootstrap import (
    NOW as BOOTSTRAP_NOW,
    _FakePatternMemoryAdmissionSink,
    _StaticSocketPeerAttestor,
    _ed25519_signing_material_with_socket_backend,
    _slice_verifier_plan,
    _test_governed_environment,
)
from modules.communication.moltbot_bridge.src.reddog_isolated_signer_socket_resident_service import (
    SIGNER_SOCKET_RESIDENT_SERVICE_SERVED,
    serve_reddog_isolated_signer_socket_bounded,
)
from modules.communication.moltbot_bridge.tests.reddog_resident_queue_test_helpers import (
    install_signed_worker_envelope_test_authority,
    with_architect_fix_publication,
)
from modules.communication.moltbot_bridge.tests.reddog_authoritative_use_lease_test_support import (
    inject_stub_governed_valve_use_time_authority,
)
from modules.communication.moltbot_bridge.tests.reddog_elevated_consensus_downstream_test_support import (
    downstream_test_consensus,
)
from modules.communication.moltbot_bridge.tests.reddog_progressive_chain_e2e_test_support import (
    assert_progressive_chain_state,
    assert_progressive_control_receipt,
    assert_progressive_effects,
    configure_control_receipt_signing_backend,
    configure_outcome_signing_backend,
    supply_runtime_authority_source,
)
from modules.communication.moltbot_bridge.tests.test_reddog_main_openclaw_signed_worker_claim_loop_preflight import (
    AgentDB,
    PILOT_ARTIFACT,
    PROFILE_SIGNED_0102_BOUNDED_CODE_FUSION_WORKTREE_DRAFT_PR_PATTERN_MEMORY,
    Path,
    _FakeEnvCommitDraftPrRunner,
    _FakeExactShaEvidenceRunner,
    _FakeProfileWorktreeRunner,
    _assurance_store,
    _draft_pr_publish_request,
    _patch_fusion_artifact_generator,
    _pilot_bounded_worker_plan,
    _pilot_path_overrides,
    _pilot_worktree_path,
    _principals,
    _repo,
    _slice_verifier_request,
    _snapshots,
    _write_json,
    json,
    isolated_agent_db,  # noqa: F401
    model_bound_queue_inputs,
    os,
    resident_queue_runtime_file_path,
    runtime,
    threading,
)


@pytest.mark.skipif(not hasattr(socket, "AF_UNIX"), reason="AF_UNIX required")
def test_main_resident_control_loop_profile_runtime_completes_socket_signed_queue_chain_without_work_orders(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    import main
    from modules.foundups.agent.src import worktree_pr_runner
    from modules.communication.moltbot_bridge.src import (
        reddog_main_resident_queue_serial_loop_bootstrap as serial_bootstrap,
    )
    from modules.communication.moltbot_bridge.src import (
        reddog_verified_pattern_memory_sink as pattern_memory_sink_module,
    )

    monkeypatch.setattr(
        main, "time", type("_TestClock", (), {"time": staticmethod(lambda: 1000)})
    )
    real_agent_db_init = AgentDB.__init__

    def _fixed_agent_db_init(instance, *, assurance_now_provider=None):
        real_agent_db_init(
            instance,
            assurance_now_provider=assurance_now_provider
            or (lambda: datetime.fromisoformat(BOOTSTRAP_NOW)),
        )

    monkeypatch.setattr(AgentDB, "__init__", _fixed_agent_db_init)
    real_serial_bootstrap = (
        serial_bootstrap.run_reddog_main_resident_queue_serial_loop_bootstrap
    )
    assurance_store = _assurance_store()

    def _fixed_policy_time_bootstrap(**kwargs: object):
        kwargs["now_iso"] = BOOTSTRAP_NOW
        kwargs["assurance_reservation_store"] = assurance_store
        return real_serial_bootstrap(**kwargs)

    monkeypatch.setattr(
        serial_bootstrap,
        "run_reddog_main_resident_queue_serial_loop_bootstrap",
        _fixed_policy_time_bootstrap,
    )
    monkeypatch.setattr(
        serial_bootstrap,
        "_build_worktree_runner",
        lambda repo_root, **_: (
            _FakeProfileWorktreeRunner(repo_root=repo_root, timeout_s=77),
            (),
        ),
    )
    _FakeProfileWorktreeRunner.instances.clear()
    _FakeEnvCommitDraftPrRunner.instances.clear()
    pattern_memory_sink = _FakePatternMemoryAdmissionSink()
    monkeypatch.setattr(
        pattern_memory_sink_module,
        "build_reddog_verified_pattern_memory_sink",
        lambda **_: pattern_memory_sink,
    )
    repo = _repo(tmp_path)
    runtime_root = tmp_path / "resident-runtime"
    runtime_root.mkdir(parents=True)
    profile_env = {
        "REDDOG_RESIDENT_QUEUE_BINDING_PROFILE": (
            PROFILE_SIGNED_0102_BOUNDED_CODE_FUSION_WORKTREE_DRAFT_PR_PATTERN_MEMORY
        ),
        "REDDOG_RESIDENT_RUNTIME_ROOT": str(runtime_root),
    }
    principal_public, reddog_public, signer_backend = (
        _ed25519_signing_material_with_socket_backend()
    )
    pilot_overrides = _pilot_path_overrides()
    state_payload, profile_payload, materialized_work_order = model_bound_queue_inputs(
        principal_public, reddog_public, pilot_overrides
    )
    state_payload["worker_claims"][0]["expires_at"] = "2099-01-01T00:00:00+00:00"
    state_payload["wre_queue_items"][0].update(
        {
            "foundup_id": "foundup:test",
            "snapshot_id": "snapshot:test",
            "snapshot_content_digest": "sha256:" + "9" * 64,
        }
    )
    profile_payload["bounded_worker_plan"] = _pilot_bounded_worker_plan()
    profile_payload["slice_verifier_plan"] = _slice_verifier_plan()
    profile_payload, profile_source, profile_source_receipt_id = (
        supply_runtime_authority_source(
            repo_root=repo,
            runtime_root=runtime_root,
            runtime_profile=profile_payload,
            now_epoch=1000,
        )
    )
    materialized_work_order["denied_paths"] = list(profile_payload["denied_paths"])
    outcome_authority = configure_outcome_signing_backend(
        signer_backend,
        signer_public_key=reddog_public,
        principal_id=profile_payload["principal_id"],
        reddog_id=profile_payload["reddog_id"],
        key_epoch=profile_payload["key_epoch"],
        consensus_receipt_digest=profile_payload["consensus_receipt_digest"],
        now_epoch=1000,
    )
    state_payload, profile_payload, queue_item_id, _claim_id = (
        with_architect_fix_publication(state_payload, profile_payload)
    )
    configure_control_receipt_signing_backend(
        signer_backend,
        signer_public_key=reddog_public,
        runtime_profile=profile_payload,
    )
    evidence_runner = _FakeExactShaEvidenceRunner(
        branch_name=serial_bootstrap._branch_name(
            slice_id="REDDOG_TEST_SLICE_PHASE1", queue_item_id=queue_item_id
        )
    )
    _FakeEnvCommitDraftPrRunner.evidence_runner = evidence_runner
    monkeypatch.setattr(
        worktree_pr_runner, "RealWorktreeRunner", _FakeEnvCommitDraftPrRunner
    )
    monkeypatch.setattr(
        serial_bootstrap,
        "_build_evidence_command_runner",
        lambda *args, **kwargs: (evidence_runner, ()),
    )
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
        profile_payload,
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
    governed_valve_environment, expected_valve_bindings = _test_governed_environment(
        materialized_work_order
    )
    valve_env = _write_json(
        Path(
            resident_queue_runtime_file_path(
                profile_env, repo, "REDDOG_EXECUTION_VALVE_ENV_PATH"
            )
        ),
        governed_valve_environment,
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
            profile_env, repo, "REDDOG_AUTHORITY_RUNTIME_STATE_PATH"
        )
    )
    socket_path = Path(
        resident_queue_runtime_file_path(profile_env, repo, "REDDOG_SIGNER_SOCKET_PATH")
    )
    worktree = _pilot_worktree_path(repo, materialized_work_order)
    verifier_request = _write_json(
        runtime_root / "slice_verifier_request.json",
        _slice_verifier_request(),
    )
    publish_request = _write_json(
        runtime_root / "draft_pr_publish_request.json",
        _draft_pr_publish_request(worktree),
    )
    outcome_store = runtime_root / "outcomes" / "signed-worker-ratchet.jsonl"
    pattern_memory_db = runtime_root / "pattern_memory.db"
    assert not socket_path.exists()
    ready = threading.Event()
    service_result: dict[str, object] = {}

    def _serve_signer() -> None:
        service_result["result"] = serve_reddog_isolated_signer_socket_bounded(
            repo_root=repo,
            socket_path=socket_path,
            backend=signer_backend,
            peer_attestor=_StaticSocketPeerAttestor(),
            max_requests=4,
            timeout_s=5,
            ready_callback=ready.set,
        )

    signer_thread = threading.Thread(target=_serve_signer, daemon=True)
    signer_thread.start()
    assert ready.wait(5)
    calls = _patch_fusion_artifact_generator(monkeypatch, PILOT_ARTIFACT)
    monkeypatch.setenv(
        "REDDOG_RESIDENT_QUEUE_BINDING_PROFILE",
        PROFILE_SIGNED_0102_BOUNDED_CODE_FUSION_WORKTREE_DRAFT_PR_PATTERN_MEMORY,
    )
    monkeypatch.setenv("REDDOG_RESIDENT_RUNTIME_ROOT", str(runtime_root))
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_CONTROL_LOOP", "1")
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_CONTROL_LOOP_MAX_ROUNDS", "8")
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_SERIAL_LOOP_MAX_STEPS", "9")
    monkeypatch.setenv("REDDOG_SIGNED_WORKER_QUEUE_LOOP_MAX_STEPS", "2")
    monkeypatch.setenv("OPENCLAW_SIGNED_WORKER_TASK_MAX_CLAIMS", "7")
    monkeypatch.setenv("WRE_MOCK_SKILLS", runtime.SIGNED_WORKER_DISPATCH_TASK_SKILL)
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_NOW_EPOCH", "1000")
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_WORKTREE_RUNNER_TIMEOUT_S", "77")
    monkeypatch.setenv("REDDOG_DRAFT_PR_RUNNER_MODE", "real")
    monkeypatch.setenv("REDDOG_DRAFT_PR_RUNNER_TIMEOUT_S", "88")
    monkeypatch.setenv("REDDOG_AUTHORITY_RUNTIME_RESOLVER_ARTIFACT_SUPPLY", "0")
    monkeypatch.setenv("REDDOG_AUTHORITATIVE_WORK_STATE_PATH", str(state))
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_AUTHORITY_PROFILE_PATH", str(profile))
    monkeypatch.setenv("REDDOG_AUTHORITY_PROFILE_SOURCE_PATH", str(profile_source))
    monkeypatch.setenv(
        "REDDOG_AUTHORITY_PROFILE_SOURCE_RECEIPT_ID",
        profile_source_receipt_id,
    )
    monkeypatch.setenv("REDDOG_PERMISSION_SNAPSHOTS_PATH", str(snapshots))
    monkeypatch.setenv("REDDOG_PRINCIPAL_AUTHORITY_RECORDS_PATH", str(principals))
    monkeypatch.setenv("REDDOG_EXECUTION_VALVE_ENV_PATH", str(valve_env))
    monkeypatch.setenv("REDDOG_AUTHORITY_RUNTIME_STATE_PATH", str(authority_state))
    monkeypatch.setenv("REDDOG_SLICE_VERIFIER_REQUEST_PATH", str(verifier_request))
    monkeypatch.setenv("REDDOG_DRAFT_PR_PUBLISH_REQUEST_PATH", str(publish_request))
    monkeypatch.setenv("REDDOG_OUTCOME_RATCHET_STORE_PATH", str(outcome_store))
    monkeypatch.setenv(
        "REDDOG_MODEL_FEEDBACK_LEDGER_STORE_PATH",
        str(runtime_root / "model_feedback" / "model_feedback.jsonl"),
    )
    monkeypatch.setenv(
        "REDDOG_PATTERN_MEMORY_ADMISSION_DB_PATH", str(pattern_memory_db)
    )
    monkeypatch.delenv("REDDOG_WORK_ORDERS_PATH", raising=False)
    assert "REDDOG_WORK_ORDERS_PATH" not in os.environ
    install_signed_worker_envelope_test_authority(monkeypatch)
    try:
        with (
            inject_stub_governed_valve_use_time_authority(
                governed_valve_environment, expected_valve_bindings
            ),
            downstream_test_consensus(
                work_state_path=state, authority_profile_path=profile
            ),
        ):
            assert main.run_reddog_resident_queue_control_loop_preflight(repo) is True
    finally:
        signer_thread.join(5)
    result = service_result["result"]
    assert result.accepted is True
    assert result.status == SIGNER_SOCKET_RESIDENT_SERVICE_SERVED
    assert result.requests_handled == 4
    assert len(outcome_authority.committed) == 1
    assert not socket_path.exists()
    captured = capsys.readouterr().out
    assert "[REDDOG-QUEUE-CONTROL] preflight=PASS" in captured
    assert "[REDDOG-QUEUE-LOOP] preflight=PASS" in captured
    assert "[REDDOG-OPENCLAW-CLAIM-LOOP] preflight=PASS" in captured
    assert "claimed_count=7" in captured
    assert "receipts=signed_worker_task_execution_" in captured
    assert str(
        main.run_reddog_resident_queue_control_loop_preflight.last_result[
            "receipt_ids"
        ][0]
    ).startswith("signed_worker_task_execution_")
    assert "control_receipt=reddog_resident_control_loop_" in captured
    control_receipt_path = Path(
        resident_queue_runtime_file_path(
            profile_env,
            repo,
            "REDDOG_RESIDENT_QUEUE_CONTROL_LOOP_RECEIPTS_PATH",
        )
    )
    control_receipt = json.loads(
        control_receipt_path.read_text(encoding="utf-8").splitlines()[-1]
    )
    assert_progressive_control_receipt(
        control_receipt,
        main.run_reddog_resident_queue_control_loop_preflight.last_result,
    )
    assert (
        main.run_reddog_resident_queue_control_loop_preflight.last_result[
            "control_lock_acquired"
        ]
        is True
    )
    assert "REDDOG_WORK_ORDERS_PATH" not in os.environ
    pending = [
        task
        for task in AgentDB().get_autonomous_tasks(status="pending", limit=10)
        if task.get("discovered_by") == runtime.SIGNED_WORKER_DISPATCH_TASK_SOURCE
    ]
    assert pending == []
    completed = [
        task
        for task in AgentDB().get_autonomous_tasks(status="completed", limit=10)
        if task.get("discovered_by") == runtime.SIGNED_WORKER_DISPATCH_TASK_SOURCE
    ]
    assert {task["context"]["worker_runtime"] for task in completed} == {
        "0102",
        "openclaw",
    }
    assert calls

    stored = json.loads(chain.read_text(encoding="utf-8"))
    assert_progressive_chain_state(stored)
    assert_progressive_effects(
        worktree_instances=_FakeProfileWorktreeRunner.instances,
        draft_runner_instances=_FakeEnvCommitDraftPrRunner.instances,
        repo_root=repo,
        artifact_path=PILOT_ARTIFACT,
        outcome_store=outcome_store,
        pattern_memory_records=pattern_memory_sink.records,
    )
