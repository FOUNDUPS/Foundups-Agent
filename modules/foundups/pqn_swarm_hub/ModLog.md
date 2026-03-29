# ModLog - PQN Swarm Hub FoundUp

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
