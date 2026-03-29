# ROADMAP - PQN Swarm Hub FoundUp

## Phase Plan (per Exfoliation Protocol)

### Phase 0: Internal PoC (COMPLETE)

**Goal**: Minimal scaffold with explicit contracts and one end-to-end flow.

**Deliverables**:
- [x] Module structure (README, INTERFACE, ROADMAP, ModLog)
- [x] PoC contracts defined (PQNWorkUnit, rESPSubmission, VerificationDecision, ContributionRecord)
- [x] `src/contracts.py` with dataclasses
- [x] `src/registry.py` with in-memory work unit registry
- [x] `src/submission_sink.py` with rESP intake
- [x] `src/verification.py` with accept/reject logic (φ-floor 0.618, manual override)
- [x] `src/contribution.py` with ROC reporting + durable JSON artifact
- [x] One end-to-end PoC path (register -> submit -> verify -> record) — 18/18 tests pass
- [x] Basic tests for contracts and flows

**Acceptance Criteria**: ALL MET

---

### Phase 1: Internal Proto (COMPLETE)

**Goal**: Wire to shared infrastructure and prove reproducible runbook.

**Deliverables**:
- [x] SQLite persistence for contracts — `src/persistence.py` with store injection
- [x] Integration with pqn_alignment detector via API calls — `DetectorBridge` + `submit_from_detector()`
- [x] Integration with moltbook_distribution_adapter for downstream publish — `src/publication_adapter.py`
- [x] Participant gate (who can submit to this FoundUp) — `src/gate.py`
- [x] Reproducible runbook documented — `RUNBOOK.md`
- [x] Adapter boundaries to shared infrastructure documented — `src/fam_adapter.py` + `INTERFACE.md`

**Acceptance Criteria**:
- Work units persist across restarts
- Detector results flow through submission sink
- Verified contributions publish to MoltBook
- Gate enforces participant entry policy
- Another 012/Claw can participate through stable boundaries

---

### Phase 2: Externalization Readiness (CURRENT)

**Goal**: Complete externalization gates and lock interfaces.

**Entry Approved**: 2026-03-29 (proto-readiness review)

**Deliverables**:
- [ ] Live FAMDaemon validation — `pqn_swarm_hub_fam_live_validation`
- [ ] Generic external submission type — `pqn_swarm_hub_external_submission_type`
- [ ] External contributor path — `pqn_swarm_hub_external_contributor_path`
- [ ] Interfaces frozen
- [ ] Standalone deploy path verified
- [ ] Dual-remote repo setup prepared
- [ ] Monorepo stub/adapter strategy documented

**True Blockers for Exfoliation**:
1. FAMAdapter live test with actual FAMDaemon
2. Generic external submission work-unit type (NOT GPD-specific)
3. CONTRIBUTING.md + entry gate test with external identity

**Not Blockers** (optional/future):
- GPD work unit type (separate bootstrap lane)
- V3 consensus schema (Shapley/ZK)

**Acceptance Criteria**:
- FAM events appear in live FAM store
- External submission type tested
- External contributor can request entry
- No interface-breaking changes allowed
- Module can deploy independently (with adapter stubs)
- Migration path to `FOUNDUPS/PQNSwarmHub` documented

---

### Phase 3: Spin-Out

**Goal**: Externalize to standalone FoundUp repo.

**Deliverables**:
- [ ] Create `FOUNDUPS/PQNSwarmHub` as origin
- [ ] Create `Foundup/PQNSwarmHub` as backup
- [ ] Migrate product code
- [ ] Leave monorepo bridge/docs only where needed

**Acceptance Criteria**:
- Standalone repo operational
- Monorepo bridge working
- Independent release cadence possible

---

## Current Execution Priority

**Phase 0**: COMPLETE (scaffold @ 35d1e2275)

**Phase 1 Progress**: COMPLETE
- [x] `pqn_swarm_hub_detector_bridge` — DetectorBridge wires pqn_alignment.run_detector() into submission flow
- [x] `pqn_swarm_hub_gate` — ParticipantGate with tier system, policy hooks, internal-first auto-approve
- [x] `pqn_swarm_hub_fam_adapter` — FAMAdapter with emit_contribution_event(), stub fallback
- [x] `pqn_swarm_hub_persistence` — SQLiteStore with optional store injection (41/41 tests pass)
- [x] `pqn_swarm_hub_publication_adapter` — PublicationAdapter wraps MoltBook, stub-safe (57/57 tests pass)
- [x] `pqn_swarm_hub_runbook` — Reproducible execution guide in `RUNBOOK.md`

**Phase 2 Entry**: APPROVED (2026-03-29 proto-readiness review)

**Phase 2 Slices** (ordered):
1. `pqn_swarm_hub_fam_live_validation` — Test FAMAdapter with live FAMDaemon
2. `pqn_swarm_hub_external_submission_type` — Generic work unit type for external rESP
3. `pqn_swarm_hub_external_contributor_path` — CONTRIBUTING.md + entry gate test

**Next slice**: `pqn_swarm_hub_fam_live_validation`

---

## Success Metrics

### Phase 0
- Contracts compile and import cleanly
- One end-to-end flow executes without error
- Reuse of pqn_alignment detector works

### Phase 1
- Persistence survives restart
- MoltBook publish succeeds
- Gate blocks unauthorized participants

### Phase 2
- Zero interface changes after freeze
- Standalone deploy smoke test passes

### Phase 3
- External repo accepts PRs
- Independent release shipped
