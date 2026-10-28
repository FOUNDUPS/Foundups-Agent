# EDUIT Agentic Learning Game Engine — architecture contract
Date: 2026-10-28. Status: architecture proposal, not a shipped autonomous engine.

## Authority and purpose
EDUIT is the educational FoundUp; Storytime is one experience, Evolution one learning path, and WATCH → PLAY → VERIFY one complete tile. The engine composes reusable, reviewed learning objects and interaction modes across tiles. 012 provides corrections; 0102 translates them into proposed code, reproducible tests, skill updates and governed WSP97/RSI worker tickets. A correction is evidence, not automatic authority to rewrite live child-facing software.

## Learning object: multimodal, versioned
A concept such as `sound.thump` includes: semantic ID; locale-specific display word; reviewed audio effect; reviewed spoken-word TTS asset; synchronized visual cause; caption; matching choices; tracing glyph/path where supported; age band; content rights; assessment rubric; source/version; and review status. Do not assume a sound effect and speech audio are the same asset.

### Three-part cue timeline
1. **Sound**: impact Foley (THUMP) at time T.
2. **See**: visible `THUMP` synchronized at T or a small authorable offset.
3. **Hear**: localized voice says the written word at T + authorable delay, after the impact transient, with ducking to avoid overlap. Test timing in milliseconds on actual devices; no unsupported fixed magic offset. Keep captions visible for silent play and accessible alternatives.

For counting: on each successful arrival show `1 — one`, speak `one`, highlight the digit, then fade; increment through five. Review Japanese/Portuguese/Spanish translations and voice assets independently. Retain familiar sounds while layering numbers or family labels.

## Family casting
Five characters: **Mom, Dad, Brother, Sister, Baby**. Baby must be visibly smaller; Brother/Sister have consistent identity and distinguishing visuals, while both parents remain larger. Child-friendly terms are locale-reviewed; **MAMMA** (M-A-M-M-A) is the fictional mammaliaform umbrella name, not a substitute for Mom. Do not infer gender from size alone. Character visual roles are independent of starting position and seeded cave arrangement.

## Reusable interaction primitives
- **Observe**: synchronized effect + word + speech + visual cause.
- **Choose**: find the picture/word associated with a sound.
- **Match**: link two approved representations of a concept.
- **Trace**: use the existing whiteboard/drawing owner to trace a large reviewed glyph/word, with touch, pointer and accessible non-tracing alternative. Tracing correctness is forgiving and cannot depend on handwriting biometrics.
- **Count**: count rescued characters 1–5 as they arrive.
- **Recall**: recognition of a previously introduced object; optional, low-pressure.
- **Timed recognition**: optional later mode, never a default or prerequisite for preschoolers.

Each mode consumes a validated object pack and emits minimal local, parent-clearable outcomes. Game points/stars are awarded through play; **no Earn Stars button**. Replay is the primary bottom-right pulsing action, respects reduced motion, varies approved objects and safe character positions, and may increase speed within tested bounds. VERIFY is a learning function, not necessarily a separate interrupting panel; independently validate a suitable integrated format for age three. Round counter tracks three completed rescues without forcing an exam.

## Engine contracts / hooks
- `ContentCatalog`: versioned reviewed learning-object packs and locale assets.
- `LessonSelector`: deterministic, seeded selection, familiar/new balance and optional local spaced review; never silently substitute unreviewed content.
- `CueScheduler`: aligns Foley, displayed word, TTS speech, animation, pauses and caption timing; cancel on replay, locale change, tab hide or stop.
- `InteractionRegistry`: approved modes (observe, choose, match, trace, count, recall); each declares input, accessibility and scoring contract.
- `GameAdapter`: maps Storytime scene/cast/rescue events to concept events, not hard-coded content in game physics.
- `AssessmentAdapter`: records simple recognition evidence, separate from rescue stars; no IQ or mastery inference.
- `ProgressStore`: guest-first local progress and parent-controlled deletion; cross-device parent account is future authorized work.
- `RSIWorkOrderAdapter`: emits sanitized editor corrections, synthetic test failures and review receipts to existing FAM/WRE/Prometheus pathways; no direct child telemetry or self-approval.
- `TileCatalogAdapter`: references PF Mall's existing tile, released/locked status and learning-path metadata; do not create a parallel mall.

## Agentic RSI boundary
**Design time:** AI workers propose content, code, tests, locale/rights checks, and skill revisions; independent reviewer accepts/rejects; WSP97 verification and CI gate PR → squash merge → exact-main verification → deployment. **Run time:** browser executes deterministic, approved packs without autonomous code edits or unrestricted model generation. Later agent hooks require policy, parental privacy, sandboxing and human-reviewed release gates. Record which 012 correction produced which change and how it transfers to the next *different* tile; do not claim autonomous RSI exists solely because this contract exists.

## Preschool safety and UX
Large thumb-reachable bottom-right replay/close, scrollable modals, selected-language contrast, fixed score sizing across locales, low-volume phone-speaker tested effects, non-graphic SQUISH, optional sound, reduced motion, no timed pressure, accessible alternatives, and no forced sign-in. THUMP impact → CRUNCH soil break → lift → everyone safe → replay must finish reliably.

## First implementation slice / independent tests
1. Audit existing Storytime engine, Foley/cue sources, TTS pipeline, whiteboard, Skillz, and PF Mall integration; reuse owners.
2. Define five reviewed concepts per bank (sounds, family, numbers, actions) and synchronized cue fixture; use only a few focus concepts per round.
3. Implement reviewed spoken-word playback with pre-generated localized assets and robust cancellation; measure visible-word/voice timing on mobile.
4. Make Baby smaller without breaking cave collision and test all five roles/rescues and the ending.
5. Add arrival counting, deterministic replay lesson variation and basic recognition; trace mode only after existing whiteboard integration review.
6. Freeze regression cases: locale parity, TTS unavailable fallback, overlapping cues, slow phone, muted audio, small speakers, replay reset, five rescues, round count, baby collision, and accessible tracing alternative.
7. Update EDUIT canonical docs, existing learning-content/interactive-review Skillz and ModLog; PR, CI, squash merge, main verification and deployed-site smoke test are separate receipts.

This document specifies the engine; no unimplemented feature is represented as shipped.

## Millisecond cue synchronization contract — P0 (2026-10-28)
Use **milliseconds** for all timestamps, offsets and acceptance measurements, on one monotonic clock. The THUMP event has three distinct outputs, in this order: (1) audible impact Foley, (2) visible localized word, (3) audible localized spoken word. Example **initial test fixture, not a proven perceptual optimum**: `impact_at_ms=0`, `word_visible_at_ms=80`, `spoken_word_requested_at_ms=220`; spoken onset must be measured rather than assumed to equal request time. Provide a configurable offset per locale/asset and an authoring preview with timestamp traces. Schedule preloaded audio against the same time origin where possible; browser speech synthesis can be a fallback but cannot promise precise onset timing. For reliable millisecond-level tests use approved prerecorded TTS assets with decoded audio and capture actual audio onset. Preserve a clear effect before the spoken word, prevent overlap via gain ducking, and keep the word visible through the spoken audio. Include visual-only/silent alternative.

**Instrumentation:** emit development-only `cue_started`, `foley_started`, `word_visible`, `speech_started`, `speech_ended` with elapsed milliseconds; report intended vs measured onset and jitter. Never transmit child session events to RSI. Verify THUMP, CRACK, SQUISH, SNIFF and CRUNCH, all supported locales, replay cancellation, background tab, muted devices and slow phones. The first milestone is one working THUMP event with recorded timing evidence, not merely a timeline in documentation.

## Scene-driven video/game parity decision (2026-10-28)
Current Storytime video is a prerecorded MP4 while the game is an interactive code-driven scene. They are NOT currently the same renderer. The target is one shared, versioned cue/learning-object timeline used by (a) an authored demonstration rendered and recorded to video and (b) the interactive runtime. Verify video playback against its recorded cue version; a static MP4 cannot dynamically adopt replay learning objects without rerendering or adding a synchronized overlay. The first proof must demonstrate THUMP effect, text and spoken word on both paths with measured millisecond offsets and device playback tests before deploying. Learning objects independently own scene anchors, safe placement bounds, scale, opacity, fade, voice and review priority. Repeated objects can become less prominent after verified recognition, but must remain available to revisit; do not infer mastery from a single game score. All authored changes must be checked on phone and tablet layouts. Prioritize this as a bounded Sprint 1 proof, then apply to Sprint 2 game completion and Sprint 3 pack variation. Record 012 corrections as development evidence in the existing RSI ticket/skill system.

## Picture → word → sound → recognition (2026-10-28)
For preschoolers, a concept such as dinosaur must be accessible before decoding text. A learning object may supply `concept_id`, `emoji_fallback`, `illustration_asset`, `written_form_by_locale`, `spoken_audio_by_locale`, `syllable_segments_by_locale`, `caption_template`, `cue_timing_ms`, `screen_anchor`, `safe_area`, `scale_range`, `opacity_curve`, `recognition_choices`, `revision`, `rights` and `review_status`. Syllabification is optional, locale-specific, educator-reviewed and not a claim of universal phonetic spelling.

**Narrative event:** read aloud “Long, long ago, there were [dinosaur picture]”; show the short caption with 🦕 replacing the difficult word at first; then briefly reveal **DINOSAUR** and pronounce the word, optionally showing educator-approved syllable chunks; fade to the picture. **Action event:** retain the distinct Foley → written word → spoken word sequence for THUMP. Both run on the same millisecond cue scheduler, with different event templates and a measured audio-onset trace. Never flash rapidly or require timed reading; respect reduced motion and readable duration.

**Recognition mode:** later show “DINOSAUR” with large visually distinct picture choices and ask the child to match the dinosaur. Award play points/stars without forced examination. Record only minimal optional parent-clearable local evidence; a single correct answer does not establish mastery. Reviewed illustrations should be preferred to platform-dependent emojis where a consistent shape matters. Validate phone/iPad wrapping, image fallback, speech interruption, locale word length and contrast.

**Authoring/RSI hook:** independent agents may propose placement and prominence using scene bounding boxes and learner-stage objectives, but must pass collision, readability, child-safety, rights and device-layout checks before the asset is approved. Repeated familiar objects can become less prominent while remaining available for spaced review. This is a specification; no dynamic picture-to-word engine is claimed to be shipped.

## Two imprinting sequences — exact preschool narration contract (2026-10-28)
**Narration: SEE → HEAR → FADE.** Show exactly one short phrase, without punctuation where appropriate: `long long ago`. After a configurable delay measured in milliseconds, play the localized narration “long long ago”; then fade the phrase out. Next, show `there were dinosaurs`; speak the matching sentence; then fade. Do not simultaneously display a long paragraph or require a child to read it. Sentence transitions should be paced for preschool comprehension and may be paused/replayed. Visible text must match the spoken words in the chosen language.

**Object association: PICTURE → WORD FLASH + VOICE → PICTURE.** During “there were dinosaurs,” show a dinosaur illustration/emoji behind or alongside the caption. Briefly bring the written word `DINOSAUR` forward in large, readable text synchronized with the spoken word “dinosaur,” then fade it back to the illustration. Flash means a gentle emphasis/scale or opacity transition, **never rapid strobing**. Preserve the object’s visible meaning when the word fades. The object placement, text size, duration, audio onset and fade are authored parameters and independently validated on phones and tablets.

**Action imprinting remains different:** THUMP uses **FOLEY → VISIBLE WORD → SPOKEN WORD**, with separately measured millisecond offsets. Narration uses **VISIBLE PHRASE → SPOKEN PHRASE → FADE**. Both are templates in the same versioned EDUIT cue scheduler, not hard-coded one-off video animations. Do not assume a universal optimal imprinting interval or claim proven memory effects without evaluation.

**Implementation/verification:** define per-event `template`, `start_ms`, `text_visible_ms`, `speech_requested_ms`, `speech_actual_onset_ms`, `emphasis_ms`, `fade_start_ms`, `fade_end_ms`, `image_anchor`, `locale`, `asset_revision`; instrument intended and observed timing, verify speech/text correspondence and replay cancellation, and use the same approved authored timeline for game rendering and any regenerated instructional video. The existing MP4 is static and does not acquire these changes until rerendered or augmented by a synchronized overlay.

## Clarification: scenic imprinting and recorded playthroughs (2026-10-28)
The working tile currently has a **video (WATCH) and game (PLAY)**. The third part, **VERIFY (test)**, remains unbuilt. Earn stars during PLAY; Replay is the end action. Two learning sequences: **narrative imprinting** = see short text → hear same words → fade; **scenic/action imprinting** = visible cause (foot collision and simultaneous physical shake/impact Foley) → prominent written sound word (THUMP/THUD, consistent with approved locale) → spoken word → fade. Align collision, vibration and Foley by actual scene physics; measure onset in milliseconds. The authored video should ultimately be a recording from the same code-driven game timeline. Future PWA playthrough capture/export and parent-reviewed website/YouTube upload require consent, moderation, privacy, reliable audio capture and explicit publication approval. Design reusable hooks now; autonomous RSI and child uploads are not enabled.
