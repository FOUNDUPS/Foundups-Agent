# Proto Exfoliation Checklist - PQN Swarm Hub

**Status**: Phase 2 Complete → Exfoliation Review Ready (2026-03-29)
**Decision**: INTEGRATED_MODULE (per WSP 97 due diligence 2026-03-29)

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

## Current Status

| Criterion | Status |
|-----------|--------|
| Phase 1 slices | 10/10 COMPLETE |
| Phase 2 entry | APPROVED |
| FAMDaemon live test | COMPLETE (72/72 tests) |
| External submission type | COMPLETE (14/14 tests) |
| External contributor path | COMPLETE (22/22 tests) |
| Contracts stable | YES (except V3) |
| Core independence | YES |

**Overall**: Phase 2 COMPLETE. READY for exfoliation review (0 true blockers remain).

---

## Next Implementation Order (Phase 2)

1. ~~`pqn_swarm_hub_fam_live_validation`~~ — COMPLETE (15/15 tests)
2. ~~`pqn_swarm_hub_external_submission_type`~~ — COMPLETE (14/14 tests)
3. ~~`pqn_swarm_hub_external_contributor_path`~~ — COMPLETE (22/22 tests)

**Phase 2 COMPLETE**: All true blockers cleared. Ready for exfoliation review.

---

## Target Future Path (Post-Proto)

```
FOUNDUPS/pqn-swarm-hub          # origin (org repo)
Foundup/pqn-swarm-hub           # backup (personal repo)
modules/foundups/pqn_swarm_hub/ # adapter stub remains in monorepo
```

---

*Created: 2026-03-29*
*Last Updated: 2026-03-29 (Phase 2 complete — external contributor path)*
