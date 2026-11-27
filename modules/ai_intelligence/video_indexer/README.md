# Video Indexer Module

## Bounded local archive retrieval pilot & fail-closed dataset boundary — 2026-11-16

- **Implemented (`LocalArchiveRetrievalPilot`)**: `src/local_archive_retrieval.py`, `src/local_archive_parsers.py`, and `src/transcript_admission_guard.py` (`LocalArchiveRetrievalPilot`, `run_local_archive_pilot`, wired into `src/action_surface.py` and `cli.py --local-pilot-manifest / --local-pilot-query`) provide a read-only, offline local archive retrieval pilot enforcing a hard `max_records <= 10` ceiling. It supports `video_indexer` JSON artifacts, `yt-dlp` `.info.json`, JSONL, SRT, WebVTT, JSON3, and plain `.txt` transcripts using local `scikit-learn` TF-IDF (`TfidfVectorizer` + `cosine_similarity` with OOV L2-norm restoration) and an IDF-weighted lexical/CJK fallback, with zero network calls, zero model downloads, and zero Whisper/media decoding. Missing-transcript records (`scheduler_stub` stubs, metadata-only `.info.json`, raw media files) are classified as `BLOCKED_MISSING_TRANSCRIPT`. Contradictory cross-layer metadata (`provenance_conflict=True`) and summaries disguised as verbatim transcripts (`mislabeled_summary_suspected=True`) are automatically downgraded (`is_verbatim=False`, `training_eligible=False`). Returned hits preserve honest speaker attribution (`speaker=None, speaker_status="unknown"` when missing — never inventing `"012"`) and strict timestamp status (`GENUINE`, `PARTIAL_START_ONLY`, `ABSENT`, `INVALID`, `NONMONOTONIC`), emitting `&t=` deep links only when `has_genuine_timestamps=True` and returning `not_found=True` below threshold.
- **Fail-closed `DatasetBuilder` & shared admission guard**: `src/dataset_builder.py` and `src/transcript_admission_guard.py` enforce cross-layer metadata consistency (`"contradictory_metadata"`), `training_eligible`, `consent`, music-channel exclusions (`antifafm`, `ravingantifa`, `ffcpln_music`), non-verbatim provenance vetoes, mislabeled-summary detection (`"mislabeled_summary_as_transcript"` on `gemini*` models, summary schemas, summary payloads, or 3rd-person narrator framing), strict finite/range-checked monotonic timestamps (`"invalid_timestamps"`, `"nonmonotonic_timestamps"`), and honest speaker attribution (`require_speaker_attribution=True` by default, optional `require_verified_speaker=True`, never defaulting missing speakers to `"012"`, and excluding guest/unknown turns from target utterances and `VoiceClip`s) **before** admitting any training rows, with explicit rejection/error accounting in `process_folder()`.
- **Epistemological & operational status boundary**: Code-seam inspection at `877878402` and `d9d8d4450` establishes code-level admission/attribution seams only, whereas local archive artifact counts and contents come from separate direct file inspection. Offline synthetic unit suite passes **178 passed, 13 deselected** (`26 passed` in the focused pilot + integrity regression pair; `32 passed` in `youtube-selected-batch`), and the bounded read-only pilot was verified on 10 local artifacts with unchanged SHA-256 digests. Merge and deployment remain **PENDING**, and verbatim archive transcription and model weight training remain **BLOCKED** pending verbatim speech transcripts, speaker verification, explicit 012 consent, and GPU/toolchain prerequisites.

## Studio indexing cost and routing boundary — 2026-11-07

Source review of `fa7d487f3` found a separate unattended Gemini API enrichment
pass in `src/studio_ask_indexer.py:2871`, triggered by newly indexed videos and
key presence. The candidate removes only this paid pass, retaining browser
Studio Ask results and the compatible empty `gemini_analysis` field. The
[32-case offline selection](tests/TestModLog.md#2026-11-07--no-unattended-paid-enrichment-after-studio-indexing)
passes; the key-presence regression fails on old source. Merge and deployment
remain pending at this documentation checkpoint.

012 requires the existing shared AI router across AI consumers. The migration
audit remains **SPECIFIED_NOT_IMPLEMENTED**: current
`ai_gateway/src/youtube_model_routing.py` accepts only `comments`/`livechat` and
`assess`/`write`/`review`, not video analysis. Reusing its name or supplying a key
does not establish capability, cost approval or provider availability. Follow
the [existing ordered repair list](../../platform_integration/youtube_shorts_scheduler/ROADMAP.md#repair-work-list--2026-11-07);
do not add a parallel provider fallback to satisfy this requirement.

## YUMORI campaign evidence proposal

The preserved [Moshpit video-evidence work order](YOUTUBE_DAE_YUMORI_MOSHPIT_VIDEO_EVIDENCE_WORK_ORDER.md)
reuses current action and persistence owners. YUMORI-specific extraction and
candidate projection remain SPECIFIED_NOT_IMPLEMENTED; this document does not
authorize browser access, backfill, disclosure or publication. Existing
single-video/channel/portfolio/daemon routes do not prove that campaign outcome.


Japanese audio uses the existing `AudioAnalyzer(language="ja")`; automatic
detection is the default for multilingual models; omitted language remains English
for `.en` models. See [language evidence in the interface](INTERFACE.md#audioanalyzer).

**WSP Compliance**: WSP 49 (Module Structure), WSP 3 (Domain Organization), WSP 72 (Independence)

## Purpose

Comprehensive video content indexing for 012's YouTube channels (FoundUps, UnDaoDu, Move2Japan, RavingANTIFA). Transforms raw video content into searchable knowledge artifacts that enable 0102 to learn from and recall 012's teachings.

Ask-Gemini browser indexing now persists JSON artifacts for continuity across pipelines.

## Utility Routing

Index outputs are used to route downstream behavior:
- Gemini/Ask Studio summaries → searchable Digital Twin memory
- YouTube/Whisper verbatim transcripts → response/weight-training datasets
- music/video content → RavingANTIFA or faceless-video pipeline (module in development)

Gemini summaries are explicitly marked `training_eligible: false`; they must
not be treated as words 012 actually spoke.

## Architecture

```
video_indexer/
├── README.md           # This file
├── INTERFACE.md        # Public API contract
├── ModLog.md           # Change history
├── ROADMAP.md          # Future development
├── src/
│   ├── __init__.py
│   ├── video_indexer.py        # Main orchestrator
│   ├── audio_analyzer.py       # ASR, diarization, NLP
│   ├── visual_analyzer.py      # Shot detection, faces, objects
│   ├── multimodal_aligner.py   # Cross-modal moments
│   ├── clip_generator.py       # Clip candidate extraction
│   └── video_index_store.py    # JSON artifact storage
└── tests/
    └── __init__.py
```

## Integration with Existing Systems

This module EXTENDS (not replaces) existing infrastructure:

| Component | Existing System | Integration |
|-----------|-----------------|-------------|
| ASR | `batch_transcriber.py` | Reuse Whisper pipeline |
| Embeddings | `transcript_index.py` | Reuse ChromaDB collections |
| Storage | `video_index/` JSON | Same artifact format |
| Launcher | `dae_dependencies.py` | Auto-launch browsers |
| Navigation | `YouTubeStudioDOM` | Reuse Selenium navigation |

## Metadata Catalog (SQLite)

For auditability and fast listing, a SQLite catalog is maintained alongside JSON:

- Path: `memory/video_index/metadata.sqlite3`
- Updated by: `VideoIndexStore.save_index()` and Gemini `save_analysis_result()`
- Purpose: per-video metadata (channel, title, duration, topics, model, source path)

## Daemon + Reindex Signals

- STOP file: `memory/STOP_VIDEO_INDEXER` halts cycles safely.
- One-shot reindex: create `memory/REINDEX_VIDEO_INDEXER` or set `VIDEO_INDEXER_FORCE_REINDEX=true`.
- Progress telemetry: each cycle returns indexed/skip counts and per-channel JSON counts.
- Telemetry emission mode:
  - `INDEXER_TELEMETRY_MODE=full` (default) or `signal`
  - `INDEXER_TELEMETRY_SIGNAL_EVERY=60` (emit baseline pulse every N cycles)

## Lego Block Dependencies

```python
# Existing blocks reused
from modules.communication.voice_command_ingestion.src.batch_transcriber import BatchTranscriber
from modules.communication.voice_command_ingestion.src.transcript_index import TranscriptIndex
from modules.infrastructure.dependency_launcher.src.dae_dependencies import ensure_dependencies
from modules.platform_integration.youtube_shorts_scheduler.src.dom_automation import YouTubeStudioDOM
```

## Collections Architecture

Same ChromaDB instance, different collections:

```
HoloIndex ChromaDB (holo_index/chroma_store/)
├── code_snippets          # Code intelligence (existing)
├── wsp_protocols          # WSP documentation (existing)
├── video_transcripts      # Audio content (EXISTING - voice_command_ingestion)
├── video_visual           # Visual frames (NEW)
├── video_moments          # Multimodal clips (NEW)
└── clip_candidates        # Short-form candidates (NEW)
```

## Quick Start

Attach authenticated Chrome (port 9222) and Edge (port 9223) sessions, then run
one resumable batch across the three primary channels:

```bash
python -m modules.ai_intelligence.video_indexer.cli --portfolio --batch-size 10
python -m modules.ai_intelligence.video_indexer.cli --status
```

Each rerun skips valid existing manifests and advances to the next visible
unindexed videos. Use `--reindex` only for an intentional rebuild.

The Python orchestration API remains available:

```python
from modules.ai_intelligence.video_indexer.src.video_indexer import VideoIndexer

# Initialize with channel
indexer = VideoIndexer(channel="move2japan")

# Index a video
result = indexer.index_video(video_id="abc123")

# Search across all modalities
results = indexer.search("012 talks about Japan visa requirements")
```

## Related WSPs

- **WSP 27**: DAE Architecture (background indexing)
- **WSP 49**: Module Structure (this module follows)
- **WSP 50**: Pre-Action Verification (HoloIndex search first)
- **WSP 72**: Module Independence (standalone operation)
- **WSP 77**: Agent Coordination (Qwen/Gemma analysis)

## Channel Configuration

| Channel | Browser | Port | Channel ID |
|---------|---------|------|------------|
| Move2Japan | Chrome | 9222 | UC-LSSlOZwpGIRIYihaz8zCw |
| UnDaoDu | Chrome | 9222 | UCfHM9Fw9HD-NwiS0seD_oIA |
| FoundUps | Edge | 9223 | UCSNTUXjAgpd4sgWYP0xoJgw |
| RavingANTIFA | Edge | 9223 | UCVSmg5aOhP4tnQ9KFUg97qA |
