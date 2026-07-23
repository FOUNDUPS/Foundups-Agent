# AI Gateway Module

**Module Purpose**: Unified AI service access with intelligent routing, fallback, and load balancing across multiple AI providers.

**WSP Compliance Status**: [OK] WSP 49 (Module Structure), WSP 3 (Enterprise Domain), WSP 27 (DAE Architecture)

**Dependencies**: requests>=2.25.0; aiohttp>=3.9,<4

## Model Intelligence Catalog

`src/model_intelligence_catalog.py` provides the runtime evidence layer for
RedDog model intelligence. It normalizes static registry entries, provider
catalog payloads, and local role-resolution results into immutable
`ModelCatalogSnapshot` receipts.

This layer does not choose a model, call a provider, run benchmarks, or promote
any model to production. Provider catalog entries and `latest`-style aliases are
eligible candidates only; later benchmark and verifier receipts must promote
champion/challenger status.

### Explicit OpenRouter catalog discovery

`src/model_openrouter_direct_discovery.py` can refresh the public OpenRouter
model listing only through the explicit one-shot script
`scripts/openrouter_model_catalog_snapshot_once.py`. The request is a fixed,
unauthenticated `GET`, with redirects disabled, a 15-second total deadline, an
8 MiB streaming limit, and a 2,048-record limit.

The operator supplies one outside-repository runtime root and two distinct
paths beneath it: an attempt receipt and a last-known-good candidate snapshot.
Every admitted call writes pre-call and indeterminate state before transport.
Only a successfully parsed and normalized response replaces the candidate;
failed refreshes leave the last-known-good candidate untouched. Provider
listing metadata remains candidate evidence with unknown availability and
provider-policy privacy, not selection, promotion, or runtime-binding authority.

Both runtime artifacts use a module-local atomic store. It writes exact UTF-8
to an exclusive same-directory temporary file, flushes and fsyncs it, then
replaces the validated target while holding the existing runtime lock. A failed
temporary write, fsync, or replacement removes the temporary file and leaves
the previous target byte-identical. A detected post-publication mismatch is
rolled back to the prior bytes and mode, or to absence. Low-level write,
precommit, and replace seams are trusted and exist only for deterministic
offline durability tests.

The store binds each commit to post-write descriptor evidence: device/inode
identity when the host exposes it, exact size, SHA-256 digest, regular-file
type, and a single-link pathname. It retains that descriptor through
publication and verifies the published target before releasing it. Windows
production publication renames the verified object by native handle, so a
pathname substitution cannot select different bytes. Cleanup never unlinks a
foreign or identity-ambiguous substitute. Other hosts require an
operator-controlled, non-shared runtime directory because their standard
pathname replace cannot exclude an arbitrary writer after the final check.
Unavailable file identity fails closed.
Parent-directory fsync remains best-effort, including on Windows.

Transport responses that report redirect history with a non-3xx final status
produce the content-free `redirect_history_rejected` terminal reason. Raw 3xx
responses continue to use `redirect_rejected`.

Example manual invocation:

```text
python scripts/openrouter_model_catalog_snapshot_once.py --mode manual \
  --runtime-root D:/runtime/model-catalog \
  --attempt-path openrouter-attempt.json \
  --candidate-path openrouter-candidate.json
```

Scheduled mode is admission metadata, not an installed scheduler. It additionally
requires `--schedule-id`, `--scheduled-for-ms`, and `--expires-at-ms`; callers
must invoke the script explicitly within that inclusive time window.

### Scheduled discovery replay guard

`discover_scheduled_openrouter_model_catalog(...)` is the scheduled-only
execution boundary. It does not install a scheduler, alter startup behavior, or
change the manual one-shot discovery path. The caller supplies a canonical
scheduled `DiscoveryInvocation`, trusted repository/runtime roots, and a
transport seam. Attempt, candidate, replay-ledger, and operation-lock identities
are fixed beneath the validated outside-repository runtime root.

The complete synchronous admission, replay decision, transport, and publication
sequence runs in one worker thread under one outer cross-process operation lock.
The existing asynchronous discovery call runs in that same worker by
`asyncio.run`, so the outer lock never blocks the caller's event loop. Inner
artifact locks use distinct identities.

Before transport, a strict bounded durable ledger publishes `ARMED` for the
invocation ID. Completed and failed attempts are terminal. A completed replay
requires its exact valid receipt plus either the exact current candidate
lineage or a separately valid, fresh candidate observed strictly after that
completion. `ARMED`, indeterminate, malformed, capacity-exhausted, and
candidate-without-terminal states fail closed. Only an exact terminal attempt
can recover an `ARMED` entry; candidate evidence alone cannot. Only a
`BLOCKED_PRECALL` entry already owned by a valid guard ledger remains retryable.
An exact pre-ledger blocked receipt is ambiguous and fails closed.

When no guard ledger exists, older fixed direct-discovery evidence permits a
new invocation only when its attempt/candidate evidence is internally valid and
all relevant completion/observation times are strictly before the new scheduled
window. Valid ledger entries are authoritative only for their exact invocation
IDs; a missing ID still passes the same fixed-evidence chronology proof. A
different, strictly later valid scheduled window may then make one new call.

The ledger contains strict structured invocation/receipt evidence only; it does
not persist response bodies, authorization values, or secrets. Expired windows
alone are pruned and cannot pass current admission. Its `updated_at_ms` is a
wall-clock high-water mark; rollback below it fails closed. The runtime root
must be controlled by the same trusted principal as the process. The
cooperative operation lock is a replay/concurrency boundary, not a security
boundary against an arbitrary writer with access to that directory.
The fixed guarded artifact identities are exclusive to this API; manual/direct
callers must use different attempt and candidate paths.

### Idle daily catalog schedule adapter

`run_openrouter_catalog_schedule_claim(...)` is the narrow bridge from one
exact idle `ScheduleClaim` to the guarded discovery API. It accepts only the
canonical `openrouter_catalog_refresh:daily` schedule, a canonical midnight
UTC 24-hour window, and the exact execution digest. The claim maps to
`schedule_id="idle:<execution_id>"`, the window start in milliseconds, and an
inclusive expiry one millisecond before window end.

The adapter returns exactly six bounded fields: `success`, `status`, `reason`,
`replayed`, `receipt_id`, and `candidate_snapshot_id`. Guard status/reason text
is never forwarded. Completion succeeds only after exact typed receipt and
candidate evidence is serialized, canonically rehydrated, and proven to match
the derived invocation and each other. All malformed, forged, nonterminal, or
exceptional results become fixed content-free failures; cancellation still
propagates.

This is candidate-evidence collection only. It performs no catalog bridge,
model selection, promotion, registry mutation, or runtime binding. Production
enablement is owned by idle automation and remains default-off. Tests inject
transport and remain offline.

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

Every route requires immutable model-budget evidence: exact provider/API model,
canonical decimal input/output rates, prompt overhead, completion-token cap,
and an operator-supplied catalog-claim digest for reasoning effort. The fully role-wrapped prompt passes the
canonical local audit-only redaction guard byte-identically before a call.
Panel admission reserves atomically; persisted `ATTEMPTED` calls consume their
slots, while a failed run releases only its definitely unstarted suffix.
Bootstrap admission also proves the complete selected-role x normalized-task
call count against an explicit campaign-wide cap before constructing the
runner. All write artifacts must be absent or empty and canonically distinct
from every read input and other write target.
This phase-1 configured bootstrap admits exactly one executable planned call;
multi-call task sets and panel combinations remain NO-GO until the complete
task-by-role campaign can be prepared atomically before caller entry.

Call-attempt and successful-run receipts are append-only outside-repository
JSONL artifacts. Public readers rehydrate each record, recompute group/receipt
IDs and total reserved cost, and reject changed status, route, digest, cost, or
call data. A terminal persistence failure after caller entry is indeterminate
and never rolls back the consumed call. Cancellation and other `BaseException`
signals remain the caller's original signals.

`src/model_autoresearch_output_evidence_bundle.py` provides the content-bearing
evidence layer for those configured runs. When an output evidence store is
injected, each raw model response is written to an outside-repo JSONL record
whose response digest and record ID can be rehydrated later by an independent
verifier. Secret-bearing output is rejected before persistence.

`src/model_autoresearch_semantic_verifier.py` is the first deterministic
content verifier over those evidence records. It does not call a model; it
rehydrates the output evidence and durable v2 runner receipt, verifies their
task/candidate/prompt/policy/call/evidence/metrics bindings, recomputes the
configured-runner output digest, then checks explicit task metadata requirements:
`expected_answer_contains` and `expected_answer_excludes`. Missing requirements
fail closed.

This creates a real provider-call seam for AutoResearch benchmarks without
turning it on at resident startup. It does not choose candidates, verify model
answers, promote models, mutate catalogs, write PatternMemory, re-index
HoloIndex, execute commands, mutate the repository, or bind RedDog runtime
defaults.

The configured gateway includes an explicit `openrouter` provider for governed
candidate assignments such as `moonshotai/kimi-k3`. OpenRouter remains absent
from ordinary AI Gateway fallback routing; an AutoResearch candidate pool and
provider allowlist must name it explicitly. Kimi K3 is cataloged as a candidate,
not a champion, until held-out benchmark and promotion receipts prove it.
Configured-runner cost estimates include its separate input and output token
rates so the existing per-sample cost gate can reject over-budget results.

`src/model_autoresearch_campaign_execution_artifact_supply_bootstrap.py` can
use this runner only when `REDDOG_MODEL_AUTORESEARCH_CAMPAIGN_RUNNER_MODE` is
set to `configured_gateway`, prompt records are supplied from outside the repo,
providers are explicitly allowlisted, an outside-repo output evidence path is
supplied, immutable model-budget evidence and distinct attempt/success receipt
paths are supplied outside the repo, and verifier mode is `exact_output_digest` or
`output_evidence_semantic`. The default remains deterministic fixture execution.

Configured live execution remains **HALTED**. The budget bundle is
self-authenticated operator evidence, not canonical catalog admission; gateway
usage remains estimated rather than authoritative. The runner's 1 MiB limit is
post-buffer: `requests.post()` and `response.json()` can allocate an unbounded
response first, so there is no model-budget-specific pre-buffer transport
bound. Whole-file input and receipt reads also remain unbounded, and no
exclusive runtime-directory claim preserves path identity from preflight
through execution. See
`docs/audits/ai_intelligence/CONFIGURED_AUTORESEARCH_GATEWAY_WSP97_ASSUMPTION_AUDIT_20260724.md`
and its structurally validated
`CONFIGURED_AUTORESEARCH_GATEWAY_WSP97_EXECUTION_RECEIPT_PHASE1.json`.

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
payload can be emitted. Single-model chains pass through their existing typed
evidence object. Panel binding requires the separate aggregate proof described
below; a collection of otherwise-valid single-model proofs is insufficient.

`src/model_panel_signed_evidence.py` verifies every member's complete existing
single-model chain before it admits a signed PANEL envelope. The envelope binds
the exact ordered role/model/provider members, per-member evidence IDs and
digests, catalog, selection, task, topology, policy and runtime-surface context,
plus an explicit synthesizer. Aggregate trust, signature, revocation, freshness
and optional nonce consumption are checked only after all member and anti-splice
checks pass. This slice enables the runtime-binding receipt to represent a
verified panel. The returned proof is process-local, sealed, non-copyable and
non-serializable; runtime binding requires the exact factory-issued identity and
rechecks its canonical aggregate, member, context and synthesizer projections.
This slice does not wire any Fusion consumer or choose panel members.

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
