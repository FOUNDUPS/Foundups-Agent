#!/usr/bin/env python3
"""
MCP Bridge Prior Failure Adapter.

Clean interface for HoloIndex failure pattern integration.
Returns empty results when HoloIndex is not available.

This is a boundary interface for Slice 3 HoloIndex integration.

WSP References:
- WSP 48: Recursive Self-Improvement (pattern memory)
- WSP 97: Truthful verification (no fake data)
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class PriorFailureAdapter:
    """
    Adapter for retrieving prior failure patterns.

    Currently returns empty results with appropriate metadata.
    Designed for HoloIndex integration in Slice 3.
    """

    def __init__(self, repo_root: Path):
        """
        Initialize adapter.

        Args:
            repo_root: Repository root path
        """
        self.repo_root = repo_root
        self._holoindex_available = self._check_holoindex_availability()
        self._local_patterns = self._load_local_failure_patterns()

    def _check_holoindex_availability(self) -> bool:
        """Check if HoloIndex is available for queries."""
        # HoloIndex integration point - Slice 3
        # For now, check if the basic structure exists
        holo_dir = self.repo_root / "holo_index"
        return holo_dir.exists()

    def _load_local_failure_patterns(self) -> List[Dict]:
        """
        Load any locally stored failure patterns.

        Sources (in priority order):
        1. modules/ai_intelligence/ai_overseer/adaptive_learning/
        2. holo_index/adaptive_learning/
        """
        patterns = []

        # Check ai_overseer adaptive learning
        overseer_patterns = (
            self.repo_root
            / "modules"
            / "ai_intelligence"
            / "ai_overseer"
            / "adaptive_learning"
        )
        if overseer_patterns.exists():
            patterns.extend(self._scan_pattern_files(overseer_patterns))

        # Check holo_index adaptive learning
        holo_patterns = self.repo_root / "holo_index" / "adaptive_learning"
        if holo_patterns.exists():
            patterns.extend(self._scan_pattern_files(holo_patterns))

        return patterns[:100]  # Limit stored patterns

    def _scan_pattern_files(self, directory: Path) -> List[Dict]:
        """Scan directory for failure pattern files."""
        patterns = []

        for json_file in directory.glob("*.json"):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # Extract failure patterns if present
                if isinstance(data, dict):
                    if "failures" in data:
                        patterns.extend(data["failures"][:10])
                    elif "error_patterns" in data:
                        patterns.extend(data["error_patterns"][:10])
                    elif "failure_patterns" in data:
                        patterns.extend(data["failure_patterns"][:10])

            except (json.JSONDecodeError, OSError):
                continue

        return patterns

    def get_prior_failures(
        self,
        module_name: Optional[str] = None,
        file_path: Optional[str] = None,
        limit: int = 10,
    ) -> Dict[str, Any]:
        """
        Get prior failure patterns for a module or file.

        Args:
            module_name: Module name to search failures for
            file_path: File path to search failures for
            limit: Maximum number of patterns to return

        Returns:
            Failure patterns with metadata
        """
        # Search local patterns for matches
        matched_patterns = []

        search_term = module_name or file_path or ""
        search_term_lower = search_term.lower()

        for pattern in self._local_patterns:
            pattern_str = str(pattern).lower()

            # Check if pattern relates to our search
            if search_term_lower and search_term_lower in pattern_str:
                matched_patterns.append(self._normalize_pattern(pattern))

        # If no specific matches, check for general module patterns
        if not matched_patterns and module_name:
            for pattern in self._local_patterns:
                if isinstance(pattern, dict):
                    if pattern.get("module") == module_name:
                        matched_patterns.append(self._normalize_pattern(pattern))

        return {
            "patterns": matched_patterns[:limit],
            "count": len(matched_patterns),
            "source": "local_adaptive_learning" if matched_patterns else "none",
            "holoindex_available": self._holoindex_available,
            "holoindex_queried": False,  # Slice 3 will set to True
            "confidence_note": self._get_confidence_note(matched_patterns),
        }

    def _normalize_pattern(self, pattern: Any) -> Dict[str, Any]:
        """Normalize pattern to standard format."""
        if isinstance(pattern, dict):
            return {
                "pattern": pattern.get("pattern", pattern.get("error", str(pattern))),
                "last_seen": pattern.get("last_seen", pattern.get("timestamp", "unknown")),
                "frequency": pattern.get("frequency", pattern.get("count", 1)),
                "module": pattern.get("module", "unknown"),
                "severity": pattern.get("severity", "unknown"),
            }
        else:
            return {
                "pattern": str(pattern),
                "last_seen": "unknown",
                "frequency": 1,
                "module": "unknown",
                "severity": "unknown",
            }

    def _get_confidence_note(self, patterns: List) -> str:
        """Generate confidence note based on data availability."""
        if not patterns:
            return "No prior failure data available. Confidence reduced."
        elif len(patterns) < 3:
            return "Limited failure history. Confidence moderately reduced."
        else:
            return "Failure history available from local patterns."


def get_prior_failures_for_modules(
    repo_root: Path,
    modules: List[str],
    limit_per_module: int = 5,
) -> Dict[str, Any]:
    """
    Get prior failure patterns for multiple modules.

    Args:
        repo_root: Repository root path
        modules: List of module names
        limit_per_module: Max patterns per module

    Returns:
        Aggregated failure patterns
    """
    adapter = PriorFailureAdapter(repo_root)
    all_patterns = []
    modules_with_failures = 0

    for module_name in modules:
        result = adapter.get_prior_failures(module_name=module_name, limit=limit_per_module)
        if result["patterns"]:
            modules_with_failures += 1
            all_patterns.extend(result["patterns"])

    # Deduplicate by pattern string
    seen = set()
    unique_patterns = []
    for p in all_patterns:
        pattern_key = p.get("pattern", "")
        if pattern_key not in seen:
            seen.add(pattern_key)
            unique_patterns.append(p)

    return {
        "patterns": unique_patterns[:20],  # Overall limit
        "modules_checked": len(modules),
        "modules_with_failures": modules_with_failures,
        "holoindex_available": adapter._holoindex_available,
        "data_completeness": modules_with_failures / max(len(modules), 1),
    }
