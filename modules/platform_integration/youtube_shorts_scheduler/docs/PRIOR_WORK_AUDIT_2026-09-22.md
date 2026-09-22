# Prior Work audit and recent-clips contract

## Existing owner

The prior ChatGPT Work task is [Update Mosh Pit Skill](https://chatgpt.com/c/6ab0e7a1-7cfc-83ea-9b20-9f8b968dda3d).
Its September 21 completion message reports 21 Move2Japan Shorts scheduled and
verified by video ID and intended publishing time. Reported slots were:

- September 21: 19:00, 21:00, 23:00 JST.
- September 22 and 23: 08:00 through 22:00 JST, every two hours.
- September 24: 08:00 and 10:00 JST.

These are historical Work receipts, not a fresh Studio verification in this
local task. The earlier local audit's 13-row inventory is stale and must not
be replayed as a new scheduling request.

The [0102 Moshpit](https://docs.google.com/document/d/1kkexJx9YEsV5Jr5rWDovr9Oo7XhyhGUQavYC892iirE/edit)
names the reusable prototype:

- Branch: `feat/move2japan-daily-clips-skill-20260921`.
- Path: `modules/platform_integration/youtube_shorts_scheduler/skillz/publish_daily_clips/`.
- Channel: `UC-LSSlOZwpGIRIYihaz8zCw` (Move2Japan).
- Scope: owner API identity/inventory enrichment, Shorts/unlisted selection,
  neutral metadata defaults, Save persistence, final inventory audit/retry,
  and Red Dog daily-clips aliases.
- Promotion: prototype. Its subprocess command plane is plan-only until the
  live owner API plus Studio apply/readback adapter is validated.

At this audit, local refs, GitHub branch lookup and PR lookup did not expose
that branch. The Work UI lists publication as pending. Source export is needed
before claiming a code-level audit or porting its implementation. Do not build
a second daily-clips skill from this description.

## Lessons to retain

Fifteen morning clips appeared on September 20 in Studio's GMT-7 view, while
six evening clips appeared on September 21. Use timezone-aware source evidence
in Asia/Tokyo; the displayed calendar date alone is insufficient.

Eight apparent saves were missing on the first inventory readback. Work
reported that an initial click could only focus Save. Its repair requires
the actual Save control to settle disabled and non-busy, followed by an
independent video-ID-and-slot readback. Retry only missing or mismatched IDs;
a click or subprocess success is not a completed schedule.

The adjacent [YouTube Archive Files](https://chatgpt.com/c/6ab13da3-fec8-83ea-890b-cacde2ce29ae)
task reports a separate local commit `b297eb5f` on
`codex/video-training-index-orchestration`. Bulk indexing/training, RSI runtime
changes, and the separate YouTube operator command-plane PR #1759 belong to
their existing owners. This scheduling repair must not absorb those branches.

## Required enhancement to the existing prototype

012's current command is **schedule clips**. Unless otherwise specified:

1. Freeze request time and Asia/Tokyo source day when the request is accepted.
2. Select every unlisted Short uploaded within the last 60 minutes, clipped
   to the start of that Japan day. An explicit 30-minute window or other day
   overrides the corresponding default. Resolve the window before queuing so
   a delayed worker or midnight crossing cannot widen or shift it.
3. Verify owner/channel identity and use exact timestamp evidence. Upload
   time is not proof of filming time; label the evidence accurately.
4. Exclude published, private, scheduled and previously verified IDs. Never
   fill an empty recent window with older unlisted backlog. Missing timestamp
   or incomplete inventory is unresolved evidence, not permission to expand.
5. Freeze selected IDs, source timestamps and ordering. Include all matches:
   three means three, eight means eight; no default clip-count cap. Publishing
   spacing remains a separate setting.
6. Use the existing transcript/index evidence and neutral metadata path.
   Japanese comes first for these Japanese clips; a faithful English summary
   may follow. Topic/location hashtags must match each clip. Missing evidence
   must remain visible rather than being filled from a campaign template.
7. Preserve the prototype's Save-settlement and final ID/slot readback,
   idempotent retries, and promotion boundary.

Required tests when the source arrives: a recent batch larger than one page;
empty window with an old backlog; 30-minute override; Japan midnight and a
GMT-7 Studio display; missing timestamps; scheduled-ID exclusion; duplicated
inventory rows; delayed dispatch retaining its original window; partial Save
failure with retry limited to missing IDs; exact channel mismatch.

## Local repair boundary

The isolated scheduling worktree contains fixes to the existing CLI/adapter,
nonpersistent preview, exact-ID selection and batch transcript language.
It does not register a replacement `youtube-remote-scheduling` publisher.
Until `publish_daily_clips` can supply its verified selection, an unqualified
remote scheduling CLI request returns `clip_selection_required` before any
browser connection. The continuous DAE's internal queue behavior is unchanged.

One-shot execution does not require `main.py`. The local transport probe
reported Chrome/9222 unavailable; the cloud Work browser is a different
execution environment. Live autonomous scheduling from this local task is
not verified. No YouTube content was changed during this audit.
