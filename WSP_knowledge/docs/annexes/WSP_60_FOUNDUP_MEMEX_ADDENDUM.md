# WSP 60 Addendum: FoundUp Memex Composition

**Parent protocol:** `WSP_framework/src/WSP_60_Module_Memory_Architecture.md`
**Status:** Active POC addendum
**Date:** 2026-07-14
**Authority:** WSP_60 remains the controlling protocol. This addendum does not create a new WSP.

## Purpose

Define the FoundUp-level composition layer above module-owned memory without changing WSP_60 ownership, isolation, HoloIndex, or persistence boundaries.

The canonical term is **FoundUp Memex**.

```text
FoundUp Memex
= complete evolving cognition system of one FoundUp DAE

Brain
= durable-consolidation component inside the Memex

Breadcrumbs
= episodic continuity component

RedDog
= orchestrator that launches, builds, runs, audits, and improves FoundUps

012 Principal Memex
= persistent cognition substrate for the 012/0102 relationship

0102 Digital Twin
= active reasoning and orchestration agent hosted by RedDog
```

The Principal Memex is not a FoundUp Memex, conversation log, AgentDB work
state, or authority source. RedDog hosts the Digital Twin; RedDog is not the
Digital Twin's memory.

## WSP_60 relationship

WSP_60 already defines:

- module-owned persistent memory;
- semantic, episodic, procedural, and working memory;
- Breadcrumb coordination;
- HoloIndex retrieval and pattern memory;
- FoundUp DAE memory isolation;
- verified operational outcome writeback.

The FoundUp Memex composes those existing surfaces for one `foundup_id`. It does not replace them and does not introduce a parallel general-purpose memory database.

## Principal vs FoundUp cognition

The 012 Principal Memex contains principal-scoped goals, stable preferences,
architectural principles, accepted terminology, decision history,
communication preferences, and long-term unresolved questions. It may inform
0102 interpretation across FoundUps, but it cannot establish repository truth,
FoundUp scope, or work authority.

The first implemented Principal Memex layer is:

```text
REDDOG_012_PRINCIPAL_MEMEX_READONLY_PROJECTION_PHASE1
```

It is a structural, in-memory projection owned by
`modules/ai_intelligence/digital_twin`. It is not runtime-admissible and
performs no persistence, model-context admission, FoundUp projection,
HoloIndex write, or work authorization. Authenticated source admission is a
separate required slice.

Information crosses between Principal and FoundUp Memex only through a future
explicit, provenance-preserving projection. Neither side silently copies or
promotes the other's cognition.

## Required Memex sources

A current-state Memex view must preserve separate receipts for:

1. canonical repository state;
2. authoritative work state;
3. HoloIndex freshness and retrieval state;
4. existing Brain metadata;
5. scoped Breadcrumb continuity;
6. bound roadmap state;
7. independently verified outcomes;
8. governed external research receipts when required.

Every view and derived proposal must bind to the exact `snapshot_id` used to produce it.

## Authority and truth boundaries

- HoloIndex remains canonical for repository retrieval facts, subject to freshness receipts.
- Current repository and authoritative work state override stale historical interpretation.
- Brain and Breadcrumbs remain distinct sources with distinct receipts.
- Raw source evidence is not replaced by summaries.
- RedDog may assemble and reason over a Memex view but may not silently rewrite durable memory.
- Agents submit evidence-backed learning candidates; a later governed consolidation gate owns durable Brain mutation.
- Roadmaps change only through governed delta proposals and acceptance gates.
- Cross-FoundUp records must fail closed when `foundup_id` does not match.

## POC boundary

The first POC is `foundups-agent` with one RedDog and one FoundUp Memex.

Implemented slice:

```text
FOUNDUP_MEMEX_CURRENT_STATE_ASSEMBLY_PHASE1
```

The POC is read-only. It performs no Brain write, Breadcrumb write, roadmap mutation, HoloIndex mutation, queue mutation, worker spawn, repository mutation, CABR authority, stakeholder authority, delegate authority, or voting authority.

## Deferred prototype concerns

The following remain specified but not implemented:

- multi-RedDog collaboration;
- multi-FoundUp durable isolation;
- CABR-weighted contribution credibility;
- stakeholder and revocable delegate authority;
- governance thresholds and Sybil resistance;
- authenticated resident Principal Memex admission;
- governed Principal Memex source issuance and retention;
- explicit Principal-to-FoundUp and FoundUp-to-Principal projection.

These require separate WSP_97 analysis and tested contracts before runtime authority is granted.

## Related WSPs

- **WSP_60:** controlling memory ownership and architecture protocol.
- **WSP_80:** DAE orchestration and FoundUp-level coordination.
- **WSP_84:** verify existing code and memory surfaces before adding or replacing implementations.
- **WSP_82:** maintain citations and cross-references between WSP, architecture, ADR, roadmap, ModLog, and tests.
- **WSP_83:** attach Memex documentation to the canonical documentation tree.
- **WSP_22:** record implementation evolution in ModLog and TestModLog.
- **WSP_87:** retrieve code and documentation through HoloIndex before direct reconstruction.
- **WSP_97:** preserve OBSERVED, INFERRED, SPECIFIED_NOT_IMPLEMENTED, and UNKNOWN truth boundaries.

## Canonical implementation references

- `docs/architecture/REDDOG_FOUNDUPS_SECOND_BRAIN_ARCHITECTURE.md`
- `docs/adr/ADR_REDDOG_FOUNDUPS_SECOND_BRAIN_BOUNDARY.md`
- `docs/architecture/architecture_registry.yaml`
- `modules/communication/moltbot_bridge/src/foundup_memex_current_state.py`
- `modules/ai_intelligence/digital_twin/src/principal_memex_projection.py`
- `modules/communication/moltbot_bridge/ROADMAP.md`

## Framework and knowledge synchronization

`WSP_framework` is authoritative for edits. After validation, this addendum must be mirrored byte-for-byte to:

```text
WSP_knowledge/docs/annexes/WSP_60_FOUNDUP_MEMEX_ADDENDUM.md
```

The knowledge copy is a backup/reference mirror and must not diverge from the framework copy.
