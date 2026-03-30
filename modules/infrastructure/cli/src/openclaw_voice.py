"""
OpenClaw Voice REPL - Talk to 0102 with your headset.

STT chain:  Cohere Transcribe (local, lazy) -> faster-whisper (local) -> Google (cloud)
TTS chain:  edge-tts (neural) -> pyttsx3 (local SAPI5) -> print-only fallback

Usage:
    python -m modules.infrastructure.cli.src.openclaw_voice
    python main.py --voice

Env vars:
    OPENCLAW_VOICE_DISABLE_COHERE_STT=1  Skip Cohere (use Whisper as primary)
    OPENCLAW_VOICE_DISABLE_WASAPI=1      Disable WASAPI shared mode

WSP Compliance:
    WSP 73: Partner (012 voice) -> Principal (OpenClawDAE) -> Associates (domain DAEs)
    WSP 84: Reuses FasterWhisperSTT from voice_command_ingestion
    WSP 91: Lazy singleton loading for Cohere Transcribe (observability)
"""

import asyncio
import io
import logging
import os
import re
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Optional

import numpy as np

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# STT Backends (degradation chain)
# ---------------------------------------------------------------------------

class WhisperSTTBackend:
    """Primary STT: faster-whisper (local, no internet)."""

    name = "faster-whisper"

    def __init__(
        self,
        model_size: str = "base",
        use_vad_filter: Optional[bool] = None,
        vad_min_silence_ms: Optional[int] = None,
    ):
        self._stt = None
        self._model_size = model_size
        if use_vad_filter is None:
            use_vad_filter = _env_truthy("OPENCLAW_VOICE_STT_VAD_FILTER", "0")
        if vad_min_silence_ms is None:
            try:
                vad_min_silence_ms = int(
                    os.getenv("OPENCLAW_VOICE_STT_VAD_MIN_SILENCE_MS", "180")
                )
            except ValueError:
                vad_min_silence_ms = 180
        self._use_vad_filter = bool(use_vad_filter)
        self._vad_min_silence_ms = max(50, int(vad_min_silence_ms))

    def available(self) -> bool:
        try:
            from modules.communication.voice_command_ingestion.src.voice_command_ingestion import (
                FasterWhisperSTT,
            )
            self._stt = FasterWhisperSTT(
                model_size=self._model_size,
                use_vad_filter=self._use_vad_filter,
                vad_min_silence_ms=self._vad_min_silence_ms,
            )
            return True
        except Exception:
            return False

    def transcribe(self, audio: np.ndarray, sample_rate: int = 16000) -> Optional[str]:
        if self._stt is None:
            return None
        event = self._stt.transcribe(audio, sample_rate)
        return event.text if event and event.text else None


class GoogleSTTBackend:
    """Backup STT: speech_recognition + Google (needs internet)."""

    name = "Google Speech"

    def __init__(self):
        self._recognizer = None

    def available(self) -> bool:
        try:
            import speech_recognition as sr
            self._recognizer = sr.Recognizer()
            return True
        except ImportError:
            return False

    def transcribe(self, audio: np.ndarray, sample_rate: int = 16000) -> Optional[str]:
        if self._recognizer is None:
            return None
        try:
            import speech_recognition as sr
            # Convert float32 numpy to AudioData
            pcm = (audio * 32767).astype(np.int16).tobytes()
            audio_data = sr.AudioData(pcm, sample_rate, 2)
            return self._recognizer.recognize_google(audio_data)
        except Exception as exc:
            logger.debug("[STT-GOOGLE] Recognition failed: %s", exc)
            return None


# ---------------------------------------------------------------------------
# Cohere Transcribe STT - Lazy Singleton Pattern (WSP 91)
# ---------------------------------------------------------------------------

# Module-level singleton state
_cohere_model: Optional[Any] = None
_cohere_processor: Optional[Any] = None
_cohere_initialized: bool = False
_cohere_load_time_sec: float = 0.0


def _is_cohere_stt_loaded() -> bool:
    """Check if Cohere STT is loaded (no side effects)."""
    return _cohere_initialized and _cohere_model is not None


def _get_cohere_stt_singleton() -> tuple:
    """
    Get or create Cohere Transcribe singleton (lazy loading).

    Returns (processor, model) tuple, or (None, None) if unavailable.
    Logs load time for WSP 91 observability.
    """
    global _cohere_model, _cohere_processor, _cohere_initialized, _cohere_load_time_sec

    if _cohere_initialized:
        return (_cohere_processor, _cohere_model)

    # Check if model path exists
    try:
        from modules.infrastructure.shared_utilities.local_model_selection import (
            resolve_asr_model_path,
        )
        model_path = resolve_asr_model_path()
    except ImportError:
        logger.debug("[COHERE-STT] local_model_selection not available")
        _cohere_initialized = True
        return (None, None)

    if not model_path.exists():
        logger.debug("[COHERE-STT] Model path not found: %s", model_path)
        _cohere_initialized = True
        return (None, None)

    config_path = model_path / "config.json"
    if not config_path.exists():
        logger.debug("[COHERE-STT] config.json not found in %s", model_path)
        _cohere_initialized = True
        return (None, None)

    # Load model with transformers
    try:
        import time as _time
        import warnings
        warnings.filterwarnings("ignore", category=UserWarning)

        from transformers import AutoProcessor, AutoModelForSpeechSeq2Seq
        import torch

        t0 = _time.time()
        logger.info("[COHERE-STT] Loading Cohere Transcribe from %s...", model_path)

        _cohere_processor = AutoProcessor.from_pretrained(
            str(model_path),
            trust_remote_code=True,
        )

        device = "cuda" if torch.cuda.is_available() else "cpu"
        dtype = torch.float16 if device == "cuda" else torch.float32

        _cohere_model = AutoModelForSpeechSeq2Seq.from_pretrained(
            str(model_path),
            trust_remote_code=True,
            torch_dtype=dtype,
            low_cpu_mem_usage=True,
        )

        if device == "cuda":
            _cohere_model = _cohere_model.to(device)

        _cohere_load_time_sec = _time.time() - t0
        _cohere_initialized = True
        logger.info(
            "[COHERE-STT] Loaded in %.2fs (device=%s)",
            _cohere_load_time_sec,
            device.upper(),
        )
        return (_cohere_processor, _cohere_model)

    except Exception as exc:
        logger.warning("[COHERE-STT] Failed to load: %s", exc)
        _cohere_initialized = True
        return (None, None)


class CohereTranscribeBackend:
    """Primary STT: Cohere Transcribe 2B (local, transformers format).

    Uses lazy singleton pattern - model loads on first transcribe, not on init.
    This prevents 60s cold-start blocking voice REPL boot.
    """

    name = "Cohere Transcribe"

    def __init__(self):
        self._validated = None  # None = not checked, True/False = result

    def available(self) -> bool:
        """Check if Cohere Transcribe can be used (lightweight check)."""
        if self._validated is not None:
            return self._validated

        # Quick path check without loading model
        try:
            from modules.infrastructure.shared_utilities.local_model_selection import (
                resolve_asr_model_path,
            )
            model_path = resolve_asr_model_path()
            config_exists = (model_path / "config.json").exists()
            self._validated = config_exists
            return config_exists
        except Exception:
            self._validated = False
            return False

    def transcribe(self, audio: np.ndarray, sample_rate: int = 16000) -> Optional[str]:
        """Transcribe audio using Cohere Transcribe (lazy loads model on first call)."""
        processor, model = _get_cohere_stt_singleton()
        if processor is None or model is None:
            return None

        try:
            import torch

            # Cohere Transcribe expects 16kHz audio
            if sample_rate != 16000:
                ratio = 16000 / sample_rate
                new_len = int(len(audio) * ratio)
                audio = np.interp(
                    np.linspace(0, len(audio), new_len),
                    np.arange(len(audio)),
                    audio,
                ).astype(np.float32)

            # Process audio
            inputs = processor(
                audio,
                sampling_rate=16000,
                return_tensors="pt",
            )

            device = next(model.parameters()).device
            inputs = {k: v.to(device) for k, v in inputs.items()}

            with torch.no_grad():
                generated_ids = model.generate(**inputs, max_new_tokens=256)

            transcription = processor.batch_decode(
                generated_ids,
                skip_special_tokens=True,
            )[0].strip()

            return transcription if transcription else None

        except Exception as exc:
            logger.debug("[COHERE-STT] Transcription failed: %s", exc)
            return None


# ---------------------------------------------------------------------------
# TTS Backends (degradation chain)
# ---------------------------------------------------------------------------

class EdgeTTSBackend:
    """Primary TTS: Microsoft Edge neural voices (needs internet)."""

    name = "Edge TTS"

    def __init__(self, voice: str = "en-US-GuyNeural"):
        self._voice = voice

    def available(self) -> bool:
        try:
            import edge_tts  # noqa: F401
            import sounddevice  # noqa: F401
            import soundfile  # noqa: F401
            return True
        except ImportError:
            return False

    def speak(self, text: str) -> bool:
        try:
            return asyncio.run(self._speak_async(text))
        except Exception as exc:
            logger.debug("[TTS-EDGE] Speak failed: %s", exc)
            return False

    async def _speak_async(self, text: str) -> bool:
        import edge_tts
        import sounddevice as sd
        import soundfile as sf

        communicate = edge_tts.Communicate(text, self._voice)
        audio_bytes = b""
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_bytes += chunk["data"]

        if not audio_bytes:
            return False

        # edge-tts returns MP3; decode via soundfile
        buf = io.BytesIO(audio_bytes)
        data, sample_rate = sf.read(buf)
        sd.play(data, sample_rate)
        sd.wait()
        return True


class Pyttsx3TTSBackend:
    """Backup TTS: pyttsx3 local SAPI5 (offline, robotic)."""

    name = "pyttsx3"

    def __init__(self):
        self._engine = None

    def available(self) -> bool:
        try:
            import pyttsx3
            self._engine = pyttsx3.init()
            self._engine.setProperty("rate", 185)
            self._engine.setProperty("volume", 0.9)
            return True
        except Exception:
            return False

    def speak(self, text: str) -> bool:
        if self._engine is None:
            return False
        try:
            self._engine.say(text)
            self._engine.runAndWait()
            return True
        except Exception as exc:
            logger.debug("[TTS-PYTTSX3] Speak failed: %s", exc)
            return False


# ---------------------------------------------------------------------------
# Microphone capture (sounddevice)
# ---------------------------------------------------------------------------

def record_until_silence(
    sample_rate: int = 16000,
    silence_threshold: float = 0.01,
    silence_duration: float = 0.8,
    max_duration: float = 30.0,
    min_recording_duration: float = 0.0,
    announce: bool = True,
    suppress_no_speech_log: bool = False,
) -> Optional[np.ndarray]:
    """Record from microphone until silence detected.

    Returns float32 mono audio array at `sample_rate`, or None on error.
    Uses WASAPI shared mode so Windows voice typing (Win+H) still works.
    """
    record_until_silence.last_error = ""

    try:
        import sounddevice as sd
    except ImportError:
        print("[ERROR] sounddevice not installed. Run: pip install sounddevice")
        record_until_silence.last_error = "sounddevice_missing"
        return None

    if announce:
        print("  [MIC] Listening... (speak now, silence ends recording)")

    def _resample(audio: np.ndarray, src_rate: int, dst_rate: int) -> np.ndarray:
        if src_rate == dst_rate or len(audio) == 0:
            return audio.astype(np.float32)
        src_x = np.linspace(0.0, 1.0, num=len(audio), endpoint=False)
        target_len = max(1, int(round(len(audio) * float(dst_rate) / float(src_rate))))
        dst_x = np.linspace(0.0, 1.0, num=target_len, endpoint=False)
        return np.interp(dst_x, src_x, audio).astype(np.float32)

    def _capture(attempt_rate: int, extra_settings) -> Optional[np.ndarray]:
        chunk_size = int(attempt_rate * 0.1)  # 100ms chunks
        chunk_sec = max(0.01, float(chunk_size) / float(attempt_rate))
        chunks = []
        max_chunks = int(max_duration / 0.1)
        recording = False
        captured_sec = 0.0
        last_speech_sec = -1.0
        min_duration_gate = max(0.0, float(min_recording_duration))

        with sd.InputStream(
            samplerate=attempt_rate,
            channels=1,
            dtype="float32",
            blocksize=chunk_size,
            extra_settings=extra_settings,
        ) as stream:
            for _ in range(max_chunks):
                data, _ = stream.read(chunk_size)
                frame = data.flatten()
                energy = np.sqrt(np.mean(frame ** 2))
                if energy > silence_threshold:
                    recording = True
                    last_speech_sec = captured_sec
                    chunks.append(frame)
                elif recording:
                    chunks.append(frame)
                    silence_elapsed = (
                        captured_sec - last_speech_sec
                        if last_speech_sec >= 0
                        else 0.0
                    )
                    if (
                        silence_elapsed >= silence_duration
                        and captured_sec >= min_duration_gate
                    ):
                        break
                captured_sec += chunk_sec

        if not chunks:
            return None
        audio = np.concatenate(chunks)
        return _resample(audio, attempt_rate, sample_rate)

    attempts = []
    disable_wasapi = _env_truthy("OPENCLAW_VOICE_DISABLE_WASAPI", "0")
    if not disable_wasapi:
        try:
            attempts.append(("wasapi_shared", sample_rate, sd.WasapiSettings(exclusive=False, auto_convert=True)))
        except Exception:
            pass  # Non-Windows or old sounddevice
    attempts.append(("default", sample_rate, None))

    try:
        dev = sd.query_devices(kind="input")
        device_rate = int(round(float(dev.get("default_samplerate") or sample_rate)))
        if device_rate > 0 and device_rate != sample_rate:
            attempts.append(("device_default_rate", device_rate, None))
    except Exception:
        pass

    errors = []
    seen = set()
    for name, attempt_rate, extra in attempts:
        key = (attempt_rate, bool(extra))
        if key in seen:
            continue
        seen.add(key)
        try:
            audio = _capture(attempt_rate, extra)
            if audio is None:
                if not suppress_no_speech_log:
                    print("  [MIC] No speech detected.")
                record_until_silence.last_error = ""
                return None
            record_until_silence.last_error = ""
            return audio
        except Exception as exc:
            errors.append(f"{name}:{exc}")

    if errors:
        primary = errors[0]
        print(f"  [ERROR] Microphone error: {primary}")
        record_until_silence.last_error = primary
        return None
    return None


# ---------------------------------------------------------------------------
# Voice REPL
# ---------------------------------------------------------------------------

def _ensure_repo_root():
    """Add repo root to sys.path if not already present."""
    repo = Path(__file__).resolve().parents[4]
    root_str = str(repo)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)
    return repo


def _init_stt_chain() -> list:
    """Initialize STT backends in priority order.

    Chain: Cohere Transcribe (local, lazy) -> Whisper (local) -> Google (cloud)

    Cohere is lazy-loaded on first transcribe to avoid 60s boot delay.
    Set OPENCLAW_VOICE_DISABLE_COHERE_STT=1 to skip Cohere entirely.
    """
    backends = []

    # Cohere Transcribe first (if not disabled)
    if not _env_truthy("OPENCLAW_VOICE_DISABLE_COHERE_STT", "0"):
        backends.append(CohereTranscribeBackend())

    # Fallback chain
    backends.extend([WhisperSTTBackend(), GoogleSTTBackend()])

    available = []
    for b in backends:
        if b.available():
            available.append(b)
            lazy_note = " (lazy)" if b.name == "Cohere Transcribe" else ""
            print(f"  [OK] STT: {b.name}{lazy_note}")
        else:
            print(f"  [--] STT: {b.name} (unavailable)")
    return available


def _init_tts_chain() -> list:
    """Initialize TTS backends in priority order."""
    backends = [EdgeTTSBackend(), Pyttsx3TTSBackend()]
    available = []
    for b in backends:
        if b.available():
            available.append(b)
            print(f"  [OK] TTS: {b.name}")
        else:
            print(f"  [--] TTS: {b.name} (unavailable)")
    return available


def _transcribe_with_chain(stt_chain: list, audio: np.ndarray) -> Optional[str]:
    """Try each STT backend until one succeeds."""
    for backend in stt_chain:
        result = backend.transcribe(audio)
        if result:
            return result
    return None


def _speak_with_chain(tts_chain: list, text: str) -> None:
    """Try each TTS backend until one succeeds, fall back to print."""
    for backend in tts_chain:
        if backend.speak(text):
            return
    # All TTS failed; already printed by REPL


def _print_boot_model_availability(dae) -> None:
    """Print startup model/provider availability summary."""
    probe_live = _env_truthy("OPENCLAW_MODEL_BOOT_PROBE", "1")
    try:
        probe_timeout_sec = max(
            0.8,
            float(os.getenv("OPENCLAW_MODEL_BOOT_PROBE_TIMEOUT_SEC", "2.0")),
        )
    except ValueError:
        probe_timeout_sec = 2.0

    try:
        report = dae.get_model_availability_snapshot(
            live_probe=probe_live,
            timeout_sec=probe_timeout_sec,
        )
    except Exception as exc:
        print(f"[MODELS] availability probe unavailable: {type(exc).__name__}")
        return

    local_parts = []
    for target, status in report.get("local", {}).items():
        local_parts.append(f"{target}={status}")
    if local_parts:
        print(f"[MODELS] local: {', '.join(local_parts)}")

    provider_parts = []
    for provider, status in report.get("providers", {}).items():
        provider_parts.append(f"{provider}={status}")
    if provider_parts:
        probe_label = "api" if probe_live else "keys"
        print(f"[MODELS] providers({probe_label}): {', '.join(provider_parts)}")

    target = report.get("target", "unknown")
    target_status = report.get("target_status", "unknown")
    effective = report.get("effective_model_name", "unknown")
    print(f"[MODELS] target={target} ({target_status}) | effective={effective}")


def _env_truthy(name: str, default: str = "0") -> bool:
    """Read env flag as boolean."""
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "y", "on"}


def _normalize_text(text: str) -> str:
    """Collapse whitespace for stable matching and clipping."""
    return re.sub(r"\s+", " ", (text or "").strip())


def _normalize_spoken_numeric(text: str) -> str:
    """Normalize spoken-number fragments to a digit-only string."""
    msg = _normalize_text(text).lower()
    if not msg:
        return ""

    word_to_digit = {
        "zero": "0",
        "oh": "0",
        "o": "0",
        "one": "1",
        "two": "2",
        "to": "2",
        "too": "2",
        "three": "3",
        "four": "4",
        "for": "4",
        "five": "5",
        "six": "6",
        "seven": "7",
        "eight": "8",
        "ate": "8",
        "nine": "9",
    }

    tokens = [t for t in re.split(r"[\s,.;:!?\-_/\\]+", msg) if t]
    normalized = "".join(word_to_digit.get(tok, tok) for tok in tokens)
    return re.sub(r"[^0-9]", "", normalized)


def _normalize_stt_aliases(text: str, cue: str = "0102") -> str:
    """Canonicalize common STT alias drift before control/intent routing."""
    msg = _normalize_text(text)
    if not msg:
        return ""

    out = msg

    # Qwen is frequently misheard in speech transcripts.
    out = re.sub(r"\b(quinn|quin|queen|quen|gwen|coin)\b", "qwen", out, flags=re.IGNORECASE)

    cue_norm = _normalize_text(cue) or "0102"
    cue_prefix_patterns = [
        r"^\s*(zero[\s,\-]+one[\s,\-]+zero[\s,\-]+two)\b",
        r"^\s*(zero[\s,\-]+one[\s,\-]+oh[\s,\-]+two)\b",
        r"^\s*(oh[\s,\-]+one[\s,\-]+oh[\s,\-]+two)\b",
        r"^\s*(0[\s,\-]+1[\s,\-]+0[\s,\-]+2)\b",
        r"^\s*(zero[\s,\-]+two[\s,\-]+zero[\s,\-]+one)\b",
        r"^\s*(0[\s,\-]+2[\s,\-]+0[\s,\-]+1)\b",
    ]
    for pattern in cue_prefix_patterns:
        out = re.sub(pattern, cue_norm, out, count=1, flags=re.IGNORECASE)

    return _normalize_text(out)


def _utterance_tokens(text: str) -> list[str]:
    """Tokenize normalized utterance for noise/fragment checks."""
    msg = _normalize_text(text).lower()
    if not msg:
        return []
    return re.findall(r"[a-z0-9']+", msg)


def _strip_leading_numeric_phrase(text: str) -> str:
    """Remove a leading spoken-number cue phrase and separators."""
    msg = _normalize_text(text).lower()
    if not msg:
        return ""

    numeric_words = {
        "zero",
        "oh",
        "o",
        "one",
        "two",
        "to",
        "too",
        "three",
        "four",
        "for",
        "five",
        "six",
        "seven",
        "eight",
        "ate",
        "nine",
    }
    tokens = [t for t in re.split(r"[\s,.;:!?\-_/\\]+", msg) if t]
    if not tokens:
        return ""

    idx = 0
    while idx < len(tokens):
        tok = tokens[idx]
        if tok in numeric_words or tok.isdigit():
            idx += 1
            continue
        break

    if idx == 0:
        return msg
    return " ".join(tokens[idx:]).strip()


def _cue_aliases(cue: str) -> list[str]:
    """Return normalized cue aliases for STT variance."""
    cue_norm = _normalize_text(cue).lower()
    aliases = {cue_norm}
    if cue_norm in {"0102", "0 1 0 2", "01 02", "zero two", "zerotwo"}:
        aliases.update(
            {
                "0102",
                "0 1 0 2",
                "01 02",
                "zero one zero two",
                "zero one oh two",
                "oh one oh two",
                "one zero two",
                "zero two",
                "zerotwo",
                "0201",
                "0 2 0 1",
                "02 01",
                "zero two zero one",
                "zero two oh one",
                "oh two oh one",
                "0 2 0 1 0",
            }
        )
    return sorted(aliases, key=len, reverse=True)


def _strip_repeated_cue_prefix(msg_norm: str, cue_norm: str) -> str:
    """Strip one extra leading cue alias from payload (e.g., '0102 0102 status')."""
    payload = (msg_norm or "").lower().lstrip(" ,.:;-")
    for alias in _cue_aliases(cue_norm):
        if payload == alias:
            return ""
        if payload.startswith(alias):
            return payload[len(alias):].lstrip(" ,.:;-")
    return payload


def _extract_barge_payload(
    user_input: str,
    cue: str = "0102",
    require_cue: bool = True,
) -> tuple[bool, str]:
    """Parse barge-in cue and optional payload from user input.

    Examples:
      - "0102" -> (True, "")
      - "0102, status" -> (True, "status")
      - "status please" -> (False, "status please")
    """
    msg = _normalize_text(user_input)
    if not msg:
        return False, ""

    msg_norm = msg.lower()
    if not require_cue:
        return True, msg

    cue_norm = _normalize_text(cue).lower()
    if not cue_norm:
        return False, msg_norm

    for alias in _cue_aliases(cue_norm):
        if msg_norm == alias:
            return True, ""

        if msg_norm.startswith(alias):
            remainder = msg_norm[len(alias):].lstrip(" ,.:;-")
            remainder = _strip_repeated_cue_prefix(remainder, cue_norm)
            return True, remainder

    # Numeric fallback for STT artifacts such as "0, 2, 0, 1, 0".
    msg_digits = _normalize_spoken_numeric(msg_norm)
    if msg_digits:
        for alias in _cue_aliases(cue_norm):
            alias_digits = _normalize_spoken_numeric(alias)
            if alias_digits and msg_digits.startswith(alias_digits):
                remainder = _strip_leading_numeric_phrase(msg_norm)
                remainder = _strip_repeated_cue_prefix(remainder, cue_norm)
                return True, remainder

    return False, msg


def _is_meaningful_utterance(text: str) -> bool:
    return _is_meaningful_utterance_mode(text, strict=False)


def _is_meaningful_utterance_mode(text: str, strict: bool = False) -> bool:
    """Heuristic guard to avoid routing pure noise/filler fragments."""
    msg = _normalize_text(text).lower()
    if not msg:
        return False

    if sum(ch.isalnum() for ch in msg) < 3:
        return False

    tokens = _utterance_tokens(msg)
    if not tokens:
        return False

    filler = {
        "um",
        "uh",
        "hmm",
        "mm",
        "ah",
        "oh",
        "er",
        "erm",
    }
    weak_single = {
        "well",
        "okay",
        "ok",
        "yeah",
        "yep",
        "no",
        "nope",
        "right",
        "next",
    }
    fragment_tail = {
        "and",
        "or",
        "but",
        "so",
        "because",
        "if",
        "the",
        "a",
        "an",
        "to",
        "of",
        "for",
        "in",
        "on",
        "at",
        "with",
        "from",
        "under",
        "over",
        "into",
        "about",
        "around",
        "like",
    }

    non_filler = [t for t in tokens if t not in filler]
    if not non_filler:
        return False

    # Drop punctuation-only / number-only fragments (e.g., ". . . ." / "0 1 0").
    if not any(any(ch.isalpha() for ch in tok) for tok in non_filler):
        return False

    if len(non_filler) == 1:
        tok = non_filler[0]
        if tok in weak_single:
            return False
        return len(tok) >= 4

    if strict:
        # Busy-queue should only accept complete-ish utterances.
        if len(non_filler) < 3:
            return False
        if non_filler[-1] in fragment_tail:
            return False

    return True


def _truncate_for_voice(text: str, max_chars: int) -> tuple[str, bool]:
    """Trim long assistant output for voice UX; returns (text, was_trimmed)."""
    clean = _normalize_text(text)
    if len(clean) <= max_chars:
        return clean, False

    sentence_chunks = re.split(r"(?<=[.!?])\s+", clean)
    out = ""
    for chunk in sentence_chunks:
        candidate = (f"{out} {chunk}").strip() if out else chunk
        if len(candidate) > max_chars:
            break
        out = candidate

    if len(out) < 40:
        out = clean[:max_chars].rstrip(" ,;:")

    return f"{out} ... (say 'details' for full output)", True


def _control_command(user_input: str) -> Optional[str]:
    """Map utterance/text to local REPL control command."""
    msg = _normalize_text(user_input).lower()
    if not msg:
        return None

    if msg in {"exit", "quit", "q"}:
        return "exit"
    if re.search(r"\b(exit|quit)\b", msg):
        return "exit"
    if msg in {"t", "text", "text mode", "keyboard mode", "switch to text"}:
        return "text"
    if "text mode" in msg or "switch to text" in msg or "keyboard mode" in msg:
        return "text"
    if msg in {"v", "voice", "voice mode", "switch to voice"}:
        return "voice"
    if "voice mode" in msg or "switch to voice" in msg:
        return "voice"
    if msg in {"details", "detail", "more", "full response", "show details", "model details"}:
        return "details"
    direct_backend = re.search(r"\bbackend\s+(openclaw|ironclaw)\b", msg)
    if direct_backend:
        return f"backend:{direct_backend.group(1)}"
    switch_backend = re.search(
        r"\b(?:switch|change|set|use|move)\s+(?:backend\s+)?(?:to\s+)?(openclaw|ironclaw)\b",
        msg,
    )
    if switch_backend:
        return f"backend:{switch_backend.group(1)}"
    mode_backend = re.search(r"\b(openclaw|ironclaw)\s+mode\b", msg)
    if mode_backend:
        return f"backend:{mode_backend.group(1)}"
    if msg in {"switch backend", "change backend"}:
        return "backend_help"
    if msg in {"unmute", "resume voice"}:
        return "unmute"
    if "unmute" in msg or "resume voice" in msg:
        return "unmute"
    if msg in {"stop", "interrupt", "cancel", "mute"}:
        return "stop"
    if re.search(r"\b(stop|interrupt|cancel|mute)\b", msg):
        return "stop"
    return None


def _stop_audio_playback() -> None:
    """Best-effort stop for active sounddevice playback."""
    try:
        import sounddevice as sd

        sd.stop()
    except Exception:
        pass


def _run_dae_turn(
    dae,
    message: str,
    session_key: str,
    timeout_sec: int,
    output: dict,
    done_event: threading.Event,
    continuity_ctx=None,
) -> None:
    """Run one DAE turn in a background thread and store result in output dict."""
    try:
        # Gateway Continuity Layer: Propagate CLI context as parent for OpenClaw processing
        process_metadata = {"source_surface": "cli"}
        if continuity_ctx is not None:
            process_metadata["parent_continuity_id"] = continuity_ctx.continuity_id

        output["response"] = asyncio.run(
            asyncio.wait_for(
                dae.process(
                    message=message,
                    sender="@012",
                    channel="voice_repl",
                    session_key=session_key,
                    metadata=process_metadata,
                ),
                timeout=timeout_sec,
            )
        )
    except asyncio.TimeoutError:
        output["response"] = (
            "0102: That took too long and was interrupted by the voice timeout. "
            "Try a shorter prompt or ask for details step-by-step."
        )
    except Exception as exc:
        output["response"] = f"Error: {type(exc).__name__}: {exc}"
    finally:
        done_event.set()


def run_voice_repl(
    conversation_backend: str = "openclaw",
    no_api_keys: bool | None = None,
) -> None:
    """Interactive voice REPL for OpenClaw."""
    repo_root = _ensure_repo_root()
    backend = (conversation_backend or "openclaw").strip().lower()
    if backend not in {"openclaw", "ironclaw"}:
        backend = "openclaw"

    if no_api_keys is None:
        no_api_keys = backend == "ironclaw"

    print("=" * 60)
    if backend == "ironclaw":
        print("  0102 IronClaw Voice Chat (via OpenClaw DAE)")
    else:
        print("  0102 OpenClaw Voice Chat")
    print("  Commander: @012 | Channel: voice_repl")
    print(
        f"  Conversation backend: {backend} | "
        f"no_api_keys={'ON' if no_api_keys else 'OFF'}"
    )
    print("=" * 60)
    print()

    # Initialize degradation chains
    print("Initializing voice backends...")
    stt_chain = _init_stt_chain()
    tts_chain = _init_tts_chain()
    print()

    if not stt_chain:
        print("[WARN] No STT backends available. Falling back to text-only mode.")
        print("  Install: pip install faster-whisper  (or)  pip install SpeechRecognition")

    # Initialize OpenClaw
    try:
        from modules.communication.moltbot_bridge.src.openclaw_dae import OpenClawDAE
    except ImportError as exc:
        print(f"[ERROR] Cannot import OpenClawDAE: {exc}")
        return

    def _configure_backend_runtime(target_backend: str, announce: bool = True) -> bool:
        """Apply backend runtime env defaults and return no_api_keys mode."""
        normalized = (target_backend or "openclaw").strip().lower()
        if normalized not in {"openclaw", "ironclaw"}:
            normalized = "openclaw"

        target_no_api_keys = normalized == "ironclaw"
        if target_no_api_keys:
            os.environ["IRONCLAW_NO_API_KEYS"] = "1"
            os.environ["OPENCLAW_NO_API_KEYS"] = "1"
            # Autonomous continuity mode: avoid hard-stop loops when gateway is down.
            if "OPENCLAW_IRONCLAW_ALLOW_LOCAL_FALLBACK" not in os.environ:
                os.environ["OPENCLAW_IRONCLAW_ALLOW_LOCAL_FALLBACK"] = "1"
                if announce:
                    print("[MODE] ironclaw continuity: local fallback auto-enabled.")
            if "OPENCLAW_IRONCLAW_AUTOSTART_WAIT_SEC" not in os.environ:
                os.environ["OPENCLAW_IRONCLAW_AUTOSTART_WAIT_SEC"] = "2.0"
            if "OPENCLAW_IRONCLAW_AUTOSTART_COOLDOWN_SEC" not in os.environ:
                os.environ["OPENCLAW_IRONCLAW_AUTOSTART_COOLDOWN_SEC"] = "45"
        else:
            os.environ["IRONCLAW_NO_API_KEYS"] = "0"
            os.environ["OPENCLAW_NO_API_KEYS"] = "0"
        return target_no_api_keys

    no_api_keys = _configure_backend_runtime(backend, announce=True)

    dae = OpenClawDAE(repo_root=repo_root, conversation_backend=backend)
    print(f"[OK] OpenClawDAE initialized (state={dae.state})")
    print(f"[ID] 0102 taxonomy: {dae.get_identity_label_line(include_runtime_probe=(backend == 'ironclaw'))}")
    print("[ID] tip: ask `model details` for full diagnostics")
    _print_boot_model_availability(dae)
    print()

    auto_listen = _env_truthy("OPENCLAW_VOICE_AUTO_LISTEN", "1")
    configured_auto_listen = auto_listen
    max_response_chars = max(120, int(os.getenv("OPENCLAW_VOICE_MAX_RESPONSE_CHARS", "380")))
    process_timeout_sec = max(5, int(os.getenv("OPENCLAW_VOICE_PROCESS_TIMEOUT_SEC", "45")))
    tts_enabled = _env_truthy("OPENCLAW_VOICE_TTS_ENABLED", "1")
    barge_cue = _normalize_text(os.getenv("OPENCLAW_VOICE_BARGE_CUE", "0102")) or "0102"
    require_barge_cue = _env_truthy("OPENCLAW_VOICE_BARGE_REQUIRE_CUE", "1")
    queue_noncue_while_busy = _env_truthy("OPENCLAW_VOICE_QUEUE_NONCUE_WHILE_BUSY", "1")
    queue_replace_latest = _env_truthy("OPENCLAW_VOICE_QUEUE_REPLACE_LATEST", "1")
    stt_alias_normalize = _env_truthy("OPENCLAW_VOICE_STT_ALIAS_NORMALIZE", "1")
    stt_alias_verbose = _env_truthy("OPENCLAW_VOICE_STT_ALIAS_VERBOSE", "0")
    try:
        barge_window_sec = max(0.6, float(os.getenv("OPENCLAW_VOICE_BARGE_WINDOW_SEC", "2.0")))
    except ValueError:
        barge_window_sec = 2.0
    try:
        barge_cancel_grace_sec = max(0.2, float(os.getenv("OPENCLAW_VOICE_BARGE_CANCEL_GRACE_SEC", "1.5")))
    except ValueError:
        barge_cancel_grace_sec = 1.5
    try:
        mic_retry_sleep_sec = max(0.15, float(os.getenv("OPENCLAW_VOICE_MIC_RETRY_SLEEP_SEC", "0.35")))
    except ValueError:
        mic_retry_sleep_sec = 0.35
    try:
        voice_silence_sec = max(0.25, float(os.getenv("OPENCLAW_VOICE_SILENCE_SEC", "0.85")))
    except ValueError:
        voice_silence_sec = 0.85
    try:
        voice_min_utterance_sec = max(
            0.0,
            float(os.getenv("OPENCLAW_VOICE_MIN_UTTERANCE_SEC", "1.2")),
        )
    except ValueError:
        voice_min_utterance_sec = 1.2
    try:
        voice_max_utterance_sec = max(2.0, float(os.getenv("OPENCLAW_VOICE_MAX_UTTERANCE_SEC", "15.0")))
    except ValueError:
        voice_max_utterance_sec = 15.0
    try:
        barge_min_utterance_sec = max(
            0.0,
            float(os.getenv("OPENCLAW_VOICE_BARGE_MIN_UTTERANCE_SEC", "0.0")),
        )
    except ValueError:
        barge_min_utterance_sec = 0.0
    try:
        voice_silence_threshold = max(0.001, float(os.getenv("OPENCLAW_VOICE_SILENCE_THRESHOLD", "0.01")))
    except ValueError:
        voice_silence_threshold = 0.01
    try:
        mic_fail_to_text_threshold = max(2, int(os.getenv("OPENCLAW_VOICE_MIC_FAIL_TO_TEXT", "4")))
    except ValueError:
        mic_fail_to_text_threshold = 4
    main_noise_gate = _env_truthy("OPENCLAW_VOICE_MAIN_NOISE_GATE", "1")
    queue_strict_noise_gate = _env_truthy("OPENCLAW_VOICE_QUEUE_STRICT_NOISE_GATE", "1")
    try:
        noise_notice_cooldown_sec = max(
            0.0,
            float(os.getenv("OPENCLAW_VOICE_NOISE_NOTICE_COOLDOWN_SEC", "3.0")),
        )
    except ValueError:
        noise_notice_cooldown_sec = 3.0
    try:
        loop_guard_error_threshold = max(3, int(os.getenv("OPENCLAW_VOICE_LOOP_GUARD_ERRORS", "8")))
    except ValueError:
        loop_guard_error_threshold = 8
    try:
        loop_guard_window_sec = max(3.0, float(os.getenv("OPENCLAW_VOICE_LOOP_GUARD_WINDOW_SEC", "12")))
    except ValueError:
        loop_guard_window_sec = 12.0

    if auto_listen and stt_chain:
        print("[MODE] voice auto-listen ON (no Enter required).")
        if require_barge_cue:
            print(f"[MODE] barge cue: '{barge_cue} ...' (interrupt + optional prompt).")
            if queue_noncue_while_busy:
                print("[MODE] non-cue speech while busy will be queued for next turn.")
        else:
            print(
                f"[MODE] barge cue optional (cue='{barge_cue}' preferred). "
                "Any speech during active turn can interrupt."
            )
        print("[MODE] say 'text mode', 'details', 'mute', or 'exit'.")
        print("[MODE] backend switch: 'backend ironclaw' / 'backend openclaw'.")
        print("[MODE] model switch voice commands: 'switch model to qwen3', 'become codex', 'become grok'.")
    else:
        print("[MODE] push-to-talk mode. Press Enter to speak or type commands.")
        print(
            f"[MODE] commands: 't' text mode, '{barge_cue} ...' barge, "
            "'backend ironclaw/openclaw', 'exit' quit."
        )
    print(
        f"[MODE] turn timeout={process_timeout_sec}s | "
        f"barge_window={barge_window_sec}s | max_reply_chars={max_response_chars} | "
        f"pause_end={voice_silence_sec}s | min_utterance={voice_min_utterance_sec}s"
    )
    print()

    # Gateway Continuity Layer: Create CLI continuity context for this voice session
    cli_continuity_ctx = None
    session_key = "voice_repl_012"  # Default fallback

    try:
        from modules.communication.moltbot_bridge.src.continuity_context import (
            ContinuityManager,
        )
        cli_continuity_ctx = ContinuityManager.from_cli(
            command="voice_repl",
            script_name="openclaw_voice.py",
        )
        # Derive unique session_key from CLI continuity to avoid child ID collision
        session_key = f"cli_voice_{cli_continuity_ctx.continuity_id[:12]}"
        print(f"[CONTINUITY] CLI context: {cli_continuity_ctx.continuity_id[:12]}...")

        # Record CLI session start breadcrumb for cross-surface tracking
        try:
            from modules.infrastructure.database.src.agent_db import AgentDB
            db = AgentDB()
            db.add_breadcrumb(
                session_id=session_key,
                action="cli_voice_session_start",
                agent_id="0102",
                data={
                    "backend": backend,
                    "command": "voice_repl",
                },
                continuity_id=cli_continuity_ctx.continuity_id,
                runtime_surface=cli_continuity_ctx.surface.value,
                sender_normalized=cli_continuity_ctx.sender_normalized,
            )
        except Exception:
            pass  # Breadcrumb recording is optional
    except Exception:
        # Graceful degradation - continuity is optional
        pass

    text_mode = not stt_chain  # Start in text mode if no STT
    last_full_response = ""
    last_interrupt_ts = 0.0
    prefilled_user_input: Optional[str] = None
    mic_error_streak = 0
    last_mic_error_sig = ""
    mic_error_events: list[float] = []
    last_noise_notice_ts = 0.0

    def _normalize_live_stt_text(text: str) -> str:
        if not stt_alias_normalize:
            return text
        normalized = _normalize_stt_aliases(text, cue=barge_cue)
        if stt_alias_verbose and normalized != text:
            print(f"  [STT-NORM] {normalized}")
        return normalized

    while True:
        try:
            if prefilled_user_input is not None:
                user_input = prefilled_user_input
                prefilled_user_input = None
                print(f"  012> {user_input}")
            elif text_mode:
                user_input = input("012> ").strip()
            else:
                if auto_listen:
                    audio = record_until_silence(
                        silence_threshold=voice_silence_threshold,
                        silence_duration=voice_silence_sec,
                        max_duration=voice_max_utterance_sec,
                        min_recording_duration=voice_min_utterance_sec,
                    )
                    if audio is None:
                        mic_err = getattr(record_until_silence, "last_error", "")
                        if mic_err:
                            if mic_err == last_mic_error_sig:
                                mic_error_streak += 1
                            else:
                                last_mic_error_sig = mic_err
                                mic_error_streak = 1
                            if mic_error_streak >= mic_fail_to_text_threshold:
                                text_mode = True
                                print(
                                    "  [WARN] Repeated microphone stream failures. "
                                    "Switching to text mode. Type 'voice mode' after fixing the mic."
                                )
                            now_ts = time.time()
                            mic_error_events.append(now_ts)
                            mic_error_events = [
                                t for t in mic_error_events if (now_ts - t) <= loop_guard_window_sec
                            ]
                            if len(mic_error_events) >= loop_guard_error_threshold:
                                text_mode = True
                                auto_listen = False
                                try:
                                    dae.request_turn_cancel("voice_loop_guard")
                                except Exception:
                                    pass
                                print(
                                    "  [GUARD] Detected mic error loop. Auto-listen paused and switched "
                                    "to text mode. Fix input device, then type 'voice mode' to resume."
                                )
                                logger.warning(
                                    "[DAEMON][OPENCLAW-VOICE-LOOP-GUARD] "
                                    "event=mic_loop_collapse errors=%d window_sec=%.1f signature=%s",
                                    len(mic_error_events),
                                    loop_guard_window_sec,
                                    mic_err[:120],
                                )
                                try:
                                    dae._emit_to_overseer(
                                        event_type="voice_loop_guard",
                                        sender="@012",
                                        channel="voice_repl",
                                        details={
                                            "event": "mic_loop_collapse",
                                            "errors": len(mic_error_events),
                                            "window_sec": loop_guard_window_sec,
                                            "signature": mic_err[:160],
                                        },
                                    )
                                except Exception:
                                    pass
                                mic_error_events.clear()
                                time.sleep(max(mic_retry_sleep_sec, 0.6))
                                continue
                        else:
                            mic_error_streak = 0
                            mic_error_events.clear()
                        time.sleep(mic_retry_sleep_sec)
                        continue
                    mic_error_streak = 0
                    last_mic_error_sig = ""
                    mic_error_events.clear()

                    print("  [STT] Transcribing...")
                    user_input_raw = _transcribe_with_chain(stt_chain, audio)
                    if not user_input_raw:
                        print("  [STT] Could not transcribe. Try again or say 'text mode'.")
                        continue
                    user_input = _normalize_live_stt_text(user_input_raw)
                    print(f"  012> {user_input}")
                else:
                    cmd = input("Type command or press Enter to speak: ").strip()
                    if cmd:
                        user_input = cmd
                        print(f"  012> {user_input}")
                    else:
                        audio = record_until_silence(
                            silence_threshold=voice_silence_threshold,
                            silence_duration=voice_silence_sec,
                            max_duration=voice_max_utterance_sec,
                            min_recording_duration=voice_min_utterance_sec,
                        )
                        if audio is None:
                            mic_err = getattr(record_until_silence, "last_error", "")
                            if mic_err:
                                if mic_err == last_mic_error_sig:
                                    mic_error_streak += 1
                                else:
                                    last_mic_error_sig = mic_err
                                    mic_error_streak = 1
                                now_ts = time.time()
                                mic_error_events.append(now_ts)
                                mic_error_events = [
                                    t for t in mic_error_events if (now_ts - t) <= loop_guard_window_sec
                                ]
                                if len(mic_error_events) >= loop_guard_error_threshold:
                                    text_mode = True
                                    auto_listen = False
                                    try:
                                        dae.request_turn_cancel("voice_loop_guard")
                                    except Exception:
                                        pass
                                    print(
                                        "  [GUARD] Detected mic error loop. Auto-listen paused and switched "
                                        "to text mode. Fix input device, then type 'voice mode' to resume."
                                    )
                                    logger.warning(
                                        "[DAEMON][OPENCLAW-VOICE-LOOP-GUARD] "
                                        "event=mic_loop_collapse errors=%d window_sec=%.1f signature=%s",
                                        len(mic_error_events),
                                        loop_guard_window_sec,
                                        mic_err[:120],
                                    )
                                    try:
                                        dae._emit_to_overseer(
                                            event_type="voice_loop_guard",
                                            sender="@012",
                                            channel="voice_repl",
                                            details={
                                                "event": "mic_loop_collapse",
                                                "errors": len(mic_error_events),
                                                "window_sec": loop_guard_window_sec,
                                                "signature": mic_err[:160],
                                            },
                                        )
                                    except Exception:
                                        pass
                                    mic_error_events.clear()
                                    time.sleep(max(mic_retry_sleep_sec, 0.6))
                                    continue
                            else:
                                mic_error_streak = 0
                                mic_error_events.clear()
                            time.sleep(mic_retry_sleep_sec)
                            continue
                        mic_error_streak = 0
                        last_mic_error_sig = ""
                        mic_error_events.clear()

                        print("  [STT] Transcribing...")
                        user_input_raw = _transcribe_with_chain(stt_chain, audio)
                        if not user_input_raw:
                            print("  [STT] Could not transcribe. Try again or type in text mode.")
                            continue
                        user_input = _normalize_live_stt_text(user_input_raw)
                        print(f"  012> {user_input}")

            if not user_input:
                continue

            # Dedicated barge-in cue: "0102 ..."
            is_barge, barge_payload = _extract_barge_payload(user_input, cue=barge_cue, require_cue=True)
            if is_barge:
                _stop_audio_playback()
                if not barge_payload:
                    print(f"  [BARGE] cue '{barge_cue}' acknowledged. Interrupted current output.")
                    continue
                user_input = barge_payload
                print(f"  [BARGE] cue '{barge_cue}' -> {user_input}")

            cmd = _control_command(user_input)
            if cmd == "exit":
                break
            if cmd == "text":
                text_mode = True
                print("  [MODE] Switched to text mode. Type 'voice mode' to return.")
                continue
            if cmd == "voice":
                if stt_chain:
                    text_mode = False
                    auto_listen = configured_auto_listen
                    print("  [MODE] Switched to voice mode.")
                else:
                    print("  [WARN] No STT backends available.")
                continue
            if cmd == "stop":
                _stop_audio_playback()
                tts_enabled = False
                print("  [CTRL] Output interrupted. TTS muted; say 'unmute' to re-enable.")
                continue
            if cmd == "unmute":
                tts_enabled = True
                print("  [CTRL] TTS re-enabled.")
                continue
            if cmd == "details":
                if last_full_response:
                    print(f"\n0102> {last_full_response}\n")
                    if tts_chain and tts_enabled:
                        _speak_with_chain(tts_chain, last_full_response)
                else:
                    print("  [INFO] No previous response to expand.")
                continue
            if cmd == "backend_help":
                print("  [MODE] say 'backend ironclaw' or 'backend openclaw'.")
                continue
            if cmd and cmd.startswith("backend:"):
                target_backend = cmd.split(":", 1)[1].strip().lower()
                if target_backend not in {"openclaw", "ironclaw"}:
                    print("  [MODE] backend command not recognized. Use openclaw or ironclaw.")
                    continue
                if target_backend == backend:
                    print(f"  [MODE] backend already {backend}.")
                    continue

                backend = target_backend
                no_api_keys = _configure_backend_runtime(backend, announce=True)
                dae = OpenClawDAE(repo_root=repo_root, conversation_backend=backend)
                print(
                    f"  [MODE] backend switched to {backend} | "
                    f"no_api_keys={'ON' if no_api_keys else 'OFF'}"
                )
                print(
                    f"  [ID] 0102 taxonomy: "
                    f"{dae.get_identity_label_line(include_runtime_probe=(backend == 'ironclaw'))}"
                )
                continue
            if main_noise_gate and not _is_meaningful_utterance_mode(user_input, strict=False):
                now_ts = time.time()
                if (now_ts - last_noise_notice_ts) >= noise_notice_cooldown_sec:
                    print("  [NOISE] Ignored low-signal utterance. Speak naturally or use '0102 ...'.")
                    last_noise_notice_ts = now_ts
                continue

            # Process through OpenClaw in a background thread so we can barge-in mid-turn.
            turn_output: dict = {}
            turn_done = threading.Event()
            worker = threading.Thread(
                target=_run_dae_turn,
                args=(dae, user_input, session_key, process_timeout_sec, turn_output, turn_done, cli_continuity_ctx),
                daemon=True,
            )
            worker.start()

            barge_interrupted = False
            barge_mic_error_streak = 0
            while not turn_done.is_set():
                if auto_listen and stt_chain and not text_mode:
                    audio = record_until_silence(
                        silence_threshold=voice_silence_threshold,
                        silence_duration=0.6,
                        max_duration=barge_window_sec,
                        min_recording_duration=barge_min_utterance_sec,
                        announce=False,
                        suppress_no_speech_log=True,
                    )
                    if audio is None:
                        mic_err = getattr(record_until_silence, "last_error", "")
                        if mic_err:
                            barge_mic_error_streak += 1
                            if barge_mic_error_streak >= mic_fail_to_text_threshold:
                                text_mode = True
                                auto_listen = False
                                print(
                                    "  [GUARD] Barge mic unavailable while turn active. "
                                    "Switched to text mode to prevent error loop."
                                )
                                logger.warning(
                                    "[DAEMON][OPENCLAW-VOICE-LOOP-GUARD] "
                                    "event=barge_mic_unavailable streak=%d signature=%s",
                                    barge_mic_error_streak,
                                    mic_err[:120],
                                )
                                try:
                                    dae._emit_to_overseer(
                                        event_type="voice_loop_guard",
                                        sender="@012",
                                        channel="voice_repl",
                                        details={
                                            "event": "barge_mic_unavailable",
                                            "streak": barge_mic_error_streak,
                                            "signature": mic_err[:160],
                                        },
                                    )
                                except Exception:
                                    pass
                                turn_done.wait(timeout=max(mic_retry_sleep_sec, 0.25))
                                continue
                        else:
                            barge_mic_error_streak = 0
                        time.sleep(mic_retry_sleep_sec)
                        continue
                    barge_mic_error_streak = 0

                    heard_raw = _transcribe_with_chain(stt_chain, audio)
                    if not heard_raw:
                        continue
                    heard = _normalize_live_stt_text(heard_raw)
                    print(f"  012> {heard}")

                    is_barge_wait, payload_wait = _extract_barge_payload(
                        heard,
                        cue=barge_cue,
                        require_cue=require_barge_cue,
                    )
                    if not is_barge_wait:
                        queued_control = _control_command(heard)
                        queue_candidate_ok = _is_meaningful_utterance_mode(
                            heard,
                            strict=queue_strict_noise_gate,
                        )
                        if queued_control == "exit":
                            barge_interrupted = True
                            _stop_audio_playback()
                            try:
                                dae.request_turn_cancel("voice_exit_command")
                            except Exception:
                                pass
                            prefilled_user_input = heard
                            print("  [CTRL] Exit requested while busy; stopping active turn.")
                            settled = turn_done.wait(timeout=barge_cancel_grace_sec)
                            if not settled:
                                dae = OpenClawDAE(repo_root=repo_root, conversation_backend=backend)
                                print("  [BARGE] cancellation still draining; switched to fresh DAE context.")
                            break
                        if require_barge_cue and queue_noncue_while_busy and (
                            queued_control is not None or queue_candidate_ok
                        ):
                            if prefilled_user_input is None:
                                prefilled_user_input = heard
                                print("  [QUEUE] Captured speech while busy; will run after current response.")
                            elif queue_replace_latest:
                                prefilled_user_input = heard
                                print("  [QUEUE] Replaced pending speech with latest utterance.")
                            else:
                                print("  [QUEUE] Already have pending speech; ignoring additional queued input.")
                        elif require_barge_cue and queue_candidate_ok:
                            print(
                                f"  [BARGE] heard speech but no cue. Say '{barge_cue} ...' "
                                "to interrupt."
                            )
                        continue

                    barge_interrupted = True
                    _stop_audio_playback()
                    try:
                        dae.request_turn_cancel("voice_barge")
                    except Exception:
                        pass

                    if payload_wait:
                        prefilled_user_input = payload_wait
                        print(f"  [BARGE] cue '{barge_cue}' -> {payload_wait}")
                    else:
                        print(f"  [BARGE] cue '{barge_cue}' acknowledged. Interrupted active turn.")

                    settled = turn_done.wait(timeout=barge_cancel_grace_sec)
                    if not settled:
                        # Active turn is still draining; create a fresh DAE context so
                        # next prompt is not blocked behind the stale turn.
                        dae = OpenClawDAE(repo_root=repo_root, conversation_backend=backend)
                        print("  [BARGE] cancellation still draining; switched to fresh DAE context.")
                    break
                else:
                    turn_done.wait(timeout=0.1)

            if barge_interrupted:
                # Skip stale response and handle next prompt immediately (if provided).
                continue

            response = turn_output.get("response", "0102: Interrupted. Ready for your next prompt.")
            last_full_response = response or ""

            display_response, trimmed = _truncate_for_voice(response, max_response_chars)
            if trimmed:
                print("  [INFO] Long response clipped. Say 'details' for full output.")

            # Output: print + speak
            print(f"\n0102> {display_response}\n")
            if tts_chain and tts_enabled:
                _speak_with_chain(tts_chain, display_response)

        except asyncio.TimeoutError:
            timeout_msg = (
                "0102: That took too long and was interrupted by the voice timeout. "
                "Try a shorter prompt or ask for details step-by-step."
            )
            print(f"\n{timeout_msg}\n")
            if tts_chain and tts_enabled:
                _speak_with_chain(tts_chain, timeout_msg)
        except EOFError:
            print("\n[EXIT] Session ended.")
            break
        except KeyboardInterrupt:
            now = time.time()
            _stop_audio_playback()
            try:
                dae.request_turn_cancel("keyboard_interrupt")
            except Exception:
                pass
            if now - last_interrupt_ts <= 2.0:
                print("\n[EXIT] Session ended.")
                break
            last_interrupt_ts = now
            print("\n[CTRL] Turn interrupted. Press Ctrl+C again within 2s to exit.")
            continue
        except Exception as exc:
            response = f"Error: {type(exc).__name__}: {exc}"
            print(f"\n0102> {response}\n")
            if tts_chain and tts_enabled:
                _speak_with_chain(tts_chain, response)

if __name__ == "__main__":
    run_voice_repl()



