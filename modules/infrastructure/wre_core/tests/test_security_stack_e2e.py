#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Security Stack E2E Dry-Run Tests

SEC8 — SECURITY_STACK_E2E_DRY_RUN_PHASE1

Proves the merged SEC1-SEC7 stack works end-to-end using synthetic
or mocked scan output. No live scanners, no real vulnerabilities claimed.

Flow:
1. Synthetic finding (mocked SEC1 output)
2. SEC2 policy routing
3. SEC5 pattern memory storage
4. SEC6 recall
5. SEC7 analysis proposal
6. E2E report artifact

Hard constraints:
- No live Snyk/Trivy/Semgrep
- No code mutation
- No auto-remediation
- no_patch_generated: true
- requires_012 preserved for critical findings
"""

import gc
import json
import pytest
import tempfile
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

# SEC2: Policy
from modules.ai_intelligence.ai_overseer.src.vulnerability_scan_policy import (
    VulnerabilityScanPolicy,
    SeverityLevel,
    FindingType,
    EscalationDestination,
)

# SEC5: Pattern Memory
from modules.infrastructure.wre_core.src.security_pattern_memory import (
    SecurityPatternMemory,
    SecurityFinding,
)

# SEC6: Recall
from modules.infrastructure.wre_core.src.security_recall import (
    SecurityRecall,
)

# SEC7: Analysis Assistant
from modules.infrastructure.wre_core.src.security_analysis_assistant import (
    SecurityAnalysisAssistant,
    AnalysisProposal,
)


def _utc_iso() -> str:
    """Return current UTC timestamp as ISO string."""
    return datetime.now(timezone.utc).isoformat()


# Synthetic findings for E2E testing
SYNTHETIC_FINDINGS = [
    {
        "finding_id": "CVE-2024-SYNTHETIC-001",
        "tool": "snyk",
        "severity": "critical",
        "title": "Synthetic Critical Vulnerability",
        "description": "This is a synthetic finding for E2E testing. NOT a real vulnerability.",
        "package_name": "synthetic-pkg",
        "package_version": "1.0.0",
        "target": ".",
    },
    {
        "finding_id": "CVE-2024-SYNTHETIC-002",
        "tool": "trivy",
        "severity": "high",
        "title": "Synthetic High Vulnerability",
        "description": "This is a synthetic HIGH severity finding for testing.",
        "package_name": "test-pkg",
        "package_version": "2.0.0",
        "target": ".",
    },
    {
        "finding_id": "SEMGREP-SYNTHETIC-003",
        "tool": "semgrep",
        "severity": "medium",
        "title": "Synthetic SQL Injection Pattern",
        "description": "Synthetic SAST finding for testing. NOT a real vulnerability.",
        "file_path": "test/synthetic.py",
        "line_number": 42,
        "target": "test/synthetic.py",
    },
]


@pytest.fixture
def temp_db():
    """Create temporary database for E2E tests."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)

    memory = SecurityPatternMemory(db_path=db_path)
    yield memory

    memory.close()
    gc.collect()
    try:
        db_path.unlink()
    except PermissionError:
        pass


@pytest.fixture
def temp_report_dir():
    """Create temporary directory for report artifacts."""
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


class TestE2EDryRun:
    """E2E dry-run tests for SEC1-SEC7 stack."""

    def test_full_stack_critical_finding(self, temp_db, temp_report_dir):
        """
        E2E: Critical finding flows through entire stack.

        1. Synthetic finding (SEC1 output format)
        2. Policy routes to GATE_012 (SEC2)
        3. Stored in pattern memory (SEC5)
        4. Recalled with context (SEC6)
        5. Analysis proposal generated (SEC7)
        6. Report artifact written
        """
        finding = SYNTHETIC_FINDINGS[0].copy()
        fingerprint = SecurityFinding.compute_fingerprint(
            tool=finding["tool"],
            finding_id=finding["finding_id"],
            target=finding["target"],
            package_name=finding.get("package_name"),
        )
        finding["fingerprint"] = fingerprint

        # SEC2: Policy routing
        policy = VulnerabilityScanPolicy()
        escalation = policy.get_escalation(
            severity=SeverityLevel.CRITICAL,
            finding_type=FindingType.DEPENDENCY,
        )

        assert escalation.escalation.value == "gate_012"
        requires_012 = escalation.requires_012

        # SEC5: Store in pattern memory
        stored_finding = SecurityFinding(
            fingerprint=fingerprint,
            finding_id=finding["finding_id"],
            tool=finding["tool"],
            target=finding["target"],
            package_name=finding.get("package_name"),
            severity=finding["severity"],
            title=finding["title"],
            description=finding["description"],
            policy_decision="gate_012",
            requires_012=requires_012,
            status="open",
        )
        is_new = temp_db.store_finding(stored_finding)
        assert is_new is True

        # SEC6: Recall with context
        recall = SecurityRecall(temp_db)
        recall_result = recall.recall_by_fingerprint(fingerprint)

        assert recall_result.match_found is True
        assert recall_result.exact_match is True

        # SEC7: Analysis proposal
        assistant = SecurityAnalysisAssistant(
            enable_qwen=False,
            enable_gemma=False,
            proposal_output_dir=temp_report_dir,
        )

        proposal = assistant.analyze_finding(
            finding=finding,
            policy_decision="gate_012",
            requires_012=requires_012,
            recall_context=recall_result.to_dict(),
        )

        # Validate proposal invariants
        assert proposal.no_patch_generated is True
        assert proposal.requires_012 is True  # Critical finding
        assert proposal.classification in ("true_positive", "false_positive", "needs_review")
        assert proposal.recall_context_included is True

        # Write report artifact
        report_path = assistant.write_proposal_artifact(proposal)
        assert report_path is not None
        assert report_path.exists()

        # Verify report content
        with open(report_path) as f:
            report_data = json.load(f)

        assert report_data["finding_id"] == "CVE-2024-SYNTHETIC-001"
        assert report_data["no_patch_generated"] is True
        assert report_data["requires_012"] is True

    def test_full_stack_high_finding(self, temp_db, temp_report_dir):
        """E2E: High severity finding flows through stack."""
        finding = SYNTHETIC_FINDINGS[1].copy()
        fingerprint = SecurityFinding.compute_fingerprint(
            tool=finding["tool"],
            finding_id=finding["finding_id"],
            target=finding["target"],
            package_name=finding.get("package_name"),
        )
        finding["fingerprint"] = fingerprint

        # SEC2: Policy routing for HIGH
        policy = VulnerabilityScanPolicy()
        escalation = policy.get_escalation(
            severity=SeverityLevel.HIGH,
            finding_type=FindingType.DEPENDENCY,
        )

        # HIGH may or may not gate to 012 depending on policy
        requires_012 = escalation.requires_012

        # SEC5: Store
        stored_finding = SecurityFinding(
            fingerprint=fingerprint,
            finding_id=finding["finding_id"],
            tool=finding["tool"],
            target=finding["target"],
            package_name=finding.get("package_name"),
            severity=finding["severity"],
            title=finding["title"],
            policy_decision=escalation.escalation.value,
            requires_012=requires_012,
            status="open",
        )
        temp_db.store_finding(stored_finding)

        # SEC6: Recall
        recall = SecurityRecall(temp_db)
        recall_result = recall.recall_by_fingerprint(fingerprint)
        assert recall_result.match_found is True

        # SEC7: Analysis
        assistant = SecurityAnalysisAssistant(
            enable_qwen=False,
            enable_gemma=False,
        )

        proposal = assistant.analyze_finding(
            finding=finding,
            policy_decision=escalation.escalation.value,
            requires_012=requires_012,
            recall_context=recall_result.to_dict(),
        )

        assert proposal.no_patch_generated is True
        assert proposal.severity == "high"

    def test_full_stack_medium_finding(self, temp_db):
        """E2E: Medium severity SAST finding flows through stack."""
        finding = SYNTHETIC_FINDINGS[2].copy()
        fingerprint = SecurityFinding.compute_fingerprint(
            tool=finding["tool"],
            finding_id=finding["finding_id"],
            target=finding["target"],
            package_name=None,
        )
        finding["fingerprint"] = fingerprint

        # SEC2: Policy routing for MEDIUM
        policy = VulnerabilityScanPolicy()
        escalation = policy.get_escalation(
            severity=SeverityLevel.MEDIUM,
            finding_type=FindingType.SAST,
        )

        # SEC5: Store
        stored_finding = SecurityFinding(
            fingerprint=fingerprint,
            finding_id=finding["finding_id"],
            tool=finding["tool"],
            target=finding["target"],
            file_path=finding.get("file_path"),
            line_number=finding.get("line_number"),
            severity=finding["severity"],
            title=finding["title"],
            policy_decision=escalation.escalation.value,
            requires_012=escalation.requires_012,
            status="open",
        )
        temp_db.store_finding(stored_finding)

        # SEC6: Recall
        recall = SecurityRecall(temp_db)
        recall_result = recall.recall_by_fingerprint(fingerprint)
        assert recall_result.match_found is True

        # SEC7: Analysis
        assistant = SecurityAnalysisAssistant(enable_qwen=False, enable_gemma=False)
        proposal = assistant.analyze_finding(
            finding=finding,
            policy_decision=escalation.escalation.value,
            requires_012=escalation.requires_012,
            recall_context=recall_result.to_dict(),
        )

        assert proposal.no_patch_generated is True
        # File path should be included if provided
        if finding.get("file_path"):
            assert finding["file_path"] in proposal.files_likely_affected

    def test_recall_influences_repeated_finding(self, temp_db):
        """E2E: Repeated finding gets recall context from history."""
        finding = SYNTHETIC_FINDINGS[0].copy()
        fingerprint = SecurityFinding.compute_fingerprint(
            tool=finding["tool"],
            finding_id=finding["finding_id"],
            target=finding["target"],
            package_name=finding.get("package_name"),
        )
        finding["fingerprint"] = fingerprint

        # First occurrence - mark as false_positive
        first_finding = SecurityFinding(
            fingerprint=fingerprint,
            finding_id=finding["finding_id"],
            tool=finding["tool"],
            target=finding["target"],
            package_name=finding.get("package_name"),
            severity=finding["severity"],
            title=finding["title"],
            status="false_positive",  # Previously marked
        )
        temp_db.store_finding(first_finding)

        # Second occurrence - should recall history
        recall = SecurityRecall(temp_db)
        recall_result = recall.recall_by_fingerprint(fingerprint)

        assert recall_result.match_found is True
        assert recall_result.suggested_outcome == "false_positive"
        assert recall_result.suggestion_confidence >= 0.9

        # Analysis should incorporate recall
        assistant = SecurityAnalysisAssistant(enable_qwen=False, enable_gemma=False)
        proposal = assistant.analyze_finding(
            finding=finding,
            recall_context=recall_result.to_dict(),
        )

        # Historical context should influence classification
        assert proposal.recall_context_included is True
        assert proposal.suggested_outcome_from_history == "false_positive"


class TestE2EReportGeneration:
    """Tests for E2E report artifact generation."""

    def test_generates_complete_report(self, temp_db, temp_report_dir):
        """Should generate complete E2E report with all findings."""
        reports = []

        for finding_data in SYNTHETIC_FINDINGS:
            finding = finding_data.copy()
            fingerprint = SecurityFinding.compute_fingerprint(
                tool=finding["tool"],
                finding_id=finding["finding_id"],
                target=finding["target"],
                package_name=finding.get("package_name"),
            )
            finding["fingerprint"] = fingerprint

            # Policy
            policy = VulnerabilityScanPolicy()
            severity = SeverityLevel[finding["severity"].upper()]
            escalation = policy.get_escalation(severity=severity, finding_type=FindingType.DEPENDENCY)

            # Store
            stored = SecurityFinding(
                fingerprint=fingerprint,
                finding_id=finding["finding_id"],
                tool=finding["tool"],
                target=finding["target"],
                package_name=finding.get("package_name"),
                file_path=finding.get("file_path"),
                severity=finding["severity"],
                title=finding["title"],
                policy_decision=escalation.escalation.value,
                requires_012=escalation.requires_012,
            )
            temp_db.store_finding(stored)

            # Recall
            recall = SecurityRecall(temp_db)
            recall_result = recall.recall_by_fingerprint(fingerprint)

            # Analyze
            assistant = SecurityAnalysisAssistant(
                enable_qwen=False,
                enable_gemma=False,
                proposal_output_dir=temp_report_dir,
            )
            proposal = assistant.analyze_finding(
                finding=finding,
                policy_decision=escalation.escalation.value,
                requires_012=escalation.requires_012,
                recall_context=recall_result.to_dict(),
            )

            # Write artifact
            path = assistant.write_proposal_artifact(proposal)
            reports.append({"path": path, "proposal": proposal})

        # Verify all reports generated
        assert len(reports) == 3

        # Verify critical finding has requires_012
        critical_report = next(
            r for r in reports if r["proposal"].severity == "critical"
        )
        assert critical_report["proposal"].requires_012 is True
        assert critical_report["proposal"].no_patch_generated is True

    def test_report_contains_synthetic_marker(self, temp_db, temp_report_dir):
        """Report should indicate synthetic/test data."""
        finding = SYNTHETIC_FINDINGS[0].copy()
        fingerprint = SecurityFinding.compute_fingerprint(
            tool=finding["tool"],
            finding_id=finding["finding_id"],
            target=finding["target"],
            package_name=finding.get("package_name"),
        )
        finding["fingerprint"] = fingerprint

        assistant = SecurityAnalysisAssistant(
            enable_qwen=False,
            enable_gemma=False,
            proposal_output_dir=temp_report_dir,
        )

        proposal = assistant.analyze_finding(finding)
        path = assistant.write_proposal_artifact(proposal)

        with open(path) as f:
            data = json.load(f)

        # Finding ID contains SYNTHETIC marker
        assert "SYNTHETIC" in data["finding_id"]


class TestE2EInvariants:
    """Tests for E2E invariants that must hold."""

    def test_no_patch_generated_always_true(self, temp_db):
        """no_patch_generated must be True for all findings."""
        assistant = SecurityAnalysisAssistant(enable_qwen=False, enable_gemma=False)

        for finding_data in SYNTHETIC_FINDINGS:
            finding = finding_data.copy()
            fingerprint = SecurityFinding.compute_fingerprint(
                tool=finding["tool"],
                finding_id=finding["finding_id"],
                target=finding["target"],
                package_name=finding.get("package_name"),
            )
            finding["fingerprint"] = fingerprint

            proposal = assistant.analyze_finding(finding)

            assert proposal.no_patch_generated is True, (
                f"no_patch_generated was False for {finding['finding_id']}"
            )

    def test_critical_always_requires_012(self, temp_db):
        """Critical findings must require 012 review."""
        policy = VulnerabilityScanPolicy()
        escalation = policy.get_escalation(
            severity=SeverityLevel.CRITICAL,
            finding_type=FindingType.DEPENDENCY,
        )

        assert escalation.requires_012 is True
        assert escalation.escalation.value == "gate_012"

    def test_policy_decision_preserved(self, temp_db):
        """Policy decision must be preserved through stack."""
        finding = SYNTHETIC_FINDINGS[0].copy()
        fingerprint = SecurityFinding.compute_fingerprint(
            tool=finding["tool"],
            finding_id=finding["finding_id"],
            target=finding["target"],
            package_name=finding.get("package_name"),
        )
        finding["fingerprint"] = fingerprint

        # Policy says gate_012
        policy = VulnerabilityScanPolicy()
        escalation = policy.get_escalation(
            severity=SeverityLevel.CRITICAL,
            finding_type=FindingType.DEPENDENCY,
        )
        policy_decision = escalation.escalation.value
        requires_012 = escalation.requires_012

        # Analysis must preserve
        assistant = SecurityAnalysisAssistant(enable_qwen=False, enable_gemma=False)
        proposal = assistant.analyze_finding(
            finding=finding,
            policy_decision=policy_decision,
            requires_012=requires_012,
        )

        assert proposal.requires_012 == requires_012

    def test_no_live_scanner_invocation(self, temp_db):
        """E2E tests must not invoke live scanners."""
        # This test verifies we're using synthetic data
        # by checking that we never import or call SecurityScanner
        import sys

        # SecurityScanner should not be imported in test modules
        test_modules = [m for m in sys.modules if "test_security_stack_e2e" in m]
        for mod_name in test_modules:
            mod = sys.modules[mod_name]
            # Verify no SecurityScanner instance
            assert not hasattr(mod, "SecurityScanner"), (
                "SecurityScanner should not be imported in E2E tests"
            )


class TestE2ESummary:
    """Generate E2E summary report."""

    def test_generate_e2e_summary(self, temp_db, temp_report_dir):
        """Generate comprehensive E2E summary."""
        results = {
            "test_run": _utc_iso(),
            "synthetic_findings_tested": len(SYNTHETIC_FINDINGS),
            "components_validated": [
                "SEC2_policy_routing",
                "SEC5_pattern_memory",
                "SEC6_recall",
                "SEC7_analysis_proposal",
            ],
            "invariants_verified": [
                "no_patch_generated_always_true",
                "critical_requires_012",
                "policy_decision_preserved",
                "no_live_scanner_invocation",
            ],
            "findings": [],
        }

        assistant = SecurityAnalysisAssistant(
            enable_qwen=False,
            enable_gemma=False,
        )

        for finding_data in SYNTHETIC_FINDINGS:
            finding = finding_data.copy()
            fingerprint = SecurityFinding.compute_fingerprint(
                tool=finding["tool"],
                finding_id=finding["finding_id"],
                target=finding["target"],
                package_name=finding.get("package_name"),
            )
            finding["fingerprint"] = fingerprint

            # Policy
            policy = VulnerabilityScanPolicy()
            severity = SeverityLevel[finding["severity"].upper()]
            escalation = policy.get_escalation(severity=severity, finding_type=FindingType.DEPENDENCY)

            # Store
            stored = SecurityFinding(
                fingerprint=fingerprint,
                finding_id=finding["finding_id"],
                tool=finding["tool"],
                target=finding["target"],
                severity=finding["severity"],
                title=finding["title"],
                policy_decision=escalation.escalation.value,
                requires_012=escalation.requires_012,
            )
            temp_db.store_finding(stored)

            # Recall
            recall = SecurityRecall(temp_db)
            recall_result = recall.recall_by_fingerprint(fingerprint)

            # Analyze
            proposal = assistant.analyze_finding(
                finding=finding,
                policy_decision=escalation.escalation.value,
                requires_012=escalation.requires_012,
                recall_context=recall_result.to_dict(),
            )

            results["findings"].append({
                "finding_id": finding["finding_id"],
                "severity": finding["severity"],
                "tool": finding["tool"],
                "policy_decision": escalation.escalation.value,
                "requires_012": escalation.requires_012,
                "classification": proposal.classification,
                "no_patch_generated": proposal.no_patch_generated,
                "recall_context_included": proposal.recall_context_included,
            })

        # Write summary
        summary_path = temp_report_dir / "e2e_dry_run_summary.json"
        with open(summary_path, "w") as f:
            json.dump(results, f, indent=2)

        assert summary_path.exists()

        # Verify summary content
        with open(summary_path) as f:
            loaded = json.load(f)

        assert loaded["synthetic_findings_tested"] == 3
        assert len(loaded["findings"]) == 3
        assert all(f["no_patch_generated"] for f in loaded["findings"])
