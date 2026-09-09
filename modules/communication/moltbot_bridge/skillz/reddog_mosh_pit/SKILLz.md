---
name: reddog_mosh_pit
description: Curate a FoundUp Mosh Pit as newest-first daily activity bullets with expandable detail. Use for activity capture, timeline cleanup, and project-history retrieval; keep system notices and future plans out of the activity feed.
version: 0.1.0
intent_type: GENERATION
promotion_state: prototype
category: workflow
logical_roles:
  - researcher
  - implementer
  - verifier
evals:
  - name: mixed_activity_and_notifications
    expected: retain_activities_exclude_system_noise
  - name: planned_meeting
    expected: plan_outside_completed_activity_feed
  - name: stakeholder_scope
    expected: authorized_project_and_explicit_disclosure_view
  - name: duplicate_capture
    expected: one_event_with_source_preserving_correction
retirement_date: null
---
# RedDog Mosh Pit

## Output

Start with the newest day. Place one short factual bullet per activity beneath
it, newest known event first. A newly captured older event belongs under its
actual day. Unknown time stays unknown. Use the FoundUp's timezone; YUMORI.me
uses Asia/Tokyo. Do not prepend status reports, instructions, navigation links,
research summaries, or a NOW/OPEN LOOPS dashboard to a requested Mosh Pit.

Treat each activity as a small Wave: its summary stays short; its details,
discussion, evidence, decisions and follow-ups expand beneath that entry.
Keep plans, background and related documents below the history or in separate
views. A plan is never a completed event. A decision made today about a future
meeting is an activity today; the future meeting itself remains a plan.

## Capture and curation

1. Resolve the canonical FoundUp and current destination from registry/live
   evidence. Repair supported STT aliases without changing source evidence.
2. Read the existing activity and evidence before adding or editing. Capture
   meaningful meetings, actions, decisions, research, artifacts, replies and
   outcomes. Attribute 012, 0102, joint work or committee work accurately.
3. Exclude automated copyright/Content ID and blocked-video notices, delivery
   diagnostics, sync logs and unrelated entertainment. A meaningful action
   taken in response can be recorded as its own concise activity; do not copy
   the notification into the feed. Do not use artist-name keyword bans.
4. Reuse one canonical event identity across capture receipts. Keep exact
   timestamps only when evidenced. Preserve OBSERVED, REPORTED_BY_012,
   INFERRED and PROPOSED distinctions; never invent causation or completion.
5. Keep canonical evidence in the existing Breadcrumb/Contact Memory path.
   Brain/Memex owns current state and open loops. Mosh Pit is their projection,
   never a second database or a new authoritative prose history.
6. For the candidate projector, normalize approved activity into the existing
   breadcrumb `data.mosh_pit` field using the contract in the MVP document.
   Only pass independently curated fields for the requested disclosure view.
   A private summary is not a stakeholder summary with its links hidden.
7. For a live Google Doc, preserve its identity, native links and unrelated
   history. Use fresh readback and a revision guard, edit only authorized
   ranges, and verify order, bullets, duplicates and removals afterward.
8. Show completion only after the destination readback or accepted effect
   receipt proves it. A proposed entry or a local candidate is not a saved
   activity or a deployed system.

## Access and implementation boundary

This prototype Skillz grants no execution, membership, sharing or publication
authority. Resolve a signed-in stakeholder's explicit project membership and
requested disclosure on the server for every read/reply/edit; Lick alone is
not membership. Keep source evidence, sensitive identities and attachments
outside public code/builds. Never fetch private content and merely hide it in
the browser. Revoked access must also close subscriptions and cached access.

`query_mosh_pit()` is a read-only candidate requiring a trusted host source;
no production source, automatic capture, write route or deployment is wired.
Do not fall back to unrestricted `query_past_work()` for a denied stakeholder.
Missing authorization remains denied. Prototype status is not promotion.

Read `extensions/reddog/docs/MOSH_PIT_WAVE_MVP.md` for ownership, source
contract, research and the phased host integration. The candidate implementation
is `modules/communication/moltbot_bridge/src/mosh_pit_projection.py`.
