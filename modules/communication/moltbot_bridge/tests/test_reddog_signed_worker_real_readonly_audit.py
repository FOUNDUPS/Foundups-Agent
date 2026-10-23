"""Focused extraction from the inherited integration matrix."""

from __future__ import annotations

from pathlib import Path

from modules.communication.moltbot_bridge.src.reddog_signed_authority_worker_dispatch_dryrun import (
    plan_reddog_signed_authority_worker_dispatch_dry_run,
)
from modules.communication.moltbot_bridge.src.reddog_work_authority_digest import (
    canonical_work_authority_digest,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import (
    InMemoryNonceStore,
    verify_delegated_work_authority,
)
from modules.communication.moltbot_bridge.src.reddog_worker_dispatch_authority_binding import (
    WorkerDispatchAuthorityVerificationContext,
    recorded_authority_verification_binding,
)
from modules.communication.moltbot_bridge.tests.reddog_resident_queue_test_helpers import (
    worker_dispatch_queue_receipt,
    worker_dispatch_queue_receipt_digest,
    worker_dispatch_work_order_digest,
)
from modules.communication.moltbot_bridge.tests.reddog_signed_worker_dispatch_test_support import (
    signed_audit_stage_binding,
)
from modules.communication.moltbot_bridge.tests.test_reddog_signer_delegated_authority_runtime import (
    _NoRevocation as _SignerNoRevocation,
    _PrincipalKeyResolver as _SignerPrincipalKeyResolver,
    _issue as _issue_delegated_authority,
)

from modules.communication.moltbot_bridge.tests.test_reddog_signed_worker_dispatch_task_executor import (
    AgentDB,
    RUNTIME_SURFACE_READONLY_AUDIT,
    _EchoEvidenceModelRunner,
    _FakeQueryAdapter,
    _mapping_digest,
    _repo_with_readonly_target,
    _snapshot,
    canonical_model_runtime_binding_digest,
    claim_reddog_signed_worker_dispatch_task_once,
    json,
    isolated_agent_db,  # noqa: F401
    model_selection_and_runtime_binding_receipts,
    runtime,
    subprocess,
    verification_receipt_digest,
    verified_runtime_binding_receipt,
)


def test_signer_issued_audit_reaches_real_readonly_worker_without_effects(
    tmp_path: Path,
    monkeypatch,
) -> None:
    selection, runtime_binding = model_selection_and_runtime_binding_receipts(
        runtime_surface=RUNTIME_SURFACE_READONLY_AUDIT,
    )
    runtime_verification = verified_runtime_binding_receipt(runtime_binding)
    assert runtime_verification is not None
    binding = signed_audit_stage_binding(runtime_binding=runtime_binding)
    allocation = binding["wsp15_allocation_receipt"]
    snapshot = _snapshot(
        allocation,
        slice_id="REDDOG_READONLY_AUDIT_PHASE1",
        model_selection_receipt=selection,
        model_selection_receipt_id=selection["receipt_id"],
        model_selection_digest=_mapping_digest(selection),
        model_runtime_binding_receipt=runtime_binding,
        model_runtime_binding_receipt_id=runtime_binding["receipt_id"],
        model_runtime_binding_digest=canonical_model_runtime_binding_digest(
            runtime_binding
        ),
        model_runtime_binding_verification_receipt_id=(runtime_verification.receipt_id),
        model_runtime_binding_verification_digest=verification_receipt_digest(
            runtime_verification
        ),
        **{
            key: binding[key]
            for key in (
                "progressive_policy_stage_receipt_id",
                "progressive_policy_stage_digest",
                "progressive_policy_stage_receipt",
            )
        },
    )
    queue_item = snapshot["wre_queue_items"][0]
    issued, signer, _, snapshot_resolver = _issue_delegated_authority(
        **binding,
        work_order_id="wo-1",
        work_order_digest=worker_dispatch_work_order_digest(snapshot),
        queue_consumer_receipt_digest=worker_dispatch_queue_receipt_digest(snapshot),
        queue_consumer_receipt=worker_dispatch_queue_receipt(snapshot),
        requested_operation=allocation["requested_operation"],
        allowed_paths=(),
        denied_paths=(),
        model_selection_receipt_id=queue_item["model_selection_receipt_id"],
        model_selection_digest=queue_item["model_selection_digest"],
        model_runtime_binding_receipt_id=queue_item["model_runtime_binding_receipt_id"],
        model_runtime_binding_digest=queue_item["model_runtime_binding_digest"],
        model_runtime_binding_verification_receipt_id=queue_item[
            "model_runtime_binding_verification_receipt_id"
        ],
        model_runtime_binding_verification_digest=queue_item[
            "model_runtime_binding_verification_digest"
        ],
        memex_supply_receipt_id=queue_item["memex_supply_receipt_id"],
        memex_supply_digest=queue_item["memex_supply_digest"],
        valve_state_required="VALVE_OPEN_DRYRUN_ONLY",
        consensus_receipt_digest=None,
        sovereign_authorization_digest=None,
    )
    assert issued.accepted and issued.identity and issued.work_authority
    verified = verify_delegated_work_authority(
        work_authority=issued.work_authority,
        identity=issued.identity,
        signature_verifier=signer,
        principal_key_resolver=_SignerPrincipalKeyResolver(),
        nonce_store=InMemoryNonceStore(),
        snapshot_resolver=snapshot_resolver,
        revocation_oracle=_SignerNoRevocation(),
        now=1000,
        required_valve_state="VALVE_OPEN_DRYRUN_ONLY",
    )
    assert verified.accepted is True, verified.reason_codes
    authority_runtime = {
        "decision": "QUEUE_AUTHORITY_RUNTIME_INVOKE_ACCEPT",
        "authority_result": issued.to_dict(),
    }
    authority_verification = {
        "decision": "QUEUE_AUTHORITY_VERIFICATION_INVOKE_ACCEPT",
        "verified_work_authority_digest": canonical_work_authority_digest(
            issued.work_authority
        ),
        "verification_result": verified.to_dict(),
    }
    authority_verification.update(
        recorded_authority_verification_binding(
            authority_runtime,
            authority_verification,
        )
    )
    dryrun = plan_reddog_signed_authority_worker_dispatch_dry_run(
        explicit_signed_authority_worker_dispatch_dryrun_requested=True,
        queue_authority_verification_result=authority_verification,
        queue_authority_runtime_result=authority_runtime,
        wsp15_allocation_receipt=allocation,
    ).to_dict()
    context = WorkerDispatchAuthorityVerificationContext(
        signature_verifier=signer,
        principal_key_resolver=_SignerPrincipalKeyResolver(),
        nonce_store=InMemoryNonceStore(),
        snapshot_resolver=snapshot_resolver,
        revocation_oracle=_SignerNoRevocation(),
        trusted_now_epoch=lambda: 1000,
        required_valve_state="VALVE_OPEN_DRYRUN_ONLY",
    )
    published = runtime.publish_reddog_signed_worker_dispatch_runtime(
        worker_dispatch_dryrun_result=dryrun,
        queue_authority_runtime_result=authority_runtime,
        queue_authority_verification_result=authority_verification,
        authority_verification_context=context,
        work_state_snapshot=snapshot,
        queue_item_id="queue-1",
        writer=runtime.AgentDbSignedWorkerDispatchTaskWriter(),
    )
    assert published.accepted and len(published.tasks) == 1
    assert (
        published.tasks[0].context["model_runtime_binding_receipt"] == runtime_binding
    )

    repo = _repo_with_readonly_target(tmp_path)
    target = repo / "modules" / "foundups" / "paccess_001" / "src" / "worker.py"
    target.parent.mkdir(parents=True)
    target.write_text("VALUE = 1\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "commit", "-m", "test: add audit target"],
        check=True,
        capture_output=True,
    )
    head = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    from modules.communication.moltbot_bridge.src import (
        reddog_signed_worker_0102_readonly_review_binding as review_binding,
        reddog_signed_worker_agentdb_envelope as envelope_module,
    )

    model_runner = _EchoEvidenceModelRunner()
    readonly_runner = review_binding.Signed0102ReadOnlyReviewRunner(
        model_runner=model_runner,
        holoindex_adapter=_FakeQueryAdapter(head),
        codeindex_adapter=_FakeQueryAdapter(head),
    )
    monkeypatch.setattr(
        review_binding,
        "Signed0102ReadOnlyReviewRunner",
        lambda: readonly_runner,
    )
    monkeypatch.setattr(
        envelope_module,
        "build_worker_dispatch_authority_context_from_env",
        lambda **_: WorkerDispatchAuthorityVerificationContext(
            signature_verifier=signer,
            principal_key_resolver=_SignerPrincipalKeyResolver(),
            nonce_store=InMemoryNonceStore(),
            snapshot_resolver=snapshot_resolver,
            revocation_oracle=_SignerNoRevocation(),
            trusted_now_epoch=lambda: 1000,
            required_valve_state="VALVE_OPEN_DRYRUN_ONLY",
        ),
    )
    before = subprocess.run(
        ["git", "-C", str(repo), "status", "--porcelain"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout

    claimed = claim_reddog_signed_worker_dispatch_task_once(repo_root=repo)

    assert claimed["accepted"] is True, json.dumps(claimed, sort_keys=True)
    assert claimed["capability"] == "architect_review"
    assert model_runner.calls
    assert (
        subprocess.run(
            ["git", "-C", str(repo), "status", "--porcelain"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        == before
        == ""
    )
    assert not (repo / "artifact_generation_request.json").exists()
    assert "work_order_invocation" not in claimed
    assert (
        AgentDB().get_autonomous_task_by_id(published.tasks[0].task_id)["status"]
        == "completed"
    )
