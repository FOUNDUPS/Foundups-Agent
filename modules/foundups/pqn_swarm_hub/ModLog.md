# ModLog - PQN Swarm Hub FoundUp

## V0.11.0 - Exfoliation Review Decision (Phase 3 Entry)

**Slice**: `pqn_swarm_hub_exfoliation_review_decision`
**Author**: 0102
**Date**: 2026-03-29

### Architect Decision

**Decision**: `APPROVE_PHASE_3_PREP`

**Rationale**:
- All true exfoliation blockers cleared (3/3 Phase 2 slices complete)
- Interfaces stable (except V3 consensus — future scope)
- 108 tests passing across full module
- External contributor path documented and tested (22 gate tests)
- Standalone deploy path verified (stub-safe adapters)
- Monorepo stub strategy documented

**Rejected Alternatives**:
- `DEFER_WITH_ONE_CORRECTIVE_SLICE`: Not needed — doc reconciliation completed in this slice
- `REMAIN_INTEGRATED_BY_DESIGN`: Not applicable — blockers are cleared

### Stale Doc Reconciliation

Updated in this slice:

1. `ROADMAP.md`:
   - Phase 2 → COMPLETE
   - All Phase 2 deliverable checkboxes updated
   - Next phase → Phase 3 Prep

2. `RUNBOOK.md`:
   - Version → Phase 2 Complete
   - Test count → 108 passed
   - Operator notes → Ready for exfoliation review

### Next Slice

`pqn_swarm_hub_phase3_prep_scaffold`:
- Create dual-remote repo setup
- Prepare migration script
- Design monorepo stub adapter

### WSP References

- WSP 97: Lifecycle evaluation (exfoliation decision)
- WSP 22: Documentation discipline (doc reconciliation)

---

## V0.10.0 - External Contributor Path (Phase 2 Complete)

**Slice**: `pqn_swarm_hub_external_contributor_path`
**Author**: 0102
**Date**: 2026-03-29

### Changes

- Created `CONTRIBUTING.md`:
  - Path 1: Internal flow (detector bridge) documentation
  - Path 2: External flow (generic submission) with full code examples
  - Required artifacts and evidence (metrics, config, artifacts)
  - Gate expectations for proto stage (auto-approve Phase 1)
  - Stub-safe adapters (FAMDaemon, MoltBook)
  - What is NOT guaranteed (proto stage limitations)
  - Verification thresholds (coherence >= 0.618)
  - Smoke test example

- Created `tests/test_external_contributor.py` (22 tests):
  - `TestExternalIdentityDeclaration` (3 tests): Identity creation, deterministic IDs
  - `TestExternalGateEvaluation` (5 tests): Gate entry, auto-approve, tier assignment, permissions
  - `TestExternalContributorFullFlow` (3 tests): End-to-end flow, deterministic IDs, no operator context
  - `TestExternalContributorPersistence` (3 tests): Identity, decision, full flow persistence
  - `TestGatePolicyHooks` (4 tests): Optional capability/WSP00 hooks, rejection paths
  - `TestExternalContributorEdgeCases` (4 tests): Low coherence rejection, multiple contributors, suspension/reinstatement

- Updated `README.md`:
  - Status: Phase 1 Complete → Phase 2 Complete
  - Added CONTRIBUTING.md link to Links section

- Updated `PROTO_EXFOLIATION_CHECKLIST.md`:
  - All true blockers marked COMPLETE
  - Status: Ready for exfoliation review

### External Contributor Path Validation

```python
# External contributor can complete full flow without operator context
identity = ParticipantIdentity(display_name="external_researcher", model_type="human")
gate.request_entry(identity, requested_tier=ParticipantTier.CONTRIBUTOR)  # auto-approve
work_unit = registry.register_external("External work", {}, identity.participant_id)
submission = sink.submit_external(work_unit.work_unit_id, identity.participant_id, {"coherence": 0.75, "pqn_rate": 0.05})
decision = engine.auto_verify(submission.submission_id)  # accept
contribution = reporter.record(work_unit.work_unit_id, submission.submission_id, decision.decision_id, identity.participant_id, 0.85)
```

### Test Count

- Before: 86 tests (Phase 1 + FAM + external submission)
- After: 108 tests (86 + 22 external contributor)
- All passing

### Phase 2 Status

- [x] `pqn_swarm_hub_fam_live_validation` — COMPLETE (15 tests)
- [x] `pqn_swarm_hub_external_submission_type` — COMPLETE (14 tests)
- [x] `pqn_swarm_hub_external_contributor_path` — COMPLETE (22 tests)

**Phase 2 COMPLETE**: All true blockers cleared. Ready for exfoliation review.

### WSP References

- WSP 5: >=90% test coverage for public API
- WSP 97: External contributor path validation for proto-readiness
- WSP 22: Documentation discipline (CONTRIBUTING.md)

---

## V0.9.0 - External Submission Type (Phase 2 Gate 2)

**Slice**: `pqn_swarm_hub_external_submission_type`
**Author**: 0102
**Date**: 2026-03-29

### Changes

- Updated `src/contracts.py`:
  - Added `source: str = "internal"` field to `PQNWorkUnit`
  - Added `source: str = "internal"` field to `rESPSubmission`
  - Default "internal" for detector bridge, "external" for external submissions

- Updated `src/registry.py`:
  - Added `source` parameter to `register()` method
  - Added `register_external()` convenience method (sets source="external")

- Updated `src/submission_sink.py`:
  - Added `source` parameter to `submit()` method
  - Added `submit_external()` convenience method (sets source="external")

- Updated `src/persistence.py`:
  - Added `source` column to work_units table schema
  - Added `source` column to submissions table schema
  - Added `_migrate_source_columns()` for existing databases
  - Updated save/get methods to handle source field

- Added `tests/test_external_submission.py` (14 tests):
  - External work unit registration tests
  - External submission tests
  - Full external flow (register -> submit -> verify -> contribution)
  - Persistence round-trip for source field
  - Contract source field defaults

### External Submission API

```python
# Register external work unit
work_unit = registry.register_external(
    description="External GPD result",
    config={"tool": "gpd", "version": "2.0"},
    creator_id="external_contributor_001",
)
# work_unit.source == "external"

# Submit external results
submission = sink.submit_external(
    work_unit_id=work_unit.work_unit_id,
    submitter_id="external_contributor_001",
    metrics={"coherence": 0.75, "custom_metric": 42},
)
# submission.source == "external"
```

### Test Count

- Before: 72 tests (Phase 1 + FAM live validation)
- After: 86 tests (72 + 14 external submission)
- All passing

### Phase 2 Progress

- [x] `pqn_swarm_hub_fam_live_validation` — COMPLETE (15 tests)
- [x] `pqn_swarm_hub_external_submission_type` — COMPLETE (14 tests)
- [ ] `pqn_swarm_hub_external_contributor_path` — NEXT

**True blockers remaining**: 1 (external contributor path)

### WSP References

- WSP 72: Module independence (generic external type, not tool-specific)
- WSP 97: Lifecycle evaluation (externalization gate)
- WSP 84: Code reuse (extends existing contracts minimally)

---

## V0.8.0 - FAM Live Validation (Phase 2 Gate 1)

**Slice**: `pqn_swarm_hub_fam_live_validation`
**Author**: 0102
**Date**: 2026-03-29

### Changes

- Added `tests/test_fam_live_validation.py` (15 tests):
  - Live FAMDaemon connection tests
  - `emit_contribution_event()` live emission and store verification
  - `emit_verification_event()` live emission and store verification
  - Adapter boundary tests (no direct mutation)
  - Full flow integration tests
  - FAM store statistics verification

### Validation Evidence

| Test | Result |
|------|--------|
| emit_contribution_event() with live FAMDaemon | PASS |
| emit_verification_event() with live FAMDaemon | PASS |
| Events appear in FAM event store | PASS |
| Adapter uses only emit() interface | PASS |
| No direct event store access | PASS |

### Test Count

- Before: 57 tests (Phase 1)
- After: 72 tests (57 + 15 FAM live validation)
- All passing

### Phase 2 Progress

- [x] `pqn_swarm_hub_fam_live_validation` — COMPLETE
- [ ] `pqn_swarm_hub_external_submission_type` — NEXT
- [ ] `pqn_swarm_hub_external_contributor_path` — PENDING

**True blockers remaining**: 2 (external submission type, contributor path)

### WSP References

- WSP 72: Module independence (adapter boundary respected)
- WSP 91: Observability (contribution events audit-safe)
- WSP 97: Lifecycle evaluation (externalization gate)

---

## V0.7.0 - Proto-Readiness Review (Phase 2 Entry)

**Slice**: `pqn_swarm_hub_proto_readiness_review`
**Author**: 0102
**Date**: 2026-03-29

### Review Decision

- **Phase 2 Entry**: APPROVED
- **Exfoliation**: NOT APPROVED (3 true blockers remain)

### Gate Classification

**True Blockers for Externalization**:
1. Live FAMDaemon validation (adapter created, live test pending)
2. Generic external submission type (NOT GPD-specific)
3. External contributor path (CONTRIBUTING.md + entry gate test)

**Not Blockers** (optional/future):
- GPD work unit type — separate bootstrap lane, not core PQN
- V3 consensus schema — Shapley/ZK is future scope
- 3+ work unit types — generic external type sufficient

### Next Implementation Order

1. `pqn_swarm_hub_fam_live_validation`
2. `pqn_swarm_hub_external_submission_type`
3. `pqn_swarm_hub_external_contributor_path`

### Updated Files

- `PROTO_EXFOLIATION_CHECKLIST.md` — Gate classification added
- `ROADMAP.md` — Phase 2 entry approved, deliverables ordered
- `ACTIVE_SLICE_LEDGER.md` — Review closed, Phase 2 slices opened

### WSP References

- WSP 97: Lifecycle evaluation (proto-readiness gates)
- WSP 22: Documentation discipline (review as ModLog entry)

---

## V0.6.0 - Runbook (Phase 1 Complete)

**Slice**: `pqn_swarm_hub_runbook`
**Author**: 0102
**Date**: 2026-03-29

### Changes

- Added `RUNBOOK.md`:
  - Reproducible execution guide for another 0102/operator
  - Flow A: In-memory happy path
  - Flow B: SQLite-backed persistence path
  - Flow C: Stub-safe publication path
  - Flow D: Participant gate path
  - Flow E: Detector bridge path
  - Expected artifacts documentation
  - Validation commands (pytest, smoke tests)
  - Failure modes and recovery
  - Operator notes for Phase 1 vs Proto-only

- Updated `README.md`:
  - Status: Phase 0 → Phase 1 Complete
  - Added RUNBOOK.md and INTERFACE.md links

- Updated `ROADMAP.md`:
  - Marked runbook deliverable complete
  - Phase 1: CURRENT → COMPLETE
  - Phase 2 entry: Awaiting proto-readiness review

### Phase 1 Status

**COMPLETE** (10/10 slices):
1. Registry + contracts (V0.1.0)
2. Submission sink (V0.1.0)
3. Verification engine (V0.1.0)
4. Contribution reporter (V0.1.0)
5. Detector bridge (V0.2.0)
6. Participant gate (V0.3.0)
7. FAM adapter (V0.3.0)
8. SQLite persistence (V0.4.0)
9. Publication adapter (V0.5.0)
10. Runbook (V0.6.0)

### WSP References

- WSP 22: Documentation discipline (runbook as phase closure artifact)
- WSP 97: Internal-first proto before externalization

---

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
