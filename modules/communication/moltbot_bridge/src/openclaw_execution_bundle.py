"""OpenClaw Execution Bundle — HoloIndex-guided context for bounded execution.

This module provides compact, deterministic execution bundles that help
OpenClaw/Kohi make better routing and subroutine choices before acting.

Design:
- Bundles are execution aids, not architecture authorities
- Compact only — no giant context dumps
- Deterministic — same query produces same bundle shape
- Suitable for bounded doer, not open-ended cognition

WSP Compliance:
    WSP 87: Semantic Code Discovery (anti-vibecoding)
    WSP 97: System Execution (bounded retrieval)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ExecutionBundle:
    """Compact execution context retrieved from HoloIndex before acting.

    Fields:
        query: The original request/task being executed
        route: The execution route this bundle supports
        docs: Relevant doc paths (README, INTERFACE, ModLog, etc.)
        patterns: Prior successful patterns from memory/breadcrumbs
        candidate_paths: File paths or modules likely relevant to execution
        constraints: WSP constraints, permission requirements, or limits
        verification_hints: Signals for how to verify successful execution
        confidence: Bundle quality score (0.0-1.0)
        code_hits: Raw HoloIndex code search results (for route consumption)
        wsp_hits: Raw HoloIndex WSP search results (for route consumption)
    """

    query: str
    route: str = ""
    docs: List[str] = field(default_factory=list)
    patterns: List[Dict[str, Any]] = field(default_factory=list)
    candidate_paths: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    verification_hints: List[str] = field(default_factory=list)
    confidence: float = 0.0
    code_hits: List[Dict[str, Any]] = field(default_factory=list)
    wsp_hits: List[Dict[str, Any]] = field(default_factory=list)

    def is_actionable(self) -> bool:
        """Return True if bundle has enough context to guide execution."""
        return self.confidence >= 0.3 or bool(self.candidate_paths)

    def to_compact_dict(self) -> Dict[str, Any]:
        """Serialize to compact dict for logging/inspection."""
        return {
            "query": self.query[:100],
            "route": self.route,
            "docs_count": len(self.docs),
            "patterns_count": len(self.patterns),
            "candidates_count": len(self.candidate_paths),
            "constraints_count": len(self.constraints),
            "confidence": round(self.confidence, 2),
        }


def build_execution_bundle(
    query: str,
    route: str = "",
    *,
    limit: int = 5,
    include_patterns: bool = True,
    include_docs: bool = True,
) -> ExecutionBundle:
    """Build an execution bundle from HoloIndex for the given query.

    Args:
        query: The task or request to retrieve context for
        route: The execution route (e.g., "holo_index", "wre_orchestrator")
        limit: Maximum results per category
        include_patterns: Whether to include breadcrumb patterns
        include_docs: Whether to include doc artifacts

    Returns:
        ExecutionBundle with relevant context for bounded execution
    """
    bundle = ExecutionBundle(query=query, route=route)

    # Phase 1: HoloIndex semantic search for code/WSP matches
    try:
        from holo_index.core.holo_index import HoloIndex

        holo = HoloIndex(quiet=True)
        results = holo.search(query, limit=limit)

        # Store raw hits for route consumption (single search, no duplication)
        code_hits = results.get("code", []) or results.get("code_hits", [])
        wsp_hits = results.get("wsps", []) or results.get("wsp_hits", [])
        bundle.code_hits = code_hits[:limit]
        bundle.wsp_hits = wsp_hits[:3]

        # Extract candidate paths from code hits
        for hit in bundle.code_hits:
            path = hit.get("file") or hit.get("path", "")
            if path:
                bundle.candidate_paths.append(path)

        # Extract WSP constraints from WSP hits
        for hit in bundle.wsp_hits:
            title = hit.get("title", "")
            if title:
                bundle.constraints.append(f"WSP: {title}")

        # Confidence based on match quality
        if bundle.code_hits:
            top_score = bundle.code_hits[0].get("score", 0.5)
            bundle.confidence = min(1.0, top_score)
        elif bundle.wsp_hits:
            bundle.confidence = 0.4

    except ImportError:
        logger.debug("[BUNDLE] HoloIndex not available")
    except Exception as exc:
        logger.debug("[BUNDLE] HoloIndex search failed: %s", exc)

    # Phase 2: Breadcrumb patterns for prior successful executions
    if include_patterns:
        try:
            from modules.infrastructure.database.src.agent_db import AgentDB

            db = AgentDB()
            breadcrumbs = db.get_breadcrumbs(limit=20)

            # Find breadcrumbs related to query keywords
            query_words = set(query.lower().split())
            for crumb in breadcrumbs:
                action = (crumb.get("action") or "").lower()
                crumb_query = (crumb.get("query") or "").lower()
                if query_words & set(action.split()) or query_words & set(crumb_query.split()):
                    bundle.patterns.append({
                        "action": crumb.get("action"),
                        "result": bool(crumb.get("results")),
                        "session": crumb.get("session_id", "")[:8],
                    })
                    if len(bundle.patterns) >= 3:
                        break

        except Exception as exc:
            logger.debug("[BUNDLE] Breadcrumb retrieval failed: %s", exc)

    # Phase 3: Module docs if route suggests specific domain
    if include_docs and route:
        bundle.docs = _infer_docs_for_route(route)

    # Phase 4: Verification hints based on route
    bundle.verification_hints = _infer_verification_hints(route, query)

    return bundle


def _infer_docs_for_route(route: str) -> List[str]:
    """Infer relevant doc paths based on execution route."""
    route_docs = {
        "holo_index": [
            "holo_index/README.md",
            "holo_index/docs/WRE_INTEGRATION_DESIGN.md",
        ],
        "wre_orchestrator": [
            "modules/infrastructure/wre_core/README.md",
            "modules/infrastructure/wre_core/INTERFACE.md",
        ],
        "ai_overseer": [
            "modules/ai_intelligence/ai_overseer/README.md",
        ],
        "youtube_shorts_scheduler": [
            "modules/platform_integration/youtube_scheduler/README.md",
        ],
        "communication": [
            "modules/communication/moltbot_bridge/README.md",
            "modules/communication/moltbot_bridge/INTERFACE.md",
        ],
        "infrastructure": [
            "modules/infrastructure/README.md",
        ],
    }
    return route_docs.get(route, [])


def _infer_verification_hints(route: str, query: str) -> List[str]:
    """Infer verification hints based on route and query."""
    hints = []

    if "status" in query.lower() or "connect" in query.lower():
        hints.append("Check return contains status fields")
    if "search" in query.lower() or "find" in query.lower():
        hints.append("Verify results array is populated")
    if route == "wre_orchestrator":
        hints.append("Confirm WRE preflight passes")
    if route == "holo_index":
        hints.append("Verify code_hits or wsp_hits present")

    return hints[:3]


def retrieve_bundle_for_memory_query(
    query_type: str,
    topic: Optional[str] = None,
) -> ExecutionBundle:
    """Specialized bundle retrieval for memory/recall queries.

    Args:
        query_type: Type of memory query (decisions, sessions, unresolved, etc.)
        topic: Optional topic filter

    Returns:
        ExecutionBundle tailored for memory query execution
    """
    query = f"memory:{query_type}" + (f":{topic}" if topic else "")
    bundle = ExecutionBundle(query=query, route="memory_query")

    # Memory queries have known verification patterns
    bundle.verification_hints = [
        "Check breadcrumbs/sessions returned",
        "Verify time filtering applied correctly",
        "Confirm topic relevance in results",
    ]

    # Memory queries always have high confidence (deterministic)
    bundle.confidence = 0.9

    # Standard constraints for memory access
    bundle.constraints = [
        "WSP 54: Multi-Agent Coordination breadcrumbs",
        "Limit results to prevent context overflow",
    ]

    # Fetch any related breadcrumbs for pattern context
    try:
        from modules.infrastructure.database.src.agent_db import AgentDB

        db = AgentDB()
        recent = db.get_breadcrumbs(limit=5)
        for crumb in recent:
            if crumb.get("action") == query_type or (topic and topic.lower() in str(crumb).lower()):
                bundle.patterns.append({
                    "action": crumb.get("action"),
                    "session": crumb.get("session_id", "")[:8],
                })

    except Exception:
        pass

    return bundle
