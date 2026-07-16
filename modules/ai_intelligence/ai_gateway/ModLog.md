# AI Gateway Module Change Log

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
