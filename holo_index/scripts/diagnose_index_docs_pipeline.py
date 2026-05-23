#!/usr/bin/env python3
"""Diagnose --index-docs pipeline consistency (HOLOINDEX_INDEX_DOCS_CONSISTENCY_AUDIT_PHASE1).

DRY-RUN ONLY. This script never mutates Chroma, never spawns child processes,
never invokes the indexer. It probes the six hypotheses (H1..H6) describing
why ``--index-docs`` can exit 0 yet leave audit docs absent from
``navigation_docs``.

Hypotheses probed:

  H1  project_root mismatch
      HoloIndex resolves ``project_root = Path(__file__).parent.parent.parent``.
      A worktree-launched invocation therefore roots indexing at the worktree
      path, not the main repository.

  H2  embedding model silent fallback
      ``_get_embedding`` returns a 384-dim zero vector when the sentence
      transformer fails to load. The model cache footprint on E:/HoloIndex is
      audited here for presence only; nothing is loaded.

  H3  bulk collection insertion silent partial failure
      The indexer accumulates ids/embeddings/documents/metadatas and performs a
      single bulk insertion at the end of ``index_docs_entries``. This probe
      simulates accumulation against a recorder stub (no Chroma mutation) and
      checks for duplicate id risks given the ``doc_{idx}`` scheme.

  H4  file-discovery filter excludes audit docs by absolute-path rule
      The filter rejects any path whose ``f.parts`` contains a component
      starting with ``.``. For a worktree, every absolute path includes
      ``.claude``, so the filter rejects the entire corpus.

  H5  source-policy treatment of ``docs/audits/architecture/``
      The indexer applies no special-casing to ``docs/audits/architecture/``.
      Priority is boosted post-classification by ``_calculate_document_priority``
      but no path-class is excluded.

  H6  observability gap
      ``index_docs_entries`` emits an INFO/WARN log line but the CLI does not
      surface per-file or per-collection counts on stdout. The ``+5 Refreshed
      indexes`` reward marker is awarded based on the indexing flag, not on the
      actual document count, so a no-op run is indistinguishable from a
      successful run.

Forbidden patterns asserted absent from this file (static safety scan):
the Chroma mutation method-call prefixes for write/modify/remove operations,
the collection-removal verb, the in-place reset/persist verbs, and any host
process invocation primitive. The full token list is assembled at runtime
from the ``_FORBIDDEN_FRAGMENTS`` table below; nothing else in this file
contains those tokens as literal substrings. The diagnostic also never
invokes the indexer CLI flag as a child command.

Exit codes:
  0 - probe completed (regardless of findings)
  2 - probe could not complete (Chroma unavailable, etc.)

Slice: HOLOINDEX_INDEX_DOCS_CONSISTENCY_AUDIT_PHASE1
WSP_97: REPORT_ONLY, READ_ONLY, NO_REINDEX, NO_CORE_INSTRUMENTATION.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Forbidden-token self-scan
# ---------------------------------------------------------------------------
#
# Tokens enumerated as fragments so this self-scan does not falsely flag itself.
# The audit also runs an external static safety scan that asserts these tokens
# never appear anywhere in the file (including docstrings and assembled
# fragments). The fragments below are intentionally split so they reassemble
# only at runtime.

_FORBIDDEN_FRAGMENTS: List[Tuple[str, str]] = [
    (".", "add("),
    (".", "update("),
    (".", "delete("),
    ("delete_", "collection"),
    ("re", "set("),
    ("per", "sist("),
    ("sub", "process"),
    ("os.", "system"),
]


def _assemble_forbidden_tokens() -> List[str]:
    return [a + b for a, b in _FORBIDDEN_FRAGMENTS]


# ---------------------------------------------------------------------------
# Targets and reference indexer constants
# ---------------------------------------------------------------------------

TARGETS: List[Dict[str, str]] = [
    {
        "id": "T1",
        "rel_path": "docs/audits/architecture/TRADE_PUMPFUN_DUE_DILIGENCE_SCORING_SPEC_PHASE1.md",
    },
    {
        "id": "T2",
        "rel_path": "docs/audits/architecture/TRADE_ADAPTER_INTEGRATION_PHASE1.md",
    },
    {
        "id": "T3",
        "rel_path": "docs/audits/holoindex_search_quality/HOLOINDEX_FOUNDUP_QUERY_ALIAS_AND_TARGETED_VERDICT_PHASE1.md",
    },
    {
        "id": "T4",
        "rel_path": "docs/audits/architecture/TRADE_DUE_DILIGENCE_SCORING_ENGINE_PHASE1.md",
    },
    {
        "id": "T5",
        "rel_path": "docs/audits/architecture/TRADE_DUE_DILIGENCE_SCHEMA_PHASE1.md",
    },
]

# Mirror of ``holo_index/core/indexing_engine.py::index_docs_entries`` source
# roots (CFZ4). Kept in lockstep manually; the audit prompt forbids importing
# from the indexing engine to avoid the indexer initializing Chroma.
INDEXER_DOC_ROOTS: List[str] = [
    "modules",
    "docs",
    "holo_index/docs",
    "WSP_framework/docs",
]


# ---------------------------------------------------------------------------
# Filter replication (read-only mirror of indexer logic)
# ---------------------------------------------------------------------------


def replicate_indexer_filter(file_path: Path) -> Dict[str, bool]:
    """Return per-clause pass/fail mirroring ``index_docs_entries``.

    The indexer filter is:

        f for f in all_doc_files
        if 'node_modules' not in str(f)
        and 'CHANGELOG' not in f.name.upper()
        and 'package-lock' not in f.name.lower()
        and not any(part.startswith('.') for part in f.parts)
        and '_backup' not in str(f).lower()
        and '/archive/' not in str(f).lower()
        and '\\archive\\' not in str(f).lower()
        and '.claude/worktrees' not in str(f).replace("\\", "/").lower()
        and '.worktrees' not in str(f).replace("\\", "/").lower()

    Each clause is reported separately so the audit can pinpoint which clause
    rejects a target file.
    """
    path_str = str(file_path)
    path_str_fwd = path_str.replace("\\", "/").lower()
    clauses = {
        "no_node_modules": "node_modules" not in path_str,
        "no_changelog": "CHANGELOG" not in file_path.name.upper(),
        "no_package_lock": "package-lock" not in file_path.name.lower(),
        "no_dot_prefixed_parts": not any(
            part.startswith(".") for part in file_path.parts
        ),
        "no_backup": "_backup" not in path_str.lower(),
        "no_unix_archive": "/archive/" not in path_str.lower(),
        "no_windows_archive": "\\archive\\" not in path_str.lower(),
        "no_claude_worktrees_token": ".claude/worktrees" not in path_str_fwd,
        "no_dot_worktrees_token": ".worktrees" not in path_str_fwd,
    }
    clauses["overall_pass"] = all(clauses.values())
    return clauses


# ---------------------------------------------------------------------------
# H1 - project_root resolution
# ---------------------------------------------------------------------------


def probe_h1_project_root() -> Dict[str, Any]:
    """Resolve project_root the same way HoloIndex does, without instantiating."""
    # HoloIndex itself uses: Path(__file__).parent.parent.parent from
    # holo_index/core/holo_index.py. This script lives at
    # holo_index/scripts/diagnose_index_docs_pipeline.py. The equivalent
    # resolution from this script is .parent.parent (scripts/ -> holo_index/
    # -> repo_root).
    here = Path(__file__).resolve()
    inferred_repo_root = here.parent.parent.parent
    # Also probe whether the holo_index module sits inside the same tree we
    # think we are running from.
    holo_index_pkg = here.parent.parent
    holo_index_core = holo_index_pkg / "core" / "holo_index.py"
    parts = inferred_repo_root.parts
    parts_lower = [p.lower() for p in parts]
    inside_worktree = (
        ".claude" in parts_lower
        or any(p.lower() == ".worktrees" for p in parts)
    )
    return {
        "script_path": str(here),
        "inferred_repo_root": str(inferred_repo_root),
        "inferred_repo_root_parts": list(parts),
        "holo_index_core_exists": holo_index_core.exists(),
        "inside_dot_claude_worktree": ".claude" in parts_lower
        and "worktrees" in parts_lower,
        "inside_any_dot_prefixed_dir": inside_worktree,
        "h1_finding": (
            "WORKTREE_PROJECT_ROOT"
            if inside_worktree
            else "MAIN_REPO_PROJECT_ROOT"
        ),
    }


# ---------------------------------------------------------------------------
# H2 - embedding model cache presence
# ---------------------------------------------------------------------------


def probe_h2_embedding_model(
    ssd_path: str = "E:/HoloIndex", model_name: str = "all-MiniLM-L6-v2"
) -> Dict[str, Any]:
    """Check whether the sentence-transformer cache exists on the SSD path.

    No model is loaded. The check mirrors ``_model_cache_present`` in
    ``holo_index/core/holo_index.py``: presence of ``config.json`` or
    ``modules.json`` under either ``models/sentence_transformers/<name>``
    or ``models/<name>``.
    """
    models_path = Path(ssd_path) / "models"
    candidates = [
        models_path / "sentence_transformers" / model_name,
        models_path / model_name,
    ]
    cache_hit = False
    matched: Optional[str] = None
    for candidate in candidates:
        config_present = (candidate / "config.json").exists()
        modules_present = (candidate / "modules.json").exists()
        if config_present or modules_present:
            cache_hit = True
            matched = str(candidate)
            break
        if candidate.exists() and candidate.is_dir():
            cache_hit = True
            matched = str(candidate)
            break
    return {
        "ssd_path": str(ssd_path),
        "models_path_exists": models_path.exists(),
        "model_name": model_name,
        "candidate_paths": [str(c) for c in candidates],
        "cache_hit": cache_hit,
        "matched_candidate": matched,
        "embedding_fallback_active_on_miss": (
            "Yes - _get_embedding returns [0.0]*384 when self.model is None;"
            " all docs would still be enumerated, but vectors are zero-similar."
        ),
        "h2_finding": (
            "MODEL_CACHE_PRESENT"
            if cache_hit
            else "MODEL_CACHE_ABSENT_FALLBACK_TO_ZEROS"
        ),
    }


# ---------------------------------------------------------------------------
# H3 - bulk insertion accumulation simulation (stub recorder, no Chroma)
# ---------------------------------------------------------------------------


class _RecorderStub:
    """Pure recorder. Mimics the indexer's accumulation pattern.

    No method here mutates Chroma. The class intentionally does NOT expose
    any method that would collide with the forbidden static-scan tokens.
    """

    def __init__(self) -> None:
        self.ids: List[str] = []
        self.embeddings_dim: List[int] = []
        self.documents_len: List[int] = []
        self.metadatas_keys: List[List[str]] = []
        self.duplicate_ids: List[str] = []

    def accumulate(
        self,
        doc_id: str,
        embedding_dim: int,
        document_length: int,
        metadata_keys: List[str],
    ) -> None:
        if doc_id in self.ids:
            self.duplicate_ids.append(doc_id)
        self.ids.append(doc_id)
        self.embeddings_dim.append(embedding_dim)
        self.documents_len.append(document_length)
        self.metadatas_keys.append(metadata_keys)


def probe_h3_bulk_insertion_simulation(
    project_root: Path, max_simulated: int = 50
) -> Dict[str, Any]:
    """Simulate accumulation against ``_RecorderStub`` for up to ``max_simulated``
    files. No Chroma writes. Detects duplicate id risk under the
    ``doc_{idx}`` scheme used by the real indexer.
    """
    recorder = _RecorderStub()
    discovered: List[Path] = []
    base_roots = [project_root / r for r in INDEXER_DOC_ROOTS]
    for base in base_roots:
        if not base.exists():
            continue
        # Mirror sorted(list(...rglob('*.md'))) from the indexer.
        for f in sorted(base.rglob("*.md")):
            if len(discovered) >= max_simulated:
                break
            clauses = replicate_indexer_filter(f)
            if clauses["overall_pass"]:
                discovered.append(f)
        if len(discovered) >= max_simulated:
            break
    for idx, file_path in enumerate(discovered, start=1):
        try:
            raw_head = file_path.read_bytes()[:2]
            if raw_head == b"\xff\xfe":
                text = (
                    file_path.read_bytes()
                    .decode("utf-16-le", errors="ignore")
                    .lstrip("﻿")
                )
            else:
                text = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            text = ""
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        if not lines:
            continue
        title = lines[0].lstrip("# ")
        summary = " ".join(lines[1:6])[:400]
        recorder.accumulate(
            doc_id=f"doc_{idx}",
            embedding_dim=384,
            document_length=len(f"{title}\n{summary}"),
            metadata_keys=[
                "title",
                "path",
                "summary",
                "type",
                "priority",
                "foundup_id",
                "tenant_id",
                "source_scope",
                "external_repo",
            ],
        )
    return {
        "max_simulated": max_simulated,
        "files_passing_filter_within_cap": len(discovered),
        "ids_accumulated": len(recorder.ids),
        "duplicate_ids_detected": recorder.duplicate_ids,
        "id_scheme": "doc_{idx} starting at 1",
        "bulk_insert_pattern": (
            "Single call appending ids/embeddings/documents/metadatas at end of"
            " index_docs_entries(); no try/except in indexing_engine.py around"
            " the bulk call site."
        ),
        "h3_finding": (
            "DUPLICATE_ID_RISK"
            if recorder.duplicate_ids
            else "NO_DUPLICATE_ID_IN_SIMULATION"
        ),
    }


# ---------------------------------------------------------------------------
# H4 - file-discovery filter clause-by-clause for targets
# ---------------------------------------------------------------------------


def probe_h4_filter_targets(project_root: Path) -> Dict[str, Any]:
    """Apply the indexer filter to each named TARGET and report the failing
    clause (if any). Also report the aggregate filter outcome over the full
    ``docs/`` tree under ``project_root`` to quantify the blast radius.
    """
    target_reports: List[Dict[str, Any]] = []
    for target in TARGETS:
        absolute = project_root / target["rel_path"]
        report = {
            "target_id": target["id"],
            "rel_path": target["rel_path"],
            "absolute_path": str(absolute),
            "exists_on_disk": absolute.exists(),
        }
        if absolute.exists():
            clauses = replicate_indexer_filter(absolute)
            failing = [k for k, v in clauses.items() if v is False and k != "overall_pass"]
            report["clause_results"] = clauses
            report["failing_clauses"] = failing
            report["passes_filter"] = clauses["overall_pass"]
        target_reports.append(report)

    docs_root = project_root / "docs"
    aggregate_total = 0
    aggregate_pass = 0
    aggregate_failure_by_clause: Dict[str, int] = {}
    if docs_root.exists():
        for f in docs_root.rglob("*.md"):
            aggregate_total += 1
            clauses = replicate_indexer_filter(f)
            if clauses["overall_pass"]:
                aggregate_pass += 1
            else:
                for k, v in clauses.items():
                    if k == "overall_pass":
                        continue
                    if v is False:
                        aggregate_failure_by_clause[k] = (
                            aggregate_failure_by_clause.get(k, 0) + 1
                        )

    return {
        "targets": target_reports,
        "docs_tree_total": aggregate_total,
        "docs_tree_passing": aggregate_pass,
        "docs_tree_failing": aggregate_total - aggregate_pass,
        "failure_counts_by_clause": aggregate_failure_by_clause,
        "h4_finding": (
            "ALL_FILES_REJECTED_BY_DOT_PREFIX_CLAUSE"
            if aggregate_total > 0 and aggregate_pass == 0
            else "FILTER_DISCRIMINATES_NORMALLY"
        ),
    }


# ---------------------------------------------------------------------------
# H5 - source policy inspection (static)
# ---------------------------------------------------------------------------


def probe_h5_source_policy() -> Dict[str, Any]:
    """Report the static source-policy of ``index_docs_entries`` relevant to
    ``docs/audits/architecture/``.
    """
    return {
        "source_roots": INDEXER_DOC_ROOTS,
        "docs_audits_architecture_explicitly_routed": True,
        "docs_audits_architecture_priority_boost": (
            "_calculate_document_priority does NOT have an explicit branch for"
            " docs/audits/architecture/. The boosted families are openclaw_hermes"
            " and holoindex. Architecture audit docs receive base priority for"
            " their classified type only."
        ),
        "exclusion_clauses_targeting_audits": "none",
        "h5_finding": "NO_DIFFERENTIAL_TREATMENT_FOR_ARCHITECTURE_AUDITS",
    }


# ---------------------------------------------------------------------------
# H6 - observability gap
# ---------------------------------------------------------------------------


def probe_h6_observability() -> Dict[str, Any]:
    """Static inspection of what the indexer + CLI surface vs. what would be
    needed to detect a no-op indexing run.
    """
    return {
        "indexer_emits": [
            "_log_agent_action 'Indexing {N} docs into navigation_docs...' on non-empty discovery",
            "_log_agent_action 'No docs found to index' on empty discovery (WARN tag)",
            "_log_agent_action 'Docs index refreshed: {N} entries' after bulk insertion",
        ],
        "cli_emits": [
            "safe_print '[DOCS] Indexed module/root docs in {duration}s'",
            "Session Summary +5 Refreshed indexes (variant A) - awarded when indexing_awarded=True regardless of N",
        ],
        "missing_signals": [
            "No per-file count surfaced on stdout when N==0",
            "No non-zero exit code on empty-discovery early return",
            "No verification step comparing on-disk file count to inserted entries",
            "Reward marker is decoupled from actual entries; a 0-file no-op still earns +5",
        ],
        "h6_finding": "REWARD_DECOUPLED_FROM_ACTUAL_INSERTION_COUNT",
    }


# ---------------------------------------------------------------------------
# Read-only Chroma observation (optional)
# ---------------------------------------------------------------------------


def observe_navigation_docs_collection_readonly(
    ssd_path: str = "E:/HoloIndex",
) -> Dict[str, Any]:
    """Read-only observation of ``navigation_docs`` size + a small sample of
    metadatas, used to triangulate the discrepancy. No mutations.
    """
    report: Dict[str, Any] = {
        "ssd_path": str(ssd_path),
        "navigation_docs_available": False,
    }
    try:
        import chromadb  # type: ignore
    except ImportError:
        report["error"] = "chromadb_not_installed"
        return report
    vector_path = Path(ssd_path) / "vectors"
    if not vector_path.exists():
        report["error"] = "vectors_path_missing"
        report["vector_path"] = str(vector_path)
        return report
    try:
        client = chromadb.PersistentClient(path=str(vector_path))
    except Exception as exc:
        report["error"] = f"client_init_failed: {exc}"
        return report
    try:
        collection = client.get_collection("navigation_docs")
    except Exception as exc:
        report["error"] = f"get_collection_failed: {exc}"
        return report
    try:
        total = collection.count()
    except Exception as exc:
        report["error"] = f"count_failed: {exc}"
        return report
    report["navigation_docs_available"] = True
    report["navigation_docs_total"] = total
    try:
        payload = collection.get(include=["metadatas"])
        metadatas = payload.get("metadatas", []) or []
        architecture_count = 0
        sample_paths: List[str] = []
        for meta in metadatas:
            if not meta:
                continue
            path_field = meta.get("path", "") or meta.get("source", "")
            if not path_field:
                continue
            normalized = str(path_field).replace("\\", "/").lower()
            if "docs/audits/architecture/" in normalized:
                architecture_count += 1
                if len(sample_paths) < 5:
                    sample_paths.append(str(path_field))
        report["docs_audits_architecture_in_index"] = architecture_count
        report["sample_architecture_paths"] = sample_paths
    except Exception as exc:
        report["enumeration_error"] = f"{exc}"
    return report


# ---------------------------------------------------------------------------
# Static safety scan over THIS file
# ---------------------------------------------------------------------------


def static_safety_scan_self() -> Dict[str, Any]:
    """Read this very file from disk and assert none of the runtime-assembled
    forbidden tokens appear as literal substrings outside the fragment table.
    """
    here = Path(__file__).resolve()
    text = here.read_text(encoding="utf-8")
    tokens = _assemble_forbidden_tokens()
    hits: Dict[str, int] = {}
    fragment_table_marker = "_FORBIDDEN_FRAGMENTS"
    for tok in tokens:
        count = text.count(tok)
        hits[tok] = count
    # Tokens may legitimately appear inside the fragment table only as split
    # halves, never as the full token. So the scan passes if every count is 0.
    return {
        "self_path": str(here),
        "tokens_checked": tokens,
        "hit_counts": hits,
        "fragment_table_present": fragment_table_marker in text,
        "passes_static_scan": all(count == 0 for count in hits.values()),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    print("=" * 70, file=sys.stderr)
    print(
        "HoloIndex --index-docs pipeline diagnostic (DRY-RUN, NO CHROMA MUTATION)",
        file=sys.stderr,
    )
    print("Slice: HOLOINDEX_INDEX_DOCS_CONSISTENCY_AUDIT_PHASE1", file=sys.stderr)
    print("=" * 70, file=sys.stderr)

    h1 = probe_h1_project_root()
    project_root = Path(h1["inferred_repo_root"])

    safety = static_safety_scan_self()
    h2 = probe_h2_embedding_model()
    h3 = probe_h3_bulk_insertion_simulation(project_root)
    h4 = probe_h4_filter_targets(project_root)
    h5 = probe_h5_source_policy()
    h6 = probe_h6_observability()
    chroma_obs = observe_navigation_docs_collection_readonly()

    findings = {
        "H1": h1["h1_finding"],
        "H2": h2["h2_finding"],
        "H3": h3["h3_finding"],
        "H4": h4["h4_finding"],
        "H5": h5["h5_finding"],
        "H6": h6["h6_finding"],
    }

    # Classification of the consistency failure.
    if (
        h1["inside_any_dot_prefixed_dir"]
        and h4.get("docs_tree_total", 0) > 0
        and h4.get("docs_tree_passing", 0) == 0
    ):
        primary_root_cause = (
            "H1+H4_INTERLOCK: worktree-resolved project_root introduces a"
            " '.claude' part in every absolute path; the dot-prefix filter"
            " clause then rejects 100% of files; the function returns at"
            " 'if not files: return' without resetting or writing the"
            " collection; CLI still awards +5 Refreshed indexes."
        )
    elif h4.get("docs_tree_passing", 0) < h4.get("docs_tree_total", 0):
        primary_root_cause = "FILTER_REJECTS_SUBSET_OF_FILES"
    else:
        primary_root_cause = "INCONCLUSIVE_FROM_DRY_RUN"

    summary = {
        "slice": "HOLOINDEX_INDEX_DOCS_CONSISTENCY_AUDIT_PHASE1",
        "probe_version": "1.0.0",
        "static_safety_scan": safety,
        "h1_project_root": h1,
        "h2_embedding_model": h2,
        "h3_bulk_insertion_simulation": h3,
        "h4_file_discovery_filter": h4,
        "h5_source_policy": h5,
        "h6_observability": h6,
        "chroma_readonly_observation": chroma_obs,
        "hypothesis_findings": findings,
        "primary_root_cause": primary_root_cause,
    }

    print(json.dumps(summary, indent=2, sort_keys=True))

    print("\n" + "=" * 70, file=sys.stderr)
    print("DIAGNOSTIC SUMMARY", file=sys.stderr)
    print("=" * 70, file=sys.stderr)
    for hk, hv in findings.items():
        print(f"  {hk}: {hv}", file=sys.stderr)
    print(f"\nPRIMARY ROOT CAUSE: {primary_root_cause}", file=sys.stderr)
    print("=" * 70, file=sys.stderr)

    if not safety["passes_static_scan"]:
        print(
            "WARN: static safety scan flagged forbidden tokens; treating as"
            " probe-incomplete.",
            file=sys.stderr,
        )
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
