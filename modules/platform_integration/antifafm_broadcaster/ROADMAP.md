# antifaFM Broadcaster - Roadmap

## Current: Layer 1 - MVP (Static Image + Audio)

**Status**: COMPLETE

- [x] FFmpeg subprocess management
- [x] Static image overlay
- [x] RTMP streaming to YouTube Live
- [x] Auto-recovery with exponential backoff
- [x] Health monitoring
- [x] JSONL telemetry
- [x] CLI integration
- [ ] Bind/test AI Overseer alerts (initialization exists; delivery unimplemented)
- [x] **YouTube 12-hour limit auto-restart** (2026-03-04)

### YouTube Duration Limit (24/7 Streaming)
YouTube Live has a 12-hour max duration. Auto-restart before limit:
- **Default**: Restart at 11 hours (1 hour buffer)
- **ENV**: `ANTIFAFM_MAX_DURATION_HOURS=11` (set to 0 to disable)
- **Behavior**: Graceful FFmpeg restart, resets timer, stream continues

## Current: Layer 2.6 - OBS Broadcast Handshake Reliability

**Status**: COMPLETE (2026-03-06)

OBS startup path now treats stream activation as a handshake, not a fire-and-forget call.

### What Changed
- [x] Verify `output_active` after `StartStream` before reporting success
- [x] Add startup diagnostics for "accepted request but inactive output" cases
- [x] Add preflight broadcast readiness check before OBS stream request
- [x] Add focused tests for active/inactive OBS startup behavior

### Remaining Enhancements
- [ ] Optional direct OBS service reconfiguration from API-created stream key
- [ ] Optional YouTube API transition-to-live after encoder active
- [ ] OBS modal detection hook (if API supports front-end state introspection)

## Current: Layer 2.5 - Zero-Cost Animation (Occam's Layer)

**Status**: COMPLETE (2026-02-26)

Visual effects using FFmpeg filters - maximum impact with zero AI cost.

### Effects Stack
1. **Ken Burns (zoompan)** - Slow zoom/pan creates movement from static image
2. **Color Pulse (hue shift)** - Subtle color variation for visual interest
3. **GIF Overlay** - Animated logo/waveform in corner
4. **Image Cycling** - Rotate through branded images (optional)

### Tasks
- [x] Create `src/visual_effects.py` - FFmpeg filter builder
- [x] Update `src/ffmpeg_streamer.py` - Integrate visual effects
- [x] Create `assets/backgrounds/` directory
- [x] Create `assets/overlays/` directory
- [ ] Create default GIF overlay (`antifafm_pulse.gif`)
- [ ] Create 5-10 branded background images
- [x] Test combined filter_complex on live stream
- [x] Fix zoompan filter (use `on/fps` not `t`)
- [x] Fix yuv420p pixel format for YouTube RTMP
- [x] Create headless launch scripts
- [x] Video library manager (`video_library.py`)
- [x] `/add link` command for Managing Directors
- [x] Video background looping support
- [ ] Document ENV variables for effect tuning

### Environment Variables (Layer 2.5)
```bash
ANTIFAFM_FX_KEN_BURNS=true        # Enable Ken Burns zoom/pan
ANTIFAFM_FX_COLOR_PULSE=true      # Enable color pulse
ANTIFAFM_FX_GIF_OVERLAY=true      # Enable GIF overlay
ANTIFAFM_FX_GIF_PATH=assets/overlays/antifafm_pulse.gif
ANTIFAFM_FX_IMAGE_CYCLE=false     # Enable image cycling (requires image library)
ANTIFAFM_FX_IMAGE_DIR=assets/backgrounds/
```

### FFmpeg Command (Layer 2.5)
```bash
ffmpeg -re -i https://antifaFM.com/radio.mp3 \
  -loop 1 -i background.png \
  -ignore_loop 0 -i antifafm_pulse.gif \
  -filter_complex "
    [1:v]zoompan=z='1.0+0.1*sin(t*0.05)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s=1920x1080:fps=30[kb];
    [kb]hue=h=sin(t*0.1)*15[colored];
    [2:v]scale=150:150[gif];
    [colored][gif]overlay=W-w-20:H-h-20[out]
  " \
  -map "[out]" -map 0:a \
  -c:v libx264 -preset ultrafast \
  -c:a aac -b:a 128k -ar 44100 \
  -f flv rtmp://a.rtmp.youtube.com/live2/{STREAM_KEY}
```

## Future: Layer 2 - Metadata Integration

**Status**: COMPLETE (2026-03-04) via OBS WebSocket

Display current song information on YouTube stream.

### Tasks
- [x] Fetch "now playing" metadata via antifaFM API (`a12.asurahosting.com/api/nowplaying`)
- [x] Display song info overlay on video (OBS "Now Playing" text source)
- [x] Handle metadata refresh on song change (5-second polling)
- [ ] Create `src/azuracast_client.py` - AzuraCast API client (OPTIONAL - direct API used)
- [ ] Update YouTube stream title dynamically via API (FUTURE)

### Technical Notes
```bash
# AzuraCast API endpoint (example)
curl https://antifaFM.com/api/nowplaying
```

## Future: Layer 3 - Waveform Visualization

**Status**: PLANNED

Replace static image with animated audio visualization.

### Tasks
- [ ] Create `src/waveform_visualizer.py`
- [ ] FFmpeg showwaves filter for waveform
- [ ] FFmpeg showfreqs filter for frequency spectrum
- [ ] Color theming (antifaFM branding)
- [ ] Per-song visual transitions

### FFmpeg Filters
```bash
# Waveform visualization
ffmpeg -i audio.mp3 -filter_complex \
  "[0:a]showwaves=s=1920x1080:mode=line:colors=red" \
  -c:v libx264 output.mp4

# Frequency spectrum
ffmpeg -i audio.mp3 -filter_complex \
  "[0:a]showfreqs=s=1920x1080:mode=bar:colors=red" \
  -c:v libx264 output.mp4
```

## Future: Layer 4 - AI-Generated Visuals

**Status**: FUTURE

Generate unique visuals per song using AI.

### Tasks
- [ ] Integrate Veo3/Sora2 APIs
- [ ] Song-triggered visual generation
- [ ] Visual caching system
- [ ] Pre-generation queue for upcoming songs
- [ ] Style matching (genre -> visual style)

### Dependencies
- Veo3 API access
- Sora2 API access
- Significant compute budget

## FoundUp Registration

**Status**: PLANNED

Register antifaFM Broadcaster as a FoundUp in the simulator.

### Tasks
- [ ] Create FoundUp entry in `modules/foundups/simulator/`
- [ ] Define F_i token metrics
- [ ] Track streaming hours as proof-of-work
- [ ] F0_DAE tier (pre-OPO)

## Next: Layer 2.5C - News Ticker Overlay

**Status**: COMPLETE (2026-03-04) via OBS WebSocket

Display scrolling news headlines on the stream. Auto-updates from international RSS feeds.

### Architecture
```
headlines.json (mod-editable)
    ↓
Python watcher (detect changes)
    ↓
FFmpeg drawtext filter (scrolling text)
    ↓
YouTube Live stream
```

### Features
- [x] RSS feed integration (Al Jazeera, BBC, Guardian, France24, DW)
- [x] Keyword filtering (iran, tehran, attack, missile, strike, war, beirut, israel, hezbollah, idf, bombing)
- [x] Auto-update every 5 minutes
- [x] OBS "Scrolling Ticker" text source integration
- [ ] Create `src/news_ticker.py` - headline manager (OPTIONAL - inline in launch.py)
- [ ] Create `data/headlines.json` - mod-editable headline file (FUTURE)
- [ ] Hot-reload: detect headline changes without restart (FUTURE)
- [ ] Simple web UI for mods to edit headlines (FUTURE)

### FFmpeg Filter (drawtext scrolling)
```bash
# Scrolling text at bottom of screen
-vf "drawtext=textfile=headlines.txt:fontsize=36:fontcolor=white:
     x=w-mod(t*100\\,w+tw):y=h-50:
     shadowcolor=black:shadowx=2:shadowy=2"
```

### headlines.json Format
```json
{
  "headlines": [
    {"text": "🔥 BREAKING: Anti-fascist rally draws thousands", "priority": 1},
    {"text": "✊ Community organizers launch mutual aid network", "priority": 2},
    {"text": "📢 foundups.com - Building the future of autonomous ventures", "priority": 3}
  ],
  "scroll_speed": 100,
  "display_duration": 10,
  "last_updated": "2026-02-26T13:30:00Z",
  "updated_by": "mod_username"
}
```

### Mod Access
- Direct file edit: `antifafm_broadcaster/data/headlines.json`
- CLI command: `python -m antifafm_broadcaster.cli headlines add "New headline"`
- Web UI (future): Simple form to add/remove/reorder headlines

### WSP Compliance
- WSP 64: Secure mod authentication (file permissions / API keys)
- WSP 91: Observability (headline change logging)

---

## Next: Layer 2.5B - AI Chat Agents

**Status**: COMPLETE (2026-03-04) - wired into launch.py

Deploy AI personas to engage in YouTube Live chat during antifaFM streams.
**NO NEW CODE NEEDED** - uses existing `livechat` module infrastructure (WSP 84).

### Personas (already configured in persona_registry.py)
- **antifaFM** - Channel identity (primary for antifaFM stream)
- **UnDaoDu** - Cross-promote when relevant
- **FoundUps** - Promote foundups.com ecosystem

### Configuration (ENV vars)
```bash
# Focus AutoModeratorDAE on antifaFM stream
YT_FORCE_CHANNEL=antifafm
YT_ACTIVE_PERSONA=antifafm

# antifaFM already in youtube_channel_registry.py:
# - key: "antifafm"
# - id: UCVSmg5aOhP4tnQ9KFUg97qA
# - browser: Edge (port 9223, account_section 1)
```

### Existing Infrastructure
- `livechat/src/auto_moderator_dae.py` - Chat monitoring DAE
- `livechat/src/persona_registry.py` - antifaFM persona config
- `shared_utilities/youtube_channel_registry.py` - Channel metadata
- Rotation list includes antifaFM: `["Move2Japan", "UnDaoDu", "FoundUps", "antifaFM"]`

### Tasks
- [x] antifaFM persona exists in persona_registry.py
- [x] antifaFM channel in youtube_channel_registry.py
- [x] Wired into launch.py `_start_chat_agents()` function
- [x] Auto-sets YT_FORCE_CHANNEL=antifafm and YT_ACTIVE_PERSONA=antifafm
- [x] Runs AutoModeratorDAE as daemon thread alongside OBS orchestration
- [ ] Verify Whack-a-MAGA responses work with antifaFM persona (runtime test)

### WSP Compliance
- WSP 77: Agent Coordination (multi-persona chat)
- WSP 80: DAE Orchestration (chat DAE lifecycle)
- WSP 91: Observability (chat telemetry)

---

## Next: Layer 2.5D - Karaoke Mode (Lyrics Overlay)

**Status**: IN PROGRESS (2026-03-04) - Layer 0 complete

Real-time lyrics display using pre-fetched synced lyrics from LrcLib API.

### Architecture (Layer 0 - Pre-fetched Lyrics with Cache)
```
Song Change → Check Cache → (miss) → LrcLib API → .lrc parser → Cache → OBS Text Source → YouTube
                  ↓ (hit)                                           ↑
           [instant return]                              [auto-saved for reuse]
```

### Why Pre-fetched > STT (First Principles)
- antifaFM plays KNOWN songs → lyrics exist in databases
- LrcLib API: free, no key, synced .lrc format
- STT: 2-3s latency + accuracy issues + CPU cost
- Pre-fetched: instant, accurate, zero latency
- **Lyrics Cache**: As songs play, lyrics auto-captured for future use

### Open Source Stack
- **[LrcLib](https://lrclib.net)** - Free synced lyrics API (USING)
- **[faster-whisper](https://github.com/SYSTRAN/faster-whisper)** - STT fallback (FUTURE Layer 3)
- **OBS WebSocket** - Text source updates (USING)

### Lyrics Cache System (WSP 78 SQLite - 2026-03-04)
Automatic caching of lyrics as songs play via SQLite (Layer B: Operational Relational Store):
- **Location**: `data/lyrics_cache.db` (SQLite, WAL mode)
- **Table**: `modules_lyrics_cache` (WSP 78 namespace contract)
- **Flow**: Check cache → miss → fetch LrcLib → (if miss) → Whisper STT → save to cache → display
- **Sources tracked**: `lrclib-synced`, `lrclib-plain`, `lrclib-miss`, `manual-lrc`, `whisper-stt`
- **CLI import**: `import_lrc_file('Artist', 'Title', 'song.lrc')` for manual additions
- **Stats**: `get_lyrics_cache_stats()` returns synced/plain/miss/manual/whisper counts
- **Indexes**: artist, source (fast lookups)

### Whisper STT Fallback (2026-03-05)
For **original FFCPLN songs** not in LrcLib, uses Whisper STT to transcribe:
- **Trigger**: When cache returns `lrclib-miss` (original song detected)
- **Process**: Capture 30s audio → Whisper base.en → word timestamps → cache
- **Dependencies**: `faster-whisper` (pip install faster-whisper)
- **Source type**: `whisper-stt` (cached for future use)

### Features
- [x] LrcLib API integration (`fetch_lyrics()` in launch.py)
- [x] .lrc format parser (`_parse_lrc()`)
- [x] **Lyrics cache** (`lyrics_cache.db` - SQLite per WSP 78)
- [x] Manual .lrc import (`import_lrc_file()` for songs not in LrcLib)
- [x] Cache statistics (`get_lyrics_cache_stats()`)
- [x] Schema system (`VIDEO_GRID`, `VIDEO_FULL`, `KARAOKE`, `NEWS`)
- [x] Command processor (`!karaoke`, `!video`, `!grid`, `!full`, `!news`)
- [x] Elapsed time from antifaFM API for line sync
- [x] Two-line display (current + next line)
- [x] Auto-create OBS text sources (`_ensure_karaoke_sources()`)
- [ ] STT fallback for songs without lyrics (Layer 3)

### OBS Setup (AUTOMATED)
Text sources are auto-created by `_ensure_karaoke_sources()`:
1. **Lyrics Line 1** - Arial Black 72pt, white, black outline, centered
2. **Lyrics Line 2** - Arial 48pt, slightly transparent, centered below

Falls back to "Now Playing" source if auto-creation fails.

### Schema Commands (Chat)
```
!karaoke   - Switch to karaoke/lyrics mode
!video     - Switch to video grid mode
!grid      - Same as !video
!full      - Single video full screen
!news      - News-focused layout
/karaoke   - Slash command also works
```

### Environment Variables
```bash
ANTIFAFM_USE_OBS=1            # OBS mode: Skip FFmpeg/browser automation, only run OBS WebSocket + chat
ANTIFAFM_OBS_ORCHESTRATION=1  # Enable OBS orchestration (default on)
ANTIFAFM_CHAT_AGENTS=1        # Enable chat agents (default on)
# Schema defaults to VIDEO_GRID on startup
```

### OBS Mode (ANTIFAFM_USE_OBS=1)
When enabled, the broadcaster skips all browser automation and FFmpeg encoding:
- **Skipped**: FFmpeg cleanup, Edge browser launch, Go Live automation, stream verification
- **Active**: OBS WebSocket orchestration (video grid, karaoke, news ticker, schema commands)
- **Active**: Chat agents (persona engagement, command handling)
- **Use case**: OBS handles streaming directly via its own RTMP connection

### WSP Compliance
- WSP 27: DAE Architecture (karaoke as Phase 1 protocol layer)
- WSP 91: Observability (STT latency metrics)

## Integration Opportunities

1. **Live Chat Integration**: Announce current song in YouTube chat
2. **Social Media Cross-Post**: Tweet song changes
3. **Discord Bot**: Now-playing webhook to Discord
4. **Statistics Dashboard**: Streaming uptime, songs played, listener count

## Version History

| Version | Date | Layer | Status |
|---------|------|-------|--------|
| 1.0.0 | 2026-02-25 | Layer 1 | COMPLETE |
| 1.5.0 | 2026-02-26 | Layer 2.5 | COMPLETE |
| 1.6.0 | 2026-03-04 | Layer 2.5C | COMPLETE (News Ticker via OBS) |
| 1.7.0 | 2026-03-04 | Layer 2.5B | COMPLETE (AI Chat Agents) |
| 1.8.0 | 2026-03-04 | Layer 2 | COMPLETE (Metadata/Now Playing via OBS) |
| 1.9.0 | 2026-03-04 | OBS Grid | COMPLETE (Song-synced video rotation) |
| 2.0.0 | 2026-03-04 | Layer 2.5D | COMPLETE (Karaoke - LrcLib lyrics) |
| 2.1.0 | 2026-03-04 | Schema System | COMPLETE (Commands: !karaoke, !video, !grid, !news) |
| 2.2.0 | 2026-03-04 | Lyrics Cache | COMPLETE (Auto-capture lyrics as songs play) |
| 2.3.0 | 2026-03-05 | OBS Mode | COMPLETE (ANTIFAFM_USE_OBS=1 skips browser automation) |
| 2.4.0 | 2026-03-05 | LinkedIn Skill | COMPLETE (FFCPLN-aligned posting to GeoZai) |
| 2.5.0 | 2026-03-05 | Layer 5 | COMPLETE (Live Shorts Clipper) |
| 2.6.0 | 2026-03-06 | OBS Handshake | COMPLETE (Broadcast readiness preflight) |
| 2.7.0 | 2026-03-06 | Layer 7 Spec | ROADMAP (Multi-cam + Viewer Voting + Cam Sentinel) |
| 2.8.0 | 2026-03-06 | FoundUp MVP | ROADMAP (White-label streaming solution) |
| 2.9.0 | 2026-03-06 | Layer 8 | COMPLETE (External Stream Chat - DOM engagement) |
| 3.0.0 | TBD | Layer 3 | PLANNED (Waveform Visualization) |
| 4.0.0 | TBD | Layer 4 | FUTURE (AI-Generated Visuals) |
| 6.0.0 | TBD | Layer 6 | PLANNED (AI Music Videos - Veo/Sora available) |

---

## Next: Layer 5 - Live Shorts Clipper

**Status**: COMPLETE (2026-03-05)

Automatically generate 1-3 minute shorts from antifaFM live stream audio.

### Concept
- Capture audio segments during live stream
- Pair with FFCPLN-branded visuals
- Upload as Shorts via Move2Japan channel
- Use existing `ffcpln_title_enhance` skill for metadata
- **Karaoke mode**: Overlay lyrics for visual appeal

### Architecture
```
Live Stream Audio → Segment Detector (song boundaries)
        ↓
   Audio Clipper (1-3 min segments)
        ↓
   Visual Composer (background + Ken Burns)
        ↓
   Karaoke Overlay (lyrics from cache OR Whisper STT)
        ↓
   Metadata Generator (FFCPLN titles/descriptions)
        ↓
   Output Folder → youtube_shorts_scheduler CLI
```

### Tasks
- [x] Create `src/shorts_clipper.py` - Audio segment capture
- [x] Integrate with AzuraCast API for song boundary detection
- [x] Create visual templates for Shorts (1080x1920 vertical)
- [x] Reuse `ffcpln_title_enhance` skill for metadata
- [x] Track which songs have been clipped (avoid duplicates)
- [x] **Karaoke mode** with `--karaoke` flag
- [x] **Whisper STT fallback** for original FFCPLN songs (no LrcLib)
- [ ] Schedule uploads via `youtube_shorts_scheduler`

### Karaoke Mode (--karaoke)
```bash
# Create clip with lyrics overlay
python -m antifafm_broadcaster.src.shorts_clipper --karaoke --once

# Lyrics priority:
# 1. SQLite cache (manual imports or previous transcriptions)
# 2. LrcLib API (for known songs)
# 3. Whisper STT (for original FFCPLN songs - auto-transcribe)
```

### Whisper STT for Original Songs
012's original FFCPLN songs aren't in LrcLib. When `lrclib-miss` is detected:
1. Capture 30s audio from live stream
2. Transcribe with Whisper (base.en model)
3. Extract word-level timestamps
4. Cache as `whisper-stt` source for future clips

### Visual Options (Layer 5.0)
1. **Static + Ken Burns** - Branded background with zoom/pan
2. **Waveform** - Audio visualization (reuse Layer 3)
3. **Lyric Cards** - Animated lyrics from cache (reuse Layer 2.5D)

### Content Types
- **Full Song Clip** (2-3 min) - Complete song with visuals
- **Highlight Clip** (30-60 sec) - Chorus/hook segment
- **Lyric Focus** (15-30 sec) - Key lyrics with text animation

### Dependencies
- AzuraCast "now playing" API for song boundaries
- Lyrics cache (Layer 2.5D) for lyric content
- `ffcpln_title_enhance` skill for metadata
- `youtube_shorts_scheduler` for upload automation

### WSP Compliance
- WSP 77: Agent Coordination (clipper → scheduler → uploader)
- WSP 80: DAE Orchestration (shorts generation pipeline)
- WSP 91: Observability (clip telemetry)

---

## Next: Layer 6 - AI Music Video Generation

**Status**: PLANNED (2026-03-05) - Veo & Sora APIs AVAILABLE

Generate unique AI music videos for antifaFM shorts using Google Veo and OpenAI Sora.

### API Access
- **Google Veo**: Available via Vertex AI / AI Studio
- **OpenAI Sora**: Available via API
- **Strategy**: Veo for longer clips, Sora for style variety

### Concept
- Use AI video generation to create music videos from FFCPLN songs
- Lyrics drive visual narrative (using cached lyrics from Layer 2.5D)
- Genre/mood analysis for style matching
- Pre-generate videos for 160+ playlist songs

### Architecture
```
Song Metadata (lyrics, genre, mood)
        ↓
   Prompt Generator (visual narrative from lyrics)
        ↓
   AI Video API (Veo primary, Sora alternate)
        ↓
   Audio Sync (align video to song duration)
        ↓
   Post-Processing (FFCPLN branding overlay)
        ↓
   Shorts Upload (antifaFM channel)
```

### Video Generation Approaches
1. **Lyric-Driven** - Each lyric line generates a scene prompt
2. **Mood-Driven** - Genre/mood analysis generates consistent aesthetic
3. **Political-Driven** - FFCPLN themes (democracy, resistance, workers) as visual motifs
4. **Hybrid** - Veo for narrative, Sora for style moments

### FFCPLN Visual Themes (Prompt Library)
```python
THEMES = {
    "democracy": "crowds marching, raised fists, voting booths, capitol buildings",
    "labor": "workers united, picket lines, factory floors, union halls",
    "resistance": "protest signs, megaphones, night marches, candle vigils",
    "hope": "sunrise, diverse communities, children playing, green spaces",
    "warning": "storm clouds, fractured symbols, red alerts, surveillance cameras",
    "freedom": "broken chains, open roads, birds in flight, open doors"
}
```

### Tasks
- [ ] Create `src/music_video_generator.py` - Main orchestrator
- [ ] Create `src/veo_client.py` - Google Veo API integration
- [ ] Create `src/sora_client.py` - OpenAI Sora API integration
- [ ] Create `src/lyric_to_prompt.py` - Convert lyrics to visual prompts
- [ ] Create `src/video_cache.py` - SQLite cache for generated videos
- [ ] Build prompt templates for FFCPLN themes
- [ ] Create mood-to-visual mapping (genre detection)
- [ ] Build pre-generation queue for 160+ playlist songs
- [ ] Create `data/video_cache.db` - Track generated videos

### Generation Strategy
1. **Priority Queue**: Popular songs first (play count from AzuraCast)
2. **Batch Generation**: Off-peak hours to manage API costs
3. **Cache First**: Check cache before generating
4. **Fallback Chain**: Veo → Sora → Static visual (Layer 5)

### Cost Management
- Track API usage per song
- Set daily/weekly generation limits
- Prioritize songs without videos
- Consider shorter clips (30s) for expensive songs

### Output Specs
- **Resolution**: 1080x1920 (vertical Shorts)
- **Duration**: Match song length (1-3 min typical)
- **Format**: MP4 with H.264
- **Audio**: Original song audio synced

### Dependencies
- Veo API credentials (Vertex AI)
- Sora API credentials (OpenAI)
- Lyrics cache (Layer 2.5D)
- `ffcpln_title_enhance` skill for metadata

### WSP Compliance
- WSP 77: Agent Coordination (generator → post-processor → uploader)
- WSP 80: DAE Orchestration (video generation pipeline)
- WSP 91: Observability (generation telemetry, cost tracking)
- WSP 78: SQLite video cache (Layer B operational store)

---

## Future: Layer 7 - Multi-Camera Live Feeds & Enhanced Ticker

**Status**: PLANNED (2026-03-05)

**Inspiration**: [MIDDLE EAST MULTI-LIVE](https://www.youtube.com/watch?v=zQvwNP67sg4) - 4-cam grid with military alerts ticker

Deploy multi-camera live feed grid with categorized news ticker, allowing mods to dynamically control camera views and news categories.

### Architecture
```
                    ┌─────────────────────────────────────┐
                    │         OBS MULTI-CAM SCENE          │
                    ├──────────────┬──────────────────────┤
                    │  CAM 1       │       CAM 2          │
                    │  [Location]  │       [Location]     │
                    │              │                      │
                    ├──────────────┼──────────────────────┤
                    │  CAM 3       │       CAM 4          │
                    │  [Location]  │       [Location]     │
                    │              │                      │
                    └──────────────┴──────────────────────┘
  ┌──────────────────────────────────────────────────────────────────┐
  │ MISSILES  DRONES  SHELLING  AIRSPACE  NATO  SANCTIONS  CEASEFIRE │
  ├──────────────────────────────────────────────────────────────────┤
  │ 🔴 BREAKING: Iranian corvette struck during Operation Epic Fury  │
  │ [NAVAL NEWS • 8H AGO]                                            │
  └──────────────────────────────────────────────────────────────────┘
```

### Features

#### Multi-Camera Grid
- [x] 4-camera grid layout (inspired by MIDDLE EAST MULTI-LIVE)
- [ ] Create `src/multicam_controller.py` - Camera feed manager
- [ ] OBS scene collection with grid layout
- [ ] Camera location labels (city, feed type)
- [ ] Temperature/time overlay per camera
- [ ] LIVE indicator per feed
- [ ] Mod commands: `!cam1 [url]`, `!cam2 [url]`, etc.

#### Live Feed Sources
```python
CAMERA_PRESETS = {
    # Middle East
    "beirut": "rtsp://earthcam.com/beirut",
    "tel_aviv": "rtsp://earthcam.com/telaviv",
    "jerusalem": "rtsp://earthcam.com/jerusalem",
    "dubai": "rtsp://earthcam.com/dubai",
    # US Cities
    "dc": "rtsp://earthcam.com/washington",
    "nyc": "rtsp://earthcam.com/timessquare",
    "la": "rtsp://earthcam.com/losangeles",
    # Europe
    "london": "rtsp://earthcam.com/london",
    "paris": "rtsp://earthcam.com/paris",
    # Custom (mod-provided)
    "custom1": None,
    "custom2": None,
}
```

#### Enhanced News Ticker (Military Alerts Style)
- [ ] Create `src/military_alerts_ticker.py` - Advanced ticker system
- [ ] Category tabs (horizontal filter bar)
- [ ] Color-coded sources (Naval News = teal, BBC = red, etc.)
- [ ] Time-ago display ("8H AGO", "1H AGO")
- [ ] RSS aggregation from defense/news sources
- [ ] SQLite cache for headlines (avoid duplicates)

#### Category System
```python
ALERT_CATEGORIES = {
    "MILITARY_ALERTS": {"color": "#FF4444", "keywords": ["military", "alert", "warning"]},
    "MISSILES": {"color": "#FF6600", "keywords": ["missile", "ballistic", "launch"]},
    "DRONES": {"color": "#FFCC00", "keywords": ["drone", "UAV", "unmanned"]},
    "SHELLING": {"color": "#FF3333", "keywords": ["shell", "artillery", "mortar"]},
    "AIRSPACE": {"color": "#9933FF", "keywords": ["airspace", "NOTAM", "flight"]},
    "NAVAL": {"color": "#00CCCC", "keywords": ["naval", "ship", "submarine", "corvette"]},
    "AIR_FORCE": {"color": "#3399FF", "keywords": ["air force", "fighter", "bomber"]},
    "NATO": {"color": "#0066CC", "keywords": ["NATO", "alliance"]},
    "US_MILITARY": {"color": "#336699", "keywords": ["pentagon", "US military"]},
    "DEPLOYMENTS": {"color": "#669900", "keywords": ["deploy", "troops", "forces"]},
    "MOBILIZATION": {"color": "#CC6600", "keywords": ["mobiliz", "reserves"]},
    "EXERCISES": {"color": "#6699CC", "keywords": ["exercise", "drill", "maneuver"]},
    "AID": {"color": "#00CC66", "keywords": ["humanitarian", "aid", "relief"]},
    "TALKS": {"color": "#9966CC", "keywords": ["talks", "negotiation", "summit"]},
    "SANCTIONS": {"color": "#CC3366", "keywords": ["sanction", "embargo"]},
    "CEASEFIRE": {"color": "#66CC66", "keywords": ["ceasefire", "truce", "peace"]},
}
```

#### News Sources (RSS Feeds)
```python
MILITARY_NEWS_FEEDS = {
    "SHEPHARD": "https://www.shephardmedia.com/rss/",
    "DEFENSE_NEWS": "https://www.defensenews.com/rss/",
    "BBC_NEWS": "https://feeds.bbci.co.uk/news/world/rss.xml",
    "NAVAL_NEWS": "https://www.navalnews.com/rss/",
    "UN_NEWS": "https://news.un.org/feed/subscribe/en/news/all/rss.xml",
    "ALJAZEERA": "https://www.aljazeera.com/xml/rss/all.xml",
    "REUTERS": "https://www.reuters.com/world/rss",
    "JANES": "https://www.janes.com/rss/",
}
```

### Mod Commands
```bash
# Camera control
!cam1 beirut          # Set camera 1 to Beirut preset
!cam2 https://...     # Set camera 2 to custom URL
!cam3 off             # Disable camera 3
!cam4 tel_aviv        # Set camera 4 to Tel Aviv

# Layout control
!grid 4               # 4-camera grid (default)
!grid 2               # 2-camera split
!full 1               # Camera 1 fullscreen
!pip 1 2              # Picture-in-picture (cam1 main, cam2 corner)

# Ticker control
!ticker on            # Enable ticker
!ticker off           # Disable ticker
!ticker filter NAVAL  # Filter to NAVAL category only
!ticker all           # Show all categories
!alert "Breaking news text"  # Manual alert injection
```

### Integration with antifaFM
- Use during political events, protests, breaking news
- Mods can quickly switch to multi-cam view during crisis
- Return to music mode with `!karaoke` or `!video`
- Ticker runs alongside music (optional)

### Technical Approach

#### Option A: OBS Scene-Based (Recommended)
- Pre-configure OBS scenes with VLC media sources
- WebSocket commands switch sources by URL
- Lower latency, better stability
- Works with existing OBS infrastructure

#### Option B: FFmpeg Composition
- FFmpeg filter_complex for grid composition
- More flexible but higher CPU usage
- Can run independently of OBS

#### Option C: Hybrid
- OBS for display, Python for feed management
- Best of both worlds

### Viewer Voting Rotation (NEW - 2026-03-06)

Viewers can vote to rotate camera feeds democratically:

```bash
# Viewer commands (chat)
!rotate1        # Vote to rotate camera 1 to next preset
!rotate2        # Vote to rotate camera 2
!rotate3        # Vote to rotate camera 3
!rotate4        # Vote to rotate camera 4
!vote beirut 2  # Vote for specific preset on cam 2
```

**Voting Logic**:
- 51% of active chatters must vote within 60 seconds
- "Active" = sent message in last 5 minutes
- Mod override: `!force-rotate1 beirut` (instant, no vote)
- Cooldown: 5 minutes between successful rotations per camera

**Implementation**:
```python
class ViewerVotingManager:
    def __init__(self):
        self.active_voters = {}  # user_id -> last_message_time
        self.pending_votes = {}  # cam_id -> {preset: [voters]}
        self.cooldowns = {}      # cam_id -> last_rotation_time

    def process_vote(self, user_id: str, cam_id: int, preset: str = None):
        # Track vote, check threshold, execute rotation
        pass

    def get_active_voter_count(self) -> int:
        # Users who messaged in last 5 minutes
        pass

    def check_threshold(self, cam_id: int) -> bool:
        # 51% of active voters voted for this cam
        pass
```

### Cam Sentinel AI (Gemma Pattern Detection)

**Decision**: Use Gemma for fast pattern detection, NOT Qwen3.

| Task | Model | Why |
|------|-------|-----|
| "Is something happening?" | Gemma | Binary classification ~10ms |
| "Frame interest score" | Gemma | 0-1 float, pattern match |
| "Content description" | Qwen3 | Only if complex analysis needed |
| Vote tallying | None | Simple math, no LLM |

**Implementation**:
```python
class CamSentinelGemma:
    """Gemma-based pattern detection for live cam feeds."""

    def __init__(self, model_path: str = "E:/HoloIndex/models/gemma-3-270m-it-Q4_K_M.gguf"):
        self.llm = Llama(model_path=model_path, n_ctx=256, n_threads=2)

    def score_frame(self, frame_description: str) -> float:
        """Score frame interest 0-1. Fast binary classification."""
        prompt = f"Rate activity level 0-10: {frame_description[:100]}"
        result = self.llm(prompt, max_tokens=5)
        return float(result['choices'][0]['text'].strip()) / 10

    def detect_event(self, frame_description: str) -> bool:
        """Binary: Is something notable happening?"""
        prompt = f"Notable event? YES or NO: {frame_description[:100]}"
        result = self.llm(prompt, max_tokens=3)
        return "YES" in result['choices'][0]['text'].upper()
```

**Auto-rotation based on interest**:
- Sentinel scores all 4 feeds every 30 seconds
- If one feed scores >0.7 and others <0.3, suggest rotation
- "🔴 CAM 3 (Beirut) shows activity - !rotate3 to switch"

### Tasks
- [ ] Create `src/multicam_controller.py` - Feed management
- [ ] Create `src/military_alerts_ticker.py` - Enhanced ticker
- [ ] Create `src/viewer_voting.py` - Democratic rotation (51% threshold)
- [ ] Create `src/cam_sentinel.py` - Gemma pattern detection
- [ ] Create `data/camera_presets.json` - Camera URL database
- [ ] Create `data/news_sources.json` - RSS feed config
- [ ] Add OBS scene collection for multi-cam layouts
- [ ] Implement mod commands (!cam1, !grid, !ticker)
- [ ] Implement viewer commands (!rotate1-4, !vote)
- [ ] Create alert category classification (keyword matching + AI)
- [ ] Build SQLite cache for headlines (avoid duplicates)
- [ ] Add source attribution display (colored badges)
- [ ] Create time-ago calculation for headlines
- [ ] Integrate Cam Sentinel with livechat for auto-suggestions

### Environment Variables
```bash
ANTIFAFM_MULTICAM=1              # Enable multi-camera mode
ANTIFAFM_TICKER_CATEGORIES=all   # all, or comma-separated list
ANTIFAFM_TICKER_SOURCES=all      # all, or comma-separated list
ANTIFAFM_TICKER_REFRESH=300      # Seconds between RSS fetches
```

### OBS Scene Structure
```
Scene Collection: antifaFM Multi-Live
├── Scene: 4-Cam Grid
│   ├── Camera 1 (VLC Source - top-left)
│   ├── Camera 2 (VLC Source - top-right)
│   ├── Camera 3 (VLC Source - bottom-left)
│   ├── Camera 4 (VLC Source - bottom-right)
│   ├── Category Bar (Browser Source)
│   └── Alert Ticker (Text Source)
├── Scene: 2-Cam Split
├── Scene: Fullscreen Cam
└── Scene: PIP Mode
```

### WSP Compliance
- WSP 77: Agent Coordination (feed manager → OBS → display)
- WSP 80: DAE Orchestration (multi-cam pipeline)
- WSP 91: Observability (feed health, ticker metrics)
- WSP 78: SQLite headline cache

---

## Future: Layer 7.5 - FFCPLN Lyrics Library

**Status**: COMPLETE (2026-03-05)

Manage 012's **238 original FFCPLN songs** with lyrics deduplication.

### Problem
- 238 songs on Suno playlist
- Many share identical lyrics (different styles/languages)
- LrcLib doesn't have original songs

### Solution: Lyrics Library CLI
```bash
# Add unique lyrics (paste from Suno):
python ffcpln_lyrics_library.py add --name "FFCPLN" --artist "UnDaoDu" --paste

# Map all variations to same lyrics:
python ffcpln_lyrics_library.py bulk-map --lyrics "FFCPLN" --paste

# Export to LRC files:
python ffcpln_lyrics_library.py export --all

# Import to karaoke cache:
python ffcpln_lyrics_library.py import-cache
```

### Features
- [x] SQLite storage (`ffcpln_lyrics_library.db`)
- [x] Lyrics deduplication (9:1 ratio achieved with FFCPLN)
- [x] Song → lyrics mapping (many-to-one)
- [x] Style/version tracking (v4.5, v5, drill, reggaeton)
- [x] Language support (en, es, ru, etc.)
- [x] Fuzzy song title matching
- [x] Estimated timing for LRC export
- [x] Bulk song mapping from paste
- [x] Stats command (unique lyrics, mapped songs, deduplication ratio)

### Current Status
```
Unique lyrics:  1 (FFCPLN)
Mapped songs:   9
Deduplication:  9:1 ratio
LRC files:      9 exported
```

### Files
- `scripts/ffcpln_lyrics_library.py` - Main CLI
- `data/ffcpln_lyrics_library.db` - SQLite database
- `data/lyrics_source/FFCPLN.txt` - Source lyrics files
- `data/lrc_files/` - Exported LRC files

---

## Architecture: Schema Modularization (2026-03-06)

**Status**: COMPLETE

**Problem**: As schemas grow (VIDEO_LOOP, KARAOKE, LIVECAM, NEWS_TICKER), the housing code becomes monolithic and unmaintainable.

**Solution**: Visual output schemas become sub-modules. External modules (games, AI news) remain separate with cross-references.

**Implementation**: `schemas/` directory created with 7 registered schemas. See [schemas/README.md](schemas/README.md).

### Existing Code (ALREADY BUILT)

| Component | Location | Status |
|-----------|----------|--------|
| **Games** | `modules/gamification/games/` | ✅ COMPLETE |
| ↳ game_manager.py | `games/src/game_manager.py` (14.9KB) | Chess, Checkers engines |
| ↳ OBS Assets | `games/assets/chess_board.html` | Browser sources |
| **News Ticker** | `antifafm_broadcaster/src/news_ticker.py` | ✅ Basic OBS ticker |
| **AI News Ticker** | `ai_overseer/skillz/agentic_news_ticker/` | ✅ AI-powered updates |
| **Karaoke** | `antifafm_broadcaster/src/karaoke_overlay.py` | ✅ STT + LRC |
| **Scheme Manager** | `antifafm_broadcaster/src/scheme_manager.py` | ✅ 6 schemas defined |

### Current State (Monolithic)
```
antifafm_broadcaster/
├── src/
│   ├── scheme_manager.py      # ALL schemas in one file (growing)
│   ├── karaoke_overlay.py     # Karaoke-specific (already separate)
│   ├── news_ticker.py         # Basic ticker (already separate)
│   └── ...
└── ROADMAP.md                 # ALL layers in one file (1000+ lines)

# External modules (stay where they are):
modules/gamification/games/           # Chess, Checkers
modules/ai_intelligence/ai_overseer/  # AI news ticker skill
```

### Target State (Modular)
```
antifafm_broadcaster/
├── schemas/                    # NEW: Visual output schema modules
│   ├── __init__.py
│   ├── base.py                 # BaseSchema interface
│   │
│   ├── video_loop/
│   │   ├── ROADMAP.md          # Sub-roadmap
│   │   ├── src/video_loop_schema.py
│   │   └── tests/
│   │
│   ├── karaoke/
│   │   ├── ROADMAP.md          # Sub-roadmap
│   │   ├── src/
│   │   │   ├── karaoke_schema.py
│   │   │   ├── lyrics_cache.py  # Move from scripts/launch.py
│   │   │   └── stt_bridge.py    # Move from suno_stt_lyrics_extractor.py
│   │   └── tests/
│   │
│   ├── livecam/
│   │   ├── ROADMAP.md          # Sub-roadmap (NEW)
│   │   ├── src/
│   │   │   ├── livecam_schema.py
│   │   │   ├── multicam_controller.py
│   │   │   ├── viewer_voting.py     # 51% threshold rotation
│   │   │   ├── cam_sentinel.py      # Gemma pattern detection
│   │   │   └── feed_discovery.py
│   │   └── tests/
│   │
│   └── news_ticker/
│       ├── ROADMAP.md          # Sub-roadmap
│       ├── src/
│       │   ├── ticker_schema.py
│       │   ├── military_alerts.py   # Enhanced RSS (Layer 7)
│       │   └── rss_aggregator.py
│       └── tests/
│
├── src/
│   ├── scheme_manager.py       # SLIM: Just imports & orchestrates
│   └── ...
│
└── ROADMAP.md                  # Main roadmap (imports schema roadmaps)

# Cross-Module Integration (stays external):
modules/gamification/games/                    # Games logic + OBS assets
  └── INTEGRATES via OBS Browser Sources
modules/ai_intelligence/ai_overseer/skillz/agentic_news_ticker/
  └── INTEGRATES via headlines.json
```

### Cross-Module Integration Points

| Schema | External Module | Integration Method |
|--------|-----------------|-------------------|
| GAMES | `gamification/games/` | OBS Browser Source + chat commands |
| NEWS_TICKER | `ai_overseer/skillz/agentic_news_ticker/` | `data/headlines.json` |
| LIVECAM | (new) | Direct FFmpeg/OBS sources |
| KARAOKE | (internal) | `lyrics_cache.db` |

### Base Schema Interface
```python
# schemas/base.py
from abc import ABC, abstractmethod
from enum import Enum

class BaseSchema(ABC):
    """Base class for all visual schemas."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Schema identifier (e.g., 'video_loop', 'karaoke')."""
        pass

    @abstractmethod
    def build_ffmpeg_filter(self, **kwargs) -> str:
        """Build FFmpeg filter_complex for this schema."""
        pass

    @abstractmethod
    def get_obs_sources(self) -> list:
        """Return list of OBS sources needed for this schema."""
        pass

    def get_chat_commands(self) -> dict:
        """Return dict of chat commands this schema handles."""
        return {}

    def get_roadmap_path(self) -> str:
        """Return path to schema's ROADMAP.md."""
        return f"schemas/{self.name}/ROADMAP.md"
```

### Schema Registration
```python
# schemas/__init__.py
from .video_loop.src.video_loop_schema import VideoLoopSchema
from .karaoke.src.karaoke_schema import KaraokeSchema
from .livecam.src.livecam_schema import LivecamSchema
from .news_ticker.src.ticker_schema import NewsTickerSchema

# NOTE: Games is external - modules/gamification/games/
# Integration via OBS Browser Source, not schema registry

SCHEMA_REGISTRY = {
    'video_loop': VideoLoopSchema,
    'karaoke': KaraokeSchema,
    'livecam': LivecamSchema,
    'news_ticker': NewsTickerSchema,
}

# External integrations (not in registry, but in OutputScheme enum)
EXTERNAL_INTEGRATIONS = {
    'games': 'modules/gamification/games/',  # OBS Browser Source integration
    'ai_news': 'modules/ai_intelligence/ai_overseer/skillz/agentic_news_ticker/',
}
```

### ROADMAP Concatenation
```python
# scripts/build_roadmap.py
"""Concatenate schema roadmaps into main ROADMAP.md"""

SCHEMA_DIRS = ['video_loop', 'karaoke', 'livecam', 'news_ticker']
# NOTE: games is external at modules/gamification/games/

def build_combined_roadmap():
    combined = open('ROADMAP_HEADER.md').read()
    for schema in SCHEMA_DIRS:
        path = f'schemas/{schema}/ROADMAP.md'
        if Path(path).exists():
            combined += f"\n\n---\n\n## Schema: {schema.upper()}\n\n"
            combined += open(path).read()
    # Add external module references
    combined += "\n\n---\n\n## External Integrations\n\n"
    combined += "- **Games**: See `modules/gamification/games/ROADMAP.md`\n"
    combined += "- **AI News**: See `modules/ai_intelligence/ai_overseer/skillz/agentic_news_ticker/`\n"
    with open('ROADMAP.md', 'w') as f:
        f.write(combined)
```

### Migration Plan

| Phase | Task | Status |
|-------|------|--------|
| 1 | Create `schemas/` directory structure | COMPLETE |
| 2 | Extract `BaseSchema` interface | COMPLETE |
| 3 | Migrate `video_loop` to module | COMPLETE |
| 4 | Migrate `karaoke` to module | COMPLETE |
| 5 | Create `livecam` module (new) | COMPLETE |
| 6 | Migrate `news_ticker` to module | COMPLETE |
| 7 | Create `waveform` and `spectrum` modules | COMPLETE |
| 8 | Create `entangled` module (0102 Bell state) | COMPLETE |
| 9 | Update `scheme_manager.py` to use modular imports | COMPLETE |
| 10 | Add cross-reference to `gamification/games/` | TODO |
| 11 | Create roadmap concatenation script | TODO |

### Benefits
1. **Focused Development**: Work on one schema without touching others
2. **Independent Testing**: Each schema has its own test suite
3. **Clear Ownership**: Schema-specific ROADMAP tracks progress
4. **Scalability**: Add new schemas without growing monolith
5. **AI Agent Friendly**: Agents can work on isolated schema modules

### WSP Compliance
- **WSP 3**: Module Organization (schemas as sub-modules)
- **WSP 49**: Module Structure (ROADMAP + src + tests per schema)
- **WSP 72**: Module Independence (schemas don't cross-depend)
- **WSP 22**: ModLog Updates (each schema has own log)

---

## Future: FoundUp MVP - White-Label Streaming Solution

**Status**: PLANNED (2026-03-06)

**Vision**: What we're building for antifaFM becomes a deployable FoundUp that ANY creator can use for their own 24/7 YouTube streaming setup.

### The Insight

antifaFM is the prototype. But the architecture we're building is generic:
- Video rotation with Ken Burns effects
- Karaoke mode with lyrics overlay
- Live camera grid with viewer voting
- News ticker with RSS aggregation
- Chat bot personas with AI engagement
- Games integration (chess, checkers via chat)

**Move2Japan**, **FoundUps**, or ANY YouTuber could deploy this same infrastructure for their channel.

### White-Label Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    FOUNDUPS STREAMING MVP                    │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │                  CONFIG LAYER                         │  │
│  │  config/                                              │  │
│  │  ├── channel.yaml    # YouTube channel settings       │  │
│  │  ├── branding.yaml   # Colors, logos, overlays       │  │
│  │  ├── schemas.yaml    # Enabled schemas               │  │
│  │  ├── personas.yaml   # Chat bot personalities        │  │
│  │  └── content.yaml    # Video library, audio sources  │  │
│  └──────────────────────────────────────────────────────┘  │
│                           │                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │                  SCHEMA MODULES                       │  │
│  │  (Selectable per deployment)                          │  │
│  │                                                       │  │
│  │  [VIDEO_LOOP] [KARAOKE] [LIVECAM] [NEWS] [GAMES]     │  │
│  │       ✓           ✓         ○         ○       ○       │  │
│  │                                                       │  │
│  │  ✓ = enabled for this deployment                      │  │
│  │  ○ = available but disabled                           │  │
│  └──────────────────────────────────────────────────────┘  │
│                           │                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │                  FOUNDUPS LAYER                       │  │
│  │                                                       │  │
│  │  - F_i token for this streaming FoundUp              │  │
│  │  - Streaming hours = Proof of Work                   │  │
│  │  - Viewer engagement = CABR score input              │  │
│  │  - Revenue sharing via pAVS tokenomics               │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Deployment Examples

| Creator | Channel | Schemas | Use Case |
|---------|---------|---------|----------|
| antifaFM | UCVSmg5aOhP4tnQ9KFUg97qA | All | Political radio + visuals |
| Move2Japan | UCSMWKx7v5X5RI1234567 | VIDEO_LOOP, KARAOKE | Tokyo ambience + J-pop |
| FoundUps | UC123456789 | VIDEO_LOOP, NEWS | pAVS updates + tech news |
| [Your Channel] | - | Customizable | Your 24/7 stream |

### Configuration System

```yaml
# config/channel.yaml
name: "My 24/7 Stream"
youtube_channel_id: "UC..."
stream_key_env: "MY_STREAM_KEY"  # .env variable name
timezone: "America/New_York"
max_duration_hours: 11  # YouTube 12hr limit

# config/branding.yaml
primary_color: "#FF0000"
secondary_color: "#000000"
logo_path: "assets/my_logo.png"
overlay_gif: "assets/my_pulse.gif"
font_family: "Arial Black"

# config/schemas.yaml
enabled:
  - video_loop
  - karaoke
disabled:
  - livecam
  - news_ticker
  - games
default_schema: video_loop

# config/personas.yaml
primary_persona: "my_channel_bot"
personas:
  my_channel_bot:
    voice: "friendly, informative"
    topics: ["music", "community"]
    response_style: "casual"

# config/content.yaml
audio_source: "https://my-icecast.com/stream"
video_library:
  source: "assets/videos/"
  scan_on_startup: true
lyrics_cache: "data/lyrics_cache.db"
```

### FoundUp Registration

Each streaming deployment becomes a registered FoundUp in pAVS:

```python
# modules/foundups/simulator/foundups/streaming_mvp.py

STREAMING_FOUNDUPS = {
    "antifafm_broadcaster": {
        "tier": "F0_DAE",  # Pre-OPO
        "proof_of_work": "streaming_hours",
        "metrics": {
            "uptime_hours": lambda: get_total_stream_hours(),
            "viewer_engagement": lambda: get_avg_concurrent_viewers(),
            "content_library_size": lambda: count_videos(),
        },
        "cabr_inputs": [
            "stream_health_score",  # FFmpeg stability
            "chat_engagement_rate",  # Messages per hour
            "schema_variety_usage",  # How many schemas used
        ]
    },
    "move2japan_stream": {
        "tier": "F0_DAE",
        # Same structure, different config
    }
}
```

### Proof of Work: Streaming Hours

```python
# Track streaming as PoW for F_i token distribution
class StreamingProofOfWork:
    """Convert streaming hours to FoundUp proof of work."""

    def __init__(self, foundup_id: str):
        self.foundup_id = foundup_id
        self.db = sqlite3.connect('streaming_pow.db')

    def record_session(self, start: datetime, end: datetime, health_score: float):
        """Record streaming session as PoW."""
        hours = (end - start).total_seconds() / 3600
        weighted_hours = hours * health_score  # Healthy streams worth more

        self.db.execute("""
            INSERT INTO streaming_pow (foundup_id, hours, weighted_hours, timestamp)
            VALUES (?, ?, ?, ?)
        """, (self.foundup_id, hours, weighted_hours, datetime.now()))

    def get_total_pow(self) -> float:
        """Get total PoW hours for this FoundUp."""
        result = self.db.execute("""
            SELECT SUM(weighted_hours) FROM streaming_pow WHERE foundup_id = ?
        """, (self.foundup_id,)).fetchone()
        return result[0] or 0.0
```

### MVP Feature Tiers

| Tier | Features | Target User |
|------|----------|-------------|
| **Free** | VIDEO_LOOP only, 1 persona | Hobbyist |
| **Starter** ($9.95/mo) | +KARAOKE, +NEWS_TICKER, 3 personas | Small creator |
| **Pro** ($19.95/mo) | All schemas, unlimited personas, priority support | Professional |
| **FoundUp** ($195/mo Angel) | Full source access, custom schemas, F_i tokens | Ecosystem builder |

### One-Click Deployment Target

```bash
# Future: Deploy your own streaming FoundUp
npx create-foundups-stream my-channel

# Prompts for:
# - YouTube channel ID
# - Audio source URL
# - Default schema
# - Branding preferences

# Outputs:
# - Configured docker-compose.yml
# - OBS scene collection
# - .env template
# - Streaming FoundUp registered in pAVS
```

### Tasks

| Phase | Task | Status |
|-------|------|--------|
| 1 | Abstract antifaFM-specific code to config | TODO |
| 2 | Create `config/` schema with YAML validation | TODO |
| 3 | Create `foundups/streaming_mvp.py` registration | TODO |
| 4 | Build StreamingProofOfWork tracker | TODO |
| 5 | Create deployment CLI (`create-foundups-stream`) | TODO |
| 6 | Docker compose template for one-click deploy | TODO |
| 7 | Documentation: "Deploy Your Own 24/7 Stream" | TODO |
| 8 | Test with Move2Japan as second deployment | TODO |

### Revenue Model Integration

```
Creator subscribes → Gets UPs in wallet
    → Stakes UPs in Streaming FoundUp
    → Streaming hours earn F_i tokens
    → F_i holders share in ecosystem value

Viewer engagement → Higher CABR score
    → Better UPS flow from Treasury
    → More F_i distributed to creator
```

### WSP Compliance
- **WSP 26**: FoundUPS DAE Tokenization (F_i for streaming)
- **WSP 29**: CABR Engine (streaming metrics as V2 inputs)
- **WSP 3**: Module Organization (config-driven deployment)
- **WSP 77**: Agent Coordination (personas per deployment)

---

## Future: Layer 8 - External Stream Engagement

**Status**: COMPLETE (2026-03-06) - Base implementation

Engage in ANY public YouTube Live stream chat, not just owned channels.

### The Problem

We can only use YouTube API for streams we OWN. For streams like:
- MIDDLE EAST MULTI-LIVE (https://www.youtube.com/watch?v=BXMH9yBck3w)
- Ally channels
- Community streams

We need DOM-based automation (Selenium) to participate in their chat.

### Solution: External Stream Chat Skill

**Location**: `modules/ai_intelligence/ai_overseer/skillz/external_stream_chat/`

```python
from ai_overseer.skillz.external_stream_chat import ExternalStreamChat

chat = ExternalStreamChat(url="https://www.youtube.com/watch?v=BXMH9yBck3w")
await chat.connect()
await chat.send_message("Hello from OpenClaw!")
await chat.party()  # Click hearts
```

### DOM Selectors (YouTube Live Chat)
```python
SELECTORS = {
    'chat_input': "#input.yt-live-chat-text-input-field-renderer",
    'chat_input_contenteditable': "div#input[contenteditable='true']",
    'send_button': "#send-button button",
    'heart_emoji': "[aria-label*='heart' i]",
}
```

### Pixel Offset Strategy

The heart/reaction button is typically **10-50 pixels LEFT** of the chat input:
```python
# Get chat input position
chat_box = driver.find_element("css selector", SELECTORS['chat_input'])
chat_rect = chat_box.rect

# Reaction panel is left of chat input
reaction_x = chat_rect['x'] - 40  # ~40px left
```

### CLI Integration

Available via OpenClaw menu:
```
Main Menu → 8 (OpenClaw) → 10 (External Stream Chat)
  → 1. Interactive Mode (!send, !party, !watch, !status)
  → 2. Quick Send (URL + message)
  → 3. Party Mode (click hearts)
  → 4. Watch Only
```

### Commands (Interactive Mode)
```bash
!send <message>   # Send message to chat
!party            # Click heart reaction
!watch <url>      # Switch to different stream
!status           # Show connection status
!quit             # Exit
```

### Features
- [x] Navigate to any YouTube Live URL
- [x] Auto-detect chat input (multiple selector fallbacks)
- [x] Send messages via DOM
- [x] `!party` command (heart clicks)
- [x] Pixel offset calculation for reaction buttons
- [x] Human behavior simulation (bezier curves, random delays)
- [x] CLI integration in OpenClaw menu
- [ ] Auto-respond to mentions
- [ ] Cross-stream persona management
- [ ] Message queue for multi-stream engagement

### Use Cases

1. **MIDDLE EAST MULTI-LIVE engagement** - Engage in geopolitical streams
2. **Ally support** - Participate in friendly creator streams
3. **Community building** - Be present in related communities
4. **Cross-promotion** - Mention foundups.com in relevant chats

### Integration with antifaFM

While streaming antifaFM, simultaneously engage in related streams:
```
antifaFM Stream (OBS)        External Stream Chat
      ↓                              ↓
 Broadcasting video           Chatting in ally streams
      ↓                              ↓
 OBS orchestration            OpenClaw engagement
```

### WSP Compliance
- **WSP 27**: DAE Architecture (sensor: chat messages, actuator: DOM clicks)
- **WSP 77**: Agent Coordination (OpenClaw skill integration)
- **WSP 91**: Observability (engagement telemetry)
