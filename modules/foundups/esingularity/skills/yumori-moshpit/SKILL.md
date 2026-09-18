---
name: yumori-moshpit
description: Maintain the YUMORI campaign Moshpit and the private 0102 learning Moshpit with strict event-class separation, reverse chronological ordering, and verified campaign/action logging. Use for YUMORI activity logging, monk field activity, correspondence receipts, campaign procedural milestones, or 0102 learning-log routing.
---

# YUMORI Moshpit logging

Canonical repository: `FOUNDUPS/Foundups-Agent`.
FoundUp: `modules/foundups/esingularity`.

## Purpose

Maintain two distinct logs:

- **YUMORI Moshpit** = campaign history and monk activity.
- **0102 Moshpit** = agent operations, errors, repairs, confidence failures, reusable rules, and RED DOG CANDIDATE lessons.

Do not duplicate an event into both logs unless the same campaign event also produced a meaningful agent-learning incident.

## Event classification

Write to **YUMORI Moshpit** when the event materially answers “what happened in the campaign?” Examples:

- monk field activity, protest, meeting, banner/flyer work;
- substantive stakeholder reply;
- verified campaign correspondence send/follow-up;
- procedural milestone with city/council/government;
- submission, appointment, deadline, routing outcome, legal consultation, media activity;
- material document/publication milestone that changes campaign state.

Write to **0102 Moshpit** when the event primarily answers “what did 0102 learn or repair?” Examples:

- routing/data-integrity failure;
- incorrect assumption or stale state;
- preflight or send-integrity near-miss;
- spreadsheet/schema repair;
- queue/state-machine defect;
- workflow change or new generalized operating rule;
- RED DOG CANDIDATE extraction.

Routine successful checks and ordinary bookkeeping do not belong in 0102 Moshpit.

## Ordering rule

YUMORI Moshpit is grouped by Asia/Tokyo calendar date and is **reverse chronological within each day**.

1. Ensure exactly one date anchor: `YYYY-MM-DD — DAY START`.
2. Insert accepted campaign events below that anchor.
3. Sort newest effective event first.
4. For an interval, use the **end/completion time** as its effective time for ordering. Example: 16:00–17:00 sorts as 17:00.
5. Never prepend above the day anchor.
6. Never fuse the anchor with an activity paragraph.
7. Do not allow internal 0102 bookkeeping timestamps to outrank monk/campaign activity.

## Campaign-vs-agent boundary

A verified outbound email can belong in YUMORI Moshpit when it materially advances the campaign, even though the transactional details also live in Email Log.

Pure no-send escalation, queue reconciliation, formula repair, integrity checks, or operator telemetry belong in 0102 Moshpit, not the campaign timeline, unless 012 explicitly asks to promote the event into campaign history.

Material external replies and procedural outcomes stay in YUMORI Moshpit because they change the campaign path.

## Evidence and privacy

- Use Asia/Tokyo event times.
- For Gmail actions, only claim SENT after provider Sent verification.
- Keep stable message/thread IDs when useful internally.
- Do not expose private addresses, BCC, full email bodies, account-security details, or unrelated technical alerts in YUMORI Moshpit/public Git.
- Mark monk-reported activity as `REPORTED_BY_012` unless independently verified.
- Distinguish verified facts from pending/unknown details.

## Write procedure

Before editing:

1. Read the current top of YUMORI Moshpit.
2. Locate today’s date anchor.
3. Classify the event as CAMPAIGN, AGENT_INTERNAL, or BOTH.
4. Compute effective event time.
5. Check for an existing equivalent entry to avoid duplication.

After editing, read back and assert:

- exactly one date anchor for the date;
- anchor precedes all same-day events;
- newest accepted campaign event is first after the anchor;
- intervals are ordered by end/completion time;
- no AGENT_INTERNAL-only event displaced campaign activity;
- no duplicate event was introduced;
- prior-day boundaries remain intact.

## 0102 learning promotion

If the write reveals a structural weakness, append one concise entry to the private `0102 Moshpit — Agent Learning & Action Log` with root cause, generalized rule, concrete prompt/skill/code change, next test, and RED DOG CANDIDATE when repeated or structural.

## Red Dog boundary

This skill is the reusable classification and ordering contract for Red Dog/0102. It does not itself grant Gmail, Drive, GitHub, or publishing authority. Execution remains bounded by the active work order, connector permissions, correspondence preflight, and WSP 00/15/97 controls.


## PR lifecycle ownership

When 0102/Red Dog creates a bounded repository change for this skill or its projections, the work is not complete when the PR opens.

- Keep the change on a dedicated branch and PR; do not write directly to protected main.
- 0102 owns the PR to a terminal state.
- Inspect exact-head required checks, review threads, and mergeability.
- If a failure is a narrow deterministic consequence of the PR or a stale contract exposed by it, repair it on the same branch and re-verify exact-head CI.
- Do not bypass, weaken, remove, or falsify required gates.
- When all required checks pass and no blocking review remains, **squash-merge to main** and verify main contains the resulting commit.
- Retire any temporary PR-finisher watcher after verified merge.
- Do not ask 012 to manage routine GitHub mechanics. Notify/escalate only when a genuine product, policy, permission, security, or conflicting-human-intent decision is required.
