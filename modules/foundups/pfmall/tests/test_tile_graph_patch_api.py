#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for authenticated atomic Tile Graph PATCH/GET routes and durable SQLite WAL store."""

from __future__ import annotations

import asyncio
import copy
import hashlib
import importlib
import json
import sqlite3
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from modules.foundups.pfmall.fractal_tile_graph import (
    ROOT_TILE_ID,
    build_graph_indices,
    compute_tiles_etag,
    make_tile,
    project_public_tile_graph,
)
from modules.foundups.pfmall.http_api import TileGraphAuthPolicy, TrustedProxyPolicy, app
from modules.foundups.pfmall.tile_graph_store import TileGraphStore

ISSUER = "https://identity.example.com"
ORIGIN = "https://foundups.example.com"
CLERK_MOD = "modules.ai_intelligence.ai_overseer.src.foundup_genesis.clerk_intake"

ARCHITECT_SUB = "user_Architect012"
HPC_SUB = "user_HpcEditor01"
MEMBER_SUB = "user_Member042"
OUTSIDER_SUB = "user_Outsider99"


def _actor_handle(sub: str) -> str:
    return "clerk_" + hashlib.sha256((ISSUER + "\0" + sub).encode("utf-8")).hexdigest()


ARCHITECT_HANDLE = _actor_handle(ARCHITECT_SUB)
HPC_HANDLE = _actor_handle(HPC_SUB)
MEMBER_HANDLE = _actor_handle(MEMBER_SUB)
OUTSIDER_HANDLE = _actor_handle(OUTSIDER_SUB)


def _sample_architect_graph() -> dict:
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
        ),
        "tile:socket:simulator.export_adapter": make_tile(
            tile_id="tile:socket:simulator.export_adapter",
            display_name="simulator.export_adapter",
            tile_kind="socket_slot",
            visibility_scope="principal_only",
            owner_namespace="foundups_core",
            parent_tile_id="tile:sys:simulator",
            state="BLUE",
        ),
        "tile:opus:jhr": make_tile(
            tile_id="tile:opus:jhr",
            display_name="Japan Hyperscaler Report (JHR)",
            tile_kind="opus_series",
            visibility_scope="public",
            owner_namespace="foundups_core",
            parent_tile_id=ROOT_TILE_ID,
            state="AMBER",
        ),
        "tile:opus:jhr.004": make_tile(
            tile_id="tile:opus:jhr.004",
            display_name="JHR #004 (Private Draft)",
            tile_kind="opus_item",
            visibility_scope="principal_only",
            owner_namespace="foundups_core",
            parent_tile_id="tile:opus:jhr",
            state="AMBER",
            metadata={"metadata_only": True},
        ),
        "tile:space:hpc": make_tile(
            tile_id="tile:space:hpc",
            display_name="Hasan Piker Coalition (HPC)",
            tile_kind="community_fractal",
            visibility_scope="public",
            owner_namespace="hpc_coalition",
            parent_tile_id=ROOT_TILE_ID,
            state="GREEN",
        ),
        "tile:space:hpc.schumerout": make_tile(
            tile_id="tile:space:hpc.schumerout",
            display_name="SchumerOUT",
            tile_kind="wikitube_stream",
            visibility_scope="public",
            owner_namespace="hpc_coalition",
            parent_tile_id="tile:space:hpc",
            state="GREEN",
        ),
        "tile:space:hpc.schumerout.clip1": make_tile(
            tile_id="tile:space:hpc.schumerout.clip1",
            display_name="SchumerOUT Clip 1",
            tile_kind="wikitube_stream",
            visibility_scope="public",
            owner_namespace="hpc_coalition",
            parent_tile_id="tile:space:hpc.schumerout",
            state="GREEN",
        ),
        "tile:space:hpc.schumerout.clip2": make_tile(
            tile_id="tile:space:hpc.schumerout.clip2",
            display_name="SchumerOUT Clip 2",
            tile_kind="wikitube_stream",
            visibility_scope="public",
            owner_namespace="hpc_coalition",
            parent_tile_id="tile:space:hpc.schumerout",
            state="GREEN",
        ),
        "tile:space:hpc_alt": make_tile(
            tile_id="tile:space:hpc_alt",
            display_name="HPC Neighbor Space",
            tile_kind="community_fractal",
            visibility_scope="public",
            owner_namespace="hpc_neighbor_synthetic",
            parent_tile_id=ROOT_TILE_ID,
            state="BLUE",
        ),
        "tile:space:hpc_alt.item_1": make_tile(
            tile_id="tile:space:hpc_alt.item_1",
            display_name="Neighbor Item 1",
            tile_kind="wikitube_stream",
            visibility_scope="public",
            owner_namespace="hpc_neighbor_synthetic",
            parent_tile_id="tile:space:hpc_alt",
            state="BLUE",
        ),
        "tile:space:hpc_alt.item_2": make_tile(
            tile_id="tile:space:hpc_alt.item_2",
            display_name="Neighbor Item 2",
            tile_kind="wikitube_stream",
            visibility_scope="public",
            owner_namespace="hpc_neighbor_synthetic",
            parent_tile_id="tile:space:hpc_alt",
            state="BLUE",
        ),
        "tile:engine:autopost": make_tile(
            tile_id="tile:engine:autopost",
            display_name="AutoPost",
            tile_kind="licensable_engine",
            visibility_scope="public",
            owner_namespace="foundups_core",
            parent_tile_id=ROOT_TILE_ID,
            state="AMBER",
            evidence_status="claim_requires_independent_evidence",
        ),
    }
    for tid in sorted(tiles):
        pid = tiles[tid]["parent_tile_id"]
        if pid is not None:
            tiles[pid]["children_tile_ids"].append(tid)

    arch_etag = compute_tiles_etag(tiles)
    indices = build_graph_indices(tiles)
    graph = {
        "schema_version": "fractal_tile_graph.v1",
        "generated_at_utc": "2026-11-18T18:00:00+00:00",
        "git_revision": "7432d31e5a68544d2bbab6715f02f64b0b5b6f85",
        "graph_etag": arch_etag,
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


@pytest.fixture(scope="module")
def rsa_key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture(scope="module")
def clerk_owner():
    return importlib.import_module(CLERK_MOD)


@pytest.fixture
def clerk_policy(clerk_owner, rsa_key):
    pem = rsa_key.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("ascii")
    return clerk_owner.ClerkIntakePolicy(
        issuer=ISSUER,
        authorized_parties=(ORIGIN,),
        public_key_pem=pem,
    )


@pytest.fixture
def auth_policy():
    return TileGraphAuthPolicy(
        architect_actors=(ARCHITECT_HANDLE,),
        tenant_actors={"hpc_coalition": (HPC_HANDLE,)},
        admitted_member_actors=(MEMBER_HANDLE,),
    )


@pytest.fixture
def graph_store(tmp_path):
    store = TileGraphStore(tmp_path / "tile_graph.sqlite3", initial_graph=_sample_architect_graph())
    try:
        yield store
    finally:
        store.close()


@pytest.fixture
def patch_client(clerk_policy, auth_policy, graph_store, monkeypatch):
    monkeypatch.setattr(app.state, "clerk_intake_policy", clerk_policy, raising=False)
    monkeypatch.setattr(app.state, "tile_graph_policy", auth_policy, raising=False)
    monkeypatch.setattr(app.state, "tile_graph_store", graph_store, raising=False)
    with TestClient(app) as client:
        yield client


def _bearer_headers(rsa_key, *, sub: str = ARCHITECT_SUB, **extra):
    now = int(time.time())
    token = jwt.encode(
        {
            "iss": ISSUER,
            "azp": ORIGIN,
            "sub": sub,
            "sid": "sess_graphtest",
            "v": 2,
            "iat": now,
            "nbf": now - 5,
            "exp": now + 60,
        },
        rsa_key,
        algorithm="RS256",
    )
    headers = {
        "Authorization": f"Bearer {token}",
        "Origin": ORIGIN,
        "Content-Type": "application/json",
    }
    headers.update(extra)
    return headers


# ---------------------------------------------------------------------------
# Default 503 Gate, Public GET & Architect GET
# ---------------------------------------------------------------------------

class TestTileGraphRoutes:
    """Verify server-side admission on GET /pfmall/tile-graph & /pfmall/source-files and default 503 gating."""

    def test_patch_route_defaults_to_503_when_unconfigured(self, monkeypatch):
        for attr in (
            "clerk_intake_policy",
            "tile_graph_store",
            "tile_graph_policy",
            "member_source_files_path",
            "architect_source_files_path",
        ):
            monkeypatch.delattr(app.state, attr, raising=False)
        with TestClient(app) as client:
            r = client.post("/pfmall/tile-graph/patches", json={})
            assert r.status_code == 503
            assert r.json() == {"detail": "tile_graph_patch_unavailable"}
            assert r.headers["cache-control"] == "no-store"

            arch = client.get("/pfmall/tile-graph", params={"scope": "012_architect"})
            assert arch.status_code == 503
            assert arch.headers["cache-control"] == "private, no-store"

            pub = client.get("/pfmall/tile-graph")
            assert pub.status_code == 503
            assert pub.json() == {"detail": "member_tile_graph_unavailable"}
            assert pub.headers["cache-control"] == "private, no-store"

            src = client.get("/pfmall/source-files")
            assert src.status_code == 503
            assert src.json() == {"detail": "member_source_files_unavailable"}
            assert src.headers["cache-control"] == "private, no-store"

    def test_spoofed_policy_cannot_enable_patch_route(self, monkeypatch):
        monkeypatch.setattr(app.state, "clerk_intake_policy", {"ok": True}, raising=False)
        monkeypatch.setattr(app.state, "tile_graph_policy", {"architect_actors": ["x"]}, raising=False)
        monkeypatch.setattr(app.state, "tile_graph_store", {"db": "fake"}, raising=False)
        with TestClient(app) as client:
            r = client.post("/pfmall/tile-graph/patches", json={})
            assert r.status_code == 503
            assert client.get("/pfmall/tile-graph").status_code == 503
            assert client.get("/pfmall/source-files").status_code == 503

    def test_public_get_etag_and_304_and_architect_auth_gate(
        self, patch_client, clerk_policy, auth_policy, rsa_key, graph_store, tmp_path, monkeypatch
    ):
        # Unauthenticated member reads fail closed 401 with private no-store headers
        unauth_pub = patch_client.get("/pfmall/tile-graph")
        assert unauth_pub.status_code == 401
        assert unauth_pub.headers["cache-control"] == "private, no-store"
        assert patch_client.get("/pfmall/source-files").status_code == 401

        # Authenticated outsider without admission receives 403 member_admission_required
        outsider_pub = patch_client.get(
            "/pfmall/tile-graph",
            headers=_bearer_headers(rsa_key, sub=OUTSIDER_SUB),
        )
        assert outsider_pub.status_code == 403
        assert outsider_pub.json()["detail"] == "member_admission_required"
        assert outsider_pub.headers["cache-control"] == "private, no-store"
        outsider_src = patch_client.get(
            "/pfmall/source-files",
            headers=_bearer_headers(rsa_key, sub=OUTSIDER_SUB),
        )
        assert outsider_src.status_code == 403
        assert outsider_src.json()["detail"] == "member_admission_required"

        # Admitted member receives public_mall projection with ETag / 304 and private no-store headers
        member_headers = _bearer_headers(rsa_key, sub=MEMBER_SUB)
        pub_resp = patch_client.get("/pfmall/tile-graph", headers=member_headers)
        assert pub_resp.status_code == 200
        pub_data = pub_resp.json()
        assert pub_data["scope"] == "public_mall"
        assert "tile:opus:jhr.004" not in pub_data["tiles"]
        pub_etag = pub_data["public_graph_etag"]
        assert pub_resp.headers["etag"] == f'"{pub_etag}"'
        assert pub_resp.headers["cache-control"] == "private, no-store"
        assert "authorization" in pub_resp.headers["vary"].lower()
        assert "origin" in pub_resp.headers["vary"].lower()

        not_mod = patch_client.get(
            "/pfmall/tile-graph",
            headers={**member_headers, "If-None-Match": f'"{pub_etag}"'},
        )
        assert not_mod.status_code == 304
        assert not_mod.headers["cache-control"] == "private, no-store"

        # Same-origin browser GET without explicit Origin succeeds ONLY with Sec-Fetch-Site + Referer
        bare_bearer = {"Authorization": member_headers["Authorization"]}
        with TestClient(app, base_url=ORIGIN) as origin_client:
            missing_origin = origin_client.get("/pfmall/tile-graph", headers=bare_bearer)
            assert missing_origin.status_code == 401
            same_origin = origin_client.get(
                "/pfmall/tile-graph",
                headers={
                    **bare_bearer,
                    "Sec-Fetch-Site": "same-origin",
                    "Referer": f"{ORIGIN}/member/",
                },
            )
            assert same_origin.status_code == 200

        # Admitted non-architect member cannot access 012_architect or submit patches
        assert patch_client.get(
            "/pfmall/tile-graph",
            params={"scope": "012_architect"},
            headers=member_headers,
        ).status_code == 403

        # Architect scope denies unauthenticated (401) and non-architect tenant (403)
        unauth = patch_client.get("/pfmall/tile-graph", params={"scope": "012_architect"})
        assert unauth.status_code == 401
        non_arch = patch_client.get(
            "/pfmall/tile-graph",
            params={"scope": "012_architect"},
            headers=_bearer_headers(rsa_key, sub=HPC_SUB),
        )
        assert non_arch.status_code == 403

        arch = patch_client.get(
            "/pfmall/tile-graph",
            params={"scope": "012_architect"},
            headers=_bearer_headers(rsa_key, sub=ARCHITECT_SUB),
        )
        assert arch.status_code == 200
        assert "tile:opus:jhr.004" in arch.json()["tiles"]
        assert arch.headers["cache-control"] == "private, no-store"

        # GET /pfmall/source-files enforces scope, ETag/304, gzip, and outside-public guard
        pub_src_path = tmp_path / "source_files.public.json"
        arch_src_path = tmp_path / "source_files.architect.json"
        pub_src_path.write_text(json.dumps({"scope": "public_mall", "tiles": {}, "pad": "x" * 1500}), encoding="utf-8")
        arch_src_path.write_text(json.dumps({"scope": "012_architect", "tiles": {}}), encoding="utf-8")
        monkeypatch.setattr(app.state, "member_source_files_path", pub_src_path, raising=False)
        monkeypatch.setattr(app.state, "architect_source_files_path", arch_src_path, raising=False)

        src_ok = patch_client.get("/pfmall/source-files", headers={**member_headers, "Accept-Encoding": "gzip"})
        assert src_ok.status_code == 200
        assert src_ok.json()["scope"] == "public_mall"
        assert src_ok.headers["cache-control"] == "private, no-store"
        assert src_ok.headers.get("content-encoding") == "gzip"
        assert "accept-encoding" in src_ok.headers["vary"].lower()
        assert patch_client.get(
            "/pfmall/source-files",
            headers={**member_headers, "If-None-Match": src_ok.headers["etag"]},
        ).status_code == 304
        assert patch_client.get(
            "/pfmall/source-files",
            params={"scope": "012_architect"},
            headers=member_headers,
        ).status_code == 403
        arch_src = patch_client.get(
            "/pfmall/source-files",
            params={"scope": "012_architect"},
            headers=_bearer_headers(rsa_key, sub=ARCHITECT_SUB),
        )
        assert arch_src.status_code == 200
        assert arch_src.json()["scope"] == "012_architect"

        # Paths inside public/ web root fail closed 503
        bad_public_path = Path(__file__).resolve().parents[4] / "public/member/forbidden_source_files.json"
        monkeypatch.setattr(app.state, "member_source_files_path", bad_public_path, raising=False)
        assert patch_client.get("/pfmall/source-files", headers=member_headers).status_code == 503


# ---------------------------------------------------------------------------
# Atomic Patch Store, Idempotency, Concurrency & Tenant Auth
# ---------------------------------------------------------------------------

class TestAtomicPatchOperations:
    """Verify all 6 patch ops, idempotency, conflict, concurrency, WAL mode, and regeneration."""

    def test_wal_mode_enabled_on_sqlite_file(self, tmp_path):
        db_file = tmp_path / "wal_check.sqlite3"
        store = TileGraphStore(db_file, initial_graph=_sample_architect_graph())
        try:
            conn = sqlite3.connect(str(db_file))
            mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
            conn.close()
            assert mode.lower() == "wal"
        finally:
            store.close()

    def test_idempotent_retry_returns_exact_receipt_and_tamper_409(self, patch_client, rsa_key, graph_store):
        arch_etag = graph_store.get_architect_graph()["graph_etag"]
        patch = {
            "patch_id": "patch-add-blue-001",
            "base_graph_etag": arch_etag,
            "scope": "012_architect",
            "tenant": "foundups_core",
            "op": "ADD_BLUE_TILE",
            "target_tile_id": "tile:sys:simulator",
            "payload": {
                "tile_id": "tile:socket:simulator.live_telemetry",
                "display_name": "simulator.live_telemetry",
                "tile_kind": "socket_slot",
                "visibility_scope": "public",
            },
        }
        headers = _bearer_headers(rsa_key, sub=ARCHITECT_SUB, **{"If-Match": f'"{arch_etag}"'})

        first = patch_client.post("/pfmall/tile-graph/patches", headers=headers, json=patch)
        assert first.status_code == 201
        first_body = first.json()
        assert first_body["status"] == "committed"
        receipt_1 = first_body["receipt"]
        assert receipt_1["actor_id"] == ARCHITECT_HANDLE
        assert receipt_1["new_graph_etag"] != arch_etag

        # Exact retry with SAME patch_id + payload returns 200 and exact original receipt
        retry = patch_client.post("/pfmall/tile-graph/patches", headers=headers, json=patch)
        assert retry.status_code == 200
        retry_body = retry.json()
        assert retry_body["status"] == "idempotent_replay"
        assert retry_body["receipt"] == receipt_1

        # Reusing patch_id with tampered payload returns 409 patch_id_binding_conflict
        tampered = copy.deepcopy(patch)
        tampered["payload"]["display_name"] = "Tampered Name"
        conflict = patch_client.post("/pfmall/tile-graph/patches", headers=headers, json=tampered)
        assert conflict.status_code == 409
        assert conflict.json()["detail"] == "patch_id_binding_conflict"

    def test_concurrent_distinct_patches_serialize_one_commit_one_conflict(self, tmp_path, auth_policy):
        db_file = tmp_path / "concurrent.sqlite3"
        base_graph = _sample_architect_graph()
        base_etag = base_graph["graph_etag"]
        store = TileGraphStore(db_file, initial_graph=base_graph)
        try:
            barrier = threading.Barrier(2)

            def submit(idx: int):
                barrier.wait(timeout=5)
                return store.apply_patch(
                    {
                        "patch_id": f"concurrent-patch-{idx}",
                        "base_graph_etag": base_etag,
                        "scope": "012_architect",
                        "tenant": "foundups_core",
                        "op": "RENAME_DISPLAY_LABEL",
                        "target_tile_id": "tile:sys:simulator",
                        "payload": {"display_name": f"Simulator Concurrent {idx}"},
                    },
                    actor_id=ARCHITECT_HANDLE,
                    policy=auth_policy,
                )

            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(submit, [1, 2]))

            statuses = sorted(r.http_status for r in results)
            assert statuses == [201, 409]
            conflict_res = next(r for r in results if r.http_status == 409)
            assert conflict_res.detail == "etag_conflict"
            assert conflict_res.current_graph_etag is not None
        finally:
            store.close()

    def test_tenant_auth_boundaries_and_neighbor_isolation(self, patch_client, rsa_key, graph_store):
        pub_etag = graph_store.get_public_graph()["public_graph_etag"]

        # Outsider is rejected 403
        outsider_patch = {
            "patch_id": "patch-outsider-01",
            "base_graph_etag": pub_etag,
            "scope": "public_mall",
            "tenant": "hpc_coalition",
            "op": "REORDER_CHILDREN",
            "target_tile_id": "tile:space:hpc.schumerout",
            "payload": {
                "children_tile_ids": [
                    "tile:space:hpc.schumerout.clip2",
                    "tile:space:hpc.schumerout.clip1",
                ]
            },
        }
        r_out = patch_client.post(
            "/pfmall/tile-graph/patches",
            headers=_bearer_headers(rsa_key, sub=OUTSIDER_SUB),
            json=outsider_patch,
        )
        assert r_out.status_code == 403

        # HPC actor CANNOT mutate neighbor space tile:space:hpc_alt (403)
        cross_patch = copy.deepcopy(outsider_patch)
        cross_patch["patch_id"] = "patch-hpc-cross-neighbor"
        cross_patch["target_tile_id"] = "tile:space:hpc_alt"
        cross_patch["payload"] = {
            "children_tile_ids": ["tile:space:hpc_alt.item_2", "tile:space:hpc_alt.item_1"]
        }
        r_cross = patch_client.post(
            "/pfmall/tile-graph/patches",
            headers=_bearer_headers(rsa_key, sub=HPC_SUB),
            json=cross_patch,
        )
        assert r_cross.status_code == 403

        # HPC actor CANNOT touch principal_only tile or 012_architect scope
        priv_patch = {
            "patch_id": "patch-hpc-private-01",
            "base_graph_etag": pub_etag,
            "scope": "public_mall",
            "tenant": "foundups_core",
            "op": "UPDATE_PRIVATE_NOTE",
            "target_tile_id": "tile:opus:jhr.004",
            "payload": {"note": "unauthorized note"},
        }
        r_priv = patch_client.post(
            "/pfmall/tile-graph/patches",
            headers=_bearer_headers(rsa_key, sub=HPC_SUB),
            json=priv_patch,
        )
        assert r_priv.status_code == 403

        # HPC actor CAN reorder its own tile:space:hpc.schumerout; neighbor hpc_alt keeps order
        r_ok = patch_client.post(
            "/pfmall/tile-graph/patches",
            headers=_bearer_headers(rsa_key, sub=HPC_SUB),
            json=outsider_patch,
        )
        assert r_ok.status_code == 201
        pub_after = patch_client.get("/pfmall/tile-graph", headers=_bearer_headers(rsa_key, sub=MEMBER_SUB)).json()
        assert pub_after["tiles"]["tile:space:hpc.schumerout"]["children_tile_ids"] == [
            "tile:space:hpc.schumerout.clip2",
            "tile:space:hpc.schumerout.clip1",
        ]
        assert pub_after["tiles"]["tile:space:hpc_alt"]["children_tile_ids"] == [
            "tile:space:hpc_alt.item_1",
            "tile:space:hpc_alt.item_2",
        ]

    def test_private_note_patch_leaves_public_etag_unchanged(self, patch_client, rsa_key, graph_store):
        before_arch_etag = graph_store.get_architect_graph()["graph_etag"]
        before_pub_etag = graph_store.get_public_graph()["public_graph_etag"]

        r = patch_client.post(
            "/pfmall/tile-graph/patches",
            headers=_bearer_headers(rsa_key, sub=ARCHITECT_SUB),
            json={
                "patch_id": "patch-private-note-01",
                "base_graph_etag": before_arch_etag,
                "scope": "012_architect",
                "tenant": "foundups_core",
                "op": "UPDATE_PRIVATE_NOTE",
                "target_tile_id": "tile:sys:simulator",
                "payload": {"note": "012 verified export_adapter plan"},
            },
        )
        assert r.status_code == 201
        assert r.json()["receipt"]["new_graph_etag"] != before_arch_etag
        assert r.json()["receipt"]["public_graph_etag"] == before_pub_etag
        pub_graph = patch_client.get("/pfmall/tile-graph", headers=_bearer_headers(rsa_key, sub=MEMBER_SUB)).json()
        assert pub_graph["public_graph_etag"] == before_pub_etag
        assert "private_notes" not in pub_graph["tiles"]["tile:sys:simulator"]

    def test_wire_hygiene_wsp71_and_if_match_rejections(self, patch_client, rsa_key, graph_store, clerk_owner, monkeypatch):
        arch_etag = graph_store.get_architect_graph()["graph_etag"]

        # Duplicate JSON key or invalid JSON never invokes _verify_session
        calls = []
        monkeypatch.setattr(clerk_owner, "_verify_session", lambda *args: calls.append(1))
        bad_raw = b'{"patch_id":"a","patch_id":"b"}'
        r_dup = patch_client.post(
            "/pfmall/tile-graph/patches",
            headers=_bearer_headers(rsa_key, sub=ARCHITECT_SUB),
            content=bad_raw,
        )
        assert r_dup.status_code == 400
        assert calls == []

        # WSP 71 secret/local path rejected before verification
        leak_patch = {
            "patch_id": "patch-wsp71-leak",
            "base_graph_etag": arch_etag,
            "scope": "012_architect",
            "tenant": "foundups_core",
            "op": "RENAME_DISPLAY_LABEL",
            "target_tile_id": "tile:sys:simulator",
            "payload": {"display_name": "O:/Foundups-Agent/secret"},
        }
        r_leak = patch_client.post(
            "/pfmall/tile-graph/patches",
            headers=_bearer_headers(rsa_key, sub=ARCHITECT_SUB),
            json=leak_patch,
        )
        assert r_leak.status_code == 400
        assert r_leak.json()["detail"] == "wsp71_secret_or_path_rejected"
        assert calls == []

        # If-Match header mismatch rejected 400
        valid_patch = {
            "patch_id": "patch-if-match-check",
            "base_graph_etag": arch_etag,
            "scope": "012_architect",
            "tenant": "foundups_core",
            "op": "RENAME_DISPLAY_LABEL",
            "target_tile_id": "tile:sys:simulator",
            "payload": {"display_name": "Simulator Renamed"},
        }
        r_mismatch = patch_client.post(
            "/pfmall/tile-graph/patches",
            headers=_bearer_headers(rsa_key, sub=ARCHITECT_SUB, **{"If-Match": '"0' + "0" * 63 + '"'}),
            json=valid_patch,
        )
        assert r_mismatch.status_code == 400
        assert r_mismatch.json()["detail"] == "if_match_mismatch"

    def test_wire_socket_promote_state_and_regeneration_survival(self, tmp_path, auth_policy):
        db_file = tmp_path / "regen.sqlite3"
        base1 = _sample_architect_graph()
        store = TileGraphStore(db_file, initial_graph=base1)
        try:
            etag1 = store.get_architect_graph()["graph_etag"]
            r1 = store.apply_patch(
                {
                    "patch_id": "regen-wire-01",
                    "base_graph_etag": etag1,
                    "scope": "012_architect",
                    "tenant": "foundups_core",
                    "op": "WIRE_SOCKET_EDGE",
                    "target_tile_id": "tile:socket:simulator.export_adapter",
                    "payload": {
                        "edge_field": "reusable_candidates",
                        "to_tile_id": "tile:space:hpc",
                    },
                },
                actor_id=ARCHITECT_HANDLE,
                policy=auth_policy,
            )
            assert r1.http_status == 201
            etag2 = r1.receipt["new_graph_etag"]

            r2 = store.apply_patch(
                {
                    "patch_id": "regen-promote-02",
                    "base_graph_etag": etag2,
                    "scope": "012_architect",
                    "tenant": "foundups_core",
                    "op": "PROMOTE_STATE",
                    "target_tile_id": "tile:socket:simulator.export_adapter",
                    "payload": {"state": "GREEN", "reason": "wired to exporter"},
                },
                actor_id=ARCHITECT_HANDLE,
                policy=auth_policy,
            )
            assert r2.http_status == 201
            etag3 = r2.receipt["new_graph_etag"]

            r3 = store.apply_patch(
                {
                    "patch_id": "regen-reorder-03",
                    "base_graph_etag": etag3,
                    "scope": "012_architect",
                    "tenant": "foundups_core",
                    "op": "REORDER_CHILDREN",
                    "target_tile_id": "tile:space:hpc.schumerout",
                    "payload": {
                        "children_tile_ids": [
                            "tile:space:hpc.schumerout.clip2",
                            "tile:space:hpc.schumerout.clip1",
                        ]
                    },
                },
                actor_id=ARCHITECT_HANDLE,
                policy=auth_policy,
            )
            assert r3.http_status == 201
        finally:
            store.close()

        # Reopen store on same SQLite DB and regenerate from an updated catalog base
        fresh_base = _sample_architect_graph()
        fresh_base["tiles"]["tile:engine:autopost"]["display_name"] = "AutoPost (Catalog Updated)"
        reopened = TileGraphStore(db_file)
        try:
            replayed = reopened.regenerate_from_catalog(fresh_base)
            assert replayed["tiles"]["tile:engine:autopost"]["display_name"] == "AutoPost (Catalog Updated)"
            sock = replayed["tiles"]["tile:socket:simulator.export_adapter"]
            assert "tile:space:hpc" in sock["dag_edges"]["reusable_candidates"]
            assert sock["lifecycle"]["state"] == "GREEN"
            assert replayed["tiles"]["tile:space:hpc.schumerout"]["children_tile_ids"] == [
                "tile:space:hpc.schumerout.clip2",
                "tile:space:hpc.schumerout.clip1",
            ]
            assert len(reopened.list_accepted_patches()) == 3
        finally:
            reopened.close()

    def test_cross_actor_patch_id_conflict_and_invalid_mutations_rollback(self, patch_client, rsa_key, graph_store):
        pub_etag = graph_store.get_public_graph()["public_graph_etag"]

        # Architect commits an HPC patch first
        patch = {
            "patch_id": "cross-actor-id-01",
            "base_graph_etag": pub_etag,
            "scope": "public_mall",
            "tenant": "hpc_coalition",
            "op": "RENAME_DISPLAY_LABEL",
            "target_tile_id": "tile:space:hpc",
            "payload": {"display_name": "HPC Coalition Renamed"},
        }
        r1 = patch_client.post(
            "/pfmall/tile-graph/patches",
            headers=_bearer_headers(rsa_key, sub=ARCHITECT_SUB),
            json=patch,
        )
        assert r1.status_code == 201

        # Different actor reusing same patch_id + identical payload must receive 409, never 200 replay
        r2 = patch_client.post(
            "/pfmall/tile-graph/patches",
            headers=_bearer_headers(rsa_key, sub=HPC_SUB),
            json=patch,
        )
        assert r2.status_code == 409
        assert r2.json()["detail"] == "patch_id_binding_conflict"

        # Invalid REORDER_CHILDREN (missing child) and self-loop edge reject 400 without mutating snapshot
        cur_pub_etag = graph_store.get_public_graph()["public_graph_etag"]
        r_bad_reorder = patch_client.post(
            "/pfmall/tile-graph/patches",
            headers=_bearer_headers(rsa_key, sub=HPC_SUB),
            json={
                "patch_id": "bad-reorder-01",
                "base_graph_etag": cur_pub_etag,
                "scope": "public_mall",
                "tenant": "hpc_coalition",
                "op": "REORDER_CHILDREN",
                "target_tile_id": "tile:space:hpc.schumerout",
                "payload": {"children_tile_ids": ["tile:space:hpc.schumerout.clip1"]},
            },
        )
        assert r_bad_reorder.status_code == 400

        r_self_loop = patch_client.post(
            "/pfmall/tile-graph/patches",
            headers=_bearer_headers(rsa_key, sub=HPC_SUB),
            json={
                "patch_id": "bad-self-loop-01",
                "base_graph_etag": cur_pub_etag,
                "scope": "public_mall",
                "tenant": "hpc_coalition",
                "op": "WIRE_SOCKET_EDGE",
                "target_tile_id": "tile:space:hpc",
                "payload": {"edge_field": "cross_links", "to_tile_id": "tile:space:hpc"},
            },
        )
        assert r_self_loop.status_code == 400
        assert graph_store.get_public_graph()["public_graph_etag"] == cur_pub_etag

    def test_static_public_fallback_get_when_store_unconfigured(
        self, monkeypatch, clerk_policy, auth_policy, rsa_key
    ):
        for attr in ("clerk_intake_policy", "tile_graph_store", "tile_graph_policy"):
            monkeypatch.delattr(app.state, attr, raising=False)
        with TestClient(app) as unconf_client:
            assert unconf_client.get("/pfmall/tile-graph").status_code == 503
            assert unconf_client.get("/pfmall/source-files").status_code == 503

        monkeypatch.setattr(app.state, "clerk_intake_policy", clerk_policy, raising=False)
        monkeypatch.setattr(app.state, "tile_graph_policy", auth_policy, raising=False)
        member_headers = _bearer_headers(rsa_key, sub=MEMBER_SUB)
        with TestClient(app) as client:
            assert client.get("/pfmall/tile-graph").status_code == 401
            r = client.get("/pfmall/tile-graph", headers=member_headers)
            assert r.status_code == 200
            data = r.json()
            assert data["scope"] == "public_mall"
            etag = data["public_graph_etag"]
            assert r.headers["etag"] == f'"{etag}"'
            assert r.headers["cache-control"] == "private, no-store"
            not_mod = client.get(
                "/pfmall/tile-graph",
                headers={**member_headers, "If-None-Match": etag},
            )
            assert not_mod.status_code == 304
            bad_scope = client.get("/pfmall/tile-graph", params={"scope": "unknown_scope"})
            assert bad_scope.status_code == 400

    def test_typed_relationship_wire_patch_survives_regeneration(self, patch_client, rsa_key, graph_store):
        base_etag = graph_store.get_public_graph()["public_graph_etag"]
        r = patch_client.post(
            "/pfmall/tile-graph/patches",
            headers=_bearer_headers(rsa_key, sub=ARCHITECT_SUB),
            json={
                "patch_id": "wire-typed-evaluates-01",
                "base_graph_etag": base_etag,
                "scope": "public_mall",
                "tenant": "foundups_core",
                "op": "WIRE_SOCKET_EDGE",
                "target_tile_id": "tile:sys:simulator",
                "payload": {"edge_field": "evaluates", "to_tile_id": "tile:space:hpc"},
            },
        )
        assert r.status_code == 201
        graph_store.regenerate_from_catalog(_sample_architect_graph())
        pub_after = graph_store.get_public_graph()
        assert "tile:space:hpc" in pub_after["tiles"]["tile:sys:simulator"]["dag_edges"]["evaluates"]


# ---------------------------------------------------------------------------
# Fail-Closed Trusted Proxy & Local Admission Matrix Security
# ---------------------------------------------------------------------------

class TestTrustedProxySchemeHandling:
    """Verify reverse-proxy X-Forwarded-Proto handling fails closed by default and verifies peer trust."""

    _PROD_ORIGIN = "https://foundups.com"
    _PROD_HTTP_BASE = "http://foundups.com"

    @pytest.fixture
    def prod_clerk_policy(self, clerk_owner, rsa_key):
        pem = rsa_key.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode("ascii")
        return clerk_owner.ClerkIntakePolicy(
            issuer=ISSUER,
            authorized_parties=(self._PROD_ORIGIN,),
            public_key_pem=pem,
        )

    @staticmethod
    def _prod_token(rsa_key, *, sub: str = MEMBER_SUB, azp: str = "https://foundups.com") -> str:
        now = int(time.time())
        return jwt.encode(
            {
                "iss": ISSUER,
                "azp": azp,
                "sub": sub,
                "sid": "sess_proxytest",
                "v": 2,
                "iat": now,
                "nbf": now - 5,
                "exp": now + 60,
            },
            rsa_key,
            algorithm="RS256",
        )

    @staticmethod
    def _clear_proxy_state(monkeypatch):
        for attr in ("trusted_proxy_policy", "trust_proxy_headers", "trusted_proxy_hosts"):
            monkeypatch.delattr(app.state, attr, raising=False)

    def test_untrusted_x_forwarded_proto_spoofing_fails_closed_401(
        self, prod_clerk_policy, auth_policy, graph_store, rsa_key, tmp_path, monkeypatch
    ):
        self._clear_proxy_state(monkeypatch)
        pub_src_path = tmp_path / "source_files.public.json"
        pub_src_path.write_text(json.dumps({"scope": "public_mall", "tiles": {}}), encoding="utf-8")
        monkeypatch.setattr(app.state, "clerk_intake_policy", prod_clerk_policy, raising=False)
        monkeypatch.setattr(app.state, "tile_graph_policy", auth_policy, raising=False)
        monkeypatch.setattr(app.state, "tile_graph_store", graph_store, raising=False)
        monkeypatch.setattr(app.state, "member_source_files_path", pub_src_path, raising=False)

        spoof_headers = {
            "Authorization": f"Bearer {self._prod_token(rsa_key, sub=MEMBER_SUB)}",
            "Sec-Fetch-Site": "same-origin",
            "Referer": f"{self._PROD_ORIGIN}/member/",
            "X-Forwarded-Proto": "https",
        }

        # Default OFF: X-Forwarded-Proto ignored, http != https -> 401
        with TestClient(app, base_url=self._PROD_HTTP_BASE) as http_client:
            for endpoint in ("/pfmall/tile-graph", "/pfmall/source-files"):
                resp = http_client.get(endpoint, headers=spoof_headers)
                assert resp.status_code == 401
                assert resp.headers["cache-control"] == "private, no-store"
                assert "authorization" in resp.headers["vary"].lower()
                assert "origin" in resp.headers["vary"].lower()

            # Non-bool truthy flag, spoofed policy dict, missing hosts, bare string host, untrusted peer all fail 401
            bad_configs = [
                {"trust_proxy_headers": "true", "trusted_proxy_hosts": ("*",)},
                {"trusted_proxy_policy": {"trust_proxy_headers": True, "trusted_proxy_hosts": ("*",)}},
                {"trust_proxy_headers": True},
                {"trust_proxy_headers": True, "trusted_proxy_hosts": "testclient"},
                {"trust_proxy_headers": True, "trusted_proxy_hosts": ("10.0.0.99",)},
                {"trusted_proxy_policy": TrustedProxyPolicy(trust_proxy_headers=True, trusted_proxy_hosts=("10.0.0.99",))},
                {"trusted_proxy_policy": TrustedProxyPolicy(trust_proxy_headers=False, trusted_proxy_hosts=("*",))},
            ]
            for cfg in bad_configs:
                self._clear_proxy_state(monkeypatch)
                for k, v in cfg.items():
                    monkeypatch.setattr(app.state, k, v, raising=False)
                r_graph = http_client.get("/pfmall/tile-graph", headers=spoof_headers)
                r_src = http_client.get("/pfmall/source-files", headers=spoof_headers)
                assert r_graph.status_code == 401
                assert r_src.status_code == 401

    @pytest.mark.parametrize(
        "proxy_cfg",
        [
            {"trusted_proxy_policy": TrustedProxyPolicy(trust_proxy_headers=True, trusted_proxy_hosts=("testclient",))},
            {"trust_proxy_headers": True, "trusted_proxy_hosts": ("*",)},
            {"trust_proxy_headers": True, "trusted_proxy_hosts": "*"},
        ],
    )
    def test_configured_trusted_proxy_same_origin_enforces_admission_and_gzip(
        self, proxy_cfg, prod_clerk_policy, auth_policy, graph_store, rsa_key, tmp_path, monkeypatch
    ):
        self._clear_proxy_state(monkeypatch)
        pub_src_path = tmp_path / "source_files.public.json"
        arch_src_path = tmp_path / "source_files.architect.json"
        pub_src_path.write_text(
            json.dumps({"scope": "public_mall", "tiles": {}, "pad": "x" * 1600}),
            encoding="utf-8",
        )
        arch_src_path.write_text(json.dumps({"scope": "012_architect", "tiles": {}}), encoding="utf-8")

        monkeypatch.setattr(app.state, "clerk_intake_policy", prod_clerk_policy, raising=False)
        monkeypatch.setattr(app.state, "tile_graph_policy", auth_policy, raising=False)
        monkeypatch.setattr(app.state, "tile_graph_store", graph_store, raising=False)
        monkeypatch.setattr(app.state, "member_source_files_path", pub_src_path, raising=False)
        monkeypatch.setattr(app.state, "architect_source_files_path", arch_src_path, raising=False)
        for k, v in proxy_cfg.items():
            monkeypatch.setattr(app.state, k, v, raising=False)

        member_hdrs = {
            "Authorization": f"Bearer {self._prod_token(rsa_key, sub=MEMBER_SUB)}",
            "Sec-Fetch-Site": "same-origin",
            "Referer": f"{self._PROD_ORIGIN}/member/",
            "X-Forwarded-Proto": "https",
            "Accept-Encoding": "gzip",
        }
        outsider_hdrs = {
            **member_hdrs,
            "Authorization": f"Bearer {self._prod_token(rsa_key, sub=OUTSIDER_SUB)}",
        }
        architect_hdrs = {
            **member_hdrs,
            "Authorization": f"Bearer {self._prod_token(rsa_key, sub=ARCHITECT_SUB)}",
        }

        with TestClient(app, base_url=self._PROD_HTTP_BASE) as http_client:
            # Admitted member succeeds with gzip + private, no-store
            for endpoint in ("/pfmall/tile-graph", "/pfmall/source-files"):
                ok_resp = http_client.get(endpoint, headers=member_hdrs)
                assert ok_resp.status_code == 200
                assert ok_resp.headers.get("content-encoding") == "gzip"
                assert ok_resp.headers["cache-control"] == "private, no-store"
                assert "authorization" in ok_resp.headers["vary"].lower()
                assert "origin" in ok_resp.headers["vary"].lower()
                assert "accept-encoding" in ok_resp.headers["vary"].lower()

                # Unauthenticated / missing Sec-Fetch-Site / wrong Referer / wrong azp -> 401
                assert http_client.get(endpoint, headers={"X-Forwarded-Proto": "https"}).status_code == 401
                assert http_client.get(
                    endpoint,
                    headers={
                        "Authorization": member_hdrs["Authorization"],
                        "Referer": f"{self._PROD_ORIGIN}/member/",
                        "X-Forwarded-Proto": "https",
                    },
                ).status_code == 401
                assert http_client.get(
                    endpoint,
                    headers={
                        **member_hdrs,
                        "Referer": "https://evil.example.com/member/",
                    },
                ).status_code == 401
                assert http_client.get(
                    endpoint,
                    headers={
                        **member_hdrs,
                        "Authorization": f"Bearer {self._prod_token(rsa_key, sub=MEMBER_SUB, azp='https://other.example.com')}",
                    },
                ).status_code == 401

                # Outsider -> 403 member_admission_required
                out_resp = http_client.get(endpoint, headers=outsider_hdrs)
                assert out_resp.status_code == 403
                assert out_resp.json()["detail"] == "member_admission_required"
                assert out_resp.headers["cache-control"] == "private, no-store"

                # Admitted non-architect member on 012_architect -> 403 forbidden
                arch_deny = http_client.get(endpoint, params={"scope": "012_architect"}, headers=member_hdrs)
                assert arch_deny.status_code == 403
                assert arch_deny.json()["detail"] == "forbidden"
                assert arch_deny.headers["cache-control"] == "private, no-store"

                # Architect on 012_architect succeeds -> 200
                arch_ok = http_client.get(endpoint, params={"scope": "012_architect"}, headers=architect_hdrs)
                assert arch_ok.status_code == 200
                assert arch_ok.headers["cache-control"] == "private, no-store"

            # First hop normalization: "https, http" -> https (200); "http, https" or invalid scheme -> 401
            multi_ok = http_client.get(
                "/pfmall/tile-graph",
                headers={**member_hdrs, "X-Forwarded-Proto": "HTTPS, http"},
            )
            assert multi_ok.status_code == 200

            multi_http = http_client.get(
                "/pfmall/tile-graph",
                headers={**member_hdrs, "X-Forwarded-Proto": "http, https"},
            )
            assert multi_http.status_code == 401

            bad_proto = http_client.get(
                "/pfmall/tile-graph",
                headers={**member_hdrs, "X-Forwarded-Proto": "ftp"},
            )
            assert bad_proto.status_code == 401

        # Even over https:// ASGI base_url, trusted proxy X-Forwarded-Proto: http fails closed 401
        with TestClient(app, base_url=self._PROD_ORIGIN) as https_client:
            downgrade = https_client.get(
                "/pfmall/tile-graph",
                headers={**member_hdrs, "X-Forwarded-Proto": "http"},
            )
            assert downgrade.status_code == 401

    def test_duplicate_security_headers_rejected_400_and_304_gated_behind_auth(
        self, prod_clerk_policy, auth_policy, graph_store, rsa_key, tmp_path, monkeypatch
    ):
        self._clear_proxy_state(monkeypatch)
        pub_src_path = tmp_path / "source_files.public.json"
        pub_src_path.write_text(json.dumps({"scope": "public_mall", "tiles": {}}), encoding="utf-8")
        monkeypatch.setattr(app.state, "clerk_intake_policy", prod_clerk_policy, raising=False)
        monkeypatch.setattr(app.state, "tile_graph_policy", auth_policy, raising=False)
        monkeypatch.setattr(app.state, "tile_graph_store", graph_store, raising=False)
        monkeypatch.setattr(app.state, "member_source_files_path", pub_src_path, raising=False)
        monkeypatch.setattr(
            app.state,
            "trusted_proxy_policy",
            TrustedProxyPolicy(trust_proxy_headers=True, trusted_proxy_hosts=("testclient",)),
            raising=False,
        )

        tok = self._prod_token(rsa_key, sub=MEMBER_SUB)
        base_hdrs = [
            ("Authorization", f"Bearer {tok}"),
            ("Origin", self._PROD_ORIGIN),
        ]

        with TestClient(app, base_url=self._PROD_HTTP_BASE) as http_client:
            # Duplicate Authorization / Origin / X-Forwarded-Proto -> 400 on GETs
            for dup_name, dup_val in (
                ("Authorization", f"Bearer {tok}"),
                ("Origin", self._PROD_ORIGIN),
                ("X-Forwarded-Proto", "https"),
            ):
                hdrs = list(base_hdrs) + [("X-Forwarded-Proto", "https"), (dup_name, dup_val)]
                for endpoint in ("/pfmall/tile-graph", "/pfmall/source-files"):
                    r_dup = http_client.get(endpoint, headers=hdrs)
                    assert r_dup.status_code == 400
                    assert r_dup.json() == {"detail": "invalid_request"}
                    assert r_dup.headers["cache-control"] == "private, no-store"

            # Duplicate X-Forwarded-Proto -> 400 on POST /pfmall/tile-graph/patches
            post_hdrs = [
                ("Authorization", f"Bearer {tok}"),
                ("Origin", self._PROD_ORIGIN),
                ("Content-Type", "application/json"),
                ("X-Forwarded-Proto", "https"),
                ("X-Forwarded-Proto", "http"),
            ]
            r_post_dup = http_client.post("/pfmall/tile-graph/patches", headers=post_hdrs, content=b"{}")
            assert r_post_dup.status_code == 400
            assert r_post_dup.json() == {"detail": "invalid_request"}
            assert r_post_dup.headers["cache-control"] == "no-store"

            # Auth + scope run strictly BEFORE store/disk lookup and 304 If-None-Match gating
            graph_resp = http_client.get("/pfmall/tile-graph", headers=dict(base_hdrs))
            src_resp = http_client.get("/pfmall/source-files", headers=dict(base_hdrs))
            assert graph_resp.status_code == 200
            assert src_resp.status_code == 200
            graph_etag = graph_resp.headers["etag"]
            src_etag = src_resp.headers["etag"]

            for endpoint, etag in (("/pfmall/tile-graph", graph_etag), ("/pfmall/source-files", src_etag)):
                # Unauth with If-None-Match -> 401 (never 304)
                assert http_client.get(endpoint, headers={"If-None-Match": etag}).status_code == 401
                assert http_client.get(endpoint, headers={"If-None-Match": "*"}).status_code == 401
                # Outsider with If-None-Match -> 403 (never 304)
                out_tok = self._prod_token(rsa_key, sub=OUTSIDER_SUB)
                assert http_client.get(
                    endpoint,
                    headers={"Authorization": f"Bearer {out_tok}", "Origin": self._PROD_ORIGIN, "If-None-Match": etag},
                ).status_code == 403
                # Member on 012_architect with If-None-Match -> 403 (never 304)
                assert http_client.get(
                    endpoint,
                    params={"scope": "012_architect"},
                    headers={**dict(base_hdrs), "If-None-Match": "*"},
                ).status_code == 403
                # Admitted member on public_mall -> 304
                r_304 = http_client.get(endpoint, headers={**dict(base_hdrs), "If-None-Match": etag})
                assert r_304.status_code == 304
                assert r_304.headers["cache-control"] == "private, no-store"
                assert "authorization" in r_304.headers["vary"].lower()
                assert "origin" in r_304.headers["vary"].lower()

    def test_asgi_direct_peer_ip_allowlist_enforcement(
        self, prod_clerk_policy, auth_policy, graph_store, rsa_key, monkeypatch
    ):
        self._clear_proxy_state(monkeypatch)
        monkeypatch.setattr(app.state, "clerk_intake_policy", prod_clerk_policy, raising=False)
        monkeypatch.setattr(app.state, "tile_graph_policy", auth_policy, raising=False)
        monkeypatch.setattr(app.state, "tile_graph_store", graph_store, raising=False)
        monkeypatch.setattr(
            app.state,
            "trusted_proxy_policy",
            TrustedProxyPolicy(trust_proxy_headers=True, trusted_proxy_hosts=("127.0.0.1", "::1")),
            raising=False,
        )

        hdrs = {
            "Authorization": f"Bearer {self._prod_token(rsa_key, sub=MEMBER_SUB)}",
            "Sec-Fetch-Site": "same-origin",
            "Referer": f"{self._PROD_ORIGIN}/member/",
            "X-Forwarded-Proto": "https",
        }

        async def _probe(peer_ip: str) -> int:
            transport = httpx.ASGITransport(app=app, client=(peer_ip, 54321))
            async with httpx.AsyncClient(transport=transport, base_url=self._PROD_HTTP_BASE) as ac:
                resp = await ac.get("/pfmall/tile-graph", headers=hdrs)
                return resp.status_code

        assert asyncio.run(_probe("127.0.0.1")) == 200
        assert asyncio.run(_probe("0:0:0:0:0:0:0:1")) == 200
        assert asyncio.run(_probe("203.0.113.5")) == 401
