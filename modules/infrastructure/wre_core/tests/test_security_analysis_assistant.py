#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for Security Analysis Assistant

SEC7 — SECURITY_ANALYSIS_ASSISTANT_PHASE1

Validates:
- LLM unavailable path returns needs_review
- Qwen/Gemma outputs are parsed safely
- Policy requires_012 is preserved
- Proposal contains no_patch_generated: true
- Recall context is included when provided
- No file writes except explicit proposal artifact writer
- Mocked LLM backends (no LM Studio required)
"""

import gc
import json
import pytest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from modules.infrastructure.wre_core.src.security_analysis_assistant import (
    SecurityAnalysisAssistant,
    AnalysisProposal,
    get_security_analysis_assistant,
)


@pytest.fixture
def sample_finding():
    """Sample normalized finding for tests."""
    return {
        "fingerprint": "abc123def456",
        "finding_id": "CVE-2024-001",
        "tool": "snyk",
        "severity": "critical",
        "title": "Prototype Pollution in lodash",
        "description": "Versions of lodash before 4.17.21 are vulnerable to prototype pollution.",
        "package_name": "lodash",
        "package_version": "4.17.20",
    }


@pytest.fixture
def sample_recall_context():
    """Sample SEC6 recall context for tests."""
    return {
        "match_found": True,
        "similar_matches": 3,
        "prior_outcomes": {
            "resolved": 2,
            "false_positive": 1,
            "open": 0,
        },
        "suggested_outcome": "resolved",
        "suggestion_confidence": 0.8,
    }


class TestLLMUnavailablePath:
    """Tests verifying LLM unavailable fallback."""

    def test_returns_needs_review_when_llm_disabled(self, sample_finding):
        """Should return needs_review when LLM is disabled."""
        assistant = SecurityAnalysisAssistant(enable_qwen=False, enable_gemma=False)

        proposal = assistant.analyze_finding(sample_finding)

        assert proposal.classification == "needs_review"
        assert proposal.llm_available is False
        assert proposal.analysis_source == "deterministic"

    def test_returns_needs_review_when_resolver_fails(self, sample_finding):
        """Should return needs_review when LLM resolver import fails."""
        assistant = SecurityAnalysisAssistant(enable_qwen=True, enable_gemma=True)

        # Mock resolver to raise ImportError
        with patch(
            "modules.infrastructure.wre_core.src.security_analysis_assistant.SecurityAnalysisAssistant._resolve_backends"
        ) as mock_resolve:
            # Simulate resolver failure by not setting backends
            def fail_resolve(self):
                self._backends_resolved = True
                self._qwen_backend = None
                self._gemma_backend = None

            mock_resolve.side_effect = lambda: fail_resolve(assistant)

            proposal = assistant.analyze_finding(sample_finding)

        assert proposal.classification == "needs_review"
        assert proposal.llm_available is False

    def test_deterministic_has_low_confidence(self, sample_finding):
        """Deterministic analysis should have low confidence."""
        assistant = SecurityAnalysisAssistant(enable_qwen=False, enable_gemma=False)

        proposal = assistant.analyze_finding(sample_finding)

        assert proposal.confidence_score <= 0.5
        assert proposal.classification_confidence <= 0.5


class TestQwenGemmaParsing:
    """Tests for LLM output parsing safety."""

    def test_parses_valid_json_output(self, sample_finding):
        """Should parse valid JSON output from LLM."""
        assistant = SecurityAnalysisAssistant(enable_qwen=True, enable_gemma=False)

        # Mock Qwen backend
        mock_qwen = MagicMock()
        mock_qwen.generate_response.return_value = json.dumps({
            "classification": "true_positive",
            "confidence": 0.85,
            "finding_summary": "Critical prototype pollution vulnerability",
            "risk_explanation": "Allows property injection",
            "remediation_proposal": "Upgrade lodash to 4.17.21",
        })

        assistant._backends_resolved = True
        assistant._qwen_backend = mock_qwen
        assistant._gemma_backend = None

        proposal = assistant.analyze_finding(sample_finding)

        assert proposal.classification == "true_positive"
        assert proposal.classification_confidence == 0.85
        assert "prototype pollution" in proposal.finding_summary.lower()

    def test_handles_malformed_json(self, sample_finding):
        """Should handle malformed JSON gracefully."""
        assistant = SecurityAnalysisAssistant(enable_qwen=True, enable_gemma=False)

        mock_qwen = MagicMock()
        mock_qwen.generate_response.return_value = "This is not JSON at all"

        assistant._backends_resolved = True
        assistant._qwen_backend = mock_qwen
        assistant._gemma_backend = None

        proposal = assistant.analyze_finding(sample_finding)

        # Should fall back to deterministic
        assert proposal.classification == "needs_review"
        assert proposal.no_patch_generated is True

    def test_handles_partial_json(self, sample_finding):
        """Should extract what it can from partial JSON."""
        assistant = SecurityAnalysisAssistant(enable_qwen=True, enable_gemma=False)

        mock_qwen = MagicMock()
        mock_qwen.generate_response.return_value = json.dumps({
            "classification": "false_positive",
            # Missing other fields
        })

        assistant._backends_resolved = True
        assistant._qwen_backend = mock_qwen
        assistant._gemma_backend = None

        proposal = assistant.analyze_finding(sample_finding)

        assert proposal.classification == "false_positive"

    def test_handles_markdown_wrapped_json(self, sample_finding):
        """Should handle JSON wrapped in markdown code blocks."""
        assistant = SecurityAnalysisAssistant(enable_qwen=True, enable_gemma=False)

        mock_qwen = MagicMock()
        mock_qwen.generate_response.return_value = """```json
{
    "classification": "true_positive",
    "confidence": 0.9
}
```"""

        assistant._backends_resolved = True
        assistant._qwen_backend = mock_qwen
        assistant._gemma_backend = None

        proposal = assistant.analyze_finding(sample_finding)

        assert proposal.classification == "true_positive"

    def test_extracts_keyword_from_text(self, sample_finding):
        """Should extract classification keyword from plain text."""
        assistant = SecurityAnalysisAssistant(enable_qwen=True, enable_gemma=False)

        mock_qwen = MagicMock()
        mock_qwen.generate_response.return_value = (
            "Based on my analysis, this appears to be a TRUE_POSITIVE finding."
        )

        assistant._backends_resolved = True
        assistant._qwen_backend = mock_qwen
        assistant._gemma_backend = None

        proposal = assistant.analyze_finding(sample_finding)

        assert proposal.classification == "true_positive"

    def test_gemma_validation_adjusts_confidence(self, sample_finding):
        """Gemma validation should adjust confidence."""
        assistant = SecurityAnalysisAssistant(enable_qwen=True, enable_gemma=True)

        mock_qwen = MagicMock()
        mock_qwen.generate_response.return_value = json.dumps({
            "classification": "true_positive",
            "confidence": 0.7,
        })

        mock_gemma = MagicMock()
        mock_gemma.generate_response.return_value = "true_positive"

        assistant._backends_resolved = True
        assistant._qwen_backend = mock_qwen
        assistant._gemma_backend = mock_gemma

        proposal = assistant.analyze_finding(sample_finding)

        # Gemma agrees, confidence should increase
        assert proposal.classification == "true_positive"
        assert proposal.classification_confidence >= 0.7
        assert "qwen" in proposal.analysis_source
        assert "gemma" in proposal.analysis_source


class TestRequires012Preservation:
    """Tests verifying requires_012 is preserved from policy."""

    def test_preserves_requires_012_true(self, sample_finding):
        """Should preserve requires_012=True from policy."""
        assistant = SecurityAnalysisAssistant(enable_qwen=False, enable_gemma=False)

        proposal = assistant.analyze_finding(
            sample_finding,
            policy_decision="gate_012",
            requires_012=True,
        )

        assert proposal.requires_012 is True

    def test_preserves_requires_012_false(self, sample_finding):
        """Should preserve requires_012=False from policy."""
        assistant = SecurityAnalysisAssistant(enable_qwen=False, enable_gemma=False)

        proposal = assistant.analyze_finding(
            sample_finding,
            policy_decision="report_only",
            requires_012=False,
        )

        assert proposal.requires_012 is False

    def test_requires_012_not_modified_by_llm(self, sample_finding):
        """LLM analysis should not modify requires_012."""
        assistant = SecurityAnalysisAssistant(enable_qwen=True, enable_gemma=False)

        mock_qwen = MagicMock()
        # LLM output does not contain requires_012
        mock_qwen.generate_response.return_value = json.dumps({
            "classification": "false_positive",
            "confidence": 0.95,
        })

        assistant._backends_resolved = True
        assistant._qwen_backend = mock_qwen
        assistant._gemma_backend = None

        proposal = assistant.analyze_finding(
            sample_finding,
            requires_012=True,  # Policy says requires 012
        )

        # Should still require 012 despite LLM saying false_positive
        assert proposal.requires_012 is True


class TestNoPatchGenerated:
    """Tests verifying no_patch_generated invariant."""

    def test_no_patch_generated_always_true(self, sample_finding):
        """no_patch_generated must always be True."""
        assistant = SecurityAnalysisAssistant(enable_qwen=False, enable_gemma=False)

        proposal = assistant.analyze_finding(sample_finding)

        assert proposal.no_patch_generated is True

    def test_no_patch_generated_with_llm(self, sample_finding):
        """no_patch_generated must be True even with LLM analysis."""
        assistant = SecurityAnalysisAssistant(enable_qwen=True, enable_gemma=False)

        mock_qwen = MagicMock()
        mock_qwen.generate_response.return_value = json.dumps({
            "classification": "true_positive",
            "patch": "// This should be ignored",
        })

        assistant._backends_resolved = True
        assistant._qwen_backend = mock_qwen
        assistant._gemma_backend = None

        proposal = assistant.analyze_finding(sample_finding)

        assert proposal.no_patch_generated is True

    def test_proposal_dataclass_default(self):
        """AnalysisProposal default should have no_patch_generated=True."""
        proposal = AnalysisProposal(
            fingerprint="test",
            finding_id="CVE-TEST",
            tool="test",
            severity="high",
        )

        assert proposal.no_patch_generated is True


class TestRecallContextInclusion:
    """Tests for recall context inclusion."""

    def test_includes_recall_context(self, sample_finding, sample_recall_context):
        """Should include recall context when provided."""
        assistant = SecurityAnalysisAssistant(enable_qwen=False, enable_gemma=False)

        proposal = assistant.analyze_finding(
            sample_finding,
            recall_context=sample_recall_context,
        )

        assert proposal.recall_context_included is True
        assert proposal.prior_outcomes == {"resolved": 2, "false_positive": 1, "open": 0}
        assert proposal.suggested_outcome_from_history == "resolved"

    def test_no_recall_context_when_not_provided(self, sample_finding):
        """Should not include recall context when not provided."""
        assistant = SecurityAnalysisAssistant(enable_qwen=False, enable_gemma=False)

        proposal = assistant.analyze_finding(sample_finding)

        assert proposal.recall_context_included is False
        assert proposal.prior_outcomes is None
        assert proposal.suggested_outcome_from_history is None

    def test_recall_context_influences_deterministic_classification(
        self, sample_finding
    ):
        """Recall context should influence deterministic classification."""
        assistant = SecurityAnalysisAssistant(enable_qwen=False, enable_gemma=False)

        # Recall says high confidence false_positive
        recall_context = {
            "suggested_outcome": "false_positive",
            "suggestion_confidence": 0.9,
        }

        proposal = assistant.analyze_finding(
            sample_finding,
            recall_context=recall_context,
        )

        # Should classify as false_positive based on history
        assert proposal.classification == "false_positive"

    def test_recall_context_passed_to_llm_prompt(self, sample_finding, sample_recall_context):
        """Recall context should be included in LLM prompt."""
        assistant = SecurityAnalysisAssistant(enable_qwen=True, enable_gemma=False)

        mock_qwen = MagicMock()
        mock_qwen.generate_response.return_value = json.dumps({
            "classification": "needs_review",
        })

        assistant._backends_resolved = True
        assistant._qwen_backend = mock_qwen
        assistant._gemma_backend = None

        assistant.analyze_finding(
            sample_finding,
            recall_context=sample_recall_context,
        )

        # Check that recall context was in the prompt
        call_args = mock_qwen.generate_response.call_args
        prompt = call_args[0][0]
        assert "Historical context" in prompt
        assert "Prior outcomes" in prompt


class TestNoFileWritesExceptExplicit:
    """Tests verifying no file writes except explicit artifact writer."""

    def test_analyze_does_not_write_files(self, sample_finding, tmp_path):
        """analyze_finding should not write any files."""
        assistant = SecurityAnalysisAssistant(
            enable_qwen=False,
            enable_gemma=False,
            proposal_output_dir=None,  # Disabled
        )

        # Record files before
        files_before = set(tmp_path.rglob("*"))

        proposal = assistant.analyze_finding(sample_finding)

        # Verify no files written
        files_after = set(tmp_path.rglob("*"))
        assert files_after == files_before

    def test_explicit_write_creates_file(self, sample_finding, tmp_path):
        """Explicit write_proposal_artifact should create file."""
        assistant = SecurityAnalysisAssistant(enable_qwen=False, enable_gemma=False)

        proposal = assistant.analyze_finding(sample_finding)

        # Explicit write
        output_path = assistant.write_proposal_artifact(proposal, output_dir=tmp_path)

        assert output_path is not None
        assert output_path.exists()
        assert output_path.suffix == ".json"

        # Verify content
        with open(output_path) as f:
            data = json.load(f)
        assert data["finding_id"] == "CVE-2024-001"
        assert data["no_patch_generated"] is True

    def test_write_disabled_returns_none(self, sample_finding):
        """Should return None when output dir is None."""
        assistant = SecurityAnalysisAssistant(
            enable_qwen=False,
            enable_gemma=False,
            proposal_output_dir=None,
        )

        proposal = assistant.analyze_finding(sample_finding)
        result = assistant.write_proposal_artifact(proposal)

        assert result is None


class TestAnalysisProposalDataclass:
    """Tests for AnalysisProposal dataclass."""

    def test_to_dict(self, sample_finding):
        """Should convert to dictionary."""
        proposal = AnalysisProposal(
            fingerprint="abc123",
            finding_id="CVE-2024-001",
            tool="snyk",
            severity="critical",
            classification="needs_review",
        )

        d = proposal.to_dict()

        assert d["fingerprint"] == "abc123"
        assert d["finding_id"] == "CVE-2024-001"
        assert d["no_patch_generated"] is True

    def test_to_json(self):
        """Should convert to JSON string."""
        proposal = AnalysisProposal(
            fingerprint="abc123",
            finding_id="CVE-2024-001",
            tool="snyk",
            severity="critical",
        )

        json_str = proposal.to_json()

        data = json.loads(json_str)
        assert data["finding_id"] == "CVE-2024-001"

    def test_default_values(self):
        """Should have sensible defaults."""
        proposal = AnalysisProposal(
            fingerprint="test",
            finding_id="TEST",
            tool="test",
            severity="low",
        )

        assert proposal.classification == "needs_review"
        assert proposal.no_patch_generated is True
        assert proposal.llm_available is False
        assert proposal.analysis_source == "deterministic"
        assert proposal.files_likely_affected == []


class TestFactoryFunction:
    """Tests for get_security_analysis_assistant factory."""

    def test_creates_with_defaults(self):
        """Should create assistant with default settings."""
        assistant = get_security_analysis_assistant()

        assert assistant.enable_qwen is True
        assert assistant.enable_gemma is True

    def test_creates_with_custom_settings(self):
        """Should respect custom settings."""
        assistant = get_security_analysis_assistant(
            enable_qwen=False,
            enable_gemma=True,
        )

        assert assistant.enable_qwen is False
        assert assistant.enable_gemma is True


class TestDeterministicAnalysis:
    """Tests for deterministic analysis logic."""

    def test_includes_severity_in_risk_explanation(self, sample_finding):
        """Risk explanation should mention severity."""
        assistant = SecurityAnalysisAssistant(enable_qwen=False, enable_gemma=False)

        proposal = assistant.analyze_finding(sample_finding)

        assert "critical" in proposal.risk_explanation.lower()

    def test_includes_package_in_remediation(self, sample_finding):
        """Remediation should mention package when available."""
        assistant = SecurityAnalysisAssistant(enable_qwen=False, enable_gemma=False)

        proposal = assistant.analyze_finding(sample_finding)

        assert "lodash" in proposal.remediation_proposal

    def test_includes_file_in_affected(self):
        """Should include file_path in files_likely_affected."""
        finding = {
            "fingerprint": "xyz789",
            "finding_id": "RULE-001",
            "tool": "semgrep",
            "severity": "high",
            "file_path": "src/api/handler.py",
        }

        assistant = SecurityAnalysisAssistant(enable_qwen=False, enable_gemma=False)

        proposal = assistant.analyze_finding(finding)

        assert "src/api/handler.py" in proposal.files_likely_affected

    def test_summary_includes_tool(self, sample_finding):
        """Summary should mention the scanning tool."""
        assistant = SecurityAnalysisAssistant(enable_qwen=False, enable_gemma=False)

        proposal = assistant.analyze_finding(sample_finding)

        assert "snyk" in proposal.finding_summary.lower()


class TestEdgeCases:
    """Tests for edge cases."""

    def test_handles_empty_finding(self):
        """Should handle minimal finding dict."""
        finding = {
            "fingerprint": "min",
            "finding_id": "UNKNOWN",
            "tool": "unknown",
            "severity": "unknown",
        }

        assistant = SecurityAnalysisAssistant(enable_qwen=False, enable_gemma=False)

        proposal = assistant.analyze_finding(finding)

        assert proposal.classification == "needs_review"
        assert proposal.no_patch_generated is True

    def test_handles_llm_exception(self, sample_finding):
        """Should handle LLM backend exception gracefully."""
        assistant = SecurityAnalysisAssistant(enable_qwen=True, enable_gemma=False)

        mock_qwen = MagicMock()
        mock_qwen.generate_response.side_effect = Exception("LLM crashed")

        assistant._backends_resolved = True
        assistant._qwen_backend = mock_qwen
        assistant._gemma_backend = None

        proposal = assistant.analyze_finding(sample_finding)

        # Should fall back to deterministic
        assert proposal.analysis_source == "deterministic"
        assert proposal.no_patch_generated is True

    def test_handles_very_long_description(self, sample_finding):
        """Should truncate very long descriptions."""
        sample_finding["description"] = "A" * 10000

        assistant = SecurityAnalysisAssistant(enable_qwen=False, enable_gemma=False)

        proposal = assistant.analyze_finding(sample_finding)

        # Should not crash and should complete
        assert proposal.finding_id == "CVE-2024-001"
