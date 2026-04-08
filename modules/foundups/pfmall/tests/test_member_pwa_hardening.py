"""Tests for pfMALL PWA hardening — Worker AM acceptance criteria.

Validates:
- manifest.json presence and required PWA fields
- Service worker shell asset list matches actual files
- Service worker never-cache list covers auth providers
- mall-state-restore.js public API shape
- index.html wiring (manifest link, SW registration, state restore calls)
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

MEMBER_DIR = Path(__file__).parent.parent.parent.parent.parent / "public" / "member"
MANIFEST_PATH = MEMBER_DIR / "manifest.json"
SW_PATH = MEMBER_DIR / "member-sw.js"
STATE_RESTORE_PATH = MEMBER_DIR / "js" / "mall-state-restore.js"
INDEX_PATH = MEMBER_DIR / "index.html"


# ─── Manifest Tests ───


class TestManifestPresence:
    """Test manifest.json exists and has required PWA fields."""

    @pytest.fixture
    def manifest(self) -> dict:
        assert MANIFEST_PATH.exists(), f"Manifest not found at {MANIFEST_PATH}"
        return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    def test_manifest_exists(self):
        assert MANIFEST_PATH.exists()

    def test_required_pwa_fields(self, manifest: dict):
        required = ["name", "short_name", "start_url", "scope", "display", "icons"]
        for field in required:
            assert field in manifest, f"Missing required PWA field: {field}"

    def test_scope_is_member(self, manifest: dict):
        assert manifest["scope"] == "/member/"

    def test_start_url_is_member(self, manifest: dict):
        assert manifest["start_url"] == "/member/"

    def test_display_is_standalone(self, manifest: dict):
        assert manifest["display"] == "standalone"

    def test_has_192_and_512_icons(self, manifest: dict):
        sizes = {icon["sizes"] for icon in manifest["icons"]}
        assert "192x192" in sizes, "Missing 192x192 icon"
        assert "512x512" in sizes, "Missing 512x512 icon"

    def test_theme_color_matches_brand(self, manifest: dict):
        assert manifest.get("theme_color") == "#08080f"


# ─── Service Worker Tests ───


class TestServiceWorker:
    """Test member-sw.js caching strategy and safety."""

    @pytest.fixture
    def sw_source(self) -> str:
        assert SW_PATH.exists(), f"Service worker not found at {SW_PATH}"
        return SW_PATH.read_text(encoding="utf-8")

    def test_sw_exists(self):
        assert SW_PATH.exists()

    def test_shell_assets_array_present(self, sw_source: str):
        assert "SHELL_ASSETS" in sw_source

    def test_shell_assets_include_core_files(self, sw_source: str):
        """Shell assets must include the member entry point and key JS/CSS."""
        expected_patterns = [
            "/member/",
            "manifest.json",
            "member.css",
            "mall-tile-field.css",
            "gesture-engine.js",
            "mall-state-restore.js",
        ]
        for pattern in expected_patterns:
            assert pattern in sw_source, f"Shell asset missing: {pattern}"

    def test_never_cache_covers_auth(self, sw_source: str):
        """Auth providers must NEVER be cached."""
        auth_patterns = ["clerk", "firebaseapp.com", "googleapis.com"]
        for pattern in auth_patterns:
            assert pattern in sw_source, f"Auth pattern missing from NEVER_CACHE: {pattern}"

    def test_catalog_is_network_first(self, sw_source: str):
        """Catalog must use network-first strategy (not cache-first)."""
        assert "mall-video-catalog.json" in sw_source
        # Network-first: the catalog respondWith block calls fetch() first,
        # then falls back to caches.match() in .catch()
        catalog_section_match = re.search(
            r"indexOf\(CATALOG_URL\).*?return;", sw_source, re.DOTALL
        )
        assert catalog_section_match, "Catalog fetch section not found"
        section = catalog_section_match.group()
        fetch_pos = section.find("fetch(event.request)")
        cache_pos = section.find("caches.match(")
        assert fetch_pos >= 0, "fetch() not found in catalog section"
        assert cache_pos >= 0, "caches.match() not found in catalog section"
        assert fetch_pos < cache_pos, "Catalog should be network-first (fetch before cache)"

    def test_shell_assets_reference_real_files(self, sw_source: str):
        """Each JS/CSS in SHELL_ASSETS should have a corresponding file on disk."""
        # Extract paths from SHELL_ASSETS array
        asset_matches = re.findall(r"'(/member/(?:js|css)/[^']+)'", sw_source)
        for asset_path in asset_matches:
            # Convert URL path to filesystem path relative to public/
            rel = asset_path.lstrip("/")
            file_path = MEMBER_DIR.parent / rel
            assert file_path.exists(), f"Shell asset references missing file: {asset_path} -> {file_path}"


# ─── State Restore Tests ───


class TestStateRestore:
    """Test mall-state-restore.js public API surface."""

    @pytest.fixture
    def sr_source(self) -> str:
        assert STATE_RESTORE_PATH.exists(), f"State restore not found at {STATE_RESTORE_PATH}"
        return STATE_RESTORE_PATH.read_text(encoding="utf-8")

    def test_state_restore_exists(self):
        assert STATE_RESTORE_PATH.exists()

    def test_exposes_public_api(self, sr_source: str):
        """Must expose save, restore, clear, bindAutoSave, peek."""
        api_methods = ["save:", "restore:", "clear:", "bindAutoSave:", "peek:"]
        for method in api_methods:
            assert method in sr_source, f"Missing public API method: {method}"

    def test_uses_localstorage(self, sr_source: str):
        assert "localStorage" in sr_source

    def test_does_not_import_mall_tile_field(self, sr_source: str):
        """Must NOT import or require mall-tile-field.js — boundary rule."""
        assert "import" not in sr_source.lower() or "import" not in sr_source.split("window.mallTileField")[0]
        assert "require(" not in sr_source

    def test_reads_via_public_api_only(self, sr_source: str):
        """Must use window.mallTileField public API, not internal state."""
        assert "window.mallTileField" in sr_source
        # Should use getProjection/setProjection, not internal _projection
        assert "getProjection" in sr_source or "setProjection" in sr_source

    def test_scroll_debounce(self, sr_source: str):
        """Scroll save must be debounced to avoid performance issues."""
        assert "SCROLL_DEBOUNCE_MS" in sr_source
        assert "setTimeout" in sr_source

    def test_is_iife(self, sr_source: str):
        """Must be wrapped in an IIFE to avoid global pollution."""
        assert sr_source.strip().startswith("(function(") or sr_source.strip().startswith("/**")
        assert sr_source.strip().endswith("})();") or "})();" in sr_source


# ─── Index.html Wiring Tests ───


class TestIndexWiring:
    """Test that index.html correctly wires manifest, SW, and state restore."""

    @pytest.fixture
    def index_source(self) -> str:
        assert INDEX_PATH.exists(), f"index.html not found at {INDEX_PATH}"
        return INDEX_PATH.read_text(encoding="utf-8")

    def test_manifest_link_present(self, index_source: str):
        assert 'rel="manifest"' in index_source
        assert "manifest.json" in index_source

    def test_sw_registration_present(self, index_source: str):
        assert "serviceWorker" in index_source
        assert "member-sw.js" in index_source

    def test_state_restore_script_loaded(self, index_source: str):
        assert "mall-state-restore.js" in index_source

    def test_state_restore_called_after_initialize(self, index_source: str):
        """mallStateRestore.restore() must appear after mallTileField.initialize()."""
        init_pos = index_source.find("mallTileField.initialize(mallCatalog)")
        restore_pos = index_source.find("mallStateRestore.restore()")
        assert init_pos > 0, "mallTileField.initialize() not found"
        assert restore_pos > 0, "mallStateRestore.restore() not found"
        assert restore_pos > init_pos, "restore() must come after initialize()"

    def test_autosave_bound_after_interactions(self, index_source: str):
        """mallStateRestore.bindAutoSave() must appear after bindMallInteractions()."""
        bind_pos = index_source.find("bindMallInteractions()")
        autosave_pos = index_source.find("mallStateRestore.bindAutoSave()")
        assert bind_pos > 0, "bindMallInteractions() not found"
        assert autosave_pos > 0, "mallStateRestore.bindAutoSave() not found"
        assert autosave_pos > bind_pos, "bindAutoSave() must come after bindMallInteractions()"

    def test_sw_scope_matches_manifest(self, index_source: str):
        """SW registration scope must match manifest scope."""
        assert "scope: '/member/'" in index_source or "scope: \"/member/\"" in index_source
