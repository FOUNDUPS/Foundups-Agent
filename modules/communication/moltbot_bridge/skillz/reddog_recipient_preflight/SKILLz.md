---
name: reddog_recipient_preflight
description: Fail-closed independent recipient and release audit for outbound correspondence
version: 1.2.0
author: 0102
agents: [0102, qwen, gemma]
primary_agent: 0102
dependencies: [openclaw_dae]
domain: communication
intent_type: DECISION
promotion_state: prototype
pattern_fidelity_threshold: 0.99
category: safety
wsp_chain: [WSP_00, WSP_15, WSP_48, WSP_50, WSP_73, WSP_77, WSP_91, WSP_95, WSP_97]
evals:
  - composer_cannot_self_approve
  - audience_and_need_to_know_checked
  - rendered_links_verified
  - privacy_and_attachment_release_gate
  - concise_single_purpose_message
---

# RedDog Recipient Preflight

## Purpose

Prevent outbound correspondence from using stale, mistyped, blocked, or duplicate
recipient routes.

This skill is provider-agnostic. It does not send messages. It runs immediately
before any send-capable adapter and produces a deterministic SEND/BLOCK receipt.

## Source precedence

Freshest authoritative routing evidence wins:

1. explicit current instruction in the provider thread/record;
2. binding Correspondence Routing policy;
3. canonical Contacts record;
4. established prior thread route;
5. current authoritative public organization directory when no verified route exists.

A newer explicit instruction always overrides older contact history.

**Sent is not verification.** Prior outbound mail, autocomplete history, an old
BCC list, or `NO BOUNCE DETECTED` does not independently prove that a route is
current or correct. Address evidence used to authorize HIGH/CRITICAL mail must
be independently verified (for example by current provider instruction,
authoritative public organization directory, verified business card/direct
source, or an already-binding route record whose underlying evidence is
verified). Represent sent-only evidence as `RouteEvidence(..., verified=False)`;
it must fail closed until independent evidence exists.

**BCC is purpose-scoped.** Past inclusion in BCC does not create standing BCC
authority. Only a current routing policy may define a default BCC. Otherwise,
the caller must establish a message-specific purpose and rerun full preflight
for that recipient.

## Two-pass contract

### Pass A — identity and policy

- resolve intended person or organization and stable Contact ID;
- distinguish person route from organization route;
- enforce DO_NOT_ADDRESS_OR_CC, PERSONAL_ROUTE_CLOSED, BCC_ONLY,
  ORGANIZATION_ONLY, and other binding route policy;
- reject stale or conflicting top-precedence evidence.

### Pass B — exact transaction

- expand final To/CC/BCC exactly as the provider will receive it;
- independently reconstruct each address from Pass-A evidence;
- compare exact normalized equality;
- do not silently alter hyphens, dots, plus tags, subdomains, or other characters;
- compare against already-sent coverage to stop accidental resends;
- block the entire transaction if any recipient fails.

## Independent content and release audit

Recipient resolution is necessary but not sufficient. Every external email,
reply, forward, and send-ready draft must be audited by a verifier that did not
compose the message. The verifier reads the final rendered transaction and
records PASS/BLOCK for:

- correct audience, exact recipient roles, consent, need-to-know, and current
  thread;
- supported material claims, bounded authority, and one clear purpose/ask;
- concise audience-appropriate wording without duplicated or irrelevant context;
- visible link labels, href destinations, redirects, canonical publisher, and
  live destination/title agreement;
- attachments, quoted history, and MIME for secrets, private data, stale/HOLD
  content, or wrong files;
- duplicate/stale-send protection and current provider watermark.

Apply WSP 97: retrieve current evidence, challenge the proposed message from the
recipient/security perspectives, separate facts from inference/unknowns, and
bind the verifier's evidence to the final content digest. A model critique,
draft label, syntax check, or successful provider response is not independent
release evidence.

The complete routing and release contract is:
`modules/communication/moltbot_bridge/docs/clarity/gmail_wre_rsi_routing.md`.

## Sender boundary

The final provider mutation must run through the repository-owned host adapter:

`modules/communication/moltbot_bridge/host/reddog_correspondence_sender_boundary.mjs`

For Gmail `send_email`, reply, `send_draft`, and recipient-specific delivery repair:

1. read fresh Sent coverage immediately before preflight;
2. build a machine-readable receipt that binds provider operation, correspondence
   scope/purpose, Contact IDs, exact To/CC/BCC roles and addresses, content digest,
   draft/thread identifiers, duplicate coverage, issue/expiry time and Sent watermark;
3. require `decision=SEND` and an unexpired transaction-identical receipt at the
   adapter boundary; missing, BLOCK, stale, altered or digest-invalid receipts make
   the provider mutation unreachable;
4. re-read Sent coverage at the boundary and reject if the watermark or duplicate
   coverage changed after receipt issuance;
5. for `send_draft`, read the exact provider draft before submission and require its
   message/thread IDs, To/CC/BCC and content digest to match the bound transaction;
6. submit only through the injected provider callback owned by the host adapter;
7. immediately read the exact provider Sent message and require message/thread IDs
   plus To/CC/BCC equality before returning `VERIFIED_SENT`.

A provider exception is `PROVIDER_STATE_UNKNOWN`; reconcile Sent before any retry.
A read-back failure/mismatch is `PROVIDER_SENT_INTEGRITY_INCIDENT`, never a reason
for an automatic resend.

HIGH/CRITICAL correspondence must fail closed when a recipient is:

- UNKNOWN
- UNVERIFIED
- CONFLICTING
- STALE
- NEAR_MATCH
- CLOSED
- DUPLICATE_COVERAGE

The composer does not authorize its own recipient list.

## Post-send verification

After a provider reports success:

1. read back the exact sent transaction;
2. compare actual To/CC/BCC with the preflight receipt;
3. treat any missing or extra recipient as a send-integrity incident;
4. do not infer delivery from absence of a bounce;
5. repair only a verified missing recipient after rerunning preflight.

## Reference implementation

Recipient evidence resolution:
`modules/communication/moltbot_bridge/src/reddog_recipient_preflight.py`

Provider-call enforcement:
`modules/communication/moltbot_bridge/host/reddog_correspondence_sender_boundary.mjs`

Core APIs:

- `preflight_recipients(...)`
- `verify_sent_readback(...)`
- `normalize_address(...)`

## Acceptance tests

Contract tests cover:

- stale Contacts overridden by a newer explicit provider route;
- one-character/hyphen near-match rejection;
- closed personal route;
- BCC-only route policy;
- duplicate sent coverage;
- conflicting top-authority records;
- unknown route;
- display-name/case normalization without address rewriting;
- mixed valid/invalid multi-recipient transactions;
- exact provider read-back;
- missing/extra recipient read-back detection.

## Security property

Default deny. Recipient correctness is a per-transaction authorization decision,
not a remembered fact.
