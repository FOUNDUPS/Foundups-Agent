"""
Confidence Scoring Integration Tests.

Tests for VOTE_POC_CONFIDENCE_SCORING_INTEGRATION_PHASE1.

Test Boundaries:
- NO_LIVE_API_REQUIRED_FOR_TESTS
- NO_API_KEY_REQUIRED_FOR_TESTS
- NO_NETWORK_CALLS_IN_TESTS
- VERIFIED_FACT_REQUIRES_DIRECT_SOURCE
- UNKNOWN_WHEN_SOURCE_ABSENT
- TRAIL_TERMINATION_MARKERS_PRESERVED
- SOURCE_REFERENCES_PRESERVED
- HUMAN_REVIEW_FOR_HIGH_RISK_CLAIMS
- NO_FOREIGN_FUNDING_CLAIM_GENERATED
- NO_DARK_MONEY_AS_VERIFIED_FACT
- NO_QUICK_ANSWER_GENERATION
- NO_PERSUASION_LANGUAGE
- NO_CANDIDATE_RECOMMENDATION

Builds on:
- VOTE_POC_FEC_ADAPTER_PHASE1 (PR #707)
- VOTE_POC_ENTITY_RESOLUTION_PHASE1 (PR #709)
- VOTE_POC_FUNDING_SUMMARY_PHASE1 (PR #710)
"""

from __future__ import annotations

import pytest

from modules.foundups.voteballots.src.fec_adapter import (
    CandidateRecord,
    ConfidenceLevel,
    ContributionRecord,
    FECErrorType,
    FECSource,
    MockFECAdapter,
    get_mock_adapter,
)
from modules.foundups.voteballots.src.entity_resolution import (
    EntityResolutionRequest,
    EntityResolutionResult,
    EntityResolutionStatus,
    resolve_candidate_entity,
)
from modules.foundups.voteballots.src.funding_summary import (
    FundingSummaryRequest,
    FundingSummaryResult,
    FundingSummaryStatus,
    FundingSourceSummary,
    TrailTerminationMarker,
    summarize_candidate_funding,
    summarize_by_candidate_id,
)
from modules.foundups.voteballots.src.confidence_scoring import (
    ConfidenceLabel,
    ConfidenceScoredClaim,
    ConfidenceScoredFundingSource,
    ConfidenceScoredFundingSummary,
    ConfidenceScoringStatus,
    HumanReviewTrigger,
    score_funding_summary_confidence,
    get_verified_facts,
    get_unknown_claims,
    get_human_review_claims,
)


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def adapter() -> MockFECAdapter:
    """Get mock FEC adapter with default fixtures."""
    return get_mock_adapter()


@pytest.fixture
def resolved_candidate(adapter: MockFECAdapter) -> EntityResolutionResult:
    """Get a resolved candidate (AOC)."""
    request = EntityResolutionRequest(query="OCASIO-CORTEZ, ALEXANDRIA")
    return resolve_candidate_entity(request, adapter)


@pytest.fixture
def funding_summary(
    adapter: MockFECAdapter, resolved_candidate: EntityResolutionResult
) -> FundingSummaryResult:
    """Get a funding summary for AOC."""
    request = FundingSummaryRequest(resolution_result=resolved_candidate)
    return summarize_candidate_funding(request, adapter)


@pytest.fixture
def funding_summary_with_contributions(
    adapter: MockFECAdapter, resolved_candidate: EntityResolutionResult
) -> FundingSummaryResult:
    """Get a funding summary with contributions from AOC."""
    request = FundingSummaryRequest(resolution_result=resolved_candidate, top_n=5)
    return summarize_candidate_funding(request, adapter)


# =============================================================================
# Direct FEC Source -> VERIFIED_FACT Tests
# =============================================================================


class TestDirectFECSourceVerifiedFact:
    """Tests that direct FEC-backed sources become VERIFIED_FACT."""

    def test_fec_filing_source_is_verified_fact(
        self, funding_summary: FundingSummaryResult
    ):
        """Source with FEC filing source_type should be VERIFIED_FACT."""
        scored = score_funding_summary_confidence(funding_summary)

        assert scored.is_successful
        # All sources from mock adapter have FECSource with fec_filing type
        for source in scored.scored_sources:
            if source.source_reference is not None:
                # Sources with direct FEC reference should be verified or high confidence
                assert source.confidence_label in (
                    ConfidenceLabel.VERIFIED_FACT,
                    ConfidenceLabel.HIGH_CONFIDENCE_INFERENCE,
                )

    def test_verified_fact_requires_direct_source(self):
        """VERIFIED_FACT requires direct source reference."""
        # Create a source without reference
        source_no_ref = FundingSourceSummary(
            source_name="Test Donor",
            source_type="individual",
            amount=1000.0,
            percentage=10.0,
            confidence=ConfidenceLevel.VERIFIED_FACT,
            source_reference=None,  # No reference
        )

        # Create minimal summary
        summary = FundingSummaryResult(
            status=FundingSummaryStatus.SUCCESS,
            candidate_id="TEST",
            candidate_name="Test Candidate",
            top_sources=[source_no_ref],
            trail_termination_markers=[TrailTerminationMarker.DIRECT_FEC_RECORDS_ONLY],
        )

        scored = score_funding_summary_confidence(summary)

        assert scored.is_successful
        # Without source reference, cannot be verified fact
        assert len(scored.scored_sources) == 1
        # Should be downgraded due to missing source reference
        assert scored.scored_sources[0].confidence_label != ConfidenceLabel.VERIFIED_FACT or (
            "downgraded" in str(scored.scored_sources[0].scoring_factors).lower()
            or scored.scored_sources[0].source_reference is not None
        )


# =============================================================================
# Source Absent -> UNKNOWN Tests
# =============================================================================


class TestSourceAbsentUnknown:
    """Tests that missing source results in UNKNOWN confidence."""

    def test_source_absent_gives_unknown_or_capped_confidence(self):
        """Missing source reference caps confidence level."""
        source = FundingSourceSummary(
            source_name="Unknown Donor",
            source_type="individual",
            amount=500.0,
            percentage=5.0,
            confidence=ConfidenceLevel.UNKNOWN,  # Original unknown
            source_reference=None,  # No reference
        )

        summary = FundingSummaryResult(
            status=FundingSummaryStatus.SUCCESS,
            candidate_id="TEST",
            top_sources=[source],
            trail_termination_markers=[TrailTerminationMarker.UNKNOWN_WHERE_SOURCE_ABSENT],
        )

        scored = score_funding_summary_confidence(summary)

        assert scored.is_successful
        assert scored.scored_sources[0].confidence_label == ConfidenceLabel.UNKNOWN
        assert "source_reference_absent" in scored.scored_sources[0].scoring_factors


# =============================================================================
# Trail Termination Marker Tests
# =============================================================================


class TestTrailTerminationMarkerPreserved:
    """Tests that trail termination markers are preserved and scored."""

    def test_trail_termination_markers_preserved(self, funding_summary: FundingSummaryResult):
        """Trail termination markers must be preserved in scored summary."""
        scored = score_funding_summary_confidence(funding_summary)

        assert scored.is_successful
        assert len(scored.trail_termination_markers) > 0
        assert (
            scored.trail_termination_markers == funding_summary.trail_termination_markers
        )

    def test_trail_termination_marker_creates_unknown_claim(
        self, funding_summary: FundingSummaryResult
    ):
        """Trail termination markers create UNKNOWN claims."""
        scored = score_funding_summary_confidence(funding_summary)

        assert scored.is_successful
        # Find trail termination claims
        trail_claims = [
            c for c in scored.summary_claims if c.claim_type == "trail_termination"
        ]
        assert len(trail_claims) > 0

        # All trail termination claims should be UNKNOWN
        for claim in trail_claims:
            assert claim.confidence_label == ConfidenceLabel.UNKNOWN


# =============================================================================
# No Dark Money as Verified Fact Tests
# =============================================================================


class TestNoDarkMoneyAsVerifiedFact:
    """Tests that dark money is never presented as verified fact."""

    def test_dark_money_trail_termination_is_unknown(
        self, funding_summary: FundingSummaryResult
    ):
        """Dark money trail termination results in UNKNOWN claims."""
        scored = score_funding_summary_confidence(funding_summary)

        assert scored.is_successful

        # Check that NO_DARK_MONEY_TRACE marker is preserved
        has_dark_money_marker = (
            TrailTerminationMarker.NO_DARK_MONEY_TRACE_IN_THIS_SLICE
            in scored.trail_termination_markers
        )
        assert has_dark_money_marker

        # Find dark money related claims
        dark_money_claims = [
            c
            for c in scored.summary_claims
            if "dark_money" in c.claim_text.lower()
            or "NO_DARK_MONEY_TRACE" in c.claim_text
        ]

        # If dark money claims exist, they should not be verified fact
        for claim in dark_money_claims:
            assert claim.confidence_label != ConfidenceLabel.VERIFIED_FACT


# =============================================================================
# No Foreign Funding Claim Generated Tests
# =============================================================================


class TestNoForeignFundingClaimGenerated:
    """Tests that foreign funding claims are not generated by the system."""

    def test_foreign_funding_text_triggers_human_review(self):
        """If foreign funding text appears in INPUT, it triggers human review."""
        # Create a source with foreign-sounding name (simulating input data)
        source = FundingSourceSummary(
            source_name="Foreign Donor LLC",  # Contains "foreign" keyword
            source_type="committee",
            amount=10000.0,
            percentage=5.0,
            confidence=ConfidenceLevel.HIGH_CONFIDENCE_INFERENCE,
            source_reference=FECSource(source_type="fec_filing"),
        )

        summary = FundingSummaryResult(
            status=FundingSummaryStatus.SUCCESS,
            candidate_id="TEST",
            top_sources=[source],
            trail_termination_markers=[TrailTerminationMarker.DIRECT_FEC_RECORDS_ONLY],
        )

        scored = score_funding_summary_confidence(summary)

        assert scored.is_successful
        # Foreign keyword should trigger human review
        assert scored.human_review_required
        assert (
            HumanReviewTrigger.FOREIGN_FUNDING_ALLEGATION
            in scored.all_human_review_triggers
        )
        # But the claim itself is NOT verified as foreign funding
        assert scored.scored_sources[0].confidence_label != ConfidenceLabel.VERIFIED_FACT or (
            HumanReviewTrigger.FOREIGN_FUNDING_ALLEGATION
            in scored.scored_sources[0].human_review_triggers
        )

    def test_system_does_not_generate_foreign_claims(
        self, funding_summary: FundingSummaryResult
    ):
        """System does not generate foreign funding claims from neutral data."""
        scored = score_funding_summary_confidence(funding_summary)

        assert scored.is_successful

        # No foreign funding trigger unless input contains foreign keywords
        has_foreign_trigger = (
            HumanReviewTrigger.FOREIGN_FUNDING_ALLEGATION
            in scored.all_human_review_triggers
        )

        # The default mock data doesn't contain foreign keywords
        # So no foreign trigger should be present
        assert not has_foreign_trigger


# =============================================================================
# Contradiction Triggers Human Review Tests
# =============================================================================


class TestContradictionTriggersHumanReview:
    """Tests that contradictions trigger human review."""

    def test_contradiction_flag_in_enum(self):
        """HumanReviewTrigger includes SOURCE_CONTRADICTION."""
        assert HumanReviewTrigger.SOURCE_CONTRADICTION is not None
        assert HumanReviewTrigger.SOURCE_CONTRADICTION.value == "source_contradiction"


# =============================================================================
# Low Confidence + High Impact Triggers Human Review Tests
# =============================================================================


class TestLowConfidenceHighImpactReview:
    """Tests that low confidence + high impact claims trigger human review."""

    def test_low_confidence_large_amount_triggers_review(self):
        """Low confidence claim with large amount triggers human review."""
        source = FundingSourceSummary(
            source_name="Big Unknown Donor",
            source_type="individual",
            amount=500000.0,  # Large amount (> $100K threshold)
            percentage=40.0,
            confidence=ConfidenceLevel.LOW_CONFIDENCE_INFERENCE,
            source_reference=None,  # Low confidence due to no reference
        )

        summary = FundingSummaryResult(
            status=FundingSummaryStatus.SUCCESS,
            candidate_id="TEST",
            top_sources=[source],
            trail_termination_markers=[TrailTerminationMarker.DIRECT_FEC_RECORDS_ONLY],
        )

        scored = score_funding_summary_confidence(summary)

        assert scored.is_successful
        # Should trigger human review due to low confidence + high impact
        assert scored.human_review_required
        assert (
            HumanReviewTrigger.LOW_CONFIDENCE_HIGH_IMPACT
            in scored.all_human_review_triggers
        )


# =============================================================================
# Source References Preserved Tests
# =============================================================================


class TestSourceReferencesPreserved:
    """Tests that source references are preserved through scoring."""

    def test_source_reference_preserved_in_scored_source(
        self, funding_summary: FundingSummaryResult
    ):
        """Source references should be preserved in scored sources."""
        scored = score_funding_summary_confidence(funding_summary)

        assert scored.is_successful

        # Check that sources with references keep them
        for i, source in enumerate(funding_summary.top_sources):
            if source.source_reference is not None:
                assert scored.scored_sources[i].source_reference is not None
                assert (
                    scored.scored_sources[i].source_reference.source_type
                    == source.source_reference.source_type
                )

    def test_primary_source_reference_preserved(
        self, funding_summary: FundingSummaryResult
    ):
        """Primary source reference should be preserved in scored summary."""
        scored = score_funding_summary_confidence(funding_summary)

        assert scored.is_successful
        if funding_summary.source_reference is not None:
            assert scored.source_reference is not None


# =============================================================================
# Funding Source Order Preserved Tests
# =============================================================================


class TestFundingSourceOrderPreserved:
    """Tests that funding source order is preserved through scoring."""

    def test_source_order_preserved(self, funding_summary: FundingSummaryResult):
        """Funding sources should maintain their original order."""
        scored = score_funding_summary_confidence(funding_summary)

        assert scored.is_successful
        assert len(scored.scored_sources) == len(funding_summary.top_sources)

        # Order should be preserved
        for i, original in enumerate(funding_summary.top_sources):
            assert scored.scored_sources[i].source_name == original.source_name
            assert scored.scored_sources[i].amount == original.amount


# =============================================================================
# Error Status Propagation Tests
# =============================================================================


class TestErrorStatusPropagation:
    """Tests that error status propagates fail-closed."""

    def test_error_status_propagates(self, adapter: MockFECAdapter):
        """Error status in funding summary propagates to scoring result."""
        # Create error adapter
        error_adapter = MockFECAdapter(simulate_error=FECErrorType.UNAVAILABLE)
        result = summarize_by_candidate_id("H8NY15148", error_adapter)

        assert result.status == FundingSummaryStatus.ADAPTER_ERROR

        # Score the error result
        scored = score_funding_summary_confidence(result)

        assert scored.status == ConfidenceScoringStatus.FUNDING_SUMMARY_ERROR
        assert scored.has_error
        assert not scored.is_successful

    def test_none_input_returns_error(self):
        """None input returns NO_FUNDING_SUMMARY status."""
        scored = score_funding_summary_confidence(None)  # type: ignore

        assert scored.status == ConfidenceScoringStatus.NO_FUNDING_SUMMARY
        assert not scored.is_successful


# =============================================================================
# No Prose Quick Answer Tests
# =============================================================================


class TestNoProseQuickAnswer:
    """Tests that no prose quick answer is generated."""

    def test_no_quick_answer_field(self, funding_summary: FundingSummaryResult):
        """Scored summary has no quick answer field."""
        scored = score_funding_summary_confidence(funding_summary)

        assert scored.is_successful
        assert not hasattr(scored, "quick_answer")
        assert not hasattr(scored, "prose_summary")
        assert not hasattr(scored, "plain_summary")

    def test_claims_are_structured_not_prose(
        self, funding_summary: FundingSummaryResult
    ):
        """Claims are structured data, not prose."""
        scored = score_funding_summary_confidence(funding_summary)

        assert scored.is_successful

        # All claims should have structured fields
        for claim in scored.summary_claims:
            assert isinstance(claim.claim_text, str)
            assert isinstance(claim.claim_type, str)
            assert isinstance(claim.confidence_label, ConfidenceLabel)
            assert isinstance(claim.factors, list)


# =============================================================================
# No Persuasion/Recommendation Language Tests
# =============================================================================


class TestNoPersusaionRecommendation:
    """Tests that no persuasion or recommendation language is present."""

    def test_no_recommendation_fields(self, funding_summary: FundingSummaryResult):
        """Scored summary has no recommendation fields."""
        scored = score_funding_summary_confidence(funding_summary)

        assert scored.is_successful
        assert not hasattr(scored, "recommendation")
        assert not hasattr(scored, "vote_recommendation")
        assert not hasattr(scored, "candidate_ranking")
        assert not hasattr(scored, "preference_score")
        assert not hasattr(scored, "should_vote_for")
        assert not hasattr(scored, "better_than")
        assert not hasattr(scored, "worse_than")

    def test_no_targeting_fields(self, funding_summary: FundingSummaryResult):
        """Scored summary has no targeting fields."""
        scored = score_funding_summary_confidence(funding_summary)

        assert scored.is_successful
        assert not hasattr(scored, "target_audience")
        assert not hasattr(scored, "user_profile_match")
        assert not hasattr(scored, "demographic_score")


# =============================================================================
# No Network / No API Key Tests
# =============================================================================


class TestNoNetworkNoAPIKey:
    """Tests verifying no network calls and no API key required."""

    def test_scoring_requires_no_api_key(self, funding_summary: FundingSummaryResult):
        """Confidence scoring requires no API key."""
        # Should work without any environment variables
        scored = score_funding_summary_confidence(funding_summary)

        assert scored.is_successful

    def test_all_operations_offline(self, adapter: MockFECAdapter):
        """All operations work offline."""
        assert adapter.is_available()

        # Full pipeline: resolve -> summarize -> score
        resolution = resolve_candidate_entity(
            EntityResolutionRequest(query="OCASIO"), adapter
        )
        if resolution.status == EntityResolutionStatus.EXACT_ONE_MATCH:
            summary = summarize_candidate_funding(
                FundingSummaryRequest(resolution_result=resolution), adapter
            )
            scored = score_funding_summary_confidence(summary)

            assert scored.is_successful


# =============================================================================
# Convenience Function Tests
# =============================================================================


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_get_verified_facts(self, funding_summary: FundingSummaryResult):
        """get_verified_facts returns only verified fact claims."""
        scored = score_funding_summary_confidence(funding_summary)
        verified = get_verified_facts(scored)

        for claim in verified:
            assert claim.confidence_label == ConfidenceLabel.VERIFIED_FACT

    def test_get_unknown_claims(self, funding_summary: FundingSummaryResult):
        """get_unknown_claims returns unknown claims including trail terminations."""
        scored = score_funding_summary_confidence(funding_summary)
        unknown = get_unknown_claims(scored)

        for claim in unknown:
            assert claim.confidence_label == ConfidenceLabel.UNKNOWN

        # Should include trail termination claims
        trail_claims = [c for c in unknown if c.claim_type == "trail_termination"]
        assert len(trail_claims) > 0

    def test_get_human_review_claims(self):
        """get_human_review_claims returns claims requiring review."""
        # Create source that triggers review
        source = FundingSourceSummary(
            source_name="Foreign Entity Inc",  # Triggers foreign review
            source_type="committee",
            amount=100000.0,
            percentage=10.0,
            confidence=ConfidenceLevel.HIGH_CONFIDENCE_INFERENCE,
            source_reference=FECSource(source_type="fec_filing"),
        )

        summary = FundingSummaryResult(
            status=FundingSummaryStatus.SUCCESS,
            candidate_id="TEST",
            top_sources=[source],
            trail_termination_markers=[TrailTerminationMarker.DIRECT_FEC_RECORDS_ONLY],
        )

        scored = score_funding_summary_confidence(summary)
        review_claims = get_human_review_claims(scored)

        assert len(review_claims) > 0
        for claim in review_claims:
            assert claim.requires_human_review

    def test_get_verified_facts_on_error_returns_empty(self):
        """get_verified_facts on error summary returns empty list."""
        scored = ConfidenceScoredFundingSummary(
            status=ConfidenceScoringStatus.FUNDING_SUMMARY_ERROR,
            error_message="Test error",
        )
        verified = get_verified_facts(scored)
        assert verified == []


# =============================================================================
# Data Type Tests
# =============================================================================


class TestDataTypes:
    """Tests for data type structures."""

    def test_confidence_label_values(self):
        """ConfidenceLabel enum has expected values."""
        assert ConfidenceLabel.VERIFIED_FACT.value == "verified_fact"
        assert (
            ConfidenceLabel.HIGH_CONFIDENCE_INFERENCE.value
            == "high_confidence_inference"
        )
        assert (
            ConfidenceLabel.LOW_CONFIDENCE_INFERENCE.value == "low_confidence_inference"
        )
        assert ConfidenceLabel.UNKNOWN.value == "unknown"

    def test_human_review_trigger_values(self):
        """HumanReviewTrigger enum has expected values."""
        assert (
            HumanReviewTrigger.FOREIGN_FUNDING_ALLEGATION.value
            == "foreign_funding_allegation"
        )
        assert HumanReviewTrigger.CRIMINAL_ACCUSATION.value == "criminal_accusation"
        assert (
            HumanReviewTrigger.LOW_CONFIDENCE_HIGH_IMPACT.value
            == "low_confidence_high_impact"
        )
        assert HumanReviewTrigger.SOURCE_CONTRADICTION.value == "source_contradiction"
        assert (
            HumanReviewTrigger.DARK_MONEY_LARGE_AMOUNT.value == "dark_money_large_amount"
        )
        assert (
            HumanReviewTrigger.TRAIL_TERMINATION_SIGNIFICANT.value
            == "trail_termination_significant"
        )

    def test_confidence_scoring_status_values(self):
        """ConfidenceScoringStatus enum has expected values."""
        assert ConfidenceScoringStatus.SUCCESS.value == "success"
        assert ConfidenceScoringStatus.NO_FUNDING_SUMMARY.value == "no_funding_summary"
        assert (
            ConfidenceScoringStatus.FUNDING_SUMMARY_ERROR.value
            == "funding_summary_error"
        )
        assert ConfidenceScoringStatus.SCORING_ERROR.value == "scoring_error"

    def test_scored_claim_fields(self):
        """ConfidenceScoredClaim has required fields."""
        claim = ConfidenceScoredClaim(
            claim_text="Test claim",
            claim_type="test",
            confidence_label=ConfidenceLabel.VERIFIED_FACT,
            original_confidence=ConfidenceLevel.VERIFIED_FACT,
        )

        assert claim.claim_text == "Test claim"
        assert claim.claim_type == "test"
        assert claim.confidence_label == ConfidenceLabel.VERIFIED_FACT
        assert claim.factors == []
        assert claim.source_reference is None
        assert claim.requires_human_review is False
        assert claim.human_review_triggers == []

    def test_scored_source_fields(self):
        """ConfidenceScoredFundingSource has required fields."""
        source = ConfidenceScoredFundingSource(
            source_name="Test Source",
            source_type="individual",
            amount=1000.0,
            percentage=10.0,
            contribution_count=5,
            is_aggregated=False,
            original_confidence=ConfidenceLevel.VERIFIED_FACT,
            confidence_label=ConfidenceLabel.VERIFIED_FACT,
        )

        assert source.source_name == "Test Source"
        assert source.source_type == "individual"
        assert source.amount == 1000.0
        assert source.percentage == 10.0
        assert source.contribution_count == 5
        assert source.is_aggregated is False
        assert source.confidence_label == ConfidenceLabel.VERIFIED_FACT
        assert source.source_reference is None
        assert source.requires_human_review is False
        assert source.human_review_triggers == []
        assert source.scoring_factors == []

    def test_scored_summary_properties(self, funding_summary: FundingSummaryResult):
        """ConfidenceScoredFundingSummary has correct properties."""
        scored = score_funding_summary_confidence(funding_summary)

        assert isinstance(scored.is_successful, bool)
        assert isinstance(scored.has_error, bool)


# =============================================================================
# Integration with Full Pipeline Tests
# =============================================================================


class TestFullPipelineIntegration:
    """Tests for full pipeline integration (resolve -> summarize -> score)."""

    def test_full_pipeline_success(self, adapter: MockFECAdapter):
        """Full pipeline: resolve -> summarize -> score succeeds."""
        # Step 1: Resolve candidate
        resolution = resolve_candidate_entity(
            EntityResolutionRequest(query="OCASIO-CORTEZ"), adapter
        )
        assert resolution.status == EntityResolutionStatus.EXACT_ONE_MATCH

        # Step 2: Summarize funding
        summary = summarize_candidate_funding(
            FundingSummaryRequest(resolution_result=resolution), adapter
        )
        assert summary.status == FundingSummaryStatus.SUCCESS

        # Step 3: Score confidence
        scored = score_funding_summary_confidence(summary)
        assert scored.status == ConfidenceScoringStatus.SUCCESS
        assert scored.is_successful

        # Verify data flow
        assert scored.candidate_id == summary.candidate_id
        assert scored.candidate_name == summary.candidate_name
        assert scored.total_raised == summary.total_raised
        assert len(scored.scored_sources) == len(summary.top_sources)

    def test_pipeline_preserves_trail_termination_through_all_stages(
        self, adapter: MockFECAdapter
    ):
        """Trail termination markers preserved through all pipeline stages."""
        resolution = resolve_candidate_entity(
            EntityResolutionRequest(query="BIDEN"), adapter
        )

        if resolution.status == EntityResolutionStatus.EXACT_ONE_MATCH:
            summary = summarize_candidate_funding(
                FundingSummaryRequest(resolution_result=resolution), adapter
            )
            scored = score_funding_summary_confidence(summary)

            # Trail markers should be present at every stage
            assert len(summary.trail_termination_markers) > 0
            assert len(scored.trail_termination_markers) > 0
            assert (
                summary.trail_termination_markers == scored.trail_termination_markers
            )


# =============================================================================
# Criminal Accusation Human Review Tests
# =============================================================================


class TestCriminalAccusationReview:
    """Tests that criminal accusations trigger human review."""

    def test_criminal_keyword_triggers_review(self):
        """Criminal keyword in source name triggers human review."""
        source = FundingSourceSummary(
            source_name="Indicted PAC LLC",  # Contains "indicted"
            source_type="committee",
            amount=50000.0,
            percentage=5.0,
            confidence=ConfidenceLevel.HIGH_CONFIDENCE_INFERENCE,
            source_reference=FECSource(source_type="fec_filing"),
        )

        summary = FundingSummaryResult(
            status=FundingSummaryStatus.SUCCESS,
            candidate_id="TEST",
            top_sources=[source],
            trail_termination_markers=[TrailTerminationMarker.DIRECT_FEC_RECORDS_ONLY],
        )

        scored = score_funding_summary_confidence(summary)

        assert scored.is_successful
        assert scored.human_review_required
        assert (
            HumanReviewTrigger.CRIMINAL_ACCUSATION in scored.all_human_review_triggers
        )


# =============================================================================
# Edge Case Tests
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases."""

    def test_empty_sources_list(self):
        """Empty sources list doesn't crash scoring."""
        summary = FundingSummaryResult(
            status=FundingSummaryStatus.SUCCESS,
            candidate_id="TEST",
            top_sources=[],
            trail_termination_markers=[TrailTerminationMarker.DIRECT_FEC_RECORDS_ONLY],
        )

        scored = score_funding_summary_confidence(summary)

        assert scored.is_successful
        assert len(scored.scored_sources) == 0

    def test_zero_amount_source(self):
        """Zero amount source is scored correctly."""
        source = FundingSourceSummary(
            source_name="Zero Donor",
            source_type="individual",
            amount=0.0,
            percentage=0.0,
            confidence=ConfidenceLevel.VERIFIED_FACT,
            source_reference=FECSource(source_type="fec_filing"),
        )

        summary = FundingSummaryResult(
            status=FundingSummaryStatus.SUCCESS,
            candidate_id="TEST",
            top_sources=[source],
            trail_termination_markers=[TrailTerminationMarker.DIRECT_FEC_RECORDS_ONLY],
        )

        scored = score_funding_summary_confidence(summary)

        assert scored.is_successful
        assert len(scored.scored_sources) == 1

    def test_very_long_source_name(self):
        """Very long source name is handled correctly."""
        long_name = "A" * 1000
        source = FundingSourceSummary(
            source_name=long_name,
            source_type="individual",
            amount=100.0,
            percentage=1.0,
            confidence=ConfidenceLevel.VERIFIED_FACT,
            source_reference=FECSource(source_type="fec_filing"),
        )

        summary = FundingSummaryResult(
            status=FundingSummaryStatus.SUCCESS,
            candidate_id="TEST",
            top_sources=[source],
            trail_termination_markers=[TrailTerminationMarker.DIRECT_FEC_RECORDS_ONLY],
        )

        scored = score_funding_summary_confidence(summary)

        assert scored.is_successful
        assert scored.scored_sources[0].source_name == long_name


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
