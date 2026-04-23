# pfMALL YouTube Ingest Audit

**Worker**: CI (audit) → CM (implementation) → CP (apply)  
**Date**: 2026-04-13  
**Prompt**: PFMALL_YOUTUBE_SEARCH_AND_INGEST_AUDIT_PHASE1 → YOUTUBE_CHANNEL_PULL_PHASE1 → YOUTUBE_DELTA_REVIEW_AND_CATALOG_APPLY_PHASE1  
**Question**: How do YouTube videos currently populate pfMALL? Is there already a search or ingest path?

## STATUS: IMPLEMENTED + FIRST APPLY COMPLETE

**PR #341 MERGED** - YouTube channel pull delta generator is now available.
**Worker CP** - First delta reviewed and applied to live catalog.

```bash
# Run the pull (dry-run default)
python -m modules.communication.youtube_channel_pull.src.pull_cli

# Output: docs/audits/pfmall_youtube_ingest/youtube_channel_pull_delta.json
```

### First Apply (Worker CP, 2026-04-13)
- **Channel**: move2japan
- **Videos Applied**: 19
- **video_count**: 573 → 592
- **Duplicates**: 0

---

## Current Catalog Truth

### mall-video-catalog.json (MANUALLY MAINTAINED)

**Location**: `public/member/mall-video-catalog.json`  
**Status**: MANUAL JSON EDITING - No automated generation

**Structure**:
```json
{
  "foundup_id": "antifafm",
  "source_type": "youtube_channel",
  "source_id": "UC...",           // YouTube channel ID
  "videos": [
    {
      "id": "dQw4w9WgXcQ",         // YouTube video ID
      "title": "...",
      "thumbnail": "...",
      "publishedAt": "..."
    }
  ]
}
```

**Evidence** (git log):
```
feat(member): add video mall demo manifest phase 1
feat(member): add gotjunk demo video to mall catalog
```

These commits show hand-edited JSON additions, not script outputs.

### mall-catalog.json (DIFFERENT PURPOSE)

**Location**: `public/member/mall-catalog.json`  
**Generator**: `modules/foundups/pfmall/member_catalog_export.py`  
**Purpose**: FoundUp metadata export for mall grid (NOT video content)

The `member_catalog_export.py` script exports from `mall-video-catalog.json` source, it does NOT generate video entries.

---

## Current Ingest Path

### YouTube-to-Catalog Pipeline: NONE

**Finding**: No automated pipeline exists to:
1. Query YouTube Data API for channel videos
2. Transform responses to catalog format
3. Append to mall-video-catalog.json
4. Commit changes

### What EXISTS but is NOT ingest:

| Module | Purpose | Is Ingest? |
|--------|---------|------------|
| `video_indexer/` | Digital Twin learning from video content | NO |
| `youtube_ingest_resolver.py` | RTMPS live stream resolution | NO |
| `pfmall_catalog.py` | OpenClaw catalog queries | NO (read-only) |
| `member_catalog_export.py` | Export catalog to public/ | NO (copies existing) |

### Current "Ingest" Workflow

```
Human edits mall-video-catalog.json → git commit → firebase deploy
```

This is NOT scalable for 100+ FoundUps or real-time updates.

---

## Search Capability: MISSING

### What "search the web" would require:

1. **YouTube Data API v3 integration**
   - `youtube.channels.list` - Get channel metadata
   - `youtube.search.list` - Search videos
   - `youtube.videos.list` - Get video details

2. **API Key management**
   - `.env`: `YOUTUBE_API_KEY=AIza...`
   - Quota tracking (10,000 units/day default)

3. **Catalog writer**
   - Transform API response to catalog schema
   - Dedup existing entries
   - Append new videos
   - Commit/PR workflow

### Current Capability

| Feature | Status |
|---------|--------|
| YouTube API integration | NOT FOUND |
| Channel subscription | NOT FOUND |
| Video search | NOT FOUND |
| Auto-catalog population | NOT FOUND |

---

## Gaps To Real-Time Tile Population

### Gap 1: No YouTube API Client

**Required**: `google-api-python-client` or `pytube`  
**Current**: Not in any requirements.txt

### Gap 2: No Channel Pull Script

**Required**: Script to fetch videos from `source_id` channel  
**Current**: Only manual JSON editing

### Gap 3: No Catalog Updater

**Required**: Script to merge new videos into catalog without duplicates  
**Current**: Human must check for dupes manually

### Gap 4: No Webhook/Schedule

**Required**: Cron or webhook to trigger updates  
**Current**: Only when human remembers to edit

### Gap 5: No Thumbnail Fetch

**Required**: Download/cache thumbnails for offline display  
**Current**: Direct YouTube CDN links (may break)

---

## Recommended Next Slice: IMPLEMENTED

### YouTube Channel Puller: COMPLETE (PR #341)

**Name**: `YOUTUBE_CHANNEL_PULL_PHASE1`  
**Status**: MERGED 2026-04-13

**Implementation**:
1. Reads channel IDs from mall-video-catalog.json `source_id` fields
2. Fetches latest N videos per channel via YouTube Data API (`search.list`)
3. Outputs delta JSON (new videos not in catalog)
4. Human reviews and merges

**Files (in repo)**:
```
modules/communication/youtube_channel_pull/
  src/
    channel_puller.py      # Fetch videos from channel
    catalog_delta.py       # Compare with existing, output new
    pull_cli.py            # CLI entry point
  tests/
    test_catalog_delta.py  # 13 tests
  README.md
  INTERFACE.md
  requirements.txt         # google-api-python-client
```

**Test Results**: 13/13 passed

**NOT in scope for Phase 1** (future slices):
- Auto-commit/PR
- Scheduled runs
- Thumbnail caching
- Search (only channel pull)

---

## Summary

| Aspect | Before (CI Audit) | After (CM Implementation) |
|--------|-------------------|---------------------------|
| Catalog source | Manual JSON | **Automated pull + manual merge** |
| YouTube API | None | **google-api-python-client** |
| Channel subscriptions | Implicit in source_id | **Explicit fetch via `source_id`** |
| Update frequency | Human-driven | **On-demand CLI pull** |
| Deduplication | Manual | **Script-handled delta** |

**Answer to original question**:
- **How do YouTube videos populate pfMALL?** Manual editing of `mall-video-catalog.json` (but now with automated pull support)
- **Is there a search or ingest path?** **YES** - `youtube_channel_pull` module provides delta generation
- **Next slice?** `YOUTUBE_CHANNEL_PULL_PHASE1` - **COMPLETE** (PR #341 merged)

---

*Audit complete. Catalog still requires manual merge, but delta generation is now automated. Implementation: PR #341.*
