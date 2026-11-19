# Preschool viewer iteration — 2026-10-26 JST

Revision `preschool-controls-10`. Source baseline main `c4e179c4`; existing Shorts
viewer and EDUIT scene/renderer owners extended. Audience direction is now ages
**3–4**, replacing the initial 3–6 target for this episode. This is a design target,
not child-comprehension, developmental or emotional-suitability validation.

## Delivered candidate

- Cream surround, warm yellow buttons, dark teal primary controls; 56px targets.
  Preserve all approved cast geometry and dark earth `#69472F` through collapse.
- Stateful game/video Play/Pause, direct fullscreen Video/Game switch, existing
  pinch owner plus per-panel expand/collapse. One audio source, paused view changes.
- Pencil freezes exact game state without leaving fullscreen. Undo, reversible
  Clear, Resume and picture capture stay in-panel. Structured notes remain in
  combined view. New capture/reopened records retain prior draft locally.
- Snapshot dialog contains a 1920x1080 PNG of scene plus current marks. Native file
  Share appears only when supported; otherwise the image can be screen-captured.
  No direct Photos write or automatic Red Dog ingestion is claimed.
- More contains Repeat video (default off) and Child lock. Lock hides adult tools
  and collapse, preserves play/switch/rescue; deliberate hold plus confirmation
  unlocks. It guards accidental touches, not OS navigation or adult identity.
- Larger English and existing localized sound words; SNIFF tracks the selected,
  moving or sheltered actor and avoids the parent's face in sampled film frames.
  Saved count is larger and on a cream badge; no scoring/analytics added.
- Same 15-second world clock, rescue deadline and sound events. No next story,
  game speed changes, ratings, Mall backend, membership or worker activation.

## Ordered audit and retained failures

1. Physics: increasing `cue.size` initially increased shake because it was shared
   with tremor amplitude. Rejected. Separate `shakeSize` preserves original motion;
   regression test compares transforms under font changes.
2. Continuity: cast, root pocket, soil and event timing preserved. Original WAV
   SHA256 `5eb91326c6a6890223208467bd1e364146268a34d34b2b957ca15d81e2f4a3a8`
   matches prior media provenance exactly. No new listening review claimed.
3. Education: typography enlarged from 30–60 to 48–80 scene units. SNIFF58 maps
   to about24 CSS pixels at390px width, versus14 previously. Durations unchanged;
   CRUNCH remains brief. Reading/mastery and tone for ages3–4 are UNVERIFIED.
4. Art: first encoded preview exposed Cairo ignoring SVG paint-order, darkening
   glyphs and placing SNIFF over a parent's lower body. Rejected. Explicit outline
   then fill rendering plus nose-side placement yields the same clear output in
   browser and encoded frames. CJK width bounds treated separately from Latin.
5. Interaction: reviewer found draft overwrite, missing fullscreen Clear and lock
   retaining drawing controls. Repaired. A first single-slot Clear undo failed
   Clear→draw→Undo; replaced with bounded chronological history. Second-touch
   cancellation also removes provisional ink/history.

Reusable lesson: separate visual emphasis from physics; inspect the encoded output
as well as SVG; test sequences of actions, not just isolated buttons. This is a
retained candidate improvement under the existing viewer-iteration skill. Next
actual episode is its transfer check; no autonomous RSI/training claim.

## Validation and grades

- 15 Node checks PASS (existing suite plus typography/physics regression).
- Browser harness:18 checks PASS at390x844 and844x390; expanded20 checks PASS at
  768x1024 and1024x768 after chronological-undo repair. Synthetic pointers test
  handlers only. Harness initially assumed PNG ready in600ms and failed; a bounded
  completion wait passed. No production sleep or timeout workaround added.
- Mouse hold/unlock confirmation exercised in browser; controls returned.
- Encoded video:1920x1080,30fps,15.000s. SHA256:
  `3116a33754e48e9a5f8abb2a6c7294d94ae8568669ec1d1cab29073e78b759c1`.
- Independent reviewer inspected12 encoded cue/transition frames and nose-side
  SNIFF closeup, confirmed continuity and readability, and reviewed repairs.
- Diagnostic grades: sampled English readability4/5; source/state continuity4/5;
  native input parity3/5. No aggregate score or claimed child learning outcome.
- Physical iPhone Home Screen/pinch, Photos targets, native-language perception,
  actual child use and a new auditory review remain UNVERIFIED. Browser dimensions
  and synthetic gestures are not physical-device acceptance.

The test-only `tests/director_harness.html` is served temporarily as `layout-qa.html`
for browser QA and excluded from published assets. Media is republished on the
existing Sites preview, not uploaded again to YouTube. Custom domain/DNS remains
separate. PR/deployment identities are reported by their owning service receipts.
