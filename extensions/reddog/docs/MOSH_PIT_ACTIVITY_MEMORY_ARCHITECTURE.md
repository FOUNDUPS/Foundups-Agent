# RedDog Mosh Pit Projection Architecture

Status: `PARTIALLY_SUPPORTED` / `UNIFIED_RENDERER_NOT_IMPLEMENTED`

Canonical behavior authority: `MOSH_PIT_PROTOCOL.md`.

This document defines the architecture and composition of the Mosh Pit projection. If any wording here could be read more broadly than the protocol, the protocol wins. In particular, the Mosh Pit is an **012-centered principal-continuity projection**, not a general 0102 activity log.

Existing Breadcrumb and Brain/Memex query components are reusable inputs. The unified Mosh Pit projection and reverse-chronological renderer are not wired.

## Purpose

The **Mosh Pit is not a new memory subsystem**. It is a governed, reverse-chronological project/FoundUp projection assembled from the memory architecture already present in FoundUps Agent:

- **Breadcrumbs** record the broad evidence-backed activity/discovery trail, including technical 0102/agent continuity.
- **Brain** is the durable consolidation component that interprets current state, active work, queued work, roadmap state, verified outcomes, and breadcrumb position.
- **Memex** is the canonical broader FoundUp memory/current-state surface; Brain is one component inside it.
- **RedDog** is the low-latency human-facing proxy/attention boundary that retrieves and presents the useful projection.
- **0102** performs deeper normalization, retrieval, reasoning, evidence reconciliation, and prioritization behind RedDog.
- **Mosh Pit** is the principal-significance view: what 012 did/decided, what materially changed through joint 012+0102 work or consequential delegated 0102 work, what happened next, what is complete, what remains open, and what should be resumed.

The founding YUMORI workflow is the alpha pattern: 012 acts in the physical world while 0102 performs supporting research, documentation, architecture, coding, analysis, and artifact work. Both streams remain recoverable in Breadcrumb/Brain/Memex, but **only principal-significant events pass into the Mosh Pit projection**.

## Canonical Flow

```text
live interaction / capture / repo work / external encounter
        |
        v
RedDog surface
  - low-latency interaction
  - capture/attention boundary
        |
        v
0102 normalization + evidence binding
  - normalize STT aliases
  - identify actor / FoundUp / event
  - classify fact vs inference vs proposal
  - connect evidence, contacts, PRs, artifacts
        |
        v
Breadcrumbs
  - broad chronological activity/discovery trail
  - provenance-bearing event records
        |
        v
FoundUp Brain / Memex
  - current state
  - active work
  - queued/open work
  - roadmap state
  - verified outcomes
  - breadcrumb high-water mark / history position
        |
        v
Mosh Pit inclusion gate (`MOSH_PIT_PROTOCOL.md`)
  - 012 action/decision
  - 012+0102 material state change
  - consequential 0102-delegated result
  - material external response
  - milestone/state transition
        |
        +--> Mosh Pit reverse chronology
        +--> accomplishments / milestones
        +--> open loops / "go back to this"
        +--> stakeholder-safe status report
        +--> RedDog "what are we doing?" retrieval
```

No duplicate Mosh Pit database should be created. The same underlying event/evidence graph should feed contact memory, Breadcrumbs, Brain/Memex, and Mosh Pit projections.

## Breadcrumb Contract

Breadcrumbs are the broad event trail. A meaningful operational breadcrumb should be capable of carrying or resolving to:

- event/timestamp or bounded approximate time;
- canonical actor;
- principal/project/FoundUp scope;
- concise factual action;
- observed result/outcome when known;
- evidence/provenance references;
- confidence / truth classification;
- related contact, organization, meeting, commitment, PR, commit, or artifact identifiers;
- disclosure class;
- correction/supersession linkage where needed.

Breadcrumb history should remain source-preserving. Correcting a normalized fact must not destroy the original transcript, image, capture, or receipt.

Breadcrumb inclusion is broader than Mosh Pit inclusion. A technical 0102 breadcrumb may be valid without belonging in the Mosh Pit.

## Brain / Memex Contract

Brain/Memex answers **what the breadcrumb trail means now**.

For one FoundUp it should consolidate, without silently rewriting history:

- current state;
- completed/verified outcomes;
- active work;
- queued work;
- unresolved commitments;
- roadmap state;
- relationship-dependent follow-ups;
- relevant breadcrumb range/high-water mark;
- candidate next actions.

This is the layer that handles 012 moving rapidly between topics. A diversion does not need to be manually remembered by 012. Brain/Memex should retain the open loop so RedDog can later surface: "we still need to return to this."

## Mosh Pit Projection

Mosh Pit is the human-readable **012-continuity** projection over selected Breadcrumbs plus current-state interpretation from Brain/Memex.

The canonical inclusion/exclusion tests live in `MOSH_PIT_PROTOCOL.md`; this architecture must not introduce a competing event policy.

Its default YUMORI-style rendering is reverse chronological and grows upward:

```text
[space for next event]
2026-09-08
- 012: field action / decision ...
- 012+0102: material project-state change ...
- 0102-delegated: consequential authorized result ...
- PC: formal committee action ...

2026-09-07
- ...

RESEARCH / PRE-LAUNCH FOUNDATION
```

The oldest/origin material remains at the bottom. New material is prepended. This ordering is a **view rule**, not a storage rule.

## Retrieval Contract for RedDog

RedDog must be able to answer compactly when 012 asks variants of:

- "What have we done?"
- "Where were we?"
- "What did we accomplish today/this week?"
- "Show me the YUMORI timeline."
- "What is still left over?"
- "What do we need to go back to?"
- "What consequential thing did 0102 complete for me?"
- "What did 012 do in the field?"

Retrieval should combine existing memory lanes rather than depend on a single prose document:

1. resolve FoundUp/project scope;
2. retrieve matching/recent Breadcrumbs;
3. retrieve Brain/Memex current state and open/queued work;
4. retrieve verified Git/PR/artifact evidence where relevant;
5. apply the canonical Mosh Pit inclusion gate;
6. deduplicate multiple receipts representing one event;
7. normalize aliases while preserving source evidence;
8. sort events by event time for the requested view;
9. return a concise projection with explicit actor attribution and provenance class;
10. separately identify **completed**, **open**, and **next-highest-leverage** work when requested.

For a general "what are we doing?" request, the target RedDog output is:

```text
NOW
- current highest-leverage work

OPEN LOOPS
- items Brain/Memex says remain active/queued/unresolved

RECENT ACCOMPLISHMENTS
- reverse-chronological Mosh-Pit-qualified events

HISTORY
- available on request as the full Mosh Pit projection
```

### Current implementation boundary

The repository already contains reusable runtime pieces for this retrieval path:

- `query_past_work()` searches workspace memory plus AgentDB Breadcrumbs;
- `query_unresolved_work()` retrieves unresolved/queued work;
- FoundUp Brain/Memex assembly already consumes Breadcrumb state plus active/queued work and verified outcomes.

The unified Mosh Pit runtime renderer and principal-significance gate are not yet claimed wired into RedDog. The implementation work order is `docs/prompts/WSP97_REDDOG_MOSH_PIT_PROTOCOL_IMPLEMENTATION_PROMPT.md`.

## What Belongs in a Project Mosh Pit

The operational spine is:

```text
012 acts/decides or delegates
-> 0102/RedDog captures and binds evidence
-> project state materially changes
-> response/outcome is observed
-> open/next action retained
```

An event belongs when the canonical protocol says it has principal significance. Routine 0102 search/reasoning/formatting/retries/tool plumbing/code iterations stay in technical Breadcrumbs unless their **delegated result materially changes project state**.

External events enter only when they caused, constrained, validated, rejected, or materially changed our work. The Mosh Pit is not a history of the City, NVIDIA, an investor, or another organization.

Examples:

- `012: met Sano; presented reuse concept.`
- `012+0102: strengthened Document 03 with investment, financing and 60-day FS logic; it became the primary economic support document.`
- `0102-delegated: sent approved technical-review outreach; a reply closed one expert lead.`
- `PC: quorum established; second meeting scheduled.`
- **Excluded:** `0102 searched 14 sites, retried Gmail, reformatted paragraphs.`

## Event / Truth Classification

Useful projections must preserve the distinction between:

- **OBSERVED** — directly evidenced event/result;
- **REPORTED_BY_012** — 012's contemporaneous account;
- **EVIDENCED** — supported by durable external/artifact evidence;
- **INFERRED** — derived relationship/significance;
- **PROPOSED** — future action or strategy, not accomplished fact.

Example: `zazen protest occurred` and `decision was postponed` can coexist as historical events. `protest caused postponement` must not be promoted to fact without supporting evidence.

## Actor Attribution

Actor labels are provenance, not ownership partitions. Canonical actor semantics are defined by `MOSH_PIT_PROTOCOL.md`:

- **012** — principal physically acted, spoke, decided, approved, witnessed, or directly executed.
- **012+0102** — genuine joint work where 012 directed/shaped the result and project state materially changed.
- **0102-delegated** — authorized 0102 result that materially changed principal/project state; log the result, not internal computation.
- **PC** — formal committee action after organizational authority exists.
- **External** — included only when its action materially changed ours.

A generic `0102` technical actor remains valid in Breadcrumbs but does **not** automatically qualify for Mosh Pit projection.

The founding-operation convention remains **our work** while preserving actor provenance.

## STT / Alias Normalization

Surface transcription must not fragment identity. These all normally resolve to canonical actor `0102` when context supports it:

```text
0102
01-02
0 1 0 2
zero one zero two
```

The original transcript remains attached as provenance. The same rule applies to known project/contact aliases and recurring STT artifacts.

## Contact Memory Integration

Contact memory and Mosh Pit are different projections over overlapping event evidence:

- **Contact memory**: who is this person, what is our relationship, what happened between us, what commitments remain?
- **Mosh Pit**: what did 012/our operation do, what happened next, and how did the FoundUp advance?

A meeting should exist once as an event/breadcrumb and be projected into both contexts.

## Git / Engineering Integration

Git history is high-value evidence for 0102 activity, but engineering activity enters a project Mosh Pit only when the canonical principal-significance gate passes. Typical qualifying cases:

1. 012 directed/approved a change that materially changed the FoundUp/project;
2. the engineering change emerged directly from field use and changed the principal's operating capability; or
3. consequential delegated 0102 implementation completed an authorized project milestone.

Routine commits, retries, CI noise, refactors, formatting and internal implementation detail remain in technical Breadcrumbs/ModLogs, not Mosh Pit.

## Daily Reconciliation

A bounded curator/logging worker can reconcile candidate Breadcrumbs asynchronously and at a daily boundary. It should ask:

1. What did 012 materially do or decide?
2. What joint 012+0102 work changed project state?
3. What delegated 0102 results became consequential?
4. What external responses changed next action?
5. What milestones/open loops changed state?
6. Which candidate items are merely machine activity and should stay out?
7. Is it already represented by another receipt?
8. What evidence supports it?
9. Is the time exact, approximate, or unknown?
10. Is human resolution required for identity, causation, or disclosure ambiguity?

The worker creates/curates Breadcrumb evidence and Brain/Memex candidates; it does not maintain a second historical database.

## Disclosure Views

One underlying evidence trail can support multiple governed projections:

- **private principal** — full legitimate evidence and counterparties;
- **team/PC** — operational facts needed by the organization;
- **stakeholder** — concise milestones with confidential counterparties withheld;
- **public** — explicitly approved facts only.

Redaction is a projection policy, not a mutation of canonical evidence.

## Google Doc Projection

A living Google Doc is appropriate as a convenient stakeholder/human Mosh Pit view for YUMORI. It should be generated from approved Mosh-Pit-qualified Breadcrumb/Brain/Memex state and should not become the sole canonical memory store.

Target:

```text
Breadcrumbs + Brain/Memex
-> canonical Mosh Pit inclusion gate
-> Mosh Pit projection
-> disclosure filter
-> prepend/sync living Google Doc
```

If Google synchronization is unavailable, the underlying memory remains intact and the document can be regenerated later.

## Attention Behavior

This machinery normally stays beneath the RedDog attention boundary. Surface it when:

- 012 explicitly asks for history/status/accounting;
- an open loop is being forgotten;
- a commitment/follow-up is at risk;
- evidence conflicts;
- a milestone changes the next action;
- a stakeholder report needs refresh.

**Act first; capture automatically; reconcile below the attention boundary.**

## Implementation Direction

Do not build a separate Mosh Pit store. Follow the canonical work order:

`docs/prompts/WSP97_REDDOG_MOSH_PIT_PROTOCOL_IMPLEMENTATION_PROMPT.md`

The implementation direction remains:

1. reuse/extend the existing project/FoundUp-aware Breadcrumb event contract;
2. ensure relevant 012/012+0102/0102-delegated/PC events can enter with provenance;
3. implement the canonical inclusion gate;
4. ensure Brain/Memex consolidates completion/open-loop state from those receipts;
5. extend existing `query_past_work()` + `query_unresolved_work()` retrieval;
6. add Git/PR/artifact receipt matching;
7. add the reverse-chronological renderer;
8. add optional governed Google Doc synchronization;
9. keep RedDog output concise by default and expand full history only on request.

## Non-Goals / Safety

- no new parallel memory database;
- no automatic public posting;
- no silent sensitive-identity inference;
- no conversion of every utterance into a historical event;
- no destruction of source text during normalization;
- no causal claim without evidence;
- no principal-boundary leakage;
- no external mutation authority implied by memory retrieval;
- no requirement that 012 manually maintain the log;
- no generic 0102 background activity in Mosh Pit merely because it happened.

## Founding Alpha

YUMORI makes the architecture visible. 012 moves through City Hall, community, stakeholders and field activity while 0102 simultaneously supports research, models, documents, outreach, RedDog architecture and code. Breadcrumbs preserve the broad evidence trail. Brain/Memex keeps current meaning and open loops. The Mosh Pit inclusion gate extracts the principal-significant continuity view. RedDog should then be able to answer:

> **What did 012 do? What materially changed through our work? What is complete? What remains open? What do we return to next?**
