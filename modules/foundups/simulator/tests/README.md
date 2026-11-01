# FoundUps Simulator Test Suite

## Hourly queue cadence acceptance — 2026-11-01

The existing breaker owner retains seven original test ASTs / 35 cases. Nineteen
frozen desired cases cover 3,599.999/3,600 boundaries, rollback, long gaps, FIFO
identity conservation, minimum-one math, empty/refill, emergency holds, logging
failure and constructor/equality compatibility. Patch stdlib `time.monotonic`;
no private timer name or clock-read count is an oracle. Actual RED is 12 pass /
7 fail; focused 54 and independent five pass, with source acceptance. The promoted
240-line owner keeps its old raw prefix/oracles; broader 1,209 passes, same three
SSE HTTP deselections, zero failures/errors/skips/guards and 174 stable snapshots.
New 19 are within the broad run, five outside it; do not sum scopes. Package eight
Python/three Node pass; security/publication remain pending. No fresh 240-tick trace
ran; prior traces did not exercise positive queue releases or prove payment/recovery.

## Native allocation admission controls — 2026-11-01

Execution and independent scoped source review are accepted:
The 171 frozen cases plus 25 independent held-outs passed: 196 cases. The 311
original regressions passed with exact prior case IDs. Zero errors, skips or guard
denials were recorded; 174 simulator/FAM Python source snapshots remained stable.
Independent source/AST/budget review reports no material findings within the
frozen native-state contract.
Frozen controls cover wallet receive, human debit, engine routing and MetaGPT
registration: hostile/non-finite/negative scalars, participating-state overflow,
preparation failures with no participating writes, policy retention, valid
arithmetic, lookup precedence and insufficient zero-wallet registration.
Supported native state and trusted serialized hosting are the boundary; arbitrary
receiver hooks, logging rollback, concurrency and durable funding are unqualified.

The 311-pass baseline and separate desired 171-case RED (48 pass / 123 fail)
remain historical evidence. The 171 frozen controls are promoted into existing
`test_allocation_and_treasury_runtime.py` (336 lines); the original prefix/AST
and frozen non-docstring AST are preserved. Promoted/broader execution results:
The broad run passed 1,190 cases: the prior 1,019 plus 171 promoted controls.
The promoted owner contributes 173 cases, derived from that broad result rather
than another run. The same three SSE HTTP cases were deselected; zero failures,
errors, skips or guard denials; 174 source snapshots remained stable. The 25
external held-outs are outside 1,190, and these overlapping scopes are not added.
Controlled fresh de baseline/candidate 240-tick raw traces match under the finite
profile. Package eight Python/three Node and registry 1,800/260 pass with the
same 1,481 members and unchanged caps. Security/publication/candidate-main/PC/Holo
remain pending and separate. Do not sum scopes,
replace old oracles, infer full A02/B05 or use passing tests as chain authority.

## Reserve quote observation — 2026-11-01

Existing `test_btc_reserve_semantics.py` retains all seven original cases and adds
the frozen 89-case observation acceptance: literal digest goldens, exact record
types/detachment, rational extrema, hostile scalar/receiver rejection without
hooks, context/tick grammar, zero-reserve branches and unchanged source/Decimal
state. Historical baseline: 7 pass/89 desired failures. Independent candidate
selection passes 113 including 17 separate held-outs. Promoted 96 and broader
1,019 cases pass with 174 unchanged simulator/FAM Python source snapshots,
including tests, the same three SSE HTTP
deselections and zero failures/errors/skips/guard denials; counts overlap.
Package eight Python cases/three Node entrypoints and unchanged registry check
pass separately; these are not installed-runtime or chain acceptance.
The [interface](../INTERFACE.md#opt-in-simulator-reserve-quote-observation--2026-11-01)
requires serialized host reads and grants no authority or funded/chain proof.

## Replay-safe epoch effects — 2026-11-01

Existing `test_staker_hurdle_state.py`, `test_epoch_ledger_settlement_commitment.py`
and `test_layer_d_anchor_runtime.py` retain prior oracles and add41 controls for
complete effects, detached exact/late retries, conflicts, invalid requests,
overflow, shared staker sequencing, failed preparation, concurrency, captured
Mesa retry and observer failures. The three-owner run passes192; separate frozen
acceptance plus held-outs passes57. These scopes overlap. See
[TestModLog](TestModLog.md) for the genuine RED failures, source bindings,
controlled-process trace parity and rejected initial nondeterministic traces.
Do not infer reproducibility from config.seed alone or chain safety from mocks.
The [interface](../INTERFACE.md#pool-epoch-effect-contract--2026-11-01) states the
process-local boundary and remaining funded/durable accounting work.
Broader simulator:930 pass with the same3 SSEHTTP deselections; package checks
pass8 Python cases and3 Node entrypoints. These are separate, overlapping scopes.

## Wallet policy security suite — 2026-11-01

`test_wallet_policy.py` freezes constructor, host replacement, allocation, hostile
object admission, nested alias isolation, public-view immutability, exact integer
limits and legacy empty-policy behavior. Desired baseline: 76 cases, 6 passed/
70 failed. Candidate with three original regression owners: 311 passed, no
failures/errors/skips or instrumented forbidden effects. Independent held-outs
are separate; counts overlap other runs and do not establish chain security.


This directory contains regression tests for the FoundUps simulator module.

`test_docs_contract_alignment.py` also checks the explicit blocked denomination
conflict against the tested genesis value and compares governing WSP26/27/29/100
mirrors. These are documentation guardrails, not funded settlement tests. Any
resolution needs a reviewed simulator decision and new economic oracles before
changing the conflict expectation; do not simply delete the gate.

2026-10-31: `test_cabr_flow_router.py` adds exact-bool/finite scalar admission
and seeded valid-formula/conservation properties; `test_circuit_breaker.py`
covers competing severity, frozen-clock cooldown, queue hold and invalid inputs.
The final connected9-owner run passes414 cases; independent6 held-outs pass.
The seven separate external adversarial probes have six unresolved failures;
they are recorded in the architecture receipt, not passing chain-security tests.
Use credential-free scratch storage and real central-daemon scratch configuration;
no live signer/provider is necessary or authorized for these tests.

## Work/stake/unstake numeric admission

The existing `test_alignment_and_tokenomics.py` retains all6 original test ASTs
and adds223 controls for invalid quantities/fees, prospective overflow, mutation
order, optional adoption None and valid zero/fractional/normalization behavior.
Focused exact-AST projection226 passes; independent held-outs28 pass. Actual
combined-main simulator736 passes, including all6 originals and8 adjacent
profit/allocation/FAM lifecycle cases, with exactly3 existing SSE HTTP exclusions.
These overlapping counts are not added. [TestModLog](TestModLog.md) records
the corrected optional-None oracle, genuine normalization regression, historical
runner limits and fresh scratch-store confinement. No funded settlement proof.

## Mock BTC replay and realm integrity

The existing `test_btc_anchor_connector.py` covers full-v2 field/type/version/hex
and UTC validation, force semantics, immutable conflicts, legacy/partial migration,
canonical schema constraints, failed/pending receipt gates, two-instance races,
rollback/response loss and constructor/singleton configuration. Fifteen original
case oracles remain; the TestNet-to-mock coercion expectation is deliberately
replaced by unsupported-mode rejection. `test_layer_d_anchor_runtime.py` retains
its two original runtime cases and adds selected-mode rejection through the real
builder. No new test file or live backend is introduced.

Current repaired selection:113 BTC,8 runtime,88 epoch and2 parameter cases =211.
Affected simulator closure:513 pass with the same3 named SSE HTTP exclusions.
Independent21 held-outs and source review pass. These counts overlap and must
not be added. [TestModLog](TestModLog.md) preserves initial failures, the fixture
timing correction and the supplied-schema review repair. No real network,
funded transfer, source authenticity or future external-I/O recovery is qualified.

## Epoch evidence integrity

`test_epoch_ledger_settlement_commitment.py` retains its original two cases and
adds adversarial claim/context/root/path binding, invalid numbers/maps/epochs,
large-integer normalization, exact/conflicting retries, monotonic gaps, nested
snapshot ownership, hash-failure atomicity, concurrent finalization and stable
versioned commitments. Existing `test_btc_anchor_connector.py` and
`test_layer_d_anchor_runtime.py` remain adjacent regression owners. Local
focused closure is106 cases, including two independently motivated private
list/index corruption controls; exact RED/GREEN inventories and offline runner
isolation are in [TestModLog.md](TestModLog.md). These tests do not establish
funded balances, durable source consumption, non-mock migration or settlement.

## FAM authority compatibility

`test_fam_lifecycle_flow.py` retains existing lifecycle behavior and checks that
caller-ID impersonation and mutable legacy role labels cannot create trusted
verification or treasury contexts. The bridge uses fixed simulation principals.
These are local simulation controls, not authentication or funded settlement.
See [TestModLog](TestModLog.md) for combined closure and explicit SSE exclusions.

## Relevant files for this change

| Test file | Purpose |
|---|---|
| `test_btc_reserve_semantics.py` | Validates BTC reserve semantics, canonical UPS supply fields, treasury routing aliases, and the genesis UPS denomination contract. |
| `test_docs_contract_alignment.py` | Guards alignment between tokenomics and architecture documentation and simulator contracts. |

## UPS genesis denomination guard

The BTC reserve simulator currently defines:

```text
1 BTC = 100,000 UPS at genesis
1 UPS = 0.00001 BTC
1 UPS = 1,000 sats
```

`test_btc_reserve_semantics.py` checks the genesis denomination and verifies that increasing the reserve changes the circulating UPS value. `test_docs_contract_alignment.py` reads the architecture's genesis denomination and TOKENOMICS example and compares them with `genesis_ups_per_btc`, preventing a return to `1 UPS = 1 sat` while that constant remains `100000`.

## Running targeted tests

```bash
pytest modules/foundups/simulator/tests/test_btc_reserve_semantics.py modules/foundups/simulator/tests/test_docs_contract_alignment.py -v
```

## WSP notes

- WSP 13/14/22: test changes are documented here and in the existing `TestModLog.md`.
- WSP 97/99: this change is scoped to denomination alignment only.
- Out of scope: BitcoinStandardValuation, F_i notation cleanup, and I_i bonding curve logic.
