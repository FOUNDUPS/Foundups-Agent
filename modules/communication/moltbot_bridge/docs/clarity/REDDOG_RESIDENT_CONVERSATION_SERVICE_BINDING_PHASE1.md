# Assumption Audit: RedDog Resident Conversation Service Binding Phase 1

## 1. Problem Statement

- **What**: Bind one validated `reddog_resident_conversation_request.v1`
  envelope to one authenticated, current AgentDB conversation-scope revision.
- **Why**: The transport envelope is intentionally zero-authority. A VSIX or
  PFMall adapter cannot safely use it until resident authority and durable
  conversation state are verified together.
- **Who**: Authorized by 012; executed by `0102/architect` on 2026-08-22.

This phase is admission-only. It does not create a network endpoint, create a
conversation, reserve a revision, persist an idempotency key, invoke a model,
dispatch a worker, or mutate AgentDB.

## 2. WSP 15 Allocation

- Receipt: `sha256:65476fbc497c4aba12f5d4eb2b058d55801eecc757f4376b7fa3afe1ae2aea05`
- Scores: complexity `5`, importance `5`, deferability `4`, impact `5`
- Total/priority: `19 / P0`
- Reasoning tier: `ULTRA`
- Execution plane: local code and tests; WRE runtime attachment is not part of
  this layer.
- Final allocation is bound to all 15 changed paths and five directly read
  authority/transport sources; its canonical validator accepts with no
  rejection reasons.

## 3. Retrieval Evaluation

- Exact owner query: `CURRENT`, `index_gap_detected=false`, sealed replica;
  no reindex was run.
- Broad-query precision was low: the durable AgentDB cycle ranked first, but
  the exact transport and session-authority contracts were absent.
- A tightened exact-symbol query found the transport contract, scope store,
  scope capability, pending store, lifecycle tests, and session-source tests.
- Ordering improved, but one unrelated permission module remained and the
  transport contract appeared twice across code/symbol result sets.
- Tier-0 module documents did not rank in the Holo result. The required
  `README.md`, `INTERFACE.md`, `ROADMAP.md`, `ModLog.md`, `tests/README.md`,
  and `tests/TestModLog.md` were therefore read directly as explicit
  must-includes.
- Staleness risk is low because the query reported exact-current HEAD and no
  index gap. The ranking noise is recorded but does not justify an index
  mutation in this transaction.

## 4. Assumptions

| ID | Assumption | Evidence | Confidence |
|---|---|---|---|
| A1 | Client identity and FoundUp scope must never come from the envelope. | `resident_conversation_transport_contract.py`; injected identity/routing fields reject. | HIGH |
| A2 | The existing opaque conversation capability is the correct one-use identity proof. | `reddog_conversation_scope_capability.py`; capabilities are process-local, one-use, immutable, and scope-restricted. | HIGH |
| A3 | The current AgentDB record is authoritative only after structural, digest, authority, and record-authentication verification. | `reddog_conversation_scope_store.py`; `reddog_authenticated_conversation_scope_state.py`. | HIGH |
| A4 | Admission can bind a CAS precondition but cannot reserve it. | The store mutates only through compare-and-swap; this phase performs no mutation. | HIGH |
| A5 | A new conversation cannot be derived from operator text alone. | Scope creation also requires host-selected scope, grounding/snapshot inputs, and authenticated authority. | HIGH |
| A6 | Request nonce/idempotency fields are equality inputs, not durable replay prevention, until a resident request journal exists. | The envelope has no persistence and its digest is explicitly non-authenticating. | HIGH |

## 5. Failure Modes

| ID | Failure Mode | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| F1 | Forged or replayed capability admits another principal/session. | LOW | CRITICAL | Consume the existing opaque capability once; verify exact scope, authority fields, and authenticated record. |
| F2 | State changes after admission but before a later operation. | MEDIUM | HIGH | Mark the result non-reserving; every later mutation must repeat current-record authentication and AgentDB CAS. |
| F3 | New-scope defaults silently select a FoundUp or scope kind. | MEDIUM | HIGH | Reject empty conversation IDs with `resident_conversation_new_scope_resolution_required`. |
| F4 | STATUS/CANCEL targets a stale or different turn. | MEDIUM | HIGH | Require the request turn ID to equal the current stored turn and require the exact revision. |
| F5 | Operator text or principal/FoundUp identifiers leak into receipts. | LOW | HIGH | Emit only digest-shaped request/state bindings and explicit no-authority flags. |
| F6 | A request is replayed with a newly issued capability. | MEDIUM | HIGH | Do not execute any operation in this phase; require a durable idempotency journal before handlers are enabled. |
| F7 | Store errors reveal whether a conversation exists. | MEDIUM | MEDIUM | Collapse missing, malformed, and unavailable load outcomes to the same access-denied result. |

## 6. Alternatives Considered

| Alternative | Why Rejected |
|---|---|
| Add an HTTP/WebSocket service now | Prematurely combines ingress, authentication, state, idempotency, and execution before the authority/CAS seam is proven. |
| Reuse the architect intent-coupled session source as the chat service | Its binding is intentionally tied to an already-grounded resident work intent; a conversation turn is earlier and broader than that boundary. |
| Advance or cancel AgentDB state during admission | The envelope does not contain the trusted continuity patch, grounding, or cancellation-state contract required for a valid mutation. |
| Create a second conversation database | Duplicates the existing AgentDB store and breaks the single durable authority boundary. |
| Put the bridge in the Digital Twin module | The Digital Twin owns the zero-authority client contract; authentication and AgentDB state belong to the resident communication module. |

## 7. Decision Record

- **Decision**: PROCEED
- **Owner**: `0102/architect`
- **Timestamp**: `2026-08-22`
- **Boundary**: Existing conversations only; admission result is content-free,
  non-reserving, non-persistent, and grants no identity, model, work, or effect
  authority.
- **Required follow-ons before a live adapter**: trusted new-scope resolution,
  durable idempotency/replay journal, operation-specific TURN/STATUS/CANCEL
  handlers, and immediate pre-mutation CAS revalidation.

## 8. Verification Record

- Focused admission tests: `15 passed`; statement and branch coverage:
  `106/106` statements and `24/24` branches.
- Cross-module transport/authentication/signing/tamper/WSP-62 matrix:
  `130 passed` with importlib collection.
- Focused binding plus module exemption gates: `31 passed`.
- Full local bridge closure: `6,220 passed`, `47 skipped`, `45 failed` in
  `17m24s`. At exact parent `f06ca1fcc4acc9e2645a3ed898bad844ac6df298`,
  44 failure node IDs reproduce. The remaining node passes at the parent and
  in isolated candidate execution, proving order pollution rather than a
  persistent candidate failure. This is differential evidence, not a clean
  promotion-suite claim.
- Repository-wide FMAS is not clean because of missing security-audit tools
  and inherited structure/parse/exemption debt. Independent CI is still the
  publication authority.
