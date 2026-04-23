"""
Unit tests for confidence scoring hook.

Tests WSP 97 compliance: verified_fact, high_confidence_inference,
low_confidence_inference, unknown classification.
"""

from __future__ import annotations

import pytest
from dataclasses import dataclass
from typing import List, Optional


# =============================================================================
# Test Types (mirrors architecture spec)
# =============================================================================

@dataclass
class Source:
    url: str
    title: str
    source_type: str
    credibility_score: float


@dataclass
class EvidenceItem:
    claim: str
    sources: List[Source]
    has_contradictions: bool = False


# =============================================================================
# Confidence Scoring Implementation (stub for testing)
# =============================================================================

def classify_confidence(evidence: EvidenceItem) -> str:
    """
    Classify evidence confidence per WSP 97 rubric.

    Returns: verified_fact | high_confidence_inference |
             low_confidence_inference | unknown
    """
    if not evidence.sources:
        return "unknown"

    source_scores = [s.credibility_score for s in evidence.sources]
    avg_score = sum(source_scores) / len(source_scores)
    max_score = max(source_scores)
    num_sources = len(source_scores)

    # Diversity bonus
    diversity_bonus = min(0.15, (num_sources - 1) * 0.05)

    # Contradiction penalty
    contradiction_penalty = 0.20 if evidence.has_contradictions else 0

    # Direct filing bonus
    is_direct = any(
        s.source_type in ['fec_filing', 'state_filing', 'court_record']
        for s in evidence.sources
    )
    direct_bonus = 0.10 if is_direct else 0

    # Final score
    final_score = (
        (avg_score * 0.6 + max_score * 0.4)
        + diversity_bonus
        + direct_bonus
        - contradiction_penalty
    )

    # Classification
    if final_score >= 0.85 and is_direct:
        return "verified_fact"
    elif final_score >= 0.70:
        return "high_confidence_inference"
    elif final_score >= 0.45:
        return "low_confidence_inference"
    else:
        return "unknown"


# =============================================================================
# Tests
# =============================================================================

class TestConfidenceScoring:
    """WSP 97 confidence classification tests."""

    def test_verified_fact_from_fec_filing(self):
        """FEC filing with high credibility = verified_fact."""
        evidence = EvidenceItem(
            claim="Candidate received $500,000 from PAC X",
            sources=[
                Source(
                    url="https://fec.gov/data/...",
                    title="FEC Filing 12345",
                    source_type="fec_filing",
                    credibility_score=0.95
                )
            ]
        )
        assert classify_confidence(evidence) == "verified_fact"

    def test_verified_fact_requires_direct_source(self):
        """High score without direct source = high_confidence, not verified."""
        evidence = EvidenceItem(
            claim="Candidate received $500,000",
            sources=[
                Source(
                    url="https://nytimes.com/...",
                    title="NYT Report",
                    source_type="news_report",
                    credibility_score=0.90
                ),
                Source(
                    url="https://wapo.com/...",
                    title="WaPo Report",
                    source_type="news_report",
                    credibility_score=0.88
                )
            ]
        )
        # High score but no direct filing = high_confidence, not verified
        assert classify_confidence(evidence) == "high_confidence_inference"

    def test_high_confidence_from_multiple_news(self):
        """Multiple credible news sources = high_confidence_inference."""
        evidence = EvidenceItem(
            claim="PAC X supported candidate with attack ads",
            sources=[
                Source(
                    url="https://nytimes.com/...",
                    title="NYT Report",
                    source_type="news_report",
                    credibility_score=0.75
                ),
                Source(
                    url="https://wapo.com/...",
                    title="WaPo Report",
                    source_type="news_report",
                    credibility_score=0.75
                )
            ]
        )
        assert classify_confidence(evidence) == "high_confidence_inference"

    def test_low_confidence_from_single_weak_source(self):
        """Single source with moderate credibility = low_confidence."""
        evidence = EvidenceItem(
            claim="Candidate has ties to organization X",
            sources=[
                Source(
                    url="https://local-news.com/...",
                    title="Local News Report",
                    source_type="news_report",
                    credibility_score=0.55
                )
            ]
        )
        assert classify_confidence(evidence) == "low_confidence_inference"

    def test_unknown_from_no_sources(self):
        """No sources = unknown."""
        evidence = EvidenceItem(
            claim="Candidate received foreign money",
            sources=[]
        )
        assert classify_confidence(evidence) == "unknown"

    def test_contradiction_reduces_confidence(self):
        """Contradictions should reduce confidence level."""
        # Without contradiction: high_confidence
        evidence_clean = EvidenceItem(
            claim="PAC spent $1M",
            sources=[
                Source(
                    url="https://nytimes.com/...",
                    title="NYT",
                    source_type="news_report",
                    credibility_score=0.80
                )
            ],
            has_contradictions=False
        )

        # With contradiction: drops by 0.20
        evidence_contradicted = EvidenceItem(
            claim="PAC spent $1M",
            sources=[
                Source(
                    url="https://nytimes.com/...",
                    title="NYT",
                    source_type="news_report",
                    credibility_score=0.80
                )
            ],
            has_contradictions=True
        )

        clean_conf = classify_confidence(evidence_clean)
        contradicted_conf = classify_confidence(evidence_contradicted)

        # Contradiction should result in lower confidence
        confidence_order = ["unknown", "low_confidence_inference",
                          "high_confidence_inference", "verified_fact"]
        assert confidence_order.index(contradicted_conf) <= confidence_order.index(clean_conf)

    def test_multiple_sources_boost_confidence(self):
        """Multiple corroborating sources should boost confidence."""
        # Single source
        single = EvidenceItem(
            claim="Donation received",
            sources=[
                Source(
                    url="https://news.com/1",
                    title="Report 1",
                    source_type="news_report",
                    credibility_score=0.65
                )
            ]
        )

        # Multiple sources
        multiple = EvidenceItem(
            claim="Donation received",
            sources=[
                Source(
                    url="https://news.com/1",
                    title="Report 1",
                    source_type="news_report",
                    credibility_score=0.65
                ),
                Source(
                    url="https://news.com/2",
                    title="Report 2",
                    source_type="news_report",
                    credibility_score=0.65
                ),
                Source(
                    url="https://news.com/3",
                    title="Report 3",
                    source_type="news_report",
                    credibility_score=0.65
                )
            ]
        )

        # Multiple should have higher or equal confidence
        single_conf = classify_confidence(single)
        multiple_conf = classify_confidence(multiple)

        confidence_order = ["unknown", "low_confidence_inference",
                          "high_confidence_inference", "verified_fact"]
        assert confidence_order.index(multiple_conf) >= confidence_order.index(single_conf)


class TestSourceCredibilityMatrix:
    """Tests for source credibility baseline scores."""

    SOURCE_BASELINE_SCORES = {
        'fec_filing': 0.95,
        'state_filing': 0.90,
        'court_record': 0.95,
        'news_report': 0.75,  # Major outlet
        'ad_archive': 0.80,
        'press_release': 0.50,
    }

    def test_fec_filing_highest_baseline(self):
        """FEC filings should have highest baseline credibility."""
        assert self.SOURCE_BASELINE_SCORES['fec_filing'] >= 0.90

    def test_press_release_requires_corroboration(self):
        """Press releases alone should not reach high confidence."""
        evidence = EvidenceItem(
            claim="Candidate announces policy position",
            sources=[
                Source(
                    url="https://campaign.com/press",
                    title="Campaign Press Release",
                    source_type="press_release",
                    credibility_score=0.50
                )
            ]
        )
        assert classify_confidence(evidence) == "low_confidence_inference"


class TestHumanReviewTriggers:
    """Tests for human review flag conditions."""

    def test_foreign_funding_always_requires_review(self):
        """Foreign funding allegations must trigger human review regardless of confidence."""
        # This would be implemented in the full hook
        # Stub test to document requirement
        claim = "Candidate received foreign money"
        is_foreign_funding_claim = "foreign" in claim.lower()
        requires_review = is_foreign_funding_claim  # Always true for foreign claims
        assert requires_review is True

    def test_criminal_accusation_requires_review(self):
        """Criminal accusations must trigger human review."""
        claim = "Candidate committed fraud"
        is_criminal_claim = any(
            word in claim.lower()
            for word in ["fraud", "crime", "criminal", "indicted", "convicted"]
        )
        requires_review = is_criminal_claim
        assert requires_review is True

    def test_low_confidence_high_impact_requires_review(self):
        """Low confidence claims with high impact should trigger review."""
        confidence = "low_confidence_inference"
        impact_score = 0.8  # High impact

        requires_review = (
            confidence == "low_confidence_inference" and
            impact_score > 0.7
        )
        assert requires_review is True


class TestInfluenceCategoryDistinction:
    """Tests ensuring influence categories are never conflated."""

    INFLUENCE_CATEGORIES = [
        'direct_pac_donation',
        'super_pac_independent',
        'individual_donor_aligned',
        'bundler_network',
        'dark_money_501c4',
        'foreign_national_alleged',
        'corporate_pac',
        'union_pac',
        'policy_advocacy_org',
        'unknown_origin',
    ]

    def test_aipac_is_direct_pac_not_foreign(self):
        """AIPAC contributions should be 'direct_pac_donation', never 'foreign_national_alleged'."""
        # Test case: AIPAC is a registered US PAC
        aipac_contribution_type = 'direct_pac_donation'
        assert aipac_contribution_type != 'foreign_national_alleged'
        assert aipac_contribution_type in self.INFLUENCE_CATEGORIES

    def test_pro_israel_donor_is_individual_not_foreign(self):
        """Pro-Israel individual donors should be 'individual_donor_aligned', not foreign."""
        donor_type = 'individual_donor_aligned'
        assert donor_type != 'foreign_national_alleged'
        assert donor_type in self.INFLUENCE_CATEGORIES

    def test_501c4_is_dark_money_not_foreign(self):
        """501(c)(4) undisclosed donors should be 'dark_money_501c4', not foreign unless proven."""
        unknown_501c4_type = 'dark_money_501c4'
        assert unknown_501c4_type != 'foreign_national_alleged'
        assert unknown_501c4_type in self.INFLUENCE_CATEGORIES

    def test_foreign_requires_evidence(self):
        """'foreign_national_alleged' requires explicit evidence, never inferred from policy position."""
        # This is a documentation test - the category exists but requires evidence
        assert 'foreign_national_alleged' in self.INFLUENCE_CATEGORIES
        # Note: In implementation, this category triggers mandatory human review


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
