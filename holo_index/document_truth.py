"""Deterministic document-authority policy for current-state retrieval.

This policy does not decide whether prose is factually correct. It separates
canonical current contracts from implementation evidence, vision, and
historical records so a current-status query does not treat every Markdown
artifact as equal authority.
"""

from __future__ import annotations

from pathlib import PurePosixPath
import re
from typing import Any, Mapping


CURRENT_TRUTH = "current_truth"
IMPLEMENTATION_EVIDENCE = "implementation_evidence"
HISTORICAL_RECORD = "historical_record"
VISION = "vision"
UNCLASSIFIED = "unclassified"

_CURRENT_QUERY_TERMS = frozenset({
    "complete", "completed", "current", "done", "implemented", "latest",
    "missing", "now", "operational", "remaining", "status", "today",
    "working",
})
_HISTORICAL_QUERY_TERMS = frozenset({
    "baseline", "before", "earlier", "historical", "history", "last",
    "past", "previous", "previously", "prior", "retrospective", "then",
    "was", "were", "yesterday",
})
_CURRENT_DOCUMENT_NAMES = frozenset({
    "interface.md", "readme.md", "roadmap.md",
})
_HOLO_CURRENT_CONTRACTS = frozenset({
    "holo_index/interface.md",
    "holo_index/memory/readme.md",
    "holo_index/readme.md",
    "holo_index/roadmap.md",
    "holo_index/tests/readme.md",
    "holo_index/adaptive_learning/interface.md",
    "holo_index/adaptive_learning/readme.md",
})
_IMPLEMENTATION_SUFFIXES = frozenset({
    ".c", ".cc", ".cpp", ".cs", ".go", ".h", ".hpp", ".java", ".js",
    ".jsx", ".mjs", ".py", ".rs", ".ts", ".tsx",
})
_EXACT_TARGET = re.compile(
    r"(?:\bPR\s*#?\d+\b|\b(?:HXA|FX|CFZ)\d+\b|"
    r"\b[A-Z][A-Z0-9]*(?:_[A-Z0-9]+){2,}\b)",
    re.IGNORECASE,
)
_YEAR_TARGET = re.compile(r"\b(?:19|20)\d{2}\b")


def _normalized_path(item: Mapping[str, Any]) -> str:
    return str(
        item.get("path") or item.get("file") or item.get("location") or ""
    ).replace("\\", "/").split(":", 1)[0].strip("/")


def classify_document_truth(item: Mapping[str, Any]) -> str:
    """Classify one result by repository role using only bounded metadata."""

    path = _normalized_path(item)
    lowered = path.casefold()
    name = PurePosixPath(path).name.casefold()
    result_type = str(item.get("type") or "").casefold()
    wrapped = f"/{lowered}/"
    if (
        any(segment in wrapped for segment in ("/archive/", "/audits/"))
        or lowered.startswith("holo_index/docs/")
        or name in {"modlog.md", "testmodlog.md"}
    ):
        return HISTORICAL_RECORD
    if PurePosixPath(path).suffix.casefold() in _IMPLEMENTATION_SUFFIXES or result_type in {
        "code", "symbol", "test",
    }:
        return IMPLEMENTATION_EVIDENCE
    if any(term in name for term in ("audit", "categorization", "cleanup")):
        return HISTORICAL_RECORD
    if (
        "foundups_vision" in lowered
        or "/vision/" in wrapped
        or result_type in {"vision", "architecture_vision"}
    ):
        return VISION
    if (
        lowered.startswith("wsp_framework/src/wsp_")
        or lowered in _HOLO_CURRENT_CONTRACTS
        or (
            lowered.startswith("modules/")
            and "/docs/" not in wrapped
            and name in _CURRENT_DOCUMENT_NAMES
        )
        or result_type == "wsp_protocol"
    ):
        return CURRENT_TRUTH
    return UNCLASSIFIED


def query_requests_current_truth(query: str) -> bool:
    """Return true for broad state questions, not exact artifact lookups."""

    text = str(query or "")
    if _EXACT_TARGET.search(text):
        return False
    tokens = frozenset(re.findall(r"[a-z0-9]+", text.casefold()))
    historical = bool(
        tokens.intersection(_HISTORICAL_QUERY_TERMS) or _YEAR_TARGET.search(text)
    )
    if historical:
        return False
    current = bool(tokens.intersection(_CURRENT_QUERY_TERMS))
    return current or "what is" in text.casefold()


def current_truth_rank(query: str, item: Mapping[str, Any]) -> int:
    """Return a stable authority tier for global current-state ordering."""

    if not query_requests_current_truth(query):
        return 0
    return {
        CURRENT_TRUTH: 4,
        IMPLEMENTATION_EVIDENCE: 3,
        UNCLASSIFIED: 2,
        VISION: 1,
        HISTORICAL_RECORD: 0,
    }[classify_document_truth(item)]


__all__ = [
    "CURRENT_TRUTH", "HISTORICAL_RECORD", "IMPLEMENTATION_EVIDENCE",
    "UNCLASSIFIED", "VISION", "classify_document_truth",
    "current_truth_rank", "query_requests_current_truth",
]
