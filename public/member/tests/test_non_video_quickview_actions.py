"""Tests for non-video quickview/overlay action surfaces on Mall index.

Verifies that non-video FoundUps (github_repo, external_app, internal_service)
get truthful CTAs and metadata in the Mall quick-view and overlay surfaces,
while video-backed entries retain their existing semantics.

WSP Compliance:
  WSP 5  : Test coverage for new surfaces
  WSP 72 : Scoped to index.html + mall-planes.js (no tile-field)
"""

import json
import re

import pytest

# ── Paths ──
MALL_PLANES_JS = "public/member/js/mall-planes.js"
INDEX_HTML = "public/member/index.html"
CATALOG_JSON = "public/member/mall-video-catalog.json"


@pytest.fixture(scope="module")
def mall_planes_js():
    with open(MALL_PLANES_JS, encoding="utf-8") as f:
        return f.read()


@pytest.fixture(scope="module")
def index_html():
    with open(INDEX_HTML, encoding="utf-8") as f:
        return f.read()


@pytest.fixture(scope="module")
def catalog():
    with open(CATALOG_JSON, encoding="utf-8") as f:
        data = json.load(f)
    # Flatten lanes into entries
    entries = []
    for lane in data:
        if isinstance(lane, dict) and "entries" in lane:
            entries.extend(lane["entries"])
        elif isinstance(lane, dict) and "foundup_id" in lane:
            entries.append(lane)
    return entries


# ═══════════════════════════════════════════════
# 1. Quick-view (mall-planes.js) source-type config
# ═══════════════════════════════════════════════

class TestQuickViewSourceTypeConfig:
    """SOURCE_TYPE_CTA and NON_VIDEO_SOURCE_TYPES in mall-planes.js."""

    def test_source_type_cta_defined(self, mall_planes_js):
        assert "SOURCE_TYPE_CTA" in mall_planes_js

    def test_github_repo_label(self, mall_planes_js):
        assert "'View Repo'" in mall_planes_js or '"View Repo"' in mall_planes_js

    def test_external_app_label(self, mall_planes_js):
        assert "'Open App'" in mall_planes_js or '"Open App"' in mall_planes_js

    def test_internal_service_label(self, mall_planes_js):
        assert "'Open Service'" in mall_planes_js or '"Open Service"' in mall_planes_js

    def test_non_video_source_types_defined(self, mall_planes_js):
        assert "NON_VIDEO_SOURCE_TYPES" in mall_planes_js

    def test_non_video_types_include_all_three(self, mall_planes_js):
        for st in ["github_repo", "external_app", "internal_service"]:
            assert st in mall_planes_js


# ═══════════════════════════════════════════════
# 2. Quick-view renders source-type CTA
# ═══════════════════════════════════════════════

class TestQuickViewCTARendering:
    """renderView() in mall-planes.js uses source-type-aware CTAs."""

    def test_renders_fv_source_cta_class(self, mall_planes_js):
        assert "fv-source-cta" in mall_planes_js

    def test_renders_source_type_label(self, mall_planes_js):
        assert "fv-source-type-label" in mall_planes_js

    def test_non_video_suppresses_video_hint(self, mall_planes_js):
        """Non-video entries must not get 'N videos' hint."""
        assert "isNonVideo" in mall_planes_js
        # videoHint is conditional on !isNonVideo
        assert "!isNonVideo" in mall_planes_js

    def test_cta_uses_target_blank(self, mall_planes_js):
        assert 'target="_blank"' in mall_planes_js or "target=\\'_blank\\'" in mall_planes_js


# ═══════════════════════════════════════════════
# 3. Overlay (index.html) source-type config
# ═══════════════════════════════════════════════

class TestOverlaySourceTypeConfig:
    """OVERLAY_SOURCE_TYPE_CTA and OVERLAY_NON_VIDEO_TYPES in index.html."""

    def test_overlay_source_type_cta_defined(self, index_html):
        assert "OVERLAY_SOURCE_TYPE_CTA" in index_html

    def test_overlay_non_video_types_defined(self, index_html):
        assert "OVERLAY_NON_VIDEO_TYPES" in index_html

    def test_overlay_github_repo_label(self, index_html):
        assert "View Repo" in index_html

    def test_overlay_external_app_label(self, index_html):
        assert "Open App" in index_html

    def test_overlay_internal_service_label(self, index_html):
        assert "Open Service" in index_html


# ═══════════════════════════════════════════════
# 4. Overlay renders source-type CTA
# ═══════════════════════════════════════════════

class TestOverlayCTARendering:
    """openFoundupOverlay() renders source-type-aware CTAs."""

    def test_overlay_renders_source_type_class(self, index_html):
        assert "foundup-overlay-source-type" in index_html

    def test_overlay_renders_source_cta_class(self, index_html):
        assert "foundup-overlay-source-cta" in index_html

    def test_overlay_non_video_description_no_video_count(self, index_html):
        """Non-video overlay description must not use video_count."""
        assert "isNonVideo" in index_html


# ═══════════════════════════════════════════════
# 5. Video entries unchanged
# ═══════════════════════════════════════════════

class TestVideoEntriesUnchanged:
    """Video-backed entries retain existing semantics."""

    def test_video_hint_still_present_for_video(self, mall_planes_js):
        """Video entries still get 'N videos' hint."""
        assert "video_count" in mall_planes_js

    def test_open_foundup_link_always_present(self, mall_planes_js):
        """All entries still get 'Open FoundUp' link to entry page."""
        assert "Open FoundUp" in mall_planes_js

    def test_overlay_video_count_still_used(self, index_html):
        """Video entries still use video_count in description."""
        assert "video_count" in index_html


# ═══════════════════════════════════════════════
# 6. No fake playback language on non-video items
# ═══════════════════════════════════════════════

class TestNoFakePlayback:
    """Non-video CTA labels must not use playback language."""

    def test_no_play_in_source_cta_labels(self, mall_planes_js):
        """Source CTAs must not contain 'Play' or 'Watch' or 'Stream'."""
        # Extract CTA label strings from SOURCE_TYPE_CTA block
        cta_block_match = re.search(
            r"SOURCE_TYPE_CTA\s*=\s*\{([^}]+)\}", mall_planes_js
        )
        assert cta_block_match, "SOURCE_TYPE_CTA block not found"
        cta_block = cta_block_match.group(1)
        for word in ["Play", "Watch", "Stream"]:
            assert word not in cta_block, f"Found '{word}' in SOURCE_TYPE_CTA labels"

    def test_no_play_in_overlay_cta_labels(self, index_html):
        """Overlay CTAs must not contain 'Play' or 'Watch' or 'Stream'."""
        cta_block_match = re.search(
            r"OVERLAY_SOURCE_TYPE_CTA\s*=\s*\{([^}]+)\}", index_html
        )
        assert cta_block_match, "OVERLAY_SOURCE_TYPE_CTA block not found"
        cta_block = cta_block_match.group(1)
        for word in ["Play", "Watch", "Stream"]:
            assert word not in cta_block, f"Found '{word}' in OVERLAY_SOURCE_TYPE_CTA labels"


# ═══════════════════════════════════════════════
# 7. Catalog truth — non-video entries have external_url
# ═══════════════════════════════════════════════

class TestCatalogNonVideoTruth:
    """Catalog non-video entries have required fields for CTA rendering."""

    def test_science_swarm_is_github_repo(self, catalog):
        entry = next((e for e in catalog if e.get("foundup_id") == "science_swarm"), None)
        assert entry is not None, "science_swarm not in catalog"
        assert entry["source_type"] == "github_repo"
        assert entry.get("external_url"), "science_swarm missing external_url"

    def test_autopost_is_external_app(self, catalog):
        entry = next((e for e in catalog if e.get("foundup_id") == "autopost"), None)
        assert entry is not None, "autopost not in catalog"
        assert entry["source_type"] == "external_app"
        assert entry.get("external_url"), "autopost missing external_url"

    def test_kosei_is_internal_service(self, catalog):
        entry = next((e for e in catalog if e.get("foundup_id") == "kosei"), None)
        assert entry is not None, "kosei not in catalog"
        assert entry["source_type"] == "internal_service"
        assert entry.get("external_url"), "kosei missing external_url"
