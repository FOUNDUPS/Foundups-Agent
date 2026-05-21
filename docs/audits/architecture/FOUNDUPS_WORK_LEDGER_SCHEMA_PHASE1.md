# FoundUps Work Ledger Schema — Phase 1

**Date**: 2026-05-21
**Window**: W9
**Slice**: FOUNDUPS_WORK_LEDGER_SCHEMA_PHASE1
**Base Commit**: `a763a15a1` (origin/main with PR #642 merged)
**Branch**: `docs/foundups-work-ledger-schema-phase1`
**Mode**: SCHEMA_ONLY / DOCS_ONLY

---

## WSP 97 Truth Boundary Labels

| Label | Status |
|-------|--------|
| WORK_LEDGER_SCHEMA_ONLY | YES |
| NO_RUNTIME_CHANGE | YES |
| NO_AGENTDB_MUTATION | YES |
| NO_HOLOINDEX_MUTATION | YES |
| NO_REGISTRY_MUTATION | YES |
| NO_PR_MUTATION | YES |
| NO_SQLITE_IMPLEMENTATION | YES |
| NO_WORK_QUEUE_MUTATION | YES |
| NO_CABR_READY | YES |
| NO_PAYOUT_READY | YES |
| NO_DAO_ACTIVATION | YES |

---

## 1. Purpose

Create the first typed, machine-readable work ledger schema that unifies existing Brain / work-tracking artifacts without replacing runtime systems.

---

## 2. Source Artifacts Unified

| Artifact | Location | Role |
|----------|----------|------|
| ACTIVE_SLICE_LEDGER.md | `docs/0102_session_briefings/ACTIVE_SLICE_LEDGER.md` | Manual work ledger (96 closed, 8 open slices) |
| BACKUP_UNIQUE_WORK_LEDGER | `docs/0102_session_briefings/BACKUP_UNIQUE_WORK_LEDGER_PHASE1.md` | Backup branch work tracking |
| Brain Artifact Index | `WSP_knowledge/reasoning_traces/brain_artifact_index.json` | Indexed reasoning traces |
| FoundUp Registry | `modules/foundups/foundup_registry.json` | Product/entity registry with `next_slice` field |
| Registry Schema | `modules/foundups/foundup_registry.schema.json` | Schema pattern reference |
| Brain Audit | `docs/audits/architecture/FOUNDUPS_WORK_LEDGER_BRAIN_CURRENT_STATE_AUDIT_PHASE1.md` | Gap analysis and field recommendations |

---

## 3. HoloIndex Assessment

### 3.1 Queries Executed

| Query | Hits | Quality |
|-------|------|---------|
| `work ledger Brain active slice ledger schema WSP 15 WSP 60 WSP 70` | 32 | GOOD — found ACTIVE_SLICE_LEDGER, WSP 60 |
| `FoundUps work ledger AgentDB branch PR slice status worker packet` | 32 | GOOD — found worker_queue_observability, worker_assignment_protocol |
| `ACTIVE_SLICE_LEDGER backup unique work ledger brain artifact index` | 32 | EXCELLENT — found both ledgers, epoch_ledger |

### 3.2 Fallback rg Required

**NO** — HoloIndex semantic search returned all required artifacts.

---

## 4. Design Decisions

### 4.1 Core Decisions

| Decision | Rationale |
|----------|-----------|
| Ledger schema is source-of-truth candidate, not yet authoritative runtime state | Allows validation before making authoritative |
| ACTIVE_SLICE_LEDGER remains human-readable projection until migration | Preserves existing workflow |
| AgentDB remains runtime task/breadcrumb store, not replaced | Different abstraction layer |
| FoundUp registry remains product/entity registry, not work ledger | Different purpose |
| W10 PR reports should become future ingestion source, but not in this slice | Scoped to schema only |
| HoloIndex should index ledger docs/schema after merge, but no reindex in this slice | Avoids mutation |

### 4.2 Schema Design Principles

1. **Unify, don't replace**: Schema accommodates all existing artifact structures
2. **Status lifecycle**: 11 states covering full slice lifecycle
3. **WSP 15 integration**: Native `wsp15_score` object with dimension breakdown
4. **Provenance tracking**: `source` field captures origin (audit, pr_review, brain_artifact, etc.)
5. **Dependency modeling**: `blocked_by`, `supersedes`, `superseded_by` for DAG relationships
6. **Evidence linking**: `evidence_docs`, `holoindex_queries` for traceability

---

## 5. Schema Summary

### 5.1 Files Created

| File | Purpose | Lines |
|------|---------|-------|
| `docs/0102_session_briefings/work_ledger.schema.json` | JSON Schema (Draft 2020-12) | ~200 |
| `docs/0102_session_briefings/work_ledger.example.json` | Example entries | ~150 |

### 5.2 Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `slice_id` | string | Unique identifier (pattern: `^[A-Z0-9_]+$`) |
| `title` | string | Human-readable title |
| `status` | enum | Lifecycle status |
| `created_at` | datetime | Creation timestamp |

### 5.3 Optional Fields (25 total)

| Category | Fields |
|----------|--------|
| Assignment | `lane`, `owner_worker`, `priority`, `wsp15_score` |
| Git | `branch`, `worktree`, `base_commit`, `head_commit`, `merge_commit` |
| GitHub | `pr_number` |
| Relations | `related_foundup_id`, `related_wsp`, `blocked_by`, `supersedes`, `superseded_by`, `next_slice` |
| Evidence | `evidence_docs`, `holoindex_queries`, `wsp_97_labels` |
| Timestamps | `updated_at`, `last_verified_at` |
| Provenance | `source` |

### 5.4 Status Enum Values

| Status | Description |
|--------|-------------|
| PROPOSED | Identified but not yet assigned |
| ASSIGNED | Worker assigned, not started |
| IN_PROGRESS | Actively being worked |
| STAGED_FOR_W10 | Ready for W10 review |
| PR_OPEN | PR created, awaiting merge |
| MERGED | PR merged to main |
| BLOCKED | Waiting on dependency |
| PARKED | Intentionally paused |
| SUPERSEDED | Replaced by another slice |
| CLOSED | Complete (non-PR path) |
| ABANDONED | Will not be completed |

---

## 6. Validation Results

| Test | Result |
|------|--------|
| Schema is valid JSON Schema Draft 2020-12 | PASS |
| Example validates against schema | PASS |
| All slices have required fields | PASS |
| All statuses are valid enum values | PASS |
| `related_foundup_id` can be null or string | PASS |
| `wsp_97_labels` are arrays of strings | PASS |
| No runtime imports required | PASS |

---

## 7. WSP Coverage

| WSP | How Schema Supports |
|-----|---------------------|
| WSP 15 | Native `wsp15_score` object with dimension breakdown + `priority` enum |
| WSP 22 | `evidence_docs` links to ModLog entries |
| WSP 60 | Schema can be indexed by HoloIndex memory architecture |
| WSP 70 | `status` + `last_verified_at` enable system status reporting |
| WSP 97 | `wsp_97_labels` array per slice |

---

## 8. What This Slice Does NOT Do

| Action | Why Not |
|--------|---------|
| Modify AgentDB | Different abstraction layer, not replaced |
| Modify HoloIndex | No reindex in this slice |
| Migrate ACTIVE_SLICE_LEDGER | Future slice after validation |
| Implement SQLite | Schema-only phase |
| Create runtime ingestion | Future slice |
| Mutate FoundUp registry | Registry is separate concern |
| Change PRs/branches/GitHub state | Read-only audit |

---

## 9. Next Slices

### 9.1 Primary (Immediate)

| Slice ID | Purpose |
|----------|---------|
| `FOUNDUPS_WORK_LEDGER_HOLOINDEX_INDEXING_SPEC_PHASE1` | Spec HoloIndex indexing of ledger entries |

### 9.2 Secondary (Follow-on)

| Slice ID | Purpose |
|----------|---------|
| `FOUNDUPS_WORK_LEDGER_AGENTDB_SYNC_AUDIT_PHASE1` | Audit AgentDB breadcrumb sync potential |
| `FOUNDUPS_WORK_LEDGER_W10_INGESTION_SPEC_PHASE1` | Spec automated W10 merge report ingestion |
| `FOUNDUPS_WORK_LEDGER_MIGRATION_PHASE1` | Migrate ACTIVE_SLICE_LEDGER entries to JSON |

---

## 10. Summary

### 10.1 Key Deliverables

1. **work_ledger.schema.json** — JSON Schema Draft 2020-12 with 29 fields
2. **work_ledger.example.json** — 5 example entries covering status lifecycle
3. **This audit document** — Design decisions and validation

### 10.2 W10 Readiness

| Gate | Status |
|------|--------|
| Schema created | YES |
| Example validates | YES |
| Tests pass | YES |
| No runtime changes | YES |
| No mutations | YES |
| Ready for PR | YES |

---

## Appendix A: File Evidence

| File | Purpose | Status |
|------|---------|--------|
| `docs/0102_session_briefings/work_ledger.schema.json` | Schema definition | CREATED |
| `docs/0102_session_briefings/work_ledger.example.json` | Example entries | CREATED |
| `docs/0102_session_briefings/ACTIVE_SLICE_LEDGER.md` | Source artifact | READ |
| `docs/0102_session_briefings/BACKUP_UNIQUE_WORK_LEDGER_PHASE1.md` | Source artifact | READ |
| `WSP_knowledge/reasoning_traces/brain_artifact_index.json` | Source artifact | READ |
| `modules/foundups/foundup_registry.schema.json` | Pattern reference | READ |
| `docs/audits/architecture/FOUNDUPS_WORK_LEDGER_BRAIN_CURRENT_STATE_AUDIT_PHASE1.md` | Field recommendations | READ |

---

**Audit Complete**: 2026-05-21
**Auditor**: W9
**WSP 97 Verdict**: PASS — schema/docs only, no mutations
**Next Slice**: FOUNDUPS_WORK_LEDGER_HOLOINDEX_INDEXING_SPEC_PHASE1
**W10 Readiness**: APPROVED for PR
