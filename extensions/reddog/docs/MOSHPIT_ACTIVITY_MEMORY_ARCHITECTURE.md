# RedDog Moshpit Projection Architecture

Status: `PARTIALLY_SUPPORTED` / `UNIFIED_RENDERER_NOT_IMPLEMENTED`

**Canonical term:** `Moshpit` (one word). **Canonical machine token:** `moshpit`. Split or underscored variants must not be introduced into active contracts.

Existing Breadcrumb and Brain/Memex query components are reusable inputs. The
unified Moshpit projection and reverse-chronological renderer are not wired.

## Purpose

The **Moshpit is not a new memory subsystem**. It is a governed, reverse-chronological project/FoundUp projection assembled from the memory architecture already present in FoundUps Agent:

- **Breadcrumbs** record the evidence-backed activity/discovery trail.
- **Brain** is the durable consolidation component that interprets current state, active work, queued work, roadmap state, verified outcomes, and breadcrumb position.
- **Memex** is the canonical broader FoundUp memory/current-state surface; Brain is one component inside it.
- **RedDog** is the low-latency human-facing proxy/attention boundary that retrieves and presents the useful projection.
- **0102** performs the deeper normalization, retrieval, reasoning, evidence reconciliation, and prioritization behind RedDog.
- **Moshpit** is a view: what we did, what happened, what is complete, what remains open, and what should be resumed next.

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
        +--> Moshpit reverse chronology
        +--> accomplishments / milestones
        +--> open loops / "go back to this"
        +--> stakeholder-safe status report
        +--> RedDog "what are we doing?" retrieval
```

No duplicate Moshpit database should be created. The same underlying event/evidence graph should feed contact memory, Breadcrumbs, Brain/Memex, and Moshpit projections.

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

## Operational safety correction: timezone and send effects (2026-11-11)

Live Moshpits should show the latest JST day first, actions newest-first, and only a minimal skill pointer above the feed. Skills own verbose instructions and the registry; historical evidence remains intact. Convert provider timestamps to Asia/Tokyo independently of VPN/IP locale. This is a view contract, not proof that a unified renderer is deployed.

Moshpit history does not authorize or prove a Gmail send. Before any outbound effect reconcile exact-thread Gmail Sent, Inbox, drafts, latest Moshpit day and scoped asks. Incremental conversational improvements after a send default to an unsent revision. Another send needs a material delta and independent preflight. The November 11 Sunvista three-email incident exposed this missing guard. See reddog_correspondence_state/SKILLz.md and yumori_moshpit/SKILLz.md.

## Moshpit Projection

Moshpit is the human-readable activity/history projection over selected Breadcrumbs plus current-state interpretation from Brain/Memex.

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

## Conversation navigation and pins (specified, not implemented)

012's RedDog conversation is also a Moshpit working surface: useful messages,
Markdown blocks and artifacts should remain easy to find as discussion moves
between topics. This navigation view complements the project activity projection;
it does not turn every conversational utterance into an activity event.

| View or interaction | Required behavior |
|---|---|
| Conversation history | Latest messages sit near the bottom/composer. Scrolling upward reveals older history. |
| Project activity/audit projection | Retain the existing newest-day/newest-event-first view, including its JST conversion. |
| Pin a source | Pin/unpin a message, Markdown block or artifact from its contextual action. |
| Open pins | One thumb-reachable pin icon near the existing bottom conversation controls opens the scoped pin tray. |
| Select a pin | Navigate to and highlight the original source, loading only its required history range if necessary. |
| Continue browsing | Preserve the reading anchor during history loading, live replies, pin-tray navigation and return. |

Conversation ordering is a presentation rule, independent of storage order or the
activity renderer. New replies must not force a reader back to the bottom while
they are examining history. Provide a return-to-latest action when appropriate.
The pin tray must respect the phone safe area and composer, with equivalent
keyboard/mouse access and accessible labels/focus; it is not another permanent
toolbar or a second conversation surface.

### Pin references and lifecycle

Persist a pin as a reference through the existing principal-scoped conversation /
Breadcrumb / Brain-Memex owners. Resolve the actual owner before implementing;
do not create a separate Moshpit database or use browser storage as authority.
The reference must bind principal, FoundUp/project, session/thread, stable source
message/block/artifact identity, creator and pin timestamp. Bind an artifact
revision when a specific version is intended. A display label/excerpt is a
projection, not a replacement copy of canonical content.

Re-pinning the same source must not create duplicates. Unpinning removes only the
pin reference. Reload/reconnect should recover authorized pins from their owner.
Deleted, expired, inaccessible or superseded sources need explicit states; never
silently retarget a pin to different content. Recheck access at resolution and
rendering, and withhold excerpts when access has been revoked. A pin does not
change disclosure, establish approval/completion, or automatically inject its
content into a model's context.

### Wave reuse and smallest prototype

Inspect the existing Google Wave-inspired GotJunk message owners under
`modules/foundups/gotjunk/frontend/src/message/` and
`modules/foundups/gotjunk/frontend/components/MessageThreadPanel.tsx` for stable
message identity, persistence, synchronization, permissions and history rendering.
They are reuse candidates, not evidence that RedDog already integrates Wave or
supports pins. Reconcile their message order and scrolling behavior before reuse.

First verify a bounded soft-proto: pin one message and one Markdown/artifact
reference, open the bottom pin tray, jump into older paged history, then return
without losing reading position. Exercise new replies while reading, duplicate
pins, unpin, reload, changed/deleted sources and cross-principal denial. Preserve
the separate activity ordering. Phone-sized preview, keyboard/mouse checks and
physical-phone acceptance precede any claim of a working phone feature.

This section records a product requirement from the conversation prototype.
The current host chat does not gain a pin button from this documentation edit.
Implementation remains a planned slice in [the RedDog roadmap](../ROADMAP.md#moshpit-conversation-navigation-and-pins-planned).

## RedDog layers, Moshpit actions, search and AutoPost convergence (2026-11-17; proposed)

Status: `SPECIFIED_NOT_IMPLEMENTED` for the unified mobile conversation UX, action menu, cross-surface search and automatic capture-to-Moshpit path. This section consolidates 012/0102/RedDog/Little Dog dialogue; it is a product requirement, not a deployment or tool-access claim.

### Layers and source of truth

- RedDog is the fast, persistent interaction/attention layer; 0102 is the deeper principal-scoped cognition and governed orchestration layer. Interaction effort may be Instant, Think or Deep, with optional Auto routing; this changes compute/response behavior, **not** identity, permission or storage authority.
- AutoPost is the locally permissioned camera/perception surface. It may propose structured, evidence-linked capture context, but must not auto-publish, identify people conclusively or authorize disclosure. Lick remains the consent-aware encounter handshake and never grants blanket access.
- Principal Activity Ledger (PAL) captures eligible local activity once; Breadcrumbs preserve evidence; Brain/Memex consolidates state; Moshpit renders selected material project events and recoverable discussion sources. Do not create a second store or treat every chat utterance as a project event.
- DAEmon emits sanitized diagnostics (load time, capture/inference state, latency, error and recovery) with private evidence kept outside public Git. Diagnostic observations are not automatically project accomplishments.

### Context actions, archive and deletion

On a conversation message, Markdown block, artifact or Moshpit title, a long-press (touch) or equivalent context action (mouse/keyboard) should expose concise text-labeled actions, without decorative emoji: **Pin / Unpin, Audit, Store, Archive, Delete**. Show only actions applicable and authorized for that object.

- **Pin** keeps a stable reference to a source, not a duplicate. The bottom pin tray navigates back to the original; it is not the same as storing evidence or recording a completed outcome.
- **Audit** requests an evidence/provenance/status check; it does not itself mark the content verified.
- **Store** proposes/adopts a governed Breadcrumb, PAL event or Brain/Memex update according to materiality and source authority. Never silently turn brainstorming into canonical project truth.
- **Archive** removes a conversation/title from the active Moshpit browsing surface while preserving authorized history and references; it is not deletion. Exact archive ownership and retention policy require implementation audit.
- **Delete** is a separately confirmed, scoped operation with source/reference lifecycle handling and an explicit receipt; never infer deletion of canonical evidence, backups, remote copies or audit logs from hiding a title. Destructive authority and retention policy must be resolved first.
- Titles can be archived/deleted independently of project facts. Pinned references to archived or deleted sources must retain honest inaccessible/deleted states, not silently redirect.
- No context action automatically creates a GitHub commit, sends email, publishes content, grants work authority or invokes a worker.

### Search and navigation

- Search must state its scope: current conversation/thread, pinned sources, current FoundUp/project Moshpit, or permitted cross-FoundUp discovery. Default to the active context; do not silently search all private projects.
- Search matches messages, Markdown blocks, artifact references, relevant Breadcrumbs and project status through existing authorized query/projection owners. Results should preserve provenance, stable source navigation and the reading anchor; use bounded pagination and avoid loading entire history.
- Conversation messages remain newest near the composer; project Moshpit events remain newest-first by JST day. Do not conflate their ordering.
- RedDog's shared search-bar `+` may expose listening, reasoning effort, model diagnostics, autoplay and DAEmon. Those controls belong to the interaction shell; they must not crowd the contextual message-action menu or imply capabilities are active before testing.

### AutoPost-to-Moshpit flow

```text
permissioned AutoPost photo/video/observation
 -> local perception and explicit source/provenance reference
 -> proposed principal/project/intent classification (editable)
 -> scoped PAL / Breadcrumb admission when material and authorized
 -> Brain/Memex state and open-loop reconciliation
 -> Moshpit projection and RedDog contextual search/navigation
```

A filmed phone debugging session may suggest a debugging tag and an evidence-linked issue; a photographed car may suggest a vehicle FoundUp. Both remain suggestions until corrected/admitted. No raw personal media in public repo, and no automatic cross-principal publication.

### Soft-proto acceptance and drift gates

Reconcile the existing Wave-inspired GotJunk message controls, RedDog conversation owner, PAL adapter, Moshpit projection and AutoPost capture/DAEmon owners before coding. Verify a phone-sized soft-proto for: long-press menu; pin and jump; audit/store distinction; archive versus delete; scoped search; reading-anchor persistence; newest-first project projection; captured evidence with corrected project classification; consent denial; reload/reconnect; and cross-principal access denial. Each implemented slice must carry tests, a status receipt and roadmap reconciliation. Do not label a menu stub, source-only PoC or a document as a deployed feature.

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
- available on request as the full Moshpit projection
```

### Current implementation boundary

The repository already contains reusable runtime pieces for this retrieval path:

- `query_past_work()` searches workspace memory plus AgentDB Breadcrumbs;
- `query_unresolved_work()` retrieves unresolved/queued work;
- FoundUp Brain/Memex assembly already consumes Breadcrumb state plus active/queued work and verified outcomes.

This PR **does not claim that a unified Moshpit runtime renderer is already wired into RedDog**. It defines the canonical composition so the next runtime slice extends those existing query surfaces rather than creating a parallel memory/query stack.

## What Belongs in a Project Moshpit

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

External events enter only when they caused, constrained, validated, or materially changed our work. The Moshpit is not a history of the City, NVIDIA, an investor, or another organization.

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

Contact memory and Moshpit are different projections over overlapping event evidence:

- **Contact memory**: who is this person, what is our relationship, what happened between us, what commitments remain?
- **Moshpit**: what did our operation do, what happened next, and how did the FoundUp advance?

A meeting should exist once as an event/breadcrumb and be projected into both contexts.

## Git / Engineering Integration

Git history is high-value evidence for 0102 activity. Include technical work in a project Moshpit when it:

1. directly builds that FoundUp/project;
2. emerges directly from field use of that FoundUp/project; or
3. materially improves the 012/0102 system being used to execute it.

Do not turn the Moshpit into a complete repository changelog.

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

A living Google Doc is appropriate as a convenient stakeholder/human Moshpit view for YUMORI. It should be generated from approved Breadcrumb/Brain/Memex state and should not become the sole canonical memory store.

Target:

```text
Breadcrumbs + Brain/Memex
-> Moshpit projection
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

Do not build a separate Moshpit store. Extend existing surfaces in this order:

1. define a project/FoundUp-aware Breadcrumb event contract;
2. ensure relevant 012/0102/PC events can enter that trail with provenance;
3. ensure Brain/Memex can consolidate completion/open-loop state from those receipts;
4. extend existing `query_past_work()` + `query_unresolved_work()` retrieval to emit a unified project activity projection;
5. add Git/PR/artifact receipt matching;
6. add the reverse-chronological Moshpit renderer;
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
