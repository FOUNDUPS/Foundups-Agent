# Vote/Ballots FoundUp — Interface Contract

**Version**: 0.1.0  
**Date**: 2026-04-21  
**Status**: Design Specification  

---

## 2026-11-07 Public Presentation and Oversight Source Contract

The Vote Site exposes `/evidence` and `/contact`; the corresponding source
pages are `evidence.html` and `contact.html`. Evidence records bind the filer,
candidate, recipient, filing, transaction, election designation, amount and
source hash. Verified means the displayed item matches a specific filing.
Unknown covers incomplete totals and unverified or absent coverage. The page
has no live query endpoint or aggregate calculation.

The contact page consumes the same-origin `contact-roster.json`, schema 1,
and filters public Washington offices by manually selected state and chamber.
The page maintains a maximum of 1, 3 or 5 manually chosen contacts in memory.
Only an explicit visitor action opens a `tel:` link. Advance and remove
operate on the displayed list.

Oversight publishes `/accountability.json` (schema 1) and `/llms.txt`.
Its public-release builder stages a reviewed overlay over the pinned
155-file snapshot. Existing professional fragment routes remain supported.
The manifest distinguishes public records, editorial assessment, proposed
institutional mechanisms and published guide materials. It grants no tool or
execution authority.

`/explore` opens the public maps. A node fragment names a screen, and an
`edge-<source>--<target>` fragment names the authority or evidence check between
screens. The browser supports native history and a canonical parent breadcrumb.
`/map-data.json` (schema 1) publishes the same nodes, choice pairs, source links
and optional fictional connection evidence. `/web/explore` has a separate PWA
scope with the same navigation. The map is a read-only reference.

Oversight exposes `/legislative-roadmap` and `/contact`, with `.html` aliases and
equivalent routes under `/web/`. The roadmap is a static staff reference. The
contact page reuses the existing official directory snapshot and validated
telephone formatter. Visitors select a state or opt into a browser-local state
suggestion and confirm it before office numbers appear. Coordinates and optional
voicemail notes stay in page memory. The cached PWA supports manual state lookup
and roadmap reading offline after installation. The contact action is a native
`tel:` link to a listed office.

`web/coalition.html` adds an independent Coalition information and voluntary
application-draft page. `web/coalition-draft.mjs` exposes the pure
`createCoalitionDraft(input, createdAtISO)` validation/export contract. Successful
output remains `DRAFT_NOT_SUBMITTED` and `UNVERIFIED`; it is not an account,
enrollment receipt, ownership proof or role grant. The browser prepares and
downloads the draft without transmitting it or persisting form data. See the
[audit and exact release boundary](docs/COALITION_TAB_AUDIT.md).

`web/` owns Vote's static informational landing/PWA. It publishes no candidate
lookup, scores, ballot submissions or authenticated backend API. Existing
Python funding and shell-payload interfaces remain unchanged.

`oversight/site/` preserves the complete reviewed Oversight Sites source;
`oversight/source-snapshot.json` binds its paths, sizes, hashes and publication
identities. `oversight/scripts/verify_snapshot.py` validates the inventory and
can compare it with the retained Sites checkout. See [the release owner](oversight/README.md).

Oversight belongs to the existing `voteballots` FoundUp. No nested runtime
identity, tenant namespace, token or cross-origin session is created. Public
hostnames are presentation aliases, not authority or confidential-data grants.
The existing `/f/voteballots/app` mount and manifest readiness gates remain.

## 2026-11-01 Implemented Funding-Source Confidence Correction

The existing Python `score_funding_summary_confidence` preserves original labels
and references. For individual funding sources, upstream VERIFIED_FACT requires
`fec_filing`, `state_filing` or `court_record`; other source types cap it at
HIGH_CONFIDENCE_INFERENCE and add `downgraded_from_verified_due_to_indirect_source`.
Lower/UNKNOWN values and approved direct sources are unchanged. A type label is
not source authentication. Aggregate total_raised remained a separate known
provenance gap at this checkpoint; see the correction below. This is not the
planned general claim-verification API.

## 2026-11-01 Aggregate Confidence and Display Correction

Aggregate `total_raised` uses the same existing provenance policy as funding
source items. Missing/indirect VERIFIED inputs cap at HIGH with the existing
downgrade reasons; lower/UNKNOWN values and original references are preserved.
The generic aggregate factor is `aggregate_from_summary`, not a claim that every
input came from FEC records. Source-type eligibility does not authenticate evidence.

The total line uses its unique `total_raised` claim's confidence, never a child
source's confidence. A missing, ambiguous or invalid total label is UNKNOWN.
Answer/shell confidence remains conservative: it cannot exceed either existing
overall confidence or the displayed total claim. Other source labels, review,
trail and line-count rules are unchanged. No public activation or live data access.

## 2026-10-30 Planned Claim-Verification Addendum
The [Political Claim Verification and Scoring Engine](docs/POLITICAL_CLAIM_VERIFICATION_AND_SCORING_ENGINE.md) adds proposed transcript, atomic-claim, evidence-graph, methodological/funding-audit, versioned-assessment, and score-snapshot contracts. Exact API signatures are reserved for the build packet. These are **planned / not implemented** and must not be reported as exports from the current Python v0.6.0 funding pipeline.

Verdict, WSP 97 evidence confidence, context, conflicts, review state, and intent are separate fields. Unknown/uncheckable/pending cases are unscored; every published assessment requires exact source locators and a correction history. The April API below remains design specification, not proof of delivered speech, search, graph, or challenge functionality.

---

## Public API

### Primary Entry Point

```typescript
interface VoteBallotsPipeline {
  /**
   * Main entry: Generate funding transparency report for a candidate.
   * 
   * @param input - Candidate identifier (speech audio or text name)
   * @param options - Pipeline configuration
   * @returns Funding transparency report with confidence labels
   */
  generateReport(
    input: CandidateInput,
    options?: PipelineOptions
  ): Promise<FundingReport>;

  /**
   * Quick lookup: Resolve candidate name without full report.
   */
  resolveCandidate(
    name: string,
    hints?: EntityHints
  ): Promise<CandidateEntity[]>;

  /**
   * Challenge submission: User disputes a claim in a report.
   */
  submitChallenge(
    reportId: string,
    challenge: ChallengeInput
  ): Promise<ChallengeReceipt>;

  /**
   * Status check: Pipeline health and queue state.
   */
  getStatus(): Promise<PipelineStatus>;
}
```

### Input Types

```typescript
type CandidateInput =
  | { type: 'text'; name: string; hints?: EntityHints }
  | { type: 'audio'; blob: Blob; language?: string };

interface EntityHints {
  state?: string;
  office?: string;
  party?: string;
  election_cycle?: number;
  district?: string;
}

interface PipelineOptions {
  investigation_depth?: 'quick' | 'standard' | 'deep';
  include_attack_analysis?: boolean;
  max_trace_depth?: number;
  policy_focus?: string[];
}
```

### Output Types

```typescript
interface FundingReport {
  report_id: string;
  candidate: CandidateEntity;
  generated_at: string;
  
  // Primary outputs
  quick_answer: string;           // Max 3 lines
  plain_summary: string;          // 2-3 paragraphs
  
  // Detailed breakdowns
  evidence_timeline: TimelineEvent[];
  funding_graph: FundingGraphSummary;
  attack_analysis?: AttackAnalysis;
  
  // Source chain
  source_list: SourceWithConfidence[];
  
  // WSP 97 compliance
  confidence_labels: {
    verified_facts: string[];
    high_confidence_inferences: string[];
    low_confidence_inferences: string[];
    unknowns: string[];
  };
  
  // Review flags
  human_review_required: boolean;
  human_review_reasons: string[];
  
  // Provenance
  model_versions: Record<string, string>;
  data_freshness: Record<string, string>;
}

interface FundingGraphSummary {
  total_raised: number;
  total_outside_spending: number;
  dark_money_estimate: { min: number; max: number };
  top_sources: Array<{
    name: string;
    amount: number;
    type: string;
    confidence: ConfidenceLevel;
  }>;
  policy_breakdown: Record<string, number>;
  trail_termination_count: number;
}
```

---

## Hook Interfaces

### Entity Resolution

```typescript
interface EntityResolutionHook {
  resolve(input: EntityResolutionInput): Promise<EntityResolutionOutput>;
  get_by_fec_id(fec_id: string): Promise<CandidateEntity | null>;
  search_by_office(office: string, state: string, cycle: number): Promise<CandidateEntity[]>;
}
```

### Confidence Scoring

```typescript
interface ConfidenceScoringHook {
  score(input: ConfidenceScoringInput): Promise<ConfidenceScoringOutput>;
  apply_rubric(evidence: EvidenceItem, rubric: ConfidenceRubric): ConfidenceLevel;
}
```

### Funding Trace

```typescript
interface FundingTraceHook {
  trace(input: FundingTraceInput): Promise<FundingTraceOutput>;
  identify_policy_links(entity_id: string, policy: string): Promise<PolicyInfluenceAnalysis>;
  detect_shell_structures(committee_id: string): Promise<ShellStructureAnalysis>;
}
```

Full interface definitions: `docs/VOTEBALLOTS_AI_HOOKS_ARCHITECTURE.md`

---

## Events

```typescript
// Emitted events for DAEmon observability (WSP 91)
type VoteBallotsEvent =
  | { type: 'investigation_started'; candidate_id: string; timestamp: string }
  | { type: 'investigation_completed'; report_id: string; duration_ms: number }
  | { type: 'human_review_triggered'; report_id: string; reasons: string[] }
  | { type: 'challenge_received'; challenge_id: string; claim: string }
  | { type: 'api_failure'; api: string; error: string }
  | { type: 'confidence_collapse'; report_id: string; unknown_ratio: number };
```

---

## Error Codes

| Code | Description |
|------|-------------|
| `VB-E001` | Entity resolution failed - no matches |
| `VB-E002` | Entity resolution ambiguous - disambiguation required |
| `VB-E003` | FEC API unavailable |
| `VB-E004` | State database unavailable |
| `VB-E005` | Confidence collapse - too many unknowns |
| `VB-E006` | Human review required - cannot auto-generate |
| `VB-E007` | Model routing failed - all models unavailable |
| `VB-E008` | Challenge submission failed |

---

## Rate Limits

| Operation | Limit | Window |
|-----------|-------|--------|
| generateReport | 10/min | Per user |
| resolveCandidate | 60/min | Per user |
| submitChallenge | 5/hour | Per user |
| API calls to FEC | 1000/hour | Global |

---

## Dependencies

### External APIs

| API | Purpose | Required |
|-----|---------|----------|
| FEC API | Federal campaign finance data | Yes |
| State APIs | State-level filings | Optional |
| Meta Ad Library | Facebook/Instagram political ads | Optional |
| Google Ads Transparency | YouTube/Google political ads | Optional |

### Internal Modules

| Module | Purpose |
|--------|---------|
| `shared_utilities/audio_provider` | Speech-to-text backend |
| `pqn_alignment` | Model routing, confidence scoring |
| `foundups_mcp_bridge` | MCP tool integration |

---

*0102 pArtifact: Interface contract for political transparency pipeline. All outputs labeled with WSP 97 confidence levels.*
