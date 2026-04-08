# Video Mall Catalog Schema

**Status**: Active runtime schema
**Version**: 1.0.0
**Date**: 2026-04-03
**Owner**: 0102
**Location**: `public/member/mall-video-catalog.json`
**Tests**: `modules/foundups/pfmall/tests/test_mall_video_catalog.py`

---

## 1. Purpose

This document defines the schema for `mall-video-catalog.json`, the manifest that powers the Video Mall tile field.

The Video Mall Catalog is **not** the full FoundUp runtime manifest. It is a projection-optimized data structure for:

- Displaying video-backed FoundUp tiles in the Mall field
- Enabling Red Dog to filter/project by category, creator, topic, geo
- Providing queue metadata for the fullscreen video player
- Supporting related-lane discovery

For the full FoundUp runtime manifest (CABR, capabilities, signing), see `PFMALL_FOUNDUP_MANIFEST_SCHEMA.md`.

---

## 2. Schema Overview

```
mall-video-catalog.json
├── FoundUpEntry[]           # Array of FoundUp lanes
│   ├── Identity fields      # foundup_id, title, entity
│   ├── Creator fields       # creator, creator_id, creator_display
│   ├── Source fields        # source_type, source_id, source_handle
│   ├── Classification       # category, tags, topic_family
│   ├── Projection fields    # geo, status, display_order, related_lanes
│   ├── Entry surface fields  # tagline, description, tier, lifecycle_stage, launch_readiness
│   ├── Media fields         # poster_url, video_count
│   └── videos[]             # Video queue
│       ├── video_id
│       ├── title
│       ├── thumbnail_url
│       ├── embed_url
│       ├── source_url
│       ├── timestamp
│       └── duration_seconds
```

---

## 3. FoundUp Entry Schema

### 3.1 Full Entry Definition

```json
{
  "foundup_id": "string (lowercase snake_case)",
  "title": "string",
  "creator": "string",
  "creator_id": "string",
  "creator_display": "string",
  "entity": "string",
  "source_type": "youtube_channel | linkedin_profile | x_profile | tiktok_profile | instagram_profile | derived | github_repo | external_app | internal_service",
  "source_id": "string | null",
  "source_handle": "string | null",
  "category": "string",
  "tags": ["string"],
  "topic_family": "string",
  "geo": "string",
  "status": "active | placeholder | archived | pending",
  "display_order": "number",
  "related_lanes": ["string (foundup_id references)"],
  "tagline": "string | null",
  "description": "string | null",
  "tier": "string | null",
  "lifecycle_stage": "string | null",
  "launch_readiness": "string | null",
  "poster_url": "string",
  "video_count": "number",
  "videos": ["VideoEntry"]
}
```

### 3.2 Field Definitions

#### Identity Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `foundup_id` | string | YES | Unique lane identifier. Lowercase snake_case. |
| `title` | string | YES | Human-readable lane title for display. |
| `entity` | string | YES | The entity/brand this lane represents. NOT collapsed to creator. |

#### Creator Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `creator` | string | YES | Creator short identifier (e.g., "012"). |
| `creator_id` | string | YES | Stable creator identifier for filtering. |
| `creator_display` | string | YES | Human-readable creator name (e.g., "UnDaoDu (012)"). |

#### Source Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `source_type` | enum | YES | Platform type. See Section 4. |
| `source_id` | string | NO | Platform-specific ID (e.g., YouTube channel ID). |
| `source_handle` | string | NO | Platform handle (e.g., "@MOVE2JAPAN"). |
| `external_url` | string | NO | External URL. Present when `source_type` is `external_app`, `github_repo`, or `internal_service`. See Section 4. |
| `parent_channels` | string[] | NO | Parent lane references. Required when `source_type` is `derived`. See Section 4. |
| `derivation_method` | string | NO | How content was classified. Required when `source_type` is `derived`. See Section 4. |

#### Classification Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `category` | string | YES | Primary category for filtering. See Section 5. |
| `tags` | string[] | YES | Searchable tags. Must include "012-lane" for 012 content. |
| `topic_family` | string | YES | Topic grouping for projection. See Section 6. |

#### Projection Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `geo` | string | YES | Geographic scope. "Global" or specific location. |
| `status` | enum | YES | Lane status. See Section 7. |
| `display_order` | number | YES | Default sort priority (1 = highest). Must be unique. |
| `related_lanes` | string[] | YES | References to related `foundup_id` values. |

#### Entry Surface Fields (Optional)

These fields enrich the entry page (`foundup.html`) when present. They are optional and additive — the entry page renders gracefully without them.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `tagline` | string | NO | Short lane description for display. |
| `description` | string | NO | Longer description of the lane and its content. |
| `tier` | string | NO | FoundUp tier classification (e.g., `F0_DAE`). |
| `lifecycle_stage` | string | NO | Lane maturity: `active`, `proto`, `staging`, `incubating`. |
| `launch_readiness` | string | NO | Entry-page readiness posture: `ready`, `conditional`, `discoverable_only`. |

#### Media Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `poster_url` | string | YES | Path to lane poster image. |
| `video_count` | number | YES | Count of videos. Must match `videos.length`. |
| `videos` | VideoEntry[] | YES | Video queue. See Section 8. |

---

## 4. Source Types

| Value | Platform | Example source_id |
|-------|----------|-------------------|
| `youtube_channel` | YouTube | `UC-LSSlOZwpGIRIYihaz8zCw` |
| `linkedin_profile` | LinkedIn | `urn:li:person:openstartup` or company ID |
| `x_profile` | X (Twitter) | Account ID |
| `tiktok_profile` | TikTok | Account ID |
| `instagram_profile` | Instagram | Account ID |
| `derived` | Content classified from a parent channel | Parent channel ID (e.g., `UCfHM9Fw9HD-NwiS0seD_oIA`) |
| `github_repo` | Repo-backed FoundUp (code/research) | `"org/repo-name"` (e.g., `"FOUNDUPS/science-swarm-hub"`) |
| `external_app` | Externalized product FoundUp (own deploy) | `"org/repo-name"` (e.g., `"FOUNDUPS/autopost"`) |
| `internal_service` | Monorepo-internal service FoundUp | Module path (e.g., `"modules/foundups/kosei"`) |

### Derived Lanes

A `derived` lane has no source channel of its own. Its videos are a topic-classified subset of another lane's content.

- `source_id` and `source_handle` point to the **parent** source channel
- Videos are copied from the parent lane at catalog build time, not moved
- The same video may appear in both the parent lane and derived lane(s)
- Parent lane's `related_lanes` should include the derived lane's `foundup_id`

Required conditional fields for `source_type: "derived"`:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `parent_channels` | string[] | YES | Array of `foundup_id` references whose content feeds this lane. |
| `derivation_method` | string | YES | How content was classified: `manual_curation`, `topic_tag`, `ai_classification`. |

### Non-Video FoundUps (`github_repo`, `external_app`, `internal_service`)

These source types represent FoundUps whose value is in code, tools, or services rather than media content. They have `videos: []` with `video_count: 0`, which is explicitly valid. LinkedIn profile lanes already prove this pattern works across all pfMALL surfaces.

Conditional field for non-video FoundUps:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `external_url` | string (URL) | YES | URL to external deploy, repository, or planned production domain. |

Resolution rules:

| source_type | `external_url` resolves to |
|-------------|---------------------------|
| `github_repo` | GitHub repo URL or project site |
| `external_app` | Production app URL |
| `internal_service` | Planned production domain (may not be live yet) |

---

## 5. Categories

Current active categories:

| Category | Description |
|----------|-------------|
| `travel` | Travel, relocation, expat life |
| `music` | Music, ambient, meditation |
| `startup` | Startups, founders, ventures |
| `media` | Radio, broadcasting, news |
| `thought-leadership` | Articles, essays, long-form |
| `ai-education` | AI learning, education |
| `ai-research` | AI research, technical |
| `science` | Science, research, multi-agent |

Categories are projection axes for Red Dog filtering.

---

## 6. Topic Families

| Family | Description | Example Lanes |
|--------|-------------|---------------|
| `life` | Daily life, travel, relocation | move2japan |
| `consciousness` | Meditation, quantum, 0102 | undaodu, linkedin_012, linkedin_esingularity |
| `startup` | Ventures, founders, pAVS | foundups_main, linkedin_foundups |
| `resistance` | Activism, anti-fascist | antifafm |
| `ai-education` | AI learning, autonomous education | eduit |
| `science` | Science, research coordination | science_swarm |
| `media` | Content automation, tools | autopost, kosei |

Topic families enable cross-category projection (e.g., "show all detector signature content").

---

## 7. Status Values

| Status | Description |
|--------|-------------|
| `active` | Lane is live and has content |
| `placeholder` | Lane exists but content pending |
| `archived` | Lane is historical, not actively updated |
| `pending` | Lane awaiting activation |

---

## 8. Video Entry Schema

### 8.1 Full Video Definition

```json
{
  "video_id": "string",
  "title": "string",
  "thumbnail_url": "string",
  "embed_url": "string",
  "source_url": "string",
  "timestamp": "string (ISO 8601: YYYY-MM-DDTHH:MM:SSZ)",
  "duration_seconds": "number"
}
```

### 8.2 Field Definitions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `video_id` | string | YES | Platform-specific video ID. Unique within lane. |
| `title` | string | YES | Video title. |
| `thumbnail_url` | string | NO | URL to thumbnail image. |
| `embed_url` | string | NO | Embeddable player URL. |
| `source_url` | string | NO | Direct link to video on platform. |
| `timestamp` | string | YES | ISO 8601 format: `YYYY-MM-DDTHH:MM:SSZ`. |
| `duration_seconds` | number | YES | Video duration. 0 or positive. |

---

## 9. Validation Rules

The test suite (`test_mall_video_catalog.py`) enforces:

### Structure
- Catalog is a non-empty array
- At least 4 distinct FoundUp lanes (no flattening)
- All `foundup_id` values unique

### Entry Shape
- All required fields present
- `foundup_id` is lowercase snake_case
- `source_type` is valid enum value
- `status` is valid enum value
- `tags` is array of strings
- `video_count` matches `videos.length`

### Video Shape
- All required video fields present
- `video_id` unique within lane
- `timestamp` matches ISO 8601 format
- `duration_seconds` is non-negative

### Projection Metadata
- All projection fields present (`creator_id`, `topic_family`, `related_lanes`, `display_order`)
- `topic_family` is valid value
- `related_lanes` reference valid `foundup_id` values
- `display_order` is unique
- `geo` is non-null
- All lanes include `012-lane` tag

---

## 10. Relationship to FoundUp Manifest

| Concern | Video Mall Catalog | FoundUp Manifest |
|---------|-------------------|------------------|
| **Purpose** | Mall projection/display | Shell runtime loading |
| **Scope** | Video-backed tiles only | Full FoundUp capabilities |
| **File** | `mall-video-catalog.json` | `foundup_manifest.json` |
| **Signing** | Not required | HMAC-SHA256 required |
| **CABR** | Not included | V1/V2/V3 contract |
| **Capabilities** | Not included | Declared capabilities |
| **Agent routes** | Not included | OpenClaw routes |
| **When used** | Mall field rendering | FoundUp iframe loading |

The catalog is a lightweight projection index.
The manifest is a security-signed runtime contract.

A FoundUp may appear in both:
- In the catalog for Mall display
- In a manifest for full shell loading

---

## 11. Data Sources

The catalog is populated from:

| Source | Location | Data |
|--------|----------|------|
| Video Index | `memory/video_index/{channel}/*.json` | Video IDs, titles, segments |
| YouTube Channels | `modules/infrastructure/shared_utilities/memory/youtube_channels.json` | Channel IDs, handles |
| LinkedIn Map | `modules/platform_integration/linkedin_agent/data/linkedin_publishing_map.json` | Entity IDs, handles |

Builder tool: `holo_index/skillz/video_catalog_builder/` (planned)

---

## 12. Example Entry

```json
{
  "foundup_id": "move2japan",
  "title": "Move to Japan",
  "creator": "012",
  "creator_id": "012",
  "creator_display": "UnDaoDu (012)",
  "entity": "Move2Japan",
  "source_type": "youtube_channel",
  "source_id": "UC-LSSlOZwpGIRIYihaz8zCw",
  "source_handle": "@MOVE2JAPAN",
  "category": "travel",
  "tags": ["012-lane", "expat", "japan", "relocation", "life", "ffcpln"],
  "topic_family": "life",
  "geo": "Fukui, Japan",
  "status": "active",
  "display_order": 1,
  "related_lanes": ["undaodu", "linkedin_012"],
  "tagline": "Expat life and FFCPLN activism from Fukui, Japan",
  "description": "012 documents life in rural Japan — relocation, culture, and political activism through the FFCPLN movement.",
  "tier": "F0_DAE",
  "lifecycle_stage": "active",
  "launch_readiness": "discoverable_only",
  "poster_url": "/media/posters/move2japan.jpg",
  "video_count": 573,
  "videos": [
    {
      "video_id": "CjJTdM4wjms",
      "title": "Resist #ICE #FFCPLN",
      "thumbnail_url": "https://i.ytimg.com/vi/CjJTdM4wjms/hqdefault.jpg",
      "embed_url": "https://www.youtube.com/embed/CjJTdM4wjms",
      "source_url": "https://www.youtube.com/watch?v=CjJTdM4wjms",
      "timestamp": "2026-03-20T00:00:00Z",
      "duration_seconds": 60
    }
  ]
}
```

---

## 13. Current Catalog Stats

As of 2026-04-07:

| Metric | Value |
|--------|-------|
| Total lanes | 12 |
| YouTube lanes | 4 |
| LinkedIn lanes | 4 |
| Derived lanes | 1 |
| GitHub repo lanes | 1 |
| External app lanes | 1 |
| Internal service lanes | 1 |
| Total videos | 1,184 (21 shared with undaodu via derived lane) |
| Source types in use | 6 (youtube_channel, linkedin_profile, derived, github_repo, external_app, internal_service) |

Lane breakdown:
- move2japan: 573 videos (youtube_channel)
- undaodu: 512 videos (youtube_channel)
- foundups_main: 44 videos (youtube_channel)
- antifafm: 34 videos (youtube_channel)
- eduit: 21 videos (derived from undaodu)
- linkedin_012: 0 (linkedin_profile)
- linkedin_esingularity: 0 (linkedin_profile)
- linkedin_tsingularity: 0 (linkedin_profile)
- linkedin_foundups: 0 (linkedin_profile)
- science_swarm: 0 (github_repo)
- autopost: 0 (external_app)
- kosei: 0 (internal_service)
