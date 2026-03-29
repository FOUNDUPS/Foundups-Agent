# Proto Exfoliation Checklist - PQN Swarm Hub

**Status**: Internal PoC → Proto gate tracking
**Decision**: INTEGRATED_MODULE (per WSP 97 due diligence 2026-03-29)

---

## Spin-Out Trigger Criteria

All criteria must be TRUE before exfoliation to standalone repo.

### Phase 1 Slices Complete

- [x] Registry (Slice 1) — `src/registry.py`
- [x] rESP Sink (Slice 2) — `src/submission_sink.py`
- [x] Verification (Slice 3) — `src/verification.py`
- [x] ROC/Contribution (Slice 4) — `src/contribution.py`
- [x] Gate (Slice 5) — `src/gate.py`
- [x] FAM Adapter (Slice 6) — `src/fam_adapter.py`
- [x] Detector Bridge — `src/detector_bridge.py`
- [ ] SQLite Persistence — `src/persistence.py` (not started)
- [ ] MoltBook Publication Adapter — integration (not started)
- [ ] Runbook Documentation — reproducible execution guide

### FAMDaemon Integration Proven

- [x] FAMAdapter created with stub fallback
- [ ] emit_contribution_event() tested with live FAMDaemon
- [ ] emit_verification_event() tested with live FAMDaemon
- [ ] Event appears in FAM event store
- [ ] No direct core mutation detected

### 3+ Work Unit Types Supported

- [x] Type 1: CMST Detector (via DetectorBridge)
- [ ] Type 2: GPD physics task
- [ ] Type 3: External submission (generic rESP)

### External Contributor Path Validated

- [ ] CONTRIBUTING.md exists
- [ ] Issue/PR template exists
- [ ] Entry gate tested with external identity
- [ ] Documentation sufficient for onboarding

### Contracts Stable Enough to Freeze

- [x] PQNWorkUnit — stable
- [x] rESPSubmission — stable
- [x] VerificationDecision — stable
- [x] ContributionRecord — stable
- [x] ParticipantIdentity — stable (Phase 1)
- [x] GateDecision — stable (Phase 1)
- [ ] V3 consensus schema — NOT stable (Shapley/ZK future)

### No Core Changes Required for External PRs

- [x] Adapter boundary respected
- [x] No imports from core control-plane beyond stable interfaces
- [ ] All shared touchpoints documented
- [ ] Stub adapter remains viable post-exfoliation

---

## Current Status

| Criterion | Status |
|-----------|--------|
| Phase 1 slices | 7/10 complete |
| FAMDaemon integration | PARTIAL (adapter created, live test pending) |
| 3+ work unit types | 1/3 |
| External contributor path | NOT VALIDATED |
| Contracts stable | YES (except V3) |
| Core independence | YES |

**Overall**: NOT READY for exfoliation

---

## Target Future Path (Post-Proto)

```
FOUNDUPS/pqn-swarm-hub          # origin (org repo)
Foundup/pqn-swarm-hub           # backup (personal repo)
modules/foundups/pqn_swarm_hub/ # adapter stub remains in monorepo
```

---

## Next Steps to Proto

1. Complete SQLite persistence slice
2. Test FAMAdapter with live FAMDaemon
3. Add GPD work unit type
4. Create CONTRIBUTING.md
5. Document runbook
6. Revalidate this checklist

---

*Created: 2026-03-29*
*Last Updated: 2026-03-29*
