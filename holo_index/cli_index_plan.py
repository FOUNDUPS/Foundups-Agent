"""Deterministic collection planning for HoloIndex maintenance CLI flags."""

from __future__ import annotations

import os
from typing import Any, Mapping

from holo_index.freshness_receipt import BASELINE_QUERY_COLLECTIONS
from holo_index.source_scope import (
    CANONICAL_SYMBOL_RELATIVE_ROOTS,
    CANONICAL_WEB_EXTENSIONS,
    CANONICAL_WEB_RELATIVE_ROOTS,
)


_INDEX_FLAG_ATTRS = (
    "index",
    "index_all",
    "index_code",
    "index_wsp",
    "index_tests",
    "index_symbols",
    "index_skills",
    "index_cli",
    "index_work_ledger",
    "index_docs",
    "index_knowledge",
)
BASELINE_INDEX_COLLECTIONS = BASELINE_QUERY_COLLECTIONS
_COLLECTION_FLAG_ATTRS = {
    "index_code": "navigation_code",
    "index_symbols": "navigation_symbols",
    "index_wsp": "navigation_wsp",
    "index_tests": "navigation_tests",
    "index_skills": "navigation_skills",
    "index_docs": "navigation_docs",
    "index_knowledge": "navigation_knowledge",
    "index_work_ledger": "navigation_work_ledger",
}


def _indexing_flags_requested(args: Any) -> bool:
    return any(bool(getattr(args, attr, False)) for attr in _INDEX_FLAG_ATTRS)


def _selected_index_collections(args: Any) -> set[str]:
    """Return the deterministic collection plan for explicit CLI flags."""

    selected: set[str] = set()
    if bool(getattr(args, "index_all", False) or getattr(args, "index", False)):
        selected.update(BASELINE_INDEX_COLLECTIONS)
    for flag, collection in _COLLECTION_FLAG_ATTRS.items():
        if bool(getattr(args, flag, False)):
            selected.add(collection)
    return selected


def _effective_index_collections(args: Any) -> set[str]:
    """Include deterministic implicit mutations in the declared plan."""

    selected = _selected_index_collections(args)
    auto_symbols = os.getenv("HOLO_SYMBOL_AUTO", "1").lower() in {
        "1", "true", "yes", "on",
    }
    if "navigation_code" in selected and auto_symbols:
        selected.add("navigation_symbols")
    return selected


def _normalized_env_values(raw: str) -> frozenset[str]:
    return frozenset(
        value.strip().replace("\\", "/").removeprefix("./").rstrip("/").lower()
        for value in raw.split(";")
        if value.strip()
    )


def _noncanonical_limit(
    environ: Mapping[str, str],
    name: str,
    canonical: int,
) -> bool:
    if name not in environ:
        return False
    try:
        return int(environ[name].strip()) != canonical
    except ValueError:
        return True


def _baseline_source_scope_violations(
    args: Any,
    environ: Mapping[str, str] | None = None,
) -> list[str]:
    """Return knobs that would make --index/--index-all non-canonical."""

    if not bool(getattr(args, "index", False) or getattr(args, "index_all", False)):
        return []
    env = os.environ if environ is None else environ
    violations: list[str] = []
    for attribute in ("symbol_roots", "wsp_path", "module"):
        if getattr(args, attribute, None):
            violations.append(f"--{attribute.replace('_', '-')}")
    symbol_roots = env.get("HOLO_SYMBOL_ROOTS")
    canonical_symbols = frozenset(value.lower() for value in CANONICAL_SYMBOL_RELATIVE_ROOTS)
    if symbol_roots and _normalized_env_values(symbol_roots) != canonical_symbols:
        violations.append("HOLO_SYMBOL_ROOTS")
    web_roots = env.get("HOLO_WEB_INDEX_ROOTS")
    canonical_web_roots = frozenset(value.lower() for value in CANONICAL_WEB_RELATIVE_ROOTS)
    if web_roots and _normalized_env_values(web_roots) != canonical_web_roots:
        violations.append("HOLO_WEB_INDEX_ROOTS")
    web_extensions = env.get("HOLO_WEB_INDEX_EXTENSIONS")
    if web_extensions and _normalized_env_values(web_extensions) != CANONICAL_WEB_EXTENSIONS:
        violations.append("HOLO_WEB_INDEX_EXTENSIONS")
    if env.get("HOLO_INDEX_WEB", "1").lower() not in {"1", "true", "yes", "on"}:
        violations.append("HOLO_INDEX_WEB")
    for name, canonical in (
        ("HOLO_WEB_INDEX_MAX_FILES", 0),
        ("HOLO_WEB_INDEX_MAX_CHARS", 5000),
        ("HOLO_SYMBOL_MAX_FILES", 0),
        ("HOLO_SYMBOL_MAX_ENTRIES", 0),
    ):
        if _noncanonical_limit(env, name, canonical):
            violations.append(name)
    return sorted(set(violations))


__all__ = [
    "BASELINE_INDEX_COLLECTIONS",
    "_INDEX_FLAG_ATTRS",
    "_effective_index_collections",
    "_baseline_source_scope_violations",
    "_indexing_flags_requested",
    "_selected_index_collections",
]
