# YouTube Shorts Scheduler - Interface Documentation

Remote requirements and current gaps: [remote runbook](docs/REMOTE_SCHEDULING.md).

## CLI Interface (Agent-Callable)

```bash
# Check the configured host transport
python -m modules.platform_integration.youtube_shorts_scheduler.cli --channel move2japan --preflight

# Schedule with limit
python -m modules.platform_integration.youtube_shorts_scheduler.cli --channel undaodu --video-ids abcdefghijk,lmnopqrstuv --max-videos 1 --preserve-metadata

# List available channels
python -m modules.platform_integration.youtube_shorts_scheduler.cli --list-channels

# Dry run (show what would be scheduled)
python -m modules.platform_integration.youtube_shorts_scheduler.cli --channel move2japan --video-ids abcdefghijk,lmnopqrstuv --dry-run --preserve-metadata
```

### CLI Arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--channel`, `-c` | str | required | Channel key: move2japan, undaodu, foundups |
| `--max-videos`, `-m` | int | 0 | Optional limit; 0 processes the entire batch |
| `--video-ids` | str | required for preview/apply | Comma-separated exact recording-batch IDs |
| `--list-channels` | flag | - | List available channels and exit |
| `--dry-run` | flag | - | Show what would be scheduled |
| `--preflight` | flag | - | Probe local browser transport only; no launch or scheduling |
| `--preserve-metadata` | flag | - | Retain existing titles/descriptions |
| `--browser`, `-b` | str | channel registry | Validate browser: chrome or edge |
| `--verbose`, `-v` | flag | - | Enable verbose logging |

The CLI defaults to `max_videos=0` (all clips); only an explicit positive value
limits a request. Negative or non-integer API limits are rejected. Attempts, including failed writes, consume the shared cross-visibility limit. It returns a
JSON receipt and a nonzero exit on failure. Preview reports `planned` and
`total_planned`; `scheduled=[]` and `total_scheduled=0`. With `--video-ids`,
inventory pagination collects the exact batch before edits (at most 100 pages per visibility pass) and preserves
requested order within each visibility pass. Preview scans that entire batch,
without persisting tracker changes or
running channel-wide sync or postcycle audit/autoheal. Simulated tracker state is discarded after each preview invocation. Preview connections disable DOM diagnostic screenshot writes; importing the DOM module does not create its diagnostics directory. These guarantees cover scheduler tracker and screenshot effects, not all optional telemetry or host logging. Preflight success proves transport only.
Use `--video-ids=...` when an ID starts with a hyphen. Empty or malformed
selections fail before connecting. Missing/failed IDs appear in
`unresolved_video_ids`; `batch_complete=false` makes the CLI return failure.
Without explicit IDs, the remote CLI returns `clip_selection_required` before
connecting; preflight/list-channels remain read-only exceptions. Automatic
recent discovery must extend the existing Work `publish_daily_clips` prototype.
Generated metadata manifests are not yet supported.
`main.py` is not required for this one-shot entry point.

---

## Public API

### YouTubeShortsScheduler

Main orchestrator class for scheduling automation. Current callable contract:

```python
scheduler = YouTubeShortsScheduler(channel_key="move2japan", storage_dir=None, dry_run=True)
if scheduler.connect_browser():
    try:
        result = await scheduler.run_scheduling_cycle(video_ids=recorded_clip_ids, update_metadata=False)
    finally:
        scheduler.disconnect()  # Leave the shared host browser running.
```

Both DAE and remote CLI default to `0 = unlimited`. Batch size is independent
of daily slot spacing. Internal dry-run rows retain the legacy `scheduled` key; the CLI
normalizes them to `planned`. `await preview_slots(count=10)` uses a nonpersistent
copy of the current tracker, including custom storage.

Legacy `channel=`/`driver=` constructor arguments and
`run_scheduling_workflow()` are not implemented. Use the current contract above.

### ChannelConfig

Channel configuration management.

```python
CHANNELS = {
    "move2japan": {
        "id": "UC-LSSlOZwpGIRIYihaz8zCw",
        "name": "Move2Japan",
        "timezone": "Asia/Tokyo",
        "time_slots": ["5:00 AM", "11:00 AM", "5:00 PM"]
    },
    "undaodu": {
        "id": "UCfHM9Fw9HD-NwiS0seD_oIA",
        "name": "UnDaoDu",
        "timezone": "Asia/Tokyo",
        "time_slots": ["5:00 AM", "11:00 AM", "5:00 PM"]
    },
    "foundups": {
        "id": "UCSNTUXjAgpd4sgWYP0xoJgw",
        "name": "FoundUps",
        "timezone": "America/New_York",
        "time_slots": ["9:00 AM", "3:00 PM", "9:00 PM"]
    }
}
```

### ScheduleTracker

Persistent schedule state management.

```python
class ScheduleTracker:
    def __init__(self, channel_id: str, storage_dir=None, *, persist: bool = True):
        """Load/create schedule state for channel."""

    def preview_copy(self):
        """Independent in-memory copy; no directories or tracker files written."""

    def get_count(self, date_str: str) -> int:
        """Get video count for a date."""

    def increment(self, date_str: str) -> None:
        """Record a scheduled video."""

    def save(self) -> None:
        """Persist to JSON."""
```

## Events

The scheduler emits events for monitoring:

- `schedule_started` - Workflow beginning
- `video_found` - Unlisted video discovered
- `video_scheduled` - Successfully scheduled
- `schedule_failed` - Scheduling error
- `schedule_completed` - Workflow finished

## Error Handling

```python
class SchedulerError(Exception):
    """Base scheduler error."""

class DOMError(SchedulerError):
    """Element not found or interaction failed."""

class AuthError(SchedulerError):
    """Not logged in or session expired."""

class QuotaError(SchedulerError):
    """Rate limited by YouTube."""
```

### Selected edit and receipt boundary (2026-10-22)

Before a selected clip is changed, its Studio edit URL and current visibility
must match the requested ID/pass. Failed metadata updates stop that clip.
`attempted_video_ids` records attempts; partial batches remain unsuccessful.
Preserve mode retains existing description-sync evidence. Metadata updates mark
sync unverified (`synced_to_youtube=false`, `independent_readback_required`);
this is lack of verification, not proof of absence on YouTube.
RedDog requires process success plus an explicit boolean success receipt, no
errors, and no incomplete-batch marker. Missing/malformed receipts fail closed.


## Evidence-bound metadata and learning (2026-10-25)

`src/content_generator.py::validated_video_evidence(index, video_id)` is an offline
identity/provenance gate, not a factual verifier. Metadata generation requires a
matching, retrieval-eligible existing artifact containing explicit Studio Ask,
Gemini video-summary, or timestamped YouTube/Whisper transcript evidence.
Missing/ineligible evidence preserves existing metadata; schedule-only mode
continues to bypass enrichment. No analyzer is launched by the scheduler.
`YT_SCHEDULER_INDEX_INFORM_TITLE` retains its existing opt-in. Description opt-out
preserves the complete description. Proposals reject platform-limit overflow.

`record_schedule_outcome` retains its Boolean storage return. A positive learning
outcome now additionally requires `details.requested_timezone` and independent
`details.readback` with matching `channel_id`, `video_id`, `date_str`, `time_str`,
`timezone` and `visibility="scheduled"`. Old callers remain recorded with
`reported_success=true`, but no verified success or positive fidelity score.
Audience performance is always marked unmeasured; no analytics/model promotion
is connected here.
