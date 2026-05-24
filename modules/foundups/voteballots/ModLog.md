# Vote/Ballots FoundUp — Module Log

---

## 2026-05-25 — Shell Integration (PoC Phase 1, Slice 6)

**Author**: W6 (0102)
**Slice**: VOTE_POC_SHELL_INTEGRATION_PHASE1
**Branch**: `feat/vote-poc-shell-integration-phase1`
**WSP Compliance**: WSP 00, WSP 15, WSP 50, WSP 64, WSP 83, WSP 87, WSP 97, WSP 104, WSP 22

### Created

- `src/shell_integration.py` — Local shell payload contract (320 lines)
- `tests/test_shell_integration.py` — Unit tests for shell integration (62 tests)

### Shell Payload Features

| Feature | Description |
|---------|-------------|
| LOCAL_SHELL_PAYLOAD_ONLY | Defines payload structure, not shell behavior |
| NO_PUBLIC_LAUNCH | No route activation or public surface changes |
| NO_MANIFEST_MUTATION | foundup_manifest.json unchanged |
| NO_LLM_CALL | Pure data transformation |
| NO_NEW_FACTS | Only repackages existing QuickAnswer data |

### Shell Payload Contract

| Field | Value | Source |
|-------|-------|--------|
| foundup_id | "voteballots" | foundup_manifest.json (readonly) |
| route_namespace | "/f/voteballots" | WSP 104 (readonly) |
| app_mount | "/f/voteballots/app" | Convention (not activated) |
| answer_format | AnswerFormat enum | From QuickAnswer |
| lines | List[str] | Preserved exactly from QuickAnswer |
| confidence_label | ConfidenceLabel | Preserved from QuickAnswer |
| source_trace_id | str | Preserved from QuickAnswer |
| trail_termination_markers | List[str] | Preserved from QuickAnswer |
| human_review_required | bool | Preserved from QuickAnswer |
| human_review_triggers | List[HumanReviewTrigger] | Preserved from QuickAnswer |
| display_ready | bool | From is_answer_ready_for_display() |
| truncated | bool | Preserved from QuickAnswer |
| warnings | List[str] | Generated from answer state |

### Data Types

- `ShellPayloadStatus` — Build operation status enum
- `VoteShellPayload` — Shell payload dataclass with all fields
- `PayloadValidationResult` — Validation result with errors/warnings

### Public API

- `build_vote_shell_payload(answer, format)` — Core payload builder
- `validate_vote_shell_payload(payload)` — Validate payload completeness
- `build_ready_payload(answer)` — Convenience for shell display format
- `is_payload_ready(payload)` — Check if ready for display
- `get_payload_summary(payload)` — Brief status summary

### Safety Boundaries

- LOCAL_SHELL_PAYLOAD_ONLY (data contract, not shell behavior)
- NO_PUBLIC_LAUNCH
- NO_ROUTE_ACTIVATION
- NO_MANIFEST_MUTATION
- NO_REGISTRY_MUTATION
- NO_CATALOG_MUTATION
- NO_PROJECTION_MUTATION
- NO_PFMALL_SHELL_BEHAVIOR_CHANGE
- NO_LLM_CALL
- NO_NEW_FACTS
- ANSWER_LINES_PRESERVED
- CONFIDENCE_LABELS_PRESERVED
- SOURCE_TRACE_PRESERVED
- TRAIL_TERMINATION_MARKERS_PRESERVED
- HUMAN_REVIEW_TRIGGER_PRESERVED
- NO_CANDIDATE_RECOMMENDATION
- NO_TARGETED_PERSUASION
- NO_MICROTARGETING

### Test Coverage

- 62 new tests, all passing
- Total: 303 tests (46 FEC + 70 entity + 42 funding + 37 confidence + 46 quick + 62 shell)
- Covers: ready payload, not-ready payload, foundup_id, route_namespace, app_mount, line preservation, confidence preservation, source trace, trail termination, human review, validation, no public launch, no manifest mutation, no LLM/network, no political safety violations, full pipeline, chain completion

### Updated

- `src/__init__.py` — Added shell integration exports, version bump to 0.6.0

### Audit Document

- `docs/audits/architecture/VOTE_POC_SHELL_INTEGRATION_PHASE1.md`

### Chain Completion Summary

| Slice | PR | Status |
|-------|-----|--------|
| Slice 1: FEC Adapter | #707 | MERGED |
| Slice 2: Entity Resolution | #709 | MERGED |
| Slice 3: Funding Summary | #710 | MERGED |
| Slice 4: Confidence Scoring | #712 | MERGED |
| Slice 5: Quick Answer | #713 | MERGED |
| Slice 6: Shell Integration | This slice | COMPLETE |

**Vote PoC Chain: 6/6 slices complete**

---

## 2026-05-22 — Quick Answer Generation (PoC Phase 1, Slice 5)

**Author**: W6 (0102)
**Slice**: VOTE_POC_QUICK_ANSWER_GENERATION_PHASE1
**Branch**: `feat/vote-poc-quick-answer-generation-phase1`
**WSP Compliance**: WSP 00, WSP 15, WSP 50, WSP 64, WSP 83, WSP 87, WSP 97, WSP 104, WSP 22

### Created

- `src/quick_answer.py` — Template-based quick answer generation (531 lines)
- `tests/test_quick_answer.py` — Unit tests for quick answer generation (46 tests)

### Quick Answer Features

| Feature | Description |
|---------|-------------|
| NO_LLM_CALL | Pure template-based generation, no AI calls |
| NO_NEW_FACTS | Only surfaces existing confidence-scored data |
| MAX_3_LINES_ENFORCED | Truncates with "[more sources - see full report]" |
| Confidence Indicators | [V], [H], [L], [?] for shell display |
| Trail Termination | Preserves and displays termination markers |
| Human Review Flags | Preserves review triggers from Slice 4 |

### Answer Format Options

| Format | Use Case |
|--------|----------|
| PLAIN_TEXT | Default, no formatting markers |
| MARKDOWN | Inline formatting for documentation |
| SHELL_DISPLAY | Compact markers for p.fMALL Vote shell |

### Confidence Indicator Matrix

| Confidence Label | Plain Text | Markdown | Shell |
|------------------|------------|----------|-------|
| VERIFIED_FACT | (verified) | [verified] | [V] |
| HIGH_CONFIDENCE_INFERENCE | (high confidence) | [high] | [H] |
| LOW_CONFIDENCE_INFERENCE | (low confidence) | [low] | [L] |
| UNKNOWN | (unknown) | [?] | [?] |

### Data Types

- `QuickAnswer` — Generated answer with provenance tracking
- `AnswerFormat` — Output format enum (PLAIN_TEXT, MARKDOWN, SHELL_DISPLAY)

### Public API

- `generate_quick_answer(scored_summary, format, max_lines)` — Core generation function
- `generate_shell_answer(scored_summary)` — Convenience for shell display
- `generate_markdown_answer(scored_summary)` — Convenience for markdown
- `is_answer_ready_for_display(answer)` — Check if answer can be displayed without review

### Safety Boundaries

- NO_LLM_CALL (pure template generation)
- NO_NEW_FACTS (only surfaces existing labeled data)
- MAX_3_LINES_ENFORCED (truncates with review note)
- NO_TARGETED_PERSUASION
- NO_CANDIDATE_RECOMMENDATION
- NO_FOREIGN_FUNDING_CLAIM
- NO_DARK_MONEY_AS_VERIFIED_FACT
- HUMAN_REVIEW_FOR_HIGH_RISK_CLAIMS
- TRAIL_TERMINATION_MARKERS_PRESERVED

### Test Coverage

- 46 new tests, all passing
- Total: 241 tests (46 FEC adapter + 70 entity resolution + 42 funding summary + 37 confidence scoring + 46 quick answer)
- Covers: verified fact answers, low confidence uncertainty, truncation enforcement, human review preservation, trail termination display, shell display format, no LLM contract, error handling, convenience functions, data properties, full pipeline, safety boundaries

### Updated

- `src/__init__.py` — Added quick answer exports, version bump to 0.5.0

### Audit Document

- `docs/audits/architecture/VOTE_POC_QUICK_ANSWER_GENERATION_PHASE1.md`

### Carry-Forward Contract for Slice 6

```python
from modules.foundups.voteballots.src import (
    # From Slice 5 (Quick Answer)
    QuickAnswer,
    AnswerFormat,
    generate_quick_answer,
    generate_shell_answer,
    generate_markdown_answer,
    is_answer_ready_for_display,
)
```

### Next Slice

- VOTE_POC_SHELL_INTEGRATION_PHASE1 — Integrate quick answers into p.fMALL Vote shell

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
