---
name: youtube-presave-audit
description: Audit YouTube scheduling drafts for a meaningful title, description, audience selection and schedule before saving; identify metadata repair candidates without publishing them.
---

# Scheduling draft audit

Use the existing detail editor, `YouTubeStudioDOM.prepare_schedule_audit`, and
`video_policy.audit_schedule`. This module-local skill describes those owners;
its presence does not establish WRE registration, invocation or live qualification.

Bind the native receiving channel and exact video ID before reading or editing.
Read the existing scheduled inventory before allocating a slot. An incomplete
calendar read means unknown coverage, not an empty calendar. A list row does not
expose enough information to audit the full description and Audience: new
content-page scheduling now enters the detail owner and ends that row snapshot
after one candidate. The old inline Save refuses without a detail audit.

Before scheduling and again at Done/page Save, check:

- A nonempty title within 100 characters. Date-only, month-only, Untitled and
  Highlight Overview labels need content evidence; do not merely rename them
  with a channel template.
- A human-facing description within 5,000 characters. A provenance trailer
  alone or drafting preamble is insufficient.
- The native Audience controls are unambiguous and the expected radio is
  actually selected. Use the explicit native IDs in the runtime environment's
  `YT_MADE_FOR_KIDS_CHANNEL_IDS` / `YT_NOT_MADE_FOR_KIDS_CHANNEL_IDS`, or the
  registry's literal `shorts.made_for_kids` boolean. Us Story Time's native ID
  belongs in the Yes configuration; 012's non-kids channel IDs belong in No.
  No IDs or channel-name defaults belong in scheduling logic. Missing, malformed,
  duplicate or conflicting policy blocks. Configuration alone does not enable
  scheduling, comments or indexing on a new channel.
- A future, valid date/time with an explicit configured timezone. Ambiguous
  or nonexistent DST times block. This validates intent, not Studio's persisted
  timezone/slot, calendar completeness or the absence of restrictions.
- Fresh private directives, STOP/public automation gate, unchanged known draft,
  exact receiving identity and durable duplicate/unknown-save protection.

Reuse `index_weave.build_index_metadata_context` and
`content_generator.validated_video_evidence` to repair incomplete metadata.
Only a matched, retrieval-eligible existing analysis can supply new text.
Preserve-metadata and exact replacement directives still apply; if they leave an
incomplete draft, hold scheduling. Missing analysis goes to the existing
Studio Ask/Gemini indexing owner. Do not start a second browser/model client or
turn indexing into a publisher.

For the AntifaFM re-audit, prioritize date/generic titles and videos around three
minutes as candidates. Duration does not identify a song, establish music, or
prove channel identity. An artifact title is not current Studio readback. Keep
candidate IDs, evidence, proposed text and uncertain records in the existing
private work ledger; read current fields and resolve ownership before applying.
Do not retry a receiving video with an unknown save outcome.

If Audience is unreadable or Save is blocked, retain the diagnostic reason.
Use the existing UI-TARS observation owner only under its qualified runtime
boundary; its `execute_action('verify').description` echoes the request and is
not a visual diagnosis. An unqualified visual answer cannot authorize a radio
selection or Save. Record unavailable visual diagnosis for the existing repair
lane rather than declaring the audience correct. The broader browser-wide
manual-takeover hold remains separate work.

For “Verify it's you”, let 012 complete verification. The existing verification
guard cancels the pending action and yields at least 30 seconds, longer while the
challenge remains. Revalidate afterward; elapsed time is not clearance.

Only independently reopened, exact channel/video/title/description/audience and
schedule readback establishes application. A click, API acknowledgement or passed
offline test does not establish saved delivery.
