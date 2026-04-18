"""
Security Scanner Module

Autonomous security scanning via CLI tools (snyk, trivy, semgrep).
Subprocess-based execution - no MCP or LLM required for scanning.

WSP References:
- WSP 49: Module structure
- WSP 77: Agent coordination (SecuritySentinel integration)
- WSP 97: Execution discipline
"""

from .security_scanner import SecurityScanner, ScanResult, ToolAvailability
from .schemas import (
    VulnerabilityReport,
    VulnerabilityFinding,
    SeverityLevel,
    normalize_snyk_output,
    normalize_trivy_output,
    normalize_semgrep_output,
)

__all__ = [
    "SecurityScanner",
    "ScanResult",
    "ToolAvailability",
    "VulnerabilityReport",
    "VulnerabilityFinding",
    "SeverityLevel",
    "normalize_snyk_output",
    "normalize_trivy_output",
    "normalize_semgrep_output",
]
