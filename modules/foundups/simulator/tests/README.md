# FoundUps Simulator Test Suite

This directory contains regression tests for the FoundUps simulator module.

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
