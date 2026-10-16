---
name: reddog_correspondence_state
description: Persist privacy-bounded provider event metadata and materialized correspondence scope state so Red Dog can resume correspondence without replaying complete mailboxes.
version: 1.0.0
author: 0102
agents: [0102, qwen, gemma]
primary_agent: 0102
dependencies: [reddog_recipient_preflight]
domain: communication
intent_type: MAINTENANCE
promotion_state: prototype
pattern_fidelity_threshold: 0.99
category: workflow
wsp_chain: [WSP_00, WSP_15, WSP_22, WSP_50, WSP_78, WSP_91, WSP_95, WSP_97]
evals:
  - provider_truth_not_cache_truth
  - scope_state_roundtrip
  - watermark_refresh_gate
  - duplicate_event_idempotency
  - no_raw_mailbox_body_persistence
  - cache_never_authorizes_send
---

# Red Dog correspondence state

## Purpose

Give Red Dog durable, machine-readable continuity across providers without making
Gmail, Google Sheets, Google Docs, Slack, LinkedIn, or another provider the
memory substrate.

The repository remembers **how to remember**. A private module-owned runtime
database remembers the compact current state. Provider systems remain transaction
truth. Human-facing Sheets / Docs are projections.

Provider systems remain transaction truth.

Do **not** create a correspondence Moshpit or a second contact database.

Do not create a correspondence Moshpit or parallel contact database.

## Canonical layers

1. **Provider truth** — Gmail / Slack / LinkedIn / other provider records prove
   whether a provider event actually exists and its current provider state.
2. **Normalized provider event ledger** — append-only metadata in
   `RedDogCorrespondenceStateStore`; no raw body or recipient dump.
3. **Materialized correspondence state** — one row per
   `stakeholder_or_org × topic_or_ask` scope.
4. **Human projections** — Google Sheets / Docs or UI projections may mirror the
   state but are rebuildable and non-authoritative.
5. **Recipient preflight** — remains the independent send-authorization gate.

The state cache never grants permission to send.

## Scope key

Use a deterministic scope key such as:

```text
FUKUI_CITY::SUKATTO::FINANCIAL_DISCLOSURE
FUKUI_CITY::SUKATTO::PPP_PFI_ROUTE
FUKUI_CITY::SUKATTO::PROCUREMENT
FUKUI_COUNCIL::SUKATTO::CONTRACT_RESOLUTION
```

Do not combine unrelated asks merely because they share a recipient.

## Stable asks

Every meaningful ask receives a stable machine ID. Example:

```text
ASK-FIN-001
ASK-FIN-002
ASK-PPP-001
ASK-PROC-001
ASK-COUNCIL-001
```

Ask states are explicit:

`NOT_YET_ASKED | OPEN | WAITING_PROVIDER | FORMAL_ROUTE_REQUIRED | ANSWERED | SUPERSEDED | CLOSED`

A procedural reply that says "use the formal information-disclosure route" can
answer the email-routing question while leaving the requested financial records
open under `FORMAL_ROUTE_REQUIRED`.

## Provider synchronization

Normal resume path:

```text
load scope state
  -> compare provider watermark
  -> exact match + VALID freshness? use cached scope state
  -> mismatch / unknown / stale? read provider delta only
  -> normalize new provider events
  -> update asks + next action
  -> advance watermark
  -> persist state
```

Never infer ordering from an opaque provider watermark. It is an equality /
change detector unless the provider adapter defines stronger semantics.

If the provider cannot establish a trustworthy watermark, set freshness
`UNKNOWN` and reconcile the relevant provider window before acting.

## Before drafting

Use the persisted scope state as the first continuity read.

Then:
1. verify freshness against the provider;
2. ingest only new provider events when the watermark changed;
3. separate answered asks, still-open asks, and genuinely new delta;
4. compute `follow_up_gate`, `next_expected_event`, and
   `next_allowed_action`;
5. if provider evidence conflicts with the cache, provider evidence wins and the
   cache is repaired.

## Recipient-facing link/source and HOLD-content gate (2026-10-16)

Apply this to every external email, reply, forward and send-ready draft, including
Gmail `send_email`, `reply`, `send_draft`, `create_draft` and `update_draft`.
Run before provider mutation AND on the final rendered plain-text/HTML MIME.
An archival draft is not a send-ready draft; keep archival text intact but require
a separately audited clean body before any send.

1. **Primary publisher first.** Link to the publisher-owned, verified article/
   report page. Social syndication (e.g. LinkedIn) is secondary and may not
   silently replace that source. Verify that the page exists and that its
   displayed edition/title matches the claim immediately before release. If
   issue #003 is not on the website yet, do not label the website page #003.
2. **No giant naked links.** Do not paste long percent-encoded URLs, LinkedIn
   `/pulse/` tracking/slugs or share parameters as visible email paragraphs.
   Prefer a verified, human-readable canonical URL; if a long URL is
   unavoidable, use a concise descriptive hyperlink in HTML/Markdown *only
   after verifying its destination and the actual rendered recipient view*.
   For official form or evidence links where the exact URL must be visible,
   retain the authoritative URL and give an intelligible reference label.
   Never invent a short link or use an unverified link shortener.
3. **Need-to-read test.** Remove unrelated newsletter links from a narrow
   government procedure/eligibility email. If a report is genuinely needed,
   cite the exact verified web article (not a broad landing page disguised as
   the precise edition) and one concise sentence explaining relevance.
4. **Internal-only text never escapes.** If the proposed outbound includes
   `内部保管・このまま送信しない`, `【HOLD`, `SUPERSEDED／送信禁止`,
   historical archiving instructions, stale deadlines, or an internal
   `DO NOT SEND` header, classify it HOLD; never forward the whole archive
   as a new email. Preserve evidence in the source archive; compose a clean
   recipient-only version from verified, current facts.
5. **Release check.** Inspect To/CC/BCC, new body, rendered links (visible label
   and href), automatic quoted/forwarded history, attachments and linked
   source status. On a failed publication-source or link-quality check,
   return REVISE/HOLD instead of releasing. Gmail provider success or a
   Gmail draft label does not by itself prove these checks ran.

This is a composition/quality policy, not proof that the direct ChatGPT Gmail
connector is intercepted by the Red Dog service-owned sender boundary.

## Before sending

A cached `CLEAR` is not send authority.

Immediately before any send-capable action:
1. refresh provider delta;
2. apply current Correspondence Routing / consent;
3. run `reddog_recipient_preflight`;
4. block duplicate coverage and closed/stale/unverified routes;
5. after send, read provider state back and record the new provider event.

## Persistence

Runtime implementation:
`modules/communication/moltbot_bridge/src/reddog_correspondence_state.py`

Persistence uses WSP 78 `ModuleDB`, producing module-owned tables under the
configured FoundUps DB. SQLite remains the local default and PostgreSQL may be
selected by the existing database infrastructure.

Live DB files are runtime/private state and remain gitignored.

Do not add correspondence tables directly to the AgentDB compatibility monolith.

## Privacy boundary

Persist only the minimum continuity metadata needed for machine operation:
provider/account correlation key, provider message/thread IDs, scope key,
direction, timestamps, event class, digests, stable ask IDs/statuses, routing
state codes, procedural state, next action, provider watermark, and state digest.

Do not persist here:
- raw message bodies;
- complete To/CC/BCC address dumps;
- credentials or tokens;
- private attachments;
- hidden model reasoning;
- unrelated mailbox content.

Provider IDs may themselves be private operational metadata; keep the runtime DB
out of Git and public telemetry.

## Human projections

A Google Sheet can expose Email Log, Action Queue, Routing, and a Correspondence
State projection for 012. Those surfaces are operational UI, not transaction
truth and not Red Dog's required persistence layer.

A deleted human projection must be recoverable from provider truth + native
runtime state.

## Failure modes

Fail closed to `HOLD / RECONCILE` when:
- state digest mismatches;
- schema version is unknown;
- provider watermark changed and delta has not been reconciled;
- freshness is UNKNOWN/STALE for a consequential action;
- ask IDs are duplicated or contradictory;
- routing state conflicts with current provider/CRM evidence;
- a cached next action would produce a duplicate or third follow-up;
- provider evidence is incomplete.

## Moshpit boundary

- YUMORI / campaign Moshpit: material campaign history only.
- 0102 Moshpit: agent errors, repairs, generalized learning.
- Correspondence state DB: current machine continuity.

Do not use any Moshpit as send proof.

## Red Dog boundary

This skill grants no provider, Gmail, Slack, LinkedIn, filesystem, database,
recipient, or send authority by itself. Execution remains bounded by the current
work order, provider connection, routing policy, recipient preflight, WSP
controls, and applicable product permissions.
