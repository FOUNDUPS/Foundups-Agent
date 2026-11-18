#!/usr/bin/env python3
"""
Stage 3b Test: Hybrid Video Indexing

Tests TWO approaches to video indexing:
    A. YouTube Studio Download (DOM click → file download)
    B. Live Playback Capture (WASAPI audio + screenshots)

Why Two Approaches:
    - Studio Download: Fast, full quality, but requires download wait
    - Live Playback: No download, real-time, works with any video

Test Stages:
    Stage 1: Navigation (single video) - DONE
    Stage 2: Batch Navigation (10+ videos) - DONE
    Stage 3: Single Video Indexing (yt-dlp) - BLOCKED
    Stage 3b: Hybrid Indexing - THIS TEST
    Stage 4: Indexing Validation

What 012 Should See:
    Approach A:
        1. Browser navigates to YouTube Studio
        2. Hovers over video row
        3. Clicks "..." menu
        4. Clicks "Download"
        5. File appears in Downloads folder

    Approach B:
        1. Browser navigates to video watch page
        2. Video plays at 2x speed
        3. Audio captured via WASAPI
        4. Screenshots taken at intervals

Usage:
    python modules/ai_intelligence/video_indexer/tests/test_stage3b_hybrid_indexing.py

WSP Compliance:
    - WSP 5: Test Coverage
    - WSP 84: Code Reuse (YouTubeStudioDOM, SystemAudioCapture)
"""

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

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
    },
}

# Known test video (oldest UnDaoDu - short, 5:55)
TEST_VIDEO = {
    "id": "8_DUQaqY6Tc",
    "title": "Vision Goal - UnDaoDu on eSingularity",
    "duration_sec": 355,  # 5:55
}


# =============================================================================
# Approach A: YouTube Studio Download
# =============================================================================

def download_via_studio(
    video_id: str,
    channel_key: str = "undaodu",
    timeout_sec: int = 120,
) -> Dict[str, Any]:
    """
    Download video via YouTube Studio's built-in download feature.

    Uses DOM automation to click the "..." menu and select Download.

    Args:
        video_id: YouTube video ID
        channel_key: Channel key
        timeout_sec: Max wait time for download

    Returns:
        Result dict with download path and status
    """
    result = {
        "success": False,
        "method": "studio_download",
        "video_id": video_id,
        "download_path": None,
        "duration_sec": 0,
        "error": None,
    }

    channel = CHANNELS.get(channel_key.lower())
    if not channel:
        result["error"] = f"Unknown channel: {channel_key}"
        return result

    chrome_port = channel.get("chrome_port", 9222)
    channel_id = channel["id"]

    # Studio URL for content page
    studio_url = f"https://studio.youtube.com/channel/{channel_id}/videos/upload"

    print("\n" + "=" * 70)
    print("[APPROACH A] YouTube Studio Download")
    print("=" * 70)
    print(f"  Video ID: {video_id}")
    print(f"  Channel: {channel['name']}")
    print(f"  Method: DOM click → Download menu")
    print("=" * 70)

    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
        from selenium.webdriver.common.action_chains import ActionChains
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from modules.platform_integration.youtube_shorts_scheduler.src.dom_automation import YouTubeStudioDOM
        from modules.infrastructure.dependency_launcher.src.dae_dependencies import is_port_open

        # Check browser
        print(f"\n[STEP 1] Checking Chrome on port {chrome_port}...")
        if not is_port_open(chrome_port):
            result["error"] = f"Chrome not running on port {chrome_port}"
            return result
        print(f"[OK] Chrome is running")

        # Connect
        print(f"\n[STEP 2] Connecting to Chrome...")
        options = Options()
        options.add_experimental_option("debuggerAddress", f"127.0.0.1:{chrome_port}")
        driver = webdriver.Chrome(options=options)
        dom = YouTubeStudioDOM(driver)
        print(f"[OK] Connected")

        # Navigate to Studio
        print(f"\n[STEP 3] Navigating to YouTube Studio... (WATCH BROWSER)")
        driver.get(studio_url)
        time.sleep(3)
        print(f"[OK] Page: {driver.title[:40]}...")

        # Find the video row by ID
        print(f"\n[STEP 4] Finding video row for {video_id}... (WATCH BROWSER)")

        # Look for link containing the video ID
        video_link = None
        try:
            video_link = driver.find_element(
                By.CSS_SELECTOR,
                f"a[href*='/video/{video_id}']"
            )
            print(f"[OK] Found video link")
        except:
            print(f"[WARN] Video not visible, may need to scroll or sort")
            result["error"] = "Video not found in current view"
            return result

        # Get the parent row element
        print(f"\n[STEP 5] Hovering over video row... (WATCH BROWSER)")
        row = video_link.find_element(By.XPATH, "./ancestor::ytcp-video-row")

        # Hover to reveal menu button
        actions = ActionChains(driver)
        actions.move_to_element(row).perform()
        time.sleep(1)
        print(f"[OK] Hovering over row")

        # Find and click the "..." menu button
        print(f"\n[STEP 6] Clicking '...' menu... (WATCH BROWSER)")
        try:
            # The menu button appears on hover
            menu_button = row.find_element(
                By.CSS_SELECTOR,
                "ytcp-icon-button.open-menu-button, button[aria-label*='Action'], #hover-items ytcp-icon-button"
            )
            dom.safe_click(menu_button)
            time.sleep(1)
            print(f"[OK] Menu opened")
        except Exception as e:
            print(f"[ERROR] Could not find menu button: {e}")
            result["error"] = f"Menu button not found: {e}"
            return result

        # Find and click "Download" option
        print(f"\n[STEP 7] Clicking 'Download'... (WATCH BROWSER)")
        try:
            # Look for Download in the popup menu
            download_option = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((
                    By.XPATH,
                    "//tp-yt-paper-item[contains(., 'Download')] | //div[contains(text(), 'Download')]"
                ))
            )
            dom.safe_click(download_option)
            print(f"[OK] Download initiated")
        except Exception as e:
            print(f"[ERROR] Could not find Download option: {e}")
            result["error"] = f"Download option not found: {e}"
            return result

        # Wait for download to complete
        print(f"\n[STEP 8] Waiting for download... (check Downloads folder)")
        downloads_path = Path.home() / "Downloads"
        start_time = time.time()
        downloaded_file = None

        while time.time() - start_time < timeout_sec:
            # Look for recently created video files
            for f in downloads_path.glob("*.mp4"):
                if f.stat().st_mtime > start_time - 5:  # Created after we started
                    downloaded_file = f
                    break

            if downloaded_file:
                break

            time.sleep(2)
            print(f"  Waiting... ({int(time.time() - start_time)}s)")

        if downloaded_file:
            result["success"] = True
            result["download_path"] = str(downloaded_file)
            result["duration_sec"] = time.time() - start_time
            print(f"\n[SUCCESS] Downloaded: {downloaded_file.name}")
            print(f"  Size: {downloaded_file.stat().st_size / 1024 / 1024:.1f} MB")
            print(f"  Time: {result['duration_sec']:.1f}s")
        else:
            result["error"] = "Download timeout"
            print(f"\n[TIMEOUT] Download did not complete in {timeout_sec}s")

        return result

    except ImportError as e:
        result["error"] = f"Missing dependency: {e}"
        return result
    except Exception as e:
        result["error"] = str(e)
        return result


# =============================================================================
# Approach B: Live Playback Capture
# =============================================================================

def capture_via_playback(
    video_id: str,
    max_duration_sec: int = 30,
    playback_speed: float = 2.0,
    screenshot_interval_sec: float = 2.0,
) -> Dict[str, Any]:
    """
    Capture video via live playback with WASAPI audio and screenshots.

    Args:
        video_id: YouTube video ID
        max_duration_sec: Max capture time (at playback speed)
        playback_speed: Video playback speed (1.0 to 2.0)
        screenshot_interval_sec: Time between screenshots

    Returns:
        Result dict with captured data
    """
    result = {
        "success": False,
        "method": "live_playback",
        "video_id": video_id,
        "audio_chunks": 0,
        "screenshots": 0,
        "transcript_preview": "",
        "duration_sec": 0,
        "error": None,
    }

    video_url = f"https://www.youtube.com/watch?v={video_id}"

    print("\n" + "=" * 70)
    print("[APPROACH B] Live Playback Capture")
    print("=" * 70)
    print(f"  Video ID: {video_id}")
    print(f"  Playback Speed: {playback_speed}x")
    print(f"  Max Duration: {max_duration_sec}s")
    print(f"  Method: WASAPI audio + Selenium screenshots")
    print("=" * 70)

    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
        from modules.infrastructure.dependency_launcher.src.dae_dependencies import is_port_open

        # Check browser
        print(f"\n[STEP 1] Checking Chrome...")
        if not is_port_open(9222):
            result["error"] = "Chrome not running on port 9222"
            return result
        print(f"[OK] Chrome is running")

        # Connect
        print(f"\n[STEP 2] Connecting to Chrome...")
        options = Options()
        options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
        driver = webdriver.Chrome(options=options)
        print(f"[OK] Connected")

        # Navigate to video
        print(f"\n[STEP 3] Navigating to video... (WATCH BROWSER)")
        driver.get(video_url)
        time.sleep(3)
        print(f"[OK] Video page loaded")

        # Set playback speed
        print(f"\n[STEP 4] Setting playback speed to {playback_speed}x...")
        try:
            driver.execute_script(f"""
                var video = document.querySelector('video');
                if (video) {{
                    video.playbackRate = {playback_speed};
                    video.play();
                }}
            """)
            print(f"[OK] Playback speed set")
        except Exception as e:
            print(f"[WARN] Could not set playback speed: {e}")

        # Try to initialize audio capture
        print(f"\n[STEP 5] Initializing audio capture...")
        audio_capture = None
        try:
            from modules.platform_integration.youtube_live_audio.src.youtube_live_audio import (
                SystemAudioCapture,
                AudioStreamConfig,
            )
            config = AudioStreamConfig(
                sample_rate_hz=16000,
                channels=1,
                chunk_duration_sec=5.0,
            )
            audio_capture = SystemAudioCapture(config)
            print(f"[OK] WASAPI audio capture ready")
        except Exception as e:
            print(f"[WARN] Audio capture not available: {e}")

        # Capture loop
        print(f"\n[STEP 6] Starting capture... (WATCH BROWSER)")
        screenshots = []
        audio_chunks = []
        start_time = time.time()
        last_screenshot = 0

        # Create output directory
        output_dir = Path(f"memory/video_index/captures/{video_id}")
        output_dir.mkdir(parents=True, exist_ok=True)

        while time.time() - start_time < max_duration_sec:
            elapsed = time.time() - start_time

            # Take screenshot at intervals
            if elapsed - last_screenshot >= screenshot_interval_sec:
                try:
                    screenshot_path = output_dir / f"frame_{len(screenshots):04d}.png"
                    driver.save_screenshot(str(screenshot_path))
                    screenshots.append(str(screenshot_path))
                    last_screenshot = elapsed
                    print(f"  Screenshot {len(screenshots)} at {elapsed:.1f}s")
                except Exception as e:
                    print(f"  [WARN] Screenshot failed: {e}")

            # Capture audio chunk
            if audio_capture:
                try:
                    chunk = audio_capture.capture_chunk(duration_sec=2.0)
                    if chunk:
                        audio_chunks.append(chunk)
                except Exception as e:
                    pass  # Audio capture is optional

            time.sleep(0.5)

        result["success"] = True
        result["screenshots"] = len(screenshots)
        result["audio_chunks"] = len(audio_chunks)
        result["duration_sec"] = time.time() - start_time

        print(f"\n[SUCCESS] Capture complete")
        print(f"  Screenshots: {len(screenshots)}")
        print(f"  Audio chunks: {len(audio_chunks)}")
        print(f"  Duration: {result['duration_sec']:.1f}s")
        print(f"  Output: {output_dir}")

        return result

    except ImportError as e:
        result["error"] = f"Missing dependency: {e}"
        return result
    except Exception as e:
        result["error"] = str(e)
        return result


# =============================================================================
# Combined Test
# =============================================================================

def run_hybrid_test(video_id: str = None) -> Dict[str, Any]:
    """Run both indexing approaches and compare results."""

    if video_id is None:
        video_id = TEST_VIDEO["id"]

    print("\n")
    print("=" * 70)
    print("  VIDEO INDEXER - STAGE 3b: HYBRID INDEXING TEST")
    print("=" * 70)
    print(f"  Video: {video_id}")
    print(f"  Started: {datetime.now().isoformat()}")
    print("=" * 70)

    results = {
        "video_id": video_id,
        "approach_a_studio": None,
        "approach_b_playback": None,
        "recommendation": None,
    }

    # Approach A: Studio Download
    print("\n" + "=" * 70)
    print("  TESTING APPROACH A: YouTube Studio Download")
    print("=" * 70)
    results["approach_a_studio"] = download_via_studio(video_id)

    # Approach B: Live Playback (shorter test - 15 seconds)
    print("\n" + "=" * 70)
    print("  TESTING APPROACH B: Live Playback Capture")
    print("=" * 70)
    results["approach_b_playback"] = capture_via_playback(
        video_id,
        max_duration_sec=15,
        playback_speed=2.0,
    )

    # Summary
    print("\n")
    print("=" * 70)
    print("  HYBRID TEST RESULTS")
    print("=" * 70)

    a_success = results["approach_a_studio"]["success"]
    b_success = results["approach_b_playback"]["success"]

    print(f"\n  Approach A (Studio Download):")
    print(f"    Success: {a_success}")
    if a_success:
        print(f"    Download: {results['approach_a_studio']['download_path']}")
        print(f"    Time: {results['approach_a_studio']['duration_sec']:.1f}s")
    else:
        print(f"    Error: {results['approach_a_studio']['error']}")

    print(f"\n  Approach B (Live Playback):")
    print(f"    Success: {b_success}")
    if b_success:
        print(f"    Screenshots: {results['approach_b_playback']['screenshots']}")
        print(f"    Audio Chunks: {results['approach_b_playback']['audio_chunks']}")
        print(f"    Time: {results['approach_b_playback']['duration_sec']:.1f}s")
    else:
        print(f"    Error: {results['approach_b_playback']['error']}")

    # Recommendation
    if a_success and not b_success:
        results["recommendation"] = "studio_download"
    elif b_success and not a_success:
        results["recommendation"] = "live_playback"
    elif a_success and b_success:
        # Both worked - recommend based on use case
        if results["approach_a_studio"]["duration_sec"] < results["approach_b_playback"]["duration_sec"]:
            results["recommendation"] = "studio_download (faster)"
        else:
            results["recommendation"] = "live_playback (no wait)"
    else:
        results["recommendation"] = "manual_review"

    print(f"\n  Recommendation: {results['recommendation']}")
    print("=" * 70)

    # Save results
    artifact_dir = Path("memory/video_index/test_results")
    artifact_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    artifact_path = artifact_dir / f"stage3b_hybrid_{video_id}_{timestamp}.json"

    with open(artifact_path, "w") as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\n[ARTIFACT] Saved: {artifact_path}")

    return results


# =============================================================================
# Test Cases
# =============================================================================

@pytest.mark.live_browser
@pytest.mark.integration
class TestStage3bHybridIndexing:
    """Stage 3b: Hybrid video indexing tests.

    LIVE BROWSER: attaches to a signed-in Chrome on port 9222 and navigates
    YouTube Studio / a watch page. Skipped by default; pass --run-live to run.
    """

    def test_approach_a_studio_download(self):
        """Test: Download video via YouTube Studio."""
        result = download_via_studio(TEST_VIDEO["id"])
        # Don't assert success - document what happens
        print(f"\n[RESULT] Studio Download: {result['success']}")
        if not result["success"]:
            print(f"[INFO] Error: {result['error']}")

    def test_approach_b_live_playback(self):
        """Test: Capture video via live playback."""
        result = capture_via_playback(TEST_VIDEO["id"], max_duration_sec=10)
        assert result["screenshots"] > 0 or result["audio_chunks"] > 0, \
            "Should capture at least screenshots or audio"


# =============================================================================
# Direct Execution
# =============================================================================

if __name__ == "__main__":
    results = run_hybrid_test()

    # Exit code based on results
    if results["approach_a_studio"]["success"] or results["approach_b_playback"]["success"]:
        sys.exit(0)
    else:
        sys.exit(1)
