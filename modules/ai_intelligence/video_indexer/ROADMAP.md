# Video Indexer Roadmap

**WSP Compliance**: WSP 27 (DAE Architecture), WSP 77 (Agent Coordination)
**Current Version**: V0.19.3 (2026-03-18)
**Status**: PRODUCTION READY

---

## LATEST: V0.19.3 - LIVE Prioritization + Daemon Mode

### New Capabilities
- **LIVE prioritization**: LIVE/Streamed/Premiered videos indexed FIRST
- **Shorts filtering**: Shorts skipped (low content value)
- **Daemon mode**: 24/7 continuous indexing via CLI
- **Dual-browser rotation**: Chrome (9222) + Edge (9223) alternation

### Research: Chrome 146 Native MCP
- Chrome DevTools MCP server v0.19.0 discovered
- 26 tools for AI browser automation
- Task spec created: `wre_core/docs/CHROME_DEVTOOLS_MCP_INTEGRATION_TASK.md`

---

## CURRENT STATUS OVERVIEW

| Phase | Component | Status | Notes |
|-------|-----------|--------|-------|
| 1 | Audio | COMPLETE | Wrapper + transcription via batch_transcriber |
| 1a | Diarization | NOT STARTED | Requires pyannote.audio |
| 1b | Quote Extraction | PARTIAL | Heuristic detection working |
| 1c | Topic ID | NOT STARTED | Requires NLP pipeline |
| 2 | Visual | COMPLETE | OpenCV + yt-dlp (2026-01-09) |
| 3 | Multimodal | COMPLETE | Heuristic alignment (2026-01-09) |
| 4 | Clips | COMPLETE | Virality scoring (2026-01-09) |
| 5 | DAE Integration | PARTIAL | Menu hook, not full daemon |
| 6 | Gemini AI | COMPLETE | Tier 1 indexing (2026-01-10) |
| 7 | HoloIndex | COMPLETE | ChromaDB semantic search (2026-01-11) |
| 8 | Quality Metrics | COMPLETE | Resolution/bitrate analysis (2026-01-11) |
| 9 | Gemma Classifier | COMPLETE | Segment quality tier classification (2026-01-12) |
| 10 | WSP 77 Validation | DESIGN READY | Parse validation + auto-repair (2026-01-14) |

---

## Phase 1: Audio Foundation

**Status**: COMPLETE (wrapper functional)

### Capabilities
- [x] ASR via Whisper (`batch_transcriber.py`) - WSP 84 reuse
- [x] ChromaDB storage (`transcript_index.py`)
- [x] JSON artifacts (`video_index/`)
- [x] Browser auto-launch (`dae_dependencies.py`)
- [x] YouTube Studio navigation (`YouTubeStudioDOM`)
- [x] `audio_analyzer.py` wrapper around batch_transcriber
- [x] Quote extraction (heuristic pattern matching)

### Gaps Remaining
- [ ] Speaker diarization (pyannote.audio) - Requires GPU
- [ ] Topic identification (LDA/BERTopic)
- [ ] Advanced sentiment analysis

---

## Phase 2: Visual Analysis

**Status**: COMPLETE (2026-01-09)

### Capabilities
- [x] Keyframe extraction (OpenCV + frame sampling)
- [x] Shot boundary detection (histogram diff)
- [x] Face detection (OpenCV Haar cascade)
- [x] Video download with caching (yt-dlp)
- [x] `visual_analyzer.py` with VisualResult dataclass

### Gaps Remaining
- [ ] Object detection (YOLO) - Future enhancement
- [ ] OCR for on-screen text - Future enhancement
- [ ] Color analysis - Future enhancement

---

## Phase 3: Multimodal Alignment

**Status**: COMPLETE (2026-01-09)

### Capabilities
- [x] Audio-visual moment alignment (timestamp overlap)
- [x] Highlight detection (engagement scoring)
- [x] `multimodal_aligner.py` with MultimodalResult dataclass
- [x] Heuristic engagement scoring (hooks, faces, punctuation)

### Gaps Remaining
- [ ] Embedding-based alignment (CLIP model) - Future
- [ ] Cross-modal search (query audio, find visual) - Future

---

## Phase 4: Clip Generation

**Status**: COMPLETE (2026-01-09)

### Capabilities
- [x] Clip candidate extraction (15-60s segments)
- [x] Hook detection (strong opening moments)
- [x] Virality scoring (engagement + duration + hooks)
- [x] Title/description generation (heuristic-based)
- [x] `clip_generator.py` with ClipGeneratorResult dataclass

### Gaps Remaining
- [ ] LLM-powered title generation - Future
- [ ] ML-based virality prediction - Future

---

## Phase 5: DAE Integration

**Status**: PARTIAL (menu hook working)

### Capabilities
- [x] Menu toggle in main.py (Option 8 in YT submenu)
- [x] Hook in auto_moderator_dae.py (post-comment processing)
- [x] `YT_VIDEO_INDEXING_ENABLED` environment toggle
- [x] `studio_ask_indexer.py` for browser automation
- [x] Ask-Gemini indexing persists JSON artifacts
- [x] Progress telemetry for indexing runs (counts + deltas)
- [x] STOP/REINDEX signals for daemon control
- [ ] Utility routing signals (012 voice vs music/video → downstream pipelines)

### Gaps Remaining
- [ ] Full background daemon (continuous operation)
- [ ] Auto-index new uploads (channel monitoring)
- [ ] Re-index on demand (admin command)

---

## Phase 6: Gemini AI Integration (NEW V0.7.0)

**Status**: COMPLETE (2026-01-10)

### Capabilities
- [x] Direct YouTube analysis via Gemini 2.0 Flash
- [x] No download required (URL-based analysis)
- [x] Live stream support (PRIMARY USE CASE)
- [x] Timestamped segments with speaker identification
- [x] `gemini_video_analyzer.py` (597 lines)
- [x] Tiered indexing: Gemini (Tier 1) -> Local (Tier 2)

### Usage
```python
indexer = VideoIndexer(channel="undaodu")
result = indexer.index_live_stream(stream_url)  # Live streams
result = indexer.index_video_gemini(video_id)   # VOD
```

---

## Phase 7: HoloIndex Integration (NEW V0.8.0)

**Status**: COMPLETE (2026-01-11)

### Capabilities
- [x] ChromaDB vector storage at E:/HoloIndex/vectors/
- [x] Semantic search across video segments
- [x] Entity correction (STT error fixes: edu.org -> eduit.org)
- [x] Deep links with timestamps (youtube.com/watch?v=...&t=XX)
- [x] `video_search.py` in holo_index/core/
- [x] Integration with gemini_video_analyzer (auto-index on save)
- [x] Safe batch indexing with corruption prevention
- [x] SQLite audit metadata index for segments

### Usage
```python
from holo_index.core.video_search import VideoContentIndex

index = VideoContentIndex()
matches = index.search("education singularity", k=3)
for m in matches:
    print(m.to_reference())  # "012 discussed this at https://..."
```

### Current Index
- 36 segments from 2 videos indexed
- video_segments collection in ChromaDB

---

## Phase 8: Quality Metrics (NEW V0.9.0)

**Status**: COMPLETE (2026-01-11)

### Capabilities
- [x] Resolution analysis (1080p/720p/480p/360p)
- [x] Bitrate analysis (Mbps)
- [x] Frame rate analysis (fps)
- [x] Quality score (0-1 normalized)
- [x] Quality tier classification (high/medium/low/poor)
- [x] Issue detection
- [x] `quality_analyzer.py` (312 lines)

### Usage
```python
from modules.ai_intelligence.video_indexer.src.quality_analyzer import analyze_video_quality_yt

quality = analyze_video_quality_yt("VIDEO_ID")
print(f"Quality: {quality.quality_tier} ({quality.quality_score:.2f})")
```

---

## Phase 9: Gemma Segment Classifier (NEW V0.10.0)

**Status**: COMPLETE (2026-01-12)

### Capabilities
- [x] Heuristic pre-filter (<5ms per segment)
- [x] Gemma binary classification (<50ms via llama_cpp)
- [x] Quality tier classification (0=LOW, 1=REGULAR, 2=HIGH)
- [x] Training-worthy segment filtering
- [x] Batch classification support
- [x] `gemma_segment_classifier.py` (400+ lines)

### Architecture
```
WSP 77 Agent Coordination:
  Phase 1: Heuristic pre-filter (<5ms)
     - Keyword detection (HIGH: "key insight", LOW: "um", "uh")
     - Word count validation
     - Returns confident classifications immediately

  Phase 2: Gemma validation (<50ms)
     - Binary question: "Is this training-worthy? YES/NO"
     - Uses Gemma 3 270M via llama_cpp
     - Model: E:/HoloIndex/models/gemma-3-270m-it-Q4_K_M.gguf
```

### Usage
```python
from modules.ai_intelligence.video_indexer.src.gemma_segment_classifier import (
    get_segment_classifier
)

classifier = get_segment_classifier()

# Single segment
result = classifier.classify_segment(
    segment_text="The key insight is that education must be democratized",
    video_title="Education Singularity"
)
print(f"Tier: {result.tier}, Confidence: {result.confidence:.2f}")

# Batch for Digital Twin training
segments = [...] # List of segment dicts
worthy = classifier.get_training_worthy_segments(segments, "Video Title")
print(f"Training-worthy: {len(worthy)}/{len(segments)}")
```

---

## ARCHITECTURE

### Tiered Indexing Approach

```
YouTube Video
    |
    +-> Tier 1: Gemini AI (PREFERRED)
    |   - Single API call, no download
    |   - Works with live streams
    |   - ~30 seconds per video
    |   - Returns timestamped segments
    |
    +-> Tier 2: Local Pipeline (FALLBACK)
        - yt-dlp download + Whisper + OpenCV
        - Full visual frame extraction
        - Used when Gemini unavailable
```

### Data Flow

```
Gemini Analysis
    |
    +-> JSON Storage (memory/video_index/{channel}/{video_id}.json)
    |
    +-> HoloIndex ChromaDB (E:/HoloIndex/vectors/video_segments)
    |       |
    |       +-> Entity Correction (edu.org -> eduit.org)
    |       +-> Sentence Embeddings (all-MiniLM-L6-v2)
    |       +-> Semantic Search
    |
    +-> 012 Digital Twin (VideoMatch.to_reference())
```

---

## Dependencies

### Core (Installed)
```
whisper>=1.0.0           # Transcription
chromadb>=0.4.0          # Vector storage
sentence-transformers    # Embeddings
opencv-python>=4.8.0     # Frame extraction
yt-dlp                   # Video download
google-genai             # Gemini AI
```

### Optional (Future Enhancement)
```
pyannote.audio>=3.0.0    # Speaker diarization (GPU required)
spacy>=3.7.0             # NLP topic extraction
ultralytics              # YOLO object detection
```

---

## Success Metrics

| Phase | Metric | Target | Current |
|-------|--------|--------|---------|
| 1 | Transcripts indexed | 100% | WORKING |
| 2 | Visual frames extracted | 1 frame/sec | WORKING |
| 3 | Moments aligned | 90% sync | WORKING |
| 4 | Clip candidates | 3-5 per video | WORKING |
| 5 | DAE auto-index | < 1 hour | PARTIAL |
| 6 | Gemini analysis | ~30 seconds | WORKING |
| 7 | HoloIndex search | < 100ms | WORKING |

---

## Integration Points

### With Comment Engagement DAE
```python
# Video knowledge enables informed replies
from holo_index.core.video_search import VideoContentIndex
index = VideoContentIndex()
matches = index.search(comment_text, k=3)
# 0102 can now reference 012's videos in replies
```

### With Digital Twin Training
```python
# Quality-aware content selection
from quality_analyzer import analyze_video_quality_yt
quality = analyze_video_quality_yt(video_id)
if quality.quality_tier == "high":
    # Include in training corpus
```

### With YouTube Shorts Scheduler
```python
# Clip candidates feed into scheduling
scheduler.add_clips(indexer.get_clip_candidates())
```

---

## Phase 10: WSP 77 Validation Layer (NEXT V0.12.0)

**Status**: DESIGN COMPLETE - READY FOR IMPLEMENTATION

### Problem Identified (2026-01-14)

During video index audit, found 13 videos (3.4%) with `segments: []` despite `success: True`.

**Root Cause** (lines 428-449 of `gemini_video_analyzer.py`):
```python
except json.JSONDecodeError as e:
    logger.warning("JSON parse failed, using raw text")
    return GeminiAnalysisResult(
        segments=[],           # EMPTY!
        transcript_summary=raw_text,  # JSON blob stored here
        success=True,          # BUG: STILL RETURNS TRUE!
    )
```

**Issues**:
1. Trailing commas in Gemini JSON output (Gemini quirk)
2. No validation gate before storage
3. `success=True` even when parsing failed

### WSP 77 Validation Layer Design

**ALL LOCAL AI** - No external API for validation (Gemini is SOURCE, not validator)

```
Gemini API Response (SOURCE - may produce bad JSON)
       |
       v
+-------------------+
| PHASE 1: Gemma    |  <5ms LOCAL (E:/HoloIndex/models/gemma-3-270m)
| Structural Check  |
+--------+----------+
        |
   +----+----+
   |         |
 VALID    INVALID
   |         |
   v         v
+-------+ +------------------+
| Store | | PHASE 2: Repair  |
| JSON  | | fix_trailing_commas()
+-------+ | re-parse JSON    |
          +--------+---------+
                   |
              +----+----+
              |         |
           REPAIRED   STILL INVALID
              |         |
              v         v
          +-------+ +------------------------+
          | Store | | PHASE 3: Qwen LOCAL    |  200-500ms
          | JSON  | | (E:/HoloIndex/models/) |
          +-------+ | Strategy Decision      |
                    | - Re-index?            |
                    | - Manual review?       |
                    +------------------------+
                              |
                              v
                    +------------------------+
                    | PHASE 4: HoloIndex     |  Pattern storage
                    | Store parse patterns   |
                    | for future learning    |
                    +------------------------+
```

**Key Principle**: Gemini API = DATA SOURCE only. Validation = 100% local Qwen/Gemma.

### Existing Components to Reuse

| Component | Purpose | WSP Reference |
|-----------|---------|---------------|
| `gemma_segment_classifier.py` | Heuristic + Gemma binary classification | WSP 77 Phase 1 |
| `repair_zero_segment_videos.py` | fix_trailing_commas() + JSON extraction | New |
| `ai_overseer.py` | Mission coordination (Qwen + Gemma + 0102) | WSP 77 |

### Implementation Plan

1. **Add validation gate in `_parse_response()`**:
   - Integrate `fix_trailing_commas()` before JSON parsing
   - Return `success=False` if no segments extracted
   - Store `parse_errors` in metadata

2. **Create `gemini_response_validator.py`**:
   - Structural validation (has `segments`, `title`, etc.)
   - JSON syntax repair (trailing commas, markdown extraction)
   - Binary valid/invalid decision

3. **Integrate with AI_Overseer pattern**:
   - Phase 1 (Gemma): Fast structural validation
   - Phase 2 (Qwen): Decide repair vs re-index
   - Phase 4 (Learning): Store parse error patterns

### Success Metrics

| Metric | Target | Before | After |
|--------|--------|--------|-------|
| Parse failures caught | 100% | 0% (silent fail) | 100% |
| Auto-repair rate | >80% | 0% | TBD |
| Zero-segment videos | 0% | 3.4% | 0% |

---

## Future Roadmap

### Near Term (V1.0)
- [ ] Batch index all UnDaoDu videos
- [ ] Integration with comment DAE for intelligent replies
- [ ] Full background daemon for new uploads

### Medium Term (V1.1+)
- [ ] Speaker diarization (pyannote.audio)
- [ ] Advanced topic modeling (BERTopic)
- [ ] Object detection (YOLO)

### Long Term (V2.0)
- [ ] Embedding-based alignment (CLIP)
- [ ] ML-based virality prediction
- [ ] Real-time live stream processing

---

**Last Updated**: 2026-01-17
**Module Version**: V0.18.0
**Total Lines of Code**: 6,500+
