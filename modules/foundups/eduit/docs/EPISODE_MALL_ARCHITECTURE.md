# EDUIT episode Mall architecture

Decision date: 2026-10-26 JST. Source baseline: main `a6fed6dd8` (PR #2215).
**SPECIFIED**, except where explicitly marked **OBSERVED**. This document owns
012's current product direction; it does not activate routes, billing or workers.

## Intent and continuity

EDUIT means **Education Using Information Technology**. `eduit` is the parent
educational FoundUp and an educational sleeve of Play FoundUps Mall. Us Story
Time is its initial learning experience, using `kids_episodes` production.
“Edjuit”, “Eduate”, “Play Founders”, and similar dictated variants in this
conversation mean these existing names, not new products, domains or IDs.

This realizes the 2007 educational vision through a small working slice. See
[historical lineage](../../../../docs/audits/pfmall_eduit/EDUIT_DISCOVERY_HISTORICAL_LINEAGE_2026-10-08.md):
The Tool + The Content + The Experience. Historical proposals are not proof of
learning outcomes. The current Fukui eSingularity application is separate.

Canonical naming correction from 012: **Us Story Time**, matching the existing
YouTube handle `@Us_Story_Time` and publisher key `us_story_time`. Earlier
“Our Story Time” wording is a dictation artifact, not a second collection.
Preserve `eduit`, `kids_episodes` and the publisher binding. The earlier planned
`ourstorytime.eduit.org` hostname is not an active deployment or a newly approved
canonical brand; reconcile the intended `usstorytime.eduit.org` name with actual
hosting/DNS ownership before binding it. No DNS rename is performed by this spec.

## Product decisions

- **One episode tile = one video + its playable learning activity.** An episode
  is a content record, not a new FoundUp registration, channel or independent app.
- Opening a tile presents one page: video above, game below, then Next and the
  existing Red Dog control at the bottom. Mobile-first; retain this reading order
  on tablets/desktops. Do not make two unrelated playback/game queues.
- `eduit.org` opens the first available watch/play episode for the initial POC,
  not the earlier introduction landing. Us Story Time deep links open the same
  experience. Introductory/about text moves behind For parents.
- The game waits for explicit Play; watching the video must not consume the
  game's reaction window. Only one video/game audio source plays at a time.
- Next advances to the next released, available episode in this story collection.
  A missing next episode shows “More stories coming” and Replay, not a dead link,
  unrelated Mall recommendation or membership promise of nonexistent content.
- For parents opens the education catalog/settings. An explicit parent action
  can leave EDUIT for the general Play FoundUps Mall. Child navigation stays scoped.
- Each panel has a small, labelled expand arrow. Reuse existing gestures, with
  buttons/keyboard equivalents; gestures are optional, not the only way out.

## Existing owners and exact gaps

| Concern | Existing owner / evidence | Integration needed |
|---|---|---|
| Mall shell, tile field, product selection | `public/member/INTERFACE.md`, `index.html`; Move2Japan adapter precedent | EDUIT adapter and episode detail mode; no copied shell |
| Gesture recognition | `public/member/js/gesture-engine.js`: `gestureZone`, `onPinchIn`, `onPinchOut` | Bind scoped episode panels; no new gesture engine |
| Video expansion | `public/member/js/mall-video-player.js`; fullscreen contract | Reuse video controls while preserving episode context |
| Return/scroll state | Existing Mall product state restoration | EDUIT collection/episode selection, no cross-product leakage |
| Red Dog/account plane | `public/member/RED_DOG_DIGITAL_TWIN_CONTRACT.md` | Reuse control; authenticated conversational dispatch remains a gap |
| Venture/catalog identity | `modules/foundups/foundup_registry.json` and its schema/loader | Reconcile EDUIT manifest; parent/surface metadata needs schema work |
| Story/learning plan | `modules/foundups/kids_episodes/src/story_pipeline.py` | Project reviewed episode references into existing catalog |
| Editing, rendering, creator review | `modules/communication/youtube_shorts/` | Keep production separate from child playback |
| Current game and scene | `public/eduit/storytime/{engine.mjs,game.js,scene.mjs,rig.mjs}` | Adapt existing activity to shared episode lifecycle |
| Deployment | `modules/foundups/eduit/DEPLOYMENT.md` | Authenticated hosting/domain bindings, verified live URL |

**OBSERVED:** shared Mall supports pinch-out tile expansion and pinch-in return;
video fullscreen supports pinch-in/swipe-down exit and a queue constrained to one
FoundUp. Its `next()` advances videos, not composite learning episodes. Do not
wire that method directly to episode Next or inherit video-ended auto-advance
that skips the game. General Mall tile tap currently starts autoplay; the EDUIT
adapter must explicitly specialize its own tiles without changing other products.

**OBSERVED:** Story Time currently shows the game before the video. The local
review page is editor-owned and mounted by EDUIT's build. Neither is the shared
Mall episode view. Registry contains `kids_episodes`; EDUIT has a module manifest
but no canonical registry entry at this baseline. Category `ai-education` alone
is not scope enforcement. Runtime admission is not paid membership entitlement.

## Interaction and lifecycle

| State/action | Result |
|---|---|
| EDUIT landing or episode tile | Open episode, selected locale; game idle |
| Watch | Play video; pause any active game |
| Play game | Pause video; start cues only now |
| Pause, hidden tab, locale change, parent plane | Pause activity and audio; no missed cue penalty |
| Expand video / game arrow or existing pinch-out | Focus selected panel; retain same episode |
| Pinch-in / Back from expanded panel | Return to combined episode page |
| Back from episode | Restore education collection and position |
| Parent leaves EDUIT | Explicit route to general Mall via existing owner |
| Next | Dispose prior handlers/media/timers; load next available episode |
| Retry | Reset same activity; unlimited attempts on unlocked content |

Fullscreen game mode must not send gestures to the background Mall. Game taps
must not accidentally trigger navigation. Pause before view changes; define
whether resume continues or restarts the attempt. Browser/native fullscreen
failure falls back to the shell overlay. Preserve browser accessibility zoom
outside dedicated gesture zones. Touch, mouse, keyboard, safe areas, rotation,
small screens and reduced motion need real device/browser acceptance.

## Sound, words and language

English is the first released locale; Spanish and Japanese are specified next.
Display language names (English / Español / 日本語); flags may be decoration,
not the only label. A locale changes the episode's captions, instructions,
visible sound words and available narration together. It must not alter story
identity, learning objective, geometry or event order.

Give each event a stable cue ID: stomp, crunch, squish. Play the actual effect
and show the localized word at that cue; optional spoken pronunciation follows
without masking the effect. Review natural sound words and pronunciation per
locale; do not invent literal translations. Text-only switching cannot change
burned-in video captions or spoken audio. Supply a matching rendered variant or
reviewed selectable caption/audio tracks; declare availability truthfully.

Unavailable locale: retain the current working version and explain availability
in the parent controls. No live paid generation from a child's language tap.
A parent-authorized Red Dog language intent resolves to the same locale selector;
a UI command hook is not proof of connected voice or backend execution.

## Discovery, identity and privacy

The general Mall shows EDUIT; EDUIT shows its educational collections/children.
Episodes remain records inside their collection. Parent FoundUp, collection,
episode identity and UI tile index are distinct. Scope filtering must cover
projection, search, suggestions, Next, restored state and Red Dog discovery.
Protected content still needs real authorization; filtering is not security.

Use existing PWA assets/service-worker ownership and product adapter boundaries.
No second installable shell. `eduit.org` is a separate origin from foundups.com:
service-worker scope, browser storage, sign-in and offline cache do not transfer
merely because source code is shared. Verify deployment and account handoff;
keep optional child progress on device, separate from general Mall history.
Never send child play records to Memex, model training or agent memory.

For parents is the boundary for account, purchase, reports and general-Mall exit.
Its exact gate must be implemented and tested; a label alone is not a parent gate.
Reuse existing account/payment owners only after verifying actual capabilities.
No credentials, authoritative entitlement or payment decisions in browser storage.

## Premium creation, quotas and ratings — specified, not activated

012's latest clarification: **the landing is the first tile**, not a separate
marketing product. Play FoundUps is the shared Mall; Play EDUIT is its education
projection; Us Story Time is a collection/creation experience within EDUIT.
EDUIT has independent identity/content/domain presentation while sharing the
platform. Each created episode pairs a video with an educational game.

The landing exposes **Create a story** for eligible members in the adult creator
area. Premium creation opens the existing Shorts/Kids editor workflow; it does
not create a second editor. The current review page is read-only and the local
editor is loopback-only: neither is a public multi-user creation service today.
Creators describe a story to Red Dog, review the structured story/learning plan,
preview the video and game, then revise. Voice, drawings and autonomous dispatch
remain integrations to qualify, not assumed live features.

Separate entitlements:
- Free viewing/play: released starter episodes and unlimited practice.
- Library membership: earlier $4.95/month proposal; contents/price unqualified.
- Premium creation: capped generation/render jobs or credits; tier price, cap,
  renewal, failed-job charging and overage policy are undecided. Do not promise
  unlimited AI work for $4.95 or silently equate library access with creation.

Use the existing billing/quota/admitted-job owners once verified. Before work,
show the parent the cost/credit estimate; reserve once per job, reconcile actual
outcome, and prevent retries from double-charging. Unknown paid outcomes require
reconciliation, not blind re-execution. Quota exhaustion saves the draft and offers
an adult renewal/upgrade path; it never removes already-unlocked child practice.
Do not add a parallel wallet, payment API or browser-authoritative entitlement.

Each saved creation becomes a **private draft tile** in its creator's EDUIT
collection. Shared catalog publication follows rights, educational/content,
playability and independent output review, then explicit creator publication.
Draft → reviewed → published → withdrawn are proposed lifecycle semantics;
withdrawn/unavailable episodes cannot remain in Next queues or stale projections.
A tile references stable episode/revision assets rather than duplicating media.
User-created games use reviewed activity templates/adapters, not arbitrary code
executed in the shared browser origin. Branching/custom game authoring is later.

012 requested episode ratings. The inspected Mall/pfmall interfaces do not expose
a reusable episode-rating API; simulator investment ratings are not a substitute.
Resolve the owner before implementation. Proposed ratings concern the episode,
not the child. Keep parent feedback, editorial educational review and aggregate
popularity distinct; no single count proves educational effectiveness. Specify
who may rate, duplicate/abuse controls, sample count and moderation before launch.
No public child identity, open child chat or purchase prompt in the game.

Optional faster challenges are independent of learning/progression. Keep untimed
practice. Parent reports, if added later, compare game-specific personal progress;
no IQ, diagnosis, age-percentile or talent claims. See the README's existing
local-report boundaries. Memory Horizon remains a separate future integration.

## Verification and release gates

1. One tile opens the correctly paired video/activity/version; unknown IDs fail
   safely; no duplicate FoundUp identity or cross-collection Next.
2. Video above idle game; sequential audio; Next/retry/empty/error states work.
3. Existing gestures and explicit arrows preserve context and return position;
   no leaked handlers, background game timers or global navigation regression.
4. Locale cue timing, script, sound word, captions and narration reviewed together;
   missing-language fallback honest; no stale-language audio after switching.
5. Public child play and parent controls use explicit admission boundaries;
   no accidental account prompt during free play or unscoped recommendations.
6. PWA/device/offline/update tests validate actual cache/version consistency.
   Offline assets do not imply offline billing verification.
7. Actual rendered output, sound and gameplay independently reviewed; public URL,
   TLS and media delivery verified separately from source merge.

## Retrieval evidence and next-session entry

Read EDUIT README → this architecture → INTERFACE → ROADMAP → DEPLOYMENT.
Then retrieve shared Mall/Red Dog contracts and Kids Episodes before implementation.
Existing NAVIGATION's `kids episodes foundup` entry leads to that module README,
which links here. The EDUIT structured-memory bundle also retrieves its canonical
README/INTERFACE/ROADMAP. Keep decisions in these files, not a duplicate memory DB.

Run the governed helper from the selected checkout with module_hint
`modules/foundups/eduit`, include_bundle=true and must_include containing this
path. See `holo_index/CLI_REFERENCE.md` for the exact accepted request contract.
The docs pass used lexical retrieval: freshness UNKNOWN, index gap true; direct
source inspection supplies only baseline-specific evidence. Do not call this
semantic indexing or Memex ingestion. Exact-main semantic maintenance belongs to
the existing post-merge controller/admitted WRE owner; no raw reindex or authority
reset from this task. Recheck CURRENT/no-gap evidence after that owner runs.

Next bounded implementation: add the EDUIT episode adapter/detail contract to
existing Mall owners; keep the first story free, English, and one episode. Bind
video/game layout and arrows, then verify gestures/return lifecycle. Language,
membership and reports follow separate tested slices. No new story generator,
payment backend, PWA shell or autonomous worker is authorized by this document.
