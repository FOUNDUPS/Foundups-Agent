# Little Shrew: A Giant Step

A source-grounded series preset within `kids_episodes`, under the existing YouTube work, with EDUIT activity links. `little_shrew` is a series ID, not a second FoundUp or active tenant.

## Source and editorial decisions

Primary source: [Preschool Simplified Edition](https://docs.google.com/document/d/1-BH_ojM7C2z2rOvAfjq5HJpyHXFvG3453uv5wpVN-Pw/edit), read 2026-10-23. Also compared [sensory edition](https://docs.google.com/document/d/1Lm2ZwvSzqGVEjJaLcxNcEoToLKGuLrRFvoHzRUmPro8/edit), [nine-panel edition](https://docs.google.com/document/d/1GQIL225ODHgKNabN48lrQuR2F92BwiFAHv4QuZub0ns/edit) and [v2.2 storyboard](https://docs.google.com/document/d/1HOTn1imDbUMnSQY_8Q570K8P1U9HygmYYbmo0HoE8BM/edit).

All seven retrieved project-bible documents contained text, with no embedded image objects. The v2.2 text names `visual_illustration_11410072553248207923.png`; that file was not retrieved. A same-day Drive image search also returned no files. The included SVGs are newly authored simplifications of the textual design, not recovered Gemini images. Missing originals do not establish reuse rights.

The latest edition and the creator's request for further simplicity take precedence:

- Preserve nine five-second beats, grouped into three linked 15-second episodes. Existing renderer uses 30 fps: 150 frames per beat, 450 per episode, 1,350 per complete story. Earlier 24 fps/120-frame directions are superseded for this renderer.
- One bean-shaped rig, fixed palette, pink triangle nose, exactly six whiskers, one curved tail. Four expressions, no teeth, highlights, fur, shading, clothing, visible idle limbs or complex walk cycles. Family members reuse the same rig at different scales. Slide, tilt and bounce only.
- Parents guide all three siblings to safety. Little Shrew shelters under the root-pocket ledge. No implied death, injury or orphaning. Reunion is a later story; this pilot ends on the family scent trail.
- Keep the dinosaur offscreen. Sound, small dust shapes and the final three-toed footprint imply its step. No frightening foot closeup or crushing imagery.
- No speech or lyrics; original instrumental music and gentle foley. The source's closing lyric conflicts with its dialogue-free direction, so it is omitted. Sound captions are accessibility cues and must be aligned to the actual finished audio.
- Treat this as fictional animal storytelling. Earlier precise claims about visual distance, vibration frequency, ancestry and prehistoric dates are not verified curriculum facts and are excluded. Independent education review still applies.

## Assets and use

`pilot.json` owns the adapted narrative, palette, source provenance, objectives, activities and music brief. `character.svg` is the shared rig/expression sheet. `storyboard.svg` is the nine-panel design preview, **not generated video**. Both SVGs embed identical rig definitions; the regression test rejects drift between them.

```python
from modules.foundups.kids_episodes.src.little_shrew import build_pilot
plan = build_pilot(request_id="little-shrew-pilot", supported_durations=(4, 6, 8))
```

The returned plan round-trips through the canonical `compile_plan` contract and can be handed to the existing admitted `run_story` owner. Six-second generations are trimmed to five seconds in this example; actual durations must come from the selected provider. A provider offering only shorter shots is rejected.

Each shot carries repository-relative reference paths and SHA-256 hashes, plus its beat ID and expression. The admitted generation adapter must resolve and verify these design references and actually supply supported reference inputs to its provider. This preset does not implement that provider binding or claim that a text prompt guarantees continuity. Independent review must compare the output with the rig, palette, story states and source beats. No provider account, scheduler, upload route or publishing authority is activated here.

Music is a brief, not an audio file or rights clearance. Use original audio with provenance through the existing audio owner. Do not copy a Baby Shark melody or recording.
