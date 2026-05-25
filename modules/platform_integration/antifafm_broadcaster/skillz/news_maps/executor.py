"""
News Maps - Consolidated conflict/shipping map rotation with ticker scraping.

Merges GCC shipping tracker + LiveUAMap conflict maps into unified schema.
Uses screenshot capture to avoid WAF blocking (5 min refresh cycle).

Sources:
- iran.liveuamap.com - Iran/Israel conflict map
- israelpalestine.liveuamap.com - Gaza/West Bank map
- vesselfinder.com - Strait of Hormuz shipping
- rocketalert.live - Israel rocket alerts

Usage:
    python executor.py --daemon           # Start rotation daemon
    python executor.py --capture iran     # Capture single source
    python executor.py --ticker           # Fetch ticker headlines
    python executor.py --list             # List sources

WSP 27: Universal DAE Architecture
"""

import argparse
import asyncio
import json
import logging
import os
import random
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from modules.platform_integration.antifafm_broadcaster.src.obs_logging_guard import (
    create_obs_req_client,
)

logger = logging.getLogger(__name__)

# Cache directories
CACHE_DIR = Path(__file__).parent / "cache"
SCREENSHOT_DIR = CACHE_DIR / "screenshots"
TICKER_DIR = CACHE_DIR / "ticker"
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
TICKER_DIR.mkdir(parents=True, exist_ok=True)

# Refresh intervals (anti-blocking)
SCREENSHOT_INTERVAL_SEC = 300  # 5 minutes
TICKER_INTERVAL_SEC = 300  # 5 minutes
VIEW_ROTATION_SEC = 60  # 1 minute per view in OBS

# News map sources
NEWS_SOURCES = {
    "iran": {
        "name": "Iran Conflict Map",
        "url": "https://iran.liveuamap.com/",
        "type": "map",
        "ticker_selectors": [".event_title", ".event-description", "h3"],
        "wait_seconds": 10,
    },
    "palestine": {
        "name": "Israel-Palestine Map",
        "url": "https://israelpalestine.liveuamap.com/",
        "type": "map",
        "ticker_selectors": [".event_title", ".event-description", "h3"],
        "wait_seconds": 10,
    },
    "hormuz": {
        "name": "Strait of Hormuz Shipping",
        "url": "https://www.vesselfinder.com/map#11/26.4/56.3/type=8",
        "type": "shipping",
        "ticker_selectors": None,  # No ticker from shipping maps
        "wait_seconds": 8,
    },
    "gulf": {
        "name": "Persian Gulf Shipping",
        "url": "https://www.vesselfinder.com/map#7/26.0/51.5/type=8",
        "type": "shipping",
        "ticker_selectors": None,
        "wait_seconds": 8,
    },
    "rockets": {
        "name": "Israel Rocket Alerts",
        "url": "https://rocketalert.live/",
        "type": "alerts",
        "ticker_selectors": [".alert-text", ".location", ".alert-info"],
        "wait_seconds": 5,
    },
}

# Rotation order for news schema
NEWS_ROTATION = ["iran", "palestine", "hormuz", "gulf", "rockets"]


def get_driver():
    """Get headless Chrome driver with anti-detection."""
    try:
        import undetected_chromedriver as uc
        options = uc.ChromeOptions()
        options.add_argument("--headless=new")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        driver = uc.Chrome(options=options)
        logger.info("[NEWS-MAPS] Using undetected-chromedriver")
        return driver
    except ImportError:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        driver = webdriver.Chrome(options=options)
        logger.warning("[NEWS-MAPS] Using standard Chrome (install undetected-chromedriver for better anti-detection)")
        return driver


async def capture_screenshot(
    source_id: str,
    force: bool = False,
) -> Optional[Path]:
    """
    Capture screenshot of news source.

    Anti-blocking pattern:
    - Check cache age before fetching
    - Human-like delays
    - Single request per 5 min

    Args:
        source_id: Key from NEWS_SOURCES
        force: Ignore cache and capture anyway

    Returns:
        Path to screenshot file
    """
    source = NEWS_SOURCES.get(source_id)
    if not source:
        logger.error(f"[NEWS-MAPS] Unknown source: {source_id}")
        return None

    # Check cache
    screenshot_path = SCREENSHOT_DIR / f"{source_id}_latest.png"
    if not force and screenshot_path.exists():
        age = datetime.now().timestamp() - screenshot_path.stat().st_mtime
        if age < SCREENSHOT_INTERVAL_SEC:
            logger.debug(f"[NEWS-MAPS] Using cached {source_id} (age: {age:.0f}s)")
            return screenshot_path

    url = source["url"]
    wait_seconds = source.get("wait_seconds", 8)

    logger.info(f"[NEWS-MAPS] Capturing {source_id}: {source['name']}")

    driver = None
    try:
        driver = get_driver()

        # Human-like delay before loading
        await asyncio.sleep(random.uniform(1.0, 3.0))

        driver.get(url)

        # Wait for content to load
        await asyncio.sleep(wait_seconds)

        # Take screenshot
        driver.save_screenshot(str(screenshot_path))
        logger.info(f"[NEWS-MAPS] Saved: {screenshot_path.name}")

        return screenshot_path

    except Exception as e:
        logger.error(f"[NEWS-MAPS] Screenshot failed for {source_id}: {e}")
        return None
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass


async def scrape_ticker_events(
    source_id: str,
    force: bool = False,
    max_events: int = 20,
) -> List[Dict[str, Any]]:
    """
    Scrape headline events from news map for ticker display.

    Anti-blocking pattern:
    - Cache results for 5 min
    - Single DOM parse per request
    - Human-like delays

    Args:
        source_id: Key from NEWS_SOURCES
        force: Ignore cache
        max_events: Max events to extract

    Returns:
        List of event dicts with text and timestamp
    """
    source = NEWS_SOURCES.get(source_id)
    if not source:
        return []

    selectors = source.get("ticker_selectors")
    if not selectors:
        return []  # Source doesn't support ticker

    # Check cache
    ticker_path = TICKER_DIR / f"{source_id}_events.json"
    if not force and ticker_path.exists():
        age = datetime.now().timestamp() - ticker_path.stat().st_mtime
        if age < TICKER_INTERVAL_SEC:
            try:
                with open(ticker_path) as f:
                    return json.load(f)
            except Exception:
                pass

    url = source["url"]
    wait_seconds = source.get("wait_seconds", 8)

    logger.info(f"[NEWS-MAPS] Scraping ticker from {source_id}")

    driver = None
    events = []

    try:
        driver = get_driver()

        # Human-like delay
        await asyncio.sleep(random.uniform(2.0, 4.0))

        driver.get(url)
        await asyncio.sleep(wait_seconds)

        # Extract text from selectors
        seen_texts = set()
        for selector in selectors:
            try:
                from selenium.webdriver.common.by import By
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for el in elements[:max_events]:
                    text = el.text.strip()
                    if text and len(text) > 10 and text not in seen_texts:
                        seen_texts.add(text)
                        events.append({
                            "text": text,
                            "source": source_id,
                            "source_name": source["name"],
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        })
                        if len(events) >= max_events:
                            break
            except Exception as e:
                logger.debug(f"[NEWS-MAPS] Selector {selector} failed: {e}")

        # Cache results
        if events:
            with open(ticker_path, "w") as f:
                json.dump(events, f, indent=2)
            logger.info(f"[NEWS-MAPS] Cached {len(events)} events from {source_id}")

        return events

    except Exception as e:
        logger.error(f"[NEWS-MAPS] Ticker scrape failed for {source_id}: {e}")
        return []
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass


async def get_all_ticker_events(force: bool = False) -> List[Dict[str, Any]]:
    """Get ticker events from all sources that support it."""
    all_events = []
    for source_id, source in NEWS_SOURCES.items():
        if source.get("ticker_selectors"):
            events = await scrape_ticker_events(source_id, force=force)
            all_events.extend(events)

    # Sort by timestamp (newest first)
    all_events.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return all_events


async def update_obs_image_source(source_name: str, image_path: Path) -> Dict[str, Any]:
    """Update OBS image source with new screenshot."""
    try:
        import obsws_python as obs

        host = os.getenv("OBS_WEBSOCKET_HOST", "localhost")
        port = int(os.getenv("OBS_WEBSOCKET_PORT", 4455))
        password = os.getenv("OBS_WEBSOCKET_PASSWORD", "")

        client = create_obs_req_client(obs, host=host, port=port, password=password)
        client.set_input_settings(
            name=source_name,
            settings={"file": str(image_path.absolute())},
            overlay=True
        )

        return {"success": True, "source": source_name, "image": str(image_path)}
    except Exception as e:
        logger.error(f"[NEWS-MAPS] OBS update failed: {e}")
        return {"success": False, "error": str(e)}


async def rotation_daemon(
    obs_source: str = "News Map",
    ticker_source: str = "Scrolling Ticker",
):
    """
    Main rotation daemon for news maps.

    - Captures screenshots every 5 min
    - Rotates display every 1 min
    - Updates ticker text periodically
    """
    logger.info("[NEWS-MAPS] Starting news maps rotation daemon")
    logger.info(f"[NEWS-MAPS] Sources: {' -> '.join(NEWS_ROTATION)}")

    rotation_index = 0
    last_capture = {}
    last_ticker_update = 0

    while True:
        try:
            current_source = NEWS_ROTATION[rotation_index]

            # Capture screenshot if needed
            now = datetime.now().timestamp()
            last = last_capture.get(current_source, 0)
            if now - last >= SCREENSHOT_INTERVAL_SEC:
                screenshot = await capture_screenshot(current_source)
                if screenshot:
                    last_capture[current_source] = now
                    # Update OBS
                    await update_obs_image_source(obs_source, screenshot)
            else:
                # Just update OBS with cached image
                cached = SCREENSHOT_DIR / f"{current_source}_latest.png"
                if cached.exists():
                    await update_obs_image_source(obs_source, cached)

            # Update ticker periodically
            if now - last_ticker_update >= TICKER_INTERVAL_SEC:
                events = await get_all_ticker_events()
                if events:
                    # Format for OBS text source
                    ticker_text = " • ".join([e["text"][:100] for e in events[:10]])
                    # Could update OBS text source here
                    logger.info(f"[NEWS-MAPS] Ticker updated: {len(events)} events")
                last_ticker_update = now

            logger.info(f"[NEWS-MAPS] Displaying: {current_source} ({NEWS_SOURCES[current_source]['name']})")

            # Wait for rotation interval
            await asyncio.sleep(VIEW_ROTATION_SEC)

            # Next source
            rotation_index = (rotation_index + 1) % len(NEWS_ROTATION)

        except asyncio.CancelledError:
            logger.info("[NEWS-MAPS] Rotation daemon stopped")
            break
        except Exception as e:
            logger.error(f"[NEWS-MAPS] Rotation error: {e}")
            await asyncio.sleep(10)


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="News Maps - Conflict/shipping map rotation")
    parser.add_argument("--daemon", action="store_true", help="Start rotation daemon")
    parser.add_argument("--capture", type=str, help="Capture single source screenshot")
    parser.add_argument("--ticker", action="store_true", help="Fetch ticker headlines")
    parser.add_argument("--list", action="store_true", help="List available sources")
    parser.add_argument("--force", action="store_true", help="Force refresh (ignore cache)")

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    if args.list:
        print("\n=== News Map Sources ===")
        for sid, source in NEWS_SOURCES.items():
            ticker = "[ticker]" if source.get("ticker_selectors") else ""
            print(f"  {sid}: {source['name']} [{source['type']}] {ticker}")
        print(f"\nRotation: {' -> '.join(NEWS_ROTATION)}")
        return

    if args.capture:
        if args.capture not in NEWS_SOURCES:
            print(f"Unknown source: {args.capture}")
            print(f"Available: {', '.join(NEWS_SOURCES.keys())}")
            return
        result = asyncio.run(capture_screenshot(args.capture, force=args.force))
        print(f"Screenshot: {result}")
        return

    if args.ticker:
        events = asyncio.run(get_all_ticker_events(force=args.force))
        print(f"\n=== Ticker Events ({len(events)}) ===")
        for e in events[:15]:
            print(f"[{e['source']}] {e['text'][:80]}")
        return

    if args.daemon:
        print("[NEWS-MAPS] Starting rotation daemon...")
        print("[NEWS-MAPS] Press Ctrl+C to stop")
        asyncio.run(rotation_daemon())
        return

    parser.print_help()


if __name__ == "__main__":
    main()
