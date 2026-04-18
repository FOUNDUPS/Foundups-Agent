#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for Security Recall Service

SEC6 — SECURITY_REMEDIATION_RECALL_READONLY_PHASE1

Validates:
- Recall by fingerprint (exact match)
- Recall by finding ID (CVE pattern)
- Recall by type (tool/category/severity)
- Historical summary generation
- Outcome suggestion logic
- Read-only invariant (no mutations from recall)
"""

import gc
import pytest
import tempfile
from pathlib import Path

from modules.infrastructure.wre_core.src.security_pattern_memory import (
    SecurityPatternMemory,
    SecurityFinding,
)
from modules.infrastructure.wre_core.src.security_recall import (
    SecurityRecall,
    RecallResult,
    get_security_recall,
)


@pytest.fixture
def temp_db():
    """Create temporary database for tests."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)

    memory = SecurityPatternMemory(db_path=db_path)
    yield memory

    memory.close()
    gc.collect()  # Windows file lock workaround
    try:
        db_path.unlink()
    except PermissionError:
        pass  # Ignore on Windows


@pytest.fixture
def populated_db(temp_db):
    """Create database with test findings."""
    # Finding 1: Critical CVE, resolved
    f1 = SecurityFinding(
        fingerprint=SecurityFinding.compute_fingerprint(
            "snyk", "CVE-2024-001", ".", "lodash"
        ),
        finding_id="CVE-2024-001",
        tool="snyk",
        target=".",
        package_name="lodash",
        severity="critical",
        title="Prototype Pollution in lodash",
        status="resolved",
        first_seen="2024-01-01T00:00:00Z",
        last_seen="2024-01-15T00:00:00Z",
        times_seen=3,
    )
    temp_db.store_finding(f1)

    # Finding 2: Same CVE, different target, false_positive
    f2 = SecurityFinding(
        fingerprint=SecurityFinding.compute_fingerprint(
            "snyk", "CVE-2024-001", "./sub", "lodash"
        ),
        finding_id="CVE-2024-001",
        tool="snyk",
        target="./sub",
        package_name="lodash",
        severity="critical",
        title="Prototype Pollution in lodash",
        status="false_positive",
        first_seen="2024-02-01T00:00:00Z",
        last_seen="2024-02-10T00:00:00Z",
        times_seen=2,
    )
    temp_db.store_finding(f2)

    # Finding 3: Different CVE, open
    f3 = SecurityFinding(
        fingerprint=SecurityFinding.compute_fingerprint(
            "trivy", "CVE-2024-002", ".", "express"
        ),
        finding_id="CVE-2024-002",
        tool="trivy",
        target=".",
        package_name="express",
        severity="high",
        title="XSS vulnerability in express",
        description="Cross-site scripting vulnerability",
        status="open",
        first_seen="2024-03-01T00:00:00Z",
        last_seen="2024-03-05T00:00:00Z",
        times_seen=1,
    )
    temp_db.store_finding(f3)

    # Finding 4: Semgrep rule, ignored
    f4 = SecurityFinding(
        fingerprint=SecurityFinding.compute_fingerprint(
            "semgrep", "python.lang.security.injection.sql", "./app.py", None
        ),
        finding_id="python.lang.security.injection.sql",
        tool="semgrep",
        target="./app.py",
        file_path="app.py",
        line_number=42,
        severity="high",
        title="SQL Injection vulnerability",
        description="Possible SQL injection",
        status="ignored",
        first_seen="2024-04-01T00:00:00Z",
        last_seen="2024-04-01T00:00:00Z",
        times_seen=1,
    )
    temp_db.store_finding(f4)

    # Finding 5: Another SQL injection instance, resolved
    f5 = SecurityFinding(
        fingerprint=SecurityFinding.compute_fingerprint(
            "semgrep", "python.lang.security.injection.sql", "./api.py", None
        ),
        finding_id="python.lang.security.injection.sql",
        tool="semgrep",
        target="./api.py",
        file_path="api.py",
        line_number=100,
        severity="high",
        title="SQL Injection vulnerability",
        description="Possible SQL injection in API",
        status="resolved",
        first_seen="2024-04-10T00:00:00Z",
        last_seen="2024-04-15T00:00:00Z",
        times_seen=2,
    )
    temp_db.store_finding(f5)

    return temp_db


class TestRecallByFingerprint:
    """Tests for recall_by_fingerprint."""

    def test_exact_match_found(self, populated_db):
        """Should find exact fingerprint match."""
        recall = SecurityRecall(populated_db)
        fingerprint = SecurityFinding.compute_fingerprint(
            "snyk", "CVE-2024-001", ".", "lodash"
        )

        result = recall.recall_by_fingerprint(fingerprint)

        assert result.match_found is True
        assert result.exact_match is True
        assert result.finding is not None
        assert result.finding["finding_id"] == "CVE-2024-001"

    def test_historical_context_populated(self, populated_db):
        """Should populate historical context fields."""
        recall = SecurityRecall(populated_db)
        fingerprint = SecurityFinding.compute_fingerprint(
            "snyk", "CVE-2024-001", ".", "lodash"
        )

        result = recall.recall_by_fingerprint(fingerprint)

        assert result.first_seen == "2024-01-01T00:00:00Z"
        assert result.last_seen == "2024-01-15T00:00:00Z"
        assert result.times_seen == 3

    def test_similar_findings_counted(self, populated_db):
        """Should count similar findings by finding_id."""
        recall = SecurityRecall(populated_db)
        fingerprint = SecurityFinding.compute_fingerprint(
            "snyk", "CVE-2024-001", ".", "lodash"
        )

        result = recall.recall_by_fingerprint(fingerprint)

        # CVE-2024-001 has 2 findings (. and ./sub)
        assert result.similar_matches == 2
        assert result.total_similar == 2

    def test_suggests_resolved_for_resolved_finding(self, populated_db):
        """Should suggest resolved for previously resolved finding."""
        recall = SecurityRecall(populated_db)
        fingerprint = SecurityFinding.compute_fingerprint(
            "snyk", "CVE-2024-001", ".", "lodash"
        )

        result = recall.recall_by_fingerprint(fingerprint)

        assert result.suggested_outcome == "resolved"
        assert result.suggestion_confidence >= 0.9

    def test_no_match_returns_empty_result(self, populated_db):
        """Should return empty result for unknown fingerprint."""
        recall = SecurityRecall(populated_db)

        result = recall.recall_by_fingerprint("nonexistent-fingerprint")

        assert result.match_found is False
        assert result.exact_match is False
        assert result.finding is None
        assert result.suggested_outcome is None


class TestRecallByFindingId:
    """Tests for recall_by_finding_id."""

    def test_finds_all_matching_cve(self, populated_db):
        """Should find all findings with same CVE."""
        recall = SecurityRecall(populated_db)

        result = recall.recall_by_finding_id("CVE-2024-001")

        assert result.match_found is True
        assert result.similar_matches == 2
        # Total times seen = 3 + 2 = 5
        assert result.times_seen == 5

    def test_aggregates_time_span(self, populated_db):
        """Should show earliest first_seen and latest last_seen."""
        recall = SecurityRecall(populated_db)

        result = recall.recall_by_finding_id("CVE-2024-001")

        assert result.first_seen == "2024-01-01T00:00:00Z"
        assert result.last_seen == "2024-02-10T00:00:00Z"

    def test_prior_outcomes_computed(self, populated_db):
        """Should compute prior outcome distribution."""
        recall = SecurityRecall(populated_db)

        result = recall.recall_by_finding_id("CVE-2024-001")

        assert result.prior_outcomes is not None
        assert result.prior_outcomes["resolved"] == 1
        assert result.prior_outcomes["false_positive"] == 1

    def test_no_match_for_unknown_cve(self, populated_db):
        """Should return no match for unknown CVE."""
        recall = SecurityRecall(populated_db)

        result = recall.recall_by_finding_id("CVE-9999-999")

        assert result.match_found is False
        assert result.similar_matches == 0


class TestRecallByType:
    """Tests for recall_by_type."""

    def test_filter_by_tool(self, populated_db):
        """Should filter by tool."""
        recall = SecurityRecall(populated_db)

        result = recall.recall_by_type(tool="semgrep")

        assert result.match_found is True
        assert result.similar_matches == 2  # Two semgrep findings

    def test_filter_by_severity(self, populated_db):
        """Should filter by severity."""
        recall = SecurityRecall(populated_db)

        result = recall.recall_by_type(severity="critical")

        assert result.match_found is True
        assert result.similar_matches == 2  # Two critical findings

    def test_filter_by_category(self, populated_db):
        """Should filter by category keyword in title/description."""
        recall = SecurityRecall(populated_db)

        result = recall.recall_by_type(category="SQL")

        assert result.match_found is True
        assert result.similar_matches == 2  # Two SQL injection findings

    def test_combined_filters(self, populated_db):
        """Should apply multiple filters."""
        recall = SecurityRecall(populated_db)

        result = recall.recall_by_type(tool="semgrep", severity="high")

        assert result.match_found is True
        assert result.similar_matches == 2

    def test_no_match_for_unknown_type(self, populated_db):
        """Should return no match for unknown type."""
        recall = SecurityRecall(populated_db)

        result = recall.recall_by_type(tool="unknown-tool")

        assert result.match_found is False


class TestOutcomeSuggestion:
    """Tests for outcome suggestion logic."""

    def test_suggests_existing_status_for_exact_match(self, populated_db):
        """Exact match with non-open status should suggest that status."""
        recall = SecurityRecall(populated_db)
        fingerprint = SecurityFinding.compute_fingerprint(
            "semgrep", "python.lang.security.injection.sql", "./app.py", None
        )

        result = recall.recall_by_fingerprint(fingerprint)

        assert result.suggested_outcome == "ignored"
        assert result.suggestion_confidence >= 0.9

    def test_mixed_outcomes_lower_confidence(self, populated_db):
        """Mixed outcomes should have lower confidence."""
        recall = SecurityRecall(populated_db)

        result = recall.recall_by_finding_id("CVE-2024-001")

        # 50% resolved, 50% false_positive
        assert result.suggestion_confidence < 0.8

    def test_majority_outcome_suggested(self, populated_db):
        """Should suggest majority outcome from similar findings."""
        recall = SecurityRecall(populated_db)

        # SQL injection: 1 ignored, 1 resolved
        result = recall.recall_by_finding_id("python.lang.security.injection.sql")

        # Both are non-open, should pick one
        assert result.suggested_outcome in ["ignored", "resolved"]

    def test_open_findings_suggest_open(self, populated_db):
        """All open findings should suggest keeping open."""
        recall = SecurityRecall(populated_db)

        result = recall.recall_by_finding_id("CVE-2024-002")

        # Only one finding, still open
        assert result.suggested_outcome == "open"
        assert result.suggestion_confidence <= 0.5

    def test_suggestion_rationale_provided(self, populated_db):
        """Should provide rationale for suggestion."""
        recall = SecurityRecall(populated_db)
        fingerprint = SecurityFinding.compute_fingerprint(
            "snyk", "CVE-2024-001", ".", "lodash"
        )

        result = recall.recall_by_fingerprint(fingerprint)

        assert result.suggestion_rationale is not None
        assert len(result.suggestion_rationale) > 0


class TestHistoricalSummary:
    """Tests for get_historical_summary."""

    def test_summary_by_finding_id(self, populated_db):
        """Should generate summary for finding ID."""
        recall = SecurityRecall(populated_db)

        summary = recall.get_historical_summary(finding_id="CVE-2024-001")

        assert summary["found"] is True
        assert summary["finding_id"] == "CVE-2024-001"
        assert summary["total_occurrences"] == 2
        assert summary["total_times_seen"] == 5

    def test_summary_by_fingerprint(self, populated_db):
        """Should generate summary for fingerprint."""
        recall = SecurityRecall(populated_db)
        fingerprint = SecurityFinding.compute_fingerprint(
            "snyk", "CVE-2024-001", ".", "lodash"
        )

        summary = recall.get_historical_summary(fingerprint=fingerprint)

        assert summary["found"] is True
        # Includes similar findings by finding_id
        assert summary["total_occurrences"] == 2

    def test_timeline_included(self, populated_db):
        """Should include timeline in summary."""
        recall = SecurityRecall(populated_db)

        summary = recall.get_historical_summary(finding_id="CVE-2024-001")

        assert "timeline" in summary
        assert len(summary["timeline"]) == 2

    def test_resolution_rate_computed(self, populated_db):
        """Should compute resolution rate."""
        recall = SecurityRecall(populated_db)

        summary = recall.get_historical_summary(finding_id="CVE-2024-001")

        # 1 resolved + 1 false_positive = 2/2 = 100%
        assert summary["resolution_rate"] == 1.0

    def test_not_found_returns_marker(self, populated_db):
        """Should return found=False for unknown."""
        recall = SecurityRecall(populated_db)

        summary = recall.get_historical_summary(finding_id="UNKNOWN-CVE")

        assert summary["found"] is False


class TestReadOnlyInvariant:
    """Tests verifying recall is read-only."""

    def test_recall_does_not_modify_finding(self, populated_db):
        """Recall should not modify the finding."""
        recall = SecurityRecall(populated_db)
        fingerprint = SecurityFinding.compute_fingerprint(
            "snyk", "CVE-2024-001", ".", "lodash"
        )

        # Get original state
        original = populated_db.get_finding_by_fingerprint(fingerprint)
        original_times_seen = original.times_seen
        original_status = original.status

        # Perform recall
        recall.recall_by_fingerprint(fingerprint)
        recall.recall_by_fingerprint(fingerprint)
        recall.recall_by_fingerprint(fingerprint)

        # Verify unchanged
        after = populated_db.get_finding_by_fingerprint(fingerprint)
        assert after.times_seen == original_times_seen
        assert after.status == original_status

    def test_recall_does_not_add_findings(self, populated_db):
        """Recall should not add new findings."""
        recall = SecurityRecall(populated_db)

        # Count before
        summary_before = populated_db.summarize_findings()
        count_before = summary_before["total_findings"]

        # Perform various recalls
        recall.recall_by_fingerprint("nonexistent")
        recall.recall_by_finding_id("UNKNOWN-CVE")
        recall.recall_by_type(tool="unknown")

        # Count after
        summary_after = populated_db.summarize_findings()
        count_after = summary_after["total_findings"]

        assert count_after == count_before

    def test_recall_does_not_update_timestamps(self, populated_db):
        """Recall should not update last_seen timestamps."""
        recall = SecurityRecall(populated_db)
        fingerprint = SecurityFinding.compute_fingerprint(
            "snyk", "CVE-2024-001", ".", "lodash"
        )

        original = populated_db.get_finding_by_fingerprint(fingerprint)
        original_last_seen = original.last_seen

        recall.recall_by_fingerprint(fingerprint)

        after = populated_db.get_finding_by_fingerprint(fingerprint)
        assert after.last_seen == original_last_seen


class TestRecallResult:
    """Tests for RecallResult dataclass."""

    def test_to_dict(self):
        """Should convert to dictionary."""
        result = RecallResult(
            query_fingerprint="abc123",
            match_found=True,
            suggested_outcome="resolved",
        )

        d = result.to_dict()

        assert d["query_fingerprint"] == "abc123"
        assert d["match_found"] is True
        assert d["suggested_outcome"] == "resolved"

    def test_default_values(self):
        """Should have sensible defaults."""
        result = RecallResult()

        assert result.match_found is False
        assert result.exact_match is False
        assert result.similar_matches == 0
        assert result.times_seen == 0
        assert result.suggestion_confidence == 0.0


class TestFactoryFunction:
    """Tests for get_security_recall factory."""

    def test_creates_with_provided_memory(self, temp_db):
        """Should use provided memory instance."""
        recall = get_security_recall(temp_db)

        assert recall.memory is temp_db

    def test_creates_default_memory(self):
        """Should create default memory if none provided."""
        recall = get_security_recall()

        assert recall.memory is not None
        assert isinstance(recall.memory, SecurityPatternMemory)

        recall.memory.close()


class TestIntegrationWithPatternMemory:
    """Integration tests with SEC5 pattern memory."""

    def test_store_then_recall(self, temp_db):
        """Should recall findings stored via pattern memory."""
        # Store via SEC5
        finding = SecurityFinding(
            fingerprint=SecurityFinding.compute_fingerprint(
                "trivy", "CVE-2025-NEW", ".", "newpkg"
            ),
            finding_id="CVE-2025-NEW",
            tool="trivy",
            target=".",
            package_name="newpkg",
            severity="medium",
            status="open",
        )
        temp_db.store_finding(finding)

        # Recall via SEC6
        recall = SecurityRecall(temp_db)
        result = recall.recall_by_fingerprint(finding.fingerprint)

        assert result.match_found is True
        assert result.finding["finding_id"] == "CVE-2025-NEW"

    def test_status_update_reflected_in_recall(self, temp_db):
        """Should reflect status updates in recall."""
        # Store open finding
        fingerprint = SecurityFinding.compute_fingerprint(
            "snyk", "CVE-2025-STATUS", ".", "pkg"
        )
        finding = SecurityFinding(
            fingerprint=fingerprint,
            finding_id="CVE-2025-STATUS",
            tool="snyk",
            target=".",
            package_name="pkg",
            severity="high",
            status="open",
        )
        temp_db.store_finding(finding)

        # Update status
        temp_db.update_status(fingerprint, "resolved")

        # Recall should reflect new status
        recall = SecurityRecall(temp_db)
        result = recall.recall_by_fingerprint(fingerprint)

        assert result.suggested_outcome == "resolved"
        assert result.suggestion_confidence >= 0.9
