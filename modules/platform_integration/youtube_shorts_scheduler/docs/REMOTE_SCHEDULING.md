# Remote scheduling through Red Dog

**2026-10-22 scope:** current interface and tests qualify bounded source behavior.
The September source/Work observations below remain dated historical reports;
they do not establish present host authentication, publication or discovery.
Selected requests never run channel-wide tracker sync/autoheal; discovery is
bounded to 100 pages per visibility pass and wrong edit identity fails closed.

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
- Selected-batch audits cannot auto-repair unrelated channel schedules.
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


## Dual-surface scheduling practice — 2026-10-25

This is an operator training procedure for the two existing implementations,
not a new publisher, registered skill, model-training run or deployed agent.
The current remote CLI still enters the detail-page orchestrator. A successful
cloud-browser action does not qualify the local Chrome/9222 transport.

| Intent | Existing owner | UI completion boundary |
|---|---|---|
| Schedule only; preserve title, description and related video | `src/content_page_scheduler.py` / `ContentPageScheduler.schedule_video_from_row` | Content-row visibility popup's **Schedule/Save**, followed by independent saved-state readback |
| Edit authorized metadata and schedule | `src/scheduler.py` -> `src/dom_automation.py` | Visibility dialog **Done** stages changes; page **Save** persists them; read back saved state |
| Change an existing schedule when explicitly requested | `ContentPageScheduler.reschedule_row_inline` | Popup save and exact-ID/date/time readback; never infer permission from a conflict alone |

### Shared preparation

1. Confirm the intended channel, content tab and visibility filter. Freeze an
   explicit selected-ID batch. An inventory count is not a selection or proof
   that all rows belong to one topic. Do not select private or already-scheduled
   videos when the request is for unlisted videos only.
2. Record each video's ID from its edit link, original title, visibility and
   planned slot. Repeated titles are not identifiers. Refresh and reacquire rows
   after writes; a stale row position can point at a different video.
3. Check existing schedules and allocate collision-free slots in the requested
   audience timezone. Read the actual Studio timezone; do not assume the host
   timezone equals the channel timezone. Convert with an IANA timezone for the
   release date, including daylight-saving transitions.
4. Preserve metadata for schedule-only requests. A topic-specific hashtag such
   as `#ActonDef` applies only to matching videos. Do not spread one description
   across unrelated uploads. If metadata changes are requested, inspect each
   video's content; a reused title or template is not transcript evidence.

### Content table route

1. Stay on **Channel content** and locate the selected ID's row.
2. Open that row's visibility edit control. The observed Content UI exposes an
   unnamed edit-triangle button in the visibility cell; it may appear only after
   the cell is clicked/hovered. Clicking **Unlisted** alone can show a tooltip
   without opening the editor. Inspect the settled row and click its actual edit
   button. Scope actions to its inline popup, not a different row.
3. Expand **Schedule** and set the date and time in the displayed timezone.
4. Inspect the entered values, then use the popup's visible **Schedule/Save**
   action. Unlike the detail route, do not search for a second page-level Save.
5. Wait for the popup to settle and refresh the inventory if necessary. A video
   disappearing from the Unlisted filter is insufficient proof: find the same
   ID under scheduled content and verify date/time using its saved schedule
   tooltip or reopened popup, together with the timezone observed in the editor.

Source grounding: `ContentPageSelectors` scopes the popup to
`ytcp-video-visibility-edit-popup`; `schedule_video_from_row` runs visibility,
expand, date, time and popup-save steps. Its Boolean return proves that those
steps returned success, not an independent server readback. Never promote this
return value or a refreshed empty list to `scheduling_verified=true`.

### Video detail route

1. Open the selected row's edit link and verify the URL's video ID.
2. Change only metadata authorized for this clip, if any.
3. Click **Edit video visibility status**. In **Select video privacy**, expand
   **Schedule** using **Click to expand** when it is collapsed.
4. Set the date and time; inspect the displayed timezone and entered values.
5. Click **Done**, then the page-level **Save**. A local **Scheduled** label
   before Save is not sufficient evidence.
6. Wait for saved state (for example, **Changes saved** and disabled Save), then
   reopen visibility and read the exact persisted date, time and timezone.
   Do not re-save a matching result merely to verify it.

### Google verification at either surface

Use phone push only for 012; never ask for, retrieve or enter a Google password,
including through a secure credential form or a manual takeover instruction.
Follow the active browser's authentication mechanism. At Studio **Verify it's
you**, click **Next** once, allow the resulting challenge to settle, and inspect
it for number matching. Immediately write the exact observed number in chat:
**Google shows N. Press N on your phone, 012.** Never guess from phone choices,
reuse an old number, or assume the first phone Yes completes verification.
Wait for approval and the refreshed result before continuing. Do not resend
while a challenge is pending. If the challenge cannot be read, state that
limitation and offer supported manual takeover; stop automated interaction
until 012 reports completion. A sent prompt is not authenticated access, and
successful authentication is not a saved schedule.

### Live practice receipts and remaining qualification

The coordinating Work browser exercised both routes during an authorized
scheduling task. Detail-page readback used disabled page Save, reopened matching
schedule and **Changes saved**. Content-table readback used **Scheduled** in
the same video's row and its saved date/time tooltip after the popup's final
**Schedule** action. No outer Save was needed on the Content table.

This documentation worker received those observations through the coordinating
agent's handoff; it did not run a second browser verification. Private video IDs,
account inventory and individual release slots are intentionally retained in the
private task receipt rather than this repository. These observations establish
bounded UI practice, not local transport qualification, video playback,
transcription, backlog completion or a model-training run.

For each future practice result retain `channel_id`, `video_id`, `surface`,
`requested_slot`, `observed_slot`, `timezone`, metadata policy, saved-state
signal and verification status. Missing/mismatched readback remains unresolved;
retry only that ID after inspecting its current state. Compare both surfaces
on distinct authorized videos to avoid duplicate scheduling. Store successful
verified outcomes through the existing `schedule_dba.py` / WRE PatternMemory
owner when that integration is actually exercised; documentation alone is not
an ingested training event.
