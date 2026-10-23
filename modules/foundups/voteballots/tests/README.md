# Vote/Ballots Tests

**Status**: Active PoC test suite  
**Primary inventory**: `tests/TestModLog.md`  
**WSP Compliance**: WSP 22, WSP 50, WSP 84, WSP 97

---

## Mandatory Pre-Test Gate

Before creating or modifying any VOTE test:

1. Read `tests/TestModLog.md`.
2. Read this README.
3. Inspect the closest existing test file.
4. Prefer extending/reusing an existing test file or fixture when the target behavior is already represented.
5. Create a new test file only for a materially distinct contract or subsystem.
6. Update `tests/TestModLog.md` after any test addition, removal, rename, or major coverage change.

This is an anti-vibecoding requirement: the test inventory exists so workers do not recreate tests that already cover the behavior.

---

## Current Active Test Surface

See `TestModLog.md` for the canonical file-by-file inventory and reuse guidance.

Current test files include:

- `test_fec_adapter.py`
- `test_entity_resolution.py`
- `test_funding_summary.py`
- `test_confidence_scoring_integration.py`
- `test_quick_answer.py`
- `test_shell_integration.py`
- `test_adversarial_influence_categories.py`
- `test_unit_confidence_scoring.py`

The canonical VOTE PoC closure snapshot records **303 passing tests** on 2026-05-25 for the implementation-complete six-slice chain. That historical result is evidence, not a claim that the suite was rerun for later docs-only work.

---

## Suite Boundaries

The current PoC suite is designed to remain deterministic and safe:

- no live FEC API required for the core tests
- no API key required for the core tests
- no unmocked network calls in the PoC chain
- ambiguity must be preserved rather than guessed
- evidence provenance and trail termination must be preserved
- dark-money or foreign-funding claims cannot be promoted to verified fact without evidence
- no candidate recommendation
- no targeted persuasion
- no microtargeting
- shell tests do not activate public routes or mutate registry/catalog/manifest state

---

## Running Tests

From repository root:

```bash
# Full VOTE suite
python -m pytest modules/foundups/voteballots/tests/ -q

# A focused existing file — preferred before inventing a new test file
python -m pytest modules/foundups/voteballots/tests/test_funding_summary.py -q

# Focus by test name / behavior
python -m pytest modules/foundups/voteballots/tests/ -k "entity_resolution" -q
```

For coverage, use the repository's current coverage workflow rather than assuming the older design-spec command is still canonical.

---

## Test Families

### Data-source and identity
- FEC adapter
- entity resolution / ambiguity

### Evidence and truth boundary
- funding summary
- confidence scoring
- adversarial influence categories

### User-facing output
- quick answer
- pfMALL shell payload

### Legacy/unit precedent
- unit confidence-scoring scaffold

When adding behavior, start from the closest family above and consult `TestModLog.md` before deciding that a new test file is necessary.

---

*0102 operational rule: retrieve the test inventory before test creation; reuse before duplication.*
