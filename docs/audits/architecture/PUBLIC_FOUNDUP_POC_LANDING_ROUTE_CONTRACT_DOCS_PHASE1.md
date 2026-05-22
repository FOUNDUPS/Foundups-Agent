# PUBLIC_FOUNDUP_POC_LANDING_ROUTE_CONTRACT_DOCS_PHASE1

**Worker**: W9
**Date**: 2026-05-23
**Status**: COMPLETE (DOCS_ONLY)
**Base commit**: post-PR #655 merge
**Mode**: Contract closeout documentation

---

## WSP 97 Truth Boundary Labels

| Label | Status |
|-------|--------|
| DOCS_ONLY | YES |
| CONTRACT_CLOSEOUT_ONLY | YES |
| WSP_FRAMEWORK_KNOWLEDGE_MIRROR_SYNC | YES |
| NO_RUNTIME_MUTATION | YES |
| NO_ROUTE_CREATION | YES |
| NO_CARD_BEHAVIOR_CHANGE | YES |
| NO_AUTH_CHANGE | YES |
| NO_PUBLIC_DEPLOYMENT | YES |
| NO_GOVERNANCE_ACTIVATION | YES |
| NO_CABR_READY | YES |
| NO_PAYOUT_READY | YES |
| NO_DAO_ACTIVATION | YES |

---

## 1. HoloIndex Assessment

### Query Executed
```
python holo_index.py --search "PUBLIC_FOUNDUP_POC_LANDING p.fMALL /f/ /f/{foundup_id} /app route contract PR 655 WSP 104" --limit 8
```

### Results Assessment

| Check | Result |
|-------|--------|
| Useful results | YES - WSP 104, route contracts surfaced |
| Noisy results | MODERATE - manifest tests not directly relevant |
| Missing results | Prior audit not in top 3 |
| Stale results | NO |
| WSP 104 surfaced | YES |
| Route contracts surfaced | YES |
| Fallback search required | NO |

---

## 2. Source Truth Consolidated

### 2.1 Prior Audit
`docs/audits/architecture/PUBLIC_FOUNDUP_POC_LANDING_AND_PFMALL_INTERACTION_AUDIT_PHASE1.md`
- Established card tap vs Enter FoundUp vs Launch App model
- Documented `/f/{foundup_id}` route already exists
- Identified portfolio gaps (since addressed by PR #655)

### 2.2 PR #655 Implementation
`feat(portfolio): public portfolio display component phase 1`
- Merged: 2026-05-22
- Created `/f/` portfolio showcase at index root
- Added `portfolio_data.json` static projection
- Updated `/f/index.html` route parsing

### 2.3 WSP 104 Semantics
- `/f/{foundup_id}` = landing / about / trust / entry surface
- `/f/{foundup_id}/app` = tenant app runtime root
- Registry-driven growth, not root sprawl

### 2.4 p.fMALL External Route Contract
- Control pipe (API/metadata) vs Experience pipe (navigation)
- In-scope route deployment preferred
- Shell owns discovery and route families

---

## 3. Canonical Route Truth (LOCKED)

### 3.1 Route Family Definitions

| Route | Purpose | Owner |
|-------|---------|-------|
| `/f/` | Public FoundUp portfolio showcase / directory | Shell |
| `/f/{foundup_id}` | Individual FoundUp public landing/about/trust/detail surface | FoundUp (within shell) |
| `/f/{foundup_id}/app` | Tenant app runtime root | FoundUp |
| `/f/{foundup_id}/app/{path...}` | Tenant-internal deep links | FoundUp |

### 3.2 Behavioral Contract

| Behavior | Contract |
|----------|----------|
| Card tap | Preview/video autoplay (non-destructive, stay in Mall context) |
| Visit/Enter FoundUp | Additive navigation to `/f/{foundup_id}` landing |
| Launch App | Navigation to `/f/{foundup_id}/app` tenant runtime |
| Direct-entry | Opt-in/configurable per FoundUp |
| Back to p.fMALL | Preserves context, returns to Mall |

### 3.3 Identity and Authorization

| Rule | Description |
|------|-------------|
| `foundup_id` is public | Public identifier for routing/discovery |
| `foundup_id` is not authorization | Gated actions must check auth/capability/role independently |
| No root route sprawl | FoundUps scale by registry, not by root pages |

### 3.4 Layer Separation

| Layer | Purpose | Example Routes |
|-------|---------|----------------|
| Public PoC | Discoverable showcase surface | `/f/`, `/f/{id}` |
| Member prototype | Auth-gated member features | `/member/` |
| App runtime | Tenant product surface | `/f/{id}/app` |
| Governance | DAO/voting surfaces | Reserved |

---

## 4. Route Contract Invariants

### 4.1 Growth Invariant
```
Scale = more manifests + more catalog entries
Scale != more root pages + more ad hoc rewrites
```

### 4.2 Namespace Invariant
```
One FoundUp -> one foundup_id -> one /f/{foundup_id} family -> one isolated tenant runtime
```

### 4.3 Behavioral Invariants

| Invariant | Status |
|-----------|--------|
| Card tap does not navigate away from Mall | PRESERVED |
| Enter FoundUp is explicit user action | PRESERVED |
| Landing surface separate from app runtime | PRESERVED |
| Back navigation preserves context | PRESERVED |
| Auth checked at action time, not route time | PRESERVED |

---

## 5. Files Updated

### 5.1 WSP 104 (Framework + Knowledge Mirror)
- Added Section 15: Public Portfolio Route Contract Closeout
- Locked `/f/` as portfolio showcase route
- Added post-PR #655 implementation notes

### 5.2 PFMALL_EXTERNAL_FOUNDUP_ROUTE_CONTRACT.md
- Added Section 11: Canonical Route Truth Summary
- Locked route family definitions
- Added behavioral contract reference

### 5.3 This Audit Document
- Created as canonical route contract closeout evidence

---

## 6. Mirror Validation

```bash
python - <<'PY'
from pathlib import Path
a = Path("WSP_framework/src/WSP_104_FoundUp_Route_Namespace_and_Tenant_Isolation_Protocol.md").read_text(encoding="utf-8")
b = Path("WSP_knowledge/src/WSP_104_FoundUp_Route_Namespace_and_Tenant_Isolation_Protocol.md").read_text(encoding="utf-8")
assert a == b, "WSP_104 framework/knowledge mirror drift"
print("WSP_104 mirrors identical")
PY
```

Result: PASS (mirrors identical after sync)

---

## 7. WSP 97 Verdict

| Check | Result |
|-------|--------|
| Documentation only | PASS |
| Contract closeout only | PASS |
| WSP framework/knowledge mirror synced | PASS |
| No runtime mutation | PASS |
| No route creation | PASS |
| No card behavior change | PASS |
| No auth change | PASS |
| No public deployment | PASS |

**Verdict**: PASS

---

## 8. Remaining Ambiguity

None. Route contract is now canonically locked.

Future slices may:
- Add portfolio fields (screenshots, demo videos)
- Enhance landing page display
- Implement governance routes

These do not change the route contract established here.

---

## Evidence Packet

```yaml
branch: docs/public-foundup-poc-landing-route-contract-phase1
base: origin/main (post-PR #655)

files_changed:
  - WSP_framework/src/WSP_104_FoundUp_Route_Namespace_and_Tenant_Isolation_Protocol.md
  - WSP_knowledge/src/WSP_104_FoundUp_Route_Namespace_and_Tenant_Isolation_Protocol.md
  - modules/foundups/docs/PFMALL_EXTERNAL_FOUNDUP_ROUTE_CONTRACT.md
  - docs/audits/architecture/PUBLIC_FOUNDUP_POC_LANDING_ROUTE_CONTRACT_DOCS_PHASE1.md

route_contract_summary:
  /f/: portfolio_showcase_directory
  /f/{foundup_id}: landing_about_trust_detail
  /f/{foundup_id}/app: tenant_app_runtime_root
  card_tap: video_preview_no_navigation
  enter_foundup: explicit_additive_navigation
  foundup_id: public_identifier_not_authorization

holoindex_assessment: USEFUL
mirror_validation: PASS
runtime_behavior_changed: NO
remaining_ambiguity: NONE
```

---

*Slice authored under WSP_00 -> WSP_50 -> WSP_87 -> WSP_97 -> WSP_104 -> WSP_102 -> WSP_22 -> WSP_81.*
*Slice: PUBLIC_FOUNDUP_POC_LANDING_ROUTE_CONTRACT_DOCS_PHASE1*
