"""
audio_content_classifier (R&D PoC) - acoustic music-vs-talk discriminator.

Slice: RND_MUSIC_VS_TALK_DETECTION_POC. NOT wired into scheduling. See README.md.

Public API (WSP 11, see INTERFACE.md):
    from modules.ai_intelligence.audio_content_classifier.src.audio_content_classifier \
        import classify_content, ClassificationResult
"""

from .audio_content_classifier import (
    ClassificationResult,
    aggregate_stt_signals,
    classify_content,
    extract_acoustic_features,
)

__all__ = [
    "ClassificationResult",
    "classify_content",
    "extract_acoustic_features",
    "aggregate_stt_signals",
]
