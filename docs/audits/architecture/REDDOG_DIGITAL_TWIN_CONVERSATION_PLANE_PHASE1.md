# RedDog Digital Twin Conversation Plane - Phase 1

**Date:** 2026-08-22 (JST)
**State:** Conversation policy and transport envelope implemented; authenticated service and production PFMall/phone channel remain gated
**Protocols:** WSP 00, 15, 22, 50, 62, 73, 97

## Decision

RedDog presents one continuous conversation. There is no visible Chat/Work
switch. The Digital Twin owns the foreground relationship; the existing
governed work plane remains a separate effect boundary.

```text
VSIX / future PFMall phone client
              |
              v
RedDog-hosted 0102 Digital Twin conversation plane
              |
              +-- CHAT / RESEARCH / PROPOSAL (no execution authority)
              |
              v
existing authenticated conversation-to-work promotion
              |
              v
OpenClaw resident work supervisor -> WRE / Hermes / FoundUp DAEs
```

The identity and runtime statements are intentionally distinct. RedDog is the
continuous Digital Twin product/persona and hosts its conversation policy. A
principal-scoped OpenClaw 0102 agent may be the resident execution/runtime
layer that embodies work for that twin. That does not make the browser an
OpenClaw host, collapse RedDog into one OpenClaw process, or give OpenClaw
independent policy authority. Hermes is not a conversation host; it receives
bounded delegated work only after the existing authority chain admits it.

## Independent axes

Every turn is classified deterministically along three independent axes:

| Axis | Values | Phase-1 rule |
|---|---|---|
| Interaction | `CHAT`, `RESEARCH`, `PROPOSE`, `AUTHORIZE`, `STATUS`, `CANCEL` | Unknown and ambiguous requests default to `CHAT`. |
| Reasoning | `FAST`, `CRITIC`, `PANEL` | Risk may raise reasoning depth; it never raises effects. |
| Effect ceiling | `NONE`, `READ_ONLY`, `PROPOSAL`, `BOUNDED_EXECUTION` | The conversation classifier can emit at most `PROPOSAL`; bounded execution is forbidden. |

`Do it`, `go ahead`, and similar unbound phrases are `CHAT / NONE`, not
authority. Even an explicit authorization sentence remains proposal-only and
requires a separately authenticated authority record. Model output is checked
against the deterministic ceiling and cannot elevate it.

## Implemented boundary

- `conversation_plane_contract.py` owns typed enums, strict rehydration, and
  effect-ceiling enforcement.
- `conversation_plane.py` owns bounded Unicode-normalized deterministic intent,
  risk, and reasoning classification. It reads no model, memory, network,
  HoloIndex, database, repository, or environment state.
- `conversation_plane_policy.js` is the thin VSIX adapter. Ordinary RedDog chat
  routes to no repository context and a single fast model. Risk may select a
  higher reasoning route while effect authority remains zero.
- Foreground chat suppresses both raw provider history and the separate
  opt-in last-work-packet continuation summary. Python and JavaScript apply the
  same 12,000-Unicode-scalar input bound.
- The 8,370-line extension host did not grow. Existing mode-resolution logic
  was extracted behind the sibling adapter and the host is below its prior
  ceiling.
- Existing AgentDB scope, signer, promotion, OpenClaw, WRE, and Hermes modules
  are reused. No second router, database, signer, queue, or worker stack exists.
- `resident_conversation_transport_contract.py` owns an exact zero-authority
  `TURN` / `STATUS` / `CANCEL` envelope. It validates canonical digest IDs,
  CAS revision, nonce/idempotency, a maximum five-minute lifetime, and emits a
  content-free binding. It contains no endpoint, authentication, persistence,
  model, queue, or effect implementation.
- `npm run test:conversation` is the dedicated cross-language fast lane.

The `asynchronous_readonly_allowed` decision field is admission metadata only.
Phase 1 does not yet start a background researcher or critic. This preserves a
truthful foreground implementation without inventing queue or cancellation
semantics.

## PFMall and phone scaling

PFMall already has a shell-local Red Dog plane and `reddog:command` UI events.
Those are presentation hooks, not an authenticated AI transport. The current
PFMall HTTP API is read-only and unauthenticated and must not be overloaded as
a conversation endpoint.

The scalable channel is hybrid:

1. The phone/PFMall surface is a thin authenticated client. It captures text
   (and later voice), renders replies/receipts, and may cancel its own turn.
2. A resident RedDog hub owns model access, secrets, current conversation
   authority, and the OpenClaw supervisor connection.
3. The client envelope carries conversation, revision, turn, nonce,
   idempotency, and expiry bindings. The admitted server-side turn must add
   principal and FoundUp scope derived from verified session authority and
   current AgentDB state; browser claims never supply or widen them.
4. AgentDB CAS/event order provides current single-host continuity. Multi-host
   scale requires the already-planned PostgreSQL/shared event-store migration,
   not browser localStorage as authority.
5. Stateless conversation workers may scale horizontally after durable CAS,
   authenticated transport, idempotency, cancellation, and progress receipts
   are present.

WSP 73 requires per-principal isolation, not a dedicated physical process per
person. WSP 98's mesh/zero-server direction is a target state. This phase does
not claim mesh-native RedDog: shared ordering, replay, and authority must be
resolved before a resident hub can be replaced or federated.

Therefore the transport envelope is `OBSERVED`, while authenticated service
binding and the PFMall/phone adapter remain `SPECIFIED_NOT_IMPLEMENTED`.
Shipping an unauthenticated fetch hook would be false progress and a
cross-principal risk.

## Memory and continuity truth

Raw model history remains disabled. Current authenticated AgentDB conversation
scope and Principal Memex admission exist, but this phase does not attach raw
history or implement "have we discussed this before?". Principal Memex,
FoundUp Memex, and HoloIndex recall must be separately sourced, freshness
labelled, and non-authoritative for work.

The governed HoloIndex owner query failed closed during pre-action research
with `HOLOINDEX_AUTHORITY_ROOT_HEAD_MISMATCH`. No query-path reindex or repair
was attempted. Exact-tree direct reads were used, and the isolated HoloIndex
repair remains outside this transaction. A HoloIndex failure must never block
ordinary zero-context chat.

## WSP 15 allocation

| Dimension | Score | Reason |
|---|---:|---|
| Complexity | 4 | Cross-language routing plus authority invariants and package closure. |
| Importance | 5 | Defines the primary 012/0102 interface. |
| Deferability | 5 | Current unknown-default HIGH/Fusion behavior harms the product boundary. |
| Impact | 5 | Establishes VSIX behavior and the reusable PFMall/phone contract. |

Total: `4 + 5 + 5 + 5 = 19`, canonical `P0`.

## WSP 97 truth boundary

| Claim | State |
|---|---|
| Deterministic Digital Twin conversation contract | OBSERVED |
| Default VSIX chat is zero-context, fast, and effect-free | OBSERVED |
| Risk/depth/effect are independent | OBSERVED |
| Chat/model text can execute work | FALSE / FORBIDDEN |
| Prior work-packet continuation enters foreground chat | FALSE / FORBIDDEN |
| Existing authenticated work promotion reused | OBSERVED, not invoked by ordinary chat |
| Strict content-free turn/status/cancel envelope | OBSERVED |
| Envelope authenticates principal or FoundUp scope | FALSE / FORBIDDEN |
| Durable cross-device conversation | SPECIFIED_NOT_IMPLEMENTED |
| PFMall authenticated conversation adapter | SPECIFIED_NOT_IMPLEMENTED |
| Phone voice ingress/barge-in | SPECIFIED_NOT_IMPLEMENTED |
| Asynchronous critic/research execution | SPECIFIED_NOT_IMPLEMENTED |
| Authoritative memory recall across four sources | SPECIFIED_NOT_IMPLEMENTED |
| OpenClaw is the resident work supervisor | OBSERVED architecture boundary |
| A principal-scoped OpenClaw 0102 runtime may back the personal RedDog agent | VISION supported by current execution-layer architecture; per-principal deployment not implemented by this slice |
| Mesh-native/zero-server RedDog | TARGET architecture; not implemented by this resident-hub phase |
| Hermes is the always-running conversation host | FALSE |

## Next gated layers

1. Authenticated resident conversation service binding the implemented
   envelope to existing conversation-session authority and AgentDB CAS ports.
2. Thin VSIX and PFMall transport adapters plus content-free progress receipts.
3. Governed bounded memory recall with source/freshness labels.
4. Local STT/TTS and interruption after consent and cancellation proofs.

## WSP 97 high-risk assumption audit

- Assumption: the host derives principal and FoundUp scope from a verified,
  current resident session. The envelope cannot assert either value.
- Failure modes held closed by this slice: identity/effect/provider injection,
  unknown operations, stale or future envelopes, revision-shape ambiguity,
  malformed digest bindings, raw operator text in public bindings, and direct
  dataclass construction with invalid static state.
- Still-open service failures: atomic idempotency storage, credential replay,
  authenticated cancellation ownership, current AgentDB CAS binding, durable
  progress ordering, and cross-surface contract parity.
- Rejected alternatives: browser localStorage as authority, extending the
  unauthenticated read-only PFMall API, adding a second database/router, or
  treating request digests as authentication.
- Decision: `PROCEED` for the pure contract and tests; `HALT` for any live
  endpoint or adapter until the existing signer/session/AgentDB authority chain
  is bound and adversarially verified.
