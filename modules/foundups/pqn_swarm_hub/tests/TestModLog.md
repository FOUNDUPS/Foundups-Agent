# TestModLog - PQN Swarm Hub FoundUp

## Test Suite Summary

| File | Tests | Purpose | Slices Covered |
|------|-------|---------|----------------|
| `test_contracts.py` | 13 | Contract creation, deterministic IDs, status values | Contracts |
| `test_poc_flow.py` | 5 | End-to-end flows (accept, reject, manual, idempotent, stats) | Registry, Sink, Verification, Contribution |
| `test_detector_bridge.py` | 5 | DetectorBridge integration with pqn_alignment | Detector Bridge |
| `test_persistence.py` | 18 | SQLite CRUD, service integration, full flow persistence | Persistence |
| `test_publication_adapter.py` | 16 | MoltBook publish, rejection gate, stub fallback | Publication Adapter |

**Total**: 57 tests (all passing)

---

## V0.5.0 - Publication Adapter Tests

**Date**: 2026-03-29

Added `test_publication_adapter.py` (15 tests):

- `TestPublicationAdapterInit` (3 tests): Init defaults, no auto-connect, get_status
- `TestPublishSuccess` (2 tests): Successful publish via mocked MoltBook, duplicate flag
- `TestRejectedDecision` (2 tests): Rejected decision does NOT publish, reason in message
- `TestStubFallback` (3 tests): Stub when not connected, records publication, clear stubs
- `TestPayloadFormatting` (3 tests): Required fields, content includes metrics, artifacts
- `TestMoltBookError` (1 test): Graceful failure on MoltBook error
- `TestSingleton` (1 test): get_publication_adapter returns singleton

**Key Coverage**:
- Publication gate: only accepted decisions publish
- Stub fallback: graceful handling when MoltBook unavailable
- Payload formatting: PQN data mapped to MoltBook research format

---

## V0.4.0 - Persistence Tests

**Date**: 2026-03-29

Added `test_persistence.py` (18 tests):

- `TestSQLiteStoreInit` (3 tests): DB file creation, directory creation, empty stats
- `TestWorkUnitPersistence` (5 tests): Save/get, nonexistent, list, filter, update
- `TestSubmissionPersistence` (2 tests): Save/get with FK, list by work unit
- `TestDecisionPersistence` (2 tests): Save/get with FK chain, list by submission
- `TestContributionPersistence` (2 tests): Save/get with full chain, list by contributor
- `TestParticipantPersistence` (1 test): Save/get participant identity
- `TestServiceIntegration` (3 tests): Registry persistence, full flow, gate persistence

**FK Handling**: Tests create proper parent entity chains to satisfy foreign key constraints.

---

## V0.3.0 - Gate/FAM Adapter

**Date**: 2026-03-29

Gate and FAM adapter tests pending (integration via `test_persistence.py::TestServiceIntegration::test_gate_persists_participants`).

---

## V0.2.0 - Detector Bridge Tests

**Date**: 2026-03-29

Added `test_detector_bridge.py` (5 tests):

- Real detector runs via `DetectorBridge.run(work_unit)`
- Metric extraction from CSV/JSONL artifacts
- Happy-path uses `manual_verify()` for guaranteed contribution flow

---

## V0.1.0 - Initial PoC Tests

**Date**: 2026-03-29

Added `test_contracts.py` (10 tests):
- Contract instantiation and defaults
- Deterministic ID generation
- Status enum values
- Score clamping (0.0-1.0)

Added `test_poc_flow.py` (5 tests):
- Full accepted flow: register -> submit -> auto_verify -> record
- Rejected flow: coherence below φ-floor
- Manual override path
- Idempotent submission handling
- Contributor stats aggregation

---

## Running Tests

```bash
# Run all pqn_swarm_hub tests
python -m pytest modules/foundups/pqn_swarm_hub/tests/ -v

# Run specific test file
python -m pytest modules/foundups/pqn_swarm_hub/tests/test_persistence.py -v

# Run with coverage
python -m pytest modules/foundups/pqn_swarm_hub/tests/ --cov=modules.foundups.pqn_swarm_hub
```

---

## Test Dependencies

- pytest
- pytest-asyncio (for future async tests)
- Temp directories for SQLite isolation (via `tmp_path` fixture)
- `gc.collect()` for Windows SQLite file lock cleanup
