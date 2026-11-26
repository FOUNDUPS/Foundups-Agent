#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Durable SQLite Atomic Patch Store for PlayFoundups Mall Fractal Tile Graph (§9.5).

Provides serialized, crash-safe graph mutations using SQLite WAL mode,
``BEGIN IMMEDIATE`` transactions, and ``threading.RLock``. Enforces tenant
authorization, ``patch_id`` payload-hash idempotency, strict ``base_graph_etag``
optimistic concurrency, containment acyclicity, DAG reference integrity,
and WSP 71 secret/local-path leak prevention prior to commit.
"""

from __future__ import annotations

import copy
import json
import re
import sqlite3
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from types import MappingProxyType
from typing import Any, Dict, List, Mapping, Optional, Tuple

from modules.foundups.pfmall.fractal_tile_graph import (
    DAG_TILE_EDGE_FIELDS,
    SCHEMA_VERSION,
    TILE_ID_RE,
    VALID_STATES,
    VALID_TILE_KINDS,
    build_graph_indices,
    compute_tiles_etag,
    make_tile,
    project_public_tile_graph,
    scan_wsp71_leaks,
    sha256_canonical,
    state_label,
    validate_tile_graph,
)

VALID_PATCH_OPS = frozenset({
    "ADD_BLUE_TILE",
    "WIRE_SOCKET_EDGE",
    "RENAME_DISPLAY_LABEL",
    "PROMOTE_STATE",
    "REORDER_CHILDREN",
    "UPDATE_PRIVATE_NOTE",
})

_PATCH_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{4,128}$")
_TENANT_RE = re.compile(r"^[a-z][a-z0-9_]{1,63}$")
_ETAG_RE = re.compile(r"^[0-9a-f]{64}$")
_PATCH_SCHEMA_PATH = Path(__file__).parent / "schemas" / "tile_graph_patch.schema.json"
_CACHED_PATCH_SCHEMA: Optional[Dict[str, Any]] = None


def _load_patch_schema() -> Dict[str, Any]:
    global _CACHED_PATCH_SCHEMA
    if _CACHED_PATCH_SCHEMA is None:
        _CACHED_PATCH_SCHEMA = json.loads(_PATCH_SCHEMA_PATH.read_text(encoding="utf-8"))
    return _CACHED_PATCH_SCHEMA


def _valid_actor_handle(value: object) -> bool:
    return (
        type(value) is str
        and value.isascii()
        and 1 <= len(value) <= 128
        and not any(c.isspace() for c in value)
    )


@dataclass(frozen=True, slots=True)
class TileGraphAuthPolicy:
    """Trusted server authorization policy, never constructed from HTTP input."""

    architect_actors: Tuple[str, ...]
    tenant_actors: Mapping[str, Tuple[str, ...]] = field(default_factory=dict)
    admitted_member_actors: Tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if (
            type(self.architect_actors) is not tuple
            or not all(_valid_actor_handle(a) for a in self.architect_actors)
            or len(set(self.architect_actors)) != len(self.architect_actors)
        ):
            raise ValueError("invalid_tile_graph_auth_policy")
        if (
            type(self.admitted_member_actors) is not tuple
            or not all(_valid_actor_handle(a) for a in self.admitted_member_actors)
            or len(set(self.admitted_member_actors)) != len(self.admitted_member_actors)
        ):
            raise ValueError("invalid_tile_graph_auth_policy")
        if not isinstance(self.tenant_actors, Mapping):
            raise ValueError("invalid_tile_graph_auth_policy")
        normalized: Dict[str, Tuple[str, ...]] = {}
        for tenant, actors in self.tenant_actors.items():
            if (
                type(tenant) is not str
                or not _TENANT_RE.match(tenant)
                or type(actors) is not tuple
                or not all(_valid_actor_handle(a) for a in actors)
                or len(set(actors)) != len(actors)
            ):
                raise ValueError("invalid_tile_graph_auth_policy")
            normalized[tenant] = actors
        object.__setattr__(self, "tenant_actors", MappingProxyType(normalized))

    def is_architect(self, actor_id: str) -> bool:
        return actor_id in self.architect_actors

    def is_tenant_actor(self, actor_id: str, tenant: str) -> bool:
        return actor_id in self.tenant_actors.get(tenant, ())

    def is_admitted_member(self, actor_id: str) -> bool:
        if not _valid_actor_handle(actor_id):
            return False
        if actor_id in self.architect_actors or actor_id in self.admitted_member_actors:
            return True
        return any(actor_id in actors for actors in self.tenant_actors.values())


@dataclass(frozen=True, slots=True)
class PatchResult:
    """Deterministic outcome of a tile graph patch attempt."""

    status: str  # committed | idempotent_replay | conflict | forbidden | invalid
    http_status: int  # 201 | 200 | 409 | 403 | 400
    receipt: Optional[Dict[str, Any]] = None
    detail: Optional[str] = None
    current_graph_etag: Optional[str] = None


def validate_patch_structure(patch_request: Mapping[str, Any]) -> Optional[str]:
    """Validate patch JSON structure against ``tile_graph_patch.schema.json``."""
    if not isinstance(patch_request, Mapping):
        return "patch_must_be_object"
    allowed_top = {"patch_id", "base_graph_etag", "scope", "tenant", "op", "target_tile_id", "payload"}
    if set(patch_request.keys()) - allowed_top:
        return "unexpected_patch_fields"
    for req in ("patch_id", "base_graph_etag", "tenant", "op", "target_tile_id", "payload"):
        if req not in patch_request:
            return f"missing_{req}"

    patch_id = patch_request["patch_id"]
    base_etag = patch_request["base_graph_etag"]
    scope = patch_request.get("scope", "public_mall")
    tenant = patch_request["tenant"]
    op = patch_request["op"]
    target_tile_id = patch_request["target_tile_id"]
    payload = patch_request["payload"]

    if type(patch_id) is not str or not _PATCH_ID_RE.match(patch_id):
        return "invalid_patch_id"
    if type(base_etag) is not str or not _ETAG_RE.match(base_etag):
        return "invalid_base_graph_etag"
    if type(scope) is not str or scope not in {"012_architect", "public_mall"}:
        return "invalid_scope"
    if type(tenant) is not str or not _TENANT_RE.match(tenant):
        return "invalid_tenant"
    if type(op) is not str or op not in VALID_PATCH_OPS:
        return "invalid_op"
    if type(target_tile_id) is not str or not TILE_ID_RE.match(target_tile_id):
        return "invalid_target_tile_id"
    if not isinstance(payload, Mapping):
        return "invalid_payload"

    try:
        import jsonschema
        jsonschema.validate(instance=dict(patch_request), schema=_load_patch_schema())
    except ImportError:
        pass
    except Exception:
        return "invalid_patch_schema"

    leaks = scan_wsp71_leaks(patch_request)
    if leaks:
        return "wsp71_secret_or_path_rejected"
    return None


def _resolve_add_blue_ids(
    target_tile_id: str,
    payload: Mapping[str, Any],
    tiles: Mapping[str, Any],
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Return ``(parent_tile_id, new_tile_id, error_detail)``."""
    has_tid = "tile_id" in payload
    has_pid = "parent_tile_id" in payload
    if has_tid and has_pid:
        parent_id = str(payload["parent_tile_id"])
        new_id = str(payload["tile_id"])
        if target_tile_id not in (parent_id, new_id):
            return None, None, "target_tile_id_mismatch"
    elif has_tid:
        parent_id = target_tile_id
        new_id = str(payload["tile_id"])
    elif has_pid:
        parent_id = str(payload["parent_tile_id"])
        new_id = target_tile_id
    else:
        return None, None, "missing_parent_or_tile_id"

    if not TILE_ID_RE.match(new_id) or not TILE_ID_RE.match(parent_id):
        return None, None, "invalid_tile_id"
    if parent_id not in tiles:
        return None, None, "parent_tile_not_found"
    if new_id in tiles:
        return None, None, "tile_already_exists"
    return parent_id, new_id, None


def _apply_patch_mutation(
    graph: Dict[str, Any],
    *,
    op: str,
    target_tile_id: str,
    payload: Mapping[str, Any],
    tenant: str,
    scope: str,
    actor_id: str,
    patch_id: str,
    committed_at_utc: str,
) -> Optional[str]:
    """Mutate *graph* in-place for a validated patch. Returns error detail or ``None``."""
    tiles = graph["tiles"]

    if op == "ADD_BLUE_TILE":
        parent_id, new_id, err = _resolve_add_blue_ids(target_tile_id, payload, tiles)
        if err or parent_id is None or new_id is None:
            return err or "invalid_add_blue_tile"
        display_name = payload.get("display_name")
        if type(display_name) is not str or not display_name.strip() or len(display_name) > 200:
            return "invalid_display_name"
        tile_kind = payload.get("tile_kind", "socket_slot")
        if tile_kind not in VALID_TILE_KINDS:
            return "invalid_tile_kind"
        vis_scope = payload.get(
            "visibility_scope",
            "principal_only" if (scope == "012_architect" and tenant == "foundups_core") else "public",
        )
        if vis_scope not in {"public", "principal_only"}:
            return "invalid_visibility_scope"
        owner_ns = payload.get("owner_namespace", tenant)
        if type(owner_ns) is not str or not _TENANT_RE.match(owner_ns):
            return "invalid_owner_namespace"

        new_tile = make_tile(
            tile_id=new_id,
            display_name=display_name.strip(),
            tile_kind=tile_kind,
            visibility_scope=vis_scope,
            owner_namespace=owner_ns,
            parent_tile_id=parent_id,
            state="BLUE",
            action_target=payload.get("action_target") or {},
            domain_override_manifest=payload.get("domain_override_manifest"),
            evidence_status=payload.get("evidence_status", "patch_proposed"),
            search_keywords=payload.get("search_keywords") or [],
            author_aliases=payload.get("author_aliases") or [],
            metadata=payload.get("metadata") or {},
        )
        tiles[new_id] = new_tile
        tiles[parent_id]["children_tile_ids"].append(new_id)
        return None

    if target_tile_id not in tiles:
        return "target_tile_not_found"
    tile = tiles[target_tile_id]

    if op == "RENAME_DISPLAY_LABEL":
        new_label = payload.get("display_name")
        if type(new_label) is not str or not new_label.strip() or len(new_label) > 200:
            return "invalid_display_name"
        new_label = new_label.strip()
        old_label = tile["display_name"]
        tile.setdefault("rename_history", []).append({
            "from": old_label,
            "to": new_label,
            "actor_id": actor_id,
            "patch_id": patch_id,
            "committed_at_utc": committed_at_utc,
        })
        tile["display_name"] = new_label
        return None

    if op == "PROMOTE_STATE":
        new_state = payload.get("state")
        if new_state not in VALID_STATES:
            return "invalid_state"
        tile["lifecycle"]["state"] = new_state
        tile["lifecycle"]["state_label"] = state_label(new_state)
        if "reason" in payload or "evidence_ref" in payload:
            tile.setdefault("metadata", {}).setdefault("state_promotions", []).append({
                "state": new_state,
                "reason": payload.get("reason", ""),
                "evidence_ref": payload.get("evidence_ref", ""),
                "patch_id": patch_id,
                "committed_at_utc": committed_at_utc,
            })
        return None

    if op == "WIRE_SOCKET_EDGE":
        edge_field = payload.get("edge_field", "cross_links")
        if edge_field not in set(DAG_TILE_EDGE_FIELDS) | {"used_by_foundups"}:
            return "invalid_edge_field"
        to_id = payload.get("to_tile_id") or payload.get("target_id")
        if type(to_id) is not str or not to_id:
            return "invalid_target_edge"
        if edge_field != "used_by_foundups" or to_id.startswith("tile:"):
            if to_id == target_tile_id:
                return "self_loop_rejected"
            if to_id not in tiles:
                return "edge_target_not_found"
        action = payload.get("action", "add")
        if action not in {"add", "remove"}:
            return "invalid_edge_action"
        edge_list = tile["dag_edges"].setdefault(edge_field, [])
        if action == "add":
            if to_id not in edge_list:
                edge_list.append(to_id)
        else:
            if to_id in edge_list:
                edge_list.remove(to_id)
        return None

    if op == "REORDER_CHILDREN":
        requested = payload.get("children_tile_ids")
        if type(requested) is not list or len(requested) != len(set(requested)):
            return "invalid_children_order"
        current_children = list(tile.get("children_tile_ids", []))
        if scope == "public_mall":
            visible_children = [
                cid for cid in current_children
                if tiles.get(cid, {}).get("visibility_scope") != "principal_only"
                and tiles.get(cid, {}).get("lifecycle", {}).get("state") != "RED"
            ]
            hidden_children = [cid for cid in current_children if cid not in set(visible_children)]
            if set(requested) != set(visible_children) or len(requested) != len(visible_children):
                return "children_reorder_mismatch"
            tile["children_tile_ids"] = list(requested) + hidden_children
        else:
            if set(requested) != set(current_children) or len(requested) != len(current_children):
                return "children_reorder_mismatch"
            tile["children_tile_ids"] = list(requested)
        return None

    if op == "UPDATE_PRIVATE_NOTE":
        note = payload.get("note")
        if type(note) is not str or not note.strip() or len(note) > 2000:
            return "invalid_private_note"
        tile.setdefault("private_notes", []).append({
            "note": note.strip(),
            "category": payload.get("category", "architect_note"),
            "actor_id": actor_id,
            "patch_id": patch_id,
            "committed_at_utc": committed_at_utc,
        })
        return None

    return "unsupported_op"


def _refresh_graph_metadata(graph: Dict[str, Any], *, updated_at_utc: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Recompute ETags and derived indices for architect & public projections."""
    arch_etag = compute_tiles_etag(graph["tiles"])
    indices = build_graph_indices(graph["tiles"])
    graph["schema_version"] = SCHEMA_VERSION
    graph["scope"] = "012_architect"
    graph["generated_at_utc"] = updated_at_utc
    graph["graph_etag"] = arch_etag
    graph["counts"] = indices["counts"]
    graph["links"] = indices["links"]
    graph["search_index"] = indices["search_index"]

    public_proj = project_public_tile_graph(graph)
    graph["public_graph_etag"] = public_proj["public_graph_etag"]
    return graph, public_proj


class TileGraphStore:
    """Thread-safe, WAL-backed atomic SQLite store for Fractal Tile Graph patches."""

    def __init__(
        self,
        db_path: Path | str,
        initial_graph: Optional[Mapping[str, Any]] = None,
    ) -> None:
        self._db_path = Path(db_path) if str(db_path) != ":memory:" else db_path
        if isinstance(self._db_path, Path):
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(
            str(self._db_path),
            timeout=30.0,
            isolation_level=None,
            check_same_thread=False,
        )
        self._init_schema()
        if initial_graph is not None:
            self._seed_if_empty(initial_graph)
        else:
            with self._lock:
                row = self._conn.execute(
                    "SELECT 1 FROM graph_snapshots WHERE snapshot_kind='active'"
                ).fetchone()
                if row is None:
                    raise ValueError("tile_graph_store_uninitialized")

    def _init_schema(self) -> None:
        with self._lock:
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA synchronous=NORMAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
            self._conn.execute("PRAGMA busy_timeout=5000")
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS accepted_patches (
                    seq INTEGER PRIMARY KEY AUTOINCREMENT,
                    patch_id TEXT UNIQUE NOT NULL,
                    actor_id TEXT NOT NULL,
                    tenant TEXT NOT NULL,
                    payload_sha256 TEXT NOT NULL,
                    base_graph_etag TEXT NOT NULL,
                    op TEXT NOT NULL,
                    target_tile_id TEXT NOT NULL,
                    patch_json TEXT NOT NULL,
                    receipt_json TEXT NOT NULL,
                    committed_at_utc TEXT NOT NULL
                )
                """
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS graph_snapshots (
                    snapshot_kind TEXT PRIMARY KEY,
                    graph_etag TEXT NOT NULL,
                    public_graph_etag TEXT NOT NULL,
                    graph_json TEXT NOT NULL,
                    updated_at_utc TEXT NOT NULL
                )
                """
            )

    def _seed_if_empty(self, initial_graph: Mapping[str, Any]) -> None:
        base_graph = copy.deepcopy(dict(initial_graph))
        now = base_graph.get("generated_at_utc") or datetime.now(timezone.utc).isoformat()
        base_graph, _ = _refresh_graph_metadata(base_graph, updated_at_utc=now)
        errs = validate_tile_graph(base_graph)
        if errs:
            raise ValueError(f"invalid_initial_graph: {errs[:3]}")
        encoded = json.dumps(base_graph, ensure_ascii=False)
        with self._lock:
            self._conn.execute("BEGIN IMMEDIATE")
            try:
                existing = self._conn.execute(
                    "SELECT 1 FROM graph_snapshots WHERE snapshot_kind='active'"
                ).fetchone()
                if existing is None:
                    for kind in ("base", "active"):
                        self._conn.execute(
                            """
                            INSERT OR REPLACE INTO graph_snapshots
                            (snapshot_kind, graph_etag, public_graph_etag, graph_json, updated_at_utc)
                            VALUES (?, ?, ?, ?, ?)
                            """,
                            (
                                kind,
                                base_graph["graph_etag"],
                                base_graph["public_graph_etag"],
                                encoded,
                                now,
                            ),
                        )
                self._conn.execute("COMMIT")
            except Exception:
                self._conn.execute("ROLLBACK")
                raise

    def close(self) -> None:
        """Close the underlying SQLite connection."""
        with self._lock:
            self._conn.close()

    def get_architect_graph(self) -> Dict[str, Any]:
        """Return the current active ``012_architect`` graph snapshot."""
        with self._lock:
            row = self._conn.execute(
                "SELECT graph_json FROM graph_snapshots WHERE snapshot_kind='active'"
            ).fetchone()
            if row is None:
                raise RuntimeError("active_graph_snapshot_missing")
            return json.loads(row[0])

    def get_public_graph(self) -> Dict[str, Any]:
        """Return the fresh ``public_mall`` projection of the active graph."""
        return project_public_tile_graph(self.get_architect_graph())

    def list_accepted_patches(self) -> List[Dict[str, Any]]:
        """Return ordered accepted patch records (without mutating store)."""
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT seq, patch_id, actor_id, tenant, payload_sha256, base_graph_etag,
                       op, target_tile_id, receipt_json, committed_at_utc
                FROM accepted_patches
                ORDER BY seq ASC
                """
            ).fetchall()
            return [
                {
                    "seq": r[0],
                    "patch_id": r[1],
                    "actor_id": r[2],
                    "tenant": r[3],
                    "payload_sha256": r[4],
                    "base_graph_etag": r[5],
                    "op": r[6],
                    "target_tile_id": r[7],
                    "receipt": json.loads(r[8]),
                    "committed_at_utc": r[9],
                }
                for r in rows
            ]

    def _check_actor_can_target(
        self,
        *,
        is_architect: bool,
        tenant: str,
        scope: str,
        op: str,
        target_tile_id: str,
        payload: Mapping[str, Any],
        tiles: Mapping[str, Any],
    ) -> Optional[str]:
        if is_architect:
            return None
        if scope == "012_architect":
            return "architect_authority_required"
        if tenant == "foundups_core" or op == "UPDATE_PRIVATE_NOTE":
            return "architect_authority_required"

        if op == "ADD_BLUE_TILE":
            parent_id, _new_id, err = _resolve_add_blue_ids(target_tile_id, payload, tiles)
            if parent_id and parent_id in tiles:
                parent_tile = tiles[parent_id]
                if parent_tile.get("visibility_scope") == "principal_only":
                    return "principal_only_tile_denied"
                if parent_tile.get("owner_namespace") != tenant:
                    return "cross_tenant_mutation_denied"
            if payload.get("visibility_scope", "public") != "public":
                return "principal_only_tile_denied"
            if payload.get("owner_namespace", tenant) != tenant:
                return "cross_tenant_mutation_denied"
            if err and err in {"parent_tile_not_found", "tile_already_exists"}:
                return None  # Let ETag/structural validation report cleanly
            return None

        target = tiles.get(target_tile_id)
        if target is None:
            return None
        if target.get("visibility_scope") == "principal_only" or target.get("lifecycle", {}).get("state") == "RED":
            return "principal_only_tile_denied"
        if target.get("owner_namespace") != tenant:
            return "cross_tenant_mutation_denied"

        if op == "WIRE_SOCKET_EDGE":
            to_id = payload.get("to_tile_id") or payload.get("target_id")
            if isinstance(to_id, str) and to_id in tiles:
                peer = tiles[to_id]
                if peer.get("visibility_scope") == "principal_only" or peer.get("lifecycle", {}).get("state") == "RED":
                    return "principal_only_target_denied"
        if op == "PROMOTE_STATE" and payload.get("state") == "RED":
            return "architect_authority_required"
        return None

    def apply_patch(
        self,
        patch_request: Mapping[str, Any],
        *,
        actor_id: str,
        policy: TileGraphAuthPolicy,
    ) -> PatchResult:
        """Validate, authorize, and atomically commit or replay a tile graph patch."""
        if type(policy) is not TileGraphAuthPolicy or not _valid_actor_handle(actor_id):
            return PatchResult(status="forbidden", http_status=403, detail="authorization_unavailable")

        struct_err = validate_patch_structure(patch_request)
        if struct_err is not None:
            return PatchResult(status="invalid", http_status=400, detail=struct_err)

        patch_id = str(patch_request["patch_id"])
        base_etag = str(patch_request["base_graph_etag"])
        scope = str(patch_request.get("scope", "public_mall"))
        tenant = str(patch_request["tenant"])
        op = str(patch_request["op"])
        target_tile_id = str(patch_request["target_tile_id"])
        payload = dict(patch_request["payload"])

        is_architect = policy.is_architect(actor_id)
        if not is_architect:
            if not policy.is_tenant_actor(actor_id, tenant):
                return PatchResult(status="forbidden", http_status=403, detail="actor_not_authorized_for_tenant")
            if scope == "012_architect" or tenant == "foundups_core" or op == "UPDATE_PRIVATE_NOTE":
                return PatchResult(status="forbidden", http_status=403, detail="architect_authority_required")

        payload_sha256 = sha256_canonical({
            "op": op,
            "target_tile_id": target_tile_id,
            "payload": payload,
            "tenant": tenant,
            "scope": scope,
        })

        with self._lock:
            self._conn.execute("BEGIN IMMEDIATE")
            try:
                existing = self._conn.execute(
                    """
                    SELECT actor_id, tenant, payload_sha256, receipt_json
                    FROM accepted_patches
                    WHERE patch_id = ?
                    """,
                    (patch_id,),
                ).fetchone()
                if existing is not None:
                    row_actor, row_tenant, row_sha, row_receipt = existing
                    self._conn.execute("ROLLBACK")
                    if (row_actor, row_tenant, row_sha) == (actor_id, tenant, payload_sha256):
                        return PatchResult(
                            status="idempotent_replay",
                            http_status=200,
                            receipt=json.loads(row_receipt),
                        )
                    return PatchResult(
                        status="conflict",
                        http_status=409,
                        detail="patch_id_binding_conflict",
                    )

                snap_row = self._conn.execute(
                    "SELECT graph_json FROM graph_snapshots WHERE snapshot_kind='active'"
                ).fetchone()
                if snap_row is None:
                    self._conn.execute("ROLLBACK")
                    return PatchResult(status="invalid", http_status=400, detail="active_graph_missing")

                active_graph: Dict[str, Any] = json.loads(snap_row[0])

                # Authorize target before exposing ETag or mutation state.
                auth_err = self._check_actor_can_target(
                    is_architect=is_architect,
                    tenant=tenant,
                    scope=scope,
                    op=op,
                    target_tile_id=target_tile_id,
                    payload=payload,
                    tiles=active_graph["tiles"],
                )
                if auth_err is not None:
                    self._conn.execute("ROLLBACK")
                    return PatchResult(status="forbidden", http_status=403, detail=auth_err)

                expected_etag = (
                    active_graph["graph_etag"]
                    if scope == "012_architect"
                    else active_graph["public_graph_etag"]
                )
                if base_etag != expected_etag:
                    self._conn.execute("ROLLBACK")
                    return PatchResult(
                        status="conflict",
                        http_status=409,
                        detail="etag_conflict",
                        current_graph_etag=expected_etag,
                    )

                committed_at_utc = datetime.now(timezone.utc).isoformat()
                mutated = copy.deepcopy(active_graph)
                mut_err = _apply_patch_mutation(
                    mutated,
                    op=op,
                    target_tile_id=target_tile_id,
                    payload=payload,
                    tenant=tenant,
                    scope=scope,
                    actor_id=actor_id,
                    patch_id=patch_id,
                    committed_at_utc=committed_at_utc,
                )
                if mut_err is not None:
                    self._conn.execute("ROLLBACK")
                    return PatchResult(status="invalid", http_status=400, detail=mut_err)

                mutated, public_proj = _refresh_graph_metadata(mutated, updated_at_utc=committed_at_utc)
                arch_errs = validate_tile_graph(mutated)
                pub_errs = validate_tile_graph(public_proj)
                if arch_errs or pub_errs:
                    self._conn.execute("ROLLBACK")
                    return PatchResult(
                        status="invalid",
                        http_status=400,
                        detail=f"graph_validation_failed: {(arch_errs + pub_errs)[0]}",
                    )

                new_arch_etag = mutated["graph_etag"]
                new_pub_etag = public_proj["public_graph_etag"]
                receipt: Dict[str, Any] = {
                    "receipt_id": f"rcpt_{uuid.uuid4().hex}",
                    "patch_id": patch_id,
                    "actor_id": actor_id,
                    "tenant": tenant,
                    "scope": scope,
                    "op": op,
                    "target_tile_id": target_tile_id,
                    "payload_sha256": payload_sha256,
                    "base_graph_etag": base_etag,
                    "new_graph_etag": new_arch_etag if scope == "012_architect" else new_pub_etag,
                    "public_graph_etag": new_pub_etag,
                    "committed_at_utc": committed_at_utc,
                }
                if scope == "012_architect":
                    receipt["architect_graph_etag"] = new_arch_etag

                patch_record_json = json.dumps({
                    "patch_id": patch_id,
                    "base_graph_etag": base_etag,
                    "scope": scope,
                    "tenant": tenant,
                    "op": op,
                    "target_tile_id": target_tile_id,
                    "payload": payload,
                }, ensure_ascii=False)

                cur = self._conn.execute(
                    """
                    INSERT INTO accepted_patches
                    (patch_id, actor_id, tenant, payload_sha256, base_graph_etag,
                     op, target_tile_id, patch_json, receipt_json, committed_at_utc)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        patch_id,
                        actor_id,
                        tenant,
                        payload_sha256,
                        base_etag,
                        op,
                        target_tile_id,
                        patch_record_json,
                        "{}",
                        committed_at_utc,
                    ),
                )
                receipt["seq"] = cur.lastrowid
                receipt_json = json.dumps(receipt, ensure_ascii=False)
                self._conn.execute(
                    "UPDATE accepted_patches SET receipt_json = ? WHERE seq = ?",
                    (receipt_json, cur.lastrowid),
                )
                self._conn.execute(
                    """
                    INSERT OR REPLACE INTO graph_snapshots
                    (snapshot_kind, graph_etag, public_graph_etag, graph_json, updated_at_utc)
                    VALUES ('active', ?, ?, ?, ?)
                    """,
                    (
                        new_arch_etag,
                        new_pub_etag,
                        json.dumps(mutated, ensure_ascii=False),
                        committed_at_utc,
                    ),
                )
                self._conn.execute("COMMIT")
                return PatchResult(
                    status="committed",
                    http_status=201,
                    receipt=receipt,
                    current_graph_etag=receipt["new_graph_etag"],
                )
            except Exception:
                self._conn.execute("ROLLBACK")
                raise

    def regenerate_from_catalog(self, fresh_base_graph: Mapping[str, Any]) -> Dict[str, Any]:
        """Reset base snapshot from *fresh_base_graph* and replay all accepted patches."""
        base = copy.deepcopy(dict(fresh_base_graph))
        now = datetime.now(timezone.utc).isoformat()
        base, _ = _refresh_graph_metadata(base, updated_at_utc=base.get("generated_at_utc") or now)
        base_errs = validate_tile_graph(base)
        if base_errs:
            raise ValueError(f"invalid_fresh_base_graph: {base_errs[:3]}")

        with self._lock:
            self._conn.execute("BEGIN IMMEDIATE")
            try:
                rows = self._conn.execute(
                    """
                    SELECT seq, patch_id, actor_id, tenant, op, target_tile_id, patch_json, committed_at_utc
                    FROM accepted_patches
                    ORDER BY seq ASC
                    """
                ).fetchall()

                working = copy.deepcopy(base)
                for _seq, patch_id, actor_id, tenant, op, target_tile_id, patch_json, committed_at_utc in rows:
                    patch_data = json.loads(patch_json)
                    scope = patch_data.get("scope", "public_mall")
                    payload = patch_data.get("payload", {})
                    err = _apply_patch_mutation(
                        working,
                        op=op,
                        target_tile_id=target_tile_id,
                        payload=payload,
                        tenant=tenant,
                        scope=scope,
                        actor_id=actor_id,
                        patch_id=patch_id,
                        committed_at_utc=committed_at_utc,
                    )
                    if err is not None:
                        raise RuntimeError(f"patch_replay_failed seq={_seq} patch_id={patch_id}: {err}")

                working, pub_proj = _refresh_graph_metadata(working, updated_at_utc=now)
                arch_errs = validate_tile_graph(working)
                pub_errs = validate_tile_graph(pub_proj)
                if arch_errs or pub_errs:
                    raise RuntimeError(f"replayed_graph_invalid: {(arch_errs + pub_errs)[:3]}")

                self._conn.execute(
                    """
                    INSERT OR REPLACE INTO graph_snapshots
                    (snapshot_kind, graph_etag, public_graph_etag, graph_json, updated_at_utc)
                    VALUES ('base', ?, ?, ?, ?)
                    """,
                    (
                        base["graph_etag"],
                        base["public_graph_etag"],
                        json.dumps(base, ensure_ascii=False),
                        now,
                    ),
                )
                self._conn.execute(
                    """
                    INSERT OR REPLACE INTO graph_snapshots
                    (snapshot_kind, graph_etag, public_graph_etag, graph_json, updated_at_utc)
                    VALUES ('active', ?, ?, ?, ?)
                    """,
                    (
                        working["graph_etag"],
                        working["public_graph_etag"],
                        json.dumps(working, ensure_ascii=False),
                        now,
                    ),
                )
                self._conn.execute("COMMIT")
                return working
            except Exception:
                self._conn.execute("ROLLBACK")
                raise
