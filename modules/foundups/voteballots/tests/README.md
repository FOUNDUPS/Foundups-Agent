# Vote/Ballots Tests

**Status**: Design Specification  
**WSP Compliance**: WSP 5 (Test Coverage)  

---

## Test Categories

### Unit Tests (`test_unit_*.py`)

Test individual hooks in isolation with mocked external APIs.

```bash
pytest tests/test_unit_*.py -v
```

### Golden Tests (`test_golden_*.py`)

Test against known candidates with verified ground truth.

```bash
pytest tests/test_golden_*.py -v
```

### Adversarial Tests (`test_adversarial_*.py`)

Edge cases designed to trigger failure modes.

```bash
pytest tests/test_adversarial_*.py -v
```

### Integration Tests (`test_integration_*.py`)

Full pipeline tests with sandboxed real API calls.

```bash
SANDBOX_MODE=true pytest tests/test_integration_*.py -v
```

---

## Test Data

### Golden Dataset

Location: `tests/fixtures/golden/`

Contains verified data for:
- 10 federal candidates (diverse offices, parties, funding patterns)
- 5 state candidates
- Known attack ad campaigns
- Known dark money patterns

### Adversarial Cases

Location: `tests/fixtures/adversarial/`

Contains edge cases:
- Same-name candidates (disambiguation tests)
- Foreign funding false positive prevention
- AIPAC vs foreign funding distinction
- Dark money estimation bounds

---

## Running Tests

```bash
# All tests
pytest tests/ -v

# Unit only (fast, no network)
pytest tests/test_unit_*.py -v

# With coverage
pytest tests/ --cov=src --cov-report=html

# Specific hook
pytest tests/ -k "entity_resolution" -v
```

---

## CI Requirements

1. Unit tests: Must pass on every PR
2. Golden tests: Must pass on every PR (cached data)
3. Adversarial tests: Must pass on every PR
4. Integration tests: Run on main branch only (API keys required)

---

*0102 pArtifact: Test structure per WSP 5. No tests in root directory.*
