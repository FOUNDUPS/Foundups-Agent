# voice_command_ingestion Interface

## Japanese input (2026-09-10)

`FasterWhisperSTT`, `VoiceCommandIngestion` and `get_voice_ingestion` accept an
optional trailing `language: Optional[str] = "en"`. Use `"ja"` for Japanese or
`None` for Whisper auto-detection. English-only `.en` models reject non-English
and detection requests before loading. The batch API is unchanged.
The package exports the documented BatchTranscriber/TranscriptSegment factory
as well as FasterWhisperSTT and get_voice_ingestion.

## STTEvent
```python
STTEvent(
    text: str,           # Transcribed text
    is_final: bool,      # Always True for faster-whisper
    start_ms: int,       # Start time in milliseconds
    end_ms: int,         # End time in milliseconds
    confidence: float,   # Confidence score (0-1)
)
```

## CommandEvent
```python
CommandEvent(
    command: str,           # Command text after trigger
    raw_text: str,          # Full transcription
    trigger_detected: bool, # Always True when emitted
    timestamp_iso: str,     # ISO timestamp
    confidence: float,      # STT confidence
)
```

## FasterWhisperSTT
```python
stt = FasterWhisperSTT(
    model_size: str = "base",      # tiny, base, small, medium, large-v3
    device: str = "cpu",           # cpu or cuda
    compute_type: str = "int8",    # int8, float16, float32
)
```

### transcribe
```python
transcribe(audio: np.ndarray, sample_rate: int = 16000) -> Optional[STTEvent]
```
Transcribe audio chunk to text.

### transcribe_stream
```python
transcribe_stream(audio_chunks: Iterable[np.ndarray], sample_rate: int = 16000) -> Generator[STTEvent, None, None]
```
Transcribe streaming audio chunks.

## TriggerDetector
```python
detector = TriggerDetector(trigger_token: str = "0102")
```

### detect
```python
detect(text: str) -> tuple[bool, str, str]
```
Returns `(trigger_found, command_after_trigger, full_text)`.

Recognizes patterns:
- `0102` (exact digits)
- `zero one zero two` (words)
- `oh one oh two` (common mishearing)
- `0 1 0 2` (spaced)
- `01 02` (grouped)

## VoiceCommandIngestion
```python
ingestion = VoiceCommandIngestion(
    trigger_token: str = "0102",
    stt_backend: str = "faster_whisper",
    command_window_seconds: int = 5,
    model_size: str = "base",
    device: str = "cpu",
)
```

### transcribe_audio
```python
transcribe_audio(audio: np.ndarray, sample_rate: int = 16000) -> Optional[STTEvent]
```
Transcribe a single audio chunk.

### stream_to_text
```python
stream_to_text(audio_stream: Iterable[bytes]) -> Iterator[STTEvent]
```
Convert PCM16 audio chunks into streaming STT events.

### stream_audio_to_text
```python
stream_audio_to_text(audio_chunks: Iterable[np.ndarray]) -> Iterator[STTEvent]
```
Convert float32 audio chunks into STT events. **Preferred interface.**

### detect_commands
```python
detect_commands(events: Iterable[STTEvent]) -> Iterator[CommandEvent]
```
Detect trigger tokens and emit command events.

### run
```python
run(audio_stream: Iterable[bytes]) -> Iterator[CommandEvent]
```
End-to-end pipeline: PCM16 bytes -> STT -> trigger -> commands.

### run_on_audio_chunks
```python
run_on_audio_chunks(audio_chunks: Iterable[np.ndarray]) -> Iterator[CommandEvent]
```
End-to-end pipeline for float32 audio. **Preferred interface.**

### process_single_chunk
```python
process_single_chunk(audio: np.ndarray) -> tuple[Optional[STTEvent], Optional[CommandEvent]]
```
Process single chunk and check for trigger. Convenience method.

## Convenience Function
```python
get_voice_ingestion(
    trigger_token: str = "0102",
    model_size: str = "base",
    device: str = "cpu"
) -> VoiceCommandIngestion
```

## LiveChat Routing (Sprint 3)

### LiveChatVoiceRouter
```python
router = LiveChatVoiceRouter(
    identity: Optional[LiveChatIdentity] = None,
    message_processor: Optional[MessageProcessor] = None,
)
```

Routes voice commands through livechat MessageProcessor.

### route_command_event
```python
route_command_event(
    event: CommandEvent,
    router: Optional[LiveChatVoiceRouter] = None,
    store_for_pqn: bool = True,
) -> Optional[Dict[str, Any]]
```
Main Sprint 3 integration point. Routes CommandEvent through livechat infrastructure
and stores transcript for PQN learning.

### store_transcript_for_pqn
```python
store_transcript_for_pqn(
    raw_text: str,
    command: str,
    confidence: float = 1.0,
    timestamp_iso: Optional[str] = None,
) -> None
```
Store voice transcript in `memory/voice_transcripts.jsonl` for PQN pattern learning.

### get_voice_router
```python
get_voice_router() -> LiveChatVoiceRouter
```
Get or create singleton voice router instance.

---

# PHASE 2: BATCH TRANSCRIPTION (Sprint 6)

## TranscriptSegment
```python
TranscriptSegment(
    video_id: str,        # YouTube video ID
    title: str,           # Video title
    timestamp_sec: float, # Position in video (seconds)
    end_sec: float,       # End of segment
    text: str,            # Transcribed text
    confidence: float,    # STT confidence (0-1)
    url: str,             # Deep link URL with timestamp
)
```

## BatchTranscriber
```python
transcriber = BatchTranscriber(
    model_size: str = "base",      # tiny, base, small, medium, large-v3
    device: str = "cpu",           # cpu or cuda
    output_dir: Optional[str] = None,  # Default: memory/transcripts
)
```

### transcribe_video
```python
transcribe_video(
    video_id: str,
    title: str,
    audio_chunks: Iterable[AudioChunk],
    chunk_duration_sec: float = 30.0
) -> Generator[TranscriptSegment, None, None]
```
Transcribe a video's audio chunks to text segments with timestamps.

### transcribe_channel
```python
transcribe_channel(
    channel_id: str,
    max_videos: int = 10,
    cache_dir: Optional[str] = None
) -> Generator[TranscriptSegment, None, None]
```
Transcribe all videos from a YouTube channel. Uses VideoArchiveExtractor from youtube_live_audio.

### save_transcripts_jsonl
```python
save_transcripts_jsonl(
    segments: Iterable[TranscriptSegment],
    filename: str
) -> int
```
Save transcript segments to JSONL file. Returns number of segments saved.

### get_progress
```python
get_progress(channel_id: str) -> dict
```
Get transcription progress: `{total_videos, completed_videos, total_segments, status}`.

## Convenience Function
```python
get_batch_transcriber(
    model_size: str = "base",
    device: str = "cpu",
    output_dir: Optional[str] = None
) -> BatchTranscriber
```

---

# PHASE 2: TRANSCRIPT INDEX (Sprint 7)

## SearchResult
```python
SearchResult(
    video_id: str,        # YouTube video ID
    title: str,           # Video title
    timestamp_sec: float, # Position in video
    end_sec: float,       # End of segment
    text: str,            # Transcript text
    confidence: float,    # STT confidence (0-1)
    url: str,             # Deep link URL
    score: float,         # Semantic similarity score (0-1)
)
```

## VideoTranscriptIndex
```python
index = VideoTranscriptIndex(
    ssd_path: Optional[str] = None,      # Default: E:/HoloIndex
    collection_name: str = "video_transcripts"
)
```

### index_transcript
```python
index_transcript(
    video_id, title, timestamp_sec, end_sec, text, confidence, url
) -> bool
```
Index a single transcript segment into ChromaDB.

### index_from_jsonl
```python
index_from_jsonl(jsonl_path: str) -> int
```
Index all transcripts from JSONL file. Returns count indexed.

### search
```python
search(
    query: str,
    limit: int = 10,
    min_score: float = 0.3
) -> List[SearchResult]
```
Semantic search across transcripts. Returns results with deep links.

### get_stats / clear
```python
get_stats() -> dict     # {collection, segment_count, ssd_path}
clear() -> bool         # Clear all indexed transcripts
```

## Convenience Functions
```python
get_transcript_index(ssd_path, collection_name) -> VideoTranscriptIndex
search_012_transcripts(query, limit) -> List[dict]  # MCP-compatible
```

## Notes
- Uses faster-whisper (CTranslate2 optimized, 4x faster)
- Lazy model loading (loads on first use)
- VAD filter enabled (skips silence automatically)
- Route CommandEvent into LiveChat command handling
- PQN transcripts stored in `memory/voice_transcripts.jsonl`
- **Batch transcripts** stored in `memory/transcripts/` (JSONL)
- **Transcript index** stored in `E:/HoloIndex/vectors/` (ChromaDB)
- Deep link URLs enable "What did 012 say about X?" → `https://youtu.be/VIDEO_ID?t=TIMESTAMP`
