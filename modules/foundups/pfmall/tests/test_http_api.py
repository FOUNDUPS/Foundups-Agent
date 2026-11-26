#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for p.fMALL HTTP Read Surface.

Uses FastAPI TestClient for synchronous endpoint testing.
Delegates to pfmall/api.py — tests verify transport shape only.
"""

import hashlib
import importlib
import json
import subprocess
import time

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from modules.foundups.pfmall import http_api
from modules.foundups.pfmall.api import reset_default_shell
from modules.foundups.pfmall.fractal_tile_graph import (
    ROOT_TILE_ID,
    build_graph_indices,
    compute_tiles_etag,
    make_tile,
    project_public_tile_graph,
)
from modules.foundups.pfmall.http_api import TileGraphAuthPolicy, TrustedProxyPolicy, app
from modules.foundups.pfmall.tile_graph_store import TileGraphStore


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


# ---------------------------------------------------------------------------
# Shell UI, Static Assets, Handoff & Public Listings Boundaries
# ---------------------------------------------------------------------------

class TestShellUiHandoffAndListings:
    """Verify shell UI, handoff redirects, and listing boundaries."""

    def test_shell_ui_and_static_assets(self):
        ui = client.get("/pfmall/ui/")
        assert ui.status_code == 200
        assert "text/html" in ui.headers.get("content-type", "")

        handoff_page = client.get("/pfmall/ui/handoff.html")
        assert handoff_page.status_code == 200

    def test_foundup_handoff_redirects_307(self):
        r = client.get("/f/gotjunk_001/listings", follow_redirects=False)
        assert r.status_code == 307
        assert r.headers["location"] == "/pfmall/ui/handoff.html?id=gotjunk_001"

    def test_listings_search_boundaries(self, monkeypatch):
        monkeypatch.delattr(app.state, "listing_evidence_provider", raising=False)
        assert client.get("/pfmall/listings/search").status_code == 503
        assert client.get("/pfmall/listings/search", params={"foundup_id": "antifafm_001"}).status_code == 403
        assert client.get("/pfmall/listings/search", params={"owner_uid": "uid_123"}).status_code == 403


# ---------------------------------------------------------------------------
# Local Routing & Admission Matrix Across Protected Routes
# ---------------------------------------------------------------------------

class TestLocalRoutingAndAdmissionMatrix:
    """Verify full fail-closed admission, proxy trust, gzip, and ETag gating matrix."""

    _ORIGIN = "https://foundups.com"
    _HTTP_BASE = "http://foundups.com"
    _ISSUER = "https://identity.example.com"
    _ARCHITECT_SUB = "user_Architect012"
    _MEMBER_SUB = "user_Member042"
    _OUTSIDER_SUB = "user_Outsider99"

    @staticmethod
    def _handle(sub: str) -> str:
        return "clerk_" + hashlib.sha256((f"{TestLocalRoutingAndAdmissionMatrix._ISSUER}\0{sub}").encode("utf-8")).hexdigest()

    @staticmethod
    def _minimal_graph() -> dict:
        tiles = {
            ROOT_TILE_ID: make_tile(
                tile_id=ROOT_TILE_ID,
                display_name="PlayFoundups Mall",
                tile_kind="system_cube",
                visibility_scope="public",
                owner_namespace="foundups_core",
                parent_tile_id=None,
                state="GREEN",
            ),
            "tile:sys:simulator": make_tile(
                tile_id="tile:sys:simulator",
                display_name="FoundUps Simulator",
                tile_kind="system_cube",
                visibility_scope="public",
                owner_namespace="foundups_core",
                parent_tile_id=ROOT_TILE_ID,
                state="AMBER",
                metadata={"summary": "m" * 1200},
            ),
            "tile:opus:jhr.004": make_tile(
                tile_id="tile:opus:jhr.004",
                display_name="Private Draft",
                tile_kind="opus_item",
                visibility_scope="principal_only",
                owner_namespace="foundups_core",
                parent_tile_id=ROOT_TILE_ID,
                state="AMBER",
                metadata={"metadata_only": True},
            ),
        }
        tiles[ROOT_TILE_ID]["children_tile_ids"] = ["tile:opus:jhr.004", "tile:sys:simulator"]
        indices = build_graph_indices(tiles)
        graph = {
            "schema_version": "fractal_tile_graph.v1",
            "generated_at_utc": "2026-11-21T00:00:00+00:00",
            "git_revision": "7432d31e5a68544d2bbab6715f02f64b0b5b6f85",
            "graph_etag": compute_tiles_etag(tiles),
            "public_graph_etag": "",
            "scope": "012_architect",
            "root_tile_id": ROOT_TILE_ID,
            "counts": indices["counts"],
            "links": indices["links"],
            "search_index": indices["search_index"],
            "tiles": tiles,
        }
        graph["public_graph_etag"] = project_public_tile_graph(graph)["public_graph_etag"]
        return graph

    @pytest.fixture(scope="class")
    def matrix_key(self):
        return rsa.generate_private_key(public_exponent=65537, key_size=2048)

    @pytest.fixture
    def matrix_env(self, matrix_key, tmp_path, monkeypatch):
        clerk_mod = importlib.import_module("modules.ai_intelligence.ai_overseer.src.foundup_genesis.clerk_intake")
        pem = matrix_key.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode("ascii")
        clerk_policy = clerk_mod.ClerkIntakePolicy(
            issuer=self._ISSUER,
            authorized_parties=(self._ORIGIN,),
            public_key_pem=pem,
        )
        auth_policy = TileGraphAuthPolicy(
            architect_actors=(self._handle(self._ARCHITECT_SUB),),
            admitted_member_actors=(self._handle(self._MEMBER_SUB),),
        )
        store = TileGraphStore(tmp_path / "matrix.sqlite3", initial_graph=self._minimal_graph())
        pub_src = tmp_path / "source_files.public.json"
        arch_src = tmp_path / "source_files.architect.json"
        pub_src.write_text(json.dumps({"scope": "public_mall", "tiles": {}, "pad": "y" * 1600}), encoding="utf-8")
        arch_src.write_text(json.dumps({"scope": "012_architect", "tiles": {}, "pad": "z" * 1600}), encoding="utf-8")

        monkeypatch.setattr(app.state, "clerk_intake_policy", clerk_policy, raising=False)
        monkeypatch.setattr(app.state, "tile_graph_policy", auth_policy, raising=False)
        monkeypatch.setattr(app.state, "tile_graph_store", store, raising=False)
        monkeypatch.setattr(app.state, "member_source_files_path", pub_src, raising=False)
        monkeypatch.setattr(app.state, "architect_source_files_path", arch_src, raising=False)
        for attr in ("trusted_proxy_policy", "trust_proxy_headers", "trusted_proxy_hosts"):
            monkeypatch.delattr(app.state, attr, raising=False)
        try:
            yield {"key": matrix_key, "store": store}
        finally:
            store.close()

    def _token(self, key, sub: str) -> str:
        now = int(time.time())
        return jwt.encode(
            {
                "iss": self._ISSUER,
                "azp": self._ORIGIN,
                "sub": sub,
                "sid": "sess_matrix01",
                "v": 2,
                "iat": now,
                "nbf": now - 5,
                "exp": now + 60,
            },
            key,
            algorithm="RS256",
        )

    def test_trusted_proxy_policy_validation_rejects_invalid_inputs(self):
        with pytest.raises(ValueError, match="invalid_trusted_proxy_policy"):
            TrustedProxyPolicy(trust_proxy_headers="yes")  # type: ignore[arg-type]
        with pytest.raises(ValueError, match="invalid_trusted_proxy_policy"):
            TrustedProxyPolicy(trust_proxy_headers=True, trusted_proxy_hosts="127.0.0.1")  # type: ignore[arg-type]
        with pytest.raises(ValueError, match="invalid_trusted_proxy_policy"):
            TrustedProxyPolicy(trust_proxy_headers=True, trusted_proxy_hosts=("127.0.0.1", "127.0.0.1"))
        with pytest.raises(ValueError, match="invalid_trusted_proxy_policy"):
            TrustedProxyPolicy(trust_proxy_headers=True, trusted_proxy_hosts=("10.0.0.0/8",))

    def test_full_routing_and_admission_matrix_and_pre_lookup_gates(self, matrix_env, monkeypatch):
        key = matrix_env["key"]
        store = matrix_env["store"]
        member_tok = self._token(key, self._MEMBER_SUB)
        outsider_tok = self._token(key, self._OUTSIDER_SUB)
        architect_tok = self._token(key, self._ARCHITECT_SUB)

        # Spy on store and disk loaders to prove auth/admission/scope run BEFORE lookup
        lookup_calls = []
        orig_get_pub = store.get_public_graph
        orig_get_arch = store.get_architect_graph
        orig_load_bytes = http_api._load_member_json_bytes

        def spy_pub():
            lookup_calls.append("store_public")
            return orig_get_pub()

        def spy_arch():
            lookup_calls.append("store_architect")
            return orig_get_arch()

        def spy_load(path, *, etag_field=None):
            lookup_calls.append(f"disk:{path.name}")
            return orig_load_bytes(path, etag_field=etag_field)

        monkeypatch.setattr(store, "get_public_graph", spy_pub)
        monkeypatch.setattr(store, "get_architect_graph", spy_arch)
        monkeypatch.setattr(http_api, "_load_member_json_bytes", spy_load)

        with TestClient(app, base_url=self._HTTP_BASE) as tc:
            # 1. Spoofed X-Forwarded-Proto without trusted proxy fails closed 401 before lookup
            spoof_member = {
                "Authorization": f"Bearer {member_tok}",
                "Sec-Fetch-Site": "same-origin",
                "Referer": f"{self._ORIGIN}/member/",
                "X-Forwarded-Proto": "https",
            }
            for ep in ("/pfmall/tile-graph", "/pfmall/source-files"):
                r_spoof = tc.get(ep, headers=spoof_member)
                assert r_spoof.status_code == 401
                assert r_spoof.headers["cache-control"] == "private, no-store"
                assert "authorization" in r_spoof.headers["vary"].lower()
                assert "origin" in r_spoof.headers["vary"].lower()
            assert lookup_calls == []

            # 2. Invalid scope 400 & outsider 403 & member-on-architect 403 never touch store/disk
            assert tc.get("/pfmall/tile-graph", params={"scope": "bad"}).status_code == 400
            assert tc.get("/pfmall/source-files", params={"scope": "bad"}).status_code == 400

            outsider_origin = {"Authorization": f"Bearer {outsider_tok}", "Origin": self._ORIGIN}
            member_origin = {"Authorization": f"Bearer {member_tok}", "Origin": self._ORIGIN}
            architect_origin = {"Authorization": f"Bearer {architect_tok}", "Origin": self._ORIGIN}

            for ep in ("/pfmall/tile-graph", "/pfmall/source-files"):
                assert tc.get(ep, headers={**outsider_origin, "If-None-Match": "*"}).status_code == 403
                assert tc.get(ep, params={"scope": "012_architect"}, headers={**member_origin, "If-None-Match": "*"}).status_code == 403
                assert tc.get(ep, headers={"If-None-Match": "*"}).status_code == 401
            assert lookup_calls == []

            # 3. Enable trusted proxy for https://foundups.com -> Origin-less same-origin GET succeeds
            monkeypatch.setattr(app.state, "trust_proxy_headers", True, raising=False)
            monkeypatch.setattr(app.state, "trusted_proxy_hosts", ("testclient",), raising=False)

            r_graph = tc.get("/pfmall/tile-graph", headers={**spoof_member, "Accept-Encoding": "gzip"})
            assert r_graph.status_code == 200
            assert r_graph.headers.get("content-encoding") == "gzip"
            assert r_graph.headers["cache-control"] == "private, no-store"
            assert "authorization" in r_graph.headers["vary"].lower()
            assert "origin" in r_graph.headers["vary"].lower()
            assert "accept-encoding" in r_graph.headers["vary"].lower()
            assert r_graph.json()["scope"] == "public_mall"

            r_src = tc.get("/pfmall/source-files", headers={**spoof_member, "Accept-Encoding": "gzip"})
            assert r_src.status_code == 200
            assert r_src.headers.get("content-encoding") == "gzip"
            assert r_src.headers["cache-control"] == "private, no-store"
            assert "authorization" in r_src.headers["vary"].lower()
            assert "origin" in r_src.headers["vary"].lower()

            # 304 ETag honored only for authenticated admitted caller
            assert tc.get(
                "/pfmall/tile-graph",
                headers={**spoof_member, "If-None-Match": r_graph.headers["etag"]},
            ).status_code == 304
            assert tc.get(
                "/pfmall/source-files",
                headers={**spoof_member, "If-None-Match": r_src.headers["etag"]},
            ).status_code == 304

            # 4. POST /pfmall/tile-graph/patches matrix: unauth 401, member/outsider 403, architect 201
            arch_etag = store.get_architect_graph()["graph_etag"]
            patch_body = {
                "patch_id": "matrix-patch-001",
                "base_graph_etag": arch_etag,
                "scope": "012_architect",
                "tenant": "foundups_core",
                "op": "RENAME_DISPLAY_LABEL",
                "target_tile_id": "tile:sys:simulator",
                "payload": {"display_name": "Simulator Matrix Renamed"},
            }
            assert tc.post("/pfmall/tile-graph/patches", json=patch_body).status_code == 401
            assert tc.post("/pfmall/tile-graph/patches", headers=outsider_origin, json=patch_body).status_code == 403
            assert tc.post("/pfmall/tile-graph/patches", headers=member_origin, json=patch_body).status_code == 403
            r_patch = tc.post("/pfmall/tile-graph/patches", headers=architect_origin, json=patch_body)
            assert r_patch.status_code == 201
            assert r_patch.headers["cache-control"] == "no-store"

            # Architect GET 012_architect succeeds over trusted proxy
            r_arch = tc.get(
                "/pfmall/tile-graph",
                params={"scope": "012_architect"},
                headers={
                    "Authorization": f"Bearer {architect_tok}",
                    "Sec-Fetch-Site": "same-origin",
                    "Referer": f"{self._ORIGIN}/member/",
                    "X-Forwarded-Proto": "https",
                },
            )
            assert r_arch.status_code == 200
            assert "tile:opus:jhr.004" in r_arch.json()["tiles"]

    def test_source_content_endpoint_fail_closed_matrix(self, matrix_env, monkeypatch):
        key = matrix_env["key"]
        member_tok = self._token(key, self._MEMBER_SUB)
        outsider_tok = self._token(key, self._OUTSIDER_SUB)
        member_origin = {"Authorization": f"Bearer {member_tok}", "Origin": self._ORIGIN}
        outsider_origin = {"Authorization": f"Bearer {outsider_tok}", "Origin": self._ORIGIN}

        head_rev = subprocess.check_output(
            [
                "git",
                "-C",
                str(getattr(app.state, "source_content_repo_root", None) or http_api._REPO_ROOT),
                "rev-parse",
                "HEAD",
            ],
            text=True,
        ).strip()

        pub_src = app.state.member_source_files_path
        pub_src.write_text(
            json.dumps({
                "scope": "public_mall",
                "source_revision": head_rev,
                "tiles": {
                    "tile:opus:papers.dukkyo_practitioners.md": {
                        "registry_id": "WSP_knowledge",
                        "path_prefix": "",
                        "file_count": 2,
                        "files": [
                            "WSP_knowledge/docs/Papers/Dukkyo_Practitioners.md",
                            "modules/foundups/simulator/docs/ROC_FORMULA_DERIVATION.md",
                        ],
                    }
                },
            }),
            encoding="utf-8",
        )

        with TestClient(app, base_url=self._HTTP_BASE) as tc:
            # Unauthenticated / outsider fail closed pre-lookup
            assert tc.get("/pfmall/source-content", params={"path": "WSP_knowledge/docs/Papers/Dukkyo_Practitioners.md"}).status_code == 401
            assert tc.get("/pfmall/source-content", params={"path": "WSP_knowledge/docs/Papers/Dukkyo_Practitioners.md"}, headers=outsider_origin).status_code == 403

            # Traversal, backslash, leading slash, and private/forbidden paths fail closed 403
            for bad_path in (
                "../secret.txt",
                "modules/foundups/../../secret.txt",
                "/etc/passwd",
                "WSP_knowledge\\docs\\Papers\\Dukkyo_Practitioners.md",
                "modules/platform_integration/linkedin_agent/src/content/articles/ROI_to_RoC_Paradigm_Shift.md",
                "modules/foundups/esingularity/jhr/drafts/JHR_004.md",
                "modules/foundups/simulator/adapters/pfmall_state_provider.py",
            ):
                r_bad = tc.get("/pfmall/source-content", params={"path": bad_path}, headers=member_origin)
                assert r_bad.status_code == 403
                assert r_bad.headers["cache-control"] == "private, no-store"

            # Unadmitted path fails closed 404
            r_missing = tc.get(
                "/pfmall/source-content",
                params={"path": "README.md"},
                headers=member_origin,
            )
            assert r_missing.status_code == 404
            assert r_missing.headers["cache-control"] == "private, no-store"

            # Admitted <=16KiB pinned source slice succeeds 200 with private/no-store headers
            r_ok = tc.get(
                "/pfmall/source-content",
                params={
                    "path": "WSP_knowledge/docs/Papers/Dukkyo_Practitioners.md",
                    "start_line": 1,
                    "end_line": 25,
                },
                headers=member_origin,
            )
            assert r_ok.status_code == 200
            assert r_ok.headers["cache-control"] == "private, no-store"
            body = r_ok.json()
            assert body["ok"] is True
            assert body["revision"] == head_rev
            assert body["start_line"] == 1
            assert body["end_line"] == 25
            assert body["truncated"] is False
            assert "Dukkyo" in body["content"]

            # Real blob >16KiB (18996 bytes) fails closed 413 under bounded_child_runner cap
            assert tc.get(
                "/pfmall/source-content",
                params={"path": "modules/foundups/simulator/docs/ROC_FORMULA_DERIVATION.md"},
                headers=member_origin,
            ).status_code == 413

            # Adversarial: binary extension, oversized blob, non-blob gitlink, NUL bytes, and timeout fail closed
            pub_src.write_text(
                json.dumps({
                    "scope": "public_mall",
                    "source_revision": head_rev,
                    "tiles": {
                        "tile:test:adv": {
                            "registry_id": "test",
                            "path_prefix": "",
                            "file_count": 4,
                            "files": [
                                "tools/uv.exe",
                                "modules/foundups/simulator/docs/ROC_FORMULA_DERIVATION.md",
                                "vendor/hermes-agent",
                                "package-lock.json",
                            ],
                        }
                    },
                }),
                encoding="utf-8",
            )
            assert tc.get("/pfmall/source-content", params={"path": "tools/uv.exe"}, headers=member_origin).status_code == 403
            assert tc.get("/pfmall/source-content", params={"path": "vendor/hermes-agent"}, headers=member_origin).status_code == 403

            from modules.infrastructure.foundups_mcp_bridge.src.reddog_bounded_child_process import BoundedChildResult

            def _fake_oversize(cmd, **kw):
                if "ls-tree" in cmd:
                    return BoundedChildResult(0, b"100644 blob abc1234\tpackage-lock.json\n")
                return BoundedChildResult(0, b"15728640\n")

            monkeypatch.setattr(http_api, "bounded_child_runner", _fake_oversize)
            assert tc.get("/pfmall/source-content", params={"path": "package-lock.json"}, headers=member_origin).status_code == 413

            def _fake_timeout(cmd, **kw):
                raise subprocess.TimeoutExpired(cmd, 5.0)

            monkeypatch.setattr(http_api, "bounded_child_runner", _fake_timeout)
            assert tc.get("/pfmall/source-content", params={"path": "package-lock.json"}, headers=member_origin).status_code == 504
