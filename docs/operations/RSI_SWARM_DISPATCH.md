# RSI hybrid production line: ticket dispatch and cost control

Parent authority: [system roadmap](../../ROADMAP.md). Status: operating plan; runtime observations are dated 2026-09-10 JST. The hybrid planning refinement is dated 2026-09-11; earlier runtime observations retain their date. This document configures no runtime, authorizes no new effect, and does not make the backlog executable.

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
| PQN FoundUp / Science Swarm Hub | The [monorepo entry](../../modules/foundups/pqn_swarm_hub/README.md) is a compatibility stub. The actual [external implementation](https://github.com/FOUNDUPS/science-swarm-hub/tree/bdf0e15f019f83d76fa9cf94b131716bde559350) has work registry, submissions, verification, contribution records, participant gates and optional SQLite storage. | Use a pinned external checkout and existing injected detector/store seams. Do not rebuild these services under the monorepo stub. Connect task/result evidence to existing FAM/WRE owners; R20/R23/R24. External runtime tests remain unexecuted in this review. |
| GotJunk — separately identified candidate | [Existing module](../../modules/foundups/gotjunk/README.md) and [HXA12 dry-run proof](../../modules/infrastructure/wre_core/tests/test_hxa12_gotjunk_second_proof_dryrun.py) already exist. [WREAdapter.execute_skill](../../modules/foundups/gotjunk/adapters/wre_adapter.py) raises `NotImplementedError`; the factory proof explicitly reports no real execution. | Qualify an isolated real-code/fixture task through the existing generic job path before claiming live integration. Reuse the dry-run proof as groundwork, not RSI acceptance; R08/R20/R23. The spoken name “GetK” has not been confirmed as GotJunk; resolve it before assigning a named ticket. |
| Auto-post | Existing social orchestrator, formatting/routing and duplicate prevention are listed above. | Qualify preparation/deduplication with a recording sink first; live posting is a separate effect. Reuse this workload for cross-task retained-benefit checks; R15/R23. |
| FAM, qualified teams and reward accounting | [R24](../roadmaps/R24_AGENT_PRODUCTION_LINE_PACKET.md) already binds worker qualification, tickets, independent audit, acceptance and reward policy to existing owners. | Science Hub contribution records are not confirmed FAM/financial settlement. Keep optional teams and reward effects behind their existing proof gates; R20/R21/R24. |
| 012/RedDog feedback and 3V | [R25](../roadmaps/R25_REDDOG_FEEDBACK_LOOP_PACKET.md) already covers same-FoundUp active engagement, consent, scoped proposals and typed feedback. | Reuse it for selected early-stage cohorts when admitted. V1 opinions do not self-certify V2 correctness, V3 valuation or promotion; initial tests remain synthetic. |

### Apply the existing Auto Researcher without broadening its claims

`dry_run=True` does not mean “no side effects”: its constructor creates a results
directory/copy/TSV and attempts to obtain the Qwen engine. Its present mutable
target is literal allocation/multiplier configuration for a sustainability
simulator. It is not an already-connected generic code editor or a proven
registry-workflow optimizer. Qualify paths/model loading and evaluate the
existing contract before any experiment. If a registry procedure requires a
different target shape, extend the appropriate existing owner only after the
interface mismatch is demonstrated; do not make the ROC metric its judge.

Likewise, model AutoResearch is an existing model-selection/evaluation lane.
Connect its evidence through the admitted model/runtime binding and the same
ticket lifecycle. Do not merge the two Auto Research systems into a new engine
or equate their feedback stores with automatic PatternMemory promotion.

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
were not verified. No package, remote code or FoundUp experiment was executed.

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

## First bounded dispatch

Use R06/R07/R08 to prove one documentation artifact before authorizing broader implementation:

1. Verify merged R01 integrity in the selected source and obtain current clean worktree claims. Apply the system-first / selected-early-stage validation scope above; preserve all active project/service lanes and the separate WSP state-semantics work.
2. Ask the existing runtime's binding query for its selected model/provider. The acceptance signal is `MODEL_RUNTIME_BINDING_READY`, with current verified evidence and the correct surface. Reuse the signed-evidence supply and authenticated operations bootstrap. Never populate trusted keys, acceptance flags or receipts from this planning document.
3. Compile one packet using the existing [work-order intake](../../modules/communication/moltbot_bridge/src/reddog_work_order_runtime_invocation.py), [signed worker dispatch](../../modules/communication/moltbot_bridge/src/reddog_openclaw_hermes_0102_worker_dispatch_runtime.py) and model binding. Bind one base SHA, permitted source reads, output artifact, expiry, budgets, tool profile, owner and separate verifier.
4. Candidate task: read the canonical roadmap entry and R06–R09, then return a short dependency/acceptance checklist as a bounded artifact. No repository write, Git operation, service activation, nested delegation or deployment is needed for this first canary. Finalize the exact artifact name and byte limit in the admitted contract.
5. Dispatch through the existing operations/queue adapter. Do not run an unconstrained `openclaw agent` prompt against the shared checkout, start OpenClaw inside OpenClaw, or revive the legacy blocked Hermes executor.
6. Verify actual child/provider/model attribution, returned bytes, no forbidden effects, lifecycle completion, timeout/cancellation behavior and cost receipt. A dry-run or a persuasive response is not the acceptance signal. Reconcile rejection once; stop when the budget or authority is exhausted.
7. Only after this canary passes should a writing packet receive an isolated candidate worktree. Let the independently bound verifier decide acceptance. Existing delegated policy should avoid repeat approval requests within the same scope.

The missing dispatch evidence belongs in R06/R07, not a new orchestration subsystem. Until the binding and scope are admitted, keep `dispatchable=false` in the planning backlog. An unconfigured local shell is not a reason to weaken production gates.

## Economical model and effort policy

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
