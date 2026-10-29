"""
Gemini Video Analyzer - Direct YouTube Video Analysis via Gemini API

Uses Gemini 2.5 Flash's native video understanding to analyze YouTube videos
WITHOUT downloading. Supports both VOD and LIVE streams.

Key Discovery (2026-01-10):
    Gemini can analyze YouTube videos directly using:
    Part.from_uri(youtube_url, mime_type='video/mp4')

    Returns: Timestamped segments, transcript, speakers, topics - ONE API call.

WSP Compliance:
    - WSP 72: Module Independence
    - WSP 84: Code Reuse (follows veo3_generator.py patterns)
    - WSP 91: DAE Observability (telemetry integration)

Primary Use Case:
    Live YouTube video indexing for 012's consciousness streams.

Example:
    >>> analyzer = GeminiVideoAnalyzer()
    >>> result = analyzer.analyze_video("https://www.youtube.com/watch?v=8_DUQaqY6Tc")
    >>> print(result.segments)  # Timestamped analysis
    >>> print(result.transcript)  # Full transcript with timestamps
"""

import os
import json
import time
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime
try:
    from dotenv import load_dotenv
except ImportError:  # Core parsing/storage helpers do not require python-dotenv.
    def load_dotenv(*_args, **_kwargs):
        return False

logger = logging.getLogger(__name__)
try:
    from .video_index_metadata_db import safe_upsert_from_gemini_result
except Exception as e:
    safe_upsert_from_gemini_result = None
    logger.debug("[GEMINI-VIDEO] Metadata DB unavailable: %s", e)

# WRE PatternMemory import for adaptive learning (WSP 48)
_WRE_IMPORT_ERROR = None
try:
    from modules.infrastructure.wre_core.src.pattern_memory import PatternMemory, SkillOutcome
    import uuid
    logger.debug("[GEMINI-VIDEO] WRE PatternMemory imported successfully")
except ImportError as e:
    PatternMemory = None
    SkillOutcome = None
    _WRE_IMPORT_ERROR = e
    logger.debug("[GEMINI-VIDEO] WRE PatternMemory not available: %s", e)

# SDK imports with graceful fallback
_GENAI_IMPORT_ERROR = None
try:
    import google.genai as genai
    from google.genai import types
    logger.info("[GEMINI-VIDEO] google.genai imported successfully")
except ImportError as e:
    genai = None
    types = None
    _GENAI_IMPORT_ERROR = e
    logger.warning("[GEMINI-VIDEO] google.genai not available: %s", e)


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class VideoSegment:
    """A timestamped segment from Gemini analysis."""
    start_time: str  # "0:00", "1:23", etc.
    end_time: str
    content: str
    segment_type: str = "content"  # "intro", "content", "outro", "highlight"
    speaker: Optional[str] = None
    topics: List[str] = field(default_factory=list)


@dataclass
class GeminiAnalysisResult:
    """Complete video analysis from Gemini."""
    video_id: str
    video_url: str
    title: str
    duration: str
    summary: str
    segments: List[VideoSegment]
    transcript_summary: str
    visual_description: str
    topics: List[str]
    speakers: List[str]
    key_points: List[str]
    raw_response: str
    analyzed_at: datetime
    model_used: str
    latency_ms: float
    success: bool
    # Content category for hashtag/processing strategy (auto-detected by Gemini)
    content_category: str = "other"  # ffcpln_music, personal_vlog, ice_remix, educational, other
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "video_id": self.video_id,
            "video_url": self.video_url,
            "title": self.title,
            "duration": self.duration,
            "summary": self.summary,
            "segments": [
                {
                    "start_time": s.start_time,
                    "end_time": s.end_time,
                    "content": s.content,
                    "segment_type": s.segment_type,
                    "speaker": s.speaker,
                    "topics": s.topics,
                }
                for s in self.segments
            ],
            "transcript_summary": self.transcript_summary,
            "visual_description": self.visual_description,
            "topics": self.topics,
            "speakers": self.speakers,
            "key_points": self.key_points,
            "analyzed_at": self.analyzed_at.isoformat(),
            "model_used": self.model_used,
            "latency_ms": self.latency_ms,
            "success": self.success,
            "content_category": self.content_category,
            "error": self.error,
        }

    def to_index_format(self) -> Dict[str, Any]:
        """Convert to video_indexer storage format."""
        return {
            "video_id": self.video_id,
            "title": self.title,
            "indexed_at": self.analyzed_at.isoformat(),
            "indexer": "gemini",
            "model": self.model_used,
            "transcript_source": "gemini_summary",
            "audio": {
                "segments": [
                    {
                        "start": self._parse_timestamp(s.start_time),
                        "end": self._parse_timestamp(s.end_time),
                        "text": s.content,
                        "speaker": s.speaker,
                    }
                    for s in self.segments
                ],
                "transcript_summary": self.transcript_summary,
            },
            "visual": {
                "description": self.visual_description,
                "keyframes": [],  # Gemini doesn't return frame data
            },
            "metadata": {
                "duration": self.duration,
                "topics": self.topics,
                "speakers": self.speakers,
                "key_points": self.key_points,
                "summary": self.summary,
                "content_category": self.content_category,
                # Gemini supplies semantic descriptions, not a word-for-word
                # transcript. Keep these records searchable, but never treat
                # them as ground-truth speech for Red Dog weight training.
                "retrieval_eligible": True,
                "training_eligible": False,
                "training_exclusion_reason": "gemini_summary_not_verbatim",
            },
            "clips": {
                "candidates": [],  # Generate from segments separately
            },
        }

    @staticmethod
    def _parse_timestamp(ts: str) -> float:
        """Convert 'M:SS' or 'H:MM:SS' to seconds."""
        try:
            parts = ts.split(":")
            if len(parts) == 2:
                return int(parts[0]) * 60 + int(parts[1])
            elif len(parts) == 3:
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
            return 0.0
        except (ValueError, IndexError):
            return 0.0


# =============================================================================
# Gemini Video Analyzer
# =============================================================================

class GeminiVideoAnalyzer:
    """
    Analyze YouTube videos directly using Gemini's video understanding.

    No download required - Gemini fetches and analyzes the video via URL.
    Works with both regular videos and live streams.

    Example:
        >>> analyzer = GeminiVideoAnalyzer()
        >>> result = analyzer.analyze_video("8_DUQaqY6Tc")
        >>> print(f"Found {len(result.segments)} segments")
    """

    # Default analysis prompt for comprehensive video indexing
    DEFAULT_PROMPT = """Analyze this YouTube video comprehensively for indexing.

Return a JSON object with the following structure:
{
    "title": "Video title from content",
    "duration": "Total duration (e.g., '5:43')",
    "summary": "2-3 sentence overview of the video",
    "content_category": "ffcpln_music|personal_vlog|ice_remix|educational|other",
    "segments": [
        {
            "start_time": "0:00",
            "end_time": "0:30",
            "content": "What happens in this segment",
            "segment_type": "intro|content|highlight|outro",
            "speaker": "Speaker name if identifiable",
            "topics": ["topic1", "topic2"]
        }
    ],
    "transcript_summary": "Summary of spoken content with key quotes",
    "visual_description": "Description of visual elements, setting, graphics",
    "topics": ["Main topic 1", "Main topic 2"],
    "speakers": ["Speaker 1 name/description"],
    "key_points": ["Key point 1", "Key point 2", "Key point 3"]
}

CONTENT CATEGORY DETECTION (choose ONE):
- ffcpln_music: Instrumental/electronic music, no speech, visualizers, waveforms, ambient visuals
- personal_vlog: Person talking to camera, conversational, personal stories, daily life content
- ice_remix: Political content, ICE/immigration topics, news remixes, activist commentary
- educational: Tutorial, how-to, informational content, teaching
- other: None of the above

Ensure timestamps are accurate. For segments, aim for 15-60 second chunks.
Identify speakers by name if shown/mentioned, otherwise describe them.
Focus on indexable content: topics, key statements, visual elements."""

    # Prompt for live stream analysis
    LIVE_PROMPT = """Analyze this LIVE YouTube stream for real-time indexing.

Return a JSON object with:
{
    "title": "Stream title/topic",
    "stream_type": "live",
    "summary": "Current stream content overview",
    "segments": [
        {
            "start_time": "timestamp",
            "end_time": "timestamp",
            "content": "What's happening",
            "segment_type": "discussion|qa|demo|announcement",
            "speaker": "Current speaker"
        }
    ],
    "transcript_summary": "Recent spoken content summary",
    "visual_description": "Current visual setup",
    "topics": ["Current topics being discussed"],
    "speakers": ["Active speakers"],
    "key_points": ["Important statements made"]
}

Focus on recent content (last few minutes for live streams).
Identify any actionable items or announcements."""

    def __init__(
        self,
        model: str = "gemini-2.5-flash",
        api_key: Optional[str] = None,
    ):
        """
        Initialize Gemini Video Analyzer.

        Args:
            model: Gemini model to use (default: gemini-2.5-flash)
                   Model history:
                   - gemini-2.0-flash-exp: deprecated 2026-01
                   - gemini-2.0-flash: retiring March 2026
                   - gemini-2.5-flash: current recommended (2026-01+)
            api_key: Google API key (optional, reads from env if not provided)
        """
        if genai is None:
            raise ImportError(
                "google.genai is required. Install with: pip install google-genai"
            )

        load_dotenv(override=False)

        self.api_key = api_key or self._resolve_api_key()
        self.model = model
        self.client = genai.Client(api_key=self.api_key)

        # WRE PatternMemory for adaptive learning (WSP 48, WSP 60)
        # Lazy-loaded to avoid import failures in batch processing
        self._pattern_memory = None

        logger.info(f"[GEMINI-VIDEO] Initialized with model: {model}")

    @staticmethod
    def _resolve_api_key() -> str:
        """Resolve API key from environment."""
        # GOOGLE_API_KEY works with google.genai SDK
        # GEMINI_API_KEY may be compromised/invalid in some environments
        candidates = [
            ("GOOGLE_API_KEY", os.getenv("GOOGLE_API_KEY")),
            ("GEMINI_API_KEY", os.getenv("GEMINI_API_KEY")),
        ]
        for name, value in candidates:
            if value and not value.startswith("${"):
                logger.info(f"[GEMINI-VIDEO] Using {name}")
                return value
        raise ValueError(
            "No API key found. Set GOOGLE_API_KEY or GEMINI_API_KEY in environment."
        )

    def _build_video_url(self, video_id_or_url: str) -> str:
        """Convert video ID to full YouTube URL."""
        if video_id_or_url.startswith("http"):
            return video_id_or_url
        return f"https://www.youtube.com/watch?v={video_id_or_url}"

    def _extract_video_id(self, url: str) -> str:
        """Extract video ID from URL."""
        if "watch?v=" in url:
            return url.split("watch?v=")[1].split("&")[0]
        elif "youtu.be/" in url:
            return url.split("youtu.be/")[1].split("?")[0]
        return url  # Assume it's already just the ID

    def analyze_video(
        self,
        video_id_or_url: str,
        prompt: Optional[str] = None,
        is_live: bool = False,
    ) -> GeminiAnalysisResult:
        """
        Analyze a YouTube video using Gemini's video understanding.

        Args:
            video_id_or_url: YouTube video ID or full URL
            prompt: Custom analysis prompt (optional)
            is_live: True if analyzing a live stream

        Returns:
            GeminiAnalysisResult with comprehensive video analysis
        """
        video_url = self._build_video_url(video_id_or_url)
        video_id = self._extract_video_id(video_url)

        logger.info(f"[GEMINI-VIDEO] Analyzing: {video_id}")
        start_time = time.perf_counter()

        try:
            # Build the prompt
            analysis_prompt = prompt or (self.LIVE_PROMPT if is_live else self.DEFAULT_PROMPT)

            # Create the video part using Part.from_uri
            # This is the key discovery - Gemini fetches the video directly
            video_part = types.Part.from_uri(
                file_uri=video_url,
                mime_type="video/mp4",
            )

            # Call Gemini with video + prompt
            response = self.client.models.generate_content(
                model=self.model,
                contents=[video_part, analysis_prompt],
            )

            latency_ms = (time.perf_counter() - start_time) * 1000
            raw_text = response.text

            logger.info(f"[GEMINI-VIDEO] Analysis complete in {latency_ms:.0f}ms")

            # Parse the JSON response
            result = self._parse_response(
                raw_text=raw_text,
                video_id=video_id,
                video_url=video_url,
                latency_ms=latency_ms,
            )

            return result

        except Exception as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            error_msg = f"{type(e).__name__}: {str(e)}"
            logger.error(f"[GEMINI-VIDEO] Analysis failed: {error_msg}")

            return GeminiAnalysisResult(
                video_id=video_id,
                video_url=video_url,
                title="",
                duration="",
                summary="",
                segments=[],
                transcript_summary="",
                visual_description="",
                topics=[],
                speakers=[],
                key_points=[],
                raw_response="",
                analyzed_at=datetime.now(),
                model_used=self.model,
                latency_ms=latency_ms,
                success=False,
                error=error_msg,
            )

    def _fix_trailing_commas(self, json_str: str) -> str:
        """Remove trailing commas from JSON (common Gemini output issue).

        WSP 77 Phase 2: Auto-repair before parsing failure.
        Pattern source: scripts/repair_zero_segment_videos.py
        """
        import re
        # Remove trailing commas before closing braces/brackets
        fixed = re.sub(r',(\s*[}\]])', r'\1', json_str)
        return fixed

    def _strip_control_characters(self, json_str: str) -> str:
        """Remove invalid control characters from JSON strings.

        WSP 77 Phase 2b: Handle 'Invalid control character' errors.
        Control chars 0x00-0x1F are invalid in JSON strings (except \\t, \\n, \\r).

        Pattern: Learned from batch 39b9cf failures (2026-01-14)
        - fIMGq4izGdM: Invalid control character at line 329
        - dNr9gtanXYo: Invalid control character at line 161
        """
        import re
        # Remove control characters (0x00-0x1F) except valid JSON whitespace
        # In JSON strings, only \\t (0x09), \\n (0x0A), \\r (0x0D) are valid when escaped
        # But literal control chars in strings are always invalid
        # Match control chars that appear inside string values
        def clean_string_content(match):
            content = match.group(1)
            # Remove literal control chars except escaped ones
            # This handles: \x00-\x08, \x0B, \x0C, \x0E-\x1F
            cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', content)
            return f'"{cleaned}"'

        # Find all quoted strings and clean them
        fixed = re.sub(r'"((?:[^"\\]|\\.)*)"', clean_string_content, json_str)
        return fixed

    def _fix_json_syntax(self, json_str: str) -> str:
        """Apply all JSON repair strategies in sequence.

        WSP 77 Phase 2: Multi-stage repair pipeline.
        Order matters - apply least aggressive fixes first.

        Returns:
            Repaired JSON string
        """
        # Stage 1: Strip control characters (most common Gemini issue)
        fixed = self._strip_control_characters(json_str)

        # Stage 2: Fix trailing commas (second most common)
        fixed = self._fix_trailing_commas(fixed)

        return fixed

    def _get_pattern_memory(self):
        """Get or initialize WRE PatternMemory (lazy loading).

        Per WSP 48: Enable recursive learning from repairs.
        """
        # Parsing tests and repair-only callers may construct the analyzer with
        # ``__new__`` to avoid initializing the optional Gemini SDK. Treat a
        # missing attribute exactly like the normal lazy ``None`` state.
        if getattr(self, "_pattern_memory", None) is None and PatternMemory is not None:
            try:
                self._pattern_memory = PatternMemory()
                logger.debug("[GEMINI-VIDEO] WRE PatternMemory initialized")
            except Exception as e:
                logger.warning(f"[GEMINI-VIDEO] WRE PatternMemory init failed: {e}")
        return getattr(self, "_pattern_memory", None)

    def _store_repair_outcome(
        self,
        video_id: str,
        repair_type: str,
        segment_count: int,
        latency_ms: float,
        success: bool,
        error_type: str = None,
    ) -> None:
        """Store JSON repair outcome to WRE PatternMemory.

        Per WSP 48, WSP 60: Enable recall instead of computation.
        Stores repair outcomes for recursive learning and pattern analysis.

        Args:
            video_id: YouTube video ID
            repair_type: Type of repair applied (e.g., "json_syntax_repair")
            segment_count: Number of segments extracted after repair
            latency_ms: Parse latency in milliseconds
            success: Whether repair resulted in valid segments
            error_type: Type of JSON error encountered (if any)
        """
        memory = self._get_pattern_memory()
        if memory is None or SkillOutcome is None:
            return  # WRE not available

        try:
            outcome = SkillOutcome(
                execution_id=str(uuid.uuid4()),
                skill_name="video_indexer_json_repair",
                agent="gemma",  # Heuristic repair (fast pattern matching)
                timestamp=datetime.now().isoformat(),
                input_context=json.dumps({
                    "video_id": video_id,
                    "error_type": error_type or "unknown",
                }),
                output_result=json.dumps({
                    "repair_type": repair_type,
                    "segment_count": segment_count,
                    "success": success,
                }),
                success=success,
                pattern_fidelity=1.0 if success and segment_count > 0 else 0.0,
                outcome_quality=min(1.0, segment_count / 10.0) if success else 0.0,
                execution_time_ms=int(latency_ms),
                step_count=2,  # strip_control_chars + fix_trailing_commas
                failed_at_step=None if success else 1,
                notes=f"Repair: {repair_type}, Segments: {segment_count}",
            )
            memory.store_outcome(outcome)
            logger.debug(f"[GEMINI-VIDEO] WRE outcome stored: {repair_type}, {segment_count} segments")
        except Exception as e:
            logger.warning(f"[GEMINI-VIDEO] Failed to store WRE outcome: {e}")

    def _recall_repair_patterns(self) -> Dict[str, Any]:
        """Recall historical repair patterns from WRE PatternMemory.

        Per WSP 48, WSP 60: Enable recall instead of computation.
        Returns metrics about past repair success rates for adaptive learning.

        Returns:
            Dict with keys:
            - execution_count: Total repairs tracked
            - success_rate: Percentage of successful repairs (0.0-1.0)
            - avg_fidelity: Average pattern fidelity (0.0-1.0)
            - avg_segments: Average segments extracted
            - degradation_alert: True if recent success rate dropped below threshold
        """
        memory = self._get_pattern_memory()
        if memory is None:
            return {
                "execution_count": 0,
                "success_rate": 0.0,
                "avg_fidelity": 0.0,
                "avg_segments": 0.0,
                "degradation_alert": False,
            }

        try:
            # Recall successful patterns (limit=20 for recent history)
            successful = memory.recall_successful_patterns(
                skill_name="video_indexer_json_repair",
                min_fidelity=0.5,  # Lower threshold to include partial successes
                limit=20,
            )

            # Recall failure patterns
            failures = memory.recall_failure_patterns(
                skill_name="video_indexer_json_repair",
                max_fidelity=0.70,
                limit=20,
            )

            total = len(successful) + len(failures)
            if total == 0:
                return {
                    "execution_count": 0,
                    "success_rate": 0.0,
                    "avg_fidelity": 0.0,
                    "avg_segments": 0.0,
                    "degradation_alert": False,
                }

            # Calculate metrics (returns List[Dict], not List[SkillOutcome])
            success_rate = len(successful) / total if total > 0 else 0.0
            avg_fidelity = (
                sum(s.get("pattern_fidelity", 0.0) for s in successful) / len(successful)
                if successful else 0.0
            )

            # Extract avg segments from output_result JSON
            total_segments = 0
            for s in successful:
                try:
                    result = json.loads(s.get("output_result", "{}"))
                    total_segments += result.get("segment_count", 0)
                except (json.JSONDecodeError, TypeError):
                    pass
            avg_segments = total_segments / len(successful) if successful else 0.0

            # Degradation alert: success rate below 80% with sufficient data
            degradation_alert = total >= 5 and success_rate < 0.80

            metrics = {
                "execution_count": total,
                "success_rate": success_rate,
                "avg_fidelity": avg_fidelity,
                "avg_segments": avg_segments,
                "degradation_alert": degradation_alert,
            }

            # Log insights at appropriate level
            if degradation_alert:
                logger.warning(
                    f"[GEMINI-VIDEO] WRE ALERT: Repair success rate {success_rate:.1%} "
                    f"below threshold ({total} samples)"
                )
            elif total > 0:
                logger.debug(
                    f"[GEMINI-VIDEO] WRE recall: {total} repairs, "
                    f"{success_rate:.1%} success, {avg_fidelity:.2f} fidelity"
                )

            return metrics

        except Exception as e:
            logger.warning(f"[GEMINI-VIDEO] WRE recall failed: {e}")
            return {
                "execution_count": 0,
                "success_rate": 0.0,
                "avg_fidelity": 0.0,
                "avg_segments": 0.0,
                "degradation_alert": False,
            }

    def _parse_response(
        self,
        raw_text: str,
        video_id: str,
        video_url: str,
        latency_ms: float,
    ) -> GeminiAnalysisResult:
        """Parse Gemini's JSON response into structured result.

        WSP 77 Validation Gate:
        - Phase 1: Extract JSON from markdown
        - Phase 2: Auto-repair trailing commas (Gemini quirk)
        - Phase 3: Return success=False if no segments (not silent failure)
        """
        parse_error = None

        # WRE Phase 0: Recall historical repair patterns (WSP 48, WSP 60)
        # This enables adaptive learning - check success rates before repair
        repair_metrics = self._recall_repair_patterns()
        if repair_metrics["degradation_alert"]:
            logger.warning(
                f"[GEMINI-VIDEO] WRE degradation detected - "
                f"success_rate={repair_metrics['success_rate']:.1%}, "
                f"may need repair strategy tuning"
            )

        try:
            # Phase 1: Extract JSON from response (may have markdown code blocks)
            json_text = raw_text
            if "```json" in json_text:
                json_text = json_text.split("```json")[1].split("```")[0]
            elif "```" in json_text:
                json_text = json_text.split("```")[1].split("```")[0]

            # Phase 2: Try parsing, then auto-repair if needed (WSP 77)
            repair_applied = None
            try:
                data = json.loads(json_text.strip())
            except json.JSONDecodeError as first_error:
                # Auto-repair: apply full repair pipeline (WSP 77 Phase 2)
                # Handles: trailing commas, control characters, unicode escapes
                fixed_json = self._fix_json_syntax(json_text.strip())
                try:
                    data = json.loads(fixed_json)
                    repair_applied = "json_syntax_repair"
                    logger.info(f"[GEMINI-VIDEO] JSON repaired via _fix_json_syntax pipeline")
                except json.JSONDecodeError:
                    # Re-raise original error for better diagnostics
                    raise first_error

            # Parse segments
            segments = []
            for seg in data.get("segments", []):
                segments.append(VideoSegment(
                    start_time=seg.get("start_time", "0:00"),
                    end_time=seg.get("end_time", "0:00"),
                    content=seg.get("content", ""),
                    segment_type=seg.get("segment_type", "content"),
                    speaker=seg.get("speaker"),
                    topics=seg.get("topics", []),
                ))

            # WRE Outcome Tracking: Store repair result if repair was applied
            if repair_applied:
                self._store_repair_outcome(
                    video_id=video_id,
                    repair_type=repair_applied,
                    segment_count=len(segments),
                    latency_ms=latency_ms,
                    success=len(segments) > 0,
                    error_type="json_decode_error",
                )

            # Extract content category (auto-detected by Gemini)
            content_category = data.get("content_category", "other")
            # Validate against known categories
            valid_categories = {"ffcpln_music", "personal_vlog", "ice_remix", "educational", "other"}
            if content_category not in valid_categories:
                logger.debug(f"[GEMINI-VIDEO] Unknown category '{content_category}' -> 'other'")
                content_category = "other"

            # Phase 3: WSP 77 Validation - Return success=False if no segments
            if not segments:
                logger.warning(f"[GEMINI-VIDEO] WSP 77: No segments extracted - marking as failed")
                return GeminiAnalysisResult(
                    video_id=video_id,
                    video_url=video_url,
                    title=data.get("title", ""),
                    duration=data.get("duration", ""),
                    summary=data.get("summary", ""),
                    segments=[],
                    transcript_summary=raw_text,
                    visual_description=data.get("visual_description", ""),
                    topics=data.get("topics", []),
                    speakers=data.get("speakers", []),
                    key_points=data.get("key_points", []),
                    raw_response=raw_text,
                    analyzed_at=datetime.now(),
                    model_used=self.model,
                    latency_ms=latency_ms,
                    success=False,  # WSP 77: No segments = failed indexing
                    content_category=content_category,
                    error="No segments extracted from response",
                )

            return GeminiAnalysisResult(
                video_id=video_id,
                video_url=video_url,
                title=data.get("title", ""),
                duration=data.get("duration", ""),
                summary=data.get("summary", ""),
                segments=segments,
                transcript_summary=data.get("transcript_summary", ""),
                visual_description=data.get("visual_description", ""),
                topics=data.get("topics", []),
                speakers=data.get("speakers", []),
                key_points=data.get("key_points", []),
                raw_response=raw_text,
                analyzed_at=datetime.now(),
                model_used=self.model,
                latency_ms=latency_ms,
                success=True,
                content_category=content_category,
            )

        except json.JSONDecodeError as e:
            logger.warning(f"[GEMINI-VIDEO] WSP 77: JSON parse failed after repair attempt: {e}")

            # WSP 77: Return success=False - no silent failures
            return GeminiAnalysisResult(
                video_id=video_id,
                video_url=video_url,
                title="",
                duration="",
                summary=raw_text[:500] if raw_text else "",
                segments=[],
                transcript_summary=raw_text,
                visual_description="",
                topics=[],
                speakers=[],
                key_points=[],
                raw_response=raw_text,
                analyzed_at=datetime.now(),
                model_used=self.model,
                latency_ms=latency_ms,
                success=False,  # WSP 77: Parse failure = NOT success
                error=f"JSON parse failed: {str(e)[:100]}",
            )

    def analyze_live_stream(
        self,
        stream_url: str,
        prompt: Optional[str] = None,
    ) -> GeminiAnalysisResult:
        """
        Analyze a live YouTube stream.

        This is the PRIMARY USE CASE for 012's consciousness indexing.

        Args:
            stream_url: YouTube live stream URL
            prompt: Custom analysis prompt

        Returns:
            GeminiAnalysisResult with live stream analysis
        """
        return self.analyze_video(stream_url, prompt=prompt, is_live=True)

    def batch_analyze(
        self,
        video_ids: List[str],
        delay_between: float = 1.0,
    ) -> List[GeminiAnalysisResult]:
        """
        Analyze multiple videos in sequence.

        Args:
            video_ids: List of video IDs or URLs
            delay_between: Seconds to wait between API calls (rate limiting)

        Returns:
            List of GeminiAnalysisResult objects
        """
        results = []
        total = len(video_ids)

        for i, vid in enumerate(video_ids, 1):
            logger.info(f"[GEMINI-VIDEO] Batch progress: {i}/{total}")
            result = self.analyze_video(vid)
            results.append(result)

            if i < total:
                time.sleep(delay_between)

        success_count = sum(1 for r in results if r.success)
        logger.info(f"[GEMINI-VIDEO] Batch complete: {success_count}/{total} successful")

        return results


# =============================================================================
# Hashtag Generation
# =============================================================================

# Generic/banned terms that don't add SEO value
_BANNED_HASHTAGS = {
    "video", "youtube", "content", "watch", "subscribe", "like",
    "comment", "share", "channel", "live", "stream", "trending",
    "viral", "new", "today", "update", "episode", "part",
}

# Category-specific base hashtags (always included for that content type)
_CATEGORY_HASHTAGS = {
    "ffcpln_music": ["#shorts", "#music", "#lofi", "#ambient", "#electronic", "#ffcpln"],
    "personal_vlog": ["#vlog", "#daily", "#lifestyle"],
    "ice_remix": ["#ice", "#immigration", "#resist", "#abolishice", "#news"],
    "educational": ["#tutorial", "#howto", "#learn", "#tips"],
    "other": ["#shorts"],
}


def suggest_hashtags(
    analysis: GeminiAnalysisResult,
    max_tags: int = 15,
    max_chars: int = 30,
) -> List[str]:
    """
    Generate YouTube hashtags from Gemini video analysis.

    Extracts topics, key points, and speakers from the analysis and
    converts them to SEO-friendly hashtags. Uses content_category to
    add relevant base hashtags for SEO.

    Args:
        analysis: GeminiAnalysisResult from analyze_video()
        max_tags: Maximum number of hashtags to return
        max_chars: Maximum characters per hashtag (excluding #)

    Returns:
        List of hashtags like ["#japan", "#visa", "#tokyo"]
    """
    import re

    # Start with category-specific base hashtags
    category = getattr(analysis, "content_category", "other") or "other"
    base_tags = _CATEGORY_HASHTAGS.get(category, _CATEGORY_HASHTAGS["other"])

    raw_terms: List[str] = []

    # Primary source: topics extracted by Gemini
    raw_terms.extend(analysis.topics or [])

    # Secondary: key points (extract nouns/phrases)
    for kp in (analysis.key_points or [])[:5]:
        # Take first 3 words of each key point as potential tag
        words = kp.split()[:3]
        raw_terms.append(" ".join(words))

    # Tertiary: speakers (if named)
    for speaker in (analysis.speakers or []):
        if speaker and speaker.lower() not in ("unknown", "narrator", "speaker"):
            raw_terms.append(speaker)

    # Deduplicate and format
    seen: set = set()
    hashtags: List[str] = []

    for term in raw_terms:
        if not term:
            continue
        # Normalize: lowercase, remove non-alphanumeric (keep spaces for multi-word)
        clean = re.sub(r"[^a-z0-9\s]", "", term.lower()).strip()
        if not clean or clean in _BANNED_HASHTAGS:
            continue

        # Convert to hashtag: remove spaces or camelCase
        tag = clean.replace(" ", "")
        if len(tag) > max_chars or len(tag) < 2:
            continue

        if tag not in seen:
            seen.add(tag)
            hashtags.append(f"#{tag}")

        if len(hashtags) >= max_tags:
            break

    # Prepend category-specific base tags (they come first for SEO)
    # Remove any base tags that are duplicated in content-derived tags
    final_tags = []
    seen_final = set()
    for tag in base_tags:
        tag_clean = tag.lower()
        if tag_clean not in seen_final and len(final_tags) < max_tags:
            final_tags.append(tag)
            seen_final.add(tag_clean)

    # Add content-derived tags after base tags
    for tag in hashtags:
        tag_clean = tag.lower()
        if tag_clean not in seen_final and len(final_tags) < max_tags:
            final_tags.append(tag)
            seen_final.add(tag_clean)

    return final_tags


# =============================================================================
# Utility Functions
# =============================================================================

def save_analysis_result(
    result: GeminiAnalysisResult,
    output_dir: str = "memory/video_index",
    channel: str = "undaodu",
    index_to_holoindex: bool = True,
    merge_existing: bool = False,
) -> str:
    """
    Save analysis result to video index storage and optionally HoloIndex.

    Args:
        result: GeminiAnalysisResult to save
        output_dir: Base directory for video index
        channel: Channel name for subdirectory
        index_to_holoindex: Also index to ChromaDB for semantic search
        merge_existing: Preserve an existing canonical manifest and attach this
            result under ``gemini_enrichment`` instead of overwriting it.

    Returns:
        Path to saved file
    """
    output_path = Path(output_dir) / channel
    output_path.mkdir(parents=True, exist_ok=True)

    filename = f"{result.video_id}.json"
    filepath = output_path / filename

    payload = result.to_index_format()
    if merge_existing and filepath.exists():
        try:
            existing = json.loads(filepath.read_text(encoding="utf-8"))
            if isinstance(existing, dict):
                existing["gemini_enrichment"] = payload
                existing.setdefault("metadata", {})["gemini_enriched_at"] = (
                    result.analyzed_at.isoformat()
                )
                payload = existing
        except (OSError, json.JSONDecodeError, TypeError) as exc:
            logger.warning(
                "[GEMINI-VIDEO] Existing manifest unreadable; replacing %s: %s",
                filepath,
                exc,
            )

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    logger.info(f"[GEMINI-VIDEO] Saved index: {filepath}")

    if safe_upsert_from_gemini_result:
        safe_upsert_from_gemini_result(result, channel=channel, source_path=str(filepath))

    # Index to HoloIndex for semantic search (enables 012 digital twin)
    if index_to_holoindex:
        try:
            from holo_index.core.video_search import VideoContentIndex
            video_index = VideoContentIndex()
            segment_count = video_index.index_video(result, channel=channel)
            logger.info(f"[GEMINI-VIDEO] Indexed {segment_count} segments to HoloIndex")
        except Exception as e:
            logger.warning(f"[GEMINI-VIDEO] HoloIndex indexing failed: {e}")

    return str(filepath)


# =============================================================================
# Quick Test / Demo
# =============================================================================

if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)

    print("=" * 60)
    print("GEMINI VIDEO ANALYZER - Direct YouTube Analysis")
    print("=" * 60)

    # Test video - 012's oldest UnDaoDu video
    test_video = "8_DUQaqY6Tc"

    try:
        analyzer = GeminiVideoAnalyzer()
        print(f"\n[TEST] Analyzing video: {test_video}")
        print("(This may take 10-30 seconds...)\n")

        result = analyzer.analyze_video(test_video)

        if result.success:
            print("[SUCCESS] Video analyzed!")
            print(f"\nTitle: {result.title}")
            print(f"Duration: {result.duration}")
            print(f"Summary: {result.summary[:200]}...")
            print(f"\nSegments: {len(result.segments)}")
            for seg in result.segments[:3]:
                print(f"  [{seg.start_time}-{seg.end_time}] {seg.content[:60]}...")
            print(f"\nTopics: {', '.join(result.topics[:5])}")
            print(f"Speakers: {', '.join(result.speakers)}")
            print(f"\nLatency: {result.latency_ms:.0f}ms")

            # Save to index
            saved_path = save_analysis_result(result, channel="undaodu")
            print(f"\nSaved to: {saved_path}")
        else:
            print(f"[FAILED] {result.error}")

    except ImportError as e:
        print(f"[ERROR] Missing dependency: {e}")
        print("Install with: pip install google-genai")
        sys.exit(1)
    except ValueError as e:
        print(f"[ERROR] Configuration: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] {type(e).__name__}: {e}")
        sys.exit(1)
