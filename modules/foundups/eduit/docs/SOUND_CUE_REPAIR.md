# Sound-cues-23

012 confirms the connected fullscreen leg works, then identifies clipped SNIFF,
unprogressive THUMP and missing SQUISH. The actual successful replay contained
five0.4s sniff cues, identicalTHUMP gains and no SQUISH. Tests of the historical
15s scene did not prove those concepts survived the successful engine replay.

Revision2 keeps25s/750frames. Slightly different legal offline inputs hold each
sniff0.7s without delaying live rescue inputs or changing engine scoring/clocks.
Caption windows extend toward1.2s, capped by the next event; effect→speech offsets
are320ms(SNIFF),360ms(THUMP),600ms(SQUISH), with short-window bounds. Action voice
does not duck Foley. These are requested offsets; real browser voice latency and
complete acoustic pronunciation still need device listening. No precise onset
guarantee or prerecorded speech asset is claimed.

Shared scene THUMPs render at72/90/144 world units; caption fit also preserves
relative scale instead of flattening everything to its minimum. Foley gains
.07/.11/.17 increase through distant/near/contact. Rescued presentation includes
SQUISH during compressed-foot hold/lift, not the exact first compression instant.
Only THUMP shakes/sways. `foleyVolume` restores non-thump gain. Visual cue expiry
may finish its source segment; reset/retry/practice/resume clear retained cue
and file offset. Media unlocking primes silently, including late promises.

The rerendered MP4 SHA is
`0da4cfbb13b68c812c3ae8d65a331c2b0759ef89ff641e7f63f1cda2555b2d71`.
All10 original producer-source hashes, assets and750 canonical frames match.
The separate15s game Foley is byte-identical22. Actual decoded AAC contains five
complete12480-sample sniff primitives and26400-sample SQUISH; THUMP RMS increases
.017918→.029443→.043525. Samples prove presence/levels, not audible phone quality.

Changing scene requires a fresh renderer generation. Export hashes a fixed
ordered record for scene.mjs/rig.mjs/learning-events.mjs and copies the same
verified buffers into storytime/presentations/<generation>/. Loader checks those
hashes and imports only the derived same-origin scene URL. Draw uses its functions
without static fallback. Naming assumes a trusted immutable host, not browser
SRI against a malicious origin. Missing/invalid data leaves native movie usable.
No wildcard cache or arbitrary module URL is introduced; UI worker moves to v17.

The existing producer accepts `--rasterizer sharp` when its optional Cairo stack
is unavailable, using installed Sharp via the host's NODE_PATH. Same SVG owner,
FFmpeg author/editor and provenance; no package installation, provider call or
second animation. Cairo remains the default, lazily imported for Cairo frames.

80Node tests include actual controller VM execution, full750-frame replay,
caption fit and action speech lifecycle. Independent receipts and rendered cue
stills live in outputs/storytime-sound-20261101; generation audit is in
outputs/storytime-foot-independent-20261101/GENERATION_REVIEW.json. Earlier
build/storytime-sound-23 is stale; only the verified build may publish. Browser
input remains held while the previous Save As closed-state is unknown. Native
listening, iOS voice timing and performance need012 review, not a mock PASS.
