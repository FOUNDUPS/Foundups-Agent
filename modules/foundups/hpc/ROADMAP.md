# HPC roadmap

## 2026-11-22 — Floating controls and camera continuation

**CHANGES_POC_ACCEPTANCE / IMPLEMENTED_PENDING_VERIFICATION** in the existing
#2439 continuation. 012 reports v25 playback working on an iPhone 16; the OS,
standalone mode and delivered phone fingerprints were not supplied. Preserve
that USER_REPORTED result separately from controlled browser/device acceptance.

- Extend the shared player with viewport-clamped dragging, persistent frame-edge
  gesture targets and a video-height Restore rail. Scrolling continues beneath
  it. Native YouTube input remains unobstructed. App gestures cannot capture
  touches inside the cross-origin provider document.
- Remove the redundant floating title/expand row and persistent app Play strip.
  Keep single-pointer/keyboard actions in `+` → Video and native provider Play.
  Outward pinch defaults to WikiTube as confirmed by this feedback; direct app
  Full Video is selectable. Pinch-in and swipe-up returns are independent saved
  choices. Existing return behavior remains until a return choice is selected.
- Fully hidden YouTube playback pauses, as required by provider policy. A larger
  restore rail is not a visible player and cannot justify background audio.
  Keep `revealSelectedPlayer` and visible sequential playback settings.
- Replace the separate dock microphone with the canonical public AutoPost
  camera handoff, saving Mall state and passing only an allowlisted `return_to`.
  The companion AutoPost owner supplies Camera/Preview/Options/Return. Its full
  shared search/conversation dock remains a separately missing connector.
- Red Dog tap/hold opens its existing conversation owner without navigating to
  another FoundUp or dictating into search. An unavailable service stays in-page
  with Back to browsing. This is not delivered spoken AI: the qualified public
  backend host, durable accounting/ingress/secret bindings and browser speech
  path are missing. No browser language model is admitted. The existing 41-byte
  WASM test is only compatibility evidence.

Allocation: C3/I4/D4/Impact4 = **15/P1**, extending existing owners. Accept only
after independent source review, shared browser/VM regressions, exact-head CI,
source-bound preview and physical Safari/Home Screen testing. No production
deployment, new calling engine, automatic model download or lifecycle promotion
follows from this record. The [shared incident](../pfmall/MEDIA_PLAYBACK_INCIDENT_HPC.md)
owns evidence and the [navigation contract](../docs/PFMALL_MALL_NAVIGATION_CONTRACT.md#14-shared-search-dock-and-video-preferences)
owns shared behavior.

## 2026-11-22 - main reconciliation candidate in existing PR #2439

Inputs are phone head `2a65e7983acb489084cecf1229fcfd582f68f19b` and main
`dc7c34aa6444aa1fc37de1217f99f0e75e4d2f0b`. 012 permits a normal main-into-
feature reconciliation; landing the PR and publication remain unauthorized.
Preserve the tested v26 return/navigation/player and current main contracts,
all dated Canvas decisions and accepted main-only work. No Fractal runtime or
held gesture defaults are imported.

Diagnostic probe code remains in existing test fixtures, not committed public
Hosting paths. Preview assembly must explicitly copy the canonical fixtures and
generate fresh source/build/catalog/probe/Hosting metadata outside Git. The
candidate reuses the 29 worker cases, six existing probe cases and ten metadata
groups, with additive source-hash and guard coverage in the existing workflow.
Exact composed-source tests, independent review, security/CodeQL and hosted CI
must qualify the eventual head. No new preview, live change, physical Safari/PWA
or real YouTube/sound result is claimed by this reconciliation entry.

## 2026-11-22 - main reconciliation candidate

Reconcile canonical main `dc7c34aa6444aa1fc37de1217f99f0e75e4d2f0b` with the
qualified phone source `2a65e7983acb489084cecf1229fcfd582f68f19b` in existing
PR #2439. Preserve current shared acceptance and the dated source receipts
below. Prior exact-head tests qualify their recorded sources only; the resulting
candidate needs its own validation. No publication or physical iPhone result
follows from conflict resolution, and the separate Fractal runtime is not a
phone-release prerequisite.

## 2026-11-22 - selective v26 reversible return; existing PR #2439

0102 resumes the existing clean #2439 source lane at
`5e0f87e1d4faad4de8748e83c71d02953640cb40`. Canonical main was inspected at
`dc7c34aa6444aa1fc37de1217f99f0e75e4d2f0b`; the branch remains conflicting.
This bounded continuation follows the current shared navigation contract's
[section 14](https://github.com/FOUNDUPS/Foundups-Agent/blob/dc7c34aa6444aa1fc37de1217f99f0e75e4d2f0b/modules/foundups/docs/PFMALL_MALL_NAVIGATION_CONTRACT.md#14-shared-search-dock-and-video-preferences).
It preserves the Canvas funding/Voice decisions and all prior dated evidence.

Adopt only reversible Mall return, confirmed video-tile tap destinations and
navigation from the private review bundle. Floating is the confirmed tile-tap
default; frame destination remains independent. No guest Fractal client,
prototype lenses, face loans, or unresolved pinch/swipe defaults are adopted.
The three gesture defaults remain open; no new gesture control is advertised.

Mall return pauses a controllable ready provider behind the Mall while retaining
the clip, queue/query and observed position. Existing history/field owners
restore caller scroll and focus. Forward restores paused; a deliberate visible
selection may request playback. Unsafe or unready providers are disposed with
an honest continuity-unavailable state. Final Close destroys playback. The
still-visible selected field retains its own pager until a scope change; late
page completion cannot recreate a closed player. One bottom dock remains.

The direct unavailable-conversation dog returns to Play Mall with an accessible
Mall name; campaign banner and Voice destinations remain distinct. Separately
reviewed DOM/text rendering repairs cover history and two exception messages.
They do not change admission, membership, editor permissions or URL policy.

Controlled Chromium/WebKit results, exact source hashes, independent reviews
and the red-to-green Close/reopen paging case are recorded in the
[member test log](../../../public/member/tests/TestModLog.md). The historical
aggregate's 56-case PASS does not qualify this selective composition. Hosted
checks/CodeQL, conflict reconciliation, preview parity, physical Safari/PWA and
real-provider playback remain separate gates. No merge or publication is part
of this change; live v25 and both frozen previews remain untouched.

## 2026-11-21 - v26 phone candidate; v25 frozen comparison

Current work starts from `9b85e9cbb874b3720e453d3e3d3a3974dca53504`.
Keep v25 and its exact-source artifact/results frozen for comparison. The
changed v26 source has no combined runtime, deployment or physical PASS recorded
by this entry; dated results below remain bound to their original SHAs.

The phone subset reuses the shared player and existing bottom dock. Its leading
`+` holds Video Options and a separate on-demand Browse AI pilot; the trailing
`+` opens contribution review. One visible dock, player/grid clearance, hidden
playback pause, rotation/return and desktop preservation remain acceptance gates.
Compact Play chrome and the HPC banner reuse the existing identity owner. The
banner targets `https://hasan4speaker.com/`, with a distinct Play Mall return.
These are [source destinations](../../../public/member/js/mall-video-projection.js),
not deployed navigation receipts.

Browse AI is a confirmed 41-byte WASM addition compatibility test, not an AI
model/runtime. No preload or cloud fallback; WebGPU remains UNQUALIFIED until
the exact physical Safari/PWA cases are tested. See the
[member roadmap](../../../public/member/ROADMAP.md).

Graph work referenced as `22374b` is not integrated. Depth access and backend
writer actions stay unavailable/fail closed pending their service owner;
sign-in/invite continuity grants no editor permission. Paid access is proposed.
Next: qualify combined v26 source, verify isolated HTTPS assets/worker, then
capture real media advancement on physical iPhone Safari and installed PWA
on Wi-Fi and cellular.

## 2026-11-21 JST — v25 phone preview awaiting publisher sign-in

Build v25 passed security and all five qualification gates on
`bd0510c5c2e333d07b1bb02340ca91b291420164`. The artifact binds the player,
styles, worker, entry points and current discovery generation to that source.
[Qualification run](https://github.com/FOUNDUPS/Foundups-Agent/actions/runs/44689762799) ·
[Artifact](https://github.com/FOUNDUPS/Foundups-Agent/actions/runs/44689762799/artifacts/14608356242)

**P0 under WSP 15 (3 complexity + 5 importance + 5 deferability + 4 impact = 17).**
012 needs an isolated release to test the player. The Firebase plugin is enabled.
The Firebase CLI returned `Failed to authenticate, have you run firebase login?`
when listing channels on `foundupscom` in `gen-lang-client-0061781628`. The public
`play-v24-iphone` probe still reports v24 and gives its Hosting version as
`unverified`. The owner of this delivery is 0102. Resume at authenticated
channel readback, preserve the complete baseline version and its configuration,
then release and verify `play-v25-iphone`. The release ID, URL and expiry are
pending. Physical Safari, Home Screen and real-provider acceptance follow publication.

## 2026-11-20 - Integrated v25 automated qualification PASS; publication pending

Controlled runtime qualification is PASS on
`472e3977d0cfc6948662b85de5161993eeb4faf4`. The preview is not published;
real YouTube playback and physical iPhone acceptance remain UNEXECUTED.

012's current prototype gate is one top-anchored shared player, the existing
video field scrolling beneath it, and one tile tap requesting playback with
WikiTube queue continuation. HPC remains the shared Mall test pad. Cards,
fractal navigation and another application are not prerequisites for this slice.

The candidate is based on `75c838b6eab19807487ee02c4b2f9367e580547e`, the
committed v23 continuation underlying the existing v24 preview. It repairs the
wrapper's reset of floating-player scroll padding and adds one muted retry for
an actual browser autoplay rejection during visible startup. Late rejection
callbacks cannot replace playing, paused or provider-error status. The existing
single player, visibility checks, native controls and bounded queue remain the
owners of playback.

Source repair commit: `3f6dc9f550181864b6fdb6aaa7a9ca9a6f765128` on
`fix/hpc-phone-start-scroll-20261120`. Hosted qualification PASS on exact commit
`a882d6d40302a1f682b82d372575b20108ce9ef2`:
[run 44666808469](https://github.com/FOUNDUPS/Foundups-Agent/actions/runs/44666808469).
The existing security gate and both Chromium/WebKit player-policy and delayed
queue suites pass. This includes the new 390 x 844 startup/scroll case and the
retained 375px floating-player, gesture and queue controls. The hosted runner
resolves the earlier local browser-launch limitation without changing local
permissions. This PASS qualifies the native-source repair, not the newly
integrated v25 candidate. Its provider/network events are controlled; real
YouTube time progression and physical iPhone Safari/PWA remain UNEXECUTED.
See `public/member/tests/TestModLog.md` for source hashes and retained evidence.

The v24 recovery blocker is resolved for the observed Mall/HPC surface. The
six changed Mall shell files, catalog metadata and diagnostic probe were
recovered from the public preview. All 206 referenced discovery JSON assets
were retrieved with no missing references. The existing offline exporter, with
only `hero_label` added to its metadata allowlist, reproduces every asset byte
for byte at generation
`253f25242968fe4e826671a8c654bddbd87deb8da2ff2ce737010ec0d14a078d`
(17 metadata records and 1,205 videos). Original ephemeral staging is no longer
required to reconstruct this scope. Historical overlay authorship and a full
Hosting clone are not established by this recovery.

The initial integration assembled on `dba56a6f20efd932971683ece710cba7e1921488`
retained those v24 behaviors, the qualified player and the scroll-clearance fix.
Its build label, versioned assets and member cache advance together to v25.
The root, public-directory and FoundUp detail pages use the same v25 projection
reference; the existing host allowlist adds only `play-v25-iphone`. The
diagnostic probe retains source `313d8168205178cf5387e1912bd5e462d1dafaa9`.
Local integrated checks are logged: 159 targeted pytest checks and 29
actual-worker VM cases passed. The complete 222-path recovery/integration hash
manifest passed before the subsequent player rotation repair; it is historical
bundle-parity evidence, not a whole-current-source acceptance receipt.
The two exact public SDK source bindings were independently reviewed, applied
by the release owner and confirmed by a third review.

Integrated [run 44684325801](https://github.com/FOUNDUPS/Foundups-Agent/actions/runs/44684325801)
on `58627755e4942f72852367fb7be68790dca706e8` FAILED the public-TV gate.
Security and the other four gates (player policy, delayed queue callbacks,
worker/state VM and static contracts) passed. Chromium's public-TV portion
passed; WebKit passed initial portrait and landscape, then failed the return
to 390 x 844 portrait. Its stage had resized correctly, but the player retained
the landscape header offset (top 132px instead of 165px) and zero grid
clearance. The first row overlapped the player by 117.797px, and a Member
Portal control also intersected it. The synchronous window-resize geometry
update did not track the final responsive header/player boxes.

The follow-up source repair observes only the existing header and player with
one guarded `ResizeObserver`, then reruns the existing geometry calculation
while floating/theater mode is open. It adds no playback request, timer or
iframe and preserves the existing resize/pause guards. The existing public-TV
assertion now also rejects portrait header overlap; its 90ms wait, minimum
stage size, visibility and tile-clearance checks are unchanged. Retest
[44685419171](https://github.com/FOUNDUPS/Foundups-Agent/actions/runs/44685419171)
on `9161711822556f3648968191348d30e053ef02f3` repeated the same WebKit rotation
failure; security and the other four gates passed.

Instrumented public-TV runs then passed 92/92 at `a818ac1c`
([44686567252](https://github.com/FOUNDUPS/Foundups-Agent/actions/runs/44686567252))
and 100/100 at `c7de04bf`
([44687274822](https://github.com/FOUNDUPS/Foundups-Agent/actions/runs/44687274822)).
The plain control at `ba11b0b4`
([44687859449](https://github.com/FOUNDUPS/Foundups-Agent/actions/runs/44687859449))
failed its first portrait return under the unchanged 90ms requirement. All
viewport measurements were already 390 x 844 and the header bottom was
159.1875px, but player top remained 132px and clearance 0. About 207ms later
they corrected automatically to 165px/159px, before explicit synchronization.
This proves delayed geometry updating; the earlier instrumented passes do not
prove its cause or eliminate the plain-control failure.

The current candidate adds one live media-query owner using the exact CSS
predicate `(orientation: landscape) and (max-height: 500px)`. Its guarded change
handler invokes the existing geometry calculation, which reads that query's
`.matches` instead of duplicating viewport dimensions. Observer, resize/pause
and media behavior remain unchanged.

Final controlled [run 44688858246](https://github.com/FOUNDUPS/Foundups-Agent/actions/runs/44688858246)
on `472e3977d0cfc6948662b85de5161993eeb4faf4` passed all five qualification
gates and security (53 regression tests, zero unreviewed findings). Public TV passed 100/100,
including all five plain WebKit portrait returns at the original 90ms limit,
later paging and desktop checks. Queue callbacks passed 18/18, worker/state VM
29 and static contracts 159. The plain-control test is byte-identical to the
failed `ba11b0b4` run; only the player changed among their recorded source
hashes. This qualifies the tested fix under controlled providers, without
claiming a browser-engine cause or real YouTube/device acceptance. The
subsequent documentation-head run passed as recorded above.

At handoff, the publishing CLI needed authentication and the Cloud Shell
attempt had failed to open. The committed probe receipt identifies the
unpublished candidate. Source and release fields are filled by the publisher
after Hosting allocates the version.

Next work, in order:

1. Authenticate the authorized Firebase publisher for existing project
   `gen-lang-client-0061781628`, site `foundupscom`. Read the old immutable
   Hosting release, configuration and manifest, preserving unchanged assets
   outside the recovered Mall/HPC scope. The public reconstruction is not a
   complete Hosting clone; original ephemeral staging is no longer required.
2. Publish only the isolated `play-v25-iphone` candidate. Bind the receipt to
   the qualified source SHA and actual immutable release, then verify delivered
   hashes, cache generation and Build v25. Provide the verified
   `/member/?foundup=hpc` URL; `/member/` alone is the general Mall.
3. Record physical Safari/Home Screen results before production promotion.
   The phone must show **Build v25**; the player must stay anchored while tiles
   scroll beneath it; one tile tap must request playback and allow the bounded
   muted fallback; and the queue must continue without creating a second
   player. Record advancing real media time and return/restore behavior. Check
   that the existing desktop WikiTube layout, selection and queue still work.
   A genuine provider refusal remains a visible failure, not a playback PASS.

The existing [v24 HPC preview](https://foundupscom--play-v24-iphone-3rrzxm0r.web.app/member/?foundup=hpc)
still serves the previous runtime. A cloud-browser attempt timed out after its
existing Play recovery; no explicit bot/sign-in challenge or advancing video
time was observed. Do not label that timeout as a diagnosed authentication fault.
WSP 97 keeps source, controlled validation, delivered version and device
acceptance distinct. No production merge or owned open PR was created.

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

For the Stage 2 Canvas slice, first qualify the H1H presentation-only pass.
H2 follow-ons remain future notes, not dependencies; Voice retains its later
Stage 3 gate.

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
forced WikiTube entry on a deliberate tile tap and fixed player up/down
behavior where they conflict. The default-entry decision below is distinct
from the Floating default for a selected Video tile.
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

#### Default entry and Canvas presentation-only pass — 012, 2026-11-21

**SPECIFIED_NOT_IMPLEMENTED; Canvas parity UNVERIFIED.** On default entry,
desktop/PC opens WikiTube TV in the available app window, skipping the Mall
grid; phone opens the responsive Mall grid. Explicit deep links, deliberately
chosen navigation and Back take precedence over the default. Reuse viewport
and input-capability rules rather than device-model guessing; qualify hybrid
inputs and breakpoint boundaries. Desktop viewport overrides do not prove
phone Safari or Home Screen behavior.

The Canvas first pass is presentation only: the Mall tile is the card face,
with a recognizable portrait and readable UI name. Reuse the actual v26 Video
grid component and layout tokens, not a visually similar second grid. Match
outer dimensions, aspect, spacing, columns and breakpoints only within the
same surface, viewport, settings and player/scrollbar state; do not impose a
global 3:4 ratio. Templates and crops follow the actual slot, and art master
dimensions are subordinate.

Test the same portrait resizing/repositioning through Grid, Floating,
WikiTube half/top stage and app fullscreen, or the direct destination selected
in shared Tile Settings. Grid tap does not flip. Canvas fullscreen inward
pinch returns to the originating card grid, with an accessible button/keyboard
equivalent; preserve the scroll container, anchor, offset and focus. Native
provider fullscreen remains distinct.

When Canvas exists, compare both views at identical 414 × 896, 390 × 844 and
393 × 852 CSS viewports and both sides of shared breakpoints. Record actual
rectangles and computed tokens, crop/face safe area and return continuity.
Separate calculated, desktop-override and physical Safari/Home Screen results.
The inspected HPC Video state computed 3:4; that observation is not a global
constraint. No Canvas CSS/viewer or measurement currently establishes parity.
Use one reusable still portrait master with derived crop/size variants, not
four commissions. Funding, votes, scores, detail/flip panels, progressive
content density and gameplay are not acceptance for this pass.

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
   Canvas is a separate collection: use H1H's presentation-only gate and the
   future notes below; it does not replace these nine fictional cards.
4. Adapt the existing press owner to an HPC Press Wire view. Preserve the raw
   draft separately from publication copy; fact-check factual bridges and label
   satire/nonendorsement. No live-voting or published-release claim before
   actual route/content verification.
5. Only then consider shared preferences and admitted DAE workflows. This
   documentation request sends no email, chat message or comment.

### Canvas follow-on and future roadmap — 012, 2026-11-21

These are **future design notes, not v26 presentation-pass dependencies**.
Keep the seated Senate collection separate from the nine fictional Dream Team
cards above. Use stable subject IDs and source dates; unknown data stays
unknown. No art commission, runtime change or release follows from this entry.

- **Shared Canvas/card engine or Tool, all FoundUps:** reuse rendering and
  presentation with injected FoundUp-specific content providers; HPC Funding
  is one provider. Keep this follow-on beside the Canvas entry. Future
  brainstorm only: 012 specifies what to populate; Red Dog finds and verifies
  sources, then prepares a lean collection JSON manifest and per-card JSON
  through the shared tool. No separate task or implementation is created.
- **Progressive content:** Floating may later place compact stats beside the
  portrait; WikiTube may show a smaller portrait and more information; app
  fullscreen may show sourced state represented, tenure, funding and voting
  record. A tap inside fullscreen may reveal detail or switch panels, with an
  optional reduced-motion-safe card reveal. Text/data and any future qualified
  score belong in UI, not the portrait. This does not override grid tap routing.
- **Funding Tool tile:** a separate first-class, read-only HPC Tool shows
  sources, ingestion modules and actual status, dates, revisions, filing/receipt
  links and provenance for each Canvas figure. Reuse existing Vote/evidence
  owners. Keep candidate receipts separate from outside support/oppose spending;
  qualify stable candidate/committee IDs, amendments, deduplication, coverage and
  dated receipts before deriving anything. A dated funding pledge/news item
  retains exact scope and a primary link; it changes no score and proves no
  later filing compliance.
- **Voice Tool, later Stage 3:** constituent-office queue, message preparation
  and a user-confirmed call only; no auto-dial, automatic voicemail or calls
  from this planning lane.
- **Side-by-side card comparison:** a separate future exploration.

#### Future Roadmap > Games

**Poly Magic** is a working title for original two-player card-versus-card
battles using the same Canvas cards, with possible special abilities. Rules
are deliberately open. No rules commitment, game build or change to v25/v26
scope is authorized.

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
