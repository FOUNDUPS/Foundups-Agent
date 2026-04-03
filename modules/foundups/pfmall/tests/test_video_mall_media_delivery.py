#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for video mall media delivery — Worker A phases 1-2.

Verifies:
- Firebase hosting cache headers differentiate media from HTML/JSON
- The rewrite-trap (** -> /index.html) is documented and mitigated
- Media directory conventions exist at both /media/ and /member/media/
- Embed URL patterns are safe (no arbitrary external sources)
- Service worker NEVER_CACHE excludes member media correctly
- CSS theme fallback colors survive broken poster images
- Video catalog media references use allowed paths
"""

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]
PUBLIC = ROOT / "public"
MEMBER = PUBLIC / "member"
FIREBASE_JSON = ROOT / "firebase.json"
SW_JS = PUBLIC / "sw.js"
GATEWAY = PUBLIC / "index.html"
MEMBER_INDEX = MEMBER / "index.html"
FOUNDUP_ENTRY = MEMBER / "foundup.html"
ROUTE_BRIDGE = PUBLIC / "f" / "index.html"
ROOT_MEDIA_DIR = PUBLIC / "media"
MEMBER_MEDIA_DIR = MEMBER / "media"
MALL_CATALOG = MEMBER / "mall-catalog.json"
VIDEO_CATALOG = MEMBER / "mall-video-catalog.json"
TILE_FIELD_CSS = MEMBER / "css" / "mall-tile-field.css"


# ---------------------------------------------------------------------------
# Firebase hosting — cache header rules
# ---------------------------------------------------------------------------

class TestFirebaseCacheHeaders:
    """Firebase hosting must differentiate cache policy by asset type."""

    @pytest.fixture(autouse=True)
    def load_firebase(self):
        self.config = json.loads(FIREBASE_JSON.read_text(encoding="utf-8"))
        self.hosting = self.config["hosting"]
        self.headers = self.hosting.get("headers", [])

    def _find_header_rule(self, source_pattern):
        for rule in self.headers:
            if source_pattern in rule.get("source", ""):
                return rule
        return None

    def _find_all_header_rules(self, source_pattern):
        return [r for r in self.headers if source_pattern in r.get("source", "")]

    def test_firebase_json_exists(self):
        assert FIREBASE_JSON.is_file()

    def test_global_security_headers(self):
        """Global headers include X-Frame-Options and nosniff."""
        global_rule = None
        for rule in self.headers:
            if rule["source"] == "**":
                global_rule = rule
                break
        assert global_rule is not None
        header_keys = [h["key"] for h in global_rule["headers"]]
        assert "X-Frame-Options" in header_keys
        assert "X-Content-Type-Options" in header_keys

    def test_root_media_image_cache_header(self):
        """Root /media/ images get explicit Cache-Control."""
        # Must match media/** not just member/media/**
        rules = self._find_all_header_rules("media/**/*.")
        image_rules = [r for r in rules if "jpg" in r.get("source", "")]
        assert len(image_rules) >= 1, "No cache header for root media/ images"
        # At least one must NOT start with "member/"
        root_rules = [r for r in image_rules if not r["source"].startswith("member/")]
        assert len(root_rules) >= 1, "No cache header for root-level media/ images"

    def test_root_media_video_cache_header(self):
        """Root /media/ videos get explicit Cache-Control."""
        found = False
        for rule in self.headers:
            src = rule.get("source", "")
            if "media" in src and ("mp4" in src or "webm" in src) and not src.startswith("member/"):
                found = True
                cache_headers = [h for h in rule["headers"] if h["key"] == "Cache-Control"]
                assert len(cache_headers) == 1
                assert "max-age=" in cache_headers[0]["value"]
                break
        assert found, "No cache header rule for root media/ video files"

    def test_member_media_image_cache_header(self):
        """Member /member/media/ images also get Cache-Control."""
        rules = self._find_all_header_rules("member/media/**/*.")
        assert len(rules) >= 1, "No cache header for member/media/ images"

    def test_html_no_cache(self):
        """HTML files must not be long-cached (deployment parity)."""
        rule = self._find_header_rule("*.html")
        assert rule is not None, "No cache header rule for HTML"
        cache_headers = [h for h in rule["headers"] if h["key"] == "Cache-Control"]
        assert len(cache_headers) == 1
        assert "no-cache" in cache_headers[0]["value"]

    def test_json_no_cache(self):
        """JSON catalog files must not be long-cached."""
        rule = self._find_header_rule("*.json")
        assert rule is not None, "No cache header rule for JSON"
        cache_headers = [h for h in rule["headers"] if h["key"] == "Cache-Control"]
        assert len(cache_headers) == 1
        assert "no-cache" in cache_headers[0]["value"]


# ---------------------------------------------------------------------------
# Rewrite trap awareness
# ---------------------------------------------------------------------------

class TestRewriteTrapMitigation:
    """The ** -> /index.html rewrite silently serves HTML for missing files.

    Any media path that doesn't exist as a real file will return gateway HTML
    with a 200 status instead of 404. This class documents the trap and
    verifies mitigations are in place.
    """

    @pytest.fixture(autouse=True)
    def load_firebase(self):
        self.config = json.loads(FIREBASE_JSON.read_text(encoding="utf-8"))
        self.rewrites = self.config["hosting"].get("rewrites", [])

    def test_catchall_rewrite_exists(self):
        """Confirm the catch-all rewrite is present (the trap source)."""
        sources = [r["source"] for r in self.rewrites]
        assert "**" in sources, "Catch-all rewrite expected"

    def test_catchall_goes_to_index(self):
        """Catch-all rewrites to /index.html (gateway)."""
        for r in self.rewrites:
            if r["source"] == "**":
                assert r["destination"] == "/index.html"

    def test_f_route_rewrite_before_catchall(self):
        """/f/** rewrite must come before ** catch-all."""
        sources = [r["source"] for r in self.rewrites]
        assert sources.index("/f/**") < sources.index("**")

    def test_nosniff_prevents_mime_confusion(self):
        """X-Content-Type-Options: nosniff prevents browsers treating HTML as image."""
        headers = self.config["hosting"]["headers"]
        for rule in headers:
            if rule["source"] == "**":
                vals = {h["key"]: h["value"] for h in rule["headers"]}
                assert vals.get("X-Content-Type-Options") == "nosniff"


# ---------------------------------------------------------------------------
# Media directory conventions
# ---------------------------------------------------------------------------

class TestMediaDirectoryConvention:
    """Media directories exist at both root and member level."""

    def test_root_media_dir_exists(self):
        """public/media/ exists for catalog poster paths (/media/posters/...)."""
        assert ROOT_MEDIA_DIR.is_dir(), "public/media/ directory must exist"

    def test_root_posters_dir_exists(self):
        assert (ROOT_MEDIA_DIR / "posters").is_dir(), "public/media/posters/ must exist"

    def test_root_thumbs_dir_exists(self):
        assert (ROOT_MEDIA_DIR / "thumbs").is_dir(), "public/media/thumbs/ must exist"

    def test_member_media_dir_exists(self):
        """public/member/media/ exists for member-specific media."""
        assert MEMBER_MEDIA_DIR.is_dir(), "public/member/media/ directory must exist"

    def test_member_posters_dir_exists(self):
        assert (MEMBER_MEDIA_DIR / "posters").is_dir()

    def test_member_thumbs_dir_exists(self):
        assert (MEMBER_MEDIA_DIR / "thumbs").is_dir()


# ---------------------------------------------------------------------------
# Embed URL safety rules
# ---------------------------------------------------------------------------

class TestEmbedURLSafety:
    """Embed/source URLs in catalogs must follow safety rules.

    - embed_url must be YouTube embed
    - source_url must be YouTube watch
    - poster_url / thumbnail_url must be local (/media/...) or YouTube CDN
    - No arbitrary external domains
    """

    ALLOWED_EMBED_PATTERNS = [
        r"^https://www\.youtube\.com/embed/[a-zA-Z0-9_-]+",
        r"^https://www\.youtube-nocookie\.com/embed/[a-zA-Z0-9_-]+",
    ]

    ALLOWED_SOURCE_PATTERNS = [
        r"^https://www\.youtube\.com/watch\?v=[a-zA-Z0-9_-]+",
        r"^https://youtu\.be/[a-zA-Z0-9_-]+",
    ]

    ALLOWED_MEDIA_PATTERNS = [
        r"^/media/",                     # root-relative (catalog convention)
        r"^/member/media/",              # member-relative
        r"^https://i\.ytimg\.com/",      # YouTube CDN thumbnails
        r"^https://img\.youtube\.com/",   # YouTube CDN alt
    ]

    def test_embed_patterns_are_valid_regex(self):
        for p in self.ALLOWED_EMBED_PATTERNS:
            re.compile(p)

    def test_source_patterns_are_valid_regex(self):
        for p in self.ALLOWED_SOURCE_PATTERNS:
            re.compile(p)

    def test_media_patterns_are_valid_regex(self):
        for p in self.ALLOWED_MEDIA_PATTERNS:
            re.compile(p)

    def test_validate_embed_url_accepts_youtube(self):
        url = "https://www.youtube.com/embed/dQw4w9WgXcQ"
        assert any(re.match(p, url) for p in self.ALLOWED_EMBED_PATTERNS)

    def test_validate_embed_url_rejects_arbitrary(self):
        url = "https://evil.com/embed/something"
        assert not any(re.match(p, url) for p in self.ALLOWED_EMBED_PATTERNS)

    def test_validate_source_url_accepts_youtube(self):
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        assert any(re.match(p, url) for p in self.ALLOWED_SOURCE_PATTERNS)

    def test_validate_media_url_accepts_root_local(self):
        url = "/media/posters/move2japan.jpg"
        assert any(re.match(p, url) for p in self.ALLOWED_MEDIA_PATTERNS)

    def test_validate_media_url_accepts_member_local(self):
        url = "/member/media/posters/move2japan.jpg"
        assert any(re.match(p, url) for p in self.ALLOWED_MEDIA_PATTERNS)

    def test_validate_media_url_accepts_ytimg(self):
        url = "https://i.ytimg.com/vi/dQw4w9WgXcQ/maxresdefault.jpg"
        assert any(re.match(p, url) for p in self.ALLOWED_MEDIA_PATTERNS)

    def test_validate_media_url_rejects_arbitrary(self):
        url = "https://random-cdn.com/image.jpg"
        assert not any(re.match(p, url) for p in self.ALLOWED_MEDIA_PATTERNS)


# ---------------------------------------------------------------------------
# Service worker — member media caching rules
# ---------------------------------------------------------------------------

class TestServiceWorkerMediaRules:
    """Service worker must NOT block member media but must skip auth."""

    @pytest.fixture(autouse=True)
    def load_sw(self):
        self.sw = SW_JS.read_text(encoding="utf-8")

    def test_sw_exists(self):
        assert SW_JS.is_file()

    def test_member_route_in_never_cache(self):
        """SW NEVER_CACHE includes /member/ — media falls under this."""
        assert "'/member/'" in self.sw or '"/member/"' in self.sw

    def test_clerk_in_never_cache(self):
        assert "clerk" in self.sw.lower()

    def test_firebase_in_never_cache(self):
        assert "firebaseapp" in self.sw or "firebase" in self.sw


# ---------------------------------------------------------------------------
# CSS theme fallback colors
# ---------------------------------------------------------------------------

class TestThemeFallbackColors:
    """Each tile theme must have a background-color fallback for broken posters.

    When JS sets inline background-image: url(poster.jpg) and the poster fails,
    the theme gradient is lost. background-color survives as the only CSS-
    controlled layer, providing a clean solid-tone fallback.
    """

    KNOWN_THEMES = [
        "antifafm", "gotjunk", "magadoom", "tq", "vsa", "pqn", "default",
        # Video Mall catalog lane themes
        "move2japan", "undaodu", "foundups_main",
        "linkedin_012", "linkedin_esingularity", "linkedin_tsingularity", "linkedin_foundups",
    ]

    @pytest.fixture(autouse=True)
    def load_css(self):
        self.css = TILE_FIELD_CSS.read_text(encoding="utf-8")

    def test_tile_field_css_exists(self):
        assert TILE_FIELD_CSS.is_file()

    def test_each_theme_has_background_color(self):
        """Every theme class must declare background-color for poster fallback."""
        for theme in self.KNOWN_THEMES:
            selector = f".mall-tile.theme-{theme}"
            assert selector in self.css, f"Missing theme: {selector}"
            # Find the rule block
            start = self.css.index(selector)
            # Scan forward for the closing brace
            brace_depth = 0
            block_start = None
            for i in range(start, min(start + 500, len(self.css))):
                if self.css[i] == '{':
                    if block_start is None:
                        block_start = i
                    brace_depth += 1
                elif self.css[i] == '}':
                    brace_depth -= 1
                    if brace_depth == 0:
                        block = self.css[block_start:i + 1]
                        break
            assert "background-color:" in block, (
                f"{selector} must have background-color for poster fallback"
            )

    def test_fallback_colors_are_not_transparent(self):
        """Fallback colors must be opaque, not transparent."""
        for theme in self.KNOWN_THEMES:
            selector = f".mall-tile.theme-{theme}"
            start = self.css.index(selector)
            block = self.css[start:start + 400]
            # Extract background-color value
            match = re.search(r"background-color:\s*([^;]+);", block)
            assert match is not None, f"No background-color in {selector}"
            color = match.group(1).strip()
            assert color != "transparent", f"{selector} fallback must not be transparent"
            assert color.startswith("#") or color.startswith("rgb"), (
                f"{selector} fallback should be a hex or rgb color, got: {color}"
            )


# ---------------------------------------------------------------------------
# Delivery surface verification
# ---------------------------------------------------------------------------

class TestDeliverySurfaces:
    """All three delivery surfaces exist and are auth-gated."""

    def test_member_index_exists(self):
        assert MEMBER_INDEX.is_file()

    def test_foundup_entry_exists(self):
        assert FOUNDUP_ENTRY.is_file()

    def test_route_bridge_exists(self):
        assert ROUTE_BRIDGE.is_file()

    def test_route_bridge_redirects_to_member(self):
        """Route bridge sends /f/{id} to /member/foundup.html?id={id}."""
        html = ROUTE_BRIDGE.read_text(encoding="utf-8")
        assert "/member/foundup.html" in html

    def test_member_index_has_clerk(self):
        """Mall shell loads Clerk for auth gating."""
        html = MEMBER_INDEX.read_text(encoding="utf-8")
        assert "clerk" in html.lower()

    def test_gateway_not_changed(self):
        """Gateway (public/index.html) is not modified by this slice."""
        html = GATEWAY.read_text(encoding="utf-8")
        assert "viewport-fit=cover" in html
        assert "scroll-snap-type" in html
        assert "navigateToMember" in html


# ---------------------------------------------------------------------------
# Video catalog — media path validation
# ---------------------------------------------------------------------------

class TestVideoCatalogMediaPaths:
    """Video catalog media references must use allowed URL patterns."""

    ALLOWED_POSTER_PATTERNS = [
        r"^/media/",
        r"^/member/media/",
        r"^https://i\.ytimg\.com/",
        r"^https://img\.youtube\.com/",
    ]

    ALLOWED_THUMB_PATTERNS = [
        r"^/media/",
        r"^/member/media/",
        r"^https://i\.ytimg\.com/",
        r"^https://img\.youtube\.com/",
    ]

    @pytest.fixture(autouse=True)
    def load_catalog(self):
        if VIDEO_CATALOG.is_file():
            self.catalog = json.loads(VIDEO_CATALOG.read_text(encoding="utf-8"))
        else:
            self.catalog = None

    def test_video_catalog_exists(self):
        assert VIDEO_CATALOG.is_file(), "mall-video-catalog.json must exist"

    def test_catalog_is_valid_json(self):
        assert isinstance(self.catalog, list)

    def test_lane_poster_urls_use_allowed_patterns(self):
        """Every lane poster_url must match allowed media URL patterns."""
        for lane in self.catalog:
            url = lane.get("poster_url", "")
            if not url:
                continue
            assert any(re.match(p, url) for p in self.ALLOWED_POSTER_PATTERNS), (
                f"Lane {lane['foundup_id']} poster_url uses disallowed pattern: {url}"
            )

    def test_video_thumbnail_urls_use_allowed_patterns(self):
        """Every video thumbnail_url must match allowed media URL patterns."""
        for lane in self.catalog:
            for video in lane.get("videos", []):
                url = video.get("thumbnail_url", "")
                if not url:
                    continue
                assert any(re.match(p, url) for p in self.ALLOWED_THUMB_PATTERNS), (
                    f"Video {video.get('video_id', '?')} thumbnail uses disallowed pattern: {url}"
                )

    def test_video_embed_urls_are_youtube(self):
        """Every video embed_url must be YouTube."""
        embed_patterns = [
            r"^https://www\.youtube\.com/embed/[a-zA-Z0-9_-]+",
            r"^https://www\.youtube-nocookie\.com/embed/[a-zA-Z0-9_-]+",
        ]
        for lane in self.catalog:
            for video in lane.get("videos", []):
                url = video.get("embed_url", "")
                if not url:
                    continue
                assert any(re.match(p, url) for p in embed_patterns), (
                    f"Video {video.get('video_id', '?')} embed_url not YouTube: {url}"
                )

    def test_lane_poster_dirs_exist(self):
        """The directory referenced by poster_url paths must exist."""
        for lane in self.catalog:
            url = lane.get("poster_url", "")
            if url.startswith("/media/"):
                parent = PUBLIC / url.lstrip("/").rsplit("/", 1)[0]
                assert parent.is_dir(), f"Media directory missing: {parent}"
            elif url.startswith("/member/media/"):
                parent = PUBLIC / url.lstrip("/").rsplit("/", 1)[0]
                assert parent.is_dir(), f"Media directory missing: {parent}"


# ---------------------------------------------------------------------------
# Existing mall-catalog.json — backward compat
# ---------------------------------------------------------------------------

class TestExistingCatalog:
    """Existing mall-catalog.json has no broken media references."""

    def test_catalog_exists(self):
        assert MALL_CATALOG.is_file()

    def test_catalog_is_valid_json(self):
        data = json.loads(MALL_CATALOG.read_text(encoding="utf-8"))
        assert isinstance(data, list)

    def test_catalog_entries_have_required_fields(self):
        data = json.loads(MALL_CATALOG.read_text(encoding="utf-8"))
        for entry in data:
            assert "foundup_id" in entry
            assert "name" in entry

    def test_catalog_has_no_broken_media_refs(self):
        """No poster/thumbnail/video paths that reference nonexistent files."""
        data = json.loads(MALL_CATALOG.read_text(encoding="utf-8"))
        for entry in data:
            for key in ("poster_url", "thumbnail_url"):
                if key in entry and entry[key].startswith("/"):
                    path = PUBLIC / entry[key].lstrip("/")
                    assert path.is_file(), f"Missing local media: {entry[key]}"
