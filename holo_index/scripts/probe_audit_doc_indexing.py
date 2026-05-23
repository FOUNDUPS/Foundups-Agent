#!/usr/bin/env python3
"""HoloIndex Audit Doc Indexing Probe — Phase 1

READ-ONLY diagnostic probe to classify WHY target audit docs fail to surface
for their slice-ID queries. This script does NOT mutate Chroma.

Classification space:
  A. NOT_INDEXED
     No document/chunk for the target path or filename exists in navigation_docs.

  B. INDEXED_NO_SLICE_ID
     Target is present, but slice_id metadata is absent or does not match.

  C. INDEXED_WITH_SLICE_ID_OUTRANKED
     Target is present with correct slice_id, but exact query ranks another doc higher.

  D. INDEXED_BUT_BOOST_NOT_APPLIED
     Target is present with correct slice_id, but search_engine boost path does not fire.

  E. INDEXED_METADATA_UNKNOWN_OR_PATH_SCHEMA_MISMATCH
     Target may be present, but metadata path/source fields do not allow reliable
     path matching. Requires metadata schema normalization before ranking fixes.

Exit codes:
  0 — probe completed successfully (regardless of classification)
  2 — Chroma backend unavailable or collection missing (fail-closed)

Slice: HOLOINDEX_AUDIT_DOC_INDEXING_PROBE_PHASE1
WSP 97: REPORT_ONLY, READ_ONLY_CHROMA_ACCESS, NO_CHROMA_MUTATION
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Static safety scan: This script MUST NOT contain mutation methods.
# Banned patterns: .add(, .update(, .delete(, delete_collection, reset(, persist(
# If any appears, the implementation is in violation.

# ---------------------------------------------------------------------------
# Target documents to probe
# ---------------------------------------------------------------------------

TARGETS = [
    {
        "id": "T1",
        "path": "docs/audits/architecture/TRADE_PUMPFUN_DUE_DILIGENCE_SCORING_SPEC_PHASE1.md",
        "slice_id": "TRADE_PUMPFUN_DUE_DILIGENCE_SCORING_SPEC_PHASE1",
    },
    {
        "id": "T2",
        "path": "docs/audits/architecture/TRADE_ADAPTER_INTEGRATION_PHASE1.md",
        "slice_id": "TRADE_ADAPTER_INTEGRATION_PHASE1",
    },
    {
        "id": "T3",
        "path": "docs/audits/holoindex_search_quality/HOLOINDEX_FOUNDUP_QUERY_ALIAS_AND_TARGETED_VERDICT_PHASE1.md",
        "slice_id": "HOLOINDEX_FOUNDUP_QUERY_ALIAS_AND_TARGETED_VERDICT_PHASE1",
    },
]

# ---------------------------------------------------------------------------
# Chroma client setup (read-only)
# ---------------------------------------------------------------------------


def get_chroma_client(ssd_path: str = "E:/HoloIndex"):
    """Get Chroma PersistentClient (read-only access)."""
    try:
        import chromadb
    except ImportError:
        print("ERROR: chromadb not installed", file=sys.stderr)
        sys.exit(2)

    vector_path = Path(ssd_path) / "vectors"
    if not vector_path.exists():
        print(f"ERROR: Vector path does not exist: {vector_path}", file=sys.stderr)
        sys.exit(2)

    try:
        client = chromadb.PersistentClient(path=str(vector_path))
        return client
    except Exception as e:
        print(f"ERROR: Failed to connect to Chroma: {e}", file=sys.stderr)
        sys.exit(2)


def get_navigation_docs_collection(client):
    """Get navigation_docs collection (read-only)."""
    try:
        collection = client.get_collection("navigation_docs")
        return collection
    except Exception as e:
        print(f"ERROR: navigation_docs collection not found: {e}", file=sys.stderr)
        sys.exit(2)


# ---------------------------------------------------------------------------
# Probe functions (read-only)
# ---------------------------------------------------------------------------


def normalize_path(path: str) -> str:
    """Normalize path for comparison (forward slashes, lowercase)."""
    return path.replace("\\", "/").lower()


def find_doc_by_path(collection, target_path: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """Find a document in the collection by path (partial match).

    Returns: (found: bool, metadata: dict or None)
    """
    target_normalized = normalize_path(target_path)
    target_filename = Path(target_path).name.lower()

    # Query all docs and search for path match
    # This is read-only: collection.get()
    try:
        results = collection.get(include=["metadatas", "documents"])
    except Exception as e:
        print(f"WARN: Failed to get collection data: {e}", file=sys.stderr)
        return False, None

    ids = results.get("ids", [])
    metadatas = results.get("metadatas", [])
    documents = results.get("documents", [])

    for i, meta in enumerate(metadatas):
        if meta is None:
            continue

        # Check various path fields
        source_path = meta.get("source", "")
        path_field = meta.get("path", "")
        title = meta.get("title", "")

        # Try source field
        if source_path:
            source_normalized = normalize_path(source_path)
            if target_filename in source_normalized or target_normalized in source_normalized:
                return True, {
                    "id": ids[i] if i < len(ids) else None,
                    "metadata": meta,
                    "document_preview": (documents[i][:200] if documents and i < len(documents) and documents[i] else None),
                    "matched_via": "source",
                }

        # Try path field
        if path_field:
            path_normalized = normalize_path(path_field)
            if target_filename in path_normalized or target_normalized in path_normalized:
                return True, {
                    "id": ids[i] if i < len(ids) else None,
                    "metadata": meta,
                    "document_preview": (documents[i][:200] if documents and i < len(documents) and documents[i] else None),
                    "matched_via": "path",
                }

        # Try title field
        if title:
            title_normalized = title.lower()
            slice_from_target = Path(target_path).stem.lower()
            if slice_from_target in title_normalized:
                return True, {
                    "id": ids[i] if i < len(ids) else None,
                    "metadata": meta,
                    "document_preview": (documents[i][:200] if documents and i < len(documents) and documents[i] else None),
                    "matched_via": "title",
                }

    return False, None


def check_slice_id_match(metadata: Dict[str, Any], expected_slice_id: str) -> Tuple[bool, str]:
    """Check if slice_id metadata matches expected value.

    Returns: (matches: bool, actual_slice_id: str)
    """
    actual_slice_id = metadata.get("slice_id", "")
    if not actual_slice_id:
        return False, "(absent)"

    if actual_slice_id.upper() == expected_slice_id.upper():
        return True, actual_slice_id

    return False, actual_slice_id


def run_slice_id_query(collection, slice_id: str, n_results: int = 10) -> List[Dict[str, Any]]:
    """Run a semantic query for slice_id and return ranked results.

    This uses collection.query() which is read-only.
    """
    try:
        results = collection.query(
            query_texts=[slice_id],
            n_results=n_results,
            include=["metadatas", "distances"],
        )
    except Exception as e:
        print(f"WARN: Query failed for '{slice_id}': {e}", file=sys.stderr)
        return []

    ranked = []
    ids = results.get("ids", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    for i, doc_id in enumerate(ids):
        ranked.append({
            "rank": i + 1,
            "id": doc_id,
            "distance": distances[i] if i < len(distances) else None,
            "metadata": metadatas[i] if i < len(metadatas) else {},
        })

    return ranked


def classify_target(
    collection, target: Dict[str, str]
) -> Dict[str, Any]:
    """Classify a target document into A/B/C/D/E categories."""
    target_id = target["id"]
    target_path = target["path"]
    expected_slice_id = target["slice_id"]

    result = {
        "target_id": target_id,
        "target_path": target_path,
        "expected_slice_id": expected_slice_id,
        "classification": None,
        "details": {},
    }

    # Step 1: Check if indexed
    found, doc_info = find_doc_by_path(collection, target_path)

    if not found:
        result["classification"] = "A"
        result["details"]["reason"] = "NOT_INDEXED: Document not found in navigation_docs collection"
        return result

    # Document found
    result["details"]["found_via"] = doc_info.get("matched_via", "unknown")
    result["details"]["doc_id"] = doc_info.get("id")
    metadata = doc_info.get("metadata", {})

    # Check for metadata schema issues
    source_field = metadata.get("source", "")
    path_field = metadata.get("path", "")
    if not source_field and not path_field:
        result["classification"] = "E"
        result["details"]["reason"] = "INDEXED_METADATA_UNKNOWN_OR_PATH_SCHEMA_MISMATCH: No source/path field in metadata"
        result["details"]["available_fields"] = list(metadata.keys())
        return result

    # Step 2: Check slice_id metadata
    slice_id_matches, actual_slice_id = check_slice_id_match(metadata, expected_slice_id)
    result["details"]["actual_slice_id"] = actual_slice_id
    result["details"]["slice_id_matches"] = slice_id_matches

    if not slice_id_matches:
        result["classification"] = "B"
        result["details"]["reason"] = f"INDEXED_NO_SLICE_ID: slice_id metadata is '{actual_slice_id}' but expected '{expected_slice_id}'"
        return result

    # Step 3: Run query and check ranking
    query_results = run_slice_id_query(collection, expected_slice_id)
    result["details"]["query_results_count"] = len(query_results)

    # Find target rank
    target_rank = None
    for qr in query_results:
        qr_meta = qr.get("metadata", {})
        qr_source = qr_meta.get("source", "")
        qr_path = qr_meta.get("path", "")
        target_filename = Path(target_path).name.lower()

        if target_filename in normalize_path(qr_source) or target_filename in normalize_path(qr_path):
            target_rank = qr["rank"]
            result["details"]["target_rank"] = target_rank
            result["details"]["target_distance"] = qr.get("distance")
            break

    if target_rank is None:
        # Document exists with correct slice_id but doesn't appear in query results at all
        result["classification"] = "D"
        result["details"]["reason"] = "INDEXED_BUT_BOOST_NOT_APPLIED: Document has correct slice_id but not returned in top-N query results"
        result["details"]["top_3_results"] = [
            {
                "rank": qr["rank"],
                "source": qr.get("metadata", {}).get("source", ""),
                "distance": qr.get("distance"),
            }
            for qr in query_results[:3]
        ]
        return result

    if target_rank > 1:
        # Document appears but outranked
        result["classification"] = "C"
        result["details"]["reason"] = f"INDEXED_WITH_SLICE_ID_OUTRANKED: Target at rank {target_rank}, outranked by other docs"
        result["details"]["outranked_by"] = [
            {
                "rank": qr["rank"],
                "source": qr.get("metadata", {}).get("source", ""),
                "distance": qr.get("distance"),
            }
            for qr in query_results[:target_rank - 1]
        ]
        return result

    # Document is rank 1 — this shouldn't happen if we're debugging failure, but handle it
    result["classification"] = "OK"
    result["details"]["reason"] = "Target correctly surfaces at rank 1"
    return result


def get_collection_stats(collection) -> Dict[str, Any]:
    """Get basic collection statistics (read-only)."""
    try:
        count = collection.count()
        return {"total_documents": count}
    except Exception as e:
        return {"total_documents": -1, "error": str(e)}


# ---------------------------------------------------------------------------
# Main probe execution
# ---------------------------------------------------------------------------


def main():
    print("=" * 60, file=sys.stderr)
    print("HoloIndex Audit Doc Indexing Probe — Phase 1", file=sys.stderr)
    print("READ-ONLY diagnostic: No Chroma mutations", file=sys.stderr)
    print("=" * 60, file=sys.stderr)

    # Connect to Chroma
    client = get_chroma_client()
    collection = get_navigation_docs_collection(client)

    # Get collection stats
    stats = get_collection_stats(collection)
    print(f"\nCollection stats: {stats}", file=sys.stderr)

    # Probe each target
    results = []
    for target in TARGETS:
        print(f"\nProbing {target['id']}: {target['path']}", file=sys.stderr)
        classification = classify_target(collection, target)
        results.append(classification)
        print(f"  -> Classification: {classification['classification']}", file=sys.stderr)
        print(f"  -> Reason: {classification['details'].get('reason', 'N/A')}", file=sys.stderr)

    # Generate summary
    summary = {
        "probe_version": "1.0.0",
        "slice": "HOLOINDEX_AUDIT_DOC_INDEXING_PROBE_PHASE1",
        "collection_name": "navigation_docs",
        "collection_stats": stats,
        "classifications": results,
        "classification_summary": {
            target["id"]: classification["classification"]
            for target, classification in zip(TARGETS, results)
        },
    }

    # Determine next slice recommendation
    classifications = [r["classification"] for r in results]
    if "A" in classifications:
        summary["next_slice_recommendation"] = "A_INDEXING_SOURCE_PATH_POLICY_FIX"
    elif "B" in classifications:
        summary["next_slice_recommendation"] = "B_SLICE_ID_METADATA_EXTRACTION_FIX"
    elif "E" in classifications:
        summary["next_slice_recommendation"] = "E_METADATA_SCHEMA_NORMALIZATION"
    elif "C" in classifications:
        summary["next_slice_recommendation"] = "C_SEARCH_ENGINE_RANKING_BOOST_TUNING"
    elif "D" in classifications:
        summary["next_slice_recommendation"] = "D_SEARCH_ENGINE_BOOST_INTEGRATION_FIX"
    else:
        summary["next_slice_recommendation"] = "NONE_ALL_OK"

    # Output deterministic JSON to stdout
    print(json.dumps(summary, indent=2, sort_keys=True))

    # Human summary to stderr
    print("\n" + "=" * 60, file=sys.stderr)
    print("PROBE SUMMARY", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    for target, classification in zip(TARGETS, results):
        print(f"  {target['id']}: {classification['classification']} — {classification['details'].get('reason', 'N/A')[:60]}", file=sys.stderr)
    print(f"\nRecommended next slice: {summary['next_slice_recommendation']}", file=sys.stderr)
    print("=" * 60, file=sys.stderr)

    sys.exit(0)


if __name__ == "__main__":
    main()
