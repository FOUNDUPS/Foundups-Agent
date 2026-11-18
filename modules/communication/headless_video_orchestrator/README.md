# Headless Video Orchestrator

**Domain**: `communication/`  
**Purpose**: Assemble faceless music videos (audio + visuals) and hand off to existing scheduling/indexing systems.

## Scope (Occam)
- Build music videos from:
  - Suno audio files (local library)
  - Visual clips (generated or prebuilt)
- Output ready-to-upload MP4s for Shorts (9:16) and longform (16:9).
- Reuse existing modules for formatting and scheduling (no new platform auth).

## Reused Modules
- `modules/communication/youtube_shorts/src/video_editor.py` (concat + 9:16 formatting)
- `modules/platform_integration/youtube_shorts_scheduler/src/scheduler.py` (schedule unlisted)
- `modules/platform_integration/youtube_shorts_scheduler/src/content_generator.py` (music titles/descriptions)
- `modules/platform_integration/youtube_shorts_scheduler/src/index_weave.py` (index stub + description weave)

## Optional Open-Source Tools
- **AI-Youtube-Shorts-Generator** (auto-clip + crop): clone to `external_research/AI-Youtube-Shorts-Generator`
  - Set `AI_SHORTS_REPO_PATH` if installed elsewhere.
  - Adapter: `run_ai_shorts_generator(...)`

## Output Locations
- `memory/video_lab/music_videos/` (assembled outputs)
- `memory/video_cache/` (downloaded source videos for reuse)

## Quick Start
```python
from modules.communication.headless_video_orchestrator.src.orchestrator import (
    HeadlessVideoOrchestrator,
    MusicVideoRequest,
)

req = MusicVideoRequest(
    audio_path="data/suno/track_01.mp3",
    visual_paths=["memory/video_lab/visuals/v1.mp4", "memory/video_lab/visuals/v2.mp4"],
    aspect="shorts",
)

out = HeadlessVideoOrchestrator().build_music_video(req)
print(out.output_path)
```

## Notes
- Uploading is done via existing YouTube Studio automation (scheduler).
- Indexing is handled via stub at scheduling time, then full indexing via `video_indexer`.

## Preschool Story Time destination

Kids Episodes uses **Us_Story_Time** (`us_story_time`) for reviewed preschool story output. Assembly stays here/the existing Kids renderer; upload stays in `YouTubeShortsUploader.publish_story_episode`, with FoundUps OAuth set 10 and an exact channel-ID check. See [binding instructions](../youtube_shorts/docs/KIDS_LOCAL_PRODUCTION.md#us_story_time-publishing-destination--2026-10-26). This destination registration does not install a headless worker or schedule uploads.
