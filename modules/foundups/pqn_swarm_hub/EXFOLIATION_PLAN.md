# Exfoliation Plan - PQN Swarm Hub

**Status**: Phase 3 Prep (ready for 012 approval)
**Created**: 2026-03-29
**Slice**: `pqn_swarm_hub_phase3_prep_scaffold`

---

## Executive Summary

PQN Swarm Hub is ready to exfoliate from the Foundups-Agent monorepo to standalone FoundUp repositories. This plan documents the complete procedure, approval gates, and rollback strategy.

### Current State

| Criterion | Status |
|-----------|--------|
| Phase 1 (Internal PoC) | COMPLETE |
| Phase 2 (Externalization Readiness) | COMPLETE |
| True exfoliation blockers | 0 remaining |
| Test coverage | 108 tests passing |
| Architect decision | `APPROVE_PHASE_3_PREP` |

### Target State

| Repository | Purpose |
|------------|---------|
| `FOUNDUPS/pqn-swarm-hub` | Primary (origin) |
| `Foundup/pqn-swarm-hub` | Backup (mirror) |
| `modules/foundups/pqn_swarm_hub/` | Monorepo stub |

---

## Phase 3 Procedure

### Stage 1: Preparation (COMPLETE)

- [x] All Phase 2 slices complete
- [x] Architect decision recorded (`c0cf513de`)
- [x] MIGRATION_MANIFEST.md created
- [x] DUAL_REMOTE_PLAN.md created
- [x] EXFOLIATION_PLAN.md created (this file)
- [ ] 012 approval obtained

### Stage 2: Repository Creation (Blocked on 012)

**Requires explicit 012 approval.**

1. Create `FOUNDUPS/pqn-swarm-hub` (public)
2. Create `Foundup/pqn-swarm-hub` (private)

Commands in `DUAL_REMOTE_PLAN.md`.

### Stage 3: Migration Execution (Blocked on 012)

**Requires explicit 012 approval.**

1. Clone fresh working directory
2. Copy files per `MIGRATION_MANIFEST.md`
3. Restructure for Python package:
   - `src/pqn_swarm_hub/` directory
   - `pyproject.toml` for pip install
4. Create adapter stubs for internal dependencies
5. Verify tests pass in standalone
6. Initial commit and push to both remotes

### Stage 4: Monorepo Stub Update

**After successful migration.**

1. Replace `modules/foundups/pqn_swarm_hub/` contents with stub
2. Stub `__init__.py` re-exports from installed package
3. Keep historical docs (checklist, manifest, plan)
4. Update README to point to external repo

### Stage 5: Verification

1. Verify external repos accessible
2. Verify `pip install pqn-swarm-hub` works (if PyPI published)
3. Verify monorepo stub imports work
4. Tag first release (v0.11.0 or v1.0.0)

---

## Approval Gates

| Gate | Status | Approver |
|------|--------|----------|
| Phase 2 completion | APPROVED | 0102 |
| Phase 3 prep artifacts | COMPLETE | 0102 |
| Repo creation execution | PENDING | 012 |
| Migration push execution | PENDING | 012 |
| First release tag | PENDING | 012 |

---

## Adapter Stub Strategy

### Internal Dependencies

The standalone repo will have adapter stubs for monorepo dependencies:

```python
# src/pqn_swarm_hub/adapters/detector_adapter.py
"""
Adapter for pqn_alignment detector.

In monorepo: imports from modules.ai_intelligence.pqn_alignment
Standalone: stub returns mock or raises ImportError
"""

def get_detector():
    try:
        from modules.ai_intelligence.pqn_alignment import run_detector
        return run_detector
    except ImportError:
        # Standalone mode: detector not available
        def stub_detector(*args, **kwargs):
            raise ImportError(
                "pqn_alignment not available in standalone mode. "
                "Install pqn-alignment package or run in monorepo."
            )
        return stub_detector
```

Similar adapters for:
- `moltbook_distribution_adapter`
- `fam_daemon`

### Monorepo Stub

After migration, `modules/foundups/pqn_swarm_hub/__init__.py`:

```python
"""
PQN Swarm Hub - Monorepo Stub

This module has been exfoliated to:
- Origin: https://github.com/FOUNDUPS/pqn-swarm-hub
- Backup: https://github.com/Foundup/pqn-swarm-hub

Install with: pip install pqn-swarm-hub

For local development, this stub re-exports from the installed package.
"""

try:
    from pqn_swarm_hub import *
except ImportError:
    raise ImportError(
        "pqn_swarm_hub has been externalized. "
        "Install with: pip install pqn-swarm-hub"
    )
```

---

## Rollback Plan

### If Repo Creation Fails

1. Abort procedure
2. Monorepo module remains intact
3. Retry after resolving issues

### If Migration Push Fails

1. Delete external repos
2. Monorepo module remains intact
3. Investigate and retry

### If Standalone Tests Fail

1. Do NOT push to external repos
2. Fix issues in monorepo first
3. Re-run migration after fixes

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Tests fail in standalone | Low | Medium | Pre-verify locally before push |
| Import errors from adapters | Medium | Low | Adapter stubs provide graceful fallback |
| CI/CD setup issues | Low | Low | GitHub Actions workflow documented |
| Accidental monorepo breakage | Low | High | Stub tested before removing original |

---

## Success Criteria

- [ ] External repos exist and are accessible
- [ ] All 108 tests pass in standalone
- [ ] Monorepo stub imports work
- [ ] First release tagged
- [ ] Documentation updated across all locations

---

## Timeline (After 012 Approval)

| Task | Estimate |
|------|----------|
| Repo creation | 5 min |
| Migration execution | 30 min |
| Verification | 15 min |
| Monorepo stub update | 15 min |
| **Total** | **~1 hour** |

---

## Related Documents

- [MIGRATION_MANIFEST.md](MIGRATION_MANIFEST.md) — File disposition list
- [DUAL_REMOTE_PLAN.md](DUAL_REMOTE_PLAN.md) — Repo setup commands
- [PROTO_EXFOLIATION_CHECKLIST.md](PROTO_EXFOLIATION_CHECKLIST.md) — Readiness gates
- [FOUNDUP_EXFOLIATION_PROTOCOL.md](../docs/FOUNDUP_EXFOLIATION_PROTOCOL.md) — Domain policy

---

*Created: 2026-03-29*
