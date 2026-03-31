#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for p.fMALL API Adapter.

Covers serialization shape, catalog listing, single lookup, route resolution,
overlay enrichment, and graceful degradation without provider.
"""

import pytest
from pathlib import Path
from typing import Any, Dict, List, Optional

from modules.foundups.pfmall.shell_core import (
    FoundUpManifest,
    FoundUpStateOverlay,
    FoundUpTile,
    RouteKind,
    RouteTarget,
    create_pfmall_shell,
    load_manifest,
    build_foundup_tile,
    resolve_route,
)
from modules.foundups.pfmall.api import (
    get_default_shell,
    list_foundups,
    get_foundup,
    resolve_foundup_route,
    reset_default_shell,
    DEFAULT_SEARCH_PATHS,
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
    return load_manifest(_valid_manifest_data(**overrides))


class MockStateProvider:
    """Mock StateOverlayProvider."""

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


@pytest.fixture
def shell():
    """Create a fresh shell (no default shell singleton)."""
    return create_pfmall_shell()


# ---------------------------------------------------------------------------
# Serialization: FoundUpManifest.to_dict()
# ---------------------------------------------------------------------------

class TestManifestSerialization:
    """Tests for FoundUpManifest.to_dict()."""

    def test_manifest_to_dict_shape(self):
        """to_dict returns all expected keys."""
        m = _make_manifest()
        d = m.to_dict()
        expected_keys = {
            "foundup_id", "name", "version", "description", "tagline",
            "icon_url", "tier", "lifecycle_stage", "entry_url",
            "routing_prefix", "required_subscription_tier", "capabilities",
            "agent_routes", "cabr_contract", "owner_id", "token_symbol",
            "data_namespace", "holo_collections", "category", "is_invite_only",
            "launch_readiness", "signature", "created_at", "updated_at",
        }
        assert set(d.keys()) == expected_keys

    def test_manifest_to_dict_values(self):
        """to_dict preserves field values."""
        m = _make_manifest(
            foundup_id="ser_001",
            name="Serialized",
            tier="F0_DAE",
            launch_readiness="conditional",
        )
        d = m.to_dict()
        assert d["foundup_id"] == "ser_001"
        assert d["name"] == "Serialized"
        assert d["tier"] == "F0_DAE"
        assert d["launch_readiness"] == "conditional"

    def test_manifest_to_dict_lists_are_copies(self):
        """to_dict returns copies of list fields, not references."""
        m = _make_manifest(capabilities=["search", "offline"])
        d = m.to_dict()
        d["capabilities"].append("mutated")
        assert "mutated" not in m.capabilities


# ---------------------------------------------------------------------------
# Serialization: FoundUpTile.to_dict()
# ---------------------------------------------------------------------------

class TestTileSerialization:
    """Tests for FoundUpTile.to_dict()."""

    def test_tile_to_dict_shape(self):
        """to_dict returns all expected keys."""
        tile = build_foundup_tile(_make_manifest())
        d = tile.to_dict()
        expected_keys = {
            "foundup_id", "name", "tagline", "description", "category",
            "tier", "lifecycle_stage", "routing_prefix", "token_symbol",
            "is_invite_only", "icon_url", "launch_readiness",
            "health_status", "availability", "cabr_score", "cabr_trend",
            "active_agents", "tasks_in_flight", "reserve_health",
            "state_provider", "freshness_ttl", "last_updated_at",
        }
        assert set(d.keys()) == expected_keys

    def test_tile_to_dict_overlay_defaults(self):
        """Tile without overlay has unknown/zero overlay fields."""
        tile = build_foundup_tile(_make_manifest())
        d = tile.to_dict()
        assert d["health_status"] == "unknown"
        assert d["availability"] == "unknown"
        assert d["cabr_score"] == 0.0
        assert d["state_provider"] == "none"
        assert d["active_agents"] == 0

    def test_tile_to_dict_with_overlay(self):
        """Tile with overlay includes enriched fields."""
        m = _make_manifest()
        overlay = FoundUpStateOverlay(
            foundup_id="test_001",
            health_status="healthy",
            cabr_score=0.82,
            state_provider="mock",
        )
        tile = build_foundup_tile(m, overlay)
        d = tile.to_dict()
        assert d["health_status"] == "healthy"
        assert d["cabr_score"] == 0.82
        assert d["state_provider"] == "mock"


# ---------------------------------------------------------------------------
# Serialization: RouteTarget.to_dict()
# ---------------------------------------------------------------------------

class TestRouteTargetSerialization:
    """Tests for RouteTarget.to_dict()."""

    def test_shell_route_to_dict(self):
        """Shell route serializes kind as string value."""
        t = RouteTarget(kind=RouteKind.SHELL, path="/discover")
        d = t.to_dict()
        assert d["kind"] == "shell"
        assert d["path"] == "/discover"
        assert "foundup_id" not in d
        assert "error" not in d

    def test_foundup_route_to_dict(self):
        """FoundUp route includes foundup_id and foundup_path."""
        t = RouteTarget(
            kind=RouteKind.FOUNDUP,
            path="/f/gj_001/home",
            foundup_id="gj_001",
            foundup_path="/home",
        )
        d = t.to_dict()
        assert d["kind"] == "foundup"
        assert d["foundup_id"] == "gj_001"
        assert d["foundup_path"] == "/home"
        assert "error" not in d

    def test_not_found_route_to_dict(self):
        """Not found route includes error."""
        t = RouteTarget(
            kind=RouteKind.NOT_FOUND,
            path="/unknown",
            error="no matching route",
        )
        d = t.to_dict()
        assert d["kind"] == "not_found"
        assert d["error"] == "no matching route"
        assert "foundup_id" not in d


# ---------------------------------------------------------------------------
# Adapter: list_foundups()
# ---------------------------------------------------------------------------

class TestListFoundups:
    """Tests for list_foundups()."""

    def test_list_all(self, shell):
        """List returns all registered FoundUps as dicts."""
        shell.register_manifest(_make_manifest(foundup_id="alpha_001", name="Alpha"))
        shell.register_manifest(_make_manifest(foundup_id="beta_001", name="Beta"))
        shell.boot()

        result = list_foundups(shell=shell)
        assert len(result) == 2
        assert all(isinstance(r, dict) for r in result)
        names = [r["name"] for r in result]
        assert names == ["Alpha", "Beta"]  # sorted

    def test_list_filtered_by_category(self, shell):
        """Category filter narrows results."""
        shell.register_manifest(_make_manifest(foundup_id="mkt_001", name="M1", category="marketplace"))
        shell.register_manifest(_make_manifest(foundup_id="gam_001", name="G1", category="games"))

        result = list_foundups(category="marketplace", shell=shell)
        assert len(result) == 1
        assert result[0]["category"] == "marketplace"

    def test_list_empty_catalog(self, shell):
        """Empty catalog returns empty list."""
        result = list_foundups(shell=shell)
        assert result == []


# ---------------------------------------------------------------------------
# Adapter: get_foundup()
# ---------------------------------------------------------------------------

class TestGetFoundup:
    """Tests for get_foundup()."""

    def test_known_foundup(self, shell):
        """Known ID returns tile dict."""
        shell.register_manifest(_make_manifest(foundup_id="known_001", name="Known"))
        result = get_foundup("known_001", shell=shell)
        assert result is not None
        assert result["foundup_id"] == "known_001"
        assert result["name"] == "Known"

    def test_missing_foundup(self, shell):
        """Missing ID returns None."""
        result = get_foundup("nonexistent", shell=shell)
        assert result is None

    def test_overlay_enriched(self, shell):
        """Response includes overlay when provider is configured."""
        overlay = FoundUpStateOverlay(
            foundup_id="enrich_001",
            health_status="healthy",
            cabr_score=0.9,
            state_provider="mock",
        )
        provider = MockStateProvider(overlays={"enrich_001": overlay})
        shell.configure_state_provider(provider)
        shell.register_manifest(_make_manifest(foundup_id="enrich_001", name="Enriched"))

        result = get_foundup("enrich_001", shell=shell)
        assert result["health_status"] == "healthy"
        assert result["cabr_score"] == 0.9
        assert result["state_provider"] == "mock"

    def test_no_provider_graceful(self, shell):
        """Without provider, overlay fields default to unknown/zero."""
        shell.register_manifest(_make_manifest(foundup_id="noprov_001"))
        result = get_foundup("noprov_001", shell=shell)
        assert result["health_status"] == "unknown"
        assert result["state_provider"] == "none"
        assert result["cabr_score"] == 0.0


# ---------------------------------------------------------------------------
# Adapter: resolve_foundup_route()
# ---------------------------------------------------------------------------

class TestResolveFoundupRoute:
    """Tests for resolve_foundup_route()."""

    def test_shell_route(self, shell):
        """Shell routes resolve correctly."""
        result = resolve_foundup_route("/discover", shell=shell)
        assert result["kind"] == "shell"
        assert result["path"] == "/discover"

    def test_foundup_route(self, shell):
        """FoundUp routes resolve with ID and sub-path."""
        shell.register_manifest(_make_manifest(foundup_id="rt_001"))
        result = resolve_foundup_route("/f/rt_001/listings", shell=shell)
        assert result["kind"] == "foundup"
        assert result["foundup_id"] == "rt_001"
        assert result["foundup_path"] == "/listings"

    def test_not_found_route(self, shell):
        """Unknown path returns not_found with error."""
        result = resolve_foundup_route("/random/path", shell=shell)
        assert result["kind"] == "not_found"
        assert "error" in result


# ---------------------------------------------------------------------------
# Default Shell (real repo integration)
# ---------------------------------------------------------------------------

class TestDefaultShell:
    """Tests for get_default_shell() with real repo manifests."""

    def setup_method(self):
        reset_default_shell()

    def teardown_method(self):
        reset_default_shell()

    def test_default_shell_boots(self):
        """Default shell boots and discovers manifests."""
        shell = get_default_shell()
        assert shell.is_booted
        assert shell.catalog.count >= 3

    def test_default_shell_singleton(self):
        """Repeated calls return same instance."""
        s1 = get_default_shell()
        s2 = get_default_shell()
        assert s1 is s2

    def test_list_foundups_via_default(self):
        """list_foundups() works with default shell."""
        reset_default_shell()
        result = list_foundups()
        assert len(result) >= 3
        ids = {r["foundup_id"] for r in result}
        assert "gotjunk_001" in ids
        assert "antifafm_001" in ids
        assert "magadoom_001" in ids

    def test_get_foundup_via_default(self):
        """get_foundup() works with default shell."""
        reset_default_shell()
        result = get_foundup("antifafm_001")
        assert result is not None
        assert result["name"] == "antifaFM"
        assert result["launch_readiness"] == "discoverable_only"

    def test_search_paths_point_to_repo(self):
        """DEFAULT_SEARCH_PATHS resolve to real repo directories."""
        for p in DEFAULT_SEARCH_PATHS:
            assert p.is_dir(), f"Search path does not exist: {p}"
