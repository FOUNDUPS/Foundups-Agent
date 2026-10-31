# FoundUps Simulator Test Suite

This directory contains regression tests for the FoundUps simulator module.

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
