# -*- coding: utf-8 -*-
"""TQ Corpus Freeze — deterministic corpus fingerprinting for TQ2/TQ3 audits.

Purpose:
    Provide a reproducible corpus freeze mechanism that blocks TQ2/TQ3
    promotion audits unless the audited Chroma corpus is unchanged from
    the baseline snapshot. Addresses the drift discovered between TQ2 and
    TQ3 runs (navigation_wsp: 3,446 → 1,916 docs).

Commands:
    snapshot  Create a new corpus manifest with per-collection fingerprints.
    verify    Validate current corpus against a frozen manifest.

Usage::

    # Create freeze manifest
    python holo_index/scripts/benchmarks/tq_corpus_freeze.py snapshot \
        --out docs/audits/holoindex_turboquant/corpus_freeze_manifest.json

    # Verify corpus matches manifest (exits non-zero on drift)
    python holo_index/scripts/benchmarks/tq_corpus_freeze.py verify \
        --manifest docs/audits/holoindex_turboquant/corpus_freeze_manifest.json

Environment:
    TQ_CORPUS_ALLOW_DRIFT=1   Skip verification failure (emergency override only)

WSP: WSP 97 (truth distinction), WSP 15 (scope control).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CHROMA_PATH = Path("E:/HoloIndex/vectors")

TARGET_COLLECTIONS = [
    "navigation_code",
    "navigation_wsp",
    "navigation_tests",
    "navigation_skills",
    "navigation_symbols",
    "navigation_vocabulary",
]


def _get_git_sha() -> str:
    """Get current git HEAD SHA."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent.parent,
        )
        return result.stdout.strip()[:12] if result.returncode == 0 else "unknown"
    except Exception:
        return "unknown"


def _compute_ids_hash(ids: list[str]) -> str:
    """Compute deterministic SHA256 of sorted IDs."""
    sorted_ids = sorted(ids)
    content = "\n".join(sorted_ids).encode("utf-8")
    return hashlib.sha256(content).hexdigest()


def _compute_documents_hash(documents: list[str]) -> str:
    """Compute deterministic SHA256 of sorted documents."""
    if not documents:
        return "empty"
    sorted_docs = sorted(documents)
    content = "\n---DOC_SEPARATOR---\n".join(sorted_docs).encode("utf-8")
    return hashlib.sha256(content).hexdigest()


def _compute_metadatas_hash(metadatas: list[dict]) -> str:
    """Compute deterministic SHA256 of sorted metadata entries."""
    if not metadatas:
        return "empty"
    serialized = [json.dumps(m, sort_keys=True) for m in metadatas]
    sorted_meta = sorted(serialized)
    content = "\n".join(sorted_meta).encode("utf-8")
    return hashlib.sha256(content).hexdigest()


def snapshot_corpus(output_path: Path) -> dict[str, Any]:
    """Create a frozen manifest of the current corpus state.

    Returns the manifest dict and writes it to output_path.
    """
    import chromadb

    client = chromadb.PersistentClient(path=str(CHROMA_PATH))

    manifest: dict[str, Any] = {
        "vector_path": str(CHROMA_PATH),
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_sha": _get_git_sha(),
        "collections": {},
    }

    total_docs = 0
    for coll_name in TARGET_COLLECTIONS:
        try:
            coll = client.get_collection(coll_name)
            result = coll.get(include=["documents", "metadatas"])

            ids = result.get("ids", [])
            documents = result.get("documents", []) or []
            metadatas = result.get("metadatas", []) or []

            count = len(ids)
            total_docs += count

            manifest["collections"][coll_name] = {
                "count": count,
                "ids_sha256": _compute_ids_hash(ids),
                "documents_sha256": _compute_documents_hash(documents),
                "metadatas_sha256": _compute_metadatas_hash(metadatas),
            }
            print(f"  [SNAPSHOT] {coll_name}: {count} docs")

        except Exception as e:
            manifest["collections"][coll_name] = {
                "count": 0,
                "ids_sha256": "missing",
                "documents_sha256": "missing",
                "metadatas_sha256": "missing",
                "error": str(e),
            }
            print(f"  [SNAPSHOT] {coll_name}: ERROR - {e}")

    manifest["total_documents"] = total_docs

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"\n[SNAPSHOT] Manifest written to {output_path}")
    print(f"[SNAPSHOT] Total documents: {total_docs}")
    print(f"[SNAPSHOT] Git SHA: {manifest['git_sha']}")

    return manifest


def verify_corpus(manifest_path: Path) -> tuple[bool, list[str]]:
    """Verify current corpus against a frozen manifest.

    Returns (passed, list_of_drift_messages).
    """
    import chromadb

    if not manifest_path.exists():
        return False, [f"Manifest not found: {manifest_path}"]

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    client = chromadb.PersistentClient(path=str(CHROMA_PATH))

    drifts: list[str] = []

    print(f"[VERIFY] Checking against manifest from {manifest.get('created_at_utc', 'unknown')}")
    print(f"[VERIFY] Manifest git SHA: {manifest.get('git_sha', 'unknown')}")
    print(f"[VERIFY] Current git SHA: {_get_git_sha()}")
    print()

    for coll_name in TARGET_COLLECTIONS:
        expected = manifest.get("collections", {}).get(coll_name)
        if not expected:
            drifts.append(f"{coll_name}: missing from manifest")
            print(f"  [VERIFY] {coll_name}: MISSING FROM MANIFEST")
            continue

        if expected.get("error"):
            print(f"  [VERIFY] {coll_name}: skipped (manifest recorded error)")
            continue

        try:
            coll = client.get_collection(coll_name)
            result = coll.get(include=["documents", "metadatas"])

            ids = result.get("ids", [])
            documents = result.get("documents", []) or []
            metadatas = result.get("metadatas", []) or []

            current_count = len(ids)
            expected_count = expected["count"]

            current_ids_hash = _compute_ids_hash(ids)
            current_docs_hash = _compute_documents_hash(documents)
            current_meta_hash = _compute_metadatas_hash(metadatas)

            coll_drifts = []

            if current_count != expected_count:
                coll_drifts.append(f"count {expected_count} → {current_count}")

            if current_ids_hash != expected["ids_sha256"]:
                coll_drifts.append(f"ids_sha256 changed")

            if current_docs_hash != expected["documents_sha256"]:
                coll_drifts.append(f"documents_sha256 changed")

            if current_meta_hash != expected["metadatas_sha256"]:
                coll_drifts.append(f"metadatas_sha256 changed")

            if coll_drifts:
                drift_msg = f"{coll_name}: {', '.join(coll_drifts)}"
                drifts.append(drift_msg)
                print(f"  [VERIFY] {coll_name}: DRIFT - {', '.join(coll_drifts)}")
            else:
                print(f"  [VERIFY] {coll_name}: OK ({current_count} docs)")

        except Exception as e:
            if expected["count"] == 0:
                print(f"  [VERIFY] {coll_name}: OK (expected empty, still empty)")
            else:
                drifts.append(f"{coll_name}: collection error - {e}")
                print(f"  [VERIFY] {coll_name}: ERROR - {e}")

    passed = len(drifts) == 0

    print()
    if passed:
        print("[VERIFY] PASS - corpus matches frozen manifest")
    else:
        print(f"[VERIFY] FAIL - {len(drifts)} drift(s) detected:")
        for drift in drifts:
            print(f"  - {drift}")

    return passed, drifts


def preflight_check(manifest_path: Path | str) -> None:
    """Preflight check for TQ2/TQ3 audits. Exits non-zero on drift.

    Call this at the start of TQ2/TQ3 audit scripts to enforce corpus stability.
    """
    manifest_path = Path(manifest_path)

    if os.environ.get("TQ_CORPUS_ALLOW_DRIFT") == "1":
        print("[PREFLIGHT] TQ_CORPUS_ALLOW_DRIFT=1 - skipping corpus verification (EMERGENCY OVERRIDE)")
        return

    if not manifest_path.exists():
        print(f"[PREFLIGHT] ABORT - No frozen manifest at {manifest_path}")
        print("[PREFLIGHT] Run: python holo_index/scripts/benchmarks/tq_corpus_freeze.py snapshot --out <path>")
        sys.exit(1)

    passed, drifts = verify_corpus(manifest_path)

    if not passed:
        print()
        print("[PREFLIGHT] ABORT - Corpus drift detected. TQ audit results would be invalid.")
        print("[PREFLIGHT] Options:")
        print("  1. Restore corpus to frozen state and re-run")
        print("  2. Create new frozen manifest if drift is intentional")
        print("  3. Set TQ_CORPUS_ALLOW_DRIFT=1 to override (emergency only)")
        sys.exit(1)

    print("[PREFLIGHT] Corpus verification passed - proceeding with audit")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="TQ Corpus Freeze - deterministic corpus fingerprinting for TQ audits"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    snapshot_parser = subparsers.add_parser("snapshot", help="Create corpus freeze manifest")
    snapshot_parser.add_argument(
        "--out",
        type=Path,
        required=True,
        help="Output path for manifest JSON",
    )

    verify_parser = subparsers.add_parser("verify", help="Verify corpus against manifest")
    verify_parser.add_argument(
        "--manifest",
        type=Path,
        required=True,
        help="Path to frozen manifest JSON",
    )

    args = parser.parse_args()

    if args.command == "snapshot":
        print("[TQ_CORPUS_FREEZE] Creating corpus snapshot...")
        snapshot_corpus(args.out)
        return 0

    elif args.command == "verify":
        print("[TQ_CORPUS_FREEZE] Verifying corpus against manifest...")
        passed, _ = verify_corpus(args.manifest)
        return 0 if passed else 1

    return 1


if __name__ == "__main__":
    sys.exit(main())
