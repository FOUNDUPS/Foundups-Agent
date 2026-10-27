# EDUIT test history

## 2026-10-26 — Collapse continuity

Existing inventory: `storytime.test.mjs` covers ordered inputs, wrong target,
miss/retry, practice and capped clock steps, plus shared movie/game staging.
Extended that suite (five cases total) to verify fixed soil identity, four
family reactions before roof occlusion, THUMP timing, complete chamber removal,
retained pocket and front-facing survivor. Old opacity-based assertions hid
rather than verified obsolete geometry; replaced with state/ordering checks.
Run: `node --test modules/foundups/eduit/tests/storytime.test.mjs`.
Actual encoded frame inspection remains separate from source/DOM assertions.

2026-10-26 approach iteration: existing scene case now checks wake on second
step, increasing step-word sizes, three SNIFF events, final compression cue,
intermediate turn parameter, and preserved occlusion. Review control retained.


## 2026-10-26 — Full-timeline rescue milestone

Replaced cue timeout with fixed 15s world clock, sequential five-character rescues,
slower parents, visible travel and game-over/retry. Removed shelf and tap markers;
reused Mall pinch engine with viewport-focus fallback and safe-area layout. Fixed
local SVG references in whiteboard snapshots. Tests cover no input, selection lock,
all five saved, late arrivals, reset and shared collapse/learning cues. See
[review contract](../docs/RESCUE_GAME_REVIEW.md) for boundaries and RSI lessons.


## 2026-10-26 — Touch/mouse viewer audit
Recovered latest deployed creative source; replaced flag emoji/text with local
SVG images and accessible labels. Added standalone manifest/icons and bounded
UI-only service worker. Pointer cancellation and safe-area layout strengthened;
locale selection pauses game. Mall mounting/physical-device acceptance remain
separate. See docs/TOUCH_MOUSE_PWA_AUDIT.md.


## 2026-10-26 — Home Screen launch and panel focus
Replaced viewport-less standalone redirect with a projection of the same viewer.
Each panel now owns expand/collapse. Added WebKit pinch adapter over Mall gestures,
pinch tap suppression, viewport rotation pause, safe-area sizing and inert focus.
Fourteen focused checks plus phone/tablet viewport harness; actual iOS remains
unverified. Independent CLI/resize findings repaired. See HOME_SCREEN_LAYOUT_REPAIR.


## 2026-10-26 — Preschool iteration

Existing inventory reviewed before extending storytime.test.mjs with font-size
independence from tremor.15 Node cases pass. Added separate real-DOM controller
harness for fullscreen pause, mark/undo/clear/share, switch, repeat and lock
(20 assertions); synthetic pointer limitations explicit. See tests/README.md
and docs/PRESCHOOL_VIEWER_REVIEW.md. No mirror-only test suite added.

## 2026-10-27 — Slow rescue
Extended existing storytime.test.mjs, no duplicate suite:18 total Node cases
passed for60s no-input ending, multi-tap wake locks, deliberate all-five rescue,
late arrival/frozen lost pose, dozing, practice and score uniqueness/bounds.
Browser harness extended with64px rendered bounds, rail containment, reset and
practice recovery. See SLOW_RESCUE_REVIEW for actual browser acceptance.

## 2026-10-28 — Learning shell
18 Node cases and 53 security-gate regressions pass. Existing browser fixture
extended with About/How pause/state and adaptive control measurements; image
size assertion now waits for decode, tablet comparison tolerates subpixel rounding.
Scoped rendered outcomes and device limits: ../docs/LEARNING_SHELL_REVIEW.md.


## 2026-10-28 — Batch RSI planning boundary
Four stdlib unittest methods pass with per-criterion failure subtests; existing
18 EDUIT Node tests pass. No runtime, visual/audio or forward-transfer proof.
Run `python -B -m unittest modules.foundups.kids_episodes.tests.test_tile_batch -v`.
The existing Kids Episodes workflow collects this suite through pytest; local
pytest was unavailable, not reported as passed. See TILE_PRODUCTION_RSI in EDUIT.
