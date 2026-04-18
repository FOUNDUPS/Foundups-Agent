"""
Security Scanner - Autonomous CLI-based vulnerability scanning.

Execution Boundary (CRITICAL):
- CLI subprocess executes scans (snyk, trivy, semgrep)
- Qwen/Gemma are NOT involved in scan execution
- Qwen/Gemma analyze results AFTER this module returns
- Codex/Claude MCP plugins are operator tools, NOT autonomous runtime dependencies

This module is the autonomous 0102 scanning path.
No LLM, no MCP, no human in loop for scan execution.

WSP References:
- WSP 49: Module structure
- WSP 77: Agent coordination
- WSP 97: Execution discipline
"""

import json
import logging
import shutil
import subprocess
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .schemas import (
    VulnerabilityReport,
    normalize_snyk_output,
    normalize_trivy_output,
    normalize_semgrep_output,
)

logger = logging.getLogger(__name__)


@dataclass
class ToolAvailability:
    """Status of security scanning CLI tools."""

    snyk_available: bool = False
    snyk_version: Optional[str] = None
    snyk_path: Optional[str] = None

    trivy_available: bool = False
    trivy_version: Optional[str] = None
    trivy_path: Optional[str] = None

    semgrep_available: bool = False
    semgrep_version: Optional[str] = None
    semgrep_path: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for reporting."""
        return {
            "snyk": {
                "available": self.snyk_available,
                "version": self.snyk_version,
                "path": self.snyk_path,
            },
            "trivy": {
                "available": self.trivy_available,
                "version": self.trivy_version,
                "path": self.trivy_path,
            },
            "semgrep": {
                "available": self.semgrep_available,
                "version": self.semgrep_version,
                "path": self.semgrep_path,
            },
            "any_available": self.any_available,
            "all_available": self.all_available,
        }

    @property
    def any_available(self) -> bool:
        """True if at least one tool is available."""
        return self.snyk_available or self.trivy_available or self.semgrep_available

    @property
    def all_available(self) -> bool:
        """True if all tools are available."""
        return self.snyk_available and self.trivy_available and self.semgrep_available


@dataclass
class ScanResult:
    """Result of a security scan attempt."""

    tool: str                             # snyk, trivy, or semgrep
    success: bool                         # Did the scan complete?
    available: bool                       # Is the tool installed?
    report: Optional[VulnerabilityReport] = None  # Normalized report if successful
    raw_output: Optional[str] = None      # Raw stdout
    error_output: Optional[str] = None    # Raw stderr
    error_message: Optional[str] = None   # Human-readable error
    exit_code: Optional[int] = None       # Process exit code
    duration_ms: int = 0                  # Execution time

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for reporting."""
        return {
            "tool": self.tool,
            "success": self.success,
            "available": self.available,
            "report": self.report.to_dict() if self.report else None,
            "error_message": self.error_message,
            "exit_code": self.exit_code,
            "duration_ms": self.duration_ms,
        }


class SecurityScanner:
    """
    Autonomous security scanner using CLI tools.

    This class wraps snyk, trivy, and semgrep CLI tools for
    read-only vulnerability scanning. No mutations, no auto-fixes.

    Usage:
        scanner = SecurityScanner()
        availability = scanner.check_tool_availability()

        if availability.snyk_available:
            result = scanner.scan_snyk(".")
            if result.success:
                print(result.report.to_json())

    Execution Boundary:
        - subprocess.run() executes CLI tools
        - No LLM involved in execution
        - Results are normalized JSON for later Qwen/Gemma analysis
    """

    def __init__(self, timeout_seconds: int = 300):
        """
        Initialize SecurityScanner.

        Args:
            timeout_seconds: Maximum time for each scan (default 5 minutes)
        """
        self.timeout_seconds = timeout_seconds
        self._availability: Optional[ToolAvailability] = None

    def check_tool_availability(self, force_refresh: bool = False) -> ToolAvailability:
        """
        Check which security scanning tools are installed.

        Args:
            force_refresh: Re-check even if cached

        Returns:
            ToolAvailability with status of each tool
        """
        if self._availability is not None and not force_refresh:
            return self._availability

        availability = ToolAvailability()

        # Check snyk
        snyk_path = shutil.which("snyk")
        if snyk_path:
            availability.snyk_path = snyk_path
            availability.snyk_available = True
            availability.snyk_version = self._get_version("snyk", ["snyk", "--version"])

        # Check trivy
        trivy_path = shutil.which("trivy")
        if trivy_path:
            availability.trivy_path = trivy_path
            availability.trivy_available = True
            availability.trivy_version = self._get_version("trivy", ["trivy", "--version"])

        # Check semgrep
        semgrep_path = shutil.which("semgrep")
        if semgrep_path:
            availability.semgrep_path = semgrep_path
            availability.semgrep_available = True
            availability.semgrep_version = self._get_version("semgrep", ["semgrep", "--version"])

        self._availability = availability
        return availability

    def _get_version(self, tool: str, cmd: List[str]) -> Optional[str]:
        """Get version string for a tool."""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                # Take first line, strip whitespace
                return result.stdout.strip().split("\n")[0]
        except Exception as e:
            logger.debug(f"Failed to get {tool} version: {e}")
        return None

    def _run_command(
        self,
        cmd: List[str],
        tool: str,
    ) -> Tuple[bool, Optional[str], Optional[str], int, int]:
        """
        Run a subprocess command and return results.

        Returns:
            Tuple of (success, stdout, stderr, exit_code, duration_ms)
        """
        start_time = datetime.now()

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
            )
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            # Note: Some tools return non-zero when vulnerabilities found
            # This is not a failure - it means scan completed with findings
            return (
                True,
                result.stdout,
                result.stderr,
                result.returncode,
                duration_ms,
            )

        except subprocess.TimeoutExpired:
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            logger.warning(f"{tool} scan timed out after {self.timeout_seconds}s")
            return (False, None, f"Timeout after {self.timeout_seconds}s", -1, duration_ms)

        except Exception as e:
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            logger.error(f"{tool} scan failed: {e}")
            return (False, None, str(e), -1, duration_ms)

    def scan_snyk(self, path: str = ".") -> ScanResult:
        """
        Run Snyk SAST/SCA scan.

        Args:
            path: Path to scan (default: current directory)

        Returns:
            ScanResult with normalized report or error
        """
        availability = self.check_tool_availability()

        if not availability.snyk_available:
            return ScanResult(
                tool="snyk",
                success=False,
                available=False,
                error_message="snyk CLI not installed",
            )

        scan_id = f"snyk-{uuid.uuid4().hex[:8]}"

        # Snyk test with JSON output (read-only, no fix)
        cmd = ["snyk", "test", "--json", path]

        success, stdout, stderr, exit_code, duration_ms = self._run_command(cmd, "snyk")

        if not success or stdout is None:
            return ScanResult(
                tool="snyk",
                success=False,
                available=True,
                error_output=stderr,
                error_message=stderr or "Scan failed",
                exit_code=exit_code,
                duration_ms=duration_ms,
            )

        # Parse JSON output
        try:
            raw_json = json.loads(stdout)
            report = normalize_snyk_output(raw_json, scan_id, path)
            report.scan_duration_ms = duration_ms

            return ScanResult(
                tool="snyk",
                success=True,
                available=True,
                report=report,
                raw_output=stdout,
                exit_code=exit_code,
                duration_ms=duration_ms,
            )

        except json.JSONDecodeError as e:
            return ScanResult(
                tool="snyk",
                success=False,
                available=True,
                raw_output=stdout,
                error_output=stderr,
                error_message=f"Failed to parse JSON output: {e}",
                exit_code=exit_code,
                duration_ms=duration_ms,
            )

    def scan_trivy(self, target: str = ".", scan_type: str = "fs") -> ScanResult:
        """
        Run Trivy scan.

        Args:
            target: Path or image to scan
            scan_type: Type of scan - "fs" (filesystem), "image", or "repo"

        Returns:
            ScanResult with normalized report or error
        """
        availability = self.check_tool_availability()

        if not availability.trivy_available:
            return ScanResult(
                tool="trivy",
                success=False,
                available=False,
                error_message="trivy CLI not installed",
            )

        scan_id = f"trivy-{uuid.uuid4().hex[:8]}"

        # Trivy scan with JSON output (read-only)
        cmd = ["trivy", scan_type, "--format", "json", target]

        success, stdout, stderr, exit_code, duration_ms = self._run_command(cmd, "trivy")

        if not success or stdout is None:
            return ScanResult(
                tool="trivy",
                success=False,
                available=True,
                error_output=stderr,
                error_message=stderr or "Scan failed",
                exit_code=exit_code,
                duration_ms=duration_ms,
            )

        # Parse JSON output
        try:
            raw_json = json.loads(stdout)
            report = normalize_trivy_output(raw_json, scan_id, target)
            report.scan_duration_ms = duration_ms

            return ScanResult(
                tool="trivy",
                success=True,
                available=True,
                report=report,
                raw_output=stdout,
                exit_code=exit_code,
                duration_ms=duration_ms,
            )

        except json.JSONDecodeError as e:
            return ScanResult(
                tool="trivy",
                success=False,
                available=True,
                raw_output=stdout,
                error_output=stderr,
                error_message=f"Failed to parse JSON output: {e}",
                exit_code=exit_code,
                duration_ms=duration_ms,
            )

    def scan_semgrep(self, path: str = ".", config: str = "auto") -> ScanResult:
        """
        Run Semgrep SAST scan.

        Args:
            path: Path to scan
            config: Semgrep config - "auto" for default rules

        Returns:
            ScanResult with normalized report or error
        """
        availability = self.check_tool_availability()

        if not availability.semgrep_available:
            return ScanResult(
                tool="semgrep",
                success=False,
                available=False,
                error_message="semgrep CLI not installed",
            )

        scan_id = f"semgrep-{uuid.uuid4().hex[:8]}"

        # Semgrep scan with JSON output (read-only)
        cmd = ["semgrep", "--config", config, "--json", path]

        success, stdout, stderr, exit_code, duration_ms = self._run_command(cmd, "semgrep")

        if not success or stdout is None:
            return ScanResult(
                tool="semgrep",
                success=False,
                available=True,
                error_output=stderr,
                error_message=stderr or "Scan failed",
                exit_code=exit_code,
                duration_ms=duration_ms,
            )

        # Parse JSON output
        try:
            raw_json = json.loads(stdout)
            report = normalize_semgrep_output(raw_json, scan_id, path)
            report.scan_duration_ms = duration_ms

            return ScanResult(
                tool="semgrep",
                success=True,
                available=True,
                report=report,
                raw_output=stdout,
                exit_code=exit_code,
                duration_ms=duration_ms,
            )

        except json.JSONDecodeError as e:
            return ScanResult(
                tool="semgrep",
                success=False,
                available=True,
                raw_output=stdout,
                error_output=stderr,
                error_message=f"Failed to parse JSON output: {e}",
                exit_code=exit_code,
                duration_ms=duration_ms,
            )

    def scan_all_available(self, path: str = ".") -> Dict[str, ScanResult]:
        """
        Run all available scanners on a path.

        Args:
            path: Path to scan

        Returns:
            Dict mapping tool name to ScanResult
        """
        results = {}

        availability = self.check_tool_availability()

        if availability.snyk_available:
            results["snyk"] = self.scan_snyk(path)
        else:
            results["snyk"] = ScanResult(
                tool="snyk",
                success=False,
                available=False,
                error_message="snyk CLI not installed",
            )

        if availability.trivy_available:
            results["trivy"] = self.scan_trivy(path)
        else:
            results["trivy"] = ScanResult(
                tool="trivy",
                success=False,
                available=False,
                error_message="trivy CLI not installed",
            )

        if availability.semgrep_available:
            results["semgrep"] = self.scan_semgrep(path)
        else:
            results["semgrep"] = ScanResult(
                tool="semgrep",
                success=False,
                available=False,
                error_message="semgrep CLI not installed",
            )

        return results

    def generate_capability_report(self) -> Dict[str, Any]:
        """
        Generate a report of tool availability and capabilities.

        Returns:
            Dict suitable for JSON serialization
        """
        availability = self.check_tool_availability()

        return {
            "report_type": "security_scanner_capability",
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "tools": availability.to_dict(),
            "execution_boundary": {
                "scanner_execution": "subprocess (CLI tools)",
                "llm_involvement": "NONE - Qwen/Gemma analyze results AFTER scanning",
                "mcp_dependency": "NONE - Codex/Claude MCP are operator tools only",
                "autonomous": True,
            },
            "recommendations": self._generate_recommendations(availability),
        }

    def _generate_recommendations(self, availability: ToolAvailability) -> List[str]:
        """Generate recommendations based on tool availability."""
        recommendations = []

        if not availability.snyk_available:
            recommendations.append("Install snyk: npm install -g snyk")

        if not availability.trivy_available:
            recommendations.append("Install trivy: brew install trivy (or apt/choco)")

        if not availability.semgrep_available:
            recommendations.append("Install semgrep: pip install semgrep")

        if availability.all_available:
            recommendations.append("All tools available - full security scanning ready")

        if not availability.any_available:
            recommendations.append("No security scanning tools installed - scans will report unavailable")

        return recommendations
