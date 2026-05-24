"""
Vote/Ballots FoundUp - AI-native political transparency.

User provides candidate name (speech or text), receives funding
transparency report with evidence trail.

WSP 97 Compliance: All outputs explicitly separate:
- verified_fact
- high_confidence_inference
- low_confidence_inference
- unknown

Model Behavior Rules:
- Never state hidden funding as fact unless sourced
- Distinguish direct disclosure from inferred alignment
- Never flatten influence categories
- Show where evidence stops
- No hallucinated accusations
- Flag dangerous edge cases for human review

Political Safety Boundaries:
- NO_TARGETED_PERSUASION
- NO_MICROTARGETING
- NO_CANDIDATE_RECOMMENDATION
- NO_FOREIGN_FUNDING_CLAIM_WITHOUT_EXPLICIT_EVIDENCE
- NO_DARK_MONEY_AS_VERIFIED_FACT
- HUMAN_REVIEW_FOR_HIGH_RISK_CLAIMS
"""

__version__ = "0.5.0"  # Updated for Quick Answer Generation (Phase 1, Slice 5)
__status__ = "poc"  # Phase 1 PoC implementation

# FEC Adapter exports
from .fec_adapter import (
    # Error types
    FECError,
    FECErrorType,
    # Confidence levels
    ConfidenceLevel,
    # Source tracking
    FECSource,
    # Data records
    CandidateRecord,
    CommitteeRecord,
    ContributionRecord,
    FundingSummary,
    # Result types
    CandidateSearchResult,
    CommitteeSearchResult,
    ContributionSearchResult,
    FundingSummaryResult,
    # Adapter interface and implementations
    FECAdapterInterface,
    MockFECAdapter,
    # Factory functions
    create_fec_adapter,
    get_mock_adapter,
)

# Entity Resolution exports (Slice 2)
from .entity_resolution import (
    # Status enum
    EntityResolutionStatus,
    # Request/Response types
    EntityResolutionRequest,
    EntityResolutionResult,
    EntityResolutionCandidate,
    # Core resolution function
    resolve_candidate_entity,
    # Convenience functions
    resolve_by_name,
    resolve_by_id,
)

# Funding Summary exports (Slice 3)
from .funding_summary import (
    # Status enum
    FundingSummaryStatus,
    # Trail termination markers
    TrailTerminationMarker,
    # Request/Response types
    FundingSummaryRequest,
    FundingSummaryResult,
    FundingSourceSummary,
    # Core summary function
    summarize_candidate_funding,
    # Convenience functions
    summarize_by_candidate_id,
    summarize_by_name,
)

# Confidence Scoring exports (Slice 4)
from .confidence_scoring import (
    # Enums
    ConfidenceLabel,
    HumanReviewTrigger,
    ConfidenceScoringStatus,
    # Data types
    ConfidenceScoredClaim,
    ConfidenceScoredFundingSource,
    ConfidenceScoredFundingSummary,
    # Core scoring function
    score_funding_summary_confidence,
    # Convenience functions
    get_verified_facts,
    get_unknown_claims,
    get_human_review_claims,
)

# Quick Answer exports (Slice 5)
from .quick_answer import (
    # Data types
    QuickAnswer,
    AnswerFormat,
    # Core generation function
    generate_quick_answer,
    # Convenience functions
    generate_shell_answer,
    generate_markdown_answer,
    is_answer_ready_for_display,
)

__all__ = [
    # Error types
    "FECError",
    "FECErrorType",
    # Confidence levels
    "ConfidenceLevel",
    # Source tracking
    "FECSource",
    # Data records
    "CandidateRecord",
    "CommitteeRecord",
    "ContributionRecord",
    "FundingSummary",
    # Result types
    "CandidateSearchResult",
    "CommitteeSearchResult",
    "ContributionSearchResult",
    "FundingSummaryResult",
    # Adapter interface and implementations
    "FECAdapterInterface",
    "MockFECAdapter",
    # Factory functions
    "create_fec_adapter",
    "get_mock_adapter",
    # Entity Resolution (Slice 2)
    "EntityResolutionStatus",
    "EntityResolutionRequest",
    "EntityResolutionResult",
    "EntityResolutionCandidate",
    "resolve_candidate_entity",
    "resolve_by_name",
    "resolve_by_id",
    # Funding Summary (Slice 3)
    "FundingSummaryStatus",
    "TrailTerminationMarker",
    "FundingSummaryRequest",
    "FundingSummaryResult",
    "FundingSourceSummary",
    "summarize_candidate_funding",
    "summarize_by_candidate_id",
    "summarize_by_name",
    # Confidence Scoring (Slice 4)
    "ConfidenceLabel",
    "HumanReviewTrigger",
    "ConfidenceScoringStatus",
    "ConfidenceScoredClaim",
    "ConfidenceScoredFundingSource",
    "ConfidenceScoredFundingSummary",
    "score_funding_summary_confidence",
    "get_verified_facts",
    "get_unknown_claims",
    "get_human_review_claims",
    # Quick Answer (Slice 5)
    "QuickAnswer",
    "AnswerFormat",
    "generate_quick_answer",
    "generate_shell_answer",
    "generate_markdown_answer",
    "is_answer_ready_for_display",
]
