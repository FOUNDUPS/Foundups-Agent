"""
FEC API Adapter for VoteBallots FoundUp.

Provides deterministic, mockable boundary for Federal Election Commission data.

Design Principles:
- Offline/mockable by default (no live API in tests)
- No API key required for offline mode
- Structured candidate/contribution records
- Clear error objects for all failure modes
- WSP 97 compliant confidence labeling

Safety Boundaries:
- NO_HALLUCINATED_CANDIDATE_OR_FUNDING_CLAIMS
- NO_LIVE_API_REQUIRED_FOR_TESTS
- NO_API_KEY_REQUIRED_FOR_TESTS
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional


# =============================================================================
# Error Types
# =============================================================================


class FECErrorType(Enum):
    """FEC API error categories."""

    RATE_LIMITED = "rate_limited"
    NOT_FOUND = "not_found"
    AMBIGUOUS = "ambiguous"
    UNAVAILABLE = "unavailable"
    INVALID_REQUEST = "invalid_request"
    NETWORK_ERROR = "network_error"
    PARSE_ERROR = "parse_error"


@dataclass
class FECError:
    """Structured error object for FEC API failures."""

    error_type: FECErrorType
    message: str
    details: Optional[Dict] = None
    retry_after_seconds: Optional[int] = None

    def __str__(self) -> str:
        if self.retry_after_seconds:
            return f"{self.error_type.value}: {self.message} (retry after {self.retry_after_seconds}s)"
        return f"{self.error_type.value}: {self.message}"


# =============================================================================
# Confidence Levels (WSP 97 aligned)
# =============================================================================


class ConfidenceLevel(Enum):
    """WSP 97 confidence classification."""

    VERIFIED_FACT = "verified_fact"
    HIGH_CONFIDENCE_INFERENCE = "high_confidence_inference"
    LOW_CONFIDENCE_INFERENCE = "low_confidence_inference"
    UNKNOWN = "unknown"


# =============================================================================
# Data Types
# =============================================================================


@dataclass
class FECSource:
    """Reference to FEC data source for provenance tracking."""

    source_type: str = "fec_filing"
    url: Optional[str] = None
    filing_id: Optional[str] = None
    accessed_at: Optional[str] = None

    def __post_init__(self):
        if self.accessed_at is None:
            self.accessed_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass
class CandidateRecord:
    """FEC candidate record structure."""

    candidate_id: str
    name: str
    party: Optional[str] = None
    party_full: Optional[str] = None
    state: Optional[str] = None
    district: Optional[str] = None
    office: Optional[str] = None
    office_full: Optional[str] = None
    incumbent_challenge: Optional[str] = None
    election_years: List[int] = field(default_factory=list)
    principal_committees: List[str] = field(default_factory=list)
    has_raised_funds: bool = False
    federal_funds_flag: bool = False
    source: Optional[FECSource] = None

    # Confidence for this record (typically verified_fact from FEC)
    confidence: ConfidenceLevel = ConfidenceLevel.VERIFIED_FACT


@dataclass
class CommitteeRecord:
    """FEC committee record structure."""

    committee_id: str
    name: str
    committee_type: Optional[str] = None
    committee_type_full: Optional[str] = None
    designation: Optional[str] = None
    designation_full: Optional[str] = None
    treasurer_name: Optional[str] = None
    party: Optional[str] = None
    party_full: Optional[str] = None
    state: Optional[str] = None
    candidate_ids: List[str] = field(default_factory=list)
    cycles: List[int] = field(default_factory=list)
    source: Optional[FECSource] = None
    confidence: ConfidenceLevel = ConfidenceLevel.VERIFIED_FACT


@dataclass
class ContributionRecord:
    """Individual contribution record from Schedule A filings."""

    transaction_id: Optional[str] = None
    contributor_name: str = ""
    contributor_type: Optional[str] = None
    contributor_employer: Optional[str] = None
    contributor_occupation: Optional[str] = None
    contributor_city: Optional[str] = None
    contributor_state: Optional[str] = None
    contributor_zip: Optional[str] = None
    contribution_receipt_date: Optional[str] = None
    contribution_receipt_amount: float = 0.0
    committee_id: Optional[str] = None
    committee_name: Optional[str] = None
    candidate_id: Optional[str] = None
    filing_id: Optional[str] = None
    is_individual: bool = True
    source: Optional[FECSource] = None
    confidence: ConfidenceLevel = ConfidenceLevel.VERIFIED_FACT


@dataclass
class FundingSummary:
    """Aggregated funding summary for a candidate or committee."""

    entity_id: str
    entity_name: str
    entity_type: str  # "candidate" or "committee"
    total_raised: float = 0.0
    total_spent: float = 0.0
    cash_on_hand: float = 0.0
    total_contributions: int = 0
    top_contributors: List[ContributionRecord] = field(default_factory=list)
    contributions_by_type: Dict[str, float] = field(default_factory=dict)
    reporting_period_start: Optional[str] = None
    reporting_period_end: Optional[str] = None
    source: Optional[FECSource] = None
    confidence: ConfidenceLevel = ConfidenceLevel.VERIFIED_FACT


# =============================================================================
# Result Types
# =============================================================================


@dataclass
class CandidateSearchResult:
    """Result of candidate search operation."""

    success: bool
    candidates: List[CandidateRecord] = field(default_factory=list)
    error: Optional[FECError] = None

    # Disambiguation fields
    is_ambiguous: bool = False
    disambiguation_required: bool = False
    disambiguation_message: Optional[str] = None

    # Pagination
    total_count: int = 0
    page: int = 1
    per_page: int = 20


@dataclass
class CommitteeSearchResult:
    """Result of committee search operation."""

    success: bool
    committees: List[CommitteeRecord] = field(default_factory=list)
    error: Optional[FECError] = None
    total_count: int = 0


@dataclass
class ContributionSearchResult:
    """Result of contribution search operation."""

    success: bool
    contributions: List[ContributionRecord] = field(default_factory=list)
    error: Optional[FECError] = None
    total_count: int = 0
    total_amount: float = 0.0


@dataclass
class FundingSummaryResult:
    """Result of funding summary operation."""

    success: bool
    summary: Optional[FundingSummary] = None
    error: Optional[FECError] = None


# =============================================================================
# Adapter Interface
# =============================================================================


class FECAdapterInterface(ABC):
    """Abstract interface for FEC data access.

    Implementations:
    - MockFECAdapter: Offline, deterministic testing
    - LiveFECAdapter: Real API access (optional, not default)
    """

    @abstractmethod
    def search_candidates(
        self,
        name: Optional[str] = None,
        state: Optional[str] = None,
        office: Optional[str] = None,
        party: Optional[str] = None,
        cycle: Optional[int] = None,
        candidate_id: Optional[str] = None,
    ) -> CandidateSearchResult:
        """Search for candidates by various criteria."""
        pass

    @abstractmethod
    def get_candidate(self, candidate_id: str) -> CandidateSearchResult:
        """Get a specific candidate by FEC ID."""
        pass

    @abstractmethod
    def search_committees(
        self,
        candidate_id: Optional[str] = None,
        committee_id: Optional[str] = None,
        name: Optional[str] = None,
    ) -> CommitteeSearchResult:
        """Search for committees."""
        pass

    @abstractmethod
    def get_contributions(
        self,
        committee_id: Optional[str] = None,
        candidate_id: Optional[str] = None,
        contributor_name: Optional[str] = None,
        min_amount: Optional[float] = None,
        max_amount: Optional[float] = None,
        cycle: Optional[int] = None,
        limit: int = 100,
    ) -> ContributionSearchResult:
        """Get contribution records."""
        pass

    @abstractmethod
    def get_funding_summary(
        self,
        candidate_id: Optional[str] = None,
        committee_id: Optional[str] = None,
        cycle: Optional[int] = None,
    ) -> FundingSummaryResult:
        """Get aggregated funding summary."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the adapter is operational."""
        pass


# =============================================================================
# Mock Adapter (Default for Testing)
# =============================================================================


class MockFECAdapter(FECAdapterInterface):
    """Mock FEC adapter for offline, deterministic testing.

    Features:
    - No network calls
    - No API key required
    - Deterministic responses from fixtures
    - Simulates error conditions on demand
    """

    def __init__(
        self,
        fixtures_path: Optional[Path] = None,
        simulate_error: Optional[FECErrorType] = None,
    ):
        """Initialize mock adapter.

        Args:
            fixtures_path: Path to fixture data directory
            simulate_error: If set, all calls return this error type
        """
        self._fixtures_path = fixtures_path
        self._simulate_error = simulate_error
        self._fixture_data = self._load_default_fixtures()

        if fixtures_path and fixtures_path.exists():
            self._load_fixtures(fixtures_path)

    def _load_default_fixtures(self) -> Dict:
        """Load built-in test fixtures."""
        return {
            "candidates": {
                # Sample federal candidates for testing
                "H8NY15148": CandidateRecord(
                    candidate_id="H8NY15148",
                    name="OCASIO-CORTEZ, ALEXANDRIA",
                    party="DEM",
                    party_full="Democratic Party",
                    state="NY",
                    district="14",
                    office="H",
                    office_full="House",
                    incumbent_challenge="I",
                    election_years=[2018, 2020, 2022, 2024],
                    principal_committees=["C00639591"],
                    has_raised_funds=True,
                    source=FECSource(
                        url="https://api.open.fec.gov/v1/candidate/H8NY15148/",
                        filing_id="FEC-H8NY15148",
                    ),
                ),
                "P80001571": CandidateRecord(
                    candidate_id="P80001571",
                    name="BIDEN, JOSEPH R JR",
                    party="DEM",
                    party_full="Democratic Party",
                    state="DE",
                    office="P",
                    office_full="President",
                    election_years=[2008, 2020, 2024],
                    principal_committees=["C00703975"],
                    has_raised_funds=True,
                    source=FECSource(
                        url="https://api.open.fec.gov/v1/candidate/P80001571/",
                        filing_id="FEC-P80001571",
                    ),
                ),
                "S4VT00033": CandidateRecord(
                    candidate_id="S4VT00033",
                    name="SANDERS, BERNARD",
                    party="IND",
                    party_full="Independent",
                    state="VT",
                    office="S",
                    office_full="Senate",
                    election_years=[2006, 2012, 2018, 2024],
                    principal_committees=["C00411330"],
                    has_raised_funds=True,
                    source=FECSource(
                        url="https://api.open.fec.gov/v1/candidate/S4VT00033/",
                        filing_id="FEC-S4VT00033",
                    ),
                ),
            },
            "committees": {
                "C00639591": CommitteeRecord(
                    committee_id="C00639591",
                    name="OCASIO-CORTEZ FOR CONGRESS",
                    committee_type="H",
                    committee_type_full="House",
                    designation="P",
                    designation_full="Principal campaign committee",
                    party="DEM",
                    party_full="Democratic Party",
                    state="NY",
                    candidate_ids=["H8NY15148"],
                    cycles=[2018, 2020, 2022, 2024],
                    source=FECSource(
                        url="https://api.open.fec.gov/v1/committee/C00639591/",
                        filing_id="FEC-C00639591",
                    ),
                ),
            },
            "contributions": [
                ContributionRecord(
                    transaction_id="SA11AI.1234",
                    contributor_name="SMITH, JOHN",
                    contributor_type="individual",
                    contributor_employer="TECH COMPANY INC",
                    contributor_occupation="SOFTWARE ENGINEER",
                    contributor_city="NEW YORK",
                    contributor_state="NY",
                    contribution_receipt_date="2024-01-15",
                    contribution_receipt_amount=500.0,
                    committee_id="C00639591",
                    committee_name="OCASIO-CORTEZ FOR CONGRESS",
                    candidate_id="H8NY15148",
                    filing_id="F3-12345",
                    is_individual=True,
                    source=FECSource(
                        filing_id="F3-12345",
                    ),
                ),
                ContributionRecord(
                    transaction_id="SA11AI.1235",
                    contributor_name="JONES, MARY",
                    contributor_type="individual",
                    contributor_employer="UNIVERSITY",
                    contributor_occupation="PROFESSOR",
                    contributor_city="BROOKLYN",
                    contributor_state="NY",
                    contribution_receipt_date="2024-02-01",
                    contribution_receipt_amount=250.0,
                    committee_id="C00639591",
                    committee_name="OCASIO-CORTEZ FOR CONGRESS",
                    candidate_id="H8NY15148",
                    filing_id="F3-12346",
                    is_individual=True,
                    source=FECSource(
                        filing_id="F3-12346",
                    ),
                ),
                ContributionRecord(
                    transaction_id="SA11AI.1236",
                    contributor_name="ACTBLUE",
                    contributor_type="committee",
                    contribution_receipt_date="2024-01-20",
                    contribution_receipt_amount=10000.0,
                    committee_id="C00639591",
                    committee_name="OCASIO-CORTEZ FOR CONGRESS",
                    candidate_id="H8NY15148",
                    filing_id="F3-12347",
                    is_individual=False,
                    source=FECSource(
                        filing_id="F3-12347",
                    ),
                ),
            ],
            "funding_summaries": {
                "H8NY15148": FundingSummary(
                    entity_id="H8NY15148",
                    entity_name="OCASIO-CORTEZ, ALEXANDRIA",
                    entity_type="candidate",
                    total_raised=12500000.0,
                    total_spent=11000000.0,
                    cash_on_hand=1500000.0,
                    total_contributions=150000,
                    contributions_by_type={
                        "individual_small": 8000000.0,
                        "individual_large": 2500000.0,
                        "pac": 500000.0,
                        "committee": 1500000.0,
                    },
                    reporting_period_start="2023-01-01",
                    reporting_period_end="2024-06-30",
                    source=FECSource(
                        url="https://api.open.fec.gov/v1/candidate/H8NY15148/totals/",
                    ),
                ),
            },
        }

    def _load_fixtures(self, fixtures_path: Path) -> None:
        """Load fixtures from JSON files."""
        # Load candidates
        candidates_file = fixtures_path / "candidates.json"
        if candidates_file.exists():
            with open(candidates_file) as f:
                data = json.load(f)
                for cand_data in data.get("candidates", []):
                    record = CandidateRecord(**cand_data)
                    self._fixture_data["candidates"][record.candidate_id] = record

        # Load committees
        committees_file = fixtures_path / "committees.json"
        if committees_file.exists():
            with open(committees_file) as f:
                data = json.load(f)
                for comm_data in data.get("committees", []):
                    record = CommitteeRecord(**comm_data)
                    self._fixture_data["committees"][record.committee_id] = record

        # Load contributions
        contributions_file = fixtures_path / "contributions.json"
        if contributions_file.exists():
            with open(contributions_file) as f:
                data = json.load(f)
                for contrib_data in data.get("contributions", []):
                    record = ContributionRecord(**contrib_data)
                    self._fixture_data["contributions"].append(record)

    def _check_simulated_error(self) -> Optional[FECError]:
        """Check if error simulation is active."""
        if self._simulate_error is None:
            return None

        error_messages = {
            FECErrorType.RATE_LIMITED: "API rate limit exceeded",
            FECErrorType.NOT_FOUND: "Resource not found",
            FECErrorType.AMBIGUOUS: "Multiple matches found, disambiguation required",
            FECErrorType.UNAVAILABLE: "FEC API service unavailable",
            FECErrorType.INVALID_REQUEST: "Invalid request parameters",
            FECErrorType.NETWORK_ERROR: "Network connection failed",
            FECErrorType.PARSE_ERROR: "Failed to parse API response",
        }

        return FECError(
            error_type=self._simulate_error,
            message=error_messages.get(self._simulate_error, "Unknown error"),
            retry_after_seconds=60 if self._simulate_error == FECErrorType.RATE_LIMITED else None,
        )

    def search_candidates(
        self,
        name: Optional[str] = None,
        state: Optional[str] = None,
        office: Optional[str] = None,
        party: Optional[str] = None,
        cycle: Optional[int] = None,
        candidate_id: Optional[str] = None,
    ) -> CandidateSearchResult:
        """Search for candidates in fixture data."""
        error = self._check_simulated_error()
        if error:
            return CandidateSearchResult(success=False, error=error)

        matches: List[CandidateRecord] = []

        for cand in self._fixture_data["candidates"].values():
            # Filter by candidate_id if provided
            if candidate_id and cand.candidate_id != candidate_id:
                continue

            # Filter by name (case-insensitive substring match)
            if name:
                name_upper = name.upper()
                if name_upper not in cand.name.upper():
                    continue

            # Filter by state
            if state and cand.state != state.upper():
                continue

            # Filter by office
            if office and cand.office != office.upper():
                continue

            # Filter by party
            if party and cand.party != party.upper():
                continue

            # Filter by cycle
            if cycle and cycle not in cand.election_years:
                continue

            matches.append(cand)

        # Check for ambiguity
        is_ambiguous = len(matches) > 1 and name is not None

        return CandidateSearchResult(
            success=True,
            candidates=matches,
            total_count=len(matches),
            is_ambiguous=is_ambiguous,
            disambiguation_required=is_ambiguous,
            disambiguation_message=(
                f"Found {len(matches)} candidates matching '{name}'. "
                "Please specify state, office, or full name."
                if is_ambiguous else None
            ),
        )

    def get_candidate(self, candidate_id: str) -> CandidateSearchResult:
        """Get a specific candidate by FEC ID."""
        error = self._check_simulated_error()
        if error:
            return CandidateSearchResult(success=False, error=error)

        candidate = self._fixture_data["candidates"].get(candidate_id)

        if candidate:
            return CandidateSearchResult(
                success=True,
                candidates=[candidate],
                total_count=1,
            )
        else:
            return CandidateSearchResult(
                success=False,
                error=FECError(
                    error_type=FECErrorType.NOT_FOUND,
                    message=f"Candidate {candidate_id} not found",
                ),
            )

    def search_committees(
        self,
        candidate_id: Optional[str] = None,
        committee_id: Optional[str] = None,
        name: Optional[str] = None,
    ) -> CommitteeSearchResult:
        """Search for committees in fixture data."""
        error = self._check_simulated_error()
        if error:
            return CommitteeSearchResult(success=False, error=error)

        matches: List[CommitteeRecord] = []

        for comm in self._fixture_data["committees"].values():
            # Filter by committee_id
            if committee_id and comm.committee_id != committee_id:
                continue

            # Filter by candidate_id
            if candidate_id and candidate_id not in comm.candidate_ids:
                continue

            # Filter by name
            if name and name.upper() not in comm.name.upper():
                continue

            matches.append(comm)

        return CommitteeSearchResult(
            success=True,
            committees=matches,
            total_count=len(matches),
        )

    def get_contributions(
        self,
        committee_id: Optional[str] = None,
        candidate_id: Optional[str] = None,
        contributor_name: Optional[str] = None,
        min_amount: Optional[float] = None,
        max_amount: Optional[float] = None,
        cycle: Optional[int] = None,
        limit: int = 100,
    ) -> ContributionSearchResult:
        """Get contribution records from fixture data."""
        error = self._check_simulated_error()
        if error:
            return ContributionSearchResult(success=False, error=error)

        matches: List[ContributionRecord] = []
        total_amount = 0.0

        for contrib in self._fixture_data["contributions"]:
            # Filter by committee_id
            if committee_id and contrib.committee_id != committee_id:
                continue

            # Filter by candidate_id
            if candidate_id and contrib.candidate_id != candidate_id:
                continue

            # Filter by contributor name
            if contributor_name:
                if contributor_name.upper() not in contrib.contributor_name.upper():
                    continue

            # Filter by amount range
            if min_amount and contrib.contribution_receipt_amount < min_amount:
                continue
            if max_amount and contrib.contribution_receipt_amount > max_amount:
                continue

            matches.append(contrib)
            total_amount += contrib.contribution_receipt_amount

            if len(matches) >= limit:
                break

        return ContributionSearchResult(
            success=True,
            contributions=matches,
            total_count=len(matches),
            total_amount=total_amount,
        )

    def get_funding_summary(
        self,
        candidate_id: Optional[str] = None,
        committee_id: Optional[str] = None,
        cycle: Optional[int] = None,
    ) -> FundingSummaryResult:
        """Get aggregated funding summary from fixture data."""
        error = self._check_simulated_error()
        if error:
            return FundingSummaryResult(success=False, error=error)

        # Try candidate lookup
        if candidate_id:
            summary = self._fixture_data["funding_summaries"].get(candidate_id)
            if summary:
                return FundingSummaryResult(success=True, summary=summary)

        # Try committee lookup (would need additional fixture data)
        if committee_id:
            # Generate summary from contributions
            contributions = self.get_contributions(committee_id=committee_id)
            if contributions.success:
                summary = FundingSummary(
                    entity_id=committee_id,
                    entity_name=committee_id,
                    entity_type="committee",
                    total_raised=contributions.total_amount,
                    total_contributions=contributions.total_count,
                    top_contributors=contributions.contributions[:5],
                    source=FECSource(filing_id=f"generated-{committee_id}"),
                )
                return FundingSummaryResult(success=True, summary=summary)

        return FundingSummaryResult(
            success=False,
            error=FECError(
                error_type=FECErrorType.NOT_FOUND,
                message="No funding summary found for the specified entity",
            ),
        )

    def is_available(self) -> bool:
        """Mock adapter is always available."""
        if self._simulate_error == FECErrorType.UNAVAILABLE:
            return False
        return True


# =============================================================================
# Adapter Factory
# =============================================================================


def create_fec_adapter(
    mode: str = "mock",
    fixtures_path: Optional[Path] = None,
    api_key: Optional[str] = None,
    simulate_error: Optional[FECErrorType] = None,
) -> FECAdapterInterface:
    """Create an FEC adapter instance.

    Args:
        mode: "mock" (default, offline) or "live" (requires api_key)
        fixtures_path: Path to custom fixtures for mock mode
        api_key: FEC API key for live mode (optional, not implemented yet)
        simulate_error: Error type to simulate for testing

    Returns:
        FEC adapter instance

    Note:
        Live mode is not implemented in this PoC phase.
        All tests should use mock mode.
    """
    if mode == "mock":
        return MockFECAdapter(
            fixtures_path=fixtures_path,
            simulate_error=simulate_error,
        )
    elif mode == "live":
        # Live mode not implemented in Phase 1
        raise NotImplementedError(
            "Live FEC API mode is not implemented in PoC Phase 1. "
            "Use mode='mock' for testing."
        )
    else:
        raise ValueError(f"Unknown adapter mode: {mode}. Use 'mock' or 'live'.")


# =============================================================================
# Module-level convenience function
# =============================================================================


def get_mock_adapter() -> MockFECAdapter:
    """Get a mock FEC adapter for testing.

    This is the recommended way to get an adapter for tests.
    No API key or network connection required.
    """
    return MockFECAdapter()
