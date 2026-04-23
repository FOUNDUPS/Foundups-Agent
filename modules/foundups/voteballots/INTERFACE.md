# Vote/Ballots FoundUp — Interface Contract

**Version**: 0.1.0  
**Date**: 2026-04-21  
**Status**: Design Specification  

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
