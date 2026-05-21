# FoundUps Work Ledger HoloIndex Indexing Spec — Phase 1

**Date**: 2026-05-21
**Window**: W9
**Slice**: FOUNDUPS_WORK_LEDGER_HOLOINDEX_INDEXING_SPEC_PHASE1
**Base Commit**: `abd26b56f` (origin/main with PR #643 merged)
**Branch**: `docs/foundups-work-ledger-holoindex-indexing-spec-phase1`
**Mode**: SPEC_ONLY / DOCS_ONLY

---

## WSP 97 Truth Boundary Labels

| Label | Status |
|-------|--------|
| DOCS_ONLY | YES |
| SPEC_ONLY | YES |
| NO_HOLOINDEX_MUTATION | YES |
| NO_REINDEX | YES |
| NO_RUNTIME_CHANGE | YES |
| NO_LEDGER_MUTATION | YES |
| NO_AGENTDB_MUTATION | YES |
| NO_REGISTRY_MUTATION | YES |
| NO_CABR_READY | YES |
| NO_PAYOUT_READY | YES |
| NO_DAO_ACTIVATION | YES |

---

## 1. Purpose

Specify how HoloIndex should index and retrieve the new work ledger artifacts without mutating HoloIndex in this slice. This spec enables future implementation while maintaining WSP 97 truth boundaries.

---

## 2. HoloIndex Assessment

### 2.1 Queries Executed

| Query | Hits | Quality |
|-------|------|---------|
| `work ledger schema HoloIndex indexing active slice ledger worker packet` | 32 | GOOD — found holoindex_plugin, ACTIVE_SLICE_LEDGER |
| `HoloIndex indexing JSON schema metadata slice_id status priority branch PR` | 32 | GOOD — found indexing gap reports, holo_adapter |
| `Brain audit work ledger HoloIndex retrieval worker queue WSP 15` | 32 | GOOD — found worker_queue_observability, audit docs |

### 2.2 Fallback rg Required

**NO** — HoloIndex semantic search returned relevant artifacts.

### 2.3 Key Findings from Current Architecture

| Component | Location | Relevance |
|-----------|----------|-----------|
| ChromaDB backend | `holo_index/core/holo_index.py` | Vector storage, 20K entry limit |
| Priority roots | `HIA6A_INDEXING_GAP_FIX_REPORT.md` | Traversal order matters |
| TurboQuant opt-in | `HOLO_USE_TURBOQUANT` env | Semantic backend switch |
| Agentic RAG | `holo_index/core/agentic_rag_verdict.py` | Quality scoring |

---

## 3. Audit/Spec Questions and Answers

### 3.1 Which ledger files should HoloIndex index?

| File | Index As | Priority |
|------|----------|----------|
| `docs/0102_session_briefings/work_ledger.example.json` | Structured work-state data | P1 |
| `docs/0102_session_briefings/work_ledger.schema.json` | Schema reference (docs) | P2 |
| `docs/0102_session_briefings/ACTIVE_SLICE_LEDGER.md` | Legacy human-readable (docs) | P3 |
| `docs/0102_session_briefings/BACKUP_UNIQUE_WORK_LEDGER_PHASE1.md` | Archive reference (docs) | P3 |

**Recommendation**: `work_ledger.example.json` becomes the authoritative indexed source once populated with real data. Until then, ACTIVE_SLICE_LEDGER.md remains the human-readable source.

### 3.2 How should schema and example be indexed?

| File | Indexing Type | Rationale |
|------|---------------|-----------|
| `work_ledger.schema.json` | **Docs only** | Schema defines structure, not current state |
| `work_ledger.example.json` | **Structured metadata extraction** | Contains current work state |

**Metadata extraction from `work_ledger.example.json`**:
- Parse JSON on index
- Extract each slice entry as a searchable document
- Embed slice metadata as ChromaDB metadata fields

### 3.3 Which fields should become searchable metadata?

| Field | Metadata Type | Searchable | Filter |
|-------|---------------|------------|--------|
| `slice_id` | string | YES | YES |
| `lane` | string | YES | YES |
| `priority` | enum | YES | YES |
| `status` | enum | YES | YES |
| `owner_worker` | string | YES | YES |
| `source` | enum | YES | YES |
| `branch` | string | YES | YES |
| `pr_number` | integer | YES | YES |
| `related_foundup_id` | string | YES | YES |
| `related_wsp` | array | YES (joined) | NO |
| `blocked_by` | array | YES (joined) | NO |
| `supersedes` | string | YES | YES |
| `superseded_by` | string | YES | YES |
| `next_slice` | string | YES | YES |
| `evidence_docs` | array | YES (joined) | NO |
| `last_verified_at` | datetime | NO | YES |

### 3.4 Which fields should receive exact-match boosts?

| Field | Boost Factor | Rationale |
|-------|-------------|-----------|
| `slice_id` | 3.0x | Primary identifier lookup |
| `pr_number` | 2.5x | Common "what is PR 642" queries |
| `branch` | 2.0x | Branch name lookups |
| `owner_worker` | 2.0x | "What did W6 do" queries |
| `related_foundup_id` | 2.0x | FoundUp-scoped queries |
| `status` | 1.5x | Status filter queries |

### 3.5 How should common queries resolve?

| Query Pattern | Resolution Strategy |
|---------------|---------------------|
| "what is open" | Filter `status IN (PROPOSED, ASSIGNED, IN_PROGRESS, STAGED_FOR_W10, PR_OPEN)` |
| "what is blocked" | Filter `status = BLOCKED` |
| "what is next" | Filter `status = PROPOSED OR status = ASSIGNED`, sort by `priority` |
| "what did W6 do" | Filter `owner_worker = W6`, sort by `updated_at DESC` |
| "what merged today" | Filter `status = MERGED`, filter `merge_commit` exists |
| "PR 642" | Exact match boost on `pr_number = 642` |
| "DJ2_F" | Exact match boost on `slice_id CONTAINS DJ2_F` |

### 3.6 How should HoloIndex distinguish work states?

| Work State | Status Values | Ranking Behavior |
|------------|---------------|------------------|
| **Current open work** | `IN_PROGRESS`, `STAGED_FOR_W10`, `PR_OPEN` | Rank HIGHEST in "what is open" queries |
| **Merged work** | `MERGED`, `CLOSED` | Rank lower unless explicitly queried |
| **Parked work** | `PARKED` | Visible but not ranked as next work |
| **Blocked work** | `BLOCKED` | Visible, show `blocked_by` in results |
| **Superseded work** | `SUPERSEDED` | NEVER rank unless explicitly queried with `include:superseded` |
| **Stale historical** | Any with `last_verified_at` > 30 days | Apply freshness penalty |

### 3.7 How should HoloIndex avoid stale ACTIVE_SLICE_LEDGER entries?

**Problem**: Once `work_ledger.example.json` becomes authoritative, ACTIVE_SLICE_LEDGER.md entries become stale.

**Solution**:
1. **Source tagging**: Add `source: "typed_ledger"` vs `source: "markdown_ledger"` metadata
2. **Freshness priority**: `typed_ledger` entries always rank above `markdown_ledger`
3. **Deprecation marker**: Add `ACTIVE_SLICE_LEDGER.md` header with `<!-- HOLOINDEX: deprecated_by=work_ledger.example.json -->`
4. **Reindex flag**: On next reindex, apply -0.5 rank penalty to `markdown_ledger` sources

### 3.8 What reindex or migration step will be needed later?

| Phase | Action | Trigger |
|-------|--------|---------|
| Phase 1 | Add `work_ledger.example.json` to priority roots | After spec approval |
| Phase 2 | Implement JSON metadata extraction | After Phase 1 validation |
| Phase 3 | Add status-aware ranking | After Phase 2 tests pass |
| Phase 4 | Add freshness boost for `last_verified_at` | After Phase 3 baseline |
| Phase 5 | Deprecate ACTIVE_SLICE_LEDGER.md indexing | After typed ledger is authoritative |

**Recommended implementation slice**: `FOUNDUPS_WORK_LEDGER_HOLOINDEX_IMPLEMENTATION_PHASE1`

### 3.9 What tests should implementation require?

| Test Category | Test Cases |
|---------------|------------|
| **Exact match** | `slice_id: DJ2_F_OPENCLAW_SECURITY_FAIL_DISPATCH` returns exact match top-1 |
| **PR lookup** | `PR 642` returns slice with `pr_number: 642` top-1 |
| **Status filter** | `what is open` returns only PROPOSED/ASSIGNED/IN_PROGRESS/STAGED_FOR_W10/PR_OPEN |
| **Worker query** | `what did W9 do` returns slices with `owner_worker: W9` |
| **Blocked query** | `what is blocked` returns only BLOCKED status slices |
| **Superseded exclusion** | `next work` does NOT return SUPERSEDED slices |
| **Freshness ranking** | Slice with recent `last_verified_at` ranks above stale slice |
| **FoundUp scope** | `gotjunk work` returns slices with `related_foundup_id: gotjunk` |

---

## 4. Indexing Architecture Spec

### 4.1 New Collection Definition

```python
# Proposed ChromaDB collection for work ledger
WORK_LEDGER_COLLECTION = "work_ledger_slices"

# Metadata schema per document
slice_metadata = {
    "slice_id": str,           # Primary key
    "title": str,              # Searchable text
    "lane": str | None,
    "priority": str,           # P0-P4
    "status": str,             # Enum value
    "owner_worker": str | None,
    "source": str,             # typed_ledger | markdown_ledger
    "branch": str | None,
    "pr_number": int | None,
    "related_foundup_id": str | None,
    "related_wsp_joined": str, # "|".join(related_wsp)
    "blocked_by_joined": str,  # "|".join(blocked_by)
    "next_slice": str | None,
    "last_verified_at": str,   # ISO datetime
    "freshness_score": float,  # 1.0 = today, decays over time
}
```

### 4.2 Priority Root Addition

```python
# Add to indexing_engine.py priority roots
roots = [
    holo.project_root / "holo_index" / "core",                      # P1: search infrastructure
    holo.project_root / "modules" / "infrastructure" / "wre_core" / "src",  # P1: job routing
    holo.project_root / "docs" / "0102_session_briefings" / "work_ledger.example.json",  # P1: work ledger
    holo.project_root / "modules",                                  # P2: bulk modules
    # ... rest unchanged
]
```

### 4.3 Status-Aware Ranking

```python
# Status ranking weights
STATUS_RANKING = {
    "IN_PROGRESS": 1.0,      # Highest - active work
    "STAGED_FOR_W10": 0.95,  # Ready for merge
    "PR_OPEN": 0.9,          # Under review
    "ASSIGNED": 0.8,         # Queued
    "PROPOSED": 0.7,         # Backlog
    "BLOCKED": 0.5,          # Visible but deprioritized
    "PARKED": 0.4,           # Intentionally paused
    "MERGED": 0.3,           # Historical
    "CLOSED": 0.3,           # Historical
    "SUPERSEDED": 0.1,       # Almost never show
    "ABANDONED": 0.05,       # Rarely show
}
```

### 4.4 Freshness Calculation

```python
def calculate_freshness(last_verified_at: str) -> float:
    """Calculate freshness score from last_verified_at timestamp.
    
    Returns 1.0 for today, decays to 0.5 at 14 days, 0.1 at 30 days.
    """
    if not last_verified_at:
        return 0.5  # Unknown freshness = middle value
    
    verified = datetime.fromisoformat(last_verified_at.replace("Z", "+00:00"))
    age_days = (datetime.now(timezone.utc) - verified).days
    
    if age_days <= 1:
        return 1.0
    elif age_days <= 7:
        return 0.9
    elif age_days <= 14:
        return 0.7
    elif age_days <= 30:
        return 0.5
    else:
        return max(0.1, 0.5 - (age_days - 30) * 0.01)
```

---

## 5. Query Resolution Examples

### 5.1 "What is open"

```
Query: "what is open"
Filter: status IN (PROPOSED, ASSIGNED, IN_PROGRESS, STAGED_FOR_W10, PR_OPEN)
Sort: priority ASC, status_rank DESC, freshness DESC
Result: Active work items, P0 first, most recent first within priority
```

### 5.2 "What did W9 do"

```
Query: "what did W9 do"
Filter: owner_worker = "W9"
Sort: updated_at DESC
Result: All W9 slices, most recent first
```

### 5.3 "PR 642"

```
Query: "PR 642"
Exact match: pr_number = 642 (boost 2.5x)
Fallback: semantic search "PR 642"
Result: Slice with pr_number 642 top-1
```

### 5.4 "What is next for gotjunk"

```
Query: "what is next for gotjunk"
Filter: related_foundup_id = "gotjunk"
Filter: status IN (PROPOSED, ASSIGNED)
Sort: priority ASC, freshness DESC
Result: Next gotjunk work items
```

---

## 6. Migration Path

### 6.1 Phase Sequence

| Phase | Slice ID | Deliverable |
|-------|----------|-------------|
| Current | `FOUNDUPS_WORK_LEDGER_HOLOINDEX_INDEXING_SPEC_PHASE1` | This spec (DOCS_ONLY) |
| Next | `FOUNDUPS_WORK_LEDGER_HOLOINDEX_IMPLEMENTATION_PHASE1` | Priority root + JSON parsing |
| +1 | `FOUNDUPS_WORK_LEDGER_HOLOINDEX_RANKING_PHASE1` | Status-aware ranking |
| +2 | `FOUNDUPS_WORK_LEDGER_HOLOINDEX_TESTS_PHASE1` | Test suite |
| +3 | `FOUNDUPS_WORK_LEDGER_MARKDOWN_DEPRECATION_PHASE1` | Deprecate ACTIVE_SLICE_LEDGER indexing |

### 6.2 Rollback Strategy

If ranking changes cause quality regression:
1. Revert status ranking weights to flat 1.0
2. Keep freshness calculation (low risk)
3. Preserve JSON metadata extraction
4. Re-evaluate ranking weights with A/B testing

---

## 7. What This Spec Does NOT Do

| Action | Why Not |
|--------|---------|
| Modify HoloIndex code | SPEC_ONLY — no implementation |
| Reindex existing data | NO_REINDEX — spec only |
| Change ACTIVE_SLICE_LEDGER | NO_LEDGER_MUTATION |
| Modify ChromaDB collections | NO_HOLOINDEX_MUTATION |
| Add runtime dependencies | NO_RUNTIME_CHANGE |

---

## 8. Summary

### 8.1 Key Recommendations

1. **Index `work_ledger.example.json`** as structured work-state data with metadata extraction
2. **Extract 16 fields** as searchable/filterable metadata
3. **Apply exact-match boosts** for slice_id (3.0x), pr_number (2.5x), branch/worker/foundup (2.0x)
4. **Implement status-aware ranking** with IN_PROGRESS/STAGED_FOR_W10/PR_OPEN highest
5. **Apply freshness boost** based on `last_verified_at`
6. **Never rank SUPERSEDED** unless explicitly queried
7. **Deprecate ACTIVE_SLICE_LEDGER.md** indexing after typed ledger is authoritative

### 8.2 W10 Readiness

| Gate | Status |
|------|--------|
| Spec complete | YES |
| All questions answered | YES |
| Implementation path defined | YES |
| Test cases specified | YES |
| No mutations | YES |
| Ready for PR | YES |

---

## Appendix A: File Evidence

| File | Purpose | Status |
|------|---------|--------|
| `docs/0102_session_briefings/work_ledger.schema.json` | Schema definition | READ |
| `docs/0102_session_briefings/work_ledger.example.json` | Example entries | READ |
| `docs/audits/architecture/FOUNDUPS_WORK_LEDGER_SCHEMA_PHASE1.md` | Schema audit | READ |
| `docs/audits/architecture/FOUNDUPS_WORK_LEDGER_BRAIN_CURRENT_STATE_AUDIT_PHASE1.md` | Brain audit | READ |
| `docs/0102_session_briefings/ACTIVE_SLICE_LEDGER.md` | Legacy ledger | READ |
| `holo_index/core/holo_index.py` | HoloIndex core | READ |
| `docs/audits/holoindex_search_quality/HIA6A_INDEXING_GAP_FIX_REPORT.md` | Indexing pattern | READ |

---

**Spec Complete**: 2026-05-21
**Author**: W9
**WSP 97 Verdict**: PASS — spec/docs only, no mutations
**Next Slice**: FOUNDUPS_WORK_LEDGER_HOLOINDEX_IMPLEMENTATION_PHASE1
**W10 Readiness**: APPROVED for PR
