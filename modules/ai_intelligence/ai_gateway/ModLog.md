# AI Gateway Module Change Log

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

## [2026-07-17] - Model AutoResearch Cycle Feedback Chain Main Preflight

**Who:** 0102 Codex
**Type:** Runtime Startup Wiring
**Slice:** MODEL_AUTORESEARCH_CYCLE_FEEDBACK_CHAIN_MAIN_PREFLIGHT_PHASE1

**What:** Exposed the model AutoResearch cycle feedback chain through the
main resident preflight as `REDDOG_MODEL_AUTORESEARCH_CYCLE_FEEDBACK_CHAIN`.

**Why:** The chain bootstrap must be reachable from startup without requiring
operators to manually enable three separate post-execution artifact steps.

**Files:**
- `main.py` - adds disabled-by-default chain flag, enforced mode, startup
  logging, and environment path propagation.
- `modules/communication/moltbot_bridge/tests/test_reddog_main_architect_fix_promotion_bootstrap.py`
  - covers successful chain execution before promotion and enforced startup
  failure.

**Truth Boundary:**
- IMPLEMENTED: explicit startup wiring for the already-merged post-execution
  AutoResearch chain.
- NOT IMPLEMENTED: direct provider calls, benchmark execution, model
  promotion, catalog mutation, PatternMemory writes, HoloIndex re-indexing,
  runtime model binding, worker spawn, shell execution, source mutation, or
  extension mutation.

**WSP References:** WSP 15, WSP 22, WSP 50, WSP 97.

---

## [2026-07-17] - Model AutoResearch Cycle Feedback Chain Bootstrap

**Who:** 0102 Codex
**Type:** Runtime Evidence Chain
**Slice:** MODEL_AUTORESEARCH_CYCLE_FEEDBACK_CHAIN_BOOTSTRAP_PHASE1

**What:** Added an outside-repo bootstrap that chains existing model
AutoResearch artifacts from campaign execution through promotion-gate supply,
cycle receipt creation, and cycle feedback ledger admission.

**Why:** The model AutoResearch loop now has content-bearing semantic
verification, promotion-gate supply, and feedback admission primitives. This
slice proves they can be composed as one configured runtime chain without
manual artifact stitching.

**Files:**
- `src/model_autoresearch_cycle_feedback_chain_bootstrap.py` - orchestrates
  promotion-gate supply, cycle receipt supply, and feedback ledger admission
  from outside-repo runtime artifacts.
- `tests/test_model_autoresearch_cycle_feedback_chain_bootstrap.py` - covers
  semantic-accepted and semantic-rejected configured gateway campaigns,
  inside-repo path rejection, malformed policy rejection, duplicate output
  path rejection, and AST authority boundaries.

**Truth Boundary:**
- IMPLEMENTED: one configured post-execution chain from semantic campaign
  output to feedback ledger admission.
- NOT IMPLEMENTED: direct provider calls, benchmark execution, model
  promotion, catalog mutation, PatternMemory writes, HoloIndex re-indexing,
  runtime model binding, worker spawn, shell execution, source mutation, or
  extension mutation.

**WSP References:** WSP 15, WSP 22, WSP 50, WSP 97.

---

## [2026-07-17] - Semantic Verifier Promotion Chain Regression

**Who:** 0102 Codex
**Type:** Runtime Chain Regression
**Slice:** MODEL_AUTORESEARCH_SEMANTIC_PROMOTION_CHAIN_REGRESSION_PHASE1

**What:** Added promotion-gate supply regression coverage proving a configured
gateway campaign verified by `output_evidence_semantic` can feed promotion-gate
receipts, and that semantically rejected samples cannot promote.

**Why:** The evidence bundle and semantic verifier are useful only if their
accepted/rejected benchmark receipts are honored by the downstream
champion/challenger gate.

**Files:**
- `tests/test_model_autoresearch_campaign_promotion_gate_supply.py` - adds the
  configured-gateway semantic campaign -> promotion-gate acceptance and
  rejection regressions.

**Truth Boundary:**
- IMPLEMENTED: regression proof for semantic verifier evidence flowing into
  promotion-gate supply.
- NOT IMPLEMENTED: free-form LLM verifier, model catalog mutation, runtime
  model binding, PatternMemory writes, HoloIndex re-indexing, worker spawn,
  shell execution, source mutation, or extension mutation.

**WSP References:** WSP 15, WSP 22, WSP 50, WSP 97.

---

## [2026-07-17] - Model AutoResearch Output Evidence Semantic Verifier

**Who:** 0102 Codex
**Type:** Runtime Benchmark Verifier
**Slice:** MODEL_AUTORESEARCH_CONFIGURED_GATEWAY_SEMANTIC_VERIFIER_PHASE1

**What:** Added a deterministic verifier over configured-gateway output
evidence records and exposed it through the campaign execution bootstrap as
`output_evidence_semantic` verifier mode.

**Why:** The benchmark path can now preserve raw model output, but promotion
still needs a verifier that checks actual content rather than output digest
shape alone.

**Files:**
- `src/model_autoresearch_semantic_verifier.py` - rehydrates output evidence,
  recomputes configured-runner output/receipt digests, and checks task-declared
  required/forbidden answer terms.
- `src/model_autoresearch_campaign_execution_artifact_supply_bootstrap.py` -
  adds `output_evidence_semantic` as an explicit configured-gateway verifier
  mode.
- `tests/test_model_autoresearch_semantic_verifier.py` and bootstrap tests -
  acceptance, missing evidence, missing requirements, forbidden term, digest
  mismatch, panel-role evidence, and startup coverage.

**Truth Boundary:**
- IMPLEMENTED: deterministic output-evidence verifier for task-declared
  semantic requirements.
- NOT IMPLEMENTED: free-form LLM verifier, model promotion, PatternMemory
  writes, HoloIndex re-indexing, runtime model binding, worker spawn, shell
  execution, source mutation, or extension mutation.

**WSP References:** WSP 15, WSP 22, WSP 50, WSP 97.

---

## [2026-07-17] - Model AutoResearch Output Evidence Bundle

**Who:** 0102 Codex
**Type:** Runtime Benchmark Evidence
**Slice:** MODEL_AUTORESEARCH_OUTPUT_EVIDENCE_BUNDLE_PHASE1

**What:** Added content-bearing output evidence records for configured gateway
AutoResearch benchmark calls and required an outside-repo JSONL evidence path
when resident startup uses `configured_gateway` mode.

**Why:** The configured runner returned only output digests. An independent
semantic verifier cannot inspect or cite a model answer if raw output is not
preserved as governed evidence.

**Files:**
- `src/model_autoresearch_output_evidence_bundle.py` - digest-bound output
  evidence records, rehydration, secret scan, and outside-repo JSONL store.
- `src/model_autoresearch_configured_gateway_runner.py` - optional evidence
  store injection and evidence-record ID binding into runner receipts.
- `src/model_autoresearch_campaign_execution_artifact_supply_bootstrap.py` -
  configured-mode output evidence path requirement.
- `tests/test_model_autoresearch_output_evidence_bundle.py` and adjacent tests
  - tamper rejection, secret rejection, outside-repo guard, configured runner,
  bootstrap, and `main.py` pass-through coverage.

**Truth Boundary:**
- IMPLEMENTED: content-bearing benchmark output evidence, digest rehydration,
  outside-repo persistence, and configured startup evidence-path enforcement.
- NOT IMPLEMENTED: semantic answer verification, model promotion, PatternMemory
  writes, HoloIndex re-indexing, runtime model binding, worker spawn, shell
  execution, source mutation, or extension mutation.

**WSP References:** WSP 15, WSP 22, WSP 50, WSP 97.

---

## [2026-07-17] - Model AutoResearch Configured Gateway Runner

**Who:** 0102 Codex
**Type:** Runtime Benchmark Runner Seam
**Slice:** MODEL_AUTORESEARCH_CONFIGURED_GATEWAY_RUNNER_PHASE1

**What:** Added a configured gateway benchmark runner adapter that verifies
held-out prompt digests before provider calls and targets candidate
provider/model role assignments through an injected gateway seam.

**Why:** The AutoResearch campaign executor could run only deterministic
fixtures. RedDog needs a real, governed benchmark-call seam before the model
improvement loop can measure current providers and fusion panels.

**Files:**
- `src/model_autoresearch_configured_gateway_runner.py` - configured caller,
  prompt-source, policy, and benchmark-runner adapter.
- `tests/test_model_autoresearch_configured_gateway_runner.py` - verifies
  digest-bound prompts, explicit provider/model routing, panel role calls,
  cost/provider fail-closed paths, and AST no-network/no-command boundaries.

**Truth Boundary:**
- IMPLEMENTED: reusable configured gateway runner seam for benchmark campaigns.
- NOT IMPLEMENTED: startup auto-enable, independent verifier runtime, model
  promotion, PatternMemory writes, HoloIndex re-indexing, RedDog runtime model
  binding, worker spawn, shell execution, source mutation, or extension
  mutation.

**WSP References:** WSP 15, WSP 22, WSP 50, WSP 97.

---

## [2026-07-17] - Model AutoResearch Configured Gateway Bootstrap

**Who:** 0102 Codex
**Type:** Runtime Benchmark Bootstrap
**Slice:** MODEL_AUTORESEARCH_CONFIGURED_GATEWAY_BOOTSTRAP_PHASE1

**What:** Extended campaign execution artifact supply so resident startup can
explicitly select `configured_gateway` runner mode with outside-repo prompt
records, provider allowlist, bounded runner policy, and
`exact_output_digest` verifier mode.

**Why:** The configured runner was reusable but not reachable from the startup
artifact supply path. RedDog needs an opt-in benchmark execution path that can
call configured models without weakening the default fixture mode.

**Files:**
- `src/model_autoresearch_campaign_execution_artifact_supply_bootstrap.py` -
  configured runner mode, prompt-record loading, exact-output verifier, and
  fail-closed policy parsing.
- `tests/test_model_autoresearch_campaign_execution_artifact_supply_bootstrap.py`
  - configured-mode receipt materialization and prompt-record rejection tests.
- `main.py` and `test_reddog_main_architect_fix_promotion_bootstrap.py` -
  environment pass-through for configured runner controls.

**Truth Boundary:**
- IMPLEMENTED: explicit opt-in configured gateway benchmark execution bootstrap.
- NOT IMPLEMENTED: open-ended semantic verifier, model promotion, PatternMemory
  writes, HoloIndex re-indexing, runtime model binding, worker spawn, shell
  execution, source mutation, or extension mutation.

**WSP References:** WSP 15, WSP 22, WSP 50, WSP 97.

---

## [2026-07-17] - Model AutoResearch Cycle Feedback Plan Supply Regression

**Who:** 0102 Codex
**Type:** Runtime Supply Regression
**Slice:** REDDOG_MODEL_AUTORESEARCH_CYCLE_FEEDBACK_PLAN_SUPPLY_REGRESSION_PHASE1

**What:** Added direct supplier and startup-bootstrap regression coverage proving
context-bound cycle feedback JSONL records flow into AutoResearch plan
artifact supply.

**Why:** The planner can consume cycle feedback and the bootstrap can read JSONL
feedback, but the runtime boundary needed an explicit proof that cycle feedback
from the feedback ledger can influence the next benchmark plan.

**Files:**
- `tests/test_model_autoresearch_plan_artifact_supply.py` - verifies direct
  supplier priority from cycle feedback.
- `tests/test_model_autoresearch_plan_artifact_supply_bootstrap.py` - verifies
  startup JSONL feedback supply with the cycle feedback shape.

**Truth Boundary:**
- IMPLEMENTED: regression proof that context-bound cycle feedback reaches
  AutoResearch plan supply through direct and bootstrap paths.
- NOT IMPLEMENTED: provider calls, benchmark execution, model promotion,
  PatternMemory writes, HoloIndex re-indexing, runtime binding, worker spawn,
  shell execution, source mutation, or extension mutation.

**WSP References:** WSP 15, WSP 22, WSP 50, WSP 97.

---

## [2026-07-17] - Model AutoResearch Cycle Feedback Planner Input

**Who:** 0102 Codex
**Type:** Planner Feedback Integration
**Slice:** MODEL_AUTORESEARCH_CYCLE_FEEDBACK_PLANNER_INPUT_PHASE1

**What:** Extended the model champion/challenger AutoResearch planner to accept
context-bound `model_autoresearch_cycle_feedback_record.v1` records as bounded
feedback input.

**Why:** Completed AutoResearch cycles now need to influence the next
benchmark plan without trusting unbound ledger records or changing runtime
model bindings.

**Files:**
- `src/model_champion_challenger_autoresearch.py` - normalizes cycle feedback
  only when source-plan context, task family, catalog snapshot, source-plan
  digest, executed candidates, and promotion-gate receipts are present.
- `tests/test_model_champion_challenger_autoresearch.py` - verifies bounded
  priority influence plus fail-closed rejection for unbound, mismatched, and
  incomplete cycle feedback records.

**Truth Boundary:**
- IMPLEMENTED: planner consumption of context-bound cycle feedback as a
  priority signal for existing candidates.
- NOT IMPLEMENTED: provider calls, benchmark execution, model promotion,
  PatternMemory writes, HoloIndex re-indexing, runtime binding, worker spawn,
  shell execution, source mutation, or extension mutation.

**WSP References:** WSP 15, WSP 22, WSP 50, WSP 97.

---

## [2026-07-17] - Model AutoResearch Cycle Feedback Context Binding

**Who:** 0102 Codex
**Type:** Feedback Ledger Hardening
**Slice:** MODEL_AUTORESEARCH_CYCLE_FEEDBACK_CONTEXT_BINDING_PHASE1

**What:** Hardened AutoResearch cycle feedback admission so a supplied source
plan receipt is rehydrated, matched to the cycle receipt, and bound into the
feedback record.

**Why:** Cycle feedback records need task-family and catalog-snapshot context
before any later planner-consumption slice can safely use them as recursive
model-improvement input.

**Files:**
- `src/model_autoresearch_cycle_feedback_ledger.py` - accepts optional source
  plan receipts, rejects tampered/mismatched plans, and records bound plan
  context.
- `src/model_autoresearch_cycle_feedback_ledger_admission_bootstrap.py` -
  requires the outside-repo plan receipt path and passes it into admission.
- Tests updated for context-bound records, plan tamper rejection, and main
  preflight argument binding.

**Truth Boundary:**
- IMPLEMENTED: context-bound cycle feedback records.
- NOT IMPLEMENTED: planner consumption of cycle feedback records, provider
  calls, benchmark execution, model promotion, PatternMemory writes, HoloIndex
  re-indexing, runtime binding, worker spawn, shell execution, source mutation,
  or extension mutation.

**WSP References:** WSP 15, WSP 22, WSP 50, WSP 97.

---

## [2026-07-17] - Model AutoResearch Cycle Feedback Ledger Admission Bootstrap

**Who:** 0102 Codex
**Type:** Runtime Preflight Adapter
**Slice:** REDDOG_MODEL_AUTORESEARCH_CYCLE_FEEDBACK_LEDGER_ADMISSION_MAIN_PREFLIGHT_PHASE1

**What:** Added a disabled-by-default bootstrap for admitting an outside-repo
model AutoResearch cycle receipt into an outside-repo cycle feedback ledger.

**Why:** The model AutoResearch loop can now persist completed cycle evidence
as durable feedback input without changing runtime model bindings or promoting
models.

**Files:**
- `src/model_autoresearch_cycle_feedback_ledger_admission_bootstrap.py` - reads
  an outside-repo cycle receipt, invokes the cycle feedback admission guard, and
  appends to an outside-repo JSONL ledger.
- `tests/test_model_autoresearch_cycle_feedback_ledger_admission_bootstrap.py`
  - verifies successful append, inside-repo path rejection, tamper rejection,
  missing output rejection, and AST import/call denylist controls.

**Truth Boundary:**
- IMPLEMENTED: opt-in AutoResearch cycle feedback ledger admission from an
  outside-repo cycle receipt.
- NOT IMPLEMENTED: provider calls, benchmark execution, model promotion,
  PatternMemory writes, HoloIndex re-indexing, runtime binding, queue-stage
  wiring, worker spawn, shell execution, source mutation, or extension mutation.

**WSP References:** WSP 15, WSP 22, WSP 50, WSP 97.

---

## [2026-07-17] - Model AutoResearch Cycle Feedback Ledger Admission

**Who:** 0102 Codex
**Type:** Feedback Ledger Admission
**Slice:** MODEL_AUTORESEARCH_CYCLE_FEEDBACK_LEDGER_ADMISSION_PHASE1

**What:** Added an explicit-invoke admission guard for verified model
AutoResearch cycle receipts.

**Why:** The recursive model-improvement loop needs to retain completed
AutoResearch cycles as durable learning input without promoting models or
changing runtime bindings.

**Files:**
- `src/model_autoresearch_cycle_feedback_ledger.py` - rehydrates cycle
  receipts, builds minimal cycle feedback records, writes through an injected
  store, and emits a digest-bound admission receipt.
- `tests/test_model_autoresearch_cycle_feedback_ledger.py` - verifies admission,
  JSONL output, explicit invoke/store requirements, tamper rejection,
  eligibility checks, secret-marker rejection, store-failure handling, JSON
  serialization, and AST import/call denylist controls.

**Truth Boundary:**
- IMPLEMENTED: explicit-invoke AutoResearch cycle feedback ledger admission.
- NOT IMPLEMENTED: provider calls, benchmark execution, model promotion,
  PatternMemory writes, HoloIndex re-indexing, runtime binding, queue-stage
  wiring, worker spawn, shell execution, source mutation, or extension mutation.

**WSP References:** WSP 15, WSP 22, WSP 50, WSP 97.

---

## [2026-07-17] - Model AutoResearch Cycle Receipt Supply Bootstrap

**Who:** 0102 Codex
**Type:** Runtime Preflight Adapter
**Slice:** REDDOG_MODEL_AUTORESEARCH_CYCLE_RECEIPT_SUPPLY_MAIN_PREFLIGHT_PHASE1

**What:** Added a disabled-by-default bootstrap for materializing a model
AutoResearch cycle receipt from outside-repo plan, campaign execution, and
promotion-gate supply artifacts.

**Why:** The resident startup loop can now carry one digest-bound evidence
object proving that the plan, execution, and gate supply belong to the same
AutoResearch cycle before later feedback or planning stages consume it.

**Files:**
- `src/model_autoresearch_cycle_receipt_supply_bootstrap.py` - reads
  outside-repo artifacts, invokes the cycle receipt builder, and writes the
  cycle receipt outside the repository.
- `tests/test_model_autoresearch_cycle_receipt_supply_bootstrap.py` - verifies
  successful materialization, inside-repo path rejection, tamper rejection,
  malformed execution rejection, and AST import/call denylist controls.

**Truth Boundary:**
- IMPLEMENTED: opt-in AutoResearch cycle receipt artifact supply from
  outside-repo receipts.
- NOT IMPLEMENTED: provider calls, benchmark execution, model promotion,
  PatternMemory writes, HoloIndex re-indexing, runtime binding, worker spawn,
  shell execution, source mutation, or extension mutation.

**WSP References:** WSP 15, WSP 22, WSP 50, WSP 97.

---

## [2026-07-17] - Model AutoResearch Cycle Receipt

**Who:** 0102 Codex
**Type:** Receipt Integrity
**Slice:** MODEL_AUTORESEARCH_CYCLE_RECEIPT_PHASE1

**What:** Added a digest-bound cycle receipt that binds one AutoResearch plan,
campaign execution, and promotion-gate supply artifact.

**Why:** Recursive model improvement needs a single evidence object proving
which plan was executed and which promotion-gate receipts resulted before a
later queue stage or feedback ledger consumes the cycle output.

**Files:**
- `src/model_autoresearch_cycle_receipt.py` - rehydrates and binds plan,
  execution, and gate-supply receipts; rejects plan/execution, execution/gate,
  and candidate coverage mismatches; supports rehydration of the cycle receipt.
- `tests/test_model_autoresearch_cycle_receipt.py` - verifies successful
  binding, each mismatch rejection, receipt tamper rejection, and AST
  import/call denylist controls.

**Truth Boundary:**
- IMPLEMENTED: receipt-bound proof for plan -> execution -> promotion-gate
  supply continuity.
- NOT IMPLEMENTED: provider calls, benchmark execution, model promotion,
  PatternMemory writes, HoloIndex re-indexing, runtime binding, worker spawn,
  shell execution, file output, or main.py preflight wiring.

**WSP References:** WSP 15, WSP 22, WSP 50, WSP 97.

---

## [2026-07-17] - Model AutoResearch Campaign Promotion Gate Supply Bootstrap

**Who:** 0102 Codex
**Type:** Runtime Preflight Adapter
**Slice:** REDDOG_MODEL_AUTORESEARCH_CAMPAIGN_PROMOTION_GATE_SUPPLY_MAIN_PREFLIGHT_PHASE1

**What:** Added a disabled-by-default bootstrap for materializing promotion-gate
receipts from outside-repo AutoResearch campaign execution and promotion-policy
artifacts.

**Why:** The campaign execution bridge can now produce promotion-gate receipts,
but resident startup needs an explicit, outside-repo artifact pathway to persist
those receipts for the next planning cycle.

**Files:**
- `src/model_autoresearch_campaign_promotion_gate_supply_bootstrap.py` - reads
  outside-repo campaign execution and promotion policy JSON, invokes the
  promotion-gate supply bridge, and writes an outside-repo gate supply receipt.
- `tests/test_model_autoresearch_campaign_promotion_gate_supply_bootstrap.py`
  - verifies successful materialization, inside-repo path rejection, malformed
  policy rejection, candidate mismatch rejection, and AST import/call denylist
  controls.

**Truth Boundary:**
- IMPLEMENTED: opt-in campaign promotion-gate artifact supply from outside-repo
  receipts and policies.
- NOT IMPLEMENTED: provider calls, benchmark execution, model promotion,
  PatternMemory writes, HoloIndex re-indexing, runtime binding, worker spawn,
  shell execution, or extension mutation.

**WSP References:** WSP 15, WSP 22, WSP 50, WSP 97.

---

## [2026-07-17] - Model AutoResearch Campaign Promotion Gate Supply

**Who:** 0102 Codex
**Type:** Feedback Loop Bridge
**Slice:** MODEL_AUTORESEARCH_CAMPAIGN_PROMOTION_GATE_SUPPLY_PHASE1

**What:** Added a bridge that turns a verified
`ModelAutoResearchCampaignExecutionReceipt` into promotion-gate receipts for the
next AutoResearch planning cycle.

**Why:** Campaign execution receipts contain measured benchmark evidence, but
the planner consumes promotion-gate receipts. This slice closes that internal
evidence loop without promoting models or mutating runtime defaults.

**Files:**
- `src/model_autoresearch_campaign_promotion_gate_supply.py` - rehydrates the
  campaign execution receipt, requires exact candidate-policy coverage,
  evaluates existing promotion gates, writes an outside-repo supply receipt, and
  supports rehydration of the supply artifact.
- `tests/test_model_autoresearch_campaign_promotion_gate_supply.py` - verifies
  successful gate supply, no-authority no-promotion behavior, policy mismatch
  rejection, execution tamper rejection, output path rejection, rehydration
  tamper rejection, and AST import/call denylist controls.

**Truth Boundary:**
- IMPLEMENTED: receipt-bound promotion-gate supply from verified AutoResearch
  campaign execution output.
- NOT IMPLEMENTED: provider calls, benchmark execution, model promotion,
  PatternMemory writes, HoloIndex re-indexing, runtime binding, worker spawn,
  shell execution, or main.py preflight wiring.

**WSP References:** WSP 15, WSP 22, WSP 50, WSP 97.

---

## [2026-07-17] - Model AutoResearch Campaign Execution Artifact Supply Bootstrap

**Who:** 0102 Codex
**Type:** Runtime Preflight Adapter
**Slice:** REDDOG_MODEL_AUTORESEARCH_CAMPAIGN_EXECUTION_ARTIFACT_SUPPLY_MAIN_PREFLIGHT_PHASE1

**What:** Added a disabled-by-default bootstrap for materializing
`ModelAutoResearchCampaignExecutionReceipt` artifacts from outside-repo runtime
inputs.

**Why:** The model AutoResearch lane needs a governed way to advance from a
verified campaign plan to a receipt-bearing benchmark execution artifact before
any promotion, runtime model binding, or PatternMemory feedback can trust it.

**Files:**
- `src/model_autoresearch_campaign_execution_artifact_supply_bootstrap.py` -
  reads outside-repo plan, candidate pool, and held-out task JSON; runs the
  bounded campaign executor with deterministic fixture seams; writes only an
  outside-repo execution receipt.
- `tests/test_model_autoresearch_campaign_execution_artifact_supply_bootstrap.py`
  - verifies successful receipt materialization, rehydration, fail-closed path
  handling, verifier mismatch rejection, unsupported mode rejection, and AST
  import/call denylist controls.

**Truth Boundary:**
- IMPLEMENTED: opt-in campaign execution artifact supply using deterministic
  fixture runner/verifier seams and outside-repo receipt output.
- NOT IMPLEMENTED: provider calls, network research, model promotion,
  PatternMemory writes, HoloIndex re-indexing, runtime model binding, worker
  spawn, shell execution, or extension mutation.

**WSP References:** WSP 15, WSP 22, WSP 50, WSP 97.

---

## [2026-07-17] - Model AutoResearch Campaign Execution Receipt Rehydration

**Who:** 0102 Codex
**Type:** Receipt Integrity
**Slice:** MODEL_AUTORESEARCH_CAMPAIGN_EXECUTION_RECEIPT_REHYDRATION_PHASE1

**What:** Added rehydration for serialized
`ModelAutoResearchCampaignExecutionReceipt` artifacts.

**Why:** Campaign execution now emits a benchmark-run-bearing artifact. Future
promotion, runtime binding, or feedback ratchet consumers must verify the
campaign receipt and its embedded benchmark run before trusting the execution
result.

**Files:**
- `src/model_autoresearch_campaign_execution.py` - adds campaign execution
  receipt rehydration, shared canonical execution digest body, embedded
  benchmark-run rehydration, candidate consistency checks, and constant-time
  receipt ID comparison.
- `tests/test_model_autoresearch_campaign_execution.py` - verifies round-trip
  rehydration, digest-bound tamper rejection, embedded benchmark tamper
  rejection, and malformed shape rejection.

**Truth Boundary:**
- IMPLEMENTED: serialized campaign execution receipts can be accepted only
  after schema, digest, embedded benchmark, and candidate consistency checks.
- NOT IMPLEMENTED: model promotion, runtime binding, PatternMemory writes,
  HoloIndex re-indexing, provider calls, or automatic resident campaign
  execution.

**WSP References:** WSP 15, WSP 22, WSP 50, WSP 97.

---

## [2026-07-17] - Model Benchmark Run Receipt Rehydration

**Who:** 0102 Codex
**Type:** Receipt Integrity
**Slice:** MODEL_COMBINATION_BENCHMARK_RUN_RECEIPT_REHYDRATION_PHASE1

**What:** Added rehydration for serialized
`ModelCombinationBenchmarkRunReceipt` records.

**Why:** AutoResearch campaign execution now emits benchmark run receipts. Any
later promotion or campaign-execution receipt consumer must be able to verify
the benchmark run body, embedded evidence receipts, sample counts, accepted
counts, task-set binding, held-out split, verifier digest, and candidate
topology before trusting a serialized artifact.

**Files:**
- `src/model_combination_benchmark_harness.py` - adds benchmark run
  rehydration, shared canonical digest body, candidate/sample/evidence
  consistency checks, and constant-time receipt ID comparison.
- `tests/test_model_combination_benchmark_harness.py` - verifies valid
  round-trip rehydration, tamper rejection, evidence-count mismatch rejection,
  and malformed shape rejection.

**Truth Boundary:**
- IMPLEMENTED: serialized benchmark run receipts can be accepted only after
  schema, digest, candidate, sample, and evidence consistency checks.
- NOT IMPLEMENTED: provider calls, benchmark campaign scheduling,
  AutoResearch promotion, PatternMemory writes, HoloIndex re-indexing, or
  resident runtime execution.

**WSP References:** WSP 15, WSP 22, WSP 50, WSP 97.

---

## [2026-07-17] - Model AutoResearch Campaign Execution

**Who:** 0102 Codex
**Type:** Bounded Benchmark Execution
**Slice:** MODEL_AUTORESEARCH_CAMPAIGN_EXECUTION_PHASE1

**What:** Added a bounded AutoResearch campaign executor that consumes a
rehydrated `ModelAutoResearchPlanReceipt`, validates candidate-pool digest and
verifier requirements, and runs selected candidates through injected benchmark
runner/verifier seams.

**Why:** The resident model-intelligence lane can now plan benchmark campaigns,
but future recursive improvement needs a verified execution receipt before any
promotion or PatternMemory step. This layer produces that receipt without
direct provider imports or runtime binding.

**Files:**
- `src/model_autoresearch_campaign_execution.py` - validates plans,
  candidates, held-out tasks, verifier digests, and outside-repo output before
  running the existing benchmark harness.
- `tests/test_model_autoresearch_campaign_execution.py` - verifies successful
  execution, tampered plan rejection, candidate-pool mismatch rejection,
  verifier mismatch rejection, STOP/no-op rejection, inside-repo output denial,
  and no provider/network/runtime imports.

**Truth Boundary:**
- IMPLEMENTED: verified AutoResearch plans can produce digest-bound campaign
  execution receipts through injected runner/verifier seams.
- IMPLEMENTED: serialized plans, candidate topology, candidate-pool digest,
  task set, verifier digest, and output path are fail-closed before execution.
- NOT IMPLEMENTED: live provider calls, model promotion, catalog mutation,
  PatternMemory writes, HoloIndex re-indexing, RedDog runtime binding, or
  automatic resident campaign execution.

**WSP References:** WSP 15, WSP 22, WSP 50, WSP 97.

---

## [2026-07-17] - Model AutoResearch Plan Receipt Rehydration

**Who:** 0102 Codex
**Type:** Receipt Integrity
**Slice:** MODEL_AUTORESEARCH_PLAN_RECEIPT_REHYDRATION_PHASE1

**What:** Added rehydration helpers for serialized
`ModelAutoResearchPolicy` and `ModelAutoResearchPlanReceipt`.

**Why:** Future campaign execution must not trust a serialized AutoResearch
plan list. Before a runner consumes a plan artifact, the policy, source
receipts, candidate-pool digest, feedback digest, campaign items, and rejection
reasons must be recomputed against the original deterministic receipt ID.

**Files:**
- `src/model_champion_challenger_autoresearch.py` - adds policy and plan
  rehydration, shared canonical digest body, and constant-time receipt ID
  comparison.
- `tests/test_model_champion_challenger_autoresearch.py` - verifies valid
  round-trip rehydration, digest-bound tamper rejection, and malformed campaign
  shape rejection.

**Truth Boundary:**
- IMPLEMENTED: serialized AutoResearch plan receipts can be accepted only after
  schema and digest rehydration.
- IMPLEMENTED: policy, source-gate IDs, feedback IDs, pool digest, feedback
  digest, campaign items, verifier flags, and rejection reasons are covered.
- NOT IMPLEMENTED: benchmark execution, provider calls, model promotion,
  PatternMemory writes, HoloIndex re-indexing, or resident campaign execution.

**WSP References:** WSP 15, WSP 22, WSP 50, WSP 97.

---

## [2026-07-17] - Model AutoResearch Plan Artifact Supply Bootstrap

**Who:** 0102 Codex
**Type:** Runtime Artifact Bootstrap
**Slice:** REDDOG_MODEL_AUTORESEARCH_PLAN_ARTIFACT_SUPPLY_MAIN_PREFLIGHT_PHASE1

**What:** Added an opt-in main-startup bootstrap for materializing a
`ModelAutoResearchPlanReceipt` from outside-repo promotion-gate receipts,
benchmark candidates, AutoResearch policy, and optional model-feedback records.

**Why:** The resident RedDog path can now produce verified model feedback and
promotion evidence, but future benchmark campaigns need a governed artifact
handoff before any AutoResearch execution slice runs. This bridges the landed
planner into preflight while preserving read-only, no-benchmark behavior.

**Files:**
- `src/model_autoresearch_plan_artifact_supply_bootstrap.py` - reads
  outside-repo JSON/JSONL inputs, invokes the landed plan supplier, and returns
  an explicit applied/not-ready bootstrap receipt.
- `tests/test_model_autoresearch_plan_artifact_supply_bootstrap.py` - verifies
  JSONL feedback, optional feedback omission, inside-repo rejection, tamper
  rejection, and no provider/network/runtime imports.
- `main.py` - adds the opt-in
  `REDDOG_MODEL_AUTORESEARCH_PLAN_ARTIFACT_SUPPLY` preflight hook.

**Truth Boundary:**
- IMPLEMENTED: configured outside-repo artifacts can materialize a
  digest-bound AutoResearch plan receipt during startup preflight.
- IMPLEMENTED: the hook is opt-in, fail-closed when enforced, and propagates
  only the output receipt path after successful supply.
- NOT IMPLEMENTED: benchmark execution, model promotion, runtime model binding,
  PatternMemory writes, HoloIndex re-indexing, provider calls, worker dispatch,
  or automatic resident campaign execution.

**WSP References:** WSP 15, WSP 22, WSP 50, WSP 97.

---

## [2026-07-17] - Model AutoResearch Plan Artifact Supply

**Who:** 0102 Codex
**Type:** Artifact Supply
**Slice:** MODEL_AUTORESEARCH_PLAN_ARTIFACT_SUPPLY_PHASE1

**What:** Added an artifact supplier that materializes a
`ModelAutoResearchPlanReceipt` from serialized promotion-gate receipts,
benchmark candidates, policy, and optional model-feedback records.

**Why:** Verified model feedback now reaches the AutoResearch planner, but the
resident runtime needs an outside-repo artifact seam before future benchmark
campaign execution can consume it. This supplier validates serialized evidence
and writes a single plan receipt without running benchmarks or mutating runtime
defaults.

**Files:**
- `src/model_autoresearch_plan_artifact_supply.py` - rehydrates promotion-gate
  receipts, validates candidate topology, consumes optional feedback records,
  and writes an outside-repo plan JSON atomically.
- `tests/test_model_autoresearch_plan_artifact_supply.py` - validates accepted
  supply, inside-repo output rejection, tampered gate/candidate rejection,
  malformed feedback rejection, and no provider/network/runtime imports.

**Truth Boundary:**
- IMPLEMENTED: serialized promotion-gate receipts and benchmark candidates can
  produce a digest-bound AutoResearch plan artifact.
- IMPLEMENTED: output is denied inside the repository and feedback records
  remain planner-only signals.
- NOT IMPLEMENTED: provider calls, benchmark execution, model promotion,
  catalog mutation, PatternMemory writes, HoloIndex re-indexing, runtime model
  default binding, or resident `main.py` preflight wiring.

**WSP References:** WSP 15, WSP 22, WSP 50, WSP 97.

---

## [2026-07-17] - Model Promotion Gate Receipt Rehydration

**Who:** 0102 Codex
**Type:** Receipt Integrity
**Slice:** MODEL_PROMOTION_GATE_RECEIPT_REHYDRATION_PHASE1

**What:** Added rehydration helpers for serialized model-promotion policies,
promotion evidence receipts, and promotion gate receipts.

**Why:** AutoResearch artifact supply must not trust raw serialized promotion
gate mappings. Before runtime planning can consume promotion gates from
outside-repo artifacts, the gate receipt ID and embedded promotion evidence must
be recomputed and checked.

**Files:**
- `src/model_promotion_gate.py` - rehydrates and recomputes promotion policy,
  promotion evidence, and gate receipts, including champion evidence checks.
- `tests/test_model_promotion_gate.py` - verifies champion/challenger
  round-trip and tampered/missing/mismatched evidence rejection.

**Truth Boundary:**
- IMPLEMENTED: serialized promotion gate receipts can be rehydrated with
  deterministic ID checks and embedded promotion-evidence consistency checks.
- IMPLEMENTED: champion gate receipts require promotion evidence; tampered
  receipt bodies and forged evidence reject before downstream planning.
- NOT IMPLEMENTED: provider calls, benchmark execution, model promotion,
  AutoResearch artifact supply, catalog mutation, PatternMemory writes, or
  HoloIndex re-indexing.

**WSP References:** WSP 15, WSP 22, WSP 50, WSP 97.

---

## [2026-07-17] - Model Feedback Ledger AutoResearch Signal

**Who:** 0102 Codex
**Type:** Recursive Learning Signal
**Slice:** MODEL_FEEDBACK_LEDGER_AUTORESEARCH_SIGNAL_PHASE1

**What:** Extended the champion/challenger AutoResearch planner to accept
validated model-feedback ledger records as bounded planning signals.

**Why:** RedDog now admits independently verified model-selection outcomes into
the model-feedback ledger. The AutoResearch planner needs to cite and digest
those outcomes so verified runtime evidence can influence future benchmark
campaign priority without promoting models or trusting raw claims.

**Files:**
- `src/model_champion_challenger_autoresearch.py` - validates same-task,
  same-catalog feedback records, binds their IDs/digest into the plan receipt,
  and uses them only to reprioritize known candidates.
- `tests/test_model_champion_challenger_autoresearch.py` - verifies feedback
  priority, malformed/mismatched feedback rejection, and no candidate invention.

**Truth Boundary:**
- IMPLEMENTED: feedback records can raise priority for existing benchmark
  candidates and are digest-bound into AutoResearch plan receipts.
- IMPLEMENTED: feedback records must be same task family, same catalog snapshot,
  have valid source-ratchet digest and verification receipts, and cannot create
  candidates outside the supplied candidate pool.
- NOT IMPLEMENTED: provider calls, benchmark execution, model promotion,
  catalog mutation, PatternMemory writes, HoloIndex re-indexing, or runtime model
  default binding.

**WSP References:** WSP 15, WSP 22, WSP 50, WSP 97.

---

## Future Changes
- Enhanced routing algorithms (Phase 1)
- Cost optimization features (Phase 2)
- Enterprise monitoring (Phase 3)
- Multi-provider ensemble methods (Phase 4)
