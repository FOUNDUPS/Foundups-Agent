"""Focused resident-queue model runtime artifact integration coverage."""

import json
from pathlib import Path

import pytest

from modules.ai_intelligence.ai_gateway.src.model_runtime_binding_verified_admission import (
    discard_verified_runtime_binding_capability,
    verified_runtime_binding_receipt,
)
from modules.communication.moltbot_bridge.tests.model_runtime_binding_receipt_test_helpers import (
    model_runtime_binding_test_verifier,
    model_selection_and_runtime_binding_receipts,
)
from modules.communication.moltbot_bridge.src import (
    reddog_architect_fix_promotion_transaction,
    reddog_bounded_artifact_generation_runtime,
)
from modules.communication.moltbot_bridge.src.reddog_authority_profile_safety import (
    authority_profile_unknown_field_paths,
)
from modules.communication.moltbot_bridge.src.reddog_architect_fix_promotion_publication import (
    AtomicArchitectFixPromotionPublisher,
)
from modules.communication.moltbot_bridge.src.reddog_authoritative_work_state_refresh_runtime import (
    InMemoryAuthoritativeWorkStateStore,
)
from modules.communication.moltbot_bridge.src.reddog_bounded_artifact_generation_runtime import (
    FoundupsFusionArtifactGenerationRunner,
)
from modules.communication.moltbot_bridge.src.reddog_main_resident_queue_serial_loop_bootstrap import (
    _materialize_work_orders_from_authority_profile,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_bounded_worker_pilot_handler import (
    BOUNDED_WORKER_PILOT_STAGE_KEY,
    build_reddog_resident_queue_bounded_worker_pilot_stage_handler,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_next_stage_dispatch import (
    invoke_reddog_resident_queue_next_stage_dispatch,
)
from modules.communication.moltbot_bridge.src.reddog_wsp15_allocation_receipt import (
    allocate_reddog_wsp15_receipt,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_chain_results_store import (
    AtomicJsonResidentQueueChainResultsStore,
)
from modules.communication.moltbot_bridge.tests.model_runtime_binding_queue_test_helpers import (
    model_bound_profile,
    model_bound_snapshot,
    model_bound_work_order,
)
from modules.communication.moltbot_bridge.src.reddog_model_runtime_verifier_bootstrap import (
    build_model_runtime_verifier,
)
from modules.communication.moltbot_bridge.tests.test_reddog_main_resident_queue_serial_loop_bootstrap import (
    NOW,
    REDDOG_SIGNATURE_VERIFIER_BACKEND_ED25519,
    PILOT_ARTIFACT,
    PILOT_DOMAIN_ID,
    PILOT_OPERATION,
    PERMISSION_DIGEST,
    RUNTIME_SURFACE_ARTIFACT_GENERATION,
    WORK_ORDER_ID,
    _FakeArtifactGenerator,
    _FakeModelRuntimeBindingVerifier,
    _FakeWorkerDispatchTaskWriter,
    _FakeWorktreeRunner,
    _assert_bootstrap_yielded_at_assurance,
    _ed25519_signing_material,
    _pilot_path_overrides,
    _pilot_bounded_worker_plan,
    _pilot_allowed_paths,
    _pilot_payloads,
    _pilot_worktree_path,
    _principals,
    _repo,
    _snapshots,
    _valve_environment,
    _write_runtime_json,
    run_reddog_main_resident_queue_serial_loop_bootstrap,
)
from modules.communication.moltbot_bridge.tests.test_reddog_resident_queue_bounded_worker_pilot_handler import (
    _Resolver,
    _binding_stage_overrides,
    _seeded_store,
    _snapshot as _handler_snapshot,
    _valid_bundle,
    _work_order_with_plan,
)
from modules.communication.moltbot_bridge.tests.test_reddog_architect_fix_signed_wsp15_work_order_promotion import (
    _authority_profile,
    _determination,
    _promote,
    _rebind_determination_admission,
    _work_state,
)
from modules.communication.moltbot_bridge.tests.architect_proposal_promotion_test_helpers import (
    PRINCIPAL_PRIVATE_KEY,
    REDDOG_PRIVATE_KEY,
)
from modules.communication.moltbot_bridge.tests.test_reddog_wre_queue_authorized_bounded_worker_pilot_invoke import (
    ARTIFACT as HANDLER_ARTIFACT,
)


def test_bootstrap_generates_model_bound_artifacts_before_pilot(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path)
    principal_public, reddog_public, connector = _ed25519_signing_material(
        principal_key=PRINCIPAL_PRIVATE_KEY,
        reddog_key=REDDOG_PRIVATE_KEY,
    )
    selection, binding = model_selection_and_runtime_binding_receipts(
        runtime_surface=RUNTIME_SURFACE_ARTIFACT_GENERATION
    )
    verification = verified_runtime_binding_receipt(binding)
    assert verification is not None
    snapshot = model_bound_snapshot(selection, binding, verification)
    state = _write_runtime_json(tmp_path, "work_state.json", snapshot)
    overrides = _pilot_path_overrides()
    profile = _write_runtime_json(
        tmp_path,
        "profile.json",
        model_bound_profile(
            principal_public, reddog_public, selection, binding, verification, overrides
        ),
    )
    work_order = model_bound_work_order(
        selection, binding, verification, overrides
    )
    paths = _runtime_paths(tmp_path, repo, work_order, principal_public)
    artifact_generator = _FakeArtifactGenerator(content="# generated by bootstrap\n")
    result = _run_bootstrap(
        repo, state, profile, paths, connector, artifact_generator
    )
    _assert_bootstrap_yielded_at_assurance(result, paths["chain"])
    assert artifact_generator.calls == []


def test_malformed_model_runtime_verifier_config_fails_closed(
    tmp_path: Path,
) -> None:
    verifier, reasons = build_model_runtime_verifier(
        repo_root=tmp_path / "repo",
        runtime_root=tmp_path / "runtime",
        config={"unexpected_authority_field": "attacker"},
        trusted_now=lambda: 1000,
        artifact_generator=object(),
    )

    assert verifier is None
    assert reasons == ("malformed_model_runtime_verifier_config",)


def test_bounded_plan_authority_schema_rejects_shadow_model_receipts() -> None:
    profile = _authority_profile(
        bounded_worker_plan={
            "operation": "bounded",
            "model_runtime_binding_receipt": {"receipt_id": "attacker"},
        }
    )

    assert authority_profile_unknown_field_paths(profile, seed=False) == (
        "bounded_worker_plan.model_runtime_binding_receipt",
    )


def test_assigned_worker_reverifies_signed_model_evidence_before_provider(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bundle = _valid_bundle(tmp_path)
    work_order = _work_order_with_plan(bundle)
    runtime_binding = work_order["model_runtime_binding_receipt"]
    verification = verified_runtime_binding_receipt(runtime_binding)
    verifier = model_runtime_binding_test_verifier(runtime_binding)
    assert verification is not None and verifier is not None
    probe = verifier.verify(
        binding=runtime_binding,
        selection=work_order["model_selection_receipt"],
    )
    discard_verified_runtime_binding_capability(probe)
    chain_store = _seeded_store(bundle, **_binding_stage_overrides())
    provider_calls: list[dict[str, object]] = []

    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr(
        reddog_bounded_artifact_generation_runtime,
        "_load_foundups_fusion_runner",
        lambda: _provider_stub(provider_calls),
    )
    handler = build_reddog_resident_queue_bounded_worker_pilot_stage_handler(
        chain_results_store=chain_store,
        work_order_resolver=_Resolver(work_order),
        generic_writer_dryrun_result=bundle["generic_writer_dryrun_result"],
        governed_shell_dryrun_result=bundle["governed_shell_dryrun_result"],
        artifact_contents={},
        artifact_generation_request_binding_enabled=True,
            artifact_generator=FoundupsFusionArtifactGenerationRunner(
                runtime_mode="foundups_fusion",
                available_model_providers=("openrouter",),
            ),
        model_runtime_binding_verifier=verifier,
        repo_root=bundle["repo_root"],
    )

    result = invoke_reddog_resident_queue_next_stage_dispatch(
        explicit_resident_queue_stage_dispatch_requested=True,
        work_state_snapshot=_handler_snapshot(),
        store=chain_store,
        handlers={BOUNDED_WORKER_PILOT_STAGE_KEY: handler},
        now_iso="2026-07-14T00:00:00+00:00",
    )

    assert result.accepted is True, result.rejection_reasons
    assert len(provider_calls) == 1
    bridge_meta = provider_calls[0]["bridge_meta"]
    assert (
        bridge_meta["model_runtime_topology_verification_receipt_id"]
        == verification.receipt_id
    )
    stage = chain_store.load()["stage_results"][BOUNDED_WORKER_PILOT_STAGE_KEY]
    generation = stage["artifact_generation_result"]["receipt"]
    assert (
        generation["model_runtime_binding_verification_receipt_id"]
        == verification.receipt_id
    )


def test_promoted_queue_claim_materialization_reaches_exact_provider(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = _promoted_runtime_context(tmp_path, monkeypatch)
    provider_calls = _invoke_promoted_provider(context, monkeypatch)
    assert len(provider_calls) == 1
    _assert_continuous_lineage(
        context["queue_item"],
        context["worker_claim"],
        context["work_order"],
        provider_calls[0],
        context["chain_store"].load(),
    )


def _promoted_runtime_context(tmp_path, monkeypatch):
    repo = _repo(tmp_path)
    principal_public, reddog_public, connector = _ed25519_signing_material(
        principal_key=PRINCIPAL_PRIVATE_KEY,
        reddog_key=REDDOG_PRIVATE_KEY,
    )
    binding, snapshot, queue_item, worker_claim, work_order, authority_profile = (
        _promote_claimed_work_order(
            monkeypatch,
            tmp_path=tmp_path,
            repo=repo,
        )
    )
    state = _write_runtime_json(tmp_path, "promoted_work_state.json", snapshot)
    profile = _write_runtime_json(
        tmp_path, "promoted_authority_profile.json", authority_profile
    )
    paths = _runtime_paths(tmp_path, repo, work_order, principal_public)
    verifier = model_runtime_binding_test_verifier(binding)
    assert verifier is not None
    bootstrap = _run_bootstrap(
        repo,
        state,
        profile,
        paths,
        connector,
        _FakeArtifactGenerator(content="# bootstrap must not generate\n"),
        requested_queue_item_id=queue_item["queue_item_id"],
        model_runtime_binding_verifier=verifier,
    )
    _assert_bootstrap_yielded_at_assurance(bootstrap, paths["chain"])
    chain_store = AtomicJsonResidentQueueChainResultsStore(
        paths["chain"], allowed_root=tmp_path
    )
    return {
        "binding": binding,
        "snapshot": snapshot,
        "queue_item": queue_item,
        "worker_claim": worker_claim,
        "work_order": work_order,
        "repo": repo,
        "chain_store": chain_store,
    }


def _invoke_promoted_provider(context, monkeypatch):
    provider_calls: list[dict[str, object]] = []
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr(
        reddog_bounded_artifact_generation_runtime,
        "_load_foundups_fusion_runner",
        lambda: _provider_stub(provider_calls, PILOT_ARTIFACT),
    )
    handler = build_reddog_resident_queue_bounded_worker_pilot_stage_handler(
        chain_results_store=context["chain_store"],
        work_order_resolver=_Resolver(context["work_order"]),
        artifact_contents={},
        artifact_generation_request_binding_enabled=True,
        artifact_generator=FoundupsFusionArtifactGenerationRunner(
            runtime_mode="foundups_fusion",
            available_model_providers=("openrouter",),
        ),
        model_runtime_binding_verifier=model_runtime_binding_test_verifier(
            context["binding"]
        ),
        repo_root=context["repo"],
    )
    result = invoke_reddog_resident_queue_next_stage_dispatch(
        explicit_resident_queue_stage_dispatch_requested=True,
        work_state_snapshot=context["snapshot"],
        store=context["chain_store"],
        handlers={BOUNDED_WORKER_PILOT_STAGE_KEY: handler},
        now_iso=NOW,
    )
    assert result.accepted is True, result.rejection_reasons
    return provider_calls


def _promote_claimed_work_order(
    monkeypatch,
    *,
    tmp_path: Path,
    repo: Path,
):
    selection, binding = model_selection_and_runtime_binding_receipts(
        runtime_surface=RUNTIME_SURFACE_ARTIFACT_GENERATION,
        task_family="reddog_architect_fix_promotion",
    )
    allocation = allocate_reddog_wsp15_receipt(
        requested_operation=PILOT_OPERATION,
        prompt_text="Fix one bounded module defect",
        changed_paths=(PILOT_ARTIFACT,),
        allowed_read_targets=(PILOT_ARTIFACT,),
    ).to_dict()
    denied_paths = [
        f"modules/foundups/{PILOT_DOMAIN_ID}/**/.env",
        f"modules/foundups/{PILOT_DOMAIN_ID}/**/secrets/**",
    ]
    determination = _rebind_determination_admission(
        _determination(allocation=allocation),
        {
            "allowed_paths": _pilot_allowed_paths(),
            "denied_paths": denied_paths,
            "requested_operation": PILOT_OPERATION,
        },
    )
    monkeypatch.setattr(
        reddog_architect_fix_promotion_transaction,
        "_work_order_id",
        lambda _queue_item_id: WORK_ORDER_ID,
    )
    store = InMemoryAuthoritativeWorkStateStore(_work_state())
    publication_runtime = tmp_path / "publication_runtime"
    publisher = AtomicArchitectFixPromotionPublisher(
        repo_root=repo,
        runtime_root=publication_runtime,
        authority_profile_path=publication_runtime / "authority_profile.json",
        work_state_store=store,
    )
    promoted, store = _promote(
        store=store,
        model_selection_receipt=selection,
        model_runtime_binding_receipt=binding,
        authority_profile=_promoted_authority_profile(
            _promoted_bounded_worker_plan(),
            denied_paths=denied_paths,
        ),
        architect_determination=determination,
        authority_profile_publication_publisher=publisher.publish,
    )
    assert promoted.accepted is True, promoted.rejection_reasons
    snapshot = store.load()
    queue_item = snapshot["wre_queue_items"][0]
    work_orders, reasons = _materialize_work_orders_from_authority_profile(
        snapshot=snapshot,
        authority_profile=promoted.authority_profile,
        requested_queue_item_id=queue_item["queue_item_id"],
        now_iso=NOW,
    )
    assert reasons == ()
    assert work_orders is not None
    return (
        binding,
        snapshot,
        queue_item,
        snapshot["worker_claims"][0],
        work_orders[WORK_ORDER_ID],
        promoted.authority_profile,
    )


def _promoted_bounded_worker_plan():
    plan = _pilot_bounded_worker_plan()
    plan["shell_profile"].pop("secret_env_refs", None)
    return plan


def _promoted_authority_profile(
    plan,
    *,
    denied_paths,
):
    path_overrides = _pilot_path_overrides()
    path_overrides.pop("task_summary", None)
    path_overrides.pop("rollback_plan", None)
    path_overrides.pop("wsp15_allocation_receipt", None)
    path_overrides["denied_paths"] = list(denied_paths)
    return _authority_profile(
        foundup_id=PILOT_DOMAIN_ID,
        permission_snapshot_digest=PERMISSION_DIGEST,
        sovereign_authorization_digest="sha256:" + ("e" * 64),
        holoindex_evidence={
            "holoindex_query": "Promoted pAccess bounded artifact generation",
            "holoindex_status": "bundle_json_ok",
            "index_gap_detected": False,
            "retrieval_quality": "HIGH",
            "applicable_wsps": ["WSP_15", "WSP_50", "WSP_97"],
            "evidence_refs": [
                "modules/communication/moltbot_bridge/src/"
                "reddog_bounded_artifact_generation_runtime.py"
            ],
            "holoindex_freshness_receipt_digest": "sha256:" + ("f" * 64),
        },
        **path_overrides,
        bounded_worker_plan=plan,
    )


def _assert_continuous_lineage(queue_item, worker_claim, work_order, call, chain):
    expected = {field: work_order[field] for field in _LINEAGE_FIELDS}
    assert {field: queue_item[field] for field in _LINEAGE_FIELDS} == expected
    assert {field: worker_claim[field] for field in _LINEAGE_FIELDS} == expected
    bridge_meta = call["bridge_meta"]
    assert {field: bridge_meta[field] for field in _LINEAGE_FIELDS} == expected
    runtime = work_order["model_runtime_binding_receipt"]
    assert call["lead_model"] == runtime["principal_model"]
    assert call["panel_models"] == runtime["panel_models"]
    generation = chain["stage_results"][BOUNDED_WORKER_PILOT_STAGE_KEY][
        "artifact_generation_result"
    ]["receipt"]
    assert {field: generation[field] for field in _LINEAGE_FIELDS} == expected


def _provider_stub(calls, artifact_path=HANDLER_ARTIFACT):
    def run(_api_key, _prompt, _messages, payload):
        calls.append(dict(payload))
        return {
            "ok": True,
            "content": json.dumps(
                {"artifact_contents": {artifact_path: "# generated\n"}},
                sort_keys=True,
            ),
            "review_packet": {"receipt_id": "fusion-review:integration"},
        }

    return run


_LINEAGE_FIELDS = (
    "model_selection_receipt_id",
    "model_selection_digest",
    "model_runtime_binding_receipt_id",
    "model_runtime_binding_digest",
    "model_runtime_binding_verification_receipt_id",
    "model_runtime_binding_verification_digest",
)


def _run_bootstrap(
    repo,
    state,
    profile,
    paths,
    connector,
    artifact_generator,
    *,
    requested_queue_item_id="queue-1",
    model_runtime_binding_verifier=None,
):
    return run_reddog_main_resident_queue_serial_loop_bootstrap(
        repo_root=repo,
        work_state_path=state,
        chain_results_path=paths["chain"],
        authority_profile_path=profile,
        work_orders_path=paths["work_orders"],
        valve_environment_path=paths["valve_env"],
        generic_writer_dryrun_result_path=paths["generic_writer"],
        governed_shell_dryrun_result_path=paths["governed_shell"],
        artifact_generation_request_binding_enabled=True,
        holoindex_evidence_path=paths["holoindex"],
        authority_state_path=paths["authority_state"],
        permission_snapshots_path=paths["snapshots"],
        principal_authority_records_path=paths["principals"],
        signer_socket_path=paths["socket_path"],
        signer_socket_connector=connector,
        signature_verifier_backend=REDDOG_SIGNATURE_VERIFIER_BACKEND_ED25519,
        worker_dispatch_writer=_FakeWorkerDispatchTaskWriter(),
        worktree_runner=_FakeWorktreeRunner(),
        artifact_generator=artifact_generator,
        model_runtime_binding_verifier=(
            model_runtime_binding_verifier or _FakeModelRuntimeBindingVerifier()
        ),
        now_iso=NOW,
        now_epoch=1000,
        trusted_now_epoch=lambda: 1000,
        requested_queue_item_id=requested_queue_item_id,
        max_steps=11,
    )


def _runtime_paths(tmp_path: Path, repo: Path, work_order, principal_public):
    worktree = _pilot_worktree_path(repo, work_order)
    payloads = _pilot_payloads(repo, worktree, work_order)
    return {
        "work_orders": _write_runtime_json(
            tmp_path, "work_orders.json", {"work_orders": {WORK_ORDER_ID: work_order}}
        ),
        "valve_env": _write_runtime_json(
            tmp_path, "valve_env.json", _valve_environment()
        ),
        "generic_writer": _write_runtime_json(
            tmp_path, "generic_writer.json", payloads["generic_writer_dryrun_result"]
        ),
        "governed_shell": _write_runtime_json(
            tmp_path, "governed_shell.json", payloads["governed_shell_dryrun_result"]
        ),
        "holoindex": _write_runtime_json(
            tmp_path, "holoindex_evidence.json", payloads["holoindex_evidence"]
        ),
        "snapshots": _write_runtime_json(tmp_path, "snapshots.json", _snapshots()),
        "principals": _write_runtime_json(
            tmp_path, "principals.json", _principals(principal_public)
        ),
        "chain": tmp_path / "runtime" / "chain_results.json",
        "authority_state": tmp_path / "runtime" / "authority_state.json",
        "socket_path": tmp_path / "runtime" / "signer.sock",
    }
