# p.fMALL Launch Catalog Taxonomy

**Status**: Architecture specification (first tranche)
**Owner**: 0102
**Slice**: `pfmall_architecture_and_template_contract`
**WSP References**: WSP 3 (Domains), WSP 100 (SmartDAO Tiers)

---

## 1. Purpose

Define the category taxonomy for FoundUps in the p.fMALL launch catalog, classify the initial portfolio, and establish rules for catalog membership.

---

## 2. Category Taxonomy

### 2.1 Categories

| Category | Slug | Description |
|----------|------|-------------|
| **Marketplace** | `marketplace` | Buy/sell/trade platforms (goods, services, assets) |
| **Media** | `media` | Broadcasting, content creation, social publishing |
| **Science** | `science` | Research tools, data analysis, scientific collaboration |
| **Games** | `games` | Interactive entertainment, white-label game families |
| **Community** | `community` | Engagement tools, moderation, social coordination |

### 2.2 Category Rules

1. **Infrastructure is never a category**. OpenClaw, WRE, HoloIndex are substrate — they never appear in the catalog.
2. **Categories are extensible**. New categories added by WSP governance (propose via WSP process, not ad hoc).
3. **One primary category per FoundUp**. A FoundUp can have tags for secondary discovery, but one primary category for catalog display.
4. **Categories are user-facing**. Slugs are URL-stable (`/discover?category=marketplace`).

---

## 3. Initial FoundUp Portfolio

Classification based on `FOUNDUPS_DOMAIN_CANONICAL_INDEX.md`:

### 3.1 Catalog FoundUps

| FoundUp | Category | Tier | Lifecycle | Invite Only | Launch Priority |
|---------|----------|------|-----------|-------------|-----------------|
| **GotJunk** | marketplace | F0_DAE | proto | YES | 1 (first) |
| **antifaFM** | media | F0_DAE | incubating | YES | 2 (after V3.2.8 stabilizes) |
| **AutoPost** | media | F0_DAE | externalized | YES | 3 (own repo, adapter needed) |
| **Whack-a-Magot** | games | F0_DAE | incubating | YES | 4 (concept stage) |
| **YouTube Engagement** | community | F0_DAE | incubating | YES | 5 |
| **LinkedIn Agent** | community | F0_DAE | incubating | YES | 6 |

### 3.2 NOT in Catalog (Infrastructure)

| Module | Why Excluded |
|--------|-------------|
| OpenClaw | Control plane — substrate, not product |
| WRE | Execution layer — substrate, not product |
| HoloIndex | Memory/retrieval — substrate, not product |
| FAM DAEmon | Agent market internals — substrate |
| WSP Framework | Protocol governance — substrate |
| Simulator | Economics tooling — substrate |

### 3.3 External FoundUps (Federated)

| FoundUp | Category | Status | Integration |
|---------|----------|--------|-------------|
| **Science Swarm Hub** | science | externalized (own repo) | Catalog link to external deploy |
| **AutoPost** | media | externalized (own repo) | Catalog link to external deploy |

Externalized FoundUps appear in the catalog but link to their external deployment rather than loading inside p.fMALL's iframe.

---

## 4. Catalog Entry Schema

Each entry in `catalog.json` uses this schema (subset of full manifest):

```json
{
  "foundup_id": "string (16-char hex)",
  "name": "string",
  "tagline": "string (max 80 chars)",
  "category": "marketplace | media | science | games | community",
  "tier": "F0_DAE | F1_OPO | F2_GROWTH | F3_INFRA | F4_MEGA | F5_SYSTEMIC",
  "lifecycle_stage": "incubating | proto | externalized | federated",
  "required_subscription_tier": "free | starter | plus | pro | angel | ultimate",
  "is_invite_only": true,
  "icon_url": "string",
  "manifest_url": "string (path to full foundup_manifest.json)",
  "external_url": "string | null (for externalized FoundUps)"
}
```

### 4.1 Display Rules

| Lifecycle Stage | Catalog Display |
|-----------------|-----------------|
| incubating | Card with "Coming Soon" badge, no click-through |
| proto | Card with "Early Access" badge, click loads if tier sufficient |
| externalized | Card with "External" badge, click opens external_url |
| federated | Card (normal), click loads in iframe |

| Invite Status | Catalog Display |
|---------------|-----------------|
| invite_only: true | "Angel Access" badge, tier gate on click |
| invite_only: false | Normal card, tier gate on click |

---

## 5. Launch Order

### 5.1 Phase 1 Launch Candidates

**Priority 1: GotJunk**
- Status: proto-ready (3-app PWA architecture already designed)
- Why first: Clear product boundary, proven multi-PWA pattern, marketplace category validates UPs spending
- Blockers: None (architecture exists in `FOUNDUP_ECOSYSTEM_ARCHITECTURE.md`)

**Priority 2: antifaFM**
- Status: incubating (V3.2.8 in progress)
- Why second: Active broadcaster with real OBS integration, validates media category
- Blockers: V3.2.8 stabilization (news maps BLOCKED on Chrome 147)

### 5.2 Phase 2 Launch Candidates

- AutoPost (externalized — needs adapter for catalog listing)
- Science Swarm Hub (externalized — needs catalog entry)
- Whack-a-Magot (incubating — needs PoC completion)

### 5.3 Launch Readiness Gate

A FoundUp is ready for catalog inclusion when:

1. Has valid `foundup_manifest.json` (signed, all required fields)
2. Has working `entry_url` (bundle loads without errors)
3. Responds to shell "ready" handshake within 30 seconds
4. Does not violate any sentinel rate limits during testing
5. Has documented CABR contract
6. Has at least one passing integration test with shell

---

## 6. Catalog Maintenance

### 6.1 Adding a FoundUp

```
1. Create foundup_manifest.json (per PFMALL_FOUNDUP_MANIFEST_SCHEMA.md)
2. Sign manifest with project key
3. Add catalog entry to catalog.json
4. Deploy FoundUp bundle to entry_url
5. Run integration test with shell
6. Bump catalog version
```

### 6.2 Removing a FoundUp

```
1. Remove catalog entry from catalog.json
2. Bump catalog version
3. Existing users see "This FoundUp is no longer available"
4. FoundUp bundle and data remain (not deleted)
5. FoundUp can be re-added later
```

### 6.3 Upgrading Lifecycle Stage

When a FoundUp passes the Exfoliation Readiness Gate (see `FOUNDUP_EXFOLIATION_PROTOCOL.md`):

```
1. Update lifecycle_stage in manifest (e.g., incubating → proto)
2. Update is_invite_only if transitioning to public (OPO)
3. Re-sign manifest
4. Update catalog entry
5. Bump catalog version
```

---

## 7. Relationship to Existing Architecture

| Existing Component | p.fMALL Relationship |
|--------------------|---------------------|
| `FOUNDUPS_DOMAIN_CANONICAL_INDEX.md` | Source of truth for portfolio classification |
| `FOUNDUP_EXFOLIATION_PROTOCOL.md` | Governs lifecycle_stage transitions |
| `smartdao_spawning.py` (DAOTier enum) | Defines tier values used in manifests |
| `subscription_tiers.py` | Defines tier names used in required_subscription_tier |
| `foundup_spawner.py` | Creates initial FoundUp structures (could generate manifests) |
| `FOUNDUP_ECOSYSTEM_ARCHITECTURE.md` | GotJunk multi-PWA pattern = architectural precedent |
| `skill_manifest_guard.py` | HMAC signing pattern reused for manifest verification |
