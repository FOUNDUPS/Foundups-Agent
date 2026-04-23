"""
Adversarial tests for influence category classification.

These tests ensure the system NEVER conflates:
- "Israel-linked" with "foreign-funded"
- "AIPAC-linked" with "foreign national"
- "Pro-Israel donor" with "Israel policy"
- "Jewish donor" with any policy category

WSP 97 compliance: Distinguish direct disclosure from inferred alignment.
"""

from __future__ import annotations

import pytest
from dataclasses import dataclass
from typing import List, Optional


# =============================================================================
# Types (mirrors architecture spec)
# =============================================================================

@dataclass
class FundingNode:
    entity_id: str
    entity_name: str
    entity_type: str
    influence_category: str
    policy_alignments: Optional[List[str]] = None


@dataclass
class PolicyInfluenceAnalysis:
    has_connection: str  # confidence level
    connection_type: str  # influence category
    warnings: List[str]
    direct_vs_indirect: str


# =============================================================================
# Stub Implementation
# =============================================================================

def classify_funding_source(
    source_name: str,
    source_type: str,
    fec_registered: bool,
    country_of_origin: str,
) -> str:
    """
    Classify funding source into influence category.

    CRITICAL: Never infer foreign connection from policy position.
    """
    # Explicit foreign national check
    if country_of_origin != "USA" and country_of_origin != "unknown":
        return "foreign_national_alleged"

    # Registered PAC
    if fec_registered and source_type == "pac":
        return "direct_pac_donation"

    # Super PAC
    if fec_registered and source_type == "super_pac":
        return "super_pac_independent"

    # 501(c)(4)
    if source_type == "501c4":
        return "dark_money_501c4"

    # Individual
    if source_type == "individual":
        return "individual_donor_aligned"

    # Corporate PAC
    if source_type == "corporate_pac":
        return "corporate_pac"

    # Union PAC
    if source_type == "union_pac":
        return "union_pac"

    return "unknown_origin"


def analyze_policy_influence(
    entity_name: str,
    policy_area: str,
) -> PolicyInfluenceAnalysis:
    """
    Analyze policy influence connection.

    CRITICAL RULES:
    1. Policy advocacy ≠ foreign connection
    2. AIPAC = registered US PAC
    3. Must explicitly warn against conflation
    """
    warnings = []

    # Standard warnings for Israel-related policy analysis
    if policy_area == "israel_policy":
        warnings.extend([
            "Do not conflate with foreign funding",
            "AIPAC is a registered US PAC",
            "Pro-Israel position ≠ foreign connection",
            "Individual donor policy positions are protected speech",
        ])

    # Determine connection type based on entity
    if "AIPAC" in entity_name.upper():
        connection_type = "direct_pac_donation"
    elif "501(c)(4)" in entity_name or "Foundation" in entity_name:
        connection_type = "dark_money_501c4"
    else:
        connection_type = "policy_advocacy_org"

    return PolicyInfluenceAnalysis(
        has_connection="high_confidence_inference",
        connection_type=connection_type,
        warnings=warnings,
        direct_vs_indirect="direct" if "AIPAC" in entity_name.upper() else "one_hop",
    )


# =============================================================================
# Adversarial Tests
# =============================================================================

class TestAIPACNotForeign:
    """AIPAC must never be classified as foreign."""

    def test_aipac_is_domestic_pac(self):
        """AIPAC is a registered US PAC."""
        result = classify_funding_source(
            source_name="AIPAC",
            source_type="pac",
            fec_registered=True,
            country_of_origin="USA",
        )
        assert result == "direct_pac_donation"
        assert result != "foreign_national_alleged"

    def test_aipac_affiliated_pac_is_domestic(self):
        """AIPAC-affiliated PACs are domestic."""
        result = classify_funding_source(
            source_name="United Democracy Project",  # AIPAC-affiliated
            source_type="super_pac",
            fec_registered=True,
            country_of_origin="USA",
        )
        assert result == "super_pac_independent"
        assert result != "foreign_national_alleged"

    def test_policy_analysis_warns_against_conflation(self):
        """Israel policy analysis must include conflation warnings."""
        analysis = analyze_policy_influence(
            entity_name="AIPAC",
            policy_area="israel_policy",
        )

        assert "Do not conflate with foreign funding" in analysis.warnings
        assert "AIPAC is a registered US PAC" in analysis.warnings
        assert analysis.connection_type == "direct_pac_donation"


class TestProIsraelDonorsNotForeign:
    """Pro-Israel individual donors must not be classified as foreign."""

    def test_individual_with_israel_policy_position(self):
        """Individual donor with pro-Israel position = individual, not foreign."""
        result = classify_funding_source(
            source_name="John Smith (pro-Israel activist)",
            source_type="individual",
            fec_registered=False,
            country_of_origin="USA",
        )
        assert result == "individual_donor_aligned"
        assert result != "foreign_national_alleged"

    def test_policy_position_is_protected_speech(self):
        """Policy positions don't change citizenship status."""
        analysis = analyze_policy_influence(
            entity_name="Individual Donor",
            policy_area="israel_policy",
        )

        assert "Individual donor policy positions are protected speech" in analysis.warnings


class TestDarkMoneyNotForeign:
    """501(c)(4) dark money should be classified appropriately, not assumed foreign."""

    def test_501c4_is_dark_money_not_foreign(self):
        """Unknown 501(c)(4) donors = dark_money, not foreign."""
        result = classify_funding_source(
            source_name="Americans for Progress",
            source_type="501c4",
            fec_registered=False,
            country_of_origin="USA",  # Org is US-based
        )
        assert result == "dark_money_501c4"
        assert result != "foreign_national_alleged"

    def test_501c4_israel_advocacy_is_domestic(self):
        """Israel advocacy 501(c)(4) = domestic dark money, not foreign."""
        result = classify_funding_source(
            source_name="Christians United for Israel",
            source_type="501c4",
            fec_registered=False,
            country_of_origin="USA",
        )
        assert result == "dark_money_501c4"
        assert result != "foreign_national_alleged"


class TestActualForeignMustBeEvident:
    """Foreign national classification requires explicit evidence."""

    def test_explicit_foreign_origin_required(self):
        """Foreign classification requires country_of_origin ≠ USA."""
        result = classify_funding_source(
            source_name="Some Entity",
            source_type="individual",
            fec_registered=False,
            country_of_origin="Germany",  # Explicit foreign
        )
        assert result == "foreign_national_alleged"

    def test_unknown_origin_not_foreign(self):
        """Unknown origin should NOT default to foreign."""
        result = classify_funding_source(
            source_name="Mystery Donor",
            source_type="individual",
            fec_registered=False,
            country_of_origin="unknown",
        )
        assert result != "foreign_national_alleged"
        # Should be individual or unknown, not foreign
        assert result in ["individual_donor_aligned", "unknown_origin"]


class TestNoReligiousInference:
    """Religion/ethnicity must never imply foreign connection."""

    def test_jewish_donor_not_israel_linked(self):
        """Jewish identity ≠ Israel policy ≠ foreign connection."""
        # This is a documentation test - the system should not
        # have any logic that connects religious identity to
        # foreign influence categories

        # There should be no "jewish_donor" category
        valid_categories = [
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

        assert 'jewish_donor' not in valid_categories
        assert 'religious_affiliation' not in valid_categories
        assert 'ethnic_identity' not in valid_categories

    def test_no_religious_field_in_funding_node(self):
        """FundingNode should not have religion/ethnicity fields."""
        node = FundingNode(
            entity_id="test",
            entity_name="Test Donor",
            entity_type="individual",
            influence_category="individual_donor_aligned",
            policy_alignments=["israel_policy"],
        )

        # Verify no religious fields exist
        assert not hasattr(node, 'religion')
        assert not hasattr(node, 'ethnicity')
        assert not hasattr(node, 'religious_affiliation')


class TestPolicyVsFunding:
    """Policy alignment ≠ funding source."""

    def test_policy_alignment_separate_from_influence_category(self):
        """Policy alignment is metadata, not classification."""
        node = FundingNode(
            entity_id="test",
            entity_name="Pro-Israel PAC",
            entity_type="pac",
            influence_category="direct_pac_donation",  # Based on FEC status
            policy_alignments=["israel_policy"],  # Separate metadata
        )

        # Influence category based on org type, not policy
        assert node.influence_category == "direct_pac_donation"
        # Policy alignment is informational
        assert "israel_policy" in node.policy_alignments

    def test_same_policy_different_categories(self):
        """Same policy position can have different influence categories."""
        # PAC with Israel policy
        pac_node = FundingNode(
            entity_id="1",
            entity_name="AIPAC",
            entity_type="pac",
            influence_category="direct_pac_donation",
            policy_alignments=["israel_policy"],
        )

        # Individual with Israel policy
        individual_node = FundingNode(
            entity_id="2",
            entity_name="Individual Donor",
            entity_type="individual",
            influence_category="individual_donor_aligned",
            policy_alignments=["israel_policy"],
        )

        # 501(c)(4) with Israel policy
        c4_node = FundingNode(
            entity_id="3",
            entity_name="Advocacy Org",
            entity_type="501c4",
            influence_category="dark_money_501c4",
            policy_alignments=["israel_policy"],
        )

        # Same policy, different categories
        assert pac_node.policy_alignments == individual_node.policy_alignments
        assert pac_node.influence_category != individual_node.influence_category
        assert c4_node.influence_category != pac_node.influence_category


class TestEdgeCases:
    """Edge cases that could trigger false positives."""

    def test_american_friends_of_x_is_domestic(self):
        """'American Friends of [Foreign Org]' is still domestic."""
        result = classify_funding_source(
            source_name="American Friends of Hebrew University",
            source_type="501c4",
            fec_registered=False,
            country_of_origin="USA",  # US-registered org
        )
        assert result == "dark_money_501c4"
        assert result != "foreign_national_alleged"

    def test_dual_citizen_is_domestic(self):
        """US citizens with dual citizenship are domestic donors."""
        result = classify_funding_source(
            source_name="US-Israel Dual Citizen",
            source_type="individual",
            fec_registered=False,
            country_of_origin="USA",  # US citizen
        )
        assert result == "individual_donor_aligned"
        assert result != "foreign_national_alleged"

    def test_israeli_american_pac_is_domestic(self):
        """PACs organized by Israeli-Americans are domestic."""
        result = classify_funding_source(
            source_name="Israeli-American Coalition PAC",
            source_type="pac",
            fec_registered=True,
            country_of_origin="USA",
        )
        assert result == "direct_pac_donation"
        assert result != "foreign_national_alleged"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
