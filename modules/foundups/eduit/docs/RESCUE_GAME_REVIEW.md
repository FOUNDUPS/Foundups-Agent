# Storytime rescue/viewer milestone — 2026-10-26

## Current accepted direction

Video above game, with no introductory prose. Learning words appear in the video and game;
the game has no visual tap markers. Child-facing controls are icons with accessible
names. Feedback is a separate mode that freezes the actual game, captures its scene
and state, and accepts pointer marks. Local save/copy works; automatic Red Dog
feedback ingestion is NOT implemented. No voice capture or child profiles.

The film has one scripted survivor. The game explores alternate outcomes with the
same world timeline: THUMP, sniffing cues, cracks, compression, foot lift, imprint.
At 9.6 seconds rescue closes; the roof compacts through 10.8 seconds. At 15 seconds
show Game over if none survived, otherwise the saved count. No input never skips
the collapse/reveal. Restart resets all five actors. A Next episode is not invented.

Three babies and two parents are rescuable. Select one, tap the root, watch travel,
then select the next. Selection stays locked during travel. Babies take 0.9 seconds;
parents 2.6 seconds. This makes saving five possible but harder. These are fictional
game mechanics, not developmental norms, lives lost across sessions, or intelligence
measurements. Large parents appear above the babies as stylized burrow depth; only the green
shelf was removed. Screen-space height is not a support requirement. Saved animals occupy the pocket, unsaved animals are occluded by earth.

## Ownership and boundaries

- Existing EDUIT `engine.mjs` owns deterministic state and actor timing.
- `scene.mjs` owns material, cast geometry and movie/game world effects.
- Existing Shorts `assets/kids_review/director.*` owns creator view and annotations.
- Reuse Mall `public/member/js/gesture-engine.js`, packaged unchanged. Pinch out
  expands; pinch in exits. Explicit expand/exit buttons and Escape provide fallback.
  Expansion is CSS viewport focus, not a promise of browser-native iPhone fullscreen.
- Responsive aspect ratios, dynamic viewport and safe-area padding replace device
  model detection. No decorative filler content is added to the child's scene.
- Private Sites staging is deployed separately from `storytime.eduit.org`; domain,
  Mall mounting, installed/offline PWA and authenticated Red Dog transport remain gaps.

## RSI correction record

| Observed failure | Correction | Acceptance evidence |
|---|---|---|
| Missing input immediately retried; world depended on success | Absolute world clock plus independently rescued actors | No-input game reaches imprint and ending |
| Creator page overloaded with prose | Two media panels, icon controls, hidden feedback tools | Browser layout inspection |
| Annotation review replayed a separate timeline | Capture exact game state and SVG at pause | Frame/state included in saved feedback |
| SVG sanitizer removed local use elements, losing characters | Preserve fragment-only SVG references, strip external/script content | Reopened snapshot retains cast |
| Green support line cluttered the cave | Preserve the approved depth composition and remove only the shelf | Render before/during/after |
| Visual corrections treated as proof of learning | Keep learning/phone/listening limitations explicit | No child-learning or autonomous RSI claim |

Retrieval used the governed lexical fallback: ok=true, freshness=UNKNOWN,
index_gap_detected=true. Existing owners were inspected directly. This is source
and manual review evidence, not semantic-index acceptance or WRE activation.

## Deferred browser-agent experiment

012 proposed an agent controlling each shrew. Record as an experiment, not an
installed capability. First expose bounded game observations/actions through the
existing admitted agent interface, with fixed seeds, budgets and reset/stop. Compare
a deterministic policy to a replaceable browser-capable model (Gemma is only a
candidate, capability/access unverified). Models never own physics, deadline,
outcome scoring or child data. No per-frame model calls in the POC. Evaluate causal
success, latency/cost, and failure recovery; next actual episode is the transfer test.

## Priorities (WSP 15 planning judgments)

1. P0: full timeline, rescue state, actual-frame feedback and view fit (needed now).
2. P1: real-device touch/audio and independent perception review, then next episode.
3. P1: authenticated feedback transport using existing Red Dog owner.
4. Deferred: Mall catalog mounting, memberships, multilingual variants, NPC models.

No artificial Next button, paid membership gate or AI-worker activation is included.
