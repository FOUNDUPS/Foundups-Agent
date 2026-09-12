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
  - name: government_correspondence_routing
    expected: japanese_first_government_mail_resolves_verified_routes_and_default_bcc_from_connected_ledgers_without_hard_coded_addresses
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
3. `Correspondence Routing` tab in `YUMORI.me Contacts` — mutable To/CC/BCC policy keyed by Contact ID, never by hard-coded repo addresses.
4. Google Doc `YUMORI.me Moshpit` — dated campaign milestones and material outcomes.
5. Google Doc `YUMORI.me Contacts Pics` — source imagery/business cards and transcription evidence.

Repository context: `modules/foundups/esingularity/docs/YUMORI_CONTACT_LEDGER_CONTEXT.md`.

## Truth hierarchy

```text
Gmail message/thread bytes
  -> YUMORI.me Contacts / Email Log / Correspondence Routing
  -> YUMORI.me Contacts Pics when identity/route needs card verification
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

#### Government correspondence operating contract

Use this branch when 012 says variants of `government correspondence`, `use the correspondence skill`, `write/send this to the city`, `send this to council`, or asks for follow-up with a public office.

1. **Repo first for project truth.** Read the relevant eSingularity/YUMORI repo source, Skillz, Breadcrumbs/Moshpit architecture, financial/legal contract, or current implementation before treating a Drive derivative as canonical project truth. External official records remain primary evidence for what government actually published or said.
2. **Read correspondence before drafting.** Search Gmail for the agency, named official, subject, and prior request. Read the full relevant thread before sending a reply/follow-up. Preserve `message_id` and `thread_id` lineage.
3. **Resolve contacts from the ledger.** Read `YUMORI.me Contacts`. Never infer a current address from a remembered name or email pattern.
4. **Card fallback.** If the contact is missing, ambiguous, or a TTS-normalized Japanese name cannot be resolved from the structured ledger, inspect `YUMORI.me Contacts Pics` and other source-card imagery before asking 012 to repeat information.
5. **Public-source fallback.** If no verified route exists in the ledger/card evidence, research the official municipal/prefectural/organization site or the person's own public professional/campaign page. Do not guess undisclosed internal addresses and do not treat absence of bounce as identity verification.
6. **Japanese-first government drafting.** Government-facing correspondence is drafted in natural formal Japanese unless 012 explicitly requests another language. Keep the request concrete, procedural, evidence-based, and easy for a Japanese administrative recipient to route internally.
7. **Identity and authority.** Retrieve the current committee/signatory/principal role from live project records before signing. When 0102 acts as proxy/translator, label that role accurately. Do not imply legal representation, committee authority, endorsement, land ownership, taxpayer status, or official filing status beyond verified/current evidence.
8. **Procedural precision.** Distinguish ordinary email, formal information-disclosure request, petition/陳情, PFI/PPP proposal, resident audit request, hearing request, and litigation/legal-consultation notice. An email receipt does not become a statutory filing merely because it was copied to an office.
9. **To/CC/BCC are data, not code.** Read the connected `Correspondence Routing` tab at send time. Apply active rows matching the correspondence scope. `DEFAULT_BCC` means include the currently resolved contact route in BCC unless 012 explicitly overrides it for that message. Never expose BCC recipients in To/CC or the body merely because they are routing observers.
10. **No private addresses in Git.** The repo stores only this workflow contract and stable Contact-ID semantics. Do not hard-code private/personal email addresses, phone numbers, street addresses, or mutable BCC lists in Skillz, docs, tests, source, or configuration.
11. **Reuse before creating Docs.** Prefer an existing canonical filing/proposal/evidence document. Create a new Drive document only when a distinct formal filing or collaboration artifact is actually required. Record its purpose/lifecycle so temporary working documents can later be archived or deleted without losing the sent/signed record.
12. **Send only when authorized.** Drafting does not itself grant mutation authority. When the user explicitly asks to send now and the route is verified, use the connected mail action; otherwise draft/review only.
13. **Post-send reconciliation.** Record the sent Gmail event in Email Log/Contacts, preserve the message/thread identifiers, update delivery/reply state when known, and add only material project milestones/open loops to Moshpit.
14. **No tracking decoration.** Do not add a custom campaign tracking signature, pixel, hidden identifier, or recipient fingerprint to government correspondence.

This branch intentionally stores no named default-BCC people in Git. `Correspondence Routing` is the live operational authority so the list can change without code changes or PII leakage.

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

`Correspondence Routing` should preserve Contact ID, human-readable name, channel, visibility (`TO`/`CC`/`BCC`), policy (`DEFAULT_BCC`, conditional routing, etc.), scope, active/inactive status, and a short non-secret note. Resolve the actual address from `Contacts`; do not duplicate addresses into this routing tab unless operationally required.

## Moshpit discipline

Use Moshpit as operational memory/open-loop index, not a mailbox or private address book. Keep newest material milestones first. Mark unresolved actions `OPEN`. Keep facts separate from proposals/assumptions. Apply STT repair against canonical campaign entities before indexing. Preserve contact-source imagery in `YUMORI.me Contacts Pics`, structured identity in the Contacts Sheet, and only material cross-index events in Moshpit.

## Current framing

Campaign question:
> Can compute help save an onsen, revitalize a region, and create a repeatable regional model for Japan?

Immediate civic ask: preserve a short evidence-based review window to compare reuse against irreversible demolition and convene relevant parties; it is not automatic approval of eSingularity.

## RedDog / Rolodex behavior

This is the parent YUMORI.me correspondence Skillz. Branch inside it by task/reply type unless a future branch independently passes the Three Skill Questions and has distinct tools, invariants, evaluation requirements, or lifecycle.

RedDog/WRE should discover it for YUMORI.me contacts, outreach, Gmail replies, campaign email audit, government correspondence, stakeholder follow-up, Moshpit updates, business-card indexing, and communications history.

The Skillz grants no Gmail or Drive mutation authority by itself. If connected sources are unavailable, report `NEEDS_VERIFICATION`; never reconstruct live correspondence from repository memory.
