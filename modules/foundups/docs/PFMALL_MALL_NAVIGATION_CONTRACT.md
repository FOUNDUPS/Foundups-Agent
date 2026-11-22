# p.fMALL Navigation Contract

**Version**: 2.3.0
**Date**: 2026-11-21
**Status**: Runtime baseline with explicitly pending shared dock, player and fractal acceptance changes

## 2026-11-21 — v26 phone candidate (unreleased)

This dated phone-lane record is retained from source `2a65e7983acb489084cecf1229fcfd582f68f19b`.
Its controlled results do not qualify the subsequent main reconciliation.
Sections 13–14 below remain the broader canonical contract; the qualified
phone subset does not implement that full matrix or finalize held defaults.

Build v25 remains the frozen comparison at its existing preview. Build v26 uses a
separate source receipt and preview channel; no production redirect or release is
part of this change. Phone-layout browser fixtures are separate from physical
Safari and installed-PWA evidence. The principal has opened v25 on an iPhone 11;
v26 physical playback, audio and uninterrupted three-clip transitions are NOT_RUN.

The shared pre-Fractal shell keeps one provider and one actionable bottom Search
Dock while entering/leaving WikiTube or app Full Video. A fully hidden parked
player pauses. Native YouTube controls and native fullscreen are not intercepted.
The leading + retains discovery controls, AutoPost and Video Options; the trailing
+ is Add FoundUp on Play and Add Video in the HPC pilot. Video preferences affect
app controls and qualified visible playback, never promise provider autoplay.

Play public browsing and static FoundUp details correspond to the currently
available public discovery surfaces. The requested future levels 1–2 public /
level 3+ member policy is not a deployed graph ACL. The separate Fractal runtime
`22374b161570b2cd0e265e1c2b8c1009fb599394` is not imported. Contributions remain
unavailable until an authoritative service verifies current identity, membership
and per-FoundUp editor permission (012 initially for HPC). A successful existing
invite check only restores a manual review; it does not publish or grant editor
permission. No six-month checkout is activated. Cross-origin HPC-to-Play
contribution return is not connected and fails closed.

The existing same-origin Play `/?signin=required` gate and `/sso-callback/` are
preserved. Valid legacy `enter` links resolve public metadata rather than being
silently intercepted as a Mall view. Auth/callback, deep links and existing invite
flows are excluded from public landing normalization. Apex-to-Play routing is a
pure tested plan only; no live apex redirect is installed.

The full HPC banner opens <https://hasan4speaker.com/>. The distinct Mall return
opens Play; Voice Your Opinion / Contact Congress retains
<https://vote.mtrout.com/contact>. Vote/Contact whole-banner return links to HPC
remain a different navigation contract.

Browse AI is a separate compatibility pilot: no model is preloaded, no automatic
cloud fallback, and no model capability is claimed. The explicit, checksum-bound
41-byte WASM addition fixture is not an AI model. Actual model selection/download
and WebGPU qualification remain later work, including same-runtime Safari/PWA
checks. This dependency does not block the phone UI candidate.


## 2026-11-16 acceptance update on native v21 (candidate, unreleased)

The latest 012 acceptance supersedes selected-row phone placement below:
one visible top-anchored player with independently scrolling grid beneath;
preserve selection, close/Back and single-instance queue transitions.
Pause when fully hidden/dismissed. Native v21's fully offscreen audio and
tucked visibility bypass are release blockers, not accepted navigation.
Retain YouTube minimum dimensions, unobscured controls and qualified
visible-player autoplay. See [HPC roadmap](../hpc/ROADMAP.md).

Public Play uses the same shell and the existing member-entry gate. Its
candidate top-level portrait grid has centered real FoundUp names and
six-item observer/manual incremental append. Current catalog: 16 records;
144 is the product target, not current inventory or a video classification.
Retain quick view, FoundUp entry, query/reset and scroll/expanded return.
Ordinary member category rows, grouped products and expanded video fields
retain their existing contracts. Incremental append is not virtualization
or server metadata pagination. See [Mall roadmap](../pfmall/ROADMAP.md).

The whole HPC left banner with build above remains separate from the right
Voice CTA. Vote and Contact Congress each have one whole-banner return link
to HPC and a distinct Red Dog Mall link in draft PR #2411; no deployed state
is implied. That historical shared-dock deferral is superseded by section 14;
other source, provider and device gates remain separate.


---

## 1. Purpose

p.fMALL is an **AI interaction space** — a new way of interacting with AI and the world. Video is the default surface, but the paradigm extends to any content type: documents, community, FoundUps. The same interaction model (pinch, zoom, navigate) works everywhere, with AI mediating all engagement. Built for FoundUps first, with hooks into all content. Videos are the catalog layer — they tell each FoundUp's story.

This document defines the Mall as **fixed navigation infrastructure**.

The Mall is not a SoftProto customization surface.

The Mall is a discovery map with fixed navigation grammar. Browsing does not
edit that grammar. The separately authorized graph-content proposals in
section 13 do not create a free-layout shell edit mode.

SoftProto customization begins **inside FoundUp interiors**, not in the Mall shell.

---

## 2. Mall Anchor Model

The Mall has three fixed vertical zones:

```
+---------------------------+
|         TOP ANCHOR        |  <- Account / Profile / Self
|---------------------------|
|                           |
|       MIDDLE FIELD        |  <- Mall / FoundUps / Navigation Space
|                           |
|---------------------------|
|       BOTTOM ANCHOR       |  <- Red Dog / Digital Twin / Agent
+---------------------------+
```

### 2.1 Top Anchor

**Owner**: Account surface
**Contains**: Avatar trigger, user handle, account access
**Behavior**: Swipe-down from top opens account plane
**Fixed**: Yes - position and trigger are not user-configurable

### 2.2 Middle Field

**Owner**: Mall navigation
**Contains**: FoundUp cards, discovery space, navigation field
**Behavior**: 2D map navigation (see Section 4)
**Fixed**: Yes - navigation grammar is not user-configurable

### 2.3 Bottom Anchor

**Owner**: Red Dog / Concierge
**Contains**: Red Dog trigger, concierge panel
**Behavior**: Tap opens concierge panel
**Fixed**: Yes - position and trigger are not user-configurable

---

## 3. Mall vs FoundUp Interior

| Attribute | Mall | FoundUp Interior |
|-----------|------|------------------|
| Customizable layout | NO | YES (SoftProto) |
| Edit mode | NO | YES |
| Gesture override | No arbitrary field remapping; planned shared video preferences in section 14 | YES (object-scoped); shared video preferences use section 14 |
| Module repositioning | NO | YES |
| AI projection | YES | YES |
| User navigation | YES | YES |
| Fixed grammar | YES | Partial (escape/close locked) |

**Rule**: The Mall is infrastructure. The FoundUp interior is user-owned space.

The shared Search Dock and video preferences in section 14 apply in both
columns. They are bounded platform settings, not permission to redesign the
Mall's axes, account anchors or non-video navigation.

---

## 4. Mall Navigation Grammar

### 4.1 Axis Semantics

The Mall is a navigable discovery field, not a linear feed.

```
Y axis = distance / relevance gradient
         up = further / less relevant
         down = nearer / more relevant

X axis = category / cluster / similarity band
         left = shift to adjacent cluster
         right = shift to adjacent cluster
```

### 4.2 Gesture Bindings (Runtime)

| Gesture | Mall Action | Status |
|---------|-------------|--------|
| swipe | Navigate: snapped field motion (default) or glide (override) | RUNTIME |
| tap or click video tile | Inspected wide desktop and HPC phone runtime opens the shared player at the selected tile; ordinary category rows retain inline preview and lane/clip identity. The HPC phone target in section 4.7 instead uses one top-anchored player above the scrolling grid. | RUNTIME baseline; HPC target SPECIFIED |
| tap or click non-video tile | Open the FoundUp quick view or the property listing detail. | RUNTIME |
| hover tile on desktop | Show available tile controls. | RUNTIME |
| Expand button | Open the shared full player for the selected video or lane. | RUNTIME |
| Enter button | Navigate to `/f/{foundup_id}` (WSP 104 canonical) | RUNTIME |
| pinch-out on an ordinary video lane | Expand the FoundUp into its video field. Desktop Ctrl+wheel up uses the same handler. | RUNTIME |
| pinch-in in the expanded field | Collapse back to the Mall. Desktop Ctrl+wheel down uses the same handler. | RUNTIME |
| long-press | Reserved (future: quick actions) | RESERVED |

### 4.3 Motion Modes (Runtime)

| Mode | Behavior | Status |
|------|----------|--------|
| Snap (default) | Discrete paging like iPhone home screens | RUNTIME |
| Glide | Fluid scroll for browsing (AI-tools override) | RUNTIME |

Set via `mallTileField.setMotionMode('snap')` or `mallTileField.setMotionMode('glide')`.

### 4.4 Keyboard Bindings (Fixed)

| Key | Mall Action | Status |
|-----|-------------|--------|
| Arrow Up | Navigate: further | FIXED |
| Arrow Down | Navigate: nearer | FIXED |
| Arrow Left | Navigate: cluster left | FIXED |
| Arrow Right | Navigate: cluster right | FIXED |
| Enter on a video tile | Match click on wide desktop and HPC phone entry. Other ordinary rows open the full player. | RUNTIME |
| Space on a tile | Use the tile's tap action. | RUNTIME |
| Escape | Close the active desktop poster player first. The next Escape can collapse the expanded lane. | FIXED |

### 4.5 What Users Cannot Do

Users cannot:
- Arbitrarily remap field-navigation swipe directions in the Mall
- Change the field axes; the approved video-object preferences in section 14
  are a specific exception, not a general gesture editor
- Hide Mall navigation controls
- Move Mall anchor zones
- Enter "edit mode" for the Mall itself
- Reposition FoundUp cards manually

### 4.6 Desktop poster browsing

The ordinary Mall checks member admission before mounting the member
catalog. `foundups.com/member/` remains an entry. The exact Play hostname
root forwards to its own `/member/` and permits the `/?signin=required`
return page. The shell loads lane and card
metadata and hands it to the shared field. On entry at 1024 CSS px or wider
with a fine primary pointer and hover, the default is the adaptive poster
grid. Touch and narrower entry use category rows. Saved layout takes
precedence, and the desktop grid retains its layout while resize adapts its
density. The state owner restores the selected layout and position.
[Member shell](../../../public/member/index.html) ·
[Tile field](../../../public/member/js/mall-tile-field.js) ·
[State restore](../../../public/member/js/mall-state-restore.js)

The grid can show video-backed FoundUps and cards for apps, repositories
and services. Non-video selection opens the existing quick view. Listings
use their detail view. Click, Enter or Space on a wide desktop video poster
enlarges its selected position and requests muted playback with the shared
player. The fullscreen button opens the full viewer. Expand from the inline
controls retains the same provider iframe. Hover reveals the action without
mounting media. Escape or Back returns focus and scroll to the poster.
After density reflow, dismissal restores the same tile in its new row.
WikiTube is the design reference for the full viewer and continuous queue.
The admitted browse dock searches the loaded Mall catalog. The full viewer
places its left-aligned queue search beneath the video and above the rail.
Search filters the active lane. Submit starts the first match when idle.
It leaves active playback alone.
[Catalog schema](PFMALL_VIDEO_MALL_CATALOG_SCHEMA.md) ·
[Quick view](../../../public/member/js/mall-planes.js) ·
[Full player](PFMALL_FULLSCREEN_PLAYER_CONTRACT.md)

The gesture engine recognizes double-tap and double-click. The tile field
binds click, keyboard activation and pinch handlers. FLIP animates expansion
and collapse of a FoundUp video field. Save and Share use explicit player
controls. [Gesture engine](../../../public/member/js/gesture-engine.js) ·
[Tile interactions](../../../public/member/js/mall-tile-field.js)

Before this change, a controlled Windows Chromium 143 run at 1440 × 900 CSS px
showed the member shell opening in rows. Selecting the grid gave eight columns
and 15 cards. Hover mounted zero iframes. Clicking a video lane mounted one.
Enter opened the shared full player, Ctrl+wheel expanded and collapsed the
Move2Japan lane, and clicking AutoPost opened its quick view. This run used
the real shell and catalog with a provider fixture at source `4c1d1e7d`.

HPC uses a fixed scoped collection. Its wide fine-pointer view opens the
shared theater and its narrow or touch view opens the portrait grid.
Desktop verification and the remaining preview work are tracked in the
shared roadmap.
[HPC acceptance](../hpc/ROADMAP.md) ·
[Desktop poster browsing PoC](../pfmall/ROADMAP.md#desktop-poster-browsing-poc)

---

### 4.7 HPC, Vote and Contact Congress return navigation — 012 request 2026-11-16

**CHANGES_POC_ACCEPTANCE / SPECIFIED, not a runtime or live-navigation claim.** The latest entire-banner request supersedes an icon-only return target. Preserve the existing PWA/tile architecture and existing Vote/Contact pages, with no parallel shell or new Voice tenant. The existing Mall implementation owner coordinates the Vote source and its existing Sites mirror.

| Surface/control | Required destination or behavior | Current source at `72a3182c` |
| --- | --- | --- |
| HPC -> Vote / Contact Congress | Reach the existing Vote landing and Contact Congress resource; retain `https://vote.mtrout.com/contact` for the existing Voice CTA. Qualify the intended Vote host/alias independently. | Contact CTA exists; do not infer a separately admitted Voice runtime. |
| Vote landing: entire top HPC banner | One accessible link to `https://hpc.foundups.com`, including banner text, padding and small top-corner animated Hasan icon in the same target. | `modules/foundups/voteballots/web/index.html` has no HPC banner. |
| Call Your Congressperson: entire top HPC banner | The same single-link HPC return behavior, preserving contact forms and existing navigation. | `modules/foundups/voteballots/web/contact.html` has no HPC banner. |
| Adjacent-surface Red Dog navigation icon | Reuse the existing Red Dog identity and link to `https://play.foundups.com`. Do not repurpose the portrait as Mall identity. | HPC scoped dog currently links to `/f/hpc#red-dog`; its portrait header currently links to `https://foundups.com/member/`. |
| HPC phone video selection | One deliberate tile tap requests playback in the existing shared, top-anchored floating player by default; saved destinations follow section 14. The grid scrolls independently below; retain WikiTube transitions/queue and close/back/query/scroll/focus recovery. | Current selected-tile placement remains implementation evidence; this new target is not implemented by this contract. |

The Vote/Contact banners and distinct Mall return links have a source candidate in [PR #2411](https://github.com/FOUNDUPS/Foundups-Agent/pull/2411), with fixture evidence in [Vote's TestModLog](../voteballots/tests/TestModLog.md). The table above records the inspected base; it is not an assertion that candidate navigation is live. Phone-player placement and new portrait artwork remain separate work.

Use concise **HPC** branding. Reuse the existing `public/member/hpc-icon-{180,192,512}.png` portrait and `public/logo-dog.png` Red Dog asset. 012's existing illustrated poster is the character reference for a satirical crown-of-thorns/optional-halo adaptation; the inspected portrait has neither. Materialize the supplied reference images through the supported Library route, verify local bytes and inspect pixels before image-dependent work. Keep the small portrait artwork to the recognizable face rather than the whole poster, and preserve independent/non-affiliation framing with no implied Hasan or organizational endorsement. Host approved copies on the adjacent page's existing origin without weakening its image CSP.

The entire banner is **one link** with one meaningful accessible name and visible focus, no nested anchor or competing clickable portrait. Provide at least a 44 CSS px touch target and avoid obscuring page navigation. A subtle wiggle must have a static `prefers-reduced-motion` fallback and stop when the document is hidden. Keep application controls outside the YouTube player rectangle and leave native YouTube controls unobscured.

Acceptance: exercise HPC -> Vote -> banner -> HPC and HPC -> Contact Congress -> banner -> HPC, separately on both pages; activate text, padding and portrait areas, plus keyboard Enter. Verify the distinct Red Dog -> Mall destination, page fit, focus, reduced-motion/visibility behavior, form/install controls, admission and return state. Reuse existing tests. Source, preview route/asset parity, actual phone navigation/playback and production deployment are separate gates. A saved direction or a working href alone is not completion.

Deferred, not part of this immediate return-link slice: the larger shared floating Red Dog and bottom FoundUps search dock across existing surfaces. Reuse current navigation/state/search owners and do not duplicate the dock. `https://play.foundups.com` is the intended public Mall entry with its existing access policy; **144 FoundUps is a product target, not a claimed current inventory**. The ordinary Mall's internal concierge keeps its existing semantics. No production deployment is authorized by this change.

## 5. AI Projection vs User Navigation

### 5.1 Separation of Concerns

**User controls**: Navigation within the current projection
**AI controls**: The projection itself (sort, filter, arrangement)

This means:
- User swipes to move through the field
- AI changes what the field looks like
- Swipe grammar remains stable regardless of projection

### 5.2 Field Scope API (Runtime)

The Mall field scope filters the catalog before projection.

| API | Purpose | Status |
|-----|---------|--------|
| `setFieldScope({ type, query })` | Generic scope setter | RUNTIME |
| `projectPersonalMall()` | Filter to creator === '012' | RUNTIME |
| `searchByCreator(query)` | Case-insensitive substring on creator/entity | RUNTIME |
| `filterByCategory(category)` | Exact category match | RUNTIME |
| `filterByTag(tag)` | Exact tag match in tags array | RUNTIME |
| `clearFieldScope()` | Reset to full catalog | RUNTIME |
| `getFieldScope()` | Get current scope | RUNTIME |

Scope types:
- `personal` — `creator === '012'`
- `creator` — substring match on creator/entity
- `category` — exact match (case-insensitive)
- `tag` — exact match in tags array

### 5.3 Projection Commands (AI-Controlled)

AI can reproject the Mall based on:
- "show FoundUps near me"
- "show only food category"
- "show highest activity"
- "show things my agent recommends"
- "show by newest"
- "show by my network"

### 5.4 Invariant

**AI projection changes tile placement, not navigation grammar.**

If user swipes down, they always move toward "nearer/more relevant" in the current projection, regardless of what projection is active.

---

## 6. Protected Mall Anchors

### 6.1 Always Visible

| Element | Zone | Reason |
|---------|------|--------|
| Avatar trigger | Top | Account access |
| Red Dog trigger | Bottom | Concierge/help access |
| FoundUp field | Middle | Core Mall function |

### 6.2 Always Functional

| Action | Binding | Reason |
|--------|---------|--------|
| Open account | Swipe-down from top | User identity access |
| Open concierge | Tap Red Dog | Help/recovery path |
| Enter FoundUp | Enter button (tile or fullscreen) | Core navigation |
| Close overlay | Escape | Universal escape |

### 6.3 Cannot Be Hidden or Disabled

- Account avatar trigger
- Red Dog trigger
- Escape key binding
- Close buttons on overlays
- Sign out action (within account plane)

---

## 7. Account and Red Dog Treatment

### 7.1 Account Plane

**Status**: Anchored personal surface
**Position**: Slides down from top
**Customizable**: Partially, in later phases
**Phase 1**: Fixed layout, fixed controls

Contents (fixed in phase 1):
- Identity block (avatar, name, handle)
- FoundUps grid (tiles linking to entries)
- Invites drawer (collapsible)
- Options (sign out)

### 7.2 Red Dog Concierge

**Status**: Anchored agent surface
**Position**: Slides up from bottom-right trigger
**Customizable**: Partially, in later phases
**Phase 1**: Fixed layout, fixed content

Contents (fixed in phase 1):
- Concierge header
- Member info
- Current context
- Navigation guide
- Readiness guide
- Sign out

---

## 8. Overlay Behavior

When an overlay is open (FoundUp view, account plane, concierge):

| Gesture | Overlay Action | Status |
|---------|----------------|--------|
| swipe-up | Close overlay | LOCKED |
| Escape | Close overlay | LOCKED |
| Scrim tap | Close overlay | LOCKED |
| Close button | Close overlay | LOCKED |

**LOCKED** applies to these overlay dismissal controls, including inside
FoundUps. A gesture owned by the active video uses section 14's planned
video-return preference before an outer overlay handler; it must not also
close that overlay or advance the queue. Escape, scrim and explicit Close
retain their independent recovery roles. This is a specified exception, not
evidence that the current runtime already arbitrates it.

---

## 9. Reset Behaviors

### 9.1 Mall-Level Resets

| Reset | Trigger | Effect |
|-------|---------|--------|
| Reset projection | AI command / voice | Return to default sort |
| Center on me | AI command / voice | Return to self-proximity view |
| Reset navigation | Escape (no overlay) | Return to home position |

### 9.2 URL Reset

```
/member/?reset=mall
```

Clears any cached Mall state and returns to default projection.

---

## 10. What This Contract Does NOT Cover

Out of scope for this document:
- FoundUp interior layout (see SoftProto guardrails)
- FoundUp interior gesture overrides (see SoftProto guardrails)
- Edit mode behavior (SoftProto only, not Mall)
- AI command layer implementation (SoftProto architecture)
- Persistence schema for user preferences (SoftProto architecture)

---

## 11. Summary

| Surface | Fixed | SoftProto-Enabled |
|---------|-------|-------------------|
| Gateway | YES | NO |
| Mall navigation | YES | NO |
| Mall anchors (top/bottom) | YES | NO |
| Account plane | YES (phase 1) | Later |
| Red Dog concierge | YES (phase 1) | Later |
| FoundUp interior | NO | YES |

**The Mall is a map. Maps have coordinates. Users navigate maps. They do not edit the map's coordinate system.**

---

*Contract complete. SoftProto begins inside FoundUp interiors, not in the Mall shell.*


## 12. Responsive category-row projection — 2026-10-18

The default browse projection is vertically stacked category groups with horizontal
tracks. Vertical movement visits another group; horizontal movement stays within
that group. Category sorting alone does not establish a relevance/distance score:
those earlier axis descriptions remain projection intent until such data exists.

Visible card count follows available space, not a fixed 3x2 grid or fixed number
of rows. Existing density presets select an explicit grid projection. Pinch-out
opens the selected FoundUp's videos; pinch-in returns to the rows. Independent
row offsets restore locally, using category keys and original catalog indexes.

All FoundUps reuse this grammar and the catalog search/presentation APIs. A future
housing projection may group by location through a separately declared adapter;
this slice groups by catalog category only. No unseen listings, location hierarchy,
personalized ranking or voice runtime is claimed.

## 13. Fractal work navigation

**TARGET / SPECIFIED, reconciled 2026-11-19.** This section defines acceptance
for the shared graph. It does not turn existing category-row or video-lane
handlers into an implemented general graph renderer. The
[master architecture](FOUNDUPS_MASTER_ARCHITECTURE.md#fractal-views-of-the-same-work)
owns entity identity, relationships, evidence and the current implementation
boundary.

### 13.1 Selection and drill-down

Tap, keyboard activation and a supported RedDog navigation request resolve
the same permitted stable tile ID. A container reveals its children; an
actionable leaf opens its real artifact or entrypoint. A declared gap opens
its expected contract and evidence status, not a fabricated working tool.
The field remains usable in 2D, with keyboard controls and reduced motion.
The 3D view is an alternative projection; spatial animation is not evidence
that a component or worker ran. Voice is optional navigation input and cannot
be the only way to select, return or recover.

Search, sorting and lens changes retain stable IDs. A shared component can
appear in several views without copying it or changing its primary owner.
Reuse existing search, state-restoration and media owners. A graph view must
not silently replace the current catalog if its graph is unavailable or invalid.
Qualify the existing fallback behavior when the graph client is recovered.

### 13.2 Caller restoration

Record the actual caller, lens, selected tile, query and recoverable viewport
and media state when entering a child or following a related-component edge.
From HPC, entering AutoPost and pressing Back restores HPC and its selection;
AutoPost's primary containment parent does not replace the caller. Direct
entry without session history uses visible containment ancestors.

Revalidate access on restoration, direct entry, search and context projection.
If a caller has become inaccessible, return to a permitted ancestor or overview
without leaking its private title, path or receipt. Retain a safe return path
when evidence is missing. Preserve playback state through its existing owner
where supported; real provider playback and autoplay recovery require separate
live acceptance from DOM or mocked-media tests.

### 13.3 Work and revision binding

A request binds the selected entity, graph/projection revision and, where
relevant, the work reference and exact artifact revision or base-plus-overlay
digest. Source revision is not interchangeable with graph revision. An
unavailable pinned file must not silently open the current `main` file as
though it were the same evidence.

Selecting a builder with a fresh, permitted work-to-tile association opens the
referenced component. “What is this builder changing?” uses that same binding.
Multiple builders may work on one component, and one work item may span several
components. A builder label or animation cannot supply a missing mapping.
Simulated, stale, ambiguous, unmapped and restricted evidence retains its
status in the permitted view.

The first Tools path is
`Tools → Benchmark → harness/evaluator → module or model/scaffold configuration → run receipt → pinned test/source → Back`.
Follow only supported relationships with real IDs. Show a missing adapter,
receipt or source binding as a gap. Rendering the path does not establish
that its represented tool ran.

### 13.4 Co-building and acceptance

Selection, conversation and camera movement grant no mutation or execution
authority. A separately approved graph-content change uses the existing
authenticated server owner, an expected graph revision, validated containment
and typed references, and an attributable receipt. A stale write is rejected
rather than overwriting another worker. Adding a proposed tile or socket does
not implement it or promote its evidence status.

Keep public and architect projections separate through navigation, search,
history and agent context. The [Mall roadmap](../pfmall/ROADMAP.md#fractal-tile-graph-and-agent-work-navigation)
owns the bounded acceptance sequence. The
[documentation audit](https://github.com/FOUNDUPS/Foundups-Agent/blob/dc7c34aa6444aa1fc37de1217f99f0e75e4d2f0b/docs/audits/architecture/PFMALL_FRACTAL_DOCUMENTATION_AUDIT_20261119.md)
records the reported local navigation test and its unproven live-media,
voice and Simulator boundaries.

## 14. Shared Search Dock and video preferences

2026-11-22 candidate update: the shared #2439 continuation implements clamped
floating drag/frame targets, a video-height tuck/restore rail, independent
validated options and menu-based accessible actions. Outward pinch now defaults
to WikiTube by 012's clarification. Return defaults remain open; an unselected
return choice preserves its existing behavior. Dock camera delegates to AutoPost
with a bounded caller return. Dock Red Dog stays in-page when unavailable; no
public backend, STT or language model is thereby activated. Final source/preview
and physical-device qualification remain separate from this candidate.

**PFDOCK-20261121 / CHANGES_POC_ACCEPTANCE / SPECIFIED_NOT_IMPLEMENTED.**
012's 2026-11-21 correction applies to **all FoundUps and every fractal view**,
including `play.foundups.com`, HPC, nested FoundUp interiors, the tile field,
Floating, WikiTube and Fullscreen. HPC is the first qualification surface for
the same shared behavior. It does not own a separate dock or settings fork.
Existing independent sites need their owner's shared-shell integration before
claiming parity; this contract does not change their deployments or admission.

This supersedes HPC-only dock scope, a forced WikiTube intermediate and the
older fixed video swipe-up-to-next rule as next-iteration acceptance. Earlier
runtime tables remain historical implementation evidence until the shared
owner is changed and qualified. Preserve field navigation, non-video actions,
modal/account recovery and the existing fractal caller/identity rules.

### 14.1 One shell-owned dock and menu order

Keep one floating dock anchored to the visible app viewport bottom, below
the scrolling tiles/queue, with safe-area and keyboard clearance. Retain
query, selection, focus, preferences and caller when changing FoundUp, depth
or media presentation. Focused input, dictation and an open menu pin the dock
visible. No duplicate visible/focusable search bar or new dock per skin.

The `+` opens upward. Its top-level reading order is:

1. **AI / Browse AI**: the model list and current availability/selection.
2. **Video**: player behavior settings, directly reachable from the same menu.
3. Relevant existing discovery/filter actions, then secondary Tools/About.

Use a compact expandable AI list so it does not push Video out of thumb reach.
Do not bury either entry behind About or unrelated placeholders. Offer only
real candidates compatible with the running browser; show download size,
require deliberate selection and confirmation, and provide Cancel/Unload.
Keep startup light, with no automatic model download, page reload or hosted
fallback. An unavailable list says so. The v26 41-byte WASM arithmetic probe
is a compatibility fixture, not an AI model or an approved model inventory.
The existing small pinned WASM model benchmark on physical iPhone 11 Safari
and installed PWA remains required before a model is qualified there.

The dock `+` opens settings/tools. The grid's trailing `+` contributes the
active element type (initially Video, under existing editor authorization).
Swipe-up on the designated element-type selector changes element type;
ordinary grid swipes retain their scrolling/navigation owner. Video-surface
swipe-up uses the video-return setting below. Neither grants contribution, agent
execution, member access or access to another FoundUp's protected context.

### 14.2 Presentation and independently selectable behaviors

**Mall** means the originating tile field, with its FoundUp/fractal context
and scroll position. **Floating** is the shared player over that field.
**WikiTube** is the main-video-and-queue presentation. **Fullscreen** is the
requested immersive destination, subject to the mechanism boundary in 14.4.

| Interaction / Video setting | Required choices and behavior | Decision boundary |
| --- | --- | --- |
| Deliberate video-tile activation from the Mall/FoundUp field (tap or Enter/Space) | **Floating / WikiTube / Fullscreen**. Selection loads/plays the chosen clip in that presentation without a compulsory WikiTube stop. | **Floating is the confirmed default.** Field selection is distinct from queue thumbnails, an app-frame action and taps inside provider controls. |
| Pinch outward to expand the active video | WikiTube or direct Fullscreen, allowing Floating to skip WikiTube. WikiTube can expand to Fullscreen. | WikiTube is the default confirmed by 012 on 2026-11-22; direct Fullscreen remains selectable. |
| Pinch inward from Fullscreen | Return to **WikiTube / Mall tiles** according to its own preference. | Do not bind this to the swipe-up preference; initial return default is unresolved. |
| Swipe up on the active video | Return to **WikiTube / Mall tiles** according to a separate preference. | This changes the older video swipe-up-to-next acceptance. It must not also advance the queue or trigger grid/type navigation. Initial return default is unresolved. |
| Rotate an active Floating video portrait to landscape | Enter the supported fullscreen presentation; portrait rotation restores the prior Floating presentation. | Required behavior. Track whether rotation caused expansion; a later deliberate view selection takes precedence over automatic restoration. |
| Swipe right on the Floating player | Park/hide it with a visible restore action and supported leftward restore gesture; preserve the selected clip and browse context. | Fully hidden YouTube playback pauses. Do not restart a deliberate pause on restoration. |
| Autoplay and parked-player selection | Retain autoplay/next-clip and reveal-versus-keep-parked preferences in Video. | Preserve their existing qualified behavior; this decision does not guarantee audible startup or change their defaults. |
| Rotation lock | Possible opt-in lock / stay-landscape behavior. | **OPEN IDEA**, not an approved control, default, or implemented capability. |

Queue-thumbnail selection and automatic advancement change the clip within
the active presentation; they do not reapply the field-entry default or force
Floating. Preserve the separately selected parked-player reveal behavior.

Use one validated preference owner and schema across consumers. Reuse the
existing `mall-state-restore.js` path, extending/migrating its v26
`pfmall_video_options_v1` data. A missing **tile-tap** preference initializes to
Floating; the old `frameDestination: 'wikitube'` describes a frame action and
must not silently become a tile preference. Validate independent choices,
ignore invalid values, and preserve valid existing preferences. Do not turn
unresolved return defaults or the rotation-lock idea into approved decisions.
Local storage is origin-local: common behavior/schema across HPC and Play
does not itself synchronize saved choices between their hostnames. Any future
cross-origin preference sync needs an explicit existing authenticated owner.

### 14.3 Transition ownership and continuity

Extend the existing tile-selection, player, dock and state owners. One action
produces one transition. Scope gestures to their actual surface and active
mode; keyboard, provider controls, modal input and ordinary page scroll must
not be captured by competing global listeners. Keep a visible single-pointer
and keyboard alternative for each application gesture and preserve page zoom.
WikiTube next/previous and continuous queues remain usable through the queue
and their existing explicit actions when swipe-up is assigned to return.

Presentation changes keep the same active provider instance, clip, permitted
queue, observed playback position, captions, zoom, query, scroll and focus.
Keep native sound/fullscreen controls and compact blocked-play/resume recovery.
Move app settings into the dock, remove redundant app Back/title/expand noise
and the identified app-owned diagonal expand arrow, while retaining one clear
accessible navigation path. Do not remove or mask provider controls.

An explicit final Close is distinct from a reversible presentation change.
Return to Mall restores the actual caller's tiles; it does not discard state
or navigate to an unrelated FoundUp. Retaining state never authorizes invisible
playback: pause when fully hidden and restore without overriding deliberate
pause or provider policy. Source/graph identity and admission remain separate
from player presentation and saved preferences.

### 14.4 Fullscreen, gesture and orientation capability boundary

Keep **app Full Video** (expanded viewport), browser DOM fullscreen and
YouTube/iOS native video fullscreen distinct in implementation and evidence.
The [YouTube IFrame API](https://developers.google.com/youtube/iframe_api_reference)
has no documented native-fullscreen trigger; its
[fs parameter](https://developers.google.com/youtube/player_parameters#fs)
controls the native button. Keep that control available. A viewport expansion
alone is not a native-fullscreen pass.

The [Fullscreen Standard](https://fullscreen.spec.whatwg.org/#api) permits a
request with transient activation or a user-generated orientation change;
actual device support and permission still need qualification. Detect support,
handle the returned outcome and observe the actual presentation. If a requested
native path is unavailable, retain the provider control and an honestly labeled
app-expansion alternative; do not claim the requested native path passed.

The app cannot assume it receives pinch/swipe events inside a cross-origin
YouTube player. Recognize app gestures on its owned surround or handle outside
provider controls, without an intercepting overlay. Record that surface in
acceptance; do not silently substitute surround evidence for an untested
gesture inside the video. Follow the provider's
[overlay requirements](https://developers.google.com/youtube/terms/required-minimum-functionality#overlays-and-frames)
and provide [simple pointer alternatives](https://www.w3.org/WAI/WCAG22/Understanding/pointer-gestures.html).

Native fullscreen may temporarily own the entire screen. Preserve dock state
and restore the one dock on exit; do not overlay it on native player controls.
Apply the saved return choice for a recognized initiating action when its exit
is observable; an exit event alone does not identify pinch-in, swipe-up, native
Done, Escape or rotation. Reading device
orientation does not establish [orientation-lock support](https://www.w3.org/TR/screen-orientation/),
and keyboard/viewport resizing must not be mistaken for physical rotation.

### 14.5 Qualification and existing implementation lane

At inspection, [v26 PR #2439](https://github.com/FOUNDUPS/Foundups-Agent/pull/2439)
head `5be6f3b7bd9eb3c24c39210e74fada8e773a97c7` is an unmerged draft.
Its menu places AI last; `frameDestination` allows WikiTube/app Full Video,
tile selection does not read that setting, pinch-out opens WikiTube, and
WikiTube swipe-up advances the queue. Its orientation listener adjusts geometry.
This is partial implementation evidence, not the acceptance defined above.
Reconcile in that existing owner before runtime changes; do not merge its
unrelated history or overwrite an active worktree for this documentation task.

Acceptance must cover fresh/default and saved/invalid preferences, all three
tile destinations, direct fullscreen expansion, both pinch-in return choices,
both video-swipe-up return choices independently, right tuck/restore, and
landscape/portrait restoration with later deliberate navigation. Test ordinary
Play, HPC and at least one other FoundUp plus nested fractal entry/Back; keep
public/member/editor boundaries and caller context intact. Include keyboard,
reduced motion, normal page zoom, safe areas, open keyboard/menu and no duplicate
focusable dock or media instance.

Physical iPhone 11 Safari and installed PWA, other supported phone paths and
desktop must record requested destination, actual fullscreen mechanism,
gesture surface, queue/time continuity and observed return. Browser emulation
or the WASM fixture alone cannot qualify these provider/device behaviors.
The [Mall roadmap](../pfmall/ROADMAP.md) and [HPC roadmap](../hpc/ROADMAP.md)
own sequencing. Documentation, source merge, preview qualification and
production release retain separate receipts.
