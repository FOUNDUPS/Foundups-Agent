# AI Gateway Module

**Module Purpose**: Unified AI service access with intelligent routing, fallback, and load balancing across multiple AI providers.

**WSP Compliance Status**: [OK] WSP 49 (Module Structure), WSP 3 (Enterprise Domain), WSP 27 (DAE Architecture)

**Dependencies**: requests>=2.25.0; aiohttp>=3.9,<4

## Exact Kimi K3 Request Contract

The provider boundary applies a model-specific contract only to provider
`openrouter` with model `moonshotai/kimi-k3`. After explicit request, provider
environment, and default resolution, `max_tokens` is floored to 4,096 without
truncating valid larger requests. The maximum is 131,072, matching the bounded
OpenRouter endpoint fixture; 131,073 and higher fail before HTTP. K3 always
emits `reasoning={"effort":"max"}` and omits `temperature`. Other provider/model
pairs retain their existing request behavior.

[VERIFIED] The contract is covered by offline mocked-transport tests; it does
not grant model promotion, provider availability, or live-call authority.

## Model Intelligence Catalog

`src/model_intelligence_catalog.py` provides the runtime evidence layer for
RedDog model intelligence. It normalizes static registry entries, provider
catalog payloads, and local role-resolution results into immutable
`ModelCatalogSnapshot` receipts.

This layer does not choose a model, call a provider, run benchmarks, or promote
any model to production. Provider catalog entries and `latest`-style aliases are
eligible candidates only; later benchmark and verifier receipts must promote
champion/challenger status.

Static task policy and live provider evidence for the same provider/model are
merged into one conservative card. Live catalog evidence owns context, price,
protocol capabilities, and availability; static policy may add task-family
intent. Conflicting provider records intersect supported parameters and
capabilities, use the smallest context and highest price, and never synthesize
availability, modalities, or champion state. Missing/disjoint modality evidence
remains empty and therefore fails any modality requirement.

## Nemotron Shadow Topology Proposals

`model_topology_proposal_lm_studio.py` acquires one exact local
`nvidia/nemotron-3.5-lightning` model transaction and calls the verified
instance through LM Studio's native reasoning-off route. It borrows a
pre-existing instance or explicitly loads and then unloads its own instance;
managed loading is serialized per physical node/port and admitted only when no
other instance is resident. It never starts LM Studio, downloads a model,
evicts a pre-existing model, or falls back. The content-addressed lifecycle
receipt is jointly bound into the proposer call evidence; neither hash is an
authentication boundary. Existing short-lived signed proposer provenance
authenticates the pair before downstream authority. The
model returns only two compact ordered model-ID arrays; deterministic code owns
role/provider/catalog/requirements projection. `model_topology_proposal_admission.py`
then rejects unknown models, provider substitutions, role/topology drift,
duplicates, malformed output, and every production-scoped proposal.

Accepted candidates are shadow inputs to the existing held-out combination
benchmark harness, which always includes the deterministic AI Gateway incumbent
outside proposer control. Nemotron does not select production models, act as
verifier, promote a champion, or bind runtime defaults.

The configured gateway runner now prepares and reserves the complete bounded
task-by-candidate call set before first egress. It then executes only those exact
members and records content-free, content-addressed call evidence. The earlier
live two-task run proved the exact model route but predated native
residency/ownership receipts; it is historical evidence, not release authority.
Offline lifecycle and proposer contracts are the current release authority.

`model_autoresearch_campaign_configured_runtime.py` owns configured runner
construction, canonical prompt-guard injection, typed campaign-member
preflight, and transactional exclusive outside-repository output claims. The startup bootstrap
only validates runtime inputs and coordinates that bounded component. This
WSP-62 decomposition lowered the bootstrap function and file ceilings instead
of expanding an exemption.

`model_autoresearch_configured_gateway_callers.py` owns the exact AI Gateway,
LM Studio, and routed caller adapters used by that runner. These adapters
preserve the admitted provider/model/API route and do not start a local server
or introduce fallback.

Authenticated proposer provenance binds the exact LM Studio call and
deterministic admission receipt to an externally signed, short-lived receipt
stored outside the repository. Campaign authority separately binds that
provenance, campaign execution, normalized policies, and exact candidate set
before any promotion gate can emit champion evidence. Durable replay state is
required; neither module owns signing keys. The production handoff accepts
only single-model candidates and delegates final independent benchmark and
promotion signatures to the existing signed-evidence verifier and runtime
binder. At use time it independently re-verifies the campaign signature,
trusted key, revocation epoch, trusted-time validity, exact durable receipt,
issuance-equivalent TTL bounds, and an already-APPLIED publication marker read
through a non-mutating exact-status API. Missing, RESERVED, or AUTHORIZED
publication state rejects without marker advancement. Runtime policy, evidence
trust, exact authority-use nonce/binding, and a durable tokenized staging claim
finish before the external evidence call; consumable final paths remain absent.
A nonce-level runtime lock and durable RESERVED binding precede the callback,
so competing output bindings cannot both reach the provider. A conflicting or
completed exact authority use is therefore decided with zero callback. An
unreadable existing provider receipt is not treated as absence. After
the callback, the bounded raw bundle is immediately persisted under the exact
binding. A pre-terminal retry resumes that bundle with zero callback and
re-verifies current trusted time, authority, signatures, evidence, and runtime
policy before any authority transition. After
the key, signature, store, and runtime-verification callbacks return, a fresh
trusted-time sample drives a callback-free check of authority time, both signed
evidence receipts, and the embedded runtime verification validity window.

Suppliers write to fresh per-attempt paths while durable claim markers remain
unchanged. A death before sealing can orphan an isolated file but cannot wedge
the deterministic claim; recovery never deletes that unproved orphan.
Successful sealed artifacts and the verified evidence bundle are bound into a
bounded durable terminal receipt before the two final paths are published.
Terminal v3 binds each source path and device/inode/size/content proof. Held
descriptors are rechecked for the terminal digest and immediately before and
after non-replacing publication. Same-content inode replacement, hard links,
symlinks, and foreign final occupation fail closed without deleting the
foreign object. Each publication is followed by a final-parent flush,
including recovery when a prior ambiguous attempt already moved one artifact.
This does not claim two-file filesystem atomicity: interruption can expose one
final path while the other remains staged. AUTHORIZED or ambiguously APPLIED
retries load the exact terminal receipt, materialize any remaining stage,
rehydrate both artifacts, and use-time verify the full evidence chain before
returning the same result without another provider callback, only while the
authority and evidence remain current. Cleanup removes or quarantines only an
exact retained identity/content proof; an ambiguous or foreign replacement
survives and raises an explicit ownership conflict. APPLIED state
without its exact terminal receipt fails closed and preserves evidence.
Aggregate panel promotion remains shadow-only.

Windows publishes the verified stage object by retained handle. POSIX uses a
non-replacing hard-link commit followed by exact source removal; the output
directory must therefore be controlled by the same principal as the process.
Recovery recognizes only the exact terminal-proved two-link inode left by
death between those POSIX operations, removes the proven source link, flushes
the affected directories, and resumes the final.
The POSIX path does not claim protection against an arbitrary same-UID writer.

New immutable receipt and publication files use a same-directory temporary,
file fsync, identity check, non-replacing commit, and directory-lineage fsync.
Process death can orphan only a hidden pending file, never expose a partial
final record. POSIX retry repairs the exact target/pending two-link state before
claim validation. An exact existing record is idempotent; a different record is a
deterministic conflict. `model_autoresearch_configured_gateway_durability.py`
owns the directory boundary so serialization remains WSP-62 bounded.

## Verified Runtime Topology Resolution

`model_runtime_topology_resolver.py` consumes the canonical verifier's opaque
runtime-binding capability once, preserves exact role/provider/model identity,
requires the consumer's explicit available-provider set, and mints a second
opaque one-shot topology capability. Unknown or unavailable providers reject;
there is no keyword routing, local/remote substitution, fallback, server probe,
server launch, or model call in this resolver. Consumption requires trusted
time and rejects after the earlier of evidence expiry or a 60-second resolver TTL.

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

### Provider-asserted execution-control evidence

`src/model_provider_execution_control_evidence.py` derives immutable,
content-addressed evidence for one exact model from a fresh, rehydrated
`ProviderCatalogCandidateSnapshot`. It binds the OpenRouter model-list source
endpoint, candidate and discovery lineage, exact canonical prompt/completion
prices, supported parameters, and allowlisted optional `reasoning` and
`top_provider` assertions.

Optional provider fields remain optional: omitted and explicit-null effort,
default-effort, or top-provider numeric claims are distinct, partial assertions
survive, and unknown nested fields are dropped. Malformed recognized values
and contradictory co-present claims poison the record. The result has trust class
`provider_asserted_model_execution_controls`; it is candidate evidence only,
not canonical route admission, endpoint discovery, sampling defaults,
selection, promotion, runtime binding, or permission to call a provider.

### Endpoint-route evidence and single-call eligibility

`src/model_openrouter_endpoint_payload_projection.py` and
`src/model_openrouter_endpoint_route_evidence.py` accept only externally
supplied, bounded OpenRouter endpoint fixtures. They project a strict recognized
schema, preserve null versus omission, bind exact response bytes and request
lineage, reject duplicate or prefix-ambiguous endpoint tags, and produce
immutable provider-asserted evidence for one exact route. They do not perform
metadata discovery, networking, authentication, or credential access. Pricing
is a closed allowlist: any unknown additive cost key is rejected even when its
reported value is zero. Endpoint status is restricted to the current official
enum; known negative states remain evidence but cannot satisfy the initial
trusted accepted-status policy `(0,)`.

`src/model_autoresearch_single_call_contracts.py` and
`src/model_autoresearch_single_call_admission.py` combine that route evidence
with fresh model-control evidence, one trusted job policy, and one content-bound
call intent. The resulting `CanonicalSingleCallAdmission` fixes the
`POST /chat/completions` route, endpoint order, no-fallback and
required-parameter controls, reasoning effort, exact Decimal price ceiling,
prompt/completion/context/response bounds, and a single-call limit.
The policy must contain the exact immutable emitted-control set
`("max_tokens", "reasoning")`, and admission independently derives the same
mandatory set. A model-level `supports_max_tokens=false` assertion is an
explicit contradiction and rejects; an omitted/unknown assertion is accepted
only when exact endpoint and model parameter evidence both include
`max_tokens`.
For the Chat Completions route, `request_control` is exactly the three-key
wire-control overlay `max_tokens`, `reasoning`, and `provider`.
`max_completion_tokens` remains the internal admission/budget field and never
appears in that wire overlay. Route headers, model/intent identity, stream
policy, and prompt bounds remain separately admission-bound rather than being
misrepresented as this control object.

OpenRouter `PublicPricing` requires `prompt` and `completion` while `request`
is optional. Admission preserves `request_price_present`; absence becomes zero
only under the named, content-digested
`openrouter_public_pricing_request_optional_absence_as_zero.v1` schema policy.
This is a local eligibility policy proof, not provider billing or usage proof.
The named `endpoint_status_policy_accepted` proof means only that the observed
status was present and belonged to the trusted job policy; it is not proof of
live or authoritative endpoint availability.

This receipt has `runtime_authority=eligibility_only`. It cannot be consumed as
permission to call a provider. Availability evidence, task-specific job
certification, and permission to train on output are independent decisions:
the current POC admits evaluation-only intent, fails closed when ZDR evidence is
requested, and never grants output-training permission. Live execution remains
halted pending authenticated endpoint supply, atomic admission consumption,
authoritative availability and usage, caller wiring, a pre-buffer response-byte
bound, and runtime-directory identity.

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
The configured bootstrap admits the complete bounded task-by-role campaign
only after atomic preparation and reservation before caller entry. Multi-task
and panel evaluation is admitted within explicit per-sample and campaign-wide
caps and exact budget, route, output, and receipt claims. Production/OpenRouter
activation remains halted by the separately documented live-admission gates.

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
