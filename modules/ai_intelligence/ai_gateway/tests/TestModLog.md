# AI Gateway TestModLog

## [2026-08-22] - Nemotron Lifecycle Receipt Binding

- Added valid, missing, and tampered lifecycle-receipt coverage for the local
  topology proposer; call evidence now binds the exact model instance and
  owned cleanup state.
- Added joint call/lifecycle validation that rejects a different lifecycle even
  when its unkeyed content ID is correctly recomputed; signed provenance, not
  either deterministic hash, remains the authentication contract.
- Revalidated authenticated proposer provenance and promotion authority against
  the v2 call receipt without live provider/model/network effects.

## [2026-08-21] - Restart, Provider-Presence, and POSIX Link Regressions

- Added real subprocess death at selection-only and selection-plus-runtime
  pre-seal points. Retry completes from the durable provider bundle with zero
  callback and leaves unproved isolated attempt artifacts untouched.
- Added unreadable durable provider-receipt and concurrent conflicting-binding
  regressions. Corruption/transient read failure is not absence, and only the
  nonce-reservation winner reaches provider code.
- Added POSIX-only subprocess coverage for death after final hard-link creation
  and after immutable target-link creation. Recovery accepts only the exact
  proof-bound nlink=2 state and durably removes the corresponding owned source
  or pending link. Invalid interrupted-publication payload, later runtime-proof
  failure, and post-open trusted-time failure prove every retained descriptor
  closes before fallback or rejection. Extended WSP-62 guards to both extracted
  helper modules.
- Commands: `python -m pytest modules/ai_intelligence/ai_gateway/tests/test_model_autoresearch_production_binding_crash_security.py modules/ai_intelligence/ai_gateway/tests/test_model_runtime_binding_wsp62_boundaries.py -q` -> `17 passed, 3 skipped` in 5.36 seconds; `python -m pytest modules/ai_intelligence/ai_gateway/tests -q` -> `830 passed, 5 skipped` in 31.49 seconds; exact manifest identity test -> `1 passed` in 62.81 seconds.
- Evidence location: this entry plus the final-SHA check rollup on PR #1529.
  WSP-62, Ruff, compileall, and diff-check passed locally.

## [2026-08-21] - Production ownership and process-crash regressions

- Added claim-race winner-token convergence and real subprocess death after an
  exact claim. Retry reuses the owned claim; a provider bundle persisted
  immediately after callback resumes with zero provider callback and fresh
  trust/time/evidence/runtime verification.
- Added foreign cleanup replacement and occupied-final probes, plus post-seal
  same-content inode replacement, hard-link, and symlink substitution. Foreign
  objects survive with explicit ownership conflict and never become finals.
- Added a real subprocess midwrite death against the immutable configured store.
  The final receipt remains absent, retry commits a complete record, and only a
  hidden pending temporary may remain from the killed process.
- Extended WSP-62 guards to atomic-create, claim, and retained artifact-identity
  modules. Current validation is recorded in the 2026-08-21 corrective entry
  above. WSP 00/15/22/50/62/97.

## [2026-08-21] - Production transaction immutable-audit regressions

- Added zero-callback exact/conflicting replay, APPLIED directory-flush
  ambiguity, AUTHORIZED terminal retry, callback/terminal authority expiry,
  partial final publication, and unlink-denial regressions. Production artifacts
  stage behind a durable terminal receipt; no valid final is exposed before
  APPLIED, recovery rehydrates and use-time verifies without provider replay,
  and cleanup quarantine is explicit and surfaced; failed quarantine rename
  preserves the artifact under an explicit cleanup failure.
- Added stage file/parent durability failure and post-APPLIED final-directory
  failure injection. The former proves zero terminal/APPLIED/final effects; the
  latter proves exact retry completes rename durability with zero callback.
- Added normal and recovery callbacks that advance trusted time after the prior
  sample. The final callback-free authority, signed-evidence, and runtime-window
  checks block terminal/APPLIED/final publication without provider replay.
- Extended the unchanged WSP-62 limits to every new
  output/freshness/JSON/recovery/rehydration/runner/terminal module. Validation:
  52 focused passed; full AI Gateway 815 passed, 2 skipped; scoped Ruff
  lint/format passed. WSP 00/15/22/50/62/87/97.

## [2026-08-21] - Governed AutoResearch and production-handoff contracts

- Added successful multi-task/panel configured campaigns plus zero-egress
  preflight, exact reservation membership, budget, route, and failure-release
  regressions.
- Added authenticated durable proposer and campaign-authority adversarial
  coverage for call/admission/campaign/policy substitution, trust, revocation,
  negative/overlong TTL, replay across restart, store failure, retry, and gate
  output preflight.
- Added single-model production handoff coverage through external independent
  signed evidence and the existing runtime binder; panel promotion is rejected.
  Added zero-effect forged/expired/revoked authority, malformed policy/trust,
  and preexisting-output preflight regressions plus restart-safe exact retry
  after a transient post-reservation runtime-supply failure.
  Added immutable publication-status regressions proving missing, RESERVED, and
  AUTHORIZED markers cannot be elevated by use-time verification, plus forged
  signed invalid/overlong TTL rejection with zero effects.
- Moved configured runtime construction/preflight into a bounded module and
  lowered the enforced bootstrap ceilings rather than expanding WSP-62.
- Added receipt/publication directory-lineage durability and fail-closed retry
  coverage, including explicit pointer-width Windows `HANDLE` ABI assertions
  for `FlushFileBuffers` and `CloseHandle`. Added source-shape gates that keep
  the configured runner at or below its prior 769-line ceiling, the caller
  module at or below 200 lines, the evidence module at or below 910 lines, the
  durability module at or below 200 lines, and every function in all four files
  at or below 50 lines.
- Added WSP-62 guards for the five extracted production-binding authority,
  preflight, transaction, evidence, and execution modules; each remains at or
  below 200 lines and every function remains at or below 50 lines.
## [2026-08-21] - Nemotron Proposal and Verified Topology Contracts

- Added offline coverage for conservative catalog-card merge, local compact
  Nemotron proposals, deterministic shadow admission, held-out harness handoff,
  exact runtime topology preservation, unavailable providers, and replay.
- Added fail-closed regressions for missing/disjoint provider modalities,
  post-expiry topology consumption, and deterministic incumbent inclusion in
  every proposer benchmark set.
- Live Nemotron evidence is documented in the module ModLog and is not required
  by the offline suite.

## [2026-08-21] - Exact Kimi K3 request truth

- Added an offline request matrix for explicit 256/4,096/8,192/131,072
  budgets, environment 256/8,192, explicit-over-environment precedence, forced
  maximum reasoning, temperature omission, and exact provider/model scope.
- Proved 131,073 rejects before mocked HTTP and non-K3 OpenRouter behavior is
  unchanged.
- Validation: exact K3 matrix 36 passed; focused gateway/advisory compatibility
  176 passed; full AI Gateway module 742 passed with 2 skips.

## [2026-07-30] - Model-runtime security test decomposition

- Split serialized-evidence, capability-identity, replay, revocation, and
  bootstrap regressions into a focused bounded module.
- Preserved every assertion while keeping the legacy artifact-supply matrix
  below the WSP 62 file limit.

## [2026-07-29] - Live provider header normalization and chronology

- Reproduced aiohttp multidict header-name subclasses and proved the transport
  projects them to exact strings before strict validation.
- Proved canonical slug and creation chronology remain allowlisted,
  deterministic candidate evidence.
- Revalidated discovery, candidate rehydration, protected surfaces, and
  no-growth limits.

## 2026-07-24 - OpenRouter endpoint-route single-call admission phase B2A

Scope: offline adversarial verification of externally supplied endpoint
observation, exact route evidence, and one-call evaluation eligibility.

- Binds exact raw bytes, request/response digests, payload/record IDs,
  observation freshness, model identity, and one unambiguous endpoint tag.
- Preserves nullable caps/status/quantization separately from omission and
  rejects malformed recognized values, duplicate keys, non-finite JSON,
  duplicate tags, prefix collisions, and oversized payloads.
- Rejects every unknown pricing key, including zero-valued forward additions;
  additive cost-schema drift is never dropped or inferred free.
- Restricts status projection to official values `0, -1, -2, -3, -5, -10`,
  retains known negative evidence, and requires a present value accepted by the
  trusted exact `(0,)` job policy.
- Rejects unknown caps, unsupported controls, mismatched identities/intents,
  stale/future evidence, requested ZDR, output training, unsafe cost
  dimensions, price-cap violations, and context/token overflow.
- Proves exact Decimal reconciliation and reservation, exact immutable POST
  route controls, response-byte binding, rehydration, and explicit HALTED
  reasons with `runtime_authority=eligibility_only`.
- Rejects reasoning-only and max-tokens-only weakened policies even when both
  evidence sources match the weakened subset. The policy and admission bind the
  exact emitted-control set independently.
- Proves the Chat Completions wire-control mapping has exactly `max_tokens`,
  `reasoning`, and `provider`, excludes internal `max_completion_tokens`, and
  retains the same value in the separate admission/budget field.
- Rejects explicit `supports_max_tokens=false`; proves omitted/unknown and true
  claims can proceed only with exact endpoint/model `max_tokens` evidence.
- Preserves present versus absent request pricing, binds the named PublicPricing
  optional-request absence-as-zero policy and digest, and rejects recomputed-ID
  tampering of presence, proof, or digest.
- Binds `endpoint_status_policy_accepted` through policy/admission IDs and
  rehydration while proving that omitted, negative, forward-unknown, and
  policy-tampered status evidence fails closed. The proof is not availability.
- Enrolls all four production modules in protected-authority import, network
  purity, source-line, and WSP_62 AST function guards.

Initial amendment RED: `8 failed, 20 passed`; emitted-control/request-price
amendment RED: `9 failed, 25 passed`; integration wire-key RED: `2 failed, 34
passed`. Post-rebase focused endpoint/admission: `65 passed`; combined protected
catalog/execution-control: `134 passed`; full AI Gateway: `712 passed, 2
skipped`. Ruff and WSP_97 v1.1 validation passed. All fixtures and transports
were offline; no provider, model, network, or credential call occurred.

## 2026-07-24 - OpenRouter model execution-control evidence phase B1

Scope: offline adversarial coverage of optional provider-control projection and
exact-model evidence lineage.

- Preserves current K3 price/context/reasoning assertions without hard-coding
  runtime behavior.
- Proves descending effort order, duplicate/enum/bool/token bounds,
  mandatory contradictions, and top-provider context/completion relationships.
- Proves partial assertions, explicit empty lists, null-versus-omitted effort,
  default-effort, and top-provider numeric claims, and omitted
  `supports_max_tokens` remain distinct.
- Drops unknown provider names, prose, secrets, defaults, and per-request limits
  before duplicate equality and evidence construction.
- Rehydrates legacy v1 candidates, rejects stale/future/tampered candidates,
  exact-ID aliases, evidence field tampering, and recomputed attacker IDs.
- Enrolls both new modules in persistent protected-authority import guards,
  AST network/runtime-dependency purity, explicit `<200`/`<400` source
  ceilings, and WSP_62 function ceilings.

Focused execution-control/catalog/protected result: `112 passed`. Full AI
Gateway: `647 passed, 2 skipped`. Ruff passed. No provider, model, network, or
credential call occurred.

## 2026-07-24 - Configured AutoResearch gateway safety contract v2

Scope: offline adversarial verification of configured provider calls, prompt
egress, exact cost/call bounds, durable receipts, and semantic verification.

- Exact route/budget/reasoning evidence rejects substitution and malformed or
  noncanonical values before provider entry.
- Canonical audit-only prompt guarding permits only byte-identical fully
  wrapped prompts and emits content-free failures.
- Twenty-way contention admits one bounded call. Panel failure/cancellation
  consumes the attempted role, releases the definitely unstarted suffix, and
  permits only the remaining capacity.
- ATTEMPTED-store failure releases its pre-call reservation; caller or terminal
  failure never reclaims an entered call. Terminal-store failure preserves the
  original cancellation/SystemExit/KeyboardInterrupt/BaseException.
- JSONL attempt/success readers rehydrate records, recompute IDs/cost totals,
  and reject tampered call routes.
- The semantic verifier binds output evidence to the durable v2 runner receipt
  rather than the obsolete v1 reconstructed digest shape.

Corrective coverage additionally proves exact-one-call campaign admission,
campaign-wide total-call preflight, canonical cost/cap inputs, route-alias
rejection, read/write and write/write artifact separation, stale-target
rejection, falsey injected gateway preservation, final wrapped-prompt bounds,
durable evidence ordering and fsync, conservative truth flags, and exact
WSP_62 ceilings.

Focused corrective result: `88 passed`; targeted root-main environment
threading: `1 passed`. Full AI Gateway: `587 passed, 2 skipped` (platform
capabilities only). All callers/transports were injected; no provider or
network call was made. Sampling controls and provider endpoint evidence are not
catalog-bound yet, so no live K3-vs-GLM comparative ranking was attempted.

## 2026-07-24 - Idle OpenRouter schedule adapter

Scope: offline adversarial validation of the exact daily claim-to-guard bridge.

- Proves canonical claim/invocation mapping and exact six-key output.
- Proves default-independent injected transport with no live network.
- Proves fixed local status/reason codes do not expose guard or exception text.
- Proves receipt and candidate `.to_dict()` evidence is canonically rehydrated
  before lineage/output.
- Rejects forged, malformed, matching 10,000-character, recursive, and
  nonterminal evidence with bounded content-free results.
- Preserves `CancelledError` and enforces no direct discovery, catalog bridge,
  selection, promotion, registry, or runtime-binding escape hatch.

Focused cross-module result: `174 passed, 1 skipped`. Combined AI Gateway +
IdleAutomation + runtime-artifact-safety result: `575 passed, 3 skipped`.

## 2026-07-24 - Scheduled provider discovery replay guard

Scope: offline-only adversarial verification of scheduled replay admission
around the unchanged direct OpenRouter discovery boundary.

- Concurrent same-loop callers and two subprocesses permit one transport call.
- `ARMED`, indeterminate, malformed, deep-nested, capacity-exhausted, linked,
  missing-candidate, and candidate-only states fail closed.
- Pre-ledger exact terminal evidence can migrate; exact blocked evidence cannot
  retry. Every missing ledger ID must prove fixed evidence strictly predates the
  new scheduled window, while guard-owned blocked entries remain retryable.
- Ledger `updated_at_ms` is enforced as a high-water mark so expiry pruning
  followed by wall-clock rollback cannot reopen transport admission.
- Event-driven cancellation cases prove that a cancelled active caller and a
  cancelled lock waiter leave their worker threads governed by the same outer
  lock, complete without deadlock, and never duplicate transport.
- Terminal ledger-write failure preserves the exact prior `ARMED` bytes and
  recovers only from the exact same-invocation terminal attempt.
- A valid candidate artifact larger than 1 MiB replays under the conservative
  bound derived from the direct 8 MiB response limit.
- Protected AST/file/function gates enforce no scheduler, startup, selection,
  promotion, registry, runtime-binding, or manual-surface authority expansion.

Focused scheduled/replay/protected result: `44 passed, 1 skipped` (unavailable
unprivileged Windows symlink creation only). Full ai_gateway: `378 passed, 2
skipped`. Idle automation: `126 passed`. Runtime artifact safety: `11 passed, 1
skipped`. Ruff, compileall, and diff-check passed.

## 2026-07-24 - Provider discovery defensive reliability hotfix

Scope: offline-only regressions for redirect-history receipt coherence,
retained-handle publication, rollback, and pathname integrity.

- `test_redirected_200_emits_truthful_terminal_receipt_and_preserves_lkg`
  requires a canonical `FAILED/redirect_history_rejected` receipt, exact final
  HTTP status, rehydration, and unchanged last-known-good candidate.
- `test_precommit_path_attack_never_publishes_substituted_bytes` covers
  pathname replacement, hard-link creation, and file-symlink substitution.
  Unsupported unprivileged Windows symlink creation is reported as one
  platform skip; ambiguous foreign substitutes are preserved, never unlinked.
- Post-validation and Windows final-check substitution cases prove that no
  substituted bytes become the candidate; Windows publishes the exact verified
  handle object. Wrong-publication and held-target failures restore exact prior
  bytes/mode or absence and clean only identity-owned temporary files.
- Receipt-unit cases require redirect-history evidence with a non-3xx final
  status and keep raw 3xx evidence bound to `redirect_rejected`.
- WSP 62 AST enforcement remains green for every touched production function.

Hotfix focused gate (the five provider/catalog files): `98 passed, 1 skipped`.
Full `modules/ai_intelligence/ai_gateway/tests`: `339 passed, 1 skipped`.

## 2026-07-23 - Direct provider catalog durability and WSP62 repair

Scope: offline-only verification for the bounded OpenRouter catalog discovery
slice. No test invokes a live provider, scheduler, runtime binding, or network
transport.

### Focused test files

| Test file | Cases | Scope |
|---|---:|---|
| `test_model_provider_catalog_snapshot.py` | 40 | Strict invocation, receipt, candidate, sanitization, freshness, and fail-closed evidence contracts |
| `test_model_openrouter_direct_discovery.py` | 27 | Manual/scheduled admission, bounded transport outcomes, durable receipt transitions, and candidate ordering |
| `test_model_provider_catalog_artifact_store.py` | 5 | Partial write, fsync, replace, cleanup, exact UTF-8, and permission-preserving atomic replacement |
| `test_model_provider_catalog_protected_surfaces.py` | 5 | Authority isolation, file ceilings, and AST-based 50-line production function ceiling |

Focused result: `77 passed`.

Supporting compatibility coverage:

- `test_model_intelligence_catalog.py`: `8 passed`, including OpenRouter
  normalization behavior preserved after cohesive single-record extraction.
- Combined provider-catalog and catalog-normalization focus: `85 passed`.
- Full `modules/ai_intelligence/ai_gateway/tests`: `326 passed`.

The counts above include the WSP62 AST regression added in this repair. The
artifact-store file is also run independently as the five-case atomic failure
matrix.
