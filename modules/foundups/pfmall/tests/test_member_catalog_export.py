#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for member Mall catalog export.

Verifies that the exported catalog matches canonical pfmall truth,
includes required presentation fields, and preserves the shape
consumed by public/member/index.html.
"""

import json
import pytest
from pathlib import Path

from modules.foundups.pfmall.api import reset_default_shell
from modules.foundups.pfmall.fractal_tile_graph import (
    ROOT_TILE_ID,
    build_graph_indices,
    compute_tiles_etag,
    make_tile,
)
from modules.foundups.pfmall.member_catalog_export import (
    _OWNER_NODE_TILE_FALLBACKS,
    build_fractal_source_file_index,
    build_mall_catalog,
    export_mall_catalog,
    validate_source_file_index,
)
from modules.foundups.pfmall.member_presentation import (
    MEMBER_PRESENTATION,
    get_presentation,
)


@pytest.fixture(autouse=True)
def _reset():
    reset_default_shell()
    yield
    reset_default_shell()


EXPECTED_IDS = {"antifafm_001", "gotjunk_001", "magadoom_001"}


# ---------------------------------------------------------------------------
# build_mall_catalog()
# ---------------------------------------------------------------------------

class TestBuildMallCatalog:
    """Tests for build_mall_catalog()."""

    def test_produces_list(self):
        catalog = build_mall_catalog()
        assert isinstance(catalog, list)

    def test_includes_seeded_foundups(self):
        catalog = build_mall_catalog()
        ids = {e["foundup_id"] for e in catalog}
        assert EXPECTED_IDS.issubset(ids)

    def test_canonical_fields_present(self):
        """Each entry has the 10 tile-derived fields."""
        catalog = build_mall_catalog()
        tile_fields = {
            "foundup_id", "name", "tagline", "description", "category",
            "tier", "lifecycle_stage", "launch_readiness", "token_symbol",
            "routing_prefix",
        }
        for entry in catalog:
            assert tile_fields.issubset(entry.keys()), (
                f"{entry['foundup_id']} missing: {tile_fields - entry.keys()}"
            )

    def test_presentation_fields_present(self):
        """Each entry has the 4 presentation fields."""
        catalog = build_mall_catalog()
        pres_fields = {"theme", "hero_label", "hero_mood", "entry_copy"}
        for entry in catalog:
            assert pres_fields.issubset(entry.keys()), (
                f"{entry['foundup_id']} missing: {pres_fields - entry.keys()}"
            )

    def test_readiness_matches_manifest(self):
        """Readiness posture matches canonical manifest truth."""
        catalog = build_mall_catalog()
        by_id = {e["foundup_id"]: e for e in catalog}
        assert by_id["antifafm_001"]["launch_readiness"] == "discoverable_only"
        assert by_id["gotjunk_001"]["launch_readiness"] == "conditional"
        assert by_id["magadoom_001"]["launch_readiness"] == "discoverable_only"

    def test_lifecycle_matches_manifest(self):
        catalog = build_mall_catalog()
        by_id = {e["foundup_id"]: e for e in catalog}
        assert by_id["antifafm_001"]["lifecycle_stage"] == "proto"
        assert by_id["gotjunk_001"]["lifecycle_stage"] == "proto"
        assert by_id["magadoom_001"]["lifecycle_stage"] == "incubating"

    def test_routing_prefixes(self):
        catalog = build_mall_catalog()
        by_id = {e["foundup_id"]: e for e in catalog}
        assert by_id["gotjunk_001"]["routing_prefix"] == "/f/gotjunk_001"
        assert by_id["antifafm_001"]["routing_prefix"] == "/f/antifafm_001"

    def test_category_matches_manifest(self):
        catalog = build_mall_catalog()
        by_id = {e["foundup_id"]: e for e in catalog}
        assert by_id["antifafm_001"]["category"] == "media"
        assert by_id["gotjunk_001"]["category"] == "marketplace"
        assert by_id["magadoom_001"]["category"] == "games"

    def test_sorted_by_name(self):
        """Catalog entries are sorted by name (inherits from list_foundups)."""
        catalog = build_mall_catalog()
        names = [e["name"] for e in catalog]
        assert names == sorted(names)


# ---------------------------------------------------------------------------
# Presentation overrides
# ---------------------------------------------------------------------------

class TestMemberPresentation:
    """Tests for member_presentation module."""

    def test_known_foundup_has_overrides(self):
        p = get_presentation("antifafm_001")
        assert p["theme"] == "antifafm"
        assert p["hero_label"] == "SIGNAL"
        assert p["hero_mood"] != ""
        assert p["entry_copy"] != ""

    def test_unknown_foundup_gets_defaults(self):
        p = get_presentation("nonexistent_999")
        assert p["theme"] == "default"
        assert p["hero_label"] == ""

    def test_all_seeded_have_overrides(self):
        for fid in EXPECTED_IDS:
            p = get_presentation(fid)
            assert p["theme"] != "default", f"{fid} missing presentation"


# ---------------------------------------------------------------------------
# export_mall_catalog()
# ---------------------------------------------------------------------------

class TestExportMallCatalog:
    """Tests for export_mall_catalog() file generation."""

    def test_writes_valid_json(self, tmp_path):
        out = tmp_path / "mall-catalog.json"
        export_mall_catalog(output_path=out)
        data = json.loads(out.read_text(encoding="utf-8"))
        assert isinstance(data, list)
        assert len(data) >= 3

    def test_output_matches_build(self, tmp_path):
        """Written file matches build_mall_catalog() output."""
        out = tmp_path / "mall-catalog.json"
        export_mall_catalog(output_path=out)
        written = json.loads(out.read_text(encoding="utf-8"))
        built = build_mall_catalog()
        assert written == built

    def test_member_mall_shape_compatible(self, tmp_path):
        """Output shape matches what public/member/index.html expects."""
        out = tmp_path / "mall-catalog.json"
        export_mall_catalog(output_path=out)
        data = json.loads(out.read_text(encoding="utf-8"))
        # index.html accesses these fields on each item
        required_by_html = {
            "foundup_id", "name", "tagline", "description", "category",
            "tier", "lifecycle_stage", "launch_readiness", "token_symbol",
            "routing_prefix", "theme", "hero_label", "hero_mood", "entry_copy",
        }
        for entry in data:
            assert required_by_html.issubset(entry.keys()), (
                f"{entry.get('foundup_id', '?')} missing: {required_by_html - entry.keys()}"
            )


class TestFractalSourceFileIndexProvenance:
    """Verify source-file index provenance headers, owner fallbacks, and validation."""

    def test_owner_node_tile_fallbacks_cover_all_three_nodes(self):
        assert _OWNER_NODE_TILE_FALLBACKS == {
            "ext_repo:foundups.github.io": "tile:mockup:foundups_github_io",
            "harness:ai_gateway_lego_benchmark_2c936f78c": "tile:harness:lego_scaffolding_protocol",
            "harness:ai_gateway_model_benchmarks": "tile:harness:model_combination_benchmark",
        }

    def test_build_and_validate_source_file_index_provenance_headers(self):
        census_rev = "7432d31e5a68544d2bbab6715f02f64b0b5b6f85"
        head_rev = "b0ba2d7b41e4425f41ccb4a7f09ed2f7b1c667c8"
        tiles = {
            ROOT_TILE_ID: make_tile(
                tile_id=ROOT_TILE_ID,
                display_name="PlayFoundups Mall",
                tile_kind="system_cube",
                visibility_scope="public",
                owner_namespace="foundups_core",
                parent_tile_id=None,
                state="AMBER",
            ),
            "tile:harness:model_combination_benchmark": make_tile(
                tile_id="tile:harness:model_combination_benchmark",
                display_name="Model Combination Benchmark",
                tile_kind="system_cube",
                visibility_scope="public",
                owner_namespace="foundups_core",
                parent_tile_id=ROOT_TILE_ID,
                state="GREEN",
                metadata={"registry_verification": {"registry_id": "harness:ai_gateway_model_benchmarks"}},
            ),
        }
        tiles[ROOT_TILE_ID]["children_tile_ids"].append("tile:harness:model_combination_benchmark")
        etag = compute_tiles_etag(tiles)
        indices = build_graph_indices(tiles)
        pub_graph = {
            "schema_version": "fractal_tile_graph.v1",
            "git_revision": head_rev,
            "source_revisions": {
                "census_source_revision": census_rev,
                "mall_feature_code_revision": head_rev,
                "scanner_projector_revision": head_rev,
            },
            "graph_etag": etag,
            "public_graph_etag": etag,
            "scope": "public_mall",
            "root_tile_id": ROOT_TILE_ID,
            "counts": indices["counts"],
            "links": indices["links"],
            "search_index": indices["search_index"],
            "tiles": tiles,
        }
        acct = {
            "repository_slug": "FOUNDUPS/Foundups-Agent",
            "source_revision": census_rev,
            "rows": [
                {
                    "path": "modules/ai_intelligence/ai_gateway/src/model_combination_benchmark_harness.py",
                    "disposition": "MAPPED",
                    "owner_node_id": "harness:ai_gateway_model_benchmarks",
                    "git_mode": "100644",
                    "git_object_type": "blob",
                }
            ],
        }
        idx = build_fractal_source_file_index(pub_graph, acct, scope="public_mall")
        assert idx["source_revision"] == census_rev
        assert idx["git_revision"] == head_rev
        assert idx["source_revisions"]["census_source_revision"] == census_rev
        assert idx["source_revisions"]["mall_feature_code_revision"] == head_rev
        assert idx["source_revisions"]["scanner_projector_revision"] == head_rev
        assert validate_source_file_index(idx, pub_graph) == []

        bad_census = dict(idx)
        bad_census["source_revisions"] = {"census_source_revision": "0" * 40}
        assert any("census_source_revision" in err for err in validate_source_file_index(bad_census, pub_graph))

        bad_git = dict(idx)
        bad_git["git_revision"] = ""
        assert any("git_revision" in err for err in validate_source_file_index(bad_git, pub_graph))
