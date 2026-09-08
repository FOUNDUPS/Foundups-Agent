# RedDog Mosh Pit Protocol

Status: `CANONICAL_BEHAVIOR_SPEC` / `IMPLEMENTATION_REQUIRED`

## Purpose

The **Mosh Pit Protocol** is the principal-continuity layer for RedDog/0102. It is the human operational breadcrumb projection for a FoundUp or project.

It answers:

- What did 012 do?
- What did 012 decide or approve?
- What materially changed because 012 and 0102 worked together?
- What consequential delegated result did 0102 complete for 012?
- What remains open and should be resumed?

The Mosh Pit is **not** a general 0102 activity log, repository changelog, transcript dump, or second memory database.

## Core distinction

**Breadcrumbs** can record broad agent/system discovery and execution history.

**Mosh Pit** is a governed projection of Breadcrumb/Brain/Memex state centered on **012 continuity**.

Default inclusion rule:

> Record an event when 012 participated in it, initiated it, approved it, witnessed it, caused it through delegated authority, or when a delegated 0102 result materially changed 012's project state.

Default exclusion rule:

> Do not record internal 0102 searches, reasoning, formatting, retries, tool plumbing, code iterations, failed queries, or background work that produced no meaningful principal/project state change.

This makes Mosh Pit to 012 what technical Breadcrumbs are to 0102: a recoverable continuity trail, but filtered for principal significance.

## Canonical event tests

A candidate event belongs in the Mosh Pit if **at least one** is true:

1. **012 physical-world action** — meeting, protest, visit, call, encounter, field test, presentation, inspection, signing, payment, travel for project execution.
2. **012 decision** — approved/rejected strategy, changed direction, selected a plan, created a commitment, assigned delegated work.
3. **012 + 0102 joint work** — materially changed a document, model, financial plan, architecture, campaign, artifact, stakeholder position, or implementation direction.
4. **External response to our action** — reply, approval, rejection, commitment, contradiction, funding/technical evidence, or stakeholder change that materially changes next action.
5. **Consequential delegated 0102 result** — 0102 completed an authorized action or artifact that changed project state, even if 012 was not actively present during execution.
6. **Milestone / state transition** — project moved from idea to outreach, draft to submitted, contact to committee member, hypothesis to validated/rejected, open loop to closed.

If none apply, keep it in technical Breadcrumbs/logs, not Mosh Pit.

## Event schema

Each Mosh Pit event should be capable of resolving to:

```text
event_id
event_time | approximate_time | date_only
principal_id = 012
actor = 012 | 012+0102 | 0102-delegated | PC | external
foundup_id / project_scope
action
counterparty_or_place
state_change
status = completed | open | blocked | proposed | superseded
truth_class = observed | reported_by_012 | evidenced | inferred | proposed
evidence_refs[]
contact_refs[]
artifact_refs[]
open_loop_refs[]
disclosure_class
supersedes_event_id?
```

The human projection should normally show only:

**Date/time -> 012 action/decision -> counterpart/place -> resulting state change -> evidence/status**

## Actor semantics

- `012` — principal physically acted, spoke, decided, approved, witnessed, or directly executed.
- `012+0102` — genuine joint reasoning/work product where the principal directed or shaped the result.
- `0102-delegated` — 0102 completed authorized work that materially changed principal/project state. Log the **result**, not the internal computation.
- `PC` — formal preparatory committee or organization acted under its authority.
- `external` — include only when the external event materially changed our project state.

Examples:

```text
GOOD: 012 + 0102 strengthened Document 03 with investment, financing and 60-day FS logic; 03 became the primary economic support document.
BAD: 0102 searched 14 websites and reformatted six paragraphs.

GOOD: 0102-delegated sent the approved university technical-review outreach; Aoki replied that the request is outside his expertise, closing that expert lead.
BAD: 0102 retried Gmail search twice.

GOOD: 012 protested at the onsen intersection for the first time, expanding field activity beyond City Hall.
```

## Capture pipeline

```text
RedDog interaction / phone / meeting / email / artifact / repo evidence
        -> candidate event
        -> 0102 normalization + evidence binding
        -> Mosh Pit inclusion gate
        -> canonical Breadcrumb / Brain-Memex update
        -> project-scoped Mosh Pit projection
        -> optional private/team/stakeholder/public view
```

Do **not** create a separate Mosh Pit persistence database. Use existing principal-scoped Breadcrumb/Brain/Memex event state and render the Mosh Pit as a projection.

## RedDog behavior

RedDog should capture candidate events below the attention boundary while interacting with 012. It should not repeatedly interrupt 012 to ask whether obvious events should be logged.

RedDog/0102 should surface a clarification only when:

- identity is ambiguous;
- causation would otherwise be overstated;
- a sensitive disclosure class is uncertain;
- time/date materially matters and cannot be bounded;
- the event could change a formal record or external submission.

When 012 asks "what did we do?", "where are we?", "what happened this week?", or equivalent, RedDog should retrieve the Mosh Pit projection first, then Brain/Memex open loops.

## Contact-memory integration

A single event may project into both contact memory and Mosh Pit.

- Contact memory asks: **Who is this person and what happened between us?**
- Mosh Pit asks: **What did 012/our operation do and how did the project change?**

Do not duplicate the underlying event.

## Evidence and truth

Never silently promote inference to fact.

Maintain:

- source transcript/image/email/receipt;
- normalized event statement;
- truth class;
- confidence;
- corrections/supersession.

STT artifacts such as `01-02`, `0 1 0 2`, and `zero one zero two` may normalize to `0102` when context supports it, while preserving the original source.

## Daily reconciliation

At a bounded daily boundary, the curator should ask:

1. What did 012 materially do or decide?
2. What joint 012+0102 work changed project state?
3. What delegated 0102 results became consequential?
4. What external responses changed next action?
5. What milestones or open loops changed state?
6. Which candidate items are merely machine activity and should stay out?
7. Is every included item evidence-backed or explicitly marked `reported_by_012`/`inferred`/`proposed`?
8. Are contact and artifact references linked without duplicating events?

## Projection order

Default human view is reverse chronological and grows upward. Storage order is independent.

```text
TODAY
- newest consequential principal event
- next event

YESTERDAY
- ...

OPEN LOOPS
- ...
```

## YUMORI founding alpha

`YUMORI.me Moshpit` is the current alpha human projection. It is a working principal-continuity record, not the canonical database.

The alpha should be used to test:

- field-event capture;
- email/reply linkage;
- contact linkage;
- document/financial-model milestone capture;
- 012 vs 012+0102 vs 0102-delegated attribution;
- daily reconciliation;
- reverse-chronological rendering;
- later regeneration from canonical memory.

## Safety / privacy

- principal-scoped by default;
- no public sync without explicit disclosure policy;
- no bulk raw contact leakage into model context;
- no silent identity inference;
- no causal claims without evidence;
- no automatic external mutation from retrieval alone;
- local-device/private-vault contact identifiers should be preferred where available;
- source evidence must remain separable from public/stakeholder projections.

## Relationship to existing architecture

This protocol specializes `MOSH_PIT_ACTIVITY_MEMORY_ARCHITECTURE.md` by defining the inclusion gate around **012 continuity**. Technical Breadcrumbs remain broader. Brain/Memex remains the state-consolidation layer. RedDog remains the low-latency surface and 0102 the deeper normalization/reasoning layer.
