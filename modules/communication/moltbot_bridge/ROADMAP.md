# moltbot_bridge Roadmap

## RedDog conversational work promotion

- COMPLETE: raw provider history is denied by default and continuation
  telemetry reflects the actual admitted context.
- COMPLETE: AgentDB-backed authenticated conversation scope with insert-only
  creation, CAS revisions, expiry, FoundUp and session scope, typed continuity,
  current grounding, snapshot/HEAD/Holo bindings, opaque one-use session
  capabilities, authenticated records, and bounded projections.
- COMPLETE: editor source for pre-issued principal-signed conversation
  credentials. Verification is public-key-only and binds repository, audience,
  transport, TTL, principal, FoundUp, current generation, intent and grounding.
- BLOCKED: principal-side credential issuance UX and P1 durable-scope runtime
  consumption. Environment principal/FoundUp values are not authentication.
- COMPLETE: one authenticated scope revision and resident intent can be bound
  to an immutable architect proposal preview. AgentDB CAS stores the exact
  pending proposal; backend determination rejects stale snapshot/HEAD/Holo
  context before Fusion; signed WSP 15 promotion requires a fresh one-use
  pending capability plus the existing principal-signed proposal policy.
- BLOCKED: editor/runtime conversation-to-proposal consumption until the
  verified session receipt is connected to the existing P1/P2 APIs.
- HELD: OpenClaw/Hermes dispatch until the editor/runtime binding and all
  existing WRE work-order gates pass.

## Stable External Signer Lifecycle

- COMPLETE: the external signer can sign one canonical authoritative-use lease
  for an exact `worktree_create` or `live_enqueue` request through the existing
  strict socket-v2 secret-grant boundary. The consumer rehydrates only verified
  signature and audit evidence against current root-owned generation artifacts
  and the existing durable E0 replay store. The signed typed effect payload is
  recomputed signer-side; socket v1 and noncanonical JSON reject. Current config
  selects the signer profile/key/epoch, all four E0 replay identities match on
  both sides, and lease lifetime cannot exceed current-generation selection.
- BLOCKED: production lease issuance and effect activation. There is no local
  grant issuer, and the resident resolver still requires all current lifecycle,
  generation, authority, and deployment anchors. Queue dispatch, assurance,
  model/artifact generation, commit, verification, PR publication, learning,
  and merge each require their own exact-effect admission before autonomous
  production use. Crash recovery must distinguish authorized, applied, and
  indeterminate effects without replay.
- COMPLETE: current authenticated signer generation selection.
- COMPLETE: policy-less key profiles cannot sign delegated identity or work
  authority. Resolve-per-sign binds a real ephemeral backend to the exact
  independently authenticated E0 grant request.
- COMPLETE: stable signer-owned system-service entrypoint and v2 packet
  binding.
- COMPLETE: signer-side socket v2 admission binds one authenticated grant to
  the exact request, operation, authority tier, peer principal, profile,
  permission snapshot, owner configuration, and signer generation. The grant
  is consumed through pre-provisioned disjoint replay state before one fresh
  ephemeral backend construction. Its signature is independently verified
  while one signer-owned revocation fence covers the complete sign operation;
  missing stores and backend-authored rejection payloads fail closed.
- COMPLETE: owner-controlled E0 composition admission consumes one opaque
  current-generation selection, requires that signed generation to pin the
  complete E0 authority-scope digest and principal artifact, independently
  verifies the signed owner policy and both authority keys, and releases one
  process-local capability. Capability consumption revalidates under the
  shared generation fence and returns only a non-authoritative receipt. It
  performs no secret resolution, socket binding, or signer start.
- NEXT: independently administered grant and revocation supply, WSP 71
  permissioned resolver composition, and native-memory zeroization evidence
  entrypoint. Socket v1 remains compatible but cannot reach the resolve-per-sign
  backend.
- BLOCKED: durable system-service deployment and no-work-authority Linux
  canary until grant/revocation supply, secret resolution, zeroization, and lifecycle
  supervision slices pass.

## RedDog provider-call evidence follow-ups

- Phase 2a covers only the governed repo-audit and backend-architect in-process
  FoundUps Fusion entry paths with one durable, generic content-free receipt.
- Review repair complete: typed served-identity parsers, exact audit/architect
  acceptance lineage gates, post-invocation extraction failure evidence,
  frozen legacy-v1 progress compatibility, and platform-neutral WSP 62
  exemption matching are covered by adversarial regressions.
- Final review repair: requested identities use the same typed grammar, and
  acceptance compares the complete invocation lineage plus requested runtime
  identity; unbound lineage fields must remain null.
- Next: make the Fusion/OpenRouter gateway return authoritative served
  provider/model and normalized numeric usage evidence. Until then those
  fields remain null; configuration is never evidence of service.
- Complete: actual upstream OpenClaw Gateway and Hermes API artifact providers
  emit the canonical effect receipt. OpenClaw is exact-session sandboxed;
  Hermes is text-only and requires a disabled tool/skill surface before and
  after each run plus a complete effect-free SSE event history. Neither
  provider owns Foundups repository effects.
- Next: bind authoritative served provider/model and normalized usage evidence
  from both upstream response surfaces without trusting requested identity.
- Next: extract the atomic store from the focused contract module after
  cross-surface parity is stable, retiring the temporary WSP 62 ceiling.
- Next: extract the backend architect model-call and accepted-receipt
  composition transaction behind a focused internal boundary, then retire its
  temporary WSP 62 ceiling without changing determination/queue identities.

## FoundUp scaffold routing

- Completed prerequisite: canonical `FoundUpJob` now carries typed
  `new_scaffold`, genesis-envelope, and scaffold-contract lineage bindings for
  WRE's distinct dry-run scaffold route.
- Still deferred: live scaffold writer, registry mutation, worktree creation,
  provider/model execution, capability certification, and launch authority.

## Create FoundUp job contract WSP62 decomposition

The canonical `src/foundup_job_contract.py` remains an inherited 796-line
contract surface after the nullable create-route lineage fields were added.
Its temporary module exemption is an exact, non-ratcheting 796-line ceiling.

Before 2026-09-30, split serialization, validation, and action-specific
contract helpers into cohesive modules while preserving the public import and
wire-format compatibility. Remove the exemption once the canonical contract
file is at or below the WSP 62 file threshold; do not widen the ceiling.

## RedDog execution-valve readiness

- Architect proposal admission is complete: audit-supported validity is
  recorded separately from current execution readiness, and signed WSP 15
  promotion rechecks the canonical admission receipt, current repository HEAD,
  HoloIndex freshness receipt, work-state revision, platform, and code-owned
  trust-anchor capabilities.
  Valid prerequisite work may remain a blocked candidate and may enter the
  authoritative queue only after proposal authenticity is cryptographically
  verified. It still cannot execute until a fresh use-time determination
  observes every required capability. SHA-bound proposal receipts remain
  integrity-only and never establish readiness.
- Phase 1 safety wiring complete locally: token-free canonical supplier,
  bootstrap-to-handler canonical routing, secure use-time reload, signed
  authority re-verification, process-local single-use effect admissions, and
  fail-closed decision lineage. Persisted results are audit-only. Queue and
  use-time preflight are non-consuming; after every non-mutating gate passes,
  the final worktree/live-enqueue boundary consumes the nonce lease exactly once.
- Current-generation use-time concatenation is complete for three existing
  trust primitives. After signed work-authority re-verification, the resolver
  consumes the root-owned system-service selection boundary, verifies the
  exact current manifest/config/run-packet generation and durable replay
  high-water state, and records a non-authoritative audit receipt. Trusted-clock
  manifest freshness is checked independently of the selection owner's wall
  clock. No local effect lease is minted. This discharges only
  the authenticated-manifest, replay/high-water, and current-generation blockers.
  Failed, stale, malformed, or substituted evidence cannot authorize an effect.
- Operational status is BLOCKED, not READY. Next gates are independently signed
  descriptor-derived artifact manifests; verified consensus and sovereign
  receipts; authenticated principal/model trust provenance; a fresh client-side
  signer handshake. Closed attempts do not consume nonce state.
- Signed artifact manifests, signer mutual handshake, authenticated generation
  state, authenticated transactional high-water persistence, generation-root-
  first atomic provisioning on Windows, verifier-only lifecycle reads,
  authenticated current-generation manifest launch selection, a descriptor-
  bound root-owned Linux/WSL signer-service selection loader, kernel
  process/socket observation,
  and opaque lifecycle admission are implemented.
  POSIX/WSL activation fails closed because same-principal file modes cannot
  prevent pre-open descriptor writes or atomic replacement. It remains blocked
  until the external signer owner supplies a distinct-principal activation
  lease and lifecycle supervision.
  Independently administered production high-water authority issuance and the
  external system-service deployment/lease owner remain
  SPECIFIED_NOT_IMPLEMENTED. Use-time valve consumption now verifies the
  current-generation selection, but remains blocked by peer-handshake
  re-observation, external effect-lease issuance, and the six other named trust
  anchors.
- Only after those anchors and adversarial live-path tests are green may an
  operator run the Linux live canary; merge authority remains unavailable.

## FoundUps Memex lane

The FoundUp Memex grows from existing RedDog operational context, Brain,
Breadcrumbs, authoritative work state, HoloIndex repository truth, verified
outcomes, and roadmap receipts. Brain remains the durable-consolidation
component inside the Memex. The lane does not begin as a separate personal
second-brain database.

### POC

1. `FOUNDUP_MEMEX_CURRENT_STATE_ASSEMBLY_PHASE1`
   - Status: implementation in PR #1015.
   - Entity: `foundups-agent`.
   - Canonical adapter: `src/foundup_memex_current_state.py`.
   - Compatibility component: `src/foundup_brain_current_state.py`.
   - Read-only deterministic view from an accepted operational snapshot.
   - No memory, roadmap, queue, worker, repository, governance, or HoloIndex mutation.

### MVP sequence

2. `FOUNDUP_MEMEX_LEARNING_CANDIDATE_GATE_PHASE1`
   - Convert scoped Breadcrumbs, verified outcomes, and governed research
     receipts into evidence-backed learning candidates.
   - No durable Brain write.

3. `FOUNDUP_MEMEX_GOVERNED_BRAIN_CONSOLIDATION_PHASE1`
   - Admit accepted learning candidates into the existing Brain through a
     provenance, contradiction, supersession, and authority gate.

4. `FOUNDUP_ADAPTIVE_ROADMAP_DELTA_PROPOSAL_PHASE1`
   - Produce roadmap deltas from accepted learning and external change signals.
   - Proposal only; no roadmap mutation.

5. `FOUNDUP_ADAPTIVE_ROADMAP_GOVERNANCE_GATE_PHASE1`
   - Accept, reject, or defer roadmap deltas with recorded rationale.

6. `FOUNDUP_MEMEX_MULTI_ENTITY_ISOLATION_PHASE1`
   - Generalize the proven Foundups Agent POC to independently scoped FoundUps.

### Prototype sequence

7. `FOUNDUP_MEMEX_MULTI_REDDOG_COLLABORATION_PROTOTYPE_PHASE1`
   - Permit multiple RedDogs to contribute through verified, scoped receipts.
   - No CABR or delegated authority until a separate contract is ratified.

8. `FOUNDUP_MEMEX_CABR_DELEGATED_AUTHORITY_CONTRACT_PHASE1`
   - Deferred research placeholder only.
   - Revisit stakeholder, delegate, revocation, Sybil resistance, and CABR scoring.

### Deferred applications

- `REDDOG_012_PERSONAL_MEMEX_PHASE1`
- `FOUNDUPS_COLLECTIVE_MEMEX_EXCHANGE_PHASE1`

These remain deferred until the FoundUp Memex POC and MVP contracts are proven.

## Invariants

- Operate in WSP_00 and apply WSP_97 before each slice.
- RedDog is focused on launching, building, running, and improving FoundUps.
- HoloIndex remains canonical for repository facts.
- Brain and Breadcrumbs remain separate sources with separate receipts.
- Current repo/work state overrides historical memory when they conflict.
- Agents propose learning and roadmap changes; they do not directly rewrite durable cognition.
- Every Memex view, learning candidate, and roadmap proposal binds to exact `foundup_id` and `snapshot_id` receipts.
- No CABR, stakeholder, or delegate status grants runtime authority during POC or MVP.

## 2026-07-18: RedDog / HoloIndex Truth Boundary Follow-ups

- Completed 2026-07-24 P0: direct diagnostics now share the canonical
  root/SSD/HEAD/generation/baseline/maintenance admission proof before backend
  construction. P1 store namespaces and legacy metadata migration remain owned
  by the HoloIndex roadmap.
- Completed Phase 1 exact-SHA post-merge activation: durable AgentDB task,
  OpenClaw CAS claim, authority/SSD leases, atomic completion, and canonical
  receipt rehydration. CI/webhook-triggered enqueue remains a future event
  source; the current resident observer is opt-in and bounded.
- Bind resident governed work orders to process-private owner handoffs without
  adding an indexing surface to the supported query adapter; OS permissions
  remain a separate deployment control.
- Split reddog_readonly_0102_audit_worker_runtime.py by evidence acquisition,
  freshness normalization, model invocation, and receipt composition.
- Extract the duplicated audit/architect runtime-binding rehydration and
  topology projection into a focused contract module after Phase 1 parity is
  stable. Until then, keep the two surface constants and rejection semantics
  covered by cross-surface tests; do not broaden either production surface.
- Continue extracting main.py RedDog preflight and dispatch policy into
  cohesive module-owned helpers; do not add new orchestration branches to the
  root monolith.
- Keep communication tests below the domain threshold by separating owner
  client, adapter, direct diagnostics, maintenance dispatch, and downstream
  operational consumers.
- Migrate or explicitly retire the legacy foundups_mcp_bridge `holo_tools.py`
  direct-store consumer; Phase 1 covers only the wired RedDog operational
  consumers.
- Decompose `ground_transport_work_focus` into request validation, target
  classification, owner preflight, and receipt composition after the bounded
  repository-audit fallback stabilizes; the temporary WSP_62 exemption records
  this integration debt without expanding the runtime's authority.

These items are an explicit WSP_62 remediation register; no global compliance
claim is made while historical monolith debt remains.

## RedDog execution-valve trust-boundary decomposition

- Split the resident serial bootstrap into runtime-input loading, dependency
  assembly, handler construction, and bounded-loop coordination without
  changing canonical receipts.
- Extract delegated-authority request validation and signed model/Memex
  lineage assembly from the signer transaction boundary.
- Split worktree and OpenClaw effect transactions into preflight, effect
  attempt, reconciliation, and receipt modules while preserving stable attempt
  keys and truthful indeterminate outcomes.
- Decompose inherited end-to-end startup suites by stage contract. Temporary
  WSP_62 exemptions expire on 2026-09-30 and their exact no-growth ceilings are
  enforced by AST tests.
- Production remains `VALVE_CLOSED` until independent signed model-selection,
  Memex, runtime-artifact manifest, consensus, sovereign, principal-subject,
  and signer peer-handshake anchors are implemented and adversarially verified.
