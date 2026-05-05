# -*- coding: utf-8 -*-
"""Collection Health Helper — HIA_AGENTIC_RAG_LIVE_COLLECTION_HEALTH_PHASE2

Inspects HoloIndex collection health to determine Agentic RAG readiness.

WSP 97: Reports truthfully. Missing/empty collections are reported as-is.
If collection access fails, report UNKNOWN rather than assume healthy.

WSP 87: Keep helper small. Do not refactor indexing engine.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .holo_index import HoloIndex


class CollectionHealthStatus(Enum):
    """Health status for a single collection."""

    HEALTHY = "healthy"
    """Collection exists and has documents."""

    EMPTY = "empty"
    """Collection exists but has no documents."""

    MISSING = "missing"
    """Collection does not exist."""

    DEGRADED = "degraded"
    """Collection exists but may have issues (low count, stale, etc.)."""

    UNKNOWN = "unknown"
    """Could not determine collection status (access error)."""


@dataclass
class CollectionHealth:
    """Health status for a single collection."""

    name: str
    count: int = 0
    status: CollectionHealthStatus = CollectionHealthStatus.UNKNOWN
    required_for_agentic_rag: bool = False
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "name": self.name,
            "count": self.count,
            "status": self.status.value,
            "required_for_agentic_rag": self.required_for_agentic_rag,
            "reason": self.reason,
        }


@dataclass
class HoloIndexHealthReport:
    """Overall HoloIndex health report for Agentic RAG readiness."""

    vector_path: str
    collections: List[CollectionHealth] = field(default_factory=list)
    overall_status: CollectionHealthStatus = CollectionHealthStatus.UNKNOWN
    agentic_rag_ready: bool = False
    degraded: bool = False
    reasons: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "vector_path": self.vector_path,
            "collections": [c.to_dict() for c in self.collections],
            "overall_status": self.overall_status.value,
            "agentic_rag_ready": self.agentic_rag_ready,
            "degraded": self.degraded,
            "reasons": self.reasons,
        }

    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)


# Collection requirements for Agentic RAG
# WSP 97: These are the truth boundaries for readiness
REQUIRED_COLLECTIONS = {
    "navigation_code": True,      # Required for code search
    "navigation_wsp": True,       # Required for WSP retrieval
    "navigation_symbols": True,   # Required for symbol lookup
}

OPTIONAL_COLLECTIONS = {
    "navigation_docs": False,       # Optional but recommended
    "navigation_knowledge": False,  # Optional but recommended
    "navigation_tests": False,      # Optional
    "navigation_skills": False,     # Optional
}

ALL_EXPECTED_COLLECTIONS = {**REQUIRED_COLLECTIONS, **OPTIONAL_COLLECTIONS}


def _get_collection_count(holo: "HoloIndex", collection_name: str) -> tuple[int, CollectionHealthStatus, str]:
    """Get count for a collection, returning (count, status, reason).

    Returns:
        Tuple of (count, status, reason).
        - count: Document count or 0 if unavailable
        - status: CollectionHealthStatus
        - reason: Human-readable explanation
    """
    try:
        # Try to get collection from holo instance
        collection = None

        # Map collection names to attributes
        attr_map = {
            "navigation_code": "code_collection",
            "navigation_wsp": "wsp_collection",
            "navigation_tests": "test_collection",
            "navigation_skills": "skill_collection",
            "navigation_symbols": "symbol_collection",
            "navigation_docs": "docs_collection",
            "navigation_knowledge": "knowledge_collection",
        }

        attr_name = attr_map.get(collection_name)
        if attr_name:
            collection = getattr(holo, attr_name, None)

        if collection is None:
            # Collection attribute is None - try direct client access
            client = getattr(holo, "client", None)
            if client:
                try:
                    collection = client.get_collection(collection_name)
                except Exception:
                    return (0, CollectionHealthStatus.MISSING, f"Collection '{collection_name}' not found")
            else:
                # No client available - treat as missing (not unknown)
                return (0, CollectionHealthStatus.MISSING, f"Collection '{collection_name}' not available")

        count = collection.count()

        if count == 0:
            return (0, CollectionHealthStatus.EMPTY, f"Collection '{collection_name}' is empty")
        elif count < 10:
            return (count, CollectionHealthStatus.DEGRADED, f"Collection '{collection_name}' has low count ({count})")
        else:
            return (count, CollectionHealthStatus.HEALTHY, f"Collection '{collection_name}' healthy ({count} docs)")

    except Exception as e:
        return (0, CollectionHealthStatus.UNKNOWN, f"Error accessing '{collection_name}': {str(e)}")


def inspect_holoindex_collection_health(holo: "HoloIndex") -> HoloIndexHealthReport:
    """Inspect HoloIndex collection health for Agentic RAG readiness.

    Args:
        holo: HoloIndex instance to inspect

    Returns:
        HoloIndexHealthReport with collection statuses and overall assessment.

    WSP 97 Rules:
    - Missing or empty navigation_wsp => agentic_rag_ready=False
    - Missing or empty navigation_code => DEGRADED, not ready for full RAG
    - Missing docs/knowledge may be DEGRADED depending on use case
    - All required collections with counts > 0 => agentic_rag_ready=True
    - Never classify UNKNOWN as ready
    """
    vector_path = str(getattr(holo, "vector_path", "unknown"))

    report = HoloIndexHealthReport(
        vector_path=vector_path,
        collections=[],
        overall_status=CollectionHealthStatus.UNKNOWN,
        agentic_rag_ready=False,
        degraded=False,
        reasons=[],
    )

    all_healthy = True
    has_required = True
    has_degraded = False

    # Check all expected collections
    for collection_name, required in ALL_EXPECTED_COLLECTIONS.items():
        count, status, reason = _get_collection_count(holo, collection_name)

        health = CollectionHealth(
            name=collection_name,
            count=count,
            status=status,
            required_for_agentic_rag=required,
            reason=reason,
        )
        report.collections.append(health)

        # Track overall status
        if status == CollectionHealthStatus.UNKNOWN:
            all_healthy = False
            if required:
                has_required = False
                report.reasons.append(f"Required collection '{collection_name}' status unknown")

        elif status == CollectionHealthStatus.MISSING:
            all_healthy = False
            if required:
                has_required = False
                report.reasons.append(f"Required collection '{collection_name}' is missing")
            else:
                has_degraded = True
                report.reasons.append(f"Optional collection '{collection_name}' is missing")

        elif status == CollectionHealthStatus.EMPTY:
            all_healthy = False
            if required:
                has_required = False
                report.reasons.append(f"Required collection '{collection_name}' is empty")
            else:
                has_degraded = True
                report.reasons.append(f"Optional collection '{collection_name}' is empty")

        elif status == CollectionHealthStatus.DEGRADED:
            has_degraded = True
            if required:
                report.reasons.append(f"Required collection '{collection_name}' is degraded")

    # Determine overall status
    if all_healthy and has_required:
        report.overall_status = CollectionHealthStatus.HEALTHY
        report.agentic_rag_ready = True
        if has_degraded:
            report.degraded = True
    elif has_required:
        if has_degraded:
            report.overall_status = CollectionHealthStatus.DEGRADED
            report.agentic_rag_ready = True  # Can still operate but degraded
            report.degraded = True
        else:
            report.overall_status = CollectionHealthStatus.HEALTHY
            report.agentic_rag_ready = True
    else:
        report.overall_status = CollectionHealthStatus.DEGRADED
        report.agentic_rag_ready = False
        report.degraded = True

    return report


def format_health_report(report: HoloIndexHealthReport) -> str:
    """Format health report for human-readable output.

    Args:
        report: HoloIndexHealthReport to format

    Returns:
        Formatted string suitable for CLI output.
    """
    lines = [
        "=" * 60,
        "HoloIndex Collection Health Report",
        "=" * 60,
        f"Vector Path: {report.vector_path}",
        f"Overall Status: {report.overall_status.value.upper()}",
        f"Agentic RAG Ready: {'YES' if report.agentic_rag_ready else 'NO'}",
        f"Degraded: {'YES' if report.degraded else 'NO'}",
        "",
        "Collections:",
        "-" * 40,
    ]

    for collection in report.collections:
        status_icon = {
            CollectionHealthStatus.HEALTHY: "[OK]",
            CollectionHealthStatus.EMPTY: "[EMPTY]",
            CollectionHealthStatus.MISSING: "[MISSING]",
            CollectionHealthStatus.DEGRADED: "[WARN]",
            CollectionHealthStatus.UNKNOWN: "[?]",
        }.get(collection.status, "[?]")

        required_tag = " (REQUIRED)" if collection.required_for_agentic_rag else ""
        lines.append(f"  {status_icon} {collection.name}: {collection.count} docs{required_tag}")

    if report.reasons:
        lines.extend([
            "",
            "Reasons:",
            "-" * 40,
        ])
        for reason in report.reasons:
            lines.append(f"  - {reason}")

    lines.append("=" * 60)

    return "\n".join(lines)
