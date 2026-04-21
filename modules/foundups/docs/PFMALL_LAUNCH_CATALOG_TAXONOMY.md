# p.fMALL Launch Catalog Taxonomy

**Status**: Architecture specification (first tranche) — reconciled 2026-04-21
**Owner**: 0102
**Slice**: `pfmall_architecture_and_template_contract`
**Reconciled**: PFMALL-LAUNCH-CATALOG-TAXONOMY-RECON (W2, 2026-04-21)
**WSP References**: WSP 3 (Domains), WSP 97 (Truth), WSP 100 (SmartDAO Tiers), WSP 104 (Namespace)

---

## WSP 97 Implementation Status

| Feature | Status | Evidence |
|---------|--------|----------|
| Catalog file (`mall-video-catalog.json`) | `IMPLEMENTED_IN_CATALOG` | 13 entries in `public/member/mall-video-catalog.json` |
| Category taxonomy | `PARTIAL` | Spec defined 5 categories; catalog uses 9 (`travel`, `music`, `startup`, `media`, `marketplace`, `science`, `thought-leadership`, `ai-education`, `ai-research`). `games` and `community` specified but not in catalog. |
| FoundUp portfolio classification | `PARTIAL` | Spec listed 6 FoundUps; catalog contains 13. 3 spec entries (Whack-a-Magot, YouTube Engagement, LinkedIn Agent) absent from catalog. Kosei was missing from spec entirely. |
| Bound tenant manifests | `IMPLEMENTED_IN_MANIFESTS` | `gotjunk_001` and `kosei` have `foundup_manifest.json` with `routing_prefix` + `data_namespace`. All other FoundUps are discoverable-only (catalog presence, not yet bound). |
| Namespace guardrail testing | `IMPLEMENTED_IN_TESTS` | `test_namespace_guardrail.py` validates WSP 104 constraints for bound tenants |
| HMAC manifest signing | `SPECIFIED_NOT_IMPLEMENTED` | All manifests have `signature: ""`. `skill_manifest_guard.py` exists for WRE skills, not extended to FoundUp manifests. |
| `required_subscription_tier` enum | `SPECIFIED_NOT_IMPLEMENTED` | No `required_subscription_tier` field in actual catalog entries. Spec used `angel, ultimate`; codebase uses `free, starter, basic, plus, pro, enterprise` (per `subscription_tiers.py`). |
| `is_invite_only` field | `SPECIFIED_NOT_IMPLEMENTED` | Not present in actual catalog entries |
| Launch readiness gating | `PARTIAL` | `shell_core.py` validates `launch_readiness` in manifests. Only bound tenants have it (`conditional`, `ready`). Discoverable-only entries use `discoverable_only`. |
| Display rules (badges, tier gates) | `SPECIFIED_NOT_IMPLEMENTED` | Current mall is video tile overlay — no badge rendering, no tier-gated click-through |
| Catalog versioning | `SPECIFIED_NOT_IMPLEMENTED` | No version field in `mall-video-catalog.json` |
| External FoundUp linking | `PARTIAL` | `science_swarm` and `autopost` marked `externalized` in catalog but no `external_url` field exists in catalog schema |

**Phase 1 reality**: `mall-video-catalog.json` is the operational catalog with 13 FoundUps across 9 categories. All 13 are FoundUps — videos are the catalog layer telling each FoundUp's story. 2 are bound FoundUps (gotjunk_001, kosei) with full manifest/route/namespace binding. The remaining 11 are discoverable-only FoundUps with catalog presence through video tiles, not yet bound as tenants. Badge rendering, tier gating, HMAC signing, and catalog versioning are Phase 2.

---

## 1. Purpose

p.fMALL is an **AI interaction space** — a new way of interacting with AI and the world. Video is the default surface, but the paradigm extends to any content type: documents, community, FoundUps. The same interaction model (pinch, zoom, navigate) works everywhere, with AI mediating all engagement. Built for FoundUps first, with hooks into all content.

Videos are the **catalog layer** — they tell each FoundUp's story. Every FoundUp in the catalog is a FoundUp, regardless of binding maturity. The distinction is not "FoundUp vs content" but "bound FoundUp vs discoverable-only FoundUp."

This document defines the category taxonomy for FoundUps in the p.fMALL catalog, classifies the current portfolio, and establishes rules for catalog membership and binding maturity progression.

---

## 2. Category Taxonomy

### 2.1 Categories

**Spec-defined categories** (original architecture):

| Category | Slug | Description |
|----------|------|-------------|
| **Marketplace** | `marketplace` | Buy/sell/trade platforms (goods, services, assets) |
| **Media** | `media` | Broadcasting, content creation, social publishing |
| **Science** | `science` | Research tools, data analysis, scientific collaboration |
| **Games** | `games` | Interactive entertainment, white-label game families |
| **Community** | `community` | Engagement tools, moderation, social coordination |

**Additional categories in actual catalog** (`mall-video-catalog.json`):

| Category | Slug | Description | Entries |
|----------|------|-------------|---------|
| **Travel** | `travel` | Location-based content, relocation guides | move2japan |
| **Music** | `music` | Music production, DJ sets, audio content | undaodu |
| **Startup** | `startup` | Entrepreneurship, venture building | foundups_main, linkedin_foundups |
| **Thought Leadership** | `thought-leadership` | Industry perspectives, opinion | linkedin_012 |
| **AI Education** | `ai-education` | AI learning, tutorials, courses | linkedin_esingularity, eduit |
| **AI Research** | `ai-research` | AI research, papers, experiments | linkedin_tsingularity |

> **Drift note**: Catalog has 9 categories total. `games` and `community` are specified but have no catalog entries. 4 categories (`travel`, `music`, `thought-leadership`, `ai-research`) emerged organically and were never added to this spec via WSP governance.

### 2.2 Category Rules

1. **Infrastructure is never a category**. OpenClaw, WRE, HoloIndex are substrate — they never appear in the catalog.
2. **Categories are extensible**. New categories added by WSP governance (propose via WSP process, not ad hoc).
3. **One primary category per FoundUp**. A FoundUp can have tags for secondary discovery, but one primary category for catalog display.
4. **Categories are user-facing**. Slugs are URL-stable (`/discover?category=marketplace`).

---

## 3. Actual FoundUp Portfolio

Source of truth: `public/member/mall-video-catalog.json` (13 entries).

### 3.1 Bound Tenants (Full Manifest Binding)

These FoundUps have `foundup_manifest.json`, `routing_prefix`, and `data_namespace` — they can load inside the shell and have isolated data.

| FoundUp | `foundup_id` | Category | Tier | Lifecycle | Launch Readiness | Route | Namespace |
|---------|-------------|----------|------|-----------|-----------------|-------|-----------|
| **GotJunk** | `gotjunk_001` | marketplace | F0_DAE | proto | conditional | `/f/gotjunk_001` | `idb_gotjunk_001` |
| **Kosei** | `kosei` | media | F0_DAE | incubating | ready | `/f/kosei` | `idb_kosei` |

### 3.2 Discoverable-Only FoundUps

These FoundUps have catalog presence through video tiles (the catalog layer) but have no manifest, no route binding, and no iframe loading yet. Binding is a maturity step — these are valid FoundUps at an earlier stage of the binding lifecycle.

| FoundUp | `foundup_id` | Category | Tier | Lifecycle | Launch Readiness |
|---------|-------------|----------|------|-----------|-----------------|
| **Move2Japan** | `move2japan` | travel | F0_DAE | active | discoverable_only |
| **UndaOdu** | `undaodu` | music | F0_DAE | active | discoverable_only |
| **FoundUps Main** | `foundups_main` | startup | F0_DAE | active | discoverable_only |
| **antifaFM** | `antifafm` | media | F0_DAE | proto | discoverable_only |
| **LinkedIn 012** | `linkedin_012` | thought-leadership | F0_DAE | staging | discoverable_only |
| **LinkedIn eSingularity** | `linkedin_esingularity` | ai-education | F0_DAE | staging | discoverable_only |
| **LinkedIn tSingularity** | `linkedin_tsingularity` | ai-research | F0_DAE | staging | discoverable_only |
| **LinkedIn FoundUps** | `linkedin_foundups` | startup | F0_DAE | staging | discoverable_only |
| **EduIT** | `eduit` | ai-education | F0_DAE | staging | discoverable_only |
| **Science Swarm** | `science_swarm` | science | F0_DAE | externalized | discoverable_only |
| **AutoPost** | `autopost` | media | F0_DAE | externalized | discoverable_only |

### 3.3 FoundUps Not Yet in Catalog

These are FoundUps recognized in the original taxonomy that have not yet entered `mall-video-catalog.json`. They are FoundUps — the catalog entry is a maturity step, not a classification gate.

| FoundUp | Original Category | Original Lifecycle | Status |
|---------|------------------|--------------------|--------|
| **Whack-a-Magot** | games | incubating | FoundUp at concept stage — needs catalog entry to become discoverable |
| **YouTube Engagement** | community | incubating | FoundUp — needs catalog entry |
| **LinkedIn Agent** | community | incubating | FoundUp — possibly subsumed by the 4 LinkedIn-prefixed FoundUps above |

### 3.4 NOT in Catalog (Infrastructure)

| Module | Why Excluded |
|--------|-------------|
| OpenClaw | Control plane — substrate, not product |
| WRE | Execution layer — substrate, not product |
| HoloIndex | Memory/retrieval — substrate, not product |
| FAM DAEmon | Agent market internals — substrate |
| WSP Framework | Protocol governance — substrate |
| Simulator | Economics tooling — substrate |

### 3.5 External FoundUps

| FoundUp | `foundup_id` | Category | Integration |
|---------|-------------|----------|-------------|
| **Science Swarm Hub** | `science_swarm` | science | Discoverable-only tile in catalog; own repo (`O:\repos\science-swarm-hub`) |
| **AutoPost** | `autopost` | media | Discoverable-only tile in catalog; own repo (`O:\repos\AutoPost`) |

> **Note**: These are marked `externalized` in catalog but currently function as discoverable-only video tiles. No `external_url` field exists in the catalog schema to link to their deployments.

---

## 4. Catalog Entry Schema

### 4.1 Actual Schema (`mall-video-catalog.json`)

The operational catalog uses this structure (not the originally specified schema):

```json
{
  "foundup_id": "string (human-readable slug, e.g. 'gotjunk_001', 'kosei')",
  "category": "marketplace | media | science | travel | music | startup | thought-leadership | ai-education | ai-research",
  "tier": "F0_DAE",
  "lifecycle_stage": "active | staging | proto | incubating | externalized",
  "launch_readiness": "ready | conditional | discoverable_only",
  "routing_prefix": "string | '' (only bound tenants, e.g. '/f/gotjunk_001')",
  "data_namespace": "string | '' (only bound tenants, e.g. 'idb_gotjunk_001')",
  "video_channels": ["array of video channel objects"],
  "video_tiles": ["array of video tile objects"]
}
```

### 4.2 Originally Specified Schema (Not Fully Implemented)

> **WSP 97 `PARTIAL`**: The originally specified schema below is an architectural target. Fields marked with `†` are not present in the actual catalog.

```json
{
  "foundup_id": "string (human-readable slug — NOT 16-char hex as originally specified)",
  "name": "string †",
  "tagline": "string (max 80 chars) †",
  "category": "9 actual categories (not the original 5)",
  "tier": "F0_DAE | F1_OPO | F2_GROWTH | F3_INFRA | F4_MEGA | F5_SYSTEMIC",
  "lifecycle_stage": "active | staging | proto | incubating | externalized (actual) — plus federated (spec only)",
  "required_subscription_tier": "free | starter | basic | plus | pro | enterprise † (per subscription_tiers.py — NOT angel | ultimate)",
  "is_invite_only": "boolean †",
  "icon_url": "string †",
  "manifest_url": "string (path to foundup_manifest.json) †",
  "external_url": "string | null (for externalized FoundUps) †"
}
```

### 4.3 Display Rules

> **WSP 97 `SPECIFIED_NOT_IMPLEMENTED`**: Current mall renders video tiles — no badge system, no tier-gated click-through. Rules below are architectural targets.

| Lifecycle Stage | Catalog Display (Target) |
|-----------------|--------------------------|
| incubating | Card with "Coming Soon" badge, no click-through |
| proto | Card with "Early Access" badge, click loads if tier sufficient |
| externalized | Card with "External" badge, click opens external_url |
| federated | Card (normal), click loads in iframe |

| Invite Status | Catalog Display (Target) |
|---------------|--------------------------|
| invite_only: true | "Angel Access" badge, tier gate on click |
| invite_only: false | Normal card, tier gate on click |

---

## 5. Launch Order

### 5.1 Phase 1: Bound Tenants (Current)

**Priority 1: GotJunk** (`gotjunk_001`)
- Status: proto, launch_readiness: conditional
- Bound tenant with manifest, route (`/f/gotjunk_001`), namespace (`idb_gotjunk_001`)
- Why first: Clear product boundary, proven multi-PWA pattern, marketplace category validates UPs spending
- Blockers: `launch_readiness: conditional` — deploy blocker (Cloud Run stale, CSP unverified)

**Priority 2: Kosei** (`kosei`)
- Status: incubating, launch_readiness: ready
- Bound tenant with manifest, route (`/f/kosei`), namespace (`idb_kosei`)
- Why second: PWA deployed, route bound, namespace isolated
- Note: Was missing entirely from original taxonomy spec

### 5.2 Phase 2: Promote Discoverable-Only to Bound Tenant

To promote a discoverable-only entry to a bound tenant:
1. Create `foundup_manifest.json` in `modules/foundups/{foundup_id}/`
2. Add `routing_prefix` (`/f/{foundup_id}`) and `data_namespace` (`idb_{foundup_id}`) to catalog entry
3. Validate with `test_namespace_guardrail.py`
4. Update `launch_readiness` from `discoverable_only` to `conditional` or `ready`

Candidates (by current lifecycle proximity):
- antifaFM (proto — closest to bound-tenant readiness)
- AutoPost (externalized — needs adapter, own repo)
- Science Swarm (externalized — needs adapter, own repo)

### 5.3 Phase 3: Concept-Stage FoundUps

- Whack-a-Magot (not in catalog — needs PoC, then catalog entry, then manifest)
- YouTube Engagement (not in catalog — needs catalog entry)

### 5.4 Launch Readiness Gate

A FoundUp is ready for **bound tenant** status when:

1. Has valid `foundup_manifest.json` (all required fields per `PFMALL_FOUNDUP_MANIFEST_SCHEMA.md`)
2. Has `routing_prefix` and `data_namespace` in catalog entry
3. Passes `test_namespace_guardrail.py` validation
4. Has working `entry_url` (bundle loads without errors)
5. `shell_core.py` `validate_manifest()` passes

> **WSP 97 `SPECIFIED_NOT_IMPLEMENTED`**: The following gates are specified but not enforced: HMAC manifest signing, shell "ready" handshake, sentinel rate limit testing, CABR contract documentation.

---

## 6. Catalog Maintenance

### 6.1 Adding a Discoverable-Only Entry

```
1. Add entry to mall-video-catalog.json with video_channels/video_tiles
2. Set lifecycle_stage (active, staging, incubating, externalized)
3. Set launch_readiness: discoverable_only
4. Leave routing_prefix and data_namespace empty
```

### 6.2 Upgrading to Bound Tenant

```
1. Create foundup_manifest.json (per PFMALL_FOUNDUP_MANIFEST_SCHEMA.md)
2. Add routing_prefix (/f/{foundup_id}) to catalog entry
3. Add data_namespace (idb_{foundup_id}) to catalog entry
4. Update launch_readiness to conditional or ready
5. Run test_namespace_guardrail.py to validate WSP 104 compliance
6. Validate manifest with shell_core.py validate_manifest()
```

> **WSP 97 `SPECIFIED_NOT_IMPLEMENTED`**: Steps 2-3 of the originally specified flow (HMAC sign manifest, bump catalog version) are not implemented.

### 6.3 Removing a FoundUp

```
1. Remove entry from mall-video-catalog.json
2. FoundUp manifest and data remain (not deleted)
3. FoundUp can be re-added later
```

### 6.4 Upgrading Lifecycle Stage

When a FoundUp passes the Exfoliation Readiness Gate (see `FOUNDUP_EXFOLIATION_PROTOCOL.md`):

```
1. Update lifecycle_stage in catalog entry and manifest (if bound)
2. Re-validate with test_namespace_guardrail.py (if bound)
```

---

## 7. Relationship to Existing Architecture

| Existing Component | p.fMALL Relationship | Status |
|--------------------|---------------------|--------|
| `mall-video-catalog.json` | Operational catalog (13 entries, 9 categories) | `IMPLEMENTED_IN_CATALOG` |
| `test_namespace_guardrail.py` | Validates WSP 104 (route, namespace, uniqueness) for bound tenants | `IMPLEMENTED_IN_TESTS` |
| `shell_core.py` | Validates manifests (tier, lifecycle_stage, launch_readiness, foundup_id) | `IMPLEMENTED_IN_MANIFESTS` |
| `smartdao_spawning.py` (DAOTier enum) | Defines tier values: F0_DAE through F5_SYSTEMIC | `IMPLEMENTED_IN_MANIFESTS` |
| `subscription_tiers.py` | Defines tier names: free, starter, basic, plus, pro, enterprise | Not used in catalog |
| `FOUNDUPS_DOMAIN_CANONICAL_INDEX.md` | Source of truth for portfolio classification | Reference doc |
| `FOUNDUP_EXFOLIATION_PROTOCOL.md` | Governs lifecycle_stage transitions | Reference doc |
| `FOUNDUP_ECOSYSTEM_ARCHITECTURE.md` | GotJunk multi-PWA pattern = architectural precedent | Reference doc |
| `skill_manifest_guard.py` | HMAC signing pattern (WRE skills only — not extended to FoundUp manifests) | `SPECIFIED_NOT_IMPLEMENTED` for catalog |

### Companion Documents (Reconciled)

| Document | Reconciliation Slice | Status |
|----------|---------------------|--------|
| `PFMALL_SHELL_CONTRACT.md` | — | Original spec (not yet reconciled) |
| `PFMALL_FOUNDUP_MANIFEST_SCHEMA.md` | PFMALL-MANIFEST-SCHEMA-RECON (W2) | Reconciled 2026-04-21, PR #414 merged |
| `PFMALL_ROUTING_DISCOVERY_MODEL.md` | PFMALL-ROUTING-RECON (W3) | Reconciled 2026-04-21 |
| `PFMALL_DATA_ISOLATION_MODEL.md` | PFMALL-DATA-ISOLATION-RECON (W1) | Reconciled 2026-04-21, PR #415 open |
| `PFMALL_LAUNCH_CATALOG_TAXONOMY.md` | PFMALL-LAUNCH-CATALOG-TAXONOMY-RECON (W2) | This document |
