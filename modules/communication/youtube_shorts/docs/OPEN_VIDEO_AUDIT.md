# Open-model video production audit — 2026-10-23 JST

## Decision

Keep the existing Kids Episodes story controller and FFmpeg renderer. Qualify Wan2.2-TI2V-5B on a controlled GPU worker as the first open-model video candidate, preferably through a pinned ComfyUI workflow. Reuse OpenRouter for configured planning/storyboard capabilities; treat its hosted video service as a separate optional transport, not proof that a selected model is open source. Do not create another editor, scheduler, credential store, FoundUp identity or Mall media catalog.

This is an audited implementation plan, not an activated video service or a quality benchmark. No model was downloaded and no paid generation was submitted. The initial user requirement is three five-second shots from the existing first Little Shrew episode, followed by the remaining linked episodes.

## Repository evidence

Inspected clean source at `82db91eba5df1bc5b7f0f78b6cb791db8547ceea`; fetched main `f2e9408ba950a80fe549887db39289e6aff04f27` has no changes in the audited Shorts, Kids Episodes or video-indexer trees. Governed lexical retrieval reported UNKNOWN freshness and index_gap=true. Results mixed relevant Kids docs with unrelated permission-routing results and omitted generators/tests; exact-path searches supplied the missing evidence. No semantic-index freshness is claimed.

| Existing owner | Verified source behavior | Decision / remaining gap |
|---|---|---|
| `kids_episodes/src/story_pipeline.py` | Plans source-covered linked episodes; injects generation/audio/render/review; bounded repair; checkpoints; full-story review | Retain. Bind real providers and independent review through the current owner. |
| `kids_episodes/src/little_shrew.py` | Nine five-second beats in three 15-second episodes; shared references; native generation duration separate from edit duration | Use this content, not a new demo story. |
| `youtube_shorts/src/openrouter_storyboard.py` | Existing gateway config; raster references; one image; admission; attempt record; frame review before video callback | Image adapter only. `generate_video` is still supplied by the host. |
| `youtube_shorts/src/kids_episode.py` | Local trim/scale, 30 fps, captions/SRT, audio mix, cuts/fade-through-black, 450-frame episode verification; full-story assembly | Keep as canonical Kids renderer. It discards clip audio and uses separate music/voice inputs. |
| `youtube_shorts/src/kids_editor_server.py` | Local adult-facing episode editor and render preview | No autonomous generation UI/executor is established by this server. |
| `youtube_shorts/src/video_editor.py` | Older FFmpeg concatenation and crossfades | Do not route Kids through it: shared concat filename, fixed 4.5s transition offsets, and crossfade path maps video without an audio mix. |
| `youtube_shorts/src/veo3_generator.py`, `sora2_generator.py` | Existing proprietary generation integrations | Preserve legacy consumers; neither fulfills open-model independence. Source presence is not current API qualification. |
| `youtube_shorts/src/shorts_orchestrator.py` | Veo/Sora selection and fallback; uploader coupled into orchestration | Do not reuse automatic proprietary fallback for the open-model Kids route. |
| `youtube_shorts/src/shorts_pipeline.py`, `clip_exporter.py` | Extract shorts from indexed existing videos | Different input path; not original story generation. Reuse media ownership, not extraction semantics. |
| `kids_episodes/src/gemini_story_adapters.py` | Concrete Gemini structured planner and actual-MP4 reviewer | Core controller is injectable, but Google-independent planner/reviewer bindings still need qualification. |
| `video_indexer/src/visual_analyzer.py` | Frame/shot extraction and face sampling; object/OCR/color outputs remain TODOs | Reuse useful technical extraction. Do not claim cartoon-character or educational continuity review is implemented. |
| `kids_episodes/src/work_order_adapter.py` | Existing WRE entry rejects absent production executor/provider/reviewer authority | Retain. Source adapters are not live OpenClaw/Hermes admission. |

No Wan, LTX, HunyuanVideo or ComfyUI implementation was found in the searched repository source/configuration surfaces. That is a scoped search result, not an audit of every external runtime. FFmpeg is present in this execution environment; `nvidia-smi` was not found. No conclusion about 012's other machines follows.

## OpenRouter verification

Read public `https://openrouter.ai/api/v1/videos/models` on 2026-10-23 without credentials. The Wan/LTX/Hunyuan/Cog-name filter returned only:

| Model ID | Advertised durations | Reference support |
|---|---|---|
| `alibaba/wan-3.0-prime` | 2–30 seconds | First and last frame |
| `alibaba/wan-3.0` | 2–30 seconds | First and last frame |
| `alibaba/wan-2.7` | 2–10 seconds | First and last frame |
| `alibaba/wan-2.6` | 5 or 10 seconds | First frame |

All four entries had `hugging_face_id: null`; that alone neither proves nor disproves open licensing. No Wan2.2 or LTX entry was returned by this filter. Do not transfer the Wan2.2 Apache license to later hosted Wan versions. An exact model/license/weights mapping is required before labeling any hosted route open-model.

The official video API has a separate asynchronous lifecycle: submit `/api/v1/videos`, retain the returned job ID, poll job status, download `/content`. It is not the image adapter's synchronous request. A future adapter must validate current model capabilities, bind the reviewed start frame, persist submission uncertainty, resume polling without resubmitting generation, bound waits/downloads, handle failure/cancellation and record actual usage. Reuse AI Gateway configuration and existing story admission rather than the explicitly dormant `infrastructure/openrouter_client`.

Sources: https://openrouter.ai/docs/guides/overview/multimodal/video-generation ; https://openrouter.ai/collections/video-models ; https://openrouter.ai/api/v1/videos/models . Catalog/pricing claims are dated observations, not guaranteed availability or a quote.

## Open-model candidates

**Wan2.2-TI2V-5B — first qualification candidate.** Official code and models use Apache 2.0. It supports image-conditioned generation; the documented 5B example targets 24 GB VRAM with offloading and 720-class output at 24 fps. This is an upstream configuration, not a measured capacity or performance promise for our worker. Pin code, weights and workflow; benchmark the exact three shots before choosing it for production. The larger A14B models are a later quality comparison with greater resource requirements.

**LTX — challenger, not an Apache-equivalent default.** The official project supports audio/video generation and local inference, but specific releases have their own community/model terms. LTX-2.3 explicitly uses a community license. Qualify the exact release, dependencies, hardware and terms separately; do not call the whole family unrestricted open source. No relative quality claim against Wan or Veo has been tested here.

**ComfyUI — worker interface, not the model or Foundups orchestrator.** Its self-hosted API supports image upload, queued workflow submission, status/history and output retrieval. Foundups should supply a reviewed, pinned workflow and controlled inputs; WRE retains execution authority. No arbitrary story-authored nodes, automatic custom-node installs or exposed unauthenticated public worker. Direct Diffusers/Wan inference is an alternative if the pinned ComfyUI graph adds more dependencies than value.

Sources: https://github.com/Wan-Video/Wan2.2 ; https://github.com/Lightricks/LTX-2 ; https://huggingface.co/Lightricks/LTX-2.3/blob/main/LICENSE ; https://docs.comfy.org/development/comfyui-server/comms_routes ; https://github.com/Comfy-Org/ComfyUI ; https://github.com/huggingface/diffusers .

## Editors and deterministic animation

| Project | Fit for this system | Decision |
|---|---|---|
| FFmpeg | Already implements required headless edits, audio and captions | Keep. |
| Kdenlive / MLT | Rich manual timeline; MLT can render Kdenlive project data | Optional later project export for adult editing, not a new production backend now. |
| Shotcut | Manual timeline, subtitles, audio filters and FFmpeg formats | Useful optional inspection/editing application. No automation dependency needed. |
| libopenshot | Embeddable C++ editing library with Python bindings and layered/keyframe editing | Adds a second editing dependency without closing the current generation gap. Defer. |
| Blender Grease Pencil | 2D/cut-out animation and storyboarding | Strong candidate for deterministic motion of our simple bean-shaped rig if diffusion loses continuity. A separately built animation backend, not a ready-made pipeline. |

For this unusually simple visual style, deterministic breathing, sniffing and pebble movement may preserve six-character continuity better than regenerating every pixel. That is an engineering hypothesis to compare against Wan, not a tested winner. Keep fixed geometry/palette either way. Avoid adding transitions unless they improve the story; they must not shorten the fifteen-second timeline.

Sources: https://ffmpeg.org/ffmpeg-filters.html ; https://docs.kdenlive.org/en/project_and_asset_management/file_management/project_files.html ; https://mltframework.org/docs/melt/ ; https://www.shotcut.org/features/ ; https://www.openshot.org/libopenshot/ ; https://docs.blender.org/manual/en/latest/grease_pencil/introduction.html .

## Finish in this order

1. **Qualify one worker:** identify the actual GPU host, available VRAM/storage and allowed runtime; pin Wan2.2 weights and an image-to-video workflow. No installation or endpoint is verified yet.
2. **Connect one shot:** implement the generation callback under YouTube Shorts, passing `shot.start_frame`, prompt, seed, native frame count/fps and output location. Return the existing `{path, rights_evidence}` contract. Preserve actual frame-count/duration evidence and native generation versus five-second editorial trim. Fit job recovery into current effect/checkpoint ownership, not a second scheduler.
3. **Complete non-Google production inputs/review:** bind the planner via the existing model gateway; implement independent actual-media review with a suitable non-Google model plus technical checks. Supply original music/foley through the existing audio contract. Native generated audio is currently discarded by the renderer, so preserve needed foley in the explicit audio mix or deliberately extend that contract with tests. Do not silently lose it.
4. **Run the existing first episode:** cozy sleeping family (six), hero sniffs the sprout, parents notice a gentle shake. Check count, body geometry, palette, positions, safe action and shot joins. Render three five-second clips into exactly fifteen seconds; measure 450 output frames at 30 fps and inspect/listen to the actual result. A 1080p export does not establish native 1080p detail.
5. **Then activate autonomy:** qualify the existing WRE executor/provider/reviewer bindings, test interruption/recovery and bounded repairs, and repeat across the remaining six shots. Keep publication through the current channel-verified publisher and PF Mall media owner. Do not register duplicate services.

Acceptance requires actual generated media, independent visual/audio review and a recovery trial. Offline callbacks and existing CI are necessary but insufficient.

## Verification for this audit

137 focused tests passed: Kids renderer (including FFmpeg integration), OpenRouter storyboard boundaries, and all Kids Episodes story/preset contracts. No source-code behavior changed in this audit slice. No live images/video, model benchmark, runtime activation or upload is claimed. Historical `MULTI_CLIP_SYSTEM.md` quality, duration and cost promises are not current runtime evidence.
