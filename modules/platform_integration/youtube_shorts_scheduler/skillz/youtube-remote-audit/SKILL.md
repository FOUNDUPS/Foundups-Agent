---
name: youtube-remote-audit
description: Inspect the existing FoundUps YouTube DAE, check remote readiness, and inventory specified clips without changing YouTube metadata, visibility, playlists, or schedules. Use for YouTube DAE discovery and read-only remote preflight.
---

# YouTube remote audit

Reuse the existing YouTube DAE, scheduler, indexer, and control routes. This
is a diagnostic skill, not a publisher or replacement system. This
module-local instruction file does not register a WRE executor or install
a personal Codex skill.

## Recover the implementation

First read the [prior Work audit](../../docs/PRIOR_WORK_AUDIT_2026-09-22.md).
The existing `publish_daily_clips` prototype belongs to the Work branch named
there. Retrieve its source before creating a daily-clips workflow. Historical
scheduled receipts must not be reused as a new batch. For “schedule clips,”
the current default is every recent clip within the last hour and the current
Japan day; preserve explicit window overrides and never substitute backlog.

Apply WSP 00 and WSP 97. Record the working branch, HEAD, dirty-file boundary,
and main revision examined. Source on main is not proof of a running service.

Attempt the governed HoloIndex owner query. Preserve a failure verbatim and
use bounded lexical/source inspection under WSP_CORE's degraded-retrieval
rule. Route index repair to the existing governed maintenance owner; never
reindex inside the query or represent lexical results as semantic evidence.

Read the scheduler README, INTERFACE, ModLog, ROADMAP, tests/README and
tests/TestModLog. Verify callable definitions against callers. Existing owners:

| Responsibility | Repository-relative owner |
|---|---|
| Launcher | `main.py`, `modules/infrastructure/cli/src/youtube_menu.py` |
| Comment/index/schedule loop | `modules/communication/livechat/src/auto_moderator_dae.py` |
| Scheduler | `modules/platform_integration/youtube_shorts_scheduler/src/scheduler.py` |
| Rotation | `modules/platform_integration/youtube_shorts_scheduler/scripts/launch.py` |
| Agent ingress | `modules/communication/moltbot_bridge/src/youtube_automation_adapter.py` |
| Transcript/index evidence | `modules/ai_intelligence/video_indexer/` |
| Live content skill | `.agents/skills/youtube_dae/SKILL.md` |

The operator confirmed that “YouTube Day” was a speech-to-text rendering of
“YouTube DAE.” Retrieve the existing DAE; do not search for or create a
separate Day workflow.

## Separate access from readiness

Check host access, browser authentication, scheduler transport, runtime,
and command compatibility separately. An authenticated extension-controlled
Studio tab does not prove Selenium debug ports are available. A separate
cloud/Work session must prove access to the local host.

Do not launch main.py merely to inspect it: the DAE may engage with comments
and schedule uploads. Do not queue manifest commands unless the actual
watcher, allowlist, and acknowledgement contract are verified. A skill
describing a watcher is not proof that it exists.

Inspect dry-run and preview effects before invocation. The September 21
audit found obsolete legacy CLI calls and persistent tracker increments in
both scheduling dry-run and slot preview. Recheck against the current
revision before treating those paths as read-only.

The subsequent [remote repair](../../docs/REMOTE_SCHEDULING.md) updates the CLI,
makes tracker preview nonpersistent and adds a transport preflight. Use that
current runbook alongside the historical audit.

## Inventory with evidence

Confirm channel ID. Inspect Shorts and Videos when type is unknown. Record
video ID, Studio URL, existing title, duration, displayed upload date and
visibility. Keep pending, private, scheduled and unlisted items distinct.
Report the observed count; do not force an approximate requested count.
Record filter, pagination coverage and observation time.

Check matching `memory/video_index/{channel}/{video_id}.json` artifacts.
For transcripts, record source, language, coverage and uncertain passages.
A repeated title, description template, filename or `scheduler_stub` does
not establish spoken content. Do not generalize one sampled clip's caption
availability to the whole batch.

Factual summaries and faithful translations must reflect inspected content.
Leave proposed titles unset when clip-level evidence is missing. A project
brief alone does not verify a government decision date or a person's position.

For YUMORI context, reopen the [source review](../../docs/YUMORI_SOURCE_CONTEXT_2026-09-21.md)
and follow its links to current project masters and official records. Keep
verified facts, project proposals, modeled assumptions and missing evidence
distinct. Historical campaign wording and a title-only index are not current
clip evidence. Factual information and faithful translation are not automatically
political persuasion; assess the actual requested content and action.

Before Japanese transcription, verify language handling in the existing audio
path. The September 21 source review found forced English in FasterWhisperSTT
and a hard-coded English result label in AudioAnalyzer's video path. Do not
claim Japanese transcription merely because an index artifact was produced.

The subsequent repair propagates Japanese/automatic language through the
existing batch pipeline. Actual recognition quality and clip coverage still
require audio evidence; offline tests do not establish them.

## Deliver a receipt

Return implementation owners, revisions, readiness matrix, exact inventory,
transcript coverage, defects and missing proof. Distinguish source-supported
capability from a successfully exercised action. State changes and unresolved
work. Never report scheduled, published or transcribed without evidence.

Initial findings: [September 21 audit](../../docs/REMOTE_AUDIT_2026-09-21.md).

Reusable invocation:

> Apply WSP 00 and WSP 97. Audit the existing YouTube DAE for the specified
> channel and clip date. Compare the checkout with main, verify remote access
> and callable interfaces, and inventory matching clips using live read-only
> evidence. Report transcript coverage and runtime blockers. Preserve metadata,
> visibility, playlists and schedules. Reuse existing components.
