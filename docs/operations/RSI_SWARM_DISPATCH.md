# RSI hybrid production line: ticket dispatch and cost control

Parent authority: [system roadmap](../../ROADMAP.md). Status: operating plan; runtime observations are dated 2026-09-10 JST. The hybrid planning refinement is dated 2026-09-11; earlier runtime observations retain their date. This document configures no runtime, authorizes no new effect, and does not make the backlog executable.

## Recursive repository prioritization and execution

012's 2026-09-14 objective makes this the continuing work-selection rule for RSI:

**Observe → Score → Reconcile → Select → Execute → Validate → Document → Re-observe.**

This refines the existing system plan under [WSP 15](../../WSP_framework/src/WSP_15_Module_Prioritization_Scoring_System.md)
and [WSP 97](../../WSP_framework/src/WSP_97_System_Execution_Prompting_Protocol.md).
It adds no scheduler, scoring variant, WRE grant, independent verifier or promotion authority.

1. **Observe current evidence.** Reconcile exact Git base/HEAD and owned work;
   finish or safely disposition an already-owned sprint before changing lanes.
   Inspect current WSP 15/97, applicable skills/instructions, canonical roadmap
   and backlog, relevant ModLogs/contracts/tests, changed source, visible
   branches/worktrees, current CI and operational TODO/FIXME or incomplete code.
   Use the governed Holo entry and evaluate noise, ordering, missing artifacts,
   freshness and duplication. An inventory, archived claim or unavailable remote
   is not verified completion. Expand into adjacent owners where evidence requires.
2. **Score actionable work using WSP 15.** Record Complexity, Importance,
   Deferability/urgency and Impact, each 1–5; sum C + I + D + Impact. Higher D
   means less deferrable. Use the canonical P0–P4 ranges; review LLME only when
   applicable to a module. Record cost/effort and verification burden as context,
   not an invented ROI formula, extra score dimension or inverted Complexity.
3. **Reconcile with WSP 97.** Classify each candidate as outstanding, partial,
   complete but unclosed, duplicated, stale/superseded, blocked or externally
   owned. Verify completion in source/tests and available receipts. Consolidate
   into existing owners; close resolved scope without erasing its history.
4. **Select the highest-ranked eligible action.** Dependencies, active ownership,
   current evidence, budget and delegated authority constrain eligibility. A
   blocked theoretical P0 cannot displace an executable action. Record a short
   decision rationale and prerequisite; never take the old queue's next row by
   default. A tied score requires an evidenced dependency/value judgment, not a
   new numeric framework. Planning records remain non-dispatchable.
5. **Execute one coherent sprint.** Use an owned branch/worktree and the smallest
   change that closes or materially advances the selected scope. Search and reuse
   before creating; use existing tests/fixtures and deterministic checks before
   paid model work. Preserve concurrent work, signed execution boundaries and
   separate verification/promotion roles. Stop or fail closed on uncertain validation.
6. **Validate and close.** Record exact scope, command, source and result. Distinguish
   local verification, observed remote/CI verification and infrastructure-blocked
   checks. Update only canonical roadmap/backlog, module docs and ModLogs required
   by WSP. Do not claim push, PR, merge, deployment or checks without observing them.
7. **Immediately re-observe after completion or blockage.** Refresh changed Git,
   ownership, CI and dependency evidence; reapply WSP 15 and WSP 97, remove resolved
   or superseded candidates, rescore and select again. Record the changed decision
   in the existing backlog's `current_observation`; preserve dated baseline history
   and point `current_selection` to it. Reuse evidence only at its exact source;
   do not rerun a full audit or unchanged failed probe at every checkpoint. If no
   authorized independent action remains, record the specific blocker and the
   evidence change needed to resume; do not fabricate progress or busy-loop.

**012 escalation:** WSP 15 helps prioritize consequential unresolved decisions.
It does not establish an approval threshold or confer permission. Escalate new
high-consequence ambiguity, irreversible external effects, strategic changes,
financial/legal decisions or insufficient evidence before dependent work. Include
the concrete decision, evidence and consequence; honor standing authorization for
routine reversible work and continue independent authorized actions while waiting.

**External boundary:** `FOUNDUPS/autopost` is owned separately by Remote. Related
items here are dependency/state inputs, never automatic RSI work. Preserve
YUMORI.me/eSingularity, active RedDog services and concurrently reserved lanes.

**Measure progress:** fewer unresolved high-value items, duplicates, stale plans,
undocumented completions, CI debt, drift and unnecessary escalations; more verified
closures, reusable execution capability and clearer next actions. Count only the
scope actually observed. Repository convergence is a prerequisite, not proof of
independent retained learning or production RSI.

**Current selection evidence:** `current_observation` in the [planning backlog](../roadmaps/rsi_swarm_backlog.json).
The [dated baseline](../roadmaps/RSI_BASELINE_OBSERVATIONS_20260913.json) is preserved near its size budget; its 55 top-level fields are not 55 observations. Git retains subsequent checkpoints.
The [AmIBot experiment](../../ROADMAP.md#amibot-autonomous-production-experiment--2026-09-15) remains at G0: registry candidate held in draft PR1751; explicit M2M profile/signing and local provider prompt fidelity qualified; runtime admission remains open.
Next: explicit plan input through the existing seed supplier/bootstrap, 18/P0. Full context/native-child fidelity and live admission remain separate.

## Production-line operating model

Use a **hybrid production line**: qualification → admitted ticket → one worker or bounded team → evidence synthesis → independent audit → governed acceptance → reward eligibility → confirmed settlement. A swarm may self-organize only inside a separately admitted team profile. The existing filename is retained for link compatibility. See the [hybrid decision and current RedDog assessment](../architecture/REDDOG_HYBRID_TICKET_SWARM_FEEDBACK_MODEL.md).

[Implement this through packet R24](../roadmaps/R24_AGENT_PRODUCTION_LINE_PACKET.md). It names the existing FAM/WRE/AgentDB owners, qualification requirements, reward conditions and acceptance tests. The pool can work concurrently within station and reviewer capacity; a single job need not launch a panel or sub-swarm. Each ticket fixes its acceptance criteria, scope, price/reward policy, budget and independent reviewer before assignment. R24-E covers optional teams; [R25](../roadmaps/R25_REDDOG_FEEDBACK_LOOP_PACKET.md) covers consented feedback only from 012s actively engaged with the same FoundUp, delivery-time activity rechecks, recipient/attention caps and truthful outcome return. Responses supply V1 Validation evidence; V2 Verification and V3 Valuation retain their separate CABR owners and gates. Team agreement, 012 preference and sovereign authorization are separate evidence types.

FAM currently exposes `open → claimed → submitted → verified → paid`; the persistent pipeline sets the task `paid` while its payout is only `initiated`. Treat actual reward delivery as unproven until the settlement owner returns confirmation. Qualification, review and settlement are distinct gates. Reviewers should be rewarded for correct assessment, including justified rejection.

## Which component does what

| Component | Role and present boundary |
|---|---|
| 012 | Principal: objectives, bounded standing authority, budget and correction. |
| 0102 | FoundUps governed destination/state terminology, separate from the replaceable model, task role and product interface. State-semantics correction remains owned by [PR #1636](https://github.com/FOUNDUPS/Foundups-Agent/pull/1636); this roadmap does not implement or claim that unmerged repair. |
| Codex / Astra or another model | The intelligence performing an architect, worker or verifier role. This Codex task is not automatically attached to a FoundUps provider route. Its app setting and a worker's model binding are separate. |
| RedDog | Fast principal-facing interaction surface for the deeper 0102 Digital Twin. Conversation/context-to-work integration remains bounded by the current client and service contracts; durable live feedback delivery is not established by the existing backend primitives alone. A conversation is not a work receipt. |
| FoundUps Fusion | Provider adapter for principal/panel model work through the admitted OpenRouter route. A panel result is candidate content, not independent acceptance. |
| Local Nemotron | Evaluation-only topology proposer via LM Studio. It proposes compact candidate model lists; deterministic admission and held-out evaluation own the next step. It cannot select production models or promote itself. |
| AI Gateway | Catalog, selection/evaluation evidence, promotion evidence and verified provider/model/topology binding at use time. It resolves the approved route; a provider name is insufficient. |
| WRE / AgentDB | Work admission, durable claims, scope, evidence and lifecycle. Reuse these owners; do not build a second scheduler. |
| OpenClaw / Hermes | OpenClaw supervises admitted jobs; the currently accepted Hermes profile handles one bounded native leaf and returns artifacts/lifecycle evidence. |
| Independent verifier / promoter | Verify outcomes and authorize activation under separate authority. Neither a model's confidence nor Fusion agreement replaces this. |

Source anchors: [AI Gateway](../../modules/ai_intelligence/ai_gateway/README.md#nemotron-shadow-topology-proposals), [topology proposer](../../modules/ai_intelligence/ai_gateway/src/model_topology_proposal_lm_studio.py), [worker route](../../modules/communication/moltbot_bridge/README.md#receipt-bound-artifact-model-routing), [Fusion provider](../../modules/communication/moltbot_bridge/src/reddog_foundups_fusion_artifact_provider.py).

The execution path is:

`012 intent → RedDog proposal → WRE admission/claim → verified AI Gateway route → OpenClaw supervision → bounded Hermes/OpenClaw artifact → independent verification → authorized activation/rollback → verified memory`

Nemotron's optional evaluation path feeds candidate routing evidence into AI Gateway. It is not an additional runtime boss above WRE. A Fusion panel is optional only where an admitted SINGLE/PANEL policy permits that topology; never silently strip an already-bound panel to save cost.

## What was actually checked

- Local CLI: `openclaw --version` returned `OpenClaw 2026.5.2 (8b2a6e5)`. `hermes` was not resolved on this shell's PATH; that does not establish whether a separately hosted native API is available.
- The existing [model-binding query](../../scripts/reddog_model_runtime_binding_query_once.py), targeting the shared repository from the clean audit control source, returned `MODEL_RUNTIME_BINDING_UNCONFIGURED`, `configured=false`, `accepted=false`. It performed no model call or mutation. This is the current shell's configuration result, not a global diagnosis of every RedDog process.
- The previous [Holo recovery](../audits/rsi/2026-09-09/holo_recovery_receipt.json) completed through real governed OpenClaw/WRE maintenance. That proves that maintenance slice at its recorded SHA, not general coding-swarm readiness.
- No live model work was dispatched for this documentation change. No service or existing model instance was started, stopped, evicted or reconfigured in this integration slice.

MCP can expose these existing operations for easier tool access, but it cannot supply a missing signed binding or repair source/generation drift. Prefer the existing one-shot bridges and runtime adapters. Do not add another MCP server merely to wrap a working CLI.

## Internal RSI validation candidates

012's latest 2026-09-13 clarification permits system-first improvement and selected early-stage FoundUps/other repositories as RSI test workloads. This supersedes the earlier blanket active-FoundUp exclusion. Preserve YUMORI.me/eSingularity and concurrent reserved lanes. Use isolated source checkouts, declared test inputs and disposable state; a candidate entry alone does not authorize posting, account access, live-session mutation, outreach or deployment.

| Candidate | Existing implementation to reuse | First isolated experiment | Fixed independent checks |
|---|---|---|---|
| Test-registry-audit procedure — first R15 target | [Existing Skillz workflow](../../modules/infrastructure/wre_core/skillz/auto_test_registry_audit/SKILLz.md) and registry generator | Reduce repeated context assembly or redundant steps in a disposable source snapshot. | Registry meaning, required test selection, quarantine rules and held-out correctness stay unchanged; measure actual cost/latency and rollback a bad candidate. |
| Auto-post workflow — candidate for a later repeat | [Social Media Orchestrator](../../modules/platform_integration/social_media_orchestrator/README.md), its [interface](../../modules/platform_integration/social_media_orchestrator/INTERFACE.md), and [duplicate prevention](../../modules/platform_integration/social_media_orchestrator/src/core/duplicate_prevention_manager.py) | Replay synthetic post requests through isolated formatting/routing/deduplication work, with an injected no-network recording sink. | Correct destination/content, no duplicate dispatch, retry/idempotency behavior, zero external effects, and cost/latency against unchanged fixtures. Do not count a mocked sink as proof of real posting. |
| PQN researcher — candidate for a later repeat | [PQN research orchestrator](../../modules/ai_intelligence/pqn_alignment/src/pqn_research_dae_orchestrator.py), [detector API](../../modules/ai_intelligence/pqn_alignment/src/detector/api.py), and [research interface](../../modules/ai_intelligence/pqn_alignment/INTERFACE.md) | Improve research-task preparation, experiment scheduling or artifact assembly using fixed synthetic sequences/seeds and scratch output. | Reproducibility, schema/invariant checks, evidence traceability, held-out task quality and cost/latency. Keep detector thresholds, hypotheses and judging criteria fixed; a stronger apparent PQN signal is not proof of RSI or a scientific claim. |

The first three workflow observations above originated at `2b56415aebf551b54caf4b4fe3cfa53f27d5856b`. The expanded component review below is pinned separately to `837da85f0b10aaacd393c78f5162efe10e5cfad1` and the named external commit. These are planning candidates, not claims that isolation or end-to-end RSI already works. This review performed source/document reads only; it launched no Auto Researcher, provider campaign, FoundUp test or PQN experiment.

Before admitting a candidate:

1. Inventory current imports, constructors, output paths, provider calls and background hooks. Reuse existing seams; extend the existing owner only if a missing isolation seam is demonstrated.
2. Bind explicit temporary database/JSON/output paths, synthetic fixtures, fixed seeds where applicable, and a network-denied test runtime. Exclude live credentials, browser profiles, schedulers, callbacks and production memories.
3. Check each selected test for side effects. The auto-post [test guide](../../modules/platform_integration/social_media_orchestrator/tests/README.md) includes live browser/engagement tests; its whole-directory command is not an RSI-safe selection. The duplicate manager defaults to module memory paths and Qwen enabled; explicit db/json arguments alone do not prove all side effects are isolated.
4. The PQN detector API already accepts `out_dir` and `seed`; its default writes under the shared detection logs. Use an explicit scratch directory and inspect the downstream runner before execution. The [PQN test guide](../../modules/ai_intelligence/pqn_alignment/tests/README.md) supplies synthetic/invariant candidates, not permission to run provider or active research sessions.
5. Apply R06–R15's admitted worker, independent evaluator, promotion, activation and rollback requirements to the **isolated candidate**. Retain verified improvement only in its test memory until separately admitted. Report mocks, unavailable providers, skips and real effects separately.

R20/R22 may later use a dedicated fixture or an explicitly selected early-stage repository/test consumer. R24/R25 first use synthetic qualification and participant fixtures; any later cohort remains scoped and consented. Protected projects remain excluded. Neither a product launch nor external federation is needed to prove system RSI.

## Existing component coverage and RSI insertion points

Reviewed main: `837da85f0b10aaacd393c78f5162efe10e5cfad1` (2026-09-13).
This extends the existing full audit with the components raised by 012; it is
not a fresh claim that every repository/module has been operationally tested.
Source presence, existing wiring, exercised behavior and complete RSI remain
separate levels of evidence.

| Component / existing owner | What exists and where it fits | Next bounded connection or evidence; existing packet |
|---|---|---|
| HoloIndex + WSP | [Owner-query entry](../../holo_index/CLI_REFERENCE.md#source-bound-owner-queries) retrieves source-bound context; WSP governs work. | Exact-current-main qualification remains open. Reuse the restored reference runtime; R03–R05. |
| WRE + AgentDB + OpenClaw/Hermes | [WRE interface](../../modules/infrastructure/wre_core/INTERFACE.md), existing signed worker dispatch and durable job owners carry tickets/leaf results. | Admit one real bounded artifact through the existing path; do not attach another scheduler to Auto Researcher; R06–R09/R16–R18. |
| WRE Auto Researcher | [WREAutoResearcher](../../modules/infrastructure/wre_core/src/wre_auto_researcher.py), [research evaluator](../../modules/infrastructure/wre_core/src/wre_research_evaluator.py), [existing tests](../../modules/infrastructure/wre_core/tests/test_wre_auto_researcher.py). Proposes changes to a scratch copy and compares ROC simulation metrics. Non-dry-run and live commit remain `SPECIFIED_NOT_IMPLEMENTED`. | Reuse as a bounded proposal/evaluation producer where its target contract fits. Static Python caller search finds its own CLI and tests, not a separately wired generic WRE job caller. Bind proposals/results to the admitted ticket and independent oracle; R07/R10/R14/R15. Do not replace `IGitRunner` with unrestricted Git execution. |
| AI Gateway model AutoResearch | [Campaign planner](../../modules/ai_intelligence/ai_gateway/src/model_champion_challenger_autoresearch.py), [configured runner](../../modules/ai_intelligence/ai_gateway/src/model_autoresearch_configured_gateway_runner.py), [model interface](../../modules/ai_intelligence/ai_gateway/INTERFACE.md). Campaign planning, exact model/provider budgets, benchmark receipts and feedback admission already exist. | Use this path to compare model quality/cost for a fixed ticket family; its planner does not itself call providers or change defaults. Require current runtime/call admission and a task-appropriate judge; R07/R10/R14/R18. |
| Existing judges and retention | The [ROC evaluator](../../modules/infrastructure/wre_core/src/wre_research_evaluator.py) parses literal configuration with AST, not arbitrary target execution. The [model output verifier](../../modules/ai_intelligence/ai_gateway/src/model_autoresearch_semantic_verifier.py) checks content-bound records and declared required/forbidden terms. [PatternMemory](../../modules/infrastructure/wre_core/src/pattern_memory.py) and [model cycle feedback](../../modules/ai_intelligence/ai_gateway/src/model_autoresearch_cycle_feedback_ledger.py) have distinct owners. | Freeze a relevant oracle and baseline; a better simulated margin or keyword match is not general task correctness. Keep model feedback separate from admitted skill memory, then prove the next invocation consumes the accepted result; R10/R11/R14. |
| Promotion, activation and rollback | Existing model promotion/runtime binding and WRE evidence/activation patterns are already mapped in R02. The generic [legacy variation promoter](../../modules/infrastructure/wre_core/src/pattern_ab_evidence.py) still rejects direct production mutation. | Compose the matching independent authorities for the chosen asset. Model campaign evidence cannot substitute for generic skill activation or rollback proof; R12/R13/R15. |
| PQN research engine | [PQN interface](../../modules/ai_intelligence/pqn_alignment/INTERFACE.md), existing research orchestrator and detector API perform research execution. It is distinct from the FoundUp's work registry. | Run a bounded, reproducible research-workflow experiment with fixed seeds/oracle and explicit scratch output. Judge reproducibility and task quality, not stronger apparent PQN signals; R10/R15/R23. |
| PQN FoundUp / Science Swarm Hub | The [monorepo entry](../../modules/foundups/pqn_swarm_hub/README.md) is a compatibility stub. The actual [external implementation](https://github.com/FOUNDUPS/science-swarm-hub/tree/bdf0e15f019f83d76fa9cf94b131716bde559350) has work registry, submissions, verification, contribution records, participant gates and optional SQLite storage. | Use a pinned external checkout and existing injected detector/store seams. Do not rebuild these services under the monorepo stub. Connect task/result evidence to existing FAM/WRE owners; R20/R23/R24. The later baseline below passes 36 selected standalone tests; live detector, FAM, publication and RSI integration remain unverified. |
| GotJunk — separately identified candidate | [Existing module](../../modules/foundups/gotjunk/README.md) and [HXA12 dry-run proof](../../modules/infrastructure/wre_core/tests/test_hxa12_gotjunk_second_proof_dryrun.py) already exist. [WREAdapter.execute_skill](../../modules/foundups/gotjunk/adapters/wre_adapter.py) raises `NotImplementedError`; the factory proof explicitly reports no real execution. | Qualify an isolated real-code/fixture task through the existing generic job path before claiming live integration. Reuse the dry-run proof as groundwork, not RSI acceptance; R08/R20/R23. The spoken name “GetK” has not been confirmed as GotJunk; resolve it before assigning a named ticket. |
| Auto-post | Existing social orchestrator, formatting/routing and duplicate prevention are listed above. | Qualify preparation/deduplication with a recording sink first; live posting is a separate effect. Reuse this workload for cross-task retained-benefit checks; R15/R23. |
| FAM, qualified teams and reward accounting | [R24](../roadmaps/R24_AGENT_PRODUCTION_LINE_PACKET.md) already binds worker qualification, tickets, independent audit, acceptance and reward policy to existing owners. | Science Hub contribution records are not confirmed FAM/financial settlement. Keep optional teams and reward effects behind their existing proof gates; R20/R21/R24. |
| 012/RedDog feedback and 3V | [R25](../roadmaps/R25_REDDOG_FEEDBACK_LOOP_PACKET.md) already covers same-FoundUp active engagement, consent, scoped proposals and typed feedback. | Reuse it for selected early-stage cohorts when admitted. V1 opinions do not self-certify V2 correctness, V3 valuation or promotion; initial tests remain synthetic. |

### Apply the existing Auto Researcher without broadening its claims

The [launch/evaluation sequence](../../modules/infrastructure/wre_core/ROADMAP.md#rsi-launch-and-evaluation-sequence--2026-09-15)
now binds 012's startup proposal to existing owners. Launch should display current
evidence; bounded campaigns belong to the admitted WRE queue. No automatic doubling.
The 2026-09-15 rehearsal uses five ten-attempt controls/runs: 40 candidate evaluations,
five baselines, repeatable simulated gain and no independent retained-benefit claim.
The existing tests pass 41 cases; see `launch_evaluation_continuation_20260915`.

`dry_run=True` still creates scratch/TSV and attempts Qwen initialization. Disable
model construction before diagnostic instantiation. ROC targets are literal
allocation/multiplier configurations, not a generic editor or registry optimizer.
Keep its simulator distinct from model AutoResearch and their existing judges,
feedback stores and admission contracts. Neither grants PatternMemory promotion.

### External Science Hub evidence boundary

Remote inspected: `FOUNDUPS/science-swarm-hub`, main
`bdf0e15f019f83d76fa9cf94b131716bde559350`. The pinned
[verification implementation](https://github.com/FOUNDUPS/science-swarm-hub/blob/bdf0e15f019f83d76fa9cf94b131716bde559350/src/pqn_swarm_hub/verification.py)
accepts submitted coherence/PQN-rate values against configurable thresholds;
its manual path records a supplied verifier ID and decision. Those operations
alone do not authenticate independent execution or establish scientific truth.
The existing
[detector bridge](https://github.com/FOUNDUPS/science-swarm-hub/blob/bdf0e15f019f83d76fa9cf94b131716bde559350/src/pqn_swarm_hub/detector_bridge.py)
supports an injected runner and otherwise imports the configured detector.
Use that seam with fixed test inputs and independently reproduced artifacts;
do not optimize the submitted metric merely to pass its own threshold.
Package publication/installation, live research participation and settlement
were not verified in that source review. The later isolated baseline below
executes selected tests from the same pinned external source without installing
the package or calling a live detector, FAM service or publication adapter.

### System first, then prove transfer across workloads

1. **System baseline:** R03–R09 establishes current retrieval and one admitted
   real worker artifact before any FoundUp is needed. Record baseline quality,
   cost, latency and allowed effects for the registry-audit procedure.
2. **One retained system improvement:** R10–R15 binds a fitting existing
   proposal producer, fixed independent oracle, accepted artifact, activation,
   forced regression/rollback and a better subsequent invocation. Reuse WRE
   Auto Researcher only where its inspected contract fits. Model AutoResearch
   can separately test economical model assignments for this same task family.
3. **Early-stage transfer:** R20/R23 qualifies Science Hub or another selected
   repository at a pinned commit using isolated real source and test state.
   GotJunk's existing dry-run proof is a candidate starting point. Measure
   whether the *system improvement* transfers; passing a project's tests alone
   does not prove RSI. Keep project-specific improvements labeled separately.
4. **Broaden only from evidence:** repeat across auto-post/PQN/another admitted
   workload with explicit per-ticket budgets. Add bounded teams only when
   measured benefit outweighs coordination and review cost. R24/R25 retain
   independent audit, reward and scoped feedback responsibilities.

No dependency, numerical priority or packet ID is changed by this coverage
addition. Current work-order admission and exact runtime/source evidence still
decide what can execute. The expanded list corrects omissions in the roadmap;
it does not claim that all components are already integrated or RSI-complete.

## Baseline and context preservation checkpoint — 2026-09-13

These are preparatory observations for R10/R15/R20/R23, not an admitted worker
cycle or a promotion receipt. The [machine-readable evidence](../roadmaps/RSI_BASELINE_OBSERVATIONS_20260913.json)
pins the source, selected commands/tests, hashes and rejected candidate. It
does not alter the frozen September 9 audit or any packet dependency/priority.

| Observation | Result | What it establishes |
|---|---|---|
| Registry audit at `bcc877829653997d7df638b7069258a061d04ee1` | Existing `generate_test_registry.py --check`: exit 0, 1,650 registered / 269 quarantined, one wall-time sample of 18.589 seconds. | A reproducible starting observation. Skillz, generator and registry hashes stayed unchanged. One sample is not a statistical performance baseline or an improvement. |
| Existing deterministic M2M compiler on a copied dispatch runbook at the same SHA | 28,223 to 641 bytes; 186 to 14 lines. All eight declared boundary passages absent; the actual shim rejects invalid YAML and removes its stage. | Reject this candidate. Byte/line reduction is not measured model-token savings. |
| Existing M2M shim on a synthetic seven-line reference | YAML gate PASS, but `The worker must not approve its own output.` is absent from the candidate. | YAML parsing does not prove preservation. This is a synthetic counterexample, not a claim that the real runbook passed. |
| Existing compact-prompt fidelity gate | At the baseline it reported PASS when a comma split one stop condition into two. The repaired comparison checks the parsed packet and rejects that loss; 53 fidelity/compatibility tests pass. | A narrow field-preservation defect is repaired in the existing owner. The compact prompt grammar and the reference-YAML compressor are distinct. |
| External Science Hub at `bdf0e15f019f83d76fa9cf94b131716bde559350` | `test_contracts.py`, `test_detector_bridge.py`, `test_persistence.py`: 36 passed in 1.01 seconds; total process wall time 1.714 seconds, one sample. | Existing contracts, injected detector-artifact handling and disposable SQLite persistence execute. No live detector, FAM/publication suite, package install or financial settlement was tested. |

The eight predeclared runbook passages cover ticket/reviewer assignment,
settlement confirmation, signed-binding provenance, actual execution evidence,
non-dispatchable planning, protected project scope, separate 3V roles, and
unchanged registry/quarantine/oracle behavior. The source text and missing
passages are retained in the evidence artifact. Both M2M candidates were
rejected; no source was replaced and no PatternMemory success was recorded.
The production registry `SKILLz.md` was copied unchanged and correctly rejected
by the existing boot/Skillz exclusion.

After the repair merged in PR #1710, the existing OpenClaw/WRE maintenance
controller completed source `5326080d583625aebbc230242117fb7fcf0044a6` and
stopped both owned runtimes. The fixed six-case public retrieval benchmark
then passed: Recall@8 `1.0`, MRR `1.0`, nDCG@8 `0.9939998`, mean latency
`3702.667ms`, p95 `4031ms`; whole invocation `97.102s`, including startup and
cleanup. All query receipts are CURRENT/no-gap at the same generation.
The complete run and deterministic verification receipts are retained in the
dated evidence file above. Exact runtime closure is false in every receipt;
this public regression corpus is not an independently sealed evaluator.
No ranker, query set, threshold, generation-promotion rule or runtime binding
was changed to obtain the pass. These observations do not establish a causal
RSI improvement relative to the historical benchmark or qualify a later SHA.

The [existing M2M owner](../../modules/ai_intelligence/ai_overseer/src/m2m_compression_sentinel.py),
[compile shim](../../modules/ai_intelligence/ai_overseer/src/ai_overseer.py) and
separate [compact-prompt fidelity gate](../../modules/infrastructure/token_efficiency/src/m2m_fidelity_gate.py)
are existing extension points. Holo retrieved the compact gate and its tests;
it must not be recreated or mistaken for a reference-YAML validator. Its stop
condition comparison now includes the parsed packet. Its CTX.HOLO check still
round-trips a separately supplied context object, not context serialized through
the compact packet; this does not authenticate current retrieval.

The next action check at source `7b7a1946171d6105e0e495835dc724683c719ad5`
found 13 false passes among the 14 recognized verbs in plan mode. The compiler
discarded the action and the gate accepted default `IMPLEMENT`. The existing
compiler now carries explicit `A:<action>` and the gate compares compiled,
parsed and decompiled actions plus the actual parsed scope. All 158 focused
fidelity/compatibility cases pass, covering every verb/mode combination and
dropped/changed field rejection. Legacy actionless packets retain their old
reader behavior; older readers that ignore `A` cannot certify action fidelity.
This repairs field preservation, not arbitrary objectives or prose. Static
caller search finds the gate's module export and tests; a generic admitted
worker/evaluator integration is still required. See the extended [dated evidence](../roadmaps/RSI_BASELINE_OBSERVATIONS_20260913.json).

Retrieval for this continuation preserved `HOLOINDEX_AUTHORITY_ROOT_HEAD_MISMATCH`
between task main `7b7a1946` and indexed authority `5326080d`. The existing lexical
bundle returned current checkout context with UNKNOWN freshness/no semantic
qualification. It located the existing gate, compiler and tests; unrelated
agent-market noise and duplicated result arrays were omitted from the working
context. Missing optional module history/test docs were recorded, not replaced
with placeholder modules. No owner startup or inline reindex occurred.

The reference compiler documentation now distinguishes structure and YAML
parsing from unimplemented fidelity checks. Before this producer is
eligible for R15 context, R10 must bind source and candidate bytes to an
independently fixed preservation corpus. Reject omitted or inverted negations,
authority limits, dependencies, references and executable commands; include
valid-YAML counterexamples and stale-source cases. A proposer must not choose
its own required passages, relax the judge or turn a local helper's PASS into
promotion. Keep the original text as the fallback. Do not create another
compression engine to bypass this result.

The next existing R10 owner, `wre_research_evaluator.py`, also accepted invalid
numeric input. A synthetic negative allocation scored `4.116279` against the
valid baseline's `1.042679`, allowing a false simulated improvement. The
repaired evaluator rejects non-finite/boolean metrics, unregistered agent
types, fractions outside `[0, 1]` and totals outside `1.0 ± 1e-9` before
simulation. Its multiplier bounds remain `[1, 5]`. All 26 existing/extended
Auto Researcher tests pass, including the real dry-run validation/restore path
with an injected invalid proposal and model construction disabled. The valid
baseline is unchanged. This closes a numeric-input defect in the existing
simulation oracle; a separately bound evaluator, task-specific schema and
measured real outcome are still required. [Current callable contract](../../modules/infrastructure/wre_core/INTERFACE.md#roc-research-evaluator-and-dry-run-producer).

For the next registry workflow ticket, use the existing production Skillz
verbatim, its generator contract and the selected packet's exact current
references. The full system audit is navigation, not mandatory per-call
context. Fix the input set, oracle, budgets and held-out negative cases before
authoring a candidate. Obtain actual worker/verifier usage and repeated
paired latency measurements only after R06–R09 admission; then compare an
accepted change against the same unchanged registry/quarantine oracle. These
observations do not prove cost savings, G1 admission or G4 retained benefit.

Science Hub's test named `test_real_detector_verdict` also uses its existing
`fake_detector_runner` fixture. Record the runner that executed, not the test
name. All tracked external source bytes stayed unchanged; the source checkout
and test state were separate from the active monorepo/product lanes. A later
transfer experiment must bind both repository SHAs to the same admitted
system-improvement lineage. Passing these project tests alone does not close
R20/R23, authenticate a verifier or establish the PQN hypothesis.

### Execution admission ownership checkpoint — 2026-09-15

Source: `cd532a538720b1c659f4625784032ebfb24ed012`, merged RSI PR
[#1745](https://github.com/FOUNDUPS/Foundups-Agent/pull/1745); both main workflows
passed. WSP 00's software gate passed. Fresh main and 96 open PR heads are
unchanged, with no admission/dispatch source or test owner conflict. Governed
lexical retrieval remains UNKNOWN with an index gap and zero owner attempts;
current Git reads supply source evidence without claiming semantic qualification.

WSP 15 selected **4/5/4/4 = 17/P0**. A reentrant test reproduced an earlier
execution consuming a changed bundle admitted by a later execution. The changed
case failed before repair; the unchanged-bundle control passed. This uses disposable
files and scanner-result doubles, not a live incident or runtime admission.

The existing admission owner now returns `(ok, message, fingerprint)` through
`admit_runtime_skill(...)`, with `None` on failure. The fingerprint comes from
that invocation's cached or fresh verdict, never a later cache lookup. The
existing `ensure_runtime_skill_safety(...)` preserves its two-value signature
and result by forwarding to the same implementation.

The coordinator keeps this value in its existing execution call and passes it
explicitly to the registered executor. It no longer stores/reads a shared skill-name
fingerprint map. Missing explicit evidence rejects; changed bytes reject through
the existing capture/manifest guard. Cached success/failure and a second admission
finishing before the first returns retain their own fingerprint results. No new
context class, module, skill, test file or admission authority is introduced.

Validation: **172 passed / four existing link-related skips** across seven
connected files, including **71 passed / one skip** in the three focused files.
Six cases extend the existing suites. Original test definitions remain; two
receipt assertions/mocks follow the new private contract. Identical `_Libido` and
`_Memory` helpers are reused from their existing test owner. Eight manifest tests
and 15 RedDog fast groups pass; registry remains current at 1,650/269.

The admission owner grows 197→214 lines. Coordinator file/class shrink
1,165→1,149 and 1,047→1,032; its 250-line execution method does not grow.
Root test files remain 574/581 lines and the nested test file stays 436. Existing
size debt is not increased and no exemption changes. Exactly two runtime hashes
and both existing pins change within the unchanged 1,400-member package.

Fresh WSP 15/WSP 97 removes this reproduced handoff defect. The next eligible
action is **OpenClaw workspace cache content/policy ownership, 3/5/4/4 = 16/P0**.
Its existing permission-policy owner returns by TTL before checking current content
or policy. Retrieve wardrobe/manifest fixtures and reproduce the gap before repair;
reuse the current owners where their contracts fit. Equal-ranked R11 acceptance
and reader work retain their write-authority and unanswered 012 policy dependencies.
Higher-ranked RedDog work remains externally owned; Holo/MCP, worker, independent
execution/promotion and deployment qualification keep their existing blockers.

The fingerprint is local supply-chain evidence, not an independently authenticated
permission or revocation lifetime. Whole-coordinator concurrency, current authority
composition and retained benefit remain unproved. Exact queue, commands, source/test
fingerprints and skipped IDs: `execution_admission_ownership_continuation_20260915`
in the existing baseline. All packets remain non-dispatchable. Production RSI remains
incomplete; re-observe again after closure.

### Scan-report ownership checkpoint — 2026-09-15

Source: `8682d569b1022f35fd357af6b3b20e4b5ce52a7e`, merged RSI PR
[#1744](https://github.com/FOUNDUPS/Foundups-Agent/pull/1744); both main workflows
passed. WSP 00's software gate passed. Fresh Git and ownership reads retain
96 unchanged open PR heads with no scan-source/test owner conflict. Governed
lexical retrieval remains UNKNOWN with an index gap and zero owner attempts;
direct Git reads establish the source used here, not current semantic qualification.

WSP 15 selected **4/5/4/4 = 17/P0**. The existing scanner tests reproduced
12 failures: an unsafe or missing report could consume another call's clean
report, a clean call could consume unsafe findings, and interrupted scans left
working evidence behind. This is a disposable reproduction, not a live incident.

The existing bridge scanner owner now creates a private temporary directory
for each invocation, including scanner TMP/TEMP. It computes the verdict from
that private report, then atomically replaces the existing latest diagnostic
file. Normal returns, timeouts, process errors and Python cancellation clean
only that call's workspace. Allocation/publication failures return a failed scan.
The public signature and result fields are unchanged. `report_path` names a
mutable latest diagnostic, can be absent, and is never immutable per-call evidence.
Hard process termination may leave an isolated directory; crash scavenging and
hostile-filesystem isolation are not established by this change.

Validation: **166 passed / four existing link-related skips** across seven
connected files, including **40 passed / one skip** in the scanner suite.
Two independent Python processes and reentrant callers retain their own verdicts.
Scanner output is injected; no live provider, scanner or FoundUp is used.
Eight manifest tests and all 15 RedDog fast groups passed. An initial packaging
run caught pins read before asynchronous manifest generation completed; the logs
are retained and final checks passed after regeneration/pin ordering was corrected.

The source is 394 lines (was 370); the test file is 668 (was 665). Reused setup
keeps all 27 original test/helper definitions and 56 unchanged assertions. One
TMP assertion follows the private-directory contract with added containment and
cleanup checks. No module, test file, skill, registry entry or size exemption is
added. The 1,400-member runtime manifest changes one source hash and both existing
digest pins; the test registry remains current at 1,650/269.

Fresh WSP 15/WSP 97 removes this local report-ownership defect and selects
**per-execution fingerprint handoff, 4/5/4/4 = 17/P0**. The coordinator still
stores admission by skill name and dispatches from that shared map; retrieve
existing execution-context evidence and reproduce interleavings before repair.
The adjacent OpenClaw workspace cache returns by TTL before current content/policy
checks; record that existing-owner gap at **3/5/4/4 = 16/P0** for later work.
Higher-ranked RedDog work remains externally owned; independent execution,
current Holo/MCP, worker and deployment qualification keep their existing blockers.
R11 acceptance and the unanswered 012 reader-policy decision remain separate.

Exact queue, source/test fingerprints, commands, skipped IDs, failure history and
evidence are in `scan_report_ownership_continuation_20260915` in the canonical
baseline. Planning packets remain non-dispatchable and production RSI remains
incomplete. Re-observe main, ownership and checks again after sprint closure.

### Admission cache ownership checkpoint — 2026-09-14

Source: `cfe510f4198de3d1339be6a124b2f529d3d99c79`, merged RSI PR
[#1743](https://github.com/FOUNDUPS/Foundups-Agent/pull/1743). Its main CI and
CodeQL passed. WSP 00's software gate passed; the 96 open PR heads and source
owners were unchanged. Holo supplied required module documents with UNKNOWN
freshness/index gap; direct current Git reads are explicitly degraded navigation.

Canonical WSP 15 selected existing cache ownership **4/5/4/4 = 17/P0**.
Eight regressions failed before repair: old successful admission survived a
pending/failed refresh, different scan severity reused the same result, entries
were unbounded, and removed scan ownership could be republished.

The existing cache owner now reserves a pending slot before scanning. Within a
shared mapping, another request for that directory returns blocked while the
scan is pending. Refresh removes the old admission immediately. Only the same
reservation may publish; exceptions and cancellation remove its pending slot.
Cache keys bind severity as well as directory and exact bundle fingerprint.
The coordinator passes its configured severity to the fingerprint reader.

A short-held module lock protects mapping operations; scanner calls run outside
it. The mapping retains at most **128 entries**, evicting the oldest completed
entry first. Pending entries are never evicted; exhausted pending capacity
returns blocked. Different directories can scan concurrently when space exists.
This does not serialize separate cache owners/processes or make raw concurrent
mapping mutation safe. Legacy cache keys miss and rescan.

Validation: **148 passed / four existing link-related skips** in seven connected
files, including **20 passed / one skip** in the focused admission file and all
23 coordinator tests. The selections overlap. Eight manifest tests and all
15 RedDog fast groups passed. All 23 original function definitions and 32
assertions remain. Cache source grows 168→197 lines; the coordinator remains
1,165 lines with its inherited class unchanged at 1,047. The test file is 545
lines. Exactly two of 1,400 runtime hashes and both existing pins change; the
registry stays current at 1,650/269. No new module, test file or exemption.

Fresh reconciliation retains the external RedDog audit's extension decomposition
20/P0 and closure/conversation work 19/P0 with that owner. Its broader current-Holo
qualification 19/P0 consolidates the earlier narrower navigation 16/P0; the existing
maintenance/runtime blocker remains. Independent execution/promotion 19/P0,
MCP/worker 18/P0 and Chroma 17/P0 still require their current owners and admission.

The next eligible local action is **scan-report ownership, 4/5/4/4 = 17/P0**.
`_scan_report_dir()` keys the report directory only by fingerprint; the bridge
unlinks and reads `openclaw_skill_scan_report.json`. Independent mappings/callers
can still target that path. Reproduce this through the existing scanner tests
before repair; no live corruption or substituted verdict is claimed. Equal-ranked
per-execution fingerprint handoff follows because it consumes this scan evidence.
R11 acceptance/read policy 16/P0, worker lifecycle 14/P1 and researcher durability 13/P1
retain their separate dependencies. Evidence: `admission_cache_ownership_continuation_20260914`
in the canonical baseline. All planning packets remain non-dispatchable;
production RSI is incomplete. Re-observe again after closure.

### PatternMemory connection ownership checkpoint — 2026-09-14

Source: `477cde2b80f2171e05343b398e4a73f7503a9735`. Prior RSI PR
[#1742](https://github.com/FOUNDUPS/Foundups-Agent/pull/1742) is merged as
`cc2ef5d8023b5c88669143d25a482148482a75d7`; its main CI and CodeQL passed.
The intervening RedDog identity/CLI change is separately owned. WSP 00's software
gate passed. Holo retrieval remains explicitly degraded (UNKNOWN/index gap);
current Git source and required module/test documents supplied the evidence.

Canonical WSP 15 selected the existing PatternMemory ownership item at
**4/5/4/4 = 17/P0**. A real SQLite commit denial leaves a pending proposal:
the second default instance could read, commit, roll back or close its owner's
connection. Foreign-thread operations also succeeded; closing one worker broke
the other. The 17-case reproduction had **13 failures and four explicit-path
controls passing** before repair.

The existing constructor now creates an independent connection for every default
or explicit-path instance. SQLite's creating-thread check is retained. Construct,
use and close the memory handle inside its owning worker. Sharing a database path
still shares committed records, while each handle owns its transaction and close
lifecycle. A foreign-thread call raises `sqlite3.ProgrammingError`; this deliberately
rejects the formerly unguarded use. Schema and all other storage methods are unchanged.

**41 focused tests and 206 connected tests pass** (overlapping selections), plus
8 manifest tests and all 15 RedDog fast groups. All original 24 test/fixture
definitions and 55 assertions remain. The source shrinks 1,294→1,279 lines and its
inherited class 1,164→1,149; the test file is 569 lines with no grown existing class.
The 1,400-member manifest changes only PatternMemory's hash; both existing pins
are refreshed. Registry remains current at 1,650/269. No new module or exemption.

Fresh WSP 15/WSP 97 reconciliation selects **WRE admission-cache ownership**:

| Action | C/I/D/Im | Score | Current next step |
|---|---|---|---|
| Independent execution/verification/promotion | 5/5/4/5 | 19/P0 | Blocked on independent runtime admission. |
| Integrated MCP qualification; WRE/OpenClaw/Hermes worker | 4/5/4/5 each | 18/P0 each | Existing owners and current signed job/model/runtime qualification. |
| Chroma deployment | 3/5/4/5 | 17/P0 | Existing deployment owner and qualification. |
| **WRE admission-cache ownership** | **4/5/4/4** | **17/P0** | Retrieve current tests; reproduce overlapping cache publication and assess bounded eviction. |
| R11 memory acceptance contract | 4/5/3/4 | 16/P0 | Existing write-authorization and independently bound transaction participant remain unresolved. |
| Response-read authorization; current semantic retrieval | 4/4/4/4; 3/5/4/4 | 16/P0 each | Pending 012 reader policy; governed Holo owner qualification. |
| Protected FoundUps; memory worker lifecycle | 3/4/4/3; 3/4/3/4 | 14/P1 each | Preserve external ownership; later inspect handle disposal/restart/handoff. |
| Auto Researcher process/volume durability | 4/3/3/3 | 13/P1 | Later disposable failure fixtures. |

The existing `_wre_skill_scan_cache` and `_scan_and_cache()` mutate a caller-supplied
mapping without a synchronization or total-entry bound. The roadmap already names
this gap; no live race is claimed. Thread-confined storage does not make the whole
orchestrator concurrently safe. Same-instance multi-call transactions, handle
restart/disposal, atomic R11 acceptance and independently admitted production RSI
remain open. Evidence and exact execution contract: `pattern_memory_ownership_continuation_20260914`
in the existing baseline. All packets remain non-dispatchable. Re-observe at closure.

### Research run isolation checkpoint — 2026-09-14

Source: `9b056d641442022022925bb2ad4b934f621298e3`, merged PR
[#1740](https://github.com/FOUNDUPS/Foundups-Agent/pull/1740); its main CI and
CodeQL passed. WSP 00's software gate passed. Governed Holo lexical bundles name
the clean owned source; UNKNOWN freshness/index gap remains navigation evidence.

R11-B contract tracing found the existing `canonical_pattern_memory_admission_identity()`
and its full record digest. Reuse it. The root outcome capability reserves/commits
signatures; the protected-use oracle binds signer grants and signing-request
digests. Neither currently composes the PatternMemory transaction. Resolve the
existing WRE write-authorization and participant binding before wiring acceptance;
unsigned metadata and read/signing capabilities are not a substitute. No new grant
architecture or activation path is chosen here. R11 remains partial.

WSP 97 reconciliation exposed an independent executable defect in the existing
Auto Researcher: overlapping invocations reused one working filename and TSV log.
Canonical WSP 15 scored its repair **3/4/4/4 = 15/P1**. Five failure cases reproduced
the collision, target/log aliasing and mkdir-before-rejection behavior.

`WREAutoResearcher(..., results_dir=parent)` now allocates a unique `run-*` child
under that parent (or the existing default temp parent). Its `results_dir` is the
actual run directory, `working_target_path` is `target/<original basename>` inside
it, and `results_path` names its `results.tsv`. Initialization reports that path.
Output parents resolving inside `REPO_ROOT` reject before mkdir. Cleanup restores
only that run's target; original templates and other run logs remain separate.

**35 tests pass** in the existing suite: four added cases plus the original 31,
with all 47 original assertions preserved. Three setup/path definitions now use
the actual run attributes and a disposable fake repository. Source/test files are
466/475 lines; the inherited researcher class shrinks from 316 to 304 lines.
Registry remains current at 1,650/269. These files are outside the unchanged RedDog
runtime manifest, so package checks were not repeated. Tests disable model
construction and use real files/concurrent threads. Process death, hostile storage,
production authority and independently measured RSI benefit remain unproved.

Fresh re-observation adds the existing WRE roadmap's **PatternMemory transaction
ownership, 4/5/4/4 = 17/P0**, as the next eligible local investigation. Its default
instances share a SQLite connection created with `check_same_thread=False`; that
flag is not transaction ownership. Reproduce interleaving in disposable databases
and inspect existing connection owners before editing. No live corruption is claimed.
This candidate outranks the remaining 13/P1 Auto Researcher durability work; the
previous next item does not automatically win. Exact ranking, source hashes, test
commands and boundaries are in `research_run_isolation_continuation_20260914` in
the existing baseline. All packets stay non-dispatchable; re-observe after closure.

### Activation recovery checkpoint — 2026-09-14

Source: `21afc9108fec741ec883efacc47e542dc2461a7b`, merged PR
[#1739](https://github.com/FOUNDUPS/Foundups-Agent/pull/1739); its main CI and
CodeQL passed. Fresh canonical WSP 15 ranks existing R11-B **4/5/3/4 = 16/P0**.
WSP 97 closes the earlier visibility guard and reuses its authority store.

`activate()` now reconciles a lost commit acknowledgment or identical competing
activation against the original envelope digest and current accepted memory.
Only revision conflicts can cause another commit, bounded to three attempts.
It preserves unrelated state and original evidence; missing/substituted evidence,
memory disagreement and unreadable state reject. Cancellation propagates.
This is authority-view recovery, not the memory acceptance transaction.

The 23 new cases reuse the existing adversarial suite and real disposable-store
fixtures: 13 initially failed; **204 connected tests, 8 manifest tests and 15 fast
groups pass** after repair. Original test definitions remain unchanged. Source/test
files are 306/416 lines. The 1,400-member manifest changes only this runtime hash
and its existing pins. An initial pin edit introduced CRLF; restoring required LF
bytes resolved the package rejection. Current registry remains 1,650/269.

**R11-B acceptance decision contract — design only.** Keep the decision with the
existing sink/PatternMemory transaction; the JSON authority ACTIVE state is a
recoverable view. No new coordinator, store or activation flag is introduced here.

| Boundary | Required behavior before production activation |
|---|---|
| Prepare | Preserve the exact signed envelope and staged memory bytes outside successful recall. Bind full record/envelope digests, work lineage, memory participant and independent current write authority. |
| Accept | Under the current protected write-authority lifetime, commit the decision and accepted `skill_outcomes` row in one SQLite transaction. `store_outcome()` commits itself; calling it before a separate decision write is insufficient. |
| Recover | After acceptance, repair the authority view against the same decision without repeating the memory effect, signature or timestamps. Retain and reject conflicting winners. |
| Read | Generic successful-pattern and direct SQL readers do not consult JSON authority. Never expose their accepted row before its transaction commits; Memex still applies current key, expiry, revocation and one-use checks. |

Existing owners: `reddog_verified_pattern_memory_sink.py`, `pattern_memory.py`,
`reddog_resident_queue_pattern_memory_admission_handler.py` and
`foundup_memex_verified_outcome_runtime_store.py`. The adjacent architect FIX
publisher supplies a recovery pattern, not interchangeable bound participants.
The next eligible local action remains **R11-B memory acceptance contract, 16/P0**:
resolve the existing purpose-specific write-authority/protected-use binding before
changing the sink transaction. A readiness marker, worker-supplied receipt or Memex
read capability cannot grant memory writes. R11-C/D and both production factories
remain closed. Composed process/volume recovery and retained benefit are unproved.

All 96 open PR file lists were inspected: no outcome-source/test owner collision;
PR #1680 shares only generated compatibility surfaces in this source slice and
remains untouched. Fresh source/owner ranking, exact commands, fingerprints and
limits are in `activation_recovery_continuation_20260914` in the existing baseline.
The pending 012 reader-policy question and separate AutoPost/product ownership
remain boundaries. All 26 packets and six substeps remain non-dispatchable;
re-observe and rescore after owned closure.

### Accepted-memory visibility checkpoint — 2026-09-14

Source: `916d81118bf37d8ba45b13ba2af9ec7d59d1b9c7`, merged PR
[#1738](https://github.com/FOUNDUPS/Foundups-Agent/pull/1738); its main CI and
CodeQL runs are verified successful. Fresh WSP 15/WSP 97 selected existing R11-B
**4/5/3/4 = 16/P0** after current source, ownership and dependency reconciliation.

The current composed regression failed: a real durable authority envelope became
readable after an injected memory activation failure. The existing
`AuthorityRuntimeVerifiedOutcomeStore` now accepts an explicitly configured
`accepted_outcome_source`. Its existing `load_verified_outcome(record_id)` method
must return the exact canonical accepted record before activation, after a new
authority commit, and at every consumable envelope read. Missing, changed or
unreadable records reject. Staged memory and readiness markers do not satisfy this
check. Cancellation propagates; exact publication history remains retryable.

The production publisher/reader factories remain unbound and therefore closed
for activation/consumable reads. Supplying a source object grants no authority;
current admitted composition must bind the correct participant. This guard is a
prerequisite for recoverable acceptance, not a cross-store transaction or a change
to every direct PatternMemory consumer. No production sink activation was added.

Validation: **181 connected Python tests passed**, including 64 runtime-authority
cases; **8 manifest tests** and **15 fast extension groups** also passed. One
initial fast-tier invocation lacked the worktree dependency-root setting; the
existing qualified environment resolved it without installation or a relaxed
guard. The runtime file is 285 lines and its existing test suite is 927 lines.
The 1,400-member manifest changes only this runtime hash and its two existing pins;
registry 1,650/269 remains current. Fixtures use real disposable JSON/SQLite
stores, digest-signature doubles and injected failures; no live admission proof.

Fresh re-observation closes this exposure guard and retains **R11-B recoverable
acceptance decision, 16/P0**, as the next eligible local work. The handler still
has separate activation callbacks and no factory binds an admitted participant;
reuse those owners and the existing adjacent two-phase publication pattern to
establish fault/retry behavior before activation. Higher runtime dependencies,
read-policy clarification and external product ownership remain separate. The
complete ranked queue, commands, source fingerprints and limits are in
`acceptance_visibility_continuation_20260914` in the existing baseline. All packets
and substeps remain non-dispatchable; re-observe again after owned closure.

### Competing-process response checkpoint — 2026-09-14

Source: main `35eb1e863b7ab73024f6d430f9b116bfeebd49d7`, following merged
PR [#1737](https://github.com/FOUNDUPS/Foundups-Agent/pull/1737). That merge's CI
and CodeQL runs are both observed successful. This continuation closes the
existing **15/P1** full-response process-race validation scope.

Two spawned processes now exercise identical and conflicting signed responses
through the existing root handler and real disposable stores. Conflicting
responses yield one winner; identical responses are idempotent. Reopening and
retrying preserves the winner's exact bytes, mirrored terminal digest and consumed
authorization. Distinct child PIDs, coordinated start and clean exits are checked.
The old bare-reservation test reuses the existing store factory while retaining
eight attempts/four workers; 64 other definitions remain AST-identical.

Validation: focused **7 passed**, then full service suite and three unchanged size
guards **138 passed / one Linux-only skip in 76.65s**. Counts overlap. The test
file remains 1,497 lines; registry 1,650/269 is current. No runtime source, manifest,
wire contract, new file or size exemption changed. This Windows fixture injects
peer/ownership decisions; it does not prove privileged Linux service behavior,
physical-volume failure or every possible process schedule.

Fresh WSP 15/WSP 97 reconciliation promotes the existing **R11-B recoverable
acceptance/visibility** substep to **4/5/3/4 = 16/P0**, the highest eligible
local source action. Current `_activate_published` still activates authority
before the memory sink; its existing failure test checks sink records using a
fake publisher. The earlier composed counterexample remains dated evidence.
First reproduce it against current real disposable stores in the existing tests,
then establish a recoverable decision through the existing owners. Do not merely
reverse callbacks or enable the production sink. This work does not depend on
granting response-read permission; live activation retains its separate gates.

| Work after this local closure | C/I/D/Impact | WSP 15 | WSP 97 disposition / next action |
|---|---|---|---|
| Independent execution/verification/promotion/activation | 5/5/4/5 | 19/P0 | Current independent runtime admission remains blocked. |
| Integrated FastMCP/MCP migration | 4/5/4/5 | 18/P0 | Local preflight exists; current owner/live lifecycle remains required. |
| WRE/OpenClaw/Hermes worker | 4/5/4/5 | 18/P0 | Reuse adapters; changed signed work/model/runtime admission is required. |
| Chroma deployment qualification | 3/5/4/5 | 17/P0 | Runtime owner/deployment dependency; no exposure inferred. |
| R11-B acceptance and visibility | 4/5/3/4 | 16/P0 | **Selected:** reproduce composed failure in existing tests; recoverable agreement before activation. |
| Authenticated response read | 4/4/4/4 | 16/P0 | Eligible-reader decision remains pending; no default permission. |
| Current semantic retrieval | 3/5/4/4 | 16/P0 | Governed owner qualification remains required; lexical UNKNOWN is not semantic proof. |
| Protected eSingularity work | 3/4/4/3 | 14/P1 | External ownership; preserve product work. |
| Existing AutoResearcher process/volume durability | 4/3/3/3 | 13/P1 | Later eligible disposable fixtures; ordinary Python-exit restore is already covered. |

The earlier ranking omitted R11-B as a separate authorable action while focusing
on R11-A. This re-observation corrects that omission without creating a packet.
No matching open PR currently owns the inspected root, acceptance or researcher
source paths; all runtime packets/substeps remain non-dispatchable. Re-observe
again after owned review/closure. Exact source, tests, ranking and limits are in
`process_race_continuation_20260914` in the existing baseline observations.

### Writer-process recovery checkpoint — 2026-09-14

PR [#1736](https://github.com/FOUNDUPS/Foundups-Agent/pull/1736) merged as
`18981983c1935bfed55ca8703b05629d2b9634ad`; its exact-head checks and subsequent
main CI/CodeQL succeeded. This cycle adds four cases to the existing root service
suite, using its real signed-record, SQLite and atomic-store fixtures.

An independently spawned writer exits normally, or uses `os._exit` after payload
persistence, after the primary terminal write before the witness, or after the
accepted reply is built. No Python cleanup runs on those three abrupt exits.
The parent confirms the exact exit code and both pre-recovery checkpoints, reopens
the existing stores, and retries the same signed request twice. Both mirrors reach
the same terminal digest, exact response bytes are preserved, and the consumed
authorization cannot be reserved again. The child receives public descriptor,
snapshot and signed-request data; no new outcome signing is needed in that child.

Validation: **136 passed / one Linux-only skip in 71.44s**, including the full
service suite and three unchanged size guards. The first run had four failures
from a misplaced test assertion; it was restored to its original case. All 64
previous definitions remain AST-identical. The file is 1,497 lines; no runtime
source, manifest pin, skill, module or new test file changed. Registry stays
1,650/269. Exact IDs, command, environment and hashes are recorded in
`process_exit_continuation_20260914` in the existing baseline.

This proves the selected local writer-process exits. It does not prove physical
volume/power failure, a privileged Linux socket service, competing full-record
processes, production runtime admission or retained learning. Peer/UID decisions
remain injected; the production read RPC is still absent.

**WSP 97 reconciliation:** read authorization remains **16/P0**, but the broad
prior `ELIGIBLE_LOCAL_AUTHORING` designation lacked an eligible-reader policy.
Existing signing, `get_secret`, and conversation-read grants do not establish it.
012 has been asked whether readership is limited to the current original signer
or also admits separately authorized recovery agents. That decision is pending;
elapsed time supplies no policy or authorization.

**Re-scored next action:** competing-process full-response commitment/recovery,
**4/4/3/4 = 15/P1**, using existing full-record thread and process-reservation
fixtures. Single-writer exit recovery leaves the outstanding queue. Higher runtime
and model items remain separately gated. Re-observe after closure, including any
012 policy answer. All 26 planning packets and six R11 substeps stay non-dispatchable.

### Root-record readback checkpoint — 2026-09-14

Source: merged PR1735/main `c7e2272fb555d0aef2657b94f142c9d7c7fbbb3d`;
its exact merge CI and CodeQL succeeded. Fresh WSP 15 retains readback at
**4+4+4+4 = 16/P0**, ahead of later eligible recovery fixtures. The nine-row
reassessment, unchanged dependency PRs/alerts and absence of competing root-owner
PRs are recorded in `root_record_read_continuation_20260914`. Higher runtime,
model and independent activation candidates still require current admission.

The smallest local prerequisite is now
`RootVerifiedOutcomeAuthorityState.load_committed_response_for_root(*,
expected_binding, expected_record_digest, expected_generation, now_epoch) -> bytes`.
It reuses the existing root lock, installation/ownership checks, fixed pending
store, bounded snapshot parser and signature/context validators. Before returning
the exact bytes, it requires the record's generation to match both the supplied
pin and current mirrored generation, and the authorization marker to be sequence
2 with the complete record digest. The pending selection must also match. The
original descriptor/grants must remain valid at the supplied current time.

Healthy repeated/reopened reads preserve the stored payload and terminal state;
one missing mirror uses the already-validated deterministic recovery path. Pending
or unavailable bytes, a valid but differently selected response, wrong pins,
non-integer generation, expired authority, rotation and conflicting state reject.
The method adds no signing call, reservation reset, caller-selected path or grant.

**Storage integrity is not read authorization.** A separately authenticated
current read admission must precede any external disclosure. The existing root
protocol/client/router remain unchanged, and a proposed read RPC still rejects.
Do not reinterpret conversation/Principal Memex read capabilities or WSP 71
`get_secret` grants as permission to disclose these records. Cross-generation
recovery, expired-record recovery and publisher integration remain separate.

Validation: a proposed-API control failed with `AttributeError` before the new
method existed; it is not an inherited production defect. The 30 new cases pass
in the existing service suite. Nine connected suites and three unchanged size
guards pass **348 tests / one Linux-only skip in 133.65s**. The source grows by
23 lines to 675; the service test file is 1,441 lines and reuses existing fixtures.
Runtime membership remains 1,400 with one changed source hash; registry remains
1,650/269. Packaging and exact commands/fingerprints are in the existing baseline.
Windows peer/ownership checks remain injected; no privileged Linux process or
physical-volume recovery, runtime activation or retained benefit is claimed.

**Re-scored next action:** purpose-specific current read admission and the
existing service/client route, **16/P0**. The local storage-read prerequisite is
removed from outstanding work. Re-observe current authority/source/ownership
before that slice; this method, its supplied pins and historical signatures
cannot mint permission. The state owner is at its existing 675-line ceiling;
future changes must preserve the guard. All 26 packets and six R11 substeps remain
non-dispatchable, and R11/G4/production RSI remain incomplete.

### Mirror restoration checkpoint — 2026-09-14

**Remote closure:** [PR #1734](https://github.com/FOUNDUPS/Foundups-Agent/pull/1734)
merged at `7f4f49b79692a1aa6484544c4e46115fe6690027` on 2026-09-14 06:07:08 UTC.
Its exact head `4f4e466f4151eb06676b60394a98a6cfb37c7d24` passed all ten reported
checks; GitHub reported no required-check set and no independent review. All
18 owned Git blobs match the merge, and the 13 incoming YUMORI paths are preserved.
The current selection is now based on post-merge observation, not pending PR
closure. WSP 15 was reapplied: the merged local repair leaves the queue; current
dependency alerts/PRs and runtime-admission dependencies do not change the remaining
scores. Readback remains **16/P0**, with its absent route confirmed in the existing
root protocol/service/router. Its next bounded step is to bind a fresh read request
to current authorization, exact record/context and terminal state using those
owners and their existing tests. A historical signing grant supplies no read grant.
See `merge_closure` and `post_merge_reobservation` under this checkpoint's existing
baseline key for separate local, exact-head CI and merge-CI evidence. This closure
adds no runtime implementation, service activation or retained-learning claim.

Base: PR1733/main `84e72cd55442a7cbe04e834642269d929b90e362`; exact merge CI and
CodeQL succeeded. Fresh ownership review found no open PR on the two selected
source owners or their closest tests. WSP 15 selected local mirror restoration
at **4+5+4+4 = 17/P0**; the higher migration/worker/activation candidates remained
without current admission. No packet order supplied an automatic assignment.

`SqliteMonotonicAuthorityStore.restore_missing_from_witness(binding_digest, *,
witness: SqliteMonotonicAuthorityReader, expected: ProposalReplayHighWater)`
reuses the existing readonly reader and identity checks. It requires the exact
reader class, the same repository context and disjoint storage roots; the source
must contain the exact expected checkpoint. Within a destination `BEGIN IMMEDIATE`
transaction it rechecks destination metadata and the source, then inserts only
when missing. An identical destination is an idempotent no-op; any other existing
checkpoint rejects. It verifies both stores again after commit. Exceptions before
commit roll back; an exception after commit can leave exact copied state and must
not be interpreted as acknowledgment. Retries revalidate current state.

The two missing-side branches of `RootVerifiedOutcomeAuthorityState._current()`
now call that operation under the existing confined root lock. Existing principal,
installation, peer, grant and generation checks remain with their current owners.
The generic `advance()` and readonly reader implementations are unchanged: normal
writes still require None → 1 or exact +1. No intermediate history is synthesized.
The store primitive supplies no grant, readback API or runtime admission by itself.
Its caller must serialize mirror use; it is not a cross-volume atomic transaction.

Tests reopen an exact configured store after its database file is lost, then
restore either side at sequences 1, 2 and 5. V1 and v2 commitment retries retain
the original terminal state. Corrupt identity, stale/wrong checkpoint, overlapping
domains, foreign repository context, conflicting destination, cancellation,
source changes and competing restorations reject or preserve the exact winner.
Loss of both mirrors still fails service use; this change cannot reconstruct
unavailable signed response bytes. The payload remains a separate single copy.
Physical volume failure and privileged Linux service recovery need later proof.

Validation: the expanded pre-change recovery test had **4 failures / 2 passes**,
reproducing the sequence-2/5 defect in both directions. Focused validation passed
136 with one skip. Final connected selection: **318 passed / one Linux-only skip
in 113.80s**, including three unchanged size guards. Packaging passed 8 manifest
tests in 68.57s and 15 fast groups in 3,804ms. The fast harness first rejected a
default C: temporary path, then CRLF in the edited JavaScript pin; setting the
required O: temp root and restoring LF resolved both without changing a guard.
Runtime membership remains 1,400; exactly two source hashes change. Test registry
remains 1,650/269. Source is 450/652 lines; interface/guard ceilings are unchanged.

**Re-scored next action: independently authenticated response readback, 16/P0.**
The local missing-mirror implementation is removed from outstanding work.
Higher candidates remain blocked: independent execution/promotion/activation
19/P0; integrated MCP migration and admitted WRE worker 18/P0; Chroma deployment
qualification 17/P0. Semantic qualification is 16/P0 under its existing owner.
Local process/volume recovery qualification is 15/P1, protected product observation
14/P1, and AutoResearcher durability 13/P1. Readback wins as the highest eligible
local action after the new evidence/ownership review. Use the existing record,
root protocol/client/service and current authorization owners; a digest or
historical signing grant cannot create current read authority. Re-observe again
after closure. Normal v2 signer/publisher wiring, readback, whole-operation
deadlines, independent activation and retained benefit remain open; R11/G4 and
all 26 planning packets/six R11 substeps remain incomplete/non-dispatchable.

### Dependency qualification checkpoint — 2026-09-14

Source: merged PR1732/main `1173d1ab5e4af8a0e3cbe5381bcd30cf0e865ac3`.
Its exact CI/CodeQL runs succeeded. WSP 97 reuses the
[existing MCP assumption audit](../../modules/infrastructure/foundups_mcp_bridge/docs/clarity/REDDOG_CHATGPT_HOLO_QUERY_BUNDLE_MCP_ASSUMPTION_AUDIT_20260821.md#6-dependency-qualification--2026-09-14),
PR1526/1525, launcher pin checks and existing snapshot tests. Production source,
pins and runtime admission are unchanged; the candidate venv is a disposable test.

The FastMCP-only upgrade fails dependency resolution. The paired quartet resolves
and passes 25 existing MCP tests in a disposable venv. The query interpreter passes
38 launcher/MCP/snapshot tests; these include the same 25 MCP cases. Both runs
deselect the two fixed-port service tests. Existing code uses direct MCP tool
registration and immutable readonly query snapshots; no affected OpenAPI/Chroma
server setup was found in the bounded source/configuration search. This does not
establish deployment exposure or close the three manifest alerts. Both one-line
PRs also omit the intentionally exact `MCP_RUNTIME_VERSIONS` contract.

**Local qualification is complete; runtime migration is not.** Reconcile both PRs,
the launcher pins, admitted replacement bytes and owned live lifecycle before
changing the shared runtime. Chroma has no first patched version in the observed
alerts. Preserve current services and the separate AutoPost/product lanes.

| Re-scored action | C/I/D/Impact | WSP 15 | WSP 97 disposition / next step |
|---|---|---|---|
| Independent execution/verification/promotion/activation | 5/5/4/5 | 19/P0 | Blocked on current admission and independent evidence; no dispatch. |
| Integrated MCP migration; admitted WRE worker | 4/5/4/5 each | 18/P0 each | Existing owners/contracts; runtime/model admission not established. Qualified package resolution is not activation. |
| R11 authenticated restoration of a missing later-sequence mirror | 4/5/4/4 | 17/P0 | **Selected local authoring.** Extend existing root authority/store owners and closest tests; preserve generic CAS monotonicity. |
| Chroma deployment qualification/mitigation | 3/5/4/5 | 17/P0 | Runtime-owner dependency; source search cannot establish current live exposure. |
| R11 independently authenticated readback; current semantic retrieval | 4/4/4/4; 3/5/4/4 | 16/P0 each | Readback follows recovery; semantic qualification stays with the governed owner. |
| Protected eSingularity observation | 3/4/4/3 | 14/P1 | Separate owner; no product edits. |
| Existing AutoResearcher process/volume durability | 4/3/3/3 | 13/P1 | Later eligible local fixtures. |

The previous dependency preflight is removed from outstanding executable work.
Mirror restoration wins after the new eligibility review, not because it was the
previous runner-up. Its surviving witness must be authenticated before restoring
a missing marker; do not loosen None → 1 CAS or synthesize intermediate history.
Re-observe and rescore again after this checkpoint closes. Production RSI, R03/R04,
R11/G4 and all planning-packet admission remain incomplete.

### Full-record commitment checkpoint — 2026-09-14

Base: PR1731/main `b2ae1e159c22bd9de67cfef8eb4bb062e5a517f8`.
Fresh WSP 15 selected R11-A terminal commitment at **4+4+4+4 = 16/P0**.
The prior recursion policy is merged and current-main CI passed; no open PR
claimed these source files. This is authorized isolated local authoring, with
disposable stores/signatures. It supplies no independent runtime admission.

The existing root protocol/service/client now support exact canonical **v2
`COMMIT_RECORD`** requests and responses. V1 parsers, wire fields and proof domain
remain separate. V2 covers the complete immutable response record, its externally
supplied digest, reservation/request context and a domain-separated current E0
signer proof. The normal root router reaches the same current descriptor,
owner/state binding, kernel peer, grant, revocation, expiry and signer checks.
The inner signing event must also match the exact outer reserved request.

`commit_pending_response()` reuses the pending writer under the existing root
lock. It validates current generation and exact reservation, pins the record in
both mirrors, persists and verifies exact bytes, then commits sequence 2 with the
**full record digest** as its revision. The standalone pending method still
leaves sequence 1 reserved and rejects terminal state. A competing valid response
cannot replace the selected winner; v1 and v2 terminal states cannot substitute
for one another. Exact acknowledgment retries revalidate current authority and
stored bytes. Caller-retained exact bytes can repair a missing payload file;
digest-only state cannot reconstruct that payload or authorize a read.

`commit_service_response_record_proof_input()` bounds the entire enclosing
message before proof signing; `commit_service_response_record()` performs one
root-authenticated exchange and requires an exact v2 acknowledgment. There is
no hidden transport retry. Explicit same-process retry retains the original
reservation seal, record, issuance and proof. Existing transport timeouts remain
per socket operation (default 5 seconds, maximum 30), not a combined wall deadline.
The complete request including escaped nested bytes and newline must fit 64 KiB;
an inner record that fits by itself may still reject before any persistence.

Storage still has eight slots and a complete 512 KiB snapshot, with no eviction
or retention-policy change. The pure existing pending JSON codec moved into the
existing root wire-codec owner; serialization and public state exports are kept.
The root state remains below 675 lines / 50 per function; no exemption was widened.
Existing signing fixtures are shared with the root service suite, not duplicated.

**Observed recovery gap:** deleting an entire mirror after sequence 2 rejects
with `monotonic_authority_not_monotonic`. The generic CAS permits only None → 1,
so the existing `_current()` repair cannot reconstruct a missing later marker.
A disposable v1 control reproduces this with the repair method unchanged from
the base. A one-step lagging mirror is repairable; total mirror loss at a later
sequence is a distinct case. Current behavior preserves the surviving terminal
marker and fails closed. No intermediate history, reset or authority is fabricated.

Local verification: **279 passed / one Linux-root skip** across eight suites
(201/1 focused, 78 connected). The first expanded run had one failed positive
expectation for whole-mirror restoration; the explicit negative regression and
v1 control now preserve that limitation. Test registry remains 1,650/269; runtime
membership remains 1,400 with five changed source hashes. Packaging passed
15 fast groups in 3,529ms and 8 manifest + 16 unchanged WSP 62 checks in 65.51s.
Exact source/test fingerprints are recorded in `full_record_commit_continuation_20260914`.

Local re-observation ranked **authenticated restoration of a missing later-sequence
mirror at 4+5+4+4 = 17/P0**, ahead of authenticated readback at 16/P0. Subsequent
read-only GitHub/source observation changed the next system action again: critical
alerts target `chromadb==1.5.5` in `holo_index/requirements.txt` (alerts 322/286)
and `fastmcp==2.13.0.2` in the MCP bridge requirements (alert 317). The query
interpreter reports ChromaDB 1.5.5 and FastMCP 3.2.0; this metadata does not prove
which service is active or whether an affected feature is reachable. GitHub reported
no first patched ChromaDB version for these alerts at observation. No upgrade is
assumed safe from the manifest alone.

**Next system preflight: Holo/MCP dependency exposure and pin reconciliation,
3+5+5+5 = 18/P0.** Read primary advisories and existing service/deployment/runtime
contracts, verify reachability and current mitigation ownership, then choose an
isolated fix if supported. No live package changes, service restarts or protected
FoundUp work occurred. The other critical manifest alerts remain recorded owner/
scope inputs, including protected eSingularity. After that qualification, rescore
again. Mirror restoration remains the next R11-specific action; use existing owners
and tests without loosening generic CAS or synthesizing sequence-1 history.
The ordinary signer finalizer still uses v1. Independently authorized readback,
normal signer/publisher integration, a whole-operation deadline, real process/volume
recovery, memory activation and measured retained benefit remain open. R11-A/R11/G4
and every planning packet remain incomplete/non-dispatchable.

### Pending-response storage checkpoint — 2026-09-14

Final local verification: **226 passed / one Linux-only skip** across eight
distinct suites. Packaging: **15 fast groups in 3,378ms** and **8 staged-manifest
tests in 63.94s**, with two pytest configuration warnings. Runtime
membership is unchanged at 1,400 with one changed source hash and matching pins;
test registry remains current at 1,650 files / 269 quarantined. Guards are
unchanged; the existing interface metadata decreases from 1527 to 1517.

Base: PR1728/main `bec40ffe52cd0076013a4bb9e5f7629b683741be`.
WSP 00 awakening/strict software gate passed. WSP 97 reused the exact root state,
immutable-record validator and atomic writer. The refined lexical query returned
both owners, with the POSIX writer as secondary context. Module contracts were
present; optional design/memory/requirements artifacts remain absent. Peripheral
initial hits were removed. Freshness remains UNKNOWN/gap with zero semantic-owner
attempts; workspace HEAD matches the base. No unchanged blocked runtime/model
probe was repeated. WSP 15 local planning is **4 + 4 + 4 + 4 = 16/P0**.
This automated continuation uses 012's existing local authoring instruction;
it is not a WRE allocation, independent verification role or runtime admission.

**Implemented:** `RootVerifiedOutcomeAuthorityState.persist_pending_response`
reuses `AtomicJsonAuthorityRuntimeStore` under the already owner-bound primary
root at `verified-outcome-pending-responses.json`. No configurable path, owner
schema or additional storage domain is introduced. Under the existing root lock,
the current owner generation and exact reserved tuple must match. Full co-signed
history, signatures and the caller's supplied current epoch are validated first.
A separate mirrored sequence-1 selection pins the **full record digest before
payload storage**. The outcome grant stays sequence 1 (reserved), not terminal.
Every retained row is verified against its own mirrored selection before mutation
and acknowledgment. Real ownership is required by the production state owner;
the new boundary checks the pending file before load and acknowledgment.

The snapshot permits at most **eight records** and **512 KiB including the complete
pretty-printed JSON, revision and newline**; individual records retain 64 KiB.
Capacity rejects before selecting the new record, with no eviction. Repeated exact
bytes are acknowledged; different valid responses, conflicting persisted bytes,
unanchored rows, wrong generation/reservation/digest, expired context and terminal
grants reject. Interrupted writes keep the selection pinned. Lost acknowledgments
require an exact validated readback. One missing state replica uses the existing
repair; loss of both cannot bypass the installation witness. Cancellation remains
visible, and no failure resets the outcome reservation or signs again.

**Validation scope:** disposable real SQLite mirrors and real Ed25519 fixtures.
The fixture captures actual signed bytes immediately before v1 finalization;
it does not wire the new method into the live backend. Twenty-two new cases extend
the existing signing suite to 94 cases. Connected service, descriptor, startup,
provisioning, runtime-binding and protected-use tests pass **116 / one Linux-only
skip in 36.89s**. Ownership decisions in two Windows cases are injected, not proof
of Linux UID isolation. Real process kills, whole-volume failure and concurrent
processes have not been exercised; the concurrency case uses two state instances
and threads. Exact commands, failure history and packaging results are recorded in
`pending_response_continuation_20260914` in the existing baseline observations.

**WSP 62/97 closure:** the combined check found inherited interface metadata
1527 versus 1620 actual lines. Its full outcome contract is preserved verbatim in
the API reference below; the module now carries a smaller API index and a reduced
existing exemption, not a larger ceiling. README history is consolidated into
current R11 pointers. Runtime source stays below its 675-line ceiling with every
function at most 50 lines and every pre-existing method/function unchanged.
The signing test file is now in the 1000–1500-line critical window: keep subsequent
RPC/readback cases in the existing root service/client suites and reuse current
fixtures; review cohesion before further growth, with no new exemption or module.

**Remaining:** this is a local pending-byte primitive. Caller-supplied pins/time
are not authentication. Payload bytes are a single primary-domain copy; mirrored
selection digests cannot recover them. A missing file can only be repaired from
caller-retained exact bytes. Capacity bounds the current snapshot, not a new
cross-domain retention policy. Next is a versioned full-record commitment in the
existing root service/client with fresh owner, peer, signer proof and revocation
checks, then separately authorized readback and signer/publisher restart recovery.
Keep complete enclosing-wire limits and an operation deadline explicit. R11-B–F,
production isolation/launch, independent memory activation and measured later
benefit remain open. All 26 packets and six R11 substeps remain non-dispatchable.

### Verified-outcome API reference

The following contract moved verbatim from the module interface at PR1728; its
historical validation, root v1, publication and memory conditions remain in force.
The pending-storage addition is defined in the checkpoint immediately above.

Architect proposal attestation v2 requires a typed `OperationalMemexSupplyReceipt`;
promotion rehydrates its complete serialized form, recomputes the canonical ID,
rejects unknown/stale/scope-mismatched inputs, and signs its full digest. Outcome
rehydration checks canonical verifier/held-out receipts. The system-service
signer loads an exact root-owned v2 outcome-authority descriptor and an opaque
client for a separately launched root authority service. The service owns
disjoint primary, witness, and one-time installation monotonic stores; the
signer owns none of them. Each
co-signed grant binds FoundUp, snapshot,
work order, slice, job, worker, exact head/content, runtime, PatternMemory record,
signer key/epoch, and the current signer run packet/config/session/manifest
generation through an immutable authority-context digest covered by both
independent signatures. Only a root-UID-authenticated socket exchange can mint
the opaque E0 capability; every key-provider constructor verifies that boundary
before resolving key material. Every reserve and commit additionally carries a
domain-separated Ed25519 proof from the exact current E0 signer key, while fresh
kernel UID/GID credentials are checked against the current root config. The
root service burns a reservation before signing, then re-reads current root
configuration and rechecks revocation, generation, grant, reservation, signer
proof, and signature digest before commit. After those same checks, an exact
already-committed reservation/digest is acknowledged without advancing or resetting
the terminal marker. `commit_service_authority(...)` retries identical encoded
request bytes once for ConnectionError/TimeoutError only. Plain OSError ownership
or size failures, malformed replies, explicit rejection and cancellation do not
retry. Each exchange retains its configured timeout (default 5 seconds, maximum
30); there is no combined deadline across the two attempts. No protocol/schema or
method signature changes. The response contains no full outcome signature payload,
and the opaque reservation seal remains process-local; acknowledgment recovery
does not supply durable outcome-response recovery. Runtime startup cannot initialize or
reset replay state. The separate installer rejects after its third-domain
commit, including after both replay stores are deleted. A failed or crashed
reservation never reopens. Every current snapshot must match the exact roots,
paths, store IDs, and durability receipts opened at service startup; state-store
rotation therefore rejects until a supervised restart. The production isolated
signer applies its Linux E0 boundary before key resolution: distinct non-root
UID/GID matching the root-owned v2 owner config, YAMA ptrace controls, no
`CAP_SYS_PTRACE`, disabled core/dumpable state, and a cleared inherited
environment. The legacy CLI and one-shot isolated-process composer reject every
non-test provider before authority, resolver, or socket access. Only the stable
service is production; it derives manifest, outcome authority, owner ID, and
signer UID/GID from one authenticated v2 snapshot. Legacy v1 cannot start it;
test-only dry-run is non-authoritative. The same root service optionally routes opaque `RootRevocationAnchorAuthority.load()`/`advance_snapshot()` operations with no caller-selected CAS state, holding `lease_validated_owner_e0_current_admission()` through signed policy, topology, snapshot, witness, and monotonic validation.
An absent outcome policy leaves unrelated signer operations available. The root protected-use protocol can atomically order revocation and one callback, but production E0 activation remains blocked until the service startup factory supplies that capability with authenticated grants and WSP71 resolution.
Owner, generation, key, expiry, revocation, replay, or grant mismatches reject.
Resident production admission remains blocked until the root service is deployed
and independent verifier runtimes issue both grant signatures. Staged authority
envelopes remain non-consumable until exact activation.
`AuthorityRuntimeVerifiedOutcomeStore.load_publication(record_id)` reads STAGED
or ACTIVE evidence for the existing publisher's retry check, returns `None` when
absent, and raises on invalid durable state. It is not the consumable source.
`SignedVerifiedOutcomeEvidencePublisher.publish()` acknowledges a byte-equivalent
existing envelope after checking exact requested evidence, publisher identity,
original issuance and signature. It does not re-sign, rewrite, renew or activate
on retry. `load_envelope()`/`load_verified_outcome()` still hide staging.
`AuthorityRuntimeVerifiedOutcomeStore(store, *, accepted_outcome_source=None)`
requires its configured source's `load_verified_outcome(record_id)` to return the
exact accepted canonical record at activation and envelope reads. A new activation
checks again after commit; ACTIVE retries recheck the source. Activation pins
the original envelope digest and reloads durable state after every commit attempt.
An exact ACTIVE winner recovers a lost acknowledgment; only revision conflicts
retry, at most three commits. An uncommitted reply, substituted envelope or
unreadable state cannot acknowledge success. Cancellation propagates. Missing, changed or
unreadable memory rejects, including a historically ACTIVE envelope with no bound
source. Publication staging/retry remains available unbound. The source must be
bound by current admitted runtime composition; this interface supplies no permission
or cross-store transaction. Runtime authority still checks current key, revocation
and expiry.
`validate_verified_outcome_signing_response(response, signing_input, *,
signer_public_key, key_epoch, requester_principal_id, signature_verifier)` is the
shared predicate in `foundup_memex_verified_outcome_signing.py`; the publisher's
existing validation wrapper calls it. Acceptance, boundary/requester attestations,
untrusted-code exclusion and secret exclusion require exact `True`, as do both
signature-verifier results. A present rejection code must be empty. Original
receipt and outcome-domain audit signatures, key, fingerprint and epoch remain
bound. The predicate performs no persistence, issuance renewal, state transition, current
read-authorization check or record deserialization. Malformed attributes or
dependency exceptions can still raise; consumers must fail closed. Its result
cannot authorize durable response replay or construct a process-local capability.
`VerifiedOutcomeResponseBinding(descriptor_id, owner_config_id,
authorization_id, reservation_id)` is frozen public identifier data, never a root
reservation capability. `build_verified_outcome_response_record(request, response,
*, descriptor, binding, signature_verifier) -> bytes` snapshots a v1 record using
the existing root codec. `parse_verified_outcome_response_record(raw, *,
expected_binding, expected_record_digest, signature_verifier) ->
tuple[SigningRequest, SigningResponse]` returns the original typed pair after
canonical/full-record digest, scope, co-signed descriptor and receipt/audit checks.
The complete record includes its response digest, full descriptor/grant context
and the four root identifiers. V1 requires exact string/boolean fields, omits the
unsupported elevated-consensus proof, rejects unknown/missing fields and duplicate
keys, and caps the full ASCII canonical JSON plus newline at 65,536 bytes.
Historical validation uses original issuance; replay anchor identifiers receive
shape checks without touching their store. Expected bindings/digest must come
from an independently authenticated owner, not the parsed record. The parser
does not supply that authentication, fresh expiry/revocation/read authority,
durable root commitment, process-local seals, persistence or memory activation.
The local v2 root commit route now consumes this record through the existing
pending-state owner and checks the complete enclosing wire limit. Ordinary signer
finalization still uses v1; current read authority and publisher recovery are separate.

`AuthorityRuntimeVerifiedOutcomeStore.publish()` bounds revision-conflict retries
to three commit attempts, preserving the signed envelope and unrelated current
state. Other errors are not retried. On publication OSError/RuntimeError/ValueError,
the signed publisher may acknowledge only a reloaded, fully validated durable
publication, including an equivalent winner with its original issuance/signature.
Missing or invalid evidence still rejects. Signing failures and cancellation are
not publication recovery; no burned signer reservation is reset. This does not
recover process death before an envelope is durable or activate memory.
`ResidentQueueChainResultReceipt.recorded_at` is optional for historical objects;
new accepted `record_resident_queue_stage_result()` writes require a timezone-aware
`now_iso` and persist it once. Earlier receipts and transition IDs are preserved;
the canonical snapshot revision covers the field. Admission derivation requires
one held-out-stage receipt with a matching queue/slice/transition ID and valid
nonfuture timestamp in a canonical snapshot. It reuses that time as `verified_at`.
Snapshot `updated_at` and the current bootstrap clock cannot backfill missing
historical event time. Old histories remain readable; timestamp-less admission
requires owner-controlled recovery. This integrity check is not signed authority.
PatternMemory admission
uses an invisible staging table in the existing database. Conflicting existing
rows and legacy hash-shaped compatibility markers reject. Staging snapshots
the input, reconciles a competing record-key insert without replacing the
winner, and checks exact stored payload/agent before commit. Same-record retry
returns the same ID; staging remains outside recall. Active-row retries compare
the stored payload's canonical JSON with the requested canonical JSON. Values
such as `true`/`1`, `12`/`12.0` and `0.0`/`-0.0` conflict even when Python
equality accepts them; existing record IDs and digest serialization are unchanged.
This does not make
activation and authority revalidation one atomic transaction. The real sink is deliberately
not activation-ready until it can independently revalidate a durable authority
source; direct sink activation is forbidden. Authority-envelope consumption reloads
the durable envelope, resolves the key from the current committed authority profile,
checks revocation, freshness, FoundUp/snapshot/head/content/work/slice/job/worker/
verifier/runtime lineage, and issues an opaque one-use capability. The FoundUp Brain
assembler consumes that capability against the same durable replay state. Raw
booleans, raw receipt IDs, caller-supplied records, and serializable capability
markers are never authority. `gate_foundup_memex_learning_candidates()` emits exception-total, pre-traversal-bounded, canonical, digest-bound `STRUCTURAL_ONLY` candidates from structurally self-consistent assembly-receipt-bound Memex views plus Breadcrumb/verified-outcome evidence; this is not authenticated view provenance. Governed research fails closed until an authenticated authority exists, and caller-supplied receipt IDs never authorize it. `verify_foundup_memex_learning_candidate_reconstruction(candidate, proposal, evidence)` requires the exact proposal and evidence closure. The gate is non-runtime-admissible and performs no persistence or mutation.
Brain writes, runtime source adapters, roadmap writes, default Memex supply, and HoloIndex mutation remain outside this interface. `ExternalSignerAuthoritativeUseLeaseIssuer` extends socket-v2/E0 with an opaque exact-effect capability bound to the root-selected signer profile, current generation, and durable replay root; substitution, replay, expiry overrun, rollback revival, and socket-v1 downgrade reject, while production remains inactive until the external signer lifecycle and live canary are provisioned.

### Immutable-response record checkpoint — 2026-09-14

Packaging: **15 fast groups in 3,013ms**, **8 staged-manifest tests in 64.36s**
(two pytest configuration warnings). Runtime membership remains 1,400 with one
changed source hash and matching pins. The registry is current at 1,650 files /
269 quarantined; no guard or membership changed.

Base: PR1727/main `1103f7b218d71d8592d1e8b391ea6b8290275496`.
WSP 00 awakening/strict software gate passed. WSP 97 retrieved current owners
and reused the existing outcome-signing suite. The refined lexical query returns
the exact source/test pair; direct imports supplied the codec and full descriptor
validator. Required module contracts are present. Peripheral memory hits were
removed; optional design/memory artifacts and requirements remain absent.
Freshness is UNKNOWN/gap, workspace HEAD matches the base, and semantic-owner
attempts remain zero. No unchanged blocked runtime/model probe was repeated.

**WSP 15 correction:** canonical section 4 assigns 16–20 to P0, 13–15 to P1.
This layer scores 4 + 4 + 4 + 4 = **16/P0**: difficult authority/context integration,
critical recovery dependency, needed next for progress, major retained-learning
value. Three earlier baseline observations incorrectly labeled 16 as P1. Their
original objects are preserved with an explicit erratum in
`response_record_continuation_20260914`; current prose labels are corrected.
This is local planning under 012's authoring instruction, not runtime allocation.

**Implemented:** the existing `foundup_memex_verified_outcome_signing.py` now
builds immutable canonical response-record bytes and parses them against an
external expected context and digest. It reuses the root bounded/duplicate-key
codec, full co-signed descriptor validation and shared receipt/audit verifier.
The record binds the complete descriptor/grant context, exact request/response,
original issuance/key/epoch, root descriptor/owner/authorization/reservation IDs,
response digest and full-record digest. V1 rejects unknown/missing/coerced fields,
elevated-consensus proof payloads, malformed anchor identifiers, noncanonical
bytes, tampering and complete messages over 64 KiB, including the newline.
Original function/class definitions and root service v1 semantics are preserved.

**Verification:** 51 added cases extend one existing file (72 cases total).
The first control documented the absent proposed API. Initial implementation:
67 passed in 19.17s. Extended counterexamples found three malformed co-signed
anchor fields accepted by the new parser; exact identifier-shape checks fixed
them. The final nine-suite selection passes **294 tests / one Linux-root skip
in 51.29s**. Real disposable root stores and Ed25519 fixtures preserve one outcome
signature and the consumed terminal marker. Serialization survives caller
mutation, cannot create a root capability, and does not renew ordinary signing.
A valid 65,536-byte complete record passes; 65,537 bytes reject. Commands, source
hashes and failure logs are bound in `response_record_continuation_20260914`.

**Remaining:** public identifiers and externally supplied digest arguments are
data; this parser does not authenticate their provenance or prove a root commit.
Historical validation at original issuance supplies no current read authorization,
expiry/revocation check, grant renewal, persistence, publication or activation.
The next layer is root-owner-bound pending storage using the existing atomic
store, with exact-byte conflict and durability tests. Full-response terminal
commitment, separately authorized readback, enclosing-wire capacity, process-kill
recovery and R11-B–F remain open. No new module, scheduler or active FoundUp test;
all 26 packets and six R11 substeps remain non-dispatchable.

### Signer-response handoff checkpoint — 2026-09-14

Packaging passed: **15 fast groups in 3,372ms** and **8 staged-manifest tests
in 62.51s** (two pytest configuration warnings). Runtime membership remains
1,400 with two changed source hashes and matching pins. The current 1,650-file /
269-quarantined registry and all existing guards are unchanged.

Base: main `96b70c085711da16e57d582b03ffa063b8227025`, containing PR1723 and
one separate eSingularity frontend change. The latter stays outside this scope.
WSP 00 awakening/strict software gate passed. Local WSP 15 planning is
4 + 4 + 4 + 4 = **16/P0**; this app continuation supplies no runtime allocation.

Retrieval was initially noisy: lexical path matching favored peripheral test
fixtures. An exact outcome-signing query recovered its current source and test
file. Direct imports/call sites supplied the publisher, root protocol/state,
conversation/control anchors, secret-grant wrapper and startup owners. Required
module contracts are present; optional design/memory artifacts and requirements
are absent. Hit arrays were deduplicated and ordered by the actual signing path.
Freshness remains UNKNOWN/gap with zero semantic-owner attempts; workspace
evidence matches the base. No unchanged model/runtime probe was repeated.

**Implemented prerequisite:** `validate_verified_outcome_signing_response(...)`
now lives in the existing outcome-signing module, extracted from the publisher.
The publisher delegates to it. It preserves original key, epoch, fingerprint,
receipt signature and outcome-domain audit verification, requires exact `True`
for all five acceptance/attestation flags and both verifier results, and rejects
a present nonempty rejection code. It does not deserialize a durable record,
check current read authority or grant replay. No new module or scheduler exists.

**Verification:** four new root-backed cases compose the existing Ed25519 backend
with real disposable primary/witness/installation stores. A successful control
signs once; interruptions before/after root commit leave sequence 1/2 consumed;
reconstructed stores and a fresh client seal reject another ordinary signing use.
At the signer clock +61 seconds, the original request fails signing freshness;
changing issuance still cannot reuse the consumed root grant. The counter covers
all receipt-domain signatures, including altered issuance. These are injected
interruptions and object reconstruction, not OS-process death or production UID
proof. The real Linux-root socket case remains skipped locally.

Thirteen validator counterexamples failed before repair (one positive control
passed, five cases deselected, 1.81s): integer/string boolean claims, contradictory
rejection and truthy verifier returns. The focused repaired suite initially passed
19 cases in 3.11s; separate receipt/audit verifier cases then expanded it to 21.
The connected run caught an import still used by publication retry: 19 failed /
188 passed / one skipped in 32.12s. Restoring that import retained the retry
contract. Final eight-suite result: **207 passed / one skipped in 31.12s**.
Exact commands, hashes and failure evidence: `response_handoff_continuation_20260914`.

**Remaining handoff design — not runtime admitted:** the full-record checkpoint
above implements the local terminal-commit route. Continue extending the
existing root outcome owner for commitment/readback and reuse the current atomic
JSON store for bounded response bytes. Do not repurpose conversation or control
receipt authority, and do not add a generic outbox. Keep the following layers
ordered within R11-A; none is an executable work order.

| Layer | Existing owner and required contract | Acceptance boundary |
|---|---|---|
| Immutable response record — local prerequisite implemented above | `foundup_memex_verified_outcome_signing.py`: bind the exact canonical SigningRequest/SigningResponse, complete outcome-grant context, root reservation, original issuance, key/epoch and full response digest. Reuse the shared response validator. | Exact bounded schema; reject unknown/coerced fields, changed response/audit/signing input, foreign scope and digest substitution. No credentials, private keys, caller-selected paths or executable capabilities in serialized data. |
| Durable pending bytes — local primitive implemented above | `RootVerifiedOutcomeAuthorityState` with `AtomicJsonAuthorityRuntimeStore` and existing confined operation locks. Bind storage locations and durability to current root-owner configuration before writes. | Persist validated immutable bytes before terminal response commitment; pending bytes are unreadable to publication/learning. Preserve conflicting winners. Missing replicas or rollback cannot silently create authority. |
| Terminal commitment — local v2 route implemented above | Existing root service/client/protocol and pending state owner bind the complete record digest. | V1 remains separate. V2 commits after exact durable readback and acknowledges only the same record under current peer/proof/grant checks. The mirror-restoration checkpoint above closes local one-sided recovery after exact store reopening; both-mirror loss and physical process/volume qualification remain open. |
| Authenticated readback | Existing root owner, current principal/peer resolver and independently authorized work/grant boundaries. Bind current requester and immutable historical response separately. | Revalidate current owner, caller, scope, expiry/revocation and key policy. A consumed secret-access grant or serialized client seal is not read authority. Readback must not invoke ordinary outcome signing or manufacture a fresh grant. Cross-generation recovery requires explicit current independent authority. |
| Publisher handoff | Existing publisher/runtime store and the shared response validator. | Reuse original request, response, issuance and event identity; ordinary signing's 60-second freshness rule is not a recovery API. Verify durable root commitment plus current read authority before publication. No acceptance or memory activation is implied. |

The required order is: validated response → durable pending bytes → exact terminal
commitment → authenticated readback → existing publication contract. If the
process dies before any response is durable, the reservation remains consumed
and owner-controlled recovery is required. If only bytes survive, they remain
pending; if only a commitment survives, do not reconstruct a signature from its
digest. A successful ordinary exception cleanup is not proof of abrupt process
death cleanup. The outer secret-grant/protected-use lifecycle remains a separate
composition prerequisite; `ResolvePerSignSignerBackend` consumes its grant before
the signing callback, and root protected use completes before returning a result.

Bound the complete new wire record within the existing 64 KiB transport ceiling;
reject oversize input before persistence. Specify store capacity/retention,
operation deadline, owner recovery and version compatibility before activation.
Verify real process kill/restart, competing writers, partial replica loss,
fresh expiry/revocation and absent/forged read authority in the admitted target
environment. R11-B–F, legacy event recovery and measured later benefit stay open.
All 26 packets and six R11 substeps remain non-dispatchable.

### Root-commit acknowledgment checkpoint — 2026-09-14

Packaging passed: **15 fast groups in 4,658ms** and **8 staged-manifest tests
in 62.11s** (two pytest configuration warnings). Runtime membership remains
1,400 with two updated source hashes and matching pins. The registry is current
and unchanged at 1,650 files / 269 quarantined; no guard changed.

Base: PR1722/main `15fafb8d828d93e229796fff722cb5e806988aeb`.
WSP 00 awakening/strict software gate passed. Local WSP 15 planning is
4 + 4 + 4 + 4 = **16/P0** under the existing 012 authoring instruction.
This isolated source continuation supplies no signed allocation or runtime grant.

WSP 97 retrieval evaluation: the first lexical query was noisy; an exact-owner
refinement found the existing conversation response anchor. Deduplicated hits,
direct imports and module contracts identified the outcome root service/client
and their current test file. Tier-0 contracts are present; optional design/memory
artifacts and requirements.txt are absent. Workspace evidence matches the base;
semantic freshness remains UNKNOWN/gap, with zero owner attempts. No reindex,
new model dispatch or repeated missing-runtime probe was attempted.

The existing root service acknowledges only the exact durable terminal marker,
including the reservation binding and signature digest. The state owner's
existing terminal acknowledgment behavior provided the precedent. A repeated
COMMIT still passes fresh snapshot, generation, peer, grant and signer-proof
validation; changed reservation/digest, expiry or revocation rejects. RESERVE
remains burned. The existing client retries once only for ConnectionError or
TimeoutError, with identical encoded request bytes, proof and request ID.
Plain OSError ownership/size failures, malformed replies, explicit rejection and
cancellation do not retry. Each exchange retains its configured per-call timeout;
two attempts can consume two timeouts. No shared operation deadline is claimed.

**Verification:** 17 cases extend the existing root-service test file. The first
16 cases produced **9 failed / 7 passed / 22 deselected in 8.02s** before repair;
these include assertions for the proposed retry bound and fresh revalidation,
not nine distinct production defects. The focused result was **17 passed /
22 deselected in 8.18s**. The connected run first exposed the existing Windows
spawn/importlib callable failure (**114 passed / 1 failed / 1 skipped**).
Using the canonical import preserves its eight-attempt, single-reservation-winner
assertion. The final six-suite selection passes **115 tests / 1 skipped in
36.42s**. Disposable SQLite primary/witness/installation stores and Ed25519
fixtures cover exact replay, four concurrent acknowledgments, before/after-commit
reply loss, changed receipts, fresh revocation/expiry, protocol rejection,
cancellation and the two-attempt limit. The real Linux-root socket test is
skipped here; these results do not establish production peer or process isolation.

**Next R11-A step:** preserve and recover the full signed outcome response across
process death before publication. The root protocol stores a digest, not those
response bytes, and the client reservation seal is process-local. The conversation
anchor already stores full responses under a different operation/principal/session
policy; it cannot authorize outcome recovery. Extend the existing signer/root
and durable-store owners only after defining authenticated readback, current
key/revocation checks, pending versus committed visibility, and restart binding.
Do not reset a burned reservation, re-sign on retry, or substitute conversation
authority. R11-B–F, owner-controlled legacy event recovery and later measured
benefit remain open. All 26 packets and six substeps remain non-dispatchable.
Commands, hashes and limits: `outcome_response_continuation_20260914`.

### Publication-commit checkpoint — 2026-09-14

Packaging passed: **15 fast groups in 2,882ms** and **8 staged-manifest tests
in 62.62s** (two pytest configuration warnings). Runtime membership stays at
1,400 with two changed source hashes and matching pins. The test registry is
current and unchanged at 1,650 files / 269 quarantined; no guard was weakened.

Base: PR1721/main `9d69a111a096aa4279eaa6f318ebb0bd63808cac`.
WSP 00 awakening/strict software gate passed. Local WSP 15 planning is
3 + 4 + 4 + 4 = **15/P1** under the existing 012 authoring instruction.
This app continuation is not a signed allocation, work order or runtime grant.

Governed lexical retrieval found the existing publisher and signing owners;
deduplicated hit arrays and direct reads supplied the omitted store and nearest
runtime-authority tests. Tier-0 contracts are present; optional memory/design
artifacts and requirements.txt are absent. Peripheral authenticity hits were
deferred until the connected verification pass. Workspace evidence matches the
base above; freshness remains UNKNOWN/gap with zero semantic-owner attempts.
The unchanged semantic authority at `5326080d` was not queried again or moved.
Deterministic source/fixture work was selected before any model dispatch.

The existing authority-store adapter now attempts at most three commits for
`revision_conflict`, retaining the same signed envelope and rebuilding each
candidate snapshot from current state. Unrelated updates survive. Other errors
do not trigger write retries. The existing publisher handles a publication error
only after signing succeeded: it reloads the durable publication and reuses its
original evidence/identity/issuance/signature validator. A matching winner can be
acknowledged without replacement, activation or another signing use. Missing,
invalid or conflicting durable evidence still rejects; signer rejection and
KeyboardInterrupt/SystemExit remain outside recovery.

**Verification:** 16 new cases extend the existing runtime-authority test file.
Before repair: **7 failed / 9 passed / 33 deselected in 4.31s**. Six failures
reproduced recoverable commit behavior; one checked the proposed three-attempt
bound. Focused result: **49 passed in 13.81s**. Connected publication, queue
binding, authenticity, adversarial, Ed25519 and admission-handler result:
**118 passed in 15.96s**. Controlled interleavings use real disposable atomic JSON
stores and injected signer/verifier doubles; each candidate signs once. Competing
fixtures produce their own publication and do not prove one global signer use.
Existing separate-interpreter publication retry tests also pass. Process death
before durable publication and production root/UID isolation remain unverified.

R11-A remains partial. The root outcome service deliberately burns reservations
and stores a signature digest, while conversation signing already has a distinct
response-replay/anchor contract. Next, map a durable outcome-response handoff onto
those existing owners before considering a new mechanism. Preserve operation,
scope, current-key/revocation and independent grant boundaries; do not reinterpret
conversation recovery as an outcome grant or reset burned reservations. Process
death or exhausted retries with no durable envelope still require owner recovery.
R11-B–F, legacy event recovery and measured retained benefit stay open.
All 26 packets and six R11 substeps remain non-dispatchable. Exact source hashes,
commands and limits are in `publication_commit_continuation_20260914`.

### Event-timestamp checkpoint — 2026-09-14

Packaging passed: **15 fast groups in 2,988ms** and **8 staged-manifest tests
in 61.83s** (two pytest configuration warnings). The runtime list stays at
1,400 files with two changed source hashes and matching pins. The test registry
is current at 1,650 files / 269 quarantined, with no registry or guard change.

Base: PR1720/main `9c949e8debf4540c504de57133e980b7eb2dcab4`.
WSP 00 awakening/strict software gate passed. Local WSP 15 planning is
3 + 4 + 4 + 4 = **15/P1** under the existing 012 authoring instruction;
this app continuation supplies no signed allocation, work order or runtime grant.

The governed source-bound lexical query returned the existing chain store/test,
with UNKNOWN freshness, an index gap and zero semantic-owner attempts. Its clean
workspace binding matches the base above. Prior semantic authority remains at
`5326080d`; no unchanged semantic failure was retried. Tier-0 documents are
complete; optional memory/design documents and requirements.txt remain absent.
Deduplicate repeated hit arrays, prioritize the chain store and exact admission
binder, and discard peripheral authority-admission/adversarial hits. Direct
symbol/caller reads recovered the missing binder and confirmed the existing
canary receipt consumer. This is local retrieval evidence, not CURRENT semantics.
Deterministic fixtures/contract checks were selected before any model work.

The existing `ResidentQueueChainResultReceipt` now carries optional
`recorded_at`. Newly accepted stage writes require a timezone-aware recording
clock and save it with the stage in the existing atomic commit. Prior receipts
and their timestamps remain unchanged as later stages advance. Historical
receipt objects omit the field when absent; the transition-ID algorithm and
chain schema version stay unchanged. The existing canonical snapshot revision
covers the timestamp. This is integrity binding, not a signed clock attestation.

The admission binder requires a canonical chain snapshot and exactly one
held-out-stage receipt with matching queue/slice and recomputable transition ID.
It reuses that receipt's time as `verified_at`, rejecting missing, malformed,
timezone-naive, future, duplicated or mismatched evidence. It does not substitute
the current bootstrap clock or snapshot-wide `updated_at`. Legacy histories
without this event time remain readable but cannot derive a new admission;
owner-controlled evidence recovery is required, not automatic timestamp backfill.

**Verification:** the new pre-repair selection had 18 failed assertions. The
first attempt also exposed an older store fixture without progressive-stage
binding; reusing the existing planner's governed fixture let the timestamp
assertions run. The old fixture remains as an explicit rejection case. An
existing spawn test now imports its callable by canonical package name so
pytest's temporary import name is not pickled into the child. A broader run
then exposed rejection-message precedence; validating timestamps only after
the existing planner accepts the stage preserved the original assertion.

The final connected chain-store, admission, planner, serial bootstrap, publication,
canary and dispatcher selection passed **214 tests / four skipped in 99.49s**.
The skipped capabilities are symlink creation and AF_UNIX availability on this
host. Tests cover unchanged old receipt bytes during stage advancement, duplicate
stage rejection, atomic store reload, canonical snapshot tampering, invalid event
bindings, spawn/CAS behavior and existing publication freshness/revocation gates.
They use disposable state and synthetic/injected authorities. No production
signer, active FoundUp, queue activation or live memory experiment ran.

R11-A remains partial. Next, inspect the existing publisher/signer/store boundary
for signing accepted before publication becomes durable, lost acknowledgments
and competing first publications. Do not add a second outbox or scheduler before
checking current recovery owners. Cross-store acceptance (R11-B), admitted startup,
memory activation, legacy event recovery and measured later benefit remain open.
All 26 planning packets and six R11 substeps remain non-dispatchable. Exact
commands, source hashes, failures and limits are in baseline section
`event_timestamp_continuation_20260914`.

### Publication-retry checkpoint — 2026-09-14

Packaging: **15 fast groups passed in 4,425ms** and **8 staged-manifest tests
passed in 66.65s** (two pytest configuration warnings). The 1,400-file runtime
membership is unchanged; only the publisher/store hashes and their two pins
changed. The existing test registry gains `process` capability on one already
quarantined runtime-authority test row; membership/quarantine stay 1,650/269.
The first fast invocations rejected a missing worktree dependency setting and
CRLF bytes in the edited package pin. Supplying the existing vetted dependency
path and restoring that file's required LF bytes resolved them; no guard changed.

Base: PR1719/main `94d58e73df016e20867f0f17b88af715a85b5110`.
WSP 00 awakening and its strict software gate passed. Local WSP 15 planning:
3 + 4 + 4 + 4 = **15/P1**; this is local authoring under 012's instruction,
not a signed allocation or permission to dispatch the planning packet.

The source-bound Holo helper rejected semantic retrieval with
`HOLOINDEX_AUTHORITY_ROOT_HEAD_MISMATCH`, UNKNOWN freshness, index gap and
zero owner attempts. Its lexical fallback bound the clean implementation
checkout and found the existing queue binding/store and tests. Deduplicate its
repeated hit arrays; put the exact publisher and runtime-authority fixture ahead
of peripheral root-runtime hits. Required README/INTERFACE and evolution/test
docs are present; optional memory/design artifacts and requirements.txt are
absent. Exact symbol/caller reads supplied the missing publisher context;
NAVIGATION confirms the existing PatternMemory owner. No query reindex or
CURRENT-semantic claim. Deterministic local debugging was selected because this
defect needs exact signed-byte, process-restart and runtime-contract evidence;
no new model call, worker admission or autonomous dispatch was inferred.

The existing signed publisher now first checks the existing authority store for
an exact publication. It reconstructs and verifies the stored signed payload
against the requested evidence and publisher identity using the original
`issued_at`. A matching retry returns the record ID without another signing use,
store write, timestamp refresh or activation. Changed evidence, principal,
provider, RedDog identity, key/epoch, invalid signature, extra signed fields and
invalid/future issuance reject. Initial publication still uses the existing
signer and attestation checks; the record is snapshotted before callbacks.

`AuthorityRuntimeVerifiedOutcomeStore.load_publication()` is a publication-owner
read of STAGED or ACTIVE evidence. It raises on invalid durable state and is not
the consumable outcome source. Existing `load_envelope()` and
`load_verified_outcome()` still hide staging; runtime authority still performs
fresh key, revocation and expiry checks. A publication acknowledgment does not
grant memory-write authority or renew an expired outcome.

**Verification:** three new cases failed before repair (staged/active child-process
retry requested another signing use; later-clock retry conflicted). The expanded
existing runtime-authority, queue-binding, authenticity, adversarial, Ed25519
signing and admission-handler selection passed **91 tests in 13.08s**. The two
restart cases launch a separate Python interpreter, reopen the same disposable
atomic JSON store and require unchanged bytes. Their signer/verifier remain
digest-based doubles. This is real local process reconstruction, not production
root/UID isolation or composed crash recovery. Rehashed invalid evidence and
changed publisher identities reject; later retries do not extend expiry or
cancel revocation. No existing test assertion was weakened.

**R11-A remains partial.** A separate read-only derivation probe confirms that
the same queue/chain inputs at NOW and NOW+1 differ only in `verified_at`.
`derive_verified_outcome_admission()` still uses the bootstrap clock; its held-out
receipt has no event timestamp, and the chain store currently keeps only a
snapshot-wide `updated_at`. Define/reuse an immutable admitted event timestamp
through those existing owners; do not simply substitute a mutable snapshot time
or alter canonical record hashing. That is the next bounded implementation.
First-signing failure before durable publication, competing initial publications,
cross-store acceptance, startup authority, sink activation and later improvement
remain separate proofs. This repair does not close R11-A, R11 or G4.

The baseline section `publication_retry_continuation_20260914` retains the exact
source/test hashes, commands, failures, queue observation and limits. All 26
packets and six R11 substeps remain non-dispatchable. Protected YUMORI/eSingularity
work, queue activation, root/signer deployment and live memory are unchanged.

### Authority-to-memory connection checkpoint — 2026-09-14

Source: merged PR1718/main `5c29a0af1eabc49ee97939e7eca800fb36d22407`.
WSP 00 awakening and its strict software gate passed. This checkpoint is a
local composition audit and R11 plan refinement; runtime code and production
configuration are unchanged. Local WSP 15 planning: 2 + 4 + 4 + 4 = **14/P1**,
not a signed allocation or runtime admission.

The canonical-main Holo bundle again returned `UNKNOWN`, index gap and zero
semantic owner attempts at workspace `0c81418f`, with peripheral simulator,
market and general bridge test hits. Its required module documents exist;
optional memory/design artifacts and requirements.txt remain absent. Deduplicate
hit arrays, discard unrelated hits, and explicitly retrieve the exact owners
and existing fixtures below at the selected source. This is degraded retrieval,
not CURRENT authority. Static caller searches and deterministic fixture runs
resolve this bounded question without a model/provider call or new subsystem.

| Existing connection | Verified source and boundary |
|---|---|
| Queue to admission and publisher | [Queue binding](../../modules/communication/moltbot_bridge/src/foundup_memex_verified_outcome_queue_binding.py) is called by [serial-loop bootstrap](../../modules/communication/moltbot_bridge/src/reddog_main_resident_queue_serial_loop_bootstrap.py). It derives admission metadata and constructs the existing signed publisher from supplied dependencies. This connection already exists. |
| Queue to PatternMemory | [Runtime binding](../../modules/communication/moltbot_bridge/src/reddog_signed_worker_openclaw_queue_loop_runtime_binding.py) constructs the existing sink with a database path. The [sink](../../modules/communication/moltbot_bridge/src/reddog_verified_pattern_memory_sink.py) remains staging-only, has no activation method, and does not receive an independent authority dependency. An environment flag cannot supply that missing contract. |
| Publisher to durable evidence | [Publisher](../../modules/communication/moltbot_bridge/src/foundup_memex_verified_outcome_publisher.py) signs and stages an envelope in the [existing authority store](../../modules/communication/moltbot_bridge/src/foundup_memex_verified_outcome_runtime_store.py). The store separates STAGED/ACTIVE evidence and durable receipt consumption. It is not a second PatternMemory implementation. |
| Signer startup and protected use | [Startup selection](../../modules/communication/moltbot_bridge/src/reddog_signer_system_service_manifest_selection_loader.py) supplies root-backed outcome signing. A separate [protected-use loader](../../modules/communication/moltbot_bridge/src/reddog_signer_system_service_root_protected_use_loader.py) and [WSP 71 ephemeral factory](../../modules/communication/moltbot_bridge/src/reddog_signer_wsp71_ephemeral_backend_factory.py) already exist; static Python search under modules/scripts finds their definitions and tests, without a production caller. Do not recreate them. |
| Evidence to Memex | [Runtime authority](../../modules/communication/moltbot_bridge/src/foundup_memex_verified_outcome_runtime_authority.py) revalidates active durable evidence and issues an opaque read/assembly capability. [Operational Memex supply](../../modules/communication/moltbot_bridge/src/reddog_operational_memex_snapshot_supplier.py) already accepts this authority and consumes capabilities through the existing assembler. That capability is not permission to mutate PatternMemory. |

**Fresh evidence:** the existing runtime-authority, protected-use-composition
and startup-selection suites passed **46 tests, with one Linux ownership check
skipped, in 26.90s**. The tests use disposable state and injected dependencies;
this is not production signer/startup admission or a multi-process deployment
proof. In particular, a fresh store handle in a replay test is not itself a
separate operating-system process.

**Composition counterexamples:** reuse the runtime-authority test's `_publish`
fixture with `activate=False`, the real signed publisher/authority-store code,
and the existing admission-handler test's failing `_CanonicalPatternMemorySink`.
The signer and verifier here are digest-based test doubles. Calling the actual
handler `_activate_published()` rejects memory admission and reports no memory
write, but the authority envelope has already become ACTIVE. The fixture runtime
authority can issue a capability while memory still has zero records and one
staged record. Retrying the same publication with a trusted clock one second
later raises `verified_outcome_evidence_conflict`: newly signed bytes differ
under the same evidence key. These observations identify latent composition
gaps; the real staging-only sink still prevents this production path.

The [baseline evidence](../roadmaps/RSI_BASELINE_OBSERVATIONS_20260913.json),
`authority_activation_continuation_20260914`, retains the exact source hashes,
fixture observation, command and limitations. Do not relax conflict checks,
replace signed evidence, reverse callbacks blindly, or switch activation on
to make a canary pass. Signer protected-use ordering covers signing/revocation;
it does not prove atomic acceptance across the authority store and PatternMemory.

**R11 implementation sequence:** these are substeps of the existing packet,
not new independently dispatchable tickets. The machine-readable plan is in
R11's `authority_activation_plan` in the existing backlog.

1. **R11-A — immutable publication and retry.** Start with the existing queue
   binding, publisher, authority store and their tests. Define and retain the
   exact admitted event/publication across restart and clock advancement. The
   derived `verified_at` field and signing `issued_at` field must not accidentally
   create a new outcome or conflicting signature on a retry. Preserve fresh
   use-time expiry/revocation checks; reject changed scope, evidence and keys.
2. **R11-B — acceptance and visibility.** Bind evidence and memory acceptance
   to one recoverable decision under the existing authority/WRE owners. A failed
   memory operation must not expose an accepted outcome to the Memex reader.
   Fix the composed counterexample with the real adapters and explicit fault
   boundaries before enabling activation; existing signer locks alone are insufficient.
3. **R11-C — admitted startup composition.** Reuse current owner selection,
   protected-use loader, grant/revocation and WSP 71 factories. Require authentic
   current owner/runtime bindings and independent verifier inputs, preserving
   their distinct operations and principals. Missing dependencies remain a
   rejection; a local fixture or installed executable is not admission evidence.
4. **R11-D — existing sink activation.** Extend the existing sink and its queue
   factory only after A–C have a verified contract. Supply independent authority
   at the write boundary, revalidate exact staged bytes/agent/scope, and use the
   existing PatternMemory transaction. Return success only after the accepted
   record and its durable decision agree. Preserve the default closed path.
5. **R11-E — recovery and ownership.** Exercise real process restart, competing
   writers, expiry/revocation, cancellation and lost acknowledgments across the
   composed stores. Require one accepted effect, preserved conflicts/failures
   and safe recovery. Reuse current tests and Linux harnesses; do not count a
   skipped ownership test or a second object as process-isolation proof.
6. **R11-F — later use and benefit.** Reuse existing Memex supply/PatternMemory
   consumers with an admitted accepted version and the fixed R15 system-workflow
   oracle. Distinguish one-use assembly receipts from durable learning. Demonstrate
   the next invocation consumes the accepted improvement, retains rejected
   variants, and improves measured outcome/cost. Storage or a successful read
   alone cannot close R11/G4 or R15.

Next authorable step is **R11-A** in an isolated source snapshot. Independent
authority/runtime supply remains a separate prerequisite for C/D and live proof.
All 26 packets remain non-dispatchable, and no completion gate advances here.

### Active-record identity checkpoint — 2026-09-14

Packaging: **15 fast groups passed in 3,104ms** and **8 staged-manifest tests
passed in 68.97s**. The 1,400-member runtime closure changes only the sink hash;
both existing compatibility pins were refreshed. Earlier fast invocations
rejected an incorrect temporary-drive setting and the not-yet-refreshed
manifest; the final qualified invocation passes. No test or guard was weakened.

Resumed from merged PR1717/main
`dae4b76aeae06d4dd25e6d8a80ef1b65b32b6c19`; the previous staging repair is
complete at that source. WSP 00 awakening and its strict software gate passed.
This is one local R11 maintenance checkpoint, not a distributed worker run.

The canonical-main Holo query returned a lexical workspace bundle at
`0c81418fe94a7786cfd55f01e138ddc5d510583d`: `UNKNOWN`, index gap, zero semantic
owner attempts. Its five code hits were peripheral and it returned no tests.
The bundle's README/INTERFACE and history paths were useful navigation only.
Deduplicate hit arrays, discard unrelated false-positive/vision/market hits,
and explicitly include the sink, its existing tests, admission producer and
handler in the owned source above. Read those exact files and module contracts;
NAVIGATION confirms PatternMemory. Optional memory/design artifacts and the
module requirements file are absent. This repairs local context assembly, not
Holo freshness; no reindex or CURRENT claim is made.

Micro finding: the active-row retry branch used Python dictionary equality,
which equates `true` with `1`, `12` with `12.0`, and `0.0` with `-0.0`.
Those JSON values have different canonical digests. All three preseeded-row
counterexamples were acknowledged despite failing subsequent record-ID
readback: **3 failed / 18 passed in 1.62s** before repair. Reuse the existing
canonical serializer for this comparison, keeping the digest algorithm and
record-ID format unchanged. The existing conflict test now covers those values;
the idempotence test also covers a valid fixture-seeded active row. Conflicting
rows retain their bytes and create no staging row. **55 sink/admission/handler
tests pass in 4.15s**; registry remains current at 1,650 / 269 quarantined.

Macro decision: preserve PatternMemory, its existing tables and the admission
contracts. Numeric normalization would change receipt identities, and a new
store would duplicate the existing boundary; neither is needed. Deterministic
SQLite fixtures are sufficient for this narrow defect, so no Qwen/Gemma or
provider call is needed. Local WSP 15 planning score: 2 + 4 + 3 + 4 = **13/P1**,
under section 4; this is not a signed allocation or runtime admission receipt.

The real sink remains `activation_ready=False`. Fixture-seeded active rows
are test inputs, not authenticated activation. No production memory, protected
FoundUp, worker binding, or service was changed. R11 still requires an
independently bound durable authority, activation/revocation ordering and
recovery, then an invocation consuming accepted memory. Resume by retrieving
the existing root-authority/startup-factory and admission contracts named in
the module INTERFACE and R02 map; do not synthesize authority to unblock them.
R15 still needs measured retained benefit. This checkpoint advances no G0–G5
gate. Machine-readable evidence is in the existing
[baseline observations](../roadmaps/RSI_BASELINE_OBSERVATIONS_20260913.json),
under `active_record_identity_continuation_20260914`.

### Staging replay checkpoint — 2026-09-14

Packaging validation: all 15 RedDog fast groups pass (3,052ms), and all eight
staged-manifest tests pass (65.51s). Runtime membership remains 1,400; only the
sink source hash and the two compatibility pins change.

Source: merged PR1716/main `0120878c7febc68b794c749a10e80c305fd0c89f`.
WSP 00 awakening and its strict software gate passed again. The local execution
plane remains preparatory maintenance; no distributed worker/model authority
is inferred from a planning score or successful local tests.

Holo retrieval found the existing sink, its tests and adjacent root/Memex
authority modules. The lexical bundle is UNKNOWN/index-gap with zero semantic
owner attempts; current source and module contracts supply the working context.
Duplicate hit arrays and the peripheral false-positive-memory hit were excluded.
Tier-0 README/INTERFACE and test histories exist; optional memory/design docs
and a module requirements file are absent. NAVIGATION confirms PatternMemory.

The micro pass reproduced a lookup/insert interleaving and shallow-copy drift.
One existing sink test file now has six additional cases: three controlled
second-connection insertions, a nested-input mutation and two commit-boundary
failures. Before: four failed / 13 passed. After: all 17 sink cases and 34
adjacent admission/handler cases pass (51 in 3.19s). The canonical registry is
current at 1,650 files / 269 quarantined; no test was newly quarantined.

The existing sink now snapshots the payload and uses SQLite's record-key
conflict handling, then checks the stored payload and agent before commit.
An identical winner yields the same ID; a different winner retains its bytes,
agent and timestamp and produces the existing conflict error. Failure before
commit leaves no staging row, and retry after a completed commit retains one
row. The tests use disposable SQLite state and explicitly injected failures.

The macro pass keeps the existing staging table, PatternMemory, admission
adapter and authority boundaries. A new memory backend or scheduler is
unnecessary. Whole-workflow locking would need the independent activation
owner; this repair covers staging-row replay only. It does not prove process
crash/power-loss recovery, sustained concurrency, atomic activation/revocation,
authenticated recall or retained benefit. The real sink remains
`activation_ready=False`; no live authority, provider or protected FoundUp ran.

WSP 15 local planning score: 2+4+4+4=14/P1. This is recorded preparation for
R11/R15/R17, not a signed allocation or packet admission. Deterministic local
counterexamples justify the small existing-code repair without a model call.
The canonical WSP 15 section 4 also corrects the prior outcome checkpoint's
score-16 label to **P0**. Its earlier P1 label is preserved in the raw dated
observation with an explicit correction in this continuation; packet scores,
dependencies and execution authority are unchanged.

### Outcome retention checkpoint — 2026-09-14

Source: `e03f68badd7664e20c7f6dd47304f69b009d16cb`. This continuation followed
the existing recorder, held-out retention gate, queue wrappers and final
memory-admission adapter as one connected block. Three existing runtime files,
four existing test files and one existing shared canary fixture were extended;
no new module or test file.

The recorder now rejects malformed/non-finite/Boolean measurements, non-integer
token counts, foreign or missing receipt lineage, contradictory acceptance
evidence and empty storage acknowledgments. Invalid inputs cannot claim memory
eligibility. Its v2 identity seed covers cost, latency, complete publication and
Holo evidence; callback success/failure does not rename the same evidence.
Copies isolate caller/store/sink objects. The JSONL store refuses non-standard
numeric JSON, and secret-marker rejections suppress affected receipt labels.

The retention gate requires an accepted, memory-eligible outcome with explicit
no-write state, the same work/slice/verifier, and the recorder's digest of the
exact verifier result. Invalid regression counts cannot become zero failures.
Its v2 identity seed binds the complete supplied evidence. The final existing
admission adapter also requires a nonempty string acknowledgment and protects
its receipt inputs from sink mutation. A recorded failure remains auditable;
it cannot qualify as a successful learning outcome.

Validation: 171 recorder/gate tests, 39 queue integration tests, 34 upstream
verifier/publication tests and 34 memory-admission/handler tests pass (278
distinct selected cases). The composed fixture exercises the real recorder,
queue retention wrapper/gate and admission adapter with synthetic receipts and
an injected sink. Valid evidence reaches that sink; invalid cost, a failed
outcome and changed verifier evidence do not. The dated JSON continuation
retains the initial failures and the fixture/API corrections separately.

Downstream review also ran the existing real-sink and canary-integration tests
in disposable repositories/databases. An older shared canary fixture omitted
the newly required ratchet outcome/no-write state and verifier digest: 26
failures/11 passes became 37 passes after that fixture matched the producer
contract. Total distinct selected tests: 315. The existing sink already stages
identical records idempotently and keeps them out of normal recall. Its
`activation_ready` is deliberately false and direct activation is rejected
until an independent durable authority source is wired. Reuse this staging
implementation for R11; the canary tests assert blocked proof, not live success.

The initial PR CI stopped at registry freshness: a new test decorator called a
local digest helper at import time, triggering the existing quarantine rule.
Replacing that pure test parameter with its literal digest preserves coverage;
the registry is current at 1,650 files/269 quarantined with no registry or
classification-rule change. No new test was excluded to make CI pass.

Packaging checks pass: all 15 RedDog fast groups (3,137ms) and all eight staged
manifest tests (65.74s). Runtime membership stays at 1,400 files; the three
runtime sources and already-included shared test fixture account for all four
changed hashes. The compatibility digest and both pins agree. The later test
parameter and canary-fixture corrections are outside that runtime manifest.

These are deterministic local contract checks. They do not authenticate the
synthetic authorities, execute a model, admit a live worker, write production
PatternMemory or demonstrate retained improvement. Stored ratchet records are
pre-callback snapshots; final callback status is returned separately. IDs are
not replay locks, and a callback may write before failing. Atomic retention,
exactly-once effects, crash recovery, concurrent ownership and a subsequent
invocation consuming authenticated memory remain R11/R17/R15 work. Historical
v1 receipts are retained as history, not rewritten with v2 identifiers.

Retrieval: the local Holo bundle found the existing ratchet, architecture and
PatternMemory surfaces, then both target tests. Freshness remained UNKNOWN with
an index gap and zero semantic-owner attempts. A neighboring conversation-scope
hit and duplicate arrays were excluded; current module contracts and test
histories supplied the missing execution context. Optional memory/design docs
were absent. The queue/persistence owners already exist; no replacement was
introduced. Local WSP 15 selection: 3+5+4+4=16/P0 (the earlier P1 label was incorrect). Signed runtime-owner
clarification remains pending, and no unchanged service probe was repeated.

### Stop-rule handoff checkpoint — 2026-09-14

Source: `3fc74285cb19b681de5219b8288e5307a0ea533a`, after PR1714 merged with
all ten checks successful and its accepted tree equal to main. The existing
compact compiler retained explicit `F` stop conditions while omitting them
from decompiled instructions; the existing gate still reported success.

The compiler now emits `Abort if any condition holds: <condition list>.`
The gate compares that instruction with the original declared stop list, as
well as comparing compiled and parsed fields. The existing tests reject
removed instructions, an `Abort` changed to `Continue`, and a replacement
list; they also cover legacy actionless packets. Before: five failures /
157 passes. After: 162 passes in 0.48s, with two configuration warnings from
disabled automatic pytest plugins. No model call was needed.

This is local field-preservation evidence for R10/R15. Commas/brackets that
the existing compact parser cannot preserve still fail closed. Arbitrary
prose, objective and authenticated context delivery remain open. Keep the
original prompt and governed work contract; this change supplies no worker
admission, independent verification, promotion or retained-benefit evidence.
The dated continuation in `RSI_BASELINE_OBSERVATIONS_20260913.json` preserves
earlier observations. All 26 planning packets remain non-dispatchable.

Retrieval evaluation: the governed local bundle located the existing compiler
gate and then its test file, with UNKNOWN freshness, an index gap and zero
semantic-owner attempts. Duplicate hit arrays were discarded; NAVIGATION
confirmed the compiler. README/interface and both existing M2M tests were
read first. Missing test history is now filled with an inventory of the
seven existing test files; no test module, compiler or scheduler was created.
Local WSP 15 selection: 2+4+4+4=14/P1, deterministic local execution, focused
tests followed by packaged dependency checks. The signed runtime-owner
clarification remains pending; no unchanged runtime probe was repeated.

## First bounded dispatch

### Research lifecycle checkpoint — 2026-09-14

At main `595d9007125a7bc261efcfb8d2ed67b55e7d0bba`, four new existing-suite
cases exposed local lifecycle gaps in `WREAutoResearcher`: a diff failure or
keyboard cancellation left the candidate in its scratch file; a runner failure
prevented local restore; and an invalid baseline still reached proposal
generation. The existing producer now guarantees a final restore attempt on
Python exits and rejects baseline validation errors before proposing. Local
restore is attempted even when the injected runner fails; errors propagate.
A further broken-output case exposed a status message preceding cleanup;
restoration now runs first. The expanded selection passes 31 tests. Models are disabled before fixture
initialization, with disposable files and isolated database paths.

This advances a local R10/R13/R15 dependency. It does not prove durable recovery
after process termination or storage failure, independent verification,
activation or retained benefit. The existing [dated baseline evidence](../roadmaps/RSI_BASELINE_OBSERVATIONS_20260913.json)
contains an explicitly dated `research_lifecycle_continuation_20260914` entry;
its earlier observations remain unchanged.

The verified runtime environment names `REDDOG_RESIDENT_MODEL_RUNTIME_BINDING_ROOT`
and `REDDOG_ARTIFACT_GENERATOR_MODE` remain unset in this shell. That preserves
the R06/R07 admission dependency, not a machine-wide availability verdict.
The local Holo bundle initially returned unrelated dry-run examples; narrowing
to `wre_auto_researcher` located the existing producer and tests. Both bundles
retained UNKNOWN freshness and zero semantic-owner attempts. Current module
contracts/history/test docs were available; no new module or reindex was needed.

### Worker readiness checkpoint — 2026-09-13

Source inspected: `bcc877829653997d7df638b7069258a061d04ee1`.
The local Windows CLI reports OpenClaw `2026.5.2`; the existing canonical
WSL command transport reports OpenClaw `2026.7.1-2`, and the WSL advisory finds
Hermes `0.20.4`. Windows PATH has no Hermes command. These are different
execution surfaces, so Windows PATH alone cannot establish worker absence.
The existing WSL advisory's numeric-release parsing defect is corrected in
this revision; version-only availability remains non-authoritative.

Earlier [upstream live proofs](../audits/openclaw_hermes/REDDOG_UPSTREAM_WORKER_LIVE_PROOF_20260821.md)
already exercised confined Hermes/OpenClaw GotJunk audit canaries. Preserve
that groundwork: those diagnostic invocations ran beneath model-capability
admission, so they do not supply a current signed work order, materializer or
independent verifier. The current missing API/bindings do not justify rebuilding
the existing adapters.

| Existing step | Current evidence and required connection |
|---|---|
| Architect model query | `MODEL_RUNTIME_BINDING_UNCONFIGURED`, `configured=false`, `accepted=false` in this shell. The [query](../../modules/communication/moltbot_bridge/src/reddog_model_runtime_binding_query.py) validates `reddog_backend_architect` only; READY here is insufficient for artifact execution. |
| Artifact model/provider binding | [Generation runtime](../../modules/communication/moltbot_bridge/src/reddog_bounded_artifact_generation_runtime.py) requires a separately verified `reddog_artifact_generation` surface and matching one-use authority. [Existing provider bootstrap](../../modules/communication/moltbot_bridge/src/reddog_artifact_generation_provider_bootstrap.py) composes OpenClaw/Hermes/Fusion; it does not invent available providers. No resident runtime root or artifact-generator mode is configured in this shell. |
| Hermes service | Existing transport's unauthenticated `GET /v1/capabilities` on loopback returned status `0` (no usable HTTP response). Installed CLI `0.20.4` is not proof of the required running API. Qualify the existing API service/profile/auth/tool-surface/lifecycle contract before a leaf; do not replace it with the legacy executor. |
| Work-order intake | [Existing invocation](../../modules/communication/moltbot_bridge/src/reddog_work_order_runtime_invocation.py) is explicitly `invoke_reddog_work_order_dryrun`: policy evaluation and receipt emission, with no execution. Its acceptance must not be reported as worker execution. |
| Durable publication | [Existing publisher](../../modules/communication/moltbot_bridge/src/reddog_openclaw_hermes_0102_worker_dispatch_runtime.py) authenticates, stages, commits publication and activates AgentDB tasks; it does not execute the worker. Use the existing claim/runner path afterward. |
| Independent effect evidence | Artifact generation returns checked content; its module does not write the worktree. Bind subsequent materialization, verifier and final result separately. Do not call provider text, queue acceptance or a dry-run receipt a completed artifact. |

Local validation: 148 existing job/admission/artifact/Hermes/model-query tests
passed with synthetic authorities/transports and isolated database/temp state.
The first attempt had 20 temporary-directory setup errors; the corrected full
run passed. The WSL parser repair first reproduced two failing release-suffix
cases, then passed 68 focused WSL/Gateway tests and a real version-only probe.
No live model call or worker artifact is claimed by those tests. Required module
documents were available; lexical Holo retrieval had historical/noisy peripheral
hits and UNKNOWN/index-gap evidence. Direct exact-source reads supplied missing
runtime/test context; no semantic CURRENT claim follows from that retrieval.

Holo's existing exact-main controller subsequently completed at the named
`bcc87782` source, and a fresh owner query returned CURRENT/no-gap with matching
workspace/authority HEADs. See the [maintenance checkpoint](../../holo_index/CLI_REFERENCE.md#exact-main-maintenance-checkpoint--2026-09-13).
The receipt does not apply automatically to later main commits or this edited
worktree, and exact runtime closure remains false.

Next executable proof still requires current Holo evidence, distinct verified
architect/artifact bindings, an admitted provider profile, exact signed work
scope/budget/expiry, one durable claim, bounded artifact materialization and a
separate verifier. Reuse the existing owners above; preserve `dispatchable=false`
until their real admission succeeds. Holo maintenance has its own owner and
does not supply these model or worker authorities.

### Dispatch through the existing owners

Use R06/R07/R08 to prove one documentation artifact before authorizing broader implementation:

1. Verify merged R01 integrity in the selected source and obtain current clean worktree claims. Apply the system-first / selected-early-stage validation scope above; preserve all active project/service lanes and the separate WSP state-semantics work.
2. Ask the existing runtime's binding query for its selected architect model/provider. `MODEL_RUNTIME_BINDING_READY` validates that architect surface only. Separately admit the `reddog_artifact_generation` binding and provider through the existing generation bootstrap before worker execution. Reuse the signed-evidence supply and authenticated operations bootstrap. Never populate trusted keys, acceptance flags or receipts from this planning document.
3. Compile one packet using the existing [work-order intake](../../modules/communication/moltbot_bridge/src/reddog_work_order_runtime_invocation.py), [signed worker dispatch](../../modules/communication/moltbot_bridge/src/reddog_openclaw_hermes_0102_worker_dispatch_runtime.py) and model binding. Bind one base SHA, permitted source reads, output artifact, expiry, budgets, tool profile, owner and separate verifier.
4. Candidate task: read the canonical roadmap entry and R06–R09, then return a short dependency/acceptance checklist as a bounded artifact. No repository write, Git operation, service activation, nested delegation or deployment is needed for this first canary. Finalize the exact artifact name and byte limit in the admitted contract.
5. Dispatch through the existing operations/queue adapter. Do not run an unconstrained `openclaw agent` prompt against the shared checkout, start OpenClaw inside OpenClaw, or revive the legacy blocked Hermes executor.
6. Verify actual child/provider/model attribution, returned bytes, no forbidden effects, lifecycle completion, timeout/cancellation behavior and cost receipt. A dry-run or a persuasive response is not the acceptance signal. Reconcile rejection once; stop when the budget or authority is exhausted.
7. Only after this canary passes should a writing packet receive an isolated candidate worktree. Let the independently bound verifier decide acceptance. Existing delegated policy should avoid repeat approval requests within the same scope.

The missing dispatch evidence belongs in R06/R07, not a new orchestration subsystem. Until the binding and scope are admitted, keep `dispatchable=false` in the planning backlog. An unconfigured local shell is not a reason to weaken production gates.

## Economical model and effort policy

**012 working-session preference, revised 2026-09-14:** use short, bounded
checkpoints following the reported Codex connection interruption. This
supersedes the earlier preference for several layers per session. Complete
one evidenced change, its consumer checks and documentation; save the exact
source, results, outstanding gates and next action before continuing. Recover
from that checkpoint after an interruption and verify Git/PR state before
repeating work. Continue the RSI journey across checkpoints. Keep concise
progress updates, and never enlarge scope, retry unchanged failures, or bypass
authority merely to extend a run. Short checkpoints reduce recovery work;
they are not a demonstrated fix for the unconfirmed connection failure.

These are proposed operating defaults to benchmark, not runtime settings changed by this document. An admitted provider/model contract takes precedence.

| Work | Starting tier | Escalation condition |
|---|---|---|
| File inventory, links, hashes, schema checks, test execution | Deterministic tools; no model call | Only ambiguous interpretation needs a model. |
| Routing proposals and small classification tasks | Existing local model with bounded context; Nemotron remains evaluation-only | No eligible model, invalid proposal or measured quality failure. Never download/evict another lane's model as a fallback. |
| Routine docs and narrowly specified implementation | Eligible economical coding model, medium effort | One bounded repair attempt fails the fixed acceptance test, or contract ambiguity is found. |
| Cross-module design, unexplained failures, novel interfaces | Strong architect model, high effort | Competing constraints cannot be resolved with the evidence available. |
| Authority, promotion, rollback and final difficult review | Strong independent reviewer, high; extra high only for unresolved hard cases | Escalate by risk/evidence, not by default for every packet. |

For Codex work, Terra is a candidate for balanced work and Luna for small repeatable tasks; Astra is the strong architect/reviewer candidate. Evaluate against actual acceptance results and available bindings. Model names are candidates, not assumed OpenRouter availability. [Official model guidance](https://developers.openai.com/api/docs/models), [Astra effort support](https://developers.openai.com/api/docs/models/gpt-6-astra).

One important local exception: the current AI Gateway `openrouter` / `moonshotai/kimi-k3` request contract forces reasoning `max` and at least 4,096 completion tokens. A “medium effort” label in a prompt cannot override it. Select a different admitted route for small jobs or change that contract in a separately validated slice. [Exact gateway interface](../../modules/ai_intelligence/ai_gateway/INTERFACE.md#public-api).

Practical cost controls:

- Send one small packet and its necessary Holo/module context, with stable evidence references. Reuse retrieved evidence while its source and generation remain valid; refresh after relevant changes. Avoid repeating the full audit in each worker.
- Use one author per slice by default. Reserve separate verification capacity. Add a panel or team only where its measured improvement justifies its full aggregate price and the exact admitted policy permits it. Start flat; cap children, aggregate calls and retries. Keep failed lanes visible and preserve independent audit outside the author team.
- Before dispatch bind numeric maxima for input/context, generated output, model calls, retries, wall time and aggregate spend. Reserve verifier cost before spending the author budget. Values come from existing delegated policy and fresh provider evidence; none are invented here.
- Record actual input, cached input, output/reasoning charges where exposed, per-call cost, retries and verifier cost. Unknown usage stays unknown. Measure **cost per independently accepted slice**, not cheapest token or largest number of agents.
- A bounded failure returns a small blocker/evidence packet to the architect. Do not turn low-cost workers into an unbounded retry loop.
- Use caching and supported asynchronous batch pricing only after the specific API/adapter contract is verified. Codex subscription usage and OpenRouter/API billing are different meters; do not present public API prices as this task's account charge.

Recommended operating rhythm: one architect pass to define acceptance, one economical worker, deterministic validation, one independent review, then compact results back into the roadmap and module memory. Extra high is justified for the hard authority decisions in this audit; it is excessive as the permanent default for routine roadmap execution.
