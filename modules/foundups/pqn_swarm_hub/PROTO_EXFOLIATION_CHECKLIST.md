# Proto Exfoliation Checklist - PQN Swarm Hub

**Status**: Phase 3 COMPLETE — Standalone Repos Live (2026-03-30)
**Decision**: INTEGRATED_MODULE (per WSP 97 due diligence 2026-03-29)

---

## Migration Status

### Standalone Repositories (LIVE)

| Repo | Status | URL |
|------|--------|-----|
| `FOUNDUPS/science-swarm-hub` | LIVE | https://github.com/FOUNDUPS/science-swarm-hub |
| `Foundup/science-swarm-hub` | LIVE | https://github.com/Foundup/science-swarm-hub |

### Monorepo Status

| Item | Status |
|------|--------|
| Migration executed | COMPLETE |
| Standalone tests pass | 108/108 PASSING |
| Monorepo stub cutover | COMPLETE (2026-03-30) |

---

## Gate Classification (Proto-Readiness Review 2026-03-29)

### Required for Phase 2 Entry

- [x] Phase 1 slices complete (10/10)
- [x] Contracts stable (except V3)
- [x] Core independence proven
- [x] Runbook documented

**Status**: APPROVED — Phase 2 scope: complete externalization gates below.

### Required for Exfoliation (TRUE BLOCKERS)

| Gate | Status | Slice |
|------|--------|-------|
| Live FAMDaemon validation | COMPLETE | `pqn_swarm_hub_fam_live_validation` |
| External submission type | COMPLETE | `pqn_swarm_hub_external_submission_type` |
| CONTRIBUTING.md | COMPLETE | `pqn_swarm_hub_external_contributor_path` |
| Entry gate tested with external identity | COMPLETE | `pqn_swarm_hub_external_contributor_path` |
| Shared touchpoints documented | COMPLETE | `pqn_swarm_hub_external_contributor_path` |

### Optional / Post-Proto (NOT BLOCKERS)

| Item | Rationale |
|------|-----------|
| GPD work unit type | Separate bootstrap lane, not core PQN |
| V3 consensus schema | Shapley/ZK is future scope |
| Issue/PR template | Nice-to-have, not required for first external PR |
| 3+ work unit types | Generic external type sufficient; GPD optional |

---

## Phase 1 Slices Complete

- [x] Registry (Slice 1) — `src/registry.py`
- [x] rESP Sink (Slice 2) — `src/submission_sink.py`
- [x] Verification (Slice 3) — `src/verification.py`
- [x] ROC/Contribution (Slice 4) — `src/contribution.py`
- [x] Gate (Slice 5) — `src/gate.py`
- [x] FAM Adapter (Slice 6) — `src/fam_adapter.py`
- [x] Detector Bridge — `src/detector_bridge.py`
- [x] SQLite Persistence — `src/persistence.py` (41/41 tests pass)
- [x] MoltBook Publication Adapter — `src/publication_adapter.py` (57/57 tests pass)
- [x] Runbook Documentation — `RUNBOOK.md` (reproducible execution guide)

---

## FAMDaemon Integration

- [x] FAMAdapter created with stub fallback
- [x] emit_contribution_event() tested with live FAMDaemon — 15/15 tests pass
- [x] emit_verification_event() tested with live FAMDaemon — 15/15 tests pass
- [x] Event appears in FAM event store — verified via `query_events()`
- [x] No direct core mutation detected — adapter boundary tests pass

---

## Work Unit Types

- [x] Type 1: CMST Detector (via DetectorBridge)
- [x] Type 2: External submission (generic rESP) — COMPLETE (14/14 tests)
- [ ] Type 3: GPD physics task — **optional/future**

**Note**: Generic external submission type complete. GPD is optional (separate bootstrap lane).

---

## External Contributor Path

- [x] CONTRIBUTING.md exists
- [x] Entry gate tested with external identity (22 tests in test_external_contributor.py)
- [x] Shared touchpoints documented
- [x] Stub adapter viable post-exfoliation

---

## Contracts Stable

- [x] PQNWorkUnit — stable
- [x] rESPSubmission — stable
- [x] VerificationDecision — stable
- [x] ContributionRecord — stable
- [x] ParticipantIdentity — stable (Phase 1)
- [x] GateDecision — stable (Phase 1)
- [ ] V3 consensus schema — NOT stable (optional/future)

---

## Final Status

| Criterion | Status |
|-----------|--------|
| Phase 1 slices | 10/10 COMPLETE |
| Phase 2 entry | APPROVED |
| Phase 2 slices | 3/3 COMPLETE |
| FAMDaemon live test | COMPLETE (72/72 tests) |
| External submission type | COMPLETE (14/14 tests) |
| External contributor path | COMPLETE (22/22 tests) |
| Contracts stable | YES (except V3) |
| Core independence | YES |
| Migration executed | COMPLETE |
| Standalone tests | 108/108 PASSING |
| Monorepo stub cutover | DEFERRED |

**Overall**: Phase 3 Migration COMPLETE. Standalone repos live.

---

## Phase 3 Migration Execution (2026-03-30)

### Preparation Artifacts (COMPLETE)

- [x] `MIGRATION_MANIFEST.md` — File disposition list
- [x] `DUAL_REMOTE_PLAN.md` — Repo setup commands
- [x] `EXFOLIATION_PLAN.md` — Full procedure

### Approval Gates (ALL CLEARED)

| Gate | Status |
|------|--------|
| Prep artifacts complete | COMPLETE |
| 012 approval for repo creation | APPROVED |
| 012 approval for migration push | APPROVED |

### Migration Actions (COMPLETE)

- [x] `gh repo create FOUNDUPS/science-swarm-hub` — LIVE
- [x] `gh repo create Foundup/science-swarm-hub` — LIVE
- [x] Copy files per manifest — COMPLETE
- [x] Create package structure — COMPLETE
- [x] Verify tests pass standalone — 108/108 PASSING
- [x] Push to both remotes — COMPLETE
- [x] Update monorepo stub — COMPLETE

---

## Current Path (Post-Migration)

```
FOUNDUPS/science-swarm-hub          # origin (org repo) - LIVE
Foundup/science-swarm-hub           # backup (personal repo) - LIVE
modules/foundups/pqn_swarm_hub/     # monorepo stub (cutover COMPLETE)
```

---

*Created: 2026-03-29*
*Last Updated: 2026-03-30 (stub cutover complete — exfoliation finished)*
