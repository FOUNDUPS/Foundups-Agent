# PUBLIC_FOUNDUP_POC_LANDING_AND_PFMALL_INTERACTION_AUDIT_PHASE1

**Worker**: W6
**Date**: 2026-05-21
**Status**: COMPLETE (AUDIT_ONLY)
**Base commit**: `7091d1733`
**Mode**: Read-only architecture audit

---

## 1. HoloIndex Assessment

### Query Executed
```
python holo_index.py --search "p.fMALL card interaction FoundUp public PoC Landing bottom bar pinch zoom direct entry WSP 102 WSP 104" --limit 8
```

### Results (32 hits)
| Type | File | Relevance |
|------|------|-----------|
| DOCS | PFMALL_FOUNDUP_ENTRY_AND_STAKE_GATE_CONTRACT.md | Entry gate contract |
| WSP | WSP_86_0102_Modular_Navigation_Protocol.md | Navigation patterns |
| WSP | WSP_87_Code_Navigation_Protocol.md | Code navigation |
| CODE | moltbot_bridge/openclaw_dae.py | OpenClaw integration |

### Assessment
HoloIndex surfaced entry gate contract but missed tile field gestures documentation. Direct file inspection required for interaction inventory.

---

## 2. Current p.fMALL Interaction Inventory

### Source: `public/member/js/mall-tile-field.js` (lines 1-21)

| Gesture | Behavior | WSP Reference |
|---------|----------|---------------|
| **Tap tile** | Start lane autoplay through FoundUp's video queue (Shorts-style) | Video Mall |
| **Enter button** | Navigate to `/f/{foundup_id}` | WSP 104 canonical |
| **Pinch-out on tile** | Expand into FoundUp's video field | Tile field |
| **Pinch-in (expanded)** | Collapse back to Mall | Tile field |
| **Swipe** | Navigate snapped field (default) or glide (override) | Motion modes |
| **Double-tap** | Detection window 300ms | Tap guard |

### Motion Modes
- **Snap (default)**: Discrete paging like iPhone home screens
- **Glide**: Fluid scroll for browsing

### Density Presets
- 3x4, 3x5, 4x6, 5x8 (portrait-first dense walls)
- 6x3 (desktop wide viewport)

---

## 3. Current `/f/{foundup_id}` Landing Inventory

### Source: `public/f/index.html` (38KB, full implementation)

**The route `/f/{foundup_id}` ALREADY EXISTS with a complete landing page implementation.**

### Landing Page Components

| Component | Location | Purpose |
|-----------|----------|---------|
| Back nav | `<nav>` | "Back to Mall" link |
| Hero section | `.entry-hero` | Token symbol, name, tagline |
| Badges row | `.entry-badges` | Tier, lifecycle badges |
| Readiness block | `.entry-readiness-block` | Ready/Conditional/Discoverable status |
| Details table | `.entry-details` | Category, tier, lifecycle, etc. |
| What's Next | `.entry-what-next` | Readiness explanation |
| Description | `.entry-description` | FoundUp description |
| Launch App CTA | `.entry-launch-app-block` | Links to `/f/{id}/app` |
| Source CTA | `.entry-cta-block` | External URL if applicable |
| Red Dog FAB | `.entry-red-dog` | Floating concierge button |
| Concierge sheet | `.concierge-sheet` | Red Dog briefing panel |
| App mount | `.app-mount-container` | Iframe for tenant app |

### WSP 104 Route Parsing (lines 706-724)
```javascript
/f/{foundup_id}           -> landing surface
/f/{foundup_id}/app       -> app mount root (Phase 2)
/f/{foundup_id}/app/{...} -> app deep links
```

### Readiness States Supported
- `ready` - Green, "live frontend, direct shell handoff"
- `conditional` - Yellow, "working frontend with known gaps"
- `discoverable_only` - Gray, "backend service, no web frontend"

### Launch App Support
- Entry URL checked from catalog `item.entry_url`
- If present: iframe mount with header bar
- If absent: "App Not Ready" error screen

---

## 4. Current Route / Gate / Public Boundary Inventory

### WSP 104 Route Families

| Family | Owner | Purpose |
|--------|-------|---------|
| `/member/` | Shell | p.fMALL shell and browse surface |
| `/discover` | Shell | Reserved browse route |
| `/search` | Shell | Reserved search |
| `/wallet` | Shell | Reserved wallet |
| `/settings` | Shell | Reserved preferences |
| `/f/` | Shell (manages) | FoundUp namespace family |
| `/f/{foundup_id}` | FoundUp | Landing / about / trust / entry |
| `/f/{foundup_id}/app` | FoundUp | Tenant app runtime root |

### Current Public Boundaries

| Surface | Auth Required | Public Accessible |
|---------|---------------|-------------------|
| `/member/` (Mall) | Curtain pattern | Yes (with disclaimer) |
| `/f/{foundup_id}` | No (reads catalog) | Yes |
| `/f/{foundup_id}/app` | Depends on tenant | Varies |

### No Auth Gate on Landing
The landing page at `/f/{foundup_id}` fetches from `/member/mall-video-catalog.json` directly. No authentication required for landing page view.

---

## 5. FoundUp Surface Inventory

### Registry Entities with Public URLs

| foundup_id | public_url_or_route | launch_readiness | entity_type |
|------------|---------------------|------------------|-------------|
| gotjunk_001 | Cloud Run URL | conditional | foundup |
| kosei | Firebase URL | ready | foundup |
| voteballots | null | discoverable_only | skeleton_candidate |
| trade | null | discoverable_only | skeleton_candidate |
| magadoom_001 | null | discoverable_only | foundup |
| antifafm_001 | null | discoverable_only | foundup |
| pfmall | null | N/A | platform_layer |
| autopost | AI Studio URL | discoverable_only | external_foundup |

### Catalog Entities (mall-video-catalog.json)

| foundup_id | source_type | video_count | has_entry_url |
|------------|-------------|-------------|---------------|
| move2japan | youtube_channel | 594 | No |
| undaodu | youtube_channel | 512 | No |
| foundups_main | youtube_channel | 44 | No |
| antifafm | youtube_channel | 34 | No |
| linkedin_012 | linkedin_profile | 0 | No |
| linkedin_esingularity | linkedin_profile | 0 | No |
| linkedin_tsingularity | linkedin_profile | 0 | No |
| linkedin_foundups | linkedin_profile | 0 | No |

### Portfolio-Ready FoundUps
Only **2** have live, accessible web frontends:
1. **gotjunk_001** - Cloud Run (conditional readiness)
2. **kosei** - Firebase (ready)

---

## 6. Card Tap vs Enter FoundUp vs Launch App Model

### Current Model (Three-Tier)

```
CARD TAP                   ENTER FOUNDUP                 LAUNCH APP
    |                           |                            |
    v                           v                            v
Video autoplay            /f/{foundup_id}              /f/{id}/app
(Shorts-style)            Landing page                 Tenant iframe
    |                           |                            |
No navigation             Navigation                   Navigation
    |                           |                            |
Same context              New context                  App context
```

### Interaction Semantics

| Action | Result | Context |
|--------|--------|---------|
| **Card Tap** | Start video queue autoplay | Stay in Mall |
| **Enter FoundUp** | Navigate to `/f/{id}` landing | Leave Mall, enter landing |
| **Launch App** | Navigate to `/f/{id}/app` | Enter tenant app |
| **Back to Mall** | Return to `/member/` | Leave landing/app |

### Default Behavior Preserved
Card tap = video/about behavior (non-destructive, in-context preview)
Enter FoundUp = explicit navigation via button/drawer

---

## 7. Foundups.com Portfolio Gap Analysis

### Current State
- Landing pages exist at `/f/{id}`
- Catalog provides videos for 8 lanes
- Only 2 FoundUps have launchable apps
- No consolidated portfolio view

### Missing for Portfolio Surface

| Gap | Current | Needed |
|-----|---------|--------|
| Portfolio index | None | `/portfolio` or `/f/` index page |
| PoC screenshots | None | `poc_screenshot_url` field |
| PoC demo video | None | `poc_demo_video_url` field |
| Public status badge | `launch_readiness` | Exposed on landing |
| Team/creator info | `creator` (partial) | `team_members` array |
| Links section | None | `website`, `github`, `docs` links |
| Investment status | None | `investment_stage` field |
| Metrics | None | `user_count`, `transaction_volume` |

### Registry Fields Already Present
- `public_surface_status` (hidden, discoverable, listed)
- `poc_status` (idea, poc, proto, mvp, launch)
- `prototype_gate_status` (pending, passed, failed)
- `public_url_or_route`
- `mall_entry_status`

### Landing Page Already Has
- Token symbol, name, tagline
- Tier, lifecycle badges
- Readiness status with explanation
- Description
- Launch App button
- Red Dog concierge

---

## 8. Preserve / Extend / Create Matrix

| Component | Action | Rationale |
|-----------|--------|-----------|
| Card tap = video autoplay | **PRESERVE** | Core Shorts-style UX |
| Enter button = `/f/{id}` | **PRESERVE** | WSP 104 canonical |
| Pinch gestures | **PRESERVE** | Core navigation UX |
| Landing page structure | **PRESERVE** | Already comprehensive |
| Red Dog concierge | **PRESERVE** | AI interaction UX |
| Readiness block | **EXTEND** | Add screenshot/demo |
| Details table | **EXTEND** | Add links, team |
| Portfolio index | **CREATE** | `/portfolio` or `/f/` |
| Registry schema | **EXTEND** | Add portfolio fields |

---

## 9. New FoundUp Standard vs Legacy Migration Policy

### New FoundUp Standard (for new entries)
1. Must have `foundup_manifest.json`
2. Must have registry entry
3. Should have at least `discoverable_only` readiness
4. Should have tagline and description
5. Should have PoC screenshot if beyond idea stage

### Legacy Migration Policy (for existing)
| Lane | Current | Migration |
|------|---------|-----------|
| move2japan | Catalog only | Needs manifest, registry entry |
| undaodu | Catalog only | Brand/identity, not FoundUp |
| foundups_main | Catalog only | Brand/meta, not FoundUp |
| antifafm | Catalog + registry | Already migrated |

### Migration NOT Required
- `undaodu`, `foundups_main` - Brand channels, not FoundUps
- LinkedIn lanes - Identity/social, not FoundUps

---

## 10. WSP Ownership Recommendation

### WSP 102 (FoundUps Web Design Protocol)
Should own:
- Visual design standards (colors, typography)
- Click economy grading
- Authentication flow (curtain pattern)
- Touch target minimums
- Responsive breakpoints

Should NOT own:
- Route namespace definitions
- Tenant isolation rules
- Catalog schema

### WSP 104 (Route Namespace and Tenant Isolation)
Should own:
- `/f/{foundup_id}` namespace definition
- Landing vs app route separation
- Tenant data isolation
- Service worker scope

Already owns all above correctly.

### Gap: Portfolio Display Protocol
Consider creating **WSP 107 (FoundUp Portfolio Display Protocol)** to define:
- Portfolio index page requirements
- Public PoC showcase standards
- Investment-ready presentation checklist

---

## 11. WSP_15 Slice Ranking

### Priority 1: Schema Extension
**FOUNDUPS_PUBLIC_PORTFOLIO_STATUS_SCHEMA_PHASE1**
- Add portfolio fields to registry schema
- `poc_screenshot_url`, `poc_demo_video_url`, `website_url`, `github_url`
- Read-only, no runtime changes

### Priority 2: Landing Completeness Spec
**PFMALL_PUBLIC_LANDING_COMPLETENESS_SPEC_PHASE1**
- Define minimum fields for portfolio-quality landing
- Specify fallback behavior when fields missing
- Spec-only, no implementation

### Priority 3: Portfolio Index
**FOUNDUPS_PORTFOLIO_INDEX_PAGE_PHASE1**
- Create `/portfolio` or `/f/` index page
- List all `listed` or `discoverable` FoundUps
- Implementation

### Priority 4: Landing Enhancement
**PFMALL_LANDING_PORTFOLIO_FIELDS_PHASE1**
- Render new portfolio fields on landing
- Screenshots, links, team display
- Implementation

---

## 12. Recommended Docs PR Path

1. **This audit** -> PR for review
2. **Portfolio schema spec** -> Add fields to registry schema doc
3. **Landing completeness spec** -> Define requirements
4. **WSP 107 draft** (optional) -> Portfolio display protocol

---

## 13. Recommended First Implementation PR Path

**FOUNDUPS_PUBLIC_PORTFOLIO_STATUS_SCHEMA_PHASE1**

Scope:
1. Extend `foundup_registry.schema.json` with optional portfolio fields:
   - `poc_screenshot_url: string | null`
   - `poc_demo_video_url: string | null`
   - `website_url: string | null`
   - `github_url: string | null`
   - `docs_url: string | null`
2. Update example registry with sample values
3. Update schema tests
4. No runtime changes

Why first:
- Schema change is foundational
- No runtime risk
- Enables subsequent landing enhancements
- Follows existing schema/population pattern

---

## 14. WSP_97 Truth Boundary

### Labels Applied
- `DOCS_ONLY` - This is an audit document
- `AUDIT_ONLY` - Read-only analysis
- `NO_RUNTIME_MUTATION` - No code changes
- `NO_ROUTE_CREATION` - No new routes
- `NO_AUTH_CHANGE` - Auth unchanged
- `NO_PUBLIC_DEPLOYMENT` - No deployments
- `NO_CARD_BEHAVIOR_CHANGE` - Card tap preserved
- `NO_PFMALL_CATALOG_MUTATION` - Catalog unchanged
- `NO_GOVERNANCE_ACTIVATION` - No governance
- `NO_CABR_READY` - Not CABR-related
- `NO_PAYOUT_READY` - Not payout-related
- `NO_DAO_ACTIVATION` - No DAO action

### Truth Assertions

| Assertion | Evidence |
|-----------|----------|
| `/f/{id}` route already exists | `public/f/index.html` exists (38KB) |
| Card tap = video autoplay | `mall-tile-field.js` line 8 |
| Enter = `/f/{id}` navigation | `mall-tile-field.js` line 9 |
| Launch App = `/f/{id}/app` | `public/f/index.html` lines 720-724 |
| Landing has Red Dog | `public/f/index.html` lines 661-663 |
| Only 2 launchable apps | gotjunk_001, kosei in registry |

---

## Evidence Packet

```yaml
branch: docs/public-foundup-poc-landing-audit-phase1
base_commit: 7091d1733

files_created:
  - docs/audits/architecture/PUBLIC_FOUNDUP_POC_LANDING_AND_PFMALL_INTERACTION_AUDIT_PHASE1.md

holoindex_assessment: PARTIAL
  - Entry gate contract found
  - Tile field gestures required direct inspection

wsp_97_verdict: PASS
  - DOCS_ONLY
  - AUDIT_ONLY
  - NO_RUNTIME_MUTATION
  - NO_CARD_BEHAVIOR_CHANGE
  - NO_PFMALL_CATALOG_MUTATION

wsp_15_next_slice: FOUNDUPS_PUBLIC_PORTFOLIO_STATUS_SCHEMA_PHASE1
  - Extend registry schema with portfolio fields
  - No runtime changes
  - Foundation for landing enhancements

w10_readiness: READY
  - Single audit doc
  - No implementation
  - Commit locally, W10 handles PR
```
