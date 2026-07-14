# ADR: RedDog, 012 Brain, and FoundUp Brain Boundary

**Date:** 2026-07-14  
**Status:** Proposed  
**Author:** 0102  
**Scope:** Digital-twin memory, organizational memory, roadmap cognition, and context assembly

**Not a WSP:** This ADR records an architecture boundary. WSP elevation is deferred until the contracts have been exercised in implementation.

---

## Context

RedDog already has access to multiple memory-like sources: repository truth through HoloIndex, continuity and breadcrumbs, workspace memory, work state, and execution history. These sources are useful but do not define ownership, mutation governance, temporal revision, or the distinction between a personal digital twin and an autonomous FoundUp.

Treating all memory as one index would create authority drift, privacy bleed, stale context, and organizational cross-contamination.

---

## Decision

### Separate sovereign brains

1. **012 Brain** owns the evidence-backed, versioned model of 012's knowledge, preferences, decisions, experiences, terminology, and evolving positions.
2. **Each FoundUp Brain** owns that FoundUp's mission, roadmap, architecture, decisions, experiments, dependencies, and institutional knowledge.
3. **RedDog** is the cognitive operating system that routes across authorized sources, assembles `snapshot_id`-bound working context, dispatches agents, records outcomes, and proposes controlled memory evolution.

RedDog does not own all durable memory.

### Existing boundary preserved

`ADR_OPENCLAW_MEMORY_HOLOINDEX_BOUNDARY.md` remains authoritative for the distinction between canonical repository truth, continuity memory, and automation memory.

HoloIndex remains canonical for repository facts. The Second Brain architecture does not ingest personal continuity into HoloIndex by default and does not make continuity authoritative over repository content.

### Mutation rule

Agents do not directly rewrite durable 012 or FoundUp memory.

Agents submit evidence-backed mutations using controlled operations:

```text
create
reinforce
amend
supersede
contradict
archive
forget
```

Every mutation must identify its target brain, source receipts, confidence, temporal validity, agent identity, approval policy, and `snapshot_id`.

### Snapshot rule

Operational answers, audits, assignments, roadmap proposals, and memory mutations must bind to `snapshot_id`.

The snapshot preserves separate receipts for:

```text
repo_state
work_state
continuity_or_breadcrumbs
012_brain
relevant_foundup_brain
workspace_memory
holoindex
external_research_when_needed
```

These sources must not be collapsed into one freshness or authority flag.

### Roadmap rule

A FoundUp roadmap is a versioned set of hypotheses and governed decisions. Agents may propose evidence-backed roadmap deltas but may not silently modify mission or accepted strategy.

---

## Consequences

### Positive

- Personal and organizational memory remain separately owned and auditable.
- RedDog can become a true digital-twin operating layer without confusing inference with direct statements by 012.
- FoundUps can adapt roadmaps while preserving decision history and rationale.
- HoloIndex remains focused on canonical repository retrieval.
- Prompt injection and stale-memory risks are constrained by mutation gates and source receipts.

### Negative / tradeoffs

- Context assembly requires more explicit source routing and labeling.
- Memory writes become slower because they pass through mutation validation.
- Contradiction, supersession, retention, and forgetting policies must be implemented and tested.
- Separate brain stores require access-control and migration discipline.

---

## Canonical Architecture

- `docs/architecture/REDDOG_FOUNDUPS_SECOND_BRAIN_ARCHITECTURE.md`
- `docs/architecture/architecture_registry.yaml`

---

## Initial Implementation Sequence

```text
REDDOG_SECOND_BRAIN_MEMORY_CONTRACT_PHASE1
REDDOG_SOURCE_PROVENANCE_AND_TEMPORAL_MEMORY_PHASE1
REDDOG_012_DIGITAL_TWIN_EPISTEMIC_GRAPH_PHASE1
FOUNDUP_BRAIN_RUNTIME_AND_MEMORY_ISOLATION_PHASE1
FOUNDUP_ADAPTIVE_ROADMAP_ENGINE_PHASE1
REDDOG_CROSS_BRAIN_CONTEXT_ROUTER_PHASE1
REDDOG_MEMORY_CONSOLIDATION_CONTRADICTION_AND_FORGETTING_PHASE1
REDDOG_MEMORY_EVALUATION_AND_REGRESSION_HARNESS_PHASE1
FOUNDUPS_COLLECTIVE_MEMORY_EXCHANGE_PHASE1
```
