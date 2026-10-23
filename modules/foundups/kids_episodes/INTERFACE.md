# Kids Episodes interface

This is the FoundUp product boundary. Executable render contracts are owned by the existing `modules/communication/youtube_shorts` module; do not create a competing encoder or uploader here.

## Story and sequence contract

Retain the raw story/intention input and any corrected transcription separately. Create a stable `story_id`, ordered episode IDs, learning progression, character bible, continuity notes, source provenance and review state. Each 15-second episode must carry its parent story ID and sequence position; transitions should preserve the story and teaching intent. A future EDUIT game link should name its learning objective and verified game/capability ID, not invent a deployed game URL.

This is the target product contract; the current renderer consumes individual episode inputs and does not prove end-to-end story generation. Commercial sale/licensing is not part of this contract without explicit scope clarification.

## Episode product contract

A production episode must retain its learning objective, age band, language, activity instructions, original-character reference, 15-second timeline, render preset and aspect ratio. Each visual/audio asset must retain its source, creation/export timestamp and rights evidence. Captions require text plus start/end times checked against the actual audible words; provider lyric text alone is not alignment evidence.

The local renderer's JSON schema is a narrower technical input and does not by itself satisfy educational, rights or publication review. Its output is an MP4 and subtitle artifact, not a published YouTube video.

## Future research result contract

Store observed URLs/video IDs, query/region/language, observation timestamps, public statistics, learning-theme candidates and a confidence label. Distinguish observed growth from inferred recommendations. A single observation cannot establish growth. Video/music inspection must have actual source evidence; metadata-only research must be labeled as such.

## Future publishing boundary

Use the existing channel-verified `YouTubeShortsUploader.publish_video` boundary. Specify the intended channel, `selfDeclaredMadeForKids=true`, and the appropriate privacy/disclosure values. A local render does not establish channel authority or publication approval. Independent review must verify educational correctness, safe activity, comprehensible sound, synchronized captions and asset rights before a publish operation.

Keep credentials server-side through existing auth owners. Future pfMALL identity/listing integration must use the canonical `kids_episodes` identifier and existing tenant boundaries.

## Discovery versus tenant binding

`pfmall.api` discovers manifests; its required fields include `name` and `version` in addition to ID/tier/stage. The kids manifest supplies these and `launch_readiness=discoverable_only`. Active `routing_prefix` and `data_namespace` remain blank. `shell_core` synthesizes `/f/kids_episodes` in its information tile; that informational fallback does not establish an app mount. The separate video-catalog truth gate expects discoverable-only entries without routing/storage binding, so member and video projection formats must not be conflated. Future bound-tenant activation requires WSP 104 `/f/kids_episodes`, `/f/kids_episodes/app` and `idb_kids_episodes`.

## Implemented source interfaces (not live admission)

- `story_pipeline.compile_plan` validates source coverage and assigns deterministic project/story/episode/shot IDs and plan digest.
- `plan_story` calls an injected structured planner only after the owner admits planning.
- `run_story` performs bounded generation, audio production, rendering, review, repair and checkpointed assembly. See its typed callback docstring. Runtime callback binding/authentication remains owner-provided; labels and digests confer no authority.
- `GeminiStoryPlanner` and `GeminiEpisodeReviewer` accept configured clients/model IDs. Reviewer sends actual MP4 bytes and binds the artifact digest. Fake-SDK tests are not live account qualification.
- `prepare_episode_request` preserves raw input as non-executable data; `dispatch_episode_request` crosses the existing registered WRE admission/executor boundary. Prototype or absent binding returns BLOCKED.

Full-story assembly returns `assembled_unreviewed` until independent checks including joins pass for `story_reviewed`. Neither publishes video. The local UI remains an episode component; live-model conversational production is not activated.
