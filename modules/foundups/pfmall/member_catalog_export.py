#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Member Mall catalog exporter — generates public/member/mall-catalog.json
from canonical p.fMALL manifest/tile truth + presentation overrides.

Usage:
    python -m modules.foundups.pfmall.member_catalog_export

This replaces hand-maintained catalog duplication with a single
generated artifact. The Firebase Mall remains static-hostable;
it just consumes a generated file instead of a hand-edited one.
"""

import argparse
import copy
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

from modules.foundups.pfmall.api import get_default_shell, list_foundups, reset_default_shell
from modules.foundups.pfmall.fractal_tile_graph import (
    PRIVATE_METADATA_ONLY_PATHS,
    _FORBIDDEN_LEAK_RE,
    _PUBLIC_FORBIDDEN_SUBSTRINGS,
    build_repo_fractal_tile_graph,
    project_public_tile_graph,
    validate_tile_graph,
)
from modules.foundups.pfmall.member_presentation import get_presentation

logger = logging.getLogger("pfmall_export")

_REPO_ROOT = Path(__file__).resolve().parents[3]
_MODULE_PROJECTIONS_DIR = Path(__file__).resolve().parent / "projections"
DEFAULT_OUTPUT_PATH = _REPO_ROOT / "public" / "member" / "mall-catalog.json"
DEFAULT_FRACTAL_GRAPH_OUTPUT_PATH = _MODULE_PROJECTIONS_DIR / "fractal_tile_graph.public.json"
DEFAULT_FRACTAL_SOURCE_FILES_OUTPUT_PATH = _MODULE_PROJECTIONS_DIR / "fractal_source_files.public.json"
SOURCE_FILE_INDEX_SCHEMA_VERSION = "fractal_source_file_index.v1"


def _assert_outside_public_root(
    output_path: Path,
    label: str,
    repo_root: Optional[Path] = None,
) -> Path:
    """Resolve *output_path* and refuse any destination inside static ``public/``."""
    resolved_out = Path(output_path).resolve()
    roots = [(_REPO_ROOT / "public").resolve()]
    if repo_root is not None:
        candidate = Path(repo_root).resolve() / "public"
        if candidate not in roots:
            roots.append(candidate)
    for public_root in roots:
        if resolved_out == public_root or public_root in resolved_out.parents:
            raise ValueError(f"Refusing to write {label} inside public web root: {resolved_out}")
    return resolved_out

# Explicit owner_node_id -> tile_id bridge for census nodes as defense-in-depth
# alongside tile metadata.registry_verification.registry_id.
_OWNER_NODE_TILE_FALLBACKS: Dict[str, str] = {
    "ext_repo:foundups.github.io": "tile:mockup:foundups_github_io",
    "harness:ai_gateway_lego_benchmark_2c936f78c": "tile:harness:lego_scaffolding_protocol",
    "harness:ai_gateway_model_benchmarks": "tile:harness:model_combination_benchmark",
}

# Fields from the tile that the member Mall consumes.
_TILE_FIELDS = [
    "foundup_id",
    "name",
    "tagline",
    "description",
    "category",
    "tier",
    "lifecycle_stage",
    "launch_readiness",
    "token_symbol",
    "routing_prefix",
]


def build_mall_catalog(shell=None) -> List[Dict[str, Any]]:
    """Build the member Mall catalog from canonical pfmall truth.

    Returns a list of dicts matching the shape consumed by
    public/member/index.html: tile fields + presentation overrides.
    """
    tiles = list_foundups(shell=shell)
    catalog = []
    for tile in tiles:
        entry: Dict[str, Any] = {}
        for field in _TILE_FIELDS:
            entry[field] = tile.get(field, "")
        # Merge presentation overrides
        presentation = get_presentation(tile["foundup_id"])
        entry.update(presentation)
        catalog.append(entry)
    return catalog


def export_mall_catalog(
    output_path: Path = DEFAULT_OUTPUT_PATH,
    shell=None,
) -> Path:
    """Generate and write mall-catalog.json.

    Args:
        output_path: Where to write the JSON file.
        shell: Optional PfmallShell instance (uses default if None).

    Returns:
        Path to the written file.
    """
    catalog = build_mall_catalog(shell=shell)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)
        f.write("\n")
    logger.info(
        "[PFMALL-EXPORT] Wrote %d entries to %s",
        len(catalog),
        output_path,
    )
    return output_path


def export_fractal_tile_graph(
    output_path: Path = DEFAULT_FRACTAL_GRAPH_OUTPUT_PATH,
    store: Optional[Any] = None,
    repo_root: Path = _REPO_ROOT,
    compact: bool = True,
) -> Path:
    """Export the leak-free ``public_mall`` Fractal Tile Graph projection.

    Safety guard: refuses destinations inside ``public/`` static hosting root.

    Args:
        output_path: Destination JSON path (defaults to ``modules/foundups/pfmall/projections/fractal_tile_graph.public.json``).
        store: Optional ``TileGraphStore`` providing live accepted edits.
        repo_root: Repository root used when building directly from tracked files.
        compact: Emit single-line compact JSON instead of 2-space indented JSON.

    Returns:
        Path to the written public projection JSON file.
    """
    resolved_out = _assert_outside_public_root(
        output_path, "public_mall fractal graph", repo_root=repo_root
    )
    if store is not None:
        public_graph = store.get_public_graph()
    else:
        architect_graph = build_repo_fractal_tile_graph(repo_root)
        public_graph = project_public_tile_graph(architect_graph)

    errors = validate_tile_graph(public_graph)
    if errors:
        raise ValueError(f"Public fractal tile graph failed validation: {errors[:5]}")

    resolved_out.parent.mkdir(parents=True, exist_ok=True)
    with open(resolved_out, "w", encoding="utf-8") as f:
        if compact:
            json.dump(public_graph, f, separators=(",", ":"), ensure_ascii=False)
        else:
            json.dump(public_graph, f, indent=2, ensure_ascii=False)
        f.write("\n")
    logger.info(
        "[PFMALL-EXPORT] Wrote %d public tiles (etag=%s) to %s",
        public_graph.get("counts", {}).get("total_tiles", 0),
        public_graph.get("public_graph_etag", ""),
        resolved_out,
    )
    return resolved_out


def export_architect_tile_graph(
    output_path: Path,
    store: Optional[Any] = None,
    repo_root: Path = _REPO_ROOT,
) -> Path:
    """Export the full ``012_architect`` Fractal Tile Graph projection to *output_path*.

    Safety guard: refuses destinations inside ``public/`` static hosting root.
    """
    resolved_out = _assert_outside_public_root(
        output_path, "012_architect graph", repo_root=repo_root
    )

    if store is not None:
        architect_graph = store.get_architect_graph()
    else:
        architect_graph = build_repo_fractal_tile_graph(repo_root)

    errors = validate_tile_graph(architect_graph)
    if errors:
        raise ValueError(f"Architect fractal tile graph failed validation: {errors[:5]}")

    resolved_out.parent.mkdir(parents=True, exist_ok=True)
    with open(resolved_out, "w", encoding="utf-8") as f:
        json.dump(architect_graph, f, indent=2, ensure_ascii=False)
        f.write("\n")
    logger.info(
        "[PFMALL-EXPORT] Wrote %d architect tiles (etag=%s) to %s",
        architect_graph.get("counts", {}).get("total_tiles", 0),
        architect_graph.get("graph_etag", ""),
        resolved_out,
    )
    return resolved_out


def build_fractal_source_file_index(
    graph: Dict[str, Any],
    path_accounting_doc: Dict[str, Any],
    *,
    scope: Optional[str] = None,
) -> Dict[str, Any]:
    """Build a scope-isolated, revision-pinned census file index for Fractal Mall tiles.

    Maps each tracked repository path in ``path_accounting_doc`` to its owning
    tile in ``graph`` via ``registry_verification.registry_id`` (preserving
    component-level tile granularity while exposing file-level inspection inside
    each tile's source drawer).

    Gated envelope rule:
      - ``public_mall`` is strictly for the gated member Mall envelope (never
        public unauthenticated HPC video surfaces) and omits all ``RED``,
        ``principal_only``, metadata-only private manuscripts, and forbidden
        restricted paths (e.g. ``pfmall_state_provider.py``).
      - ``012_architect`` includes principal-only tiles and marks private
        manuscripts under ``metadata_only_files`` with no clickable source URL.
    """
    graph_scope = graph.get("scope")
    resolved_scope = scope or graph_scope
    if resolved_scope not in ("public_mall", "012_architect"):
        raise ValueError(f"Unsupported fractal source file index scope: {resolved_scope!r}")
    if graph_scope != resolved_scope:
        raise ValueError(
            f"Scope mismatch: graph.scope={graph_scope!r} does not match requested scope={resolved_scope!r}"
        )

    tiles_map: Dict[str, Dict[str, Any]] = graph.get("tiles", {})
    reg_id_to_tile_id: Dict[str, str] = {}
    tile_id_to_reg_id: Dict[str, str] = {}

    for tid, tile in tiles_map.items():
        if resolved_scope == "public_mall":
            if tile.get("visibility_scope") != "public":
                continue
            if (tile.get("lifecycle") or {}).get("state") == "RED":
                continue
        rv = (tile.get("metadata") or {}).get("registry_verification") or {}
        reg_id = rv.get("registry_id")
        if isinstance(reg_id, str) and reg_id:
            reg_id_to_tile_id[reg_id] = tid
            tile_id_to_reg_id[tid] = reg_id

    for owner_node_id, target_tid in _OWNER_NODE_TILE_FALLBACKS.items():
        tile = tiles_map.get(target_tid)
        if not tile:
            continue
        if resolved_scope == "public_mall":
            if tile.get("visibility_scope") != "public" or (tile.get("lifecycle") or {}).get("state") == "RED":
                continue
        reg_id_to_tile_id.setdefault(owner_node_id, target_tid)
        tile_id_to_reg_id.setdefault(target_tid, owner_node_id)

    files_by_tile: Dict[str, List[str]] = {}
    meta_only_by_tile: Dict[str, List[str]] = {}
    gitlinks_by_tile: Dict[str, List[Dict[str, str]]] = {}

    for row in path_accounting_doc.get("rows", []):
        if row.get("disposition") != "MAPPED":
            continue
        owner_node_id = row.get("owner_node_id")
        if not owner_node_id:
            continue
        tid = reg_id_to_tile_id.get(owner_node_id)
        if not tid:
            continue
        rel_path = str(row.get("path", "")).replace("\\", "/").lstrip("/")
        if not rel_path:
            continue

        if rel_path in PRIVATE_METADATA_ONLY_PATHS:
            if resolved_scope == "012_architect":
                meta_only_by_tile.setdefault(tid, []).append(rel_path)
            continue

        if resolved_scope == "public_mall":
            low = rel_path.lower()
            if any(forbidden.lower() in low for forbidden in _PUBLIC_FORBIDDEN_SUBSTRINGS):
                continue

        if row.get("git_object_type") == "commit" or row.get("git_mode") == "160000":
            gitlinks_by_tile.setdefault(tid, []).append(
                {
                    "path": rel_path,
                    "commit_sha": str(row.get("git_object_sha1") or ""),
                }
            )
            continue

        files_by_tile.setdefault(tid, []).append(rel_path)

    all_owning_tids = sorted(
        set(files_by_tile.keys()) | set(meta_only_by_tile.keys()) | set(gitlinks_by_tile.keys())
    )
    tiles_out: Dict[str, Dict[str, Any]] = {}
    total_mapped_files = 0
    total_metadata_only = 0
    total_gitlinks = 0

    for tid in all_owning_tids:
        reg_id = tile_id_to_reg_id.get(tid, "")
        sorted_files = sorted(set(files_by_tile.get(tid, [])))
        sorted_meta_only = sorted(set(meta_only_by_tile.get(tid, [])))
        sorted_gitlinks = sorted(gitlinks_by_tile.get(tid, []), key=lambda item: item["path"])

        path_prefix = ""
        if (
            reg_id
            and ":" not in reg_id
            and sorted_files
            and all(p.startswith(reg_id.rstrip("/") + "/") for p in sorted_files)
        ):
            path_prefix = reg_id.rstrip("/") + "/"
            compact_files = [p[len(path_prefix) :] for p in sorted_files]
        else:
            compact_files = sorted_files

        entry: Dict[str, Any] = {
            "registry_id": reg_id,
            "path_prefix": path_prefix,
            "file_count": len(compact_files),
            "files": compact_files,
        }
        if sorted_meta_only:
            entry["metadata_only_files"] = sorted_meta_only
        if sorted_gitlinks:
            entry["gitlinks"] = sorted_gitlinks

        tiles_out[tid] = entry
        total_mapped_files += len(compact_files)
        total_metadata_only += len(sorted_meta_only)
        total_gitlinks += len(sorted_gitlinks)

    census_rev = str(path_accounting_doc.get("source_revision") or "")
    git_rev = str(graph.get("git_revision") or "").strip()
    graph_src_revs = graph.get("source_revisions")
    src_revs: Dict[str, Any] = copy.deepcopy(dict(graph_src_revs)) if isinstance(graph_src_revs, Mapping) else {}
    if census_rev:
        src_revs["census_source_revision"] = census_rev
    if git_rev:
        src_revs.setdefault("mall_feature_code_revision", git_rev)
        src_revs.setdefault("scanner_projector_revision", git_rev)

    out_doc: Dict[str, Any] = {
        "schema_version": SOURCE_FILE_INDEX_SCHEMA_VERSION,
        "scope": resolved_scope,
        "access_envelope": "gated_member_mall" if resolved_scope == "public_mall" else "012_architect_local",
        "public_hpc_surface_allowed": False,
        "repository_slug": str(path_accounting_doc.get("repository_slug") or "FOUNDUPS/Foundups-Agent"),
        "source_revision": census_rev,
    }
    if git_rev:
        out_doc["git_revision"] = git_rev
    if src_revs:
        out_doc["source_revisions"] = src_revs
    out_doc["counts"] = {
        "owning_tiles": len(tiles_out),
        "mapped_files": total_mapped_files,
        "metadata_only_files": total_metadata_only,
        "gitlinks": total_gitlinks,
    }
    out_doc["tiles"] = tiles_out
    return out_doc


def validate_source_file_index(
    index_doc: Dict[str, Any],
    graph: Dict[str, Any],
) -> List[str]:
    """Validate a fractal source file index for scope isolation and WSP 71 hygiene."""
    errors: List[str] = []
    if index_doc.get("schema_version") != SOURCE_FILE_INDEX_SCHEMA_VERSION:
        errors.append(f"Invalid schema_version: {index_doc.get('schema_version')!r}")
    scope = index_doc.get("scope")
    if scope not in ("public_mall", "012_architect"):
        errors.append(f"Invalid scope: {scope!r}")
    if scope != graph.get("scope"):
        errors.append(f"Scope mismatch with graph: index={scope!r} graph={graph.get('scope')!r}")
    if index_doc.get("public_hpc_surface_allowed") is not False:
        errors.append("Gated envelope violation: public_hpc_surface_allowed must be false")
    rev = str(index_doc.get("source_revision") or "")
    if len(rev) != 40 or any(ch not in "0123456789abcdef" for ch in rev.lower()):
        errors.append(f"source_revision must be a 40-char commit SHA, got {rev!r}")
    if "git_revision" in index_doc:
        git_rev = index_doc.get("git_revision")
        if not isinstance(git_rev, str) or not git_rev.strip():
            errors.append(f"git_revision must be a non-empty string, got {git_rev!r}")
    if "source_revisions" in index_doc:
        src_revs = index_doc.get("source_revisions")
        if not isinstance(src_revs, Mapping):
            errors.append("source_revisions must be a mapping when present")
        elif src_revs.get("census_source_revision") != rev:
            errors.append(
                f"source_revisions.census_source_revision={src_revs.get('census_source_revision')!r} "
                f"must match source_revision={rev!r}"
            )

    graph_tiles = graph.get("tiles", {})
    index_tiles = index_doc.get("tiles", {})
    if not isinstance(index_tiles, dict):
        errors.append("tiles must be a dict")
        return errors

    for tid, entry in index_tiles.items():
        tile = graph_tiles.get(tid)
        if tile is None:
            errors.append(f"Owning tile missing from graph: {tid}")
            continue
        if scope == "public_mall":
            if tile.get("visibility_scope") != "public":
                errors.append(f"Public leak: principal_only tile in public file index: {tid}")
            if (tile.get("lifecycle") or {}).get("state") == "RED":
                errors.append(f"Public leak: RED tile in public file index: {tid}")
            if entry.get("metadata_only_files"):
                errors.append(f"Public leak: metadata_only_files present on {tid}")

    serialized = json.dumps(index_doc, ensure_ascii=False)
    leak = _FORBIDDEN_LEAK_RE.search(serialized)
    if leak:
        errors.append(f"WSP 71 forbidden path/secret pattern detected: {leak.group(0)!r}")
    if scope == "public_mall":
        low = serialized.lower()
        for forbidden in _PUBLIC_FORBIDDEN_SUBSTRINGS:
            if forbidden.lower() in low:
                errors.append(f"Public projection leak: forbidden substring {forbidden!r} found in file index")
    return errors


def export_public_source_file_index(
    graph: Dict[str, Any],
    path_accounting_doc: Dict[str, Any],
    output_path: Path = DEFAULT_FRACTAL_SOURCE_FILES_OUTPUT_PATH,
) -> Path:
    """Validate and write the gated-member ``public_mall`` source file index strictly outside ``public/``."""
    resolved_out = _assert_outside_public_root(output_path, "public_mall source file index")
    index_doc = build_fractal_source_file_index(graph, path_accounting_doc, scope="public_mall")
    errors = validate_source_file_index(index_doc, graph)
    if errors:
        raise ValueError(f"Public source file index failed validation: {errors[:5]}")
    resolved_out.parent.mkdir(parents=True, exist_ok=True)
    with open(resolved_out, "w", encoding="utf-8") as f:
        json.dump(index_doc, f, separators=(",", ":"), ensure_ascii=False)
        f.write("\n")
    logger.info(
        "[PFMALL-EXPORT] Wrote %d public source files across %d tiles to %s",
        index_doc["counts"]["mapped_files"],
        index_doc["counts"]["owning_tiles"],
        resolved_out,
    )
    return resolved_out


def export_architect_source_file_index(
    graph: Dict[str, Any],
    path_accounting_doc: Dict[str, Any],
    output_path: Path,
) -> Path:
    """Validate and write the ``012_architect`` source file index strictly outside ``public/``."""
    resolved_out = _assert_outside_public_root(output_path, "012_architect source file index")
    index_doc = build_fractal_source_file_index(graph, path_accounting_doc, scope="012_architect")
    errors = validate_source_file_index(index_doc, graph)
    if errors:
        raise ValueError(f"Architect source file index failed validation: {errors[:5]}")
    resolved_out.parent.mkdir(parents=True, exist_ok=True)
    with open(resolved_out, "w", encoding="utf-8") as f:
        json.dump(index_doc, f, separators=(",", ":"), ensure_ascii=False)
        f.write("\n")
    logger.info(
        "[PFMALL-EXPORT] Wrote %d architect source files across %d tiles to %s",
        index_doc["counts"]["mapped_files"],
        index_doc["counts"]["owning_tiles"],
        resolved_out,
    )
    return resolved_out


def main(argv: Optional[List[str]] = None) -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Export p.fMALL member catalogs.")
    parser.add_argument("--fractal-graph", action="store_true", help="Export modules/foundups/pfmall/projections/fractal_tile_graph.public.json")
    parser.add_argument("--architect-output", type=Path, default=None, help="Optional destination outside public/ for 012_architect graph")
    parser.add_argument("--all", action="store_true", help="Export both mall-catalog.json and modules/foundups/pfmall/projections/fractal_tile_graph.public.json")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    if (not args.fractal_graph and args.architect_output is None) or args.all:
        path = export_mall_catalog()
        print(f"Generated {path} ({path.stat().st_size} bytes)")
    if args.fractal_graph or args.all:
        graph_path = export_fractal_tile_graph()
        print(f"Generated {graph_path} ({graph_path.stat().st_size} bytes)")
    if args.architect_output is not None:
        arch_path = export_architect_tile_graph(output_path=args.architect_output)
        print(f"Generated {arch_path} ({arch_path.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
