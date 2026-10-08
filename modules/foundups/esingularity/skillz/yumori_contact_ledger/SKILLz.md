---
name: yumori_contact_ledger
description: Ground YUMORI.me correspondence in live Gmail/CRM state, preserve routing consent, write plain committee correspondence, reconcile receipts, and promote repeated operator failures into reusable rules.
version: 0.8.0
communication_policy_revision: 2026-10-06
document_audit_policy_revision: 2026-10-08
author: 0102
agents: [0102, qwen, gemma]
primary_agent: 0102
intent_type: MAINTENANCE
promotion_state: prototype
pattern_fidelity_threshold: 0.99
domain: foundup_campaign_operations
category: workflow
wsp_chain: [WSP_00, WSP_15, WSP_22, WSP_50, WSP_95, WSP_97]
evals:
  - sent_first_reconciliation
  - pre_draft_correspondence_state_capsule
  - routing_consent_enforced
  - plain_committee_correspondence
  - accurate_human_and_organization_attribution
  - committee_signature_default
  - no_parallel_contact_database
  - moshpit_receipt_integrity
  - recipient_document_audit_required
  - recursive_learning_promotion
  - capital_network_graph_reconciliation
---

# YUMORI.me correspondence / contact ledger

## Purpose

This is the parent correspondence Skillz for YUMORI.me.

It does not create a second contact database. Live state remains in:

1. Gmail — canonical message/thread history.
2. Google Sheet `CONTACTS — YUMORI Master Contact Sheet`:
   - `Contacts`
   - `Email Log`
   - `Action Queue`
   - `Correspondence Routing`
   - `LinkedIn` — provider-visible relationship/contact evidence staging
   - `Capital Targets` — organization-level capital/relevance pipeline
   - `Capital People` — named decision-maker and warm-path graph
3. Google Doc `LOG — YUMORI Moshpit Activity Ledger | 活動ログ`.
4. Google Doc `0102 Moshpit — Agent Learning & Action Log` for operator learning.
5. Existing contact-source images / business cards when identity needs verification.

Repository Skillz own reusable operating rules, not private recipient dumps.

## Drive working-artifact routing

Use Google Drive for mutable human/0102 working artifacts; do not create parallel private drafts in Git.

- Discover the current Drive structure live by folder/file name rather than hard-coding personal Drive IDs.
- Treat broad `eSingularity` search results as mixed-era by default. Current Fukui/YUMORI/AI Koban work and historical Educational Singularity/eSingularity material are separate retrieval scopes; historical material is context/provenance until explicitly promoted by the current project authority.
- Reserve numeric prefixes for the canonical current-project document spine; operational folders use semantic prefixes.
- Current eSingularity working hierarchy: `CURRENT — YUMORI × eSingularity.ai × AI Koban — Working Documents` with `WORK — Correspondence Drafts`, `EDITORIAL — Newsletters & Articles`, `PARTNERS — Partnership & Business Development`, and `ARCHIVE — Superseded Current-Project Drafts`.
- Substantive unsent stakeholder email drafts that 012 and 0102 are collaboratively revising belong in `WORK — Correspondence Drafts`.
- Partnership strategy/reference material belongs in `PARTNERS — Partnership & Business Development`; do not duplicate the live email manuscript there.
- Gmail remains canonical for sent/thread history. A Drive draft is a working artifact, never proof of send, receipt, approval, or current recipient routing.
- Before creating a new draft, search Drive for the current stakeholder/topic manuscript and update it in place when appropriate.
- Preserve private recipient/BCC state in the live CRM/Gmail surfaces, not in public Git.
- Obvious speech-to-text substitutions may be normalized only against established project vocabulary; genuinely ambiguous identity/term substitutions must be held for 012 clarification.

## Mandatory execution order

For every substantive YUMORI.me correspondence task:

1. Resolve the person / organization from live Contacts.
2. Read Correspondence Routing for current consent and route state.
3. Search Gmail Sent before claiming an ask is unsent or unanswered.
4. Read the complete relevant thread and every current draft for the same recipient/topic scope.
5. Reconcile the latest real state against Email Log / Action Queue / Correspondence Routing / relevant Moshpit receipts.
6. Build the **Correspondence State Capsule** below. No substantive recipient-finalized draft may be created or materially updated before the capsule resolves.
7. For a proposal, PDF, form, briefing, presentation or substantive linked document, load
   `../recipient_document_audit/SKILLz.md` and audit the whole package before finalization.
   Preserve review-only instructions; an audit PASS is not send authorization.
8. Draft or act only within the capsule's current authorization and next-allowed-action state.
9. Verify provider state after mutation.
10. Reconcile the canonical records.
11. If the run exposed a meaningful error, near-miss, stale assumption, duplicate, coverage failure, or reusable improvement, update the operating rule and 0102 learning log.

Do not replace these reads with memory.

## Plain committee correspondence

Policy revision: 2026-10-06, explicit 012 direction. This replaces the former
mandatory proxy introduction, third-person monk framing and `0102` sign-off for
external YUMORI text. Internal operator identity and audit attribution stay intact.

### Sender and opening

- Write the authorized message as correspondence from the YUMORI Preparatory Committee.
- Use the established committee name. Do not invent a secretariat, officer, employee,
  registered corporation, legal representative or individual sender.
- Start with the subject/request. On first contact, one short committee introduction
  is enough; established threads do not need the organization explained again.
- Default: do not open with `0102です`, `私は0102です`, or an English equivalent.
- Do not add routine AI, digital-twin, proxy or translation-credit labels to external
  openings, body text, display names or signatures. Drafting software is not the subject.
- Use natural committee wording such as `当委員会では` for authorized committee facts.
  Refer to an individual by the verified name only when attribution actually matters;
  do not force `この僧は` into formal correspondence.
- Never imply that 0102 personally performed a field action completed by the monk.
  Report the verified event naturally without inventing who did it or who signed.

### Signature and truthfulness

Default sign-off: `YUMORI.me設立準備委員会`.

Use the verified full committee name when the procedure requires it. Add only the
approved contact details and, when required, the actual authorized person's name.
Do not automatically append `0102`, `代理・翻訳：0102`, `AIアシスタント`,
`AI representative` or `digital proxy` as authorship/signature boilerplate.

Routine assisted writing needs no unsolicited authorship announcement. Answer direct
questions about AI assistance truthfully and satisfy any explicit procedural disclosure
requirement. Do not claim to be a human employee, personally sign for someone, assert
human review that did not occur, or imply delegated legal authority without evidence.
A required representative/translator field on an official form is not optional branding:
complete it accurately from verified authority; never erase or falsify it.

### Simplicity and attribution

- Translate intent into natural, polite Japanese, not literal English structure.
- One purpose per message; put the requested action and relevant date near the top.
- Prefer a short opening, essential facts, a small number of questions and the committee
  signature. Include only links/attachments needed for that purpose.
- Omit internal protocols, status codes, character introductions and jokes from City,
  Council, grant, legal and other formal correspondence.
- Do not repeat unsupported claims, invent quotations or promote an inquiry to approval.
  Attribute personal opinions and reported events only when relevant.
- Do not infer that unanswered email proves rejection because of AI assistance. Keep
  a reported call refusal distinct from an evidenced explanation for email nonresponse.

Example opening: `旧羽生小学校・旧下宇坂小学校の事前相談について、受領状況を確認させてください。`

Example closing: `お手数ですが、ご確認のほどよろしくお願いいたします。` followed by
`YUMORI.me設立準備委員会`.

### Existing drafts and other channels

Apply this policy to newly authored external text and authorized edits of existing
unsent drafts. Search Sent first, preserve draft/thread identity, and rerun the required
capsule and recipient preflight before a recipient-finalized draft mutation. Editing
style does not authorize sending. Never rewrite historical Sent mail, quoted stakeholder
text, official forms or audit evidence to hide how earlier correspondence occurred.
Do not remove `AI` from legitimate project descriptions such as AI Koban or AI infrastructure.

Phone calls use `.claude/skills/reddog-phone-conversation/SKILL.md`: default to a human-led
call with translation support, not an independently presented agent. No routine branded
AI/proxy opening is required. Do not pretend synthetic speech is a human representative;
answer identity questions accurately and stop direct synthetic participation after refusal.
Personal/casual field-proxy humor remains outside the formal City correspondence default.

## Routing-consent guard

Correspondence Routing is binding state.

- Person and organization routes are separate.
- `DO_NOT_ADDRESS_OR_CC` / `PERSONAL_ROUTE_CLOSED` are hard denies.
- Historical direct correspondence never reopens a closed personal route.
- If an institutional route already received the current request, do not create duplicate resend work.
- Resolve mutable To/CC/BCC at execution time from live state.
- Never hard-code private recipient addresses or BCC lists into public Git.

A human-friendly internal disambiguation alias may exist in live/private state when needed (for example two people sharing a surname), but do not turn an unverified alias into a formal identity.

## Execution origin — 012-directed Work and unattended Red Dog

Apply the 2026-10-02 instruction from 012: developing the Red Dog schema must not
become a blanket veto on correspondence 012 has explicitly directed in Work.

Classify each work item before applying #1779 containment:

- `012_DIRECTED_WORK`: an identifiable current or still-valid 012 instruction
  authorizes this specific work item/send. Continue through the existing live
  capsule, Sent-first, recipient preflight and provider-readback checks. An open
  #1779 alone is not a blocker in this lane. Do not ask again for authorization
  already given. The live connector remains a directly callable provider surface;
  this lane does not claim mechanical sender-boundary enforcement.
- `REDDOG_AUTO`: schedules, background triggers, autonomous queue processing and
  agent-selected outreach. Keep external sends draft/HOLD-only until #1779's actual
  service/tool-host boundary is deployed and qualified. A Work-origin instruction
  cannot be copied into a later automated run as standing send authority.
- `UNKNOWN`: HOLD / RECONCILE; never silently promote an unclear origin to Work.

Bind `execution_origin`, `work_item_id` and `principal_instruction_ref` in the
working handoff/receipt. Recover direction from the actual 012 instruction, never
from a model-created label, a draft, urgency, a PR, or a stale queue row. Retain any
message-specific hold: the instruction not to send the Fukui reply during the
#1779 engineering task remains `HOLD_ENGINEERING` in that task.

For a directed Work send, immediately before submission:

1. read fresh relevant Sent, complete thread and current canonical draft;
2. reconcile capsule/CRM/routing and reject duplicates, third follow-ups, closed or
   unknown routes; engineering holds and recipient BLOCK results still win;
3. reuse `reddog_recipient_preflight` for identity/policy and exact To/CC/BCC;
   bind Contact IDs/roles, purpose, body/attachments and reply target to the reviewed
   transaction; do not let the composer authorize its own list;
4. use the actual Gmail tool only within the established 012 direction, after
   re-reading the exact saved draft or reconstructing the exact explicit headers;
5. read back the exact provider message/thread and full To/CC/BCC; only exact equality
   becomes VERIFIED_SENT. Missing/extra recipients are integrity incidents, not
   automatic resend work. Record actual verification separately from delivery.

This is a user-directed operating-policy correction, not resolution of #1779 and
not a software bypass around recipient/Sent checks. Do not weaken Red Dog AUTO,
close #1779, or claim the direct Work connector has been mechanically isolated.
The schema classifier `reddog_correspondence_execution_mode.py` returns only mode/
checks-required labels; it grants no provider capability or SEND receipt.

STT correction: recent “Akida” / “Akita” means **Akira Hasegawa**. Resolve the
existing contact; do not create an Akita identity or guess a new address.

## Sent-first reconciliation

**Assume-Sent invariant:** every proposed outbound must begin from the presumption that it may already have crossed the provider boundary. A Gmail draft, Drive manuscript, CRM row, queue label, Moshpit entry, or prior session statement is never proof that the message is unsent.

Before claiming that a message is unanswered, an ask is unsent, a draft is pending, or before any send-capable action:

1. Search relevant Gmail Sent with overlap. Use the exact recipient route(s) plus thread/message identifiers when known, and corroborate with subject/body/attachment markers rather than a single broad keyword.
2. Read exact candidates and their full threads.
3. Compare newly authored text, attachments, and recipient coverage — not subjects alone.
4. Distinguish:
   - `SAME_MESSAGE_SENT`
   - `EARLIER_SENT_NEW_DRAFT`
   - `PARTIAL_RECIPIENT_COVERAGE`
   - `NO_SENT_MATCH_IN_CHECKED_SCOPE`
   - `UNKNOWN`
5. Only a complete `NO_SENT_MATCH_IN_CHECKED_SCOPE` result permits progression toward a new provider send. `UNKNOWN`, incomplete pagination, ambiguous matches, or an unsearched exact recipient means HOLD / RECONCILE.
6. Immediately before every send-capable action, repeat the Sent check even when it was already performed earlier in the same session. A newly provider-sent event invalidates the prior capsule/preflight.
7. If any matching provider-Sent event already covers the ask or recipient scope, do not resend. Reconcile Gmail -> Email Log -> Contacts/Action Queue -> Moshpit instead.
8. A surviving newer draft is distinct from an earlier successful send only when its unsent delta is proven after the Sent comparison.
9. Missing Moshpit receipt after a verified send is a logging repair, not permission to resend.
10. Provider-Sent integrity incidents still count as Sent for duplicate and follow-up suppression.

## Correspondence State Capsule — native continuity first, provider delta second

The fastest safe cross-session memory is **not another Moshpit or another contact database**.
YUMORI consumes the generic Red Dog correspondence-state capability at
`modules/communication/moltbot_bridge/skillz/reddog_correspondence_state/SKILLz.md`.

Before creating, materially updating, forwarding, or sending substantive recipient-finalized
correspondence:

1. load the persisted Red Dog scope state when available;
2. compare its provider watermark/freshness with the live provider;
3. when unchanged and VALID, use the native scope state as the continuity starting point;
4. when changed/unknown/stale, reconcile only the provider delta needed for that scope;
5. rebuild the state capsule below from provider truth + current routing/CRM evidence;
6. persist the repaired materialized state after reconciliation.

The native correspondence store is the durable M2M continuity layer. It is a rebuildable
continuity projection, not send authority. Gmail/provider records remain transaction truth,
and live recipient/routing preflight remains mandatory before every send-capable action.

If native correspondence state is unavailable, fall back to the full reconciliation sequence
below rather than inventing state.

The capsule is a working receipt for the current execution only. Do **not** persist raw
email bodies or private recipient dumps in Git. Gmail remains transaction truth; Email Log
is the event index; Contacts / Action Queue carry current operational state; Correspondence
Routing carries recipient authorization; Moshpits carry campaign history or reusable
learning.

Minimum capsule schema:

```text
scope_key:
  stakeholder_or_org:
  topic_or_ask:
active_thread_ids:
latest_inbound:
  message_id:
  occurred_at:
  answered_asks:
latest_outbound:
  message_id:
  occurred_at:
  purpose:
outbound_since_latest_inbound:
sent_coverage_state:
  SAME_MESSAGE_SENT | EARLIER_SENT_NEW_DRAFT | PARTIAL_RECIPIENT_COVERAGE |
  NO_SENT_MATCH_IN_CHECKED_SCOPE | UNKNOWN
current_drafts:
  - draft_id:
    thread_id:
    status: ACTIVE | HOLD | SUPERSEDED
    delta_vs_sent:
open_asks:
new_delta_not_previously_sent:
routing_state:
sender_boundary_state:
queue_state:
follow_up_gate:
  CLEAR | WAIT | ESCALATE | BLOCK_DUPLICATE | BLOCK_THIRD_FOLLOWUP | UNKNOWN
next_expected_event:
next_allowed_action:
evidence_checked:
  gmail_sent:
  full_thread:
  drafts:
  email_log:
  action_queue:
  correspondence_routing:
  relevant_moshpit:
```

Rules:

1. Build the capsule **before** `create_draft`, before a material `update_draft`, and again
   immediately before any send-capable action.
2. Count follow-ups from provider evidence, not memory or labels. A provider-sent message
   still counts for duplicate/follow-up suppression even when a separate send-integrity
   incident means it cannot be promoted to `VERIFIED_SENT`.
3. Separate **old unresolved asks** from **new delta**. New facts may be retained for the
   next legitimate event without re-sending the entire prior request.
4. `Action Queue` is an operational projection, not sufficient by itself. If it conflicts
   with Gmail / Email Log / Routing, repair the stale projection and fail closed until the
   conflict is understood.
5. A Moshpit receipt can accelerate continuity but cannot prove a send. Missing narrative
   logging never creates resend authority.
6. If `follow_up_gate` is `WAIT`, `ESCALATE`, `BLOCK_DUPLICATE`,
   `BLOCK_THIRD_FOLLOWUP`, or `UNKNOWN`, do not create a new send-ready draft. An existing
   draft may be marked `HOLD` while preserving genuinely new delta.
7. If any required evidence check is incomplete or contradictory, `next_allowed_action`
   is `HOLD / RECONCILE`, never `SEND`.
8. A fresh inbound, a newly provider-sent message, a changed draft, recipient-routing
   mutation, or a materially changed ask invalidates the old capsule and requires rebuild.

This capsule is the session-to-session operational view. The generic Red Dog native
correspondence store is the durable M2M continuity layer; this YUMORI skill adds project
voice, routing, CRM and campaign semantics. The capsule intentionally references stable
provider/CRM IDs and compact ask state rather than copying correspondence prose.
## Gmail filing and queue semantics

Use the established YUMORI labels and current live evidence.

- `YUMORI`: clear YUMORI.me stakeholder/project correspondence.
- `YUMORI/Responses`: genuine stakeholder reply or substantive project correspondence.
- `YUMORI/Action Required`: current evidence shows 0102 / the monk owes a response, document, decision, meeting action, deadline action, or delivery repair.
- `YUMORI/Waiting`: latest verified sent request where the next step belongs to the recipient.

Do not turn automated acknowledgments, newsletters, GitHub/service notices, or resolved declines into stakeholder-response/action state.

Preserve unread state unless the task explicitly authorizes changing it.

## Capital network graph / warm-path expansion

Capital discovery belongs in the existing CONTACTS workbook. Do **not** create a
parallel investor spreadsheet, VC rolodex, or email-enrichment database.

Canonical roles:

- `Capital Targets` = organizations/funds/platforms. Classify capital type, geography,
  direct data-center/AI-infrastructure evidence, Japan/APAC evidence, scale evidence,
  fit lane, status, named leads, warm path, sources, and next action.
- `Capital People` = people graph. Record current role evidence, LinkedIn/profile URL,
  relationship state, connection date when provider-verified, target IDs, capital
  relevance, and next action.
- `LinkedIn` = provider-visible first-degree/contact-info evidence. A row here does
  not itself authorize outreach.
- `Contacts` / Email Log / Action Queue / Correspondence Routing remain the
  correspondence authority once outreach is contemplated.

### Relationship evidence classes

Use exact relationship states:

- `1ST_DEGREE_VERIFIED` — provider evidence or 012-supplied LinkedIn UI proves an
  accepted first-degree connection.
- `WARM_HISTORY` — prior investor/adviser relationship is evidenced, but current
  LinkedIn degree/contact route is not yet verified.
- `WARM_ADJACENT` — an active partner/counterparty can plausibly introduce a target;
  no direct relationship is claimed.
- `PUBLIC_TARGET` — named public professional only; no relationship is inferred.
- `NEEDS_NETWORK_RECON` — 012 reports a network path but provider evidence has not
  yet established it.

Do not promote follows, profile views, recommendations, “people you may know,” group
membership, or news-digest mentions into first-degree evidence.

### Mutual-network crawl

When browser-capable Work is available, prefer a bounded warm-path crawl over cold
mass outreach:

1. start from `1ST_DEGREE_VERIFIED` bridge nodes;
2. inspect P0/P1 `Capital Targets` named decision-makers;
3. record only mutual connections actually visible in the authenticated UI;
4. reverify current company/title before using historical acceptance-mail titles;
5. capture Contact info only when LinkedIn exposes it to 012's authenticated account;
6. store exact visible email/website/profile URL with observation date and source;
7. never guess email patterns or use enrichment that bypasses LinkedIn visibility;
8. rank one-hop warm paths above cold targets when fit evidence is otherwise comparable.

A contact-info email is a route fact, not permission to send. Before any message or
email, run the normal correspondence-state capsule, Sent-first reconciliation,
routing/preflight, and duplicate/follow-up gates.

### Capital-fit classes

Assign one primary class to each organization:

`DIRECT_DC_EQUITY`, `INFRASTRUCTURE_PE`, `SOVEREIGN_PENSION`,
`PROJECT_FINANCE_DEBT`, `STRATEGIC_CORPORATE`, `OPERATOR_JV`,
`VC_GROWTH_PLATFORM`, `ANGEL_PREDEVELOPMENT`, or `INTRODUCTION_BRIDGE`.

Also record Japan direct evidence as `YES / NO / ADJACENT` and Phase-1 fit as
`HIGH / MEDIUM / LOW / UNKNOWN`. Fame, fund size, or a mutual connection does not
by itself make a target HIGH fit.

### Work / browser boundary

The normal text/connector path may research organizations, verify named public
profiles, inspect Gmail LinkedIn acceptance receipts, and update the CRM. If the
task requires clicking LinkedIn mutual connections, connection controls, or
Contact info panels that are not exposed through the connector, hand that bounded
UI work to ChatGPT Work / Cloud Browser.

Discovery does not authorize:
- bulk connection requests;
- bulk messages;
- automatic email sends;
- scraping hidden contact data.

If connection requests are desired, Work must return a `CONNECT_CANDIDATE` list
with target, current role, mutual path, rationale, proposed short note, and existing
direct-route state. Sending remains a separately authorized effect.

## Structured-sheet integrity

Before writing Contacts, Email Log, Action Queue, Correspondence Routing, or another structured Sheet:

1. Read the live header row.
2. Read the exact target row/range.
3. Build the write map by header name.
4. Capture rollback values.
5. Inspect formulas / ARRAYFORMULA spill ownership with CellData metadata.
6. Never write into active formula-owned output cells.
7. Write canonical datetime fields as real date-time values with proper DATE_TIME formatting, never text timestamps.
8. Prefer small atomic updates.
9. Immediately read back exact modified fields and relevant formula source/projection cells using:
   `formattedValue,userEnteredValue,effectiveValue`
10. Roll back on alignment, formula, typed-date, or projection failure.

## Moshpit integration

Use `yumori_moshpit` after material campaign events.

- Campaign history / monk activity -> YUMORI Moshpit.
- Agent error / repair / reusable operating lesson -> 0102 Moshpit.
- Do not publish private addresses, BCC, full bodies, or unrelated technical alerts to campaign/public logs.
- Mark monk-reported activity as `REPORTED_BY_012` unless independently verified.

## Recursive self-improvement

A correspondence run is not complete when a meaningful failure is merely noticed.

When a run discovers or causes a meaningful:
- error;
- near-miss;
- bad assumption;
- duplicate;
- route-consent problem;
- stale queue state;
- integrity problem;
- coverage failure;
- repeated wording/voice defect;
- generalizable improvement;

then:

1. record concise evidence in `0102 Moshpit — Agent Learning & Action Log`;
2. identify the root cause;
3. change the prompt / Skillz / test / code that allowed the defect, or record a concrete reason no rule change is appropriate;
4. add or update a regression test when the failure is mechanically testable;
5. mark repeated or structural lessons `RED DOG CANDIDATE`;
6. verify the changed operating rule in the next relevant event.

Routine successful runs do not create learning entries.

## Dependencies

- `recipient_document_audit` for audience fit, total reading burden, exact PDF/export
  visual review, internal-artifact removal and review-only release control.

- `reddog_correspondence_state` for provider-delta continuity, stable ask IDs, watermarks and private runtime persistence.
- `yumori_moshpit` for campaign-vs-agent logging.
- `fukui_city_procedure` for municipal procedure lanes and official-form fidelity.
- `reddog_recipient_preflight` for consequential outbound recipient authorization.
- WSP 15 for priority / action.
- WSP 95 for Skillz reuse / extension before proliferation.
- WSP 97 for dialectic self-audit.

## Fukui City / Council handoff

When correspondence is to Fukui City or Fukui City Council:

1. load `fukui_city_procedure`;
2. classify the exact lane (petition, PPP/PFI, disclosure, procurement, meeting, routing, audit/legal);
3. use the current official form/process where one exists;
4. keep procedural state separate from correspondence state;
5. still apply this parent voice, routing, Sent-first, reconciliation, and recursive-learning contract.

## Authority boundary

This Skillz grants no independent Gmail / Drive / GitHub / legal / financial authority.

Execution remains bounded by:
- the current user instruction;
- connector permissions;
- recipient routing consent;
- procedure/form requirements;
- WSP controls;
- applicable platform and safety policy.

Google Sheets / Docs remain human-facing working projections. They are not required as Red Dog's memory substrate and must be rebuildable from provider truth plus native runtime state.

Documentation is not proof that an action was sent, filed, received, accepted, or deployed.