# -*- coding: utf-8 -*-
"""
Dataset Builder - Create training data from indexed videos.

WSP Compliance:
    WSP 77: Agent Coordination (Digital Twin training)
    WSP 72: Module Independence
    WSP 84: Code Reuse (GemmaSegmentClassifier integration)

Purpose:
    Takes transcript outputs and produces:
    1. training_rows.jsonl - Input/output pairs for SFT
    2. voice_clips_manifest.jsonl - Clean segments for TTS (Gemma quality-filtered)
    3. training_worthy.jsonl - HIGH tier segments for Digital Twin (tier >= 2)
    4. style_stats.json - WPM, avg sentence length

Gemma Integration (V0.10.0):
    Uses GemmaSegmentClassifier for quality filtering:
    - Tier 0 (LOW): Noise, music, inaudible → skip
    - Tier 1 (REGULAR): Normal speech → include in voice_clips
    - Tier 2 (HIGH): Key insights, paradigm shifts → training_worthy
"""

import json
import logging
import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .gemma_segment_classifier import GemmaSegmentClassifier

logger = logging.getLogger(__name__)


@dataclass
class TrainingRow:
    """Single training example."""
    input: Dict[str, Any]  # context, topic_tags, intent, constraints
    output: Dict[str, Any]  # next_utterance_text
    metadata: Dict[str, Any]  # video_id, t_start, t_end


@dataclass
class VoiceClip:
    """Voice clip for TTS training."""
    video_id: str
    t_start: float
    t_end: float
    text: str
    speaker: str
    quality_score: float
    quality_tier: int = 1  # 0=LOW, 1=REGULAR, 2=HIGH (Gemma classification)
    gemma_reason: str = ""  # Why Gemma classified this tier


@dataclass
class TrainingWorthySegment:
    """HIGH-quality segment for Digital Twin training (tier >= 2)."""
    video_id: str
    title: str
    t_start: float
    t_end: float
    text: str
    speaker: str
    confidence: float  # Gemma classification confidence
    reason: str  # Why this is training-worthy
    deep_link: str = ""  # YouTube URL with timestamp


@dataclass
class StyleStats:
    """Style statistics for a video."""
    video_id: str
    wpm: float  # Words per minute
    avg_sentence_length: float
    pause_ratio: float  # Ratio of pauses to speech
    total_words: int
    total_sentences: int
    duration_seconds: float


class DatasetBuilder:
    """
    Build training datasets from video transcripts.

    Example:
        >>> builder = DatasetBuilder(use_gemma=True)
        >>> builder.process_folder("video_index/", "training_data/")

    With Gemma classification:
        >>> from gemma_segment_classifier import get_segment_classifier
        >>> classifier = get_segment_classifier()
        >>> builder = DatasetBuilder(classifier=classifier)
        >>> result = builder.process_folder("video_index/", "training_data/")
        >>> print(f"Training-worthy: {result['training_worthy']}")
    """

    def __init__(
        self,
        context_window_words: int = 50,
        min_segment_words: int = 5,
        max_segment_words: int = 100,
        classifier: Optional["GemmaSegmentClassifier"] = None,
        use_gemma: bool = False
    ):
        """
        Initialize builder.

        Args:
            context_window_words: Words of context for training
            min_segment_words: Minimum words per segment
            max_segment_words: Maximum words per segment
            classifier: Optional GemmaSegmentClassifier instance
            use_gemma: If True and classifier is None, auto-create classifier
        """
        self.context_window_words = context_window_words
        self.min_segment_words = min_segment_words
        self.max_segment_words = max_segment_words

        # Initialize Gemma classifier
        self.classifier = classifier
        if use_gemma and classifier is None:
            try:
                from .gemma_segment_classifier import get_segment_classifier
                self.classifier = get_segment_classifier()
                logger.info("[DATASET] Gemma classifier initialized")
            except Exception as e:
                logger.warning(f"[DATASET] Gemma classifier unavailable: {e}")
                self.classifier = None
    
    def process_folder(
        self,
        input_dir: str,
        output_dir: str,
        speaker_filter: Optional[str] = None
    ) -> Dict[str, int]:
        """
        Process all transcripts in a folder.

        Args:
            input_dir: Folder with transcript JSON files
            output_dir: Folder for output datasets
            speaker_filter: Optional speaker name to filter

        Returns:
            Dict with counts of processed items including training_worthy
        """
        input_path = Path(input_dir)
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        all_rows: List[TrainingRow] = []
        all_clips: List[VoiceClip] = []
        all_stats: List[StyleStats] = []
        all_training_worthy: List[TrainingWorthySegment] = []

        # Process each transcript
        for json_file in input_path.glob("*.json"):
            try:
                rows, clips, stats, training_worthy = self._process_transcript(
                    json_file, speaker_filter
                )
                all_rows.extend(rows)
                all_clips.extend(clips)
                all_training_worthy.extend(training_worthy)
                if stats:
                    all_stats.append(stats)
            except Exception as e:
                logger.warning(f"[DATASET] Failed to process {json_file}: {e}")

        # Write output files
        self._write_jsonl(output_path / "training_rows.jsonl", all_rows)
        self._write_jsonl(output_path / "voice_clips_manifest.jsonl", all_clips)
        self._write_jsonl(output_path / "training_worthy.jsonl", all_training_worthy)
        self._write_json(output_path / "style_stats.json", all_stats)

        # Log summary
        if self.classifier:
            logger.info(f"[DATASET] Gemma classified {len(all_clips)} clips -> "
                       f"{len(all_training_worthy)} training-worthy (tier >= 2)")

        return {
            "training_rows": len(all_rows),
            "voice_clips": len(all_clips),
            "training_worthy": len(all_training_worthy),
            "videos_processed": len(all_stats),
        }
    
    def _process_transcript(
        self,
        json_file: Path,
        speaker_filter: Optional[str]
    ) -> tuple[List[TrainingRow], List[VoiceClip], Optional[StyleStats], List[TrainingWorthySegment]]:
        """Process a single transcript file."""
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        video_id = data.get("video_id", json_file.stem)
        video_title = data.get("title", "")

        # Extract segments
        segments = self._extract_segments(data)

        if not segments:
            return [], [], None, []

        # Filter by speaker if specified
        if speaker_filter:
            segments = [s for s in segments if s.get("speaker") == speaker_filter]

        # Build training rows
        rows = self._build_training_rows(segments, video_id)

        # Build voice clips with Gemma classification
        clips, training_worthy = self._build_voice_clips(segments, video_id, video_title)

        # Calculate style stats
        stats = self._calculate_style_stats(segments, video_id)

        return rows, clips, stats, training_worthy
    
    def _extract_segments(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract only ground-truth/verbatim segments for model training.

        Gemini/Ask Studio segments are semantic summaries and teacher labels.
        They remain useful for retrieval and prioritization but must never be
        presented to Red Dog as words 012 actually spoke.
        """
        if isinstance(data, list):
            return data
        metadata = data.get("metadata") or {}
        transcript_source = str(data.get("transcript_source") or "").lower()

        youtube_segments = data.get("youtube_transcript")
        if isinstance(youtube_segments, list) and youtube_segments:
            return youtube_segments

        whisper_segments = data.get("whisper_transcript")
        if isinstance(whisper_segments, list) and whisper_segments:
            return whisper_segments

        if metadata.get("training_eligible") is False:
            return []
        if transcript_source in {"gemini", "gemini_summary", "studio_ask"}:
            return []
        if data.get("indexer") == "gemini" or (
            data.get("audio") or {}
        ).get("extraction_method") == "youtube_ask_gemini":
            return []

        # Legacy transcript files without an explicit provenance marker remain
        # supported; provider-labelled Gemini summaries are excluded above.
        if "segments" in data:
            return data["segments"]
        if "audio" in data and "segments" in data["audio"]:
            return data["audio"]["segments"]
        if "transcript" in data:
            # Convert plain transcript to segments
            return [{"text": data["transcript"], "start": 0, "end": 0}]
        if isinstance(data, list):
            return data
        
        return []
    
    def _build_training_rows(
        self,
        segments: List[Dict[str, Any]],
        video_id: str
    ) -> List[TrainingRow]:
        """Build training rows from segments."""
        rows = []
        
        for i, segment in enumerate(segments):
            text = segment.get("text", "").strip()
            if not text:
                continue
            
            words = text.split()
            if len(words) < self.min_segment_words:
                continue
            
            # Build context from previous segments
            context_parts = []
            word_count = 0
            for j in range(i - 1, -1, -1):
                prev_text = segments[j].get("text", "").strip()
                prev_words = prev_text.split()
                if word_count + len(prev_words) > self.context_window_words:
                    break
                context_parts.insert(0, prev_text)
                word_count += len(prev_words)
            
            context = " ".join(context_parts)
            
            # Extract topic tags (simple keyword extraction)
            topic_tags = self._extract_topics(text)
            
            row = TrainingRow(
                input={
                    "context_window_text": context,
                    "topic_tags": topic_tags,
                    "intent_label": "inform",  # Default
                    "constraints": {"max_length": 300}
                },
                output={
                    "next_utterance_text": text
                },
                metadata={
                    "video_id": video_id,
                    "t_start": segment.get("start", 0),
                    "t_end": segment.get("end", 0),
                }
            )
            rows.append(row)
        
        return rows
    
    def _build_voice_clips(
        self,
        segments: List[Dict[str, Any]],
        video_id: str,
        video_title: str = ""
    ) -> tuple[List[VoiceClip], List[TrainingWorthySegment]]:
        """
        Build voice clips manifest with Gemma classification.

        Returns:
            Tuple of (all clips with tier >= 1, training-worthy segments with tier >= 2)
        """
        clips = []
        training_worthy = []

        for segment in segments:
            text = segment.get("text", "").strip()
            words = text.split()
            t_start = segment.get("start", 0)
            t_end = segment.get("end", 0)
            speaker = segment.get("speaker", "012")

            # Skip segments that are too short or too long
            if not (self.min_segment_words <= len(words) <= self.max_segment_words):
                continue

            # Classify using Gemma if available
            if self.classifier:
                classification = self.classifier.classify_segment(
                    segment_text=text,
                    video_title=video_title,
                    speaker=speaker,
                    timestamp=t_start
                )
                quality_tier = classification.tier
                quality_score = classification.confidence
                gemma_reason = classification.reason
            else:
                # Fallback: simple heuristic (original behavior)
                quality_tier = 1  # REGULAR
                quality_score = 0.8
                if text.endswith((".", "!", "?")):
                    quality_score += 0.1
                gemma_reason = "Heuristic (no Gemma)"

            # Skip LOW tier segments (noise, music, etc.)
            if quality_tier == 0:
                continue

            # Create voice clip (tier >= 1)
            clip = VoiceClip(
                video_id=video_id,
                t_start=t_start,
                t_end=t_end,
                text=text,
                speaker=speaker,
                quality_score=min(quality_score, 1.0),
                quality_tier=quality_tier,
                gemma_reason=gemma_reason
            )
            clips.append(clip)

            # HIGH tier (tier >= 2) goes to training-worthy
            if quality_tier >= 2:
                deep_link = f"https://youtube.com/watch?v={video_id}&t={int(t_start)}"
                tw = TrainingWorthySegment(
                    video_id=video_id,
                    title=video_title,
                    t_start=t_start,
                    t_end=t_end,
                    text=text,
                    speaker=speaker,
                    confidence=quality_score,
                    reason=gemma_reason,
                    deep_link=deep_link
                )
                training_worthy.append(tw)

        return clips, training_worthy
    
    def _calculate_style_stats(
        self,
        segments: List[Dict[str, Any]],
        video_id: str
    ) -> Optional[StyleStats]:
        """Calculate style statistics."""
        if not segments:
            return None
        
        all_text = " ".join(s.get("text", "") for s in segments)
        words = all_text.split()
        sentences = re.split(r'[.!?]+', all_text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        # Calculate duration
        t_starts = [s.get("start", 0) for s in segments]
        t_ends = [s.get("end", 0) for s in segments]
        duration = max(t_ends) - min(t_starts) if t_starts and t_ends else 0
        
        # Calculate pause ratio
        speech_time = sum(s.get("end", 0) - s.get("start", 0) for s in segments)
        pause_ratio = 1 - (speech_time / duration) if duration > 0 else 0
        
        return StyleStats(
            video_id=video_id,
            wpm=len(words) / (duration / 60) if duration > 0 else 0,
            avg_sentence_length=len(words) / len(sentences) if sentences else 0,
            pause_ratio=max(0, pause_ratio),
            total_words=len(words),
            total_sentences=len(sentences),
            duration_seconds=duration,
        )
    
    def _extract_topics(self, text: str) -> List[str]:
        """Simple topic extraction via keywords."""
        keywords = {
            "japan": "japan",
            "visa": "immigration",
            "business": "business",
            "startup": "business",
            "ai": "technology",
            "consciousness": "philosophy",
            "youtube": "content",
        }
        
        text_lower = text.lower()
        topics = set()
        
        for kw, topic in keywords.items():
            if kw in text_lower:
                topics.add(topic)
        
        return list(topics) or ["general"]
    
    def _write_jsonl(self, path: Path, items: list) -> None:
        """Write items to JSONL file."""
        with open(path, "w", encoding="utf-8") as f:
            for item in items:
                if hasattr(item, "__dict__"):
                    data = asdict(item)
                else:
                    data = item
                f.write(json.dumps(data, ensure_ascii=False) + "\n")
        
        logger.info(f"[DATASET] Wrote {len(items)} items to {path}")
    
    def _write_json(self, path: Path, items: list) -> None:
        """Write items to JSON file."""
        data = [asdict(item) if hasattr(item, "__dict__") else item for item in items]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"[DATASET] Wrote stats to {path}")


# =============================================================================
# Quick Test
# =============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("=" * 60)
    print("Dataset Builder Test")
    print("=" * 60)
    
    import tempfile
    
    with tempfile.TemporaryDirectory() as input_dir:
        with tempfile.TemporaryDirectory() as output_dir:
            # Create sample transcript
            sample = {
                "video_id": "test123",
                "segments": [
                    {"text": "Welcome to my channel about Japan.", "start": 0, "end": 3},
                    {"text": "Today I want to talk about getting a work visa.", "start": 3, "end": 8},
                    {"text": "The process requires a sponsor company.", "start": 8, "end": 12},
                ]
            }
            
            with open(f"{input_dir}/test123.json", "w") as f:
                json.dump(sample, f)
            
            builder = DatasetBuilder()
            result = builder.process_folder(input_dir, output_dir)
            
            print(f"Result: {result}")
