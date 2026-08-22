# AI Gateway Module Change Log

## [2026-08-22] - Nemotron Exact Model Lifecycle Evidence

- Replaced the assumed already-loaded proposer boundary with an explicit exact
  LM Studio model transaction using native installed/resident instance truth.
- Bound lifecycle receipt ID/digest, exact instance, observed configuration,
  origin, and load/unload confirmation into the v2 shadow-call receipt.
- Added a public joint validator for lifecycle/call structural agreement and
  documented that deterministic hashes are content addressing, while existing
  signed proposer provenance supplies authentication.
- Managed proposer loads now inherit node/port-wide capacity serialization,
  maximum-context preflight, and durable interrupted-load recovery/quarantine.
- Kept Nemotron evaluation-only and reasoning-off with no server launch,
  download, fallback, verifier, promotion, or production-binding authority.

## [2026-08-21] - Production Binding Restart and Reservation Closure

- Moved supplier writes off deterministic claim markers onto fresh per-attempt
  paths. Process death before either seal no longer wedges retry; unproved
  orphan files are preserved, while terminal v3 durably binds each sealed
  source path and exact device/inode/size/content proof for recovery.
- Reserved the exact authority nonce/binding before provider entry and keyed
  the runtime lock by authority nonce. Competing output bindings now permit one
  provider callback; an unreadable existing provider receipt fails closed and
  cannot be collapsed into absence or trigger another callback.
- Added exact POSIX restart repair for death between hard-link publication and
  source unlink, plus the corresponding two-link pending/target state in
  immutable record creation. Repair removes only the exact proven sibling link
  and flushes affected directories under the documented controlled-principal
  boundary. Recovery transfers retained-descriptor ownership only after both
  artifacts and all trust/evidence/time checks succeed; any later failure
  closes every descriptor already acquired. Validation: complete AI Gateway
  suite 830 passed, 5 platform skips; crash/WSP-62 matrix 17 passed, 3 platform skips; WSP-62 and
  diff-check passed. WSP 00/15/22/50/62/97.

## [2026-08-21] - Production Binding Ownership and Crash-Safety Correction

- Replaced consumable zero-byte final claims with durable tokenized hidden-stage
  claims. The provider bundle is persisted immediately after callback;
  pre-terminal retry resumes it with zero callback and repeats current
  authority, signature, evidence, runtime, and pure-time verification.
- Retained exact stage descriptors through terminal digest and non-replacing
  publication. Terminal v3 receipts bind source path/device/inode/size/content proofs.
  Same-content replacement, hard links, symlinks, foreign stage swaps, and
  occupied finals fail closed without deleting the foreign object.
- Cleanup now removes or quarantines only an exact owned identity/content proof.
  Windows publication renames the verified object by handle. POSIX uses an
  exact non-replacing link commit under the documented same-principal runtime
  directory boundary; it does not claim arbitrary same-UID exclusion.
- Changed immutable receipt/publication creation to same-directory temporary,
  file fsync, identity verification, non-replacing commit, and lineage fsync.
  Midwrite process death can leave only a hidden pending file, not a partial
  final record. Current validation is recorded in the 2026-08-21 corrective
  entry above. WSP 00/15/22/50/62/97.

## [2026-08-21] - Production Binding Terminal Recovery Hardening

- Derived exact authority-use identity before the external evidence callback,
  so exact APPLIED replay and conflicting output bindings decide with zero
  callback. Trusted time, campaign authority, and signed evidence refresh after
  callback and immediately before APPLIED completion.
- Added deterministic hidden stages and a bounded durable terminal receipt.
  APPLIED ambiguity, AUTHORIZED retry, and partial two-file publication now
  rehydrate and use-time verify exact artifacts without provider replay. No
  valid final artifact is exposed before APPLIED. Cleanup failure is surfaced
  and attempts explicit `.invalid.*` quarantine; if quarantine rename also
  fails, an explicit cleanup failure preserves the artifact. This is restart
  recovery, not a false claim of two-file filesystem atomicity.
- Sealed each regular, single-link stage with file and parent-directory fsync
  before terminal persistence, and flushed each final parent after rename.
  Pre-terminal stage durability failure leaves no terminal/APPLIED/final;
  post-APPLIED final-directory ambiguity resumes from the terminal with zero
  provider callback.
- Added fresh callback-free temporal checks after authority/evidence/runtime
  verification callbacks and before terminal/APPLIED/recovery publication.
  Authority, both signed evidence receipts, and runtime valid-until are checked
  from the same final trusted-time sample; callback clock advancement fails
  closed without terminal or remaining-stage publication.
- Validation: 52 focused authority/provenance/production/WSP-62 tests passed;
  the complete AI Gateway suite passed 815 with 2 skips. Scoped Ruff lint and
  format checks passed. WSP 00/15/22/50/62/87/97.

## [2026-08-21] - Governed Multi-Call and Authenticated Promotion Composition

- Added atomic preparation/reservation of the complete bounded configured
  gateway campaign before first provider egress, exact per-call receipts, and
  deterministic campaign rehydration. A two-task exact local Nemotron run
  completed without fallback.
- Added externally signed, durable proposer-call/admission provenance and a
  separate campaign-promotion authority binding execution, policies, and exact
  candidates. Short TTL, revocation, trust, signature, replay, substitution,
  and output-preflight failures close before promotion use.
- Added a single-model handoff into the existing independent signed production
  evidence, deterministic selection, and runtime-binding artifact supply.
  The handoff independently authenticates the exact durable campaign authority
  at use time, mirrors issuance TTL limits, and now proves already-APPLIED
  upstream publication through a non-mutating status read; missing, RESERVED,
  or AUTHORIZED markers reject without advancement. It preflights runtime
  policy/trust and transactionally acquires both exclusive output claims before
  external evidence, rolling back owned placeholders on partial failure, and
  uses durable exact publication state for restart-safe retry and replay
  rejection. Private keys/signers remain external; panel promotion remains
  shadow-only.
- Extracted configured runner construction, canonical prompt-guard ownership,
  campaign-member preflight, and transactional exclusive output claims into
  `model_autoresearch_campaign_configured_runtime.py`. The WSP-62 bootstrap
  ceiling decreased from 235 to 233 lines and its file ceiling from 920 to 868.
- Extracted exact AI Gateway, LM Studio, and routed caller adapters from the
  configured runner. The runner is now 759 lines, below its prior 769-line
  ceiling, and both files have no function above the WSP-62 50-line ceiling.
- Hardened new receipt and publication writes with fail-closed file plus
  directory-lineage durability. Exact identical retries can complete a failed
  directory flush without treating the earlier write as durable. Windows
  flush and close calls now declare the pointer-width `HANDLE` and `BOOL` ABI
  explicitly, preventing default C-integer handle conversion. Extracted this
  platform boundary into a 138-line durability module; the evidence module is
  held to 910 lines, only 21 above its exact 889-line parent. Corrected the
  obsolete documentation claim that configured execution was one-call-only.
  WSP 00/15/22/50/62/87/97.

## [2026-08-21] - Verified Topology Resolution and Nemotron Shadow Proposer

- Added a process-local one-shot resolver from canonically verified runtime
  bindings to exact role/provider/model endpoints; unsupported providers and
  replay reject without fallback or a model call. Resolutions now carry the
  evidence expiry and a maximum 60-second TTL checked against trusted time at
  consumption, so one-shot authority cannot be retained past freshness.
- Added bounded evaluation-only Nemotron proposal generation through LM Studio's
  native reasoning-off API. Nemotron returns compact ordered model IDs only;
  deterministic code owns providers, roles, catalog/requirements binding, and
  admission into held-out AutoResearch candidates. The deterministic Gateway
  incumbent is injected into every accepted benchmark outside model control.
- Merged complementary static/live catalog cards with conservative field-level
  provenance and registered current OpenRouter GLM, DeepSeek, Qwen, Kimi, and
  Nemotron candidates without creating champion authority. Missing or disjoint
  provider modality evidence remains unknown; it is never synthesized as text.
- Live validation against a bounded evaluation catalog: exact local Nemotron ID loaded; two four-role candidates
  admitted in 36.7 seconds with content-bound call/admission receipts. Configured
  multi-call/panel AutoResearch remains halted. WSP 15/22/50/62/97.

## [2026-08-21] - Exact Kimi K3 Request-Truth Boundary

**Who/Type/Slice:** 0102 architect / Defensive /
`REDDOG_KIMI_K3_REQUEST_TRUTH_PHASE1`

**What:** Hardened the exact `openrouter` / `moonshotai/kimi-k3` provider path.
Explicit completion budget overrides environment, then the resolved value is
floored to 4,096. Valid 8,192 through 131,072 requests are preserved; 131,073
fails before HTTP. K3 always forces maximum reasoning and omits temperature.
Non-K3 behavior is unchanged.

**Validation boundary:** Offline mocked HTTP tests cover explicit, environment,
precedence, floor, endpoint maximum, reasoning, temperature omission, and
non-K3 compatibility. The focused gateway/advisory matrix passed 176 tests;
the complete AI Gateway module passed 742 tests with 2 skips. No provider call
or promotion authority was exercised.

**WSP References:** WSP 00, WSP 15, WSP 22, WSP 49, WSP 50, WSP 62, WSP 97.

## [2026-07-30] - Shared Model-Evidence Authority Validation

**Who/Type/Slice:** 0102 architect / Defensive /
`REDDOG_ARTIFACT_GENERATION_BOUND_MODEL_RUNTIME_PHASE1`

**What:** Consolidated exact trusted-key validation, signer independence, and
panel-authority independence into one bounded helper used by both SINGLE and
PANEL evidence paths. This removes duplicate policy islands without weakening
freshness, revocation, topology, or signer-role checks.

## [2026-07-30] - Runtime-Binding Evidence Admission Hardening

**Who/Type/Slice:** 0102 architect / Defensive /
`REDDOG_ARTIFACT_GENERATION_BOUND_MODEL_RUNTIME_PHASE1`

**What:** Replaced mapping-presence trust with canonical signed-evidence
rehydration and closure-confined one-shot capability issuance. The production
consumer shares no importable issuer, seal, or registry; capabilities created
by another factory instance are rejected. Runtime-binding capabilities bind
the full persisted artifact and verification receipt. Trusted keys resolve
only by exact `(role, fingerprint, key_epoch)` identity; role-only fallback is
rejected. Benchmark, promotion, panel-authority, and panel-member signers must
be independent.

**Truth boundary:** A serialized verification mapping is audit evidence, not
authority. Only fresh re-verification against host-pinned keys, revocation,
policy, topology, and time can issue the one-shot capability consumed at the
provider boundary.

**Validation:** Full AI Gateway `732 passed, 2 skipped`; focused authority
surface `336 passed, 1 skipped`; compileall, WSP 62, diff, NUL, and added-line
ASCII checks passed.

**WSP References:** WSP 00, WSP 15, WSP 22, WSP 50, WSP 62, WSP 97.

## [2026-07-29] - Provider Catalog Runtime Header and Chronology Hardening

**Who/Type/Slice:** 0102 architect / Defensive /
`REDDOG_HEALTH_AND_MODEL_FRESHNESS_ROUTING_PHASE1`

**What:** Normalized aiohttp header-name subclasses to exact strings before
the strict transport validator, fixing real HTTP 200 catalog discovery that
previously failed as `transport_failed`. Added allowlisted `canonical_slug`
and `created` provider fields so a freshness receipt can distinguish exact
availability from provider chronology.

**Truth boundary:** Provider chronology is candidate metadata only. It does
not prove task fitness, promotion, availability at execution time, or
production authority.

## [2026-07-24] - OpenRouter Endpoint Route Single-Call Admission Phase B2A

**Who/Type/Slice:** 0102 RedDog Architect isolated worker / Defensive
Eligibility / `OPENROUTER_ENDPOINT_ROUTE_SINGLE_CALL_ADMISSION_PHASE_B2A`

**What:** Added strict bounded projection of externally supplied OpenRouter
endpoint payloads, immutable byte/receipt/route lineage, trusted one-call policy
and intent contracts, and a pure canonical admission receipt binding the exact
POST route, provider order, no-fallback policy, supported controls, token/
context/response limits, Decimal cost reservation, and trusted exact `(0,)`
endpoint-status policy. Unknown additive price keys now fail closed even at
zero; only the current official endpoint-status enum crosses projection. The
trusted policy and independent admission derivation both require the exact
emitted-control set `("max_tokens", "reasoning")`; explicit model
`supports_max_tokens=false` contradicts the emitted cap. Request-price presence
is preserved, and absence becomes zero only under a named, digested OpenRouter
PublicPricing schema-policy proof.

**Integration migration:** Rebased the single focused slice onto
`origin/main` `a3c13f05299bf745a1fc01650e1ae91f0db2f820` after WSP_97 PR #1334.
Migrated the execution receipt to `wsp97_execution_receipt.v1.1` with exact
repository context. Corrected the Chat Completions wire overlay to the exact
keys `max_tokens`, `reasoning`, and `provider`; `max_completion_tokens` remains
only the internal admission/budget field. Deterministic admission IDs now
rederive from the corrected control object.

**Truth boundary:** `runtime_authority=eligibility_only`. No metadata-fetch,
network, model, provider, credential, gateway, configured-runner, caller, or
startup call was added. Availability, job certification, and output-training
permission stay separate; the POC is evaluation-only and fails closed for
requested ZDR or training authority. Live execution remains explicitly halted
for authenticated endpoint supply, atomic consumption, authoritative
availability and usage, caller wiring, pre-buffer response enforcement, and
runtime-directory identity.
`endpoint_status_policy_accepted` proves policy membership, not availability.
The request-price schema proof is not authoritative billing/usage evidence.

**WSP_15 MPS:** Complexity 4 + Importance 5 + Deferability 5 + Impact 5 = 19
(P0 defensive trust boundary).

**Validation:** Initial amendment RED: `8 failed, 20 passed`; emitted-control/
request-price amendment RED: `9 failed, 25 passed`; integration wire-key RED:
`2 failed, 34 passed`. Post-rebase endpoint/admission: `65 passed`; combined
protected catalog/execution-control: `134 passed`; full AI Gateway: `712 passed,
2 skipped`. Ruff, WSP_62, JSON, diff, and WSP_97 v1.1 receipt validation passed.
No provider, model, network, or credential call occurred.

**WSP References:** WSP 00, WSP 15, WSP 22, WSP 50, WSP 62, WSP 97.

---

## [2026-07-24] - OpenRouter Model Execution-Control Evidence Phase B1

**Who/Type/Slice:** 0102 RedDog Architect isolated worker / Provider Evidence /
`OPENROUTER_MODEL_EXECUTION_CONTROL_EVIDENCE_PHASE_B1`

**What:** Evolved the v1 candidate payload compatibly to retain only strict
optional `reasoning` and `top_provider` projections, then added immutable
exact-model evidence binding canonical prices, supported parameters, candidate
and discovery lineage, source-record/control digests, freshness, and a
recomputed content ID.

**Truth boundary:** Unknown provider prose, names, secrets, default parameters,
and per-request limits are dropped. Partial assertions, explicit empty effort
lists, and omitted/null distinctions remain truthful candidate evidence.
Malformed recognized fields and contradictory co-present claims fail closed.
This trust class is provider-asserted only: no endpoint discovery, sampling
default, canonical route, selection, promotion, transport, provider call,
credential access, startup wiring, or live authority was added.

**WSP_15 MPS:** Complexity 4 + Importance 5 + Deferability 5 + Impact 5 = 19
(P0 defensive trust boundary).

**Validation:** Focused execution-control/catalog/protected matrix: `112
passed`. Full AI Gateway: `647 passed, 2 skipped`. Ruff and WSP_62 source-file/
function gates passed. The projection and evidence modules are explicitly
enrolled in authority-import, network-purity, line-ceiling, and AST function
guards. Tests were offline; no provider, model, network, or credential call
occurred.

**WSP References:** WSP 00, WSP 15, WSP 22, WSP 50, WSP 62, WSP 81, WSP 97.

---

## [2026-07-24] - Configured AutoResearch Gateway Safety Contract v2

**Who/Type/Slice:** 0102 Codex worker / Defensive Reliability /
OPENROUTER_AUTORESEARCH_CANARY_PHASE1

**What:** Replaced permissive configured-runner inputs with exact immutable
model-budget and reasoning evidence, canonical fully wrapped prompt guarding,
authoritative Decimal cost reservation, exact gateway token/reasoning controls,
durable attempt/success receipts, and typed tamper-detecting receipt readers.
The semantic verifier now authenticates the persisted v2 success receipt.

**Concurrency/security boundary:** Panel capacity is reserved atomically.
Persisted attempts remain consumed; only a definitely unstarted suffix is
released in a per-run `finally`. Caller entry is never rolled back, terminal
persistence failure is indeterminate, and cancellation/SystemExit/
KeyboardInterrupt/other BaseException signals are not swallowed. No live
provider call, startup default, promotion, registry, HoloIndex, worker, or
repository-mutation authority was added.

**Comparative-canary gap:** Sampling controls and the provider endpoint are not
yet catalog-bound evidence. This slice therefore makes no K3-vs-GLM ranking
call and performs no live comparative canary.

**WSP_15 MPS:** Complexity 5 + Importance 5 + Deferability 5 + Impact 5 = 20
(P0).

**WSP References:** WSP 00, WSP 15, WSP 22, WSP 50, WSP 62, WSP 97.

**Corrective safety gate:** Campaign admission now computes the complete
selected-role x task call count and requires exactly one executable planned
call in this POC. It also requires an explicit total-call cap, exact budget for
every selected assignment, canonical positive Decimal strings, exact
provider/API routes, distinct empty write artifacts, bounded final prompts,
durable output evidence before completion, and duplicate-role rejection.
Multi-call and panel campaigns remain halted pending atomic whole-campaign
preparation. Live execution remains halted pending canonical catalog admission,
authoritative usage, model-specific pre-buffer response-byte transport bounds,
bounded input/receipt reads, and an exclusive runtime-directory claim or
equivalent path-identity boundary.

**WSP_62:** New/touched helpers are at most 50 lines; root `main.py` is 4,974
lines and its touched architect function is 953. The bootstrap entry point grew
from 208 to 235 lines; inherited semantic factory/closure remain 96/83.
Module-local temporary exact no-growth ceilings, owner/reviewer, 2026-09-30
expiry, mechanical tests, and ROADMAP decomposition anchors govern these three
inherited boundaries.

**Validation:** 88 focused corrective/bootstrap/semantic/evidence tests and the
targeted root-main environment-threading test passed. Full AI Gateway: 587
passed, 2 platform-capability skips. Ruff on the changed module/test scope,
compileall, and diff-check passed. All callers/transports were injected; no
live provider call was made.

**WSP_97 evidence:** The assumption audit and structurally validated execution
receipt are stored under `docs/audits/ai_intelligence/` as
`CONFIGURED_AUTORESEARCH_GATEWAY_WSP97_ASSUMPTION_AUDIT_20260724.md` and
`CONFIGURED_AUTORESEARCH_GATEWAY_WSP97_EXECUTION_RECEIPT_PHASE1.json`.

---

## [2026-07-24] - Idle OpenRouter Catalog Schedule Adapter

**Who/Type/Slice:** 0102 Codex / Defensive Reliability /
OPENROUTER_CATALOG_SCHEDULE_ADAPTER_PHASE1

**What:** Added a daily-only adapter from the exact idle durable claim to the
existing scheduled replay guard. The adapter derives the invocation, returns an
exact six-key bounded projection, normalizes all status/reason codes locally,
and canonically rehydrates typed receipt/candidate evidence before accepting
completion.

**Truth Boundary:** Default-off idle execution; tests use injected offline
transport, and trusted runtime evidence remains outside the repository.
Replay/finalization requires exact evidence lineage. No catalog bridge, model
selection, promotion, registry mutation, runtime binding, startup hook, or
general scheduler was added.

**WSP_15 MPS:** Complexity 4 + Importance 5 + Deferability 5 + Impact 5 = 19
(P0).

**MPS rationale/remediation:** A forged exact dataclass could previously
carry matching oversized identifiers, and raw guard status/reason text could
cross the adapter. Canonical rehydration, fixed local projection codes, bounded
six-key output, recursive-data rejection, and cancellation-preserving tests
close that false-evidence and secret-disclosure boundary.

**Validation:** `174 passed, 1 skipped` focused; `575 passed, 3 skipped`
combined AI Gateway + IdleAutomation + runtime-artifact-safety scope. All
validation calls used injected offline transport; no live provider call was
made.

---

## [2026-07-24] - Scheduled Provider Discovery Replay Guard

**Who:** 0102 Codex worker, architect-audited lane
**Type:** Defensive Reliability / Durable Replay Control
**Slice:** SCHEDULED_PROVIDER_DISCOVERY_REPLAY_GUARD_PHASE1

**What:** Added a scheduled-only execution boundary around the existing direct
OpenRouter catalog discovery. The boundary serializes the complete operation
off-loop under one cross-process lock and publishes a strict bounded
per-invocation `ARMED`/terminal replay ledger before and after transport.

**Truth Boundary:**
- IMPLEMENTED: fixed outside-repository guarded identities, admission recheck
  under lock, exact terminal replay, fail-closed ARMED/indeterminate/malformed
  recovery, chronology-proved missing-entry migration, wall-clock rollback
  rejection, capacity/expiry controls, and bounded large-candidate reads.
- IMPLEMENTED: offline same-loop/process concurrency, crash-window, legacy
  evidence, cancellation/lock-waiter continuation, deep-JSON, link,
  ledger-write, large-candidate, and authority isolation regressions.
- NOT IMPLEMENTED: scheduler installation, startup/network routines, selection
  or promotion authority, registry/runtime binding, or changes to manual
  discovery. Manual/direct callers must not use the guarded fixed identities.

**WSP_15 Score:** Complexity 4 + Importance 5 + Deferability 5 + Impact 5 =
19 (P0 durable replay and duplicate-provider-call prevention boundary).

**WSP References:** WSP 00, WSP 15, WSP 22, WSP 50, WSP 62, WSP 97.

**Validation:** Scheduled/replay/protected focus: 44 passed, 1 Windows symlink
capability skip. Full ai_gateway: 378 passed, 2 Windows capability skips.
Idle automation: 126 passed. Runtime artifact safety: 11 passed, 1 Windows
symlink capability skip. Ruff, compileall, and diff-check passed.

---

## [2026-07-24] - Provider Discovery Defensive Reliability Hotfix

**Who/Type/Slice/WSP:** 0102 Codex / Defensive Reliability / DIRECT_PROVIDER_DEFENSIVE_RELIABILITY_20260723 / 15,22,50,62,97
**What:** Added truthful non-3xx redirect-history receipts; retained verified
artifact identity through publication; added Windows exact-handle rename,
identity-aware cleanup, and exact prior-target rollback on detected mismatch.
**Truth:** Path replacement, hard links, and supported symlinks fail closed.
Non-Windows publication requires a trusted non-shared runtime directory;
parent-directory fsync and Windows sync/mode behavior remain limited.
No live network/provider/runtime/Holo or authority mutations were performed.
**Validation:** 98 passed / 1 Windows symlink skip focused; 339 passed / 1
skip full ai_gateway.

## [2026-07-23] - Provider Catalog Atomic Artifact Repair

**Who:** 0102 Codex worker, independent reviewer-driven repair
**Type:** Security / Crash-Safe Artifact Durability
**Slice:** DIRECT_PROVIDER_SNAPSHOT_AND_BOUNDED_DISCOVERY_PHASE1_REPAIR2

**What:** Replaced destructive runtime artifact writes with a module-local,
same-directory atomic store for both attempt receipts and candidate snapshots.
Exact UTF-8 bytes are flushed and fsynced before locked replacement; failure
removes the temporary file while preserving the prior target byte-for-byte.

**Truth Boundary:**
- IMPLEMENTED: confined exclusive temp files, regular-file and link checks,
  target-mode preservation, injected partial-write/fsync/replace regressions,
  best-effort parent-directory fsync, and reason-specific FAILED evidence.
- NOT IMPLEMENTED: shared runtime-safety changes, live provider calls,
  scheduling, registry/selection/promotion mutation, or runtime binding.

**WSP_15 Score:** Complexity 4 + Importance 5 + Deferability 5 + Impact 5 =
19 (P0 crash-safety and receipt-truth boundary).

**WSP References:** WSP 15, WSP 22, WSP 50, WSP 62, WSP 97.

---

## [2026-07-23] - Direct Provider Discovery Independent NO-GO Repair

**Who:** 0102 Codex worker, independent reviewer-driven repair
**Type:** Security / Durability Hardening
**Slice:** DIRECT_PROVIDER_SNAPSHOT_AND_BOUNDED_DISCOVERY_PHASE1_REPAIR1

**What:** Closed seven trust-boundary blockers covering exact model identifiers,
future-dated candidate observations, receipt state coherence, hostile HTTP
metadata, candidate-before-COMPLETED durability, truthful pre-call transitions,
and exact prior-candidate ID admission.

**Truth Boundary:**
- IMPLEMENTED: content-free rejection of hostile response objects and metadata,
  truthful durable intent/armed/terminal transitions, last-known-good
  preservation on candidate failure, and adversarial regression coverage.
- NOT IMPLEMENTED: provider calls in tests, automatic scheduling, registry or
  selection mutation, promotion, runtime binding, or RedDog evidence changes.

**WSP_15 Score:** Complexity 4 + Importance 5 + Deferability 5 + Impact 5 =
19 (P0 security and durable-truth boundary).

**WSP References:** WSP 15, WSP 22, WSP 50, WSP 62, WSP 97.

---

## [2026-07-23] - Direct Provider Snapshot and Bounded Discovery

**Who:** 0102 Codex worker, architect-audited lane
**Type:** Provider Evidence / Offline-Bounded Discovery
**Slice:** DIRECT_PROVIDER_SNAPSHOT_AND_BOUNDED_DISCOVERY_PHASE1

**What:** Added an explicit, unauthenticated OpenRouter model-list refresh with
strict JSON and record normalization, digest-bound invocation/attempt/candidate
receipts, freshness-aware rehydration, and an idempotent bridge to the existing
canonical model catalog builder.

**Truth Boundary:**
- IMPLEMENTED: manual or pre-authorized scheduled one-shot invocation, fixed
  GET envelope, redirect/deadline/body/record bounds, duplicate-group poison
  handling, allowlisted candidate metadata, separate outside-repository attempt
  and last-known-good artifacts, and offline injected-transport tests.
- NOT IMPLEMENTED: automatic scheduling, registry mutation, model selection or
  promotion, runtime binding, RedDog provider evidence, provider credentials,
  startup imports, or live provider calls in tests.

**WSP References:** WSP 15, WSP 22, WSP 50, WSP 62, WSP 97.

---

## [2026-07-18] - Signed Aggregate Fusion PANEL Evidence

**Who:** 0102 Codex worker, architect-audited lane
**Type:** Production Evidence / Runtime Binding Security
**Slice:** MODEL_SIGNED_PANEL_EVIDENCE_PHASE1

**What:** Added a separate signed aggregate PANEL envelope and required it for
PANEL runtime binding. Every member's existing signed benchmark/promotion chain
is verified first; the aggregate binds ordered roles, models, providers,
per-member evidence IDs/digests, catalog, selection, task, topology, policy,
runtime surface and explicit synthesizer before aggregate signature and nonce
admission.

**Truth Boundary:**
- IMPLEMENTED: process-local sealed PANEL proof, deterministic rehydration,
  independent member verification, anti-splice checks, signer trust/revocation/
  freshness, replay rejection, exact runtime identity/projection gate, and
  adversarial construction/replacement/copy/pickle tests.
- NOT IMPLEMENTED: Fusion consumer wiring, provider calls, model discovery or
  ranking, artifact supply/bootstrap, WRE scheduling, OpenClaw/Hermes changes,
  signing/private-key custody, durable nonce/trust stores, live execution.

**WSP References:** WSP 00, WSP 15, WSP 22, WSP 50, WSP 62, WSP 97.

**WSP_15 Score:** Complexity 4 + Importance 5 + Deferability 5 + Impact 5 =
19 (P0 security boundary).

---

## [2026-07-18] - Kimi K3 OpenRouter AutoResearch Candidate

**Who:** 0102 Codex
**Type:** Model Candidate / Configured Gateway Wiring
**Slice:** MODEL_AUTORESEARCH_OPENROUTER_KIMI_K3_PHASE1

**What:** Added Kimi K3 to the static candidate catalog and enabled the existing
configured AutoResearch gateway to target exact OpenRouter model assignments.

**Why:** The combination harness and campaign loop were already implemented, but
`AIGatewayConfiguredModelCaller` could not execute an OpenRouter candidate. This
prevented governed held-out comparison of Kimi K3 with RedDog's existing panel.

**Truth Boundary:**
- IMPLEMENTED: explicit `openrouter` provider, exact `moonshotai/kimi-k3`
  candidate metadata, mandatory-max-reasoning request shape, 4096-token default,
  separate input/output cost accounting, catalog and caller tests.
- NOT IMPLEMENTED: automatic fallback to OpenRouter, automatic promotion,
  implicit candidate-pool mutation, or bypass of benchmark/verifier receipts.

**WSP References:** WSP 15, WSP 22, WSP 50, WSP 84, WSP 97.

**WSP_15 Score:** Complexity 3 + Importance 4 + Deferability 4 + Impact 4 =
15 (P1).

---

## Future Changes
- Enhanced routing algorithms (Phase 1)
- Cost optimization features (Phase 2)
- Enterprise monitoring (Phase 3)
- Multi-provider ensemble methods (Phase 4)
