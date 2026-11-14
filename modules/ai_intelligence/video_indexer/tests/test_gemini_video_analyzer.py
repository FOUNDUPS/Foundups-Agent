#!/usr/bin/env python3
"""
Test: Gemini Video Analyzer

Tests the Gemini-based video analysis for live YouTube indexing.
This is the PRIMARY indexing method for 012's consciousness streams.

Test Categories:
    1. Unit tests - API response parsing
    2. Integration tests - Actual Gemini API calls

Usage:
    # Run all tests
    python -m pytest modules/ai_intelligence/video_indexer/tests/test_gemini_video_analyzer.py -v

    # Run integration tests only (requires GOOGLE_API_KEY)
    python -m pytest modules/ai_intelligence/video_indexer/tests/test_gemini_video_analyzer.py -v -m integration

    # Run directly
    python modules/ai_intelligence/video_indexer/tests/test_gemini_video_analyzer.py

WSP Compliance:
    - WSP 5: Test Coverage
    - WSP 6: Test Audit
    - WSP 84: Code Reuse (Gemini patterns from veo3_generator)
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
from unittest.mock import Mock, patch

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest


# =============================================================================
# Test Data
# =============================================================================

MOCK_GEMINI_RESPONSE = '''```json
{
    "title": "Education Singularity",
    "duration": "6:01",
    "summary": "Michael Trauth discusses the Education Singularity concept.",
    "segments": [
        {
            "start_time": "0:00",
            "end_time": "0:30",
            "content": "Introduction by speaker",
            "segment_type": "intro",
            "speaker": "Michael Trauth",
            "topics": ["education", "technology"]
        },
        {
            "start_time": "0:30",
            "end_time": "2:00",
            "content": "Main content about education transformation",
            "segment_type": "content",
            "speaker": "Michael Trauth",
            "topics": ["singularity", "eLearning"]
        }
    ],
    "transcript_summary": "Speaker discusses radical changes in education.",
    "visual_description": "Man speaking to camera in office setting.",
    "topics": ["Education", "Technology", "eLearning"],
    "speakers": ["Michael Trauth"],
    "key_points": ["Education transformation is coming", "Technology enables free learning"]
}
```'''

TEST_VIDEOS = {
    "undaodu_oldest": {
        "video_id": "8_DUQaqY6Tc",
        "title": "Education Singularity",
        "channel": "undaodu",
    },
    "short_video": {
        "video_id": "y1e0rwE7hI4",
        "title": "Cherry blossoms at Meguro River",
        "channel": "undaodu",
    },
}


# =============================================================================
# Unit Tests (No API calls)
# =============================================================================

class TestGeminiResponseParsing:
    """Test Gemini response parsing without API calls."""

    def test_parse_json_response(self):
        """Test: Parse well-formed JSON response."""
        from modules.ai_intelligence.video_indexer.src.gemini_video_analyzer import (
            GeminiVideoAnalyzer,
            GeminiAnalysisResult,
        )

        # Create analyzer with mock (won't init API)
        with patch.object(GeminiVideoAnalyzer, '__init__', lambda x, **kw: None):
            analyzer = GeminiVideoAnalyzer()
            analyzer.model = "gemini-2.0-flash-exp"

            result = analyzer._parse_response(
                raw_text=MOCK_GEMINI_RESPONSE,
                video_id="test123",
                video_url="https://youtube.com/watch?v=test123",
                latency_ms=1000.0,
            )

            assert result.success is True
            assert result.title == "Education Singularity"
            assert result.duration == "6:01"
            assert len(result.segments) == 2
            assert result.segments[0].speaker == "Michael Trauth"
            assert "Education" in result.topics

    def test_parse_malformed_json(self):
        """Test: Handle malformed JSON gracefully."""
        from modules.ai_intelligence.video_indexer.src.gemini_video_analyzer import (
            GeminiVideoAnalyzer,
        )

        with patch.object(GeminiVideoAnalyzer, '__init__', lambda x, **kw: None):
            analyzer = GeminiVideoAnalyzer()
            analyzer.model = "gemini-2.0-flash-exp"

            # Malformed JSON has no usable segments and must fail closed.
            result = analyzer._parse_response(
                raw_text="This is not JSON, just text about the video.",
                video_id="test123",
                video_url="https://youtube.com/watch?v=test123",
                latency_ms=500.0,
            )

            assert result.success is False
            assert "This is not JSON" in result.transcript_summary

    def test_video_url_building(self):
        """Test: Build video URL from ID."""
        from modules.ai_intelligence.video_indexer.src.gemini_video_analyzer import (
            GeminiVideoAnalyzer,
        )

        with patch.object(GeminiVideoAnalyzer, '__init__', lambda x, **kw: None):
            analyzer = GeminiVideoAnalyzer()

            # Video ID should become full URL
            url = analyzer._build_video_url("abc123")
            assert url == "https://www.youtube.com/watch?v=abc123"

            # Full URL should remain unchanged
            full_url = "https://www.youtube.com/watch?v=xyz789"
            assert analyzer._build_video_url(full_url) == full_url

    def test_video_id_extraction(self):
        """Test: Extract video ID from URL."""
        from modules.ai_intelligence.video_indexer.src.gemini_video_analyzer import (
            GeminiVideoAnalyzer,
        )

        with patch.object(GeminiVideoAnalyzer, '__init__', lambda x, **kw: None):
            analyzer = GeminiVideoAnalyzer()

            # Standard watch URL
            assert analyzer._extract_video_id("https://www.youtube.com/watch?v=abc123") == "abc123"

            # Short URL
            assert analyzer._extract_video_id("https://youtu.be/xyz789") == "xyz789"

            # Just ID
            assert analyzer._extract_video_id("abc123") == "abc123"

    def test_timestamp_parsing(self):
        """Test: Parse timestamps to seconds."""
        from modules.ai_intelligence.video_indexer.src.gemini_video_analyzer import (
            GeminiAnalysisResult,
        )

        # MM:SS format
        assert GeminiAnalysisResult._parse_timestamp("1:30") == 90.0
        assert GeminiAnalysisResult._parse_timestamp("0:45") == 45.0

        # HH:MM:SS format
        assert GeminiAnalysisResult._parse_timestamp("1:02:30") == 3750.0

        # Invalid formats
        assert GeminiAnalysisResult._parse_timestamp("invalid") == 0.0
        assert GeminiAnalysisResult._parse_timestamp("") == 0.0


class TestDataClasses:
    """Test data class functionality."""

    def test_analysis_result_to_dict(self):
        """Test: Convert analysis result to dictionary."""
        from modules.ai_intelligence.video_indexer.src.gemini_video_analyzer import (
            GeminiAnalysisResult,
            VideoSegment,
        )

        result = GeminiAnalysisResult(
            video_id="test123",
            video_url="https://youtube.com/watch?v=test123",
            title="Test Video",
            duration="5:00",
            summary="Test summary",
            segments=[
                VideoSegment(
                    start_time="0:00",
                    end_time="1:00",
                    content="Test segment",
                    segment_type="content",
                )
            ],
            transcript_summary="Test transcript",
            visual_description="Test visual",
            topics=["Topic1"],
            speakers=["Speaker1"],
            key_points=["Point1"],
            raw_response="raw",
            analyzed_at=datetime.now(),
            model_used="gemini-2.0-flash-exp",
            latency_ms=1000.0,
            success=True,
        )

        d = result.to_dict()
        assert d["video_id"] == "test123"
        assert d["title"] == "Test Video"
        assert len(d["segments"]) == 1
        assert d["success"] is True

    def test_analysis_result_to_index_format(self):
        """Test: Convert to video indexer storage format."""
        from modules.ai_intelligence.video_indexer.src.gemini_video_analyzer import (
            GeminiAnalysisResult,
            VideoSegment,
        )

        result = GeminiAnalysisResult(
            video_id="test123",
            video_url="https://youtube.com/watch?v=test123",
            title="Test Video",
            duration="5:00",
            summary="Test summary",
            segments=[
                VideoSegment(
                    start_time="1:30",
                    end_time="2:00",
                    content="Test segment",
                    segment_type="content",
                    speaker="Test Speaker",
                )
            ],
            transcript_summary="Test transcript",
            visual_description="Test visual",
            topics=["Topic1"],
            speakers=["Speaker1"],
            key_points=["Point1"],
            raw_response="raw",
            analyzed_at=datetime.now(),
            model_used="gemini-2.0-flash-exp",
            latency_ms=1000.0,
            success=True,
        )

        index = result.to_index_format()

        assert index["video_id"] == "test123"
        assert index["indexer"] == "gemini"
        assert "audio" in index
        assert len(index["audio"]["segments"]) == 1
        assert index["audio"]["segments"][0]["start"] == 90.0  # 1:30 = 90s
        assert index["audio"]["segments"][0]["speaker"] == "Test Speaker"


# =============================================================================
# Integration Tests (Require API)
# =============================================================================

@pytest.mark.integration
class TestGeminiVideoAnalyzerIntegration:
    """Integration tests that call the actual Gemini API."""

    @pytest.fixture(autouse=True)
    def check_api_key(self):
        """Skip integration tests if no API key."""
        from dotenv import load_dotenv
        load_dotenv()
        if not os.getenv("GOOGLE_API_KEY") and not os.getenv("GEMINI_API_KEY"):
            pytest.skip("No GOOGLE_API_KEY or GEMINI_API_KEY set")

    def test_analyze_oldest_undaodu_video(self):
        """Test: Analyze oldest UnDaoDu video via Gemini."""
        from modules.ai_intelligence.video_indexer.src.gemini_video_analyzer import (
            GeminiVideoAnalyzer,
        )

        video = TEST_VIDEOS["undaodu_oldest"]
        analyzer = GeminiVideoAnalyzer()

        result = analyzer.analyze_video(video["video_id"])

        assert result.success is True, f"Analysis failed: {result.error}"
        assert result.video_id == video["video_id"]
        assert len(result.segments) > 0, "Should have at least one segment"
        assert result.latency_ms > 0, "Should have positive latency"

        print(f"\n[PASS] Analyzed: {result.title}")
        print(f"  Segments: {len(result.segments)}")
        print(f"  Topics: {result.topics}")
        print(f"  Latency: {result.latency_ms:.0f}ms")

    def test_video_indexer_gemini_method(self):
        """Test: VideoIndexer.index_video_gemini() integration."""
        from modules.ai_intelligence.video_indexer.src.video_indexer import VideoIndexer

        video = TEST_VIDEOS["undaodu_oldest"]
        indexer = VideoIndexer(channel="undaodu", auto_launch=False)

        result = indexer.index_video_gemini(video["video_id"], force_reindex=True)

        assert result.success is True, f"Indexing failed: {result.error}"
        assert result.audio_segments > 0, "Should have segments"

        print(f"\n[PASS] VideoIndexer Gemini: {result.title}")
        print(f"  Segments: {result.audio_segments}")

    def test_save_and_load_index(self):
        """Test: Save analysis result and verify file."""
        from modules.ai_intelligence.video_indexer.src.gemini_video_analyzer import (
            GeminiVideoAnalyzer,
            save_analysis_result,
        )

        video = TEST_VIDEOS["undaodu_oldest"]
        analyzer = GeminiVideoAnalyzer()

        result = analyzer.analyze_video(video["video_id"])

        if result.success:
            # Save to test directory
            saved_path = save_analysis_result(
                result,
                output_dir="memory/video_index/test_results",
                channel="gemini_test",
            )

            # Verify file exists
            assert Path(saved_path).exists(), f"Index file not created: {saved_path}"

            # Verify contents
            with open(saved_path) as f:
                index = json.load(f)

            assert index["video_id"] == video["video_id"]
            assert index["indexer"] == "gemini"
            assert "audio" in index
            assert len(index["audio"]["segments"]) > 0

            print(f"\n[PASS] Index saved: {saved_path}")


# =============================================================================
# Direct Execution
# =============================================================================

def run_gemini_tests():
    """Run Gemini analyzer tests directly."""
    from dotenv import load_dotenv
    load_dotenv()

    print("\n" + "=" * 70)
    print("  GEMINI VIDEO ANALYZER - TEST SUITE")
    print("=" * 70)

    # Check API key
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("\n[WARN] No GOOGLE_API_KEY or GEMINI_API_KEY set")
        print("[SKIP] Integration tests will be skipped")
        return 1

    print(f"\n[OK] API key found: {api_key[:8]}...")

    # Run unit tests
    print("\n--- Unit Tests ---")
    try:
        test_parsing = TestGeminiResponseParsing()
        test_parsing.test_parse_json_response()
        print("[PASS] test_parse_json_response")

        test_parsing.test_video_url_building()
        print("[PASS] test_video_url_building")

        test_parsing.test_video_id_extraction()
        print("[PASS] test_video_id_extraction")

        test_parsing.test_timestamp_parsing()
        print("[PASS] test_timestamp_parsing")

    except Exception as e:
        print(f"[FAIL] Unit test error: {e}")
        return 1

    # Run integration test
    print("\n--- Integration Test ---")
    try:
        from modules.ai_intelligence.video_indexer.src.gemini_video_analyzer import (
            GeminiVideoAnalyzer,
        )

        video_id = TEST_VIDEOS["undaodu_oldest"]["video_id"]
        print(f"Analyzing: {video_id}")
        print("(This may take 15-30 seconds...)\n")

        analyzer = GeminiVideoAnalyzer()
        result = analyzer.analyze_video(video_id)

        if result.success:
            print(f"[PASS] Video analyzed successfully!")
            print(f"  Title: {result.title}")
            print(f"  Segments: {len(result.segments)}")
            print(f"  Latency: {result.latency_ms:.0f}ms")
        else:
            print(f"[FAIL] Analysis failed: {result.error}")
            return 1

    except Exception as e:
        print(f"[FAIL] Integration test error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    print("\n" + "=" * 70)
    print("  ALL TESTS PASSED")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(run_gemini_tests())
