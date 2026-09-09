# RSI production line: ticket dispatch and cost control

Parent authority: [system roadmap](../../ROADMAP.md). Status: operating plan; runtime observations are dated 2026-09-10 JST. This document configures no runtime, authorizes no new effect, and does not make the backlog executable.

## Production-line operating model

Use **agent production line** for qualification → ticket assignment → bounded execution → independent audit → accepted contribution → authorized reward settlement. “Swarm” may describe the available pool, not the rules for accepting or rewarding work. The existing filename is retained for link compatibility.

[Implement this through packet R24](../roadmaps/R24_AGENT_PRODUCTION_LINE_PACKET.md). It names the existing FAM/WRE/AgentDB owners, qualification requirements, reward conditions and acceptance tests. The pool can work concurrently within station and reviewer capacity; a single job need not launch a panel or sub-swarm. Each ticket fixes its acceptance criteria, scope, price/reward policy, budget and independent reviewer before assignment.

FAM currently exposes `open → claimed → submitted → verified → paid`; the persistent pipeline sets the task `paid` while its payout is only `initiated`. Treat actual reward delivery as unproven until the settlement owner returns confirmation. Qualification, review and settlement are distinct gates. Reviewers should be rewarded for correct assessment, including justified rejection.

## Which component does what

| Component | Role and present boundary |
|---|---|
| 012 | Principal: objectives, bounded standing authority, budget and correction. |
| 0102 | FoundUps governed destination/state terminology, separate from the replaceable model, task role and product interface. State-semantics correction remains owned by [PR #1636](https://github.com/FOUNDUPS/Foundups-Agent/pull/1636); this roadmap does not implement or claim that unmerged repair. |
| Codex / Astra or another model | The intelligence performing an architect, worker or verifier role. This Codex task is not automatically attached to a FoundUps provider route. Its app setting and a worker's model binding are separate. |
| RedDog | Principal-facing Digital Twin surface that captures intent and can submit an admitted proposal through the existing operations path. A conversation is not itself a work receipt. |
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

## First bounded dispatch

Use R06/R07/R08 to prove one documentation artifact before authorizing broader implementation:

1. Reconcile the RedDog operations skill integrity finding (R01) with its current owner. Obtain the intended exact source and current clean worktree claims. Keep YUMORI/eSingularity and the WSP state-semantics lane reserved.
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
- Use one author per slice by default. Reserve separate verification capacity. Add a panel only where its measured improvement justifies its full aggregate price and policy permits it.
- Before dispatch bind numeric maxima for input/context, generated output, model calls, retries, wall time and aggregate spend. Reserve verifier cost before spending the author budget. Values come from existing delegated policy and fresh provider evidence; none are invented here.
- Record actual input, cached input, output/reasoning charges where exposed, per-call cost, retries and verifier cost. Unknown usage stays unknown. Measure **cost per independently accepted slice**, not cheapest token or largest number of agents.
- A bounded failure returns a small blocker/evidence packet to the architect. Do not turn low-cost workers into an unbounded retry loop.
- Use caching and supported asynchronous batch pricing only after the specific API/adapter contract is verified. Codex subscription usage and OpenRouter/API billing are different meters; do not present public API prices as this task's account charge.

Recommended operating rhythm: one architect pass to define acceptance, one economical worker, deterministic validation, one independent review, then compact results back into the roadmap and module memory. Extra high is justified for the hard authority decisions in this audit; it is excessive as the permanent default for routine roadmap execution.
