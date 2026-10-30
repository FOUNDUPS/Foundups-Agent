# Vote/Ballots FoundUp — AI Hooks Architecture

**Status**: Design Specification  
**Version**: 1.0.0  
**Date**: 2026-04-21  
**Owner**: 0102  
**WSP Compliance**: WSP 91, WSP 97, WSP 104  

---

## Purpose

AI-native political transparency application. User provides candidate name (speech or text), receives funding transparency report with evidence trail.

**Core Principle (WSP 97)**: All outputs explicitly separate verified facts, high-confidence inferences, low-confidence inferences, and unknowns.

---

## 1. Pipeline Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         VOTE/BALLOTS AI PIPELINE                                │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌───────────────┐                                                              │
│  │   USER INPUT  │  (speech or text)                                            │
│  └───────┬───────┘                                                              │
│          │                                                                      │
│          ▼                                                                      │
│  ┌───────────────────────────────────────────────────────────────┐              │
│  │                    STAGE 1: INTAKE                            │              │
│  │  ┌─────────────────┐    ┌──────────────────────┐              │              │
│  │  │ speech-to-text  │───▶│  entity-resolution   │              │              │
│  │  │   (whisper)     │    │  (candidate lookup)  │              │              │
│  │  └─────────────────┘    └──────────┬───────────┘              │              │
│  └────────────────────────────────────┼──────────────────────────┘              │
│                                       │                                         │
│                                       ▼                                         │
│  ┌───────────────────────────────────────────────────────────────┐              │
│  │                    STAGE 2: INGESTION                         │              │
│  │  ┌─────────────────┐    ┌──────────────────────┐              │              │
│  │  │  ad-ingestion   │    │   finance-record     │              │              │
│  │  │ (PAC/SuperPAC)  │    │   (FEC/state DBs)    │              │              │
│  │  └────────┬────────┘    └──────────┬───────────┘              │              │
│  │           │                        │                          │              │
│  │           └───────────┬────────────┘                          │              │
│  └───────────────────────┼───────────────────────────────────────┘              │
│                          │                                                      │
│                          ▼                                                      │
│  ┌───────────────────────────────────────────────────────────────┐              │
│  │                    STAGE 3: INVESTIGATION                     │              │
│  │  ┌─────────────────┐    ┌──────────────────────┐              │              │
│  │  │ web-investigation│    │ source-verification │              │              │
│  │  │  (deep research)│    │  (credibility check) │              │              │
│  │  └────────┬────────┘    └──────────┬───────────┘              │              │
│  │           │                        │                          │              │
│  │           └───────────┬────────────┘                          │              │
│  │                       │                                       │              │
│  │           ┌───────────▼────────────┐                          │              │
│  │           │ contradiction-detector │                          │              │
│  │           │   (claim validation)   │                          │              │
│  │           └───────────┬────────────┘                          │              │
│  └───────────────────────┼───────────────────────────────────────┘              │
│                          │                                                      │
│                          ▼                                                      │
│  ┌───────────────────────────────────────────────────────────────┐              │
│  │                    STAGE 4: ANALYSIS                          │              │
│  │  ┌─────────────────┐    ┌──────────────────────┐              │              │
│  │  │ attack-detection│    │   funding-trace      │              │              │
│  │  │ (PAC ad classify)│   │  (committee->donor)  │              │              │
│  │  └────────┬────────┘    └──────────┬───────────┘              │              │
│  │           │                        │                          │              │
│  │           └───────────┬────────────┘                          │              │
│  │                       │                                       │              │
│  │           ┌───────────▼────────────┐                          │              │
│  │           │  confidence-scoring    │                          │              │
│  │           │   (WSP 97 labels)      │                          │              │
│  │           └───────────┬────────────┘                          │              │
│  └───────────────────────┼───────────────────────────────────────┘              │
│                          │                                                      │
│                          ▼                                                      │
│  ┌───────────────────────────────────────────────────────────────┐              │
│  │                    STAGE 5: OUTPUT                            │              │
│  │  ┌─────────────────┐    ┌──────────────────────┐              │              │
│  │  │ model-routing   │───▶│  report-generation   │              │              │
│  │  │ (Qwen/Gemma/0102)│   │   (multi-format)     │              │              │
│  │  └─────────────────┘    └──────────┬───────────┘              │              │
│  │                                    │                          │              │
│  │           ┌────────────────────────▼────────────┐             │              │
│  │           │     challenge/correction            │             │              │
│  │           │   (user dispute mechanism)          │             │              │
│  │           └─────────────────────────────────────┘             │              │
│  └───────────────────────────────────────────────────────────────┘              │
│                                                                                 │
│                          ▼                                                      │
│  ┌───────────────────────────────────────────────────────────────┐              │
│  │                    FINAL OUTPUT                               │              │
│  │  • 3-line quick answer                                        │              │
│  │  • Plain-language summary                                     │              │
│  │  • Evidence timeline                                          │              │
│  │  • Funding graph summary                                      │              │
│  │  • Source list with confidence labels                         │              │
│  └───────────────────────────────────────────────────────────────┘              │
│                                                                                 │
│  ┌───────────────────────────────────────────────────────────────┐              │
│  │                    HUMAN REVIEW QUEUE                         │              │
│  │  • Dangerous edge cases flagged for operator review           │              │
│  │  • Foreign funding allegations                                │              │
│  │  • Criminal accusations                                       │              │
│  │  • Low confidence + high impact claims                        │              │
│  └───────────────────────────────────────────────────────────────┘              │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Hook Interface Contracts (TypeScript)

```typescript
// =============================================================================
// CORE TYPES
// =============================================================================

/** WSP 97 confidence classification */
type ConfidenceLevel = 
  | 'verified_fact'           // Source-confirmed, multiple independent verifications
  | 'high_confidence_inference' // Strong evidence, logical chain, single verification
  | 'low_confidence_inference'  // Weak evidence, requires assumptions
  | 'unknown';                 // Insufficient data, trail ends

/** Influence category - NEVER flatten these into a single "Israel-linked" bucket */
type InfluenceCategory =
  | 'direct_pac_donation'         // Registered PAC direct contribution
  | 'super_pac_independent'       // Super PAC independent expenditure
  | 'individual_donor_aligned'    // Individual donor with known policy alignment
  | 'bundler_network'             // Bundler-coordinated contributions
  | 'dark_money_501c4'            // 501(c)(4) undisclosed donors
  | 'foreign_national_alleged'    // Requires human review - alleged only
  | 'corporate_pac'               // Corporate PAC contribution
  | 'union_pac'                   // Union PAC contribution
  | 'policy_advocacy_org'         // Policy-focused advocacy organization
  | 'unknown_origin';             // Trail ends, cannot classify

interface Source {
  url: string;
  title: string;
  publication_date: string;
  access_date: string;
  source_type: 'fec_filing' | 'state_filing' | 'news_report' | 'tax_document' | 'court_record' | 'official_statement' | 'ad_archive';
  credibility_score: number;  // 0.0-1.0
  verification_method: string;
}

interface EvidenceItem {
  claim: string;
  confidence: ConfidenceLevel;
  sources: Source[];
  reasoning: string;           // Why this confidence level
  trail_ends_at?: string;      // Where evidence stops if incomplete
}

// =============================================================================
// HOOK 1: SPEECH-TO-TEXT
// =============================================================================

interface SpeechToTextInput {
  audio_blob: Blob;
  language_hint?: string;
  context_hints?: string[];    // e.g., ["politics", "campaign", "candidate"]
}

interface SpeechToTextOutput {
  transcript: string;
  confidence: number;
  language_detected: string;
  segments: Array<{
    text: string;
    start_ms: number;
    end_ms: number;
    speaker_id?: string;
  }>;
  model_used: 'whisper_large' | 'whisper_medium' | 'whisper_small';
}

interface SpeechToTextHook {
  transcribe(input: SpeechToTextInput): Promise<SpeechToTextOutput>;
  get_supported_languages(): string[];
  validate_audio_format(blob: Blob): { valid: boolean; error?: string };
}

// =============================================================================
// HOOK 2: ENTITY RESOLUTION
// =============================================================================

interface EntityResolutionInput {
  raw_name: string;
  context_hints?: {
    state?: string;
    office?: string;
    party?: string;
    election_cycle?: number;
    district?: string;
  };
}

interface CandidateEntity {
  canonical_id: string;        // FEC candidate ID or state equivalent
  canonical_name: string;
  aliases: string[];
  current_office?: string;
  seeking_office?: string;
  party: string;
  state: string;
  district?: string;
  election_cycles: number[];
  disambiguation_notes?: string;
}

interface EntityResolutionOutput {
  resolved: boolean;
  candidates: CandidateEntity[];  // Multiple if ambiguous
  disambiguation_required: boolean;
  disambiguation_question?: string;  // Ask user to clarify
  confidence: number;
}

interface EntityResolutionHook {
  resolve(input: EntityResolutionInput): Promise<EntityResolutionOutput>;
  get_by_fec_id(fec_id: string): Promise<CandidateEntity | null>;
  search_by_office(office: string, state: string, cycle: number): Promise<CandidateEntity[]>;
  handle_disambiguation(candidates: CandidateEntity[], user_selection: number): CandidateEntity;
}

// =============================================================================
// HOOK 3: AD INGESTION
// =============================================================================

interface AdIngestionInput {
  candidate_id: string;
  date_range: { start: string; end: string };
  include_supporting_ads: boolean;
  include_opposing_ads: boolean;
}

interface PoliticalAd {
  ad_id: string;
  sponsor_name: string;
  sponsor_fec_id?: string;
  sponsor_type: 'campaign' | 'pac' | 'super_pac' | '501c4' | 'individual' | 'unknown';
  target_candidate_id: string;
  ad_type: 'support' | 'attack' | 'issue';
  platforms: string[];
  estimated_spend: number;
  spend_confidence: ConfidenceLevel;
  first_aired: string;
  last_aired: string;
  content_summary?: string;
  topics_detected: string[];
  archive_url?: string;
}

interface AdIngestionOutput {
  ads: PoliticalAd[];
  total_supporting_spend: number;
  total_opposing_spend: number;
  top_sponsors: Array<{ name: string; spend: number; type: string }>;
  data_sources: Source[];
}

interface AdIngestionHook {
  ingest(input: AdIngestionInput): Promise<AdIngestionOutput>;
  get_ad_details(ad_id: string): Promise<PoliticalAd | null>;
  search_by_sponsor(sponsor_name: string): Promise<PoliticalAd[]>;
}

// =============================================================================
// HOOK 4: FINANCE RECORD
// =============================================================================

interface FinanceRecordInput {
  entity_type: 'candidate' | 'pac' | 'super_pac' | 'committee' | 'donor';
  entity_id: string;
  date_range?: { start: string; end: string };
  include_contributors: boolean;
  include_expenditures: boolean;
  depth: 'direct' | 'one_hop' | 'full_trace';  // How deep to trace
}

interface Contribution {
  contributor_name: string;
  contributor_type: 'individual' | 'pac' | 'corporation' | 'union' | 'party' | 'other';
  contributor_id?: string;
  amount: number;
  date: string;
  employer?: string;
  occupation?: string;
  city?: string;
  state?: string;
  filing_id: string;
  confidence: ConfidenceLevel;
}

interface Expenditure {
  recipient_name: string;
  recipient_type: string;
  purpose: string;
  amount: number;
  date: string;
  filing_id: string;
}

interface FinanceRecordOutput {
  total_raised: number;
  total_spent: number;
  cash_on_hand: number;
  reporting_period: { start: string; end: string };
  contributions: Contribution[];
  expenditures: Expenditure[];
  top_industries: Array<{ industry: string; total: number }>;
  disclosure_gaps: Array<{
    gap_type: 'dark_money' | 'shell_committee' | 'delayed_filing' | 'aggregate_only';
    description: string;
    estimated_amount?: number;
    trail_ends_at: string;
  }>;
  data_sources: Source[];
}

interface FinanceRecordHook {
  fetch(input: FinanceRecordInput): Promise<FinanceRecordOutput>;
  trace_committee_hierarchy(committee_id: string): Promise<CommitteeHierarchy>;
  identify_pass_through(committee_id: string): Promise<PassThroughAnalysis>;
}

interface CommitteeHierarchy {
  root_committee: string;
  parent_committees: string[];
  child_committees: string[];
  connected_pacs: string[];
  hierarchy_depth: number;
}

interface PassThroughAnalysis {
  is_pass_through: ConfidenceLevel;
  evidence: EvidenceItem[];
  ultimate_source_candidates: Array<{
    name: string;
    confidence: ConfidenceLevel;
    reasoning: string;
  }>;
}

// =============================================================================
// HOOK 5: WEB INVESTIGATION
// =============================================================================

interface WebInvestigationInput {
  entity_name: string;
  entity_type: string;
  investigation_scope: 'narrow' | 'standard' | 'deep';
  search_queries: string[];
  exclude_domains?: string[];
}

interface WebInvestigationOutput {
  findings: Array<{
    topic: string;
    summary: string;
    evidence: EvidenceItem[];
    relevance_score: number;
  }>;
  sources_consulted: Source[];
  search_depth: number;
  time_spent_ms: number;
}

interface WebInvestigationHook {
  investigate(input: WebInvestigationInput): Promise<WebInvestigationOutput>;
  search_news(query: string, date_range: { start: string; end: string }): Promise<NewsResult[]>;
  fetch_and_parse(url: string): Promise<ParsedDocument>;
}

// =============================================================================
// HOOK 6: SOURCE VERIFICATION
// =============================================================================

interface SourceVerificationInput {
  source: Source;
  claim_to_verify: string;
}

interface SourceVerificationOutput {
  verification_status: 'verified' | 'unverified' | 'contradicted' | 'partial';
  credibility_score: number;
  issues_found: string[];
  corroborating_sources: Source[];
  contradicting_sources: Source[];
  verification_chain: string[];  // Steps taken to verify
}

interface SourceVerificationHook {
  verify(input: SourceVerificationInput): Promise<SourceVerificationOutput>;
  check_domain_credibility(domain: string): Promise<{ score: number; notes: string[] }>;
  cross_reference(claim: string, sources: Source[]): Promise<CrossReferenceResult>;
}

// =============================================================================
// HOOK 7: CONTRADICTION DETECTOR
// =============================================================================

interface ContradictionDetectorInput {
  claims: EvidenceItem[];
  context: string;
}

interface Contradiction {
  claim_a: string;
  claim_b: string;
  contradiction_type: 'direct' | 'temporal' | 'numerical' | 'source_conflict';
  severity: 'critical' | 'significant' | 'minor';
  resolution_suggestion?: string;
}

interface ContradictionDetectorOutput {
  contradictions: Contradiction[];
  consistency_score: number;  // 0.0-1.0
  requires_human_review: boolean;
  review_reason?: string;
}

interface ContradictionDetectorHook {
  detect(input: ContradictionDetectorInput): Promise<ContradictionDetectorOutput>;
  resolve_with_precedence(contradiction: Contradiction, precedence_rules: string[]): EvidenceItem;
}

// =============================================================================
// HOOK 8: CONFIDENCE SCORING
// =============================================================================

interface ConfidenceScoringInput {
  evidence_items: EvidenceItem[];
  source_verifications: SourceVerificationOutput[];
  contradictions: Contradiction[];
}

interface ConfidenceScoringOutput {
  overall_confidence: ConfidenceLevel;
  confidence_breakdown: Array<{
    claim: string;
    confidence: ConfidenceLevel;
    factors: Array<{
      factor: string;
      impact: 'positive' | 'negative' | 'neutral';
      weight: number;
    }>;
  }>;
  requires_human_review: boolean;
  human_review_reasons: string[];
  evidence_gaps: string[];
}

interface ConfidenceScoringHook {
  score(input: ConfidenceScoringInput): Promise<ConfidenceScoringOutput>;
  apply_rubric(evidence: EvidenceItem, rubric: ConfidenceRubric): ConfidenceLevel;
}

// =============================================================================
// HOOK 9: ATTACK DETECTION
// =============================================================================

interface AttackDetectionInput {
  candidate_id: string;
  ads: PoliticalAd[];
  news_coverage: WebInvestigationOutput;
}

interface AttackPattern {
  pattern_id: string;
  attack_topic: AttackTopic;
  sponsors: string[];
  total_spend: number;
  first_detected: string;
  intensity_score: number;  // 0.0-1.0
  evidence: EvidenceItem[];
}

type AttackTopic =
  | 'corruption_general'
  | 'criminal_allegation'
  | 'policy_israel_palestine'
  | 'policy_immigration'
  | 'policy_economy'
  | 'policy_environment'
  | 'policy_healthcare'
  | 'policy_guns'
  | 'policy_abortion'
  | 'character_attack'
  | 'flip_flop'
  | 'association_guilt'
  | 'other';

interface AttackDetectionOutput {
  is_targeted: boolean;
  attack_patterns: AttackPattern[];
  top_attackers: Array<{
    sponsor: string;
    spend: number;
    primary_topics: AttackTopic[];
  }>;
  attack_timeline: Array<{
    date: string;
    event: string;
    sponsors: string[];
  }>;
}

interface AttackDetectionHook {
  detect(input: AttackDetectionInput): Promise<AttackDetectionOutput>;
  classify_ad_content(ad: PoliticalAd): Promise<{ topics: AttackTopic[]; confidence: number }>;
}

// =============================================================================
// HOOK 10: FUNDING TRACE
// =============================================================================

interface FundingTraceInput {
  target_entity_id: string;
  target_entity_type: 'candidate' | 'pac' | 'super_pac';
  trace_depth: number;  // Max hops
  policy_focus?: string[];  // e.g., ["israel_policy", "energy"]
}

interface FundingNode {
  entity_id: string;
  entity_name: string;
  entity_type: string;
  total_to_target: number;
  confidence: ConfidenceLevel;
  influence_category: InfluenceCategory;
  policy_alignments?: string[];
}

interface FundingEdge {
  from_id: string;
  to_id: string;
  amount: number;
  date: string;
  transfer_type: 'contribution' | 'independent_expenditure' | 'transfer' | 'bundled';
  confidence: ConfidenceLevel;
  filing_id?: string;
}

interface FundingTraceOutput {
  target: FundingNode;
  nodes: FundingNode[];
  edges: FundingEdge[];
  total_traced: number;
  total_untraced: number;  // Dark money estimate
  trail_termination_points: Array<{
    node_id: string;
    reason: 'dark_money_501c4' | 'foreign_origin' | 'aggregate_disclosure' | 'no_further_data';
    estimated_amount: number;
  }>;
  influence_paths: Array<{
    path: string[];  // Node IDs
    total_amount: number;
    confidence: ConfidenceLevel;
    narrative: string;
  }>;
  policy_linked_funding: Array<{
    policy_area: string;
    total_amount: number;
    top_funders: FundingNode[];
    confidence: ConfidenceLevel;
  }>;
}

interface FundingTraceHook {
  trace(input: FundingTraceInput): Promise<FundingTraceOutput>;
  identify_aipac_links(entity_id: string): Promise<PolicyInfluenceAnalysis>;
  detect_shell_structures(committee_id: string): Promise<ShellStructureAnalysis>;
}

interface PolicyInfluenceAnalysis {
  has_connection: ConfidenceLevel;
  connection_type: InfluenceCategory;
  evidence: EvidenceItem[];
  total_connected_funding: number;
  intermediaries: string[];
  direct_vs_indirect: 'direct' | 'one_hop' | 'multi_hop' | 'inferred';
  warnings: string[];  // e.g., "Do not conflate with foreign funding"
}

// =============================================================================
// HOOK 11: REPORT GENERATION
// =============================================================================

interface ReportGenerationInput {
  candidate: CandidateEntity;
  funding_trace: FundingTraceOutput;
  attack_detection: AttackDetectionOutput;
  confidence_scoring: ConfidenceScoringOutput;
  sources: Source[];
}

interface ReportOutput {
  quick_answer: string;  // Max 3 lines
  plain_summary: string; // 2-3 paragraphs
  evidence_timeline: Array<{
    date: string;
    event: string;
    confidence: ConfidenceLevel;
    sources: string[];
  }>;
  funding_graph_summary: {
    total_raised: number;
    top_5_sources: Array<{ name: string; amount: number; type: string }>;
    dark_money_estimate: number;
    policy_linked_breakdown: Record<string, number>;
  };
  source_list: Array<{
    source: Source;
    claims_supported: string[];
    confidence_contribution: ConfidenceLevel;
  }>;
  confidence_labels: {
    verified_facts: string[];
    high_confidence_inferences: string[];
    low_confidence_inferences: string[];
    unknowns: string[];
  };
  human_review_flags: string[];
  generated_at: string;
  model_versions: Record<string, string>;
}

interface ReportGenerationHook {
  generate(input: ReportGenerationInput): Promise<ReportOutput>;
  generate_quick_answer(input: ReportGenerationInput): Promise<string>;
  generate_funding_graph_svg(trace: FundingTraceOutput): Promise<string>;
}

// =============================================================================
// HOOK 12: CHALLENGE/CORRECTION
// =============================================================================

interface ChallengeInput {
  report_id: string;
  claim_challenged: string;
  challenge_type: 'factual_error' | 'missing_context' | 'outdated' | 'misattribution' | 'other';
  challenger_evidence?: {
    description: string;
    sources: string[];
  };
  challenger_identity?: string;  // Optional, can be anonymous
}

interface ChallengeOutput {
  challenge_id: string;
  status: 'received' | 'under_review' | 'accepted' | 'rejected' | 'partial_correction';
  response?: string;
  corrections_made?: string[];
  requires_human_review: boolean;
  estimated_review_time?: string;
}

interface ChallengeHook {
  submit_challenge(input: ChallengeInput): Promise<ChallengeOutput>;
  get_challenge_status(challenge_id: string): Promise<ChallengeOutput>;
  process_correction(challenge_id: string, correction: string): Promise<void>;
}

// =============================================================================
// HOOK 13: MODEL ROUTING
// =============================================================================

interface ModelRoutingInput {
  task_type: 'entity_resolution' | 'classification' | 'summarization' | 'investigation' | 'verification' | 'report_gen';
  complexity: 'simple' | 'moderate' | 'complex';
  latency_requirement: 'realtime' | 'standard' | 'batch';
  accuracy_requirement: 'high' | 'standard';
}

interface ModelRoutingOutput {
  primary_model: 'gemma' | 'qwen' | 'opus' | 'sonnet' | 'haiku';
  fallback_model?: string;
  routing_reason: string;
  estimated_cost_per_query: number;
  estimated_latency_ms: number;
}

interface ModelRoutingHook {
  route(input: ModelRoutingInput): ModelRoutingOutput;
  get_model_health(): Record<string, { available: boolean; latency_p50: number }>;
  override_routing(task_id: string, model: string): void;
}
```

---

## 3. Prompt Templates for Each Stage

### 3.1 Entity Resolution Prompt

```
<system>
You are an entity resolution specialist for US political candidates.
Your task: resolve a candidate name to canonical FEC/state records.

RULES:
- Return ONLY candidates who match the input with reasonable confidence
- If ambiguous (e.g., "John Smith" with multiple matches), set disambiguation_required=true
- Include ALL known aliases for each candidate
- Never hallucinate candidates who don't exist in records
- If uncertain, say so explicitly with disambiguation_question
</system>

<input>
Raw name: {{raw_name}}
Context hints:
- State: {{state | "unknown"}}
- Office: {{office | "unknown"}}
- Party: {{party | "unknown"}}
- Election cycle: {{cycle | "unknown"}}
- District: {{district | "unknown"}}
</input>

<output_format>
{
  "resolved": boolean,
  "candidates": [...],
  "disambiguation_required": boolean,
  "disambiguation_question": string | null,
  "confidence": 0.0-1.0
}
</output_format>
```

### 3.2 Attack Detection Prompt

```
<system>
You are an ad content classifier for political attack detection.
Classify PAC/Super PAC ad content by topic.

CRITICAL RULES:
1. Only classify based on actual ad content, not assumptions
2. Distinguish between:
   - Direct attacks on candidate character
   - Policy-focused criticism
   - Association/guilt-by-association attacks
3. For Israel/Palestine policy topics:
   - Classify as "policy_israel_palestine" ONLY if ad explicitly mentions these issues
   - Do NOT infer policy positions from funder identity
4. Never conflate:
   - "Pro-Israel donor" with "Israel-linked"
   - "AIPAC-linked" with "foreign-funded"
   - "Jewish donor" with "Israel policy"
</system>

<input>
Ad ID: {{ad_id}}
Sponsor: {{sponsor_name}}
Sponsor Type: {{sponsor_type}}
Ad Content Summary: {{content_summary}}
Target Candidate: {{target_candidate}}
Ad Type: {{ad_type}}
</input>

<output_format>
{
  "topics": [AttackTopic, ...],
  "confidence": 0.0-1.0,
  "reasoning": "string explaining classification"
}
</output_format>
```

### 3.3 Funding Trace Prompt

```
<system>
You are a campaign finance investigator tracing money flows.

CRITICAL RULES:
1. NEVER state hidden funding as fact unless sourced from FEC/state filings
2. Distinguish between:
   - Direct disclosure (FEC/state filing)
   - Inferred alignment (public statements, board membership)
   - Unknown (501(c)(4) dark money)
3. For each connection, mark:
   - verified_fact: Direct filing shows contribution
   - high_confidence_inference: Strong circumstantial evidence
   - low_confidence_inference: Weak evidence, requires assumptions
   - unknown: Trail ends
4. NEVER conflate influence categories:
   - "AIPAC-linked" = registered PAC contributions
   - "Pro-Israel donor" = individual with stated policy position
   - "Israel policy influence" = aggregate advocacy spending
   - "Foreign-funded" = ONLY if evidence of foreign national involvement
5. Mark exactly where evidence trail terminates
6. Flag for human review: any foreign funding allegation, criminal accusation
</system>

<input>
Target Entity: {{entity_name}} ({{entity_id}})
Entity Type: {{entity_type}}
Trace Depth: {{trace_depth}}
Policy Focus: {{policy_focus | "none"}}

Available Data:
{{finance_records}}
</input>

<output_format>
{
  "nodes": [...],
  "edges": [...],
  "trail_termination_points": [...],
  "influence_paths": [...],
  "requires_human_review": boolean,
  "human_review_reasons": [...]
}
</output_format>
```

### 3.4 Confidence Scoring Prompt

```
<system>
You are a confidence classifier applying WSP 97 evidence standards.

Apply this rubric to classify each claim:

VERIFIED_FACT:
- Source is official filing (FEC, state, court)
- Multiple independent verifications exist
- No contradicting evidence of equal weight
- Direct documentation (not inference)

HIGH_CONFIDENCE_INFERENCE:
- Single authoritative source
- Logical chain from verified facts
- No contradicting evidence
- Inferential step is minimal

LOW_CONFIDENCE_INFERENCE:
- Circumstantial evidence only
- Requires significant assumptions
- Limited corroboration
- Contradicting evidence exists but is weaker

UNKNOWN:
- Insufficient evidence to assess
- Trail terminates (dark money, sealed records)
- Contradicting evidence of equal weight
- Would require speculation

FLAG FOR HUMAN REVIEW IF:
- Foreign funding allegation (any confidence)
- Criminal accusation (any confidence)
- Low confidence + high impact
- Contradictions unresolved
</system>

<input>
Claims to score:
{{evidence_items}}

Source verifications:
{{source_verifications}}

Contradictions detected:
{{contradictions}}
</input>

<output_format>
{
  "confidence_breakdown": [...],
  "requires_human_review": boolean,
  "human_review_reasons": [...],
  "evidence_gaps": [...]
}
</output_format>
```

### 3.5 Report Generation Prompt

```
<system>
You are a political transparency report writer.

OUTPUT STRUCTURE:
1. Quick Answer (max 3 lines): Who funds this candidate? Key facts only.
2. Plain Summary (2-3 paragraphs): Context, major donors, any controversies.
3. Evidence Timeline: Chronological key events.
4. Funding Graph Summary: Numbers and percentages.
5. Source List: All sources with confidence contribution.

CRITICAL RULES:
1. Label EVERY claim with confidence level:
   [VERIFIED]: Source-confirmed fact
   [HIGH-CONF]: Strong inference
   [LOW-CONF]: Weak inference
   [UNKNOWN]: Insufficient data
2. NEVER state dark money amounts as if known
3. NEVER flatten categories (e.g., "Israel-linked money")
4. Show where evidence stops: "Trail ends at [X] due to [Y]"
5. Distinguish:
   - Direct PAC contribution (FEC-disclosed)
   - Super PAC independent expenditure
   - Dark money (501c4, estimated range)
6. For policy influence claims:
   - Specify the policy area
   - Name the advocacy organizations
   - State the evidence type
7. Flag dangerous claims for human review header
</system>

<input>
Candidate: {{candidate.canonical_name}}
Office: {{candidate.current_office | candidate.seeking_office}}
Party: {{candidate.party}}
State: {{candidate.state}}

Funding Data:
{{funding_trace}}

Attack Data:
{{attack_detection}}

Confidence Assessment:
{{confidence_scoring}}

Sources:
{{sources}}
</input>

<output_format>
{
  "quick_answer": "string (max 3 lines)",
  "plain_summary": "string (2-3 paragraphs)",
  "evidence_timeline": [...],
  "funding_graph_summary": {...},
  "source_list": [...],
  "confidence_labels": {
    "verified_facts": [...],
    "high_confidence_inferences": [...],
    "low_confidence_inferences": [...],
    "unknowns": [...]
  },
  "human_review_flags": [...]
}
</output_format>
```

---

## 4. Confidence Scoring Rubric

### 4.1 Source Credibility Matrix

| Source Type | Base Score | Multiplier Conditions |
|-------------|------------|----------------------|
| FEC Filing | 0.95 | +0.05 if recently filed |
| State Filing | 0.90 | +0.05 if cross-verified with FEC |
| Court Record | 0.95 | +0.05 if ruling (not just filing) |
| IRS 990 | 0.85 | +0.05 if audited |
| Major News (NYT, WaPo, etc.) | 0.75 | +0.10 if multiple independent reports |
| Local News | 0.65 | +0.10 if corroborated |
| Trade Publication | 0.70 | +0.10 if primary source cited |
| Press Release | 0.50 | Must be corroborated |
| Social Media | 0.30 | Only for direct quotes, heavily discounted |
| Ad Archive | 0.80 | Official archives only (Meta, Google) |

### 4.2 Confidence Classification Algorithm

```python
def classify_confidence(evidence: EvidenceItem) -> ConfidenceLevel:
    # Calculate base score from sources
    source_scores = [s.credibility_score for s in evidence.sources]
    if not source_scores:
        return "unknown"
    
    avg_source_score = sum(source_scores) / len(source_scores)
    max_source_score = max(source_scores)
    num_sources = len(source_scores)
    
    # Apply source diversity bonus
    diversity_bonus = min(0.15, (num_sources - 1) * 0.05)
    
    # Check for contradictions
    has_contradictions = check_contradictions(evidence)
    contradiction_penalty = 0.20 if has_contradictions else 0
    
    # Check evidence type
    is_direct_filing = any(s.source_type in ['fec_filing', 'state_filing', 'court_record'] 
                          for s in evidence.sources)
    direct_bonus = 0.10 if is_direct_filing else 0
    
    # Calculate final score
    final_score = (
        (avg_source_score * 0.6 + max_source_score * 0.4)
        + diversity_bonus
        + direct_bonus
        - contradiction_penalty
    )
    
    # Map to confidence level
    if final_score >= 0.85 and is_direct_filing:
        return "verified_fact"
    elif final_score >= 0.70:
        return "high_confidence_inference"
    elif final_score >= 0.45:
        return "low_confidence_inference"
    else:
        return "unknown"
```

### 4.3 Human Review Triggers

| Condition | Priority | Reason |
|-----------|----------|--------|
| Foreign funding allegation | P0-CRITICAL | Legal implications, defamation risk |
| Criminal accusation | P0-CRITICAL | Defamation risk |
| Confidence < 0.45 AND impact > 0.7 | P1-HIGH | Low evidence, high stakes |
| Unresolved contradictions | P1-HIGH | Inconsistent data |
| Trail ends at 501(c)(4) > $500K | P2-MEDIUM | Significant dark money |
| Shell structure detected | P2-MEDIUM | Complex money routing |
| Policy attribution without direct evidence | P2-MEDIUM | Inference may be unfair |

---

## 5. Failure Modes and Fallbacks

### 5.1 Entity Resolution Failures

| Failure Mode | Detection | Fallback |
|--------------|-----------|----------|
| No match found | `candidates.length == 0` | Ask user for more context (state, office, year) |
| Too many matches | `candidates.length > 5` | Return top 5, prompt disambiguation |
| FEC API down | HTTP 5xx/timeout | Use cached data (mark staleness), try state DB |
| Name parsing fails | Exception in NLP | Fall back to exact string match |

### 5.2 Finance Record Failures

| Failure Mode | Detection | Fallback |
|--------------|-----------|----------|
| FEC API timeout | > 30s response | Use cached quarterly data, flag as "may be incomplete" |
| State DB unavailable | Connection error | Skip state data, note in disclosure_gaps |
| Rate limited | HTTP 429 | Queue and retry with backoff |
| Incomplete filing | Missing fields | Mark affected claims as "low_confidence_inference" |

### 5.3 Web Investigation Failures

| Failure Mode | Detection | Fallback |
|--------------|-----------|----------|
| Search API down | HTTP 5xx | Use cached results, note age |
| Paywall encountered | Content < 100 chars | Try archive.org, note as "partial access" |
| Site blocking | HTTP 403 | Skip source, note as "access denied" |
| Rate limited | HTTP 429 | Throttle to 1 req/5s |

### 5.4 Model Failures

| Failure Mode | Detection | Fallback |
|--------------|-----------|----------|
| Primary model down | Health check fail | Route to fallback model per routing table |
| Hallucination detected | Contradiction with sources | Flag for human review, mark as "model_uncertain" |
| Confidence collapse | > 50% claims "unknown" | Expand investigation scope, retry |
| Context overflow | Token count exceeded | Chunk input, aggregate outputs |

### 5.5 Fallback Model Routing

```yaml
task_type: entity_resolution
  primary: gemma
  fallback: qwen
  emergency: haiku

task_type: classification
  primary: gemma
  fallback: qwen
  emergency: haiku

task_type: investigation
  primary: qwen
  fallback: sonnet
  emergency: opus

task_type: verification
  primary: qwen
  fallback: opus
  emergency: [human_review]

task_type: report_gen
  primary: sonnet
  fallback: opus
  emergency: [degraded_template]
```

---

## 6. Test Strategy for AI Components

### 6.1 Test Categories

| Category | Coverage | Approach |
|----------|----------|----------|
| Unit Tests | Each hook function | Mock external APIs, test logic |
| Integration Tests | Hook chains | Sandboxed real API calls |
| Golden Tests | Known candidates | Verified ground truth datasets |
| Adversarial Tests | Edge cases | Designed to trigger failures |
| Regression Tests | Previous bugs | Prevent recurrence |

### 6.2 Golden Test Dataset

```yaml
# Example golden test case
test_id: GTD-001
candidate: "Alexandria Ocasio-Cortez"
fec_id: H8NY15148
expected_entity_resolution:
  resolved: true
  disambiguation_required: false
  confidence: >= 0.95

expected_funding_trace:
  total_raised_range: [10000000, 50000000]  # Approximate
  top_industries_include:
    - "Small Individual Contributions"
    - "Labor Unions"
  dark_money_estimate_max: 500000

expected_confidence_labels:
  verified_facts_min: 20
  human_review_required: false
```

### 6.3 Adversarial Test Cases

```yaml
# Test: Same name different candidates
test_id: ADV-001
input: "John Smith"
context: {}
expected: disambiguation_required == true

# Test: Foreign funding false positive prevention
test_id: ADV-002  
input: "Candidate funded by American Friends of [Foreign Org]"
expected:
  influence_category: != "foreign_national_alleged"
  confidence_level: "high_confidence_inference" OR "low_confidence_inference"
  human_review_reasons: []  # Should NOT trigger foreign review

# Test: Dark money estimation bounds
test_id: ADV-003
input: PAC with 501(c)(4) donors
expected:
  dark_money_estimate: > 0
  trail_termination_points: length >= 1
  confidence: "unknown" for 501c4 ultimate sources

# Test: AIPAC vs foreign funding distinction
test_id: ADV-004
input: "AIPAC contribution"
expected:
  influence_category: "direct_pac_donation"
  NOT: "foreign_national_alleged"
  warnings_include: "Do not conflate with foreign funding"
```

### 6.4 CI/CD Integration

```yaml
# .github/workflows/voteballots-ai-tests.yml
name: Vote/Ballots AI Hook Tests

on:
  push:
    paths:
      - 'modules/foundups/voteballots/**'
  pull_request:
    paths:
      - 'modules/foundups/voteballots/**'

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run unit tests
        run: pytest modules/foundups/voteballots/tests/unit/ -v

  golden-tests:
    runs-on: ubuntu-latest
    needs: unit-tests
    steps:
      - uses: actions/checkout@v4
      - name: Run golden tests
        run: pytest modules/foundups/voteballots/tests/golden/ -v
        env:
          MOCK_EXTERNAL_APIS: true  # Use cached responses

  adversarial-tests:
    runs-on: ubuntu-latest
    needs: unit-tests
    steps:
      - uses: actions/checkout@v4
      - name: Run adversarial tests
        run: pytest modules/foundups/voteballots/tests/adversarial/ -v

  integration-tests:
    runs-on: ubuntu-latest
    needs: [golden-tests, adversarial-tests]
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4
      - name: Run integration tests (sandboxed)
        run: pytest modules/foundups/voteballots/tests/integration/ -v
        env:
          FEC_API_KEY: ${{ secrets.FEC_API_KEY }}
          SANDBOX_MODE: true
```

### 6.5 Evaluation Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Entity Resolution Accuracy | > 95% | % correct on golden set |
| False Positive Rate (Foreign Funding) | < 0.1% | Manual audit sample |
| False Negative Rate (Dark Money) | < 5% | Known dark money test set |
| Confidence Calibration | < 10% deviation | Confidence vs actual accuracy |
| Human Review Rate | 5-15% | Monitor over time |
| Average Latency | < 30s full report | P95 latency tracking |

---

## WSP References

- **WSP 91** — DAEMON observability (telemetry, health, traces)
- **WSP 97** — System execution prompting (confidence labels, CoT/CoR gates)
- **WSP 104** — FoundUp route namespace (`/f/voteballots`)

---

## Route Namespace

| Field | Value |
|-------|-------|
| `foundup_id` | `voteballots` |
| `routing_prefix` | `/f/voteballots` |
| Landing route | `/f/voteballots` |
| App mount | `/f/voteballots/app` |

---

## App Mount

Shell contract: **/f/voteballots/app**
Current status: Design specification (not deployed)

---

## AI Capability Hooks

Per `FOUNDUP_AI_HOOKS_AND_DAEMON_SURFACE_CONTRACT.md`:

| Hook | Status |
|------|--------|
| `get_status` | Planned |
| `get_context` | Planned |
| `navigate` | Planned |
| `launch_capability` | Planned — triggers funding report |
| Shell handoff/return | Planned |

---

## DAEmon Outputs

Per WSP 91:

| Output | Description |
|--------|-------------|
| Health status | Pipeline health: all APIs reachable |
| Last action | Last candidate researched |
| Error state | API failures, confidence collapse |
| Recommended next action | Retry, expand scope, human review |
| Queue/work state | Pending investigations |
| Telemetry namespace | `voteballots.*` |

---

## Data / Telemetry Namespace

| Field | Value |
|-------|-------|
| `foundup_id` | `voteballots` |
| `data_namespace` | `idb_voteballots` |
| Tenant bounds | Cache, reports, user challenges scoped |

---

*0102 pArtifact: This architecture enforces WSP 97 confidence labeling throughout the political transparency pipeline. No hallucinated accusations. Evidence trail termination points explicitly marked. Human review queue for dangerous edge cases.*
