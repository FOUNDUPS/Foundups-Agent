# antifaFM Discord Voice Output Spec

**Status**: Canonical spec
**Owner**: 0102 (Worker Q)
**Slice**: `ANTIFAFM_DISCORD_VOICE_OUTPUT_SPEC_PHASE1`
**Date**: 2026-04-06
**Parent**: antifaFM Broadcaster module

---

## 1. Problem

antifaFM streams 24/7 radio from AzuraCast to YouTube Live via FFmpeg. The FOUNDUPS Discord server has no way to play this same stream in a voice channel. Off-the-shelf music bots (Jockie, Tempo, etc.) are either dead, unreliable, or opaque third-party failure modes.

The antifaFM broadcaster already owns the audio source, health monitoring, reconnect logic, and telemetry. Discord voice should be a sibling output lane — not a separate tool island.

**Architect call**: Same source URL, same monitoring/recovery domain, same operator ownership. No off-the-shelf bots.

---

## 2. Architecture Decision: Python (discord.py)

### Why Python

| Factor | Python (discord.py) | Node (@discordjs/voice) |
|--------|---------------------|------------------------|
| Existing ecosystem | Python-native codebase (3.12.2) | Minimal Node deps (firebase, vercel only) |
| Async model | asyncio — same as broadcaster | Separate event loop, separate process |
| FFmpeg | Already installed, used by broadcaster | Would need separate FFmpeg binding |
| Audio libs | torch, librosa, soundfile already installed | Would need new installs |
| Health monitor | `StreamHealthMonitor` directly importable | Would need IPC/HTTP bridge to Python monitor |
| Telemetry | Same JSONL writer, same `BroadcastTelemetry` dataclass | Would need adapter |
| Discord framework | None exists yet (webhooks only) | None exists yet |
| Voice support | discord.py 2.x + PyNaCl + FFmpeg | @discordjs/voice + sodium + FFmpeg |

**Decision**: Python. The broadcaster is Python. The health monitor is Python. The telemetry is Python. Adding a Node sidecar for one audio pipe creates a cross-language coordination problem for zero benefit.

**Evidence status**: PROVEN (all existing infrastructure is Python, Node has no audio or Discord dependencies installed).

### Library Choice: discord.py 2.x

- `discord.py>=2.3.0` — maintained, async, voice support via `discord.VoiceClient`
- `PyNaCl>=1.5.0` — required for Discord voice encryption (libsodium binding)
- FFmpeg — already installed (system dependency of broadcaster)

Alternative considered: `py-cord` (fork of discord.py). Rejected — discord.py 2.x is actively maintained and has the larger ecosystem. No feature gap for this use case.

---

## 3. Runtime Model: Can the Broadcaster Host Discord Voice?

### 3.1 Current Runtime

```
AntifaFMBroadcaster.start()
  → FFmpegStreamer.start()      ← spawns FFmpeg subprocess
  → StreamHealthMonitor.start() ← asyncio task (check every 30s)
  → _heartbeat_loop()           ← asyncio task (telemetry every 30s)
```

All runs in one Python process, one asyncio event loop.

### 3.2 Discord Voice Client Runtime

```
discord.Client (bot)
  → bot.connect_to_voice()
    → VoiceClient ← manages UDP + WebSocket to Discord voice gateway
      → FFmpegOpusAudio(url) ← spawns FFmpeg subprocess reading Icecast
```

discord.py runs its own event loop via `bot.run()` or `await bot.start()`.

### 3.3 Can They Share a Process?

**YES, with caveats.**

Both are asyncio-native. The discord.py bot can be started as an asyncio task alongside the broadcaster's heartbeat and health monitor:

```python
# In the broadcaster orchestrator:
discord_output = DiscordVoiceOutput(bot_token, channel_id, stream_url)
youtube_output = FFmpegStreamer(config)

# Both run as tasks in the same event loop
await asyncio.gather(
    youtube_output_lifecycle(),
    discord_output.start(),
    health_monitor.start(),
    heartbeat_loop(),
)
```

**Caveats**:
1. **discord.py blocks on `bot.run()`** — must use `await bot.start()` (non-blocking) instead
2. **Voice gateway is UDP** — latency-sensitive, but the Icecast source adds ~2-5s buffer anyway, so sub-second jitter from shared event loop is acceptable
3. **Crash isolation** — if the Discord bot raises an unhandled exception, it must NOT kill the YouTube stream. Each output needs its own try/except boundary.
4. **Independent lifecycle** — Discord output should start/stop independently of YouTube output. YouTube being down should not affect Discord voice. Discord token being invalid should not prevent YouTube streaming.

### 3.4 Decision: Shared Process, Independent Lifecycles

The Discord voice output runs in the same asyncio event loop as the broadcaster but has its own:
- Start/stop methods
- Health monitor instance (same `StreamHealthMonitor` class, different callbacks)
- Telemetry stream
- Error handling boundary

**Evidence status**: PROVEN (discord.py 2.x supports `await bot.start()` for embedded use).

---

## 4. Component Design

### 4.1 File: `discord_voice_output.py`

```python
class DiscordVoiceOutput:
    """
    Discord voice channel output adapter for antifaFM.

    Sibling to FFmpegStreamer — reads the same Icecast source,
    outputs to a Discord voice channel instead of YouTube RTMPS.

    Uses the same StreamHealthMonitor for reconnect/recovery.
    """

    def __init__(
        self,
        bot_token: str,           # ANTIFAFM_DISCORD_BOT_TOKEN
        guild_id: int,            # ANTIFAFM_DISCORD_GUILD_ID
        channel_id: int,          # ANTIFAFM_DISCORD_VOICE_CHANNEL_ID
        stream_url: str,          # Same Icecast URL as YouTube output
    ): ...

    async def start(self) -> bool:
        """Connect bot, join voice channel, start playing Icecast stream."""

    async def stop(self) -> bool:
        """Stop playback, disconnect from voice, close bot."""

    def is_healthy(self) -> bool:
        """Health check: bot connected AND voice playing AND not stalled."""

    async def _restart(self) -> bool:
        """Reconnect to voice and restart FFmpeg audio source."""

    def get_status(self) -> dict:
        """Status dict matching broadcaster telemetry format."""
```

### 4.2 Audio Pipeline

```
Icecast MP3 stream (192kbps)
  → FFmpegOpusAudio (discord.py built-in)
    → Reads HTTP stream via FFmpeg subprocess
    → Transcodes to Opus (Discord's required codec)
    → Pipes to VoiceClient
      → Encrypted UDP to Discord voice gateway
        → Users hear radio in voice channel
```

discord.py's `FFmpegOpusAudio.from_probe(url)` handles this natively. No custom audio processing needed.

```python
# Core playback — this is the entire audio pipe
source = discord.FFmpegOpusAudio(
    self.stream_url,
    before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
)
voice_client.play(source, after=self._on_playback_error)
```

The `-reconnect` flags tell FFmpeg to auto-reconnect to the Icecast source on network drops — same resilience model as the YouTube output.

### 4.3 Health Model

Reuses `StreamHealthMonitor` with Discord-specific callbacks:

```python
self.health_monitor = StreamHealthMonitor(
    check_fn=self._check_discord_health,
    restart_fn=self._restart_discord,
    config=RecoveryConfig(
        initial_delay=5.0,
        max_delay=120.0,          # Lower than YouTube (300s) — Discord reconnects faster
        backoff_multiplier=2.0,
        max_consecutive_failures=8,  # Higher than YouTube (5) — Discord is more flaky
        health_check_interval=15.0,  # More frequent than YouTube (30s) — voice drops are time-sensitive
    ),
)
```

**Health check signals**:
1. `bot.is_ready()` — bot connected to Discord gateway
2. `voice_client.is_connected()` — voice WebSocket alive
3. `voice_client.is_playing()` — audio source active (not paused, not errored)

All three must be True for healthy. Any False triggers recovery.

### 4.4 Reconnect Scenarios

| Failure | Detection | Recovery |
|---------|-----------|----------|
| Icecast source drops | `voice_client.is_playing()` returns False, `after` callback fires with error | Restart FFmpegOpusAudio with same URL |
| Discord voice gateway drops | `voice_client.is_connected()` returns False | Reconnect to voice channel, restart audio |
| Bot disconnected (kicked, network) | `bot.is_ready()` returns False | Full reconnect cycle (bot → voice → audio) |
| Channel deleted/permissions revoked | `on_voice_state_update` event | Log error, enter FAILED state, notify operator |
| Rate limited by Discord | 429 response | Respect `retry_after`, backoff naturally handled |

### 4.5 Environment Variables

```bash
# Required
ANTIFAFM_DISCORD_BOT_TOKEN=           # Bot token (from Discord Developer Portal)
ANTIFAFM_DISCORD_GUILD_ID=            # FOUNDUPS server ID
ANTIFAFM_DISCORD_VOICE_CHANNEL_ID=    # Target voice channel ID

# Optional
ANTIFAFM_DISCORD_VOICE_ENABLED=false  # Master switch (default off until configured)
ANTIFAFM_DISCORD_VOICE_VOLUME=1.0     # 0.0-2.0 (PCMVolumeTransformer, optional)
```

**Stream URL is NOT duplicated** — uses the same `ANTIFAFM_STREAM_URL` as the YouTube output.

---

## 5. Integration into Broadcaster

### 5.1 Orchestrator Changes

`antifafm_broadcaster.py` becomes the **multi-output orchestrator**. Minimal changes:

```python
class AntifaFMBroadcaster(SkillTriggerMixin):
    def __init__(self, enable_ai_monitoring=True):
        # ... existing YouTube config ...

        # Discord voice output (optional, independent lifecycle)
        self.discord_output: Optional[DiscordVoiceOutput] = None
        if _env_truthy("ANTIFAFM_DISCORD_VOICE_ENABLED"):
            self._init_discord_output()

    def _init_discord_output(self):
        """Initialize Discord voice output if configured."""
        bot_token = os.getenv("ANTIFAFM_DISCORD_BOT_TOKEN", "")
        guild_id = os.getenv("ANTIFAFM_DISCORD_GUILD_ID", "")
        channel_id = os.getenv("ANTIFAFM_DISCORD_VOICE_CHANNEL_ID", "")

        if not all([bot_token, guild_id, channel_id]):
            logger.warning("[DISCORD] Missing config — need BOT_TOKEN, GUILD_ID, VOICE_CHANNEL_ID")
            return

        self.discord_output = DiscordVoiceOutput(
            bot_token=bot_token,
            guild_id=int(guild_id),
            channel_id=int(channel_id),
            stream_url=self.stream_url,  # Same Icecast source
        )

    async def start(self) -> bool:
        # ... existing YouTube start logic ...

        # Start Discord output independently (failure does NOT block YouTube)
        if self.discord_output:
            try:
                await self.discord_output.start()
            except Exception as e:
                logger.error(f"[DISCORD] Failed to start voice output: {e}")
                # YouTube continues regardless

    async def stop(self) -> bool:
        # ... existing YouTube stop logic ...

        if self.discord_output:
            try:
                await self.discord_output.stop()
            except Exception as e:
                logger.error(f"[DISCORD] Failed to stop voice output: {e}")

    def get_status(self) -> dict:
        status = {
            # ... existing fields ...
            "discord_voice": self.discord_output.get_status() if self.discord_output else None,
        }
        return status
```

### 5.2 Boundary Rule

> YouTube output failing MUST NOT affect Discord voice.
> Discord output failing MUST NOT affect YouTube stream.
> Each output has its own health monitor, its own restart logic, its own error boundary.

This is the sibling adapter contract. The orchestrator starts/stops both, but they are crash-isolated.

### 5.3 Telemetry

Discord output writes to the same JSONL telemetry path with a `"output": "discord_voice"` field to distinguish from YouTube entries:

```json
{
    "timestamp": "2026-04-06T12:00:00.000000",
    "output": "discord_voice",
    "status": "playing",
    "uptime_seconds": 3600.0,
    "stream_url": "https://a12.asurahosting.com/listen/antifafm/radio.mp3",
    "restart_count": 1,
    "health_state": "healthy",
    "guild_id": "123456789",
    "channel_id": "987654321",
    "error_message": null
}
```

---

## 6. Single-Channel vs Multi-Channel

### 6.1 Phase 1: Single Channel

One bot instance → one voice channel → one stream. This is the correct starting point.

The operator sets `ANTIFAFM_DISCORD_VOICE_CHANNEL_ID` to the target channel (e.g., `#antifafm-radio`). The bot joins that channel on start and stays there.

### 6.2 Future: Multi-Channel

Not in scope for Phase 1. If needed later:
- One `VoiceClient` per channel (discord.py supports this per guild)
- Each channel gets its own `StreamHealthMonitor`
- Config becomes a list: `ANTIFAFM_DISCORD_VOICE_CHANNELS=id1,id2,id3`
- Each channel could potentially play a different AzuraCast mount point

### 6.3 Decision

**Phase 1: Single channel only.** Multi-channel adds complexity with no current demand.

---

## 7. Operator Controls

### 7.1 CLI Integration

Add to existing CLI YouTube menu (option 10 submenu) or create dedicated option:

```
antifaFM Broadcaster
  1. Start YouTube stream
  2. Stop YouTube stream
  3. Start Discord voice       ← NEW
  4. Stop Discord voice        ← NEW
  5. Start both                ← NEW
  6. Stop both                 ← NEW
  7. Status (all outputs)
  8. View telemetry
```

### 7.2 Discord Slash Commands (Future, Not Phase 1)

Once the bot is in the server, it could respond to:
- `/radio join` — join the user's current voice channel
- `/radio leave` — disconnect
- `/radio status` — show stream health
- `/radio nowplaying` — query AzuraCast `/api/nowplaying`

These are NOT Phase 1. Phase 1 is headless — bot auto-joins configured channel on start.

---

## 8. Platform Risk and TOS

### 8.1 Discord TOS

Discord's Terms of Service and Developer Policy allow bots to:
- Play audio in voice channels (this is a core bot capability)
- Stream from external URLs via FFmpeg (standard music bot pattern)
- Run 24/7 in voice channels (no duration limits like YouTube's 12-hour cap)

No TOS violations identified.

### 8.2 Operational Brittleness

Discord voice is **more brittle** than YouTube RTMPS:

| Factor | YouTube RTMPS | Discord Voice |
|--------|--------------|---------------|
| Protocol | TCP (reliable) | UDP (lossy) |
| Duration limit | 12 hours | None (but gateway resets happen) |
| Reconnect latency | ~5-10s | ~2-5s (faster, but more frequent) |
| Server-side kicks | Rare | Voice gateway resets every ~4-12 hours |
| Rate limits | Generous | Strict (1 reconnect per 15s) |
| Network sensitivity | Tolerant (TCP retransmit) | Sensitive (UDP packet loss = audio glitches) |

**Mitigation**: Higher `max_consecutive_failures` (8 vs 5), more frequent health checks (15s vs 30s), lower max backoff (120s vs 300s).

### 8.3 Bot Token Security

The bot token is a credential. Same WSP 64 rules as the YouTube stream key:
- Stored in `.env` only
- Never logged, never committed
- `ANTIFAFM_DISCORD_BOT_TOKEN` — not a shared bot, dedicated to antifaFM

### 8.4 Bot Permissions Required

Minimum Discord permissions for voice playback:
- `Connect` — join voice channels
- `Speak` — transmit audio
- `View Channels` — see the target channel

No message permissions needed (Phase 1 is headless — no text commands).

**Permission integer**: `3145728` (Connect + Speak + View Channels)

---

## 9. Dependencies

### 9.1 New Python Dependencies

Add to `modules/platform_integration/antifafm_broadcaster/requirements.txt`:

```
discord.py>=2.3.0    # Discord bot + voice support
PyNaCl>=1.5.0        # Voice encryption (libsodium)
```

### 9.2 System Dependencies

- **FFmpeg** — already installed (broadcaster system requirement)
- **libopus** — discord.py auto-detects; bundled on Windows, `apt install libopus0` on Linux

### 9.3 No Root requirements.txt Changes

These are module-local dependencies. The broadcaster's own `requirements.txt` already lists `psutil>=5.9.0` as a module-local dep. Adding `discord.py` and `PyNaCl` follows the same pattern.

---

## 10. Discord Bot Setup Prerequisites

Before implementation, the operator (012) must:

1. **Create a Discord Application** at https://discord.com/developers/applications
2. **Create a Bot** within the application
3. **Copy the bot token** → set as `ANTIFAFM_DISCORD_BOT_TOKEN` in `.env`
4. **Enable these Privileged Gateway Intents**: None required (voice doesn't need Message Content, Members, or Presence intents)
5. **Invite the bot** to the FOUNDUPS server with permission integer `3145728`
6. **Create a voice channel** (e.g., `#antifafm-radio`) and note its ID → set as `ANTIFAFM_DISCORD_VOICE_CHANNEL_ID`
7. **Note the server ID** → set as `ANTIFAFM_DISCORD_GUILD_ID`

---

## 11. Current Repo State

| Component | Status | Evidence |
|-----------|--------|----------|
| AntifaFMBroadcaster | LIVE | `src/antifafm_broadcaster.py` — 586 lines, async lifecycle |
| FFmpegStreamer | LIVE | `src/ffmpeg_streamer.py` — 890 lines, YouTube RTMPS output |
| StreamHealthMonitor | LIVE | `src/stream_health_monitor.py` — 274 lines, generic callbacks |
| OBS Controller | LIVE | `src/obs_controller.py` — alt YouTube output |
| Discord voice output | DOES NOT EXIST | This spec defines it |
| Discord bot framework | DOES NOT EXIST | Only webhook-based (moltbot_bridge) |
| PyNaCl / discord.py | NOT INSTALLED | Need to add to requirements.txt |

---

## 12. Implementation Order

### Layer 1 — Bot Skeleton + Voice Join
- Create `discord_voice_output.py`
- Bot connects to Discord gateway
- Joins configured voice channel
- No audio yet — just prove connection lifecycle works
- Test: bot appears in voice channel, can be stopped cleanly

### Layer 2 — Audio Playback
- Add `FFmpegOpusAudio` playback from Icecast URL
- `-reconnect` flags for source resilience
- Test: radio plays in voice channel
- Test: manually kill Icecast → FFmpeg reconnects → audio resumes

### Layer 3 — Health Monitor Integration
- Wire `StreamHealthMonitor` with Discord-specific check/restart callbacks
- Exponential backoff on voice disconnects
- Test: force disconnect bot → health monitor restarts it
- Test: 5+ consecutive failures → FAILED state, stops retrying

### Layer 4 — Orchestrator Integration
- Wire into `AntifaFMBroadcaster` as optional output
- Independent start/stop lifecycle
- Combined status reporting
- Telemetry with `"output": "discord_voice"` field
- Test: start both outputs → kill Discord → YouTube unaffected
- Test: start both outputs → kill YouTube → Discord unaffected

### Layer 5 — CLI Integration
- Add Discord voice options to broadcaster CLI menu
- Start/stop/status commands

Each layer is tested independently. Each layer is a single PR.

---

## 13. Non-Goals

- No slash commands (Phase 1 is headless)
- No multi-channel support
- No Now Playing metadata display in Discord (future)
- No text channel integration (no chat commands)
- No music queue / playlist management (this is radio, not a jukebox)
- No Node.js components
- No off-the-shelf bot dependencies

---

*Inspected current broadcaster architecture (antifafm_broadcaster.py, ffmpeg_streamer.py, stream_health_monitor.py). Confirmed StreamHealthMonitor is generic (callback-based). Confirmed discord.py 2.x supports embedded async operation. Confirmed no existing Discord bot framework. Designed sibling output adapter with crash isolation and shared health model.*
