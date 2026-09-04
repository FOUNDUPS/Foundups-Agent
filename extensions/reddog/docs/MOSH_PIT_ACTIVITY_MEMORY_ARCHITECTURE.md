# RedDog Mosh Pit Projection Architecture

## Purpose

The **Mosh Pit is not a new memory subsystem**. It is a governed, reverse-chronological project/FoundUp projection assembled from the memory architecture already present in FoundUps Agent:

- **Breadcrumbs** record the evidence-backed activity/discovery trail.
- **Brain** is the durable consolidation component that interprets current state, active work, queued work, roadmap state, verified outcomes, and breadcrumb position.
- **Memex** is the canonical broader FoundUp memory/current-state surface; Brain is one component inside it.
- **RedDog** is the low-latency human-facing proxy/attention boundary that retrieves and presents the useful projection.
- **0102** performs the deeper normalization, retrieval, reasoning, evidence reconciliation, and prioritization behind RedDog.
- **Mosh Pit** is a view: what we did, what happened, what is complete, what remains open, and what should be resumed next.

The founding YUMORI workflow is the alpha pattern: 012 acts in the physical world while 0102 simultaneously performs research, documentation, architecture, coding, analysis, and artifact work. Both streams must be recoverable as **our** single operational history.

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
  - chronological activity/discovery trail
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
        +--> Mosh Pit reverse chronology
        +--> accomplishments / milestones
        +--> open loops / "go back to this"
        +--> stakeholder-safe status report
        +--> RedDog "what are we doing?" retrieval
```

No duplicate Mosh Pit database should be created. The same underlying event/evidence graph should feed contact memory, Breadcrumbs, Brain/Memex, and Mosh Pit projections.

## Breadcrumb Contract

Breadcrumbs are the event trail. A meaningful operational breadcrumb should be capable of carrying or resolving to:

- event/timestamp or bounded approximate time;
- canonical actor: `012`, `0102`, `012 + 0102`, `PC`, or relevant external party;
- FoundUp/project scope;
- concise factual action;
- observed result/outcome when known;
- evidence/provenance references;
- confidence / truth classification;
- related contact, organization, meeting, commitment, PR, commit, or artifact identifiers;
- disclosure class;
- correction/supersession linkage where needed.

Breadcrumb history should remain source-preserving. Correcting a normalized fact must not destroy the original transcript, image, capture, or receipt.

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

Mosh Pit is the human-readable activity/history projection over selected Breadcrumbs plus current-state interpretation from Brain/Memex.

Its default YUMORI-style rendering is reverse chronological and grows upward:

```text
[space for next event]
2026-09-05
- 012: ...
- 0102: ...
- PC: ...

2026-09-04
- 012: ...
- 0102: ...

...

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
- "What did 0102 build?"
- "What did 012 do in the field?"

Retrieval should combine existing memory lanes rather than depend on a single prose document:

1. resolve FoundUp/project scope;
2. retrieve matching/recent Breadcrumbs;
3. retrieve Brain/Memex current state and open/queued work;
4. retrieve verified Git/PR/artifact evidence where relevant;
5. deduplicate multiple receipts representing one event;
6. normalize aliases while preserving source evidence;
7. sort events by event time for the requested view;
8. return a concise projection with explicit actor attribution and provenance class;
9. separately identify **completed**, **open**, and **next-highest-leverage** work when requested.

For a general "what are we doing?" request, the target RedDog output is:

```text
NOW
- current highest-leverage work

OPEN LOOPS
- items Brain/Memex says remain active/queued/unresolved

RECENT ACCOMPLISHMENTS
- reverse-chronological selected Breadcrumbs

HISTORY
- available on request as the full Mosh Pit projection
```

This is consistent with the existing `query_past_work` / Breadcrumb retrieval and unresolved-work concepts in the OpenClaw memory query lane. Runtime expansion should extend those existing surfaces rather than create a parallel query system.

## What Belongs in a Project Mosh Pit

The operational spine is:

```text
012/0102 found out
-> researched
-> decided
-> acted / built
-> response observed
-> outcome recorded
-> next/open action retained
```

External events enter only when they caused, constrained, validated, or materially changed our work. The Mosh Pit is not a history of the City, NVIDIA, an investor, or another organization.

Examples:

- `012: met Sano; presented reuse concept.`
- `0102: eSingularity PWA moved into canonical FoundUps module; PR #1608.`
- `012 + 0102: Japan/NVIDIA compute-infrastructure research changed viability assessment; active collateral work began.`
- `PC: quorum established; second meeting scheduled.`

## Event / Truth Classification

Useful projections must preserve the distinction between:

- **OBSERVED** — directly evidenced event/result;
- **REPORTED_BY_012** — 012's contemporaneous account;
- **INFERRED** — derived relationship/significance;
- **PROPOSED** — future action or strategy, not accomplished fact.

Example: `zazen protest occurred` and `decision was postponed` can coexist as historical events. `protest caused postponement` must not be promoted to fact without supporting evidence.

## Actor Attribution

Actor labels are provenance, not ownership partitions:

- **012** — principal's physical-world execution;
- **0102** — digital-twin research, documentation, architecture, coding, analysis, artifacts;
- **012 + 0102** — genuinely joint decision/discovery/work product;
- **PC** — formal committee action after organizational authority exists;
- **External** — included only when its action materially changed ours.

The founding-operation convention remains **our work**.

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
- **Mosh Pit**: what did our operation do, what happened next, and how did the FoundUp advance?

A meeting should exist once as an event/breadcrumb and be projected into both contexts.

## Git / Engineering Integration

Git history is high-value evidence for 0102 activity. Include technical work in a project Mosh Pit when it:

1. directly builds that FoundUp/project;
2. emerges directly from field use of that FoundUp/project; or
3. materially improves the 012/0102 system being used to execute it.

Do not turn the Mosh Pit into a complete repository changelog.

## Daily Reconciliation

A bounded curator/logging worker can reconcile candidate Breadcrumbs asynchronously and at a daily boundary. It should ask:

1. What materially happened?
2. Is it already represented by another receipt?
3. What evidence supports it?
4. Which actor owns execution provenance?
5. Which FoundUp/project does it belong to?
6. Is the time exact, approximate, or unknown?
7. Is the item completed, open, blocked, or proposed?
8. Does Brain/Memex already retain the associated open loop?
9. Is human resolution required for identity, causation, or disclosure ambiguity?

The worker creates/curates Breadcrumb evidence and Brain/Memex candidates; it does not maintain a second historical database.

## Disclosure Views

One underlying evidence trail can support multiple governed projections:

- **private principal** — full legitimate evidence and counterparties;
- **team/PC** — operational facts needed by the organization;
- **stakeholder** — concise milestones with confidential counterparties withheld;
- **public** — explicitly approved facts only.

Redaction is a projection policy, not a mutation of canonical evidence.

## Google Doc Projection

A living Google Doc is appropriate as a convenient stakeholder/human Mosh Pit view for YUMORI. It should be generated from approved Breadcrumb/Brain/Memex state and should not become the sole canonical memory store.

Target:

```text
Breadcrumbs + Brain/Memex
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

Do not build a separate Mosh Pit store. Extend existing surfaces in this order:

1. define a project/FoundUp-aware Breadcrumb event contract;
2. ensure relevant 012/0102/PC events can enter that trail with provenance;
3. ensure Brain/Memex can consolidate completion/open-loop state from those receipts;
4. extend existing past-work/unresolved-work retrieval to emit a unified project activity projection;
5. add Git/PR/artifact receipt matching;
6. add the reverse-chronological Mosh Pit renderer;
7. add optional governed Google Doc synchronization;
8. keep RedDog output concise by default and expand full history only on request.

## Non-Goals / Safety

- no new parallel memory database;
- no automatic public posting;
- no silent sensitive-identity inference;
- no conversion of every utterance into a historical event;
- no destruction of source text during normalization;
- no causal claim without evidence;
- no principal-boundary leakage;
- no external mutation authority implied by memory retrieval;
- no requirement that 012 manually maintain the log.

## Founding Alpha

YUMORI makes the architecture visible. 012 moves through City Hall, police, community, investors, and prefectural offices while 0102 simultaneously builds websites, research, models, documentation, RedDog architecture, and code. Breadcrumbs preserve those events. Brain/Memex keeps their current meaning and open loops. RedDog should be able to retrieve the relevant projection on demand and answer:

> **What have we done? What changed? What is complete? What remains open? What do we return to next?**
