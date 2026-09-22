# Editorial orchestration and resumable work

This is the shared instruction contract for the newsletter router and its lane
skills. It also accepts public intelligence from `openclaw_group_news`. It adds
no dispatcher, database, scheduler or autonomous publication authority.

Read [research-verification.md](research-verification.md) for the lane-specific
source gate, Gemini boundary, WSP 15 ordering, Google Docs manuscript ownership,
session-learning capture and relevant project discovery. 012's current queue is
JHR -> ROC -> Good/Bad/Ugly -> FoundUps/Eat the Startup; narrow requests override it.

## Red Dog -> 0102 -> Red Dog

012 sets scope. Red Dog normalizes that request, selects the existing LinkedIn
master and passes the following work packet to 0102. These are responsibilities,
not proof that separate processes/models ran; one session can perform both roles.

| Packet field | Required meaning |
| --- | --- |
| request / mode | Original request; audit, develop, revise, create_series, publish or schedule |
| scope | Named lane(s), issue key, destination type; exclusions implied by narrow scope |
| continuity | Existing run/task ID and parent context; current artifact location and revision |
| evidence | Source references, retrieval times, latest coverage and unresolved questions |
| target | Publisher/series IDs with verification date, or explicitly unknown |
| authority | Actual 012 instruction and applicable approval; never a worker's self-assertion |
| acceptance | Requested stage and evidence needed to call it complete |
| return | Result, artifact revision, checks, blockers, next action/owner |

0102 reads the selected child and evidence, performs only the requested work and
returns a receipt. Red Dog verifies it against the acceptance condition, presents
the result to 012 and preserves continuity. Returning to the master does not start
a full LinkedIn cycle. Passing a packet does not grant new authority or spawn a
worker automatically. On an actual runtime handoff, inherit the existing
`continuity_context.py` lineage and use authorized AgentDB breadcrumb/task/event
surfaces; do not create an editorial state database. In Work use the established
private continuity/artifact store. If persistence is unavailable, report that
limitation and provide the handoff; never claim it was saved.

## Route the requested verb

| Request | Work and stopping condition |
| --- | --- |
| Audit newsletters / have they been written? | Inventory selected lanes and evidence; report below. Do not silently write or publish issues. |
| Develop next ROC / Eat the Startup / JHR | Audit that lane, reuse a draft if relevant, create/update its brief, research and draft within scope. |
| Revise this issue | Load the latest edited artifact and 012 feedback; update the same issue and revision. |
| Create a newsletter | Distinguish a new issue from a new series using context; prepare the brief before asking a material unresolved choice. |
| Create a new series | Prepare identity/editorial specification and reuse the series skill template; live creation is a separate authorized action. |
| Publish / schedule approved issue | Pass exact revision, publisher, series and timing to `linkedin_publishing`; revalidate approval and live state. |

An audit may identify more live series than the three known lanes. Inventory all
accessible series under the verified account and selected owned publishers; mark
unsupported ones `UNMAPPED_SERIES` and propose a child after checking for an
existing owner. Never infer newsletter membership from an article title. Full
LinkedIn also selects the group cycle; a newsletter audit alone does not.

## Evidence-backed editorial audit

Return one row per lane with these fields:

`lane | skill owner | publisher/series evidence | latest live issue/date |
draft artifact/revision | editorial stage | delivery state | coverage/gaps |
next action/owner`

Search the current repository, authorized continuity/draft store, LinkedIn
published issues, drafts and scheduled queue. Use exact titles/IDs and source
locations. Record which surfaces and time range were inspected. A repository-only
audit labels LinkedIn `NOT_CHECKED_LIVE`; inaccessible surfaces are `UNAVAILABLE`.
Use `NOT_FOUND_IN_CHECKED_SCOPE`, never a global “not written,” when retrieval is
incomplete. A file, website report or merged PR proves no LinkedIn publication.

Track editorial progress separately from delivery:

- Editorial: `IDEA -> RESEARCHED -> DRAFTED -> REVIEWED -> APPROVED`.
- Delivery: `NOT_PLACED`, `DRAFT_SAVED_VERIFIED`, `SCHEDULED_VERIFIED`,
  `PUBLISHED`, `VERIFIED_LIVE`, `UNKNOWN_SUBMISSION`, or `BLOCKED_IDENTITY`.
- `NO_ACTION` and JHR `NO_REPORT` require a reason and next useful trigger.

An unresolved series blocks placement/creation/publication, not useful source
research or a local draft. Return both facts, e.g. `DRAFTED / BLOCKED_IDENTITY`.
Read back uncertain submissions before retrying. Verify draft persistence,
schedule and live publication independently. Revision or destination changes
invalidate an approval that no longer covers the exact action.

## Collaborative issue development

Use the lane's stable Google Docs master moshpit for newest-first issue history
and private session decisions; each linked issue retains its own manuscript Doc.
Search before creating either identity, preserve recovered older drafts, and record
the scope of missing-history searches. The shared research contract owns the
moshpit/issue reconciliation rules; no runtime state store is added.

Use [issue-brief.md](../assets/issue-brief.md) for all three lanes, applying the
child's editorial lens. Start from the latest artifact rather than creating a
second draft on every turn. Capture 012's angle, audience, voice and requested
language; infer only from established context and label remaining choices.
Research before claims; propose a working title, thesis, outline and evidence
gaps. When development is authorized, continue to a useful draft without requiring
approval of every reversible step. Keep the draft version and feedback together.
Only ask when a missing decision materially blocks the requested stage.

Store the completed issue artifact in the existing authorized publication/project
store; link it from continuity. Keep generic templates in the skill and private
notes/approvals out of public Git. Use current primary evidence for volatile claims.
Apply the existing imagery skill and publisher workflow for covers and rendering.

## New series onboarding

Use [newsletter-skill-template.md](../assets/newsletter-skill-template.md).
Distinguish the series specification (identity, audience, thesis, language,
cadence proposal and source owner) from its first issue. Search current skills,
publishing map and live series before adding anything. Reuse or extend an existing
lane when it fits; only a genuinely distinct publication needs another child.

For a justified child, replace every template placeholder, place `SKILLz.md` under
the existing LinkedIn skill tree, connect master and newsletter router, add the
Work reference, and extend the existing link/routing validation. This template is
an asset, not a discoverable skill or executor. Verify current platform eligibility
and UI limits before authorized live creation. Record the resulting series ID and
publisher only after read-back. A proposed cadence creates no recurring task;
creating the series does not publish its first issue.

## Group -> newsletter intelligence

Good/Bad/Ugly remains `openclaw_group_news`, separate from membership moderation.
After its authorized review, retain public source/post URL, date, concrete lesson,
evidence type and candidate lane: engineering -> FoundUps; compute economics ->
ROC; Japan infrastructure -> JHR. Deduplicate against covered topics. A private
member conversation is not reusable public evidence without permission.
Route a useful lead as an idea with next action, not a syndicated copy of the group
post. The next authorized group review checks replies and unanswered questions.
