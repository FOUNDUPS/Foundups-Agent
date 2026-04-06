# EDUIT Minimum pfMALL Entry Spec

**Worker C** · `PFMALL_EDUIT_DERIVED_LANE_FEASIBILITY_PHASE1` · 2026-04-05

---

## What EDUIT's First pfMALL Entry Should Contain

Per `PFMALL_VIDEO_MALL_CATALOG_SCHEMA.md` required fields:

```json
{
  "foundup_id": "eduit",
  "title": "EDUIT",
  "entity": "EDUIT, Inc",
  "creator": "012",
  "creator_id": "012",
  "creator_display": "Michael Trout",
  "source_type": "derived",
  "source_id": "UCfHM9Fw9HD-NwiS0seD_oIA",
  "source_handle": "@UnDaoDu",
  "category": "ai-education",
  "tags": ["012-lane", "eduit", "esingularity", "education", "autonomous-learning", "hapticsign"],
  "topic_family": "ai-education",
  "geo": "Global",
  "status": "active",
  "display_order": 9,
  "related_lanes": ["undaodu", "linkedin_esingularity"],
  "poster_url": "/media/posters/eduit.jpg",
  "video_count": 21,
  "videos": [],
  "tagline": "FoundUP for autonomous learning on any device",
  "description": "EDUIT (eSingularity) — autonomous learning platform. Content derived from 012's UnDaoDu channel covering the eSingularity educational initiative.",
  "lifecycle_stage": "staging",
  "tier": "F0_DAE",
  "launch_readiness": "discoverable_only"
}
```

## Key Design Decisions

### 1. `source_type: "derived"` (new value)

Current schema has `youtube_channel` and `linkedin_profile`. EDUIT is neither — it's content classified from a parent channel. This requires a new `source_type` enum value.

- `source_id` and `source_handle` still point to the parent YouTube channel (undaodu)
- The `derived` type signals: "these videos come from another lane's source, filtered by topic"

### 2. Videos array: reference, not copy

Two architectures possible:

| Approach | Pros | Cons |
|----------|------|------|
| **A: Copy video objects** into `eduit.videos[]` | Simple, self-contained | Data duplication — same video in two lanes, catalog bloat, sync risk |
| **B: Reference by video_id** | No duplication, single source of truth | Requires runtime join against undaodu lane |
| **C: Copy at build time** | Best of both — catalog generator copies, source stays in undaodu | Build step needed, but pfMALL runtime reads flat catalog |

**Recommendation: C (copy at build time)**. The video objects live in `undaodu.videos[]` as source of truth. A catalog build step copies matching videos into `eduit.videos[]`. pfMALL runtime reads the flat catalog with no joins. If undaodu videos update, the next build propagates changes.

### 3. `category: "ai-education"` (existing category)

The catalog schema already defines `ai-education` in `PFMALL_VIDEO_MALL_CATALOG_SCHEMA.md`, and matching `theme-cat-ai-education` CSS classes already exist in `mall-tile-field.css` and `member.css`. No new category or CSS needed.

### 4. Poster image

Requires `/media/posters/eduit.jpg`. Can be generated from one of the video thumbnails or from EDUIT branding (faq.eduit.org).

### 5. `related_lanes`

- `undaodu` — parent content source
- `linkedin_esingularity` — eSingularity LinkedIn company page (already in catalog)

The `undaodu` lane should also add `eduit` to its own `related_lanes` array (currently: `["move2japan", "linkedin_012", "linkedin_esingularity"]`).

## What Does NOT Need to Change

- No `modules/foundups/eduit/` directory needed yet (this is a content lane, not a module)
- No CHANNEL_CONFIG entry in `video_indexer.py` (EDUIT has no YouTube channel — videos come from undaodu)
- No new LinkedIn lane (linkedin_esingularity already exists as a staging lane)
- No new credentials or API keys

---

**Smallest viable entry**: Add the JSON block above to `mall-video-catalog.json`, populate `videos[]` with the 21 candidate video objects from undaodu, add poster image. Three changes total (category and CSS already exist).
