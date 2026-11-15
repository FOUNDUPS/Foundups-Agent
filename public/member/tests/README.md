# Member Mall tests

Read [TestModLog.md](TestModLog.md) before extending a fixture. It records the
existing suites, historical results and their limits; those results are not a
fresh test run.

### Scoped video

Run `python -B public/member/tests/mall_scoped_video_browser.py` with the
existing Python Playwright and Chromium test runtime. It serves the real
shell from local files with a 31-video fixture and controlled provider events.
The test covers vertical batching, playback in the selected tile's row,
one active inline iframe, immersive
promotion, Back and Escape, deep Vote return, orientation, diagnostics and
manual Play at 320 px. The desktop cases cover first-video startup,
filtered queue advancement, keyboard selection, breakpoint continuity and
civic-resource return. The phone cases check the selected install manifest,
options, scoped search, fixture dictation and Red Dog return. The member
case uses controlled Clerk and Firestore responses to check sign-in return,
invitation denial, admitted theater and the public discovery link.
`node public/member/tests/mall_product_state_vm.mjs` covers v16 installation,
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
`public/member/playback-probe/probe.js` and
`modules/foundups/pfmall/tests/fixtures/hpc_iphone_playback_reference.html` as
`public/member/playback-probe/reference.html`. Load the deferred probe
script in the staged member document. The fixture sources live outside
the Hosting public root. Use an online device and hold the phone and
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
