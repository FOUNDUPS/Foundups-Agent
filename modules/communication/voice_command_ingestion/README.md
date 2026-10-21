# voice_command_ingestion

Domain: communication
Status: MVP
WSP: WSP 3, WSP 11, WSP 22, WSP 49, WSP 84

## Overview

Japanese input is available through `FasterWhisperSTT(language="ja")` and
`get_voice_ingestion(language="ja")`; the existing default remains English.
Use `language=None` for Whisper detection and a multilingual model (not `.en`).
The [Japanese message-call prototype](../../platform_integration/elevenlabs_calls/README.md)
reuses this STT through the CLI speech adapter; telephone speech is hosted by
ElevenLabs. Batch-transcriber language behavior is unchanged.

voice_command_ingestion converts live audio into text events using faster-whisper,
detects the "0102" trigger token, and emits command events for WRE skill routing.

## Architecture

```
AudioChunk (from youtube_live_audio)
        |
        v
FasterWhisperSTT (local, 4x faster than vanilla)
        |
        v
STTEvent (transcription + confidence)
        |
        v
TriggerDetector ("0102" pattern matching)
        |
        v
CommandEvent -> livechat_router -> WRE skills
```

## Key Classes

- **FasterWhisperSTT**: CTranslate2-optimized Whisper with lazy loading
- **TriggerDetector**: Regex patterns for "0102" variations
- **VoiceCommandIngestion**: Orchestrator combining STT + trigger detection
- **STTEvent**: Transcription result with timing and confidence
- **CommandEvent**: Detected command after trigger

## Trigger Patterns

The TriggerDetector recognizes multiple variations of "0102":
- `0102` (exact digits)
- `zero one zero two` (words)
- `oh one oh two` (common mishearing)
- `0 1 0 2` (spaced digits)
- `01 02` (grouped)

## Responsibilities

- Transcribe audio chunks using faster-whisper (local, no cloud)
- Detect trigger token "0102" in transcriptions
- Extract command text after trigger
- Emit CommandEvent for downstream skill routing
- Log all transcriptions for digital twin training

## Inputs and Outputs

Input:
- AudioChunk from youtube_live_audio (float32 @ 16kHz mono)
- Or PCM16 byte stream (legacy interface)

Output:
- STTEvent for each transcription
- CommandEvent when trigger "0102" detected

## Dependencies

- faster-whisper>=1.0.0 (CTranslate2 optimized Whisper)
- numpy>=1.21.0

## Usage

```python
from modules.communication.voice_command_ingestion.src.voice_command_ingestion import (
    get_voice_ingestion
)

# Get voice ingestion instance
ingestion = get_voice_ingestion(model_size="base", device="cpu")

# Transcribe single chunk
stt_event = ingestion.transcribe_audio(audio_chunk.audio)
print(f"Heard: '{stt_event.text}'")

# Process with trigger detection
stt_event, cmd_event = ingestion.process_single_chunk(audio_chunk.audio)
if cmd_event:
    print(f"Trigger detected! Command: '{cmd_event.command}'")

# Stream processing
for cmd in ingestion.run_on_audio_chunks(audio_source.stream_audio_chunks()):
    print(f"Command: {cmd.command}")
```

## Integration

- Receives AudioChunk from youtube_live_audio
- Routes CommandEvent via livechat_router.py to WRE skills
- Logs transcriptions to memory/ for PQN digital twin training

## Model Sizes

| Model | VRAM | Speed | Accuracy |
|-------|------|-------|----------|
| tiny | 1GB | Fastest | Lower |
| base | 1GB | Fast | Good |
| small | 2GB | Medium | Better |
| medium | 5GB | Slower | High |
| large-v3 | 10GB | Slowest | Best |

Recommended: `base` for real-time, `small` for accuracy

## Digital Twin and PQN Integration

- STT transcripts stored in memory/ for pattern analysis
- PQN experiments replay stored events for artifact analysis
- Transcripts form training data for 0102 digital twin profile

## Phase 2: Digital Twin Video Learning (Sprints 6-8)

### BatchTranscriber (Sprint 6)
Transcribe entire YouTube video archives:
```python
from voice_command_ingestion import get_batch_transcriber

transcriber = get_batch_transcriber(model_size="base")
segments = transcriber.transcribe_channel("UC-LSSlOZwpGIRIYihaz8zCw", max_videos=10)
transcriber.save_transcripts_jsonl(segments, "012_transcripts.jsonl")
```

### VideoTranscriptIndex (Sprint 7)
Semantic search across transcripts:
```python
from transcript_index import get_transcript_index

index = get_transcript_index()
index.index_from_jsonl("memory/transcripts/012_transcripts.jsonl")
results = index.search("What did 012 say about WSP?")
for r in results:
    print(f"{r.text} -> {r.url}")  # Deep link to exact moment
```

### Digital Twin Query (Sprint 8)
MCP-compatible function:
```python
from transcript_index import search_012_transcripts

results = search_012_transcripts("recursive self-improvement")
# Returns: [{video_id, title, timestamp_sec, text, url, score}, ...]
```

## Testing

```bash
# Run end-to-end test with youtube_live_audio
python -m modules.platform_integration.youtube_live_audio.scripts.test_live_stt
```

## Logging

Structured log lines:
- `[STT] Loading faster-whisper model: {size} on {device}`
- `[STT] '{transcription}'`
- `[TRIGGER] Detected '0102' - Command: '{command}'`
