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
from modules.foundups.pfmall.member_catalog_export import (
    build_mall_catalog,
    export_mall_catalog,
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
