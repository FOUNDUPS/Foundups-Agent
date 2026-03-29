#!/usr/bin/env python3
"""
Parse 012.txt, extract actionable patterns, and store them in the
HoloIndex PatternMemory (ChromaDB-backed) so Gemma/Qwen can recall them.

Outputs a JSON task list that Qwen (or AI Overseer) can iterate over.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from holo_index.qwen_advisor.pattern_memory import PatternMemory  # noqa: E402
from modules.infrastructure.shared_utilities.corpus_resolver import resolve_corpus_path  # noqa: E402

DEFAULT_012_PATH = resolve_corpus_path(REPO_ROOT)
TASK_EXPORT = REPO_ROOT / "holo_index" / "memory" / "012_pattern_tasks.json"
KEYWORDS = [
    "Option",
    "CRITICAL",
    "Quick Classify",
    "Nested_Module",
    "AI_overseer",
    "PQN",
    "AUTO",
    "Gemma",
    "Skill",
    "WARDROBE",
    "training case",
    "vibecoding",
]


def extract_blocks(text: str) -> List[str]:
    """Split text into blocks and keep ones that look actionable."""
    blocks: List[str] = []
    for raw in text.split("\n\n"):
        block = raw.strip()
        if len(block) < 80:
            continue
        if not any(keyword.lower() in block.lower() for keyword in KEYWORDS):
            continue
        blocks.append(block)
    return blocks


def build_pattern(block: str, index: int) -> Dict:
    """Construct pattern payload compatible with PatternMemory.store_pattern."""
    lines = block.splitlines()
    title = lines[0][:160]
    module_match = re.search(r"(modules[\\/][\w/\\.-]+)", block)
    module = module_match.group(1).replace("\\", "/") if module_match else "unknown"
    keywords = [word for word in KEYWORDS if word.lower() in block.lower()]

    pattern = {
        "id": f"012_{index:04d}",
        "context": block,
        "decision": {
            "summary": title,
            "keywords": keywords,
        },
        "outcome": {
            "status": "pending",
            "notes": "Extracted automatically from 012.txt",
        },
        "module": module,
        "timestamp": datetime.utcnow().isoformat(),
        "verified": False,
        "source": "012.txt",
    }
    return pattern


def main():
    parser = argparse.ArgumentParser(description="Ingest 012.txt patterns into PatternMemory.")
    parser.add_argument(
        "--file",
        type=Path,
        default=DEFAULT_012_PATH,
        help="Path to 012.txt (default: repo root)",
    )
    parser.add_argument(
        "--max",
        type=int,
        default=50,
        help="Maximum number of patterns to ingest",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and print patterns without storing",
    )
    args = parser.parse_args()

    if not args.file.exists():
        raise FileNotFoundError(f"012 file not found: {args.file}")

    text = args.file.read_text(encoding="utf-8", errors="ignore")
    blocks = extract_blocks(text)[: args.max]
    if not blocks:
        print("[WARN] No qualifying blocks found in 012.txt")
        return

    pattern_memory = PatternMemory()
    stored = 0
    tasks: List[Dict] = []

    for idx, block in enumerate(blocks, 1):
        pattern = build_pattern(block, idx)
        if args.dry_run:
            print(f"\n--- Pattern {pattern['id']} ---\n{pattern['context']}\n")
            continue

        if pattern_memory.store_pattern(pattern):
            stored += 1
            suggested_query = pattern["decision"]["summary"]
            tasks.append(
                {
                    "pattern_id": pattern["id"],
                    "suggested_query": suggested_query,
                    "module": pattern["module"],
                    "source": pattern["source"],
                }
            )

    if args.dry_run:
        print(f"\n[DRY-RUN] {len(blocks)} blocks parsed.")
        return

    TASK_EXPORT.parent.mkdir(parents=True, exist_ok=True)
    TASK_EXPORT.write_text(json.dumps(tasks, indent=2), encoding="utf-8")

    print(f"[OK] Stored {stored} patterns from 012.txt into PatternMemory.")
    print(f"[OK] Exported {len(tasks)} Qwen task seeds to {TASK_EXPORT}")


if __name__ == "__main__":
    main()
