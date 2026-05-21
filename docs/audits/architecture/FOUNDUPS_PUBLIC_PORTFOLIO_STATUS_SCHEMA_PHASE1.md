# FOUNDUPS_PUBLIC_PORTFOLIO_STATUS_SCHEMA_PHASE1

**Worker**: W9
**Date**: 2026-05-21
**Status**: COMPLETE (SCHEMA_ONLY)
**Base commit**: main post-PR #645
**Mode**: Schema implementation

---

## WSP 97 Truth Boundary Labels

| Label | Status |
|-------|--------|
| PUBLIC_PORTFOLIO_SCHEMA_ONLY | YES |
| NO_RUNTIME_CHANGE | YES |
| NO_ROUTE_CREATION | YES |
| NO_PFMALL_CATALOG_MUTATION | YES |
| NO_REGISTRY_ID_RECLASSIFICATION | YES |
| NO_TOKEN_ASSIGNMENT | YES |
| NO_AUTH_CHANGE | YES |
| NO_CABR_READY | YES |
| NO_PAYOUT_READY | YES |
| NO_DAO_ACTIVATION | YES |

---

## 1. HoloIndex Assessment

### Queries Executed

| Query | Hits | Quality |
|-------|------|---------|
| `FoundUp public portfolio status registry schema foundups.com p.fMALL landing` | 32 | GOOD - found pfmall-control-dispatcher, WSP 102 |
| `public FoundUp PoC landing /f/{foundup_id} registry fields screenshot website github docs` | 32 | GOOD - found shell_core, WSP 103 |
| `foundup_registry.schema.json public_surface_status portfolio fields` | 6 | LIMITED - schema file not indexed |

### Fallback rg Required

**NO** — HoloIndex found related documentation and implementation files.

---

## 2. Purpose

Extend the FoundUp canonical registry schema to support foundups.com / p.fMALL portfolio display fields without changing runtime routes, catalogs, or public pages.

---

## 3. Schema Additions

### 3.1 New Enum Definitions

```json
"PortfolioStatus": {
  "type": "string",
  "enum": ["not_portfolio", "portfolio_candidate", "portfolio_ready", "portfolio_featured"],
  "description": "foundups.com public portfolio display status"
}

"PocLandingStatus": {
  "type": "string",
  "enum": ["none", "placeholder", "functional", "polished"],
  "description": "PoC landing page implementation status"
}
```

### 3.2 New RegistryEntry Properties

| Field | Type | Description |
|-------|------|-------------|
| `portfolio_status` | PortfolioStatus | Portfolio display eligibility |
| `poc_landing_status` | PocLandingStatus | Landing page implementation level |
| `website_url` | string\|null | Public website URL |
| `poc_url` | string\|null | PoC/demo URL |
| `app_url` | string\|null | Production app URL |
| `github_url` | string\|null | Public GitHub repo |
| `docs_url` | string\|null | Public documentation |
| `screenshot_url` | string\|null | Hero image for portfolio |
| `public_summary` | string\|null | 280 char max summary |
| `portfolio_priority` | int\|null | Display order (1=highest) |
| `portfolio_ready` | boolean | Display eligibility flag |
| `portfolio_evidence_docs` | array | Evidence supporting readiness |

---

## 4. Registry Updates

### 4.1 Production Registry (14 entities)

| foundup_id | portfolio_status | poc_landing_status | portfolio_ready |
|------------|------------------|-------------------|-----------------|
| gotjunk_001 | portfolio_candidate | functional | false |
| kosei | portfolio_candidate | functional | false |
| voteballots | not_portfolio | none | false |
| trade | not_portfolio | none | false |
| magadoom_001 | not_portfolio | none | false |
| antifafm_001 | not_portfolio | none | false |
| pfmall | not_portfolio | none | false |
| agent_market | not_portfolio | none | false |
| move2japan | not_portfolio | none | false |
| simulator | not_portfolio | none | false |
| social_twin | not_portfolio | none | false |
| autopost | not_portfolio | placeholder | false |
| pqn_portal | not_portfolio | none | false |
| science_swarm_hub | not_portfolio | none | false |

### 4.2 Example Registry (6 entities)

All entities updated with portfolio fields matching production values.

---

## 5. Test Coverage

### Test File: `modules/foundups/tests/test_foundup_registry_schema.py`

| Category | Tests | Status |
|----------|-------|--------|
| Schema Structure | 7 | PASS |
| Schema Validation | 2 | PASS |
| Example Portfolio Fields | 3 | PASS |
| Registry Consistency | 3 | PASS |
| **Total** | **15** | **PASS** |

### Key Test Cases

- `test_schema_has_portfolio_status_enum` — Enum exists with 4 values
- `test_portfolio_ready_is_boolean` — Type and default validated
- `test_url_fields_allow_null_or_string` — All 6 URL fields checked
- `test_example_validates` — Example validates against schema
- `test_registry_validates` — Production validates against schema
- `test_gotjunk_is_portfolio_candidate` — Correct status assignment
- `test_voteballots_not_portfolio_ready` — No false positives
- `test_no_invented_urls` — No placeholder URLs

---

## 6. Files Changed

| File | Changes |
|------|---------|
| `modules/foundups/foundup_registry.schema.json` | +2 enums, +12 properties |
| `modules/foundups/foundup_registry.example.json` | +12 fields per entity (6 entities) |
| `modules/foundups/foundup_registry.json` | +12 fields per entity (14 entities) |
| `modules/foundups/tests/test_foundup_registry_schema.py` | Created (15 tests) |
| `modules/foundups/ModLog.md` | Entry added |

---

## 7. What This Implementation Does NOT Do

| Action | Why Not |
|--------|---------|
| Create routes | NO_ROUTE_CREATION |
| Modify pFMALL catalog | NO_PFMALL_CATALOG_MUTATION |
| Change runtime behavior | NO_RUNTIME_CHANGE |
| Assign tokens | NO_TOKEN_ASSIGNMENT |
| Invent URLs | All URLs null or from existing fields |
| Reclassify entity IDs | NO_REGISTRY_ID_RECLASSIFICATION |

---

## 8. Registry/Catalog Boundary Preservation

The registry schema now supports portfolio display fields, but:

1. **No catalog writes** — pFMALL catalog (`mall-video-catalog.json`) unchanged
2. **No route creation** — `/f/{foundup_id}` exists per PUBLIC_FOUNDUP_POC_LANDING audit
3. **No display logic** — Portfolio rendering is a future slice
4. **Separation preserved** — Registry is canonical source; catalog is derived

---

## 9. Next Slices

| Priority | Slice ID | Description |
|----------|----------|-------------|
| P1 | FOUNDUPS_PORTFOLIO_DISPLAY_COMPONENT_PHASE1 | React/HTML component for portfolio grid |
| P2 | FOUNDUPS_PORTFOLIO_API_ENDPOINT_PHASE1 | API to serve portfolio-ready entries |
| P3 | FOUNDUPS_PORTFOLIO_SCREENSHOT_UPLOAD_PHASE1 | Upload pipeline for screenshot_url |

---

## 10. Summary

| Gate | Status |
|------|--------|
| Schema extended | YES |
| Example validates | YES |
| Registry validates | YES |
| Tests pass | YES (15/15) |
| No mutations | YES |
| Audit complete | YES |
| W10 Ready | YES |

---

**Implementation Complete**: 2026-05-21
**Author**: W9
**WSP 97 Verdict**: PASS — schema only, no runtime/catalog/route changes
**Next Slice**: FOUNDUPS_PORTFOLIO_DISPLAY_COMPONENT_PHASE1
