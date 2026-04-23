/**
 * FEC (Federal Election Commission) Data Adapter
 *
 * Fetches and parses data from FEC.gov API including:
 * - Candidate filings
 * - Committee registrations
 * - Contributions
 * - Independent expenditures
 * - Disbursements
 *
 * API Documentation: https://api.open.fec.gov/developers/
 */

import {
  SourceAdapter,
  SourceClass,
  AdapterQuery,
  AdapterError,
  ValidationResult,
  RateLimitStatus,
  GraphNode,
  GraphEdge,
  CandidateNode,
  CommitteeNode,
  PACNode,
  SuperPACNode,
  DonorNode,
  ExpenditureNode,
  FinancialEdge,
  NodeType,
  EdgeType,
  EvidenceStatus,
  EvidenceType,
  ConfidenceScore,
  SourceCitation,
  ProvenanceRecord,
} from '../src/evidence_graph_schema';

// ============================================================================
// FEC API TYPES
// ============================================================================

export interface FECAdapterConfig {
  api_key: string;
  base_url: string;
  rate_limit_per_hour: number;
  timeout_ms: number;
}

export interface FECCandidate {
  candidate_id: string;
  name: string;
  party: string;
  office: string;
  state: string;
  district: string;
  incumbent_challenge: string;
  candidate_status: string;
  principal_committees: { committee_id: string; name: string }[];
}

export interface FECCommittee {
  committee_id: string;
  name: string;
  committee_type: string;
  designation: string;
  treasurer_name: string;
  street_1: string;
  city: string;
  state: string;
  zip: string;
  candidate_ids: string[];
}

export interface FECIndependentExpenditure {
  committee_id: string;
  committee_name: string;
  candidate_id: string;
  candidate_name: string;
  support_oppose_indicator: 'S' | 'O';
  expenditure_amount: number;
  expenditure_date: string;
  payee_name: string;
  expenditure_description: string;
  transaction_id: string;
}

export interface FECContribution {
  committee_id: string;
  contributor_name: string;
  contributor_employer: string;
  contributor_occupation: string;
  contributor_city: string;
  contributor_state: string;
  contributor_zip: string;
  contribution_receipt_amount: number;
  contribution_receipt_date: string;
  transaction_id: string;
}

// ============================================================================
// ADAPTER IMPLEMENTATION
// ============================================================================

export class FECAdapter implements SourceAdapter<FECRawData, GraphNode, GraphEdge> {
  readonly adapter_id = 'fec_gov_v1';
  readonly source_class = SourceClass.FEC_DISCLOSURE;
  readonly supported_formats = ['json'];

  private config: FECAdapterConfig;
  private requestCount = 0;
  private lastResetTime = Date.now();

  constructor(config: FECAdapterConfig) {
    this.config = config;
  }

  async parse(raw: FECRawData): Promise<{
    nodes: GraphNode[];
    edges: GraphEdge[];
    errors: AdapterError[];
  }> {
    const nodes: GraphNode[] = [];
    const edges: GraphEdge[] = [];
    const errors: AdapterError[] = [];

    // Parse candidates
    if (raw.candidates) {
      for (const candidate of raw.candidates) {
        try {
          nodes.push(this.parseCandidateNode(candidate));
        } catch (e) {
          errors.push({
            error_code: 'PARSE_CANDIDATE_FAILED',
            message: e instanceof Error ? e.message : 'Unknown error',
            field: 'candidate',
            raw_value: candidate,
            recoverable: true,
          });
        }
      }
    }

    // Parse committees
    if (raw.committees) {
      for (const committee of raw.committees) {
        try {
          const node = this.parseCommitteeNode(committee);
          nodes.push(node);
        } catch (e) {
          errors.push({
            error_code: 'PARSE_COMMITTEE_FAILED',
            message: e instanceof Error ? e.message : 'Unknown error',
            field: 'committee',
            raw_value: committee,
            recoverable: true,
          });
        }
      }
    }

    // Parse independent expenditures
    if (raw.independent_expenditures) {
      for (const ie of raw.independent_expenditures) {
        try {
          const { node, edge } = this.parseIndependentExpenditure(ie);
          nodes.push(node);
          edges.push(edge);
        } catch (e) {
          errors.push({
            error_code: 'PARSE_IE_FAILED',
            message: e instanceof Error ? e.message : 'Unknown error',
            field: 'independent_expenditure',
            raw_value: ie,
            recoverable: true,
          });
        }
      }
    }

    // Parse contributions
    if (raw.contributions) {
      for (const contrib of raw.contributions) {
        try {
          const { node, edge } = this.parseContribution(contrib);
          nodes.push(node);
          edges.push(edge);
        } catch (e) {
          errors.push({
            error_code: 'PARSE_CONTRIBUTION_FAILED',
            message: e instanceof Error ? e.message : 'Unknown error',
            field: 'contribution',
            raw_value: contrib,
            recoverable: true,
          });
        }
      }
    }

    return { nodes, edges, errors };
  }

  async validate(data: { nodes: GraphNode[]; edges: GraphEdge[] }): Promise<ValidationResult> {
    const errors: AdapterError[] = [];
    let nodesRejected = 0;
    let edgesRejected = 0;

    // Validate nodes
    for (const node of data.nodes) {
      if (!node.node_id) {
        errors.push({
          error_code: 'MISSING_NODE_ID',
          message: 'Node missing required node_id',
          field: 'node_id',
          raw_value: node,
          recoverable: false,
        });
        nodesRejected++;
      }

      if (!node.provenance?.citations?.length) {
        errors.push({
          error_code: 'MISSING_CITATION',
          message: 'Node missing required source citation',
          field: 'provenance.citations',
          raw_value: node.node_id,
          recoverable: true,
        });
      }
    }

    // Validate edges
    for (const edge of data.edges) {
      if (!edge.sources?.length) {
        errors.push({
          error_code: 'EDGE_MISSING_SOURCE',
          message: 'Edge missing required source citation',
          field: 'sources',
          raw_value: edge.edge_id,
          recoverable: false,
        });
        edgesRejected++;
      }
    }

    return {
      is_valid: errors.filter(e => !e.recoverable).length === 0,
      errors,
      warnings: [],
      stats: {
        nodes_validated: data.nodes.length,
        edges_validated: data.edges.length,
        nodes_rejected: nodesRejected,
        edges_rejected: edgesRejected,
      },
    };
  }

  async fetch(query: AdapterQuery): Promise<FECRawData> {
    this.checkRateLimit();

    const result: FECRawData = {
      candidates: [],
      committees: [],
      independent_expenditures: [],
      contributions: [],
    };

    // Implementation would make actual API calls here
    // This is a stub showing the structure

    this.requestCount++;
    return result;
  }

  async healthCheck(): Promise<boolean> {
    try {
      // Would ping FEC API status endpoint
      return true;
    } catch {
      return false;
    }
  }

  getRateLimitStatus(): RateLimitStatus {
    const hourMs = 3600000;
    const timeSinceReset = Date.now() - this.lastResetTime;

    if (timeSinceReset > hourMs) {
      this.requestCount = 0;
      this.lastResetTime = Date.now();
    }

    return {
      is_limited: this.requestCount >= this.config.rate_limit_per_hour,
      requests_remaining: Math.max(0, this.config.rate_limit_per_hour - this.requestCount),
      reset_at: new Date(this.lastResetTime + hourMs).toISOString(),
      daily_limit: null,
      daily_used: null,
    };
  }

  // ============================================================================
  // PRIVATE PARSING METHODS
  // ============================================================================

  private parseCandidateNode(raw: FECCandidate): CandidateNode {
    const now = new Date().toISOString();
    const citation = this.makeFECCitation(
      `Candidate: ${raw.name}`,
      `https://fec.gov/data/candidate/${raw.candidate_id}`
    );

    return {
      node_id: `fec_cand_${raw.candidate_id}`,
      node_type: NodeType.CANDIDATE,
      display_name: raw.name,
      aliases: [],
      status: EvidenceStatus.VERIFIED,
      confidence: this.makeHighConfidence('FEC candidate registration'),
      provenance: this.makeProvenance([citation]),
      first_seen: now,
      last_updated: now,
      is_active: raw.candidate_status === 'C',
      merged_from: [],
      tags: ['fec_imported'],
      fec_candidate_id: raw.candidate_id,
      party: raw.party,
      office_sought_id: `office_${raw.office}_${raw.state}_${raw.district}`,
      is_incumbent: raw.incumbent_challenge === 'I',
      election_cycle: new Date().getFullYear().toString(),
      campaign_website: null,
      person_node_id: null,
      principal_committee_id: raw.principal_committees?.[0]?.committee_id || null,
      fec_status: raw.candidate_status === 'C' ? 'active' : 'terminated',
    };
  }

  private parseCommitteeNode(raw: FECCommittee): CommitteeNode | PACNode | SuperPACNode {
    const now = new Date().toISOString();
    const citation = this.makeFECCitation(
      `Committee: ${raw.name}`,
      `https://fec.gov/data/committee/${raw.committee_id}`
    );

    // Determine committee type
    if (raw.committee_type === 'O' || raw.committee_type === 'U') {
      // Super PAC
      return {
        node_id: `fec_comm_${raw.committee_id}`,
        node_type: NodeType.SUPER_PAC,
        display_name: raw.name,
        aliases: [],
        status: EvidenceStatus.VERIFIED,
        confidence: this.makeHighConfidence('FEC committee registration'),
        provenance: this.makeProvenance([citation]),
        first_seen: now,
        last_updated: now,
        is_active: true,
        merged_from: [],
        tags: ['fec_imported', 'super_pac'],
        fec_committee_id: raw.committee_id,
        legal_name: raw.name,
        treasurer: raw.treasurer_name,
        registration_date: null,
        total_raised: null,
        total_spent: null,
        financials_as_of: null,
      };
    }

    // Regular committee
    return {
      node_id: `fec_comm_${raw.committee_id}`,
      node_type: NodeType.COMMITTEE,
      display_name: raw.name,
      aliases: [],
      status: EvidenceStatus.VERIFIED,
      confidence: this.makeHighConfidence('FEC committee registration'),
      provenance: this.makeProvenance([citation]),
      first_seen: now,
      last_updated: now,
      is_active: true,
      merged_from: [],
      tags: ['fec_imported'],
      fec_committee_id: raw.committee_id,
      committee_type: this.mapCommitteeType(raw.committee_type),
      treasurer: raw.treasurer_name,
      address: `${raw.street_1}, ${raw.city}, ${raw.state} ${raw.zip}`,
      candidate_id: raw.candidate_ids?.[0] || null,
      irs_determination_date: null,
    };
  }

  private parseIndependentExpenditure(raw: FECIndependentExpenditure): {
    node: ExpenditureNode;
    edge: FinancialEdge;
  } {
    const now = new Date().toISOString();
    const citation = this.makeFECCitation(
      `Independent Expenditure: ${raw.committee_name}`,
      `https://fec.gov/data/independent-expenditures`
    );

    const node: ExpenditureNode = {
      node_id: `fec_ie_${raw.transaction_id}`,
      node_type: NodeType.EXPENDITURE,
      display_name: `IE: ${raw.expenditure_description}`,
      aliases: [],
      status: EvidenceStatus.VERIFIED,
      confidence: this.makeHighConfidence('FEC independent expenditure filing'),
      provenance: this.makeProvenance([citation]),
      first_seen: now,
      last_updated: now,
      is_active: true,
      merged_from: [],
      tags: ['fec_imported', 'independent_expenditure'],
      fec_transaction_id: raw.transaction_id,
      amount: raw.expenditure_amount,
      currency: 'USD',
      expenditure_date: raw.expenditure_date,
      purpose: raw.expenditure_description,
      payee: raw.payee_name,
      payee_address: null,
      is_independent_expenditure: true,
      support_oppose: raw.support_oppose_indicator === 'S' ? 'support' : 'oppose',
      target_candidate_id: `fec_cand_${raw.candidate_id}`,
      election_type: null,
    };

    const edge: FinancialEdge = {
      edge_id: `edge_ie_${raw.transaction_id}`,
      source_node_id: `fec_comm_${raw.committee_id}`,
      target_node_id: node.node_id,
      edge_type: EdgeType.FUNDS,
      sources: [citation],
      date: raw.expenditure_date,
      date_range: null,
      evidence_type: EvidenceType.FINANCIAL_TRANSACTION,
      confidence: this.makeHighConfidence('FEC filing'),
      status: EvidenceStatus.VERIFIED,
      provenance: this.makeProvenance([citation]),
      is_active: true,
      label: `${raw.committee_name} spent on ${raw.support_oppose_indicator === 'S' ? 'supporting' : 'opposing'} ${raw.candidate_name}`,
      metadata: {},
      amount_cents: Math.round(raw.expenditure_amount * 100),
      currency: 'USD',
      transaction_type: 'expenditure',
      fec_transaction_id: raw.transaction_id,
      is_aggregated: false,
      transaction_count: null,
      earmarked_for: null,
    };

    return { node, edge };
  }

  private parseContribution(raw: FECContribution): {
    node: DonorNode;
    edge: FinancialEdge;
  } {
    const now = new Date().toISOString();
    const citation = this.makeFECCitation(
      `Contribution to ${raw.committee_id}`,
      `https://fec.gov/data/receipts`
    );

    const donorId = this.generateDonorId(raw);

    const node: DonorNode = {
      node_id: donorId,
      node_type: NodeType.DONOR,
      display_name: raw.contributor_name,
      aliases: [],
      status: EvidenceStatus.VERIFIED,
      confidence: this.makeHighConfidence('FEC contribution filing'),
      provenance: this.makeProvenance([citation]),
      first_seen: now,
      last_updated: now,
      is_active: true,
      merged_from: [],
      tags: ['fec_imported'],
      donor_type: 'individual',
      total_contributed: raw.contribution_receipt_amount,
      contribution_period: {
        start: raw.contribution_receipt_date,
        end: raw.contribution_receipt_date,
      },
      is_aggregated_small_donors: false,
      person_node_id: null,
      org_node_id: null,
    };

    const edge: FinancialEdge = {
      edge_id: `edge_contrib_${raw.transaction_id}`,
      source_node_id: donorId,
      target_node_id: `fec_comm_${raw.committee_id}`,
      edge_type: EdgeType.DONATED_TO,
      sources: [citation],
      date: raw.contribution_receipt_date,
      date_range: null,
      evidence_type: EvidenceType.FINANCIAL_TRANSACTION,
      confidence: this.makeHighConfidence('FEC filing'),
      status: EvidenceStatus.VERIFIED,
      provenance: this.makeProvenance([citation]),
      is_active: true,
      label: `${raw.contributor_name} donated to committee`,
      metadata: {
        employer: raw.contributor_employer,
        occupation: raw.contributor_occupation,
      },
      amount_cents: Math.round(raw.contribution_receipt_amount * 100),
      currency: 'USD',
      transaction_type: 'contribution',
      fec_transaction_id: raw.transaction_id,
      is_aggregated: false,
      transaction_count: null,
      earmarked_for: null,
    };

    return { node, edge };
  }

  // ============================================================================
  // HELPER METHODS
  // ============================================================================

  private makeFECCitation(title: string, url: string): SourceCitation {
    const now = new Date().toISOString();
    return {
      citation_id: `cit_fec_${Date.now()}_${Math.random().toString(36).substring(7)}`,
      source_class: SourceClass.FEC_DISCLOSURE,
      title,
      url,
      archive_url: null,
      date: now,
      accessed_at: now,
      author: null,
      publisher: 'Federal Election Commission',
      excerpt: null,
      document_hash: null,
      is_live: true,
      last_verified: now,
    };
  }

  private makeHighConfidence(reason: string): ConfidenceScore {
    return {
      score: 0.95,
      justification: reason,
      supporting_factors: ['FEC official filing', 'Primary source'],
      diminishing_factors: [],
      calculated_at: new Date().toISOString(),
    };
  }

  private makeProvenance(citations: SourceCitation[]): ProvenanceRecord {
    return {
      created_at: new Date().toISOString(),
      created_by: this.adapter_id,
      creation_method: 'automated_ingest',
      citations,
      modifications: [],
      reviews: [],
    };
  }

  private mapCommitteeType(fecType: string): 'principal' | 'authorized' | 'leadership' | 'party' | 'other' {
    switch (fecType) {
      case 'P': return 'principal';
      case 'A': return 'authorized';
      case 'D': return 'leadership';
      case 'X':
      case 'Y':
      case 'Z': return 'party';
      default: return 'other';
    }
  }

  private generateDonorId(contrib: FECContribution): string {
    // Create deterministic ID from donor info
    const key = `${contrib.contributor_name}_${contrib.contributor_city}_${contrib.contributor_state}`.toLowerCase();
    return `donor_${Buffer.from(key).toString('base64').substring(0, 16)}`;
  }

  private checkRateLimit(): void {
    const status = this.getRateLimitStatus();
    if (status.is_limited) {
      throw new Error(`Rate limit exceeded. Resets at ${status.reset_at}`);
    }
  }
}

// ============================================================================
// RAW DATA TYPE
// ============================================================================

export interface FECRawData {
  candidates: FECCandidate[];
  committees: FECCommittee[];
  independent_expenditures: FECIndependentExpenditure[];
  contributions: FECContribution[];
}

// ============================================================================
// FACTORY
// ============================================================================

export function createFECAdapter(apiKey: string): FECAdapter {
  return new FECAdapter({
    api_key: apiKey,
    base_url: 'https://api.open.fec.gov/v1',
    rate_limit_per_hour: 1000,
    timeout_ms: 30000,
  });
}
