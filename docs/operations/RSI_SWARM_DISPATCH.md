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

012's 2026-09-13 correction separates system improvement from active FoundUp development. Use internal workflows with synthetic inputs and disposable state. Exclude all active FoundUps, including YUMORI.me/eSingularity, from RSI experiments and their datasets. No posting, campaign change, account access, live research-session mutation or project deployment is authorized by this candidate assessment.

| Candidate | Existing implementation to reuse | First isolated experiment | Fixed independent checks |
|---|---|---|---|
| Test-registry-audit procedure — first R15 target | [Existing Skillz workflow](../../modules/infrastructure/wre_core/skillz/auto_test_registry_audit/SKILLz.md) and registry generator | Reduce repeated context assembly or redundant steps in a disposable source snapshot. | Registry meaning, required test selection, quarantine rules and held-out correctness stay unchanged; measure actual cost/latency and rollback a bad candidate. |
| Auto-post workflow — candidate for a later repeat | [Social Media Orchestrator](../../modules/platform_integration/social_media_orchestrator/README.md), its [interface](../../modules/platform_integration/social_media_orchestrator/INTERFACE.md), and [duplicate prevention](../../modules/platform_integration/social_media_orchestrator/src/core/duplicate_prevention_manager.py) | Replay synthetic post requests through isolated formatting/routing/deduplication work, with an injected no-network recording sink. | Correct destination/content, no duplicate dispatch, retry/idempotency behavior, zero external effects, and cost/latency against unchanged fixtures. Do not count a mocked sink as proof of real posting. |
| PQN researcher — candidate for a later repeat | [PQN research orchestrator](../../modules/ai_intelligence/pqn_alignment/src/pqn_research_dae_orchestrator.py), [detector API](../../modules/ai_intelligence/pqn_alignment/src/detector/api.py), and [research interface](../../modules/ai_intelligence/pqn_alignment/INTERFACE.md) | Improve research-task preparation, experiment scheduling or artifact assembly using fixed synthetic sequences/seeds and scratch output. | Reproducibility, schema/invariant checks, evidence traceability, held-out task quality and cost/latency. Keep detector thresholds, hypotheses and judging criteria fixed; a stronger apparent PQN signal is not proof of RSI or a scientific claim. |

These are planning candidates, not a declaration that their isolation or end-to-end RSI loop already works. The inspected source is `2b56415aebf551b54caf4b4fe3cfa53f27d5856b`. Only documentation/source reads were performed for this assessment; neither auto-post nor PQN experiments/tests were launched.

Before admitting a candidate:

1. Inventory current imports, constructors, output paths, provider calls and background hooks. Reuse existing seams; extend the existing owner only if a missing isolation seam is demonstrated.
2. Bind explicit temporary database/JSON/output paths, synthetic fixtures, fixed seeds where applicable, and a network-denied test runtime. Exclude live credentials, browser profiles, schedulers, callbacks and production memories.
3. Check each selected test for side effects. The auto-post [test guide](../../modules/platform_integration/social_media_orchestrator/tests/README.md) includes live browser/engagement tests; its whole-directory command is not an RSI-safe selection. The duplicate manager defaults to module memory paths and Qwen enabled; explicit db/json arguments alone do not prove all side effects are isolated.
4. The PQN detector API already accepts `out_dir` and `seed`; its default writes under the shared detection logs. Use an explicit scratch directory and inspect the downstream runner before execution. The [PQN test guide](../../modules/ai_intelligence/pqn_alignment/tests/README.md) supplies synthetic/invariant candidates, not permission to run provider or active research sessions.
5. Apply R06–R15's admitted worker, independent evaluator, promotion, activation and rollback requirements to the **isolated candidate**. Retain verified improvement only in its test memory until separately admitted. Report mocks, unavailable providers, skips and real effects separately.

R20/R22 are later synthetic lifecycle/consumer demonstrations. R24/R25 first use synthetic qualification and participant fixtures; their future live product vision does not authorize an experiment against an active FoundUp. Product adoption is a separate decision after a system improvement is proven.

## First bounded dispatch

Use R06/R07/R08 to prove one documentation artifact before authorizing broader implementation:

1. Verify merged R01 integrity in the selected source and obtain current clean worktree claims. Apply the internal-only validation scope above; preserve all active project/service lanes and the separate WSP state-semantics work.
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
