# Headless Video Orchestrator - Roadmap

## Phase 0 (Current)
- Scaffolding, docs, and minimal build pipeline (audio overlay + visuals concat).
- Output Shorts (9:16) and longform (16:9) variants.

## Phase 1
- Auto-pull clip candidates from `video_indexer` for visuals.
- Add music metadata (song name/artist) into scheduler templates.
- Add Video Lab menu action to emit unlisted-ready assets.

## Phase 2
- Visual generator integration (Veo3/Sora2) with deterministic prompts.
- Per-track visual style presets (retro MTV, lyric visualizer, abstract loops).

## Phase 3
- AI_overseer autonomous queue (generate -> schedule -> index).
- Telemetry + retry loop for failed builds.

## Proposed cross-module video identity and reward experiment (2026-11-16)

For LEGO-style and music-video outputs, reuse the existing Shorts production owner and its [video provenance/RSI/reward PoC](../youtube_shorts/docs/VIDEO_PROVENANCE_RSI_REWARDS_POC.md). Sequence: exact-copy/hash fixture -> signed provenance manifest -> watermark red-team benchmark -> WRE research qualification -> agent authority and gifted collectible policy -> isolated geometry research. Assembly remains here; do not create a second signing or NFT service. This is unimplemented research, not a Phase 0 completion claim.

Architectural clarification: this orchestrator is a reusable assembly candidate, not an antifaFM-specific or LEGO-only renderer. Any FoundUp producer may supply code-built scenes, animation, clips or other authorized assets. Keep cryptographic provenance and optional Mall collectible rewards behind separate adapters; see the [shared-tool boundary](../youtube_shorts/docs/VIDEO_PROVENANCE_RSI_REWARDS_POC.md#architectural-correction-shared-tool-not-a-channel-owned-product-012-2026-11-16). Do not duplicate existing FFmpeg/editor/publisher owners.
