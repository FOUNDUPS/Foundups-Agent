# Storytime episode tile: child controls and creator feedback

Decision: 2026-10-26 JST. **SPECIFIED, not implemented by this documentation.**
Source inspected: `1cc7c7228991043ee513ef9f00854ff1e88f4bd1`, unchanged viewer
from the Home Screen milestone. This contract refines the existing
[episode architecture](EPISODE_MALL_ARCHITECTURE.md); it does not create a new
FoundUp, viewer, gesture engine, rating backend or autonomous worker.

## One tile, two views

One episode tile pairs a video and its game. Combined view puts video above game.
Either expands into the same episode's fullscreen view. A large video/game icon
switches directly between them without returning through the combined page.
Preserve video time, game state, locale and feedback draft across view changes.
Pause the departing surface first; the destination stays paused until Play.
Only one audio source runs. Switching never consumes unseen game time or resets
an attempt. The film's fixed survivor and the game's alternate rescues remain distinct.

Initial audience: ages 3–6. Use consistent SVG icons, accessible names, visible
focus and at least 48 CSS-pixel targets with separation. Keep the scene's aspect
ratio, safe areas and learning words; don't fill spare space with decoration.
Anchor controls to the panel in a reserved rail, clear of shrews, root and words.
Test portrait/landscape rather than guessing the phone model.

## Controls and gestures

| Action | Specified behavior |
|---|---|
| Play/Pause | One stateful button; show Pause only while running, Replay at completion |
| Video/Game | Large, distinct film/game icons; retain fullscreen and episode context |
| Expand/Collapse | Visible corner icon on each panel; keyboard equivalent and Escape when unlocked |
| Spread two fingers (pinch out) | Expand the selected panel |
| Bring fingers together (pinch in) | Collapse to combined view when unlocked |
| Pencil | Freeze the current game frame and audio immediately; remain fullscreen |
| More (three dots) | Adult options: Repeat video and Child lock; defer other settings until needed |

Keep normal child controls minimal: Play/Pause, Video/Game, Expand/Collapse.
Pencil and More belong to the unlocked adult surface. The first iteration freezes
the game; video-frame annotation is a separate later capability, not implied.
Native video controls may take over in browser fullscreen: the chosen panel-focus
fallback must retain the app's switch/feedback controls. Do not promise overlays
inside an operating-system-owned player.

## Freeze, mark, resume and share

Pencil changes the game panel into a whiteboard without shrinking or restaging it.
Keep Resume, Undo, Clear and Share inside that panel. Show an active pencil state;
no text-heavy instructions in child play. Capture exact SVG/state, revision,
locale and episode time; normalized strokes survive rotation and resizing.
One pointer draws. On a second pointer, cancel the provisional stroke and treat
the sequence as a pinch; it must not select a shrew or draw a diagonal line.
Collapse/expand also works in whiteboard mode and retains marks.

Resume continues from the paused state, not a restarted game. Preserve the current
draft on resume, mode switch, repeated Pencil and sharing cancellation. Reopening
the same frame must not clear it. A new capture archives the prior draft locally
before replacement; report storage failure and retain the in-memory draft.
Clear is explicit and undoable. Reopening an old annotated frame must not silently
rewind live gameplay; display it as a review snapshot with a return-to-game action.

Share exports the frozen scene plus the current, even unsaved, strokes as a PNG.
Exclude toolbar, private notes and unrelated saved records from the image.
Keep structured feedback (time/revision/locale/marks/note) as a separate adult
copy action. No automatic upload or Red Dog delivery is implied.
Use feature detection for file sharing and prepare the image before the Share tap
so user activation is retained. If unsupported, show the image for an ordinary
screen capture/save flow; do not require a download to use Storytime.
Cancelled sharing is not an error and must not lose marks or resume gameplay.
Never report "saved to Photos" merely because the share sheet opened; the parent
chooses an available destination. Physical iOS Photos behavior needs verification.

Capability reference, checked 2026-10-26:
[MDN Web Share](https://developer.mozilla.org/en-US/docs/Web/API/Navigator/share)
requires HTTPS, supported file data and a user gesture; destinations vary by device.

## Repeat video, not automatic game attempts

More contains **Repeat video** with a loop icon and an explicit selected state.
Default off; the adult enables it and starts playback with Play. This repeats
the same video, not the next episode, and is not a promise of audible autoplay
on page load. Pause, game switching, page hiding and feedback stop playback.
Returning requires Play; enabling repeat never starts the game. Do not loop
failed game attempts automatically or change their timing/difficulty.

## Child lock / adult handoff

The adult selects the intended fullscreen surface, then enables Child lock.
Lock keeps gameplay/rescue taps, Play/Pause, Replay and Video/Game switching usable.
Hide Pencil, More, sharing, language/settings, ratings, external links and Mall exit;
disable app collapse gestures/buttons while locked. Switching retains the lock.
Keep a small reachable lock control: deliberate press-and-hold opens an adult
confirmation to unlock, with a keyboard/accessibility equivalent. A hold alone
does not authenticate an adult and must not authorize purchases or publication.
Cancel releases the hold without activating gameplay underneath. Never strand
the adult without an exit. Pause on background/rotation; recover the same lock
state within the session, without a trapped reload or surprise playback.
This is an accidental-touch guard, **not an OS/device lock, parental identity
proof or security boundary**. Browser/system exits remain possible.

## Later Mall features, not this prototype slice

Record episode ratings using the existing Play FoundUps owner when verified.
Heart/press-and-hold, Red Dog and chili-pepper presentation are requested candidates,
not an invented scale or API. Keep ratings separate from favorites and adult
editorial/learning audits. Rating concerns the episode, never the child's ability.
No long-press rating on the game canvas: it conflicts with rescue, ink and unlock.
Provide an explicit accessible action; child lock hides rating/submission.
Verify owner, scale, admission, abuse controls and privacy before implementing.
Red Dog transport, shared Mall mounting, Next, membership and native-device lock
integration remain separate work; do not add placeholder controls that do nothing.

## Source audit and RSI acceptance

**OBSERVED:** current viewer always sends Play, collapses before Pencil, disables
pinch during ink, resets marks on a new Pencil tap and copies only saved entries.
Tools live outside the expanded panel. Existing 48px targets and gesture owner
are reusable. Supplied fullscreen screenshot shows detached bottom controls.
Independent source audit confirmed these issues; native touch remains UNVERIFIED.
Current workflow/feedback continuity/readability: 2/5; input parity: 3/5. These
are diagnostic judgments, not child-learning measures or WSP15 priority scores.

Next repair must independently exercise:

1. Combined → each fullscreen view → switch → collapse, without losing time/state.
2. Running game → Pencil → circle → resize → collapse/expand → resume at same time.
3. Draft retention, repeated Pencil, Undo/Clear, share cancellation and PNG contents.
4. One-finger drawing vs two-finger pinch/cancel; no unintended game action.
5. Repeat selection, one audio source, background pause and no automatic game retry.
6. Lock/unlock, hold cancellation, accessible exit, locked video/game switching.
7. Mouse/keyboard and phone/tablet portrait/landscape; actual installed iPhone
   touch/Photos behavior separately from browser emulation.

Follow the existing production skill's viewer-iteration rubric: inspect → grade
→ repair → independent review → retain failure/correction → reuse on the next
actual episode. Preserve approved art/audio and the 15-second world timeline.
Bundle one milestone PR, update evidence with exact source and scope; a docs
commit is not proof of a working control, learned model or admitted WRE worker.
