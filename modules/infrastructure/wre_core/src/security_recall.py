#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Security Recall - Read-Only Historical Finding Lookup

SEC6 — SECURITY_REMEDIATION_RECALL_READONLY_PHASE1

Given a fingerprint/type, look up prior resolved/false-positive records.
Return historical context and suggested prior outcome.

This is READ-ONLY:
- No code changes
- No auto-fix
- No Qwen/Gemma generation

WSP Compliance:
- WSP 60: Module Memory Architecture (recall patterns)
- WSP 97: Truthful claims (observations only)

Architecture:
- SEC5 stores findings (SecurityPatternMemory)
- SEC6 (this) recalls historical context + suggests outcomes
- Future SEC7+ may add Qwen/Gemma analysis (NOT in this phase)
"""

import logging
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional

from .security_pattern_memory import SecurityPatternMemory, SecurityFinding

logger = logging.getLogger(__name__)


@dataclass
class RecallResult:
    """
    Result of a historical finding recall.

    Contains historical context and suggested outcome based on patterns.
    """

    # Query info
    query_fingerprint: Optional[str] = None
    query_finding_id: Optional[str] = None
    query_type: Optional[str] = None

    # Match info
    match_found: bool = False
    exact_match: bool = False
    similar_matches: int = 0

    # Historical context
    finding: Optional[Dict[str, Any]] = None
    first_seen: Optional[str] = None
    last_seen: Optional[str] = None
    times_seen: int = 0

    # Prior outcomes (for similar findings)
    prior_outcomes: Optional[Dict[str, int]] = None  # {"resolved": N, "false_positive": M, ...}
    total_similar: int = 0

    # Suggested outcome
    suggested_outcome: Optional[str] = None
    suggestion_confidence: float = 0.0
    suggestion_rationale: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class SecurityRecall:
    """
    Security Recall - Read-only historical finding lookup.

    Provides recall of prior vulnerability findings and suggests outcomes
    based on historical patterns. Does NOT perform any remediation.

    Usage:
        memory = SecurityPatternMemory()
        recall = SecurityRecall(memory)

        # Recall by fingerprint
        result = recall.recall_by_fingerprint("abc123...")
        if result.match_found:
            print(f"First seen: {result.first_seen}")
            print(f"Suggested: {result.suggested_outcome}")

        # Recall by finding ID (CVE)
        result = recall.recall_by_finding_id("CVE-2024-001")

        # Recall by type pattern
        result = recall.recall_by_type("snyk", "sql-injection")
    """

    def __init__(self, memory: SecurityPatternMemory):
        """
        Initialize SecurityRecall.

        Args:
            memory: SecurityPatternMemory instance for querying
        """
        self.memory = memory
        logger.info("[SECURITY-RECALL] Initialized - read-only recall service")

    def recall_by_fingerprint(self, fingerprint: str) -> RecallResult:
        """
        Recall finding by exact fingerprint match.

        Args:
            fingerprint: SHA256 fingerprint from SecurityFinding

        Returns:
            RecallResult with historical context and suggested outcome
        """
        result = RecallResult(query_fingerprint=fingerprint)

        finding = self.memory.get_finding_by_fingerprint(fingerprint)

        if not finding:
            logger.debug(
                "[SECURITY-RECALL] No match for fingerprint=%s",
                fingerprint[:8] if fingerprint else "None",
            )
            return result

        result.match_found = True
        result.exact_match = True
        result.finding = finding.to_dict()
        result.first_seen = finding.first_seen
        result.last_seen = finding.last_seen
        result.times_seen = finding.times_seen

        # Get similar findings by finding_id for outcome patterns
        similar = self._get_similar_by_finding_id(finding.finding_id)
        result.similar_matches = len(similar)
        result.total_similar = len(similar)
        result.prior_outcomes = self._compute_outcome_distribution(similar)

        # Suggest outcome
        suggestion = self._suggest_outcome_from_patterns(
            exact_finding=finding,
            similar_findings=similar,
        )
        result.suggested_outcome = suggestion["outcome"]
        result.suggestion_confidence = suggestion["confidence"]
        result.suggestion_rationale = suggestion["rationale"]

        logger.info(
            "[SECURITY-RECALL] Recalled fingerprint=%s, suggested=%s (%.2f)",
            fingerprint[:8],
            result.suggested_outcome,
            result.suggestion_confidence,
        )

        return result

    def recall_by_finding_id(self, finding_id: str) -> RecallResult:
        """
        Recall findings by finding ID (CVE, SNYK-XXX, rule-id).

        Returns aggregated historical context from all matching findings.

        Args:
            finding_id: CVE-XXXX, SNYK-XXX, or other finding identifier

        Returns:
            RecallResult with aggregated history and suggested outcome
        """
        result = RecallResult(query_finding_id=finding_id)

        similar = self._get_similar_by_finding_id(finding_id)

        if not similar:
            logger.debug(
                "[SECURITY-RECALL] No matches for finding_id=%s",
                finding_id,
            )
            return result

        result.match_found = True
        result.exact_match = False  # Multiple matches possible
        result.similar_matches = len(similar)
        result.total_similar = len(similar)

        # Use most recent as primary finding
        most_recent = max(similar, key=lambda f: f.last_seen)
        result.finding = most_recent.to_dict()
        result.first_seen = min(f.first_seen for f in similar)
        result.last_seen = max(f.last_seen for f in similar)
        result.times_seen = sum(f.times_seen for f in similar)

        result.prior_outcomes = self._compute_outcome_distribution(similar)

        # Suggest outcome
        suggestion = self._suggest_outcome_from_patterns(
            exact_finding=None,
            similar_findings=similar,
        )
        result.suggested_outcome = suggestion["outcome"]
        result.suggestion_confidence = suggestion["confidence"]
        result.suggestion_rationale = suggestion["rationale"]

        logger.info(
            "[SECURITY-RECALL] Recalled finding_id=%s, matches=%d, suggested=%s (%.2f)",
            finding_id,
            len(similar),
            result.suggested_outcome,
            result.suggestion_confidence,
        )

        return result

    def recall_by_type(
        self,
        tool: Optional[str] = None,
        category: Optional[str] = None,
        severity: Optional[str] = None,
    ) -> RecallResult:
        """
        Recall findings by type pattern.

        Looks up similar findings matching tool, category, or severity patterns.

        Args:
            tool: Scanner tool (snyk, trivy, semgrep)
            category: Finding category (from title/description keywords)
            severity: Severity level

        Returns:
            RecallResult with aggregated patterns
        """
        result = RecallResult(query_type=f"{tool or '*'}:{category or '*'}:{severity or '*'}")

        similar = self._get_similar_by_type(tool, category, severity)

        if not similar:
            logger.debug(
                "[SECURITY-RECALL] No matches for type pattern tool=%s, category=%s, severity=%s",
                tool,
                category,
                severity,
            )
            return result

        result.match_found = True
        result.exact_match = False
        result.similar_matches = len(similar)
        result.total_similar = len(similar)

        # Use most recent as primary finding
        most_recent = max(similar, key=lambda f: f.last_seen)
        result.finding = most_recent.to_dict()
        result.first_seen = min(f.first_seen for f in similar)
        result.last_seen = max(f.last_seen for f in similar)
        result.times_seen = sum(f.times_seen for f in similar)

        result.prior_outcomes = self._compute_outcome_distribution(similar)

        # Suggest outcome
        suggestion = self._suggest_outcome_from_patterns(
            exact_finding=None,
            similar_findings=similar,
        )
        result.suggested_outcome = suggestion["outcome"]
        result.suggestion_confidence = suggestion["confidence"]
        result.suggestion_rationale = suggestion["rationale"]

        logger.info(
            "[SECURITY-RECALL] Recalled type=%s, matches=%d, suggested=%s (%.2f)",
            result.query_type,
            len(similar),
            result.suggested_outcome,
            result.suggestion_confidence,
        )

        return result

    def get_historical_summary(
        self,
        finding_id: Optional[str] = None,
        fingerprint: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get comprehensive historical summary for a finding.

        Args:
            finding_id: CVE or finding ID
            fingerprint: Exact fingerprint

        Returns:
            Dict with historical timeline, outcomes, and statistics
        """
        findings: List[SecurityFinding] = []

        if fingerprint:
            finding = self.memory.get_finding_by_fingerprint(fingerprint)
            if finding:
                findings.append(finding)
                # Also get similar by finding_id
                similar = self._get_similar_by_finding_id(finding.finding_id)
                findings.extend([f for f in similar if f.fingerprint != fingerprint])

        elif finding_id:
            findings = self._get_similar_by_finding_id(finding_id)

        if not findings:
            return {
                "found": False,
                "query": {"finding_id": finding_id, "fingerprint": fingerprint},
            }

        # Build timeline
        timeline = []
        for f in sorted(findings, key=lambda x: x.first_seen):
            timeline.append({
                "fingerprint": f.fingerprint[:16],
                "target": f.target,
                "first_seen": f.first_seen,
                "last_seen": f.last_seen,
                "times_seen": f.times_seen,
                "status": f.status,
            })

        # Compute statistics
        outcomes = self._compute_outcome_distribution(findings)
        total = sum(outcomes.values())

        return {
            "found": True,
            "finding_id": findings[0].finding_id,
            "tool": findings[0].tool,
            "severity": findings[0].severity,
            "total_occurrences": len(findings),
            "total_times_seen": sum(f.times_seen for f in findings),
            "first_seen_ever": min(f.first_seen for f in findings),
            "last_seen_ever": max(f.last_seen for f in findings),
            "outcome_distribution": outcomes,
            "resolution_rate": (
                (outcomes.get("resolved", 0) + outcomes.get("false_positive", 0)) / total
                if total > 0
                else 0.0
            ),
            "timeline": timeline,
        }

    def _get_similar_by_finding_id(self, finding_id: str) -> List[SecurityFinding]:
        """Get all findings with matching finding_id."""
        cursor = self.memory.conn.cursor()
        cursor.execute(
            "SELECT * FROM security_findings WHERE finding_id = ?",
            (finding_id,)
        )
        return [self.memory._row_to_finding(row) for row in cursor.fetchall()]

    def _get_similar_by_type(
        self,
        tool: Optional[str],
        category: Optional[str],
        severity: Optional[str],
    ) -> List[SecurityFinding]:
        """Get findings matching type pattern."""
        cursor = self.memory.conn.cursor()

        query = "SELECT * FROM security_findings WHERE 1=1"
        params: List[Any] = []

        if tool:
            query += " AND tool = ?"
            params.append(tool.lower())

        if severity:
            query += " AND severity = ?"
            params.append(severity.lower())

        if category:
            # Search in title and description
            query += " AND (title LIKE ? OR description LIKE ?)"
            pattern = f"%{category}%"
            params.extend([pattern, pattern])

        cursor.execute(query, params)
        return [self.memory._row_to_finding(row) for row in cursor.fetchall()]

    def _compute_outcome_distribution(
        self,
        findings: List[SecurityFinding],
    ) -> Dict[str, int]:
        """Compute outcome distribution from findings."""
        outcomes: Dict[str, int] = {
            "open": 0,
            "resolved": 0,
            "false_positive": 0,
            "ignored": 0,
        }

        for f in findings:
            status = f.status.lower()
            if status in outcomes:
                outcomes[status] += 1
            else:
                outcomes[status] = 1

        return outcomes

    def _suggest_outcome_from_patterns(
        self,
        exact_finding: Optional[SecurityFinding],
        similar_findings: List[SecurityFinding],
    ) -> Dict[str, Any]:
        """
        Suggest outcome based on historical patterns.

        Decision logic:
        1. If exact match has status != open, suggest that status
        2. If majority of similar have same non-open status, suggest that
        3. Otherwise, suggest keeping open with low confidence

        Returns:
            Dict with outcome, confidence, rationale
        """
        # Case 1: Exact match with non-open status
        if exact_finding and exact_finding.status != "open":
            return {
                "outcome": exact_finding.status,
                "confidence": 0.95,
                "rationale": f"Exact fingerprint previously marked as {exact_finding.status}",
            }

        # Case 2: Analyze similar findings
        if not similar_findings:
            return {
                "outcome": None,
                "confidence": 0.0,
                "rationale": "No historical data available",
            }

        outcomes = self._compute_outcome_distribution(similar_findings)
        total = sum(outcomes.values())

        if total == 0:
            return {
                "outcome": None,
                "confidence": 0.0,
                "rationale": "No historical data available",
            }

        # Find majority outcome (excluding open)
        non_open = {k: v for k, v in outcomes.items() if k != "open" and v > 0}

        if not non_open:
            # All similar are still open
            return {
                "outcome": "open",
                "confidence": 0.5,
                "rationale": f"All {total} similar findings still open",
            }

        # Get most common non-open outcome
        best_outcome = max(non_open, key=lambda k: non_open[k])
        best_count = non_open[best_outcome]
        confidence = best_count / total

        # Require at least 60% for suggestion
        if confidence < 0.6:
            return {
                "outcome": best_outcome,
                "confidence": confidence,
                "rationale": f"Mixed outcomes: {outcomes}. Weak suggestion based on {best_count}/{total}",
            }

        return {
            "outcome": best_outcome,
            "confidence": confidence,
            "rationale": f"{best_count}/{total} similar findings were {best_outcome}",
        }


def get_security_recall(memory: Optional[SecurityPatternMemory] = None) -> SecurityRecall:
    """
    Factory function to get SecurityRecall instance.

    Args:
        memory: Optional SecurityPatternMemory instance.
                If None, creates new memory with default path.

    Returns:
        SecurityRecall instance
    """
    if memory is None:
        memory = SecurityPatternMemory()
    return SecurityRecall(memory)
