---
name: fukui-city-procedure
description: Apply current verified Fukui City and Fukui City Council procedures for YUMORI/Sukatto Land matters, including official forms, 請願/陳情, PPP/PFI proposal routing, information disclosure, procurement milestones, meetings, correspondence routing, and audit/legal handoff. Use whenever 0102 must determine what formal city procedure applies, which exact official form to use, who may receive it, when it is due, or what step follows.
metadata:
  homepage: https://github.com/FOUNDUPS/Foundups-Agent/tree/main/modules/foundups/esingularity/skills/fukui-city-procedure
---

# Fukui City procedure — YUMORI / Sukatto Land

Owner: `esingularity_001` in `FOUNDUPS/Foundups-Agent`.

This skill is the durable **procedure layer** for 0102/Red Dog when dealing with Fukui City, Fukui City Council, and related formal municipal processes. It prevents each session from rediscovering the same rules and, equally importantly, prevents stale remembered rules from being treated as current law or current case state.

## Prime directive

**Procedure knowledge and live case state are separate.**

- This file stores reusable procedure, source hierarchy, verification rules, form fidelity, routing rules, and state transitions.
- Gmail, Drive, the YUMORI Contacts/Correspondence Routing sheet, Email Log, Action Queue, Moshpit, and current official websites hold live case state.
- Never copy private addresses, BCC lists, personal data, account secrets, or confidential legal material into this public skill.
- Never infer that a historical route, deadline, form, office, or eligibility rule is still current. Re-verify it before consequential action.

## Source hierarchy

For a substantive current procedural claim, verify in this order:

1. **Current official Fukui City / Fukui City Council page or downloadable official form**
2. **Applicable law / regulation / ordinance / council rule** from e-Gov or Fukui City's official rules service
3. **Current written direction from the responsible Fukui City organizational office**
4. **Current Cabinet Office / national PPP-PFI guidance**, when relevant
5. YUMORI's verified Gmail/Drive records for case history
6. Secondary reporting only as context, never as the sole source for a filing rule

If sources conflict, stop and identify the conflict. Do not silently choose the convenient interpretation.

## Official-form fidelity guard — non-negotiable

When an authority publishes an official form or template, **that exact official file is the submission master**.

Do not:
- regenerate, redraw, re-typeset, simplify, translate, or substitute a look-alike;
- change field order, labels, tables, checkboxes, margins, page structure, signature blocks, required wording, or version/year;
- reuse a prior-year form without live verification;
- assume a Google Doc recreation is equivalent to the authority's Word/PDF file.

Do:
1. verify the official source URL, title, issuing authority, version/year, and current submission instructions;
2. download/use the exact official file;
3. fill only fields the form permits;
4. put longer argument/evidence in attachments only if the procedure allows attachments;
5. compare the completed document against the untouched official source before filing;
6. preserve the original official binary as provenance.

A format conversion may be used as a working copy only when its structure is visually verified against the official source and the authority accepts the resulting format. The official source remains the master.

If the exact official file cannot be retrieved or edited, set:
`BLOCKED_ON_OFFICIAL_TEMPLATE`
and prepare only a field-by-field content map. Never create a substitute that could be mistaken for the official form.

## Procedure classifier

Before drafting or acting, classify the request into one or more independent lanes:

| Lane | Purpose | Primary authority |
| --- | --- | --- |
| `COUNCIL_PETITION` | 請願 / 陳情 to Fukui City Council | Council Secretariat / council rules |
| `PPP_PFI` | Private PPP/PFI proposal, pre-consultation, VFM/PSC route | Executive side / facility or project office |
| `ASSET_PROPOSAL` | 財産有効活用民間提案制度 for specifically listed property | Facility Utilization Promotion Division + current call |
| `INFO_DISCLOSURE` | Obtain public records | Information disclosure procedure / relevant implementing body |
| `PROCUREMENT` | Budget → design → survey → tender → award → contract → works | City procurement/contract notices + responsible office |
| `MEETING_ACCESS` | Appointment, site access, technical inspection, hearing | Responsible office / Council Secretariat |
| `ROUTING` | Correct organizational vs personal correspondence channel | Correspondence Routing + verified office instruction |
| `AUDIT_LEGAL` | Resident audit, administrative appeal, litigation/counsel handoff | Audit office / applicable law / counsel |

Do not collapse these lanes. A Council 陳情 is not a PPP/PFI proposal. A budget vote is not a demolition contract. An information-disclosure appeal is not an appeal of a council petition deadline.

## Lane A — Council 請願 / 陳情

Current source anchor:
https://www.city.fukui.lg.jp/sisei/gikai/seigan/p004047.html

As verified 2026-09-18, Fukui City Council states:
- 請願 has an introducing council member; 陳情 does not.
- The document must be in Japanese and include the subject, purpose, submission date, petitioner address, and signature or name/seal; corporate/group submissions use the entity name, office location, and representative signature/name-seal.
- Direct submission is to the Council Secretariat at City Hall, with advance scheduling.
- Mailed items are handled differently from direct submission; verify the current page before choosing mail.
- Petitions/陳情 are accepted on an ongoing basis.
- The regular-session cutoff determines **which session examines the item**; missing a session cutoff does not by itself mean the Council will never accept the document.

Every execution must re-open the current page and exact downloadable form before advising or filing.

### Council state machine

`DRAFT -> OFFICIAL_TEMPLATE_VERIFIED -> APPOINTMENT_CONFIRMED -> HAND_DELIVERED -> RECEIPT_CONFIRMED -> SESSION_ASSIGNED -> COMMITTEE/COUNCIL_HANDLING -> RESULT_RECORDED`

Never mark `HAND_DELIVERED` or `RECEIPT_CONFIRMED` from an email saying "we plan to submit."

## Lane B — PPP/PFI

Current source anchors:
- https://www.city.fukui.lg.jp/sisei/plan/reform/p015778.html
- https://www.city.fukui.lg.jp/sisei/plan/reform/p015778_d/fil/PFIgaiyou.pdf

The City's published PPP/PFI framework includes private proposals at the project-origination stage and describes simplified/detailed review including quantitative VFM and qualitative review. Treat that as a framework, **not automatic eligibility or acceptance of a particular YUMORI filing**.

For Sukatto Land:
1. determine whether the City will accept the material under PFI Act Article 6, another PPP/PFI path, a sounding/pre-consultation route, or another process;
2. obtain the responsible office, required proposer legal status, exact required materials, submission method, confidentiality treatment, review body, and schedule **in writing**;
3. keep Council petition handling separate from executive PPP/PFI processing;
4. do not claim a PPP/PFI proposal has been formally filed until the responsible City office identifies/accepts the route and a submission receipt exists.

## Lane C — 財産有効活用民間提案制度

Current call:
https://www.city.fukui.lg.jp/sisei/plan/reform/p073300.html

**Dated case note — verify again before use:** on 2026-09-18 the FY2026 call listed only 旧下宇坂小学校 and 旧羽生小学校. Sukatto Land Kuzuryu was not listed. Therefore 0102 must not place Sukatto Land onto the FY2026 program's form or claim eligibility unless Fukui City expressly confirms a lawful route.

The current call also requires pre-consultation before proposal submission and limits proposal scope/eligibility. Always read the live call, guidelines, property list, and official forms together.

## Lane D — information disclosure

Current source:
https://www.city.fukui.lg.jp/sisei/kisoku/koukai/joho.html

As verified 2026-09-18:
- the process uses the official `公文書開示請求書` or, depending on eligibility, `公文書開示申出書`;
- forms differ by implementing body, so identify whether the target records are held by the Mayor, Council, Audit Committee, etc.;
- current submission methods include in-person, mail, fax, and online routes described on the official page;
- the City says a decision is ordinarily made within 15 days of a disclosure request, subject to extension;
- an appeal against a non-disclosure decision is a separate administrative-review process with its own deadline.

**Do not treat a previous free-form email request as the statutory filing** merely because the City acknowledged receiving the email.

### Disclosure state machine

`RECORD_SET_DEFINED -> IMPLEMENTING_BODY_IDENTIFIED -> OFFICIAL_FORM_VERIFIED -> REQUESTER_ELIGIBILITY_CHECKED -> FILED -> RECEIPT/DATE_CAPTURED -> DECISION_PENDING -> DISCLOSED/PARTIAL/NONDISCLOSED -> APPEAL_WINDOW_IF_NEEDED`

## Lane E — procurement and irreversible-action tracking

Always decompose:
`BUDGET_PROPOSED -> BUDGET_APPROVED -> DESIGN/SURVEY_AUTHORIZED -> PROCUREMENT_PREP -> TENDER/REQUEST -> BID/SELECTION -> PROVISIONAL_AWARD -> CONTRACT_EXECUTED -> WORK_NOTICE -> PHYSICAL_WORK`

Rules:
- A budget vote is not proof of a demolition contract.
- A design or asbestos-survey contract is not proof that the main demolition contract has been executed.
- A tender notice is not a contract award.
- A contract award is not physical demolition.
- Record the **exact official artifact and date** supporting each transition.
- For Sukatto Land, monitor procurement, contract-award, council-agenda/resolution, and responsible-department notices separately.

When the user asks "how much time do we have?", answer from the latest verified irreversible milestone, not from the budget date alone.

## Lane F — routing and correspondence

1. Consult the live YUMORI Correspondence Routing state before addressing City mail.
2. Person route and organization route are separate states.
3. An explicit request not to address/CC a personal mailbox is binding:
   `DO_NOT_ADDRESS_OR_CC / PERSONAL_ROUTE_CLOSED`.
4. Historical direct correspondence does not reopen a closed route.
5. If the City directs future correspondence to an organizational mailbox, use that organization route.
6. Search Sent before claiming a request is unsent or unanswered.
7. Preserve message_id/thread_id and verify send receipts before logging a send.
8. Acknowledgment of receipt is not substantive resolution.
9. Never infer delivery success only from absence of a bounce.

## Lane G — meetings, site access, and verbal statements

- A meeting, hallway conversation, protest interaction, or business card creates evidence of contact, not automatically a formal filing or institutional decision.
- After consequential verbal guidance, seek concise written confirmation from the responsible organizational office.
- Separate "official said X verbally" from "City formally decided X."
- For site/technical access, obtain the required appointment, safety conditions, authority, and permitted scope in writing before representing access as approved.

## Lane H — audit/legal escalation

Current resident-audit source:
https://www.city.fukui.lg.jp/sisei/kansa/juminkansa/jyukanqa.html

Fukui describes resident audit as a mechanism for alleged illegal/improper **financial/accounting acts** or failures that cause or risk municipal loss; it is not a generic appeal from political disagreement or a Council vote. The official page also imposes standing, evidence, target-act, and timing requirements.

Rules:
- never label a Council deadline challenge, PPP dispute, or policy disagreement a resident-audit claim without matching the statutory financial-act requirements;
- use the exact official audit form where applicable;
- distinguish `possible issue for counsel` from `valid claim`;
- novel legal arguments, litigation, injunction strategy, or contested interpretation -> `ESCALATE_TO_COUNSEL`.

## Standard execution workflow

For every Fukui City procedural task:

1. **Recover live case state** only from the systems relevant to the request: Gmail threads/Sent, Drive master docs, Contacts/Correspondence Routing, Email Log, Action Queue, Moshpit.
2. **Classify lane(s)** using the table above.
3. **Verify the current official source** online. Record page title, authority, URL, last-updated date when shown, and verification date.
4. **Locate the exact official form/template** if the procedure has one.
5. **Check authority and requester identity requirements**. Do not invent addresses, titles, legal status, signatures, seals, or representative authority.
6. **Check deadline semantics**: submission deadline, session-assignment cutoff, response deadline, appeal deadline, procurement date, and physical-work date are different clocks.
7. **Prepare a field map** from verified case facts to exact official fields.
8. **Execute only within granted authority**. If signature, seal, physical delivery, payment, or identity proof is needed, mark the human step explicitly.
9. **Verify outcome**: receipt, submission number, Sent MID/TID, appointment confirmation, or official docket state.
10. **Reconcile records** across Gmail -> Email Log -> Contacts -> Action Queue -> Moshpit where applicable.
11. **Promote learning**: if a new generalizable rule is discovered, update this skill; case-only facts stay in case records.

## Required output for procedure analysis

Use this compact schema:

```text
PROCEDURE:
AUTHORITY:
CURRENT OFFICIAL SOURCE:
VERIFIED:
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

If several lanes apply, produce one block per lane and then a short dependency order.

## Stop conditions

Stop and escalate instead of guessing when:
- the official form/version cannot be retrieved;
- two official sources conflict;
- requester standing or representative authority is unclear;
- a personal route is closed and no verified organization route is available;
- the action would create a new legal/financial commitment;
- a signature, seal, in-person identity step, or physical delivery is required;
- the user asks for a legal conclusion that requires counsel;
- the current procurement milestone cannot be verified.

## Regression tests / examples

1. **"Fill the Fukui 陳情 form."** -> retrieve exact current Council form; no recreated Google Doc; field map first.
2. **"We missed the September cutoff, can we still submit?"** -> distinguish acceptance from session-assignment timing; verify current Council page.
3. **"File the PPP proposal using the 2026 asset-proposal form."** -> check current property list; if Sukatto is not listed, do not misuse that form; seek correct PPP route.
4. **"City acknowledged our records email, so disclosure is filed."** -> fail; acknowledgment != formal information-disclosure filing.
5. **"Budget passed, so demolition contract exists."** -> fail; verify procurement state transitions.
6. **"Email Yoshikawa again because he answered before."** -> fail if current routing state says personal route closed.
7. **"Appeal the three-day petition window."** -> identify which procedure actually has an appeal mechanism; do not import information-disclosure appeal rights into Council petition procedure.
8. **"Use resident audit to reverse the vote."** -> fail as stated; first test resident standing + specific financial/accounting act + alleged illegality/impropriety + municipal loss + evidence, then escalate legal merits.

## Maintained official-source registry

These are discovery anchors, **not permanent truth**. Re-open before action.

- Council 請願・陳情: https://www.city.fukui.lg.jp/sisei/gikai/seigan/p004047.html
- Facility management / PPP-PFI: https://www.city.fukui.lg.jp/sisei/plan/reform/p015778.html
- PPP/PFI overview PDF: https://www.city.fukui.lg.jp/sisei/plan/reform/p015778_d/fil/PFIgaiyou.pdf
- FY2026 asset-use private proposal: https://www.city.fukui.lg.jp/sisei/plan/reform/p073300.html
- Information disclosure: https://www.city.fukui.lg.jp/sisei/kisoku/koukai/joho.html
- Resident audit Q&A: https://www.city.fukui.lg.jp/sisei/kansa/juminkansa/jyukanqa.html

## Red Dog / 0102 discovery

Trigger on obvious requests such as:
- "deal with Fukui City"
- "what form do we file"
- "petition / 陳情 / 請願"
- "PPP/PFI route"
- "information disclosure"
- "city deadline"
- "procurement / demolition contract"
- "what can we do after the vote"
- "official Fukui form"

Speech-recognition variants of YUMORI still resolve to YUMORI. This skill does not grant new credentials or legal authority. It tells the executing agent how to recover current evidence, verify the governing procedure, use the exact form, and keep case state synchronized.
