#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for p.fMALL Catalog Integration.

Tests catalog listing, status queries, and routing without simulator coupling.
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from modules.communication.moltbot_bridge.src.pfmall_catalog import (
    CatalogEntry,
    FoundUpStateOverlay,
    PfmallCatalogManager,
    handle_list_foundups,
    handle_foundup_catalog,
    handle_foundup_status,
    handle_open_foundup,
    parse_catalog_command,
)


# ---------------------------------------------------------------------------
# CatalogEntry Tests
# ---------------------------------------------------------------------------

class TestCatalogEntry:
    """Tests for CatalogEntry dataclass."""

    def test_catalog_entry_defaults(self):
        """CatalogEntry has sensible defaults."""
        entry = CatalogEntry(foundup_id="test_001", name="Test")
        assert entry.foundup_id == "test_001"
        assert entry.name == "Test"
        assert entry.tier == "F0_DAE"
        assert entry.lifecycle_stage == "incubating"
        assert entry.is_invite_only is True

    def test_catalog_entry_full(self):
        """CatalogEntry accepts all fields."""
        entry = CatalogEntry(
            foundup_id="gotjunk_001",
            name="GotJunk",
            tagline="Sell your stuff",
            category="marketplace",
            tier="F1_OPO",
            lifecycle_stage="proto",
            is_invite_only=False,
            token_symbol="JUNK",
        )
        assert entry.category == "marketplace"
        assert entry.token_symbol == "JUNK"
        assert entry.is_invite_only is False


# ---------------------------------------------------------------------------
# FoundUpStateOverlay Tests
# ---------------------------------------------------------------------------

class TestFoundUpStateOverlay:
    """Tests for FoundUpStateOverlay dataclass."""

    def test_overlay_defaults(self):
        """StateOverlay defaults to unknown status."""
        overlay = FoundUpStateOverlay(foundup_id="test_001")
        assert overlay.health_status == "unknown"
        assert overlay.availability == "unknown"
        assert overlay.cabr_score == 0.0
        assert overlay.state_provider == "none"

    def test_overlay_full(self):
        """StateOverlay accepts all fields."""
        overlay = FoundUpStateOverlay(
            foundup_id="test_001",
            health_status="healthy",
            availability="online",
            cabr_score=0.75,
            cabr_trend="rising",
            state_provider="simulator",
            freshness_ttl=60,
        )
        assert overlay.health_status == "healthy"
        assert overlay.cabr_score == 0.75


# ---------------------------------------------------------------------------
# PfmallCatalogManager Tests
# ---------------------------------------------------------------------------

class TestPfmallCatalogManager:
    """Tests for PfmallCatalogManager."""

    def test_list_foundups_returns_known_foundups(self):
        """Manager returns known FoundUps from registry."""
        manager = PfmallCatalogManager()
        entries = manager.list_foundups()
        assert len(entries) >= 1
        names = [e.name for e in entries]
        assert "GotJunk" in names

    def test_get_foundup_by_name(self):
        """Manager finds FoundUp by name."""
        manager = PfmallCatalogManager()
        entry = manager.get_foundup("GotJunk")
        assert entry is not None
        assert entry.name == "GotJunk"

    def test_get_foundup_by_name_case_insensitive(self):
        """Manager finds FoundUp case-insensitively."""
        manager = PfmallCatalogManager()
        entry = manager.get_foundup("gotjunk")
        assert entry is not None
        assert entry.name == "GotJunk"

    def test_get_foundup_by_id(self):
        """Manager finds FoundUp by ID."""
        manager = PfmallCatalogManager()
        entry = manager.get_foundup("gotjunk_001")
        assert entry is not None
        assert entry.foundup_id == "gotjunk_001"

    def test_get_foundup_not_found(self):
        """Manager returns None for unknown FoundUp."""
        manager = PfmallCatalogManager()
        entry = manager.get_foundup("nonexistent")
        assert entry is None

    def test_get_catalog_all(self):
        """Manager returns all catalog entries."""
        manager = PfmallCatalogManager()
        entries = manager.get_catalog()
        assert len(entries) >= 1

    def test_get_catalog_filtered(self):
        """Manager filters by category."""
        manager = PfmallCatalogManager()
        entries = manager.get_catalog(category="marketplace")
        assert all(e.category == "marketplace" for e in entries)

    def test_get_status_includes_manifest_and_overlay(self):
        """Status includes both manifest and overlay data."""
        manager = PfmallCatalogManager()
        status = manager.get_status("GotJunk")
        assert status is not None
        # Manifest fields
        assert status["name"] == "GotJunk"
        assert status["tier"] == "F0_DAE"
        # Overlay fields (degraded to unknown without provider)
        assert status["health_status"] == "unknown"
        assert status["state_provider"] == "none"

    def test_get_status_not_found(self):
        """Status returns None for unknown FoundUp."""
        manager = PfmallCatalogManager()
        status = manager.get_status("nonexistent")
        assert status is None

    def test_get_open_target(self):
        """Manager returns routing target."""
        manager = PfmallCatalogManager()
        target = manager.get_open_target("GotJunk")
        assert target is not None
        assert "/f/" in target

    def test_get_open_target_not_found(self):
        """Open target returns None for unknown FoundUp."""
        manager = PfmallCatalogManager()
        target = manager.get_open_target("nonexistent")
        assert target is None

    def test_state_overlay_with_provider(self):
        """Manager uses state provider when available."""
        mock_provider = MagicMock()
        mock_provider.get_foundup_state.return_value = FoundUpStateOverlay(
            foundup_id="gotjunk_001",
            health_status="healthy",
            availability="online",
            cabr_score=0.85,
            state_provider="test_provider",
        )

        manager = PfmallCatalogManager(state_provider=mock_provider)
        status = manager.get_status("GotJunk")

        assert status["health_status"] == "healthy"
        assert status["cabr_score"] == 0.85
        assert status["state_provider"] == "test_provider"

    def test_state_overlay_provider_error(self):
        """Manager degrades gracefully on provider error."""
        mock_provider = MagicMock()
        mock_provider.get_foundup_state.side_effect = Exception("Provider down")

        manager = PfmallCatalogManager(state_provider=mock_provider)
        status = manager.get_status("GotJunk")

        assert status["health_status"] == "unknown"
        assert status["state_provider"] == "error"


# ---------------------------------------------------------------------------
# Command Handler Tests
# ---------------------------------------------------------------------------

class TestCommandHandlers:
    """Tests for catalog command handlers."""

    def test_handle_list_foundups(self):
        """List command returns catalog."""
        response = handle_list_foundups()
        assert "p.fMALL Catalog" in response
        assert "GotJunk" in response

    def test_handle_foundup_catalog(self):
        """Catalog command groups by category."""
        response = handle_foundup_catalog()
        assert "p.fMALL Catalog" in response
        assert "Total:" in response

    def test_handle_foundup_catalog_filtered(self):
        """Catalog command filters by category."""
        response = handle_foundup_catalog(category="marketplace")
        assert "GotJunk" in response

    def test_handle_foundup_status(self):
        """Status command returns FoundUp info."""
        response = handle_foundup_status("GotJunk")
        assert "GotJunk" in response
        assert "Health:" in response
        assert "CABR Score:" in response

    def test_handle_foundup_status_not_found(self):
        """Status command handles unknown FoundUp."""
        response = handle_foundup_status("nonexistent")
        assert "not found" in response

    def test_handle_open_foundup(self):
        """Open command returns routing target."""
        response = handle_open_foundup("GotJunk")
        assert "Open GotJunk" in response
        assert "/f/" in response

    def test_handle_open_foundup_not_found(self):
        """Open command handles unknown FoundUp."""
        response = handle_open_foundup("nonexistent")
        assert "not found" in response


# ---------------------------------------------------------------------------
# Command Parser Tests
# ---------------------------------------------------------------------------

class TestCommandParser:
    """Tests for parse_catalog_command."""

    def test_parse_list_foundups(self):
        """Parser recognizes 'list foundups'."""
        response = parse_catalog_command("list foundups")
        assert response is not None
        assert "p.fMALL Catalog" in response

    def test_parse_show_foundups(self):
        """Parser recognizes 'show foundups'."""
        response = parse_catalog_command("show foundups")
        assert response is not None

    def test_parse_foundup_catalog(self):
        """Parser recognizes 'foundup catalog'."""
        response = parse_catalog_command("foundup catalog")
        assert response is not None

    def test_parse_foundup_catalog_with_category(self):
        """Parser recognizes 'foundup catalog marketplace'."""
        response = parse_catalog_command("foundup catalog marketplace")
        assert response is not None

    def test_parse_foundup_status(self):
        """Parser recognizes 'foundup status <name>'."""
        response = parse_catalog_command("foundup status GotJunk")
        assert response is not None
        assert "GotJunk" in response

    def test_parse_open_foundup(self):
        """Parser recognizes 'open <foundup>'."""
        response = parse_catalog_command("open GotJunk")
        assert response is not None
        assert "/f/" in response

    def test_parse_unknown_command(self):
        """Parser returns None for unknown commands."""
        response = parse_catalog_command("do something else")
        assert response is None

    def test_parse_launch_not_handled(self):
        """Parser does not handle launch commands (handled by FAMAdapter)."""
        response = parse_catalog_command("launch foundup test")
        assert response is None


# ---------------------------------------------------------------------------
# Integration Tests
# ---------------------------------------------------------------------------

class TestFamAdapterIntegration:
    """Tests for FAM adapter integration with catalog."""

    def test_fam_intent_routes_to_catalog(self):
        """FAM intent handler routes catalog commands."""
        from modules.communication.moltbot_bridge.src.fam_adapter import (
            handle_fam_intent,
        )

        response = handle_fam_intent("list foundups", sender="test")
        assert "p.fMALL Catalog" in response

    def test_fam_intent_routes_status(self):
        """FAM intent handler routes status commands."""
        from modules.communication.moltbot_bridge.src.fam_adapter import (
            handle_fam_intent,
        )

        response = handle_fam_intent("foundup status GotJunk", sender="test")
        assert "GotJunk" in response
        assert "Health:" in response

    def test_fam_intent_routes_open(self):
        """FAM intent handler routes open commands."""
        from modules.communication.moltbot_bridge.src.fam_adapter import (
            handle_fam_intent,
        )

        response = handle_fam_intent("open GotJunk", sender="test")
        assert "/f/" in response

    def test_fam_intent_help_includes_new_commands(self):
        """FAM help text includes new commands."""
        from modules.communication.moltbot_bridge.src.fam_adapter import (
            handle_fam_intent,
        )

        response = handle_fam_intent("help", sender="test")
        assert "list foundups" in response
        assert "foundup status" in response
