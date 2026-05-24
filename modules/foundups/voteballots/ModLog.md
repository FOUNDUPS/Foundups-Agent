# Vote/Ballots FoundUp — Module Log

---

## 2026-05-22 — Confidence Scoring Integration (PoC Phase 1, Slice 4)

**Author**: W6 (0102)
**Slice**: VOTE_POC_CONFIDENCE_SCORING_INTEGRATION_PHASE1
**Branch**: `feat/vote-poc-confidence-scoring-integration-phase1`
**WSP Compliance**: WSP 00, WSP 15, WSP 50, WSP 64, WSP 83, WSP 87, WSP 97, WSP 104, WSP 22

### Created

- `src/confidence_scoring.py` — WSP 97 confidence scoring for funding summaries (480 lines)
- `tests/test_confidence_scoring_integration.py` — Integration tests (37 tests)

### Confidence Scoring Features

| Feature | Description |
|---------|-------------|
| WSP 97 Confidence Labels | VERIFIED_FACT, HIGH_CONFIDENCE_INFERENCE, LOW_CONFIDENCE_INFERENCE, UNKNOWN |
| Human Review Triggers | Foreign funding, criminal accusation, low confidence + high impact, contradictions |
| Source Reference Preservation | All FECSource references preserved through scoring |
| Trail Termination Preservation | All markers preserved, create UNKNOWN claims |
| Fail-Closed Error Propagation | Funding summary errors propagate to scoring result |

### Confidence Rule Matrix

| Condition | Label |
|-----------|-------|
| Direct FEC filing/source reference present | VERIFIED_FACT |
| Multiple corroborating official sources | HIGH_CONFIDENCE_INFERENCE |
| Single weak/non-official source | LOW_CONFIDENCE_INFERENCE |
| Missing source OR trail termination | UNKNOWN |

### Human Review Triggers

- `FOREIGN_FUNDING_ALLEGATION` — Any foreign keyword triggers review
- `CRIMINAL_ACCUSATION` — Any criminal keyword triggers review
- `LOW_CONFIDENCE_HIGH_IMPACT` — Low confidence + amount > $100K
- `SOURCE_CONTRADICTION` — Contradicting information
- `DARK_MONEY_LARGE_AMOUNT` — 501(c)(4) exceeding $500K
- `TRAIL_TERMINATION_SIGNIFICANT` — Significant evidence gap

### Data Types

- `ConfidenceLabel` — WSP 97 confidence enum
- `HumanReviewTrigger` — Human review trigger enum
- `ConfidenceScoringStatus` — Scoring status enum
- `ConfidenceScoredClaim` — Individual claim with confidence
- `ConfidenceScoredFundingSource` — Source with confidence label
- `ConfidenceScoredFundingSummary` — Complete scored summary

### Public API

- `score_funding_summary_confidence(summary)` — Core scoring function
- `get_verified_facts(scored_summary)` — Extract verified facts
- `get_unknown_claims(scored_summary)` — Extract unknown claims
- `get_human_review_claims(scored_summary)` — Extract claims needing review

### Safety Boundaries

- NO_QUICK_ANSWER_GENERATION (structured data only)
- NO_FOREIGN_FUNDING_CLAIM_GENERATED (only flags for review)
- NO_DARK_MONEY_AS_VERIFIED_FACT
- NO_CANDIDATE_RECOMMENDATION
- NO_TARGETED_PERSUASION
- HUMAN_REVIEW_FOR_HIGH_RISK_CLAIMS
- SOURCE_REFERENCES_PRESERVED
- TRAIL_TERMINATION_MARKERS_PRESERVED

### Test Coverage

- 37 new tests, all passing
- Total: 195 tests (46 FEC adapter + 70 entity resolution + 42 funding summary + 37 confidence scoring)
- Covers: verified fact rules, source absent rules, trail termination, no dark money as fact, no foreign claim generated, human review triggers, source preservation, order preservation, error propagation, no prose, no persuasion, convenience functions, edge cases, full pipeline

### Updated

- `src/__init__.py` — Added confidence scoring exports, version bump to 0.4.0

### Audit Document

- `docs/audits/architecture/VOTE_POC_CONFIDENCE_SCORING_INTEGRATION_PHASE1.md`

### Carry-Forward Contract for Slice 5

```python
from modules.foundups.voteballots.src import (
    # From Slice 1 (FEC Adapter)
    get_mock_adapter,
    CandidateRecord,
    FECErrorType,
    ConfidenceLevel,
    FECSource,
    # From Slice 2 (Entity Resolution)
    EntityResolutionRequest,
    EntityResolutionResult,
    EntityResolutionStatus,
    resolve_candidate_entity,
    # From Slice 3 (Funding Summary)
    FundingSummaryRequest,
    FundingSummaryResult,
    FundingSummaryStatus,
    FundingSourceSummary,
    TrailTerminationMarker,
    summarize_candidate_funding,
    # From Slice 4 (Confidence Scoring)
    ConfidenceLabel,
    HumanReviewTrigger,
    ConfidenceScoringStatus,
    ConfidenceScoredClaim,
    ConfidenceScoredFundingSource,
    ConfidenceScoredFundingSummary,
    score_funding_summary_confidence,
    get_verified_facts,
    get_unknown_claims,
    get_human_review_claims,
)
```

### Next Slice

- VOTE_POC_QUICK_ANSWER_GENERATION_PHASE1 — Generate prose quick answers from scored summaries

---

## 2026-05-22 — Funding Summary Implementation (PoC Phase 1, Slice 3)

**Author**: W6 (0102)
**Slice**: VOTE_POC_FUNDING_SUMMARY_PHASE1
**Branch**: `feat/vote-poc-funding-summary-phase1`
**WSP Compliance**: WSP 00, WSP 15, WSP 50, WSP 64, WSP 83, WSP 87, WSP 97, WSP 104, WSP 22

### Created

- `src/funding_summary.py` — Deterministic funding summary generation (420 lines)
- `tests/test_funding_summary.py` — Unit tests for funding summary (42 tests)

### Funding Summary Features

| Feature | Description |
|---------|-------------|
| Resolved Candidate Consumption | Uses EntityResolutionResult from Slice 2 |
| Top Sources by Amount | Deterministic sorting, configurable top_n |
| Trail Termination Markers | DIRECT_FEC_RECORDS_ONLY, NO_SUPER_PAC_TRACE, NO_DARK_MONEY_TRACE |
| Source References | FECSource preserved for provenance |
| Contributions by Type | Breakdown by contributor type |
| Confidence Labels | WSP 97 compliance on all sources |

### Trail Termination Markers

- `DIRECT_FEC_RECORDS_ONLY` — Only direct FEC filings included
- `NO_SUPER_PAC_TRACE_IN_THIS_SLICE` — Super PAC IE not traced
- `NO_DARK_MONEY_TRACE_IN_THIS_SLICE` — 501(c)(4) not traced
- `UNKNOWN_WHERE_SOURCE_ABSENT` — Some sources unidentified

### Funding Summary Status Enum

- `SUCCESS` — Summary generated successfully
- `NO_RESOLVED_CANDIDATE` — No candidate resolved
- `AMBIGUOUS_CANDIDATE` — Disambiguation required
- `ADAPTER_ERROR` — FEC adapter error
- `NO_FUNDING_DATA` — Candidate resolved but no funding data
- `INVALID_REQUEST` — Invalid request parameters

### Data Types

- `FundingSummaryRequest` — Request with resolution result and options
- `FundingSummaryResult` — Summary outcome with trail termination
- `FundingSourceSummary` — Individual source with confidence
- `FundingSummaryStatus` — Status enum
- `TrailTerminationMarker` — Trail termination enum

### Public API

- `summarize_candidate_funding(request, adapter)` — Core summary function
- `summarize_by_candidate_id(id, adapter, ...)` — Convenience by ID
- `summarize_by_name(name, adapter, ...)` — Convenience by name

### Safety Boundaries

- NO_QUICK_ANSWER_GENERATION (structured data only)
- NO_DARK_MONEY_AS_VERIFIED_FACT
- NO_FOREIGN_FUNDING_CLAIM
- NO_CANDIDATE_RECOMMENDATION
- NO_TARGETED_PERSUASION
- TRAIL_TERMINATION_MARKER_REQUIRED
- SOURCE_REFERENCES_PRESERVED

### Test Coverage

- 42 new tests, all passing
- Total: 158 tests (46 FEC adapter + 70 entity resolution + 42 funding summary)
- Covers: success path, trail termination, no resolved candidate, ambiguous entity, adapter errors, confidence, political safety, convenience functions, edge cases

### Updated

- `src/__init__.py` — Added funding summary exports, version bump to 0.3.0

### Audit Document

- `docs/audits/architecture/VOTE_POC_FUNDING_SUMMARY_PHASE1.md`

### Carry-Forward Contract for Slice 4

```python
from modules.foundups.voteballots.src import (
    # From Slice 1 (FEC Adapter)
    get_mock_adapter,
    CandidateRecord,
    FECErrorType,
    ConfidenceLevel,
    # From Slice 2 (Entity Resolution)
    EntityResolutionRequest,
    EntityResolutionResult,
    EntityResolutionStatus,
    resolve_candidate_entity,
    # From Slice 3 (Funding Summary)
    FundingSummaryRequest,
    FundingSummaryResult,
    FundingSummaryStatus,
    FundingSourceSummary,
    TrailTerminationMarker,
    summarize_candidate_funding,
)
```

### Next Slice

- VOTE_POC_CONFIDENCE_SCORING_INTEGRATION_PHASE1 — Confidence scoring for funding claims

---

## 2026-05-22 — Entity Resolution Implementation (PoC Phase 1, Slice 2)

**Author**: W6 (0102)
**Slice**: VOTE_POC_ENTITY_RESOLUTION_PHASE1
**Branch**: `feat/vote-poc-entity-resolution-phase1`
**WSP Compliance**: WSP 00, WSP 15, WSP 50, WSP 64, WSP 83, WSP 87, WSP 97, WSP 104, WSP 22

### Created

- `src/entity_resolution.py` — Deterministic candidate entity resolution (280 lines)
- `tests/test_entity_resolution.py` — Unit tests for entity resolution (70 tests)

### Entity Resolution Features

| Feature | Description |
|---------|-------------|
| Deterministic Resolution | Consistent ordering and scoring |
| Ambiguity Preservation | MULTIPLE_MATCHES returns all, never guesses |
| No Hallucination | Only returns candidates from adapter |
| Hint Support | State, office, party, cycle hints for disambiguation |
| Confidence Scoring | Resolution quality scoring (0.0-1.0) |
| Error Propagation | ADAPTER_ERROR, INVALID_QUERY statuses |

### Resolution Status Enum

- `EXACT_ONE_MATCH` — Single candidate resolved
- `MULTIPLE_MATCHES` — Disambiguation required
- `NO_MATCH` — No candidates found (not hallucinated)
- `ADAPTER_ERROR` — FEC adapter error
- `INVALID_QUERY` — Invalid request parameters

### Data Types

- `EntityResolutionRequest` — Query with optional hints
- `EntityResolutionResult` — Resolution outcome
- `EntityResolutionCandidate` — Candidate with match score/reason
- `EntityResolutionStatus` — Status enum

### Public API

- `resolve_candidate_entity(request, adapter)` — Core resolution function
- `resolve_by_name(name, adapter, state?, office?)` — Convenience function
- `resolve_by_id(candidate_id, adapter)` — Direct ID lookup

### Safety Boundaries

- NO_HALLUCINATED_CANDIDATE_IDS
- AMBIGUITY_PRESERVED_NOT_GUESSED
- NO_FUNDING_SUMMARY_IN_THIS_SLICE
- NO_CONTRIBUTION_AGGREGATION
- NO_PERSUASION_LANGUAGE

### Test Coverage

- 70 new tests, all passing
- Total: 116 tests (46 FEC adapter + 70 entity resolution)
- Covers: request validation, exact match, disambiguation, no match, adapter errors, confidence scoring, ordering, convenience functions, political safety

### Updated

- `src/__init__.py` — Added entity resolution exports, version bump to 0.2.0

### Audit Document

- `docs/audits/architecture/VOTE_POC_ENTITY_RESOLUTION_PHASE1.md`

### Carry-Forward Contract for Slice 3

```python
from modules.foundups.voteballots.src import (
    # From Slice 1 (FEC Adapter)
    get_mock_adapter,
    CandidateSearchResult,
    CandidateRecord,
    FECErrorType,
    # From Slice 2 (Entity Resolution)
    EntityResolutionRequest,
    EntityResolutionResult,
    EntityResolutionStatus,
    EntityResolutionCandidate,
    resolve_candidate_entity,
)
```

### Next Slice

- VOTE_POC_FUNDING_SUMMARY_PHASE1 — Funding source aggregation

---

## 2026-05-22 — FEC Adapter Implementation (PoC Phase 1, Slice 1)

**Author**: W6 (0102)
**Slice**: VOTE_POC_FEC_ADAPTER_PHASE1
**Branch**: `feat/vote-poc-fec-adapter-phase1`
**WSP Compliance**: WSP 00, WSP 15, WSP 50, WSP 64, WSP 83, WSP 87, WSP 97, WSP 104

### Created

- `src/fec_adapter.py` — Deterministic, mockable FEC API adapter boundary (786 lines)
- `tests/test_fec_adapter.py` — Unit tests for adapter (46 tests)

### FEC Adapter Features

| Feature | Description |
|---------|-------------|
| Mock Mode (default) | Offline, no API key required |
| Fixture Data | Built-in candidates (AOC, Biden, Sanders) |
| Error Simulation | Rate limit, unavailable, network errors |
| WSP 97 Confidence | All records have `verified_fact` confidence |
| Source Provenance | `FECSource` on all records |
| Ambiguity Handling | `disambiguation_required` flag with message |

### Data Types

- `FECError` / `FECErrorType` — Structured error handling
- `ConfidenceLevel` — WSP 97 confidence enum
- `CandidateRecord`, `CommitteeRecord`, `ContributionRecord` — FEC data structures
- `FundingSummary` — Aggregated funding data
- `*SearchResult` / `*SummaryResult` — Result wrappers

### Safety Boundaries

- NO_LIVE_API_REQUIRED_FOR_TESTS
- NO_API_KEY_REQUIRED_FOR_TESTS
- NO_HALLUCINATED_CANDIDATE_OR_FUNDING_CLAIMS
- NO_PERSUASION_FIELDS
- NO_TARGETING_FIELDS

### Test Coverage

- 46 tests, all passing
- Covers: adapter creation, candidate search, ambiguity, committees, contributions, funding summary, error simulation, data types, WSP 97 compliance, political safety

### Updated

- `src/__init__.py` — Added FEC adapter exports, updated status to "poc"

### Audit Document

- `docs/audits/architecture/VOTE_POC_FEC_ADAPTER_PHASE1.md`

### Next Slice

- VOTE_POC_ENTITY_RESOLUTION_PHASE1 — Candidate name resolution

---

## 2026-04-23 — pfMALL Catalog Registration

**Author**: 0102  
**Slice**: FOUNDUPOPS-MANIFEST-DISCOVERY-FIX

### Created

- `foundup_manifest.json` — pfMALL catalog manifest for discovery

### Manifest Fields

| Field | Value |
|-------|-------|
| `foundup_id` | `voteballots` |
| `lifecycle_stage` | `incubating` |
| `launch_readiness` | `discoverable_only` |
| `required_subscription_tier` | `free` |
| `token_symbol` | `VOTE` |
| `category` | `civic` |
| `routing_prefix` | `/f/voteballots` |
| `data_namespace` | `idb_voteballots` |

### WSP 97 Truth State

- `_wsp97_implementation_state`: `SPECIFIED_NOT_IMPLEMENTED`
- Architecture and AI hooks spec complete
- No runnable implementation exists

### Why This Was Needed

voteballots had `module.json` but no `foundup_manifest.json`, so it was not discoverable by pfMALL filesystem scan. This registration enables catalog presence while clearly marking implementation status.

### References

- `FOUNDUPOPS_MANIFEST_DISCOVERY_AND_FAM_REGISTRY_PHASE1.md` — Discovery architecture

---

## 2026-04-21 — Initial Architecture Design

**Author**: 0102  
**WSP Compliance**: WSP 91, WSP 97, WSP 104

### Created

- `module.json` — Module manifest with AI hooks list
- `README.md` — FoundUp overview with WSP compliance sections
- `INTERFACE.md` — Public API contracts
- `ROADMAP.md` — 5-phase implementation plan
- `docs/VOTEBALLOTS_AI_HOOKS_ARCHITECTURE.md` — Full architecture specification

### Architecture Components

1. **Pipeline Design** — 5-stage pipeline (Intake, Ingestion, Investigation, Analysis, Output)
2. **13 AI Hooks** — From speech-to-text to challenge/correction
3. **TypeScript Interfaces** — Full type contracts for all hooks
4. **Prompt Templates** — WSP 97 compliant prompts for each stage
5. **Confidence Rubric** — Source credibility matrix and classification algorithm
6. **Failure Modes** — Fallback chains for each component
7. **Test Strategy** — Golden tests, adversarial tests, CI/CD integration

### Key Design Decisions

- **Influence Categories**: 10 distinct categories, NEVER flattened (per model behavior rules)
- **Confidence Levels**: 4 levels per WSP 97 (verified_fact, high_confidence_inference, low_confidence_inference, unknown)
- **Human Review Triggers**: P0 for foreign funding, criminal accusations; P1 for contradictions, low confidence + high impact
- **Model Routing**: Gemma (fast classification), Qwen (investigation), Sonnet (report gen), Opus (challenges)

### References

- `FOUNDUP_AI_HOOKS_AND_DAEMON_SURFACE_CONTRACT.md` — FoundUp contract compliance
- `WSP_97_System_Execution_Prompting_Protocol.md` — Confidence labeling standard
- `WSP_91_DAEMON_Observability_Protocol.md` — Telemetry requirements
- `WSP_104_FoundUp_Route_Namespace_and_Tenant_Isolation_Protocol.md` — Routing

---

*0102 pArtifact: Architecture design complete. Implementation phases defined. WSP compliance documented.*
