"""Offline deterministic tests for `lego_topology_fixture_adapter`."""

from __future__ import annotations

import copy
import hashlib
import json
import pytest

from modules.foundups.simulator.adapters.lego_topology_fixture_adapter import (
    AGI_SCAFFOLDING_HYPOTHESIS_STATUS,
    BLOCKED_DEPENDENCY_CYCLE,
    BLOCKED_MISSING_BLOCK,
    BLOCKED_STALE_PROVENANCE,
    BLOCKED_UNKNOWN_CONSUMER,
    BLOCKED_UPSTREAM_DEPENDENCY,
    FORBIDDEN_RUNTIME_PROMOTION_ERROR,
    SIMULATED_EVIDENCE_ORIGIN,
    LegoTopologyAdapterConfig,
    SimulatedTransitionRecord,
    apply_stage_caps_to_sim_state,
    export_for_runtime_verification,
    guard_no_simulated_runtime_promotion,
    resolve_adapter_config,
    run_lego_topology_simulation,
)
from modules.foundups.simulator.config import SimulatorConfig
from modules.foundups.simulator.parameter_registry import load_bundle, to_simulator_config
from modules.foundups.simulator.state_contracts import (
    STAGE_TO_INT,
    ActorState,
    FoundUpState,
    FrozenDict,
    PoolState,
    SimState,
)


def _dynamic_sha256(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _dynamic_git_oid(label: str) -> str:
    raw = label.encode("utf-8")
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\x00" + raw).hexdigest()


def _three_block_foundup_fixture() -> dict:
    """Build a 1-FoundUp, 3-block topology using typed projection-compatible relations."""
    clean_blob_sha = _dynamic_sha256("auth_clean_blob_v1")
    stale_blob_sha = _dynamic_sha256("infra_committed_blob_v1")
    drifted_checkout_sha = _dynamic_sha256("infra_modified_checkout_v2")
    return {
        "blocks": [
            {
                "identity": {"canonical_id": "block_infra"},
                "readiness_state": "STALE_PROVENANCE_MISMATCH",
                "provenance_status": "STALE_PROVENANCE_MISMATCH",
                "byte_provenance": {
                    "git_blob_oid_sha1": _dynamic_git_oid("infra_v1"),
                    "git_blob_sha256": stale_blob_sha,
                    "checkout_bytes_sha256": drifted_checkout_sha,
                    "byte_status": "MODIFIED_CONTENT",
                },
                "verified_capabilities": [
                    {
                        "capability_id": "blob_store",
                        "status": "STALE_PROVENANCE_MISMATCH",
                        "verifier_receipt_id": "rcpt_stale_infra",
                    }
                ],
            },
            {
                "identity": {"canonical_id": "block_auth"},
                "readiness_state": "VERIFIED_CAPABILITY",
                "byte_provenance": {
                    "git_blob_oid_sha1": _dynamic_git_oid("auth_v1"),
                    "git_blob_sha256": clean_blob_sha,
                    "checkout_bytes_sha256": clean_blob_sha,
                    "byte_status": "CLEAN_EXACT_MATCH",
                },
                "verified_capabilities": [
                    {
                        "capability_id": "verify_session",
                        "status": "VERIFIED_CAPABILITY",
                        "verifier_receipt_id": "rcpt_clean_auth",
                    }
                ],
            },
            {
                "canonical_id": "block_api",
                "depends_on_block_ids": ["block_infra", "block_auth"],
                "readiness_state": "DOCUMENTED_ONLY",
                "triage": {"classification": "UNKNOWN_DYNAMIC_OR_EXTERNAL_CONSUMER"},
            },
        ],
        "relations": [
            {"relation_type": "BLOCK_IMPORTS_BLOCK", "source_id": "block_auth", "target_id": "block_infra"},
            {
                "relation_type": "FOUNDUP_TO_MODULE",
                "source_id": "foundup_carbon",
                "target_id": "block_infra",
                "required_capabilities": ["block_infra:blob_store"],
            },
            {
                "relation_type": "FOUNDUP_TO_MODULE",
                "source_id": "foundup_carbon",
                "target_id": "block_auth",
                "required_capabilities": ["block_auth:verify_session"],
            },
            {
                "relation_type": "FOUNDUP_TO_MODULE",
                "source_id": "foundup_carbon",
                "target_id": "block_api",
                "required_capabilities": ["block_api:serve_http"],
            },
        ],
    }


def test_disabled_by_default_and_baseline_invariance() -> None:
    baseline_before = load_bundle("baseline")
    sim_cfg_before = SimulatorConfig()
    assert "lego_topology_enabled" not in baseline_before.params
    assert sim_cfg_before.seed == 42
    assert sim_cfg_before.epoch_funding_mode == "legacy_unfunded"
    assert sim_cfg_before.pure_step_shadow_enabled is False

    adapter_cfg = LegoTopologyAdapterConfig()
    assert adapter_cfg.enabled is False
    resolved_default = resolve_adapter_config(baseline_before, simulator_config=sim_cfg_before)
    assert resolved_default.enabled is False
    assert resolved_default.scenario == "baseline"
    assert resolved_default.seed == 42

    with pytest.raises(ValueError, match="exact bool"):
        LegoTopologyAdapterConfig(enabled=1)  # type: ignore[arg-type]

    fixture = _three_block_foundup_fixture()
    fixture_copy = copy.deepcopy(fixture)
    base_state = SimState(
        tick=3,
        actors=FrozenDict({"agent_0": ActorState("agent_0", "agent", 100.0, 50.0, 0.618, 1)}),
        foundups=FrozenDict({"foundup_carbon": FoundUpState("foundup_carbon", STAGE_TO_INT["MVP"], 500.0, 0.8, 0.1)}),
        pools=PoolState(60.0, 16.0, 4.0, 16.0, 4.0),
        btc_reserve_total=0.1,
        fi_released_total=500.0,
    )

    assert run_lego_topology_simulation(fixture, ticks=4, base_sim_state=base_state) is None
    assert apply_stage_caps_to_sim_state(base_state, {}) is None
    assert fixture == fixture_copy
    assert base_state.foundups["foundup_carbon"].stage == STAGE_TO_INT["MVP"]
    assert load_bundle("baseline") == baseline_before
    assert to_simulator_config(baseline_before) == to_simulator_config(load_bundle("baseline"))


def test_typed_multi_block_dependency_gating_and_stage_progression() -> None:
    fixture = _three_block_foundup_fixture()
    fixture_snapshot = copy.deepcopy(fixture)
    base_state = SimState(
        tick=0,
        actors=FrozenDict({}),
        foundups=FrozenDict({"foundup_carbon": FoundUpState("foundup_carbon", STAGE_TO_INT["MVP"], 250.0, 0.7, 0.0)}),
        pools=PoolState(0.0, 0.0, 0.0, 0.0, 0.0),
        btc_reserve_total=0.0,
        fi_released_total=250.0,
    )

    tickets_by_tick = {
        # Tick 1: downstream block_api marks code ready early, while upstream block_infra is STILL stale!
        1: [{"ticket_id": "t_early_api", "block_id": "block_api", "sets_block_ready": True}],
        # Tick 2: upstream block_infra clears stale provenance + satisfies blob_store -> unblocks block_infra & block_auth;
        # block_api still has UNKNOWN_DYNAMIC_OR_EXTERNAL_CONSUMER -> FoundUp capped at PoC!
        2: [
            {
                "ticket_id": "t_fix_infra",
                "block_id": "block_infra",
                "clears_stale_provenance": True,
                "sets_block_ready": True,
                "satisfies_capabilities": ["blob_store"],
            }
        ],
        # Tick 3: block_api clears UNKNOWN_DYNAMIC_OR_EXTERNAL_CONSUMER -> 3/3 blocks ready, serve_http still pending -> Proto!
        3: [{"ticket_id": "t_triage_api", "block_id": "block_api", "clears_unknown_consumer": True}],
        # Tick 4: block_api satisfies serve_http -> 3/3 blocks ready + 3/3 capabilities -> MVP!
        4: [{"ticket_id": "t_cap_api", "block_id": "block_api", "satisfies_capabilities": ["serve_http"]}],
    }

    result = run_lego_topology_simulation(
        fixture,
        enabled=True,
        ticks=4,
        completed_tickets_by_tick=tickets_by_tick,
        base_sim_state=base_state,
    )
    assert result is not None
    assert fixture == fixture_snapshot
    assert base_state.foundups["foundup_carbon"].stage == STAGE_TO_INT["MVP"]

    # Tick 0: blocked by upstream STALE_PROVENANCE_MISMATCH + UNKNOWN_DYNAMIC_OR_EXTERNAL_CONSUMER -> Idea (0)
    p0 = result.snapshots[0].foundup_projections["foundup_carbon"]
    assert p0.stage_cap_name == "Idea"
    assert p0.stage_cap_int == STAGE_TO_INT["Idea"]
    assert result.snapshots[0].sim_state.foundups["foundup_carbon"].stage == STAGE_TO_INT["Idea"]
    assert BLOCKED_STALE_PROVENANCE in p0.blocking_reasons
    assert BLOCKED_UNKNOWN_CONSUMER in p0.blocking_reasons
    assert BLOCKED_UPSTREAM_DEPENDENCY in result.snapshots[0].blocks["block_auth"].blocking_reasons

    # Tick 1: premature downstream ticket cannot bypass upstream STALE_PROVENANCE_MISMATCH -> still Idea (0)
    p1 = result.snapshots[1].foundup_projections["foundup_carbon"]
    assert p1.stage_cap_name == "Idea"
    assert p1.ready_block_ids == ()

    # Tick 2: block_infra + block_auth now ready (2/3), block_api still blocked by UNKNOWN_DYNAMIC_OR_EXTERNAL_CONSUMER -> PoC (1)
    p2 = result.snapshots[2].foundup_projections["foundup_carbon"]
    assert p2.stage_cap_name == "PoC"
    assert result.snapshots[2].sim_state.foundups["foundup_carbon"].stage == STAGE_TO_INT["PoC"]
    assert p2.ready_block_ids == ("block_auth", "block_infra")
    assert p2.blocking_reasons == (BLOCKED_UNKNOWN_CONSUMER,)

    # Tick 3: all 3 blocks unblocked & ready, 2/3 capabilities satisfied -> Proto (3)
    p3 = result.snapshots[3].foundup_projections["foundup_carbon"]
    assert p3.stage_cap_name == "Proto"
    assert result.snapshots[3].sim_state.foundups["foundup_carbon"].stage == STAGE_TO_INT["Proto"]
    assert p3.ready_block_ids == ("block_api", "block_auth", "block_infra")
    assert p3.simulated_satisfied_capabilities == ("block_auth:verify_session", "block_infra:blob_store")

    # Tick 4: all 3 blocks + all 3 capabilities satisfied -> MVP (4)
    p4 = result.snapshots[4].foundup_projections["foundup_carbon"]
    assert p4.stage_cap_name == "MVP"
    assert result.final_sim_state.foundups["foundup_carbon"].stage == STAGE_TO_INT["MVP"]
    assert p4.simulated_satisfied_capabilities == (
        "block_api:serve_http",
        "block_auth:verify_session",
        "block_infra:blob_store",
    )


def test_simulated_vs_real_barrier_and_preserved_input_provenance() -> None:
    fixture = _three_block_foundup_fixture()
    result = run_lego_topology_simulation(
        fixture,
        enabled=True,
        ticks=1,
        completed_tickets_by_tick={
            1: [
                {
                    "ticket_id": "t_sim_infra",
                    "block_id": "block_infra",
                    "clears_stale_provenance": True,
                    "satisfies_capabilities": ["blob_store"],
                }
            ]
        },
    )
    assert result is not None
    assert result.evidence_origin == SIMULATED_EVIDENCE_ORIGIN
    assert result.runtime_verification_eligible is False
    assert result.agi_scaffolding_hypothesis_status == AGI_SCAFFOLDING_HYPOTHESIS_STATUS

    for snap in result.snapshots:
        assert snap.evidence_origin == SIMULATED_EVIDENCE_ORIGIN
        assert snap.runtime_verification_eligible is False
        guard_no_simulated_runtime_promotion(snap)
        for bstate in snap.blocks.values():
            assert bstate.evidence_origin == SIMULATED_EVIDENCE_ORIGIN
            assert bstate.runtime_verification_eligible is False
        for tr in snap.transitions:
            assert tr.evidence_origin == SIMULATED_EVIDENCE_ORIGIN
            assert tr.runtime_verification_eligible is False

    # Distinguish real pre-existing verified capabilities from simulated-only transitions:
    snap1 = result.snapshots[1]
    assert snap1.blocks["block_auth"].preserved_verified_capabilities == ("verify_session",)
    assert snap1.blocks["block_auth"].simulated_only_capabilities == ()
    assert snap1.blocks["block_infra"].preserved_verified_capabilities == ()
    assert snap1.blocks["block_infra"].simulated_only_capabilities == ("blob_store",)

    # Unconditional export & relabeling barriers:
    with pytest.raises(ValueError, match=FORBIDDEN_RUNTIME_PROMOTION_ERROR):
        export_for_runtime_verification(result)
    with pytest.raises(ValueError, match=FORBIDDEN_RUNTIME_PROMOTION_ERROR):
        export_for_runtime_verification(snap1.transitions[0], target_status="execution_feedback")
    with pytest.raises(ValueError, match=FORBIDDEN_RUNTIME_PROMOTION_ERROR):
        guard_no_simulated_runtime_promotion(snap1, requested_origin="VERIFIED_RUNTIME")
    with pytest.raises(ValueError, match=FORBIDDEN_RUNTIME_PROMOTION_ERROR):
        guard_no_simulated_runtime_promotion(snap1, requested_origin="execution_feedback")
    with pytest.raises(ValueError, match=FORBIDDEN_RUNTIME_PROMOTION_ERROR):
        guard_no_simulated_runtime_promotion(snap1, requested_runtime_eligible=True)
    with pytest.raises(ValueError, match=FORBIDDEN_RUNTIME_PROMOTION_ERROR):
        SimulatedTransitionRecord(0, "t0", "block_infra", "CAPABILITY_SIMULATED", "x", evidence_origin="VERIFIED_RUNTIME")
    with pytest.raises(ValueError, match=FORBIDDEN_RUNTIME_PROMOTION_ERROR):
        SimulatedTransitionRecord(0, "t0", "block_infra", "CAPABILITY_SIMULATED", "x", runtime_verification_eligible=True)

    # Smuggling simulated origin inside input fixture verified_capabilities must fail closed:
    poisoned = _three_block_foundup_fixture()
    poisoned["blocks"][1]["verified_capabilities"] = [
        {"capability_id": "forged_cap", "evidence_origin": SIMULATED_EVIDENCE_ORIGIN}
    ]
    with pytest.raises(ValueError, match=FORBIDDEN_RUNTIME_PROMOTION_ERROR):
        run_lego_topology_simulation(poisoned, enabled=True, ticks=1)


def test_cycle_and_missing_dependency_fail_closed_without_infinite_recursion() -> None:
    cyclic_and_missing_fixture = {
        "blocks": [
            {"canonical_id": "b_cycle_a", "depends_on_block_ids": ["b_cycle_b"], "initial_ready": True},
            {"canonical_id": "b_cycle_b", "depends_on_block_ids": ["b_cycle_a"], "initial_ready": True},
            {"canonical_id": "b_downstream_cycle", "depends_on_block_ids": ["b_cycle_a"], "initial_ready": True},
            {"canonical_id": "b_self_loop", "depends_on_block_ids": ["b_self_loop"], "initial_ready": True},
            {"canonical_id": "b_missing_dep", "depends_on_block_ids": ["nonexistent_core"], "initial_ready": True},
        ],
        "foundups": [
            {"foundup_id": "f_cycle", "required_block_ids": ["b_downstream_cycle"]},
            {"foundup_id": "f_self", "required_block_ids": ["b_self_loop"]},
            {"foundup_id": "f_missing_dep", "required_block_ids": ["b_missing_dep"]},
            {"foundup_id": "f_missing_direct", "required_block_ids": ["ghost_block"]},
        ],
    }

    res = run_lego_topology_simulation(cyclic_and_missing_fixture, enabled=True, ticks=2)
    assert res is not None
    final_snap = res.snapshots[-1]

    for cid in ("b_cycle_a", "b_cycle_b", "b_downstream_cycle", "b_self_loop"):
        assert BLOCKED_DEPENDENCY_CYCLE in final_snap.blocks[cid].blocking_reasons
        assert final_snap.blocks[cid].effective_ready is False

    assert BLOCKED_MISSING_BLOCK in final_snap.blocks["b_missing_dep"].blocking_reasons
    assert final_snap.foundup_projections["f_cycle"].blocking_reasons == (BLOCKED_DEPENDENCY_CYCLE,)
    assert final_snap.foundup_projections["f_self"].blocking_reasons == (BLOCKED_DEPENDENCY_CYCLE,)
    assert BLOCKED_MISSING_BLOCK in final_snap.foundup_projections["f_missing_dep"].blocking_reasons
    assert final_snap.foundup_projections["f_missing_direct"].blocking_reasons == (BLOCKED_MISSING_BLOCK,)
    for fid in ("f_cycle", "f_self", "f_missing_dep", "f_missing_direct"):
        assert final_snap.foundup_projections[fid].stage_cap_name == "Idea"
        assert res.final_sim_state.foundups[fid].stage == STAGE_TO_INT["Idea"]

    with pytest.raises(ValueError, match="duplicate"):
        run_lego_topology_simulation(
            {"blocks": [{"canonical_id": "dup_b"}, {"canonical_id": "dup_b"}]},
            enabled=True,
            ticks=1,
        )


def test_deterministic_trace_and_json_roundtrip_equivalence() -> None:
    fixture_a = _three_block_foundup_fixture()
    fixture_b = json.loads(json.dumps(fixture_a))
    fixture_b["blocks"] = list(reversed(fixture_b["blocks"]))
    fixture_b["relations"] = list(reversed(fixture_b["relations"]))
    tickets = {
        1: [
            {
                "ticket_id": "t_1",
                "block_id": "block_infra",
                "clears_stale_provenance": True,
                "satisfies_capabilities": ["blob_store"],
            },
            {
                "ticket_id": "t_2",
                "block_id": "block_api",
                "clears_unknown_consumer": True,
                "sets_block_ready": True,
                "satisfies_capabilities": ["serve_http"],
            },
        ]
    }

    run_1 = run_lego_topology_simulation(fixture_a, enabled=True, ticks=2, completed_tickets_by_tick=tickets)
    run_2 = run_lego_topology_simulation(fixture_b, enabled=True, ticks=2, completed_tickets_by_tick=tickets)
    assert run_1 is not None and run_2 is not None
    assert run_1.canonical_trace_json == run_2.canonical_trace_json
    assert run_1.simulation_trace_sha256 == run_2.simulation_trace_sha256
    assert run_1.simulation_trace_sha256 == hashlib.sha256(run_1.canonical_trace_json.encode("utf-8")).hexdigest()
    assert dict(run_1.final_sim_state.foundups.items()) == dict(run_2.final_sim_state.foundups.items())

    projection_json_shape = {
        "schema_version": "wre_lego_block_projection.v1",
        "blocks": [
            {
                "identity": {"canonical_id": "module::infra"},
                "static_tier": "STATICALLY_ANALYZED",
                "capability_statuses": [{"capability_id": "kv", "status": "VERIFIED_CAPABILITY"}],
                "triage": {"classification": "ACTIVE_STATIC_CALLERS"},
            }
        ],
        "catalog_relations": [{"relation_type": "FOUNDUP_TO_MODULE", "source_id": "foundup::demo", "target_id": "module::infra"}],
    }
    proj_run = run_lego_topology_simulation(projection_json_shape, enabled=True, ticks=0)
    assert proj_run is not None
    assert proj_run.snapshots[0].foundup_projections["foundup::demo"].stage_cap_name == "MVP"
    assert proj_run.snapshots[0].blocks["module::infra"].preserved_verified_capabilities == ("kv",)
