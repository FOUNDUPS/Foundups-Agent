/**
 * Vote/Ballots Source Adapters
 *
 * Adapters for each primary source class:
 * 1. Political ad libraries (Google, Meta, etc.)
 * 2. Campaign finance disclosures (FEC)
 * 3. Outside spending databases (OpenSecrets, FollowTheMoney)
 * 4. Committee/PAC filings
 * 5. Candidate websites/statements
 * 6. Watchdog reports
 * 7. Investigative reporting
 * 8. User challenge submissions
 */

export { FECAdapter, createFECAdapter, FECAdapterConfig, FECRawData } from './fec_adapter';

// Future adapters - stubs for interface consistency

import {
  SourceAdapter,
  SourceClass,
  GraphNode,
  GraphEdge,
  AdapterQuery,
  RateLimitStatus,
  ValidationResult,
  AdapterError,
} from '../src/evidence_graph_schema';

/**
 * Google Ad Library Adapter (stub)
 *
 * Fetches political ads from Google Transparency Report
 * https://adstransparency.google.com/
 */
export interface GoogleAdsAdapterConfig {
  developer_token: string;
}

export class GoogleAdsAdapter implements SourceAdapter<unknown, GraphNode, GraphEdge> {
  readonly adapter_id = 'google_ads_v1';
  readonly source_class = SourceClass.POLITICAL_AD_LIBRARY;
  readonly supported_formats = ['json'];

  async parse(_raw: unknown): Promise<{ nodes: GraphNode[]; edges: GraphEdge[]; errors: AdapterError[] }> {
    // TODO: Implement Google Ad Library parsing
    return { nodes: [], edges: [], errors: [] };
  }

  async validate(_data: { nodes: GraphNode[]; edges: GraphEdge[] }): Promise<ValidationResult> {
    return { is_valid: true, errors: [], warnings: [], stats: { nodes_validated: 0, edges_validated: 0, nodes_rejected: 0, edges_rejected: 0 } };
  }

  async fetch(_query: AdapterQuery): Promise<unknown> {
    // TODO: Implement Google Transparency Report API
    return {};
  }

  async healthCheck(): Promise<boolean> {
    return true;
  }

  getRateLimitStatus(): RateLimitStatus {
    return { is_limited: false, requests_remaining: 10000, reset_at: null, daily_limit: 10000, daily_used: 0 };
  }
}

/**
 * Meta Ad Library Adapter (stub)
 *
 * Fetches political ads from Meta Ad Library
 * https://www.facebook.com/ads/library/
 */
export interface MetaAdsAdapterConfig {
  access_token: string;
  api_version: string;
}

export class MetaAdsAdapter implements SourceAdapter<unknown, GraphNode, GraphEdge> {
  readonly adapter_id = 'meta_ads_v1';
  readonly source_class = SourceClass.POLITICAL_AD_LIBRARY;
  readonly supported_formats = ['json'];

  async parse(_raw: unknown): Promise<{ nodes: GraphNode[]; edges: GraphEdge[]; errors: AdapterError[] }> {
    // TODO: Implement Meta Ad Library parsing
    return { nodes: [], edges: [], errors: [] };
  }

  async validate(_data: { nodes: GraphNode[]; edges: GraphEdge[] }): Promise<ValidationResult> {
    return { is_valid: true, errors: [], warnings: [], stats: { nodes_validated: 0, edges_validated: 0, nodes_rejected: 0, edges_rejected: 0 } };
  }

  async fetch(_query: AdapterQuery): Promise<unknown> {
    // TODO: Implement Meta Ad Library API
    return {};
  }

  async healthCheck(): Promise<boolean> {
    return true;
  }

  getRateLimitStatus(): RateLimitStatus {
    return { is_limited: false, requests_remaining: 200, reset_at: null, daily_limit: null, daily_used: null };
  }
}

/**
 * OpenSecrets Adapter (stub)
 *
 * Fetches data from Center for Responsive Politics
 * https://www.opensecrets.org/api
 */
export interface OpenSecretsAdapterConfig {
  api_key: string;
}

export class OpenSecretsAdapter implements SourceAdapter<unknown, GraphNode, GraphEdge> {
  readonly adapter_id = 'opensecrets_v1';
  readonly source_class = SourceClass.OUTSIDE_SPENDING_DATABASE;
  readonly supported_formats = ['json', 'xml'];

  async parse(_raw: unknown): Promise<{ nodes: GraphNode[]; edges: GraphEdge[]; errors: AdapterError[] }> {
    // TODO: Implement OpenSecrets parsing
    return { nodes: [], edges: [], errors: [] };
  }

  async validate(_data: { nodes: GraphNode[]; edges: GraphEdge[] }): Promise<ValidationResult> {
    return { is_valid: true, errors: [], warnings: [], stats: { nodes_validated: 0, edges_validated: 0, nodes_rejected: 0, edges_rejected: 0 } };
  }

  async fetch(_query: AdapterQuery): Promise<unknown> {
    // TODO: Implement OpenSecrets API
    return {};
  }

  async healthCheck(): Promise<boolean> {
    return true;
  }

  getRateLimitStatus(): RateLimitStatus {
    return { is_limited: false, requests_remaining: 100, reset_at: null, daily_limit: null, daily_used: null };
  }
}

/**
 * Watchdog Report Adapter (stub)
 *
 * Fetches data from watchdog organizations:
 * - CREW (Citizens for Responsibility and Ethics)
 * - Sunlight Foundation
 * - Campaign Legal Center
 */
export class WatchdogAdapter implements SourceAdapter<unknown, GraphNode, GraphEdge> {
  readonly adapter_id = 'watchdog_v1';
  readonly source_class = SourceClass.WATCHDOG_REPORT;
  readonly supported_formats = ['json', 'html'];

  async parse(_raw: unknown): Promise<{ nodes: GraphNode[]; edges: GraphEdge[]; errors: AdapterError[] }> {
    return { nodes: [], edges: [], errors: [] };
  }

  async validate(_data: { nodes: GraphNode[]; edges: GraphEdge[] }): Promise<ValidationResult> {
    return { is_valid: true, errors: [], warnings: [], stats: { nodes_validated: 0, edges_validated: 0, nodes_rejected: 0, edges_rejected: 0 } };
  }

  async fetch(_query: AdapterQuery): Promise<unknown> {
    return {};
  }

  async healthCheck(): Promise<boolean> {
    return true;
  }

  getRateLimitStatus(): RateLimitStatus {
    return { is_limited: false, requests_remaining: 1000, reset_at: null, daily_limit: null, daily_used: null };
  }
}

/**
 * User Submission Adapter
 *
 * Handles community-submitted evidence
 * All submissions start as HYPOTHESIS status until verified
 */
export class UserSubmissionAdapter implements SourceAdapter<unknown, GraphNode, GraphEdge> {
  readonly adapter_id = 'user_submission_v1';
  readonly source_class = SourceClass.USER_SUBMISSION;
  readonly supported_formats = ['json'];

  async parse(_raw: unknown): Promise<{ nodes: GraphNode[]; edges: GraphEdge[]; errors: AdapterError[] }> {
    // TODO: Implement user submission parsing
    // CRITICAL: All parsed items MUST have status = HYPOTHESIS
    return { nodes: [], edges: [], errors: [] };
  }

  async validate(_data: { nodes: GraphNode[]; edges: GraphEdge[] }): Promise<ValidationResult> {
    // Validate format only - content verification is separate
    return { is_valid: true, errors: [], warnings: ['User submissions require manual verification'], stats: { nodes_validated: 0, edges_validated: 0, nodes_rejected: 0, edges_rejected: 0 } };
  }

  async fetch(_query: AdapterQuery): Promise<unknown> {
    // User submissions are pushed, not fetched
    return {};
  }

  async healthCheck(): Promise<boolean> {
    return true;
  }

  getRateLimitStatus(): RateLimitStatus {
    return { is_limited: false, requests_remaining: 1000, reset_at: null, daily_limit: null, daily_used: null };
  }
}

/**
 * Adapter Registry
 *
 * Centralized registry for all source adapters
 */
export const ADAPTER_REGISTRY: Record<string, () => SourceAdapter<unknown, GraphNode, GraphEdge>> = {
  fec: () => new (require('./fec_adapter').FECAdapter)({ api_key: '', base_url: '', rate_limit_per_hour: 1000, timeout_ms: 30000 }),
  google_ads: () => new GoogleAdsAdapter(),
  meta_ads: () => new MetaAdsAdapter(),
  opensecrets: () => new OpenSecretsAdapter(),
  watchdog: () => new WatchdogAdapter(),
  user_submission: () => new UserSubmissionAdapter(),
};

export function getAdapter(adapterId: string): SourceAdapter<unknown, GraphNode, GraphEdge> | null {
  const factory = ADAPTER_REGISTRY[adapterId];
  return factory ? factory() : null;
}

export function listAdapters(): string[] {
  return Object.keys(ADAPTER_REGISTRY);
}
