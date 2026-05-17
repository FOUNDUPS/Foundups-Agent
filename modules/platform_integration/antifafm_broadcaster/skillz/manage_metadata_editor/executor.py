"""
Manage Metadata Editor - Edit past/scheduled broadcasts via YouTube Studio DOM

CLI Skillz for OpenClaw/IronClaw invocation.
Navigates to Manage page and edits title/description via DOM automation.

Usage:
    python executor.py list                           # List recent broadcasts
    python executor.py edit <video_id> --title "..."  # Edit specific broadcast
    python executor.py recent --title "..."           # Edit most recent broadcast
    python executor.py clickbait                      # Apply clickbait to most recent

WSP 27: Universal DAE Architecture
WSP 84: Code Reuse (youtube_go_live patterns)
WSP 103: CLI Interface Standard
"""

import asyncio
import argparse
import logging
import os
import socket
import time
from typing import Optional, Dict, Any, List

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

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
MANAGE_URL = f"https://studio.youtube.com/channel/{ANTIFAFM_CHANNEL_ID}/livestreaming/manage"


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


async def list_broadcasts(limit: int = 10) -> List[Dict[str, Any]]:
    """
    List recent broadcasts from the Manage page.

    Returns:
        List of broadcast info dicts
    """
    driver = _connect_to_browser()
    if not driver:
        return []

    broadcasts = []

    try:
        print(f"[MANAGE] Navigating to {MANAGE_URL}")
        driver.get(MANAGE_URL)
        await asyncio.sleep(3)

        wait = WebDriverWait(driver, 15)

        # Wait for video rows to load
        try:
            rows = wait.until(EC.presence_of_all_elements_located((
                By.CSS_SELECTOR, "ytcp-video-row"
            )))

            print(f"[MANAGE] Found {len(rows)} broadcasts")

            for i, row in enumerate(rows[:limit]):
                try:
                    # Extract video info
                    title_el = row.find_element(By.CSS_SELECTOR, "#video-title")
                    title = title_el.text if title_el else "Unknown"

                    # Try to get video ID from href
                    video_id = "unknown"
                    try:
                        link = row.find_element(By.CSS_SELECTOR, "a[href*='/video/']")
                        href = link.get_attribute("href")
                        if "/video/" in href:
                            video_id = href.split("/video/")[1].split("/")[0]
                    except Exception:
                        pass

                    broadcasts.append({
                        "index": i,
                        "video_id": video_id,
                        "title": title[:60],
                    })
                    print(f"  [{i}] {video_id}: {title[:50]}...")

                except Exception as e:
                    logger.debug(f"Could not parse row {i}: {e}")

        except Exception as e:
            print(f"[MANAGE] Could not find video rows: {e}")

    except Exception as e:
        logger.error(f"[MANAGE] List broadcasts failed: {e}")

    return broadcasts


async def edit_broadcast_metadata(
    video_index: int = 0,
    title: Optional[str] = None,
    description: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Edit a broadcast's title and/or description via DOM automation.

    Args:
        video_index: Row index in the Manage list (0 = most recent)
        title: New title (optional)
        description: New description (optional)

    Returns:
        dict with success status and details
    """
    result = {"success": False, "error": None, "changes": []}

    if not title and not description:
        result["error"] = "Must provide title or description"
        return result

    driver = _connect_to_browser()
    if not driver:
        result["error"] = f"Could not connect to {ANTIFAFM_BROWSER_TYPE} on debug port {ANTIFAFM_BROWSER_PORT}"
        return result

    try:
        print(f"[MANAGE] Navigating to Manage page...")
        driver.get(MANAGE_URL)
        await asyncio.sleep(3)

        wait = WebDriverWait(driver, 15)
        actions = ActionChains(driver)

        # Step 1: Find video rows
        print(f"[MANAGE] Finding video row {video_index}...")
        rows = wait.until(EC.presence_of_all_elements_located((
            By.CSS_SELECTOR, "ytcp-video-row"
        )))

        if video_index >= len(rows):
            result["error"] = f"Video index {video_index} out of range (max {len(rows)-1})"
            return result

        target_row = rows[video_index]

        # Step 2: Hover over row to reveal Options button
        print("[MANAGE] Hovering over video row...")
        actions.move_to_element(target_row).perform()
        await asyncio.sleep(0.5)

        # Step 2b: Click Options button (three dots)
        print("[MANAGE] Clicking Options button...")
        try:
            options_btn = target_row.find_element(
                By.CSS_SELECTOR, "ytcp-icon-button.open-menu-button"
            )
            options_btn.click()
            await asyncio.sleep(0.5)
        except Exception as e:
            # Try JavaScript click as fallback
            try:
                options_btn = target_row.find_element(
                    By.CSS_SELECTOR, "#hover-items ytcp-icon-button"
                )
                driver.execute_script("arguments[0].click()", options_btn)
                await asyncio.sleep(0.5)
            except Exception:
                result["error"] = f"Could not find Options button: {e}"
                return result

        # Step 3: Click "Edit title and description"
        print("[MANAGE] Clicking 'Edit title and description'...")
        try:
            edit_option = wait.until(EC.element_to_be_clickable((
                By.XPATH, "//yt-formatted-string[contains(text(), 'Edit title and description')]"
            )))
            edit_option.click()
            result["changes"].append("opened_edit_dialog")
            await asyncio.sleep(1)
        except Exception as e:
            result["error"] = f"Could not find edit option: {e}"
            return result

        # Step 4: Edit title if provided
        if title:
            print(f"[MANAGE] Setting title: {title[:40]}...")
            try:
                title_box = wait.until(EC.presence_of_element_located((
                    By.CSS_SELECTOR,
                    "ytcp-video-list-cell-video-edit-dialog #title-input #textbox"
                )))

                # Clear existing content (Ctrl+A, Delete)
                title_box.click()
                await asyncio.sleep(0.2)
                title_box.send_keys(Keys.CONTROL, 'a')
                await asyncio.sleep(0.1)
                title_box.send_keys(Keys.DELETE)
                await asyncio.sleep(0.1)

                # Type new title
                title_box.send_keys(title)
                result["changes"].append(f"title={title[:30]}")
                print("[MANAGE] Title set")

            except Exception as e:
                logger.warning(f"Could not set title: {e}")

        # Step 5: Edit description if provided
        if description:
            print("[MANAGE] Setting description...")
            try:
                desc_box = wait.until(EC.presence_of_element_located((
                    By.CSS_SELECTOR,
                    "ytcp-video-list-cell-video-edit-dialog #description-textarea #textbox"
                )))

                # Clear existing content
                desc_box.click()
                await asyncio.sleep(0.2)
                desc_box.send_keys(Keys.CONTROL, 'a')
                await asyncio.sleep(0.1)
                desc_box.send_keys(Keys.DELETE)
                await asyncio.sleep(0.1)

                # Type new description
                desc_box.send_keys(description)
                result["changes"].append("description_set")
                print("[MANAGE] Description set")

            except Exception as e:
                logger.warning(f"Could not set description: {e}")

        # Step 6: Click Save
        print("[MANAGE] Saving changes...")
        try:
            save_btn = wait.until(EC.element_to_be_clickable((
                By.CSS_SELECTOR,
                "ytcp-video-list-cell-video-edit-dialog #save-button button"
            )))
            save_btn.click()
            result["changes"].append("saved")
            print("[MANAGE] Changes saved!")
            await asyncio.sleep(2)
        except Exception as e:
            result["error"] = f"Could not click Save: {e}"
            return result

        result["success"] = True

    except Exception as e:
        result["error"] = str(e)
        logger.error(f"[MANAGE] Edit failed: {e}")

    return result


async def apply_clickbait_to_recent() -> Dict[str, Any]:
    """
    Apply clickbait title and M2M description to most recent broadcast.
    """
    try:
        from modules.platform_integration.antifafm_broadcaster.src.youtube_broadcast_manager import (
            generate_clickbait_title, generate_m2m_description
        )

        title = generate_clickbait_title()
        description = generate_m2m_description()

        print(f"[MANAGE] Generated title: {title}")
        print(f"[MANAGE] Generated description preview: {description[:100]}...")

        return await edit_broadcast_metadata(
            video_index=0,  # Most recent
            title=title,
            description=description
        )

    except Exception as e:
        return {"success": False, "error": str(e)}


async def get_shareable_link(video_index: int = 0) -> Dict[str, Any]:
    """
    Get shareable link for a broadcast via Options menu.

    Args:
        video_index: Row index in the Manage list (0 = most recent)

    Returns:
        dict with success status and link (copied to clipboard by YouTube)
    """
    result = {"success": False, "error": None, "link": None}

    driver = _connect_to_browser()
    if not driver:
        result["error"] = f"Could not connect to {ANTIFAFM_BROWSER_TYPE} on debug port {ANTIFAFM_BROWSER_PORT}"
        return result

    try:
        print(f"[MANAGE] Navigating to Manage page...")
        driver.get(MANAGE_URL)
        await asyncio.sleep(3)

        wait = WebDriverWait(driver, 15)
        actions = ActionChains(driver)

        # Find video rows
        print(f"[MANAGE] Finding video row {video_index}...")
        rows = wait.until(EC.presence_of_all_elements_located((
            By.CSS_SELECTOR, "ytcp-video-row"
        )))

        if video_index >= len(rows):
            result["error"] = f"Video index {video_index} out of range (max {len(rows)-1})"
            return result

        target_row = rows[video_index]

        # Hover to reveal Options button
        print("[MANAGE] Hovering over video row...")
        actions.move_to_element(target_row).perform()
        await asyncio.sleep(0.5)

        # Click Options button (three dots)
        print("[MANAGE] Clicking Options button...")
        try:
            options_btn = target_row.find_element(
                By.CSS_SELECTOR, "ytcp-icon-button.open-menu-button"
            )
            options_btn.click()
            await asyncio.sleep(0.5)
        except Exception as e:
            try:
                options_btn = target_row.find_element(
                    By.CSS_SELECTOR, "#hover-items ytcp-icon-button"
                )
                driver.execute_script("arguments[0].click()", options_btn)
                await asyncio.sleep(0.5)
            except Exception:
                result["error"] = f"Could not find Options button: {e}"
                return result

        # Click "Get shareable link" (item-1)
        print("[MANAGE] Clicking 'Get shareable link'...")
        try:
            link_option = wait.until(EC.element_to_be_clickable((
                By.CSS_SELECTOR, "tp-yt-paper-item#text-item-1"
            )))
            link_option.click()
            result["success"] = True
            print("[MANAGE] Link copied to clipboard by YouTube!")
            await asyncio.sleep(1)

            # Try to extract video ID from the row for manual link construction
            try:
                link_el = target_row.find_element(By.CSS_SELECTOR, "a[href*='/video/']")
                href = link_el.get_attribute("href")
                if "/video/" in href:
                    video_id = href.split("/video/")[1].split("/")[0]
                    result["link"] = f"https://youtube.com/watch?v={video_id}"
                    print(f"[MANAGE] Video link: {result['link']}")
            except Exception:
                result["link"] = "(copied to clipboard)"

        except Exception as e:
            result["error"] = f"Could not click 'Get shareable link': {e}"
            return result

    except Exception as e:
        result["error"] = str(e)
        logger.error(f"[MANAGE] Get link failed: {e}")

    return result


# ============================================================================
# CLI ENTRY POINT (WSP 103)
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Edit YouTube broadcast metadata via Manage page DOM"
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # List command
    list_parser = subparsers.add_parser("list", help="List recent broadcasts")
    list_parser.add_argument("--limit", type=int, default=10, help="Max broadcasts to show")

    # Edit command
    edit_parser = subparsers.add_parser("edit", help="Edit specific broadcast")
    edit_parser.add_argument("index", type=int, help="Video index (0=most recent)")
    edit_parser.add_argument("--title", type=str, help="New title")
    edit_parser.add_argument("--description", type=str, help="New description")

    # Recent command (edit most recent)
    recent_parser = subparsers.add_parser("recent", help="Edit most recent broadcast")
    recent_parser.add_argument("--title", type=str, help="New title")
    recent_parser.add_argument("--description", type=str, help="New description")

    # Clickbait command
    subparsers.add_parser("clickbait", help="Apply clickbait title + M2M description to most recent")

    # Link command
    link_parser = subparsers.add_parser("link", help="Get shareable link for a broadcast")
    link_parser.add_argument("index", type=int, nargs="?", default=0, help="Video index (0=most recent)")

    args = parser.parse_args()

    async def run():
        if args.command == "list":
            await list_broadcasts(limit=args.limit)

        elif args.command == "edit":
            result = await edit_broadcast_metadata(
                video_index=args.index,
                title=args.title,
                description=args.description
            )
            print(f"\nResult: {result}")

        elif args.command == "recent":
            result = await edit_broadcast_metadata(
                video_index=0,
                title=args.title,
                description=args.description
            )
            print(f"\nResult: {result}")

        elif args.command == "clickbait":
            result = await apply_clickbait_to_recent()
            print(f"\nResult: {result}")

        elif args.command == "link":
            result = await get_shareable_link(video_index=args.index)
            print(f"\nResult: {result}")

        else:
            parser.print_help()

    asyncio.run(run())


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s"
    )
    main()
