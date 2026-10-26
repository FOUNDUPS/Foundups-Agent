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
