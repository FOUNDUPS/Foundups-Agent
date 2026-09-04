# RedDog / FoundUp Memex Projection Emitter

Status: `SPECIFIED_NOT_IMPLEMENTED`

This document defines a target contract. It is not evidence that a projection
emitter, authorization service, renderer, or external sink is operational.

## Purpose

The emitter turns existing FoundUp memory state into governed, human-readable projections without creating another memory database.

Canonical source path:

```text
Breadcrumbs + Brain/Memex + verified evidence
        |
        v
projection request
        |
        v
policy/authz gate
        |
        v
Memex Projection Emitter
        |
        +--> RedDog compact status
        +--> Mosh Pit reverse chronology
        +--> founder dashboard
        +--> PC/team view
        +--> stakeholder view
        +--> public-safe export
```

The emitter is a renderer/projection service. It is not an authority source and it does not own canonical history.

## Security Model

Actual principal/project history must not live in the public repository. The repo contains only schemas, renderer code, tests, fixtures using synthetic/public-safe data, and documentation.

Private runtime records remain principal-scoped and encrypted. A projection request must bind all of:

- authenticated principal/session;
- `principal_id`;
- `foundup_id` / project scope;
- disclosure class;
- snapshot/content digest or equivalent freshness binding;
- short-lived read capability / authorization receipt;
- requested projection type.

Default behavior is deny. A missing, stale, ambiguous, revoked, cross-principal, or cross-FoundUp authorization fails closed.

### Disclosure classes

Canonical classes:

```text
principal_private
team_pc
stakeholder
public
```

A canonical private event is not rewritten for disclosure. Projection policy decides which fields/events survive into each view.

Example:

- `principal_private`: investor identity + meeting evidence where legitimately retained.
- `team_pc`: operational facts needed by the committee.
- `stakeholder`: "investment-capable company; positive meeting; follow-up planned."
- `public`: omitted unless explicitly approved.

## Non-Authority Invariant

The emitter receives read capability only. It has no implicit authority to:

- write Breadcrumbs;
- mutate Brain/Memex;
- merge contacts;
- execute queued work;
- modify GitHub;
- send email/messages;
- publish social content;
- change financial data;
- synchronize an external document.

Any later external sink (web page, Google Doc, PDF, API, etc.) requires a separately governed write/export adapter.

## Projection Contract

A projection request should be explicit:

```text
principal_id
foundup_id
projection_type
  - compact_status
  - mosh_pit
  - accomplishments
  - open_loops
  - timeline
  - stakeholder_report
disclosure_class
time_range / limit (optional)
snapshot binding / freshness receipt
authz capability
```

The emitter should return structured JSON first, with HTML/Markdown as deterministic renderings of that structure.

Suggested response shape:

```json
{
  "projection_id": "...",
  "foundup_id": "...",
  "disclosure_class": "principal_private",
  "snapshot_id": "...",
  "generated_at": "...",
  "now": [],
  "open_loops": [],
  "recent_accomplishments": [],
  "timeline": [],
  "evidence_receipts": [],
  "redactions": [],
  "invariants": {
    "read_only": true,
    "principal_scoped": true,
    "no_source_mutation": true
  }
}
```

## RedDog Retrieval Behavior

When 012 asks:

- "What are we doing?"
- "Where were we?"
- "What did we accomplish?"
- "What's left?"
- "Show the YUMORI history."

RedDog should resolve the target FoundUp, obtain an authorized Memex projection, and present the smallest useful answer.

Default compact order:

```text
NOW
OPEN LOOPS
RECENT ACCOMPLISHMENTS
NEXT HIGHEST-LEVERAGE ACTION
```

Full reverse chronology is expanded only when requested.

## Mosh Pit Rendering

The Mosh Pit is one projection type. It remains reverse chronological:

```text
2026-09-05
- 012: ...
- 0102: ...
- PC: ...

2026-09-04
...

RESEARCH / PRE-LAUNCH FOUNDATION
...
```

Ordering is determined from canonical event timestamps/bounds. Storage order is irrelevant.

The emitter may include actor labels, outcome state, evidence class, PR/commit references, and correction markers according to disclosure policy.

## Evidence / Truth Rules

Projection must preserve distinctions among:

- `OBSERVED`
- `REPORTED_BY_012`
- `INFERRED`
- `PROPOSED`

A renderer may simplify labels for human readability but must not upgrade an inference/proposal into an observed fact.

Causal claims require supporting evidence. Alias normalization (for example `0102`, `01-02`, `0 1 0 2`) may unify entities in the projection while preserving original source text in evidence storage.

## Data Protection

Minimum target controls:

1. encryption at rest for principal-scoped private event/evidence stores;
2. TLS in transit;
3. short-lived scoped capabilities/tokens;
4. server-side authorization on every projection request;
5. no security-by-secret-URL;
6. audit receipt for projection access where appropriate;
7. deterministic disclosure filtering;
8. secret/credential scanning before any public/stakeholder projection;
9. rate/bounds limits to prevent bulk exfiltration;
10. explicit cross-principal isolation tests;
11. source evidence never embedded in public build artifacts by default;
12. logs minimize sensitive payloads and retain identifiers/digests instead.

## Lick Relationship

Lick can contribute governed identity/session evidence, but Lick evidence is not blanket authority. A successful Lick encounter/identity proof may strengthen authentication or continuity; authorization to read a FoundUp projection still requires the appropriate principal/project/disclosure capability.

## Existing System Integration

Do not rebuild memory retrieval.

Use and extend existing surfaces:

- WSP 60 Breadcrumbs for activity/discovery trails;
- FoundUp Brain/Memex current-state assembly;
- existing past-work and unresolved-work query paths;
- Contact Memory event/entity graph for relationship-linked events;
- HoloIndex for governed discovery/retrieval of code/docs;
- verified Git/PR/artifact receipts as technical evidence.

The emitter composes these into a projection. It does not replace them.

## Export / Sink Adapters

Initial runtime should return JSON/Markdown locally or through the authenticated RedDog/founder surface.

Possible later adapters:

- founder web dashboard;
- static/SSR stakeholder page;
- Google Doc synchronization;
- PDF/report export;
- grant/deck chronology feed.

Each sink receives an already disclosure-filtered projection and has separate mutation authority. A sink must never query private stores directly if the emitter can provide the governed projection.

## Threat Model Summary

Primary risks:

- cross-principal data leakage;
- disclosure-policy bypass;
- stale authorization replay;
- accidental private evidence in public repo/build;
- secret URL treated as authentication;
- prompt/model output upgrading uncertain claims;
- unrestricted bulk timeline export;
- sink adapter gaining source-write authority;
- logs retaining sensitive raw payloads.

Design response: explicit principal/FoundUp binding, short-lived capabilities, fail-closed authorization, deterministic policy filtering, read-only emitter, bounded outputs, provenance-preserving truth classes, and independent sink authority.

## Acceptance Invariants

A production implementation is not complete until tests prove:

- same principal + authorized FoundUp + valid capability can retrieve permitted view;
- wrong principal fails closed;
- wrong FoundUp fails closed;
- stale/revoked/malformed capability fails closed;
- `stakeholder` and `public` cannot leak private-only fields;
- renderer never mutates Breadcrumb/Brain/Memex source state;
- source truth classification survives projection;
- pagination/bounds cannot bypass disclosure controls;
- synthetic secret-bearing input is redacted/rejected from public-safe projection;
- RedDog can answer status/history from the emitted structure without requiring a parallel prose database.

## WSP Boundary

Implementation must begin in **WSP_00 state**: inspect current repo/work state, existing memory/query interfaces, and WSP constraints before proposing edits.

Apply **WSP 97** agentic execution discipline: use HoloIndex and existing module interfaces to locate canonical owners, avoid vibe coding, assign bounded implementation slices, validate each slice independently, and preserve audit/receipt lineage.

The first implementation milestone is intentionally narrow: **read-only local projection from existing synthetic/test Breadcrumb + Brain/Memex inputs, with disclosure filtering and security tests.** Do not add external publishing or broad autonomous write authority in the same slice.
