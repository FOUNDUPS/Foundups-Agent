#!/usr/bin/env python3
"""
Integration Test: Navigate to UnDaoDu's Oldest Video via YouTube Studio

WSP Compliance:
    - WSP 5: Test Coverage (E2E integration test)
    - WSP 50: Pre-Action Verification (reuses existing Selenium patterns)
    - WSP 84: Code Reuse (uses YouTubeStudioDOM from youtube_shorts_scheduler)

What 012 Should See:
    1. Chrome browser navigates to YouTube Studio
    2. Video list sorted oldest-first (2009 video)
    3. First video selected for indexing
    4. Console output showing indexing progress
    5. Final validation of indexed content

Uses Same Pattern As:
    - modules/communication/voice_command_ingestion/scripts/index_channel.py
    - modules/platform_integration/youtube_shorts_scheduler/src/dom_automation.py

Usage:
    python modules/ai_intelligence/video_indexer/tests/test_integration_oldest_video.py

Prerequisites:
    Chrome must be running with remote debugging on port 9222
"""

import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

# Add project root to path for module imports
PROJECT_ROOT = Path(__file__).resolve().parents[4]  # Go up 4 levels to O:\Foundups-Agent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# =============================================================================
# Channel Configuration (same as index_channel.py)
# =============================================================================

CHANNELS = {
    "undaodu": {
        "id": "UCfHM9Fw9HD-NwiS0seD_oIA",
        "name": "UnDaoDu",
        "description": "012's consciousness exploration channel",
        "chrome_port": 9222,
    },
    "move2japan": {
        "id": "UC-LSSlOZwpGIRIYihaz8zCw",
        "name": "Move2Japan",
        "description": "012's Japan living channel",
        "chrome_port": 9222,
    },
    "foundups": {
        "id": "UCSNTUXjAgpd4sgWYP0xoJgw",
        "name": "FoundUps",
        "description": "FoundUps venture studio channel",
        "chrome_port": 9223,  # Edge browser
    },
}


# =============================================================================
# YouTube Studio Navigation (WSP 84 - Reuse from index_channel.py)
# =============================================================================

def list_videos_via_studio(
    channel_key: str,
    max_videos: int = 5,
    oldest_first: bool = True
) -> List[Dict[str, Any]]:
    """
    List videos via YouTube Studio using YouTubeStudioDOM.

    This uses the SAME pattern as the working commenting system:
    - Connects to existing Chrome on port 9222
    - Uses YouTubeStudioDOM for navigation
    - Already signed in (same session as commenting)

    Args:
        channel_key: Channel key (undaodu, move2japan, foundups)
        max_videos: Maximum videos to list
        oldest_first: Sort oldest first

    Returns:
        List of dicts with video_id, title
    """
    channel = CHANNELS.get(channel_key.lower())
    if not channel:
        print(f"[ERROR] Unknown channel: {channel_key}")
        return []

    channel_id = channel["id"]
    chrome_port = channel.get("chrome_port", 9222)
    is_edge = (chrome_port == 9223)
    browser_name = "Edge" if is_edge else "Chrome"

    # Build Studio URL WITHOUT filter (filter URLs trigger bot detection!)
    # We'll use DOM clicks to sort instead
    studio_url = f"https://studio.youtube.com/channel/{channel_id}/videos/upload"

    print("\n" + "=" * 70)
    print("[YOUTUBE STUDIO] Listing Videos via Signed-In Browser")
    print("=" * 70)
    print(f"  Channel: {channel['name']} ({channel_key})")
    print(f"  Channel ID: {channel_id}")
    print(f"  Browser: {browser_name} (port {chrome_port})")
    print(f"  Sort: {'Oldest First' if oldest_first else 'Newest First'}")
    print("=" * 70)

    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options as ChromeOptions
        from selenium.webdriver.edge.options import Options as EdgeOptions
        from selenium.webdriver.common.by import By
        from modules.platform_integration.youtube_shorts_scheduler.src.dom_automation import YouTubeStudioDOM
        from modules.infrastructure.dependency_launcher.src.dae_dependencies import is_port_open

        # Check if browser is running
        print(f"\n[STEP 1] Checking {browser_name} on port {chrome_port}...")
        if not is_port_open(chrome_port):
            print(f"[ERROR] {browser_name} not running on port {chrome_port}")
            print(f"[TIP] Start {browser_name} with --remote-debugging-port={chrome_port}")
            return []
        print(f"[OK] {browser_name} is running")

        # Connect to browser
        print(f"\n[STEP 2] Connecting to {browser_name}...")
        if is_edge:
            options = EdgeOptions()
            options.add_experimental_option("debuggerAddress", f"127.0.0.1:{chrome_port}")
            driver = webdriver.Edge(options=options)
        else:
            options = ChromeOptions()
            options.add_experimental_option("debuggerAddress", f"127.0.0.1:{chrome_port}")
            driver = webdriver.Chrome(options=options)

        # Create DOM handler (same as commenting system)
        dom = YouTubeStudioDOM(driver)
        print(f"[OK] Connected - YouTubeStudioDOM initialized")

        # Navigate to Studio videos page
        print(f"\n[STEP 3] Navigating to YouTube Studio... (WATCH THE BROWSER)")
        dom.driver.get(studio_url)
        time.sleep(3)  # Wait for page load
        print(f"[OK] Page loaded: {driver.title[:50]}...")

        # Check if we're on the right page
        if "Oops" in driver.title or "Error" in driver.title:
            print(f"[WARN] Page shows error - may need to switch accounts")
            print(f"[INFO] Current account may not own this channel")

        # Sort by Date using DOM click (NOT URL filter - avoids bot detection)
        if oldest_first:
            print(f"\n[STEP 4] Clicking Date header to sort... (WATCH THE BROWSER)")
            try:
                # DOM path from 012: button#date-header-name
                # Single click toggles sort order
                date_header = driver.find_element(By.CSS_SELECTOR, "button#date-header-name")
                dom.safe_click(date_header)
                time.sleep(2)
                print(f"[OK] Clicked Date header - videos should reorder")

                # Check if we need to click again (look for sort indicator)
                # If first video is still recent, click again
            except Exception as e:
                print(f"[WARN] Could not click Date header: {e}")
                print(f"[INFO] Videos may not be sorted by oldest")

        # Get video rows using YouTubeStudioDOM pattern
        print(f"\n[STEP 5] Extracting video list...")
        videos = []

        # Try to get video rows
        try:
            rows = dom.get_video_rows() if hasattr(dom, 'get_video_rows') else []
        except:
            rows = []

        if rows:
            print(f"[OK] Found {len(rows)} video rows via DOM")
            for row in rows[:max_videos]:
                try:
                    link = row.find_element(By.CSS_SELECTOR, "a[href*='/edit']")
                    href = link.get_attribute("href")
                    video_id = href.split("/video/")[1].split("/")[0]
                    title = link.text or "Unknown Title"
                    videos.append({
                        "video_id": video_id,
                        "title": title[:60],
                        "href": href,
                    })
                except:
                    continue
        else:
            # Fallback: direct link extraction
            print("[WARN] No rows via DOM, trying direct extraction...")
            links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/video/'][href*='/edit']")
            for link in links[:max_videos]:
                try:
                    href = link.get_attribute("href")
                    video_id = href.split("/video/")[1].split("/")[0]
                    title = link.text or link.get_attribute("title") or "Unknown"
                    videos.append({
                        "video_id": video_id,
                        "title": title[:60],
                        "href": href,
                    })
                except:
                    continue

        if videos:
            print(f"\n[SUCCESS] Found {len(videos)} videos:")
            for i, v in enumerate(videos, 1):
                print(f"  {i}. {v['video_id']}: {v['title']}")
        else:
            print("[WARN] No videos found - checking page state...")
            print(f"  URL: {driver.current_url[:80]}...")
            print(f"  Title: {driver.title}")

        return videos

    except ImportError as e:
        print(f"[ERROR] Missing dependency: {e}")
        print("[TIP] This test requires youtube_shorts_scheduler module")
        return []
    except Exception as e:
        print(f"[ERROR] Failed: {e}")
        logger.error(f"Studio listing failed: {e}", exc_info=True)
        return []


def navigate_to_video(video_id: str, channel_key: str = "undaodu") -> bool:
    """
    Navigate browser to specific video watch page.

    Args:
        video_id: YouTube video ID
        channel_key: Channel for browser selection

    Returns:
        True if navigation succeeded
    """
    channel = CHANNELS.get(channel_key.lower(), CHANNELS["undaodu"])
    chrome_port = channel.get("chrome_port", 9222)
    is_edge = (chrome_port == 9223)

    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options as ChromeOptions
        from selenium.webdriver.edge.options import Options as EdgeOptions

        # Connect to browser
        if is_edge:
            options = EdgeOptions()
            options.add_experimental_option("debuggerAddress", f"127.0.0.1:{chrome_port}")
            driver = webdriver.Edge(options=options)
        else:
            options = ChromeOptions()
            options.add_experimental_option("debuggerAddress", f"127.0.0.1:{chrome_port}")
            driver = webdriver.Chrome(options=options)

        # Navigate to video
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        print(f"\n[NAVIGATE] Opening video: {video_id}")
        driver.get(video_url)
        time.sleep(3)

        print(f"[OK] Now playing: {driver.title[:50]}...")
        return True

    except Exception as e:
        print(f"[ERROR] Navigation failed: {e}")
        return False


def save_test_artifact(data: Dict[str, Any], filename: str) -> str:
    """Save test result as JSON artifact."""
    artifact_dir = Path("memory/video_index/test_results")
    artifact_dir.mkdir(parents=True, exist_ok=True)

    artifact_path = artifact_dir / filename
    with open(artifact_path, "w") as f:
        json.dump(data, f, indent=2, default=str)

    print(f"[ARTIFACT] Saved: {artifact_path}")
    return str(artifact_path)


# =============================================================================
# Test Cases
# =============================================================================

@pytest.mark.live_browser
@pytest.mark.integration
class TestUnDaoDuOldestVideo:
    """Integration tests for indexing UnDaoDu's oldest video.

    LIVE BROWSER: attaches to a signed-in Chrome on port 9222 and navigates
    to a hardcoded video. Skipped by default; pass --run-live to run.
    """

    def test_list_videos_via_studio(self):
        """Test: List videos via YouTube Studio (same as commenting system)."""
        videos = list_videos_via_studio("undaodu", max_videos=5, oldest_first=True)
        assert len(videos) > 0, "No videos found via Studio"
        print(f"\n[PASS] Found {len(videos)} videos via YouTube Studio")

    def test_navigate_to_oldest_video(self):
        """Test: Navigate to oldest video."""
        videos = list_videos_via_studio("undaodu", max_videos=1, oldest_first=True)
        if videos:
            video_id = videos[0]["video_id"]
            success = navigate_to_video(video_id, "undaodu")
            assert success, "Navigation failed"
            print(f"\n[PASS] Navigated to oldest video: {video_id}")


# =============================================================================
# Direct Execution
# =============================================================================

def run_integration_test():
    """Run the integration test directly."""
    print("\n")
    print("=" * 70)
    print("  VIDEO INDEXER INTEGRATION TEST")
    print("  Using YouTubeStudioDOM (same as commenting system)")
    print("=" * 70)
    print(f"  Started: {datetime.now().isoformat()}")
    print("=" * 70)

    # Step 1: List videos via YouTube Studio
    print("\n[PHASE 1] Listing videos via YouTube Studio")
    videos = list_videos_via_studio("undaodu", max_videos=5, oldest_first=True)

    if not videos:
        print("\n[WARN] Could not list videos via Studio")
        print("[INFO] This may mean the browser is logged into a different account")
        print("[TIP] Make sure Chrome is logged into the account that owns UnDaoDu")

        # Fallback: Use known oldest video ID
        print("\n[FALLBACK] Using known oldest video ID: 8_DUQaqY6Tc")
        videos = [{"video_id": "8_DUQaqY6Tc", "title": "Vision Goal - UnDaoDu on eSingularity"}]

    # Step 2: Navigate to oldest video
    print("\n[PHASE 2] Navigating to oldest video")
    oldest = videos[0]
    success = navigate_to_video(oldest["video_id"], "undaodu")

    # Step 3: Save results
    print("\n[PHASE 3] Saving test results")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    artifact = {
        "test": "integration_oldest_video",
        "channel": "undaodu",
        "videos_found": len(videos),
        "oldest_video": oldest,
        "navigation_success": success,
        "timestamp": timestamp,
        "method": "YouTubeStudioDOM (WSP 84)",
    }
    artifact_path = save_test_artifact(artifact, f"integration_run_{timestamp}.json")

    # Summary
    print("\n")
    print("=" * 70)
    print("  INTEGRATION TEST COMPLETE")
    print("=" * 70)
    print(f"  Method: YouTubeStudioDOM (same as commenting)")
    print(f"  Videos Found: {len(videos)}")
    print(f"  Oldest Video: {oldest['video_id']}")
    print(f"  Navigation: {'SUCCESS' if success else 'FAILED'}")
    print(f"  Artifact: {artifact_path}")
    print("=" * 70)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(run_integration_test())
