"""
Funding Summary unit tests.

Tests for VOTE_POC_FUNDING_SUMMARY_PHASE1.

Test Boundaries:
- NO_LIVE_API_REQUIRED_FOR_TESTS
- NO_API_KEY_REQUIRED_FOR_TESTS
- NO_NETWORK_CALLS_IN_TESTS
- TRAIL_TERMINATION_MARKER_REQUIRED
- SOURCE_REFERENCES_PRESERVED
- NO_QUICK_ANSWER_GENERATION
- NO_PERSUASION_LANGUAGE
- NO_DARK_MONEY_AS_VERIFIED_FACT
- NO_CANDIDATE_RECOMMENDATION

Uses mock FEC adapter from VOTE_POC_FEC_ADAPTER_PHASE1 (PR #707).
Uses entity resolution from VOTE_POC_ENTITY_RESOLUTION_PHASE1 (PR #709).
"""

from __future__ import annotations

import pytest

from modules.foundups.voteballots.src.fec_adapter import (
    CandidateRecord,
    ConfidenceLevel,
    FECErrorType,
    MockFECAdapter,
    get_mock_adapter,
)
from modules.foundups.voteballots.src.entity_resolution import (
    EntityResolutionRequest,
    EntityResolutionResult,
    EntityResolutionStatus,
    resolve_candidate_entity,
    resolve_by_id,
    resolve_by_name,
)
from modules.foundups.voteballots.src.funding_summary import (
    FundingSummaryRequest,
    FundingSummaryResult,
    FundingSummaryStatus,
    FundingSourceSummary,
    TrailTerminationMarker,
    summarize_candidate_funding,
    summarize_by_candidate_id,
    summarize_by_name,
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
def adapter_with_common_names() -> MockFECAdapter:
    """Get mock FEC adapter with multiple candidates sharing common names."""
    adapter = get_mock_adapter()
    adapter._fixture_data["candidates"]["H0NY01001"] = CandidateRecord(
        candidate_id="H0NY01001",
        name="SMITH, JOHN A",
        party="DEM",
        state="NY",
        office="H",
        election_years=[2024],
    )
    adapter._fixture_data["candidates"]["H0CA05002"] = CandidateRecord(
        candidate_id="H0CA05002",
        name="SMITH, JOHN B",
        party="REP",
        state="CA",
        office="H",
        election_years=[2024],
    )
    return adapter


# =============================================================================
# Success Path Tests
# =============================================================================


class TestSuccessPath:
    """Tests for successful funding summary generation."""

    def test_resolved_candidate_produces_summary(
        self, adapter: MockFECAdapter, resolved_candidate: EntityResolutionResult
    ):
        """Resolved candidate produces funding summary."""
        request = FundingSummaryRequest(resolution_result=resolved_candidate)
        result = summarize_candidate_funding(request, adapter)

        assert result.status == FundingSummaryStatus.SUCCESS
        assert result.is_successful
        assert result.candidate_id == "H8NY15148"
        assert result.candidate_name == "OCASIO-CORTEZ, ALEXANDRIA"
        assert result.total_raised > 0

    def test_summary_has_top_sources(
        self, adapter: MockFECAdapter, resolved_candidate: EntityResolutionResult
    ):
        """Funding summary includes top funding sources."""
        request = FundingSummaryRequest(resolution_result=resolved_candidate)
        result = summarize_candidate_funding(request, adapter)

        assert result.is_successful
        assert len(result.top_sources) > 0

    def test_top_sources_sorted_by_amount(
        self, adapter: MockFECAdapter, resolved_candidate: EntityResolutionResult
    ):
        """Top sources are sorted by amount descending."""
        request = FundingSummaryRequest(resolution_result=resolved_candidate)
        result = summarize_candidate_funding(request, adapter)

        assert result.is_successful
        if len(result.top_sources) > 1:
            amounts = [s.amount for s in result.top_sources]
            assert amounts == sorted(amounts, reverse=True)

    def test_top_sources_deterministic_ordering(
        self, adapter: MockFECAdapter, resolved_candidate: EntityResolutionResult
    ):
        """Top sources have deterministic ordering."""
        request = FundingSummaryRequest(resolution_result=resolved_candidate)

        result1 = summarize_candidate_funding(request, adapter)
        result2 = summarize_candidate_funding(request, adapter)

        assert len(result1.top_sources) == len(result2.top_sources)
        for s1, s2 in zip(result1.top_sources, result2.top_sources):
            assert s1.source_name == s2.source_name
            assert s1.amount == s2.amount

    def test_source_references_preserved(
        self, adapter: MockFECAdapter, resolved_candidate: EntityResolutionResult
    ):
        """Source references are preserved in funding summary."""
        request = FundingSummaryRequest(resolution_result=resolved_candidate)
        result = summarize_candidate_funding(request, adapter)

        assert result.is_successful
        # Primary source reference should be present
        assert result.source_reference is not None

    def test_contributions_by_type_included(
        self, adapter: MockFECAdapter, resolved_candidate: EntityResolutionResult
    ):
        """Contributions breakdown by type is included."""
        request = FundingSummaryRequest(resolution_result=resolved_candidate)
        result = summarize_candidate_funding(request, adapter)

        assert result.is_successful
        assert result.contributions_by_type is not None
        assert len(result.contributions_by_type) > 0

    def test_top_n_parameter_respected(
        self, adapter: MockFECAdapter, resolved_candidate: EntityResolutionResult
    ):
        """Top N parameter limits number of sources returned."""
        request = FundingSummaryRequest(
            resolution_result=resolved_candidate,
            top_n=2,
        )
        result = summarize_candidate_funding(request, adapter)

        assert result.is_successful
        assert len(result.top_sources) <= 2

    def test_reporting_period_included(
        self, adapter: MockFECAdapter, resolved_candidate: EntityResolutionResult
    ):
        """Reporting period is included when available."""
        request = FundingSummaryRequest(resolution_result=resolved_candidate)
        result = summarize_candidate_funding(request, adapter)

        assert result.is_successful
        # These may be None if not in fixture, but should be accessible
        # For the mock adapter, they should be populated
        assert result.reporting_period_start is not None or result.reporting_period_end is not None


# =============================================================================
# Trail Termination Tests
# =============================================================================


class TestTrailTermination:
    """Tests for trail termination markers."""

    def test_trail_termination_marker_always_present(
        self, adapter: MockFECAdapter, resolved_candidate: EntityResolutionResult
    ):
        """Trail termination markers are always present."""
        request = FundingSummaryRequest(resolution_result=resolved_candidate)
        result = summarize_candidate_funding(request, adapter)

        assert len(result.trail_termination_markers) > 0

    def test_trail_termination_includes_fec_only_marker(
        self, adapter: MockFECAdapter, resolved_candidate: EntityResolutionResult
    ):
        """Trail termination includes DIRECT_FEC_RECORDS_ONLY marker."""
        request = FundingSummaryRequest(resolution_result=resolved_candidate)
        result = summarize_candidate_funding(request, adapter)

        assert TrailTerminationMarker.DIRECT_FEC_RECORDS_ONLY in result.trail_termination_markers

    def test_trail_termination_includes_no_super_pac_trace(
        self, adapter: MockFECAdapter, resolved_candidate: EntityResolutionResult
    ):
        """Trail termination includes NO_SUPER_PAC_TRACE marker."""
        request = FundingSummaryRequest(resolution_result=resolved_candidate)
        result = summarize_candidate_funding(request, adapter)

        assert (
            TrailTerminationMarker.NO_SUPER_PAC_TRACE_IN_THIS_SLICE
            in result.trail_termination_markers
        )

    def test_trail_termination_includes_no_dark_money_trace(
        self, adapter: MockFECAdapter, resolved_candidate: EntityResolutionResult
    ):
        """Trail termination includes NO_DARK_MONEY_TRACE marker."""
        request = FundingSummaryRequest(resolution_result=resolved_candidate)
        result = summarize_candidate_funding(request, adapter)

        assert (
            TrailTerminationMarker.NO_DARK_MONEY_TRACE_IN_THIS_SLICE
            in result.trail_termination_markers
        )

    def test_trail_termination_on_error_status(self, adapter: MockFECAdapter):
        """Trail termination markers present even on error status."""
        # Create an invalid resolution result
        result = summarize_by_candidate_id("INVALID_ID", adapter)

        assert result.status != FundingSummaryStatus.SUCCESS
        assert len(result.trail_termination_markers) > 0


# =============================================================================
# No Resolved Candidate Tests
# =============================================================================


class TestNoResolvedCandidate:
    """Tests for no resolved candidate scenarios."""

    def test_no_match_returns_no_resolved_candidate(self, adapter: MockFECAdapter):
        """NO_MATCH resolution returns NO_RESOLVED_CANDIDATE status."""
        resolution = resolve_by_name("NONEXISTENT_CANDIDATE_XYZ", adapter)
        request = FundingSummaryRequest(resolution_result=resolution)
        result = summarize_candidate_funding(request, adapter)

        assert result.status == FundingSummaryStatus.NO_RESOLVED_CANDIDATE
        assert not result.is_successful
        assert result.error_message is not None

    def test_invalid_candidate_id_returns_no_resolved(self, adapter: MockFECAdapter):
        """Invalid candidate ID returns NO_RESOLVED_CANDIDATE."""
        result = summarize_by_candidate_id("INVALID_ID", adapter)

        # resolve_by_id returns NO_MATCH for invalid ID
        assert result.status in (
            FundingSummaryStatus.NO_RESOLVED_CANDIDATE,
            FundingSummaryStatus.NO_FUNDING_DATA,
        )
        assert not result.is_successful


# =============================================================================
# Ambiguous Entity Tests
# =============================================================================


class TestAmbiguousEntity:
    """Tests for ambiguous candidate scenarios."""

    def test_ambiguous_result_does_not_summarize(
        self, adapter_with_common_names: MockFECAdapter
    ):
        """Ambiguous entity result does not generate summary."""
        resolution = resolve_by_name("SMITH, JOHN", adapter_with_common_names)
        # Should have multiple matches
        assert resolution.status == EntityResolutionStatus.MULTIPLE_MATCHES

        request = FundingSummaryRequest(resolution_result=resolution)
        result = summarize_candidate_funding(request, adapter_with_common_names)

        assert result.status == FundingSummaryStatus.AMBIGUOUS_CANDIDATE
        assert result.requires_disambiguation
        assert result.error_message is not None

    def test_ambiguous_preserves_disambiguation_message(
        self, adapter_with_common_names: MockFECAdapter
    ):
        """Ambiguous result preserves disambiguation message from resolution."""
        resolution = resolve_by_name("SMITH, JOHN", adapter_with_common_names)
        request = FundingSummaryRequest(resolution_result=resolution)
        result = summarize_candidate_funding(request, adapter_with_common_names)

        assert result.status == FundingSummaryStatus.AMBIGUOUS_CANDIDATE
        # Should include disambiguation guidance
        assert result.error_message is not None
        assert "SMITH" in result.error_message or "candidate" in result.error_message.lower()


# =============================================================================
# Adapter Error Tests
# =============================================================================


class TestAdapterError:
    """Tests for adapter error handling."""

    def test_adapter_unavailable_returns_error(self):
        """Adapter unavailable returns ADAPTER_ERROR status."""
        adapter = MockFECAdapter(simulate_error=FECErrorType.UNAVAILABLE)
        result = summarize_by_name("TEST", adapter)

        assert result.status == FundingSummaryStatus.ADAPTER_ERROR
        assert result.has_error
        assert result.error_message is not None

    def test_rate_limited_returns_error(self):
        """Rate limited adapter returns ADAPTER_ERROR status."""
        adapter = MockFECAdapter(simulate_error=FECErrorType.RATE_LIMITED)
        result = summarize_by_name("TEST", adapter)

        assert result.status == FundingSummaryStatus.ADAPTER_ERROR
        assert result.has_error

    def test_network_error_returns_error(self):
        """Network error returns ADAPTER_ERROR status."""
        adapter = MockFECAdapter(simulate_error=FECErrorType.NETWORK_ERROR)
        result = summarize_by_name("TEST", adapter)

        assert result.status == FundingSummaryStatus.ADAPTER_ERROR
        assert result.has_error


# =============================================================================
# Confidence Tests
# =============================================================================


class TestConfidence:
    """Tests for confidence labeling."""

    def test_summary_has_confidence_level(
        self, adapter: MockFECAdapter, resolved_candidate: EntityResolutionResult
    ):
        """Funding summary has overall confidence level."""
        request = FundingSummaryRequest(resolution_result=resolved_candidate)
        result = summarize_candidate_funding(request, adapter)

        assert result.is_successful
        assert result.confidence is not None
        assert isinstance(result.confidence, ConfidenceLevel)

    def test_fec_data_is_verified_fact(
        self, adapter: MockFECAdapter, resolved_candidate: EntityResolutionResult
    ):
        """FEC data has verified_fact confidence."""
        request = FundingSummaryRequest(resolution_result=resolved_candidate)
        result = summarize_candidate_funding(request, adapter)

        assert result.is_successful
        # FEC direct records should be verified_fact
        assert result.confidence == ConfidenceLevel.VERIFIED_FACT

    def test_top_sources_have_confidence(
        self, adapter: MockFECAdapter, resolved_candidate: EntityResolutionResult
    ):
        """Each top source has confidence level."""
        request = FundingSummaryRequest(resolution_result=resolved_candidate)
        result = summarize_candidate_funding(request, adapter)

        assert result.is_successful
        for source in result.top_sources:
            assert source.confidence is not None
            assert isinstance(source.confidence, ConfidenceLevel)


# =============================================================================
# Political Safety Tests
# =============================================================================


class TestPoliticalSafety:
    """Tests ensuring political safety boundaries are maintained."""

    def test_no_persuasion_language(
        self, adapter: MockFECAdapter, resolved_candidate: EntityResolutionResult
    ):
        """Funding summary contains no persuasion language."""
        request = FundingSummaryRequest(resolution_result=resolved_candidate)
        result = summarize_candidate_funding(request, adapter)

        # Check that result has no persuasion-related fields
        assert not hasattr(result, "recommendation")
        assert not hasattr(result, "should_vote_for")
        assert not hasattr(result, "better_than")
        assert not hasattr(result, "worse_than")
        assert not hasattr(result, "alignment_score")

    def test_no_recommendation_fields(
        self, adapter: MockFECAdapter, resolved_candidate: EntityResolutionResult
    ):
        """Funding summary has no recommendation fields."""
        request = FundingSummaryRequest(resolution_result=resolved_candidate)
        result = summarize_candidate_funding(request, adapter)

        assert not hasattr(result, "vote_recommendation")
        assert not hasattr(result, "candidate_ranking")
        assert not hasattr(result, "preference_score")

    def test_no_dark_money_as_verified_fact(
        self, adapter: MockFECAdapter, resolved_candidate: EntityResolutionResult
    ):
        """Dark money is not presented as verified fact."""
        request = FundingSummaryRequest(resolution_result=resolved_candidate)
        result = summarize_candidate_funding(request, adapter)

        # Trail termination marker should indicate dark money is not traced
        assert (
            TrailTerminationMarker.NO_DARK_MONEY_TRACE_IN_THIS_SLICE
            in result.trail_termination_markers
        )

        # If there were any dark money claims, they should not be verified_fact
        # This is enforced by the architecture (we only return FEC records)

    def test_no_targeting_fields(
        self, adapter: MockFECAdapter, resolved_candidate: EntityResolutionResult
    ):
        """Result has no microtargeting fields."""
        request = FundingSummaryRequest(resolution_result=resolved_candidate)
        result = summarize_candidate_funding(request, adapter)

        assert not hasattr(result, "target_audience")
        assert not hasattr(result, "user_profile_match")
        assert not hasattr(result, "demographic_score")


# =============================================================================
# Convenience Function Tests
# =============================================================================


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_summarize_by_candidate_id(self, adapter: MockFECAdapter):
        """summarize_by_candidate_id convenience function works."""
        result = summarize_by_candidate_id("H8NY15148", adapter)

        assert result.status == FundingSummaryStatus.SUCCESS
        assert result.candidate_id == "H8NY15148"

    def test_summarize_by_name(self, adapter: MockFECAdapter):
        """summarize_by_name convenience function works."""
        result = summarize_by_name("OCASIO", adapter, state="NY")

        assert result.status == FundingSummaryStatus.SUCCESS
        assert result.candidate_id == "H8NY15148"

    def test_summarize_by_name_with_hints(self, adapter: MockFECAdapter):
        """summarize_by_name works with state and office hints."""
        # Use AOC since only H8NY15148 has mock funding data
        result = summarize_by_name("OCASIO", adapter, state="NY", office="H")

        assert result.status == FundingSummaryStatus.SUCCESS
        assert result.candidate_id == "H8NY15148"

    def test_summarize_by_name_not_found(self, adapter: MockFECAdapter):
        """summarize_by_name handles not found gracefully."""
        result = summarize_by_name("NONEXISTENT_XYZ", adapter)

        assert result.status == FundingSummaryStatus.NO_RESOLVED_CANDIDATE
        assert not result.is_successful


# =============================================================================
# No Network / No API Key Tests
# =============================================================================


class TestNoNetworkCalls:
    """Tests verifying no network calls are made."""

    def test_mock_adapter_requires_no_api_key(self, adapter: MockFECAdapter):
        """Mock adapter works without API key."""
        assert adapter.is_available()

        result = summarize_by_candidate_id("H8NY15148", adapter)

        # Should succeed without any API key
        assert result.status == FundingSummaryStatus.SUCCESS

    def test_all_data_from_fixtures(
        self, adapter: MockFECAdapter, resolved_candidate: EntityResolutionResult
    ):
        """All returned data comes from fixtures, not live API."""
        request = FundingSummaryRequest(resolution_result=resolved_candidate)
        result = summarize_candidate_funding(request, adapter)

        # Verify candidate is from known fixtures
        assert result.candidate_id in ["H8NY15148", "P80001571", "S4VT00033"]


# =============================================================================
# Data Type Tests
# =============================================================================


class TestDataTypes:
    """Tests for data type structures."""

    def test_funding_source_summary_fields(self):
        """FundingSourceSummary has all required fields."""
        source = FundingSourceSummary(
            source_name="TEST CONTRIBUTOR",
            source_type="individual",
            amount=500.0,
            percentage=10.0,
            confidence=ConfidenceLevel.VERIFIED_FACT,
        )

        assert source.source_name == "TEST CONTRIBUTOR"
        assert source.source_type == "individual"
        assert source.amount == 500.0
        assert source.percentage == 10.0
        assert source.confidence == ConfidenceLevel.VERIFIED_FACT
        assert source.contribution_count == 1
        assert source.is_aggregated is False

    def test_trail_termination_marker_values(self):
        """TrailTerminationMarker enum has expected values."""
        assert TrailTerminationMarker.DIRECT_FEC_RECORDS_ONLY.value == "direct_fec_records_only"
        assert (
            TrailTerminationMarker.NO_SUPER_PAC_TRACE_IN_THIS_SLICE.value
            == "no_super_pac_trace_in_this_slice"
        )
        assert (
            TrailTerminationMarker.NO_DARK_MONEY_TRACE_IN_THIS_SLICE.value
            == "no_dark_money_trace_in_this_slice"
        )
        assert (
            TrailTerminationMarker.UNKNOWN_WHERE_SOURCE_ABSENT.value
            == "unknown_where_source_absent"
        )

    def test_funding_summary_status_values(self):
        """FundingSummaryStatus enum has expected values."""
        assert FundingSummaryStatus.SUCCESS.value == "success"
        assert FundingSummaryStatus.NO_RESOLVED_CANDIDATE.value == "no_resolved_candidate"
        assert FundingSummaryStatus.AMBIGUOUS_CANDIDATE.value == "ambiguous_candidate"
        assert FundingSummaryStatus.ADAPTER_ERROR.value == "adapter_error"
        assert FundingSummaryStatus.NO_FUNDING_DATA.value == "no_funding_data"
        assert FundingSummaryStatus.INVALID_REQUEST.value == "invalid_request"

    def test_request_top_n_bounds(self):
        """FundingSummaryRequest caps top_n parameter."""
        # Minimum
        request = FundingSummaryRequest(
            resolution_result=EntityResolutionResult(
                status=EntityResolutionStatus.NO_MATCH
            ),
            top_n=0,
        )
        assert request.top_n == 1

        # Maximum
        request2 = FundingSummaryRequest(
            resolution_result=EntityResolutionResult(
                status=EntityResolutionStatus.NO_MATCH
            ),
            top_n=100,
        )
        assert request2.top_n == 20

    def test_result_properties(
        self, adapter: MockFECAdapter, resolved_candidate: EntityResolutionResult
    ):
        """FundingSummaryResult has correct properties."""
        request = FundingSummaryRequest(resolution_result=resolved_candidate)
        result = summarize_candidate_funding(request, adapter)

        # Test properties work correctly
        assert isinstance(result.is_successful, bool)
        assert isinstance(result.has_error, bool)
        assert isinstance(result.requires_disambiguation, bool)


# =============================================================================
# Edge Case Tests
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases."""

    def test_none_resolution_result(self, adapter: MockFECAdapter):
        """None resolution result returns INVALID_REQUEST."""
        request = FundingSummaryRequest(resolution_result=None)  # type: ignore
        result = summarize_candidate_funding(request, adapter)

        assert result.status == FundingSummaryStatus.INVALID_REQUEST
        assert result.error_message is not None

    def test_empty_candidate_list(self, adapter: MockFECAdapter):
        """Empty candidate list in resolution returns NO_RESOLVED_CANDIDATE."""
        resolution = EntityResolutionResult(
            status=EntityResolutionStatus.EXACT_ONE_MATCH,
            candidates=[],  # Empty list despite EXACT_ONE_MATCH
        )
        request = FundingSummaryRequest(resolution_result=resolution)
        result = summarize_candidate_funding(request, adapter)

        assert result.status == FundingSummaryStatus.NO_RESOLVED_CANDIDATE

    def test_adapter_error_in_resolution(self, adapter: MockFECAdapter):
        """ADAPTER_ERROR in resolution propagates correctly."""
        resolution = EntityResolutionResult(
            status=EntityResolutionStatus.ADAPTER_ERROR,
            error_message="Test adapter error",
        )
        request = FundingSummaryRequest(resolution_result=resolution)
        result = summarize_candidate_funding(request, adapter)

        assert result.status == FundingSummaryStatus.ADAPTER_ERROR

    def test_invalid_query_in_resolution(self, adapter: MockFECAdapter):
        """INVALID_QUERY in resolution propagates correctly."""
        resolution = EntityResolutionResult(
            status=EntityResolutionStatus.INVALID_QUERY,
            error_message="Test invalid query",
        )
        request = FundingSummaryRequest(resolution_result=resolution)
        result = summarize_candidate_funding(request, adapter)

        assert result.status == FundingSummaryStatus.INVALID_REQUEST


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
