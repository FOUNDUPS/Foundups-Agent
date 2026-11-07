# LiveChat Module Interface

## Emoji question routing (2026-11-07)

`MessageProcessor.generate_response` routes permitted hand-emoji-plus-text
messages through `model_reply_request` and `_resolve_model_command`, preserving
the original text, captured author ID/role, receiving channel and stream title.
The existing bounded `_await_intelligent_reply` validates the exact reviewed
payload and theme; its returned carrier is not reformatted or prefixed here.
Question failure returns `None` without entering the legacy template path.
Existing rate/diversity and sender throttles remain in force. Exact whole-message
quiz answers (including variation selectors/skin modifiers) return their handler
result directly; bare emoji and explicit code-command handling stay separate.

## Capture before response selection (2026-11-07)

`LiveChatCore.process_message` calls the existing `_log_to_user_file` once for a
new received text-message ID, before schema handling, routing, filtering, command
throttling and reply generation. It retains author identity and USER/MOD/OWNER
role through ChatMemoryManager's immediate SQLite storage. Duplicate IDs retain
their previous in-memory suppression. Ban/timeout events keep their separate path.
No database schema or public posting policy changes. Existing storage-error and
cross-restart deduplication limitations remain; capture is not reply delivery.

The poller's available first batch retains text-bearing provider items with the
internal boolean `_capture_only=True`. Core captures these and returns before
schema actions, command processing and replies. Historical moderation events keep
their existing skip policy. This only preserves history supplied by the API;
it does not recover an entire missed stream or replay old commands/donations.

## Existing STOP owner: comments-quality scope (2026-11-05)

`automation_gates.stop_active()` retains its any-STOP behavior. Explicit
`stop_active('comments')` also sees every STOP; explicit `global`, `livechat`,
`scheduling`, `shorts` and `indexing` scopes permit only the recognized comments
incident exception. Invalid scopes fail closed. `gate_snapshot.stop_active` is
the global/manual decision; `comments_stop_active` and `comment_stop_status`
report the separate comment decision. Comment engagement/reply flags are masked
off while comments are stopped; other environment permissions are not enabled.

`latch_comment_quality_stop(reason)` accepts only `invalid_reply_text`,
`review_rejected` or `review_unavailable_or_invalid`. It exclusively creates the
existing STOP path under the existing runtime-operation lock, never overwriting
manual, newer or uncertain evidence. Its closed record has exactly `version=1`,
`kind='comment_reply_quality'`, `scope='comments'`, a 32-character lowercase-hex
`incident_id`, the recognized `reason`, and a finite positive
`recorded_at_unix` below `1e12`. Reads are bounded to 4 KiB; nonregular,
linked/reparse, malformed, changed or unreadable files fail closed globally.
`read_comment_quality_stop()` returns only a validated record, otherwise `None`;
use the gate snapshot to distinguish absence from a global/unknown STOP.

`clear_comment_quality_stop(expected_record)` requires the complete exact current
recognized record under the same owner lock and rechecks file identity/content.
It never clears manual/newer/unknown STOP or any delivery claim. This is a
cooperating-writer guarantee, not OS compare-and-swap against arbitrary manual
replacement. Successful clear describes the file gate only: first settle the
halted comment owners, then clear the matching incident and start fresh owners.
Existing DAE/coordinator parent receipts remain halted, including when exclusive
creation failed. No context command, expiry, restart loop or generic reset clears
them automatically.

`comment_stop_result()` supplies content-free typed halt evidence. The comments
CLI uses reserved exit `78` for that result, including failed persistence; both
subprocess readers and comments rotation honor it even without usable stdout.
Other rotation task types keep their existing exit semantics. Halts preserve
unfinished checkpoints and never publish comment/rotation completion evidence.
An active owned comment task must settle before a comments-halted inbox wait can
yield to live chat; that yield does not claim the inbox was cleared.

## Subprocess framing and cleanup evidence (2026-11-05)

`SubprocessRunner` reads stdout/stderr in fixed65,536-byte chunks. Physical
lines may contain at most65,536 bytes before LF; CR counts toward that cap.
Oversized lines are discarded through their delimiter or EOF, so their suffix
cannot become a separate JSON result. Subsequent valid lines and normal EOF
remain parseable; byte framing preserves UTF-8 split across chunks. Existing
first-JSON-result parsing and total retained-line-list policy are unchanged.

`_finish_subprocess` still awaits the owned direct child and every pipe reader.
A completed reader or queued-wait BaseException, including CancelledError,
becomes `RuntimeError("subprocess_cleanup_reader_or_wait_failed")` with no raw
cause. The existing coordinator retains that failed owner and refuses later
dispatch. Normal targeted caller cancellation and `_await_owned_completion`
keep their prior behavior. No unknown child is abandoned or family killed.

Content-free INFO phases are `LIVECHAT-HANDOFF` initialize/settling/polling and
`SUBPROCESS-CLEANUP` await_spawn/await_exit/process_exit_observed/readers_settled.
Direct-child exit is explicitly distinct from complete reader settlement. A
descendant retaining inherited pipe handles may still hold the await indefinitely;
phase evidence does not grant permission to drop that ownership. These codes
contain no chat text, identity, provider payload or credential.

## Shared YouTube model route (2026-11-01)

Assessment, writer and exact final review now call the shared AI Gateway.
Direct xAI and embedded local-provider fallback are retired for these consumers.
Ordinary and themed live chat share this reviewed path. NVIDIA's shadow proposer
remains evaluation-only; exact signed bindings govern dynamic production models.
See [routing/configuration and evidence limits](../video_comments/LLM_INTEGRATION.md).

Language-producing command adapters return a frozen private `ModelReplyRequest`
containing the original message, author identity/role and receiving-channel/stream
snapshot; construction performs no model call. The existing async
`MessageProcessor._resolve_model_command` consumes it through
`_await_intelligent_reply` with its bounded thread, cancellation token and exact
reviewed-payload checks. It rejects a changed receiving context before or after
the call. Raw request text is excluded from the descriptor representation.

## Confirmed live-session handoff (PR841)

`AutoModeratorDAE.terminate_comment_engagement(for_live_handoff=False)` keeps
full supervisor shutdown as its default. The explicit live-handoff path reserves
the successfully initialized API session's nonempty actual channel/chat identity,
settles matching comment operations, then starts polling. Social-only initialization,
pending stream hints and an environment fallback channel do not confirm a session.
Concurrent live sessions cannot replace the reservation; every exit clears it.

`MultiChannelCoordinator.settle_channel(channel_id)` and
`RotationSupervisor.settle_channel(channel_id)` operate on their existing owned
tasks. Both browser paths, pre-audit/fallback/retry dispatch and enabled rotation
consult the confirmed identity in addition to the advisory signal's 300-second
TTL. Rotation resolves registry names to channel IDs. Direct restart/inbox-clear
runner calls use the same coordinator ownership and canonical browser mapping.
Unrelated browser work remains owned and running. Deferred work is not reported
as processed/failed or completed in a rotation checkpoint.

`engagement_lifecycle.py` contains shared functions only; session identities and
task registries stay on the existing DAE/coordinator/rotation instances. Subprocess
cancellation recovers racing spawns, terminates then kills if necessary, and awaits
child exit and pipe readers. Thread cancellation/deadlines await actual worker
completion and may remain blocked indefinitely. Unknown/in-process runner modes
are not treated as preemptible; handoff awaits natural completion. Failed cleanup
retains ownership and blocks later handoff/dispatch rather than reporting settlement.
Default shutdown awaits browser children; heartbeat cleanup also runs if session
persistence fails.

This is bounded local source/lifecycle qualification. It does not establish global
browser quiescence, browser-side rollback, independently scheduled CommunityMonitor
settlement, live YouTube delivery, full installed-package readiness or native RSI.
The existing cross-browser singleton checkpoint can still race; no checkpoint
schema/store or timing configuration is added. Existing #848 indexing, #1759 watcher
and #782 quota contracts remain separate and intact.

## Overview
The LiveChat module provides functionality to connect to a YouTube livestream chat, listen for messages, log them, and send responses. It integrates with other modules like BanterEngine for automated responses and token_manager for credential rotation. The module now includes QWEN intelligence for enhanced decision-making and pattern learning.

## Exports
This module exports:
- `LiveChatListener`: Class for connecting to and interacting with YouTube livestream chats
- `AutoModeratorDAE`: WSP-compliant DAE orchestrator with QWEN intelligence
- `QwenYouTubeIntegration`: QWEN intelligence layer for channel prioritization

## Classes

## Operator command inbox (Phase 1)

`set_context` activates private behavioral guidance and records
`context_activated=true, public_message_sent=false`. Only `announce` sends the
operator's message publicly. Private activation needs no public sender and is
independent of STOP/send/announcement/dry-run gates. Those gates remain
authoritative at actual public writers.
`enqueue_operator_command(command, command_path=None, acknowledgement_path=None)`
appends under the existing queue ledger lock, preserving queued work and rejecting
reused IDs. Producers never write active state or acknowledgements.
Private video metadata/scheduling/Shorts policy uses that same inbox, lock,
acknowledgement ledger and state owner; see [the bounded policy contract](docs/VIDEO_POLICY_INTERFACE.md).
Spoken scope: “Live stream …” selects livechat; “Commenting …” selects comments;
“Push …” selects both; “Update the chat manifest with …” is private and honors
the stated scope (both when unstated). A public announcement requires explicit intent.

Themed livechat retains the existing Grok generation/review success path. On
unavailable, empty, failed or rejected output, it reuses the existing comment
generator with `reply_surface='livechat'` and supplied author, receiving channel
and stream identity. This fallback accepts only the general-role LM Studio HTTP
assessment/writer/reviewer; it cannot enter embedded inference, cloud retries or
templates. Livechat reads only its queue-owned theme; comments retain their
existing scoped and legacy readers. Generator caching includes channel and stream.
Malformed native themes fail normalization before either Grok or local inference;
the local receipt must match the qualified theme captured before generation.

The exact final `@mention` text must fit 200 characters before review; it is never
truncated afterward. `ReviewedLivechatReply` carries that text and a deep copy of
the full native theme to `ChatSender`, which rechecks after delay/conversion
immediately before the API request. Expiry, supersession or native metadata drift
blocks sending. Existing engagement and cooldown gates precede generation.

Both existing MessageProcessor call sites await threaded generation for at most
ten seconds and set a cancellation event on exit. Cancellation discards late
results and prevents subsequent provider stages/local fallback; it cannot kill
an active provider call. Livechat generation/review rejects a busy shared lock
immediately; comments keep serialized blocking access. The caller retains themed
mode across the await, so clearing a theme cannot enable unreviewed fallback.
Receipt, active context and observed wording remain distinct outcomes; API
acceptance alone is not delivery readback.

`OperatorCommandQueue` polls the trusted-local `memory/012_manifest.json` once
per minute. `AutoModeratorDAE.run()` owns and awaits its watcher on every exit.
Allowlisted actions: `status`, gated `announce`, private `set_context` /
`clear_context`, and private `set_video_policy` / `clear_video_policy`.
No arbitrary prompt, shell, browser or code execution exists.

`YT_012_MANIFEST_FILE`, `YT_012_MANIFEST_ACK_FILE` and
`YT_012_MANIFEST_STATE_FILE` override the three distinct paths. Relative paths
are rooted in the actual checkout, independent of process working directory.
`resolve_manifest_state_path()` is shared with the stored-comment reader.

The version-1 acknowledgement ledger claims each immutable ID and payload
digest **before** any effect. The existing runtime OS lock plus an in-process
guard serialize one canonical ledger. `unknown` outcomes (including crashes,
cancellation, timeouts and ambiguous sender results) are terminal and require
operator reconciliation; they are never automatically retried. Legacy terminal
receipts remain terminal. This is duplicate-attempt prevention, not exactly-once
delivery, authentication, or power-loss durability on every filesystem.

Only public `deferred` work may retry, using its persisted first-observation time.
Private video-policy reservations never retry an unknown/deferred outcome.
TTL defaults to 3,600 seconds; integer values 60–86,400 are accepted. Optional
finite `expires_at_unix` can shorten that deadline. Private context activates
without send gates; newer context/clear commands supersede older legacy pending
context. `clear_context` clears the shared
context, not legacy module-local broadcast configuration. Live-chat messages
are limited to 200 characters; comment-only context allows 500. Existing STOP,
automation, announcement, send and comment-engagement gates remain authoritative
at public writers. Live-chat announcement dry-run is `simulated` without calling
a sender; it does not disable private context activation.

Accepted sender results report `sender_accepted=true, delivery_verified=false`
and amber health. Local status/context acknowledgements can be green. Receipts
and optional heartbeat telemetry do not authenticate delivery. Malformed state
blocks the poll without resetting the ledger; the watcher retries later. Each
JSON file is bounded to 4 MiB and an inbox to 100 entries. Ledgers are not pruned
automatically: capacity requires supervised archival preserving replay history.
The sender deadline defaults to 30 seconds (maximum 300), relying on cooperative
async cancellation. See [the existing contract](docs/clarity/YOUTUBE_DAE_OPERATOR_COMMAND_PLANE_PHASE1.md)
for authority and validation limits.

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
