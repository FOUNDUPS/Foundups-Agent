---
name: reddog_mosh_pit
description: Curate newest-first FoundUp activity with expandable evidence. Every scoped correspondence event requires its Gmail message/thread receipt under the actual project-local date; retain plans and unrelated notices outside completed activity.
version: 0.2.0
intent_type: GENERATION
promotion_state: prototype
category: workflow
logical_roles:
  - researcher
  - implementer
  - verifier
  - correspondence_curator
evals:
  - name: mixed_activity_and_notifications
    expected: retain_activities_exclude_unrelated_system_noise
  - name: planned_meeting
    expected: plan_outside_completed_activity_feed
  - name: stakeholder_scope
    expected: authorized_project_and_explicit_disclosure_view
  - name: duplicate_capture
    expected: one_event_with_source_preserving_correction
  - name: gmail_receipt_required
    expected: every_scoped_email_has_message_id_thread_id_and_actual_local_day
  - name: gmail_exhaustive_audit
    expected: paginate_primary_ids_reconcile_sets_and_report_missing_or_unknown_records
  - name: surviving_draft
    expected: compare_sent_envelopes_and_content_before_resend_never_infer_non_send_from_draft
  - name: utc_date_boundary
    expected: convert_source_timestamp_to_project_timezone_not_audit_or_creation_date
  - name: communication_privacy
    expected: private_envelopes_and_bodies_stay_in_gmail_and_contact_ledger
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
3. Exclude automated copyright/Content ID and blocked-video notices, sync logs
   and unrelated entertainment. A meaningful action taken in response can be
   recorded as its own concise activity. Scoped email bounces and auto-replies
   are an exception for receipt completeness: retain their compact evidence
   beneath the corresponding communication, not copied diagnostic bodies or
   inflated accomplishment bullets. Do not use artist-name keyword bans.
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

## Mandatory correspondence receipts: GMAIL_RECEIPT_REQUIRED

Principal clarification, 2026-09-15: every email within the authorized FoundUp
correspondence scope must be recoverable from the Mosh Pit on the day it was
actually sent or received. Materiality determines the top-level story, not
whether a scoped message retains evidence. This supersedes any interpretation
of 'material milestones only' that drops individual email references.

### Event identity and date

- `message_id` is one email event; `thread_id` is its conversation lineage.
  Never substitute a subject, draft ID, or thread ID for the message ID.
- Preserve a Gmail message URL in the connected Email Log. In an authorized
  private/team Mosh Pit, show the MID/TID pair in an evidence child. An approved
  public projection can redact these identifiers; it must not expose the
  private Gmail envelope, contact record or attachment.
- Convert an offset-aware source timestamp to the project's timezone. For
  YUMORI this is `Asia/Tokyo`. Do not use the audit day, thread's latest date,
  device timezone, or draft-creation day as the sent day. A date-only record
  retains date-only precision; missing or conflicting time remains UNKNOWN.
- Replies, forwards, corrections and supplements are distinct message events,
  even with identical subjects or the same thread. Group them under one
  activity when appropriate, retaining each individual receipt exactly once.
- A later correction may reference an earlier receipt without creating another
  email event. Preserve original evidence and an explicit supersession link.

Private/team evidence-child template:

```text
2026-09-15
- 012 + 0102: issued a press release; recipient response remains open.
  Evidence: SENT | actual time JST | short purpose | MID=<message_id>; TID=<thread_id>
  Follow-up: awaiting substantive reply; sent is not delivery or coverage.
```

### State and privacy

`DRAFT`, `SENT`, `RECEIVED`, `AUTO-REPLY`, `BOUNCE`, and `TECHNICAL_SEND` are
distinct states/classes. A draft can be recorded as a drafting activity on its
creation date, but never in the sent count. A sent message later moved to Trash
is still a sent event. Technical self-tests and accidental diagnostic sends
remain auditable but do not count as substantive outreach.

A human reply may close an ask; an automatic acknowledgment is not human
engagement. An absence of bounce is not confirmed delivery. The name of the
mayor/governor/council in a salutation is not evidence of that person's actual
receipt or of distribution to every member. Retain envelope details in Gmail
and the contact ledger, not in the Mosh Pit prose.

Never paste full email bodies, BCC lists, personal addresses, phone numbers,
Contact IDs, source-card indexes, or identity-resolution records into this
projection or public Git. A short role/name may explain an activity without
becoming a contact record.

### Audit and post-send reconciliation

1. Fix the authorized project, mailbox coverage, date window and as-of boundary.
   Inventory primary Gmail IDs over that window, including relevant archived
   and trashed sent mail. Exhaust pagination; do not interpret a snippet-only
   search as a complete mailbox inventory.
2. Union relevant recipient, subject and distinctive-body searches with the
   existing Email Log and Mosh Pit references. Read disputed messages and full
   threads. Classify unrelated messages instead of importing the whole mailbox.
3. Reconcile unique primary IDs against Email Log IDs and Mosh Pit evidence
   children. Compute missing IDs, duplicate canonical entries, incorrect local
   dates, unresolved lineage and state conflicts. Report unknowns explicitly.
4. Compare surviving drafts against sent envelopes, subjects and substantive
   content, not just matching titles. If a send result is ambiguous, hold the
   resend and inspect Gmail. A stale draft alone proves neither sent nor unsent.
5. For an authorized new send, read back Gmail's SENT state and actual recipient
   and attachment metadata first. Then upsert one Email Log event and one
   Mosh Pit receipt, update the relevant contact/open-loop state, and verify
   destination readback. Failure to log after a send is a reconciliation error,
   never permission to send the message again.
6. Backfill older receipts beneath their actual day. Preserve existing field
   narratives and links. Keep obsolete demands in historical messages labeled
   historical; do not silently apply them to today's campaign position.
7. Close the audit only with coverage totals and unresolved exclusions stated.
   An ID-index audit is not a fresh verification of every historical claim in
   every message. More detailed envelope/content validation must say what it
   covered. Scheduled automatic capture is not implied by this manual workflow.

For YUMORI recipient resolution, government/publication preflight and press
roles, reuse the existing module-owned `yumori_contact_ledger` skill. Do not
create another address book or separate correspondence database.

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
