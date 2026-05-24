"""
Funding Summary for VoteBallots FoundUp.

Generates structured funding summaries from resolved candidate entities using
deterministic FEC adapter data.

Design Principles:
- Consumes resolved candidate from entity_resolution module
- Uses FEC adapter funding data only
- Preserves source references for provenance
- Marks trail termination points explicitly
- No quick answer generation (just structured data)

WSP 97 Compliance:
- Confidence labels for each funding source
- Trail termination markers always present
- Source references preserved

Political Safety Boundaries:
- NO_TARGETED_PERSUASION
- NO_MICROTARGETING
- NO_CANDIDATE_RECOMMENDATION
- NO_FOREIGN_FUNDING_CLAIM
- NO_DARK_MONEY_AS_VERIFIED_FACT
- NO_QUICK_ANSWER_GENERATION
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

from .fec_adapter import (
    ConfidenceLevel,
    ContributionRecord,
    FECAdapterInterface,
    FECErrorType,
    FECSource,
    FundingSummary as AdapterFundingSummary,
)
from .entity_resolution import (
    EntityResolutionResult,
    EntityResolutionStatus,
)


# =============================================================================
# Trail Termination Markers
# =============================================================================


class TrailTerminationMarker(Enum):
    """Markers indicating where the public evidence trail stops.

    These markers make explicit what is NOT included in the funding summary.
    WSP 97 requires showing where evidence stops.
    """

    DIRECT_FEC_RECORDS_ONLY = "direct_fec_records_only"
    """Only direct FEC filings are included. No tracing through intermediaries."""

    NO_SUPER_PAC_TRACE_IN_THIS_SLICE = "no_super_pac_trace_in_this_slice"
    """Super PAC independent expenditures are not traced in this slice."""

    NO_DARK_MONEY_TRACE_IN_THIS_SLICE = "no_dark_money_trace_in_this_slice"
    """501(c)(4) dark money is not traced in this slice."""

    UNKNOWN_WHERE_SOURCE_ABSENT = "unknown_where_source_absent"
    """Some sources could not be identified; marked as unknown."""


# =============================================================================
# Funding Summary Status
# =============================================================================


class FundingSummaryStatus(Enum):
    """Status of a funding summary operation."""

    SUCCESS = "success"
    """Funding summary successfully generated."""

    NO_RESOLVED_CANDIDATE = "no_resolved_candidate"
    """No resolved candidate provided."""

    AMBIGUOUS_CANDIDATE = "ambiguous_candidate"
    """Multiple candidates matched; disambiguation required."""

    ADAPTER_ERROR = "adapter_error"
    """FEC adapter returned an error."""

    NO_FUNDING_DATA = "no_funding_data"
    """Candidate resolved but no funding data found."""

    INVALID_REQUEST = "invalid_request"
    """Invalid request parameters."""


# =============================================================================
# Data Types
# =============================================================================


@dataclass
class FundingSourceSummary:
    """Summary of a single funding source.

    Attributes:
        source_name: Name of the funding source (contributor name or category).
        source_type: Type of source (individual, committee, pac, etc.).
        amount: Total amount from this source.
        percentage: Percentage of total funding (0.0-100.0).
        confidence: WSP 97 confidence level for this source.
        source_reference: FEC source reference for provenance.
        contribution_count: Number of contributions from this source.
        is_aggregated: True if this is an aggregated category (e.g., "small donations").
    """

    source_name: str
    source_type: str
    amount: float
    percentage: float
    confidence: ConfidenceLevel
    source_reference: Optional[FECSource] = None
    contribution_count: int = 1
    is_aggregated: bool = False


@dataclass
class FundingSummaryRequest:
    """Request for funding summary generation.

    Attributes:
        resolution_result: The resolved candidate entity from entity_resolution.
        cycle: Optional election cycle year filter.
        top_n: Number of top sources to include (default 5).
    """

    resolution_result: EntityResolutionResult
    cycle: Optional[int] = None
    top_n: int = 5

    def __post_init__(self):
        """Validate request parameters."""
        if self.top_n < 1:
            self.top_n = 1
        elif self.top_n > 20:
            self.top_n = 20  # Cap to prevent excessive results


@dataclass
class FundingSummaryResult:
    """Result of funding summary generation.

    Attributes:
        status: Summary generation status.
        candidate_id: FEC candidate ID (if resolved).
        candidate_name: Candidate name (if resolved).
        total_raised: Total amount raised.
        total_contributions: Total number of contributions.
        top_sources: Top funding sources sorted by amount.
        contributions_by_type: Breakdown by contributor type.
        trail_termination_markers: Explicit markers showing where evidence stops.
        reporting_period_start: Start of reporting period.
        reporting_period_end: End of reporting period.
        source_reference: Primary FEC source reference.
        confidence: Overall confidence level for the summary.
        error_message: Error message if status is not SUCCESS.
    """

    status: FundingSummaryStatus
    candidate_id: Optional[str] = None
    candidate_name: Optional[str] = None
    total_raised: float = 0.0
    total_contributions: int = 0
    top_sources: List[FundingSourceSummary] = field(default_factory=list)
    contributions_by_type: dict = field(default_factory=dict)
    trail_termination_markers: List[TrailTerminationMarker] = field(default_factory=list)
    reporting_period_start: Optional[str] = None
    reporting_period_end: Optional[str] = None
    source_reference: Optional[FECSource] = None
    confidence: ConfidenceLevel = ConfidenceLevel.UNKNOWN
    error_message: Optional[str] = None

    @property
    def is_successful(self) -> bool:
        """True if funding summary was generated successfully."""
        return self.status == FundingSummaryStatus.SUCCESS

    @property
    def has_error(self) -> bool:
        """True if the summary generation failed."""
        return self.status in (
            FundingSummaryStatus.ADAPTER_ERROR,
            FundingSummaryStatus.INVALID_REQUEST,
        )

    @property
    def requires_disambiguation(self) -> bool:
        """True if the candidate was ambiguous."""
        return self.status == FundingSummaryStatus.AMBIGUOUS_CANDIDATE


# =============================================================================
# Core Summary Generation
# =============================================================================


def _build_trail_termination_markers(
    has_complete_data: bool,
    has_unknown_sources: bool,
) -> List[TrailTerminationMarker]:
    """Build trail termination markers based on data completeness.

    Args:
        has_complete_data: True if all data was successfully retrieved.
        has_unknown_sources: True if some sources could not be identified.

    Returns:
        List of applicable trail termination markers.
    """
    markers = [
        TrailTerminationMarker.DIRECT_FEC_RECORDS_ONLY,
        TrailTerminationMarker.NO_SUPER_PAC_TRACE_IN_THIS_SLICE,
        TrailTerminationMarker.NO_DARK_MONEY_TRACE_IN_THIS_SLICE,
    ]

    if has_unknown_sources:
        markers.append(TrailTerminationMarker.UNKNOWN_WHERE_SOURCE_ABSENT)

    return markers


def _aggregate_contributions_by_source(
    contributions: List[ContributionRecord],
) -> dict:
    """Aggregate contributions by contributor name.

    Args:
        contributions: List of contribution records.

    Returns:
        Dict mapping contributor name to aggregated data.
    """
    aggregated = {}

    for contrib in contributions:
        name = contrib.contributor_name or "UNKNOWN"
        if name not in aggregated:
            aggregated[name] = {
                "amount": 0.0,
                "count": 0,
                "source_type": contrib.contributor_type or "individual",
                "source_reference": contrib.source,
                "confidence": contrib.confidence,
            }
        aggregated[name]["amount"] += contrib.contribution_receipt_amount
        aggregated[name]["count"] += 1

    return aggregated


def _aggregate_contributions_by_type(
    contributions: List[ContributionRecord],
) -> dict:
    """Aggregate contributions by contributor type.

    Args:
        contributions: List of contribution records.

    Returns:
        Dict mapping contributor type to total amount.
    """
    by_type = {}

    for contrib in contributions:
        contrib_type = contrib.contributor_type or "individual"
        if contrib_type not in by_type:
            by_type[contrib_type] = 0.0
        by_type[contrib_type] += contrib.contribution_receipt_amount

    return by_type


def _build_top_sources(
    aggregated: dict,
    total_raised: float,
    top_n: int,
) -> List[FundingSourceSummary]:
    """Build top funding sources list sorted by amount.

    Args:
        aggregated: Aggregated contributions by source.
        total_raised: Total amount raised for percentage calculation.
        top_n: Number of top sources to include.

    Returns:
        List of FundingSourceSummary sorted by amount descending.
    """
    sources = []

    for name, data in aggregated.items():
        amount = data["amount"]
        percentage = (amount / total_raised * 100.0) if total_raised > 0 else 0.0

        sources.append(
            FundingSourceSummary(
                source_name=name,
                source_type=data["source_type"],
                amount=amount,
                percentage=round(percentage, 2),
                confidence=data["confidence"],
                source_reference=data["source_reference"],
                contribution_count=data["count"],
                is_aggregated=data["count"] > 1,
            )
        )

    # Sort by amount descending, then by name for deterministic ordering
    sources.sort(key=lambda x: (-x.amount, x.source_name))

    return sources[:top_n]


def summarize_candidate_funding(
    request: FundingSummaryRequest,
    adapter: FECAdapterInterface,
) -> FundingSummaryResult:
    """Generate a structured funding summary for a resolved candidate.

    This function consumes a resolved candidate entity and retrieves funding
    data from the FEC adapter. It produces a structured summary with:
    - Top funding sources sorted by amount
    - Contribution breakdown by type
    - Trail termination markers showing where evidence stops
    - Source references for provenance

    IMPORTANT: This function does NOT generate prose or quick answers.
    It produces structured data only.

    SAFETY: This function does NOT:
    - Make recommendations
    - Generate persuasion language
    - Claim dark money as verified fact
    - Claim foreign funding without explicit evidence
    - Generate quick answers

    Args:
        request: Funding summary request with resolved candidate.
        adapter: FEC adapter interface for data retrieval.

    Returns:
        FundingSummaryResult with funding data or error status.
    """
    resolution = request.resolution_result

    # Check resolution status
    if resolution is None:
        return FundingSummaryResult(
            status=FundingSummaryStatus.INVALID_REQUEST,
            error_message="Resolution result is required",
            trail_termination_markers=_build_trail_termination_markers(False, False),
        )

    if resolution.status == EntityResolutionStatus.NO_MATCH:
        return FundingSummaryResult(
            status=FundingSummaryStatus.NO_RESOLVED_CANDIDATE,
            error_message="No candidate matched the query",
            trail_termination_markers=_build_trail_termination_markers(False, False),
        )

    if resolution.status == EntityResolutionStatus.MULTIPLE_MATCHES:
        return FundingSummaryResult(
            status=FundingSummaryStatus.AMBIGUOUS_CANDIDATE,
            error_message=resolution.disambiguation_message or "Multiple candidates matched",
            trail_termination_markers=_build_trail_termination_markers(False, False),
        )

    if resolution.status == EntityResolutionStatus.ADAPTER_ERROR:
        return FundingSummaryResult(
            status=FundingSummaryStatus.ADAPTER_ERROR,
            error_message=resolution.error_message or "Adapter error during resolution",
            trail_termination_markers=_build_trail_termination_markers(False, False),
        )

    if resolution.status == EntityResolutionStatus.INVALID_QUERY:
        return FundingSummaryResult(
            status=FundingSummaryStatus.INVALID_REQUEST,
            error_message=resolution.error_message or "Invalid query",
            trail_termination_markers=_build_trail_termination_markers(False, False),
        )

    # Must be EXACT_ONE_MATCH at this point
    if resolution.status != EntityResolutionStatus.EXACT_ONE_MATCH:
        return FundingSummaryResult(
            status=FundingSummaryStatus.INVALID_REQUEST,
            error_message=f"Unexpected resolution status: {resolution.status}",
            trail_termination_markers=_build_trail_termination_markers(False, False),
        )

    if not resolution.candidates:
        return FundingSummaryResult(
            status=FundingSummaryStatus.NO_RESOLVED_CANDIDATE,
            error_message="No candidate in resolution result",
            trail_termination_markers=_build_trail_termination_markers(False, False),
        )

    # Get the resolved candidate
    resolved = resolution.candidates[0]
    candidate = resolved.candidate
    candidate_id = candidate.candidate_id
    candidate_name = candidate.name

    # Get funding summary from adapter
    try:
        summary_result = adapter.get_funding_summary(
            candidate_id=candidate_id,
            cycle=request.cycle,
        )
    except Exception as e:
        return FundingSummaryResult(
            status=FundingSummaryStatus.ADAPTER_ERROR,
            candidate_id=candidate_id,
            candidate_name=candidate_name,
            error_message=f"Adapter error: {str(e)}",
            trail_termination_markers=_build_trail_termination_markers(False, False),
        )

    # Handle adapter errors
    if not summary_result.success:
        error = summary_result.error
        if error and error.error_type == FECErrorType.NOT_FOUND:
            return FundingSummaryResult(
                status=FundingSummaryStatus.NO_FUNDING_DATA,
                candidate_id=candidate_id,
                candidate_name=candidate_name,
                error_message="No funding data found for this candidate",
                trail_termination_markers=_build_trail_termination_markers(False, False),
            )

        if error and error.error_type == FECErrorType.RATE_LIMITED:
            return FundingSummaryResult(
                status=FundingSummaryStatus.ADAPTER_ERROR,
                candidate_id=candidate_id,
                candidate_name=candidate_name,
                error_message=f"Rate limited: {str(error)}",
                trail_termination_markers=_build_trail_termination_markers(False, False),
            )

        if error and error.error_type == FECErrorType.UNAVAILABLE:
            return FundingSummaryResult(
                status=FundingSummaryStatus.ADAPTER_ERROR,
                candidate_id=candidate_id,
                candidate_name=candidate_name,
                error_message="FEC service unavailable",
                trail_termination_markers=_build_trail_termination_markers(False, False),
            )

        error_msg = str(error) if error else "Unknown adapter error"
        return FundingSummaryResult(
            status=FundingSummaryStatus.ADAPTER_ERROR,
            candidate_id=candidate_id,
            candidate_name=candidate_name,
            error_message=error_msg,
            trail_termination_markers=_build_trail_termination_markers(False, False),
        )

    # Extract summary data
    summary: AdapterFundingSummary = summary_result.summary

    if summary is None:
        return FundingSummaryResult(
            status=FundingSummaryStatus.NO_FUNDING_DATA,
            candidate_id=candidate_id,
            candidate_name=candidate_name,
            error_message="No funding summary returned",
            trail_termination_markers=_build_trail_termination_markers(False, False),
        )

    # Get contributions for top sources analysis
    try:
        contrib_result = adapter.get_contributions(
            candidate_id=candidate_id,
            cycle=request.cycle,
            limit=100,  # Get enough for aggregation
        )
    except Exception as e:
        # If contributions fail, we can still use the summary data
        contrib_result = None

    # Build top sources from contributions if available
    top_sources = []
    has_unknown_sources = False

    if contrib_result and contrib_result.success and contrib_result.contributions:
        aggregated = _aggregate_contributions_by_source(contrib_result.contributions)
        has_unknown_sources = "UNKNOWN" in aggregated
        top_sources = _build_top_sources(
            aggregated,
            summary.total_raised,
            request.top_n,
        )
    elif summary.top_contributors:
        # Fall back to summary's top contributors
        for contrib in summary.top_contributors[:request.top_n]:
            amount = contrib.contribution_receipt_amount
            percentage = (amount / summary.total_raised * 100.0) if summary.total_raised > 0 else 0.0
            top_sources.append(
                FundingSourceSummary(
                    source_name=contrib.contributor_name or "UNKNOWN",
                    source_type=contrib.contributor_type or "individual",
                    amount=amount,
                    percentage=round(percentage, 2),
                    confidence=contrib.confidence,
                    source_reference=contrib.source,
                    contribution_count=1,
                    is_aggregated=False,
                )
            )
            if not contrib.contributor_name:
                has_unknown_sources = True

    # Use contributions_by_type from summary or aggregate from contributions
    contributions_by_type = {}
    if summary.contributions_by_type:
        contributions_by_type = dict(summary.contributions_by_type)
    elif contrib_result and contrib_result.success and contrib_result.contributions:
        contributions_by_type = _aggregate_contributions_by_type(contrib_result.contributions)

    # Build result
    return FundingSummaryResult(
        status=FundingSummaryStatus.SUCCESS,
        candidate_id=candidate_id,
        candidate_name=candidate_name,
        total_raised=summary.total_raised,
        total_contributions=summary.total_contributions,
        top_sources=top_sources,
        contributions_by_type=contributions_by_type,
        trail_termination_markers=_build_trail_termination_markers(True, has_unknown_sources),
        reporting_period_start=summary.reporting_period_start,
        reporting_period_end=summary.reporting_period_end,
        source_reference=summary.source,
        confidence=summary.confidence,
    )


# =============================================================================
# Convenience Functions
# =============================================================================


def summarize_by_candidate_id(
    candidate_id: str,
    adapter: FECAdapterInterface,
    cycle: Optional[int] = None,
    top_n: int = 5,
) -> FundingSummaryResult:
    """Convenience function to summarize funding by candidate ID.

    This resolves the candidate by ID first, then generates the funding summary.

    Args:
        candidate_id: FEC candidate ID.
        adapter: FEC adapter interface.
        cycle: Optional election cycle filter.
        top_n: Number of top sources to include.

    Returns:
        FundingSummaryResult.
    """
    from .entity_resolution import resolve_by_id

    resolution = resolve_by_id(candidate_id, adapter)
    request = FundingSummaryRequest(
        resolution_result=resolution,
        cycle=cycle,
        top_n=top_n,
    )
    return summarize_candidate_funding(request, adapter)


def summarize_by_name(
    name: str,
    adapter: FECAdapterInterface,
    state: Optional[str] = None,
    office: Optional[str] = None,
    cycle: Optional[int] = None,
    top_n: int = 5,
) -> FundingSummaryResult:
    """Convenience function to summarize funding by candidate name.

    This resolves the candidate by name first, then generates the funding summary.

    Args:
        name: Candidate name to search.
        adapter: FEC adapter interface.
        state: Optional state hint.
        office: Optional office hint.
        cycle: Optional election cycle filter.
        top_n: Number of top sources to include.

    Returns:
        FundingSummaryResult.
    """
    from .entity_resolution import resolve_by_name

    resolution = resolve_by_name(name, adapter, state=state, office=office)
    request = FundingSummaryRequest(
        resolution_result=resolution,
        cycle=cycle,
        top_n=top_n,
    )
    return summarize_candidate_funding(request, adapter)
