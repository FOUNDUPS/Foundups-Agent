#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Security Stack Control Hooks - 0102 Entry Points

SEC9 — SECURITY_STACK_0102_CONTROL_HOOKS_PHASE1

Provides safe control hooks for the merged SEC1-SEC7 security stack:
1. Manual 0102 invocation hook (CLI/module entrypoint)
2. WRE skill invocation hook (SEC3 contract)
3. HoloDAE trigger bridge (SEC4 -> SEC3)
4. Status/report hook (durable artifact)
5. 012 escalation hook (alert artifact)

Hard constraints:
- No auto-remediation
- No code patch generation
- No MCP dependency
- Report-only mode by default

WSP Compliance:
- WSP 97: Truthful state distinction (triggered/proposed/executed/unavailable/escalated)
- WSP 77: Agent coordination
"""

import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

logger = logging.getLogger(__name__)


def _utc_iso() -> str:
    """Return current UTC timestamp as ISO string."""
    return datetime.now(timezone.utc).isoformat()


# State machine for truthful distinction (WSP 97)
SecurityState = Literal[
    "triggered",      # Trigger detected
    "proposed",       # Scan proposed but not executed
    "executed",       # Scan executed
    "unavailable",    # Tool unavailable
    "escalated",      # Escalated to 012
    "completed",      # Flow completed
]


@dataclass
class SecurityStackStatus:
    """
    Durable status artifact for security stack.

    Written to alerts/security/status.json after each run.
    """

    # Timestamps
    last_run_at: str = ""
    generated_at: str = ""

    # Mode
    mode: str = "report_only"  # report_only, dry_run, live

    # Tool availability
    tools_available: Dict[str, bool] = field(default_factory=dict)
    any_tool_available: bool = False

    # Counts
    trigger_count: int = 0
    scans_proposed: int = 0
    scans_executed: int = 0
    findings_stored: int = 0
    proposals_written: int = 0
    requires_012_count: int = 0

    # State (WSP 97)
    current_state: str = "completed"

    # Next action
    next_operator_action: str = "none"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)


@dataclass
class SecurityAlert:
    """
    Alert artifact for critical/secret findings requiring 012 review.

    Written to alerts/security/<finding_id>_<timestamp>.json.
    """

    # Finding identification
    finding_id: str
    fingerprint: str
    tool: str
    severity: str

    # Alert metadata
    alert_type: str = "security_finding"  # security_finding, secret_exposure
    escalation_reason: str = ""
    created_at: str = ""

    # Finding details
    title: str = ""
    description: str = ""
    target: str = ""
    file_path: Optional[str] = None
    package_name: Optional[str] = None

    # Analysis proposal (if available)
    analysis_proposal: Optional[Dict[str, Any]] = None

    # State
    state: str = "escalated"
    requires_012: bool = True
    acknowledged: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)


class SecurityStackController:
    """
    Main controller for 0102 security stack invocation.

    Provides entrypoints for:
    - Manual dry-run/report mode
    - WRE skill invocation
    - HoloDAE trigger processing
    - Status reporting
    - 012 escalation

    Example (manual invocation):
        controller = SecurityStackController()
        result = controller.run_dry_run(target=".")
        print(result.status.to_json())

    Example (WRE skill contract):
        controller = SecurityStackController()
        report = controller.invoke_sec3_skill(
            tool="snyk",
            target=".",
            mode="report_only",
        )

    Example (trigger bridge):
        controller = SecurityStackController()
        sec3_inputs = controller.bridge_trigger_to_sec3(trigger_proposals)
    """

    DEFAULT_ALERTS_DIR = Path("alerts/security")
    DEFAULT_STATUS_FILE = "status.json"

    def __init__(
        self,
        alerts_dir: Optional[Path] = None,
        report_only: bool = True,
    ):
        """
        Initialize SecurityStackController.

        Args:
            alerts_dir: Directory for alert/status artifacts
            report_only: If True, never execute scans (default: True)
        """
        self.alerts_dir = Path(alerts_dir) if alerts_dir else self.DEFAULT_ALERTS_DIR
        self.report_only = report_only

        # Lazy-loaded components
        self._scanner = None
        self._policy = None
        self._executor = None
        self._memory = None
        self._recall = None
        self._assistant = None
        self._trigger_detector = None

        # Run state
        self._status = SecurityStackStatus(mode="report_only" if report_only else "live")

        logger.info(
            "[SECURITY-CONTROL] Initialized - alerts_dir=%s, report_only=%s",
            self.alerts_dir,
            report_only,
        )

    def _ensure_alerts_dir(self) -> None:
        """Ensure alerts directory exists."""
        self.alerts_dir.mkdir(parents=True, exist_ok=True)

    def _load_sec1_scanner(self) -> bool:
        """Lazy-load SEC1 scanner."""
        if self._scanner is not None:
            return True

        try:
            from modules.infrastructure.security_scanner.src.security_scanner import (
                SecurityScanner,
            )
            self._scanner = SecurityScanner()
            return True
        except ImportError as e:
            logger.debug("[SECURITY-CONTROL] SEC1 scanner not available: %s", e)
            return False

    def _load_sec2_policy(self) -> bool:
        """Lazy-load SEC2 policy."""
        if self._policy is not None:
            return True

        try:
            from modules.ai_intelligence.ai_overseer.src.vulnerability_scan_policy import (
                VulnerabilityScanPolicy,
            )
            self._policy = VulnerabilityScanPolicy()
            return True
        except ImportError as e:
            logger.debug("[SECURITY-CONTROL] SEC2 policy not available: %s", e)
            return False

    def _load_sec3_executor(self) -> bool:
        """Lazy-load SEC3 executor."""
        if self._executor is not None:
            return True

        try:
            from modules.infrastructure.wre_core.skillz.security_scan.executor import (
                SecurityScanExecutor,
            )
            self._executor = SecurityScanExecutor()
            return True
        except ImportError as e:
            logger.debug("[SECURITY-CONTROL] SEC3 executor not available: %s", e)
            return False

    def _load_sec4_trigger(self) -> bool:
        """Lazy-load SEC4 trigger detector."""
        if self._trigger_detector is not None:
            return True

        try:
            from modules.infrastructure.wre_core.src.security_trigger import (
                SecurityTriggerDetector,
            )
            self._trigger_detector = SecurityTriggerDetector()
            return True
        except ImportError as e:
            logger.debug("[SECURITY-CONTROL] SEC4 trigger not available: %s", e)
            return False

    def _load_sec5_memory(self) -> bool:
        """Lazy-load SEC5 pattern memory."""
        if self._memory is not None:
            return True

        try:
            from modules.infrastructure.wre_core.src.security_pattern_memory import (
                SecurityPatternMemory,
            )
            self._memory = SecurityPatternMemory()
            return True
        except ImportError as e:
            logger.debug("[SECURITY-CONTROL] SEC5 memory not available: %s", e)
            return False

    def _load_sec6_recall(self) -> bool:
        """Lazy-load SEC6 recall."""
        if self._recall is not None:
            return True

        if not self._load_sec5_memory():
            return False

        try:
            from modules.infrastructure.wre_core.src.security_recall import (
                SecurityRecall,
            )
            self._recall = SecurityRecall(self._memory)
            return True
        except ImportError as e:
            logger.debug("[SECURITY-CONTROL] SEC6 recall not available: %s", e)
            return False

    def _load_sec7_assistant(self) -> bool:
        """Lazy-load SEC7 analysis assistant."""
        if self._assistant is not None:
            return True

        try:
            from modules.infrastructure.wre_core.src.security_analysis_assistant import (
                SecurityAnalysisAssistant,
            )
            self._assistant = SecurityAnalysisAssistant(
                enable_qwen=True,
                enable_gemma=True,
            )
            return True
        except ImportError as e:
            logger.debug("[SECURITY-CONTROL] SEC7 assistant not available: %s", e)
            return False

    # =========================================================================
    # Hook 1: Manual 0102 Invocation
    # =========================================================================

    def run_dry_run(
        self,
        target: str = ".",
        tools: Optional[List[str]] = None,
    ) -> "DryRunResult":
        """
        Run security stack in dry-run/report mode.

        This is the main entrypoint for 0102 manual invocation.
        Does not require 012 except for critical escalation review.

        Args:
            target: Path to scan
            tools: List of tools to use (default: all available)

        Returns:
            DryRunResult with status, reports, and alerts
        """
        self._status = SecurityStackStatus(
            last_run_at=_utc_iso(),
            generated_at=_utc_iso(),
            mode="dry_run",
            current_state="triggered",
        )

        reports = []
        alerts = []

        # Check tool availability
        self._status.tools_available = self.check_tool_availability()
        self._status.any_tool_available = any(self._status.tools_available.values())

        if not self._status.any_tool_available:
            self._status.current_state = "unavailable"
            self._status.next_operator_action = "install_security_tools"
            self._status.generated_at = _utc_iso()
            self.write_status()
            return DryRunResult(
                status=self._status,
                reports=reports,
                alerts=alerts,
            )

        # Load components
        if not self._load_sec3_executor():
            self._status.current_state = "unavailable"
            self._status.next_operator_action = "check_sec3_installation"
            self._status.generated_at = _utc_iso()
            self.write_status()
            return DryRunResult(status=self._status, reports=reports, alerts=alerts)

        # Determine tools to use
        tools_to_run = tools or [t for t, avail in self._status.tools_available.items() if avail]

        # Execute scans (report-only)
        self._status.current_state = "proposed"
        self._status.scans_proposed = len(tools_to_run)

        for tool in tools_to_run:
            if not self._status.tools_available.get(tool, False):
                continue

            if self.report_only:
                # Dry-run: don't execute, just report proposed
                report = {
                    "tool": tool,
                    "target": target,
                    "state": "proposed",
                    "scan_status": "not_executed_dry_run",
                }
                reports.append(report)
            else:
                # Live mode: actually execute
                self._status.current_state = "executed"
                scan_report = self._executor.scan(tool, target)
                reports.append(scan_report.to_dict())
                self._status.scans_executed += 1

                # Check for escalation
                if scan_report.requires_012:
                    self._status.requires_012_count += 1
                    alert = self._create_alert_from_report(scan_report)
                    alerts.append(alert)
                    self._status.current_state = "escalated"

        # Store findings in memory (if available)
        if self._load_sec5_memory() and not self.report_only:
            for report in reports:
                if isinstance(report, dict) and report.get("findings"):
                    stored = self._memory.store_from_scan_report(report)
                    self._status.findings_stored += stored.get("new", 0) + stored.get("updated", 0)

        # Write status artifact
        self._status.current_state = "completed"
        self._status.generated_at = _utc_iso()
        self._status.next_operator_action = self._determine_next_action()
        self.write_status()

        # Write alerts
        for alert in alerts:
            self.write_alert(alert)

        return DryRunResult(
            status=self._status,
            reports=reports,
            alerts=alerts,
        )

    def check_tool_availability(self) -> Dict[str, bool]:
        """
        Check which security scanning tools are available.

        Returns:
            Dict mapping tool name to availability status
        """
        if not self._load_sec1_scanner():
            return {"snyk": False, "trivy": False, "semgrep": False}

        availability = self._scanner.check_tool_availability()
        return {
            "snyk": availability.snyk_available,
            "trivy": availability.trivy_available,
            "semgrep": availability.semgrep_available,
        }

    # =========================================================================
    # Hook 2: WRE Skill Invocation Contract
    # =========================================================================

    def invoke_sec3_skill(
        self,
        tool: str,
        target: str,
        mode: str = "report_only",
    ) -> Dict[str, Any]:
        """
        WRE skill invocation hook for SEC3.

        Input Contract:
            tool: "snyk" | "trivy" | "semgrep" | "all"
            target: Path to scan (string)
            mode: "report_only" | "dry_run" | "live"

        Output Contract:
            {
                "tool": str,
                "target": str,
                "state": "proposed" | "executed" | "unavailable",
                "scan_status": str,
                "tool_available": bool,
                "findings": List[Dict],
                "total_findings": int,
                "requires_012": bool,
                "policy_decision": str,
            }

        Example:
            # Scan one path with snyk
            result = controller.invoke_sec3_skill("snyk", ".", "report_only")

            # Scan all supported tools
            result = controller.invoke_sec3_skill("all", ".", "report_only")

        Args:
            tool: Tool to use
            target: Path to scan
            mode: Execution mode

        Returns:
            Dict with scan result
        """
        if not self._load_sec3_executor():
            return {
                "tool": tool,
                "target": target,
                "state": "unavailable",
                "scan_status": "sec3_not_available",
                "tool_available": False,
                "findings": [],
                "total_findings": 0,
                "requires_012": False,
                "policy_decision": "report_only",
            }

        if mode == "report_only" or self.report_only:
            # Don't actually scan, just check availability
            availability = self.check_tool_availability()
            tool_available = availability.get(tool, False) if tool != "all" else any(availability.values())

            return {
                "tool": tool,
                "target": target,
                "state": "proposed",
                "scan_status": "not_executed_report_only",
                "tool_available": tool_available,
                "findings": [],
                "total_findings": 0,
                "requires_012": False,
                "policy_decision": "report_only",
            }

        # Live execution
        report = self._executor.scan(tool, target)
        return report.to_dict()

    # =========================================================================
    # Hook 3: HoloDAE Trigger Bridge
    # =========================================================================

    def bridge_trigger_to_sec3(
        self,
        trigger_proposals: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Bridge SEC4 trigger proposals to SEC3 input contracts.

        Transforms SEC4 TriggerProposal format to SEC3 skill input.

        SEC4 TriggerProposal format:
            {
                "trigger_id": str,
                "status": "proposed",
                "scan_type": "sca" | "container" | "sast" | "iac",
                "recommended_tools": List[str],
                "priority": int,
                "triggered_at": str,
                "matched_patterns": List[str],
            }

        SEC3 Skill Input format:
            {
                "tool": str,
                "target": str,
                "mode": "report_only",
                "trigger_id": str,
            }

        Note: Automatic execution is DEFERRED because:
        1. Default mode is report_only (no auto-scan)
        2. Live execution requires explicit opt-in
        3. 012 review required for critical findings

        Args:
            trigger_proposals: List of SEC4 trigger proposals

        Returns:
            List of SEC3 skill input contracts
        """
        sec3_inputs = []

        for proposal in trigger_proposals:
            # Skip non-proposed status
            if proposal.get("status") != "proposed":
                continue

            # Map scan_type to tool
            scan_type = proposal.get("scan_type", "all")
            recommended_tools = proposal.get("recommended_tools", [])

            # Use recommended tools if available, else map scan_type
            if recommended_tools:
                tools = recommended_tools
            else:
                tools = self._map_scan_type_to_tools(scan_type)

            for tool in tools:
                sec3_input = {
                    "tool": tool,
                    "target": ".",  # Default to repo root
                    "mode": "report_only",  # NEVER auto-execute
                    "trigger_id": proposal.get("trigger_id"),
                    "scan_type": scan_type,
                    "priority": proposal.get("priority", 1),
                }
                sec3_inputs.append(sec3_input)

        logger.info(
            "[SECURITY-CONTROL] Bridged %d triggers to %d SEC3 inputs (auto-execution DEFERRED)",
            len(trigger_proposals),
            len(sec3_inputs),
        )

        return sec3_inputs

    def _map_scan_type_to_tools(self, scan_type: str) -> List[str]:
        """Map SEC4 scan_type to SEC3 tool names."""
        mapping = {
            "sca": ["snyk", "trivy"],
            "container": ["trivy"],
            "sast": ["semgrep"],
            "iac": ["trivy"],
            "all": ["snyk", "trivy", "semgrep"],
        }
        return mapping.get(scan_type, ["snyk"])

    # =========================================================================
    # Hook 4: Status/Report Artifact
    # =========================================================================

    def write_status(self, status: Optional[SecurityStackStatus] = None) -> Path:
        """
        Write durable status artifact.

        Args:
            status: Status to write (default: current status)

        Returns:
            Path to written status file
        """
        self._ensure_alerts_dir()
        status = status or self._status

        status_path = self.alerts_dir / self.DEFAULT_STATUS_FILE

        with open(status_path, "w", encoding="utf-8") as f:
            f.write(status.to_json())

        logger.info("[SECURITY-CONTROL] Wrote status artifact: %s", status_path)
        return status_path

    def read_status(self) -> Optional[SecurityStackStatus]:
        """
        Read current status artifact.

        Returns:
            SecurityStackStatus or None if not found
        """
        status_path = self.alerts_dir / self.DEFAULT_STATUS_FILE

        if not status_path.exists():
            return None

        try:
            with open(status_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            return SecurityStackStatus(**data)
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning("[SECURITY-CONTROL] Failed to read status: %s", e)
            return None

    # =========================================================================
    # Hook 5: 012 Escalation Alert
    # =========================================================================

    def write_alert(self, alert: SecurityAlert) -> Path:
        """
        Write alert artifact for 012 review.

        Args:
            alert: SecurityAlert to write

        Returns:
            Path to written alert file
        """
        self._ensure_alerts_dir()

        # Generate filename
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        safe_id = alert.finding_id.replace("/", "_").replace(":", "_")[:50]
        filename = f"alert_{safe_id}_{timestamp}.json"

        alert_path = self.alerts_dir / filename

        with open(alert_path, "w", encoding="utf-8") as f:
            f.write(alert.to_json())

        logger.warning(
            "[SECURITY-CONTROL] ALERT: %s finding requires 012 review - %s",
            alert.severity.upper(),
            alert_path,
        )

        return alert_path

    def create_alert_from_finding(
        self,
        finding: Dict[str, Any],
        escalation_reason: str = "Critical/secret finding",
        analysis_proposal: Optional[Dict[str, Any]] = None,
    ) -> SecurityAlert:
        """
        Create alert artifact from a finding.

        Args:
            finding: Finding dict
            escalation_reason: Reason for escalation
            analysis_proposal: SEC7 analysis proposal (optional)

        Returns:
            SecurityAlert
        """
        return SecurityAlert(
            finding_id=finding.get("finding_id", finding.get("vuln_id", "unknown")),
            fingerprint=finding.get("fingerprint", "unknown"),
            tool=finding.get("tool", "unknown"),
            severity=finding.get("severity", "unknown"),
            alert_type="secret_exposure" if finding.get("finding_type") == "secret" else "security_finding",
            escalation_reason=escalation_reason,
            created_at=_utc_iso(),
            title=finding.get("title", ""),
            description=finding.get("description", ""),
            target=finding.get("target", "."),
            file_path=finding.get("file_path"),
            package_name=finding.get("package_name"),
            analysis_proposal=analysis_proposal,
            state="escalated",
            requires_012=True,
        )

    def _create_alert_from_report(self, scan_report: Any) -> SecurityAlert:
        """Create alert from scan report with critical findings."""
        report_dict = scan_report.to_dict() if hasattr(scan_report, "to_dict") else scan_report

        # Find most critical finding
        findings = report_dict.get("findings", [])
        critical_finding = None
        for f in findings:
            if f.get("severity") == "critical":
                critical_finding = f
                break
        if not critical_finding and findings:
            critical_finding = findings[0]

        if critical_finding:
            return self.create_alert_from_finding(
                finding=critical_finding,
                escalation_reason=f"Critical finding from {report_dict.get('scan_tool', 'unknown')} scan",
            )

        # Fallback
        return SecurityAlert(
            finding_id="unknown",
            fingerprint="unknown",
            tool=report_dict.get("scan_tool", "unknown"),
            severity="critical",
            escalation_reason="Scan report requires 012 review",
            created_at=_utc_iso(),
        )

    def _determine_next_action(self) -> str:
        """Determine next operator action based on status."""
        if not self._status.any_tool_available:
            return "install_security_tools"
        if self._status.requires_012_count > 0:
            return "review_critical_alerts"
        if self._status.scans_executed == 0 and self._status.scans_proposed > 0:
            return "approve_proposed_scans"
        if self._status.findings_stored > 0:
            return "review_findings"
        return "none"


@dataclass
class DryRunResult:
    """Result of dry-run execution."""

    status: SecurityStackStatus
    reports: List[Dict[str, Any]]
    alerts: List[SecurityAlert]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "status": self.status.to_dict(),
            "reports": self.reports,
            "alerts": [a.to_dict() for a in self.alerts],
        }


# =========================================================================
# CLI Entrypoint
# =========================================================================

def main() -> int:
    """CLI entrypoint for 0102 manual invocation."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Security Stack Control Hooks - 0102 Entrypoint",
    )
    parser.add_argument(
        "command",
        choices=["status", "dry-run", "check-tools"],
        help="Command to run",
    )
    parser.add_argument(
        "--target",
        default=".",
        help="Path to scan (default: .)",
    )
    parser.add_argument(
        "--tools",
        nargs="+",
        help="Tools to use (default: all available)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    controller = SecurityStackController(report_only=True)

    if args.command == "status":
        status = controller.read_status()
        if status:
            print(status.to_json() if args.json else f"Last run: {status.last_run_at}\nState: {status.current_state}")
        else:
            print('{"error": "no status found"}' if args.json else "No status found")
        return 0

    if args.command == "check-tools":
        availability = controller.check_tool_availability()
        if args.json:
            print(json.dumps(availability, indent=2))
        else:
            for tool, available in availability.items():
                status_str = "available" if available else "unavailable"
                print(f"{tool}: {status_str}")
        return 0

    if args.command == "dry-run":
        result = controller.run_dry_run(target=args.target, tools=args.tools)
        if args.json:
            print(json.dumps(result.to_dict(), indent=2))
        else:
            print(f"State: {result.status.current_state}")
            print(f"Tools available: {result.status.tools_available}")
            print(f"Scans proposed: {result.status.scans_proposed}")
            print(f"Requires 012: {result.status.requires_012_count}")
            print(f"Next action: {result.status.next_operator_action}")
        return 0

    return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
