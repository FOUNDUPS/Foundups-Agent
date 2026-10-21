"""Voice command ingestion for live audio streams.

WSP Compliance:
    - WSP 3: communication domain (voice processing)
    - WSP 11: Public interface defined
    - WSP 49: Module structure compliant
    - WSP 84: Reuses faster-whisper for local STT

Architecture:
    Live Audio -> faster-whisper STT -> Trigger Detection ("0102") -> Command Events

    The trigger token "0102" activates command capture mode.
    Everything after the trigger until silence/timeout is the command.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Iterable, Iterator, Optional, List, Generator
import logging
import re
import numpy as np

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class STTEvent:
    """Single speech to text event from the streaming recognizer."""

    text: str
    is_final: bool
    start_ms: int
    end_ms: int
    confidence: float = 1.0


@dataclass(frozen=True)
class CommandEvent:
    """Detected command event after trigger recognition."""

    command: str
    raw_text: str
    trigger_detected: bool
    timestamp_iso: str
    confidence: float = 1.0


class FasterWhisperSTT:
    """Local STT using faster-whisper (CTranslate2 optimized Whisper).

    Features:
    - 4x faster than vanilla whisper
    - Same accuracy (~6.7% WER)
    - CPU and GPU support
    - Streaming-friendly chunked processing
    """

    def __init__(
        self,
        model_size: str = "base",
        device: str = "cpu",
        compute_type: str = "int8",
        use_vad_filter: bool = True,
        vad_min_silence_ms: int = 250,
        language: Optional[str] = "en",
    ) -> None:
        """Initialize faster-whisper model.

        Args:
            model_size: Model size (tiny, base, small, medium, large-v3)
            device: Device to use (cpu, cuda)
            compute_type: Computation type (int8, float16, float32)
            use_vad_filter: Whether to apply Whisper VAD filtering.
            vad_min_silence_ms: Minimum silence for VAD segmentation.
            language: Whisper language code, or None for automatic detection.
        """
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        if language is not None and not re.fullmatch(r"[a-z]{2,3}", language):
            raise ValueError("language must be a Whisper language code or None")
        if model_size.endswith(".en") and language != "en":
            raise ValueError("English-only Whisper models cannot transcribe Japanese or auto-detect")
        self.language = language
        self.use_vad_filter = bool(use_vad_filter)
        self.vad_min_silence_ms = int(max(50, vad_min_silence_ms))
        self._model = None
        self._initialized = False

    def _initialize(self) -> bool:
        """Lazy initialization of Whisper model."""
        if self._initialized:
            return True

        try:
            from faster_whisper import WhisperModel

            logger.info(f"[STT] Loading faster-whisper model: {self.model_size} on {self.device}")
            self._model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type
            )
            self._initialized = True
            logger.info("[STT] Model loaded successfully")
            return True

        except ImportError:
            logger.error("[STT] faster-whisper not installed. Run: pip install faster-whisper")
            return False
        except Exception as e:
            logger.error(f"[STT] Failed to load model: {e}")
            return False

    def transcribe(self, audio: np.ndarray, sample_rate: int = 16000) -> Optional[STTEvent]:
        """Transcribe audio chunk to text.

        Args:
            audio: Float32 audio data (mono)
            sample_rate: Sample rate (default 16000 for Whisper)

        Returns:
            STTEvent with transcription, or None on failure
        """
        if not self._initialize():
            return None

        try:
            start_ms = 0

            # Transcribe
            transcribe_kwargs = {
                "beam_size": 5,
                "language": self.language,
                "vad_filter": self.use_vad_filter,
            }
            if self.use_vad_filter:
                transcribe_kwargs["vad_parameters"] = {
                    "min_silence_duration_ms": self.vad_min_silence_ms,
                }

            segments, info = self._model.transcribe(audio, **transcribe_kwargs)

            # Collect all segments
            text_parts = []
            end_ms = 0
            avg_confidence = 0.0
            segment_count = 0

            for segment in segments:
                text_parts.append(segment.text.strip())
                end_ms = int(segment.end * 1000)
                avg_confidence += segment.avg_logprob
                segment_count += 1

            if segment_count > 0:
                avg_confidence = avg_confidence / segment_count
                # Convert log prob to rough confidence (0-1 range)
                confidence = min(1.0, max(0.0, 1.0 + avg_confidence / 5))
            else:
                confidence = 0.0

            full_text = " ".join(text_parts).strip()

            return STTEvent(
                text=full_text,
                is_final=True,
                start_ms=start_ms,
                end_ms=end_ms,
                confidence=confidence
            )

        except Exception as e:
            logger.error(f"[STT] Transcription failed: {e}")
            return None

    def transcribe_stream(
        self,
        audio_chunks: Iterable[np.ndarray],
        sample_rate: int = 16000
    ) -> Generator[STTEvent, None, None]:
        """Transcribe streaming audio chunks.

        Args:
            audio_chunks: Iterator of float32 audio arrays
            sample_rate: Sample rate

        Yields:
            STTEvent for each chunk
        """
        for chunk in audio_chunks:
            event = self.transcribe(chunk, sample_rate)
            if event and event.text:
                yield event


class TriggerDetector:
    """Detect trigger token "0102" in transcribed text.

    Handles variations:
    - "0102" (exact)
    - "zero one zero two"
    - "oh one oh two"
    - "0 1 0 2"
    """

    # Patterns that match "0102" trigger
    TRIGGER_PATTERNS = [
        r"\b0102\b",                          # Exact digits
        r"\bzero\s*one\s*zero\s*two\b",       # Words
        r"\boh\s*one\s*oh\s*two\b",           # "oh" variant
        r"\b0\s*1\s*0\s*2\b",                 # Spaced digits
        r"\bzero\s*1\s*zero\s*2\b",           # Mixed
        r"\b01\s*02\b",                       # Grouped
    ]

    def __init__(self, trigger_token: str = "0102") -> None:
        self.trigger_token = trigger_token
        self._compiled_patterns = [
            re.compile(p, re.IGNORECASE) for p in self.TRIGGER_PATTERNS
        ]

    def detect(self, text: str) -> tuple[bool, str, str]:
        """Check if text contains trigger.

        Returns:
            (trigger_found, command_after_trigger, full_text)
        """
        text_lower = text.lower()

        for pattern in self._compiled_patterns:
            match = pattern.search(text_lower)
            if match:
                # Extract everything after the trigger
                command = text[match.end():].strip()
                return True, command, text

        return False, "", text


class VoiceCommandIngestion:
    """Convert PCM audio into commands after trigger detection.

    Pipeline:
    1. Audio chunks from youtube_live_audio
    2. faster-whisper transcription
    3. Trigger detection ("0102")
    4. Command extraction and event emission
    """

    def __init__(
        self,
        trigger_token: str = "0102",
        stt_backend: str = "faster_whisper",
        command_window_seconds: int = 5,
        model_size: str = "base",
        device: str = "cpu",
        language: Optional[str] = "en",
    ) -> None:
        """Initialize voice command ingestion.

        Args:
            trigger_token: Token to trigger command capture (default "0102")
            stt_backend: STT backend to use (faster_whisper recommended)
            command_window_seconds: Seconds to capture after trigger
            model_size: Whisper model size (tiny, base, small, medium, large-v3)
            device: Device for inference (cpu, cuda)
        """
        self.trigger_token = trigger_token
        self.stt_backend = stt_backend
        self.command_window_seconds = command_window_seconds

        # Initialize components
        self._stt = FasterWhisperSTT(model_size=model_size, device=device, language=language)
        self._trigger_detector = TriggerDetector(trigger_token)

        # State for command accumulation
        self._waiting_for_command = False
        self._command_buffer: List[str] = []

    def transcribe_audio(self, audio: np.ndarray, sample_rate: int = 16000) -> Optional[STTEvent]:
        """Transcribe a single audio chunk.

        Args:
            audio: Float32 audio data (mono)
            sample_rate: Sample rate

        Returns:
            STTEvent with transcription
        """
        return self._stt.transcribe(audio, sample_rate)

    def stream_to_text(self, audio_stream: Iterable[bytes]) -> Iterator[STTEvent]:
        """Convert PCM16 audio chunks into streaming STT events.

        Args:
            audio_stream: Iterator of PCM16 bytes

        Yields:
            STTEvent for each transcribed chunk
        """
        for pcm_bytes in audio_stream:
            # Convert PCM16 bytes to float32 numpy array
            audio = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32) / 32767.0
            event = self._stt.transcribe(audio)
            if event and event.text:
                yield event

    def stream_audio_to_text(self, audio_chunks: Iterable[np.ndarray]) -> Iterator[STTEvent]:
        """Convert float32 audio chunks into streaming STT events.

        This is the preferred interface when using AudioChunk from youtube_live_audio.

        Args:
            audio_chunks: Iterator of float32 numpy arrays

        Yields:
            STTEvent for each transcribed chunk
        """
        for audio in audio_chunks:
            event = self._stt.transcribe(audio)
            if event and event.text:
                yield event

    def detect_commands(self, events: Iterable[STTEvent]) -> Iterator[CommandEvent]:
        """Detect trigger tokens and emit command events.

        Args:
            events: Iterator of STT events

        Yields:
            CommandEvent when trigger + command detected
        """
        for event in events:
            trigger_found, command, raw_text = self._trigger_detector.detect(event.text)

            if trigger_found:
                logger.info(f"[TRIGGER] Detected '0102' - Command: '{command}'")

                yield CommandEvent(
                    command=command,
                    raw_text=raw_text,
                    trigger_detected=True,
                    timestamp_iso=datetime.now(timezone.utc).isoformat(),
                    confidence=event.confidence
                )
            else:
                # Log transcription for monitoring/digital twin training
                if event.text.strip():
                    logger.debug(f"[STT] '{event.text}'")

    def run(self, audio_stream: Iterable[bytes]) -> Iterator[CommandEvent]:
        """End to end pipeline: audio stream -> STT -> trigger -> command events.

        Args:
            audio_stream: Iterator of PCM16 bytes

        Yields:
            CommandEvent when trigger detected
        """
        return self.detect_commands(self.stream_to_text(audio_stream))

    def run_on_audio_chunks(self, audio_chunks: Iterable[np.ndarray]) -> Iterator[CommandEvent]:
        """End to end pipeline for float32 audio chunks.

        This is the preferred interface when using youtube_live_audio.

        Args:
            audio_chunks: Iterator of float32 numpy arrays

        Yields:
            CommandEvent when trigger detected
        """
        return self.detect_commands(self.stream_audio_to_text(audio_chunks))

    def process_single_chunk(self, audio: np.ndarray) -> tuple[Optional[STTEvent], Optional[CommandEvent]]:
        """Process a single audio chunk and check for trigger.

        Convenience method for testing and one-shot processing.

        Args:
            audio: Float32 audio data

        Returns:
            (STTEvent, CommandEvent or None)
        """
        event = self._stt.transcribe(audio)
        if event and event.text:
            trigger_found, command, raw_text = self._trigger_detector.detect(event.text)
            if trigger_found:
                cmd_event = CommandEvent(
                    command=command,
                    raw_text=raw_text,
                    trigger_detected=True,
                    timestamp_iso=datetime.now(timezone.utc).isoformat(),
                    confidence=event.confidence
                )
                return event, cmd_event
            return event, None
        return None, None


# Convenience function
def get_voice_ingestion(
    trigger_token: str = "0102",
    model_size: str = "base",
    device: str = "cpu",
    language: Optional[str] = "en",
) -> VoiceCommandIngestion:
    """Get a configured voice command ingestion instance."""
    return VoiceCommandIngestion(
        trigger_token=trigger_token,
        model_size=model_size,
        device=device,
        language=language,
    )


# =============================================================================
# PHASE 2: BATCH TRANSCRIPTION PIPELINE (Sprint 6)
# =============================================================================

@dataclass(frozen=True)
class TranscriptSegment:
    """Single transcription segment with timestamp for deep linking."""
    video_id: str
    title: str
    timestamp_sec: float  # Position in video
    end_sec: float  # End of segment
    text: str
    confidence: float
    url: str  # Deep link URL with timestamp


class BatchTranscriber:
    """Batch transcription pipeline for video archives.

    Connects VideoArchiveExtractor (audio source) with faster-whisper (STT)
    to produce searchable transcripts with timestamps.

    WSP Compliance:
    - WSP 84: Reuses FasterWhisperSTT
    - WSP 72: Independent of youtube_live_audio (imports only)
    """

    def __init__(
        self,
        model_size: str = "base",
        device: str = "cpu",
        output_dir: Optional[str] = None
    ) -> None:
        """Initialize batch transcriber.

        Args:
            model_size: Whisper model size (tiny, base, small, medium, large-v3)
            device: Device for inference (cpu, cuda)
            output_dir: Directory for transcript JSONL files (default: memory/transcripts)
        """
        from pathlib import Path
        self._stt = FasterWhisperSTT(model_size=model_size, device=device)
        self.output_dir = Path(output_dir) if output_dir else Path("memory/transcripts")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._progress: Dict[str, dict] = {}

    def transcribe_video(
        self,
        video_id: str,
        title: str,
        audio_chunks: Iterable,  # Generator[AudioChunk, None, None]
        chunk_duration_sec: float = 30.0
    ) -> Generator[TranscriptSegment, None, None]:
        """Transcribe a video's audio chunks to text segments.

        Args:
            video_id: YouTube video ID
            title: Video title for metadata
            audio_chunks: AudioChunk generator from VideoArchiveExtractor
            chunk_duration_sec: Expected chunk duration for progress tracking

        Yields:
            TranscriptSegment for each transcribed chunk
        """
        logger.info(f"[BATCH] Transcribing video: {title} ({video_id})")

        for chunk in audio_chunks:
            # Transcribe chunk
            event = self._stt.transcribe(chunk.audio, chunk.sample_rate)

            if event is None or not event.text.strip():
                continue

            # Calculate position in video (chunk.timestamp_ms is position in video)
            timestamp_sec = chunk.timestamp_ms / 1000.0
            end_sec = timestamp_sec + chunk.duration_sec

            # Create deep link URL
            url = f"https://youtu.be/{video_id}?t={int(timestamp_sec)}"

            yield TranscriptSegment(
                video_id=video_id,
                title=title,
                timestamp_sec=timestamp_sec,
                end_sec=end_sec,
                text=event.text.strip(),
                confidence=event.confidence,
                url=url
            )

    def transcribe_channel(
        self,
        channel_id: str,
        max_videos: int = 10,
        cache_dir: Optional[str] = None
    ) -> Generator[TranscriptSegment, None, None]:
        """Transcribe all videos from a YouTube channel.

        Args:
            channel_id: YouTube channel ID
            max_videos: Maximum videos to transcribe
            cache_dir: Audio cache directory

        Yields:
            TranscriptSegment for each transcribed segment
        """
        # Import VideoArchiveExtractor (lazy to avoid circular imports)
        try:
            from modules.platform_integration.youtube_live_audio.src.youtube_live_audio import (
                VideoArchiveExtractor
            )
        except ImportError:
            logger.error("[BATCH] youtube_live_audio module not found")
            return

        extractor = VideoArchiveExtractor(cache_dir=cache_dir)

        # Initialize progress tracking
        self._progress[channel_id] = {
            "total_videos": 0,
            "completed_videos": 0,
            "total_segments": 0,
            "status": "listing"
        }

        logger.info(f"[BATCH] Starting channel transcription: {channel_id}")

        # List and process videos
        video_count = 0
        for video in extractor.list_channel_videos(channel_id, max_videos):
            video_count += 1
            self._progress[channel_id]["total_videos"] = video_count
            self._progress[channel_id]["status"] = f"transcribing {video.video_id}"

            logger.info(f"[BATCH] Processing video {video_count}: {video.title}")

            # Stream audio chunks and transcribe
            audio_chunks = extractor.stream_video_chunks(video.video_id)

            for segment in self.transcribe_video(
                video_id=video.video_id,
                title=video.title,
                audio_chunks=audio_chunks
            ):
                self._progress[channel_id]["total_segments"] += 1
                yield segment

            self._progress[channel_id]["completed_videos"] += 1

        self._progress[channel_id]["status"] = "complete"
        logger.info(f"[BATCH] Channel transcription complete: {video_count} videos")

    def save_transcripts_jsonl(
        self,
        segments: Iterable[TranscriptSegment],
        filename: str
    ) -> int:
        """Save transcript segments to JSONL file.

        Args:
            segments: Iterator of TranscriptSegment
            filename: Output filename (will be placed in output_dir)

        Returns:
            Number of segments saved
        """
        import json
        from dataclasses import asdict

        output_path = self.output_dir / filename
        count = 0

        with open(output_path, 'w', encoding='utf-8') as f:
            for segment in segments:
                f.write(json.dumps(asdict(segment), ensure_ascii=False) + '\n')
                count += 1

        logger.info(f"[BATCH] Saved {count} segments to {output_path}")
        return count

    def get_progress(self, channel_id: str) -> dict:
        """Get transcription progress for a channel."""
        return self._progress.get(channel_id, {"status": "not_started"})


def get_batch_transcriber(
    model_size: str = "base",
    device: str = "cpu",
    output_dir: Optional[str] = None
) -> BatchTranscriber:
    """Get a configured batch transcriber instance."""
    return BatchTranscriber(
        model_size=model_size,
        device=device,
        output_dir=output_dir
    )
