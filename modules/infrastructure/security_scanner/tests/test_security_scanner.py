"""
Security Scanner Tests

All tests use mocked subprocess calls - no actual CLI tools required.
Tests verify the execution boundary: CLI subprocess executes, Qwen/Gemma not involved.

WSP References:
- WSP 5: Test coverage
- WSP 72: Module independence (no external dependencies in tests)
"""

import json
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from modules.infrastructure.security_scanner.src.security_scanner import (
    SecurityScanner,
    ScanResult,
    ToolAvailability,
)
from modules.infrastructure.security_scanner.src.schemas import (
    VulnerabilityReport,
    VulnerabilityFinding,
    SeverityLevel,
    normalize_snyk_output,
    normalize_trivy_output,
    normalize_semgrep_output,
)


# =============================================================================
# Mock Data
# =============================================================================

MOCK_SNYK_OUTPUT = {
    "vulnerabilities": [
        {
            "id": "SNYK-JS-LODASH-1234",
            "title": "Prototype Pollution",
            "severity": "high",
            "packageName": "lodash",
            "version": "4.17.15",
            "fixedIn": ["4.17.21"],
            "description": "Prototype pollution vulnerability in lodash",
        },
        {
            "id": "SNYK-JS-AXIOS-5678",
            "title": "SSRF Vulnerability",
            "severity": "critical",
            "packageName": "axios",
            "version": "0.21.0",
            "fixedIn": ["0.21.1"],
            "description": "Server-side request forgery",
        },
    ]
}

MOCK_TRIVY_OUTPUT = {
    "Results": [
        {
            "Target": "package-lock.json",
            "Vulnerabilities": [
                {
                    "VulnerabilityID": "CVE-2021-44228",
                    "PkgName": "log4j",
                    "InstalledVersion": "2.14.0",
                    "FixedVersion": "2.17.0",
                    "Severity": "CRITICAL",
                    "Title": "Log4Shell",
                    "Description": "Remote code execution via JNDI lookup",
                },
            ],
        }
    ]
}

MOCK_SEMGREP_OUTPUT = {
    "results": [
        {
            "check_id": "python.lang.security.audit.dangerous-exec",
            "path": "src/main.py",
            "start": {"line": 42},
            "extra": {
                "severity": "ERROR",
                "message": "Dangerous use of exec()",
            },
        },
    ]
}


# =============================================================================
# Tool Availability Tests
# =============================================================================

class TestToolAvailability:
    """Tests for tool availability detection."""

    def test_no_tools_available(self):
        """Test when no tools are installed."""
        with patch("shutil.which", return_value=None):
            scanner = SecurityScanner()
            availability = scanner.check_tool_availability()

            assert not availability.snyk_available
            assert not availability.trivy_available
            assert not availability.semgrep_available
            assert not availability.any_available
            assert not availability.all_available

    def test_snyk_available(self):
        """Test snyk detection."""
        def mock_which(cmd):
            return "/usr/bin/snyk" if cmd == "snyk" else None

        with patch("shutil.which", side_effect=mock_which):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(
                    returncode=0,
                    stdout="1.1000.0",
                )
                scanner = SecurityScanner()
                availability = scanner.check_tool_availability()

                assert availability.snyk_available
                assert availability.snyk_version == "1.1000.0"
                assert availability.snyk_path == "/usr/bin/snyk"
                assert not availability.trivy_available
                assert not availability.semgrep_available
                assert availability.any_available
                assert not availability.all_available

    def test_all_tools_available(self):
        """Test when all tools are installed."""
        def mock_which(cmd):
            paths = {
                "snyk": "/usr/bin/snyk",
                "trivy": "/usr/bin/trivy",
                "semgrep": "/usr/bin/semgrep",
            }
            return paths.get(cmd)

        with patch("shutil.which", side_effect=mock_which):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(
                    returncode=0,
                    stdout="1.0.0",
                )
                scanner = SecurityScanner()
                availability = scanner.check_tool_availability()

                assert availability.snyk_available
                assert availability.trivy_available
                assert availability.semgrep_available
                assert availability.any_available
                assert availability.all_available

    def test_availability_caching(self):
        """Test that availability is cached."""
        with patch("shutil.which", return_value=None) as mock_which:
            scanner = SecurityScanner()

            # First call
            scanner.check_tool_availability()
            call_count_1 = mock_which.call_count

            # Second call (should use cache)
            scanner.check_tool_availability()
            call_count_2 = mock_which.call_count

            assert call_count_1 == call_count_2  # No additional calls

            # Force refresh
            scanner.check_tool_availability(force_refresh=True)
            assert mock_which.call_count > call_count_2


# =============================================================================
# Scan Execution Tests
# =============================================================================

class TestSnykScanner:
    """Tests for Snyk scanning."""

    def test_snyk_unavailable(self):
        """Test scan when snyk not installed."""
        with patch("shutil.which", return_value=None):
            scanner = SecurityScanner()
            result = scanner.scan_snyk(".")

            assert not result.success
            assert not result.available
            assert result.tool == "snyk"
            assert "not installed" in result.error_message

    def test_snyk_scan_success(self):
        """Test successful snyk scan with mocked output."""
        def mock_which(cmd):
            return "/usr/bin/snyk" if cmd == "snyk" else None

        with patch("shutil.which", side_effect=mock_which):
            with patch("subprocess.run") as mock_run:
                # Version check
                mock_run.return_value = MagicMock(
                    returncode=0,
                    stdout=json.dumps(MOCK_SNYK_OUTPUT),
                    stderr="",
                )

                scanner = SecurityScanner()
                scanner._availability = ToolAvailability(snyk_available=True)
                result = scanner.scan_snyk(".")

                assert result.success
                assert result.available
                assert result.report is not None
                assert result.report.scanner == "snyk"
                assert len(result.report.findings) == 2
                assert result.report.critical_count == 1
                assert result.report.high_count == 1

    def test_snyk_scan_with_vulnerabilities(self):
        """Test snyk correctly parses vulnerability details."""
        with patch("shutil.which", return_value="/usr/bin/snyk"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(
                    returncode=1,  # Non-zero = vulns found
                    stdout=json.dumps(MOCK_SNYK_OUTPUT),
                    stderr="",
                )

                scanner = SecurityScanner()
                scanner._availability = ToolAvailability(snyk_available=True)
                result = scanner.scan_snyk(".")

                assert result.success  # Vulns found is still success
                finding = result.report.findings[0]
                assert finding.vuln_id == "SNYK-JS-LODASH-1234"
                assert finding.package_name == "lodash"
                assert finding.severity == SeverityLevel.HIGH
                assert finding.fix_available
                assert finding.fix_version == "4.17.21"


class TestTrivyScanner:
    """Tests for Trivy scanning."""

    def test_trivy_unavailable(self):
        """Test scan when trivy not installed."""
        with patch("shutil.which", return_value=None):
            scanner = SecurityScanner()
            result = scanner.scan_trivy(".")

            assert not result.success
            assert not result.available
            assert result.tool == "trivy"
            assert "not installed" in result.error_message

    def test_trivy_scan_success(self):
        """Test successful trivy scan with mocked output."""
        with patch("shutil.which", return_value="/usr/bin/trivy"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(
                    returncode=0,
                    stdout=json.dumps(MOCK_TRIVY_OUTPUT),
                    stderr="",
                )

                scanner = SecurityScanner()
                scanner._availability = ToolAvailability(trivy_available=True)
                result = scanner.scan_trivy(".")

                assert result.success
                assert result.available
                assert result.report is not None
                assert result.report.scanner == "trivy"
                assert len(result.report.findings) == 1
                assert result.report.critical_count == 1

                finding = result.report.findings[0]
                assert finding.vuln_id == "CVE-2021-44228"
                assert finding.severity == SeverityLevel.CRITICAL


class TestSemgrepScanner:
    """Tests for Semgrep scanning."""

    def test_semgrep_unavailable(self):
        """Test scan when semgrep not installed."""
        with patch("shutil.which", return_value=None):
            scanner = SecurityScanner()
            result = scanner.scan_semgrep(".")

            assert not result.success
            assert not result.available
            assert result.tool == "semgrep"
            assert "not installed" in result.error_message

    def test_semgrep_scan_success(self):
        """Test successful semgrep scan with mocked output."""
        with patch("shutil.which", return_value="/usr/bin/semgrep"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(
                    returncode=0,
                    stdout=json.dumps(MOCK_SEMGREP_OUTPUT),
                    stderr="",
                )

                scanner = SecurityScanner()
                scanner._availability = ToolAvailability(semgrep_available=True)
                result = scanner.scan_semgrep(".")

                assert result.success
                assert result.available
                assert result.report is not None
                assert result.report.scanner == "semgrep"
                assert len(result.report.findings) == 1

                finding = result.report.findings[0]
                assert finding.file_path == "src/main.py"
                assert finding.line_number == 42
                assert finding.severity == SeverityLevel.HIGH


# =============================================================================
# Schema Normalization Tests
# =============================================================================

class TestSchemas:
    """Tests for output normalization schemas."""

    def test_severity_mapping_snyk(self):
        """Test Snyk severity mapping."""
        assert SeverityLevel.from_snyk("critical") == SeverityLevel.CRITICAL
        assert SeverityLevel.from_snyk("high") == SeverityLevel.HIGH
        assert SeverityLevel.from_snyk("medium") == SeverityLevel.MEDIUM
        assert SeverityLevel.from_snyk("low") == SeverityLevel.LOW
        assert SeverityLevel.from_snyk("unknown") == SeverityLevel.UNKNOWN

    def test_severity_mapping_trivy(self):
        """Test Trivy severity mapping."""
        assert SeverityLevel.from_trivy("CRITICAL") == SeverityLevel.CRITICAL
        assert SeverityLevel.from_trivy("HIGH") == SeverityLevel.HIGH
        assert SeverityLevel.from_trivy("MEDIUM") == SeverityLevel.MEDIUM
        assert SeverityLevel.from_trivy("LOW") == SeverityLevel.LOW
        assert SeverityLevel.from_trivy("UNKNOWN") == SeverityLevel.UNKNOWN

    def test_severity_mapping_semgrep(self):
        """Test Semgrep severity mapping."""
        assert SeverityLevel.from_semgrep("ERROR") == SeverityLevel.HIGH
        assert SeverityLevel.from_semgrep("WARNING") == SeverityLevel.MEDIUM
        assert SeverityLevel.from_semgrep("INFO") == SeverityLevel.INFO

    def test_vulnerability_report_summary(self):
        """Test VulnerabilityReport calculates summary correctly."""
        findings = [
            VulnerabilityFinding(
                vuln_id="CVE-1", title="Test 1", severity=SeverityLevel.CRITICAL, scanner="test"
            ),
            VulnerabilityFinding(
                vuln_id="CVE-2", title="Test 2", severity=SeverityLevel.HIGH, scanner="test"
            ),
            VulnerabilityFinding(
                vuln_id="CVE-3", title="Test 3", severity=SeverityLevel.HIGH, scanner="test"
            ),
            VulnerabilityFinding(
                vuln_id="CVE-4", title="Test 4", severity=SeverityLevel.MEDIUM, scanner="test"
            ),
        ]

        report = VulnerabilityReport(
            scan_id="test-123",
            scanner="test",
            scan_target=".",
            scan_timestamp="2026-04-18T00:00:00Z",
            findings=findings,
        )

        assert report.total_findings == 4
        assert report.critical_count == 1
        assert report.high_count == 2
        assert report.medium_count == 1
        assert report.low_count == 0
        assert report.max_severity == SeverityLevel.CRITICAL

    def test_report_to_json(self):
        """Test report serialization to JSON."""
        report = VulnerabilityReport(
            scan_id="test-123",
            scanner="snyk",
            scan_target=".",
            scan_timestamp="2026-04-18T00:00:00Z",
            findings=[],
        )

        json_str = report.to_json()
        parsed = json.loads(json_str)

        assert parsed["scan_id"] == "test-123"
        assert parsed["scanner"] == "snyk"
        assert "summary" in parsed


# =============================================================================
# Capability Report Tests
# =============================================================================

class TestCapabilityReport:
    """Tests for capability reporting."""

    def test_capability_report_no_tools(self):
        """Test capability report when no tools installed."""
        with patch("shutil.which", return_value=None):
            scanner = SecurityScanner()
            report = scanner.generate_capability_report()

            assert report["report_type"] == "security_scanner_capability"
            assert not report["tools"]["any_available"]
            assert report["execution_boundary"]["autonomous"] is True
            assert "NONE" in report["execution_boundary"]["llm_involvement"]
            assert "NONE" in report["execution_boundary"]["mcp_dependency"]
            # Check that one of the recommendations mentions no tools
            assert any("No security scanning tools" in r for r in report["recommendations"])

    def test_capability_report_all_tools(self):
        """Test capability report when all tools installed."""
        def mock_which(cmd):
            return f"/usr/bin/{cmd}"

        with patch("shutil.which", side_effect=mock_which):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout="1.0.0")

                scanner = SecurityScanner()
                report = scanner.generate_capability_report()

                assert report["tools"]["all_available"]
                assert "All tools available" in str(report["recommendations"])


# =============================================================================
# Execution Boundary Tests
# =============================================================================

class TestExecutionBoundary:
    """Tests verifying the execution boundary is correct."""

    def test_subprocess_is_execution_mechanism(self):
        """Verify subprocess.run is used for execution."""
        with patch("shutil.which", return_value="/usr/bin/snyk"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(
                    returncode=0,
                    stdout="{}",
                    stderr="",
                )

                scanner = SecurityScanner()
                scanner._availability = ToolAvailability(snyk_available=True)
                scanner.scan_snyk(".")

                # Verify subprocess.run was called
                mock_run.assert_called()

                # Verify it was called with snyk command
                call_args = mock_run.call_args[0][0]
                assert "snyk" in call_args

    def test_no_llm_in_scan_path(self):
        """Verify no LLM/Qwen/Gemma imports in scanner (comments documenting boundary are OK)."""
        # This test verifies by inspection that the scanner module
        # does not IMPORT any LLM-related modules
        import modules.infrastructure.security_scanner.src.security_scanner as scanner_module

        module_source = scanner_module.__file__

        with open(module_source, "r") as f:
            source_code = f.read()

        # Check for actual imports - these would violate execution boundary
        # (Comments explaining the boundary are allowed)
        forbidden_imports = [
            "from llm_engine",
            "import llm_engine",
            "from mcp__",
            "import mcp__",
            "from anthropic",
            "import anthropic",
            "from openai",
            "import openai",
            "from qwen",
            "import qwen",
            "from gemma",
            "import gemma",
        ]

        for pattern in forbidden_imports:
            assert pattern.lower() not in source_code.lower(), \
                f"Scanner should not import '{pattern}' - execution boundary violation"
