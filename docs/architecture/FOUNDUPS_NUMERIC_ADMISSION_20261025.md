# Simulator work/stake/unstake numeric admission — 2026-10-25

## Pre-code allocation and current authority

Allocated by the parent before test/product authoring:
**C3/I4/D4/Impact4 = 15/P1** under WSP15.
This phase authorizes this plan and RED tests only. Product authoring is blocked
until the parent accepts the frozen test contract and explicitly releases it.

Base: `f11d7559746bb64677e448ff8e4e24ebfcea8feb`.
Worktree: `C:/Users/user/.codex/worktrees/foundups-fx-chain-delivery/Foundups-Agent`.
Branch: `agent/foundups-numeric-admission-20261025`.
Role0102/worker; origin internal_handoff. No Git stage/commit/push, dependencies,
keys, provider calls, persistent daemon data or financial effects.

Source/test match the prior read-only numeric research exactly:
- `modules/foundups/simulator/economics/token_economics.py`: raw SHA256
  `c0dee07c331a520119b942a4f5bc5ea448d69fd0d9c5f9ac438e5fc8b8eb6a1c`.
- `modules/foundups/simulator/tests/test_alignment_and_tokenomics.py`: raw SHA256
  `abeef89b41f3d944c6c6490603317999cb311b8e04bb0871ebb0a52efc29e3c5`.

## Contract and scope

Selected existing paths:
- FoundUpTokenPool.mint_for_work, stake_ups, unstake_fi.
- Pool.update_adoption only for the work_completed operand used by selected work;
  invalid work rejects before any mixed valid metric inputs are assigned. This
  does not add independent revenue/count admission guarantees.
- TokenEconomicsEngine.agent_completes_task, human_stakes_ups, human_unstakes_fi.
- Wallet.spend and account.receive_fi/record_stake/record_unstake only as the
  selected path's called mutations; shared pure numerical preflight.
- Relevant fee operands as read at use, including mutable injected FeeConfig and
  discounted staking rate. Preserve existing default internal wallet fee source.

Invalid arguments raise documented ValueError before registration, gas spending,
adoption updates or participating balance/treasury/reward/position mutations.
Accept built-in int/float quantities, excluding bool/coercible text/custom numeric
objects; reject negatives, NaN and infinities. Preserve zero, fractional finite
values and current insufficient-funds zero/false results. Unsupported huge
integers or arithmetic overflow must reject before effects, not leak an exception
after a debit. No rounding, unit conversion or aggregate cap is added.

Selected operation fee rates must satisfy **0 <= rate < 1**. The exact100% fee
endpoint is deliberately rejected: existing code's zero-net commit behavior is
undefined/inconsistent. This is fail-closed admission; no new burn/refund/ownership
policy is introduced. Preserve all configured fee math and valid mutable configs.
At-use checking is required; constructor-only FeeConfig checks are insufficient.

Compute prospective participating results privately and validate finite/nonnegative
values before assignment. Input-only isfinite does not prevent1e308+1e308 overflow.
Work must preflight both operands, adoption/mint and owner credit before gas or
new registrations. Neither helper nor result may mutate live objects during
preflight. No generic transaction/rollback framework or second economic ledger.

Independent credit/allocation/conversion/profit entrypoints, outer Mesa/CABR and
allocation batches are OUT. Only minimum preflight for mutations called by the
selected paths is included. A proposed change that needs to alter an OUT path
must return scope pressure to the parent before authoring. No whole-engine,
whole-simulator, custody, funded settlement or complete blockchain claim.

## Reuse and exact implementation budget

Product budget after separate release: **one existing product file** and **one
existing test file**, no new Python files, exports, public signatures, SDKs or
runtime dependencies. Parent owns publication/manifests/security; module docs
follow only after source/test freeze and independent review.

WSP62 baseline: product1375lines; HumanUPSAccount289, FoundUpTokenPool271,
TokenEconomicsEngine445. update_adoption60 and unstake_fi52 are inherited review
debt. Planned source ceiling **1424 lines** (net<=49), target no class-span growth.
At most **three private pure helpers**, each<=40lines; no new/grown function>50.
Touched inherited update_adoption may remain<=60 only without growth; reduce
unstake_fi to<=50 if modified. Candidate class spans must remain at/below baseline
where practical; any inability to meet the bound returns for scope review rather
than silently expanding it. No candidate-created exemption or framework.

Existing test file102lines: extend to **<=550lines**, helpers/tests<=50lines,
using parameterization and meaningful before/after/success assertions.
Preserve the original module docstring, imports and all six test function ASTs,
including the200→194(fee6)→184.3(fee9.7) oracle and MINED adoption cap.
No new repository suite file or generic actor grant fixture.

## Baseline/RED qualification and execution plane

WSP97 local deterministic execution plane; provider/model/WRE runtime calls are
not applicable. Holo/Gemma/Qwen results cannot replace direct arithmetic proof.

The existing test file eagerly imports Mesa and FAM and one old case instantiates
them. For this no-Mesa/FAM phase use an external AST projection of the exact
three original pure numeric test nodes (adoption bounds, mint cap, stake roundtrip)
and all added numerical tests. Direct-load only token_economics.py and pytest/
stdlib. Preserve original test bodies/decorators/parameterization and bind their
ASTs, original paths/canonical IDs, source/projected bytes and hashes in receipts.
No runtime assertion or economic implementation substitution.
The other three original cases remain untouched but are deferred to the later
proper full simulator closure. Projection is a bounded test method, not ordinary
whole-file pytest qualification.

Runner: existing vetted `O:/Foundups-Agent/.venv/Scripts/python.exe -B -X utf8`;
PYTHONDONTWRITEBYTECODE=1, PYTHON_DOTENV_DISABLED=1,
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1, HF/HOLO offline/skip-model, cacheprovider off,
external TEMP/TMP/pytest base, socket/DNS guards, dotenv forbidden.
Reject unexpected imports of simulator Mesa/FAM/provider modules.
No package constructors, default singleton or daemon initialization.

Order:
1. Record unchanged3-case numeric baseline with source hashes/AST inventory.
2. Append meaningful bad-quantity/fee/mutation-order/overflow and valid controls
   to the existing test owner.
3. Record desired RED against completely unchanged product; exact collected
   canonical IDs, outcomes, exception/assertion failures, hashes and0 attempts.
4. Freeze plan/tests; report to parent. No product edits in this phase.
5. After explicit release, GREEN then independent held-outs and unchanged
   adjacent profit/allocation/lifecycle oracles, affected simulator closure.

## Retrieval evaluation before authoring

WSP00 awakening executed in selected root; tracker is_zen_compliant=true.
WSP97, WSP15/62 inherited/current rules, MASTER rows and NAVIGATION:94 verified.
Current simulator README/INTERFACE/ROADMAP/ModLog/tests README/TestModLog relevant
portions read before authoring; long historical logs selectively refreshed.
memory/README.md and requirements.txt are absent, requirements-sse.txt optional.

Canonical task-source owner query:
`simulator numeric admission work stake unstake wallet invalid quantity tests`,
limit5/include_bundle/module_hint modules/foundups/simulator.
Result: HOLOINDEX_AUTHORITY_ROOT_HEAD_MISMATCH; ok=false, freshnessUNKNOWN,
index_gap_detected=true; authority a519f0ad... versus selected f11d7559...;
workspace_head bundle, overlay=false, owner_attempts0. No reindex/change of root.
Bundle enumerated current contracts but missed nearest numerical tests and
returned unrelated WSP hits. Direct rg/NAVIGATION/current owner/test reads supply
must-include evidence. Current contracts precede historical reports; deduplicate
paths, retain staleness and missing-artifact limits. No semantic success claimed.

## Status

PRE-CODE plan/tests frozen; product remains unchanged at its initial raw hash.

External evidence root:
`C:/Users/user/AppData/Local/Temp/foundups-numeric-testfirst-fc613fcc381141c98b319c94faffd072/`.

- `baseline/receipt.json`: three unchanged original pure numerical cases pass.
- `red/receipt.json`: initial200 cases,184 desired failures/16 passes.
- `red_temporal/receipt.json`: independent-review additions,218 cases,
  200 desired failures/18 passes.
- `red_final/receipt.json`: final219 cases,**200 desired failures/19 passes**,
  zero skips/setup errors, zero guarded attempts/forbidden runtime imports,
  stable source/test hashes during the run. Product was never edited.

Independent pre-product review confirmed all six original function ASTs, original
imports and module docstring unchanged. It found missing owner-only overflow
coverage; those controls were added before product authoring, alongside effective
discount, invalid-even-insufficient, called-mutator overflow and valid-first-work
controls. Work metrics preserve their existing double increment on valid rewards.
Three original nonselected cases are deferred, not reported as fresh passes.

The final runner snapshots raw input files and itself; receipts bind selected AST,
projection and canonical source IDs. Earlier runner phases retain their exact
outputs/projections/receipts; their totals overlap and are not added.
Product implementation, full simulator/adjacent closure, main convergence and any
financial activation remain unperformed and separately gated.

## Product release event — 2026-10-25

Parent accepted the frozen219-case RED contract and released product authoring
for the selected token_economics.py boundaries only, under the same15/P1 scope.
This event is appended BEFORE product edits. No OUT expansion, signatures, new
repository Python files, generic transaction framework or Git mutation is
authorized. Readable preflight that exceeds the planned size budget must return
actual size/scope pressure before expansion. First qualification is the frozen219
projection; source freeze then independent review precedes any full simulator run.

## Pre-product contract refinement — 2026-10-25

Parent declined the external clone-mutator draft before it was applied or run:
the existing INFO logs are observable during staging, so that path is not pure.
Checked-out product remains unchanged. Add RED controls before product for:

- Nonfinite prospective wallet total_debit raises ValueError before insufficient
  funds can short-circuit it, including selected engine work.
- Positive finite subnormal stake/unstake amounts whose valid rate<1 nevertheless
  rounds the fee to the full amount and net to0 raise ValueError. This is an
  unsupported numerical representation, not a replacement economic policy.

All ordinary finite configured fee and zero/fractional controls remain. A cohesive
pure-calculation extraction proposal, with measured file/helper/class/function
budget, must be accepted in an updated allocation before canonical product edits.
The prior219-case freeze remains historical evidence, not final refined coverage.

## Revised pure-extraction allocation — 2026-10-25, BEFORE canonical edits

Parent accepts the225-case RED contract (206 desired failures/19 passes) and
explicitly releases one cohesive private arithmetic owner:
`modules/foundups/simulator/economics/_token_numeric.py`.
Priority remains **C3/I4/D4/Impact4=15/P1**. The earlier clone draft remains
rejected/unapplied/unexecuted; the old3-helper/net49-line budget is superseded.

Exact bounds:
- New internal owner<=320lines HARD, target240–280; prefer<=220 and9 pure
  functions where readable. At most11 pure functions<=40lines and8 immutable
  scalar result records<=20lines. No gratuitous classes/long positional tuples.
- Existing token_economics.py<=1375lines HARD, with public class/function/export/
  signature/module identities preserved. Class ceilings: HumanUPSAccount289,
  FoundUpTokenPool271, TokenEconomicsEngine445. Wallet<=80 permits only its
  specific preflight wiring, versus baseline67. New/grown selected functions<=50.
- Existing test owner<=550lines; no new repository test file or new public API.

Pure helpers have no logging, I/O, domain imports or import side effects; they
contain shared existing calculations only. Engine preflight and standalone
mutators use the same formulas. Commit assignments/post-commit logs preserve live
object references and valid double-work arithmetic. Composite log granularity
may change; no log describes an unsuccessful numeric preparation as a spend.
Unknown valid-but-insufficient work no longer registers objects before failure.
No generic transaction, rollback, second ledger or OUT atomicity guarantee.

One required AST-reachable source member is explicitly accepted as a future
parent-owned derived allocation: measure1471 accepted/1472 rejected, both pins,
fixed caps, generator and exact security bindings after source freeze. This is
not a blanket cap increase or authority for this worker to edit manifests, pins,
registry, security ledger or derived controls now.

Frozen225 exact-AST projection GREEN is the first gate; then source freeze and
independent parent review precede full simulator/adjacent qualification.

## Optional-None control correction — 2026-10-25, BEFORE test edit

Parent classifies only the adoption-work/None Cartesian pair as nonapplicable:
the public update_adoption signature explicitly uses work_completed=None for
no increment. Omitted/explicit None must retain that existing behavior. Other13
None rejection cases remain. Replace this one false negative with a positive
optional-None/omitted-work compatibility oracle, without a skip or signature change.

Original225 RED206F/19P includes one incorrect negative control and is retained.
First pure candidate225 run224P/1F likewise remains evidence of the contract gap,
not a product defect. Corrected225 inventory is205 negative/20 positive. Its
original-source replay occurs AFTER authoring and is an effective negative
control, not retroactive test-first proof; load an external exact rawc0 source
copy and keep the canonical candidate untouched.

## Valid engine normalization regression — 2026-10-25

Corrected225-case candidate passes, but an independent guarded original/candidate
witness exposed a real compatibility defect: requested built-in int cost2**53+1
with policy max_per_task2**53 was previously float-normalized before the policy
check and admitted. The strict candidate denied it. Preserve existing engine
float normalization AFTER strict built-in/finite/nonnegative admission; do not
introduce a precision policy. Add one positive regression in the existing test
owner and record its RED before this narrow product correction. Parent's release
permits candidate arithmetic repair only for such a demonstrated actual defect.
The225 GREEN and witness remain bound to the prior candidate hash.

## Candidate source freeze — 2026-10-25

Pure scalar extraction is implemented only in the allocated owners. Existing
token_economics.py shrinks1375→1351lines; _token_numeric.py is156lines, with11
pure functions and5 small immutable numeric records. Wallet64/account289/
pool229/engine439 meet the allocated class bounds. All new/touched selected
functions are<=50lines; two unchanged OUT functions retain inherited size debt.
The test owner is527lines. No source-cloning or live mutators run in preflight.

Chronology, without adding overlapping counts:
- Unchanged baseline3 selected originals pass.
- Initial200 RED184F/16P; temporal218 RED200F/18P; original219 RED200F/19P.
- Representability225 RED206F/19P includes the one incorrectly classified
  optional-None pair; first pure candidate225 produced224P/1F on that pair.
- Parent-classified corrected225 replay against external raw originalc0 source
  AFTER authoring produces205F/20P. Canonical candidate is not replaced.
- Corrected225 candidate passes; the independently demonstrated valid integer
  cost normalization regression then produces1F/225P with the new226 inventory,
  BEFORE restoring strict-admission-then-float normalization.
- Final corrected226 **all pass**,0 skips/setup errors,0 guarded network/dotenv
  attempts or forbidden Mesa/FAM/model imports; all measured inputs stay stable
  in-run. This is selected exact-AST projection, not full-file/full-simulator
  qualification. The3 unrelated original cases remain explicitly deferred.

Evidence under the existing external root: red_representability/receipt.json,
green_candidate/receipt.json, red_corrected_after_authoring/receipt.json,
green_corrected/receipt.json, valid_policy_coercion_probe.json,
red_policy_normalization/receipt.json and green_policy_fixed/receipt.json.
Runner snapshots bind canonical namespace direct loading of the actual two
product files, without executing package initialization. Corrected original
replay separately binds the effective rawc0 external source copy.

Composite work/stake/unstake log granularity changes to engine summaries after
all numerical results commit; independent standalone mutators retain their own
logs. Unknown valid-but-insufficient work no longer registers its wallet/pool
before failed preparation. Existing references, fee math, public signatures and
double work-metric arithmetic remain. This is numerical preflight in the existing
simulation call, not concurrent isolation, outer-call atomicity, custody or
settlement. Parent independent review is the next gate; no full simulator or
adjacent suite, generated closure, manifest/pin/security/Git action is claimed.


## Parent qualification and publication preparation — 2026-10-25

Independent held-outs pass28/28; actual full simulator closure passes633,
including all6 original alignment cases and8 adjacent cases, with exactly3
existing SSE exclusions. Counts overlap the226 focused cases. The real central
daemon singleton was configured with an external scratch data_dir before FAM
construction; no callback/start replacement or economic assertion substitution.
Zero instrumented network/dotenv/checkout-write attempts, all SQLite connections
scratch/memory, default central-store names/sizes/mtime_ns unchanged. Historical
older runs without this explicit central confinement are not relabeled.

Independent receipt rawSHA256
07053c264d5cc7fc197d56364fab5855db6edd66b6507e3f05d70464f6651367;
full handoff rawSHA256
6f6a44af3bdd01ba975af7d783fd9f1617a1b4ced45c5a57f9ebba86b4a53060.
Parent accepts the frozen source for publication preparation. A first diff-check
rejected one extra blank EOF line in the existing test owner before staging;
only that blank line was removed, with the complete test AST verified identical.
Historical receipt hashes retain the actual earlier bytes. Fresh combined-main
qualification, derived closure and security review remain required before merge.

## Combined main and derived closure allocation — 2026-10-25

Numeric source commit dc844e3ba8a52d367af4e8e9f490316c88c9aa66 is reconciled
with verified main6fe7eba424c17f7813043dfb104cd845617cab38 at
89486886f87dbe4216fdcfc3afa513cd23f2cac5. No arithmetic bytes changed.
Fresh actual whole-simulator736 passes in60.00s;169 simulator/FAM sources and8
central sources stable, all original/adjacent required IDs present, exact3 SSE
exclusions, zero instrumented network/dotenv/checkout-write attempts. All13532
SQLite connections use scratch/memory; default central store stats unchanged.
This supersedes no historical result and does not add overlapping counts.

BEFORE derived edits, parent allocates C2/I5/D5/Impact4=16/P0 to regenerate the
existing manifest and two pins for exactly one required arithmetic member:
economics/_token_numeric.py. Accept exactly1471 members and reject1472 using
the existing explicit Node boundary oracle. Change MAX_RUNTIME_FILES1470->1471
only for that measured member; keep328KiB manifest,2MiB/source,32MiB total caps.
The existing test's1470/1471 accepted/rejected constants advance1471/1472;
no generic cap widening, runtime endpoint or installed-runtime qualification.
Generator8 and existing Node3 entrypoints require fresh guarded execution.

Evidence packaging C2/I4/D4/Impact4=14/P1 may create one receipt plus exact-case
companion and update existing module/test memory. Retain raw-vs-Git hash domains,
chronology, commands and explicit limits; no raw logs/credentials. Exact existing
known-metadata rebinding is separately14/P1 and requires independent review
before ledger mutation. Unknown findings are held, never blanket-exempted.

## Derived source closure qualification — 2026-10-25

Pre-edit WSP15 allocation16/P0 in the numeric plan permits exactly one required
private arithmetic member. Runtime1470->1471; the existing explicit Node boundary
now accepts1471 and rejects1472. The old boundary oracle first failed its
1470 expected-count assertion on actual1471, before calling the validator.
That RED is an oracle-count mismatch, not evidence of old-validator execution. All328KiB manifest,2MiB/source and32MiB total caps remain unchanged.
Only token_economics.py's existing LF digest changes, plus _token_numeric.py.
The alignment test owner is outside runtime membership: an initial parent
measurement assertion wrongly expected its digest, before any pins changed.

Canonical write/check, all8 existing generator cases and3 existing Node
compatibility/preflight/blocked-recovery entrypoints pass. Existing Python pin
and JS pin advance together. All1614 evidence hashes stay stable after deliberate
write/cap edits; zero instrumented Python/Node network or dotenv attempts.
No generator/source-discovery algorithm, runtime authority, dependency or API
change. Evidence count1614 differs from actual1471 runtime members.

Exact commands, IDs, timings and source maps are external under
foundups-numeric-source-closure-f3jex_4s and in the numeric portable receipt.
Known38 metadata findings are proposed, pending independent review:37 sources/
contexts unchanged and1 known arithmetic-source SHA256 value changed. No blanket
rule/path exemption, unknown finding approval, OS isolation, installed-runtime
promotion, real chain effect or additional economic coverage follows.

## Parent independent acceptance — 2026-10-25

Independent review rehashes all1471 staged normalized sources, both pins and
fixed byte caps. Exactly38 known generator metadata bindings are accepted:
37 sources/contexts unchanged;1 token_economics source SHA256 value matches the
actual tested arithmetic bytes. Append only those38,1988->2026; preserve every
old binding. No unknown finding, scanner rule/path or GitGuardian exemption.
Generation's1613->1614 evidence-domain growth has unchanged intersection hashes;
final check/tests/Node1614 maps are stable. Old boundary RED is an expected-count
assertion before validator invocation, not old-validator execution proof.
Fresh hosted scans/CI, dedicated PR and main readback remain required.
Independent report rawSHA256:
dfc1b1093eb982f11d5e6ebb8b97cea82037e9fb7203946e231dee6bf8da22c2.
