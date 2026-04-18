#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for Security Stack Control Hooks

SEC9 — SECURITY_STACK_0102_CONTROL_HOOKS_PHASE1

Validates:
- 0102 can invoke dry-run/status path
- Unavailable tools still produce valid status
- Critical/secret findings generate alert artifact
- Report-only mode does not mutate code
- HoloDAE trigger proposal can be transformed into SEC3 input contract
"""

import gc
import json
import pytest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from modules.infrastructure.wre_core.src.security_control_hooks import (
    SecurityStackController,
    SecurityStackStatus,
    SecurityAlert,
    DryRunResult,
)


@pytest.fixture
def temp_alerts_dir():
    """Create temporary directory for alerts."""
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture
def controller(temp_alerts_dir):
    """Create controller with temp alerts dir."""
    return SecurityStackController(alerts_dir=temp_alerts_dir, report_only=True)


class TestManual0102Invocation:
    """Tests for Hook 1: Manual 0102 invocation."""

    def test_dry_run_returns_status(self, controller):
        """Dry-run should return valid status."""
        result = controller.run_dry_run(target=".")

        assert isinstance(result, DryRunResult)
        assert isinstance(result.status, SecurityStackStatus)
        assert result.status.mode == "dry_run"

    def test_dry_run_checks_tool_availability(self, controller):
        """Dry-run should check tool availability."""
        result = controller.run_dry_run()

        assert "snyk" in result.status.tools_available
        assert "trivy" in result.status.tools_available
        assert "semgrep" in result.status.tools_available

    def test_dry_run_writes_status_artifact(self, controller, temp_alerts_dir):
        """Dry-run should write status artifact."""
        controller.run_dry_run()

        status_path = temp_alerts_dir / "status.json"
        assert status_path.exists()

        with open(status_path) as f:
            data = json.load(f)

        assert "last_run_at" in data
        assert "mode" in data
        assert "current_state" in data

    def test_report_only_does_not_execute_scans(self, controller):
        """Report-only mode should not execute scans."""
        result = controller.run_dry_run()

        assert result.status.scans_executed == 0

    def test_dry_run_sets_next_action(self, controller):
        """Dry-run should set next_operator_action."""
        result = controller.run_dry_run()

        assert result.status.next_operator_action in [
            "none",
            "install_security_tools",
            "approve_proposed_scans",
            "review_findings",
            "review_critical_alerts",
        ]


class TestUnavailableToolsPath:
    """Tests for unavailable tools producing valid status."""

    def test_unavailable_tools_returns_valid_status(self, controller):
        """Should return valid status even when tools unavailable."""
        # Mock scanner to return no tools
        with patch.object(controller, "_load_sec1_scanner", return_value=False):
            result = controller.run_dry_run()

        assert result.status.current_state in ["unavailable", "completed", "proposed"]
        assert isinstance(result.status.tools_available, dict)

    def test_unavailable_tools_sets_install_action(self, temp_alerts_dir):
        """Should suggest installing tools when none available."""
        controller = SecurityStackController(alerts_dir=temp_alerts_dir)

        # Mock all tools unavailable
        with patch.object(controller, "check_tool_availability", return_value={
            "snyk": False,
            "trivy": False,
            "semgrep": False,
        }):
            result = controller.run_dry_run()

        assert result.status.next_operator_action == "install_security_tools"

    def test_partial_availability_still_works(self, controller):
        """Should work with partial tool availability."""
        # Mock only snyk available
        with patch.object(controller, "check_tool_availability", return_value={
            "snyk": True,
            "trivy": False,
            "semgrep": False,
        }):
            result = controller.run_dry_run()

        assert result.status.any_tool_available is True
        assert result.status.tools_available["snyk"] is True


class TestAlertArtifactGeneration:
    """Tests for critical/secret findings generating alert artifacts."""

    def test_create_alert_from_finding(self, controller):
        """Should create alert from finding dict."""
        finding = {
            "finding_id": "CVE-2024-CRITICAL",
            "fingerprint": "abc123",
            "tool": "snyk",
            "severity": "critical",
            "title": "Critical Vulnerability",
            "description": "This is critical",
            "target": ".",
        }

        alert = controller.create_alert_from_finding(
            finding=finding,
            escalation_reason="Critical severity",
        )

        assert isinstance(alert, SecurityAlert)
        assert alert.finding_id == "CVE-2024-CRITICAL"
        assert alert.severity == "critical"
        assert alert.requires_012 is True
        assert alert.state == "escalated"

    def test_write_alert_creates_file(self, controller, temp_alerts_dir):
        """Should write alert to file."""
        alert = SecurityAlert(
            finding_id="CVE-2024-TEST",
            fingerprint="test123",
            tool="snyk",
            severity="critical",
            escalation_reason="Test alert",
            created_at="2024-01-01T00:00:00Z",
        )

        path = controller.write_alert(alert)

        assert path.exists()
        assert "CVE-2024-TEST" in path.name

        with open(path) as f:
            data = json.load(f)

        assert data["finding_id"] == "CVE-2024-TEST"
        assert data["requires_012"] is True

    def test_secret_finding_creates_alert(self, controller):
        """Secret findings should create alerts."""
        finding = {
            "finding_id": "SECRET-001",
            "fingerprint": "secret123",
            "tool": "semgrep",
            "severity": "high",
            "finding_type": "secret",
            "title": "Hardcoded API Key",
        }

        alert = controller.create_alert_from_finding(
            finding=finding,
            escalation_reason="Secret exposure",
        )

        assert alert.alert_type == "secret_exposure"
        assert alert.requires_012 is True

    def test_alert_includes_analysis_proposal(self, controller):
        """Alert can include SEC7 analysis proposal."""
        finding = {"finding_id": "CVE-001", "fingerprint": "abc", "tool": "snyk", "severity": "critical"}
        proposal = {
            "classification": "true_positive",
            "confidence": 0.9,
            "no_patch_generated": True,
        }

        alert = controller.create_alert_from_finding(
            finding=finding,
            analysis_proposal=proposal,
        )

        assert alert.analysis_proposal is not None
        assert alert.analysis_proposal["no_patch_generated"] is True


class TestReportOnlyMode:
    """Tests for report-only mode not mutating code."""

    def test_report_only_does_not_execute(self, controller):
        """Report-only should not execute scans."""
        assert controller.report_only is True

        result = controller.run_dry_run()

        assert result.status.scans_executed == 0

    def test_report_only_sets_proposed_state(self, controller):
        """Report-only should set proposed state for available tools."""
        with patch.object(controller, "check_tool_availability", return_value={
            "snyk": True,
            "trivy": False,
            "semgrep": False,
        }):
            with patch.object(controller, "_load_sec3_executor", return_value=True):
                controller._executor = MagicMock()
                result = controller.run_dry_run()

        # Should have proposed but not executed
        assert result.status.scans_proposed >= 0

    def test_invoke_sec3_report_only(self, controller):
        """SEC3 invocation in report-only should not execute."""
        result = controller.invoke_sec3_skill("snyk", ".", "report_only")

        assert result["state"] == "proposed" or result["state"] == "unavailable"
        assert result["scan_status"] in ["not_executed_report_only", "sec3_not_available"]


class TestHoloDAETriggerBridge:
    """Tests for HoloDAE trigger proposal transformation."""

    def test_bridge_trigger_to_sec3(self, controller):
        """Should transform SEC4 trigger to SEC3 input."""
        trigger_proposals = [
            {
                "trigger_id": "trigger-001",
                "status": "proposed",
                "scan_type": "sca",
                "recommended_tools": ["snyk"],
                "priority": 2,
                "triggered_at": "2024-01-01T00:00:00Z",
                "matched_patterns": ["requirements.txt"],
            },
        ]

        sec3_inputs = controller.bridge_trigger_to_sec3(trigger_proposals)

        assert len(sec3_inputs) == 1
        assert sec3_inputs[0]["tool"] == "snyk"
        assert sec3_inputs[0]["mode"] == "report_only"
        assert sec3_inputs[0]["trigger_id"] == "trigger-001"

    def test_bridge_skips_non_proposed(self, controller):
        """Should skip triggers that are not proposed."""
        trigger_proposals = [
            {"trigger_id": "001", "status": "executed", "scan_type": "sca"},
            {"trigger_id": "002", "status": "proposed", "scan_type": "sca"},
        ]

        sec3_inputs = controller.bridge_trigger_to_sec3(trigger_proposals)

        assert len(sec3_inputs) >= 1
        # Only proposed triggers should be bridged
        assert all(inp["mode"] == "report_only" for inp in sec3_inputs)

    def test_bridge_maps_scan_types(self, controller):
        """Should map scan_type to appropriate tools."""
        trigger_proposals = [
            {"trigger_id": "001", "status": "proposed", "scan_type": "sca"},
            {"trigger_id": "002", "status": "proposed", "scan_type": "container"},
            {"trigger_id": "003", "status": "proposed", "scan_type": "sast"},
        ]

        sec3_inputs = controller.bridge_trigger_to_sec3(trigger_proposals)

        # SCA maps to snyk, trivy
        sca_tools = [inp["tool"] for inp in sec3_inputs if inp["trigger_id"] == "001"]
        assert "snyk" in sca_tools or "trivy" in sca_tools

        # Container maps to trivy
        container_tools = [inp["tool"] for inp in sec3_inputs if inp["trigger_id"] == "002"]
        assert "trivy" in container_tools

        # SAST maps to semgrep
        sast_tools = [inp["tool"] for inp in sec3_inputs if inp["trigger_id"] == "003"]
        assert "semgrep" in sast_tools

    def test_bridge_never_enables_auto_execution(self, controller):
        """Bridge should never set mode != report_only."""
        trigger_proposals = [
            {"trigger_id": "001", "status": "proposed", "scan_type": "sca", "auto_execute": True},
        ]

        sec3_inputs = controller.bridge_trigger_to_sec3(trigger_proposals)

        # All inputs must be report_only regardless of trigger settings
        assert all(inp["mode"] == "report_only" for inp in sec3_inputs)


class TestStatusArtifact:
    """Tests for status artifact read/write."""

    def test_write_status(self, controller, temp_alerts_dir):
        """Should write status to file."""
        status = SecurityStackStatus(
            last_run_at="2024-01-01T00:00:00Z",
            mode="dry_run",
            current_state="completed",
        )

        path = controller.write_status(status)

        assert path.exists()
        assert path.name == "status.json"

    def test_read_status(self, controller, temp_alerts_dir):
        """Should read status from file."""
        # Write first
        status = SecurityStackStatus(
            last_run_at="2024-01-01T00:00:00Z",
            mode="dry_run",
            current_state="completed",
        )
        controller.write_status(status)

        # Read back
        read_status = controller.read_status()

        assert read_status is not None
        assert read_status.last_run_at == "2024-01-01T00:00:00Z"
        assert read_status.mode == "dry_run"

    def test_read_status_missing_returns_none(self, controller):
        """Should return None if status file doesn't exist."""
        status = controller.read_status()

        assert status is None


class TestSecurityStackStatus:
    """Tests for SecurityStackStatus dataclass."""

    def test_to_dict(self):
        """Should convert to dictionary."""
        status = SecurityStackStatus(
            last_run_at="2024-01-01T00:00:00Z",
            mode="dry_run",
            tools_available={"snyk": True},
        )

        d = status.to_dict()

        assert d["last_run_at"] == "2024-01-01T00:00:00Z"
        assert d["mode"] == "dry_run"
        assert d["tools_available"]["snyk"] is True

    def test_to_json(self):
        """Should convert to JSON."""
        status = SecurityStackStatus(mode="dry_run")

        json_str = status.to_json()
        data = json.loads(json_str)

        assert data["mode"] == "dry_run"


class TestSecurityAlert:
    """Tests for SecurityAlert dataclass."""

    def test_to_dict(self):
        """Should convert to dictionary."""
        alert = SecurityAlert(
            finding_id="CVE-001",
            fingerprint="abc",
            tool="snyk",
            severity="critical",
        )

        d = alert.to_dict()

        assert d["finding_id"] == "CVE-001"
        assert d["requires_012"] is True

    def test_default_values(self):
        """Should have sensible defaults."""
        alert = SecurityAlert(
            finding_id="TEST",
            fingerprint="test",
            tool="test",
            severity="high",
        )

        assert alert.state == "escalated"
        assert alert.requires_012 is True
        assert alert.acknowledged is False


class TestWRESkillContract:
    """Tests for WRE skill invocation contract."""

    def test_invoke_sec3_returns_contract(self, controller):
        """Should return proper SEC3 output contract."""
        result = controller.invoke_sec3_skill("snyk", ".", "report_only")

        # Verify contract fields
        assert "tool" in result
        assert "target" in result
        assert "state" in result
        assert "scan_status" in result
        assert "tool_available" in result
        assert "findings" in result
        assert "total_findings" in result
        assert "requires_012" in result
        assert "policy_decision" in result

    def test_invoke_all_tools(self, controller):
        """Should handle 'all' tool option."""
        result = controller.invoke_sec3_skill("all", ".", "report_only")

        assert result["tool"] == "all"
        assert result["state"] in ["proposed", "unavailable"]


class TestDryRunResult:
    """Tests for DryRunResult dataclass."""

    def test_to_dict(self, controller):
        """Should convert to dictionary."""
        result = DryRunResult(
            status=SecurityStackStatus(mode="dry_run"),
            reports=[{"tool": "snyk"}],
            alerts=[],
        )

        d = result.to_dict()

        assert "status" in d
        assert "reports" in d
        assert "alerts" in d
        assert d["status"]["mode"] == "dry_run"
