#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Scope-aware Context, Navigation, Search & Lens Helpers for Fractal Tile Graph.

Provides pure, read-only traversal over either a ``public_mall`` or
``012_architect`` graph snapshot: breadcrumbs, sorted/filtered child grids,
search-index alias resolution, rescue queue ranking, co-building socket
inspection, and RedDog advisory context extraction. Never mutates state or
leaks ``principal_only`` / ``RED`` data into public contexts.
"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Sequence

from modules.foundups.pfmall.fractal_tile_graph import (
    DAG_TILE_EDGE_FIELDS,
    ROOT_TILE_ID,
    scan_wsp71_leaks,
)

VALID_VIEW_MODES = frozenset({"tiles", "mind_map", "learn", "debug", "rescue"})
VALID_CHILD_SORTS = frozenset({
    "default",
    "published_date_desc",
    "published_date_asc",
    "title_asc",
    "scheduled_next_asc",
    "rescue_score_desc",
})


def _is_visible_in_scope(tile: Mapping[str, Any], scope: str) -> bool:
    if scope == "012_architect":
        return True
    return (
        tile.get("visibility_scope") != "principal_only"
        and tile.get("lifecycle", {}).get("state") != "RED"
    )


def _editorial_bucket(tile: Mapping[str, Any]) -> str:
    meta = tile.get("metadata") or {}
    stage = str(meta.get("editorial_stage", "")).upper()
    state = tile.get("lifecycle", {}).get("state")
    if stage == "SCHEDULED_VERIFIED":
        return "scheduled"
    if stage in {"DRAFTED", "DRAFTED_V2", "LOCAL_GITIGNORED_PRIVATE", "HISTORICAL_CORPUS_BASELINE"}:
        return "draft"
    if stage == "PLANNED_SOCKET" or state == "BLUE":
        return "planned"
    return "published"


def _sort_children(children: List[Dict[str, Any]], sort: str) -> List[Dict[str, Any]]:
    if sort == "default":
        return children
    if sort == "title_asc":
        return sorted(children, key=lambda t: (t.get("display_name", "").lower(), t["tile_id"]))
    if sort == "published_date_desc":
        return sorted(
            children,
            key=lambda t: (
                str((t.get("metadata") or {}).get("published_date") or ""),
                t["tile_id"],
            ),
            reverse=True,
        )
    if sort == "published_date_asc":
        return sorted(
            children,
            key=lambda t: (
                str((t.get("metadata") or {}).get("published_date") or "9999-99-99"),
                t["tile_id"],
            ),
        )
    if sort == "scheduled_next_asc":
        return sorted(
            children,
            key=lambda t: (
                0 if (t.get("metadata") or {}).get("scheduled_release_at") else 1,
                str((t.get("metadata") or {}).get("scheduled_release_at") or "9999-99-99"),
                t["tile_id"],
            ),
        )
    if sort == "rescue_score_desc":
        return sorted(
            children,
            key=lambda t: (
                -(t.get("mall_rescue_score") or 0),
                -((t.get("wsp15_canonical") or {}).get("mps") or 0),
                t["tile_id"],
            ),
        )
    raise ValueError(f"Unsupported sort mode: {sort!r}")


def get_breadcrumbs(graph: Mapping[str, Any], tile_id: str) -> List[Dict[str, Any]]:
    """Return ordered root-to-tile breadcrumb trail strictly within *graph*."""
    tiles = graph.get("tiles", {})
    if tile_id not in tiles:
        return []
    trail: List[Dict[str, Any]] = []
    seen = set()
    cur: Optional[str] = tile_id
    while cur is not None and cur in tiles and cur not in seen:
        seen.add(cur)
        t = tiles[cur]
        trail.append({
            "tile_id": cur,
            "display_name": t["display_name"],
            "tile_kind": t["tile_kind"],
            "state": t["lifecycle"]["state"],
        })
        cur = t.get("parent_tile_id")
    trail.reverse()
    return trail


def build_tile_context(
    graph: Mapping[str, Any],
    tile_id: str,
    *,
    view_mode: str = "tiles",
    sort: str = "default",
    filter_state: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Build scoped navigation, children, DAG neighbors, and anchor context for *tile_id*."""
    if view_mode not in VALID_VIEW_MODES:
        raise ValueError(f"Unsupported view_mode: {view_mode!r}")
    if sort not in VALID_CHILD_SORTS:
        raise ValueError(f"Unsupported sort mode: {sort!r}")

    tiles = graph.get("tiles", {})
    scope = graph.get("scope", "public_mall")
    tile = tiles.get(tile_id)
    if tile is None or not _is_visible_in_scope(tile, scope):
        return None

    raw_children = [
        tiles[cid] for cid in tile.get("children_tile_ids", [])
        if cid in tiles and _is_visible_in_scope(tiles[cid], scope)
    ]
    if filter_state:
        needle = filter_state.lower()
        if needle in {"published", "scheduled", "draft", "planned"}:
            raw_children = [c for c in raw_children if _editorial_bucket(c) == needle]
        else:
            upper = filter_state.upper()
            raw_children = [c for c in raw_children if c["lifecycle"]["state"] == upper]

    ordered_children = _sort_children(list(raw_children), sort)

    dag_neighbors: Dict[str, List[Dict[str, Any]]] = {}
    edges = tile.get("dag_edges", {})
    for efield in DAG_TILE_EDGE_FIELDS:
        resolved = []
        for target_id in edges.get(efield, []):
            target = tiles.get(target_id)
            if target is not None and _is_visible_in_scope(target, scope):
                resolved.append({
                    "tile_id": target_id,
                    "display_name": target["display_name"],
                    "tile_kind": target["tile_kind"],
                    "state": target["lifecycle"]["state"],
                })
        dag_neighbors[efield] = resolved

    pid = tile.get("parent_tile_id")
    parent_summary = None
    if pid and pid in tiles and _is_visible_in_scope(tiles[pid], scope):
        parent_summary = {
            "tile_id": pid,
            "display_name": tiles[pid]["display_name"],
            "tile_kind": tiles[pid]["tile_kind"],
        }

    available_lenses = ["tiles", "mind_map", "learn", "debug"]
    if scope == "012_architect" or tile.get("mall_rescue_score") is not None:
        available_lenses.append("rescue")

    return {
        "scope": scope,
        "graph_etag": graph.get("graph_etag"),
        "public_graph_etag": graph.get("public_graph_etag"),
        "tile": tile,
        "parent": parent_summary,
        "breadcrumbs": get_breadcrumbs(graph, tile_id),
        "children": ordered_children,
        "dag_neighbors": dag_neighbors,
        "available_lenses": available_lenses,
        "selection_anchor": {
            "tile_id": tile_id,
            "view_mode": view_mode,
            "sort": sort,
            "filter_state": filter_state,
        },
    }


def search_tiles(
    graph: Mapping[str, Any],
    query: str,
    *,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    """Resolve text or voice-intent queries strictly across visible tiles in *graph*."""
    q = (query or "").strip()
    if not q or limit <= 0:
        return []

    tiles = graph.get("tiles", {})
    scope = graph.get("scope", "public_mall")
    needle = q.lower()
    ordered_ids: List[str] = []

    aliases = (graph.get("search_index") or {}).get("aliases") or {}
    for alias_key, alias_ids in aliases.items():
        if alias_key.lower() == needle:
            for tid in alias_ids:
                if tid in tiles and _is_visible_in_scope(tiles[tid], scope) and tid not in ordered_ids:
                    ordered_ids.append(tid)

    for tid in sorted(tiles):
        if tid in ordered_ids:
            continue
        t = tiles[tid]
        if not _is_visible_in_scope(t, scope):
            continue
        meta = t.get("metadata") or {}
        haystack = " ".join(
            [
                tid,
                str(t.get("display_name", "")),
                str(meta.get("subtitle", "")),
                str(meta.get("municipality", "")),
                str(meta.get("prefecture", "")),
            ]
            + [str(k) for k in t.get("search_keywords", [])]
            + [str(a) for a in t.get("author_aliases", [])]
        ).lower()
        if needle in haystack:
            ordered_ids.append(tid)

    return [tiles[tid] for tid in ordered_ids[:limit]]


def get_rescue_queue(
    graph: Mapping[str, Any],
    *,
    limit: int = 20,
    include_green: bool = False,
) -> List[Dict[str, Any]]:
    """Return tiles ranked by ``mall_rescue_score`` descending strictly within *graph*."""
    tiles = graph.get("tiles", {})
    scope = graph.get("scope", "public_mall")
    candidates = [
        t for t in tiles.values()
        if _is_visible_in_scope(t, scope)
        and t.get("mall_rescue_score") is not None
        and (include_green or t["lifecycle"]["state"] != "GREEN")
    ]
    candidates.sort(
        key=lambda t: (
            -int(t["mall_rescue_score"]),
            -int((t.get("wsp15_canonical") or {}).get("mps") or 0),
            t["tile_id"],
        )
    )
    return [
        {
            "rank": idx,
            "tile_id": t["tile_id"],
            "display_name": t["display_name"],
            "state": t["lifecycle"]["state"],
            "visibility_scope": t["visibility_scope"],
            "mall_rescue_score": t["mall_rescue_score"],
            "wsp15_canonical": t["wsp15_canonical"],
            "next_action": (t.get("rescue_axes") or {}).get("next_action"),
        }
        for idx, t in enumerate(candidates[:limit], 1)
    ]


def get_cobuilding_context(
    graph: Mapping[str, Any],
    tile_id: str = "tile:sys:simulator",
) -> Optional[Dict[str, Any]]:
    """Inspect a tile's open BLUE sockets, candidate adapters, and test anchors."""
    ctx = build_tile_context(graph, tile_id, view_mode="mind_map")
    if ctx is None:
        return None
    open_sockets = [
        {
            "tile_id": c["tile_id"],
            "display_name": c["display_name"],
            "reusable_candidates": (c.get("dag_edges") or {}).get("reusable_candidates", []),
            "next_action": (c.get("rescue_axes") or {}).get("next_action"),
            "interface_doc": (c.get("action_target") or {}).get("interface_doc"),
        }
        for c in ctx["children"]
        if c["lifecycle"]["state"] == "BLUE" or c["tile_kind"] == "socket_slot"
    ]
    return {
        "tile_id": tile_id,
        "scope": ctx["scope"],
        "state": ctx["tile"]["lifecycle"]["state"],
        "mall_rescue_score": ctx["tile"].get("mall_rescue_score"),
        "wsp15_canonical": ctx["tile"].get("wsp15_canonical"),
        "open_sockets": open_sockets,
        "dag_neighbors": ctx["dag_neighbors"],
        "action_target": ctx["tile"].get("action_target"),
    }


def build_reddog_tile_briefing(
    graph: Mapping[str, Any],
    tile_id: str = ROOT_TILE_ID,
) -> Optional[Dict[str, Any]]:
    """Produce a concise, scope-safe advisory briefing for RedDog / 0102 surfaces."""
    ctx = build_tile_context(graph, tile_id)
    if ctx is None:
        return None
    tile = ctx["tile"]
    briefing: Dict[str, Any] = {
        "scope": ctx["scope"],
        "tile_id": tile_id,
        "display_name": tile["display_name"],
        "tile_kind": tile["tile_kind"],
        "state": tile["lifecycle"]["state"],
        "state_label": tile["lifecycle"]["state_label"],
        "evidence_status": tile.get("evidence_status"),
        "breadcrumbs": ctx["breadcrumbs"],
        "child_count": len(ctx["children"]),
        "available_lenses": ctx["available_lenses"],
        "graph_etag": ctx["graph_etag"],
    }
    if tile.get("mall_rescue_score") is not None:
        briefing["mall_rescue_score"] = tile["mall_rescue_score"]
    if ctx["scope"] == "012_architect" and "private_notes" in tile:
        briefing["private_notes"] = list(tile["private_notes"])

    if ctx["scope"] == "public_mall" and scan_wsp71_leaks(briefing):
        return None
    return briefing


def query_tools_benchmark_readback(graph: Mapping[str, Any]) -> Dict[str, Any]:
    """Answer all 5 Tools -> Benchmark questions strictly from visible tiles in *graph*."""
    tiles = graph.get("tiles", {})
    scope = graph.get("scope", "public_mall")

    visible_tiles = {
        tid: tile
        for tid, tile in tiles.items()
        if _is_visible_in_scope(tile, scope)
    }
    bench_tile = visible_tiles.get("tile:tools:benchmark") or {}
    bench_cross = set((bench_tile.get("dag_edges") or {}).get("cross_links") or [])
    bench_runs_through = set((bench_tile.get("dag_edges") or {}).get("runs_through") or [])

    # Q1: Which benchmark tools are present on this PC?
    tools_root = visible_tiles.get("tile:tools:root") or {}
    pc_tools: List[Dict[str, Any]] = []
    for cid in tools_root.get("children_tile_ids", []):
        ctile = visible_tiles.get(cid)
        if not ctile or cid == "tile:tools:benchmark":
            continue
        if not (cid.startswith("tile:tool:") or cid == "tile:socket:benchmark.hermes_cli_runner"):
            continue
        be = (ctile.get("metadata") or {}).get("benchmark_evidence") or {}
        pc_tools.append({
            "tile_id": cid,
            "display_name": ctile["display_name"],
            "tile_kind": ctile["tile_kind"],
            "state": ctile["lifecycle"]["state"],
            "parent_tile_id": ctile.get("parent_tile_id"),
            "availability": be.get("availability"),
            "models": list(be.get("models") or []),
            "cost_usd": be.get("cost_usd", 0.0),
            "appears_in_benchmark_via": [
                edge for edge, s in (("cross_links", bench_cross), ("runs_through", bench_runs_through)) if cid in s
            ],
        })

    # Collect configurations & runs indexed cleanly by harness/tool
    cfg_tiles = [
        t for tid, t in sorted(visible_tiles.items())
        if tid.startswith("tile:benchcfg:")
    ]
    run_tiles = [
        t for tid, t in sorted(visible_tiles.items())
        if tid.startswith("tile:benchrun:")
    ]

    # Q2: Which modules, models and scaffolds can each harness/tool evaluate?
    evaluatable_targets: List[Dict[str, Any]] = []
    for htid, htile in sorted(visible_tiles.items()):
        if not htid.startswith("tile:harness:"):
            continue
        edges = htile.get("dag_edges") or {}
        be = (htile.get("metadata") or {}).get("benchmark_evidence") or {}
        eval_ids = [eid for eid in (edges.get("evaluates") or []) if eid in visible_tiles]
        eval_modules = sorted(
            eid for eid in eval_ids
            if eid.startswith("tile:mod:") or eid == "tile:sys:simulator"
        )
        child_cfgs = [visible_tiles[c] for c in htile.get("children_tile_ids", []) if c in visible_tiles and c.startswith("tile:benchcfg:")]
        models = be.get("evaluated_models") or [
            ((c.get("metadata") or {}).get("benchmark_evidence") or {}).get("model_name")
            for c in child_cfgs
            if ((c.get("metadata") or {}).get("benchmark_evidence") or {}).get("model_name")
        ]
        scaffolds = be.get("evaluated_scaffolds") or sorted({
            str(((c.get("metadata") or {}).get("benchmark_evidence") or {}).get("scaffold_name"))
            for c in child_cfgs
            if ((c.get("metadata") or {}).get("benchmark_evidence") or {}).get("scaffold_name")
        })
        evaluatable_targets.append({
            "harness_tile_id": htid,
            "display_name": htile["display_name"],
            "state": htile["lifecycle"]["state"],
            "runs_through_tools": [t for t in (edges.get("runs_through") or []) if t in visible_tiles],
            "evaluated_modules": eval_modules,
            "evaluated_models": models,
            "evaluated_scaffolds": scaffolds,
            "evaluated_tile_ids": eval_ids,
        })

    # Also summarize per PC tool from configs & direct edges
    for tool_row in pc_tools:
        tid = tool_row["tile_id"]
        ttile = visible_tiles[tid]
        tedges = ttile.get("dag_edges") or {}
        matching_cfgs = [
            c for c in cfg_tiles
            if tid in ((c.get("dag_edges") or {}).get("runs_through") or [])
        ]
        mod_set = set(e for e in (tedges.get("evaluates") or []) if e in visible_tiles and (e.startswith("tile:mod:") or e == "tile:sys:simulator"))
        for c in matching_cfgs:
            for e in ((c.get("dag_edges") or {}).get("evaluates") or []):
                if e in visible_tiles and (e.startswith("tile:mod:") or e == "tile:sys:simulator"):
                    mod_set.add(e)
        tool_row["evaluated_modules"] = sorted(mod_set)
        tool_row["evaluated_scaffolds"] = sorted({
            str(((c.get("metadata") or {}).get("benchmark_evidence") or {}).get("scaffold_name"))
            for c in matching_cfgs
            if ((c.get("metadata") or {}).get("benchmark_evidence") or {}).get("scaffold_name")
        })

    # Q3: Which combinations have actually run, with what result and revision?
    executed_runs: List[Dict[str, Any]] = []
    for rtile in run_tiles:
        be = (rtile.get("metadata") or {}).get("benchmark_evidence") or {}
        executed_runs.append({
            "tile_id": rtile["tile_id"],
            "config_tile_id": rtile.get("parent_tile_id"),
            "phase": be.get("phase"),
            "packet_id": be.get("packet_id"),
            "model_name": be.get("model_name"),
            "scaffold_name": be.get("scaffold_name"),
            "verdict": be.get("verdict"),
            "factual_coverage": be.get("factual_coverage"),
            "schema_valid": be.get("schema_valid"),
            "latency_ms": be.get("latency_ms"),
            "cost_usd": be.get("cost_usd"),
            "error_taxonomy": be.get("error_taxonomy"),
            "git_revision": be.get("git_revision"),
            "harness_receipt_id": be.get("harness_receipt_id"),
        })

    # Q4: Which expected capability has no verified owner or adapter?
    missing_or_blocked_capabilities: List[Dict[str, Any]] = []
    for tid, tile in sorted(visible_tiles.items()):
        is_bench_domain = (
            tid.startswith("tile:socket:benchmark.")
            or tid.startswith("tile:benchcfg:")
            or tid.startswith("tile:tool:")
        )
        if not is_bench_domain:
            continue
        state = tile["lifecycle"]["state"]
        be = (tile.get("metadata") or {}).get("benchmark_evidence") or {}
        if tile["tile_kind"] == "socket_slot" or state == "BLUE" or be.get("missing_capability_reason"):
            missing_or_blocked_capabilities.append({
                "tile_id": tid,
                "display_name": tile["display_name"],
                "tile_kind": tile["tile_kind"],
                "state": state,
                "parent_tile_id": tile.get("parent_tile_id"),
                "reason": be.get("missing_capability_reason") or be.get("summary") or (tile.get("rescue_axes") or {}).get("next_action"),
            })

    # Q5: Can the reader follow a result back to its inputs and evidence?
    traceability_checks: List[Dict[str, Any]] = []
    for rtile in run_tiles:
        redges = rtile.get("dag_edges") or {}
        reads_from = [eid for eid in (redges.get("reads_from") or []) if eid in visible_tiles]
        produces_receipt = [rid for rid in (redges.get("produces_receipt") or []) if rid in visible_tiles]
        verified_by = [vid for vid in (redges.get("verified_by") or []) if vid in visible_tiles]
        runs_through = [tid for tid in (redges.get("runs_through") or []) if tid in visible_tiles]
        ev_revs = sorted({
            str(((visible_tiles[eid].get("metadata") or {}).get("benchmark_evidence") or {}).get("git_revision") or "")
            for eid in reads_from
        })
        traceable = bool(reads_from and produces_receipt and verified_by and runs_through and any(ev_revs))
        traceability_checks.append({
            "run_tile_id": rtile["tile_id"],
            "reads_from": reads_from,
            "produces_receipt": produces_receipt,
            "verified_by": verified_by,
            "runs_through": runs_through,
            "evidence_git_revisions": ev_revs,
            "traceable": traceable,
        })

    return {
        "scope": scope,
        "graph_etag": graph.get("graph_etag"),
        "q1_pc_benchmark_tools": pc_tools,
        "q2_evaluatable_targets": evaluatable_targets,
        "q3_executed_runs": executed_runs,
        "q4_missing_or_blocked_capabilities": missing_or_blocked_capabilities,
        "q5_result_to_evidence_traceability": {
            "runs_checked": len(traceability_checks),
            "all_runs_traceable": bool(traceability_checks) and all(c["traceable"] for c in traceability_checks),
            "runs": traceability_checks,
        },
    }


def walk_fractal_path(graph: Mapping[str, Any], waypoints: Sequence[str]) -> Dict[str, Any]:
    """Simulate step-by-step forward navigation across *waypoints* and full Back return."""
    if not waypoints:
        return {"ok": False, "error": "empty_waypoints", "forward_trail": [], "back_trail": [], "terminal_tile": None}

    tiles = graph.get("tiles", {})
    scope = graph.get("scope", "public_mall")

    first = waypoints[0]
    if first not in tiles or not _is_visible_in_scope(tiles[first], scope):
        return {"ok": False, "error": f"invisible_or_missing_start:{first}", "forward_trail": [], "back_trail": [], "terminal_tile": None}

    nav_stack: List[str] = []
    forward_trail: List[str] = [first]
    cur = first

    for nxt in waypoints[1:]:
        if nxt not in tiles or not _is_visible_in_scope(tiles[nxt], scope):
            return {"ok": False, "error": f"invisible_or_missing_waypoint:{nxt}", "forward_trail": forward_trail, "back_trail": [], "terminal_tile": cur}
        cur_tile = tiles[cur]
        cur_edges = cur_tile.get("dag_edges") or {}
        reachable: List[str] = list(cur_tile.get("children_tile_ids") or [])
        for efield in DAG_TILE_EDGE_FIELDS:
            reachable.extend(cur_edges.get(efield) or [])
        if nxt not in reachable:
            return {"ok": False, "error": f"unreachable_step:{cur}->{nxt}", "forward_trail": forward_trail, "back_trail": [], "terminal_tile": cur}
        nav_stack.append(cur)
        cur = nxt
        forward_trail.append(cur)

    back_trail: List[str] = [cur]
    while nav_stack:
        cur = nav_stack.pop()
        back_trail.append(cur)

    return {
        "ok": cur == first,
        "forward_trail": forward_trail,
        "back_trail": back_trail,
        "terminal_tile": cur,
    }


def compute_view_reachability(
    graph: Mapping[str, Any],
    eligible_ids: Sequence[str],
) -> Dict[str, Any]:
    """Traverse actual UI-navigable links from ``root_tile_id`` and reconcile against *eligible_ids*.

    *eligible_ids* must be derived from upstream manifests + visibility policy BEFORE
    inspecting the rendered graph. Reports ``R``, ``T``, ``R/T``, ``unreachable_ids``,
    ``unexpected_reachable_ids``, and ``dangling_links``.
    """
    scope = str(graph.get("scope") or "public_mall")
    tiles = graph.get("tiles") or {}
    root_id = str(graph.get("root_tile_id") or ROOT_TILE_ID)
    eligible_set = set(eligible_ids)

    dangling_links: List[Dict[str, str]] = []
    for src_id, src_tile in sorted(tiles.items()):
        if not _is_visible_in_scope(src_tile, scope):
            continue
        for cid in src_tile.get("children_tile_ids") or []:
            if cid not in tiles or not _is_visible_in_scope(tiles[cid], scope):
                dangling_links.append({"source": src_id, "edge": "children_tile_ids", "target": str(cid)})
        edges = src_tile.get("dag_edges") or {}
        for efield in DAG_TILE_EDGE_FIELDS:
            for tgt in edges.get(efield) or []:
                if tgt not in tiles or not _is_visible_in_scope(tiles[tgt], scope):
                    dangling_links.append({"source": src_id, "edge": efield, "target": str(tgt)})
        for uf in edges.get("used_by_foundups") or []:
            if isinstance(uf, str) and uf.startswith("tile:") and (uf not in tiles or not _is_visible_in_scope(tiles[uf], scope)):
                dangling_links.append({"source": src_id, "edge": "used_by_foundups", "target": uf})

    # 1. Containment-only BFS
    containment_reachable: set[str] = set()
    if root_id in tiles and _is_visible_in_scope(tiles[root_id], scope):
        q_cont = [root_id]
        idx = 0
        while idx < len(q_cont):
            cur = q_cont[idx]
            idx += 1
            if cur in containment_reachable:
                continue
            containment_reachable.add(cur)
            for cid in tiles[cur].get("children_tile_ids") or []:
                if cid in tiles and _is_visible_in_scope(tiles[cid], scope) and cid not in containment_reachable:
                    q_cont.append(cid)

    # 2. Full UI-navigable BFS (containment + cross_links + typed relationship / reuse pills)
    navigable_reachable: set[str] = set()
    if root_id in tiles and _is_visible_in_scope(tiles[root_id], scope):
        q_nav = [root_id]
        idx2 = 0
        while idx2 < len(q_nav):
            cur = q_nav[idx2]
            idx2 += 1
            if cur in navigable_reachable:
                continue
            navigable_reachable.add(cur)
            cur_tile = tiles[cur]
            neighbors: List[str] = list(cur_tile.get("children_tile_ids") or [])
            edges = cur_tile.get("dag_edges") or {}
            for efield in DAG_TILE_EDGE_FIELDS:
                neighbors.extend(edges.get(efield) or [])
            for nxt in neighbors:
                if nxt in tiles and _is_visible_in_scope(tiles[nxt], scope) and nxt not in navigable_reachable:
                    q_nav.append(nxt)

    reachable_eligible = navigable_reachable & eligible_set
    unreachable = sorted(eligible_set - navigable_reachable)
    unexpected = sorted(navigable_reachable - eligible_set)
    t_count = len(eligible_set)
    r_count = len(reachable_eligible)

    return {
        "scope": scope,
        "root_tile_id": root_id,
        "eligible_total_T": t_count,
        "reachable_eligible_R": r_count,
        "reachability_ratio": round(r_count / t_count, 6) if t_count > 0 else 1.0,
        "reachability_display": f"{r_count}/{t_count}",
        "containment_only_reachable_count": len(containment_reachable),
        "navigable_reachable_total_count": len(navigable_reachable),
        "unreachable_ids": unreachable,
        "unexpected_reachable_ids": unexpected,
        "dangling_links": dangling_links,
        "reconciled_exact": (r_count == t_count and len(unreachable) == 0 and len(unexpected) == 0 and len(dangling_links) == 0),
    }
