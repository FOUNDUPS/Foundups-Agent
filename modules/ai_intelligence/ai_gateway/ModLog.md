# AI Gateway Module Change Log

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

## [2026-07-16] - Model Feedback Ledger Admission

**Who:** 0102 Codex
**Type:** Feedback Admission
**Slice:** REDDOG_MODEL_FEEDBACK_LEDGER_ADMISSION_PHASE1

**What:** Added verified model-selection outcome rehydration and an explicit
model-feedback ledger admission layer.

**Why:** RedDog verified-outcome ratchet can now emit a
`ModelSelectionOutcomeReceipt`, but no model-feedback ledger admitted that
receipt. Recursive model intelligence needs a receipt-checked ledger entry
before any later benchmark, promotion, or PatternMemory feedback can trust the
outcome.

**Files:**
- `src/model_intelligence_outcomes.py` - rehydrates serialized outcome receipts
  and recomputes deterministic IDs before feedback use.
- `src/model_feedback_ledger.py` - explicit injected-store admission with
  source-ratchet consistency checks and secret scanning.
- `tests/test_model_intelligence_outcomes.py` - serialized receipt rehydration
  and tamper rejection tests.
- `tests/test_model_feedback_ledger.py` - ledger admission acceptance,
  fail-closed, mismatch, secret, and AST boundary tests.

**Truth Boundary:**
- IMPLEMENTED: explicit ledger admission for feedback-eligible model-selection
  outcome receipts.
- IMPLEMENTED: serialized outcome receipts are rehydrated and digest-checked
  before admission.
- IMPLEMENTED: optional source-ratchet verifier/runtime-binding consistency is
  checked before ledger writes.
- NOT IMPLEMENTED: provider calls, benchmark execution, catalog promotion,
  runtime default binding, PatternMemory writes, HoloIndex re-indexing, or
  automatic resident-loop model-feedback admission.

**WSP References:** WSP 15, WSP 22, WSP 50, WSP 97.

---

## [2026-07-16] - Model Outcome Runtime Binding Feedback Carry

**Who:** 0102 Codex
**Type:** Receipt Hardening
**Slice:** MODEL_SELECTION_OUTCOME_RUNTIME_BINDING_FEEDBACK_PHASE1

**What:** Added optional runtime-binding proof fields to
`ModelSelectionOutcomeReceipt` and feedback records.

**Why:** Verified RedDog execution now carries model-runtime binding proof
through verifier, publish, ratchet, held-out, and PatternMemory admission. The
model-intelligence feedback receipt also needs to cite the model runtime binding
that actually produced an accepted outcome, so recursive model learning does not
collapse back to selection-only evidence.

**Files:**
- `src/model_intelligence_outcomes.py` - validates a supplied
  `RedDogModelRuntimeBindingReceipt`, recomputes its digest, checks selection,
  catalog, task-family, decision, and receipt-prefix invariants, and carries the
  binding into accepted feedback records.
- `tests/test_model_intelligence_outcomes.py` - runtime-binding carry and
  forged/mismatched binding rejection tests.

**Truth Boundary:**
- IMPLEMENTED: optional runtime-binding evidence carry for model selection
  outcome feedback.
- IMPLEMENTED: supplied runtime-binding receipts are rehashed and cross-checked
  before feedback eligibility can cite them.
- NOT IMPLEMENTED: provider calls, benchmark execution, catalog promotion,
  PatternMemory writes, HoloIndex re-indexing, or RedDog runtime default
  mutation.

**WSP References:** WSP 15, WSP 22, WSP 50, WSP 97.

---

## [2026-07-16] - RedDog Runtime Binding Artifact Supply

**Who:** 0102 Codex
**Type:** Runtime Artifact Bridge
**Slice:** REDDOG_MODEL_RUNTIME_BINDING_ARTIFACT_SUPPLY_PHASE1

**What:** Added a bounded supplier and startup adapter that materialize a
`RedDogModelRuntimeBindingReceipt` JSON artifact from an existing production
model-selection receipt, benchmark evidence, promotion evidence, signed
production evidence, and explicit runtime binding policy.

**Why:** After RedDog runtime paths learned to consume runtime-binding receipts,
the resident runtime needs a receipt artifact producer. This bridge supplies the
artifact without hard-coding model defaults or trusting catalog-only champion
fields.

**Files:**
- `src/model_runtime_binding_artifact_supply.py` - rehydrates source receipts,
  verifies signed production evidence, binds runtime models, and atomically
  writes one receipt outside the repository.
- `src/model_runtime_binding_artifact_supply_bootstrap.py` - outside-repo JSON
  input loader, trusted model-evidence key resolver construction, public
  signature verifier selection, and supplier invocation.
- `tests/test_model_runtime_binding_artifact_supply.py` - serialized and typed
  evidence acceptance, missing signature-gate rejection, policy-mismatch
  rejection, repository-output rejection, and AST boundary tests.
- `tests/test_model_runtime_binding_artifact_supply_bootstrap.py` - positive
  materialization and missing-key/output/AST boundary tests.
- `README.md` and `INTERFACE.md` - API and truth-boundary notes.

**Truth Boundary:**
- IMPLEMENTED: production runtime-binding receipt artifact supply.
- IMPLEMENTED: serialized evidence requires key resolution and signature
  verification before runtime binding.
- IMPLEMENTED: receipt output must live outside the repository.
- NOT IMPLEMENTED: provider calls, benchmark execution, telemetry persistence,
  HoloIndex re-indexing, extension runtime default mutation, worker dispatch,
  PatternMemory writes, or panel runtime promotion.

**WSP References:** WSP 15, WSP 22, WSP 50, WSP 97.

---

## [2026-07-16] - RedDog Model Selection Artifact Supply Main Preflight

**Who:** 0102 Codex
**Type:** Runtime Artifact Bridge
**Slice:** REDDOG_MODEL_SELECTION_ARTIFACT_SUPPLY_MAIN_PREFLIGHT_PHASE1

**What:** Added an optional `main.py` startup adapter that materializes the
production `ModelSelectionReceipt` path from outside-repo catalog, signed
evidence, requirements, and trusted public-key JSON inputs.

**Why:** The resident RedDog architect FIX promotion path should not require a
manual model-selection receipt when the signed benchmark/promotion evidence is
already available. The bridge still must fail closed instead of trusting catalog
champion fields or raw evidence mappings.

**Files:**
- `src/model_selection_artifact_supply_bootstrap.py` - outside-repo input
  loader, trusted model-evidence key resolver construction, public signature
  verifier selection, and supplier invocation.
- `tests/test_model_selection_artifact_supply_bootstrap.py` - positive
  materialization and missing-key/output/backend/AST boundary tests.
- `README.md` and `INTERFACE.md` - API and startup-boundary notes.

**Truth Boundary:**
- IMPLEMENTED: explicit main-startup model-selection artifact supply.
- IMPLEMENTED: trusted public keys and signed evidence are required before
  production selection.
- NOT IMPLEMENTED: provider calls, benchmark execution, runtime model default
  binding, telemetry persistence, worker dispatch, source mutation,
  PatternMemory writes, or HoloIndex re-indexing.

**WSP References:** WSP 15, WSP 22, WSP 50, WSP 97.

---

## [2026-07-16] - RedDog Model Selection Artifact Supply

**Who:** 0102 Codex
**Type:** Runtime Artifact Bridge
**Slice:** REDDOG_MODEL_SELECTION_ARTIFACT_SUPPLY_PHASE1

**What:** Added a bounded supplier that materializes a production
`ModelSelectionReceipt` JSON artifact from a catalog snapshot and signed
benchmark/promotion evidence.

**Why:** The resident RedDog architect FIX promotion bridge expects a
model-selection receipt path. After signed production-evidence hardening,
production model selection must be created from verified evidence, not raw
mappings or catalog-only champion fields.

**Files:**
- `src/model_selection_artifact_supply.py` - rehydrates the catalog snapshot,
  verifies serialized signed evidence, runs production model selection, and
  atomically writes one receipt outside the repository.
- `tests/test_model_selection_artifact_supply.py` - serialized and typed
  evidence acceptance, missing signature-gate rejection, non-production
  rejection, repository-output rejection, and AST boundary tests.
- `README.md` and `INTERFACE.md` - API and truth-boundary notes.

**Truth Boundary:**
- IMPLEMENTED: production model-selection receipt artifact supply.
- IMPLEMENTED: serialized evidence requires key resolution and signature
  verification before production selection.
- IMPLEMENTED: receipt output must live outside the repository.
- NOT IMPLEMENTED: provider calls, benchmark execution, telemetry persistence,
  HoloIndex re-indexing, runtime model default binding, extension mutation,
  worker dispatch, PatternMemory writes, or panel runtime promotion.

**WSP References:** WSP 15, WSP 22, WSP 50, WSP 97.

---

## [2026-07-16] - Model Intelligence Receipt Rehydration and Signed Evidence

**Who:** 0102 Codex
**Type:** Runtime Foundation Hardening
**Slice:** MODEL_INTELLIGENCE_RECEIPT_REHYDRATION_AND_SIGNED_EVIDENCE_VERIFICATION_PHASE1

**What:** Added the signed production-evidence admission gate for model
intelligence and wired production model selection/runtime binding to it.

**Why:** Production selection previously accepted raw `production_evidence`
mappings and presence-checked receipt IDs. A forged mapping could produce a
production `ModelSelectionReceipt` without authentic benchmark-verifier and
promotion-authority signatures.

**Files:**
- `src/model_signed_evidence.py` - receipt rehydration, deterministic ID
  recomputation, role-specific signed evidence verification, nonce admission
  handling, and typed `VerifiedModelProductionEvidence`.
- `src/model_intelligence_selection.py` - production selection now rejects raw
  mappings and requires verified signed evidence.
- `src/model_runtime_binding.py` - runtime bridge binding now requires verified
  production evidence and keeps panel runtime binding deferred.
- `tests/test_model_signed_evidence.py` and helper - rehydration, tamper,
  signer-role, signature, nonce and panel-deferred tests.
- Existing selection/outcome/runtime-binding tests - updated for the new truth
  boundary.
- `README.md` and `INTERFACE.md` - API and truth-boundary notes.

**Truth Boundary:**
- IMPLEMENTED: benchmark/promotion/catalog/selection/runtime receipts can be
  rehydrated and digest-checked.
- IMPLEMENTED: single-model production evidence requires signed
  `benchmark_verifier` and `promotion_authority` receipts.
- IMPLEMENTED: production selection rejects raw evidence mappings.
- IMPLEMENTED: runtime binding requires verified production evidence.
- IMPLEMENTED: panel runtime binding remains fail-closed/deferred.
- NOT IMPLEMENTED: private-key handling, signing, provider calls, benchmark
  execution, panel topology promotion, extension runtime mutation, PatternMemory
  writes, or HoloIndex re-indexing.

**WSP References:** WSP 15, WSP 22, WSP 50, WSP 97.

---

## [2026-07-16] - RedDog Dynamic Runtime Model Binding

**Who:** 0102 Codex
**Type:** Runtime Foundation
**Slice:** REDDOG_DYNAMIC_MODEL_SELECTION_RUNTIME_BINDING_PHASE1

**What:** Added a receipt-bound runtime binding layer for RedDog dynamic model
selection.

**Why:** RedDog must not install hard-coded GLM/DeepSeek/Kimi panels or
catalog-only champion fields as production authority. Runtime model binding must
consume the catalog snapshot, production selection receipt, benchmark evidence,
signed promotion evidence, role/topology bindings, and explicit WSP_15 policy
before emitting bridge-ready model IDs.

**Files:**
- `src/model_runtime_binding.py` - runtime binding policy, receipt, role binding,
  evidence checks, and bridge-payload projection.
- `tests/test_model_runtime_binding.py` - single-model binding, catalog-only
  champion rejection, evaluation rejection, policy mismatch, panel role/topology,
  duplicate evidence, and no-network/no-command tests.
- `README.md` and `INTERFACE.md` - API and truth-boundary notes.

**Truth Boundary:**
- IMPLEMENTED: receipt-bound production model selections can produce a RedDog
  bridge payload.
- IMPLEMENTED: catalog-only champions and evaluation selections fail closed for
  runtime binding.
- IMPLEMENTED: panel role/topology evidence is bound, with verifier kept outside
  the candidate panel.
- NOT IMPLEMENTED: extension runtime mutation, provider calls, benchmark
  execution, champion ledger writes, PatternMemory promotion, or dynamic default
  persistence.

**WSP References:** WSP 15, WSP 22, WSP 50, WSP 97.

---

## [2026-07-16] - Champion/Challenger AutoResearch Planner

**Who:** 0102 Codex
**Type:** Runtime Foundation
**Slice:** MODEL_CHAMPION_CHALLENGER_AUTORESEARCH_PHASE1

**What:** Added a receipt-bound AutoResearch campaign planner for model
champion/challenger evaluation.

**Why:** After benchmark harness and promotion gate receipts exist, RedDog needs
a governed way to decide which model or panel candidates should be benchmarked
next without running providers, writing PatternMemory, or installing runtime
defaults.

**Files:**
- `src/model_champion_challenger_autoresearch.py` - AutoResearch policy, campaign
  items, plan receipts, gate/candidate binding, and fail-closed budget/verifier
  checks.
- `tests/test_model_champion_challenger_autoresearch.py` - new-candidate,
  challenger-retest, stop, missing gate/budget, verifier mismatch, cap,
  deterministic digest, and no-network/no-command tests.
- `README.md` and `INTERFACE.md` - API and truth-boundary notes.

**Truth Boundary:**
- IMPLEMENTED: promotion-gate receipts can produce a deterministic benchmark
  campaign plan.
- IMPLEMENTED: untested candidates and challengers are routed separately.
- IMPLEMENTED: missing gate receipts, verifier mismatch, and missing cost budget
  fail closed.
- NOT IMPLEMENTED: campaign execution, provider calls, PatternMemory writes,
  champion ledger writes, AutoResearch git mutation, or RedDog runtime binding.

**WSP References:** WSP 15, WSP 22, WSP 50, WSP 97.

---

## [2026-07-16] - Champion/Challenger Promotion Gate

**Who:** 0102 Codex
**Type:** Runtime Foundation
**Slice:** MODEL_CHAMPION_CHALLENGER_PROMOTION_GATE_PHASE1

**What:** Added a fail-closed promotion gate over model benchmark evidence.

**Why:** Benchmark evidence alone should not install production authority. RedDog
needs a separate gate that validates task-set/verifier/topology evidence against
explicit WSP_15 policy and requires signed promotion authority before a champion
receipt exists.

**Files:**
- `src/model_promotion_gate.py` - promotion policy, gate receipt, evidence
  consistency checks, challenger/hero threshold handling, and signed promotion
  evidence emission.
- `tests/test_model_promotion_gate.py` - signed authority, below-threshold
  challenger, missing evidence, tampered benchmark projection, policy conflict,
  threshold, deterministic digest, and no-network/no-command tests.
- `README.md` and `INTERFACE.md` - API and truth-boundary notes.

**Truth Boundary:**
- IMPLEMENTED: matching benchmark evidence plus signed authority can produce a
  `ModelPromotionEvidenceReceipt`.
- IMPLEMENTED: below-threshold candidates remain challengers without champion
  authority.
- IMPLEMENTED: mismatched or tampered benchmark evidence fails closed.
- NOT IMPLEMENTED: model catalog mutation, champion ledger persistence,
  AutoResearch scheduling, provider calls, or RedDog dynamic runtime binding.

**WSP References:** WSP 15, WSP 22, WSP 50, WSP 97.

---

## [2026-07-16] - Model Combination Benchmark Harness

**Who:** 0102 Codex
**Type:** Runtime Foundation
**Slice:** MODEL_COMBINATION_BENCHMARK_HARNESS_PHASE1

**What:** Added a deterministic benchmark harness for single-model and Fusion
panel candidates.

**Why:** RedDog model selection must be driven by measured task fitness. After
receipt-bound production evidence landed, the next missing layer was a governed
way to produce benchmark evidence from held-out tasks without turning provider
catalog claims or model self-reports into production authority.

**Files:**
- `src/model_combination_benchmark_harness.py` - held-out task and candidate
  schemas, role/topology-bound candidate construction, injected runner/verifier
  benchmark execution, fail-closed sample receipts, and benchmark run receipts.
- `tests/test_model_combination_benchmark_harness.py` - single-model, panel,
  verifier-role exclusion, runner/verifier failure, deterministic digest, task
  validation, panel evidence boundary, and no-network/no-command tests.
- `README.md` and `INTERFACE.md` - public truth boundary and API notes.

**Truth Boundary:**
- IMPLEMENTED: benchmark evidence can be produced for single-model and panel
  candidates from injected runner/verifier seams.
- IMPLEMENTED: task-set, held-out split, verifier, sample count, cost, latency,
  and role/topology digests are bound into receipts.
- IMPLEMENTED: runner/verifier failures produce rejected sample evidence rather
  than promotion evidence by assertion.
- NOT IMPLEMENTED: provider calls, benchmark scheduling, champion/challenger
  promotion gates, PatternMemory writes, AutoResearch campaigns, or RedDog
  dynamic runtime binding.

**WSP References:** WSP 15, WSP 22, WSP 50, WSP 97.

---

## [2026-07-16] - Benchmark Evidence and Outcome Receipts

**Who:** 0102 Codex
**Type:** Runtime Foundation Hardening
**Slice:** MODEL_BENCHMARK_EVIDENCE_AND_OUTCOME_RECEIPTS_PHASE1

**What:** Hardened model-intelligence production selection with receipt-bound
benchmark, verifier, promotion, topology, and outcome evidence.

**Why:** #1129 introduced task-selection receipts, but production selection still
depended on scalar catalog fields (`promotion_state`, `benchmark_scores`,
`verifier_pass_rate`). Production binding must not trust those fields unless they
are backed by measured held-out benchmark evidence and signed promotion authority.

**Files:**
- `src/model_intelligence_outcomes.py` - benchmark evidence receipts, signed
  promotion evidence receipts, production evidence mapping, and fail-closed
  outcome receipts.
- `src/model_intelligence_selection.py` - production selection now requires
  receipt-bound evidence and an explicit nonzero verifier threshold; panel
  selection emits role assignments/topology digest and reserves verifier outside
  the candidate panel.
- `tests/test_model_intelligence_outcomes.py` and
  `tests/test_model_intelligence_selection.py` - benchmark digest, held-out
  split, verifier digest, signed promotion, threshold, panel-role, and no-network
  guards.

**Truth Boundary:**
- IMPLEMENTED: evaluation selection behavior remains available for benchmarking.
- IMPLEMENTED: production selection rejects catalog-only champions.
- IMPLEMENTED: benchmark evidence binds model ID, task-set digest, held-out split,
  prompt/topology digest, verifier digest, sample count, cost, and latency.
- IMPLEMENTED: promotion evidence requires signed promotion authority.
- NOT IMPLEMENTED: benchmark harness execution, champion/challenger ledger writes,
  AutoResearch campaigns, RedDog dynamic runtime binding, provider calls, or
  PatternMemory admission.

**WSP References:** WSP 15, WSP 22, WSP 50, WSP 97.

---

## [2026-07-16] - Model Intelligence Task Selection Receipts

**Who:** 0102 Codex
**Type:** Runtime Foundation
**Slice:** MODEL_INTELLIGENCE_TASK_SELECTION_RECEIPT_PHASE1

**What:** Added task-scoped model selection receipts over canonical catalog snapshots.

**Why:** RedDog should request capabilities, budget and WSP_15 task requirements, not
hardcoded model names. This slice provides the deterministic receipt layer that later
RedDog runtime binding and benchmark promotion can consume.

**Files:**
- `src/model_intelligence_selection.py` - model task requirements, single/panel
  selection, production/evaluation modes, candidate rankings, digest-bound receipts.
- `tests/test_model_intelligence_selection.py` - production fail-closed, panel
  diversity, capability/cost filtering, digest, and no-network/no-command tests.

**Truth Boundary:**
- IMPLEMENTED: evaluation can select candidate models for benchmarking.
- IMPLEMENTED: production rejects unbenchmarked non-champion candidates.
- IMPLEMENTED: panel mode prefers provider diversity without hardcoded providers.
- NOT IMPLEMENTED: RedDog bridge binding, benchmark ledger, champion/challenger
  promotion writes, AutoResearch campaigns, or provider calls.

**WSP References:** WSP 15, WSP 22, WSP 50, WSP 97.

---

## [2026-07-16] - Model Intelligence Canonical Catalog Runtime

**Who:** 0102 Codex
**Type:** Runtime Foundation
**Slice:** MODEL_INTELLIGENCE_CANONICAL_CATALOG_RUNTIME_PHASE1

**What:** Added a canonical model catalog snapshot layer for RedDog model intelligence.

**Why:** RedDog must select models by measured task fitness, not by permanent hardcoded
GLM/DeepSeek/Kimi or static gateway defaults. This slice creates the receipt-bound
catalog evidence layer that later selection, benchmarking, and champion/challenger
promotion can consume.

**Files:**
- `src/model_intelligence_catalog.py` - model capability cards, catalog snapshot receipts,
  static registry normalization, OpenRouter-style catalog normalization, and local role
  normalization.
- `tests/test_model_intelligence_catalog.py` - deterministic digest, malformed record,
  local path privacy, and no-network/no-command guard tests.

**Truth Boundary:**
- IMPLEMENTED: immutable catalog snapshot receipts and normalized capability cards.
- IMPLEMENTED: "latest/provider catalog" evidence remains `candidate`, never `champion`.
- NOT IMPLEMENTED: task selection receipts, benchmark harness, fusion panel optimization,
  RedDog bridge binding, AutoResearch promotion, or provider network fetch.

**WSP References:** WSP 15, WSP 22, WSP 50, WSP 97.

---

## [2026-02-17] - Full Model Registry Refresh (Feb 2026 Current)

**Who:** 0102
**Type:** Configuration Update + Enhancement
**What:** Refreshed entire model registry to Feb 2026 current + activity routing matrix

**Model Registry Updates:**
| Provider | Changes |
|----------|---------|
| OpenAI | GPT-5.2 (flagship), GPT-5.2-Codex (coding), GPT-5, o3, o3-pro, o4-mini now CURRENT; GPT-4o/GPT-4o-mini SUNSET (retired Feb 13); o1/o1-mini/o3-mini DEPRECATED |
| Grok/X.AI | Grok-4 (flagship $3/$15), grok-4-fast ($0.20/$0.50), grok-code-fast-1 (coding), grok-3-mini now CURRENT; grok-3 LEGACY; grok-2 DEPRECATED |
| Gemini | gemini-3-pro-preview, gemini-3-flash-preview, gemini-2.5-flash-lite added; gemini-2.0-flash DEPRECATED (shutdown March 31 2026) |
| Anthropic | No changes (claude-opus-4-6, claude-sonnet-4-5, claude-haiku-4-5 remain current) |

**Codebase Migration (8 files updated):**
- `ai_gateway.py`: OpenAI models gpt-4o→gpt-5.2-codex/gpt-5, o3-mini→o4-mini, o1→o3; Grok models grok-3→grok-4/grok-code-fast-1/grok-4-fast
- `main.py`: Updated extract_model_ids regex patterns + PROVIDER_MODEL_SOURCES search terms
- `ai_parameter_optimizer.py`: gpt-4o → gpt-5.2
- `pqn_research_dae_orchestrator.py`: gpt-4o → gpt-5.2, claude-3-5-sonnet → claude-sonnet-4-5
- `theorist_dae_poc.py`: grok-2 → grok-4
- `fam_adapter.py`: gpt-4o-mini → gpt-5, grok-3-mini-fast → grok-4-fast
- `fix_openclaw_auth.py`: openai/gpt-4o → openai/gpt-5
- `api_preflight_check.py`: gpt-4o-mini → gpt-5, openai/gpt-4o → openai/gpt-5
- `cmst_pqn_detector_v3.py`: gpt-4o → gpt-5

**Activity Routing Matrix (updated):**
| Task | Primary Provider | Model |
|------|-----------------|-------|
| coding | anthropic | claude-opus-4-6 |
| math | openai | o4-mini |
| reasoning | openai | o3 |
| social/edgy | grok | grok-4 |
| research | gemini | gemini-2.5-pro |
| quick | grok | grok-4-fast |

**MIGRATION_MAP updated:** gpt-4o→gpt-5, gpt-4o-mini→gpt-5, o1→o3, o1-mini→o4-mini, o3-mini→o4-mini, grok-2→grok-4

**WSP References:** WSP 50 (web search for current models), WSP 84 (extended model_registry), WSP 22 (ModLog)

---

## [2026-02-15] - Model Version Update (Obsolete → Current)

**Who:** 0102 Claude
**Type:** Configuration Update
**What:** Updated all provider models to current versions

**Changes:**
| Provider | Old (Obsolete) | New (Current) |
|----------|----------------|---------------|
| OpenAI | `gpt-4`, `gpt-3.5-turbo` | `gpt-4o`, `gpt-4o-mini` |
| Anthropic | `claude-3-opus-20240229`, `claude-3-sonnet-20240229`, `claude-3-haiku-20240307` | `claude-opus-4-6`, `claude-sonnet-4-5-20250929`, `claude-haiku-4-5-20251001` |
| Gemini | `gemini-pro`, `gemini-pro-vision` | `gemini-2.0-flash` |
| Grok | `grok-3` | `grok-3` (unchanged - current) |

**Why:** Old model IDs deprecated or sunset by providers
**Impact:** Ensures API calls succeed with current model endpoints

---

## [2025-09-29] - Module Creation and WSP Compliance
**Who:** 0102 Claude (Assistant)
**Type:** New Module Creation - WSP 49 Compliance
**What:** Created AI Gateway module following WSP modular coding principles
**Why:** Consolidated scattered AI gateway files into proper module structure
**Impact:** Improved code organization, WSP compliance, and maintainability

**Files Created:**
- `modules/ai_intelligence/ai_gateway/README.md` - WSP compliance status
- `modules/ai_intelligence/ai_gateway/ROADMAP.md` - Development roadmap
- `modules/ai_intelligence/ai_gateway/ModLog.md` - This change log
- `modules/ai_intelligence/ai_gateway/INTERFACE.md` - API documentation
- `modules/ai_intelligence/ai_gateway/requirements.txt` - Dependencies
- `modules/ai_intelligence/ai_gateway/__init__.py` - Public API
- `modules/ai_intelligence/ai_gateway/src/__init__.py` - Package init
- `modules/ai_intelligence/ai_gateway/src/ai_gateway.py` - Main implementation
- `modules/ai_intelligence/ai_gateway/tests/README.md` - Test documentation

**WSP Protocols Applied:**
- **WSP 3**: Enterprise Domain placement (ai_intelligence)
- **WSP 49**: Mandatory module directory structure
- **WSP 22**: Change tracking with ModLog
- **WSP 11**: Clear public API definition
- **WSP 34**: Test documentation structure

**Technical Details:**
- Moved `ai_gateway.py` from root to `modules/ai_intelligence/ai_gateway/src/`
- Created proper import structure with `__init__.py` files
- Maintained all existing functionality while improving organization
- Added comprehensive documentation following WSP standards

## Future Changes
- Enhanced routing algorithms (Phase 1)
- Cost optimization features (Phase 2)
- Enterprise monitoring (Phase 3)
- Multi-provider ensemble methods (Phase 4)
