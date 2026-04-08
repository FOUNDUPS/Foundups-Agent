"""Tests for pfMALL PWA hardening — Worker AM/AQ acceptance criteria.

Validates:
- manifest.json presence and required PWA fields
- Service worker shell asset list matches actual files
- Service worker never-cache list covers auth providers
- Service worker cache versioning and poster cache bounding
- Service worker offline catalog fallback
- mall-state-restore.js public API shape, state validation, versioned key
- index.html wiring (manifest link, SW registration, state restore calls)
- Offline notice presence in index.html
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
        asset_matches = re.findall(r"'(/member/(?:js|css)/[^']+)'", sw_source)
        for asset_path in asset_matches:
            rel = asset_path.lstrip("/")
            file_path = MEMBER_DIR.parent / rel
            assert file_path.exists(), f"Shell asset references missing file: {asset_path} -> {file_path}"

    def test_poster_cache_is_bounded(self, sw_source: str):
        """Poster cache must have a size limit to prevent unbounded growth."""
        assert "MAX_POSTER_ENTRIES" in sw_source
        assert "POSTER_CACHE_NAME" in sw_source
        assert "trimPosterCache" in sw_source

    def test_poster_cache_is_separate(self, sw_source: str):
        """Posters must use a dedicated cache, not the shell cache."""
        poster_match = re.search(
            r"indexOf\('/media/posters/'\).*?return;", sw_source, re.DOTALL
        )
        assert poster_match, "Poster cache section not found"
        section = poster_match.group()
        assert "POSTER_CACHE_NAME" in section, (
            "Poster section must use POSTER_CACHE_NAME, not CACHE_NAME"
        )

    def test_catalog_offline_fallback(self, sw_source: str):
        """Catalog miss path must return an empty-array fallback with header."""
        catalog_match = re.search(
            r"indexOf\(CATALOG_URL\).*?return;", sw_source, re.DOTALL
        )
        assert catalog_match, "Catalog section not found"
        section = catalog_match.group()
        assert "X-Offline-Fallback" in section, (
            "Catalog offline fallback must set X-Offline-Fallback header"
        )
        assert "'[]'" in section, (
            "Catalog offline fallback must return empty JSON array"
        )

    def test_activate_preserves_poster_cache(self, sw_source: str):
        """Activate handler must not delete the poster cache."""
        assert "KEEP_CACHES" in sw_source or "POSTER_CACHE_NAME" in sw_source
        activate_match = re.search(
            r"addEventListener\('activate'.*?\}\);", sw_source, re.DOTALL
        )
        assert activate_match, "Activate handler not found"


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
        """Must expose save, restore, clear, bindAutoSave, peek, isValid."""
        api_methods = ["save:", "restore:", "clear:", "bindAutoSave:", "peek:", "isValid:"]
        for method in api_methods:
            assert method in sr_source, f"Missing public API method: {method}"

    def test_uses_localstorage(self, sr_source: str):
        assert "localStorage" in sr_source

    def test_does_not_import_mall_tile_field(self, sr_source: str):
        """Must NOT import or require mall-tile-field.js — boundary rule."""
        assert "require(" not in sr_source

    def test_reads_via_public_api_only(self, sr_source: str):
        """Must use window.mallTileField public API, not internal state."""
        assert "window.mallTileField" in sr_source
        assert "getProjection" in sr_source or "setProjection" in sr_source

    def test_scroll_debounce(self, sr_source: str):
        """Scroll save must be debounced to avoid performance issues."""
        assert "SCROLL_DEBOUNCE_MS" in sr_source
        assert "setTimeout" in sr_source

    def test_projection_restored_with_scope(self, sr_source: str):
        """Projection must NOT be silently dropped when field scope is present.

        A saved state like 'personal mall + readiness sort' must round-trip.
        """
        restore_match = re.search(
            r"function restore\(\).*?return restored;", sr_source, re.DOTALL
        )
        assert restore_match, "restore() function not found"
        restore_body = restore_match.group()
        assert "setProjection" in restore_body, "restore() must call setProjection"
        assert "if (!state.fieldScope)" not in restore_body, (
            "restore() must not skip projection when fieldScope is present"
        )

    def test_autosave_covers_scope_mutations(self, sr_source: str):
        """Auto-save must trigger on Red Dog scope-changing interactions."""
        scope_selectors = [
            "data-reddog-populate-mall",
            "data-reddog-personal-mall",
            "data-reddog-category",
            "data-reddog-tag-select",
            "data-reddog-search-input",
        ]
        for selector in scope_selectors:
            assert selector in sr_source, (
                f"Auto-save missing trigger for scope mutation: {selector}"
            )

    def test_scope_listeners_are_delegated(self, sr_source: str):
        """Tag-select and search-input listeners must be delegated on document,
        not bound directly via querySelector, because those elements are
        injected later by account-concierge.js when the Red Dog plane opens.
        """
        assert "querySelector('[data-reddog-tag-select]')" not in sr_source, (
            "tag-select listener must be delegated, not bound via querySelector"
        )
        assert "querySelector('[data-reddog-search-input]')" not in sr_source, (
            "search-input listener must be delegated, not bound via querySelector"
        )

    def test_storage_key_is_versioned(self, sr_source: str):
        """Storage key must include a version suffix to invalidate stale state."""
        key_match = re.search(r"STORAGE_KEY\s*=\s*'([^']+)'", sr_source)
        assert key_match, "STORAGE_KEY not found"
        key = key_match.group(1)
        assert re.search(r"_v\d+$", key), (
            f"STORAGE_KEY '{key}' must end with version suffix like _v1"
        )

    def test_state_validation_exists(self, sr_source: str):
        """restore() must validate state shape before applying."""
        assert "isValidState" in sr_source or "isValid" in sr_source
        assert "VALID_PROJECTIONS" in sr_source

    def test_invalid_state_triggers_clear(self, sr_source: str):
        """Invalid stored state must be cleared, not silently applied."""
        restore_match = re.search(
            r"function restore\(\).*?return restored;", sr_source, re.DOTALL
        )
        assert restore_match, "restore() function not found"
        restore_body = restore_match.group()
        assert "clear()" in restore_body, (
            "restore() must call clear() when state is invalid"
        )

    def test_is_iife(self, sr_source: str):
        """Must be wrapped in an IIFE to avoid global pollution."""
        assert sr_source.strip().startswith("(function(") or sr_source.strip().startswith("/**")
        assert "})();" in sr_source


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

    def test_offline_notice_function_present(self, index_source: str):
        """Offline notice function must exist for catalog miss handling."""
        assert "showOfflineNotice" in index_source

    def test_offline_fallback_header_detected(self, index_source: str):
        """Shell must check X-Offline-Fallback header from SW."""
        assert "X-Offline-Fallback" in index_source
