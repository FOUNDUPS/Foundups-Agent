# Remote scheduling through Red Dog

The existing route is `youtube_automation_adapter` -> scheduler CLI ->
`YouTubeShortsScheduler.run_scheduling_cycle()` -> Studio DOM controls.
One-shot execution does not require `python main.py`. An unattended remote
request still needs an awake, reachable host and an authenticated browser.
Move2Japan uses Chrome debug port 9222; extension access or a cloud Work
browser does not prove that this local transport is available.

## Reuse prior Work

Read the [prior Work audit](PRIOR_WORK_AUDIT_2026-09-22.md) first. Work already
created `publish_daily_clips` and reported 21 verified schedules. Its branch
was not available locally or on GitHub during this audit. Retrieve it before
extending discovery; no replacement publishing skill is registered here.

The required default is every unlisted Short from the last 60 minutes within
the current Japan day, with explicit time/day overrides. Freeze that window
at request acceptance, exclude scheduled IDs and never select old backlog
as a fallback. The Work prototype's source export and recent-window enhancement
remain pending. Unqualified CLI preview/apply returns `clip_selection_required`.

## Available commands

Transport preflight (no browser launch, authentication or publication):

```text
youtube action scheduling channel=move2japan preflight=true
```

Equivalent standalone command:

```powershell
python -m modules.platform_integration.youtube_shorts_scheduler.cli --channel move2japan --preflight
```

Given a verified batch, substitute its real IDs for these examples:

```text
youtube action scheduling channel=move2japan video_ids=abcdefghijk,lmnopqrstuv dry_run=true preserve_metadata=true
```

The same selected-ID request with `dry_run=false` invokes existing scheduling.
`max_videos=0` is the default and includes the entire selection; a positive
limit is optional. Publication spacing is independent of batch size. The
legacy slot allocator does not implement a custom deadline or Japanese
exposure plan. `preserve_metadata=true` retains prepared factual metadata;
the legacy templates are not transcript-grounded generation.

## Implemented repair

- Correct async constructor/method calls and registry-selected browser.
- Transport-only readiness and JSON failure receipts through Red Dog.
- Nonpersistent tracker preview, no preview autoheal, and shared-browser detach.
- Exact-ID selection across Studio pages, requested order per visibility,
  stalled-page detection, and explicit unresolved IDs for partial batches.
- No default clip-count cap and no unqualified remote backlog execution.
- Batch Japanese/auto transcription reusing the existing STT, with reported
  language and original chunk offsets retained by the audio analyzer.

## Evidence boundary

`preflight` success proves only transport. The actual local probe reported
`browser_unavailable` for Move2Japan/9222; authentication and live scheduling
were not established. No YouTube mutation occurred in this local task.

Offline tests prove interface and selection behavior, not saved schedules.
The existing scheduler receipt is not an independent readback. It explicitly
returns `scheduling_verified=false`; non-preview responses say
`verification_status=independent_readback_required`. `total_scheduled` is the
legacy scheduler's reported count, not a verified final inventory. Before enabling
unattended apply, retain Work's settled-Save check plus final video-ID-and-slot
inventory verification and retries limited to missing/mismatched results.
A natural-language acknowledgement is not a queued or completed job.

Generated-metadata manifest application, the existing Work source export,
recent-window integration, resident dispatch and live apply/readback validation
remain outstanding. The generic DAE queue remains separate from this remote
selected-batch command. Bulk indexing and RSI changes are outside this branch.

For source context see [the historical remote audit](REMOTE_AUDIT_2026-09-21.md)
and [the YUMORI source review](YUMORI_SOURCE_CONTEXT_2026-09-21.md).
