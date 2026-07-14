# moltbot_bridge Roadmap

## FoundUp Brain lane

The FoundUp Brain grows from existing RedDog operational context, Brain,
Breadcrumbs, authoritative work state, HoloIndex repository truth, verified
outcomes, and roadmap receipts. It does not begin as a separate personal
second-brain database.

### POC

1. `FOUNDUP_BRAIN_CURRENT_STATE_ASSEMBLY_PHASE1`
   - Status: implementation in PR #1015.
   - Entity: `foundups-agent`.
   - Read-only deterministic view from an accepted operational snapshot.
   - No memory, roadmap, queue, worker, repository, or HoloIndex mutation.

### MVP sequence

2. `FOUNDUP_BRAIN_LEARNING_CANDIDATE_GATE_PHASE1`
   - Convert scoped Breadcrumbs, verified outcomes, and governed research
     receipts into evidence-backed learning candidates.
   - No durable Brain write.

3. `FOUNDUP_BRAIN_GOVERNED_CONSOLIDATION_PHASE1`
   - Admit accepted learning candidates into the existing Brain through a
     provenance, contradiction, supersession, and authority gate.

4. `FOUNDUP_ADAPTIVE_ROADMAP_DELTA_PROPOSAL_PHASE1`
   - Produce roadmap deltas from accepted learning and external change signals.
   - Proposal only; no roadmap mutation.

5. `FOUNDUP_ADAPTIVE_ROADMAP_GOVERNANCE_GATE_PHASE1`
   - Accept, reject, or defer roadmap deltas with recorded rationale.

6. `FOUNDUP_BRAIN_MULTI_ENTITY_ISOLATION_PHASE1`
   - Generalize the proven Foundups Agent POC to independently scoped FoundUps.
   - Require explicit `foundup_id` on work, roadmap, outcome, Brain, and
     Breadcrumb records before multi-entity mode is enabled.

### Deferred application

- `REDDOG_012_DIGITAL_TWIN_SECOND_BRAIN_PHASE1`
- `FOUNDUPS_COLLECTIVE_MEMORY_EXCHANGE_PHASE1`

These remain deferred until the FoundUp Brain POC and MVP contracts are proven.

## Invariants

- Operate in WSP_00 and apply WSP_97 before each slice.
- HoloIndex remains canonical for repository facts.
- Brain and Breadcrumbs remain separate sources with separate receipts.
- Current repo/work state overrides historical memory when they conflict.
- Agents propose learning and roadmap changes; they do not directly rewrite
  durable cognition.
- Every brain view, learning candidate, and roadmap proposal binds to the exact
  `snapshot_id` used to derive it.
