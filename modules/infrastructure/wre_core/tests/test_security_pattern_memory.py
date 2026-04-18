"""
Security Pattern Memory Tests

SEC5 — SECURITY_PATTERN_MEMORY_PHASE1

Tests storage and retrieval of vulnerability outcomes.
No remediation learning - observations only.

WSP References:
- WSP 5: Test coverage
- WSP 97: Truthful claims (store observations, not remediation)
"""

import json
import pytest
from pathlib import Path
from datetime import datetime, timezone

from modules.infrastructure.wre_core.src.security_pattern_memory import (
    SecurityPatternMemory,
    SecurityFinding,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def memory(tmp_path):
    """Create isolated SecurityPatternMemory instance."""
    db_path = tmp_path / "test_security_memory.db"
    mem = SecurityPatternMemory(db_path=db_path)
    yield mem
    mem.close()


@pytest.fixture
def sample_finding():
    """Create sample finding."""
    return SecurityFinding(
        fingerprint=SecurityFinding.compute_fingerprint(
            tool="snyk",
            finding_id="SNYK-JS-LODASH-1234",
            target=".",
            package_name="lodash",
        ),
        finding_id="SNYK-JS-LODASH-1234",
        tool="snyk",
        target=".",
        package_name="lodash",
        package_version="4.17.15",
        severity="high",
        title="Prototype Pollution",
        policy_decision="modlog_only",
        requires_012=False,
    )


@pytest.fixture
def critical_finding():
    """Create critical finding that requires 012."""
    return SecurityFinding(
        fingerprint=SecurityFinding.compute_fingerprint(
            tool="trivy",
            finding_id="CVE-2021-44228",
            target=".",
            package_name="log4j",
        ),
        finding_id="CVE-2021-44228",
        tool="trivy",
        target=".",
        package_name="log4j",
        package_version="2.14.0",
        severity="critical",
        title="Log4Shell",
        policy_decision="gate_012",
        requires_012=True,
    )


# =============================================================================
# SecurityFinding Tests
# =============================================================================

class TestSecurityFinding:
    """Tests for SecurityFinding dataclass."""

    def test_compute_fingerprint_deterministic(self):
        """Same inputs produce same fingerprint."""
        fp1 = SecurityFinding.compute_fingerprint("snyk", "CVE-2024-001", ".", "lodash")
        fp2 = SecurityFinding.compute_fingerprint("snyk", "CVE-2024-001", ".", "lodash")

        assert fp1 == fp2
        assert len(fp1) == 32  # SHA256 truncated

    def test_compute_fingerprint_differs_by_tool(self):
        """Different tools produce different fingerprints."""
        fp1 = SecurityFinding.compute_fingerprint("snyk", "CVE-2024-001", ".", "lodash")
        fp2 = SecurityFinding.compute_fingerprint("trivy", "CVE-2024-001", ".", "lodash")

        assert fp1 != fp2

    def test_compute_fingerprint_differs_by_finding(self):
        """Different finding IDs produce different fingerprints."""
        fp1 = SecurityFinding.compute_fingerprint("snyk", "CVE-2024-001", ".", "lodash")
        fp2 = SecurityFinding.compute_fingerprint("snyk", "CVE-2024-002", ".", "lodash")

        assert fp1 != fp2

    def test_to_dict(self, sample_finding):
        """Test finding serialization."""
        data = sample_finding.to_dict()

        assert data["fingerprint"] == sample_finding.fingerprint
        assert data["finding_id"] == "SNYK-JS-LODASH-1234"
        assert data["severity"] == "high"


# =============================================================================
# Store and Retrieve Tests
# =============================================================================

class TestStoreAndRetrieve:
    """Tests for storing and retrieving findings."""

    def test_store_new_finding(self, memory, sample_finding):
        """Store new finding returns True."""
        is_new = memory.store_finding(sample_finding)

        assert is_new is True

    def test_store_duplicate_increments_times_seen(self, memory, sample_finding):
        """Storing same fingerprint increments times_seen."""
        memory.store_finding(sample_finding)
        is_new = memory.store_finding(sample_finding)

        assert is_new is False

        retrieved = memory.get_finding_by_fingerprint(sample_finding.fingerprint)
        assert retrieved.times_seen == 2

    def test_store_three_times(self, memory, sample_finding):
        """Multiple stores increment correctly."""
        memory.store_finding(sample_finding)
        memory.store_finding(sample_finding)
        memory.store_finding(sample_finding)

        retrieved = memory.get_finding_by_fingerprint(sample_finding.fingerprint)
        assert retrieved.times_seen == 3

    def test_get_finding_by_fingerprint(self, memory, sample_finding):
        """Retrieve stored finding."""
        memory.store_finding(sample_finding)

        retrieved = memory.get_finding_by_fingerprint(sample_finding.fingerprint)

        assert retrieved is not None
        assert retrieved.finding_id == "SNYK-JS-LODASH-1234"
        assert retrieved.tool == "snyk"
        assert retrieved.severity == "high"

    def test_get_nonexistent_returns_none(self, memory):
        """Non-existent fingerprint returns None."""
        result = memory.get_finding_by_fingerprint("nonexistent")

        assert result is None


# =============================================================================
# Severity and Policy Tests
# =============================================================================

class TestSeverityAndPolicy:
    """Tests for severity and policy field preservation."""

    def test_severity_preserved(self, memory, sample_finding):
        """Severity field is stored and retrieved correctly."""
        memory.store_finding(sample_finding)

        retrieved = memory.get_finding_by_fingerprint(sample_finding.fingerprint)
        assert retrieved.severity == "high"

    def test_policy_decision_preserved(self, memory, sample_finding):
        """Policy decision field is preserved."""
        memory.store_finding(sample_finding)

        retrieved = memory.get_finding_by_fingerprint(sample_finding.fingerprint)
        assert retrieved.policy_decision == "modlog_only"

    def test_requires_012_preserved(self, memory, critical_finding):
        """requires_012 flag is preserved."""
        memory.store_finding(critical_finding)

        retrieved = memory.get_finding_by_fingerprint(critical_finding.fingerprint)
        assert retrieved.requires_012 is True

    def test_critical_with_gate_012(self, memory, critical_finding):
        """Critical findings store gate_012 policy."""
        memory.store_finding(critical_finding)

        retrieved = memory.get_finding_by_fingerprint(critical_finding.fingerprint)
        assert retrieved.severity == "critical"
        assert retrieved.policy_decision == "gate_012"
        assert retrieved.requires_012 is True


# =============================================================================
# Query Tests
# =============================================================================

class TestQueries:
    """Tests for query methods."""

    def test_list_open_findings(self, memory, sample_finding, critical_finding):
        """List open findings."""
        memory.store_finding(sample_finding)
        memory.store_finding(critical_finding)

        open_findings = memory.list_open_findings()

        assert len(open_findings) == 2

    def test_list_open_findings_min_severity(self, memory, sample_finding, critical_finding):
        """Filter by minimum severity."""
        memory.store_finding(sample_finding)  # high
        memory.store_finding(critical_finding)  # critical

        # Only critical
        critical_only = memory.list_open_findings(min_severity="critical")
        assert len(critical_only) == 1
        assert critical_only[0].severity == "critical"

        # Critical and high
        high_plus = memory.list_open_findings(min_severity="high")
        assert len(high_plus) == 2

    def test_list_open_findings_by_tool(self, memory, sample_finding, critical_finding):
        """Filter by tool."""
        memory.store_finding(sample_finding)  # snyk
        memory.store_finding(critical_finding)  # trivy

        snyk_only = memory.list_open_findings(tool="snyk")
        assert len(snyk_only) == 1
        assert snyk_only[0].tool == "snyk"

    def test_list_findings_requiring_012(self, memory, sample_finding, critical_finding):
        """List findings requiring 012 review."""
        memory.store_finding(sample_finding)  # requires_012=False
        memory.store_finding(critical_finding)  # requires_012=True

        requiring_012 = memory.list_findings_requiring_012()

        assert len(requiring_012) == 1
        assert requiring_012[0].finding_id == "CVE-2021-44228"

    def test_get_repeated_findings(self, memory, sample_finding):
        """Get findings seen multiple times."""
        # Store same finding 3 times
        memory.store_finding(sample_finding)
        memory.store_finding(sample_finding)
        memory.store_finding(sample_finding)

        repeated = memory.get_repeated_findings(min_times=2)

        assert len(repeated) == 1
        assert repeated[0].times_seen == 3


# =============================================================================
# Summary Tests
# =============================================================================

class TestSummary:
    """Tests for summary statistics."""

    def test_summarize_empty(self, memory):
        """Summary of empty database."""
        summary = memory.summarize_findings()

        assert summary["total_findings"] == 0
        assert summary["open_high_critical"] == 0
        assert summary["repeated_findings"] == 0

    def test_summarize_with_findings(self, memory, sample_finding, critical_finding):
        """Summary with stored findings."""
        memory.store_finding(sample_finding)
        memory.store_finding(critical_finding)

        summary = memory.summarize_findings()

        assert summary["total_findings"] == 2
        assert summary["by_severity"]["high"] == 1
        assert summary["by_severity"]["critical"] == 1
        assert summary["by_tool"]["snyk"] == 1
        assert summary["by_tool"]["trivy"] == 1
        assert summary["open_high_critical"] == 2
        assert summary["pending_012_review"] == 1

    def test_summarize_repeated(self, memory, sample_finding):
        """Summary counts repeated findings."""
        memory.store_finding(sample_finding)
        memory.store_finding(sample_finding)

        summary = memory.summarize_findings()

        assert summary["repeated_findings"] == 1


# =============================================================================
# Status Update Tests
# =============================================================================

class TestStatusUpdate:
    """Tests for status updates."""

    def test_update_status_resolved(self, memory, sample_finding):
        """Mark finding as resolved."""
        memory.store_finding(sample_finding)
        result = memory.update_status(sample_finding.fingerprint, "resolved")

        assert result is True

        retrieved = memory.get_finding_by_fingerprint(sample_finding.fingerprint)
        assert retrieved.status == "resolved"

    def test_update_status_false_positive(self, memory, sample_finding):
        """Mark finding as false positive."""
        memory.store_finding(sample_finding)
        memory.update_status(sample_finding.fingerprint, "false_positive")

        retrieved = memory.get_finding_by_fingerprint(sample_finding.fingerprint)
        assert retrieved.status == "false_positive"

    def test_update_status_ignored(self, memory, sample_finding):
        """Mark finding as ignored."""
        memory.store_finding(sample_finding)
        memory.update_status(sample_finding.fingerprint, "ignored")

        retrieved = memory.get_finding_by_fingerprint(sample_finding.fingerprint)
        assert retrieved.status == "ignored"

    def test_update_status_invalid(self, memory, sample_finding):
        """Invalid status raises error."""
        memory.store_finding(sample_finding)

        with pytest.raises(ValueError):
            memory.update_status(sample_finding.fingerprint, "invalid_status")

    def test_update_status_nonexistent(self, memory):
        """Update non-existent finding returns False."""
        result = memory.update_status("nonexistent", "resolved")

        assert result is False


# =============================================================================
# Scan Report Integration Tests
# =============================================================================

class TestScanReportIntegration:
    """Tests for storing from SEC3 scan reports."""

    def test_store_from_scan_report(self, memory):
        """Store findings from scan report."""
        report = {
            "scan_tool": "snyk",
            "target": ".",
            "policy_decision": "modlog_only",
            "requires_012": False,
            "findings": [
                {
                    "vuln_id": "SNYK-001",
                    "severity": "high",
                    "package_name": "lodash",
                    "title": "Test Vuln 1",
                },
                {
                    "vuln_id": "SNYK-002",
                    "severity": "medium",
                    "package_name": "axios",
                    "title": "Test Vuln 2",
                },
            ],
        }

        result = memory.store_from_scan_report(report)

        assert result["new"] == 2
        assert result["updated"] == 0

    def test_store_from_scan_report_updates(self, memory):
        """Second report updates existing findings."""
        report = {
            "scan_tool": "snyk",
            "target": ".",
            "findings": [
                {"vuln_id": "SNYK-001", "severity": "high", "package_name": "lodash"},
            ],
        }

        memory.store_from_scan_report(report)
        result = memory.store_from_scan_report(report)

        assert result["new"] == 0
        assert result["updated"] == 1

    def test_store_from_scan_report_critical_requires_012(self, memory):
        """Critical findings in report set requires_012."""
        report = {
            "scan_tool": "trivy",
            "target": ".",
            "findings": [
                {"vuln_id": "CVE-CRITICAL", "severity": "critical", "package_name": "log4j"},
            ],
        }

        memory.store_from_scan_report(report)

        summary = memory.summarize_findings()
        assert summary["pending_012_review"] == 1


# =============================================================================
# Optional Field Tests
# =============================================================================

class TestOptionalFields:
    """Tests for handling missing optional fields."""

    def test_missing_package_name(self, memory):
        """Finding without package_name doesn't crash."""
        finding = SecurityFinding(
            fingerprint=SecurityFinding.compute_fingerprint("semgrep", "rule-001", "."),
            finding_id="rule-001",
            tool="semgrep",
            target=".",
            severity="medium",
            file_path="src/main.py",
            line_number=42,
            policy_decision="report_only",
            requires_012=False,
        )

        memory.store_finding(finding)
        retrieved = memory.get_finding_by_fingerprint(finding.fingerprint)

        assert retrieved is not None
        assert retrieved.package_name is None
        assert retrieved.file_path == "src/main.py"

    def test_missing_description(self, memory):
        """Finding without description doesn't crash."""
        finding = SecurityFinding(
            fingerprint=SecurityFinding.compute_fingerprint("snyk", "SNYK-001", "."),
            finding_id="SNYK-001",
            tool="snyk",
            target=".",
            severity="low",
            policy_decision="ignore",
            requires_012=False,
        )

        memory.store_finding(finding)
        retrieved = memory.get_finding_by_fingerprint(finding.fingerprint)

        assert retrieved is not None
        assert retrieved.description == ""

    def test_missing_fix_info(self, memory):
        """Finding without fix info doesn't crash."""
        finding = SecurityFinding(
            fingerprint=SecurityFinding.compute_fingerprint("trivy", "CVE-001", "."),
            finding_id="CVE-001",
            tool="trivy",
            target=".",
            severity="high",
            policy_decision="modlog_only",
            requires_012=False,
            # No fix_available or fix_version
        )

        memory.store_finding(finding)
        retrieved = memory.get_finding_by_fingerprint(finding.fingerprint)

        assert retrieved is not None
        assert retrieved.fix_available is False
        assert retrieved.fix_version is None

    def test_with_fix_info(self, memory):
        """Finding with fix info is preserved."""
        finding = SecurityFinding(
            fingerprint=SecurityFinding.compute_fingerprint("snyk", "SNYK-002", ".", "axios"),
            finding_id="SNYK-002",
            tool="snyk",
            target=".",
            package_name="axios",
            severity="high",
            policy_decision="modlog_only",
            requires_012=False,
            fix_available=True,
            fix_version="1.0.1",
        )

        memory.store_finding(finding)
        retrieved = memory.get_finding_by_fingerprint(finding.fingerprint)

        assert retrieved.fix_available is True
        assert retrieved.fix_version == "1.0.1"
