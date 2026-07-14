# FoundUps Memex Vision

**Date:** 2026-07-14  
**Status:** Vision with active POC  
**Owner:** 0102 / RedDog  
**POC entity:** `foundups-agent`

## Canonical terminology

```text
FoundUp Memex
= the complete evolving cognition system of one FoundUp DAE

Brain
= the Memex component that holds durable consolidated understanding

Breadcrumbs
= episodic continuity and recent operational history

RedDog
= the orchestrator that launches, builds, runs, audits, and improves FoundUps
```

"Second Brain" and personal digital-twin language describe possible later applications. They are not the implementation center of the current lane.

## Vision

Each FoundUp is a decentralized autonomous entity, not merely a repository or application. Its Memex preserves and connects:

- identity, purpose, outcome, solution, and pain;
- Brain artifacts and Breadcrumb continuity;
- canonical repository truth through HoloIndex;
- authoritative work state and agent assignments;
- roadmap state, dependencies, and blockers;
- verified outcomes and held-out regression evidence;
- governed research and environmental signals;
- decision history, contradictions, and supersession.

RedDog operates through the Memex of the FoundUp currently in scope. RedDog does not silently collapse all FoundUps into one memory store.

## POC

The POC is 012 operating one RedDog that launches, builds, runs, and improves the internal FoundUps in Foundups-Agent.

Current slice:

```text
FOUNDUP_MEMEX_CURRENT_STATE_ASSEMBLY_PHASE1
```

Compatibility implementation:

```text
modules/communication/moltbot_bridge/src/foundup_brain_current_state.py
```

Canonical public adapter:

```text
modules/communication/moltbot_bridge/src/foundup_memex_current_state.py
```

The POC proves that one RedDog can assemble one deterministic, read-only, snapshot-bound FoundUp cognition view from existing systems without creating a parallel database.

## Prototype

The prototype begins only after the single-RedDog POC is proven:

```text
multiple RedDogs
-> independently scoped FoundUp work
-> verified contributions
-> governed collaboration
-> weighted authority
```

## Deferred governance research

Future multi-RedDog governance must revisit:

- CABR-weighted RedDog credibility and authority;
- stakeholder and delegate roles;
- revocable vote delegation;
- a possible delegate threshold based on delegated voting power;
- differentiated proposal, mutation, and roadmap authority;
- Sybil resistance and new-account limits.

No authority formula, threshold, or CABR implementation is approved by this document. See:

```text
docs/architecture/FOUNDUPS_MEMEX_DEFERRED_GOVERNANCE_NOTES.md
```

## Existing boundaries preserved

- HoloIndex remains canonical for repository facts.
- Brain and Breadcrumbs remain separate, separately receipted sources.
- Current repo/work state overrides stale historical interpretation.
- Raw evidence is preserved; summaries do not replace sources.
- Every Memex view binds to `foundup_id`, `snapshot_id`, and source receipts.
- Agents propose learning and roadmap deltas; they do not directly rewrite durable cognition.
- Runtime RedDog does not re-index HoloIndex.

## POC-to-MVP sequence

```text
1. FOUNDUP_MEMEX_CURRENT_STATE_ASSEMBLY_PHASE1
2. FOUNDUP_MEMEX_LEARNING_CANDIDATE_GATE_PHASE1
3. FOUNDUP_MEMEX_GOVERNED_BRAIN_CONSOLIDATION_PHASE1
4. FOUNDUP_ADAPTIVE_ROADMAP_DELTA_PROPOSAL_PHASE1
5. FOUNDUP_ADAPTIVE_ROADMAP_GOVERNANCE_GATE_PHASE1
6. FOUNDUP_MEMEX_MULTI_ENTITY_ISOLATION_PHASE1
7. FOUNDUP_MEMEX_MULTI_REDDOG_COLLABORATION_PROTOTYPE_PHASE1
```

Personal 012/0102 Memex work and collective ecosystem memory remain deferred until the FoundUp-centric contracts are proven.
