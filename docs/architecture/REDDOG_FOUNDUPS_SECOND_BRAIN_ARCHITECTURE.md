# FoundUps Memex Vision

**Date:** 2026-07-14
**Status:** Vision with active POC
**Owner:** 0102 / RedDog
**POC entity:** `foundups-agent`
**Controlling protocol:** WSP_60 Module Memory Architecture
**WSP addendum:** `WSP_framework/docs/annexes/WSP_60_FOUNDUP_MEMEX_ADDENDUM.md`

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

012 Principal Memex
= persistent principal cognition that informs 0102 across FoundUps

0102 Digital Twin
= active reasoning/orchestration agent hosted by RedDog
```

The FoundUp Memex remains the implementation center of FoundUp cognition. The
Principal Memex is a separate Digital Twin substrate, not a global FoundUp
store, conversation transcript, AgentDB queue, or authority source.

## Principal Memex and RedDog

```text
012 -> Principal Memex -> 0102 Digital Twin -> RedDog interface/runtime
```

RedDog hosts 0102. The Principal Memex helps 0102 interpret stable 012 goals,
preferences, terminology, decision history, and cross-FoundUp strategy.
Current repository evidence remains authoritative for code truth, and signed
authorization remains authoritative for work.

The structural read-only projection is implemented in
`modules/ai_intelligence/digital_twin/src/principal_memex_projection.py`. A
caller-supplied projection remains non-admissible. The resident backend may
derive and admit one projection from the exact current signed principal
conversation only after consuming its conversation capability and a separate
principal-signed disclosure bound to exact decision IDs, model runtime, nonce,
TTL, revocation, and durable replay state. This admitted context cannot persist,
project into a FoundUp, mutate HoloIndex, or grant work authority. Governed
durable source issuance, conversation learning, and cross-Memex transfer remain
explicit later lifecycles.

## WSP alignment

This architecture is an application of WSP_60, not a new memory protocol. The FoundUp Memex composes WSP_60 module-owned memory, semantic/episodic/procedural/working memory, Breadcrumbs, HoloIndex retrieval, and FoundUp DAE isolation into one snapshot-bound cognition view.

Related protocol responsibilities:

- WSP_60 controls memory ownership, isolation, persistence, and retrieval boundaries.
- WSP_80 controls FoundUp DAE orchestration.
- WSP_84 requires verification of existing code and memory surfaces before replacement.
- WSP_82 controls citation and cross-reference integrity.
- WSP_83 attaches this architecture to the canonical documentation tree.
- WSP_22 records implementation evolution through ModLog and TestModLog.
- WSP_87 requires HoloIndex-first discovery.
- WSP_97 preserves truth-state labels and prevents inferred authority from becoming implemented fact.

The framework addendum is authoritative. Its `WSP_knowledge` copy is a byte-for-byte backup/reference mirror.

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

Authenticated admission of current public accepted principal decisions is now
implemented for the resident backend architect model. Governed durable
Principal Memex source issuance and retention, automatic resident supply,
explicit cross-Memex projection, and collective ecosystem memory remain
deferred until their independent trust contracts are proven.
