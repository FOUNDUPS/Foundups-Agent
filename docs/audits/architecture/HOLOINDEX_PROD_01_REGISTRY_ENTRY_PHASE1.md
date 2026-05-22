# HoloIndex Prod 01 Registry Entry — Phase 1

**Slice**: `HOLOINDEX_PROD_01_REGISTRY_ENTRY_PHASE1`
**Worker**: W6
**Date**: 2026-05-22
**Mode**: Registry data fix + tests
**Base commit**: PR #672 merged
**Branch**: `feat/holoindex-prod-01-registry-entry-phase1`
**WSP Lock**: WSP_00 -> WSP_15 -> WSP_50 -> WSP_83 -> WSP_87 -> WSP_97 -> WSP_104 -> WSP_22

---

## WSP_97 Truth Boundary Labels

| Label | Status |
|-------|--------|
| REGISTRY_DATA_FIX_ONLY | YES |
| HOLOINDEX_PROD_01_REGISTRY_BACKING_ONLY | YES |
| DUAL_IDENTITY_BOUNDARY_ENFORCED | YES |
| NO_PFMALL_CATALOG_MUTATION | YES |
| NO_PORTFOLIO_PROJECTION_MUTATION | YES |
| NO_UI_CHANGE | YES |
| NO_ROUTE_CHANGE | YES |
| NO_HOLOINDEX_CORE_MUTATION | YES |
| NO_BACKEND_ACCESS_ENABLEMENT | YES |
| NO_INTERNAL_INDEX_EXPOSURE | YES |
| NO_TOKEN_ASSIGNMENT | YES |
| NO_MCP_CHANGE | YES |
| NO_CI_CHANGE | YES |
| NO_CABR_READY | YES |
| NO_PAYOUT_READY | YES |
| NO_DAO_ACTIVATION | YES |

---

## 1. Mission

Add `holoindex_prod_01` to the canonical FoundUp registry to resolve the validator-detected registry-backing drift (R1, R11).

## 2. Pre-Fix Validator Output

```
registry_total              : 14
registry_portfolio_eligible : 2
projection_total            : 3
errors                      : 2
warnings                    : 2

[ERROR] R1  holoindex_prod_01 has no matching entry in foundup_registry.json
[WARNING] R10 Projection lists 3 entities, registry has 2 portfolio-eligible
[ERROR] R11 holoindex_prod_01 has no registry backing (orphan)
[WARNING] C4 HoloIndex must set is_dual_identity=true

Exit code: 1
```

## 3. Post-Fix Validator Output

```
registry_total              : 15
registry_portfolio_eligible : 3
projection_total            : 3
errors                      : 0
warnings                    : 1

[WARNING] C4 entity='holoindex_prod_01' field='is_dual_identity' source=projection
    expected: True
    actual  : None
    -> HoloIndex projection must set is_dual_identity=true (spec section 5)

Exit code: 1
```

## 4. Registry Entry Values

| Field | Value | Source |
|-------|-------|--------|
| `foundup_id` | `holoindex_prod_01` | Manifest + projection |
| `display_name` | `HoloIndex` | Manifest |
| `entity_type` | `infra_service` | Manifest `category: infrastructure` |
| `module_path` | `modules/foundups/holoindex_prod_01` | File system |
| `stage` | `incubating` | Manifest `lifecycle_stage` |
| `tier` | `F3_INFRA` | Manifest `tier: INFRA` mapped to schema |
| `implementation_status` | `IMPLEMENTED` | Operational evidence |
| `public_surface_status` | `listed` | Catalog evidence |
| `poc_status` | `poc` | Catalog `launch_readiness: discoverable_only` |
| `prototype_gate_status` | `passed` | Operational evidence |
| `manifest_status` | `exists` | File exists |
| `manifest_path` | `modules/foundups/holoindex_prod_01/foundup_manifest.json` | File system |
| `hermes_openclaw_build_status` | `wired` | MCP/OpenClaw integration exists |
| `token_status` | `TOKEN_DEFERRED` | Manifest has HOLO but not deployed |
| `token_symbol` | `null` | Token not active |
| `portfolio_status` | `portfolio_candidate` | Projection |
| `poc_landing_status` | `polished` | Projection |
| `website_url` | `https://foundups.com/holoindex` | Projection |
| `poc_url` | `https://foundups.com/holoindex` | Same as website (PoC landing) |
| `portfolio_priority` | `3` | Projection |
| `portfolio_ready` | `false` | Projection |

### 4.1 Entity Type Rationale

**Choice**: `infra_service`

**Rationale**:
- Manifest `category: "infrastructure"` explicitly marks it as infrastructure
- Primary identity is internal retrieval/memory infrastructure
- External FoundUp surface is secondary (dual identity)
- `infra_service` does not require `related_external_repo` (unlike `external_foundup`)
- Schema allows optional `tier` and `stage` for `infra_service`

### 4.2 Token Status Rationale

**Choice**: `TOKEN_DEFERRED`

**Rationale**:
- Manifest has `token_symbol: "HOLO"` indicating token is planned
- Token is not live/deployed/active
- `NOT_APPLICABLE` would incorrectly imply no token planned
- `TOKEN_DEFERRED` with `token_symbol: null` is schema-compliant

### 4.3 Dual Identity Boundary Note

The registry entry includes a notes field documenting the dual identity:

> DUAL IDENTITY BOUNDARY: Internal HoloIndex remains protected FoundUps retrieval/memory/work-ledger infrastructure. External HoloIndex is the public p.fMALL-discoverable FoundUp/connective trust surface. This registry entry does not expose internal backend/core/index access.

## 5. Drift Resolution

| Drift | Status |
|-------|--------|
| R1 (projection entity missing from registry) | **CLEARED** |
| R11 (no registry backing) | **CLEARED** |
| R10 (count mismatch) | **CLEARED** (3==3) |
| C4 (is_dual_identity missing) | **REMAINS** (projection-side) |

C4 remains because `is_dual_identity` is a projection field, not a registry field. Resolution belongs to a separate `PORTFOLIO_DATA_PROJECTION_FIX_PHASE1` slice.

## 6. Test Results

### 6.1 Registry Schema Tests

```
46 passed in 0.33s
```

### 6.2 Portfolio Validator Tests

```
43 passed in 0.79s
```

Tests updated to reflect fixed state:
- `test_real_repo_holoindex_has_registry_backing` — R1/R11 no longer fire
- `test_real_repo_count_matches` — R10 no longer fires
- `test_real_repo_stats_capture_full_inventory` — registry_total=15, eligible=3
- `test_cli_exit_code_1_against_current_repo` — C4 remains

## 7. Files Changed

| File | Change |
|------|--------|
| `modules/foundups/foundup_registry.json` | Added holoindex_prod_01 entry (+45 lines) |
| `modules/foundups/portfolio_validator/tests/test_validator.py` | Updated real-repo tests (~20 lines) |
| `docs/audits/architecture/HOLOINDEX_PROD_01_REGISTRY_ENTRY_PHASE1.md` | NEW (this file) |

## 8. HoloIndex Assessment

| Query | Result |
|-------|--------|
| `holoindex_prod_01 registry entry portfolio validator R1 R11` | WEAK (no direct hits) |
| `HoloIndex dual identity foundup_registry portfolio_candidate NOT_APPLICABLE token` | WEAK (no direct hits) |

Fallback to direct file reads was required. Recommendation: index audit docs by slice ID.

## 9. WSP_97 Verdict

| Check | Result |
|-------|--------|
| Registry data fix only | PASS |
| No catalog mutation | PASS |
| No projection mutation | PASS |
| No UI change | PASS |
| No route change | PASS |
| No HoloIndex core mutation | PASS |
| No backend access enablement | PASS |
| No internal index exposure | PASS |
| No token assignment | PASS |
| No MCP change | PASS |
| No CI change | PASS |
| Dual identity boundary enforced | PASS |

**Verdict**: PASS

## 10. Next Slice

| Slice | Purpose |
|-------|---------|
| `PORTFOLIO_DATA_PROJECTION_FIX_PHASE1` | Add `is_dual_identity: true` to projection for holoindex_prod_01 |

---

*Slice authored under WSP_00 -> WSP_15 -> WSP_50 -> WSP_83 -> WSP_87 -> WSP_97 -> WSP_104 -> WSP_22.*
*Slice: HOLOINDEX_PROD_01_REGISTRY_ENTRY_PHASE1*
