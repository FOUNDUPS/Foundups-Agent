"""
Route Contract Bridge Tests

Tests for the /f/{foundup_id} route bridge.
Bridge redirects to transitional entry: /member/foundup.html?id={foundup_id}

Route contract: PFMALL_EXTERNAL_FOUNDUP_ROUTE_CONTRACT.md
"""
import json
import os
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_ROOT = os.path.dirname(os.path.dirname(ROOT))


def _read(relpath, base=ROOT):
    with open(os.path.join(base, relpath), encoding="utf-8") as f:
        return f.read()


class TestRouteBridgeExists:
    """Test that the route bridge surface exists."""

    def test_bridge_html_exists(self):
        """Bridge HTML file exists at public/f/index.html."""
        bridge_path = os.path.join(REPO_ROOT, "public", "f", "index.html")
        assert os.path.isfile(bridge_path), "public/f/index.html must exist"

    def test_bridge_has_route_parsing(self):
        """Bridge parses foundup_id from path."""
        bridge = _read("../f/index.html")
        assert "/f/" in bridge
        assert "foundup_id" in bridge.lower() or "foundupId" in bridge

    def test_bridge_redirects_to_transitional_entry(self):
        """Bridge redirects to /member/foundup.html."""
        bridge = _read("../f/index.html")
        assert "/member/foundup.html" in bridge


class TestFirebaseRouting:
    """Test Firebase hosting configuration for route bridge."""

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


class TestBridgeBehavior:
    """Test bridge page behavior."""

    def test_bridge_handles_missing_id(self):
        """Bridge shows error for missing foundup_id."""
        bridge = _read("../f/index.html")
        assert "No FoundUp specified" in bridge or "No valid foundup_id" in bridge.lower()

    def test_bridge_handles_invalid_id(self):
        """Bridge validates foundup_id format."""
        bridge = _read("../f/index.html")
        assert "Invalid" in bridge or "not valid" in bridge

    def test_bridge_has_mall_fallback(self):
        """Bridge has Return to Mall link."""
        bridge = _read("../f/index.html")
        assert "/member/" in bridge
        assert "Mall" in bridge

    def test_bridge_preserves_subpath(self):
        """Bridge captures subpath for future routing."""
        bridge = _read("../f/index.html")
        assert "subpath" in bridge


class TestNoFakeRuntime:
    """Test that no fake live runtime claims exist."""

    def test_bridge_does_not_render_foundup(self):
        """Bridge does not render FoundUp content itself."""
        bridge = _read("../f/index.html")
        # Should redirect, not render FoundUp interior
        assert "location.replace" in bridge or "location.href" in bridge

    def test_bridge_is_transitional(self):
        """Bridge explicitly mentions transitional routing."""
        bridge = _read("../f/index.html")
        assert "transitional" in bridge.lower()


class TestTransitionalFallbackPreserved:
    """Test that transitional entry path still works."""

    def test_foundup_html_exists(self):
        """Transitional entry page exists."""
        assert os.path.isfile(os.path.join(ROOT, "foundup.html"))

    def test_foundup_html_accepts_id_param(self):
        """Transitional entry reads id from URL param."""
        entry = _read("foundup.html")
        assert "params.get('id')" in entry or "get('id')" in entry

    def test_member_entry_flow_unchanged(self):
        """Member entry flow structure is preserved."""
        entry = _read("foundup.html")
        assert "entry-shell" in entry
        assert "entryContent" in entry
