#!/usr/bin/env python3
"""
MCP Bridge HoloIndex Tools.

Integrates HoloIndex read capabilities for recall/memory layer.

Tools:
- holo_search: Semantic search across repo
- holo_related: Find related modules
- holo_failure_memory: Recall failure patterns
- holo_pattern_search: Search learned patterns
- holo_task_packet: Assemble context for tasks

Falls back to existing tools when HoloIndex unavailable.

WSP References:
- WSP 48: Recursive Self-Improvement (pattern memory)
- WSP 93: CodeIndex Surgical Intelligence
"""

from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .response_schema import ok_response, error_response

logger = logging.getLogger(__name__)

# HoloIndex availability flag
_HOLOINDEX_AVAILABLE = None
_HOLOINDEX_INSTANCE = None


def _get_holoindex(repo_root: Path):
    """Get or create HoloIndex instance."""
    global _HOLOINDEX_AVAILABLE, _HOLOINDEX_INSTANCE

    if _HOLOINDEX_AVAILABLE is False:
        return None

    if _HOLOINDEX_INSTANCE is not None:
        return _HOLOINDEX_INSTANCE

    try:
        # Try to import and instantiate HoloIndex
        import sys
        holo_path = repo_root / "holo_index"
        if str(holo_path) not in sys.path:
            sys.path.insert(0, str(holo_path.parent))

        from holo_index.core.holo_index import HoloIndex

        # Check for SSD path
        ssd_path = os.getenv("HOLO_SSD_PATH", "E:/HoloIndex")
        if not Path(ssd_path).exists():
            ssd_path = str(repo_root / "holo_index" / ".ssd")

        _HOLOINDEX_INSTANCE = HoloIndex(ssd_path=ssd_path, quiet=True)
        _HOLOINDEX_AVAILABLE = True
        logger.info("[MCP] HoloIndex initialized successfully")
        return _HOLOINDEX_INSTANCE

    except Exception as e:
        logger.warning(f"[MCP] HoloIndex not available: {e}")
        _HOLOINDEX_AVAILABLE = False
        return None


# =============================================================================
# Tool 1: Semantic Search
# =============================================================================


def holo_search(
    repo_root: Path,
    query: str,
    scope: str = "all",
    top_k: int = 10,
) -> Dict[str, Any]:
    """
    Semantic search across the repository.

    Args:
        repo_root: Repository root path
        query: Search query
        scope: Search scope ("all", "code", "wsp", "test", "skill")
        top_k: Maximum results to return

    Returns:
        MCPResponse with search results
    """
    if not query or not query.strip():
        return error_response("Query cannot be empty")

    holo = _get_holoindex(repo_root)
    source = "holoindex"
    confidence = 0.8

    if holo:
        try:
            # Use real HoloIndex search
            results = holo.search(query, limit=top_k, doc_type_filter=scope)

            hits = []
            # Combine all hit types
            for hit in results.get("code_hits", [])[:top_k]:
                hits.append({
                    "type": "code",
                    "path": hit.get("path") or hit.get("location"),
                    "relevance": _parse_similarity(hit.get("similarity", "0%")),
                    "preview": hit.get("preview", "")[:200],
                    "need": hit.get("need", ""),
                })

            for hit in results.get("wsp_hits", [])[:top_k]:
                hits.append({
                    "type": "wsp",
                    "path": hit.get("path"),
                    "title": hit.get("title"),
                    "summary": hit.get("summary", "")[:200],
                    "relevance": _parse_similarity(hit.get("similarity", "0%")),
                })

            for hit in results.get("test_hits", [])[:top_k]:
                hits.append({
                    "type": "test",
                    "path": hit.get("path"),
                    "relevance": _parse_similarity(hit.get("similarity", "0%")),
                })

            for hit in results.get("skill_hits", [])[:top_k]:
                hits.append({
                    "type": "skill",
                    "path": hit.get("path"),
                    "name": hit.get("name"),
                    "relevance": _parse_similarity(hit.get("similarity", "0%")),
                })

            # Sort by relevance and limit
            hits.sort(key=lambda x: x.get("relevance", 0), reverse=True)
            hits = hits[:top_k]

            return ok_response(
                {
                    "query": query,
                    "scope": scope,
                    "hits": hits,
                    "hit_count": len(hits),
                    "metadata": results.get("metadata", {}),
                },
                source=source,
                confidence=confidence,
                tool="holo_search",
            )

        except Exception as e:
            logger.warning(f"[MCP] HoloIndex search failed, using fallback: {e}")
            source = "fallback"
            confidence = 0.5

    # Fallback: use ripgrep search
    source = "fallback"
    confidence = 0.4

    from .repo_tools import search_repo
    fallback_result = search_repo(repo_root, query=query, path=".", top_k=top_k)

    if fallback_result.get("status") != "ok":
        return fallback_result

    # Convert fallback results to holo format
    hits = []
    for match in fallback_result["data"].get("matches", []):
        hits.append({
            "type": "code",
            "path": match.get("file"),
            "relevance": 0.5,  # No semantic score in fallback
            "preview": match.get("line", "")[:200],
            "line_num": match.get("line_num"),
        })

    return ok_response(
        {
            "query": query,
            "scope": scope,
            "hits": hits[:top_k],
            "hit_count": len(hits[:top_k]),
            "fallback_note": "Using ripgrep text search (HoloIndex unavailable)",
        },
        source=source,
        confidence=confidence,
        tool="holo_search",
    )


# =============================================================================
# Tool 2: Related Modules
# =============================================================================


def holo_related(
    repo_root: Path,
    target: str,
    relation_type: str = "all",
    limit: int = 10,
) -> Dict[str, Any]:
    """
    Find modules related to target.

    Args:
        repo_root: Repository root path
        target: Target module name or file path
        relation_type: Type of relation ("dependency", "co_change", "failure", "all")
        limit: Maximum results

    Returns:
        MCPResponse with related modules
    """
    related_modules = []
    sources_used = []
    confidence = 0.6

    # Source 1: Dependency graph
    from .dependency_tools import get_module_dependencies, get_reverse_dependencies

    # Get dependencies
    deps = get_module_dependencies(repo_root, module_name=target)
    if deps.get("status") == "ok":
        sources_used.append("dependencies")
        for dep in deps["data"].get("internal_dependencies", [])[:limit]:
            related_modules.append({
                "module": dep["module"],
                "relation": "depends_on",
                "strength": 0.8,
                "import_count": dep.get("import_count", 1),
            })

    # Get reverse deps
    rdeps = get_reverse_dependencies(repo_root, module_name=target)
    if rdeps.get("status") == "ok":
        sources_used.append("reverse_dependencies")
        for dep in rdeps["data"].get("dependents", [])[:limit]:
            related_modules.append({
                "module": dep["module"],
                "relation": "depended_by",
                "strength": 0.7,
                "import_count": dep.get("import_count", 1),
            })

    # Source 2: HoloIndex semantic similarity
    holo = _get_holoindex(repo_root)
    if holo:
        try:
            results = holo.search(f"module {target}", limit=limit, doc_type_filter="code")
            sources_used.append("holoindex_semantic")
            confidence = 0.75

            for hit in results.get("code_hits", [])[:limit]:
                path = hit.get("path", "")
                module = _extract_module_from_path(path)
                if module and module != target:
                    if not any(r["module"] == module for r in related_modules):
                        related_modules.append({
                            "module": module,
                            "relation": "semantic_similar",
                            "strength": _parse_similarity(hit.get("similarity", "0%")),
                            "path": path,
                        })
        except Exception as e:
            logger.debug(f"[MCP] HoloIndex semantic search failed: {e}")

    # Source 3: Co-change analysis (recent commits)
    from .diff_tools import get_diff_summary

    try:
        diff_result = get_diff_summary(repo_root, commit_range="HEAD~20..HEAD")
        if diff_result.get("status") == "ok":
            sources_used.append("co_change")
            grouped = diff_result["data"].get("grouped_by_module", {})
            target_key = None
            for key in grouped:
                if target in key:
                    target_key = key
                    break

            if target_key:
                # Find other modules changed in same commits
                for key, files in grouped.items():
                    module = key.split("/")[-1] if "/" in key else key
                    if module != target and module not in ["root", "docs", "wsp_framework"]:
                        if not any(r["module"] == module for r in related_modules):
                            related_modules.append({
                                "module": module,
                                "relation": "co_changed",
                                "strength": 0.5,
                                "files_changed": len(files),
                            })
    except Exception:
        pass

    # Deduplicate and sort by strength
    seen = set()
    unique_related = []
    for r in sorted(related_modules, key=lambda x: x.get("strength", 0), reverse=True):
        if r["module"] not in seen:
            seen.add(r["module"])
            unique_related.append(r)

    return ok_response(
        {
            "target": target,
            "relation_type": relation_type,
            "related": unique_related[:limit],
            "related_count": len(unique_related[:limit]),
            "sources_used": sources_used,
        },
        source="holoindex" if "holoindex_semantic" in sources_used else "fallback",
        confidence=confidence,
        tool="holo_related",
    )


# =============================================================================
# Tool 3: Failure Memory
# =============================================================================


def holo_failure_memory(
    repo_root: Path,
    query: str,
    limit: int = 10,
) -> Dict[str, Any]:
    """
    Recall failure patterns related to query.

    Args:
        repo_root: Repository root path
        query: Search query for failures
        limit: Maximum results

    Returns:
        MCPResponse with failure patterns
    """
    failures = []
    sources_used = []
    confidence = 0.5

    # Source 1: Overseer failure patterns (via existing adapter)
    from .failure_adapter import PriorFailureAdapter

    adapter = PriorFailureAdapter(repo_root)
    prior = adapter.get_prior_failures(module_name=query, limit=limit)

    if prior.get("patterns"):
        sources_used.append("overseer_adaptive_learning")
        for p in prior["patterns"]:
            failures.append({
                "pattern": p.get("pattern", ""),
                "module": p.get("module", "unknown"),
                "last_seen": p.get("last_seen", "unknown"),
                "frequency": p.get("frequency", 1),
                "severity": p.get("severity", "unknown"),
                "source": "adaptive_learning",
            })

    # Source 2: HoloIndex pattern memory
    holo = _get_holoindex(repo_root)
    if holo:
        try:
            # Search for failure-related content
            results = holo.search(
                f"error failure {query}",
                limit=limit,
                doc_type_filter="all"
            )
            if results.get("code_hits") or results.get("wsp_hits"):
                sources_used.append("holoindex")
                confidence = 0.65

                for hit in results.get("code_hits", [])[:5]:
                    preview = hit.get("preview", "")
                    if any(kw in preview.lower() for kw in ["error", "fail", "exception", "bug"]):
                        failures.append({
                            "pattern": preview[:100],
                            "module": _extract_module_from_path(hit.get("path", "")),
                            "path": hit.get("path"),
                            "relevance": _parse_similarity(hit.get("similarity", "0%")),
                            "source": "holoindex",
                        })
        except Exception as e:
            logger.debug(f"[MCP] HoloIndex failure search failed: {e}")

    # Source 3: Scan ModLog for failure mentions
    modlog_failures = _scan_modlogs_for_failures(repo_root, query, limit=5)
    if modlog_failures:
        sources_used.append("modlog")
        failures.extend(modlog_failures)

    # Deduplicate
    seen = set()
    unique_failures = []
    for f in failures:
        key = f.get("pattern", "")[:50]
        if key and key not in seen:
            seen.add(key)
            unique_failures.append(f)

    return ok_response(
        {
            "query": query,
            "failures": unique_failures[:limit],
            "failure_count": len(unique_failures[:limit]),
            "sources_used": sources_used,
            "data_note": "No failures found" if not unique_failures else None,
        },
        source="holoindex" if "holoindex" in sources_used else "fallback",
        confidence=confidence,
        tool="holo_failure_memory",
    )


# =============================================================================
# Tool 4: Pattern Search
# =============================================================================


def holo_pattern_search(
    repo_root: Path,
    query: str,
    limit: int = 10,
) -> Dict[str, Any]:
    """
    Search learned patterns.

    Args:
        repo_root: Repository root path
        query: Pattern search query
        limit: Maximum results

    Returns:
        MCPResponse with patterns
    """
    patterns = []
    sources_used = []
    confidence = 0.5

    # Source 1: Adaptive learning JSON files
    adaptive_dir = repo_root / "holo_index" / "adaptive_learning"
    if adaptive_dir.exists():
        sources_used.append("adaptive_learning_files")
        for json_file in adaptive_dir.glob("*.json"):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # Search for patterns matching query
                data_str = json.dumps(data).lower()
                if query.lower() in data_str:
                    patterns.append({
                        "name": json_file.stem,
                        "source_file": str(json_file.relative_to(repo_root)),
                        "type": "learned_pattern",
                        "data_preview": str(data)[:200],
                        "relevance": 0.6,
                    })
            except (json.JSONDecodeError, OSError):
                continue

    # Source 2: HoloIndex ChromaDB pattern memory
    try:
        from holo_index.qwen_advisor.pattern_memory import PatternMemory

        pm = PatternMemory()
        # Query patterns (if method exists)
        if hasattr(pm, "query") or hasattr(pm, "search"):
            sources_used.append("chromadb_patterns")
            confidence = 0.7
            # PatternMemory uses ChromaDB collection query
            if hasattr(pm, "collection"):
                results = pm.collection.query(query_texts=[query], n_results=limit)
                if results and results.get("documents"):
                    for i, doc in enumerate(results["documents"][0]):
                        patterns.append({
                            "pattern": doc[:200],
                            "source": "chromadb",
                            "type": "012_pattern",
                            "relevance": 0.7,
                        })
    except Exception as e:
        logger.debug(f"[MCP] PatternMemory query failed: {e}")

    # Source 3: WSP protocol search
    holo = _get_holoindex(repo_root)
    if holo:
        try:
            results = holo.search(f"pattern {query}", limit=5, doc_type_filter="wsp")
            if results.get("wsp_hits"):
                sources_used.append("holoindex_wsp")
                confidence = max(confidence, 0.65)
                for hit in results["wsp_hits"][:5]:
                    patterns.append({
                        "name": hit.get("title", "WSP"),
                        "wsp": hit.get("wsp"),
                        "summary": hit.get("summary", "")[:200],
                        "path": hit.get("path"),
                        "type": "wsp_pattern",
                        "relevance": _parse_similarity(hit.get("similarity", "0%")),
                    })
        except Exception:
            pass

    return ok_response(
        {
            "query": query,
            "patterns": patterns[:limit],
            "pattern_count": len(patterns[:limit]),
            "sources_used": sources_used,
        },
        source="holoindex" if "holoindex" in str(sources_used) else "fallback",
        confidence=confidence,
        tool="holo_pattern_search",
    )


# =============================================================================
# Tool 5: Task Packet Assembly
# =============================================================================


def holo_task_packet(
    repo_root: Path,
    task_description: str,
    include_patterns: bool = True,
    include_failures: bool = True,
) -> Dict[str, Any]:
    """
    Assemble context packet for a task.

    Args:
        repo_root: Repository root path
        task_description: Description of the task
        include_patterns: Include relevant patterns
        include_failures: Include related failure warnings

    Returns:
        MCPResponse with assembled context
    """
    if not task_description or not task_description.strip():
        return error_response("Task description cannot be empty")

    packet = {
        "task": task_description,
        "relevant_modules": [],
        "relevant_docs": [],
        "relevant_patterns": [],
        "known_risks": [],
        "suggested_wsp": [],
        "confidence": 0.5,
    }

    sources_used = []

    # Step 1: Search for relevant code/modules
    search_result = holo_search(repo_root, query=task_description, scope="all", top_k=10)
    if search_result.get("status") == "ok":
        sources_used.append("holo_search")
        for hit in search_result["data"].get("hits", [])[:5]:
            if hit.get("type") == "code":
                module = _extract_module_from_path(hit.get("path", ""))
                if module and module not in packet["relevant_modules"]:
                    packet["relevant_modules"].append({
                        "module": module,
                        "path": hit.get("path"),
                        "relevance": hit.get("relevance", 0.5),
                    })
            elif hit.get("type") == "wsp":
                packet["suggested_wsp"].append({
                    "title": hit.get("title"),
                    "path": hit.get("path"),
                    "summary": hit.get("summary"),
                })

    # Step 2: Get related modules for top hits
    if packet["relevant_modules"]:
        top_module = packet["relevant_modules"][0]["module"]
        related_result = holo_related(repo_root, target=top_module, limit=5)
        if related_result.get("status") == "ok":
            sources_used.append("holo_related")
            for rel in related_result["data"].get("related", [])[:3]:
                if rel["module"] not in [m["module"] for m in packet["relevant_modules"]]:
                    packet["relevant_modules"].append({
                        "module": rel["module"],
                        "relation": rel.get("relation"),
                        "relevance": rel.get("strength", 0.5),
                    })

    # Step 3: Get relevant docs
    from .doc_tools import get_module_docs

    for mod_info in packet["relevant_modules"][:3]:
        doc_result = get_module_docs(repo_root, module_name=mod_info["module"])
        if doc_result.get("status") == "ok" and doc_result["data"].get("readme"):
            packet["relevant_docs"].append({
                "module": mod_info["module"],
                "doc_type": "readme",
                "excerpt": doc_result["data"]["readme"][:300],
            })

    # Step 4: Get patterns if requested
    if include_patterns:
        pattern_result = holo_pattern_search(repo_root, query=task_description, limit=5)
        if pattern_result.get("status") == "ok":
            sources_used.append("holo_pattern_search")
            packet["relevant_patterns"] = pattern_result["data"].get("patterns", [])[:3]

    # Step 5: Get failure warnings if requested
    if include_failures:
        failure_result = holo_failure_memory(repo_root, query=task_description, limit=5)
        if failure_result.get("status") == "ok":
            sources_used.append("holo_failure_memory")
            for f in failure_result["data"].get("failures", [])[:3]:
                packet["known_risks"].append({
                    "risk": f.get("pattern", "Unknown"),
                    "module": f.get("module"),
                    "severity": f.get("severity", "unknown"),
                })

    # Compute overall confidence
    packet["confidence"] = _compute_packet_confidence(packet, sources_used)

    return ok_response(
        packet,
        source="holoindex" if any("holo" in s for s in sources_used) else "fallback",
        confidence=packet["confidence"],
        tool="holo_task_packet",
        sources_used=sources_used,
    )


# =============================================================================
# Helper Functions
# =============================================================================


def _parse_similarity(sim_str: str) -> float:
    """Parse similarity string like '85.1%' to float 0.851."""
    try:
        if isinstance(sim_str, (int, float)):
            return float(sim_str) if sim_str <= 1 else sim_str / 100
        if "%" in str(sim_str):
            return float(sim_str.replace("%", "")) / 100
        return float(sim_str)
    except (ValueError, TypeError):
        return 0.0


def _extract_module_from_path(path: str) -> Optional[str]:
    """Extract module name from file path."""
    if not path:
        return None
    match = re.match(r"modules[/\\][^/\\]+[/\\]([^/\\]+)", path)
    if match:
        return match.group(1)
    return None


def _scan_modlogs_for_failures(
    repo_root: Path,
    query: str,
    limit: int = 5,
) -> List[Dict]:
    """Scan ModLog files for failure mentions."""
    failures = []
    query_lower = query.lower()

    # Check root ModLog
    root_modlog = repo_root / "ModLog.md"
    if root_modlog.exists():
        failures.extend(_extract_failures_from_modlog(root_modlog, query_lower, repo_root))

    # Check module ModLogs
    modules_dir = repo_root / "modules"
    if modules_dir.exists():
        for modlog in modules_dir.rglob("ModLog.md"):
            if len(failures) >= limit:
                break
            failures.extend(_extract_failures_from_modlog(modlog, query_lower, repo_root))

    return failures[:limit]


def _extract_failures_from_modlog(
    modlog_path: Path,
    query: str,
    repo_root: Path,
) -> List[Dict]:
    """Extract failure mentions from a ModLog file."""
    failures = []
    try:
        with open(modlog_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        # Look for failure-related entries
        lines = content.split("\n")
        for i, line in enumerate(lines):
            line_lower = line.lower()
            if any(kw in line_lower for kw in ["fix", "bug", "error", "fail", "issue", "broken"]):
                if query in line_lower or query in lines[max(0, i - 2):i + 3]:
                    failures.append({
                        "pattern": line.strip()[:100],
                        "source": str(modlog_path.relative_to(repo_root)),
                        "source_type": "modlog",
                        "relevance": 0.4,
                    })
                    if len(failures) >= 3:
                        break
    except OSError:
        pass

    return failures


def _compute_packet_confidence(packet: Dict, sources_used: List[str]) -> float:
    """Compute confidence for task packet."""
    confidence = 0.3  # Base

    # More sources = higher confidence
    confidence += min(len(sources_used) * 0.1, 0.3)

    # More modules = higher confidence
    if packet.get("relevant_modules"):
        confidence += min(len(packet["relevant_modules"]) * 0.05, 0.15)

    # Patterns found = higher confidence
    if packet.get("relevant_patterns"):
        confidence += 0.1

    # HoloIndex used = higher confidence
    if any("holo" in s for s in sources_used):
        confidence += 0.1

    return min(confidence, 0.95)
