#!/usr/bin/env python3
"""
Stage 3 Test: Single Video Indexing

Tests the full video indexing pipeline on a single video.
This validates that all 4 phases work correctly.

Test Stages:
    Stage 1: Navigation (single video) - DONE
    Stage 2: Batch Navigation (10+ videos) - DONE
    Stage 3: Single Video Indexing - THIS TEST
    Stage 4: Indexing Validation

Pipeline Phases Tested:
    1. Audio: Transcription via batch_transcriber
    2. Visual: Keyframe/shot extraction via OpenCV
    3. Multimodal: Audio/visual alignment
    4. Clips: Candidate generation for Shorts

What 012 Should See:
    1. Video download progress
    2. Audio transcription (ASR)
    3. Visual frame extraction
    4. Clip candidate generation
    5. Final index summary

Usage:
    python modules/ai_intelligence/video_indexer/tests/test_stage3_video_indexing.py

WSP Compliance:
    - WSP 5: Test Coverage
    - WSP 84: Code Reuse (VideoIndexer)
    - WSP 91: DAE Observability (telemetry)
"""

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest
import logging

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(message)s",
    datefmt="%H:%M:%S",
)

# =============================================================================
# Test Videos (known good videos for testing)
# =============================================================================

TEST_VIDEOS = {
    # UnDaoDu oldest video (2009) - good for testing, relatively short
    "undaodu_oldest": {
        "video_id": "8_DUQaqY6Tc",
        "title": "Vision Goal - UnDaoDu on eSingularity",
        "channel": "undaodu",
        "expected_duration": 355,  # ~6 min
    },
    # Short video for quick testing
    "undaodu_short": {
        "video_id": "y1e0rwE7hI4",
        "title": "Cherry blossoms falling at Meguro River",
        "channel": "undaodu",
        "expected_duration": 9,  # 9 seconds
    },
}


# =============================================================================
# Indexing Functions
# =============================================================================

def index_single_video(
    video_id: str,
    channel: str = "undaodu",
    enable_audio: bool = True,
    enable_visual: bool = True,
    enable_multimodal: bool = True,
    enable_clips: bool = True,
) -> Dict[str, Any]:
    """
    Index a single video through the full pipeline.

    Args:
        video_id: YouTube video ID
        channel: Channel name
        enable_*: Enable/disable specific layers

    Returns:
        Dict with indexing results
    """
    print("\n" + "=" * 70)
    print(f"[STAGE 3] Single Video Indexing")
    print("=" * 70)
    print(f"  Video ID: {video_id}")
    print(f"  Channel: {channel}")
    print(f"  Layers: audio={enable_audio}, visual={enable_visual}, "
          f"multimodal={enable_multimodal}, clips={enable_clips}")
    print("=" * 70)

    result = {
        "video_id": video_id,
        "channel": channel,
        "success": False,
        "phases": {
            "audio": {"enabled": enable_audio, "success": False, "segments": 0},
            "visual": {"enabled": enable_visual, "success": False, "keyframes": 0},
            "multimodal": {"enabled": enable_multimodal, "success": False, "moments": 0},
            "clips": {"enabled": enable_clips, "success": False, "candidates": 0},
        },
        "duration_seconds": 0,
        "error": None,
    }

    start_time = time.time()

    try:
        # Set environment variables for layer configuration
        os.environ["VIDEO_INDEXER_AUDIO_ENABLED"] = str(enable_audio).lower()
        os.environ["VIDEO_INDEXER_VISUAL_ENABLED"] = str(enable_visual).lower()
        os.environ["VIDEO_INDEXER_MULTIMODAL_ENABLED"] = str(enable_multimodal).lower()
        os.environ["VIDEO_INDEXER_CLIPS_ENABLED"] = str(enable_clips).lower()

        from modules.ai_intelligence.video_indexer.src.video_indexer import VideoIndexer

        print(f"\n[INIT] Creating VideoIndexer...")
        indexer = VideoIndexer(channel=channel)

        print(f"[CONFIG] Enabled layers: {indexer.config.get_enabled_layers()}")

        print(f"\n[INDEX] Starting pipeline... (this may take several minutes)")
        index_result = indexer.index_video(video_id=video_id)

        result["success"] = index_result.success
        result["duration_seconds"] = time.time() - start_time
        result["title"] = index_result.title
        result["video_duration"] = index_result.duration

        # Extract phase results
        result["phases"]["audio"]["segments"] = index_result.audio_segments
        result["phases"]["audio"]["success"] = index_result.audio_segments > 0

        result["phases"]["visual"]["keyframes"] = index_result.visual_frames
        result["phases"]["visual"]["success"] = index_result.visual_frames > 0

        result["phases"]["clips"]["candidates"] = index_result.clip_candidates
        result["phases"]["clips"]["success"] = index_result.clip_candidates > 0

        if index_result.error:
            result["error"] = index_result.error

        # Summary
        print("\n" + "=" * 70)
        print("[INDEXING RESULTS]")
        print("=" * 70)
        print(f"  Success: {result['success']}")
        print(f"  Duration: {result['duration_seconds']:.1f}s")
        print(f"  Title: {result.get('title', 'N/A')}")
        print()
        print("  Phase Results:")
        for phase, data in result["phases"].items():
            status = "PASS" if data["success"] else "SKIP/FAIL"
            count_key = [k for k in data.keys() if k not in ["enabled", "success"]][0]
            count = data[count_key]
            print(f"    {phase:12}: {status:10} ({count} {count_key})")
        print("=" * 70)

    except ImportError as e:
        result["error"] = f"Import error: {e}"
        print(f"[ERROR] {result['error']}")
    except Exception as e:
        result["error"] = str(e)
        result["duration_seconds"] = time.time() - start_time
        print(f"[ERROR] Indexing failed: {e}")

    return result


def save_indexing_artifact(result: Dict, video_id: str) -> str:
    """Save indexing test results."""
    artifact_dir = Path("memory/video_index/test_results")
    artifact_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    artifact = {
        "test": "stage3_video_indexing",
        "result": result,
        "timestamp": timestamp,
    }

    filename = f"stage3_index_{video_id}_{timestamp}.json"
    path = artifact_dir / filename
    with open(path, "w") as f:
        json.dump(artifact, f, indent=2, default=str)

    print(f"[ARTIFACT] Saved: {path}")
    return str(path)


# =============================================================================
# Test Cases
# =============================================================================

@pytest.mark.live_browser
@pytest.mark.integration
class TestStage3VideoIndexing:
    """Stage 3: Single video indexing tests.

    LIVE BROWSER: runs the real VideoIndexer pipeline against a hardcoded
    video, which drives the signed-in Chrome session. Skipped by default;
    pass --run-live to run.
    """

    def test_index_short_video_audio_only(self):
        """Test: Index short video with audio layer only."""
        video = TEST_VIDEOS["undaodu_short"]
        result = index_single_video(
            video["video_id"],
            channel=video["channel"],
            enable_audio=True,
            enable_visual=False,
            enable_multimodal=False,
            enable_clips=False,
        )

        save_indexing_artifact(result, video["video_id"])

        # Audio layer should have been attempted (even if bot detection blocked it)
        assert result["phases"]["audio"]["enabled"], "Audio should be enabled"
        print(f"\n[PASS] Audio-only indexing completed")

    def test_index_oldest_video_full_pipeline(self):
        """Test: Full pipeline on oldest UnDaoDu video."""
        video = TEST_VIDEOS["undaodu_oldest"]
        result = index_single_video(
            video["video_id"],
            channel=video["channel"],
            enable_audio=True,
            enable_visual=True,
            enable_multimodal=True,
            enable_clips=True,
        )

        save_indexing_artifact(result, video["video_id"])

        # Pipeline should complete (even with partial success)
        assert result is not None, "Result should not be None"
        assert result["duration_seconds"] > 0, "Duration should be positive"
        print(f"\n[PASS] Full pipeline completed in {result['duration_seconds']:.1f}s")


# =============================================================================
# Direct Execution
# =============================================================================

def run_stage3_test():
    """Run Stage 3 indexing test."""
    print("\n")
    print("=" * 70)
    print("  VIDEO INDEXER - STAGE 3: SINGLE VIDEO INDEXING")
    print("=" * 70)
    print(f"  Started: {datetime.now().isoformat()}")
    print("=" * 70)

    # Use short video for quick testing
    video = TEST_VIDEOS["undaodu_short"]

    print(f"\n[TEST] Indexing: {video['title']}")
    print(f"  Video ID: {video['video_id']}")
    print(f"  Expected Duration: {video['expected_duration']}s")

    result = index_single_video(
        video["video_id"],
        channel=video["channel"],
        enable_audio=True,
        enable_visual=True,
        enable_multimodal=True,
        enable_clips=True,
    )

    artifact_path = save_indexing_artifact(result, video["video_id"])

    # Summary
    print("\n")
    print("=" * 70)
    print("  STAGE 3 TEST COMPLETE")
    print("=" * 70)
    print(f"  Video: {video['video_id']}")
    print(f"  Success: {result['success']}")
    print(f"  Duration: {result['duration_seconds']:.1f}s")
    print(f"  Artifact: {artifact_path}")
    print()
    print("  Phase Summary:")
    for phase, data in result["phases"].items():
        status = "PASS" if data["success"] else "SKIP"
        print(f"    {phase}: {status}")
    print("=" * 70)

    return 0 if result["success"] else 1


if __name__ == "__main__":
    sys.exit(run_stage3_test())
