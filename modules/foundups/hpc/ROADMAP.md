# HPC roadmap

## 2026-11-16 - Build v22 direct continuation and policy qualification

012 explicitly authorized the existing v21 continuation through tests, push,
draft PR and isolated preview. WSP 110 section 2.1 principal handoff records
previous owner `pfmall-truth-author`, accepting direct Codex continuation,
expected native head `1b5b77323325b855faf25d4a04ba3e671462084e`, and preserved
header/entity commits `fe9e9afe4fd94e23ce027e7ae125ced075b53ba6` and
`bfcd7d0de721288260fafcadc9fd71bcc1bb0485`. No exclusive lease or native-agent
ACK is invented. Recheck head and all working state before ff-only native
integration and use a guarded same-branch push. No production deploy or merge.

The v21 hidden-player release defect described below is repaired in the v22
source candidate: tuck/dismiss/document hide pause playback and cancel loading,
start and recovery timers. Closed/tucked/hidden/offscreen stages cannot start;
late READY/PLAYING/ENDED/error/recovery callbacks enforce that boundary. Untuck
keeps the same iframe paused for explicit visible Play. Scripted playback
retains the 200 x 200 stage and more-than-half-visible gate; continuous partial
visibility is not redefined as a universal 50-percent pause rule. One stage
observer reuses the central pause helper; chrome timers remain separate.
Generic third-party iframe and opacity-only hiding are outside this YouTube fix.

Build label, shell cache and versioned assets move together to v22. Existing
browser fixtures now reject hidden audio rather than certifying it. Controlled
Chromium/WebKit player-policy and header/entity runners pass, including pending
WikiTube recovery cancellation, same-frame manual return, provider error
taxonomy, rotation and exact far-scroll restoration. Targeted pytest: 209 pass;
direct Node state/cache VM: 24 pass (overlaps its pytest wrapper). These are
source/fixture results, not real YouTube or physical iPhone acceptance.

See [before/after regression matrix](../docs/PFMALL_V22_REGRESSION_MATRIX.md)
for preserved routes, actions, gestures and explicit acceptance changes.
Native integration, remote push/PR/checks and fresh preview parity are separate
receipts. Physical Safari/PWA on Wi-Fi/cellular remains unexecuted as a structured
matrix. Principal-reported VPN-off playback is retained without invented numeric
telemetry. WSP 22, 50, 71, 91, 97 and 110 apply.

## 2026-11-16 small-sprint reconciliation (candidate on native Build v21)

CHANGES_POC_ACCEPTANCE: 012 now requests one visible, top-anchored shared
player with the grid scrolling beneath it. This supersedes H1's earlier
selected-row placement. Preserve one media instance, selection, queue,
close/Back restoration and both phone and desktop browsing. Full offscreen
tuck with continuing audio is a release blocker, not accepted behavior.

The first bounded source candidate reuses the whole supplied wide satire
artwork in the existing left HPC header, keeps Build v21 directly above it,
and leaves the separate right Voice / Contact Congress control unchanged.
It reuses the existing repository artwork (`hpc-banner.webp`), concise HPC
semantics, Mall return link and independent-site disclosure. The new asset
is declared in the shell precache; release generation and deployed parity
still require the existing release owner. This is not a new deployed build.

Vote and Contact Congress return links are implemented separately in draft
PR [#2411](https://github.com/FOUNDUPS/Foundups-Agent/pull/2411), head
`5c7c22554be86b9ec1c8cbcd3cb5b5c12e85098d`: the entire top HPC banner
returns to `https://hpc.foundups.com`; distinct Red Dog links return to
`https://play.foundups.com`. The draft is unmerged in this reconciliation.
Its 129 Node / 132 controlled Chromium-WebKit checks do not prove production
or physical iPhone navigation. Keep that PR separate from Mall/player work.

Continue with one public Mall entity/loading slice, then other creators'
qualified video tests, shared player repair and WikiTube search/sequential
playback. The wider design remains under discussion. See the
[Mall roadmap](../pfmall/ROADMAP.md), [navigation contract](../docs/PFMALL_MALL_NAVIGATION_CONTRACT.md)
and [shared incident](../pfmall/MEDIA_PLAYBACK_INCIDENT_HPC.md).

Release blocker on source `1b5b77323325b855faf25d4a04ba3e671462084e`:
`mall-video-player.js` `tuck()` does not pause, `canStartYouTube()` returns
true when tucked, and the matching CSS moves the whole player offscreen.
The existing player owner must pause fully hidden/dismissed playback and
remove the visibility bypass. Displayed player minimum 200 x 200 and
unobscured native controls remain required; scripted autoplay requires more
than half the player visible. The visible stage's minimum height does not
qualify the hidden state. Sources: [YouTube policies](https://developers.google.com/youtube/terms/developer-policies)
and [required minimum functionality](https://developers.google.com/youtube/terms/required-minimum-functionality).

Physical Safari and installed-PWA Wi-Fi/cellular receipts remain incomplete.
012's VPN-on challenge and VPN-off playback/Wi-Fi continuation are principal
reports, not independently captured player telemetry or proof that Clerk
authentication fixes YouTube session state. Keep provider challenges,
embedding restrictions and app defects separate. No production deployment
or release approval is claimed by this candidate.

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
| PC / monitor | Centered main video above a continuous horizontal thumbnail strip. Search sits **between the main video and the bottom tiles**. The main player is not forced browser fullscreen. | Desktop screenshots and browser interaction tests must show this composition; oversized three-column posters or an extra player inserted below a selected row do not satisfy it. |
| Desktop startup / queue | Request playback of the first eligible clip on entry, then advance through the queue. Preserve one active player and deliberate sound controls. | Test actual provider state and advancing time. Where the browser blocks startup, show a truthful user-activation recovery; never claim guaranteed audible autoplay. No duplicate or hidden players. |
| Search | Center a compact search bar beneath the desktop video. Typing filters the scoped queue. Submit plays the next match or the first available match. The phone search submits a grid filter and offers local dictation where available. | Search uses existing HPC catalog metadata. Test stable IDs, selection, no results, return state and the phone keyboard. Cross-FoundUp discovery remains a later permissioned expansion. |
| Phone | Compact three-column portrait grid, fixed header, thumb-accessible bottom controls, vertical browsing through eligible clips. Selection opens the one visible top-anchored shared player; the grid scrolls beneath it. Close restores browsing position and focus. | Check header/player clearance, all three columns, one iframe, provider minimum size and visibility, explicit expand or supported pinch, and return. Fully hidden playback is a release blocker. |
| Breakpoint / rotation | Change presentation without duplicating the media session or losing video identity, queue, query and browsing position. | Test desktop, phone portrait/landscape, resizing and keyboard access independently. Do not classify all large tablets by pointer alone without testing. |
| Entry and membership | Guests browse on `hpc.foundups.com`. `foundups.com/members` leads to the existing member gate. Admitted members can select HPC from the Mall or return to the same selection after sign-in. | Guest, uninvited and admitted browser cases. The `/f/hpc` landing links to the dedicated host. `/f/hpc/app` retains its protected handoff. |
| Shared-regression guard | Preserve ordinary Mall channel expansion, other FoundUp projections, guest/member boundaries, provider diagnostics, save/history and return navigation. | Reuse the existing tests and fixtures for the shared grid, player and account boot. |

This request supersedes earlier hidden-search wording only for **HPC-scoped bottom search**. The master-Mall logo link and independent-site disclosure remain. The latest clarification places search above the bottom desktop strip, not below it.

### H1C · Evidence and recovery before implementation

- Revalidate current main, related heads and deployed assets separately. PR #2357 introduced a hard-coded three-column scoped grid and `openScopedVideo()` inserts `.mall-inline-player-slot` after a calculated row. The reported desktop result is a regression candidate, not a fully reproduced cause of every playback failure.
- The original #2359 draft changed desktop density alone. Browser reproduction showed that six CSS columns still used three-column JavaScript row placement. #2359 and #2364 restored the shared desktop theater and search. 012's 2026-11-12 correction changes phone acceptance from a player below the row to playback in place of the selected tile.
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
the existing public Red Dog briefing. Check iPhone standalone installation
and keyboard dictation against a hosted build before accepting that device.

Prototype work includes an admitted device-compatible agent selector, Red
Dog press-and-hold speech, and camera handoff to AutoPost. Reuse existing
identity, admission and capture owners. Verify consent, cancellation,
supported device models and return context before exposing actions.
Seven-level preferences, community nominations, comics/story panels and
whole-Mall discovery keep their existing stages.

## 2026-11-11 reconciliation receipt

PR #2358 is reused for this documentation/skill correction; no new branch or UI implementation is created by this revision. Repository reads are GitHub connector evidence against main `f0d08839e78c0aa2cca592ef20773fc5826f9040`; native WSP bootstrap, HoloIndex, WRE admission, PC state and physical-device playback were not executed in this connector session. Documentation review is not runtime verification. Exact-head checks, authorized merge, main read-back, deployment and PC synchronization must be reported separately.
