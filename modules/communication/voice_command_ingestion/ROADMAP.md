# voice_command_ingestion Roadmap (Sprint Plan)

## Japanese input integration (2026-09-10)
- [x] Explicit Japanese/detection selection in real-time Whisper and ingestion.
- [x] Shared CLI adapter use by the Japanese message-call prototype.
- [ ] Benchmark Japanese microphone recognition on the operator's workstation.

## Sprint 0 - Architecture Lock (COMPLETE)
- [x] Confirm reuse of LiveChat routing (message_processor/message_router)
- [x] Document whisper.cpp vs faster-whisper decision
- [x] Update docs and interfaces

## Sprint 1 - Streaming STT (COMPLETE - 2026-01-02)
Architecture Decision: faster-whisper over whisper.cpp (4x faster, pure Python)
- [x] Implement FasterWhisperSTT with lazy model loading
- [x] Implement stream_audio_to_text() for AudioChunk integration
- [x] VAD filter enabled (auto-skip silence)
- [x] Log latency and confidence scores

## Sprint 2 - Trigger Detection (COMPLETE - 2026-01-02)
- [x] Implement TriggerDetector with regex patterns
- [x] Handle variations: "0102", "zero one zero two", "oh one oh two"
- [x] Extract command text after trigger
- [x] Emit CommandEvent with timestamp and confidence
- [x] Tests passing for all trigger patterns

## Sprint 3 - LiveChat Routing Hook (COMPLETE - 2026-01-03)
- [x] Convert CommandEvent into synthetic livechat message payload
- [x] Route through livechat_router.py (LiveChatVoiceRouter)
- [x] Ensure command handler path is exercised (MessageProcessor)
- [x] Store transcripts in memory/ for PQN (voice_transcripts.jsonl)

## Sprint 4 - Skill Routing (DEFERRED)
Occam's Razor: MessageProcessor already routes commands. Defer until skills exist.
- [ ] Map command text to WRE skills (rule-based)
- [ ] One demo command (e.g., "send email", "take screenshot")
- [ ] Emit no_match for unknown commands

## Sprint 5 - End-to-End Soak (COMPLETE - 2026-01-04)
- [x] Run with youtube_live_audio for 2 minutes (stability test)
- [x] Monitor memory usage and latency (stable, no leaks)
- [x] Pipeline stable with 0 errors over 24 chunks
- [x] Ready for extended soak when audio available

---

# PHASE 2: DIGITAL TWIN TRANSCRIPT LEARNING

**Objective**: Enable digital twin to learn from 012's spoken content (live + archive)

## Sprint 6 - Batch Transcription Pipeline (COMPLETE - 2026-01-07)
Architecture Decision: BatchTranscriber connects VideoArchiveExtractor with faster-whisper
- [x] Implement BatchTranscriber class with progress tracking
- [x] TranscriptSegment dataclass with video_id, title, timestamp, text, confidence, url
- [x] transcribe_video() yields TranscriptSegment with timestamps
- [x] transcribe_channel() processes multiple videos with progress tracking
- [x] save_transcripts_jsonl() stores transcripts to `memory/transcripts/`
- [x] Deep link URLs: `https://youtu.be/VIDEO_ID?t=TIMESTAMP`
- [x] Skip empty/silence chunks (deduplication)

## Sprint 7 - Transcript Index (COMPLETE - 2026-01-07)
Architecture Decision: ChromaDB + sentence-transformers (HoloIndex pattern)
- [x] Implement VideoTranscriptIndex class in transcript_index.py
- [x] SearchResult dataclass with semantic similarity score
- [x] index_transcript() stores embedding + metadata in ChromaDB
- [x] index_from_jsonl() batch indexing from JSONL transcripts
- [x] search() semantic search with deep link URLs
- [x] search_012_transcripts() MCP-compatible function
- [x] Lazy initialization (model loads on first use)

## Sprint 8 - Digital Twin Query Interface (COMPLETE - 2026-01-07)
- [x] "What did 012 say about [topic]?" → search_012_transcripts(query)
- [x] Deep links to exact video moments in results
- [ ] Pattern extraction: recurring topics, teaching moments (FUTURE)
- [ ] Cross-reference with git commits by timestamp (FUTURE)
- [ ] Integration with PQN for personality modeling (FUTURE)

## Notes
- faster-whisper chosen for 4x speedup and pure Python integration
- Lazy initialization: Model loads on first transcribe() call
- Trigger patterns handle common Whisper misrecognitions of "0102"
- Video archive transcription handled by youtube_live_audio Phase 2
- This module provides the STT engine; indexing handled by HoloIndex patterns
