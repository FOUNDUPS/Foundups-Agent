#!/usr/bin/env python3
"""Diagnose --index-docs pipeline consistency without mutation.

DRY-RUN ONLY. This script opens Chroma's SQLite metadata in ``mode=ro``, never
spawns child processes, and never invokes the indexer. It probes seven
hypotheses (H1..H7) describing
why ``--index-docs`` can exit 0 yet leave audit docs absent from
``navigation_docs``.

Hypotheses probed:

  H1  project_root mismatch
      HoloIndex resolves ``project_root = Path(__file__).parent.parent.parent``.
      A linked-worktree invocation roots indexing at that exact checkout.

  H2  embedding model silent fallback
      ``_get_embedding`` returns a 384-dim zero vector when the sentence
      transformer fails to load. The canonical flat/Hugging Face snapshot
      resolver is used for presence only; nothing is loaded.

  H3  bulk collection insertion silent partial failure
      The indexer accumulates ids/embeddings/documents/metadatas and performs a
      single bulk insertion at the end of ``index_docs_entries``. This probe
      simulates accumulation against a recorder stub (no Chroma mutation) and
      checks for duplicate id risks given the ``doc_{idx}`` scheme.

  H4  file-discovery filter excludes target audit docs
      The current source filter evaluates dot-prefixed components relative to
      each discovery root. Policy exclusions are reported separately from
      target rejection.

  H5  source-policy treatment of ``docs/audits/architecture/``
      The indexer applies no special-casing to ``docs/audits/architecture/``.
      Priority is boosted post-classification by ``_calculate_document_priority``
      but no path-class is excluded.

  H6  observability gap
      Current ``IndexResult`` handling surfaces discovered/indexed counts and
      withholds the refresh reward from zero-entry runs. The probe records this
      closure instead of repeating the historical gap.

  H7  stored metadata path compatibility
      Strict Tier-0 injection performs exact repository-relative metadata
      lookups with cardinality one. The read-only metadata probe rejects
      missing, duplicate, mixed, non-POSIX, wrong-case, and malformed evidence.

Forbidden patterns asserted absent from this operator and its private metadata
helper (static safety scan):
the Chroma mutation method-call prefixes for write/modify/remove operations,
the collection-removal verb, the in-place reset/persist verbs, and any host
process invocation primitive. The full token list is assembled at runtime
from the ``_FORBIDDEN_FRAGMENTS`` table below; neither source file contains
those tokens as literal substrings. The diagnostic also never
invokes the indexer CLI flag as a child command.

Exit codes:
  0 - probe completed (regardless of findings)
  2 - probe could not complete (Chroma unavailable, etc.)

Slice: HOLOINDEX_INDEX_DOCS_CONSISTENCY_AUDIT_PHASE1
WSP_97: REPORT_ONLY, READ_ONLY, NO_REINDEX, NO_CORE_INSTRUMENTATION.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

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


def replicate_indexer_filter(
    file_path: Path, discovery_base: Optional[Path] = None
) -> Dict[str, bool]:
    """Return per-clause pass/fail mirroring ``index_docs_entries``.

    The indexer filter is:

        f for f in all_doc_files
        if 'node_modules' not in str(f)
        and 'CHANGELOG' not in f.name.upper()
        and 'package-lock' not in f.name.lower()
        and not _has_dotfile_in_relative_path(f, discovery_base)
        and '_backup' not in str(f).lower()
        and '/archive/' not in str(f).lower()
        and '\\archive\\' not in str(f).lower()
    Each clause is reported separately so the audit can pinpoint which clause
    rejects a target file.
    """
    path_str = str(file_path)
    try:
        relative = file_path.relative_to(discovery_base) if discovery_base else file_path
    except ValueError:
        relative = file_path
    relative_fwd = relative.as_posix().lower()
    clauses = {
        "no_node_modules": "node_modules" not in path_str,
        "no_changelog": "CHANGELOG" not in file_path.name.upper(),
        "no_package_lock": "package-lock" not in file_path.name.lower(),
        "no_dot_prefixed_parts": not any(part.startswith(".") for part in relative.parts),
        "no_backup": "_backup" not in path_str.lower(),
        "no_archive": "/archive/" not in f"/{relative_fwd}/",
    }
    clauses["overall_pass"] = all(clauses.values())
    return clauses


# ---------------------------------------------------------------------------
# H1 - project_root resolution
# ---------------------------------------------------------------------------


def probe_h1_project_root(project_root: Optional[Path] = None) -> Dict[str, Any]:
    """Resolve project_root the same way HoloIndex does, without instantiating."""
    # HoloIndex itself uses: Path(__file__).parent.parent.parent from
    # holo_index/core/holo_index.py. This script lives at
    # holo_index/scripts/diagnose_index_docs_pipeline.py. The equivalent
    # resolution from this script is .parent.parent (scripts/ -> holo_index/
    # -> repo_root).
    inferred_repo_root = project_root or Path(__file__).resolve().parent.parent.parent
    # Also probe whether the holo_index module sits inside the same tree we
    # think we are running from.
    holo_index_pkg = inferred_repo_root / "holo_index"
    holo_index_core = holo_index_pkg / "core" / "holo_index.py"
    git_marker = inferred_repo_root / ".git"
    linked_worktree = git_marker.is_file()
    return {
        "holo_index_core_exists": holo_index_core.exists(),
        "git_marker_present": git_marker.exists(),
        "linked_worktree": linked_worktree,
        "h1_finding": (
            "LINKED_WORKTREE_PROJECT_ROOT"
            if linked_worktree
            else "MAIN_REPO_PROJECT_ROOT"
        ),
    }


# ---------------------------------------------------------------------------
# H2 - embedding model cache presence
# ---------------------------------------------------------------------------


def probe_h2_embedding_model(
    ssd_path: str = "E:/HoloIndex", model_name: str = "all-MiniLM-L6-v2"
) -> Dict[str, Any]:
    """Resolve the canonical model snapshot without loading it."""
    from holo_index.embedding_space import resolve_sentence_transformer_snapshot

    models_path = Path(ssd_path) / "models"
    snapshot = resolve_sentence_transformer_snapshot(models_path, model_name)
    cache_hit = snapshot is not None
    layout = "none"
    if snapshot is not None:
        normalized = snapshot.as_posix().lower()
        layout = "huggingface_snapshot" if "/snapshots/" in normalized else "flat"
    return {
        "models_path_exists": models_path.exists(),
        "model_name": model_name,
        "cache_hit": cache_hit,
        "cache_layout": layout,
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


def _discover_simulated_docs(project_root: Path, limit: int) -> List[Path]:
    discovered: List[Path] = []
    for base in [project_root / root for root in INDEXER_DOC_ROOTS]:
        if not base.exists():
            continue
        for file_path in sorted(base.rglob("*.md")):
            if len(discovered) >= limit:
                break
            if replicate_indexer_filter(file_path, base)["overall_pass"]:
                discovered.append(file_path)
        if len(discovered) >= limit:
            break
    return discovered


def _simulation_report(
    max_simulated: int, discovered: List[Path], recorder: _RecorderStub
) -> Dict[str, Any]:
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


def probe_h3_bulk_insertion_simulation(
    project_root: Path, max_simulated: int = 50
) -> Dict[str, Any]:
    """Simulate accumulation against ``_RecorderStub`` for up to ``max_simulated``
    files. No Chroma writes. Detects duplicate id risk under the
    ``doc_{idx}`` scheme used by the real indexer.
    """
    recorder = _RecorderStub()
    discovered = _discover_simulated_docs(project_root, max_simulated)
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
    return _simulation_report(max_simulated, discovered, recorder)


# ---------------------------------------------------------------------------
# H4 - file-discovery filter clause-by-clause for targets
# ---------------------------------------------------------------------------


def _target_filter_reports(project_root: Path) -> List[Dict[str, Any]]:
    docs_root = project_root / "docs"
    target_reports: List[Dict[str, Any]] = []
    for target in TARGETS:
        absolute = project_root / target["rel_path"]
        report = {
            "target_id": target["id"],
            "rel_path": target["rel_path"],
            "exists_on_disk": absolute.exists(),
        }
        if absolute.exists():
            clauses = replicate_indexer_filter(absolute, docs_root)
            failing = [k for k, v in clauses.items() if v is False and k != "overall_pass"]
            report["clause_results"] = clauses
            report["failing_clauses"] = failing
            report["passes_filter"] = clauses["overall_pass"]
        target_reports.append(report)
    return target_reports


def _aggregate_docs_filter(project_root: Path) -> Dict[str, Any]:
    docs_root = project_root / "docs"
    aggregate_total = 0
    aggregate_pass = 0
    aggregate_failure_by_clause: Dict[str, int] = {}
    if docs_root.exists():
        for f in docs_root.rglob("*.md"):
            aggregate_total += 1
            clauses = replicate_indexer_filter(f, docs_root)
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
        "docs_tree_total": aggregate_total,
        "docs_tree_passing": aggregate_pass,
        "docs_tree_failing": aggregate_total - aggregate_pass,
        "failure_counts_by_clause": aggregate_failure_by_clause,
    }


def probe_h4_filter_targets(project_root: Path) -> Dict[str, Any]:
    """Distinguish target rejection from intentional policy exclusions."""
    target_reports = _target_filter_reports(project_root)
    aggregate = _aggregate_docs_filter(project_root)
    existing = [report for report in target_reports if report["exists_on_disk"]]
    rejected = [report for report in existing if not report.get("passes_filter", False)]
    if rejected:
        finding = "TARGET_FILES_REJECTED_BY_SOURCE_FILTER"
    elif len(existing) != len(TARGETS):
        finding = "TARGET_FILES_MISSING_FROM_CHECKOUT"
    elif aggregate["docs_tree_failing"]:
        finding = "TARGETS_ADMITTED_WITH_POLICY_EXCLUSIONS"
    else:
        finding = "TARGETS_ADMITTED_NO_POLICY_EXCLUSIONS"
    return {
        "targets": target_reports,
        **aggregate,
        "rejected_target_count": len(rejected),
        "h4_finding": finding,
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
    """Record the current zero-entry IndexResult/CLI truth boundary."""
    return {
        "indexer_emits": [
            "IndexResult discovered_count and indexed_count",
            "stable warning when discovery or indexed content is empty",
        ],
        "cli_emits": [
            "warning plus discovered/indexed counts for unsuccessful IndexResult",
            "indexed entry count for successful IndexResult",
        ],
        "refresh_reward_withheld_on_zero_entries": True,
        "h6_finding": "ZERO_DOC_OBSERVABILITY_PRESENT",
    }


# ---------------------------------------------------------------------------
# Read-only Chroma observation (optional)
# ---------------------------------------------------------------------------


def observe_navigation_docs_collection_readonly(
    ssd_path: str = "E:/HoloIndex", project_root: Optional[Path] = None
) -> Dict[str, Any]:
    """Delegate to the bounded private SQLite metadata observer."""
    from holo_index.scripts._navigation_docs_metadata_probe import (
        observe_navigation_docs_collection_readonly as observe,
    )

    return observe(ssd_path, project_root)


# ---------------------------------------------------------------------------
# Static safety scan over the operator and its private metadata helper
# ---------------------------------------------------------------------------


def static_safety_scan_self() -> Dict[str, Any]:
    """Assert mutation and service-control tokens are absent from both files."""
    here = Path(__file__).resolve()
    helper = here.parent / "_navigation_docs_metadata_probe.py"
    text = "\n".join(
        source.read_text(encoding="utf-8") for source in (here, helper)
    )
    tokens = _assemble_forbidden_tokens()
    hits: Dict[str, int] = {}
    fragment_table_marker = "_FORBIDDEN_FRAGMENTS"
    for tok in tokens:
        count = text.count(tok)
        hits[tok] = count
    # Tokens may legitimately appear inside the fragment table only as split
    # halves, never as the full token. So the scan passes if every count is 0.
    return {
        "tokens_checked": tokens,
        "hit_counts": hits,
        "files_checked": 2,
        "fragment_table_present": fragment_table_marker in text,
        "passes_static_scan": all(count == 0 for count in hits.values()),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def _build_argument_parser() -> argparse.ArgumentParser:
    return argparse.ArgumentParser(
        prog="diagnose_index_docs_pipeline.py",
        description=(
            "Read-only HoloIndex docs-pipeline diagnostic. The probe never"
            " invokes an indexer or opens Chroma with write authority."
        )
    )


def _classify_primary_root_cause(
    h4: Dict[str, Any], chroma_obs: Dict[str, Any]
) -> str:
    if not chroma_obs.get("navigation_docs_available"):
        return "INCOMPLETE_NAVIGATION_DOCS_METADATA_PROBE"
    h7_findings = chroma_obs.get("h7_findings", [])
    if (
        "TIER0_ABSOLUTE_PATH_ROWS" in h7_findings
        or chroma_obs.get("h7_finding")
        == "ABSOLUTE_METADATA_BREAKS_STRICT_TIER0_EXACT_LOOKUP"
    ):
        return "ABSOLUTE_NAVIGATION_DOC_PATHS_BREAK_STRICT_TIER0_EXACT_LOOKUP"
    if chroma_obs.get("strict_tier0_contract_complete") is False:
        return "STRICT_TIER0_METADATA_CONTRACT_INVALID"
    if h4.get("rejected_target_count", 0):
        return "TARGET_SOURCE_FILTER_REJECTION"
    if h4.get("h4_finding") == "TARGET_FILES_MISSING_FROM_CHECKOUT":
        return "TARGET_FILES_MISSING_FROM_CHECKOUT"
    return "INCONCLUSIVE_FROM_READ_ONLY_PROBES"


def _build_summary(project_root: Path) -> Dict[str, Any]:
    h1 = probe_h1_project_root(project_root)
    safety = static_safety_scan_self()
    h2 = probe_h2_embedding_model()
    h3 = probe_h3_bulk_insertion_simulation(project_root)
    h4 = probe_h4_filter_targets(project_root)
    h5 = probe_h5_source_policy()
    h6 = probe_h6_observability()
    chroma_obs = observe_navigation_docs_collection_readonly(
        project_root=project_root
    )
    findings = {
        "H1": h1["h1_finding"],
        "H2": h2["h2_finding"],
        "H3": h3["h3_finding"],
        "H4": h4["h4_finding"],
        "H5": h5["h5_finding"],
        "H6": h6["h6_finding"],
        "H7": chroma_obs.get("h7_finding", "METADATA_PROBE_UNAVAILABLE"),
    }
    complete = safety["passes_static_scan"] and chroma_obs.get(
        "navigation_docs_available", False
    )
    return {
        "slice": "HOLOINDEX_INDEX_DOCS_DIAGNOSTIC_HARDENING_PHASE1",
        "probe_version": "2.1.0",
        "outcome": "DIAGNOSED" if complete else "PROBE_INCOMPLETE",
        "static_safety_scan": safety,
        "h1_project_root": h1,
        "h2_embedding_model": h2,
        "h3_bulk_insertion_simulation": h3,
        "h4_file_discovery_filter": h4,
        "h5_source_policy": h5,
        "h6_observability": h6,
        "h7_navigation_docs_metadata": chroma_obs,
        "hypothesis_findings": findings,
        "primary_root_cause": _classify_primary_root_cause(h4, chroma_obs),
    }


def _emit_summary(summary: Dict[str, Any]) -> None:
    print("=" * 70, file=sys.stderr)
    print(
        "HoloIndex --index-docs pipeline diagnostic (DRY-RUN, NO CHROMA MUTATION)",
        file=sys.stderr,
    )
    print("Slice: HOLOINDEX_INDEX_DOCS_CONSISTENCY_AUDIT_PHASE1", file=sys.stderr)
    print("=" * 70, file=sys.stderr)

    print(json.dumps(summary, indent=2, sort_keys=True))

    print("\n" + "=" * 70, file=sys.stderr)
    print("DIAGNOSTIC SUMMARY", file=sys.stderr)
    print("=" * 70, file=sys.stderr)
    for hk, hv in summary["hypothesis_findings"].items():
        print(f"  {hk}: {hv}", file=sys.stderr)
    print(
        f"\nPRIMARY ROOT CAUSE: {summary['primary_root_cause']}",
        file=sys.stderr,
    )
    print("=" * 70, file=sys.stderr)


def main(argv: Optional[List[str]] = None) -> int:
    _build_argument_parser().parse_args(argv)
    project_root = Path(__file__).resolve().parent.parent.parent
    summary = _build_summary(project_root)
    _emit_summary(summary)
    if summary["outcome"] != "DIAGNOSED":
        print(
            "WARN: required read-only evidence unavailable; probe incomplete.",
            file=sys.stderr,
        )
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
