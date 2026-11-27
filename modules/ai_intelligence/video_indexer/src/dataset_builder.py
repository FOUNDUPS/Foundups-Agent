# -*- coding: utf-8 -*-
"""
Dataset Builder - Create training data from indexed videos (fail-closed admission).

WSP Compliance:
    WSP 62: Large File / Function Discipline (< 800 lines, all functions <= 50 lines)
    WSP 72: Module Independence
    WSP 77: Agent Coordination (Digital Twin training)
    WSP 84: Code Reuse (GemmaSegmentClassifier + transcript_admission_guard)
    WSP 97: Truth Boundary (preserve 'unknown'/None; never invent '012' or 0.0 timestamps)
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, TYPE_CHECKING

from .transcript_admission_guard import (
    ALLOWED_PRINCIPAL_SPEAKERS,
    ALLOWED_VERBATIM_SOURCES,
    DISALLOWED_PROVIDERS,
    DISALLOWED_TRANSCRIPT_SOURCES,
    EXCLUDED_MUSIC_CHANNELS,
    NON_TARGET_SPEAKERS,
    SPEAKER_UNKNOWN,
    SPEAKER_VERIFIED,
    classify_speaker_attribution,
    detect_metadata_contradictions,
    detect_mislabeled_summary,
    parse_bool_flag,
    parse_strict_timestamp,
    summarize_record_speakers,
)

if TYPE_CHECKING:
    from .gemma_segment_classifier import GemmaSegmentClassifier

logger = logging.getLogger(__name__)


@dataclass
class TrainingRow:
    """Single training example."""
    input: Dict[str, Any]
    output: Dict[str, Any]
    metadata: Dict[str, Any]


@dataclass
class VoiceClip:
    """Timed voice clip for TTS training (requires genuine positive t_end > t_start span)."""
    video_id: str
    t_start: Optional[float]
    t_end: Optional[float]
    text: str
    speaker: str
    quality_score: float
    quality_tier: int = 1
    gemma_reason: str = ""


@dataclass
class TrainingWorthySegment:
    """HIGH-quality segment for Digital Twin training (tier >= 2)."""
    video_id: str
    title: str
    t_start: Optional[float]
    t_end: Optional[float]
    text: str
    speaker: str
    confidence: float
    reason: str
    deep_link: str = ""


@dataclass
class StyleStats:
    """Style statistics for a video."""
    video_id: str
    wpm: float
    avg_sentence_length: float
    pause_ratio: float
    total_words: int
    total_sentences: int
    duration_seconds: float


def _extract_segment_timestamps_strict(
    segment: Dict[str, Any],
) -> Tuple[Optional[float], Optional[float], str]:
    """Extract (t_start, t_end, status) without fabricating 0.0 or ignoring invalid values."""
    start_key = next((k for k in ("start", "start_time", "timestamp_sec", "t_start", "time") if k in segment and segment[k] is not None), None)
    end_key = next((k for k in ("end", "end_time", "end_sec", "t_end") if k in segment and segment[k] is not None), None)

    t_start, s_ok = parse_strict_timestamp(segment[start_key]) if start_key else (None, True)
    t_end, e_ok = parse_strict_timestamp(segment[end_key]) if end_key else (None, True)
    if not s_ok or not e_ok:
        return None, None, "invalid"
    if t_start is None and t_end is not None:
        return None, None, "invalid"
    if t_start is not None and t_end is not None and t_end < t_start:
        return None, None, "invalid"
    if (t_start is None and t_end is None) or (t_start == 0.0 and t_end == 0.0):
        return None, None, "unknown"
    if t_start is not None and t_end is not None:
        return t_start, t_end, "genuine"
    return t_start, None, "partial_start_only"


def _extract_segment_timestamps(segment: Dict[str, Any]) -> Tuple[Optional[float], Optional[float]]:
    """Compatibility wrapper returning (t_start, t_end) or (None, None) when absent/invalid."""
    t_s, t_e, _ = _extract_segment_timestamps_strict(segment)
    return t_s, t_e


def _validate_timestamps_sequence(segments: Sequence[Dict[str, Any]]) -> Optional[str]:
    """Verify all segment timestamps are valid and monotonically non-decreasing."""
    prev_start: Optional[float] = None
    prev_end: Optional[float] = None
    for seg in segments:
        t_s, t_e, status = _extract_segment_timestamps_strict(seg)
        if status == "invalid":
            return "invalid_timestamps"
        if t_s is not None:
            if (prev_start is not None and t_s < prev_start) or (prev_end is not None and t_s < prev_end):
                return "nonmonotonic_timestamps"
            prev_start = t_s
            if t_e is not None:
                prev_end = t_e
    return None


class DatasetBuilder:
    """Build training datasets from verified verbatim video transcripts."""

    def __init__(
        self,
        context_window_words: int = 50,
        min_segment_words: int = 5,
        max_segment_words: int = 100,
        classifier: Optional["GemmaSegmentClassifier"] = None,
        use_gemma: bool = False,
        require_speaker_attribution: bool = True,
        require_verified_speaker: bool = False,
    ) -> None:
        self.context_window_words = context_window_words
        self.min_segment_words = min_segment_words
        self.max_segment_words = max_segment_words
        self.require_speaker_attribution = bool(require_speaker_attribution)
        self.require_verified_speaker = bool(require_verified_speaker)
        self.classifier = classifier
        if use_gemma and classifier is None:
            try:
                from .gemma_segment_classifier import get_segment_classifier
                self.classifier = get_segment_classifier()
                logger.info("[DATASET] Gemma classifier initialized")
            except Exception as e:
                logger.warning(f"[DATASET] Gemma classifier unavailable: {e}")
                self.classifier = None
        self.last_run_report: Dict[str, Any] = {}

    def process_folder(
        self, input_dir: str, output_dir: str, speaker_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """Process all transcripts in a folder with fail-closed admission accounting."""
        input_path, output_path = Path(input_dir), Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        all_rows: List[TrainingRow] = []
        all_clips: List[VoiceClip] = []
        all_stats: List[StyleStats] = []
        all_tw: List[TrainingWorthySegment] = []
        reasons: Dict[str, int] = {}
        errors: List[Dict[str, str]] = []
        scanned = rejected = failed = 0

        for json_file in sorted(input_path.glob("*.json")):
            scanned += 1
            try:
                rows, clips, stats, tw, rej = self._process_transcript_with_reason(json_file, speaker_filter)
                if rej is not None:
                    rejected += 1
                    reasons[rej] = reasons.get(rej, 0) + 1
                    logger.info("[DATASET] Rejected %s (%s)", json_file.name, rej)
                    continue
                all_rows.extend(rows)
                all_clips.extend(clips)
                all_tw.extend(tw)
                if stats:
                    all_stats.append(stats)
            except Exception as e:
                failed += 1
                reasons["parse_or_process_error"] = reasons.get("parse_or_process_error", 0) + 1
                errors.append({"file": json_file.name, "error_type": type(e).__name__, "error": str(e)})
                logger.warning(f"[DATASET] Failed to process {json_file}: {e}")

        self._write_jsonl(output_path / "training_rows.jsonl", all_rows)
        self._write_jsonl(output_path / "voice_clips_manifest.jsonl", all_clips)
        self._write_jsonl(output_path / "training_worthy.jsonl", all_tw)
        self._write_json(output_path / "style_stats.json", all_stats)

        report: Dict[str, Any] = {
            "files_scanned": scanned, "videos_processed": len(all_stats),
            "videos_rejected": rejected, "videos_failed": failed,
            "rejection_reasons": reasons, "errors": errors,
            "training_rows": len(all_rows), "voice_clips": len(all_clips), "training_worthy": len(all_tw),
        }
        self.last_run_report = report
        return report

    def _process_transcript(
        self, json_file: Path, speaker_filter: Optional[str]
    ) -> Tuple[List[TrainingRow], List[VoiceClip], Optional[StyleStats], List[TrainingWorthySegment]]:
        """Process a single transcript file (compatibility wrapper)."""
        rows, clips, stats, training_worthy, _ = self._process_transcript_with_reason(json_file, speaker_filter)
        return rows, clips, stats, training_worthy

    def _process_transcript_with_reason(
        self, json_file: Path, speaker_filter: Optional[str]
    ) -> Tuple[List[TrainingRow], List[VoiceClip], Optional[StyleStats], List[TrainingWorthySegment], Optional[str]]:
        """Process a single transcript file and return explicit rejection reason when skipped."""
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        segments, resolved_source, rejection_reason = self.inspect_record_eligibility(data, speaker_filter=speaker_filter)
        if rejection_reason is not None or not segments:
            return [], [], None, [], rejection_reason or "empty_segments"

        meta = data.get("metadata") if isinstance(data, dict) and isinstance(data.get("metadata"), dict) else {}
        raw_vid = str(data.get("video_id") or meta.get("video_id") or "").strip() if isinstance(data, dict) else ""
        video_id = raw_vid or json_file.stem
        video_title = str(data.get("title") or meta.get("title") or "") if isinstance(data, dict) else ""
        target_segments = [s for s in segments if self._is_target_speaker(s, speaker_filter, metadata=meta)]
        if not target_segments:
            return [], [], None, [], "speaker_filtered_out"

        rows = self._build_training_rows(
            segments, video_id, speaker_filter=speaker_filter,
            transcript_source=resolved_source or "verbatim", record_metadata=meta,
        )
        clips, training_worthy = self._build_voice_clips(target_segments, video_id, video_title, record_metadata=meta)
        stats = self._calculate_style_stats(target_segments, video_id)
        return rows, clips, stats, training_worthy, None

    def _is_target_speaker(
        self, segment: Dict[str, Any], speaker_filter: Optional[str] = None,
        *, metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Check whether segment has explicit consented target speaker attribution (never defaults blank to '012')."""
        spk, status = classify_speaker_attribution(segment, metadata)
        if status == SPEAKER_UNKNOWN or spk is None:
            return (not self.require_speaker_attribution) and (speaker_filter is None)
        if self.require_verified_speaker and status != SPEAKER_VERIFIED:
            return False
        if speaker_filter:
            return spk == speaker_filter
        lowered = spk.lower()
        return False if lowered in NON_TARGET_SPEAKERS else (lowered in ALLOWED_PRINCIPAL_SPEAKERS)

    @staticmethod
    def _check_record_vetoes(
        data: Dict[str, Any], metadata: Dict[str, Any], provenance: Dict[str, Any], audio: Dict[str, Any]
    ) -> Tuple[Optional[str], str, str]:
        """Evaluate contradictions and provenance/eligibility vetoes across ALL layers without masking."""
        if detect_metadata_contradictions(data):
            return "contradictory_metadata", "", ""

        for container in (data, metadata, provenance):
            if parse_bool_flag(container.get("training_eligible")) is False:
                return "training_ineligible", "", ""
            if parse_bool_flag(container.get("consent")) is False:
                return "consent_denied", "", ""

        channels = {str(d.get("channel") or "").strip().lower() for d in (data, metadata) if d.get("channel")}
        categories = {str(d.get("content_category") or "").strip().lower() for d in (data, metadata) if d.get("content_category")}
        if (channels & EXCLUDED_MUSIC_CHANNELS) or ("ffcpln_music" in categories):
            return "music_channel_excluded", "", ""

        ts_src = str(data.get("transcript_source") or metadata.get("transcript_source") or provenance.get("transcript_source") or "").strip().lower()
        indexer = str(data.get("indexer") or metadata.get("indexer") or provenance.get("indexer") or "").strip().lower()
        provider = str(data.get("provider") or metadata.get("provider") or provenance.get("provider") or "").strip().lower()
        ext_m = str(audio.get("extraction_method") or metadata.get("extraction_method") or "").strip().lower()
        if ts_src in DISALLOWED_TRANSCRIPT_SOURCES or indexer in DISALLOWED_PROVIDERS or provider in DISALLOWED_PROVIDERS or ext_m in DISALLOWED_TRANSCRIPT_SOURCES:
            return "disallowed_provenance", ts_src, ext_m
        return None, ts_src, ext_m

    @staticmethod
    def _resolve_candidate_segments(
        data: Dict[str, Any], audio: Dict[str, Any], ts_src: str, ext_m: str
    ) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str], Optional[str]]:
        """Extract raw candidate segment dicts when explicit ground-truth provenance exists."""
        has_verbatim_container = False
        for vf in ("youtube_transcript", "whisper_transcript"):
            if isinstance(data.get(vf), list):
                has_verbatim_container = True
                if any(not isinstance(s, dict) for s in data[vf]):
                    return None, None, "invalid_segment_schema"
                valid = [
                    s for s in data[vf]
                    if str(s.get("text") or s.get("content") or s.get("summary") or "").strip() or "ask_segments" in s
                ]
                if valid:
                    return valid, vf, None

        resolved = ts_src if ts_src in ALLOWED_VERBATIM_SOURCES else (ext_m if ext_m in ALLOWED_VERBATIM_SOURCES else "")
        if not resolved:
            return None, None, ("empty_segments" if has_verbatim_container else "missing_verbatim_provenance")

        for seg_list in (data.get("segments"), audio.get("segments")):
            if isinstance(seg_list, list):
                if any(not isinstance(s, dict) for s in seg_list):
                    return None, None, "invalid_segment_schema"
                valid = [
                    s for s in seg_list
                    if str(s.get("text") or s.get("content") or s.get("summary") or "").strip() or "ask_segments" in s
                ]
                return (valid, resolved, None) if valid else (None, None, "empty_segments")

        if isinstance(data.get("transcript"), str):
            text = data["transcript"].strip()
            seg = {"text": text, "start": None, "end": None, "speaker": data.get("speaker"), "speaker_verified": data.get("speaker_verified")}
            return ([seg], resolved, None) if text else (None, None, "empty_segments")
        return None, None, "empty_segments"

    def inspect_record_eligibility(
        self, data: Any, *, speaker_filter: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], Optional[str], Optional[str]]:
        """Evaluate training eligibility, provenance, summary leakage, timestamps, and speakers fail-closed."""
        if isinstance(data, list):
            return [], None, "unlabeled_raw_list"
        if not isinstance(data, dict):
            return [], None, "invalid_record_type"

        metadata = data.get("metadata") if isinstance(data.get("metadata"), dict) else {}
        provenance = metadata.get("provenance") if isinstance(metadata.get("provenance"), dict) else {}
        audio = data.get("audio") if isinstance(data.get("audio"), dict) else {}

        veto, ts_src, ext_m = self._check_record_vetoes(data, metadata, provenance, audio)
        if veto is not None:
            return [], None, veto

        candidates, resolved, err = self._resolve_candidate_segments(data, audio, ts_src, ext_m)
        if err is not None or not candidates or not resolved:
            return [], None, err or "empty_segments"

        if detect_mislabeled_summary(data, candidates, has_verbatim_claim=True) is not None:
            return [], None, "mislabeled_summary_as_transcript"

        ts_err = _validate_timestamps_sequence(candidates)
        if ts_err is not None:
            return [], None, ts_err

        if self.require_speaker_attribution:
            spk_info = summarize_record_speakers(candidates, metadata)
            if not spk_info["known_speakers"]:
                return [], None, "missing_speaker_attribution"
            if not any(self._is_target_speaker(s, speaker_filter, metadata=metadata) for s in candidates):
                return [], None, "speaker_filtered_out"

        return candidates, resolved, None

    def _extract_segments(self, data: Any) -> List[Dict[str, Any]]:
        """Extract only verified ground-truth/verbatim target-eligible segments for training."""
        segments, _, _ = self.inspect_record_eligibility(data)
        return segments

    def _collect_context_window(
        self, segments: List[Dict[str, Any]], upto_idx: int, metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, List[str]]:
        """Collect bounded preceding context and honest speaker labels ('unknown' when absent, never '012')."""
        parts: List[str] = []
        ctx_speakers: List[str] = []
        word_count = 0
        for j in range(upto_idx - 1, -1, -1):
            prev_text = str(segments[j].get("text") or "").strip()
            if not prev_text:
                continue
            prev_words = prev_text.split()
            if word_count + len(prev_words) > self.context_window_words:
                break
            spk, _ = classify_speaker_attribution(segments[j], metadata)
            parts.insert(0, prev_text)
            ctx_speakers.insert(0, spk if spk is not None else SPEAKER_UNKNOWN)
            word_count += len(prev_words)
        return " ".join(parts), ctx_speakers

    def _build_training_rows(
        self, segments: List[Dict[str, Any]], video_id: str,
        speaker_filter: Optional[str] = None, transcript_source: str = "verbatim",
        record_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[TrainingRow]:
        """Build training rows from admitted target segments without inventing '012' or 0.0 timestamps."""
        spk_summary = summarize_record_speakers(segments, record_metadata)
        rows: List[TrainingRow] = []
        for i, segment in enumerate(segments):
            if not self._is_target_speaker(segment, speaker_filter, metadata=record_metadata):
                continue
            text = str(segment.get("text") or "").strip()
            if not text or len(text.split()) < self.min_segment_words:
                continue
            t_start, t_end, ts_status = _extract_segment_timestamps_strict(segment)
            spk, spk_status = classify_speaker_attribution(segment, record_metadata)
            speaker_label = spk if spk is not None else SPEAKER_UNKNOWN
            ctx_text, ctx_speakers = self._collect_context_window(segments, i, record_metadata)
            rows.append(TrainingRow(
                input={
                    "context_window_text": ctx_text,
                    "context_speakers": ctx_speakers,
                    "topic_tags": self._extract_topics(text),
                    "intent_label": "inform",
                    "constraints": {"max_length": 300},
                },
                output={"next_utterance_text": text},
                metadata={
                    "video_id": video_id, "t_start": t_start, "t_end": t_end,
                    "timestamp_status": ts_status, "speaker": speaker_label,
                    "speaker_status": spk_status, "has_mixed_speakers": spk_summary["has_mixed_speakers"],
                    "transcript_source": transcript_source,
                },
            ))
        return rows

    def _score_voice_segment(
        self, text: str, video_title: str, speaker: str, t_start: float
    ) -> Tuple[int, float, str]:
        """Classify segment quality tier via Gemma or heuristic fallback."""
        if self.classifier:
            cls = self.classifier.classify_segment(
                segment_text=text, video_title=video_title, speaker=speaker, timestamp=t_start,
            )
            return cls.tier, cls.confidence, cls.reason
        score = 0.9 if text.endswith((".", "!", "?")) else 0.8
        return 1, score, "Heuristic (no Gemma)"

    def _build_voice_clips(
        self, segments: List[Dict[str, Any]], video_id: str, video_title: str = "",
        record_metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[VoiceClip], List[TrainingWorthySegment]]:
        """Build timed voice clips ONLY when genuine positive span (t_end > t_start) and attributed speaker exist."""
        clips: List[VoiceClip] = []
        training_worthy: List[TrainingWorthySegment] = []
        for segment in segments:
            text = str(segment.get("text") or "").strip()
            if not (self.min_segment_words <= len(text.split()) <= self.max_segment_words):
                continue
            t_start, t_end, ts_status = _extract_segment_timestamps_strict(segment)
            if ts_status != "genuine" or t_start is None or t_end is None or t_end <= t_start:
                continue
            spk, spk_status = classify_speaker_attribution(segment, record_metadata)
            if spk_status == SPEAKER_UNKNOWN or spk is None:
                continue
            tier, score, reason = self._score_voice_segment(text, video_title, spk, t_start)
            if tier == 0:
                continue
            clips.append(VoiceClip(video_id, t_start, t_end, text, spk, min(score, 1.0), tier, reason))
            if tier >= 2:
                link = f"https://youtube.com/watch?v={video_id}&t={int(t_start)}"
                training_worthy.append(TrainingWorthySegment(video_id, video_title, t_start, t_end, text, spk, score, reason, link))
        return clips, training_worthy

    def _calculate_style_stats(
        self, segments: List[Dict[str, Any]], video_id: str
    ) -> Optional[StyleStats]:
        """Calculate style statistics across valid positive timestamp spans only."""
        if not segments:
            return None
        all_text = " ".join(str(s.get("text") or "") for s in segments)
        words = all_text.split()
        sentences = [s.strip() for s in re.split(r"[.!?]+", all_text) if s.strip()]
        valid_spans = [
            (ts, te)
            for s in segments
            for ts, te, st in [_extract_segment_timestamps_strict(s)]
            if st == "genuine" and ts is not None and te is not None and te > ts
        ]
        duration = (max(e for _, e in valid_spans) - min(s for s, _ in valid_spans)) if valid_spans else 0.0
        speech_time = sum(e - s for s, e in valid_spans) if valid_spans else 0.0
        pause_ratio = max(0.0, 1.0 - (speech_time / duration)) if duration > 0 else 0.0
        return StyleStats(
            video_id=video_id,
            wpm=len(words) / (duration / 60.0) if duration > 0 else 0.0,
            avg_sentence_length=len(words) / len(sentences) if sentences else 0.0,
            pause_ratio=pause_ratio,
            total_words=len(words),
            total_sentences=len(sentences),
            duration_seconds=duration,
        )

    def _extract_topics(self, text: str) -> List[str]:
        """Simple topic extraction via keywords."""
        keywords = {
            "japan": "japan", "visa": "immigration", "business": "business",
            "startup": "business", "ai": "technology", "consciousness": "philosophy", "youtube": "content",
        }
        text_lower = text.lower()
        topics = {topic for kw, topic in keywords.items() if kw in text_lower}
        return sorted(topics) or ["general"]

    def _write_jsonl(self, path: Path, items: list) -> None:
        """Write items to JSONL file."""
        with open(path, "w", encoding="utf-8") as f:
            for item in items:
                data = asdict(item) if hasattr(item, "__dict__") else item
                f.write(json.dumps(data, ensure_ascii=False) + "\n")
        logger.info(f"[DATASET] Wrote {len(items)} items to {path}")

    def _write_json(self, path: Path, items: list) -> None:
        """Write items to JSON file."""
        data = [asdict(item) if hasattr(item, "__dict__") else item for item in items]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info(f"[DATASET] Wrote stats to {path}")
