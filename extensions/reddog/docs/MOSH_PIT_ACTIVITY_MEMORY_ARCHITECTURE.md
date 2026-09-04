# RedDog Mosh Pit Activity Memory Architecture

## Purpose

The Mosh Pit is the principal-scoped, append/prepend activity ledger that answers a different question from contact memory:

> What did 012 + 0102 actually do, in what order, what changed because of it, and what evidence proves it?

It is not a diary, transcript dump, city history, generic RAG store, or automatic public feed. It is an evidence-backed operational history of the shared 012/0102 work.

The founding YUMORI workflow is the alpha pattern: physical-world actions by 012 and digital/research/engineering actions by 0102 occur in parallel and must be recoverable as one project history.

## Layer Ownership

```text
live interaction / capture
        |
        v
RedDog surface
  - low-latency interaction
  - capture receipt
  - immediate ambiguity only
        |
        v
0102 activity-memory cognition
  - normalize STT aliases (0102 / 01-02 / zero one zero two)
  - identify actors/projects/events
  - retrieve related evidence
  - distinguish fact / inference / claim
  - generate candidate ledger events
        |
        v
Mosh Pit logger / curator worker
  - deduplicate
  - provenance-bind
  - assign confidence
  - preserve corrections
  - prepend accepted event
        |
        v
principal-scoped event store
        |
        +--> project Mosh Pit views
        +--> stakeholder-safe views
        +--> grant / deck / report chronology
        +--> RedDog contextual recall
```

RedDog should not itself become the historical database. RedDog is the front attention/capture layer. 0102 owns deeper interpretation and retrieval. A bounded **Mosh Pit logger/curator worker** maintains the operational ledger behind them.

## Core Event Model

Every accepted event should carry at least:

- `event_id`
- timestamp or bounded/approximate time
- actor: `012`, `0102`, `PC`, external party, or joint actor
- project / FoundUp
- concise action (noun/verb factual form)
- outcome, if observed
- source evidence references
- provenance and confidence
- disclosure class
- correction/supersession links
- optional related contact/organization/meeting entities
- optional Git commit / PR / artifact references

The canonical store is structured events. The human-facing Mosh Pit document is a **view**, not the database.

## Reverse-Chronological View

The Mosh Pit view grows upward:

```text
[space for next event]
2026-09-05 ...
2026-09-04 ...
2026-09-03 ...
...
RESEARCH / PRE-LAUNCH FOUNDATION
```

New accepted events are prepended. Old events are not silently rewritten. Material corrections create explicit correction/supersession evidence while the rendered view may show the corrected canonical fact.

## What Belongs in the Ledger

The spine is:

```text
012/0102 found out
-> researched
-> decided
-> acted / built
-> response observed
-> next action
```

External facts enter the timeline only when they caused, constrained, validated, or materially changed our work. The Mosh Pit is not a parallel history of the city, a company, or the world.

Examples:

- `012: met Sano; presented reuse concept.`
- `0102: eSingularity PWA moved into canonical FoundUps module; PR #1608.`
- `012 + 0102: NVIDIA/Japan compute-financing research changed viability assessment; active collateral work began.`
- `PC: quorum established; second meeting scheduled.`

## Daily Logger Pattern

A lightweight logger worker should be able to run continuously/asynchronously from receipts and again at a daily reconciliation boundary.

### Continuous candidate capture

Candidate events can be spawned by:

- conversation decisions
- photos/business cards/screenshots
- calendar/meeting evidence where authorized
- Git commits and PRs
- created/updated artifacts
- government/business interactions captured by 012
- explicit commitments and follow-ups
- AutoPost capture receipts

The worker does **not** publish every interaction. It creates candidate events.

### Daily reconciliation

At a daily boundary, the curator asks:

1. What materially happened today?
2. Is it already represented?
3. What evidence supports it?
4. Which actor owns the action: 012, 0102, PC, joint, external?
5. Is timing exact, approximate, or unknown?
6. Does it belong to this FoundUp/project?
7. What disclosure class applies?
8. Is a human decision needed because identity/causation is ambiguous?

If nothing material changed, no ledger entry is required.

## Evidence and Truth Boundary

The logger must distinguish:

- **OBSERVED** — directly evidenced event/result.
- **REPORTED_BY_012** — principal's contemporaneous account, preserved as such.
- **INFERRED** — derived relationship or significance.
- **PROPOSED** — future action/strategy, not accomplished fact.

Example: `zazen protest occurred` and `vote was postponed` may both be observed/reported. `protest caused postponement` must not become an asserted fact without evidence supporting causation.

## Actor Attribution

Actor prefixes are first-class metadata, not decoration.

- **012** — principal's physical-world action.
- **0102** — digital-twin research, documentation, architecture, coding, analysis, artifact work.
- **012 + 0102** — genuinely joint decision/discovery/work product.
- **PC** — formal preparatory-committee action once organizational authority exists.
- **External** — response or event included only because it materially changed our activity.

The shared-operation convention remains **our work**. Actor attribution records execution provenance; it does not divide the operation into competing ownership claims.

## STT / Alias Normalization

Surface transcription must not fragment identity. Examples such as:

```text
0102
01-02
0 1 0 2
zero one zero two
```

normalize to the same canonical actor `0102` when context/evidence supports it. Original transcript text remains preserved as evidence. Normalization never destroys the source artifact.

The same principle applies to contact names, project names, Japanese/English aliases, and known speech-recognition artifacts.

## Contact Memory Integration

Mosh Pit activity memory and contact memory share the event graph but answer different questions:

- **Contact memory**: who is this person, what is our relationship, what commitments remain?
- **Mosh Pit**: what did our operation do and what happened next?

A meeting can therefore exist once as an event and be projected into both views.

```text
Meeting Event
  -> participant edges -> Contact Memory
  -> project/action edge -> Mosh Pit
  -> evidence edge -> capture/photo/message
  -> commitment edges -> follow-up system
```

No duplicate prose record is required.

## Git / Engineering Integration

For FoundUps work, Git history is high-value evidence. The logger can ingest PR/commit receipts and attach them to project events.

Do not dump every repository change into every Mosh Pit. Include technical work when it:

1. directly builds the FoundUp/project;
2. emerges directly from field use of that FoundUp/project; or
3. materially improves the 012/0102 system used to execute it.

This allows a project chronology to show physical and digital execution in parallel without becoming a repository changelog.

## Disclosure Views

One underlying event store can render different governed views:

- **private principal view** — names, evidence, relationship notes, exact counterparties where legitimate.
- **team/PC view** — operational facts needed by the organization.
- **stakeholder view** — concise milestones; confidential investor/contact identities withheld.
- **public view** — approved facts only.

Disclosure is a view policy. Redaction does not alter the canonical private event.

## Google Doc / Human Mosh Pit

A living Google Doc can be a convenient human-facing projection for YUMORI, with new entries prepended at the top. It should not become the only canonical memory store.

Target behavior:

```text
structured event store
-> render stakeholder-safe reverse chronology
-> prepend/update living Google Doc
-> retain evidence references internally
```

If Google Doc synchronization is unavailable, the event store remains authoritative and can regenerate the view later.

## Attention Behavior

The Mosh Pit logger normally stays below the RedDog attention boundary. RedDog surfaces it only when:

- an event is materially ambiguous;
- evidence conflicts;
- a promised follow-up is at risk;
- a milestone changes the next action;
- the principal asks for an accounting/history;
- a stakeholder report needs refresh.

The human should not spend the day maintaining the log. **Act first; organize never; reconcile automatically.**

## Implementation Slices

1. **Documentation / schema** — define event and disclosure contracts.
2. **Local event store** — principal-scoped, append-only/correction-aware structured events.
3. **Conversation/capture candidate adapter** — explicit receipt input first; no ambient surveillance assumption.
4. **Git receipt adapter** — PR/commit candidates matched to FoundUps/projects.
5. **Daily curator worker** — dedupe, evidence classification, project matching, ambiguity queue.
6. **Mosh Pit renderer** — reverse chronology with actor prefixes.
7. **Google Doc adapter** — governed prepend/sync of approved view.
8. **RedDog attention integration** — surface only consequential ambiguity/follow-up.

## Non-Goals / Safety

- No automatic public posting.
- No silent inference of sensitive identity.
- No claim that every conversation sentence is a historical event.
- No rewriting source evidence to match normalized entities.
- No causal claims without evidence.
- No contact or project data crossing principal boundaries.
- No Google Doc, GitHub, email, social, financial, or other external mutation without the appropriate governed authority.
- No requirement that 012 manually maintain the ledger.

## Founding Alpha

YUMORI demonstrates the need directly. 012 moves through the physical world — City Hall, police, community, investors, prefecture — while 0102 simultaneously builds websites, research, economic models, RedDog architecture, documentation, and code. A useful digital twin must remember both streams as one evidence-backed operational history and be able to answer, at any moment:

> What have we done, what changed, what is still open, and what is the next highest-leverage action?
