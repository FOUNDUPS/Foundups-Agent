# FoundUps Simulator Test Suite

This directory contains regression tests for the FoundUps simulator module.

## Relevant files for this change

| Test file | Purpose |
|---|---|
| `test_btc_reserve_semantics.py` | Validates BTC reserve semantics, canonical UPS supply fields, treasury routing aliases, and the genesis UPS denomination contract. |
| `test_docs_contract_alignment.py` | Guards alignment between tokenomics documentation and simulator contracts. |

## UPS genesis denomination guard

The BTC reserve simulator currently defines:

```text
1 BTC = 100,000 UPS at genesis
1 UPS = 0.00001 BTC
1 UPS = 1,000 sats
```

`test_btc_reserve_semantics.py` includes regression coverage to prevent documentation or implementation drift back to `1 UPS = 1 sat` while `genesis_ups_per_btc` remains `100000`.

## Running targeted tests

```bash
pytest modules/foundups/simulator/tests/test_btc_reserve_semantics.py -v
```

## WSP notes

- WSP 13/14: test changes should be documented in this README.
- WSP 97/99: this change is scoped to denomination alignment only.
- Out of scope: BitcoinStandardValuation, F_i notation cleanup, and I_i bonding curve logic.
