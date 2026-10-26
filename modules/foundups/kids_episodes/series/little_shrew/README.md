# Little Shrew: A Giant Step

A source-grounded series preset within `kids_episodes`, under the existing YouTube work, with EDUIT activity links. `little_shrew` is a series ID, not a second FoundUp or active tenant.

## Source and editorial decisions

Primary source: [Preschool Simplified Edition](https://docs.google.com/document/d/1-BH_ojM7C2z2rOvAfjq5HJpyHXFvG3453uv5wpVN-Pw/edit), read 2026-10-23. Also compared [sensory edition](https://docs.google.com/document/d/1Lm2ZwvSzqGVEjJaLcxNcEoToLKGuLrRFvoHzRUmPro8/edit), [nine-panel edition](https://docs.google.com/document/d/1GQIL225ODHgKNabN48lrQuR2F92BwiFAHv4QuZub0ns/edit) and [v2.2 storyboard](https://docs.google.com/document/d/1HOTn1imDbUMnSQY_8Q570K8P1U9HygmYYbmo0HoE8BM/edit).

All seven retrieved project-bible documents contained text, with no embedded image objects. The v2.2 text names `visual_illustration_11410072553248207923.png`; that file was not retrieved. A same-day Drive image search also returned no files. The included SVGs are newly authored simplifications of the textual design, not recovered Gemini images. Missing originals do not establish reuse rights.

### Historical source adaptation — superseded for episode one

The following bullets describe the 2026-10-23 adaptation, not current episode-one
production authority. Later creator direction replaces family escape/offscreen
dinosaur/no-collapse staging and accessibility-only captioning. The final
‘Next revision: ordered audits and sniff learning’ section below is the current
episode-one brief; use it over these historical bullets.

- Preserve nine five-second beats, grouped into three linked 15-second episodes. Existing renderer uses 30 fps: 150 frames per beat, 450 per episode, 1,350 per complete story. Earlier 24 fps/120-frame directions are superseded for this renderer.
- One bean-shaped rig, fixed palette, pink triangle nose, exactly six whiskers, one curved tail. Four expressions, no teeth, highlights, fur, shading, clothing, visible idle limbs or complex walk cycles. Family members reuse the same rig at different scales. Slide, tilt and bounce only.
- Parents guide all three siblings to safety. Little Shrew shelters under the root-pocket ledge. No implied death, injury or orphaning. Reunion is a later story; this pilot ends on the family scent trail.
- Keep the dinosaur offscreen. Sound, small dust shapes and the final three-toed footprint imply its step. No frightening foot closeup or crushing imagery.
- No speech or lyrics; original instrumental music and gentle foley. The source's closing lyric conflicts with its dialogue-free direction, so it is omitted. Sound captions are accessibility cues and must be aligned to the actual finished audio.
- Treat this as fictional animal storytelling. Earlier precise claims about visual distance, vibration frequency, ancestry and prehistoric dates are not verified curriculum facts and are excluded. Independent education review still applies.

## Assets and use

`pilot.json` preserves the historical adapted narrative, palette, source provenance, objectives, activities and music brief. It has not been reconciled with the later episode-one override; do not regenerate the current episode from that preset without reconciliation. `character.svg` is the shared rig/expression sheet. `storyboard.svg` is the nine-panel design preview, **not generated video**. Both SVGs embed identical rig definitions; the regression test rejects drift between them.

```python
from modules.foundups.kids_episodes.src.little_shrew import build_pilot
plan = build_pilot(request_id="little-shrew-pilot", supported_durations=(4, 6, 8))
```

The returned plan round-trips through the canonical `compile_plan` contract and can be handed to the existing admitted `run_story` owner. Six-second generations are trimmed to five seconds in this example; actual durations must come from the selected provider. A provider offering only shorter shots is rejected.

Each shot carries repository-relative reference paths and SHA-256 hashes, plus its beat ID and expression. The admitted generation adapter must resolve and verify these design references and actually supply supported reference inputs to its provider. This preset does not implement that provider binding or claim that a text prompt guarantees continuity. Independent review must compare the output with the rig, palette, story states and source beats. No provider account, scheduler, upload route or publishing authority is activated here.

Music is a brief, not an audio file or rights clearance. Use original audio with provenance through the existing audio owner. Do not copy a Baby Shark melody or recording.

### Current episode-one vocabulary — 2026-10-26

Rendered revision sound-words-5: **THUMP → CRACK → SQUISH** (superseded teaching scope; see next revision below). One goal: match each
sound-word to its visible cause. THUMP accompanies the first shake/wake-up;
CRACK accompanies visible growing roof fissures; SQUISH accompanies the final
compression into the same dark earth. This replaces the previous stomp/crunch
caption plan. Keep two parents and three equal-sized young, reacting family
before roof occlusion, only the hero in the right root pocket afterward.
Shared implementation remains `public/eduit/storytime/scene.mjs`, rendered by
`modules/foundups/eduit/render_story_preview.py` (sound-words-5). Storytime's
website label/domain is Storytime / storytime.eduit.org; YouTube remains Us
Story Time. No new FoundUp ID or live domain deployment is implied.

### Next revision: ordered audits and sniff learning — 2026-10-26

SPECIFIED, not yet rendered: early THUMP wakes the hero; repeated SNIFF binds
nose/body movement, sniff audio and a large nearby word; CRACK binds growing
fissures and nearby word; the roof descends with staggered family reactions;
a contact THUMP may precede final SQUISH as the chamber finishes compressing.
Final hero turns toward camera through readable intermediate poses. Keep the
same dark earth and sole-survivor pocket. English only for the current proof;
future locale variants reuse stable event IDs and reviewed words/fonts/audio.

Current source audit against this new brief: FAIL physics/staging (family shares
one reaction onset; frontal pose changes instantly; adults lack clear supporting
ground); PASS fixed earth material based on earlier raw-frame pixel review;
FAIL education (SNIFF omitted from current word events); FAIL contextual text
placement (all words use the same bottom-center anchor). Actual listening and
locale delivery remain UNVERIFIED. Footprint readability remains unresolved.
These are next-preview repairs, not a claim that revision sound-words-5 satisfies
the latest brief. Apply production skill's four ordered audits before delivery.


### 2026-10-26 — Interactive alternate outcomes

The film retains one survivor; the game can rescue three babies and two slower
parents through repeated select-then-root actions. Both use the same world timeline.
The cave shelf is removed; large parents remain above the three small babies
in the approved stylized burrow perspective. See
[rescue contract](../../../eduit/docs/RESCUE_GAME_REVIEW.md).
