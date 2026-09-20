---
name: reddog_recipient_preflight
description: Fail-closed two-pass recipient authorization for outbound correspondence
version: 1.0.0
author: 0102
agents: [qwen, gemma]
dependencies: [openclaw_dae]
domain: communication
intent_type: DECISION
promotion_state: prototype
pattern_fidelity_threshold: 0.99
category: safety
evals: []
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

## Sender boundary

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

`modules/communication/moltbot_bridge/src/reddog_recipient_preflight.py`

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
