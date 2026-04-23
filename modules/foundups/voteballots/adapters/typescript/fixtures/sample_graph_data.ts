/**
 * Vote/Ballots FoundUp - Test Fixtures
 *
 * Sample data for testing evidence graph schema
 * Includes realistic political finance scenarios
 */

import {
  EvidenceStatus,
  SourceClass,
  EvidenceType,
  NodeType,
  EdgeType,
  ConfidenceScore,
  SourceCitation,
  ProvenanceRecord,
  MoneyTrailTerminus,
  CandidateNode,
  SuperPACNode,
  DarkMoneyEntityNode,
  DonorNode,
  ExpenditureNode,
  AdCreativeNode,
  AttackThemeNode,
  AIPACLinkageNode,
  FinancialEdge,
  TargetingEdge,
  FundingChainResult,
  AttackersQueryResult,
  AIPACSpendingQueryResult,
  DEFAULT_CONFIDENCE_RULES,
} from '../../src/evidence_graph_schema';

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

const now = new Date().toISOString();

function makeConfidence(
  score: number,
  justification: string,
  supporting: string[] = [],
  diminishing: string[] = []
): ConfidenceScore {
  return {
    score,
    justification,
    supporting_factors: supporting,
    diminishing_factors: diminishing,
    calculated_at: now,
  };
}

function makeCitation(
  source_class: SourceClass,
  title: string,
  url: string | null,
  date: string
): SourceCitation {
  return {
    citation_id: `cit_${Math.random().toString(36).substring(7)}`,
    source_class,
    title,
    url,
    archive_url: url ? `https://web.archive.org/web/${url}` : null,
    date,
    accessed_at: now,
    author: null,
    publisher: 'FEC' + (source_class === SourceClass.FEC_DISCLOSURE ? '' : ''),
    excerpt: null,
    document_hash: null,
    is_live: true,
    last_verified: now,
  };
}

function makeProvenance(
  method: string,
  citations: SourceCitation[]
): ProvenanceRecord {
  return {
    created_at: now,
    created_by: 'test_fixture_generator',
    creation_method: method,
    citations,
    modifications: [],
    reviews: [],
  };
}

// ============================================================================
// SAMPLE CANDIDATES
// ============================================================================

export const SAMPLE_CANDIDATE_PROGRESSIVE: CandidateNode = {
  node_id: 'cand_001_progressive',
  node_type: NodeType.CANDIDATE,
  display_name: 'Jane Progressive',
  aliases: ['J. Progressive', 'Jane P.'],
  status: EvidenceStatus.VERIFIED,
  confidence: makeConfidence(
    0.98,
    'FEC candidate registration confirmed',
    ['FEC filing exists', 'Active campaign website']
  ),
  provenance: makeProvenance('automated_ingest', [
    makeCitation(
      SourceClass.FEC_DISCLOSURE,
      'FEC Form 2: Statement of Candidacy',
      'https://fec.gov/data/candidate/H0CA01234',
      '2024-01-15'
    ),
  ]),
  first_seen: '2024-01-15T00:00:00Z',
  last_updated: now,
  is_active: true,
  merged_from: [],
  tags: ['progressive', 'incumbent', 'targeted'],
  fec_candidate_id: 'H0CA01234',
  party: 'Democratic',
  office_sought_id: 'office_house_ca_15',
  is_incumbent: true,
  election_cycle: '2024',
  campaign_website: 'https://janeforthepeople.com',
  person_node_id: 'person_jane_p',
  principal_committee_id: 'comm_jane_2024',
  fec_status: 'active',
};

export const SAMPLE_CANDIDATE_CHALLENGER: CandidateNode = {
  node_id: 'cand_002_challenger',
  node_type: NodeType.CANDIDATE,
  display_name: 'Bob Challenger',
  aliases: ['Robert Challenger', 'Bob C.'],
  status: EvidenceStatus.VERIFIED,
  confidence: makeConfidence(
    0.95,
    'FEC candidate registration confirmed',
    ['FEC filing exists']
  ),
  provenance: makeProvenance('automated_ingest', [
    makeCitation(
      SourceClass.FEC_DISCLOSURE,
      'FEC Form 2: Statement of Candidacy',
      'https://fec.gov/data/candidate/H0CA05678',
      '2024-02-01'
    ),
  ]),
  first_seen: '2024-02-01T00:00:00Z',
  last_updated: now,
  is_active: true,
  merged_from: [],
  tags: ['challenger', 'aipac_backed'],
  fec_candidate_id: 'H0CA05678',
  party: 'Democratic',
  office_sought_id: 'office_house_ca_15',
  is_incumbent: false,
  election_cycle: '2024',
  campaign_website: 'https://bobforprogress.com',
  person_node_id: 'person_bob_c',
  principal_committee_id: 'comm_bob_2024',
  fec_status: 'active',
};

// ============================================================================
// SAMPLE SUPER PACS
// ============================================================================

export const SAMPLE_SUPER_PAC_UDP: SuperPACNode = {
  node_id: 'spac_001_udp',
  node_type: NodeType.SUPER_PAC,
  display_name: 'United Democracy Project',
  aliases: ['UDP'],
  status: EvidenceStatus.VERIFIED,
  confidence: makeConfidence(
    0.99,
    'FEC registered Super PAC with extensive filing history',
    ['Multiple FEC filings', 'Publicly disclosed funding sources'],
    []
  ),
  provenance: makeProvenance('automated_ingest', [
    makeCitation(
      SourceClass.FEC_DISCLOSURE,
      'FEC Committee Registration',
      'https://fec.gov/data/committee/C00770941',
      '2021-12-01'
    ),
  ]),
  first_seen: '2021-12-01T00:00:00Z',
  last_updated: now,
  is_active: true,
  merged_from: [],
  tags: ['pro_israel', 'aipac_affiliated', 'super_pac'],
  fec_committee_id: 'C00770941',
  legal_name: 'UNITED DEMOCRACY PROJECT',
  treasurer: 'John Smith',
  registration_date: '2021-12-01',
  total_raised: 105000000,
  total_spent: 98000000,
  financials_as_of: '2024-06-30',
};

export const SAMPLE_SUPER_PAC_GENERIC: SuperPACNode = {
  node_id: 'spac_002_generic',
  node_type: NodeType.SUPER_PAC,
  display_name: 'Americans for Good Things',
  aliases: ['AFGT', 'Good Things PAC'],
  status: EvidenceStatus.VERIFIED,
  confidence: makeConfidence(0.90, 'FEC registered but limited activity history'),
  provenance: makeProvenance('automated_ingest', [
    makeCitation(
      SourceClass.FEC_DISCLOSURE,
      'FEC Committee Registration',
      'https://fec.gov/data/committee/C00888888',
      '2023-06-15'
    ),
  ]),
  first_seen: '2023-06-15T00:00:00Z',
  last_updated: now,
  is_active: true,
  merged_from: [],
  tags: ['generic', 'super_pac'],
  fec_committee_id: 'C00888888',
  legal_name: 'AMERICANS FOR GOOD THINGS',
  treasurer: 'Jane Doe',
  registration_date: '2023-06-15',
  total_raised: 5000000,
  total_spent: 4500000,
  financials_as_of: '2024-06-30',
};

// ============================================================================
// SAMPLE DARK MONEY ENTITIES
// ============================================================================

export const SAMPLE_DARK_MONEY_501C4: DarkMoneyEntityNode = {
  node_id: 'dark_001_civic',
  node_type: NodeType.DARK_MONEY_ENTITY,
  display_name: 'Civic Engagement Alliance',
  aliases: ['CEA', 'CE Alliance'],
  status: EvidenceStatus.INFERRED,
  confidence: makeConfidence(
    0.65,
    'IRS 501(c)(4) status confirmed but donor sources unknown',
    ['IRS determination letter exists'],
    ['No donor disclosure required', 'Limited public filings']
  ),
  provenance: makeProvenance('manual', [
    makeCitation(
      SourceClass.WATCHDOG_REPORT,
      'CREW Dark Money Report',
      'https://crew.org/reports/dark-money-2024',
      '2024-03-01'
    ),
  ]),
  first_seen: '2023-01-01T00:00:00Z',
  last_updated: now,
  is_active: true,
  merged_from: [],
  tags: ['501c4', 'dark_money', 'disclosure_gap'],
  ein: '12-3456789',
  tax_status: '501c4',
  legal_name: 'CIVIC ENGAGEMENT ALLIANCE INC',
  state_of_incorporation: 'Delaware',
  is_suspected_shell: false,
  shell_evidence: null,
  donor_disclosure: 'none',
  is_money_trail_terminus: true,
  terminus_info: {
    terminus_node_id: 'dark_001_civic',
    reason: 'disclosure_gap',
    explanation:
      '501(c)(4) organizations are not required to publicly disclose donors',
    display_message: 'The public money trail stops here.',
    missing_disclosure_type: 'Schedule B donor disclosure',
    responsible_regulator: 'IRS',
  },
};

export const SAMPLE_SHELL_COMPANY: DarkMoneyEntityNode = {
  node_id: 'dark_002_shell',
  node_type: NodeType.DARK_MONEY_ENTITY,
  display_name: 'Delaware Holdings LLC',
  aliases: ['DH LLC'],
  status: EvidenceStatus.INFERRED,
  confidence: makeConfidence(
    0.45,
    'Suspected shell company - minimal public footprint',
    [],
    [
      'No employees found',
      'Address is registered agent only',
      'Single purpose entity',
    ]
  ),
  provenance: makeProvenance('entity_resolution', [
    makeCitation(
      SourceClass.INVESTIGATIVE_REPORTING,
      'ProPublica Shell Company Investigation',
      'https://propublica.org/investigation/shell-companies-2024',
      '2024-04-15'
    ),
  ]),
  first_seen: '2024-04-15T00:00:00Z',
  last_updated: now,
  is_active: true,
  merged_from: [],
  tags: ['shell_company', 'suspected', 'needs_investigation'],
  ein: null,
  tax_status: 'llc',
  legal_name: 'DELAWARE HOLDINGS LLC',
  state_of_incorporation: 'Delaware',
  is_suspected_shell: true,
  shell_evidence:
    'No employees, registered agent address only, formed 30 days before large contribution',
  donor_disclosure: 'none',
  is_money_trail_terminus: true,
  terminus_info: {
    terminus_node_id: 'dark_002_shell',
    reason: 'shell_company',
    explanation:
      'LLC with no public business activity, likely created to obscure funding source',
    display_message: 'The public money trail stops here.',
    missing_disclosure_type: 'Beneficial ownership disclosure',
    responsible_regulator: 'FinCEN',
  },
};

// ============================================================================
// SAMPLE EXPENDITURES
// ============================================================================

export const SAMPLE_EXPENDITURE_ATTACK_AD: ExpenditureNode = {
  node_id: 'exp_001_attack',
  node_type: NodeType.EXPENDITURE,
  display_name: 'IE Against Jane Progressive - TV Buy',
  aliases: [],
  status: EvidenceStatus.VERIFIED,
  confidence: makeConfidence(
    0.98,
    'FEC independent expenditure report',
    ['FEC 24-hour IE report filed', 'Ad library confirmation']
  ),
  provenance: makeProvenance('automated_ingest', [
    makeCitation(
      SourceClass.FEC_DISCLOSURE,
      'FEC Form 24: 24-Hour Report of Independent Expenditure',
      'https://fec.gov/data/independent-expenditures',
      '2024-05-15'
    ),
  ]),
  first_seen: '2024-05-15T00:00:00Z',
  last_updated: now,
  is_active: true,
  merged_from: [],
  tags: ['attack_ad', 'television', 'independent_expenditure'],
  fec_transaction_id: 'SA24_12345678',
  amount: 2500000,
  currency: 'USD',
  expenditure_date: '2024-05-15',
  purpose: 'Television Advertising - Opposing',
  payee: 'WMUR-TV',
  payee_address: 'Manchester, NH',
  is_independent_expenditure: true,
  support_oppose: 'oppose',
  target_candidate_id: 'cand_001_progressive',
  election_type: 'primary',
};

// ============================================================================
// SAMPLE AD CREATIVES
// ============================================================================

export const SAMPLE_ATTACK_AD_CREATIVE: AdCreativeNode = {
  node_id: 'ad_001_attack',
  node_type: NodeType.AD_CREATIVE,
  display_name: 'Too Extreme for California - TV Spot',
  aliases: ['Too Extreme Ad'],
  status: EvidenceStatus.VERIFIED,
  confidence: makeConfidence(
    0.95,
    'Confirmed via Google Ad Library',
    ['Google Transparency Report entry', 'Archival copy preserved']
  ),
  provenance: makeProvenance('automated_ingest', [
    makeCitation(
      SourceClass.POLITICAL_AD_LIBRARY,
      'Google Political Ad Library Entry',
      'https://adstransparency.google.com/advertiser/AR123456789',
      '2024-05-10'
    ),
  ]),
  first_seen: '2024-05-10T00:00:00Z',
  last_updated: now,
  is_active: false,
  merged_from: [],
  tags: ['attack_ad', 'television', 'verified'],
  platform: 'google',
  platform_ad_id: 'AR123456789',
  ad_library_url: 'https://adstransparency.google.com/advertiser/AR123456789',
  creative_type: 'video',
  transcript:
    'Jane Progressive says she supports working families. But Progressive voted against tax relief for small businesses. Progressive sided with big corporations. Jane Progressive: too extreme for California.',
  is_attack_ad: true,
  attack_theme_ids: ['theme_001_extreme', 'theme_002_taxes'],
  target_candidate_id: 'cand_001_progressive',
  supporting_candidate_id: null,
  first_seen_date: '2024-05-10',
  last_seen_date: '2024-05-25',
  estimated_impressions: 5000000,
  estimated_spend: {
    min: 2000000,
    max: 2500000,
  },
  geo_targeting: ['California', 'CA-15'],
  demo_targeting: ['18-65', 'All genders'],
  archived_creative_url: 'https://archive.org/details/ad_001_attack',
};

// ============================================================================
// SAMPLE ATTACK THEMES
// ============================================================================

export const SAMPLE_ATTACK_THEME_EXTREME: AttackThemeNode = {
  node_id: 'theme_001_extreme',
  node_type: NodeType.ATTACK_THEME,
  display_name: 'Too Extreme',
  aliases: ['Radical', 'Out of Touch'],
  status: EvidenceStatus.VERIFIED,
  confidence: makeConfidence(
    0.85,
    'Documented attack theme pattern across multiple campaigns'
  ),
  provenance: makeProvenance('manual', [
    makeCitation(
      SourceClass.WATCHDOG_REPORT,
      'Ad Fontes Media Attack Ad Analysis',
      'https://adfontesmedia.com/attack-patterns',
      '2024-01-15'
    ),
  ]),
  first_seen: '2020-01-01T00:00:00Z',
  last_updated: now,
  is_active: true,
  merged_from: [],
  tags: ['attack_theme', 'common'],
  theme_category: 'Character Attack',
  theme_name: 'Too Extreme',
  description:
    'Portrays candidate as ideologically extreme or out of mainstream',
  keywords: ['extreme', 'radical', 'out of touch', 'too far'],
  is_documented_disinfo: false,
  fact_check_status: 'mixed',
  fact_check_citations: [],
};

// ============================================================================
// SAMPLE AIPAC LINKAGE
// ============================================================================

export const SAMPLE_AIPAC_LINKAGE_UDP: AIPACLinkageNode = {
  node_id: 'aipac_001_udp',
  node_type: NodeType.AIPAC_LINKAGE,
  display_name: 'UDP-AIPAC Connection',
  aliases: [],
  status: EvidenceStatus.VERIFIED,
  confidence: makeConfidence(
    0.95,
    'Publicly acknowledged AIPAC affiliation',
    [
      'AIPAC press release confirming affiliation',
      'Shared leadership overlap',
    ]
  ),
  provenance: makeProvenance('manual', [
    makeCitation(
      SourceClass.WATCHDOG_REPORT,
      'OpenSecrets AIPAC Profile',
      'https://opensecrets.org/orgs/aipac',
      '2024-03-01'
    ),
  ]),
  first_seen: '2021-12-01T00:00:00Z',
  last_updated: now,
  is_active: true,
  merged_from: [],
  tags: ['aipac', 'verified_connection'],
  aipac_entity: 'united_democracy_project',
  connection_type: 'funded',
  amount: 105000000,
  activity_description:
    'AIPAC-affiliated Super PAC for independent expenditures',
  connection_date: '2021-12-01',
};

// ============================================================================
// SAMPLE EDGES
// ============================================================================

export const SAMPLE_EDGE_FUNDING: FinancialEdge = {
  edge_id: 'edge_001_funds',
  source_node_id: 'spac_001_udp',
  target_node_id: 'exp_001_attack',
  edge_type: EdgeType.FUNDS,
  sources: [
    makeCitation(
      SourceClass.FEC_DISCLOSURE,
      'FEC Independent Expenditure Report',
      'https://fec.gov/data/independent-expenditures',
      '2024-05-15'
    ),
  ],
  date: '2024-05-15',
  date_range: null,
  evidence_type: EvidenceType.FINANCIAL_TRANSACTION,
  confidence: makeConfidence(
    0.98,
    'FEC filing directly documents this transaction'
  ),
  status: EvidenceStatus.VERIFIED,
  provenance: makeProvenance('automated_ingest', []),
  is_active: true,
  label: 'United Democracy Project funded attack ad expenditure',
  metadata: {},
  amount_cents: 250000000,
  currency: 'USD',
  transaction_type: 'expenditure',
  fec_transaction_id: 'SA24_12345678',
  is_aggregated: false,
  transaction_count: null,
  earmarked_for: null,
};

export const SAMPLE_EDGE_ATTACKS: TargetingEdge = {
  edge_id: 'edge_002_attacks',
  source_node_id: 'ad_001_attack',
  target_node_id: 'cand_001_progressive',
  edge_type: EdgeType.ATTACKS,
  sources: [
    makeCitation(
      SourceClass.POLITICAL_AD_LIBRARY,
      'Google Ad Library',
      'https://adstransparency.google.com',
      '2024-05-10'
    ),
  ],
  date: '2024-05-10',
  date_range: {
    start: '2024-05-10',
    end: '2024-05-25',
  },
  evidence_type: EvidenceType.AD_PLACEMENT,
  confidence: makeConfidence(
    0.95,
    'Ad content directly names and attacks candidate'
  ),
  status: EvidenceStatus.VERIFIED,
  provenance: makeProvenance('automated_ingest', []),
  is_active: true,
  label: 'Attack ad targeting Jane Progressive',
  metadata: {
    ad_id: 'ad_001_attack',
    themes: ['theme_001_extreme'],
  },
  intensity: 'primary',
  sentiment: 'negative',
};

export const SAMPLE_EDGE_DARK_MONEY_FUNDS: FinancialEdge = {
  edge_id: 'edge_003_dark_funds',
  source_node_id: 'dark_001_civic',
  target_node_id: 'spac_002_generic',
  edge_type: EdgeType.FUNDS,
  sources: [
    makeCitation(
      SourceClass.FEC_DISCLOSURE,
      'FEC Schedule A - Itemized Receipts',
      'https://fec.gov/data/receipts',
      '2024-03-01'
    ),
  ],
  date: '2024-03-01',
  date_range: null,
  evidence_type: EvidenceType.FINANCIAL_TRANSACTION,
  confidence: makeConfidence(
    0.85,
    'FEC receipt filed but original donor unknown',
    ['FEC filing exists'],
    ['501(c)(4) does not disclose donors']
  ),
  status: EvidenceStatus.VERIFIED,
  provenance: makeProvenance('automated_ingest', []),
  is_active: true,
  label: 'Dark money to Super PAC (original source unknown)',
  metadata: {
    terminus_warning:
      'Upstream funding sources are not publicly disclosed',
  },
  amount_cents: 500000000,
  currency: 'USD',
  transaction_type: 'contribution',
  fec_transaction_id: 'SA11_87654321',
  is_aggregated: false,
  transaction_count: null,
  earmarked_for: null,
};

// ============================================================================
// SAMPLE QUERY RESULTS
// ============================================================================

export const SAMPLE_FUNDING_CHAIN: FundingChainResult = {
  root_entity: SAMPLE_SUPER_PAC_UDP,
  chain: [
    {
      depth: 1,
      from_node: SAMPLE_SUPER_PAC_UDP,
      to_node: SAMPLE_EXPENDITURE_ATTACK_AD,
      edge: SAMPLE_EDGE_FUNDING,
      cumulative_amount: 2500000,
    },
  ],
  terminus_nodes: [],
  total_traceable: 2500000,
  total_untraceable: 0,
  disclosure_gaps: [],
};

export const SAMPLE_FUNDING_CHAIN_WITH_DARK_MONEY: FundingChainResult = {
  root_entity: SAMPLE_SUPER_PAC_GENERIC,
  chain: [
    {
      depth: 1,
      from_node: SAMPLE_DARK_MONEY_501C4,
      to_node: SAMPLE_SUPER_PAC_GENERIC,
      edge: SAMPLE_EDGE_DARK_MONEY_FUNDS,
      cumulative_amount: 5000000,
    },
  ],
  terminus_nodes: [
    {
      node: SAMPLE_DARK_MONEY_501C4,
      terminus_info: SAMPLE_DARK_MONEY_501C4.terminus_info!,
    },
  ],
  total_traceable: 5000000,
  total_untraceable: 5000000,
  disclosure_gaps: [
    'Civic Engagement Alliance (501c4) does not disclose donors',
  ],
};

export const SAMPLE_ATTACKERS_RESULT: AttackersQueryResult = {
  target_candidate: SAMPLE_CANDIDATE_PROGRESSIVE,
  attackers: [
    {
      attacker_node: SAMPLE_SUPER_PAC_UDP,
      attack_edges: [SAMPLE_EDGE_ATTACKS],
      ad_creatives: [SAMPLE_ATTACK_AD_CREATIVE],
      total_spend: 2500000,
      attack_themes: [SAMPLE_ATTACK_THEME_EXTREME],
      funding_chain: SAMPLE_FUNDING_CHAIN,
    },
  ],
  summary: {
    total_attackers: 1,
    total_attack_ads: 1,
    total_estimated_spend: 2500000,
    top_attack_themes: ['Too Extreme'],
  },
};

export const SAMPLE_AIPAC_SPENDING_RESULT: AIPACSpendingQueryResult = {
  target_candidate: SAMPLE_CANDIDATE_PROGRESSIVE,
  aipac_linked_spending: [
    {
      spender_node: SAMPLE_SUPER_PAC_UDP,
      aipac_linkage: SAMPLE_AIPAC_LINKAGE_UDP,
      expenditures: [SAMPLE_EXPENDITURE_ATTACK_AD],
      ad_creatives: [SAMPLE_ATTACK_AD_CREATIVE],
      total_amount: 2500000,
      support_oppose: 'oppose',
    },
  ],
  aligned_group_spending: [],
  summary: {
    total_aipac_linked: 2500000,
    total_aligned_groups: 0,
    total_supporting: 0,
    total_opposing: 2500000,
  },
};

// ============================================================================
// ENTITY RESOLUTION TEST CASES
// ============================================================================

export const ENTITY_RESOLUTION_CASES = [
  {
    input: [
      { identifier_type: 'fec_committee_id', identifier_value: 'C00770941' },
    ],
    expected_node_id: 'spac_001_udp',
    expected_confidence: 0.99,
  },
  {
    input: [
      { identifier_type: 'name', identifier_value: 'United Democracy Project' },
      { identifier_type: 'alias', identifier_value: 'UDP' },
    ],
    expected_node_id: 'spac_001_udp',
    expected_confidence: 0.95,
  },
  {
    input: [
      { identifier_type: 'name', identifier_value: 'J Progressive' },
      { identifier_type: 'party', identifier_value: 'Democratic' },
      { identifier_type: 'state', identifier_value: 'CA' },
    ],
    expected_node_id: 'cand_001_progressive',
    expected_confidence: 0.85,
  },
];

// ============================================================================
// DUPLICATE DETECTION TEST CASES
// ============================================================================

export const DUPLICATE_DETECTION_CASES = [
  {
    node_a: {
      ...SAMPLE_CANDIDATE_PROGRESSIVE,
      node_id: 'cand_dup_001',
      display_name: 'Jane Progressive',
    },
    node_b: {
      ...SAMPLE_CANDIDATE_PROGRESSIVE,
      node_id: 'cand_dup_002',
      display_name: 'J. Progressive',
      aliases: ['Jane Progressive'],
    },
    expected_similarity: 0.92,
    should_merge: true,
  },
  {
    node_a: SAMPLE_CANDIDATE_PROGRESSIVE,
    node_b: SAMPLE_CANDIDATE_CHALLENGER,
    expected_similarity: 0.15,
    should_merge: false,
  },
];

// ============================================================================
// DISCLOSURE GAP SCENARIOS
// ============================================================================

export const DISCLOSURE_GAP_SCENARIOS: MoneyTrailTerminus[] = [
  {
    terminus_node_id: 'dark_001_civic',
    reason: 'disclosure_gap',
    explanation:
      '501(c)(4) organizations are not required to publicly disclose their donors under current law',
    display_message: 'The public money trail stops here.',
    missing_disclosure_type: 'Schedule B donor disclosure',
    responsible_regulator: 'IRS',
  },
  {
    terminus_node_id: 'dark_002_shell',
    reason: 'shell_company',
    explanation:
      'LLC formed in Delaware with no apparent business operations, registered agent address only',
    display_message: 'The public money trail stops here.',
    missing_disclosure_type: 'Beneficial ownership disclosure',
    responsible_regulator: 'FinCEN',
  },
  {
    terminus_node_id: 'foreign_001',
    reason: 'foreign_source',
    explanation:
      'Funds traced to foreign entity; foreign contributions prohibited but enforcement limited',
    display_message: 'The public money trail stops here.',
    missing_disclosure_type: 'Foreign principal disclosure (FARA)',
    responsible_regulator: 'DOJ FARA Unit',
  },
  {
    terminus_node_id: 'aggregate_001',
    reason: 'aggregated_small_donors',
    explanation:
      'Contributions under $200 are aggregated and individual donors not itemized',
    display_message: 'The public money trail stops here.',
    missing_disclosure_type: 'Itemized small donor disclosure',
    responsible_regulator: 'FEC',
  },
];

// ============================================================================
// EXPORT ALL FIXTURES
// ============================================================================

export const TEST_FIXTURES = {
  candidates: {
    progressive: SAMPLE_CANDIDATE_PROGRESSIVE,
    challenger: SAMPLE_CANDIDATE_CHALLENGER,
  },
  super_pacs: {
    udp: SAMPLE_SUPER_PAC_UDP,
    generic: SAMPLE_SUPER_PAC_GENERIC,
  },
  dark_money: {
    c501c4: SAMPLE_DARK_MONEY_501C4,
    shell: SAMPLE_SHELL_COMPANY,
  },
  expenditures: {
    attack_ad: SAMPLE_EXPENDITURE_ATTACK_AD,
  },
  ad_creatives: {
    attack: SAMPLE_ATTACK_AD_CREATIVE,
  },
  attack_themes: {
    extreme: SAMPLE_ATTACK_THEME_EXTREME,
  },
  aipac_linkages: {
    udp: SAMPLE_AIPAC_LINKAGE_UDP,
  },
  edges: {
    funding: SAMPLE_EDGE_FUNDING,
    attacks: SAMPLE_EDGE_ATTACKS,
    dark_money: SAMPLE_EDGE_DARK_MONEY_FUNDS,
  },
  query_results: {
    funding_chain: SAMPLE_FUNDING_CHAIN,
    funding_chain_dark: SAMPLE_FUNDING_CHAIN_WITH_DARK_MONEY,
    attackers: SAMPLE_ATTACKERS_RESULT,
    aipac_spending: SAMPLE_AIPAC_SPENDING_RESULT,
  },
  entity_resolution_cases: ENTITY_RESOLUTION_CASES,
  duplicate_detection_cases: DUPLICATE_DETECTION_CASES,
  disclosure_gaps: DISCLOSURE_GAP_SCENARIOS,
};

export default TEST_FIXTURES;
