#!/usr/bin/env python3
"""
Stage 2 Test: Batch Video Navigation

Tests the system's ability to navigate through multiple videos in a channel.
This validates that we can find and list 10+ videos for batch indexing.

Test Stages:
    Stage 1: Navigation (single video) - DONE
    Stage 2: Batch Navigation (10+ videos) - THIS TEST
    Stage 3: Single Video Indexing
    Stage 4: Indexing Validation
    Stage 5: Full Channel Indexing (future)

What 012 Should See:
    1. Browser navigates to YouTube Studio
    2. Date header clicked to sort oldest first
    3. System extracts 10 videos
    4. Console shows video list with IDs

Usage:
    python modules/ai_intelligence/video_indexer/tests/test_stage2_batch_navigation.py

WSP Compliance:
    - WSP 5: Test Coverage
    - WSP 84: Code Reuse (YouTubeStudioDOM)
"""

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest

# =============================================================================
# Channel Configuration
# =============================================================================

CHANNELS = {
    "undaodu": {
        "id": "UCfHM9Fw9HD-NwiS0seD_oIA",
        "name": "UnDaoDu",
        "chrome_port": 9222,
        "expected_video_count": 2321,  # Known from earlier yt-dlp check
    },
    "move2japan": {
        "id": "UC-LSSlOZwpGIRIYihaz8zCw",
        "name": "Move2Japan",
        "chrome_port": 9222,
        "expected_video_count": 500,  # Approximate
    },
    "foundups": {
        "id": "UCSNTUXjAgpd4sgWYP0xoJgw",
        "name": "FoundUps",
        "chrome_port": 9223,  # Edge
        "expected_video_count": 100,  # Approximate
    },
}


# =============================================================================
# Batch Navigation Functions
# =============================================================================

def list_videos_batch(
    channel_key: str,
    count: int = 10,
    oldest_first: bool = True
) -> List[Dict[str, Any]]:
    """
    List multiple videos from a channel via YouTube Studio.

    Uses DOM clicks (not URL filters) to avoid bot detection.

    Args:
        channel_key: Channel key (undaodu, move2japan, foundups)
        count: Number of videos to retrieve
        oldest_first: Sort by oldest first

    Returns:
        List of video dicts with id, title, duration
    """
    channel = CHANNELS.get(channel_key.lower())
    if not channel:
        print(f"[ERROR] Unknown channel: {channel_key}")
        return []

    channel_id = channel["id"]
    chrome_port = channel.get("chrome_port", 9222)
    is_edge = (chrome_port == 9223)
    browser_name = "Edge" if is_edge else "Chrome"

    # Clean Studio URL (no filter - avoids bot detection)
    studio_url = f"https://studio.youtube.com/channel/{channel_id}/videos/upload"

    print("\n" + "=" * 70)
    print(f"[STAGE 2] Batch Video Navigation - {channel['name']}")
    print("=" * 70)
    print(f"  Channel: {channel['name']}")
    print(f"  Target: {count} videos")
    print(f"  Sort: {'Oldest First' if oldest_first else 'Newest First'}")
    print(f"  Browser: {browser_name} (port {chrome_port})")
    print("=" * 70)

    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options as ChromeOptions
        from selenium.webdriver.edge.options import Options as EdgeOptions
        from selenium.webdriver.common.by import By
        from modules.platform_integration.youtube_shorts_scheduler.src.dom_automation import YouTubeStudioDOM
        from modules.infrastructure.dependency_launcher.src.dae_dependencies import is_port_open

        # Check browser
        print(f"\n[STEP 1] Checking {browser_name}...")
        if not is_port_open(chrome_port):
            print(f"[ERROR] {browser_name} not running on port {chrome_port}")
            return []
        print(f"[OK] {browser_name} is running")

        # Connect
        print(f"\n[STEP 2] Connecting to {browser_name}...")
        if is_edge:
            options = EdgeOptions()
            options.add_experimental_option("debuggerAddress", f"127.0.0.1:{chrome_port}")
            driver = webdriver.Edge(options=options)
        else:
            options = ChromeOptions()
            options.add_experimental_option("debuggerAddress", f"127.0.0.1:{chrome_port}")
            driver = webdriver.Chrome(options=options)

        dom = YouTubeStudioDOM(driver)
        print(f"[OK] Connected")

        # Navigate to Studio
        print(f"\n[STEP 3] Navigating to YouTube Studio... (WATCH BROWSER)")
        dom.driver.get(studio_url)
        time.sleep(3)
        print(f"[OK] Page: {driver.title[:40]}...")

        # Check for error
        if "Oops" in driver.title:
            print(f"[ERROR] Wrong account - need to switch to {channel['name']} owner")
            return []

        # Sort by date (DOM click - avoids bot detection)
        if oldest_first:
            print(f"\n[STEP 4] Clicking Date header to sort... (WATCH BROWSER)")
            try:
                date_header = driver.find_element(By.CSS_SELECTOR, "button#date-header-name")
                dom.safe_click(date_header)
                time.sleep(2)
                print(f"[OK] Sorted by date")
            except Exception as e:
                print(f"[WARN] Could not sort: {e}")

        # Extract videos
        print(f"\n[STEP 5] Extracting {count} videos...")
        videos = []

        rows = dom.get_video_rows() if hasattr(dom, 'get_video_rows') else []
        if rows:
            print(f"[OK] Found {len(rows)} rows in DOM")
            for row in rows[:count]:
                try:
                    link = row.find_element(By.CSS_SELECTOR, "a[href*='/edit']")
                    href = link.get_attribute("href")
                    video_id = href.split("/video/")[1].split("/")[0]

                    # Get title
                    title = link.text or "Unknown"

                    # Try to get duration
                    try:
                        duration_el = row.find_element(By.CSS_SELECTOR, "span.duration, .ytcp-video-row-duration")
                        duration = duration_el.text
                    except:
                        duration = "N/A"

                    videos.append({
                        "video_id": video_id,
                        "title": title[:50],
                        "duration": duration,
                        "href": href,
                    })
                except Exception as e:
                    continue
        else:
            # Fallback: direct extraction
            print("[WARN] No rows via DOM, using fallback...")
            links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/video/'][href*='/edit']")
            for link in links[:count]:
                try:
                    href = link.get_attribute("href")
                    video_id = href.split("/video/")[1].split("/")[0]
                    title = link.text or link.get_attribute("title") or "Unknown"
                    videos.append({
                        "video_id": video_id,
                        "title": title[:50],
                        "duration": "N/A",
                        "href": href,
                    })
                except:
                    continue

        # Results
        print(f"\n[SUCCESS] Found {len(videos)} videos:")
        print("-" * 60)
        for i, v in enumerate(videos, 1):
            print(f"  {i:2}. {v['video_id']} | {v['duration']:>6} | {v['title'][:35]}")
        print("-" * 60)

        return videos

    except ImportError as e:
        print(f"[ERROR] Missing dependency: {e}")
        return []
    except Exception as e:
        print(f"[ERROR] Failed: {e}")
        return []


def save_batch_artifact(videos: List[Dict], channel: str) -> str:
    """Save batch navigation results."""
    artifact_dir = Path("memory/video_index/test_results")
    artifact_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    artifact = {
        "test": "stage2_batch_navigation",
        "channel": channel,
        "video_count": len(videos),
        "videos": videos,
        "timestamp": timestamp,
    }

    filename = f"stage2_batch_{channel}_{timestamp}.json"
    path = artifact_dir / filename
    with open(path, "w") as f:
        json.dump(artifact, f, indent=2)

    print(f"[ARTIFACT] Saved: {path}")
    return str(path)


# =============================================================================
# Test Cases
# =============================================================================

@pytest.mark.live_browser
@pytest.mark.integration
class TestStage2BatchNavigation:
    """Stage 2: Batch video navigation tests.

    LIVE BROWSER: attaches to a signed-in Chrome on port 9222 and navigates
    YouTube Studio. Skipped by default; pass --run-live to run.
    """

    def test_find_10_videos_undaodu(self):
        """Test: Find 10 oldest videos from UnDaoDu."""
        videos = list_videos_batch("undaodu", count=10, oldest_first=True)
        assert len(videos) >= 10, f"Expected 10 videos, got {len(videos)}"

        # Verify first video is the known oldest
        if videos:
            assert videos[0]["video_id"] == "8_DUQaqY6Tc", "First video should be oldest (2009)"

        save_batch_artifact(videos, "undaodu")
        print(f"\n[PASS] Found {len(videos)} videos from UnDaoDu")

    def test_find_10_videos_move2japan(self):
        """Test: Find 10 oldest videos from Move2Japan."""
        videos = list_videos_batch("move2japan", count=10, oldest_first=True)
        assert len(videos) >= 5, f"Expected at least 5 videos, got {len(videos)}"

        save_batch_artifact(videos, "move2japan")
        print(f"\n[PASS] Found {len(videos)} videos from Move2Japan")


# =============================================================================
# Direct Execution
# =============================================================================

def run_stage2_test():
    """Run Stage 2 batch navigation test."""
    print("\n")
    print("=" * 70)
    print("  VIDEO INDEXER - STAGE 2: BATCH NAVIGATION")
    print("=" * 70)
    print(f"  Started: {datetime.now().isoformat()}")
    print("=" * 70)

    # Test UnDaoDu (10 videos)
    print("\n[TEST 1] UnDaoDu - Finding 10 oldest videos")
    videos = list_videos_batch("undaodu", count=10, oldest_first=True)

    if len(videos) >= 10:
        print(f"\n[PASS] Found {len(videos)} videos")
        save_batch_artifact(videos, "undaodu")

        # Verify known oldest video
        if videos[0]["video_id"] == "8_DUQaqY6Tc":
            print("[PASS] First video is correct (2009 video)")
        else:
            print(f"[WARN] First video is {videos[0]['video_id']}, expected 8_DUQaqY6Tc")
    else:
        print(f"[WARN] Only found {len(videos)} videos")

    # Summary
    print("\n")
    print("=" * 70)
    print("  STAGE 2 TEST COMPLETE")
    print("=" * 70)
    print(f"  Videos Found: {len(videos)}")
    print(f"  First Video: {videos[0]['video_id'] if videos else 'None'}")
    print(f"  Last Video: {videos[-1]['video_id'] if videos else 'None'}")
    print("=" * 70)

    return 0 if len(videos) >= 10 else 1


if __name__ == "__main__":
    sys.exit(run_stage2_test())
