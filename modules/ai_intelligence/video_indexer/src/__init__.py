"""Video indexer public API with dependency-isolated lazy imports.

Importing a lightweight surface such as ``studio_ask_indexer`` or
``action_surface`` must not require the optional Gemini, Whisper, OpenCV, or
Gemma runtimes. The previous eager imports made every action fail when any one
optional provider dependency was absent.
"""

from __future__ import annotations

from importlib import import_module
from typing import Dict, Tuple


_EXPORTS: Dict[str, Tuple[str, str]] = {
    "VideoIndexer": (".video_indexer", "VideoIndexer"),
    "IndexResult": (".video_indexer", "IndexResult"),
    "SearchResult": (".video_indexer", "SearchResult"),
    "LayerResult": (".video_indexer", "LayerResult"),
    "GeminiVideoAnalyzer": (".gemini_video_analyzer", "GeminiVideoAnalyzer"),
    "GeminiAnalysisResult": (".gemini_video_analyzer", "GeminiAnalysisResult"),
    "VideoSegment": (".gemini_video_analyzer", "VideoSegment"),
    "save_analysis_result": (".gemini_video_analyzer", "save_analysis_result"),
    "AudioAnalyzer": (".audio_analyzer", "AudioAnalyzer"),
    "VisualAnalyzer": (".visual_analyzer", "VisualAnalyzer"),
    "VisualResult": (".visual_analyzer", "VisualResult"),
    "MultimodalAligner": (".multimodal_aligner", "MultimodalAligner"),
    "MultimodalResult": (".multimodal_aligner", "MultimodalResult"),
    "ClipGenerator": (".clip_generator", "ClipGenerator"),
    "ClipGeneratorResult": (".clip_generator", "ClipGeneratorResult"),
    "VideoIndexStore": (".video_index_store", "VideoIndexStore"),
    "IndexData": (".video_index_store", "IndexData"),
    "IndexerConfig": (".indexer_config", "IndexerConfig"),
    "get_indexer_config": (".indexer_config", "get_indexer_config"),
    "reload_config": (".indexer_config", "reload_config"),
    "IndexerTelemetry": (".indexer_telemetry", "IndexerTelemetry"),
    "get_indexer_telemetry": (".indexer_telemetry", "get_indexer_telemetry"),
    "GemmaSegmentClassifier": (".gemma_segment_classifier", "GemmaSegmentClassifier"),
    "SegmentClassification": (".gemma_segment_classifier", "SegmentClassification"),
    "get_segment_classifier": (".gemma_segment_classifier", "get_segment_classifier"),
}

__all__ = list(_EXPORTS)
__version__ = "0.31.0"


def __getattr__(name: str):
    """Load only the provider requested by the caller."""
    target = _EXPORTS.get(name)
    if target is None:
        raise AttributeError(name)
    module_name, attribute = target
    value = getattr(import_module(module_name, __name__), attribute)
    globals()[name] = value
    return value
