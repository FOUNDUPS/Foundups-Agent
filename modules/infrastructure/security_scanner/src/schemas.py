"""
Normalized Security Scan Output Schemas

All scanner outputs (snyk, trivy, semgrep) normalize to these structures.
This enables consistent processing regardless of which tool ran the scan.

Execution Boundary:
- CLI subprocess executes scans (produces raw JSON)
- This module normalizes raw JSON to standard schema
- Qwen/Gemma analyze normalized results LATER (not here)
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import json


class SeverityLevel(Enum):
    """Normalized severity levels across all scanners."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"
    UNKNOWN = "unknown"

    @classmethod
    def from_snyk(cls, severity: str) -> "SeverityLevel":
        """Map Snyk severity to normalized level."""
        mapping = {
            "critical": cls.CRITICAL,
            "high": cls.HIGH,
            "medium": cls.MEDIUM,
            "low": cls.LOW,
        }
        return mapping.get(severity.lower(), cls.UNKNOWN)

    @classmethod
    def from_trivy(cls, severity: str) -> "SeverityLevel":
        """Map Trivy severity to normalized level."""
        mapping = {
            "CRITICAL": cls.CRITICAL,
            "HIGH": cls.HIGH,
            "MEDIUM": cls.MEDIUM,
            "LOW": cls.LOW,
            "UNKNOWN": cls.UNKNOWN,
        }
        return mapping.get(severity.upper(), cls.UNKNOWN)

    @classmethod
    def from_semgrep(cls, severity: str) -> "SeverityLevel":
        """Map Semgrep severity to normalized level."""
        mapping = {
            "ERROR": cls.HIGH,
            "WARNING": cls.MEDIUM,
            "INFO": cls.INFO,
        }
        return mapping.get(severity.upper(), cls.UNKNOWN)


@dataclass
class VulnerabilityFinding:
    """Single vulnerability finding normalized across scanners."""

    # Identification
    vuln_id: str                          # CVE-2026-XXXX or rule ID
    title: str                            # Human-readable title
    severity: SeverityLevel               # Normalized severity

    # Location
    file_path: Optional[str] = None       # Affected file
    line_number: Optional[int] = None     # Line number if applicable
    package_name: Optional[str] = None    # Affected package/dependency
    package_version: Optional[str] = None # Current version

    # Details
    description: str = ""                 # Vulnerability description
    fix_available: bool = False           # Is a fix available?
    fix_version: Optional[str] = None     # Version that fixes it

    # Metadata
    scanner: str = ""                     # snyk, trivy, or semgrep
    raw_data: Dict[str, Any] = field(default_factory=dict)  # Original scanner output

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "vuln_id": self.vuln_id,
            "title": self.title,
            "severity": self.severity.value,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "package_name": self.package_name,
            "package_version": self.package_version,
            "description": self.description,
            "fix_available": self.fix_available,
            "fix_version": self.fix_version,
            "scanner": self.scanner,
        }


@dataclass
class VulnerabilityReport:
    """Complete vulnerability scan report."""

    # Metadata
    scan_id: str                          # Unique scan identifier
    scanner: str                          # snyk, trivy, or semgrep
    scan_target: str                      # What was scanned (path, image, etc.)
    scan_timestamp: str                   # ISO format timestamp
    scan_duration_ms: int = 0             # How long the scan took

    # Results
    findings: List[VulnerabilityFinding] = field(default_factory=list)

    # Summary
    total_findings: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0

    # Status
    scan_success: bool = True
    error_message: Optional[str] = None

    def __post_init__(self):
        """Calculate summary counts from findings."""
        if self.findings and self.total_findings == 0:
            self.total_findings = len(self.findings)
            self.critical_count = sum(1 for f in self.findings if f.severity == SeverityLevel.CRITICAL)
            self.high_count = sum(1 for f in self.findings if f.severity == SeverityLevel.HIGH)
            self.medium_count = sum(1 for f in self.findings if f.severity == SeverityLevel.MEDIUM)
            self.low_count = sum(1 for f in self.findings if f.severity == SeverityLevel.LOW)

    @property
    def max_severity(self) -> SeverityLevel:
        """Return the highest severity found."""
        if self.critical_count > 0:
            return SeverityLevel.CRITICAL
        if self.high_count > 0:
            return SeverityLevel.HIGH
        if self.medium_count > 0:
            return SeverityLevel.MEDIUM
        if self.low_count > 0:
            return SeverityLevel.LOW
        return SeverityLevel.INFO

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "scan_id": self.scan_id,
            "scanner": self.scanner,
            "scan_target": self.scan_target,
            "scan_timestamp": self.scan_timestamp,
            "scan_duration_ms": self.scan_duration_ms,
            "findings": [f.to_dict() for f in self.findings],
            "summary": {
                "total": self.total_findings,
                "critical": self.critical_count,
                "high": self.high_count,
                "medium": self.medium_count,
                "low": self.low_count,
                "max_severity": self.max_severity.value,
            },
            "scan_success": self.scan_success,
            "error_message": self.error_message,
        }

    def to_json(self, indent: int = 2) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)


def normalize_snyk_output(raw_json: Dict[str, Any], scan_id: str, target: str) -> VulnerabilityReport:
    """
    Normalize Snyk JSON output to VulnerabilityReport.

    Snyk output structure (simplified):
    {
        "vulnerabilities": [
            {
                "id": "SNYK-JS-LODASH-1234",
                "title": "Prototype Pollution",
                "severity": "high",
                "packageName": "lodash",
                "version": "4.17.15",
                "fixedIn": ["4.17.21"],
                "description": "..."
            }
        ]
    }
    """
    findings = []
    vulnerabilities = raw_json.get("vulnerabilities", [])

    for vuln in vulnerabilities:
        fixed_versions = vuln.get("fixedIn", [])
        finding = VulnerabilityFinding(
            vuln_id=vuln.get("id", "UNKNOWN"),
            title=vuln.get("title", "Unknown vulnerability"),
            severity=SeverityLevel.from_snyk(vuln.get("severity", "unknown")),
            package_name=vuln.get("packageName"),
            package_version=vuln.get("version"),
            description=vuln.get("description", ""),
            fix_available=len(fixed_versions) > 0,
            fix_version=fixed_versions[0] if fixed_versions else None,
            scanner="snyk",
            raw_data=vuln,
        )
        findings.append(finding)

    return VulnerabilityReport(
        scan_id=scan_id,
        scanner="snyk",
        scan_target=target,
        scan_timestamp=datetime.utcnow().isoformat() + "Z",
        findings=findings,
    )


def normalize_trivy_output(raw_json: Dict[str, Any], scan_id: str, target: str) -> VulnerabilityReport:
    """
    Normalize Trivy JSON output to VulnerabilityReport.

    Trivy output structure (simplified):
    {
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
                        "Description": "..."
                    }
                ]
            }
        ]
    }
    """
    findings = []
    results = raw_json.get("Results", [])

    for result in results:
        target_file = result.get("Target", "")
        vulnerabilities = result.get("Vulnerabilities") or []

        for vuln in vulnerabilities:
            fixed_version = vuln.get("FixedVersion")
            finding = VulnerabilityFinding(
                vuln_id=vuln.get("VulnerabilityID", "UNKNOWN"),
                title=vuln.get("Title", "Unknown vulnerability"),
                severity=SeverityLevel.from_trivy(vuln.get("Severity", "UNKNOWN")),
                file_path=target_file,
                package_name=vuln.get("PkgName"),
                package_version=vuln.get("InstalledVersion"),
                description=vuln.get("Description", ""),
                fix_available=bool(fixed_version),
                fix_version=fixed_version,
                scanner="trivy",
                raw_data=vuln,
            )
            findings.append(finding)

    return VulnerabilityReport(
        scan_id=scan_id,
        scanner="trivy",
        scan_target=target,
        scan_timestamp=datetime.utcnow().isoformat() + "Z",
        findings=findings,
    )


def normalize_semgrep_output(raw_json: Dict[str, Any], scan_id: str, target: str) -> VulnerabilityReport:
    """
    Normalize Semgrep JSON output to VulnerabilityReport.

    Semgrep output structure (simplified):
    {
        "results": [
            {
                "check_id": "python.lang.security.audit.dangerous-exec",
                "path": "src/main.py",
                "start": {"line": 42},
                "extra": {
                    "severity": "ERROR",
                    "message": "Dangerous use of exec()"
                }
            }
        ]
    }
    """
    findings = []
    results = raw_json.get("results", [])

    for result in results:
        extra = result.get("extra", {})
        start = result.get("start", {})

        finding = VulnerabilityFinding(
            vuln_id=result.get("check_id", "UNKNOWN"),
            title=extra.get("message", "Security finding"),
            severity=SeverityLevel.from_semgrep(extra.get("severity", "INFO")),
            file_path=result.get("path"),
            line_number=start.get("line"),
            description=extra.get("message", ""),
            fix_available=False,  # Semgrep doesn't provide fix versions
            scanner="semgrep",
            raw_data=result,
        )
        findings.append(finding)

    return VulnerabilityReport(
        scan_id=scan_id,
        scanner="semgrep",
        scan_target=target,
        scan_timestamp=datetime.utcnow().isoformat() + "Z",
        findings=findings,
    )
