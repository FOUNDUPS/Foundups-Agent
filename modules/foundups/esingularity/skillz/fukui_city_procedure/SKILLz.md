---
name: fukui_city_procedure
description: Verify and execute Fukui City / Fukui City Council procedures for YUMORI and Sukatto Land without relearning or guessing forms, routes, deadlines, or procurement state.
version: 0.2.0
author: 0102
agents: [0102, qwen, gemma]
primary_agent: 0102
intent_type: DECISION
promotion_state: prototype
pattern_fidelity_threshold: 0.99
domain: foundup_campaign_operations
category: workflow
wsp_chain: [WSP_00, WSP_15, WSP_22, WSP_50, WSP_95, WSP_97]
evals:
  - current_primary_source_required
  - official_form_binary_fidelity
  - independent_procedure_lane_classification
  - recipient_preflight_required_for_correspondence
  - budget_not_contract
  - acknowledgment_not_statutory_filing
  - routing_consent_enforced
---

# Fukui City procedure — YUMORI / Sukatto Land

## Purpose

Provide a durable procedure layer for 0102 / Red Dog when dealing with Fukui City,
Fukui City Council, and related municipal processes.

This skill prevents two opposite failures:

1. relearning the same municipal procedure from scratch every session; and
2. treating remembered procedure as current after the City, Council, form, deadline,
   office, or case state has changed.

Durable procedure lives here. Live case state remains in Gmail, Drive, the YUMORI
Contacts / Correspondence Routing sheet, Email Log, Action Queue, Moshpit, and current
official websites.

## Source hierarchy

For consequential current procedure, verify in this order:

1. current official Fukui City / Fukui City Council page and exact downloadable form;
2. applicable ordinance, rule, law, council rule, or e-Gov source;
3. current written direction from the responsible organizational office;
4. current Cabinet Office / national PPP-PFI guidance when relevant;
5. verified YUMORI Gmail / Drive case history;
6. secondary reporting only as context.

If authoritative sources conflict, stop and surface the conflict. Do not choose the
convenient interpretation.

## Official-form fidelity — fail closed

When an authority publishes a Word, PDF, web form, or other official template, that
exact current official artifact is the submission master.

Never:
- regenerate, redraw, re-typeset, simplify, translate, or substitute a look-alike;
- alter field order, labels, tables, checkboxes, page structure, signature blocks,
  required wording, or version/year;
- reuse a prior-year form without live verification;
- assume a recreated Google Doc is equivalent to the official file.

Always:
1. verify official source URL, title, issuing authority, version/year, and submission method;
2. use the exact official file or live form;
3. fill only fields permitted by that surface;
4. add attachments only where the instructions permit them;
5. compare the completed artifact with the untouched official source;
6. preserve the original official binary / source URL as provenance.

If the exact official artifact cannot be retrieved or edited safely, set
`BLOCKED_ON_OFFICIAL_TEMPLATE` and prepare only a field map. Do not create a substitute
that could be mistaken for the official form.

## Procedure lanes

Classify the task before acting:

| Lane | Purpose |
| --- | --- |
| `COUNCIL_PETITION` | Fukui City Council 請願 / 陳情 |
| `PPP_PFI` | executive-side PPP/PFI proposal, Article 6 or other route |
| `ASSET_PROPOSAL` | 財産有効活用民間提案制度 for currently listed assets |
| `INFO_DISCLOSURE` | formal public-record disclosure |
| `PROCUREMENT` | budget through physical work |
| `MEETING_ACCESS` | appointments, hearings, site / technical access |
| `ROUTING` | person vs organization correspondence route |
| `AUDIT_LEGAL` | resident audit / legal escalation / counsel handoff |

Do not collapse lanes. A Council 陳情 is not a PPP/PFI filing. An information-disclosure
appeal is not an appeal of a Council filing deadline. A budget vote is not a demolition
contract.

## Council 請願 / 陳情

Discovery anchor:
https://www.city.fukui.lg.jp/sisei/gikai/seigan/p004047.html

Before each use, re-open the live page and exact downloadable form.

Track state as:

`DRAFT -> OFFICIAL_TEMPLATE_VERIFIED -> PRIOR_CONSULTATION_IF_REQUIRED -> APPOINTMENT_CONFIRMED -> HAND_DELIVERED -> RECEIPT_CONFIRMED -> SESSION_ASSIGNED -> COUNCIL_HANDLING -> RESULT_RECORDED`

Never infer HAND_DELIVERED or RECEIPT_CONFIRMED from an email saying the Commission
plans or wants to submit.

Distinguish:
- whether the Council accepts documents at all;
- the cutoff controlling which regular session handles them;
- any required prior consultation;
- actual hand delivery / receipt;
- committee / plenary treatment.

## PPP/PFI

Discovery anchors:
- https://www.city.fukui.lg.jp/sisei/plan/reform/p015778.html
- https://www.city.fukui.lg.jp/sisei/plan/reform/p015778_d/fil/PFIgaiyou.pdf

The published framework may recognize private proposals, simplified review, detailed
review, VFM, or other PPP/PFI steps. That does not prove that a specific YUMORI package
has been formally accepted.

For Sukatto Land, obtain in writing:
- exact receiving route;
- responsible office;
- whether PFI Act Article 6 or another PPP route applies;
- required proposer legal form / authority;
- exact required materials and format;
- confidentiality treatment;
- review body;
- review schedule;
- receipt / case identifier after filing.

Do not mark `FORMALLY_FILED` until the responsible office has accepted the route and a
submission receipt exists.

## 財産有効活用民間提案制度

Discovery anchor:
https://www.city.fukui.lg.jp/sisei/plan/reform/p073300.html

The property list and eligibility are live facts. Re-open the current call, guidelines,
property list, consultation requirements, and exact forms together before use.

Never place Sukatto Land on a current-year program form merely because it appeared in a
prior-year program. If the current property list excludes it, seek the correct PPP route
instead of misusing the form.

## Information disclosure

Discovery anchor:
https://www.city.fukui.lg.jp/sisei/kisoku/koukai/joho.html

Track state as:

`RECORD_SET_DEFINED -> IMPLEMENTING_BODY_IDENTIFIED -> OFFICIAL_FORM_VERIFIED -> REQUESTER_ELIGIBILITY_CHECKED -> FILED -> RECEIPT_CAPTURED -> DECISION_PENDING -> DISCLOSED/PARTIAL/NONDISCLOSED -> REVIEW_OR_APPEAL_WINDOW_IF_APPLICABLE`

A free-form email asking for records is not automatically the statutory request merely
because the City acknowledged receiving it.

Identify the correct implementing body before choosing a form or filing route.

## Procurement / irreversible-action state

Always decompose:

`BUDGET_PROPOSED -> BUDGET_APPROVED -> DESIGN_OR_SURVEY_AUTHORIZED -> PROCUREMENT_PREP -> TENDER_OR_REQUEST -> BID_OR_SELECTION -> PROVISIONAL_AWARD -> CONTRACT_EXECUTED -> WORK_NOTICE -> PHYSICAL_WORK`

Rules:
- budget approval is not a demolition contract;
- design / asbestos survey is not the main demolition contract;
- tender is not award;
- award is not physical work;
- every transition needs an exact official artifact and date.

When asked "how much time do we have?", answer from the latest verified irreversible
milestone, not from the budget date alone.

## Canonical contact-store integrity

- `Contacts` and `Correspondence Routing` are the canonical recipient state.
- Projection tabs such as Media, Government & Council, Universities & Research,
  Business & Investors, Community & NGOs, Technical & Infrastructure,
  Hospitality & Tourism, and Arts & Culture are **read-only generated views**.
- Never create or edit a contact directly in a projection spill range.
- If a projection reports `#REF!` because curated rows block an ARRAYFORMULA/QUERY,
  first migrate any unique data into canonical Contacts with unique Contact IDs,
  then clear only the projection blocker and verify both source and projection.
- A projection row must never reuse a Contact ID that belongs to a different
  canonical Contacts identity.

## Routing and outbound correspondence dependency

All Fukui City / Council email or addressed-document actions must first apply the
repository-owned YUMORI.me correspondence parent:

`modules/foundups/esingularity/skillz/yumori_contact_ledger/SKILLz.md`

That parent owns the canonical 0102 proxy voice, third-person monk reference,
Sent-first reconciliation, routing consent, receipt reconciliation, and recursive
learning contract.

Consequential outbound actions must also apply the repository-owned recipient guard:

`modules/communication/moltbot_bridge/skillz/reddog_recipient_preflight/SKILLz.md`

The procedure skill never authorizes a recipient or overrides the parent voice/routing
contract by itself.

Before finalizing To/CC/BCC:
1. resolve every intended identity against the live YUMORI Contacts sheet;
2. read the current Correspondence Routing row for the same Contact ID;
3. distinguish person vs organization route;
4. enforce route closure / BCC-only / organization-only policy;
5. independently reconstruct the exact transaction;
6. compare exact characters;
7. block on unknown, conflicting, stale, near-match, closed, or duplicate coverage;
8. after send, read back exact provider To/CC/BCC and compare with the receipt.

Historical correspondence does not reopen a closed personal route.

## Meetings, site access, verbal statements

A meeting, hallway conversation, protest interaction, or business card proves contact,
not automatically a formal filing or City decision.

For consequential verbal guidance:
- seek written confirmation through the verified organization route;
- keep "official said verbally" distinct from "City formally decided";
- for site / technical access, obtain the authority, appointment, safety conditions, and
  permitted scope before describing access as approved.

## Audit / legal escalation

Discovery anchor:
https://www.city.fukui.lg.jp/sisei/kansa/juminkansa/jyukanqa.html

Resident audit is not a generic mechanism to reverse political disagreement. Before
treating it as applicable, verify current standing, the specific financial/accounting
act or omission, alleged illegality/impropriety, municipal loss/risk, timing, evidence,
and exact official form.

Novel legal conclusions, injunction strategy, contested statutory interpretation, or
litigation posture -> `ESCALATE_TO_COUNSEL`.

## Standard execution workflow

1. Recover only the live case state relevant to the task.
2. Classify the procedure lane(s).
3. Re-open the current official source.
4. Locate and verify the exact official form if one exists.
5. Check requester identity, authority, address/signature/seal requirements without inventing them.
6. Separate every deadline clock: session cutoff, filing deadline, response deadline,
   procurement milestone, appeal window, physical-work date.
7. Build a field map from verified case facts.
8. If correspondence is involved, run `reddog_recipient_preflight`.
9. Execute only within granted authority; expose required physical/signature human steps.
10. Verify receipt / docket / MID-TID / appointment / provider read-back.
11. Reconcile Gmail -> Email Log -> Contacts -> Action Queue -> YUMORI Moshpit where applicable.
12. Promote a genuinely reusable new procedure rule back into this skill.

## Required analysis output

```text
PROCEDURE:
AUTHORITY:
CURRENT OFFICIAL SOURCE:
VERIFIED_AT:
OFFICIAL FORM:
SUBMISSION METHOD:
DEADLINE / CLOCK:
LIVE CASE STATE:
WHAT THIS ACTION DOES:
WHAT IT DOES NOT DO:
BLOCKERS:
NEXT FORMAL STEP:
EVIDENCE / RECEIPT:
```

## Stop conditions

Stop rather than guess when:
- the current official form/version cannot be established;
- authoritative sources conflict;
- requester standing / representative authority is unclear;
- a personal route is closed and no verified organization route exists;
- a signature, seal, in-person identity step, payment, or physical delivery is required;
- the action creates a new material legal/financial commitment;
- current procurement milestone cannot be verified;
- a legal conclusion requires counsel.

## Regression scenarios

- "Fill the Fukui 陳情 form." -> exact official template first; no recreated Google Doc.
- "We missed this session cutoff, so submission is impossible." -> verify acceptance and
  session-assignment rules separately.
- "Use the current property-proposal form for Sukatto." -> verify the current property
  list before using any form.
- "The City acknowledged our records email, so disclosure is filed." -> fail.
- "Budget passed, therefore demolition is contracted." -> fail.
- "Email the old personal City mailbox again." -> fail if routing says closed.
- "Copy the same media BCC list from last time." -> fail; re-resolve each recipient.
- "Appeal the petition deadline." -> identify the actual procedure and appeal mechanism;
  never import another lane's appeal rights.
