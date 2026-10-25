# Kids Episodes

Working name for `kids_episodes`, a story-to-linked-episodes educational FoundUp in the EDUIT context, using the existing YouTube production work.

**State:** registered, discoverable-only, incubating candidate. The product contract is specified; local renderer work belongs to `modules/communication/youtube_shorts`. No running production service, scheduled worker, public route, token, or deployed editor is claimed by this registration.

The intended product accepts a story or teaching intent, plans linked 15-second episodes, maintains character/story continuity, and prepares visuals, music, captions and activities through an autonomous production workflow. The local editor/renderer is one technical component of this product, not the complete product. An adult creator can review and revise the sequence, then export draft or final episodes. Initial assumptions are English and ages 3–6; these are configurable planning defaults, not audience research findings. The reference screenshot supplies broad visual traits: colorful animation, a clear activity, and readable sing-along captions. Use original characters and licensed or original music.

## Ownership

- Educational lineage and future linked learning games: [EDUIT](../eduit/README.md); the existing `eduit` identity remains unchanged.
- Episode rendering, generation adapters, captions and YouTube publishing: [YouTube Shorts](../../communication/youtube_shorts/README.md).
- Venture identity, curriculum/quality contracts and progression: this module.
- Future discovery, identity and media listing: existing pfMALL owners; no second catalog or authentication system.
- Future autonomous research/production: existing WRE admission and scheduling; this intake is not an executable work order.

Read [outcome](docs/intake/OUTCOME.md), [solution](docs/intake/SOLUTION.md), [scope](docs/intake/POC_SCOPE.md), [prototype gate](docs/intake/PROTOTYPE_GATE.md), then [roadmap](ROADMAP.md). [Intake source](docs/intake/INTAKE_SOURCE.md) records assumptions and retrieval limits.

## Local implementation checkpoint

The companion YouTube module now contains a local browser editor and tested FFmpeg renderer; use its README launch command. This does not advance the independent educational/production prototype gate. The separate ChatGPT trend scout was disabled at 012's request on 2026-10-24. No recurring scout or WRE worker is active from this registration.

## Discovery and identity

Canonical ID: `kids_episodes`. The valid manifest can produce a pfMALL information card with `launch_readiness=discoverable_only`. It declares no active app URL, routing prefix or storage namespace. The member-catalog exporter synthesizes `/f/kids_episodes` as a shell information-card destination when the manifest route is blank; this does not bind an app or storage tenant. Registry discoverability and an exportable card are not evidence that the hosted Mall has been redeployed. Future tenant binding must use `/f/kids_episodes`, app mount `/f/kids_episodes/app`, and `idb_kids_episodes` under WSP 104, with no shared child-profile storage or eSingularity campaign dependency.

EDUIT is verified from its existing module and manifest. Ambiguous dictated phrases are preserved in [intake source](docs/intake/INTAKE_SOURCE.md); no story marketplace or commerce workflow is inferred.

## Story pipeline foundation

`src/story_pipeline.py` plans linked episodes and runs checkpointed generation, audio, rendering, independent artifact review and optional whole-story assembly/review through injected runtime capabilities. `src/gemini_story_adapters.py` supplies structured planning and actual-MP4 review adapters. `src/work_order_adapter.py` admits only an existing registered WRE executor; the OpenClaw `kids story:` / `eduit story:` route stays blocked without that binding. Prototype skills are not production authority. See INTERFACE.md for callback and checkpoint contracts.

## Little Shrew series preset

[Little Shrew](series/little_shrew/README.md) adapts the Gemini/Drive preschool storyboard into nine five-second beats and three linked episodes. It includes a simpler shared vector character rig, nine-panel storyboard, source provenance and `build_pilot` integration with the existing story compiler. Reference assets are design inputs; live generation remains owner-admitted and unactivated.

## First rendered episode

The [local production command and autonomy audit](../../communication/youtube_shorts/docs/KIDS_LOCAL_PRODUCTION.md) generate the first three Little Shrew beats as actual deterministic animation, with original synthesized audio and timed captions. This local preview does not activate the autonomous production executor.
