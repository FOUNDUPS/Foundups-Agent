# Vote/Ballots FoundUp - Interface Specification

## Public API

### Graph Operations

```typescript
interface EvidenceGraph {
  // Node CRUD
  addNode(node: GraphNode): Promise<string>;
  getNode(node_id: string): Promise<GraphNode | null>;
  updateNode(node_id: string, updates: Partial<GraphNode>): Promise<void>;
  deleteNode(node_id: string): Promise<void>;

  // Edge CRUD
  addEdge(edge: GraphEdge): Promise<string>;
  getEdge(edge_id: string): Promise<GraphEdge | null>;
  updateEdge(edge_id: string, updates: Partial<GraphEdge>): Promise<void>;
  deleteEdge(edge_id: string): Promise<void>;

  // Entity Resolution
  resolveEntity(identifiers: Record<string, string>[]): Promise<EntityResolutionResult>;
  detectDuplicates(node_id: string): Promise<DuplicateDetectionResult>;
  mergeNodes(merge_operation: MergeOperation): Promise<string>;

  // Queries
  queryAttackers(query: AttackersQuery): Promise<AttackersQueryResult>;
  queryFundingChain(query: FundingChainQuery): Promise<FundingChainResult>;
  queryAIPACSpending(query: AIPACSpendingQuery): Promise<AIPACSpendingQueryResult>;
  traverse(query: GraphTraversalQuery): Promise<GraphNode[]>;

  // Bulk
  bulkImport(nodes: GraphNode[], edges: GraphEdge[]): Promise<BulkImportResult>;
  export(format: 'json' | 'graphml' | 'neo4j'): Promise<string>;
}
```

### Source Adapters

```typescript
interface SourceAdapter<TRawData, TNode, TEdge> {
  adapter_id: string;
  source_class: SourceClass;
  supported_formats: string[];

  parse(raw: TRawData): Promise<{ nodes: TNode[]; edges: TEdge[]; errors: AdapterError[] }>;
  validate(data: { nodes: TNode[]; edges: TEdge[] }): Promise<ValidationResult>;
  fetch(query: AdapterQuery): Promise<TRawData>;
  healthCheck(): Promise<boolean>;
  getRateLimitStatus(): RateLimitStatus;
}
```

### Cache Interface

```typescript
interface EvidenceGraphCache {
  get<T>(key: string): Promise<CacheEntry<T> | null>;
  set<T>(key: string, value: T, ttl_seconds?: number): Promise<void>;
  invalidate(key: string): Promise<void>;
  invalidateByPattern(pattern: string): Promise<number>;
  invalidateBySourceClass(source_class: SourceClass): Promise<number>;
  getStats(): Promise<CacheStats>;
}
```

## Key Types

### Evidence Status

```typescript
enum EvidenceStatus {
  VERIFIED = 'verified',      // Primary source confirmed
  INFERRED = 'inferred',      // Derived via entity resolution
  HYPOTHESIS = 'hypothesis',  // User-submitted, unverified
  UNKNOWN = 'unknown',        // Disclosure gap
  RETRACTED = 'retracted'     // Source removed
}
```

### Confidence Score

```typescript
interface ConfidenceScore {
  score: number;              // 0.0 to 1.0
  justification: string;      // Human-readable reason
  supporting_factors: string[];
  diminishing_factors: string[];
  calculated_at: string;      // ISO 8601
}
```

### Money Trail Terminus

```typescript
interface MoneyTrailTerminus {
  terminus_node_id: string;
  reason: 'disclosure_gap' | 'shell_company' | 'foreign_source' | 'aggregated_small_donors' | 'unknown';
  explanation: string;
  display_message: 'The public money trail stops here.';  // REQUIRED constant
  missing_disclosure_type: string | null;
  responsible_regulator: string | null;
}
```

## Error Types

| Error | Code | Recoverable |
|-------|------|-------------|
| ValidationError | VALIDATION_ERROR | Yes |
| EntityResolutionError | ENTITY_RESOLUTION_ERROR | Yes |
| SourceAdapterError | SOURCE_ADAPTER_ERROR | Varies |
| DisclosureGapError | DISCLOSURE_GAP | No (by design) |

## Rate Limits

| Source | Limit | Window |
|--------|-------|--------|
| FEC API | 1000 | per hour |
| Google Ads | 10000 | per day |
| Meta Ads | 200 | per hour |
| OpenSecrets | 100 | per hour |

## Cache TTLs

| Source Class | TTL |
|--------------|-----|
| FEC Disclosure | 24 hours |
| Committee Filing | 24 hours |
| Ad Library | 6 hours |
| Outside Spending DB | 12 hours |
| Watchdog Report | 24 hours |
| Candidate Statement | 1 hour |
| Investigative Reporting | 24 hours |
| User Submission | 5 minutes |
