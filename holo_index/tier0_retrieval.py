"""Shared, bounded module Tier-0 retrieval rules.

This module contains no repository or collection I/O. It keeps the bundle and
owner semantic paths on one generic README/INTERFACE contract.
"""

from __future__ import annotations

import re
from typing import Iterable, Mapping


TIER0_REQUIRED_DOCS = ("README.md", "INTERFACE.md")
MAX_TIER0_QUERY_CHARS = 4096
MAX_MODULE_COMPONENT_CHARS = 128
MAX_MODULE_PATH_CHARS = 512
_MODULE_PATH_RE = re.compile(r"^modules/([^/]+)/([^/]+)(?:/|$)", re.I)
_EXPLICIT_MODULE_PATH_RE = re.compile(
    r"(?<![A-Za-z0-9_.+/-])"
    r"(modules/([A-Za-z0-9_.+-]{1,128})/([A-Za-z0-9_.+-]{1,128}))"
    r"(?=$|/|[^A-Za-z0-9_.+-])",
    re.I,
)
_MODULE_COMPONENT_RE = re.compile(
    r"^(?:[A-Za-z0-9_+]|[A-Za-z0-9_+][A-Za-z0-9_.+-]*[A-Za-z0-9_+])$"
)


def _valid_module_component(component: str) -> bool:
    """Reject traversal, hidden, whitespace, and control-bearing components."""
    return (
        0 < len(component) <= MAX_MODULE_COMPONENT_CHARS
        and bool(_MODULE_COMPONENT_RE.fullmatch(component))
    )


def module_path_from_hit(item: Mapping[str, object]) -> str:
    """Return ``modules/<domain>/<module>`` from one repository hit."""
    raw = item.get("path") or item.get("file") or item.get("location") or ""
    path = str(raw).replace("\\", "/").strip()
    if len(path) > MAX_MODULE_PATH_CHARS:
        return ""
    match = _MODULE_PATH_RE.match(path)
    if not match:
        return ""
    if not all(_valid_module_component(part) for part in match.groups()):
        return ""
    return f"modules/{match.group(1)}/{match.group(2)}"


def _query_mentions_module(query: str, module_path: str) -> bool:
    query_lower = str(query or "").replace("\\", "/").lower()
    basename = module_path.lower().rsplit("/", 1)[-1]
    exact_name = re.compile(
        rf"(?<![a-z0-9_]){re.escape(basename)}(?![a-z0-9_])"
    )
    words = [part for part in re.split(r"[_-]+", basename) if part]
    phrase = None
    if len(words) > 1:
        phrase = re.compile(
            rf"(?<![a-z0-9]){'[\\s_-]+'.join(map(re.escape, words))}(?![a-z0-9])"
        )
    return bool(exact_name.search(query_lower) or (phrase and phrase.search(query_lower)))


def _explicit_module_paths(query: str) -> set[str]:
    normalized = str(query or "").replace("\\", "/")
    if len(normalized) > MAX_TIER0_QUERY_CHARS:
        return set()
    paths: set[str] = set()
    for match in _EXPLICIT_MODULE_PATH_RE.finditer(normalized):
        domain, module = match.group(2), match.group(3)
        if not _valid_module_component(domain) or not _valid_module_component(module):
            continue
        paths.add(f"modules/{domain.casefold()}/{module.casefold()}")
    return paths


def infer_explicit_module_target(
    query: str, hits: Iterable[Mapping[str, object]]
) -> str | None:
    """Resolve one module explicitly named by the query and evidenced by hits.

    Hit-only inference is intentionally forbidden. A normalized basename or
    full module path must be present in the query, and the resulting module
    path must be unique.
    """
    if len(str(query or "")) > MAX_TIER0_QUERY_CHARS:
        return None
    explicit_paths = _explicit_module_paths(query)
    if explicit_paths:
        return next(iter(explicit_paths)) if len(explicit_paths) == 1 else None
    candidates = {
        module
        for item in hits
        if (module := module_path_from_hit(item))
        and _query_mentions_module(query, module)
    }
    return next(iter(candidates)) if len(candidates) == 1 else None


def module_tier0_paths(module_path: str) -> tuple[str, ...]:
    """Return exact repository-relative Tier-0 paths in canonical order."""
    normalized = str(module_path or "").replace("\\", "/").rstrip("/")
    if len(normalized) > MAX_MODULE_PATH_CHARS:
        return ()
    match = _MODULE_PATH_RE.fullmatch(normalized)
    if not match or not all(
        _valid_module_component(part) for part in match.groups()
    ):
        return ()
    return tuple(f"{normalized}/{name}" for name in TIER0_REQUIRED_DOCS)


__all__ = [
    "MAX_MODULE_COMPONENT_CHARS",
    "MAX_MODULE_PATH_CHARS",
    "MAX_TIER0_QUERY_CHARS",
    "TIER0_REQUIRED_DOCS",
    "infer_explicit_module_target",
    "module_path_from_hit",
    "module_tier0_paths",
]
