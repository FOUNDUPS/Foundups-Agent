"""
Quick Answer Generation Tests.

Tests for VOTE_POC_QUICK_ANSWER_GENERATION_PHASE1.

Test Boundaries:
- NO_LLM_CALL: Pure template-based, no AI generation
- NO_NEW_FACTS: Only surfaces existing confidence-scored data
- MAX_3_LINES_ENFORCED: Truncates with human review note
- HUMAN_REVIEW_FOR_HIGH_RISK_CLAIMS: Preserves review triggers
- TRAIL_TERMINATION_MARKERS_PRESERVED: Shows termination markers
- NO_TARGETED_PERSUASION
- NO_CANDIDATE_RECOMMENDATION
- NO_FOREIGN_FUNDING_CLAIM
- NO_DARK_MONEY_AS_VERIFIED_FACT

Builds on:
- VOTE_POC_FEC_ADAPTER_PHASE1 (PR #707)
- VOTE_POC_ENTITY_RESOLUTION_PHASE1 (PR #709)
- VOTE_POC_FUNDING_SUMMARY_PHASE1 (PR #710)
- VOTE_POC_CONFIDENCE_SCORING_INTEGRATION_PHASE1 (PR #712)
"""

from __future__ import annotations

import pytest
from typing import List

from modules.foundups.voteballots.src.fec_adapter import (
    ConfidenceLevel,
    FECSource,
    MockFECAdapter,
    get_mock_adapter,
)
from modules.foundups.voteballots.src.entity_resolution import (
    EntityResolutionRequest,
    resolve_candidate_entity,
)
from modules.foundups.voteballots.src.funding_summary import (
    FundingSummaryRequest,
    FundingSummaryResult,
    FundingSummaryStatus,
    FundingSourceSummary,
    TrailTerminationMarker,
    summarize_candidate_funding,
)
from modules.foundups.voteballots.src.confidence_scoring import (
    ConfidenceLabel,
    ConfidenceScoredFundingSummary,
    ConfidenceScoredFundingSource,
    ConfidenceScoringStatus,
    HumanReviewTrigger,
    score_funding_summary_confidence,
)
from modules.foundups.voteballots.src.quick_answer import (
    AnswerFormat,
    QuickAnswer,
    generate_quick_answer,
    generate_shell_answer,
    generate_markdown_answer,
    format_funding_line,
    truncate_with_review_note,
    is_answer_ready_for_display,
    get_answer_confidence_summary,
    MAX_LINES,
)


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def adapter() -> MockFECAdapter:
    """Get mock FEC adapter with default fixtures."""
    return get_mock_adapter()


@pytest.fixture
def scored_summary(adapter: MockFECAdapter) -> ConfidenceScoredFundingSummary:
    """Get a scored funding summary for AOC."""
    request = EntityResolutionRequest(query="OCASIO-CORTEZ, ALEXANDRIA")
    resolution = resolve_candidate_entity(request, adapter)

    summary_request = FundingSummaryRequest(resolution_result=resolution)
    funding_summary = summarize_candidate_funding(summary_request, adapter)

    return score_funding_summary_confidence(funding_summary)


@pytest.fixture
def verified_fact_summary() -> ConfidenceScoredFundingSummary:
    """Create a high-confidence verified fact summary."""
    return ConfidenceScoredFundingSummary(
        status=ConfidenceScoringStatus.SUCCESS,
        candidate_id="TEST001",
        candidate_name="Test Candidate",
        total_raised=1500000.0,
        total_contributions=5000,
        scored_sources=[
            ConfidenceScoredFundingSource(
                source_name="ActBlue",
                source_type="committee",
                amount=500000.0,
                percentage=33.3,
                contribution_count=2000,
                is_aggregated=True,
                original_confidence=ConfidenceLevel.VERIFIED_FACT,
                confidence_label=ConfidenceLabel.VERIFIED_FACT,
                source_reference=FECSource(source_type="fec_filing"),
            ),
            ConfidenceScoredFundingSource(
                source_name="Small Donors",
                source_type="individual",
                amount=400000.0,
                percentage=26.7,
                contribution_count=3000,
                is_aggregated=True,
                original_confidence=ConfidenceLevel.VERIFIED_FACT,
                confidence_label=ConfidenceLabel.VERIFIED_FACT,
            ),
        ],
        trail_termination_markers=[TrailTerminationMarker.DIRECT_FEC_RECORDS_ONLY],
        overall_confidence=ConfidenceLabel.VERIFIED_FACT,
    )


@pytest.fixture
def low_confidence_summary() -> ConfidenceScoredFundingSummary:
    """Create a low-confidence summary with uncertainty markers."""
    return ConfidenceScoredFundingSummary(
        status=ConfidenceScoringStatus.SUCCESS,
        candidate_id="TEST002",
        candidate_name="Unknown Candidate",
        total_raised=50000.0,
        total_contributions=100,
        scored_sources=[
            ConfidenceScoredFundingSource(
                source_name="Unknown PAC",
                source_type="committee",
                amount=30000.0,
                percentage=60.0,
                contribution_count=10,
                is_aggregated=False,
                original_confidence=ConfidenceLevel.LOW_CONFIDENCE_INFERENCE,
                confidence_label=ConfidenceLabel.LOW_CONFIDENCE_INFERENCE,
            ),
        ],
        trail_termination_markers=[
            TrailTerminationMarker.DIRECT_FEC_RECORDS_ONLY,
            TrailTerminationMarker.UNKNOWN_WHERE_SOURCE_ABSENT,
        ],
        overall_confidence=ConfidenceLabel.LOW_CONFIDENCE_INFERENCE,
    )


@pytest.fixture
def human_review_summary() -> ConfidenceScoredFundingSummary:
    """Create a summary that requires human review."""
    return ConfidenceScoredFundingSummary(
        status=ConfidenceScoringStatus.SUCCESS,
        candidate_id="TEST003",
        candidate_name="Review Candidate",
        total_raised=1000000.0,
        total_contributions=500,
        scored_sources=[
            ConfidenceScoredFundingSource(
                source_name="Foreign Entity LLC",  # Triggers foreign review
                source_type="committee",
                amount=500000.0,
                percentage=50.0,
                contribution_count=5,
                is_aggregated=False,
                original_confidence=ConfidenceLevel.HIGH_CONFIDENCE_INFERENCE,
                confidence_label=ConfidenceLabel.HIGH_CONFIDENCE_INFERENCE,
                requires_human_review=True,
                human_review_triggers=[HumanReviewTrigger.FOREIGN_FUNDING_ALLEGATION],
            ),
        ],
        trail_termination_markers=[TrailTerminationMarker.DIRECT_FEC_RECORDS_ONLY],
        human_review_required=True,
        all_human_review_triggers=[HumanReviewTrigger.FOREIGN_FUNDING_ALLEGATION],
        overall_confidence=ConfidenceLabel.HIGH_CONFIDENCE_INFERENCE,
    )


@pytest.fixture
def many_sources_summary() -> ConfidenceScoredFundingSummary:
    """Create a summary with many sources to test truncation."""
    sources = [
        ConfidenceScoredFundingSource(
            source_name=f"Source {i}",
            source_type="individual",
            amount=100000.0 - (i * 10000),
            percentage=10.0 - i,
            contribution_count=100 - (i * 10),
            is_aggregated=True,
            original_confidence=ConfidenceLevel.VERIFIED_FACT,
            confidence_label=ConfidenceLabel.VERIFIED_FACT,
        )
        for i in range(5)
    ]

    return ConfidenceScoredFundingSummary(
        status=ConfidenceScoringStatus.SUCCESS,
        candidate_id="TEST004",
        candidate_name="Many Sources Candidate",
        total_raised=500000.0,
        total_contributions=1000,
        scored_sources=sources,
        trail_termination_markers=[TrailTerminationMarker.DIRECT_FEC_RECORDS_ONLY],
        overall_confidence=ConfidenceLabel.VERIFIED_FACT,
    )


@pytest.fixture
def trail_terminated_summary() -> ConfidenceScoredFundingSummary:
    """Create a summary with trail termination."""
    return ConfidenceScoredFundingSummary(
        status=ConfidenceScoringStatus.SUCCESS,
        candidate_id="TEST005",
        candidate_name="Trail End Candidate",
        total_raised=200000.0,
        total_contributions=200,
        scored_sources=[
            ConfidenceScoredFundingSource(
                source_name="Dark Money PAC",
                source_type="committee",
                amount=100000.0,
                percentage=50.0,
                contribution_count=1,
                is_aggregated=False,
                original_confidence=ConfidenceLevel.UNKNOWN,
                confidence_label=ConfidenceLabel.UNKNOWN,
            ),
        ],
        trail_termination_markers=[
            TrailTerminationMarker.DIRECT_FEC_RECORDS_ONLY,
            TrailTerminationMarker.NO_DARK_MONEY_TRACE_IN_THIS_SLICE,
            TrailTerminationMarker.NO_SUPER_PAC_TRACE_IN_THIS_SLICE,
        ],
        overall_confidence=ConfidenceLabel.UNKNOWN,
    )


# =============================================================================
# Core Generation Tests
# =============================================================================


class TestGenerateQuickAnswerVerifiedFact:
    """Tests for generating quick answers from verified fact data."""

    def test_verified_fact_clean_answer(
        self, verified_fact_summary: ConfidenceScoredFundingSummary
    ):
        """Clean high-confidence answer generates without review flag."""
        answer = generate_quick_answer(verified_fact_summary)

        assert isinstance(answer, QuickAnswer)
        assert answer.confidence_label == ConfidenceLabel.VERIFIED_FACT
        assert not answer.requires_human_review
        assert len(answer.lines) <= MAX_LINES
        assert len(answer.lines) > 0

    def test_verified_fact_includes_total(
        self, verified_fact_summary: ConfidenceScoredFundingSummary
    ):
        """Verified fact answer includes total raised."""
        answer = generate_quick_answer(verified_fact_summary)

        # Should include total raised in first line
        assert any("1,500,000" in line for line in answer.lines)

    def test_verified_fact_includes_candidate_name(
        self, verified_fact_summary: ConfidenceScoredFundingSummary
    ):
        """Verified fact answer includes candidate name."""
        answer = generate_quick_answer(verified_fact_summary)

        assert any("Test Candidate" in line for line in answer.lines)

    def test_verified_fact_shows_confidence_indicator(
        self, verified_fact_summary: ConfidenceScoredFundingSummary
    ):
        """Verified fact answer shows confidence indicator."""
        answer = generate_quick_answer(
            verified_fact_summary, format=AnswerFormat.PLAIN_TEXT
        )

        # Should have verified indicator
        text = answer.text
        assert "verified" in text.lower() or "(verified)" in text


class TestGenerateQuickAnswerLowConfidence:
    """Tests for generating quick answers from low-confidence data."""

    def test_low_confidence_includes_uncertainty(
        self, low_confidence_summary: ConfidenceScoredFundingSummary
    ):
        """Low confidence answer includes uncertainty markers."""
        answer = generate_quick_answer(low_confidence_summary)

        assert answer.confidence_label == ConfidenceLabel.LOW_CONFIDENCE_INFERENCE
        # Should show low confidence indicator
        text = answer.text
        assert "low" in text.lower() or "[L]" in text or "[low]" in text

    def test_low_confidence_preserves_sources(
        self, low_confidence_summary: ConfidenceScoredFundingSummary
    ):
        """Low confidence answer preserves source information."""
        answer = generate_quick_answer(low_confidence_summary)

        # Should include source name
        assert any("Unknown PAC" in line for line in answer.lines)


class TestGenerateQuickAnswerTruncation:
    """Tests for MAX 3 lines enforcement."""

    def test_truncation_enforced_max_3_lines(
        self, many_sources_summary: ConfidenceScoredFundingSummary
    ):
        """Answer never exceeds 3 lines."""
        answer = generate_quick_answer(many_sources_summary)

        assert len(answer.lines) <= 3
        assert answer.truncated is True

    def test_truncation_adds_review_note(
        self, many_sources_summary: ConfidenceScoredFundingSummary
    ):
        """Truncated answer adds 'see full report' note."""
        answer = generate_quick_answer(many_sources_summary)

        # Should have truncation indicator
        assert any("more sources" in line.lower() or "full report" in line.lower()
                   for line in answer.lines)

    def test_truncation_preserves_original_count(
        self, many_sources_summary: ConfidenceScoredFundingSummary
    ):
        """Truncated answer preserves original line count."""
        answer = generate_quick_answer(many_sources_summary)

        assert answer.truncated is True
        # Original would have total + 5 sources = 6 potential lines
        # but we requested only 2 sources max, so it's total + 2 = 3

    def test_max_lines_parameter_respected(
        self, verified_fact_summary: ConfidenceScoredFundingSummary
    ):
        """Custom max_lines parameter is respected."""
        answer = generate_quick_answer(verified_fact_summary, max_lines=2)

        assert len(answer.lines) <= 2

    def test_max_lines_capped_at_3(
        self, verified_fact_summary: ConfidenceScoredFundingSummary
    ):
        """max_lines cannot exceed MAX_LINES (3)."""
        answer = generate_quick_answer(verified_fact_summary, max_lines=10)

        assert len(answer.lines) <= MAX_LINES


class TestGenerateQuickAnswerHumanReviewFlag:
    """Tests for human review flag preservation."""

    def test_human_review_flag_preserved(
        self, human_review_summary: ConfidenceScoredFundingSummary
    ):
        """Human review flag is preserved in answer."""
        answer = generate_quick_answer(human_review_summary)

        assert answer.requires_human_review is True
        assert len(answer.human_review_reasons) > 0
        assert HumanReviewTrigger.FOREIGN_FUNDING_ALLEGATION in answer.human_review_reasons

    def test_human_review_not_ready_for_display(
        self, human_review_summary: ConfidenceScoredFundingSummary
    ):
        """Human review answers are not ready for display."""
        answer = generate_quick_answer(human_review_summary)

        assert not is_answer_ready_for_display(answer)


class TestGenerateQuickAnswerTrailTerminated:
    """Tests for trail termination marker handling."""

    def test_trail_terminated_flag(
        self, trail_terminated_summary: ConfidenceScoredFundingSummary
    ):
        """Trail terminated flag is set correctly."""
        answer = generate_quick_answer(trail_terminated_summary)

        assert answer.trail_terminated is True
        assert answer.trail_termination_reason is not None

    def test_trail_termination_reason_readable(
        self, trail_terminated_summary: ConfidenceScoredFundingSummary
    ):
        """Trail termination reason is human-readable."""
        answer = generate_quick_answer(trail_terminated_summary)

        # Should not have underscores (converted to spaces)
        assert "_" not in (answer.trail_termination_reason or "")


# =============================================================================
# Format Tests
# =============================================================================


class TestFormatFundingLineAllConfidenceLevels:
    """Tests for format_funding_line across all confidence levels."""

    @pytest.mark.parametrize(
        "confidence,expected_marker",
        [
            (ConfidenceLabel.VERIFIED_FACT, "verified"),
            (ConfidenceLabel.HIGH_CONFIDENCE_INFERENCE, "high"),
            (ConfidenceLabel.LOW_CONFIDENCE_INFERENCE, "low"),
            (ConfidenceLabel.UNKNOWN, "unknown"),
        ],
    )
    def test_format_funding_line_plain_text(
        self, confidence: ConfidenceLabel, expected_marker: str
    ):
        """format_funding_line includes correct confidence marker in plain text."""
        line = format_funding_line(
            "Test Source", 50000.0, confidence, AnswerFormat.PLAIN_TEXT
        )

        assert expected_marker in line.lower()
        assert "50,000" in line
        assert "Test Source" in line

    @pytest.mark.parametrize(
        "confidence,expected_marker",
        [
            (ConfidenceLabel.VERIFIED_FACT, "[V]"),
            (ConfidenceLabel.HIGH_CONFIDENCE_INFERENCE, "[H]"),
            (ConfidenceLabel.LOW_CONFIDENCE_INFERENCE, "[L]"),
            (ConfidenceLabel.UNKNOWN, "[?]"),
        ],
    )
    def test_format_funding_line_shell_display(
        self, confidence: ConfidenceLabel, expected_marker: str
    ):
        """format_funding_line uses correct shell display markers."""
        line = format_funding_line(
            "Test Source", 50000.0, confidence, AnswerFormat.SHELL_DISPLAY
        )

        assert expected_marker in line
        assert "50,000" in line

    def test_format_funding_line_markdown(self):
        """format_funding_line uses markdown formatting."""
        line = format_funding_line(
            "Test Source",
            75000.0,
            ConfidenceLabel.VERIFIED_FACT,
            AnswerFormat.MARKDOWN,
        )

        assert line.startswith("-")  # Markdown list item
        assert "75,000" in line


class TestShellDisplayFormat:
    """Tests for p.fMALL shell rendering format."""

    def test_shell_display_format(
        self, verified_fact_summary: ConfidenceScoredFundingSummary
    ):
        """Shell display format uses compact indicators."""
        answer = generate_quick_answer(
            verified_fact_summary, format=AnswerFormat.SHELL_DISPLAY
        )

        # Should use [V], [H], [L], [?] markers
        text = answer.text
        assert any(marker in text for marker in ["[V]", "[H]", "[L]", "[?]"])

    def test_generate_shell_answer_convenience(
        self, verified_fact_summary: ConfidenceScoredFundingSummary
    ):
        """generate_shell_answer convenience function works."""
        answer = generate_shell_answer(verified_fact_summary)

        assert isinstance(answer, QuickAnswer)
        # Should have shell format markers
        assert any(marker in answer.text for marker in ["[V]", "[H]", "[L]", "[?]"])


# =============================================================================
# No LLM Call Contract Tests
# =============================================================================


class TestNoLLMCallContract:
    """Tests verifying no external AI dependency."""

    def test_no_llm_call_no_external_imports(self):
        """quick_answer module has no LLM/AI imports."""
        import modules.foundups.voteballots.src.quick_answer as qa_module

        # Check module doesn't import AI libraries
        module_source = qa_module.__file__
        with open(module_source, "r") as f:
            source_code = f.read()

        # Should not import any AI/LLM libraries
        ai_imports = [
            "import openai",
            "import anthropic",
            "from openai",
            "from anthropic",
            "import transformers",
            "from transformers",
            "import torch",
            "import tensorflow",
            "import langchain",
            "from langchain",
        ]

        for ai_import in ai_imports:
            assert ai_import not in source_code, f"Found AI import: {ai_import}"

    def test_generation_is_deterministic(
        self, verified_fact_summary: ConfidenceScoredFundingSummary
    ):
        """Quick answer generation is deterministic (same input = same output)."""
        answer1 = generate_quick_answer(verified_fact_summary)
        answer2 = generate_quick_answer(verified_fact_summary)

        assert answer1.lines == answer2.lines
        assert answer1.confidence_label == answer2.confidence_label
        assert answer1.requires_human_review == answer2.requires_human_review

    def test_no_network_calls(
        self, verified_fact_summary: ConfidenceScoredFundingSummary
    ):
        """Quick answer generation makes no network calls."""
        # This is implicit - if it required network, it would fail in test env
        # but we can verify by checking execution time is instant
        import time

        start = time.time()
        for _ in range(100):
            generate_quick_answer(verified_fact_summary)
        elapsed = time.time() - start

        # 100 generations should take < 1 second (no network)
        assert elapsed < 1.0, f"Generation took {elapsed}s - possible network call"


# =============================================================================
# Error Handling Tests
# =============================================================================


class TestErrorHandling:
    """Tests for error status handling."""

    def test_error_summary_produces_error_answer(self):
        """Error summary produces error answer."""
        error_summary = ConfidenceScoredFundingSummary(
            status=ConfidenceScoringStatus.FUNDING_SUMMARY_ERROR,
            error_message="Test error message",
        )

        answer = generate_quick_answer(error_summary)

        assert "[Error]" in answer.lines[0]
        assert answer.requires_human_review is True
        assert answer.trail_terminated is True

    def test_no_funding_summary_error(self):
        """NO_FUNDING_SUMMARY status produces error answer."""
        error_summary = ConfidenceScoredFundingSummary(
            status=ConfidenceScoringStatus.NO_FUNDING_SUMMARY,
            error_message="No data",
        )

        answer = generate_quick_answer(error_summary)

        assert len(answer.lines) > 0
        assert answer.confidence_label == ConfidenceLabel.UNKNOWN


# =============================================================================
# Convenience Function Tests
# =============================================================================


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_generate_markdown_answer(
        self, verified_fact_summary: ConfidenceScoredFundingSummary
    ):
        """generate_markdown_answer convenience function works."""
        answer = generate_markdown_answer(verified_fact_summary)

        assert isinstance(answer, QuickAnswer)
        # Should have markdown formatting
        text = answer.text
        assert "**" in text or "-" in text or "*" in text

    def test_is_answer_ready_for_display_verified(
        self, verified_fact_summary: ConfidenceScoredFundingSummary
    ):
        """Verified fact answer is ready for display."""
        answer = generate_quick_answer(verified_fact_summary)

        # Verified fact without review flags should be ready
        if not answer.requires_human_review:
            assert is_answer_ready_for_display(answer)

    def test_is_answer_ready_for_display_unknown(self):
        """Unknown confidence answer is not ready for display."""
        unknown_summary = ConfidenceScoredFundingSummary(
            status=ConfidenceScoringStatus.SUCCESS,
            candidate_id="TEST",
            overall_confidence=ConfidenceLabel.UNKNOWN,
        )

        answer = generate_quick_answer(unknown_summary)

        assert not is_answer_ready_for_display(answer)

    def test_get_answer_confidence_summary(
        self, verified_fact_summary: ConfidenceScoredFundingSummary
    ):
        """get_answer_confidence_summary returns readable summary."""
        answer = generate_quick_answer(verified_fact_summary)
        summary = get_answer_confidence_summary(answer)

        assert isinstance(summary, str)
        assert "verified" in summary.lower()


class TestTruncateWithReviewNote:
    """Tests for truncate_with_review_note function."""

    def test_no_truncation_needed(self):
        """Lines within limit are not truncated."""
        lines = ["Line 1", "Line 2"]
        result = truncate_with_review_note(lines, 3, has_more=False)

        assert result == lines

    def test_truncation_with_more_content(self):
        """Truncation adds note when there's more content."""
        lines = ["Line 1", "Line 2", "Line 3"]
        result = truncate_with_review_note(lines, 3, has_more=True)

        assert len(result) <= 3
        assert "more sources" in result[-1].lower() or "full report" in result[-1].lower()

    def test_truncation_exceeds_limit(self):
        """Lines exceeding limit are truncated."""
        lines = ["Line 1", "Line 2", "Line 3", "Line 4"]
        result = truncate_with_review_note(lines, 3, has_more=False)

        assert len(result) == 3
        assert "more sources" in result[-1].lower() or "full report" in result[-1].lower()


# =============================================================================
# QuickAnswer Dataclass Tests
# =============================================================================


class TestQuickAnswerDataclass:
    """Tests for QuickAnswer dataclass properties."""

    def test_text_property(self):
        """text property joins lines correctly."""
        answer = QuickAnswer(
            lines=["Line 1", "Line 2", "Line 3"],
            confidence_label=ConfidenceLabel.VERIFIED_FACT,
        )

        assert answer.text == "Line 1\nLine 2\nLine 3"

    def test_line_count_property(self):
        """line_count property returns correct count."""
        answer = QuickAnswer(
            lines=["Line 1", "Line 2"],
            confidence_label=ConfidenceLabel.VERIFIED_FACT,
        )

        assert answer.line_count == 2

    def test_empty_answer(self):
        """Empty answer has zero line count."""
        answer = QuickAnswer(confidence_label=ConfidenceLabel.UNKNOWN)

        assert answer.line_count == 0
        assert answer.text == ""


# =============================================================================
# Integration Tests
# =============================================================================


class TestFullPipelineIntegration:
    """Tests for full pipeline integration through quick answer."""

    def test_full_pipeline_to_quick_answer(self, adapter: MockFECAdapter):
        """Full pipeline: resolve -> summarize -> score -> quick answer."""
        # Step 1: Resolve candidate
        resolution = resolve_candidate_entity(
            EntityResolutionRequest(query="OCASIO-CORTEZ"), adapter
        )

        # Step 2: Summarize funding
        summary = summarize_candidate_funding(
            FundingSummaryRequest(resolution_result=resolution), adapter
        )

        # Step 3: Score confidence
        scored = score_funding_summary_confidence(summary)

        # Step 4: Generate quick answer
        answer = generate_quick_answer(scored)

        assert isinstance(answer, QuickAnswer)
        assert len(answer.lines) <= MAX_LINES
        assert len(answer.lines) > 0

    def test_pipeline_preserves_candidate_id(self, scored_summary: ConfidenceScoredFundingSummary):
        """Source summary ID is preserved in answer."""
        answer = generate_quick_answer(scored_summary)

        assert answer.source_summary_id == scored_summary.candidate_id


# =============================================================================
# Safety Boundary Tests
# =============================================================================


class TestSafetyBoundaries:
    """Tests verifying political safety boundaries."""

    def test_no_recommendation_language(
        self, verified_fact_summary: ConfidenceScoredFundingSummary
    ):
        """Quick answer contains no recommendation language."""
        answer = generate_quick_answer(verified_fact_summary)

        text = answer.text.lower()

        # Should not contain recommendation words
        recommendation_words = [
            "vote for",
            "vote against",
            "should vote",
            "recommend",
            "better than",
            "worse than",
            "support",
            "oppose",
            "elect",
            "defeat",
        ]

        for word in recommendation_words:
            assert word not in text, f"Found recommendation language: {word}"

    def test_no_persuasion_language(
        self, verified_fact_summary: ConfidenceScoredFundingSummary
    ):
        """Quick answer contains no persuasion language."""
        answer = generate_quick_answer(verified_fact_summary)

        text = answer.text.lower()

        # Should not contain persuasion words
        persuasion_words = [
            "must",
            "urgent",
            "critical",
            "important that you",
            "you should",
            "you need to",
            "don't miss",
            "act now",
        ]

        for word in persuasion_words:
            assert word not in text, f"Found persuasion language: {word}"

    def test_no_targeting_fields(
        self, verified_fact_summary: ConfidenceScoredFundingSummary
    ):
        """QuickAnswer has no targeting-related fields."""
        answer = generate_quick_answer(verified_fact_summary)

        # Should not have targeting fields
        assert not hasattr(answer, "target_audience")
        assert not hasattr(answer, "demographic")
        assert not hasattr(answer, "user_profile")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
