#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for p.fMALL HTTP Read Surface.

Uses FastAPI TestClient for synchronous endpoint testing.
Delegates to pfmall/api.py — tests verify transport shape only.
"""

import pytest
from fastapi.testclient import TestClient

from modules.foundups.pfmall.http_api import app
from modules.foundups.pfmall.api import reset_default_shell


@pytest.fixture(autouse=True)
def _reset_shell():
    """Reset default shell before each test for isolation."""
    reset_default_shell()
    yield
    reset_default_shell()


client = TestClient(app)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

class TestHealth:
    """Tests for GET /pfmall/health."""

    def test_health_ok(self):
        r = client.get("/pfmall/health")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "ok"
        assert body["booted"] is True
        assert isinstance(body["catalog_count"], int)
        assert body["catalog_count"] >= 3


# ---------------------------------------------------------------------------
# Catalog
# ---------------------------------------------------------------------------

class TestCatalog:
    """Tests for GET /pfmall/catalog."""

    def test_catalog_returns_list(self):
        r = client.get("/pfmall/catalog")
        assert r.status_code == 200
        body = r.json()
        assert isinstance(body, list)
        assert len(body) >= 3

    def test_catalog_entries_have_expected_keys(self):
        r = client.get("/pfmall/catalog")
        body = r.json()
        entry = body[0]
        assert "foundup_id" in entry
        assert "name" in entry
        assert "tier" in entry
        assert "launch_readiness" in entry
        assert "health_status" in entry

    def test_catalog_sorted_by_name(self):
        r = client.get("/pfmall/catalog")
        body = r.json()
        names = [e["name"] for e in body]
        assert names == sorted(names)

    def test_catalog_filtered_by_category(self):
        r = client.get("/pfmall/catalog", params={"category": "marketplace"})
        assert r.status_code == 200
        body = r.json()
        assert len(body) >= 1
        assert all(e["category"] == "marketplace" for e in body)

    def test_catalog_filter_no_match(self):
        r = client.get("/pfmall/catalog", params={"category": "nonexistent"})
        assert r.status_code == 200
        body = r.json()
        assert body == []


# ---------------------------------------------------------------------------
# Single FoundUp
# ---------------------------------------------------------------------------

class TestFoundupDetail:
    """Tests for GET /pfmall/foundups/{foundup_id}."""

    def test_known_foundup(self):
        r = client.get("/pfmall/foundups/gotjunk_001")
        assert r.status_code == 200
        body = r.json()
        assert body["foundup_id"] == "gotjunk_001"
        assert body["name"] == "GotJunk"
        assert body["launch_readiness"] == "conditional"

    def test_missing_foundup_404(self):
        r = client.get("/pfmall/foundups/nonexistent_999")
        assert r.status_code == 404
        body = r.json()
        assert "not found" in body["detail"].lower()

    def test_antifafm_foundup(self):
        r = client.get("/pfmall/foundups/antifafm_001")
        assert r.status_code == 200
        body = r.json()
        assert body["name"] == "antifaFM"
        assert body["launch_readiness"] == "discoverable_only"


# ---------------------------------------------------------------------------
# Route Resolution
# ---------------------------------------------------------------------------

class TestResolveRoute:
    """Tests for GET /pfmall/resolve-route."""

    def test_shell_route(self):
        r = client.get("/pfmall/resolve-route", params={"path": "/discover"})
        assert r.status_code == 200
        body = r.json()
        assert body["kind"] == "shell"
        assert body["path"] == "/discover"

    def test_foundup_route(self):
        r = client.get("/pfmall/resolve-route", params={"path": "/f/gotjunk_001/listings"})
        assert r.status_code == 200
        body = r.json()
        assert body["kind"] == "foundup"
        assert body["foundup_id"] == "gotjunk_001"
        assert body["foundup_path"] == "/listings"

    def test_not_found_route(self):
        r = client.get("/pfmall/resolve-route", params={"path": "/random/path"})
        assert r.status_code == 200
        body = r.json()
        assert body["kind"] == "not_found"
        assert "error" in body

    def test_missing_path_param(self):
        r = client.get("/pfmall/resolve-route")
        assert r.status_code == 422  # FastAPI validation error
