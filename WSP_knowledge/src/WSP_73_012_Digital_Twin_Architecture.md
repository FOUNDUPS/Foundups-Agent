# WSP 73: 012 Digital Twin / RedDog Architecture Protocol

- **Status:** Active
- **Version:** 2.2
- **Updated:** 2026-08-26
- **Purpose:** Define the identity, memory, conversation, orchestration, and
  authority boundaries for a principal-scoped 0102 Digital Twin presented as
  RedDog.
- **Dependencies:** WSP 00, WSP 15, WSP 27, WSP 46, WSP 60, WSP 77,
  WSP 80, WSP 97, WSP 98

## 1. Canonical identity

RedDog is the operator-facing name, persona, continuous product identity, and
conversation surface of a principal-scoped 0102 Digital Twin. RedDog does not
name a separate intelligence that contains 0102, and 0102 does not disappear
behind a browser extension. A service can host the runtime, memory adapters,
models, and transports, but no single shell, model, server, or OpenClaw process
is the complete RedDog identity.

```text
012 <-> RedDog / principal-scoped 0102 Digital Twin
```

The same relationship may be presented through a VSIX, p.fMALL, phone, voice,
or future surface. Surface continuity is a product goal; durable continuity is
claimed only when authenticated server-side session and event state prove it.

012 remains the sovereign principal. RedDog personality, model output, memory,
conversation text, and confidence do not create effect authority.

## 2. Responsibility map

| Component | Canonical responsibility |
|---|---|
| 012 | Work focus, sovereign authorization, testing, correction, and override |
| RedDog / 0102 Digital Twin | Conversation, reasoning, requirements, architecture, evidence synthesis, proposal, and orchestration intent |
| RedDog services | Host authenticated transport, session state, model access, bounded memory adapters, and receipts without becoming the identity itself |
| Principal Memex | Durable principal cognition admitted under principal scope; never implicit work authority |
| FoundUp Memex | Snapshot-bound cognition for one FoundUp; never a global cross-tenant store |
| HoloIndex | Generation-bound repository/WSP retrieval; query paths never reindex |
| AI Gateway | Model catalog, capability admission, evaluated selection, and receipt-bound runtime topology |
| Nemotron | Local shadow proposer for evaluation topologies; never production selection or promotion authority |
| OpenClaw | Principal-scoped channel gateway and policy/control supervisor for admitted work |
| WRE | Work decomposition, execution admission, repository/process authority, verification, and recursive learning |
| Hermes | Bounded delegated leaf-worker/scaffolding runtime; not policy or conversation authority |
| Overseer/sentinel agents | Health, security, drift, violation, and regression review; findings do not self-authorize repairs |
| p.fMALL / phone / VSIX | Untrusted thin clients that submit authenticated requests and render replies/receipts |

## 3. Layered architecture

```text
Presentation
  p.fMALL / phone / VSIX / voice
        |
        v
Conversation
  RedDog / principal-scoped 0102
        |
        +--> Principal Memex
        +--> scoped FoundUp Memex
        +--> HoloIndex
        +--> AI Gateway runtime topology
        |
        v
Promotion
  authenticated proposal + explicit authorization + current policy
        |
        v
Execution
  OpenClaw control supervisor -> WRE authority -> Hermes/FoundUp DAE workers
        |
        v
Verification and learning
  receipts -> tests -> Overseer review -> governed Memex/roadmap candidates
```

This is a layered cake built as independently testable LEGO contracts. A layer
cannot borrow authority from a later layer. Conversation can exist while
HoloIndex or worker infrastructure is unavailable. Work cannot exist merely
because conversation succeeded.

## 4. Continuous conversation contract

Every turn has independent axes:

- interaction intent: `CHAT`, `RESEARCH`, `PROPOSE`, `AUTHORIZE`, `STATUS`, or
  `CANCEL`;
- reasoning depth: `FAST`, `CRITIC`, or `PANEL`; and
- effect ceiling: `NONE`, `READ_ONLY`, `PROPOSAL`, or separately admitted
  bounded execution.

Unknown or ambiguous text defaults to `CHAT / FAST / NONE`. Risk may increase
reasoning depth, never effect authority. "Do it" or "continue" identifies
operator intent but does not manufacture the missing authenticated proposal,
authorization, policy, or work-order bindings.

Raw model-provider history is not authoritative memory. Cross-session and
cross-surface continuity requires authenticated conversation scope, durable
event order, compare-and-swap, idempotency, replay prevention, and cancellation
ownership. Until those are connected, the product identity may be continuous
while the implementation remains session-local.

## 5. Memory and recall

RedDog composes bounded sources; it does not collapse them into one database:

1. **Current repository and receipts** for executable truth.
2. **HoloIndex** for generation-bound repository/WSP discovery.
3. **Principal Memex** for authenticated principal goals, terminology,
   preferences, and accepted decisions.
4. **FoundUp Memex** for one FoundUp's Brain, Breadcrumbs, roadmap, decisions,
   and verified outcomes.
5. **Conversation events** for ordered turn continuity.

Each result declares source, scope, freshness, provenance, and authority. Newer
repository/work truth overrides stale memory interpretation. Memories can
inform reasoning and proposals; they cannot authorize effects or silently
rewrite durable cognition. Cross-FoundUp retrieval is explicitly scoped and
does not imply cross-FoundUp mutation.

## 6. Model-routing boundary

RedDog emits task requirements. It does not hard-code a champion model from a
prompt heuristic.

```text
task requirements
  -> AI Gateway eligible catalog and incumbent
  -> Nemotron shadow candidates
  -> held-out AutoResearch measurements
  -> independent signed promotion
  -> short-lived receipt-bound runtime topology
  -> RedDog / Fusion / OpenClaw / Hermes consumers
```

Nemotron can propose candidate roles and panels. AutoResearch can measure those
candidates under a reserved campaign. Neither can promote its own output.
Production consumers accept only current, authenticated, provider-available
runtime bindings. A static extension roster is an explicit dialogue-only
evaluation fallback and cannot open action planning or worker dispatch.

## 7. Work orchestration and recursive operation

RedDog may inspect readiness and formulate work, then submit a bounded proposal
to the existing work spine. Before dispatch, the system asks and proves:

- Is repository and dependency evidence current?
- Are upstream runtime versions and security advisories within policy?
- Is the codebase health receipt current?
- What WSP, structure, test, documentation, and security violations are open?
- Which bounded jobs can internal agents safely perform?
- What independent review or 0102 consensus is required?

OpenClaw supervises admitted intent and channel policy. WRE owns decomposition,
repository/process effects, verification, and recursive learning. Hermes or a
FoundUp DAE receives one bounded leaf job. Overseers report health and security
evidence; they do not bypass the same work admission.

Every work cycle follows WSP 97:

```text
research -> assumptions -> failure modes -> smallest layer -> execute
  -> verify -> independent audit -> receipt -> next WSP 15 allocation
```

No component assumes that generated code is viable. Code and documentation are
accepted only after repository discovery, interface verification, tests, and
truth-labelled review.

## 8. p.fMALL, phone, and scale

p.fMALL is the FoundUp discovery and interaction shell. Its browser Red Dog
plane is currently presentation-only, not the resident Digital Twin transport.
A phone is normally another thin client: it emits authenticated turns to a
resident or federated RedDog service and renders ordered replies and receipts.
It does not need to host the full OpenClaw/WRE/Hermes stack.

The first deployment may use one resident hub. Horizontal or mesh scale must
preserve principal/session/FoundUp/workspace isolation, durable ordering,
idempotency, revocation, policy, and receipts. WSP 98 is the target migration
contract; it is not proof that zero-server or peer mesh operation exists.

## 9. DAE and Progressive Web Agent terminology

The governance expansion is **Decentralized or Distributed Autonomous
Entity/Ecosystem** under WSP 27. **Digital Autonomous Entity** may describe the
software embodiment. **Distributive** describes the intended allocation of
benefit and agency; it is not a separate runtime type unless a future protocol
defines one.

A Progressive Web App is browser technology. A **Progressive Web Agent** is the
target FoundUp experience formed when that surface connects to scoped Memex,
reasoning, governance, and worker services. A manifest, service worker, or
chat widget alone does not prove a Progressive Web Agent.

## 10. Current implementation truth

| Capability | State |
|---|---|
| Deterministic RedDog conversation classification and effect ceiling | Implemented |
| VSIX RedDog thin client and governed model calls | Implemented |
| HoloIndex generation-bound read-only query integration | Implemented with freshness/route preconditions |
| AgentDB existing-scope admission, trusted new-scope persistence, and durable first-TURN resolution link | Implemented with signed immutable E0 request commitment and atomic replay authority; first TURN handler/CAS not executed |
| Principal Memex structural projection and bounded resident admission | Implemented building blocks |
| Static evaluation fallback isolated from action planning | Implemented |
| Authenticated durable resident conversation service | Not implemented |
| ChatGPT-like cross-session/cross-surface history | Not implemented |
| p.fMALL/phone RedDog transport | Specified, not implemented |
| Automatic conversation-to-work production binding | Not implemented |
| Autonomous preflight job dispatch from health findings | Not implemented |
| Mesh-native or zero-server RedDog | Target, not implemented |

## 11. Phase gates

1. Add immediate authenticated AgentDB CAS and operation handlers after the
   completed durable empty-ID first-request resolution link.
2. Connect VSIX and p.fMALL/phone thin-client adapters to that one service.
3. Add source-labelled, governed Principal/FoundUp Memex recall.
4. Bind proposal-to-work promotion to current OpenClaw/WRE authority receipts.
5. Add readiness/security assessment and bounded autonomous job proposals.
6. Prove one external FoundUp onboarding flow through WSP 109.
7. Only then prototype WSP 98 peer-assisted/federated deployment.

Each gate is a separate WSP 15 transaction with its own acceptance evidence.

## 12. Implementation references

- `modules/ai_intelligence/digital_twin/`
- `modules/communication/moltbot_bridge/`
- `modules/infrastructure/wre_core/`
- `modules/infrastructure/foundups_mcp_bridge/`
- `extensions/reddog/`
- `modules/foundups/pfmall/`
- `public/member/RED_DOG_DIGITAL_TWIN_CONTRACT.md`
- `docs/architecture/REDDOG_FOUNDUPS_SECOND_BRAIN_ARCHITECTURE.md`
- `docs/audits/architecture/REDDOG_DIGITAL_TWIN_CONVERSATION_PLANE_PHASE1.md`

Historical II-Agent/CommonGround, FastAPI/WebSocket, Docker, YAML-profile,
video-training, and browser-routing material from WSP 73 remains available in
Git history and its owning module documentation. Those implementation choices
are donors, not mandatory Digital Twin topology. WSP 73 owns the identity and
authority invariants above; module documents own implementation detail.
