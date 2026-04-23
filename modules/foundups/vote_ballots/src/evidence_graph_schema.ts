/**
 * Vote/Ballots FoundUp - Evidence Graph Schema
 *
 * Political transparency app tracing attack ad funding.
 * Every claim must have source citation and confidence.
 *
 * WSP-97 Compliance: All schema fields distinguish verified vs inferred vs unknown.
 *
 * @module vote_ballots/evidence_graph_schema
 */

// ============================================================================
// SECTION 1: CORE ENUMS AND CONSTANTS
// ============================================================================

/**
 * WSP-97: Evidence status classification
 * CRITICAL: Every edge and claim MUST have one of these statuses
 */
export enum EvidenceStatus {
  /** Confirmed by primary source document with citation */
  VERIFIED = 'verified',
  /** Derived through entity resolution or pattern matching */
  INFERRED = 'inferred',
  /** User-submitted, pending review */
  HYPOTHESIS = 'hypothesis',
  /** Explicitly unknown - disclosure gap identified */
  UNKNOWN = 'unknown',
  /** Previously verified but source since removed/retracted */
  RETRACTED = 'retracted'
}

/**
 * Primary source classes as specified
 */
export enum SourceClass {
  /** Google, Meta, TikTok political ad libraries */
  POLITICAL_AD_LIBRARY = 'political_ad_library',
  /** Federal Election Commission filings */
  FEC_DISCLOSURE = 'fec_disclosure',
  /** OpenSecrets, FollowTheMoney, etc. */
  OUTSIDE_SPENDING_DATABASE = 'outside_spending_database',
  /** Committee/PAC official filings */
  COMMITTEE_FILING = 'committee_filing',
  /** Candidate websites, press releases, official statements */
  CANDIDATE_STATEMENT = 'candidate_statement',
  /** CREW, Sunlight Foundation, CLC, etc. */
  WATCHDOG_REPORT = 'watchdog_report',
  /** NYT, WaPo, ProPublica investigations */
  INVESTIGATIVE_REPORTING = 'investigative_reporting',
  /** Community submissions - UNVERIFIED until reviewed */
  USER_SUBMISSION = 'user_submission'
}

/**
 * Evidence types for edge classification
 */
export enum EvidenceType {
  /** Direct financial transaction records */
  FINANCIAL_TRANSACTION = 'financial_transaction',
  /** Employment, board membership, leadership */
  ORGANIZATIONAL_ROLE = 'organizational_role',
  /** Official campaign endorsement */
  ENDORSEMENT = 'endorsement',
  /** Ad buy, media placement */
  AD_PLACEMENT = 'ad_placement',
  /** Lobbying registration or activity */
  LOBBYING_ACTIVITY = 'lobbying_activity',
  /** Policy position alignment scoring */
  POLICY_ALIGNMENT = 'policy_alignment',
  /** Inferred from naming patterns, addresses, etc. */
  ENTITY_RESOLUTION = 'entity_resolution',
  /** Temporal correlation of events */
  TEMPORAL_CORRELATION = 'temporal_correlation',
  /** User-reported tip */
  USER_TIP = 'user_tip'
}

/**
 * Node type discriminator
 */
export enum NodeType {
  PERSON = 'person',
  CANDIDATE = 'candidate',
  OFFICE = 'office',
  COMMITTEE = 'committee',
  PAC = 'pac',
  SUPER_PAC = 'super_pac',
  DARK_MONEY_ENTITY = 'dark_money_entity', // 501(c)(4)
  DONOR = 'donor',
  EXPENDITURE = 'expenditure',
  AD_CREATIVE = 'ad_creative',
  ATTACK_THEME = 'attack_theme',
  ISSUE_ALIGNMENT = 'issue_alignment',
  LOBBY_ADVOCACY = 'lobby_advocacy',
  ISRAEL_POLICY_ALIGNMENT = 'israel_policy_alignment',
  AIPAC_LINKAGE = 'aipac_linkage',
  CORPORATE_INDUSTRY_LINKAGE = 'corporate_industry_linkage',
  SOURCE_DOCUMENT = 'source_document'
}

/**
 * Edge type discriminator for relationships
 */
export enum EdgeType {
  FUNDS = 'funds',
  CONTROLS = 'controls',
  AFFILIATED_WITH = 'affiliated_with',
  TARGETS = 'targets',
  ATTACKS = 'attacks',
  SUPPORTS = 'supports',
  OPPOSES = 'opposes',
  EMPLOYS = 'employs',
  DONATED_TO = 'donated_to',
  RECEIVED_FROM = 'received_from',
  CREATED_AD = 'created_ad',
  SPONSORS_AD = 'sponsors_ad',
  LOBBIES_FOR = 'lobbies_for',
  ALIGNED_WITH = 'aligned_with',
  DISCLOSED_BY = 'disclosed_by',
  TRACED_VIA = 'traced_via',
  SUCCEEDED_BY = 'succeeded_by', // Entity reconstitution tracking
  SHELL_FOR = 'shell_for' // Dark money shell company relationship
}

// ============================================================================
// SECTION 2: BASE TYPES AND PROVENANCE
// ============================================================================

/**
 * Confidence score with required justification
 * Range: 0.0 (no confidence) to 1.0 (absolute certainty)
 */
export interface ConfidenceScore {
  /** Numeric confidence 0.0-1.0 */
  score: number;
  /** Human-readable justification for this score */
  justification: string;
  /** Factors that increased confidence */
  supporting_factors: string[];
  /** Factors that decreased confidence */
  diminishing_factors: string[];
  /** Last recalculation timestamp */
  calculated_at: string; // ISO 8601
}

/**
 * Source citation - REQUIRED for all claims
 */
export interface SourceCitation {
  /** Unique citation ID */
  citation_id: string;
  /** Source class category */
  source_class: SourceClass;
  /** Display title */
  title: string;
  /** Direct URL to source (if available) */
  url: string | null;
  /** Archive.org/perma.cc backup URL */
  archive_url: string | null;
  /** Publication/filing date */
  date: string; // ISO 8601
  /** Date we accessed/captured this */
  accessed_at: string; // ISO 8601
  /** Author/filer if known */
  author: string | null;
  /** Publisher/platform */
  publisher: string;
  /** Excerpt or relevant passage */
  excerpt: string | null;
  /** Hash of document for integrity */
  document_hash: string | null;
  /** Is this source still accessible? */
  is_live: boolean;
  /** Last verification of source availability */
  last_verified: string; // ISO 8601
}

/**
 * Provenance chain for audit trail
 */
export interface ProvenanceRecord {
  /** When this record was created */
  created_at: string; // ISO 8601
  /** Who/what created this record */
  created_by: string;
  /** Creation method: 'manual' | 'automated_ingest' | 'entity_resolution' | 'user_submission' */
  creation_method: string;
  /** Source citations backing this record */
  citations: SourceCitation[];
  /** Modification history */
  modifications: {
    modified_at: string;
    modified_by: string;
    modification_type: string;
    previous_value: unknown;
    new_value: unknown;
    justification: string;
  }[];
  /** Review/verification events */
  reviews: {
    reviewed_at: string;
    reviewed_by: string;
    review_type: 'verification' | 'challenge' | 'audit';
    outcome: 'confirmed' | 'disputed' | 'corrected' | 'retracted';
    notes: string;
  }[];
}

/**
 * CRITICAL: Money trail terminus marker
 * When disclosure is absent, we MUST surface this explicitly
 */
export interface MoneyTrailTerminus {
  /** The node ID where the trail ends */
  terminus_node_id: string;
  /** Why the trail stops here */
  reason: 'disclosure_gap' | 'shell_company' | 'foreign_source' | 'aggregated_small_donors' | 'unknown';
  /** Human-readable explanation */
  explanation: string;
  /** The canonical message to display */
  display_message: 'The public money trail stops here.';
  /** What disclosure WOULD be required to continue */
  missing_disclosure_type: string | null;
  /** Regulatory body that should have this info */
  responsible_regulator: string | null;
}

// ============================================================================
// SECTION 3: NODE TYPES
// ============================================================================

/**
 * Base node interface - all nodes extend this
 */
export interface BaseNode {
  /** Unique node identifier */
  node_id: string;
  /** Discriminator for node type */
  node_type: NodeType;
  /** Canonical display name */
  display_name: string;
  /** Alternative names for entity resolution */
  aliases: string[];
  /** Evidence status for this node's existence */
  status: EvidenceStatus;
  /** Confidence in node identity/existence */
  confidence: ConfidenceScore;
  /** Full provenance chain */
  provenance: ProvenanceRecord;
  /** When this node was first seen in our system */
  first_seen: string; // ISO 8601
  /** When this node was last updated */
  last_updated: string; // ISO 8601
  /** Is this node still active/operational? */
  is_active: boolean;
  /** Merged node IDs (if this node absorbed duplicates) */
  merged_from: string[];
  /** Tags for categorization */
  tags: string[];
}

/**
 * Person node - natural person (not acting as candidate)
 */
export interface PersonNode extends BaseNode {
  node_type: NodeType.PERSON;
  /** Full legal name if known */
  legal_name: string | null;
  /** Known employers */
  employers: string[];
  /** Known board positions */
  board_positions: string[];
  /** FEC individual ID if registered */
  fec_individual_id: string | null;
  /** OpenSecrets ID if indexed */
  opensecrets_id: string | null;
  /** Disclosed occupation */
  occupation: string | null;
  /** Disclosed city/state */
  location: {
    city: string | null;
    state: string | null;
    zip: string | null;
  };
}

/**
 * Candidate node - person running for office
 */
export interface CandidateNode extends BaseNode {
  node_type: NodeType.CANDIDATE;
  /** FEC candidate ID */
  fec_candidate_id: string | null;
  /** Party affiliation */
  party: string;
  /** Office being sought */
  office_sought_id: string;
  /** Is currently incumbent? */
  is_incumbent: boolean;
  /** Election cycle (e.g., "2024") */
  election_cycle: string;
  /** Campaign website */
  campaign_website: string | null;
  /** Associated person node ID */
  person_node_id: string | null;
  /** Principal campaign committee ID */
  principal_committee_id: string | null;
  /** Candidate status per FEC */
  fec_status: 'active' | 'terminated' | 'unknown';
}

/**
 * Office node - elected position
 */
export interface OfficeNode extends BaseNode {
  node_type: NodeType.OFFICE;
  /** Office level */
  level: 'federal' | 'state' | 'local';
  /** Office type */
  office_type: 'president' | 'senate' | 'house' | 'governor' | 'state_legislature' | 'local' | 'other';
  /** State if applicable */
  state: string | null;
  /** District if applicable */
  district: string | null;
  /** Current term end date */
  term_ends: string | null;
}

/**
 * Committee node - campaign committee
 */
export interface CommitteeNode extends BaseNode {
  node_type: NodeType.COMMITTEE;
  /** FEC committee ID */
  fec_committee_id: string;
  /** Committee type per FEC */
  committee_type: 'principal' | 'authorized' | 'leadership' | 'party' | 'other';
  /** Treasurer name */
  treasurer: string | null;
  /** Filing address */
  address: string | null;
  /** Associated candidate ID if any */
  candidate_id: string | null;
  /** IRS determination letter date */
  irs_determination_date: string | null;
}

/**
 * PAC node - Political Action Committee
 */
export interface PACNode extends BaseNode {
  node_type: NodeType.PAC;
  /** FEC committee ID */
  fec_committee_id: string;
  /** PAC type */
  pac_type: 'connected' | 'non_connected' | 'leadership' | 'carey';
  /** Connected organization if any */
  connected_org: string | null;
  /** Treasurer name */
  treasurer: string | null;
  /** Can accept unlimited contributions? */
  accepts_unlimited: boolean;
}

/**
 * Super PAC node - Independent Expenditure Committee
 */
export interface SuperPACNode extends BaseNode {
  node_type: NodeType.SUPER_PAC;
  /** FEC committee ID */
  fec_committee_id: string;
  /** Legal name */
  legal_name: string;
  /** Treasurer */
  treasurer: string | null;
  /** Registration date */
  registration_date: string | null;
  /** Total raised (last reported) */
  total_raised: number | null;
  /** Total spent (last reported) */
  total_spent: number | null;
  /** As of date for financials */
  financials_as_of: string | null;
}

/**
 * Dark money entity - 501(c)(4) or similar non-disclosing org
 */
export interface DarkMoneyEntityNode extends BaseNode {
  node_type: NodeType.DARK_MONEY_ENTITY;
  /** IRS EIN if known */
  ein: string | null;
  /** 501(c) subsection */
  tax_status: '501c4' | '501c6' | '527' | 'llc' | 'unknown';
  /** Legal name on IRS filing */
  legal_name: string | null;
  /** State of incorporation */
  state_of_incorporation: string | null;
  /** Known/suspected shell company? */
  is_suspected_shell: boolean;
  /** Shell company evidence if suspected */
  shell_evidence: string | null;
  /** Does NOT disclose donors */
  donor_disclosure: 'none' | 'partial' | 'full';
  /**
   * CRITICAL: This is where money trails often end
   * If this is a terminus, must populate terminus_info
   */
  is_money_trail_terminus: boolean;
  terminus_info: MoneyTrailTerminus | null;
}

/**
 * Donor node - individual or entity that gave money
 */
export interface DonorNode extends BaseNode {
  node_type: NodeType.DONOR;
  /** Donor type */
  donor_type: 'individual' | 'corporation' | 'labor' | 'pac' | 'other' | 'unknown';
  /** Total contributed (aggregated) */
  total_contributed: number | null;
  /** Contribution period */
  contribution_period: {
    start: string;
    end: string;
  } | null;
  /** Is this an aggregated "small donor" bucket? */
  is_aggregated_small_donors: boolean;
  /** If linked to a person node */
  person_node_id: string | null;
  /** If linked to an org node */
  org_node_id: string | null;
}

/**
 * Expenditure node - money spent on political activity
 */
export interface ExpenditureNode extends BaseNode {
  node_type: NodeType.EXPENDITURE;
  /** FEC transaction ID if applicable */
  fec_transaction_id: string | null;
  /** Amount spent */
  amount: number;
  /** Currency (always USD for FEC) */
  currency: string;
  /** Date of expenditure */
  expenditure_date: string;
  /** Purpose description */
  purpose: string;
  /** Payee name */
  payee: string;
  /** Payee address */
  payee_address: string | null;
  /** Is independent expenditure? */
  is_independent_expenditure: boolean;
  /** Support or oppose? */
  support_oppose: 'support' | 'oppose' | null;
  /** Targeted candidate ID if IE */
  target_candidate_id: string | null;
  /** Election type */
  election_type: 'primary' | 'general' | 'special' | 'runoff' | null;
}

/**
 * Ad creative node - specific ad/message
 */
export interface AdCreativeNode extends BaseNode {
  node_type: NodeType.AD_CREATIVE;
  /** Platform where ad ran */
  platform: 'google' | 'meta' | 'tiktok' | 'tv' | 'radio' | 'print' | 'direct_mail' | 'digital_other';
  /** Platform's ad ID */
  platform_ad_id: string | null;
  /** Ad library URL */
  ad_library_url: string | null;
  /** Creative type */
  creative_type: 'video' | 'image' | 'text' | 'audio' | 'mixed';
  /** Transcript or text content */
  transcript: string | null;
  /** Is this an attack ad? */
  is_attack_ad: boolean;
  /** Attack themes if attack ad */
  attack_theme_ids: string[];
  /** Target candidate if applicable */
  target_candidate_id: string | null;
  /** Supporting candidate if applicable */
  supporting_candidate_id: string | null;
  /** First air/publish date */
  first_seen_date: string | null;
  /** Last air/publish date */
  last_seen_date: string | null;
  /** Estimated impressions */
  estimated_impressions: number | null;
  /** Estimated spend */
  estimated_spend: {
    min: number;
    max: number;
  } | null;
  /** Geographic targeting */
  geo_targeting: string[];
  /** Demographic targeting */
  demo_targeting: string[];
  /** Archived creative URL */
  archived_creative_url: string | null;
}

/**
 * Attack theme node - categorized attack messaging
 */
export interface AttackThemeNode extends BaseNode {
  node_type: NodeType.ATTACK_THEME;
  /** Theme category */
  theme_category: string;
  /** Specific theme */
  theme_name: string;
  /** Theme description */
  description: string;
  /** Keywords associated with this theme */
  keywords: string[];
  /** Is this a documented disinformation theme? */
  is_documented_disinfo: boolean;
  /** Fact-check status if applicable */
  fact_check_status: 'debunked' | 'misleading' | 'mixed' | 'accurate' | 'unverified' | null;
  /** Fact-check citations */
  fact_check_citations: SourceCitation[];
}

/**
 * Issue alignment node - policy position tracking
 */
export interface IssueAlignmentNode extends BaseNode {
  node_type: NodeType.ISSUE_ALIGNMENT;
  /** Issue area */
  issue_area: string;
  /** Specific position */
  position: string;
  /** Position spectrum score (-1.0 to 1.0) */
  spectrum_score: number | null;
  /** Scoring methodology */
  scoring_methodology: string | null;
  /** Scorecard source */
  scorecard_source: string | null;
}

/**
 * Lobby/advocacy linkage node
 */
export interface LobbyAdvocacyNode extends BaseNode {
  node_type: NodeType.LOBBY_ADVOCACY;
  /** Lobby disclosure ID */
  lobby_disclosure_id: string | null;
  /** Registrant name */
  registrant: string;
  /** Client name */
  client: string | null;
  /** Issues lobbied on */
  issues: string[];
  /** Specific bills */
  bills: string[];
  /** Total lobbying spend */
  total_spend: number | null;
  /** Reporting period */
  reporting_period: string | null;
}

/**
 * Israel policy alignment node - specific tracking per requirements
 */
export interface IsraelPolicyAlignmentNode extends BaseNode {
  node_type: NodeType.ISRAEL_POLICY_ALIGNMENT;
  /** Position type */
  position_type: 'pro_israel' | 'pro_palestinian' | 'two_state' | 'neutral' | 'unclear';
  /** Specific policy positions */
  policy_positions: string[];
  /** Has signed AIPAC pledge? */
  signed_aipac_pledge: boolean | null;
  /** Visited Israel? */
  israel_visit: boolean | null;
  /** Vote record on Israel-related bills */
  vote_record: {
    bill_id: string;
    bill_name: string;
    vote: 'yes' | 'no' | 'abstain' | 'not_voting';
    date: string;
  }[];
}

/**
 * AIPAC linkage node - specific tracking per requirements
 */
export interface AIPACLinkageNode extends BaseNode {
  node_type: NodeType.AIPAC_LINKAGE;
  /** AIPAC entity type */
  aipac_entity: 'aipac_pac' | 'united_democracy_project' | 'dmfi' | 'aipac_affiliated' | 'aipac_member';
  /** Nature of connection */
  connection_type: 'endorsed' | 'funded' | 'member' | 'staff' | 'speaker' | 'trip_participant';
  /** Amount if applicable */
  amount: number | null;
  /** Event/activity description */
  activity_description: string | null;
  /** Date of connection */
  connection_date: string | null;
}

/**
 * Corporate/industry linkage node
 */
export interface CorporateIndustryLinkageNode extends BaseNode {
  node_type: NodeType.CORPORATE_INDUSTRY_LINKAGE;
  /** Industry sector */
  industry_sector: string;
  /** NAICS code if applicable */
  naics_code: string | null;
  /** Specific companies involved */
  companies: string[];
  /** Industry association involvement */
  trade_associations: string[];
  /** Total industry contributions */
  industry_total: number | null;
}

/**
 * Source document node - represents an actual source file
 */
export interface SourceDocumentNode extends BaseNode {
  node_type: NodeType.SOURCE_DOCUMENT;
  /** Source class */
  source_class: SourceClass;
  /** Document type */
  document_type: string;
  /** Original URL */
  original_url: string | null;
  /** Archived URL */
  archived_url: string | null;
  /** File hash for integrity */
  file_hash: string;
  /** File size bytes */
  file_size: number;
  /** MIME type */
  mime_type: string;
  /** Ingestion timestamp */
  ingested_at: string;
  /** Extraction status */
  extraction_status: 'pending' | 'complete' | 'failed' | 'partial';
  /** Extracted entity count */
  extracted_entity_count: number;
  /** Extracted edge count */
  extracted_edge_count: number;
}

/**
 * Union type for all nodes
 */
export type GraphNode =
  | PersonNode
  | CandidateNode
  | OfficeNode
  | CommitteeNode
  | PACNode
  | SuperPACNode
  | DarkMoneyEntityNode
  | DonorNode
  | ExpenditureNode
  | AdCreativeNode
  | AttackThemeNode
  | IssueAlignmentNode
  | LobbyAdvocacyNode
  | IsraelPolicyAlignmentNode
  | AIPACLinkageNode
  | CorporateIndustryLinkageNode
  | SourceDocumentNode;

// ============================================================================
// SECTION 4: EDGE TYPES
// ============================================================================

/**
 * Base edge interface - all edges extend this
 * CRITICAL: Every edge MUST carry source, date, evidence type, confidence, and status
 */
export interface BaseEdge {
  /** Unique edge identifier */
  edge_id: string;
  /** Source node ID */
  source_node_id: string;
  /** Target node ID */
  target_node_id: string;
  /** Edge type discriminator */
  edge_type: EdgeType;
  /** REQUIRED: Source citations */
  sources: SourceCitation[];
  /** REQUIRED: Date of relationship/transaction */
  date: string; // ISO 8601
  /** Date range if relationship spans time */
  date_range: {
    start: string;
    end: string | null; // null = ongoing
  } | null;
  /** REQUIRED: Evidence type classification */
  evidence_type: EvidenceType;
  /** REQUIRED: Confidence score */
  confidence: ConfidenceScore;
  /** REQUIRED: WSP-97 verified/inferred/hypothesis label */
  status: EvidenceStatus;
  /** Full provenance */
  provenance: ProvenanceRecord;
  /** Is this edge currently active? */
  is_active: boolean;
  /** Human-readable relationship label */
  label: string;
  /** Additional structured metadata */
  metadata: Record<string, unknown>;
}

/**
 * Financial edge - money flow
 */
export interface FinancialEdge extends BaseEdge {
  edge_type: EdgeType.FUNDS | EdgeType.DONATED_TO | EdgeType.RECEIVED_FROM;
  /** Amount in cents (to avoid floating point) */
  amount_cents: number;
  /** Currency code */
  currency: string;
  /** Transaction type */
  transaction_type: 'contribution' | 'expenditure' | 'transfer' | 'loan' | 'refund' | 'other';
  /** FEC transaction ID if applicable */
  fec_transaction_id: string | null;
  /** Is this aggregated from multiple transactions? */
  is_aggregated: boolean;
  /** If aggregated, transaction count */
  transaction_count: number | null;
  /** Earmarked for specific candidate? */
  earmarked_for: string | null;
}

/**
 * Control edge - organizational control
 */
export interface ControlEdge extends BaseEdge {
  edge_type: EdgeType.CONTROLS | EdgeType.SHELL_FOR | EdgeType.SUCCEEDED_BY;
  /** Control type */
  control_type: 'legal' | 'operational' | 'financial' | 'suspected';
  /** Control evidence strength */
  control_evidence: string;
}

/**
 * Affiliation edge - organizational relationship
 */
export interface AffiliationEdge extends BaseEdge {
  edge_type: EdgeType.AFFILIATED_WITH | EdgeType.EMPLOYS | EdgeType.ALIGNED_WITH;
  /** Role/position in affiliation */
  role: string | null;
  /** Is current affiliation? */
  is_current: boolean;
}

/**
 * Targeting edge - ad/attack targeting
 */
export interface TargetingEdge extends BaseEdge {
  edge_type: EdgeType.TARGETS | EdgeType.ATTACKS | EdgeType.SUPPORTS | EdgeType.OPPOSES;
  /** Targeting intensity */
  intensity: 'primary' | 'secondary' | 'mentioned';
  /** Support/oppose classification */
  sentiment: 'positive' | 'negative' | 'neutral';
}

/**
 * Union type for all edges
 */
export type GraphEdge =
  | FinancialEdge
  | ControlEdge
  | AffiliationEdge
  | TargetingEdge
  | BaseEdge;

// ============================================================================
// SECTION 5: ENTITY RESOLUTION
// ============================================================================

/**
 * Entity resolution result
 */
export interface EntityResolutionResult {
  /** Resolution ID */
  resolution_id: string;
  /** Input identifiers that were resolved */
  input_identifiers: {
    identifier_type: string;
    identifier_value: string;
    source: SourceCitation;
  }[];
  /** Resolved node ID */
  resolved_node_id: string;
  /** Resolution method */
  resolution_method: 'exact_id_match' | 'fuzzy_name_match' | 'address_match' | 'cross_reference' | 'manual_review';
  /** Resolution confidence */
  confidence: ConfidenceScore;
  /** Alternative candidates considered */
  candidates_considered: {
    node_id: string;
    similarity_score: number;
    rejection_reason: string;
  }[];
  /** Resolved at timestamp */
  resolved_at: string;
  /** Resolved by (system or user ID) */
  resolved_by: string;
}

/**
 * Entity resolution configuration
 */
export interface EntityResolutionConfig {
  /** Minimum confidence to auto-resolve */
  auto_resolve_threshold: number;
  /** Minimum confidence to suggest */
  suggestion_threshold: number;
  /** Fields to match on by node type */
  matching_fields: Record<NodeType, {
    field: string;
    weight: number;
    exact_match_required: boolean;
  }[]>;
  /** Name normalization rules */
  name_normalization: {
    remove_suffixes: string[];
    standardize_prefixes: Record<string, string>;
    ignore_case: boolean;
    ignore_punctuation: boolean;
  };
}

// ============================================================================
// SECTION 6: DEDUPE STRATEGY
// ============================================================================

/**
 * Duplicate detection result
 */
export interface DuplicateDetectionResult {
  /** Detection ID */
  detection_id: string;
  /** Potential duplicate node IDs */
  duplicate_candidates: string[];
  /** Similarity scores */
  similarity_scores: {
    node_id_a: string;
    node_id_b: string;
    overall_similarity: number;
    field_similarities: Record<string, number>;
  }[];
  /** Suggested merge target */
  suggested_merge_target: string | null;
  /** Auto-merge confidence */
  auto_merge_confidence: number;
  /** Detected at */
  detected_at: string;
  /** Resolution status */
  resolution_status: 'pending' | 'merged' | 'kept_separate' | 'needs_review';
}

/**
 * Merge operation record
 */
export interface MergeOperation {
  /** Merge ID */
  merge_id: string;
  /** Source node IDs (being merged) */
  source_node_ids: string[];
  /** Target node ID (surviving) */
  target_node_id: string;
  /** Merge strategy */
  merge_strategy: 'latest_wins' | 'highest_confidence' | 'manual_selection';
  /** Field-level merge decisions */
  field_decisions: Record<string, {
    source_node_id: string;
    value: unknown;
    reason: string;
  }>;
  /** Edges transferred */
  edges_transferred: string[];
  /** Executed at */
  executed_at: string;
  /** Executed by */
  executed_by: string;
  /** Is reversible? */
  is_reversible: boolean;
}

// ============================================================================
// SECTION 7: CONFIDENCE SCORING RULES
// ============================================================================

/**
 * Confidence scoring configuration
 */
export interface ConfidenceScoringRules {
  /** Base scores by source class */
  source_class_base_scores: Record<SourceClass, number>;

  /** Modifiers applied to base score */
  modifiers: {
    /** Source is primary (direct filing) vs secondary (reporting) */
    primary_source_bonus: number;
    /** Multiple independent sources confirm */
    corroboration_bonus: number;
    /** Source has been fact-checked */
    fact_checked_bonus: number;
    /** Source is archived/preserved */
    archived_bonus: number;
    /** Source is recent (< 30 days) */
    recency_bonus: number;
    /** Source is old (> 2 years) */
    age_penalty: number;
    /** Single source only */
    single_source_penalty: number;
    /** User-submitted, unverified */
    unverified_submission_penalty: number;
    /** Source no longer accessible */
    dead_link_penalty: number;
    /** Inferred relationship (not stated) */
    inference_penalty: number;
  };

  /** Minimum thresholds */
  thresholds: {
    /** Below this = HYPOTHESIS */
    hypothesis_max: number;
    /** Below this = INFERRED */
    inferred_max: number;
    /** At or above this = VERIFIED */
    verified_min: number;
  };
}

/**
 * Default confidence scoring rules
 */
export const DEFAULT_CONFIDENCE_RULES: ConfidenceScoringRules = {
  source_class_base_scores: {
    [SourceClass.FEC_DISCLOSURE]: 0.95,
    [SourceClass.COMMITTEE_FILING]: 0.90,
    [SourceClass.POLITICAL_AD_LIBRARY]: 0.85,
    [SourceClass.OUTSIDE_SPENDING_DATABASE]: 0.80,
    [SourceClass.WATCHDOG_REPORT]: 0.75,
    [SourceClass.CANDIDATE_STATEMENT]: 0.70,
    [SourceClass.INVESTIGATIVE_REPORTING]: 0.70,
    [SourceClass.USER_SUBMISSION]: 0.30,
  },
  modifiers: {
    primary_source_bonus: 0.10,
    corroboration_bonus: 0.15,
    fact_checked_bonus: 0.10,
    archived_bonus: 0.05,
    recency_bonus: 0.05,
    age_penalty: -0.10,
    single_source_penalty: -0.15,
    unverified_submission_penalty: -0.40,
    dead_link_penalty: -0.20,
    inference_penalty: -0.25,
  },
  thresholds: {
    hypothesis_max: 0.40,
    inferred_max: 0.70,
    verified_min: 0.70,
  },
};

// ============================================================================
// SECTION 8: SOURCE ADAPTERS
// ============================================================================

/**
 * Base adapter interface
 */
export interface SourceAdapter<TRawData, TNode extends GraphNode, TEdge extends GraphEdge> {
  /** Adapter identifier */
  adapter_id: string;
  /** Source class this adapter handles */
  source_class: SourceClass;
  /** Supported data formats */
  supported_formats: string[];

  /** Parse raw data */
  parse(raw: TRawData): Promise<{
    nodes: TNode[];
    edges: TEdge[];
    errors: AdapterError[];
  }>;

  /** Validate parsed data */
  validate(data: { nodes: TNode[]; edges: TEdge[] }): Promise<ValidationResult>;

  /** Fetch fresh data from source */
  fetch(query: AdapterQuery): Promise<TRawData>;

  /** Check if source is available */
  healthCheck(): Promise<boolean>;

  /** Get rate limit status */
  getRateLimitStatus(): RateLimitStatus;
}

export interface AdapterError {
  error_code: string;
  message: string;
  field: string | null;
  raw_value: unknown;
  recoverable: boolean;
}

export interface ValidationResult {
  is_valid: boolean;
  errors: AdapterError[];
  warnings: string[];
  stats: {
    nodes_validated: number;
    edges_validated: number;
    nodes_rejected: number;
    edges_rejected: number;
  };
}

export interface AdapterQuery {
  /** Query type */
  query_type: string;
  /** Query parameters */
  parameters: Record<string, unknown>;
  /** Date range if applicable */
  date_range: { start: string; end: string } | null;
  /** Pagination */
  pagination: { offset: number; limit: number } | null;
}

export interface RateLimitStatus {
  is_limited: boolean;
  requests_remaining: number;
  reset_at: string | null;
  daily_limit: number | null;
  daily_used: number | null;
}

/**
 * FEC Disclosure Adapter config
 */
export interface FECAdapterConfig {
  api_key: string;
  base_url: string;
  rate_limit_per_hour: number;
}

/**
 * Google Ad Library Adapter config
 */
export interface GoogleAdLibraryAdapterConfig {
  developer_token: string;
  transparency_report_url: string;
}

/**
 * Meta Ad Library Adapter config
 */
export interface MetaAdLibraryAdapterConfig {
  access_token: string;
  api_version: string;
}

/**
 * OpenSecrets Adapter config
 */
export interface OpenSecretsAdapterConfig {
  api_key: string;
  base_url: string;
}

// ============================================================================
// SECTION 9: QUERY PATTERNS
// ============================================================================

/**
 * Query: Who is attacking candidate X?
 */
export interface AttackersQuery {
  query_type: 'attackers';
  target_candidate_id: string;
  /** Include indirect attackers (via PACs)? */
  include_indirect: boolean;
  /** Time range */
  date_range: { start: string; end: string } | null;
  /** Minimum confidence threshold */
  min_confidence: number;
}

export interface AttackersQueryResult {
  target_candidate: CandidateNode;
  attackers: {
    attacker_node: GraphNode;
    attack_edges: TargetingEdge[];
    ad_creatives: AdCreativeNode[];
    total_spend: number | null;
    attack_themes: AttackThemeNode[];
    funding_chain: FundingChainResult | null;
  }[];
  summary: {
    total_attackers: number;
    total_attack_ads: number;
    total_estimated_spend: number;
    top_attack_themes: string[];
  };
}

/**
 * Query: What is the funding chain for PAC Y?
 */
export interface FundingChainQuery {
  query_type: 'funding_chain';
  entity_id: string;
  /** Max depth to traverse */
  max_depth: number;
  /** Include suspected/inferred links? */
  include_inferred: boolean;
  /** Minimum amount to include */
  min_amount: number | null;
}

export interface FundingChainResult {
  root_entity: GraphNode;
  chain: {
    depth: number;
    from_node: GraphNode;
    to_node: GraphNode;
    edge: FinancialEdge;
    cumulative_amount: number;
  }[];
  /** CRITICAL: Where the trail ends */
  terminus_nodes: {
    node: GraphNode;
    terminus_info: MoneyTrailTerminus;
  }[];
  total_traceable: number;
  total_untraceable: number;
  disclosure_gaps: string[];
}

/**
 * Query: What AIPAC-linked spending targets candidate X?
 */
export interface AIPACSpendingQuery {
  query_type: 'aipac_spending';
  target_candidate_id: string;
  /** Include all pro-Israel spending or just AIPAC-linked? */
  include_aligned_groups: boolean;
  /** Support or oppose spending? */
  spending_type: 'support' | 'oppose' | 'both';
  date_range: { start: string; end: string } | null;
}

export interface AIPACSpendingQueryResult {
  target_candidate: CandidateNode;
  aipac_linked_spending: {
    spender_node: GraphNode;
    aipac_linkage: AIPACLinkageNode;
    expenditures: ExpenditureNode[];
    ad_creatives: AdCreativeNode[];
    total_amount: number;
    support_oppose: 'support' | 'oppose';
  }[];
  aligned_group_spending: {
    spender_node: GraphNode;
    israel_alignment: IsraelPolicyAlignmentNode;
    expenditures: ExpenditureNode[];
    total_amount: number;
  }[];
  summary: {
    total_aipac_linked: number;
    total_aligned_groups: number;
    total_supporting: number;
    total_opposing: number;
  };
}

/**
 * General graph traversal query
 */
export interface GraphTraversalQuery {
  query_type: 'traverse';
  start_node_id: string;
  edge_types: EdgeType[];
  direction: 'outgoing' | 'incoming' | 'both';
  max_depth: number;
  filters: {
    node_types?: NodeType[];
    min_confidence?: number;
    statuses?: EvidenceStatus[];
    date_range?: { start: string; end: string };
  };
}

// ============================================================================
// SECTION 10: CACHE STRATEGY
// ============================================================================

/**
 * Cache entry
 */
export interface CacheEntry<T> {
  /** Cache key */
  key: string;
  /** Cached value */
  value: T;
  /** When cached */
  cached_at: string;
  /** Expires at */
  expires_at: string;
  /** Cache hit count */
  hit_count: number;
  /** Last accessed */
  last_accessed: string;
  /** Source freshness timestamp */
  source_freshness: string | null;
  /** ETags or version identifiers */
  version_tags: string[];
}

/**
 * Cache configuration
 */
export interface CacheConfig {
  /** Default TTL in seconds */
  default_ttl_seconds: number;

  /** TTL by source class (more volatile = shorter TTL) */
  ttl_by_source_class: Record<SourceClass, number>;

  /** TTL by query type */
  ttl_by_query_type: Record<string, number>;

  /** Maximum cache size in entries */
  max_entries: number;

  /** Eviction policy */
  eviction_policy: 'lru' | 'lfu' | 'ttl';

  /** Stale-while-revalidate window in seconds */
  stale_revalidate_seconds: number;

  /** Background refresh enabled? */
  background_refresh: boolean;
}

/**
 * Default cache configuration
 */
export const DEFAULT_CACHE_CONFIG: CacheConfig = {
  default_ttl_seconds: 3600, // 1 hour
  ttl_by_source_class: {
    [SourceClass.FEC_DISCLOSURE]: 86400, // 24 hours (updated daily)
    [SourceClass.COMMITTEE_FILING]: 86400,
    [SourceClass.POLITICAL_AD_LIBRARY]: 21600, // 6 hours
    [SourceClass.OUTSIDE_SPENDING_DATABASE]: 43200, // 12 hours
    [SourceClass.WATCHDOG_REPORT]: 86400,
    [SourceClass.CANDIDATE_STATEMENT]: 3600,
    [SourceClass.INVESTIGATIVE_REPORTING]: 86400,
    [SourceClass.USER_SUBMISSION]: 300, // 5 minutes (volatile)
  },
  ttl_by_query_type: {
    'attackers': 1800, // 30 minutes
    'funding_chain': 3600, // 1 hour
    'aipac_spending': 3600,
    'traverse': 1800,
  },
  max_entries: 10000,
  eviction_policy: 'lru',
  stale_revalidate_seconds: 300,
  background_refresh: true,
};

/**
 * Cache interface
 */
export interface EvidenceGraphCache {
  get<T>(key: string): Promise<CacheEntry<T> | null>;
  set<T>(key: string, value: T, ttl_seconds?: number): Promise<void>;
  invalidate(key: string): Promise<void>;
  invalidateByPattern(pattern: string): Promise<number>;
  invalidateBySourceClass(source_class: SourceClass): Promise<number>;
  getStats(): Promise<CacheStats>;
}

export interface CacheStats {
  total_entries: number;
  hit_rate: number;
  miss_rate: number;
  evictions: number;
  memory_bytes: number;
  oldest_entry: string | null;
  newest_entry: string | null;
}

// ============================================================================
// SECTION 11: GRAPH OPERATIONS
// ============================================================================

/**
 * Main evidence graph interface
 */
export interface EvidenceGraph {
  // Node operations
  addNode(node: GraphNode): Promise<string>;
  getNode(node_id: string): Promise<GraphNode | null>;
  updateNode(node_id: string, updates: Partial<GraphNode>): Promise<void>;
  deleteNode(node_id: string): Promise<void>;

  // Edge operations
  addEdge(edge: GraphEdge): Promise<string>;
  getEdge(edge_id: string): Promise<GraphEdge | null>;
  updateEdge(edge_id: string, updates: Partial<GraphEdge>): Promise<void>;
  deleteEdge(edge_id: string): Promise<void>;

  // Entity resolution
  resolveEntity(identifiers: Record<string, string>[]): Promise<EntityResolutionResult>;

  // Duplicate detection
  detectDuplicates(node_id: string): Promise<DuplicateDetectionResult>;
  mergeNodes(merge_operation: MergeOperation): Promise<string>;

  // Queries
  queryAttackers(query: AttackersQuery): Promise<AttackersQueryResult>;
  queryFundingChain(query: FundingChainQuery): Promise<FundingChainResult>;
  queryAIPACSpending(query: AIPACSpendingQuery): Promise<AIPACSpendingQueryResult>;
  traverse(query: GraphTraversalQuery): Promise<GraphNode[]>;

  // Bulk operations
  bulkImport(nodes: GraphNode[], edges: GraphEdge[]): Promise<BulkImportResult>;

  // Export
  export(format: 'json' | 'graphml' | 'neo4j'): Promise<string>;
}

export interface BulkImportResult {
  nodes_created: number;
  nodes_updated: number;
  nodes_rejected: number;
  edges_created: number;
  edges_updated: number;
  edges_rejected: number;
  errors: AdapterError[];
  duration_ms: number;
}

// ============================================================================
// SECTION 12: TEST FIXTURES
// ============================================================================

/**
 * Test fixture types
 */
export interface TestFixtures {
  /** Sample nodes by type */
  sample_nodes: Record<NodeType, GraphNode[]>;
  /** Sample edges by type */
  sample_edges: Record<EdgeType, GraphEdge[]>;
  /** Complete funding chains */
  funding_chains: FundingChainResult[];
  /** Attack scenarios */
  attack_scenarios: AttackersQueryResult[];
  /** AIPAC spending scenarios */
  aipac_scenarios: AIPACSpendingQueryResult[];
  /** Disclosure gap scenarios */
  disclosure_gaps: MoneyTrailTerminus[];
  /** Entity resolution test cases */
  entity_resolution_cases: {
    input: Record<string, string>[];
    expected_node_id: string;
    expected_confidence: number;
  }[];
  /** Duplicate detection cases */
  duplicate_cases: {
    node_a: GraphNode;
    node_b: GraphNode;
    expected_similarity: number;
    should_merge: boolean;
  }[];
}

// ============================================================================
// SECTION 13: ERROR TYPES
// ============================================================================

export class EvidenceGraphError extends Error {
  constructor(
    public code: string,
    message: string,
    public recoverable: boolean = true,
    public details?: Record<string, unknown>
  ) {
    super(message);
    this.name = 'EvidenceGraphError';
  }
}

export class ValidationError extends EvidenceGraphError {
  constructor(message: string, field: string, value: unknown) {
    super('VALIDATION_ERROR', message, true, { field, value });
    this.name = 'ValidationError';
  }
}

export class EntityResolutionError extends EvidenceGraphError {
  constructor(message: string, candidates: string[]) {
    super('ENTITY_RESOLUTION_ERROR', message, true, { candidates });
    this.name = 'EntityResolutionError';
  }
}

export class SourceAdapterError extends EvidenceGraphError {
  constructor(adapter_id: string, message: string, recoverable: boolean = true) {
    super('SOURCE_ADAPTER_ERROR', message, recoverable, { adapter_id });
    this.name = 'SourceAdapterError';
  }
}

export class DisclosureGapError extends EvidenceGraphError {
  constructor(terminus_node_id: string, reason: string) {
    super('DISCLOSURE_GAP', 'The public money trail stops here.', false, {
      terminus_node_id,
      reason,
      display_message: 'The public money trail stops here.'
    });
    this.name = 'DisclosureGapError';
  }
}
