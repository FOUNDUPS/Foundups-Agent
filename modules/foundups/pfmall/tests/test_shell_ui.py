#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for p.fMALL Shell UI Phase 1.

Lightweight response/content assertions via FastAPI TestClient.
Verifies catalog, detail, handoff views load and contain expected content.
"""

import pytest
from fastapi.testclient import TestClient

from modules.foundups.pfmall.http_api import app
from modules.foundups.pfmall.api import reset_default_shell


@pytest.fixture(autouse=True)
def _reset_shell():
    reset_default_shell()
    yield
    reset_default_shell()


client = TestClient(app)


# ---------------------------------------------------------------------------
# Static Assets
# ---------------------------------------------------------------------------

class TestStaticAssets:
    """Static files are served correctly."""

    def test_css_loads(self):
        r = client.get("/pfmall/static/styles.css")
        assert r.status_code == 200
        assert "text/css" in r.headers["content-type"]
        assert "--bg:" in r.text


# ---------------------------------------------------------------------------
# Catalog Page
# ---------------------------------------------------------------------------

class TestCatalogPage:
    """Tests for the catalog view at /pfmall/ui/."""

    def test_catalog_page_loads(self):
        r = client.get("/pfmall/ui/")
        assert r.status_code == 200
        assert "text/html" in r.headers["content-type"]

    def test_catalog_page_has_shell_chrome(self):
        r = client.get("/pfmall/ui/")
        assert "p.fMALL" in r.text
        assert "catalog" in r.text.lower()

    def test_catalog_page_fetches_api(self):
        """Page contains fetch call to /pfmall/catalog."""
        r = client.get("/pfmall/ui/")
        assert "/pfmall/catalog" in r.text

    def test_catalog_page_has_readiness_badges(self):
        """Page template includes readiness badge classes."""
        r = client.get("/pfmall/ui/")
        assert "badge-readiness-" in r.text


# ---------------------------------------------------------------------------
# Detail Page
# ---------------------------------------------------------------------------

class TestDetailPage:
    """Tests for the detail view at /pfmall/ui/detail.html."""

    def test_detail_page_loads(self):
        r = client.get("/pfmall/ui/detail.html")
        assert r.status_code == 200
        assert "text/html" in r.headers["content-type"]

    def test_detail_page_has_back_link(self):
        r = client.get("/pfmall/ui/detail.html")
        assert "Back to catalog" in r.text

    def test_detail_page_fetches_api(self):
        """Page contains fetch call to /pfmall/foundups/."""
        r = client.get("/pfmall/ui/detail.html")
        assert "/pfmall/foundups/" in r.text

    def test_detail_page_shows_overlay_section(self):
        """Page template includes overlay status section."""
        r = client.get("/pfmall/ui/detail.html")
        assert "Overlay Status" in r.text


# ---------------------------------------------------------------------------
# Handoff Page
# ---------------------------------------------------------------------------

class TestHandoffPage:
    """Tests for the handoff view at /pfmall/ui/handoff.html."""

    def test_handoff_page_loads(self):
        r = client.get("/pfmall/ui/handoff.html")
        assert r.status_code == 200
        assert "text/html" in r.headers["content-type"]

    def test_handoff_page_has_shell_chrome(self):
        r = client.get("/pfmall/ui/handoff.html")
        assert "p.fMALL" in r.text
        assert "handoff" in r.text.lower()

    def test_handoff_page_resolves_routes(self):
        """Page contains fetch call to /pfmall/resolve-route."""
        r = client.get("/pfmall/ui/handoff.html")
        assert "/pfmall/resolve-route" in r.text

    def test_handoff_page_handles_not_found(self):
        """Page template includes not-found handling."""
        r = client.get("/pfmall/ui/handoff.html")
        assert "Not Found" in r.text


# ---------------------------------------------------------------------------
# FoundUp Route Handoff (/f/{foundup_id})
# ---------------------------------------------------------------------------

class TestFoundUpRouteHandoff:
    """Tests for /f/{foundup_id} redirect to handoff UI."""

    def test_f_route_redirects(self):
        """GET /f/{id} redirects to handoff UI."""
        r = client.get("/f/gotjunk_001", follow_redirects=False)
        assert r.status_code == 307
        assert "/pfmall/ui/handoff.html?id=gotjunk_001" in r.headers["location"]

    def test_f_route_with_subpath_redirects(self):
        """GET /f/{id}/listings/search strips sub-path and redirects."""
        r = client.get("/f/gotjunk_001/listings/search", follow_redirects=False)
        assert r.status_code == 307
        assert "/pfmall/ui/handoff.html?id=gotjunk_001" in r.headers["location"]

    def test_f_route_unknown_id_still_redirects(self):
        """Unknown FoundUp ID still redirects; handoff page shows not-found."""
        r = client.get("/f/nonexistent_999", follow_redirects=False)
        assert r.status_code == 307
        assert "id=nonexistent_999" in r.headers["location"]

    def test_f_route_follows_to_handoff(self):
        """Following redirect lands on handoff HTML page."""
        r = client.get("/f/gotjunk_001")
        assert r.status_code == 200
        assert "text/html" in r.headers["content-type"]
        assert "handoff" in r.text.lower()


# ---------------------------------------------------------------------------
# JSON API Regressions (ensure UI mount didn't break API)
# ---------------------------------------------------------------------------

class TestApiRegressions:
    """Verify JSON endpoints still work after UI mount."""

    def test_health_still_works(self):
        r = client.get("/pfmall/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    def test_catalog_api_still_works(self):
        r = client.get("/pfmall/catalog")
        assert r.status_code == 200
        assert len(r.json()) >= 3

    def test_foundup_api_still_works(self):
        r = client.get("/pfmall/foundups/gotjunk_001")
        assert r.status_code == 200
        assert r.json()["name"] == "GotJunk"

    def test_resolve_route_api_still_works(self):
        r = client.get("/pfmall/resolve-route", params={"path": "/discover"})
        assert r.status_code == 200
        assert r.json()["kind"] == "shell"

    def test_foundup_404_still_works(self):
        r = client.get("/pfmall/foundups/nonexistent_999")
        assert r.status_code == 404
