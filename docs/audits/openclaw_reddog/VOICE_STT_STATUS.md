# OpenClaw Voice STT Status

**Audit Date**: 2026-04-03
**Worker**: G
**PR Reference**: #258 (MERGED 2026-04-02)

---

## Current State

### What Exists (MERGED to main)

| Component | Location | Status |
|-----------|----------|--------|
| `openclaw_voice.py` | `infrastructure/cli/src/` | MERGED |
| `CohereTranscribeBackend` | lines 215-282 | REAL |
| `WhisperSTTBackend` | lines 44-87 | REAL |
| `GoogleSTTBackend` | lines 90-116 | REAL |
| Lazy singleton loader | lines 121-214 | REAL |

### Capability Chain

```
Audio Input
    ↓
[1] Cohere Transcribe (local, lazy, 2B model)
    ↓ (fallback)
[2] faster-whisper (local, no internet)
    ↓ (fallback)
[3] Google Speech (cloud, needs internet)
    ↓
Transcribed Text → OpenClaw DAE
```

---

## API Surface

### Entry Points

| Entry | Type | Callable From |
|-------|------|---------------|
| `python main.py --voice` | CLI | Terminal |
| `openclaw_voice.py` module | Python | CLI |
| WASAPI audio capture | System | Local only |

**NOT browser-callable.** No HTTP/WebSocket API exposed.

### Python Interface

```python
# STT backends
class CohereTranscribeBackend:
    def available(self) -> bool
    def transcribe(self, audio: np.ndarray, sample_rate: int = 16000) -> Optional[str]

class WhisperSTTBackend:
    def available(self) -> bool
    def transcribe(self, audio: np.ndarray, sample_rate: int = 16000) -> Optional[str]

class GoogleSTTBackend:
    def available(self) -> bool
    def transcribe(self, audio: np.ndarray, sample_rate: int = 16000) -> Optional[str]
```

---

## Auth/Permission Model

### Current

- Local CLI only (no auth needed - physical access implies auth)
- WASAPI audio capture requires local machine access
- No remote API exposed

### Red Dog Implication

Red Dog runs in browser shell.
Voice STT runs on local machine via CLI.
These are different execution contexts.

---

## Browser Integration Path

### What Would Be Needed

For Red Dog (browser) to use voice:

1. **Browser captures audio** via Web Audio API / MediaRecorder
2. **Audio sent to backend** via WebSocket or HTTP
3. **Backend routes to STT** via openclaw_voice backends
4. **Transcription returned** to browser
5. **Red Dog processes** text command

### What Exists Today

- Steps 1-2: NOT IMPLEMENTED (no audio ingress API)
- Steps 3-4: REAL (STT backends work)
- Step 5: REAL (OpenClaw DAE processes commands)

### Gap

No audio ingress API from browser to local STT backends.

---

## Model Details

### Cohere Transcribe (Primary)

| Property | Value |
|----------|-------|
| Model | `CohereForAI/c4ai-command-r-v01-4bit` (speech variant) |
| Size | ~2B parameters |
| Device | CUDA (GPU) or CPU fallback |
| Load time | 2-5 seconds (lazy singleton) |
| Format | transformers (AutoModelForSpeechSeq2Seq) |

### faster-whisper (Fallback 1)

| Property | Value |
|----------|-------|
| Model | `base` (default) |
| Size | ~74M parameters |
| Device | CPU |
| Load time | <1 second |
| Format | CTranslate2 |

### Google Speech (Fallback 2)

| Property | Value |
|----------|-------|
| Model | Cloud service |
| Requires | Internet connection |
| Auth | None (free tier) |

---

## Test Coverage

| Test File | Coverage |
|-----------|----------|
| `test_openclaw_voice_cue_parsing.py` | Cue detection |
| `test_voice_command_ingestion.py` | Whisper backend |

No dedicated tests for Cohere backend yet.

---

## Gaps

| Gap | Severity | Notes |
|-----|----------|-------|
| No browser audio ingress | HIGH | Required for Red Dog voice |
| No HTTP/WS API | HIGH | Required for remote access |
| No Cohere-specific tests | MEDIUM | Backend works but untested |
| WASAPI Windows-only | LOW | Linux/Mac would need alternative |

---

## Summary

**Voice STT is real but not browser-accessible.**

The STT backends work locally via CLI.
Red Dog (browser) cannot access them without:
1. WebSocket audio ingress endpoint
2. Backend audio routing to STT
3. Response channel back to browser

This is a significant gap for voice-enabled Red Dog.

---

## Smallest Safe Integration Step

If voice is desired for Red Dog:

1. Add WebSocket endpoint in gateway for audio chunks
2. Route chunks to `CohereTranscribeBackend.transcribe()`
3. Return transcription via WebSocket
4. Red Dog uses text result as command input

Estimated effort: 2-3 hours (new WebSocket handler + audio routing).

---

*Worker G - 2026-04-03*
