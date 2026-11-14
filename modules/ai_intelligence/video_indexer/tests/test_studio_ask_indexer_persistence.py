import json
import os
import tempfile

from modules.ai_intelligence.video_indexer.src.studio_ask_indexer import (
    AskResult,
    StudioAskIndexer,
)
from modules.ai_intelligence.video_indexer.src.video_index_store import VideoIndexStore


def test_studio_ask_persists_json():
    os.environ["VIDEO_INDEX_SQLITE_DISABLE"] = "1"
    try:
        ask_result = AskResult(
            video_id="vid123",
            title="Test Video",
            response_text="Topics covered: memory, WSP",
            topics=["memory", "WSP"],
            timestamps=[
                {"time": "0:10", "topic": "Memory", "summary": "Memory basics"},
                {"time": "1:20", "topic": "WSP", "summary": "Protocol overview"},
            ],
            success=True,
        )

        index_data = StudioAskIndexer._ask_result_to_index_data(ask_result, channel_key="undaodu")

        with tempfile.TemporaryDirectory() as tmpdir:
            store = VideoIndexStore(base_path=tmpdir)
            saved_path = store.save_index("vid123", index_data)

            with open(saved_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            assert data["video_id"] == "vid123"
            assert data["channel"] == "undaodu"
            assert data["transcript_source"] == "gemini_summary"
            assert "gemini_summary" in data
            assert data["audio"]["segments"]
    finally:
        os.environ.pop("VIDEO_INDEX_SQLITE_DISABLE", None)
