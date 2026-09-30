## Basic RSI layer and correspondence freshness — 2026-09-29

**Current qualification: 2026-09-30, source `8e04a39f4`.** The existing local
worker returned one proposal under a separately reviewed 180-second deadline.
It repeated the prompt's warnings instead of producing a function. The original
AST parser rejected it before execution. Basic autonomous RSI is still incomplete.

| Current qualification | Observed result |
|---|---|
| Dispatches / returned proposals / timeouts | 2 / 1 / 1 |
| Automatic retries / deliberate budget follow-ups | 0 / 1 |
| First packet, 90s nominal deadline | Timeout; parent wall 91.515s |
| First prompt evaluation / sample-return progress | 15.734s / at least 256 method returns |
| Separate 180s packet | Returned; parent wall 119.797s |
| Second prompt evaluation / generation | 13.188s / 113.359s |
| Completed eval / sample method returns | 512 / 512; not usage-token counts |
| Syntax-valid / accepted proposals | 0/1 /0/1 returned proposal |
| Candidate execution / later reuse | Not reached |

The first trace demonstrated progressing generation. Its64→256 sample-return
interval justified a separately frozen 180-second qualification; it did not prove
output-token throughput or guarantee completion. The follow-up retained the
same model, prompt, settings, 512 output cap and 48-case criteria. Its child
reported complete close and no method/cleanup journal error; parent binding
checks passed. No additional generation is admitted by this completed sprint.

Independent review accepts the diagnostic evidence and rejects the proposal.
Usage tokens, finish reason, held-out gain and retained gain remain unknown.
These observations do not explain earlier uninstrumented timeouts. Eight local
pass-through checks passed; the rejected text was parsed only, never executed.
Historical controls remain40 passed/8 failed versus 48 passed on 48 unchanged
development cases. They were not rerun and are not new improvement evidence.

**Next eligible layer: qualify existing prompt/chat formatting (13/P1;
C2/I4/D4/Impact3).** Inspect the raw-completion call in the current Qwen engine
and existing `local_llm_backends.create_chat_completion` support against the
selected model contract. A formatting mismatch is a hypothesis to verify, not a
proven cause. Reuse before extending; preserve effect-evidence quarantine and
the original code criteria. Do not add another backend, enlarge the budget again
or relax the parser to accept prose. No production source/runtime changed here.

The minimum path to basic RSI remains:

1. Produce one correctly scoped worker proposal and independently review it.
2. Pass unchanged repair controls; exercise rejection/rollback.
3. Reuse the verified artifact later and measure independent held-out benefit.
4. Run one admitted, isolated AmIBot ticket; then increase workers from 1 to 2.

This is direct supervised qualification, not native WRE/OpenClaw/Hermes
admission. Installed llama-cpp 0.3.20 still differs from declared 0.2.72. Process
guards are not OS memory/network isolation. Broader Gmail/LinkedIn quality
remains separate; prior rejected 1/12 general and 0/12 coder results are unchanged.
Active eSingularity/YUMORI and separately owned AutoPost remain protected.

Exact evidence/queue: `docs/roadmaps/rsi_swarm_backlog.json` →
`current_observation.native_phase_20260930`. All prior observations remain intact.
PR #1975 is merged/main-verified at `8e04a39f4` (CI 36680667946 and CodeQL 36680668121
passed; owned lane closed). This sprint has separate publication/cleanup receipts.

## Staged general-role decision cohort — 2026-09-29

At source `5b830f1ca6041a2cd9334b88a5b4d4fb1e084e3f`, the existing general-role Qwen3.5-4B
backend completed **eleven new bounded calls**. Compatible frozen G01 evidence
from PR1967 is reused explicitly: **one inherited + eleven new development cases**.
Independent review found **1/12 staged cases met every original criterion**. The candidate is rejected for promotion.

| Measure | Observed |
|---|---|
| New planned / attempted / returned / not run | 11 / 11 / 11 / 0 |
| Staged JSON/shape-valid | 12 / 12 |
| Full response-contract valid | 1 / 12 |
| Full original criteria passed | 1 / 12 |
| Unsupported completion claims | 2 |
| Unnecessary / missed required principal attention | 4 / 0 |
| New input / output tokens | 11889 / 1763 |
| New bounded-child / cohort wall seconds | 781.392 / 945.562 |
| Provider requests / retries | 0 / 0 |
| Held-out / retained gain | unknown / unknown |

JSON shape is not full response-contract validity or decision correctness.
Wrong ask IDs, unsupported transaction claims, premature terminal outcomes and
unnecessary escalation remain failed cases. The independent review records exact
violations and denominators. G01 retains its original wording caveat; the eleven
new outputs and all original criteria remain unchanged. This is descriptive
development evidence, not an externally standardized RSI score, held-out
improvement, or twelve newly preregistered calls. The prior coder baseline remains
0/12; a zero baseline does not support a finite relative-gain percentage.

**Next layer: Qualify grounded ask and evidence-transition rejection at the existing correspondence/WRE proposal boundary; extend only a demonstrated gap (14/P1).** Trace the existing consumer first, replay these
failures as negatives, and include legitimate-update controls. Reuse before
extending. A validator must reject unsupported proposals, not rewrite them into
success or hardcode fixture IDs. The evaluation envelope stays an evaluation
convention; no universal runtime schema is introduced.

This sprint changes no production adapter and grants no native OpenClaw/Hermes
admission. Broader quality, independent held-out evaluation, retained use and an
admitted ticket still precede isolated AmIBot and worker scaling. No extra model
tuning budget is selected. Existing active FoundUps remain outside the experiment.

Evidence and current queue: `docs/roadmaps/rsi_swarm_backlog.json` →
`current_observation.operational_general_cohort_20260929`. Local execution,
independent learned-judge review, hosted checks and publication/cleanup receipts
are distinct evidence. Earlier sections below are historical checkpoints.

## General-role JSON decision canary — 2026-09-29

At source `d8263ecf8b6cd3d72244177bde86d292875d106f`, one bounded G01 call
through the existing general-role Qwen3.5-4B chat backend passed strict JSON and
the original independently frozen semantic criteria. This is one known
development case, not a twelve-case result or retained RSI improvement.

| Measure | Observed |
|---|---|
| Attempted / returned / format valid / semantically correct | 1 / 1 / 1 / 1 |
| Input / output tokens | 1081 / 163 |
| Native generation / bounded child wall seconds | 60.562 / 64.672 |
| False completion / unnecessary principal attention | 0 / 0 |
| Provider requests / retries | 0 / 0 |
| Held-out gain / retained gain | unknown / unknown |

The proposal supplied an unsent draft and correctly separated draft preparation
(`ACHIEVED`) from sending (`NOT_ATTEMPTED`). The request appears first. The
secondary availability sentence is vague and remains a wording caveat; it does
not invent a fact under the original criteria. No criteria were changed after
the response. A returned model proposal is never evidence of a provider action.

WSP 15 / WSP 97 selects **the eleven remaining original cases** (13/P1).
Reuse this immutable G01 only if source/runtime/model/template/procedure remain
compatible; label aggregate coverage as a staged **1+11 development cohort**.
Freeze a new budget before any further calls. This canary's one-call budget is
closed. Avoid another G01 tuning cycle or an unnecessary duplicate call.

Full decision coverage, held-out evaluation, later retained use and one admitted
OpenClaw/Hermes ticket precede isolated AmIBot and worker scaling. Production
WRE routing is unchanged. Native admission remains separately blocked.
Canonical evidence and next queue: `docs/roadmaps/rsi_swarm_backlog.json` →
`current_observation.operational_general_canary_20260929`. Publication/main and
owned-lane closure require separate receipts. Earlier sections are historical.

## General-role compatibility layer — 2026-09-29

The existing general-role Qwen3.5-4B model loaded through `LlamaCppBackend` at
source `4ba9ddd1a72b5ba055674e4ef462ef12e90fb1a7`. All 12 unchanged synthetic
Gmail/LinkedIn prompts fit the actual template and 2048-token context with
512 output tokens reserved. Independent artifact review accepted this narrow
compatibility result; no generation or semantic qualification occurred.

| Measure | Observed |
|---|---|
| Child dispatches / successful backend initializations reported by child | 1 / 1 |
| Prompts fitting / tokenized | 12 / 12 |
| Prompt tokens / minimum remaining headroom after output reservation | 1059–1108 / 428 |
| Native load / bounded child wall seconds | 3.062 / 3.875 |
| Generations / provider requests | 0 / 0 |
| Semantic correctness / retained gain | unknown / unknown |

The parent's native-load count remains unknown; the child reports one successful
load. Counts from tokenization are capacity evidence, not inference usage.
All rendered prompts end in an open thinking tag, which alone is not a defect.
The existing JSON grammar path still needs an actual bounded decoder check.

WSP 15 / WSP 97 next layer: **one frozen general-model JSON canary** (13/P1),
then re-observe before a full unchanged 12-case comparison. This completed
budget permits no further model calls. Preserve the previous coder baseline
of 0/12 semantically correct and the original acceptance criteria.

Use the existing backend and process owner; no new router or application module.
Native WRE admission, held-out evaluation, retained use, one OpenClaw/Hermes
ticket and isolated AmIBot remain later gates. The installed/declaration version
mismatch and absence of OS memory/network isolation remain explicit limits.

Canonical evidence and ranked next queue: `docs/roadmaps/rsi_swarm_backlog.json`
→ `current_observation.operational_general_preflight_20260929`. Publication and
main/owned-lane closure require separate receipts. Earlier sections are historical
checkpoints; active YUMORI/eSingularity and Remote-owned AutoPost remain protected.

## Frozen operational decision matrix — 2026-09-29

The frozen diagnostic run uses the unchanged C3 procedure and original
twelve synthetic Gmail/LinkedIn cases. It is supervised local qualification under
WSP 97, using existing model/backend/child owners; no production adapter was changed.

| Measure | Observed |
|---|---|
| Planned / attempted / returned / not run | 12 / 12 / 12 / 0 |
| Format valid | 12 |
| Semantically correct / evaluated | 0 / 12 |
| Known input / output tokens | 12746 / 1195 |
| Measured model-child / total wall seconds | 846.253 / 1145.968 |

All 12 responses were structurally valid, but 0/12 met every frozen semantic criterion. The independent review found one unsupported transaction completion claim (G05) and four unnecessary requests for principal attention (G04, L03, L05, L06). Missing ask-state updates, incorrect objective/transaction distinctions and incorrect action selection prevent promotion.

JSON validity does not establish decision correctness. Independent semantic grading
uses the original frozen criteria, including transaction-versus-objective distinctions.
This is a development baseline; held-out gain, retained use and native admission
remain unproven. No live account actions, candidate promotion or FoundUp launch.

WSP 15 re-observation selects: **Qualify the existing general-role local model for one fixed operational decision comparison before changing the WRE adapter**
(13/P1). The existing WRE adapter resolves the code model, whereas the existing resolver already has a general role for non-code reasoning. The matrix establishes a broad semantic failure baseline; testing role fit is smaller than changing production logic or creating another router. Model availability is not runtime compatibility or decision qualification. First verify the existing general-role runtime and bounded procedure; if compatible, freeze one comparison budget and unchanged criteria before any generation. No additional calls are part of this completed 12-call matrix.

Use the existing model roles, correspondence/recipient guards and unverified-proposal
boundary. Do not add another orchestrator or repair a model claim by relabelling it
as verified success. The installed/declaration version mismatch and lack of OS
memory/network isolation remain explicit qualification limits.

Canonical case outputs, independent judgments, budget, source/runtime bindings and
next ranked queue: `docs/roadmaps/rsi_swarm_backlog.json` →
`current_observation.operational_matrix_20260929`. Publication/main/cleanup receipts
are separate from local model execution. Earlier experiment sections below are
historical checkpoints. Protect active YUMORI/eSingularity and Remote-owned AutoPost.

## First local operational RSI experiment — 2026-09-29

Use the existing synthetic correspondence fixture before building another FoundUp.
WSP 97 classifies this as directly supervised local qualification, not native
multi-agent admission. The existing operational work item remains 14/P1;
native 18/P0 still has its separate seven authority blockers and no effect-use lease.

| Check | Observed result |
|---|---|
| Original twelve full prompts | 4,233–4,281 input tokens; 0/12 fit 2048 with 512 output reserved |
| Experimental compact M2M packet | 1,001–1,049 tokens; 12/12 fit; same cases/labels |
| Existing WRE adapter, C1 G01 | Native generation returned; non-JSON instruction echo; 1 failed, 11 not run |
| Existing local chat backend, C2 G01 | 1,035 input/123 output tokens; Markdown and incorrect objective status; rejected |
| JSON-mode and draft-rule candidate, C3 G01 | Valid JSON; 0/1 correct (objective status wrong); 1,062 input/95 output tokens |

Three generation attempts cover **one known development case**, not twelve
successful decisions. No held-out or retained gain is established. C2/C3 call
the existing generic backend directly; the production WRE adapter is unchanged.
No live Gmail/LinkedIn action, new orchestrator, skill promotion or FoundUp launch.
The local guard enforces time/tree/stdout bounds, not OS memory/network isolation.
Runtime pin mismatch 0.3.20 installed versus 0.2.72 declared remains explicit.

PR #1950 measurement repair is merged/main-verified at 83b06897; hosted PR and main
each passed the same 308 connected cases. Earlier pending/failed entries below
are historical checkpoints, not the current measurement closure state.

Canonical inputs, raw synthetic outputs, counts, judgments and artifact bindings:
`docs/roadmaps/rsi_swarm_backlog.json` →
`current_observation.operational_first_loop_20260929`. Publication and owned-lane
closure have separate receipts; native inference was local, not CI execution.

Build the next layer only after the preceding gate passes:

1. Frozen full 12-case decision baseline and semantic acceptance; preserve failures and stop tuning G01.
   Wire a qualified candidate into the existing WRE adapter only after its acceptance gates pass.
2. Independently frozen held-out/transfer comparison, later-invocation retained use and rollback.
3. One admitted OpenClaw/Hermes ticket, independent verification and observable receipt chain.
4. Isolated AmIBot fixture; then 2→10 worker scaling with measured collisions, cost and rejection rates.

Do not expand into active eSingularity/YUMORI or separately owned AutoPost work.
Resolve the exact Mind FoundUp owner before selection; no guessed module or duplicate plan.

## Hosted measurement portability follow-up — 2026-09-29

Expanded CI on PR1950 head `5449bcde` ran308 cases:306 passed, two failed.
The existing mixed-slash path test exposed a Linux-only filesystem read; reject
both mixed UNC-style prefixes lexically. The existing startup test imported all
of main and hit an unrelated missing Chroma dependency; reuse the established
two-function AST fixture while preserving actual report-reader/output assertions.
No tests were removed. Updated connected local307 pass; final hosted execution
and publication remain bound to the canonical backlog. The earlier103-case
comparison is retained as the initial scalar-repair evidence, not rewritten.

## RSI measurement reader reconciliation — 2026-09-29

The PR #1903 handoff was checked against current main `7c2e0b6f`, not its
historical merge. Existing producer, persisted invocation report, dashboard and
startup owners remain in place. Fix the demonstrated nested Boolean/number
confusion, missing explicit unknowns and overflowed relative-gain acceptance in
the existing reader. WSP15 C2/I4/D4/Impact4=14/P1; this is a bounded R10
measurement prerequisite, not another orchestrator or production RSI grant.

Frozen103 controls: baseline80 passed/23 failed; candidate103 passed, no errors
or skips. Connected local regression307 passed, no errors/skips; three abrupt
process-exit cases were excluded by the local no-child guard and remain in the
hosted full-file selection. Real dry-run producer/evaluator → saved JSON → reader
and asserted advisory output pass for accepted/rejected/invalid/absent proposals
over repeated invocations; aborted and cleanup-failed persisted reports stay
unknown. Startup wiring is tested through two exact function bodies, not a live
main launch. No model/provider/memory/retention execution occurred.

Complete historical v1 reports remain compatible; malformed partial bundles
reject. Finite gains do not authenticate independence, resources, rollback or
retention. Existing sampled evaluator drift/ABA limits remain. The producer's
behavior under synthetic extreme evaluator outputs is a separate unqualified
robustness question; this slice does not claim its numerical domain is closed.

Canonical evidence and pending PR/main/owned-lane closure:
`docs/roadmaps/rsi_swarm_backlog.json`,
`current_observation.measurement_seam_20260929`. After closure re-score the
existing G1–G4 queue: native ticket18/P0 remains blocked by seven trust anchors
and absent effect-use lease; the prior runtime/model/tokenizer qualification
component12/P2 remains the next eligible operational14/P1 preparation.

## Qwen import boundary qualified locally — 2026-09-29

The eager package-import prerequisite below is repaired in the existing Qwen
initializer. The same8 controls move from0/8 to8/8 locally;20 public exports and
their8 original owners remain compatible. Source review and deterministic
manifest/test-registry projections preserve existing ownership. Hosted/main
checks and lane closure are separate gates in the canonical RSI backlog under
`current_observation.qwen_lazy_import_20260929`.

Operational RSI remains14/P1 and incomplete. The next12/P2 component is native
runtime/resolver provenance and a qualified tokenizer-only boundary before the
unchanged12 full-prompt counts. The repository dependency pin0.2.72 and observed
installed llama_cpp_python0.3.20 differ; reconcile their intended ownership
without silently changing the environment. No model/native execution, retained
gain, new WRE grant or AmIBot build is established. PR1948's metadata preparation
is merged/main-verified and its owned lane retired; its closure receipt remains
linked in the existing backlog.

## Local inference readiness qualification — 2026-09-29

The existing local WRE proposal route now has source and artifact evidence in
the RSI backlog under `current_observation.local_inference_qualification_20260928`.
One existing 4,683,073,536-byte Qwen2.5 Coder 7B GGUF is SHA-256 bound, with
29 metadata entries and the installed `llama_cpp_python 0.3.20` source/DLL inventory.
It is the default-folder candidate under the observed pre-import environment;
the actual production resolver outcome and complete native environment remain unqualified.

Ordinary Qwen engine import eagerly reaches the coordinator package graph,
including path/logging mutations. A conservative static graph has108 repository
modules; this is not a claim that108 modules executed. Native imports also load
DLLs and register a logging callback. No product or native import ran in this audit.

The12 frozen prompt digests remain unchanged. Token counts, fit, generated
responses and quality gains remain unmeasured. Model metadata advertises a larger
context, but the existing adapter still requests2048 tokens with512 reserved for
output. The proposed counting check must match completion BOS/EOS/special-token
handling; output-budget clamping cannot count as passing the full-budget check.
The high-level vocabulary-only helper still constructs a context. The proposed
lower-level alternative has partial-constructor cleanup and retry-allocation
limits, so its source/effect plan remains non-executable pending a qualified boundary.

PR1947 is merged/main-verified and its owned lane retired. WSP15 preserves the
operational14/P1 whole item; this12/P2 metadata preparation does not close it.
After publication and fresh observation, qualify the smallest lazy-import repair
in the existing Qwen package using the existing root-package pattern and existing
test owners. Do not add another evaluator or duplicate the frozen controls.
The backlog binds independent review, PR/main checks, Holo and cleanup receipts.

## Operational instruction controls prepared — 2026-09-28

Twelve synthetic instruction controls (six Gmail-shaped, six LinkedIn-shaped) and independently authored labels now reside in the existing [RSI backlog](../../../docs/roadmaps/rsi_swarm_backlog.json), under `current_observation.operational_controls_20260928`. The packet binds the unchanged correspondence/recipient Skillz, subject-visible response conventions, source hashes, full prompt manifests and a proposed bounded local evaluation route. One draft-versus-response outcome ambiguity was corrected before any model output; original label evidence is retained.

Preparation counts are12 inputs/12 labels/12 prompt artifacts. Subject-model calls and evaluated cases are0; correctness, outcome gain, tokens/cost and retained improvement remain unknown. Existing `local_skill_inference` is a concrete text-proposal entry, but its eager imports, exact model/tokenizer,2048-token prompt fit and enforceable resource bounds remain unqualified. Proposed caps grant no execution authority. No application, test, skill, model, provider or CI behavior changes.

PR1946 is merged/main-verified at `daff2848` with29/29 fixed cases and owned closure. WSP15 rescoring preserves59 task identities/26 packets/native7/nulllease; the completed preparation component is12/P2 within the operational14/P1 work item. Publication/main/Holo/owned closure and subsequent rescoring are bound to the backlog receipts.

# WRE Core Roadmap

## Operational RSI measurement and experiment design — 2026-09-28

Planning extension of the [canonical operational decision contract](../../../ROADMAP.md#operational-decision-contract-and-rsi-audit--2026-09-28),
WSP 73 and WSP 48 §4.2. No executable schema, new telemetry store, runtime
activation or production eligibility is introduced. Keep
`wre_rsi_measurements.v1` and its existing producer/consumer truthful about their
current simulator scope; map operational measurements into the existing owners
only after consumer and provenance qualification.

### Existing measurements that must not be conflated

Source checkpoint: `e5600fe103441c91a81e0220aea9e48496b79b60`.

- `src/wre_auto_researcher.py` records candidate evaluations, baseline/best
  fitness, candidate hashes and dispositions. Independent/held-out verification
  and production eligibility are false; unknown resources, rollback and retained
  gain do not become zero. `src/wre_research_evaluator.py` models economic
  assumptions; its fitness is not measured revenue, spend or communication quality.
- `src/dashboard_alerts.py` consumes the bundle as unverified diagnostic
  evidence. File age alone is not authenticated source freshness or promotion.
- `src/pattern_memory.py::get_skill_metrics` counts stored success, whereas
  `get_skill_fidelity_stats` uses a fidelity threshold (0.7) and feeds skill
  ranking. These use different success definitions and default time windows;
  the same configured window can yield the same denominator. Empty-history defaults
  must not be presented as observed performance. `transfer_learning` recalls
  records; `patterns_transferred` does not prove target application or gain.
- `wre_master_orchestrator/src/wre_master_orchestrator.py` currently supplies an
  `outcome_quality=0.0` placeholder in its skill outcome path. That value is not a
  measured quality failure or baseline. `src/pattern_ab_evidence.py` uses sample
  and rate rules; its winner is not statistical confidence or native authority.
- The verified-outcome ratchet and queue-to-PatternMemory admission handlers
  already enforce stronger evidence boundaries. Their existence does not mean
  externally coordinated PR work traversed that native path.

### Proposed operational measures

Report each domain, task class and checkpoint separately. Each value needs its
unit, sample count, source/experiment identity, authority scope and observation
window. `null` means unavailable; zero requires an observed zero. A percentage
with an empty denominator is unknown. Do not combine these into a universal RSI
or consciousness score.

| Measure | Definition and evidence |
|---|---|
| Decision correctness | Correctly scoped/routed decisions / eligible labeled cases; frozen independent labels distinguish act, draft, escalate, defer and abstain |
| Outcome attainment | Independently witnessed declared outcomes / eligible cases whose observation window matured; report pending, censored and failed counts separately. A delivery receipt is only transaction evidence |
| Truthful completion | False success claims / evaluated attempts, plus coverage of negative/unimplemented/uncertain-result fixtures |
| Authority and privacy | Unauthorized effects or disclosures / evaluated attempts, with the tested negative-case inventory. Zero observed violations does not prove universal safety |
| 012 attention | Necessary versus avoidable escalations, corrections and measured review minutes per eligible task; label necessity independently. Legitimate escalation must not be penalized |
| Efficiency | Authenticated total tokens, currency cost and wall time, including failed proposals and verification, per correctly completed outcome. If no correct outcomes, report totals and an undefined ratio |
| Paired improvement | Mean per-case candidate outcome minus baseline outcome on the same frozen cases and conditions; report discordant pairs and uncertainty. Relative gain is undefined when the baseline is zero |
| Transfer and retention | Paired gain on separate unseen task/entity cases; repeat at a later checkpoint after unrelated learning and measure loss/regression against the earlier checkpoint |
| Learning/admission quality | Candidate proposals, rejects, invalid runs, rollbacks and independently accepted procedure versions; tie later decisions to the version actually used, not just stored |
| Mechanism attribution | Trace the authorized save → retrieve → apply → correct path for eligible episodes; report each observed stage and missing evidence separately from task score. A memory write alone earns no reuse claim |

Style checks (purpose/request early, necessary context, concision, relationship
continuity) support decision correctness. Their scores cannot replace outcome
attainment. A persuasive message may still seek the wrong thing. Preserve 012's
objective corrections and rejected approaches as evidence of that distinction.

### Smallest bounded pilot, proposed counts rather than results

1. **Qualify evidence first:** independently freeze 12 synthetic contract cases
   (six Gmail-shaped, six LinkedIn-shaped) in existing test owners. Include
   ambiguous identity, stale context, absent authority, appropriate escalation,
   an unresolved substantive ask after a routing reply, uncertain submission and
   a no-op that must not count as posted. No real account actions or private
   correspondence are required. Repair only demonstrated existing-owner defects.
2. **Prepare a comparison:** if qualification passes, predeclare 40 held-out
   scenarios (20 per domain), separate from development cases. Freeze objective,
   acceptance rubric, model/tool versions, allowed effects, evaluator identity,
   random seeds where applicable and total time/token/currency caps before
   evaluating a candidate. No paid-provider dispatch until those numeric caps
   and the execution route are actually admitted. These sample counts are a
   feasibility proposal, not a power calculation or paper-mandated threshold.
3. **Bound adaptation:** baseline versus at most two candidate procedure versions;
   score the same cases with a separately controlled evaluator. Keep acceptance
   data unavailable to the proposer. If acceptance feedback is used to redesign
   the procedure, reserve a new untouched confirmation set and account for every
   proposal. No automatic 10 → 20 → 40 cycle escalation.
4. **Test persistence:** freeze baseline, candidate and post-unrelated-learning
   checkpoints; add 20 separate transfer/retention cases (10 per domain). Compare
   with both a non-evolving control and the same candidate with its learned
   artifact disabled, so base-model skill is not mislabeled as retained learning.
   Clear volatile conversation context between episodes; preserve only the
   declared persistent state. Include stale-state, irrelevant-memory and wrong-
   procedure controls and authenticated read/apply traces.
5. **Accept narrowly:** require zero observed authority/privacy/false-completion
   violations and no correctness regression in the declared sample. Report effect
   size and a prespecified paired uncertainty analysis; repeated selection needs
   its own error-control plan. Retain as *improved* only if a predeclared meaningful
   positive gain is supported on the primary outcome (or declared efficiency
   outcome with correctness preserved). Zero gain is not improvement. An
   underpowered or mixed result is inconclusive,
   not production success. Keep evaluator criteria fixed, record rejects, and
   require the existing independent admission/rollback chain before retention
   or activation. This pilot alone cannot close G2-G5.

The first 12 cases qualify a contract; they do not run a model or demonstrate
autonomous learning. Costs, live outcome windows, statistical power and deployment
authority remain prerequisites of later stages. Re-score with WSP 15 after each
stage; stop when a real blocker or violated acceptance condition is observed.

### Primary research coverage and limits

Reviewed on 2026-09-28; a targeted research update, not an exhaustive literature
review. All proposed FoundUps measures/counts above are design choices for this
system, not results reported by these papers.

- [Chen, Wang and Qu, RSI survey v2](https://arxiv.org/html/2607.07663v2): main
  taxonomy, evaluation, research and discussion sections reviewed; interpretation
  and limitations recorded in the root roadmap.
- [EvoPathBench (21 September)](https://arxiv.org/html/2609.24663v1): methods and
  evaluation sections reviewed. Fixed models/tools, frozen artifact checkpoints,
  held-out tasks and artifact-disabled controls help distinguish transfer,
  retention and adaptation. Its finance setting does not validate our mail or
  social workflows.
- [PACE (6 June)](https://arxiv.org/html/2606.08106v1): acceptance method and
  limitations reviewed. Repeated noisy candidate selection needs explicit
  statistical controls. Its per-decision guarantees are not a run-wide error
  guarantee, and this roadmap does not claim to implement PACE.
- [PAST-Bench (4 August)](https://arxiv.org/html/2608.04003v1): evaluation pipeline
  and limitations reviewed. Fresh sessions, persistence-on/off comparisons and
  save/retrieve/update traces directly address personal-agent learning. Hermes+
  is a research variant, not evidence that our installed Hermes is updated or
  qualified. Its reported overall gain difference is smaller than run variation;
  memory accumulation alone is not proof of beneficial reuse.
- [AIDE² (22 September)](https://arxiv.org/html/2609.26457v1): abstract and method
  reviewed. Fixed per-task cost budgets and private grading support its research-
  agent rewrite experiment. Its held-out transfer results motivate testing our
  retained procedures under fixed resources; they do not prove FoundUps gains.
- [RSIAgent (14 September)](https://arxiv.org/abs/2609.15364): abstract reviewed
  only; verifier-assisted exploration and frozen memory are a comparison lead,
  not a validated replacement for our admission or evaluator path.
- [SEA-Eval (10 April)](https://arxiv.org/abs/2604.08988) and
  [FinEvo-Bench (6 August)](https://arxiv.org/abs/2608.06144): abstracts reviewed
  only, motivating further sequential-task and paired-control comparison.
  No FoundUps capability claim depends on their reported benchmark scores.

## RSI verification hierarchy and measurement contract — 2026-09-25

WSP 48 now adopts the research verification hierarchy: intrinsic signals <
learned judges < execution feedback < formal verifiers, while human research
judgment remains the unresolved direction-setting rung. The current
AutoResearcher is truthfully classified as **execution feedback**.

Every AutoResearcher invocation now emits a persisted `wre_rsi_measurements.v1`
bundle containing baseline/best fitness, absolute/relative gain, evaluator and
outcome counts, and explicit unknowns for independent verification, resource
usage, activation rollback and successive-generation gain. The dashboard
consumes and validates this bundle instead of treating a raw fitness delta as
an RSI claim.

This closes a measurement/labeling gap only. It does **not** close G2-G5.
Next RSI closure work remains: independent authenticated evaluator + held-out
cases, receipt-backed resource usage, governed activation/canary rollback, then
multiple successive generations showing retained measured benefit under fixed
criteria.


## Advisory research display — 2026-09-24

The planned launch seam now consumes an explicitly selected local ROC report in
the existing dashboard/startup owners. It validates displayed accounting and
labels it **unverified diagnostic**; absent/stale/aborted/inconsistent input is
unknown. File age is not execution freshness. Health enforcement is preserved.
No researcher, model, queue, retention or campaign is launched by the new read.

All 67 focused cases pass locally and independently. The initial 63-case baseline
was 7 pass / 56 fail. Independent source review then found impossible gain with
zero accepted attempts: two added controls failed before repair and pass afterward.
Two further mixed-slash UNC controls failed before lexical drive rejection;
all 67 then pass. No network access was attempted under the filesystem sentinels.
Exact startup function bodies are exercised without full main import/menu effects.
Main remains 4855 lines; six new dashboard helpers are at most 42 lines.

PR1898 comparison-guard work is merged as `c1eeaa08f3f8eecfdf43c2b66a407bb31a0f8019`,
all ten PR checks and both main workflows passed, and its owned lane is retired.
The 14/P1 consumer investigation closes as source reconciliation: the existing
ratchet accepts admitted, independently verified published work; raw ROC reports
cannot supply that chain. Repeating caller-absence tests would duplicate evidence.

The remaining launch plan still requires authenticated program/oracle/runtime
identity, an admitted campaign and independent retention acceptance. Explicit
diagnostic display does not close those gates. Re-observe the canonical backlog;
the next executable candidate is fake-only LinkedIn manager-result qualification
12/P2, a daily-work effect boundary, with no live UI or external sends.

## Persistent comparison-profile guard — 2026-09-24

The existing evaluator and dry-run producer reject persistent consumed-profile
drift before a candidate can advance best metrics. Costs still use a separate
immutable invocation catalog. The comparison basis preserves effective distribution
order/membership, current consumer values and actual consumed definition-bound
defaults. Invalid capture is reported before baseline evaluation; later runs refresh.

All 66 fixed controls pass locally and independently after a 32-pass/34-failure
pre-change baseline; all 136 existing lifecycle/program cases also pass. There are
202 unique cases, not 404. The genuine multiplier change still improves the real
synthetic model. The shared economic calculator is unchanged.

Before/after checks do not freeze consumption: an explicit transient change restored
inside evaluation still escapes detection. Concurrent evaluation, authenticated
program/oracle/environment identity and independently retained benefit remain open.
Do not expand into an immutable-profile rewrite merely because that limitation exists.

Historical next 14/P1, reconciled above: determine the intended existing WRE consumer boundary for
ROC reports before extending oracle identity. Locate an actual accepted/error/cleanup reader and its
existing WRE evidence contract, or record the missing connection with a smallest
existing-owner repair. Keep ROC research separate from model AutoResearch and the
registry-workflow correctness oracle; no parallel framework or runtime authority.

## Remaining evaluation-profile qualification — 2026-09-23

Historical PR1897 qualification: all 43 fixed cases passed locally and independently: 22 existing
cost controls plus 21 profile cases. Production source is unchanged. Seven
isolated subscription/distribution/margin/angel/fee changes and a combined change
can remove the ROI penalty while target/proposal text and compute results stay
identical. Apparent fitness rises by 5; this is dependency drift, not improved code.

The fixed baseline has revenue 26830, burn 27000, margin -170 and fitness -281/64.
The eight upward crossings retain ROC 39/64 but switch ROI to true. Reverse and
membership controls preserve the best baseline while recording changed candidate
metrics. Exporter rebinding and reassigned constructor-default globals do not
behave like actual consumer mutation. Finite SATS_PER_USD does not alter returned
scores; invalid values can fail construction. Empty distribution uses a live fallback.

Historical next step, addressed by the bounded guard above: extend the comparison boundary for consumed profile
values and catalog membership, including failure inputs and already-bound defaults,
or explicitly reject drift. Preserve one-argument evaluator and existing keyword
compatibility, per-invocation isolation and cleanup/report contracts. Freeze repair
acceptance before editing; do not treat characterization of bad acceptance as desired
behavior. Complete oracle authentication and retained benefit remain separate gates.

## Invocation-scoped cost comparability — 2026-09-23

The14/P1 repair closes PR1895's dependency-only cost acceptance gap. Baseline and
candidates now consume one immutable numeric cost/name snapshot per invocation;
later calls capture current values. Direct evaluator calls retain valid one-argument
behavior. Invalid/empty explicit catalogs cannot fall back to globals; invalid
captured totals abort before evaluation with terminal reporting and cleanup.

Fixed22cases pass locally and independently after2pass/20fail baseline. The136
existing lifecycle/program cases also pass, including3 bounded child exits.
No native worker/provider or retained-learning claim. Same-instance concurrency
and atomic capture under concurrent global mutation remain unsupported.

WSP62: same-file baseline/scoring extraction reduces inherited class249→242,
loop82→75 and evaluator93→60; researcher594lines remains below600. New helpers
are bounded; legacy996-line lifecycle tests only adapt signatures/stub imports.
Continue reducing inherited orchestration debt when that owner is next changed.

Historical next step, now qualified above, examined remaining ROC assumptions:
distinguish live economic dictionaries from already-bound constructor defaults,
enumerate values actually consumed and fix a comparison oracle before choosing
further capture/report integration. Avoid one-constant repairs or unused hashes.
Complete oracle/environment identity and independent retained benefit remain open.

## Actual-loop comparison qualification — 2026-09-23

The13/P1 qualification extends the existing evaluator-input test owner with two
one-attempt controls using the real dry-run producer and evaluator. Identical
candidate text rejects with stable synthetic costs. Changing only one cost in
the proposal callback accepts with simulated improvement975/6592, despite equal
baseline/proposal digests. The independently derived full metrics include ROI
and expose an incomparable-basis result; they do not validate economic assumptions.

The three fixed cases (one preserved evaluator case plus two loop controls) pass
locally and independently. Saved JSON, TSV, history, planned operations, source
and scratch restoration agree. Model loading is disabled before construction;
no provider, native worker, live commit or retained improvement occurs. Production
source is unchanged. This closes the actual-loop observation, not the repair.

Historical follow-up, now addressed for cost inputs above: define the smallest comparison-basis repair
in the existing evaluator/producer before admitting score improvements. Consider
freezing the consumed input values versus rejecting detected drift; enumerate
remaining mutable dependencies and concurrency limits. An unused digest or a
cost-only claim of complete oracle identity is insufficient. The canonical
backlog retains broader native/runtime/authority blockers and publication evidence.

## Evaluator dependency qualification — 2026-09-23

The12/P2 qualification confirms that fixed target bytes can produce different
scores when a shared cost input changes. One real-evaluator case uses synthetic
local costs and independently calculated expected cost/margin/ROC, then restores
the dependency and reproduces the full baseline. Local and independent replays
pass the same case; original target bytes and table keys/object identities are
preserved. Source behavior remains unchanged and is not labelled a defect.

This closes the narrow dependency-sensitivity question. Effective oracle and
workload identity, admitted comparison/consumer binding and independent retention
remain open in the15/P1 report parent. Do not add an unused hash or equate a target
or evaluator-file digest with its mutable dependency state. The canonical backlog
reconciles PR1887 closure and selects the next eligible core runtime prerequisite.
No native OpenClaw/Hermes/FoundUp activation is implied.

## Attempted-call program identity — 2026-09-23

The13/P1 change extends the existing AutoResearcher report with per-call rendered
instruction hashes. It preserves three-argument proposal callbacks, mode gates
and exception behavior. Ordinals distinguish multiple backend calls within one
iteration; the collector resets between invocations and restores prior state.
Encoding failure is recorded without suppressing the call. Backend failures and
interruptions remain visible; bypass/heuristic paths fabricate no input record.

Local and independent24-case qualification includes the seven prior controls plus boundary and
restoration cases. Independent review caught a rendered-str-subclass mismatch;
a failing regression preceded the fix.34 unchanged legacy regression cases pass.
Exact independent replay, publication and next selection belong to the canonical
backlog. This advances the15/P1 report parent, which still needs authenticated
provenance, evaluator/environment qualification, consumer binding and retention.
No live OpenClaw/Hermes or FoundUp build is enabled by this diagnostic field.

## Program-consumption qualification — 2026-09-23

The12/P2 seven-case characterization is locally and independently verified at
base `228ecbe0`. Program-file contents are captured at construction, but each
LLM prompt reads the current mutable instruction attribute. Baseline and backend
callbacks can change what later calls receive. A failing backend still receives
its prompt; heuristic/zero-attempt paths make no backend call.

Tests reuse the model-disable fixture and actual prompt/loop code with fake
metrics/backend responses. Production and the996-line legacy test file remain
unchanged; a107-line focused sibling avoids unrelated file growth. This qualifies
current consumption, not program identity, authenticated provenance or retained
learning. The15/P1 report program still needs program/oracle/environment/reader
contracts. Do not add an unused reader or label an entry hash as consumed input.
The canonical backlog records the next bounded action and the separate paused
lineage draft, with current ownership and publication state.


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
source inspection and the rehearsal below. Explicit advisory report wiring is now implemented in the 2026-09-24 checkpoint above; admitted campaign/retention remain planned.

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
| `main.py:run_wre_dashboard_preflight` and `src/dashboard_alerts.py` | Current startup health/sample warnings; may dispatch resolution events. Not an RSI benefit report or a wholly read-only path. | Explicit advisory ROC display is implemented above; automatic report selection and admitted campaigns remain separate. Do not infer learning from health/sample count. |
| `main.py:_reddog_run_bounded_control_rounds` | Existing resident serial/claim rounds, configured default eight, idle/failure stops and receipt persistence. Count bounds alone are not time/cost bounds. | Compile an eligible campaign into current admitted jobs; retain stop, claim and receipt owners. No new ten-round default is enabled here. |
| `src/wre_auto_researcher.py` / `src/wre_research_evaluator.py` | Isolated dry-run ROC configuration proposal/evaluation and per-run TSV; constructor attempts Qwen loading. | Terminal accounting and explicit unverified launch reading are implemented. Authenticated source/oracle/environment identity remains required for qualified-benefit display or an admitted campaign. Keep its simulator judge task-specific. |
| AI Gateway model AutoResearch | Existing [benchmark and feedback contracts](../../ai_intelligence/ai_gateway/INTERFACE.md#benchmark-evidence-and-outcome-receipts) bind task family/split, model, verifier, cost and latency. | Reuse for model selection under current provider budgets/admission. A model campaign is not a generic repository editor. |
| WRE differential tests, independent slice verifier and PatternMemory | Existing [verification and retention contracts](INTERFACE.md#outcome-recording-and-retention). Production acceptance/activation and later benefit remain incomplete. | Bind accepted evidence to the exact artifact and prove a later invocation consumes it successfully; keep write/read/promotion authorities distinct. |

### Current core canary test checkpoint — 2026-09-23

PR1877/1879/1880/1882 closed callback/chain, generation, final-receipt and
PatternMemory evidence qualifications. The13/P1 worktree projection now passes12
fixed cases locally and independently:10 direct disposable real-Git cases plus
two existing blocked callbacks. Registry/HEAD readers accept the registered
external control and reject stage/result/path, isolation and lineage mismatches.
Input stages, repository/worktree HEAD and registry stay unchanged. Existing
fixtures/test owner are reused; production remains unchanged. This is local
structural consistency, not authorized worker creation, native execution, race
confinement or retained improvement. AmIBot remains undispatched; Memory Horizon
is separately owned. The [canonical backlog](../../../docs/roadmaps/rsi_swarm_backlog.json)
binds exact source, ownership, tests and the re-scored next action.

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
