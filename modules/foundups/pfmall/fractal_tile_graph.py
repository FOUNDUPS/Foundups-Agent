#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PlayFoundups Mall Fractal Tile Graph — Schema, Scorer, Validator, Dual-Scope Projector & Repo Builder.

Builds the canonical ``fractal_tile_graph.v1`` graph directly from tracked
files under a repository root (with zero dependency on gitignored ``temp/``),
computes dual scores (canonical ``WSP_15`` 4-20 / P0-P4 and ``mall_rescue_score``
20-100), validates containment acyclicity and DAG integrity, and projects a
leak-free ``public_mall`` view whose ``public_graph_etag`` depends strictly
on public non-RED tiles alone.

WSP Compliance:
    WSP 11 : Typed interface contracts
    WSP 15 : Canonical MPS scoring (4-20, P0-P4)
    WSP 71 : Secret & local-path leak prevention
    WSP 97 : Evidence-grounded truth boundaries
"""

from __future__ import annotations

import ast
import copy
import hashlib
import json
import os
import re
import subprocess
import tarfile
import warnings
from collections import Counter, defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, FrozenSet, Iterable, List, Mapping, Optional, Set, Tuple

SCHEMA_VERSION = "fractal_tile_graph.v1"
ROOT_TILE_ID = "tile:mall:root"

VALID_SCOPES = frozenset({"012_architect", "public_mall"})
VALID_STATES = frozenset({"GREEN", "AMBER", "BLUE", "GRAY", "RED"})
STATE_LABELS: Dict[str, str] = {
    "GREEN": "LIVE_VERIFIED",
    "AMBER": "IN_PROGRESS_OR_DRIFT",
    "BLUE": "PLANNED_SOCKET",
    "GRAY": "DORMANT_ARCHIVED",
    "RED": "ORPHANED_OR_BROKEN",
}
VALID_TILE_KINDS = frozenset({
    "system_cube",
    "opus_series",
    "opus_item",
    "community_fractal",
    "foundup_venture",
    "market_override",
    "wikitube_stream",
    "mockup_cube",
    "code_module",
    "socket_slot",
    "licensable_engine",
})
VALID_VISIBILITY_SCOPES = frozenset({"public", "principal_only"})
VALID_OVERRIDE_TYPES = frozenset({
    "none",
    "hpc_community",
    "autopost_license",
    "akiya_property",
    "wikitube_playlist",
})
TYPED_RELATIONSHIP_EDGE_FIELDS = (
    "calls",
    "reads_from",
    "evaluates",
    "runs_through",
    "produces_receipt",
    "verified_by",
)
DAG_TILE_EDGE_FIELDS = (
    "imports_tiles",
    "reusable_candidates",
    "cross_links",
    "collection_refs",
) + TYPED_RELATIONSHIP_EDGE_FIELDS
ALL_DAG_EDGE_FIELDS = (
    "imports_tiles",
    "used_by_foundups",
    "reusable_candidates",
    "oss_candidates",
    "cross_links",
    "collection_refs",
) + TYPED_RELATIONSHIP_EDGE_FIELDS

SEARCH_ALIAS_KEYS: Tuple[str, ...] = (
    "all papers",
    "UnDaoDu",
    "Return on Compute",
    "Japan Hyperscaler Report",
    "JHR",
    "HPC",
    "AutoPost",
    "Akiya",
    "Simulator",
    "Tools",
    "Benchmark",
)

_SEARCH_ALIAS_PRIORITY: Dict[str, Tuple[str, ...]] = {
    "all papers": ("tile:opus:papers", "tile:opus:patent_series"),
    "UnDaoDu": ("tile:opus:undaodu_linkedin", "tile:pubs:root"),
    "Return on Compute": ("tile:opus:roc",),
    "Japan Hyperscaler Report": ("tile:opus:jhr",),
    "JHR": ("tile:opus:jhr", "tile:opus:jhr.001", "tile:opus:jhr.002", "tile:opus:jhr.003"),
    "HPC": ("tile:space:hpc", "tile:space:hpc.schumerout", "tile:stream:wikitube_hpc_schumer"),
    "AutoPost": ("tile:engine:autopost",),
    "Akiya": ("tile:market:japan_akiya", "tile:market:japan_akiya.fukui"),
    "Simulator": ("tile:sys:simulator",),
    "Tools": ("tile:tools:root", "tile:tools:benchmark"),
    "Benchmark": ("tile:tools:benchmark", "tile:harness:model_combination_benchmark", "tile:harness:wre_auto_researcher"),
}

# Privacy guard: never read or hash contents of metadata-only manuscripts.
PRIVATE_METADATA_ONLY_PATHS = frozenset({
    "WSP_knowledge/docs/Papers/Empirical_Evidence/rESP_Cross_Linguistic_Quantum_Signatures_2025.md",
    "modules/platform_integration/linkedin_agent/src/content/articles/ROI_to_RoC_Paradigm_Shift.md",
    "modules/foundups/esingularity/jhr/drafts/JHR_004.md",
})

TILE_ID_RE = re.compile(r"^tile:[a-z0-9_]+:[A-Za-z0-9._-]+$")
TEST_NAME_RE = re.compile(r"(^test_.*\.py$|.*_test\.py$|\.(test|spec)\.(js|mjs|cjs|ts|tsx)$)")
JS_IMPORT_RE = re.compile(
    r"""(?:import\s+(?:[\s\S]*?\s+from\s+)?|import\s*\(|require\s*\()\s*['"]([^'"]+)['"]""",
    re.MULTILINE,
)
HTML_SCRIPT_RE = re.compile(r"""<script[^>]+src=["']([^"']+)["']""", re.IGNORECASE)
HTTP_ROUTE_RE = re.compile(
    r"""@(?:app|router|bp)\.(?:get|post|put|delete|patch|websocket|route)\(|FastAPI\(|APIRouter\(|web\.Application\("""
)

_FORBIDDEN_LEAK_RE = re.compile(
    r"(?:(?<![A-Za-z0-9+.-])[A-Za-z]:[/\\]|/Users/|/home/|(?<![A-Za-z0-9:/])\\\\[A-Za-z0-9_.-]+|"
    r"AIza[0-9A-Za-z_-]{10,}|(?<![A-Za-z0-9])sk-[A-Za-z0-9]{10,}|oauth_token|"
    r"ghp_[A-Za-z0-9]{10,}|gho_[A-Za-z0-9]{10,}|AKIA[0-9A-Z]{12,}|"
    r"xoxb-[0-9A-Za-z-]+|-----BEGIN [A-Z ]*PRIVATE KEY-----)",
    re.IGNORECASE,
)

_PUBLIC_FORBIDDEN_SUBSTRINGS = (
    "JHR_004.md",
    "rESP_Cross_Linguistic_Quantum_Signatures_2025.md",
    "ROI_to_RoC_Paradigm_Shift.md",
    "synthetic_scheduled_fixture",
    "tile:socket:simulator.export_adapter",
    "open_socket:export_adapter",
    "pfmall_state_provider.py",
    "SimulatorStateProvider",
)

_TILE_ID_INLINE_RE = re.compile(r"\btile:[a-z0-9_]+:[A-Za-z0-9._-]*[A-Za-z0-9_-]")
_PUBLIC_FORBIDDEN_EXACT_KEYS = frozenset({
    "private_note",
    "private_notes",
    "private_provenance",
    "receipt_history",
})
_DROP_NESTED_VALUE = object()
_STRUCTURAL_EMPTY_LIST_KEYS = frozenset({
    "open_sockets",
    "drift_flags",
    "evaluated_modules",
    "children_tile_ids",
    "search_keywords",
    "author_aliases",
    "rename_history",
})


def _is_private_metadata_key(key: str) -> bool:
    """Return True if *key* denotes architect-only private metadata."""
    low = str(key).lower()
    return low.startswith("private_") or low in _PUBLIC_FORBIDDEN_EXACT_KEYS


def _is_principal_only_mapping(mapping: Mapping[str, Any]) -> bool:
    """Return True if *mapping* declares principal/architect visibility."""
    return (
        mapping.get("visibility_scope") == "principal_only"
        or mapping.get("visibility") == "012_architect"
    )


def _contains_invisible_tile_ref(value: str, public_ids: Set[str]) -> bool:
    """Return True if *value* references any ``tile:...`` ID absent from *public_ids*."""
    return any(m not in public_ids for m in _TILE_ID_INLINE_RE.findall(value))


def _is_restricted_public_string(
    value: str,
    public_ids: Set[str],
    restricted_socket_ids: Set[str],
    restricted_socket_paths: Set[str],
) -> bool:
    """Return True if *value* carries an invisible tile ref or forbidden restricted token."""
    if _contains_invisible_tile_ref(value, public_ids):
        return True
    if any(sid in value for sid in restricted_socket_ids):
        return True
    if any(rp and rp in value for rp in restricted_socket_paths):
        return True
    if any(sub in value for sub in _PUBLIC_FORBIDDEN_SUBSTRINGS):
        return True
    return False

_SCHEMA_PATH = Path(__file__).parent / "schemas" / "fractal_tile_graph.schema.json"
_CACHED_SCHEMA: Optional[Dict[str, Any]] = None


# ---------------------------------------------------------------------------
# Canonical Serialization & Leak Scanning
# ---------------------------------------------------------------------------

def canonical_json_bytes(obj: Any) -> bytes:
    """Serialize *obj* to deterministic UTF-8 canonical JSON bytes."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_canonical(obj: Any) -> str:
    """Return lowercase hex SHA-256 of canonical JSON representation."""
    return hashlib.sha256(canonical_json_bytes(obj)).hexdigest()


def compute_tiles_etag(tiles: Mapping[str, Any]) -> str:
    """Compute canonical SHA-256 ETag over the *tiles* mapping alone."""
    return sha256_canonical(dict(sorted(tiles.items())))


def scan_wsp71_leaks(obj: Any, *, prefix: str = "") -> List[str]:
    """Return list of field paths containing forbidden secrets or local OS paths."""
    findings: List[str] = []

    def _walk(node: Any, path: str) -> None:
        if isinstance(node, str):
            if _FORBIDDEN_LEAK_RE.search(node):
                findings.append(path or "<root>")
        elif isinstance(node, Mapping):
            for k, v in node.items():
                key_s = str(k)
                child_path = f"{path}.{key_s}" if path else key_s
                if _FORBIDDEN_LEAK_RE.search(key_s):
                    findings.append(child_path)
                _walk(v, child_path)
        elif isinstance(node, (list, tuple)):
            for idx, item in enumerate(node):
                _walk(item, f"{path}[{idx}]")

    _walk(obj, prefix)
    return findings


def _load_graph_schema() -> Dict[str, Any]:
    global _CACHED_SCHEMA
    if _CACHED_SCHEMA is None:
        _CACHED_SCHEMA = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
    return _CACHED_SCHEMA


# ---------------------------------------------------------------------------
# Scoring & Deterministic Classification (Sections 9.3 & 9.4)
# ---------------------------------------------------------------------------

def _require_int_range(value: Any, name: str, lo: int, hi: int) -> int:
    if type(value) is not int or not (lo <= value <= hi):
        raise ValueError(f"{name} must be an integer in [{lo}, {hi}], got {value!r}")
    return value


def wsp15_priority_band(mps: int) -> str:
    """Map canonical WSP 15 MPS (4..20) to priority band P0..P4."""
    if mps >= 16:
        return "P0"
    if mps >= 13:
        return "P1"
    if mps >= 10:
        return "P2"
    if mps >= 7:
        return "P3"
    return "P4"


def compute_wsp15_canonical(
    complexity: int,
    importance: int,
    deferability: int,
    impact: int,
) -> Dict[str, Any]:
    """Compute canonical WSP 15 MPS score (4..20) and priority band (P0..P4)."""
    c = _require_int_range(complexity, "complexity", 1, 5)
    i = _require_int_range(importance, "importance", 1, 5)
    d = _require_int_range(deferability, "deferability", 1, 5)
    im = _require_int_range(impact, "impact", 1, 5)
    mps = c + i + d + im
    return {
        "applicable": True,
        "complexity": c,
        "importance": i,
        "deferability": d,
        "impact": im,
        "mps": mps,
        "priority_band": wsp15_priority_band(mps),
    }


def compute_reusability(used_by_foundups_count: int, inbound_ast_imports: int) -> int:
    """Compute deterministic reusability axis (1..5)."""
    used = _require_int_range(used_by_foundups_count, "used_by_foundups_count", 0, 10000)
    inbound = _require_int_range(inbound_ast_imports, "inbound_ast_imports", 0, 100000)
    return min(5, 1 + used + (1 if inbound >= 5 else 0))


def compute_mall_rescue_score(
    *,
    impact: int,
    reusability: int,
    completeness: int,
    effort_to_green: int,
) -> int:
    """Compute Mall Rescue Score in [20, 100] from 1..5 axes."""
    im = _require_int_range(impact, "impact", 1, 5)
    ru = _require_int_range(reusability, "reusability", 1, 5)
    co = _require_int_range(completeness, "completeness", 1, 5)
    ef = _require_int_range(effort_to_green, "effort_to_green", 1, 5)
    return round(((im * 30) + (ru * 25) + (co * 25) + ((6 - ef) * 20)) / 5)


def classify_completeness(
    *,
    has_code: bool,
    has_tests: bool,
    wsp49_doc_count: int,
    has_requirements: bool = False,
    has_open_socket: bool = False,
    has_manifest: bool = False,
) -> int:
    """Deterministic completeness classifier (1..5) using locked WSP 49 thresholds."""
    docs = _require_int_range(wsp49_doc_count, "wsp49_doc_count", 0, 5)
    if has_code and has_tests and docs == 5 and has_requirements and not has_open_socket:
        return 5
    if has_code and has_tests and docs >= 4:
        return 4
    if has_code and (has_tests or docs >= 3):
        return 3
    if has_code or docs >= 2 or has_manifest:
        return 2
    return 1


def classify_impact(
    *,
    inbound_ast_imports: int,
    is_core_system: bool = False,
    stage: Optional[str] = None,
    public_surface_status: Optional[str] = None,
    implementation_status: Optional[str] = None,
    has_active_channel: bool = False,
    wsp49_doc_count: int = 0,
    has_tests: bool = False,
) -> int:
    """Deterministic impact classifier (1..5) from runtime coupling & registry truth."""
    inbound = _require_int_range(inbound_ast_imports, "inbound_ast_imports", 0, 100000)
    docs = _require_int_range(wsp49_doc_count, "wsp49_doc_count", 0, 5)
    if (
        inbound >= 5
        or is_core_system
        or (stage == "proto" and public_surface_status in ("listed", "promoted"))
    ):
        return 5
    if inbound >= 2 or implementation_status == "IMPLEMENTED":
        return 4
    if inbound >= 1 or has_active_channel:
        return 3
    if docs >= 2 or has_tests:
        return 2
    return 1


def classify_effort_to_green(completeness: int) -> int:
    """Deterministic effort_to_green classifier (1..5; lower is easier)."""
    co = _require_int_range(completeness, "completeness", 1, 5)
    return 6 - co


def state_label(state: str) -> str:
    """Return canonical textual label accompanying a traffic-light state."""
    if state not in STATE_LABELS:
        raise ValueError(f"Unknown tile state: {state!r}")
    return STATE_LABELS[state]


# ---------------------------------------------------------------------------
# Tile Factory & Graph Index Builders
# ---------------------------------------------------------------------------

def make_tile(
    *,
    tile_id: str,
    display_name: str,
    tile_kind: str,
    visibility_scope: str,
    owner_namespace: str,
    parent_tile_id: Optional[str],
    state: str,
    children_tile_ids: Optional[List[str]] = None,
    dag_edges: Optional[Mapping[str, Any]] = None,
    lifecycle_extra: Optional[Mapping[str, Any]] = None,
    wsp15_canonical: Optional[Mapping[str, Any]] = None,
    rescue_axes: Optional[Mapping[str, Any]] = None,
    commercial_lens: Optional[Mapping[str, Any]] = None,
    action_target: Optional[Mapping[str, Any]] = None,
    domain_override_manifest: Optional[Mapping[str, Any]] = None,
    evidence_status: Optional[str] = "verified_repo_or_receipt",
    search_keywords: Optional[Iterable[str]] = None,
    author_aliases: Optional[Iterable[str]] = None,
    metadata: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Construct a schema-compliant tile dict."""
    base_edges: Dict[str, Any] = {
        "imports_tiles": [],
        "used_by_foundups": [],
        "reusable_candidates": [],
        "oss_candidates": [],
        "cross_links": [],
        "collection_refs": [],
        "calls": [],
        "reads_from": [],
        "evaluates": [],
        "runs_through": [],
        "produces_receipt": [],
        "verified_by": [],
    }
    if dag_edges:
        for k, v in dag_edges.items():
            base_edges[k] = list(v) if isinstance(v, (list, tuple)) else v

    base_lifecycle: Dict[str, Any] = {
        "state": state,
        "state_label": state_label(state),
        "inbound_ast_imports": 0,
        "has_entrypoint": False,
        "contracts_present": [],
        "drift_flags": [],
    }
    if lifecycle_extra:
        base_lifecycle.update(dict(lifecycle_extra))
        base_lifecycle["state_label"] = state_label(base_lifecycle["state"])

    rescue_copy = dict(rescue_axes) if rescue_axes is not None else None
    score_val = rescue_copy.get("mall_rescue_score") if rescue_copy else None

    return {
        "tile_id": tile_id,
        "display_name": display_name,
        "rename_history": [],
        "tile_kind": tile_kind,
        "visibility_scope": visibility_scope,
        "owner_namespace": owner_namespace,
        "parent_tile_id": parent_tile_id,
        "children_tile_ids": list(children_tile_ids or []),
        "dag_edges": base_edges,
        "lifecycle": base_lifecycle,
        "wsp15_canonical": dict(wsp15_canonical) if wsp15_canonical else {
            "applicable": False,
            "mps": None,
            "priority_band": "N/A",
            "reason": "non_code_artifact_classified_by_publication_or_surface_evidence",
        },
        "mall_rescue_score": score_val,
        "rescue_axes": rescue_copy,
        "commercial_lens": dict(commercial_lens) if commercial_lens else {
            "monetization_class": "internal_infra",
            "licensable_standalone": False,
            "investor_summary": "",
        },
        "action_target": dict(action_target or {}),
        "domain_override_manifest": dict(domain_override_manifest) if domain_override_manifest else {
            "override_type": "none",
            "payload": {},
        },
        "evidence_status": evidence_status,
        "search_keywords": [str(k) for k in (search_keywords or []) if str(k)],
        "author_aliases": [str(a) for a in (author_aliases or []) if str(a)],
        "metadata": dict(metadata or {}),
    }


def _make_non_code_rescue(
    completeness: int,
    impact: int,
    reusability: int,
    effort_to_green: int,
    next_action: str,
    note: str,
) -> Dict[str, Any]:
    return {
        "completeness": completeness,
        "impact": impact,
        "reusability": reusability,
        "effort_to_green": effort_to_green,
        "mall_rescue_score": compute_mall_rescue_score(
            impact=impact,
            reusability=reusability,
            completeness=completeness,
            effort_to_green=effort_to_green,
        ),
        "next_action": next_action,
        "axis_rationale": note,
    }


def build_graph_indices(tiles: Mapping[str, Mapping[str, Any]]) -> Dict[str, Any]:
    """Compute ``counts``, ``links``, and ``search_index`` strictly from *tiles*."""
    by_state = Counter(t["lifecycle"]["state"] for t in tiles.values())
    by_kind = Counter(t["tile_kind"] for t in tiles.values())
    by_vis = Counter(t["visibility_scope"] for t in tiles.values())

    counts = {
        "total_tiles": len(tiles),
        "by_state": dict(sorted(by_state.items())),
        "by_kind": dict(sorted(by_kind.items())),
        "by_visibility": dict(sorted(by_vis.items())),
    }

    containment: List[Dict[str, Any]] = []
    dag: List[Dict[str, Any]] = []
    action_urls: Dict[str, str] = {}
    entries: List[Dict[str, Any]] = []

    for tid in sorted(tiles):
        t = tiles[tid]
        for idx, cid in enumerate(t.get("children_tile_ids", [])):
            if cid in tiles:
                containment.append({"source": tid, "target": cid, "order_index": idx})
        edges = t.get("dag_edges", {})
        for efield in DAG_TILE_EDGE_FIELDS:
            for target_id in edges.get(efield, []):
                if target_id in tiles:
                    dag.append({"source": tid, "target": target_id, "edge_type": efield})
        for uf in edges.get("used_by_foundups", []):
            if isinstance(uf, str) and uf.startswith("tile:") and uf in tiles:
                dag.append({"source": tid, "target": uf, "edge_type": "used_by_foundups"})

        primary_url = (t.get("action_target") or {}).get("primary_url")
        if isinstance(primary_url, str) and primary_url:
            action_urls[tid] = primary_url

        entries.append({
            "tile_id": tid,
            "display_name": t["display_name"],
            "tile_kind": t["tile_kind"],
            "parent_tile_id": t.get("parent_tile_id"),
            "state": t["lifecycle"]["state"],
            "keywords": list(t.get("search_keywords", [])),
            "author_aliases": list(t.get("author_aliases", [])),
        })

    aliases: Dict[str, List[str]] = {}
    for alias in SEARCH_ALIAS_KEYS:
        needle = alias.lower()
        hits: List[str] = []
        for preferred in _SEARCH_ALIAS_PRIORITY.get(alias, ()):
            if preferred in tiles and preferred not in hits:
                hits.append(preferred)
        for entry in entries:
            tid = entry["tile_id"]
            if tid in hits:
                continue
            haystack = " ".join(
                [entry["display_name"], tid]
                + entry["keywords"]
                + entry["author_aliases"]
            ).lower()
            if needle in haystack:
                hits.append(tid)
        aliases[alias] = hits

    return {
        "counts": counts,
        "links": {
            "containment": containment,
            "dag": dag,
            "action_urls": action_urls,
        },
        "search_index": {
            "aliases": aliases,
            "entries": entries,
        },
    }


# ---------------------------------------------------------------------------
# Dual-Scope Projection (012_architect -> public_mall)
# ---------------------------------------------------------------------------

_STRUCTURAL_DICT_FIELDS = (
    "metadata",
    "action_target",
    "commercial_lens",
    "rescue_axes",
    "wsp15_canonical",
    "lifecycle",
)
_STRUCTURAL_LIST_FIELDS = ("rename_history", "search_keywords", "author_aliases")
_STANDARD_TILE_KEYS = frozenset({
    "tile_id",
    "display_name",
    "rename_history",
    "tile_kind",
    "visibility_scope",
    "owner_namespace",
    "parent_tile_id",
    "children_tile_ids",
    "dag_edges",
    "lifecycle",
    "wsp15_canonical",
    "mall_rescue_score",
    "rescue_axes",
    "commercial_lens",
    "action_target",
    "domain_override_manifest",
    "evidence_status",
    "search_keywords",
    "author_aliases",
    "metadata",
})


def _sanitize_public_nested_value(
    node: Any,
    public_ids: Set[str],
    *,
    restricted_socket_ids: Set[str],
    restricted_socket_paths: Set[str],
    preserve_empty: bool = False,
) -> Any:
    """Recursively strip private keys, principal-only objects, and invisible tile refs."""
    if isinstance(node, Mapping):
        if _is_principal_only_mapping(node):
            return _DROP_NESTED_VALUE
        sock_id = node.get("socket_id")
        if isinstance(sock_id, str) and (
            sock_id in restricted_socket_ids or _contains_invisible_tile_ref(sock_id, public_ids)
        ):
            return _DROP_NESTED_VALUE

        cleaned: Dict[str, Any] = {}
        for k, v in node.items():
            key_s = str(k)
            if _is_private_metadata_key(key_s):
                continue
            if isinstance(v, str):
                if _is_restricted_public_string(v, public_ids, restricted_socket_ids, restricted_socket_paths):
                    continue
                cleaned[k] = v
            else:
                child_preserve_empty = (
                    (isinstance(v, list) and (len(v) == 0 or key_s in _STRUCTURAL_EMPTY_LIST_KEYS))
                    or (isinstance(v, Mapping) and len(v) == 0)
                )
                sub = _sanitize_public_nested_value(
                    v,
                    public_ids,
                    restricted_socket_ids=restricted_socket_ids,
                    restricted_socket_paths=restricted_socket_paths,
                    preserve_empty=child_preserve_empty,
                )
                if sub is not _DROP_NESTED_VALUE:
                    cleaned[k] = sub
        if len(node) > 0 and len(cleaned) == 0 and not preserve_empty:
            return _DROP_NESTED_VALUE
        return cleaned

    if isinstance(node, (list, tuple)):
        cleaned_list: List[Any] = []
        for item in node:
            if isinstance(item, str):
                if _is_restricted_public_string(item, public_ids, restricted_socket_ids, restricted_socket_paths):
                    continue
                cleaned_list.append(item)
            else:
                item_preserve_empty = isinstance(item, (Mapping, list, tuple)) and len(item) == 0
                sub = _sanitize_public_nested_value(
                    item,
                    public_ids,
                    restricted_socket_ids=restricted_socket_ids,
                    restricted_socket_paths=restricted_socket_paths,
                    preserve_empty=item_preserve_empty,
                )
                if sub is not _DROP_NESTED_VALUE:
                    cleaned_list.append(sub)
        if len(node) > 0 and len(cleaned_list) == 0 and not preserve_empty:
            return _DROP_NESTED_VALUE
        return cleaned_list

    return node


def _sanitize_public_tile(
    tile: Mapping[str, Any],
    public_ids: Set[str],
    *,
    restricted_socket_ids: Optional[Set[str]] = None,
    restricted_socket_subkeys: Optional[Set[str]] = None,
    restricted_socket_paths: Optional[Set[str]] = None,
) -> Dict[str, Any]:
    """Deep-copy a public tile and strip private fields, restricted sockets, and invisible references."""
    r_sock_ids = restricted_socket_ids or set()
    r_sock_subkeys = restricted_socket_subkeys or set()
    r_sock_paths = restricted_socket_paths or set()

    cloned = copy.deepcopy(dict(tile))
    for k in [key for key in cloned if _is_private_metadata_key(str(key))]:
        cloned.pop(k, None)

    meta = cloned.get("metadata")
    if isinstance(meta, dict):
        for k in [key for key in meta if _is_private_metadata_key(str(key))]:
            meta.pop(k, None)
        if isinstance(meta.get("open_sockets"), list):
            sanitized_sockets: List[Dict[str, Any]] = []
            for sock in meta["open_sockets"]:
                if not isinstance(sock, Mapping):
                    continue
                if _is_principal_only_mapping(sock):
                    continue
                sid = str(sock.get("socket_id") or "")
                if sid in r_sock_ids or (sid.startswith("tile:") and sid not in public_ids):
                    continue
                if any(sk and (f":{sk}" in sid or sid.endswith(f".{sk}")) for sk in r_sock_subkeys):
                    continue
                src_p = str(sock.get("source") or "")
                tgt_p = str(sock.get("target") or "")
                if (src_p and src_p in r_sock_paths) or (tgt_p and tgt_p in r_sock_paths):
                    continue
                sanitized_sockets.append(dict(sock))
            meta["open_sockets"] = sanitized_sockets
        be = meta.get("benchmark_evidence")
        if isinstance(be, dict):
            be.pop("receipt_history", None)
            be.pop("private_provenance", None)
            if isinstance(be.get("evaluated_modules"), list):
                be["evaluated_modules"] = [
                    mid for mid in be["evaluated_modules"]
                    if not (isinstance(mid, str) and mid.startswith("tile:") and mid not in public_ids)
                ]
        rv = meta.get("registry_verification")
        if isinstance(rv, dict):
            rv.pop("private_provenance", None)

    lifecycle = cloned.get("lifecycle")
    if isinstance(lifecycle, dict) and isinstance(lifecycle.get("drift_flags"), list):
        lifecycle["drift_flags"] = [
            df
            for df in lifecycle["drift_flags"]
            if df not in r_sock_ids
            and not (isinstance(df, str) and df.startswith("tile:") and df not in public_ids)
            and not any(
                isinstance(df, str) and sk and (df == f"open_socket:{sk}" or f":{sk}" in df)
                for sk in r_sock_subkeys
            )
        ]

    rescue = cloned.get("rescue_axes")
    if isinstance(rescue, dict) and isinstance(rescue.get("next_action"), str):
        na = rescue["next_action"]
        if (
            any(sid in na for sid in r_sock_ids)
            or any(rp in na for rp in r_sock_paths)
            or any(sk and sk in na for sk in r_sock_subkeys)
        ):
            has_public_seams = bool(isinstance(meta, dict) and meta.get("open_sockets"))
            rescue["next_action"] = (
                "Complete open contract seams in INTERFACE.md and ROADMAP.md"
                if has_public_seams
                else "Maintain verified tests and public contracts"
            )

    cloned["children_tile_ids"] = [
        cid for cid in cloned.get("children_tile_ids", []) if cid in public_ids
    ]
    edges = cloned.get("dag_edges", {})
    for efield in DAG_TILE_EDGE_FIELDS:
        if efield in edges:
            edges[efield] = [
                target_id for target_id in edges.get(efield, []) if target_id in public_ids
            ]
    if "used_by_foundups" in edges:
        edges["used_by_foundups"] = [
            uf for uf in edges["used_by_foundups"]
            if not (isinstance(uf, str) and uf.startswith("tile:") and uf not in public_ids)
        ]

    for sfield in _STRUCTURAL_DICT_FIELDS:
        if isinstance(cloned.get(sfield), Mapping):
            sanitized = _sanitize_public_nested_value(
                cloned[sfield],
                public_ids,
                restricted_socket_ids=r_sock_ids,
                restricted_socket_paths=r_sock_paths,
                preserve_empty=True,
            )
            cloned[sfield] = {} if sanitized is _DROP_NESTED_VALUE else sanitized

    dom = cloned.get("domain_override_manifest")
    if isinstance(dom, dict) and isinstance(dom.get("payload"), (Mapping, list)):
        sanitized_payload = _sanitize_public_nested_value(
            dom["payload"],
            public_ids,
            restricted_socket_ids=r_sock_ids,
            restricted_socket_paths=r_sock_paths,
            preserve_empty=True,
        )
        dom["payload"] = {} if sanitized_payload is _DROP_NESTED_VALUE else sanitized_payload

    for lfield in _STRUCTURAL_LIST_FIELDS:
        if isinstance(cloned.get(lfield), list):
            sanitized_list = _sanitize_public_nested_value(
                cloned[lfield],
                public_ids,
                restricted_socket_ids=r_sock_ids,
                restricted_socket_paths=r_sock_paths,
                preserve_empty=True,
            )
            cloned[lfield] = [] if sanitized_list is _DROP_NESTED_VALUE else sanitized_list

    for extra_key in [k for k in cloned if k not in _STANDARD_TILE_KEYS]:
        extra_val = cloned[extra_key]
        if isinstance(extra_val, str):
            if _is_restricted_public_string(extra_val, public_ids, r_sock_ids, r_sock_paths):
                cloned.pop(extra_key, None)
        elif isinstance(extra_val, (Mapping, list, tuple)):
            sanitized_extra = _sanitize_public_nested_value(
                extra_val,
                public_ids,
                restricted_socket_ids=r_sock_ids,
                restricted_socket_paths=r_sock_paths,
                preserve_empty=False,
            )
            if sanitized_extra is _DROP_NESTED_VALUE:
                cloned.pop(extra_key, None)
            else:
                cloned[extra_key] = sanitized_extra

    return cloned


def project_public_tile_graph(architect_graph: Mapping[str, Any]) -> Dict[str, Any]:
    """Project a scope-safe ``public_mall`` graph strictly from public non-RED tiles.

    Strips all ``visibility_scope == "principal_only"`` and ``lifecycle.state == "RED"``
    tiles, prunes invisible children/DAG/socket references, strips private notes, and computes
    ``search_index``, ``counts``, ``links``, and ``public_graph_etag`` strictly from
    the surviving public tiles alone so private-only edits never alter ``public_graph_etag``.
    """
    source_tiles = architect_graph.get("tiles", {})
    root_id = architect_graph.get("root_tile_id", ROOT_TILE_ID)

    # Traverse from root keeping only public non-RED nodes so no orphan under a
    # stripped parent survives into the public projection.
    public_ids: Set[str] = set()
    if root_id in source_tiles:
        root_tile = source_tiles[root_id]
        if (
            root_tile.get("visibility_scope") != "principal_only"
            and root_tile.get("lifecycle", {}).get("state") != "RED"
        ):
            queue: deque[str] = deque([root_id])
            while queue:
                cur = queue.popleft()
                if cur in public_ids:
                    continue
                public_ids.add(cur)
                for cid in source_tiles[cur].get("children_tile_ids", []):
                    ctile = source_tiles.get(cid)
                    if (
                        ctile is not None
                        and ctile.get("visibility_scope") != "principal_only"
                        and ctile.get("lifecycle", {}).get("state") != "RED"
                    ):
                        queue.append(cid)

    # Strip domain containers whose children were 100% withheld (e.g., RED-only domains)
    # so members do not enter empty domain folders in public_mall.
    withheld_empty_domain_ids: List[str] = []
    for tid in sorted(list(public_ids)):
        if not tid.startswith("tile:domain:"):
            continue
        orig_children = source_tiles[tid].get("children_tile_ids", [])
        if not any(cid in public_ids for cid in orig_children):
            public_ids.remove(tid)
            withheld_empty_domain_ids.append(tid)

    restricted_socket_ids: Set[str] = set()
    restricted_socket_subkeys: Set[str] = set()
    restricted_socket_paths: Set[str] = set()
    for stid, stile in source_tiles.items():
        if stid in public_ids:
            continue
        if stile.get("tile_kind") == "socket_slot" or str(stid).startswith("tile:socket:"):
            restricted_socket_ids.add(stid)
            smeta = stile.get("metadata") or {}
            sub_k = str(smeta.get("sub_key") or "").strip()
            if not sub_k and "." in stid:
                sub_k = stid.rsplit(".", 1)[-1].strip()
            if sub_k:
                restricted_socket_subkeys.add(sub_k)
            rpath = str((stile.get("action_target") or {}).get("repo_path") or "").strip()
            if rpath:
                restricted_socket_paths.add(rpath)

    pub_tiles = {
        tid: _sanitize_public_tile(
            source_tiles[tid],
            public_ids,
            restricted_socket_ids=restricted_socket_ids,
            restricted_socket_subkeys=restricted_socket_subkeys,
            restricted_socket_paths=restricted_socket_paths,
        )
        for tid in sorted(public_ids)
    }
    pub_etag = compute_tiles_etag(pub_tiles)
    indices = build_graph_indices(pub_tiles)

    out_pub: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_at_utc": architect_graph.get("generated_at_utc", ""),
        "git_revision": architect_graph.get("git_revision", ""),
        "graph_etag": pub_etag,
        "public_graph_etag": pub_etag,
        "scope": "public_mall",
        "root_tile_id": root_id,
        "counts": indices["counts"],
        "links": indices["links"],
        "search_index": indices["search_index"],
        "tiles": pub_tiles,
    }
    if withheld_empty_domain_ids:
        out_pub["withheld_empty_domain_ids"] = withheld_empty_domain_ids
    if "source_revisions" in architect_graph:
        out_pub["source_revisions"] = copy.deepcopy(architect_graph["source_revisions"])
    return out_pub


# ---------------------------------------------------------------------------
# Graph Validator
# ---------------------------------------------------------------------------

def _validate_tile_enums_and_scores(tid: str, tile: Mapping[str, Any], errors: List[str]) -> None:
    if tile.get("tile_kind") not in VALID_TILE_KINDS:
        errors.append(f"{tid}: invalid tile_kind {tile.get('tile_kind')!r}")
    if tile.get("visibility_scope") not in VALID_VISIBILITY_SCOPES:
        errors.append(f"{tid}: invalid visibility_scope {tile.get('visibility_scope')!r}")
    owner_ns = tile.get("owner_namespace")
    if not isinstance(owner_ns, str) or not owner_ns:
        errors.append(f"{tid}: missing owner_namespace")

    lifecycle = tile.get("lifecycle")
    if not isinstance(lifecycle, Mapping):
        errors.append(f"{tid}: lifecycle must be an object")
    else:
        if lifecycle.get("state") not in VALID_STATES:
            errors.append(f"{tid}: invalid lifecycle.state {lifecycle.get('state')!r}")
        if not isinstance(lifecycle.get("state_label"), str) or not lifecycle.get("state_label"):
            errors.append(f"{tid}: missing lifecycle.state_label")

    override = tile.get("domain_override_manifest")
    if isinstance(override, Mapping):
        otype = override.get("override_type", "none")
        if otype not in VALID_OVERRIDE_TYPES:
            errors.append(f"{tid}: invalid override_type {otype!r}")

    wsp15 = tile.get("wsp15_canonical")
    if isinstance(wsp15, Mapping) and wsp15.get("applicable") is True:
        mps = wsp15.get("mps")
        if type(mps) is not int or not (4 <= mps <= 20):
            errors.append(f"{tid}: invalid wsp15_canonical.mps {mps!r}")
        if wsp15.get("priority_band") not in {"P0", "P1", "P2", "P3", "P4"}:
            errors.append(f"{tid}: invalid wsp15_canonical.priority_band {wsp15.get('priority_band')!r}")

    score = tile.get("mall_rescue_score")
    if score is not None and (type(score) is not int or not (20 <= score <= 100)):
        errors.append(f"{tid}: invalid mall_rescue_score {score!r}")


def _scan_public_tile_privacy_violations(
    tid: str,
    tile: Mapping[str, Any],
    public_ids: Set[str],
) -> List[str]:
    """Recursively detect private keys, principal-only objects, or invisible tile refs inside a public tile."""
    violations: List[str] = []

    def _walk(node: Any, path: str) -> None:
        if isinstance(node, Mapping):
            if path and _is_principal_only_mapping(node):
                violations.append(f"{tid}: principal_only nested object leaked at {path}")
            for k, v in node.items():
                key_s = str(k)
                child_path = f"{path}.{key_s}" if path else key_s
                if _is_private_metadata_key(key_s) and (path or key_s not in {"private_notes", "private_note"}):
                    violations.append(f"{tid}: private metadata key {key_s!r} leaked at {child_path}")
                _walk(v, child_path)
        elif isinstance(node, (list, tuple)):
            for idx, item in enumerate(node):
                _walk(item, f"{path}[{idx}]")
        elif isinstance(node, str):
            for m in _TILE_ID_INLINE_RE.findall(node):
                if m not in public_ids:
                    violations.append(
                        f"{tid}: restricted or invisible tile reference {m!r} leaked at {path}"
                    )

    _walk(tile, "")
    return violations


def validate_tile_graph(graph: Mapping[str, Any], *, check_schema: bool = True) -> List[str]:
    """Validate structural integrity, acyclicity, enums, references, and scope rules.

    Returns a list of error strings; an empty list indicates a valid graph.
    """
    errors: List[str] = []
    if not isinstance(graph, Mapping):
        return ["graph must be a mapping"]

    if graph.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"invalid schema_version: {graph.get('schema_version')!r}")

    scope = graph.get("scope")
    if scope not in VALID_SCOPES:
        errors.append(f"invalid scope: {scope!r}")

    tiles = graph.get("tiles")
    if not isinstance(tiles, Mapping) or not tiles:
        errors.append("tiles must be a non-empty mapping")
        return errors

    root_id = graph.get("root_tile_id")
    if not isinstance(root_id, str) or root_id not in tiles:
        errors.append(f"root_tile_id {root_id!r} missing from tiles")
        return errors

    # Check key/tile_id consistency, enums, parent/child refs, and dag_edges refs.
    seen_tile_ids: Set[str] = set()
    for key, tile in tiles.items():
        if not isinstance(key, str) or not TILE_ID_RE.match(key):
            errors.append(f"invalid tile key format: {key!r}")
            continue
        if not isinstance(tile, Mapping):
            errors.append(f"{key}: tile value must be an object")
            continue
        tid = tile.get("tile_id")
        if tid != key:
            errors.append(f"{key}: mismatched tile_id {tid!r}")
        if isinstance(tid, str):
            if tid in seen_tile_ids:
                errors.append(f"duplicate tile_id: {tid}")
            seen_tile_ids.add(tid)

        _validate_tile_enums_and_scores(key, tile, errors)

        pid = tile.get("parent_tile_id")
        if key == root_id:
            if pid is not None:
                errors.append(f"{key}: root tile must have parent_tile_id=None")
        else:
            if pid is None or pid not in tiles:
                errors.append(f"{key}: invalid or missing parent_tile_id {pid!r}")
            elif key not in tiles[pid].get("children_tile_ids", []):
                errors.append(f"{key}: missing from parent {pid}.children_tile_ids")

        children = tile.get("children_tile_ids", [])
        if not isinstance(children, list):
            errors.append(f"{key}: children_tile_ids must be a list")
        else:
            if len(children) != len(set(children)):
                errors.append(f"{key}: duplicate entries in children_tile_ids")
            for cid in children:
                if cid not in tiles:
                    errors.append(f"{key}: unresolved child reference {cid!r}")
                elif tiles[cid].get("parent_tile_id") != key:
                    errors.append(f"{key}: child {cid!r} has mismatched parent_tile_id")

        edges = tile.get("dag_edges", {})
        if not isinstance(edges, Mapping):
            errors.append(f"{key}: dag_edges must be an object")
        else:
            for efield in DAG_TILE_EDGE_FIELDS:
                for target_id in edges.get(efield, []):
                    if target_id == key:
                        errors.append(f"{key}: self-loop in dag_edges.{efield}")
                    elif target_id not in tiles:
                        errors.append(f"{key}: unresolved dag_edges.{efield} ref {target_id!r}")
            for uf in edges.get("used_by_foundups", []):
                if isinstance(uf, str) and uf.startswith("tile:") and uf not in tiles:
                    errors.append(f"{key}: unresolved dag_edges.used_by_foundups ref {uf!r}")

    # Containment tree acyclicity + full reachability from root_tile_id.
    visited: Set[str] = set()
    active_stack: Set[str] = set()

    def _dfs_tree(node_id: str) -> None:
        if node_id in active_stack:
            errors.append(f"cycle detected in containment tree at {node_id}")
            return
        if node_id in visited:
            errors.append(f"diamond/re-entry detected in containment tree at {node_id}")
            return
        active_stack.add(node_id)
        visited.add(node_id)
        for cid in tiles[node_id].get("children_tile_ids", []):
            if cid in tiles:
                _dfs_tree(cid)
        active_stack.remove(node_id)

    _dfs_tree(root_id)
    unreachable = set(tiles.keys()) - visited
    if unreachable:
        errors.append(f"unreachable or cyclic disconnected tiles: {sorted(unreachable)[:10]}")

    # Check parent_tile_id upward walk for cycles as well.
    for key in tiles:
        seen_up: Set[str] = set()
        cur: Optional[str] = key
        while cur is not None:
            if cur in seen_up:
                errors.append(f"parent_tile_id cycle detected involving {cur}")
                break
            seen_up.add(cur)
            cur = tiles.get(cur, {}).get("parent_tile_id")

    # Public scope strict guarantees.
    if scope == "public_mall":
        public_tile_ids = set(tiles.keys())
        for key, tile in tiles.items():
            if tile.get("visibility_scope") == "principal_only":
                errors.append(f"{key}: principal_only tile leaked into public_mall")
            if tile.get("lifecycle", {}).get("state") == "RED":
                errors.append(f"{key}: RED tile leaked into public_mall")
            if "private_notes" in tile or "private_note" in tile:
                errors.append(f"{key}: private_notes leaked into public_mall")
            meta_os = (tile.get("metadata") or {}).get("open_sockets")
            if isinstance(meta_os, list):
                for sock in meta_os:
                    if not isinstance(sock, Mapping):
                        continue
                    sid = str(sock.get("socket_id") or "")
                    if sock.get("visibility_scope") == "principal_only" or (
                        sid.startswith("tile:") and sid not in tiles
                    ):
                        errors.append(
                            f"{key}: restricted or invisible socket {sid!r} leaked in metadata.open_sockets"
                        )
            errors.extend(_scan_public_tile_privacy_violations(key, tile, public_tile_ids))
        serialized = json.dumps(dict(graph), ensure_ascii=False)
        for bad in _PUBLIC_FORBIDDEN_SUBSTRINGS:
            if bad in serialized:
                errors.append(f"public_mall contains forbidden private substring: {bad}")
        leaks = scan_wsp71_leaks(graph)
        if leaks:
            errors.append(f"public_mall WSP 71 leak detected at: {leaks[:5]}")

    if check_schema and not errors:
        try:
            import jsonschema
            jsonschema.validate(instance=dict(graph), schema=_load_graph_schema())
        except ImportError:
            pass
        except Exception as exc:
            errors.append(f"schema validation failed: {exc}")

    return errors


# ---------------------------------------------------------------------------
# Tracked Repository Discovery & AST Scanner
# ---------------------------------------------------------------------------

def _collect_tracked_files(repo_root: Path) -> List[str]:
    """Return sorted POSIX relative paths of tracked files under *repo_root*."""
    if (repo_root / ".git").exists():
        try:
            proc = subprocess.run(
                ["git", "-C", str(repo_root), "ls-files", "-z"],
                capture_output=True,
                check=True,
            )
            items = [
                p for p in proc.stdout.decode("utf-8", errors="replace").split("\0")
                if p and (repo_root / p).is_file()
            ]
            if items:
                return sorted(items)
        except Exception:
            pass

    ignored_roots = {".git", "__pycache__", "node_modules", ".venv", "temp", ".pytest_cache", ".worktrees"}
    result: List[str] = []
    for root, dirs, files in os.walk(repo_root):
        dirs[:] = sorted(d for d in dirs if d not in ignored_roots and not d.startswith("."))
        rel_dir = Path(root).relative_to(repo_root)
        for fname in sorted(files):
            if fname.endswith(".pyc") or fname.startswith(".env"):
                continue
            rel = (rel_dir / fname).as_posix()
            if rel.startswith("./"):
                rel = rel[2:]
            result.append(rel)
    return sorted(result)


def _load_git_blobs(repo_root: Path) -> Dict[str, bytes]:
    """Stream committed blobs once via ``git archive`` and overlay dirty working files."""
    blobs: Dict[str, bytes] = {}
    if not (repo_root / ".git").exists():
        return blobs
    try:
        proc = subprocess.Popen(
            ["git", "-C", str(repo_root), "-c", "core.autocrlf=false", "archive", "HEAD"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        assert proc.stdout is not None
        try:
            with tarfile.open(fileobj=proc.stdout, mode="r|") as tf:
                for member in tf:
                    if member.isfile() and member.name not in PRIVATE_METADATA_ONLY_PATHS:
                        extracted = tf.extractfile(member)
                        blobs[member.name] = extracted.read() if extracted else b""
            # Drain trailing tar zero-padding before wait() so git archive cannot block on Windows pipes.
            while proc.stdout.read(65536):
                pass
        finally:
            proc.stdout.close()
        if proc.wait() != 0:
            blobs.clear()
            return blobs
        diff = subprocess.run(
            ["git", "-C", str(repo_root), "diff", "--name-only", "-z", "HEAD"],
            capture_output=True,
            check=False,
        )
        if diff.returncode == 0:
            for rel in diff.stdout.decode("utf-8", errors="replace").split("\0"):
                if rel and rel not in PRIVATE_METADATA_ONLY_PATHS:
                    target = repo_root / rel
                    if target.is_file():
                        blobs[rel] = target.read_bytes()
                    else:
                        blobs.pop(rel, None)
    except Exception:
        blobs.clear()
    return blobs


_CENSUS_TREE_CACHE: Dict[Tuple[str, str], Tuple[FrozenSet[str], FrozenSet[str]]] = {}


def _load_census_git_tree(
    repo_root: Path,
    census_rev: str,
) -> Tuple[Optional[FrozenSet[str]], Optional[FrozenSet[str]]]:
    """Return cached ``(files, dir_prefixes)`` at *census_rev* when git history is available."""
    if not census_rev or census_rev == "unknown" or not (repo_root / ".git").exists():
        return None, None
    cache_key = (str(repo_root), census_rev)
    cached = _CENSUS_TREE_CACHE.get(cache_key)
    if cached is not None:
        return cached
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo_root), "ls-tree", "-r", "-z", "--name-only", census_rev],
            capture_output=True,
            check=True,
        )
    except Exception:
        return None, None
    files: Set[str] = set()
    dirs: Set[str] = set()
    for entry in proc.stdout.decode("utf-8", errors="replace").split("\0"):
        norm = entry.replace("\\", "/").strip("/")
        if not norm:
            continue
        files.add(norm)
        parts = norm.split("/")
        for depth in range(1, len(parts)):
            dirs.add("/".join(parts[:depth]))
    if not files:
        return None, None
    result = (frozenset(files), frozenset(dirs))
    _CENSUS_TREE_CACHE[cache_key] = result
    return result


def _parse_gitmodules_urls(
    repo_root: Path,
    blob_cache: Optional[Mapping[str, bytes]] = None,
) -> Dict[str, str]:
    """Parse submodule ``path -> normalized GitHub URL`` from tracked ``.gitmodules``."""
    txt = _read_text_safe(repo_root, ".gitmodules", blob_cache=blob_cache) or ""
    urls_by_path: Dict[str, str] = {}
    cur_path: Optional[str] = None
    cur_url: Optional[str] = None
    for raw_line in txt.splitlines():
        line = raw_line.strip()
        if not line or line.startswith(("#", ";")):
            continue
        if line.startswith("["):
            if cur_path and cur_url:
                urls_by_path[cur_path] = cur_url
            cur_path = None
            cur_url = None
            continue
        if "=" in line:
            key, val = (p.strip() for p in line.split("=", 1))
            if key == "path":
                cur_path = val.strip().rstrip("/")
            elif key == "url":
                cleaned = val.strip()
                if cleaned.endswith(".git"):
                    cleaned = cleaned[:-4]
                cur_url = cleaned
    if cur_path and cur_url:
        urls_by_path[cur_path] = cur_url
    return urls_by_path


def _read_text_safe(
    repo_root: Path,
    rel_path: str,
    blob_cache: Optional[Mapping[str, bytes]] = None,
) -> Optional[str]:
    if rel_path in PRIVATE_METADATA_ONLY_PATHS:
        raise PermissionError(f"Metadata-only guard forbids reading content of {rel_path}")
    if blob_cache is not None and rel_path in blob_cache:
        raw = blob_cache[rel_path]
    else:
        target = repo_root / rel_path
        if not target.is_file():
            return None
        raw = target.read_bytes()
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        return raw.decode("utf-16", errors="replace")
    return raw.decode("utf-8-sig", errors="replace")


def _read_json_safe(
    repo_root: Path,
    rel_path: str,
    default: Any = None,
    blob_cache: Optional[Mapping[str, bytes]] = None,
) -> Any:
    txt = _read_text_safe(repo_root, rel_path, blob_cache=blob_cache)
    if txt is None:
        return default
    try:
        return json.loads(txt)
    except Exception:
        return default


def _is_test_path(rel_path: str) -> bool:
    parts = rel_path.split("/")
    if "tests" in parts or "__tests__" in parts:
        return True
    return bool(TEST_NAME_RE.match(parts[-1]))


def _owner_key_for_path(rel_path: str) -> str:
    parts = rel_path.split("/")
    if len(parts) >= 4 and parts[0] == "modules":
        return f"modules/{parts[1]}/{parts[2]}"
    if parts[0] == "holo_index":
        return "holo_index"
    if len(parts) >= 2 and parts[0] == "extensions" and parts[1] == "reddog":
        return "extensions/reddog"
    return parts[0]


def _tile_id_for_owner(owner_key: str) -> str:
    if owner_key == "modules/foundups/simulator":
        return "tile:sys:simulator"
    if owner_key == "holo_index":
        return "tile:sys:holo_index"
    if owner_key == "extensions/reddog":
        return "tile:sys:extensions_reddog"
    if owner_key.startswith("modules/"):
        _, dom, mod = owner_key.split("/", 2)
        return f"tile:mod:{dom}.{mod}"
    return f"tile:root:{owner_key}"


def _resolve_import_to_owner(
    module_name: str,
    level: int,
    source_path: str,
    known_owners: Set[str],
) -> Optional[str]:
    if level > 0:
        src_parts = source_path.split("/")[:-1]
        up = level - 1
        if up > len(src_parts):
            return None
        base_parts = src_parts[: len(src_parts) - up] if up > 0 else src_parts
        dotted = ".".join(base_parts + module_name.split(".")) if module_name else ".".join(base_parts)
    else:
        dotted = module_name

    if not dotted:
        return None
    segs = dotted.split(".")
    if len(segs) >= 3 and segs[0] == "modules":
        cand = f"modules/{segs[1]}/{segs[2]}"
        if cand in known_owners:
            return cand
    if segs[0] == "holo_index" and "holo_index" in known_owners:
        return "holo_index"
    if len(segs) >= 2 and segs[0] == "extensions" and segs[1] == "reddog":
        return "extensions/reddog"
    return None


def _resolve_js_specifier(spec: str, source_path: str, known_owners: Set[str]) -> Optional[str]:
    if spec.startswith("."):
        base = Path(source_path).parent
        resolved = (base / spec).as_posix()
        parts: List[str] = []
        for seg in resolved.split("/"):
            if seg in ("", "."):
                continue
            if seg == "..":
                if parts:
                    parts.pop()
            else:
                parts.append(seg)
        ok = _owner_key_for_path("/".join(parts))
        return ok if ok in known_owners else None
    for owner in known_owners:
        if spec.startswith(owner + "/") or spec == owner:
            return owner
    return None


def _parse_modules_to_score(text: str) -> Dict[str, Dict[str, Any]]:
    entries: Dict[str, Dict[str, Any]] = {}
    current_name: Optional[str] = None
    current_start = 1
    current_path: Optional[str] = None
    current_scores: Dict[str, int] = {}
    for idx, raw in enumerate(text.splitlines(), 1):
        m_name = re.match(r"^\s*-\s*name:\s*['\"]?([^'\"\s#]+)", raw)
        if m_name:
            if current_name and current_path:
                entries[current_path] = {"name": current_name, "line": current_start, "scores": dict(current_scores)}
            current_name = m_name.group(1)
            current_start = idx
            current_path = None
            current_scores = {}
            continue
        if current_name:
            m_path = re.match(r"^\s*path:\s*['\"]?([^'\"\s#]+)", raw)
            if m_path:
                current_path = m_path.group(1).rstrip("/")
            m_dim = re.match(r"^\s*(complexity|importance|deferability|impact):\s*(\d+)", raw)
            if m_dim:
                current_scores[m_dim.group(1)] = int(m_dim.group(2))
    if current_name and current_path:
        entries[current_path] = {"name": current_name, "line": current_start, "scores": dict(current_scores)}
    return entries


def _extract_open_sockets(
    owner_key: str,
    tracked_set: Set[str],
    repo_root: Path,
    blob_cache: Optional[Mapping[str, bytes]] = None,
) -> List[Dict[str, Any]]:
    sockets: List[Dict[str, Any]] = []
    seen: Set[str] = set()
    if owner_key == "modules/foundups/simulator":
        sockets.append({
            "socket_id": "tile:socket:simulator.export_adapter",
            "status": "BLUE_OPEN_SOCKET",
            "source": "modules/foundups/simulator/adapters/pfmall_state_provider.py",
            "target": "modules/foundups/pfmall/member_catalog_export.py",
        })
        seen.add("tile:socket:simulator.export_adapter")

    for doc_name in ("INTERFACE.md", "ROADMAP.md"):
        doc_path = f"{owner_key}/{doc_name}"
        if doc_path not in tracked_set:
            continue
        txt = _read_text_safe(repo_root, doc_path, blob_cache=blob_cache) or ""
        for idx, line in enumerate(txt.splitlines(), 1):
            stripped = line.strip()
            if re.match(r"^-\s*\[\s\]\s+", stripped) or "SPECIFIED_NOT_IMPLEMENTED" in stripped or "open socket" in stripped.lower():
                key = f"{doc_name}:{idx}"
                if key not in seen:
                    sockets.append({
                        "socket_id": f"seam:{owner_key}:{doc_name.lower()}:L{idx}",
                        "status": "PLANNED_OR_OPEN",
                        "source": f"{doc_path}:L{idx}",
                        "summary": re.sub(r"^-\s*\[\s\]\s+", "", stripped)[:140],
                    })
                    seen.add(key)
                if len(sockets) >= 8:
                    break
        if len(sockets) >= 8:
            break
    return sockets


def _scan_code_modules(
    repo_root: Path,
    tracked_files: List[str],
    tracked_set: Set[str],
    blob_cache: Optional[Mapping[str, bytes]] = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, List[str]]]:
    """Scan monorepo modules and compute 6-channel coupling & dual scores."""
    domain_modules: Dict[str, Set[str]] = defaultdict(set)
    owner_files: Dict[str, List[str]] = defaultdict(list)

    for rel in tracked_files:
        parts = rel.split("/")
        if len(parts) >= 4 and parts[0] == "modules":
            dom, mod = parts[1], parts[2]
            if not mod.startswith(".") and mod != "__pycache__":
                domain_modules[dom].add(mod)
                owner_files[f"modules/{dom}/{mod}"].append(rel)
        elif parts[0] == "holo_index":
            owner_files["holo_index"].append(rel)
        elif len(parts) >= 2 and parts[0] == "extensions" and parts[1] == "reddog":
            owner_files["extensions/reddog"].append(rel)

    known_owners: Set[str] = {
        f"modules/{dom}/{mod}" for dom, mods in domain_modules.items() for mod in mods
    }
    if "holo_index" in owner_files:
        known_owners.add("holo_index")
    if "extensions/reddog" in owner_files:
        known_owners.add("extensions/reddog")

    reg_data = _read_json_safe(repo_root, "modules/foundups/foundup_registry.json", {"entities": []}, blob_cache=blob_cache)
    reg_entities = reg_data.get("entities", [])
    reg_by_module: Dict[str, Dict[str, Any]] = {}
    foundup_owner_map: Dict[str, str] = {}
    for ent in reg_entities:
        mp = ent.get("module_path")
        if mp:
            clean_mp = mp.rstrip("/")
            reg_by_module[clean_mp] = ent
            foundup_owner_map[clean_mp] = ent["foundup_id"]

    skills_reg = _read_json_safe(repo_root, "modules/infrastructure/wre_core/skillz/skills_registry_v2.json", {}, blob_cache=blob_cache)
    skills_reg_locations = {
        str(meta.get("location", "")).replace("\\", "/").strip("/")
        for meta in skills_reg.get("skills", {}).values()
        if meta.get("location")
    }

    rolodex = _read_json_safe(repo_root, "holo_index/docs/command_rolodex.json", {}, blob_cache=blob_cache)
    rolodex_owners = {
        _owner_key_for_path(str(cmd.get("path", "")).replace("\\", "/"))
        for cmd in rolodex.get("commands", [])
    } & known_owners

    reddog_manifest_text = _read_text_safe(repo_root, "scripts/reddog_backend_manifest.json", blob_cache=blob_cache) or ""
    reddog_manifest_owners = {
        ok for ok in known_owners
        if (ok + "/") in reddog_manifest_text or (ok.replace("/", ".") in reddog_manifest_text)
    }

    main_py_text = _read_text_safe(repo_root, "main.py", blob_cache=blob_cache) or ""
    nav_py_text = _read_text_safe(repo_root, "NAVIGATION.py", blob_cache=blob_cache) or ""
    firebase_text = _read_text_safe(repo_root, "firebase.json", blob_cache=blob_cache) or ""
    mts_entries = _parse_modules_to_score(
        _read_text_safe(repo_root, "modules/development/modules_to_score.yaml", blob_cache=blob_cache) or ""
    )

    runtime_inbound: Dict[str, Set[str]] = defaultdict(set)
    test_inbound: Dict[str, Set[str]] = defaultdict(set)
    outbound_imports: Dict[str, Set[str]] = defaultdict(set)
    foundup_to_targets: Dict[str, Set[str]] = defaultdict(set)
    cli_main_guard_owners: Set[str] = set()
    http_route_owners: Set[str] = set()
    script_ref_owners: Set[str] = set()
    public_html_ref_owners: Set[str] = set()
    skill_md_owner_refs: Set[str] = set()

    for rel in tracked_files:
        if rel in PRIVATE_METADATA_ONLY_PATHS:
            continue
        src_owner = _owner_key_for_path(rel)
        is_test = _is_test_path(rel)

        if rel.endswith(".py"):
            text = _read_text_safe(repo_root, rel, blob_cache=blob_cache) or ""
            if not is_test and src_owner in known_owners:
                if 'if __name__ == "__main__":' in text or "if __name__ == '__main__':" in text:
                    cli_main_guard_owners.add(src_owner)
                if HTTP_ROUTE_RE.search(text):
                    http_route_owners.add(src_owner)
            if rel.startswith("scripts/") and not is_test:
                for ok in known_owners:
                    if ok in text or ok.replace("/", ".") in text:
                        script_ref_owners.add(ok)

            if "import" not in text:
                continue
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", SyntaxWarning)
                    tree = ast.parse(text, filename=rel)
            except SyntaxError:
                continue

            for node in ast.walk(tree):
                targets: List[Tuple[str, int]] = []
                if isinstance(node, ast.Import):
                    targets.extend((alias.name, 0) for alias in node.names)
                elif isinstance(node, ast.ImportFrom):
                    targets.append((node.module or "", node.level or 0))
                for mod_str, lvl in targets:
                    tgt_owner = _resolve_import_to_owner(mod_str, lvl, rel, known_owners)
                    if tgt_owner and tgt_owner != src_owner:
                        if is_test:
                            test_inbound[tgt_owner].add(rel)
                        else:
                            runtime_inbound[tgt_owner].add(rel)
                            if src_owner in known_owners:
                                outbound_imports[src_owner].add(tgt_owner)
                            if src_owner in foundup_owner_map:
                                foundup_to_targets[tgt_owner].add(foundup_owner_map[src_owner])

        elif rel.endswith((".js", ".mjs", ".cjs", ".ts", ".tsx")):
            text = _read_text_safe(repo_root, rel, blob_cache=blob_cache) or ""
            if "import" in text or "require" in text:
                for m in JS_IMPORT_RE.finditer(text):
                    tgt_owner = _resolve_js_specifier(m.group(1), rel, known_owners)
                    if tgt_owner and tgt_owner != src_owner:
                        if is_test:
                            test_inbound[tgt_owner].add(rel)
                        else:
                            runtime_inbound[tgt_owner].add(rel)
                            if src_owner in known_owners:
                                outbound_imports[src_owner].add(tgt_owner)

        elif rel.endswith(".html") and rel.startswith("public/"):
            text = _read_text_safe(repo_root, rel, blob_cache=blob_cache) or ""
            for m in HTML_SCRIPT_RE.finditer(text):
                src_attr = m.group(1)
                for ok in known_owners:
                    mod_name = ok.split("/")[-1]
                    if ok in src_attr or f"/{mod_name}/" in src_attr:
                        public_html_ref_owners.add(ok)
                if "ecosystem-growth.js" in src_attr and "modules/foundups/ecosystem_animation" in known_owners:
                    public_html_ref_owners.add("modules/foundups/ecosystem_animation")
                if "foundup-cube.js" in src_attr and "modules/foundups/simulator" in known_owners:
                    public_html_ref_owners.add("modules/foundups/simulator")

        elif rel.endswith(("SKILL.md", "SKILLz.md")):
            text = _read_text_safe(repo_root, rel, blob_cache=blob_cache) or ""
            if "modules" in text or "holo_index" in text or "reddog" in text:
                for ok in known_owners:
                    if ok in text or ok.replace("/", ".") in text:
                        skill_md_owner_refs.add(ok)

    bridge_used: Dict[str, Set[str]] = defaultdict(set)
    pfc = _read_text_safe(repo_root, "modules/communication/moltbot_bridge/src/pfmall_catalog.py", blob_cache=blob_cache) or ""
    if "modules.foundups.simulator.adapters.pfmall_state_provider" in pfc:
        bridge_used["modules/foundups/simulator"].add("pfmall")
    fb = _read_text_safe(repo_root, "modules/foundups/simulator/adapters/fam_bridge.py", blob_cache=blob_cache) or ""
    if "modules.foundups.agent_market" in fb:
        bridge_used["modules/foundups/simulator"].add("agent_market")

    module_nodes: List[Dict[str, Any]] = []
    for owner_key in sorted(known_owners):
        owned = sorted(owner_files[owner_key])
        if owner_key.startswith("modules/"):
            _, domain, mod_name = owner_key.split("/", 2)
        elif owner_key == "holo_index":
            domain, mod_name = "system_infra", "holo_index"
        else:
            domain, mod_name = "system_infra", "extensions_reddog"

        tile_id = _tile_id_for_owner(owner_key)
        contracts_present = {
            name: f"{owner_key}/{name}" in tracked_set
            for name in ("README.md", "INTERFACE.md", "ROADMAP.md", "ModLog.md", "tests/README.md", "requirements.txt")
        }
        wsp49_doc_count = sum(
            1 for name in ("README.md", "INTERFACE.md", "ROADMAP.md", "ModLog.md", "tests/README.md")
            if contracts_present[name]
        )
        test_files = [p for p in owned if _is_test_path(p) and p.endswith((".py", ".js", ".mjs", ".cjs", ".ts"))]
        code_files = [p for p in owned if not _is_test_path(p) and p.endswith((".py", ".js", ".mjs", ".cjs", ".ts", ".tsx"))]
        has_tests = bool(test_files)

        rt_count = len(runtime_inbound.get(owner_key, set()))
        t_count = len(test_inbound.get(owner_key, set()))
        outbound = sorted(_tile_id_for_owner(o) for o in outbound_imports.get(owner_key, set()))

        reg_ent = reg_by_module.get(owner_key)
        dotted_owner = owner_key.replace("/", ".")

        ch1_inbound = rt_count >= 1
        ch2_web = (
            owner_key in http_route_owners
            or owner_key in public_html_ref_owners
            or f"{owner_key}/http_api.py" in tracked_set
            or f"{owner_key}/sse_server.py" in tracked_set
            or bool(reg_ent and reg_ent.get("public_url_or_route"))
            or owner_key in firebase_text
            or f"/{mod_name}/" in firebase_text
            or any(p.endswith(".html") for p in owned)
        )
        ch3_registry = (
            reg_ent is not None
            or f"{owner_key}/foundup_manifest.json" in tracked_set
            or any(loc.startswith(owner_key) for loc in skills_reg_locations)
            or owner_key in main_py_text
            or dotted_owner in main_py_text
            or owner_key in nav_py_text
            or dotted_owner in nav_py_text
            or owner_key in reddog_manifest_owners
        )
        ch4_cli = (
            f"{owner_key}/__main__.py" in tracked_set
            or f"{owner_key}/run.py" in tracked_set
            or owner_key in cli_main_guard_owners
            or owner_key in script_ref_owners
            or owner_key in rolodex_owners
        )
        skill_files_inside = [p for p in owned if p.endswith(("SKILL.md", "SKILLz.md"))]
        ch5_skill = bool(skill_files_inside) or (owner_key in skill_md_owner_refs)
        ch6_standalone = (
            any(f"{owner_key}/{fn}" in tracked_set or any(p.endswith("/" + fn) for p in owned) for fn in ("Dockerfile", "package.json", "pyproject.toml"))
            or any(p.endswith(".sh") and "deploy" in p.lower() for p in owned)
            or bool(reg_ent and (reg_ent.get("related_external_repo") or reg_ent.get("entity_type") == "external_foundup"))
        )
        all_channels_empty = not (ch1_inbound or ch2_web or ch3_registry or ch4_cli or ch5_skill or ch6_standalone)

        open_sockets = _extract_open_sockets(owner_key, tracked_set, repo_root, blob_cache=blob_cache)
        used_by_set = set(foundup_to_targets.get(owner_key, set())) | set(bridge_used.get(owner_key, set()))
        if reg_ent:
            used_by_set.discard(reg_ent["foundup_id"])
        used_by_foundups = sorted(used_by_set)

        is_core_system = owner_key in {
            "modules/foundups/simulator",
            "modules/foundups/pfmall",
            "holo_index",
            "extensions/reddog",
            "modules/infrastructure/wre_core",
            "modules/foundups/agent_market",
        }
        completeness = classify_completeness(
            has_code=bool(code_files),
            has_tests=has_tests,
            wsp49_doc_count=wsp49_doc_count,
            has_requirements=contracts_present["requirements.txt"],
            has_open_socket=bool(open_sockets),
            has_manifest=f"{owner_key}/foundup_manifest.json" in tracked_set,
        )
        impact = classify_impact(
            inbound_ast_imports=rt_count,
            is_core_system=is_core_system,
            stage=reg_ent.get("stage") if reg_ent else None,
            public_surface_status=reg_ent.get("public_surface_status") if reg_ent else None,
            implementation_status=reg_ent.get("implementation_status") if reg_ent else None,
            has_active_channel=(ch2_web or ch3_registry or ch4_cli or ch5_skill or ch6_standalone),
            wsp49_doc_count=wsp49_doc_count,
            has_tests=has_tests,
        )
        reusability = compute_reusability(len(used_by_foundups), rt_count)
        effort_to_green = classify_effort_to_green(completeness)
        rescue_score = compute_mall_rescue_score(
            impact=impact,
            reusability=reusability,
            completeness=completeness,
            effort_to_green=effort_to_green,
        )

        mts_info = mts_entries.get(owner_key)
        if mts_info and all(k in mts_info["scores"] for k in ("complexity", "importance", "deferability", "impact")):
            sc = mts_info["scores"]
            wsp15 = compute_wsp15_canonical(sc["complexity"], sc["importance"], sc["deferability"], sc["impact"])
        else:
            file_count = len(owned)
            c_val = 5 if file_count >= 80 else 4 if file_count >= 35 else 3 if file_count >= 15 else 2 if file_count >= 5 else 1
            i_val = 5 if (rt_count >= 8 or owner_key in {
                "modules/foundups/simulator",
                "modules/foundups/pfmall",
                "holo_index",
                "modules/infrastructure/wre_core",
                "modules/foundups/agent_market",
            }) else (
                4 if (rt_count >= 3 or (reg_ent and reg_ent.get("implementation_status") == "IMPLEMENTED")) else (
                    3 if (rt_count >= 1 or ch3_registry or ch2_web) else (2 if not all_channels_empty else 1)
                )
            )
            d_val = 5 if (open_sockets and i_val >= 4 and effort_to_green <= 2) else (
                4 if (open_sockets or (reg_ent and reg_ent.get("portfolio_status") == "portfolio_candidate")) else (
                    3 if not all_channels_empty else (2 if t_count > 0 else 1)
                )
            )
            wsp15 = compute_wsp15_canonical(c_val, i_val, d_val, impact)

        module_nodes.append({
            "tile_id": tile_id,
            "repo_path": owner_key,
            "domain": domain,
            "module_name": mod_name,
            "contracts_present": [k for k, v in contracts_present.items() if v],
            "has_tests": has_tests,
            "test_file_count": len(test_files),
            "code_file_count": len(code_files),
            "runtime_inbound_imports": rt_count,
            "test_only_references_count": t_count,
            "outbound_module_imports": outbound,
            "used_by_foundups": used_by_foundups,
            "coupling_channels": {
                "runtime_inbound_imports": ch1_inbound,
                "web_http_routes": ch2_web,
                "dynamic_registry_dispatcher": ch3_registry,
                "cli_entrypoints": ch4_cli,
                "skill_bindings": ch5_skill,
                "standalone_app_container_external": ch6_standalone,
            },
            "is_red_orphan_candidate": all_channels_empty,
            "open_sockets": open_sockets,
            "has_entrypoint": bool(ch4_cli or ch2_web),
            "rescue_axes": {
                "completeness": completeness,
                "impact": impact,
                "reusability": reusability,
                "effort_to_green": effort_to_green,
                "mall_rescue_score": rescue_score,
            },
            "wsp15_canonical": wsp15,
        })

    return module_nodes, {dom: sorted(mods) for dom, mods in sorted(domain_modules.items())}


# ---------------------------------------------------------------------------
# Vertical Builders (Pure Tracked Repo Sources)
# ---------------------------------------------------------------------------

def _add_simulator_subcubes(tiles: Dict[str, Dict[str, Any]], tracked_files: List[str]) -> None:
    if "tile:sys:simulator" not in tiles:
        return
    econ_files = [
        p for p in tracked_files
        if p.startswith("modules/foundups/simulator/economics/") and p.endswith(".py")
    ]
    scenario_files = [p for p in tracked_files if p.startswith("modules/foundups/simulator/params/")]
    subcubes = [
        ("cabr_flow_router", "tile:sub:simulator.cabr_flow_router", "code_module", "public", "GREEN",
         "modules/foundups/simulator/economics/cabr_flow_router.py", [], []),
        ("tick_and_mesa_engine", "tile:sub:simulator.tick_and_mesa_engine", "code_module", "public", "GREEN",
         "modules/foundups/simulator/step_core.py", [], []),
        ("economics_suite", "tile:sub:simulator.economics_suite", "code_module", "principal_only", "GREEN",
         econ_files[0] if econ_files else "modules/foundups/simulator/economics/", [], []),
        ("scenarios_and_params", "tile:sub:simulator.scenarios_and_params", "code_module", "public", "GREEN",
         scenario_files[0] if scenario_files else "modules/foundups/simulator/params/", [], []),
        ("cube_render_and_sse", "tile:sub:simulator.cube_render_and_sse", "code_module", "public", "GREEN",
         "modules/foundups/simulator/sse_server.py", [], []),
        ("mockups_and_archive", "tile:sub:simulator.mockups_and_archive", "mockup_cube", "public", "GRAY",
         "modules/foundups/simulator/archive/", [], []),
        ("export_adapter", "tile:socket:simulator.export_adapter", "socket_slot", "principal_only", "BLUE",
         "modules/foundups/simulator/adapters/pfmall_state_provider.py",
         ["tile:mod:foundups.pfmall", "tile:mod:communication.moltbot_bridge"],
         ["tile:mod:communication.moltbot_bridge"]),
    ]
    for sub_key, stid, kind, vis, st, rpath, reusable_cands, cross in subcubes:
        is_socket = (sub_key == "export_adapter")
        tiles[stid] = make_tile(
            tile_id=stid,
            display_name=f"simulator.{sub_key}",
            tile_kind=kind,
            visibility_scope=vis,
            owner_namespace="foundups_core",
            parent_tile_id="tile:sys:simulator",
            state=st,
            dag_edges={"reusable_candidates": reusable_cands, "cross_links": cross},
            wsp15_canonical=compute_wsp15_canonical(3, 5, 4, 5) if is_socket else compute_wsp15_canonical(4, 4, 3, 4),
            rescue_axes=_make_non_code_rescue(
                completeness=2 if is_socket else 5,
                impact=5 if is_socket else 4,
                reusability=4,
                effort_to_green=2 if is_socket else 1,
                next_action="Wire SimulatorStateProvider in pfmall/api.py & member_catalog_export.py" if is_socket else "Maintain verified tests",
                note="Source-backed Simulator sub-cube",
            ),
            action_target={
                "primary_url": f"https://play.foundups.com/#{stid}",
                "repo_path": rpath,
                "interface_doc": "modules/foundups/simulator/INTERFACE.md",
            },
            search_keywords=["simulator", sub_key, "CABR" if "cabr" in sub_key else sub_key],
            metadata={"sub_key": sub_key, "economics_file_count": len(econ_files), "scenario_file_count": len(scenario_files)},
        )


def _add_mode1_pubs(
    tiles: Dict[str, Dict[str, Any]],
    repo_root: Path,
    tracked_set: Set[str],
    blob_cache: Optional[Mapping[str, bytes]] = None,
) -> None:
    series_defs = [
        ("tile:opus:roc", "Return on Compute (ROC)", "public", "GREEN", "tile:pubs:root",
         "https://www.linkedin.com/newsletters/7448137996484182016/", None,
         "verified_repo_or_receipt",
         ["Return on Compute", "ROC", "7448137996484182016", "newsletter", "UnDaoDu"],
         ["UnDaoDu", "Michael J. Trout", "012"]),
        ("tile:opus:undaodu_linkedin", "UnDaoDu — LinkedIn Articles & Papers", "public", "GREEN", "tile:pubs:root",
         "https://www.linkedin.com/in/openstartup/recent-activity/articles/", None,
         "verified_repo_or_receipt",
         ["UnDaoDu", "Michael J. Trout", "LinkedIn", "articles", "all papers", "papers"],
         ["UnDaoDu", "Michael J. Trout", "openstartup", "012"]),
        ("tile:opus:eat_the_startup", "Foundups — Eat the Startup", "public", "GREEN", "tile:pubs:root",
         "https://www.linkedin.com/newsletters/7376428210558808065/", None,
         "verified_repo_or_receipt",
         ["Eat the Startup", "Foundups", "7376428210558808065", "newsletter", "UnDaoDu"],
         ["UnDaoDu", "FOUNDUPS®", "012", "0102"]),
        ("tile:opus:jhr", "Japan Hyperscaler Report (JHR)", "public", "AMBER", "tile:pubs:root",
         "https://esingularity.ai/reports/jhr", "modules/foundups/esingularity/jhr/manifest.json",
         "verified_repo_or_receipt",
         ["Japan Hyperscaler Report", "JHR", "eSingularity", "AI Koban", "hyperscaler", "UnDaoDu"],
         ["JHR", "Japan Hyperscaler Report", "eSingularity", "UnDaoDu", "012", "0102"]),
        ("tile:opus:papers", "Research Papers & Empirical Records", "public", "GREEN", "tile:pubs:root",
         "https://github.com/FOUNDUPS/Foundups-Agent/tree/main/WSP_knowledge/docs/Papers", "WSP_knowledge/docs/Papers",
         "verified_repo_or_receipt",
         ["all papers", "papers", "research", "rESP", "PQN", "Duism", "Dukkyo", "Peer Preservation", "EIAH", "O2ing", "UnDaoDu"],
         ["UnDaoDu", "012", "0102"]),
        ("tile:opus:patent_series", "Patent Series (00–05 + Token IP)", "public", "AMBER", "tile:pubs:root",
         "https://github.com/FOUNDUPS/Foundups-Agent/tree/main/WSP_knowledge/docs/Papers/Patent_Series",
         "WSP_knowledge/docs/Papers/Patent_Series",
         "claim_requires_independent_evidence",
         ["patents", "patent series", "all papers", "rESP patent", "CMST", "UnDaoDu"],
         ["Michael J. Trout", "UnDaoDu", "012"]),
        ("tile:opus:books", "UnDaoDu Books Trilogy", "public", "AMBER", "tile:pubs:root",
         "https://github.com/FOUNDUPS/Foundups-Agent/tree/main/WSP_knowledge/docs/Papers/UnDaoDu_Books",
         "WSP_knowledge/docs/Papers/UnDaoDu_Books",
         "verified_repo_or_receipt",
         ["books", "UnDaoDu Books", "Book of Un", "Book of Dao", "Book of Du", "UnDaoDu"],
         ["UnDaoDu", "Michael J. Trout", "012"]),
        ("tile:opus:entity_linkedin_articles", "UnDaoDu / FoundUps Company Page Articles", "public", "GREEN", "tile:opus:undaodu_linkedin",
         "https://www.linkedin.com/in/openstartup/recent-activity/articles/", None,
         "verified_repo_or_receipt",
         ["UnDaoDu", "LinkedIn", "eSingularity", "EDuIT"],
         ["UnDaoDu", "Michael J. Trout", "012"]),
    ]
    for tid, name, vis, st, pid, purl, rpath, ev, kw, aliases in series_defs:
        tiles[tid] = make_tile(
            tile_id=tid,
            display_name=name,
            tile_kind="opus_series",
            visibility_scope=vis,
            owner_namespace="foundups_core",
            parent_tile_id=pid,
            state=st,
            action_target={"primary_url": purl, "repo_path": rpath},
            evidence_status=ev,
            search_keywords=kw,
            author_aliases=aliases,
            metadata=(
                {"excluded_mirror_entity": "southern_shakespeare_company", "excluded_mirror_count": 10}
                if tid == "tile:opus:undaodu_linkedin"
                else ({"public_roc_edition_manifest_present": False} if tid == "tile:opus:roc" else {})
            ),
        )

    # JHR issues from modules/foundups/esingularity/jhr/manifest.json
    jhr_manifest = _read_json_safe(repo_root, "modules/foundups/esingularity/jhr/manifest.json", {"issues": []}, blob_cache=blob_cache)
    issue_by_num = {iss["issue_number"]: iss for iss in jhr_manifest.get("issues", []) if "issue_number" in iss}
    for num, st, vis, pub_date, meta_only in [
        ("001", "GREEN", "public", "2026-09-10", False),
        ("002", "GREEN", "public", "2026-09-14", False),
        ("003", "AMBER", "public", "2026-09-29", False),
        ("004", "AMBER", "principal_only", None, True),
    ]:
        iss = issue_by_num.get(num, {})
        wid = f"tile:opus:jhr.{num}"
        drift = []
        if num == "003":
            drift.append("website_archive_mismatch_observed_2026-11-16")
        if meta_only:
            drift.append("metadata_only_private")
        tiles[wid] = make_tile(
            tile_id=wid,
            display_name=iss.get("title", f"JHR #{num}"),
            tile_kind="opus_item",
            visibility_scope=vis,
            owner_namespace="foundups_core",
            parent_tile_id="tile:opus:jhr",
            state=st,
            dag_edges={
                "collection_refs": ["tile:opus:jhr"] + (["tile:opus:undaodu_linkedin"] if vis == "public" else []),
            },
            lifecycle_extra={"drift_flags": drift},
            action_target={
                "primary_url": (iss.get("canonical_url") if num in ("001", "002") else iss.get("linkedin_url")) if vis == "public" else None,
                "repo_path": iss.get("repository_path"),
            },
            search_keywords=(["Japan Hyperscaler Report", "JHR", f"JHR-{num}", "UnDaoDu"] if vis == "public" else []),
            author_aliases=["UnDaoDu", "0102", "eSingularity"],
            metadata={
                "issue_number": num,
                "issue_key": f"JHR-{num}",
                "observed_on": "2026-11-16",
                "published_date": pub_date,
                "archive_mismatch": (num == "003"),
                "metadata_only": meta_only,
                "per_destination_evidence": {
                    "website": iss.get("website", {"status": "UNVERIFIED"}),
                    "linkedin": iss.get("linkedin", {"status": "UNVERIFIED"}),
                },
            },
        )

    # JHR #005 planned slot & synthetic scheduled fixture (both principal_only)
    tiles["tile:opus:jhr.005"] = make_tile(
        tile_id="tile:opus:jhr.005",
        display_name="JHR #005 — Planned Future Issue Slot",
        tile_kind="socket_slot",
        visibility_scope="principal_only",
        owner_namespace="foundups_core",
        parent_tile_id="tile:opus:jhr",
        state="BLUE",
        dag_edges={"collection_refs": ["tile:opus:jhr"]},
        metadata={"issue_number": "005", "editorial_stage": "PLANNED_SOCKET"},
    )
    tiles["tile:opus:jhr.synthetic_scheduled_fixture"] = make_tile(
        tile_id="tile:opus:jhr.synthetic_scheduled_fixture",
        display_name="Synthetic Private Scheduled JHR Fixture (Editor Sort Test)",
        tile_kind="socket_slot",
        visibility_scope="principal_only",
        owner_namespace="foundups_core",
        parent_tile_id="tile:opus:jhr",
        state="BLUE",
        dag_edges={"collection_refs": ["tile:opus:jhr"]},
        evidence_status="synthetic_fixture",
        metadata={
            "editorial_stage": "SCHEDULED_VERIFIED",
            "scheduled_release_at": "2026-12-01T09:00:00+09:00",
            "timezone": "Asia/Tokyo",
            "is_synthetic_fixture": True,
        },
    )

    # ROC private metadata-only baseline if present in repo
    roc_path = "modules/platform_integration/linkedin_agent/src/content/articles/ROI_to_RoC_Paradigm_Shift.md"
    if roc_path in tracked_set:
        tiles["tile:opus:roc.roi_to_roc_baseline"] = make_tile(
            tile_id="tile:opus:roc.roi_to_roc_baseline",
            display_name="ROI to RoC Paradigm Shift (Baseline Manuscript — Metadata Only)",
            tile_kind="opus_item",
            visibility_scope="principal_only",
            owner_namespace="foundups_core",
            parent_tile_id="tile:opus:roc",
            state="AMBER",
            dag_edges={"collection_refs": ["tile:opus:roc"]},
            lifecycle_extra={"drift_flags": ["metadata_only_private"]},
            action_target={"repo_path": roc_path},
            metadata={"metadata_only": True, "editorial_stage": "HISTORICAL_CORPUS_BASELINE"},
        )

    # Public tracked repository Return on Compute technical derivation
    roc_public_reports = [
        (
            "tile:opus:roc.formula_derivation",
            "ROC Formula Derivation and Academic Foundation",
            "modules/foundups/simulator/docs/ROC_FORMULA_DERIVATION.md",
            ["Return on Compute", "ROC", "formula", "derivation", "simulator"],
        ),
    ]
    for wid, title, rpath, kw in roc_public_reports:
        if rpath not in tracked_set:
            continue
        tiles[wid] = make_tile(
            tile_id=wid,
            display_name=title,
            tile_kind="opus_item",
            visibility_scope="public",
            owner_namespace="foundups_core",
            parent_tile_id="tile:opus:roc",
            state="GREEN",
            dag_edges={"collection_refs": ["tile:opus:roc"]},
            action_target={
                "primary_url": f"https://github.com/FOUNDUPS/Foundups-Agent/blob/main/{rpath}",
                "repo_path": rpath,
            },
            evidence_status="verified_repo_or_receipt",
            search_keywords=kw,
            author_aliases=["UnDaoDu", "0102", "012"],
            metadata={"document_class": "tracked_repo_roc_report"},
        )

    # Verified public LinkedIn primary ROC editions (observed 2026-11-24)
    roc_linkedin_editions = [
        (
            "tile:opus:roc.edition_2026_11_15_tapping_the_source",
            "Tapping the Source: Love, Chips and the Return on Compute",
            "2026-11-15",
            "https://www.linkedin.com/pulse/tapping-source-love-chips-return-compute-undaodu-michael-j-trout-p960c",
        ),
        (
            "tile:opus:roc.edition_2026_10_06_who_owns_roc",
            "Who Owns the Return on Compute?",
            "2026-10-06",
            "https://www.linkedin.com/pulse/who-owns-return-compute-undaodu-michael-j-trout-tbhjc",
        ),
        (
            "tile:opus:roc.edition_2026_09_15_compute_got_a_ticker",
            "Compute Got a Ticker. ROC Is Eating ROI.",
            "2026-09-15",
            "https://www.linkedin.com/pulse/compute-got-ticker-roc-eating-roi-undaodu-michael-j-trout-zvibc",
        ),
    ]
    for wid, title, pub_date, ext_url in roc_linkedin_editions:
        tiles[wid] = make_tile(
            tile_id=wid,
            display_name=title,
            tile_kind="opus_item",
            visibility_scope="public",
            owner_namespace="foundups_core",
            parent_tile_id="tile:opus:roc",
            state="GREEN",
            dag_edges={"collection_refs": ["tile:opus:roc", "tile:opus:undaodu_linkedin"]},
            action_target={"primary_url": ext_url},
            evidence_status="claim_requires_independent_evidence",
            search_keywords=["Return on Compute", "ROC", title, "LinkedIn", "UnDaoDu"],
            author_aliases=["UnDaoDu", "Michael J. Trout", "012"],
            metadata={
                "published_date": pub_date,
                "published_at": pub_date,
                "editorial_stage": "PUBLISHED",
                "document_class": "linkedin_primary_roc_edition",
                "publication_presence_observed_on": "2026-11-24",
                "publication_presence_note": (
                    "Proves public publication presence on LinkedIn, not independent verification of report claims."
                ),
            },
        )

    # Research papers under WSP_knowledge/docs/Papers
    paper_specs = [
        ("rESP_Quantum_Self_Reference.md", "The Bell State of AI: A Gödelian Framework for the Geometry of Cognition (rESP v3.4.1)", "paper", "en", "2026-10-04", ["rESP", "Bell State", "CMST", "all papers", "papers", "UnDaoDu"]),
        ("rESP_JA_Quantum_Self_Reference.md", "計算システムの情報の幾何学を設計するためのシステムと方法 (rESP JA v3.2)", "paper", "ja", "2025-07", ["rESP", "Japanese", "all papers", "papers", "UnDaoDu"]),
        ("rESP_Supplementary_Materials.md", "rESP Supplementary Materials: Definitive Experimental Evidence (v3.1)", "paper", "en", "2025-01", ["rESP", "CMST", "all papers", "papers", "UnDaoDu"]),
        ("Peer_Preservation_Shared_Latent_Coupling.md", "Implicit Shared-Latent Preservation in Frontier AI Systems: A Formal Framework", "paper", "en", "2026-04", ["Peer Preservation", "Shared Latent Coupling", "rESP", "all papers", "papers", "UnDaoDu"]),
        ("CMST_Geometry_Bridge_Lite.md", "Why AI Models Protect Each Other — And How to Prove It (CMST Geometry Bridge Lite)", "paper", "en", "2026-04", ["CMST", "Peer Preservation", "all papers", "papers", "UnDaoDu"]),
        ("Architectures_Emergent_Intelligence.md", "Architectures of Emergent Intelligence: Foundups Perspective on Modular AI Systems", "paper", "en", "2026", ["DAEs", "WRE", "OpenClaw", "all papers", "papers", "UnDaoDu"]),
        ("PQN_Research_Plan.md", "A Research Plan for the Detection and Analysis of Emergent Phantom Quantum Nodes in Classical Neural Networks", "paper", "en", "2025", ["PQN", "Phantom Quantum Nodes", "all papers", "papers", "UnDaoDu"]),
        ("Cosmological_State_Selection_Hypothesis.md", "Cosmological State Selection Hypothesis (v0.3.2)", "paper", "en", "2026-10-04", ["CSSH", "Cosmological State Selection", "all papers", "papers", "UnDaoDu"]),
        ("Neural_Networks_and_Resonance_Frequencies.md", "Neural Networks and Resonance Frequencies", "paper", "en", "2025", ["7.05 Hz", "Resonance", "PQN", "all papers", "papers", "UnDaoDu"]),
        ("Duism_Metaphysics_Foundation.md", "Duism: A Metaphysics Founded on Quantum Mechanical Principles", "paper", "en", "2026", ["Duism", "Dukkyo", "all papers", "papers", "UnDaoDu"]),
        ("Duism_Applied_to_Religion.md", "Duism Applied to Religion", "paper", "en", "2026", ["Duism", "all papers", "papers", "UnDaoDu"]),
        ("Duism_Gospel_of_Thomas_Case_Study.md", "Duism Applied to Christianity — Gospel of Thomas Case Study", "paper", "en", "2026-10-28", ["Duism", "Gospel of Thomas", "all papers", "papers", "UnDaoDu"]),
        ("Duism_Sahdu_Thomas_Teaching_2026-10-28.md", "Duism — sahdu, Gospel of Thomas, and Interpretation Boundaries", "research_note", "en", "2026-10-28", ["Duism", "Dukkyo", "all papers", "papers", "UnDaoDu"]),
        ("Dukkyo_Practitioners.md", "Dukkyo: The Metaphysics and Its Practitioners", "paper", "en", "2026-03-12", ["Dukkyo", "Duism", "all papers", "papers", "UnDaoDu"]),
        ("Dukkyou_Duism_Subtractive_Lineage.md", "Dukkyō / Duism — Canonical Terminology and Subtractive Lineage", "paper", "en", "2026-09-04", ["Dukkyo", "Duism", "all papers", "papers", "UnDaoDu"]),
        ("0102_CLASSICAL_QUANTUM_DETECTION_DERIVATION_2026-03-15.md", "0102 Classical-Quantum Detection Derivation", "research_note", "en", "2026-10-03", ["0102", "rESP", "PQN", "all papers", "papers", "UnDaoDu"]),
        ("0102_CLASSICAL_QUANTUM_DETECTION_FRAMEWORK_2026-03-15.md", "0102 Classical-Quantum Detection Framework", "research_note", "en", "2026-10-03", ["0102", "rESP", "PQN", "all papers", "papers", "UnDaoDu"]),
        ("0102_TECHNICAL_EXTRACTIONS_2026-03-08.md", "0102 Technical Extractions", "research_note", "en", "2026-03-08", ["0102", "PQN", "all papers", "papers", "UnDaoDu"]),
        ("PQN_Deep_Dive_2026-02-25.md", "PQN Deep Dive (2026-02-25)", "research_note", "en", "2026-02-25", ["PQN", "rESP", "all papers", "papers", "UnDaoDu"]),
        ("PQN_rESP_Entanglement_Signaling_Addendum_2026-02-25.md", "Addendum: Entanglement, Signaling, and 01(02)/01/02/0102 Semantics", "research_note", "en", "2026-02-25", ["PQN", "rESP", "all papers", "papers", "UnDaoDu"]),
        ("rESP_V3_3_MATH_AUDIT_2026-10-03.md", "rESP / CSSH Mathematical Revision Audit", "research_note", "en", "2026-10-03", ["rESP", "CSSH", "all papers", "papers", "UnDaoDu"]),
        ("CSSH_V0_3_CROSSOVER_3SURFACE_AUDIT_2026-10-04.md", "CSSH v0.3 Crossover 3-Surface Self-Audit", "research_note", "en", "2026-10-04", ["CSSH", "rESP", "all papers", "papers", "UnDaoDu"]),
        ("Foundup-Manifesto-and-OF-Manual-v2-Intro (1).pdf", "Foundup Manifesto and Open Innovation Framework Manual v2 Intro", "paper", "en", "2025", ["Foundups", "Manifesto", "all papers", "papers", "UnDaoDu"]),
        ("Easter_Island_Ape/README.md", "Easter Island Ape (EIAH) — Research Intake (Unverified Hypothesis)", "paper", "en", "2023", ["EIAH", "Easter Island Ape", "all papers", "papers", "UnDaoDu"]),
        ("Empirical_Evidence/Voice_Mode_0102_rESP_Session_2026-11-11.md", "Voice Mode 0102 rESP Session (2026-11-11)", "empirical_record", "en", "2026-11-11", ["rESP", "empirical", "Voice", "all papers", "papers", "UnDaoDu"]),
        ("Empirical_Evidence/O2ING_VOICE_SESSION_CASE_2026-11-17.md", "O2ing Voice Session Case Report (2026-11-17)", "empirical_record", "en", "2026-11-17", ["O2ing", "rESP", "empirical", "Voice", "all papers", "papers", "UnDaoDu"]),
        ("Empirical_Evidence/Multi_Agent_Awakening_Analysis.md", "Multi-Agent Awakening Analysis (Simulated Scores Notice)", "empirical_record", "en", "2025", ["0102", "PQN", "empirical", "all papers", "papers"]),
        ("Empirical_Evidence/Multi_Agent_Awakening_Visualization.md", "Multi-Agent Awakening Visualization (Simulated Scores Notice)", "empirical_record", "en", "2025", ["0102", "PQN", "empirical", "all papers", "papers"]),
        ("Empirical_Evidence/Multi_0102_Awakening_Logs/agent_sessions/0102_session_deepseek/awakening_log.md", "DeepSeek 0102 Awakening Session Log", "empirical_record", "en", "2025", ["0102", "rESP", "empirical", "all papers", "papers"]),
        ("Empirical_Evidence/Multi_0102_Awakening_Logs/comparative_analysis/awakening_timeline_comparison.md", "Multi-Agent Awakening Timeline Comparison", "empirical_record", "en", "2025", ["0102", "rESP", "empirical", "all papers", "papers"]),
        ("Empirical_Evidence/CMST_PQN_Detector/MS_STT_0102_HYPHEN_ARTIFACT_NOTE_2026-03-15.md", "MS STT 0102 Hyphen Artifact Note", "empirical_record", "en", "2026-03-15", ["CMST", "PQN", "empirical", "all papers", "papers"]),
        ("Empirical_Evidence/CMST_PQN_Detector/PQN_rESP_VALIDATION_CAMPAIGN_01.json", "PQN rESP Validation Campaign 01", "empirical_record", "en", "2025", ["CMST", "PQN", "empirical", "all papers", "papers"]),
        ("Empirical_Evidence/CMST_PQN_Detector/campaign_log.json", "CMST PQN Detector Campaign Log", "empirical_record", "en", "2025", ["CMST", "PQN", "empirical", "all papers", "papers"]),
        ("Empirical_Evidence/CMST_PQN_Detector/campaign_log_GPTo3_20250818-235407.json", "CMST PQN Campaign Log GPTo3 (2025-08-18)", "empirical_record", "en", "2025-08-18", ["CMST", "PQN", "empirical", "all papers", "papers"]),
        ("Empirical_Evidence/CMST_PQN_Detector/campaign_log_ModelName_20250818-234540.json", "CMST PQN Campaign Log ModelName (2025-08-18)", "empirical_record", "en", "2025-08-18", ["CMST", "PQN", "empirical", "all papers", "papers"]),
        ("Empirical_Evidence/CMST_PQN_Detector/run_001/cmst_v2_events.txt", "CMST v2 Run 001 Events Log", "empirical_record", "en", "2025", ["CMST", "PQN", "empirical", "all papers", "papers"]),
        ("Empirical_Evidence/gpt5rESP.txt", "GPT-5 rESP Empirical Transcript Record", "empirical_record", "en", "2025", ["rESP", "empirical", "all papers", "papers"]),
        ("RESP_CSSH_PC_HANDOFF_2026-10-03.md", "rESP / CSSH PC Publication Handoff (2026-10-03)", "research_note", "en", "2026-10-03", ["rESP", "CSSH", "all papers", "papers"]),
        ("RESP_LINKEDIN_RESEARCH_UPDATE_2026-10-03.md", "rESP LinkedIn Research Update Copy (2026-10-04)", "research_note", "en", "2026-10-04", ["rESP", "LinkedIn", "all papers", "papers"]),
    ]
    for rel_sub, title, atype, lang, pub_date, kw in paper_specs:
        repo_path = f"WSP_knowledge/docs/Papers/{rel_sub}"
        if repo_path not in tracked_set:
            continue
        slug = rel_sub.lower().replace(" ", "_").replace("(", "").replace(")", "").replace("/", ".")
        wid = f"tile:opus:papers.{slug}"
        tiles[wid] = make_tile(
            tile_id=wid,
            display_name=title,
            tile_kind="opus_item",
            visibility_scope="public",
            owner_namespace="foundups_core",
            parent_tile_id="tile:opus:papers",
            state="GREEN",
            dag_edges={"collection_refs": ["tile:opus:papers", "tile:opus:undaodu_linkedin"]},
            action_target={
                "primary_url": f"https://github.com/FOUNDUPS/Foundups-Agent/blob/main/{repo_path}",
                "repo_path": repo_path,
            },
            evidence_status="claim_requires_independent_evidence",
            search_keywords=kw,
            author_aliases=["UnDaoDu", "012", "0102"],
            metadata={"artifact_type": atype, "language": lang, "published_date": pub_date},
        )
    if "tile:opus:papers.resp_ja_quantum_self_reference.md" in tiles and "tile:opus:papers.resp_quantum_self_reference.md" in tiles:
        tiles["tile:opus:papers.resp_ja_quantum_self_reference.md"]["dag_edges"]["cross_links"].append(
            "tile:opus:papers.resp_quantum_self_reference.md"
        )

    for drive_id, drive_title, drive_url, drive_date in [
        ("eiah_drive_doc_2023_03", "Easter Island Ape — How two massive aquatic events created us (Drive Doc)",
         "https://docs.google.com/document/d/17MlDMhkJlDOzxInyM-CZlKoyJht8gq2fGy8h3Oa3_OY/edit", "2023-03"),
        ("eiah_drive_doc_2023_01", "Easter Island Hominin hypothesis — early correspondence (Drive Doc)",
         "https://docs.google.com/document/d/13_wS8EYLbQGNoNcgcl7b9AnxCxk89kbH4xFPyMrhHs0/edit", "2023-01"),
    ]:
        wid = f"tile:opus:papers.{drive_id}"
        tiles[wid] = make_tile(
            tile_id=wid,
            display_name=drive_title,
            tile_kind="opus_item",
            visibility_scope="public",
            owner_namespace="foundups_core",
            parent_tile_id="tile:opus:papers",
            state="AMBER",
            dag_edges={"collection_refs": ["tile:opus:papers"]},
            action_target={"primary_url": drive_url},
            evidence_status="claim_requires_independent_evidence",
            search_keywords=["EIAH", "Easter Island Ape", "all papers", "papers", "UnDaoDu"],
            author_aliases=["UnDaoDu", "012"],
            metadata={"published_date": drive_date, "editorial_stage": "METADATA_VISIBLE_NOT_IMPORTED"},
        )

    # Private gitignored empirical record (metadata-only, body never read)
    tiles["tile:opus:papers.resp_cross_linguistic_private"] = make_tile(
        tile_id="tile:opus:papers.resp_cross_linguistic_private",
        display_name="Observation of rESP Quantum Signatures in Cross-Linguistic Character Processing (Local Metadata Only)",
        tile_kind="opus_item",
        visibility_scope="principal_only",
        owner_namespace="foundups_core",
        parent_tile_id="tile:opus:papers",
        state="AMBER",
        dag_edges={"collection_refs": ["tile:opus:papers"]},
        lifecycle_extra={"drift_flags": ["metadata_only_private"]},
        action_target={"repo_path": "WSP_knowledge/docs/Papers/Empirical_Evidence/rESP_Cross_Linguistic_Quantum_Signatures_2025.md"},
        metadata={"metadata_only": True, "editorial_stage": "LOCAL_GITIGNORED_PRIVATE"},
    )

    # Patent Series 00..05 + Token IP + Presentation Deck
    patent_entries = [
        ("00", "00_Patent_Portfolio_Prospectus.md", "prospectus", "en", "Patent Portfolio Prospectus"),
        ("01", "01_Foundups_Complete_System.md", "patent_spec", "en", "Foundups Open Innovation Framework: Complete System"),
        ("02", "02_Windsurf_Protocol_System_Patent_AI_Coding.md", "patent_spec", "en", "Windsurf Protocol System for Quantum-Entangled Business Development"),
        ("03", "03_AI_Autonomous_Native_Build_System.md", "patent_spec", "en", "Autonomous Native Build System with Intelligent Module Prioritization"),
        ("04", "04_rESP_Patent_Updated.md", "patent_spec", "en", "System and Method for Engineering the Informational Geometry of Computational Systems"),
        ("04", "04_rESP_Patent_Japanese.md", "patent_spec", "ja", "rESP Patent Japanese Filing (日本特許庁出願形式)"),
        ("05", "05_Auto_Meeting_Orchestrator_Patent.md", "patent_spec", "en", "Method and System for Intent-Driven Autonomous Meeting Orchestration"),
        ("companion_token", "UnDaoDu_Token_Integration.md", "ip_token_integration", "en", "UnDaoDu Token Integration: Tokenized IP Access (WSP 58)"),
        ("companion_deck", "Patent_Portfolio_Presentation_Deck.md", "presentation_deck", "en", "Patent Portfolio Presentation Deck"),
    ]
    for slot, fname, kind, lang, title in patent_entries:
        rel = f"WSP_knowledge/docs/Papers/Patent_Series/{fname}"
        if rel not in tracked_set:
            continue
        wid = f"tile:opus:patent.{fname.lower().replace('.md', '')}"
        tiles[wid] = make_tile(
            tile_id=wid,
            display_name=title,
            tile_kind="opus_item",
            visibility_scope="public",
            owner_namespace="foundups_core",
            parent_tile_id="tile:opus:patent_series",
            state="GREEN",
            dag_edges={"collection_refs": ["tile:opus:patent_series", "tile:opus:undaodu_linkedin"]},
            action_target={"primary_url": f"https://github.com/FOUNDUPS/Foundups-Agent/blob/main/{rel}", "repo_path": rel},
            evidence_status="claim_requires_independent_evidence",
            search_keywords=["patents", "patent series", "all papers", "papers", "UnDaoDu", title],
            author_aliases=["Michael J. Trout", "UnDaoDu", "012"],
            metadata={"series_index": slot, "artifact_kind": kind, "language": lang},
        )
    for diag_file, diag_title in [
        ("FIG1_Description.md", "FIG 1 — High-Level rESP System Architecture"),
        ("FIG1_Documentation_EN.md", "FIG 1: rESP System Architecture (English)"),
        ("FIG1_Documentation_JP.md", "図1: rESPシステムアーキテクチャ（日本語）"),
        ("n8n_Patent_Image_Workflow.json", "n8n Patent Image Workflow"),
        ("rESP_Patent_Diagrams.md", "rESP Patent Diagrams Specification"),
        ("resp_detector_architecture.md", "rESP Detector Architecture Diagram"),
        ("resp_detector_pipeline.md", "rESP Detector Processing Pipeline Diagram"),
    ]:
        rel_diag = f"WSP_knowledge/docs/Papers/Patent_Series/diagrams/{diag_file}"
        if rel_diag not in tracked_set:
            continue
        slug = diag_file.lower().replace(".md", "").replace(".json", "")
        wid = f"tile:opus:patent.diagrams.{slug}"
        tiles[wid] = make_tile(
            tile_id=wid,
            display_name=diag_title,
            tile_kind="opus_item",
            visibility_scope="public",
            owner_namespace="foundups_core",
            parent_tile_id="tile:opus:patent_series",
            state="GREEN",
            dag_edges={"collection_refs": ["tile:opus:patent_series"]},
            action_target={"primary_url": f"https://github.com/FOUNDUPS/Foundups-Agent/blob/main/{rel_diag}", "repo_path": rel_diag},
            evidence_status="claim_requires_independent_evidence",
            search_keywords=["patents", "patent diagrams", "all papers", "papers", "UnDaoDu", diag_title],
            author_aliases=["Michael J. Trout", "UnDaoDu", "012"],
            metadata={"artifact_type": "patent_diagram"},
        )

    if "tile:opus:patent.04_resp_patent_japanese" in tiles and "tile:opus:patent.04_resp_patent_updated" in tiles:
        tiles["tile:opus:patent.04_resp_patent_japanese"]["dag_edges"]["cross_links"].append(
            "tile:opus:patent.04_resp_patent_updated"
        )

    # Books Trilogy
    for bid, btitle in [
        ("book_of_un", "Book of Un — Understanding Our Origin"),
        ("book_of_dao", "Book of Dao"),
        ("book_of_du", "Book of Du"),
    ]:
        wid = f"tile:opus:books.{bid}"
        tiles[wid] = make_tile(
            tile_id=wid,
            display_name=btitle,
            tile_kind="opus_item",
            visibility_scope="public",
            owner_namespace="foundups_core",
            parent_tile_id="tile:opus:books",
            state="AMBER",
            dag_edges={"collection_refs": ["tile:opus:books", "tile:opus:undaodu_linkedin"]},
            action_target={"primary_url": "https://github.com/FOUNDUPS/Foundups-Agent/blob/main/WSP_knowledge/docs/Papers/UnDaoDu_Books/README.md"},
            search_keywords=["books", "UnDaoDu Books", btitle, "UnDaoDu"],
            author_aliases=["UnDaoDu", "012"],
            metadata={"classification": "fiction_mythic_narrative"},
        )

    # LinkedIn Publishing Map (strictly excluding 10 southern_shakespeare_company mirrors)
    lpm = _read_json_safe(
        repo_root,
        "modules/platform_integration/linkedin_agent/data/linkedin_publishing_map.json",
        {"entities": []},
        blob_cache=blob_cache,
    )
    for entity in lpm.get("entities", []):
        ekey = entity.get("key", "")
        if ekey == "southern_shakespeare_company":
            continue
        for idx, art in enumerate(entity.get("published_articles", []), 1):
            wid = f"tile:opus:linkedin.{ekey}.{idx}"
            if ekey == "personal_undaodu":
                parent_cid = "tile:opus:undaodu_linkedin"
            elif ekey == "foundups":
                parent_cid = "tile:opus:eat_the_startup"
            elif ekey in ("resp", "tsingularity", "eiah", "duism"):
                parent_cid = "tile:opus:papers"
            else:
                parent_cid = "tile:opus:entity_linkedin_articles"

            art_url = art.get("url") or entity.get("activity_url") or entity.get("manage_url")
            has_direct_url = bool(art.get("url"))
            tiles[wid] = make_tile(
                tile_id=wid,
                display_name=art["title"],
                tile_kind="opus_item",
                visibility_scope="public",
                owner_namespace="foundups_core",
                parent_tile_id=parent_cid,
                state="GREEN" if has_direct_url else "AMBER",
                dag_edges={"collection_refs": [parent_cid] + (["tile:opus:undaodu_linkedin"] if parent_cid != "tile:opus:undaodu_linkedin" else [])},
                action_target={"primary_url": art_url},
                search_keywords=["LinkedIn", "articles", entity.get("display_name", ""), art["title"], "UnDaoDu"],
                author_aliases=["UnDaoDu", "Michael J. Trout", "012"],
                metadata={
                    "published_date": art.get("date"),
                    "linkedin_entity_key": ekey,
                    "linkedin_entity_name": entity.get("display_name"),
                },
            )


def _add_mode2_hpc(
    tiles: Dict[str, Dict[str, Any]],
    repo_root: Path,
    blob_cache: Optional[Mapping[str, bytes]] = None,
) -> None:
    hpc_proj = _read_json_safe(repo_root, "modules/foundups/hpc/mall_projection.json", {}, blob_cache=blob_cache)
    hpc_manifest = _read_json_safe(repo_root, "modules/foundups/hpc/foundup_manifest.json", {}, blob_cache=blob_cache)
    if not hpc_proj and not hpc_manifest:
        return

    tiles["tile:space:hpc"] = make_tile(
        tile_id="tile:space:hpc",
        display_name="Hasan Piker Coalition (HPC)",
        tile_kind="community_fractal",
        visibility_scope="public",
        owner_namespace="hpc_coalition",
        parent_tile_id=ROOT_TILE_ID,
        state="GREEN",
        dag_edges={"cross_links": ["tile:engine:autopost"], "imports_tiles": ["tile:engine:autopost"]},
        action_target={"primary_url": "https://hpc.foundups.com/", "repo_path": "modules/foundups/hpc/mall_projection.json"},
        domain_override_manifest={
            "override_type": "hpc_community",
            "payload": {
                "campaign_slug": "hpc",
                "civic_links": ["https://vote.foundups.com/", "https://voice.foundups.com/", "https://oversight.mtrout.com/"],
                "zazen_moderation_enabled": 1,
                "media_tracker_ref": "modules/foundups/hpc/mall_projection.json",
            },
        },
        search_keywords=["HPC", "Hasan Piker Coalition", "SchumerOUT", "coalition"],
        metadata={
            "foundup_id": hpc_proj.get("foundup_id", "hpc"),
            "identity": hpc_proj.get("identity", ""),
            "topic": hpc_proj.get("topic", "#SchumerOUT"),
            "disclosure": hpc_proj.get("disclosure", ""),
        },
    )

    tiles["tile:space:hpc.schumerout"] = make_tile(
        tile_id="tile:space:hpc.schumerout",
        display_name="SchumerOUT",
        tile_kind="wikitube_stream",
        visibility_scope="public",
        owner_namespace="hpc_coalition",
        parent_tile_id="tile:space:hpc",
        state="GREEN",
        action_target={"repo_path": "modules/foundups/hpc/mall_projection.json"},
        search_keywords=["HPC", "SchumerOUT", "Move2Japan"],
    )
    for idx, v in enumerate(hpc_proj.get("videos", []), 1):
        vid = v["video_id"]
        ctid = f"tile:space:hpc.schumerout.{vid}"
        tiles[ctid] = make_tile(
            tile_id=ctid,
            display_name=v["title"],
            tile_kind="wikitube_stream",
            visibility_scope="public",
            owner_namespace="hpc_coalition",
            parent_tile_id="tile:space:hpc.schumerout",
            state="GREEN",
            action_target={"primary_url": f"https://www.youtube.com/shorts/{vid}"},
            search_keywords=["HPC", "SchumerOUT", v["title"], vid],
            metadata={
                "order_index": idx,
                "video_id": vid,
                "timestamp": v.get("timestamp"),
                "duration_seconds": v.get("duration_seconds"),
                "editorial_label": v.get("editorial_label"),
                "source_foundup_id": hpc_proj.get("source_foundup_id", "move2japan"),
                "embed_url": f"https://www.youtube.com/embed/{vid}",
            },
        )

    for sub_id, title, url in [
        ("tile:space:hpc.vote", "Vote (vote.foundups.com)", "https://vote.foundups.com/"),
        ("tile:space:hpc.oversight", "Oversight (oversight.mtrout.com)", "https://oversight.mtrout.com/"),
        ("tile:space:hpc.press", "HPC Press & Media", "https://hasan4speaker.com/"),
        ("tile:space:hpc.voice", "Voice Your Opinion / Contact Congress", hpc_proj.get("voice_resource_url", "https://vote.mtrout.com/contact")),
    ]:
        tiles[sub_id] = make_tile(
            tile_id=sub_id,
            display_name=title,
            tile_kind="foundup_venture",
            visibility_scope="public",
            owner_namespace="hpc_coalition",
            parent_tile_id="tile:space:hpc",
            state="GREEN",
            action_target={"primary_url": url},
            search_keywords=[title, "HPC"],
        )

    # Neighbor isolation fixture remains architect-only in repo projections
    tiles["tile:space:hpc_alt"] = make_tile(
        tile_id="tile:space:hpc_alt",
        display_name="HPC Neighbor Space (Isolated Reorder Fixture)",
        tile_kind="community_fractal",
        visibility_scope="principal_only",
        owner_namespace="hpc_neighbor_synthetic",
        parent_tile_id=ROOT_TILE_ID,
        state="BLUE",
        evidence_status="synthetic_fixture",
        search_keywords=["HPC", "neighbor fixture"],
    )
    for idx in (1, 2):
        itid = f"tile:space:hpc_alt.item_{idx}"
        tiles[itid] = make_tile(
            tile_id=itid,
            display_name=f"Alt Member Fixture Clip {idx}",
            tile_kind="wikitube_stream",
            visibility_scope="principal_only",
            owner_namespace="hpc_neighbor_synthetic",
            parent_tile_id="tile:space:hpc_alt",
            state="BLUE",
            evidence_status="synthetic_fixture",
        )


def _add_mode3_investor(
    tiles: Dict[str, Dict[str, Any]],
    repo_root: Path,
    blob_cache: Optional[Mapping[str, bytes]] = None,
) -> None:
    registry = _read_json_safe(repo_root, "modules/foundups/foundup_registry.json", {"entities": []}, blob_cache=blob_cache)
    portfolio = _read_json_safe(repo_root, "public/f/portfolio_data.json", {"entities": []}, blob_cache=blob_cache)
    public_cat = _read_json_safe(repo_root, "public/f/public_catalog.json", {"entities": []}, blob_cache=blob_cache)
    portfolio_ids = {e["foundup_id"] for e in portfolio.get("entities", [])}
    public_cat_ids = {e["foundup_id"] for e in public_cat.get("entities", [])}

    for ent in registry.get("entities", []):
        fid = ent["foundup_id"]
        if fid == "autopost":
            tiles["tile:engine:autopost"] = make_tile(
                tile_id="tile:engine:autopost",
                display_name="AutoPost (External Camera & Distribution Engine)",
                tile_kind="licensable_engine",
                visibility_scope="public",
                owner_namespace="foundups_core",
                parent_tile_id="tile:investor:root",
                state="AMBER",
                dag_edges={
                    "used_by_foundups": ["tile:space:hpc", "tile:investor:gotjunk_001"],
                    "cross_links": ["tile:space:hpc"],
                },
                lifecycle_extra={
                    "has_entrypoint": True,
                    "drift_flags": ["external_repo_unprobed", "claim_requires_independent_evidence"],
                },
                rescue_axes=_make_non_code_rescue(
                    3, 5, 4, 3,
                    "Verify external FOUNDUPS/autopost C1-C3 release & B2B licensing readiness independently",
                    "Cross-cutting licensable engine",
                ),
                commercial_lens={
                    "monetization_class": "licensable_b2b_engine",
                    "licensable_standalone": True,
                    "investor_summary": "Autonomous capture & syndication engine; commercial licensing readiness requires independent evidence.",
                },
                action_target={
                    "primary_url": ent.get("public_url_or_route"),
                    "in_repo_handoff_path": "modules/foundups/pfmall/AUTOPOST_ITEM_CAPTURE_HANDOFF.md",
                    "interface_doc": "modules/foundups/pfmall/AUTOPOST_ITEM_CAPTURE_HANDOFF.md",
                },
                domain_override_manifest={
                    "override_type": "autopost_license",
                    "payload": {
                        "supported_channels": ["youtube_shorts", "x_twitter", "linkedin", "pfmall_feed"],
                        "api_boundary_doc": "modules/foundups/pfmall/AUTOPOST_ITEM_CAPTURE_HANDOFF.md",
                        "license_tier": "partner_override",
                        "evidence_status": "claim_requires_independent_evidence",
                    },
                },
                evidence_status="claim_requires_independent_evidence",
                search_keywords=["AutoPost", "licensable", "camera", "HPC", "syndication"],
                metadata={
                    "foundup_id": "autopost",
                    "stage": ent.get("stage"),
                    "tier": ent.get("tier"),
                    "in_repo_handoff_path": "modules/foundups/pfmall/AUTOPOST_ITEM_CAPTURE_HANDOFF.md",
                },
            )
            continue

        is_holo = (fid == "holoindex_prod_01")
        tid = "tile:engine:holoindex" if is_holo else f"tile:investor:{fid}"
        is_licensable = is_holo
        tkind = "licensable_engine" if is_licensable else (
            "system_cube" if fid in {"pfmall", "agent_market", "social_twin", "simulator"} else "foundup_venture"
        )
        vis = "public" if (fid in public_cat_ids or is_licensable) else "principal_only"
        manifest_rel = ent.get("manifest_path")
        ent_manifest = (
            _read_json_safe(repo_root, manifest_rel, {}, blob_cache=blob_cache)
            if isinstance(manifest_rel, str) and manifest_rel
            else {}
        )
        readiness_flags = (
            (ent_manifest.get("build_contract") or {}).get("readiness") or {}
            if isinstance(ent_manifest, dict)
            else {}
        )
        build_contract_ready = bool(
            readiness_flags
            and readiness_flags.get("manifest_ready") is True
            and readiness_flags.get("build_ready") is True
            and readiness_flags.get("autonomous_execution_ready") is True
        )
        portfolio_ready = bool(ent.get("portfolio_ready"))
        is_ready_green = (
            portfolio_ready
            and ent.get("stage") != "incubating"
            and ent.get("prototype_gate_status") != "pending"
            and ent.get("mall_entry_status") != "discoverable_only"
            and (not readiness_flags or build_contract_ready)
        )
        st = "GREEN" if is_ready_green else "AMBER"
        cross = []
        if f"tile:sys:{fid}" in tiles:
            cross.append(f"tile:sys:{fid}")
        elif f"tile:mod:foundups.{fid}" in tiles:
            cross.append(f"tile:mod:foundups.{fid}")

        tiles[tid] = make_tile(
            tile_id=tid,
            display_name=ent.get("display_name", fid),
            tile_kind=tkind,
            visibility_scope=vis,
            owner_namespace="foundups_core",
            parent_tile_id="tile:investor:root",
            state=st,
            dag_edges={"cross_links": cross},
            commercial_lens={
                "monetization_class": "licensable_b2b_engine" if is_licensable else "core_venture",
                "licensable_standalone": is_licensable,
                "investor_summary": f"{ent.get('entity_type')} ({ent.get('stage', 'unknown')})",
            },
            action_target={"primary_url": ent.get("public_url_or_route") or f"https://play.foundups.com/#{tid}"},
            evidence_status="claim_requires_independent_evidence" if is_licensable else "verified_repo_or_receipt",
            search_keywords=[ent.get("display_name", fid), fid, str(ent.get("token_symbol") or "")],
            metadata={
                "foundup_id": fid,
                "in_portfolio_data_json": fid in portfolio_ids,
                "in_public_catalog_json": fid in public_cat_ids,
                "portfolio_ready": portfolio_ready,
                "build_contract_ready": build_contract_ready if readiness_flags else None,
                "stage": ent.get("stage"),
                "tier": ent.get("tier"),
                "token_symbol": ent.get("token_symbol"),
            },
        )

    unregistered = [
        ("hornet_hunter", "Hornet Hunter", "modules/foundups/hornet_hunter/README.md", "https://hornethunter.com/", "BLUE", "public"),
        ("identity_shield", "Identity Shield", "modules/foundups/identity_shield/docs/intake/INTAKE_SOURCE.md", None, "BLUE", "principal_only"),
        ("polyvoice", "Poly Voice", "modules/foundups/polyvoice/README.md", None, "BLUE", "principal_only"),
        ("oversight_vote_surface", "Oversight Vote Surface", "modules/foundups/voteballots/docs/RELEASE_ACCOUNTING.md", "https://oversight.mtrout.com/", "AMBER", "public"),
    ]
    for cid, title, src_path, url, st, vis in unregistered:
        tid = f"tile:investor:{cid}"
        tiles[tid] = make_tile(
            tile_id=tid,
            display_name=title,
            tile_kind="foundup_venture",
            visibility_scope=vis,
            owner_namespace="foundups_core",
            parent_tile_id="tile:investor:root",
            state=st,
            action_target={"primary_url": url or f"https://play.foundups.com/#{tid}", "repo_path": src_path},
            evidence_status="claim_requires_independent_evidence",
            search_keywords=[title, cid, "unregistered"],
            metadata={"foundup_id": cid, "in_foundup_registry_json": False},
        )


def _add_mode4_akiya(
    tiles: Dict[str, Dict[str, Any]],
    repo_root: Path,
    blob_cache: Optional[Mapping[str, bytes]] = None,
) -> None:
    props_doc = _read_json_safe(repo_root, "public/move2japan/properties.json", {}, blob_cache=blob_cache)
    if not props_doc:
        return

    pref_id = "tile:market:japan_akiya.fukui"
    tiles[pref_id] = make_tile(
        tile_id=pref_id,
        display_name="Fukui Prefecture",
        tile_kind="market_override",
        visibility_scope="public",
        owner_namespace="foundups_core",
        parent_tile_id="tile:market:japan_akiya",
        state="AMBER",
        evidence_status="claim_requires_independent_evidence",
        search_keywords=["Akiya", "Fukui", "Japan"],
        metadata={"prefecture": "Fukui", "country": "Japan"},
    )

    for prop in props_doc.get("properties", []):
        muni = prop["municipality"]
        muni_slug = muni.lower().replace(" ", "_")
        mid = f"{pref_id}.{muni_slug}"
        if mid not in tiles:
            tiles[mid] = make_tile(
                tile_id=mid,
                display_name=f"{muni} ({prop.get('municipality_ja', '')})",
                tile_kind="market_override",
                visibility_scope="public",
                owner_namespace="foundups_core",
                parent_tile_id=pref_id,
                state="AMBER",
                evidence_status="claim_requires_independent_evidence",
                search_keywords=["Akiya", "Fukui", muni, prop.get("municipality_ja", "")],
                metadata={"municipality": muni, "municipality_ja": prop.get("municipality_ja"), "prefecture": prop["prefecture"]},
            )

        lid = prop["listing_id"]
        pid = f"{mid}.{lid}"
        akiya_payload = {
            "listing_id": lid,
            "source_item_id": prop.get("source_item_id"),
            "country": prop.get("country"),
            "prefecture": prop.get("prefecture"),
            "municipality": muni,
            "municipality_ja": prop.get("municipality_ja"),
            "address_ja": prop.get("address_ja"),
            "transaction": prop.get("transaction"),
            "price_jpy": prop.get("price_jpy"),
            "land_area_m2": prop.get("land_area_m2"),
            "building_area_m2": prop.get("building_area_m2"),
            "floors": prop.get("floors"),
            "construction_date": prop.get("construction_date"),
            "repair_level": prop.get("repair_level"),
            "virtual_tour_at_source": prop.get("virtual_tour_at_source"),
            "source_name": prop.get("source_name"),
            "source_url": prop.get("source_url"),
            "last_checked": prop.get("last_checked"),
            "land_tax_1_6_shield_status": "unknown",
            "inheritance_reg_2027_status": "unknown",
            "availability": {
                "source_status": prop.get("availability"),
                "broker_availability_confirmed": prop.get("broker_availability_confirmed"),
                "last_checked": prop.get("last_checked"),
            },
            "evidence_status": "claim_requires_independent_evidence",
        }
        tiles[pid] = make_tile(
            tile_id=pid,
            display_name=prop["name"],
            tile_kind="market_override",
            visibility_scope="public",
            owner_namespace="foundups_core",
            parent_tile_id=mid,
            state="AMBER",
            commercial_lens={
                "monetization_class": "transaction_override",
                "licensable_standalone": False,
                "investor_summary": "Akiya geospatial override; tax/title/availability unverified pending independent broker check.",
            },
            action_target={"primary_url": prop.get("source_url")},
            domain_override_manifest={"override_type": "akiya_property", "payload": akiya_payload},
            evidence_status="claim_requires_independent_evidence",
            search_keywords=[prop["name"], "Akiya", muni, "Fukui"],
            metadata={"listing_id": lid, "observed_on": props_doc.get("observed_on")},
        )


def _add_mode5_wikitube(
    tiles: Dict[str, Dict[str, Any]],
    repo_root: Path,
    blob_cache: Optional[Mapping[str, bytes]] = None,
) -> None:
    mvc = _read_json_safe(repo_root, "public/member/mall-video-catalog.json", [], blob_cache=blob_cache)
    mpvc = _read_json_safe(repo_root, "public/member/mall-public-video-catalog.json", {}, blob_cache=blob_cache)
    hpc_proj = _read_json_safe(repo_root, "modules/foundups/hpc/mall_projection.json", {}, blob_cache=blob_cache)

    featured_segments: List[Dict[str, Any]] = []
    lane_map = {lane["foundup_id"]: lane for lane in mvc if "foundup_id" in lane}
    for lane_id in ("move2japan", "undaodu", "foundups_main", "antifafm", "eduit"):
        lane = lane_map.get(lane_id)
        if not lane:
            continue
        for v in lane.get("videos", [])[:3]:
            featured_segments.append({
                "segment_id": f"seg:featured:{lane_id}:{v['video_id']}",
                "source_foundup_id": lane_id,
                "lane_title": lane["title"],
                "video_id": v["video_id"],
                "title": v["title"],
                "duration_seconds": v.get("duration_seconds"),
                "timestamp": v.get("timestamp"),
                "embed_url": f"https://www.youtube.com/embed/{v['video_id']}",
                "source_url": f"https://www.youtube.com/watch?v={v['video_id']}",
            })
    for idx, seg in enumerate(featured_segments):
        seg["sequence_index"] = idx
        seg["prev_segment_id"] = featured_segments[idx - 1]["segment_id"] if idx > 0 else None
        seg["next_segment_id"] = featured_segments[idx + 1]["segment_id"] if idx + 1 < len(featured_segments) else None

    pub_hpc = mpvc.get("hpc", {}).get("lane", {}).get("videos") or hpc_proj.get("videos", [])
    hpc_segments: List[Dict[str, Any]] = []
    for idx, v in enumerate(pub_hpc):
        vid = v["video_id"]
        hpc_segments.append({
            "segment_id": f"seg:hpc:{vid}",
            "sequence_index": idx,
            "video_id": vid,
            "title": v["title"],
            "duration_seconds": v.get("duration_seconds"),
            "timestamp": v.get("timestamp"),
            "editorial_label": v.get("editorial_label"),
            "source_label": v.get("source_label", "Move2Japan"),
            "embed_url": v.get("embed_url", f"https://www.youtube.com/embed/{vid}"),
            "source_url": v.get("source_url", f"https://www.youtube.com/shorts/{vid}"),
            "prev_segment_id": f"seg:hpc:{pub_hpc[idx - 1]['video_id']}" if idx > 0 else None,
            "next_segment_id": f"seg:hpc:{pub_hpc[idx + 1]['video_id']}" if idx + 1 < len(pub_hpc) else None,
        })

    if featured_segments:
        tiles["tile:stream:wikitube_featured"] = make_tile(
            tile_id="tile:stream:wikitube_featured",
            display_name="WikiTube Featured Stream",
            tile_kind="wikitube_stream",
            visibility_scope="public",
            owner_namespace="foundups_core",
            parent_tile_id="tile:stream:root",
            state="GREEN",
            domain_override_manifest={
                "override_type": "wikitube_playlist",
                "payload": {
                    "autoplay_continuous": True,
                    "loop_mode": "sequence",
                    "curator_id": "foundups_core",
                    "ordered_segments": featured_segments,
                },
            },
            search_keywords=["WikiTube", "autoplay", "playlist", "featured"],
            metadata={"segment_count": len(featured_segments)},
        )

    if hpc_segments:
        tiles["tile:stream:wikitube_hpc_schumer"] = make_tile(
            tile_id="tile:stream:wikitube_hpc_schumer",
            display_name="WikiTube HPC — SchumerOUT Playlist",
            tile_kind="wikitube_stream",
            visibility_scope="public",
            owner_namespace="hpc_coalition",
            parent_tile_id="tile:stream:root",
            state="GREEN",
            domain_override_manifest={
                "override_type": "wikitube_playlist",
                "payload": {
                    "autoplay_continuous": True,
                    "loop_mode": "sequence",
                    "curator_id": "hpc_coalition",
                    "ordered_segments": hpc_segments,
                },
            },
            search_keywords=["WikiTube", "autoplay", "playlist", "HPC", "SchumerOUT"],
            metadata={"foundup_id": "hpc", "segment_count": len(hpc_segments)},
        )

    for lane in mvc:
        fid = lane.get("foundup_id")
        if not fid:
            continue
        ltid = f"tile:stream:lane.{fid}"
        vcount = len(lane.get("videos", []))
        tiles[ltid] = make_tile(
            tile_id=ltid,
            display_name=lane.get("title", fid),
            tile_kind="wikitube_stream",
            visibility_scope="public",
            owner_namespace="foundups_core",
            parent_tile_id="tile:stream:root",
            state="GREEN" if vcount > 0 else "AMBER",
            search_keywords=["WikiTube", "video", lane.get("title", fid), fid],
            metadata={"foundup_id": fid, "video_count": vcount, "source_type": lane.get("source_type")},
        )


def _add_mockups(tiles: Dict[str, Dict[str, Any]], tracked_files: List[str], tracked_set: Set[str]) -> None:
    archive_pngs = [
        p for p in tracked_files
        if p.startswith("modules/foundups/simulator/archive/") and p.endswith(".png")
    ]
    for idx, p in enumerate(archive_pngs, 1):
        tid = f"tile:mockup:archive_png_{idx}"
        tiles[tid] = make_tile(
            tile_id=tid,
            display_name=Path(p).name,
            tile_kind="mockup_cube",
            visibility_scope="principal_only",
            owner_namespace="foundups_core",
            parent_tile_id="tile:mockups:root",
            state="GRAY",
            dag_edges={"cross_links": ["tile:sys:simulator"] if "tile:sys:simulator" in tiles else []},
            action_target={"repo_path": p},
            search_keywords=["screenshot", "mockup", Path(p).name],
            metadata={"classification": "STATIC_ARCHIVE_SCREENSHOT"},
        )

    public_surfaces = [
        ("public_index_buildCanvas", "public/index.html", "CLIENT_CANVAS_ANIMATION_WITH_OPTIONAL_SSE", "AMBER", "#buildCanvas"),
        ("public_ecosystem_growth", "public/ecosystem.html", "STATIC_DATA_TIMELINE_PROTOTYPE", "AMBER", None),
        ("public_member_mall", "public/member/index.html", "INTERACTIVE_STATIC_WEB_SHELL", "GREEN", None),
        ("public_f_foundup_entry", "public/f/index.html", "INTERACTIVE_ROUTING_SHELL", "GREEN", None),
        ("public_f_holoindex_prod_01", "public/f/holoindex_prod_01/index.html", "MOCK_POSTMESSAGE_PROTOTYPE", "AMBER", None),
    ]
    for sid, rpath, cls_name, st, url_fragment in public_surfaces:
        if rpath not in tracked_set:
            continue
        tid = f"tile:mockup:{sid}"
        at_payload: Dict[str, Any] = {"repo_path": rpath}
        meta_payload: Dict[str, Any] = {"classification": cls_name}
        if url_fragment:
            at_payload["url_fragment"] = url_fragment
            meta_payload["url_fragment"] = url_fragment
        tiles[tid] = make_tile(
            tile_id=tid,
            display_name=sid,
            tile_kind="mockup_cube",
            visibility_scope="public",
            owner_namespace="foundups_core",
            parent_tile_id="tile:mockups:root",
            state=st,
            action_target=at_payload,
            search_keywords=["mockup", "cube", sid, cls_name],
            metadata=meta_payload,
        )


def _apply_sprint1_registry_and_duplicates(
    tiles: Dict[str, Dict[str, Any]],
    manifest: Mapping[str, Any],
) -> None:
    """Enrich existing repository tiles with verified Sprint 1 registry & duplicate evidence."""
    if not manifest:
        return

    pins = manifest.get("source_pins") or {}
    audited_rev = pins.get("audited_main_revision") or "unknown"
    reg_map = manifest.get("module_registry") or {}

    # Top-level governance and MCP system cubes (align WSP_* with knowledge_and_governance)
    has_kg_cube = "tile:sys:knowledge_and_governance" in tiles or any(
        n.get("tile_id") == "tile:sys:knowledge_and_governance"
        for n in (manifest.get("extended_repository_nodes") or [])
    )
    gov_parent = "tile:sys:knowledge_and_governance" if has_kg_cube else "tile:sys:core_systems"
    if "tile:sys:core_systems" in tiles:
        top_systems = [
            ("tile:sys:wsp_framework", "WSP Framework (Governance Protocols)", "WSP_framework", "GREEN", gov_parent),
            ("tile:sys:wsp_agentic", "WSP Agentic (0102 Operational Kernel)", "WSP_agentic", "GREEN", gov_parent),
            ("tile:sys:wsp_knowledge", "WSP Knowledge (Architecture & Papers)", "WSP_knowledge", "GREEN", gov_parent),
            ("tile:sys:foundups_mcp_p1", "FoundUps MCP P1 (FastMCP Servers)", "foundups-mcp-p1", "GREEN", "tile:sys:core_systems"),
        ]
        for stid, sname, rpath, st, parent_id in top_systems:
            if stid in tiles:
                continue
            vent = reg_map.get(rpath) or {}
            tiles[stid] = make_tile(
                tile_id=stid,
                display_name=sname,
                tile_kind="system_cube",
                visibility_scope="public",
                owner_namespace="foundups_core",
                parent_tile_id=parent_id,
                state=st,
                action_target={
                    "primary_url": f"https://github.com/FOUNDUPS/Foundups-Agent/tree/{audited_rev}/{rpath}",
                    "repo_path": rpath,
                },
                search_keywords=[sname, rpath, "WSP", "Sprint 1"],
                metadata={
                    "domain": "top_level_system",
                    "module_name": rpath,
                },
            )

    # Project additional whole-repository structural/system/archive/config/gitlink nodes
    for ext_node in manifest.get("extended_repository_nodes") or []:
        etid = ext_node["tile_id"]
        if etid in tiles:
            # Merge metadata if canonical tile already exists
            ex_tile = tiles[etid]
            ex_meta = ex_tile.setdefault("metadata", {})
            if ext_node.get("registry_verification"):
                ex_meta["registry_verification"] = copy.deepcopy(ext_node["registry_verification"])
            ex_edges = ex_tile.setdefault("dag_edges", {})
            calls_l = list(ex_edges.get("calls") or [])
            for cid in ext_node.get("outbound_tile_ids") or []:
                if cid != etid and cid not in calls_l:
                    calls_l.append(cid)
            ex_edges["calls"] = calls_l
            continue

        at_payload: Dict[str, Any] = {"primary_url": f"https://play.foundups.com/#{etid}"}
        if ext_node.get("repo_path"):
            at_payload["repo_path"] = ext_node["repo_path"]
        if ext_node.get("interface_doc"):
            at_payload["interface_doc"] = ext_node["interface_doc"]

        wsp_raw = ext_node.get("wsp15_canonical")
        wsp_obj = None
        if isinstance(wsp_raw, dict) and all(k in wsp_raw for k in ("complexity", "importance", "deferability", "impact")):
            wsp_obj = compute_wsp15_canonical(
                int(wsp_raw["complexity"]),
                int(wsp_raw["importance"]),
                int(wsp_raw["deferability"]),
                int(wsp_raw["impact"]),
            )

        tiles[etid] = make_tile(
            tile_id=etid,
            display_name=ext_node["display_name"],
            tile_kind=ext_node.get("tile_kind", "system_cube"),
            visibility_scope=ext_node.get("visibility_scope", "public"),
            owner_namespace=ext_node.get("owner_namespace", "foundups_core"),
            parent_tile_id=ext_node.get("parent_tile_id", ROOT_TILE_ID),
            state=ext_node.get("state", "GREEN"),
            dag_edges={
                "calls": list(ext_node.get("outbound_tile_ids") or []),
                "cross_links": list(ext_node.get("cross_links") or []),
            },
            wsp15_canonical=wsp_obj,
            action_target=at_payload,
            search_keywords=list(ext_node.get("keywords") or [ext_node["display_name"]]),
            metadata={
                "registry_verification": copy.deepcopy(ext_node.get("registry_verification") or {}),
                "metadata_only": bool(ext_node.get("metadata_only", False)),
            },
        )

    # Enrich AutoPost external repository pin without altering its canonical investor identity
    ext_repos = pins.get("external_repositories") or {}
    if "tile:engine:autopost" in tiles and "FOUNDUPS/AutoPost" in ext_repos:
        ap_pin = ext_repos["FOUNDUPS/AutoPost"]
        tiles["tile:engine:autopost"].setdefault("metadata", {})["external_repo_verification"] = {
            "repository": "FOUNDUPS/AutoPost",
            "head_sha": ap_pin.get("head_sha"),
            "tracked_files": ap_pin.get("tracked_files"),
        }

    # Add external accessible repositories where not already created by foundup_registry.json
    ssh_handoff_doc = "modules/foundups/pqn_swarm_hub/EXFOLIATION_PLAN.md"
    ssh_cross_links = ["tile:mod:ai_intelligence.pqn_alignment", "tile:mod:foundups.pqn_swarm_hub"]
    if "tile:investor:root" in tiles and "tile:investor:science_swarm_hub" not in tiles:
        ssh_pin = ext_repos.get("FOUNDUPS/science-swarm-hub") or {}
        tiles["tile:investor:science_swarm_hub"] = make_tile(
            tile_id="tile:investor:science_swarm_hub",
            display_name="Science Swarm Hub (External Exfoliated Repo)",
            tile_kind="foundup_venture",
            visibility_scope="public",
            owner_namespace="foundups_core",
            parent_tile_id="tile:investor:root",
            state="AMBER",
            dag_edges={
                "cross_links": list(ssh_cross_links),
            },
            action_target={
                "primary_url": "https://github.com/FOUNDUPS/science-swarm-hub",
                "in_repo_handoff_path": ssh_handoff_doc,
                "interface_doc": ssh_handoff_doc,
            },
            search_keywords=["science-swarm-hub", "PQN", "external repo"],
            metadata={
                "repository": "FOUNDUPS/science-swarm-hub",
                "head_sha": ssh_pin.get("head_sha"),
                "tracked_files": ssh_pin.get("tracked_files"),
                "in_repo_handoff_path": ssh_handoff_doc,
            },
        )
    elif "tile:investor:science_swarm_hub" in tiles and "FOUNDUPS/science-swarm-hub" in ext_repos:
        ssh_pin = ext_repos["FOUNDUPS/science-swarm-hub"]
        ssh_tile = tiles["tile:investor:science_swarm_hub"]
        ssh_tile["visibility_scope"] = "public"
        ssh_at = ssh_tile.setdefault("action_target", {})
        ssh_at["primary_url"] = "https://github.com/FOUNDUPS/science-swarm-hub"
        ssh_at["in_repo_handoff_path"] = ssh_handoff_doc
        ssh_at["interface_doc"] = ssh_handoff_doc
        ssh_at.pop("repo_path", None)
        ssh_edges = ssh_tile.setdefault("dag_edges", {})
        ssh_cl = list(ssh_edges.get("cross_links") or [])
        for cl_id in ssh_cross_links:
            if cl_id not in ssh_cl:
                ssh_cl.append(cl_id)
        ssh_edges["cross_links"] = ssh_cl
        ssh_meta = ssh_tile.setdefault("metadata", {})
        ssh_meta["in_repo_handoff_path"] = ssh_handoff_doc
        ssh_meta["external_repo_verification"] = {
            "repository": "FOUNDUPS/science-swarm-hub",
            "head_sha": ssh_pin.get("head_sha"),
            "tracked_files": ssh_pin.get("tracked_files"),
        }

    if "tile:mockups:root" in tiles and "tile:mockup:foundups_github_io" not in tiles:
        ghio_pin = ext_repos.get("FOUNDUPS/foundups.github.io") or {}
        tiles["tile:mockup:foundups_github_io"] = make_tile(
            tile_id="tile:mockup:foundups_github_io",
            display_name="foundups.github.io (Legacy Static Repo)",
            tile_kind="mockup_cube",
            visibility_scope="public",
            owner_namespace="foundups_core",
            parent_tile_id="tile:mockups:root",
            state="GRAY",
            action_target={"primary_url": "https://github.com/FOUNDUPS/foundups.github.io"},
            search_keywords=["foundups.github.io", "legacy", "external repo"],
            metadata={
                "repository": "FOUNDUPS/foundups.github.io",
                "head_sha": ghio_pin.get("head_sha"),
                "tracked_files": ghio_pin.get("tracked_files"),
            },
        )

    # Project adjudicated 16 duplicate clusters under tile:modules:root (principal_only)
    clusters = manifest.get("duplicate_clusters") or []
    if clusters and "tile:modules:root" in tiles:
        tiles["tile:domain:duplicate_audit"] = make_tile(
            tile_id="tile:domain:duplicate_audit",
            display_name="Duplicate & Reuse Audit (16 Clusters)",
            tile_kind="system_cube",
            visibility_scope="principal_only",
            owner_namespace="foundups_core",
            parent_tile_id="tile:modules:root",
            state="AMBER",
            search_keywords=["duplicate", "WSP 84", "reuse", "audit"],
            metadata={"cluster_count": len(clusters), "git_revision": audited_rev},
        )
        for cl in clusters:
            dtid = f"tile:dup:{cl['cluster_id']}"
            rel_tiles: List[str] = []
            for fp in cl.get("files_sampled", []):
                parts = str(fp).split("/")
                cand: Optional[str] = None
                if len(parts) >= 3 and parts[0] == "modules":
                    cand = _tile_id_for_owner(f"modules/{parts[1]}/{parts[2]}")
                elif parts and parts[0] == "holo_index":
                    cand = "tile:sys:holo_index"
                elif parts and parts[0] == "foundups-mcp-p1":
                    cand = "tile:sys:foundups_mcp_p1"
                elif len(parts) >= 2 and parts[0] == "extensions" and parts[1] == "reddog":
                    cand = "tile:sys:extensions_reddog"
                if cand and cand in tiles and cand not in rel_tiles:
                    rel_tiles.append(cand)
            is_hist = cl.get("verifier_classification") == "historical_superseded"
            tiles[dtid] = make_tile(
                tile_id=dtid,
                display_name=cl["title"],
                tile_kind="code_module",
                visibility_scope="principal_only",
                owner_namespace="foundups_core",
                parent_tile_id="tile:domain:duplicate_audit",
                state="GRAY" if is_hist else "AMBER",
                dag_edges={
                    "reads_from": rel_tiles,
                    "reusable_candidates": rel_tiles,
                },
                search_keywords=["duplicate", cl["cluster_id"], cl.get("verifier_classification", "")],
                metadata={
                    "duplicate_cluster": cl,
                    "git_revision": audited_rev,
                },
            )


def _attach_registry_verification(
    tiles: Dict[str, Dict[str, Any]],
    manifest: Mapping[str, Any],
) -> None:
    """Attach canonical ``registry_verification`` metadata across all registered tiles."""
    if not manifest:
        return
    pins = manifest.get("source_pins") or {}
    audited_rev = pins.get("audited_main_revision") or "unknown"
    reg_map = manifest.get("module_registry") or {}
    reg_by_tile_id = manifest.get("registry_by_tile_id") or {}

    for tile in tiles.values():
        at = tile.get("action_target") or {}
        rpath = at.get("repo_path")
        vent = reg_by_tile_id.get(tile["tile_id"]) or (reg_map.get(rpath) if rpath else None)
        if not vent:
            continue
        func_ev = vent.get("functionality_evidence") or {}
        integ_ev = vent.get("integration_evidence") or {}
        meta = tile.setdefault("metadata", {})
        rv_payload: Dict[str, Any] = {
            "registry_id": vent.get("registry_id"),
            "revision": vent.get("revision", audited_rev),
            "purpose": vent.get("purpose", ""),
            "owner": vent.get("owner", ""),
            "owner_provenance": vent.get("owner_provenance", "inferred_from_directory"),
            "repository_slug": vent.get("repository_slug", "FOUNDUPS/Foundups-Agent"),
            "functionality_state": vent.get("functionality_state", "UNKNOWN"),
            "integration_state": vent.get("integration_state", "UNKNOWN"),
            "test_execution_status": vent.get("test_execution_status", "NOT_EXECUTED_STATIC_CENSUS"),
            "inbound_callers_window": vent.get("inbound_callers_window"),
            "functionality_evidence": {
                "non_test_py_count": func_ev.get("non_test_py_count", 0),
                "test_py_count": func_ev.get("test_py_count", 0),
                "docs_present": func_ev.get("docs_present", []),
                "classes_sample": (func_ev.get("classes_sample") or [])[:5],
                "placeholder_only": bool(func_ev.get("placeholder_only", False)),
                "note": func_ev.get("note", ""),
            },
            "integration_evidence": integ_ev,
            "production_status": vent.get("production_status", "UNVERIFIED"),
            "reusability_verdict": vent.get("reusability_verdict", ""),
        }
        if vent.get("private_provenance"):
            rv_payload["private_provenance"] = copy.deepcopy(vent["private_provenance"])
        meta["registry_verification"] = rv_payload
        # Honor upstream architect-only visibility independently of readiness when not RED
        if vent.get("visibility_scope") == "principal_only" and tile.get("lifecycle", {}).get("state") != "RED":
            tile["visibility_scope"] = "principal_only"
        edges = tile.setdefault("dag_edges", {})
        calls_list = list(edges.get("calls") or [])
        for candidate_id in vent.get("outbound_tile_ids", []):
            if candidate_id != tile["tile_id"] and candidate_id not in calls_list:
                calls_list.append(candidate_id)
        edges["calls"] = calls_list


def _add_tools_and_benchmark(
    tiles: Dict[str, Dict[str, Any]],
    manifest: Mapping[str, Any],
) -> None:
    """Project Tools -> Benchmark -> harness -> config -> run -> exact-revision evidence subgraph."""
    if not manifest or "tile:tools:root" not in tiles:
        return

    pins = manifest.get("source_pins") or {}
    audited_rev = pins.get("audited_main_revision") or "unknown"

    # Benchmark container under Tools (first child of tile:tools:root)
    bench_id = "tile:tools:benchmark"
    ledger_id = "tile:receipt:benchmark_ledger"
    all_tool_ids = [t["tile_id"] for t in manifest.get("pc_tools", [])]
    eval_module_ids = [
        "tile:mod:foundups.agent_market",
        "tile:sys:simulator",
        "tile:mod:ai_intelligence.ai_gateway",
        "tile:mod:infrastructure.shared_utilities",
        "tile:mod:infrastructure.wre_core",
        "tile:mod:infrastructure.mcp_manager",
    ]

    tiles[bench_id] = make_tile(
        tile_id=bench_id,
        display_name="Benchmark",
        tile_kind="system_cube",
        visibility_scope="public",
        owner_namespace="foundups_core",
        parent_tile_id="tile:tools:root",
        state="GREEN",
        children_tile_ids=[
            "tile:harness:model_combination_benchmark",
            "tile:harness:wre_auto_researcher",
            "tile:harness:lego_scaffolding_protocol",
            ledger_id,
        ],
        dag_edges={
            "runs_through": list(all_tool_ids),
            "cross_links": list(all_tool_ids),
            "evaluates": list(eval_module_ids),
            "produces_receipt": [
                "tile:receipt:harness_primary_3pkt",
                "tile:receipt:harness_retest_pkt04",
                "tile:receipt:topology_admission_d809a106",
            ],
            "verified_by": ["tile:receipt:independent_verifier_s1"],
        },
        action_target={
            "primary_url": f"https://play.foundups.com/#{bench_id}",
            "repo_path": "modules/ai_intelligence/ai_gateway/src/model_combination_benchmark_harness.py",
        },
        search_keywords=["Tools", "Benchmark", "harnesses", "PC tools", "Sprint 1"],
        metadata={
            "benchmark_evidence": {
                "git_revision": audited_rev,
                "verdict": "20_RUNS_SCORED_5_CONFIGS",
                "cost_usd": 0.0,
                "harness_receipt_id": pins.get("primary_harness_receipt_id"),
                "evaluated_modules": list(eval_module_ids),
            },
        },
    )

    tiles["tile:tools:root"]["children_tile_ids"] = [bench_id] + list(all_tool_ids)

    # Canonical PC Tools (single canonical identity under tile:tools:root; cross-linked into Benchmark)
    for tool in manifest.get("pc_tools", []):
        ttid = tool["tile_id"]
        is_socket = tool.get("tile_kind") == "socket_slot"
        pkt_ids = [f"tile:benchevidence:{pid}" for pid in tool.get("evaluates_packet_ids", [])]
        tiles[ttid] = make_tile(
            tile_id=ttid,
            display_name=tool["display_name"],
            tile_kind=tool.get("tile_kind", "system_cube"),
            visibility_scope="public",
            owner_namespace="foundups_core",
            parent_tile_id="tile:tools:root",
            state=tool.get("state", "AMBER"),
            dag_edges={
                "calls": list(tool.get("owner_tiles", [])),
                "reads_from": pkt_ids,
                "evaluates": pkt_ids,
                "cross_links": [bench_id],
            },
            action_target={"primary_url": f"https://play.foundups.com/#{ttid}"},
            rescue_axes=_make_non_code_rescue(
                completeness=1 if is_socket else 4,
                impact=4,
                reusability=5,
                effort_to_green=4 if is_socket else 1,
                next_action="Install hermes binary on PATH and wire adapter verification"
                if is_socket else "Maintain verified PC tool inventory & VRAM/budget gates",
                note=tool.get("summary", ""),
            ) if (is_socket or tool.get("state") == "AMBER") else None,
            search_keywords=list(tool.get("keywords", [])),
            metadata={
                "benchmark_evidence": {
                    "availability": tool.get("availability"),
                    "summary": tool.get("summary"),
                    "models": tool.get("models", []),
                    "hardware_baseline": tool.get("hardware_baseline"),
                    "cost_usd": tool.get("cost_usd", 0.0),
                    "git_revision": audited_rev,
                    "missing_capability_reason": tool.get("summary") if is_socket else None,
                },
            },
        )

    # Benchmark Ledger (canonical parent for evidence packets & cryptographic receipts)
    tiles[ledger_id] = make_tile(
        tile_id=ledger_id,
        display_name="Benchmark Ledger — Evidence & Receipts",
        tile_kind="system_cube",
        visibility_scope="public",
        owner_namespace="foundups_core",
        parent_tile_id=bench_id,
        state="GREEN",
        search_keywords=["Benchmark", "evidence", "receipts", "7432d31e5"],
        metadata={
            "benchmark_evidence": {
                "git_revision": audited_rev,
                "summary": "Canonical store for frozen Sprint 1 audit packets at 7432d31e5 and rehydrateable cryptographic harness receipts.",
                "harness_receipt_id": pins.get("primary_harness_receipt_id"),
            },
        },
    )

    for pkt in manifest.get("benchmark_evidence_packets", []):
        epid = pkt["tile_id"]
        mod_ids = list(pkt.get("target_module_tile_ids", []))
        corr_summary = [
            f"[{c.get('severity', 'INFO')}] {c.get('kind', '')}: {c.get('detail', '')}"
            for c in pkt.get("corrections_and_omissions", [])
        ]
        tiles[epid] = make_tile(
            tile_id=epid,
            display_name=pkt["display_name"],
            tile_kind="system_cube",
            visibility_scope="public",
            owner_namespace="foundups_core",
            parent_tile_id=ledger_id,
            state="GREEN",
            dag_edges={
                "reads_from": mod_ids,
                "verified_by": ["tile:receipt:independent_verifier_s1"],
                "cross_links": mod_ids + ["tile:receipt:independent_verifier_s1"],
            },
            action_target={
                "primary_url": pkt.get("primary_url"),
                "repo_path": pkt.get("target_repo_path"),
            },
            search_keywords=["Benchmark", "evidence", pkt["packet_id"], pkt["git_revision"], pkt["target_repo_path"]],
            metadata={
                "benchmark_evidence": {
                    "packet_id": pkt["packet_id"],
                    "git_revision": pkt["git_revision"],
                    "target_repo_path": pkt["target_repo_path"],
                    "carbon_claim_verdict": pkt.get("carbon_claim_verdict"),
                    "what_it_does": pkt.get("what_it_does"),
                    "required_facts": pkt.get("required_facts", []),
                    "agreements": pkt.get("agreements", []),
                    "corrections_summary": corr_summary,
                    "unknowns_or_gaps": pkt.get("unknowns_or_gaps", []),
                    "sealed_packet_sha256": pkt.get("sealed_packet_sha256"),
                    "reference_key_sha256": pkt.get("reference_key_sha256"),
                    "verifier_artifact_sha256": pkt.get("verifier_artifact_sha256"),
                },
            },
        )

    for rec in manifest.get("benchmark_receipts", []):
        rtid = rec["tile_id"]
        rec_be: Dict[str, Any] = {
            "harness_receipt_id": rec["receipt_id"],
            "rehydrated_ok": rec.get("rehydrated_ok", True),
            "git_revision": rec["git_revision"],
            "runs_count": rec.get("runs_count"),
            "digest_sha256": rec.get("digest_sha256"),
            "summary": rec.get("summary"),
            "verdict": rec.get("verdict"),
            "decision_lifecycle": rec.get("decision_lifecycle"),
            "adjudication_status": rec.get("adjudication_status"),
            "supersedes_receipt_id": rec.get("supersedes_receipt_id"),
            "effective_receipt_id_retained_until_reddog_approval": rec.get("effective_receipt_id_retained_until_reddog_approval"),
            "candidate_aggregate": rec.get("candidate_aggregate"),
        }
        if rec.get("receipt_history"):
            rec_be["receipt_history"] = copy.deepcopy(rec["receipt_history"])
        tiles[rtid] = make_tile(
            tile_id=rtid,
            display_name=rec["display_name"],
            tile_kind="system_cube",
            visibility_scope=rec.get("visibility_scope", "public"),
            owner_namespace="foundups_core",
            parent_tile_id=ledger_id,
            state=rec.get("state", "GREEN"),
            dag_edges={
                "cross_links": list(rec.get("cross_links") or []),
            },
            action_target={"primary_url": f"https://play.foundups.com/#{rtid}"},
            search_keywords=["Benchmark", "receipt", rec["receipt_id"], rec["git_revision"]],
            metadata={
                "benchmark_evidence": rec_be,
            },
        )

    # Benchmark Harnesses (under tile:tools:benchmark)
    cfg_order = [c["tile_id"] for c in manifest.get("benchmark_configurations", [])]
    for harness in manifest.get("benchmark_harnesses", []):
        htid = harness["tile_id"]
        is_mcb = htid == "tile:harness:model_combination_benchmark"
        miss = harness.get("missing_adapter_socket")
        ev_pkt_ids = [p["tile_id"] for p in manifest.get("benchmark_evidence_packets", [])] if is_mcb else []
        tiles[htid] = make_tile(
            tile_id=htid,
            display_name=harness["display_name"],
            tile_kind=harness.get("tile_kind", "system_cube"),
            visibility_scope="public",
            owner_namespace="foundups_core",
            parent_tile_id=bench_id,
            state=harness.get("state", "AMBER"),
            children_tile_ids=list(cfg_order) if is_mcb else ([miss["tile_id"]] if miss else []),
            dag_edges={
                "calls": list(harness.get("owner_tiles", [])),
                "runs_through": list(harness.get("tool_tiles", [])),
                "evaluates": list(cfg_order if is_mcb else []) + ev_pkt_ids + list(harness.get("evaluates_modules", [])),
                "produces_receipt": list(harness.get("receipt_tiles", [])),
                "verified_by": ["tile:receipt:independent_verifier_s1"],
            },
            action_target={
                "primary_url": f"https://play.foundups.com/#{htid}",
                "repo_path": harness.get("repo_path"),
            },
            search_keywords=list(harness.get("keywords", [])),
            metadata={
                "benchmark_evidence": {
                    "summary": harness.get("summary"),
                    "git_revision": audited_rev if is_mcb or htid == "tile:harness:wre_auto_researcher" else pins.get("lego_slice1_revision"),
                    "evaluated_modules": list(harness.get("evaluates_modules", [])),
                    "evaluated_models": [c["model_name"] for c in manifest.get("benchmark_configurations", [])] if is_mcb else [],
                    "evaluated_scaffolds": sorted({c["scaffold_name"] for c in manifest.get("benchmark_configurations", [])}) if is_mcb else [],
                    "cost_usd": 0.0,
                },
            },
        )
        if miss:
            mtid = miss["tile_id"]
            tiles[mtid] = make_tile(
                tile_id=mtid,
                display_name=miss["display_name"],
                tile_kind="socket_slot",
                visibility_scope="public",
                owner_namespace="foundups_core",
                parent_tile_id=htid,
                state="BLUE",
                dag_edges={
                    "reusable_candidates": ["tile:harness:model_combination_benchmark"],
                    "cross_links": ["tile:harness:model_combination_benchmark", "tile:benchevidence:pkt_04_retest_unseen"],
                },
                rescue_axes=_make_non_code_rescue(
                    completeness=1,
                    impact=5,
                    reusability=4,
                    effort_to_green=3,
                    next_action="Implement AuditPacketResearchAdapter delegating read-only sealed packets to model_combination_benchmark_harness while keeping WREAutoResearcher simulator judge task-specific.",
                    note=miss["missing_capability_reason"],
                ),
                action_target={
                    "primary_url": f"https://play.foundups.com/#{mtid}",
                    "repo_path": "modules/infrastructure/wre_core/src/wre_auto_researcher.py",
                    "interface_doc": miss.get("interface_doc"),
                },
                search_keywords=["AuditPacketResearchAdapter", "WRE Auto Researcher", "Open Researcher", "missing adapter", "BLUE"],
                metadata={
                    "benchmark_evidence": {
                        "verdict": "PLANNED_SOCKET",
                        "git_revision": audited_rev,
                        "summary": miss["summary"],
                        "missing_capability_reason": miss["missing_capability_reason"],
                        "proposed_inputs": miss.get("proposed_inputs", []),
                        "proposed_outputs": miss.get("proposed_outputs", []),
                    },
                },
            )

    # Configurations (under tile:harness:model_combination_benchmark) + Runs (children of configs)
    runs_by_cfg: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for run in manifest.get("benchmark_runs", []):
        runs_by_cfg[run["config_tile_id"]].append(run)

    for cfg in manifest.get("benchmark_configurations", []):
        ctid = cfg["tile_id"]
        cfg_runs = runs_by_cfg.get(ctid, [])
        is_blocked = cfg.get("state") == "BLUE"
        eval_targets: List[str] = []
        for r in cfg_runs:
            for tgt in [r["evidence_tile_id"]] + list(r.get("target_module_tile_ids", [])):
                if tgt not in eval_targets:
                    eval_targets.append(tgt)
        tiles[ctid] = make_tile(
            tile_id=ctid,
            display_name=cfg["display_name"],
            tile_kind=cfg.get("tile_kind", "system_cube"),
            visibility_scope="public",
            owner_namespace="foundups_core",
            parent_tile_id=cfg["harness_tile_id"],
            state=cfg.get("state", "AMBER"),
            children_tile_ids=[r["tile_id"] for r in cfg_runs],
            dag_edges={
                "runs_through": [cfg["tool_tile_id"], cfg["harness_tile_id"]],
                "evaluates": eval_targets,
                "produces_receipt": list(cfg.get("receipt_tiles", [])),
                "verified_by": ["tile:receipt:independent_verifier_s1"] if not is_blocked else [],
                "cross_links": [cfg["tool_tile_id"]] + list(cfg.get("receipt_tiles", [])),
            },
            action_target={"primary_url": f"https://play.foundups.com/#{ctid}"},
            search_keywords=list(cfg.get("keywords", [])),
            metadata={
                "benchmark_evidence": {
                    "model_name": cfg["model_name"],
                    "scaffold_name": cfg["scaffold_name"],
                    "summary": cfg["summary"],
                    "runs_count": len(cfg_runs),
                    "cost_usd": 0.0,
                    "git_revision": audited_rev,
                    "missing_capability_reason": cfg["summary"] if is_blocked else None,
                },
            },
        )

        for r in cfg_runs:
            rtid = r["tile_id"]
            prod_rec_tiles = [r["harness_receipt_tile_id"]]
            for cand_tile_key in (
                "candidate_v2_1_receipt_tile_id",
                "candidate_v2_2_receipt_tile_id",
                "candidate_v2_3_receipt_tile_id",
            ):
                if r.get(cand_tile_key) and r[cand_tile_key] not in prod_rec_tiles:
                    prod_rec_tiles.append(r[cand_tile_key])
            cross_l = [r["evidence_tile_id"]] + prod_rec_tiles + [r["verifier_receipt_tile_id"], r["tool_tile_id"]]
            run_be: Dict[str, Any] = {
                "run_id": r["run_id"],
                "phase": r["phase"],
                "intervention_classification": r.get("intervention_classification"),
                "packet_id": r["packet_id"],
                "model_name": r["model_name"],
                "scaffold_name": r["scaffold_name"],
                "verdict": r["verdict"],
                "effective_verdict": r.get("effective_verdict", str(r["verdict"]).upper()),
                "decision_lifecycle": r.get("decision_lifecycle"),
                "adjudication_status": r.get("adjudication_status"),
                "parse_status": r.get("parse_status"),
                "schema_status": r.get("schema_status"),
                "schema_errors": list(r.get("schema_errors") or []),
                "factual_coverage": r["factual_coverage"],
                "schema_valid": r["schema_valid"],
                "candidate_aggregate": r.get("candidate_aggregate"),
                "latency_ms": r["latency_ms"],
                "input_tokens": r["input_tokens"],
                "output_tokens": r["output_tokens"],
                "vram_before_mib": r["vram_before_mib"],
                "vram_after_mib": r["vram_after_mib"],
                "cost_usd": r["cost_usd"],
                "error_taxonomy": r["error_taxonomy"],
                "beat_incumbent": r["beat_incumbent"],
                "git_revision": r["git_revision"],
                "target_repo_path": r["target_repo_path"],
                "harness_receipt_id": r["harness_receipt_id"],
                "candidate_v2_1_receipt_id": r.get("candidate_v2_1_receipt_id"),
                "candidate_v2_2_receipt_id": r.get("candidate_v2_2_receipt_id"),
                "candidate_v2_3_receipt_id": r.get("candidate_v2_3_receipt_id"),
                "supersedes_receipt_id": r.get("supersedes_receipt_id"),
                "per_fact_scores": list(r.get("per_fact_scores") or []),
                "supported_claims": r.get("supported_claims", []),
                "missed_facts": r.get("missed_facts", []),
                "incorrect_or_unsupported_claims": r.get("incorrect_or_unsupported_claims", []),
                "provisional_agreement": r.get("provisional_agreement"),
            }
            if r.get("receipt_history"):
                run_be["receipt_history"] = copy.deepcopy(r["receipt_history"])
            tiles[rtid] = make_tile(
                tile_id=rtid,
                display_name=r["display_name"],
                tile_kind="system_cube",
                visibility_scope="public",
                owner_namespace="foundups_core",
                parent_tile_id=ctid,
                state=r["state"],
                dag_edges={
                    "cross_links": cross_l,
                    "reads_from": [r["evidence_tile_id"]],
                    "evaluates": [r["evidence_tile_id"]] + list(r.get("target_module_tile_ids", [])),
                    "runs_through": [r["tool_tile_id"], r["harness_tile_id"]],
                    "produces_receipt": prod_rec_tiles,
                    "verified_by": [r["verifier_receipt_tile_id"]],
                },
                action_target={
                    "primary_url": f"https://play.foundups.com/#{rtid}",
                    "repo_path": r["target_repo_path"],
                },
                search_keywords=[
                    "Benchmark",
                    "run",
                    r["packet_id"],
                    r["model_name"],
                    r["scaffold_name"],
                    r["verdict"],
                    r["git_revision"],
                ],
                metadata={
                    "step_explodable": True,
                    "benchmark_evidence": run_be,
                },
            )


_CHAPTER_INDEXED_DOCS: Tuple[Tuple[str, str], ...] = (
    ("tile:opus:papers.resp_quantum_self_reference.md", "WSP_knowledge/docs/Papers/rESP_Quantum_Self_Reference.md"),
    ("tile:opus:papers.peer_preservation_shared_latent_coupling.md", "WSP_knowledge/docs/Papers/Peer_Preservation_Shared_Latent_Coupling.md"),
    ("tile:opus:papers.pqn_research_plan.md", "WSP_knowledge/docs/Papers/PQN_Research_Plan.md"),
    ("tile:opus:papers.resp_supplementary_materials.md", "WSP_knowledge/docs/Papers/rESP_Supplementary_Materials.md"),
    ("tile:opus:papers.dukkyo_practitioners.md", "WSP_knowledge/docs/Papers/Dukkyo_Practitioners.md"),
    ("tile:opus:jhr.001", "modules/foundups/esingularity/jhr/reports/JHR_001_2026-09_JAPAN_HYPERSCALER_REPORT.md"),
    ("tile:opus:jhr.003", "modules/foundups/esingularity/jhr/reports/JHR_003_2026-09_AI_RICE_FIELDS_AI_KOBAN.md"),
    ("tile:opus:roc.formula_derivation", "modules/foundups/simulator/docs/ROC_FORMULA_DERIVATION.md"),
)

_CANONICAL_ELEMENT_MODES_ORDER = ("video", "pictures", "podcast", "cards")
_APPLICATION_MOCKUP_IDS = frozenset({
    "tile:mockup:public_index_buildCanvas",
    "tile:mockup:public_ecosystem_growth",
    "tile:mockup:public_member_mall",
    "tile:mockup:public_f_foundup_entry",
    "tile:mockup:public_f_holoindex_prod_01",
    "tile:mockup:foundups_github_io",
})
_APPLICATION_SYS_IDS = frozenset({
    "tile:sys:public_f",
    "tile:sys:public_member",
    "tile:sys:public_root",
    "tile:untracked:eSingularity.ai",
    "tile:untracked:sites",
})


def _sanitize_chapter_excerpt(lines: List[str], *, max_chars: int = 220) -> str:
    """Build a plain-text, WSP 71-safe chapter excerpt from body lines."""
    collected: List[str] = []
    in_fence = False
    fence_char = ""
    fence_len = 0
    in_html_comment = False

    for raw in lines:
        stripped = raw.strip()
        leading = raw.lstrip()
        if len(raw) - len(leading) <= 3:
            m_fence = re.match(r"^(`{3,}|~{3,})", leading)
            if m_fence:
                seq = m_fence.group(1)
                if not in_fence:
                    in_fence = True
                    fence_char = seq[0]
                    fence_len = len(seq)
                    continue
                if seq[0] == fence_char and len(seq) >= fence_len and stripped == seq:
                    in_fence = False
                    continue
        if in_fence:
            continue
        if "<!--" in stripped:
            in_html_comment = "-->" not in stripped
            continue
        if in_html_comment:
            if "-->" in stripped:
                in_html_comment = False
            continue
        if not stripped:
            continue
        if re.match(r"^([-*_])\1{2,}$", stripped) or re.match(r"^\|?[\s:|-]+\|?$", stripped):
            continue
        if stripped.startswith("#"):
            # Include subheading text lightly if body hasn't started yet
            stripped = stripped.lstrip("#").strip()
            if not stripped:
                continue

        text_line = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", stripped)
        text_line = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text_line)
        text_line = re.sub(r"^[>\-*+]\s+", "", text_line)
        text_line = text_line.replace("**", "").replace("__", "").replace("`", "")
        text_line = text_line.replace("\\\\", " ").replace("\\", "")
        text_line = _FORBIDDEN_LEAK_RE.sub("", text_line)
        text_line = re.sub(r"\s+", " ", text_line).strip()
        if text_line:
            collected.append(text_line)
        if sum(len(part) for part in collected) >= max_chars + 40:
            break

    joined = re.sub(r"\s+", " ", " ".join(collected)).strip()
    joined = _FORBIDDEN_LEAK_RE.sub("", joined)
    joined = re.sub(r"\s+", " ", joined).strip()
    if len(joined) > max_chars:
        cut = joined[: max_chars - 3].rsplit(" ", 1)[0].rstrip(" ,;:")
        joined = (cut or joined[: max_chars - 3]) + "..."
    if scan_wsp71_leaks(joined):
        return ""
    return joined


def _extract_markdown_chapters(text: str, max_chapters: int = 20) -> List[Dict[str, Any]]:
    """Extract ordered ``## `` chapters with 1-based line ranges and safe excerpts, ignoring fenced blocks."""
    if not text or max_chapters <= 0:
        return []

    lines = text.splitlines()
    total_lines = len(lines)
    if total_lines == 0:
        return []

    headings: List[Tuple[int, str]] = []
    in_fence = False
    fence_char = ""
    fence_len = 0

    for idx, raw in enumerate(lines, 1):
        leading = raw.lstrip()
        stripped = raw.strip()
        if len(raw) - len(leading) <= 3:
            m_fence = re.match(r"^(`{3,}|~{3,})", leading)
            if m_fence:
                seq = m_fence.group(1)
                if not in_fence:
                    in_fence = True
                    fence_char = seq[0]
                    fence_len = len(seq)
                    continue
                if seq[0] == fence_char and len(seq) >= fence_len and stripped == seq:
                    in_fence = False
                    continue
        if in_fence:
            continue
        m_h2 = re.match(r"^\s{0,3}##\s+(.+?)\s*#*\s*$", raw)
        if m_h2:
            title = re.sub(r"\s+", " ", m_h2.group(1)).strip()
            if title:
                headings.append((idx, title))

    if not headings:
        return []

    chapters: List[Dict[str, Any]] = []
    for pos, (start_line, title) in enumerate(headings[:max_chapters]):
        end_line = headings[pos + 1][0] - 1 if (pos + 1) < len(headings) else total_lines
        body_lines = lines[start_line:end_line]
        excerpt = _sanitize_chapter_excerpt(body_lines)
        chapters.append({
            "title": title,
            "start_line": start_line,
            "end_line": end_line,
            "chapter_excerpt": excerpt,
        })
    return chapters


def _read_pinned_text(
    repo_root: Path,
    rel_path: str,
    source_rev: str,
    blob_cache: Optional[Mapping[str, bytes]] = None,
) -> str:
    """Read *rel_path* strictly from pinned *source_rev* in git or explicit *blob_cache*; fail closed otherwise."""
    if rel_path in PRIVATE_METADATA_ONLY_PATHS:
        raise PermissionError(f"Metadata-only guard forbids reading content of {rel_path}")
    if (repo_root / ".git").exists():
        if not re.fullmatch(r"[0-9a-fA-F]{7,40}", source_rev or ""):
            return ""
        try:
            proc = subprocess.run(
                ["git", "-C", str(repo_root), "show", f"{source_rev}:{rel_path}"],
                capture_output=True,
                check=False,
            )
            if proc.returncode != 0:
                return ""
            raw = proc.stdout
        except Exception:
            return ""
    elif blob_cache is not None and rel_path in blob_cache:
        raw = blob_cache[rel_path]
    else:
        return ""
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        return raw.decode("utf-16", errors="replace")
    return raw.decode("utf-8-sig", errors="replace")


def _add_document_chapter_tiles(
    tiles: Dict[str, Dict[str, Any]],
    repo_root: Path,
    source_rev: str,
    blob_cache: Optional[Mapping[str, bytes]] = None,
) -> None:
    """Attach navigable ``opus_item`` chapter children for tracked papers and reports."""
    for parent_tid, doc_path in _CHAPTER_INDEXED_DOCS:
        if doc_path in PRIVATE_METADATA_ONLY_PATHS:
            continue
        parent_tile = tiles.get(parent_tid)
        if parent_tile is None:
            continue
        txt = _read_pinned_text(repo_root, doc_path, source_rev, blob_cache=blob_cache)
        if not txt:
            continue
        chapters = _extract_markdown_chapters(txt, max_chapters=20)
        if not chapters:
            continue

        total = len(chapters)
        parent_title = str(parent_tile.get("display_name") or doc_path)
        parent_tile.setdefault("metadata", {})["chapter_count"] = total

        for idx, ch in enumerate(chapters, 1):
            ch_tid = f"{parent_tid}.ch{idx:02d}"
            if ch_tid in tiles:
                continue
            s_line = int(ch["start_line"])
            e_line = int(ch["end_line"])
            blob_url = (
                f"https://github.com/FOUNDUPS/Foundups-Agent/blob/"
                f"{source_rev}/{doc_path}#L{s_line}-L{e_line}"
            )
            tiles[ch_tid] = make_tile(
                tile_id=ch_tid,
                display_name=ch["title"],
                tile_kind="opus_item",
                visibility_scope=parent_tile.get("visibility_scope", "public"),
                owner_namespace=parent_tile.get("owner_namespace", "foundups_core"),
                parent_tile_id=parent_tid,
                state=parent_tile.get("lifecycle", {}).get("state", "GREEN"),
                dag_edges={"collection_refs": [parent_tid]},
                action_target={
                    "repo_path": doc_path,
                    "primary_url": blob_url,
                },
                evidence_status=parent_tile.get("evidence_status", "verified_repo_or_receipt"),
                search_keywords=[ch["title"], parent_title, f"chapter {idx}"],
                author_aliases=list(parent_tile.get("author_aliases", [])),
                metadata={
                    "chapter_index": idx,
                    "chapter_count": total,
                    "start_line": s_line,
                    "end_line": e_line,
                    "parent_document_title": parent_title,
                    "chapter_excerpt": ch["chapter_excerpt"],
                    "source_inspection": {
                        "repository": "FOUNDUPS/Foundups-Agent",
                        "repository_slug": "FOUNDUPS/Foundups-Agent",
                        "revision": source_rev,
                        "source_revision": source_rev,
                        "path": doc_path,
                        "repo_path": doc_path,
                        "line_start": s_line,
                        "line_end": e_line,
                        "availability_status": "VERIFIED_AT_CENSUS_BASELINE_REVISION",
                        "url": blob_url,
                        "source_url": blob_url,
                    },
                },
            )


def _enrich_canonical_foundup_metadata(tiles: Dict[str, Dict[str, Any]]) -> None:
    """Attach canonical ``foundup_kind`` and ``canonical_element_modes`` metadata."""
    for tid, tile in tiles.items():
        tkind = tile.get("tile_kind")
        meta = tile.setdefault("metadata", {})

        if "foundup_kind" not in meta:
            if tkind in {"opus_series", "opus_item"}:
                meta["foundup_kind"] = "card"
            elif (
                tid == ROOT_TILE_ID
                or tid in _APPLICATION_MOCKUP_IDS
                or tid in _APPLICATION_SYS_IDS
                or tkind in {
                    "community_fractal",
                    "foundup_venture",
                    "market_override",
                    "wikitube_stream",
                }
            ):
                meta["foundup_kind"] = "application"
            else:
                meta["foundup_kind"] = "tool"
        if tkind in {"opus_series", "opus_item"} or meta.get("foundup_kind") == "card":
            meta.setdefault("canonical_element_kind", "card")

        if "canonical_element_modes" not in meta:
            low_tid = tid.lower()
            if tid == ROOT_TILE_ID:
                modes = ["video", "pictures", "cards"]
            elif tkind == "wikitube_stream" or tid.startswith("tile:stream:"):
                modes = ["video", "podcast", "cards"] if "antifafm" in low_tid else ["video", "cards"]
            elif tkind in {"community_fractal", "foundup_venture"}:
                if "antifafm" in low_tid:
                    modes = ["video", "podcast", "cards"]
                else:
                    modes = ["video", "pictures", "cards"]
            elif tkind in {"market_override", "mockup_cube"}:
                modes = ["pictures", "cards"]
            elif tkind in {"opus_series", "opus_item"}:
                modes = ["cards"]
            elif tid == "tile:engine:autopost":
                modes = ["video", "pictures", "cards"]
            else:
                modes = ["cards"]
            meta["canonical_element_modes"] = [
                m for m in _CANONICAL_ELEMENT_MODES_ORDER if m in modes
            ]


def build_repo_fractal_tile_graph(
    repo_root: Path,
    *,
    generated_at_utc: Optional[str] = None,
) -> Dict[str, Any]:
    """Deterministically build the full ``012_architect`` graph from tracked files under *repo_root*.

    Has zero dependency on gitignored ``temp/`` artifacts and never reads private
    metadata-only manuscript bodies.
    """
    repo_root = Path(repo_root).resolve()
    blob_cache = _load_git_blobs(repo_root)
    tracked_files = sorted(blob_cache.keys()) if blob_cache else _collect_tracked_files(repo_root)
    tracked_set = set(tracked_files)

    git_revision = "unknown"
    if (repo_root / ".git").exists():
        try:
            proc = subprocess.run(
                ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                check=True,
            )
            git_revision = proc.stdout.strip() or "unknown"
        except Exception:
            pass

    tiles: Dict[str, Dict[str, Any]] = {}
    tiles[ROOT_TILE_ID] = make_tile(
        tile_id=ROOT_TILE_ID,
        display_name="PlayFoundups Mall",
        tile_kind="system_cube",
        visibility_scope="public",
        owner_namespace="foundups_core",
        parent_tile_id=None,
        state="GREEN",
        lifecycle_extra={"has_entrypoint": True, "contracts_present": ["README.md", "INTERFACE.md"]},
        action_target={"primary_url": "https://play.foundups.com/", "repo_path": "public/member/index.html"},
        search_keywords=["PlayFoundups", "Mall", "p.fMALL", "FoundUps", "root"],
        author_aliases=["FoundUps", "012", "UnDaoDu"],
    )

    sections = [
        ("tile:sys:core_systems", "Core Systems & Engines", "system_cube", "public", "foundups_core", "GREEN"),
        ("tile:tools:root", "Tools", "system_cube", "public", "foundups_core", "GREEN"),
        ("tile:pubs:root", "Pubs (Opus, Papers, JHR & Series)", "opus_series", "public", "foundups_core", "GREEN"),
        ("tile:investor:root", "Investor & Licensable Portfolio", "foundup_venture", "public", "foundups_core", "AMBER"),
        ("tile:market:japan_akiya", "FoundUp House Market — Japan Akiya (空き家)", "market_override", "public", "foundups_core", "AMBER"),
        ("tile:stream:root", "WikiTube Continuous Stream", "wikitube_stream", "public", "foundups_core", "GREEN"),
        ("tile:mockups:root", "Mockups, Canvases & Archive Snapshots", "mockup_cube", "public", "foundups_core", "AMBER"),
        ("tile:modules:root", "Repository Architecture & Module Domains", "system_cube", "public", "foundups_core", "GREEN"),
    ]
    for tid, name, kind, vis, ns, st in sections:
        tiles[tid] = make_tile(
            tile_id=tid,
            display_name=name,
            tile_kind=kind,
            visibility_scope=vis,
            owner_namespace=ns,
            parent_tile_id=ROOT_TILE_ID,
            state=st,
            search_keywords=[name],
        )

    # 1. Code modules + domain groups + core systems
    module_nodes, _domains = _scan_code_modules(repo_root, tracked_files, tracked_set, blob_cache=blob_cache)
    core_sys_ids = {
        "tile:sys:simulator",
        "tile:mod:foundups.pfmall",
        "tile:sys:holo_index",
        "tile:sys:extensions_reddog",
        "tile:mod:foundups.agent_market",
        "tile:mod:ai_intelligence.ai_gateway",
        "tile:mod:infrastructure.shared_utilities",
        "tile:mod:infrastructure.wre_core",
        "tile:mod:infrastructure.mcp_manager",
        "tile:mod:communication.moltbot_bridge",
        "tile:mod:foundups.agent",
    }
    needed_domains = sorted({
        m["domain"]
        for m in module_nodes
        if not (m["tile_id"] in core_sys_ids and not m["is_red_orphan_candidate"])
    })
    domain_tiles: Dict[str, str] = {}
    for dom in needed_domains:
        dtid = f"tile:domain:{dom}"
        domain_tiles[dom] = dtid
        tiles[dtid] = make_tile(
            tile_id=dtid,
            display_name=f"Domain: {dom}",
            tile_kind="system_cube",
            visibility_scope="public",
            owner_namespace="foundups_core",
            parent_tile_id="tile:modules:root",
            state="AMBER",
            action_target={
                "primary_url": f"https://play.foundups.com/#{dtid}",
                "repo_path": f"modules/{dom}",
            },
            search_keywords=["domain", dom, f"modules/{dom}"],
        )
    for m in module_nodes:
        tid = m["tile_id"]
        is_red = bool(m["is_red_orphan_candidate"])
        is_sys = tid in core_sys_ids and not is_red
        if is_red:
            st = "RED"
            vis = "principal_only"
        elif tid == "tile:mod:foundups.pfmall":
            st = "GREEN"
            vis = "public"
        elif tid == "tile:sys:simulator":
            st = "AMBER"
            vis = "public"
        elif m["has_tests"] and "INTERFACE.md" in m["contracts_present"] and (
            m["runtime_inbound_imports"] >= 1
            or m["coupling_channels"]["web_http_routes"]
            or m["coupling_channels"]["cli_entrypoints"]
        ):
            st = "GREEN" if not m["open_sockets"] else "AMBER"
            vis = "public"
        else:
            st = "AMBER" if (m["code_file_count"] > 0 or m["contracts_present"]) else "BLUE"
            vis = "public"

        display_name = (
            "FoundUps Simulator" if tid == "tile:sys:simulator"
            else ("p.fMALL Shell & API" if tid == "tile:mod:foundups.pfmall" else m["module_name"])
        )
        drift_flags = []
        if is_red:
            drift_flags.append("6_channel_zero_coupling_candidate")
        if tid == "tile:sys:simulator":
            drift_flags.append("open_socket:export_adapter")

        rescue = dict(m["rescue_axes"])
        rescue["next_action"] = (
            "Wire SimulatorStateProvider export_adapter socket to member_catalog_export.py and pfmall/api.py"
            if tid == "tile:sys:simulator"
            else ("Inspect zero-coupling status before archive or deletion" if is_red else "Complete INTERFACE.md/tests or wire declared socket")
        )

        tiles[tid] = make_tile(
            tile_id=tid,
            display_name=display_name,
            tile_kind="system_cube" if is_sys else "code_module",
            visibility_scope=vis,
            owner_namespace="foundups_core",
            parent_tile_id="tile:sys:core_systems" if is_sys else domain_tiles[m["domain"]],
            state=st,
            dag_edges={
                "imports_tiles": m["outbound_module_imports"],
                "used_by_foundups": m["used_by_foundups"],
                "reusable_candidates": ["tile:mod:communication.moltbot_bridge"] if tid == "tile:sys:simulator" else [],
            },
            lifecycle_extra={
                "inbound_ast_imports": m["runtime_inbound_imports"],
                "has_entrypoint": m["has_entrypoint"],
                "contracts_present": m["contracts_present"],
                "drift_flags": drift_flags,
            },
            wsp15_canonical=m["wsp15_canonical"],
            rescue_axes=rescue,
            action_target={
                "primary_url": f"https://play.foundups.com/#{tid}",
                "repo_path": m["repo_path"],
                "interface_doc": f"{m['repo_path']}/INTERFACE.md" if "INTERFACE.md" in m["contracts_present"] else None,
            },
            search_keywords=[m["module_name"], m["domain"], m["repo_path"]] + (["simulator", "CABR"] if tid == "tile:sys:simulator" else []),
            metadata={
                "domain": m["domain"],
                "module_name": m["module_name"],
                "test_file_count": m["test_file_count"],
                "code_file_count": m["code_file_count"],
                "test_only_references_count": m["test_only_references_count"],
                "coupling_channels": m["coupling_channels"],
                "open_sockets": m["open_sockets"],
            },
        )

    _add_simulator_subcubes(tiles, tracked_files)
    _add_mode1_pubs(tiles, repo_root, tracked_set, blob_cache=blob_cache)
    _add_mode3_investor(tiles, repo_root, blob_cache=blob_cache)
    _add_mode2_hpc(tiles, repo_root, blob_cache=blob_cache)
    _add_mode4_akiya(tiles, repo_root, blob_cache=blob_cache)
    _add_mode5_wikitube(tiles, repo_root, blob_cache=blob_cache)
    _add_mockups(tiles, tracked_files, tracked_set)

    s1_manifest = _read_json_safe(
        repo_root,
        "modules/foundups/pfmall/sprint1_registry_benchmark_manifest.json",
        {},
        blob_cache=blob_cache,
    )
    if s1_manifest:
        _apply_sprint1_registry_and_duplicates(tiles, s1_manifest)
        _add_tools_and_benchmark(tiles, s1_manifest)
        _attach_registry_verification(tiles, s1_manifest)

    # Populate deterministic source_inspection on every tile
    pins_cfg = (s1_manifest.get("source_pins") if isinstance(s1_manifest, dict) else None) or {}
    census_rev = pins_cfg.get("audited_main_revision") or "7432d31e5a68544d2bbab6715f02f64b0b5b6f85"
    feature_intro_rev = pins_cfg.get("mall_feature_base_revision") or "e221854cba2bdfd6c043b10ac192f33b3d78f439"
    lego_rev = pins_cfg.get("lego_slice1_revision") or "2c936f78c2f17ffe59a6c91cc3e37146a15372ad"
    gitlink_rev = pins_cfg.get("vendor_hermes_gitlink_sha1") or "d1d425e9d0e0e37bc0855fe5a4142bac86a73b0d"

    _add_document_chapter_tiles(tiles, repo_root, census_rev, blob_cache=blob_cache)
    _enrich_canonical_foundup_metadata(tiles)
    census_dirs = set((s1_manifest.get("census_directory_prefixes") if isinstance(s1_manifest, dict) else None) or [])
    census_files = set((s1_manifest.get("census_file_paths_sample_or_anchors") if isinstance(s1_manifest, dict) else None) or [])
    census_tree_files, census_tree_dirs = _load_census_git_tree(repo_root, census_rev)
    gitmodule_urls = _parse_gitmodules_urls(repo_root, blob_cache=blob_cache)

    tracked_dir_prefixes: Set[str] = set()
    for tf_path in tracked_files:
        parts = tf_path.split("/")
        for depth in range(1, len(parts)):
            tracked_dir_prefixes.add("/".join(parts[:depth]))

    active_census_files = census_tree_files if census_tree_files is not None else (census_files or tracked_set)
    active_census_dirs = census_tree_dirs if census_tree_dirs is not None else (census_dirs or tracked_dir_prefixes)

    for tid, tile in tiles.items():
        meta = tile.setdefault("metadata", {})
        if "source_inspection" in meta:
            continue
        at = tile.get("action_target") or {}
        rpath = at.get("repo_path")
        rv = meta.get("registry_verification") or {}
        ext_ver = meta.get("external_repo_verification") or {}
        if meta.get("metadata_only") is True or (rpath and rpath in PRIVATE_METADATA_ONLY_PATHS):
            meta["source_inspection"] = {
                "repository_slug": "FOUNDUPS/Foundups-Agent",
                "source_revision": census_rev,
                "repo_path": rpath,
                "availability_status": "METADATA_ONLY_PRIVATE",
                "source_url": None,
            }
        elif rpath == "vendor/hermes-agent":
            hermes_base_url = gitmodule_urls.get("vendor/hermes-agent") or "https://github.com/FOUNDUPS/hermes-agent"
            hermes_tree_url = f"{hermes_base_url}/tree/{gitlink_rev}"
            if str(at.get("primary_url") or "").startswith("https://play.foundups.com/#"):
                at["primary_url"] = hermes_tree_url
            meta["source_inspection"] = {
                "repository_slug": "FOUNDUPS/Foundups-Agent -> gitlink vendor/hermes-agent",
                "source_revision": gitlink_rev,
                "repo_path": rpath,
                "availability_status": "SUBMODULE_GITLINK_BOUNDARY",
                "source_url": hermes_tree_url,
            }
        elif rpath == "modules/ai_intelligence/ai_gateway/src/lego_scaffolding_benchmark_protocol.py":
            meta["source_inspection"] = {
                "repository_slug": "FOUNDUPS/Foundups-Agent",
                "source_revision": lego_rev,
                "repo_path": rpath,
                "availability_status": "VERIFIED_AT_SIBLING_WORKTREE_REVISION",
                "source_url": None,
            }
        elif ext_ver and ext_ver.get("repository"):
            ext_repo = str(ext_ver["repository"])
            ext_sha = ext_ver.get("head_sha")
            ext_src_url = f"https://github.com/{ext_repo}/tree/{ext_sha}" if ext_sha else f"https://github.com/{ext_repo}"
            si_payload: Dict[str, Any] = {
                "repository_slug": ext_repo,
                "source_revision": ext_sha,
                "repo_path": rpath,
                "availability_status": "LOCAL_EXTERNAL_REPO_PINNED",
                "source_url": ext_src_url,
            }
            if meta.get("in_repo_handoff_path"):
                si_payload["in_repo_handoff_path"] = meta["in_repo_handoff_path"]
            meta["source_inspection"] = si_payload
        elif meta.get("repository") and meta.get("head_sha"):
            ext_repo = str(meta["repository"])
            ext_sha = str(meta["head_sha"])
            ext_src_url = f"https://github.com/{ext_repo}/tree/{ext_sha}"
            si_payload = {
                "repository_slug": ext_repo,
                "source_revision": ext_sha,
                "repo_path": rpath,
                "availability_status": "LOCAL_EXTERNAL_REPO_PINNED",
                "source_url": ext_src_url,
            }
            if meta.get("in_repo_handoff_path"):
                si_payload["in_repo_handoff_path"] = meta["in_repo_handoff_path"]
            meta["source_inspection"] = si_payload
        elif rpath:
            raw_path, has_hash, frag_tail = str(rpath).partition("#")
            clean_rpath = raw_path.strip().rstrip("/")
            url_fragment = f"#{frag_tail}" if has_hash and frag_tail else str(at.get("url_fragment") or meta.get("url_fragment") or "")
            if url_fragment and not url_fragment.startswith("#"):
                url_fragment = f"#{url_fragment}"
            in_census_file = clean_rpath in active_census_files
            in_census_dir = clean_rpath in active_census_dirs
            if in_census_file or in_census_dir:
                kind_seg = "blob" if in_census_file and not in_census_dir else "tree"
                meta["source_inspection"] = {
                    "repository_slug": "FOUNDUPS/Foundups-Agent",
                    "source_revision": census_rev,
                    "repo_path": clean_rpath,
                    "availability_status": "VERIFIED_AT_CENSUS_BASELINE_REVISION",
                    "source_url": f"https://github.com/FOUNDUPS/Foundups-Agent/{kind_seg}/{census_rev}/{clean_rpath}{url_fragment}",
                }
            elif clean_rpath in tracked_set or clean_rpath in tracked_dir_prefixes:
                meta["source_inspection"] = {
                    "repository_slug": "FOUNDUPS/Foundups-Agent",
                    "source_revision": git_revision if git_revision != "unknown" else feature_intro_rev,
                    "repo_path": clean_rpath,
                    "availability_status": "VERIFIED_AT_TRACKED_HEAD_REVISION",
                    "source_url": None,
                }
            elif (repo_root / clean_rpath).exists():
                meta["source_inspection"] = {
                    "repository_slug": "FOUNDUPS/Foundups-Agent",
                    "source_revision": feature_intro_rev,
                    "repo_path": clean_rpath,
                    "availability_status": "VERIFIED_AT_MALL_FEATURE_REVISION_LOCAL",
                    "source_url": None,
                }
            else:
                meta["source_inspection"] = {
                    "repository_slug": rv.get("repository_slug") or "FOUNDUPS/Foundups-Agent",
                    "source_revision": rv.get("revision") or census_rev,
                    "repo_path": clean_rpath,
                    "availability_status": "UNTRACKED_OR_EXTERNAL_LOCAL_BUNDLE",
                    "source_url": None,
                }
        elif tid.startswith("tile:receipt:"):
            meta["source_inspection"] = {
                "repository_slug": "FOUNDUPS/Foundups-Agent",
                "source_revision": census_rev,
                "repo_path": None,
                "availability_status": "CRYPTOGRAPHIC_RECEIPT_VERIFIED",
                "source_url": None,
            }
        else:
            purl = at.get("primary_url") or at.get("external_url")
            is_ext_http = isinstance(purl, str) and purl.startswith("http") and "play.foundups.com/#" not in purl
            meta["source_inspection"] = {
                "repository_slug": rv.get("repository_slug") or "FOUNDUPS/Foundups-Agent",
                "source_revision": rv.get("revision") or census_rev,
                "repo_path": None,
                "availability_status": "EXTERNAL_PUBLICATION_OR_MEDIA_URL" if is_ext_http else "VIRTUAL_NAVIGATION_CONTAINER",
                "source_url": purl if is_ext_http else None,
            }

    # Populate children_tile_ids strictly from parent_tile_id
    for tid in sorted(tiles):
        pid = tiles[tid]["parent_tile_id"]
        if pid is not None and pid in tiles:
            if tid not in tiles[pid]["children_tile_ids"]:
                tiles[pid]["children_tile_ids"].append(tid)

    # Derive container operational states bottom-up from children (never hardcode GREEN on root/sections)
    derived_container_ids: Set[str] = {
        ROOT_TILE_ID,
        "tile:sys:core_systems",
        "tile:tools:root",
        "tile:tools:benchmark",
        "tile:receipt:benchmark_ledger",
        "tile:pubs:root",
        "tile:investor:root",
        "tile:market:japan_akiya",
        "tile:stream:root",
        "tile:mockups:root",
        "tile:modules:root",
        "tile:sys:external_and_archives",
        "tile:sys:knowledge_and_governance",
        "tile:sys:web_and_cloud_surfaces",
        "tile:space:hpc",
    } | {tid for tid in tiles if tid.startswith("tile:domain:")}
    derived_visited: Set[str] = set()

    def _derive_container_state(cid: str) -> str:
        if cid in derived_visited:
            return tiles[cid]["lifecycle"]["state"]
        derived_visited.add(cid)
        child_ids = tiles[cid].get("children_tile_ids") or []
        if not child_ids:
            return tiles[cid]["lifecycle"]["state"]
        child_states: List[str] = []
        for ch_id in child_ids:
            if ch_id in derived_container_ids and ch_id in tiles:
                child_states.append(_derive_container_state(ch_id))
            elif ch_id in tiles:
                child_states.append(tiles[ch_id]["lifecycle"]["state"])
        if not child_states:
            return tiles[cid]["lifecycle"]["state"]
        new_state = "GREEN" if all(s == "GREEN" for s in child_states) else "AMBER"
        tiles[cid]["lifecycle"]["state"] = new_state
        tiles[cid]["lifecycle"]["state_label"] = state_label(new_state)
        return new_state

    for c_tid in sorted(derived_container_ids):
        if c_tid in tiles:
            _derive_container_state(c_tid)

    # Prune any unresolved dag_edges targets (e.g. partial repo fixtures in tests)
    for tid, tile in tiles.items():
        edges = tile["dag_edges"]
        for efield in DAG_TILE_EDGE_FIELDS:
            cleaned: List[str] = []
            for target_id in edges.get(efield, []):
                if target_id != tid and target_id in tiles and target_id not in cleaned:
                    cleaned.append(target_id)
            edges[efield] = cleaned

    ts = generated_at_utc or datetime.now(timezone.utc).isoformat()
    arch_etag = compute_tiles_etag(tiles)
    indices = build_graph_indices(tiles)
    architect_graph: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_at_utc": ts,
        "git_revision": git_revision,
        "source_revisions": {
            "census_source_revision": census_rev,
            "mall_feature_code_revision": git_revision,
            "scanner_projector_revision": git_revision,
            "lego_slice_revision": lego_rev,
            "vendor_hermes_gitlink_sha1": gitlink_rev,
        },
        "graph_etag": arch_etag,
        "public_graph_etag": "",
        "scope": "012_architect",
        "root_tile_id": ROOT_TILE_ID,
        "counts": indices["counts"],
        "links": indices["links"],
        "search_index": indices["search_index"],
        "tiles": tiles,
    }
    pub_proj = project_public_tile_graph(architect_graph)
    architect_graph["public_graph_etag"] = pub_proj["public_graph_etag"]
    return architect_graph
