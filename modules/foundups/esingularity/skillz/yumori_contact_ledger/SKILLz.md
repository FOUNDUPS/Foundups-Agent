---
name: yumori_contact_ledger
description: Reconcile YUMORI.me campaign contacts with Gmail thread history and the connected YUMORI.me Contacts ledger without duplicating canonical email bodies.
version: 0.3.0
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
  - name: three_question_gate
    expected: repeated_high_cost_work_is_skillized_only_when_reuse_value_exceeds_maintenance_cost
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

## Three Skill Questions

Before creating, expanding, or branching any Skillz, apply this gate:

1. **Do we need it?** Is this a recurring, consequential workflow where forgetting context or repeating manual reasoning creates material cost, delay, inconsistency, or risk?
2. **Can we live without it?** Can existing WSPs, tools, another Skillz, or a short one-off procedure handle the work reliably without adding another persistent abstraction?
3. **Can we afford not to have it?** If the workflow is omitted, what is the expected cost of missed replies, duplicated outreach, stale context, bad classification, lost evidence, or inconsistent execution?

Decision rule:
- YES / NO / NO -> do not create a Skillz; use the existing path.
- YES / YES / YES -> optional; prefer the simpler existing path unless reuse frequency justifies maintenance.
- YES / YES / NO -> create/extend a Skillz because omission risk is material.
- YES / NO / NO-to-uncertain -> extend an existing Skillz rather than branching.

For this workflow: **need = yes; live without = poorly; afford not to have = no.** YUMORI.me has repeated multi-party outreach where context loss can cause duplicate contact, inappropriate follow-up, or failure to act on a material reply. Therefore this belongs as one parent Skillz with conditional branches, not many disconnected skills.

## Purpose

Maintain one recoverable communications picture for the YUMORI.me Save the Onsen / eSingularity effort without copying entire email bodies into the repo or spreadsheet.

External sources:
1. Gmail — canonical correspondence record.
2. Google Sheet `YUMORI.me Contacts` — operational contact/index ledger.
3. Google Doc `YUMORI.me Moshpit` — dated campaign milestones and material outcomes.
4. Google Doc `YUMORI.me Contacts Pics` — source imagery/business cards and transcription evidence.

Repository context: `modules/foundups/esingularity/docs/YUMORI_CONTACT_LEDGER_CONTEXT.md`.

## Truth hierarchy

```text
Gmail message/thread bytes
  -> YUMORI.me Contacts / Email Log index
  -> YUMORI.me Moshpit milestone summary
  -> repository workflow/context documentation
  -> model recollection
```

Read connected Gmail/Drive before current-state claims.

## Canonical keys

- Gmail `message_id`: unique communication event.
- Gmail `thread_id`: conversation lineage.
- normalized email: contact-route join.
- `Contact ID` (`YMC-####`): stable Contacts row identity.
- Subject text is descriptive, never a unique key.

## Parent workflow

For any incoming reply, requested audit, or stakeholder follow-up:

1. Resolve the person/organization in `YUMORI.me Contacts`.
2. Read the complete relevant Gmail thread, not only the newest message/snippet.
3. Recover what 0102/RedDog previously sent, promised, asked, or closed.
4. Read relevant Moshpit milestones and project evidence needed to understand the current campaign state.
5. When identity, authority, specialty, organization, or public position materially affects the response, research that background from authoritative/current sources. Do not research merely to decorate the reply.
6. Classify the inbound event before drafting.
7. Route to the appropriate branch below.
8. 0102 performs context synthesis, evidence checking, strategy, and culturally appropriate drafting. RedDog is the proxy/execution surface; it does not invent facts or escalate merely to win an exchange.
9. Execute only actions authorized by the current task and connector permissions.
10. Reconcile Gmail event -> Email Log -> Contacts roll-up -> Moshpit if material.

## Conditional reply branches

### Constructive / interested
Acknowledge exact substance, identify next action, preserve commitments, and never upgrade interest into endorsement/support.

### Request for information
Answer the actual question first. Retrieve current evidence before factual claims. Link the smallest useful source set; do not dump the whole prospectus.

### Pushback / objection
Determine which class applies before responding:
- factual correction;
- technical objection;
- jurisdiction/authority boundary;
- policy/process objection;
- misunderstanding of the ask;
- capacity/time refusal;
- explicit decline/no-contact.

Treat pushback as evidence, not an opponent. Correct genuine errors. Narrow requests when the recipient is the wrong expert. Clarify misunderstandings once. Respect explicit boundaries. Do not keep reframing a rejected request until the person says yes.

### Wrong person / referral
Close the rejected ask cleanly, preserve any useful referral, research the referred person/office, and start a new route with accurate context rather than forwarding a context dump.

### Media
Recover prior pitch and reporter context. Distinguish acknowledgement, request for materials, interview interest, publication decision, and automatic response. Never report press interest as coverage.

### Government / political / administrative
Recover the exact prior request and current procedural status. Separate observed official facts from campaign strategy. Address authority/jurisdiction precisely. Never imply that a meeting, copied email, or receipt equals support.

### Auto-reply
Record `AUTO ONLY`; do not treat it as human engagement.

### Bounce
Preserve the failed route/reason, verify another route, and classify a resend separately.

### Closure / explicit decline
Mark `CLOSED`. Do not nudge again unless materially new facts justify a genuinely new approach and the sender did not request no further contact.

## Event classes

`OUTREACH`, `FOLLOW-UP`, `FORMAL REQUEST`, `FORWARD`, `RESEND`, `REPLY`, `AUTO-REPLY`, `BOUNCE`, `CLOSURE`.

## Reconciliation rules

- One Email Log event per Gmail `message_id`.
- Group lineage by Gmail `thread_id`.
- Do not infer delivery from absence of bounce.
- Do not paste full message bodies into the Sheet.
- Recompute contact roll-up from Gmail truth and logged events.
- Update `Last Interaction`, `Next Action`, and notes from observed facts or clearly labeled strategy.
- Add a Moshpit entry only for material campaign changes.
- Report discrepancies instead of silently overwriting evidence.

## Contacts / Email Log minimums

`YUMORI.me Contacts` should preserve identity/context, verified routes, source/verification, Primary Gmail Thread, Email Events, First/Last Outbound, Last Inbound, Email Status, Last Subject, Last Gmail URL, Delivery, Last Reply Summary, Email Follow-up, and Last Email Sync.

`Email Log` should preserve Message ID, Thread ID, Contact ID/relationship, Direction, Date JST, From, To, CC, Subject, Event Type, short Snippet/Note, Status, Gmail URL, Sync Date.

## Moshpit discipline

Use Moshpit as operational memory/open-loop index, not a mailbox or private address book. Keep newest material milestones first. Mark unresolved actions `OPEN`. Keep facts separate from proposals/assumptions. Apply STT repair against canonical campaign entities before indexing. Preserve contact-source imagery in `YUMORI.me Contacts Pics`, structured identity in the Contacts Sheet, and only material cross-index events in Moshpit.

## Current framing

Campaign question:
> Can compute help save an onsen, revitalize a region, and create a repeatable regional model for Japan?

Immediate civic ask: preserve a short evidence-based review window to compare reuse against irreversible demolition and convene relevant parties; it is not automatic approval of eSingularity.

## RedDog / Rolodex behavior

This is the parent YUMORI.me correspondence Skillz. Branch inside it by task/reply type unless a future branch independently passes the Three Skill Questions and has distinct tools, invariants, evaluation requirements, or lifecycle.

RedDog/WRE should discover it for YUMORI.me contacts, outreach, Gmail replies, campaign email audit, stakeholder follow-up, Moshpit updates, business-card indexing, and communications history.

The Skillz grants no Gmail/Drive mutation authority. If connected sources are unavailable, report `NEEDS_VERIFICATION`; never reconstruct live correspondence from repository memory.
