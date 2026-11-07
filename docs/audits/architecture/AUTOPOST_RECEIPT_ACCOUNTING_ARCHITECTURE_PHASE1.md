# AutoPost Receipt -> Accounting Architecture, Phase 1

**Status:** DECISION / CONTRACT SLICE  
**Scope:** AutoPost capture extension + FoundUp accounting boundary  
**Initial consumer:** YUMORI  
**Privacy rule:** NO receipt image, bank data, member financial data, or live accounting rows in the public repository.

## Decision

Do not bolt a full ERP into AutoPost.

AutoPost should become the **capture/intake edge**. Accounting should remain a separate, deterministic service with an append-only double-entry ledger.

The reusable path is:

```
camera / gallery / file
  -> media classifier
      -> social/content path (existing AutoPost purpose)
      -> receipt/accounting path
           -> preserve original evidence
           -> SHA-256 hash
           -> structured extraction
           -> ReceiptAccountingEventV1
           -> REVIEW_REQUIRED
           -> human/0102 approval gate
           -> balanced double-entry post
           -> private ledger
           -> Google Sheet / report projection
```

The contract between capture and accounting is:

`modules/foundups/docs/RECEIPT_ACCOUNTING_EVENT_SCHEMA_V1.json`

## Why this boundary

The existing AutoPost capture audit already found that AutoPost has a useful capture shell but lacks still-image/file intake, real recognition, persistence, and a reusable structured output contract.

Accounting has different invariants from social posting:

- evidence must remain auditable;
- amounts must use exact arithmetic;
- every posted journal must balance;
- corrections should be reversals, not silent edits;
- payment source must not be guessed;
- financial evidence must remain private.

Those rules belong outside the social-post pipeline.

## Storage model

### 1. Device staging

Current AutoPost is a browser/PWA surface. Use IndexedDB only as an **offline queue/staging cache**.

Do not treat iOS/browser storage as the sole archive. Browser storage can be evicted and does not provide the durability expected for accounting evidence.

A future native/mobile shell may use encrypted SQLite locally.

### 2. Evidence store

Original receipt photo/PDF is immutable evidence.

For each evidence object store:

- receipt_id
- SHA-256
- MIME type
- original filename when available
- private storage URI
- capture timestamp

For YUMORI today, Google Drive is an acceptable private evidence store and Google Sheets is an operational projection.

### 3. Canonical accounting store

Target shape: local/private SQLite with append-only journal semantics.

Core tables/concepts:

- evidence
- receipt_extraction
- accounts
- journal_transaction
- journal_posting
- audit_event
- projection_sync_state

Money must be stored with exact semantics (integer minor units or decimal), never binary float.

### 4. Google Sheet projection

Google Sheets is for:

- human review
- bank/post-office preparation
- summaries
- export
- collaboration

It is **not** the only source of truth.

A sheet row may be edited for workflow convenience, but POSTED ledger entries remain immutable and changes are represented by reversing/correcting entries.

## Posting gate

Extraction does not equal accounting.

A receipt may reach CAPTURED / REVIEW_REQUIRED with:

- known vendor
- known amount
- known tax
- known purpose

while still lacking:

- who actually paid;
- which bank/cash/card account funded it;
- whether it is reimbursable.

No double-entry transaction is POSTED until the funding/payment source is confirmed.

This prevents the agent from inventing a credit-side account.

## Initial chart-of-accounts pattern

Example only; projects may extend it:

```
Assets:Cash
Assets:Bank:<FoundUp>
Liabilities:FounderAdvance
Equity:OpeningBalance
Income:Donations
Expenses:Admin:Hanko
Expenses:Admin:Printing
Expenses:Admin:Postage
Expenses:Campaign:Materials
Expenses:Transport
Expenses:Meetings
```

If a founder personally pays a project expense, `Liabilities:FounderAdvance` is appropriate only after that fact is confirmed.

## AutoPost UX

Phase 1 capture behavior:

1. User takes a photo or selects an image.
2. AutoPost classifies the media.
3. If likely receipt/invoice, show "Accounting receipt detected".
4. Extract draft fields.
5. Preserve image and hash before transformation.
6. Ask only for missing high-impact facts, especially payment source.
7. Show a compact confirmation card.
8. On approval, hand the normalized event to the accounting adapter.
9. Ledger service validates balance and posts.
10. Projection adapter updates private Google Sheet/reporting surfaces.

The social posting flow is not invoked for a receipt unless the user separately asks to publish it.

## Open-source accounting evaluation

### Recommended integration strategy

Keep the FoundUps contract neutral and make the accounting backend replaceable.

**Best architectural reference / sidecar candidate:** Attri-Inc OpenLedger.
- Python
- SQLite
- MCP
- local-first
- append-only / reversal semantics
- Apache-2.0

This is a close match to the desired agent interface, but it is young software. Do not make YUMORI dependent on it before regression/security testing.

**Useful second candidate:** Dispatch Labs `books`.
- local-first
- agent-operated CLI
- balanced double-entry
- audit trail
- MIT
- currently experimental

**Interop/reporting candidates:** hledger and Beancount.
- mature plain-text accounting ecosystems
- excellent deterministic export/report validation
- GPL licenses make them better as optional external tools/adapters than code copied into Foundups-Agent.

**Not selected for Phase 1:** full ERP stacks such as ERPNext/Frappe Books/Akaunting. They solve much larger operational problems and add deployment, UI, database, upgrade, and licensing surface that receipt capture does not require.

## Public-repo privacy boundary

Allowed in GitHub:
- schemas
- adapters
- tests with synthetic data
- architecture
- migration logic

Never commit:
- receipt photos
- bank statements
- account numbers
- member addresses
- private payment details
- live accounting exports
- Drive credentials or URLs that expose private documents

## Phase 1 acceptance criteria

A successful first slice must prove:

- image/file intake exists;
- original evidence gets a deterministic SHA-256;
- receipt extraction produces `ReceiptAccountingEventV1`;
- uncertain payment source leaves the event in REVIEW_REQUIRED;
- no unbalanced journal can be posted;
- posted entries are append-only;
- corrections use reversals;
- a private Google Sheet projection can be regenerated from ledger data;
- the same pipeline routes by `foundup_id`, with YUMORI as the first consumer;
- no private evidence enters the public repo.

## Phase 2

- encrypted local/mobile store;
- bank CSV/API reconciliation;
- automated duplicate-receipt detection by SHA-256 + vendor/date/amount;
- tax-code mapping per jurisdiction;
- optional OpenLedger or Books adapter;
- accounting MCP tools for 0102/Red Dog;
- export adapters: hledger/Beancount/CSV.

## Current implementation note

The current YUMORI receipt workflow may be bootstrapped with private Google Drive evidence + a Google Sheet ledger mirror while the local SQLite service is built.

That keeps today's administration moving without making Google Sheets the long-term accounting database.
