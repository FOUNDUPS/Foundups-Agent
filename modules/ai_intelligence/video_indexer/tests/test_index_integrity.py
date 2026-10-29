"""Per-video identity, duplicate-response, and training-boundary regressions."""

import json
from datetime import datetime

from modules.ai_intelligence.video_indexer.src.dataset_builder import DatasetBuilder
from modules.ai_intelligence.video_indexer.src.gemini_video_analyzer import (
    GeminiAnalysisResult,
    VideoSegment,
    save_analysis_result,
)
from modules.ai_intelligence.video_indexer.src.studio_ask_indexer import (
    AskResult,
    StudioAskIndexer,
)


def test_duplicate_response_digest_is_rejected_across_video_ids(tmp_path):
    channel_dir = tmp_path / "undaodu"
    channel_dir.mkdir()
    digest = StudioAskIndexer._response_sha256('{"topics":["same"]}')
    (channel_dir / "video-a.json").write_text(
        json.dumps(
            {
                "video_id": "video-a",
                "metadata": {"provenance": {"response_sha256": digest}},
            }
        ),
        encoding="utf-8",
    )

    assert StudioAskIndexer._find_duplicate_response(
        tmp_path, "undaodu", "video-b", digest
    ) == "video-a"
    assert StudioAskIndexer._find_duplicate_response(
        tmp_path, "undaodu", "video-a", digest
    ) is None


def test_ask_artifact_records_identity_and_excludes_summary_from_training():
    response = '{"source_video_id":"video-a","topics":["FoundUps"]}'
    result = AskResult(
        video_id="video-a",
        title="A",
        response_text=response,
        topics=["FoundUps"],
        timestamps=[{"time": "0:00", "summary": "Gemini summary"}],
        success=True,
        response_video_id="video-a",
        identity_verified=True,
        response_sha256=StudioAskIndexer._response_sha256(response),
    )
    artifact = StudioAskIndexer._ask_result_to_index_data(result, "undaodu")

    assert artifact.metadata["provenance"]["requested_video_id"] == "video-a"
    assert artifact.metadata["provenance"]["identity_verified"] is True
    assert artifact.metadata["training_eligible"] is False
    assert artifact.transcript_source == "gemini_summary"


def test_dataset_builder_rejects_gemini_summary_but_accepts_verbatim():
    builder = DatasetBuilder()
    assert builder._extract_segments(
        {
            "transcript_source": "gemini_summary",
            "metadata": {"training_eligible": False},
            "audio": {"segments": [{"text": "not a quote"}]},
        }
    ) == []
    verbatim = [{"text": "actual words", "start": 0, "end": 1}]
    assert builder._extract_segments({"youtube_transcript": verbatim}) == verbatim
    assert builder._extract_segments({"indexer": "gemini", "audio": {"segments": verbatim}}) == []
    assert builder._extract_segments(verbatim) == verbatim


def test_cycle_failure_reporting_includes_nested_passes():
    from modules.ai_intelligence.video_indexer.src.action_surface import _cycle_succeeded
    assert not _cycle_succeeded({"skipped": True})
    assert not _cycle_succeeded({"channels": {"a": {"pass_errors": {"upload": "failed"}}}})
    assert not _cycle_succeeded({"channels": {"a": {"failed": 1}}})
    assert _cycle_succeeded({"channels": {"a": {"indexed": 0, "failed": 0}}})


def test_gemini_enrichment_preserves_existing_manifest(tmp_path):
    channel_dir = tmp_path / "foundups"
    channel_dir.mkdir()
    manifest = channel_dir / "video-a.json"
    manifest.write_text(
        json.dumps({"video_id": "video-a", "metadata": {"provenance": {"provider": "studio_ask"}}}),
        encoding="utf-8",
    )
    result = GeminiAnalysisResult(
        video_id="video-a",
        video_url="https://youtube.com/watch?v=video-a",
        title="A",
        duration="1:00",
        summary="Semantic summary",
        segments=[VideoSegment("0:00", "0:10", "Semantic segment")],
        transcript_summary="Summary",
        visual_description="Scene",
        topics=["FoundUps"],
        speakers=[],
        key_points=[],
        raw_response="{}",
        analyzed_at=datetime(2026, 9, 21),
        model_used="gemini-test",
        latency_ms=1.0,
        success=True,
    )

    save_analysis_result(
        result,
        output_dir=str(tmp_path),
        channel="foundups",
        index_to_holoindex=False,
        merge_existing=True,
    )
    saved = json.loads(manifest.read_text(encoding="utf-8"))
    assert saved["metadata"]["provenance"]["provider"] == "studio_ask"
    assert saved["gemini_enrichment"]["transcript_source"] == "gemini_summary"
    assert saved["gemini_enrichment"]["metadata"]["training_eligible"] is False
