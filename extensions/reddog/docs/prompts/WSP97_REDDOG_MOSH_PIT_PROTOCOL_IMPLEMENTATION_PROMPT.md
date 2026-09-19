# WSP97 Work Order — Implement RedDog Mosh Pit Protocol

Status: `WORK_ORDER`
Owner surface: `extensions/reddog`
Canonical behavior spec: `extensions/reddog/docs/MOSH_PIT_PROTOCOL.md`
Related architecture: `extensions/reddog/docs/MOSH_PIT_ACTIVITY_MEMORY_ARCHITECTURE.md`

## Mission

Implement the Mosh Pit Protocol as a **principal-centered projection over existing Breadcrumb/Brain/Memex memory**, not as a new database.

The implementation must preserve the distinction:

- technical Breadcrumbs = broad 0102/agent/system continuity;
- Mosh Pit = governed **012 continuity** projection;
- 0102-only background work is excluded unless a delegated result materially changes principal/project state.

## Required WSP posture

1. Run WSP_00 intake before editing.
2. Apply WSP_97 ownership discovery and use HoloIndex first.
3. Inspect existing memory/query/runtime seams before creating new code.
4. Reuse `query_past_work()`, `query_unresolved_work()`, FoundUp Brain/Memex state, Breadcrumb persistence, contact-memory linkage, and projection/emitter infrastructure where applicable.
5. Do not create a parallel Mosh Pit store.
6. Preserve principal/privacy boundaries and fail closed.
7. Add tests before claiming implementation complete.
8. Update RedDog docs/HOLOINDEX/ModLog with the actual integration seam and status.

## Existing seams to inspect first

At minimum:

- `modules/communication/moltbot_bridge/src/openclaw_memory_queries.py`
- `modules/communication/moltbot_bridge/src/foundup_memex_current_state.py`
- `modules/communication/moltbot_bridge/src/foundup_brain_current_state.py`
- Breadcrumb storage/query components under cross-platform memory/livechat
- `extensions/reddog/docs/MEMEX_PROJECTION_EMITTER_ARCHITECTURE.md`
- `extensions/reddog/docs/CONTACT_MEMORY_ARCHITECTURE.md`
- `WSP_framework/src/WSP_60_Module_Memory_Architecture.md`

If HoloIndex or ownership metadata is stale, repair/index it under the applicable WSP before proceeding.

## Functional requirements

### 1. Candidate-event contract

Introduce or extend a typed event structure capable of representing:

```text
event_id
event_time | approximate_time | date_only
principal_id
actor
foundup_id / project_scope
action
counterparty_or_place
state_change
status
truth_class
evidence_refs[]
contact_refs[]
artifact_refs[]
open_loop_refs[]
disclosure_class
supersedes_event_id?
```

Do not duplicate data already represented in existing event/Breadcrumb structures; extend/adapt instead.

### 2. Mosh Pit inclusion gate

Implement a deterministic policy function/service that classifies a candidate as `include`, `exclude`, or `needs_resolution`.

Include when one or more apply:

- 012 physical-world action;
- 012 decision/approval/rejection;
- joint 012+0102 work materially changed project state;
- external response materially changed next action;
- consequential delegated 0102 result changed project state;
- project milestone/state transition.

Exclude:

- internal search/reasoning;
- formatting-only changes;
- tool retries/plumbing;
- failed queries with no consequence;
- routine code iterations with no project-state change;
- every-utterance logging.

`needs_resolution` is required for ambiguous identity, causation, disclosure, or materially uncertain event time.

### 3. Actor normalization

Support canonical actors:

- `012`
- `012+0102`
- `0102-delegated`
- `PC`
- `external`

Normalize common STT variants of 0102 without destroying source evidence.

### 4. Truth/provenance

Preserve at least:

- `observed`
- `reported_by_012`
- `evidenced`
- `inferred`
- `proposed`

Never promote inference or causation to fact without evidence.

### 5. Projection renderer

Implement a project-scoped reverse-chronological Mosh Pit renderer.

Default compact rendering should support:

```text
NOW
OPEN LOOPS
RECENT ACCOMPLISHMENTS
HISTORY
```

Full history should grow upward in the human view while storage remains chronological/implementation-defined.

### 6. RedDog retrieval behavior

Wire RedDog/0102 retrieval for variants of:

- what did we do?
- where were we?
- what happened today/this week?
- show the Mosh Pit/timeline
- what is still open?
- what do we return to next?

The response should resolve project scope, retrieve Mosh Pit-qualified events, combine Brain/Memex open loops, deduplicate receipts, and return compact output first.

### 7. Contact-memory linkage

One underlying event must be projectable into both contact memory and Mosh Pit without duplication.

Contact memory = relationship-centric view.
Mosh Pit = principal/project-continuity view.

### 8. Daily reconciliation

Add a bounded curator/reconciliation path that can process candidate events and answer:

- what materially happened to 012/project state?
- what joint/delegated result became consequential?
- what external response changed next action?
- what stayed machine-internal and should be excluded?
- what remains open?

This worker may curate existing memory records/projections but must not maintain a second history database.

### 9. YUMORI alpha adapter

Treat `YUMORI.me Moshpit` as the founding alpha projection.

Implement the architecture so a governed external projection adapter could later sync a Google Doc, but **do not make Google Docs canonical storage** and do not add automatic external write authority as part of the core memory path.

### 10. Privacy and disclosure

Support disclosure classes for at least:

- private principal
- team/PC
- stakeholder
- public

Raw contacts/private evidence remain principal-scoped. Retrieval does not imply external mutation. Public projection requires explicit approved disclosure.

## Required tests

Add focused tests covering at least:

1. 012 field action -> included.
2. 012 decision -> included.
3. 012+0102 document/financial-model milestone -> included.
4. delegated 0102 consequential result -> included.
5. 0102 search/tool retry -> excluded.
6. formatting-only document edit -> excluded.
7. external reply changing next action -> included.
8. unsupported causation -> marked inferred/needs-resolution, not fact.
9. duplicate receipts -> one Mosh Pit event.
10. contact-memory and Mosh Pit share one underlying event.
11. principal/disclosure mismatch -> fail closed.
12. reverse-chronological renderer ordering.
13. open-loop retrieval combines Brain/Memex state.
14. STT alias normalization preserves source text.

## Acceptance criteria

Do not declare complete until all are true:

- Mosh Pit is implemented as a projection, not a parallel store;
- inclusion gate enforces 012-centered continuity;
- consequential `0102-delegated` work is supported;
- routine 0102 background activity is excluded;
- RedDog can retrieve compact status/history for one FoundUp/project;
- open loops are included from Brain/Memex;
- provenance/truth classes are preserved;
- contact-memory integration does not duplicate events;
- disclosure tests fail closed;
- unit/integration tests pass;
- HOLOINDEX and relevant ModLog/ROADMAP docs are updated with exact files/symbols/status.

## Deliverable report

Return:

- exact files changed;
- exact existing seams reused;
- new symbols/classes/functions;
- tests run and results;
- remaining gaps;
- whether YUMORI Google Doc sync remains projection-only/not wired;
- branch/PR integration state.

Do not claim runtime support that was not tested.
