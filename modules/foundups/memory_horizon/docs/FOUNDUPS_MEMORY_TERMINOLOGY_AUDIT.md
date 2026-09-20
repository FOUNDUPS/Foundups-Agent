# Memory Horizon - FoundUps Memory Terminology Audit

**Date:** 2026-09-20  
**Method:** WSP 97 retrieve-before-stating audit against current Foundups-Agent repository evidence.  
**Status:** Canonical terminology reference for Memory Horizon design.

## Rule

Memory Horizon must not treat FoundUps memory terms as generic English labels. When a FoundUps term is reused, the canonical repository meaning and truth boundary must be preserved. Analogies must be labeled as analogies.

## Canonical terms

### FoundUp Memex

**Canonical meaning:** the complete evolving cognition system of one FoundUp DAE.

It composes existing WSP 60 memory surfaces for one `foundup_id`. It is not a parallel general-purpose memory database.

Canonical sources:
- `WSP_framework/docs/annexes/WSP_60_FOUNDUP_MEMEX_ADDENDUM.md`
- `docs/adr/ADR_REDDOG_FOUNDUPS_SECOND_BRAIN_BOUNDARY.md`
- `docs/architecture/REDDOG_FOUNDUPS_SECOND_BRAIN_ARCHITECTURE.md`

### Brain

**Canonical meaning:** the durable-consolidation component inside a FoundUp Memex.

Brain is not synonymous with Memex. Current public Memex terminology is layered over the proven `foundup_brain_current_state.py` compatibility implementation, but that does not collapse the concepts.

Canonical sources:
- `modules/communication/moltbot_bridge/src/foundup_brain_current_state.py`
- `modules/communication/moltbot_bridge/src/foundup_memex_current_state.py`

### Breadcrumbs

**Canonical meaning:** episodic continuity / evidence-backed chronological activity-discovery trail.

A meaningful Breadcrumb can carry or resolve event time, actor, FoundUp/project scope, factual action, observed result, provenance, confidence/truth class, related identifiers, disclosure class, and correction/supersession linkage.

Breadcrumbs preserve event history. They are not Brain consolidation and are not the Moshpit view.

Canonical sources:
- `WSP_framework/docs/annexes/WSP_60_FOUNDUP_MEMEX_ADDENDUM.md`
- `extensions/reddog/docs/MOSHPIT_ACTIVITY_MEMORY_ARCHITECTURE.md`
- `modules/infrastructure/cross_platform_memory/src/breadcrumb_trail.py`

### 012 Principal Memex

**Canonical meaning:** persistent principal-scoped cognition substrate for the 012/0102 relationship.

It contains principal-scoped goals, stable preferences, architectural principles, accepted terminology, decision history, communication preferences, and long-term unresolved questions.

It is explicitly **not**:
- a FoundUp Memex;
- a conversation log;
- AgentDB work state;
- repository truth;
- an authority source.

Principal-to-FoundUp transfer requires an explicit provenance-preserving projection; automatic copying is forbidden by the architecture.

Canonical sources:
- `WSP_framework/docs/annexes/WSP_60_FOUNDUP_MEMEX_ADDENDUM.md`
- `docs/adr/ADR_REDDOG_FOUNDUPS_SECOND_BRAIN_BOUNDARY.md`

### RedDog

Within the canonical memory architecture, RedDog is the low-latency interaction/exchange/attention surface through which 012 interacts with the principal-scoped 0102 Digital Twin. RedDog is not itself the Digital Twin's memory.

The deeper 0102 layer retrieves Principal Memex, scoped FoundUp Memex, Brain/Breadcrumbs, HoloIndex and WSP truth, then returns bounded context deltas to RedDog.

Canonical source:
- `docs/architecture/REDDOG_DUAL_LOOP_COGNITION_ARCHITECTURE.md`

### HoloIndex

**Canonical memory role:** repository/WSP retrieval and pattern-memory surface under WSP 60, with freshness and evidence boundaries.

For Memex querying, historical Memex evidence may support continuity and prior-decision recall but does not prove current code or authoritative work state.

Therefore Memory Horizon must not casually repurpose the term `HoloIndex` as the human episodic-memory retriever. A future human-memory retriever may use analogous evidence-ranking patterns, but that is a separate scoped component unless an explicit interface proves reuse.

Canonical sources:
- `WSP_framework/src/WSP_60_Module_Memory_Architecture.md`
- `holo_index/memex_query_routing.py`
- `holo_index/memex_evidence_bundle.py`

### Semantic / Episodic / Procedural / Working Memory

WSP 60 defines:
- **Semantic Memory:** stable knowledge.
- **Episodic Memory:** what was seen and chosen — queries, results, session context.
- **Procedural Memory:** how to act — protocols, skills and workflows.
- **Working Memory:** the current Holo result pack used for the next decision.

These are canonical 0102/HoloDAE layers. Human cognitive-science uses of the same terms must be distinguished when necessary.

Canonical source:
- `WSP_framework/src/WSP_60_Module_Memory_Architecture.md`

### Moshpit

**Canonical meaning:** a governed reverse-chronological projection/view over selected Breadcrumbs plus Brain/Memex current-state interpretation.

It is explicitly **not a memory subsystem** and should not get a duplicate database.

Canonical source:
- `extensions/reddog/docs/MOSHPIT_ACTIVITY_MEMORY_ARCHITECTURE.md`

### Contact Memory

**Canonical meaning:** a principal-scoped relationship-memory architecture for contacts, organizations, interaction events, commitments, provenance and relationship edges.

Current truth label: `ARCHITECTURE_VISION / SPECIFIED_NOT_IMPLEMENTED`.

It is entity/event based, with RAG as one retrieval lane rather than the whole memory model. Project-relevant interactions can become/refer to Breadcrumbs; Brain/Memex and Moshpit remain separate projections/roles.

Canonical source:
- `extensions/reddog/docs/CONTACT_MEMORY_ARCHITECTURE.md`

### Memory Nudge Engine

**Canonical current implementation:** automatic capture of high-value repository/autonomy events into deduplicated workspace-memory notes, optionally recording AgentDB Breadcrumbs.

Current trigger classes include supervisor escalations, self-research changes, worktree pressure and grant-watchlist changes.

It is **not** currently a human-facing assistive recall-cue engine. Memory Horizon must not use "Memory Nudge Engine" as if it already implements spoken cueing for a wearer.

Canonical source:
- `modules/communication/moltbot_bridge/src/memory_nudge_engine.py`

### AgentDB / workspace memory

Existing RedDog query paths can combine workspace memory with AgentDB Breadcrumbs. AgentDB is a shared agent memory/state and coordination surface; it is not synonymous with Principal Memex, FoundUp Memex or Brain.

Canonical sources:
- `modules/infrastructure/database/src/agent_db.py`
- `modules/communication/moltbot_bridge/src/openclaw_memory_queries.py`

## Unresolved term: "Memic"

WSP 97 retrieval found **no canonical exact term `Memic`** in:
- current default-branch repository code/docs;
- repository issue search;
- branch-name search;
- retrieved historical 012/0102 context.

`Memex` is canonical and heavily defined, but this audit does **not** silently normalize `Memic` to `Memex`.

Until 012 explicitly establishes that `Memic` is an alias, historical term, separate subsystem, or speech-to-text rendering of `Memex`, use truth label:

`UNRESOLVED_TERM_MEMIC`

and retrieve again before making a semantic claim.

## Memory Horizon reuse decision

For our Memory Horizon work:

- Reuse the **event/provenance discipline** of Breadcrumbs.
- Reuse the **separation concept** of episodic trail vs durable consolidation vs presentation.
- Do not claim the human wearable is literally writing existing FoundUp Breadcrumbs until an interface and principal-scope contract exist.
- Do not call the assistive cue path the existing Memory Nudge Engine.
- Do not use HoloIndex as a synonym for the wearable's personal-event retriever.
- Keep controlled cognitive measurement data separate from FoundUp operational memory.
- Any bridge into Principal Memex must be explicit, provenance-preserving, principal-scoped and separately authorized.

## WSP 97 operating rule for future terminology

For every named term supplied by 012:

```text
term from 012
-> exact repo search
-> retrieve canonical docs/code/interfaces
-> micro pass: exact term contract
-> macro pass: adjacent memory surfaces
-> truth label: OBSERVED / SPECIFIED / PARTIAL / UNRESOLVED
-> only then map it into Memory Horizon or another FoundUp
```

No guessed expansion or silent synonymization.
