# Video Indexer Module

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
