"""
Entity Resolution for VoteBallots FoundUp.

Resolves user-provided candidate queries to FEC candidate records using
deterministic matching against the FEC adapter.

Design Principles:
- AMBIGUITY_PRESERVED_NOT_GUESSED: When multiple matches exist, return all
- NO_HALLUCINATED_CANDIDATE_IDS: Only return candidates from adapter
- Confidence scoring for RESOLUTION quality (not funding claims)
- Deterministic ordering for reproducibility

WSP 97 Compliance:
- Confidence labels apply to resolution quality only
- No funding summary, no contribution aggregation
- No quick answer generation

Political Safety Boundaries:
- NO_TARGETED_PERSUASION
- NO_MICROTARGETING
- NO_CANDIDATE_RECOMMENDATION
- NO_PARTISAN_SCORING
- NO_FUNDING_SUMMARY_IN_THIS_SLICE
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

from .fec_adapter import (
    CandidateRecord,
    FECAdapterInterface,
    FECErrorType,
)


# =============================================================================
# Resolution Status
# =============================================================================


class EntityResolutionStatus(Enum):
    """Status of an entity resolution attempt."""

    EXACT_ONE_MATCH = "exact_one_match"
    MULTIPLE_MATCHES = "multiple_matches"
    NO_MATCH = "no_match"
    ADAPTER_ERROR = "adapter_error"
    INVALID_QUERY = "invalid_query"


# =============================================================================
# Request/Response Types
# =============================================================================


@dataclass
class EntityResolutionRequest:
    """Request for entity resolution.

    Attributes:
        query: User-provided candidate name or identifier.
        state_hint: Optional state code (e.g., "NY", "CA").
        office_hint: Optional office code ("H" for House, "S" for Senate, "P" for President).
        party_hint: Optional party code (e.g., "DEM", "REP", "IND").
        cycle_hint: Optional election cycle year (e.g., 2024).
    """

    query: str
    state_hint: Optional[str] = None
    office_hint: Optional[str] = None
    party_hint: Optional[str] = None
    cycle_hint: Optional[int] = None

    def __post_init__(self):
        """Normalize hints to uppercase."""
        if self.state_hint:
            self.state_hint = self.state_hint.upper().strip()
        if self.office_hint:
            self.office_hint = self.office_hint.upper().strip()
        if self.party_hint:
            self.party_hint = self.party_hint.upper().strip()
        if self.query:
            self.query = self.query.strip()


@dataclass
class EntityResolutionCandidate:
    """A resolved candidate from entity resolution.

    Attributes:
        candidate: The underlying CandidateRecord from FEC adapter.
        match_score: Score indicating match quality (0.0-1.0).
        match_reason: Human-readable explanation of why this matched.
    """

    candidate: CandidateRecord
    match_score: float
    match_reason: str

    @property
    def candidate_id(self) -> str:
        """Convenience accessor for candidate ID."""
        return self.candidate.candidate_id

    @property
    def name(self) -> str:
        """Convenience accessor for candidate name."""
        return self.candidate.name


@dataclass
class EntityResolutionResult:
    """Result of entity resolution.

    Attributes:
        status: Resolution status (one of EntityResolutionStatus).
        candidates: List of resolved candidates, empty if no match.
        confidence: Overall resolution confidence (0.0-1.0).
        disambiguation_message: Message for user when disambiguation required.
        error_message: Error message when status is ADAPTER_ERROR or INVALID_QUERY.
        request: Original request for reference.
    """

    status: EntityResolutionStatus
    candidates: List[EntityResolutionCandidate] = field(default_factory=list)
    confidence: float = 0.0
    disambiguation_message: Optional[str] = None
    error_message: Optional[str] = None
    request: Optional[EntityResolutionRequest] = None

    @property
    def is_resolved(self) -> bool:
        """True if exactly one candidate was found."""
        return self.status == EntityResolutionStatus.EXACT_ONE_MATCH

    @property
    def requires_disambiguation(self) -> bool:
        """True if multiple candidates were found."""
        return self.status == EntityResolutionStatus.MULTIPLE_MATCHES

    @property
    def has_error(self) -> bool:
        """True if resolution failed due to error."""
        return self.status in (
            EntityResolutionStatus.ADAPTER_ERROR,
            EntityResolutionStatus.INVALID_QUERY,
        )


# =============================================================================
# Entity Resolution Logic
# =============================================================================


def _validate_request(request: EntityResolutionRequest) -> Optional[str]:
    """Validate resolution request.

    Args:
        request: The resolution request to validate.

    Returns:
        Error message if invalid, None if valid.
    """
    # Note: request.__post_init__ strips whitespace, so we need to check
    # for empty after stripping
    if not request.query:
        return "Query cannot be blank or empty"

    # Validate state hint format if provided
    if request.state_hint:
        if len(request.state_hint) != 2:
            return f"Invalid state hint: {request.state_hint}. Use 2-letter state code."

    # Validate office hint if provided
    if request.office_hint:
        valid_offices = {"H", "S", "P"}
        if request.office_hint not in valid_offices:
            return f"Invalid office hint: {request.office_hint}. Use H, S, or P."

    # Validate cycle hint if provided
    if request.cycle_hint:
        if request.cycle_hint < 1900 or request.cycle_hint > 2100:
            return f"Invalid cycle hint: {request.cycle_hint}. Use a valid election year."

    return None


def _calculate_match_score(
    candidate: CandidateRecord,
    request: EntityResolutionRequest,
) -> tuple[float, str]:
    """Calculate match score and reason for a candidate.

    Args:
        candidate: Candidate to score.
        request: Original resolution request.

    Returns:
        Tuple of (score, reason).
    """
    score = 0.0
    reasons = []

    query_upper = request.query.upper()

    # Name matching - primary factor
    if query_upper in candidate.name.upper():
        # Exact substring match
        name_ratio = len(query_upper) / len(candidate.name)
        name_score = 0.5 + (0.3 * min(1.0, name_ratio))
        score += name_score
        reasons.append(f"Name contains '{request.query}'")
    else:
        # Check individual words
        query_words = query_upper.split()
        name_words = candidate.name.upper().split()
        matching_words = sum(1 for qw in query_words if any(qw in nw for nw in name_words))
        if matching_words > 0:
            word_score = 0.3 * (matching_words / len(query_words))
            score += word_score
            reasons.append(f"Name partially matches ({matching_words} words)")

    # Hint matching - bonus points
    if request.state_hint and candidate.state == request.state_hint:
        score += 0.1
        reasons.append(f"State matches ({request.state_hint})")

    if request.office_hint and candidate.office == request.office_hint:
        score += 0.1
        reasons.append(f"Office matches ({request.office_hint})")

    if request.party_hint and candidate.party == request.party_hint:
        score += 0.05
        reasons.append(f"Party matches ({request.party_hint})")

    if request.cycle_hint and request.cycle_hint in candidate.election_years:
        score += 0.05
        reasons.append(f"Cycle matches ({request.cycle_hint})")

    # Cap score at 1.0
    score = min(1.0, score)

    reason = "; ".join(reasons) if reasons else "Partial match"
    return score, reason


def _build_disambiguation_message(
    candidates: List[EntityResolutionCandidate],
    request: EntityResolutionRequest,
) -> str:
    """Build disambiguation message for multiple matches.

    Args:
        candidates: List of matched candidates.
        request: Original request.

    Returns:
        Human-readable disambiguation message.
    """
    count = len(candidates)
    query = request.query

    # Build candidate list for message
    candidate_summaries = []
    for i, rc in enumerate(candidates[:5], 1):  # Limit to first 5
        c = rc.candidate
        office_str = c.office_full or c.office or "Unknown Office"
        state_str = c.state or "Unknown State"
        party_str = c.party or "Unknown Party"
        candidate_summaries.append(
            f"{i}. {c.name} ({party_str}, {state_str}, {office_str})"
        )

    summary_text = "\n".join(candidate_summaries)

    hints = []
    if not request.state_hint:
        hints.append("state (e.g., NY, CA)")
    if not request.office_hint:
        hints.append("office (H=House, S=Senate, P=President)")
    if not request.party_hint:
        hints.append("party (DEM, REP, IND)")

    hint_text = ", ".join(hints) if hints else "additional context"

    return (
        f"Found {count} candidates matching '{query}'.\n"
        f"Please specify {hint_text} to disambiguate.\n\n"
        f"Candidates:\n{summary_text}"
    )


def resolve_candidate_entity(
    request: EntityResolutionRequest,
    adapter: FECAdapterInterface,
) -> EntityResolutionResult:
    """Resolve a candidate entity query to FEC candidate record(s).

    This function performs deterministic entity resolution:
    - Validates the request
    - Searches the FEC adapter with query and hints
    - Scores and ranks matches
    - Returns EXACT_ONE_MATCH, MULTIPLE_MATCHES, NO_MATCH, or error status

    IMPORTANT: This function does NOT hallucinate candidates. It only returns
    candidates that exist in the adapter's data source.

    Args:
        request: Entity resolution request with query and optional hints.
        adapter: FEC adapter interface to search against.

    Returns:
        EntityResolutionResult with resolved candidates or error information.
    """
    # Validate request
    validation_error = _validate_request(request)
    if validation_error:
        return EntityResolutionResult(
            status=EntityResolutionStatus.INVALID_QUERY,
            error_message=validation_error,
            confidence=0.0,
            request=request,
        )

    # Search adapter
    try:
        search_result = adapter.search_candidates(
            name=request.query,
            state=request.state_hint,
            office=request.office_hint,
            party=request.party_hint,
            cycle=request.cycle_hint,
        )
    except Exception as e:
        return EntityResolutionResult(
            status=EntityResolutionStatus.ADAPTER_ERROR,
            error_message=f"Adapter error: {str(e)}",
            confidence=0.0,
            request=request,
        )

    # Handle adapter errors
    if not search_result.success:
        error = search_result.error
        error_msg = str(error) if error else "Unknown adapter error"
        return EntityResolutionResult(
            status=EntityResolutionStatus.ADAPTER_ERROR,
            error_message=error_msg,
            confidence=0.0,
            request=request,
        )

    # No matches
    if not search_result.candidates:
        return EntityResolutionResult(
            status=EntityResolutionStatus.NO_MATCH,
            candidates=[],
            confidence=1.0,  # High confidence in NO_MATCH
            request=request,
        )

    # Score and wrap candidates
    resolved_candidates = []
    for candidate in search_result.candidates:
        score, reason = _calculate_match_score(candidate, request)
        resolved_candidates.append(
            EntityResolutionCandidate(
                candidate=candidate,
                match_score=score,
                match_reason=reason,
            )
        )

    # Sort by score descending, then by name for deterministic ordering
    resolved_candidates.sort(
        key=lambda x: (-x.match_score, x.candidate.name)
    )

    # Determine status and confidence
    if len(resolved_candidates) == 1:
        status = EntityResolutionStatus.EXACT_ONE_MATCH
        confidence = resolved_candidates[0].match_score
        disambiguation_message = None
    else:
        status = EntityResolutionStatus.MULTIPLE_MATCHES
        # Confidence is lower when multiple matches exist
        # Higher score difference between top 2 = higher confidence
        top_score = resolved_candidates[0].match_score
        second_score = resolved_candidates[1].match_score if len(resolved_candidates) > 1 else 0.0
        score_gap = top_score - second_score
        confidence = min(0.5, top_score * 0.5 + score_gap * 0.5)
        disambiguation_message = _build_disambiguation_message(
            resolved_candidates, request
        )

    return EntityResolutionResult(
        status=status,
        candidates=resolved_candidates,
        confidence=confidence,
        disambiguation_message=disambiguation_message,
        request=request,
    )


# =============================================================================
# Module-level convenience functions
# =============================================================================


def resolve_by_name(
    name: str,
    adapter: FECAdapterInterface,
    state: Optional[str] = None,
    office: Optional[str] = None,
) -> EntityResolutionResult:
    """Convenience function to resolve a candidate by name.

    Args:
        name: Candidate name to search for.
        adapter: FEC adapter to use.
        state: Optional state hint.
        office: Optional office hint.

    Returns:
        EntityResolutionResult.
    """
    request = EntityResolutionRequest(
        query=name,
        state_hint=state,
        office_hint=office,
    )
    return resolve_candidate_entity(request, adapter)


def resolve_by_id(
    candidate_id: str,
    adapter: FECAdapterInterface,
) -> EntityResolutionResult:
    """Resolve a candidate by FEC ID.

    This performs a direct lookup by ID, which should return exactly one
    candidate or no match.

    Args:
        candidate_id: FEC candidate ID.
        adapter: FEC adapter to use.

    Returns:
        EntityResolutionResult.
    """
    if not candidate_id or not candidate_id.strip():
        return EntityResolutionResult(
            status=EntityResolutionStatus.INVALID_QUERY,
            error_message="Candidate ID cannot be empty",
            confidence=0.0,
        )

    # Use get_candidate for direct ID lookup
    try:
        result = adapter.get_candidate(candidate_id.strip())
    except Exception as e:
        return EntityResolutionResult(
            status=EntityResolutionStatus.ADAPTER_ERROR,
            error_message=f"Adapter error: {str(e)}",
            confidence=0.0,
        )

    if not result.success:
        if result.error and result.error.error_type == FECErrorType.NOT_FOUND:
            return EntityResolutionResult(
                status=EntityResolutionStatus.NO_MATCH,
                candidates=[],
                confidence=1.0,
            )
        else:
            error_msg = str(result.error) if result.error else "Unknown adapter error"
            return EntityResolutionResult(
                status=EntityResolutionStatus.ADAPTER_ERROR,
                error_message=error_msg,
                confidence=0.0,
            )

    if not result.candidates:
        return EntityResolutionResult(
            status=EntityResolutionStatus.NO_MATCH,
            candidates=[],
            confidence=1.0,
        )

    # Direct ID lookup - exact match
    candidate = result.candidates[0]
    return EntityResolutionResult(
        status=EntityResolutionStatus.EXACT_ONE_MATCH,
        candidates=[
            EntityResolutionCandidate(
                candidate=candidate,
                match_score=1.0,
                match_reason=f"Direct ID lookup: {candidate_id}",
            )
        ],
        confidence=1.0,
    )
