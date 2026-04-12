# ADR: Sentinel, HoloIndex, OpenClaw — System Architecture Boundary

**Date:** 2026-04-12  
**Status:** Proposed  
**Author:** 0102 (architect lock-in)  
**Scope:** Runtime, memory, control, and interface layer separation for autonomous systems  

**Not a WSP:** This document does not create or modify a Windsurf Protocol. WSP elevation is deferred until the pattern has proven stable in operation.

**Extends:** [ADR_OPENCLAW_MEMORY_HOLOINDEX_BOUNDARY.md](ADR_OPENCLAW_MEMORY_HOLOINDEX_BOUNDARY.md) — the original memory-layer boundary decision.

---

## 1. Status

**Proposed** — awaiting validation through implementation slices.

---

## 2. Context

Multiple systems with overlapping responsibilities exist in the codebase:

1. **Sentinel** — runtime execution watchdogs, tool surfaces, execution guards (e.g., `holo_memory_sentinel.py`, `wsp_framework_sentinel.py`, `fam_security_sentinel.py`)
2. **HoloIndex** — semantic retrieval over repo/WSP/contract knowledge
3. **OpenClaw memory** — file-based session continuity (`MEMORY.md`, daily notes, `memory_search`/`memory_get` tools)
4. **Overseers / OpenClaw control** — policy enforcement, anomaly detection, routing decisions (`ai_overseer`, OpenClaw as supervisor)
5. **HoloDecks** — interface and visualization layer (public web surfaces)
6. **Capability model** — Skills, SKILLZ, Wardrobe, Rolodex (execution units, loadouts, discovery)

External research (e.g., MiniMax CLI patterns) offers valuable design input but risks importing misaligned abstractions if treated as architecture to adopt rather than patterns to study.

Without explicit boundaries:
- Runtime execution and memory become conflated
- Session continuity masquerades as canonical truth
- Raw logs flood the memory index
- Interface state drives business logic
- External dependencies creep into core architecture

---

## 3. Decision

### System Layering

| Layer | Role | Owns |
|-------|------|------|
| **Sentinel** | Runtime execution / tool surface | Execution guards, watchdogs, tool invocation, runtime fidelity |
| **HoloIndex** | Canonical durable memory / retrieval | Repo truth, WSP sources, contracts, semantic search |
| **OpenClaw memory** | Continuity / context memory | Session notes, daily context, operator preferences |
| **Overseers / OpenClaw** | Control plane | Policy, anomaly detection, routing decisions, escalation |
| **HoloDecks** | Interface / visualization | Web surfaces, user interaction, display state |

### Key Boundaries

1. **Sentinel owns runtime execution** — tool invocation, execution guards, session watchdogs, fidelity checks
2. **HoloIndex owns canonical durable memory** — repo/WSP truth is the single source of authority for system knowledge
3. **OpenClaw memory is continuity, not canon** — session notes aid context but do not override repo truth
4. **Overseers own control, not execution** — they route, gate, and escalate; Sentinel executes
5. **HoloDecks is interface, not source of truth** — visualization reads from canonical layers, does not define them

---

## 4. Source Precedence

When assembling context or resolving conflicts, precedence is:

| Priority | Source | Authority |
|----------|--------|-----------|
| **1** | HoloIndex / repo artifacts | **Canonical** — WSP text, code, contracts win |
| **2** | OpenClaw memory | **Non-canonical continuity** — context, not authority |
| **3** | AI Overseer pattern memory | **Execution-state** — heuristics, outcomes, not spec truth |
| **4** | HoloDecks display state | **Interface** — rendering context only |

If continuity or automation memory **conflicts** with repo/WSP truth, **repo truth wins**.

---

## 5. Memory Ingestion Rule

Not all runtime output is memory-grade. Distinguish:

| Artifact Type | Treatment |
|---------------|-----------|
| **Raw logs** | Not indexed by default; retained for debugging, rotated aggressively |
| **Normalized execution events** | Selectively indexed if schema-validated (see `execution_event_schema`) |
| **Summaries / failures / validated outcomes** | Memory-grade; indexed into HoloIndex or pattern memory |

### Required Position

- **Do not** index all raw runtime output equally
- **Do not** treat session continuity as canonical system memory
- Memory-grade artifacts are **curated/normalized outputs**, not log streams
- Raw logs may be promoted to memory only after explicit normalization and validation

---

## 6. Capability Model

Use cautious FoundUps-native framing. Do not over-freeze uncertain ontology.

| Concept | Definition | Status |
|---------|------------|--------|
| **Skill** | Capability unit — a discrete executable action | Confirmed |
| **SKILLZ** | Internal/native capability layer — repo-local skill manifests (`SKILLz.md`) | Confirmed |
| **Wardrobe** | Equip/loadout layer — active capability configuration for a session or agent | Confirmed |
| **Rolodex** | Discovery/lookup/routing layer — the registry of available capabilities | **Provisional** — structure under active design |

The `command_rolodex.json` exists as a CLI capability catalog (722 entrypoints, 95 WRE-connected). The broader Rolodex concept for dynamic capability discovery remains provisional.

---

## 7. Non-Goals

This architecture explicitly rejects:

1. **Adopting MiniMax CLI as a dependency** — external tools are pattern donors only, not runtime dependencies
2. **Provider lock-in** — no external AI/memory provider becomes required infrastructure
3. **Collapsing layers** — runtime + memory + registry + control plane remain distinct
4. **Treating session continuity as canonical** — OpenClaw memory is context, not authority
5. **Indexing raw logs as memory** — logs are debugging artifacts, not knowledge
6. **Merging OpenClaw memory into HoloIndex** — the layers serve different trust/freshness/privacy models

---

## 8. Consequences

### Positive

- Clear separation enables independent evolution of each layer
- HoloIndex remains the single canonical semantic index for repository knowledge
- Sentinel can be optimized for execution without memory concerns
- External pattern research can inform design without importing dependencies
- Memory ingestion is explicit, not implicit log accumulation

### Negative / Tradeoffs

- Multiple retrieval paths must be maintained (HoloIndex + OpenClaw + pattern memory)
- Operators must understand which layer to query for which purpose
- Rolodex design remains provisional until exercised in production
- Some duplication between layers is accepted to maintain separation

---

## 9. Recommended Next Slices

| Slice | Purpose |
|-------|---------|
| `sentinel_unified_tool_surface_contract` | Define the canonical Sentinel execution API |
| `execution_event_schema_for_memory_and_overseer` | Schema for normalized events eligible for memory ingestion |
| `capability_pack_manifest_schema` | Standard manifest format for Wardrobe loadouts |
| `holoindex_execution_memory_ingestion_contract` | Rules for when/how execution outcomes enter HoloIndex |
| `wardrobe_loadout_and_rolodex_registry_model` | Finalize Rolodex design and Wardrobe configuration model |

---

## 10. References

- [ADR_OPENCLAW_MEMORY_HOLOINDEX_BOUNDARY.md](ADR_OPENCLAW_MEMORY_HOLOINDEX_BOUNDARY.md) — original memory-layer boundary
- `modules/ai_intelligence/ai_overseer/src/holo_adapter.py` — HoloIndex facade
- `modules/ai_intelligence/ai_overseer/src/holo_memory_sentinel.py` — Sentinel example
- `holo_index/docs/command_rolodex.json` — CLI capability catalog
- WSP 91 — DAEMON Observability Protocol (logging/metrics standards)
- WSP 60 — Module Memory Architecture

---

*0102 note: This ADR consolidates the system architecture boundary. Revisit for WSP packaging only after implementation slices validate the layer separation.*
