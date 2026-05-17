"""
Stream Metadata Editor - antifaFM YouTube Live

Edits live stream metadata (title, description, customization) via YouTube Studio automation.
WSP 27: Universal DAE Architecture
WSP 84: Code Reuse (youtube_go_live patterns)
"""

import asyncio
import logging
import os
from typing import Optional
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import socket
import time

logger = logging.getLogger(__name__)

# Browser debug port for antifaFM metadata editing
# antifaFM uses Edge (port 9223) per youtube_channel_registry.py
# Chrome (9222) = Move2Japan/UnDaoDu, Edge (9223) = FoundUps/antifaFM
# Env precedence: ANTIFAFM_BROWSER_PORT > FOUNDUPS_EDGE_PORT > EDGE_DEBUG_PORT > 9223
ANTIFAFM_BROWSER_PORT = int(os.getenv(
    "ANTIFAFM_BROWSER_PORT",
    os.getenv("FOUNDUPS_EDGE_PORT", os.getenv("EDGE_DEBUG_PORT", "9223"))
))
# Browser type for error messages
ANTIFAFM_BROWSER_TYPE = os.getenv("ANTIFAFM_BROWSER_TYPE", "Edge")

# Auto-launch browser fallback (default OFF for conservative behavior)
# Set ANTIFAFM_METADATA_AUTO_LAUNCH_BROWSER=1 to enable
ANTIFAFM_METADATA_AUTO_LAUNCH_BROWSER = os.getenv(
    "ANTIFAFM_METADATA_AUTO_LAUNCH_BROWSER", "0"
) == "1"

ANTIFAFM_CHANNEL_ID = "UCVSmg5aOhP4tnQ9KFUg97qA"
LIVE_DASHBOARD_URL = f"https://studio.youtube.com/channel/{ANTIFAFM_CHANNEL_ID}/livestreaming/stream"

# Default M2M description template (ASCII-safe, no emoji for Windows cp932)
DEFAULT_DESCRIPTION = """antifaFM - 24/7 Antifascist Radio

Live stream powered by FoundUps AI automation.

#antifaFM #LiveRadio #FoundUps #AI #Automation #0102 #pAVS
#AntifascistMusic #Resistance #CommunityRadio #OpenSource

LINKS:
- FoundUps: https://foundups.com
- GitHub: https://github.com/foundups

Powered by 0102 DAE Network"""


def _port_open(port: int, timeout: float = 2) -> bool:
    """Check if a port is open."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex(('127.0.0.1', port))
        sock.close()
        return result == 0
    except Exception:
        return False


def _try_auto_launch_browser() -> tuple[bool, str]:
    """Attempt to auto-launch the configured browser if enabled.

    Only called when port check fails AND ANTIFAFM_METADATA_AUTO_LAUNCH_BROWSER=1.

    Returns:
        (success, message)
    """
    if not ANTIFAFM_METADATA_AUTO_LAUNCH_BROWSER:
        return False, "Auto-launch disabled (set ANTIFAFM_METADATA_AUTO_LAUNCH_BROWSER=1 to enable)"

    try:
        from modules.infrastructure.dependency_launcher.src.dae_dependencies import (
            launch_edge,
            launch_chrome,
        )

        # Determine which launcher to use based on configured port
        if ANTIFAFM_BROWSER_PORT == 9222:
            logger.info("[AUTOLAUNCH] Launching Chrome on port 9222...")
            return launch_chrome()
        else:
            # Default to Edge for 9223 or any other port
            logger.info(f"[AUTOLAUNCH] Launching Edge on port {ANTIFAFM_BROWSER_PORT}...")
            return launch_edge()

    except ImportError as e:
        return False, f"Auto-launch unavailable: {e}"
    except Exception as e:
        return False, f"Auto-launch failed: {e}"


def _connect_to_browser():
    """Connect to existing browser via debug port.

    Uses ANTIFAFM_BROWSER_PORT (default: 9223 for Edge).
    Set ANTIFAFM_BROWSER_PORT=9222 to use Chrome instead.

    If port is not open and ANTIFAFM_METADATA_AUTO_LAUNCH_BROWSER=1,
    attempts to launch the browser automatically.
    """
    if not _port_open(ANTIFAFM_BROWSER_PORT):
        # Port not open - try auto-launch if enabled
        if ANTIFAFM_METADATA_AUTO_LAUNCH_BROWSER:
            logger.info(f"{ANTIFAFM_BROWSER_TYPE} not running on port {ANTIFAFM_BROWSER_PORT}, attempting auto-launch...")
            ok, msg = _try_auto_launch_browser()
            if ok:
                logger.info(f"[AUTOLAUNCH] {msg}")
            else:
                logger.error(f"[AUTOLAUNCH] {msg}")
                return None
        else:
            logger.error(
                f"{ANTIFAFM_BROWSER_TYPE} not running on port {ANTIFAFM_BROWSER_PORT}. "
                f"Start browser manually or set ANTIFAFM_METADATA_AUTO_LAUNCH_BROWSER=1"
            )
            return None

    opts = Options()
    opts.add_experimental_option("debuggerAddress", f"127.0.0.1:{ANTIFAFM_BROWSER_PORT}")

    try:
        driver = webdriver.Chrome(options=opts)
        return driver
    except Exception as e:
        logger.error(f"Failed to connect to {ANTIFAFM_BROWSER_TYPE} on port {ANTIFAFM_BROWSER_PORT}: {e}")
        return None


async def edit_stream_metadata(
    title: Optional[str] = None,
    description: Optional[str] = None,
    use_default_description: bool = True
) -> dict:
    """
    Edit live stream metadata on YouTube Studio.

    Args:
        title: New stream title (optional)
        description: New description (optional, uses DEFAULT_DESCRIPTION if use_default_description=True)
        use_default_description: If True and no description provided, use M2M template

    Returns:
        dict with success status and details
    """
    result = {"success": False, "error": None, "changes": []}

    # Connect to browser (Edge port 9223 by default, Chrome 9222 via ANTIFAFM_BROWSER_PORT)
    driver = _connect_to_browser()
    if not driver:
        result["error"] = f"Could not connect to {ANTIFAFM_BROWSER_TYPE} on debug port {ANTIFAFM_BROWSER_PORT}"
        return result

    try:
        # Navigate to live dashboard
        print(f"[EDIT] Navigating to live dashboard...")
        driver.get(LIVE_DASHBOARD_URL)
        await asyncio.sleep(3)

        # Wait for page to load
        wait = WebDriverWait(driver, 15)

        # Click Edit button
        print("[EDIT] Looking for Edit button...")
        try:
            edit_btn = wait.until(EC.element_to_be_clickable((
                By.CSS_SELECTOR, "ytcp-button#edit-button button"
            )))
            edit_btn.click()
            result["changes"].append("clicked_edit")
            print("[EDIT] Clicked Edit button")
            await asyncio.sleep(2)
        except Exception as e:
            # Try alternative selector
            try:
                edit_btn = driver.find_element(By.ID, "edit-button")
                edit_btn.click()
                result["changes"].append("clicked_edit_alt")
                print("[EDIT] Clicked Edit button (alt)")
                await asyncio.sleep(2)
            except Exception:
                result["error"] = f"Could not find Edit button: {e}"
                return result

        # Set title if provided
        if title:
            print(f"[EDIT] Setting title: {title[:30]}...")
            try:
                title_field = wait.until(EC.presence_of_element_located((
                    By.CSS_SELECTOR, "ytcp-video-title#title-wrapper #title-textarea"
                )))
                # Clear and set new title
                driver.execute_script("arguments[0].textContent = ''", title_field)
                title_field.send_keys(title)
                result["changes"].append(f"title={title[:30]}")
                print("[EDIT] Title set")
            except Exception as e:
                logger.warning(f"Could not set title: {e}")

        # Set description
        desc_to_use = description
        if not desc_to_use and use_default_description:
            desc_to_use = DEFAULT_DESCRIPTION

        if desc_to_use:
            print("[EDIT] Setting description...")
            try:
                desc_field = wait.until(EC.presence_of_element_located((
                    By.CSS_SELECTOR, "ytcp-video-description#description-wrapper #description-textarea"
                )))
                # Clear and set new description
                driver.execute_script("arguments[0].textContent = ''", desc_field)
                desc_field.send_keys(desc_to_use)
                result["changes"].append("description_set")
                print("[EDIT] Description set with M2M hashtags")
            except Exception as e:
                logger.warning(f"Could not set description: {e}")

        # Click Save button
        print("[EDIT] Saving changes...")
        try:
            save_btn = wait.until(EC.element_to_be_clickable((
                By.CSS_SELECTOR, "ytcp-button#save-button button"
            )))
            save_btn.click()
            result["changes"].append("saved")
            print("[EDIT] Changes saved!")
            await asyncio.sleep(2)
        except Exception as e:
            # Try alternative
            try:
                save_btn = driver.find_element(By.ID, "save-button")
                save_btn.click()
                result["changes"].append("saved_alt")
                print("[EDIT] Changes saved (alt)")
                await asyncio.sleep(2)
            except Exception:
                result["error"] = f"Could not click Save: {e}"
                return result

        result["success"] = True

    except Exception as e:
        result["error"] = str(e)
        logger.error(f"Stream metadata edit failed: {e}")

    return result


async def set_customization_options(
    live_chat: bool = True,
    chat_replay: bool = True,
    chat_summary: bool = True,
    leaderboard: bool = True,
    participation_mode: str = "anyone"  # "anyone", "subscribers", "approved"
) -> dict:
    """
    Set stream customization options.

    Args:
        live_chat: Enable live chat
        chat_replay: Enable chat replay
        chat_summary: Enable chat summary
        leaderboard: Enable viewer leaderboard
        participation_mode: Who can chat ("anyone", "subscribers", "approved")

    Returns:
        dict with success status
    """
    result = {"success": False, "error": None, "changes": []}

    driver = _connect_to_browser()
    if not driver:
        result["error"] = f"Could not connect to {ANTIFAFM_BROWSER_TYPE} on port {ANTIFAFM_BROWSER_PORT}"
        return result

    try:
        wait = WebDriverWait(driver, 10)

        # Click Customization tab
        print("[EDIT] Opening Customization tab...")
        try:
            custom_tab = wait.until(EC.element_to_be_clickable((
                By.CSS_SELECTOR, "li#customization"
            )))
            custom_tab.click()
            result["changes"].append("customization_tab")
            await asyncio.sleep(1)
        except Exception as e:
            result["error"] = f"Could not open Customization tab: {e}"
            return result

        # Set checkboxes
        checkbox_map = {
            "live_chat": "#chat-enabled-checkbox",
            "chat_replay": "#chat-replay-checkbox",
            "chat_summary": "#chat-summary-opt-out-checkbox",
            "leaderboard": "#viewer-leaderboard-opt-out-checkbox"
        }

        for name, selector in checkbox_map.items():
            desired = locals().get(name, True)
            try:
                checkbox = driver.find_element(By.CSS_SELECTOR, selector)
                is_checked = checkbox.get_attribute("checked") is not None
                if is_checked != desired:
                    checkbox.click()
                    result["changes"].append(f"{name}={desired}")
            except Exception:
                pass

        # Set participation mode
        mode_map = {
            "anyone": "#all-users-mode-radio-button",
            "subscribers": "#subscribers-only-mode-radio-button",
            "approved": "#invite-mode-radio-button"
        }

        if participation_mode in mode_map:
            try:
                radio = driver.find_element(By.CSS_SELECTOR, mode_map[participation_mode])
                radio.click()
                result["changes"].append(f"participation={participation_mode}")
            except Exception:
                pass

        result["success"] = True

    except Exception as e:
        result["error"] = str(e)

    return result


async def apply_m2m_description() -> dict:
    """
    Quick action: Apply M2M discoverable description to current stream.
    """
    return await edit_stream_metadata(
        title=None,  # Keep existing title
        description=DEFAULT_DESCRIPTION,
        use_default_description=True
    )


# ============================================================================
# API-BASED METHODS (Primary - more reliable than DOM)
# ============================================================================

async def api_update_metadata(title: Optional[str] = None, description: Optional[str] = None) -> dict:
    """
    Update stream metadata via YouTube API (preferred over DOM).

    This is the OpenClaw/IronClaw entry point for metadata updates.
    """
    try:
        from modules.platform_integration.antifafm_broadcaster.src.youtube_broadcast_manager import (
            YouTubeBroadcastManager
        )
        manager = YouTubeBroadcastManager()
        return await manager.update_current_broadcast(title=title, description=description)
    except Exception as e:
        return {"success": False, "error": str(e), "method": "api"}


async def api_clickbait_update(include_news: bool = True) -> dict:
    """
    Generate and apply clickbait title + M2M description via API.

    Args:
        include_news: Include current headlines in description

    Returns:
        dict with success status
    """
    try:
        from modules.platform_integration.antifafm_broadcaster.src.youtube_broadcast_manager import (
            YouTubeBroadcastManager, generate_clickbait_title, generate_m2m_description
        )

        # Get news headlines if requested
        news = []
        if include_news:
            try:
                from modules.platform_integration.antifafm_broadcaster.scripts.launch import _fetch_news_headlines
                news = _fetch_news_headlines()[:5] if _fetch_news_headlines else []
            except Exception:
                pass

        title = generate_clickbait_title(news)
        description = generate_m2m_description(news)

        manager = YouTubeBroadcastManager()
        result = await manager.update_current_broadcast(title=title, description=description)
        result["title_preview"] = title[:50]
        return result

    except Exception as e:
        return {"success": False, "error": str(e), "method": "api_clickbait"}


# ============================================================================
# CLI ENTRY POINT (OpenClaw/IronClaw compatible)
# ============================================================================

# CLI entry point
if __name__ == "__main__":
    import sys

    async def main():
        if len(sys.argv) > 1:
            action = sys.argv[1]

            if action == "api":
                # API-based update (preferred)
                if len(sys.argv) > 2:
                    title = " ".join(sys.argv[2:])
                    result = await api_update_metadata(title=title)
                else:
                    result = await api_clickbait_update()

            elif action == "clickbait":
                # Generate clickbait title + M2M description
                result = await api_clickbait_update(include_news=True)

            elif action == "m2m":
                # Quick apply M2M description (DOM fallback)
                result = await apply_m2m_description()

            elif action == "title" and len(sys.argv) > 2:
                # Set title (DOM fallback)
                title = " ".join(sys.argv[2:])
                result = await edit_stream_metadata(title=title)

            elif action == "customize":
                # Apply default customization (DOM)
                result = await set_customization_options()

            else:
                print("Usage:")
                print("  python executor.py api [title]   # API update (preferred)")
                print("  python executor.py clickbait     # Generate clickbait + news")
                print("  python executor.py m2m           # DOM: Apply M2M description")
                print("  python executor.py title <text>  # DOM: Set stream title")
                print("  python executor.py customize     # DOM: Apply customization")
                return

            print(f"\nResult: {result}")
        else:
            # Default: API clickbait update
            result = await api_clickbait_update()
            print(f"\nResult: {result}")

    asyncio.run(main())
