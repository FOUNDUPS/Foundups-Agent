# WSP 98: FoundUps Mesh-Native Architecture Protocol

- **Status:** Active target protocol; mesh foundation is not implemented
- **Updated:** 2026-08-26
- **Purpose:** Define the constraints and evidence gates for evolving FoundUps
  from resident-hub deployments toward federated and peer-assisted operation.
- **Trigger:** Designing a FoundUp transport, federating RedDog services,
  distributing work or storage, or claiming mesh readiness.
- **Dependencies:** WSP 27, WSP 80, WSP 3, WSP 97, WSP 103, WSP 104

## 1. Truth boundary

WSP 98 describes a target architecture. It does not prove that a mesh SDK,
peer discovery, distributed storage, distributed compute, or zero-server
deployment exists.

At this repository revision:

| Claim | State |
|---|---|
| WSP 104 FoundUp namespace guardrails | Implemented protocol and supporting contracts |
| p.fMALL/member Progressive Web App shell | Implemented presentation surface |
| Authenticated p.fMALL/phone RedDog transport | Specified, not implemented |
| Universal JavaScript or Python mesh SDK | Not implemented |
| `modules/communication/liberty_alert/src/mesh_core.py` and sibling mesh modules | Not present |
| Peer-discovery, multi-hop, distributed storage, and distributed compute proofs | Not present |
| Zero-server FoundUps | Target, not an implementation claim |

The earlier protocol named absent modules, package versions, user-count
thresholds, and performance properties as though they existed. Those names
were illustrative and are not admissible evidence. A future implementation
must be discovered from the repository and admitted through the gates below.

## 2. Canonical terms

- **Mesh-native:** contracts do not assume one permanent host and can admit
  independently authenticated peers without moving authority into clients.
- **Peer-assisted:** a resident service remains available while peers provide
  bounded transport, cache, storage, or compute capabilities.
- **Federated:** multiple independently operated authorities exchange signed,
  scoped records under WSP 103.
- **Progressive Web App (PWA):** the installable browser presentation/runtime
  technology.
- **Progressive Web Agent:** the target FoundUp/DAE experience in which an
  installable surface can reach governed agent services. It is not proven by a
  web manifest or service worker alone.
- **DAE:** Decentralized or Distributed Autonomous Entity/Ecosystem as defined
  by WSP 27. "Digital Autonomous Entity" may describe its software embodiment,
  but does not replace the governance meaning.

## 3. Mandatory invariants

### 3.1 Identity and namespace

Before any peer or FoundUp is admitted:

- `foundup_id`, `routing_prefix=/f/{foundup_id}`, and
  `data_namespace=idb_{foundup_id}` satisfy WSP 104;
- principal, session, FoundUp, workspace, and capability scopes are explicit;
- browser/device claims are untrusted until authenticated by the owning
  authority; and
- no peer can widen another tenant's namespace or effect ceiling.

### 3.2 Authority remains separate from transport

Transport availability is not work authority. A peer message, model output,
RedDog turn, OpenClaw proposal, or Hermes result cannot authorize an effect.
Repository and process effects remain behind WRE admission and separately
authenticated work orders. Durable proposal provenance, authorization, and
receipts must survive peer retries and reordering.

### 3.3 Progressive enhancement

A FoundUp must remain safe when the mesh is absent, partitioned, stale, or
hostile. Public discovery and local presentation may degrade gracefully.
Protected reads, proposals, wallet operations, governance, and work execution
must fail closed when their current authority cannot be proved.

### 3.4 Data and privacy

- Data ownership, retention, replication, deletion, and jurisdiction are
  explicit per record class.
- Personally identifiable or principal-private data is not broadcast merely
  because encryption exists.
- Local-first storage is a preference, not permission to make browser storage
  authoritative for identity, replay protection, policy, or work receipts.
- Replication requires bounded payloads, authenticated provenance, conflict
  semantics, and revocation/tombstone behavior.

### 3.5 Cryptography

Do not prescribe a cipher, password derivation function, or key topology from
an example. Use reviewed platform protocols and libraries. A production slice
requires a separate threat model covering enrollment, peer authentication,
forward secrecy, rotation, revocation, recovery, metadata leakage, and key
custody.

### 3.6 Observability and verification

Every admitted peer operation exposes content-bounded evidence for:

- peer and capability identity;
- principal/FoundUp/session scope;
- request, result, and policy digests;
- ordering/idempotency state;
- expiry and revocation state; and
- whether an effect was proposed, authorized, attempted, or completed.

Availability, latency, scale, privacy, and resilience remain
`NEEDS_VERIFICATION` until measured under a named topology and failure model.

## 4. Target layered topology

```text
p.fMALL / phone / VSIX thin clients
              |
              | authenticated, replay-safe turns
              v
RedDog / principal-scoped 0102 conversation services
              |
              +-- Principal Memex and scoped FoundUp Memex reads
              +-- HoloIndex repository retrieval
              |
              | proposal-to-work promotion
              v
OpenClaw policy/control supervisor
              |
              v
WRE authority -> Hermes bounded leaf workers -> FoundUp DAEs
              |
              v
optional federation / peer-assisted transport, storage, and compute
```

RedDog is the lightweight interaction, exchange, and attention surface across
these clients; 0102 is the principal-scoped Digital Twin and deep cognition /
orchestration layer behind it. They form one continuous conversational
relationship but are not the same component. Neither is one browser, one
server, or one OpenClaw process. OpenClaw can host or supervise an execution
runtime; Hermes is a delegated worker boundary; WRE owns admitted execution. A
phone normally emits to the resident/federated hub rather than hosting that
complete stack.

## 5. Deployment progression

### Gate 0: Resident-hub baseline

- Authenticated RedDog conversation service.
- Durable event order, compare-and-swap, replay protection, and cancellation.
- Thin clients contain no standing model, memory, repository, or worker
  credentials.
- OpenClaw/WRE/Hermes effects remain separately admitted.

### Gate 1: Peer-assisted proof of concept

- One bounded, non-authoritative capability such as public-content cache or
  disposable compute.
- Two independently identified devices.
- Partition, replay, duplicate, revocation, and malicious-peer tests.
- Resident fallback and invariant-equivalent receipts.

### Gate 2: Federated prototype

- Multiple independently operated authorities.
- WSP 103 trust and route contracts.
- Shared ordering/conflict protocol and cross-tenant isolation evidence.
- Measured capacity and failure behavior; no extrapolated user thresholds.

### Gate 3: Mesh-capable MVP

- SDK and scaffold exist as versioned, tested packages.
- At least one FoundUp uses them without losing the resident-hub safety
  contract.
- Security review, upgrade/rollback, compatibility, and incident procedures
  are operational.
- Only then may FoundUp scaffolding require the verified mesh dependency.

### Gate 4: Reduced-server or server-independent operation

This is a separately proved deployment outcome, not the definition of mesh
readiness. Bootstrap discovery, identity recovery, durable ordering, policy,
wallet, and audit requirements must all have demonstrated replacements before
any "zero-server" claim is allowed.

## 6. Validation checklist

- [ ] WSP 104 namespace admission passes.
- [ ] Current repository modules and package identities are verified before
      documentation names them.
- [ ] Client, transport, policy, execution, and storage authorities are
      separate.
- [ ] Retry, replay, reordering, partition, revocation, and malicious-peer
      tests pass.
- [ ] Private data classes and retention rules are explicit.
- [ ] Cryptography and key custody have an independent threat review.
- [ ] Scale and resilience claims cite reproducible measurements.
- [ ] Non-mesh operation remains safe and truthful.
- [ ] WSP 97 labels distinguish observed, specified, target, and false claims.

## 7. Prohibited shortcuts

- Do not invent a universal SDK or dependency in documentation before code and
  package evidence exists.
- Do not equate PWA installability with a Progressive Web Agent or mesh node.
- Do not treat WebRTC, Bluetooth, Meshtastic, MCP, or any transport as identity
  or effect authority.
- Do not store authoritative RedDog session, wallet, policy, or receipt state
  in browser-local storage.
- Do not claim exponential scaling, zero cost, censorship resistance, privacy,
  or zero-server operation without a stated threat model and measurements.
- Do not implement a custom cryptographic protocol for convenience.

## 8. Related protocols and evidence

- WSP 27: DAE and FoundUp architecture
- WSP 73: 012 Digital Twin / RedDog architecture
- WSP 80: cube-level DAE orchestration
- WSP 97: truth-labelled system execution
- WSP 103: FoundUp federation
- WSP 104: route namespace and tenant isolation
- `public/member/RED_DOG_DIGITAL_TWIN_CONTRACT.md`
- `docs/audits/architecture/REDDOG_DIGITAL_TWIN_CONVERSATION_PLANE_PHASE1.md`

The next implementation is Gate 0's authenticated resident conversation
binding, not a speculative mesh SDK. Build and verify one layer before moving
to the next.
