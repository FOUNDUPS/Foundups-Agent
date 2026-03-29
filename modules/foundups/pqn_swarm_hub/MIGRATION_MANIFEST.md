# Migration Manifest - PQN Swarm Hub

**Status**: Phase 3 COMPLETE — Migration Executed (2026-03-30)
**Created**: 2026-03-29
**Executed**: 2026-03-30
**Slice**: `pqn_swarm_hub_phase3_migration_exec`

---

## Target Repositories (LIVE)

| Repo | Role | Visibility | Status |
|------|------|------------|--------|
| `FOUNDUPS/science-swarm-hub` | origin (org repo) | public | **LIVE** |
| `Foundup/science-swarm-hub` | backup (personal repo) | private | **LIVE** |

---

## Files Migrated

### Product Code (src/)

| File | Lines | Disposition | Status |
|------|-------|-------------|--------|
| `src/__init__.py` | ~80 | MIGRATE | DONE |
| `src/contracts.py` | ~150 | MIGRATE | DONE |
| `src/registry.py` | ~100 | MIGRATE | DONE |
| `src/submission_sink.py` | ~120 | MIGRATE | DONE |
| `src/verification.py` | ~100 | MIGRATE | DONE |
| `src/contribution.py` | ~120 | MIGRATE | DONE |
| `src/gate.py` | ~300 | MIGRATE | DONE |
| `src/persistence.py` | ~400 | MIGRATE | DONE |
| `src/publication_adapter.py` | ~200 | MIGRATE | DONE |
| `src/fam_adapter.py` | ~150 | MIGRATE | DONE |
| `src/detector_bridge.py` | ~120 | MIGRATE | DONE |

**Total src/**: ~1,840 lines — MIGRATED

### Tests (tests/)

| File | Tests | Disposition | Status |
|------|-------|-------------|--------|
| `tests/__init__.py` | — | MIGRATE | DONE |
| `tests/README.md` | — | MIGRATE | DONE |
| `tests/TestModLog.md` | — | MIGRATE | DONE |
| `tests/test_contracts.py` | 13 | MIGRATE | DONE |
| `tests/test_detector_bridge.py` | 5 | MIGRATE | DONE |
| `tests/test_external_contributor.py` | 22 | MIGRATE | DONE |
| `tests/test_external_submission.py` | 14 | MIGRATE | DONE |
| `tests/test_fam_live_validation.py` | 15 | MIGRATE | DONE |
| `tests/test_persistence.py` | 18 | MIGRATE | DONE |
| `tests/test_poc_flow.py` | 5 | MIGRATE | DONE |
| `tests/test_publication_adapter.py` | 16 | MIGRATE | DONE |

**Total tests**: 108 — ALL PASSING in standalone

### Documentation

| File | Disposition | Status |
|------|-------------|--------|
| `README.md` | MIGRATE | DONE |
| `INTERFACE.md` | MIGRATE | DONE |
| `ROADMAP.md` | MIGRATE | DONE |
| `ModLog.md` | MIGRATE | DONE |
| `CONTRIBUTING.md` | MIGRATE | DONE |
| `RUNBOOK.md` | MIGRATE | DONE |
| `requirements.txt` | MIGRATE | DONE |

### Root

| File | Disposition | Status |
|------|-------------|--------|
| `__init__.py` | MIGRATE | DONE |

---

## Files Remaining in Monorepo

### Reference (Keep)

| File | Purpose |
|------|---------|
| All original files | Reference until stub cutover |

### Historical Record (Keep)

| File | Purpose |
|------|---------|
| `PROTO_EXFOLIATION_CHECKLIST.md` | Migration audit trail |
| `MIGRATION_MANIFEST.md` | This file (reference) |
| `DUAL_REMOTE_PLAN.md` | Setup reference |
| `EXFOLIATION_PLAN.md` | Procedure reference |

### Stub Cutover (DEFERRED)

| Item | Status |
|------|--------|
| Replace `__init__.py` with re-export stub | DEFERRED |
| Update `README.md` to redirect notice | DEFERRED |

---

## Standalone Repo Structure (LIVE)

```
science-swarm-hub/
├── README.md
├── INTERFACE.md
├── ROADMAP.md
├── ModLog.md
├── CONTRIBUTING.md
├── RUNBOOK.md
├── requirements.txt
├── setup.py
├── pyproject.toml
├── src/
│   └── pqn_swarm_hub/
│       ├── __init__.py
│       ├── contracts.py
│       ├── registry.py
│       ├── submission_sink.py
│       ├── verification.py
│       ├── contribution.py
│       ├── gate.py
│       ├── persistence.py
│       ├── publication_adapter.py
│       ├── fam_adapter.py
│       └── detector_bridge.py
├── tests/
│   ├── __init__.py
│   ├── README.md
│   ├── TestModLog.md
│   └── test_*.py (8 files)
└── .github/
    └── workflows/
```

---

## Monorepo Stub Structure (DEFERRED)

Stub cutover not yet executed. Module remains as reference.

```
modules/foundups/pqn_swarm_hub/
├── __init__.py           # Original (not yet stub)
├── README.md             # Updated with migration notice
├── src/                  # Original (reference)
├── tests/                # Original (reference)
├── PROTO_EXFOLIATION_CHECKLIST.md  # Historical
├── MIGRATION_MANIFEST.md           # Historical
├── DUAL_REMOTE_PLAN.md             # Historical
└── EXFOLIATION_PLAN.md             # Historical
```

---

## Dependencies Resolved

### Internal Dependencies (Adapter Strategy)

| Import | Source | Strategy | Status |
|--------|--------|----------|--------|
| `pqn_alignment.run_detector` | `modules/ai_intelligence/pqn_alignment/` | Adapter stub in standalone | DONE |
| `moltbook_distribution_adapter` | `modules/communication/moltbot_bridge/` | Adapter stub in standalone | DONE |
| `fam_daemon` | `modules/foundups/agent_market/` | Adapter stub in standalone | DONE |

### External Dependencies (requirements.txt)

```
# Core
dataclasses-json>=0.6.0

# Persistence
# (uses stdlib sqlite3)

# Testing
pytest>=8.0.0
pytest-asyncio>=1.3.0
```

---

## Migration Checklist

### Pre-Migration (COMPLETE)

- [x] MIGRATION_MANIFEST.md created
- [x] DUAL_REMOTE_PLAN.md created
- [x] EXFOLIATION_PLAN.md created
- [x] 012 approval obtained

### Migration Execution (COMPLETE)

- [x] Create `FOUNDUPS/science-swarm-hub` repo — LIVE
- [x] Create `Foundup/science-swarm-hub` repo — LIVE
- [x] Clone fresh, copy files per manifest — DONE
- [x] Create `setup.py` / `pyproject.toml` — DONE
- [x] Create adapter stubs for internal deps — DONE
- [x] Verify tests pass in standalone — 108/108 PASSING
- [x] Push to both remotes — DONE
- [ ] Update monorepo stub — DEFERRED

### Post-Migration (PARTIAL)

- [x] Verify pip installable — DONE
- [ ] Update monorepo to import from package — DEFERRED
- [x] Tag first release (v0.11.0) — DONE
- [ ] Update FOUNDUP_EXFOLIATION_PROTOCOL.md — PENDING

---

*Created: 2026-03-29*
*Last Updated: 2026-03-30 (migration executed — standalone repos live)*
