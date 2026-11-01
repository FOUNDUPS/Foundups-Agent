# Continuous fullscreen movie

012's phone image showed a static upper sky with a foot appearing only in the
lower landscape film. Gameplay's expanded scene could not fix this other surface.

The existing offline replay supplies750 worlds at30fps for the25-second film.
The existing scene renderer adds its presentation-only sky/soil and whole-leg
travel. The video retains playback, audio, narration, pause, seek and repeat;
there is no second running game, animation timer or new renderer. Expanded-only
SVG follows presented media time through requestVideoFrameCallback; the fallback
reads currentTime on rAF. A changed size redraws the same retained frame.

`export_movie_presentation.mjs` validates the film provenance's complete source
hash set and MP4 bytes before deriving sidecars. It also compares all750 canonical
scene outputs before and after safe world projection. Do not bless an old film
with new source hashes. Rerender through the existing producer when sources differ.
Version22 retained movie SHA
`9b0c3698b2ce070982a366a15cb7d403403d76427b45d549183392bf3607d374`.
Version23 rerenders the movie; see [sound cue repair](SOUND_CUE_REPAIR.md).

The same-origin loader checks bounded frame counts, finite coordinates, allowed
cast/statuses/cues and safe text before SVG construction. It verifies frame and
movie digests plus renderer dependencies. Version23 copies verified dependencies
into a content-addressed generation and imports only its derived scene URL.
Draw uses that module without static fallback. Trusted immutable naming prevents
old module-instance reuse; this is not browser SRI against malicious hosting.
Unavailable, offline or invalid data leaves native
video visible. Replay/movie JSON is not added to precache; only the small UI
module joins the existing bounded/versioned UI cache. Manifest identity stays.

Acceptance separates canonical-frame/unit proof, rendered stills, actual browser
playback and012's installed iOS PWA.012 confirmed22's leg works; the23 action hold follows an
unresolved native Save As report, not an animation result. Do not claim rVFC
progression, native audio/performance or child comprehension from mocks/stills.
Observe real Play/Pause, seek, replay, resize and expand/collapse when the hold
clears; confirm the game remains paused and record actual movie/scene frame
progression. Never download hidden assets to verify this again.

Rollback: saved Sites versions21/22 remain available. This layer can also fail
closed to the current native video. Version23 explicitly rerenders the film.
