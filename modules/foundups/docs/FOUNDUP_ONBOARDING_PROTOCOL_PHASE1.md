# FoundUp Onboarding Protocol - Phase 1

**Document Type**: Module-Level Protocol  
**Location**: `modules/foundups/docs/FOUNDUP_ONBOARDING_PROTOCOL_PHASE1.md`  
**Created**: 2026-05-25  
**Author**: W9  
**Status**: ACTIVE  

---

## Purpose

This protocol defines the canonical steps for onboarding a new FoundUp into the monorepo. It prevents workers from re-discovering registry/catalog/manifest locations each time and ensures consistent representation across all FoundUps infrastructure.

**Scope**: Registry seed, manifest creation, module scaffold, catalog decisions. Does NOT cover runtime implementation, DNS activation, or public launch.

---

## 1. Canonical Representation Locations

Every new FoundUp may need representation in the following locations:

### 1.1 Required Locations

| Location | Purpose | Required For |
|----------|---------|--------------|
| `modules/foundups/foundup_registry.json` | Canonical registry entry | ALL FoundUps |
| `modules/foundups/{id}/foundup_manifest.json` | Lifecycle/stage/tier metadata | ALL FoundUps with module_path |
| `modules/foundups/{id}/README.md` | Purpose, outcome, roadmap summary | ALL FoundUps with module_path |
| `modules/foundups/{id}/INTERFACE.md` | Public contracts (future or current) | ALL FoundUps with module_path |
| `modules/foundups/{id}/ROADMAP.md` | Stage progression plan | ALL FoundUps with module_path |
| `modules/foundups/{id}/ModLog.md` | Change history | ALL FoundUps with module_path |

### 1.2 Optional Locations (Decision Required)

| Location | Purpose | When Required |
|----------|---------|---------------|
| `public/member/mall-catalog.json` | p.fMALL shell catalog | Only if `mall_entry_status` != `not_listed` |
| `public/member/mall-video-catalog.json` | Video mall catalog | Only if media FoundUp with video surface |
| `public/f/portfolio_data.json` | Portfolio projection | Only if `portfolio_status` != `not_portfolio` |
| `modules/foundups/{id}/src/` | Implementation code | Only after POC phase begins |
| `modules/foundups/{id}/tests/` | Test suite | Only after implementation exists |
| Route contract docs | Route/API definitions | Only after public surface is planned |

### 1.3 External FoundUp Locations

For `entity_type: external_foundup`:

| Location | Purpose |
|----------|---------|
| External repo (e.g., `O:/repos/{name}/`) | Source code lives outside monorepo |
| `modules/foundups/foundup_registry.json` | Registry entry with `module_path: null` |
| `related_external_repo` field | Points to external GitHub URL |

---

## 2. Entity Type Decision Tree

Before onboarding, classify the entity:

```
Is this a consumer-facing venture?
├─ YES: Does it have its own token economics?
│   ├─ YES: Does source live in monorepo?
│   │   ├─ YES → entity_type: foundup
│   │   └─ NO  → entity_type: external_foundup
│   └─ NO: Is it planned to have tokens?
│       ├─ YES (future) → entity_type: skeleton_candidate
│       └─ NO (never) → entity_type: access_service
└─ NO: Is it infrastructure?
    ├─ YES: Does it serve multiple FoundUps?
    │   ├─ YES → entity_type: infra_service
    │   └─ NO  → entity_type: platform_layer
    └─ NO: Is it a development tool?
        └─ YES → entity_type: tool_simulator
```

### Entity Type Definitions

| Type | Description | Has Tokens | Has Module |
|------|-------------|------------|------------|
| `foundup` | Full FoundUp with token economics | YES | YES |
| `external_foundup` | FoundUp with source outside monorepo | YES | NO (null) |
| `skeleton_candidate` | Planned FoundUp, not yet implemented | PLANNED | YES |
| `access_service` | Service funnel without own tokens | NO | YES |
| `infra_service` | Shared infrastructure component | N/A | YES |
| `platform_layer` | Platform shell/orchestration | N/A | YES |
| `tool_simulator` | Development/simulation tool | N/A | YES |

---

## 3. Registry Entry Template

```json
{
  "foundup_id": "{lowercase_underscore_id}",
  "display_name": "{Human Readable Name}",
  "entity_type": "{see decision tree}",
  "module_path": "modules/foundups/{id}",
  "stage": "incubating",
  "tier": "F0_DAE",
  "implementation_status": "SPECIFIED",
  "public_surface_status": "hidden",
  "poc_status": "idea",
  "prototype_gate_status": "pending",
  "manifest_status": "exists",
  "manifest_path": "modules/foundups/{id}/foundup_manifest.json",
  "hermes_openclaw_build_status": "none",
  "token_status": "TOKEN_DEFERRED",
  "token_symbol": null,
  "evidence_docs": [
    "docs/audits/architecture/{ID}_ONBOARDING_AUDIT_PHASE1.md"
  ],
  "next_slice": "{ID}_POC_PHASE1",
  "public_url_or_route": null,
  "mall_entry_status": "not_listed",
  "invite_required": true,
  "notes": "{Brief description. Stage: SPECIFIED_NOT_IMPLEMENTED}",
  "audit_date": "{YYYY-MM-DD}",
  "auditor": "{Worker ID}",
  "portfolio_status": "not_portfolio",
  "poc_landing_status": "none",
  "website_url": null,
  "poc_url": null,
  "app_url": null,
  "github_url": null,
  "docs_url": null,
  "screenshot_url": null,
  "public_summary": null,
  "portfolio_priority": null,
  "portfolio_ready": false,
  "portfolio_evidence_docs": []
}
```

---

## 4. Manifest Template

```json
{
  "foundup_id": "{id}",
  "manifest_version": "1.0.0",
  "lifecycle_stage": "incubating",
  "tier": "F0_DAE",
  "implementation_status": "SPECIFIED",
  "runtime_status": "NO_RUNTIME",
  "poc_status": "idea",
  "token_status": "TOKEN_DEFERRED",
  "created_date": "{YYYY-MM-DD}",
  "last_updated": "{YYYY-MM-DD}",
  "maintainer": "{Worker ID}",
  "dependencies": [],
  "next_slice": "{ID}_POC_PHASE1"
}
```

---

## 5. Catalog/Projection Update Rules

### 5.1 When to Add to Catalog

| Condition | mall-catalog.json | mall-video-catalog.json | portfolio_data.json |
|-----------|-------------------|-------------------------|---------------------|
| Registry seed only | NO | NO | NO |
| POC implemented | NO | NO | NO |
| Prototype ready | MAYBE (discoverable) | MAYBE | NO |
| MVP ready | YES (listed) | IF media | MAYBE |
| Launch ready | YES (promoted) | IF media | YES |

### 5.2 Default for New FoundUps

**DEFAULT**: Do NOT add to any catalog during initial onboarding.

Catalogs should only be updated when:
1. `poc_status` >= `poc` (working proof-of-concept exists)
2. `implementation_status` = `IMPLEMENTED`
3. Tests validate catalog entry schema compliance

### 5.3 Future Slice for Catalog Entry

If catalog entry is deferred, record:
```json
"next_slice": "{ID}_PFMALL_DISCOVERABLE_ENTRY_PHASE1"
```

---

## 6. DNS/Domain Rules

### 6.1 Prohibited During Onboarding

- NO DNS record creation
- NO GoDaddy mutation
- NO subdomain activation
- NO SSL certificate provisioning

### 6.2 Proposed Domain Recording

Record proposed domain in `notes` field only:
```json
"notes": "Proposed future host: {name}.foundups.com. Not configured."
```

Domain activation requires separate slice:
```
{ID}_DNS_AND_DOMAIN_ACTIVATION_PHASE1
```

---

## 7. WSP Promotion Criteria

This protocol is a **module-level protocol**, not a formal WSP.

**Promote to WSP when**:
1. Protocol has been used for 3+ FoundUp onboardings
2. No structural changes were needed between uses
3. Pattern is stable and reusable
4. 012 approves formalization

**Promotion slice**:
```
FOUNDUP_ONBOARDING_PROTOCOL_WSP_PROMOTION_PHASE1
```

---

## 8. Onboarding Checklist

Use this checklist when onboarding a new FoundUp:

```markdown
## FoundUp Onboarding Checklist: {ID}

### Pre-Onboarding
- [ ] Entity type classified (decision tree)
- [ ] foundup_id chosen (lowercase_underscore)
- [ ] display_name chosen
- [ ] tier assigned (default: F0_DAE)
- [ ] HoloIndex search completed (no existing entry)

### Registry
- [ ] Entry added to foundup_registry.json
- [ ] Schema validation passes
- [ ] implementation_status = SPECIFIED
- [ ] token_status = TOKEN_DEFERRED
- [ ] manifest_status = exists
- [ ] manifest_path set correctly

### Module Directory
- [ ] modules/foundups/{id}/ created
- [ ] foundup_manifest.json created
- [ ] README.md created
- [ ] INTERFACE.md created
- [ ] ROADMAP.md created
- [ ] ModLog.md created

### Catalog Decision
- [ ] mall-catalog.json decision: YES/NO (default: NO)
- [ ] mall-video-catalog.json decision: YES/NO (default: NO)
- [ ] portfolio_data.json decision: YES/NO (default: NO)
- [ ] If NO, next_slice recorded for future catalog entry

### Validation
- [ ] Registry schema tests pass
- [ ] Registry loader tests pass
- [ ] No duplicate foundup_id

### Documentation
- [ ] Audit doc created
- [ ] WSP_97 Truth Boundary Checklist completed
- [ ] Next slice documented
```

---

## 9. Related Documents

- Schema: `modules/foundups/foundup_registry.schema.json`
- Loader: `modules/foundups/src/foundup_registry_loader.py`
- Tests: `modules/foundups/tests/test_foundup_registry_schema.py`
- Route Protocol: `WSP_framework/src/WSP_104_FoundUp_Route_Namespace_and_Tenant_Isolation_Protocol.md`
- Web Design: `WSP_framework/src/WSP_102_FoundUps_Web_Design_Protocol.md`
- API Gateway: `WSP_framework/src/WSP_106_FoundUp_API_Gateway_Protocol.md`

---

## 10. Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2026-05-25 | W9 | Initial protocol created. Shield as first consumer. |
