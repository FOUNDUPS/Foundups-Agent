#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for p.fMALL Shell Core Scaffold.

Covers manifest discovery, validation, catalog assembly, route resolution,
tile building (with/without overlay), and graceful degradation.
"""

import json
import pytest
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from modules.foundups.pfmall.shell_core import (
    FoundUpManifest,
    FoundUpStateOverlay,
    FoundUpTile,
    PfmallShell,
    RouteKind,
    RouteTarget,
    ShellCatalog,
    ShellConfig,
    build_foundup_tile,
    create_pfmall_shell,
    discover_manifests,
    load_manifest,
    resolve_route,
    validate_manifest,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _valid_manifest_data(**overrides) -> dict:
    """Return a valid manifest dict with optional overrides."""
    base = {
        "foundup_id": "test_001",
        "name": "TestFoundUp",
        "version": "1.0.0",
        "tier": "F0_DAE",
        "lifecycle_stage": "proto",
        "category": "marketplace",
        "tagline": "Test tagline",
        "description": "Test description",
        "token_symbol": "TEST",
        "owner_id": "012",
        "routing_prefix": "/f/test_001",
        "is_invite_only": True,
    }
    base.update(overrides)
    return base


def _make_manifest(**overrides) -> FoundUpManifest:
    """Create a FoundUpManifest with sensible defaults."""
    data = _valid_manifest_data(**overrides)
    return load_manifest(data)


class MockStateProvider:
    """Mock StateOverlayProvider for testing."""

    def __init__(self, overlays: Optional[Dict[str, FoundUpStateOverlay]] = None):
        self._overlays = overlays or {}

    @property
    def provider_id(self) -> str:
        return "mock"

    def get_foundup_state(self, foundup_id: str) -> Optional[FoundUpStateOverlay]:
        return self._overlays.get(foundup_id)

    def list_foundup_states(self) -> List[FoundUpStateOverlay]:
        return list(self._overlays.values())

    def get_state_freshness(self, foundup_id: str) -> Optional[int]:
        overlay = self._overlays.get(foundup_id)
        return overlay.freshness_ttl if overlay else None


class FailingProvider:
    """Provider that raises on every call."""

    @property
    def provider_id(self) -> str:
        return "failing"

    def get_foundup_state(self, foundup_id: str):
        raise RuntimeError("provider crashed")

    def list_foundup_states(self):
        raise RuntimeError("provider crashed")

    def get_state_freshness(self, foundup_id: str):
        raise RuntimeError("provider crashed")


# ---------------------------------------------------------------------------
# Manifest Validation
# ---------------------------------------------------------------------------

class TestValidateManifest:
    """Tests for validate_manifest."""

    def test_valid_manifest(self):
        """Valid manifest returns no errors."""
        errors = validate_manifest(_valid_manifest_data())
        assert errors == []

    def test_missing_foundup_id(self):
        data = _valid_manifest_data()
        del data["foundup_id"]
        errors = validate_manifest(data)
        assert any("foundup_id" in e for e in errors)

    def test_missing_name(self):
        data = _valid_manifest_data()
        del data["name"]
        errors = validate_manifest(data)
        assert any("name" in e for e in errors)

    def test_missing_version(self):
        data = _valid_manifest_data()
        del data["version"]
        errors = validate_manifest(data)
        assert any("version" in e for e in errors)

    def test_missing_tier(self):
        data = _valid_manifest_data()
        del data["tier"]
        errors = validate_manifest(data)
        assert any("tier" in e for e in errors)

    def test_missing_lifecycle_stage(self):
        data = _valid_manifest_data()
        del data["lifecycle_stage"]
        errors = validate_manifest(data)
        assert any("lifecycle_stage" in e for e in errors)

    def test_empty_required_field(self):
        """Empty string for required field is invalid."""
        data = _valid_manifest_data(name="")
        errors = validate_manifest(data)
        assert any("name" in e for e in errors)

    def test_invalid_tier(self):
        data = _valid_manifest_data(tier="F99_INVALID")
        errors = validate_manifest(data)
        assert any("tier" in e for e in errors)

    def test_invalid_lifecycle_stage(self):
        data = _valid_manifest_data(lifecycle_stage="nonexistent")
        errors = validate_manifest(data)
        assert any("lifecycle_stage" in e for e in errors)

    def test_foundup_id_too_short(self):
        data = _valid_manifest_data(foundup_id="ab")
        errors = validate_manifest(data)
        assert any("too short" in e for e in errors)

    def test_non_string_foundup_id(self):
        data = _valid_manifest_data(foundup_id=123)
        errors = validate_manifest(data)
        assert any("string" in e for e in errors)

    def test_multiple_errors(self):
        """Multiple issues produce multiple errors."""
        data = {"tier": "INVALID"}
        errors = validate_manifest(data)
        assert len(errors) >= 4  # missing id, name, version, stage + invalid tier

    def test_valid_all_stages(self):
        """All valid lifecycle stages pass."""
        for stage in ["idea", "PoC", "soft-proto", "Proto", "mvp", "Launch"]:
            data = _valid_manifest_data(lifecycle_stage=stage)
            errors = validate_manifest(data)
            assert errors == [], f"Stage {stage} should be valid"


# ---------------------------------------------------------------------------
# Manifest Loading
# ---------------------------------------------------------------------------

class TestLoadManifest:
    """Tests for load_manifest."""

    def test_load_from_dict(self):
        """Load manifest from valid dict."""
        manifest = load_manifest(_valid_manifest_data())
        assert manifest is not None
        assert manifest.foundup_id == "test_001"
        assert manifest.name == "TestFoundUp"
        assert manifest.tier == "F0_DAE"

    def test_load_from_dict_invalid(self):
        """Invalid dict returns None."""
        manifest = load_manifest({"name": "Missing ID"})
        assert manifest is None

    def test_load_from_file(self, tmp_path):
        """Load manifest from JSON file."""
        data = _valid_manifest_data(foundup_id="file_001", name="FileFoundUp")
        manifest_path = tmp_path / "foundup_manifest.json"
        manifest_path.write_text(json.dumps(data), encoding="utf-8")

        manifest = load_manifest(manifest_path)
        assert manifest is not None
        assert manifest.foundup_id == "file_001"
        assert manifest.name == "FileFoundUp"

    def test_load_from_missing_file(self, tmp_path):
        """Missing file returns None."""
        result = load_manifest(tmp_path / "nonexistent.json")
        assert result is None

    def test_load_from_malformed_json(self, tmp_path):
        """Malformed JSON file returns None."""
        bad = tmp_path / "bad.json"
        bad.write_text("{invalid json", encoding="utf-8")
        result = load_manifest(bad)
        assert result is None

    def test_load_preserves_optional_fields(self):
        """Optional fields are preserved when present."""
        data = _valid_manifest_data(
            capabilities=["search", "agents_basic"],
            token_symbol="JUNK",
            is_invite_only=False,
        )
        manifest = load_manifest(data)
        assert manifest.capabilities == ["search", "agents_basic"]
        assert manifest.token_symbol == "JUNK"
        assert manifest.is_invite_only is False

    def test_load_defaults_optional_fields(self):
        """Optional fields get defaults when absent."""
        data = _valid_manifest_data()
        manifest = load_manifest(data)
        assert manifest.capabilities == []
        assert manifest.data_namespace == ""
        assert manifest.holo_collections == []

    def test_load_unsupported_type(self):
        """Unsupported source type returns None."""
        result = load_manifest(42)
        assert result is None


# ---------------------------------------------------------------------------
# Manifest Discovery
# ---------------------------------------------------------------------------

class TestDiscoverManifests:
    """Tests for discover_manifests."""

    def test_discover_in_subdirectories(self, tmp_path):
        """Finds manifests in subdirectories of search paths."""
        # Create two FoundUp directories with manifests
        (tmp_path / "alpha").mkdir()
        (tmp_path / "alpha" / "foundup_manifest.json").write_text(
            json.dumps(_valid_manifest_data(foundup_id="alpha_001", name="Alpha")),
            encoding="utf-8",
        )
        (tmp_path / "beta").mkdir()
        (tmp_path / "beta" / "foundup_manifest.json").write_text(
            json.dumps(_valid_manifest_data(foundup_id="beta_001", name="Beta")),
            encoding="utf-8",
        )

        paths = discover_manifests([tmp_path])
        assert len(paths) == 2
        names = [p.parent.name for p in paths]
        assert "alpha" in names
        assert "beta" in names

    def test_discover_skips_files(self, tmp_path):
        """Does not descend into files at the search path level."""
        (tmp_path / "not_a_dir.txt").write_text("nope")
        paths = discover_manifests([tmp_path])
        assert paths == []

    def test_discover_skips_dirs_without_manifest(self, tmp_path):
        """Skips directories without foundup_manifest.json."""
        (tmp_path / "empty_dir").mkdir()
        (tmp_path / "has_other").mkdir()
        (tmp_path / "has_other" / "README.md").write_text("hi")

        paths = discover_manifests([tmp_path])
        assert paths == []

    def test_discover_empty_search_paths(self):
        """Empty search paths returns empty list."""
        paths = discover_manifests([])
        assert paths == []

    def test_discover_nonexistent_path(self, tmp_path):
        """Nonexistent path is silently skipped."""
        paths = discover_manifests([tmp_path / "nonexistent"])
        assert paths == []

    def test_discover_multiple_search_paths(self, tmp_path):
        """Discovers across multiple search paths."""
        dir_a = tmp_path / "a"
        dir_b = tmp_path / "b"
        dir_a.mkdir()
        dir_b.mkdir()
        (dir_a / "f1").mkdir()
        (dir_a / "f1" / "foundup_manifest.json").write_text(
            json.dumps(_valid_manifest_data(foundup_id="fup_001")),
            encoding="utf-8",
        )
        (dir_b / "f2").mkdir()
        (dir_b / "f2" / "foundup_manifest.json").write_text(
            json.dumps(_valid_manifest_data(foundup_id="fup_002")),
            encoding="utf-8",
        )

        paths = discover_manifests([dir_a, dir_b])
        assert len(paths) == 2


# ---------------------------------------------------------------------------
# Shell Catalog
# ---------------------------------------------------------------------------

class TestShellCatalog:
    """Tests for ShellCatalog."""

    def test_register_and_get(self):
        """Register and retrieve by ID."""
        catalog = ShellCatalog()
        m = _make_manifest(foundup_id="cat_001")
        catalog.register(m)
        assert catalog.get("cat_001") is m

    def test_get_unknown(self):
        """Get unknown ID returns None."""
        catalog = ShellCatalog()
        assert catalog.get("nonexistent") is None

    def test_find_by_id(self):
        """Find by exact ID."""
        catalog = ShellCatalog()
        m = _make_manifest(foundup_id="cat_001")
        catalog.register(m)
        assert catalog.find("cat_001") is m

    def test_find_by_name(self):
        """Find by name (case-insensitive)."""
        catalog = ShellCatalog()
        m = _make_manifest(foundup_id="cat_001", name="GotJunk")
        catalog.register(m)
        assert catalog.find("gotjunk") is m
        assert catalog.find("GOTJUNK") is m

    def test_find_not_found(self):
        """Find returns None for unknown name/ID."""
        catalog = ShellCatalog()
        assert catalog.find("nope") is None

    def test_list_entries_sorted(self):
        """List returns entries sorted by name."""
        catalog = ShellCatalog()
        catalog.register(_make_manifest(foundup_id="z_001", name="Zeta"))
        catalog.register(_make_manifest(foundup_id="a_001", name="Alpha"))
        catalog.register(_make_manifest(foundup_id="m_001", name="Mid"))

        entries = catalog.list_entries()
        names = [e.name for e in entries]
        assert names == ["Alpha", "Mid", "Zeta"]

    def test_list_entries_filtered(self):
        """List filters by category."""
        catalog = ShellCatalog()
        catalog.register(_make_manifest(foundup_id="mkt_001", name="M1", category="marketplace"))
        catalog.register(_make_manifest(foundup_id="gam_001", name="G1", category="games"))
        catalog.register(_make_manifest(foundup_id="mkt_002", name="M2", category="marketplace"))

        entries = catalog.list_entries(category="marketplace")
        assert len(entries) == 2
        assert all(e.category == "marketplace" for e in entries)

    def test_list_entries_filter_case_insensitive(self):
        """Category filter is case-insensitive."""
        catalog = ShellCatalog()
        catalog.register(_make_manifest(foundup_id="gam_001", name="G1", category="Games"))
        entries = catalog.list_entries(category="games")
        assert len(entries) == 1

    def test_count(self):
        """Count reflects registered entries."""
        catalog = ShellCatalog()
        assert catalog.count == 0
        catalog.register(_make_manifest(foundup_id="aaa_001"))
        assert catalog.count == 1
        catalog.register(_make_manifest(foundup_id="bbb_001"))
        assert catalog.count == 2

    def test_register_overwrites_same_id(self):
        """Registering same ID overwrites previous."""
        catalog = ShellCatalog()
        catalog.register(_make_manifest(foundup_id="dup", name="V1"))
        catalog.register(_make_manifest(foundup_id="dup", name="V2"))
        assert catalog.count == 1
        assert catalog.get("dup").name == "V2"

    def test_foundup_ids(self):
        """foundup_ids returns all registered IDs."""
        catalog = ShellCatalog()
        catalog.register(_make_manifest(foundup_id="aaa_001"))
        catalog.register(_make_manifest(foundup_id="bbb_001"))
        assert set(catalog.foundup_ids) == {"aaa_001", "bbb_001"}


# ---------------------------------------------------------------------------
# Route Resolution
# ---------------------------------------------------------------------------

class TestResolveRoute:
    """Tests for resolve_route."""

    def _catalog_with(self, *ids):
        """Create catalog with given FoundUp IDs."""
        catalog = ShellCatalog()
        for fid in ids:
            catalog.register(_make_manifest(foundup_id=fid, name=f"FU_{fid}"))
        return catalog

    def test_shell_route_root(self):
        """/ resolves to shell route."""
        target = resolve_route("/", self._catalog_with())
        assert target.kind == RouteKind.SHELL
        assert target.path == "/"

    def test_shell_route_discover(self):
        target = resolve_route("/discover", self._catalog_with())
        assert target.kind == RouteKind.SHELL

    def test_shell_route_wallet(self):
        target = resolve_route("/wallet", self._catalog_with())
        assert target.kind == RouteKind.SHELL

    def test_shell_route_search(self):
        target = resolve_route("/search", self._catalog_with())
        assert target.kind == RouteKind.SHELL

    def test_shell_route_settings(self):
        target = resolve_route("/settings", self._catalog_with())
        assert target.kind == RouteKind.SHELL

    def test_shell_route_auth_callback(self):
        target = resolve_route("/auth/callback", self._catalog_with())
        assert target.kind == RouteKind.SHELL

    def test_foundup_route_root(self):
        """FoundUp route resolves with correct ID."""
        catalog = self._catalog_with("gotjunk_001")
        target = resolve_route("/f/gotjunk_001", catalog)
        assert target.kind == RouteKind.FOUNDUP
        assert target.foundup_id == "gotjunk_001"
        assert target.foundup_path == "/"

    def test_foundup_route_with_path(self):
        """FoundUp route preserves sub-path."""
        catalog = self._catalog_with("gotjunk_001")
        target = resolve_route("/f/gotjunk_001/listings/search", catalog)
        assert target.kind == RouteKind.FOUNDUP
        assert target.foundup_id == "gotjunk_001"
        assert target.foundup_path == "/listings/search"

    def test_foundup_route_unknown(self):
        """Unknown FoundUp returns NOT_FOUND."""
        catalog = self._catalog_with("gotjunk_001")
        target = resolve_route("/f/nonexistent", catalog)
        assert target.kind == RouteKind.NOT_FOUND
        assert "unknown FoundUp" in target.error

    def test_foundup_route_missing_id(self):
        """Missing FoundUp ID in /f/ returns NOT_FOUND."""
        target = resolve_route("/f/", self._catalog_with())
        assert target.kind == RouteKind.NOT_FOUND

    def test_unknown_path(self):
        """Unrecognized path returns NOT_FOUND."""
        target = resolve_route("/random/path", self._catalog_with())
        assert target.kind == RouteKind.NOT_FOUND
        assert "no matching route" in target.error

    def test_trailing_slash_stripped(self):
        """Trailing slash is normalized."""
        target = resolve_route("/discover/", self._catalog_with())
        assert target.kind == RouteKind.SHELL
        assert target.path == "/discover"

    def test_shell_route_priority_over_foundup(self):
        """Shell route takes priority if collision existed."""
        # /discover is a shell route — should never be a FoundUp prefix
        target = resolve_route("/discover", self._catalog_with())
        assert target.kind == RouteKind.SHELL


# ---------------------------------------------------------------------------
# Tile Builder
# ---------------------------------------------------------------------------

class TestBuildFoundUpTile:
    """Tests for build_foundup_tile."""

    def test_tile_without_overlay(self):
        """Tile from manifest only has unknown overlay fields."""
        manifest = _make_manifest()
        tile = build_foundup_tile(manifest)

        assert tile.foundup_id == "test_001"
        assert tile.name == "TestFoundUp"
        assert tile.tier == "F0_DAE"
        # Overlay fields default
        assert tile.health_status == "unknown"
        assert tile.availability == "unknown"
        assert tile.cabr_score == 0.0
        assert tile.state_provider == "none"

    def test_tile_with_overlay(self):
        """Tile merges overlay advisory fields."""
        manifest = _make_manifest()
        overlay = FoundUpStateOverlay(
            foundup_id="test_001",
            health_status="healthy",
            availability="online",
            cabr_score=0.75,
            cabr_trend="rising",
            agent_activity={"active_agents": 3, "tasks_in_flight": 7},
            reserve_summary={"reserve_health": "strong"},
            state_provider="simulator",
            freshness_ttl=45,
            last_updated_at="2026-03-31T12:00:00Z",
        )

        tile = build_foundup_tile(manifest, overlay)

        # Manifest fields preserved
        assert tile.foundup_id == "test_001"
        assert tile.name == "TestFoundUp"
        assert tile.tier == "F0_DAE"
        # Overlay fields merged
        assert tile.health_status == "healthy"
        assert tile.availability == "online"
        assert tile.cabr_score == 0.75
        assert tile.cabr_trend == "rising"
        assert tile.active_agents == 3
        assert tile.tasks_in_flight == 7
        assert tile.reserve_health == "strong"
        assert tile.state_provider == "simulator"
        assert tile.freshness_ttl == 45

    def test_tile_overlay_never_overrides_manifest(self):
        """Overlay cannot change manifest-authoritative fields."""
        manifest = _make_manifest(name="RealName", tier="F0_DAE")
        overlay = FoundUpStateOverlay(foundup_id="test_001")

        tile = build_foundup_tile(manifest, overlay)
        assert tile.name == "RealName"
        assert tile.tier == "F0_DAE"

    def test_tile_routing_prefix_fallback(self):
        """Routing prefix defaults to /f/{id} when not set."""
        manifest = _make_manifest(routing_prefix="")
        tile = build_foundup_tile(manifest)
        assert tile.routing_prefix == "/f/test_001"

    def test_tile_overlay_missing_agent_activity(self):
        """Handles overlay with empty agent_activity."""
        manifest = _make_manifest()
        overlay = FoundUpStateOverlay(
            foundup_id="test_001",
            health_status="degraded",
            agent_activity={},
        )
        tile = build_foundup_tile(manifest, overlay)
        assert tile.active_agents == 0
        assert tile.tasks_in_flight == 0


# ---------------------------------------------------------------------------
# PfmallShell Integration
# ---------------------------------------------------------------------------

class TestPfmallShell:
    """Tests for PfmallShell orchestrator."""

    def test_create_shell(self):
        """Factory creates shell instance."""
        shell = create_pfmall_shell()
        assert shell is not None
        assert shell.catalog.count == 0
        assert shell.is_booted is False

    def test_register_manifest(self):
        """Manual manifest registration."""
        shell = create_pfmall_shell()
        m = _make_manifest(foundup_id="manual_001")
        shell.register_manifest(m)
        assert shell.catalog.count == 1
        assert shell.catalog.get("manual_001") is m

    def test_build_catalog(self):
        """Build catalog returns registered manifests."""
        shell = create_pfmall_shell()
        shell.register_manifest(_make_manifest(foundup_id="alpha_001", name="Alpha", category="games"))
        shell.register_manifest(_make_manifest(foundup_id="beta_001", name="Beta", category="media"))

        all_entries = shell.build_catalog()
        assert len(all_entries) == 2

        games = shell.build_catalog(category="games")
        assert len(games) == 1
        assert games[0].name == "Alpha"

    def test_resolve_route_shell(self):
        """Shell route resolution through orchestrator."""
        shell = create_pfmall_shell()
        target = shell.resolve_route("/discover")
        assert target.kind == RouteKind.SHELL

    def test_resolve_route_foundup(self):
        """FoundUp route resolution through orchestrator."""
        shell = create_pfmall_shell()
        shell.register_manifest(_make_manifest(foundup_id="gj_001"))
        target = shell.resolve_route("/f/gj_001/home")
        assert target.kind == RouteKind.FOUNDUP
        assert target.foundup_id == "gj_001"
        assert target.foundup_path == "/home"

    def test_build_tile_no_provider(self):
        """Tile built without provider has unknown overlay."""
        shell = create_pfmall_shell()
        shell.register_manifest(_make_manifest(foundup_id="tile_001"))

        tile = shell.build_foundup_tile("tile_001")
        assert tile is not None
        assert tile.health_status == "unknown"
        assert tile.state_provider == "none"

    def test_build_tile_with_provider(self):
        """Tile built with provider merges overlay."""
        overlay = FoundUpStateOverlay(
            foundup_id="tile_001",
            health_status="healthy",
            cabr_score=0.8,
            state_provider="mock",
        )
        provider = MockStateProvider(overlays={"tile_001": overlay})

        shell = create_pfmall_shell(state_provider=provider)
        shell.register_manifest(_make_manifest(foundup_id="tile_001"))

        tile = shell.build_foundup_tile("tile_001")
        assert tile.health_status == "healthy"
        assert tile.cabr_score == 0.8
        assert tile.state_provider == "mock"

    def test_build_tile_unknown_id(self):
        """Tile for unknown ID returns None."""
        shell = create_pfmall_shell()
        assert shell.build_foundup_tile("nonexistent") is None

    def test_build_tile_provider_fails(self):
        """Tile degrades gracefully when provider fails."""
        shell = create_pfmall_shell(state_provider=FailingProvider())
        shell.register_manifest(_make_manifest(foundup_id="tile_001"))

        tile = shell.build_foundup_tile("tile_001")
        assert tile is not None
        assert tile.health_status == "unknown"
        assert tile.state_provider == "none"

    def test_configure_state_provider(self):
        """Provider can be configured after creation."""
        shell = create_pfmall_shell()
        shell.register_manifest(_make_manifest(foundup_id="tile_001"))

        # No provider initially
        tile = shell.build_foundup_tile("tile_001")
        assert tile.state_provider == "none"

        # Configure provider
        overlay = FoundUpStateOverlay(
            foundup_id="tile_001",
            health_status="degraded",
            state_provider="mock",
        )
        shell.configure_state_provider(MockStateProvider(overlays={"tile_001": overlay}))

        tile = shell.build_foundup_tile("tile_001")
        assert tile.health_status == "degraded"
        assert tile.state_provider == "mock"

    def test_boot_discovers_manifests(self, tmp_path):
        """Boot triggers manifest discovery."""
        (tmp_path / "fu1").mkdir()
        (tmp_path / "fu1" / "foundup_manifest.json").write_text(
            json.dumps(_valid_manifest_data(foundup_id="fu1_001", name="FU1")),
            encoding="utf-8",
        )

        shell = create_pfmall_shell(search_paths=[tmp_path])
        assert shell.catalog.count == 0

        shell.boot()
        assert shell.is_booted is True
        assert shell.catalog.count == 1
        assert shell.catalog.get("fu1_001") is not None

    def test_boot_idempotent(self, tmp_path):
        """Boot only runs once."""
        (tmp_path / "fu1").mkdir()
        (tmp_path / "fu1" / "foundup_manifest.json").write_text(
            json.dumps(_valid_manifest_data(foundup_id="fu1_001", name="FU1")),
            encoding="utf-8",
        )

        shell = create_pfmall_shell(search_paths=[tmp_path])
        shell.boot()
        shell.boot()  # Second boot is no-op
        assert shell.catalog.count == 1

    def test_discover_and_route_integration(self, tmp_path):
        """End-to-end: discover manifests, then resolve route."""
        (tmp_path / "gotjunk").mkdir()
        (tmp_path / "gotjunk" / "foundup_manifest.json").write_text(
            json.dumps(_valid_manifest_data(
                foundup_id="gotjunk_001",
                name="GotJunk",
                routing_prefix="/f/gotjunk_001",
            )),
            encoding="utf-8",
        )

        shell = create_pfmall_shell(search_paths=[tmp_path])
        shell.boot()

        # Route resolves
        target = shell.resolve_route("/f/gotjunk_001/listings")
        assert target.kind == RouteKind.FOUNDUP
        assert target.foundup_id == "gotjunk_001"
        assert target.foundup_path == "/listings"

        # Unknown route fails cleanly
        target = shell.resolve_route("/f/nonexistent")
        assert target.kind == RouteKind.NOT_FOUND


# ---------------------------------------------------------------------------
# Real Repo Manifest Discovery (pfmall_manifest_seed_phase1)
# ---------------------------------------------------------------------------

class TestRealManifestDiscovery:
    """Integration tests against real seeded manifests in the repo.

    These tests verify that the p.fMALL shell can discover and load
    the Phase 1 manifest cohort from actual repo paths.
    """

    REPO_ROOT = Path("O:/Foundups-Agent")
    SEARCH_PATHS = [
        REPO_ROOT / "modules" / "foundups",
        REPO_ROOT / "modules" / "gamification",
        REPO_ROOT / "modules" / "platform_integration",
    ]

    EXPECTED_IDS = {"gotjunk_001", "magadoom_001", "antifafm_001"}

    @pytest.fixture
    def shell(self):
        """Create shell with real repo search paths."""
        return create_pfmall_shell(search_paths=self.SEARCH_PATHS)

    def test_discover_finds_seeded_manifests(self, shell):
        """Shell discovers all Phase 1 manifests from real repo paths."""
        manifests = shell.discover_foundups()
        discovered_ids = {m.foundup_id for m in manifests}
        assert self.EXPECTED_IDS.issubset(discovered_ids), (
            f"Missing: {self.EXPECTED_IDS - discovered_ids}"
        )

    def test_manifests_validate_against_schema(self, shell):
        """All seeded manifests pass schema validation."""
        shell.boot()
        for fid in self.EXPECTED_IDS:
            manifest = shell.catalog.get(fid)
            assert manifest is not None, f"{fid} not in catalog"
            assert manifest.name, f"{fid} has no name"
            assert manifest.tier in {"F0_DAE", "F1_OPO", "F2_GROWTH", "F3_INFRA", "F4_MEGA", "F5_SYSTEMIC"}
            assert manifest.category in {"marketplace", "media", "games", "community", "science"}

    def test_catalog_not_empty(self, shell):
        """Shell catalog is no longer empty after boot."""
        shell.boot()
        assert shell.catalog.count >= 3

    def test_gotjunk_manifest(self, shell):
        """GotJunk manifest has correct fields."""
        shell.boot()
        m = shell.catalog.get("gotjunk_001")
        assert m is not None
        assert m.name == "GotJunk"
        assert m.category == "marketplace"
        assert m.tier == "F0_DAE"
        assert m.lifecycle_stage == "proto"
        assert m.token_symbol == "JUNK"
        assert m.is_invite_only is True

    def test_magadoom_manifest(self, shell):
        """MAGADOOM manifest has correct fields."""
        shell.boot()
        m = shell.catalog.get("magadoom_001")
        assert m is not None
        assert m.name == "MAGADOOM"
        assert m.category == "games"
        assert m.token_symbol == "DOOM"

    def test_antifafm_manifest(self, shell):
        """antifaFM manifest has correct fields."""
        shell.boot()
        m = shell.catalog.get("antifafm_001")
        assert m is not None
        assert m.name == "antifaFM"
        assert m.category == "media"
        assert m.token_symbol == "ANTI"
        assert m.required_subscription_tier == "starter"

    def test_route_resolution_for_seeded_foundup(self, shell):
        """Route resolves for a real seeded FoundUp."""
        shell.boot()
        target = shell.resolve_route("/f/gotjunk_001/listings")
        assert target.kind == RouteKind.FOUNDUP
        assert target.foundup_id == "gotjunk_001"
        assert target.foundup_path == "/listings"

    def test_tile_build_for_seeded_foundup(self, shell):
        """Tile can be built for a seeded FoundUp (no provider)."""
        shell.boot()
        tile = shell.build_foundup_tile("gotjunk_001")
        assert tile is not None
        assert tile.name == "GotJunk"
        assert tile.health_status == "unknown"  # No provider
        assert tile.state_provider == "none"
