# antifaFM Broadcaster - ModLog

## V3.3.2 - Discord voice live guild verification (2026-04-09)

**Slice**: `ANTIFAFM_DISCORD_VOICE_LIVE_GUILD_VERIFICATION_PHASE1`

**Context**: `antifaFM Radio` bot now authorized in FOUNDUPS server with Connect/Speak/Use Voice Activity permissions. This slice verifies and documents the live Discord voice lane.

**Documentation Added** (`README.md`):
- Live Discord Voice Setup section with bot authorization status
- Required Discord permissions table (Connect, Speak, Use Voice Activity)
- Startup sequence explanation (YouTube first, then Discord if enabled)
- Smoke verification runbook with env setup + launch command
- What is verified in code vs what requires live VC run
- Common failure modes table with symptoms/causes/fixes
- Boundary clarity: YouTube primary, Discord optional sibling

**What Was Already Verified** (code-level, V3.3.0–V3.3.1):
- Env parsing with fail-closed snowflake validation
- Adapter construction and isolated failure handling
- Health monitor wiring with restart callback
- Volume filter via FFmpeg `-af`
- Unit tests for boot paths (5 tests)

**What Requires Manual Live Run**:
- Actual bot→guild→channel connection
- FFmpeg→Opus audio quality in Discord
- Reconnect under network disruption
- Real health monitor recovery cycle

**No Code Changes**: Documentation-only slice.

**WSP**: WSP 15 (pre-action verification), WSP 22 (ModLog), WSP 97 (evidence).

---

## V3.3.1 - Discord voice hardening (2026-04-07)

**Follow-up**: FFmpeg `-af volume=` for `ANTIFAFM_DISCORD_VOICE_VOLUME` (replaces `PCMVolumeTransformer`, which rejects Opus sources). Guild/channel env IDs fail closed via `_parse_snowflake_env`. `telemetry.jsonl` removed from version control + `.gitignore` (runtime WSP 91 sink only).

---

## V3.3.0 - Discord voice output runtime integration (2026-04-07)

**Slice**: `ANTIFAFM_DISCORD_VOICE_OUTPUT_INTEGRATION_PHASE2`

**What changed**
- `src/discord_voice_output.py`: bounded adapter (Icecast → `FFmpegOpusAudio`, own `StreamHealthMonitor`, start/stop/get_status); optional import when `discord.py` missing.
- `src/antifafm_broadcaster.py`: env-gated `self.discord_output`, `_init_discord_output()`, start after YouTube success (isolated failure), stop cleans Discord lane, `get_status` + JSONL telemetry include `discord_voice`.
- `requirements.txt`: `discord.py>=2.3.0`, `PyNaCl>=1.5.0`.
- `tests/test_discord_voice_broadcaster_integration.py`: boot-path mocks (5 tests).

**Env gates**: `ANTIFAFM_DISCORD_VOICE_ENABLED`, `ANTIFAFM_BOT` (or `ANTIFAFM_DISCORD_BOT_TOKEN`), `ANTIFAFM_DISCORD_GUILD_ID`, `ANTIFAFM_DISCORD_VOICE_CHANNEL_ID`, optional `ANTIFAFM_DISCORD_VOICE_VOLUME`.

**WSP**: WSP 15 (optional P1 lane), WSP 27 (DAE lifecycle), WSP 64 (secrets via env), WSP 97 (evidence + test).

---

## V3.2.9 - Voxtral TTS Evaluation Contract (2026-03-29)

**Context**: WSP 97 evaluation of Mistral Voxtral TTS (4B parameter model with zero-shot voice cloning) for potential antifaFM integration.

**Evaluation Contract Created** (`docs/VOXTRAL_EVAL_CONTRACT.md`):

1. **Voice Output Surfaces Audited** (6 surfaces):
   - Icecast stream: Pure relay (NOT TTS candidate)
   - Karaoke overlay: STT only (NOT TTS candidate)
   - News ticker: Text display → narration (TTS candidate)
   - DJ interstitials: PRIMARY TTS candidate
   - Emergency alerts: Safety-critical TTS candidate
   - Branded intros/outros: Future TTS candidate

2. **Shared Audio Substrate Binding**:
   - Must use `audio_provider_registry.py` (NOT broadcaster-local registry)
   - Voxtral registered as `voxtral_tts_eval` with `production_enabled=False`
   - Env gate: `AUDIO_ALLOW_EVAL_PROVIDERS=1` required for eval

3. **Voice Cloning Policy Gate**:
   - Generic synthetic voices: OK without consent
   - Cloned DJ personas: REQUIRES `voice_cloning_policy.py` consent + whitelist
   - Kill switch support for emergency disable

4. **Success Metrics Defined**:
   - First-audio latency: < 500ms (blocker)
   - Quality score: >= 4.0/5.0 (blocker)
   - FFmpeg integration: Working (blocker)
   - Policy gate: 100% enforced (blocker)

**Out of Scope** (explicitly excluded):
- Production TTS swap (remains eval-only)
- EdgeTTS replacement in openclaw_voice.py
- Cloned DJ persona without consent
- Broadcaster-local duplicate provider registry

**WSP Compliance**:
- WSP 97: CoT/CoR evaluation applied
- WSP 22: ModLog updated
- WSP 72: Shared audio substrate, not broadcaster-local

**Next Steps** (Phase 2 when triggered):
1. Run latency benchmark with `AUDIO_ALLOW_EVAL_PROVIDERS=1`
2. Generate quality samples for DJ interstitials
3. Test FFmpeg audio mixing integration
4. Document results in `VOXTRAL_EVAL_RESULTS.md`

---

## V3.2.8 - News Maps Schema + VIDEO_SOURCES Fix (2026-03-25)

**Context**: OBS rotator broken - VIDEO_SOURCES used `video1-9` but actual OBS sources are `France 24`, `Al Jazeera`, etc. News schema needed conflict/shipping map rotation.

**WSP 97 Analysis Applied**:
- CoT: Retrieved actual OBS source names from 012 screenshot
- CoR: Evaluated VesselFinder embed (BLOCKED), LiveUAMap screenshot (BLOCKED)

**Changes**:

1. **VIDEO_SOURCES Fix** (`boot_layer_rotator/executor.py:170`):
   ```python
   # Before:
   _default_video_sources = "video1,video2,video3,video4,video5,video6,video7,video8,video9"

   # After:
   _default_video_sources = "France 24,Al Jazeera,Telaviv,BBC Straits,DW News"
   ```

2. **OBS Client Singleton** (`boot_layer_rotator/executor.py:177-223`):
   - Added `_obs_client` singleton with thread-safe lock
   - Connection reuse prevents WebSocket spam
   - Auto-reconnect on stale connection

3. **News Maps Executor Created** (`news_maps/executor.py`):
   - Screenshot capture via undetected-chromedriver
   - Ticker scraping from conflict map sources
   - 5-minute cache to reduce request frequency
   - Human-like delays (1-4s random)

4. **News Schema Integration** (`boot_layer_rotator/executor.py:419-459`):
   - Imports `capture_screenshot` from news_maps
   - Rotates through map screenshots (60s each)
   - Updates OBS image source with cached screenshots

**Files Created**:
- `skillz/news_maps/executor.py` (400+ lines)
- `skillz/news_maps/SKILLz.md`
- `skillz/news_maps/cache/` directory structure

**Files Modified**:
- `skillz/boot_layer_rotator/executor.py` - VIDEO_SOURCES, singleton, news integration

**CRITICAL STATUS - NEWS MAPS BLOCKED**:
- LiveUAMap: IP blocked ("automatic behavior detected")
- VesselFinder: Connection timeout on embed script
- VesselFinder screenshots: Timeout on page load
- **Impact**: News schema cannot capture maps - only VIDEO schema works

**Tested**:
- [x] `boot_layer_rotator --list` works (Windows Unicode fixed)
- [x] Rocket alerts ticker: 8 events scraped from rocketalert.live
- [ ] VIDEO rotation in OBS (UNTESTED)
- [ ] News maps in OBS (BLOCKED - sources detect automation)

**WSP Compliance**:
- WSP 15: Priority assessment (VIDEO schema = P0, news = PARK)
- WSP 22: ModLog updated
- WSP 97: CoT/CoR gates applied

**Next Steps**:
1. Test VIDEO schema rotation in OBS
2. Consider paid AIS API (aisstream.io) for shipping data
3. News maps require fundamentally different approach

---

## V3.2.7 - Fix Boot Layer Integration (2026-03-22)

**Context**: Stream showing "You have been blocked" (MarineTraffic WAF) and videos not rotating (always same video).

**Root Causes** (WSP 97 Hard Think analysis):
1. **GCC schema**: `gcc_daemon()` called without `use_screenshots=True` - screenshot mode not wired
2. **Video schema**: Showed ALL video sources (video1-9) simultaneously, no actual rotation

**Fixes**:

1. **GCC Screenshot Mode Wired** (`boot_layer_rotator/executor.py:385`):
   ```python
   # Before:
   result = await gcc_daemon(standalone=False)  # Missing screenshot mode!

   # After:
   result = await gcc_daemon(standalone=False, use_screenshots=True)  # Anti-WAF
   ```

2. **Video Rotation Implemented** (`boot_layer_rotator/executor.py:390-418`):
   ```python
   # Before: Show all videos, sleep 10 minutes (no rotation)
   # After: Cycle through video1-9, ~66 seconds each
   for i, video_src in enumerate(VIDEO_SOURCES):
       await set_source_visibility(video_src, True)  # Show current
       await asyncio.sleep(video_interval)  # 66s per video
   ```

**Test Results**: 38/38 PASSED
- `test_boot_layer_rotator.py`: 16 passed
- `test_gcc_shipping_tracker.py`: 22 passed

**WSP Compliance**: WSP 97 (CoT/CoR verification gates)

---

## V3.2.6 - Screenshot Mode Anti-WAF (2026-03-22)

**Context**: MarineTraffic.com blocked by Cloudflare WAF - showing "You have been blocked" page during schema rotation.

**Root Cause**: Repeated automated requests from OBS browser source (every 2 minutes) triggered Cloudflare anti-bot protection.

**Solution** - 012 Behavior Pattern:
1. **Screenshot capture mode** (`--screenshot` flag): Captures map screenshot via headless browser
2. **Single request**: One fetch per view (not continuous iframe refresh)
3. **Local cache**: Screenshots stored in `screenshot_cache/` directory
4. **OBS displays cached image**: Data URI of screenshot, not live URL
5. **Human-like timing**: Random delays (1-3s) before loading pages

**Usage**:
```bash
# Anti-WAF mode (recommended when blocked)
python executor.py --daemon --screenshot

# Original mode (direct URL embedding)
python executor.py --daemon
```

**New Functions**:
- `capture_map_screenshot(url, view_name)` - Headless Chrome screenshot
- `get_latest_screenshot(view_name)` - Get cached screenshot path
- `screenshot_to_data_uri(path)` - Convert PNG to data URI for OBS

**Files Modified**:
- `gcc_shipping_tracker/executor.py` - Screenshot capture + caching

**WSP Compliance**: WSP 91 (Observability), YouTube Anti-Detection Pattern (2025-12-15)

---

## V3.2.5 - Fix Schema Rotation & GCC Tracker (2026-03-19)

**Context**: Boot layer rotation not working - GCC showing planes/cookie popup, video not rotating, browser not fullscreen.

**Root Causes**:
1. **GCC URLs**: MarineTraffic has cookie consent popup blocking view
2. **Wrong content**: MarineTraffic showing aircraft, not AIS ships
3. **Schema handlers**: video/news schemas not wired in run_schema()
4. **Browser sizing**: Browser source not fullscreen (small box)

**Solution**:

1. **GCC Tracker** - Switched to VesselFinder (no popup, ships not planes):
   ```python
   VESSELFINDER_HORMUZ = "https://www.vesselfinder.com/map#11/26.4/56.3/type=8"
   VESSELFINDER_GULF = "https://www.vesselfinder.com/map#7/26.0/51.5/type=8"
   # type=8 = TANKERS ONLY
   ```

2. **Schema Handlers** - Added video/news execution in run_schema():
   - Video: Shows video grid (video1-9), waits 10 min
   - News: Shows browser source, waits 10 min

3. **Fullscreen Bounds** - Added `set_source_bounds_fullscreen()`:
   ```python
   boundsWidth: 1920.0, boundsHeight: 1080.0, boundsType: "OBS_BOUNDS_STRETCH"
   ```

**Files Modified**:
- `gcc_shipping_tracker/executor.py` - VesselFinder URLs
- `boot_layer_rotator/executor.py` - Schema handlers, fullscreen bounds

**WSP Compliance**: WSP 27 (DAE), WSP 91 (Observability)

---

## V3.2.4 - Fix Dual Audio Playback (2026-03-19)

**Context**: User reported hearing "2 players" in OBS - dual audio playback.

**Root Causes**:
1. **Primary**: OBS may have launched twice ("pancaked"), creating duplicate audio streams
2. **Secondary**: Schema rotation only controlled source **visibility**, not **audio muting**

**Solution**: Enhanced `configure_schema_visibility()` to also manage audio muting:

```python
async def set_source_mute(source_name: str, muted: bool) -> Dict[str, Any]:
    """Set OBS input source mute state."""
    client = _get_obs_client()
    client.set_input_mute(name=source_name, muted=muted)
```

**Audio Behavior by Schema**:
- **Video schema**: MUTE radio source, UNMUTE video sources (video audio plays)
- **Non-video schemas** (gcc, news): UNMUTE radio source, MUTE video sources (radio plays)

**Files Modified**:
- `boot_layer_rotator/executor.py` - Added `set_source_mute()`, enhanced `configure_schema_visibility()`

**WSP Compliance**: WSP 91 (Observability), WSP 27 (DAE Architecture)

---

## V3.2.3 - Suppress Background Daemon Console Logs (2026-03-19)

**Context**: GCC daemon logs (every 2 minutes) were appearing interleaved with the main menu, disrupting UI flow.

**Root Cause**: Background daemons (gcc_shipping_tracker, boot_layer_rotator, obsws_python) logged at INFO level to console while menu was waiting for input.

**Solution**: Set WARNING level for background daemon loggers inside `run_boot_rotator()`:
- `modules.platform_integration.antifafm_broadcaster.skillz.gcc_shipping_tracker.executor`
- `modules.platform_integration.antifafm_broadcaster.skillz.boot_layer_rotator.executor`
- `obsws_python.baseclient.ObsClient`
- `obsws_python.reqs.ReqClient`

**Impact**: INFO logs still go to file (`antifafm_broadcaster.log`), but no longer spam console during menu interaction.

**WSP Compliance**: WSP 91 (Observability - logs preserved to file)

---

## V3.2.2 - antifaFM DJ Audio Health Skill (2026-03-13)

**Context**: No audio when OBS launched. Audio source (`antifaFM Radio`) needs monitoring and auto-restart.

**Root Cause**: OBS mode (`ANTIFAFM_USE_OBS=1`) requires manual audio source configuration. No ai_overseer skill existed to monitor audio health.

**Solution**: Created `antifafm_dj` OpenClaw skill for audio health monitoring:

**Audio Stream**: `https://a12.asurahosting.com/listen/antifafm/radio.mp3`

**Skill Location**: `modules/ai_intelligence/ai_overseer/skillz/antifafm_dj/`

**Capabilities**:
1. `check_audio_health()` - Verify `antifaFM Radio` media source state
2. `restart_audio_source()` - Restart media source if stopped
3. `check_stream_reachable()` - Verify stream URL responds
4. `health_daemon()` - Continuous monitoring (30s interval)

**Integration**:
- `boot_layer_rotator` now uses `antifafm_dj` skill at startup
- Fallback to direct OBS control if skill unavailable

**Files Created**:
- `ai_overseer/skillz/antifafm_dj/SKILLz.md`
- `ai_overseer/skillz/antifafm_dj/executor.py`
- `ai_overseer/skillz/antifafm_dj/__init__.py`

**Files Modified**:
- `antifafm_broadcaster/README.md` - Documented audio source requirement
- `boot_layer_rotator/executor.py` - Uses antifafm_dj skill

**WSP Compliance**: WSP 27 (DAE Architecture), WSP 91 (Observability)

---

## V3.2.1 - OBS Visibility Control (2026-03-13)

**Context**: GCC map was loading in browser source but video grid sources remained visible on top, obscuring the map.

**Root Cause**: `grid_orchestrator` and `boot_layer_rotator` control DIFFERENT OBS sources:
- `grid_orchestrator` → video1-video9 scene items (video grid)
- `boot_layer_rotator` → browser source URL (MarineTraffic map)

No visibility coordination existed between them.

**Solution**: Added OBS scene item visibility control to boot_layer_rotator:
1. `set_source_visibility()` - Control individual source visibility
2. `configure_schema_visibility()` - Schema-based visibility presets

**Visibility Logic**:
```
GCC/news/chess schemas:
  - Hide video1-video9 (video grid)
  - Show browser source (MarineTraffic/Coming Soon)

Video schema:
  - Show video1-video9 (video grid)
  - Hide browser source
```

**Files Modified**:
- `skillz/boot_layer_rotator/executor.py` - Added visibility control functions

**WSP Compliance**: WSP 97 applied (Hard Think → First Principles → Build)

---

## V3.2.0 - Boot Layer Rotator Integration (2026-03-13)

**Context**: GCC shipping tracker view not appearing when OBS launches. WSP 97 investigation revealed boot_layer_rotator was implemented but never integrated into launch.py preflight.

**Root Cause**: Two disconnected schema systems existed:
1. `launch.py SCHEMAS` (VIDEO_GRID, KARAOKE, etc.) - ACTIVE
2. `boot_layer_rotator SCHEMAS` (gcc, video, news, chess) - NOT CONNECTED

**Solution**:
1. Added boot_layer_rotator integration to `_start_obs_orchestration()` in launch.py
2. Added Schema Testing submenu (Option 8) to antifaFM CLI menu
3. Gated by `ANTIFAFM_BOOT_ROTATOR_ENABLED=1` env var

**Changes**:
1. `scripts/launch.py` - Added rotator thread start after OBS connection
2. `modules/infrastructure/cli/src/main_menu.py` - Added Schema Testing submenu
3. `.env` - Added `ANTIFAFM_BOOT_ROTATOR_ENABLED=1`

**Schema Testing Menu** (Option 8):
```
1. Test GCC Shipping Tracker     [OK] READY
2. Test Video Rotation           [OK] READY
3. Test News Ticker              [OK] READY
4. Test Chess                    [..] SOON
5. Test Checkers                 [..] SOON
6. Test Cams                     [..] SOON
7. Start Full Rotation (10-min cycle)
8. Stop/Pause Rotation
9. Show Rotation Status
0. Back
```

**Startup Flow**:
```
launch.py → _start_obs_orchestration()
    → OBS connected ✓
    → grid_thread started ✓
    → news_thread started ✓
    → IF ANTIFAFM_BOOT_ROTATOR_ENABLED=1:
        → rotator_thread started (GCC → Video → News → ...)
```

**WSP Compliance**:
- WSP 97: Applied HoloIndex → Research → Hard Think → Build methodology
- WSP 27: Boot layer rotator follows DAE architecture
- WSP 22: ModLog updated

**Files Modified**:
- `scripts/launch.py` - Boot layer rotator thread integration
- `modules/infrastructure/cli/src/main_menu.py` - Schema Testing submenu

---

## V3.1.0 - WRE Integration (2026-03-07)

**Context**: CTO assessment revealed antifaFM at 19% WRE integration - isolated island unable to execute skills autonomously or participate in ecosystem coordination.

**Solution**: Added SkillTriggerMixin for full WRE integration. Broadcaster now fires domain skills on cadence during heartbeat loop.

**Changes**:
1. `AntifaFMBroadcaster` now inherits `SkillTriggerMixin`
2. Initializes with `domain="streaming"`, `cadence_minutes=15`
3. Fires `fire_pending_skills()` in heartbeat loop when broadcasting
4. Skills registered in `skills_registry_v2.json` with domain metadata
5. Status includes WRE trigger status for observability

**Skills Registered** (domain=streaming):
| Skill | Agents | Description |
|-------|--------|-------------|
| suno_stt_lyrics_extract | qwen, gemma | Whisper STT lyrics extraction |
| antifafm_add_video | qwen | Video library management |

**WRE Pipeline**:
```
Heartbeat (30s) → fire_pending_skills() → Discover domain skills
    → Libido gating → Execute via WREMasterOrchestrator
    → Store outcome in PatternMemory → Learn for next cycle
```

**WSP Compliance**:
- WSP 46: WRE Protocol (skill trigger integration)
- WSP 77: Agent Coordination (streaming domain skills)
- WSP 96: WRE Skills (domain-based discovery)

**Files Modified**:
- `src/antifafm_broadcaster.py` - Added SkillTriggerMixin
- `skillz/suno_stt_extract.json` - Added domain field
- `skillz/add_video_link.json` - Added domain field
- `wre_core/skillz/skills_registry_v2.json` - Registered skills

---

## V3.0.0 - Modular Schema Architecture (2026-03-06)

**Context**: 012 requested WSP-compliant modular architecture for visual schemas to enable independent expansion without monolithic growth. Schemas need individual ROADMAPs.

**Solution**: Created `schemas/` directory with self-contained schema modules. Each schema is independently expandable with its own ROADMAP.md, implementation, and tests.

**Architecture Created**:
```
schemas/
├── __init__.py          # Registry with auto-import
├── base.py              # BaseSchema ABC + dataclasses
├── video_loop/          # COMPLETE - Background video
├── karaoke/             # COMPLETE - STT lyrics overlay
├── entangled/           # COMPLETE - Bell state 0102
├── waveform/            # COMPLETE - Audio waveform
├── spectrum/            # COMPLETE - Frequency spectrum
├── news_ticker/         # PARTIAL - RSS ticker
└── livecam/             # PLANNED - Multi-cam + CamSentinel
```

**Key Components**:
- `BaseSchema` abstract class with `build_ffmpeg_filter()` contract
- `SchemaType` enum for type-safe schema selection
- `register_schema()` / `get_schema_by_name()` for dynamic registry
- Auto-import on package load triggers registration
- `scheme_manager.py` updated to use modular schemas first (fallback to legacy)

**Schema Implementation Pattern**:
```python
class KaraokeSchema(BaseSchema):
    NAME = "karaoke"
    MODE = SchemaMode.FFMPEG

    def build_ffmpeg_filter(self) -> str:
        # Schema-specific FFmpeg filter
        ...

register_schema(SchemaType.KARAOKE, KaraokeSchema)
```

**7 Schemas Registered**:
| Schema | Status | Mode | Commands |
|--------|--------|------|----------|
| video_loop | COMPLETE | FFMPEG | /video |
| karaoke | COMPLETE | FFMPEG | /karaoki |
| entangled | COMPLETE | FFMPEG | /entangled, /0102 |
| waveform | COMPLETE | FFMPEG | /waveform |
| spectrum | COMPLETE | FFMPEG | /spectrum |
| news_ticker | PARTIAL | FFMPEG | /news |
| livecam | PLANNED | OBS | /cam, /grid |

**WSP Compliance**:
- WSP 3: Module Organization (domain/module structure)
- WSP 11: Interface Protocol (BaseSchema contract)
- WSP 27: Universal DAE Architecture
- WSP 49: Module Structure (ROADMAP.md per schema)
- WSP 84: Code Reuse (shared base + registry)

---

## V2.9.0 - Layer 8 External Stream Chat Integration (2026-03-06)

**Context**: 012 showed screenshot of MIDDLE EAST MULTI-LIVE (https://www.youtube.com/watch?v=BXMH9yBck3w) and requested ability to engage in external stream chats via OpenClaw, with `!party` for heart clicks.

**Solution**: Created External Stream Chat skill in AI Overseer with DOM-based engagement.

**Key Features**:
- Navigate to ANY YouTube Live URL (not just owned channels)
- DOM selectors for chat input, send button, and reactions
- `!party` command uses pixel offset (40px left of chat input) to find heart button
- Human behavior simulation integration

**Files Created** (in `ai_intelligence/ai_overseer/skillz/external_stream_chat/`):
- `SKILLz.md` - Skill documentation
- `src/stream_chat_dae.py` - Main DAE implementation (200+ lines)
- `executor.py` - CLI and skill executor
- `__init__.py` files

**CLI Integration** (`openclaw_menu.py` option 10):
- Interactive mode: `!send`, `!party`, `!watch`, `!status`, `!quit`
- Quick Send mode
- Party mode (continuous heart clicks)
- Watch Only mode

**Pixel Offset Strategy**:
```python
# Heart button is ~40px left of chat input
chat_rect = driver.find_element("css selector", "#input").rect
reaction_x = chat_rect['x'] - 40
```

**DOM Selectors**:
```python
'chat_input': "#input.yt-live-chat-text-input-field-renderer"
'send_button': "#send-button button"
'heart_emoji': "[aria-label*='heart' i]"
```

**WSP Compliance**:
- WSP 27: DAE Architecture (sensor/actuator)
- WSP 77: Agent Coordination (OpenClaw integration)
- WSP 91: Observability (engagement telemetry)

---

## V2.8.0 - FoundUp MVP White-Label Streaming Roadmap (2026-03-06)

**Context**: 012 asked to think about how antifaFM becomes a white-label FoundUp MVP that anyone can deploy for their own YouTube streaming.

**Key Insight**: The architecture we're building is generic - video rotation, karaoke, livecam, news ticker, chat bots, games. Move2Japan, FoundUps, or ANY YouTuber could deploy the same infrastructure.

**Roadmap Addition**: "FoundUp MVP - White-Label Streaming Solution"

### White-Label Architecture
- **Config Layer**: YAML-driven channel settings, branding, enabled schemas
- **Schema Modules**: Selectable per deployment (VIDEO_LOOP, KARAOKE, LIVECAM, NEWS, GAMES)
- **FoundUps Layer**: F_i tokens, streaming hours as PoW, CABR integration

### Deployment Examples
| Creator | Schemas | Use Case |
|---------|---------|----------|
| antifaFM | All | Political radio + visuals |
| Move2Japan | VIDEO_LOOP, KARAOKE | Tokyo ambience + J-pop |
| FoundUps | VIDEO_LOOP, NEWS | pAVS updates + tech news |

### Proof of Work Model
- `StreamingProofOfWork` class tracks streaming hours
- Health-weighted hours (stable streams worth more)
- Integrates with pAVS CABR engine

### Target: One-Click Deployment
```bash
npx create-foundups-stream my-channel
```

**Corrections Made**:
- Fixed schema modularization to reference games EXTERNALLY at `modules/gamification/games/` (not inside antifafm)
- Games is used by other systems (Move2Japan) so stays in gamification domain

**Files Modified**:
- `ROADMAP.md` - Added FoundUp MVP section (~200 lines)
- Corrected EXTERNAL_INTEGRATIONS reference for games

**WSP Compliance**:
- WSP 26: FoundUPS DAE Tokenization (F_i for streaming)
- WSP 29: CABR Engine (streaming metrics as V2 inputs)
- WSP 3: Module Organization (config-driven deployment)

---

## V2.7.0 - Layer 7 Livecam + Schema Modularization Roadmap (2026-03-06)

**Context**: 012 showed screenshot of MIDDLE EAST MULTI-LIVE 4-cam grid with military alerts ticker, asked about viewer voting rotation and AI sentinel.

**Roadmap Additions**:

### Layer 7 - Viewer Voting Rotation
- `!rotate1-4` commands for viewer-initiated camera rotation
- 51% threshold of active chatters (messaged in last 5 minutes)
- 60-second voting window, 5-minute cooldown per camera
- Mod override: `!force-rotate1 beirut`

### Layer 7 - Cam Sentinel AI (Gemma)
**Decision**: Use Gemma for pattern detection, NOT Qwen3
- `score_frame()` - Interest score 0-1 (~10ms)
- `detect_event()` - Binary "is something happening?"
- Auto-suggest rotation when one feed scores >0.7

### Schema Modularization Architecture
**Problem**: Monolithic `scheme_manager.py` + 891-line ROADMAP
**Solution**: Each schema becomes its own module:
```
schemas/
├── video_loop/   (ROADMAP.md + src/ + tests/)
├── karaoke/      (ROADMAP.md + src/ + tests/)
├── livecam/      (ROADMAP.md + src/ + tests/)
├── news_ticker/  (ROADMAP.md + src/ + tests/)
└── games/        (ROADMAP.md + src/ + tests/)
```
- `BaseSchema` interface for all schemas
- Roadmap concatenation script
- Independent testing per schema

**Files Modified**:
- `ROADMAP.md` - Added viewer voting, cam sentinel, schema modularization sections

**WSP Compliance**:
- WSP 3: Module Organization
- WSP 49: Module Structure
- WSP 72: Module Independence

---

## V2.6.0 - OBS Startup Verification + Broadcast Readiness Preflight (2026-03-06)

**Context**: `main.py` could log "OBS streaming to YouTube" even when OBS output never became active.
This happened when OBS was still blocked on YouTube broadcast setup ("Create broadcast and start streaming").

**Solution**:
1. Hardened OBS start path to verify `output_active` after `StartStream`.
2. Added main boot preflight to ensure a broadcast exists before OBS stream request.
3. Forced OBS stream service into `rtmp_custom` at startup (server/key from env/API), bypassing
   OBS YouTube account modal flow.
4. Added explicit diagnostics when OBS start request is accepted but output remains inactive.

**Files Modified**:
- `modules/platform_integration/antifafm_broadcaster/src/obs_controller.py`
  - `start_streaming()` now polls for active output before returning success
  - `ensure_stream_service_custom()` applies `rtmp_custom` service settings
  - Adds timeout-driven failure diagnostics and `get_last_start_error()`
- `main.py`
  - Auto-start now runs `ensure_obs_broadcast_ready()` before OBS start request
  - Startup prints accurate status instead of unconditional success
- `modules/platform_integration/antifafm_broadcaster/tests/test_obs_controller_startup.py`
  - New tests for active/inactive startup paths
- `modules/platform_integration/antifafm_broadcaster/tests/TestModLog.md`
  - Test coverage entry

**New/Used Env Vars**:
```bash
ANTIFAFM_OBS_START_VERIFY_SECONDS=20   # Wait window for OBS output_active
ANTIFAFM_OBS_START_POLL_SECONDS=0.5    # Poll interval for stream status
ANTIFAFM_OBS_AUTO_CREATE_BROADCAST=1   # Ensure broadcast exists before OBS start
ANTIFAFM_OBS_FORCE_CUSTOM_SERVICE=1    # Force OBS rtmp_custom service mode at startup
ANTIFAFM_BROADCAST_TITLE=...           # Optional override
ANTIFAFM_BROADCAST_DESCRIPTION=...     # Optional override
ANTIFAFM_BROADCAST_PRIVACY=public      # public|unlisted|private
```

**Operational Result**:
- Prevents false-positive "stream started" logs.
- Gives deterministic operator guidance when OBS is modal-blocked.
- Adds first-step automation for the missing broadcast creation flow.

---

## V2.5.0 - Karaoke Cache Bridge Integration (2026-03-06)

**Context**: STT extraction was complete (208 songs in `ffcpln_lyrics.db`), but karaoke display needed timed lyrics in `lyrics_cache.db`.

**Solution**: Created bridge function to import STT lyrics with estimated timing.

**Pipeline**:
```
ffcpln_lyrics.db (plain text)
    ↓
_estimate_lyrics_timing() (based on song duration)
    ↓
_save_lyrics_to_cache() (to lyrics_cache.db)
    ↓
Karaoke display ready
```

**Files Modified**:
- `scripts/suno_stt_lyrics_extractor.py` - Added `import_stt_to_karaoke_cache()` + `_estimate_lyrics_timing()`
- `scripts/launch.py` - Added `run_stt_to_karaoke_bridge()` + `--import-to-cache` CLI flag
- `skillz/suno_stt_extract.json` - Updated to v1.1.0 with bridge parameters

**Usage**:
```bash
# Bridge STT lyrics to karaoke cache
python launch.py --import-to-cache

# Import first 50 songs only
python launch.py --import-to-cache --import-limit 50
```

**Result**:
- 149 whisper-stt songs now in karaoke cache
- Timing estimated: ~4 seconds per line (based on duration)
- Karaoke lookup working: `get_cached_lyrics('UnDaoDu', 'title')` returns timed lyrics

**WSP Compliance**:
- WSP 84: Reused `_save_lyrics_to_cache()` from launch.py
- WSP 78: SQLite Layer B storage (lyrics_cache.db)
- WSP 72: Bridge isolated in suno_stt_lyrics_extractor.py

---

## V2.4.0 - Suno STT Lyrics Extractor (2026-03-05)

**Context**: 012 asked "can we use the system be build that STT the music?" after browser-based approaches failed.

**Solution**: Fully automated lyrics extraction using Speech-to-Text (faster-whisper) on Suno audio.

**Principle**: "Everything 012 does, 0102 should be able to do" - ZERO manual work.

**Pipeline**:
```
Suno CDN (cdn1.suno.ai/{id}.mp3)
    ↓
SunoAudioDownloader (download + cache)
    ↓
SunoSTTTranscriber (wraps FasterWhisperSTT - WSP 84 reuse)
    ↓
LyricsDeduplicator (SHA256 hash, SQLite storage)
    ↓
ffcpln_lyrics.db
```

**Files Added**:
- `scripts/suno_stt_lyrics_extractor.py` - Main extractor (550+ lines)
- `skillz/suno_stt_extract.json` - SKILLz definition for WRE
- `tests/test_suno_stt_extractor.py` - Test suite (7 tests)

**Files Modified**:
- `scripts/launch.py` - Added `run_suno_stt_extract()` + `--suno-stt` CLI flag
- `tests/TestModLog.md` - Added test documentation

**Usage**:
```bash
# Extract all 238 FFCPLN songs (fully automated)
python launch.py --suno-stt

# Test with 5 songs
python launch.py --suno-stt --max 5

# Higher accuracy model
python launch.py --suno-stt --model small
```

**V2.4.1 Pagination Fix** (2026-03-05):
- Fixed: Playlist only returning 50/238 songs
- Root cause: Suno uses API cursor pagination, not scroll-based lazy loading
- Solution: Use `studio-api.prod.suno.com/api/playlist/{id}?cursor=` with cursor-based pagination
- Result: Now fetches all 231 available songs (7 deleted/private)

**Tested**:
- [x] CDN download works (1.3 MB test song)
- [x] STT transcription works (28 words, 0.91 confidence)
- [x] Deduplication works (SHA256 hash)
- [x] API pagination works (231/238 songs)
- [x] 7/7 unit tests pass

**WSP Compliance**:
- WSP 84: Reuses `FasterWhisperSTT` from `voice_command_ingestion`
- WSP 50: HoloIndex search verified existing BatchTranscriber
- WSP 78: SQLite storage (Layer B - Operational Relational Store)
- WSP 5: Test coverage added

---

## V2.3.0 - YouTube 12-Hour Limit Auto-Restart (2026-03-04)

**Context**: 012 noted "youtube has a max video lenght... we need to have that timer in the live so that it can restart"

**Solution**: Auto-restart FFmpeg before hitting YouTube's 12-hour stream limit.

**Changes**:
- Added `self.max_duration_seconds` config (default: 11 hours)
- Added ENV: `ANTIFAFM_MAX_DURATION_HOURS` (set to 0 to disable)
- Added duration check in `_heartbeat_loop()`
- Triggers `_restart_stream()` when limit approached
- Resets `start_time` after successful restart

**Behavior**:
```
Stream starts → Timer tracks uptime → At 11 hours → Graceful restart → Timer resets → Continues
```

**WSP Compliance**:
- WSP 91: Uptime tracked in telemetry
- WSP 27: DAE Phase 2 (Agentic) auto-recovery pattern

---

## V2.2.0 - Lyrics Cache System (2026-03-04)

**Context**: 012 asked "as the music plays cant we capture the song name and lyrics with timestap then use that for the karaoke later?" Then asked: "we have a wsp Database should we use json or dba?"

**Solution**: SQLite per WSP 78 (Layer B: Operational Relational Store). Refactored from JSON to SQLite for proper indexing, concurrent access, and namespace compliance.

**Changes**:
- Added `LYRICS_DB_PATH` constant: `data/lyrics_cache.db` (SQLite)
- Added `_get_lyrics_db()`: Lazy SQLite connection with WAL mode per WSP 78
- Table: `modules_lyrics_cache` (WSP 78 namespace contract)
- Indexes: `idx_lyrics_artist`, `idx_lyrics_source` (fast lookups)
- Added `_normalize_cache_key()`: Lowercase artist|title normalization
- Added `_save_lyrics_to_cache()`: INSERT OR UPDATE with source tracking
- Added `get_cached_lyrics()`: Cache lookup (instant, no API call)
- Added `import_lrc_file()`: CLI function to manually add .lrc files
- Added `get_lyrics_cache_stats()`: Returns synced/plain/miss/manual counts via SQL
- Modified `fetch_lyrics()`: Check cache first, save successful fetches

**Architecture**:
```
Song Change → Check SQLite → (hit) → instant return
                   ↓ (miss)
              LrcLib API → parse → INSERT INTO modules_lyrics_cache → return
```

**SQLite Schema** (WSP 78 compliant):
```sql
CREATE TABLE modules_lyrics_cache (
    cache_key TEXT PRIMARY KEY,      -- artist|title normalized
    artist TEXT NOT NULL,
    title TEXT NOT NULL,
    lyrics_json TEXT NOT NULL,       -- JSON array of [timestamp_ms, text]
    source TEXT NOT NULL,            -- lrclib-synced, lrclib-plain, lrclib-miss, manual-lrc
    line_count INTEGER DEFAULT 0,
    cached_at TEXT NOT NULL
);
```

**Benefits**:
- Instant lookup for repeat songs (indexed query)
- Concurrent-safe (WAL mode, busy_timeout)
- Builds library over time (~500 unique songs on antifaFM)
- Manual correction via `import_lrc_file()`
- Works offline after initial population

**WSP Compliance**:
- WSP 00: First principles (SQLite > JSON for operational state)
- WSP 78: Layer B Operational Relational Store, namespace `modules_*`
- WSP 91: Observability (cache hit/miss logged, stats function)

---

## V2.0.0 - Karaoke Mode + Schema System (2026-03-04)

**Context**: 012 requested karaoke lyrics display with schema switching via chat commands.

**Hard Think Analysis**:
1. **PID Violation Fixed**: Chat agents now start AFTER stream verification, not at preflight
2. **Env Signal**: `ANTIFAFM_CHAT_ACTIVE=1` tells main YT DAE to exclude antifafm from rotation
3. **Lyrics Source**: Pre-fetched from LrcLib API (not STT) - known songs have existing lyrics
4. **First Principles**: Pre-fetched > STT because antifaFM plays known songs, zero latency, accurate

**Changes**:
- Added schema system: `VIDEO_GRID`, `VIDEO_FULL`, `KARAOKE`, `NEWS`
- Added command processor: `!karaoke`, `!video`, `!grid`, `!full`, `!news` (and /slash variants)
- Added `fetch_lyrics()`: LrcLib API integration (free, synced .lrc format)
- Added `_parse_lrc()`: .lrc timestamp parser
- Added elapsed time tracking from antifaFM API for line sync
- Modified grid orchestrator to be schema-aware
- Fixed chat agent timing: starts after stream verified (not preflight)

**OBS Setup (AUTOMATED)**:
- Added `_ensure_karaoke_sources()`: Auto-creates text sources if missing
- Lyrics Line 1: Arial Black 72pt, white, black outline, centered at (960, 400)
- Lyrics Line 2: Arial 48pt, transparent white, centered at (960, 500)
- Tries `text_gdiplus_v3` (Windows), falls back to `text_ft2_source_v2` (Linux/Mac)

**WSP Compliance**:
- WSP 00: Hard think applied (first principles analysis)
- WSP 84: Used existing chat infrastructure, no duplication

---

## V1.9.0 - OBS WebSocket Integration + Full Stream Orchestration (2026-03-04)

**Context**: 012 requested OBS-based video orchestration with song-synced rotation, news ticker, and AI chat agents.

**Changes**:
- Added `_start_obs_orchestration()` to `launch.py`:
  - Grid orchestrator: Song-synced video rotation (4 layouts)
  - News monitor: RSS feeds from Al Jazeera, BBC, Guardian, France24, DW
  - Keyword filtering: iran, tehran, attack, missile, strike, war, beirut, israel, hezbollah, idf, bombing
  - Updates "Scrolling Ticker" and "Now Playing" OBS text sources
- Added `_start_chat_agents()` to `launch.py`:
  - Launches AutoModeratorDAE with antifaFM persona
  - Sets YT_FORCE_CHANNEL=antifafm, YT_ACTIVE_PERSONA=antifafm
- All components run as daemon threads alongside FFmpeg broadcaster
- Env controls: `ANTIFAFM_OBS_ORCHESTRATION=0`, `ANTIFAFM_CHAT_AGENTS=0`

**Launch Chain**:
```
main.py (ANTIFAFM_AUTO_START=1)
  └── start_antifafm_background()
        ├── YouTube OAuth preflight
        ├── YouTube Go Live (browser automation)
        ├── FFmpeg broadcaster thread
        └── _start_obs_orchestration()
              ├── Grid Orchestrator (song-synced video rotation)
              ├── News Monitor (RSS ticker updates)
              └── _start_chat_agents() (AutoModeratorDAE)
```

**WSP Compliance**:
- WSP 84: Used existing livechat infrastructure (no new code for chat)
- WSP 00: Coherence maintained (012 operator reference)
- WSP 22: ModLog updated

---

## V1.3.5 - Full OpenClaw/IronClaw CLI for Broadcaster (2026-02-28)

**Context**: OpenClaw/IronClaw agents need full control over antifaFM broadcaster.

**Changes**:
- Enhanced `scripts/launch.py` with full CLI for agent control:
  - `--start` - Start broadcaster in background
  - `--stop` - Stop background broadcaster
  - `--status` - Check broadcaster status
  - `--json` - JSON output for agent parsing
  - `--title "..."` - Set stream title before start
  - `--desc "..."` - Set stream description before start
  - `--diagnose` - Run diagnostics with JSON output
  - `--layer1` - Disable visual effects

**OpenClaw/IronClaw CLI Usage**:
```powershell
# Start broadcaster with JSON output
python launch.py --start --json --title "antifaFM Radio"
# Output: {"success": true, "status": "started", "pid": 12345, "title": "antifaFM Radio"}

# Check status
python launch.py --status --json
# Output: {"running": true, "status": "broadcasting", "uptime": 3600}

# Stop broadcaster
python launch.py --stop --json
# Output: {"success": true, "stopped": true}

# Run diagnostics
python launch.py --diagnose --json
```

**WSP Compliance**:
- WSP 77: Agent Coordination (OpenClaw/IronClaw can control full broadcast lifecycle)

---

## V1.3.4 - Exact DOM Selectors + OpenClaw CLI (2026-02-28)

**Context**: 012 provided exact YouTube Studio DOM paths for reliable automation.

**Changes**:
- Updated `edit_stream_settings()` with exact DOM selectors from 012:
  - Edit button: `ytcp-button#edit-button` (Method 1)
  - Title: `#title-textarea` inside `#title-wrapper` (Method 1)
  - Description: `#description-textarea` inside `#description-wrapper` (Method 1)
  - Save: `ytcp-button#save-button` (Method 1)
- Enhanced CLI for OpenClaw/IronClaw programmatic use:
  - Added `--json` flag for JSON output (agent parsing)
  - Added `--status` flag for stream status check only
  - All results returned as structured JSON when `--json` used

**DOM Selectors (012-provided)**:
```javascript
// Edit button
document.querySelector('#edit-button, ytcp-button#edit-button')

// Title input (inside wrapper)
document.querySelector('#title-wrapper').querySelector('#title-textarea')

// Description input (inside wrapper)
document.querySelector('#description-wrapper').querySelector('#description-textarea')

// Save button
document.querySelector('#save-button, ytcp-button#save-button')
```

**OpenClaw/IronClaw CLI Usage**:
```powershell
# JSON output for agent parsing
python youtube_go_live.py --json --title "antifaFM Radio"
# Output: {"success": true, "go_live": {...}, "edit": {...}}

# Status check only
python youtube_go_live.py --status --json
# Output: {"success": true, "status": {"verified": true, "elapsed": 2.3}}

# Full automation with JSON
python youtube_go_live.py --go-live --json --title "Live" --desc "24/7 music"
```

**WSP Compliance**:
- WSP 27: Pre-FFmpeg configuration (Phase 2 agentic control)
- WSP 77: Agent Coordination (OpenClaw/IronClaw can parse JSON output)

---

## V1.3.3 - Stream Edit Settings + Studio Load Wait (2026-02-28)

**Context**: Need to edit stream title/description before FFmpeg connects.

**Changes**:
- Added `edit_stream_settings()` in `src/youtube_go_live.py`:
  - Opens Edit dialog in YouTube Studio
  - Sets title and description fields
  - Saves changes
- Added CLI support: `--title`, `--desc`, `--edit`, `--go-live` flags
- Increased studio load wait: 8s → 15s (studio is slow)
- Added `test_edit_stream()` in test suite:
  - Scans for Edit buttons
  - Clicks Edit and scans input fields
  - Takes screenshot of edit dialog

**CLI Usage**:
```powershell
# Just go live
python youtube_go_live.py

# Go live + set title
python youtube_go_live.py --title "antifaFM Radio - Live Now"

# Go live + set title + description
python youtube_go_live.py --title "Morning Show" --desc "24/7 resistance music"

# Just edit (assumes already in studio)
python youtube_go_live.py --edit --title "New Title"
```

**WSP Compliance**:
- WSP 27: Pre-FFmpeg configuration (Phase 2 agentic control)

---

## V1.3.2 - DOM Polling Verification for Dropdown (2026-02-28)

**Context**: Fixed 2-second delay after Create click is fragile - need DOM verification.

**Changes**:
- Updated `src/youtube_go_live.py`:
  - Added `_verify_dropdown_appeared()` - Polls DOM every 300ms for menu items
  - Replaced fixed `asyncio.sleep(2)` with verification loop (max 5s timeout)
  - Reports item count and elapsed time when dropdown detected
- Updated `tests/test_go_live_steps.py`:
  - Added `verify_dropdown_appeared()` - Same DOM polling pattern
  - Step 5 now verifies dropdown before proceeding to Step 6

**Verification Flow**:
```
Click Create → Poll DOM for menu items (300ms interval)
  → Detected: "Dropdown appeared (3 items, 0.6s)"
  → Timeout (5s): "WARNING: Dropdown not detected, trying Go Live anyway..."
```

**DOM Selectors for Dropdown**:
- `[role="menuitem"]`, `[role="option"]`
- `tp-yt-paper-item`, `ytcp-text-menu a`
- `ytd-menu-service-item-renderer`

**WSP Compliance**:
- WSP 27: DOM verification before action (Phase 2 agentic reliability)
- WSP 5: Test suite updated with verification

---

## V1.3.1 - Go Live Test Suite + Debug Improvements (2026-02-27)

**Context**: Go Live automation not clicking buttons - need step-by-step debugging.

**Changes**:
- Created `tests/test_go_live_steps.py` - Step-by-step Go Live debugging
  - Scans and prints all visible buttons on page
  - Scans menu items after Create click
  - Takes screenshots at each step
  - Reports stream status
- Created `tests/__init__.py` - Test module initialization
- Created `tests/README.md` - Test documentation
- Created `tests/TestModLog.md` - Test change tracking
- Updated `src/youtube_go_live.py`:
  - Added detailed debug output at each step
  - Print page title and URL after navigation
  - Print Create button click result
  - Better error reporting for Go Live failures
- Updated `scripts/launch.py`:
  - Simplified flow - always attempt Go Live
  - Removed false-positive "already live" detection
  - Added traceback on errors

**Test Usage**:
```powershell
python modules/platform_integration/antifafm_broadcaster/tests/test_go_live_steps.py
```

**Debug Output**:
- Screenshots saved to `logs/screenshot_*.png`
- Button list printed to console
- Menu items printed after Create click

**WSP Compliance**:
- WSP 5: Test coverage for automation
- WSP 6: Test documentation (README, TestModLog)

---

## V1.3.0 - YouTube Go Live Automation + Video Backgrounds (2026-02-27)

**Context**: Enable full autonomous broadcast - FFmpeg starts, Selenium clicks "Go Live".

**Changes**:
- Created `src/youtube_go_live.py` - Selenium automation for YouTube Go Live
  - `click_go_live(driver)`: Clicks Create (+) → Go live (persistence dropdown)
  - `ensure_logged_in(driver)`: Verifies YouTube login status
  - Fallback selectors for DOM changes
- Updated `src/__init__.py` - Export new functions
- Updated `src/ffmpeg_streamer.py` - Video background support
  - Detects video files (.mp4, .webm, .mkv, .avi, .mov)
  - Uses `-stream_loop -1` for infinite video loop
  - Scale + format filter for video backgrounds

**Video Background Configuration**:
```bash
# In .env - set visual to a video file instead of image
ANTIFAFM_DEFAULT_VISUAL=modules/platform_integration/antifafm_broadcaster/assets/backgrounds/December 29 2025.mp4
```

**Go Live Usage**:
```python
from modules.platform_integration.antifafm_broadcaster.src import click_go_live
success = await click_go_live(driver)  # Clicks Create → Go live
```

**WSP Compliance**:
- WSP 27: Universal DAE Architecture (Phase 2: Agentic automation)
- WSP 84: Code Reuse (foundups_selenium patterns)

---

## V1.2.0 - PID-Based Instance Locking (2026-02-26)

**Context**: Headless broadcaster wasn't launching properly due to orphaned FFmpeg processes and lack of instance coordination.

**Root Cause Analysis**:
- Multiple FFmpeg processes conflicting on same RTMP endpoint
- No mechanism to detect/kill orphaned broadcaster instances
- Needed heartbeat-based PID locking (same pattern as main.py `monitor_youtube`)

**Changes**:
- Updated `scripts/launch.py` - Integrated `InstanceLock` from `instance_manager.py`
  - `main()`: Lock acquisition before start, release in finally block
  - `start_antifafm_background()`: Duplicate detection, kill orphans, acquire lock
  - `stop_antifafm_background()`: Release lock on shutdown
- Updated `src/ffmpeg_streamer.py` - Added `_kill_orphan_ffmpeg_streams()` method
  - Detects stale FFmpeg processes streaming to same RTMP endpoint
  - Called in `start()` before launching new stream

**Instance Lock Pattern** (from main.py):
```python
from modules.infrastructure.instance_lock.src.instance_manager import get_instance_lock
lock = get_instance_lock("antifafm_broadcaster")
duplicates = lock.check_duplicates()  # Find orphans
lock.kill_pids(duplicates)            # Kill them
lock.acquire()                        # Get exclusive lock
# ... run broadcaster ...
lock.release()                        # Release on shutdown
```

**WSP Compliance**:
- WSP 84: Code Reuse (same pattern as `monitor_youtube` in main.py)
- WSP 27: Universal DAE Architecture (Phase 1 coordination)

---

## V1.1.0 - Layer 2.5 Zero-Cost Animation (2026-02-26)

**Context**: Added Occam's Layer visual effects using FFmpeg filters - maximum visual impact with zero AI cost.

**Changes**:
- Created `src/visual_effects.py` - FFmpeg filter_complex builder (280+ lines)
  - Ken Burns (zoompan) effect for slow zoom/pan animation
  - Color Pulse (hue shift) for subtle color variation
  - GIF Overlay for animated logo in corner
  - Image Cycling support (optional, requires image library)
- Updated `src/ffmpeg_streamer.py` - Integrated visual effects builder
  - Conditional filter_complex injection
  - GIF input handling with `-ignore_loop 0`
  - Proper `-map` output when effects enabled
- Updated `src/__init__.py` - Export visual effects classes
- Created `assets/backgrounds/` directory for image cycling
- Created `assets/overlays/` directory for GIF overlays
- Updated ROADMAP.md with Layer 2.5 specification

**Occam's Razor Decision** (WSP):
- Layer 4 (Veo3/Sora2 AI) was overkill - high cost, low marginal benefit
- Layer 2.5 provides 80% of visual impact at 0% of AI cost
- FFmpeg filters are zero-runtime-cost once command is built

**Environment Variables Added**:
```
ANTIFAFM_FX_KEN_BURNS=true
ANTIFAFM_FX_COLOR_PULSE=true
ANTIFAFM_FX_GIF_OVERLAY=true
ANTIFAFM_FX_GIF_PATH=<path>
ANTIFAFM_FX_IMAGE_CYCLE=false
ANTIFAFM_FX_IMAGE_DIR=<path>
```

**Files Created**:
```
modules/platform_integration/antifafm_broadcaster/
    src/visual_effects.py          # NEW - FFmpeg visual effects builder
    assets/backgrounds/            # NEW - Directory for cycling images
    assets/overlays/               # NEW - Directory for GIF overlays
```

**WSP Compliance**:
- WSP 84: Occam's Razor - simplest solution with maximum value
- WSP 27: Universal DAE Architecture (Phase 1: Protocol layer for effects)
- WSP 91: Observability (effect status in get_status())

**Next Steps**:
- Create `assets/overlays/antifafm_pulse.gif` (animated logo)
- Create 5-10 branded background images
- Test combined effects on live YouTube stream

---

## V1.0.0 - Layer 1 MVP (2026-02-25)

**Context**: Created new module to stream antifaFM radio to YouTube Live via FFmpeg.

**Changes**:
- Created module structure per WSP 49
- Implemented `ffmpeg_streamer.py` - FFmpeg subprocess management
- Implemented `stream_health_monitor.py` - Auto-recovery with exponential backoff
- Implemented `antifafm_broadcaster.py` - Main DAE class
- Added CLI integration (option 10 in YouTube menu)
- Added environment variables to `.env.example`
- Created documentation: README.md, INTERFACE.md, ROADMAP.md

**Module Cube Patterns Used (WSP 84)**:
- `peertube_relay_handler.py` - FFmpeg subprocess pattern
- `youtube_dae_heartbeat.py` - Heartbeat + telemetry pattern
- `auto_moderator_dae.py` - DAE lifecycle pattern

**WSP Compliance**:
- WSP 27: Universal DAE Architecture (4-phase lifecycle)
- WSP 49: Module Structure (README, INTERFACE, src/, tests/)
- WSP 64: Secure credential management (stream key via ENV)
- WSP 77: Agent Coordination (AI Overseer integration)
- WSP 84: Code Reuse (module cube patterns)
- WSP 91: DAEMON Observability (JSONL telemetry)

**Files Created**:
```
modules/platform_integration/antifafm_broadcaster/
    README.md
    INTERFACE.md
    ROADMAP.md
    ModLog.md
    requirements.txt
    src/
        __init__.py
        antifafm_broadcaster.py
        ffmpeg_streamer.py
        stream_health_monitor.py
    assets/
        (default_visual.png auto-generated on first run)
```

**Next Steps**:
- Layer 2: Song metadata from AzuraCast API
- Layer 3: Animated waveform visualization
- Register as FoundUp in simulator

---

## V1.3.1 - Headless Launch Flow Alignment + Edge Diagnostics (2026-03-03)

**Context**: The default `launch.py` path could start FFmpeg without first activating the YouTube Studio endpoint, while the step-by-step test still targeted Chrome `9222` instead of the antifaFM Edge `9223` profile.

**Changes**:
- Updated `scripts/launch.py`
  - added shared YouTube Studio preflight helper
  - foreground `python .../launch.py` now runs the same go-live preparation as the background path
- Updated `tests/test_go_live_steps.py`
  - uses `ANTIFAFM_BROWSER_PORT` / `FOUNDUPS_LIVECHAT_CHROME_PORT`
  - attaches with Edge WebDriver when port `9223` is in use
- Updated `src/ffmpeg_streamer.py`
  - orphan FFmpeg cleanup now matches both `rtmp://` and `rtmps://` targets

**Impact**:
- The documented headless launcher now matches the actual runtime behavior.
- antifaFM debugging no longer defaults to the wrong browser/port pair.
- RTMPS migrations no longer leave stale FFmpeg publishers behind during cleanup.

---

## V1.3.2 - Launch Runtime Hotfix (2026-03-03)

**Context**: The new YouTube preflight helper crashed at runtime with `NameError: time is not defined`, and `start_antifafm_background()` still had function-local `asyncio` imports that shadowed the module import and broke the background thread closure.

**Changes**:
- Updated `scripts/launch.py`
  - added module-level `time` import for endpoint readiness polling
  - removed function-local `asyncio` imports inside `start_antifafm_background()`
  - removed redundant function-local `time` imports in the same launch path

**Impact**:
- YouTube endpoint preflight no longer aborts before FFmpeg startup.
- Background broadcaster thread can create its event loop normally.

---

## V1.3.3 - Failed-State Stabilization (2026-03-03)

**Context**: When FFmpeg ingest failed repeatedly, the health monitor reached `FAILED` but the monitor and heartbeat loops kept polling, which spammed the same `Conversion failed!` tail and `Manual intervention required` message every cycle.

**Changes**:
- Updated `src/stream_health_monitor.py`
  - stop further health checks once the monitor enters `FAILED`
  - stop the monitor loop when max consecutive failures is reached
- Updated `src/antifafm_broadcaster.py`
  - stop the broadcaster heartbeat loop once the health monitor enters `FAILED`
  - write one final telemetry snapshot for the terminal failed state

**Impact**:
- A dead ingest attempt now settles into one stable error state instead of flooding logs every 30 seconds.
- Manual diagnosis is easier because the first failure remains visible instead of being buried by repeated copies.

---

## V1.3.4 - Targeted YouTube OAuth Preflight (2026-03-03)

**Context**: antifaFM launch had no built-in way to validate or repair its dedicated YouTube OAuth token before ingest resolution. The broadcaster also auto-rotated across unrelated YouTube credential sets, which could point ingest lookup at the wrong account.

**Changes**:
- Updated `scripts/launch.py`
  - added a targeted antifaFM OAuth preflight helper for the configured credential set
  - added `--reauth-youtube` to trigger the browser-based re-auth flow from launch
  - added OAuth health into `--diagnose`
  - background startup now actually runs the async YouTube-prep helper instead of storing the coroutine object
- Updated `src/youtube_ingest_resolver.py`
  - added explicit `token_index` support for ingest lookup
- Updated `src/antifafm_broadcaster.py`
  - resolve ingest URLs using `ANTIFAFM_YOUTUBE_TOKEN_SET` instead of generic auto-rotation
- Updated `src/ffmpeg_streamer.py`
  - threaded the same token-set selection into FFmpeg-side ingest URL resolution
- Updated `modules/platform_integration/youtube_auth/src/youtube_auth.py`
  - `preflight_oauth_check()` now supports checking a specific subset of credential sets

**Impact**:
- antifaFM startup can now verify or repair the correct YouTube token before launch.
- Ingest URL lookup is now pinned to antifaFM's own OAuth account instead of consulting unrelated channels.

---

## V1.3.5 - Studio Stream-State Detection Fix (2026-03-03)

**Context**: The direct YouTube Studio launcher was treating the instructional text `Connect your encoder to go live` as proof that a clickable Go Live action existed. That produced stale logs like `Clicking Go Live button...` even when Studio was already on the encoder-ready stream page. It also conflated the channel dashboard with the specific `video/.../livestreaming` page.

**Changes**:
- Updated `src/youtube_go_live.py`
  - added a structured Studio page-state probe that detects a real visible Go Live button separately from body text
  - added direct stream-page resolution from the dashboard's `Edit in studio` link
  - switched the default direct flow to treat `Connect your encoder` plus no visible Go Live button as `endpoint_ready`
- Updated `scripts/launch.py`
  - launcher readiness checks now use the same structured Studio page-state probe
  - startup logs now describe Studio stream preparation instead of the old `Create -> Go Live` path

**Impact**:
- antifaFM no longer reports a nonexistent Go Live button on the encoder stream page.
- The launcher now distinguishes between the channel dashboard and the real active stream page.
- When Studio is already on `video/.../livestreaming`, the flow exits as ready instead of attempting an obsolete click.

---

## V1.3.6 - Edge Tab Restore Cleanup (2026-03-03)

**Context**: antifaFM background startup force-killed Edge with `taskkill /F`. That left the dedicated automation profile marked as crashed, so the next Edge launch restored old Studio tabs and then opened the requested Studio URL again. The visible result was multiple identical YouTube Studio tabs.

**Changes**:
- Updated `src/youtube_go_live.py`
  - added `_reset_automation_profile_startup()` before launching Edge/Chrome with the automation profile
  - normalize `profile.exit_type` from `Crashed` to `Normal`
  - clear `Default/Sessions/Tabs_*` and `Session_*` restore files for the dedicated automation profile

**Impact**:
- Cold antifaFM browser launches no longer restore stale Studio tabs from previous forced shutdowns.
- A fresh launch should open only the intended Studio tab instead of duplicating restored tabs.

---

*ModLog format per WSP 22*
