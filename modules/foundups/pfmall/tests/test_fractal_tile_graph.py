#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for Fractal Tile Graph schema, dual scoring, validator, projector, context, and exporter."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from modules.foundups.pfmall.fractal_tile_graph import (
    ROOT_TILE_ID,
    _extract_markdown_chapters,
    _read_pinned_text,
    build_repo_fractal_tile_graph,
    classify_completeness,
    classify_effort_to_green,
    classify_impact,
    compute_mall_rescue_score,
    compute_reusability,
    compute_wsp15_canonical,
    project_public_tile_graph,
    scan_wsp71_leaks,
    validate_tile_graph,
)
from modules.foundups.pfmall.member_catalog_export import (
    DEFAULT_FRACTAL_GRAPH_OUTPUT_PATH,
    DEFAULT_FRACTAL_SOURCE_FILES_OUTPUT_PATH,
    build_fractal_source_file_index,
    build_mall_catalog,
    export_architect_source_file_index,
    export_architect_tile_graph,
    export_fractal_tile_graph,
    export_mall_catalog,
    export_public_source_file_index,
    validate_source_file_index,
)
from modules.foundups.pfmall.tile_graph_context import (
    build_reddog_tile_briefing,
    build_tile_context,
    compute_view_reachability,
    get_breadcrumbs,
    get_cobuilding_context,
    get_rescue_queue,
    query_tools_benchmark_readback,
    search_tiles,
    walk_fractal_path,
)

REPO_ROOT = Path(__file__).resolve().parents[4]


@pytest.fixture(scope="module")
def repo_architect_graph() -> dict:
    """Build the full 012_architect graph once from tracked files under REPO_ROOT."""
    return build_repo_fractal_tile_graph(REPO_ROOT)


@pytest.fixture(scope="module")
def repo_public_graph(repo_architect_graph: dict) -> dict:
    """Project the public_mall graph strictly from repo_architect_graph."""
    return project_public_tile_graph(repo_architect_graph)


# ---------------------------------------------------------------------------
# Dual Scoring & Classification (Sections 9.3 & 9.4)
# ---------------------------------------------------------------------------

class TestDualScoring:
    """Verify canonical WSP 15 (4-20, P0-P4) and Mall Rescue Score (20-100)."""

    @pytest.mark.parametrize("axes,expected_mps,expected_band", [
        ((5, 5, 5, 5), 20, "P0"),
        ((4, 4, 4, 4), 16, "P0"),
        ((4, 3, 3, 3), 13, "P1"),
        ((3, 3, 3, 3), 12, "P2"),
        ((3, 3, 2, 2), 10, "P2"),
        ((2, 2, 2, 1), 7, "P3"),
        ((1, 1, 1, 1), 4, "P4"),
    ])
    def test_wsp15_canonical_bands(self, axes, expected_mps, expected_band):
        res = compute_wsp15_canonical(*axes)
        assert res["applicable"] is True
        assert res["mps"] == expected_mps
        assert res["priority_band"] == expected_band

    def test_wsp15_rejects_booleans_and_out_of_range(self):
        with pytest.raises(ValueError):
            compute_wsp15_canonical(True, 3, 3, 3)  # type: ignore[arg-type]
        with pytest.raises(ValueError):
            compute_wsp15_canonical(0, 3, 3, 3)
        with pytest.raises(ValueError):
            compute_wsp15_canonical(6, 3, 3, 3)

    def test_reusability_formula_boundaries(self):
        assert compute_reusability(0, 0) == 1
        assert compute_reusability(0, 4) == 1
        assert compute_reusability(0, 5) == 2
        assert compute_reusability(2, 5) == 4
        assert compute_reusability(4, 10) == 5  # capped at 5

    def test_simulator_and_endpoint_rescue_scores(self):
        # Listed Rev 1.1 axes (completeness=4, impact=5, reusability=5, effort_to_green=2) -> 91
        assert compute_mall_rescue_score(
            impact=5, reusability=5, completeness=4, effort_to_green=2
        ) == 91
        # Derived reusability = min(5, 1 + 2 + 1) = 4 -> 86
        derived_reusability = compute_reusability(2, 5)
        assert derived_reusability == 4
        assert compute_mall_rescue_score(
            impact=5, reusability=derived_reusability, completeness=4, effort_to_green=2
        ) == 86
        # Endpoints
        assert compute_mall_rescue_score(impact=1, reusability=1, completeness=1, effort_to_green=5) == 20
        assert compute_mall_rescue_score(impact=5, reusability=5, completeness=5, effort_to_green=1) == 100

    def test_classifier_thresholds(self):
        assert classify_completeness(
            has_code=True, has_tests=True, wsp49_doc_count=5, has_requirements=True, has_open_socket=False
        ) == 5
        assert classify_completeness(
            has_code=True, has_tests=True, wsp49_doc_count=5, has_requirements=True, has_open_socket=True
        ) == 4
        assert classify_completeness(has_code=True, has_tests=False, wsp49_doc_count=3) == 3
        assert classify_completeness(has_code=False, has_tests=False, wsp49_doc_count=0, has_manifest=True) == 2
        assert classify_completeness(has_code=False, has_tests=False, wsp49_doc_count=0) == 1

        assert classify_impact(inbound_ast_imports=5) == 5
        assert classify_impact(inbound_ast_imports=2) == 4
        assert classify_impact(inbound_ast_imports=1) == 3
        assert classify_impact(inbound_ast_imports=0, wsp49_doc_count=2) == 2
        assert classify_impact(inbound_ast_imports=0) == 1

        assert [classify_effort_to_green(c) for c in (5, 4, 3, 2, 1)] == [1, 2, 3, 4, 5]


# ---------------------------------------------------------------------------
# Validator & Containment Acyclicity
# ---------------------------------------------------------------------------

class TestTileGraphValidator:
    """Verify cycle detection, reference validation, enum validation, and leak rejection."""

    def test_repo_architect_and_public_graphs_validate_cleanly(self, repo_architect_graph, repo_public_graph):
        assert validate_tile_graph(repo_architect_graph) == []
        assert validate_tile_graph(repo_public_graph) == []

    def test_detects_parent_child_cycle(self, repo_public_graph):
        bad = copy.deepcopy(repo_public_graph)
        # Create cycle: tile:sys:core_systems -> tile:sys:simulator -> tile:sys:core_systems
        bad["tiles"]["tile:sys:simulator"]["children_tile_ids"].append("tile:sys:core_systems")
        bad["tiles"]["tile:sys:core_systems"]["parent_tile_id"] = "tile:sys:simulator"
        errs = validate_tile_graph(bad, check_schema=False)
        assert any("cycle" in e.lower() for e in errs)

    def test_detects_unresolved_child_and_dag_edge(self, repo_public_graph):
        bad = copy.deepcopy(repo_public_graph)
        bad["tiles"]["tile:space:hpc"]["children_tile_ids"].append("tile:space:missing_child")
        bad["tiles"]["tile:space:hpc"]["dag_edges"]["cross_links"].append("tile:engine:nonexistent")
        errs = validate_tile_graph(bad, check_schema=False)
        assert any("unresolved child reference" in e for e in errs)
        assert any("unresolved dag_edges.cross_links" in e for e in errs)

    def test_detects_invalid_enum_and_schema_version(self, repo_public_graph):
        bad = copy.deepcopy(repo_public_graph)
        bad["schema_version"] = "fractal_tile_graph.v99"
        bad["tiles"]["tile:space:hpc"]["lifecycle"]["state"] = "PURPLE"
        errs = validate_tile_graph(bad, check_schema=False)
        assert any("schema_version" in e for e in errs)
        assert any("lifecycle.state" in e for e in errs)


# ---------------------------------------------------------------------------
# Repo Builder Fidelity & Vertical Verification
# ---------------------------------------------------------------------------

class TestRepoGraphBuilder:
    """Verify build_repo_fractal_tile_graph builds all verticals from tracked files alone."""

    def test_core_systems_and_simulator_fixture(self, repo_architect_graph):
        tiles = repo_architect_graph["tiles"]
        sim = tiles["tile:sys:simulator"]
        assert sim["lifecycle"]["state"] == "AMBER"
        assert sim["visibility_scope"] == "public"
        assert sim["wsp15_canonical"]["mps"] == 20
        assert sim["wsp15_canonical"]["priority_band"] == "P0"
        assert sim["rescue_axes"]["reusability"] == 4
        assert sim["mall_rescue_score"] == 86
        assert sim["lifecycle"]["inbound_ast_imports"] >= 5
        assert set(["agent_market", "pfmall"]).issubset(set(sim["dag_edges"]["used_by_foundups"]))

        for sub in (
            "tile:sub:simulator.cabr_flow_router",
            "tile:sub:simulator.tick_and_mesa_engine",
            "tile:sub:simulator.economics_suite",
            "tile:sub:simulator.scenarios_and_params",
            "tile:sub:simulator.cube_render_and_sse",
            "tile:sub:simulator.mockups_and_archive",
            "tile:socket:simulator.export_adapter",
        ):
            assert sub in tiles
        assert tiles["tile:socket:simulator.export_adapter"]["lifecycle"]["state"] == "BLUE"
        assert tiles["tile:socket:simulator.export_adapter"]["tile_kind"] == "socket_slot"
        assert "tile:mod:foundups.pfmall" in tiles
        assert "tile:sys:holo_index" in tiles
        assert "tile:sys:extensions_reddog" in tiles

    def test_pubs_jhr_papers_patents_and_mirror_exclusion(self, repo_architect_graph):
        tiles = repo_architect_graph["tiles"]
        assert not any("southern_shakespeare_company" in tid for tid in tiles)
        assert tiles["tile:opus:jhr.001"]["lifecycle"]["state"] == "GREEN"
        assert tiles["tile:opus:jhr.002"]["lifecycle"]["state"] == "GREEN"
        jhr3 = tiles["tile:opus:jhr.003"]
        assert jhr3["lifecycle"]["state"] == "AMBER"
        assert jhr3["metadata"]["observed_on"] == "2026-11-16"
        assert jhr3["metadata"]["archive_mismatch"] is True
        assert jhr3["metadata"]["per_destination_evidence"]["website"]["status"] == "UNVERIFIED"
        assert jhr3["metadata"]["per_destination_evidence"]["linkedin"]["status"] == "VERIFIED_LIVE"

        jhr4 = tiles["tile:opus:jhr.004"]
        assert jhr4["visibility_scope"] == "principal_only"
        assert jhr4["metadata"]["metadata_only"] is True
        assert tiles["tile:opus:jhr.005"]["lifecycle"]["state"] == "BLUE"
        assert tiles["tile:opus:jhr.005"]["visibility_scope"] == "principal_only"

        sched = tiles["tile:opus:jhr.synthetic_scheduled_fixture"]
        assert sched["visibility_scope"] == "principal_only"
        assert sched["metadata"]["editorial_stage"] == "SCHEDULED_VERIFIED"
        assert sched["metadata"]["scheduled_release_at"] == "2026-12-01T09:00:00+09:00"
        assert sched["metadata"]["timezone"] == "Asia/Tokyo"

        # Papers including O2ing 2026-11-17
        assert "tile:opus:papers.empirical_evidence.o2ing_voice_session_case_2026-11-17.md" in tiles
        assert "tile:opus:papers.resp_quantum_self_reference.md" in tiles
        assert "tile:opus:papers.resp_ja_quantum_self_reference.md" in tiles
        assert "tile:opus:papers.peer_preservation_shared_latent_coupling.md" in tiles
        assert "tile:opus:papers.eiah_drive_doc_2023_03" in tiles

        # Patent series 00..05 + companion token & deck, zero 06_*
        assert "tile:opus:patent.00_patent_portfolio_prospectus" in tiles
        assert "tile:opus:patent.04_resp_patent_updated" in tiles
        assert "tile:opus:patent.04_resp_patent_japanese" in tiles
        assert "tile:opus:patent.05_auto_meeting_orchestrator_patent" in tiles
        assert "tile:opus:patent.undaodu_token_integration" in tiles
        assert "tile:opus:patent.patent_portfolio_presentation_deck" in tiles
        assert not any("patent.06_" in tid for tid in tiles)
        assert tiles["tile:opus:patent_series"]["evidence_status"] == "claim_requires_independent_evidence"

    def test_hpc_investor_akiya_wikitube_mockups_and_red_modules(self, repo_architect_graph):
        tiles = repo_architect_graph["tiles"]
        hpc = tiles["tile:space:hpc"]
        assert hpc["owner_namespace"] == "hpc_coalition"
        assert "tile:engine:autopost" in hpc["dag_edges"]["cross_links"]
        schumer = tiles["tile:space:hpc.schumerout"]
        hpc_proj = json.loads((REPO_ROOT / "modules/foundups/hpc/mall_projection.json").read_text(encoding="utf-8"))
        expected_vids = {v["video_id"] for v in hpc_proj.get("videos", []) if isinstance(v, dict) and v.get("video_id")}
        assert len(schumer["children_tile_ids"]) >= 8
        assert len(schumer["children_tile_ids"]) == len(expected_vids)
        for sub in ("vote", "oversight", "press", "voice"):
            assert f"tile:space:hpc.{sub}" in tiles

        autopost = tiles["tile:engine:autopost"]
        assert autopost["tile_kind"] == "licensable_engine"
        assert autopost["parent_tile_id"] == "tile:investor:root"
        assert autopost["evidence_status"] == "claim_requires_independent_evidence"
        assert "tile:space:hpc" in autopost["dag_edges"]["used_by_foundups"]
        assert "tile:investor:hornet_hunter" in tiles

        # Akiya hierarchy: Japan -> Fukui -> municipalities -> 8 properties
        akiya_props = [
            t for tid, t in tiles.items()
            if tid.startswith("tile:market:japan_akiya.fukui.")
            and t["domain_override_manifest"]["override_type"] == "akiya_property"
        ]
        assert len(akiya_props) == 8
        for prop in akiya_props:
            assert prop["evidence_status"] == "claim_requires_independent_evidence"
            payload = prop["domain_override_manifest"]["payload"]
            assert payload["land_tax_1_6_shield_status"] == "unknown"
            assert payload["inheritance_reg_2027_status"] == "unknown"

        # WikiTube playlists
        for stid in ("tile:stream:wikitube_featured", "tile:stream:wikitube_hpc_schumer"):
            stream_payload = tiles[stid]["domain_override_manifest"]["payload"]
            assert stream_payload["autoplay_continuous"] is True
            assert len(stream_payload["ordered_segments"]) >= 8

        # Mockups & RED module census
        assert "tile:mockup:public_index_buildCanvas" in tiles
        assert "tile:mockup:public_ecosystem_growth" in tiles
        red_tiles = [t for t in tiles.values() if t["lifecycle"]["state"] == "RED"]
        assert len(red_tiles) >= 1
        assert all(t["visibility_scope"] == "principal_only" for t in red_tiles)


# ---------------------------------------------------------------------------
# Dual-Scope Projection, Search Aliases & Private Edit ETag Isolation
# ---------------------------------------------------------------------------

class TestDualScopeProjection:
    """Verify public projection strips all private/RED artifacts and preserves ETag isolation."""

    def test_public_projection_strips_private_red_and_leaks(self, repo_public_graph):
        pub_tiles = repo_public_graph["tiles"]
        for tid in (
            "tile:opus:jhr.004",
            "tile:opus:jhr.005",
            "tile:opus:jhr.synthetic_scheduled_fixture",
            "tile:opus:papers.resp_cross_linguistic_private",
            "tile:opus:roc.roi_to_roc_baseline",
            "tile:socket:simulator.export_adapter",
        ):
            assert tid not in pub_tiles
            assert tid not in repo_public_graph["tiles"].get("tile:opus:jhr", {}).get("children_tile_ids", [])

        assert all(t["visibility_scope"] == "public" for t in pub_tiles.values())
        assert all(t["lifecycle"]["state"] != "RED" for t in pub_tiles.values())
        assert scan_wsp71_leaks(repo_public_graph) == []

    def test_restricted_socket_absent_from_public_and_approved_public_socket_works(
        self, repo_architect_graph, repo_public_graph
    ):
        pub_tiles = repo_public_graph["tiles"]
        pub_serialized = json.dumps(repo_public_graph, ensure_ascii=False)

        # 1. Restricted principal_only socket data is completely absent from public output
        for forbidden_token in (
            "tile:socket:simulator.export_adapter",
            "open_socket:export_adapter",
            "pfmall_state_provider.py",
            "SimulatorStateProvider",
            "tile:opus:jhr.005",
            "tile:opus:jhr.synthetic_scheduled_fixture",
        ):
            assert forbidden_token not in pub_serialized

        sim_pub = pub_tiles["tile:sys:simulator"]
        sim_pub_socket_ids = [s["socket_id"] for s in sim_pub["metadata"]["open_sockets"]]
        assert "tile:socket:simulator.export_adapter" not in sim_pub_socket_ids
        assert all(sid.startswith("seam:modules/foundups/simulator:") for sid in sim_pub_socket_ids)
        assert len(sim_pub_socket_ids) >= 1
        assert "open_socket:export_adapter" not in sim_pub["lifecycle"]["drift_flags"]
        assert get_cobuilding_context(repo_public_graph, "tile:sys:simulator")["open_sockets"] == []

        # Architect scope retains restricted socket intact
        sim_arch = repo_architect_graph["tiles"]["tile:sys:simulator"]
        assert any(
            s["socket_id"] == "tile:socket:simulator.export_adapter"
            for s in sim_arch["metadata"]["open_sockets"]
        )
        assert "tile:socket:simulator.export_adapter" in repo_architect_graph["tiles"]

        # Validator actively rejects any restricted socket leak injected into public_mall
        tampered_pub = copy.deepcopy(repo_public_graph)
        tampered_pub["tiles"]["tile:sys:simulator"]["metadata"]["open_sockets"].insert(
            0,
            {
                "socket_id": "tile:socket:simulator.export_adapter",
                "status": "BLUE_OPEN_SOCKET",
                "source": "modules/foundups/simulator/adapters/pfmall_state_provider.py",
                "target": "modules/foundups/pfmall/member_catalog_export.py",
            },
        )
        tampered_errors = validate_tile_graph(tampered_pub)
        assert any("restricted or invisible socket" in err for err in tampered_errors)

        # 2. Approved public sockets remain present, valid, and navigable in public_mall
        for approved_pub_socket in (
            "tile:socket:benchmark.audit_packet_research_adapter",
            "tile:socket:benchmark.hermes_cli_runner",
            "tile:benchcfg:lm_studio_nemotron_30b_blocked",
            "tile:benchcfg:openrouter_kimi_k3_blocked",
        ):
            assert approved_pub_socket in pub_tiles
            assert pub_tiles[approved_pub_socket]["tile_kind"] == "socket_slot"
            assert pub_tiles[approved_pub_socket]["visibility_scope"] == "public"
            assert pub_tiles[approved_pub_socket]["lifecycle"]["state"] == "BLUE"

        walk_g01 = walk_fractal_path(
            repo_public_graph,
            [
                ROOT_TILE_ID,
                "tile:tools:root",
                "tile:tools:benchmark",
                "tile:harness:wre_auto_researcher",
                "tile:socket:benchmark.audit_packet_research_adapter",
            ],
        )
        assert walk_g01["ok"] is True

        walk_hermes = walk_fractal_path(
            repo_public_graph,
            [ROOT_TILE_ID, "tile:tools:root", "tile:socket:benchmark.hermes_cli_runner"],
        )
        assert walk_hermes["ok"] is True

        wre_cobuild_pub = get_cobuilding_context(repo_public_graph, "tile:harness:wre_auto_researcher")
        assert wre_cobuild_pub is not None
        assert [s["tile_id"] for s in wre_cobuild_pub["open_sockets"]] == [
            "tile:socket:benchmark.audit_packet_research_adapter"
        ]

    def test_nested_private_metadata_in_objects_and_arrays_stripped_and_validated(
        self, repo_architect_graph, repo_public_graph
    ):
        private_tid = "tile:sys:ext_claude_wre"
        assert private_tid in repo_architect_graph["tiles"]
        assert private_tid not in repo_public_graph["tiles"]

        # 1. Exact nested object sentinel probe (pure private object vanishes, ETag unchanged)
        sentinel_arch = copy.deepcopy(repo_architect_graph)
        sentinel_arch["tiles"][ROOT_TILE_ID].setdefault("metadata", {})["nested_extra"] = {
            "private_note": "PC_COMPARISON_PRIVATE_SENTINEL",
            "restricted_target": private_tid,
        }
        sentinel_snapshot = copy.deepcopy(sentinel_arch["tiles"][ROOT_TILE_ID]["metadata"]["nested_extra"])
        sentinel_pub = project_public_tile_graph(sentinel_arch)
        assert "PC_COMPARISON_PRIVATE_SENTINEL" not in json.dumps(sentinel_pub, ensure_ascii=False)
        assert private_tid not in json.dumps(sentinel_pub, ensure_ascii=False)
        assert "nested_extra" not in sentinel_pub["tiles"][ROOT_TILE_ID]["metadata"]
        assert validate_tile_graph(sentinel_pub) == []
        assert sentinel_pub["public_graph_etag"] == repo_public_graph["public_graph_etag"]
        assert sentinel_arch["tiles"][ROOT_TILE_ID]["metadata"]["nested_extra"] == sentinel_snapshot

        # 2. Mixed nested objects & arrays strip private entries while preserving permitted neighbors
        mixed_arch = copy.deepcopy(repo_architect_graph)
        target_meta = mixed_arch["tiles"]["tile:sys:core_systems"].setdefault("metadata", {})
        target_meta["mixed_probe"] = {
            "public_label": "safe_neighbor",
            "private_note": "SECRET_OBJ_NOTE",
            "restricted_ref": private_tid,
            "nested_deeper": {
                "safe_count": 7,
                "private_provenance": {"internal": "HIDDEN_PROVENANCE"},
                "private_meta_flag": True,
            },
        }
        target_meta["array_probe"] = [
            {
                "name": "keep_me",
                "private_note": "ARRAY_OBJ_SECRET",
                "tags": ["safe_tag", private_tid],
            },
            {
                "visibility_scope": "principal_only",
                "note": "DROP_ENTIRE_PRINCIPAL_ITEM",
            },
            {
                "private_note": "PURE_PRIVATE_DICT",
            },
            ["nested_safe", private_tid],
            "permitted_neighbor",
            private_tid,
        ]
        target_meta["all_private_array"] = [
            {"private_note": "ONLY_PRIVATE"},
            private_tid,
        ]

        mixed_pub = project_public_tile_graph(mixed_arch)
        assert validate_tile_graph(mixed_pub) == []
        pub_serialized = json.dumps(mixed_pub, ensure_ascii=False)
        for forbidden in (
            "SECRET_OBJ_NOTE",
            "HIDDEN_PROVENANCE",
            "ARRAY_OBJ_SECRET",
            "DROP_ENTIRE_PRINCIPAL_ITEM",
            "PURE_PRIVATE_DICT",
            "ONLY_PRIVATE",
            private_tid,
        ):
            assert forbidden not in pub_serialized

        pub_meta = mixed_pub["tiles"]["tile:sys:core_systems"]["metadata"]
        assert pub_meta["mixed_probe"] == {
            "public_label": "safe_neighbor",
            "nested_deeper": {"safe_count": 7},
        }
        assert pub_meta["array_probe"] == [
            {"name": "keep_me", "tags": ["safe_tag"]},
            ["nested_safe"],
            "permitted_neighbor",
        ]
        assert "all_private_array" not in pub_meta

        # Architect source preserves every nested private field unmodified
        arch_meta = mixed_arch["tiles"]["tile:sys:core_systems"]["metadata"]
        assert arch_meta["mixed_probe"]["private_note"] == "SECRET_OBJ_NOTE"
        assert arch_meta["array_probe"][1]["visibility_scope"] == "principal_only"

        # 3. Validator rejects unsanitized public_mall copies across objects and arrays
        def _inject_and_validate(mutator):
            tampered = copy.deepcopy(repo_public_graph)
            mutator(tampered["tiles"]["tile:sys:core_systems"])
            return validate_tile_graph(tampered, check_schema=False)

        errs_dict_note = _inject_and_validate(
            lambda t: t["metadata"].__setitem__("nested_extra", {"private_note": "LEAKED_NOTE", "safe": "ok"})
        )
        assert any("private metadata key 'private_note'" in e for e in errs_dict_note)

        errs_dict_tid = _inject_and_validate(
            lambda t: t["metadata"].__setitem__("nested_extra", {"restricted_target": private_tid})
        )
        assert any(private_tid in e for e in errs_dict_tid)

        errs_arr_obj = _inject_and_validate(
            lambda t: t["metadata"].__setitem__("arr_obj", [{"ok": 1, "private_provenance": {"x": 1}}])
        )
        assert any("private metadata key 'private_provenance'" in e for e in errs_arr_obj)

        errs_arr_vis = _inject_and_validate(
            lambda t: t["metadata"].__setitem__("arr_vis", [{"visibility_scope": "principal_only", "id": "x"}])
        )
        assert any("principal_only nested object" in e for e in errs_arr_vis)

        errs_arr_nested = _inject_and_validate(
            lambda t: t["metadata"].__setitem__("arr_nested", [["ok", f"ref:{private_tid}"]])
        )
        assert any(private_tid in e for e in errs_arr_nested)

        errs_arr_hist = _inject_and_validate(
            lambda t: t["metadata"].__setitem__("arr_hist", [{"receipt_history": ["superseded"]}])
        )
        assert any("private metadata key 'receipt_history'" in e for e in errs_arr_hist)

    def test_required_search_aliases_resolve_without_private_hits(self, repo_public_graph):
        aliases = repo_public_graph["search_index"]["aliases"]
        pub_ids = set(repo_public_graph["tiles"].keys())
        required_aliases = (
            "all papers",
            "UnDaoDu",
            "Return on Compute",
            "Japan Hyperscaler Report",
            "JHR",
            "HPC",
            "AutoPost",
            "Akiya",
            "Simulator",
        )
        for key in required_aliases:
            assert key in aliases and len(aliases[key]) >= 1
            assert set(aliases[key]).issubset(pub_ids)

    def test_private_mutations_leave_public_etag_byte_identical(self, repo_architect_graph, repo_public_graph):
        mutated = copy.deepcopy(repo_architect_graph)
        mutated["tiles"]["tile:opus:jhr.004"]["display_name"] = "Private Editor Title Override"
        mutated["tiles"]["tile:opus:jhr.synthetic_scheduled_fixture"]["display_name"] = "Private Schedule Check"
        mutated["tiles"]["tile:sys:simulator"].setdefault("private_notes", []).append({"note": "012 internal note"})

        pub_after = project_public_tile_graph(mutated)
        assert pub_after["public_graph_etag"] == repo_public_graph["public_graph_etag"]
        assert pub_after["counts"] == repo_public_graph["counts"]
        assert pub_after["links"] == repo_public_graph["links"]
        assert pub_after["search_index"] == repo_public_graph["search_index"]


# ---------------------------------------------------------------------------
# Context Helpers & Public Exporter
# ---------------------------------------------------------------------------

class TestContextAndExporter:
    """Verify tile_graph_context traversal, search, rescue queue, and exporter."""

    def test_context_navigation_and_sorting(self, repo_architect_graph, repo_public_graph):
        pub_jhr = build_tile_context(repo_public_graph, "tile:opus:jhr", sort="published_date_desc")
        assert pub_jhr is not None
        assert [c["tile_id"] for c in pub_jhr["children"]] == [
            "tile:opus:jhr.003",
            "tile:opus:jhr.002",
            "tile:opus:jhr.001",
        ]
        assert [b["tile_id"] for b in get_breadcrumbs(repo_public_graph, "tile:opus:jhr")] == [
            ROOT_TILE_ID,
            "tile:pubs:root",
            "tile:opus:jhr",
        ]

        arch_sched = build_tile_context(
            repo_architect_graph,
            "tile:opus:jhr",
            sort="scheduled_next_asc",
            filter_state="scheduled",
        )
        assert arch_sched is not None
        assert [c["tile_id"] for c in arch_sched["children"]] == ["tile:opus:jhr.synthetic_scheduled_fixture"]

        assert build_tile_context(repo_public_graph, "tile:opus:jhr.004") is None

    def test_search_rescue_cobuilding_and_reddog_briefing(self, repo_architect_graph, repo_public_graph):
        hits = search_tiles(repo_public_graph, "Japan Hyperscaler Report")
        assert any(h["tile_id"] == "tile:opus:jhr" for h in hits)
        assert not any(h["visibility_scope"] == "principal_only" for h in hits)

        queue = get_rescue_queue(repo_architect_graph, limit=10)
        assert len(queue) == 10
        assert any(item["tile_id"] == "tile:sys:simulator" for item in queue)

        cobuild = get_cobuilding_context(repo_architect_graph, "tile:sys:simulator")
        assert cobuild is not None
        assert any(s["tile_id"] == "tile:socket:simulator.export_adapter" for s in cobuild["open_sockets"])

        briefing = build_reddog_tile_briefing(repo_public_graph, "tile:sys:simulator")
        assert briefing is not None
        assert "private_notes" not in briefing

    def test_exporter_writes_valid_public_graph_and_preserves_catalog(self, tmp_path):
        out_graph = tmp_path / "fractal_tile_graph.public.json"
        written = export_fractal_tile_graph(output_path=out_graph, repo_root=REPO_ROOT)
        data = json.loads(written.read_text(encoding="utf-8"))
        assert validate_tile_graph(data) == []
        assert data["scope"] == "public_mall"

        # Existing catalog export remains intact
        out_cat = tmp_path / "mall-catalog.json"
        export_mall_catalog(output_path=out_cat)
        cat_data = json.loads(out_cat.read_text(encoding="utf-8"))
        assert cat_data == build_mall_catalog()

    def test_committed_public_fractal_tile_graph_artifact_valid(self):
        assert not (REPO_ROOT / "public/member/fractal_tile_graph.public.json").exists()
        assert not (REPO_ROOT / "public/member/fractal_source_files.public.json").exists()
        assert DEFAULT_FRACTAL_GRAPH_OUTPUT_PATH.parent == REPO_ROOT / "modules/foundups/pfmall/projections"
        assert DEFAULT_FRACTAL_GRAPH_OUTPUT_PATH.is_file()
        data = json.loads(DEFAULT_FRACTAL_GRAPH_OUTPUT_PATH.read_text(encoding="utf-8"))
        assert validate_tile_graph(data) == []
        assert data["scope"] == "public_mall"

        with pytest.raises(ValueError, match="inside public web root"):
            export_fractal_tile_graph(
                output_path=REPO_ROOT / "public/member/forbidden_public_graph.json",
                repo_root=REPO_ROOT,
            )


class TestSprint2RegistryAndBenchmarkProjection:
    """Verify Sprint 2 Tools -> Benchmark projection, typed relationships & walkthroughs."""

    def test_tools_benchmark_forward_and_back_walkthrough(self, repo_public_graph):
        run_tile_id = "tile:benchrun:antigravity_0102_blind__scaffold_b_wsp97_holo_pkt_01_module_discovery"
        ev_tile_id = "tile:benchevidence:pkt_01_module_discovery"
        waypoints = [
            ROOT_TILE_ID,
            "tile:tools:root",
            "tile:tools:benchmark",
            "tile:harness:model_combination_benchmark",
            "tile:benchcfg:antigravity_0102_blind_scaffold_b",
            run_tile_id,
            ev_tile_id,
        ]
        walk = walk_fractal_path(repo_public_graph, waypoints)
        assert walk["ok"] is True
        assert walk["forward_trail"] == waypoints
        assert walk["back_trail"] == list(reversed(waypoints))
        assert walk["terminal_tile"] == ROOT_TILE_ID

        pub_tiles = repo_public_graph["tiles"]
        run_ev = pub_tiles[run_tile_id]["metadata"]["benchmark_evidence"]
        assert run_ev["git_revision"] == "7432d31e5a68544d2bbab6715f02f64b0b5b6f85"
        assert run_ev["verdict"] == "reject"
        assert run_ev["effective_verdict"] == "REJECT"
        assert run_ev["schema_valid"] is False
        assert run_ev["schema_status"] == "SCHEMA_INVALID"
        assert run_ev["parse_status"] == "PARSE_OK"
        assert run_ev["decision_lifecycle"] == "PROVISIONAL"
        assert run_ev["cost_usd"] == 0.0
        assert run_ev["harness_receipt_id"].startswith("model_combination_benchmark_run:")
        assert run_ev["candidate_v2_1_receipt_id"] == (
            "model_combination_benchmark_run:f3066fda0f8546c3ceb30b8099e231662394208ca3d76e877feb4656af00d0bb"
        )

        inc_run_id = "tile:benchrun:incumbent_deterministic_ast_holo_pkt_02_dependency_tracing"
        inc_ev = pub_tiles[inc_run_id]["metadata"]["benchmark_evidence"]
        inc_rec_ev = pub_tiles["tile:receipt:v2_1_pkt_02"]["metadata"]["benchmark_evidence"]
        assert inc_ev["verdict"] == "reject"
        assert inc_ev["factual_coverage"] == 0.5
        assert inc_ev["schema_valid"] is True
        assert inc_ev["candidate_v2_1_receipt_id"] == inc_rec_ev["harness_receipt_id"]

        ev_meta = pub_tiles[ev_tile_id]["metadata"]["benchmark_evidence"]
        assert ev_meta["git_revision"] == "7432d31e5a68544d2bbab6715f02f64b0b5b6f85"
        assert ev_meta["target_repo_path"] == "modules/foundups/agent_market"
        assert ev_meta["sealed_packet_sha256"] == (
            "5a065f453048d2771f227a6d573c5fa143b8a10b4081a340ba7ed363d6fae72e"
        )

    def test_tools_benchmark_answers_all_five_questions(self, repo_public_graph, repo_architect_graph):
        pub_rb = query_tools_benchmark_readback(repo_public_graph)
        arch_rb = query_tools_benchmark_readback(repo_architect_graph)

        for rb in (pub_rb, arch_rb):
            # Q1: All 7 PC tools present under canonical Tools parent, reused inside Benchmark
            q1 = rb["q1_pc_benchmark_tools"]
            assert len(q1) == 7
            assert all(t["parent_tile_id"] == "tile:tools:root" for t in q1)
            assert all(
                {"cross_links", "runs_through"}.issubset(set(t["appears_in_benchmark_via"]))
                for t in q1
            )

            # Q2: Evaluatable targets per harness
            q2 = {row["harness_tile_id"]: row for row in rb["q2_evaluatable_targets"]}
            assert len(q2) == 3
            mcb = q2["tile:harness:model_combination_benchmark"]
            assert "tile:mod:foundups.agent_market" in mcb["evaluated_modules"]
            assert "tile:sys:simulator" in mcb["evaluated_modules"]
            assert "tile:mod:ai_intelligence.ai_gateway" in mcb["evaluated_modules"]
            assert "tile:mod:infrastructure.wre_core" in mcb["evaluated_modules"]

            # Q3: All 20 executed runs incl. single-variable pkt_04 retest
            q3 = rb["q3_executed_runs"]
            assert len(q3) == 20
            gemma_baseline = next(
                r for r in q3
                if "gemma2_2b__scaffold_b_baseline" in r["tile_id"]
            )
            gemma_retest = next(
                r for r in q3
                if "gemma2_2b__scaffold_b_retest_json_schema" in r["tile_id"]
            )
            assert gemma_baseline["schema_valid"] is False
            assert gemma_retest["schema_valid"] is True
            assert gemma_baseline["verdict"] == "reject"
            assert gemma_retest["verdict"] == "reject"
            assert gemma_retest["cost_usd"] == 0.0

            # Q4: Unowned / blocked capabilities surfaced truthfully
            q4_ids = {row["tile_id"] for row in rb["q4_missing_or_blocked_capabilities"]}
            assert {
                "tile:socket:benchmark.audit_packet_research_adapter",
                "tile:socket:benchmark.hermes_cli_runner",
                "tile:benchcfg:lm_studio_nemotron_30b_blocked",
                "tile:benchcfg:openrouter_kimi_k3_blocked",
            }.issubset(q4_ids)

            # Q5: Full result -> input / evidence / receipt traceability
            q5 = rb["q5_result_to_evidence_traceability"]
            assert q5["runs_checked"] == 20
            assert q5["all_runs_traceable"] is True

    def test_typed_relationship_edges_and_single_tool_identity(self, repo_public_graph):
        edge_types = {link["edge_type"] for link in repo_public_graph["links"]["dag"]}
        assert {
            "calls",
            "reads_from",
            "evaluates",
            "runs_through",
            "produces_receipt",
            "verified_by",
        }.issubset(edge_types)

        aliases = repo_public_graph["search_index"]["aliases"]
        assert "tile:tools:root" in aliases["Tools"]
        assert "tile:tools:benchmark" in aliases["Benchmark"]

        # Canonical single identity for every PC tool tile
        tool_tiles = [
            tid for tid in repo_public_graph["tiles"]
            if tid.startswith("tile:tool:")
        ]
        assert len(tool_tiles) == 6
        for ttid in tool_tiles:
            assert repo_public_graph["tiles"][ttid]["parent_tile_id"] == "tile:tools:root"

    def test_registry_verification_separation_and_duplicate_privacy(
        self, repo_architect_graph, repo_public_graph
    ):
        for tid in ("tile:mod:foundups.agent_market", "tile:sys:simulator"):
            rv = repo_public_graph["tiles"][tid]["metadata"]["registry_verification"]
            assert rv["revision"] == "7432d31e5a68544d2bbab6715f02f64b0b5b6f85"
            assert "functionality_evidence" in rv
            assert "integration_evidence" in rv
            assert "production_status" in rv

        ext_ap = repo_public_graph["tiles"]["tile:engine:autopost"]["metadata"]["external_repo_verification"]
        assert ext_ap["repository"] == "FOUNDUPS/AutoPost"
        assert ext_ap["head_sha"] == "c7fb644c1b8897f2af29f26d7e3dc3838a67ab18"
        assert ext_ap["tracked_files"] == 146

        # Duplicate clusters remain strictly principal_only in 012_architect
        arch_dups = [tid for tid in repo_architect_graph["tiles"] if tid.startswith("tile:dup:")]
        assert len(arch_dups) == 16
        assert all(
            repo_architect_graph["tiles"][tid]["visibility_scope"] == "principal_only"
            for tid in arch_dups
        )
        assert not any(
            tid.startswith("tile:dup:") or tid == "tile:domain:duplicate_audit"
            for tid in repo_public_graph["tiles"]
        )


class TestSprint21WholeRepoNavigationAndVisibility:
    """Verify Sprint 2.1 whole-repository reachability, source provenance, and orthogonal visibility."""

    def test_whole_repo_domains_public_and_source_inspection_populated(
        self, repo_architect_graph, repo_public_graph
    ):
        assert repo_public_graph["tiles"]["tile:modules:root"]["visibility_scope"] == "public"
        assert repo_public_graph["tiles"]["tile:domain:foundups"]["visibility_scope"] == "public"
        assert "tile:mod:foundups.agent_market" in repo_public_graph["tiles"]

        for graph in (repo_architect_graph, repo_public_graph):
            for tid, tile in graph["tiles"].items():
                si = (tile.get("metadata") or {}).get("source_inspection") or {}
                assert si.get("availability_status"), f"{tid} missing source_inspection.availability_status"
                assert si.get("repository_slug"), f"{tid} missing source_inspection.repository_slug"

        am = repo_public_graph["tiles"]["tile:mod:foundups.agent_market"]
        rv = am["metadata"]["registry_verification"]
        assert rv["functionality_state"] == "TEST_FILES_PRESENT_UNEXECUTED"
        assert rv["integration_state"] == "WIRED_STATIC_CALLERS"
        assert rv["inbound_callers_window"]["total_count"] == 13
        assert am["metadata"]["source_inspection"]["source_revision"] == "7432d31e5a68544d2bbab6715f02f64b0b5b6f85"
        assert am["metadata"]["source_inspection"]["availability_status"] == "VERIFIED_AT_CENSUS_BASELINE_REVISION"

    def test_visibility_orthogonal_to_state_and_architect_export_guard(
        self, repo_architect_graph, repo_public_graph, tmp_path
    ):
        # Public-safe rejected run remains visible in public_mall, with provisional receipt_history stripped
        inc_run_id = "tile:benchrun:incumbent_deterministic_ast_holo_pkt_02_dependency_tracing"
        assert inc_run_id in repo_public_graph["tiles"]
        pub_be = repo_public_graph["tiles"][inc_run_id]["metadata"]["benchmark_evidence"]
        arch_be = repo_architect_graph["tiles"][inc_run_id]["metadata"]["benchmark_evidence"]
        assert pub_be["effective_verdict"] == "REJECT"
        assert pub_be["decision_lifecycle"] == "PROVISIONAL"
        assert "receipt_history" not in pub_be
        assert "receipt_history" in arch_be

        # Architect-private working component (GREEN + principal_only) never leaks into public_mall
        priv_working_id = "tile:sys:ext_claude_wre"
        assert repo_architect_graph["tiles"][priv_working_id]["lifecycle"]["state"] == "GREEN"
        assert repo_architect_graph["tiles"][priv_working_id]["visibility_scope"] == "principal_only"
        assert priv_working_id not in repo_public_graph["tiles"]

        # Exact navigable reachability (R/T = 1.0) on both projections
        pub_reach = compute_view_reachability(repo_public_graph, sorted(repo_public_graph["tiles"].keys()))
        arch_reach = compute_view_reachability(repo_architect_graph, sorted(repo_architect_graph["tiles"].keys()))
        assert pub_reach["reconciled_exact"] is True
        assert arch_reach["reconciled_exact"] is True

        # Architect exporter works outside public/ and refuses paths inside public/
        arch_out = tmp_path / "fractal_tile_graph.architect.json"
        written = export_architect_tile_graph(output_path=arch_out, repo_root=REPO_ROOT)
        arch_loaded = json.loads(written.read_text(encoding="utf-8"))
        assert arch_loaded["scope"] == "012_architect"
        assert validate_tile_graph(arch_loaded) == []

        with pytest.raises(ValueError, match="Refusing to write 012_architect graph inside public web root"):
            export_architect_tile_graph(
                output_path=REPO_ROOT / "public/member/forbidden_architect.json",
                repo_root=REPO_ROOT,
            )


class TestFractalSourceFileIndexAndGatedEnvelope:
    """Verify census-backed source file index, scope isolation, and gated envelope contract."""

    def test_committed_public_source_file_index_valid_and_leak_free(self, repo_public_graph):
        assert not (REPO_ROOT / "public/member/fractal_source_files.public.json").exists()
        assert DEFAULT_FRACTAL_SOURCE_FILES_OUTPUT_PATH.parent == REPO_ROOT / "modules/foundups/pfmall/projections"
        assert DEFAULT_FRACTAL_SOURCE_FILES_OUTPUT_PATH.is_file()
        pub_graph = json.loads(DEFAULT_FRACTAL_GRAPH_OUTPUT_PATH.read_text(encoding="utf-8"))
        idx = json.loads(DEFAULT_FRACTAL_SOURCE_FILES_OUTPUT_PATH.read_text(encoding="utf-8"))

        assert validate_source_file_index(idx, pub_graph) == []
        with pytest.raises(ValueError, match="inside public web root"):
            export_public_source_file_index(
                repo_public_graph,
                {"repository_slug": "FOUNDUPS/Foundups-Agent", "source_revision": "7432d31e5a68544d2bbab6715f02f64b0b5b6f85", "rows": []},
                output_path=REPO_ROOT / "public/member/forbidden_public_source_files.json",
            )
        assert idx["scope"] == "public_mall"
        assert idx["access_envelope"] == "gated_member_mall"
        assert idx["public_hpc_surface_allowed"] is False
        assert idx["source_revision"] == "7432d31e5a68544d2bbab6715f02f64b0b5b6f85"
        assert idx["git_revision"] == pub_graph["git_revision"]
        assert idx["source_revisions"]["census_source_revision"] == "7432d31e5a68544d2bbab6715f02f64b0b5b6f85"

        tiles = idx["tiles"]
        assert tiles["tile:sys:simulator"]["file_count"] == 171
        assert "mesa_model.py" in tiles["tile:sys:simulator"]["files"]
        assert "economics/smartdao_spawning.py" in tiles["tile:sys:simulator"]["files"]
        assert not any("pfmall_state_provider" in p for p in tiles["tile:sys:simulator"]["files"])

        assert tiles["tile:sys:public_member"]["file_count"] == 76
        assert "js/mall-tile-field.js" in tiles["tile:sys:public_member"]["files"]
        assert tiles["tile:mod:foundups.pfmall"]["file_count"] == 48
        assert "member_catalog_export.py" in tiles["tile:mod:foundups.pfmall"]["files"]
        assert tiles["tile:mod:foundups.agent_market"]["file_count"] == 57
        assert "src/in_memory.py" in tiles["tile:mod:foundups.agent_market"]["files"]
        assert tiles["tile:mod:foundups.gotjunk"]["file_count"] == 183

        assert "tile:mod:foundups.tests" not in tiles
        assert "tile:priv:esingularity.jhr_drafts_restricted" not in tiles

    def test_source_file_index_builder_separates_public_and_architect_scopes(
        self, repo_architect_graph, repo_public_graph, tmp_path
    ):
        synthetic_accounting = {
            "repository_slug": "FOUNDUPS/Foundups-Agent",
            "source_revision": "7432d31e5a68544d2bbab6715f02f64b0b5b6f85",
            "rows": [
                {
                    "path": "modules/foundups/simulator/mesa_model.py",
                    "disposition": "MAPPED",
                    "owner_node_id": "modules/foundups/simulator",
                    "git_mode": "100644",
                    "git_object_type": "blob",
                },
                {
                    "path": "modules/foundups/simulator/adapters/pfmall_state_provider.py",
                    "disposition": "MAPPED",
                    "owner_node_id": "modules/foundups/simulator",
                    "git_mode": "100644",
                    "git_object_type": "blob",
                },
                {
                    "path": "modules/foundups/tests/test_foundup_registry_schema.py",
                    "disposition": "MAPPED",
                    "owner_node_id": "modules/foundups/tests",
                    "git_mode": "100644",
                    "git_object_type": "blob",
                },
                {
                    "path": "modules/foundups/esingularity/jhr/drafts/JHR_004.md",
                    "disposition": "MAPPED",
                    "owner_node_id": "priv:esingularity.jhr_drafts_restricted",
                    "git_mode": "100644",
                    "git_object_type": "blob",
                },
            ],
        }

        pub_out = export_public_source_file_index(
            repo_public_graph, synthetic_accounting, output_path=tmp_path / "pub_files.json"
        )
        pub_idx = json.loads(pub_out.read_text(encoding="utf-8"))
        assert pub_idx["tiles"]["tile:sys:simulator"]["files"] == ["mesa_model.py"]
        assert "tile:mod:foundups.tests" not in pub_idx["tiles"]
        assert "tile:priv:esingularity.jhr_drafts_restricted" not in pub_idx["tiles"]

        arch_out = export_architect_source_file_index(
            repo_architect_graph, synthetic_accounting, output_path=tmp_path / "arch_files.json"
        )
        arch_idx = json.loads(arch_out.read_text(encoding="utf-8"))
        assert "adapters/pfmall_state_provider.py" in arch_idx["tiles"]["tile:sys:simulator"]["files"]
        assert "test_foundup_registry_schema.py" in arch_idx["tiles"]["tile:mod:foundups.tests"]["files"]
        jhr_entry = arch_idx["tiles"]["tile:priv:esingularity.jhr_drafts_restricted"]
        assert jhr_entry["files"] == []
        assert jhr_entry["metadata_only_files"] == ["modules/foundups/esingularity/jhr/drafts/JHR_004.md"]

        with pytest.raises(ValueError, match="Refusing to write 012_architect source file index inside public web root"):
            export_architect_source_file_index(
                repo_architect_graph,
                synthetic_accounting,
                output_path=REPO_ROOT / "public/member/forbidden_architect_files.json",
            )


class TestCategoryCoverageAndSourceProvenanceFixes:
    """Regression coverage for census provenance, external anchors, and operational state truth."""

    def test_census_tree_resolves_all_17_formerly_local_tiles_and_buildcanvas(
        self, repo_architect_graph, repo_public_graph
    ):
        census_rev = "7432d31e5a68544d2bbab6715f02f64b0b5b6f85"
        for graph in (repo_architect_graph, repo_public_graph):
            local_fallback = [
                tid
                for tid, tile in graph["tiles"].items()
                if ((tile.get("metadata") or {}).get("source_inspection") or {}).get("availability_status")
                == "VERIFIED_AT_MALL_FEATURE_REVISION_LOCAL"
            ]
            assert local_fallback == [], f"Unexpected feature-local fallbacks: {local_fallback}"

        pub_tiles = repo_public_graph["tiles"]
        for tid, expected_seg, expected_path in (
            ("tile:sys:wsp_framework", "tree", "WSP_framework"),
            ("tile:sys:wsp_agentic", "tree", "WSP_agentic"),
            ("tile:sys:wsp_knowledge", "tree", "WSP_knowledge"),
            ("tile:sys:foundups_mcp_p1", "tree", "foundups-mcp-p1"),
            ("tile:sub:simulator.mockups_and_archive", "tree", "modules/foundups/simulator/archive"),
            ("tile:benchevidence:pkt_02_dependency_tracing", "blob", "modules/foundups/simulator/economics/smartdao_spawning.py"),
            ("tile:benchevidence:pkt_03_duplicate_integration", "blob", "modules/ai_intelligence/ai_gateway/src/ai_gateway.py"),
            ("tile:benchrun:incumbent_deterministic_ast_holo_pkt_02_dependency_tracing", "blob", "modules/foundups/simulator/economics/smartdao_spawning.py"),
            ("tile:benchrun:incumbent_deterministic_ast_holo_pkt_03_duplicate_integration", "blob", "modules/ai_intelligence/ai_gateway/src/ai_gateway.py"),
        ):
            si = pub_tiles[tid]["metadata"]["source_inspection"]
            assert si["availability_status"] == "VERIFIED_AT_CENSUS_BASELINE_REVISION"
            assert si["source_revision"] == census_rev
            assert si["repo_path"] == expected_path
            assert si["source_url"] == f"https://github.com/FOUNDUPS/Foundups-Agent/{expected_seg}/{census_rev}/{expected_path}"

        # buildCanvas fragment split cleanly from repo_path and preserved on source_url
        bc = pub_tiles["tile:mockup:public_index_buildCanvas"]
        assert bc["action_target"]["repo_path"] == "public/index.html"
        assert bc["action_target"]["url_fragment"] == "#buildCanvas"
        bc_si = bc["metadata"]["source_inspection"]
        assert bc_si["availability_status"] == "VERIFIED_AT_CENSUS_BASELINE_REVISION"
        assert bc_si["repo_path"] == "public/index.html"
        assert bc_si["source_url"] == f"https://github.com/FOUNDUPS/Foundups-Agent/blob/{census_rev}/public/index.html#buildCanvas"

        # Sibling-worktree LEGO benchmark stays pinned to sibling revision
        lego_si = pub_tiles["tile:harness:lego_scaffolding_protocol"]["metadata"]["source_inspection"]
        assert lego_si["availability_status"] == "VERIFIED_AT_SIBLING_WORKTREE_REVISION"
        assert lego_si["source_revision"] == "2c936f78c2f17ffe59a6c91cc3e37146a15372ad"

    def test_synthetic_repo_without_git_falls_back_to_manifest_census_sets(self, tmp_path):
        manifest_dir = tmp_path / "modules/foundups/pfmall"
        manifest_dir.mkdir(parents=True)
        (tmp_path / "modules/foundups/pfmall/sample.py").write_text("# sample\n", encoding="utf-8")
        (manifest_dir / "sprint1_registry_benchmark_manifest.json").write_text(
            json.dumps({
                "source_pins": {"audited_main_revision": "7432d31e5a68544d2bbab6715f02f64b0b5b6f85"},
                "census_directory_prefixes": ["modules/foundups/pfmall"],
                "census_file_paths_sample_or_anchors": ["modules/foundups/pfmall/sample.py"],
                "extended_repository_nodes": [
                    {
                        "tile_id": "tile:sys:sample_only",
                        "display_name": "Sample",
                        "parent_tile_id": "tile:mall:root",
                        "repo_path": "modules/foundups/pfmall/sample.py",
                    }
                ],
            }),
            encoding="utf-8",
        )
        graph = build_repo_fractal_tile_graph(tmp_path)
        si = graph["tiles"]["tile:sys:sample_only"]["metadata"]["source_inspection"]
        assert si["availability_status"] == "VERIFIED_AT_CENSUS_BASELINE_REVISION"
        assert si["source_url"] == (
            "https://github.com/FOUNDUPS/Foundups-Agent/blob/"
            "7432d31e5a68544d2bbab6715f02f64b0b5b6f85/modules/foundups/pfmall/sample.py"
        )

    def test_external_repo_submodule_and_registry_verification_completeness(
        self, repo_architect_graph, repo_public_graph
    ):
        pub_tiles = repo_public_graph["tiles"]

        # Science Swarm Hub elif fix: real GitHub URL + exfoliation handoff, never play.foundups.com hash
        ssh = pub_tiles["tile:investor:science_swarm_hub"]
        assert ssh["action_target"]["primary_url"] == "https://github.com/FOUNDUPS/science-swarm-hub"
        assert ssh["action_target"]["in_repo_handoff_path"] == "modules/foundups/pqn_swarm_hub/EXFOLIATION_PLAN.md"
        assert "repo_path" not in ssh["action_target"]
        ssh_si = ssh["metadata"]["source_inspection"]
        assert ssh_si["repository_slug"] == "FOUNDUPS/science-swarm-hub"
        assert ssh_si["source_revision"] == "bdf0e15f019f83d76fa9cf94b131716bde559350"
        assert ssh_si["availability_status"] == "LOCAL_EXTERNAL_REPO_PINNED"
        assert ssh_si["source_url"] == "https://github.com/FOUNDUPS/science-swarm-hub/tree/bdf0e15f019f83d76fa9cf94b131716bde559350"
        assert ssh_si["in_repo_handoff_path"] == "modules/foundups/pqn_swarm_hub/EXFOLIATION_PLAN.md"

        # foundups.github.io pinned tree URL + registry_verification
        ghio = pub_tiles["tile:mockup:foundups_github_io"]
        assert ghio["metadata"]["registry_verification"]["registry_id"] == "ext_repo:foundups.github.io"
        assert ghio["metadata"]["source_inspection"]["source_url"] == (
            "https://github.com/FOUNDUPS/foundups.github.io/tree/56792cee51bc745be9dc3b59e6b588dbd2ba7527"
        )

        # AutoPost keeps live Cloud Run primary_url and separates handoff doc from external repo anchor
        ap = pub_tiles["tile:engine:autopost"]
        assert ap["action_target"]["primary_url"] == "https://foundup-japan-ai-autopost-camera-56566376153.us-west1.run.app/"
        assert ap["action_target"]["in_repo_handoff_path"] == "modules/foundups/pfmall/AUTOPOST_ITEM_CAPTURE_HANDOFF.md"
        assert "repo_path" not in ap["action_target"]
        ap_si = ap["metadata"]["source_inspection"]
        assert ap_si["repository_slug"] == "FOUNDUPS/AutoPost"
        assert ap_si["source_revision"] == "c7fb644c1b8897f2af29f26d7e3dc3838a67ab18"
        assert ap_si["source_url"] == "https://github.com/FOUNDUPS/AutoPost/tree/c7fb644c1b8897f2af29f26d7e3dc3838a67ab18"
        assert ap_si["in_repo_handoff_path"] == "modules/foundups/pfmall/AUTOPOST_ITEM_CAPTURE_HANDOFF.md"

        # Hermes submodule boundary keeps SUBMODULE_GITLINK_BOUNDARY + .gitmodules tree URL
        hermes = pub_tiles["tile:submod:vendor.hermes_agent"]
        hermes_si = hermes["metadata"]["source_inspection"]
        assert hermes_si["availability_status"] == "SUBMODULE_GITLINK_BOUNDARY"
        assert hermes_si["source_revision"] == "d1d425e9d0e0e37bc0855fe5a4142bac86a73b0d"
        assert hermes_si["source_url"] == "https://github.com/FOUNDUPS/hermes-agent/tree/d1d425e9d0e0e37bc0855fe5a4142bac86a73b0d"

        # Harnesses built in _add_tools_and_benchmark also receive registry_verification
        assert pub_tiles["tile:harness:lego_scaffolding_protocol"]["metadata"]["registry_verification"]["registry_id"] == (
            "harness:ai_gateway_lego_benchmark_2c936f78c"
        )
        assert pub_tiles["tile:harness:model_combination_benchmark"]["metadata"]["registry_verification"]["registry_id"] == (
            "harness:ai_gateway_model_benchmarks"
        )

    def test_operational_states_empty_domains_and_withholds_reconciled(
        self, repo_architect_graph, repo_public_graph
    ):
        arch_tiles = repo_architect_graph["tiles"]
        pub_tiles = repo_public_graph["tiles"]

        # Phantom domain system_infra eliminated from both scopes
        assert "tile:domain:system_infra" not in arch_tiles
        assert "tile:domain:system_infra" not in pub_tiles

        # Synthetic fixture hpc_alt stays architect-only
        assert arch_tiles["tile:space:hpc_alt"]["visibility_scope"] == "principal_only"
        assert "tile:space:hpc_alt" not in pub_tiles

        # Childless domains after RED filtering stay in 012_architect (AMBER) and strip cleanly from public_mall
        for dom_tid in ("tile:domain:blockchain", "tile:domain:economy", "tile:domain:telemetry"):
            assert dom_tid in arch_tiles
            assert arch_tiles[dom_tid]["lifecycle"]["state"] == "AMBER"
            assert dom_tid not in pub_tiles
            assert dom_tid not in pub_tiles["tile:modules:root"]["children_tile_ids"]
        assert sorted(repo_public_graph.get("withheld_empty_domain_ids", [])) == [
            "tile:domain:blockchain",
            "tile:domain:economy",
            "tile:domain:telemetry",
        ]

        # Root and section states derived from children
        assert pub_tiles[ROOT_TILE_ID]["lifecycle"]["state"] == "AMBER"
        assert pub_tiles["tile:sys:knowledge_and_governance"]["lifecycle"]["state"] == "GREEN"
        assert pub_tiles["tile:sys:web_and_cloud_surfaces"]["lifecycle"]["state"] == "GREEN"
        assert pub_tiles["tile:space:hpc"]["lifecycle"]["state"] == "GREEN"

        # WSP_* aligned under knowledge_and_governance
        for wsp_tid in ("tile:sys:wsp_framework", "tile:sys:wsp_agentic", "tile:sys:wsp_knowledge"):
            assert pub_tiles[wsp_tid]["parent_tile_id"] == "tile:sys:knowledge_and_governance"
            assert wsp_tid in pub_tiles["tile:sys:knowledge_and_governance"]["children_tile_ids"]

        # Investor ventures with incubating/unready/pending gates never inflate to GREEN
        for inv_tid in (
            "tile:investor:kosei",
            "tile:investor:esingularity_001",
            "tile:engine:holoindex",
            "tile:investor:gotjunk_001",
            "tile:investor:hpc",
            "tile:investor:move2japan",
            "tile:investor:oversight_vote_surface",
        ):
            assert pub_tiles[inv_tid]["lifecycle"]["state"] == "AMBER", f"{inv_tid} should be AMBER"


class TestSlice1RocReportsChaptersAndFoundupKinds:
    """Verify public ROC reports/editions, baseline exclusion, markdown chapter children, and foundup_kind."""

    def test_roc_public_reports_editions_and_baseline_exclusion(
        self, repo_architect_graph, repo_public_graph
    ):
        arch_tiles = repo_architect_graph["tiles"]
        pub_tiles = repo_public_graph["tiles"]

        assert pub_tiles["tile:opus:roc"]["metadata"]["public_roc_edition_manifest_present"] is False
        if "tile:opus:roc.roi_to_roc_baseline" in arch_tiles:
            assert arch_tiles["tile:opus:roc.roi_to_roc_baseline"]["visibility_scope"] == "principal_only"
        assert "tile:opus:roc.roi_to_roc_baseline" not in pub_tiles
        assert "ROI_to_RoC_Paradigm_Shift.md" not in json.dumps(repo_public_graph, ensure_ascii=False)

        expected_roc_reports = {
            "tile:opus:roc.formula_derivation": "modules/foundups/simulator/docs/ROC_FORMULA_DERIVATION.md",
        }
        for tid, rpath in expected_roc_reports.items():
            tile = pub_tiles[tid]
            assert tile["tile_kind"] == "opus_item"
            assert tile["parent_tile_id"] == "tile:opus:roc"
            assert tile["visibility_scope"] == "public"
            assert tile["action_target"]["repo_path"] == rpath
            assert tile["metadata"]["document_class"] == "tracked_repo_roc_report"

        for collision_tid in (
            "tile:opus:roc.candidate_derivation_audit_p1",
            "tile:opus:roc.state_machine_audit_p1",
            "tile:opus:roc.sacrda_dae_dao_readiness",
            "tile:opus:roc.sovereign_consensus_readiness",
            "tile:opus:roc.ritual_milestone_attestation",
        ):
            assert collision_tid not in arch_tiles
            assert collision_tid not in pub_tiles

        expected_linkedin_editions = (
            "tile:opus:roc.edition_2026_11_15_tapping_the_source",
            "tile:opus:roc.edition_2026_10_06_who_owns_roc",
            "tile:opus:roc.edition_2026_09_15_compute_got_a_ticker",
        )
        for tid in expected_linkedin_editions:
            tile = pub_tiles[tid]
            assert tile["tile_kind"] == "opus_item"
            assert tile["parent_tile_id"] == "tile:opus:roc"
            assert tile["evidence_status"] == "claim_requires_independent_evidence"
            assert tile["action_target"]["primary_url"].startswith("https://www.linkedin.com/pulse/")
            assert tile["metadata"]["published_date"]
            assert tile["metadata"]["published_at"] == tile["metadata"]["published_date"]
            assert tile["metadata"]["editorial_stage"] == "PUBLISHED"
            assert tile["metadata"]["document_class"] == "linkedin_primary_roc_edition"
            assert tile["metadata"]["publication_presence_observed_on"] == "2026-11-24"

        assert _read_pinned_text(REPO_ROOT, "README.md", "invalid_rev") == ""
        assert _read_pinned_text(REPO_ROOT, "does/not/exist.md", "7432d31e5a68544d2bbab6715f02f64b0b5b6f85") == ""

    def test_extract_markdown_chapters_ignores_fences_and_preserves_ranges(self):
        sample = (
            "# Title\n"
            "```markdown\n"
            "## Fake Fenced Heading\n"
            "```\n"
            "## Chapter One\n"
            "First paragraph with H:\\rho and [link](https://example.com).\n"
            "## Chapter Two\n"
            "Second paragraph.\n"
        )
        chapters = _extract_markdown_chapters(sample, max_chapters=20)
        assert [c["title"] for c in chapters] == ["Chapter One", "Chapter Two"]
        assert chapters[0]["start_line"] == 5
        assert chapters[0]["end_line"] == 6
        assert chapters[1]["start_line"] == 7
        assert chapters[1]["end_line"] == 8
        assert scan_wsp71_leaks(chapters) == []

    def test_paper_and_report_chapter_children_populated_and_safe(
        self, repo_public_graph
    ):
        pub_tiles = repo_public_graph["tiles"]
        expected_parents = {
            "tile:opus:papers.resp_quantum_self_reference.md": 12,
            "tile:opus:papers.peer_preservation_shared_latent_coupling.md": 14,
            "tile:opus:papers.pqn_research_plan.md": 13,
            "tile:opus:papers.resp_supplementary_materials.md": 15,
            "tile:opus:papers.dukkyo_practitioners.md": 12,
            "tile:opus:jhr.001": 20,
            "tile:opus:jhr.003": 10,
            "tile:opus:roc.formula_derivation": 14,
        }
        for parent_tid, expected_count in expected_parents.items():
            parent_tile = pub_tiles[parent_tid]
            assert parent_tile["metadata"]["chapter_count"] == expected_count
            ch_ids = [cid for cid in parent_tile["children_tile_ids"] if ".ch" in cid]
            assert len(ch_ids) == expected_count
            first_ch = pub_tiles[ch_ids[0]]
            assert first_ch["tile_kind"] == "opus_item"
            assert first_ch["action_target"]["repo_path"] == parent_tile["action_target"]["repo_path"]
            meta = first_ch["metadata"]
            assert meta["chapter_index"] == 1
            assert meta["chapter_count"] == expected_count
            assert 1 <= meta["start_line"] <= meta["end_line"]
            assert meta["parent_document_title"] == parent_tile["display_name"]
            si = meta["source_inspection"]
            assert si["line_start"] == meta["start_line"]
            assert si["line_end"] == meta["end_line"]
            assert si["url"].endswith(f"#L{meta['start_line']}-L{meta['end_line']}")

    def test_canonical_foundup_kind_and_element_modes_present(self, repo_public_graph):
        pub_tiles = repo_public_graph["tiles"]
        valid_modes = {"video", "pictures", "podcast", "cards"}
        for tid, tile in pub_tiles.items():
            meta = tile["metadata"]
            assert meta["foundup_kind"] in ("tool", "application", "card"), f"{tid} missing valid foundup_kind"
            modes = meta["canonical_element_modes"]
            assert isinstance(modes, list) and len(modes) >= 1
            assert set(modes).issubset(valid_modes), f"{tid} invalid element modes {modes}"

        assert pub_tiles["tile:engine:holoindex"]["metadata"]["foundup_kind"] == "tool"
        assert pub_tiles["tile:engine:autopost"]["metadata"]["foundup_kind"] == "tool"
        assert pub_tiles["tile:sys:simulator"]["metadata"]["foundup_kind"] == "tool"
        assert pub_tiles["tile:space:hpc"]["metadata"]["foundup_kind"] == "application"
        assert pub_tiles["tile:investor:gotjunk_001"]["metadata"]["foundup_kind"] == "application"
        assert pub_tiles["tile:investor:move2japan"]["metadata"]["foundup_kind"] == "application"
        assert pub_tiles["tile:investor:esingularity_001"]["metadata"]["foundup_kind"] == "application"
        assert pub_tiles["tile:stream:lane.antifafm"]["metadata"]["foundup_kind"] == "application"
        assert pub_tiles["tile:market:japan_akiya"]["metadata"]["foundup_kind"] == "application"
        for card_tid in (
            "tile:opus:papers",
            "tile:opus:papers.resp_quantum_self_reference.md",
            "tile:opus:papers.resp_quantum_self_reference.md.ch01",
            "tile:opus:jhr.001",
            "tile:opus:roc.formula_derivation",
        ):
            assert pub_tiles[card_tid]["metadata"]["foundup_kind"] == "card"
            assert pub_tiles[card_tid]["metadata"]["canonical_element_kind"] == "card"
            assert pub_tiles[card_tid]["metadata"]["canonical_element_modes"] == ["cards"]
        assert "video" in pub_tiles["tile:stream:wikitube_featured"]["metadata"]["canonical_element_modes"]
        assert "cards" in pub_tiles["tile:stream:wikitube_featured"]["metadata"]["canonical_element_modes"]
        assert "podcast" in pub_tiles["tile:stream:lane.antifafm"]["metadata"]["canonical_element_modes"]
