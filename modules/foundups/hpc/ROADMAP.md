# HPC roadmap

| Stage | Status | Dependencies | Acceptance criteria and evidence |
| --- | --- | --- | --- |
| 0 · Genesis | Existing implementation | WSP 109, Vote ID, registry and manifest validators | Eight intake artifacts, valid genesis envelope, canonical `hpc` registry and `/f/hpc` namespace. Evidence in [intake](docs/intake/INTAKE_SOURCE.md) and [ModLog](ModLog.md). |
| 1 · PoC | Desktop theater, search, phone dock and in-place tile playback merged in #2359, #2364, #2366 and #2370. Acceptance remains open. | Shared Mall shell, reviewed Move2Japan metadata, Vote's manual contact page | Eight-Short collection and H1 desktop, phone and entry-route checks. Physical iPhone and live release verification remain open. [Shared incident](../pfmall/MEDIA_PLAYBACK_INCIDENT_HPC.md) retains provider evidence. |
| 2 · Prototype | Specified; follows accepted PoC layout/playback | PoC acceptance, provenance and rights policy, shared preference owner and privacy review | Nomination, duplicate/source review, moderation, discoverable filters, persistent seven-level preferences, edit/clear, and abuse tests. Admitted speech/model and AutoPost integrations use shared owners. Accepted events remain separate from evidence and economics. |
| 3 · MVP | Specified | Qualified moderation and escalation, independent Voice admission, preference aggregation and governance review | Moderated community submissions, working consented Voice handoff and recovery, reproducible aggregate reports and governance interfaces with correction and appeal. |
| 4 · Federation | Specified | WSP 103/104 interoperability, verified Vote/Voice interfaces and tenant isolation | Cross-FoundUp discovery, versioned context with consent, provenance and access scopes preserved in conformance tests. |

## Shared preferences and evidence

The Mall owns interaction design for video tiles. The existing player implements a browser-local bookmark and sharing. The seven-level press-and-hold preference control is specified in the Vote/Voice discussion and [EduIT interaction notes](../eduit/docs/EPISODE_TILE_CONTROLS.md). The audited Mall has no selector, approved scale, persistent preference event or aggregation integration.

Prototype acceptance requires a shared, visible preference control with press-and-hold and accessible keyboard/button access to the same signed scale. A participant can revise or clear a rating. Absence, neutral and negative values are distinct. Confirm the labels and endpoints with the interaction owner. Define event identity, source video identity, consent and retention, edit/delete semantics, deduplication, anti-bot and coordinated-abuse tests, aggregate coverage and uncertainty before collecting preferences.

[WSP 29 CABR](../../../WSP_framework/src/WSP_29_CABR_Engine.md) owns validation, verification and valuation. Preference can inform discovery after consent and abuse checks. Independent source records and review govern credibility and factual verification. Any future CABR mapping requires a reviewed event/evidence contract and independent tests. No issuance, rewards or governance authority comes from PoC viewing or saving.

## H1 — Responsive WikiTube-style discovery and shared thumb dock (specified; 012 request 2026-11-11)

### H1A · Current decision and shared ownership

012 clarified after PR #2357 that **desktop WikiTube TV mode and phone grid mode are both PoC requirements**, not two applications or a later desktop-only product. The shell, catalog, tile identities, player, queue and state restoration remain owned by Play FoundUps Mall. HPC supplies its existing scoped content and branding. A passing phone layout cannot close desktop acceptance.

Before each build, reconcile this roadmap with the [shared Mall roadmap](../pfmall/ROADMAP.md), current runtime/contracts, related PRs and the latest request. Record FITS_POC, CHANGES_POC_ACCEPTANCE, LATER_STAGE or CONFLICT in the owning work record. Update affected documentation before or alongside implementation. Do not silently replace an earlier contract, rescope tests to pass, or recreate HPC genesis.

Use the existing [strategic diligence skill](../../ai_intelligence/ai_overseer/skillz/strategic_diligence_gate/SKILLz.md), rather than creating another build skill. WSP 15 scores priority; WSP 30 defines staged build orchestration; WSP 97 governs evidence, execution and completion.

### H1B · PoC acceptance: two responsive views of one Mall

| Surface | Required behavior | Acceptance boundary |
| --- | --- | --- |
| PC / monitor | Centered main video, then a horizontal thumbnail queue, then **one viewport-bottom floating search dock below the thumbnails**. The dock remains reachable while content scrolls; the main player is not forced browser fullscreen. | Desktop screenshots and browser interaction tests must show this order and bottom anchoring; oversized three-column posters, search above the queue, or a duplicate dock do not satisfy it. See H1F. |
| Desktop startup / queue | Request playback of the first eligible clip on entry, then advance through the queue. Preserve one active player and deliberate sound controls. | Test actual provider state and advancing time. Where the browser blocks startup, show a truthful user-activation recovery; never claim guaranteed audible autoplay. No duplicate or hidden players. |
| Search | Reuse one floating bottom dock: left plus/options, editable scoped search, dictation mic, and right Red Dog action. Typing filters the scoped desktop queue; submit plays the next match or first available match. Phone search submits its grid filter. | Test exactly one visible and focusable search surface per active view, preserved query/selection, safe areas, keyboard clearance, no results, and return state. Dictation and Red Dog retain their actual capabilities; placement does not admit resident speech. |
| Phone | Compact portrait grid below one shared, top-anchored floating player by default. One deliberate tile tap requests playback using the H1H destination preference; the grid scrolls independently beneath Floating mode. Preserve video identity, WikiTube transitions and queue, query, scroll, focus and close/back recovery. | Verify one iframe/audio session, advancing media time, provider minimum size, unobscured provider controls, repeated selection, rotation and return. Provide truthful recovery when autoplay or the provider blocks playback; one tap is not a bypass guarantee. |
| Breakpoint / rotation | Change presentation without duplicating the media session or losing video identity, queue, query and browsing position. | Test desktop, phone portrait/landscape, resizing and keyboard access independently. Do not classify all large tablets by pointer alone without testing. |
| Entry and membership | Guests browse on `hpc.foundups.com`. `foundups.com/members` leads to the existing member gate. Admitted members can select HPC from the Mall or return to the same selection after sign-in. | Guest, uninvited and admitted browser cases. The `/f/hpc` landing links to the dedicated host. `/f/hpc/app` retains its protected handoff. |
| Shared-regression guard | Preserve ordinary Mall channel expansion, other FoundUp projections, guest/member boundaries, provider diagnostics, save/history and return navigation. | Reuse the existing tests and fixtures for the shared grid, player and account boot. |

The November 11 request initially superseded hidden-search wording for **HPC-scoped bottom search**. **H1H / PFDOCK-20261121 now supersedes that scope restriction: the same dock and player preferences belong to all FoundUps and their fractal views.** The master-Mall logo link and independent-site disclosure remain. The 2026-11-16 navigation matrix below defines portrait/HPC and Red Dog/Mall destinations. H1F supersedes the previous search-above-thumbnails order; H1H adds the latest shared behavior acceptance. These are requirements, not evidence that production already renders them.

### H1C · Evidence and recovery before implementation

- Revalidate current main, related heads and deployed assets separately. PR #2357 introduced a hard-coded three-column scoped grid and `openScopedVideo()` inserts `.mall-inline-player-slot` after a calculated row. The reported desktop result is a regression candidate, not a fully reproduced cause of every playback failure.
- The original #2359 draft changed desktop density alone. Browser reproduction showed that six CSS columns still used three-column JavaScript row placement. #2359 and #2364 restored the shared desktop theater and search. The 2026-11-12 selected-tile phone decision is historical: 012's 2026-11-16 top-anchored player requirement explicitly supersedes that placement acceptance. The inspected runtime still needs reconciliation; documentation is not an implemented player change.
- Retrieve actual WikiTube TV / WikiTubeTV source and history through available repositories or the PC before copying/rebuilding. Earlier search found no direct current integration; this is a retrieval gap, not proof that source does not exist. No historical deployment URL is accepted without source evidence.
- Reuse `public/member/` field, player, query and state APIs. Investigate the existing fullscreen queue/theater composition before introducing markup. Keep provider errors, unavailable media, autoplay blocking and bot/session challenges distinct in the [existing incident](../pfmall/MEDIA_PLAYBACK_INCIDENT_HPC.md).
- A full revert of #2357 would also discard catalog and diagnostic work. Prefer the smallest validated responsive correction; retain a known-base recovery path and compare its complete diff before any authorized revert.

### H1D · Three-question allocation and build order

The canonical wording is in **WSP 97 section 1.2.1**:

1. **Do I need it?** -> Importance and Impact.
2. **Can I afford it?** -> Complexity, compute, time, and verification cost.
3. **Can I live without it now?** -> Deferability and current blockers.

These questions are the plain-language projection of WSP 15, not another scoring system. Deferability 5 means cannot defer; 1 means highly deferrable. Scores below are planning allocations, not authenticated runtime admission or successful execution.

| Work item | C | I | D | Impact | Total / priority | Need / affordability / deferral |
| --- | --- | --- | --- | --- | --- | --- |
| Roadmap and existing-skill reconciliation | 2 | 4 | 4 | 4 | 14 / P1 | Needed to prevent repeated drift; bounded documentation and source checks are affordable; complete before another layout mutation. |
| Shared PC theater + preserved phone-grid recovery | 3 | 5 | 5 | 4 | 17 / P0 | Required to demonstrate the PoC; constrain scope to existing owners plus dual-view tests; cannot defer the regression behind new features. |
| Scoped bottom search and queue update | 2 | 4 | 4 | 3 | 13 / P1 | Part of the agreed PoC; reuse loaded catalog/query APIs; sequence after stable playback/layout rather than a new global engine. |
| Member entry and public host split | 3 | 5 | 4 | 4 | 16 / P0 | Required by 012's 2026-11-13 route clarification. Reuse the existing gate, bounded return record and browser tests. Verify with an invited account before release. |

Build one validated layer at a time: reconcile -> repair responsive playback -> prove PC and phone -> add scoped search -> verify shared regressions -> qualified merge and release. Prototype work must not displace this PoC acceptance.

### H1E · Retained later-stage requirements

FITS_POC for the 012 phone follow-up on 2026-11-12. HPC supplies the install
name and the portrait cropped from 012's supplied satire artwork. The shared
Mall supplies the phone header and thumb dock. The dock gives direct access to
scoped search, a separate device dictation input, an upward options sheet and
the public Red Dog briefing in the inspected runtime. The November 16
adjacent-surface navigation requirement supplies a distinct Mall return icon;
retain internal Mall concierge behavior. Check iPhone standalone installation
and keyboard dictation against a hosted build before accepting that device.

Prototype work includes an admitted device-compatible agent selector, Red
Dog press-and-hold speech, and camera handoff to AutoPost. Reuse existing
identity, admission and capture owners. Verify consent, cancellation,
supported device models and return context before exposing actions.
H1H now specifies shared AI-list placement in the next iteration; actual model
qualification and resident-agent authority remain separate acceptance gates.
Seven-level preferences, community nominations, comics/story panels and
whole-Mall discovery keep their existing stages.

### H1F · Single floating bottom dock — 012 clarification, 2026-11-18

**Scope update, 2026-11-21:** H1H and the shared navigation contract now own
cross-FoundUp scope and configurable player behavior. The layout and continuity
requirements below remain; HPC-first qualification does not mean HPC-only design.

**CHANGES_POC_ACCEPTANCE / SPECIFIED_NOT_IMPLEMENTED by this documentation slice.**
The requested composition is **main video -> video thumbnails/queue -> one
floating bottom dock**. Floating means anchored to the visible app viewport,
with a small edge gap and safe-area clearance, not a search row that scrolls
away or sits above the videos. Browse and WikiTube viewer reuse the same shared
dock owner; switching view transfers query, focus and selection without leaving
two visible or keyboard-focusable search bars.

- Put `+` on the left, scoped search in the middle, and microphone/Red Dog on
  the right in the same floating item. Reuse current options, dictation and dog
  behavior; do not turn a display change into a claim of resident-agent execution.
- Keep the dock reachable during browsing and playback. While focused, editing,
  dictating or using options, it must not auto-hide. Longer input grows upward;
  its controls remain at the bottom. Reconcile any prior scroll-hide behavior
  through the existing controller rather than adding competing timers.
- When the phone keyboard opens, keep the dock and its active input above it;
  restore the normal safe-area position on dismissal. Preserve accessible touch
  targets, keyboard navigation, reduced motion and usable portrait/landscape views.
- Reserve scroll clearance for the dock so the last tile and its title can be
  brought fully into view. Do not cover native player controls or reduce the
  active provider below its required visible dimensions. The plus menu opens
  upward within the available viewport. Choose layering in the existing shell,
  below modal dialogs, rather than an arbitrary global z-index override.
- Extend existing dock/browser fixtures: one visible dock, bottom anchoring at
  top/middle/end of scroll, thumbnails above it, keyboard open/close, expanded
  input, option dismissal, rotation, Back and preserved one-player continuity.
  Desktop and physical-iPhone acceptance remain separate from emulation.

HPC is the first preview consumer of this shared refinement, followed by
qualified Mall promotion; no standalone HPC runtime or security bypass is
introduced. Preserve the separately owned top-anchored phone-player work on
`feat/hpc-floating-wikitube-v20`; this dock correction must not revert it to an
older row-player contract during reconciliation. Refresh that owner and current
main before implementation. Keep #2405 diagnostics and #2411 Vote navigation
separate. This documentation changes neither their branches nor deployed UI.

### H1G · iPhone 12 preview feedback — 012, 2026-11-19

**CHANGES_POC_ACCEPTANCE / SPECIFIED_NOT_IMPLEMENTED by this documentation
slice.** 012 opened the review preview on an iPhone 12 and supplied
`IMG_0515.jpeg`: the app header wraps onto two lines, visible Member Portal
text occupies the second row, filter pills consume two more rows, and three
narrow portrait tiles leave too little usable browsing space. Opening the
preview is confirmed by 012; phone layout acceptance remains open.

The reviewed [Firebase preview](https://foundupscom--play-v24-iphone-3rrzxm0r.web.app/member/)
shows **Build v24** inside its existing `+` options dialog in this audit
browser. 012 called the opened test v21. Record these observations separately:
neither a channel name nor this browser's build label proves which assets or
service worker the physical phone loaded.

#### Ordered fixes in the existing shared Mall owner

| Priority | Required change | Acceptance |
| --- | --- | --- |
| 1 | Keep the ordinary/public Mall phone header on **one compact line**: FoundUPS identity and the existing compact account action. Remove visible **Member Portal** wording from that header. | No wrap, clipping or horizontal page scroll at 390 CSS px and narrower supported widths. Keep an accessible account/sign-in action and its existing destination. Preserve HPC's distinct banner/Voice and selected-player controls. |
| 2 | Move **All, A–Z, Readiness, Category, Videos, Apps, Shop and other applicable discovery controls** from above the grid into the existing bottom `+` options sheet. | No filter rows occupy the resting browsing canvas. The same controls, selection and handlers remain available in `+`; scope-inapplicable controls stay hidden. Preserve query, source/category selection, order, Back and scroll state. |
| 3 | Make the tiles and active video fit the phone's **available app viewport**, with useful content space recovered from the header/filter rows. | Readable tile content, no horizontal overflow, media contained within the viewport, provider controls unobscured and the final tile scrollable clear of the dock. Keep density policy, CSS, persisted state and row/player placement consistent. Do not treat three columns as an unconditional acceptance rule; qualify any density change with the existing owner. |
| 4 | Preserve **one floating bottom dock** with `+`, search, dictation and Red Dog. Retain the existing AutoPost camera/photos entry. | Upward menu/input growth, safe-area and keyboard clearance, focus/Escape/backdrop recovery, and one player/search surface through browsing, selection, rotation and return. H1F remains in force. |

Served-source inspection confirms `public/member/css/member.css`'s mobile
`.mall-header` column rule (at or below 720 CSS px) and `mountOpenMall()`'s visible
portal label are present in this preview. Its phone density remains `3x4` /
`3x5`; the v24 overlay has not corrected these layout behaviors. Extend
`createMemberDock()` and its
`.mall-member-search-options` dialog in `mall-video-projection.js`.
Move/reuse `#mallProjection` and the existing
`mall-tile-field.js` projection/source handlers; do not create another
filter engine, shell or dock. A CSS-only column change must not contradict the
field's density policy or row calculations.

Use the existing full-shell browser cases, including
`public/member/tests/mall_scoped_video_browser.py`, for the real header,
options sheet, dock and player. The tile-only responsive fixture cannot prove
header or dock acceptance. Cover 390 x 844 CSS px, a narrower supported width,
rotation and keyboard; then verify the same candidate on the physical iPhone
in its browser view. Retain the separate PC main-video -> thumbnails -> bottom
dock check and single-player/query/return regression checks.

#### Deferred AutoPost follow-up

**LATER_STAGE / TODO**, as 012 explicitly requested: add an AutoPost
bottom-right icon near the camera-flip control and a bottom search surface
using the shared interaction contract. The icon's exact action is not fully
specified by this feedback; settle it in the existing AutoPost capture owner
before wiring a new behavior. Preserve current capture, permissions and return
context. Use the existing [capture handoff](../pfmall/AUTOPOST_ITEM_CAPTURE_HANDOFF.md)
and external `FOUNDUPS/autopost` roadmap. This is not an AutoPost
implementation or a reason to delay the immediate Mall layout correction.

#### Source and completion boundary

Main inspected: `7432d31e5a68544d2bbab6715f02f64b0b5b6f85`.
Pushed native branch `feat/hpc-floating-wikitube-v20` remains
`75c838b6eab19807487ee02c4b2f9367e580547e` / Build v23. The served
preview has v24 markers, worker cache `pfmall-member-v24`, and Shop filtering
from a later overlay. Its [served deployment receipt](https://foundupscom--play-v24-iphone-3rrzxm0r.web.app/member/playback-probe/deployment.json)
reports that base plus overlay digest
`92e1e9338a8256328520546c89cc816563aee25f81b88214ade2fd8c87b67946`,
repair handoff `RD-MOSH-20261117-PHONE404-04`, and
`hosting_version: unverified`. This audit has not verified the complete
patch digest or immutable hosting version. Preserve the existing native
implementation owner and unpushed overlay. Before runtime mutation, reconcile
the owner's exact overlay and deployment configuration with these served
assets; then apply this correction there and publish an updated review preview.
Do not overwrite newer preview work with the older remote branch.

WSP 15 allocation for this bounded layout slice: C=2, I=4, D=4, Impact=4,
total 14/P1, subject to owner verification cost. Needed for phone PoC
acceptance; affordable by extending existing controls; cannot defer before
phone acceptance. AutoPost remains deferred. Documentation, source merge,
preview publication, physical-device acceptance and production launch require
distinct receipts. 012's preview review precedes production launch; this
feedback is not production approval.

### H1H · Shared dock and configurable video behavior — 2026-11-21

**PFDOCK-20261121 / CHANGES_POC_ACCEPTANCE / SPECIFIED_NOT_IMPLEMENTED.**
012's latest correction makes the floating Search Dock a shared FoundUps
component across the Mall, every FoundUp and their fractal views, including
`https://play.foundups.com`. HPC is the first qualification surface, not a
separate owner or the limit of the requirement. The authoritative behavior
matrix is [shared navigation contract section 14](../docs/PFMALL_MALL_NAVIGATION_CONTRACT.md#14-shared-search-dock-and-video-preferences).
This supersedes HPC-only wording, the formerly deferred shared-dock scope,
forced WikiTube entry and fixed player up/down behavior where they conflict.
The prior [Mosh Pit](https://docs.google.com/document/d/1a4TqtdnCKiQMx36hw2uObQ0YX3XGw66bDY09_vBWEm8/edit)
entry `HPC-SEARCH-DOCK-PILOT-20261121` is the pilot history; this correction
extends its scope and finalizes the default tile-tap behavior.

- The thumb-accessible `+` menu shows the **AI list first**, then a visible
  top-level **Video** entry, followed by functional actions for the current
  scope. Video settings must not require finding an About or unrelated tool
  submenu. The grid's trailing contribution `+` remains a separate control.
- Video tile tap offers **Floating / WikiTube / Fullscreen**, with **Floating
  the confirmed default**. A selected Fullscreen action can skip WikiTube.
- Configure expansion and return independently: pinch-out goes to WikiTube
  or directly Fullscreen; pinch-in from Fullscreen returns to WikiTube or
  **Mall (tiles)**; swipe-up on the video returns to WikiTube or Mall. Pinch
  and swipe return defaults are not finalized. The designated element-type
  selector, ordinary grid/queue scrolling and modal dismissal retain their
  own contexts; do not turn every upward grid swipe into type selection.
- Rotate an active Floating player to landscape Fullscreen and restore
  Floating on return to portrait. Explicit intervening navigation or mode
  selection takes precedence over an automatic restore. **Rotation lock is
  an open design idea**, not an approved setting or implementation gate.
- Retain right-swipe tuck and accessible restore, compact app-owned controls,
  native provider controls/fullscreen, useful blocked-play recovery and one
  player. Keep queue, clip, playback position, captions, zoom, query, scroll
  and focus across presentation changes. Fully hidden YouTube playback pauses.
  Native fullscreen capability and app Full Video remain distinct, as defined
  in the shared contract; do not mask provider controls to simulate either.

Local settings are available while signed out and do not grant contribution,
membership, editor or agent execution authority. Share one preference schema
and defaults across FoundUps; origin-local browser storage alone does not
synchronize HPC and Play subdomains. The AI list must reflect supported,
qualified choices, show download size and require deliberate selection and
confirmation. Preserve lightweight startup, Cancel/Unload and truthful absence
of eligible models; no automatic model download or hosted fallback.

**Implementation evidence:** [v26 PR #2439](https://github.com/FOUNDUPS/Foundups-Agent/pull/2439)
was inspected at `5be6f3b7bd9eb3c24c39210e74fada8e773a97c7`, open draft and
unmerged. It has only WikiTube/app Full Video frame options, a shared collapse
choice, fixed pinch/queue gestures and a 41-byte WASM compatibility fixture,
not an AI model. It does not satisfy this new matrix or prove physical-device
acceptance. Reconcile the latest main and that existing implementation lane;
do not overwrite its newer work or turn this documentation edit into a release.

**Allocation and acceptance:** documentation reconciliation is C2, I4, D4,
Impact4 = **14/P1** under WSP 15: needed to prevent repeat drift, affordable as
a bounded update to existing owners, and required before the next behavior
change. Reassess implementation and device-verification cost in the shared
owner. Qualify each option and same-player transition in HPC first, then the
ordinary/public Mall and another FoundUp/fractal path; check guest/member
boundaries, Back, keyboard/safe areas, rotation intent and stored preferences.
Physical iPhone Safari/PWA, desktop, source merge and production release each
need their own receipt. No runtime or deployment acceptance is closed here.

## 2026-11-16 — Return navigation, concise HPC identity and changed phone acceptance

Historical source: 012's November 16 direction. **CHANGES_POC_ACCEPTANCE** for the top-anchored phone player and return navigation; the larger shared floating dock was **LATER_STAGE** at that time. H1H / PFDOCK-20261121 supersedes that deferral and defines the current cross-FoundUp requirement. The previous selected-tile/original-row phone placement is superseded, with desktop and ordinary Mall behavior retained except for the explicit H1H changes. These requirements are specified, not an implementation or deployment receipt.

The functional Vote/Contact return links now have a source candidate on existing draft PR #2411, with fixture tests recorded in [Vote's TestModLog](../voteballots/tests/TestModLog.md). Hosted release and physical-phone acceptance remain open; this does not implement the separate phone-player placement or new portrait artwork.

Immediate owner slice: reuse the existing HPC projection, Vote landing and Contact Congress page. Keep the existing PWA/tile shell and sole Mall implementation owner (`pfmall-truth-author`; existing probe draft [#2405](https://github.com/FOUNDUPS/Foundups-Agent/pull/2405)). Coordinate adjacent Vote source and its existing Sites mirror; do not create another page, tenant, Voice shell or implementation swarm. Contact Congress is an existing manual resource; independently admitted Voice remains later work.

Use the [cross-surface navigation matrix](../docs/PFMALL_MALL_NAVIGATION_CONTRACT.md#47-hpc-vote-and-contact-congress-return-navigation--012-request-2026-11-16). The **entire HPC banner at the top of both Vote and Call Your Congressperson** must be one coherent accessible link to `https://hpc.foundups.com`. Put the small top-corner animated Hasan/HPC portrait inside that anchor; this supersedes an icon-only tap target. Do not nest another link or conflicting button in the banner. Retain the existing Vote/Contact navigation, forms, install controls and independent-site disclosure.

Use concise **HPC** for the banner, scoped heading and install identity. Reuse `public/member/hpc-icon-{180,192,512}.png` and the illustrated character supplied by 012: laughing, curly-haired, bespectacled and bearded at a microphone. The desired crown of thorns and optional halo are a satirical adaptation, not present in the inspected portrait. Materialize 012's supplied placement screenshot and illustrated poster through the supported Library flow and inspect actual pixels before image-dependent work. Do not recreate the full poster inside a small icon or substitute an unrelated face; no endorsement by Hasan or referenced organizations is implied.

A subtle attention-drawing wiggle must respect `prefers-reduced-motion`, remain static when reduced motion is requested, and stop while the document is hidden. Provide a meaningful accessible name for the single banner link, visible keyboard focus and a comfortable touch target (at least 44 CSS px); do not obscure navigation. The distinct existing Red Dog navigation icon (`public/logo-dog.png`) returns to `https://play.foundups.com`. Preserve the Mall's internal Red Dog concierge semantics.

Source audit at main `72a3182c70974f0523be91d5ce4bd32808d824bc`: HPC's Voice CTA already targets `https://vote.mtrout.com/contact`; its scoped Red Dog path is `/f/hpc#red-dog` and its portrait header targets `https://foundups.com/member/`. Both Vote `web/index.html` and `web/contact.html` lack the new banner. These are implementation gaps. Vote's same-origin image CSP requires reusing/deploying local asset copies through its existing owner, not weakening CSP to hotlink imagery.

Acceptance remains open until tests show HPC -> Vote/Contact -> whole-banner HPC return on **both** surfaces, plus the distinct Red Dog -> Mall route, keyboard activation, header fit, reduced-motion/hidden behavior and preserved form/install/admission flows. Source, staging navigation, physical-phone results and production release are separate states. No production deployment is authorized by this record.

Historical deferred roadmap, now superseded by H1H / PFDOCK-20261121: one shared floating Red Dog and bottom FoundUps search dock across existing PWA surfaces. Reuse current anchors, state and search rather than duplicate controls or shells. `https://play.foundups.com` is the intended public Mall entry; existing admission remains in force. **144 FoundUps is a product target, not a verified current inventory.** Preserve the separate return-link work while the shared owner implements the current behavior contract.

## 2026-11-11 reconciliation receipt

PR #2358 is reused for this documentation/skill correction; no new branch or UI implementation is created by this revision. Repository reads are GitHub connector evidence against main `f0d08839e78c0aa2cca592ef20773fc5826f9040`; native WSP bootstrap, HoloIndex, WRE admission, PC state and physical-device playback were not executed in this connector session. Documentation review is not runtime verification. Exact-head checks, authorized merge, main read-back, deployment and PC synchronization must be reported separately.

## H2 — Dream Team and Press Wire (2026-11-17)

**CHANGES_POC_ACCEPTANCE / SPECIFIED_NOT_IMPLEMENTED.** Documentation
reconciliation is the current slice. H1 playback/device gates remain open;
this campaign must reuse shared Mall owners and avoid a second frontend.

1. Resolve the named master workbook and reconcile its claimed four tabs with
   the existing sources in README. Preserve source rows, aliases and unknowns;
   never claim 34 audited organizations from the current 33-row source.
2. Verify existing banner assets/live rendering and both requested/referral
   domain spellings. Coordinate with #2411 and #2376 before overlapping edits.
3. Add the four top selectors to the current shell. Use the nine fictional
   cards in INTERFACE, reviewed portrait assets and source-attributed clips.
   No-result, Back, keyboard, phone/desktop and one-player behavior must pass.
4. Adapt the existing press owner to an HPC Press Wire view. Preserve the raw
   draft separately from publication copy; fact-check factual bridges and label
   satire/nonendorsement. No live-voting or published-release claim before
   actual route/content verification.
5. Only then consider shared preferences and admitted DAE workflows. This
   documentation request sends no email, chat message or comment.

### Requested worker dispatch (planning, not runtime evidence)

| Lane | Requested label in brief | Responsibility | Required receipt |
| --- | --- | --- | --- |
| Campaign/editorial | Astra 6.1 Sol | Deadpan satire, D.U.P. dictionary, hypothetical coalition math and bikini/bathtub narrative | Reviewed copy, factual-source separation, no invented endorsement or whip count |
| UI | Astra 6.1 Terra | Existing-shell selector, portraits/cards and attributed clip filtering | Exact source/head, scoped tests, phone/desktop evidence and live release state |
| Outreach/data | Astra 6 Lunar | Existing workbook reconciliation and proposed UI-TARS/DAE integration | Exact workbook identity/counts, recipient/sender preflight and separately admitted runtime |

These labels are copied from the brief, not available-model or running-worker
claims. Bind actual model IDs through runtime evidence before dispatch; do not
silently substitute tiers. No workers or DAEs were activated by this record.

D.U.P. supplied expansions: “Democratic Uniparty Pawns” and “Donor-Owned
Useless Politicians.” This is satirical vocabulary, distinct from the factual
United Democracy Project (UDP). The complete claimed dictionary has not been
located. A proposed 15–25-seat Nash Blocking Coalition is a scenario, not an
observed bloc; model actual House voting rules and attendance before claiming
a blocking threshold.

### Reconciliation coverage and remaining blockers

Owner: 0102, documentation reconciliation, 2026-11-17. Base
`fc1324815c892ab02f003fe95917a77358001a59`. Bounded open-PR check found #2376
(press), #2411 (Vote banners), #2405 (iPhone probe), and #2394 (social skills);
preserve their distinct work. No native checkout, WSP bootstrap, semantic
HoloIndex, WRE admission, PC state, deployment or physical-device execution
was verified in this connector session. Retrieval was lexical GitHub/Drive;
noise included unrelated Drive full-text matches, reduced using name filters.
Missing master identity is the consolidation blocker. Documentation checks
are not runtime or independent acceptance. Required PR checks/review and main
readback remain separate closure gates. WSP15 planning: C2/I4/D4/Impact3 = 13/P1.
