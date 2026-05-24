"""
FEC Adapter unit tests.

Tests for VOTE_POC_FEC_ADAPTER_PHASE1.

Test Boundaries:
- NO_LIVE_API_REQUIRED_FOR_TESTS
- NO_API_KEY_REQUIRED_FOR_TESTS
- NO_NETWORK_CALLS_UNLESS_MOCKED
"""

from __future__ import annotations

import pytest
from pathlib import Path

from modules.foundups.voteballots.src.fec_adapter import (
    CandidateRecord,
    CandidateSearchResult,
    CommitteeRecord,
    CommitteeSearchResult,
    ConfidenceLevel,
    ContributionRecord,
    ContributionSearchResult,
    FECError,
    FECErrorType,
    FECSource,
    FundingSummary,
    FundingSummaryResult,
    MockFECAdapter,
    create_fec_adapter,
    get_mock_adapter,
)


# =============================================================================
# Adapter Creation Tests
# =============================================================================


class TestAdapterCreation:
    """Tests for adapter factory and creation."""

    def test_create_mock_adapter_default(self):
        """Mock adapter is the default mode."""
        adapter = create_fec_adapter()
        assert isinstance(adapter, MockFECAdapter)

    def test_create_mock_adapter_explicit(self):
        """Mock adapter can be created explicitly."""
        adapter = create_fec_adapter(mode="mock")
        assert isinstance(adapter, MockFECAdapter)

    def test_get_mock_adapter_convenience(self):
        """Convenience function returns mock adapter."""
        adapter = get_mock_adapter()
        assert isinstance(adapter, MockFECAdapter)
        assert adapter.is_available()

    def test_live_adapter_not_implemented(self):
        """Live adapter raises NotImplementedError in Phase 1."""
        with pytest.raises(NotImplementedError) as exc_info:
            create_fec_adapter(mode="live")
        assert "PoC Phase 1" in str(exc_info.value)

    def test_invalid_mode_raises(self):
        """Invalid mode raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            create_fec_adapter(mode="invalid")
        assert "Unknown adapter mode" in str(exc_info.value)

    def test_no_api_key_required(self):
        """Mock adapter does not require API key."""
        # Should not raise
        adapter = create_fec_adapter(mode="mock", api_key=None)
        assert adapter.is_available()


# =============================================================================
# Candidate Search Tests
# =============================================================================


class TestCandidateSearch:
    """Tests for candidate search functionality."""

    @pytest.fixture
    def adapter(self) -> MockFECAdapter:
        return get_mock_adapter()

    def test_search_by_name(self, adapter: MockFECAdapter):
        """Can search candidates by name."""
        result = adapter.search_candidates(name="OCASIO")
        assert result.success
        assert len(result.candidates) >= 1
        assert any("OCASIO" in c.name for c in result.candidates)

    def test_search_by_name_case_insensitive(self, adapter: MockFECAdapter):
        """Name search is case-insensitive."""
        result1 = adapter.search_candidates(name="OCASIO")
        result2 = adapter.search_candidates(name="ocasio")
        result3 = adapter.search_candidates(name="Ocasio")
        assert result1.total_count == result2.total_count == result3.total_count

    def test_search_by_state(self, adapter: MockFECAdapter):
        """Can filter candidates by state."""
        result = adapter.search_candidates(state="NY")
        assert result.success
        assert all(c.state == "NY" for c in result.candidates)

    def test_search_by_office(self, adapter: MockFECAdapter):
        """Can filter candidates by office type."""
        result = adapter.search_candidates(office="P")
        assert result.success
        assert all(c.office == "P" for c in result.candidates)

    def test_search_by_party(self, adapter: MockFECAdapter):
        """Can filter candidates by party."""
        result = adapter.search_candidates(party="DEM")
        assert result.success
        assert all(c.party == "DEM" for c in result.candidates)

    def test_search_by_cycle(self, adapter: MockFECAdapter):
        """Can filter candidates by election cycle."""
        result = adapter.search_candidates(cycle=2024)
        assert result.success
        assert all(2024 in c.election_years for c in result.candidates)

    def test_search_combined_filters(self, adapter: MockFECAdapter):
        """Can combine multiple search filters."""
        result = adapter.search_candidates(
            name="OCASIO",
            state="NY",
            office="H",
            party="DEM",
        )
        assert result.success
        assert len(result.candidates) == 1
        assert result.candidates[0].candidate_id == "H8NY15148"

    def test_search_no_results(self, adapter: MockFECAdapter):
        """Search with no matches returns empty list."""
        result = adapter.search_candidates(name="NONEXISTENT_CANDIDATE_XYZ")
        assert result.success
        assert len(result.candidates) == 0
        assert result.total_count == 0

    def test_get_candidate_by_id(self, adapter: MockFECAdapter):
        """Can get specific candidate by FEC ID."""
        result = adapter.get_candidate("H8NY15148")
        assert result.success
        assert len(result.candidates) == 1
        assert result.candidates[0].candidate_id == "H8NY15148"
        assert result.candidates[0].name == "OCASIO-CORTEZ, ALEXANDRIA"

    def test_get_candidate_not_found(self, adapter: MockFECAdapter):
        """Get non-existent candidate returns NOT_FOUND error."""
        result = adapter.get_candidate("INVALID_ID")
        assert not result.success
        assert result.error is not None
        assert result.error.error_type == FECErrorType.NOT_FOUND


# =============================================================================
# Ambiguity Handling Tests
# =============================================================================


class TestAmbiguityHandling:
    """Tests for candidate disambiguation."""

    @pytest.fixture
    def adapter(self) -> MockFECAdapter:
        return get_mock_adapter()

    def test_ambiguous_name_flagged(self, adapter: MockFECAdapter):
        """Ambiguous name search sets disambiguation flags."""
        # Add a second candidate with similar name to fixture
        adapter._fixture_data["candidates"]["H0NY14001"] = CandidateRecord(
            candidate_id="H0NY14001",
            name="OCASIO, JOHN M",
            party="REP",
            state="NY",
            office="H",
            election_years=[2024],
        )

        result = adapter.search_candidates(name="OCASIO")
        assert result.success
        assert len(result.candidates) > 1
        assert result.is_ambiguous
        assert result.disambiguation_required
        assert result.disambiguation_message is not None

    def test_unique_name_not_ambiguous(self, adapter: MockFECAdapter):
        """Unique name search is not flagged as ambiguous."""
        result = adapter.search_candidates(name="SANDERS, BERNARD")
        assert result.success
        assert len(result.candidates) == 1
        assert not result.is_ambiguous
        assert not result.disambiguation_required


# =============================================================================
# Committee Search Tests
# =============================================================================


class TestCommitteeSearch:
    """Tests for committee search functionality."""

    @pytest.fixture
    def adapter(self) -> MockFECAdapter:
        return get_mock_adapter()

    def test_search_by_candidate_id(self, adapter: MockFECAdapter):
        """Can find committees associated with a candidate."""
        result = adapter.search_committees(candidate_id="H8NY15148")
        assert result.success
        assert len(result.committees) >= 1
        assert all("H8NY15148" in c.candidate_ids for c in result.committees)

    def test_search_by_committee_id(self, adapter: MockFECAdapter):
        """Can get specific committee by ID."""
        result = adapter.search_committees(committee_id="C00639591")
        assert result.success
        assert len(result.committees) == 1
        assert result.committees[0].name == "OCASIO-CORTEZ FOR CONGRESS"

    def test_search_by_name(self, adapter: MockFECAdapter):
        """Can search committees by name."""
        result = adapter.search_committees(name="OCASIO")
        assert result.success
        assert len(result.committees) >= 1


# =============================================================================
# Contribution Search Tests
# =============================================================================


class TestContributionSearch:
    """Tests for contribution search functionality."""

    @pytest.fixture
    def adapter(self) -> MockFECAdapter:
        return get_mock_adapter()

    def test_get_contributions_by_committee(self, adapter: MockFECAdapter):
        """Can get contributions for a committee."""
        result = adapter.get_contributions(committee_id="C00639591")
        assert result.success
        assert len(result.contributions) >= 1
        assert result.total_amount > 0

    def test_get_contributions_by_candidate(self, adapter: MockFECAdapter):
        """Can get contributions for a candidate."""
        result = adapter.get_contributions(candidate_id="H8NY15148")
        assert result.success
        assert len(result.contributions) >= 1

    def test_get_contributions_by_name(self, adapter: MockFECAdapter):
        """Can filter contributions by contributor name."""
        result = adapter.get_contributions(contributor_name="SMITH")
        assert result.success
        assert all(
            "SMITH" in c.contributor_name.upper()
            for c in result.contributions
        )

    def test_get_contributions_amount_range(self, adapter: MockFECAdapter):
        """Can filter contributions by amount range."""
        result = adapter.get_contributions(min_amount=200, max_amount=600)
        assert result.success
        assert all(
            200 <= c.contribution_receipt_amount <= 600
            for c in result.contributions
        )

    def test_get_contributions_limit(self, adapter: MockFECAdapter):
        """Contribution results respect limit parameter."""
        result = adapter.get_contributions(limit=2)
        assert result.success
        assert len(result.contributions) <= 2

    def test_contribution_has_confidence(self, adapter: MockFECAdapter):
        """Contributions have WSP 97 confidence level."""
        result = adapter.get_contributions(committee_id="C00639591")
        assert result.success
        for contrib in result.contributions:
            assert contrib.confidence == ConfidenceLevel.VERIFIED_FACT


# =============================================================================
# Funding Summary Tests
# =============================================================================


class TestFundingSummary:
    """Tests for funding summary functionality."""

    @pytest.fixture
    def adapter(self) -> MockFECAdapter:
        return get_mock_adapter()

    def test_get_funding_summary_by_candidate(self, adapter: MockFECAdapter):
        """Can get funding summary for a candidate."""
        result = adapter.get_funding_summary(candidate_id="H8NY15148")
        assert result.success
        assert result.summary is not None
        assert result.summary.total_raised > 0
        assert result.summary.entity_type == "candidate"

    def test_funding_summary_has_breakdown(self, adapter: MockFECAdapter):
        """Funding summary includes contribution breakdown."""
        result = adapter.get_funding_summary(candidate_id="H8NY15148")
        assert result.success
        summary = result.summary
        assert summary.contributions_by_type is not None
        assert len(summary.contributions_by_type) > 0

    def test_funding_summary_has_source(self, adapter: MockFECAdapter):
        """Funding summary includes source provenance."""
        result = adapter.get_funding_summary(candidate_id="H8NY15148")
        assert result.success
        assert result.summary.source is not None
        assert result.summary.source.source_type == "fec_filing"

    def test_funding_summary_not_found(self, adapter: MockFECAdapter):
        """Non-existent candidate returns NOT_FOUND error."""
        result = adapter.get_funding_summary(candidate_id="INVALID_ID")
        assert not result.success
        assert result.error is not None
        assert result.error.error_type == FECErrorType.NOT_FOUND


# =============================================================================
# Error Simulation Tests
# =============================================================================


class TestErrorSimulation:
    """Tests for error condition simulation."""

    def test_simulate_rate_limit(self):
        """Can simulate rate limit error."""
        adapter = MockFECAdapter(simulate_error=FECErrorType.RATE_LIMITED)

        result = adapter.search_candidates(name="TEST")
        assert not result.success
        assert result.error is not None
        assert result.error.error_type == FECErrorType.RATE_LIMITED
        assert result.error.retry_after_seconds is not None

    def test_simulate_unavailable(self):
        """Can simulate service unavailable error."""
        adapter = MockFECAdapter(simulate_error=FECErrorType.UNAVAILABLE)

        result = adapter.search_candidates(name="TEST")
        assert not result.success
        assert result.error.error_type == FECErrorType.UNAVAILABLE

        # Availability check should also reflect this
        assert not adapter.is_available()

    def test_simulate_network_error(self):
        """Can simulate network error."""
        adapter = MockFECAdapter(simulate_error=FECErrorType.NETWORK_ERROR)

        result = adapter.get_contributions(committee_id="TEST")
        assert not result.success
        assert result.error.error_type == FECErrorType.NETWORK_ERROR

    def test_error_affects_all_operations(self):
        """Simulated error affects all adapter operations."""
        adapter = MockFECAdapter(simulate_error=FECErrorType.UNAVAILABLE)

        assert not adapter.search_candidates(name="TEST").success
        assert not adapter.get_candidate("TEST").success
        assert not adapter.search_committees(name="TEST").success
        assert not adapter.get_contributions(committee_id="TEST").success
        assert not adapter.get_funding_summary(candidate_id="TEST").success


# =============================================================================
# Data Type Tests
# =============================================================================


class TestDataTypes:
    """Tests for data type structures."""

    def test_candidate_record_fields(self):
        """CandidateRecord has all required fields."""
        record = CandidateRecord(
            candidate_id="TEST",
            name="TEST CANDIDATE",
        )
        assert record.candidate_id == "TEST"
        assert record.name == "TEST CANDIDATE"
        assert record.confidence == ConfidenceLevel.VERIFIED_FACT

    def test_committee_record_fields(self):
        """CommitteeRecord has all required fields."""
        record = CommitteeRecord(
            committee_id="C00000001",
            name="TEST COMMITTEE",
        )
        assert record.committee_id == "C00000001"
        assert record.name == "TEST COMMITTEE"

    def test_contribution_record_fields(self):
        """ContributionRecord has all required fields."""
        record = ContributionRecord(
            contributor_name="JOHN DOE",
            contribution_receipt_amount=500.0,
        )
        assert record.contributor_name == "JOHN DOE"
        assert record.contribution_receipt_amount == 500.0
        assert record.confidence == ConfidenceLevel.VERIFIED_FACT

    def test_fec_source_auto_timestamp(self):
        """FECSource auto-generates accessed_at timestamp."""
        source = FECSource()
        assert source.accessed_at is not None
        assert "Z" in source.accessed_at  # UTC marker

    def test_fec_error_string_representation(self):
        """FECError has readable string representation."""
        error = FECError(
            error_type=FECErrorType.RATE_LIMITED,
            message="Too many requests",
            retry_after_seconds=60,
        )
        str_repr = str(error)
        assert "rate_limited" in str_repr
        assert "60" in str_repr


# =============================================================================
# WSP 97 Compliance Tests
# =============================================================================


class TestWSP97Compliance:
    """Tests for WSP 97 confidence labeling compliance."""

    @pytest.fixture
    def adapter(self) -> MockFECAdapter:
        return get_mock_adapter()

    def test_candidate_has_verified_fact_confidence(self, adapter: MockFECAdapter):
        """FEC candidate records have verified_fact confidence."""
        result = adapter.get_candidate("H8NY15148")
        assert result.success
        assert result.candidates[0].confidence == ConfidenceLevel.VERIFIED_FACT

    def test_contribution_has_verified_fact_confidence(self, adapter: MockFECAdapter):
        """FEC contribution records have verified_fact confidence."""
        result = adapter.get_contributions(committee_id="C00639591")
        assert result.success
        for contrib in result.contributions:
            assert contrib.confidence == ConfidenceLevel.VERIFIED_FACT

    def test_funding_summary_has_verified_fact_confidence(self, adapter: MockFECAdapter):
        """FEC funding summary has verified_fact confidence."""
        result = adapter.get_funding_summary(candidate_id="H8NY15148")
        assert result.success
        assert result.summary.confidence == ConfidenceLevel.VERIFIED_FACT

    def test_all_records_have_source(self, adapter: MockFECAdapter):
        """All records include source provenance."""
        candidate_result = adapter.get_candidate("H8NY15148")
        assert candidate_result.candidates[0].source is not None

        contrib_result = adapter.get_contributions(committee_id="C00639591")
        for contrib in contrib_result.contributions:
            assert contrib.source is not None

        summary_result = adapter.get_funding_summary(candidate_id="H8NY15148")
        assert summary_result.summary.source is not None


# =============================================================================
# Political Safety Tests
# =============================================================================


class TestPoliticalSafety:
    """Tests ensuring political safety boundaries are maintained."""

    @pytest.fixture
    def adapter(self) -> MockFECAdapter:
        return get_mock_adapter()

    def test_no_persuasion_fields(self, adapter: MockFECAdapter):
        """Records do not contain persuasion or recommendation fields."""
        result = adapter.get_candidate("H8NY15148")
        candidate = result.candidates[0]

        # Should not have any persuasion-related attributes
        assert not hasattr(candidate, "recommendation")
        assert not hasattr(candidate, "score")
        assert not hasattr(candidate, "ranking")
        assert not hasattr(candidate, "better_than")
        assert not hasattr(candidate, "worse_than")

    def test_no_targeting_fields(self, adapter: MockFECAdapter):
        """Records do not contain targeting or microtargeting fields."""
        result = adapter.get_candidate("H8NY15148")
        candidate = result.candidates[0]

        # Should not have targeting-related attributes
        assert not hasattr(candidate, "target_audience")
        assert not hasattr(candidate, "demographics")
        assert not hasattr(candidate, "user_profile_match")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
