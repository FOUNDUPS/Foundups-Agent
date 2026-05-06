# HIA_FEDERATION_METADATA_TAGGING_PHASE2

**Date**: 2026-05-06
**Slice**: HIA_FEDERATION_METADATA_TAGGING_PHASE2
**Status**: COMPLETE
**Author**: 0102 W1
**Base**: main @ `6791aabd7` (PR #509 merged)
**WSP References**: WSP 97, WSP 103, WSP 104, WSP 15
**Depends On**: HIA_FEDERATION_READINESS_AUDIT_PHASE1

---

## Purpose

Add `foundup_id` metadata to HoloIndex indexing pipeline so that every
indexed document is tagged with the FoundUp it belongs to. This is Phase 2
of the federation sequence: metadata tagging only, no query filtering yet.

---

## 1. Scope

| In Scope | Out of Scope |
|----------|-------------|
| `resolve_foundup_metadata()` helper | Query-time `where=` filtering (Phase 3) |
| `foundup_id` in all index_* metadata | Per-FoundUp collection isolation (Phase 4) |
| `tenant_id` default "core" | External repo indexing (blocked) |
| `source_scope` classification | Manifest signature verification |
| `external_repo` = False guard | Gemma/LLM changes |
| Unit tests (22) | TurboQuant promotion |
| Manifest caching | Search ranking changes |

---

## 2. Implementation

### resolve_foundup_metadata(path, project_root)

Located in `holo_index/core/indexing_engine.py`.

**Logic**:
1. Normalize path separators (Windows backslash handling)
2. Check if path matches `modules/foundups/{name}/`
3. If yes: read `foundup_manifest.json` from that FoundUp directory
   - Use `foundup_id` from manifest if present
   - Fall back to directory name if manifest missing/malformed
   - Cache manifest reads to avoid re-reading per file
4. If no: return `"core"` for all federation fields

**Returns**:
```python
{
    "foundup_id": str,      # From manifest or "core"
    "tenant_id": "core",    # Default (future: per-FoundUp tenant)
    "source_scope": str,    # "internal_foundup" or "core"
    "external_repo": False,  # Guard: no external repos yet
}
```

### Manifest Resolution

| FoundUp Directory | Manifest `foundup_id` | Resolved |
|------------------|-----------------------|----------|
| modules/foundups/trade/ | "trade" | "trade" |
| modules/foundups/kosei/ | "kosei" | "kosei" |
| modules/foundups/gotjunk/ | "gotjunk_001" | "gotjunk_001" |
| modules/foundups/voteballots/ | "voteballots" | "voteballots" |
| holo_index/core/ | N/A | "core" |
| WSP_framework/src/ | N/A | "core" |
| modules/infrastructure/ | N/A | "core" |
| docs/ | N/A | "core" |
| WSP_knowledge/ | N/A | "core" |

---

## 3. Index Functions Modified

All 7 index functions now write federation metadata:

| Function | Collection | New Metadata Fields |
|----------|-----------|-------------------|
| `index_code_entries` | navigation_code | foundup_id, tenant_id, source_scope, external_repo |
| `index_symbol_entries` | navigation_symbols | foundup_id, tenant_id, source_scope, external_repo |
| `index_wsp_entries` | navigation_wsp | foundup_id, tenant_id, source_scope, external_repo |
| `index_docs_entries` | navigation_docs | foundup_id, tenant_id, source_scope, external_repo |
| `index_knowledge_entries` | navigation_knowledge | foundup_id, tenant_id, source_scope, external_repo |
| `index_test_registry` | navigation_tests | foundup_id, tenant_id, source_scope, external_repo |
| `index_skillz_entries` | navigation_skills | foundup_id, tenant_id, source_scope, external_repo |

### Metadata Field Definitions

| Field | Type | Values | Purpose |
|-------|------|--------|---------|
| `foundup_id` | str | manifest value or "core" | Tenant isolation at query time (Phase 3) |
| `tenant_id` | str | "core" (always) | Future per-FoundUp tenant scoping |
| `source_scope` | str | "internal_foundup" or "core" | Distinguish FoundUp vs platform code |
| `external_repo` | bool | False (always) | Guard against external repo indexing |

---

## 4. Test Results

### New Tests: test_federation_metadata_tagging.py

| Test Class | Tests | Passed |
|-----------|-------|--------|
| TestResolveFoundupMetadata | 4 | 4 |
| TestCorePathResolution | 6 | 6 |
| TestExternalRepoGuard | 2 | 2 |
| TestTenantId | 2 | 2 |
| TestManifestFallback | 3 | 3 |
| TestManifestCache | 1 | 1 |
| TestReturnShape | 2 | 2 |
| TestWindowsPathHandling | 2 | 2 |
| **Total** | **22** | **22** |

### Regression Tests

| Suite | Passed | Regression |
|-------|--------|-----------|
| test_search_quality_baseline.py | 10 | NO |
| test_collection_health.py | 18 | NO |
| test_backend_routing.py | 19 | NO |
| **Total** | **47** | **NO** |

---

## 5. Reindex Requirement

**Full reindex IS required** for metadata to appear in ChromaDB. The
metadata fields are only written during indexing. Existing index entries
do not have `foundup_id` until re-indexed.

```bash
python holo_index.py --index-code --ssd E:/HoloIndex
python holo_index.py --index-symbols --ssd E:/HoloIndex
python holo_index.py --index-docs --ssd E:/HoloIndex
python holo_index.py --index-wsp --ssd E:/HoloIndex
```

**Note**: Reindex does NOT change search results or ranking. The new
metadata fields are passive — they exist in ChromaDB but are not used
for filtering until Phase 3 adds `where=` clauses.

---

## 6. WSP 97 Truth Boundaries

| Statement | Status |
|-----------|--------|
| resolve_foundup_metadata() reads real manifests | TRUE |
| All 7 index functions write federation metadata | TRUE |
| No query filtering added (Phase 3 scope) | TRUE |
| No search ranking changes | TRUE |
| No collection isolation changes | TRUE |
| No external repo indexing | TRUE |
| No Gemma/LLM changes | TRUE |
| No TurboQuant changes | TRUE |
| external_repo is always False | TRUE |
| tenant_id is always "core" | TRUE |
| All existing tests pass with no regression | TRUE |

---

## 7. Files Modified/Added

| File | Action | Purpose |
|------|--------|---------|
| `holo_index/core/indexing_engine.py` | MODIFIED | Added resolve_foundup_metadata(), wired into all index_* |
| `holo_index/tests/test_federation_metadata_tagging.py` | ADDED | 22 unit tests for metadata resolution |
| `docs/audits/holoindex_search_quality/HIA_FEDERATION_METADATA_TAGGING.md` | ADDED | This audit |
| `holo_index/ModLog.md` | MODIFIED | Phase 2 entry |

---

## 8. Federation Pipeline Status

| Phase | Status |
|-------|--------|
| HIA Federation Phase 1: Readiness audit | DONE (PR #509) |
| HIA Federation Phase 2: Metadata tagging | **DONE (this slice)** |
| HIA Federation Phase 3: Query filtering | NEXT |
| HIA Federation Phase 4: Collection isolation | BLOCKED on Phase 3 |
| HIA Federation Phase 5: External repo indexing | BLOCKED on Phase 4 + signature gate |
