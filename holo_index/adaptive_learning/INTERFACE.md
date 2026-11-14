# Adaptive Learning Interface

## Current truth boundary

This is an experimental package interface, not a production query or RSI
contract. HoloIndex CLI initialization is disabled because this path caused
hangs. No production caller can admit or promote its output. The only
orchestrator entry point below that exists is `process_adaptive_request()`;
there is no `record_feedback()` or `get_adaptation_metrics()` method.

## Public API

### Core Orchestrator

```python
class AdaptiveLearningOrchestrator:
    """Central coordinator for adaptive learning system"""

    def __init__(self):
        """Initialize all adaptive components"""

    async def process_adaptive_request(self,
                                      query: str,
                                      raw_results: List[Dict],
                                      raw_response: str,
                                      context: Optional[Dict[str, Any]] = None
                                      ) -> AdaptiveLearningResult:
        """
        Process request through adaptive learning pipeline

        Args:
            query: Original search query
            raw_results: Initial search results
            raw_response: Initial response
            context: Additional context

        Returns:
            AdaptiveLearningResult with experimental optimization outputs
        """

```

### Data Structures

```python
@dataclass
class AdaptiveLearningResult:
    """Result from adaptive learning processing"""
    query_processing: AdaptiveQueryResult
    search_optimization: OptimizedSearchResults
    response_optimization: OptimizedResponse
    memory_optimization: MemoryOptimizationResult
    overall_performance: Dict[str, float] = field(default_factory=dict)
    learning_insights: Dict[str, Any] = field(default_factory=dict)
    processing_metadata: Dict[str, Any] = field(default_factory=dict)
```

```python
@dataclass
class AdaptiveQueryResult:
    original_query: str
    enhanced_query: str
    intent: QueryIntent
    optimization_score: float
    processing_metadata: Dict[str, Any] = field(default_factory=dict)
```

```python
@dataclass
class OptimizedSearchResults:
    original_results: List[SearchResult]
    optimized_results: List[SearchResult]
    optimization_metadata: Dict[str, Any] = field(default_factory=dict)
    performance_metrics: Dict[str, float] = field(default_factory=dict)
```

```python
@dataclass
class OptimizedResponse:
    original_response: str
    optimized_response: str
    response_candidates: List[ResponseCandidate]
    optimization_metadata: Dict[str, Any] = field(default_factory=dict)
    quality_metrics: Dict[str, float] = field(default_factory=dict)
```

```python
@dataclass
class MemoryOptimizationResult:
    patterns_processed: int
    patterns_consolidated: int
    patterns_pruned: int
    optimization_metrics: Dict[str, float] = field(default_factory=dict)
    memory_efficiency: float = 0.0
    learning_adaptation: Dict[str, Any] = field(default_factory=dict)
```

### Historical component API sketch (not an implemented contract)

The signatures in this subsection predate the current async component
implementations. They are retained only as design history and must not be used
for imports, tests, or production integration.

#### Query Processor

```python
class AdaptiveQueryProcessor:
    """Learns to enhance queries"""

    def enhance_query(self, query: str) -> Tuple[str, float]:
        """
        Enhance query based on learned patterns

        Returns:
            (enhanced_query, confidence_score)
        """

    def learn_from_query(self, query: str,
                        results_quality: float):
        """Learn from query success/failure"""

    def get_query_patterns(self) -> List[QueryPattern]:
        """Get learned query patterns"""
```

#### Vector Search Optimizer

```python
class VectorSearchOptimizer:
    """Optimizes vector search operations"""

    def optimize_search(self, query: str,
                       results: List[Dict]) -> List[Dict]:
        """Rerank and optimize search results"""

    def learn_from_search(self, query: str,
                         results: List[Dict],
                         feedback: str):
        """Learn from search feedback"""

    def get_optimization_metrics(self) -> Dict[str, float]:
        """Get search optimization metrics"""
```

#### LLM Response Optimizer

```python
class LLMResponseOptimizer:
    """Enhances LLM responses"""

    def optimize_response(self, query: str,
                         response: str) -> Tuple[str, float]:
        """
        Optimize response based on learned patterns

        Returns:
            (optimized_response, quality_score)
        """

    def learn_from_response(self, query: str,
                           response: str,
                           rating: str):
        """Learn from response feedback"""

    def get_response_templates(self) -> List[ResponseTemplate]:
        """Get learned response templates"""
```

#### Memory Architecture Evolution

```python
class MemoryArchitectureEvolution:
    """Evolves memory management strategies"""

    def consolidate_patterns(self) -> ConsolidationResult:
        """Consolidate similar patterns"""

    def prune_memory(self, threshold: float = 0.3) -> PruningResult:
        """Remove unused patterns"""

    def optimize_access_patterns(self) -> OptimizationResult:
        """Optimize memory access patterns"""

    def get_memory_metrics(self) -> Dict[str, Any]:
        """Get memory usage metrics"""
```

## Usage Examples

### Isolated experimental processing

This source-shaped example is not the production HoloIndex query path. It may
initialize AgentDB-backed components and is appropriate only in a bounded test
or research harness.

```python
from holo_index.adaptive_learning import AdaptiveLearningOrchestrator
import asyncio

# Initialize
orchestrator = AdaptiveLearningOrchestrator()

# Process with adaptation
async def process_search(query):
    result = await orchestrator.process_adaptive_request(
        query=query,
        raw_results=search_results,
        raw_response=initial_response,
        context={
            'search_limit': 5,
            'advisor_enabled': True
        }
    )

    # Use enhanced results
    print(f"Enhanced Query: {result.query_processing.enhanced_query}")
    print(f"Adaptation Score: {result.overall_performance['system_adaptation_score']}")

    return result

# Run
result = asyncio.run(process_search("find authentication module"))
```

### Feedback and monitoring

No orchestrator-level feedback or metrics methods are implemented. Component
insight methods are experimental and do not authorize live ranker changes.

### Historical direct-component sketch (not executable)

The following example names methods that are not present in the current
components. Use source inspection and focused tests before any future public
component API is admitted.

```python
from holo_index.adaptive_learning import AdaptiveQueryProcessor

# Use query processor directly
processor = AdaptiveQueryProcessor()
enhanced_query, confidence = processor.enhance_query("auth module")
print(f"Enhanced: {enhanced_query} (confidence: {confidence:.2f})")

# Learn from outcome
processor.learn_from_query(enhanced_query, results_quality=0.8)
```

## Integration Points

### With HoloIndex CLI

Not integrated. `_cli_main.py` imports the class when available, but the
initialization block is commented out because it caused hangs. Import
availability is not runtime enablement.

### Storage contract

There is no admitted package-wide storage contract. Components use AgentDB or
component-specific experimental paths. No path in this package is authorized
to store or promote production ranker state.

## Performance boundary

The public coroutine is asynchronous, but no accepted latency, memory, pruning,
learning-rate, or adaptation-interval contract has been benchmarked. Component
constants must not be reported as production defaults.

## Error Handling

`process_adaptive_request()` catches broad component failures and returns a
fallback `AdaptiveLearningResult` with `processing_metadata["error"]`. There is
no stable public exception taxonomy.

## WSP Compliance

- **WSP 48**: Experimental RSI candidate work only; production RSI is absent
- **WSP 60**: Experimental memory work, without admitted production writeback
- **WSP 11**: Complete interface documentation
- **WSP 84**: Existing-source verification requirement
