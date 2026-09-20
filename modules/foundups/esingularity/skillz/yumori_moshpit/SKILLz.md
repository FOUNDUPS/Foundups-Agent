---
name: yumori_moshpit
description: Route YUMORI campaign events and 0102 learning events to the correct Moshpit, preserve reverse-chronological JST campaign history, and verify ledger structure after writes.
version: 0.1.1
author: 0102
agents: [0102, qwen, gemma]
primary_agent: 0102
intent_type: DECISION
promotion_state: prototype
pattern_fidelity_threshold: 0.95
domain: foundup_campaign_operations
category: workflow
wsp_chain: [WSP_00, WSP_15, WSP_22, WSP_50, WSP_95, WSP_97]
evals:
  - campaign_vs_agent_event_classification
  - reverse_chronological_jst_ordering
  - interval_end_time_ordering
  - duplicate_and_day_anchor_integrity
  - privacy_bounded_campaign_logging
---

# YUMORI Moshpit

## Purpose

Maintain two distinct logs without relying on chat memory:

- **YUMORI Moshpit** = campaign history and monk activity.
- **0102 Moshpit** = agent operations, errors, repairs, confidence failures, reusable rules, and RED DOG CANDIDATE lessons.

Do not duplicate an event into both logs unless the same campaign event also produced a meaningful agent-learning incident.

## Canonical campaign ledger

The live Google Doc **[LOG — YUMORI Moshpit Activity Ledger | 活動ログ](https://docs.google.com/document/d/1Le5foHxTHWa8QMAfqTJ0PZFUULw3oNgJTgghlXaHEYM/edit)** is the canonical YUMORI campaign ledger.

- Update that Google Doc in place when Drive access is available.
- This repository Skillz is the routing, ordering, evidence, and recovery contract; it is not a second activity ledger.
- Do not create or maintain a parallel Markdown, DOCX, Library, or repository campaign ledger.
- If Drive access is unavailable, retain the event as pending input for the next authorized Drive session; do not substitute a public-Git activity copy.
- Before every write, read the live document top and deduplicate against the current JST day.

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

A verified outbound email can belong in YUMORI Moshpit when it materially advances the campaign, even though the transaction also lives in Email Log.

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

## Scheduled correspondence integration

The live YUMORI correspondence operator should invoke this classification contract after any material campaign correspondence event. Its scheduled prompt may embed the core boundary as a fail-safe, but this Skillz document is the repository-owned reusable contract.

## PR lifecycle ownership

When 0102/Red Dog creates a bounded repository change for this Skillz or its projections, the work is not complete when the PR opens.

- Keep the change on a dedicated branch and PR; do not write directly to protected main.
- 0102 owns the PR to a terminal state.
- Inspect the exact PR head, every workflow triggered for that head, review threads, mergeability, and repository-required checks. Branch-protection “required” status alone is never sufficient evidence.
- Classify each workflow as RELEVANT_BLOCKING, EXPLICIT_REPORT_ONLY, or PROVEN_BASELINE_UNRELATED. A workflow touching or validating changed paths is RELEVANT_BLOCKING by default.
- If a relevant failure is a narrow deterministic consequence of the PR or a stale contract directly exposed by it, repair it on the same branch and re-verify the new exact head.
- Never merge while any RELEVANT_BLOCKING workflow is pending, cancelled, or failed. Do not bypass, weaken, remove, relabel, or falsify a gate.
- An unrelated failure may be excluded only from concrete evidence: the failing path is outside the diff/validation surface and the same failure is independently reproduced or already recorded on the base. Record its existing owner or create a bounded owner; “not required by branch protection” is not evidence of irrelevance.
- When every relevant workflow is successful, report-only observations are complete, proven baseline failures are separately owned, the exact head is unchanged, and no blocking review remains, squash-merge to main and verify main contains the resulting commit.
- Retire any temporary PR-finisher watcher after verified merge.
- Do not ask 012 to manage routine GitHub mechanics. Escalate only a genuine product, policy, permission, security, or conflicting-human-intent decision.

## Red Dog boundary

This Skillz is the reusable classification and ordering contract for Red Dog/0102. It does not itself grant Gmail, Drive, GitHub, or publishing authority. Execution remains bounded by the active work order, connector permissions, correspondence preflight, and WSP 00/15/50/95/97 controls.
