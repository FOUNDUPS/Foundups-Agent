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
