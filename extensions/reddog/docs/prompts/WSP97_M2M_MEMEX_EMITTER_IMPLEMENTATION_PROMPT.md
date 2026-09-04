# WSP97 M2M Implementation Prompt — RedDog / FoundUp Memex Projection Emitter

## Mission

Implement the first governed runtime slice of the **Memex Projection Emitter** described in:

- `extensions/reddog/docs/MEMEX_PROJECTION_EMITTER_ARCHITECTURE.md`
- `extensions/reddog/docs/MOSH_PIT_ACTIVITY_MEMORY_ARCHITECTURE.md`
- `extensions/reddog/docs/CONTACT_MEMORY_ARCHITECTURE.md`

The objective is to let RedDog answer questions such as:

- What are we doing?
- What have we accomplished?
- What is still open?
- Where were we before the diversion?
- Show the project/FoundUp timeline.

Do this by composing existing Breadcrumb + Brain/Memex + verified-evidence surfaces. **Do not create a parallel memory database.**

## Mandatory Operating State

Begin in **WSP_00 state**.

Before editing code:

1. Inspect current repository head/work state.
2. Read the canonical RedDog architecture and the two docs listed above.
3. Use HoloIndex / repository-native search to locate existing owners for:
   - Breadcrumb retrieval;
   - FoundUp Brain/Memex current-state assembly;
   - `query_past_work()` / unresolved-work paths;
   - RedDog query routing;
   - authentication/capability patterns already used in the bridge/runtime;
   - tests covering fail-closed scope/freshness behavior.
4. Identify the smallest canonical module owner. Do not create a new top-level subsystem merely because the feature is new.
5. Record the discovered ownership map before implementation.

Apply **WSP 97** throughout. No vibe coding. No guessed paths/interfaces. If an owner already exists, extend it or add a bounded adapter through its documented interface.

## WSP 97 Agentic Execution

Use bounded M2M workers only where their scope is explicit and non-overlapping.

Suggested slices:

### Worker A — Retrieval/ownership map
- Locate canonical Breadcrumb, Brain/Memex, past-work and unresolved-work interfaces.
- Produce exact file/symbol map and implementation boundary.
- No code mutation.

### Worker B — Projection contract
- Implement deterministic internal projection schema/types.
- Inputs must be existing accepted/read-only state or synthetic fixtures.
- No external sink.

### Worker C — Disclosure/security gate
- Implement `principal_id + foundup_id + disclosure_class + freshness/capability` validation using existing authorization primitives where available.
- Fail closed.
- Do not invent a second auth framework if a compatible capability pattern exists.

### Worker D — Mosh Pit renderer
- Deterministic reverse-chronological projection from accepted events.
- Preserve actor attribution and truth class.
- No source mutation.

### Worker E — RedDog query integration
- Extend the smallest existing query route so requests such as "what are we doing?" can emit:
  - NOW
  - OPEN LOOPS
  - RECENT ACCOMPLISHMENTS
  - NEXT HIGHEST-LEVERAGE ACTION (only if existing current-state/priority evidence supports it)
- Full timeline only on explicit request.

### Worker F — Adversarial tests
Prove fail-closed behavior for:
- wrong principal;
- wrong FoundUp;
- stale/revoked/malformed capability;
- disclosure leakage;
- source mutation attempt;
- secret-bearing synthetic evidence in stakeholder/public projection;
- alias normalization without source destruction;
- pagination/limit bypass;
- unsupported/ambiguous truth class.

If the repository architecture makes these slices inappropriate, change the worker split only after documenting why.

## Hard Invariants

1. **Mosh Pit is a projection, not storage.**
2. **Breadcrumbs remain the chronological evidence trail.**
3. **Brain/Memex remains the current/open-loop consolidation layer.**
4. **RedDog remains the lightweight attention/interface layer.**
5. **0102 remains the deeper reasoning/retrieval/orchestration layer.**
6. Emitter is read-only with respect to source memory.
7. No public-repo storage of private 012/contact/investor/event evidence.
8. No security-by-secret-URL.
9. Authorization must bind principal + FoundUp + disclosure scope + freshness.
10. Lick evidence may strengthen identity/continuity but does not grant blanket read/write authority.
11. `OBSERVED`, `REPORTED_BY_012`, `INFERRED`, and `PROPOSED` must not be collapsed into one truth state.
12. External sinks are out of scope for the first runtime slice.
13. No Google Docs sync, email, social posting, GitHub writeback, financial mutation, or other external mutation is authorized by this task.
14. Preserve WSP 60 module memory ownership/boundaries.
15. Use existing capability/receipt/fail-closed patterns wherever compatible.

## First Runtime Milestone

Implement only:

```text
existing/synthetic Breadcrumb + Brain/Memex inputs
-> governed read validation
-> deterministic projection JSON
-> optional deterministic Markdown/text rendering
-> RedDog read/query surface
```

Do **not** implement:

- persistent new Mosh Pit store;
- external web publishing;
- Google Doc write/sync;
- automatic stakeholder distribution;
- autonomous contact merges;
- broad background surveillance/capture;
- authority expansion.

## Projection Types

Minimum target:

- `compact_status`
- `accomplishments`
- `open_loops`
- `timeline` / `mosh_pit`

Minimum fields in the internal projection result:

```text
projection_id
principal_id (may be opaque/hash in emitted logs)
foundup_id
disclosure_class
snapshot/freshness binding
generated_at
now[]
open_loops[]
recent_accomplishments[]
timeline[]
redactions[]
evidence_receipt identifiers/digests
read_only invariant
```

Do not expose raw private evidence payloads unless the requested disclosure contract explicitly permits them.

## RedDog UX Contract

Default answer to "what are we doing?":

```text
NOW
<small number of current items>

OPEN LOOPS
<small number of unresolved items>

RECENT ACCOMPLISHMENTS
<recent evidence-backed actions>
```

Do not dump the full timeline unless asked.

For "show the history/timeline/mosh pit", emit reverse chronological events with actor attribution:

```text
YYYY-MM-DD
- 012: ...
- 0102: ...
- PC: ...
```

## Security Acceptance

Tests are required before merge. At minimum prove:

- allowed principal/FoundUp/disclosure request succeeds;
- cross-principal request fails closed;
- cross-FoundUp request fails closed;
- stale/invalid capability fails closed;
- stakeholder/public scopes cannot see private-only event fields;
- no source-memory write occurs;
- projection output is deterministic for same accepted snapshot/input;
- secrets/private fixtures cannot leak into public-safe rendering;
- alias normalization maps known `0102` surface forms while evidence source remains unchanged.

## Validation / Documentation

Before completion:

1. Run focused tests for every touched module.
2. Run relevant existing regression suites for Breadcrumb/Brain/Memex/RedDog query routing.
3. Update README/INTERFACE/HOLOINDEX/ModLog only where the repository standards require it.
4. Update the architecture docs if actual owner boundaries discovered during implementation differ from the proposed direction.
5. Keep implementation claims exact: documentation target vs implemented runtime must remain clearly distinguished.

## PR Discipline

Create one clean feature PR. Keep unrelated changes out.

PR description must include:

- WSP_00 ownership map;
- files/symbols changed;
- security boundary;
- tests run/results;
- known non-goals;
- confirmation that no parallel Mosh Pit store was created;
- confirmation that no external mutation authority was added.

Squash only after the branch is coherent and validations pass.

## Completion Test

The feature is complete for this slice when RedDog can, from authorized existing test/runtime memory surfaces, answer a FoundUp-scoped status/history request with a deterministic, disclosure-filtered projection while preserving all principal, provenance, truth-class, and read-only invariants.
