# antifaFM YouTube Live Broadcaster

Bridges antifaFM Icecast audio stream to YouTube Live via FFmpeg.

**YouTube Channel**: [antifaFM](https://www.youtube.com/channel/UCVSmg5aOhP4tnQ9KFUg97qA) (formerly ravingANTIFA - renamed to match antifaFM.com)

## Overview

This module streams the antifaFM radio station (https://antifaFM.com/radio.mp3) to the **antifaFM** YouTube channel, enabling 24/7 music broadcasting with visual overlay.

## Architecture

```
AzuraCast (antifaFM.com)
    |
    v
Icecast Stream (radio.mp3)
    |
    v
FFmpeg Bridge (this module)
    |
    v
YouTube Live (RTMP)
```

## Features

- **Layer 1 (MVP)**: Static image + audio streaming
- **Layer 2.5 (Occam's Animation)**: Zero-cost visual effects via FFmpeg filters
  - Ken Burns (zoompan) - creates movement from static image
  - Color Pulse (hue shift) - subtle color variation
  - GIF Overlay - animated logo in corner
  - Image Cycling - rotate through branded images
- **Auto-Recovery**: Exponential backoff restart on FFmpeg failures
- **Health Monitoring**: Continuous process health checks
- **Telemetry**: JSONL logging for observability (WSP 91)
- **AI Overseer Initialization Seam**: Optional object initialization only;
  error notification/alert delivery is not implemented

## Quick Start

1. Set environment variables:
```bash
export ANTIFAFM_YOUTUBE_STREAM_KEY=xxxx-xxxx-xxxx-xxxx
```

2. Run from CLI:
```
Main Menu -> YouTube DAEs -> 10. antifaFM Broadcaster
```

3. Or via Python:
```python
import asyncio
from modules.platform_integration.antifafm_broadcaster.src import AntifaFMBroadcaster

broadcaster = AntifaFMBroadcaster()
asyncio.run(broadcaster.start())
```

## Configuration

### Core Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTIFAFM_BROADCASTER_ENABLED` | `true` | Enable/disable broadcaster |
| `ANTIFAFM_STREAM_URL` | `https://antifaFM.com/radio.mp3` | Icecast stream URL |
| `ANTIFAFM_YOUTUBE_STREAM_KEY` | (required) | YouTube RTMP stream key |
| `ANTIFAFM_DEFAULT_VISUAL` | `assets/default_visual.png` | Static image overlay |
| `ANTIFAFM_HEARTBEAT_INTERVAL` | `30` | Health check interval (seconds) |
| `ANTIFAFM_LYRICS_DB` | `data/ffcpln_lyrics.db` | Explicit Suno STT SQLite path; tests must override to an isolated O: path |

### Optional Discord voice lane (sibling output)

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTIFAFM_DISCORD_VOICE_ENABLED` | unset / `false` | When truthy, starts Discord voice after YouTube lane is up |
| `ANTIFAFM_BOT` | — | Bot token (or `ANTIFAFM_DISCORD_BOT_TOKEN`) |
| `ANTIFAFM_DISCORD_GUILD_ID` | — | Discord server id |
| `ANTIFAFM_DISCORD_VOICE_CHANNEL_ID` | — | Voice channel id |
| `ANTIFAFM_DISCORD_VOICE_VOLUME` | `1.0` | FFmpeg `volume` filter gain (0.0–2.0); unity = no `-af` |

Requires `discord.py` and `PyNaCl` (see module `requirements.txt`). Discord start failure does not stop YouTube/OBS streaming.

#### Live Discord Voice Setup (FOUNDUPS Server — Verified 2026-04-09)

**Bot Authorization Status**: `antifaFM Radio` bot is authorized in the FOUNDUPS Discord server.

**Required Discord Permissions** (set via role or channel override):
| Permission | Required | Why |
|------------|----------|-----|
| Connect | Yes | Join the voice channel |
| Speak | Yes | Transmit FFmpeg→Opus audio |
| Use Voice Activity | Yes | Continuous audio without push-to-talk |

**Startup Sequence**:
1. YouTube/OBS lane starts first (primary output)
2. If `ANTIFAFM_DISCORD_VOICE_ENABLED=1` and token/guild/channel valid:
   - `DiscordVoiceOutput.start()` called after YouTube success
   - Bot connects to guild, joins voice channel, begins FFmpeg→Opus playback
   - Own `StreamHealthMonitor` instance with 15s check interval
3. Discord failure does NOT fail YouTube lane (isolated P1 output)

**Smoke Verification Runbook**:

```bash
# 1. Set env vars (example — use real snowflakes)
export ANTIFAFM_DISCORD_VOICE_ENABLED=1
export ANTIFAFM_BOT="<bot-token>"
export ANTIFAFM_DISCORD_GUILD_ID="<server-id>"
export ANTIFAFM_DISCORD_VOICE_CHANNEL_ID="<channel-id>"
export ANTIFAFM_YOUTUBE_STREAM_KEY="<stream-key>"

# 2. Launch broadcaster
python -c "
import asyncio
from modules.platform_integration.antifafm_broadcaster.src import AntifaFMBroadcaster
b = AntifaFMBroadcaster(enable_ai_monitoring=False)
asyncio.run(b.start())
"

# 3. Success indicators (in logs):
#    [DISCORD] Voice adapter ready (start deferred until YouTube lane is up)
#    [DISCORD] Voice output started in #<channel_id>
#
# 4. Verify in Discord: bot appears in voice channel, audio plays
```

**What Is Verified in Code** (no live run required):
- Env parsing and fail-closed on invalid snowflakes (`_parse_snowflake_env`)
- Adapter construction via `build_discord_voice_from_env()`
- Discord lane isolated from YouTube lane (failure doesn't cascade)
- Health monitor wiring with restart callback
- Volume filter applied via FFmpeg `-af volume=`

**What Requires Live Voice Channel Run**:
- Actual bot→guild→channel connection
- FFmpeg→Opus audio quality
- Reconnect behavior under network disruption
- Real health monitor recovery cycle

**Common Failure Modes**:
| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| "Guild not visible to bot" | Bot not in server or wrong guild ID | Re-invite bot; verify `ANTIFAFM_DISCORD_GUILD_ID` |
| "Voice channel not found" | Wrong channel ID or not a voice channel | Check `ANTIFAFM_DISCORD_VOICE_CHANNEL_ID` |
| "discord.py / PyNaCl not installed" | Missing dependencies | `pip install discord.py PyNaCl` |
| Bot joins but no audio | FFmpeg not in PATH or Icecast down | Check `ffmpeg -version`; test stream URL |
| Audio but low/loud | Volume misconfigured | Adjust `ANTIFAFM_DISCORD_VOICE_VOLUME` (0.0–2.0) |

**Boundary Clarity**:
- **Primary output**: YouTube Live (or OBS→YouTube)
- **Discord voice**: Optional sibling lane — same Icecast source, separate output
- This is NOT a full production validation — only the code path is verified
- Live VC testing remains manual until automated Discord test infrastructure exists

### OBS Mode Audio (ANTIFAFM_USE_OBS=1)

When using OBS mode, OBS handles streaming directly. You **must** configure an audio source in OBS:

**Audio Stream URL**: `https://a12.asurahosting.com/listen/antifafm/radio.mp3`

**OBS Setup**:
1. Sources → **+** → **Media Source**
2. Name: `antifaFM Radio`
3. Uncheck "Local File"
4. Input: `https://a12.asurahosting.com/listen/antifafm/radio.mp3`
5. Check "Restart playback when source becomes active"

**Audio Monitoring**: Right-click source → Advanced Audio Properties → Monitor: "Monitor and Output"

**If no audio**: The media source may need a restart. Via OBS WebSocket:
```python
client.trigger_media_input_action(name='antifaFM Radio', action='OBS_WEBSOCKET_MEDIA_INPUT_ACTION_RESTART')
```

### Layer 2.5: Visual Effects

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTIFAFM_FX_KEN_BURNS` | `true` | Slow zoom/pan animation |
| `ANTIFAFM_FX_COLOR_PULSE` | `true` | Subtle hue shift |
| `ANTIFAFM_FX_GIF_OVERLAY` | `true` | Animated logo overlay |
| `ANTIFAFM_FX_GIF_PATH` | (auto-detect) | Path to GIF file |
| `ANTIFAFM_FX_IMAGE_CYCLE` | `false` | Rotate background images |
| `ANTIFAFM_FX_IMAGE_DIR` | - | Directory for cycling images |

## FFmpeg Command

The core FFmpeg command:
```bash
ffmpeg -re -i https://antifaFM.com/radio.mp3 \
       -loop 1 -i assets/default_visual.png \
       -c:v libx264 -preset ultrafast -tune stillimage \
       -c:a aac -b:a 128k -ar 44100 \
       -f flv rtmp://a.rtmp.youtube.com/live2/{STREAM_KEY}
```

## Module Cube Patterns

This module reuses patterns from:
- `modules/communication/livechat/src/peertube_relay_handler.py` - FFmpeg subprocess
- `modules/communication/livechat/src/youtube_dae_heartbeat.py` - Heartbeat + telemetry
- `modules/communication/livechat/src/auto_moderator_dae.py` - DAE lifecycle

## WSP Compliance

- **WSP 27**: Universal DAE Architecture (4-phase lifecycle)
- **WSP 64**: Secure credential management (stream key via ENV)
- **WSP 77**: Agent Coordination (AI Overseer integration)
- **WSP 84**: Code Reuse (module cube patterns)
- **WSP 91**: DAEMON Observability (JSONL telemetry)

## Files

```
antifafm_broadcaster/
    README.md           # This file
    INTERFACE.md        # Public API specification
    ROADMAP.md          # Future phases (Layer 1 → 2.5 → 2 → 3 → 4)
    ModLog.md           # Change history
    requirements.txt    # Dependencies
    src/
        __init__.py
        antifafm_broadcaster.py   # Main DAE class
        ffmpeg_streamer.py        # FFmpeg subprocess management
        stream_health_monitor.py  # Auto-recovery system
        visual_effects.py         # Layer 2.5: FFmpeg filter builder
        scheme_manager.py         # Schema orchestration (uses modular schemas)
    schemas/                      # MODULAR SCHEMA ARCHITECTURE (V3.0)
        README.md                 # Schema system documentation
        __init__.py               # Schema registry + auto-import
        base.py                   # BaseSchema ABC
        video_loop/               # Background video rotation
        karaoke/                  # STT lyrics overlay
        livecam/                  # Multi-camera grid (Layer 7)
        news_ticker/              # RSS headline ticker
        entangled/                # Bell state 0102 visualization
        waveform/                 # Audio waveform
        spectrum/                 # Frequency spectrum
    assets/
        README.md                 # Asset guidelines
        default_visual.png        # Static image (auto-generated if missing)
        backgrounds/              # Layer 2.5: Image cycling library
        overlays/                 # Layer 2.5: Animated GIF overlays
    tests/
        (unit tests)
```

## Layer Architecture

| Layer | Description | Status | Cost |
|-------|-------------|--------|------|
| **1** | Static image + audio | COMPLETE | $0 |
| **2.5** | Zero-cost animation (FFmpeg filters) | IN PROGRESS | $0 |
| **2** | AzuraCast metadata → dynamic titles | PLANNED | $0 |
| **3** | Waveform visualization (showwaves) | PLANNED | $0 |
| **4** | AI-generated visuals (Veo3/Sora2) | FUTURE | $$$ |

**Occam's Principle**: Layer 2.5 provides 80% of visual impact at 0% of AI cost.

## Dependencies

- FFmpeg (system binary)
- Python: psutil (process monitoring)
