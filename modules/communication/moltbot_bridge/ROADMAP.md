# moltbot_bridge Roadmap

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
