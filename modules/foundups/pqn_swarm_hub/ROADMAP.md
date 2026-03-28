# ROADMAP - PQN Swarm Hub FoundUp

## Phase Plan (per Exfoliation Protocol)

### Phase 0: Internal PoC (CURRENT)

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

**Acceptance Criteria**:
- At least one PQN work unit can be registered
- At least one rESP submission can be made
- Verification can distinguish accepted vs rejected
- A durable result artifact is written
- ROC-style contribution reporting exists for accepted work

---

### Phase 1: Internal Proto

**Goal**: Wire to shared infrastructure and prove reproducible runbook.

**Deliverables**:
- [ ] SQLite persistence for contracts
- [ ] Integration with pqn_alignment detector via API calls
- [ ] Integration with moltbook_distribution_adapter for downstream publish
- [ ] Participant gate (who can submit to this FoundUp)
- [ ] Reproducible runbook documented
- [ ] Adapter boundaries to shared infrastructure documented

**Acceptance Criteria**:
- Work units persist across restarts
- Detector results flow through submission sink
- Verified contributions publish to MoltBook
- Gate enforces participant entry policy
- Another 012/Claw can participate through stable boundaries

---

### Phase 2: Externalization Readiness

**Goal**: Lock interfaces and verify standalone deploy path.

**Deliverables**:
- [ ] Interfaces frozen
- [ ] Standalone deploy path verified
- [ ] Dual-remote repo setup prepared
- [ ] Monorepo stub/adapter strategy documented

**Acceptance Criteria**:
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

**Phase 0 PoC Slice** (this scaffold):
1. Module structure created
2. Contracts defined in INTERFACE.md
3. Reuse boundaries explicit
4. Minimal end-to-end path specified

**Next Slice** (Phase 0 implementation):
1. Implement `src/contracts.py` with dataclasses
2. Implement in-memory registry
3. Write one end-to-end test
4. Prove the PoC acceptance criteria

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
