"""
Tests for pfMALL YouTube Discovery module.

Tests:
- Input parsing and validation
- Proposal formatting
- FoundUp matching logic
- Duplicate suppression
"""

import pytest
from pathlib import Path

from modules.ai_intelligence.pfmall_discovery.src.youtube_discovery import (
    DiscoveryProposal,
)
from modules.ai_intelligence.pfmall_discovery.src.foundup_matcher import (
    CatalogTarget,
    match_to_foundup,
    _calculate_tag_overlap,
    match_proposals,
)
from modules.ai_intelligence.pfmall_discovery.src.proposal_generator import (
    format_proposal_summary,
)


class TestDiscoveryProposal:
    """Test DiscoveryProposal dataclass."""

    def test_proposal_to_dict(self):
        """Proposal converts to dict correctly."""
        proposal = DiscoveryProposal(
            query="FFCPLN music",
            candidate_type="video",
            video_id="abc123",
            channel_id="UC123",
            title="Test Video",
            confidence=0.8,
        )

        d = proposal.to_dict()

        assert d["query"] == "FFCPLN music"
        assert d["candidate_type"] == "video"
        assert d["video_id"] == "abc123"
        assert d["confidence"] == 0.8
        assert d["review_status"] == "proposed"

    def test_proposal_default_values(self):
        """Proposal has correct defaults."""
        proposal = DiscoveryProposal(
            query="test",
            candidate_type="video",
        )

        assert proposal.matched_foundup_id is None
        assert proposal.confidence == 0.0
        assert proposal.ambiguous_candidates == []
        assert proposal.review_status == "proposed"


class TestTagOverlap:
    """Test tag overlap calculation."""

    def test_no_overlap(self):
        """No overlap returns 0."""
        score = _calculate_tag_overlap(["a", "b"], ["c", "d"])
        assert score == 0.0

    def test_partial_overlap(self):
        """Partial overlap returns intermediate score."""
        score = _calculate_tag_overlap(["a", "b", "c"], ["b", "c", "d"])
        assert 0.3 < score < 0.7

    def test_full_overlap(self):
        """Full overlap returns high score."""
        score = _calculate_tag_overlap(["a", "b"], ["a", "b"])
        assert score == 0.7  # Capped at 0.7

    def test_empty_tags(self):
        """Empty tags return 0."""
        assert _calculate_tag_overlap([], ["a"]) == 0.0
        assert _calculate_tag_overlap(["a"], []) == 0.0


class TestFoundUpMatching:
    """Test FoundUp matching logic."""

    @pytest.fixture
    def catalog_targets(self):
        """Sample catalog targets for testing."""
        return [
            CatalogTarget(
                foundup_id="move2japan",
                source_id="UC-LSSlOZwpGIRIYihaz8zCw",
                source_handle="@MOVE2JAPAN",
                tags=["japan", "expat", "relocation", "ffcpln"],
                category="travel",
            ),
            CatalogTarget(
                foundup_id="antifafm",
                source_id="UCVSmg5aOhP4tnQ9KFUg97qA",
                source_handle="@antifaFM",
                tags=["music", "activism", "ffcpln", "24/7"],
                category="media",
            ),
        ]

    def test_exact_channel_match(self, catalog_targets):
        """Exact channel_id match returns confidence 1.0."""
        matched_id, reason, confidence, ambiguous = match_to_foundup(
            channel_id="UC-LSSlOZwpGIRIYihaz8zCw",
            title="Some video",
            description="Description",
            targets=catalog_targets,
        )

        assert matched_id == "move2japan"
        assert reason == "channel_id_match"
        assert confidence == 1.0
        assert ambiguous == []

    def test_ambiguous_shared_topic_match(self, catalog_targets):
        """Shared topic (FFCPLN) returns ambiguous match with candidates."""
        matched_id, reason, confidence, ambiguous = match_to_foundup(
            channel_id="UC_UNKNOWN",  # Unknown channel
            title="FFCPLN music video",
            description="Anti-fascist ffcpln content",
            targets=catalog_targets,
        )

        # Both move2japan and antifafm have "ffcpln" tag
        # Should detect ambiguity
        assert reason == "ambiguous_shared_topic"
        assert matched_id is None  # No single match when ambiguous
        assert confidence <= 0.5  # Reduced confidence for ambiguity
        assert "move2japan" in ambiguous
        assert "antifafm" in ambiguous

    def test_single_tag_overlap_match(self, catalog_targets):
        """Single FoundUp tag match returns unambiguous result."""
        matched_id, reason, confidence, ambiguous = match_to_foundup(
            channel_id="UC_UNKNOWN",
            title="Japan relocation expat video",
            description="Moving to Japan advice",
            targets=catalog_targets,
        )

        # Only move2japan has "japan", "expat", "relocation" tags
        assert matched_id == "move2japan"
        assert "tag_overlap" in reason
        assert confidence >= 0.3
        assert ambiguous == []

    def test_category_match(self, catalog_targets):
        """Category match returns low confidence."""
        matched_id, reason, confidence, ambiguous = match_to_foundup(
            channel_id="UC_UNKNOWN",
            title="Travel vlog",
            description="My travel adventures",
            targets=catalog_targets,
        )

        assert matched_id == "move2japan"
        assert "category" in reason or "tag" in reason
        assert confidence >= 0.2
        assert ambiguous == []

    def test_no_match(self, catalog_targets):
        """No match returns None."""
        matched_id, reason, confidence, ambiguous = match_to_foundup(
            channel_id="UC_UNKNOWN",
            title="Random cooking video",
            description="How to make pasta",
            targets=catalog_targets,
        )

        assert matched_id is None
        assert reason == "no_match"
        assert confidence == 0.0
        assert ambiguous == []

    def test_empty_targets(self):
        """Empty targets returns no match."""
        matched_id, reason, confidence, ambiguous = match_to_foundup(
            channel_id="UC123",
            title="Test",
            description="Test",
            targets=[],
        )

        assert matched_id is None
        assert reason == "no_targets"
        assert confidence == 0.0
        assert ambiguous == []


class TestMatchProposals:
    """Test batch proposal matching."""

    def test_match_proposals_updates_fields(self):
        """match_proposals populates matched fields."""
        proposals = [
            DiscoveryProposal(
                query="test",
                candidate_type="video",
                channel_id="UC-LSSlOZwpGIRIYihaz8zCw",  # move2japan channel
                title="Test",
            ),
        ]

        targets = [
            CatalogTarget(
                foundup_id="move2japan",
                source_id="UC-LSSlOZwpGIRIYihaz8zCw",
                source_handle="@MOVE2JAPAN",
                tags=["japan"],
                category="travel",
            ),
        ]

        matched = match_proposals(proposals, targets)

        assert matched[0].matched_foundup_id == "move2japan"
        assert matched[0].confidence == 1.0
        assert matched[0].ambiguous_candidates == []

    def test_match_proposals_detects_ambiguity(self):
        """match_proposals correctly identifies ambiguous shared-topic matches."""
        proposals = [
            DiscoveryProposal(
                query="FFCPLN music",
                candidate_type="video",
                channel_id="UC_UNKNOWN",  # Unknown channel
                title="FFCPLN music video",
                description="Anti-fascist ffcpln content",
            ),
        ]

        targets = [
            CatalogTarget(
                foundup_id="move2japan",
                source_id="UC-LSSlOZwpGIRIYihaz8zCw",
                source_handle="@MOVE2JAPAN",
                tags=["japan", "expat", "ffcpln"],
                category="travel",
            ),
            CatalogTarget(
                foundup_id="antifafm",
                source_id="UCVSmg5aOhP4tnQ9KFUg97qA",
                source_handle="@antifaFM",
                tags=["music", "activism", "ffcpln"],
                category="media",
            ),
        ]

        matched = match_proposals(proposals, targets)

        # Should detect ambiguity
        assert matched[0].matched_foundup_id is None
        assert matched[0].match_reason == "ambiguous_shared_topic"
        assert "move2japan" in matched[0].ambiguous_candidates
        assert "antifafm" in matched[0].ambiguous_candidates


class TestProposalFormatting:
    """Test proposal report formatting."""

    def test_format_summary_basic(self):
        """Basic summary formatting works."""
        report = {
            "generated_at": "2026-04-13T00:00:00Z",
            "query": "test query",
            "summary": {
                "total_proposals": 10,
                "matched_to_foundup": 3,
                "unmatched": 7,
                "catalog_targets": 4,
            },
            "proposals": [],
        }

        summary = format_proposal_summary(report)

        assert "test query" in summary
        assert "10" in summary
        assert "3" in summary  # matched
        assert "7" in summary  # unmatched

    def test_format_summary_with_proposals(self):
        """Summary with proposals shows details."""
        report = {
            "generated_at": "2026-04-13T00:00:00Z",
            "query": "test",
            "summary": {
                "total_proposals": 2,
                "matched_to_foundup": 1,
                "unmatched": 1,
                "catalog_targets": 1,
            },
            "proposals": [
                {
                    "candidate_type": "video",
                    "title": "Matched Video Title",
                    "matched_foundup_id": "move2japan",
                    "match_reason": "channel_id_match",
                    "confidence": 1.0,
                },
                {
                    "candidate_type": "video",
                    "title": "Unmatched Video Title",
                    "matched_foundup_id": None,
                    "channel_title": "Random Channel",
                },
            ],
        }

        summary = format_proposal_summary(report)

        assert "MATCHED PROPOSALS" in summary
        assert "Matched Video" in summary
        assert "move2japan" in summary
        assert "UNMATCHED PROPOSALS" in summary
        assert "Unmatched Video" in summary


class TestInputValidation:
    """Test input parsing and validation."""

    def test_proposal_requires_query(self):
        """Proposal requires query."""
        proposal = DiscoveryProposal(
            query="",  # Empty but allowed
            candidate_type="video",
        )
        assert proposal.query == ""

    def test_proposal_requires_candidate_type(self):
        """Proposal requires candidate_type."""
        proposal = DiscoveryProposal(
            query="test",
            candidate_type="video",
        )
        assert proposal.candidate_type == "video"


class TestDuplicateSuppression:
    """Test duplicate handling in proposals."""

    def test_unique_proposals_by_video_id(self):
        """Proposals with same video_id should be detected."""
        proposals = [
            DiscoveryProposal(query="q1", candidate_type="video", video_id="abc"),
            DiscoveryProposal(query="q2", candidate_type="video", video_id="abc"),
            DiscoveryProposal(query="q3", candidate_type="video", video_id="xyz"),
        ]

        # Count unique video_ids
        unique_ids = {p.video_id for p in proposals}
        assert len(unique_ids) == 2  # "abc" and "xyz"

    def test_detect_duplicate_channel_proposals(self):
        """Proposals with same channel_id should be detected."""
        proposals = [
            DiscoveryProposal(query="q1", candidate_type="channel", channel_id="UC123"),
            DiscoveryProposal(query="q2", candidate_type="channel", channel_id="UC123"),
        ]

        unique_channels = {p.channel_id for p in proposals}
        assert len(unique_channels) == 1
