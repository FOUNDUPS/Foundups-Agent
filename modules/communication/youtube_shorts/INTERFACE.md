# YouTube Shorts Interface

**Module**: `youtube_shorts`
**Domain**: `communication/`
**WSP Reference**: WSP 11 (Public Interface Definition)

## Public API

### ShortsOrchestrator

Main orchestration class for 012[U+2194]0102 interaction flow.

```python
from modules.communication.youtube_shorts import ShortsOrchestrator

orchestrator = ShortsOrchestrator()
```

#### Methods

##### `create_and_upload(topic: str, duration: int = 30) -> str`
Complete flow: Generate video from topic and upload to YouTube.

**Parameters:**
- `topic` (str): Topic/theme for the video (e.g., "Cherry blossoms in Tokyo")
- `duration` (int): Video duration in seconds (15-60, default: 30)

**Returns:**
- `str`: YouTube Shorts URL (e.g., "https://youtube.com/shorts/abc123")

**Example:**
```python
url = orchestrator.create_and_upload(
    topic="Japanese tea ceremony traditions",
    duration=30
)
print(f"Posted: {url}")
```

##### `generate_video_only(topic: str, duration: int = 30) -> str`
Generate video without uploading.

**Returns:**
- `str`: Local file path to generated .mp4

##### `upload_existing(video_path: str, title: str, description: str) -> str`
Upload pre-existing video as Short.

**Returns:**
- `str`: YouTube Shorts URL

---

### Veo3Generator

Low-level Veo 3 API wrapper.

```python
from modules.communication.youtube_shorts.src.veo3_generator import Veo3Generator

generator = Veo3Generator()
```

#### Methods

##### `generate_video(prompt: str, duration: int = 30) -> str`
Generate video using Veo 3 API.

**Parameters:**
- `prompt` (str): Video generation prompt
- `duration` (int): Video length in seconds

**Returns:**
- `str`: Path to downloaded .mp4 file

**Example:**
```python
video_path = generator.generate_video(
    prompt="A serene Japanese garden with cherry blossoms falling gently",
    duration=30
)
```

---

### YouTubeShortsUploader

YouTube upload handler using the hardened `youtube_auth` service boundary. It never reads OAuth token files directly and never returns credential material.

```python
from modules.communication.youtube_shorts.src.youtube_uploader import YouTubeShortsUploader

uploader = YouTubeShortsUploader(channel="foundups-mall")
```

Construction pins a channel role to one credential set and verifies the authorized YouTube channel before any upload. `foundups-mall` requires `YT_UPLOAD_CHANNEL_ID_FOUNDUPS_MALL`; a missing or mismatched pin fails closed.

#### `publish_video(...) -> YouTubePublishResult`

Uploads MP4, WebM, or QuickTime through an 8 MB resumable transport. The default privacy is `unlisted`; optional playlist insertion returns the authoritative playlist-item ID. Callers receive video/channel/playlist identities and URLs, never an OAuth token or local credential path.

#### `publish_foundups_media(...) -> YouTubePublishResult`

Forces `unlisted` and appends a compact `foundups.media.v1` author/manifest reference. This is an uploader boundary, not a public gateway: the future caller must authenticate the AutoPost operator and verify the signed manifest before invoking it.

#### Methods

##### `upload_short(video_path: str, title: str, description: str, tags: list = None) -> str`
Upload video as YouTube Short.

Backward-compatibility note: this helper retains its existing `public` default. New Foundups/pfMALL flows must use `publish_video` or `publish_foundups_media`, whose governed default is `unlisted`.

**Parameters:**
- `video_path` (str): Local .mp4 file path
- `title` (str): Video title
- `description` (str): Video description
- `tags` (list): Optional list of tags (default: ["Shorts", "Japan", "Move2Japan"])

**Returns:**
- `str`: YouTube Shorts URL

**Example:**
```python
url = uploader.upload_short(
    video_path="generated_video.mp4",
    title="Cherry Blossoms in Tokyo",
    description="Beautiful spring scenery in Japan #Shorts",
    tags=["Shorts", "Japan", "CherryBlossoms", "Tokyo"]
)
```

---

### ShortsDAE

Autonomous DAE for background operation (WSP 80 pattern).

```python
from modules.communication.youtube_shorts.src.shorts_dae import ShortsDAE

dae = ShortsDAE()
```

#### Methods

##### `start_autonomous_mode(topics: list, interval_hours: int = 24)`
Run autonomous Short generation on schedule.

**Parameters:**
- `topics` (list): List of topics to cycle through
- `interval_hours` (int): Hours between posts (default: 24)

**Example:**
```python
dae.start_autonomous_mode(
    topics=[
        "Tokyo street food",
        "Japanese gardens",
        "Mount Fuji sunrise"
    ],
    interval_hours=24
)
```

##### `stop_autonomous_mode()`
Stop the autonomous DAE.

---

## Data Structures

### Generated Short Record
```python
{
    "id": "abc123",
    "topic": "Cherry blossoms in Tokyo",
    "prompt": "A serene Japanese garden...",
    "video_path": "assets/generated/video_abc123.mp4",
    "youtube_url": "https://youtube.com/shorts/abc123",
    "duration": 30,
    "cost": 12.00,  # USD
    "created_at": "2025-10-05T10:30:00Z",
    "status": "uploaded"
}
```

Stored in: `memory/generated_shorts.json`

---

## Integration Examples

### Basic Usage (Single Short)
```python
from modules.communication.youtube_shorts import ShortsOrchestrator

# Create and upload in one call
orchestrator = ShortsOrchestrator()
url = orchestrator.create_and_upload("Japanese autumn leaves", duration=30)
print(f"[OK] Short posted: {url}")
```

### Advanced Usage (Custom Workflow)
```python
from modules.communication.youtube_shorts.src.veo3_generator import Veo3Generator
from modules.communication.youtube_shorts.src.youtube_uploader import YouTubeShortsUploader

# Generate video
generator = Veo3Generator()
video = generator.generate_video(
    prompt="Time-lapse of Tokyo skyline at sunset",
    duration=30
)

# Upload separately
uploader = YouTubeShortsUploader()
url = uploader.upload_short(
    video_path=video,
    title="Tokyo Sunset Time-Lapse",
    description="Beautiful Tokyo cityscape #Shorts #Japan",
    tags=["Shorts", "Tokyo", "Sunset", "Timelapse"]
)
```

### Autonomous Mode
```python
from modules.communication.youtube_shorts.src.shorts_dae import ShortsDAE

# Run autonomous daily posting
dae = ShortsDAE()
dae.start_autonomous_mode(
    topics=[
        "Traditional Japanese crafts",
        "Modern Tokyo architecture",
        "Japanese cuisine preparation"
    ],
    interval_hours=24  # One Short per day
)
```

---

## Error Handling

All methods raise specific exceptions:

```python
class Veo3GenerationError(Exception):
    """Veo 3 API generation failed"""

class YouTubeUploadError(Exception):
    """YouTube upload failed"""

class InsufficientCreditsError(Exception):
    """Not enough API credits for generation"""
```

**Usage:**
```python
try:
    url = orchestrator.create_and_upload("Topic", duration=30)
except Veo3GenerationError as e:
    print(f"Video generation failed: {e}")
except YouTubeUploadError as e:
    print(f"Upload failed: {e}")
```

---

## Dependencies

**External:**
- `google-generativeai>=0.8.3` (Veo 3 API)
- `google-api-python-client` (YouTube upload)

**Internal (Read-Only):**
- `modules.platform_integration.youtube_auth` (OAuth service)

**No Modifications To:**
- [OK] livechat module
- [OK] youtube_dae module
- [OK] youtube_auth module

## Kids episode APIs (local prototype)

Load direct-file CLI modules without the legacy package initializer's optional provider imports:

- `kids_episode.validate_episode(spec) -> dict`: validate version 1, exactly 15 seconds, draft/final, landscape/portrait, clips, captions and music provenance declaration.
- `kids_episode.render_episode(spec, output_path, base_dir='.') -> dict`: local FFmpeg assembly, selected music/optional voice, burned captions and SRT. Refuses existing outputs; verifies measured duration/dimensions/audio. Returns `status=rendered_unreviewed`.
- CLI: `python modules/communication/youtube_shorts/src/kids_episode.py episode.json --output episode.mp4`.
- `kids_editor_server.EditorServer(workspace, port=8767)`: loopback single-operator UI. Confines inputs to workspace; downloads only artifacts generated by this process. CLI `--workspace` required. Not a hosted/authenticated multi-user gateway.
- `kids_research.collect_trend_snapshot(youtube_service, queries, region='US', language='en', max_results=5, observed_at=None)`: injected authorized service; at most five searches and one statistics request. No automatic retries/auth rotation.
- `kids_research.rank_observed_growth(current, previous=None)`: labels baseline, observed growth, missing statistics, decreasing counters and invalid time order.
- `kids_research.generate_lyria_clip(client, prompt, output_path)`: explicit potentially paid call to injected official Interactions client; writes MP3 and provenance metadata, preserves unknown rights/timing status. Client transport configuration and budget remain caller-owned.

No new publishing API or channel role is introduced. Use existing `publish_video` only after review, channel verification and audience/rights decisions; do not substitute the legacy public-default helper.

## OpenRouter storyboard images

`src/openrouter_storyboard.py:OpenRouterStoryboard(provider_config, references=..., authorize=..., model=MODEL, transport=None)` consumes the existing `AIGateway.providers['openrouter']` configuration. It neither reads environment files nor activates the dormant `infrastructure/openrouter_client`. The host supplies one to four approved local raster references with `path`, `sha256`, and `rights_evidence`; rasterize the Little Shrew SVG design before binding, or use an approved generated reference. Each call `(shot, context)` requires `shot_id`, `prompt`, and an existing `context.output_dir`.

The default candidate is `black-forest-labs/flux.2-klein-4b`. One non-streaming `POST /api/v1/images` requests one landscape image with actual reference bytes and no provider fallback. A mandatory host authorization callback receives `('storyboard_image', record)` before egress; it must reserve cost and admit the exact model/request digest under the existing execution owner. This callback is not an authentication system. Host configuration must confirm current endpoint capabilities and available budget before production use.

An exclusive `*.storyboard.json` intent is written before egress. `*.storyboard.result.json` records successful file output, hashes and reference provenance. Existing intents refuse replay even after timeout/malformed output; reconcile effects through the owner instead of deleting intents to retry. Responses and reference bytes are bounded, redirects are disabled, errors omit upstream text, and output is `generated_unreviewed`. File signatures do not prove complete image decoding or visual quality. No usage/cost estimate is invented.

`StoryboardVideoShot(storyboard, review_frame=..., generate_video=...)` composes into `run_story(generate_shot=...)`. The reviewer must inspect the actual frame and explicitly return True; a post-review hash check binds that frame. The video callback receives `shot.start_frame` (path, SHA-256, model, reference provenance), must consume the frame and produce the existing video asset contract. The controller retains duration trimming, uncertain-effect checkpoints, episode review and assembly. Production requires an admitted reviewer/video binding; this patch does not activate WRE or convert stills into pretend generated video.

## Local Little Shrew preview

`src/little_shrew_preview.py:produce_preview(output_dir, preset="draft")` requires a new output directory and produces the first existing episode through `kids_episode.render_episode`. `little_shrew_animation.py` samples the shared SVG rig at absolute times, encodes three 150-frame clips and authors original audio. Output includes MP4/SRT and hashed provenance; status stays `rendered_unreviewed`. This is a local authoring command, not a generic story generator, WRE executor, scheduler or provider admission callback. See docs/KIDS_LOCAL_PRODUCTION.md for dependencies, review limits and autonomy owners.

### Us_Story_Time preschool review upload

`YouTubeShortsUploader("us_story_time")` uses FoundUps credential set 10 by default (optional positive `YT_UPLOAD_CREDENTIAL_SET_US_STORY_TIME` override) and requires `YT_UPLOAD_CHANNEL_ID_US_STORY_TIME` (verified exact channel ID). Authentication remains pinned to the selected set; it does not silently rotate on failure. `publish_story_episode(video_path, title, description, *, contains_synthetic_media: bool)` rejects other channel roles, uses unlisted visibility and made-for-kids true, and returns `YouTubePublishResult`. Call only after artifact/rights review. See [setup](docs/KIDS_LOCAL_PRODUCTION.md#us_story_time-publishing-destination--2026-10-26).
