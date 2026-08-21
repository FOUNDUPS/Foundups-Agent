"""Focused extraction from the inherited integration matrix."""

from __future__ import annotations

from pathlib import Path
from datetime import datetime
import json

import pytest

from modules.communication.moltbot_bridge.tests.test_reddog_main_resident_queue_serial_loop_bootstrap import (
    _FakeModelRuntimeBindingVerifier,
    NOW,
    PILOT_ARTIFACT,
    REDDOG_SIGNATURE_VERIFIER_BACKEND_ED25519,
    WORK_ORDER_ID,
    _FakeCommitDraftPrRunner,
    _FakeExactShaEvidenceRunner,
    _FakeWorkerDispatchTaskWriter,
    _FakeWorktreeRunner,
    _draft_pr_publish_request,
    _ed25519_signing_material,
    _outcome_ratchet_request,
    _pilot_path_overrides,
    _pilot_payloads,
    _pilot_worktree_path,
    _principals,
    _ratchet_model_runtime_inputs,
    _repo,
    _slice_verifier_request,
    _snapshots,
    _valve_environment,
    _write_runtime_json,
    run_reddog_main_resident_queue_serial_loop_bootstrap,
)


def _run_bootstrap_to_verified_outcome_ratchet(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> dict[str, object]:
    from modules.communication.moltbot_bridge.src import (
        reddog_bounded_artifact_generation_runtime as artifact_runtime,
        reddog_main_resident_queue_serial_loop_bootstrap as bootstrap_module,
        reddog_openclaw_hermes_0102_worker_dispatch_runtime as dispatch_runtime,
        reddog_signed_worker_openclaw_queue_loop_runtime_binding as binding_module,
    )
    from modules.communication.moltbot_bridge.src.openclaw_supervisor import (
        claim_reddog_signed_worker_dispatch_task_once,
    )
    from modules.communication.moltbot_bridge.src.reddog_signed_worker_agentdb_envelope import (
        WorkerDispatchAuthorityVerificationConfig,
        build_worker_dispatch_authority_context,
    )
    from modules.infrastructure.database.src import agent_db as agent_db_module

    monkeypatch.setenv("FOUNDUPS_DB_PATH", str(tmp_path / "foundups.db"))
    agent_db_module.DatabaseManager.reset_for_tests()
    AgentDB = agent_db_module.AgentDB
    trusted_now = datetime.fromisoformat(NOW)
    assurance_store = lambda: AgentDB(  # noqa: E731 - compact test factory
        assurance_now_provider=lambda: trusted_now
    )
    monkeypatch.setattr(
        binding_module,
        "_build_assurance_reservation_store",
        lambda _env: assurance_store(),
    )
    repo = _repo(tmp_path)
    principal_public, reddog_public, connector = _ed25519_signing_material()
    pilot_overrides = _pilot_path_overrides()
    snapshot, profile_payload, work_order = _ratchet_model_runtime_inputs(
        principal_public,
        reddog_public,
        pilot_overrides,
    )
    state = _write_runtime_json(tmp_path, "work_state.json", snapshot)
    profile = _write_runtime_json(
        tmp_path,
        "profile.json",
        profile_payload,
    )
    snapshots = _write_runtime_json(tmp_path, "snapshots.json", _snapshots())
    principals = _write_runtime_json(
        tmp_path, "principals.json", _principals(principal_public)
    )
    work_orders = _write_runtime_json(
        tmp_path,
        "work_orders.json",
        {"work_orders": {WORK_ORDER_ID: work_order}},
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
    outcome_store = tmp_path / "runtime" / "outcomes" / "ratchet.jsonl"
    exact_sha_evidence_runner = _FakeExactShaEvidenceRunner(
        branch_name=str(work_order["branch_name"])
    )
    draft_pr_runner = _FakeCommitDraftPrRunner(exact_sha_evidence_runner)
    monkeypatch.setattr(
        binding_module,
        "_build_draft_pr_runner",
        lambda **_kwargs: (draft_pr_runner, []),
    )
    monkeypatch.setattr(
        bootstrap_module,
        "_build_evidence_command_runner",
        lambda **_kwargs: (exact_sha_evidence_runner, ()),
    )
    monkeypatch.setattr(
        bootstrap_module,
        "build_model_runtime_verifier",
        lambda **_kwargs: (_FakeModelRuntimeBindingVerifier(), ()),
    )

    verifier_run = run_reddog_main_resident_queue_serial_loop_bootstrap(
        repo_root=repo,
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
        authority_state_path=authority_state,
        permission_snapshots_path=snapshots,
        principal_authority_records_path=principals,
        signer_socket_path=socket_path,
        signer_socket_connector=connector,
        signature_verifier_backend=REDDOG_SIGNATURE_VERIFIER_BACKEND_ED25519,
        worker_dispatch_writer=dispatch_runtime.AgentDbSignedWorkerDispatchTaskWriter(),
        assurance_reservation_store=assurance_store(),
        worktree_runner=worktree_runner,
        now_iso=NOW,
        now_epoch=1000,
        trusted_now_epoch=lambda: 1000,
        requested_queue_item_id="queue-1",
        max_steps=12,
    )
    assert verifier_run.accepted is True
    assert verifier_run.dispatched_stages[-1] == "assurance_capacity_admission"

    monkeypatch.setenv(
        "WRE_MOCK_SKILLS",
        dispatch_runtime.SIGNED_WORKER_DISPATCH_TASK_SKILL,
    )
    monkeypatch.setenv("REDDOG_SIGNED_WORKER_QUEUE_LOOP_RUNNER", "1")
    monkeypatch.setenv("REDDOG_RESIDENT_RUNTIME_ROOT", str(tmp_path / "runtime"))
    monkeypatch.setenv("REDDOG_AUTHORITATIVE_WORK_STATE_PATH", str(state))
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_CHAIN_RESULTS_PATH", str(chain))
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_AUTHORITY_PROFILE_PATH", str(profile))
    monkeypatch.setenv("REDDOG_WORK_ORDERS_PATH", str(work_orders))
    monkeypatch.setenv("REDDOG_GENERIC_WRITER_DRYRUN_RESULT_PATH", str(generic_writer))
    monkeypatch.setenv("REDDOG_GOVERNED_SHELL_DRYRUN_RESULT_PATH", str(governed_shell))
    monkeypatch.setenv("REDDOG_HOLOINDEX_EVIDENCE_PATH", str(holoindex))
    monkeypatch.setenv("REDDOG_SLICE_VERIFIER_REQUEST_PATH", str(verifier))
    monkeypatch.setenv("REDDOG_ARTIFACT_GENERATION_REQUEST_BINDING", "1")
    monkeypatch.setenv("REDDOG_ARTIFACT_GENERATOR_MODE", "foundups_fusion")
    monkeypatch.setenv(
        "REDDOG_MODEL_RUNTIME_AVAILABLE_PROVIDERS",
        "openrouter",
    )
    monkeypatch.setenv("OPENCLAW_SIGNED_0102_BOUNDED_CODE_TASKS_ENABLED", "1")
    monkeypatch.setenv("REDDOG_SIGNED_WORKER_QUEUE_LOOP_MAX_STEPS", "2")
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_NOW_ISO", NOW)
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_NOW_EPOCH", "1000")
    monkeypatch.setenv("REDDOG_AUTHORITY_RUNTIME_STATE_PATH", str(authority_state))
    monkeypatch.setenv("REDDOG_PERMISSION_SNAPSHOTS_PATH", str(snapshots))
    monkeypatch.setenv(
        "REDDOG_PRINCIPAL_AUTHORITY_RECORDS_PATH",
        str(principals),
    )
    monkeypatch.setenv(
        "REDDOG_SIGNATURE_VERIFIER_BACKEND",
        REDDOG_SIGNATURE_VERIFIER_BACKEND_ED25519,
    )
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-openrouter-key")
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
    authority_context = build_worker_dispatch_authority_context(
        config=WorkerDispatchAuthorityVerificationConfig(
            repo_root=str(repo),
            runtime_allowed_root=str(tmp_path / "runtime"),
            authority_state_path=str(authority_state),
            permission_snapshots_path=str(snapshots),
            principal_authority_records_path=str(principals),
            signature_verifier_backend=REDDOG_SIGNATURE_VERIFIER_BACKEND_ED25519,
        ),
        trusted_now_epoch=lambda: 1000,
    )
    author_result = claim_reddog_signed_worker_dispatch_task_once(
        repo_root=repo,
        agent_db_factory=assurance_store,
        authority_verification_context=authority_context,
    )
    assert author_result["accepted"] is True, json.dumps(
        author_result, sort_keys=True, default=str
    )
    assert author_result["capability"] == "bounded_code_change"
    author_chain = json.loads(chain.read_text(encoding="utf-8"))["stage_results"]
    assert author_chain["exact_sha_commit"]["decision"] == (
        "RESIDENT_QUEUE_EXACT_SHA_COMMIT_ACCEPT"
    )
    assert author_chain["exact_sha_commit"]["commit_receipt"]["base_sha"] == "b" * 40
    assert author_chain["exact_sha_commit"]["commit_receipt"]["head_sha"] == "a" * 40
    assert author_chain["exact_sha_commit"]["commit_receipt"]["changed_paths"] == [
        PILOT_ARTIFACT
    ]
    verifier_result = claim_reddog_signed_worker_dispatch_task_once(
        repo_root=repo,
        agent_db_factory=assurance_store,
        authority_verification_context=authority_context,
    )
    assert verifier_result["accepted"] is True, json.dumps(
        verifier_result, sort_keys=True, default=str
    )
    assert verifier_result["capability"] == "independent_slice_verification"
    verifier_stage = json.loads(chain.read_text(encoding="utf-8"))["stage_results"][
        "slice_verifier"
    ]
    ratchet_request = _write_runtime_json(
        tmp_path,
        "ratchet_request.json",
        _outcome_ratchet_request(verifier_stage["verifier_result"]),
    )

    ratchet_run = run_reddog_main_resident_queue_serial_loop_bootstrap(
        repo_root=repo,
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
        ratchet_request_path=ratchet_request,
        outcome_ratchet_store_path=outcome_store,
        authority_state_path=authority_state,
        permission_snapshots_path=snapshots,
        principal_authority_records_path=principals,
        signer_socket_path=socket_path,
        signer_socket_connector=connector,
        signature_verifier_backend=REDDOG_SIGNATURE_VERIFIER_BACKEND_ED25519,
        worker_dispatch_writer=_FakeWorkerDispatchTaskWriter(),
        worktree_runner=worktree_runner,
        draft_pr_runner=draft_pr_runner,
        now_iso=NOW,
        now_epoch=1000,
        trusted_now_epoch=lambda: 1000,
        requested_queue_item_id="queue-1",
        max_steps=2,
    )
    assert ratchet_run.accepted is True
    stored = json.loads(chain.read_text(encoding="utf-8"))
    assert stored["stage_results"]["verified_outcome_ratchet"]["decision"] == (
        "QUEUE_AUTHORIZED_VERIFIED_OUTCOME_RATCHET_INVOKE_ACCEPT"
    )

    return {
        "repo": repo,
        "state": state,
        "profile": profile,
        "chain": chain,
        "verifier_stage": verifier_stage,
    }
