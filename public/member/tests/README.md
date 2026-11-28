# Member Mall tests

`node public/member/tests/mall_projection_routing_vm.mjs` executes the shared
contribution presentation predicate and actual dock handler. It covers public
Mall roots, HPC dedicated/admitted preview routes, admission/member owners and
forged DOM scope, preserving the existing no-submission/eligibility boundary.
These controlled VM checks establish no real membership, browser layout or
physical-phone playback result.

## v26 settings continuation — 2026-11-27

Keep the original72-row defensive phone suite intact. The additional settings
matrix runs in its own240-second CI gate, through the same existing --case API:

    python -B public/member/tests/mall_phone_ui_browser.py --case settings-close-recovery --case dock-refinement --case global-autoplay --case desktop-autoplay-startup --case non-hpc-plus-swipe

non-hpc-plus-swipe preserves the existing ordinary Mall/VOTE + upward gesture
and separate tap; HPC opens only the type picker. The additional matrix budget
is bounded240s; all original gate deadlines and case assertions remain intact.

CI retains the full-phone and settings JSON reports under distinct filenames.

settings-close-recovery covers320/414/390/402 widths, changed/no-change Close,
Dock + reopen, side tap exclusion, native modal/inert/scroll/pointer state,
post-Close taps, scrolling, focus and reload persistence. Keyboard selection is
used only to isolate initial modal setup; post-Close navigation uses taps.
WebKit DOM scrolling is labeled separately from Chromium hit-tested touch.
The old side-entry baseline is preserved as incident evidence, not a surviving
settings route. A one-time physical freeze is not asserted repeatable.

dock-refinement checks resting/focused/expanded dock and iframe non-overlap,
44px targets, an opaque badge with sampled logo contrast, dock swipe vs tap, First/Last persistence, independent dog/campaign
hit areas and navigation. Image/Podcast are asserted disabled, not faked.
global-autoplay tests visible automatic continuation in three presentations,
intentional Next when off and hidden pause. desktop-autoplay-startup also checks
stored off/on startup and deliberate Play when off. All provider events here are fixtures.
clean-video-gestures uses the reachable app sidebar for Full Video LEFT and
pinch. It does not prove gestures originating inside a YouTube iframe or on a
physical iPhone. Real provider time and physical tests require separate receipts.

## VOTE typed media qualification — 2026-11-25

The existing `mall_phone_ui_browser.py` adds `vote-native-cards`,
`vote-native-desktop` and `vote-reduced-motion`. The shared local route serves
the seven canonical module payloads, including MP4 byte ranges. Media is not
mocked: Chromium must decode 480×562 video and advance time; unsupported native
sources must report the image-animation fallback, demonstrate changing frames,
pause to a stable still and retain null media time. Both paths exercise cleanup,
the common stage, two records, search, expansion/return and motion changes.
Windows WebKit is not physical Safari or installed-PWA qualification.

Run these with the repository-approved bounded environment, then the full
existing suite and state/boot/catalog/worker regressions. Browser hashes include
the canonical VOTE catalog and six assets. Existing controlled YouTube fixtures
remain distinct from real-provider acceptance.

## Home/dock and hidden Next qualification — 2026-11-25

`mall_phone_ui_browser.py` adds `hpc-home-shared-desktop-dock` and
`tucked-next-stays-hidden` to the existing matrix (66 rows with defensive
history). It checks fresh Windows TV, exact shared-dock identity below the app
queue, live filtering/Enter selection, scoped Home/reload/resize, gated grid
Add Video and a single actions plus. Hidden right-swipe input advances exactly
once without provider creation/cue/load/play; tap materializes paused and
explicit visible Play advances fixture time. Chromium uses CDP touch and
WebKit uses synthetic touch; neither is physical iPhone evidence.

`mall_queue_callbacks_browser.py` preserves existing cases and adds hidden
paging, empty/error pages, no duplicate request, filtered first/end boundaries,
and stale-page cancellation after restore/close/new selection/scope. Existing
preference VM covers all four tucked choices, legacy migration, explicit saved
next/reveal and scoped presentation isolation. Real YouTube and delivery are
separate gates; provider fixtures cannot close those checks.

## Clean video gesture qualification — 2026-11-23

`mall_phone_ui_browser.py --include-defensive` adds `clean-video-gestures` and
`theater-clean-control-regression` while preserving previous cases (62 rows
across Chromium/WebKit). It checks app-only chrome removal, hit-tested external
full-height grips, provider minimum dimensions, full-video explicit Next with
autoplay off, filtered/multipage/end queues, menu Save/Share/Enter, caller focus
and original scroll, in-viewport tucked Next/reveal, Restore/no-action and
manual Play. Chromium injects real CDP touch input; WebKit touch events here
are synthetic. Neither is a physical iPhone or native-provider fullscreen pass.

Run `node public/member/tests/mall_local_activity_vm.mjs` for opt-in events,
getter-safe field projection, canonical diagnostic enums, deduplication,100-entry
bound, listener lifecycle and absence of network/persistence/mic/model work.
The existing phone CI invokes it; preferences (19), nested probe diagnostics (7)
and the original queue/policy/worker suites remain required. The new preview
host family is `play-v26-gestures` and its UI says Build v26 · Gestures. Keep
real YouTube, audible output, installed-client migration and physical-device
receipts separate from mocked provider and emulated-layout evidence.

## Floating control continuation — 2026-11-22

`mall_phone_ui_browser.py --case floating-frame-controls --case dog-and-camera-actions`
checks responsive minimum provider size, moving the same frame, full-height
restore, hidden pause, direct Full Video and unavailable-next-clip recovery,
independent gesture returns, in-page unavailable Red Dog and the bounded camera
caller URL. The desktop unready-return case also exercises the same options
dialog while its regular dock is hidden. Use the full `--include-defensive`
selection for shared shell/desktop/phone regression.

Playback actions relocated from floating chrome are exercised through Video,
including its persistent grip alternative; desktop theater retains its existing
Back owner. The media-policy fixture still forces actual sub-200px geometry and
asserts start refusal, preserving its original acceptance. The preference and
routing VMs qualify read-only migration, independent choices, camera URL bounds
and the explicit controls-preview host family. Existing account/product modes
remain separate regressions. All provider and camera requests are controlled;
these commands do not qualify real speech, AI, iPhone playback or camera return.

With Chromium and Python Playwright installed, run
`python -B public/member/tests/mall_guest_conversation_browser.py` from the
repository root. It drives the HPC phone dock and real dialog at 390×844 using
the scoped-video fixture's local assets. The guest API is intercepted. The
test checks consent, the extension-owned FoundUp breadcrumb, draft staging
without sending or overwriting text, the visible reply after Send, withdrawal,
and clearing the transcript. No provider or cloud service is required.

Read [TestModLog.md](TestModLog.md) before extending a fixture. It records the
existing suites, historical results and their limits; those results are not a
fresh test run.

## Current v23 qualification

The public Mall uses the existing six-item discovery pager and shared player.
Selecting a video-backed card replaces the all-Mall field with that source's
video grid. Portrait floats above the field; compact landscape retains the
floating stage with a clear browsing region beside it. Back to Mall and the
selected-scope logo restore browsing; the ordinary logo retains Member Portal.
Only Catalog order is offered because per-video popularity is unavailable.

Use the existing Python 3.12 Playwright runtime without installing dependencies:

- `node public/member/tests/mall_discovery_pager_vm.mjs`: bounded requests,
  schema/cursor/generation checks, retry, cancellation and no cross-lane fetches.
- `node public/member/tests/mall_product_state_vm.mjs`: cache generation,
  requested-only public pages, offline failures and unrelated cache preservation.
- `python -B public/member/tests/mall_public_tv_browser.py`: actual public boot,
  selected-only TV, network batches, queue and navigation/rotation regressions.
- `python -B public/member/tests/mall_queue_callbacks_browser.py`: delayed queue
  completion versus native Pause, query, hide, tuck, close and new selection;
  provider-control/browser-zoom and explicit chrome gesture boundaries.
- `mall_scoped_video_browser.py --player-policy`, `--header-only`,
  `--discovery-cards`, `--entry-regressions`: retained HPC, header, cards,
  entry gates, controls and state. The default legacy runner remains separate.

Source hashes and final commit bindings belong in each run receipt; a command
listed here is not a pass. Local routes, provider events and account state are
controlled fixtures. Real YouTube playback and physical Safari/PWA on Wi-Fi and
cellular remain separate. A physical browser must show advancing media time.

### Scoped video (historical full-suite coverage)

Run `python -B public/member/tests/mall_scoped_video_browser.py` with the
existing Python Playwright Chromium and WebKit test runtime. It serves the real
shell from local files with a 31-video fixture and controlled provider events.
The test covers vertical batching, top-anchored floating playback over a
scrolling grid, swipe-right edge tuck and edge-handle restore, intentional
pinch-in/pinch-out transitions with accessible button alternatives, one active
provider iframe across switches and WikiTube sequential advancement, bounded
error recovery, Back and Escape, deep Vote return, orientation, diagnostics and
manual Play at 320 px. The desktop cases cover first-video startup,
filtered queue advancement, keyboard selection, breakpoint continuity and
civic-resource return. The phone cases check the selected install manifest,
options, scoped search, fixture dictation and Red Dog return. The member case uses controlled Clerk and Firestore responses to check open
guest discovery on `play.foundups.com`, `Enter FoundUp` handoff through the
`foundups.com` Member Portal (`?enter={foundup_id}` -> sign-in -> invite gate ->
admitted FoundUp entry), scoped HPC sign-in return, admitted theater, and the
public discovery link.
`node public/member/tests/mall_product_state_vm.mjs` covers v23 installation,
obsolete Mall cache retirement and scoped offline behavior. Real YouTube time
progression and physical-device gates are separate in the
[incident](../../../modules/foundups/pfmall/MEDIA_PLAYBACK_INCIDENT_HPC.md).

### Member poster grid

The same browser suite opens the ordinary invited route with the real catalog.
It checks a fresh eight-column grid at 1440 × 900, no media frame on hover,
one shared player from inline to full view, queue filtering and idle submit,
manual Play for dense tiles, quick view, saved rows and wide touch entry.
The phone case checks inline playback in the selected card, continuity into
the full viewer, native horizontal touch scrolling in Chromium, and visible
queue search in portrait and landscape. It exercises swipe on plus, hold
and release on Red Dog, the square Stop in Red Dog's position, and dictation
cancellation using a local recognizer fixture. It also verifies that a long
transcript wraps, stays editable, and preserves the active provider frame.
The bottom dock also checks AutoPost and
keyboard fallback. The Play root uses the normal invitation and sign-in
path. The suite checks that
Escape restores focus and scroll in the expanded Move2Japan lane and that
Ctrl+wheel returns to the browse position. Account and provider events use
fixtures.

### Physical iPhone playback

Use a physical iPhone with Safari and a Home Screen install of the same
diagnostic preview. BrowserStack Live also supports this workflow on
provisioned real devices. The preview uses the regular Mall, its existing
manifest and the first HPC Short. From **+**, **Copy playback result** reports
the page mode, iframe dimensions, player events and advancing media time.
**Compare with the official YouTube embed** opens the same clip on the same
origin with YouTube's Play control. Copying is an explicit user action.

For an isolated Hosting preview, stage
`modules/foundups/pfmall/tests/fixtures/hpc_iphone_playback_probe.js` as
`public/member/playback-probe/probe.js`,
`modules/foundups/pfmall/tests/fixtures/hpc_iphone_playback_reference.html` as
`public/member/playback-probe/reference.html`, and a sanitized
`public/member/playback-probe/deployment.json` (`source_sha`, `channel_id`,
`hosting_version`, `mall_build`). Load the deferred probe
script only in the staged member document; the committed shared document has
no probe loader. Staged probe files and that injection remain preview-only.
`reference.html` accepts strictly
allowlisted `?v=<11-char Short ID>` (8 admitted HPC Shorts + 4 diagnostic-only
Shorts) and `?host=youtube|nocookie` (`https://www.youtube.com` vs
`https://www.youtube-nocookie.com`), retains selection across `Mall <-> official
embed`, keeps all probe controls below `#hpc-probe-embed`, and separates
`SW controller` from `Mall caches seen` and official `101/150` embed refusal
from screen-observed `LOGIN_REQUIRED` prompts. The fixture sources live outside
the Hosting public root. Hold the phone and
network constant across the browser, Home Screen and official-embed cases.

Let the first Short advance for a few seconds. If it fails, capture the
provider event after the load timeout and test Play inside the official
embed. In Safari Share, use **Add to Home Screen** and enable **Open as Web
App** when offered. Check that the second receipt says **Home Screen web
app**. Record the actual phone and iOS version separately from the
browser-reported string. A provider `playing` state and advancing time
qualify playback. Desktop and simulator results remain separate evidence.

## Public directory and gateway owners

- `test_route_contract_bridge.py` covers the canonical public `/f/` directory,
  landing aliases, public projection isolation and protected app handoff. Its
  existing Node VM executes the actual inline `/f/` owner with controlled DOM,
  history and fetch. Extend this fixture for public search behavior.
- `../../../modules/foundups/pfmall/tests/test_gateway_roc_shell.py` owns the
  homepage navigation, framing and existing gateway contracts.
- `../../../modules/foundups/pfmall/tests/test_gateway_terms_gate.py` owns the
  existing admission path; public directory discovery does not grant admission.

Other member behavior belongs to the existing field, planes, concierge, product
state and media tests listed in this directory and in the TestModLog. Reuse the
nearest owner before adding a test file. The separate projector suite owns
registry-derived public fields and committed projection parity.

## Focused execution

Run from the repository root with the declared environment dependencies and
Node on PATH (the route fixture also recognizes the standard Windows Node path):

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
python -B -m pytest public/member/tests/test_route_contract_bridge.py modules/foundups/pfmall/tests/test_gateway_roc_shell.py --import-mode=importlib -o addopts= -p no:cacheprovider -q
```

Use a scratch `--basetemp` outside the checkout. These controlled local tests do
not prove deployed routing, real browser layout, authentication-provider
availability, token deployment, liquidity or trading.

## v26 phone qualification

The v26 candidate freezes v25 as a comparison. `mall_product_state_vm.mjs`
executes the actual v26 worker, including direct v18/v25 cache retirement while
preserving unrelated cache bytes. `mall_admission_preferences_vm.mjs` tests typed,
expiring single-use review intents and video preferences; it grants no authority.
`mall_browser_ai_pilot_vm.mjs` verifies the explicitly confirmed 41-byte WASM
fixture and cancellation/hash limits; this is not a model or device qualification.

Physical iPhone 11 acceptance uses a fresh v26 origin: compact Play header and
filters/account access; HPC banner to Hasan's campaign, separate Mall return,
Voice Contact Congress; exactly one bottom Search Dock through expand/collapse
and Back. Then use one genuine tap and three distinct real YouTube clips with
two natural transitions. Record IDs, advancing time, sound/mute, provider errors,
Safari versus installed PWA and network context. A fallback tap is not a
continuous-playback pass. Fully hidden/dismissed playback must pause.

## Playback-probe release metadata

Use `node scripts/tests/hpc_preview_metadata_vm.cjs` from the repository root.
The pure `scripts/hpc_preview_metadata.cjs` factory/validator derives the build,
discovery generation and probe digest from actual candidate assets and binds both
source fields to the resolved commit. A tracked JSON cannot contain its own
commit SHA: generate the staged record after resolving that commit, then include
its bytes/hash as explicit derived release metadata in the reviewed manifest.
Always regenerate it, even when it is unchanged in the Git diff from a preserved
Hosting baseline. Never substitute an old channel, source, build or Hosting ID.

`hostingVersion` must come from the new allocation when known; otherwise the
record says `unverified`. `validateMetadata(..., {requireHosting:true})` refuses
an unknown identity. This contract checks coherence, not the authenticity of a
caller-supplied release identity or successful publication. Retain independent
Hosting/readback and unsigned asset-parity receipts. Compare served runtime,
metadata, worker and release receipt separately before investigating phone cache.
The frozen v26 discrepancy and exact historical provenance are recorded in the
TestModLog; no physical-iPhone result is inferred from those HTTP observations.

## Camera focus return qualification — 2026-11-28

Run through the approved bounded environment:

    python -B public/member/tests/mall_camera_return_browser.py

The existing scoped fixture, actual Mall shell/projection and a link-only
controlled AutoPost receiver cover 23 browser cases per engine (46 rows).
Cases include 414/402 positive query/scroll/Camera return, public Play, storage
write denial, stale unsupported outbound state, one-shot reload, malformed,
expired/future/mismatched/oversized hints, unrelated storage, read/remove failure,
typing/frame focus, modal/hidden/inert/disabled/offscreen targets. All network is
intercepted; source hashes must remain stable and page exceptions fail the row.
The own-key removal binding observes the producer before navigation; no pending
document evaluation or delayed response is used to prove retirement.

Two additional source-extracted callback-ordering rows run in Chromium/WebKit
JavaScript with controlled storage/frames, not real navigation. They cover an
empty mount followed by departure, replacement of a pending return by a newer
departure, and the matching one-shot return. The default report totals 48 rows;
`--case source-ordering` runs only those two. This regression failed before the
snapshot/equality fix and passed after. Existing browser assertions stay intact.

The existing HPC workflow adds this gate and its source hash without removing
or weakening earlier gates. A separate composed check uses the compiled AutoPost
camera-only build: four phone rows restore query/scroll/Camera focus; two desktop
rows retain theater return, with WebKit BODY focus explicitly unqualified.
Neither the link receiver nor synthetic persisted-pageshow covers native BFCache,
real capture, physical iPhone, provider playback or an arbitrary/private caller.
