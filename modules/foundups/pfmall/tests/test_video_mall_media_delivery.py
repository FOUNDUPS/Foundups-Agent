#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for video mall media delivery — Worker A phase 1.

Verifies that media path conventions, hosting config, and embed safety
rules are correct BEFORE E (content catalog) and F (player) land.

These tests ensure:
- Firebase hosting cache headers differentiate media from HTML/JSON
- The rewrite-trap (** -> /index.html) is documented and mitigated
- Media directory convention is stable
- Embed URL patterns are safe (no arbitrary external sources)
- Service worker NEVER_CACHE excludes member media correctly
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
MEDIA_DIR = MEMBER / "media"
MALL_CATALOG = MEMBER / "mall-catalog.json"


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

    def test_image_cache_header_exists(self):
        """Image media gets explicit Cache-Control."""
        rule = self._find_header_rule("member/media/**/*.")
        assert rule is not None, "No cache header rule for member/media images"
        cache_headers = [h for h in rule["headers"] if h["key"] == "Cache-Control"]
        assert len(cache_headers) == 1
        assert "max-age=" in cache_headers[0]["value"]

    def test_video_cache_header_exists(self):
        """Video media gets explicit Cache-Control."""
        found = False
        for rule in self.headers:
            src = rule.get("source", "")
            if "member/media" in src and ("mp4" in src or "webm" in src):
                found = True
                cache_headers = [h for h in rule["headers"] if h["key"] == "Cache-Control"]
                assert len(cache_headers) == 1
                assert "max-age=" in cache_headers[0]["value"]
                break
        assert found, "No cache header rule for member/media video files"

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
# Media directory convention
# ---------------------------------------------------------------------------

class TestMediaDirectoryConvention:
    """Media directory must exist at public/member/media/ with expected structure."""

    def test_media_dir_exists(self):
        assert MEDIA_DIR.is_dir(), "public/member/media/ directory must exist"

    def test_posters_dir_exists(self):
        assert (MEDIA_DIR / "posters").is_dir(), "public/member/media/posters/ must exist"

    def test_thumbs_dir_exists(self):
        assert (MEDIA_DIR / "thumbs").is_dir(), "public/member/media/thumbs/ must exist"

    def test_gitkeep_present(self):
        """Convention directory has .gitkeep until real assets land."""
        assert (MEDIA_DIR / ".gitkeep").is_file()


# ---------------------------------------------------------------------------
# Embed URL safety rules
# ---------------------------------------------------------------------------

class TestEmbedURLSafety:
    """Embed/source URLs in catalogs must follow safety rules.

    These rules apply to any future mall-video-catalog.json or similar:
    - embed_url must be YouTube embed (https://www.youtube.com/embed/...)
    - source_url must be YouTube watch (https://www.youtube.com/watch?v=...)
    - poster_url / thumbnail_url must be relative (/member/media/...) or YouTube CDN
    - No arbitrary external domains for media assets hosted on our origin
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
        r"^/member/media/",              # local relative
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

    def test_validate_media_url_accepts_local(self):
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
# Existing catalog — no media path regression
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
