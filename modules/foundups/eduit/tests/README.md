# EDUIT test inventory

Use **Run full-story interaction regression** in the existing director_harness
for the title-start and actual elapsed-time all-page/movie handoff on both routes,
plus Pause/resume, later-page start, incidental tap and synthetic pointer
cancel/multitouch/swipe cases. It uses the real silent-play UI option, not a
forced clock. Separate CUA real presses and UI-TARS model-guided input receipts
live under outputs/storytime-playback-20261101; do not call synthetic dispatch
native touch or count static model inference as a completed playthrough.

Preschool book acceptance extends the existing director_harness storybook button:
all five pages at six sizes on both routes, rendered font/target floors, no
scroll/clipping and direct hit tests. Independent rendered/silent/voice-failure
receipts are retained separately; see TestModLog. Actual Home Screen launch is
not certified by an inner iframe or direct-origin viewport measurement.

App presentation extends the same inventory with scene-presentation.test.mjs:
canonical scale/world mapping, malformed presentation rejection, default-frame
identity, full-height leg entry/exit and matching skin sky/opening. Independent
app-menu/scene browser matrix verifies actual rendered hit bounds and real-earned
state through native menu, choices, Done/Escape, fullscreen and injected safe
areas. Cross-origin wrapper escape is a separate user-activated launch check.
Retain raw failures/repairs; no physical-device claims from synthetic events.


Run `node --test modules/foundups/eduit/tests/*.test.mjs` from repository root.

Current sleeve selection adds `choice-wheel.test.mjs` and `music-picker.test.mjs`:
keyboard/drag/programmatic-centering/rejection/teardown, explicit audio start,
Off, pause, source allowlist, late promise and playback denial. Current full53/53
passes; prior baseline Windows/scene failures were repaired against unchanged
acceptance. The existing director harness adds “Run character wheel checks”.
Credits/audio rights and physical listening are separate from synthetic tests.

- `storytime.test.mjs`: world clock, rescue outcomes, scene continuity, cue/locale
  invariants and typography independent of tremor physics.
- `layout.test.mjs`: gesture adapter cancellation/destroy, root projection and
  packaging CLI with fake media (not a real video review).
- `pwa.test.mjs`: manifest, cache bounds and flag/pointer contracts.
- `director_harness.html`: actual same-origin viewer controller acceptance. Copy
  temporarily to the packaged site's root as `layout-qa.html`, open through the
  managed preview, choose a viewport and run. Reload between runs. Uses synthetic
  pointer events with explicitly stubbed pointer capture, not native touch proof.
  Remove before publishing. Exercise real mouse hold/unlock separately.

See TestModLog and ../docs/PRESCHOOL_VIEWER_REVIEW.md for results and limitations.

Slow-rescue revision extends the same engine tests and viewer fixture with
score/sleep/practice/reset and64px bound checks. The optional live rescue button
uses real-time waits; cloud-browser suspension can exhaust them before the active
game clock advances. Treat that as inconclusive, never substitute a green engine
result for a completed browser round.

- `viewport.test.mjs`: execute the actual viewer viewport owner with missing API,
  normal-zoom offsets, rotation, foreground, and browser-zoom fixtures; assert
  both owners pause when bounds change. These inputs are not device emulation.
- `director_harness.html` phone matrix: both root/manifest entry at six dimensions,
  useful landscape scene size, >=64px controls, safe-area arithmetic, hit tests,
  one drawing rail and state preservation. First run the identical oracle against
  the retained published baseline; record a red control before candidate acceptance.

- `director_harness.html` **Run storybook visibility regression**: both root and
  inner director at390x844,844x390 and1280x900. Uses the actual Story/Skip/Close
  and explicit storybook Play controls, checks native-modal opening and bounds,
  no closed-dialog layout or narration, reopening, and resizing while closed.
  Run the unchanged oracle against original CSS before testing a repair. After
  replacing local CSS, reload with fresh assets and verify the loaded stylesheet;
  a cached original rule is not evidence about the candidate. This is browser
  layout/handler evidence, not physical mobile touch or acoustic acceptance.
