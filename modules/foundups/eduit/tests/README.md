# EDUIT test inventory

Run `node --test modules/foundups/eduit/tests/*.test.mjs` from repository root.

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
