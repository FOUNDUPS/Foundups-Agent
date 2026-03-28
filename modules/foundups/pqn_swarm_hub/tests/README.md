# Tests - PQN Swarm Hub FoundUp

## Overview

Tests for the PQN Swarm Hub FoundUp contracts and flows.

## Test Structure

```
tests/
  test_contracts.py      - Contract dataclass validation
  test_registry.py       - Work unit registry operations (future)
  test_submission.py     - rESP submission sink (future)
  test_verification.py   - Accept/reject logic (future)
  test_contribution.py   - ROC reporting (future)
  test_integration.py    - End-to-end flow (future)
```

## Running Tests

```bash
# From repo root
pytest modules/foundups/pqn_swarm_hub/tests/ -v

# With coverage
pytest modules/foundups/pqn_swarm_hub/tests/ --cov=modules.foundups.pqn_swarm_hub
```

## Phase 0 PoC Tests

Minimum acceptance tests for Phase 0:

1. **Contract creation**: All four contracts can be instantiated
2. **Deterministic IDs**: Same inputs produce same IDs
3. **Status transitions**: Valid status values accepted
4. **Score clamping**: ContributionRecord.score stays in [0.0, 1.0]

## Integration Tests (Phase 1)

- Integration with pqn_alignment detector
- Integration with moltbook_distribution_adapter
- Persistence roundtrip tests
