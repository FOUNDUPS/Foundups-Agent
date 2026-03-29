# antifaFM Broadcaster - Interface Specification

## Public API

### AntifaFMBroadcaster

Main DAE class for streaming radio to YouTube Live.

```python
from modules.platform_integration.antifafm_broadcaster.src import AntifaFMBroadcaster

# Initialize
broadcaster = AntifaFMBroadcaster(enable_ai_monitoring: bool = True)

# Start broadcasting
await broadcaster.start() -> bool

# Stop broadcasting
await broadcaster.stop() -> bool

# Get status
broadcaster.get_status() -> dict
```

#### Status Dictionary

```python
{
    "status": "offline|starting|broadcasting|degraded|error|stopping",
    "enabled": bool,
    "uptime_seconds": float | None,
    "uptime_formatted": str | None,  # "HH:MM:SS"
    "stream_url": str,
    "visual_path": str,
    "stream_key_configured": bool,
    "streamer": {
        "state": "stopped|starting|streaming|error|stopping",
        "is_running": bool,
        "uptime_seconds": float | None,
        "audio_url": str,
        "error": str | None,
    },
    "health": {
        "state": "healthy|degraded|unhealthy|recovering|failed",
        "restart_count": int,
        "consecutive_failures": int,
        "last_check_time": float | None,
        "error_message": str | None,
    },
}
```

### FFmpegStreamer

Low-level FFmpeg subprocess management.

```python
from modules.platform_integration.antifafm_broadcaster.src import FFmpegStreamer, StreamConfig

# Configure
config = StreamConfig(
    audio_url="https://antifaFM.com/radio.mp3",
    visual_path="assets/default_visual.png",
    rtmp_url="rtmp://a.rtmp.youtube.com/live2",
    stream_key="xxxx-xxxx-xxxx-xxxx",
    audio_bitrate="128k",
    audio_rate=44100,
    video_preset="ultrafast",
)

# Initialize and start
streamer = FFmpegStreamer(config)
streamer.start() -> bool
streamer.stop(timeout: float = 10.0) -> bool
streamer.is_running() -> bool
streamer.get_uptime() -> float | None
streamer.get_status() -> dict
```

### StreamHealthMonitor

Auto-recovery system with exponential backoff.

```python
from modules.platform_integration.antifafm_broadcaster.src import (
    StreamHealthMonitor, RecoveryConfig
)

# Configure
config = RecoveryConfig(
    initial_delay=5.0,
    max_delay=300.0,
    backoff_multiplier=2.0,
    max_consecutive_failures=5,
    health_check_interval=30.0,
)

# Initialize with callbacks
monitor = StreamHealthMonitor(
    check_fn=lambda: streamer.is_running(),
    restart_fn=async_restart_function,
    config=config,
)

# Start/stop
await monitor.start()
await monitor.stop()
monitor.reset()

# Check state
monitor.is_healthy -> bool
monitor.needs_intervention -> bool
monitor.get_metrics() -> dict
```

### VisualEffectsBuilder (Layer 2.5)

Zero-cost animation using FFmpeg filters.

```python
from modules.platform_integration.antifafm_broadcaster.src import (
    VisualEffectsBuilder, VisualEffectsConfig,
    KenBurnsConfig, ColorPulseConfig, GifOverlayConfig
)

# Configure effects
config = VisualEffectsConfig(
    ken_burns=KenBurnsConfig(enabled=True, zoom_range=0.1, speed=0.05),
    color_pulse=ColorPulseConfig(enabled=True, hue_range=15.0, speed=0.1),
    gif_overlay=GifOverlayConfig(
        enabled=True,
        gif_path="assets/overlays/antifafm_pulse.gif",
        scale=150,
        position="bottom_right",
        margin=20,
    ),
)

# Build FFmpeg filter_complex
builder = VisualEffectsBuilder(config)
filter_complex = builder.build_filter_complex(base_input_index=1)
# Returns: "[1:v]zoompan=z='1.0+0.1*sin(t*0.05)'...;[kb]hue=h=sin(t*0.1)*15[colored];..."

# Get additional FFmpeg inputs (for GIF)
additional_inputs = builder.get_additional_inputs()
# Returns: ["-ignore_loop", "0", "-i", "assets/overlays/antifafm_pulse.gif"]

# Get output mapping
output_map = builder.get_output_map()
# Returns: ["-map", "[out]", "-map", "0:a"]

# Check status
builder.get_status() -> dict
```

## Environment Variables

### Core Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ANTIFAFM_YOUTUBE_STREAM_KEY` | **Yes** | - | YouTube RTMP stream key |
| `ANTIFAFM_BROADCASTER_ENABLED` | No | `true` | Enable/disable module |
| `ANTIFAFM_STREAM_URL` | No | `https://antifaFM.com/radio.mp3` | Icecast URL |
| `ANTIFAFM_DEFAULT_VISUAL` | No | `assets/default_visual.png` | Visual overlay |
| `ANTIFAFM_HEARTBEAT_INTERVAL` | No | `30` | Health check interval |
| `ANTIFAFM_TELEMETRY_PATH` | No | `telemetry.jsonl` | Telemetry output |

### Layer 2.5: Visual Effects

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ANTIFAFM_FX_KEN_BURNS` | No | `true` | Enable Ken Burns zoom/pan |
| `ANTIFAFM_FX_COLOR_PULSE` | No | `true` | Enable color pulse effect |
| `ANTIFAFM_FX_GIF_OVERLAY` | No | `true` | Enable GIF overlay |
| `ANTIFAFM_FX_GIF_PATH` | No | - | Path to animated GIF |
| `ANTIFAFM_FX_IMAGE_CYCLE` | No | `false` | Enable image cycling |
| `ANTIFAFM_FX_IMAGE_DIR` | No | - | Directory with cycling images |

## CLI Integration

Access via: `Main Menu -> YouTube DAEs -> 10. antifaFM Broadcaster`

Submenu options:
1. Start broadcast
2. Stop broadcast
3. Refresh status
4. View telemetry

## Telemetry Format (JSONL)

Each line is a JSON object:
```json
{
    "timestamp": "2026-02-25T10:30:00.000000",
    "status": "broadcasting",
    "uptime_seconds": 3600.5,
    "stream_url": "https://antifaFM.com/radio.mp3",
    "restart_count": 0,
    "health_state": "healthy",
    "error_message": null
}
```

## Error Handling

### FFmpegStreamerError

Raised when FFmpeg operations fail:
- FFmpeg not installed
- Stream key not configured
- Process failed to start
- Connection to RTMP server failed

### Recovery States

| State | Description | Action |
|-------|-------------|--------|
| `healthy` | Stream running normally | None |
| `degraded` | Minor issues detected | Monitor |
| `unhealthy` | Major issues, attempting recovery | Auto-restart |
| `recovering` | Restart in progress | Wait |
| `failed` | Max retries exceeded | Manual intervention |

## Modular Schema System (V3.0)

### Schema Registry

```python
from modules.platform_integration.antifafm_broadcaster.schemas import (
    SchemaType, get_schema, get_schema_by_name, list_schemas
)

# List all schemas and registration status
schemas = list_schemas()
# {'video_loop': True, 'karaoke': True, 'livecam': True, ...}

# Get schema class by enum
VideoLoopSchema = get_schema(SchemaType.VIDEO_LOOP)

# Get schema class by name
KaraokeSchema = get_schema_by_name("karaoke")
```

### Schema Types

| Type | Name | Status | Description |
|------|------|--------|-------------|
| `VIDEO_LOOP` | video_loop | COMPLETE | Background video with color pulse |
| `KARAOKE` | karaoke | COMPLETE | STT lyrics with beat-sync |
| `ENTANGLED` | entangled | COMPLETE | Bell state 0102 visualization |
| `WAVEFORM` | waveform | COMPLETE | Audio waveform |
| `SPECTRUM` | spectrum | COMPLETE | Frequency spectrum |
| `NEWS_TICKER` | news_ticker | PARTIAL | RSS headline ticker |
| `LIVECAM` | livecam | PLANNED | Multi-camera grid + CamSentinel |

### BaseSchema Interface

All schemas inherit from `BaseSchema`:

```python
from modules.platform_integration.antifafm_broadcaster.schemas.base import (
    BaseSchema, SchemaMode, SchemaConfig
)

class MySchema(BaseSchema):
    NAME = "my_schema"
    DISPLAY_NAME = "My Schema"
    MODE = SchemaMode.FFMPEG  # or OBS, HYBRID

    def build_ffmpeg_filter(self) -> str:
        """Build FFmpeg filter_complex string."""
        return "[1:v]scale=1920:1080[out]"
```

### SchemeManager Integration

```python
from modules.platform_integration.antifafm_broadcaster.src.scheme_manager import (
    SchemeManager, OutputScheme
)

manager = SchemeManager()
manager.set_scheme(OutputScheme.KARAOKE)
filter_str = manager.build_ffmpeg_filter()  # Uses modular schema

# Get modular schema instance directly
karaoke = manager.get_modular_schema("karaoke")
```

See [schemas/README.md](schemas/README.md) for full documentation.

## Boot Layer Rotator (OBS Schema Rotation)

Master schema rotation for OBS visual layers.

### CLI

```bash
# List schemas
python skillz/boot_layer_rotator/executor.py --list

# Start rotation daemon (10 min per schema)
python skillz/boot_layer_rotator/executor.py --daemon

# Skip to specific schema
python skillz/boot_layer_rotator/executor.py --skip-to video

# Pause/resume
python skillz/boot_layer_rotator/executor.py --override
python skillz/boot_layer_rotator/executor.py --clear
```

### Schemas

| Schema | Status | Description |
|--------|--------|-------------|
| `gcc` | BLOCKED | GCC shipping tracker (WAF blocks screenshots) |
| `video` | **WORKING** | Video rotation (France 24, Al Jazeera, etc.) |
| `news` | BLOCKED | Conflict maps (LiveUAMap blocks automation) |

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OBS_VIDEO_SOURCES` | `France 24,Al Jazeera,Telaviv,BBC Straits,DW News` | OBS video source names |
| `OBS_BROWSER_SOURCE` | `antifaFM Website` | Browser source for web content |
| `OBS_NEWS_MAP_SOURCE` | `News Map` | Image source for map screenshots |
| `OBS_WEBSOCKET_HOST` | `localhost` | OBS WebSocket host |
| `OBS_WEBSOCKET_PORT` | `4455` | OBS WebSocket port |
| `OBS_WEBSOCKET_PASSWORD` | (empty) | OBS WebSocket password |

### Rotation Timing

- **Schema duration**: 600 seconds (10 minutes)
- **Video rotation**: ~66 seconds per source (600s / N sources)
- **News rotation**: 60 seconds per map (if working)

## Dependencies

- **System**: FFmpeg binary (`ffmpeg` in PATH)
- **Python**: psutil (optional, for process monitoring)
- **OBS**: obsws-python (for boot layer rotator)
