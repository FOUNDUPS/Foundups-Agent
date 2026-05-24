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

__version__ = "0.2.0"  # Updated for Entity Resolution (Phase 1, Slice 2)
__status__ = "poc"  # Updated from "design" for Phase 1 implementation

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
]
