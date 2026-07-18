"""Canonical source-set identities for truthful HoloIndex refresh proofs."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Iterable


CANONICAL_SOURCE_SCOPE_IDS: dict[str, str] = {
    "navigation_code": "holoindex.navigation_code.navigation-plus-tracked-public.v1",
    "navigation_symbols": "holoindex.navigation_symbols.tracked-modules-scripts-holo.v1",
    "navigation_wsp": "holoindex.navigation_wsp.tracked-framework-src.v1",
    "navigation_tests": "holoindex.navigation_tests.canonical-registry.v1",
    "navigation_skills": "holoindex.navigation_skills.tracked-skillz-patterns.v1",
    "navigation_docs": "holoindex.navigation_docs.tracked-document-roots.v1",
    "navigation_knowledge": "holoindex.navigation_knowledge.tracked-papers.v1",
}

CANONICAL_SYMBOL_RELATIVE_ROOTS = ("modules", "scripts", "holo_index")
CANONICAL_WSP_RELATIVE_ROOTS = ("WSP_framework/src",)
CANONICAL_WEB_RELATIVE_ROOTS = ("public",)
CANONICAL_WEB_EXTENSIONS = frozenset(
    {".html", ".js", ".mjs", ".cjs", ".jsx", ".ts", ".tsx", ".css"}
)


class CanonicalSourceScopeError(RuntimeError):
    """Canonical Git source discovery could not be proven."""


def canonical_source_scope_id(collection_name: str) -> str:
    """Return the stable canonical source-set identity for a baseline collection."""

    return CANONICAL_SOURCE_SCOPE_IDS.get(collection_name, "")


def normalized_relative_roots(
    project_root: Path,
    roots: Iterable[Path],
) -> tuple[str, ...]:
    """Normalize roots for exact source-policy comparison."""

    root = project_root.resolve(strict=False)
    normalized: set[str] = set()
    for candidate in roots:
        resolved = candidate.resolve(strict=False)
        try:
            value = resolved.relative_to(root).as_posix()
        except ValueError:
            value = resolved.as_posix()
        normalized.add(value.rstrip("/"))
    return tuple(sorted(normalized, key=str.casefold))


def filter_git_tracked_files(
    project_root: Path,
    files: Iterable[Path],
) -> list[Path]:
    """Filter canonical sources to Git-tracked files when repository metadata exists.

    Trusted maintenance proves an exact Git HEAD. Ignored files are not represented
    by that HEAD, so they cannot participate in a canonical source proof. A
    non-repository unit-test fixture falls back to its declared files; the real
    maintenance boundary separately requires a proven Git repository state.
    """

    root = project_root.resolve(strict=False)
    candidates = sorted(
        {path.resolve(strict=False) for path in files},
        key=lambda path: path.as_posix().casefold(),
    )
    if not (root / ".git").exists():
        return candidates
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "ls-files", "-z"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=30,
            shell=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise CanonicalSourceScopeError(
            "HOLOINDEX_GIT_SOURCE_DISCOVERY_FAILED"
        ) from exc
    if result.returncode != 0:
        raise CanonicalSourceScopeError(
            f"HOLOINDEX_GIT_SOURCE_DISCOVERY_FAILED:{result.returncode}"
        )
    tracked = {
        os.path.normcase(str((root / os.fsdecode(raw)).resolve(strict=False)))
        for raw in result.stdout.split(b"\0")
        if raw
    }
    return [
        path for path in candidates
        if os.path.normcase(str(path)) in tracked
    ]


__all__ = [
    "CANONICAL_SOURCE_SCOPE_IDS",
    "CANONICAL_SYMBOL_RELATIVE_ROOTS",
    "CANONICAL_WEB_EXTENSIONS",
    "CANONICAL_WEB_RELATIVE_ROOTS",
    "CANONICAL_WSP_RELATIVE_ROOTS",
    "CanonicalSourceScopeError",
    "canonical_source_scope_id",
    "filter_git_tracked_files",
    "normalized_relative_roots",
]
