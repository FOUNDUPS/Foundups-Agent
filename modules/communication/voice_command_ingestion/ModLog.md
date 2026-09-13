# ModLog - voice_command_ingestion

### 2026-09-10 — Japanese STT selection and public export repair
**WSP Protocol:** 05, 06, 22, 84, 97
**Phase:** Enhancement
**Agent:** 0102 / Codex

- Removed the real-time adapter's forced English; added explicit language through
  ingestion and factory while retaining English defaults and rejecting `.en`
  model mismatches. Reused by the Japanese phone-message prototype.
- Restored batch classes/factory in package exports, resolving an existing batch
  test collection failure. No batch-transcription language change.
- Validation and test inventory: [tests/TestModLog.md](tests/TestModLog.md).

### 2026-02-24 - Faster-Whisper VAD Controls for Voice REPL Stability
**WSP Protocol**: WSP 22, WSP 84
**Phase**: Hardening
**Agent**: 0102

#### Changes
- `src/voice_command_ingestion.py`
  - Extended `FasterWhisperSTT` with configurable VAD controls:
    - `use_vad_filter` (bool)
    - `vad_min_silence_ms` (int)
  - `transcribe()` now conditionally passes `vad_filter` and `vad_parameters`.
  - Preserves previous behavior by default (`use_vad_filter=True`) for non-CLI callers.

#### Purpose
- Enables OpenClaw voice mode to disable aggressive VAD during short barge/cue captures,
  reducing false "Could not transcribe" loops from over-filtered audio.

---

### 2026-01-08 - Selenium Integration & Bug Fixes
**WSP Protocol**: WSP 22, WSP 62, WSP 84
**Phase**: Hardening
**Agent**: 0102

#### Bug Fixes
- **Double Path Bug**: Fixed `save_transcripts_jsonl` path doubling (memory/transcripts/memory/transcripts/)
- **yt-dlp Format Error**: Added fallback format `bestaudio[ext=m4a]/bestaudio/best` + browser cookies

#### Selenium Integration (Occam's Razor - Lego Blocks)
- Added `list_videos_via_selenium()` - Reuses YouTubeStudioDOM from youtube_shorts_scheduler
- Authenticated listing sees ALL videos (private/unlisted)
- Oldest-first sorting via URL parameter for historical indexing
- Chrome port 9222 (Move2Japan, UnDaoDu), Edge port 9223 (FoundUps)

#### Auto-Run Feature
- Option s4: Continuous auto-indexing of all channels
- Loops through channels, waits 5 minutes between rounds
- Ctrl+C to stop

---

### 2026-01-08 - Menu Integration: YouTube Indexing (Option 1.8)
**WSP Protocol**: WSP 22, WSP 62
**Phase**: Integration
**Agent**: 0102

#### Changes
- Created `scripts/index_channel.py` (540+ lines) - Launch script per WSP 62
- Implemented `index_channel(channel_key, max_videos, use_selenium, oldest_first)`
- Implemented `list_videos_via_selenium()` - Studio navigation
- Implemented `run_indexing_menu()` with Selenium options (s1-s4)
- Channel support: move2japan, undaodu, foundups
- Full pipeline: Selenium/yt-dlp -> faster-whisper -> ChromaDB

#### Menu Structure (main.py option 1 -> 8)
```
YouTube DAEs → 8. YouTube Indexing → Submenu:
  1-4. Index channels (yt-dlp)
  s1-s3. [SELENIUM] Index channels (authenticated, oldest first)
  s4. [SELENIUM] Auto-Index All (continuous)
  5. Search Transcripts
  6. Index Status
  7-8. Options (reindex/transcribe only)
```

#### Main Menu Restructure
- Option 0: Git Operations (now submenu with Push + History)
- Option 1: YouTube DAEs (added option 8 for indexing)
- Option 2: HoloDAE (search now directly integrated)
- Removed standalone options 11-12 (merged into submenus)
- Renumbered: 13->11, 14->12, 15->13

#### WSP Compliance
- WSP 62: Extracted to scripts/launch.py pattern
- WSP 22: ModLog documented
- WSP 84: Reuses existing infrastructure (YouTubeStudioDOM, BatchTranscriber, VideoTranscriptIndex)

---

### 2026-01-07 - Sprint 7-8: Transcript Index & Digital Twin Query (COMPLETE)
**WSP Protocol**: WSP 22, WSP 84, WSP 87
**Phase**: Implementation
**Agent**: 0102

#### Changes
- Created `transcript_index.py` (295 lines) for semantic search
- Implemented `VideoTranscriptIndex` class with ChromaDB + sentence-transformers
- Implemented `SearchResult` dataclass with semantic similarity score
- `index_transcript()`: Stores embedding + metadata in ChromaDB
- `index_from_jsonl()`: Batch indexing from JSONL transcripts
- `search()`: Semantic search with deep link URLs
- `search_012_transcripts()`: MCP-compatible function for digital twin
- `get_stats()` / `clear()`: Index management
- Updated INTERFACE.md with Sprint 7 documentation
- Updated ROADMAP.md to mark Sprints 7-8 complete

#### Architecture
```
memory/transcripts/*.jsonl → VideoTranscriptIndex → ChromaDB (E:/HoloIndex)
                                     ↓
                          search_012_transcripts(query)
                                     ↓
                    SearchResult with deep link + score
```

#### Key Feature: Digital Twin Query
```python
from transcript_index import search_012_transcripts
results = search_012_transcripts("What did 012 say about WSP?")
# Returns: [{video_id, title, timestamp, text, url, score}, ...]
```

#### WSP Compliance
- WSP 84: Reuses HoloIndex patterns (ChromaDB + sentence-transformers)
- WSP 87: Separate file to keep main module under 500 lines
- WSP 72: Module independent (standalone index)
- WSP 22: ModLog documented

#### Dependencies
- chromadb (vector storage)
- sentence-transformers (embeddings)

---

### 2026-01-08 - Sprint 6 Hardening (BatchTranscriber API + Tests)
**WSP Protocol**: WSP 11, WSP 22
**Phase**: Hardening
**Agent**: Codex

#### Changes
- Exported BatchTranscriber API via module __init__ for WSP 11 access
- Added BatchTranscriber unit tests (transcribe_video, save_transcripts_jsonl)
- Updated voice_pipeline.md sprint status to reflect Sprint 6 completion

---

### 2026-01-07 - Sprint 6: Batch Transcription Pipeline (COMPLETE)
**WSP Protocol**: WSP 22, WSP 50, WSP 84
**Phase**: Implementation
**Agent**: 0102

#### Changes
- Implemented `BatchTranscriber` class (197 lines added)
- Implemented `TranscriptSegment` dataclass for timestamped transcripts
- `transcribe_video()`: Yields TranscriptSegment with deep link URLs
- `transcribe_channel()`: Processes multiple videos with progress tracking
- `save_transcripts_jsonl()`: Stores transcripts to `memory/transcripts/`
- `get_progress()`: Returns progress dict for monitoring
- Added `get_batch_transcriber()` convenience function
- Updated INTERFACE.md with Phase 2 documentation
- Total module size: 594 lines (within WSP 87 limits)

#### Architecture
```
VideoArchiveExtractor (youtube_live_audio)
        ↓
    AudioChunk with timestamp_ms
        ↓
    BatchTranscriber (this module)
        ↓
    FasterWhisperSTT (reused)
        ↓
    TranscriptSegment with deep link URL
        ↓
    memory/transcripts/*.jsonl
```

#### Key Feature: Deep Link URLs
TranscriptSegment.url contains direct link to exact moment:
```
"What did 012 say about WSP?" → https://youtu.be/abc123?t=45
```

#### WSP Compliance
- WSP 84: Reuses FasterWhisperSTT (no new STT implementation)
- WSP 50: Pre-action verification (searched existing code first)
- WSP 22: ModLog documented
- WSP 72: Module independent (imports VideoArchiveExtractor)

#### Dependencies
- youtube_live_audio.VideoArchiveExtractor (audio source)
- faster-whisper (STT engine)

---

### 2026-01-07 - Phase 2 Roadmap: Digital Twin Transcript Learning
**WSP Protocol**: WSP 22, WSP 50
**Phase**: Planning
**Agent**: 0102

#### Changes
- Added Phase 2 roadmap (Sprints 6-8) for digital twin learning
- Sprint 6: Transcript Storage for Learning (live + archive sources)
- Sprint 7: Pattern Extraction from Transcripts (decisions, teaching moments)
- Sprint 8: Digital Twin Query Interface (MCP tool for "What did 012 say about X?")

#### Objective
Enable digital twin to learn from 012's spoken content:
- Store all transcripts with source metadata (live/archive/command)
- Extract patterns: recurring phrases, decision moments, emotional markers
- Query interface: semantic search across all 012 transcripts
- Integration with PQN for personality modeling

#### Architecture Notes
- STT engine: faster-whisper (already operational)
- Video archive extraction: handled by youtube_live_audio Phase 2
- This module focuses on learning patterns from transcripts
- Indexing follows HoloIndex patterns (SQLite + embeddings)

#### Impact
- Extends module from command detection to knowledge learning
- Foundation for "What did 012 say about X?" queries
- Cross-reference with git commits for decision-code correlation

#### WSP Compliance
- WSP 22: Roadmap documented
- WSP 50: Pre-action verification (searched existing infra first)

---

### 2026-01-03 - Sprint 3: LiveChat Routing Hook
**WSP Protocol**: WSP 3, WSP 11, WSP 22, WSP 84
**Phase**: Implementation
**Agent**: 0102

#### Changes
- Enhanced livechat_router.py with CommandEvent integration
- Added route_command_event() as main Sprint 3 entry point
- Added store_transcript_for_pqn() for PQN pattern learning
- Added get_voice_router() singleton accessor
- Created memory/voice_transcripts.jsonl for transcript storage
- Updated __init__.py to export Sprint 3 functions
- Updated INTERFACE.md with LiveChat Routing section

#### Architecture
- CommandEvent -> Synthetic LiveChat Message -> MessageProcessor
- Transcripts stored in JSONL format for PQN digital twin learning
- Lazy MessageProcessor initialization (avoids circular imports)

#### Integration
- Receives CommandEvent from VoiceCommandIngestion
- Builds synthetic livechat message with owner/mod privileges
- Routes through existing MessageProcessor pipeline
- Stores all transcripts for PQN analysis

#### Impact
- Sprint 3 complete: Voice commands route through livechat infrastructure
- PQN memory: Transcripts captured for 012 pattern learning

#### WSP Compliance
- WSP 84: Reuses existing MessageProcessor (no new orchestrator)
- WSP 3: communication domain (voice->livechat bridge)
- WSP 11: Interface documented in INTERFACE.md

### 2026-01-02 - Sprint 2: faster-whisper STT Implementation
**WSP Protocol**: WSP 3, WSP 11, WSP 22, WSP 84
**Phase**: Implementation
**Agent**: 0102

#### Changes
- Implemented FasterWhisperSTT class with lazy model loading
- Implemented TriggerDetector with regex patterns for "0102" variations:
  - "0102" (exact digits)
  - "zero one zero two" (words)
  - "oh one oh two" (common mishearing)
  - Spaced and grouped variants
- Implemented VoiceCommandIngestion orchestrator class
- Added stream_audio_to_text() for AudioChunk integration
- Added process_single_chunk() for testing/one-shot use
- Updated requirements.txt with faster-whisper dependency

#### Architecture Decision
- **faster-whisper over whisper.cpp**: 4x faster, same accuracy, pure Python
- Lazy initialization: Model loads on first use (not import time)
- VAD filter enabled: Automatically skips silence

#### Integration
- Receives AudioChunk from youtube_live_audio
- Emits STTEvent for each transcription
- Emits CommandEvent when trigger "0102" detected
- Routes to livechat_router.py for WRE skill execution

#### Impact
- Sprint 2 complete: STT + trigger detection operational
- End-to-end pipeline: YouTube Live -> Audio -> STT -> Command

#### WSP Compliance
- WSP 84: Reuses faster-whisper (no new STT implementation)
- WSP 3: communication domain (voice processing)
- WSP 11: Public interface defined

### 2026-01-01 - LiveChat routing reuse and sprint roadmap
**WSP Protocol**: WSP 22, WSP 84
**Phase**: Enhancement
**Agent**: Codex

#### Changes
- Documented reuse of LiveChat command routing (no new orchestrator)
- Converted roadmap to sprint plan and updated pipeline docs

#### Impact
- Ensures voice commands follow existing LiveChat command handling

#### WSP Compliance
- WSP 84 duplication avoidance

### 2026-01-01 - Switch default STT backend to whisper.cpp
**WSP Protocol**: WSP 22, WSP 62
**Phase**: Enhancement
**Agent**: Codex

#### Changes
- Updated default STT backend to whisper.cpp in interface and docs
- Documented Vosk as fallback streaming backend

#### Impact
- Aligns MVP with higher accuracy local STT while staying offline

#### WSP Compliance
- WSP 62 size and dependency awareness documented

### 2026-01-01 - Initial scaffolding for voice command ingestion
**WSP Protocol**: WSP 3, WSP 22, WSP 49
**Phase**: Initial Creation
**Agent**: Codex

#### Changes
- Added module structure, documentation, and interface stubs
- Added placeholder tests and memory documentation
- Added requirements list for local STT

#### Impact
- Establishes the communication block for live voice commands

#### WSP Compliance
- WSP 3 domain placement
- WSP 49 module structure
