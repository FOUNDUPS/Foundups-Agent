---
name: yumori_contact_ledger
description: Reconcile YUMORI.me Gmail history with the connected ledger and dated Mosh Pit receipts; activate bounded local, regional, national, writer, editor and release-manager media roles rather than generic outreach.
version: 0.5.0
intent_type: MAINTENANCE
promotion_state: prototype
category: workflow
agents:
  - qwen
  - gemma
logical_roles:
  - LOCAL_MEDIA_DAE
  - REGIONAL_MEDIA_DAE
  - NATIONAL_MEDIA_DAE
  - PRESS_WRITER
  - PRESS_EDITOR
  - RELEASE_MANAGER
  - CORRESPONDENCE_CURATOR
wsp_chain:
  - WSP 00
  - WSP 15
  - WSP 22
  - WSP 50
  - WSP 95
  - WSP 97
evals:
  - name: three_question_gate
    expected: extend_existing_parent_when_reuse_value_exceeds_maintenance_cost
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
    expected: every_scoped_email_has_dated_receipt_and_material_outcomes_remain_visible
  - name: government_correspondence_routing
    expected: japanese_first_verified_routes_and_live_default_bcc_without_hard_coded_addresses
  - name: editorial_hook_contract
    expected: each_pitch_has_scope_beat_hook_evidence_caveat_and_one_request
  - name: protest_novelty_boundary
    expected: preexisting_japanese_protests_preclude_first_or_begins_in_japan_claims
  - name: ai_koban_truth_boundary
    expected: regional_non_export_proposal_is_not_claimed_deployed_or_financially_validated
  - name: sent_draft_reconciliation
    expected: surviving_draft_is_not_proof_of_non_send_and_subject_is_not_a_unique_key
  - name: gmail_sent_first_entry_gate
    expected: sent_search_then_draft_comparison_then_moshpit_receipts_then_notify_0102_before_status_or_resend
  - name: earlier_sent_later_draft
    expected: report_prior_send_and_separate_update_without_claiming_the_campaign_was_never_sent
  - name: sent_missing_moshpit
    expected: repair_missing_receipt_not_resend_the_message
  - name: press_contact_resolution
    expected: latest_authorized_press_number_is_resolved_live_not_hard_coded_in_git
  - name: media_role_activation
    expected: selected_role_loads_sources_deliverable_acceptance_and_handoff
  - name: website_jhr_preference
    expected: website_report_is_primary_and_link_discovery_is_not_article_validation
  - name: role_authority_boundary
    expected: writing_or_editorial_review_never_grants_send_authority
retirement_date: null
---
# YUMORI.me Contact Ledger

## Three Skill Questions

Before creating, expanding, or branching any Skillz, apply this gate:

1. **Do we need it?** Is this recurring consequential work where forgetting context or repeating manual reasoning creates material cost, delay, inconsistency, or risk?
2. **Can we live without it?** Can existing WSPs, tools, another Skillz, or a short one-off procedure handle the work reliably without a new persistent abstraction?
3. **Can we afford not to have it?** What is the cost of missed replies, duplicated outreach, stale context, lost evidence, bad classification, or inconsistent execution?

Decision rule:
- YES / NO / NO -> do not create a Skillz; use the existing path.
- YES / YES / YES -> optional; prefer the simpler existing path unless reuse justifies maintenance.
- YES / YES / NO -> create/extend a Skillz because omission risk is material.
- YES / NO / NO-to-uncertain -> extend an existing Skillz rather than branching.

For this workflow: **need = yes; live without = poorly; afford not to have = no.** Repeated multi-party outreach makes one parent with conditional branches preferable to disconnected skills. Local and national media require different evidence, work products and hooks; they share the same identity, recipient ledger, factual spine and send gate.

## Purpose and sources

Maintain one recoverable communications picture without copying complete email bodies into the repo or spreadsheet.

1. Gmail — canonical correspondence record.
2. Google Sheet `YUMORI.me Contacts` — operational contact/index ledger.
3. Its `Correspondence Routing` tab — mutable To/CC/BCC policy keyed by Contact ID, not hard-coded repo addresses.
4. Google Doc `YUMORI.me Moshpit` — dated activity and receipt projection.
5. Google Doc `YUMORI.me Contacts Pics` — business-card/source imagery.
6. Existing `PRESS — YUMORI Media Outreach & Press Kit` — derived copy and authorized press contact details. Resolve the stable ID through `docs/DRIVE_DOCUMENT_INDEX.md`; do not create a replacement.

Repository context: `modules/foundups/esingularity/docs/YUMORI_CONTACT_LEDGER_CONTEXT.md`.

## Truth hierarchy

```text
Gmail message/thread bytes
  -> YUMORI.me Contacts / Email Log / Correspondence Routing
  -> YUMORI.me Contacts Pics when identity/route needs verification
  -> YUMORI.me Moshpit activity and receipt projection
  -> repository workflow/context documentation
  -> model recollection
```

Read connected Gmail/Drive before current-state claims. The repository owns project specifications; external primary records own what their issuers actually said. New explicit principal contact corrections take precedence over older inferred details. Record that provenance in the connected operational record, not public Git.

## Canonical keys

- Gmail `message_id`: one communication event.
- Gmail `thread_id`: conversation lineage, not an event identifier.
- Normalized email: contact-route join.
- `Contact ID` (`YMC-####`): stable identity in the private Contacts ledger.
- Subject: descriptive, never a unique key.

## Mandatory Gmail entry gate: SENT_FIRST_MOSHPIT_NOTIFY_0102

Principal correction, 2026-09-15. This gate applies to every invocation of this
Gmail/correspondence skill, including morning briefings, draft reviews, media,
government follow-ups and release-manager handoffs. Run it after governing
skill/identity intake and before reporting an outgoing item as unsent or
proposing/executing a resend. It is not merely a final pre-send checklist.

1. **Sent first.** Make the first mailbox search a relevant Sent search. Fix the
   authorized mailbox/project, date window and as-of boundary. Recover earlier
   sends for the communication's purpose using recipients, subject variants
   and distinctive content; do not limit the search to the latest draft title
   or to today's mail. Exhaust relevant pagination and include sent messages
   found in All Mail/Trash. Read candidate messages and full threads, including
   actual To/CC/BCC, message_id, thread_id and offset-aware event time. Missing
   access, incomplete pages or ambiguous matches mean UNKNOWN, not unsent.
2. **Compare every relevant draft against Sent.** Read the draft, then repeat
   or broaden the Sent search with its actual text and recipients. Compare the
   newly authored content, attachments and recipient coverage; quoted earlier
   mail, a matching subject or a similar purpose alone does not prove an exact
   duplicate. Keep the earlier campaign/request and the exact newer version
   separate. A newer unsent update does not erase an earlier successful send.
   Classify SAME_MESSAGE_SENT, EARLIER_SENT_NEW_DRAFT, PARTIAL_RECIPIENT_COVERAGE,
   NO_SENT_MATCH_IN_CHECKED_SCOPE, or UNKNOWN. No relevant draft means
   NO_RELEVANT_DRAFT, not permission to skip Sent or the receipt check.
3. **Check the Mosh Pit, not the ModLog.** Resolve each matched sent MID/TID in
   the live Mosh Pit under its actual project-local day, and cross-check the
   Email Log. Fetch Gmail IDs referenced by the Mosh Pit that the initial
   search missed. Gmail evidence is primary; Mosh Pit is a corroborating
   receipt index, not independent proof of delivery. Sent without a Mosh Pit
   entry is SENT_LOG_GAP: repair the log, never resend. A Mosh Pit SENT claim
   with no retrievable Gmail evidence is UNVERIFIED_RECORD: preserve its
   provenance and HOLD. Conflicting IDs, dates or states require correction
   notes; never resolve them by guessing. Repository ModLog entries record
   software work, not whether correspondence was sent.
4. **Notify 0102 before status or action.** Return a structured reconciliation
   packet to the supervising 0102 context, then give 012 a precise summary.
   When 0102 executes directly, this packet belongs in its current handoff and
   the conclusion is reported to 012; no email-to-self or separate agent is
   implied. Report an already-sent message before describing a surviving
   draft. State exactly which version and recipient coverage remain open.
   Do not notify another channel or claim automatic notification delivery
   without a configured, authorized channel and a receipt.

Required notification fields:
`project_scope`, `mailbox_scope`, `checked_window`, `as_of`, `sent_search_complete`,
`prior_send_state`, `sent_message_ids`, `sent_thread_ids`, `sent_local_dates`,
`actual_recipient_coverage`, `draft_message_id`, `draft_relation`, `content_delta`,
`moshpit_receipt_state`, `moshpit_event_dates`, `email_log_state`, `conflicts`,
`recommended_action`, `send_hold`, `notification_target` (0102).
Keep actual identifiers and private envelopes in the authorized handoff/ledger,
not in public Git or a public notification. Evidence fields may be explicitly
UNKNOWN; missing evidence must never be silently filled from memory.

The gate returns a reconciliation decision, not send authority. SAME_MESSAGE_SENT
blocks an automatic duplicate send; any deliberate resend requires a separate
explicit instruction after reporting the prior receipt. EARLIER_SENT_NEW_DRAFT
requires a version-specific decision, not recycling the old request. Partial
coverage never authorizes blanket resending to everyone. Unresolved evidence
keeps send_hold=true. Only a checked, authorized new action can proceed through
the existing release-manager controls. Do not delete or relabel surviving
drafts merely because a sent counterpart was found.

### Regression cases from the September 15 error

These are synthetic policy cases, not a live mailbox snapshot. They lock the
reporting distinction and no-resend behavior; static contract tests do not
prove deployed Gmail matching or automatic notifications.

| Case | Retrieved evidence | Required result | Automatic action |
| --- | --- | --- | --- |
| earlier_sent_later_draft | Earlier VOTE NO request is SENT; later AI Koban update is a distinct draft; earlier receipt is in Mosh Pit | EARLIER_SENT_NEW_DRAFT; say "The earlier VOTE NO message was sent; the later AI Koban update remains a separate draft." | NOTIFY_0102; no automatic resend |
| exact_sent_copy_draft_remains | Sent content, attachments and recipients match a surviving draft; Mosh Pit agrees | SAME_MESSAGE_SENT | NOTIFY_0102; preserve draft; no duplicate send |
| sent_missing_moshpit | Gmail verifies SENT; Mosh Pit lacks that message receipt | SENT_LOG_GAP | REPAIR_LOG; NOTIFY_0102; never resend |
| moshpit_sent_no_gmail_receipt | Mosh Pit says SENT but the Gmail message cannot be verified | UNVERIFIED_RECORD | HOLD; NOTIFY_0102 |
| incomplete_sent_search | Pagination, mailbox access or content comparison is incomplete | UNKNOWN | HOLD; NOTIFY_0102; never claim unsent |
| partial_recipient_coverage | Earlier matching content went to only part of the proposed recipient list | PARTIAL_RECIPIENT_COVERAGE | NOTIFY_0102; no blanket resend |
| draft_without_sent_match | Completed relevant searches and Mosh Pit cross-check find no sent counterpart | NO_SENT_MATCH_IN_CHECKED_SCOPE | NOTIFY_0102; state coverage; await applicable send authorization |
| no_draft | Relevant Sent search and Mosh Pit receipts checked; no relevant draft | NO_RELEVANT_DRAFT | NOTIFY_0102; report verified prior sends |

## Parent workflow

1. Run `SENT_FIRST_MOSHPIT_NOTIFY_0102` before any draft-status conclusion or resend decision; this is the first correspondence operation, not an optional media branch.
2. Resolve the person/organization in `YUMORI.me Contacts` and read the complete relevant Gmail thread, not only its latest snippet.
3. Recover previous asks, promises, sent content and closures.
4. Read relevant Moshpit milestones and current project evidence.
5. Research authoritative/current background only when identity, authority, specialty, organization or public position materially affects the response.
6. Classify the inbound event and select the conditional branch.
7. For media, load the selected duty profile from `MEDIA_DAE_ROLES.json` before drafting.
8. 0102 performs synthesis, evidence checks and drafting. RedDog is the proxy/execution surface; neither invents facts or escalates merely to win an exchange.
9. Execute only actions authorized by the current task and connector permissions.
10. Reconcile every scoped Gmail event -> Email Log -> appropriate Contacts/open-loop update -> dated Moshpit receipt. Material outcomes get a concise activity summary; routine correspondence can remain an evidence child.

## Conditional reply branches

### Constructive / interested
Acknowledge exact substance, identify the next action and preserve commitments. Never upgrade interest into endorsement or funding.

### Request for information
Answer the actual question first. Retrieve evidence and link the smallest useful source set; do not dump the prospectus.

### Pushback / objection
Classify factual correction, technical objection, jurisdiction boundary, policy/process objection, misunderstanding, capacity refusal or explicit decline/no-contact. Treat objections as evidence. Correct errors; clarify a misunderstanding once; close an ask when declined. Do not keep reframing a rejected request until the person agrees.

### Wrong person / referral
Close the wrong-person ask, preserve the referral and verify the new route before contacting it. Do not forward an indiscriminate context dump.

### Media
Recover prior pitch and reporter context. Distinguish acknowledgment, request for materials, interview interest, publication decision and automatic reply. Never report press interest as coverage.

#### Activate the work role, not a generic persona

Read the machine-readable duty profiles in [MEDIA_DAE_ROLES.json](MEDIA_DAE_ROLES.json). These profiles are part of this existing parent skill, not new parallel DAEs or contact stores. `self = 0102` remains fixed. A DAE state is a bounded assignment: selected objective, required evidence, deliverable, acceptance checks and handoff. It is not consciousness, an official appointment or extra authority.

- `LOCAL_MEDIA_DAE`: produce a Fukui onsen/public-asset pitch with a real field scene, current council decision and practical Japanese interview route.
- `REGIONAL_MEDIA_DAE`: produce an economic/industrial reporting question about regional demand, ownership, resource costs and local benefit.
- `NATIONAL_MEDIA_DAE`: produce a distinct national infrastructure story linking the Fukui case to documented wider disputes and the proposed AI Koban alternative.
- `PRESS_WRITER`: turn the selected brief into publishable copy: headline, issuer/dateline, scene, lead, why now, evidence, alternative, limits, one reporting request and contacts.
- `PRESS_EDITOR`: run the WSP 97 micro/macro/dialectic checks, challenge weak claims and record PASS or HOLD. A model's own review is not an independent third-party endorsement.
- `RELEASE_MANAGER`: resolve live recipients and authorized scope, deduplicate, inspect actual attachments, send once only with current authorization, and read back the Gmail receipt.
- `CORRESPONDENCE_CURATOR`: retain every scoped message ID under its actual local day, reconcile the ledgers and preserve open loops.

Handoff states:

```text
BRIEFED -> RESEARCHED -> WRITTEN -> EDITOR_REVIEWED
        -> AUTHORIZED -> SENT_VERIFIED -> RECONCILED
Any unresolved gate -> HOLD
```

The writer, editor and curator cannot send merely because they hold those roles. Editorial approval is not user approval. A release manager still requires the current principal instruction and connected tool permission. Preserve the active role and unfinished deliverable in a handoff when 012 changes topics; do not silently reset to generic chat.

#### Editorial positioning: one factual spine, different reporting questions

Match documented newsroom remit and format. Do not tailor political persuasion to personal demographics, inferred beliefs, vulnerabilities or private profiles. Geographic scope describes the story and editorial remit, not a demographic persuasion segment. Do not invent affiliated groups or a nationwide coalition.

Shared position: oppose hyperscale development that externalizes local burdens without adequate consent, disclosure and regional benefit; investigate locally governed regional computing. Do not oppose every data center in the same breath: COGDC is computing infrastructure too. Apply the same scrutiny to domestic and overseas owners and the proposed community model.

| Editorial scope / beat | Reporting hook | Evidence / reporting request |
| --- | --- | --- |
| Fukui civic / local | Can compute help save this onsen before an irreversible asset decision? | City records, real field photos, local voices; on-site reporting and independent verification. |
| Regional economy / industry | Will the region merely host equipment, or use, develop and govern computing? | Regional workloads, power/fiber, land and operating costs; investigate demand and ownership. |
| National society / infrastructure | Amid existing data-center opposition, an onsen campaign proposes an AI Koban alternative. | Existing disputes, JHR source trail and Fukui case; comparative reporting, not a national-first claim. |
| Technology / AI | A community computing service, not a smaller hyperscaler with a new label. | Topology, workload sizing, data boundaries, security, reliability and economics; technical challenge/interview. |
| Environment / energy | Compare measured burdens and usable heat, not green branding. | Site-specific electricity, water, noise, land and heat measurements; size or ownership alone proves no advantage. |
| Education / work | Regional AI access and locally developed applications, not job-loss predictions. | Expressed school/firm needs and skills evidence; no promised jobs, participants or displacement avoided. |
| International / human interest | An American filmmaker using AI in an onsen campaign asks who should own AI infrastructure. | Verified biography, photographs/dates, Japanese voices and records; no savior narrative or invented credentials. |

Scope changes the lead and supporting evidence, never the underlying facts, current civic request or feasibility limits. A national release is a new editorial edition, not the local release sent unchanged to more addresses.

#### AI Koban / AI交番: internal operating definition

Status: **PROPOSED / NOT DEPLOYED / ECONOMICS NOT VALIDATED**. Principal direction recorded 2026-09-15.

AI Koban is an accessible, accountable regional computing-and-learning service: **compute developed in the region, used by the region, for the region**. COGDC is the proposed locally governed computing infrastructure; AI Koban is its service, support and governance interface. Multiple access points can share a regional compute pool. Not every Koban needs a 1 MW installation.

The model is non-export-oriented: capacity serves regional workloads and locally developed/adapted applications, rather than bulk sales to outside tenants. **Do not assume export-compute revenue.** Eligible users and workloads, ownership, scheduling, pricing, accounting and local-benefit rules still require specification.

Data location, compute location, ownership, model provenance and distribution of economic value are separate claims. No implicit permission exists to export local private data, prompts or workloads to outside cloud services. No isolation or zero-export guarantee may be advertised until architecture, contracts, routing, telemetry and audit establish it. Sharing public research or open-source software is a separate decision. External hardware and adapted open models do not mean all technology was invented locally.

Proposed topology: regional school/business/community access -> AI Koban support/governance -> appropriately sized COGDC compute pool. An external-service connection is a separately disclosed design question, not a silent default or existing capability.

The police-box comparison means proximity and accountability only, not police powers, surveillance or official approval. Community ownership and green operation need legal and measured evidence.

**Macro dependency:** reconcile FIN's customer geography, offtake, utilization and pricing with the non-export model before quoting profitability. Regional-only demand may require a smaller installation. Global GPU sales assumptions cannot establish that regional-only compute funds an onsen. This documentation changes no financial engine.

#### WSP 97 media preflight

Retrieve -> inspect -> challenge -> simplify -> act -> verify:

1. Retrieve current WSP 97, this skill and selected role, live thread/recipient ledger, existing PRESS copy, project authority and JHR sources.
2. **Micro:** inspect exact subject, lead, recipients, phone, date, protest count, budget terms, source links, photo identity/captions and attachment bytes.
3. **Macro:** compare national framing to actual local activity, AI Koban/COGDC design, non-export economics, prior sends and disclosure boundaries.
4. **Dialectic:** challenge anti-data-center language versus COGDC, first/begins claims, distributed-system cost/efficiency, local-only revenue and fairness to residents/city. Record a short decision/evidence summary, not private reasoning.
5. Select the simplest defensible hook. Explain data centers as facilities with networked computing/storage; hyperscale means very large cloud/platform infrastructure, not every server facility or all foreign ownership.
6. Attribute campaign positions. A committee release is not independent news. Separate official findings, reported concerns, hypotheses, demands and proposed solutions.
7. **Website first:** use `https://esingularity.ai/reports/jhr` as the JHR publication reference, not LinkedIn. Verify the actual edition/anchor before specifying one. Finding the link on the homepage is not proof that the report body loaded. JHR is project-authored; use underlying primary sources for corroboration. Never invent article URLs.
8. Check Sent, All Mail including relevant Trash, and full threads by recipients, normalized subject and distinctive content. A surviving draft may duplicate a sent copy; a Moshpit SENT label without a Gmail receipt is insufficient. Unresolved ambiguity means HOLD, not resend.
9. Resolve the newest authorized press phone from connected PRESS/Contacts. Do not label it WhatsApp-enabled without setup confirmation or put the number into public Git.
10. Keep unrelated newsrooms BCC and committee contacts CC only as authorized. A press list does not authorize blanket repeated mail. Respect declines and verify replacement routes after bounces.
11. Send only with current authorization. Read back SENT, actual recipient classes and attachments, then reconcile every scoped email receipt. SENT is not delivered, read, interviewed or published.

The required pitch fields and role-specific acceptance tests are in `MEDIA_DAE_ROLES.json`. A pitch lacking a concrete hook, why now, source-backed evidence, strongest counterpoint and one reporting request remains unfinished.

Reject unsupported national-first claims, fabricated alliances, financial/safety certainty, unverified privacy guarantees, repeated bulk pitches, undeclared AI images, historical photos captioned as today's, and day counts advanced without evidence.

Research anchors previously checked 2026-09-15; re-read before reuse:
- Reuters, Akishima opposition, 2024-07-10: https://www.reuters.com/world/asia-pacific/tokyo-residents-seek-block-building-massive-data-centre-2024-07-10/
- TV Asahi, Inzai lawsuit, 2026-03-09: https://news.tv-asahi.co.jp/news_society/articles/900185571.html
- TV Asahi/ABEMA, community concerns, 2026-09-02: https://news.tv-asahi.co.jp/news_economy/articles/900198650.html

These establish preexisting disputes, not a YUMORI-led coalition. Role profiles are a human/agent-readable prototype workflow, not deployed automatic role routing or media distribution.

### Government / political / administrative
Recover the exact request and procedural status. Separate official facts from strategy. Meetings, copied messages and receipts are not support.

#### Government correspondence operating contract

1. **Repo first for project truth.** Read relevant eSingularity/YUMORI sources, Skillz and current financial/legal/implementation boundaries. External official records remain primary evidence for government statements.
2. **Read correspondence before drafting.** Search agency, official, subject and prior ask; read complete threads and preserve `message_id` / `thread_id`.
3. **Resolve contacts from the ledger.** Read `YUMORI.me Contacts`; never infer a route from remembered names or email patterns.
4. **Card fallback.** Resolve absent/ambiguous identities and STT-normalized Japanese names against `YUMORI.me Contacts Pics` before asking 012 to repeat information.
5. **Public-source fallback.** Use the official office/site or public professional channel when ledger/card evidence is insufficient. Do not guess undisclosed internal addresses or use absence of bounce as identity verification.
6. **Japanese-first government drafting.** Use natural formal Japanese unless otherwise requested. Keep asks concrete, procedural, sourced and easy to route.
7. **Identity and authority.** Retrieve the current signatory/committee role. Label 0102 as proxy/translator. Do not inflate legal representation, formal filing, property status, endorsement or organizational authority.
8. **Procedural precision.** Distinguish ordinary mail, information-disclosure request, petition, PPP/PFI proposal, resident audit request, hearing and legal consultation. Copying an office does not establish statutory acceptance.
9. **To/CC/BCC are data, not code.** Read `Correspondence Routing` at send time. Apply active matching `DEFAULT_BCC` rows unless 012 overrides them. Do not expose observers through To/CC or body text.
10. **No private addresses in Git.** Keep personal routes, phone/address details and mutable BCC lists in connected records, never public skills, docs, tests or config.
11. **Reuse before creating Docs.** Update canonical existing filing/proposal/evidence documents. New files need distinct durable purpose and lifecycle.
12. **Send only when authorized.** A draft or role does not grant mutation authority. An explicit current send instruction and verified route permit the connected send action.
13. **Post-send reconciliation.** Preserve Gmail message/thread IDs, event time and delivery/reply class in Email Log; update relevant Contacts state and every scoped Moshpit receipt.
14. **No tracking decoration.** Do not add a custom campaign tracking signature, pixel, hidden identifier, or recipient fingerprint to government correspondence.

Named default-BCC people remain outside Git. The connected `Correspondence Routing` tab is the mutable policy authority.

### Auto-reply
Record `AUTO ONLY`; do not count as human engagement.

### Bounce
Preserve failed route/reason, verify another route, and record an authorized resend as a distinct event.

### Closure / explicit decline
Mark `CLOSED`. Do not nudge again unless materially new facts justify a genuinely different approach and the recipient did not request no further contact.

## Event classes

`OUTREACH`, `FOLLOW-UP`, `FORMAL REQUEST`, `FORWARD`, `RESEND`, `CORRECTION`, `REPLY`, `AUTO-REPLY`, `BOUNCE`, `CLOSURE`, `TECHNICAL_SEND`, `DRAFT`.

## Reconciliation rules: every scoped message retains a receipt

- One Email Log event per Gmail `message_id`, grouped by genuine `thread_id`.
- Every scoped outgoing mail, reply, forward, correction and supplement has a Moshpit evidence child on its actual project-local send day. Every relevant inbound event retains its receipt and state. Materiality controls summary prominence, not receipt retention.
- YUMORI uses `Asia/Tokyo`. Convert offset-aware timestamps; never substitute audit day, draft day, or thread's latest date. Unknown precision stays unknown.
- Drafts remain DRAFT on creation day, outside sent totals. SENT plus Trash remains a sent event. Separate technical/test sends from substantive outreach.
- Audit a bounded primary Gmail ID inventory through all pages and reconcile set equality against the ledger and Moshpit. Report missing IDs, duplicate events, conflicting dates and coverage limits.
- A sent salutation naming mayor, governor or all councilors is not an actual-recipient receipt. Check To/CC/BCC in Gmail; distinguish department delivery from forwarding to the named official.
- Do not infer delivery from absence of bounce. Do not paste full bodies into the Sheet.
- Recompute relevant contact roll-ups and open-loop state from evidence; do not imply every contact is fully refreshed when only the message index was backfilled.
- Correct discrepancies with source-preserving notes. A failed ledger write after a successful send triggers reconciliation, never automatic resending.
- Verify Google Doc/Sheet readback, dates and unique IDs before reporting completion.

Reuse the existing `reddog_mosh_pit` skill's `GMAIL_RECEIPT_REQUIRED` contract for projection. Gmail remains primary evidence; Moshpit is not a second mailbox or memory database.

## Contacts / Email Log minimums

`YUMORI.me Contacts`: identity/context, verified routes, provenance, Primary Gmail Thread, Email Events, First/Last Outbound, Last Inbound, Email Status, Last Subject, Last Gmail URL, Delivery, Last Reply Summary, Email Follow-up and Last Email Sync.

`Email Log`: Message ID, Thread ID, Contact ID/relationship, Direction, Date JST, From, To, CC, Subject, Event Type, short Snippet/Note, Status, Gmail URL and Sync Date. A backfilled subject summary or incomplete envelope must be explicitly labeled; do not use incomplete columns as a definitive recipient list.

`Correspondence Routing`: Contact ID, readable name, channel, visibility, routing policy, scope, active/inactive state and brief non-secret note. Resolve addresses from Contacts rather than duplicating mutable routes.

## Moshpit discipline

Keep newest-first dated activity with expandable receipt details. Keep private contacts, BCC lists, phone numbers, source-card identity indexes and full bodies outside Moshpit/public Git. Mark open actions OPEN and preserve factual versus reported/proposed distinctions. One group outreach activity can contain multiple individual email receipts. Historical subjects can preserve withdrawn demands without making them the current request.

## Current framing

Campaign question:
> Can compute help save an onsen, revitalize a region, and create a repeatable regional model for Japan?

Current civic ask: **VOTE NO** on the budget containing demolition preparation at the September 25 council vote. The previous fixed 60-day/short-review-window request is superseded. A NO vote does not adopt eSingularity, approve public investment, establish a PPP or guarantee reuse. Re-verify dates and procedure before later reuse. Source: `docs/VOTE_NO_ALIGNMENT_20260913.md` on current repository main.

National proposition: **Against an export-oriented hyperscale model; for regional-use, locally governed AI infrastructure.** AI Koban is an alternative to investigate, not a demonstrated substitute for every hyperscale workload or an operating national network.

## RedDog / Rolodex behavior

This remains one parent correspondence Skillz with role-bound branches. Discover it for YUMORI outreach, local/regional/national press, hook/story development, writer/editor/release-manager assignments, Gmail audits, government correspondence, stakeholder follow-up, Moshpit capture and AI Koban explanations. Load `MEDIA_DAE_ROLES.json` rather than merely announcing a persona.

The Skillz grants no Gmail or Drive mutation authority by itself. If live sources are unavailable, report `NEEDS_VERIFICATION`; never reconstruct current correspondence from memory. Documentation and contract tests do not establish runtime activation, autonomous scheduling, deployment or permission to send.
