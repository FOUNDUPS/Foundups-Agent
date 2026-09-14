---
name: yumori_contact_ledger
description: Reconcile YUMORI.me campaign contacts with Gmail history and the connected ledger; prepare evidence-gated, editorial-beat-specific media outreach without duplicating canonical correspondence.
version: 0.4.0
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
  - name: editorial_hook_contract
    expected: each_pitch_has_editorial_scope_beat_hook_evidence_caveat_and_one_request
  - name: protest_novelty_boundary
    expected: preexisting_japanese_protests_preclude_first_or_begins_in_japan_claims
  - name: ai_koban_truth_boundary
    expected: proposed_regional_service_non_export_model_is_not_claimed_deployed_or_financially_validated
  - name: sent_draft_reconciliation
    expected: surviving_draft_is_not_proof_of_non_send_and_subject_is_not_a_unique_event_key
  - name: press_contact_resolution
    expected: latest_principal_authorized_press_number_is_resolved_live_and_not_hard_coded_in_git
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

The 2026-09-15 media extension belongs inside this existing parent. Editorial beats need different evidence and interview hooks, not a separate skill, contact store, or political demographic-targeting system for every outlet.

## Purpose

Maintain one recoverable communications picture for the YUMORI.me Save the Onsen / eSingularity effort without copying entire email bodies into the repo or spreadsheet.

External sources:
1. Gmail — canonical correspondence record.
2. Google Sheet `YUMORI.me Contacts` — operational contact/index ledger.
3. `Correspondence Routing` tab in `YUMORI.me Contacts` — mutable To/CC/BCC policy keyed by Contact ID, never by hard-coded repo addresses.
4. Google Doc `YUMORI.me Moshpit` — dated campaign milestones and material outcomes.
5. Google Doc `YUMORI.me Contacts Pics` — source imagery/business cards and transcription evidence.
6. Existing `PRESS — YUMORI Media Outreach & Press Kit` — derived press copy and principal-authorized press contact details. Resolve its stable ID from `docs/DRIVE_DOCUMENT_INDEX.md`; do not create a replacement.

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

Read connected Gmail/Drive before current-state claims. The repository owns project specifications, while external primary records own what their issuers actually said. New explicit principal corrections take precedence over older inferred contact details; record their provenance in the connected operational record, not public Git.

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

#### Editorial positioning: one factual spine, different reporting questions

Match a newsroom's documented editorial beat and requested format. Do not tailor political persuasion to personal demographics, inferred political beliefs, vulnerabilities, or private profiles. Geographic scope here describes the story and newsroom remit, not a demographic persuasion segment. Do not claim affiliated groups or a nationwide coalition merely because outreach is national.

Shared position: oppose hyperscale development that externalizes local burdens without adequate consent, disclosure and regional benefit; propose locally governed regional computing as an alternative. Do not translate this into opposition to every data center: COGDC itself is computing infrastructure. Apply the same scrutiny to Japanese and overseas owners, and to the proposed community model.

| Editorial scope / beat | Reporting hook | Evidence and reporting request |
| --- | --- | --- |
| Fukui civic / local news | Can compute help save this onsen before an irreversible asset decision? | Current council documents, request status, field photographs, local interviews; request on-site reporting and independent verification. |
| Regional economy / industry | Will the region merely host AI infrastructure, or develop computing it can use and govern? | Local workload/customer evidence, power and fiber constraints, land and operating costs; request investigation of ownership and practical demand. |
| National society / infrastructure | Amid existing data-center opposition, an onsen campaign proposes an AI Koban alternative. | Independently reported existing disputes, JHR source trail and the Fukui case; request comparative national reporting, not a claim to have started all protests. |
| Technology / AI | A proposed community computing service, not a smaller hyperscaler with a new label. | Proposed topology, workload sizing, data boundary, reliability, security and unit economics; request a technical challenge/interview. |
| Environment / energy | Compare actual local burdens and usable heat, not green branding. | Site-specific energy, water, noise, land and heat-use measurements; never infer a footprint advantage from size or ownership alone. |
| Education / work | Regional AI access and locally developed applications, rather than job-loss predictions. | Schools' and firms' expressed needs, skills and demand studies; do not promise jobs, users, participating institutions or displacement avoided. |
| International / human-interest | An American filmmaker using AI in a Japanese onsen-preservation campaign asks who should own AI infrastructure. | Verified biography, real photographs and dates, Japanese voices and public records; no savior narrative, invented credentials or national-first claim. |

Scope changes the lead and supporting evidence, never the underlying facts, current civic request or unresolved feasibility conditions. A national release is a new editorial edition, not the local release sent unchanged to more addresses.

#### AI Koban / AI交番: internal operating definition

Status: **PROPOSED / NOT DEPLOYED / ECONOMICS NOT VALIDATED**. Principal direction recorded 2026-09-15.

AI Koban means an accessible, accountable regional computing-and-learning service: **compute developed in the region, used by the region, for the region**. COGDC is the proposed locally governed computing infrastructure; AI Koban is its local service, support and governance interface. Several local access points may share a regional compute pool. Do not equate every Koban with a 1 MW installation.

The specified service model is non-export-oriented: regional capacity serves regional workloads and locally developed/adapted applications, rather than being built to sell bulk computing to outside tenants. **Do not assume export-compute revenue** in this model. The eligible regional user/workload boundary and enforceable ownership, scheduling, pricing, accounting and local-benefit rules still require definition.

Data location, compute location, ownership, model provenance and economic distribution are separate claims. There is no implicit permission to export local private data, prompts or workloads to external cloud services. No technical isolation or zero-export guarantee may be advertised until architecture, contracts, routing, telemetry and audit prove it. Sharing public research or open-source software is a distinct decision, not automatically prohibited or authorized by the compute-service definition. Buying external hardware or adapting open models does not mean that all technology was developed locally.

Proposed topology: regional school/business/community access -> AI Koban support and governance -> appropriately sized COGDC regional compute pool. Any external service connection is a separately disclosed design question, not a silent default or existing capability.

The police-box comparison concerns proximity and accountability only; it confers no police powers, surveillance mandate or government approval. Community ownership and green operation remain design goals requiring legal and measured evidence.

**Macro dependency:** before quoting profitability, reconcile the existing FIN model's customer geography, offtake, utilization and pricing with the non-export service model. Local-only demand may support a smaller installation or lower utilization. Never reuse global-market sales assumptions to claim that regional-only compute will fund the onsen. No financial engine is modified by this documentation extension.

#### WSP 97 media preflight

Retrieve -> inspect -> challenge -> simplify -> act -> verify:

1. Retrieve current WSP 97, this skill, the live thread/recipient ledger, existing PRESS copy, latest project authority and relevant JHR article/source records.
2. **Micro:** inspect the exact draft's subject, lead, recipient list, phone, date, protest count, budget terms, source links, photo identity/caption and attachment bytes.
3. **Macro:** compare the national story to the actual local campaign; test consistency with AI Koban/COGDC design, the non-export revenue constraint, audience/disclosure boundaries and prior sends.
4. **Dialectic:** ask whether anti-data-center framing contradicts COGDC; whether a first/begins claim is false; whether distributed infrastructure can be more costly or less efficient; whether refusal of outside demand breaks assumed revenue; whether residents and the city have been represented fairly. Record a short decision/evidence summary, not private reasoning.
5. Choose the simplest defensible hook. Explain a data center as a facility containing networked computing/storage systems; explain hyperscale as very large cloud/platform infrastructure, not a synonym for every server facility or foreign ownership.
6. Use campaign language as attributed campaign position. Do not present a committee release as independent news reporting. Keep city findings, reported concerns, hypotheses, demands and proposed solutions distinct.
7. Resolve actual current JHR and LinkedIn article URLs. JHR is project-authored research, not independent corroboration; link its underlying primary sources. Do not invent a LinkedIn slug or substitute a profile URL for an unverified article.
8. Check relevant Sent, All Mail and full threads by recipients, normalized subject and distinctive body text before sending. A surviving draft may duplicate a sent copy; a Moshpit SENT label without a Gmail receipt is insufficient. On unresolved ambiguity, preserve the draft and do not resend.
9. Use the newest explicitly authorized press phone from the connected press/contact record; normalize domestic and international formats. Do not label a phone as WhatsApp-enabled without setup confirmation. Never commit the personal number into this public skill.
10. Keep unrelated newsrooms in BCC and committee recipients in CC only as authorized. A press list is not authorization for blanket repeated mail. Respect declines and verify alternate routes after bounces.
11. Send only with authorization; read back SENT status, To/CC/BCC and actual attachments. SENT is not delivered, read, interviewed or published. Log one email event per message ID and one material Moshpit breadcrumb; preserve correction history.

Required internal pitch brief: `editorial_scope`, `editorial_beat`, `hook`, `why_now`, `verified_evidence`, `proposal_and_unknowns`, `strongest_counterpoint`, `single_reporting_request`, `source_urls`, `photo_provenance`, `press_contact_source`, `dedupe_result`, `authorization`, `send_state`.

Reject: unsupported national-first claims; fabricated protest alliances; financial/safety certainty; privacy/zero-export promises without controls; routine bulk repetition; undeclared AI images; historical photos captioned as today's; static day counts carried forward without evidence.

Research anchors checked 2026-09-15 (re-read before reuse): Reuters reported Akishima opposition on 2024-07-10; TV Asahi reported the Inzai residents' lawsuit on 2026-03-09; TV Asahi/ABEMA covered community concerns and local coexistence on 2026-09-02. These establish preexisting opposition, not a YUMORI-led coalition or opposition to every data center.
- https://www.reuters.com/world/asia-pacific/tokyo-residents-seek-block-building-massive-data-centre-2024-07-10/
- https://news.tv-asahi.co.jp/news_society/articles/900185571.html
- https://news.tv-asahi.co.jp/news_economy/articles/900198650.html

This is a human/agent-readable prototype workflow, not evidence of deployed RedDog enforcement or automatic media distribution.

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

Current civic ask: **VOTE NO** on the budget containing demolition preparation at the September 25 council vote. The previous fixed 60-day/short-review-window request is superseded; do not restore it as the current ask. A NO vote does not adopt eSingularity, approve public investment, establish a PPP or guarantee reuse. Re-verify dates and procedural status before later reuse. Source: `docs/VOTE_NO_ALIGNMENT_20260913.md` on current repository main.

National editorial proposition: **Against an export-oriented hyperscale model; for regional-use, locally governed AI infrastructure.** The proposed AI Koban service is an alternative to investigate, not a demonstrated substitute for every hyperscale workload or an already operating national network.

## RedDog / Rolodex behavior

This is the parent YUMORI.me correspondence Skillz. Branch inside it by task/reply type unless a future branch independently passes the Three Skill Questions and has distinct tools, invariants, evaluation requirements, or lifecycle.

RedDog/WRE should discover it for YUMORI.me contacts, outreach, Gmail replies, campaign email audit, government correspondence, stakeholder follow-up, Moshpit updates, business-card indexing, communications history, national/regional press positioning, editorial hooks and AI Koban explanations.

The Skillz grants no Gmail or Drive mutation authority by itself. If connected sources are unavailable, report `NEEDS_VERIFICATION`; never reconstruct live correspondence from repository memory.
