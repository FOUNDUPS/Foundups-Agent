# FoundUps Portfolio Data Projection Specification (Phase 1)

**Slice**: `FOUNDUPS_PORTFOLIO_DATA_PROJECTION_SPEC_PHASE1`
**Worker**: 0102
**Date**: 2026-05-22
**Mode**: Docs/spec only
**Base**: `600eee482`
**WSP Lock**: WSP_00 -> WSP_15 -> WSP_50 -> WSP_83 -> WSP_87 -> WSP_97 -> WSP_104 -> WSP_22

---

## WSP_97 Truth Boundary Labels

| Label | Status |
|-------|--------|
| DOCS_ONLY | YES |
| PORTFOLIO_PROJECTION_SPEC_ONLY | YES |
| NO_REGISTRY_MUTATION | YES |
| NO_PFMALL_CATALOG_MUTATION | YES |
| NO_PORTFOLIO_DATA_MUTATION | YES |
| NO_ROUTE_CHANGE | YES |
| NO_RUNTIME_CHANGE | YES |
| NO_HOLOINDEX_CORE_MUTATION | YES |
| NO_MCP_CHANGE | YES |
| NO_CABR_READY | YES |
| NO_PAYOUT_READY | YES |
| NO_DAO_ACTIVATION | YES |

---

## 1. Source of Truth

### 1.1 Canonical Hierarchy

```
CANONICAL SOURCE OF TRUTH (priority order)
    |
    +-- foundup_registry.json           [L1: PRIMARY - entity definitions, portfolio fields]
    |       ^
    |       |
    +-- mall-video-catalog.json         [L2: RUNTIME - video/catalog metadata, launch_readiness]
    |       ^
    |       |
    +-- foundup_manifest.json (per FoundUp)  [L3: DETAIL - tier, lifecycle, entry_url, token_symbol]
            ^
            |
    +-- portfolio_data.json             [DERIVED - must be generated, never manual source]
```

### 1.2 Key Principle

> **`portfolio_data.json` is a DERIVED PROJECTION, not a source of truth.**
>
> It MUST be generated from canonical inputs and MUST NOT be manually edited as a second source of truth.

### 1.3 Canonical Input Files

| File | Location | Role | Update Frequency |
|------|----------|------|------------------|
| `foundup_registry.json` | `modules/foundups/` | Canonical entity registry | On audit/PR |
| `foundup_registry.schema.json` | `modules/foundups/` | Schema validation | On schema change |
| `mall-video-catalog.json` | `public/member/` | Runtime catalog data | On scrape/sync |
| `foundup_manifest.json` | Per FoundUp module | Entity details | On FoundUp update |

### 1.4 Projection Output

| File | Location | Role | Update Frequency |
|------|----------|------|------------------|
| `portfolio_data.json` | `public/f/` | Frontend display projection | Generated on demand |

---

## 2. Current Static Projection Inventory

### 2.1 Current `portfolio_data.json` Content

**Entity Count**: 3

| foundup_id | display_name | portfolio_status | poc_landing_status |
|------------|--------------|------------------|-------------------|
| `gotjunk_001` | GotJunk | portfolio_candidate | functional |
| `kosei` | Kosei AI Systems | portfolio_candidate | functional |
| `holoindex_prod_01` | HoloIndex | portfolio_candidate | polished |

### 2.2 Current Registry Entity Count

**Registry Entity Count**: 14

| portfolio_status | Count |
|------------------|-------|
| `portfolio_candidate` | 2 (gotjunk_001, kosei) |
| `not_portfolio` | 12 |

### 2.3 Projection Mismatch

| Issue | Description |
|-------|-------------|
| **Stale holoindex entry** | `holoindex_prod_01` is `not_portfolio` in registry but `portfolio_candidate` in projection |
| **Missing projection fields** | Registry has 14 entities with portfolio fields; projection only has 3 |
| **Manual second source** | Current projection was manually created, not generated |

---

## 3. Canonical Input Rules

### 3.1 Registry Takes Precedence

| Field | Source | Rationale |
|-------|--------|-----------|
| `foundup_id` | Registry | Primary key, immutable |
| `display_name` | Registry | Official name |
| `portfolio_status` | Registry | Portfolio eligibility |
| `poc_landing_status` | Registry | Landing page status |
| `portfolio_priority` | Registry | Display order |
| `portfolio_ready` | Registry | Final eligibility gate |
| `website_url` | Registry | Static URL fields |
| `poc_url` | Registry | PoC demo URL |
| `app_url` | Registry | Production app URL |
| `github_url` | Registry | Repository URL |
| `docs_url` | Registry | Documentation URL |
| `screenshot_url` | Registry | Hero image URL |
| `public_summary` | Registry | Public-facing summary |

### 3.2 Catalog Provides Runtime Fields

| Field | Source | Rationale |
|-------|--------|-----------|
| `launch_readiness` | Catalog | Runtime status override |
| `video_count` | Catalog | Dynamic video count |
| `entry_url` | Catalog | App mount URL |
| `tier` | Catalog (fallback) | If missing in registry |
| `lifecycle_stage` | Catalog (fallback) | If missing in registry |
| `token_symbol` | Catalog (fallback) | If missing in registry |

### 3.3 Manifest Provides Detail Overrides

| Field | Source | Rationale |
|-------|--------|-----------|
| `tier` | Manifest | Canonical tier definition |
| `lifecycle_stage` | Manifest | Canonical lifecycle stage |
| `entry_url` | Manifest | App entry point |
| `token_symbol` | Manifest | Token assignment |
| `tagline` | Manifest | Short description |
| `description` | Manifest | Full description |

### 3.4 Conflict Resolution Order

```
Manifest (if exists) > Registry > Catalog > null
```

---

## 4. Projection Field Mapping

### 4.1 Required Projection Fields

| Projection Field | Source Field | Source File | Required |
|------------------|--------------|-------------|----------|
| `foundup_id` | `foundup_id` | Registry | YES |
| `display_name` | `display_name` | Registry | YES |
| `portfolio_status` | `portfolio_status` | Registry | YES |
| `poc_landing_status` | `poc_landing_status` | Registry | YES |
| `website_url` | `website_url` | Registry | NO |
| `poc_url` | `poc_url` | Registry | NO |
| `app_url` | `app_url` | Registry | NO |
| `github_url` | `github_url` | Registry | NO |
| `docs_url` | `docs_url` | Registry | NO |
| `screenshot_url` | `screenshot_url` | Registry | NO |
| `public_summary` | `public_summary` | Registry | NO |
| `portfolio_priority` | `portfolio_priority` | Registry | NO |
| `portfolio_ready` | `portfolio_ready` | Registry | YES |

### 4.2 Enrichment Fields (from Catalog/Manifest)

| Projection Field | Primary Source | Fallback Source |
|------------------|----------------|-----------------|
| `tier` | Manifest `tier` | Catalog `tier` |
| `lifecycle_stage` | Manifest `lifecycle_stage` | Catalog `lifecycle_stage` |
| `token_symbol` | Manifest `token_symbol` | Catalog `token_symbol` |
| `tagline` | Manifest `tagline` | Catalog `summary` |
| `entry_url` | Manifest `entry_url` | Catalog `entry_url` |
| `video_count` | Catalog `video_count` | 0 |
| `launch_readiness` | Catalog `launch_readiness` | Registry `poc_landing_status` mapping |

### 4.3 Derived Fields

| Projection Field | Derivation Logic |
|------------------|------------------|
| `is_dual_identity` | `true` if `foundup_id === 'holoindex_prod_01'` |
| `has_app` | `true` if `entry_url` is non-empty |
| `has_demo` | `true` if `poc_url` is non-empty |

---

## 5. HoloIndex Dual Identity Handling

### 5.1 Dual Identity Boundary

> **HoloIndex has a dual identity boundary.**
>
> - **Internal**: FoundUps retrieval/memory infrastructure used by 0102, WRE, OpenClaw, MCP, and workers
> - **External**: Public FoundUp surface discoverable through p.fMALL

### 5.2 Projection Rules for HoloIndex

| Rule | Implementation |
|------|----------------|
| Include in projection | YES, if `portfolio_status` allows |
| Display dual identity tag | YES, via `is_dual_identity` field |
| Use dedicated `public_summary` | YES, from registry |
| Hide internal implementation details | YES, no module_path in projection |
| Link to canonical landing | YES, `/f/holoindex_prod_01` |

### 5.3 HoloIndex Manifest Path

```
modules/foundups/holoindex_prod_01/foundup_manifest.json
```

### 5.4 HoloIndex Projection Fields

| Field | Value |
|-------|-------|
| `foundup_id` | `holoindex_prod_01` |
| `display_name` | `HoloIndex` |
| `is_dual_identity` | `true` |
| `public_summary` | From registry or manifest description |
| `tier` | From manifest: `INFRA` |
| `token_symbol` | From manifest: `HOLO` |
| `launch_readiness` | From manifest: `discoverable_only` |

---

## 6. Validation Rules

### 6.1 Structural Validation

| Rule | Description | Severity |
|------|-------------|----------|
| R1 | All projection entities MUST exist in registry | ERROR |
| R2 | `foundup_id` MUST match registry exactly | ERROR |
| R3 | `portfolio_status` MUST be valid enum value | ERROR |
| R4 | `poc_landing_status` MUST be valid enum value | ERROR |
| R5 | URL fields MUST be valid URI or null | WARNING |
| R6 | `public_summary` MUST be <= 280 characters | WARNING |
| R7 | `portfolio_priority` MUST be integer 1-100 or null | ERROR |

### 6.2 Source of Truth Validation

| Rule | Description | Severity |
|------|-------------|----------|
| R8 | Projection `portfolio_status` MUST match registry | ERROR |
| R9 | Projection `portfolio_ready` MUST match registry | ERROR |
| R10 | Projection entity count MUST match portfolio-eligible registry count | WARNING |
| R11 | No projection entity without registry backing | ERROR |

### 6.3 Consistency Checks

| Check | Description |
|-------|-------------|
| C1 | If `portfolio_ready=true`, then `poc_landing_status` MUST NOT be `none` |
| C2 | If `portfolio_status=portfolio_featured`, then `portfolio_ready` MUST be `true` |
| C3 | If `portfolio_status=not_portfolio`, entity MUST NOT appear in projection |
| C4 | HoloIndex `is_dual_identity` MUST be `true` |

### 6.4 Filter Rules

| Filter | Condition |
|--------|-----------|
| Include in projection | `portfolio_status IN ('portfolio_candidate', 'portfolio_ready', 'portfolio_featured')` |
| Exclude from projection | `portfolio_status = 'not_portfolio'` |

---

## 7. Generator/Validator Future Slice Plan

### 7.1 Generator Slice

**Slice ID**: `PORTFOLIO_DATA_GENERATOR_PHASE1`

**Scope**:
1. Create `modules/foundups/src/portfolio_data_generator.py`
2. Read `foundup_registry.json` as primary source
3. Enrich from `mall-video-catalog.json` catalog entries
4. Enrich from individual `foundup_manifest.json` files
5. Filter to portfolio-eligible entities only
6. Apply field mapping per Section 4
7. Handle HoloIndex dual identity per Section 5
8. Output to `public/f/portfolio_data.json`

**CLI Interface**:
```bash
python -m modules.foundups.src.portfolio_data_generator --generate
python -m modules.foundups.src.portfolio_data_generator --validate
python -m modules.foundups.src.portfolio_data_generator --diff
```

### 7.2 Validator Slice

**Slice ID**: `PORTFOLIO_DATA_VALIDATOR_PHASE1`

**Scope**:
1. Create `modules/foundups/src/portfolio_data_validator.py`
2. Validate existing `portfolio_data.json` against registry
3. Report all R1-R11 validation errors
4. Report all C1-C4 consistency warnings
5. Output validation report

**Integration**:
- Pre-commit hook to validate projection
- CI check to ensure projection matches registry
- PR blocker if validation fails

### 7.3 Regeneration Triggers

| Trigger | Action |
|---------|--------|
| Registry update | Regenerate projection |
| Manifest update | Regenerate projection (affected entity) |
| PR merge to main | Validate projection matches registry |
| Pre-deploy hook | Validate and regenerate if needed |

### 7.4 Implementation Priority

| Priority | Slice | Scope |
|----------|-------|-------|
| P1 | `PORTFOLIO_DATA_VALIDATOR_PHASE1` | Validate existing projection |
| P2 | `PORTFOLIO_DATA_GENERATOR_PHASE1` | Generate from canonical sources |
| P3 | `PORTFOLIO_DATA_CI_HOOK_PHASE1` | CI integration for validation |

---

## 8. WSP_97 Verdict

| Check | Result |
|-------|--------|
| Docs only | PASS |
| No registry mutation | PASS |
| No catalog mutation | PASS |
| No route changes | PASS |
| No runtime changes | PASS |
| No HoloIndex core mutation | PASS |
| No MCP changes | PASS |
| No CABR/payout/DAO claims | PASS |

**Verdict**: PASS

---

## 9. WSP_15 Next Slice

### 9.1 Primary Recommendation

**`PORTFOLIO_DATA_VALIDATOR_PHASE1`**

**Rationale**: Validate before generate. Current projection has known mismatches (HoloIndex portfolio_status differs from registry). Validator will surface all discrepancies before regeneration.

### 9.2 Secondary Recommendations

| Priority | Slice | Scope |
|----------|-------|-------|
| P2 | `PORTFOLIO_DATA_GENERATOR_PHASE1` | Implement generator with field mapping |
| P3 | `PORTFOLIO_DATA_CURRENT_STATE_FIX_PHASE1` | Manual fix of current projection to match registry |

---

## 10. HoloIndex Assessment

### Queries Executed

| Query | Hits | Quality |
|-------|------|---------|
| `FoundUps portfolio_data projection registry catalog manifest source of truth` | 32 | EXCELLENT |
| `FOUNDUPS_PORTFOLIO_DISPLAY_COMPONENT_PHASE1 bounded static projection` | 32 | EXCELLENT |
| `p.fMALL HoloIndex dual identity manifest portfolio_data` | 32 | GOOD |

### Assessment

| Criterion | Rating |
|-----------|--------|
| Top hits relevant | YES |
| Found all key documents | YES |
| Noise level | LOW |
| Fallback required | NO |

---

## Sources

### Internal

| Document | Location |
|----------|----------|
| Registry | `modules/foundups/foundup_registry.json` |
| Registry Schema | `modules/foundups/foundup_registry.schema.json` |
| Portfolio Data (current) | `public/f/portfolio_data.json` |
| Display Component | `public/f/index.html` |
| HoloIndex Manifest | `modules/foundups/holoindex_prod_01/foundup_manifest.json` |
| Schema Phase 1 | `docs/audits/architecture/FOUNDUPS_PUBLIC_PORTFOLIO_STATUS_SCHEMA_PHASE1.md` |
| Display Phase 1 | `docs/audits/architecture/FOUNDUPS_PORTFOLIO_DISPLAY_COMPONENT_PHASE1.md` |
| POC Landing Audit | `docs/audits/architecture/PUBLIC_FOUNDUP_POC_LANDING_AND_PFMALL_INTERACTION_AUDIT_PHASE1.md` |

---

*Spec authored under WSP_00 -> WSP_15 -> WSP_50 -> WSP_83 -> WSP_87 -> WSP_97 -> WSP_104 -> WSP_22.*
*Slice: FOUNDUPS_PORTFOLIO_DATA_PROJECTION_SPEC_PHASE1*
