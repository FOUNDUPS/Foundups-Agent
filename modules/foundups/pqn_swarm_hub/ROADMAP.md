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
- [x] `src/verification.py` with accept/reject logic (rho-floor 0.618, manual override)
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

### Phase 2: Externalization Readiness (COMPLETE)

**Goal**: Complete externalization gates and lock interfaces.

**Entry Approved**: 2026-03-29 (proto-readiness review)
**Phase Complete**: 2026-03-29 (exfoliation review decision)

**Deliverables**:
- [x] Live FAMDaemon validation — `pqn_swarm_hub_fam_live_validation` (15/15 tests)
- [x] Generic external submission type — `pqn_swarm_hub_external_submission_type` (14/14 tests)
- [x] External contributor path — `pqn_swarm_hub_external_contributor_path` (22/22 tests)
- [x] Interfaces frozen (except V3 consensus — future scope)
- [x] Standalone deploy path verified (RUNBOOK.md + stub-safe adapters)
- [x] Dual-remote repo setup prepared — **Phase 3 scope**
- [x] Monorepo stub/adapter strategy documented (PROTO_EXFOLIATION_CHECKLIST.md)

**True Blockers for Exfoliation**: ALL CLEARED
1. ~~FAMAdapter live test with actual FAMDaemon~~ — COMPLETE
2. ~~Generic external submission work-unit type~~ — COMPLETE
3. ~~CONTRIBUTING.md + entry gate test with external identity~~ — COMPLETE

**Not Blockers** (optional/future):
- GPD work unit type (separate bootstrap lane)
- V3 consensus schema (Shapley/ZK)

**Acceptance Criteria**: ALL MET
- FAM events appear in live FAM store
- External submission type tested (14 tests)
- External contributor can request entry (22 tests)
- No interface-breaking changes after freeze
- Module can deploy independently (with adapter stubs)
- Migration path to `FOUNDUPS/science-swarm-hub` documented

---

### Phase 3: Spin-Out (MIGRATION COMPLETE)

**Goal**: Externalize to standalone FoundUp repo.

**Phase 3 Prep** (2026-03-29):
- [x] `MIGRATION_MANIFEST.md` — file disposition list
- [x] `DUAL_REMOTE_PLAN.md` — repo setup commands
- [x] `EXFOLIATION_PLAN.md` — full procedure with rollback
- [x] 012 approval for execution — **APPROVED**

**Migration Execution** (2026-03-30):
- [x] Create `FOUNDUPS/science-swarm-hub` as origin — **LIVE**
- [x] Create `Foundup/science-swarm-hub` as backup — **LIVE**
- [x] Migrate product code per manifest — **COMPLETE**
- [x] Standalone tests pass — **108/108 PASSING**
- [x] Monorepo stub cutover — **COMPLETE** (2026-03-30)

**Acceptance Criteria**:
- [x] Standalone repo operational
- [x] All 108 tests pass standalone
- [x] Monorepo stub imports from external package — COMPLETE
- [x] Independent release cadence possible

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

**Phase 2**: COMPLETE (2026-03-29 exfoliation review decision)

**Phase 2 Slices** (all complete):
1. ~~`pqn_swarm_hub_fam_live_validation`~~ — COMPLETE (15/15 tests)
2. ~~`pqn_swarm_hub_external_submission_type`~~ — COMPLETE (14/14 tests)
3. ~~`pqn_swarm_hub_external_contributor_path`~~ — COMPLETE (22/22 tests)

**Total tests**: 108 passing

**Phase 3**: COMPLETE (2026-03-30 migration executed)

**Standalone Repos**:
- Origin: https://github.com/FOUNDUPS/science-swarm-hub
- Backup: https://github.com/Foundup/science-swarm-hub

**Status**: Exfoliation COMPLETE — monorepo stub cutover executed 2026-03-30

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
- [x] External repo accepts PRs
- [x] Independent release shipped
- [x] Monorepo stub cutover — COMPLETE
