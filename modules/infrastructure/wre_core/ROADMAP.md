# WRE Core Roadmap

## Current local RSI checkpoint — 2026-09-15

Report input consistency is locally closed within **15/P1** qualification work.
Constructor scratch no longer rereads the live target. Each invocation freezes
baseline text for scratch preparation, initial proposal and cleanup; its report
records `baseline_input_sha256`. This identifies UTF-8 encoded captured text,
not raw-file bytes or authenticated program/source/oracle/environment provenance.

**96 tests pass in 2.04s.** Ten new LF/CRLF cases reproduced construction drift,
stale reused scratch and callback/interruption mutation before repair. All 26
prior function/fixture names remain; 24 definitions are unchanged. Preparation
write failure now asserts zero baseline/proposal entries. Five ten-attempt
controls preserve 50 attempts/40 candidate/five baseline evaluations; each hash
matches the evaluator's observed text and seed97 replay matches except invocation
identity. These are local simulations, with zero completed repository RSI cycles.

Source 534→537; class 285 and loop 82 stay unchanged. Tests 742→797 remain below
the 800-line general guideline, with existing infrastructure 600 review retained.
All test/new functions ≤50; no new module/skill/file/exemption. WRE maintainers
retain inherited class/loop decomposition after report contracts. Registry 1650/269
and all 1400 package members stay unchanged; no new package run claimed.
Prior mode PR1754 merged at `07a465cd`; both main workflows passed.

Re-observation retains report qualification **15/P1** (4+4+3+4): program/proposal,
oracle, environment and reader evidence must be qualified before startup display.
A baseline digest grants no launch/admission or automatic budget growth. Resource
measurement, independent retention and process/power durability remain separate.
Read `research_input_snapshot_continuation_20260915` in canonical observations;
all earlier checkpoints remain preserved.

WRE Core maintainers retain the inherited PatternMemory schema/telemetry
cohesion debt under WSP 62: the recorded ownership repair reduced the file 1,294→1,279 lines and
class 1,164→1,149. Continue decomposition through existing storage/schema owners
after their transaction contracts are established; no new exemption is added.

## RSI launch and evaluation sequence — 2026-09-15

Planning decision from 012's launch proposal, grounded at main
`af29f082e866a05bb0d05a8f32e27414f8c1939b`. The first local layer is qualified by
source inspection and the rehearsal below; the later launch wiring is a plan.

**At launch, surface the latest qualified report quickly.** Show its source,
freshness, evidence level, measured result, blockers and next WSP-15 selection.
Absent/stale/partial reports mean unknown, not success. Launch-time reading must
use the applicable read contract and must not initialize a model, launch work,
promote memory, mutate a workspace, or block the menu for a research campaign.
Existing security gates retain their own enforcement; this display is advisory.

**Run work through the existing admitted queue after startup.** Do not add another
scheduler or invoke the ROC researcher blindly from `main()`. One active campaign
per admitted scope, duplicate-launch protection and resumable receipts must be
qualified through existing queue/job owners. A queue round, an optimizer attempt
and a complete repository RSI cycle are different units.

| Existing owner | Verified source boundary | Next integration step |
|---|---|---|
| `main.py:run_wre_dashboard_preflight` and `src/dashboard_alerts.py` | Current startup health/sample warnings; may dispatch resolution events. Not an RSI benefit report or a wholly read-only path. | Extend the existing report/display seam after report-input qualification; do not infer learning from health/sample count. |
| `main.py:_reddog_run_bounded_control_rounds` | Existing resident serial/claim rounds, configured default eight, idle/failure stops and receipt persistence. Count bounds alone are not time/cost bounds. | Compile an eligible campaign into current admitted jobs; retain stop, claim and receipt owners. No new ten-round default is enabled here. |
| `src/wre_auto_researcher.py` / `src/wre_research_evaluator.py` | Isolated dry-run ROC configuration proposal/evaluation and per-run TSV; constructor attempts Qwen loading. | Terminal accounting is implemented locally; source/oracle/environment identity and reader qualification still precede launch reading. Keep its simulator judge task-specific. |
| AI Gateway model AutoResearch | Existing [benchmark and feedback contracts](../../ai_intelligence/ai_gateway/INTERFACE.md#benchmark-evidence-and-outcome-receipts) bind task family/split, model, verifier, cost and latency. | Reuse for model selection under current provider budgets/admission. A model campaign is not a generic repository editor. |
| WRE differential tests, independent slice verifier and PatternMemory | Existing [verification and retention contracts](INTERFACE.md#outcome-recording-and-retention). Production acceptance/activation and later benefit remain incomplete. | Bind accepted evidence to the exact artifact and prove a later invocation consumes it successfully; keep write/read/promotion authorities distinct. |

### Bounded campaign and report acceptance

1. Freeze the selected WSP-15/WSP-97 ticket, exact base/candidate, allowed paths,
   oracle/test corpus, held-out split, model/configuration and input/seed identities.
   Use a repository-system fixture first; preserve active FoundUps and external owners.
2. Propose **at most ten attempts** for the first admitted campaign. Enforce explicit
   total/per-attempt time, provider/token/cost and concurrency budgets as well as
   attempt count. Their values must come from the work contract before execution.
   Stop on no eligible work, cancellation, failed admission/validation, exhausted
   budget or the declared no-progress condition; preserve partial/error receipts.
3. Record requested, started, evaluated, skipped/failed, locally improved,
   independently verified and retained counts separately. Include stop reason,
   baseline/candidate metric vectors, regression results, actual resource usage,
   source/oracle/environment identities and receipt/artifact locations. Unmeasured
   cost or retained benefit is unknown, never zero or success. Persist a terminal
   report only with truthful cleanup/rollback state; a partial log is not completion.
4. Compare candidate and unchanged control using the same frozen workload, then
   evaluate held-out cases through the independent owner. Repeated test passes or
   a better training/simulation score alone cannot admit a change.
5. After authorized retention, re-open the accepted artifact/state in a later
   invocation and measure benefit on unseen cases versus the unchanged baseline.
   Verify regression and rollback behavior. This retained capability, with the
   selection/execution/validation loop, is the RSI target.
6. Re-observe and re-score after each campaign. Consider 20, then 40 or 80 only
   when useful eligible work, repeatable independently accepted benefit, regression
   checks, resource headroom and current delegated policy justify a larger ceiling.
   Launch count never changes a budget. Shrink/stop if benefit stalls; model self-
   ratings, consensus or reward counts cannot certify the increase.

### Controlled rehearsal and next action

Five separate cases use ten attempts each, the existing dry-run runner/evaluator,
model construction disabled before initialization and unique external scratch.
Only the heuristic cases use a fixed `random.Random(97)` binding. Same seed,
target, program and source produce the same proposal hashes and returned summary.

| Case | Candidate evaluations | Local outcome |
|---|---:|---|
| Unchanged control | 10 | 10 rejected; zero gain |
| Invalid-allocation control | 10 | 10 validation failures; zero gain |
| Missing-proposal control | 0 | 10 attempts, empty history and no candidate rows; zero gain |
| Seeded heuristic | 10 | 6 locally accepted / 4 rejected; simulated fitness 1.042679 → 1.375724 |
| Fresh seeded replay | 10 | Same proposals, decisions and simulated metrics |

Total: 50 attempt slots, 40 candidate evaluations, five baseline evaluations,
**zero completed repository RSI cycles**. Source bytes/mtime remain unchanged and
scratch restores in every case. Gains are same-oracle simulation results, not live
financial results, an independent judgment or retained learning. No worker was enabled.
Existing tests: 35 researcher, two injected dashboard export and four mocked queue
boundary cases pass (**41 total**); registry remains 1,650/269 quarantined.

Evidence and reproduction inputs: `launch_evaluation_continuation_20260915` in the
[canonical observations](../../../docs/roadmaps/RSI_BASELINE_OBSERVATIONS_20260913.json).
At that diagnostic checkpoint, re-scoring left OpenClaw cache ownership at
**16/P0**, ahead of report completeness **15/P1**; the current checkpoint above supersedes that selection.
Report completeness is a launch-display dependency; do not enable startup RSI to
work around it. The existing production admission and unanswered reader-policy
dependencies remain unchanged.

## Repository prioritization and closure

Use the [canonical RSI selection loop](../../../docs/operations/RSI_SWARM_DISPATCH.md#recursive-repository-prioritization-and-execution)
to re-observe, score and reconcile after every completed or blocked work item.
Extend current WRE/AgentDB/RedDog owners when runtime wiring is qualified. The
legacy `ImprovementJob.WSP15Priority` risk hints and prototype roadmap-auditor
outputs remain advisory; neither is a signed numeric allocation or dispatch grant.

## WRE master orchestrator decomposition

Execution-truth hardening extracted registry-bound executor dispatch, local
proposal inference, production admission/scanner policy, and legacy support
plugins into focused modules. The inherited coordinator fell from 1,814 to
a substantially smaller compatibility host and remains below the canonical
Python hard limit without a candidate-authored exemption. Exact current size is
verified mechanically by WSP 62 rather than frozen into roadmap prose.

Continue parity-proven decomposition in later focused slices:

- extract outcome recording and continuity breadcrumbs from
  `_execute_skill_once` (250 lines; inherited debt reduced from 329);
- extract the ReAct retry controller (113 lines; inherited debt reduced from
  122);
- extract candidate proposal construction/storage from `evolve_skill` (108
  lines; inherited debt reduced from 123);
- extract constructor configuration blocks (`__init__`, 88 lines; inherited
  debt reduced from 93);
- separate selection, evolution proposals, and telemetry;
- keep every new module/function below WSP 62 thresholds.

## Execution-truth P0 follow-ons

- implement an authenticated independent outcome evaluator;
- implement durable proposer/verifier/promoter separation and signed receipts;
- bind a generation-current read-only Holo owner adapter before re-enabling
  any generic pre-execution retrieval;
- bring CodeAct under exact WSP 95 registry, scanner receipt, captured bytes,
  typed effect receipts, and independent verification before enabling it;
- bind A/B candidates to immutable runtime artifacts before re-enabling traffic;
- build governed artifact activation and rollback without query-time Holo writes;
- prove a production end-to-end RSI canary before describing WRE as production RSI;
- add typed admission-failure audit storage without conflating it with successful
  PatternMemory outcomes.
- reconcile cached PatternMemory handle disposal/restart/handoff with the new
  per-instance creating-thread contract before concurrent multi-agent execution;
  same-handle multi-call transactions and R11 acceptance remain unimplemented;
- qualify remaining concurrent coordinator state after the merged per-call
  report and fingerprint repairs; per-mapping refresh synchronization, severity
  binding, 128-entry retention, private scanner reports and explicit dispatch
  fingerprints are locally closed in PRs #1744–#1746, not full concurrency proof.

## Code-health composition

The deterministic WSP 62 admission layer is proposal-only and intentionally
has no runtime caller. Compose it without widening authority:

- persist one immutable, module-grouped health-review packet for bounded
  no-baseline debt samples;
- obtain RedDog architect `FIX`/`DEFER`/`REJECT` determinations with canonical
  numeric WSP 15 C/I/D/Impact scores and exact allowed paths;
- convert only authenticated `FIX` determinations to the existing signed work
  order, preserving producer-to-verifier lineage;
- route through exact typed AgentDB/OpenClaw/Hermes workers and require
  independent diff/test/effect evidence before a draft PR;
- keep Nemotron, Qwen, Gemma, AutoResearch, and PatternMemory advisory until
  deterministic admission and independent verification accept their outputs;
- add incremental exact-changed-file FMAS scanning and bounded caching. The
  tracked-only producer reduced the live scan to 471 findings / 16.3 seconds,
  but that is still too expensive per prompt or per worker;
- replace the qualitative `WSP15Priority` compatibility object with a real
  signed numeric WSP 15 allocation receipt at the architect boundary.

Dead/orphan/duplicate evidence is a separate lane. Current legacy detectors
are not deletion authorities; first build one receipt-bound import/entrypoint/
runtime/registry/Git evidence graph and held-out false-positive corpus, then
perform WSP 79 preservation before archive or consolidation.

## Autonomous slice verifier decomposition

Decompose `wre_autonomous_slice_verifier_runtime.py` without weakening its
independent authority, evidence, exact-SHA, or receipt-chain checks. The
temporary exact no-growth exemption remains a ceiling, not permission to add
logic to the inherited coordinator.

## FoundUp job router and consumer WSP62 decomposition

The create-route prerequisite now isolates its routing decision in
`src/foundup_job_route_decision.py`; every function in that module and the
public `route_foundup_job` entrypoint is at or below 75 lines.

Remaining inherited WSP 62 debt is recorded with exact, non-ratcheting
ceilings in `wsp_62_exemptions.yaml`:

- Split envelope, evidence-reference, live-mode, and compute-budget validation
  out of `src/foundup_job_router.py`.
- Split Hermes dispatch, dry-run context attachment, and queue-retention
  orchestration out of `src/foundup_job_consumer.py`.
- Remove each function exemption when its extracted replacement is at or below
  75 lines, then remove the file exemption when the host is at or below the
  canonical file threshold.

Target: complete the decomposition before the temporary exemptions expire on
2026-09-30, without widening any recorded ceiling.

## FoundUp model-capability projection follow-up

Phase 1 projects existing route and runtime-binding authority into
`validate_foundup` only. Build and extract profiles intentionally keep all
capability requirements unspecified, and no consumer selection or binding
path has been added.

Before expanding consumption beyond validation:

- designate a production authority for modality, tool, structured-output,
  reasoning, selection-mode, and panel-limit requirements;
- define the selection-receipt handoff without letting a projection select,
  bind, call a provider, or mutate catalog/runtime state;
- add action-specific admission tests and preserve exact receipt lineage;
- keep `model_preference` limited to cost-class intent.

The injected runtime-binding resolver remains a trust anchor. A production
adapter must read the persisted result of the existing outside-repository
confined artifact-supply workflow. Detecting a malicious resolver that returns
a different self-consistent receipt requires a separately authorized
provenance/signature contract and is outside Phase 1.

## WRE documentation archival

`README.md` and `INTERFACE.md` now describe current truth below the Markdown
threshold. `ModLog.md` and `tests/TestModLog.md` remain required append-only
audit histories under non-blocking archival advisories. Archive them through an
approved retention workflow without losing lineage.
