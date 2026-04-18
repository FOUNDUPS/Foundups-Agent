#!/usr/bin/env python3
"""
Security Scan Skill Executor

WRE skill wrapper for autonomous security scanning.
Calls SEC1 (scanner) for execution and SEC2 (policy) for routing.

Execution Boundary:
- SEC1 owns scanner execution (subprocess)
- SEC2 owns policy routing (escalation decisions)
- SEC3 (this) owns orchestration (skill wrapper)

WSP Compliance:
- WSP 97: Truthful reporting (unavailable tools reported as unavailable, not failure)
- WSP 77: Agent coordination
- WSP 84: Code reuse (delegates to SEC1/SEC2)
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Literal

logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    """Return current UTC datetime."""
    return datetime.now(timezone.utc)


# Type aliases
ScanTool = Literal["snyk", "trivy", "semgrep", "all"]


@dataclass
class SecurityScanReport:
    """Normalized security scan report with policy decision."""

    # Metadata
    generated_at: str
    scan_tool: str
    target: str

    # Tool status
    tool_available: bool
    scan_status: str  # "completed", "tool_unavailable", "error"

    # Findings
    findings: List[Dict[str, Any]] = field(default_factory=list)
    max_severity: Optional[str] = None
    total_findings: int = 0
    critical_count: int = 0
    high_count: int = 0

    # Policy decision
    policy_decision: str = "report_only"  # gate_012, modlog_only, report_only, ignore
    requires_012: bool = False
    recommended_next_action: str = "none"

    # Raw data
    raw_report_path: Optional[str] = None
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "generated_at": self.generated_at,
            "scan_tool": self.scan_tool,
            "target": self.target,
            "tool_available": self.tool_available,
            "scan_status": self.scan_status,
            "findings": self.findings,
            "max_severity": self.max_severity,
            "total_findings": self.total_findings,
            "critical_count": self.critical_count,
            "high_count": self.high_count,
            "policy_decision": self.policy_decision,
            "requires_012": self.requires_012,
            "recommended_next_action": self.recommended_next_action,
            "raw_report_path": self.raw_report_path,
            "error_message": self.error_message,
        }

    def to_json(self, indent: int = 2) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)


class SecurityScanExecutor:
    """
    WRE skill executor for security scanning.

    Wraps SEC1 scanner and SEC2 policy modules.
    Handles tool unavailability truthfully.

    Example:
        executor = SecurityScanExecutor()
        report = executor.scan("snyk", ".")
        if report.requires_012:
            print("CRITICAL: 012 gate required")
    """

    def __init__(
        self,
        scanner: Optional[Any] = None,
        policy: Optional[Any] = None,
        reports_dir: Optional[Path] = None,
    ) -> None:
        """
        Initialize executor.

        Args:
            scanner: SEC1 SecurityScanner instance (injected for testing)
            policy: SEC2 VulnerabilityScanPolicy instance (injected for testing)
            reports_dir: Directory for report output
        """
        self._scanner = scanner
        self._policy = policy
        self._reports_dir = reports_dir or Path("modules/infrastructure/reports/security")

        # Lazy-load SEC1/SEC2 if not injected
        self._sec1_loaded = scanner is not None
        self._sec2_loaded = policy is not None

    def _ensure_scanner(self) -> bool:
        """Lazy-load SEC1 scanner module."""
        if self._sec1_loaded:
            return self._scanner is not None

        try:
            from modules.infrastructure.security_scanner.src.security_scanner import (
                SecurityScanner,
            )
            self._scanner = SecurityScanner()
            self._sec1_loaded = True
            return True
        except ImportError as e:
            logger.warning("SEC1 scanner not available: %s", e)
            self._sec1_loaded = True  # Mark as attempted
            return False

    def _ensure_policy(self) -> bool:
        """Lazy-load SEC2 policy module."""
        if self._sec2_loaded:
            return self._policy is not None

        try:
            from modules.ai_intelligence.ai_overseer.src.vulnerability_scan_policy import (
                VulnerabilityScanPolicy,
            )
            self._policy = VulnerabilityScanPolicy()
            self._sec2_loaded = True
            return True
        except ImportError as e:
            logger.warning("SEC2 policy not available: %s", e)
            self._sec2_loaded = True  # Mark as attempted
            return False

    def _get_policy_decision(
        self,
        severity: str,
        finding_type: str = "dependency",
    ) -> Dict[str, Any]:
        """Get policy decision for a finding."""
        if not self._ensure_policy():
            # Default to report_only if policy unavailable
            return {
                "escalation": "report_only",
                "requires_012": severity.lower() == "critical",
                "reason": "SEC2 policy unavailable, using defaults",
            }

        try:
            # Try to import SEC2 enums for proper policy call
            try:
                from modules.ai_intelligence.ai_overseer.src.vulnerability_scan_policy import (
                    SeverityLevel,
                    FindingType,
                )
                severity_enum = SeverityLevel.from_string(severity)
                try:
                    finding_type_enum = FindingType(finding_type.lower())
                except ValueError:
                    finding_type_enum = FindingType.UNKNOWN

                decision = self._policy.get_escalation(severity_enum, finding_type_enum)
            except ImportError:
                # SEC2 not available - use duck-typed call (for mocks)
                # Create simple severity object that has .value attribute
                class SimpleSeverity:
                    def __init__(self, value: str):
                        self.value = value
                decision = self._policy.get_escalation(SimpleSeverity(severity.lower()))

            return {
                "escalation": decision.escalation.value if hasattr(decision.escalation, 'value') else str(decision.escalation),
                "requires_012": decision.requires_012,
                "reason": decision.reason,
            }
        except Exception as e:
            logger.error("Policy decision failed: %s", e)
            return {
                "escalation": "report_only",
                "requires_012": severity.lower() == "critical",
                "reason": f"Policy error: {e}",
            }

    def _determine_overall_policy(
        self,
        findings: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Determine overall policy decision for all findings."""
        requires_012 = False
        max_escalation = "ignore"
        escalation_priority = ["ignore", "report_only", "modlog_only", "gate_012"]

        for finding in findings:
            severity = finding.get("severity", "unknown")
            finding_type = finding.get("finding_type", "dependency")
            decision = self._get_policy_decision(severity, finding_type)

            if decision["requires_012"]:
                requires_012 = True

            # Track highest escalation
            escalation = decision["escalation"]
            if escalation_priority.index(escalation) > escalation_priority.index(max_escalation):
                max_escalation = escalation

        return {
            "escalation": max_escalation,
            "requires_012": requires_012,
        }

    def _run_single_scan(
        self,
        tool: str,
        target: str,
    ) -> SecurityScanReport:
        """Run a single tool scan."""
        generated_at = _utc_now().isoformat()

        # Check if scanner is available
        if not self._ensure_scanner():
            return SecurityScanReport(
                generated_at=generated_at,
                scan_tool=tool,
                target=target,
                tool_available=False,
                scan_status="error",
                error_message="SEC1 scanner module not available",
                recommended_next_action="Install SEC1 module (PR #369)",
            )

        # Check tool availability
        availability = self._scanner.check_tool_availability()
        tool_available_map = {
            "snyk": availability.snyk_available,
            "trivy": availability.trivy_available,
            "semgrep": availability.semgrep_available,
        }

        if not tool_available_map.get(tool, False):
            return SecurityScanReport(
                generated_at=generated_at,
                scan_tool=tool,
                target=target,
                tool_available=False,
                scan_status="tool_unavailable",
                error_message=f"{tool} CLI not installed",
                recommended_next_action=f"Install {tool} CLI tool",
            )

        # Run the scan
        scan_methods = {
            "snyk": self._scanner.scan_snyk,
            "trivy": self._scanner.scan_trivy,
            "semgrep": self._scanner.scan_semgrep,
        }

        scan_method = scan_methods.get(tool)
        if not scan_method:
            return SecurityScanReport(
                generated_at=generated_at,
                scan_tool=tool,
                target=target,
                tool_available=False,
                scan_status="error",
                error_message=f"Unknown tool: {tool}",
            )

        result = scan_method(target)

        if not result.success:
            return SecurityScanReport(
                generated_at=generated_at,
                scan_tool=tool,
                target=target,
                tool_available=True,
                scan_status="error",
                error_message=result.error_message,
            )

        # Extract findings
        findings = []
        if result.report:
            for finding in result.report.findings:
                findings.append({
                    "vuln_id": finding.vuln_id,
                    "title": finding.title,
                    "severity": finding.severity.value,
                    "package_name": finding.package_name,
                    "fix_available": finding.fix_available,
                    "fix_version": finding.fix_version,
                    "finding_type": "dependency",  # Default for package vulns
                })

        # Get policy decision
        policy_result = self._determine_overall_policy(findings)

        # Determine recommended action
        if policy_result["requires_012"]:
            recommended_action = "escalate_012"
        elif policy_result["escalation"] == "modlog_only":
            recommended_action = "log_modlog"
        elif policy_result["escalation"] == "report_only":
            recommended_action = "review_report"
        else:
            recommended_action = "none"

        # Write raw report
        raw_report_path = None
        if result.report:
            raw_report_path = self._write_raw_report(tool, target, result.report.to_dict())

        return SecurityScanReport(
            generated_at=generated_at,
            scan_tool=tool,
            target=target,
            tool_available=True,
            scan_status="completed",
            findings=findings,
            max_severity=result.report.max_severity.value if result.report else None,
            total_findings=result.report.total_findings if result.report else 0,
            critical_count=result.report.critical_count if result.report else 0,
            high_count=result.report.high_count if result.report else 0,
            policy_decision=policy_result["escalation"],
            requires_012=policy_result["requires_012"],
            recommended_next_action=recommended_action,
            raw_report_path=raw_report_path,
        )

    def _write_raw_report(
        self,
        tool: str,
        target: str,
        report_data: Dict[str, Any],
    ) -> str:
        """Write raw report to file."""
        self._reports_dir.mkdir(parents=True, exist_ok=True)

        timestamp = _utc_now().strftime("%Y%m%d_%H%M%S")
        filename = f"{tool}_scan_{timestamp}.json"
        filepath = self._reports_dir / filename

        with open(filepath, "w") as f:
            json.dump(report_data, f, indent=2)

        return str(filepath)

    def scan(
        self,
        tool: ScanTool,
        target: str = ".",
    ) -> SecurityScanReport:
        """
        Run security scan with specified tool.

        Args:
            tool: Tool to use ("snyk", "trivy", "semgrep", "all")
            target: Path to scan

        Returns:
            SecurityScanReport with findings and policy decision
        """
        if tool == "all":
            return self.scan_all(target)

        return self._run_single_scan(tool, target)

    def scan_all(self, target: str = ".") -> SecurityScanReport:
        """
        Run all available scanners.

        Returns aggregate report with combined findings.
        """
        generated_at = _utc_now().isoformat()
        all_findings: List[Dict[str, Any]] = []
        tools_run: List[str] = []
        errors: List[str] = []
        any_available = False

        for tool in ["snyk", "trivy", "semgrep"]:
            result = self._run_single_scan(tool, target)

            if result.tool_available:
                any_available = True
                tools_run.append(tool)

                if result.scan_status == "completed":
                    all_findings.extend(result.findings)
                elif result.error_message:
                    errors.append(f"{tool}: {result.error_message}")
            else:
                errors.append(f"{tool}: not available")

        if not any_available:
            return SecurityScanReport(
                generated_at=generated_at,
                scan_tool="all",
                target=target,
                tool_available=False,
                scan_status="tool_unavailable",
                error_message="No security scanning tools available",
                recommended_next_action="Install snyk, trivy, or semgrep",
            )

        # Calculate aggregate severity counts
        critical_count = sum(1 for f in all_findings if f.get("severity") == "critical")
        high_count = sum(1 for f in all_findings if f.get("severity") == "high")

        # Determine max severity
        if critical_count > 0:
            max_severity = "critical"
        elif high_count > 0:
            max_severity = "high"
        elif any(f.get("severity") == "medium" for f in all_findings):
            max_severity = "medium"
        elif any(f.get("severity") == "low" for f in all_findings):
            max_severity = "low"
        elif all_findings:
            max_severity = "info"
        else:
            max_severity = None

        # Get overall policy decision
        policy_result = self._determine_overall_policy(all_findings)

        # Determine recommended action
        if policy_result["requires_012"]:
            recommended_action = "escalate_012"
        elif policy_result["escalation"] == "modlog_only":
            recommended_action = "log_modlog"
        elif policy_result["escalation"] == "report_only":
            recommended_action = "review_report"
        else:
            recommended_action = "none"

        return SecurityScanReport(
            generated_at=generated_at,
            scan_tool=f"all ({','.join(tools_run)})",
            target=target,
            tool_available=True,
            scan_status="completed" if not errors else "partial",
            findings=all_findings,
            max_severity=max_severity,
            total_findings=len(all_findings),
            critical_count=critical_count,
            high_count=high_count,
            policy_decision=policy_result["escalation"],
            requires_012=policy_result["requires_012"],
            recommended_next_action=recommended_action,
            error_message="; ".join(errors) if errors else None,
        )


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="WRE Security Scan Skill",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "tool",
        choices=["snyk", "trivy", "semgrep", "all"],
        help="Security scanning tool to use",
    )
    parser.add_argument(
        "--target",
        default=".",
        help="Path to scan (default: current directory)",
    )
    parser.add_argument(
        "--output",
        help="Output file for report (default: stdout)",
    )
    parser.add_argument(
        "--reports-dir",
        default="modules/infrastructure/reports/security",
        help="Directory for raw reports",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    # Run scan
    executor = SecurityScanExecutor(reports_dir=Path(args.reports_dir))
    report = executor.scan(args.tool, args.target)

    # Output report
    output_json = report.to_json()

    if args.output:
        with open(args.output, "w") as f:
            f.write(output_json)
        print(f"Report written to: {args.output}")
    else:
        print(output_json)

    # Return non-zero if 012 gate required
    if report.requires_012:
        logger.warning("CRITICAL: 012 gate required")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
