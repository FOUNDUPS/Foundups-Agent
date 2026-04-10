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

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_ROOT = os.path.dirname(os.path.dirname(ROOT))


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


class TestFirebaseRouting:
    """Test Firebase hosting configuration for canonical route."""

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
        """Landing validates foundup_id format."""
        landing = _read("../f/index.html")
        assert "Invalid" in landing or "not valid" in landing

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
        """No transitional redirect — canonical URL stays visible."""
        landing = _read("../f/index.html")
        # The old bridge had "transitional" in it — this should not
        assert "location.replace(" not in landing
        assert "location.href =" not in landing

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
