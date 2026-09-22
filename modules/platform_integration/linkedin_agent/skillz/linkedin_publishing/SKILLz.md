---
name: linkedin_publishing
description: Publish, schedule or maintain exact approved LinkedIn content on a verified profile, page or newsletter
version: 1.0.0
author: 0102
agents: [qwen]
intent_type: EXECUTION
promotion_state: prototype
category: workflow
evals: []
---
# LinkedIn publishing and scheduling

Read the [master routing contract](../../docs/LINKEDIN_ACTIVITY_ROUTING.md).
Reuse article targeting and `data/linkedin_publishing_map.json`; verify the live
author, entity ID and series. eSingularity.ai is the current public identity, but
a desired name is not evidence that a LinkedIn page has been renamed.

Inspect published history, drafts, scheduled queue and failed attempts first.
Choose one primary location; contextual excerpts/reposts need distinct approved
thoughts, not identical cross-posts. Verify exact content, links, native entity
mentions, source-grounded imagery and approval for the destination. Account
switching, public edits, deletes and new schedules are separate actions.

For scheduling, confirm exact date/time/timezone and inspect current configuration
and destination support; historic 1–3/day is not a quota or permission. Do not
create an external scheduler because the UI lacks scheduling. On supported
surfaces schedule once, then reopen the queue and read back content and timing.
For immediate publication inspect the rendered post/article and actual permalink.
Empty editor or API success alone is not proof. On ambiguous submission inspect
before retry. Record draft-saved, scheduled-verified and live-verified separately.

Maintenance audits link rot, stale claims/dates, naming, duplicate drafts and
formatting. Preserve originals; apply only approved changes and verify persistence.
Do not run git-to-social hooks or legacy posting helpers as a test. Work uses
the advertised browser; a separately authorized repo runtime requires complete
side-effect/approval checks first.
