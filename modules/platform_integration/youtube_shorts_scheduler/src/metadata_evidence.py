"""Validate existing analyzer evidence before generating public video metadata.

No model or browser calls. This checks provenance/identity, not factual truth.
Legacy title-only stubs are deliberately ineligible.
"""
from typing import Any, Dict, Optional


def validated_video_evidence(index: Dict[str, Any], video_id: str) -> Optional[dict]:
    if not isinstance(index, dict) or not video_id or index.get("video_id") != video_id:
        return None
    if index.get("success") is False or index.get("error") or index.get("errors"):
        return None
    metadata = index.get("metadata")
    if not isinstance(metadata, dict) or metadata.get("retrieval_eligible") is not True:
        return None
    if not index.get("indexed_at"):
        return None
    if index.get("transcript_source") in {"whisper", "faster_whisper", "stt", "whisper_transcript", "youtube_transcript", "youtube", "stacked"}:
        audio = index.get("audio") or {}
        if not isinstance(audio, dict):
            return None
        segments = index.get("youtube_transcript") or index.get("whisper_transcript") or audio.get("segments")
        if not isinstance(segments, list) or not segments:
            return None
        valid = []
        for segment in segments:
            if not isinstance(segment, dict):
                return None
            start, end, text = segment.get("start"), segment.get("end"), segment.get("text")
            if (type(start) not in (int, float) or type(end) not in (int, float)
                    or not 0 <= start < end or not isinstance(text, str) or not text.strip()):
                return None
            valid.append(text.strip())
        return {"text": " ".join(valid), "source": index["transcript_source"],
                "modality": "speech_transcript", "video_id": video_id,
                "indexed_at": index["indexed_at"], "coverage": "provided_segments_only",
                "training_eligible": False}
    if index.get("transcript_source") != "gemini_summary":
        return None
    provenance = metadata.get("provenance") or {}
    if not isinstance(provenance, dict):
        return None
    if provenance.get("provider") == "youtube_studio_ask":
        if (provenance.get("identity_verified") is not True
                or provenance.get("requested_video_id") != video_id
                or provenance.get("response_video_id") != video_id
                or not provenance.get("response_sha256")):
            return None
        source = "youtube_studio_ask_summary"
    elif index.get("indexer") == "gemini" and index.get("model"):
        source = "gemini_video_summary"
    else:
        return None
    audio = index.get("audio") or {}
    visual = index.get("visual") or {}
    if not isinstance(audio, dict) or not isinstance(visual, dict):
        return None
    transcript = audio.get("transcript_summary")
    visual_text = visual.get("description")
    # Do not fall back to title, topics, key_points, category, duration or a stub.
    text = transcript if isinstance(transcript, str) and transcript.strip() else visual_text
    if not isinstance(text, str) or not text.strip():
        return None
    modality = "audio_summary" if isinstance(transcript, str) and transcript.strip() else "visual_summary"
    return {"text": " ".join(text.split()), "source": source, "modality": modality,
            "video_id": video_id, "indexed_at": index["indexed_at"],
            "coverage": "not_established", "training_eligible": False}
