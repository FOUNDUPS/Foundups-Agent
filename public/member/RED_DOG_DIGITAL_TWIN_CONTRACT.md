# Red Dog Digital Twin Contract

**Version**: 1.1.0
**Status**: Active identity and surface contract; authenticated PFMall transport is specified, not implemented
**Last updated**: 2026-08-28

**Vision:** `docs/REDDOG_OUTCOME_VISION.md` defines the Red Dog north-star outcome. This contract defines current identity, authority, surface, and implementation truth; where the two differ, the difference is roadmap work rather than license to overstate current capability.

## 1. Canonical identity

RedDog is the operator-facing name, product identity, persona, and conversation
surface of 012's principal-scoped 0102 Digital Twin. RedDog does not contain a
separate 0102 identity. RedDog services may host the runtime, and a
principal-scoped OpenClaw runtime may supervise admitted execution behind it.
This preserves the original "personal OpenClaw agent" direction without
claiming that the browser shell is the runtime or that one OpenClaw process
owns the complete RedDog identity and policy.

| Component | Canonical responsibility |
|---|---|
| RedDog / 0102 | Operator-facing Digital Twin product identity and the real-time reasoning/orchestration relationship, without sovereign or implicit effect authority. |
| RedDog services | Authenticated conversation, session, model, memory-adapter, transport, and receipt hosts. A service is not the complete RedDog identity. |
| PFMall shell | Thin presentation client for RedDog. It may emit authenticated requests and display replies or receipts after the resident adapter exists. |
| OpenClaw | Principal-scoped 0102 execution/runtime layer, channel gateway, and work supervisor behind RedDog. It does not independently widen RedDog policy or effect authority. |
| WRE | Work decomposition, repository/process authority, verification, and recursive learning for admitted work orders. |
| Hermes | Bounded delegated leaf-worker/scaffolding runtime. It is not policy, repository, or conversation authority. |
| AgentDB | Durable conversation/event ordering, proposal provenance, replay protection, and receipt references. Browser storage is never authoritative for these records. |

RedDog remains a companion-facing product, but personality cannot expand its
authority. 012 remains sovereign. Model output is untrusted text and cannot
authorize work.

## 2. Current PFMall implementation truth

The current member shell implements one unified Red Dog/account concierge
surface through `account-concierge.js` and `window.redDog`. It provides shell
navigation, identity display, FoundUp context, invites, search, and
recommendations.

The following are **not currently implemented** in PFMall:

- an authenticated RedDog conversation transport;
- backend inference or durable conversation memory;
- OpenClaw, WRE, or Hermes dispatch;
- compute accounting, wallet authority, or capability tiers;
- action authorization or execution.

The existing `reddog:command` browser event is a presentation hook only. It is
not an authenticated AI transport and must not be upgraded into one by adding
secrets, authority, or durable state to the browser.

## 3. Target hybrid topology

```text
PFMall / phone / VSIX thin clients
              |
              | authenticated request + session/event id
              v
Resident RedDog / 0102 conversation services
              |
              | proposal-only boundary
              v
OpenClaw resident work supervisor
              |
              v
WRE execution/effect authority
              |
              v
Hermes / FoundUp DAE workers
```

The phone emits to the resident hub; it does not need to host OpenClaw or the
full RedDog runtime. Optional on-device inference may later handle disposable,
zero-authority presentation tasks, but it cannot become the source of memory,
policy, receipts, or execution authority.

## 4. Conversation and effect contract

Every turn has three independent axes:

- interaction intent: `CHAT`, `RESEARCH`, `PROPOSE`, `AUTHORIZE`, `STATUS`, or
  `CANCEL`;
- reasoning depth: `FAST`, `CRITIC`, or `PANEL`;
- effect ceiling: `NONE`, `READ_ONLY`, `PROPOSAL`, or, only outside the
  conversation classifier, separately authorized bounded execution.

Unknown or ambiguous text defaults to `CHAT / FAST / NONE`. Risk may increase
reasoning depth, never effect authority. Chat remains foreground and must not
depend on HoloIndex health. Authorization and cancellation require a fresh
authenticated authority bound to an existing proposal or job; conversational
phrases such as "do it" do not create that binding.

## 5. Scale and durability

The first deployment may use one resident RedDog host. The client and worker
contracts must nevertheless remain stateless so they can scale horizontally
behind the same authenticated adapter. AgentDB owns compare-and-swap event
ordering, idempotency, proposal provenance, replay protection, and receipt
references. A future multi-host deployment may replace its physical store
with PostgreSQL or another shared event store without changing the client
contract.

Isolation is logical per principal, session, FoundUp, and workspace; it does
not require one physical OpenClaw process per person. WSP 98's mesh/zero-server
direction remains a target architecture, not a claim about this resident-hub
phase. A mesh deployment must first reconcile shared ordering and authority
proof rather than moving them into clients.

Raw conversation history, credentials, private model context, and work
authority must not be persisted in `localStorage`. Shell-local UI preferences
and non-sensitive navigation state may continue using browser storage under
their existing contracts.

## 6. Capability progression

Capability labels such as dormant, awake, active, or empowered are product
presentation concepts only until backed by authenticated compute and policy
receipts. They must not be mocked as real authority.

| Capability | Admission requirement |
|---|---|
| Conversation | Authenticated resident adapter and zero-authority foreground response. |
| Read-only research | Explicit read-only ceiling, bounded retrieval, and evidence receipt. |
| Proposal | Durable proposal provenance and no execution side effect. |
| Action | Separate authenticated authorization, current policy admission, bounded work order, and execution receipt. |

Voice, durable personalized memory, compute economics, wallet operations, and
PFMall action execution remain future transactions with their own threat model
and acceptance gates.

## 7. Surface requirements

- Mall and FoundUp entry reuse one RedDog identity and conversation session.
- Reconnects resume only from server-authoritative event order; the browser
  cannot invent or reorder acknowledged work.
- Replies distinguish chat, research evidence, proposal, authorization state,
  and execution receipts.
- A disconnected or unhealthy hub leaves shell browsing usable and reports the
  RedDog capability as unavailable; it never silently falls back to browser
  authority.
- OpenClaw and Hermes implementation names may appear in audit details, while
  the continuous product/persona presented to 012 remains RedDog/0102.

## 8. Phase gates

1. **Implemented in the RedDog VSIX**: deterministic conversation-plane policy,
   zero-effect foreground chat, shared Python/JavaScript vectors, governed
   model routing, and session-local presentation. Raw provider history is
   discarded; durable cross-session continuity is not implemented.
2. **Specified, not implemented in PFMall**: authenticated thin-client adapter,
   durable session/event continuity, and resident reply streaming.
3. **Blocked pending separate proof**: durable personalized memory, voice,
   automatic async research dispatch, and any action promotion or execution.

The detailed Phase 1 authority and scaling decision is maintained in
`docs/audits/architecture/REDDOG_DIGITAL_TWIN_CONVERSATION_PLANE_PHASE1.md`.

**RedDog barks `O!F`, but a bark is never an authorization receipt.**
