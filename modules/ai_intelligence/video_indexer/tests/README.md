# Video Indexer Test Suite

`test_audio_transcript_language.py` covers the reused batch and local-file
language parameters, Japanese/mixed/unknown labels and chunk start positions.
Its extractor, metadata request and model are fake; no live content changes.

**WSP Compliance**: WSP 5 (Test Coverage), WSP 6 (Test Audit), WSP 49 (Module Structure)

## Purpose

This test suite validates the video_indexer module's ability to index 012's YouTube channels for knowledge extraction. Tests verify the complete pipeline from Selenium navigation to multimodal indexing.

## Stage Test Plan (Video DAE System)

The Video Indexer uses a staged validation approach to ensure each component works before proceeding to the next. This allows 012 to observe progress visually in the browser.

```
┌──────────────────────────────────────────────────────────────────────────┐
│                     VIDEO DAE STAGE TEST PIPELINE                        │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Stage 1 ──► Stage 2 ──► Stage 3 ──► Stage 4 ──► [Future Stages]        │
│  Navigate    Batch       Index       Validate    Full Channel            │
│  (1 video)   (10 videos) (single)    (quality)   + Viral Learning        │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

### Stage 1: Navigation (COMPLETE)
**File**: `test_integration_oldest_video.py`
- Find oldest video via YouTube Studio DOM clicks
- Verify video ID matches known oldest (8_DUQaqY6Tc)
- Uses YouTubeStudioDOM pattern from commenting system

### Stage 2: Batch Navigation (COMPLETE)
**File**: `test_stage2_batch_navigation.py`
- Navigate to YouTube Studio with clean URL (no filter params)
- Click Date header to sort oldest first (DOM click avoids bot detection)
- Extract 10+ video IDs and metadata
- Validates batch discovery for channel indexing

### Stage 3: Single Video Indexing (COMPLETE)
**File**: `test_stage3_video_indexing.py`
- Full 4-phase indexing pipeline on single video
- Audio (ASR), Visual (keyframes), Multimodal (alignment), Clips (candidates)
- Saves index to `memory/video_index/{channel}/{video_id}.json`

### Stage 4: Indexing Validation (COMPLETE)
**File**: `test_stage4_validation.py`
- Load saved index and validate structure
- Check audio segments have timestamps and text
- Check visual keyframes have frame data
- Check clip candidates have virality scores
- Calculate quality score for indexed video

### Future Stages (PLANNED)
- **Stage 5**: Full Channel Indexing (all 2321 UnDaoDu videos)
- **Stage 6**: Viral Video Learning (analyze videos with 1M+ views)
- **Stage 7**: Apply to 012's Content (repurpose insights)

## Test Categories

### 1. Unit Tests (Offline)
Test individual components without external dependencies:
- `test_indexer_config.py` - Feature flag parsing
- `test_indexer_telemetry.py` - Heartbeat and health calculation
- `test_clip_generator.py` - Virality scoring algorithms
- `test_multimodal_aligner.py` - Moment alignment logic
- `test_studio_ask_indexer_persistence.py` - Ask-Gemini JSON persistence
- `test_studio_ask_indexer_signals.py` - STOP/reindex signals + counts

### 2. Integration Tests (Requires Browser)
Test full pipeline with Selenium automation:
- `test_integration_oldest_video.py` - Stage 1: Navigate to oldest video
- `test_stage2_batch_navigation.py` - Stage 2: Find 10+ videos
- `test_stage3_video_indexing.py` - Stage 3: Full indexing pipeline
- `test_stage4_validation.py` - Stage 4: Validate index quality
- `test_selenium_navigation.py` - Visual browser demo for 012

### 3. Component Tests
Test individual analyzers with mocked inputs:
- `test_audio_analyzer.py` - ASR integration with batch_transcriber
- `test_visual_analyzer.py` - OpenCV frame extraction
- `test_video_index_store.py` - JSON artifact storage

## Key Integration Test: UnDaoDu Oldest Video

**File**: `test_integration_oldest_video.py`

**Purpose**: Validate end-to-end indexing by processing UnDaoDu's oldest video (2009).

**What 012 Should See**:
1. Chrome browser opens (port 9222)
2. Navigates to YouTube Studio for UnDaoDu channel
3. Video list sorted oldest-first
4. First video (2009) selected and indexed
5. Console output showing indexing progress

**Why UnDaoDu 2009 Video**:
- UnDaoDu is 012's consciousness exploration channel
- 2009 video is earliest content - foundational to 012's YouTube presence
- Tests full pipeline with real historical content
- Validates that ancient videos still process correctly

## Running Tests

### Prerequisites
```bash
# Ensure Chrome is running with remote debugging
"C:\Program Files\Google\Chrome\Application\chrome.exe" ^
    --remote-debugging-port=9222 ^
    --user-data-dir="%LOCALAPPDATA%\Google\Chrome\User Data"
```

### Run All Tests
```bash
cd O:\Foundups-Agent
python -m pytest modules/ai_intelligence/video_indexer/tests/ -v
```

### Run Integration Test Only
```bash
python -m pytest modules/ai_intelligence/video_indexer/tests/test_integration_oldest_video.py -v -s
```

### Run Offline Tests Only
```bash
python -m pytest modules/ai_intelligence/video_indexer/tests/ -v -m "not integration"
```

## Test Fixtures

### Channel Configuration
```python
CHANNELS = {
    "undaodu": {
        "id": "UCfHM9Fw9HD-NwiS0seD_oIA",
        "name": "UnDaoDu",
        "chrome_port": 9222,
    },
    "move2japan": {
        "id": "UC-LSSlOZwpGIRIYihaz8zCw",
        "name": "Move2Japan",
        "chrome_port": 9222,
    },
    "foundups": {
        "id": "UCSNTUXjAgpd4sgWYP0xoJgw",
        "name": "FoundUps",
        "chrome_port": 9223,  # Edge browser
    },
}
```

### Environment Variables
```bash
# Enable/disable layers for testing
VIDEO_INDEXER_AUDIO_ENABLED=true
VIDEO_INDEXER_VISUAL_ENABLED=true
VIDEO_INDEXER_MULTIMODAL_ENABLED=true
VIDEO_INDEXER_CLIPS_ENABLED=true
VIDEO_INDEXER_DRY_RUN=false
VIDEO_INDEXER_VERBOSE=true
```

## Test Artifacts

Tests produce artifacts in `memory/video_index/`:
```
memory/video_index/
├── undaodu_oldest_2009.json     # Index data for 2009 video
├── video_cache/                  # Downloaded video files
│   └── {video_id}.mp4
└── test_results/                 # Test run artifacts
    └── integration_run_{timestamp}.json
```

## Dependencies

```python
# Core
pytest>=7.0.0
pytest-asyncio>=0.21.0

# Selenium (reuse from foundups_selenium)
selenium>=4.10.0

# Module dependencies
from modules.communication.voice_command_ingestion.scripts.index_channel import (
    list_videos_via_selenium, CHANNELS
)
from modules.ai_intelligence.video_indexer.src.video_indexer import VideoIndexer
```

## WSP Compliance

| WSP | Description | Implementation |
|-----|-------------|----------------|
| WSP 5 | Test Coverage | All 4 phases tested |
| WSP 6 | Test Audit | This README documents test strategy |
| WSP 49 | Module Structure | tests/ directory per spec |
| WSP 50 | Pre-Action Verification | Reuses existing Selenium patterns |
| WSP 84 | Code Reuse | Uses index_channel.py patterns |

## Test Evolution Log

| Date | Test Added | Purpose |
|------|------------|---------|
| 2026-01-09 | test_integration_oldest_video.py | Stage 1: Navigate to oldest UnDaoDu video |
| 2026-01-10 | test_selenium_navigation.py | Visual browser demo for 012 observation |
| 2026-01-10 | test_stage2_batch_navigation.py | Stage 2: Find 10+ videos with DOM clicks |
| 2026-01-10 | test_stage3_video_indexing.py | Stage 3: Full 4-phase indexing pipeline |
| 2026-01-10 | test_stage4_validation.py | Stage 4: Index quality validation |
| 2026-01-10 | test_gemini_video_analyzer.py | Gemini AI video analysis (Tier 1 method) |
| 2026-02-06 | test_studio_ask_indexer_persistence.py | Ask-Gemini JSON persistence (offline) |
| 2026-02-06 | test_studio_ask_indexer_signals.py | Ask-Gemini daemon signals + counts |

## Gemini Video Analyzer (PRIMARY METHOD)

**File**: `test_gemini_video_analyzer.py`

**Discovery**: Gemini 2.0 Flash can analyze YouTube videos directly via URL:
```python
Part.from_uri(youtube_url, mime_type='video/mp4')
```

**Usage**:
```bash
# Run all Gemini tests
python modules/ai_intelligence/video_indexer/tests/test_gemini_video_analyzer.py

# Run with pytest
python -m pytest modules/ai_intelligence/video_indexer/tests/test_gemini_video_analyzer.py -v
```

**Requirements**: `GOOGLE_API_KEY` environment variable

**Test Results**:
- Analyzes 6-minute video in ~25 seconds
- Returns 14-16 timestamped segments
- Identifies speakers, topics, key points
- Works with both VOD and LIVE streams

## Running Stage Tests Sequentially

Run each stage to validate the complete Video DAE pipeline:

```bash
# Stage 1: Can we find the oldest video?
python modules/ai_intelligence/video_indexer/tests/test_integration_oldest_video.py

# Stage 2: Can we find 10+ videos?
python modules/ai_intelligence/video_indexer/tests/test_stage2_batch_navigation.py

# Stage 3: Can we index a video? (requires Stage 2 success)
python modules/ai_intelligence/video_indexer/tests/test_stage3_video_indexing.py

# Stage 4: Is the index valid? (requires Stage 3 success)
python modules/ai_intelligence/video_indexer/tests/test_stage4_validation.py
```

## Browser Requirements

The tests use YouTubeStudioDOM pattern from commenting system (WSP 84: Code Reuse):

```bash
# Chrome for UnDaoDu/Move2Japan (port 9222)
"C:\Program Files\Google\Chrome\Application\chrome.exe" ^
    --remote-debugging-port=9222 ^
    --user-data-dir="%LOCALAPPDATA%\Google\Chrome\User Data"

# Edge for FoundUps/antifaFM (port 9223)
"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" ^
    --remote-debugging-port=9223 ^
    --user-data-dir="%LOCALAPPDATA%\Microsoft\Edge\User Data"
```

**IMPORTANT**: URL filters trigger YouTube bot detection (CAPTCHA). Tests use clean URLs + DOM clicks on the Date header to sort videos.

---

*Tests are 012's memory verification - ensuring 0102 correctly indexes and recalls 012's teachings.*
