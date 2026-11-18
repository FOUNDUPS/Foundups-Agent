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

Status: `SPECIFIED_NOT_IMPLEMENTED` for the unified mobile conversation UX, action menu, cross-surface search, Muzzle/sticky controls and automatic capture-to-Moshpit path. This section consolidates 012/0102/RedDog/Little Dog dialogue; it is a product requirement, not a deployment or tool-access claim.

### Layers and source of truth

- RedDog is the fast, persistent interaction/attention layer; 0102 is the deeper principal-scoped cognition and governed orchestration layer. Interaction effort defaults initially to **Instant**, with **Think** and **Deep** levels plus optional **Auto** routing (preferred only after routing verification); changing effort modifies compute/response behavior, **not** identity, permission or storage authority.
- **Little Dog**, **Dog**, and **Big Dog** aliases are customizable presentation only, never identity, model, permission, or authority proof.
- **Discussion, discovery, and execution are distinct modes.** Discussion is not automatic decision-making, memory certification, or worker authorization.
- AutoPost (`FOUNDUPS/autopost`) is the externally owned, locally permissioned camera/perception surface. Do not copy another camera stack into `Foundups-Agent`. Local AI may propose structured, evidence-linked capture context, but must not auto-publish, assert identity, or authorize disclosure. Lick remains the consent-aware encounter handshake and never grants blanket access.
- Principal Activity Ledger (PAL) captures eligible local activity once; Breadcrumbs preserve evidence; Brain/Memex consolidates state; Moshpit renders selected material project events and recoverable discussion sources. Do not create a second store or treat every chat utterance as a project event.
- Durable joinable Work/task handoff must reuse existing Work/task owners with real returned IDs/links, traceable status, and day-based recall evidence. Spoken acknowledgment, dispatch, run-ended, and verified completion are separate states. `docs/0102_session_briefings/work_ledger.schema.json` and `work_ledger.example.json` are historical/candidate specs only; `reddog_work_ledger_source_projection_supply.py` stamps projection time rather than a verified daily history join.
- DAEmon emits sanitized diagnostics (model load duration, capture/inference latency, media/network errors, failed actions, retries, recovery, and 012 corrections) using existing DAEmon owners with private evidence kept outside public Git. Diagnostic observations are not automatically project accomplishments.

### Context actions, archive and deletion

On a conversation message, Markdown block, artifact or Moshpit title, a long-press (touch) or equivalent context action (mouse/keyboard) should expose concise text-labeled actions, without decorative emoji: **Pin / Unpin, Audit, Store, Archive, Delete**. Show only actions applicable and authorized for that object.

- **Pin / Unpin** keeps a stable reference to an original message/Markdown/artifact identity and revision, not a duplicate. The bottom thumb pin tray navigates back to the original while preserving the reading anchor and rechecking access and source lifecycle; it is not the same as storing evidence or recording a completed outcome.
- **Audit** requests an evidence/provenance/status check; it does not itself mark the content verified.
- **Store** proposes/adopts a governed Breadcrumb, PAL event or Brain/Memex update according to materiality and source authority. Never silently promote brainstorming (`PROPOSED`/`INFERRED`) into canonical `OBSERVED` project truth.
- **Archive** removes a conversation/title from the active Moshpit browsing surface while preserving authorized history and references; it is not deletion. Exact archive ownership and retention policy require implementation audit.
- **Delete** is a separately confirmed, scoped operation with source/reference lifecycle handling and an explicit receipt; never infer deletion of canonical evidence, backups, remote copies or audit logs from hiding a title. Destructive authority and retention policy must be resolved first.
- Titles can be archived/deleted independently of project facts. Pinned references to archived, deleted, revoked, expired, or superseded sources must retain honest inaccessible/deleted/superseded states and withhold revoked excerpts, never silently retarget.
- No context action automatically creates a GitHub commit, sends email, publishes content, triggers wallet/token execution, grants work authority or invokes a worker.

### Ordering, search and navigation

- Search must state its scope: current conversation/thread, pinned sources, current FoundUp/project Moshpit, or explicitly selected and authorized cross-FoundUp discovery. Default to the active context; do not silently search all private projects.
- Search matches messages, Markdown blocks, artifact references, relevant Breadcrumbs and project status through existing authorized query/projection owners. Results should preserve provenance, stable source navigation and the reading anchor; use bounded pagination and avoid loading entire history.
- **Three-surface ordering contract (never conflate into one global sort):**
  1. **Generic RedDog conversation history**: oldest above, newest near the composer; live replies arriving while reading history preserve the scroll/reading anchor and offer return-to-latest.
  2. **AutoPost white conversational Moshpit**: swipe upward from an appropriate camera surface (kept separate from the upward-drag recording lock and `+` menu gesture) while retaining the live camera view and capture controls without unmounting or restarting its stream/controller; **latest items appear at the TOP and older below**.
  3. **Project activity/audit Moshpit**: reverse-chronological newest-first by JST (`Asia/Tokyo`) day, growing upward.
- RedDog's shared search-bar `+` may expose listening (`Auto Listen`, `Push to Talk`, `Off`), **Muzzle**, reasoning effort (`Instant`, `Think`, `Deep`, `Auto`), available local/browser/cloud models with truthful capability/loading state, sticky recording toggle, autoplay, and DAEmon diagnostics. Controls belong to the interaction shell; unavailable items stay visibly disabled (`Planned`), never presented as operational.

### Mobile control placement, Muzzle, sticky capture and governed media handoff

- Keep the bottom translucent dock shared across Mall, AutoPost, and other FoundUps (not camera-only search). The Mall camera icon beside RedDog opens existing AutoPost, preserving originating FoundUp, navigation position, and authorized conversation context so return restores the prior experience.
- In AutoPost, place the shared translucent bar below the iris/shutter, with `+` and RedDog replacing the microphone launcher while microphone input mute remains separately available. The separate pin tray opens from one nearby pin affordance; per-message long-press owns **Pin / Unpin, Audit, Store, Archive, Delete**.
- RedDog placement (`left` or `right`) is explicitly switchable in settings. 012 prefers **left**; do not infer a universal default from handedness.
- **Muzzle vs microphone mute:**
  - **Muzzle** is RedDog output mute: it silences RedDog audible output while generation/work continues, and listening continues when microphone input remains enabled.
  - Microphone input mute and **Muzzle** are independent of each other, and neither control is YouTube-player mute, preview mute, video-recording microphone settings, or cancellation of ongoing work.
  - Muzzle state must be visible to 012 and provided to the agent (avoiding unnecessary vocal filler; a barking-dog icon is a candidate only, not an implemented requirement asset).
  - **Open product decisions (must stay explicit until decided by 012):** (a) whether substantive responses are queued or surfaced separately while muzzled; (b) whether RedDog microphone mute also affects AutoPost video-recording audio.
- **AutoPost capture controls and sticky recording:** tap iris for photo; hold records video. With sticky off, release stops. Optional **sticky recording** in `+` settings makes release continue until the next tap stops. Preserve existing upward-drag recording lock, viewport camera-flip behavior, and capture settings; stopping video recording must not trigger a photograph.
- **Media attachment & security boundary:** captures share into the selected authorized conversation as references to original media with explicit `local`, `transferring`, `attached`, and `failed` states, bounded retries, and deduplication. Sharing into a conversation preserves original bytes, capture identity, and recording segments and never publishes publicly; multi-segment assembly and cross-origin transfer are **not** implemented merely by exporting local IndexedDB IDs.
- **Principal-isolation guardrail (`gotjunk_messages` / `gotjunk_blobs`):** in `modules/foundups/gotjunk/firestore.rules`, `gotjunk_messages` and `gotjunk_blobs` have `allow read: if true` (public read). Never route private principal conversations, pins, Moshpit history, or camera captures into those public collections; extend principal-scoped existing owners (`PrincipalActivityLedger`, `AgentDB`, authenticated adapter boundaries).
- Keep a separate, compact RedDog Work/task handoff for substantial implementation: record scope, status, PR/receipt and next action through existing work owners; do not promote conversational Moshpit messages directly to autonomous execution.

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

Reconcile existing GotJunk Wave message types/stores (excluding public-read Firestore rules), RedDog conversation owner, PAL adapter, Moshpit projection, `work_ledger` candidates, and AutoPost capture/DAEmon owners before coding. Verify a phone-sized soft-proto and physical-phone test matrix for: long-press menu; pin and jump; audit/store distinction; archive versus delete; scoped search; reading-anchor persistence; three-surface ordering separation; Muzzle and mic-mute independence; sticky recording stop-without-photo; captured evidence with corrected project classification; consent/permission denial; reload/reconnect; and cross-principal access denial. Each implemented slice must carry tests, a status receipt and roadmap reconciliation. Do not label a menu stub, source-only PoC or a document as a deployed feature.

### SoftProto preview and voice-directed capture convergence (2026-11-17; proposed)

Reuse [SoftProto foundation](../../../modules/foundups/docs/SOFTPROTO_FOUNDATION_ARCHITECTURE_2026-04-01.md), [rollout](../../../modules/foundups/docs/SOFTPROTO_ROLLOUT_PLAN_2026-04-01.md), and [live co-design preview extension](../../../modules/foundups/docs/SOFTPROTO_LIVE_CODESIGN_PREVIEW_EXTENSION.md). This is an incremental SoftProto/Moshpit acceptance contract, **not** a new camera module, screen recorder, preview host or deployed feature.

**Verified ownership and gaps:** The external [AutoPost](https://github.com/FOUNDUPS/autopost) repo owns camera capture, local media, multi-segment recording, perception, correction and DAEmon. The monorepo owns the SoftProto schema/gesture/command contracts, Mall shell and RedDog interface. AutoPost's browser screenshot references and camera recording do **not** establish a working browser/phone screen-capture API, cross-app recording, voice-command dispatcher, or authorized capture-to-preview evidence handoff. The existing SoftProto preview note is documentation-only; its isolated Svelte/custom-element spike and a phone-openable candidate preview URL require current runtime verification.

**Desired bounded loop:** 012 opens an admitted FoundUp's exact-revision phone preview from a RedDog/Moshpit link. The protected bottom RedDog control remains available in the supported shell; a change to external origin or browser tab must not be described as preserving a live session until independently tested. 012 says `take a screenshot` or `record ten seconds`. RedDog resolves the explicit command through the existing SoftProto addressable command/permission boundary, and AutoPost performs a **user-authorized** capture where the device/browser supports it. The user sees source selection (screen versus camera), capture/recording indicator, stop/cancel and preview/review before attachment. Attach the artifact reference, FoundUp ID, candidate commit/revision, page/route, viewport/device, time, consent state, and the spoken issue to an authorized task/feedback record; 0102 analyzes and proposes the smallest fix. No capture automatically publishes, mutates canonical Brain/Memex, or starts a worker.

**Sprint gates (WSP_15/WSP_97):** First verify a real phone-openable SoftProto preview URL and preserved/explicitly restored RedDog interaction. Next prove one on-demand screenshot using a permitted browser/device path, including denial and unsupported-OS fallback; then separately prove a bounded ten-second recording, stop/cancel, artifact review, privacy redaction and authorized feedback association. Continuous screen sharing, background cross-app capture and automatic screen observation remain deferred and require platform-specific feasibility/security review. Require actual phone tap/swipe and user acceptance before merge; a responsive desktop emulator or documentation link is not acceptance. Preserve gesture precedence: bottom-edge swipe opens Moshpit, while tile-area swipe scrolls the Mall. Track missing runtime pieces as bounded enhancements of existing owners, not as a second AutoPost implementation.

### DAEmon plus-reveal and synchronized debugging evidence (2026-11-17; proposed)

The existing external AutoPost DAEmon remains the **single diagnostics owner**. In the integrated RedDog/SoftProto shell, expose DAEmon through the existing `+` options/reveal control rather than adding a permanent left-side panel or a second logger. This is a proposed shell placement: preserve AutoPost's current right-swipe DAEmon gesture until an independently tested migration establishes no navigation regression. The expanded diagnostics view must be closable and must not obstruct RedDog, the camera/record stop, or the Moshpit bottom-edge gesture.

A user-authorized SoftProto screenshot or bounded recording should create a **time-correlated diagnostic evidence bundle** containing the media reference plus a bounded DAEmon snapshot/window: event timestamps and clock basis, relevant sanitized logs/errors, capture/perception state, device/runtime capability, performance/latency metrics where observed, FoundUp/route, build/revision and correlation ID. For a ten-second recording, retain the corresponding bounded log interval, including relevant lead-in/stop events, not an unbounded background log dump. Preserve provenance and distinguish observed events from inferred diagnoses. DAEmon retains source diagnostic ownership; RedDog/0102 consume only an authorized, minimized projection.

No raw credentials, tokens, private media, unrelated principal data, or unrestricted logs enter a public artifact, PR or model prompt. Apply explicit capture consent, redaction, size/time bounds, retention and revocation; show unavailable/partial evidence honestly when logs are inaccessible or clocks cannot be aligned. Neither opening DAEmon nor capturing diagnostics authorizes publishing or a worker action.

**Acceptance:** Verify on a physical phone that `+` reveals and closes DAEmon without gesture collisions; one screenshot yields a correlated sanitized log snapshot; one ten-second recording yields a correctly bounded diagnostic interval; deny/stop/reconnect/clock-skew and missing-log cases produce truthful receipts; the linked SoftProto feedback packet resolves to the exact candidate revision. Do not claim this UI placement or synchronized bundle is implemented from a documentation-only change.

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

External events enter only when they caused, constrained, validated, rejected, or materially changed our work. The Moshpit is not a history of the City, NVIDIA, an investor, or another organization.

Examples:

- `012: met Sano; presented reuse concept.`
- `012 + 0102: strengthened Document 03 with investment, financing and 60-day FS logic; became primary economic support document.`
- `0102-delegated: sent approved technical-review outreach; Aoki reply closed expert lead.`
- `0102: eSingularity PWA moved into canonical FoundUps module; PR #1608.`
- `012 + 0102: Japan/NVIDIA compute-infrastructure research changed viability assessment; active collateral work began.`
- `PC: quorum established; second meeting scheduled.`

### Principal-significance inclusion gate (include / exclude / needs_resolution)

This deterministic inclusion gate governs **project Moshpit activity/audit events**, while **recoverable RedDog conversation history (`conversation.message`) and pinned sources (`pin.item`) remain separate** so a conversational turn or pinned source does not need to be certified project truth.

- **`include`** when **at least one** canonical test holds:
  1. **`012` physical-world action** — meeting, protest, visit, call, encounter, field test, presentation, inspection, signing, payment, or travel for project execution.
  2. **`012` decision** — approved/rejected strategy, changed direction, selected plan, created commitment, or assigned delegated work.
  3. **`012 + 0102` joint work** — materially changed a document, model, financial plan, architecture, campaign, artifact, stakeholder position, or implementation direction.
  4. **External response to our action** — reply, approval, rejection, commitment, contradiction, funding/technical evidence, or stakeholder change that materially changes next action.
  5. **Consequential `0102-delegated` result** — `0102` completed an authorized action or artifact that materially changed principal or project state, even when `012` was not actively present during execution.
  6. **Milestone / state transition** — project moved from idea to outreach, draft to submitted, contact to committee member, hypothesis to validated/rejected, or open loop to closed.
- **`exclude`** (retain in technical Breadcrumbs/logs rather than the project Moshpit):
  - internal `0102` searches and reasoning steps;
  - formatting-only document edits;
  - tool retries and plumbing;
  - failed queries with no consequence;
  - routine code iterations with no project-state change;
  - every-utterance logging.
- **`needs_resolution`**: hold for concise `012` clarification rather than guessing or promoting inference to fact when actor/contact identity is ambiguous, causation would otherwise be overstated, sensitive disclosure class is uncertain, or event time materially matters and cannot be bounded.

Candidate project-Moshpit events should be capable of resolving to:

```text
event_id
event_time | approximate_time | date_only
principal_id = 012
actor = 012 | 012 + 0102 | 0102-delegated | PC | external
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

The compact human project-Moshpit line renders as:

`Date/time -> 012 action/decision -> counterpart/place -> resulting state change -> evidence/status`

## Event / Truth Classification

Useful projections must preserve the distinction between:

- **OBSERVED** — directly evidenced event/result;
- **REPORTED_BY_012** — 012's contemporaneous account;
- **EVIDENCED** — supported by durable external or artifact evidence;
- **INFERRED** — derived relationship/significance;
- **PROPOSED** — future action or strategy, not accomplished fact.

Example: `zazen protest occurred` and `decision was postponed` can coexist as historical events. `protest caused postponement` must not be promoted to fact without supporting evidence.

## Actor Attribution

Actor labels are provenance, not ownership partitions:

- **012** — principal's physical-world execution (acted, spoke, decided, approved, witnessed);
- **0102** — digital-twin research, documentation, architecture, coding, analysis, artifacts (remains in broad Breadcrumbs unless passing the principal-significance gate);
- **012 + 0102** — genuinely joint decision/discovery/work product where `012` directed or shaped a material project-state change;
- **0102-delegated** — authorized `0102` execution completed without `012` present whose **result** materially changed principal or project state (log the consequential result, not internal searches/retries);
- **PC** — formal committee action after organizational authority exists;
- **External** — included only when its action materially changed ours.

The founding-operation convention remains **our work** while preserving exact actor provenance:

- `GOOD`: `0102-delegated sent the approved university technical-review outreach; Aoki replied outside expertise, closing that expert lead.`
- `BAD`: `0102 searched 14 websites, retried Gmail search twice, and reformatted six paragraphs.`

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

1. What did `012` materially do or decide?
2. What joint `012 + 0102` work changed project state?
3. What consequential `0102-delegated` results changed principal or project state?
4. What external responses changed next action?
5. What milestones or open loops changed state?
6. Which candidate items are merely machine-internal activity (searches, retries, plumbing, formatting) and remain excluded from project Moshpit?
7. Is the item already represented by another receipt?
8. What evidence supports it (`OBSERVED`, `REPORTED_BY_012`, `EVIDENCED`, `INFERRED`, `PROPOSED`)?
9. Which actor (`012`, `012 + 0102`, `0102-delegated`, `PC`, `External`) owns execution provenance, and which FoundUp/project does it belong to?
10. Is the time exact, approximate, or unknown, is the item completed/open/blocked/proposed/superseded, does Brain/Memex already retain the associated open loop, and is `needs_resolution` required for identity, causation, or disclosure ambiguity?

The worker creates/curates Breadcrumb evidence and Brain/Memex candidates; it does not maintain a second historical database.

## Disclosure Views

One underlying evidence trail can support multiple governed projections:

- **private principal** — full legitimate evidence and counterparties;
- **team/PC** — operational facts needed by the organization;
- **stakeholder** — concise milestones with confidential counterparties withheld;
- **public** — explicitly approved facts only.

Redaction is a projection policy, not a mutation of canonical evidence.

## Google Doc Projection

A living Google Doc is appropriate as a convenient stakeholder/human Moshpit view for YUMORI. It should be generated from approved Moshpit-qualified Breadcrumb/Brain/Memex state and should not become the sole canonical memory store.

Target:

```text
Breadcrumbs + Brain/Memex
-> principal-significance inclusion gate
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

Do not build a separate Moshpit store. Reuse existing memory, contact, and projection owners (`modules/communication/moltbot_bridge/src/openclaw_memory_queries.py`, `foundup_memex_current_state.py`, `foundup_brain_current_state.py`, `CONTACT_MEMORY_ARCHITECTURE.md`, `CONTACT_COMMUNICATION_ACTION_PROTOCOL.md`, and `MEMEX_PROJECTION_EMITTER_ARCHITECTURE.md`) without overriding Contacts/native Docs authority or read-only Memex emitter boundaries. Extend existing surfaces in this order:

1. define/extend the project/FoundUp-aware Breadcrumb event contract;
2. ensure relevant `012`, `012 + 0102`, `0102-delegated`, `PC`, and qualifying external events enter with provenance;
3. implement the deterministic principal-significance inclusion gate (`include` / `exclude` / `needs_resolution`) for project Moshpit events while keeping recoverable conversation history and pinned sources separate;
4. ensure Brain/Memex consolidates completion/open-loop state from those receipts;
5. extend existing `query_past_work()` + `query_unresolved_work()` retrieval to emit a unified project activity projection;
6. add Git/PR/artifact receipt matching;
7. add the reverse-chronological project Moshpit renderer;
8. add optional governed Google Doc synchronization without making Google Docs canonical storage or granting automatic write authority;
9. keep RedDog output concise by default and expand full history only on request.

### Implementation acceptance cases and governance boundaries

Status of runtime gate and unified renderer: `SPECIFIED_NOT_IMPLEMENTED`. Accepting this specification grants **no** memory write, communication send, or worker/runtime admission. During discovery or implementation, **never reindex or repair stale HoloIndex inline during a query or feature slice; preserve freshness/index-gap diagnostics and route index maintenance through the governed `WSP_00` / WRE / CI maintenance owner.**

Focused implementation acceptance test cases required before claiming runtime completion:

1. `012` field action -> `include`;
2. `012` decision -> `include`;
3. `012 + 0102` document or financial-model milestone -> `include`;
4. consequential `0102-delegated` result -> `include` (result only, not internal retries);
5. `0102` internal search or tool retry -> `exclude`;
6. formatting-only document edit -> `exclude`;
7. external reply changing next action -> `include`;
8. unsupported causation -> marked `inferred` / `needs_resolution`, never promoted to fact;
9. duplicate receipts -> deduplicated into one Moshpit event;
10. contact-memory and Moshpit share one underlying event without overriding Contact authority or read-only Memex emitter boundaries;
11. principal or disclosure mismatch -> fail closed;
12. reverse-chronological project-Moshpit renderer ordering preserved independently of conversation ordering;
13. open-loop retrieval combines Brain/Memex state;
14. STT alias normalization preserves original source text.

## Non-Goals / Safety

- no new parallel memory database;
- no automatic public posting;
- no silent sensitive-identity inference;
- no conversion of every utterance into a historical event;
- no generic `0102` background activity promoted into project Moshpit without passing the principal-significance gate;
- no destruction of source text during normalization;
- no causal claim without evidence;
- no principal-boundary leakage;
- no external mutation authority implied by memory retrieval;
- no requirement that 012 manually maintain the log.

## Founding Alpha

YUMORI makes the architecture visible. 012 moves through City Hall, police, community, investors, and prefectural offices while 0102 simultaneously builds websites, research, models, documentation, RedDog architecture, and code. Breadcrumbs preserve those events. Brain/Memex keeps their current meaning and open loops. RedDog should be able to retrieve the relevant projection on demand and answer:

> **What have we done? What changed? What is complete? What remains open? What do we return to next?**
