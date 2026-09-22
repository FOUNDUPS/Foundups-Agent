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
limits a request. Negative values are rejected. It returns a
JSON receipt and a nonzero exit on failure. Preview reports `planned` and
`total_planned`; `scheduled=[]` and `total_scheduled=0`. With `--video-ids`,
inventory pagination collects the exact batch before edits and preserves
requested order within each visibility pass. Preview scans that entire batch,
without persisting tracker changes or
running postcycle audit/autoheal. Preflight success proves transport only.
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
