# moltbot_bridge Roadmap

## RedDog execution-valve readiness

- Phase 1 safety wiring complete locally: token-free canonical supplier,
  bootstrap-to-handler canonical routing, secure use-time reload, signed
  authority re-verification, process-local single-use effect admissions, and
  fail-closed decision lineage. Persisted results are audit-only. Queue and
  use-time preflight are non-consuming; after every non-mutating gate passes,
  the final worktree/live-enqueue boundary consumes the nonce lease exactly once.
- Operational status is BLOCKED, not READY. Next gates are independently signed
  descriptor-derived artifact manifests; verified consensus and sovereign
  receipts; authenticated principal/model trust provenance; a fresh client-side
  signer handshake. Closed attempts do not consume nonce state.
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

- Complete post-merge activation at the exact merge SHA before treating the
  persistent semantic store as CURRENT.
- Bind resident governed work orders to process-private owner handoffs without
  adding an indexing surface to the supported query adapter; OS permissions
  remain a separate deployment control.
- Split reddog_readonly_0102_audit_worker_runtime.py by evidence acquisition,
  freshness normalization, model invocation, and receipt composition.
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
