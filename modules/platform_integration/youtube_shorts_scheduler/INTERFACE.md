# YouTube Shorts Scheduler - Interface Documentation

## Qualified scheduled inventory

`YouTubeStudioDOM.read_scheduled_inventory(channel_id, *, max_pages=100) -> dict`
reads the current filtered list without account navigation or content changes.
`status` is `complete`, `partial` or `failed`; `total_scheduled` is an integer
only for a complete read, including a qualified empty result. Other fields are
`channel_id`, `channel_verified`, `filter_verified`, `start_verified`,
`pagination_complete`, `pages_read`, `rows_seen`, `rows_parsed`,
`observed_scheduled_count`, `videos`, `unparsed_rows` and `issues`.
Each qualified video includes exact `video_id`, displayed `date`/`time`, raw
`visibility_text`, raw `date_text`/`date_label`, and `schedule_source` equal to
`visibility_cell` or `schedule_labeled_date_cell`. A Date cell supplies a slot
only when its own text/aria-label/title explicitly says Scheduled, with no
Uploaded/Published contradiction. Unlabeled/upload dates never supply one. These are channel-local displayed wall
times, not an assertion of timezone or a verified publication write.

Native receiving ID (`ytcfg.get` or `yt.config_`, with conflicts refused) and exact Studio path must agree on every page. An actual
single Scheduled/Has schedule chip, no extra search/filter, an observed first
page and known final pagination state are required. Missing pagination controls,
repeated pages/IDs, invalid slots, changed channel/filter, parse failures or the
100-page bound retain partial observations and leave the total unknown.

`ContentPageScheduler.audit_calendar` adds `status`, `inventory`,
`observed_scheduled_count`, `observed_conflicts` and `observed_heavy_days`.
Partial reads have no automatic `conflicts`/`heavy_days` repair input and cannot
recommend a clean calendar. `ScheduleAuditor.run_audit` returns `healthy=None`
when incomplete, with no absence-based comparisons or tracker auto-heal.
`ScheduleTracker.sync_from_youtube(videos, *, inventory=None) -> bool` refuses
to reset state without a complete matching receipt, returning false unchanged.
`resolve_conflicts(..., *, inventory=None)` requires a complete receipt and every
supplied member/slot bound to it. `thin_schedule` requires matching complete
inventory, video list, channel config and tracker identity before any repair.
These read receipts establish observed inputs, not live write/readback authority.

Rotation binds canonical receiving IDs to scheduler/config/tracker/cache and
verifies native ID, Studio path and known permission before any writer. Unknown
or failed switches skip writers; fallback is deferred to its own canonical
entry. Unbound/incomplete zero caches are ignored. This is an additive receipt
and deliberate safety change for historical unqualified tracker-sync callers.

## Channel cadence

Omitted daily cap now resolves per channel: Move2Japan is eight/day at
08:00,10:00,12:00,14:00,16:00,18:00,20:00,22:00 America/New_York;
all other/unknown channels retain three/day. Explicit lower caps are preserved.
The global ET environment override does not override this explicit Move2Japan
policy. Its slots have no random jitter. Aggregate plan `cap: null` means
per-channel policy; each channel plan contains its resolved numeric cap.


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

Move2Japan cadence is not qualified for live reschedule apply: that legacy adapter
skips it with `cadence_live_unqualified` until independent timezone and occupied-slot
receipts exist. Allocation/planning rejects unknown Studio timezone or any slot
whose local date differs from its ET date (including Asia/Tokyo). This prevents
clock-only conversion from silently publishing on the wrong calendar date.
