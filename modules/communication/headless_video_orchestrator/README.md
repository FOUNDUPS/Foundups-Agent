# Headless Video Orchestrator

**Domain**: `communication/`  
**Purpose**: Assemble faceless music videos (audio + visuals), run deterministic staging/benchmark verification, and prepare dry-run daily handoffs to existing upload/scheduling/indexing owners.

## Scope (Occam)
- Build music videos from local audio tracks and visual clips (`legacy` or `staging_720p` profiles; 4K disallowed).
- Enforce explicit soundtrack mapping (`-map 0:v:0 -map 1:a:0`), `<180s` (`<=178.5s` default) Shorts ceiling, `720x1280` / `1280x720` `24fps` `H.264/yuv420p` `AAC 192k` staging, and optional clean audio fade-out.
- Audit media streams, embedded `mov_text`/SRT lyric cues vs. stage directions, 16kHz mono RMS/onset-flux quantiles, satire factual-claim provenance, native crop sharpness, and `camera_only` vs. `stepped_character_action` truth labels.
- Reuse `youtube_shorts/src/youtube_uploader.py` and `youtube_shorts_scheduler/src/schedule_tracker.py` (`preview_copy()` + `max_per_day=1`) without parallel uploaders, schedulers, or browser takeover.

## Reused Modules
- `modules/communication/youtube_shorts/src/video_editor.py` (concat + legacy formatting)
- `modules/communication/youtube_shorts/src/youtube_uploader.py` (sole YouTube upload seam, canonical channel pinning)
- `modules/platform_integration/youtube_shorts_scheduler/src/schedule_tracker.py` (browser-free 1/day slot preview)
- `modules/ai_intelligence/video_indexer` (post-schedule indexing owner)

## Preschool Story Time destination

Kids Episodes uses **Us_Story_Time** (`us_story_time`) for reviewed preschool story output. Assembly stays here/the existing Kids renderer; upload stays in `YouTubeShortsUploader.publish_story_episode`, with FoundUps OAuth set 10 and an exact channel-ID check. See [binding instructions](../youtube_shorts/docs/KIDS_LOCAL_PRODUCTION.md#us_story_time-publishing-destination--2026-10-26). This destination registration does not install a headless worker or schedule uploads.
