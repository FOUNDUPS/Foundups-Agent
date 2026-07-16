# AI Gateway Module Interface Documentation

## Public API

### Classes

#### `AIGateway`
Main class for AI service orchestration and routing.

**Constructor:**
```python
AIGateway(gateway_key: Optional[str] = None) -> AIGateway
```

**Methods:**
```python
call_with_fallback(prompt: str, task_type: str = "general", max_retries: int = 3) -> GatewayResult
call_optimized(prompt: str, task_type: str = "general") -> GatewayResult
get_usage_stats() -> Dict[str, Any]
get_available_providers() -> List[str]
```

#### `GatewayResult`
Data class containing AI call results.

**Attributes:**
- `response: str` - AI-generated response
- `provider: str` - AI provider used (openai, anthropic, grok, gemini)
- `model: str` - Specific model used
- `duration: float` - Response time in seconds
- `cost_estimate: float` - Estimated API cost
- `success: bool` - Whether the call succeeded

### Functions

#### `quick_call(base_url: str, query: str, task_type: str = "general") -> str`
Convenience function for quick AI calls without creating a client instance.

#### `test_gateway() -> bool`
Test gateway connectivity and configuration.

#### Model Intelligence Catalog

```python
normalize_static_registry_cards(...) -> tuple[ModelCapabilityCard, ...]
normalize_openrouter_catalog(payload) -> tuple[tuple[ModelCapabilityCard, ...], tuple[ModelCatalogRejectedRecord, ...]]
normalize_local_role_cards(selections) -> tuple[ModelCapabilityCard, ...]
build_model_catalog_snapshot(cards, ...) -> ModelCatalogSnapshot
build_canonical_model_catalog(...) -> ModelCatalogSnapshot
```

These functions produce immutable catalog evidence for downstream model
selection. They do not call provider APIs, execute commands, compress output,
benchmark models, or select a RedDog/Fusion panel.

`ModelCapabilityCard` captures provider, canonical model ID, availability,
context window, modalities, supported parameters, rough cost metadata, task
families, and promotion state. `ModelCatalogSnapshot` binds cards and rejected
records to a deterministic `snapshot_id`.

#### Model Intelligence Selection

```python
select_models_for_task(snapshot, requirements) -> ModelSelectionReceipt
```

`ModelTaskRequirements` describes task family, single/panel mode, evaluation vs
production purpose, required modalities, context size, tool/structured/reasoning
requirements, cost ceilings, provider allow/deny sets, candidate count, and
minimum verifier pass rate.

`ModelSelectionReceipt` binds the selected model IDs, ranked candidates,
rejection reasons, catalog snapshot ID, and requirements. Evaluation mode may
select candidates for benchmarking. Production mode requires measured champion
evidence and fails closed for unbenchmarked candidates.

## Configuration

### Environment Variables
- `AI_GATEWAY_API_KEY`: Primary gateway API key (optional)
- `OPENAI_API_KEY`: OpenAI API access
- `ANTHROPIC_API_KEY`: Anthropic Claude access
- `GROK_API_KEY`: xAI Grok access
- `XAI_API_KEY`: Alternative Grok access
- `GEMINI_API_KEY`: Google Gemini access

### Task Types
- `"code_review"`: Code analysis and review
- `"analysis"`: General analysis tasks
- `"creative"`: Creative writing tasks
- `"quick"`: Fast response tasks

## Error Handling

### Exceptions
- `FoundUpsError`: Base exception for gateway errors
  - `message`: Error description
  - `status_code`: HTTP status code (if applicable)

### Error Scenarios
- **No API keys configured**: `FoundUpsError` with "No AI providers configured"
- **All providers failed**: `GatewayResult` with `success=False`
- **Network timeout**: `FoundUpsError` with "Request timeout"
- **Rate limiting**: Automatic retry with different provider

## Dependencies

### Required
- `requests>=2.25.0`: HTTP client for API calls
- `python>=3.8`: Python version requirement

### Optional
- Provider-specific SDKs for enhanced functionality

## Performance Characteristics

### Latency
- **Typical response time**: 1-3 seconds
- **Fallback scenarios**: Additional 1-2 seconds per retry
- **Timeout**: 30 seconds per provider call

### Cost Estimation
- **OpenAI**: ~$0.002 per token
- **Anthropic**: ~$0.015 per token
- **Grok**: ~$0.001 per token
- **Gemini**: ~$0.0005 per token

### Reliability
- **Uptime target**: 99.9% with automatic fallback
- **Provider diversity**: 4+ AI providers for redundancy
- **Automatic failover**: Seamless provider switching

## Integration Examples

### Basic Usage
```python
from modules.ai_intelligence.ai_gateway import AIGateway

gateway = AIGateway()
result = gateway.call_with_fallback("Analyze this Python function", "code_review")

if result.success:
    print(f"Analysis: {result.response}")
    print(f"Provider: {result.provider}, Cost: ${result.cost_estimate:.4f}")
```

### Advanced Configuration
```python
gateway = AIGateway(gateway_key="your-custom-key")

# Custom task routing
result = gateway.call_with_fallback(
    prompt="Write a creative story",
    task_type="creative",
    max_retries=5
)
```

### Usage Monitoring
```python
stats = gateway.get_usage_stats()
print(f"Total calls: {stats['total_calls']}")
print(f"Success rate: {1 - stats['failure_rate']:.1%}")
print(f"Provider usage: {stats['provider_usage']}")
```
