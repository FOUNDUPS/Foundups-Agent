# YouTube Shorts AI Generator

**Domain**: `communication/`
**Status**: POC (Proof of Concept)
**WSP Compliance**: WSP 3, 49, 80, 54

> The Veo/Sora architecture and prices below describe legacy paths. For the current open-model Kids Episodes direction, existing components, verified gaps and release gates, read [Open video audit](docs/OPEN_VIDEO_AUDIT.md). No end-to-end autonomous open-model service is active.

## Purpose

Autonomous AI-powered YouTube Shorts creation and upload system for Move2Japan channel. Enables 012[U+2194]0102 interaction where human provides topic and AI generates, produces, and posts video Shorts automatically.

## Architecture

### 012 [U+2194] 0102 Flow
```
012 (Human) -> Topic/Theme
    v
0102 (AI) -> Video Prompt Generation
    v
Veo 3 API -> Video Creation (with native audio)
    v
YouTube Upload -> Using existing youtube_auth (read-only)
    v
0102 -> Reports URL back to 012
```

### Technology Stack
- **Video Generation**: Google Veo 3 API (veo-3.0-fast-generate-001)
- **YouTube Upload**: Existing `youtube_auth` module (zero modifications)
- **Orchestration**: Shorts DAE (WSP 80 pattern)
- **Cost**: ~$0.40/second of video (Veo 3 Fast)

## Key Features

1. **AI Video Generation**: Text-to-video using Google Veo 3
2. **Autonomous Operation**: Full 012->0102->output flow
3. **Standalone Module**: Zero modifications to existing modules
4. **Read-Only Integration**: Imports youtube_auth without touching it
5. **DAE Pattern**: WSP 80 autonomous cube architecture

## Module Structure

```
youtube_shorts/
+-- README.md              # This file
+-- INTERFACE.md           # Public API
+-- ModLog.md              # Change tracking (WSP 22)
+-- requirements.txt       # Dependencies
+-- src/
[U+2502]   +-- __init__.py
[U+2502]   +-- veo3_generator.py      # Google Veo 3 integration
[U+2502]   +-- youtube_uploader.py    # YouTube Shorts uploader
[U+2502]   +-- shorts_orchestrator.py # 012[U+2194]0102 flow manager
[U+2502]   +-- shorts_dae.py          # Autonomous DAE (WSP 80)
+-- tests/
[U+2502]   +-- test_shorts_flow.py
+-- memory/
[U+2502]   +-- generated_shorts.json  # Track all created Shorts
+-- assets/
    +-- prompts/               # Video generation templates
```

## Integration Points

### Read-Only Dependencies
```python
# Uses existing auth - NEVER modifies it
from modules.platform_integration.youtube_auth.src.youtube_auth import get_authenticated_service
```

### No Modifications To
- [OK] `modules/communication/livechat/` - Untouched
- [OK] `modules/platform_integration/youtube_dae/` - Untouched
- [OK] `modules/platform_integration/youtube_auth/` - Read-only import

## Hardened Publisher Boundary

`YouTubeShortsUploader` now obtains an authenticated service only from `youtube_auth.get_authenticated_service(token_index=...)`. Channel roles are explicit; initialization observes the authorized channel and rejects a configured channel-ID mismatch before any write. The `foundups-mall` role requires `YT_UPLOAD_CHANNEL_ID_FOUNDUPS_MALL` and uses credential set 10.

The governed API defaults to `unlisted`, supports resumable MP4/WebM/QuickTime upload, optional playlist insertion, audience/synthetic-media declarations, disabled subscriber notification, and authoritative video/channel/playlist result IDs. The legacy `upload_short` public default is retained only for existing callers.

This is the server-side publishing Lego block, not the AutoPost upload gateway. A managed Foundups Mall flow still requires a separate authenticated API that validates user/session authorization and the signed Foundups manifest before this uploader is called. Refresh tokens, client-secret files, and shared bearer credentials must never be returned to AutoPost or any browser.

## Usage

### From Main Menu (Option 11)
```
11. [U+1F3AC] YouTube Shorts Generator
    -> Enter topic
    -> AI generates video
    -> Uploads to Move2Japan
    -> Returns Short URL
```

### Direct API
```python
from modules.communication.youtube_shorts import ShortsOrchestrator

orchestrator = ShortsOrchestrator()
short_url = orchestrator.create_and_upload(
    topic="Cherry blossoms in Tokyo spring",
    duration=30  # seconds
)
print(f"Posted: {short_url}")
```

## Cost Analysis

### Veo 3 Fast Pricing
- $0.40 per second of video
- 30-second Short: $12
- 60-second Short: $24

### Optimization Strategies
1. Start with 15-30 second Shorts
2. Use Veo 3 Fast (cheaper than standard)
3. Batch generation for efficiency
4. Track costs in memory/generated_shorts.json

## WSP Compliance

- **WSP 3**: Placed in `communication/` domain (content creation)
- **WSP 49**: Full module structure with README, INTERFACE, tests
- **WSP 80**: DAE cube architecture for autonomous operation
- **WSP 54**: Partner/Principal/Associate agent pattern
- **WSP 22**: ModLog tracking all changes

## Development Status

**Phase**: POC
**Next**: Build the authenticated AutoPost-to-Foundups-Mall gateway and signed-command verifier without weakening the YouTubeAuth boundary.
**Goal**: Autonomous 012->0102->YouTube generation plus governed Foundups media publishing.

## Kids Episodes local editor

The [Kids Episodes FoundUp](../../foundups/kids_episodes/README.md) uses this module for original 15-second educational music/activity videos.

```bash
python modules/communication/youtube_shorts/src/kids_editor_server.py --workspace /path/to/your/media
```

Open the printed loopback URL. Enter a learning goal, activity, local video clips totaling 15 seconds, music and rights evidence, and timed caption cues. Choose draft (480p) or final (1080p), landscape or portrait; render, preview and download MP4/SRT. An optional voice track mixes over quieter music. Plans can be exported/imported as JSON. Media paths must stay within the selected workspace. Requires FFmpeg/ffprobe with libass; no model SDK is needed for local editing.

This is a local adult-operated editor. Caption burn-in is automatic from supplied cues; automatic speech alignment, character-consistent generation and public hosted access are not implemented. Source clip audio is replaced by selected music/voice. Outputs remain unreviewed until watched/listened and independently checked.

`src/kids_research.py` provides injected-client bounded YouTube snapshots, time-separated growth ranking and an official Lyria Clip adapter. Provider tests are mocked; live model access, billing and generation remain unverified. Suno official exports can be imported as local audio. See [research and limits](docs/KIDS_EPISODES_RESEARCH.md).

Prototype WRE instructions are in `skillz/kids_episode_production/SKILLz.md` and `skillz/kids_trend_research/SKILLz.md`; these do not admit an autonomous runtime or publisher. Existing Shorts callers and uploader behavior are unchanged.

### Kids storyboard provider

The OpenRouter adapter in `src/openrouter_storyboard.py` reuses the existing AI Gateway provider configuration and accepts approved raster character references. Its first candidate is FLUX.2 Klein 4B (Apache-2.0 weights; hosted inference is paid). `StoryboardVideoShot` passes a reviewed frame to the separately configured video generator before the existing five-second trims and 15-second assembly. See INTERFACE.md for host binding, authorization and recovery. No browser login, duplicate key store, automatic model fallback or live deployment is added.
