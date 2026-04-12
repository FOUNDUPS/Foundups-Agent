"""
Route Contract Bridge Tests

Tests for the /f/{foundup_id} canonical landing route.
WSP 104: /f/{foundup_id} is the canonical FoundUp landing namespace.

Route behavior:
  - /f/{foundup_id} renders landing content directly (no redirect)
  - Canonical URL stays visible in address bar
  - Subpath support preserved for future /app mount
"""
import json
import os
import pytest

# public/member
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _find_repo_root():
    """Walk up from ROOT to find repo root (contains .git)."""
    current = ROOT
    for _ in range(10):  # safety limit
        if os.path.isdir(os.path.join(current, ".git")):
            return current
        parent = os.path.dirname(current)
        if parent == current:  # reached filesystem root
            break
        current = parent
    # Fallback to computed path (original behavior)
    return os.path.dirname(os.path.dirname(ROOT))


REPO_ROOT = _find_repo_root()


def _firebase_json_exists():
    """Check if firebase.json exists (may not be tracked in repo)."""
    return os.path.isfile(os.path.join(REPO_ROOT, "firebase.json"))


def _read(relpath, base=ROOT):
    with open(os.path.join(base, relpath), encoding="utf-8") as f:
        return f.read()


class TestCanonicalRouteExists:
    """Test that the canonical landing surface exists."""

    def test_landing_html_exists(self):
        """Canonical landing HTML file exists at public/f/index.html."""
        landing_path = os.path.join(REPO_ROOT, "public", "f", "index.html")
        assert os.path.isfile(landing_path), "public/f/index.html must exist"

    def test_landing_has_route_parsing(self):
        """Landing parses foundup_id from path."""
        landing = _read("../f/index.html")
        assert "/f/" in landing
        assert "foundup_id" in landing.lower() or "foundupId" in landing

    def test_landing_fetches_catalog(self):
        """Landing fetches catalog to resolve FoundUp."""
        landing = _read("../f/index.html")
        assert "mall-video-catalog.json" in landing
        assert "fetch(" in landing


@pytest.mark.skipif(not _firebase_json_exists(), reason="firebase.json not tracked in repo")
class TestFirebaseRouting:
    """Test Firebase hosting configuration for canonical route.

    Note: firebase.json may not be tracked in the repo (deployment config).
    These tests are skipped in clean checkouts without firebase.json.
    """

    def test_firebase_json_exists(self):
        """firebase.json exists at repo root."""
        firebase_path = os.path.join(REPO_ROOT, "firebase.json")
        assert os.path.isfile(firebase_path)

    def test_f_route_rewrite_exists(self):
        """Firebase has rewrite rule for /f/**."""
        firebase_path = os.path.join(REPO_ROOT, "firebase.json")
        with open(firebase_path, encoding="utf-8") as f:
            config = json.load(f)

        rewrites = config.get("hosting", {}).get("rewrites", [])
        f_rule = next((r for r in rewrites if r.get("source") == "/f/**"), None)

        assert f_rule is not None, "Must have /f/** rewrite rule"
        assert f_rule.get("destination") == "/f/index.html"

    def test_f_route_comes_before_catchall(self):
        """The /f/** rule must come before the ** catchall."""
        firebase_path = os.path.join(REPO_ROOT, "firebase.json")
        with open(firebase_path, encoding="utf-8") as f:
            config = json.load(f)

        rewrites = config.get("hosting", {}).get("rewrites", [])
        sources = [r.get("source") for r in rewrites]

        f_index = sources.index("/f/**") if "/f/**" in sources else -1
        catchall_index = sources.index("**") if "**" in sources else -1

        assert f_index >= 0, "/f/** rule must exist"
        assert catchall_index >= 0, "** catchall must exist"
        assert f_index < catchall_index, "/f/** must come before ** catchall"


class TestCanonicalRouteBehavior:
    """Test canonical landing page behavior."""

    def test_landing_handles_missing_id(self):
        """Landing shows error for missing foundup_id."""
        landing = _read("../f/index.html")
        assert "No FoundUp specified" in landing

    def test_landing_handles_invalid_id(self):
        """Landing shows error for unknown/invalid foundup_id."""
        landing = _read("../f/index.html")
        # Landing shows "not found" for invalid IDs (catalog lookup fails)
        assert "not found" in landing.lower() or "does not exist" in landing.lower()

    def test_landing_has_mall_fallback(self):
        """Landing has Return to Mall link."""
        landing = _read("../f/index.html")
        assert "/member/" in landing
        assert "Mall" in landing

    def test_landing_preserves_subpath(self):
        """Landing captures subpath for future routing."""
        landing = _read("../f/index.html")
        assert "subpath" in landing


class TestCanonicalRouteRendering:
    """Test that landing renders content directly (no redirect)."""

    def test_landing_does_not_redirect(self):
        """Landing does NOT redirect to /member/foundup.html."""
        landing = _read("../f/index.html")
        # Should NOT have location.replace redirect
        assert "location.replace" not in landing
        # Should NOT redirect to transitional entry
        assert "/member/foundup.html?id=" not in landing

    def test_landing_renders_entry_content(self):
        """Landing renders entry content directly."""
        landing = _read("../f/index.html")
        # Should render landing UI elements
        assert "entry-hero" in landing
        assert "entry-details" in landing
        assert "entry-footer" in landing

    def test_landing_is_canonical(self):
        """Landing explicitly marks itself as canonical."""
        landing = _read("../f/index.html")
        assert "canonical" in landing.lower()
        assert "WSP 104" in landing


class TestWsp104Compliance:
    """Test WSP 104 route namespace compliance."""

    def test_canonical_route_displayed(self):
        """Canonical route is displayed to user."""
        landing = _read("../f/index.html")
        assert "Canonical route:" in landing or "canonical-route" in landing

    def test_no_transitional_redirect(self):
        """No auto-redirect on page load — canonical URL stays visible."""
        landing = _read("../f/index.html")
        # The old bridge had location.replace redirect — this should not
        assert "location.replace(" not in landing
        # Should not auto-redirect to transitional entry on load
        assert "/member/foundup.html?id=" not in landing
        # The word "transitional" should not appear (old bridge language)
        assert "transitional" not in landing.lower()

    def test_stable_identity_from_path(self):
        """FoundUp identity derived from URL path, not query params."""
        landing = _read("../f/index.html")
        # Should parse from pathname, not search params
        assert "window.location.pathname" in landing
        assert "/f/" in landing
        # Should NOT rely on query param for primary routing
        assert "params.get('id')" not in landing


class TestSubpathForwardCompatibility:
    """Test subpath support for future /app mount."""

    def test_subpath_captured(self):
        """Subpath is captured from URL."""
        landing = _read("../f/index.html")
        assert "subpath" in landing

    def test_subpath_info_displayed(self):
        """Subpath info displayed when present."""
        landing = _read("../f/index.html")
        assert "subpath-info" in landing or "Subpath:" in landing

    def test_app_mount_comment(self):
        """Code mentions future /app mount."""
        landing = _read("../f/index.html")
        assert "/app" in landing


class TestTransitionalFallbackPreserved:
    """Test that transitional entry path still works (backward compat)."""

    def test_foundup_html_exists(self):
        """Transitional entry page still exists."""
        assert os.path.isfile(os.path.join(ROOT, "foundup.html"))

    def test_foundup_html_accepts_id_param(self):
        """Transitional entry still reads id from URL param."""
        entry = _read("foundup.html")
        assert "params.get('id')" in entry

    def test_member_entry_flow_unchanged(self):
        """Member entry flow structure is preserved."""
        entry = _read("foundup.html")
        assert "entry-shell" in entry
        assert "entryContent" in entry


class TestAppMountRoute:
    """Test /f/{foundup_id}/app canonical app mount (WSP 104)."""

    def test_app_mount_detection(self):
        """Landing detects /app subpath."""
        landing = _read("../f/index.html")
        assert "isAppMount" in landing
        assert "subpath === 'app'" in landing or "'app'" in landing

    def test_app_mount_renders_container(self):
        """App mount has container CSS and structure."""
        landing = _read("../f/index.html")
        assert "app-mount-container" in landing
        assert "app-mount-frame" in landing
        assert "app-mount-header" in landing

    def test_app_mount_uses_entry_url(self):
        """App mount uses manifest entry_url."""
        landing = _read("../f/index.html")
        assert "entry_url" in landing
        assert "renderAppMount" in landing

    def test_app_mount_back_link(self):
        """App mount has back link to landing."""
        landing = _read("../f/index.html")
        assert "Back to FoundUp" in landing
        assert "app-mount-back" in landing

    def test_app_mount_sandbox(self):
        """App mount iframe has sandbox attribute."""
        landing = _read("../f/index.html")
        assert 'sandbox="' in landing
        assert "allow-scripts" in landing

    def test_app_not_ready_error(self):
        """App mount shows error when entry_url missing."""
        landing = _read("../f/index.html")
        assert "App Not Ready" in landing
        assert "does not have an app entry" in landing


class TestAppMountDeepLinks:
    """Test /f/{foundup_id}/app/{path...} deep link support."""

    def test_deep_path_captured(self):
        """Deep path after /app is captured."""
        landing = _read("../f/index.html")
        assert "appSubpath" in landing
        assert "deepPath" in landing or "deep" in landing.lower()

    def test_deep_path_forwarded(self):
        """Deep path is forwarded to app frame."""
        landing = _read("../f/index.html")
        # Should pass path as query param or in URL
        assert "path=" in landing or "deepPath" in landing


class TestLaunchAppCTA:
    """Test Launch App CTA on landing surface."""

    def test_launch_app_cta_exists(self):
        """Landing has Launch App CTA block."""
        landing = _read("../f/index.html")
        assert "entry-launch-app-block" in landing
        assert "entry-launch-app-btn" in landing

    def test_launch_app_links_to_app_route(self):
        """Launch App CTA links to /f/{id}/app."""
        landing = _read("../f/index.html")
        assert "'/f/' + foundupId + '/app'" in landing

    def test_launch_app_conditional_on_entry_url(self):
        """Launch App CTA only shown when entry_url exists."""
        landing = _read("../f/index.html")
        assert "item.entry_url" in landing

    def test_launch_app_recommendation(self):
        """Red Dog has Launch App recommendation."""
        landing = _read("../f/index.html")
        assert "launch_app" in landing
        assert "'Launch App'" in landing


class TestGotJunkTenantBinding:
    """Test GotJunk as first bound tenant (WSP 104)."""

    def test_gotjunk_in_catalog(self):
        """GotJunk exists in mall-video-catalog.json."""
        catalog = _read("mall-video-catalog.json")
        assert '"foundup_id": "gotjunk_001"' in catalog

    def test_gotjunk_has_routing_prefix(self):
        """GotJunk catalog entry has correct routing_prefix."""
        catalog = _read("mall-video-catalog.json")
        assert '"/f/gotjunk_001"' in catalog

    def test_gotjunk_has_data_namespace(self):
        """GotJunk catalog entry has data_namespace."""
        catalog = _read("mall-video-catalog.json")
        assert '"idb_gotjunk_001"' in catalog

    def test_gotjunk_no_entry_url_until_frame_compatible(self):
        """GotJunk has no entry_url until Cloud Run headers allow iframe embed.

        BLOCKER: Cloud Run returns X-Frame-Options: SAMEORIGIN which blocks
        the shell iframe mount at /f/gotjunk_001/app. entry_url must remain
        absent until the deployment is configured with frame-compatible headers.

        Unblock by: adding X-Frame-Options: ALLOWALL or removing the header
        and setting Content-Security-Policy frame-ancestors to include the
        shell origin, then re-adding entry_url to catalog and manifest.
        """
        catalog = _read("mall-video-catalog.json")
        idx = catalog.find('"foundup_id": "gotjunk_001"')
        assert idx > 0
        next_entry = catalog.find('"foundup_id":', idx + 30)
        if next_entry < 0:
            next_entry = len(catalog)
        gotjunk_entry = catalog[idx:next_entry]
        assert '"entry_url"' not in gotjunk_entry


class TestKoseiTenantBinding:
    """Test Kosei as second bound tenant (WSP 104).

    Kosei is bound to the canonical shell route family after GotJunk.
    Unlike GotJunk, Kosei has no embeddable runtime yet (discoverable_only).
    """

    def test_kosei_in_catalog(self):
        """Kosei exists in mall-video-catalog.json."""
        catalog = _read("mall-video-catalog.json")
        assert '"foundup_id": "kosei"' in catalog

    def test_kosei_has_routing_prefix(self):
        """Kosei catalog entry has correct routing_prefix."""
        catalog = _read("mall-video-catalog.json")
        assert '"/f/kosei"' in catalog

    def test_kosei_has_data_namespace(self):
        """Kosei catalog entry has data_namespace."""
        catalog = _read("mall-video-catalog.json")
        assert '"idb_kosei"' in catalog

    def test_kosei_has_entry_url(self):
        """Kosei has entry_url after BX4 iframe verification confirmed embeddability.

        BX4 (PR #337) verified the Kosei app renders inside the FoundUps shell iframe.
        entry_url is now truthfully set to the deployed app URL.
        """
        catalog = _read("mall-video-catalog.json")
        idx = catalog.find('"foundup_id": "kosei"')
        assert idx > 0
        next_entry = catalog.find('"foundup_id":', idx + 20)
        if next_entry < 0:
            next_entry = len(catalog)
        kosei_entry = catalog[idx:next_entry]
        # entry_url should be present after iframe verification
        assert '"entry_url": "https://foundupscom.web.app/kosei/app/"' in kosei_entry

    def test_kosei_launch_readiness_is_ready(self):
        """Kosei is ready after iframe embed verification (BX4)."""
        catalog = _read("mall-video-catalog.json")
        idx = catalog.find('"foundup_id": "kosei"')
        assert idx > 0
        next_entry = catalog.find('"foundup_id":', idx + 20)
        if next_entry < 0:
            next_entry = len(catalog)
        kosei_entry = catalog[idx:next_entry]
        assert '"ready"' in kosei_entry


class TestCatalogArrayHandling:
    """Test catalog array format handling."""

    def test_landing_handles_array_catalog(self):
        """Landing handles catalog as direct array (not wrapped)."""
        landing = _read("../f/index.html")
        assert "Array.isArray(catalog)" in landing

    def test_url_resolution_uses_foundups_path(self):
        """Relative URLs resolve to /foundups/{id}/ not routing_prefix."""
        landing = _read("../f/index.html")
        assert "'/foundups/' + foundupId" in landing
        # Should NOT use routingPrefix for asset resolution
        idx = landing.find("resolvedUrl = ")
        if idx > 0:
            snippet = landing[idx:idx+200]
            assert "routingPrefix + '/'" not in snippet
