"""
Security Scan Executor Tests

Tests WRE skill wrapper with mocked SEC1/SEC2 dependencies.

WSP References:
- WSP 5: Test coverage
- WSP 97: Truthful reporting verification
"""

import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

from modules.infrastructure.wre_core.skillz.security_scan.executor import (
    SecurityScanExecutor,
    SecurityScanReport,
)


# =============================================================================
# Mock Classes (Simulate SEC1/SEC2)
# =============================================================================

class MockSeverityLevel(Enum):
    """Mock SEC1/SEC2 SeverityLevel."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"
    UNKNOWN = "unknown"

    @classmethod
    def from_string(cls, value: str) -> "MockSeverityLevel":
        try:
            return cls(value.lower())
        except ValueError:
            return cls.UNKNOWN


class MockEscalationDestination(Enum):
    """Mock SEC2 EscalationDestination."""
    GATE_012 = "gate_012"
    MODLOG_ONLY = "modlog_only"
    REPORT_ONLY = "report_only"
    IGNORE = "ignore"


class MockFindingType(Enum):
    """Mock SEC2 FindingType."""
    DEPENDENCY = "dependency"
    SAST = "sast"
    SECRET = "secret"
    UNKNOWN = "unknown"


@dataclass
class MockVulnerabilityFinding:
    """Mock SEC1 finding."""
    vuln_id: str
    title: str
    severity: MockSeverityLevel
    package_name: Optional[str] = None
    fix_available: bool = False
    fix_version: Optional[str] = None


@dataclass
class MockVulnerabilityReport:
    """Mock SEC1 report."""
    findings: List[MockVulnerabilityFinding]
    total_findings: int = 0
    critical_count: int = 0
    high_count: int = 0
    max_severity: MockSeverityLevel = MockSeverityLevel.INFO

    def __post_init__(self):
        if self.findings and self.total_findings == 0:
            self.total_findings = len(self.findings)
            self.critical_count = sum(1 for f in self.findings if f.severity == MockSeverityLevel.CRITICAL)
            self.high_count = sum(1 for f in self.findings if f.severity == MockSeverityLevel.HIGH)
            if self.critical_count > 0:
                self.max_severity = MockSeverityLevel.CRITICAL
            elif self.high_count > 0:
                self.max_severity = MockSeverityLevel.HIGH

    def to_dict(self):
        return {
            "findings": [{"vuln_id": f.vuln_id, "severity": f.severity.value} for f in self.findings],
            "total_findings": self.total_findings,
        }


@dataclass
class MockScanResult:
    """Mock SEC1 scan result."""
    tool: str
    success: bool
    available: bool
    report: Optional[MockVulnerabilityReport] = None
    error_message: Optional[str] = None


@dataclass
class MockToolAvailability:
    """Mock SEC1 tool availability."""
    snyk_available: bool = False
    trivy_available: bool = False
    semgrep_available: bool = False


@dataclass
class MockPolicyDecision:
    """Mock SEC2 policy decision."""
    escalation: MockEscalationDestination
    requires_012: bool
    reason: str


class MockSecurityScanner:
    """Mock SEC1 SecurityScanner."""

    def __init__(self, availability: MockToolAvailability = None):
        self._availability = availability or MockToolAvailability()
        self._scan_results = {}

    def check_tool_availability(self):
        return self._availability

    def set_scan_result(self, tool: str, result: MockScanResult):
        self._scan_results[tool] = result

    def scan_snyk(self, path: str) -> MockScanResult:
        return self._scan_results.get("snyk", MockScanResult(
            tool="snyk",
            success=False,
            available=False,
            error_message="snyk not configured",
        ))

    def scan_trivy(self, path: str) -> MockScanResult:
        return self._scan_results.get("trivy", MockScanResult(
            tool="trivy",
            success=False,
            available=False,
            error_message="trivy not configured",
        ))

    def scan_semgrep(self, path: str) -> MockScanResult:
        return self._scan_results.get("semgrep", MockScanResult(
            tool="semgrep",
            success=False,
            available=False,
            error_message="semgrep not configured",
        ))


class MockVulnerabilityScanPolicy:
    """Mock SEC2 VulnerabilityScanPolicy."""

    def __init__(self):
        self._decisions = {}

    def set_decision(self, severity: str, decision: MockPolicyDecision):
        self._decisions[severity] = decision

    def get_escalation(self, severity, finding_type=None):
        severity_str = severity.value if hasattr(severity, 'value') else str(severity)

        # Default behavior: CRITICAL always gates to 012
        if severity_str == "critical":
            return MockPolicyDecision(
                escalation=MockEscalationDestination.GATE_012,
                requires_012=True,
                reason="CRITICAL severity always requires 012",
            )

        return self._decisions.get(severity_str, MockPolicyDecision(
            escalation=MockEscalationDestination.REPORT_ONLY,
            requires_012=False,
            reason="Default policy",
        ))


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_scanner():
    """Create mock scanner with all tools unavailable."""
    return MockSecurityScanner()


@pytest.fixture
def mock_scanner_snyk_available():
    """Create mock scanner with snyk available."""
    scanner = MockSecurityScanner(MockToolAvailability(snyk_available=True))
    scanner.set_scan_result("snyk", MockScanResult(
        tool="snyk",
        success=True,
        available=True,
        report=MockVulnerabilityReport(findings=[]),
    ))
    return scanner


@pytest.fixture
def mock_policy():
    """Create mock policy."""
    return MockVulnerabilityScanPolicy()


@pytest.fixture
def executor(mock_scanner, mock_policy, tmp_path):
    """Create executor with mocked dependencies."""
    return SecurityScanExecutor(
        scanner=mock_scanner,
        policy=mock_policy,
        reports_dir=tmp_path / "reports",
    )


# =============================================================================
# SecurityScanReport Tests
# =============================================================================

class TestSecurityScanReport:
    """Tests for SecurityScanReport dataclass."""

    def test_to_dict(self):
        """Test report serialization."""
        report = SecurityScanReport(
            generated_at="2026-04-18T12:00:00Z",
            scan_tool="snyk",
            target=".",
            tool_available=True,
            scan_status="completed",
            findings=[],
            policy_decision="report_only",
            requires_012=False,
            recommended_next_action="none",
        )

        data = report.to_dict()

        assert data["scan_tool"] == "snyk"
        assert data["tool_available"] is True
        assert data["requires_012"] is False

    def test_to_json(self):
        """Test JSON serialization."""
        report = SecurityScanReport(
            generated_at="2026-04-18T12:00:00Z",
            scan_tool="trivy",
            target=".",
            tool_available=False,
            scan_status="tool_unavailable",
        )

        json_str = report.to_json()
        parsed = json.loads(json_str)

        assert parsed["scan_tool"] == "trivy"
        assert parsed["tool_available"] is False


# =============================================================================
# Tool Unavailable Tests (WSP 97 Truthful Reporting)
# =============================================================================

class TestToolUnavailable:
    """Tests for truthful reporting when tools unavailable."""

    def test_snyk_unavailable_reports_truthfully(self, executor):
        """Snyk unavailable reports tool_available=false, not failure."""
        report = executor.scan("snyk", ".")

        assert report.tool_available is False
        assert report.scan_status == "tool_unavailable"
        assert "not installed" in report.error_message or "not available" in report.error_message
        assert report.findings == []
        assert report.requires_012 is False

    def test_trivy_unavailable_reports_truthfully(self, executor):
        """Trivy unavailable reports tool_available=false."""
        report = executor.scan("trivy", ".")

        assert report.tool_available is False
        assert report.scan_status == "tool_unavailable"

    def test_semgrep_unavailable_reports_truthfully(self, executor):
        """Semgrep unavailable reports tool_available=false."""
        report = executor.scan("semgrep", ".")

        assert report.tool_available is False
        assert report.scan_status == "tool_unavailable"

    def test_all_unavailable_reports_truthfully(self, executor):
        """All tools unavailable reports aggregate unavailable."""
        report = executor.scan("all", ".")

        assert report.tool_available is False
        assert report.scan_status == "tool_unavailable"
        assert "No security scanning tools available" in report.error_message


# =============================================================================
# Scan Success Tests
# =============================================================================

class TestScanSuccess:
    """Tests for successful scans."""

    def test_snyk_scan_no_findings(self, mock_policy, tmp_path):
        """Snyk scan with no findings."""
        scanner = MockSecurityScanner(MockToolAvailability(snyk_available=True))
        scanner.set_scan_result("snyk", MockScanResult(
            tool="snyk",
            success=True,
            available=True,
            report=MockVulnerabilityReport(findings=[]),
        ))

        executor = SecurityScanExecutor(
            scanner=scanner,
            policy=mock_policy,
            reports_dir=tmp_path / "reports",
        )
        report = executor.scan("snyk", ".")

        assert report.tool_available is True
        assert report.scan_status == "completed"
        assert report.total_findings == 0
        assert report.requires_012 is False

    def test_snyk_scan_with_findings(self, mock_policy, tmp_path):
        """Snyk scan with vulnerability findings."""
        findings = [
            MockVulnerabilityFinding(
                vuln_id="CVE-2024-0001",
                title="Test Vulnerability",
                severity=MockSeverityLevel.HIGH,
                package_name="test-package",
                fix_available=True,
                fix_version="2.0.0",
            ),
        ]

        scanner = MockSecurityScanner(MockToolAvailability(snyk_available=True))
        scanner.set_scan_result("snyk", MockScanResult(
            tool="snyk",
            success=True,
            available=True,
            report=MockVulnerabilityReport(findings=findings),
        ))

        executor = SecurityScanExecutor(
            scanner=scanner,
            policy=mock_policy,
            reports_dir=tmp_path / "reports",
        )
        report = executor.scan("snyk", ".")

        assert report.tool_available is True
        assert report.scan_status == "completed"
        assert report.total_findings == 1
        assert report.high_count == 1


# =============================================================================
# Policy Decision Tests
# =============================================================================

class TestPolicyDecision:
    """Tests for policy routing decisions."""

    def test_critical_requires_012(self, mock_policy, tmp_path):
        """CRITICAL findings always require 012 gate."""
        findings = [
            MockVulnerabilityFinding(
                vuln_id="CVE-2024-CRITICAL",
                title="Critical Vulnerability",
                severity=MockSeverityLevel.CRITICAL,
            ),
        ]

        scanner = MockSecurityScanner(MockToolAvailability(snyk_available=True))
        scanner.set_scan_result("snyk", MockScanResult(
            tool="snyk",
            success=True,
            available=True,
            report=MockVulnerabilityReport(findings=findings),
        ))

        executor = SecurityScanExecutor(
            scanner=scanner,
            policy=mock_policy,
            reports_dir=tmp_path / "reports",
        )
        report = executor.scan("snyk", ".")

        assert report.requires_012 is True
        assert report.policy_decision == "gate_012"
        assert report.recommended_next_action == "escalate_012"

    def test_high_does_not_require_012(self, mock_policy, tmp_path):
        """HIGH findings don't require 012 gate by default."""
        findings = [
            MockVulnerabilityFinding(
                vuln_id="CVE-2024-HIGH",
                title="High Vulnerability",
                severity=MockSeverityLevel.HIGH,
            ),
        ]

        scanner = MockSecurityScanner(MockToolAvailability(snyk_available=True))
        scanner.set_scan_result("snyk", MockScanResult(
            tool="snyk",
            success=True,
            available=True,
            report=MockVulnerabilityReport(findings=findings),
        ))

        executor = SecurityScanExecutor(
            scanner=scanner,
            policy=mock_policy,
            reports_dir=tmp_path / "reports",
        )
        report = executor.scan("snyk", ".")

        assert report.requires_012 is False


# =============================================================================
# Aggregate Scan Tests
# =============================================================================

class TestScanAll:
    """Tests for aggregate scanning."""

    def test_scan_all_no_tools(self, executor):
        """Scan all when no tools available."""
        report = executor.scan("all", ".")

        assert report.scan_tool == "all"
        assert report.tool_available is False

    def test_scan_all_one_tool_available(self, mock_policy, tmp_path):
        """Scan all with one tool available."""
        scanner = MockSecurityScanner(MockToolAvailability(snyk_available=True))
        scanner.set_scan_result("snyk", MockScanResult(
            tool="snyk",
            success=True,
            available=True,
            report=MockVulnerabilityReport(findings=[]),
        ))

        executor = SecurityScanExecutor(
            scanner=scanner,
            policy=mock_policy,
            reports_dir=tmp_path / "reports",
        )
        report = executor.scan("all", ".")

        assert report.tool_available is True
        assert "snyk" in report.scan_tool

    def test_scan_all_aggregates_findings(self, mock_policy, tmp_path):
        """Scan all aggregates findings from multiple tools."""
        scanner = MockSecurityScanner(MockToolAvailability(
            snyk_available=True,
            trivy_available=True,
        ))

        snyk_findings = [
            MockVulnerabilityFinding(
                vuln_id="SNYK-001",
                title="Snyk Finding",
                severity=MockSeverityLevel.HIGH,
            ),
        ]
        trivy_findings = [
            MockVulnerabilityFinding(
                vuln_id="CVE-2024-001",
                title="Trivy Finding",
                severity=MockSeverityLevel.MEDIUM,
            ),
        ]

        scanner.set_scan_result("snyk", MockScanResult(
            tool="snyk",
            success=True,
            available=True,
            report=MockVulnerabilityReport(findings=snyk_findings),
        ))
        scanner.set_scan_result("trivy", MockScanResult(
            tool="trivy",
            success=True,
            available=True,
            report=MockVulnerabilityReport(findings=trivy_findings),
        ))

        executor = SecurityScanExecutor(
            scanner=scanner,
            policy=mock_policy,
            reports_dir=tmp_path / "reports",
        )
        report = executor.scan("all", ".")

        assert report.total_findings == 2
        assert report.high_count == 1


# =============================================================================
# Report Writing Tests
# =============================================================================

class TestReportWriting:
    """Tests for report file writing."""

    def test_writes_raw_report(self, mock_policy, tmp_path):
        """Successful scan writes raw report file."""
        scanner = MockSecurityScanner(MockToolAvailability(snyk_available=True))
        scanner.set_scan_result("snyk", MockScanResult(
            tool="snyk",
            success=True,
            available=True,
            report=MockVulnerabilityReport(findings=[]),
        ))

        reports_dir = tmp_path / "reports"
        executor = SecurityScanExecutor(
            scanner=scanner,
            policy=mock_policy,
            reports_dir=reports_dir,
        )
        report = executor.scan("snyk", ".")

        assert report.raw_report_path is not None
        assert Path(report.raw_report_path).exists()


# =============================================================================
# Error Handling Tests
# =============================================================================

class TestErrorHandling:
    """Tests for error handling."""

    def test_scan_error_reported(self, mock_policy, tmp_path):
        """Scan errors are reported in error_message."""
        scanner = MockSecurityScanner(MockToolAvailability(snyk_available=True))
        scanner.set_scan_result("snyk", MockScanResult(
            tool="snyk",
            success=False,
            available=True,
            error_message="Authentication failed",
        ))

        executor = SecurityScanExecutor(
            scanner=scanner,
            policy=mock_policy,
            reports_dir=tmp_path / "reports",
        )
        report = executor.scan("snyk", ".")

        assert report.scan_status == "error"
        assert "Authentication failed" in report.error_message
