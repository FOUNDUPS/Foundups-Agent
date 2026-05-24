"""
Confidence Scoring for VoteBallots FoundUp.

Applies WSP 97 confidence labels to structured funding summaries, separating:
- VERIFIED_FACT: Direct FEC filing or source reference present
- HIGH_CONFIDENCE_INFERENCE: Multiple corroborating official/public sources
- LOW_CONFIDENCE_INFERENCE: Single weak/non-official source
- UNKNOWN: Missing source or trail termination

Design Principles:
- Consumes FundingSummaryResult from funding_summary module
- Preserves original source references and trail termination markers
- Applies deterministic confidence rules based on source presence/type
- Triggers human review for high-risk claims
- No quick answer generation (structured data only)

WSP 97 Compliance:
- Explicit confidence labels on every claim
- Source references preserved for provenance
- Trail termination markers propagated
- Human review triggers for dangerous edge cases

Political Safety Boundaries:
- NO_TARGETED_PERSUASION
- NO_MICROTARGETING
- NO_CANDIDATE_RECOMMENDATION
- NO_FOREIGN_FUNDING_CLAIM_GENERATED
- NO_DARK_MONEY_AS_VERIFIED_FACT
- NO_QUICK_ANSWER_GENERATION
- HUMAN_REVIEW_FOR_HIGH_RISK_CLAIMS
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

from .fec_adapter import (
    ConfidenceLevel,
    FECSource,
)
from .funding_summary import (
    FundingSummaryResult,
    FundingSummaryStatus,
    FundingSourceSummary,
    TrailTerminationMarker,
)


# =============================================================================
# Confidence Labels (aligned with fec_adapter.ConfidenceLevel)
# =============================================================================


class ConfidenceLabel(Enum):
    """WSP 97 confidence classification for claims.

    These labels map directly to ConfidenceLevel for consistency,
    but are applied at the claim level rather than source level.
    """

    VERIFIED_FACT = "verified_fact"
    """Direct FEC filing or source reference with high credibility confirms the claim."""

    HIGH_CONFIDENCE_INFERENCE = "high_confidence_inference"
    """Multiple corroborating official/public sources support the claim."""

    LOW_CONFIDENCE_INFERENCE = "low_confidence_inference"
    """Single weak/non-official source or circumstantial evidence."""

    UNKNOWN = "unknown"
    """Missing source, trail termination, or insufficient evidence."""


# =============================================================================
# Human Review Triggers
# =============================================================================


class HumanReviewTrigger(Enum):
    """Conditions that trigger human review before display.

    WSP 97 requires flagging dangerous edge cases for operator review.
    """

    FOREIGN_FUNDING_ALLEGATION = "foreign_funding_allegation"
    """Any mention of foreign funding triggers review regardless of confidence."""

    CRIMINAL_ACCUSATION = "criminal_accusation"
    """Any criminal accusation triggers review regardless of confidence."""

    LOW_CONFIDENCE_HIGH_IMPACT = "low_confidence_high_impact"
    """Low confidence claim with high potential impact."""

    SOURCE_CONTRADICTION = "source_contradiction"
    """Contradicting information between sources."""

    DARK_MONEY_LARGE_AMOUNT = "dark_money_large_amount"
    """501(c)(4) dark money exceeding threshold ($500K default)."""

    TRAIL_TERMINATION_SIGNIFICANT = "trail_termination_significant"
    """Significant evidence gap at trail termination point."""


# =============================================================================
# Confidence Scoring Status
# =============================================================================


class ConfidenceScoringStatus(Enum):
    """Status of confidence scoring operation."""

    SUCCESS = "success"
    """Confidence scoring completed successfully."""

    NO_FUNDING_SUMMARY = "no_funding_summary"
    """No funding summary provided to score."""

    FUNDING_SUMMARY_ERROR = "funding_summary_error"
    """Funding summary has an error status (fail-closed propagation)."""

    SCORING_ERROR = "scoring_error"
    """Error during confidence scoring process."""


# =============================================================================
# Data Types
# =============================================================================


@dataclass
class ConfidenceScoredClaim:
    """A single claim with explicit confidence label.

    Attributes:
        claim_text: Human-readable claim text.
        claim_type: Type of claim (e.g., "funding_source", "total_raised", "trail_termination").
        confidence_label: WSP 97 confidence classification.
        original_confidence: Original ConfidenceLevel from source data.
        factors: Factors that influenced confidence determination.
        source_reference: FEC source reference for provenance.
        requires_human_review: True if human review triggered.
        human_review_triggers: List of triggers that apply.
    """

    claim_text: str
    claim_type: str
    confidence_label: ConfidenceLabel
    original_confidence: ConfidenceLevel
    factors: List[str] = field(default_factory=list)
    source_reference: Optional[FECSource] = None
    requires_human_review: bool = False
    human_review_triggers: List[HumanReviewTrigger] = field(default_factory=list)


@dataclass
class ConfidenceScoredFundingSource:
    """A funding source with explicit confidence label.

    Preserves all original FundingSourceSummary fields plus adds confidence scoring.

    Attributes:
        source_name: Name of the funding source.
        source_type: Type of source (individual, committee, pac, etc.).
        amount: Total amount from this source.
        percentage: Percentage of total funding.
        contribution_count: Number of contributions.
        is_aggregated: True if aggregated category.
        original_confidence: Original ConfidenceLevel from source data.
        confidence_label: WSP 97 confidence classification.
        source_reference: FEC source reference for provenance (preserved).
        requires_human_review: True if human review triggered.
        human_review_triggers: List of applicable triggers.
        scoring_factors: Factors that influenced confidence determination.
    """

    source_name: str
    source_type: str
    amount: float
    percentage: float
    contribution_count: int
    is_aggregated: bool
    original_confidence: ConfidenceLevel
    confidence_label: ConfidenceLabel
    source_reference: Optional[FECSource] = None
    requires_human_review: bool = False
    human_review_triggers: List[HumanReviewTrigger] = field(default_factory=list)
    scoring_factors: List[str] = field(default_factory=list)


@dataclass
class ConfidenceScoredFundingSummary:
    """Funding summary with explicit confidence labels on all claims.

    Attributes:
        status: Confidence scoring status.
        candidate_id: FEC candidate ID.
        candidate_name: Candidate name.
        total_raised: Total amount raised.
        total_contributions: Total number of contributions.
        scored_sources: Top funding sources with confidence labels.
        summary_claims: Additional claims about the summary.
        trail_termination_markers: Preserved from original (WSP 97 compliance).
        human_review_required: True if any claim triggers human review.
        all_human_review_triggers: All triggers that apply to this summary.
        overall_confidence: Aggregate confidence for the summary.
        source_reference: Primary FEC source reference (preserved).
        error_message: Error message if status is not SUCCESS.
    """

    status: ConfidenceScoringStatus
    candidate_id: Optional[str] = None
    candidate_name: Optional[str] = None
    total_raised: float = 0.0
    total_contributions: int = 0
    scored_sources: List[ConfidenceScoredFundingSource] = field(default_factory=list)
    summary_claims: List[ConfidenceScoredClaim] = field(default_factory=list)
    trail_termination_markers: List[TrailTerminationMarker] = field(default_factory=list)
    human_review_required: bool = False
    all_human_review_triggers: List[HumanReviewTrigger] = field(default_factory=list)
    overall_confidence: ConfidenceLabel = ConfidenceLabel.UNKNOWN
    source_reference: Optional[FECSource] = None
    error_message: Optional[str] = None

    @property
    def is_successful(self) -> bool:
        """True if confidence scoring completed successfully."""
        return self.status == ConfidenceScoringStatus.SUCCESS

    @property
    def has_error(self) -> bool:
        """True if confidence scoring failed."""
        return self.status in (
            ConfidenceScoringStatus.FUNDING_SUMMARY_ERROR,
            ConfidenceScoringStatus.SCORING_ERROR,
        )


# =============================================================================
# Confidence Rule Matrix
# =============================================================================


# Keywords that trigger foreign funding human review
_FOREIGN_KEYWORDS = frozenset([
    "foreign",
    "overseas",
    "international",
    "non-us",
    "non-american",
    "china",
    "russia",
    "iran",
    "saudi",
    "qatar",
    "uae",
    "foreign national",
])

# Keywords that trigger criminal accusation human review
_CRIMINAL_KEYWORDS = frozenset([
    "fraud",
    "crime",
    "criminal",
    "indicted",
    "convicted",
    "bribery",
    "corruption",
    "money laundering",
    "illegal",
    "felony",
    "misdemeanor",
])

# Source types considered direct/official (verified_fact eligible)
_DIRECT_SOURCE_TYPES = frozenset([
    "fec_filing",
    "state_filing",
    "court_record",
])

# Dark money threshold for human review trigger ($500K default)
_DARK_MONEY_THRESHOLD = 500000.0


def _has_foreign_keywords(text: str) -> bool:
    """Check if text contains foreign funding keywords."""
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in _FOREIGN_KEYWORDS)


def _has_criminal_keywords(text: str) -> bool:
    """Check if text contains criminal accusation keywords."""
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in _CRIMINAL_KEYWORDS)


def _confidence_level_to_label(level: ConfidenceLevel) -> ConfidenceLabel:
    """Convert ConfidenceLevel to ConfidenceLabel."""
    mapping = {
        ConfidenceLevel.VERIFIED_FACT: ConfidenceLabel.VERIFIED_FACT,
        ConfidenceLevel.HIGH_CONFIDENCE_INFERENCE: ConfidenceLabel.HIGH_CONFIDENCE_INFERENCE,
        ConfidenceLevel.LOW_CONFIDENCE_INFERENCE: ConfidenceLabel.LOW_CONFIDENCE_INFERENCE,
        ConfidenceLevel.UNKNOWN: ConfidenceLabel.UNKNOWN,
    }
    return mapping.get(level, ConfidenceLabel.UNKNOWN)


def _determine_source_confidence_label(
    source: FundingSourceSummary,
) -> tuple[ConfidenceLabel, List[str]]:
    """Determine confidence label for a funding source.

    Args:
        source: Funding source summary.

    Returns:
        Tuple of (confidence label, list of factors).
    """
    factors = []

    # Check if source reference is present
    has_source_ref = source.source_reference is not None

    if has_source_ref:
        factors.append("source_reference_present")

        # Check source type
        source_type = source.source_reference.source_type if source.source_reference else None

        if source_type in _DIRECT_SOURCE_TYPES:
            factors.append(f"direct_source_type:{source_type}")
            # Direct filing with source reference = VERIFIED_FACT
            if source.confidence == ConfidenceLevel.VERIFIED_FACT:
                return ConfidenceLabel.VERIFIED_FACT, factors
            else:
                # Source reference present but original confidence is lower
                return _confidence_level_to_label(source.confidence), factors
        else:
            factors.append(f"source_type:{source_type}")
            # Non-direct source type
            if source.confidence == ConfidenceLevel.VERIFIED_FACT:
                # Verified in original, keep it
                return ConfidenceLabel.VERIFIED_FACT, factors
            elif source.confidence == ConfidenceLevel.HIGH_CONFIDENCE_INFERENCE:
                return ConfidenceLabel.HIGH_CONFIDENCE_INFERENCE, factors
            else:
                return _confidence_level_to_label(source.confidence), factors
    else:
        factors.append("source_reference_absent")
        # No source reference = cap at HIGH_CONFIDENCE_INFERENCE at best
        if source.confidence == ConfidenceLevel.VERIFIED_FACT:
            factors.append("downgraded_from_verified_due_to_missing_source")
            return ConfidenceLabel.HIGH_CONFIDENCE_INFERENCE, factors
        else:
            return _confidence_level_to_label(source.confidence), factors


def _check_human_review_triggers(
    source_name: str,
    amount: float,
    confidence_label: ConfidenceLabel,
) -> List[HumanReviewTrigger]:
    """Check which human review triggers apply to a source.

    Args:
        source_name: Name of the funding source.
        amount: Amount from this source.
        confidence_label: Determined confidence label.

    Returns:
        List of applicable human review triggers.
    """
    triggers = []

    # Foreign funding allegation (any confidence)
    if _has_foreign_keywords(source_name):
        triggers.append(HumanReviewTrigger.FOREIGN_FUNDING_ALLEGATION)

    # Criminal accusation (any confidence)
    if _has_criminal_keywords(source_name):
        triggers.append(HumanReviewTrigger.CRIMINAL_ACCUSATION)

    # Low confidence + high impact (amount > $100K and low confidence)
    if confidence_label == ConfidenceLabel.LOW_CONFIDENCE_INFERENCE and amount > 100000.0:
        triggers.append(HumanReviewTrigger.LOW_CONFIDENCE_HIGH_IMPACT)

    return triggers


def _score_funding_source(
    source: FundingSourceSummary,
) -> ConfidenceScoredFundingSource:
    """Score a single funding source.

    Args:
        source: Original funding source summary.

    Returns:
        Confidence-scored funding source.
    """
    # Determine confidence label
    confidence_label, factors = _determine_source_confidence_label(source)

    # Check human review triggers
    triggers = _check_human_review_triggers(
        source.source_name,
        source.amount,
        confidence_label,
    )

    return ConfidenceScoredFundingSource(
        source_name=source.source_name,
        source_type=source.source_type,
        amount=source.amount,
        percentage=source.percentage,
        contribution_count=source.contribution_count,
        is_aggregated=source.is_aggregated,
        original_confidence=source.confidence,
        confidence_label=confidence_label,
        source_reference=source.source_reference,  # Preserved
        requires_human_review=len(triggers) > 0,
        human_review_triggers=triggers,
        scoring_factors=factors,
    )


def _build_summary_claims(
    summary: FundingSummaryResult,
    scored_sources: List[ConfidenceScoredFundingSource],
) -> List[ConfidenceScoredClaim]:
    """Build summary-level claims with confidence labels.

    Args:
        summary: Original funding summary.
        scored_sources: Already-scored funding sources.

    Returns:
        List of summary-level claims.
    """
    claims = []

    # Total raised claim
    if summary.total_raised > 0:
        # Total raised confidence based on overall summary confidence
        total_label = _confidence_level_to_label(summary.confidence)
        total_factors = ["aggregate_from_fec_records"]

        if summary.source_reference is not None:
            total_factors.append("primary_source_reference_present")

        claims.append(
            ConfidenceScoredClaim(
                claim_text=f"Candidate raised ${summary.total_raised:,.2f}",
                claim_type="total_raised",
                confidence_label=total_label,
                original_confidence=summary.confidence,
                factors=total_factors,
                source_reference=summary.source_reference,
                requires_human_review=False,
                human_review_triggers=[],
            )
        )

    # Trail termination claims
    for marker in summary.trail_termination_markers:
        # Trail terminations are always UNKNOWN for what lies beyond
        marker_claim_text = f"Trail stops: {marker.value}"

        triggers = []
        # Dark money trail termination might trigger review
        if marker == TrailTerminationMarker.NO_DARK_MONEY_TRACE_IN_THIS_SLICE:
            # Check if there might be significant dark money
            triggers.append(HumanReviewTrigger.TRAIL_TERMINATION_SIGNIFICANT)

        claims.append(
            ConfidenceScoredClaim(
                claim_text=marker_claim_text,
                claim_type="trail_termination",
                confidence_label=ConfidenceLabel.UNKNOWN,
                original_confidence=ConfidenceLevel.UNKNOWN,
                factors=["trail_termination_marker", f"marker:{marker.value}"],
                source_reference=None,
                requires_human_review=len(triggers) > 0,
                human_review_triggers=triggers,
            )
        )

    return claims


def _calculate_overall_confidence(
    scored_sources: List[ConfidenceScoredFundingSource],
    summary_confidence: ConfidenceLevel,
) -> ConfidenceLabel:
    """Calculate overall confidence for the summary.

    Uses the minimum confidence across all sources, unless the summary itself
    has a known confidence level.

    Args:
        scored_sources: Scored funding sources.
        summary_confidence: Original summary confidence level.

    Returns:
        Overall confidence label.
    """
    if not scored_sources:
        return _confidence_level_to_label(summary_confidence)

    # Get all confidence labels
    labels = [s.confidence_label for s in scored_sources]

    # Order: UNKNOWN < LOW < HIGH < VERIFIED
    label_order = [
        ConfidenceLabel.UNKNOWN,
        ConfidenceLabel.LOW_CONFIDENCE_INFERENCE,
        ConfidenceLabel.HIGH_CONFIDENCE_INFERENCE,
        ConfidenceLabel.VERIFIED_FACT,
    ]

    # Find minimum (most conservative)
    min_label = ConfidenceLabel.VERIFIED_FACT
    for label in labels:
        if label_order.index(label) < label_order.index(min_label):
            min_label = label

    return min_label


# =============================================================================
# Core Scoring Function
# =============================================================================


def score_funding_summary_confidence(
    summary: FundingSummaryResult,
) -> ConfidenceScoredFundingSummary:
    """Score a funding summary with explicit WSP 97 confidence labels.

    This function consumes a FundingSummaryResult and applies confidence labels
    to each funding source and the overall summary. It:
    - Preserves source references for provenance
    - Preserves trail termination markers
    - Determines confidence labels based on source presence/type
    - Triggers human review for high-risk claims
    - Does NOT generate prose or quick answers

    IMPORTANT: This function does NOT generate quick answers, recommendations,
    or persuasion language. It produces structured, machine-readable claims only.

    SAFETY: This function does NOT:
    - Make candidate recommendations
    - Generate persuasion language
    - Claim dark money as verified fact
    - Generate foreign funding claims (only flags them for human review)
    - Generate quick answers

    Args:
        summary: Funding summary result to score.

    Returns:
        ConfidenceScoredFundingSummary with explicit confidence labels.
    """
    # Handle None input
    if summary is None:
        return ConfidenceScoredFundingSummary(
            status=ConfidenceScoringStatus.NO_FUNDING_SUMMARY,
            error_message="No funding summary provided",
        )

    # Handle error status from summary (fail-closed propagation)
    if summary.has_error:
        return ConfidenceScoredFundingSummary(
            status=ConfidenceScoringStatus.FUNDING_SUMMARY_ERROR,
            candidate_id=summary.candidate_id,
            candidate_name=summary.candidate_name,
            trail_termination_markers=summary.trail_termination_markers,
            source_reference=summary.source_reference,
            error_message=summary.error_message or "Funding summary has error status",
        )

    # Handle non-success status
    if not summary.is_successful:
        return ConfidenceScoredFundingSummary(
            status=ConfidenceScoringStatus.FUNDING_SUMMARY_ERROR,
            candidate_id=summary.candidate_id,
            candidate_name=summary.candidate_name,
            trail_termination_markers=summary.trail_termination_markers,
            source_reference=summary.source_reference,
            error_message=summary.error_message or f"Funding summary status: {summary.status.value}",
        )

    # Score each funding source
    scored_sources = [_score_funding_source(source) for source in summary.top_sources]

    # Build summary claims
    summary_claims = _build_summary_claims(summary, scored_sources)

    # Collect all human review triggers
    all_triggers: List[HumanReviewTrigger] = []
    for source in scored_sources:
        all_triggers.extend(source.human_review_triggers)
    for claim in summary_claims:
        all_triggers.extend(claim.human_review_triggers)

    # Deduplicate triggers
    unique_triggers = list(set(all_triggers))

    # Determine if human review is required
    human_review_required = len(unique_triggers) > 0

    # Calculate overall confidence
    overall_confidence = _calculate_overall_confidence(
        scored_sources,
        summary.confidence,
    )

    return ConfidenceScoredFundingSummary(
        status=ConfidenceScoringStatus.SUCCESS,
        candidate_id=summary.candidate_id,
        candidate_name=summary.candidate_name,
        total_raised=summary.total_raised,
        total_contributions=summary.total_contributions,
        scored_sources=scored_sources,
        summary_claims=summary_claims,
        trail_termination_markers=summary.trail_termination_markers,  # Preserved
        human_review_required=human_review_required,
        all_human_review_triggers=unique_triggers,
        overall_confidence=overall_confidence,
        source_reference=summary.source_reference,  # Preserved
    )


# =============================================================================
# Convenience Functions
# =============================================================================


def get_verified_facts(
    scored_summary: ConfidenceScoredFundingSummary,
) -> List[ConfidenceScoredClaim]:
    """Get all claims with VERIFIED_FACT confidence.

    Args:
        scored_summary: Confidence-scored funding summary.

    Returns:
        List of verified fact claims.
    """
    if not scored_summary.is_successful:
        return []

    verified = []

    # Add source claims that are verified facts
    for source in scored_summary.scored_sources:
        if source.confidence_label == ConfidenceLabel.VERIFIED_FACT:
            verified.append(
                ConfidenceScoredClaim(
                    claim_text=f"${source.amount:,.2f} from {source.source_name}",
                    claim_type="funding_source",
                    confidence_label=ConfidenceLabel.VERIFIED_FACT,
                    original_confidence=source.original_confidence,
                    factors=source.scoring_factors,
                    source_reference=source.source_reference,
                    requires_human_review=source.requires_human_review,
                    human_review_triggers=source.human_review_triggers,
                )
            )

    # Add summary claims that are verified facts
    for claim in scored_summary.summary_claims:
        if claim.confidence_label == ConfidenceLabel.VERIFIED_FACT:
            verified.append(claim)

    return verified


def get_unknown_claims(
    scored_summary: ConfidenceScoredFundingSummary,
) -> List[ConfidenceScoredClaim]:
    """Get all claims with UNKNOWN confidence.

    Args:
        scored_summary: Confidence-scored funding summary.

    Returns:
        List of unknown claims (including trail terminations).
    """
    if not scored_summary.is_successful:
        return []

    unknown = []

    # Add source claims that are unknown
    for source in scored_summary.scored_sources:
        if source.confidence_label == ConfidenceLabel.UNKNOWN:
            unknown.append(
                ConfidenceScoredClaim(
                    claim_text=f"${source.amount:,.2f} from {source.source_name}",
                    claim_type="funding_source",
                    confidence_label=ConfidenceLabel.UNKNOWN,
                    original_confidence=source.original_confidence,
                    factors=source.scoring_factors,
                    source_reference=source.source_reference,
                    requires_human_review=source.requires_human_review,
                    human_review_triggers=source.human_review_triggers,
                )
            )

    # Add summary claims that are unknown (including trail terminations)
    for claim in scored_summary.summary_claims:
        if claim.confidence_label == ConfidenceLabel.UNKNOWN:
            unknown.append(claim)

    return unknown


def get_human_review_claims(
    scored_summary: ConfidenceScoredFundingSummary,
) -> List[ConfidenceScoredClaim]:
    """Get all claims that require human review.

    Args:
        scored_summary: Confidence-scored funding summary.

    Returns:
        List of claims requiring human review.
    """
    if not scored_summary.is_successful:
        return []

    review_claims = []

    # Add source claims requiring review
    for source in scored_summary.scored_sources:
        if source.requires_human_review:
            review_claims.append(
                ConfidenceScoredClaim(
                    claim_text=f"${source.amount:,.2f} from {source.source_name}",
                    claim_type="funding_source",
                    confidence_label=source.confidence_label,
                    original_confidence=source.original_confidence,
                    factors=source.scoring_factors,
                    source_reference=source.source_reference,
                    requires_human_review=True,
                    human_review_triggers=source.human_review_triggers,
                )
            )

    # Add summary claims requiring review
    for claim in scored_summary.summary_claims:
        if claim.requires_human_review:
            review_claims.append(claim)

    return review_claims
