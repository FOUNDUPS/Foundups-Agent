# FoundUp Manifest Readiness + Execution Ecosystem Reconciliation (Phase 1)

- Lane: W9 (read-only architecture audit)
- Status: DECISION-ONLY (no manifest/code/test/registry/role mutation)
- Base: origin/main 3e5c00f59
- Date: 2026-06-08
- WSP refs: WSP_00, WSP_50/WSP_87 (HoloIndex pre-action), WSP_15 (priority), WSP_84 (reuse), WSP_97 (Truth Boundary), WSP_22 (ModLog)
- Predecessors: #763 (auto-test coverage matrix), secured base #747 (genesis gate), #762 (headless no-live-launch), #768 (typed shell=False exec boundary), #769 (durable execution = build on existing primitives)

---

## 1. Mission and Scope

Before OpenClaw/Hermes can autonomously build a FoundUp, each FoundUp needs a
machine-readable BUILD/TEST CONTRACT that the WRE reads as the build target. This audit:
1. Recomputes manifest readiness for all registered FoundUps (does not assume #763 counts).
2. Distinguishes p.fMALL routing/product manifests from true WRE build/test contracts.
3. Defines the minimum manifest build/test schema.
4. Reconciles execution roles across OpenClaw, Hermes, AI Overseer, WRE, and future
   external agents, so the schema does NOT create a second build system.
5. Names a follow-on implementation slice.

This is READ-ONLY characterization. No `foundup_manifest.json` is created or edited; no
source/test/registry/role mutation. NO_OVERCLAIM: this is a readiness + architecture
characterization, NOT a claim that FoundUps are buildable and NOT a claim that AI Overseer
is the builder.

---

## 2. Predecessors and Secured Base

- #763 FOUNDUP_AUTO_TEST_MATRIX_COVERAGE: 16 registered FoundUps, 8/16 lacking
  `foundup_manifest.json`, build/test surface gaps. This audit refines #763 with a
  build/test-contract lens (a manifest can be present yet not a build contract).
- #747 genesis gate: envelope validation before scaffold; server-authored PolicyFlags.
- #762 headless no-live-launch: execution never performs a real live launch in Phase 1.
- #768 typed shell=False exec boundary: AI Overseer auto-fix uses an allowlisted argv
  executor (autofix_executor.py), not free-form shell.
- #769 durable execution spike: build on existing primitives; do NOT add a new orchestrator.

The schema defined here must keep all of these gates load-bearing.

---

## 3. FOLLOW-WSP Evidence (HoloIndex discovery + direct-read inventory)

HoloIndex was run FIRST as discovery (not as proof). Results:

| Query | Top hits | Signal | Used for |
|-------|----------|--------|----------|
| "foundup manifest build test contract schema" | (HOLODAE-ANALYZE) "No files found to analyze" | LOW | none - fell back to git ls-files + direct read |
| "openclaw foundup job orchestrator hermes executor build plan" | agent_market/ARCHITECTURE.md, moltbot_bridge/fam_adapter.py, openclaw_dae.py, WSP_30/35/98 | MEDIUM | pointed at moltbot_bridge + WSP_30; exact build seam found via git ls-files + direct read |

HOLOINDEX_LOW_SIGNAL recorded: HoloIndex did not surface the registry, the manifests, or
the build_plan/job/hermes machinery. All inventory below is from `git ls-files` + direct
file reads, re-verified on main 3e5c00f59. Every classification and role claim carries a
file:line citation; no HoloIndex hit is used as proof.

Direct-read inventory (all read first-hand this slice):
- `modules/foundups/foundup_registry.json` (16 entities).
- All 9 tracked `foundup_manifest.json` files (enumerated in section 4).
- `modules/communication/moltbot_bridge/src/openclaw_foundup_orchestrator.py`,
  `.../foundup_job_contract.py`.
- `modules/infrastructure/wre_core/src/foundup_job_consumer.py`, `foundup_job_router.py`,
  `hermes_job_executor.py`.
- `modules/foundups/agent/src/build_plan.py`, `build_plan_generator.py`,
  `build_plan_executor.py`, `hermes_foundup_job_executor.py`.
- `modules/foundups/docs/FOUNDUP_BUILD_PLAN_CONTRACT.md`,
  `BUILD_PLAN_EXECUTION_ADAPTER_CONTRACT.md`.
- `modules/ai_intelligence/ai_overseer/` (README, foundup_genesis/, mcp_integration.py,
  autofix_executor.py) for the role-boundary check.

---

## 4. Existing-Manifest Reality: Routing/Product, Not Build Contract

CENTRAL FINDING (verified, not assumed): every existing `foundup_manifest.json` is a
p.fMALL ROUTING/PRODUCT manifest (or, for shield, a governance-spec manifest). NONE
carries a WRE build/test contract field. "Has a manifest" does NOT mean "has a build/test
contract."

Tracked manifest files (9) and the registry entry each maps to:

| Manifest file | foundup_id | Schema family | Build/test fields? |
|---------------|-----------|---------------|--------------------|
| modules/foundups/gotjunk/foundup_manifest.json | gotjunk_001 | p.fMALL routing v1 | NONE |
| modules/foundups/kosei/foundup_manifest.json | kosei | p.fMALL routing v1 | NONE |
| modules/foundups/voteballots/foundup_manifest.json | voteballots | p.fMALL routing v1 | NONE |
| modules/foundups/trade/foundup_manifest.json | trade | p.fMALL routing v1 | NONE |
| modules/gamification/whack_a_magat/foundup_manifest.json | magadoom_001 | p.fMALL routing v1 | NONE |
| modules/platform_integration/antifafm_broadcaster/foundup_manifest.json | antifafm_001 | p.fMALL routing v1 | NONE |
| modules/foundups/holoindex_prod_01/foundup_manifest.json | holoindex_prod_01 (public) | p.fMALL routing v1 | NONE |
| holo_index/foundup_manifest.json | holoindex_prod_01 (internal) | minimal routing | NONE |
| modules/foundups/shield/foundup_manifest.json | shield | governance-spec | NONE |

Field reality (file:line):
- p.fMALL routing schema (gotjunk:1-30 representative): `foundup_id, name, version,
  description, tagline, tier, lifecycle_stage, entry_url, routing_prefix, icon_url,
  required_subscription_tier, is_invite_only, capabilities, agent_routes, holo_collections,
  data_namespace, cabr_contract, owner_id, token_symbol, category, launch_readiness,
  created_at, signature`. No `build`, `test`, `dry_run`, `safe_mutation_surface`,
  `forbidden_paths`, `required_gates`, or `evidence_output`.
- Internal HoloIndex manifest (holo_index/foundup_manifest.json:1-11): `foundup_id, name,
  version, description, routing_prefix, data_namespace, capabilities, entry_point,
  capabilities_adapter`. Routing/adapter only; no build/test fields.
- shield (modules/foundups/shield/foundup_manifest.json:1-35): a governance-spec manifest
  with `implementation_status, runtime_status (NO_RUNTIME), truth_boundaries{...12 no_*
  flags...}, proposed_domain, next_slice`. The truth_boundaries are negative guards, not a
  build/test contract (no build/test/dry_run/required_gates/evidence_output).

Reconciliation note (manifest count vs registered-with-manifest):
- 9 manifest files, but 8 distinct registry FoundUps carry `manifest_status: exists`
  (gotjunk_001, kosei, voteballots, trade, magadoom_001, antifafm_001, holoindex_prod_01,
  shield). The 9th file is a DUPLICATE foundup_id: both
  `modules/foundups/holoindex_prod_01/foundup_manifest.json` (v1.0.0, public p.fMALL
  surface) and `holo_index/foundup_manifest.json` (v0.1.0, internal) declare
  `foundup_id: holoindex_prod_01`. This is the dual-identity boundary noted in the registry
  (foundup_registry.json:592). Neither carries build/test fields.

---

## 5. Per-FoundUp Classification (16; counts reconcile)

Source of truth: `modules/foundups/foundup_registry.json` (16 entities). Each entity gets
exactly one PRIMARY class. Classification was ground-truth-verified with per-module
`git ls-files` src/test counts (not registry labels alone) - this corrected two entries
(voteballots, trade) whose registry/manifest "SPECIFIED_NOT_IMPLEMENTED" labels conflict
with a real in-repo src+test surface.

Precedence applied (highest first):
1 EXTERNAL_OR_DEFERRED  >  2 NO_SAFE_BUILD_SURFACE  >  3 MISSING_MANIFEST  >
4 MANIFEST_PRESENT_BUT_INCOMPLETE  >  5 MANIFEST_READY.

DELIBERATE REFINEMENT (CoR, evidence-based): 4 registered entities have
`entity_type != foundup/skeleton_candidate/external_foundup` and `manifest_status:
not_applicable` (platform/infra/tool), yet have large real codebases (agent_market 19
src/17 tests; simulator 125 py/42 tests). Forcing them into NO_SAFE_BUILD_SURFACE would be
factually false (they HAVE build surfaces; they are simply not FoundUps). They are placed
in an explicit 6th bucket NOT_A_FOUNDUP so nothing is mischaracterized and counts still
reconcile to 16. This refines #763's binary lens per the dispatch's allowance.

| # | foundup_id | entity_type | impl | manifest | src/tests (module dir) | PRIMARY class | Evidence |
|---|-----------|-------------|------|----------|------------------------|---------------|----------|
| 1 | gotjunk_001 | foundup | IMPLEMENTED | exists (routing) | 0 py src / 1 test, 174 files (frontend) | MANIFEST_PRESENT_BUT_INCOMPLETE | registry:7-46; manifest routing-only:1-30 |
| 2 | kosei | foundup | IMPLEMENTED | exists (routing) | 2 src / 5 tests | MANIFEST_PRESENT_BUT_INCOMPLETE | registry:48-89; manifest:1-35 |
| 3 | magadoom_001 | foundup | IMPLEMENTED | exists (routing) | 14 src / 14 tests | MANIFEST_PRESENT_BUT_INCOMPLETE | registry:170-209; manifest:1-30 |
| 4 | antifafm_001 | foundup | IMPLEMENTED | exists (routing) | 21 src / 10 tests | MANIFEST_PRESENT_BUT_INCOMPLETE | registry:210-249; manifest:1-30 |
| 5 | voteballots | skeleton_candidate | SPECIFIED (label) | exists (routing) | 7 src / 8 tests | MANIFEST_PRESENT_BUT_INCOMPLETE | registry:90-129; manifest:1-32 (label conflict, see note) |
| 6 | trade | skeleton_candidate | SPECIFIED (label) | exists (routing) | 9 src / 11 tests | MANIFEST_PRESENT_BUT_INCOMPLETE | registry:130-169; manifest:1-38 (label conflict, see note) |
| 7 | move2japan | access_service | IMPLEMENTED | missing | 2 src / 2 tests | MISSING_MANIFEST | registry:328-367 (manifest_status missing) |
| 8 | shield | foundup | SPECIFIED | exists (governance) | 0 src / 0 tests | NO_SAFE_BUILD_SURFACE | registry:610-648; manifest runtime_status NO_RUNTIME:9 |
| 9 | holoindex_prod_01 | infra_service | IMPLEMENTED | exists (routing) | 0 src in module dir (dual-identity pointer) | NO_SAFE_BUILD_SURFACE | registry:567-609 (does not expose internal backend); 2 duplicate manifests |
| 10 | autopost | external_foundup | IMPLEMENTED | external | module_path null | EXTERNAL_OR_DEFERRED | registry:447-486 (related_external_repo) |
| 11 | science_swarm_hub | external_foundup | IMPLEMENTED | external | 0 src (stub delegates to package) | EXTERNAL_OR_DEFERRED | registry:527-566 (external repo) |
| 12 | pqn_portal | skeleton_candidate | SPECIFIED | partial | 4 src / 0 tests (scaffold) | EXTERNAL_OR_DEFERRED | registry:487-526 (next_slice deferred) |
| 13 | pfmall | platform_layer | IMPLEMENTED | not_applicable | 0 src / 15 tests | NOT_A_FOUNDUP | registry:250-288 ("Platform layer, not a FoundUp") |
| 14 | agent_market | infra_service | IMPLEMENTED | not_applicable | 19 src / 17 tests | NOT_A_FOUNDUP | registry:289-327 ("Not a FoundUp") |
| 15 | social_twin | infra_service | IMPLEMENTED | not_applicable | 2 src / 1 test | NOT_A_FOUNDUP | registry:407-446 ("Not a FoundUp") |
| 16 | simulator | tool_simulator | IMPLEMENTED | not_applicable | 0 src / 42 tests, 125 py | NOT_A_FOUNDUP | registry:368-406 ("Tool, not a FoundUp") |

Counts (reconcile to 16):
- MANIFEST_READY: 0
- MANIFEST_PRESENT_BUT_INCOMPLETE: 6 (gotjunk_001, kosei, magadoom_001, antifafm_001, voteballots, trade)
- MISSING_MANIFEST: 1 (move2japan)
- NO_SAFE_BUILD_SURFACE: 2 (shield, holoindex_prod_01)
- EXTERNAL_OR_DEFERRED: 3 (autopost, science_swarm_hub, pqn_portal)
- NOT_A_FOUNDUP (refinement): 4 (pfmall, agent_market, social_twin, simulator)
- TOTAL: 0+6+1+2+3+4 = 16

Key honesty flags:
- 0 FoundUps are MANIFEST_READY. Even the 6 with manifests are routing-only and
  build/test-incomplete - this is the audit's central, useful result.
- voteballots/trade DATA-QUALITY CONFLICT: registry+manifest self-declare
  SPECIFIED_NOT_IMPLEMENTED (voteballots manifest:30-31) yet the module dirs carry
  7 src/8 tests and 9 src/11 tests. Classified MANIFEST_PRESENT_BUT_INCOMPLETE (a build
  target exists), but the impl-state self-declaration must be reconciled before a build
  contract can trust them. Not overclaimed as buildable.

---

## 6. Minimum WRE Build/Test Schema (build_contract block)

Defined, NOT created. The schema EXTENDS the existing routing/product manifest with a
sibling `build_contract` block; it does not replace any routing field. Each field below
maps to existing machinery (section 9) so the WRE reads what the BuildPlanGenerator
currently DERIVES, rather than re-deriving or inventing.

| Field | Why the WRE needs it | Maps to existing code | Gate tie |
|-------|----------------------|-----------------------|----------|
| foundup_id | join to registry + job + plan | foundup_job_contract.py FoundUpJob.foundup_id:352 | identity |
| module_path (or external_repo) | build target root | build_plan.py BuildTarget.module_path:218 | scope |
| owner_lane | accountability / worker attribution | FoundUpJob.worker_id:369 | audit |
| build | the build command/action (or "no_build") | build_plan.py BuildStepAction DRY_RUN_BUILD step_10:940 | dry-run default |
| test | the discoverable test contract command | build_plan.py BuildStepAction RUN_TESTS step_07:920; adapter doc test_commands/TestResult | evidence |
| dry_run | default-safe simulation command (no live side effect) | build_plan.py mode=DRY_RUN/dry_run=True:553-556; generator forces dry_run:344-361 | #762 no-live-launch |
| safe_mutation_surface | paths the build MAY write | BuildTarget.allowed_paths:218-242; Hermes WorkspaceBinding.allowed_paths; ACTION_ALLOWED_PATHS:124-140 | D0-D6 scope |
| forbidden_paths | paths it must NEVER touch (.env, main.py, *_dae.py, vendor/, secrets) | hermes_job_executor.py BLOCKED_PATHS:103-120; build_plan.py BLOCKED_PATH_PATTERNS:183-194 | D0-D6 / #747 |
| required_gates | which secured gates apply (genesis #747 / exec #768 / no-live #762 / destructive D0-D6) | build_plan.py BuildGate/GateType:304-335; hermes D0-D6:1016-1168 | re-entry, not pre-clear |
| evidence_output | where the redacted post-build/test evidence packet is written | hermes WorkspaceBinding.evidence_output_path; _write_evidence .hermes_evidence/{job_id}/:2223; ExecutionReceipt | #768 evidence |
| execution_routing | declared orchestrator/executor/auditor path (declarative only) | foundup_job_router.py _ACTION_BACKEND_MAP:85-90 | see section 7 |

GAP this schema closes for forbidden_paths: the live Hermes BLOCKED_PATHS (:103-120)
covers .env/secrets/vendor/ but does NOT list `main.py` or `*_dae.py`. The manifest
`forbidden_paths` should ADD these per-FoundUp, and the impl slice should reconcile the
union into the guard. (Audit observation; no code changed here.)

### execution_routing block (declarative only)

```
execution_routing:
  orchestrator: openclaw
  executor: hermes
  auditor: ai_overseer
  external_agent_allowed: false
  external_agent_contract_required: true
  build_plan_source: modules/foundups/agent/src/build_plan_generator.py
  job_contract_source: modules/communication/moltbot_bridge/src/foundup_job_contract.py
```

This block DECLARES the intended path. It must NOT authorize live execution, destructive
actions, protected-path writes, gate skipping, dry-run bypass, privileged-executor
selection, or external-agent self-verification. Section 7 proves it cannot.

---

## 7. Security-Continuity (schema cannot self-authorize a bypass)

The manifest is DECLARATIVE; ENFORCEMENT stays server-side in the existing chain. Proof
that an `execution_routing` block cannot grant itself authority:

- Backend selection is server-side, not manifest-chosen. `route_foundup_job`
  (foundup_job_router.py:1077) maps `requested_action -> backend` via `_ACTION_BACKEND_MAP`
  (:85-90). A manifest declaring "executor: hermes" cannot pick a privileged executor; the
  router decides from the canonical action, and "does NOT execute the job" (:1082-1083).
- PolicyFlags are server-authored. `PolicyFlags.from_dict`
  (foundup_job_contract.py:283-324) FORCES every `_SERVER_AUTHORED_FLAGS` member
  (:200-215) to False regardless of inbound data; only `dry_run_mode` is preserved
  (:322-323). A manifest/payload cannot self-grant a passed gate or a capability token.
- Dry-run is the default and is forced. BuildPlan mode=DRY_RUN/dry_run=True
  (build_plan.py:553-556); the generator forces dry_run=True regardless of request
  (build_plan_generator.py:344-361). Hermes default dry_run=True (:555,:582);
  `HERMES_DELEGATE_ENABLED` defaults "0" (:89-95); real execution is hard-blocked
  BLOCKED_REAL_DELEGATION_NOT_IMPLEMENTED (:1843-1868).
- Destructive-action guard re-runs on every execute. `_classify_destructive_action`
  (hermes_job_executor.py:1016-1168) is fail-closed (unknown action -> D6); D4_WRITE_REPO/
  D5_EXTERNAL_SIDE_EFFECT/D6_IRREVERSIBLE are blocked
  (BLOCKED_BY_DESTRUCTIVE_ACTION_GUARD). forbidden paths via BLOCKED_PATHS (:103-120).
- Genesis gate precedes build. validate_genesis_envelope
  (openclaw_foundup_orchestrator.py:404-513); no envelope -> NOT_READY handoff (:873-879);
  the genesis validator hard-blocks `external_repo_requested` at genesis
  (ai_overseer/src/foundup_genesis/validator.py:202-206).
- Evidence is written on every terminal path (_write_evidence:2223); secrets are protected
  by path-EXCLUSION (BLOCKED_PATHS) so they never enter evidence.

POLICY_REQUIRED_SOVEREIGN_VALVE (not a runtime crutch): autonomous DRY-RUN build/test work
is code-governed and needs no human gate. NON-dry-run or out-of-policy actions require the
sovereign valve (a code-enforced policy escalation, e.g. the BuildGate approval fields
build_plan.py:304-335 / the genesis gate), NOT a blanket human-in-the-loop. This mirrors
the autonomy-boundary ruling from the AI Overseer audit (#765/#768): ordinary autonomous
work stays gate-free; only out-of-policy/credential/destructive/live actions escalate.

---

## 8. Execution Ecosystem Reconciliation (OpenClaw / Hermes / AI Overseer / External)

The 9 required questions, answered from direct reads (file:line):

1. BUILD INTENT DETECTED: `_is_explicit_build_intent`
   (openclaw_foundup_orchestrator.py:129-137) phrase-matches `_FOUNDUP_BUILD_WORDS`
   (:42-55); gated in `dispatch_foundup` (:840-911). Launch/onboard is a separate detector
   (:155-164) routed through the genesis gate first.
2. FOUNDUPJOB CREATED: `create_job` (foundup_job_contract.py:718-757) returns a typed
   `@dataclass FoundUpJob` (:332) in QUEUED state; called from orchestrator
   `_handle_build_intent` (:957-964), appended to the queue (:976). Canonical actions
   (:54-59): build_foundup, extract_foundup, validate_foundup, queue_foundup_job.
3. FOUNDUPJOB CONSUMED/DRAINED: `FoundUpJobConsumer.consume_one`
   (foundup_job_consumer.py:351) -> `route_foundup_job` (:370) -> `_dispatch_to_hermes`
   (:405) -> `execute_foundup_job` (:439). Drain: `drain_openclaw_queue_once` /
   `_with_retention` (:647/:666).
4. BUILDPLAN GENERATED: `create_build_plan_from_job` (build_plan_generator.py:310) builds a
   `BuildPlan` (build_plan.py:519) with BuildTarget/BuildStep/BuildGate/BuildEvidence; mode
   forced DRY_RUN (:344-361).
5. HERMES RECEIVE/SIMULATE/BLOCK: `HermesJobExecutor.execute`
   (hermes_job_executor.py:1536). dry_run default (:555,:582); flag off -> SIMULATED
   (:1766); dry_run -> SIMULATED (:1794); real -> BLOCKED_REAL_DELEGATION_NOT_IMPLEMENTED
   (:1843-1868); D0-D6 guard (:1016-1168); BLOCKED_* enum (:282-312).
6. AI OVERSEER AUDIT/CLEANUP: README positions it as multi-agent coordination / code-quality
   / monitoring (ai_overseer/README.md:1-14); `foundup_genesis/` is an intake VALIDATION
   gate that runs BEFORE build (validator.py:6); auto-fix uses an allowlisted argv executor
   (autofix_executor.py:157-161, only REAUTHORIZE / ROTATION_RECOVERY).
7. AI OVERSEER INTENDED TO EXECUTE BUILDS? NO. It imports none of build_plan_generator /
   build_plan / FoundUpJob / foundup_job_contract / hermes_job_executor /
   hermes_foundup_job_executor / foundup_job_router / openclaw_foundup_orchestrator (grep:
   no matches in ai_overseer). The only build-shaped surface is the "Rubik Build DAE" MCP
   stub `_execute_build_tool` (mcp_integration.py:427-429) which returns
   `{"success": True, "simulated": True}` - a pure stub (verified first-hand). Genesis
   validator even hard-blocks external builds at intake (validator.py:202-206).
8. EXTERNAL-AGENT SEAM: ABSENT in code / CATALOG-ONLY proposed. No
   `agent_capability_catalog*.json`, no `external_agent`/`partner`/`third_party` symbols
   anywhere. #764 ollama-launch catalog is decision-only and not created. The only real
   delegated-execution seam is the GATED Hermes adapter (HERMES_DELEGATE_ENABLED=0,
   dry_run, D0-D6) - blocked, not open.
9. CONTRACT BOUNDARY FOR FUTURE EXTERNAL AGENTS: any future external executor must pass
   through FoundUpJob contract -> BuildPlan -> Hermes/WRE D0-D6 guard + capability tokens +
   evidence; the genesis validator already requires an "external-build-ready gate" before
   external_repo is allowed (validator.py:202-206). Classify external agents as FUTURE_PHASE,
   untrusted-by-default, never gate-bypassers.

### Role-reconciliation table (file:line)

| Component | Current role | Build responsibility? | Evidence | Boundary decision |
|-----------|--------------|-----------------------|----------|-------------------|
| OpenClaw | intent/router/orchestrator/genesis-gate | creates+routes jobs, NOT final executor | openclaw_foundup_orchestrator.py:129-137,957-976,404-513 | keep as orchestration surface |
| Hermes | executor / dry-run builder / future gated handoff | YES, bounded executor path | hermes_job_executor.py:1536,1766-1868,1016-1168 | extend through FoundUpJob/BuildPlan |
| AI Overseer | audit / governance / codebase hygiene / genesis-validate | NO (evidence: imports no build machinery; build tool is a sim stub) | README:1-14; foundup_genesis/validator.py:6,202-206; mcp_integration.py:427-429 | keep as critic/auditor |
| WRE | runtime coordination (router/consumer) | coordinates, does not duplicate | foundup_job_router.py:1077-1083; foundup_job_consumer.py:351-439 | use existing seams |
| External agents | future/pluggable execution providers | only through explicit contract | NOT FOUND in code (FUTURE_PHASE); #764 catalog decision-only | no direct gate bypass |

### Boundaries

- AI OVERSEER DECISION RULE: no direct file:line evidence shows AI Overseer executes
  FoundUp builds, therefore AI Overseer REMAINS auditor/critic/reviewer. The impl slice
  MUST NOT create a parallel AI Overseer build path.
- NO SECOND BUILD ORCHESTRATION LAYER: the build path already exists end-to-end (OpenClaw
  -> FoundUpJob -> WRE router/consumer -> Hermes/BuildPlan). The manifest schema feeds this
  chain; it does not add an orchestrator (consistent with #769).
- EXTERNAL ECOSYSTEM: future external agents are untrusted until validated; they must use
  the FoundUpJob/BuildPlan/Hermes contract and cannot write protected paths, bypass Hermes,
  skip gates, or self-verify.
- SUBSCRIPTION vs PARTNER: (1) internal/subscription users access FoundUps-controlled
  orchestration+executor infra; (2) partner/external-agent providers bring their own
  agents/compute but plug into FoundUps contracts + evidence + gates. In BOTH,
  OpenClaw/Hermes/WRE remain the single enforcement path; AI Overseer remains
  reviewer/critic. Neither model changes the safety boundary.

---

## 9. Reuse Map (WSP 84 - extend, do not duplicate)

The impl slice should EXTEND these, not invent parallels:
- Job contract: `foundup_job_contract.py` (FoundUpJob:332, create_job:718, PolicyFlags:218,
  CANONICAL_ACTIONS:54).
- Orchestrator/intake + genesis gate: `openclaw_foundup_orchestrator.py`
  (dispatch_foundup:840, validate_genesis_envelope:404, _handle_build_intent:918).
- Router/consumer: `foundup_job_router.py` (route_foundup_job:1077, _ACTION_BACKEND_MAP:85),
  `foundup_job_consumer.py` (consume_one:351, drain:647/666).
- Build plan: `build_plan.py` (BuildPlan:519, BuildTarget:213, BuildStep:402, BuildGate:304,
  BuildEvidence:476), `build_plan_generator.py` (create_build_plan_from_job:310),
  `build_plan_executor.py` (StepExecutionResult:202, ExecutionReceipt:298).
- Hermes executor: `hermes_job_executor.py` (execute:1536, D0-D6:1016, BLOCKED_PATHS:103,
  WorkspaceBinding:148, _write_evidence:2223).
- Contract docs: `FOUNDUP_BUILD_PLAN_CONTRACT.md`, `BUILD_PLAN_EXECUTION_ADAPTER_CONTRACT.md`.

The build_contract block essentially makes per-FoundUp the values the BuildPlanGenerator
currently derives generically (target paths, allowed/blocked paths, gates, dry-run) so
generation is config-driven and auditable.

---

## 10. Recommended Implementation Slice: FOUNDUP_MANIFEST_BASELINE_IMPL_PHASE1

Scope (separate W6 slice, W10-gated): add baseline `build_contract` + `execution_routing`
blocks to the manifests of the 6 MANIFEST_PRESENT_BUT_INCOMPLETE FoundUps FIRST (gotjunk,
kosei, magadoom, antifafm, voteballots, trade), routing through the EXISTING FoundUpJob +
BuildPlan + Hermes executor (OpenClaw orchestrator, AI Overseer audit surface). No behavior
change: dry_run default, gates re-entered, no parallel AI Overseer build path. Defer
move2japan (MISSING_MANIFEST) and the NO_SAFE_BUILD_SURFACE/EXTERNAL/NOT_A_FOUNDUP entities
to their own scoped slices. First action for voteballots/trade: reconcile the
SPECIFIED_NOT_IMPLEMENTED label vs the actual src/test surface before trusting a contract.

---

## 11. Internal Review Verdict

READY. Decision-only audit; one doc. Central finding proven from source: existing
manifests are routing/product, not build/test contracts (0/16 MANIFEST_READY). 16 entities
reconciled with ground-truth src/test verification. Minimum build_contract schema +
declarative execution_routing defined and shown unable to self-authorize a gate bypass.
Execution roles reconciled: AI Overseer is auditor (not builder, evidence-backed NO); no
second build orchestration layer; external agents are contract-gated FUTURE_PHASE. Reuse
map and impl slice named. No overclaim of buildability or readiness.

---

## 12. WSP_97 Truth Boundary Checklist

Declared items: 26 - Rows: 26 - All YES

| # | Truth Boundary Checklist Item | Status | Evidence |
|---|-------------------------------|--------|----------|
| 1 | READ_ONLY_AUDIT_ONLY | YES | Only this doc added under docs/audits/architecture/; no code/test/registry/role edit |
| 2 | NO_MANIFEST_CREATED | YES | No foundup_manifest.json created/edited; schema is defined in prose only (section 6) |
| 3 | HOLOINDEX_DISCOVERY_ONLY | YES | Section 3; HoloIndex run first, LOW signal, every claim proven by direct read |
| 4 | MANIFEST_COUNTS_RECOMPUTED_NOT_ASSUMED | YES | Section 4-5; git ls-files + per-module src/test counts, not #763 labels |
| 5 | SIXTEEN_FOUNDUPS_RECONCILED | YES | Section 5; 0+6+1+2+3+4 = 16 against foundup_registry.json 16 entities |
| 6 | CLASSIFICATION_PRECEDENCE_APPLIED | YES | Section 5; precedence 1>2>3>4>5 stated and applied per entity |
| 7 | ROUTING_MANIFEST_NOT_BUILD_CONTRACT | YES | Section 4; routing schema field list, no build/test fields |
| 8 | EXISTING_MANIFEST_IS_ROUTING_NOT_BUILD | YES | Section 4; gotjunk:1-30, holo_index:1-11, shield:1-35 all lack build/test contract |
| 9 | SCHEMA_ENCODES_SECURED_GATES | YES | Section 6 required_gates + section 7; #747/#762/#768/D0-D6 tied per field |
| 10 | EXECUTION_ROUTING_DECLARATIVE_ONLY | YES | Section 6-7; routing block declares, router/_ACTION_BACKEND_MAP:85 decides |
| 11 | POLICY_REQUIRED_SOVEREIGN_VALVE_NOT_RUNTIME_CRUTCH | YES | Section 7; dry-run autonomous, non-dry-run/out-of-policy via code gate not human crutch |
| 12 | OPENCLAW_HERMES_AI_OVERSEER_ROLES_RECONCILED | YES | Section 8 role table with file:line per component |
| 13 | AI_OVERSEER_NOT_REDEFINED_AS_BUILDER | YES | Section 8 Q7; decision rule keeps AI Overseer as auditor |
| 14 | AI_OVERSEER_BUILDER_ROLE_REFUTED_OR_EVIDENCED | YES | Section 8 Q7; imports no build machinery; build tool is sim stub mcp_integration.py:427-429 |
| 15 | NO_SECOND_BUILD_ORCHESTRATION_LAYER | YES | Section 8/10; schema feeds existing OpenClaw->Job->WRE->Hermes chain (per #769) |
| 16 | MANIFEST_EXTENDS_EXISTING_FOUNDUPJOB_BUILDPLAN_HERMES_PATH | YES | Section 6/9; each field maps to FoundUpJob/BuildPlan/Hermes code |
| 17 | EXTERNAL_AGENTS_REQUIRE_CONTRACT_AND_GATES | YES | Section 8 Q9; FoundUpJob/BuildPlan/D0-D6/token + genesis external-build gate validator.py:202-206 |
| 18 | EXTERNAL_AGENTS_UNTRUSTED_BY_DEFAULT | YES | Section 8; classified FUTURE_PHASE untrusted; no seam wired (no matches) |
| 19 | EXECUTION_ROUTING_CANNOT_SELF_AUTHORIZE_GATE_BYPASS | YES | Section 7; PolicyFlags.from_dict forces server flags False:283-324; router decides backend |
| 20 | SUBSCRIPTION_AND_PARTNER_MODELS_DO_NOT_BYPASS_WRE | YES | Section 8; both models keep OpenClaw/Hermes/WRE as single enforcement path |
| 21 | NO_AUTONOMOUS_READINESS_CLAIM | YES | Section 1/5/11; 0 MANIFEST_READY; no buildability claim; voteballots/trade conflict flagged |
| 22 | CITES_PR_763 | YES | Section 2; #763 predecessor refined with build/test-contract lens |
| 23 | CURRENT_MAIN_LINE_NUMBERS_REVERIFIED | YES | All file:line read on base 3e5c00f59 this slice (registry, 9 manifests, build chain) |
| 24 | NO_CABR_READY | YES | No CABR readiness asserted; cabr_contract in manifests noted as routing field only |
| 25 | NO_PAYOUT_READY | YES | No payout readiness asserted; payout paths are D6-blocked (hermes:1107-1113) |
| 26 | NO_DAO_ACTIVATION | YES | No DAO activation asserted or implied anywhere in this audit |

---

## ModLog (WSP 22)

- 2026-06-08: W9 read-only architecture audit. Recomputed FoundUp manifest readiness
  (16 entities, ground-truth src/test verified): 0 MANIFEST_READY, 6
  MANIFEST_PRESENT_BUT_INCOMPLETE, 1 MISSING_MANIFEST, 2 NO_SAFE_BUILD_SURFACE, 3
  EXTERNAL_OR_DEFERRED, 4 NOT_A_FOUNDUP (refinement). Central finding: every existing
  manifest is a p.fMALL routing/product (or governance-spec) manifest with zero build/test
  contract fields. Defined the minimum WRE build_contract schema (10 fields + declarative
  execution_routing block), each field tied to existing machinery and a secured gate;
  proved the routing block cannot self-authorize a gate bypass. Reconciled execution roles:
  OpenClaw=orchestrator, Hermes=executor, AI Overseer=auditor (NOT builder - imports no
  build machinery, build tool is a sim stub), WRE=coordination, external agents=FUTURE_PHASE
  contract-gated. No second build orchestration layer; schema extends the existing
  FoundUpJob/BuildPlan/Hermes path (#769). Named impl slice
  FOUNDUP_MANIFEST_BASELINE_IMPL_PHASE1. Decision-only; left OPEN for W10.
