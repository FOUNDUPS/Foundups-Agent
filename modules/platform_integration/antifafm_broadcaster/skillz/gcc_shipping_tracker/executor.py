"""
GCC Shipping Tracker - Real-time Strait of Hormuz vessel tracking

Provides real-time shipping data for the Gulf Cooperation Council region,
with focus on the Strait of Hormuz - critical oil transit chokepoint.

BOOT LAYER: Default visual for antifaFM stream with 10-minute rotation.
Runs until stakeholder (moderator) or delegate (managing moderator) intervenes.

Usage:
    python executor.py --daemon              # Boot mode: 10-min rotation
    python executor.py --map                 # Open live map
    python executor.py --tankers             # Filter tankers
    python executor.py --alerts              # Show alerts

WSP 27: Universal DAE Architecture
WSP 103: CLI Interface Standard
"""

import argparse
import asyncio
import json
import logging
import os
import signal
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

# Screenshot cache directory (012 behavior - fetch once, display cached)
SCREENSHOT_CACHE_DIR = Path(__file__).parent / "screenshot_cache"
SCREENSHOT_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# View rotation interval (2 minutes per view)
VIEW_INTERVAL_SEC = 120

# Schema duration before switching to next schema (10 minutes)
SCHEMA_DURATION_SEC = 600

# Stakeholder/Delegate override signal file
OVERRIDE_SIGNAL_FILE = Path(__file__).parent / "stakeholder_override.signal"

# Coming Soon fallback HTML (data:uri for OBS browser source)
COMING_SOON_HTML = """
<!DOCTYPE html>
<html>
<head>
<style>
body {
    margin: 0;
    height: 100vh;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    font-family: 'Segoe UI', Arial, sans-serif;
    color: white;
    text-align: center;
}
.title {
    font-size: 4em;
    font-weight: bold;
    text-shadow: 0 0 20px rgba(255,100,100,0.5);
    margin-bottom: 20px;
}
.subtitle {
    font-size: 2.5em;
    color: #ff6b6b;
    animation: pulse 2s infinite;
}
.signature {
    font-size: 3em;
    margin-top: 40px;
}
@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
}
.region {
    font-size: 1.5em;
    color: #4ecdc4;
    margin-top: 20px;
}
</style>
</head>
<body>
<div class="title">GCC Shipping Tracker</div>
<div class="subtitle">Coming Soon</div>
<div class="region">Strait of Hormuz | Persian Gulf</div>
<div class="signature">0102🦞</div>
</body>
</html>
"""

# Encode as data URI for OBS browser source
import base64
COMING_SOON_DATA_URI = "data:text/html;base64," + base64.b64encode(COMING_SOON_HTML.encode()).decode()

# Shipping tracker URLs for GCC region
# NOTE: VesselFinder preferred - no cookie consent popup, cleaner embed
# MarineTraffic has cookie consent dialog that blocks the view

# VesselFinder URLs (PREFERRED - no cookie popup)
# type=8 = Tankers only (critical for oil transit monitoring)
VESSELFINDER_HORMUZ = "https://www.vesselfinder.com/map#11/26.4/56.3/type=8"
VESSELFINDER_GULF = "https://www.vesselfinder.com/map#7/26.0/51.5/type=8"
VESSELFINDER_TANKERS = "https://www.vesselfinder.com/map#8/26.5/55.0/type=8"

# MarineTraffic URLs (BACKUP - has cookie popup issues)
MARINETRAFFIC_HORMUZ = "https://www.marinetraffic.com/en/ais/home/centerx/56.3/centery/26.5/zoom/8"
MARINETRAFFIC_GULF = "https://www.marinetraffic.com/en/ais/home/centerx/51.5/centery/26.0/zoom/6"


# Hormuz region bounding box (approximate)
HORMUZ_BOUNDS = {
    "lat_min": 25.5,
    "lat_max": 27.5,
    "lon_min": 55.0,
    "lon_max": 57.5,
}


async def fetch_marine_traffic_data() -> Dict[str, Any]:
    """
    Fetch vessel data from MarineTraffic.

    Note: Full API requires subscription. This provides summary view.
    """
    try:
        import aiohttp

        # MarineTraffic requires API key for programmatic access
        # This is a placeholder for the data structure
        return {
            "source": "marinetraffic",
            "status": "api_key_required",
            "fallback": MARINETRAFFIC_HORMUZ,
            "message": "Open map URL for live view"
        }
    except ImportError:
        return {"error": "aiohttp not installed", "fallback": MARINETRAFFIC_HORMUZ}


async def fetch_ais_summary() -> Dict[str, Any]:
    """
    Fetch AIS (Automatic Identification System) summary for Hormuz region.

    Returns approximate vessel counts by type.
    """
    # Real implementation would query AIS data providers
    # This provides the data structure for integration
    return {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "region": "strait_of_hormuz",
        "bounds": HORMUZ_BOUNDS,
        "status": "live_map_available",
        "map_urls": {
            "vesselfinder_hormuz": VESSELFINDER_HORMUZ,
            "vesselfinder_gulf": VESSELFINDER_GULF,
            "vesselfinder_tankers": VESSELFINDER_TANKERS,
        },
        "note": "VesselFinder type=8 filters for tankers only (oil transit)"
    }


def open_live_map(source: str = "vesselfinder") -> Dict[str, Any]:
    """Open live shipping map in default browser."""
    urls = {
        "vesselfinder": VESSELFINDER_HORMUZ,
        "gulf": VESSELFINDER_GULF,
        "tankers": VESSELFINDER_TANKERS,
        "marinetraffic": MARINETRAFFIC_HORMUZ,  # backup
    }

    url = urls.get(source, VESSELFINDER_HORMUZ)
    webbrowser.open(url)

    return {
        "success": True,
        "action": "opened_browser",
        "url": url,
        "source": source
    }


def get_tanker_focus_url() -> str:
    """Get URL filtered for tankers only."""
    # VesselFinder type=8 = Tankers (cleaner, no cookie popup)
    return VESSELFINDER_TANKERS


async def check_alerts() -> List[Dict[str, Any]]:
    """
    Check for shipping alerts in GCC region.

    Alert types:
    - high_traffic: Unusual congestion
    - naval_activity: Military vessels detected
    - blockade_risk: Potential transit disruption
    - incident: Reported maritime incident
    """
    # Placeholder for alert system
    # Would integrate with news feeds, maritime security services
    return [
        {
            "type": "info",
            "message": "Strait of Hormuz: Normal traffic conditions",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    ]


async def execute_skill(
    action: str = "summary",
    open_map: bool = False,
    tankers_only: bool = False,
    show_alerts: bool = False,
) -> Dict[str, Any]:
    """
    Main skill executor for GCC shipping tracker.

    Args:
        action: summary|map|tankers|alerts
        open_map: Open live map in browser
        tankers_only: Filter for oil tankers
        show_alerts: Check for maritime alerts

    Returns:
        Dict with shipping data and status
    """
    result = {
        "skill": "gcc_shipping_tracker",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "region": "gcc_strait_of_hormuz",
    }

    if open_map or action == "map":
        source = "tankers" if tankers_only else "marinetraffic"
        if tankers_only:
            url = get_tanker_focus_url()
            webbrowser.open(url)
            result["map"] = {"opened": True, "url": url, "filter": "tankers"}
        else:
            map_result = open_live_map()
            result["map"] = map_result
        return result

    if show_alerts or action == "alerts":
        alerts = await check_alerts()
        result["alerts"] = alerts
        return result

    if tankers_only or action == "tankers":
        result["focus"] = "tankers"
        result["tanker_map_url"] = get_tanker_focus_url()
        result["message"] = "Use --map to open tanker-filtered view"
        return result

    # Default: summary
    summary = await fetch_ais_summary()
    result.update(summary)
    return result


# Trusted domains that block HEAD requests but work in browser context
TRUSTED_DOMAINS = [
    "marinetraffic.com",
    "vesselfinder.com",
    "fleetmon.com",
]


def is_trusted_domain(url: str) -> bool:
    """Check if URL is from a trusted shipping tracker domain."""
    return any(domain in url.lower() for domain in TRUSTED_DOMAINS)


async def capture_map_screenshot(
    url: str,
    view_name: str = "map",
    wait_seconds: int = 8,
    width: int = 1920,
    height: int = 1080,
) -> Optional[Path]:
    """
    Capture screenshot of shipping map using headless browser.

    012 BEHAVIOR PATTERN:
    - Single request to fetch map (not continuous iframe refresh)
    - Cache screenshot locally
    - OBS displays cached image (no repeated requests to site)
    - Reduces Cloudflare/WAF detection probability

    Args:
        url: Map URL to screenshot
        view_name: Name for cached file
        wait_seconds: Time to wait for map tiles to load
        width: Screenshot width
        height: Screenshot height

    Returns:
        Path to screenshot file, or None on failure
    """
    screenshot_path = SCREENSHOT_CACHE_DIR / f"{view_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"

    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service

        logger.info(f"[GCC-SCREENSHOT] Capturing {view_name}: {url[:50]}...")

        # Use undetected-chromedriver if available (anti-detection)
        try:
            import undetected_chromedriver as uc
            options = uc.ChromeOptions()
            options.add_argument("--headless=new")
            options.add_argument(f"--window-size={width},{height}")
            options.add_argument("--disable-gpu")
            options.add_argument("--no-sandbox")
            driver = uc.Chrome(options=options)
            logger.info("[GCC-SCREENSHOT] Using undetected-chromedriver")
        except ImportError:
            # Fallback to standard Chrome
            options = Options()
            options.add_argument("--headless=new")
            options.add_argument(f"--window-size={width},{height}")
            options.add_argument("--disable-gpu")
            options.add_argument("--no-sandbox")
            driver = webdriver.Chrome(options=options)
            logger.info("[GCC-SCREENSHOT] Using standard Chrome (consider installing undetected-chromedriver)")

        try:
            # Human-like delay before loading
            import random
            await asyncio.sleep(random.uniform(1.0, 3.0))

            driver.get(url)

            # Wait for map tiles to load (critical for shipping maps)
            await asyncio.sleep(wait_seconds)

            # Take screenshot
            driver.save_screenshot(str(screenshot_path))
            logger.info(f"[GCC-SCREENSHOT] Saved: {screenshot_path.name}")

            # Clean old screenshots (keep last 5)
            await _cleanup_old_screenshots(view_name, keep=5)

            return screenshot_path

        finally:
            driver.quit()

    except ImportError as e:
        logger.warning(f"[GCC-SCREENSHOT] Selenium not available: {e}")
        return None
    except Exception as e:
        logger.error(f"[GCC-SCREENSHOT] Capture failed: {e}")
        return None


async def _cleanup_old_screenshots(view_prefix: str, keep: int = 5):
    """Remove old screenshots, keeping only the most recent N."""
    try:
        screenshots = sorted(
            SCREENSHOT_CACHE_DIR.glob(f"{view_prefix}_*.png"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        for old_screenshot in screenshots[keep:]:
            old_screenshot.unlink()
            logger.debug(f"[GCC-SCREENSHOT] Cleaned: {old_screenshot.name}")
    except Exception as e:
        logger.warning(f"[GCC-SCREENSHOT] Cleanup failed: {e}")


def get_latest_screenshot(view_name: str = "map") -> Optional[Path]:
    """Get most recent screenshot for a view."""
    screenshots = sorted(
        SCREENSHOT_CACHE_DIR.glob(f"{view_name}_*.png"),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )
    return screenshots[0] if screenshots else None


def screenshot_to_data_uri(screenshot_path: Path) -> str:
    """Convert screenshot to data URI for OBS browser source."""
    with open(screenshot_path, "rb") as f:
        import base64
        data = base64.b64encode(f.read()).decode()
    return f"data:image/png;base64,{data}"


async def check_url_reachable(url: str, timeout: float = 10.0) -> bool:
    """Check if a URL is reachable (basic HTTP HEAD check)."""
    # Skip check for trusted shipping domains (they block HEAD but work in browser)
    if is_trusted_domain(url):
        return True

    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.head(url, timeout=aiohttp.ClientTimeout(total=timeout)) as response:
                return response.status < 400
    except ImportError:
        # No aiohttp - assume reachable
        return True
    except Exception:
        return False


async def update_obs_browser_source(url: str, fallback_on_fail: bool = True) -> Dict[str, Any]:
    """
    Update OBS browser source to show GCC shipping map.

    Requires: GCC_Browser source in OBS scene.
    Falls back to "Coming Soon" screen if URL check fails.
    """
    actual_url = url

    # Check if URL is reachable (skip for data URIs)
    if fallback_on_fail and not url.startswith("data:"):
        is_reachable = await check_url_reachable(url)
        if not is_reachable:
            logger.warning(f"[GCC] URL not reachable: {url[:50]}... - showing Coming Soon")
            actual_url = COMING_SOON_DATA_URI

    try:
        import obsws_python as obs

        host = os.getenv("OBS_WEBSOCKET_HOST", "localhost")
        port = int(os.getenv("OBS_WEBSOCKET_PORT", 4455))
        password = os.getenv("OBS_WEBSOCKET_PASSWORD", "")

        client = obs.ReqClient(host=host, port=port, password=password)

        # Browser source name (env var or default to existing)
        source_name = os.getenv("OBS_BROWSER_SOURCE", "antifaFM Website")

        # Update browser source URL
        client.set_input_settings(
            name=source_name,
            settings={"url": actual_url},
            overlay=True
        )

        is_fallback = actual_url == COMING_SOON_DATA_URI
        if is_fallback:
            logger.info("[GCC] Showing 'Coming Soon' fallback screen")
        else:
            logger.info(f"[GCC] Updated OBS browser source: {actual_url[:50]}...")

        return {
            "success": True,
            "source": source_name,
            "url": actual_url,
            "is_fallback": is_fallback
        }

    except ImportError:
        logger.warning("[GCC] obsws-python not installed")
        return {"success": False, "error": "obsws-python not installed"}
    except Exception as e:
        logger.error(f"[GCC] OBS update failed: {e}")
        return {"success": False, "error": str(e)}


async def show_coming_soon() -> Dict[str, Any]:
    """Show the Coming Soon fallback screen."""
    return await update_obs_browser_source(COMING_SOON_DATA_URI, fallback_on_fail=False)


def check_stakeholder_override() -> bool:
    """Check if stakeholder/delegate has requested override."""
    if OVERRIDE_SIGNAL_FILE.exists():
        logger.info("[GCC] Stakeholder override detected - pausing rotation")
        return True
    return False


def clear_stakeholder_override():
    """Clear the override signal (for restart)."""
    if OVERRIDE_SIGNAL_FILE.exists():
        OVERRIDE_SIGNAL_FILE.unlink()
        logger.info("[GCC] Override signal cleared")


async def rotation_daemon(standalone: bool = True, use_screenshots: bool = False):
    """
    Boot layer daemon - 2-minute view rotation within 10-minute schema slot.

    Shows GCC shipping map on stream, rotates views every 2 minutes.
    After 10 minutes (schema duration), returns to allow next schema.
    Stops early if stakeholder/delegate signals override.

    Args:
        standalone: If True, runs indefinitely. If False, returns after schema duration.
        use_screenshots: If True, capture screenshots instead of direct URLs (012 behavior - anti-WAF)

    Returns:
        Dict with schema result (elapsed time, cycles completed, override status)
    """
    mode = "SCREENSHOT" if use_screenshots else "DIRECT"
    logger.info(f"[GCC-DAEMON] Starting GCC schema ({mode} mode, 2-min view rotation)")
    logger.info(f"[GCC-DAEMON] Schema duration: {SCHEMA_DURATION_SEC}s, View interval: {VIEW_INTERVAL_SEC}s")

    # Rotation views - VesselFinder preferred (no cookie popup, ships not planes)
    views = [
        ("hormuz_tankers", VESSELFINDER_HORMUZ),
        ("gulf_tankers", VESSELFINDER_GULF),
        ("all_tankers", VESSELFINDER_TANKERS),
    ]
    view_index = 0
    cycle_count = 0
    schema_start = asyncio.get_event_loop().time()

    running = True
    override_detected = False

    def signal_handler(sig, frame):
        nonlocal running
        logger.info("[GCC-DAEMON] Shutdown signal received")
        running = False

    if standalone:
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    while running:
        # Check schema duration (10 minutes)
        elapsed = asyncio.get_event_loop().time() - schema_start
        if not standalone and elapsed >= SCHEMA_DURATION_SEC:
            logger.info(f"[GCC-DAEMON] Schema complete ({elapsed:.0f}s) - yielding to next schema")
            break

        # Check for stakeholder override
        if check_stakeholder_override():
            logger.info("[GCC-DAEMON] Stakeholder override - pausing schema")
            override_detected = True
            if standalone:
                await asyncio.sleep(60)
                continue
            else:
                break

        # Get current view
        view_name, view_url = views[view_index]
        cycle_count += 1

        logger.info(f"[GCC-DAEMON] View {cycle_count}: {view_name} (elapsed: {elapsed:.0f}s)")

        # Update OBS browser source
        if use_screenshots:
            # 012 BEHAVIOR: Capture screenshot, display cached image (anti-WAF)
            screenshot_path = await capture_map_screenshot(view_url, view_name)
            if screenshot_path and screenshot_path.exists():
                # Convert to data URI for OBS browser source
                data_uri = screenshot_to_data_uri(screenshot_path)
                obs_result = await update_obs_browser_source(data_uri, fallback_on_fail=False)
                if obs_result.get("success"):
                    logger.info(f"[GCC-DAEMON] OBS updated with screenshot: {view_name}")
                else:
                    logger.warning(f"[GCC-DAEMON] OBS update failed: {obs_result.get('error')}")
            else:
                # Screenshot failed - fall back to Coming Soon
                logger.warning(f"[GCC-DAEMON] Screenshot failed for {view_name}, showing fallback")
                obs_result = await show_coming_soon()
        else:
            # Direct URL mode (original behavior)
            obs_result = await update_obs_browser_source(view_url)
            if obs_result.get("success"):
                if obs_result.get("is_fallback"):
                    logger.info("[GCC-DAEMON] Showing Coming Soon fallback")
                else:
                    logger.info(f"[GCC-DAEMON] OBS updated: {view_name}")
            else:
                logger.warning(f"[GCC-DAEMON] OBS update failed: {obs_result.get('error')}")

        # Check alerts
        alerts = await check_alerts()
        for alert in alerts:
            if alert.get("type") != "info":
                logger.warning(f"[GCC-ALERT] {alert['type']}: {alert['message']}")

        # Wait for view interval (2 minutes), check override every 15s
        wait_remaining = VIEW_INTERVAL_SEC
        while wait_remaining > 0 and running:
            # Check schema duration
            if not standalone:
                elapsed = asyncio.get_event_loop().time() - schema_start
                if elapsed >= SCHEMA_DURATION_SEC:
                    break
            if check_stakeholder_override():
                override_detected = True
                break
            sleep_time = min(15, wait_remaining)
            await asyncio.sleep(sleep_time)
            wait_remaining -= sleep_time

        # Rotate to next view
        view_index = (view_index + 1) % len(views)

    elapsed = asyncio.get_event_loop().time() - schema_start
    logger.info(f"[GCC-DAEMON] Schema ended ({elapsed:.0f}s, {cycle_count} views)")

    return {
        "schema": "gcc",
        "elapsed_sec": elapsed,
        "view_count": cycle_count,
        "override": override_detected
    }


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="GCC Shipping Tracker - Strait of Hormuz vessel monitoring"
    )
    parser.add_argument(
        "action",
        nargs="?",
        default="summary",
        choices=["summary", "map", "tankers", "alerts", "daemon"],
        help="Action to perform"
    )
    parser.add_argument("--daemon", action="store_true", help="Run boot layer daemon (10-min rotation)")
    parser.add_argument("--screenshot", action="store_true", help="Use screenshot mode (012 behavior - anti-WAF)")
    parser.add_argument("--map", action="store_true", help="Open live map in browser")
    parser.add_argument("--tankers", action="store_true", help="Filter for oil tankers")
    parser.add_argument("--alerts", action="store_true", help="Show maritime alerts")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--override", action="store_true", help="Set stakeholder override (pause daemon)")
    parser.add_argument("--clear-override", action="store_true", help="Clear stakeholder override")
    parser.add_argument("--coming-soon", action="store_true", help="Show Coming Soon fallback screen")

    args = parser.parse_args()

    # Handle override commands
    if args.override:
        OVERRIDE_SIGNAL_FILE.touch()
        print(f"[GCC] Stakeholder override set - daemon will pause")
        print(f"[GCC] Signal file: {OVERRIDE_SIGNAL_FILE}")
        return

    if args.clear_override:
        clear_stakeholder_override()
        print(f"[GCC] Override cleared - daemon will resume")
        return

    # Coming Soon screen test
    if args.coming_soon:
        print("[GCC] Showing Coming Soon fallback screen...")
        result = asyncio.run(show_coming_soon())
        if result.get("success"):
            print("[GCC] Coming Soon screen displayed in OBS")
        else:
            print(f"[GCC] Failed: {result.get('error')}")
            # Print the HTML for manual use
            print("\n[GCC] Fallback HTML (copy to browser source):")
            print(COMING_SOON_HTML[:200] + "...")
        return

    # Daemon mode
    if args.daemon or args.action == "daemon":
        if args.screenshot:
            print("[GCC] Starting boot layer daemon (SCREENSHOT mode - 012 behavior)...")
            print("[GCC] This mode captures screenshots to avoid WAF detection")
        else:
            print("[GCC] Starting boot layer daemon...")
        print("[GCC] Press Ctrl+C or use --override to stop")
        asyncio.run(rotation_daemon(use_screenshots=args.screenshot))
        return

    # Regular skill execution
    result = asyncio.run(execute_skill(
        action=args.action,
        open_map=args.map,
        tankers_only=args.tankers,
        show_alerts=args.alerts,
    ))

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"\n{'='*60}")
        print("GCC SHIPPING TRACKER - Strait of Hormuz")
        print(f"{'='*60}")
        print(f"Timestamp: {result.get('timestamp', 'N/A')}")
        print(f"Region: {result.get('region', 'gcc_strait_of_hormuz')}")

        if "map" in result:
            print(f"\nMap opened: {result['map'].get('url', 'N/A')}")

        if "alerts" in result:
            print("\nAlerts:")
            for alert in result["alerts"]:
                print(f"  [{alert['type'].upper()}] {alert['message']}")

        if "map_urls" in result:
            print("\nLive Maps:")
            for name, url in result["map_urls"].items():
                print(f"  {name}: {url}")

        print(f"\n{'='*60}")


if __name__ == "__main__":
    main()
