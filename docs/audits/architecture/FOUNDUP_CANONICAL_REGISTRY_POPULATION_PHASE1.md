# FOUNDUP_CANONICAL_REGISTRY_POPULATION_PHASE1

**Worker**: W6  
**Date**: 2026-05-18  
**Status**: COMPLETE  
**Prerequisite**: PR #630 (Schema Phase 1) merged

## Objective

Populate the canonical registry data file with all evidence-backed FoundUp entries discovered in manifests and prior audits.

## Data Sources

### Manifest Files Discovered (7)
1. `modules/foundups/gotjunk/foundup_manifest.json` - gotjunk_001
2. `modules/foundups/kosei/foundup_manifest.json` - kosei
3. `modules/foundups/voteballots/foundup_manifest.json` - voteballots
4. `modules/foundups/trade/foundup_manifest.json` - trade
5. `modules/gamification/whack_a_magat/foundup_manifest.json` - magadoom_001
6. `modules/platform_integration/antifafm_broadcaster/foundup_manifest.json` - antifafm_001
7. `holo_index/infra/foundup_manifest.json` - holo_index (infra, excluded)

### Prior Audit Documents
- `FOUNDUP_CANONICAL_INVENTORY_AND_STAGE_REGISTRY_AUDIT_PHASE1.md`
- `FOUNDUP_PUBLIC_SURFACE_STATUS_AUDIT_PHASE1.md`
- `MOVE2JAPAN_FOUNDUP_ROLE_AUDIT_PHASE1.md`
- `AUTOPOST_EXTERNAL_FOUNDUP_COMPLETION_AUDIT_PHASE1.md`
- `PQN_PORTAL_SCIENCE_SWARM_DRIFT_AUDIT_PHASE1.md`

## Registry Entries Created (14)

### Manifest-Bearing FoundUps (6)

| foundup_id | entity_type | token_status | token_symbol | impl_status |
|------------|-------------|--------------|--------------|-------------|
| gotjunk_001 | foundup | EXISTS | JUNK | IMPLEMENTED |
| kosei | foundup | EXISTS | KOSEI | IMPLEMENTED |
| voteballots | skeleton_candidate | EXISTS | VOTE | SPECIFIED |
| trade | skeleton_candidate | EXISTS | TRADE | SPECIFIED |
| magadoom_001 | foundup | EXISTS | DOOM | IMPLEMENTED |
| antifafm_001 | foundup | EXISTS | ANTI | IMPLEMENTED |

### Platform/Infrastructure (4)

| foundup_id | entity_type | token_status | notes |
|------------|-------------|--------------|-------|
| pfmall | platform_layer | NOT_APPLICABLE | Shell/funnel interaction surface |
| agent_market | infra_service | NOT_APPLICABLE | CABR/FAM daemon |
| simulator | tool_simulator | NOT_APPLICABLE | Economic simulation engine |
| social_twin | infra_service | NOT_APPLICABLE | Cross-FoundUp reporting layer |

### External FoundUps (2)

| foundup_id | entity_type | repo | impl_status |
|------------|-------------|------|-------------|
| autopost | external_foundup | github.com/FOUNDUPS/autopost.git | IMPLEMENTED |
| science_swarm_hub | external_foundup | github.com/FOUNDUPS/science-swarm-hub | IMPLEMENTED |

### Access Service (1)

| foundup_id | entity_type | notes |
|------------|-------------|-------|
| move2japan | access_service | YouTube monitor + stakeholder funnel. DO NOT DELETE. |

### Skeleton Candidate (1)

| foundup_id | entity_type | notes |
|------------|-------------|-------|
| pqn_portal | skeleton_candidate | SCAFFOLD status. Frontend exists but not deployed. |

## Boundary: Registry vs pFMALL Catalogs

The canonical FoundUp registry (`foundup_registry.json`) does **not** replace:
- `catalog.json` (pFMALL Launch Catalog per PFMALL_SHELL_CONTRACT.md)
- `mall-video-catalog.json` (Video Mall catalog per PFMALL_VIDEO_MALL_CATALOG_SCHEMA.md)
- pFMALL runtime manifests or routing catalogs

**Separation of concerns**:
- **Canonical registry**: "What exists, what class is it, what stage is it in, what can builders touch?" (Hermes/OpenClaw build contract)
- **pFMALL catalogs**: "What does the Mall show/route/render?" (Runtime display/routing)

The registry may later validate or generate projections for pFMALL catalogs, but Phase 1 is inventory/build-contract only. Note that `pfmall` itself is classified as `entity_type: platform_layer` with `manifest_status: not_applicable` — it is the container, not a FoundUp.

## WSP 97 Compliance

### Truth Boundary Constraints
- NO runtime changes
- NO token assignment (only documented existing: JUNK, KOSEI, VOTE, TRADE, DOOM, ANTI)
- NO manifest creation
- NO stage promotion
- Classification only from evidence

### Token Status Rules Applied
- `EXISTS`: Token symbol documented in manifest (6 entries)
- `TOKEN_DEFERRED`: No evidence of token assignment (4 entries)
- `NOT_APPLICABLE`: Platform/infra/tools not tokenizable (4 entries)

## Test Results

```
30 passed in 0.25s

TestProductionRegistryValidation:
- test_production_file_exists PASSED
- test_production_validates_against_schema PASSED
- test_production_has_expected_entity_count PASSED
- test_production_entity_ids_unique PASSED
- test_production_has_manifest_foundups PASSED
- test_production_external_foundups_have_repos PASSED
- test_production_foundups_have_tier_and_stage PASSED
- test_production_token_exists_has_symbol PASSED
```

## Files Created/Modified

### Created
- `modules/foundups/foundup_registry.json` (14 entities, 396 lines)

### Modified
- `modules/foundups/tests/test_foundup_registry_schema.py` (added 8 production validation tests)
- `modules/foundups/ModLog.md` (population phase entry)

## Next Steps

None - population complete. Future additions require:
1. New manifest discovery
2. Audit evidence linking
3. Schema validation pass
4. PR review

## Evidence Packet

```yaml
files_created:
  - modules/foundups/foundup_registry.json
  - docs/audits/architecture/FOUNDUP_CANONICAL_REGISTRY_POPULATION_PHASE1.md

files_modified:
  - modules/foundups/tests/test_foundup_registry_schema.py
  - modules/foundups/ModLog.md

test_results:
  passed: 30
  failed: 0
  
entities_populated: 14
  foundup: 4
  skeleton_candidate: 3
  platform_layer: 1
  infra_service: 2
  tool_simulator: 1
  access_service: 1
  external_foundup: 2

wsp_compliance:
  - WSP_97: PASS (truth boundary respected)
  - WSP_87: PASS (evidence-backed classification)
  - WSP_15: PASS (no token invention)
  - WSP_50: PASS (pre-action verification)
```
