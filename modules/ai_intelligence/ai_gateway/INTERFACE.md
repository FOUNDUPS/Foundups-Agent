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

**Exact OpenRouter Kimi K3 boundary:** `_call_openai(...)` recognizes only the
pair `openrouter` / `moonshotai/kimi-k3`. Its effective completion budget is
`max(resolved_request, 4096)` within the inclusive range `1..131072`; requests
above that endpoint-fixture limit fail before transport. Explicit input takes
precedence over provider environment configuration. The wire request forces
reasoning effort `max` and omits temperature. Non-K3 routes are unchanged.

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

#### Direct provider catalog candidate snapshots

```python
build_discovery_invocation(...) -> DiscoveryInvocation
discover_openrouter_model_catalog(..., transport=...) -> DiscoveryRunResult
rehydrate_candidate_snapshot(candidate, now_ms=...) -> ProviderCatalogCandidateSnapshot
bridge_candidate_to_canonical_catalog(..., prior_admitted_candidate_id=...) -> CatalogBridgeResult
```

Discovery is an explicit manual or pre-authorized scheduled operation. It
persists an attempt receipt separately from the last-known-good candidate under
one validated outside-repository runtime root. Candidate IDs bind only the
schema, provider, model-list source endpoint, and sanitized payload, while
embedded observation receipts and a 24-hour freshness window are revalidated
on admission.

The bridge is idempotent for an unchanged prior candidate ID and invokes the
existing canonical catalog builder with `static_registry=False`. It does not
mutate the registry, select or promote a model, bind runtime roles, or create a
scheduler.

#### Provider model execution-control evidence

```python
build_provider_model_execution_control_evidence(
    candidate=...,
    model_id=...,
    now_ms=...,
) -> ProviderModelExecutionControlEvidence

rehydrate_provider_model_execution_control_evidence(
    payload,
    candidate=...,
    now_ms=...,
) -> ProviderModelExecutionControlEvidence
```

The builder requires an exact model ID and a fresh, canonical candidate
snapshot. It binds candidate/receipt lineage, exact prices, supported
parameters, and strict optional projections of provider `reasoning` and
`top_provider` metadata. The rehydrator recomputes the complete evidence object
and content ID from the supplied candidate.

The trust class is `provider_asserted_model_execution_controls`. These APIs do
not call providers, discover an execution endpoint, select sampling defaults,
admit a canonical route, rank a model, or grant runtime authority.

#### OpenRouter endpoint-route evidence and single-call eligibility

```python
parse_and_sanitize_openrouter_endpoint_payload(
    raw,
    requested_model_id=...,
) -> dict

build_endpoint_observation_receipt(...) -> EndpointObservationReceipt

build_openrouter_endpoint_route_evidence(
    raw=...,
    observation_receipt=...,
    endpoint_tag=...,
    now_ms=...,
) -> OpenRouterEndpointRouteEvidence

build_canonical_single_call_admission(
    raw_endpoint_payload=...,
    endpoint_observation_receipt=...,
    endpoint_route_evidence=...,
    model_candidate=...,
    model_control_evidence=...,
    policy=...,
    intent=...,
    now_ms=...,
) -> CanonicalSingleCallAdmission
```

The endpoint payload is supplied by the caller and bounded before strict JSON
projection; these APIs contain no network or credential boundary. Observation
and route evidence bind exact bytes, request/response digests, model identity,
one unambiguous endpoint tag, caps, prices, parameters, nullable controls, and
freshness. Malformed recognized fields, unsafe secondary price dimensions,
duplicate tags, and base-tag/prefix collisions fail closed.
The pricing object is closed to the current explicit allowlist: unknown keys
fail even when their value is zero. Endpoint status must be omitted or one of
the current official enum values `0, -1, -2, -3, -5, -10`; known negative
values remain route evidence.

The admission builder rehydrates both independent evidence sources and binds
one normalized `CanonicalSingleCallJobPolicy` to one
`CanonicalSingleCallIntent`. Endpoint-specific prices supersede model-summary
prices only after exact reconciliation and policy-cap checks. The receipt is
evaluation-only and `runtime_authority=eligibility_only`; it deliberately does
not invoke `AIGateway`, a configured runner, a provider caller, or any transport.
Availability, job certification, and output-training permission are distinct.
The initial trusted `accepted_endpoint_statuses` policy is exactly `(0,)`.
`endpoint_status_policy_accepted=true` proves policy membership only; it is not
authoritative availability evidence, and live availability remains HALTED.

The trusted policy's `required_parameters` must be exactly
`("max_tokens", "reasoning")`; admission also derives this mandatory set
independently from the emitted `max_tokens` and `reasoning` controls.
Both endpoint and model supported-parameter evidence must contain both names.
An explicit model `reasoning.supports_max_tokens=false` contradicts the emitted
cap and rejects. Omitted/unknown remains non-contradictory only because the two
exact supported-parameter sources independently assert `max_tokens`.
The resulting Chat Completions `request_control` contains exactly
`max_tokens`, `reasoning`, and `provider`. Its `max_tokens` value is copied from
the separately retained internal admission/budget field
`max_completion_tokens`; the internal name is forbidden from the wire-control
mapping. Route, model, intent, and prompt evidence remain in their dedicated
receipt fields/digests.

The receipt preserves `request_price_present`. OpenRouter `PublicPricing`
requires prompt/completion prices and makes request price optional; an absent
request price is interpreted as zero only under the named
`openrouter_public_pricing_request_optional_absence_as_zero.v1` code-owned
schema policy. Its digest and acceptance proof are admission-ID and rehydration
bound. They do not prove provider billing, usage, or availability.

`ProviderCatalogArtifactStore` is the confined persistence boundary used for
both attempt and candidate artifacts. Replacement is same-directory and atomic:
the target is untouched until exact UTF-8 bytes have been flushed and fsynced
to a validated exclusive temporary file. `AtomicArtifactOps` is injectable for
offline failure tests and is a trusted seam. Before replacement, the pathname
must still be a single-link regular file matching the post-write descriptor
device/inode, exact size, and expected SHA-256 content digest; unavailable
identity fails closed. Production retains that descriptor through publication.
On Windows it renames the exact verified object by native handle and verifies
the target before release. Detected publication mismatch restores the prior
bytes/mode or absence, and cleanup does not unlink identity-ambiguous foreign
substitutes. Non-Windows pathname publication requires an operator-controlled,
non-shared runtime directory and makes no claim against an arbitrary
concurrent directory writer. Parent-directory fsync is best-effort.

Redirect history with a non-3xx final response is represented by
`redirect_history_rejected`; raw 3xx responses remain `redirect_rejected`.

#### Scheduled provider discovery replay guard

```python
await discover_scheduled_openrouter_model_catalog(
    invocation,
    repo_root=...,
    runtime_root=...,
    transport=...,
) -> ScheduledDiscoveryResult
```

This API accepts scheduled invocations only. It fixes attempt, candidate,
bounded replay-ledger, and outer operation-lock identities below the validated
outside-repository runtime root. The full synchronous critical section executes
in one worker thread; the asynchronous direct-discovery implementation executes
there with `asyncio.run`, leaving the caller's event loop outside the OS lock.
Nested artifact locks have separate identities.

The ledger is keyed by invocation ID and durably publishes `ARMED` before
transport. Exact completed/failed attempt receipts are terminal. A
`BLOCKED_PRECALL` entry already owned by a valid guard ledger may retry.
`ARMED`, indeterminate, malformed, capacity-exhausted, and
candidate-only states fail closed without transport. `ARMED` recovery requires
the exact same-invocation terminal attempt receipt. Completed replay additionally
requires exact candidate lineage or independently valid fresh candidate evidence
observed strictly later than the cached completion.

An exact pre-ledger blocked receipt is ambiguous and fails closed. With no
guard ledger, older fixed evidence permits a new invocation only when that
evidence is internally valid and every relevant completion/observation time is
strictly before the new scheduled window. Ledger entries are authoritative only
for their exact invocation IDs; missing IDs still pass the chronology proof.
Ledger `updated_at_ms` is a wall-clock high-water mark, so rollback below it
fails closed. The fixed guarded identities are exclusive to this API;
manual/direct callers must use other attempt and candidate paths.

This boundary provides scheduled replay control only. It installs no scheduler,
does not run at startup, does not change manual discovery, and grants no
selection, promotion, runtime-binding, or registry authority. Runtime artifacts
must remain under a trusted-principal-controlled root; the cooperative lock
does not defend against an arbitrary writer with directory access. Ledger state
contains no response body, credential, or authorization data.

#### Idle schedule adapter

```python
await run_openrouter_catalog_schedule_claim(
    claim,
    repo_root=...,
    runtime_root=...,
    transport=...,
) -> dict[str, object]
```

The claim must be the exact durable `ScheduleClaim` type for canonical schedule
ID `e324884d66c4`, routine `openrouter_catalog_refresh`, cadence `daily`, and a
canonical midnight-to-midnight UTC window. The adapter derives the guarded
invocation; callers cannot supply invocation or artifact identities.

The result has exactly six keys: `success`, `status`, `reason`, `replayed`,
`receipt_id`, and `candidate_snapshot_id`. Only canonically rehydrated
`DiscoveryReceipt` and `ProviderCatalogCandidateSnapshot` evidence with exact
invocation and observation lineage can yield `COMPLETED/completed`. Other
results use fixed local codes and do not expose guard text. The API gathers
candidate evidence only and has no bridge, selection, promotion, registry, or
runtime-binding authority.

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

#### Model AutoResearch Cycle Feedback Ledger Admission

```python
rehydrate_model_autoresearch_cycle_receipt(...) -> ModelAutoResearchCycleReceipt
admit_model_autoresearch_cycle_feedback(...) -> ModelAutoResearchCycleFeedbackLedgerAdmissionResult
```

The admission layer accepts a serialized or typed
`ModelAutoResearchCycleReceipt`, recomputes its deterministic receipt ID,
requires executed candidate and promotion-gate evidence, and writes a minimal
cycle feedback record through an injected
`ModelAutoResearchCycleFeedbackLedgerStore`.

The default in-memory and JSONL stores are append-only adapters. The API is
explicit-invoke only and does not call providers, run benchmarks, promote
models, write PatternMemory, mutate HoloIndex, or bind RedDog runtime defaults.

#### Model AutoResearch Configured Gateway Runner

```python
build_configured_gateway_benchmark_runner(...) -> BenchmarkRunner
AIGatewayConfiguredModelCaller(gateway).call_model(...)
JsonlModelAutoResearchOutputEvidenceStore(path, repo_root=...)
JsonlConfiguredGatewayReceiptStore(path)
rehydrate_model_budget_evidence_bundle(payload)
read_call_attempt_receipts_jsonl(path)
read_runner_receipts_jsonl(path)
build_model_autoresearch_output_evidence_semantic_verifier(
    evidence_records=..., runner_receipts=...
) -> BenchmarkVerifier
```

The configured runner consumes a digest-bound prompt source and an explicit
provider/model gateway caller, then produces `ModelBenchmarkTaskOutput` records
for the benchmark harness. It verifies `ModelBenchmarkTask.prompt_digest`
against the supplied prompt before any call and emits only content digests,
runner receipt IDs, and bounded metrics.

`ConfiguredGatewayRunnerPolicy.model_budgets` is mandatory. Each assignment is
bound to its exact provider/API model, canonical decimal rates, prompt overhead,
completion-token cap, and operator catalog-claim-bound reasoning effort. This
claim is non-authoritative until canonical catalog admission. The caller
receives `max_completion_tokens` and `reasoning_effort` as exact keyword-only
controls. The canonical prompt guard evaluates the fully wrapped prompt in
audit mode and permits only a byte-identical approved prompt.

The reasoning catalog digest is currently an operator-supplied catalog claim,
not proof of canonical catalog admission. Exact assignment/API-model equality
is therefore mandatory; aliases are rejected.

Panel calls are reserved atomically against `max_total_calls`. A durable
`ATTEMPTED` receipt is written before caller entry and consumes that slot.
Failure releases only roles whose attempts were never persisted. Attempt and
success JSONL readers canonically rehydrate records, recompute their IDs and
cost totals, and reject tampering.

Configured bootstrap callers must also provide `runner_max_total_calls` and a
canonical positive Decimal string for per-sample cost. Before runner
construction it checks the complete selected-role x normalized-task call count,
all selected assignment budgets, canonical path non-aliasing, and absent/empty
write targets. The runner checks each final wrapped prompt size before prompt
guard evaluation or caller entry.

This phase-1 configured bootstrap admits exactly one executable planned call.
Multi-call task sets and panel combinations remain NO-GO until a later phase
can atomically prepare the complete task-by-role campaign before caller entry.

When supplied with a `ModelAutoResearchOutputEvidenceStore`, the runner writes
each raw role response as a digest-bound
`ModelAutoResearchOutputEvidenceRecord` and binds the evidence record ID into
the runner receipt. JSONL evidence stores must resolve outside the repository
because they contain raw model output. Records rehydrate by recomputing response
digests and record IDs, and secret-bearing output is rejected before append.

The `AIGatewayConfiguredModelCaller` adapter reuses the existing `AIGateway`
provider registry to target the candidate's exact role assignment. It is not
enabled automatically by `main.py` and does not perform verification, promotion,
PatternMemory writes, HoloIndex mutation, runtime binding, command execution, or
repository mutation.

OpenRouter candidates use provider `openrouter` and an exact model ID such as
`moonshotai/kimi-k3`. The provider is available only through explicit configured
gateway assignments and allowlisting; it is not inserted into normal fallback
routing. Kimi K3 remains an AutoResearch candidate until signed benchmark and
promotion evidence authorizes a production binding. Its configured provider
records separate input/output token prices for bounded cost-gate estimates.

The campaign execution bootstrap accepts this runner only through the explicit
`configured_gateway` mode, an outside-repo prompt-record file, an explicit
provider allowlist, an outside-repo output-evidence JSONL path, and the
outside-repo model-budget evidence, call-attempt JSONL, runner-success JSONL,
`exact_output_digest` or `output_evidence_semantic` verifier mode. The semantic
mode is deterministic: it rehydrates output-evidence and runner-success
records, verifies exact lineage/call/metric bindings, recomputes the output
digest, and checks explicit task metadata keys
`expected_answer_contains` and `expected_answer_excludes`. It fails closed when
required terms are absent or no semantic requirements are supplied. Default
startup behavior remains `deterministic_fixture`.

Live configured-provider execution is a phase-B NO-GO until canonical catalog
admission, authoritative provider usage receipts, and a model-budget-specific
pre-buffer response-byte transport contract are present, and every
input/receipt read and preflight path identity is protected by bounded
streaming and an exclusive runtime-directory claim or equivalent
identity-preserving boundary.

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
may consume verified selection-outcome feedback records and context-bound
AutoResearch cycle feedback records as bounded priority signals. Cycle feedback
is accepted only when its source plan context is bound, task family and catalog
snapshot match the policy, source-plan digest is present, and executed
candidates plus promotion-gate receipt IDs are nonempty. The planner
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
below-threshold evidence fail closed. Panel runtime binding accepts only a
`VerifiedModelPanelEvidence` aggregate; independently valid member proofs alone
remain insufficient. This API does not
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

#### Signed Aggregate PANEL Evidence

```python
build_panel_member_evidence_binding(...) -> PanelMemberEvidenceBinding
build_model_panel_signed_evidence_receipt(...) -> ModelPanelSignedEvidenceReceipt
rehydrate_model_panel_signed_evidence_receipt(...)
build_verified_model_panel_evidence(...) -> VerifiedModelPanelEvidence
```

The PANEL verifier first invokes the existing signed single-model admission
chain for every ordered role/model/provider member. It then checks member and
required-role uniqueness, exact selection order, per-member evidence IDs and
digests, explicit synthesizer, and exact catalog/selection/task/topology/policy/
surface ID-and-digest bindings. Only then does it verify the aggregate signer,
trusted key, key epoch, validity window and signature; optional aggregate nonce
consumption is last. Runtime binding rejects PANEL selections unless supplied
this exact process-local factory-issued aggregate proof. The proof cannot be
directly constructed, copied, replaced or serialized; runtime rechecks its
closure-held identity seal and exact aggregate/member/context/synthesizer
projections. The API does not sign, choose models, call providers,
wire Fusion consumers, mutate runtime defaults or perform network/file writes.

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
