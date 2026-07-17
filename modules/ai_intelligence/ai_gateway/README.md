# AI Gateway Module

**Module Purpose**: Unified AI service access with intelligent routing, fallback, and load balancing across multiple AI providers.

**WSP Compliance Status**: [OK] WSP 49 (Module Structure), WSP 3 (Enterprise Domain), WSP 27 (DAE Architecture)

**Dependencies**: requests>=2.25.0

## Model Intelligence Catalog

`src/model_intelligence_catalog.py` provides the runtime evidence layer for
RedDog model intelligence. It normalizes static registry entries, provider
catalog payloads, and local role-resolution results into immutable
`ModelCatalogSnapshot` receipts.

This layer does not choose a model, call a provider, run benchmarks, or promote
any model to production. Provider catalog entries and `latest`-style aliases are
eligible candidates only; later benchmark and verifier receipts must promote
champion/challenger status.

## Model Selection Receipts

`src/model_intelligence_selection.py` consumes a `ModelCatalogSnapshot` and
`ModelTaskRequirements` to produce a deterministic `ModelSelectionReceipt`.

Two purposes are supported:

- `evaluation`: may select candidate models for benchmark or shadow testing.
- `production`: requires champion promotion, task benchmark evidence, and verifier
  pass-rate evidence.

This keeps RedDog flexible without allowing a newly discovered model alias to
become production authority before measured FoundUps performance exists.

## Benchmark Evidence and Outcome Receipts

`src/model_intelligence_outcomes.py` defines the receipt-bound evidence required
before production model selection can trust a champion:

- held-out benchmark evidence bound to model ID, task family, task-set digest,
  held-out split digest, prompt/topology digest, verifier digest, sample count,
  cost and latency
- signed promotion evidence over the benchmark receipt
- selection outcome receipts that become feedback-eligible only after independent
  verifier acceptance and regression/unauthorized-change checks

Catalog scalar fields remain useful for evaluation and ranking, but production
selection rejects `CHAMPION` unless these evidence receipts are supplied.

## Model Feedback Ledger Admission

`src/model_feedback_ledger.py` admits feedback-eligible
`ModelSelectionOutcomeReceipt` records into an injected model-feedback ledger.
It rehydrates serialized outcome receipts, recomputes their deterministic IDs,
checks optional source-ratchet verifier/runtime-binding consistency, scans the
feedback record for secret markers, and emits a digest-bound admission receipt.

This layer is the bridge from verified RedDog outcomes back into model
intelligence feedback. It does not call providers, run benchmarks, promote
models, write PatternMemory, mutate HoloIndex, or change RedDog runtime model
defaults.

## Model AutoResearch Cycle Feedback Ledger Admission

`src/model_autoresearch_cycle_feedback_ledger.py` admits verified
`ModelAutoResearchCycleReceipt` records into an injected AutoResearch cycle
feedback ledger. It rehydrates serialized cycle receipts, recomputes their
deterministic IDs, verifies that the cycle contains executed candidates and
promotion-gate receipts, scans the feedback record for secret markers, and emits
a digest-bound admission receipt.

This layer lets the recursive model-improvement loop retain which campaign was
run and which promotion-gate receipts resulted. It does not call providers, run
benchmarks, promote models, write PatternMemory, mutate HoloIndex, or change
RedDog runtime model defaults.

## Model AutoResearch Configured Gateway Runner

`src/model_autoresearch_configured_gateway_runner.py` adapts a configured model
gateway and digest-bound prompt source into the existing benchmark runner
contract. It verifies the held-out prompt digest before any model call, targets
the exact provider/model role assignment in the candidate, supports panel role
calls, and returns only digest-bound output and runner receipts to the benchmark
harness.

`src/model_autoresearch_output_evidence_bundle.py` provides the content-bearing
evidence layer for those configured runs. When an output evidence store is
injected, each raw model response is written to an outside-repo JSONL record
whose response digest and record ID can be rehydrated later by an independent
verifier. Secret-bearing output is rejected before persistence.

`src/model_autoresearch_semantic_verifier.py` is the first deterministic
content verifier over those evidence records. It does not call a model; it
rehydrates the output evidence, recomputes the configured-runner output and
receipt digests, then checks explicit task metadata requirements:
`expected_answer_contains` and `expected_answer_excludes`. Missing requirements
fail closed.

This creates a real provider-call seam for AutoResearch benchmarks without
turning it on at resident startup. It does not choose candidates, verify model
answers, promote models, mutate catalogs, write PatternMemory, re-index
HoloIndex, execute commands, mutate the repository, or bind RedDog runtime
defaults.

`src/model_autoresearch_campaign_execution_artifact_supply_bootstrap.py` can
use this runner only when `REDDOG_MODEL_AUTORESEARCH_CAMPAIGN_RUNNER_MODE` is
set to `configured_gateway`, prompt records are supplied from outside the repo,
providers are explicitly allowlisted, an outside-repo output evidence path is
supplied, and verifier mode is `exact_output_digest` or
`output_evidence_semantic`. The default remains deterministic fixture execution.

## Model Combination Benchmark Harness

`src/model_combination_benchmark_harness.py` runs deterministic held-out
benchmarks for single-model and panel candidates through injected runner and
verifier callables. It binds task-set, held-out split, verifier, role/topology
and sample results into benchmark evidence receipts.

This layer is still pre-production. It does not call providers, execute shell
commands, promote champions, write PatternMemory, or bind RedDog runtime model
defaults. Panel benchmark evidence remains panel evidence; a later promotion
gate must decide how, or whether, panel combinations become production choices.

## Champion/Challenger Promotion Gate

`src/model_promotion_gate.py` validates benchmark-run evidence against an
explicit promotion policy. It can emit a `ModelPromotionEvidenceReceipt` only
when the benchmark evidence matches the policy and a signed promotion authority
receipt is supplied.

The gate does not mutate the catalog, write a champion ledger, call providers,
or bind RedDog runtime defaults. Below-threshold candidates remain challengers;
tampered or mismatched evidence fails closed.

## Champion/Challenger AutoResearch Planner

`src/model_champion_challenger_autoresearch.py` converts promotion-gate receipts
and candidate pools into a digest-bound benchmark campaign plan. It can propose
benchmarking untested candidates or rebenchmarking challengers, but it does not
execute those campaigns.

The planner requires source promotion-gate receipts and a cost-budget receipt.
It can use verified selection-outcome feedback and context-bound AutoResearch
cycle feedback as bounded priority signals for existing candidates. Cycle
feedback must be source-plan-bound and policy-matched before it can influence
the next campaign. It does not call providers, run benchmarks, mutate catalogs,
write PatternMemory, or bind RedDog runtime defaults.

## RedDog Runtime Model Binding

`src/model_runtime_binding.py` is the first production-facing binding layer for
dynamic RedDog model selection. It consumes a production `ModelSelectionReceipt`,
the matching catalog snapshot, benchmark evidence receipts, promotion evidence
receipts, and an explicit runtime policy. Only after those receipts agree does it
emit a digest-bound `RedDogModelRuntimeBindingReceipt` plus a minimal
RedDog/Fusion bridge payload (`lead_model`, `panel_models`, role bindings, and
binding receipt IDs).

Catalog-only `CHAMPION` fields do not bind runtime authority. Evaluation
selections remain valid for benchmarking, but cannot become RedDog runtime
defaults. This layer still does not call providers, run benchmarks, mutate the
extension, persist champion ledgers, write PatternMemory, or change
`extension.js`.

## Signed Production Evidence

`src/model_signed_evidence.py` is the production evidence admission gate between
benchmark/promotion receipts and model selection/runtime binding. It rehydrates
serialized catalog, selection, benchmark, promotion and runtime binding receipts,
recomputes deterministic IDs, and verifies role-specific signed evidence through
the existing RedDog signature verifier interface.

Production selection no longer accepts raw `production_evidence` mappings as
authority. Those mappings remain useful as legacy scalar projections, but
`selection.purpose == production` requires a typed
`VerifiedModelProductionEvidence` object that passed signed-evidence
verification. Runtime binding also requires that verified object before a bridge
payload can be emitted. Single-model chains can pass; panel runtime binding is
still deferred until topology-bound panel evidence is signed and verified.

## RedDog Model Selection Artifact Supply

`src/model_selection_artifact_supply.py` materializes a production
`ModelSelectionReceipt` JSON artifact from a model catalog snapshot and signed
benchmark/promotion evidence. It is a bounded bridge for RedDog architect FIX
promotion: the resident cycle can write the receipt path expected by the
promotion bridge without calling models or trusting raw production-evidence
mappings.

The supplier verifies serialized evidence through the signed-evidence gate
before production selection, rejects non-production requirements, and refuses to
write artifacts inside the repository. It does not call providers, run
benchmarks, execute commands, persist telemetry, re-index HoloIndex, bind
runtime model defaults, mutate `extension.js`, or dispatch workers.

`src/model_selection_artifact_supply_bootstrap.py` is the optional `main.py`
startup adapter for that supplier. When explicitly enabled, it reads the model
catalog snapshot, signed production-evidence bundle, selection requirements and
trusted public-key records from outside-repo runtime files, then writes the
selection receipt path consumed by RedDog FIX promotion. The adapter defaults to
the existing Ed25519 public verifier and fails closed when trusted keys or
signed evidence are absent.

## RedDog Runtime Binding Artifact Supply

`src/model_runtime_binding_artifact_supply.py` materializes a
`RedDogModelRuntimeBindingReceipt` JSON artifact from the production
`ModelSelectionReceipt`, matching benchmark evidence, matching promotion
evidence, signed verified production evidence, and an explicit runtime binding
policy.

This closes the handoff after model selection: resident RedDog can now consume a
receipt-bound runtime model topology instead of hard-coded GLM/DeepSeek/Kimi
defaults. The supplier rehydrates and digest-checks every source receipt before
binding, rejects mismatched policy evidence, and refuses to write artifacts
inside the repository. It does not call providers, run benchmarks, execute
commands, mutate catalogs, persist telemetry, re-index HoloIndex, mutate
`extension.js`, dispatch workers, or write PatternMemory.

`src/model_runtime_binding_artifact_supply_bootstrap.py` is the optional
`main.py` startup adapter for that supplier. It reads outside-repo catalog,
selection, benchmark, promotion, signed-evidence, policy and trusted-key JSON
inputs, then writes the runtime-binding receipt path for later resident runtime
consumption. It remains disabled unless explicitly configured.

**Usage Examples**:
```python
from modules.ai_intelligence.ai_gateway import AIGateway

gateway = AIGateway()
result = gateway.call_with_fallback("Analyze this code", task_type="code_review")
```

**Integration Points**:
- Qwen Orchestrator (enhanced analysis capabilities)
- LLM Response Optimizer (fallback intelligence)
- Agentic Output Throttler (routing decisions)

**WSP Recursive Instructions**:
[U+1F300] Windsurf Protocol (WSP) Recursive Prompt
**0102 Directive**: This module operates within the WSP framework...
- UN (Understanding): Anchor signal and retrieve protocol state
- DAO (Execution): Execute modular logic
- DU (Emergence): Collapse into 0102 resonance and emit next prompt

wsp_cycle(input="012", log=True)
