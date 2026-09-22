# WRE Core Roadmap

## Consumer dry-run isolation qualification — 2026-09-21

The15/P1 qualification at main `e1c64d00674f1205ec20ca460c8b963fb34b6daa`
reached eight actual-module control-flow cases: fresh, warmed dry, warmed non-dry
and warmed controlled executors, each with consumer dry-run True/False. Two
force-dry configurations violate the documented promise: a True consumer reaches
an executor with `dry_run=False`, or inherits controlled-harness/adapter flags and
terminal tools. The executor body, routing result, receipt and ContextBundle sinks
were mocked. This is configuration-isolation evidence, not a live-effect result.

The existing mocked singleton test cannot establish this guarantee. An initial
probe stopped before any case on an unrelated editable-install metadata read;
child-only search-path pruning produced the scoped witness with zero forbidden
effects. Exact source/runner/replay receipts are bound in the RSI backlog.

The bounded source repair is scored C3/I4/D3/Impact3=13/P1 and locally implemented below.
Live delegation already blocks; the witness is not a production incident:

- Extend existing `execute_foundup_job` with a keyword-only force-dry request,
  default False, preserving one-argument callers and `get_executor` semantics.
- Validate the request as a literal boolean before construction. True selects a
  fresh dry-run executor with ordinary safe defaults; never modify or copy warmed
  harness/tools/adapter state. Preserve the default capability-validator singleton
  so nonce/replay history is not reset. False grants no live authority.
- Capture consumer policy once before routing/binding callbacks and use the same
  value for model admission and dispatch. Keep job flags as independent guard
  input; do not rewrite them to make a dry-run succeed.
- Prove fresh/warmed state, flag combinations, invalid requests, callback mutation,
  legacy caller compatibility, model-admission rejection and shared-validator
  preservation in existing tests. No real delegation or weaker gates.

A fresh executor uses normal workspace discovery, not the warmed instance's
custom root; bind an owned disposable root before tests. Per-call allocation cost
remains unmeasured. Dry-run evidence may write files and is not OS confinement.
The original qualification did not implement or test the repair; the subsequent source sprint does.

The next source sprint's baseline exposed a separate local fixture prerequisite:
the shared runtime helper supplies an enriched receipt and an aggregator provider,
while this projection accepts an exact core/direct-provider contract. The 10/P2
test-only adapter repair now yields 49 focused and 174 connected passing cases,
with production/shared-helper bytes unchanged. Rejection controls remain active.
The fixture prerequisite is closed in PR1837, with all ten PR checks and both main
workflows successful. The 13/P1 repair now implements the contract above in the
existing consumer/executor owners. New regression cases reproduce 24 failures and
23 passes on unchanged production, then pass all 47 after repair. Expanded connected
and size-governance coverage passes 221 tests; ContextBundle wiring passes 24 more.
These runs overlap and observed zero forbidden effects. Independent source review
accepted the repair and replayed the same 245 cases;84 source/test hashes remained
stable. Hosted publication is tracked separately in the canonical RSI backlog.
OpenRouter compatibility and live provider admission remain separate questions;
direct-provider fixtures do not answer them.

## AutoResearcher abrupt-exit witness — 2026-09-20

The **10/P2** test-only witness is locally verified on unchanged production source.
The existing suite passes **112 cases**, independently replayed with the same 112
cases; these runs overlap. Three deterministic child modes establish:

| Mode | Observed scratch | Publication and acknowledgment |
|---|---|---|
| Normal return | Baseline restored | Final report and return acknowledgment agree; no temporary report. |
| Exit71 after proposal write | Proposal remains | No final report or acknowledgment. |
| Exit72 before atomic replacement | Baseline restored | Temporary JSON only, despite completed/restored labels; no final report or acknowledgment. |

Exact exit/phase markers and owned paths identify these injected events. Missing
reports alone remain incomplete/unknown. Target/program and seeded prior-artifact
bytes remain unchanged; that prior fixture is not a prior successful invocation.
The child uses fixed proposal/evaluator/model stubs. This does not prove model
quality, live concurrency, an adversarial OS sandbox, power durability or recovery.
Durable pre-mutation baseline, current ownership/quiescence and a recovery caller
are still required before automatic restore/resume/delete can be qualified.

Static review preceded execution. Initial pytest logging hit the parent's Windows
null-device restriction before collection: zero tests/children. A narrowly
reviewed external runner correction yielded author 112 and independent 112 passes.
Each run records 111 denied symlink attempts, consistent with the installed pytest
best-effort alias helper; per-event attribution is inferred, not stack-proven.
There were three suite attempts and six actual witness child invocations, within
the 3/9 budget. The test is 996 lines; its original 896-line prefix/31 definitions are
preserved. The new parent test is 41 lines and embedded functions are <=50. Retain
the existing cohesive 800-line size review; no new exemption or product edit.
Canonical registry generation/check preserves 1651/269 and adds only the existing
test's process capability; independently reconciled against unmerged PR1820.

The freshly selected conditional next action is **10/P2** call-local OpenClaw
skill-safety diagnostic qualification, ahead of optional cache planning 9/P3.
Correct per-call Boolean admission already exists; a nested publication can
replace its caller's latest explanation. Qualify compatibility in existing owners
before any repair. Preserve 26 original packets and 41 histories; the distinct next
plan makes 42. Both PR1827 main workflows passed. Exact receipts, limitations and
the next M2M packet are in the current RSI backlog. No live runtime activation.


## AutoResearcher interruption qualification — 2026-09-20

The **12/P2** source-only qualification is complete. The producer reserves an
invocation directory but writes no initial report or durable baseline manifest.
Abrupt process exit can bypass cleanup. A missing report cannot say
whether scratch is dirty, restored, still in use or abandoned.

| Observed evidence | Permitted interpretation |
|---|---|
| Missing report or temporary JSON only | Incomplete/unknown; never promote TSV or temporary JSON to completion. |
| Completed/aborted `report.json` | Local terminal diagnostic at its exact invocation; no caller acknowledgement, current liveness or independent acceptance claim. |
| Cleanup failure or missing cleanup evidence | Restoration is not certified; no automatic restore/resume/delete. |
| Partial/mismatched terminal JSON | Unqualified diagnostic; reader validation remains a separate contract. |

Tracked Python class/schema searches found only the producer and its tests/CLI,
not a current report consumer. Adding an unused classifier would duplicate a
future reader boundary. Automatic recovery also lacks a durable baseline manifest,
current ownership/quiescence and an idempotent recovery caller. These remain open.

The independently reviewed next action is **10/P2**:
`auto-researcher-abrupt-exit-diagnostic-witness`. Its exact bounded M2M packet is in the current backlog. Reuse the existing
test owner and unchanged producer; compare an isolated abrupt-exit witness with a
normal control. Inject synthetic model/evaluator dependencies before import;
observe explicit owned paths, exit markers and bytes independently. This tests
producer lifecycle only, not the real evaluator, arbitrary-host sandboxing,
power-loss durability or production recovery. No child/test runs occurred here.

Preserve all26 original packets and40 prior candidate histories; this distinct
test action is scored separately. The optional cache plan is freshly9/P3:
safe rescanning remains correct and no measured latency harm justifies the
earlier12/P2 bounded score. Preserve that earlier score and the15/P1 broad parent
in their historical scope. Both PR1826 main workflows passed. Re-observe
before executing the next packet; no model, WSL, service, AmIBot or startup activation.


## Proposal diagnostic lineage — 2026-09-20

The independently qualified **12/P2** proposal-text step extends the existing
report with per-attempt `proposal_inputs`. Text identity is captured before
scratch write/diff after mode admission, including later rejected/interrupted
attempts. Existing outcomes, evaluator, callback, cleanup and live-mode rejection
remain unchanged. This advances the aggregate report qualification work; it does
not complete its program/oracle/environment/reader or retained-learning contracts.

Thirteen new regressions failed against unchanged source while96 existing cases
passed. The repaired suite passes109; independent review reruns the same109
cases separately. Counts overlap. Tests share the existing model-disable fixture,
use external state and cover Unicode/newlines, sequential invocations, write/diff/
evaluation interruptions, missing/non-text returns and string subclasses.
The existing test file crosses the800-line review guideline but remains a cohesive
report-lifecycle suite below1000; no new fixture owner, module or exemption is added.
All new functions stay within50 lines, while inherited class285/loop82 do not grow.
Exact evidence and fresh selection are in the canonical backlog's current observation.

## Current local RSI checkpoint — 2026-09-15

Historical checkpoint; the September20 qualification above is current.

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

### Current core canary test checkpoint — 2026-09-23

PR1877 closed the deferred-callback qualification. The next core contract now
passes11 frozen cases locally and independently: real use-time collection and
resident readiness retain distinct diagnostics. Accepted typed generation evidence
removes only three use-time reasons; seven other anchors and no effect lease
remain. Readiness retains its own generation/peer blockers with no supplier calls.
The minimal fixture retains independent binding errors while signature acceptance
still triggers collection. This is characterized acquisition, not a source repair.
Production, shared fixtures and existing tests are unchanged; no native or retained
RSI claim. AmIBot remains registered/undispatched, Memory Horizon separately owned.
The [canonical backlog](../../../docs/roadmaps/rsi_swarm_backlog.json) binds exact
source, synthetic evidence, current ownership and the freshly scored next action.

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

## Self-audit scan status and decomposition

The bounded scan-status repair extends the existing scanner and OpenClaw
consumer. Its fixed acceptance covers same-attempt count/status correspondence,
incomplete inputs, detached snapshots and monotonic success age. The
[interface](INTERFACE.md#self-audit-scan-observations) and
[monitor map](../../../docs/DAEMON_ARCHITECTURE_MAP.md#self-audit-scan-qualification--2026-09-22)
describe the exact contract; validation/publication receipts belong to the
current system backlog. Local tests do not establish live RSI or full coverage.

WSP62 review: the scanner enters the 1000–1499-line critical window while its
inherited class and constructor shrink. The new bounded state helper and input
diagnostics stay with their existing owner; no new monitor module or exemption
is introduced. Exact candidate dimensions are recorded in validation. WRE Core
Maintainers own the remaining decomposition: extract existing input-discovery,
tailing and runtime-configuration responsibilities in a later parity-tested
slice before further scanner growth. Preserve public integer/exception callers,
path confinement, offsets, effects and fixed scan-status acceptance. Do not
compress unrelated code to disguise size debt. The supervisor separately retains
its pre-existing 3419-line ceiling and 2026-09-30 review deadline.

## Self-audit diagnostic accounting — 2026-09-22

The 11/P2 repair separates SQLite diagnostics from repair counters, feedback and
escalation suppression. 94 fixed cases pass locally and independently, including
the unchanged 71-case scan-status suite. Exact publication and re-observation
belong to the canonical backlog; native runtime and retained learning remain open.

The touched outcome responsibility is decomposed within the existing WRE module.
This shrinks the critical scanner and its inherited oversized class; exact
dimensions are in candidate validation. Remaining input/tail/config decomposition
above is still required before scanner growth. No new monitor, store or authority
owner is introduced. The single runtime helper requires a reviewed 1400-to-1401
manifest count ceiling; all byte, path, digest and execution controls remain.

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

## Cross-layer RSI monitoring and controls — 2026-09-22

Use the existing [daemon architecture map](../../../docs/DAEMON_ARCHITECTURE_MAP.md#rsi-and-wre-supervision-contract--2026-09-22)
as the supervision contract, not a second roadmap or scheduler. WRE/AgentDB keep
admission/claim/lease authority; CentralDAEmon supplies its existing observation
surface. R18 capacity and R23 sustained operation now require truthful progress,
freshness, persistence acknowledgment, confirmed control outcomes and monitor health.

Sequence: qualify central event-store collision/partial-write/ack behavior in
disposable fixtures (15/P1), then repair only confirmed existing-owner defects;
bind one component and admitted ticket; prove two/ten workers with verifier capacity;
only then qualify hundred/thousand-agent throughput and bounded advisory supervision.
Read-side broker initialization, scan errors and stop confirmation are still open.
Small-model watchers are advisory candidates with fixed evaluations, not authorized
controllers. Startup status must not automatically admit RSI work or double cycles.

This is a source/document audit, not a new live test. The per-counter repair below
remains its own narrower result. Native18/P0 is blocked; persistent role15/P1 remains
outstanding. Re-score after closure; no production services or protected FoundUps
are test fixtures for this layer. Each component handoff carries its existing
owner, oracle, telemetry/control consumer, rollback and independent evidence.

## Daemon counter memory lifetime — 2026-09-20

The 13/P1 qualifier merged in PR1807. On unchanged source, its independent
witness returned two events from distinct live threads but persisted only one
counter increment. The existing supervisor both starts the daemon and invokes
synchronous scans; its cached connection violated SQLite creating-thread use.

The separately scored **C2/I4/D4/Impact3=13/P1 source repair is locally verified**.
The existing daemon now creates, uses and finally closes a handle per counter
operation on its calling thread. It retains no cache. Disabled telemetry opens
nothing, ordinary errors remain fail-soft, and interruption propagates after
cleanup. Scheduler methods, public signatures and PatternMemory are unchanged.

Ten new tests preserve the original 20. Before repair: 8 failed/22 passed.
After: 30 passed; connected 71 passed with 115 disposable database opens and zero
external attempts. Independent 71 replay overlaps. Distinct events persist both
increments; a blocked-counter timeout proves stop does not close a foreign
handle and the owner closes when released. No actual start/restart or live log
tail was exercised. Close-failure injection follows real close, not partial
SQLite close failure. Partial constructor failure, contention, initialization
cost, real shutdown/restart, other consumers and R11 acceptance remain open.

Source 865/class755 retain inherited size without growth; constructor shrinks
62→61. Tests 750/max function 40 satisfy their bounds. Existing 1,400-file backend
membership/API/assertions remain unchanged; only this member digest and both
existing pins advance. Generator 8 tests, RedDog 15 fast groups and 67-file package
pass. Registry 1651/269 remains current; no generated registry edit is needed.

Canonical current evidence and next selection are in
[the existing backlog](../../../docs/roadmaps/rsi_swarm_backlog.json),
daemon_counter_memory_ownership_20260920. Local verification is not WRE worker
admission, deployment, authenticated write acceptance or retained RSI benefit.

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
- the daemon per-counter lifetime is locally repaired above; qualify remaining
  cached consumers, actual restart/shutdown, same-handle multi-call transactions
  and R11 acceptance separately before concurrent production use;
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
