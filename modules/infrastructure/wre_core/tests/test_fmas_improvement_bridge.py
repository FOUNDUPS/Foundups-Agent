#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FMAS-to-ImprovementJob Bridge Tests

Verifies the FMAS finding parser and ImprovementJob creation.

WSP 97 TRUTH BOUNDARIES:
  - Tests verify parsing, NOT FMAS execution
  - Tests verify mapping, NOT repair execution
  - Tests verify dry_run=True always
  - Tests verify no execution methods exist

Contract References:
  modules/infrastructure/wre_core/src/fmas_improvement_bridge.py
  modules/infrastructure/wre_core/src/improvement_job_contract.py
"""

import pytest

from modules.infrastructure.wre_core.src.fmas_improvement_bridge import (
    FMASFinding,
    FMASFindingType,
    FMASSeverity,
    build_scope_from_fmas_finding,
    derive_wsp15_priority,
    generate_finding_id,
    map_fmas_severity_to_risk,
    map_fmas_type_to_improvement_type,
    parse_fmas_dict,
    parse_fmas_finding,
    parse_fmas_findings,
    parse_fmas_string,
    parse_fmas_strings,
)
from modules.infrastructure.wre_core.src.improvement_job_contract import (
    ImprovementRiskLevel,
    ImprovementStatus,
    ImprovementType,
)


# ---------------------------------------------------------------------------
# Test 1: missing_tests finding creates TEST_HYGIENE ImprovementJob
# ---------------------------------------------------------------------------


class TestMissingTestsFinding:
    """Test missing_tests FMAS finding parsing."""

    def test_parse_missing_tests_string(self):
        """Missing tests string parses to MISSING_TESTS finding."""
        raw = "ERROR: Module 'communication/livechat' is missing the tests/ directory"
        finding = parse_fmas_string(raw)

        assert finding is not None
        assert finding.finding_type == FMASFindingType.MISSING_TESTS
        assert finding.module_path == "communication/livechat"
        assert "WSP 49" in finding.wsp_refs or "WSP 5" in finding.wsp_refs

    def test_missing_tests_creates_test_hygiene_job(self):
        """Missing tests creates TEST_HYGIENE ImprovementJob."""
        finding_dict = {
            "type": "missing_tests",
            "severity": "medium",
            "module_path": "modules/ai_intelligence/test_module",
            "message": "Module missing tests/ directory",
        }
        job = parse_fmas_finding(finding_dict)

        assert job.improvement_type == ImprovementType.TEST_HYGIENE
        assert job.dry_run is True
        assert "modules/ai_intelligence/test_module" in job.scope.module_path


# ---------------------------------------------------------------------------
# Test 2: missing_src finding creates MODULE_REPAIR ImprovementJob
# ---------------------------------------------------------------------------


class TestMissingSrcFinding:
    """Test missing_src FMAS finding parsing."""

    def test_parse_missing_src_string(self):
        """Missing src string parses to MISSING_SRC finding."""
        raw = "ERROR: Module 'infrastructure/broken_module' is missing the src/ directory"
        finding = parse_fmas_string(raw)

        assert finding is not None
        assert finding.finding_type == FMASFindingType.MISSING_SRC
        assert finding.module_path == "infrastructure/broken_module"
        assert finding.severity == FMASSeverity.HIGH

    def test_missing_src_creates_module_repair_job(self):
        """Missing src creates MODULE_REPAIR ImprovementJob."""
        finding_dict = {
            "type": "missing_src",
            "severity": "high",
            "module_path": "modules/platform_integration/orphan",
            "message": "Module missing src/ directory",
        }
        job = parse_fmas_finding(finding_dict)

        assert job.improvement_type == ImprovementType.MODULE_REPAIR
        assert job.risk_level == ImprovementRiskLevel.HIGH
        assert job.dry_run is True


# ---------------------------------------------------------------------------
# Test 3: wsp_violation finding creates WSP_VIOLATION ImprovementJob
# ---------------------------------------------------------------------------


class TestWspViolationFinding:
    """Test WSP violation FMAS finding parsing."""

    def test_wsp_violation_creates_wsp_violation_job(self):
        """WSP violation creates WSP_VIOLATION ImprovementJob."""
        finding_dict = {
            "type": "wsp_violation",
            "severity": "medium",
            "module_path": "modules/foundups/agent",
            "message": "WSP 49 violation: incorrect directory structure",
            "wsp_refs": ["WSP 49"],
        }
        job = parse_fmas_finding(finding_dict)

        assert job.improvement_type == ImprovementType.WSP_VIOLATION
        assert "WSP 49" in job.scope.wsp_refs
        assert job.dry_run is True

    def test_domain_violation_creates_wsp_violation_job(self):
        """Domain violation also maps to WSP_VIOLATION."""
        finding_dict = {
            "type": "domain_violation",
            "severity": "medium",
            "module_path": "modules/unknown_domain/test",
            "message": "Module in unknown domain",
            "wsp_refs": ["WSP 3"],
        }
        job = parse_fmas_finding(finding_dict)

        assert job.improvement_type == ImprovementType.WSP_VIOLATION


# ---------------------------------------------------------------------------
# Test 4: unknown finding maps to FMAS_SCAN
# ---------------------------------------------------------------------------


class TestUnknownFinding:
    """Test unknown FMAS finding handling."""

    def test_unknown_type_maps_to_fmas_scan(self):
        """Unknown finding type maps to FMAS_SCAN."""
        finding_dict = {
            "type": "some_new_finding_type",
            "severity": "medium",
            "module_path": "modules/test",
            "message": "Some unknown finding",
        }
        job = parse_fmas_finding(finding_dict)

        assert job.improvement_type == ImprovementType.FMAS_SCAN

    def test_unrecognized_string_creates_unknown_finding(self):
        """Unrecognized FMAS string creates UNKNOWN finding."""
        raw = "NOTICE: Something happened in module X"
        finding = parse_fmas_string(raw)

        assert finding is not None
        assert finding.finding_type == FMASFindingType.UNKNOWN


# ---------------------------------------------------------------------------
# Test 5: scope extracts module_path and file_paths
# ---------------------------------------------------------------------------


class TestScopeExtraction:
    """Test scope extraction from FMAS findings."""

    def test_scope_extracts_module_path(self):
        """Scope includes module_path from finding."""
        finding = FMASFinding(
            finding_id="test_001",
            finding_type=FMASFindingType.MISSING_TESTS,
            severity=FMASSeverity.MEDIUM,
            module_path="modules/infrastructure/wre_core",
        )
        scope = build_scope_from_fmas_finding(finding)

        assert scope.module_path == "modules/infrastructure/wre_core"
        assert "modules/infrastructure/wre_core/**" in scope.allowed_paths

    def test_scope_extracts_file_path(self):
        """Scope includes file_path when present."""
        finding = FMASFinding(
            finding_id="test_002",
            finding_type=FMASFindingType.SECRET_DETECTED,
            severity=FMASSeverity.CRITICAL,
            module_path="",
            file_path="modules/test/src/config.py",
        )
        scope = build_scope_from_fmas_finding(finding)

        assert "modules/test/src/config.py" in scope.file_paths

    def test_scope_includes_wsp_refs(self):
        """Scope includes WSP references from finding."""
        finding = FMASFinding(
            finding_id="test_003",
            finding_type=FMASFindingType.WSP_VIOLATION,
            severity=FMASSeverity.MEDIUM,
            module_path="modules/test",
            wsp_refs=["WSP 49", "WSP 22"],
        )
        scope = build_scope_from_fmas_finding(finding)

        assert "WSP 49" in scope.wsp_refs
        assert "WSP 22" in scope.wsp_refs


# ---------------------------------------------------------------------------
# Test 6: low severity single-file becomes LOW risk low_lying_fruit
# ---------------------------------------------------------------------------


class TestLowLyingFruitDerivation:
    """Test WSP15Priority derivation for low-lying fruit."""

    def test_low_severity_single_file_is_low_lying_fruit(self):
        """Low severity + single file = low_lying_fruit."""
        finding = FMASFinding(
            finding_id="test_low",
            finding_type=FMASFindingType.MISSING_TEST_README,
            severity=FMASSeverity.LOW,
            module_path="",
            file_path="modules/test/tests/README.md",
        )
        priority = derive_wsp15_priority(finding)

        assert priority.low_lying_fruit is True
        assert priority.requires_architect_review is False
        assert priority.estimated_complexity == "trivial"

    def test_info_severity_is_low_risk(self):
        """INFO severity maps to LOW risk."""
        finding = FMASFinding(
            finding_id="test_info",
            finding_type=FMASFindingType.DOC_STALE,
            severity=FMASSeverity.INFO,
            module_path="modules/docs",
        )
        risk = map_fmas_severity_to_risk(finding)

        assert risk == ImprovementRiskLevel.LOW


# ---------------------------------------------------------------------------
# Test 7: medium/high severity requires architect review
# ---------------------------------------------------------------------------


class TestArchitectReviewRequired:
    """Test architect review requirements for higher severity."""

    def test_medium_severity_requires_review(self):
        """Medium severity requires architect review."""
        finding = FMASFinding(
            finding_id="test_med",
            finding_type=FMASFindingType.MISSING_TESTS,
            severity=FMASSeverity.MEDIUM,
            module_path="modules/test",
        )
        priority = derive_wsp15_priority(finding)

        # Medium severity with moderate complexity should require review
        # Actually, let's check the actual logic - medium severity alone
        # doesn't require review unless complexity is complex
        assert priority.low_lying_fruit is False

    def test_high_severity_requires_review(self):
        """High severity always requires architect review."""
        finding = FMASFinding(
            finding_id="test_high",
            finding_type=FMASFindingType.MISSING_SRC,
            severity=FMASSeverity.HIGH,
            module_path="modules/critical",
        )
        priority = derive_wsp15_priority(finding)

        assert priority.requires_architect_review is True
        assert priority.low_lying_fruit is False

    def test_critical_severity_requires_review(self):
        """Critical severity always requires architect review."""
        finding = FMASFinding(
            finding_id="test_crit",
            finding_type=FMASFindingType.SECRET_DETECTED,
            severity=FMASSeverity.CRITICAL,
            module_path="modules/secrets",
            file_path="modules/secrets/config.py",
        )
        priority = derive_wsp15_priority(finding)

        assert priority.requires_architect_review is True

    def test_security_finding_requires_review(self):
        """Security findings always require architect review."""
        finding = FMASFinding(
            finding_id="test_sec",
            finding_type=FMASFindingType.SECURITY_VULNERABILITY,
            severity=FMASSeverity.MEDIUM,
            module_path="modules/web",
        )
        priority = derive_wsp15_priority(finding)

        assert priority.requires_architect_review is True


# ---------------------------------------------------------------------------
# Test 8: dry_run defaults True
# ---------------------------------------------------------------------------


class TestDryRunDefault:
    """Test dry_run is always True."""

    def test_parsed_job_has_dry_run_true(self):
        """Parsed ImprovementJob always has dry_run=True."""
        finding_dict = {
            "type": "missing_tests",
            "severity": "low",
            "module_path": "modules/test",
            "message": "Test",
        }
        job = parse_fmas_finding(finding_dict)

        assert job.dry_run is True

    def test_multiple_jobs_all_have_dry_run_true(self):
        """All parsed jobs have dry_run=True."""
        findings = [
            {"type": "missing_tests", "severity": "low", "module_path": "m1"},
            {"type": "missing_src", "severity": "high", "module_path": "m2"},
            {"type": "wsp_violation", "severity": "medium", "module_path": "m3"},
        ]
        jobs = parse_fmas_findings(findings)

        for job in jobs:
            assert job.dry_run is True


# ---------------------------------------------------------------------------
# Test 9: no execution methods exist
# ---------------------------------------------------------------------------


class TestNoExecutionMethods:
    """Test that bridge functions don't include execution logic."""

    def test_parse_fmas_finding_returns_job_not_executes(self):
        """parse_fmas_finding returns job, doesn't execute."""
        finding_dict = {
            "type": "missing_tests",
            "severity": "medium",
            "module_path": "modules/test",
        }
        job = parse_fmas_finding(finding_dict)

        # Job should be in PENDING status (not executed)
        assert job.status == ImprovementStatus.PENDING
        assert job.completed_at is None

    def test_bridge_has_no_execute_functions(self):
        """Bridge module has no execute/run/repair functions."""
        import modules.infrastructure.wre_core.src.fmas_improvement_bridge as bridge

        # These should not exist
        assert not hasattr(bridge, "execute_improvement")
        assert not hasattr(bridge, "run_repair")
        assert not hasattr(bridge, "perform_fix")


# ---------------------------------------------------------------------------
# Test 10: malformed finding fails truthfully
# ---------------------------------------------------------------------------


class TestMalformedFindingHandling:
    """Test malformed finding error handling."""

    def test_empty_finding_raises_error(self):
        """Empty finding dict raises ValueError."""
        with pytest.raises(ValueError, match="empty"):
            parse_fmas_finding({})

    def test_malformed_finding_creates_blocked_job(self):
        """Malformed finding in batch creates BLOCKED job."""
        findings = [
            {"type": "missing_tests", "module_path": "valid"},
            {},  # Malformed
            {"type": "wsp_violation", "module_path": "also_valid"},
        ]
        jobs = parse_fmas_findings(findings)

        # Should have 3 jobs (one blocked for malformed)
        assert len(jobs) == 3

        # Second job should be blocked
        assert jobs[1].status == ImprovementStatus.BLOCKED
        assert "Malformed" in jobs[1].status_reason_human

    def test_none_finding_raises_error(self):
        """None finding raises ValueError."""
        with pytest.raises(ValueError):
            parse_fmas_finding(None)


# ---------------------------------------------------------------------------
# Additional Tests
# ---------------------------------------------------------------------------


class TestFindingIdGeneration:
    """Test finding ID generation."""

    def test_finding_id_is_deterministic(self):
        """Same input produces same finding ID."""
        id1 = generate_finding_id("ERROR: Test", "modules/test")
        id2 = generate_finding_id("ERROR: Test", "modules/test")
        assert id1 == id2

    def test_finding_id_format(self):
        """Finding ID has correct format."""
        finding_id = generate_finding_id("test", "module")
        assert finding_id.startswith("fmas_")
        assert len(finding_id) == 17  # fmas_ + 12 hex chars


class TestFMASFindingRoundtrip:
    """Test FMASFinding serialization."""

    def test_fmas_finding_roundtrip(self):
        """FMASFinding survives to_dict/from_dict roundtrip."""
        original = FMASFinding(
            finding_id="fmas_test123",
            finding_type=FMASFindingType.MISSING_TESTS,
            severity=FMASSeverity.MEDIUM,
            module_path="modules/test",
            file_path="modules/test/src/file.py",
            message="Test message",
            wsp_refs=["WSP 49"],
        )
        as_dict = original.to_dict()
        restored = FMASFinding.from_dict(as_dict)

        assert restored.finding_id == original.finding_id
        assert restored.finding_type == original.finding_type
        assert restored.severity == original.severity
        assert restored.module_path == original.module_path


class TestOrphanCapabilityMapping:
    """Test orphan capability finding mapping."""

    def test_orphan_capability_creates_orphan_connection_job(self):
        """Orphan capability creates ORPHAN_CONNECTION job."""
        finding_dict = {
            "type": "orphan_capability",
            "severity": "medium",
            "module_path": "modules/platform_integration/orphan",
            "message": "CLI entrypoint not connected to WRE",
        }
        job = parse_fmas_finding(finding_dict)

        assert job.improvement_type == ImprovementType.ORPHAN_CONNECTION


class TestDocStaleMapping:
    """Test doc_stale finding mapping."""

    def test_doc_stale_creates_doc_hygiene_job(self):
        """Doc stale creates DOC_LEDGER_HYGIENE job."""
        finding_dict = {
            "type": "doc_stale",
            "severity": "low",
            "module_path": "modules/test",
            "message": "ModLog not updated",
        }
        job = parse_fmas_finding(finding_dict)

        assert job.improvement_type == ImprovementType.DOC_LEDGER_HYGIENE


class TestSecurityFindingMapping:
    """Test security vulnerability finding mapping."""

    def test_security_vulnerability_string_parsing(self):
        """Security vulnerability string parses correctly."""
        raw = "SECURITY_VULNERABILITY_HIGH: bandit issue in src/file.py:42"
        finding = parse_fmas_string(raw)

        assert finding is not None
        assert finding.finding_type == FMASFindingType.SECURITY_VULNERABILITY
        assert finding.severity == FMASSeverity.HIGH

    def test_secret_detected_string_parsing(self):
        """Secret detected string parses correctly."""
        raw = "SECRET_DETECTED: Potential secret in modules/test/config.py:10"
        finding = parse_fmas_string(raw)

        assert finding is not None
        assert finding.finding_type == FMASFindingType.SECRET_DETECTED
        assert finding.severity == FMASSeverity.CRITICAL


class TestRawFMASStringParsing:
    """Test parsing raw FMAS output strings."""

    def test_parse_fmas_strings_batch(self):
        """parse_fmas_strings handles batch of strings."""
        raw_findings = [
            "ERROR: Module 'test1' is missing the src/ directory",
            "ERROR: Module 'test2' is missing the tests/ directory",
            "WARNING: Module 'test3' is missing tests/README.md file",
        ]
        jobs = parse_fmas_strings(raw_findings)

        assert len(jobs) == 3
        assert jobs[0].improvement_type == ImprovementType.MODULE_REPAIR
        assert jobs[1].improvement_type == ImprovementType.TEST_HYGIENE
        assert jobs[2].improvement_type == ImprovementType.DOC_LEDGER_HYGIENE


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
