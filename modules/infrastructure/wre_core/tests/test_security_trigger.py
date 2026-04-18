#!/usr/bin/env python3
"""
Tests for SEC4 — Security Scan Trigger Detector

Verifies:
- Dependency file changes propose SCA scan
- Dockerfile/container changes propose Trivy scan
- Docs-only changes do not propose security scan
- Policy remains report-only by default

WSP Compliance: WSP 97 (Truthful testing)
"""

import pytest
from pathlib import Path

from modules.infrastructure.wre_core.src.security_trigger import (
    SecurityTriggerDetector,
    ScanProposal,
    TriggerReport,
    SECURITY_PATTERNS,
)


class TestSecurityTriggerDetector:
    """Test suite for SecurityTriggerDetector."""

    def setup_method(self):
        """Setup test fixtures."""
        self.detector = SecurityTriggerDetector()

    # --- Dependency file tests (SCA) ---

    def test_requirements_txt_proposes_sca(self):
        """Verify requirements.txt changes propose SCA scan."""
        changed = ["requirements.txt"]
        report = self.detector.detect(changed)

        assert len(report.proposals) == 1
        assert report.proposals[0].scan_type == "sca"
        assert report.proposals[0].tool == "snyk"
        assert "requirements.txt" in report.proposals[0].triggered_by
        assert report.mode == "report_only"

    def test_requirements_dev_txt_proposes_sca(self):
        """Verify requirements-dev.txt changes propose SCA scan."""
        changed = ["requirements-dev.txt"]
        report = self.detector.detect(changed)

        assert len(report.proposals) == 1
        assert report.proposals[0].scan_type == "sca"

    def test_pyproject_toml_proposes_sca(self):
        """Verify pyproject.toml changes propose SCA scan."""
        changed = ["pyproject.toml"]
        report = self.detector.detect(changed)

        assert len(report.proposals) == 1
        assert report.proposals[0].scan_type == "sca"

    def test_package_json_proposes_sca(self):
        """Verify package.json changes propose SCA scan."""
        changed = ["package.json"]
        report = self.detector.detect(changed)

        assert len(report.proposals) == 1
        assert report.proposals[0].scan_type == "sca"
        assert "Node.js dependencies" in report.proposals[0].reason

    def test_package_lock_json_proposes_sca(self):
        """Verify package-lock.json changes propose SCA scan."""
        changed = ["frontend/package-lock.json"]
        report = self.detector.detect(changed)

        assert len(report.proposals) == 1
        assert report.proposals[0].scan_type == "sca"

    def test_yarn_lock_proposes_sca(self):
        """Verify yarn.lock changes propose SCA scan."""
        changed = ["yarn.lock"]
        report = self.detector.detect(changed)

        assert len(report.proposals) == 1
        assert report.proposals[0].scan_type == "sca"

    # --- Container file tests (Trivy) ---

    def test_dockerfile_proposes_container_scan(self):
        """Verify Dockerfile changes propose container scan."""
        changed = ["Dockerfile"]
        report = self.detector.detect(changed)

        assert len(report.proposals) == 1
        assert report.proposals[0].scan_type == "container"
        assert report.proposals[0].tool == "trivy"

    def test_dockerfile_dev_proposes_container_scan(self):
        """Verify Dockerfile.dev changes propose container scan."""
        changed = ["Dockerfile.dev"]
        report = self.detector.detect(changed)

        assert len(report.proposals) == 1
        assert report.proposals[0].scan_type == "container"

    def test_docker_compose_proposes_container_scan(self):
        """Verify docker-compose.yml changes propose container scan."""
        changed = ["docker-compose.yml"]
        report = self.detector.detect(changed)

        assert len(report.proposals) == 1
        assert report.proposals[0].scan_type == "container"

    def test_docker_compose_yaml_proposes_container_scan(self):
        """Verify docker-compose.yaml changes propose container scan."""
        changed = ["docker-compose.yaml"]
        report = self.detector.detect(changed)

        assert len(report.proposals) == 1
        assert report.proposals[0].scan_type == "container"

    # --- CI/CD file tests (IaC) ---

    def test_github_workflow_proposes_iac_scan(self):
        """Verify GitHub workflow changes propose IaC scan."""
        changed = [".github/workflows/ci.yml"]
        report = self.detector.detect(changed)

        assert len(report.proposals) == 1
        assert report.proposals[0].scan_type == "iac"
        assert report.proposals[0].tool == "trivy"
        assert "GitHub Actions" in report.proposals[0].reason

    def test_cloudbuild_proposes_iac_scan(self):
        """Verify cloudbuild.yaml changes propose IaC scan."""
        changed = ["cloudbuild.yaml"]
        report = self.detector.detect(changed)

        assert len(report.proposals) == 1
        assert report.proposals[0].scan_type == "iac"

    # --- Skip tests (docs-only) ---

    def test_docs_only_no_proposals(self):
        """Verify docs-only changes do not propose security scan."""
        changed = [
            "README.md",
            "docs/architecture.md",
            "CHANGELOG.md",
        ]
        report = self.detector.detect(changed)

        assert len(report.proposals) == 0
        assert len(report.skipped_files) == 3

    def test_test_files_no_proposals(self):
        """Verify test file changes do not propose security scan."""
        changed = [
            "tests/test_security.py",
            "test_integration.py",
        ]
        report = self.detector.detect(changed)

        assert len(report.proposals) == 0
        assert len(report.skipped_files) == 2

    def test_generic_json_no_proposals(self):
        """Verify generic JSON (not package.json) does not propose scan."""
        changed = [
            "config.json",
            "data/settings.json",
        ]
        report = self.detector.detect(changed)

        assert len(report.proposals) == 0
        assert len(report.skipped_files) == 2

    # --- Mixed changes tests ---

    def test_mixed_changes_multiple_proposals(self):
        """Verify mixed changes generate appropriate proposals."""
        changed = [
            "requirements.txt",
            "Dockerfile",
            "README.md",
        ]
        report = self.detector.detect(changed)

        # Should have SCA and container proposals
        assert len(report.proposals) == 2
        scan_types = {p.scan_type for p in report.proposals}
        assert "sca" in scan_types
        assert "container" in scan_types

        # README should be skipped
        assert "README.md" in report.skipped_files

    def test_multiple_dependency_files_single_sca_proposal(self):
        """Verify multiple dependency files create single SCA proposal."""
        changed = [
            "requirements.txt",
            "requirements-dev.txt",
            "pyproject.toml",
        ]
        report = self.detector.detect(changed)

        # Should consolidate to single SCA proposal
        sca_proposals = [p for p in report.proposals if p.scan_type == "sca"]
        assert len(sca_proposals) == 1

        # All files should be in triggered_by
        triggered_by = sca_proposals[0].triggered_by
        assert len(triggered_by) == 3

    # --- Priority tests ---

    def test_dockerfile_higher_priority_than_dockerignore(self):
        """Verify Dockerfile has higher priority than .dockerignore."""
        changed = [
            ".dockerignore",
            "Dockerfile",
        ]
        report = self.detector.detect(changed)

        # Should be single container proposal with Dockerfile priority (3)
        assert len(report.proposals) == 1
        assert report.proposals[0].priority == 3  # Dockerfile priority

    def test_github_workflow_high_priority(self):
        """Verify GitHub workflow has high priority."""
        changed = [".github/workflows/deploy.yml"]
        report = self.detector.detect(changed)

        assert len(report.proposals) == 1
        assert report.proposals[0].priority == 3

    # --- Report structure tests ---

    def test_report_structure(self):
        """Verify TriggerReport structure."""
        changed = ["requirements.txt"]
        report = self.detector.detect(changed)

        assert hasattr(report, "generated_at")
        assert hasattr(report, "changed_files")
        assert hasattr(report, "security_relevant_files")
        assert hasattr(report, "proposals")
        assert hasattr(report, "skipped_files")
        assert hasattr(report, "mode")

    def test_report_to_dict(self):
        """Verify TriggerReport.to_dict() works."""
        changed = ["requirements.txt", "README.md"]
        report = self.detector.detect(changed)
        report_dict = report.to_dict()

        assert "generated_at" in report_dict
        assert "changed_files" in report_dict
        assert "proposals" in report_dict
        assert len(report_dict["proposals"]) == 1

    def test_proposal_status_defaults_proposed(self):
        """Verify ScanProposal status defaults to 'proposed'."""
        changed = ["requirements.txt"]
        report = self.detector.detect(changed)

        assert report.proposals[0].status == "proposed"

    # --- Mode tests ---

    def test_default_mode_report_only(self):
        """Verify default mode is report_only."""
        changed = ["requirements.txt"]
        report = self.detector.detect(changed)

        assert report.mode == "report_only"

    def test_empty_changes_no_proposals(self):
        """Verify empty changes list produces no proposals."""
        report = self.detector.detect([])

        assert len(report.proposals) == 0
        assert len(report.changed_files) == 0


class TestSecurityPatterns:
    """Test security pattern definitions."""

    def test_all_patterns_have_required_fields(self):
        """Verify all patterns have required fields."""
        for pattern in SECURITY_PATTERNS:
            assert pattern.pattern
            assert pattern.scan_type in ["sca", "container", "sast", "iac", "all"]
            assert pattern.description
            assert pattern.priority >= 1

    def test_pattern_coverage(self):
        """Verify key file types are covered."""
        patterns_str = " ".join(p.pattern for p in SECURITY_PATTERNS)

        # Dependency files
        assert "requirements" in patterns_str
        assert "pyproject" in patterns_str
        assert "package" in patterns_str

        # Container files
        assert "Dockerfile" in patterns_str or "docker" in patterns_str.lower()
        assert "docker-compose" in patterns_str

        # CI/CD files
        assert "github" in patterns_str.lower() or "workflows" in patterns_str
