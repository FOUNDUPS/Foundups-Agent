---
name: recipient_document_audit
description: Audit recipient-facing proposals, PDFs, forms, presentations and linked document packages for audience fit, evidence, repetition, internal artifacts and final rendering before correspondence release.
version: 0.1.0
author: 0102
agents: [0102]
primary_agent: 0102
intent_type: DECISION
promotion_state: prototype
domain: foundup_campaign_operations
category: workflow
wsp_chain: [WSP_15, WSP_50, WSP_95, WSP_97]
evals:
  - whole_package_reading_burden
  - exact_export_visual_review
  - audience_action_fit
  - no_internal_artifacts
  - refusal_and_draft_only_preserved
  - audit_receipt_not_send_authority
---

# Recipient document audit

Run this subordinate skill from `yumori_contact_ledger` and
`fukui_city_procedure` whenever an outbound contains or links a proposal,
PDF, form, presentation, briefing, or other substantive document. Apply it to
the exact recipient-facing package, including forwarded and quoted material.
Reuse the available PDF/document rendering skills; do not build a new renderer.

## 1. Establish the reader and task

Record the receiving office/person's role, language, latest request, permitted
procedure and the single decision or response needed now. Distinguish a clerk
checking procedure, an elected decision-maker, a technical reviewer and a funder.
Read the latest inbound and Sent state before drafting a reply to criticism.

Honor `DO_NOT_SEND` / review-only instructions even after every audit passes.
A request to circulate an original petition is not permission to circulate a
new dossier. A refusal of supplements stays binding until the recipient changes
it; produce an internal revision, not another unsolicited attachment or link.

## 2. Inventory the entire package

Inventory the new email body, provider-added quote/forward history, every
attachment and every linked document the reader is asked to consult. Resolve
redirects and verify the destination/version. Label each item REQUIRED,
OPTIONAL_REFERENCE or INTERNAL_ONLY, with its purpose and observed page count.
Record unknown counts as UNKNOWN; never invent a total. For changing cloud
documents, record revision/export time rather than attributing today's count to
an earlier send. Duplicate Word/PDF formats are one content item but two files;
state this explicitly and avoid requiring both formats to be read.

Do not hide an oversized package behind a short cover email or an optional-link
label. Remove unnecessary references from the outbound altogether. The requested
action must be understandable without opening a technical dossier.

## 3. Apply WSP 97 at sentence and package level

- Lead with the requested action and only the facts needed to decide it.
- For an unsolicited official briefing, default to one readable A4 page. This is
  an editorial default, not a legal rule: preserve official templates and every
  required field/attachment, and allow a longer specifically requested technical
  report with a concise executive entry and a documented reason.
- Apply the three questions to every section, claim, image and link: Do we need
  it for this decision? Can the reader afford the attention? Can we omit it now?
- Remove repetition within and across documents; retain unique required facts,
  assumptions, material risks, sources and uncertainty. Do not meet a page limit
  by shrinking text or deleting inconvenient qualifications.
- Replace internal jargon with plain recipient-language wording. Expand an
  unavoidable abbreviation at first use in each independently read document.
  A glossary at the end does not repair an unexplained opening. Avoid internal
  protocol names, agent labels, Site/Priority codes and planning shorthand unless
  the recipient needs them and their meaning is explained.
- Distinguish current facts, proposals, reported statements and unverified
  assumptions. Do not promote an inquiry to approval, a prospective partner to
  a participant, automation to a completed feasibility study, or projections to
  guaranteed revenue. Preserve separate procedure lanes and unconfirmed capacity.
- When correcting criticism, own the specific failure without an invented excuse.
  Keep a recipient's complaint separate from independently confirmed defects.

## 4. Audit content and the final artifact separately

Content pass: inspect all text, tables, captions, references, links, comments,
tracked changes, notes and metadata that may reach the reader. Flag placeholders,
TODOs, duplicate headings/sections, raw Markdown/HTML, tool citation tokens,
unresolved field codes, internal instructions, stale dates and contradictory
claims. Remove private data not needed by this recipient. Preserve legally or
procedurally required wording and approved disclosures.

Artifact pass: export the exact final file, count its actual pages, render every
page and inspect at readable scale. Check Japanese glyphs/fonts, clipping,
overlap, orphan/blank pages, image legibility, table breaks, headers/footers and
links. Text extraction alone never proves visual quality. Scan hidden comments
and annotations separately; rendering may not display them. Record uninspected
surfaces as UNKNOWN, never PASS. Use OCR when needed, but inspect the images too.

For an official form, compare the completed artifact with the untouched official
source. Preserve labels, structure, required content and permitted field limits.
For a linked native document, audit its current reader view/export as well as
the link's access and target; do not rely on a private editing view.

After any content, layout, export or linked-version change, invalidate the prior
receipt and repeat the affected checks on the new exact artifact. Re-read mutable
linked-document revisions immediately before any authorized release; a changed or
unavailable revision requires re-audit or HOLD. Prefer an audited immutable export
when a fixed version is required and the procedure permits it. Never claim a live
link will remain unchanged after sending. Record each
final filename, SHA-256 (binary files), revision (native documents), page count
and scope reviewed. Never substitute a similarly named unaudited export.

## 5. Record a release decision, not a send permission

Keep the compact audit receipt with the existing private working manuscript or
canonical log, not in the recipient's document or a public repository:

```text
audience / role / language:
current request / one requested action:
instruction: REVIEW_ONLY | SEND_AUTHORIZED_WITHIN_SCOPE
package: filenames or document revisions, hashes, pages, required/optional role
total required reading: observed count or UNKNOWN; duplicate formats noted
content audit: PASS | REVISE | UNKNOWN; defects and repairs
visual audit: PASS | REVISE | UNKNOWN; pages actually inspected
template / source / privacy / link checks:
latest recipient restriction:
verdict: PASS_FOR_REVIEW | PASS_FOR_AUTHORIZED_RELEASE | REVISE | HOLD
remaining uncertainties / reviewer / checked_at:
```

Only PASS checks allow progression to release; revision and inspection remain allowed; UNKNOWN required evidence or unresolved
defects mean HOLD/REVISE. A content audit is an operating instruction, **not an
implemented sender-boundary enforcement mechanism**, and grants no authority.
Retain current Sent reconciliation, recipient preflight and procedure controls.
Verify the final draft/MIME manifest before sending; if the provider adds history,
inspect that actual draft. If it cannot be inspected and could change the package,
hold rather than assume the new-body-only audit covers it. After an authorized
send, reconcile the exact attachment names/bytes where available and body against
the receipt. Log a mismatch; do not send an automatic repair or duplicate apology.

## Regression scenarios

- Short email + a 16-page attachment + two long required links: REVISE the entire
  package, not just the email; no guessed combined page count.
- Clerk asks whether an original petition should circulate: answer that question;
  do not attach a new multi-site technical dossier without an applicable request.
- Recipient refuses supplements and 012 requests review only: prepare the brief
  privately; no email, link or attachment is released.
- One-page PDF has intact extracted Japanese but blank rendered glyphs: REVISE.
- Perfect layout contains TODOs, raw citation tokens or unexplained abbreviations:
  REVISE. Glossary-only repair is insufficient at first use.
- Official form is three pages or the recipient requests a long technical report:
  preserve the required content; one-page default does not override the request.
- One-page output was audited, then its source changed: audit the new export again.
- Recipient says 90 pages, attachment is verifiably 16: preserve both observations;
  investigate links/history without claiming the recipient counted incorrectly.
- Apology already in Sent: reconcile it; do not draft a send-ready duplicate.
