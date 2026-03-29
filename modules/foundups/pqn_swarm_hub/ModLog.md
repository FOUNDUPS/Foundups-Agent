# ModLog - PQN Swarm Hub FoundUp

## V0.5.0 - Publication Adapter (MoltBook Integration)

**Slice**: `pqn_swarm_hub_publication_adapter`
**Author**: 0102
**Date**: 2026-03-29

### Changes

- Added `src/publication_adapter.py`:
  - `PublicationAdapter` class wraps `moltbook_distribution_adapter`
  - `publish(work_unit, submission, decision, contribution)` main API
  - `PublicationResult` dataclass for structured return
  - Gate: only publishes accepted decisions (rejects return immediately)
  - Stub fallback: graceful handling when MoltBook unavailable
  - `get_publication_adapter()` singleton accessor
  - `reset_publication_adapter()` for testing

- Added `tests/test_publication_adapter.py`:
  - 16 tests for publication adapter
  - Success path with mocked MoltBook
  - Rejected decision does NOT publish (gate test)
  - Stub fallback when MoltBook unavailable
  - Payload formatting tests
  - Error handling tests

- Updated exports:
  - `PublicationAdapter`, `PublicationAdapterError`, `PublicationResult`
  - `get_publication_adapter()`, `reset_publication_adapter()`

- Updated `INTERFACE.md`:
  - Documented PublicationResult contract
  - Documented Publication Adapter API
  - Added usage examples for publish, rejection gate, stub fallback

### Publication Boundary

Per WSP 72 (module independence):
- **Owns**: Formatting PQN data for MoltBook, publication decision gate
- **Does NOT Own**: Retry logic, Discord webhooks (stays in moltbook_distribution_adapter)
- **Stub-Safe**: Graceful fallback records locally if MoltBook unavailable

### Publication Gate

Only accepted decisions publish:
```python
if decision.decision != "accept":
    return PublicationResult(status="rejected_decision", ...)
```

### Test Count

- Before: 41 tests (persistence)
- After: 57 tests (41 + 16 publication)
- All passing

### WSP References

- WSP 72: Module independence (wraps, doesn't duplicate)
- WSP 91: Observability (publication events traceable)
- WSP 84: Code reuse (reuses moltbook_distribution_adapter)

---

## V0.4.0 - SQLite Persistence Layer

**Slice**: `pqn_swarm_hub_persistence`
**Author**: 0102
**Date**: 2026-03-29

### Changes

- Added `src/persistence.py`:
  - `SQLiteStore` class for all 6 contract types
  - Tables: work_units, submissions, verification_decisions, contributions, participants, gate_decisions
  - Thread-safe with lock pattern (following FAMEventStore)
  - WAL mode + foreign key constraints enabled
  - `get_sqlite_store()` singleton accessor
  - `reset_sqlite_store()` for testing

- Updated service classes with optional store injection:
  - `WorkUnitRegistry(store=SQLiteStore)` — persist work units
  - `SubmissionSink(registry, store=SQLiteStore)` — persist submissions
  - `VerificationEngine(sink, store=SQLiteStore)` — persist decisions
  - `ContributionReporter(engine, store=SQLiteStore)` — persist contributions
  - `ParticipantGate(store=SQLiteStore)` — persist participants/gate decisions

- Updated exports:
  - Root `__init__.py` exports persistence classes
  - `src/__init__.py` exports persistence classes

- Added `tests/test_persistence.py`:
  - 18 tests for SQLiteStore CRUD operations
  - Service integration tests with store injection
  - Full flow persistence test

### Backward Compatibility

All services maintain backward compatibility:
- `store=None` (default) = in-memory only (Phase 0 behavior)
- `store=SQLiteStore` = memory + SQLite dual-write

### Test Count

- Before: 23 tests
- After: 41 tests (23 existing + 18 persistence)
- All passing

### WSP References

- WSP 72: Module independence
- WSP 91: Observability (persistent audit trail)
- WSP 97: Internal-first persistence before externalization

---

## V0.3.0 - Gate & FAM Adapter Integration

**Slice**: `pqn_swarm_hub_gate` + `pqn_swarm_hub_fam_adapter`
**Author**: 0102
**Date**: 2026-03-29

### WSP 97 Due Diligence

Executed WSP 97 repo strategy decision:
- **Decision**: INTEGRATED_MODULE (not separate repo)
- **Rationale**: Still-moving surfaces, FAMDaemon integration untested, exfoliation protocol mandates internal-first
- **Proto trigger**: Defined in `PROTO_EXFOLIATION_CHECKLIST.md`

### Changes

- Added `src/gate.py`:
  - `ParticipantGate` class for entry policy enforcement
  - `ParticipantIdentity` dataclass (model type, compute capacity, capability tags)
  - `GateDecision` dataclass (audit-safe decision records)
  - `ParticipantTier` enum (OBSERVER, CONTRIBUTOR, VERIFIER, COORDINATOR)
  - `ParticipantStatus` enum (PENDING, APPROVED, REJECTED, SUSPENDED)
  - Policy hooks for capability verification and WSP 00 checks
  - Phase 1: Internal-first auto-approve, external-ready structure

- Added `src/fam_adapter.py`:
  - `FAMAdapter` class for FAMDaemon integration
  - `emit_contribution_event(ContributionRecord)` — ONLY allowed emission point
  - `emit_verification_event(VerificationDecision)` — secondary audit trail
  - Lazy connection to FAMDaemon singleton
  - Stub fallback when FAMDaemon unavailable
  - `get_fam_adapter()` singleton accessor

- Updated `src/__init__.py`:
  - Exported gate contracts and services
  - Exported FAMAdapter and error types

- Updated `INTERFACE.md`:
  - Documented Phase 1 contracts (ParticipantIdentity, GateDecision)
  - Documented Phase 1 API functions (gate, FAM adapter)
  - Documented adapter boundary (HARD: allowed vs not allowed)

- Updated `ROADMAP.md`:
  - Marked gate slice complete
  - Marked adapter boundary slice complete
  - Updated next slices list

- Created `PROTO_EXFOLIATION_CHECKLIST.md`:
  - Spin-out trigger criteria
  - Current status tracking (7/10 slices, 1/3 work unit types)
  - Target future path documentation

### Adapter Boundary (HARD)

Per WSP 97 directive:
- **ALLOWED**: `emit_contribution_event()`, `emit_verification_event()`
- **NOT ALLOWED**: Direct FAM event store mutation, core control-plane imports

### Test Count

- Before: 23 tests (Phase 0 + detector bridge)
- After: 23 tests (gate/adapter tests pending)
- Gate/adapter integration tests needed

### WSP References

- WSP 72: Module independence
- WSP 91: Observability (contribution events audit-safe)
- WSP 97: Lifecycle evaluation (repo strategy decision)

---

## V0.2.0 - Detector Bridge Integration

**Slice**: `pqn_swarm_hub_detector_bridge`
**Author**: 0102

### Changes

- Added `src/detector_bridge.py`:
  - `DetectorBridge` class bridges pqn_swarm_hub to pqn_alignment detector
  - `run(work_unit)` calls `pqn_alignment.run_detector()` and parses artifacts
  - Extracts metrics from CSV (coherence) and JSONL (pqn_rate, paradox_rate, resonance_hz)
  - No changes to pqn_alignment source code (reuse only per WSP 84)

- Updated `src/submission_sink.py`:
  - Added `submit_from_detector(work_unit_id, bridge_result, submitter_id)` method
  - Extracts metrics and artifact paths from bridge output
  - Creates rESPSubmission with detector-derived data

- Added `tests/test_detector_bridge.py`:
  - 5 new tests for detector bridge integration
  - Real detector runs with truthful verification verdicts
  - Happy-path test uses manual_verify() for guaranteed contribution flow

### Metrics Derivation

From detector artifacts:
- `coherence`: mean of C column from CSV
- `pqn_rate`: PQN_DETECTED event count / steps
- `paradox_rate`: PARADOX_RISK event count / steps
- `resonance_hz`: modal frequency from RESONANCE_HIT events

### Test Count

- Before: 18 tests (Phase 0)
- After: 23 tests (18 Phase 0 + 5 detector bridge)
- All passing

### WSP References

- WSP 72: Module independence (no circular deps)
- WSP 84: Code reuse (reuses pqn_alignment detector, doesn't recreate)

---

## V0.1.0 - Initial PoC Scaffold

**Slice**: `pqn_swarm_hub_internal_poc_scaffold`
**Author**: 0102

### Changes

- Created module structure per WSP 49:
  - `README.md` - module purpose and reuse boundaries
  - `INTERFACE.md` - PoC contracts and public API
  - `ROADMAP.md` - Phase 0-3 execution plan
  - `ModLog.md` - this file
  - `src/` - source directory
  - `tests/` - test directory
  - `docs/` - additional documentation

- Defined PoC contracts:
  - `PQNWorkUnit` - bounded research task registration
  - `rESPSubmission` - structured rESP result intake
  - `VerificationDecision` - accept/reject outcome
  - `ContributionRecord` - ROC-style contribution output

- Established reuse boundaries:
  - Reuses: pqn_alignment, pqn_mcp, pqn_portal, moltbook_distribution_adapter
  - Owns: work registry, submission sink, verification, contribution reporting

### WSP References

- WSP 3: Domain placement (foundups)
- WSP 11: Interface documentation
- WSP 22: ModLog/Roadmap discipline
- WSP 49: Module structure
- WSP 72: Module independence
- WSP 84: Code reuse

### Architectural Decisions

- **Internal first**: Per exfoliation protocol, building inside monorepo before spin-out
- **Contracts first**: Defined contracts in INTERFACE.md before implementation
- **Reuse existing**: Detector engine stays in pqn_alignment, distribution stays in moltbook_distribution_adapter
- **Moltbook influence**: Social UX patterns from Moltbook, structural ownership in this FoundUp
