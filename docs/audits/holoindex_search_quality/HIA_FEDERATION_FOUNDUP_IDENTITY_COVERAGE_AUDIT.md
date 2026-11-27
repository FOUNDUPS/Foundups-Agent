# HIA_FEDERATION_FOUNDUP_IDENTITY_COVERAGE_AUDIT_PHASE2B

**Date**: 2026-05-06
**Slice**: HIA_FEDERATION_FOUNDUP_IDENTITY_COVERAGE_AUDIT_PHASE2B
**Status**: COMPLETE - AUDIT ONLY
**Author**: 0102 W1
**Base**: main @ `fccd7d9a8` (PR #510 merged)
**WSP References**: WSP 97, WSP 103, WSP 104, WSP 15
**Depends On**: HIA_FEDERATION_METADATA_TAGGING_PHASE2

---

## Purpose

Audit FoundUp identity coverage before enabling `foundup_id` query filtering.
Determine which `modules/foundups/*` directories are actual FoundUps, which
have manifests, which are externalized, and whether any ID mismatches exist.

---

## 1. Preflight Query Results

| Query | Top Doc Hits |
|-------|-------------|
| AutoPost externalized FoundUp | AUTOPOST_EXTERNAL_OPERATIONAL_READINESS_AUDIT.md (docs), INTERFACE.md (foundups) |
| Science Swarm Hub external pqn_swarm_hub | pqn_swarm_hub/README.md, FOUNDUPS_SCIENCE_SWARM_EMBED_SPEC.md, WSP_103, WSP_104 |
| FoundUp manifest schema foundup_id | PFMALL_FOUNDUP_MANIFEST_SCHEMA.md (TOP-1 docs), WSP_104 |

All preflight queries return relevant docs at top positions.

---

## 2. Catalog FoundUp IDs

From `public/member/mall-video-catalog.json`:

| Catalog foundup_id | Classification |
|-------------------|----------------|
| `antifafm` | ACTIVE_PFMALL_FOUNDUP |
| `autopost` | EXTERNAL_APP |
| `eduit` | CANDIDATE |
| `foundups_main` | BRAND_META |
| `gotjunk_001` | ACTIVE_INTERNAL |
| `kosei` | ACTIVE_INTERNAL |
| `linkedin_012` | IDENTITY_ONLY |
| `linkedin_esingularity` | LINKEDIN_MICRO |
| `linkedin_foundups` | IDENTITY_ONLY |
| `linkedin_tsingularity` | LINKEDIN_MICRO |
| `move2japan` | ACTIVE_PFMALL_FOUNDUP |
| `science_swarm` | EXTERNALIZED_STUB |
| `undaodu` | BRAND_META |

---

## 3. modules/foundups/* Directory Analysis

### Directories with foundup_manifest.json (4)

| Directory | Manifest foundup_id | Catalog Match | Status |
|-----------|-------------------|---------------|--------|
| `trade/` | `trade` | Not in catalog | MATCH - proto-ready |
| `kosei/` | `kosei` | `kosei` | MATCH |
| `gotjunk/` | `gotjunk_001` | `gotjunk_001` | MATCH |
| `voteballots/` | `voteballots` | Not in catalog | MATCH - proto-ready |

### FoundUp Directories WITHOUT Manifest (5)

| Directory | Evidence of FoundUp | Catalog ID | Action Required |
|-----------|-------------------|-----------|-----------------|
| `move2japan/` | README: "FoundUp", has src/ | `move2japan` | **ADD MANIFEST** |
| `geoze/` | README: FoundUp intent, has src/ | Not in catalog | ADD MANIFEST when activated |
| `pqn_portal/` | Has src/, incubating | Not in catalog | ADD MANIFEST when activated |
| `social_twin/` | Has src/, PoC status | Not in catalog | ADD MANIFEST when activated |
| `ecosystem_animation/` | Frontend animation | Not in catalog | ADD MANIFEST when activated |

### Support Modules (NOT FoundUps) (8)

| Directory | Purpose | Manifest Required |
|-----------|---------|-------------------|
| `agent/` | Agent lifecycle management | NO |
| `agent_market/` | CABR engine, FAM daemon | NO |
| `agent_market+/` | Memory folder only | NO |
| `memory/` | WSP 60 compliance storage | NO |
| `mobile_worker_skills/` | Worker skills framework | NO |
| `pfmall/` | Catalog API | NO |
| `simulator/` | Simulation tool | NO |
| `src/` | Infrastructure code | NO |

### Documentation Only (1)

| Directory | Purpose |
|-----------|---------|
| `docs/` | Architecture documentation |

### Externalized Stub (1)

| Directory | External Repo | Catalog ID | ID Mismatch |
|-----------|--------------|-----------|-------------|
| `pqn_swarm_hub/` | FOUNDUPS/science-swarm-hub | `science_swarm` | **YES** |

---

## 4. ID Mismatches

### Mismatch 1: science_swarm vs pqn_swarm_hub

| Field | Value |
|-------|-------|
| Catalog `foundup_id` | `science_swarm` |
| Module directory | `modules/foundups/pqn_swarm_hub/` |
| External repo | `FOUNDUPS/science-swarm-hub` |
| Package name | `science-swarm-hub` (pyproject.toml) |

**Resolution**: The directory name `pqn_swarm_hub` is historical. The canonical
name is `science_swarm`. If a manifest is added to the stub, use `foundup_id: "science_swarm"`.

**Current impact**: Files under `pqn_swarm_hub/` resolve to `foundup_id: "pqn_swarm_hub"`
(directory fallback). This is a stub-only directory with no executable code.

---

## 5. External FoundUps (Correctly Blocked)

| FoundUp | Monorepo Module | External Surface | Status |
|---------|----------------|-----------------|--------|
| AutoPost | NO (correct) | FOUNDUPS/AutoPost repo | BLOCKED |
| Science Swarm Hub | STUB only | FOUNDUPS/science-swarm-hub repo | BLOCKED |

Both externalized FoundUps are correctly blocked from internal indexing.

---

## 6. Missing Manifests

### Priority 1: move2japan

| Field | Recommended Value |
|-------|-------------------|
| `foundup_id` | `move2japan` |
| `routing_prefix` | `/f/move2japan` |
| `data_namespace` | `idb_move2japan` |
| `tier` | `F1_OPO` |
| `lifecycle_stage` | `proto` |
| Reason | Active in pfMALL (573 videos), has src/ |

### Priority 2-3: Deferred

| FoundUp | Priority | Reason |
|---------|----------|--------|
| `geoze` | P2 | Has src/, not in catalog |
| `pqn_portal` | P3 | Incubating |
| `social_twin` | P3 | PoC status |

---

## 7. antifaFM Location

antifaFM module is at `modules/platform_integration/antifafm_broadcaster/`, not
under `foundups/`. This means `resolve_foundup_metadata()` classifies it as `"core"`.

This is acceptable: the broadcaster is platform infrastructure. The FoundUp identity
`antifafm` belongs to the content lane, not the broadcaster code.

---

## 8. Phase 3 Filtering Readiness

### Ready for Query Filtering (4)

| foundup_id | Has Manifest | Filter-Ready |
|-----------|--------------|--------------|
| `trade` | YES | YES |
| `kosei` | YES | YES |
| `gotjunk_001` | YES | YES |
| `voteballots` | YES | YES |

### Fallback Works (1)

| Directory | Effective ID | Gap |
|-----------|-------------|-----|
| `move2japan/` | `move2japan` (fallback) | Manifest recommended |

### External (Blocked)

| FoundUp | Status |
|---------|--------|
| `autopost` | BLOCKED |
| `science_swarm` | BLOCKED |

**VERDICT**: Phase 3 query filtering CAN proceed. The 4 manifested FoundUps are
filter-ready. `move2japan` fallback produces correct ID.

---

## 9. WSP 97 Truth Boundaries

| Statement | Status |
|-----------|--------|
| Only 4 directories have foundup_manifest.json | TRUE |
| move2japan has 573 catalog videos but no manifest | TRUE |
| pqn_swarm_hub directory name mismatches catalog ID science_swarm | TRUE |
| antifaFM is under platform_integration, not foundups | TRUE |
| AutoPost has no internal module (correctly externalized) | TRUE |
| Science Swarm Hub is stub-only (code migrated to external) | TRUE |
| resolve_foundup_metadata() falls back to directory name | TRUE |
| No manifests added in this audit | TRUE |
| No external repo indexing enabled | TRUE |

---

## 10. Recommended Manifest Additions

| FoundUp | Priority | When |
|---------|----------|------|
| `move2japan` | P1 | Before Phase 3 (optional) |
| `geoze` | P2 | When activated |
| `pqn_portal` | P3 | When proto |
| `social_twin` | P3 | When proto |

---

## Files Added

| File | Purpose |
|------|---------|
| `HIA_FEDERATION_FOUNDUP_IDENTITY_COVERAGE_AUDIT.md` | This audit |
