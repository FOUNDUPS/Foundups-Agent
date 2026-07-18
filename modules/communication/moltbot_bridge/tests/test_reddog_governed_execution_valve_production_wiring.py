"""Production-path wiring tests for the governed RedDog execution valve."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from modules.communication.moltbot_bridge.src import (
    reddog_main_resident_queue_serial_loop_bootstrap as bootstrap,
)
from modules.communication.moltbot_bridge.src.reddog_execution_valve_use_time_authority import (
    GovernedValveUseTimeAuthorityResolver,
    SIGNED_RUNTIME_ARTIFACT_MANIFEST_PRODUCER_MISSING,
    _digest,
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
    repo, runtime = _roots(tmp_path)
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
    dependency_bundle = SimpleNamespace(
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
        authority_state_path=runtime / "authority_state.json",
        permission_snapshots_path=runtime / "permission_snapshots.json",
        principal_authority_records_path=runtime / "principal_authority_records.json",
        requested_queue_item_id=QUEUE_ID,
        now_iso=NOW,
        now_epoch=dependency_bundle.now_epoch,
        max_steps=1,
    )

    assert result.accepted is True, result.rejection_reasons
    assert isinstance(captured["valve_environment"], GovernedExecutionValveEnvironment)
    resolver = captured["governed_use_time_authority_resolver"]
    assert isinstance(resolver, GovernedValveUseTimeAuthorityResolver)
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
    repo, runtime = _roots(tmp_path)
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
    repo, runtime = _roots(tmp_path)
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
        work_order_materializer_mode="authority_profile",
        valve_environment_path=link,
        requested_queue_item_id=QUEUE_ID,
        now_iso=NOW,
        max_steps=1,
    )

    assert result.accepted is False
    assert result.rejection_reasons == ("malformed_valve_environment",)


def test_real_use_time_resolver_reverifies_without_consuming_and_names_missing_anchors(
    tmp_path, monkeypatch,
) -> None:
    repo, runtime = _roots(tmp_path)
    valve = json.loads((runtime / "execution_valve_env.json").read_text(encoding="utf-8"))
    work_order_id = valve["work_order_id"]
    work_authority = {
        "work_order_id": work_order_id,
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
        signature_verifier=object(),
        principal_key_resolver=object(),
        nonce_store=object(),
        snapshot_resolver=object(),
        revocation_oracle=object(),
        now_epoch=1_784_006_400,
        required_valve_state="VALVE_OPEN_WORKTREE_CREATE",
    )

    result = resolver.resolve(
        chain_state=store.load(),
        work_order={"work_order_id": work_order_id},
        queue_item_id=QUEUE_ID,
        selected_slice="REDDOG_TEST_SLICE_PHASE1",
    )

    assert len(calls) == 1
    assert (
        calls[0]["verification_phase"]
        == WorkAuthorityVerificationPhase.PREFLIGHT_NON_CONSUMING
    )
    assert result.signed_authority_reverified is True
    assert result.authoritative_use_lease is None
    assert SIGNED_RUNTIME_ARTIFACT_MANIFEST_PRODUCER_MISSING in result.rejection_reasons
    assert "canonical_consensus_receipt_verifier_missing" in result.rejection_reasons
    assert "canonical_sovereign_authorization_verifier_missing" in result.rejection_reasons
