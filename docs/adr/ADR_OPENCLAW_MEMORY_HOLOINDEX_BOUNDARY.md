# ADR: OpenClaw Memory, HoloIndex, and AI Overseer — Retrieval Boundary

**Date:** 2026-04-11  
**Status:** Accepted  
**Author:** 0102 (architect lock-in)  
**Scope:** Context assembly for `ai_overseer` and related autonomous agents  

**Not a WSP:** This document does not create or modify a Windsurf Protocol. WSP elevation is deferred until the pattern has proven stable in operation.

---

## Context

Three memory-like systems are in play:

1. **HoloIndex** — semantic retrieval over the repository (code, WSP sources, repo docs, contracts).  
2. **OpenClaw memory** — file-based continuity (e.g. `MEMORY.md`, daily notes under `memory/`, tools such as `memory_search` / `memory_get` in the OpenClaw/Molt workspace).  
3. **AI Overseer** — automation-oriented persistence (pattern memory, execution history, DAEmon-style state under module memory per WSP 60).

Merging these into a single index or treating session notes as repo truth causes **privacy bleed**, **stale notes masquerading as canon**, and **ranking / authority drift**. Quiet injection of unlabeled context lets models treat operator preferences as if they were codebase facts.

---

## Decision

### Layer roles

| Layer | Role |
|-------|------|
| **HoloIndex** | **Canonical** retrieval for code, WSPs, repo docs, and contracts. |
| **OpenClaw memory** | **Non-canonical continuity** — operator/session notes, recent decisions, preferences, daily working context. |
| **AI Overseer memory** | **Automation / pattern / execution-state** — heuristics, outcomes, DAEmon-style state — not a substitute for repo or WSP text. |

### Conflict rule

If continuity or automation context **conflicts** with **HoloIndex / repository** content, **repo truth wins**. OpenClaw memory is **context**, not authority.

### Source precedence (query / assembly order)

When `ai_overseer` (or a delegated assembler) builds context:

1. **HoloIndex** — canonical repo/WSP truth first.  
2. **OpenClaw memory** — continuity second.  
3. **AI Overseer pattern / execution memory** — automation heuristics last.

### Provenance in **prompt assembly** (required)

Context injected into prompts must be **visibly labeled** so operators and models do not confuse layers:

- **`Canonical repo truth`** — from HoloIndex / repo-grounded snippets.  
- **`Continuity memory`** — from OpenClaw memory files or `memory_search` / `memory_get` (and equivalents).  
- **`Automation pattern memory`** — from overseer pattern files, execution reports, DAEmon-style state.

Implementations may also attach machine-readable tags (e.g. `source=holoindex`, `source=openclaw_memory`, `source=ai_overseer_pattern`) **in addition to** these human-visible headings, not instead of them.

### Phase-1 integration scope

- Prefer **read-through** (read configured OpenClaw workspace files such as `MEMORY.md` and today/yesterday daily notes) and/or a **thin tool/CLI wrapper** around OpenClaw memory APIs.  
- **Do not** by default **ingest raw OpenClaw memory into HoloIndex** (no shared reindexing as the starting position).  
- **Do not** lead with **QMD / dual-index fusion** or other multi-index cleverness until trust, freshness, and privacy rules are operational.

### Privacy and logging

Apply an explicit **redaction / privacy rule** before continuity content is **logged**, **persisted outside the continuity layer**, or **indexed** anywhere. Default stance: OpenClaw memory may contain operator-private material; treat it as sensitive unless classified otherwise.

---

## Consequences

### Positive

- Clear **authority ordering** reduces silent drift (“memory said X” vs “repo says Y”).  
- **Labeled** prompt sections make audits and debugging tractable.  
- HoloIndex remains the **single canonical** semantic index for **repository** knowledge without mixing session diaries by default.

### Negative / tradeoffs

- Overseer prompt assembly grows slightly (section headers).  
- Operators must **configure** one canonical OpenClaw workspace path for internal read-through.  
- Two retrieval paths (HoloIndex + OpenClaw tools) remain until a future phase explicitly justifies unification under stricter governance.

---

## References

- OpenClaw memory overview: [Memory Overview](https://docs.molt.bot/concepts/memory)  
- AI Overseer Holo facade: `modules/ai_intelligence/ai_overseer/src/holo_adapter.py`  

---

*0102 note: Revisit for WSP packaging only after this boundary has been exercised in production-style runs.*
