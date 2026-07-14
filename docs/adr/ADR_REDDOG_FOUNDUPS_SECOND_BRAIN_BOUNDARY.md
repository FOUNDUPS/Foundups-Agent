# ADR: FoundUp Brain and RedDog Operating Boundary

**Date:** 2026-07-14  
**Status:** Proposed  
**Author:** 0102  
**Scope:** FoundUp cognition, existing Brain and Breadcrumb composition, roadmap evolution, and RedDog context assembly

**Not a WSP:** This ADR records an architecture boundary. WSP elevation is deferred until the contracts have been exercised in implementation.

---

## Context

Foundups Agent already has multiple cognition and continuity systems: Brain artifacts, Breadcrumbs, HoloIndex, authoritative work state, operational context snapshots, verified outcomes, held-out regression evidence, research receipts, and roadmap documents.

The architectural risk is creating a second parallel memory platform centered on a personal digital twin while the immediate product goal is to code out FoundUps as decentralized autonomous entities.

The first implementation must therefore make one FoundUp able to assemble and evolve its own cognition by composing the systems already present in the repository.

---

## Decision

### FoundUp-first implementation

The primary implementation target is the **Foundups Agent Brain POC**.

```text
FoundUp Brain
= existing Brain
+ Breadcrumbs
+ authoritative work state
+ HoloIndex-grounded repository truth
+ verified outcomes
+ roadmap state
+ governed external signals
```

Personal 012 / 0102 digital-twin memory is deferred until the FoundUp Brain contracts have been proven.

### Existing roles remain intact

1. **Brain** is durable consolidated FoundUp understanding: mission, thesis, decisions, architecture, validated lessons, and strategic state.
2. **Breadcrumbs** are episodic chronological continuity: what happened, changed, failed, succeeded, or remains unresolved.
3. **HoloIndex** remains canonical retrieval for repository facts.
4. **Authoritative work state** remains the current execution truth.
5. **Verified outcomes and held-out regressions** are the admission evidence for durable learning.
6. **RedDog** operates through a snapshot-bound view of the FoundUp Brain; it does not receive a separate new durable brain in the POC.

### Existing memory boundary preserved

`ADR_OPENCLAW_MEMORY_HOLOINDEX_BOUNDARY.md` remains authoritative for canonical repository truth, continuity memory, and automation memory.

Brain, Breadcrumbs, work state, roadmap, HoloIndex, and verified outcomes remain separately receipted. No source may be collapsed into one authority or freshness flag.

### First runtime slice

The next implementation slice is:

```text
FOUNDUP_BRAIN_CURRENT_STATE_ASSEMBLY_PHASE1
```

It composes existing accepted receipts into a deterministic, read-only FoundUp brain view identified by:

```text
foundup_id
foundup_brain_view_id
snapshot_id
```

It introduces no new general-purpose memory database and performs no Brain, Breadcrumb, roadmap, HoloIndex, queue, or repository mutation.

### Learning rule

Agents do not directly rewrite Brain state.

Signals from Breadcrumbs, verified outcomes, or independently verified research become **learning candidates**. A later governance gate may accept, reject, or defer a consolidation proposal.

### Roadmap rule

The roadmap is governed strategic state within the FoundUp Brain. Agents may submit evidence-backed roadmap deltas but may not silently change mission or accepted strategy.

### Multi-FoundUp rule

After the Foundups Agent POC is proven, each FoundUp receives an isolated brain scope under `foundup_id`, including its own Brain namespace, Breadcrumb stream, roadmap, work-state view, learning candidates, and access policy.

---

## Consequences

### Positive

- Extends the Brain, Breadcrumb, snapshot, and verification systems already implemented.
- Keeps development aligned with coding out FoundUps as DAEs.
- Creates a narrow POC-to-MVP path before generalizing memory infrastructure.
- Preserves HoloIndex and authoritative work-state boundaries.
- Makes roadmap adaptation part of entity cognition rather than detached planning documentation.
- Defers personal digital-twin complexity until the organizational contracts are proven.

### Negative / tradeoffs

- The initial POC is deliberately limited to one FoundUp.
- Brain consolidation and roadmap mutation remain blocked until later governed slices.
- Existing Brain and Breadcrumb formats may require adapters after their actual contracts are fully inspected.
- Multi-entity storage and access-control design is postponed until the single-entity view is verified.

---

## Canonical Architecture

- `docs/architecture/REDDOG_FOUNDUPS_SECOND_BRAIN_ARCHITECTURE.md`
- `docs/architecture/architecture_registry.yaml`

---

## Implementation Sequence

```text
1. FOUNDUP_BRAIN_CURRENT_STATE_ASSEMBLY_PHASE1
2. FOUNDUP_BRAIN_LEARNING_CANDIDATE_GATE_PHASE1
3. FOUNDUP_BRAIN_GOVERNED_CONSOLIDATION_PHASE1
4. FOUNDUP_ADAPTIVE_ROADMAP_DELTA_PROPOSAL_PHASE1
5. FOUNDUP_ADAPTIVE_ROADMAP_GOVERNANCE_GATE_PHASE1
6. FOUNDUP_BRAIN_MULTI_ENTITY_ISOLATION_PHASE1
7. FOUNDUPS_COLLECTIVE_MEMORY_EXCHANGE_PHASE1
8. REDDOG_012_DIGITAL_TWIN_APPLICATION_PHASE1 (deferred)
```
