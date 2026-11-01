# FoundUps blockchain reconciliation and security decision — 2026-10-31

## Allocation delivery and stored Chroma security hold — 2026-11-01

[PR2290](https://github.com/FOUNDUPS/Foundups-Agent/pull/2290) delivered allocation
source at `5d9f91346b75f4ae330aa64dbf737e766106d6da`, candidate-identical tree
`7fdbb0fcda2fa25b6fe5edca3631ce09afd2663b`: 40 PR/21 main checks and 20 C/O blob
bindings pass. Exactly 17,227 untracked pathnames were preserved at reconciliation,
without content hashes or a whole-interval claim; all 502 frozen evidence files
were independently C/O hash-verified. Delivery report SHA256:
`0b73f3618f876af9e7061cbd2f4943f76b582ffe8f9105aafc9e856214fba86d`.
The [allocation receipt](receipts/FOUNDUPS_ALLOCATION_PREFLIGHT_20261101.json) retains
its sealed prepublication scope; later delivery does not rewrite it.

The dependency snapshot records 44 open alerts, including critical ChromaDB
[UPDATE_COLLECTION](https://github.com/advisories/GHSA-36p7-vc44-83pf) and
[pre-auth collection](https://github.com/advisories/GHSA-f4j7-r4q5-qw2c) advisories.
Both include pinned/metadata-observed 1.5.5 and list no patched version at review.
[Issue 6717](https://github.com/chroma-core/chroma/issues/6717) separately reports
client-side exposure independent of server language; repository source review
confirms local config/schema constructor paths. No local compromise, blockchain
hack or AI participation is established.

Dated delivery correction: [PR2291](https://github.com/FOUNDUPS/Foundups-Agent/pull/2291)
merged at `424e6863b19c9353a296e0cc837e3f30eaa428fd`, exact reviewed tree,
with 23 PR/21 main checks successful. Independent readback verifies 28 delivered
C/O files, 17,551 preserved PC pathnames and 10,051 evidence-file copies; these
are separate scopes, not a content audit of all unrelated PC paths. PC record:
`outputs/blockchain-holo-admission-20261101-db203f83/EXECUTION_REPORT.md`, SHA256
`cdcf19ff9721f80f8504dec6c0523571d2cb4e5d7147410553cf207106ac8246`.
The [guard contract](../../holo_index/INTERFACE.md#stored-chroma-settings-admission--2026-11-01) and [test history](../../holo_index/tests/TestModLog.md#stored-settings-local-qualification--2026-11-01)
retain failed native runs and explicit sparse/fixture corrections. These selected
callers do not fix every SDK consumer or upstream advisory. Publication/PC pending
notes below are historical; persistent maintenance remains HOLD, with exact
runtime/current-store qualification unproved. No fresh semantic CURRENT claim follows.

## Hourly queue readiness candidate — 2026-11-01

The existing breaker owns this 14/P1 class-B B09 slice: first nonempty release,
FIFO and minimum-one/count math stay; later dequeues require 3,600 monotonic seconds.
Native slices precede final time observation and queue/timer publication. No catch-up,
empty/emergency timer advance or drain/refill reset is allowed. Private timer state
is excluded from constructor/repr/equality but appears additively in `asdict`.
Actual baseline 35 passes; frozen desired RED is 12 pass/7 fail. Focused candidate
passes the combined 54; independent five and source review accept the frozen
scope. Code/method 324/28 lines fit 330/35. Promoted owner 240 lines preserves
old prefix/oracles; broader 1,209 passes with the same three SSE HTTP deselections,
zero failures/errors/skips/guards and 174 stable snapshots. New 19 are within that
run, five held-outs outside it; do not add overlapping counts. No fresh 240-tick
trace ran, and older traces did not exercise positive queue release.
Package eight Python/three Node pass with 1,481 members, only the breaker hash
changed, unchanged caps and 35 bytes CRLF headroom. Registry was not run locally;
no instrumented zero-effects or native-runtime claim follows. Security/publication remain pending.
Only native serialized-instance readiness is claimed. Logging can fail after a
committed dequeue; successful return, lost-result recovery, concurrency, restart,
funded payment and authenticated unfreeze are not supplied. Historical A12 failure
below stays evidence; this partial candidate does not close full A12 or broad B09.
B03 C/D units/thresholds/liabilities/issuance, B05 funding and separate custody
remain unresolved or blocked; no TestNet/production activation follows.

## Allocation numeric preflight and delivered-source checkpoint — 2026-11-01

PR2288 merged at `d9279817b45d9339d62bccfb0fa6965a305c688d`. Concurrent
PR2289 advanced main to `de6917e59c68cc2036622741455737366242bde7` without
changing the 174 simulator/FAM Python source snapshots, nine Holo contracts or
1,481 runtime members. Fresh de6917 qualification passes 21 source checks,
including all five required app-15368 contexts; primary/control source readback
passes separately, with unrelated PC files preserved. Separate control and actual
primary semantic queries are CURRENT with no index gap at de6917: committed-head evidence
only; lexical bundles remain UNKNOWN with an index gap and exact installed/native runtime
closure remains false. Reserve source delivery is complete. Historical d927 has
21 source successes and a separate failed
Dependabot frontend-maintenance job; retain that failure and the original ENOSPC
attempt/successful single retry. Earlier sealed quote receipts remain unchanged.

The allocation candidate implements **class B, WSP15 18/P0 (4/5/5/4)** in existing owners:
`AgentExecutionWallet.receive_allocation`, `HumanUPSAccount.allocate_to_agent`,
`TokenEconomicsEngine.human_allocates_to_agent` and `SwarmFoundUp.register_agent`.
Unsupported/non-finite/negative operands and prospective overflow are rejected
before participating numeric, installed-policy or MetaGPT registration changes.
Composite source is mandatory: None is invalid source state, not an absence or
unfunded-credit sentinel. Standalone wallet credit remains separate bookkeeping.
Numeric scalar hooks do not execute. Accepted built-in int/float arithmetic,
legacy lookup/allocator precedence and valid insufficient funding behavior,
including MetaGPT zero-wallet registration, are preserved.

Composite human/engine/MetaGPT allocation omits the previous standalone wallet
receipt INFO log, as allowed before implementation. Logging is neither settlement
evidence nor rollback authority.

This is native-state admission and precommit preparation under a trusted
serialized host. It does not supply arbitrary receiver/property-hook rollback,
postcommit logging rollback, concurrency isolation, durable reservations, B05
funded conservation, a global UPS unit or full A02 authority protection. B03 class
C/D and the signer/activation gates remain open. It adds no runtime owner or
resource-cap authority.

Frozen pre-edit evidence remains separate: existing baseline 311 passes; desired
171 cases have 48 passes/123 failures. The delivered de6917 source/PC/Holo
checkpoint does not qualify this allocation candidate.

- Independent candidate acceptance: The 171 frozen cases plus 25 independent held-outs passed: 196 cases. The 311
  original regressions passed with exact prior case IDs. Zero errors, skips or guard
  denials were recorded; 174 simulator/FAM Python source snapshots remained stable.
  Independent source/AST/budget review reports no material findings within the
  frozen native-state contract.
  Source ceilings are met: numeric helper 176/185 lines, token economics
  1,392/1,393 and MetaGPT 639/643; unrelated source ASTs are preserved.
- The 171 frozen controls are promoted into existing
  `test_allocation_and_treasury_runtime.py` (336 lines), preserving the original
  prefix/AST and frozen non-docstring AST. Its actual 173-case subset is verified
  within the broad run below.
- Promoted/broader regressions: The broad run passed 1,190 cases: the prior 1,019 plus 171 promoted controls.
  The promoted owner contributes 173 cases, derived from that broad result rather
  than another run. The same three SSE HTTP cases were deselected; zero failures,
  errors, skips or guard denials; 174 source snapshots remained stable. The 25
  external held-outs are outside 1,190, and these overlapping scopes are not added.
- Controlled finite-profile parity: Fresh de6917 baseline and candidate controlled 240-tick traces match raw bytes,
  SHA256 `672d12c9d8fb6286624ea892fb3a5d0315c475ee45f8c83c9a271ba4328f0ff1`.
  This finite process/profile observation is not seed-only or whole-model proof.
- Canonical packaging: Canonical package qualification passed eight Python cases and three Node
  entrypoints; registry 1,800/260 is unchanged. The same 1,481 ordered members remain,
  with only the numeric-helper and token-economics runtime hashes changed; MetaGPT
  is outside the closure. Canonical digest is
  `7d35294b980d4f4e329edf003e7e96337e3a6413c288764e2f07d5a465c3980e`.
  Manifest LF/CRLF sizes are 334,850/337,885 bytes under the unchanged 337,920 cap,
  leaving 35 bytes; individual 2 MiB and total 32 MiB caps are unchanged. This
  qualifies staged package bytes, not hosted checks, installed closure or activation.
  No runtime member, accepted-count or byte-cap increase was introduced.
- Fresh security/publication/main/PC/Holo: Pending at this prepublication checkpoint: fresh immutable security gate, protected
  PR, resulting-main checks and new-source PC/Holo qualification; later observations
  belong in separately dated delivery evidence.

The [allocation preflight receipt](receipts/FOUNDUPS_ALLOCATION_PREFLIGHT_20261101.json)
binds source, corrected precode ceilings, test/trace/package evidence and portable
held-out reproduction sources. The old verifier ceiling typo remains preserved
in its original report and corrected by a separate addendum; no budget increased.

This dated reserve source-delivery checkpoint closes its corresponding older
pending notes below. Candidate publication/main/PC/Holo and all economic
activation gates remain separate.

## Concurrent-main quote reconciliation — 2026-11-01

This dated prepublication qualification tested the uncommitted merge overlay of owned
`b0b112572f75c1e12b69305b6753b1a2f346f2ae` and upstream PR2287 main
`b3e0465c237bd53bfa473195720c2c5e55a1882a`. It preserves the upstream YouTube
work, both inherited metadata sets and the exact quote source/test blobs.
No blockchain economic source changes are introduced by reconciliation.
The original 4c96-based qualification and 1,478-member package below remain
dated pre-integration evidence. Its sealed quote receipt is unchanged; the
[separate reconciliation receipt](receipts/FOUNDUPS_RESERVE_QUOTE_RECONCILIATION_20261101.json)
binds the new scope without relabeling prior runs.

Actual combined-overlay regression passes 1,019 cases with the same three SSE
HTTP deselections, zero failures/errors/skips/guard denials and 174 unchanged
simulator/FAM Python source snapshots, including tests. One fresh controlled
candidate trace matches the retained fb58 reference byte-for-byte; the reference
was not rerun. This is one repeated finite process/hash-seed scenario, not a new
distinct regression case, seed-only portability or a future-commit/main result.

The inherited runtime closure has 1,481 paths, including three YouTube owners;
only the reserve hash differs from upstream. Fresh canonical check, eight Python
cases, three Node entrypoints and the 1,800-owner/260-quarantine registry check
pass. The original raw-byte preflight stopped on CRLF versus staged LF bytes;
canonical generation materialized LF; root verified exact normalized/index
equality and retained the failure. Normal checks then passed with unchanged
guards and no extra generator write.
Manifest LF/CRLF sizes are 334,850/337,885 bytes under the unchanged 337,920 cap:
only 35 bytes of Windows headroom remain. Individual 2 MiB and total 32 MiB source
caps remain. New owners or source growth need separate resource admission.

Protected publication, fresh security qualification, resulting-main and actual
PC/Holo readback remain separate gates. No global unit decision, quote consumer,
authenticated reserve, custody, funding, token issuance or chain activation follows.

## Reserve quote observation and B02 delivery — 2026-11-01

[PR2285](https://github.com/FOUNDUPS/Foundups-Agent/pull/2285) delivered B02/A07
at `fb58cd530d7b6887ce6218af282cb6ee7382ded5`: all 23 PR checks and 21
resulting-main checks passed. Primary-PC source/preservation and exact-source
Holo qualification passed separately. Its semantic receipt qualified committed
fb58, CURRENT/no gap; its lexical bundle retained UNKNOWN/gaptrue. This closes
the earlier B02 publication-pending state below, without changing sealed records
or qualifying a newer source, installed runtime or live monetary service.

The next bounded prerequisite is **class A representation, WSP15 16/P0
(3/4/5/4)**, on the docs-only successor base
`4c96d6b17429226248c3a82de5544262e773c41e`. Existing `btc_reserve.py` adds
`snapshot_simulator_quote(reserve, *, context_id, tick)` and an immutable,
11-field record. `decimal_view_v1` keeps integers exact and interprets finite
floats through their canonical decimal spelling, then exact rational arithmetic.
This opt-in view does not recover historical float precision or change any
legacy calculation, default consumer, fee, supply or chain behavior.

The [interface](../../modules/foundups/simulator/INTERFACE.md#opt-in-simulator-reserve-quote-observation--2026-11-01)
defines fields, work limits, branches and the domain-separated content digest.
Context, tick, digest and public record construction confer no authentication,
currentness, unique consumption, funded backing or settlement authority. The host
must serialize observation with source writes; concurrent multiscalar capture is
not atomic. Zero circulation is explicitly notional. Zero BTC with outstanding
UPS rejects only in this new API; both differing legacy views remain unchanged.

Frozen historical acceptance produced 7 original passes and 89 desired failures
before implementation. The independently reviewed source passes 113 cases:
those 96 cases plus 17 additional held-outs, with unchanged source snapshots and
zero effect-guard denials. Review found no material defect within the selected
contract. The promoted existing owner passes 96 cases; the broader simulator
passes 1,019 with the same three named SSE HTTP cases deselected. All GREEN selections
have zero failures/errors/skips/guard denials and 174 unchanged simulator/FAM
Python source snapshots, including tests; these are not the runtime closure.
These scopes overlap. Python guards are not OS confinement. The [quote receipt](receipts/FOUNDUPS_RESERVE_QUOTE_OBSERVATION_20261101.json)
records the actual source-bound evidence and open publication gates.

Canonical packaging preserves all 1,478 runtime paths and changes only the reserve
owner's hash. Eight Python generator/index cases, three Node entrypoints and the
unchanged 1,794-owner/260-quarantine registry check pass. Manifest 330 KiB,
individual-source 2 MiB and total-source 32 MiB caps are unchanged. These checks
bind the tested source and staged package entries, not an installed runtime or
a future commit. Protected publication, resulting-main and new-source PC/Holo
qualification remain pending; chain activation remains blocked.

A fresh controlled profile ran the clean fb58 reference, whose 174 simulator/FAM
Python source hashes equal the docs-only 4c96 base, and two candidate processes. Complete trace
bytes match SHA256 `672d12c9d8fb6286624ea892fb3a5d0315c475ee45f8c83c9a271ba4328f0ff1`:
240 ticks, six FoundUps, 214 paid simulated tasks and 24 epochs. Python 3.12.10,
`-P -s` and explicit `PYTHONHASHSEED=710007` bind this finite profile. No monetary
fields were normalized. The actual reference ran fb58, not 4c96. This verifies no
observed change to that default path; seed-only portability, all model states,
economic correctness and live backing remain unproved. The new observer is unused
by existing model/fee consumers. These are repeated scenario runs, not additional
distinct regression cases.

B03's **19/P0 class C/D unit and issuance decision remains unresolved**. This
representation prerequisite does not ratify the one-satoshi/1000-satoshi conflict
or authorize changed economics. Future class C transitions need their own
versioned simulator decision and independent acceptance. Durable funded limits,
authentic source facts, custody, chain parity and activation remain blocked.

## Replay-safe epoch settlement and AI threat update — 2026-11-01

**Historical B02 implementation checkpoint; delivered above.** Source baseline: `24cc4aa2971b05ff8b53f76d157145da4134ed5c`.
[PR2281](https://github.com/FOUNDUPS/Foundups-Agent/pull/2281) delivered B01/A10
wallet-policy isolation. All 24 final PR checks and 22 resulting-main checks
passed; the primary PC checkout was fast-forwarded with its existing untracked
work preserved. This supersedes the older active-sprint, baseline and
publication-pending status below; sealed observations retain their source scope.
Neither publication nor simulation qualifies a live monetary service.

**B02/A07, class B, WSP15 18/P0 (4/5/5/4).** At the original 24cc baseline,
the pool credited participants, updated staker hurdles, accumulated the fund
and paid drip before Mesa asked the epoch ledger to deduplicate evidence. A ledger retry check
alone therefore cannot prevent a second economic payment. Reuse these owners,
prepare their complete effects before publication, and retain one detached
receipt per distributor/epoch in the process lifetime. Existing valid pool
formulas, numeric conventions and first-hurdle sequencing remain the reference.
Shared staker positions must preserve the original participant iteration order.

The independent baseline run passed 154 cases, including an actual non-AI
240-tick Mesa run with seed 710007, three founders and eight user agents. It
created FoundUps, submitted and verified work, paid tasks and produced a valid
epoch chain. Its earlier harness failures remain recorded: two rejected default
repository-database writes and one incorrect inspection attribute. The corrected
test configuration only directs default FAM storage to separate scratch paths;
real economic and authorization implementations remain in use. Python effect
guards are not OS confinement. This baseline does not establish the repair.

Independent acceptance froze 40 cases before implementation: 2 passed and 38
failed on the baseline. All 40 then passed, together with 16 separate held-outs
covering shared-ledger races, forged receipts, failed preparation and observers.
Root review identified one callback return-value regression; its separate test
first failed, then passed after a one-line correction. The corrected source
passes all 57 independent cases with no failures, errors, skips or guard denials.
These checks qualify selected **VERIFIED_SIMULATED** process-local effects,
not the complete A07 durable or chain-level attack family.

The initial seeded reruns passed their individual smoke assertions but produced
different economic totals, including between two candidate runs. They are not
parity evidence. Source inspection found process-randomized `hash()` in founder
naming and rating potential, process-global random state and a shared rating
engine. `SimulatorConfig.seed` alone therefore does not establish fresh-process
reproducibility. Qualification must bind the full process configuration and
initial state; no monetary difference may be removed as volatile metadata.

The separately frozen controlled profile uses a fresh process, Python3.12.10,
`-P -s`, an explicitly constructed credential-free environment and
`PYTHONHASHSEED=710007`. The original audit guards and real scratch-state owners
remain unchanged; Python's `-I` would ignore that hash-seed variable. One original
24cc baseline and two corrected-candidate runs produced byte-identical recorded
traces: SHA256 `672d12c9d8fb6286624ea892fb3a5d0315c475ee45f8c83c9a271ba4328f0ff1`.
Each ran 240 ticks, created six FoundUps, paid 214 simulated tasks and recorded
24 epochs. Recorded final stakes, F_i outstanding and fund values also match.
This qualifies that exact profile and recorded trace; it does not fix model-wide
global RNG/singleton ownership or prove seed-only portability. A model-owned RNG,
stable identity hashing and independently isolated runs need a separate versioned
simulation change before expanding economic acceptance.

The promoted three-owner regression passes 192 cases, retaining every old test
AST and matching the frozen new oracles after helper-name disambiguation. The
broader simulator run passes 930 cases with the same three explicitly named SSE
HTTP cases deselected, zero failures/errors/skips and zero effect-guard denials.
These overlapping counts are not added. The [epoch security receipt](receipts/FOUNDUPS_EPOCH_REPLAY_SECURITY_20261101.json)
binds sources, actual runs, rejected probes and remaining activation boundaries.
Package, hosted and resulting-main evidence is separate from these local results.

Canonical package generation adds only `_mesa_epoch.py`: all 1,477 earlier
members remain, and the three edited runtime owners receive new hashes. The
actual old validator refused the 1,478-member closure before the reviewed count
update; the new boundary accepts 1,478 and rejects 1,479. Eight existing Python
generator/index cases and three Node consumer entrypoints pass. The 330KiB
manifest, 2MiB/source and 32MiB total caps are unchanged; LF/CRLF manifest sizes
are 334,222/337,251 bytes. The canonical test registry remains 1,794 owners.
Publication was pending at this checkpoint; the dated delivery addendum above
records its completion. Live economic deployment remains **BLOCKED**.

### AI-exposed financial attack surfaces

Primary sources were checked on 2026-11-01. AI can reduce the work required to
discover and exploit a defect; that does not establish a break of cryptography.
Anthropic's [December2025 SCONE study](https://www.anthropic.com/research/smart-contracts)
and [May2026 update](https://www.anthropic.com/research/exploit-evals) demonstrate
exploit generation in local blockchain simulations. Their simulated proceeds
are not live theft, and their EVM results are not FoundUps or Algorand findings.

Agents can also be redirected through information they are allowed to read.
Invariant's [GitHub MCP demonstration](https://invariantlabs.ai/blog/mcp-github-vulnerability)
and [tool-poisoning experiments](https://invariantlabs.ai/blog/mcp-security-notification-tool-poisoning-attacks)
show repository and tool-metadata risks in controlled settings.
[GitHub's VS Code assessment](https://github.blog/security/vulnerability-research/safeguarding-vs-code-against-prompt-injections/)
documents addressed tool/file-action bypasses.
[OpenAI's September2026 self-replication report](https://alignment.openai.com/misalignment-reports/self-replicating-prompt-injections-exist)
observed no impact outside simulated tool calls. None is evidence of a FoundUps
incident or confirmed blockchain theft.

Repository content, dependencies, tool metadata/results, RPC facts, memory and
model-written PoB explanations remain untrusted inputs. A claimed approval or
urgent recovery instruction cannot grant spending authority. Host qualification
requires pinned dependencies, bounded I/O and custody outside candidate code.
FAM's `CallerAuthorization` is a trusted-host injection seam, not an issuer or
a same-process sandbox; different agent IDs do not prove independent control.
[MCP security guidance](https://modelcontextprotocol.io/docs/2026-07-28/tutorials/security/security_best_practices)
requires audience separation and rejects token passthrough. This is a requirement
for host integration, not evidence that FoundUps has completed it.

Deterministic controls must constrain effects even if hostile text redirects an
agent; [OpenAI's security guidance](https://openai.com/index/designing-agents-to-resist-prompt-injection/)
supports this separation. The [Bybit/Safe investigation](https://www.sygnia.co/blog/sygnia-investigation-bybit-hack/)
illustrates shared signing-presentation compromise, without establishing AI
causation. Signers must independently decode the exact transaction, bind current
scoped approval and deny unapproved authority changes. Post-quantum signatures
cannot repair poisoned construction, accounting, authorization or recovery.

| Existing attack / status at the baseline | Required next evidence in the existing roadmap |
| --- | --- |
| A01/A02: local policy exists; funded aggregate reservations do not | B05/B09: pending and ambiguous exposure across agent, controller, FoundUp and system windows; coordinated small calls stay within funded limits. |
| A03/A04: unsigned Algorand field restrictions exist; monetary signer missing | B08: separate custody/control domains, independently decoded effects, one-use approvals, denied rekey/close/delegation and independently observed finality. |
| A05/A06: local proof/task and type checks exist; independent facts and release authority missing | B03/B06: authentic work/maturity evidence, unique consumption and combined release/supply bounds; names and literal `True` are insufficient. |
| A07: delivered B02 qualifies process-local pool/ledger/Mesa retries; restart, funded and chain replay remain missing | B05/B08: durable funded admission and chain-level no-effect/replay tests; no whole outer-cycle guarantee. |
| A08: matching simulated; self-trade gap remains | B11: funded two-sided reservations, related-controller/Sybil controls, exact settlement/fees and cancellation. |
| A09: external venue/bridge unqualified | Keep disabled; require separate asset, venue and bridge admission plus independent chain restrictions. |
| A10: B01 detaches caller policy; trusted-host replacement remains | B08/B09: authenticated versioned policy and approvals outside candidate-controlled code; stale or self-granted authority rejected. |
| A11: numeric checks do not authenticate reserve backing | B05/B09: authentic fresh backing and liabilities; fabricated plausible inputs cannot increase capacity. |
| A12: hourly readiness has focused 54, independent five/source, broader and package acceptance; security/delivery pending | B09: retain native-instance limits; authenticated recovery, safe reconciliation and independent freeze/unfreeze authority remain absent. |

These are linked threat requirements, not passed attack tests. The current
distribution layer cannot establish restart recovery, cross-process exclusion,
funded Treasury conservation or chain finality. Algorand's
[sender/lease exclusion](https://dev.algorand.co/concepts/transactions/leases/)
lasts only for its validity window; it is not lifetime business idempotency or
authority to issue a replacement payment after a timeout. The dated Binance,
bridge and quantum-risk evidence below retains its stated uncertainties.

## Current sprint and blockchain roadmap — 2026-11-01

**Historical B01 checkpoint.** Current execution status is in the A07 addendum
above. The ordered B01–B11 work packets below still own the remaining gates.

This dated addendum supersedes planning/publication status below, not the sealed
October 31 observations. PR2279 merged at `9925eb65e08b3602ad11ee32537bebf0d94bca32`;
its 41 PR checks and 22 resulting-main checks passed. PR2210 and PR2261 were
closed as incorporated/superseded, with their original history retained.
The November 1 research baseline is `43b3b66cce8a01f28fb08577a9db84f731e50455`.
Its intervening change concerns YUMORI documentation. Neither source publication
nor a passing simulator authorizes chain activation.

### Concurrent main reconciliation

During final PR2281 checks, another session landed RSI/Vote PR2282 at
`12adf3e4824645a21d93d10339ac4ccfa304e723`. The wallet implementation and its
qualified tests do not overlap. Both root-log additions and the union of exact
reviewed security records are preserved, along with all Vote/CI changes. The
combined local policy/documentation/Vote selection passes 404 cases with no
failures, errors, skips or guard denials. Previous 41 passing hosted checks belong
to `6bc295c8f5242c808f30985334d4e5af7730d9fe`; combined-head hosted
qualification and resulting-main checks are required separately.

### The economy being built

The simulator already includes tokenomics. In
[`FoundUpTokenPool`](../../modules/foundups/simulator/economics/token_economics.py),
the intended per-FoundUp total is 21 million F_i; adoption increases the released
ceiling within that total. Remaining work-mint capacity is released ceiling minus
already mined supply. The pool of available rewards can therefore grow without
raising the total cap. It is useful-work allocation, not Bitcoin proof-of-work.

This is only **VERIFIED_SIMULATED** behavior. The total-supply field is mutable,
work inputs are not authenticated, and UPS-backed staked F_i outstanding is a
separate counter without a demonstrated combined cap. Product milestones
(PoC/Prototype/MVP), adoption scores, and governance tiers are distinct inputs;
none is mint authority. Whether mined and staked F_i share the same issuance
ceiling remains a class D conflict. No second asset or new release schedule is
silently introduced to resolve it.

Historical WSP26§4.4.1 no-breaker, implementation and 100%-reserve assertions
are not accepted proof of funded solvency or security. Fees (including 11% mined
and 5% staked paths versus 2–5% wording),1-sat versus 1000-sat units, distribution
denominators and reserve/exit rights remain blocked conflicts; no rule is chosen.

The current [FAM launch orchestrator](../../modules/foundups/agent_market/src/orchestrator.py)
optionally creates a token through a factory. The implemented default is a
clearly identified mock. Mock Treasury credit of the requested supply is not
circulation, vested eligibility, a live ASA, or proof that every catalog project
has its own token. Generic TokenTerms do not enforce a universal 21M policy.
The simulator's configured verifier/treasury identities and auto-approved work
are also not production collective consensus. CABR sizes validated Treasury flow;
it never independently mints UPS.

### Typed catalog snapshot, not a token inventory

The [typed registry](../../modules/foundups/foundup_registry.json) contains 19
entries at 43b3:7 foundups,5 skeleton candidates,3 infrastructure services,
one platform layer, one simulator and 2 external foundups. Its five public
projections are directory metadata; no 115-project source list was established
by this bounded audit. The registry does not exhaust every project or nomination.

| Typed ID / name | Registry type | Declared stage / PoC | Token metadata | Public projection |
| --- | --- | --- | --- | --- |
| `gotjunk_001` / GotJunk | `foundup` | proto / proto | `EXISTS` | yes |
| `kosei` / Kosei AI Systems | `foundup` | incubating / poc | `EXISTS` | yes |
| `voteballots` / Vote/Ballots | `skeleton_candidate` | incubating / idea | `EXISTS` | no |
| `trade` / Trade | `skeleton_candidate` | incubating / idea | `EXISTS` | no |
| `magadoom_001` / MAGADOOM | `foundup` | incubating / poc | `EXISTS` | no |
| `antifafm_001` / antifaFM | `foundup` | proto / proto | `EXISTS` | no |
| `pfmall` / p.fMALL | `platform_layer` | n/a / not_applicable | `NOT_APPLICABLE` | no |
| `agent_market` / FAM - FoundUp Agent Market | `infra_service` | n/a / not_applicable | `NOT_APPLICABLE` | no |
| `move2japan` / Move2Japan | `foundup` | incubating / poc | `TOKEN_DEFERRED` | yes |
| `simulator` / Economics Simulator | `tool_simulator` | n/a / not_applicable | `NOT_APPLICABLE` | no |
| `social_twin` / Social Twin | `infra_service` | n/a / poc | `NOT_APPLICABLE` | no |
| `autopost` / AutoPost | `external_foundup` | incubating / poc | `TOKEN_DEFERRED` | no |
| `pqn_portal` / PQN Portal | `skeleton_candidate` | incubating / poc | `TOKEN_DEFERRED` | no |
| `science_swarm_hub` / Science Swarm Hub | `external_foundup` | proto / proto | `TOKEN_DEFERRED` | no |
| `holoindex_prod_01` / HoloIndex | `infra_service` | incubating / poc | `TOKEN_DEFERRED` | yes |
| `esingularity_001` / eSingularity | `foundup` | proto / proto | `TOKEN_DEFERRED` | yes |
| `shield` / Shield | `foundup` | incubating / idea | `TOKEN_DEFERRED` | no |
| `detect_ai` / AmIBot | `skeleton_candidate` | incubating / idea | `TOKEN_DEFERRED` | no |
| `kids_episodes` / Kids Episodes | `skeleton_candidate` | incubating / idea | `TOKEN_DEFERRED` | no |

`EXISTS` above is a registry declaration, not verified token issuance. No reviewed
row records an authenticated chain/genesis/asset-ID and confirmed-issuance mapping.
The 14 tracked manifests include 12 registry references; the 14 video entries also
contain creators, brands and aliases. They are not14 extra admitted ventures.
Repository/controller proof, issuer rights, live readiness and catalog promotion
remain separate gates; no row, ticker or asset is created by this table.

### First sprint: isolate agent spending policy

**A10 / class B / WSP15 17/P0 (C3/I5/D5/Impact4).** At the pinned baseline, the wallet stores a
caller-owned policy dictionary. A later edit to its nested allowed-operation
list changes spending permission. Repair this existing owner before adding a
signer: install a detached policy snapshot, expose a read-only view, validate
policy before funding effects, and retain explicit trusted-host replacement.

Frozen acceptance covers constructor/direct replacement, direct allocation and
engine allocation; original/nested mutation; invalid policy with no debit or
replacement; insufficient funding; valid host rebinding; exact integer limits;
and existing empty/omitted-policy behavior. Valid fees and the existing numeric
normalization oracle remain unchanged. The host replacement API remains trusted:
this is not authenticated governance, a same-process sandbox, or a live wallet.
Serialization through dataclasses.asdict is outside the qualified interface.

The alternatives were an epoch cache, immediate token issuance, and a new wallet
framework. An epoch cache alone would miss side effects and failure recovery;
issuance lacks prerequisite authority/funding; a new framework duplicates existing
owners. A10 is the smallest independent security layer. A07 follows with complete
effect accounting rather than a ledger-only patch. Candidate acceptance supplied by the root records 311 passing cases (235 existing
plus 76 wallet-policy cases), with zero failures, skips or recorded guard denials. The
independent 13-case run also passes, with 173 source snapshots unchanged. These
scopes are not summed; the 235 baseline and 76-case RED (6 pass/70 fail) remain.
See the [wallet-policy receipt](receipts/FOUNDUPS_WALLET_POLICY_SECURITY_20261101.json);
Connected simulator/documentation qualification passes 489 cases with no
failures, errors, skips or guard denials. These overlap the focused selection.
Eight manifest-generator tests and three Node consumer entrypoints also pass.
Final publication and resulting-main verification remain pending.

Trusted host policy replacement remains available, and omitted limits retain
their existing unbounded semantics. This fixes hostile caller aliases, not
malicious host replacement, authenticated policy governance, aggregate withdrawals
or funded conservation. A07 remains the next complete-effect accounting layer.

### Ordered work packets and acceptance gates

These are planning assignments to 0102 roles under WSP97, not signed runtime
orders or a claim that background workers have been activated. Each packet gets
fresh source retrieval, frozen tests, a separate implementer/verifier, and a
reviewable receipt before promotion. No wrapper or new scheduler is required.

| Order / packet | Existing owner / assigned 0102 role | WSP / class / MPS | Exit evidence |
| --- | --- | --- | --- |
| B01 policy isolation | simulator token_economics / security worker; economics verifier | 26/50/97, B, 17/P0 | Caller aliases cannot expand permission; rejection has no funding effects; valid regressions and held-outs pass. |
| B02 epoch effects once | pool_distribution + epoch_ledger + Mesa callers / accounting worker | 26/29/97, B, 18/P0 (4/5/5/4) | Exact retries return detached prior result; conflicting context rejects; prepare participant/fund/drip/hurdle and ledger effects before scoped publication. Ordinary preparation failures leave participating state unchanged; qualify concurrency separately. No process-death rollback or durable recovery claim. |
| B03 monetary units and issuance decision | simulator source matrix + tokenomics / economic architect | 26/27/29/100, C/D, 19/P0 (4/5/5/5) | Versioned asset units, integer scale/rounding/residuals, mined/staked cap and release policy; seeded boundary/conservation tests; independent acceptance before governing mirrors and chain port. |
| B04 catalog-to-asset identity | foundup_registry + manifests + FAM registry/intake / catalog worker | 26/58/109, A/B, 15/P1 (3/4/4/4) | Joined read-only coverage report; stable project IDs; nomination distinct from verified repository control and issuer grant; duplicate/repository-transfer/expired-claim controls. No ticker treated as chain evidence. |
| B05 funded allocation and limits | FAM persistent payout/intent + existing simulator Treasury/FX / accounting worker | 26/29/97, B, 19/P0 (4/5/5/5) | Atomic funded reservations count pending/ambiguous operations across wallet, agent, controlling identity, FoundUp and system windows; unique proof consumption; crash/replay reconciliation; integer conservation. |
| B06 approved release and consensus | FAM verifier + simulator work/maturity/release owners / issuance worker | 26/27/29/100, B/C, 19/P0 (4/5/5/5) | Authenticated independent work/maturity evidence; no self-verification or Sybil quorum; per-FoundUp cumulative issuance never exceeds the approved released/total bounds across all lanes. Depends on B03/B05. |
| B07 intent-to-unsigned consumer | FAM current-intent API + Algorand codec / transport worker | 11/26/97, A/B, 15/P1 (3/4/4/4) | Current host authority before/after I/O; admitted producer; independent network/account/asset/fee/round facts; existing-only revalidation; no implicit reissue or signing. Preserve existing bounded JSON/wire contracts. |
| B08 custody and constrained signer | existing platform integration boundary / security architect and independent chain verifier | 26/71/97, B, 20/P0 (5/5/5/5) | Separate custody/control domains; exact-effect decode; scoped one-use authorization; algorithm/domain/encoding vectors; deny rekey/close/delegation/unknown groups; durable attempts; independently observed finality. Provider qualification and external audit required. |
| B09 freeze, monitoring and recovery | existing breaker/queue/FAM evidence owners / incident worker | 26/48/91/97, B, 19/P0 (4/5/5/5) | Coordinated small drains, oracle forgery, pending exposure and governance changes detected; authenticated freeze/recovery; ambiguous payment reconciliation; no queue release accelerated by repeated calls. |
| B10 one-project TestNet pilot, then inventory rollout | FAM token factory + Algorand + catalog / integration worker | 26/97/100/109, A/B, 17/P0 (4/5/4/4) | Separately authorized bounded pilot only after B03-B09; actual network/genesis, asset ID, issuer/privileged authorities, supply/decimals, opt-ins and confirmed transaction evidence; exact retries do not create a second token. Expand only to eligible verified projects. |
| B11 internal FX settlement | existing fi_orderbook + FAM settlement / exchange worker | 26/29/97, B/C, 19/P0 (4/5/5/5) | Funded two-sided reservations, exact settlement/fees, related-party/Sybil manipulation controls and cancellation/recovery. External DEX, bridge or wrapped assets require another simulator decision and security review. |

B02, B03 and B04 can prepare independently; dependency order still gates effects.
The original A01-A12 taxonomy remains the coverage map: B05/B09 cover A01/A02;
B08 covers A03/A04/A09; B06 covers A05/A06; B02/B05/B08 cover A07; B11 covers A08;
B01/B08/B09 cover A10; B05/B09 cover A11; B09 covers A12. A mock or missing hook
cannot be marked a passed attack. B01 alone does not close A10 governance risks.

### Custody research and decisions

Retain Algorand as the existing TestNet transport candidate, with Bitcoin reserve
custody a separate boundary. There is no connected FoundUps monetary signer to
certify. RedDog's existing Ed25519 governance signing is a different authority;
it must never be reused or described as the token wallet merely because an
algorithm name matches. No model, repository text, RPC response, GitHub badge,
or fee incentive grants spending or mint authority.

Bitcoin HD derivation separates addresses, not compromise domains. Shared seeds,
backups, signer hosts, administrator credentials or approval UIs can correlate
thousands of wallets. Threshold signatures only help when independent parties
independently validate the exact intended effect. Agent-facing tools should
submit typed bounded intents; key material and arbitrary signing APIs stay out
of the agent's environment. Normal reward capabilities deny privilege-changing
transactions; recovery is a separate independently approved capability.

The service shortlist is a qualification queue, not a selected production wallet:
[AWS KMS](https://docs.aws.amazon.com/kms/latest/developerguide/symm-asymm-choose-key-spec.html)
now documents Ed25519, with different RAW versus prehash modes. Exact Algorand
domain/message interoperability and restricted IAM/control-plane access still
need tests. [Google Cloud KMS](https://cloud.google.com/kms/docs/algorithms)
lists PureEdDSA Ed25519 in software; that does not prove a qualifying HSM mode.
Neither enumerated service algorithm list establishes support for Algorand's
Falcon f1 scheme; ML-DSA is not a substitute. SDK support does not establish
hardware custody, recovery support, or a safe FoundUps caller.

[Algorand's post-quantum account guidance](https://dev.algorand.co/concepts/accounts/post-quantum/)
distinguishes Falcon accounts, ordinary Ed25519 multisig, consensus and tooling.
Keep algorithm/network/compiler/runtime versions and migration/recovery tests
explicit. No claim of universal quantum protection or unhackability follows.
The initial deployment gate also includes the existing dependency exposure and
configuration review, including Chroma advisories; a source-only query or pinned
package is not evidence that every local service is safely configured.

The incident table below remains dated evidence. Binance's
[October 31 update](https://www.binance.com/en-AU/support/announcement/detail/1fdf1f61559c401da0435895ffcccb62)
reports 90% replenishment using company/insurance funds. Replenishment is not
recovery of stolen assets or a final forensic finding. The October 29 compromise
is corroborated by official disclosures; final mechanism and attribution remain
provisional. Direct detail requests sometimes redirect to the announcement index;
indexed official and locale-specific responses were retained with this limitation.
TRM's EIP-7702/signing-infrastructure analysis stays an investigator assessment,
not proof that FoundUps or Algorand uses that Ethereum delegation mechanism.

No real token creation, keys, funded transactions, bridge, runtime installation,
or blockchain deployment is authorized or performed by this research sprint.
**Readiness remains BLOCKED** until the applicable gates above are independently
qualified. Source publication and the ledger of remaining work remain separate.

### Retrieval repair and qualification

The initial owner query rejected a stale authority head. One governed existing
post-merge maintenance task completed for 43b3; it stopped both runtimes it
started. A separate source-bound query returned CURRENT with no index gap and
matching authority/workspace/generation. This qualifies the clean 43b3 reference,
not the edited candidate. Candidate work used explicit lexical bundles and direct
source inspection; noise and incomplete generic hits were resolved by exact owner
documents and source. No raw reindex or authority-reset workaround was used.

### Sources and acceptance boundary

The catalog and economic audits are source-bound to43b3; the portable receipt
retains their hashes and independent attribution. Custody corrections also use
[BIP32](https://bips.dev/32/), [NIST threshold guidance](https://csrc.nist.gov/projects/threshold-cryptography)
and [Safe transaction verification](https://help.safe.global/articles/4369997924-how-to-verify-safewallet-transactions-on-a-hardware-wallet).
These explain common-mode risk; they do not certify any FoundUps deployment.

## Publication and simulator authority addendum — 2026-10-31

012 subsequently authorized GitHub source publication and gated integration.
The sealed audit below retains its original local-only scope and observations;
its4050 base and old primary status are historical, not current synchronization
claims. PC recovery is now in main21ac89287449d8ca54385a116053a33655d86e6b
via PR2278. Checkpoint17678de1f17210eb9e5c2c7c75cc00fe57315980 preserves this
blockchain work, merged with that main in60d899fd6f58d69c8924f39c2262a39fa453463a.
Both independent ModLog additions and main's2993 reviewed security records survive.

The [WSP26 simulator-first contract](../../WSP_framework/src/WSP_26_FoundUPS_DAE_Tokenization.md#12-simulator-first-change-contract)
governs economic changes: classify, verify the existing simulator, resolve and
test the versioned decision there, review independently, align governing docs,
then require blockchain transaction parity. Source publication is separate from
economic activation. Deployment remains **BLOCKED** by the findings below.

The existing source-of-truth matrix incorrectly described a universal one-sat
unit. Its fee/projection convention and BTCReserve's tested1000-sat genesis
configuration are now explicitly **CONFLICTING / class D / activation BLOCKED**.
No balance conversion, peg, fee, supply or runtime policy changes in this addendum.
The six failed adversarial assertions remain failures, and missing signer/rekey/
bridge paths remain untested. Historical receipts retain their exact bytes.

Fresh publication qualification: selected simulator/documentation420 pass,
FAM485 pass, strict unsigned format52 pass, manifest consumer8 pass and three
Node compatibility commands pass. Scopes are separate and not summed. Desired
documentation RED was5 pass/1 failure before the matrix correction. All final
selected runs have no unexpected denied effects or source mutation. The four
strict SDK guard-denial controls are expected tests, not chain execution.
See the [separate publication receipt](receipts/FOUNDUPS_BLOCKCHAIN_PUBLICATION_20261031.json)
for exact result bindings and limits. Hosted PR/main gates remain required.

## Historical sealed local audit

**Deployment readiness: BLOCKED.** This is a local source reconciliation,
architectural review and offline verification record. It does not authorize
signing, funding, broadcasting, mainnet, deployment or GitHub changes.
Architect/integrator: 0102; independent source/research/test reviewers are
identified in the accompanying evidence. RedDog is the interaction surface,
not a monetary authorization authority.

## 1. PC and GitHub reconciliation

| Surface | Observed identity | Disposition |
| --- | --- | --- |
| Remote HEAD/main, fetched without pruning | `4050bdf880a2974511377a510a859f70101ea478` | Actual current observation, not assumed historical checkpoint |
| Remote `agent/simulator-first-blockchain-parity-20261031` | Same `4050bdf880a2974511377a510a859f70101ea478` | Branch creation only; no unique implementation |
| Primary `O:/Foundups-Agent` | `0c81418fe94a7786cfd55f01e138ddc5d510583d`, `feat/yumori-economic-impact-model` | 561 initially changed/untracked paths; preserved, no branch switch or edits |
| Owned PC worktree | `C:/Users/user/.codex/worktrees/foundups-repo-observation/Foundups-Agent` | Local parity branch at `4050bdf880a2974511377a510a859f70101ea478`, with reviewable uncommitted changes |
| Previous controller-allocation branch | `1c2176803927c4e8871b3213b5cbe54cb9334b4f` | Preserved; contains allocation prose, not a working controller |
| Open PR2261 | `0a3f06c5938b12863f0a00783b7fa8e3adc48789` | Exact scoped local import; no remote merge or disposition |

PR2202 (durable TestNet intention), PR2206 (unsigned codec), and PR2211 (JSON
framing) are merged. PR2210 and PR2261 remained open at inspection. Main lacks
the reviewed exact-built-in-integer admission and existing-intent revalidation.
The 14-path PR2261 delta was applied with `git apply --check` followed by
`git apply`, preserving current main's newer code and metadata. This includes
three product sources, three existing test owners, six module documents and two
receipt addenda. Historical receipt fields were preserved.

Comparison of 201 selected primary core Python files found no unique primary
product improvement requiring a second port. Of 40 selected dirty blockchain
paths, 29 matched main after line-ending normalization; a token-factory BOM
difference is not missing functionality. Primary historical research and older
policy overlays remain intact. This is a scoped comparison, not a claim that
all 561 unrelated paths were reconciled. Other worktrees and concurrent work
were not reset, cleaned, deleted or overwritten. Work is on the PC in the owned
worktree; it has deliberately not been copied over the busy primary checkout.

Current 1477-member runtime membership must be preserved; the older donor's
1472-member manifest is not applicable. Existing consumer pins are regenerated
from current sources. No old security exception ledger is copied or broadened.

## 2. Source-backed architecture map

Status distinguishes executable source from simulated economics and live evidence.
Module-relative references below use `modules/foundups/agent_market/` for FAM,
`modules/foundups/simulator/` for simulator economics, and `modules/` for
`platform_integration/algorand/`. Line references in the portable receipt bind
the inspected base and current source hashes.

| Component | Classification | Evidence and practical limit |
| --- | --- | --- |
| FAM scoped verifier/treasury context and pending payout | VERIFIED_IMPLEMENTED | `agent_market/src/authorization.py`, `src/persistence/sqlite_adapter.py`; transactional local controls, no independent grant issuer or funded payment |
| PREPARED TestNet intention and existing-only revalidation | VERIFIED_IMPLEMENTED locally | `agent_market/src/persistence/testnet_transfer_intents.py`; imported revalidation checks current policy/context without creating another intention; not a reservation or signed transaction |
| Integer reward/quantity admission | VERIFIED_IMPLEMENTED locally | `agent_market/src/models.py`, `src/orchestrator.py`; prevents bool/coercion acceptance, not monetary denomination conversion |
| Algorand ASA unsigned codec/framing | VERIFIED_IMPLEMENTED | `platform_integration/algorand/src/unsigned_asa_probe.py`; canonical unsigned bytes and declared TestNet inputs, no signature or ledger fact verification |
| FAM-to-codec controller, signer and transport | SPECIFIED_NOT_IMPLEMENTED | Algorand and FAM INTERFACE/ROADMAP; no connected funded settlement or durable attempt/reissue owner |
| Current account/ASA facts and confirmation | UNVERIFIED | No provider/RPC was queried; checksum, supplied authorization address and genesis label do not prove control, balance, freeze state or finality |
| Token factory and in-memory completed payouts | VERIFIED_SIMULATED | `agent_market/src/token_factory.py`, `src/in_memory.py`; shipped backend is mock; enum names are not Solana/EVM/Hedera deployments |
| CABR, demurrage, staking and pool distributions | VERIFIED_SIMULATED | `simulator/economics/`, `mesa_model.py`; tested portions use floating-point, process-local economic state |
| Internal F_i/UPS order book | VERIFIED_SIMULATED | `economics/fi_orderbook.py`, `allocation_engine.py`; matching/fees exist, funded escrow and settlement do not |
| Epoch commitment and BTC anchor | VERIFIED_IMPLEMENTED local integrity; VERIFIED_SIMULATED publication | `epoch_ledger.py`, `btc_anchor_connector.py`; local replay/Merkle checks, mock-only publication and locally incremented confirmations |
| 21M aggregate issuance, release and backing parity | CONFLICTING | `token_economics.py`, `pool_distribution.py`, WSP26/27/29/100; no proven aggregate chain supply invariant across mined/staked lanes |
| Generic blockchain domain | SPECIFIED_NOT_IMPLEMENTED | `modules/blockchain/src/src/src.py` remains a placeholder |

## 3. Incident evidence and lessons

Research accessed 2026-10-31. Company assertions, investigator conclusions and
independently decoded chain facts are different evidence classes. This review
did not reproduce transaction decoding, signatures or original deployed bytecode.

| Incident | Verified disclosure / investigation | FoundUps implication |
| --- | --- | --- |
| Binance exchange, 2019-05-07 | Binance reported approximately 7,000 BTC taken using compromised credentials/API/2FA information and coordinated withdrawals. SAFU coverage was promised; coverage is not recovery. [Binance](https://www.binance.com/en/support/announcement/detail/360028031711) | Aggregate limits and independent transaction authorization matter even when transfers carry valid signatures. |
| BSC Token Hub, 2022-10-06 | Bridge proof-verification failure enabled 2M unauthorized BNB, around $570M gross. The operator's October 11 snapshot reported roughly $100M moved off-chain and unrecovered. This was distinct from exchange custody. [BNB Chain](https://www.bnbchain.org/en/blog/bnb-chain-a-decentralized-response), [Coinbase investigation](https://www.coinbase.com/en-gb/blog/bsc-token-hub-compromise-investigation-and-analysis-8) | Do not add a bridge/wrapped-asset dependency to the initial FoundUps settlement path. |
| Bybit/Safe, 2025-02-21 | Targeted signing-interface/supply-chain manipulation changed the approved transaction's meaning. Multiple approvals shared compromised presentation. This was not an EIP-7702 incident. [Sygnia report](https://www.sygnia.co/blog/sygnia-investigation-bybit-hack/), [NCC analysis](https://www.nccgroup.com/research/in-depth-technical-analysis-of-the-bybit-hack/) | Independent signers must independently decode and verify the exact effect; quorum on one compromised interface is insufficient. |
| Binance exchange, 2026-10-29 | Company update acknowledges about $6.3B affected and about $3B frozen at its snapshot; initial laptop hypothesis expanded to other breach points. TRM reports Ethereum EIP-7702 authorizations and ordinary signed transfers on other chains; signing-infrastructure compromise is its assessment. [Binance update #2](https://www.binance.com/en/support/announcement/detail/d3306d9dca5243548c813b605e1d1751), [TRM](https://www.trmlabs.com/resources/blog/north-korea-steals-usd-6-36-billion-from-binance-in-the-largest-hack-in-history) | Deny arbitrary transaction/delegation capabilities. Key non-exfiltration does not establish that a signer cannot be misused. Root cause and final net loss remain provisional. |

The 2026 Binance support/Square date labels differ; the evidence retains that
discrepancy. Direct Binance requests returned a challenge, while search-reference
reads returned the disclosure. TRM and Hacken public bodies were retrieved;
explorer requests returned 403. Their linked delegation/reset/sweep hashes are
investigative references, not independently verified transaction proofs here.
[Hacken](https://hacken.io/insights/binance-hack/).

AI does not need to break cryptography to exploit an overprivileged operator.
An agent can be redirected by repository content, a tool response or dependency
into using otherwise legitimate credentials. Invariant demonstrated this with
a GitHub-connected agent; it was a controlled demonstration, not a FoundUps
incident. [Invariant](https://invariantlabs.ai/blog/mcp-github-vulnerability).
Treat prompts, project submissions, repository ownership badges, model-generated
PoB explanations and RPC responses as data, never new authority.

## 4. Cryptographic and service decision

Retain **Algorand as the existing bounded TestNet transport candidate**, subject
to fresh implementation/network qualification. Do not replace it with a new
Solana/EVM adapter or external DEX before the simulator/funding invariants exist.
This decision minimizes new dependencies; it is not a claim that Algorand or any
provider cannot be exploited. A public RPC service must never hold the signing
capability. Funded decisions require independently verified account/network/ASA
facts and exact effect checks, not trust in one RPC response.

Current Algorand documentation describes Falcon-1024 accounts after the v42
upgrade, alongside Ed25519. Network activation, SDK, signer and key-storage
support need explicit qualification. Native multisignature remains Ed25519-only;
participation/consensus keys are separate. Algorand's deterministic Falcon
variant must not be described as the unfinished NIST FN-DSA standard.
[Algorand account documentation](https://dev.algorand.co/concepts/accounts/post-quantum/).

Two additional migration checks matter: one Falcon key may control multiple
salt-derived addresses, so address count is not controller independence. The
documented off-curve address safety check is at the submission boundary rather
than consensus. Qualify canonical off-curve address generation independently;
never enable its bypass. Delegated programs must bind the intended sender.
[Algorand account limitations](https://dev.algorand.co/concepts/accounts/post-quantum/).

NIST FIPS203/204/205 are final; Falcon/FN-DSA standardization remains underway.
Use algorithm/version inventory and a migration plan, not custom cryptography
or a blanket quantum-proof label. PQ signatures do not repair compromised
transaction construction, policy, oracles, recovery, host software or supply-chain
dependencies. [NIST PQC](https://csrc.nist.gov/projects/post-quantum-cryptography).

Rekeying changes transaction authority; it is not automatic PQ migration or a
protection against malicious authorized signing. Account close-out clears rekey
state and can restore original-address authority. Normal reward/FX capabilities
must deny rekey, close/remainder, arbitrary app calls, delegation, asset authority
changes and unapproved grouped transactions. Recovery needs a distinct bounded,
independently approved path. [Algorand rekeying](https://dev.algorand.co/concepts/accounts/rekeying/).

Compiler security is a separate gate. Algorand's October 2025 Puya bulletin
documents optimizer removal of a final assertion and missing ARC-4 input checks.
It prescribes patched compilers, recompilation, build-metadata inspection and
negative tests of compiled output. The scoped FoundUps Algorand/blockchain source
search found no Puya/Algokit/TEAL compiler implementation to qualify here. Future
contract admission must pin a current patched toolchain and test generated code;
a chain brand or high-level source review is insufficient.
[Algorand compiler disclosure](https://dev.algorand.co/bulletins/puya-issues-27-10-2025/).

## 5. Economic conflicts and 0102 decisions

The simulator is the economic reference, not an excuse to promote a defect.
These unresolved class D conflicts block economic activation. Recommendations
below are architectural choices for the next versioned simulator decisions,
not silently enacted economic changes or legal conclusions.

| Conflict and current evidence | Recommendation before chain promotion |
| --- | --- |
| Nontransferable language in WSP26 versus internal F_i/UPS trading | Define separate token rights, permitted internal recipients/venues, staking claims and external restrictions; enforce them at the ledger/contract boundary. Nomination is not ownership or consent to tokenize someone else's rights. |
| 21M F_i cap versus separately tracked mined/staked issuance | Define whether staked F_i is the same capped asset or a separate claim. A single atomic supply/release authority must enforce the chosen aggregate invariant. |
| Continuous adoption versus PoC/Prototype/MVP and WSP100 tiers | Treat product milestones, adoption and governance maturity as distinct inputs. Ratify one release schedule and authenticated evidence rules; none independently grants mint authority. |
| UPS denomination: reserve/pool genesis uses 100,000 UPS/BTC; order cap uses 100,000,000 | Use the tested genesis denomination (1 UPS = 1,000 sats for that accounting snapshot) as the proposed canonical conversion; revise the order-cap oracle only through an explicit versioned simulator decision. Do not promise fixed redemption from a unit convention. |
| Per-call CABR release budget versus per-epoch Treasury allocation | Debit/reserve one funded epoch allocation before PoB/CABR routing. Bind proof/source consumption and all partial releases to its durable identity. CABR never independently mints UPS. |
| Mesa independently distributes 1% of total stakes per interval | No visible corresponding Treasury debit establishes funding. Replace only after the funded allocation model passes conservation/replay tests. |
| Task, epoch and stakeholder pool fractions use different denominators | Specify operation, source pool, beneficiary/residual and fee order. Do not normalize competing percentages into a new economy without a versioned decision. |
| Fees differ across WSP26, TOKENOMICS and code | One operation/version/unit/beneficiary schedule; preserve existing valid tests until each discrepancy is explicitly decided. |
| Float balances, demurrage redistribution/burn variants and reserve snapshots | Exact integer asset units, specified rounding/residual owner, liquid-UPS-only decay, and reconciled mirrored balances are prerequisites for funded settlement. |
| Internal FX versus external venues/bridges and BTC custody | Internal funded FX first; BTC custody and attestations remain separate. Token rights, custody, exits and jurisdiction-specific legal review are unresolved. No compliance certificate is asserted. |

The source audit records precise WSP26/27/29/100, TOKENOMICS, BTC architecture and
simulator references for every row. WSP mirrors were not rewritten because this
slice changes no approved economic policy. Future class C changes must update
the simulator, pass independent review, then update both governing mirrors before
any corresponding blockchain behavior is promoted.

## 6. Security architecture and attack coverage

Required flow: funded Treasury reservation -> allocation identity -> independently
validated PoB/CABR -> integer distribution plan -> exact unsigned artifact ->
independent controller approval -> separately held signer -> bounded submission
-> independently confirmed settlement. Most stages after local planning remain
unimplemented. A separate signature on arbitrary model text would not satisfy this.

Capabilities must bind operation, chain/genesis, asset, source, destination,
amount, fee ceiling, rounds/expiry, policy version, controller/beneficial owner,
intent/artifact identity and one-use execution attempt. Pending amounts count
against wallet, agent, identity, FoundUp and global rolling-window limits within
the same atomic admission transaction. Timeout is not permission to release a
reservation or submit a second payment. Reconcile ambiguous outcomes before retry.

Work verification must be independent of both the worker and the creator's
controlling 012, consistent with WSP29. Distinct displayed IDs are insufficient.
The monitor must aggregate activity across FoundUps and related identities so
many small withdrawals cannot evade a per-wallet threshold. Key rotation,
threshold approval, emergency freeze/unfreeze and recovery must use independent
administrative authority and audit evidence. A different agent name or key on
the same compromised host is not independent control. Quorum, HSM/MPC and PQ
signatures reduce particular risks; none replaces transaction-effect validation.

The following A01-A12 identifiers are the operator's mission taxonomy. The
research attachment's similarly numbered threat rows are a separate catalog;
they are not substituted for this required scenario matrix.

| Scenario | Actual local evidence in this mission | Remaining boundary |
| --- | --- | --- |
| A01 coordinated small losses | External probe of 1,000 FoundUp books/shared identity | Aggregate pending reservations and distributed drain detection absent; no live withdrawal simulation |
| A02 compromised agent | Existing prepaid-wallet spending/permission tests and external bounded-spend probe | No durable pending-agent/global limit or independent signing capability |
| A03 compromised signing key | BLOCKED: no real signer to attack | Separate signer/controller, treasury policy and aggregate funding required |
| A04 delegation/rekey abuse | BLOCKED chain execution; existing unsigned field allowlist only | Verify actual account authority, reject rekey/close/delegation at signer and chain boundary |
| A05 false PoB | Truthy/non-boolean and invalid numeric inputs reproduced RED, fixed locally | A literal True or plausible false score still needs independent authenticated evidence and one-time consumption |
| A06 manipulated maturity | Existing numeric/supply tests; source-level release conflict | Authenticated maturity, aggregate issuance and versioned release policy not established |
| A07 replay/double settlement | Existing FAM/epoch replay tests plus external duplicate distribution probe | Local ledger deduplication does not undo upstream distribution side effects or prove chain settlement |
| A08 collusive FX prices | External same-identity self-trade probe | No funded matching, related-party detection or oracle-independent price policy |
| A09 external swap/bridge bypass | BLOCKED: no real external venue/bridge path | No bridge enabled; chain restrictions must be proven before any external listing |
| A10 governance manipulation | External policy alias probe; current source review | Trusted issuer, immutable versioned policy, timelock and independent governance controls absent |
| A11 reserve oracle abuse | Invalid numeric breaker inputs fixed; external plausible false-credit probe | Numeric validity is not authentic/fresh BTC backing or proof of liabilities |
| A12 emergency recovery | Historical timing failure retained; hourly-readiness candidate passes focused 54, independent five, broader and package; security/delivery pending | Emergency with queued exits stays held; no funded/concurrent/restart or authenticated cancellation/reconciliation/unfreeze guarantee |

Contract audit must additionally cover reentrancy/inner-call behavior, group/order
manipulation, fee changes, stale prices, replay domains/nonces, duplicate settlement,
storage/resource exhaustion and compiler/dependency defects. No deployed FoundUps
contract was available to qualify those defenses. These are requirements, not
claims that A01-A12 or a provider test establishes universal protection.

## 7. Local changes and verification

The imported FAM changes are class B security changes with unchanged valid
quantity economics. New local CABR admission preserves finite signed clamps,
the 2% default and valid operation order. The breaker now chooses restricted
outflow before backing caution and applies its existing cooldown/empty-queue
condition to every severity downgrade. Invalid inputs fail before transition.
Thresholds, fees and demurrage multipliers are unchanged. These class B fixes
operate in the simulator; chain-level independent testing remains unavailable.

New CABR/flow conservation properties use seeds 0, 7 and 3102, 256 cases per seed.
Their exact valid formula outputs are checked and conservation uses an explicit
floating tolerance. This is not exact-integer financial conservation. Circuit
tests freeze the clock; no wall-clock sleep is used. Existing assertions remain.

Fresh selected baseline: 244 passed. Desired security RED: 79 cases, 12 passed
and 67 failed. Repaired connected selection: **414 passed, zero failed/error/skipped**,
with unchanged source hashes during execution and zero denied effects in the
final configured scratch run. No historical test count is substituted.

Retained diagnostic failures: the first harness rejected pytest's default log
path before collection; an initial connected selection named a nonexistent test
owner and ran zero tests. Early valid runs denied a local `socket.gethostname`
query and optional central-daemon SQLite outside scratch. Stack attribution led
to allowing only the local hostname operation and configuring the actual central
daemon's documented scratch directory. No economics/module stub replaced it.
All network connections, subprocess attempts, dotenv reads and non-scratch
SQLite remained denied in the simulator harness. This is Python instrumentation,
not operating-system confinement or a production-runtime qualification.

Additional FAM, Algorand, manifest, held-out and attack-probe results are recorded
in the companion portable receipt and final execution addendum below. Deliberate
failed attack oracles remain failures; they are not relabeled xfail or PASS.

### Fresh execution addendum

| Executed scope | Result | Qualification limit |
| --- | --- | --- |
| Ten existing FAM owners, current imported overlay | 485 passed, zero failures/errors/skips | 45 stable FAM source files; 329 scratch SQLite connections; no funded payment |
| Nine simulator owners, current fixes | 414 passed, zero failures/errors/skips | Real module paths and scratch central daemon; not a full simulator suite |
| Independent CABR/breaker held-outs | 6 passed, zero failures/errors/skips | Independent reviewer accepts this bounded fix; emergency queue recovery remains absent |
| Existing strict Algorand format qualifier | 52 passed, zero unexpected effects/diagnostics | Separate preserved SDK profile; four intentional guard-denial controls passed; not FAM/SDK integration |
| External adversarial assertions, seed310001 | 1 passed, 6 failed, zero errors/skips | Root reproduced the same outcomes; no failed oracle was weakened |
| Existing manifest generator/consumer tests | 8 passed, zero failures/errors/skips | Current worktree generation/pins; staged-index case separately checks unchanged base4050 |
| Existing Node compatibility/preflight/recovery entrypoints | 3 entrypoints passed | Package checks, no runtime activation or real chain effects |

The strict codec qualifier rechecked 5,263 file bindings and 286 prebound loaded
origins. Its compatible CPython3.12.10 profile is not a current patched production
runtime claim. FAM and codec results do not combine into settlement qualification.

The regenerated manifest retains all 1,477 members and 1,473 unchanged runtime
hashes. Only models, orchestrator, CABR router and breaker hashes change, with
both existing consumer pins updated to
`56c72c629300b55834f9e40156c12d1f00bdf37947a902867cfb203d133e4426`.
The initial five-change preflight correctly stopped before writing: the opt-in
intent facade is not resident runtime membership. The corrected four-change
preflight and canonical generation do not expand membership or byte caps.
Future controller admission must include its actual facade/ORM/SDK closure.
All seven economic traces were byte-identical in the independent reproduction.

Actual adversarial traces:

- **A01 FAIL:** the existing allocation consumer accepted 1,000 one-UPS pending
  orders in 1,000 FoundUp books for one owner; its 100-UPS balance stayed unchanged.
  This invokes the private simulator consumer, not a public withdrawal endpoint.
- **A02 PASS:** a 20-UPS prepaid wallet paid 15 UPS plus 0.015 fees, retained
  4.985 UPS and denied 17 further requests. This proves only that tested sequence.
- **A07 FAIL:** duplicate epoch distribution raised one participant's credits
  from 76.8 to 153.6 and accumulated fund from 4 to 8. The epoch ledger correctly
  retained one entry: deduplication happened after economic side effects.
- **A08 FAIL:** one identity bought from itself, producing 10 UPS volume and
  0.2 UPS simulated fee counters. No funded trade was demonstrated.
- **A10 FAIL:** mutating the caller-owned allowed-operation list changed a
  denied action into an accepted 2-UPS spend plus 0.002 fee. This exposes missing
  policy snapshot isolation, not proven external governance takeover.
- **A11 FAIL:** the trusted-caller simulator reserve method accepted an
  unverified finite 10-BTC input. There is no existing deposit-proof verifier to
  claim was bypassed; authenticity admission is missing.
- **A12 FAIL:** consecutive queue-processing calls released 10 then 9 of 100
  requests, leaving 81. Request count is conserved, but hourly scheduling is a
  caller assumption. This does not bypass the repaired emergency cooldown.

Initial test harness failures and all desired RED evidence remain retained.
Absent signer, live delegation/rekey and external venue hooks are **BLOCKED**,
not skipped or simulated PASS. There is no current CI, mainnet, installed-runtime,
legal or comprehensive dependency-security certification from these results.

## 8. Ordered remaining implementation

1. **P0, class D/C:** resolve and version the asset-unit, 21M aggregate release,
   funded epoch budget, fee and pool denominator decisions above. Add integer
   conservation and replay tests in the existing simulator owners first.
2. **P0, class B:** implement durable funded reservations and idempotent
   distribution/FX settlement in existing FAM/ledger owners; enforce overlapping
   identity/FoundUp/global windows including pending and ambiguous attempts.
3. **P0, class B:** independent controller/grant issuer, immutable policy and
   authenticated proof/oracle facts; fix self-trade/queue/policy findings with
   actual path tests. Emergency recovery requires a recoverable audit trail.
4. **P0, class A/B:** connect existing PREPARED intention and unsigned codec with
   durable artifact/attempt/reissue records. Independently compare simulator and
   chain transitions, integer units, fees, authority and finality.
5. **P0, class B:** qualify a separate signer and patched dependency/runtime
   profile, chain-level adversarial tests and external security review. PQ
   migration and recovery drills must include actual supported account types.
6. Only after those gates, separately authorize an unfunded/local or bounded
   TestNet deployment experiment. Live signing/funding is outside this mission.

No external DEX, bridge, mass token issuance, treasury launch or production
deployment is justified by the current source, mock tests or documentation.

## 9. Evidence location and scope

External working evidence is retained under
`C:/Users/user/AppData/Local/Temp/foundups-blockchain-20261031/`.
The portable receipt preserves reviewed source/command/outcome identities for
reproduction beyond that temporary directory. Initial source audits are pinned to
4050; subsequent local fixes and test results are separately labeled.
Holo lexical retrieval returned UNKNOWN freshness and a reported index gap;
current direct source inspection and NAVIGATION verified the selected owners.
No reindex, GitHub write, live asset access or signing occurred.

[Portable source and test receipt](receipts/FOUNDUPS_BLOCKCHAIN_RECONCILIATION_20261031.json)
includes actual case results, source hashes, commands, primary-source citations,
failed attack traces, independent review and reproducible external test sources.
