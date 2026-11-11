"""Production-path wiring tests for the governed RedDog execution valve."""

from __future__ import annotations

import json
from dataclasses import replace
from types import SimpleNamespace

import pytest

from modules.communication.moltbot_bridge.src import (
    reddog_main_resident_queue_serial_loop_bootstrap as bootstrap,
)
from modules.communication.moltbot_bridge.src.reddog_execution_valve_use_time_authority import (
    AUTHENTICATED_RUNTIME_ARTIFACT_MANIFEST_SELECTION_MISSING,
    GovernedValveUseTimeAuthorityResolver,
    _digest,
    _signed_binding_reasons,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_binding import (
    canonical_full_work_order_digest,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_chain_results_store import (
    InMemoryResidentQueueChainResultsStore,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import (
    VerificationResult,
    WorkAuthorityVerificationPhase,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_serial_loop import (
    ResidentQueueSerialLoopResult,
)
from modules.communication.moltbot_bridge.src.reddog_wre_execution_valve import (
    ExecutionValveEnvironment,
    GovernedExecutionValveEnvironment,
)
from modules.communication.moltbot_bridge.tests.reddog_resident_live_canary_test_support import (
    NOW,
    QUEUE_ID,
    _roots,
)
from modules.communication.moltbot_bridge.tests.test_reddog_architect_fix_signed_wsp15_work_order_promotion import (
    _authority_profile,
    _promote,
)


def test_bootstrap_routes_canonical_environment_and_use_time_resolver(
    tmp_path, monkeypatch,
) -> None:
    repo, runtime = _roots(tmp_path, canonical_artifacts=True)
    valve_payload = json.loads(
        (runtime / "execution_valve_env.json").read_text(encoding="utf-8")
    )
    work_order_id = valve_payload["work_order_id"]
    work_orders_path = runtime / "work_orders.json"
    work_orders_path.write_text(
        json.dumps({"work_orders": {work_order_id: {"work_order_id": work_order_id}}}),
        encoding="utf-8",
    )
    captured: dict[str, object] = {}
    issuer = object()
    from modules.communication.moltbot_bridge.src.reddog_main_resident_queue_runtime_dependency_bundle import RedDogMainResidentQueueRuntimeDependencyBundle
    dependency_bundle = RedDogMainResidentQueueRuntimeDependencyBundle(
        accepted=True,
        rejection_reasons=(),
        status="READY",
        requested=True,
        authority_store=object(),
        signer=object(),
        principal_resolver=object(),
        snapshot_resolver=object(),
        signature_verifier=object(),
        principal_key_resolver=object(),
        nonce_store=object(),
        revocation_oracle=object(),
        now_epoch=1_784_006_400,
    )

    monkeypatch.setattr(
        bootstrap,
        "load_reddog_main_resident_queue_runtime_dependency_bundle",
        lambda **_: dependency_bundle,
    )

    def capture_registry(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(handlers={})

    monkeypatch.setattr(bootstrap, "build_reddog_resident_queue_stage_handler_registry", capture_registry)
    monkeypatch.setattr(
        bootstrap,
        "run_reddog_resident_queue_serial_loop",
        lambda **_: ResidentQueueSerialLoopResult(
            accepted=True,
            status="RESIDENT_QUEUE_SERIAL_LOOP_LIMIT_REACHED",
            steps_run=0,
        ),
    )

    result = bootstrap.run_reddog_main_resident_queue_serial_loop_bootstrap(
        repo_root=repo,
        work_state_path=runtime / "authoritative_work_state.json",
        chain_results_path=runtime / "chain_results.json",
        authority_profile_path=runtime / "authority_profile.json",
        work_orders_path=work_orders_path,
        valve_environment_path=runtime / "execution_valve_env.json",
        runtime_allowed_root=runtime,
        authority_state_path=runtime / "authority_state.json",
        permission_snapshots_path=runtime / "permission_snapshots.json",
        principal_authority_records_path=runtime / "principal_authority_records.json",
        requested_queue_item_id=QUEUE_ID,
        now_iso=NOW,
        now_epoch=dependency_bundle.now_epoch,
        max_steps=1,
        worktree_lease_issuer=issuer,
        signer_peer_secret_access_grant_supplier=issuer,
    )

    assert result.accepted is True, result.rejection_reasons
    assert captured["worktree_lease_issuer"] is issuer
    assert isinstance(captured["valve_environment"], GovernedExecutionValveEnvironment)
    resolver = captured["governed_use_time_authority_resolver"]
    assert isinstance(resolver, GovernedValveUseTimeAuthorityResolver)
    assert resolver.signer_peer_secret_access_grant_supplier is issuer
    assert resolver.valve_environment_path == runtime / "execution_valve_env.json"
    assert resolver.permission_snapshots_path == runtime / "permission_snapshots.json"


def test_real_promotion_materializes_complete_governed_work_order() -> None:
    promoted, store = _promote(
        authority_profile=_authority_profile(
            allowed_paths=["modules/foundups/paccess_001/**"],
            denied_paths=["modules/foundups/paccess_001/secrets/**"],
        )
    )
    assert promoted.accepted is True
    assert promoted.authority_profile is not None
    snapshot = store.load()
    queue = snapshot["wre_queue_items"][0]

    work_orders, reasons = bootstrap._materialize_work_orders_from_authority_profile(
        snapshot=snapshot,
        authority_profile=promoted.authority_profile,
        requested_queue_item_id=queue["queue_item_id"],
        now_iso="2026-07-16T00:10:00+00:00",
    )

    assert reasons == ()
    assert work_orders is not None
    work_order = work_orders[promoted.authority_profile["work_order_id"]]
    allocation = queue["wsp15_allocation_receipt"]
    assert work_order["foundup_id"] == promoted.authority_profile["foundup_id"]
    assert work_order["valve_state_required"] == "VALVE_OPEN_WORKTREE_CREATE"
    assert work_order["wsp15_allocation_receipt"] == allocation
    assert work_order["wsp15_allocation_receipt_id"] == allocation["receipt_id"]
    assert work_order["wsp15_priority"] == allocation["priority"]
    assert work_order["wsp15_mps_total"] == allocation["mps_total"]
    assert work_order["wsp15_reasoning_tier"] == allocation["reasoning_tier"]


def test_bootstrap_rejects_legacy_token_json_before_registry_or_worktree_stage(
    tmp_path, monkeypatch,
) -> None:
    repo, runtime = _roots(tmp_path, canonical_artifacts=True)
    valve_payload = json.loads(
        (runtime / "execution_valve_env.json").read_text(encoding="utf-8")
    )
    work_order_id = valve_payload["work_order_id"]
    work_orders_path = runtime / "work_orders.json"
    work_orders_path.write_text(
        json.dumps({"work_orders": {work_order_id: {"work_order_id": work_order_id}}}),
        encoding="utf-8",
    )
    legacy_path = runtime / "legacy_valve.json"
    legacy_path.write_text(
        json.dumps(
            {
                "valve_worktree_create_enabled": True,
                "sovereign_worktree_token": "attacker-controlled-token",
            }
        ),
        encoding="utf-8",
    )
    dependency_calls = 0
    registry_calls = 0

    def dependency_bundle(**_):
        nonlocal dependency_calls
        dependency_calls += 1
        raise AssertionError("dependency bundle must not be constructed")

    def registry(**_):
        nonlocal registry_calls
        registry_calls += 1
        raise AssertionError("effectful registry must not be constructed")

    monkeypatch.setattr(
        bootstrap, "load_reddog_main_resident_queue_runtime_dependency_bundle", dependency_bundle
    )
    monkeypatch.setattr(
        bootstrap, "build_reddog_resident_queue_stage_handler_registry", registry
    )

    result = bootstrap.run_reddog_main_resident_queue_serial_loop_bootstrap(
        repo_root=repo,
        work_state_path=runtime / "authoritative_work_state.json",
        chain_results_path=runtime / "chain_results.json",
        authority_profile_path=runtime / "authority_profile.json",
        work_orders_path=work_orders_path,
        valve_environment_path=legacy_path,
        runtime_allowed_root=runtime,
        requested_queue_item_id=QUEUE_ID,
        now_iso=NOW,
        max_steps=1,
    )

    assert result.accepted is False
    assert result.rejection_reasons == (
        "governed_execution_valve_environment_required",
    )
    assert dependency_calls == 0
    assert registry_calls == 0


def test_registry_rejects_legacy_environment_with_zero_handlers() -> None:
    from modules.communication.moltbot_bridge.src.reddog_resident_queue_stage_handler_registry import (
        build_reddog_resident_queue_stage_handler_registry,
    )

    registry = build_reddog_resident_queue_stage_handler_registry(
        work_state_snapshot={},
        chain_results_store=InMemoryResidentQueueChainResultsStore(),
        now_iso=NOW,
        valve_environment=ExecutionValveEnvironment(
            valve_worktree_create_enabled=True,
            sovereign_worktree_token="attacker-controlled-token",
        ),  # type: ignore[arg-type]
    )

    assert registry.handlers == {}
    assert registry.missing_stage_reasons["production_environment"] == (
        "governed_execution_valve_environment_required",
    )


def test_bootstrap_rejects_symlinked_valve_artifact_before_dependency_bundle(
    tmp_path, monkeypatch,
) -> None:
    repo, runtime = _roots(tmp_path, canonical_artifacts=True)
    valve = json.loads((runtime / "execution_valve_env.json").read_text(encoding="utf-8"))
    work_order_id = valve["work_order_id"]
    work_orders_path = runtime / "work_orders.json"
    work_orders_path.write_text(json.dumps({"work_orders": {
        work_order_id: {"work_order_id": work_order_id}}}), encoding="utf-8")
    link = runtime / "valve-link.json"
    try:
        link.symlink_to(runtime / "execution_valve_env.json")
    except OSError as exc:
        pytest.skip(f"symlink creation unavailable: {exc}")
    monkeypatch.setattr(
        bootstrap,
        "load_reddog_main_resident_queue_runtime_dependency_bundle",
        lambda **_: (_ for _ in ()).throw(
            AssertionError("dependency bundle must not be constructed")
        ),
    )

    result = bootstrap.run_reddog_main_resident_queue_serial_loop_bootstrap(
        repo_root=repo,
        work_state_path=runtime / "authoritative_work_state.json",
        chain_results_path=runtime / "chain_results.json",
        authority_profile_path=runtime / "authority_profile.json",
        work_orders_path=work_orders_path,
        valve_environment_path=link,
        runtime_allowed_root=runtime,
        requested_queue_item_id=QUEUE_ID,
        now_iso=NOW,
        max_steps=1,
    )

    assert result.accepted is False
    assert result.rejection_reasons == ("malformed_valve_environment",)


@pytest.mark.parametrize("fresh_now", [1_784_006_400, 1_784_006_405, True, None, 1_784_006_399])
def test_real_use_time_resolver_reverifies_without_consuming_and_names_missing_anchors(
    tmp_path, monkeypatch, fresh_now,
) -> None:
    repo, runtime = _roots(tmp_path, canonical_artifacts=True)
    valve = json.loads((runtime / "execution_valve_env.json").read_text(encoding="utf-8"))
    work_order_id = valve["work_order_id"]
    work_order = {"work_order_id": work_order_id, "base_ref": "main"}
    work_authority = {
        "work_order_id": work_order_id,
        "work_order_digest": canonical_full_work_order_digest(work_order),
        "base_ref": "main",
        "nonce": "nonce-use-time",
        "expires_at": 1_784_006_700,
    }
    stages = {
        "authority_runtime": {
            "decision": "QUEUE_AUTHORITY_RUNTIME_INVOKE_ACCEPT",
            "authority_result": {
                "accepted": True,
                "receipt": {
                    "status": "DELEGATED_AUTHORITY_ISSUED",
                    "work_authority_digest": _digest(work_authority),
                },
                "identity": {"principal_id": "github:mjtrout"},
                "work_authority": work_authority,
            },
        },
        "authority_verification": {
            "decision": "QUEUE_AUTHORITY_VERIFICATION_INVOKE_ACCEPT",
            "verification_result": {
                "accepted": True,
                "work_order_id": work_order_id,
            },
        },
    }
    store = InMemoryResidentQueueChainResultsStore()
    store.commit(
        {
            "schema_version": "reddog_resident_queue_chain_results.v1",
            "queue_item_id": QUEUE_ID,
            "selected_slice": "REDDOG_TEST_SLICE_PHASE1",
            "stage_results": stages,
            "receipts": [{"store_revision": None}],
        },
        expected_revision=None,
    )
    calls: list[dict[str, object]] = []

    def verify(**kwargs):
        calls.append(kwargs)
        return VerificationResult(accepted=True, work_order_id=work_order_id)

    monkeypatch.setattr(
        "modules.communication.moltbot_bridge.src.reddog_execution_valve_use_time_authority.verify_delegated_work_authority",
        verify,
    )
    resolver = GovernedValveUseTimeAuthorityResolver(
        repo_root=repo,
        work_state_path=runtime / "authoritative_work_state.json",
        authority_profile_path=runtime / "authority_profile.json",
        permission_snapshots_path=runtime / "permission_snapshots.json",
        principal_authority_records_path=runtime / "principal_authority_records.json",
        valve_environment_path=runtime / "execution_valve_env.json",
        runtime_allowed_root=runtime,
        signature_verifier=object(),
        principal_key_resolver=object(),
        nonce_store=object(),
        snapshot_resolver=object(),
        revocation_oracle=object(),
        now_epoch=1_784_006_400,
        required_valve_state="VALVE_OPEN_WORKTREE_CREATE",
        trusted_now_epoch=lambda: fresh_now,
    )

    result = resolver.resolve(
        chain_state=store.load(),
        work_order=work_order,
        queue_item_id=QUEUE_ID,
        selected_slice="REDDOG_TEST_SLICE_PHASE1",
    )

    if type(fresh_now) is not int or fresh_now < resolver.now_epoch:
        assert not calls
        assert result.rejection_reasons == ("canonical_trusted_clock_invalid",)
        assert result.signed_authority_reverified is False
        return
    assert len(calls) == 1
    assert calls[0]["now"] == fresh_now
    assert (
        calls[0]["verification_phase"]
        == WorkAuthorityVerificationPhase.PREFLIGHT_NON_CONSUMING
    )
    assert result.signed_authority_reverified is True
    assert result.authoritative_use_lease is None
    assert AUTHENTICATED_RUNTIME_ARTIFACT_MANIFEST_SELECTION_MISSING in result.rejection_reasons
    assert "canonical_consensus_receipt_verifier_missing" in result.rejection_reasons
    assert "canonical_sovereign_authorization_verifier_missing" in result.rejection_reasons
    assert "canonical_model_selection_signed_evidence_verifier_missing" in result.rejection_reasons
    assert "canonical_memex_supply_signed_evidence_verifier_missing" in result.rejection_reasons

def test_use_time_binding_rejects_base_ref_and_full_work_order_splices() -> None:
    original = {"work_order_id": "wo-bound", "base_ref": "main", "task_summary": "one"}
    authority = {
        "work_order_id": "wo-bound",
        "base_ref": "main",
        "work_order_digest": canonical_full_work_order_digest(original),
    }
    spliced = dict(original)
    spliced["base_ref"] = "release"
    spliced["task_summary"] = "two"

    reasons = _signed_binding_reasons(authority, spliced, {})

    assert "canonical_signed_work_order_binding_mismatch:base_ref" in reasons
    assert "canonical_signed_work_order_binding_mismatch:work_order_digest" in reasons


def _parent_bootstrap_artifacts(tmp_path):
    """Use canonical fixture data without the canary helper's Git subprocesses."""
    from .reddog_live_canary_artifact_test_support import write_live_canary_artifacts
    repo, runtime = tmp_path / "bootstrap-repo", tmp_path / "bootstrap-runtime"
    repo.mkdir(); runtime.mkdir()
    write_live_canary_artifacts(repo=repo, runtime=runtime, queue_item_id=QUEUE_ID, now_iso=NOW)
    environment = json.loads((runtime / "execution_valve_env.json").read_text("utf-8"))
    work_id = environment["work_order_id"]
    (runtime / "work_orders.json").write_text(
        json.dumps({"work_orders": {work_id: {"work_order_id": work_id}}}), encoding="utf-8")
    return runtime, environment


def _capture_parent_bootstrap(monkeypatch, state, runtime, supplied):
    """Real bootstrap/resolver; dependency loading and stage dispatch are seams."""
    from modules.communication.moltbot_bridge.src.reddog_main_resident_queue_runtime_dependency_bundle import RedDogMainResidentQueueRuntimeDependencyBundle
    bundle = RedDogMainResidentQueueRuntimeDependencyBundle(
        accepted=True, status="READY", requested=True, rejection_reasons=(), now_epoch=1000)
    captured = {}
    def registry(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(handlers={})
    monkeypatch.setattr(bootstrap, "load_reddog_main_resident_queue_runtime_dependency_bundle", lambda **_: bundle)
    monkeypatch.setattr(bootstrap, "build_reddog_resident_queue_stage_handler_registry", registry)
    monkeypatch.setattr(bootstrap, "run_reddog_resident_queue_serial_loop", lambda **_: ResidentQueueSerialLoopResult(
        accepted=True, status="RESIDENT_QUEUE_SERIAL_LOOP_LIMIT_REACHED", steps_run=0))
    result = bootstrap.run_reddog_main_resident_queue_serial_loop_bootstrap(
        repo_root=state.repo, runtime_allowed_root=runtime,
        work_state_path=runtime / "authoritative_work_state.json",
        authority_profile_path=runtime / "authority_profile.json",
        chain_results_path=runtime / "chain_results.json",
        work_orders_path=runtime / "work_orders.json",
        valve_environment_path=runtime / "execution_valve_env.json",
        requested_queue_item_id=QUEUE_ID, now_iso=NOW, now_epoch=1000,
        trusted_now_epoch=lambda: state.now, max_steps=1, **supplied)
    assert result.accepted is True, result.rejection_reasons
    assert result.steps_run == 0
    assert captured["worktree_lease_issuer"] is None
    resolver = captured["governed_use_time_authority_resolver"]
    assert type(resolver) is GovernedValveUseTimeAuthorityResolver
    return resolver


def _recorded_parent_chain(identity, authority):
    """Canonical chain shape; prior signed-work acceptance is synthetic."""
    store = InMemoryResidentQueueChainResultsStore()
    store.commit({"schema_version": "reddog_resident_queue_chain_results.v1",
        "queue_item_id": QUEUE_ID, "selected_slice": "synthetic-parent-consensus",
        "receipts": [{"store_revision": None}], "stage_results": {
            "authority_runtime": {"decision": "QUEUE_AUTHORITY_RUNTIME_INVOKE_ACCEPT",
                "authority_result": {"accepted": True, "identity": identity, "work_authority": authority,
                    "receipt": {"receipt_id": "synthetic-prior-work", "status": "DELEGATED_AUTHORITY_ISSUED",
                        "work_order_id": authority["work_order_id"], "generated_at": 1000,
                        "identity_digest": _digest(identity), "work_authority_digest": _digest(authority)}}},
            "authority_verification": {"decision": "QUEUE_AUTHORITY_VERIFICATION_INVOKE_ACCEPT",
                "verification_result": {"accepted": True, "work_order_id": authority["work_order_id"]}}}},
        expected_revision=None)
    return store.load()


def _isolate_prior_parent_inputs(monkeypatch, environment, binding):
    """Earlier artifact/queue/signed-work/generation checks are explicit seams.

    resolve, _resolve_current, collection, parent/model signatures and lease
    recognition remain real. This does not qualify the upstream input bundle.
    """
    from modules.communication.moltbot_bridge.src import reddog_execution_valve_use_time_authority as resolver_module
    from modules.communication.moltbot_bridge.src import reddog_signer_current_generation_use_time_gate as gate
    monkeypatch.setattr(resolver_module, "_read_runtime_artifacts", lambda _: (
        {"valve_environment": environment, "authority_profile": {}}, []))
    monkeypatch.setattr(GovernedValveUseTimeAuthorityResolver, "_resolve_expected", staticmethod(lambda *args: {}))
    monkeypatch.setattr(GovernedValveUseTimeAuthorityResolver, "_validate_queue", lambda *args: {})
    monkeypatch.setattr(GovernedValveUseTimeAuthorityResolver, "_reverify_and_bind", lambda *args, **kwargs: True)
    monkeypatch.setattr(gate, "verify_signer_current_generation_runtime_binding", lambda **kwargs: binding)


def _assert_no_parent_effect_admission(resolution, work):
    from modules.communication.moltbot_bridge.src.reddog_worktree_admission_capability import InMemoryWorktreeAdmissionRegistry
    registry = InMemoryWorktreeAdmissionRegistry()
    assert resolution.authoritative_use_lease is None
    assert registry.issue(queue_item_id=QUEUE_ID, selected_slice="synthetic-parent-consensus",
        work_order=work, executor_plan_result={}, valve_decision={},
        signed_authority_reverified=resolution.signed_authority_reverified,
        authoritative_use_lease=resolution.authoritative_use_lease) is False
    assert registry._capabilities == {}


@pytest.mark.parametrize("case", ["valid", "omitted", "none", "mapping", "callable", "expired", "work", "generation"])
def test_bootstrap_parent_authority_reaches_real_use_time_verification(tmp_path, monkeypatch, case):
    from .test_reddog_parent_consensus_use_time import fixture, REASONS
    runtime, environment = _parent_bootstrap_artifacts(tmp_path)
    state, parent, binding, identity, authority, work = fixture(monkeypatch, tmp_path / "parent")
    supplied = {} if case == "omitted" else {"parent_consensus_authority": parent}
    called = []
    if case == "none": supplied["parent_consensus_authority"] = None
    if case == "mapping": supplied["parent_consensus_authority"] = {"accepted": True}
    if case == "callable": supplied["parent_consensus_authority"] = lambda *args: called.append(True)
    resolver = _capture_parent_bootstrap(monkeypatch, state, runtime, supplied)
    if case == "expired": state.now = 1020
    if case == "work": work = {**work, "different_work": True}
    if case == "generation": binding = replace(binding, generation=binding.generation + 1)
    _isolate_prior_parent_inputs(monkeypatch, environment, binding)
    result = resolver.resolve(chain_state=_recorded_parent_chain(identity, authority), work_order=work,
        queue_item_id=QUEUE_ID, selected_slice="synthetic-parent-consensus")
    reasons = set(result.rejection_reasons)
    unresolved = {"canonical_memex_supply_signed_evidence_verifier_missing",
                  "canonical_signer_client_peer_handshake_verifier_missing"}
    if case == "valid":
        assert reasons == unresolved
        assert state.reads > 0
    else:
        assert set(REASONS) <= reasons
        assert unresolved <= reasons
    assert called == []
    _assert_no_parent_effect_admission(result, work)
