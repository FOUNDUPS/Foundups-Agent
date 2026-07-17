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

Production model selection must pass `production_evidence` containing
typed, rehydrated and signature-verified benchmark/promotion proof. Catalog
fields and raw evidence mappings do not satisfy production authority, even when
`promotion_state == CHAMPION`.

Panel mode emits role assignments and a topology digest. The candidate panel may
include roles such as principal, researcher, critic and implementer; the verifier
role is reserved for an independent verifier outside the candidate panel.

#### Benchmark Evidence and Outcome Receipts

```python
build_model_benchmark_evidence_receipt(...) -> ModelBenchmarkEvidenceReceipt
build_model_promotion_evidence_receipt(...) -> ModelPromotionEvidenceReceipt
production_evidence_for_selection(...) -> dict[str, dict[str, Any]]
build_model_selection_outcome_receipt(...) -> ModelSelectionOutcomeReceipt
outcome_feedback_record(receipt) -> dict[str, Any]
```

Benchmark evidence binds the model, task family, task-set digest, held-out split
digest, prompt/topology digest, verifier digest, verifier receipt, sample count,
accepted count, cost and latency. Promotion evidence binds a signed authority
receipt to that benchmark evidence. Outcome receipts are feedback-eligible only
when the independent verifier accepts, task completion is true, evidence is
verified, and no regression or unauthorized change is detected.

#### Model Feedback Ledger Admission

```python
rehydrate_model_selection_outcome_receipt(...) -> ModelSelectionOutcomeReceipt
admit_model_selection_outcome_feedback(...) -> ModelFeedbackLedgerAdmissionResult
```

The admission layer accepts a serialized or typed
`ModelSelectionOutcomeReceipt`, recomputes its deterministic receipt ID, requires
`feedback_eligible == True`, optionally checks the source ratchet verifier and
runtime-binding fields, and writes a minimal feedback record through an injected
`ModelFeedbackLedgerStore`.

The default in-memory and JSONL stores are append-only adapters. The API is
explicit-invoke only and does not call providers, run benchmarks, promote
models, write PatternMemory, mutate HoloIndex, or bind RedDog runtime defaults.

#### Model Combination Benchmark Harness

```python
build_model_benchmark_candidate(role_assignments) -> ModelBenchmarkCandidate
run_model_combination_benchmark(...) -> ModelCombinationBenchmarkRunReceipt
```

The harness evaluates single-model or panel candidates against a held-out
`ModelBenchmarkTask` set using injected runner and verifier callables. It
produces per-candidate `ModelBenchmarkEvidenceReceipt` records and a digest-bound
run receipt over task-set digest, held-out split digest, verifier digest,
role/topology assignments, sample receipts, and benchmark evidence receipt IDs.

The verifier role is reserved for an independent verifier and cannot be part of
the candidate panel. The harness does not call model providers, execute commands,
promote champions, persist PatternMemory, mutate HoloIndex, or bind RedDog
runtime defaults.

#### Champion/Challenger Promotion Gate

```python
evaluate_model_promotion_gate(...) -> ModelPromotionGateReceipt
```

`ModelPromotionPolicy` binds task family, candidate ID, minimum verifier pass
rate, minimum sample count, required task-set digest, required held-out split
digest, required verifier digest, and optional latency/cost ceilings.

The gate validates a `ModelCombinationBenchmarkRunReceipt` and emits
`PROMOTE_CHAMPION` only when benchmark evidence matches the policy and signed
promotion authority is supplied. `KEEP_CHALLENGER` records below-threshold
benchmark evidence without creating champion authority. Mismatched or tampered
benchmark projections return `REJECT`.

This API does not mutate model catalogs, write champion ledgers, call providers,
or bind runtime RedDog model defaults.

#### Champion/Challenger AutoResearch Planner

```python
plan_model_champion_challenger_autoresearch(...) -> ModelAutoResearchPlanReceipt
```

The planner consumes promotion-gate receipts, a candidate pool, and
`ModelAutoResearchPolicy`. It emits a digest-bound plan containing
`BENCHMARK_NEW_CANDIDATE`, `REBENCHMARK_CHALLENGER`, or `STOP` items.

The policy binds task family, catalog snapshot ID, maximum campaign items,
optional verifier digest, and a required cost-budget receipt. Missing source gate
receipts, verifier mismatch, or missing budget evidence fails closed. The planner
does not execute benchmarks, call providers, write PatternMemory, mutate
catalogs, or bind runtime defaults.

#### RedDog Runtime Model Binding

```python
bind_reddog_runtime_models(...) -> RedDogModelRuntimeBindingReceipt
```

`ModelRuntimeBindingPolicy` binds the task family, runtime surface, minimum
verifier pass rate, required task-set digest, held-out split digest, verifier
digest, optional panel topology digest, and optional authority receipt ID.

The binding function consumes:

- the `ModelCatalogSnapshot` used for selection
- a production `ModelSelectionReceipt`
- per-selected-model `ModelBenchmarkEvidenceReceipt` records
- per-selected-model `ModelPromotionEvidenceReceipt` records

It returns `BOUND` only when every selected model is present in the catalog,
selection is production-scoped, benchmark and signed-promotion evidence match the
runtime policy, and panel role/topology bindings are valid. A bound receipt can
produce a minimal RedDog bridge payload via `to_reddog_bridge_payload()`.

The verifier role remains outside candidate panels. Catalog-only champions,
evaluation selections, stale topology, mismatched benchmark evidence, missing
verified production evidence, missing signed promotion receipts, and
below-threshold evidence fail closed. Panel runtime binding is intentionally
deferred until panel topology evidence is signed and verified. This API does not
call model providers, run benchmarks, mutate the extension, persist runtime
defaults, or write PatternMemory.

#### Signed Production Evidence

```python
rehydrate_model_benchmark_evidence_receipt(...)
rehydrate_model_promotion_evidence_receipt(...)
rehydrate_model_selection_receipt(...)
rehydrate_model_runtime_binding_receipt(...)
rehydrate_model_signed_evidence_receipt(...)
build_verified_model_production_evidence(...) -> VerifiedModelProductionEvidence
verify_model_signed_evidence_receipt(...) -> SignedEvidenceVerificationResult
```

Signed evidence binds signer role, public key fingerprint, key epoch, model
subject, catalog snapshot, selection receipt, benchmark run, benchmark evidence,
task set, held-out split, verifier digest, prompt/topology digest, promotion
evidence, promotion policy, issued/expiry time and nonce.

Accepted signer roles are `benchmark_verifier` and `promotion_authority`.
Signatures are verified through the existing RedDog `SignatureVerifier`
interface; this module never signs, never holds private keys and never imports a
crypto signing library. Nonces are consumed only when admission explicitly
requests it. Downstream selection and runtime checks validate immutable verified
evidence and do not consume single-use nonces again.

#### RedDog Model Selection Artifact Supply

```python
run_reddog_model_selection_artifact_supply(...) -> ModelSelectionArtifactSupplyResult
```

The supplier rehydrates a catalog snapshot, verifies serialized signed
benchmark/promotion evidence into `VerifiedModelProductionEvidence`, runs
production model selection, and atomically writes one `ModelSelectionReceipt`
JSON artifact outside the repository. It is intended for the resident RedDog
architect FIX promotion bridge, where the promotion layer expects a file path
rather than an in-memory object.

Evaluation requirements, raw serialized evidence without a key resolver and
signature verifier, rejected model selections, missing output paths, and
repository-internal output paths fail closed. The API does not call providers,
run benchmarks, execute commands, persist telemetry, re-index HoloIndex, bind
runtime defaults, mutate the extension, dispatch workers, or write PatternMemory.

```python
run_reddog_model_selection_artifact_supply_bootstrap(...) -> ModelSelectionArtifactBootstrapResult
```

The bootstrap adapter is the explicit `main.py` preflight surface. It reads
outside-repo catalog/evidence/requirements/key JSON inputs, constructs a trusted
public-key resolver, uses the configured public signature verifier, and delegates
receipt creation to `run_reddog_model_selection_artifact_supply`. It is disabled
unless `REDDOG_MODEL_SELECTION_ARTIFACT_SUPPLY=1`.

#### RedDog Runtime Binding Artifact Supply

```python
run_reddog_model_runtime_binding_artifact_supply(...) -> ModelRuntimeBindingArtifactSupplyResult
```

The supplier rehydrates a catalog snapshot, a production model-selection
receipt, benchmark evidence receipts, promotion evidence receipts, signed
production-evidence proof, and a runtime binding policy. It then calls
`bind_reddog_runtime_models` and atomically writes one
`RedDogModelRuntimeBindingReceipt` JSON artifact outside the repository.

Serialized signed evidence requires a trusted public-key resolver and signature
verifier before runtime binding. A binding is emitted only when the production
selection, benchmark evidence, promotion evidence, verified signed evidence and
runtime policy agree. Policy mismatches, missing signature verification,
rejected runtime binding, missing output paths and repository-internal output
paths fail closed.

```python
run_reddog_model_runtime_binding_artifact_supply_bootstrap(...) -> ModelRuntimeBindingArtifactBootstrapResult
```

The bootstrap adapter is the explicit `main.py` preflight surface for runtime
binding artifacts. It reads outside-repo catalog, selection, benchmark,
promotion, evidence-bundle, policy and trusted-key JSON inputs, constructs a
trusted public-key resolver, uses the configured public signature verifier, and
delegates receipt creation to
`run_reddog_model_runtime_binding_artifact_supply`.

This API does not call providers, run benchmarks, execute shell commands,
persist telemetry, mutate extension runtime defaults, dispatch workers, write
PatternMemory, or re-index HoloIndex. It supplies a receipt artifact only; later
resident runtime code must explicitly consume that receipt.

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
