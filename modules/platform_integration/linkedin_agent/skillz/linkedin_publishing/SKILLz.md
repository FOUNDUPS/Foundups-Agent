---
name: linkedin_publishing
description: Publish, schedule or maintain exact approved LinkedIn content on a verified profile, page or newsletter
version: 1.0.1
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

## Browser route — October 3, 2026

TinyFish is excluded from LinkedIn in this workflow after its hosted setup
browser displayed an access block. This is a project routing decision based on
the attempted session, not a claim of a universal vendor ban or a diagnosed
blocking mechanism. No TinyFish login retries, proxies, stealth profiles,
credential/vault use, cookie imports or alternate-host workarounds.

Use the established authorized browser instead. A PC-based worker must actually
reach the existing signed-in browser on that PC; GitHub access is not access to
its loopback debug port. Work must inspect its advertised browser and verify the
same intended account/page. If the runtime cannot reach an authorized session,
return `BLOCKED_BROWSER_ACCESS` and a handoff; do not silently create another
login dependency. Do not run both workers against one publishing transaction.

For other public research, [TinyFish has a separate bounded skill](../../../../infrastructure/browser_actions/skillz/tinyfish_research/SKILLz.md).
It does not grant LinkedIn publication authority.

## Publication contract

Inspect published history, drafts, scheduled queue and failed attempts first.
Choose one primary location; contextual excerpts/reposts need distinct approved
thoughts, not identical cross-posts. Verify exact content, links, native entity
mentions, source-grounded imagery and approval for the destination. Account
switching, public edits, deletes and new schedules are separate actions.

Preserve exact approved copy. A legacy helper's default company, signature or
hashtags must not override the requested publisher/text. A redirect, removed
`share=true` parameter, empty composer or helper Boolean is not publication proof.
Once either worker has attempted submission, reconcile that provider state before
any retry or handoff to another submitter; ambiguous delivery stays
`SUBMITTED_UNVERIFIED`, not permission to repost. This instruction is not a claim
that a distributed exactly-once lock has been implemented.

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
