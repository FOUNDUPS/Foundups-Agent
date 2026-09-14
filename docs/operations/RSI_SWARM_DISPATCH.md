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
| PQN FoundUp / Science Swarm Hub | The [monorepo entry](../../modules/foundups/pqn_swarm_hub/README.md) is a compatibility stub. The actual [external implementation](https://github.com/FOUNDUPS/science-swarm-hub/tree/bdf0e15f019f83d76fa9cf94b131716bde559350) has work registry, submissions, verification, contribution records, participant gates and optional SQLite storage. | Use a pinned external checkout and existing injected detector/store seams. Do not rebuild these services under the monorepo stub. Connect task/result evidence to existing FAM/WRE owners; R20/R23/R24. The later baseline below passes 36 selected standalone tests; live detector, FAM, publication and RSI integration remain unverified. |
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

**Selected remaining design — specified, not runtime implemented:** extend the
existing root outcome owner for commitment/readback and reuse the current atomic
JSON store for bounded response bytes. Do not repurpose conversation or control
receipt authority, and do not add a generic outbox. Keep the following layers
ordered within R11-A; none is an executable work order.

| Layer | Existing owner and required contract | Acceptance boundary |
|---|---|---|
| Immutable response record — local prerequisite implemented above | `foundup_memex_verified_outcome_signing.py`: bind the exact canonical SigningRequest/SigningResponse, complete outcome-grant context, root reservation, original issuance, key/epoch and full response digest. Reuse the shared response validator. | Exact bounded schema; reject unknown/coerced fields, changed response/audit/signing input, foreign scope and digest substitution. No credentials, private keys, caller-selected paths or executable capabilities in serialized data. |
| Durable pending bytes | `RootVerifiedOutcomeAuthorityState` with `AtomicJsonAuthorityRuntimeStore` and existing confined operation locks. Bind storage locations and durability to current root-owner configuration before writes. | Persist validated immutable bytes before terminal response commitment; pending bytes are unreadable to publication/learning. Preserve conflicting winners. Missing replicas or rollback cannot silently create authority. |
| Terminal commitment | Existing root service/client/protocol. A versioned contract must bind the full response digest, not only the signature digest. | Keep current v1 reserve/commit semantics intact. Unknown recovery fields/operations still reject on v1. Commit only exact pending bytes; lost acknowledgments cannot replace the response or reopen a grant. |
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
