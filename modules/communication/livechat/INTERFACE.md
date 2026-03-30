# LiveChat Module Interface

## Overview
The LiveChat module provides functionality to connect to a YouTube livestream chat, listen for messages, log them, and send responses. It integrates with other modules like BanterEngine for automated responses and token_manager for credential rotation. The module now includes QWEN intelligence for enhanced decision-making and pattern learning.

## Exports
This module exports:
- `LiveChatListener`: Class for connecting to and interacting with YouTube livestream chats
- `AutoModeratorDAE`: WSP-compliant DAE orchestrator with QWEN intelligence
- `QwenYouTubeIntegration`: QWEN intelligence layer for channel prioritization

## Classes

### `QwenYouTubeIntegration`
QWEN intelligence layer providing smart decision-making for YouTube DAE channel rotation.

#### Public Methods

##### `get_qwen_youtube()`
Returns singleton instance of QWEN YouTube intelligence.

**Returns:**
- `QwenYouTubeIntegration`: Singleton QWEN instance

##### `should_check_now() -> Tuple[bool, str]`
Global decision on whether to check any channels based on system health.

**Returns:**
- `bool`: Whether checking is recommended
- `str`: Reason for the decision

##### `prioritize_channels(channels: List[Tuple[str, str]]) -> List[Tuple[str, str, float]]`
Intelligently prioritize channel checking order based on patterns and heat levels.

**Parameters:**
- `channels`: List of (channel_id, channel_name) tuples

**Returns:**
- List of (channel_id, channel_name, priority_score) tuples sorted by priority

##### `record_stream_found(channel_id: str, channel_name: str, video_id: str)`
Record successful stream detection for pattern learning.

**Parameters:**
- `channel_id`: YouTube channel ID
- `channel_name`: Display name of channel
- `video_id`: ID of detected stream

### `AutoModeratorDAE`
WSP-compliant DAE orchestrator with integrated QWEN intelligence for stream detection and chat monitoring.

#### Features
- QWEN-powered channel prioritization
- Heat level management for 429 error prevention
- Pattern learning from successful detections
- Automatic social media posting orchestration
- Stream lifecycle management

### `LiveChatListener`
Connects to a YouTube livestream chat, listens for messages, logs them, and provides hooks for sending messages and AI interaction.

#### Constructor

##### `__init__(youtube_service, video_id, live_chat_id=None)`
Initializes a new LiveChatListener instance.

**Parameters:**
- `youtube_service`: Authenticated YouTube API service object
- `video_id`: ID of the YouTube video/livestream to connect to
- `live_chat_id`: Optional. If provided, uses this chat ID directly. Otherwise, it will be retrieved from the video details.

**Behavior:**
- Sets up the connection parameters with the provided YouTube service and video ID
- Initializes memory directory for chat logs
- Sets up trigger detection with BanterEngine
- Configures rate limiting for user interactions

#### Public Methods

##### `async start_listening()`
Starts the chat listener loop to poll for and process messages.

**Parameters:**
- None

**Returns:**
- None

**Behavior:**
- If not already running, retrieves the live chat ID if not provided
- Sends a greeting message if configured
- Enters a continuous polling loop to fetch and process messages
- Updates viewer count periodically to adjust polling intervals
- Processes and logs incoming messages
- Detects emoji triggers and responds with appropriate banter

##### `async send_chat_message(message_text)`
Sends a text message to the live chat.

**Parameters:**
- `message_text`: The text message to send to the chat

**Returns:**
- `bool`: True if message was sent successfully, False otherwise

**Behavior:**
- Truncates messages that exceed the maximum length
- Sends the message via the YouTube API
- Handles authentication errors with token rotation
- Returns success/failure status

## Usage Example
```python
import asyncio
from modules.livechat import LiveChatListener
from modules.youtube_auth import get_authenticated_service

async def main():
    # Get authenticated YouTube service
    youtube = get_authenticated_service()
    
    # Video ID of the livestream
    video_id = "YOUR_YOUTUBE_VIDEO_ID"
    
    # Create and start a listener
    listener = LiveChatListener(youtube, video_id)
    
    try:
        # Start listening for messages
        await listener.start_listening()
    except KeyboardInterrupt:
        print("Interrupted by user, shutting down...")
    except Exception as e:
        print(f"Error occurred: {e}")

# Run the async main function
if __name__ == "__main__":
    asyncio.run(main())
```

## Internal Methods
The class contains several internal methods not intended for direct public use:
- `_get_live_chat_id()`: Retrieves the liveChatId for the specified video_id
- `_update_viewer_count()`: Updates viewer count from livestream statistics
- `_poll_chat_messages()`: Polls the YouTube API for new chat messages
- `_process_message(message)`: Processes a single chat message and handles triggers
- `_log_to_user_file(message)`: Appends a log entry to a user-specific file
- `_is_rate_limited(user_id)`: Checks if a user is rate limited
- `_update_trigger_time(user_id)`: Updates the last trigger time for a user
- `_handle_auth_error(error)`: Handles authentication errors with token rotation

## FFCPLN Mining Commands (/fuc)

### Access Control
- **OWNER**: Full access to all /fuc commands
- **MANAGING_DIRECTORS**: Elevated MODs with owner-level /fuc access

```python
MANAGING_DIRECTORS = {
    'UCcnCiZV5ZPJ_cjF7RsWIZ0w',  # JS (Al-sq5ti) - Move2Japan Managing Director
}
```

### Command: /fuc status
Shows MAGAt balance for the user.

### Command: /fuc claim
Generates HMAC-secured claim link for pending MAGAts.

### Command: /fuc top
Displays MAGAts leaderboard (top 5 miners).

### Command: /fuc mine
Shows mining progress bar toward next MAGAt.

### Command: /fuc invite [@user]
Distributes invite code to user or self.

### Command: /fuc distribute
Auto-distributes invites to TOP 10 whackers (OWNER only).
- Random community presenter selection

### Command: /fuc stats
Shows invite distribution statistics.

---

## Dependencies
- googleapiclient.errors
- asyncio
- time
- datetime
- dotenv
- os
- logging
- modules.token_manager
- modules.banter_engine
- utils.throttling
- utils.oauth_manager

---

## YouTube Telemetry Store (Phase 2)

### `YouTubeTelemetryStore`
SQLite-based storage for YouTube DAE cardiovascular telemetry.

#### Public Methods

##### `record_channel_operation(channel_id: str, channel_name: str, operation: str, success: bool = True)`
Record operation timestamp for a channel (sentinel-queryable raw facts).

**Parameters:**
- `channel_id`: YouTube channel ID
- `channel_name`: Channel display name
- `operation`: Operation type (`comment_scan`, `shorts`, `indexing`, `rotation`)
- `success`: Whether operation succeeded

##### `get_stale_channels(operation: str, max_age_hours: int = 24) -> List[Dict]`
Find channels not processed within max_age_hours.

**Parameters:**
- `operation`: Operation type to check
- `max_age_hours`: Maximum age before channel is considered stale

**Returns:**
- List of dicts with `channel_id`, `channel_name`, `last_scan`, `hours_stale`, `consecutive_failures`

##### `get_channel_operation_stats(channel_id: str) -> Optional[Dict]`
Get all operation timestamps and failure count for a channel.

---

## Rotation Supervisor (Phase 2 + Phase 3)

### Constants

- `MAX_CYCLE_DURATION_HOURS`: Maximum cycle duration before emitting stall breadcrumb (env: `YT_MAX_CYCLE_DURATION_HOURS`, default: `2.0`)
- `ESCALATION_FAILURE_THRESHOLD`: Consecutive failure count triggering escalation breadcrumb (env: `YT_ESCALATION_FAILURE_THRESHOLD`, default: `3`)

### Watchdog Behavior (Phase 2 G5)

When rotation cycle exceeds `MAX_CYCLE_DURATION_HOURS`:
1. Emits `rotation_cycle_stalled` breadcrumb with metadata
2. Breaks out of rotation loop
3. AI Overseer can query breadcrumbs to detect and recover

### Escalation Behavior (Phase 3 G6)

When channel `consecutive_failures >= ESCALATION_FAILURE_THRESHOLD`:
1. Emits `human_intervention_required` breadcrumb with metadata
2. Includes channel_id, channel_name, failure count, threshold, operation
3. Does NOT modify telemetry store (read-only escalation check)

---

## STT/TTS Boundary Protocol (2026-03-30)

### AI Overseer Sentinel Layer

**Principle:** AI Overseer sentinels are OBSERVATIONAL, not AUTHORITATIVE.

```
SQLite (raw facts) → Sentinel Query (STT/observe) → Command Gate (TTS/act)
```

**Rules:**
1. **Raw Facts Only**: Telemetry stores timestamps and counts, NOT classifications
2. **Ephemeral Classifications**: Sentinel computes DEAD/ALIVE/WEAK at query time
3. **Authority Separation**:
   - STT (observe) → Can recommend actions
   - TTS (command) → Requires owner/mod approval
   - Rotation recovery → Autonomous (no user impact)
   - Moderation → NEVER autonomous (user impact)

### Audio STT/TTS Substrate

**Substrate Available:** STT/TTS provider registry and voice cloning policy now exist in `modules/infrastructure/shared_utilities/`:
- `audio_provider_registry.py` — provider metadata with production/eval-only gating
- `voice_cloning_policy.py` — consent + whitelist + kill switch enforcement
- `local_model_selection.py` — `asr` and `tts` role resolution

**Not Wired in LiveChat:**
- This module does NOT currently use STT for voice command input
- This module does NOT currently use TTS for audio output
- Any future STT integration is **observational only** until owner/mod command gates are explicitly wired
- Any future TTS voice cloning **must pass** `voice_cloning_policy.py` before synthesis

**Runtime Authority:**
- `openclaw_voice.py` (CLI) is the current STT/TTS runtime — uses legacy backends
- LiveChat remains text-only until explicit integration is approved and scoped

---

**WSP 11 Compliance:** Complete
**Last Updated:** 2026-03-30