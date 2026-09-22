"""
Audio Analyzer - ASR, diarization, NLP extraction.

WSP Compliance:
    - WSP 72: Module Independence
    - WSP 84: Code Reuse (wraps get_batch_transcriber from voice_command_ingestion)
    - WSP 91: DAE Observability (integrates with video_indexer telemetry)

Integration:
    - Wraps get_batch_transcriber() for faster-whisper ASR
    - Uses existing JSONL transcript storage
    - Adds quote extraction (NLP heuristics)
    - Adds topic identification (keyword extraction)

Existing Infrastructure:
    - modules/communication/voice_command_ingestion/src/voice_command_ingestion.py:get_batch_transcriber()
    - modules/communication/voice_command_ingestion/src/transcript_index.py:VideoTranscriptIndex
    - memory/transcripts/*.jsonl - Transcript storage
"""

import logging
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class TranscriptSegment:
    """Single segment of transcribed audio."""
    text: str
    start_time: float
    end_time: float
    speaker: Optional[str] = None
    confidence: float = 1.0


@dataclass
class TranscriptResult:
    """Complete transcription result."""
    segments: List[TranscriptSegment]
    full_text: str
    duration: float
    language: str


@dataclass
class Quote:
    """Notable quote extracted from transcript."""
    text: str
    start_time: float
    end_time: float
    speaker: Optional[str] = None
    sentiment: float = 0.0  # -1 to 1


@dataclass
class Topic:
    """Topic identified in transcript."""
    name: str
    keywords: List[str]
    relevance: float
    start_time: float
    end_time: float


# =============================================================================
# Audio Analyzer
# =============================================================================

class AudioAnalyzer:
    """
    Audio content analysis: ASR, diarization, NLP extraction.

    Wraps get_batch_transcriber() from voice_command_ingestion (WSP 84).

    Example:
        >>> analyzer = AudioAnalyzer()
        >>> result = analyzer.transcribe_video("abc123")  # YouTube video ID
        >>> quotes = analyzer.extract_quotes(result)

    For local files:
        >>> result = analyzer.transcribe_file("video.mp3")
    """

    def __init__(
        self,
        whisper_model: str = "base",
        enable_diarization: bool = False,  # Default off until pyannote integration
        output_dir: Optional[str] = None,
        language: Optional[str] = None,
    ):
        """
        Initialize audio analyzer.

        Args:
            whisper_model: Whisper model size ("tiny", "base", "small", "medium", "large-v3")
            enable_diarization: Enable speaker identification (requires pyannote.audio)
            output_dir: Directory for JSONL transcripts (default: memory/transcripts)
            language: Whisper language code (e.g. "ja"), or None to detect.
        """
        self.whisper_model = whisper_model
        self.language = language
        self.enable_diarization = enable_diarization
        self.output_dir = Path(output_dir) if output_dir else Path("memory/transcripts")

        # Lazy-loaded components
        self._batch_transcriber = None
        self._whisper = None
        self._diarization = None

        logger.info(f"[AUDIO-ANALYZER] Initialized (model={whisper_model}, diarization={enable_diarization})")

    def _get_batch_transcriber(self):
        """Get batch transcriber from voice_command_ingestion (WSP 84 reuse)."""
        if self._batch_transcriber is not None:
            return self._batch_transcriber

        try:
            from modules.communication.voice_command_ingestion.src.voice_command_ingestion import (
                get_batch_transcriber,
            )
            self._batch_transcriber = get_batch_transcriber(
                model_size=self.whisper_model, language=self.language,
                output_dir=str(self.output_dir),
            )
            logger.info(f"[AUDIO-ANALYZER] Loaded batch transcriber (model={self.whisper_model})")
            return self._batch_transcriber
        except ImportError as e:
            logger.error(f"[AUDIO-ANALYZER] Failed to import batch_transcriber: {e}")
            raise

    def transcribe_video(self, video_id: str, channel_id: Optional[str] = None) -> TranscriptResult:
        """
        Transcribe YouTube video by ID using existing infrastructure.

        Uses VideoArchiveExtractor + BatchTranscriber from voice_command_ingestion (WSP 84).

        Pipeline:
            1. VideoArchiveExtractor.stream_video_chunks() - Download audio
            2. BatchTranscriber.transcribe_video() - Transcribe audio chunks

        Args:
            video_id: YouTube video ID
            channel_id: Optional channel ID for batch processing

        Returns:
            TranscriptResult with segments and full text
        """
        logger.info(f"[AUDIO-ANALYZER] Transcribing video: {video_id}")

        transcriber = self._get_batch_transcriber()

        # Get audio chunks using VideoArchiveExtractor (WSP 84 - reuse existing infrastructure)
        try:
            from modules.platform_integration.youtube_live_audio.src.youtube_live_audio import (
                VideoArchiveExtractor,
            )
            extractor = VideoArchiveExtractor()
        except ImportError as e:
            logger.error(f"[AUDIO-ANALYZER] VideoArchiveExtractor not available: {e}")
            return TranscriptResult(
                segments=[],
                full_text="",
                duration=0,
                language="unknown",
            )

        # First, get video metadata (title, duration)
        logger.info(f"[AUDIO-ANALYZER] Fetching video metadata for {video_id}")
        video_title = f"Video {video_id}"  # Default title
        try:
            # Try to get video info - this also validates the video exists
            import yt_dlp
            ydl_opts = {'quiet': True, 'no_warnings': True}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
                video_title = info.get('title', video_title)
                logger.info(f"[AUDIO-ANALYZER] Video title: {video_title[:50]}...")
        except Exception as e:
            logger.warning(f"[AUDIO-ANALYZER] Could not get video title: {e}")

        # Stream audio chunks and transcribe
        logger.info(f"[AUDIO-ANALYZER] Streaming audio chunks for {video_id}")
        audio_chunks = extractor.stream_video_chunks(video_id)

        segments_raw = list(transcriber.transcribe_video(
            video_id=video_id,
            title=video_title,
            audio_chunks=audio_chunks,
        ))

        if not segments_raw:
            logger.warning(f"[AUDIO-ANALYZER] No segments returned for {video_id}")
            return TranscriptResult(
                segments=[],
                full_text="",
                duration=0,
                language="unknown",
            )

        # Convert to our TranscriptSegment format
        segments = []
        for seg in segments_raw:
            segments.append(
                TranscriptSegment(
                    text=seg.text.strip() if hasattr(seg, 'text') else str(seg),
                    start_time=getattr(seg, 'timestamp_sec', getattr(seg, 'start_sec', 0)),
                    end_time=getattr(seg, 'end_sec', 0),
                    confidence=getattr(seg, 'confidence', 1.0),
                )
            )

        # Build full text
        full_text = " ".join(s.text for s in segments)
        duration = segments[-1].end_time if segments else 0

        logger.info(f"[AUDIO-ANALYZER] Transcribed {len(segments)} segments ({duration:.1f}s)")

        languages = {getattr(seg, 'language', 'unknown') for seg in segments_raw}
        languages.discard('unknown')
        languages.discard(None)
        language = next(iter(languages)) if len(languages) == 1 else (
            'mixed' if languages else 'unknown'
        )
        return TranscriptResult(
            segments=segments,
            full_text=full_text,
            duration=duration,
            language=language,
        )

    def transcribe_file(self, audio_path: str) -> TranscriptResult:
        """
        Transcribe local audio file (fallback for testing).

        Args:
            audio_path: Path to audio file (mp3, wav, etc.)

        Returns:
            TranscriptResult with segments and full text
        """
        return self.transcribe(audio_path)  # Use existing method

    def _load_whisper(self):
        """Lazy load Whisper model."""
        if self._whisper is not None:
            return

        try:
            import whisper
            logger.info(f"[AUDIO-ANALYZER] Loading Whisper {self.whisper_model}...")
            self._whisper = whisper.load_model(self.whisper_model)
            logger.info("[AUDIO-ANALYZER] Whisper loaded")
        except ImportError:
            logger.error("[AUDIO-ANALYZER] whisper not installed: pip install openai-whisper")
            raise

    def transcribe(self, audio_path: str) -> TranscriptResult:
        """
        Transcribe audio with timestamps.

        Args:
            audio_path: Path to audio file (mp3, wav, etc.)

        Returns:
            TranscriptResult with segments and full text
        """
        audio_path = Path(audio_path)
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        logger.info(f"[AUDIO-ANALYZER] Transcribing: {audio_path.name}")

        self._load_whisper()

        # Transcribe with Whisper
        result = self._whisper.transcribe(
            str(audio_path),
            language=self.language,
            word_timestamps=True,
            verbose=False,
        )

        # Convert to segments
        segments = []
        for seg in result.get("segments", []):
            segments.append(
                TranscriptSegment(
                    text=seg["text"].strip(),
                    start_time=seg["start"],
                    end_time=seg["end"],
                )
            )

        # Add diarization if enabled
        if self.enable_diarization:
            segments = self._add_diarization(audio_path, segments)

        return TranscriptResult(
            segments=segments,
            full_text=result.get("text", "").strip(),
            duration=segments[-1].end_time if segments else 0,
            language=result.get("language", "en"),
        )

    def _add_diarization(
        self,
        audio_path: Path,
        segments: List[TranscriptSegment],
    ) -> List[TranscriptSegment]:
        """Add speaker labels to segments using diarization."""
        # TODO: Implement pyannote.audio diarization
        # For now, return segments unchanged
        logger.debug("[AUDIO-ANALYZER] Diarization not yet implemented")
        return segments

    def extract_quotes(
        self,
        transcript: TranscriptResult,
        min_length: int = 10,
        max_length: int = 50,
    ) -> List[Quote]:
        """
        Extract notable quotes from transcript.

        Args:
            transcript: TranscriptResult from transcribe()
            min_length: Minimum quote length in words
            max_length: Maximum quote length in words

        Returns:
            List of Quote objects
        """
        logger.info("[AUDIO-ANALYZER] Extracting quotes...")

        quotes = []
        for segment in transcript.segments:
            words = segment.text.split()
            if min_length <= len(words) <= max_length:
                # Simple heuristic: quotes often have certain patterns
                # TODO: Implement proper NLP quote detection
                if self._is_quotable(segment.text):
                    quotes.append(
                        Quote(
                            text=segment.text,
                            start_time=segment.start_time,
                            end_time=segment.end_time,
                            speaker=segment.speaker,
                            sentiment=self._analyze_sentiment(segment.text),
                        )
                    )

        logger.info(f"[AUDIO-ANALYZER] Found {len(quotes)} quotes")
        return quotes

    def _is_quotable(self, text: str) -> bool:
        """Check if text is quotable based on heuristics."""
        # Simple heuristics for now
        quotable_patterns = [
            "here's what",
            "the truth is",
            "nobody tells you",
            "the secret is",
            "most people don't",
            "the real reason",
            "what I learned",
        ]
        text_lower = text.lower()
        return any(pattern in text_lower for pattern in quotable_patterns)

    def _analyze_sentiment(self, text: str) -> float:
        """Analyze sentiment of text (-1 to 1)."""
        # TODO: Implement proper sentiment analysis
        return 0.0

    def identify_topics(self, transcript: TranscriptResult) -> List[Topic]:
        """
        Extract topics using NLP.

        Args:
            transcript: TranscriptResult from transcribe()

        Returns:
            List of Topic objects
        """
        logger.info("[AUDIO-ANALYZER] Identifying topics...")

        # TODO: Implement topic modeling (LDA, BERTopic, etc.)
        # For now, return empty list

        return []


    def to_segments_list(self, result: TranscriptResult) -> List[Dict[str, Any]]:
        """
        Convert TranscriptResult to list of dicts for video_indexer pipeline.

        Args:
            result: TranscriptResult from transcribe_video()

        Returns:
            List of segment dicts compatible with video_indexer
        """
        return [
            {
                "text": seg.text,
                "start": seg.start_time,
                "end": seg.end_time,
                "speaker": seg.speaker,
                "confidence": seg.confidence,
            }
            for seg in result.segments
        ]


# =============================================================================
# Quick Test
# =============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    print("=" * 60)
    print("Audio Analyzer Test")
    print("=" * 60)

    analyzer = AudioAnalyzer(whisper_model="base", enable_diarization=False)
    print(f"Model: {analyzer.whisper_model}")
    print(f"Diarization: {analyzer.enable_diarization}")
    print(f"Output Dir: {analyzer.output_dir}")

    # Test quote detection heuristics
    print("\n--- Quote Detection Test ---")
    test_texts = [
        "Here's what nobody tells you about Japan visas",
        "The weather is nice today",
        "The truth is, starting a business is hard",
        "Most people don't realize how hard immigration is",
    ]
    for text in test_texts:
        is_quotable = analyzer._is_quotable(text)
        print(f"  '{text[:45]}...' -> quotable={is_quotable}")

    # Test batch transcriber integration (dry run - just check import)
    print("\n--- Batch Transcriber Integration Test ---")
    try:
        transcriber = analyzer._get_batch_transcriber()
        print(f"  [OK] Batch transcriber loaded: {type(transcriber).__name__}")
    except ImportError as e:
        print(f"  [WARN] Batch transcriber not available: {e}")
    except Exception as e:
        print(f"  [ERROR] Batch transcriber failed: {e}")
