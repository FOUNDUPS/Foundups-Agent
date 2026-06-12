# WSP Multi-Agent Evolution Audit -- Phase 1 (Decision-Only)

- Slice: WSP_MULTI_AGENT_EVOLUTION_AUDIT_PHASE1
- Base SHA: 3339d34c4
- Method: WSP_00 (Zen State) / WSP_50 (pre-action verification) / WSP_97 (Truth Boundary) / COTCAR
- Status: decision-only architecture audit. NO runtime / source / test changes. No fixes.
- Grounding: 5 read-only code-auditors (file:line cited), 6 web-verified external researchers,
  1 adversarial second-brain critic (verdict: anySecondBrain=false, BLUEPRINT_SOUND).

Evidence-class key:
- [SV] Session-verified across PRs #775-#790 (out-of-band run results carried from session).
- [AV] Audit-verified: a code-auditor read+cited the code AND the adversarial critic re-confirmed it; W9 (this slice) ALSO re-ran the grep/git-show against base 3339d34c4.
- [AA] Agent-asserted: cited but line numbers may have drifted; W9 spot-checked the cite below.

Re-verification note (W9): Every load-bearing repo claim in Section 2 was re-run by W9 via
`git show 3339d34c4:<path>` / blob grep at audit-write time. The four high-load-bearing external
claims (LangGraph BSP-barrier + InvalidUpdateError; "checkpoints are not rollback"; merge-queue
speculative+bisect+eject; A2A opaque-no-shared-state) were web-spot-checked via their cited URLs.

Sibling audits (cross-link):
- [OPENCLAW_HERMES_WRE_EXECUTION_CHAIN_AUDIT_PHASE1.md](OPENCLAW_HERMES_WRE_EXECUTION_CHAIN_AUDIT_PHASE1.md)
- [DURABLE_EXECUTION_SPIKE_PHASE1.md](DURABLE_EXECUTION_SPIKE_PHASE1.md)
- [FOUNDUPS_WORK_LEDGER_BRAIN_CURRENT_STATE_AUDIT_PHASE1.md](FOUNDUPS_WORK_LEDGER_BRAIN_CURRENT_STATE_AUDIT_PHASE1.md)
- [EXTERNAL_SWARM_OPENCLAW_HERMES_CURRENT_STATE_RECONCILIATION_PHASE1.md](EXTERNAL_SWARM_OPENCLAW_HERMES_CURRENT_STATE_RECONCILIATION_PHASE1.md)

---

## 1. Executive Summary

The execution spine already exists and is PROVEN; the threat is existing duplicate orchestrators,
not missing infrastructure.

(1) The one-way seam create -> queue -> drain -> resolver -> Hermes(SIMULATED) is green [SV], resting
on three immovable single-authority facts re-verified at base:
- source_authority cannot self-promote: `request_promotion` ALWAYS raises `NotImplementedError`
  (modules/foundups/agent/src/source_authority.py:167); the builder-constant `SOURCE_AUTHORITY =
  "monorepo_poc"` ignores any declared value.
- one AST-enforced module_path resolver: `NO_SECOND_MODULE_PATH_RESOLVER` AST scan +
  `FAIL_TOKEN_CROSS_FOUNDUP_MISMATCH` reject a forged cross-FoundUp path
  (modules/foundups/agent/src/module_path_resolution.py:21,115,375-383).
- the #771/#773 manifest validator is the lone canonical authority: `validate_manifest_file` is
  imported by both builder and resolver and explicitly "imports validator; does not reimplement"
  (context_bundle_builder.py:75,93-95; module_path_resolution.py:67-68).

(2) FoundUps LEADS on three axes that external research holds up as best practice:
git-worktree fan-out [AV], evidence receipts (observable-ignore + fail-token taxonomy +
authority-laundering denylist) [SV], and event-sourcing (FAM = Temporal/OpenHands philosophy,
already built) [AV].

(3) The real danger is internal: 4-5 competing orchestrators run as peers; WREMasterOrchestrator
declares primacy ("This is THE orchestrator", wre_master_orchestrator.py:22) but is NOT wired to
the FoundUpJob seam -- grep for `FoundUpJob|drain|_FOUNDUP_JOB_QUEUE` in that file returns ZERO
matches [AV].

(4) Two active concurrency hazards: queue split-authority TOCTOU [AV] and policy_flags in-place
mutation [AV]. Current thread-safety is accidental (process isolation per worktree + GIL); it is
"NOT GUARANTEED for multiple agents in the same process." These are DOCUMENTED here, NOT fixed.

Smallest safe path: consolidate (WSP 65), do not construct. Add three thin in-spine layers (durable
receipt log, lane partition, speculative-merge land-gate); ADAPT three external patterns; BUILD
almost nothing net-new; REJECT every external orchestrator + every competing internal orchestrator.
Real execution stays BLOCKED. Critic verdict: anySecondBrain=false, BLUEPRINT_SOUND.

The "competing brain" framing in this document is an ARCHITECTURAL-RISK JUDGMENT (multiple files
hold orchestration authority and could diverge), NOT a runtime-observed failure. No multi-agent
concurrent run was executed; the present PoC is single-drain and dry-run.

---

## 2. WSP 97 Truth Boundary Report

Classification counts across the audited surface: PROVEN 12, IMPLEMENTED 30, PLANNED 5,
HYPOTHETICAL 1 (47 components across 5 internal lanes).

Epistemic caveats:
- Duplicate-authority findings are HIGH confidence: the critic re-verified the two load-bearing
  races, and W9 re-ran the greps against base 3339d34c4.
- The "competing brain" characterization is an architectural-risk judgment, not a runtime failure.
- Several [AA] line numbers were spot-checked by W9; corrections are noted inline.

Load-bearing repo claims (all re-verified by W9 at base 3339d34c4):

| # | Claim | Evidence at base 3339d34c4 | Class |
|---|---|---|---|
| 1 | Seam green end-to-end dry-run | test_operational_wre_monorepo_poc_vertical_proof.py has exactly 3 test methods (lines 208/237/387); "3 passed" run carried from session | [SV] |
| 2 | source_authority cannot self-promote | source_authority.py: `request_promotion` raises `NotImplementedError` (line 167); builder-constant `monorepo_poc`, declared value ignored | [SV] |
| 3 | Single AST-enforced module_path resolver | module_path_resolution.py:21 (`NO_SECOND_MODULE_PATH_RESOLVER`), :115 (`FAIL_TOKEN_CROSS_FOUNDUP_MISMATCH`), :375-383 forged-path reject | [SV] |
| 4 | #773 validator is lone authority | `validate_manifest_file` imported by builder (context_bundle_builder.py:93-95, "does not reimplement" :75) AND resolver (module_path_resolution.py:67-68) | [SV] |
| 5 | dry_run default; D4+ fail-closed; BLOCKED_REAL_DELEGATION | hermes_job_executor.py: `dry_run: bool = True` (:358), `BLOCKED_REAL_DELEGATION_NOT_IMPLEMENTED` (:300), D4/D5/D6 BLOCKED Phase 1 (:1042-1053), unknown action -> D6 (:1071-1072) | [SV] |
| 6 | PolicyFlags.from_dict untrusts deserialized flags (#746) | foundup_job_contract.py: `from_dict` (:284) forces gate + 4 capability_token_* flags to False; server-authored, not via untrusted path (:287-319) | [SV] |
| 7 | Worktree-per-agent substrate | docs/GIT_WORKFLOW_0102.md exists; `git worktree list` is live environment state (currently 15 worktrees, was "13" at draft time -- count is environment-dependent, not SHA-pinned) | [AV] |
| 8 | FAM dual-write concurrency-safe | fam_daemon.py: JSONL+SQLite dual-write (:311), `event_id/sequence_id/dedupe_key ... UNIQUE NOT NULL` (:323-325), `threading.Lock()` (:360), `PRAGMA journal_mode=WAL` (:379) | [SV] |
| 9 | 4-5 competing orchestrators exist as peers | All present at base: wsp_orchestrator.py; wre_master_orchestrator.py; holo_index/.../autonomous_refactoring.py; holo_index/.../qwen_orchestrator.py; orchestration_switchboard.py; agent_permission_manager.py; block_orchestrator.py | [AV] |
| 10 | WREMaster declares "THE orchestrator" but is NOT wired | wre_master_orchestrator.py:22 "This is THE orchestrator"; grep `FoundUpJob|drain|_FOUNDUP_JOB_QUEUE` in that file = ZERO matches | [AV] |
| 11 | Queue split-authority TOCTOU | `remove_jobs_by_id` exported in openclaw_foundup_orchestrator.py:240; consumer reads `get_job_queue()` then `drain_jobs(queue)` then `remove_jobs_by_id(...)` non-atomically (foundup_job_consumer.py:897,914,930) | [AV] |
| 12 | policy_flags in-place mutation | hermes_job_executor.py: `_writeback_token_verdict` mutates `job.policy_flags.*` in place (:1302-1305, docstring "mutated in place" :1287); called (:1616) THEN destructive guard reads the mutated flags (:1619 -> :1227-1232) | [AV] |
| 13 | _FOUNDUP_JOB_QUEUE non-durable in-memory list | openclaw_foundup_orchestrator.py:39 `_FOUNDUP_JOB_QUEUE: List[FoundUpJob] = []`; :40 docstring "Production will use persistent queue" | [AA] -> confirmed at exact cited lines |

Correction note (claim 9): the draft tagged `block_orchestrator` as "PLANNED". At base it EXISTS as
a real file (modules/infrastructure/shared_utilities/block_orchestrator/src/block_orchestrator.py),
so it is counted here as an additional present orchestrator surface, not a planned one.

Correction note (claim 6b): the draft phrase "Gates name-lists not pass-state" overstates the data
shape. The verifiable fact is that gate fields are server-authored booleans (e.g.
`security_gate_passed: bool = False`) and `PolicyFlags.from_dict` (#746) FORCES every gate and
capability_token flag to False on deserialization so a job payload cannot self-authorize. The
load-bearing security property (untrust-on-deserialize) holds; the "name-list" wording is dropped.

---

## 3. Current FoundUps Architecture Map

Three layers:

(a) THE PROVEN SPINE [SV]: FoundUpJob contract -> in-process queue -> FoundUpJobConsumer drain ->
shared module_path resolver + #773 validator + source_authority constant -> HermesJobExecutor
(dry_run=True, SIMULATED). One-way authority: creation -> validated drain -> execution.

(b) COMPETING ORCHESTRATORS (second-brain risk) [AV]: WSPOrchestrator,
AutonomousRefactoringOrchestrator, OrchestrationSwitchboard, QwenOrchestrator,
WREMasterOrchestrator (declares primacy, unwired), plus block_orchestrator and
agent_permission_manager. None is wired to the FoundUpJob seam; several hold their own
input()/supervision loops.

(c) PROVEN MULTI-AGENT SUBSTRATE FoundUps leads on [SV]/[AV]: git worktree-per-agent isolation;
pure ContextBundle builder + resolver + validator (no singleton state on the authority path);
FAM dual-write event store (JSONL truth + SQLite WAL index).

Supports multi-agent TODAY: worktree isolation; ContextBundle/resolver/validator (pure functions);
FAM (locked, deduped, WAL).
Assumes single-agent TODAY: the queue (no lane/lock); the drain (sequential for-loop, no
async/threading imported); evidence paths (job_id-only, collide if job_id not globally unique);
HoloIndex/PatternMemory singletons (read-derived but unlocked); every standalone orchestrator.

---

## 4. External Architecture Comparison (web-verified)

All six external systems -> ADAPT, with one explicit carve-out: REJECT the A2A opaque-no-shared-state
model. Convergent lesson across the field: separate a durable append-only log (one truth,
reconstructed by replay) from the decision function; and separate work-isolation from
merge-serialization.

- LangGraph [confidence: web-verified]: Pregel/BSP superstep barrier; writes from one superstep
  become visible only at the next; concurrent single-writer writes without a reducer raise
  `InvalidUpdateError`; interrupt()/Command(resume=) human gate. Carry: checkpoints are save-points.
  (Sources: docs.langchain.com/oss/python/langgraph/durable-execution;
  deepwiki.com/langchain-ai/langgraph/3-core-execution-system;
  reference.langchain.com/python/langgraph/types/interrupt -- BSP barrier + InvalidUpdateError
  web-verified by W9 at deepwiki.)
- AutoGen [web-verified]: actor runtime; single shared transcript; typed Handoff control token;
  dual human-gate (UserProxyAgent / ExternalTermination); OpenTelemetry span trail. Standard chat
  Teams are turn-sequential. ADAPT spine + handoff + human gates; constrain emergent LLM routing.
  (Sources: microsoft.github.io/autogen/stable -- human-in-the-loop, termination, telemetry.)
- CrewAI [web-verified]: Crews + Flows; task.context = fan-in DAG barrier; typed Flow state;
  guardrails. REJECT LLM-judged validation gates; note idempotency/rollback gap (issue #5802).
  (Sources: docs.crewai.com; github.com/crewAIInc/crewAI/issues/5802.)
- OpenHands [web-verified]: immutable event-stream / event-sourcing single truth;
  WAITING_FOR_CONFIRMATION; ConfirmationPolicy x SecurityAnalyzer; sandbox/CoW overlays. Adopt as a
  tool under the WRE spine; do NOT run AgentController as a second brain.
  (Sources: arXiv:2407.16741; arXiv:2511.03690; docs.openhands.dev.)
- MCP + A2A [web-verified]: MCP human-consent tool-gate ("untrusted unless validated") + Agent-Card
  capability/auth manifest -> ADAPT. A2A opaque-no-shared-state -> REJECT: A2A agents collaborate
  "without needing access to each other's internal state, memory, or tools", which collides with
  single-source-of-truth. Reuse only the Agent-Card/auth + task-lifecycle envelope.
  (Sources: modelcontextprotocol.io/specification; a2a-protocol.org/v0.2.5/specification --
  opaque-no-shared-state web-verified by W9.)
- DAG + git-multiagent [web-verified]: merge-queue speculative + batch + bisect + eject; Temporal
  saga compensation + replay-skip idempotency + event-history/deterministic replay; Dagster
  derive-deps-from-artifact-IO. ADAPT the land-gate and event-log/saga patterns.
  (Sources: temporal.io docs; mergify merge-queue articles; github.com merge-queue docs --
  speculative+batch+bisect+eject web-verified by W9.)

Verified caution to carry forward: checkpoints are save-points, NOT transactional rollback; resume
re-executes the node from its start (completed tool results may be replayed, side effects are not
auto-undone). Any future real execution therefore requires saga compensation + per-step idempotency.

---

## 5. Multi-Agent Gap Analysis

Capability | FoundUps current (class) | External best | Recommendation

1. Single execution spine | PARTIAL/CONTESTED: WREMaster claims "THE ONE" [IMPLEMENTED] but 4-5 competing brains run | one wired spine | BUILD (WSP 65 consolidation)
2. Task graph / decomposition | WEAK: decomposition implicit in route_foundup_job (pure fn) [PROVEN] | LangGraph topology-as-decomposition | BUILD (parent_job_id / produces_artifact on FoundUpJob; developer-authored, no LLM planner)
3. Agent lanes / work isolation | PROVEN at git layer (worktree-per-agent) [PROVEN]; queue has no lane metadata | path-scoped lanes (merge-queue) | ADAPT (lane_id partition, ~100 LOC, backward-compatible)
4. Dependency graph | WEAK/ABSENT: FIFO append-order only | Dagster asset-keyed deps | ADAPT (infer from manifest IO; no second DAG DB)
5. Work / file ownership | PROVEN at git layer but MANUAL contract | worktree fan-out | ADAPT (pre-commit hook asserting worktree-per-agent; per-job file-scope)
6. Conflict detection | MANUAL/ABSENT; resolver catches module_path only [IMPLEMENTED] | reducer-conflict fail-fast + speculative CI | ADAPT (fix policy_flags race FIRST, then layered textual+semantic+determinism checks)
7. Merge coordination | MANUAL dual-remote sync, human-resolved [IMPLEMENTED] | merge-queue speculative+bisect+eject | ADAPT (in-spine land-gate; drop backup remote)
8. Shared memory / state | STRONG but UNSAFE under concurrency: FAM safe, singletons unlocked | single State (LangGraph/CrewAI) | ADAPT (lock singletons; JSONL = truth)
9. Agent comms bus | PARTIAL: Switchboard routes signals, competes as authority [IMPLEMENTED] | Temporal signals + indirect git comms | ADAPT (route via FAM receipts; REJECT A2A opaque RPC)
10. Checkpointing | PARTIAL: checkpoint_state per job_id [IMPLEMENTED] | Temporal event-history / OpenHands event-sourcing | ADAPT (lane-prefixed job_id on FAM)
11. Rollback | WEAK: git revert + dry_run default only | Temporal saga compensation | ADAPT (saga, later; never-corrupt-spine first)
12. Evidence receipts | STRONG -- FoundUps LEADS [PROVEN] | (FoundUps ahead) | REJECT external store; only add lane_id tag
13. WSP compliance gates | STRONG -- FoundUps LEADS: genesis + D0-D6 fail-closed + token validation [IMPLEMENTED] | MCP consent-gate / OpenHands ConfirmationPolicy | REJECT external (code-pinned exceeds LLM-judged)
14. Sovereign approval | PARTIAL: dry_run default + D4+ block = strong implicit gate [PROVEN] | LangGraph interrupt / OpenHands WAITING_FOR_CONFIRMATION | ADAPT (one compiled BLOCKED_AWAITING_SOVEREIGN gate)
15. Scheduling | WEAK: synchronous sequential drain [IMPLEMENTED] | Temporal multi-worker | ADAPT (QueueManager + ThreadPool per lane, ~20 LOC)
16. State durability | MIXED: FAM durable; in-memory queue is not [IMPLEMENTED] | event-history persistence | ADAPT (persist queue to FAM/SQLite)

---

## 6. Recommended Multi-Agent Blueprint

One spine, many front-doors. Zero new orchestrators. Every agent is a stateless worker in an
isolated worktree that PUSHES jobs/receipts; the consumer is the only drainer. 15 components, all
critic-CLEAN (anySecondBrain=false). The two net-new BUILDs carry non-blocking cautions:
the dependency graph MUST stay inference-over-manifests (else it becomes a 2nd scheduling authority);
the merge coordinator MUST stay decision-only / dry-run-gated (else it becomes a BLOCKER 2nd brain).

| # | Component | builds_on_existing | second_brain_risk control | class | rec |
|---|---|---|---|---|---|
| 1 | Puzzle-board / task-graph (the FoundUpJob queue IS the board) | _FOUNDUP_JOB_QUEUE + FoundUpJob contract | reuse ONE queue + ONE typed job; no parallel task store; PolicyFlags.from_dict untrusts payload | IMPLEMENTED | ADAPT |
| 2 | Agent lanes (partition of the existing queue) | drain_jobs + worktree-per-agent | lane_id is metadata only; partitions of ONE queue, not separate authorities | PLANNED | ADAPT |
| 3 | Dependency graph (artifact/asset-keyed, derived) | ContextBundle provenance + manifest build_contract | inferred from manifests (Dagster pattern), no second graph DB | PLANNED | BUILD |
| 4 | Work ownership (job state machine + lease) | FoundUpJob QUEUED->RUNNING + idempotency_key | ownership lives IN the job; RUNNING->RUNNING rejected | PROVEN | ADAPT |
| 5 | File ownership (worktree isolation) | git worktree-per-agent | git is the single source; add pre-commit hook (no second registry) | IMPLEMENTED | ADAPT |
| 6 | Conflict detection (textual+semantic+determinism) | resolver cross-FoundUp/case-variant defense | structural fail-fast at one barrier (InvalidUpdateError pattern), not a heuristic arbiter | IMPLEMENTED | ADAPT |
| 7 | Merge coordinator (speculative+batch+bisect+eject land queue) | NONE in-repo (net-new) | serialization layer on ONE spine; decision-only; remove backup remote | HYPOTHETICAL | BUILD |
| 8 | Shared memory (one queue + one ContextBundle) | ContextBundle + PatternMemory + HoloIndex | ONE bounded bundle forward, not a blackboard; lock singletons | PROVEN | ADAPT |
| 9 | Agent comms bus (artifact/receipt-mediated) | FAM dual-write event store | async receipt-mediated via ONE FAM log; REJECT A2A opaque RPC | IMPLEMENTED | ADAPT |
| 10 | Checkpointing (durable append-only log + replay) | Phase 1C checkpoint + .hermes_evidence + FAM | one append-only log; replay-skip; lane-prefix evidence path | IMPLEMENTED | ADAPT |
| 11 | Rollback (saga + never-corrupt-spine + git revert) | dry_run=True default + git revert | merge-queue eject so spine never advances bad; per-step compensation | PLANNED | ADAPT |
| 12 | Evidence receipts (audit substrate) | ConsumerResult/DrainResult + observable-ignore + FAIL_TOKEN | receipts observational only; add lane_id (~10 LOC) | PROVEN | ADAPT |
| 13 | WSP compliance gates (genesis + D0-D6 + token) | genesis gate + destructive guard + capability token | stateless pure validators; FIX policy_flags in-place mutation (return request-scoped verdict) | IMPLEMENTED | ADAPT |
| 14 | Sovereign approval (compiled human-gate interrupt) | dry_run default + existing supervision loops (to consolidate) | ONE compiled interrupt at land; request_promotion stays NotImplementedError | PLANNED | ADAPT |
| 15 | Queue-ownership consolidation + REJECT standalone orchestrators | FoundUpJobConsumer as sole queue owner | OpenClaw PUSH only; consumer sole drainer/remover; fold orchestrators to WRE plugins (WSP 65) | IMPLEMENTED | BUILD |

---

## 7. Ordered Implementation Roadmap

Immediate Foundation (before any 2nd lane):
- Formalize work/file ownership as data, not a doc contract (pre-commit hook asserting
  worktree-per-agent; receipted, fail-closed).
- Build a lane registry as the single authority for "which lane owns which work" (lane_id ->
  declared file/module scope), referencing the #773 validator, never duplicating it.
- Add conflict detection on the queue BEFORE concurrency exists: promote `_FOUNDUP_JOB_QUEUE`
  (openclaw_foundup_orchestrator.py:39) into an explicit QueueManager owning append+remove under a
  lock with atomic classify-remove (closes the TOCTOU).
- Consolidate queue mutation authority: OpenClaw PUSH only; WRE consumer owns POP/remove (remove
  `remove_jobs_by_id`/`clear_job_queue` as orchestrator-side exports).
- Enforce idempotency at job creation (the deterministic idempotency_key exists but OpenClaw never
  checks it before append).
- Stamp evidence paths with lane_id (get_evidence_output_path keys only on job_id today).

Near-Term (one lane -> many dry-run lanes; the dry-run boundary is sacred):
- Remove in-place job mutation: return token verdict as request-scoped metadata instead of mutating
  `job.policy_flags` (fixes the policy_flags race).
- Parallelize drain per-lane, not globally (one consumer per lane over a lane-partitioned queue);
  adopt LangGraph's BSP superstep barrier so a lane's writes only become visible at the next barrier.
- Route multi-lane output through a speculative merge queue (validate projected output against
  main+ahead+self; batch-with-bisect-and-eject) BEFORE it touches the spine, even in dry-run.
- Layer conflict detection: (1) textual git conflict at worktree merge, (2) semantic conflict via CI
  on the projected post-merge branch, (3) resolver/contract conflict.
- Add a replayable event log as the cross-lane single source of truth, reusing FAM's proven
  dual-write (JSONL + SQLite WAL + dedupe_key UNIQUE + lock-protected sequence).

Long-Term (before any real execution):
- Build the sovereign valve: the only thing that can flip dry_run -> real, as a receipted 012 event
  (OpenHands ConfirmationPolicy x SecurityAnalyzer + LangGraph interrupt admission gate).
- CABR readiness as a hard precondition: `request_promotion` stays `NotImplementedError` until the
  multi-WSP human gate (WSP 29 CABR, WSP 103 federation/OPO) is satisfied.
- Harden D0-D6 for real execution: D0-D3 "allowed" must mean allowed-with-compensation.
- Implement transactional rollback + never-corrupt-the-spine (saga compensation + merge-queue eject
  + Temporal-style worker/version pinning).
- Consolidate the orchestration brains to ONE spine (WSP 65): fold WSPOrchestrator,
  AutonomousRefactoringOrchestrator, OrchestrationSwitchboard, QwenOrchestrator into WRE plugins;
  wire WREMasterOrchestrator to the FoundUpJob seam or demote its "THE orchestrator" claim.
- Formalize filesystem-level isolation + copy-on-write overlays for real edits; replace dual-remote
  with branch protection + required status checks.

Forbidden:
- A 6th orchestrator or a per-FoundUp WRE; any parallel-lane drainer that creates/drains
  `_FOUNDUP_JOB_QUEUE` independently of the WRE consumer.
- The A2A opaque-no-shared-state model (collides with single-source-of-truth).
- Any manifest / context bundle / job payload / lane self-declaring lifecycle stage, module_path,
  or validation verdict (already code-pinned).
- Flipping dry_run off, weakening `request_promotion`'s NotImplementedError, or allowing D4+ real
  execution before the sovereign valve + CABR readiness + saga rollback exist.
- Scaling concurrency on the in-memory queue's accidental GIL/process-isolation safety.
- Checkpoints-as-rollback for side effects; LLM-judged validation as a merge gate.
- Duplicating the module_path/manifest resolver or the pattern-memory store.

---

## 8. Top 10 Architectural Risks

These risks are DOCUMENTED, NOT FIXED in this slice (decision-only). The first execution follow-up
is WRE_MULTI_AGENT_CONCURRENCY_RISK_CONFIRMATION_PHASE1 (confirm queue TOCTOU + policy_flags race
against current main, then implement ONLY confirmed fixes).

1. policy_flags in-place mutation (active) [AV]: `_writeback_token_verdict` mutates `job.policy_flags`
   in place (hermes_job_executor.py:1302-1305), then the destructive guard reads the mutated flags
   (:1619 -> :1227-1232); a shared `job` across lanes could flip each other's guard input.
2. Queue split-authority TOCTOU [AV]: read `get_job_queue()` -> `drain_jobs(queue)` ->
   `remove_jobs_by_id(...)` is non-atomic (foundup_job_consumer.py:897,914,930) against the shared
   global `_FOUNDUP_JOB_QUEUE`.
3. Accidental thread-safety [AV]: safety is incidental to worktree-per-agent being separate
   processes (process isolation + GIL); NOT GUARANTEED for multiple agents in one process.
4. Orchestrator proliferation [AV]: 4-5 competing authorities make autonomy unverifiable across
   brains.
5. Non-durable work queue [AA]: `_FOUNDUP_JOB_QUEUE` is an in-memory list (line 39-40,
   "Production will use persistent queue").
6. Evidence path collision [AA]: evidence keyed on job_id only; two lanes with a colliding job_id
   overwrite each other's checkpoint evidence.
7. Unlocked HoloIndex/PatternMemory singletons [AV]: read-derived but not lock-protected for
   concurrent reuse.
8. Manual conflict/merge coordination + dual-remote divergence [AV]: no automated collision
   detection; merges are human-resolved.
9. WREMaster declares primacy but isn't wired [AV]: naive activation would add a 5th brain instead
   of consolidating.
10. Checkpoints mistaken for rollback [web-verified]: a Phase-2 risk; resume re-executes node start,
    side effects not auto-undone.

Second-orchestrator risks specifically identified (do NOT construct any of these):
- Activating WREMasterOrchestrator without wiring it to the FoundUpJob seam (becomes a 5th brain).
- Any new parallel-lane drainer mutating `_FOUNDUP_JOB_QUEUE` outside the consumer.
- A dependency-graph engine that stores deps instead of inferring them from manifests.
- A merge coordinator that owns work (must stay decision-only / dry-run-gated).
- A2A-style opaque agents with private state.

---

## 9. Top 10 Strategic Opportunities

1. Worktree fan-out already SOTA [AV] -- the hard isolation problem is solved.
2. Evidence model leads the field [SV] (observable-ignore + FAIL_TOKEN taxonomy + authority-laundering
   denylist).
3. FAM = Temporal/OpenHands event-sourcing already built [AV].
4. Lane partition ~100 LOC, backward-compatible.
5. Drain parallelization ~20 LOC (QueueManager + ThreadPool per lane).
6. WSP 65 consolidation turns 5 liabilities into plugins.
7. Sovereign valve upgrades doctrine to a compiled gate.
8. Merge-queue land-gate is the canonical scale pattern (testable dry-run first).
9. Gates already exceed LLM-judged guardrails [SV].
10. Drop the backup remote -- removes divergence risk for zero loss.

---

## 10. WSP Compliance Review

- WSP 65 (component consolidation) is the largest open gap: doctrine present (WREMaster declares
  "THE orchestrator"), wiring absent.
- WSP 50/64 (pre-action verification / violation prevention) strongly upheld by
  resolver/validator/source-authority [SV]; extend to lane-scope.
- WSP 97 (truth boundary): this audit complies -- classes separated, nothing promoted, no code
  changed.
- WSP 60 (memory) compliant; needs singleton locks for concurrent reuse.
- WSP 22 (ModLog) aligned (this slice adds one root entry).
- WSP 3/49 (domains/structure): orchestrators are scattered across infrastructure/, ai_intelligence/,
  holo_index/, communication/; consolidation improves domain hygiene.
- No new WSP needed (WSP 64 prefer-enhance).

Bottom line: the minimum safe architecture is mostly subtraction -- consolidate 5 orchestrators into
one wired spine (WSP 65), fix two concrete races, partition one queue, add one durable log + one
land-gate. ADAPT three external patterns; BUILD two thin layers; REJECT every external orchestrator
+ A2A opaque state. Real execution stays BLOCKED. FoundUps is closer to safe thousand-agent scale
than a greenfield build because the hard parts (evidence, isolation, single-authority resolution,
event-sourcing) are already PROVEN; the work is wiring and hardening, not invention.

---

## WSP_97 Truth Boundary Checklist

Declared rows: 11

| # | Truth Boundary Checklist Item | Status | Evidence |
|---|---|---|---|
| 1 | DECISION_DOC_ONLY_NO_CODE_CHANGE | YES | Only three docs touched (this audit, ROADMAP anchor, root ModLog); zero .py/tests/runtime edits; git diff --name-only lists exactly the three docs |
| 2 | LOAD_BEARING_REPO_CLAIMS_REVERIFIED_AT_3339d34c4 | YES | All 13 claims in Section 2 re-run by W9 via git show 3339d34c4:<path> / blob grep at audit-write time; cite lines confirmed (e.g. claim 10 grep = ZERO, claim 12 :1616->:1619, claim 13 :39-40) |
| 3 | EXTERNAL_CLAIMS_WEB_SPOTCHECKED | YES | LangGraph BSP+InvalidUpdateError (deepwiki), checkpoints-not-rollback (diagrid), merge-queue speculative+bisect+eject (mergify/github), A2A opaque-no-shared-state (a2a-protocol.org) all fetched and confirmed |
| 4 | CLASSIFICATION_TAGS_APPLIED | YES | Every major claim tagged PROVEN/IMPLEMENTED/PLANNED/HYPOTHETICAL (Sections 2,5,6); evidence-class [SV]/[AV]/[AA] applied per claim |
| 5 | CONCURRENCY_RISKS_DOCUMENTED_NOT_FIXED | YES | Section 8 lists Top-10 risks with explicit "DOCUMENTED, NOT FIXED" banner and names WRE_MULTI_AGENT_CONCURRENCY_RISK_CONFIRMATION_PHASE1 as the first execution follow-up |
| 6 | SECOND_ORCHESTRATOR_RISKS_IDENTIFIED | YES | Section 8 "Second-orchestrator risks specifically identified" + Section 3(b) competing-orchestrator layer + claim 10 (WREMaster unwired) |
| 7 | ROADMAP_ANCHOR_LINK_NOT_DUPLICATION | YES | ROADMAP.md edit adds a short anchor sub-section linking to this audit + ordered next slices; the audit body is NOT pasted into ROADMAP |
| 8 | NO_NAVIGATION_CHANGE | YES | NAVIGATION.py not touched; out of scope this slice; git diff confirms it is not in the changed set |
| 9 | NO_HOLOINDEX_ARTIFACTS_COMMITTED | YES | No HoloIndex DB/index, AGENT_CLI_CATALOG.md, command_rolodex.json, or .claude/** staged; only the three in-scope docs |
| 10 | ASCII_CLEAN | YES | Audit doc byte-checked NON_ASCII 0; ROADMAP added lines and ModLog entry contain 0 non-ASCII bytes |
| 11 | FILE_SCOPE_EXACTLY_THREE | YES | git diff --cached --name-only = exactly docs/audits/architecture/WSP_MULTI_AGENT_EVOLUTION_AUDIT_PHASE1.md, modules/infrastructure/wre_core/wre_master_orchestrator/ROADMAP.md, ModLog.md |
