# moltbot_bridge Roadmap

- CURRENT EXACT-MAIN EVIDENCE: after the earlier `61c2c300` canary and manual
  `a7302344` recovery, the automatic post-merge transaction completed through
  the real broker-managed OpenClaw supervisor at exact main `cfd1e0051`,
  generation `sha256:60d06274...`. AgentDB claim/completion bindings validated;
  a fresh owner query returned CURRENT/no-gap/no-reindex and full immutable
  revalidation preserved all 33 artifacts. This closes the automatic
  activation-order candidate gate for that commit only.

- IMPLEMENTED / HISTORICAL EXACT-HEAD CANARY EVIDENCE: the default resident/OpenClaw read-only audit worker now reaches
  the verified Holo query-replica resolver through the existing one-shot owner
  bridge. Complete owner lifecycles are serialized, the child/parent deadline
  is bounded, response/receipt bindings are reverified, and only scoped hit
  metadata enters the worker. The 60-second parent wall gives the child at most
  57 seconds and retains three seconds for cleanup. The prior 27-second child
  budget failed a real cold query; the repaired default completed CURRENT in
  32.5 seconds. Commit-bound activation and owner-query evidence passed at
  `61c2c3003bc4c2086f105f4c39effd499a026627` on 2026-08-27; it does not
  authorize this candidate or any later commit. Fusion receives no private route state and no
  Hermes dispatch is performed. P1 scale debt remains: the safe phase-1 path serializes only
  within one process and starts a bounded one-shot process per Holo query; a
  future supervised owner lease may reduce cross-process contention and
  cold-start cost without weakening proof.
- P1 SCALE DEBT: concurrent one-shot owner startups can still fail closed with
  `HOLOINDEX_QUERY_SERVICE_PORT_IN_USE`. A supervised cross-process owner
  lease/reuse boundary must preserve the same route, cleanup, and receipt proof.
- P0 DESIGN REQUIRED: a committed feature branch whose HEAD advances beyond
  the sealed authority is correctly rejected today. Normal post-commit IDE
  recall needs a bounded, independently verified branch-overlay design (or an
  equally strong per-commit replica path) before it may report CURRENT/no-gap;
  the same-HEAD gate must not be weakened to simulate freshness.
- COMPLETE: bounded FoundUps Fusion, OpenClaw gateway, and Hermes API artifact
  providers consume one shared verified runtime-topology capability. Exact
  role/provider/model identity and explicit available-provider inventory are
  checked at use time; stale, replayed, unavailable, or retargeted bindings
  reject before provider/worker egress. Static RedDog evaluation fallback does
  not enter the resident worker path.
- DEPLOYMENT REQUIRED: production model routes still depend on independently
  supplied signed production evidence, trust/revocation inputs, current runtime
  binding artifacts, and provider credentials. This bridge does not sign,
  select champions, or make aggregate panel promotion authoritative.
- COMPLETE: architect FIX promotion resolves the explicit active HoloIndex
  query-replica capability and passes it into exact owner binding verification.
  Input preparation and locked publication execution are bounded modules; the
  public startup adapter retains its API without a WSP 62 exemption. Live
  replica materialization and retention remain outside promotion.
- COMPLETE: the signed-worker queue-loop environment projection is separated
  from effectful dependency construction. The runtime binding and projection
  modules now remain below 500 lines with every function at most 50 lines.

- COMPLETE: RedDog repository-state v2 intake consumes only the extension's
  digest-only executable v1 public projection and strictly validates bounded
  identity/signature/verifier shape. Raw executable paths and ambient Python Git
  subprocesses are absent. Independent origin authentication and Git DLL/helper
  closure remain explicitly outside this receipt proof.

- COMPLETE: canonical HIGH-tier consensus capability binds the exact delegated
  request, author model/runtime evidence, sovereign authorization, reviewer
  principal/provider/role membership, distinct reviewer keys/models/runtime
  bindings, and the exact two signer requests. Signer admission reserves replay
  state transactionally and commits only after accepted signing.
- BLOCKED: production HIGH authority composition until signed E0 supplies the
  authoritative author/reviewer/runtime/policy/sovereign resolvers and a durable
  consensus nonce authority. ULTRA and the production live canary remain closed.
- COMPLETE: LOW-tier independent signer secret-grant provider foundation and strict grant
  domain with durable signed-policy rate admission, distinct caller/beneficiary
  identity, public response verification and one generation lease.
- COMPLETE: root-bound owner policy v6 preserves v5 compatibility and binds
  the grant-service signer profile, public identity, key-reference hashes,
  permission evidence identifiers, signed manifest generation, config, run
  packet, and content-addressed service archive. The v2 manifest covers exactly
  those three grant artifacts; every binding reloads current signed E0 and
  re-verifies the exact bytes under the runtime-generation lock. Downgrade,
  cross-role key aliasing, and substitution reject before secret resolution or
  service start.
- COMPLETE: owner config v3 and the uncomposed independent-grant client supply
  bind a disjoint Unix socket plus exact non-root peer UID/GID to signed policy.
- COMPLETE: owner config v4 binds the canonical grant-service source map to the
  existing root-owned configuration and exposes it only through an opaque,
  revalidatable process capability. V3 retains grant-client compatibility but
  cannot authorize a build source policy.
- COMPLETE (UNCOMPOSED): the existing atomic signer-generation provisioner can
  consume that capability through a fixed grant-profile context, config v2, a
  shared root-owner operation fence, profile-derived three-artifact leases,
  source-policy revalidation at production/commit/recovery, and durable
  generation binding. No production bootstrap calls it yet. WSP 15: C4 + I5 +
  D5 + Im5 = 19/20, P0.
- COMPLETE: deterministic grant-service zipapp validation at manifest
  production and use time. Canonical ZIP bytes, exact member digests, package
  structure, direct static-import references, common loader defenses, and the
  fixed synchronous `main()` ABI fail closed. This is not a Python sandbox.
  Claimed source metadata is not Git
  provenance, and the archive is never launched by this layer.
- COMPLETE: exact-Git grant-authority effect admission. The v2 inner archive,
  owner policy v7 and runtime manifest v3 bind each non-synthetic member to one
  exact commit-tree blob, explicit source-path policy and authority repository.
  Signing, current-generation rehydration and final WSP 71 use re-read bounded
  Git objects; legacy v6/v2 remains inspection-only and cannot produce effects.
- COMPLETE: grant-service WSP 71 permission receipt rehydration. Exact canonical
  bytes and receipt ID follow the acyclic receipt -> config -> manifest -> E0
  trust chain. One callback runs only while the current E0 lease and matching
  durable revocation fence remain held; no reusable permission object escapes.
  Root-generation, grant, revocation and target-signer keys are role-distinct.
- BLOCKED: pinned-byte launch, grant-service isolation, resolver composition,
  external lifecycle supervision and the live canary remain next. Atomic
  provisioning does not launch a service, resolve a secret, execute repository
  work or prove production readiness.

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
- COMPLETE: admission-only binding of an existing transport envelope to one
  consumed session capability and exact authenticated AgentDB CAS revision.
  One atomic capability operation retires the verified secret-backed parent,
  re-verifies the exact record, and issues at most one opaque child bound to the
  canonical reservation identity; the process-local proof stays out of output.
- COMPLETE: durable, content-free AgentDB request reservation with exact replay,
  divergent global key/request/nonce rejection, bounded serialized capacity,
  SQLite/PostgreSQL locking, and an atomic current unexpired scope revision/
  digest/revision-receipt fence. The store consumes the binder proof before
  database access and uses its owned clock to prevent expiry backdating. It
  does not reserve conversation CAS or authorize handler execution.
- COMPLETE: inert current-generation admission aggregation for existing
  conversations. One host call prevalidates the request before credential use,
  holds the signed-generation lease through authority-native scope binding and
  durable reservation, consumes the verified parent, and returns only the
  existing content-free result. It is not wired to traffic or handlers.
- COMPLETE: trusted empty-ID TURN resolution and current-generation new-scope
  persistence. Exact extension intent, request, grounding, and registered
  FoundUp bindings are checked before credential use; the generation lease and
  E0 signer cover authority-native AgentDB create/exact recovery. Signed session
  identity fences nonce divergence, and scope lifetime spans the request.
- COMPLETE: durable first-turn request-to-resolved-conversation journal
  binding. One signed-session lease produces two separately registered one-use
  FoundUp authorities; E0 create/exact recovery and the explicit v2
  `RESOLVED_INITIAL_TURN` journal fence therefore share one credential/
  generation boundary. Exact authenticated replay remains valid through later
  signed revisions by checking the immutable E0 receipt chain and its signed
  source/resolved request commitment; replay authority consumption is atomic.
- COMPLETE: the two legacy WSP 62 ratchet failures are repaired without a
  ceiling increase. Mapping-list recursion is an owned helper and
  `_visit_type_paths` is 59 lines. The bootstrap result schema and bounded
  projections are a 286-line sibling; the public bootstrap surface is
  identity-preserving and the host fell from 858 to 615 lines.
- WSP 15 FOLLOW-UP: decompose the unchanged 432-line
  `run_reddog_main_readonly_operational_bootstrap` entrypoint by lifecycle
  ownership. Its exact function and host-file no-growth ratchets remain active;
  this result-only extraction does not claim the orchestration monolith is
  fully WSP 62 compliant.
- BLOCKED: principal-side credential issuance UX, host invocation wiring, and
  operation-specific TURN/STATUS/CANCEL handlers with immediate authenticated
  CAS. Environment principal/FoundUp values are not authentication.
- COMPLETE: one authenticated scope revision and resident intent can be bound
  to an immutable architect proposal preview. AgentDB CAS stores the exact
  pending proposal; backend determination rejects stale snapshot/HEAD/Holo
  context before Fusion; signed WSP 15 promotion requires a fresh one-use
  pending capability plus the existing principal-signed proposal policy.
- BLOCKED: editor/runtime conversation-to-proposal consumption until the host
  adapter supplies the verified capability and downstream mutations repeat
  authenticated current-record/CAS checks.
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
- COMPLETE: an independently signed revocation-snapshot contract binds the
  exact current E0 policy, generation, authority, target signer, and durable
  store. Grant/revocation/target-signer authority collapse rejects.
- COMPLETE: the uncomposed local durability foundation uses an application-
  append-only primary log, a separately rooted monotonic witness, signed exact
  topology, spawned-process crash recovery, and a cross-process use fence. It
  detects primary-only rollback but does not claim coordinated local-domain
  rollback resistance or production authority.
- COMPLETE: owner policy v3 binds the identity, durability receipt, and
  three-domain topology digest of the existing root-owned monotonic state.
  The uncomposed publisher and oracle require that domain-separated anchor, so
  coordinated rollback of the two revocation-local domains rejects while the
  root state remains intact. The dynamic high-water has two root-owned mirrors;
  coordinated rollback of both is root-authority compromise and remains
  outside this slice. The static installation domain does not witness each
  high-water update.
- COMPLETE: the existing root service now admits an opaque protected-use
  client and atomically orders signed use-ID consumption, ACQUIRE, one exact
  signer callback, FINISH, and revocation advancement. Both race orderings,
  replay, lost FINISH response, active-use crash, peer/policy/context
  substitution, and Linux-root socket transport fail closed.
- COMPLETE: an uncomposed WSP 71 op CLI resolver factory requires a fixed,
  root-owned executable with secure ancestry and no group/other write access.
- NEXT: independently administered grant-service composition and lifecycle,
  including production E0 provider/backend composition, WSP 71
  resolve-per-sign composition, native-memory
  zeroization evidence, and supervised handling of a crashed active use.
  The protected-use client is available through the current owner-config
  loader, but no production grant issuer or service startup path consumes it.
  Socket v1
  remains compatible but cannot reach the resolve-per-sign backend.
- BLOCKED: durable system-service deployment and no-work-authority Linux
  canary until production grant/revocation authority, secret resolution,
  zeroization, and lifecycle supervision slices pass.

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
  Hermes requires one native, stable, completed leaf delegate with only
  `delegate_task`, zero skills, and zero child file effects before and after
  each run. Neither provider owns Foundups repository effects. Live bounded
  GotJunk canaries now prove both upstream runtimes can return accepted artifacts.
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
   - Status: LANDED in PR #1015 (`3fe2feb72`); current code remains a
     read-only deterministic assembly surface, not a live memory writer.
   - Entity: `foundups-agent`.
   - Canonical adapter: `src/foundup_memex_current_state.py`.
   - Compatibility component: `src/foundup_brain_current_state.py`.
   - Read-only deterministic view from an accepted operational snapshot.
   - No memory, roadmap, queue, worker, repository, governance, or HoloIndex mutation.

### MVP sequence

2. `FOUNDUP_MEMEX_LEARNING_CANDIDATE_GATE_PHASE1`
   - Status: IMPLEMENTED_NOT_RUNTIME_ADMITTED on the current candidate branch.
   - Convert scoped Breadcrumbs and verified outcomes into evidence-backed
     learning candidates. Governed research is declared but fail-closed until
     an authenticated research-receipt authority is integrated.
   - No durable Brain write.
   - The structural gate preserves contradictions, supersession pointers,
     proposed salience/confidence, canonical bounded inputs, exact upstream
     view receipts, and proposal-bound reconstructable source-receipt closure.
     Live source adapters and durable admission remain deferred.
   - AutoResearch follow-up must retain a deterministic incumbent and use a
     frozen held-out corpus. Primary metrics are reconstruction fidelity,
     contradiction retention, false-merge/false-forget rate, semantic token
     compression, retrieval quality, and latency. WRE may coordinate bounded
     experiments but is not promotion or memory-write authority.

3. `FOUNDUP_MEMEX_GOVERNED_BRAIN_CONSOLIDATION_PHASE1`
   - Status: SPECIFIED_NOT_IMPLEMENTED.
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
