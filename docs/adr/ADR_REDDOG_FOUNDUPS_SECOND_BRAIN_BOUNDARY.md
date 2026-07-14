# ADR: RedDog and FoundUp Memex Boundary

**Date:** 2026-07-14
**Status:** Proposed and exercised by POC
**Author:** 0102
**Scope:** FoundUp cognition, orchestration, and future multi-RedDog collaboration

## Context

The earlier Second Brain framing mixed a long-term personal digital-twin vision with the immediate FoundUps implementation. The active system already contains Brain, Breadcrumbs, HoloIndex, authoritative work state, roadmaps, and verified outcomes. The required architecture is to compose those systems around one FoundUp DAE rather than create a new general memory platform.

## Decision

1. **FoundUp Memex** is the complete evolving cognition system of one FoundUp.
2. **Brain** remains the durable-consolidation component inside the Memex.
3. **Breadcrumbs** remain episodic continuity inside the Memex.
4. **RedDog** orchestrates FoundUps through exact `foundup_id` and `snapshot_id` bindings.
5. **Foundups Agent** is the first POC entity.
6. Personal 012/0102 Memex work is deferred.
7. Multi-RedDog governance, CABR weighting, stakeholders, and delegates are deferred research, not active runtime authority.

## Existing boundary preserved

`ADR_OPENCLAW_MEMORY_HOLOINDEX_BOUNDARY.md` remains authoritative. HoloIndex is canonical for repository facts and is not replaced by the Memex.

## POC contract

The canonical slice is:

```text
FOUNDUP_MEMEX_CURRENT_STATE_ASSEMBLY_PHASE1
```

The existing `foundup_brain_current_state.py` implementation remains as a compatibility component. `foundup_memex_current_state.py` is the canonical public adapter.

The POC must:

- consume an accepted operational snapshot;
- require separate fresh receipts for repo, work state, HoloIndex, Brain, and Breadcrumbs;
- require a bound roadmap;
- isolate all work and outcomes by `foundup_id`;
- admit only verified, held-out-passed outcomes;
- emit a deterministic read-only Memex view;
- perform no Brain, Breadcrumb, roadmap, HoloIndex, queue, worker, or repository mutation.

## Deferred governance note

The prototype may later use CABR-derived RedDog credibility and delegated stakeholder authority. No formula or threshold is ratified. The future design must address revocation, Sybil resistance, evidence weighting, conflicts of interest, and separation between economic voting power and verified technical competence.

## Consequences

- Implementation stays FoundUp-centric.
- Existing Brain/Breadcrumb code is extended rather than replaced.
- The Memex can later scale from one RedDog to multiple RedDogs without prematurely granting authority.
- Legacy Second Brain names may remain in filenames temporarily for link compatibility, but registry and public contracts use Memex terminology.
