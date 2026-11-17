# OpenRouter storyboard decision — 2026-10-23

Repository first: AI Gateway already configures `OPENROUTER_API_KEY` and the OpenRouter base URL. Its ordinary response path is text-oriented; it does not return image bytes. `infrastructure/openrouter_client` is explicitly dormant and must remain so. Kids story production already accepts an injected shot generator. Extend the YouTube generation owner with a bounded image adapter and compose it with that callback; do not create a second auth, editor, scheduler or FoundUp.

Initial candidate: `black-forest-labs/flux.2-klein-4b`. Black Forest Labs documents reference editing, Apache 2.0 weights for 4B (the 9B license differs), and API availability. OpenRouter lists the first output megapixel at $0.014 and subsequent megapixels at $0.001. This is observed list pricing, not a per-request quote or guaranteed bill. Recheck current endpoint capabilities, price and budget at host admission. Newer FLUX 3 Klein and Qwen Image candidates exist, but have not been benchmarked against the Little Shrew reference; neither model names nor family membership establish a license. No automatic challenger switch.

- https://openrouter.ai/black-forest-labs/flux.2-klein-4b
- https://docs.bfl.ai/flux_2/flux2_overview
- https://openrouter.ai/docs/guides/overview/multimodal/image-generation

The current documented API is POST `/api/v1/images`, with `input_references` (data URLs), `n`, `aspect_ratio`, and base64 `data[].b64_json` output. Capability discovery is GET `/api/v1/images/models` and per-model `/endpoints`. Do not assume the existing general text catalog's policies qualify media endpoints.

First episode remains Little Shrew beats 1–3: sleeping family of six, hero sniffing the sprout, parents noticing gentle shaking. Request one frame per beat, keep flat bean geometry and fixed palette, inspect actual character count and placement, then pass approved frames into three video generations. Editorial clips remain five seconds each even if the video provider requires longer native durations. Images alone do not complete the video request.

Runtime binding example (inside the admitted owner; direct-file loading avoids legacy optional provider imports):

```python
images = OpenRouterStoryboard(
    gateway.providers['openrouter'], references=approved_raster_references,
    authorize=owner_admit_storyboard_request,
)
shots = StoryboardVideoShot(
    images, review_frame=independent_actual_image_review,
    generate_video=admitted_image_to_video_generator,
)
# run_story(..., generate_shot=shots, ...) retains its existing controller gates.
```

These names denote required host capabilities, not installed services. The reviewer checks actual decoded imagery; the video callback consumes `shot['start_frame']`, verifies its digest and records its use. No paid calls or visual benchmark have been performed for this integration. OpenRouter also documents video generation, but selecting/binding that separate API is not part of this image-provider slice.

WSP retrieval: governed lexical query at the verified checkout reported UNKNOWN freshness and index_gap=true; results prioritized Kids docs but missed the gateway owner and tests. Direct searches resolved both and the dormant-client boundary. Optional Kids memory/README and Shorts tests/README are absent. No semantic freshness is asserted. Manual provider-contract adaptation was used because no local Qwen/Gemma executor is bound in this session. Existing WSP 00 invocation/tracker evidence remains as recorded in the Little Shrew ModLog; no new detector success is claimed.
