---
name: yumori_contact_ledger
description: Reconcile YUMORI.me campaign contacts with Gmail thread history and the connected YUMORI.me Contacts ledger without duplicating canonical email bodies.
version: 0.2.0
intent_type: MAINTENANCE
promotion_state: prototype
category: workflow
agents:
  - qwen
  - gemma
wsp_chain:
  - WSP 00
  - WSP 15
  - WSP 22
  - WSP 50
  - WSP 95
  - WSP 97
evals:
  - name: canonical_message_lineage
    expected: gmail_message_id_and_thread_id_are_preserved
  - name: dedupe
    expected: one_email_event_per_gmail_message_id
  - name: reply_state
    expected: human_reply_auto_reply_bounce_and_closure_are_distinguished
  - name: external_truth_boundary
    expected: live_gmail_and_drive_are_read_before_current_state_claims
  - name: privacy_boundary
    expected: repo_stores_workflow_contract_not_private_contact_dump
  - name: moshpit_followup_index
    expected: material_milestones_and_open_followups_are_recorded_without_private_contact_duplication
retirement_date: null
---
# YUMORI.me Contact Ledger

## Purpose

Maintain one recoverable communications picture for the YUMORI.me Save the
Onsen / eSingularity effort without copying entire email bodies into the repo or
spreadsheet.

The workflow joins four external sources by explicit identifiers:

1. Gmail message/thread history — canonical correspondence record.
2. Google Sheet `YUMORI.me Contacts` — operational contact/index ledger.
3. Google Doc `YUMORI.me Moshpit` — dated campaign milestones and material
   communication outcomes, not a message-by-message mail archive.
4. Google Doc `YUMORI.me Contacts Pics` — source imagery such as business cards;
   it is evidence for contact transcription, not the communication ledger.

Repository context for this workflow is
`modules/foundups/esingularity/docs/YUMORI_CONTACT_LEDGER_CONTEXT.md`.

## Truth hierarchy

For current communication state, use this order:

```text
Gmail message/thread bytes
  -> YUMORI.me Contacts / Email Log index
  -> YUMORI.me Moshpit milestone summary
  -> repository workflow/context documentation
  -> model recollection
```

The repo defines how to reconcile the system. It does not prove that a new email
was sent, received, delivered, bounced, or replied to. Read the connected Gmail
and Drive sources before making a current-state claim.

## Canonical keys

Do not add a custom campaign tracking signature merely for indexing.

Use Gmail's existing identifiers:

- `message_id`: unique event key. One Email Log event per Gmail message ID.
- `thread_id`: conversation lineage key. First email, follow-ups, replies, and
  closures in the same Gmail conversation share this key.
- normalized email address: contact join key when resolving a contact row.
- `Contact ID` (`YMC-####`): stable YUMORI.me Contacts row identifier after the
  contact has been added to the sheet.

Subject text is useful for humans but is not a unique key.

## Required sheet model

`YUMORI.me Contacts` contains two operational tabs:

### Contacts

One row per person or organization/contact route. Keep identity, role/context,
email/phone, verification/source notes, and communication roll-up fields.

Communication roll-up fields should include at least:

- `Primary Gmail Thread`
- `Email Events`
- `First Outbound`
- `Last Outbound`
- `Last Inbound`
- `Email Status`
- `Last Subject`
- `Last Gmail URL`
- `Delivery`
- `Last Reply Summary`
- `Email Follow-up`
- `Last Email Sync`

### Email Log

One row per Gmail message/event, keyed by `Message ID`. Preserve at least:

- `Message ID`
- `Thread ID`
- `Contact ID` or resolvable contact relationship
- `Direction` (`OUT`, `IN`, `SYSTEM`)
- `Date (JST)`
- `From`
- `To`
- `CC`
- `Subject`
- `Event Type`
- short `Snippet / Note`
- `Status`
- `Gmail URL`
- `Sync Date`

Do not paste full message bodies into the sheet. Gmail is the message store.

## Reconciliation loop

When asked to audit, update, or answer from YUMORI.me correspondence:

1. Read the connected `YUMORI.me Contacts` spreadsheet first to establish the
   current contact IDs, addresses, and recorded state.
2. Search Gmail for the contact address and/or known thread ID. When doing a
   campaign-wide audit, search the YUMORI.me campaign date range and sent/inbox
   mail, including delivery failures.
3. Read all unseen messages required to classify the thread. Do not infer a
   reply from labels, snippets, or absence of a bounce.
4. For every Gmail message whose `message_id` is not already in `Email Log`, add
   exactly one event row.
5. Classify the event:
   - `OUTREACH` — first targeted outbound
   - `FOLLOW-UP` — additional outbound in an existing thread
   - `FORMAL REQUEST` — official institutional request
   - `FORWARD` — forwarded record/material
   - `RESEND` — new route after a delivery failure
   - `REPLY` — human inbound response
   - `AUTO-REPLY` — automated inbound response
   - `BOUNCE` — delivery-status failure
   - `CLOSURE` — explicit close/no-further-action outbound
6. Recompute the contact roll-up from Gmail truth plus Email Log events. A
   corrected/resend route must not remain globally `BOUNCED` merely because an
   older address failed; preserve the failed route in notes and show the active
   route's current state.
7. Update `Last Interaction`, `Next Action`, and notes only from observed facts
   or clearly labeled strategy.
8. Add a Moshpit entry only when the communication materially changes the
   campaign: substantive reply, explicit decline/support, formal request,
   meeting, delivery correction, media development, or other milestone. Do not
   dump every routine email into the Moshpit.
9. Report discrepancies instead of silently overwriting evidence.

## Reply handling

Before drafting or sending a reply, read the entire relevant thread.

- Positive/constructive reply: acknowledge the substance, preserve commitments,
  record the next action, and avoid upgrading interest into support.
- Decline/negative reply: thank the sender, stop the rejected request, and only
  introduce a broader YUMORI.me question when appropriate and not contrary to an
  explicit no-contact request.
- Auto-reply: record it as `AUTO ONLY`; never describe it as a human response.
- Bounce: record the exact failed address/reason, verify another route before
  resending, and link the resend as a new message/thread when Gmail does so.
- Closure: mark `CLOSED` and do not keep nudging the contact unless new material
  facts justify a separate future approach.

## Moshpit operational discipline

Use `YUMORI.me Moshpit` as the campaign's current operational memory and open-loop
index, not as a private-address book or a duplicate mailbox.

When a day's work materially changes the campaign:

1. Read the current Moshpit before writing so the newest date remains first and
   completed work is not re-added as a future task.
2. Add one short bullet per material event: protest/action, committee decision,
   formal request, media development, stakeholder meeting, source/evidence
   update, or meaningful outreach outcome.
3. Put unresolved actions in the same entry with an explicit `OPEN` marker and a
   concrete follow-up target. Examples: awaiting a government document, arranging
   a landowner meeting, obtaining a reply from a reporter, or reaching a higher
   decision-maker.
4. When a new contact/business card arrives, transcribe verified identity fields
   into `YUMORI.me Contacts`, preserve the source image in `YUMORI.me Contacts
   Pics`, and record only that cross-indexing event in the Moshpit. Do not copy
   private phone/email/address fields into the Moshpit merely for convenience.
5. If Gmail has not yet surfaced a user-reported send, label the Moshpit note as
   user-reported/needs Gmail reconciliation rather than manufacturing a
   `message_id` or claiming connector verification.
6. Apply STT repair before indexing. If a spoken term conflicts with established
   campaign entities or sounds semantically wrong, resolve it against canonical
   context before writing (for example Sano vs. a transcription artifact, or AI
   `tanbo`/rice field rather than an unrelated word). Do not preserve obvious STT
   noise as a new entity.
7. Keep milestone facts separate from proposals and assumptions. Use explicit
   labels such as observed, 012-reported, proposed, and open/needs verification
   when the evidence class differs.
8. After updating Moshpit, reconcile any affected contact rows and Email Log
   entries so the operational record and communication index do not drift.

## Current YUMORI.me context anchors

The campaign question is:

> Can compute help save an onsen, revitalize a region, and create a repeatable
> regional model for Japan?

The immediate civic ask is not automatic approval of the eSingularity concept.
It is a short evidence-based window to compare reuse against irreversible
demolition and convene the relevant parties.

For project facts, economics, building claims, council timing, and current
strategy, retrieve the eSingularity module docs and the connected `YUMORI.me
Moshpit`; do not turn this Skillz file into a stale duplicate campaign dossier.

## RedDog / Rolodex behavior

This is a module-owned WSP 95 Skillz candidate. RedDog/WRE discovery should find
it through `skills_registry_v2.json` and use it when the work focus contains
YUMORI.me contacts, outreach, Gmail replies, campaign email audit, contact
ledger, stakeholder follow-up, Moshpit update, campaign activity log, open
follow-up, business-card indexing, or communications history.

The Skillz grants no Gmail or Drive mutation authority by itself. Connector
permissions and explicit task authority remain separate. If connected Gmail or
Drive is unavailable, report `NEEDS_VERIFICATION`; never reconstruct live
correspondence from repository memory.
