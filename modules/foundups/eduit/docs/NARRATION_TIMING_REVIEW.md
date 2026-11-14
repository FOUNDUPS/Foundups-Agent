# Storytime narration reconciliation — 2026-10-28

## Scope and source
SOURCE-READ: reconciles open PR #2249 with main 913924c and handoff
01ff6c6. The conversation handoff remains the decision-precedence record.
This is a bounded implementation of narrative SEE → HEAR → FADE, not the
whole adaptive learning engine or proof of learning effectiveness. WSP15
allocation: C2/I4/D4/Impact4 = 14/P1; separate from quality ratings below.

Shorts owns the viewer and browser adapter (`story-narration.mjs`); EDUIT owns
`public/eduit/storytime/cue-scheduler.mjs`. The media clock drives five English
cues. THUMP's existing 9600ms effect is followed by caption at9680ms and speech
request at10400ms, leaving the transient clear. These are authored offsets,
not proven acoustic synchronization. The existing15s film is not rerendered.
Game60s/48s hazard timing, practice mode and language flags remain separate.

## Correction loop
- Paused initialization previously consumed first phrase; now only running,
  audible playback requests speech. Pause/seek/replay invalidate old callbacks.
- Independent reviewer identified buffering and user-volume bugs. Waiting and
  seeking hold voice; playing/seek completion release the hold. A changed volume,
  including zero, is preserved rather than overwritten when ducking ends.
- Visual review found `#video-panel {position:relative}` defeating fullscreen.
  Replaced with explicit fixed fullscreen positioning and regression bounds.
- Caption height now participates in fullscreen sizing; four game buttons wrap
  to two rows on narrow phones, with separate bottom-right exit space.
- Caption text at6500ms now describes waking rather than falsely claiming all
  characters still sleep during the visible danger sequence.

## Evidence and limitations
OBSERVED: Node26 tests pass, including7 scheduler cases and1 adapter lifecycle
case with injected speech callbacks. Existing game/render/gesture/PWA tests pass.
OBSERVED: browser fixture at320x568 passed30 pre-existing checks; 568x320 passed
33 checks including fixed fullscreen origin, caption/control separation and exit
nonoverlap. Actual browser playback displayed timed captions. Browser returned
zero installed voices and speech_unavailable; no actual narration was heard.
The adapter retains silent captions and visible voice-unavailable status.
Synthetic pointer events test handlers, not physical touch or installed iOS.

Optional `?timing` keeps at most300 trace events in page memory; no network or
persistent learner record. intended_ms is authored media time; observed_ms is
browser callback time. speech_started is not speaker/hardware onset evidence.
Native iPhone/iPad voice, offline voice, audio balance and acoustic jitter remain
UNVERIFIED. English-only narration is explicitly labeled; game language does not
claim to translate the movie. Precise recorded localized speech, object emphasis,
counting voice, assessment, gameplay recording and autonomous RSI remain roadmap.

Quality rubric (ordinal1–5, not WSP15): lifecycle4; responsive layout4 within
checked desktop-browser frames; learning correspondence3; real audio3 (missing
voice platform evidence). No5 or universal device acceptance claimed. Independent
source/test reviewer narration_review identified the two adapter defects above;
repaired test evidence retained. Forward-test cue lifecycle on the next actual
tile before claiming skill transfer. Baseline rollback: Site version11.

## Reproduction
`node --test modules/foundups/eduit/tests/*.test.mjs`
Serve existing director_harness.html as a temporary same-origin QA route; run
acceptance after each reload. Do not deploy QA routes. Review the actual shipped
root in addition to fixtures. PR and exact-main CI plus Site publication are
separate gates; this receipt alone does not assert merge/deployment.
