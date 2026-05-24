"""
Entity Resolution unit tests.

Tests for VOTE_POC_ENTITY_RESOLUTION_PHASE1.

Test Boundaries:
- NO_LIVE_API_REQUIRED_FOR_TESTS
- NO_API_KEY_REQUIRED_FOR_TESTS
- NO_NETWORK_CALLS_IN_TESTS
- NO_HALLUCINATED_CANDIDATE_IDS
- AMBIGUITY_PRESERVED_NOT_GUESSED
- NO_FUNDING_SUMMARY
- NO_CONTRIBUTION_AGGREGATION
- NO_PERSUASION_LANGUAGE

Uses mock FEC adapter from VOTE_POC_FEC_ADAPTER_PHASE1 (PR #707).
"""

from __future__ import annotations

import pytest

from modules.foundups.voteballots.src.fec_adapter import (
    CandidateRecord,
    FECErrorType,
    MockFECAdapter,
    get_mock_adapter,
)
from modules.foundups.voteballots.src.entity_resolution import (
    EntityResolutionRequest,
    EntityResolutionStatus,
    resolve_by_id,
    resolve_by_name,
    resolve_candidate_entity,
)


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def adapter() -> MockFECAdapter:
    """Get mock FEC adapter with default fixtures."""
    return get_mock_adapter()


@pytest.fixture
def adapter_with_common_names() -> MockFECAdapter:
    """Get mock FEC adapter with multiple candidates sharing common names."""
    adapter = get_mock_adapter()
    # Add candidates with common name "SMITH"
    adapter._fixture_data["candidates"]["H0NY01001"] = CandidateRecord(
        candidate_id="H0NY01001",
        name="SMITH, JOHN A",
        party="DEM",
        party_full="Democratic Party",
        state="NY",
        district="01",
        office="H",
        office_full="House",
        election_years=[2024],
    )
    adapter._fixture_data["candidates"]["H0CA05002"] = CandidateRecord(
        candidate_id="H0CA05002",
        name="SMITH, JOHN B",
        party="REP",
        party_full="Republican Party",
        state="CA",
        district="05",
        office="H",
        office_full="House",
        election_years=[2024],
    )
    adapter._fixture_data["candidates"]["S4TX00003"] = CandidateRecord(
        candidate_id="S4TX00003",
        name="SMITH, MARIA",
        party="DEM",
        party_full="Democratic Party",
        state="TX",
        office="S",
        office_full="Senate",
        election_years=[2024],
    )
    return adapter


# =============================================================================
# Request Validation Tests
# =============================================================================


class TestRequestValidation:
    """Tests for request validation."""

    def test_empty_query_returns_invalid(self, adapter: MockFECAdapter):
        """Empty query returns INVALID_QUERY status."""
        request = EntityResolutionRequest(query="")
        result = resolve_candidate_entity(request, adapter)

        assert result.status == EntityResolutionStatus.INVALID_QUERY
        assert result.has_error
        assert result.error_message is not None
        msg = result.error_message.lower()
        assert "blank" in msg or "empty" in msg

    def test_blank_query_returns_invalid(self, adapter: MockFECAdapter):
        """Blank (whitespace-only) query returns INVALID_QUERY status."""
        request = EntityResolutionRequest(query="   ")
        result = resolve_candidate_entity(request, adapter)

        assert result.status == EntityResolutionStatus.INVALID_QUERY
        assert result.has_error
        assert result.error_message is not None
        msg = result.error_message.lower()
        assert "blank" in msg or "empty" in msg

    def test_invalid_state_hint_returns_invalid(self, adapter: MockFECAdapter):
        """Invalid state hint (not 2 letters) returns INVALID_QUERY."""
        request = EntityResolutionRequest(query="Test", state_hint="NEW YORK")
        result = resolve_candidate_entity(request, adapter)

        assert result.status == EntityResolutionStatus.INVALID_QUERY
        assert result.error_message is not None
        assert "state hint" in result.error_message.lower()

    def test_invalid_office_hint_returns_invalid(self, adapter: MockFECAdapter):
        """Invalid office hint returns INVALID_QUERY."""
        request = EntityResolutionRequest(query="Test", office_hint="X")
        result = resolve_candidate_entity(request, adapter)

        assert result.status == EntityResolutionStatus.INVALID_QUERY
        assert result.error_message is not None
        assert "office hint" in result.error_message.lower()

    def test_invalid_cycle_hint_returns_invalid(self, adapter: MockFECAdapter):
        """Invalid cycle year returns INVALID_QUERY."""
        request = EntityResolutionRequest(query="Test", cycle_hint=1800)
        result = resolve_candidate_entity(request, adapter)

        assert result.status == EntityResolutionStatus.INVALID_QUERY
        assert result.error_message is not None
        assert "cycle hint" in result.error_message.lower()

    def test_valid_hints_accepted(self, adapter: MockFECAdapter):
        """Valid hints are accepted without error."""
        request = EntityResolutionRequest(
            query="Test",
            state_hint="ny",  # lowercase should be normalized
            office_hint="h",  # lowercase should be normalized
            party_hint="dem",  # lowercase should be normalized
            cycle_hint=2024,
        )
        result = resolve_candidate_entity(request, adapter)

        # Should not be INVALID_QUERY (may be NO_MATCH)
        assert result.status != EntityResolutionStatus.INVALID_QUERY


# =============================================================================
# Exact Match Tests
# =============================================================================


class TestExactMatch:
    """Tests for exact single candidate resolution."""

    def test_exact_name_resolves_to_single_candidate(self, adapter: MockFECAdapter):
        """Exact candidate name resolves to EXACT_ONE_MATCH."""
        request = EntityResolutionRequest(query="OCASIO-CORTEZ, ALEXANDRIA")
        result = resolve_candidate_entity(request, adapter)

        assert result.status == EntityResolutionStatus.EXACT_ONE_MATCH
        assert result.is_resolved
        assert len(result.candidates) == 1
        assert result.candidates[0].candidate_id == "H8NY15148"
        assert result.confidence > 0.5

    def test_partial_name_with_state_hint_resolves(self, adapter: MockFECAdapter):
        """Partial name with state hint resolves correctly."""
        request = EntityResolutionRequest(query="OCASIO", state_hint="NY")
        result = resolve_candidate_entity(request, adapter)

        assert result.status == EntityResolutionStatus.EXACT_ONE_MATCH
        assert result.candidates[0].candidate_id == "H8NY15148"

    def test_name_with_office_hint_resolves(self, adapter: MockFECAdapter):
        """Name with office hint resolves correctly."""
        request = EntityResolutionRequest(query="SANDERS", office_hint="S")
        result = resolve_candidate_entity(request, adapter)

        assert result.status == EntityResolutionStatus.EXACT_ONE_MATCH
        assert result.candidates[0].candidate_id == "S4VT00033"

    def test_name_case_insensitive(self, adapter: MockFECAdapter):
        """Name matching is case-insensitive."""
        request1 = EntityResolutionRequest(query="biden")
        request2 = EntityResolutionRequest(query="BIDEN")
        request3 = EntityResolutionRequest(query="Biden")

        result1 = resolve_candidate_entity(request1, adapter)
        result2 = resolve_candidate_entity(request2, adapter)
        result3 = resolve_candidate_entity(request3, adapter)

        assert result1.status == result2.status == result3.status
        assert len(result1.candidates) == len(result2.candidates) == len(result3.candidates)

    def test_match_reason_included(self, adapter: MockFECAdapter):
        """Resolved candidates include match reason."""
        request = EntityResolutionRequest(query="SANDERS", state_hint="VT")
        result = resolve_candidate_entity(request, adapter)

        assert result.status == EntityResolutionStatus.EXACT_ONE_MATCH
        candidate = result.candidates[0]
        assert candidate.match_reason is not None
        assert len(candidate.match_reason) > 0


# =============================================================================
# Disambiguation Tests
# =============================================================================


class TestDisambiguation:
    """Tests for multiple candidate disambiguation."""

    def test_name_plus_state_disambiguates(
        self, adapter_with_common_names: MockFECAdapter
    ):
        """Name with state hint disambiguates common names."""
        # Without state hint - should return multiple
        request_no_hint = EntityResolutionRequest(query="SMITH, JOHN")
        result_no_hint = resolve_candidate_entity(request_no_hint, adapter_with_common_names)

        assert result_no_hint.status == EntityResolutionStatus.MULTIPLE_MATCHES
        assert len(result_no_hint.candidates) >= 2

        # With state hint - should resolve to one
        request_with_hint = EntityResolutionRequest(query="SMITH, JOHN", state_hint="NY")
        result_with_hint = resolve_candidate_entity(
            request_with_hint, adapter_with_common_names
        )

        assert result_with_hint.status == EntityResolutionStatus.EXACT_ONE_MATCH
        assert result_with_hint.candidates[0].candidate.state == "NY"

    def test_name_plus_office_disambiguates(
        self, adapter_with_common_names: MockFECAdapter
    ):
        """Name with office hint disambiguates."""
        # Add a Senate candidate with same name
        adapter_with_common_names._fixture_data["candidates"]["S0NY00004"] = CandidateRecord(
            candidate_id="S0NY00004",
            name="SMITH, JOHN A",
            party="DEM",
            state="NY",
            office="S",
            office_full="Senate",
            election_years=[2024],
        )

        # Query with office hint should resolve correctly
        request_house = EntityResolutionRequest(
            query="SMITH, JOHN A", state_hint="NY", office_hint="H"
        )
        result_house = resolve_candidate_entity(request_house, adapter_with_common_names)

        assert result_house.status == EntityResolutionStatus.EXACT_ONE_MATCH
        assert result_house.candidates[0].candidate.office == "H"

    def test_ambiguous_common_name_returns_multiple(
        self, adapter_with_common_names: MockFECAdapter
    ):
        """Ambiguous common name returns MULTIPLE_MATCHES with disambiguation message."""
        request = EntityResolutionRequest(query="SMITH")
        result = resolve_candidate_entity(request, adapter_with_common_names)

        assert result.status == EntityResolutionStatus.MULTIPLE_MATCHES
        assert result.requires_disambiguation
        assert len(result.candidates) >= 3
        assert result.disambiguation_message is not None
        assert "SMITH" in result.disambiguation_message

    def test_disambiguation_message_suggests_hints(
        self, adapter_with_common_names: MockFECAdapter
    ):
        """Disambiguation message suggests adding hints."""
        request = EntityResolutionRequest(query="SMITH")
        result = resolve_candidate_entity(request, adapter_with_common_names)

        assert result.disambiguation_message is not None
        # Should suggest state, office, or party
        message_lower = result.disambiguation_message.lower()
        assert "state" in message_lower or "office" in message_lower or "party" in message_lower

    def test_disambiguation_lists_candidates(
        self, adapter_with_common_names: MockFECAdapter
    ):
        """Disambiguation message lists matching candidates."""
        request = EntityResolutionRequest(query="SMITH")
        result = resolve_candidate_entity(request, adapter_with_common_names)

        assert result.disambiguation_message is not None
        # Should list candidate names
        assert "SMITH, JOHN A" in result.disambiguation_message or "SMITH" in result.disambiguation_message


# =============================================================================
# No Match Tests
# =============================================================================


class TestNoMatch:
    """Tests for no match scenarios."""

    def test_nonexistent_name_returns_no_match(self, adapter: MockFECAdapter):
        """Nonexistent candidate name returns NO_MATCH, not hallucinated candidate."""
        request = EntityResolutionRequest(query="NONEXISTENT_CANDIDATE_XYZ123")
        result = resolve_candidate_entity(request, adapter)

        assert result.status == EntityResolutionStatus.NO_MATCH
        assert len(result.candidates) == 0
        assert not result.is_resolved
        assert not result.requires_disambiguation
        assert result.confidence == 1.0  # High confidence in the "no match" result

    def test_wrong_state_returns_no_match(self, adapter: MockFECAdapter):
        """Correct name but wrong state returns NO_MATCH."""
        request = EntityResolutionRequest(query="OCASIO-CORTEZ", state_hint="CA")
        result = resolve_candidate_entity(request, adapter)

        assert result.status == EntityResolutionStatus.NO_MATCH
        assert len(result.candidates) == 0

    def test_no_hallucinated_candidate_ids(self, adapter: MockFECAdapter):
        """No hallucinated candidate IDs are returned."""
        request = EntityResolutionRequest(query="FAKE CANDIDATE")
        result = resolve_candidate_entity(request, adapter)

        # Should return NO_MATCH, not a fabricated candidate
        assert result.status == EntityResolutionStatus.NO_MATCH
        assert len(result.candidates) == 0
        # No candidate IDs should be present
        for candidate in result.candidates:
            # This loop should not execute if candidates is empty
            assert candidate.candidate_id is not None


# =============================================================================
# Adapter Error Tests
# =============================================================================


class TestAdapterError:
    """Tests for adapter error handling."""

    def test_adapter_error_propagates_as_adapter_error(self):
        """Adapter error propagates as ADAPTER_ERROR status."""
        adapter = MockFECAdapter(simulate_error=FECErrorType.UNAVAILABLE)

        request = EntityResolutionRequest(query="TEST")
        result = resolve_candidate_entity(request, adapter)

        assert result.status == EntityResolutionStatus.ADAPTER_ERROR
        assert result.has_error
        assert result.error_message is not None
        assert "unavailable" in result.error_message.lower()

    def test_network_error_handled(self):
        """Network error is handled gracefully."""
        adapter = MockFECAdapter(simulate_error=FECErrorType.NETWORK_ERROR)

        request = EntityResolutionRequest(query="TEST")
        result = resolve_candidate_entity(request, adapter)

        assert result.status == EntityResolutionStatus.ADAPTER_ERROR
        assert result.has_error

    def test_rate_limited_error_handled(self):
        """Rate limited error is handled gracefully."""
        adapter = MockFECAdapter(simulate_error=FECErrorType.RATE_LIMITED)

        request = EntityResolutionRequest(query="TEST")
        result = resolve_candidate_entity(request, adapter)

        assert result.status == EntityResolutionStatus.ADAPTER_ERROR
        assert result.has_error


# =============================================================================
# Confidence and Ordering Tests
# =============================================================================


class TestConfidenceAndOrdering:
    """Tests for confidence scoring and result ordering."""

    def test_confidence_bounded_zero_to_one(self, adapter: MockFECAdapter):
        """Confidence is bounded between 0.0 and 1.0."""
        request = EntityResolutionRequest(query="SANDERS")
        result = resolve_candidate_entity(request, adapter)

        assert 0.0 <= result.confidence <= 1.0
        for candidate in result.candidates:
            assert 0.0 <= candidate.match_score <= 1.0

    def test_confidence_deterministic(self, adapter: MockFECAdapter):
        """Same request produces same confidence."""
        request = EntityResolutionRequest(query="OCASIO", state_hint="NY")

        result1 = resolve_candidate_entity(request, adapter)
        result2 = resolve_candidate_entity(request, adapter)

        assert result1.confidence == result2.confidence
        assert result1.candidates[0].match_score == result2.candidates[0].match_score

    def test_result_ordering_deterministic(
        self, adapter_with_common_names: MockFECAdapter
    ):
        """Result ordering is deterministic for reproducibility."""
        request = EntityResolutionRequest(query="SMITH")

        result1 = resolve_candidate_entity(request, adapter_with_common_names)
        result2 = resolve_candidate_entity(request, adapter_with_common_names)

        # Order should be identical
        assert len(result1.candidates) == len(result2.candidates)
        for c1, c2 in zip(result1.candidates, result2.candidates):
            assert c1.candidate_id == c2.candidate_id

    def test_higher_score_ranked_first(
        self, adapter_with_common_names: MockFECAdapter
    ):
        """Candidates with higher match scores are ranked first."""
        request = EntityResolutionRequest(query="SMITH, JOHN", state_hint="NY")
        result = resolve_candidate_entity(request, adapter_with_common_names)

        # The NY candidate should be ranked higher due to state hint match
        if len(result.candidates) > 1:
            scores = [c.match_score for c in result.candidates]
            assert scores == sorted(scores, reverse=True)


# =============================================================================
# Convenience Function Tests
# =============================================================================


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_resolve_by_name(self, adapter: MockFECAdapter):
        """resolve_by_name convenience function works."""
        result = resolve_by_name("SANDERS", adapter, state="VT")

        assert result.status == EntityResolutionStatus.EXACT_ONE_MATCH
        assert result.candidates[0].candidate_id == "S4VT00033"

    def test_resolve_by_id_exact(self, adapter: MockFECAdapter):
        """resolve_by_id returns exact match for valid ID."""
        result = resolve_by_id("H8NY15148", adapter)

        assert result.status == EntityResolutionStatus.EXACT_ONE_MATCH
        assert result.candidates[0].candidate_id == "H8NY15148"
        assert result.confidence == 1.0

    def test_resolve_by_id_not_found(self, adapter: MockFECAdapter):
        """resolve_by_id returns NO_MATCH for invalid ID."""
        result = resolve_by_id("INVALID_ID", adapter)

        assert result.status == EntityResolutionStatus.NO_MATCH
        assert len(result.candidates) == 0

    def test_resolve_by_id_empty(self, adapter: MockFECAdapter):
        """resolve_by_id returns INVALID_QUERY for empty ID."""
        result = resolve_by_id("", adapter)

        assert result.status == EntityResolutionStatus.INVALID_QUERY
        assert result.has_error


# =============================================================================
# Political Safety Tests
# =============================================================================


class TestPoliticalSafety:
    """Tests ensuring political safety boundaries are maintained."""

    def test_no_persuasion_language_in_disambiguation(
        self, adapter_with_common_names: MockFECAdapter
    ):
        """Disambiguation message contains no persuasion language."""
        request = EntityResolutionRequest(query="SMITH")
        result = resolve_candidate_entity(request, adapter_with_common_names)

        if result.disambiguation_message:
            message_lower = result.disambiguation_message.lower()
            # Should not contain persuasion language
            assert "recommend" not in message_lower
            assert "better" not in message_lower
            assert "worse" not in message_lower
            assert "should vote" not in message_lower
            assert "support" not in message_lower
            assert "oppose" not in message_lower

    def test_no_recommendation_fields(self, adapter: MockFECAdapter):
        """Resolution result has no recommendation fields."""
        request = EntityResolutionRequest(query="SANDERS")
        result = resolve_candidate_entity(request, adapter)

        assert not hasattr(result, "recommendation")
        assert not hasattr(result, "ranking")
        assert not hasattr(result, "score")  # Different from match_score

        for candidate in result.candidates:
            assert not hasattr(candidate, "recommendation")
            assert not hasattr(candidate, "partisan_score")


# =============================================================================
# No Network / No Live API Tests
# =============================================================================


class TestNoNetworkCalls:
    """Tests verifying no network calls are made."""

    def test_mock_adapter_requires_no_api_key(self, adapter: MockFECAdapter):
        """Mock adapter works without API key."""
        # This implicitly tests no network calls since mock adapter
        # doesn't make any network calls
        assert adapter.is_available()

        request = EntityResolutionRequest(query="SANDERS")
        result = resolve_candidate_entity(request, adapter)

        # Should succeed without any API key
        assert result.status != EntityResolutionStatus.ADAPTER_ERROR

    def test_all_data_from_fixtures(self, adapter: MockFECAdapter):
        """All returned data comes from fixtures, not live API."""
        request = EntityResolutionRequest(query="OCASIO")
        result = resolve_candidate_entity(request, adapter)

        # Verify candidate is from known fixtures
        if result.candidates:
            candidate = result.candidates[0].candidate
            assert candidate.candidate_id in ["H8NY15148", "P80001571", "S4VT00033"]


# =============================================================================
# Request/Result Type Tests
# =============================================================================


class TestTypes:
    """Tests for request and result type structures."""

    def test_request_normalizes_hints(self):
        """Request normalizes hints to uppercase."""
        request = EntityResolutionRequest(
            query="test",
            state_hint="ny",
            office_hint="h",
            party_hint="dem",
        )

        assert request.state_hint == "NY"
        assert request.office_hint == "H"
        assert request.party_hint == "DEM"

    def test_result_properties(self, adapter: MockFECAdapter):
        """Result has correct properties."""
        request = EntityResolutionRequest(query="SANDERS")
        result = resolve_candidate_entity(request, adapter)

        # Test properties work correctly
        assert isinstance(result.is_resolved, bool)
        assert isinstance(result.requires_disambiguation, bool)
        assert isinstance(result.has_error, bool)

    def test_candidate_convenience_accessors(self, adapter: MockFECAdapter):
        """EntityResolutionCandidate has convenience accessors."""
        request = EntityResolutionRequest(query="SANDERS")
        result = resolve_candidate_entity(request, adapter)

        if result.candidates:
            candidate = result.candidates[0]
            assert candidate.candidate_id == candidate.candidate.candidate_id
            assert candidate.name == candidate.candidate.name

    def test_original_request_preserved(self, adapter: MockFECAdapter):
        """Result preserves original request."""
        request = EntityResolutionRequest(
            query="SANDERS",
            state_hint="VT",
        )
        result = resolve_candidate_entity(request, adapter)

        assert result.request is not None
        assert result.request.query == "SANDERS"
        assert result.request.state_hint == "VT"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
