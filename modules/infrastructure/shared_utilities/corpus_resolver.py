"""Shared training corpus path resolver.

Single source of truth for resolving the active training corpus path across
all runtime consumers. Promotes resolve_source_path() from ingest_012_corpus.py
to a shared utility (WSP 84 - evolve, don't duplicate).

Resolution order (deterministic):
    1. OPENCLAW_TRAINING_CORPUS env var — absolute path if given, else repo-relative
    2. <repo_root>/holo_index/data/<corpus_name>
    3. <repo_root>/docs/012_moshpit/<corpus_name>
    4. <repo_root>/012.txt  (final fallback)

Returns:
    Path if a candidate exists, None otherwise.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional


def resolve_corpus_path(repo_root: Path) -> Optional[Path]:
    """Resolve the active training corpus path for *repo_root*.

    Reads ``OPENCLAW_TRAINING_CORPUS`` (default ``"012.txt"``) and walks the
    deterministic fallback chain until a file is found.

    Args:
        repo_root: Absolute path to the repository root.

    Returns:
        The first existing candidate ``Path``, or ``None`` if none found.
    """
    corpus_name = os.getenv("OPENCLAW_TRAINING_CORPUS", "012.txt").strip()

    # If env var is an absolute path, honour it directly.
    if os.path.isabs(corpus_name):
        candidate = Path(corpus_name)
        return candidate if candidate.exists() else None

    candidates = [
        repo_root / corpus_name,
        repo_root / "holo_index" / "data" / corpus_name,
        repo_root / "docs" / "012_moshpit" / corpus_name,
        repo_root / "012.txt",  # final fallback regardless of env var name
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None
