"""
DOM Automation Layer for YouTube Studio

Selenium/UI-TARS selectors and interaction methods for Shorts scheduling.
Based on live DOM inspection of YouTube Studio pages.
"""

import asyncio
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

logger = logging.getLogger(__name__)

# Orchestration switchboard for OOPS breadcrumb telemetry (optional, graceful degradation)
try:
    from modules.infrastructure.orchestration_switchboard.src.orchestration_switchboard import get_orchestration_switchboard
    _has_switchboard = True
except ImportError:
    _has_switchboard = False


def _emit_oops_signal(signal_type: str, source_dae: str = "shorts_scheduler_dom", **metadata):
    """Emit OOPS breadcrumb to orchestration switchboard (fire-and-forget)."""
    if not _has_switchboard:
        return
    try:
        sb = get_orchestration_switchboard()
        sb.receive_signal(signal_type, source_dae, metadata=metadata)
    except Exception as e:
        logger.debug(f"[OOPS] Switchboard signal failed: {e}")


# Diagnostic screenshot directory
DIAGNOSTIC_DIR = Path("modules/platform_integration/youtube_shorts_scheduler/memory/diagnostics")
DIAGNOSTIC_DIR.mkdir(parents=True, exist_ok=True)


class DOMSelectors:
    """
    Comprehensive DOM selectors for YouTube Studio.

    Page 1: Channel Content (Shorts List)
    Page 2: Video Details/Edit Page
    Page 3: Visibility/Scheduling Dialog
    """

    # =========================================
    # PAGE 1: SHORTS LIST
    # =========================================

    # Navigation
    SHORTS_TAB = "tab[aria-label='Shorts']"
    FILTER_INPUT = "input[placeholder='Filter']"

    # Video Table
    # Updated: Original selector doesn't match - use ytcp-video-row
    VIDEO_TABLE = "ytcp-video-row"  # Wait for at least one video row to appear
    VIDEO_ROWS = "ytcp-video-row"
    VIDEO_TITLE_LINK = "a[href*='/edit']"
    VIDEO_THUMBNAIL = "img[alt*='Video thumbnail']"

    # Pagination
    NEXT_PAGE_BTN = "button[aria-label='Navigate to the next page']"
    PREV_PAGE_BTN = "button[aria-label='Navigate to the previous page']"

    # XPath selectors for visibility filtering
    XPATH_UNLISTED_ROWS = "//ytcp-video-row[.//span[contains(text(),'Unlisted')]]"
    XPATH_SCHEDULED_ROWS = "//ytcp-video-row[.//span[contains(text(),'Scheduled')]]"
    XPATH_VIDEO_DATE_CELL = "//td[contains(text(),'202')]"  # Matches 2025, 2026, etc.

    # Filter UI selectors (DOM fallback - Layer 1)
    FILTER_ICON_COORDS = (170, 104)  # Hamburger icon + Filter area
    VISIBILITY_MENU_ITEM_XPATH = "//span[text()='Visibility']"
    UNLISTED_CHECKBOX_XPATH = "//span[text()='Unlisted']/ancestor::ytcp-checkbox-lit"
    APPLY_FILTER_BTN_XPATH = "//button[.//span[text()='Apply']]"
    # Filter chip is ytcp-chip element (discovered via diagnose_page.py)
    FILTER_CHIP_UNLISTED = "ytcp-chip"  # Check text content for "Visibility: Unlisted"
    FILTER_CHIP_ANY = "ytcp-chip"  # Any visibility chip

    # Sort by Date header (2026-01-28: Added for oldest-first processing)
    # DOM: ytcp-table-header > button#date-header-name
    DATE_HEADER_SORT_CSS = "ytcp-table-header button#date-header-name"
    DATE_HEADER_SORT_XPATH = "//ytcp-table-header//button[@id='date-header-name']"
    # Sort indicator - check if sorted ascending (oldest first) or descending (newest first)
    DATE_SORT_ICON_CSS = "ytcp-table-header button#date-header-name yt-icon"

    # Page size selector (2026-01-28: Added for 50-video batches)
    # DOM: ytcp-table-footer#footer > div#page-control-container > ytcp-select#page-size > ytcp-text-dropdown-trigger#trigger
    PAGE_SIZE_TRIGGER_CSS = "ytcp-table-footer#footer ytcp-select#page-size ytcp-text-dropdown-trigger#trigger"
    PAGE_SIZE_TRIGGER_XPATH = "//ytcp-table-footer[@id='footer']//ytcp-select[@id='page-size']//ytcp-text-dropdown-trigger[@id='trigger']"
    # Menu items: tp-yt-paper-listbox#paper-list > tp-yt-paper-item
    PAGE_SIZE_MENU_CSS = "ytcp-text-menu#select-menu-for-page-size tp-yt-paper-listbox#paper-list"
    PAGE_SIZE_ITEM_50_CSS = "ytcp-text-menu#select-menu-for-page-size tp-yt-paper-item:nth-child(3)"  # 10, 30, 50
    PAGE_SIZE_ITEM_50_XPATH = "//ytcp-text-menu[@id='select-menu-for-page-size']//tp-yt-paper-item[.//yt-formatted-string[text()='50']]"

    # Back button to return to shorts list (2026-01-28: For continuous processing)
    # DOM: ytcp-navigation-drawer > nav#left-nav > ytcp-animatable > ytcp-ve > a#back-button
    BACK_BUTTON_CSS = "ytcp-navigation-drawer a#back-button"
    BACK_BUTTON_XPATH = "//ytcp-navigation-drawer//a[@id='back-button']"

    # =========================================
    # LAYER 2: VIDEO EDIT PAGE SELECTORS
    # =========================================

    # Edit button on video row (hover to reveal)
    EDIT_BUTTON_COORDS = (232, 349)  # Pencil/details icon
    EDIT_BUTTON_SELECTOR = "a#anchor-video-details"
    EDIT_BUTTON_ICON = "ytcp-icon-button#video-details"

    # Title textbox on edit page
    TITLE_TEXTBOX_SELECTOR = "#title-textarea #textbox[contenteditable='true']"
    TITLE_TEXTBOX_XPATH = "//div[@id='textbox'][contains(@aria-label,'Add a title')]"

    # Description textbox on edit page
    DESC_TEXTBOX_SELECTOR = "#description-textarea #textbox[contenteditable='true']"
    DESC_TEXTBOX_XPATH = "//div[@id='textbox'][contains(@aria-label,'Tell viewers')]"

    # Save button
    SAVE_BUTTON = "button#save-button"
    SAVE_BUTTON_XPATH = "//ytcp-button[@id='save-button']"

    # =========================================
    # LAYER 3: SCHEDULING SELECTORS
    # Based on 0102 Scheduling Layer Stack
    # =========================================

    # L1: Visibility Dialog
    VISIBILITY_BUTTON = "button[aria-label*='visibility']"
    VISIBILITY_BUTTON_XPATH = "//button[contains(@aria-label,'Edit video visibility status')]"
    VISIBILITY_STATUS = "#visibility-status-span"

    # L1.1: Schedule Expand
    # 2026-02-04: Live DOM confirmed - expand button is ytcp-icon-button#second-container-expand-button
    SCHEDULE_EXPAND_XPATH = "//ytcp-icon-button[@id='second-container-expand-button']"
    # 2026-02-04: Live DOM confirms name="PUBLISH_FROM_PRIVATE" (no name="SCHEDULE" exists)
    SCHEDULE_RADIO_XPATH = "//tp-yt-paper-radio-button[@name='PUBLISH_FROM_PRIVATE']"

    # L2: Date
    DATE_DROPDOWN_XPATH = "//div[contains(@class,'date')]//ytcp-dropdown-trigger"
    DATE_INPUT_XPATH = "//input[contains(@aria-label,'Date')]"
    DATE_TEXT_XPATH = "//div[contains(@class,'date')]//span[@class='text']"
    # Current Studio variant: date is a left-container div inside datepicker-trigger
    DATE_TRIGGER_CSS = (
        "ytcp-visibility-scheduler ytcp-text-dropdown-trigger#datepicker-trigger "
        "ytcp-dropdown-trigger div.left-container"
    )
    # Date picker popup input (ytcp-date-picker dialog)
    DATE_PICKER_INPUT_CSS = "ytcp-date-picker tp-yt-paper-dialog#dialog input.tp-yt-paper-input"

    # L3: Time
    TIME_INPUT_XPATH = "//input[contains(@aria-label,'time') or contains(@placeholder,'time')]"
    TIME_TEXTBOX_XPATH = "//ytcp-form-input-container[contains(.,'Time')]//input"
    # Current Studio variant: time input lives under ytcp-datetime-picker form#form time-of-day-container
    TIME_OF_DAY_INPUT_CSS = (
        "ytcp-visibility-scheduler ytcp-datetime-picker form#form "
        "ytcp-form-input-container#time-of-day-container input.tp-yt-paper-input"
    )

    # L4: Done
    DONE_BUTTON_XPATH = "//button[.//span[text()='Done']]"
    DONE_BUTTON = "button#done-button"

    # =========================================
    # L5: RELATED VIDEO + SAVE + RETURN
    # =========================================

    # L5.1: Related Video Modal
    RELATED_VIDEO_SECTION = "ytcp-video-metadata-related-video"
    RELATED_VIDEO_BUTTON = "ytcp-dropdown-trigger#related-video-dropdown"
    RELATED_VIDEO_BUTTON_XPATH = "//ytcp-dropdown-trigger[@id='related-video-dropdown']"
    RELATED_VIDEO_MODAL = "ytcp-video-picker-dialog"
    RELATED_VIDEO_MODAL_XPATH = "//ytcp-video-picker-dialog"

    # L5.1 Search (for future use)
    RELATED_VIDEO_SEARCH_INPUT = "#video-picker-search-input"
    RELATED_VIDEO_SEARCH_XPATH = "//input[@id='video-picker-search-input']"
    RELATED_VIDEO_SEARCH_BTN = "button#video-picker-search-button"

    # L5.2: Video Grid (first = top-left)
    RELATED_VIDEO_GRID = "ytcp-video-picker-item"
    RELATED_VIDEO_FIRST_XPATH = "(//ytcp-video-picker-item)[1]"  # XPath index for first
    RELATED_VIDEO_THUMBNAIL = "ytcp-video-picker-item img.video-thumbnail"
    RELATED_VIDEO_FIRST_THUMBNAIL_XPATH = "(//ytcp-video-picker-item//img[contains(@class,'thumbnail')])[1]"

    # L5.3: Save (reuse existing SAVE_BUTTON)
    # SAVE_BUTTON already defined above

    # L5.4: Return to list
    BACK_BUTTON = "#back-button"
    BACK_BUTTON_XPATH = "//a[@id='back-button']"
    CHANNEL_CONTENT_LINK = "a[href*='/videos/short']"

    # L5.5: Refresh (handled via keyboard F5)

    # =========================================
    # PAGE 2: VIDEO EDIT PAGE
    # =========================================

    TITLE_INPUT = "textbox[placeholder*='Add a title']"
    TITLE_INPUT_XPATH = "//div[@id='textbox' and @aria-label='Add a title that describes your video (type @ to mention a channel)']"

    DESCRIPTION_INPUT = "textbox[placeholder*='Tell viewers']"
    DESCRIPTION_INPUT_XPATH = "//div[@id='textbox' and contains(@aria-label,'Tell viewers about your video')]"

    SAVE_BTN = "button#save-button"
    UNDO_BTN = "button#undo-button"

    VISIBILITY_BTN = "button[aria-label='Edit video visibility status']"
    VISIBILITY_BTN_XPATH = "//button[@aria-label='Edit video visibility status']"

    BACK_TO_LIST = "a[href*='/videos/short']"

    # Sidebar Navigation
    MENU_DETAILS = "a[href*='/edit']"
    MENU_ANALYTICS = "a[href*='/analytics']"
    MENU_MONETIZATION = "a[href*='/monetization']"
    MENU_COMMENTS = "a[href*='/comments']"

    # =========================================
    # PAGE 3: VISIBILITY/SCHEDULING DIALOG
    # =========================================

    VISIBILITY_DIALOG = "dialog[aria-label='Select video privacy']"
    VISIBILITY_DIALOG_XPATH = "//tp-yt-paper-dialog[contains(@aria-label,'visibility') or contains(@aria-label,'privacy')]"

    # Radio buttons
    RADIO_PRIVATE = "//tp-yt-paper-radio-button[.//span[text()='Private']]"
    RADIO_UNLISTED = "//tp-yt-paper-radio-button[.//span[text()='Unlisted']]"
    RADIO_PUBLIC = "//tp-yt-paper-radio-button[.//span[text()='Public']]"
    # 2026-02-04: No "Schedule" radio exists; scheduling is triggered by expanding #second-container
    RADIO_SCHEDULE = "//tp-yt-paper-radio-button[@name='PUBLISH_FROM_PRIVATE']"

    # Schedule section
    # 2026-02-04: Live DOM confirmed - expand button is #second-container-expand-button
    SCHEDULE_EXPAND = "//ytcp-icon-button[@id='second-container-expand-button']"
    # 2026-02-04: Live DOM - text not in <span>, use contains(.) or @name
    SCHEDULE_RADIO = "//tp-yt-paper-radio-button[@name='PUBLISH_FROM_PRIVATE']"

    # Date/Time inputs
    DATE_PICKER_BTN = "//div[@id='datepicker-trigger']//button"
    DATE_INPUT = "//input[@aria-label='Date picker']"
    TIME_INPUT = "//input[contains(@aria-label,'Time')]"
    TIME_INPUT_TEXTBOX = "//tp-yt-paper-dialog//input[@type='text' and (contains(@value,'AM') or contains(@value,'PM'))]"

    # Dialog buttons
    DONE_BTN = "//button[.//span[text()='Done']]"
    CANCEL_BTN = "//button[.//span[text()='Cancel']]"
    SAVE_CLOSE_BTN = "//button[.//span[contains(text(),'Save')]]"

    # =========================================
    # OOPS PAGE / ACCOUNT RECOVERY SELECTORS
    # =========================================
    # When landing on a channel without correct account logged in

    # Oops page detection - "Switch account" link on error page
    OOPS_SWITCH_ACCOUNT = "#selectaccount-link"
    OOPS_SWITCH_ACCOUNT_XPATH = "//a[@id='selectaccount-link']"
    OOPS_PAGE_CONTENT = "div.content"  # Container on oops page

    # Channel switcher page - after clicking "Switch account"
    CHANNEL_SWITCHER_AVATAR = "#avatar-btn"
    CHANNEL_SWITCHER_AVATAR_XPATH = "//button[@id='avatar-btn']"

    # Account menu popup - after clicking avatar
    ACCOUNT_MENU_POPUP = "ytd-multi-page-menu-renderer"
    ACCOUNT_ITEM_XPATH = "//yt-multi-page-menu-section-renderer//ytd-account-item-renderer"
    # Account name in menu item
    ACCOUNT_NAME_XPATH = ".//yt-formatted-string[@id='channel-title']"

    # Switch account option in avatar menu popup
    SWITCH_ACCOUNT_MENU_ITEM = "//ytd-compact-link-renderer//tp-yt-paper-item[contains(text(),'Switch account')]"
    SWITCH_ACCOUNT_MENU_XPATH = "//tp-yt-paper-item[contains(text(),'Switch account')]"
    ADD_ACCOUNT_XPATH = "//yt-formatted-string[contains(text(),'Add account')]"

    # Channel list in account switcher popup
    CHANNEL_LIST_ITEM = "//ytd-account-item-renderer"
    CHANNEL_NAME_IN_LIST = ".//yt-formatted-string[@id='channel-title']"
    # Account item by channel name (for selecting specific channel)
    ACCOUNT_ITEM_BY_NAME_TEMPLATE = "//ytd-account-item-renderer[.//yt-formatted-string[contains(text(),'{channel_name}')]]"


# Filter dialog checkbox labels (Studio UI text — not always visibility.capitalize())
VISIBILITY_CHECKBOX_LABELS: Dict[str, str] = {
    "UNLISTED": "Unlisted",
    "PRIVATE": "Private",
    "PUBLIC": "Public",
    "SCHEDULED": "Has schedule",
    "DRAFT": "Draft",
    "MEMBERS": "Members",
}

# Chip / URL markers used to detect which visibility filter is active
VISIBILITY_CHIP_MARKERS: Dict[str, tuple] = {
    "UNLISTED": ("unlisted",),
    "SCHEDULED": ("scheduled", "has schedule"),
    "PUBLIC": ("public",),
    "PRIVATE": ("private",),
    "DRAFT": ("draft",),
}


def classify_visibility_filter(chip_text: str, url: str = "") -> Optional[str]:
    """
    Infer active Studio list filter from chip text and/or URL filter param.

    Returns:
        UNLISTED, SCHEDULED, PUBLIC, PRIVATE, DRAFT, or None if unknown/no filter.
    """
    text = (chip_text or "").lower()
    href = (url or "").lower()

    if text:
        for visibility, markers in VISIBILITY_CHIP_MARKERS.items():
            if any(m in text for m in markers):
                return visibility
        if "visibility:" in text:
            return "UNKNOWN"

    if "filter=" in href:
        for visibility, markers in VISIBILITY_CHIP_MARKERS.items():
            if any(m in href for m in markers):
                return visibility

    return None


class YouTubeStudioDOM:
    """
    DOM interaction layer for YouTube Studio automation.
    """

    def __init__(self, driver):
        """
        Initialize with Selenium WebDriver.

        Args:
            driver: Selenium WebDriver instance (Chrome or Edge)
        """
        self.driver = driver
        self.wait = WebDriverWait(driver, 10)
        self.selectors = DOMSelectors()
        # 012 digital twin (Occam): slow + deterministic + stable.
        # No Bezier cursor paths, no jitter offsets, no mouse jumping.
        self._pre_click_delay = float(os.getenv("YT_SCHEDULER_PRE_CLICK_DELAY_SEC", "0.25"))
        self._post_click_delay = float(os.getenv("YT_SCHEDULER_POST_CLICK_DELAY_SEC", "0.25"))
        self._last_shorts_channel_id: Optional[str] = None

    # =========================================
    # UTILITY METHODS
    # =========================================

    def check_driver_health(self, thorough: bool = False) -> bool:
        """
        Check if the WebDriver connection is still alive.

        Args:
            thorough: If True, also test element finding (slower but catches more issues)

        Returns:
            True if driver is healthy, False if connection is stale/broken
        """
        try:
            # Basic test: get current URL (fast)
            url = self.driver.current_url
            if not url:
                logger.warning("[DOM] Driver health check: empty URL")
                return False

            if thorough:
                # Thorough test: try to find body element (catches "Symbols not available" crashes)
                try:
                    _ = self.driver.find_element(By.TAG_NAME, "body")
                except Exception as e:
                    logger.error(f"[DOM] Driver health check: find_element failed - {e}")
                    return False

            return True
        except Exception as e:
            logger.error(f"[DOM] Driver health check failed: {e}")
            return False

    def capture_diagnostic_screenshot(self, context: str = "unknown") -> Optional[str]:
        """
        Capture a diagnostic screenshot for debugging.

        Args:
            context: Description of what was happening (e.g., "filter_click_failed")

        Returns:
            Path to screenshot file, or None if capture failed
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"diag_{context}_{timestamp}.png"
            filepath = DIAGNOSTIC_DIR / filename

            # Try to capture screenshot
            self.driver.save_screenshot(str(filepath))
            logger.info(f"[DOM] Diagnostic screenshot saved: {filepath}")
            return str(filepath)
        except Exception as e:
            logger.error(f"[DOM] Failed to capture diagnostic screenshot: {e}")
            return None

    def get_browser_state(self) -> Dict[str, Any]:
        """
        Get current browser state for debugging.

        Returns:
            Dict with URL, title, viewport size, etc.
        """
        state = {
            "timestamp": datetime.now().isoformat(),
            "healthy": False,
            "url": None,
            "title": None,
            "viewport": None,
            "error": None,
        }

        try:
            state["url"] = self.driver.current_url
            state["title"] = self.driver.title
            state["healthy"] = True

            # Get viewport info
            viewport = self.driver.execute_script("""
                return {
                    width: window.innerWidth,
                    height: window.innerHeight,
                    scrollX: window.scrollX,
                    scrollY: window.scrollY,
                    devicePixelRatio: window.devicePixelRatio
                };
            """)
            state["viewport"] = viewport

        except Exception as e:
            state["error"] = str(e)
            logger.error(f"[DOM] Failed to get browser state: {e}")

        return state

    def diagnose_failure(self, context: str, error: Exception = None) -> Dict[str, Any]:
        """
        Full diagnostic capture when an error occurs.

        Args:
            context: What was being attempted
            error: The exception that occurred

        Returns:
            Diagnostic info dict with screenshot path and browser state
        """
        logger.warning(f"[DOM] Running diagnostics for: {context}")

        diagnostic = {
            "context": context,
            "error": str(error) if error else None,
            "error_type": type(error).__name__ if error else None,
            "browser_state": self.get_browser_state(),
            "screenshot": self.capture_diagnostic_screenshot(context.replace(" ", "_")[:30]),
        }

        # Log summary
        logger.info(f"[DOM] Diagnostic summary: healthy={diagnostic['browser_state']['healthy']}, "
                   f"url={diagnostic['browser_state'].get('url', 'N/A')[:50]}, "
                   f"screenshot={diagnostic['screenshot']}")

        return diagnostic

    async def diagnose_with_ui_tars(self, question: str, screenshot_path: str = None) -> Dict[str, Any]:
        """
        Use UI-TARS vision model to analyze current browser state.

        Args:
            question: What to ask UI-TARS about the screenshot
            screenshot_path: Path to existing screenshot, or capture new one

        Returns:
            Dict with UI-TARS analysis results
        """
        try:
            from modules.infrastructure.foundups_vision.src.ui_tars_bridge import UITarsBridge

            # Capture screenshot if not provided
            if not screenshot_path:
                screenshot_path = self.capture_diagnostic_screenshot("ui_tars_analysis")

            if not screenshot_path:
                return {"error": "Could not capture screenshot for UI-TARS analysis"}

            # Initialize UI-TARS bridge
            bridge = UITarsBridge(browser_port=9222)
            await bridge.connect()

            # Execute analysis action
            result = await bridge.execute_action(
                action="verify",
                description=question,
                context={"screenshot_path": screenshot_path},
                driver=self.driver
            )

            return {
                "success": result.success,
                "analysis": result.description,
                "confidence": result.confidence,
                "screenshot": screenshot_path,
            }

        except ImportError:
            logger.warning("[DOM] UI-TARS bridge not available - skipping visual diagnosis")
            return {"error": "UI-TARS not available", "screenshot": screenshot_path}
        except Exception as e:
            logger.error(f"[DOM] UI-TARS analysis failed: {e}")
            return {"error": str(e), "screenshot": screenshot_path}

    def verify_shorts_listed(self, use_ui_tars: bool = True) -> Dict[str, Any]:
        """
        Verify if Shorts videos are visible on the page.

        Uses DOM check first (fast), falls back to UI-TARS visual verification if needed.

        Args:
            use_ui_tars: Whether to use UI-TARS for visual verification if DOM check uncertain

        Returns:
            Dict with: 'shorts_visible', 'count', 'method', 'needs_filter'
        """
        result = {
            "shorts_visible": False,
            "count": 0,
            "method": "dom",
            "needs_filter": True,
            "filter_applied": False,
            "detected_filter": None,
        }

        try:
            filter_state = self.read_visibility_filter_state()
            result["detected_filter"] = filter_state.get("detected")
            result["filter_applied"] = filter_state.get("detected") == "UNLISTED"

            # Quick DOM check first
            video_rows = self.driver.execute_script("""
                const rows = document.querySelectorAll('ytcp-video-row');
                const filterChips = document.querySelectorAll('ytcp-chip');
                let filterApplied = false;
                for (let chip of filterChips) {
                    const text = (chip.textContent || '').trim().toLowerCase();
                    if (text.includes('visibility:') && text.includes('unlisted')) {
                        filterApplied = true;
                        break;
                    }
                }
                return {
                    count: rows.length,
                    hasTable: !!document.querySelector('.video-table-content, #video-list, ytcp-video-row'),
                    filterApplied: filterApplied
                };
            """)

            if video_rows:
                result["count"] = video_rows.get("count", 0)
                result["filter_applied"] = video_rows.get("filterApplied", False)
                result["shorts_visible"] = video_rows.get("hasTable", False) and result["count"] > 0

                if result["shorts_visible"]:
                    logger.info(
                        f"[DOM] Shorts verified: {result['count']} videos visible, "
                        f"filter={result.get('detected_filter')}, unlisted_chip={result['filter_applied']}"
                    )
                    result["needs_filter"] = not result["filter_applied"]
                    return result

            # If DOM check shows no videos, optionally use UI-TARS
            if use_ui_tars and not result["shorts_visible"]:
                import asyncio
                result["method"] = "ui_tars"

                async def _check_with_ui_tars():
                    analysis = await self.diagnose_with_ui_tars(
                        "Are there any video thumbnails or video items visible in this YouTube Studio page? "
                        "Answer YES if you see video rows/thumbnails, NO if the content area is empty."
                    )
                    return analysis

                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # Already in async context
                        import concurrent.futures
                        with concurrent.futures.ThreadPoolExecutor() as pool:
                            analysis = pool.submit(asyncio.run, _check_with_ui_tars()).result(timeout=30)
                    else:
                        analysis = asyncio.run(_check_with_ui_tars())

                    if analysis and not analysis.get("error"):
                        response = (analysis.get("analysis") or "").lower()
                        result["shorts_visible"] = "yes" in response and "no" not in response[:20]
                        result["ui_tars_response"] = analysis.get("analysis", "")
                        logger.info(f"[DOM] UI-TARS verification: shorts_visible={result['shorts_visible']}")
                except Exception as e:
                    logger.warning(f"[DOM] UI-TARS verification failed: {e}")

        except Exception as e:
            logger.error(f"[DOM] Shorts verification failed: {e}")

        return result

    def wait_for_element(self, selector: str, by: str = By.CSS_SELECTOR, timeout: int = 10):
        """Wait for element to be present and visible."""
        # Thorough health check before expensive WebDriverWait (catches stale connections)
        if not self.check_driver_health(thorough=True):
            raise RuntimeError("WebDriver connection is stale or broken - cannot find elements")
        wait = WebDriverWait(self.driver, timeout)
        return wait.until(EC.visibility_of_element_located((by, selector)))

    def wait_for_clickable(self, selector: str, by: str = By.CSS_SELECTOR, timeout: int = 10):
        """Wait for element to be clickable."""
        # Thorough health check before expensive WebDriverWait
        if not self.check_driver_health(thorough=True):
            raise RuntimeError("WebDriver connection is stale or broken - cannot find elements")
        wait = WebDriverWait(self.driver, timeout)
        return wait.until(EC.element_to_be_clickable((by, selector)))

    def dismiss_youtube_notifications(self) -> bool:
        """
        Dismiss any YouTube Studio notification banners that might block content.

        Common notifications:
        - Monetization status changes
        - Policy updates
        - System announcements

        Returns:
            True if any notifications were dismissed
        """
        dismissed = False
        try:
            # Find and click all "Dismiss" buttons
            dismiss_result = self.driver.execute_script("""
                const dismissed = [];

                // Look for dismiss buttons in notification banners
                const dismissBtns = document.querySelectorAll(
                    'button[aria-label="Dismiss"], ' +
                    'ytcp-button[aria-label="Dismiss"], ' +
                    'button:contains("Dismiss"), ' +
                    '#dismiss-button, ' +
                    '.dismiss-button, ' +
                    '[data-dismiss]'
                );

                for (const btn of dismissBtns) {
                    try {
                        btn.click();
                        dismissed.push(btn.textContent || 'dismiss');
                    } catch (e) {}
                }

                // Also try clicking any visible "Dismiss" text links
                const allBtns = document.querySelectorAll('button, a, [role="button"]');
                for (const el of allBtns) {
                    const text = (el.textContent || '').trim().toLowerCase();
                    if (text === 'dismiss' || text === 'close' || text === 'got it') {
                        try {
                            el.click();
                            dismissed.push(text);
                        } catch (e) {}
                    }
                }

                return dismissed;
            """)

            if dismiss_result and len(dismiss_result) > 0:
                logger.info(f"[DOM] Dismissed {len(dismiss_result)} notification(s): {dismiss_result}")
                dismissed = True
                import time
                time.sleep(1)  # Wait for UI to update

        except Exception as e:
            logger.debug(f"[DOM] Notification dismiss check: {e}")

        return dismissed

    def _wait_for_page_content(self, timeout: int = 12, login_wait_timeout: int = 120) -> bool:
        """
        Wait for YouTube Studio page content to fully render.

        Checks for multiple indicators that the page is ready:
        - Video table (ytcp-video-row)
        - Filter bar (input with placeholder='Filter')
        - Channel content header

        If page is on Google login, waits for 012 to log in manually.

        Args:
            timeout: Maximum seconds to wait for content
            login_wait_timeout: Maximum seconds to wait for login (default 2 min)

        Returns:
            True if page content is ready

        Raises:
            TimeoutException if page doesn't load in time
        """
        import time
        start = time.time()

        # Health check first
        if not self.check_driver_health(thorough=True):
            raise RuntimeError("WebDriver connection is stale")

        # Check for login page and wait for 012 to log in
        login_start = time.time()
        while time.time() - login_start < login_wait_timeout:
            current_url = self.driver.current_url
            if 'accounts.google.com' in current_url or current_url.startswith('data:'):
                # On login page or blank page - wait for 012 to log in
                if time.time() - login_start < 5:  # Only log once initially
                    logger.info("[DOM] Login required - waiting for 012 to log in...")
                    logger.info(f"[DOM] Current URL: {current_url[:80]}...")
                time.sleep(2)
                continue
            else:
                # Not on login page - proceed
                break
        else:
            # Exceeded login wait timeout
            logger.error(f"[DOM] Login wait timeout ({login_wait_timeout}s) - still on login page")
            raise TimeoutException(f"Login not completed within {login_wait_timeout}s")

        # First, try to dismiss any blocking notifications
        self.dismiss_youtube_notifications()

        while time.time() - start < timeout:
            try:
                # Check for any of these indicators that page is ready
                indicators = self.driver.execute_script("""
                    const result = {
                        hasVideoTable: !!document.querySelector('ytcp-video-row'),
                        hasFilterBar: !!document.querySelector("input[placeholder='Filter']"),
                        hasChipBar: !!document.querySelector('ytcp-chip-bar'),
                        hasContentHeader: !!document.querySelector('.video-table-content, #video-list'),
                        pageTitle: document.title || ''
                    };
                    // Page is ready if we have video table OR filter bar
                    result.ready = result.hasVideoTable || result.hasFilterBar || result.hasChipBar;
                    return result;
                """)

                if indicators and indicators.get('ready'):
                    logger.info(f"[DOM] Page content ready: table={indicators.get('hasVideoTable')}, "
                               f"filter={indicators.get('hasFilterBar')}, chips={indicators.get('hasChipBar')}")
                    return True

                # Log what we're still waiting for
                logger.debug(f"[DOM] Waiting for content... {indicators}")

            except Exception as e:
                logger.warning(f"[DOM] Page content check error: {e}")

            time.sleep(0.5)

        # Timeout - capture diagnostic and raise
        self.diagnose_failure("page_content_timeout")
        raise TimeoutException(f"Page content did not load within {timeout}s")

    def safe_click(self, element, use_js: bool = False):
        """
        012-modeled click (slow + deterministic) with robust fallbacks.

        Args:
            element: WebElement to click
            use_js: Force JavaScript click
        """
        import time
        try:
            if use_js:
                self.driver.execute_script("arguments[0].click();", element)
            else:
                try:
                    self.driver.execute_script(
                        "arguments[0].scrollIntoView({block:'center', inline:'center'});",
                        element,
                    )
                except Exception:
                    pass
                time.sleep(self._pre_click_delay)
                element.click()
                time.sleep(self._post_click_delay)
        except Exception:
            # Fallback order: ActionChains (often works on custom elements) -> JS click
            try:
                time.sleep(self._pre_click_delay)
                ActionChains(self.driver).move_to_element(element).click().perform()
                time.sleep(self._post_click_delay)
            except Exception:
                try:
                    self.driver.execute_script("arguments[0].click();", element)
                    time.sleep(self._post_click_delay)
                except Exception:
                    raise

    def _focus_and_select_all_input(self, el) -> None:
        """
        Ensure an <input> has focus and its entire value is selected.
        This prevents Ctrl+A being applied to the wrong surface (e.g., the page).
        """
        import time
        try:
            self.safe_click(el)
        except Exception:
            try:
                el.click()
            except Exception:
                pass
        time.sleep(0.2)
        try:
            self.driver.execute_script(
                """
                const el = arguments[0];
                if (!el) return false;
                try { el.focus(); } catch (e) {}
                try {
                  const v = el.value || '';
                  if (typeof el.setSelectionRange === 'function') {
                    el.setSelectionRange(0, v.length);
                    return true;
                  }
                } catch (e) {}
                return false;
                """,
                el,
            )
        except Exception:
            pass
        try:
            # Keyboard fallback if setSelectionRange isn't available.
            ActionChains(self.driver).key_down(Keys.CONTROL).send_keys("a").key_up(Keys.CONTROL).perform()
        except Exception:
            pass
        time.sleep(0.2)

    def human_delay(self, base: float = 0.5, variance: float = 0.3) -> float:
        """Return randomized delay for human-like behavior."""
        import random
        return base + random.uniform(-variance, variance)

    async def async_sleep(self, seconds: float):
        """Async sleep for non-blocking waits."""
        await asyncio.sleep(seconds)

    # =========================================
    # OOPS PAGE / ACCOUNT RECOVERY METHODS
    # =========================================

    # Channel ID to account name mapping (for account switching)
    CHANNEL_ACCOUNT_MAP = {
        # Chrome channels (port 9222)
        "UC-LSSlOZwpGIRIYihaz8zCw": "Move2Japan",      # M2J
        "UCfHM9Fw9HD-NwiS0seD_oIA": "UnDaoDu",         # UnDaoDu
        # Edge channels (port 9223)
        "UCSNTUXjAgpd4sgWYP0xoJgw": "FoundUps",        # FoundUps
        "UCVSmg5aOhP4tnQ9KFUg97qA": "antifaFM",    # antifaFM
    }

    def detect_oops_page(self) -> bool:
        """
        Detect if current page is the "oops" error page (wrong account).

        Returns:
            True if oops page detected, False otherwise
        """
        try:
            # Check for "Switch account" link on oops page
            switch_link = self.driver.find_elements(By.CSS_SELECTOR, self.selectors.OOPS_SWITCH_ACCOUNT)
            if switch_link:
                logger.warning("[OOPS] Detected oops page - wrong account logged in")
                return True
            # Fallback: text-based detection (handles updated Studio UI)
            text = self.driver.execute_script(
                "return (document.body && document.body.innerText) || '';"
            )
            norm = (text or "").lower().replace("\u2019", "'")
            if ("don't have permission" in norm
                    or "dont have permission" in norm
                    or "do not have permission" in norm
                    or "permission to view this page" in norm
                    or "switch account" in norm
                    or "return to studio" in norm):
                logger.warning("[OOPS] Detected oops page via text match")
                return True
            return False
        except Exception as e:
            logger.debug(f"[OOPS] Detection check failed: {e}")
            return False

    def _click_oops_switch_account(self) -> bool:
        """Click the 'Switch account' button on the OOPS page using broad selectors.

        2026-02-04: Also removes target="_blank" and rewrites ?next= to prevent redirect loop.
        """
        try:
            return bool(self.driver.execute_script("""
                const candidates = [...document.querySelectorAll(
                    'button, ytcp-button, a, [role="button"], tp-yt-paper-button, yt-button-renderer'
                )];
                for (const el of candidates) {
                    const text = (el.textContent || '').trim().toLowerCase();
                    if (text.includes('switch account') || text.includes('switch acct')) {
                        el.removeAttribute('target');
                        var href = el.getAttribute('href') || '';
                        if (href.includes('channel_switcher')) {
                            var url = new URL(href, window.location.origin);
                            url.searchParams.set('next', 'https://studio.youtube.com/');
                            el.setAttribute('href', url.toString());
                        }
                        el.click();
                        return true;
                    }
                }
                return false;
            """))
        except Exception:
            return False

    def get_target_channel_name(self, channel_id: str) -> Optional[str]:
        """
        Get the account/channel name for a channel ID.

        Args:
            channel_id: YouTube channel ID

        Returns:
            Account name string or None if not mapped
        """
        return self.CHANNEL_ACCOUNT_MAP.get(channel_id)

    def handle_oops_page(self, target_channel_id: str, max_retries: int = 2) -> bool:
        """
        Handle oops page by switching to the correct account.

        Flow:
            1. Detect oops page
            2. Click "Switch account" link
            3. On YouTube page, click avatar button
            4. Click "Switch account" in menu
            5. Select the correct account from list
            6. Navigate back to target channel

        Args:
            target_channel_id: The channel ID we're trying to access
            max_retries: Maximum retry attempts

        Returns:
            True if successfully recovered, False otherwise
        """
        import time

        if not self.detect_oops_page():
            logger.debug("[OOPS] No oops page detected - proceeding normally")
            return True

        target_name = self.get_target_channel_name(target_channel_id)
        if not target_name:
            logger.error(f"[OOPS] No account mapping for channel {target_channel_id}")
            return False

        logger.info(f"[OOPS] Attempting recovery - switching to account: {target_name}")

        # 2026-02-03: Emit OOPS breadcrumb to orchestration switchboard
        _emit_oops_signal("oops_page_detected", channel_name=target_name,
                          channel_id=target_channel_id, browser="edge")

        for attempt in range(max_retries):
            try:
                # Step 1: Click "Switch account" on oops page
                # 2026-02-04: CRITICAL fix from live DOM inspection via --chrome:
                # The "Switch account" link has target="_blank" which opens a new tab.
                # Must remove it first so navigation stays in same tab for Selenium.
                switch_clicked = False
                try:
                    switch_link = self.wait_for_clickable(
                        self.selectors.OOPS_SWITCH_ACCOUNT,
                        timeout=5
                    )
                    # Remove target="_blank" to prevent new tab (confirmed via live DOM 2026-02-04)
                    # AND rewrite ?next= to Studio root to prevent redirect loop (2026-02-04)
                    self.driver.execute_script("""
                        arguments[0].removeAttribute('target');
                        var href = arguments[0].getAttribute('href') || '';
                        if (href.includes('channel_switcher')) {
                            var url = new URL(href, window.location.origin);
                            url.searchParams.set('next', 'https://studio.youtube.com/');
                            arguments[0].setAttribute('href', url.toString());
                        }
                    """, switch_link)
                    self.safe_click(switch_link)
                    switch_clicked = True
                except Exception:
                    switch_clicked = self._click_oops_switch_account()
                if not switch_clicked:
                    logger.warning("[OOPS] Could not click 'Switch account' button")
                    return False
                time.sleep(2)  # Wait for navigation

                # Step 2: On YouTube channel switcher, click avatar button
                try:
                    avatar_btn = self.wait_for_clickable(
                        self.selectors.CHANNEL_SWITCHER_AVATAR,
                        timeout=5
                    )
                    self.safe_click(avatar_btn)
                    time.sleep(1)
                except TimeoutException:
                    logger.debug("[OOPS] Avatar button not found - may already be in account list")

                # Step 3: Click "Switch account" in menu popup
                try:
                    switch_menu = self.wait_for_clickable(
                        self.selectors.SWITCH_ACCOUNT_MENU_XPATH,
                        by=By.XPATH,
                        timeout=5
                    )
                    self.safe_click(switch_menu)
                    time.sleep(1.5)
                except TimeoutException:
                    logger.debug("[OOPS] Switch account menu item not found - may already be in account list")

                # Step 4: Find and click the target account
                account_xpath = self.selectors.ACCOUNT_ITEM_BY_NAME_TEMPLATE.format(
                    channel_name=target_name
                )
                try:
                    target_account = self.wait_for_clickable(
                        account_xpath,
                        by=By.XPATH,
                        timeout=5
                    )
                    self.safe_click(target_account)
                    time.sleep(2)  # Wait for account switch
                except TimeoutException:
                    logger.warning(f"[OOPS] Account '{target_name}' not found in account list")
                    # Try listing available accounts
                    self._log_available_accounts()
                    continue

                # Step 5: Navigate to target YouTube Studio channel
                target_url = f"https://studio.youtube.com/channel/{target_channel_id}/videos/short"
                logger.info(f"[OOPS] Navigating to target channel: {target_url}")
                self.driver.get(target_url)
                time.sleep(2)

                # Verify we're no longer on oops page
                if not self.detect_oops_page():
                    logger.info(f"[OOPS] Successfully recovered - now on correct account")
                    _emit_oops_signal("oops_page_recovered", channel_name=target_name,
                                      channel_id=target_channel_id, recovery_method="account_switch")
                    return True
                else:
                    logger.warning(f"[OOPS] Still on oops page after attempt {attempt + 1}")

            except Exception as e:
                logger.error(f"[OOPS] Recovery attempt {attempt + 1} failed: {e}")

        logger.error(f"[OOPS] Failed to recover after {max_retries} attempts")
        _emit_oops_signal("oops_page_detected", channel_name=target_name,
                          channel_id=target_channel_id, browser="edge",
                          attempt_count=max_retries, recovery_failed=True)
        return False

    def _log_available_accounts(self):
        """Log available accounts in the account list for debugging."""
        try:
            accounts = self.driver.find_elements(By.XPATH, self.selectors.CHANNEL_LIST_ITEM)
            if accounts:
                logger.info(f"[OOPS] Found {len(accounts)} accounts in list:")
                for acc in accounts:
                    try:
                        name_el = acc.find_element(By.XPATH, self.selectors.CHANNEL_NAME_IN_LIST)
                        logger.info(f"[OOPS]   - {name_el.text}")
                    except Exception:
                        pass
        except Exception as e:
            logger.debug(f"[OOPS] Could not list accounts: {e}")

    def navigate_with_oops_recovery(
        self,
        channel_id: str,
        target_url: str,
        max_oops_retries: int = 2
    ) -> bool:
        """
        Navigate to URL with automatic oops page recovery.

        Args:
            channel_id: Target channel ID
            target_url: URL to navigate to
            max_oops_retries: Max recovery attempts

        Returns:
            True if navigation successful, False otherwise
        """
        import time

        logger.info(f"[NAV] Navigating to: {target_url[:80]}...")
        self.driver.get(target_url)
        time.sleep(2)

        # Check for oops page and recover if needed
        if self.detect_oops_page():
            if not self.handle_oops_page(channel_id, max_oops_retries):
                return False

        return True

    # =========================================
    # PAGE 1: SHORTS LIST METHODS
    # =========================================

    def _visibility_checkbox_label(self, visibility: str) -> str:
        """Studio checkbox label for a visibility filter key (e.g. SCHEDULED -> Has schedule)."""
        key = (visibility or "UNLISTED").upper()
        return VISIBILITY_CHECKBOX_LABELS.get(key, key.capitalize())

    def read_visibility_filter_state(self) -> Dict[str, Any]:
        """
        Read current Shorts list visibility filter from chip text and URL.

        Returns dict with keys: active, chip_texts, url, detected, wrong_for_unlisted.
        """
        try:
            raw = self.driver.execute_script("""
                const chips = document.querySelectorAll('ytcp-chip');
                const texts = [];
                for (let chip of chips) {
                    const text = (chip.textContent || '').trim();
                    if (text && text.toLowerCase().includes('visibility')) {
                        texts.push(text);
                    }
                }
                return { chipTexts: texts, url: window.location.href || '' };
            """) or {}
        except Exception as exc:
            logger.warning(f"[DOM] Could not read visibility filter state: {exc}")
            raw = {"chipTexts": [], "url": ""}

        chip_texts = raw.get("chipTexts") or []
        url = raw.get("url") or ""
        chip_blob = " | ".join(chip_texts)
        detected = classify_visibility_filter(chip_blob, url)

        return {
            "active": bool(chip_texts) or ("UNLISTED" in url.upper() and "filter=" in url),
            "chip_texts": chip_texts,
            "url": url,
            "detected": detected,
            "wrong_for_unlisted": detected is not None and detected != "UNLISTED",
        }

    def verify_visibility_filter(self, visibility: str = "UNLISTED") -> bool:
        """True only when the requested visibility filter is confirmed (chip or URL)."""
        target = (visibility or "UNLISTED").upper()
        state = self.read_visibility_filter_state()

        # Reject wrong filter even if URL looks ambiguous
        detected = state.get("detected")
        if detected and detected != target and detected != "UNKNOWN":
            return False

        if detected == target:
            return True

        url = (state.get("url") or "").upper()
        if "FILTER=" in url:
            markers = VISIBILITY_CHIP_MARKERS.get(target, (target.lower(),))
            if any(m.upper() in url for m in markers):
                # URL says UNLISTED but chip says Scheduled — trust chip over URL
                if target == "UNLISTED" and state.get("wrong_for_unlisted"):
                    return False
                return True
        return False

    def _clear_visibility_filter_chips(self) -> bool:
        """Remove active visibility filter chips (e.g. Has schedule) before switching to Unlisted."""
        import time
        try:
            cleared = self.driver.execute_script("""
                let removed = 0;
                const chips = document.querySelectorAll('ytcp-chip');
                for (const chip of chips) {
                    const text = (chip.textContent || '').trim().toLowerCase();
                    if (!text.includes('visibility') && !text.includes('schedule') && !text.includes('unlisted')) {
                        continue;
                    }
                    const close = chip.querySelector(
                        'ytcp-icon-button, tp-yt-iron-icon, button[aria-label*="Remove"], ' +
                        'button[aria-label*="Clear"], #remove-icon-button, [id*="remove"]'
                    );
                    if (close) {
                        close.click();
                        removed += 1;
                    }
                }
                return removed;
            """)
            if cleared:
                logger.info(f"[DOM] Cleared {cleared} visibility filter chip(s)")
                time.sleep(1.0)
            return bool(cleared)
        except Exception as exc:
            logger.warning(f"[DOM] Could not clear visibility chips: {exc}")
            return False

    def _uncheck_other_visibility_checkboxes(self, keep_label: str) -> None:
        """In the filter dialog, uncheck visibility options other than keep_label."""
        import time
        try:
            self.driver.execute_script(
                """
                const keep = (arguments[0] || '').toLowerCase();
                const dialog = document.querySelector('ytcp-filter-dialog');
                if (!dialog) return;
                const labels = ['Unlisted', 'Has schedule', 'Public', 'Private', 'Draft', 'Members'];
                for (const label of labels) {
                    if (label.toLowerCase() === keep) continue;
                    const spans = dialog.querySelectorAll('span');
                    for (const span of spans) {
                        if ((span.textContent || '').trim() !== label) continue;
                        let current = span.parentElement;
                        for (let i = 0; i < 10 && current; i++) {
                            const cb = current.querySelector('ytcp-checkbox-lit');
                            if (cb && (cb.hasAttribute('checked') || cb.checked === true)) {
                                cb.click();
                            }
                            current = current.parentElement;
                        }
                    }
                }
                """,
                keep_label,
            )
            time.sleep(0.5)
        except Exception as exc:
            logger.debug(f"[DOM] Uncheck other visibility filters skipped: {exc}")

    def _visibility_chip_matches(self, visibility_label: str) -> bool:
        """True if list page shows the expected visibility filter chip."""
        label = (visibility_label or "Unlisted").lower()
        try:
            return bool(
                self.driver.execute_script(
                    """
                    const want = (arguments[0] || '').toLowerCase();
                    const chips = document.querySelectorAll('ytcp-chip');
                    for (const chip of chips) {
                        const text = (chip.textContent || '').trim().toLowerCase();
                        if (!text) continue;
                        if (text.includes('visibility') && text.includes(want)) return true;
                        if (want === 'unlisted' && text.includes('unlisted')) return true;
                        if (want === 'has schedule' && (text.includes('has schedule') || text.includes('scheduled'))) return true;
                    }
                    return false;
                    """,
                    visibility_label,
                )
            )
        except Exception:
            return False

    def read_edit_page_visibility(self) -> str:
        """
        Read current video visibility on the Studio edit page.

        Returns: unlisted, scheduled, public, private, draft, or unknown
        """
        try:
            raw = (
                self.driver.execute_script(
                    """
                    const selectors = [
                        '#visibility-text',
                        '#visibility-status-span',
                        'ytcp-video-metadata-visibility #select-button',
                        'button[aria-label="Edit video visibility status"]',
                    ];
                    for (const sel of selectors) {
                        const el = document.querySelector(sel);
                        if (el && el.textContent) return el.textContent.trim().toLowerCase();
                    }
                    return '';
                    """
                )
                or ""
            )
        except Exception:
            raw = ""

        if "scheduled" in raw or "has schedule" in raw:
            return "scheduled"
        if "unlisted" in raw:
            return "unlisted"
        if "private" in raw:
            return "private"
        if "public" in raw:
            return "public"
        if "draft" in raw:
            return "draft"
        return "unknown"

    def ensure_visibility_filter(self, visibility: str = "UNLISTED", channel_id: Optional[str] = None) -> bool:
        """
        Enforce list filter before scraping or scheduling.

        When Scheduled (or any non-target filter) is active, unlisted rows are invisible
        and F5 refresh does not fix it — must re-apply Unlisted explicitly.
        """
        target = (visibility or "UNLISTED").upper()
        state = self.read_visibility_filter_state()

        if self.verify_visibility_filter(target):
            logger.info(f"[DOM] Visibility filter OK: {target} ({state.get('chip_texts') or 'URL param'})")
            return True

        if state.get("wrong_for_unlisted") or (
            state.get("detected") and state.get("detected") != target
        ):
            logger.warning(
                f"[DOM] Wrong visibility filter active: detected={state.get('detected')} "
                f"chips={state.get('chip_texts')} — clearing and re-applying {target}"
            )
            self._clear_visibility_filter_chips()

        cid = channel_id or self._last_shorts_channel_id
        if cid:
            if self._navigate_shorts_with_url_filter(cid, target):
                if self.verify_visibility_filter(target):
                    self.sort_by_date_oldest()
                    return True

        if cid:
            return self.navigate_to_shorts_with_fallback(cid, target, use_ui_tars=False)

        logger.error(f"[DOM] Cannot enforce {target} filter — channel_id unknown")
        return False

    def _navigate_shorts_with_url_filter(self, channel_id: str, visibility: str) -> bool:
        """Navigate using encoded Studio URL filter (reliable reset from wrong filter state)."""
        import time
        from .channel_config import build_studio_url

        target = (visibility or "UNLISTED").upper()
        url = build_studio_url(channel_id, "short", target)
        logger.info(f"[DOM] URL filter navigation → {target}: {url[:90]}...")
        self.driver.get(url)

        for attempt in range(3):
            try:
                self._wait_for_page_content(timeout=15, login_wait_timeout=120)
            except Exception as exc:
                logger.warning(f"[DOM] URL filter page not ready (attempt {attempt + 1}/3): {exc}")
                if attempt < 2:
                    self.driver.refresh()
                    time.sleep(2)
                continue

            if self.verify_visibility_filter(target):
                logger.info(f"[DOM] URL filter navigation confirmed: {target}")
                return True

            # Chip may lag behind URL on Edge — brief wait and re-check
            time.sleep(1.5)
            if self.verify_visibility_filter(target):
                logger.info(f"[DOM] URL filter confirmed after chip lag: {target}")
                return True

        state = self.read_visibility_filter_state()
        logger.warning(
            f"[DOM] URL filter navigation did not confirm {target}: "
            f"detected={state.get('detected')} chips={state.get('chip_texts')}"
        )
        return False

    def navigate_to_shorts(self, channel_id: str, visibility: Optional[str] = None):
        """
        Navigate to Shorts list with optional visibility filter.

        Args:
            channel_id: YouTube channel ID
            visibility: "UNLISTED", "SCHEDULED", "PUBLIC", or None
        """
        from .channel_config import build_studio_url
        url = build_studio_url(channel_id, "short", visibility)
        logger.info(f"[DOM] Navigating to: {url[:80]}...")
        self.driver.get(url)
        self.wait_for_element(self.selectors.VIDEO_TABLE)

    def navigate_to_shorts_with_fallback(
        self,
        channel_id: str,
        visibility: str = "UNLISTED",
        use_ui_tars: bool = True
    ) -> bool:
        """
        Navigate to Shorts with visibility filter using UI-TARS verification.

        Flow (0102-modeled):
        1. Navigate to shorts page (no filter URL params)
        2. UI-TARS verify page loaded
        3. Check if filter already applied (via DOM)
        4. If not filtered -> click Filter -> Visibility -> Unlisted -> Apply
        5. UI-TARS verify filter was applied

        Args:
            channel_id: YouTube channel ID
            visibility: "UNLISTED", "SCHEDULED", "PUBLIC", "PRIVATE"
            use_ui_tars: Use UI-TARS for visual verification (default True)

        Returns:
            True if filter successfully applied, False otherwise
        """
        import time

        target = (visibility or "UNLISTED").upper()
        self._last_shorts_channel_id = channel_id
        visibility_label = self._visibility_checkbox_label(target)

        # Step 1: URL filter first for UNLISTED — clears stale Scheduled/Has schedule views.
        # Refresh (F5) on Scheduled does NOT expose unlisted rows; URL reset is required.
        url_first = os.getenv("YT_SCHEDULER_URL_FILTER_FIRST", "true").lower() in ("1", "true", "yes")
        if target == "UNLISTED" and url_first:
            if self._navigate_shorts_with_url_filter(channel_id, target):
                self.sort_by_date_oldest()
                return True
            logger.warning("[DOM] URL-first UNLISTED failed — falling back to base page + DOM clicks")

        # Step 2: Navigate to base shorts page (DOM fallback)
        base_url = f"https://studio.youtube.com/channel/{channel_id}/videos/short"
        logger.info(f"[DOM] Step 1: Navigating to shorts page: {base_url[:60]}...")
        self.driver.get(base_url)

        # Step 3: Wait for page to load (with login wait if needed)
        page_ready = False
        for attempt in range(3):
            try:
                self._wait_for_page_content(timeout=15, login_wait_timeout=120)
                page_ready = True
                break
            except Exception as e:
                logger.warning(f"[DOM] Page content not ready (attempt {attempt + 1}/3): {e}")
                if attempt < 2:
                    logger.info("[DOM] Refreshing page...")
                    self.driver.refresh()
                    time.sleep(2)

        if not page_ready:
            logger.error("[DOM] Page failed to load after 3 attempts")
            self.diagnose_failure("page_load_failed")
            return False

        # Step 4: Reject wrong filter (e.g. Scheduled on antifaFM) before proceeding
        state = self.read_visibility_filter_state()
        if target == "UNLISTED" and state.get("wrong_for_unlisted"):
            logger.warning(
                f"[DOM] Wrong filter on Shorts list: {state.get('detected')} "
                f"chips={state.get('chip_texts')} — clearing chips + UNLISTED URL reset"
            )
            self._clear_visibility_filter_chips()
            if self._navigate_shorts_with_url_filter(channel_id, target):
                self.sort_by_date_oldest()
                return True

        # Step 5: UI-TARS verify page loaded (optional)
        if use_ui_tars:
            logger.info("[DOM] Step 2: UI-TARS verification - checking if page loaded...")
            verification = self.verify_shorts_listed(use_ui_tars=True)
            if not verification.get("shorts_visible") and verification.get("count", 0) == 0:
                logger.warning(
                    f"[DOM] UI-TARS: No shorts visible. "
                    f"filter={verification.get('detected_filter')} "
                    f"Response: {verification.get('ui_tars_response', 'N/A')[:100]}"
                )

        # Step 6: Check if correct filter already applied
        if self.verify_visibility_filter(target):
            chip_text = (state.get("chip_texts") or ["URL/param"])[0]
            logger.info(f"[DOM] Filter already applied: {target} ({chip_text})")
            self.sort_by_date_oldest()
            return True

        # Step 7: Apply filter via DOM clicking
        logger.info(f"[DOM] Step 3: Applying {target} filter via UI clicks...")
        filter_applied = self._apply_filter_via_dom(target)

        if not filter_applied:
            logger.error(f"[DOM] Failed to apply {target} filter via UI")
            self.diagnose_failure("dom_filter_failed")
            if target == "UNLISTED" and url_first:
                logger.info("[DOM] DOM filter failed — retrying UNLISTED URL navigation")
                if self._navigate_shorts_with_url_filter(channel_id, target):
                    self.sort_by_date_oldest()
                    return True
            return False

        # Step 8: UI-TARS verify filter was applied (optional)
        if use_ui_tars:
            logger.info("[DOM] Step 4: UI-TARS verification - checking filter applied...")
            time.sleep(1)

            if self.verify_visibility_filter(target):
                logger.info(f"[DOM] UI-TARS verified: {target} filter applied")
                self.sort_by_date_oldest()
                return True
            else:
                import asyncio
                try:
                    async def _verify_filter():
                        return await self.diagnose_with_ui_tars(
                            f"Is there a filter chip showing 'Visibility: {visibility_label}' "
                            f"visible on this YouTube Studio page? Answer YES or NO."
                        )

                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        import concurrent.futures
                        with concurrent.futures.ThreadPoolExecutor() as pool:
                            analysis = pool.submit(asyncio.run, _verify_filter()).result(timeout=30)
                    else:
                        analysis = asyncio.run(_verify_filter())

                    if analysis and not analysis.get("error"):
                        response = (analysis.get("analysis") or "").lower()
                        if "yes" in response:
                            logger.info("[DOM] UI-TARS confirmed filter applied")
                            self.sort_by_date_oldest()
                            return True
                        logger.warning(f"[DOM] UI-TARS says filter NOT applied: {response[:100]}")
                except Exception as e:
                    logger.warning(f"[DOM] UI-TARS final verification failed: {e}")

        # Strict gate: must confirm target filter (never accept Scheduled when UNLISTED requested)
        if self.verify_visibility_filter(target):
            self.sort_by_date_oldest()
            return True

        wrong = self.read_visibility_filter_state()
        logger.error(
            f"[DOM] Filter verification failed for {target}: "
            f"detected={wrong.get('detected')} chips={wrong.get('chip_texts')}"
        )
        self.diagnose_failure("wrong_visibility_filter")
        return False

    def _click_viewport_point(self, x: int, y: int) -> None:
        """
        Click a viewport coordinate reliably.
        Uses ActionChains with element offset to avoid mouse drift from move_by_offset().
        """
        body = self.driver.find_element(By.TAG_NAME, "body")
        ActionChains(self.driver).move_to_element_with_offset(body, x, y).click().perform()

    def _open_filter_ui(self) -> bool:
        """
        Open the filter UI on the Shorts list page.

        YouTube Studio UI changes frequently; do not rely on a single selector.

        2026-02-25 FIX: After clicking, move mouse INTO dropdown area to keep it open.
        Edge browser closes hover-dependent dropdowns faster than Chrome.
        """
        selectors = [
            "input#text-input[placeholder='Filter']",
            "input[placeholder='Filter']",
            "ytcp-chip-bar input#text-input",
            "#text-input[placeholder='Filter']",
        ]

        clicked = False
        click_element = None

        for sel in selectors:
            try:
                elem = WebDriverWait(self.driver, 3).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, sel))
                )
                if elem and elem.is_displayed():
                    self.safe_click(elem)
                    click_element = elem
                    clicked = True
                    break
            except Exception:
                continue

        # Fallback 1: click known toolbar coords (from module ModLog ADR-008)
        if not clicked:
            try:
                x, y = self.selectors.FILTER_ICON_COORDS
                self._click_viewport_point(int(x), int(y))
                clicked = True
            except Exception:
                pass

        # Fallback 2: JS click element under point (sometimes enough to open dropdown)
        if not clicked:
            try:
                x, y = self.selectors.FILTER_ICON_COORDS
                self.driver.execute_script(
                    "const el = document.elementFromPoint(arguments[0], arguments[1]); if (el) el.click();",
                    int(x), int(y)
                )
                clicked = True
            except Exception:
                return False

        # 2026-02-25: HOVER FIX - Move mouse into dropdown area to keep it open
        # Edge browser closes hover-dependent menus faster than Chrome.
        # The dropdown appears ~80px below the filter button.
        if clicked:
            try:
                import time
                time.sleep(0.3)  # Let dropdown start rendering
                actions = ActionChains(self.driver)
                if click_element:
                    # Move from clicked element down into dropdown
                    actions.move_to_element_with_offset(click_element, 0, 80).perform()
                else:
                    # Move from filter coords down into dropdown area
                    x, y = self.selectors.FILTER_ICON_COORDS
                    body = self.driver.find_element(By.TAG_NAME, "body")
                    actions.move_to_element_with_offset(body, int(x), int(y) + 80).perform()
                logger.debug("[DOM] Moved mouse into dropdown area to keep it open")
            except Exception as e:
                logger.debug(f"[DOM] Hover move failed (non-critical): {e}")

        return clicked

    def _apply_filter_via_dom(self, visibility: str = "UNLISTED") -> bool:
        """
        Apply visibility filter by clicking through the filter UI.

        Fallback method when URL-based filtering fails.

        Key Findings (ADR-005, ADR-006, ADR-007):
        - Visibility item needs test-id selector
        - Dialog must be force-opened after clicking Visibility
        - Checkboxes need ActionChains coordinate clicks (not JS .click())

        Args:
            visibility: "UNLISTED", "SCHEDULED", "PUBLIC", "PRIVATE"

        Returns:
            True if successful
        """
        import time
        from selenium.webdriver.common.action_chains import ActionChains
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC

        try:
            logger.info(f"[DOM] Applying {visibility} filter via UI interaction")

            # Step 1: Open filter UI (multi-selector + coords fallback)
            # 2026-01-30 HARDENED: Retry loop — Edge renders dropdown slower than Chrome.
            # Without retry, the Visibility menu item isn't in the DOM yet on Edge,
            # causing navigate_to_shorts_with_fallback to refresh-loop endlessly.
            logger.info("[DOM] Step 1: Opening filter UI...")
            if not self._open_filter_ui():
                logger.error("[DOM] Could not open filter UI (no filter input/button found)")
                return False

            # Step 2: Click Visibility menu item with RETRY + increasing wait
            # Edge shadow-DOM can take 800-1500ms to render the dropdown;
            # Chrome finishes in ~300ms.  Retry up to 3 times with longer waits.
            visibility_result = {"success": False}
            MAX_VISIBILITY_RETRIES = 3
            VISIBILITY_WAIT_SECS = [1.5, 2.5, 4.0]  # Increasing back-off

            for vis_attempt in range(MAX_VISIBILITY_RETRIES):
                wait_sec = VISIBILITY_WAIT_SECS[vis_attempt]
                logger.info(f"[DOM] Step 2: Waiting {wait_sec}s for Visibility menu (attempt {vis_attempt + 1}/{MAX_VISIBILITY_RETRIES})...")
                time.sleep(wait_sec)

                # Check if dropdown/listbox is actually visible before scanning
                dropdown_visible = self.driver.execute_script("""
                    const listbox = document.querySelector('tp-yt-paper-listbox[role="listbox"]');
                    if (listbox && listbox.offsetParent !== null) return true;
                    // Also check for any visible menu items
                    const items = document.querySelectorAll('tp-yt-paper-item');
                    for (let item of items) {
                        if (item.offsetParent !== null) return true;
                    }
                    return false;
                """)
                if not dropdown_visible:
                    logger.warning(f"[DOM] Dropdown not visible yet (attempt {vis_attempt + 1})")
                    if vis_attempt < MAX_VISIBILITY_RETRIES - 1:
                        # Re-click filter to try opening the dropdown again
                        logger.info("[DOM] Re-clicking filter UI to open dropdown...")
                        self._open_filter_ui()
                    continue

                # Dropdown is visible — scan for Visibility item
                try:
                    visibility_result = self.driver.execute_script("""
                        const tryClick = (el) => {
                            try { el.click(); return true; } catch (e) { return false; }
                        };

                        // 1) listbox menu
                        const listbox = document.querySelector('tp-yt-paper-listbox[role="listbox"]');
                        if (listbox) {
                            const items = listbox.querySelectorAll('tp-yt-paper-item, [role="option"], *');
                            for (let item of items) {
                                const text = (item.textContent || '').trim();
                                if (!text) continue;
                                if (item.offsetParent === null) continue;
                                if (text.toLowerCase() === 'visibility' || text.toLowerCase().includes('visibility')) {
                                    if (tryClick(item)) return {success: true, method: 'listbox'};
                                }
                            }
                        }

                        // 2) test-id hooks
                        const testItem = document.querySelector('[test-id*="VISIBILITY"]');
                        if (testItem && testItem.offsetParent !== null) {
                            if (tryClick(testItem)) return {success: true, method: 'test-id'};
                        }

                        // 3) deep visible text scan (last resort)
                        const all = document.querySelectorAll('*');
                        for (let el of all) {
                            if (el.offsetParent === null) continue;
                            if (el.children && el.children.length > 0) continue;
                            const text = (el.textContent || '').trim();
                            if (text === 'Visibility') {
                                if (tryClick(el)) return {success: true, method: 'deep-text'};
                            }
                        }

                        return {success: false};
                    """)
                except Exception:
                    visibility_result = {"success": False}

                if visibility_result.get('success'):
                    logger.info(f"[DOM] Visibility clicked via {visibility_result.get('method')} (attempt {vis_attempt + 1})")
                    break

                # Fallback: explicit XPath
                try:
                    item = WebDriverWait(self.driver, 4).until(
                        EC.element_to_be_clickable((By.XPATH, self.selectors.VISIBILITY_MENU_ITEM_XPATH))
                    )
                    item.click()
                    visibility_result = {"success": True, "method": "xpath"}
                    logger.info(f"[DOM] Visibility clicked via xpath (attempt {vis_attempt + 1})")
                    break
                except Exception:
                    visibility_result = {"success": False}

                if vis_attempt < MAX_VISIBILITY_RETRIES - 1:
                    logger.warning(f"[DOM] Visibility not found/clickable, will retry...")
                    # Press ESC to close any partial dropdown, then re-open
                    try:
                        self.driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
                        time.sleep(0.5)
                        self._open_filter_ui()
                    except Exception:
                        pass

            if not visibility_result.get('success'):
                logger.error("[DOM] Visibility menu item not found/clickable")
                return False
            time.sleep(0.5)

            # Step 3: Wait for dialog to open — HARDENED for Edge (2026-01-30)
            # Edge can take 1.5-3s for the filter dialog to render after clicking
            # Visibility.  Retry with increasing back-off + force-open fallback.
            DIALOG_MAX_RETRIES = 3
            DIALOG_WAIT_SECS = [2.0, 3.5, 5.0]
            dialog_open = False

            for dlg_attempt in range(DIALOG_MAX_RETRIES):
                wait_sec = DIALOG_WAIT_SECS[dlg_attempt]
                logger.info(f"[DOM] Step 3: Waiting {wait_sec}s for filter dialog (attempt {dlg_attempt + 1}/{DIALOG_MAX_RETRIES})...")
                try:
                    dialog_open = WebDriverWait(self.driver, wait_sec).until(lambda d: d.execute_script("""
                        const dialog = document.querySelector('ytcp-filter-dialog #dialog');
                        if (!dialog) return false;
                        const style = window.getComputedStyle(dialog);
                        return style && style.display !== 'none' && dialog.getAttribute('aria-hidden') !== 'true';
                    """))
                except Exception:
                    dialog_open = False

                if dialog_open:
                    logger.info(f"[DOM] Filter dialog confirmed open (attempt {dlg_attempt + 1})")
                    break

                # Force-open fallback (ADR-007)
                logger.warning(f"[DOM] Dialog not open yet (attempt {dlg_attempt + 1}), force-opening...")
                try:
                    self.driver.execute_script("""
                        const filterDialog = document.querySelector('ytcp-filter-dialog');
                        if (!filterDialog) return;
                        const paperDialog = filterDialog.querySelector('#dialog');
                        if (!paperDialog) return;
                        paperDialog.opened = true;
                        paperDialog.setAttribute('opened', '');
                        paperDialog.removeAttribute('aria-hidden');
                        paperDialog.style.display = 'block';
                    """)
                except Exception:
                    pass
                time.sleep(0.8)

                # Verify force-open worked
                try:
                    dialog_open = self.driver.execute_script("""
                        const dialog = document.querySelector('ytcp-filter-dialog #dialog');
                        if (!dialog) return false;
                        const style = window.getComputedStyle(dialog);
                        return style && style.display !== 'none' && dialog.getAttribute('aria-hidden') !== 'true';
                    """)
                except Exception:
                    dialog_open = False

                if dialog_open:
                    logger.info(f"[DOM] Filter dialog force-opened successfully (attempt {dlg_attempt + 1})")
                    break

            if not dialog_open:
                logger.error("[DOM] Filter dialog failed to open after all retries")
                return False
            time.sleep(0.5)

            # Step 3b: When switching to Unlisted, clear Has schedule / other visibility filters first.
            visibility_label = self._visibility_checkbox_label(visibility)
            if visibility.upper() == "UNLISTED":
                self._uncheck_other_visibility_checkboxes(visibility_label)

            # Step 4: Select checkbox — HARDENED for Edge (2026-01-30)
            # Edge needs longer for checkbox elements to become interactive after
            # dialog opens.  Retry up to 3 times with verification that the
            # checkbox state actually changed.
            CHECKBOX_MAX_RETRIES = 3
            CHECKBOX_WAIT_SECS = [1.0, 2.0, 3.0]
            checkbox_clicked = False

            for cb_attempt in range(CHECKBOX_MAX_RETRIES):
                logger.info(f"[DOM] Step 4: Finding checkbox for '{visibility_label}' (attempt {cb_attempt + 1}/{CHECKBOX_MAX_RETRIES})...")

                # Wait for checkbox to appear in the DOM
                time.sleep(CHECKBOX_WAIT_SECS[cb_attempt])

                checkbox_coords = self.driver.execute_script(f"""
                    const filterDialog = document.querySelector('ytcp-filter-dialog');
                    if (!filterDialog) return {{error: 'no dialog'}};

                    const spans = filterDialog.querySelectorAll('span');
                    for (let span of spans) {{
                        if (span.textContent.trim() === '{visibility_label}' && span.offsetParent !== null) {{
                            let current = span.parentElement;
                            for (let i = 0; i < 10 && current; i++) {{
                                const checkbox = current.querySelector('ytcp-checkbox-lit');
                                if (checkbox && checkbox.offsetParent !== null) {{
                                    const rect = checkbox.getBoundingClientRect();
                                    return {{
                                        success: true,
                                        x: Math.round(rect.left + rect.width / 2),
                                        y: Math.round(rect.top + rect.height / 2),
                                        checked: checkbox.hasAttribute('checked') || checkbox.checked === true
                                    }};
                                }}
                                current = current.parentElement;
                            }}
                            break;
                        }}
                    }}
                    return {{success: false, error: 'checkbox not found'}};
                """)

                if checkbox_coords.get('success'):
                    was_checked = checkbox_coords.get('checked', False)
                    # ActionChains click at coordinates (required for ytcp-checkbox-lit)
                    actions = ActionChains(self.driver)
                    actions.move_by_offset(checkbox_coords['x'], checkbox_coords['y']).click().perform()
                    actions.move_by_offset(-checkbox_coords['x'], -checkbox_coords['y']).perform()
                    time.sleep(0.8)  # Edge needs time for state change

                    # VERIFY: checkbox state actually changed
                    now_checked = self.driver.execute_script(f"""
                        const filterDialog = document.querySelector('ytcp-filter-dialog');
                        if (!filterDialog) return null;
                        const spans = filterDialog.querySelectorAll('span');
                        for (let span of spans) {{
                            if (span.textContent.trim() === '{visibility_label}' && span.offsetParent !== null) {{
                                let current = span.parentElement;
                                for (let i = 0; i < 10 && current; i++) {{
                                    const checkbox = current.querySelector('ytcp-checkbox-lit');
                                    if (checkbox) return checkbox.hasAttribute('checked') || checkbox.checked === true;
                                    current = current.parentElement;
                                }}
                            }}
                        }}
                        return null;
                    """)

                    if now_checked is True:
                        logger.info(f"[DOM] Checkbox '{visibility_label}' verified CHECKED (attempt {cb_attempt + 1})")
                        checkbox_clicked = True
                        break
                    elif now_checked != was_checked:
                        # State changed (even if we can't read True), accept it
                        logger.info(f"[DOM] Checkbox state changed (attempt {cb_attempt + 1}), accepting")
                        checkbox_clicked = True
                        break
                    else:
                        logger.warning(f"[DOM] Checkbox click did not change state (attempt {cb_attempt + 1})")
                        continue
                else:
                    # Fallback: click visible label directly (some UIs auto-apply)
                    clicked_label = self.driver.execute_script(f"""
                        const spans = document.querySelectorAll('span');
                        for (let span of spans) {{
                            if (span.offsetParent !== null && span.textContent.trim() === '{visibility_label}') {{
                                span.click();
                                return true;
                            }}
                        }}
                        return false;
                    """)
                    if clicked_label:
                        logger.info(f"[DOM] Clicked '{visibility_label}' label directly (attempt {cb_attempt + 1})")
                        checkbox_clicked = True
                        time.sleep(0.8)
                        break
                    else:
                        logger.warning(f"[DOM] Checkbox/label not found (attempt {cb_attempt + 1})")

            if not checkbox_clicked:
                logger.error(f"[DOM] Checkbox/label not found for {visibility_label} after {CHECKBOX_MAX_RETRIES} attempts")
                return False

            # Step 5: Click Apply button — HARDENED for Edge (2026-01-30)
            # Edge Apply button can take 0.5-1.5s to become interactive.
            # Verify the dialog actually closes after clicking Apply.
            APPLY_MAX_RETRIES = 3
            APPLY_WAIT_SECS = [1.0, 2.0, 3.0]
            apply_clicked = False

            for apply_attempt in range(APPLY_MAX_RETRIES):
                logger.info(f"[DOM] Step 5: Finding Apply button (attempt {apply_attempt + 1}/{APPLY_MAX_RETRIES})...")
                time.sleep(APPLY_WAIT_SECS[apply_attempt])

                apply_coords = self.driver.execute_script("""
                    const filterDialog = document.querySelector('ytcp-filter-dialog');
                    if (!filterDialog) return {error: 'no dialog'};

                    const buttons = filterDialog.querySelectorAll('button, ytcp-button');
                    for (let btn of buttons) {
                        if (btn.textContent.trim() === 'Apply' && btn.offsetParent !== null) {
                            const rect = btn.getBoundingClientRect();
                            return {
                                success: true,
                                x: Math.round(rect.left + rect.width / 2),
                                y: Math.round(rect.top + rect.height / 2)
                            };
                        }
                    }
                    return {success: false};
                """)

                if apply_coords.get('success'):
                    actions = ActionChains(self.driver)
                    actions.move_by_offset(apply_coords['x'], apply_coords['y']).click().perform()
                    actions.move_by_offset(-apply_coords['x'], -apply_coords['y']).perform()
                    time.sleep(1.5)  # Edge needs more time for dialog dismiss

                    # VERIFY: dialog actually closed after Apply
                    dialog_still_open = self.driver.execute_script("""
                        const dialog = document.querySelector('ytcp-filter-dialog #dialog');
                        if (!dialog) return false;
                        const style = window.getComputedStyle(dialog);
                        return style && style.display !== 'none' && dialog.getAttribute('aria-hidden') !== 'true';
                    """)

                    if not dialog_still_open:
                        logger.info(f"[DOM] Apply clicked and dialog dismissed (attempt {apply_attempt + 1})")
                        apply_clicked = True
                        break
                    else:
                        logger.warning(f"[DOM] Apply clicked but dialog still open (attempt {apply_attempt + 1})")
                        # Try clicking again — Edge sometimes needs a second click
                        continue
                else:
                    # No Apply button found — some Studio variants auto-apply on checkbox click
                    logger.info(f"[DOM] No Apply button found (attempt {apply_attempt + 1}), may be auto-apply UI")
                    apply_clicked = True  # Assume auto-apply
                    break

            # Close any remaining dialog/dropdown with ESC
            try:
                self.driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
            except Exception:
                pass
            time.sleep(0.8)

            # Step 6: Verify filter chip — HARDENED for Edge (2026-01-30)
            # Instead of returning True optimistically when chip not found,
            # retry chip detection with increasing waits (Edge rerenders slowly).
            CHIP_MAX_RETRIES = 3
            CHIP_WAIT_SECS = [1.0, 2.0, 3.0]

            for chip_attempt in range(CHIP_MAX_RETRIES):
                logger.info(f"[DOM] Step 6: Verifying filter chip (attempt {chip_attempt + 1}/{CHIP_MAX_RETRIES})...")
                time.sleep(CHIP_WAIT_SECS[chip_attempt])

                if self._visibility_chip_matches(visibility_label):
                    logger.info(f"[DOM] Filter chip verified: {visibility_label} (attempt {chip_attempt + 1})")
                    return True

                if self.verify_visibility_filter(visibility.upper()):
                    logger.info(f"[DOM] Filter confirmed via URL/state (attempt {chip_attempt + 1})")
                    return True

                # Detect wrong filter chip (e.g. Scheduled when Unlisted requested)
                wrong_state = self.read_visibility_filter_state()
                if wrong_state.get("wrong_for_unlisted") and visibility.upper() == "UNLISTED":
                    logger.error(
                        f"[DOM] Wrong filter after Apply: detected={wrong_state.get('detected')} "
                        f"chips={wrong_state.get('chip_texts')} (expected Unlisted)"
                    )
                    return False

                logger.warning(f"[DOM] Chip not found yet (attempt {chip_attempt + 1})")

            # Last resort: URL reset when DOM filter did not stick (Scheduled view persists)
            if visibility.upper() == "UNLISTED" and self._last_shorts_channel_id:
                logger.warning("[DOM] DOM filter failed — retrying UNLISTED via URL navigation")
                if self._navigate_shorts_with_url_filter(self._last_shorts_channel_id, "UNLISTED"):
                    if self.verify_visibility_filter("UNLISTED"):
                        return True

            logger.error("[DOM] Filter not applied — target chip not verified")
            self.diagnose_failure("filter_chip_not_verified")
            return False

        except Exception as e:
            logger.error(f"[DOM] Filter fallback failed: {e}")
            # Capture diagnostic on filter failure
            self.diagnose_failure("dom_filter_failed", e)

        return False

    # =========================================
    # LAYER 2: VIDEO EDIT METHODS
    # =========================================

    def click_first_video_edit_button(self) -> Optional[str]:
        """
        Click edit button on first video row to open edit page.
        
        Returns:
            Video ID if successful, None otherwise
        """
        import time
        from selenium.webdriver.common.action_chains import ActionChains

        try:
            logger.info("[DOM Layer 2] Clicking edit button on first video...")
            
            # Get first video row
            rows = self.driver.find_elements(By.CSS_SELECTOR, self.selectors.VIDEO_ROWS)
            if not rows:
                logger.error("[DOM Layer 2] No video rows found")
                return None
            
            first_row = rows[0]
            
            # Hover to reveal edit button
            actions = ActionChains(self.driver)
            actions.move_to_element(first_row).perform()
            time.sleep(0.5)
            
            # Try to find and click edit button
            try:
                edit_btn = first_row.find_element(By.CSS_SELECTOR, self.selectors.EDIT_BUTTON_SELECTOR)
                if edit_btn:
                    href = edit_btn.get_attribute("href")
                    video_id = href.split("/video/")[1].split("/")[0] if "/video/" in href else None
                    self.safe_click(edit_btn)
                    logger.info(f"[DOM Layer 2] Clicked edit for video: {video_id}")
                    time.sleep(2)  # Wait for page load
                    return video_id
            except NoSuchElementException:
                pass
            
            # Fallback: coordinate-based click
            x, y = self.selectors.EDIT_BUTTON_COORDS
            actions = ActionChains(self.driver)
            actions.move_by_offset(x, y).click().perform()
            actions.reset_actions()
            time.sleep(2)
            
            # Extract video ID from URL
            if "/video/" in self.driver.current_url:
                video_id = self.driver.current_url.split("/video/")[1].split("/")[0]
                logger.info(f"[DOM Layer 2] On edit page for video: {video_id}")
                return video_id
            
        except Exception as e:
            logger.error(f"[DOM Layer 2] Edit button click failed: {e}")
        
        return None

    def get_current_title(self) -> Optional[str]:
        """
        Extract current title from video edit page.
        
        Returns:
            Title text or None
        """
        try:
            # Try CSS selector first
            title_elem = self.driver.find_element(
                By.CSS_SELECTOR, self.selectors.TITLE_TEXTBOX_SELECTOR
            )
            title = title_elem.text or title_elem.get_attribute("textContent")
            logger.info(f"[DOM Layer 2] Current title: {title[:50]}...")
            return title.strip()
        except NoSuchElementException:
            pass
        
        # Try XPath
        try:
            title_elem = self.driver.find_element(
                By.XPATH, self.selectors.TITLE_TEXTBOX_XPATH
            )
            title = title_elem.text or title_elem.get_attribute("textContent")
            logger.info(f"[DOM Layer 2] Current title (XPath): {title[:50]}...")
            return title.strip()
        except NoSuchElementException:
            logger.warning("[DOM Layer 2] Could not find title textbox")
        
        return None

    def get_current_description(self) -> Optional[str]:
        """
        Extract current description from video edit page.
        
        Returns:
            Description text or None
        """
        try:
            desc_elem = self.driver.find_element(
                By.CSS_SELECTOR, self.selectors.DESC_TEXTBOX_SELECTOR
            )
            desc = desc_elem.text or desc_elem.get_attribute("textContent")
            logger.info(f"[DOM Layer 2] Current description: {desc[:50]}...")
            return desc.strip()
        except NoSuchElementException:
            pass
        
        try:
            desc_elem = self.driver.find_element(
                By.XPATH, self.selectors.DESC_TEXTBOX_XPATH
            )
            desc = desc_elem.text or desc_elem.get_attribute("textContent")
            logger.info(f"[DOM Layer 2] Current description (XPath): {desc[:50]}...")
            return desc.strip()
        except NoSuchElementException:
            logger.warning("[DOM Layer 2] Could not find description textbox")
        
        return None

    def set_title(self, new_title: str) -> bool:
        """
        Set new title in video edit page.
        
        Args:
            new_title: New title text
            
        Returns:
            True if successful
        """
        try:
            title_elem = self.driver.find_element(
                By.CSS_SELECTOR, self.selectors.TITLE_TEXTBOX_SELECTOR
            )
            title_elem.click()
            title_elem.send_keys(Keys.CONTROL + "a")  # Select all
            title_elem.send_keys(new_title)
            logger.info(f"[DOM Layer 2] Set title: {new_title[:50]}...")
            return True
        except Exception as e:
            logger.error(f"[DOM Layer 2] Set title failed: {e}")
            return False

    def set_description(self, new_description: str) -> bool:
        """
        Set new description in video edit page.
        
        Args:
            new_description: New description text
            
        Returns:
            True if successful
        """
        try:
            desc_elem = self.driver.find_element(
                By.CSS_SELECTOR, self.selectors.DESC_TEXTBOX_SELECTOR
            )
            desc_elem.click()
            desc_elem.send_keys(Keys.CONTROL + "a")  # Select all
            desc_elem.send_keys(new_description)
            logger.info(f"[DOM Layer 2] Set description: {new_description[:50]}...")
            return True
        except Exception as e:
            logger.error(f"[DOM Layer 2] Set description failed: {e}")
            return False

    def sort_by_date_oldest(self) -> bool:
        """
        Sort video table by date, oldest first.

        Clicks the Date column header to toggle sort. YouTube Studio sorts:
        - First click: ascending (oldest first) - this is what we want
        - Second click: descending (newest first)

        Returns:
            True if sort action was performed, False on error
        """
        import time
        try:
            # Find the date header sort button
            date_header = None
            selectors_to_try = [
                (By.CSS_SELECTOR, self.selectors.DATE_HEADER_SORT_CSS),
                (By.XPATH, self.selectors.DATE_HEADER_SORT_XPATH),
                # Fallback: look for any sortable header with "Date" text
                (By.XPATH, "//button[contains(@id,'date-header')]"),
                (By.XPATH, "//ytcp-table-header//h3[contains(text(),'Date')]/ancestor::button"),
            ]

            for by, selector in selectors_to_try:
                try:
                    date_header = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((by, selector))
                    )
                    if date_header and date_header.is_displayed():
                        logger.info(f"[DOM] Found date header via: {selector[:50]}")
                        break
                except Exception:
                    continue

            if not date_header:
                logger.warning("[DOM] Date header sort button not found")
                return False

            # Check current sort state via aria-sort or class
            sort_state = self.driver.execute_script("""
                const header = arguments[0];
                // Check parent th/td for aria-sort
                const parent = header.closest('.tablecell-date') || header.closest('th') || header;
                const ariaSort = parent.getAttribute('aria-sort') || '';
                const classes = parent.className || '';
                const isSorted = classes.includes('column-sorted');
                const hasAscIcon = parent.querySelector('yt-icon[icon="icons:arrow-upward"]') !== null;
                const hasDescIcon = parent.querySelector('yt-icon[icon="icons:arrow-downward"]') !== null;
                return {
                    ariaSort: ariaSort,
                    isSorted: isSorted,
                    hasAscIcon: hasAscIcon,
                    hasDescIcon: hasDescIcon,
                };
            """, date_header)

            logger.info(f"[DOM] Current sort state: {sort_state}")

            # If already sorted ascending (oldest first), we're done
            if sort_state.get("ariaSort") == "ascending" or sort_state.get("hasAscIcon"):
                logger.info("[DOM] Already sorted oldest first - no action needed")
                return True

            # Click to sort (first click = ascending = oldest first)
            self.safe_click(date_header)
            time.sleep(1)  # Wait for sort to apply

            # If it was already sorted descending, need to click again to flip to ascending
            if sort_state.get("ariaSort") == "descending" or sort_state.get("hasDescIcon"):
                logger.info("[DOM] Was sorted newest first, clicking again for oldest first")
                self.safe_click(date_header)
                time.sleep(1)

            logger.info("[DOM] Sorted by date (oldest first)")
            return True

        except Exception as e:
            logger.warning(f"[DOM] Sort by date failed: {e}")
            return False

    def set_page_size(self, size: int = 50) -> bool:
        """
        Set the page size for video table display.

        Args:
            size: Target page size (10, 30, or 50). Default 50 for efficiency.

        Returns:
            True if page size was set successfully.

        2026-01-28: Added for processing larger batches before pagination.
        """
        import time  # local import (needed for time.sleep below)

        try:
            logger.info(f"[DOM] Setting page size to {size}...")

            # Strategy 1: Click the page size dropdown trigger
            trigger = None
            for selector in [self.selectors.PAGE_SIZE_TRIGGER_CSS, self.selectors.PAGE_SIZE_TRIGGER_XPATH]:
                try:
                    if selector.startswith("//"):
                        trigger = self.driver.find_element(By.XPATH, selector)
                    else:
                        trigger = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if trigger:
                        break
                except NoSuchElementException:
                    continue

            if not trigger:
                logger.warning("[DOM] Page size trigger not found")
                return False

            self.safe_click(trigger)
            time.sleep(0.5)  # Wait for menu to open

            # Strategy 2: Click the target size item (50)
            size_item = None
            # Try XPath first (most precise - looks for text "50")
            try:
                size_item = self.driver.find_element(By.XPATH, self.selectors.PAGE_SIZE_ITEM_50_XPATH)
            except NoSuchElementException:
                pass

            # Fallback: find by text content
            if not size_item:
                try:
                    menu_items = self.driver.find_elements(
                        By.CSS_SELECTOR,
                        "ytcp-text-menu#select-menu-for-page-size tp-yt-paper-item"
                    )
                    for item in menu_items:
                        if str(size) in item.text:
                            size_item = item
                            break
                except Exception:
                    pass

            if not size_item:
                logger.warning(f"[DOM] Page size {size} option not found")
                return False

            self.safe_click(size_item)
            time.sleep(1)  # Wait for table to reload

            logger.info(f"[DOM] Page size set to {size}")
            return True

        except Exception as e:
            logger.warning(f"[DOM] Set page size failed: {e}")
            return False

    def click_back_to_shorts_list(self) -> bool:
        """
        Click the back button to return to the shorts list from video edit page.

        This is used after processing a batch of videos to reload the unlisted list
        and continue with the next batch.

        Returns:
            True if back navigation succeeded.

        2026-01-28: Added for continuous processing loop.
        """
        try:
            logger.info("[DOM] Clicking back button to return to shorts list...")

            back_btn = None
            for selector in [self.selectors.BACK_BUTTON_CSS, self.selectors.BACK_BUTTON_XPATH]:
                try:
                    if selector.startswith("//"):
                        back_btn = self.driver.find_element(By.XPATH, selector)
                    else:
                        back_btn = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if back_btn:
                        break
                except NoSuchElementException:
                    continue

            if not back_btn:
                logger.warning("[DOM] Back button not found")
                return False

            self.safe_click(back_btn)
            time.sleep(2)  # Wait for navigation

            logger.info("[DOM] Navigated back to shorts list")
            return True

        except Exception as e:
            logger.warning(f"[DOM] Back navigation failed: {e}")
            return False

    def get_video_rows(self) -> List:
        """Get all video row elements from the table."""
        return self.driver.find_elements(By.CSS_SELECTOR, self.selectors.VIDEO_ROWS)

    def get_scheduled_videos(self) -> List[Dict[str, str]]:
        """
        Get all scheduled videos with their dates.

        Returns:
            List of dicts with video_id, title, date
        """
        videos = []
        rows = self.driver.find_elements(By.XPATH, self.selectors.XPATH_SCHEDULED_ROWS)

        for row in rows:
            try:
                # Extract video ID from link href
                link = row.find_element(By.CSS_SELECTOR, self.selectors.VIDEO_TITLE_LINK)
                href = link.get_attribute("href")
                video_id = href.split("/video/")[1].split("/")[0]
                title = link.text

                # Extract date from date cell
                date_cell = row.find_element(By.XPATH, ".//td[contains(text(),'202')]")
                date_text = date_cell.text

                videos.append({
                    "video_id": video_id,
                    "title": title,
                    "date": date_text,
                })
            except Exception as e:
                logger.warning(f"[DOM] Error parsing video row: {e}")

        return videos

    def get_scheduled_videos_detailed(self) -> List[Dict[str, str]]:
        """
        Get scheduled videos with parsed date/time when available.

        Returns:
            List of dicts with video_id, title, date_text, date, time
        """
        import re

        def _normalize(text: str) -> str:
            return (text or "").replace("\u202f", " ").replace("\u00a0", " ").strip()

        def _parse_date_time(text: str) -> Dict[str, str]:
            clean = _normalize(text)
            # Expected format often includes a comma before time.
            # Example: "Jan 21, 2026, 5:15 PM"
            time_match = re.search(r"(\d{1,2}:\d{2}\s*[AP]M)", clean)
            date_match = re.search(r"([A-Za-z]{3,9}\s+\d{1,2},\s+\d{4})", clean)
            return {
                "date": date_match.group(1) if date_match else "",
                "time": time_match.group(1) if time_match else "",
                "date_text": clean,
            }

        videos = []
        rows = self.driver.find_elements(By.XPATH, self.selectors.XPATH_SCHEDULED_ROWS)

        for row in rows:
            try:
                link = row.find_element(By.CSS_SELECTOR, self.selectors.VIDEO_TITLE_LINK)
                href = link.get_attribute("href")
                video_id = href.split("/video/")[1].split("/")[0]
                title = link.text

                date_cell = row.find_element(By.XPATH, ".//td[contains(text(),'202')]")
                parsed = _parse_date_time(date_cell.text)

                videos.append({
                    "video_id": video_id,
                    "title": title,
                    "date_text": parsed["date_text"],
                    "date": parsed["date"],
                    "time": parsed["time"],
                })
            except Exception as e:
                logger.warning(f"[DOM] Error parsing scheduled row: {e}")

        return videos

    def get_unlisted_videos(self) -> List[Dict[str, str]]:
        """
        Get all unlisted videos.

        Returns:
            List of dicts with video_id, title, href
        """
        if not self.ensure_visibility_filter("UNLISTED"):
            logger.error(
                "[DOM] Refusing to scrape rows — UNLISTED filter not active "
                "(list may be on Scheduled; refresh will not fix)"
            )
            return []

        # Strict row scan — reject Scheduled rows (wrong filter / Has schedule still active)
        try:
            scraped = self.driver.execute_script("""
                const rows = document.querySelectorAll('ytcp-video-row');
                const out = [];
                let skippedScheduled = 0;
                for (const row of rows) {
                    const text = (row.textContent || '').toLowerCase();
                    const hasUnlisted = /\\bunlisted\\b/.test(text);
                    const hasScheduled = /\\bscheduled\\b/.test(text) || text.includes('has schedule');
                    if (!hasUnlisted) continue;
                    if (hasScheduled && !hasUnlisted) {
                        skippedScheduled += 1;
                        continue;
                    }
                    const link = row.querySelector("a[href*='/video/']");
                    if (!link) continue;
                    const href = link.getAttribute('href') || '';
                    const m = href.match(/\\/video\\/([^/?]+)/);
                    if (!m) continue;
                    out.push({
                        video_id: m[1],
                        title: (link.textContent || '').trim(),
                        href: href,
                        row_has_scheduled: hasScheduled,
                    });
                }
                return { videos: out, skippedScheduled: skippedScheduled };
            """) or {}
        except Exception as exc:
            logger.error(f"[DOM] Unlisted row scrape failed: {exc}")
            return []

        skipped = int(scraped.get("skippedScheduled") or 0)
        if skipped:
            logger.warning(f"[DOM] Skipped {skipped} row(s) that look Scheduled (wrong filter?)")

        videos = []
        for item in scraped.get("videos") or []:
            if item.get("row_has_scheduled"):
                logger.warning(
                    f"[DOM] Skip row {item.get('video_id')}: row shows Scheduled + Unlisted — not scheduling"
                )
                continue
            videos.append({
                "video_id": item.get("video_id"),
                "title": item.get("title", ""),
                "href": item.get("href", ""),
            })

        state = self.read_visibility_filter_state()
        logger.info(
            f"[DOM] Unlisted scrape: {len(videos)} videos "
            f"(filter={state.get('detected')}, chips={state.get('chip_texts')})"
        )
        return videos

    def has_next_page(self) -> bool:
        """Check if there's a next page of results."""
        try:
            btn = self.driver.find_element(By.CSS_SELECTOR, self.selectors.NEXT_PAGE_BTN)
            return btn.is_enabled()
        except NoSuchElementException:
            return False

    def click_next_page(self):
        """Navigate to next page of results."""
        btn = self.wait_for_clickable(self.selectors.NEXT_PAGE_BTN)
        self.safe_click(btn)
        import time
        time.sleep(1)  # Wait for page load

    # =========================================
    # PAGE 2: VIDEO EDIT METHODS
    # =========================================

    def navigate_to_video(self, video_id: str):
        """Navigate to video edit page."""
        url = f"https://studio.youtube.com/video/{video_id}/edit"
        logger.info(f"[DOM] Navigating to video: {video_id}")
        self.driver.get(url)
        # Wait for edit page readiness (Studio variants render different visibility controls).
        # We wait for ANY stable marker rather than a single brittle selector.
        wait = WebDriverWait(self.driver, 12)

        def _is_ready(drv) -> bool:
            try:
                candidates = [
                    "ytcp-video-metadata-visibility",
                    "ytcp-video-metadata-visibility #select-button",
                    "button[aria-label='Edit video visibility status']",
                    "#select-button",
                    "#title-textarea",
                    "#description-textarea",
                ]
                for css in candidates:
                    if drv.find_elements(By.CSS_SELECTOR, css):
                        return True
            except Exception:
                return False
            return False

        wait.until(lambda d: _is_ready(d))

    def _has_non_bmp_chars(self, text: str) -> bool:
        """Check if text contains non-BMP characters (emojis, etc.) that ChromeDriver can't send_keys()."""
        return any(ord(ch) > 0xFFFF for ch in text)

    def _set_text_via_js(self, element, text: str, field_name: str = "field"):
        """Set text content via JavaScript (handles non-BMP chars like emojis)."""
        self.driver.execute_script(
            """
            const el = arguments[0];
            const text = arguments[1];
            el.focus();
            el.textContent = text;
            el.dispatchEvent(new Event('input', { bubbles: true }));
            """,
            element,
            text,
        )
        logger.debug(f"[DOM] {field_name} set via JS ({len(text)} chars)")

    def edit_title(self, new_title: str):
        """Edit video title."""
        import time
        title_input = self.wait_for_element(
            self.selectors.TITLE_INPUT_XPATH, By.XPATH
        )
        self.safe_click(title_input)

        # Skip send_keys if non-BMP chars (emojis) - go straight to JS
        if self._has_non_bmp_chars(new_title):
            logger.debug(f"[DOM] Title has emojis - using JS method")
            ActionChains(self.driver).key_down(Keys.CONTROL).send_keys("a").key_up(Keys.CONTROL).perform()
            time.sleep(self.human_delay(0.25, 0.15))
            self._set_text_via_js(title_input, new_title, "Title")
            return

        try:
            # 012-modeled: focus is handled by safe_click; replace via Ctrl+A.
            ActionChains(self.driver).key_down(Keys.CONTROL).send_keys("a").key_up(Keys.CONTROL).perform()
            time.sleep(self.human_delay(0.25, 0.15))
            title_input.send_keys(new_title)
        except Exception as e:
            # ChromeDriver may fail on non-BMP characters (emoji). Fallback to JS assignment.
            logger.debug(f"[DOM] Title send_keys failed ({type(e).__name__}), using JS fallback")
            self._set_text_via_js(title_input, new_title, "Title")

    def edit_description(self, new_description: str):
        """Edit video description."""
        import time
        desc_input = self.wait_for_element(
            self.selectors.DESCRIPTION_INPUT_XPATH, By.XPATH
        )
        self.safe_click(desc_input)

        # Skip send_keys if non-BMP chars (emojis) - go straight to JS
        if self._has_non_bmp_chars(new_description):
            logger.debug(f"[DOM] Description has emojis - using JS method")
            ActionChains(self.driver).key_down(Keys.CONTROL).send_keys("a").key_up(Keys.CONTROL).perform()
            time.sleep(self.human_delay(0.25, 0.15))
            self._set_text_via_js(desc_input, new_description, "Description")
            return

        try:
            ActionChains(self.driver).key_down(Keys.CONTROL).send_keys("a").key_up(Keys.CONTROL).perform()
            time.sleep(self.human_delay(0.25, 0.15))
            desc_input.send_keys(new_description)
        except Exception as e:
            # ChromeDriver may fail on non-BMP characters (emoji). Fallback to JS assignment.
            logger.debug(f"[DOM] Description send_keys failed ({type(e).__name__}), using JS fallback")
            self._set_text_via_js(desc_input, new_description, "Description")

    def click_save(self):
        """Click page-level Save button (not dialog Done/Save)."""
        import time

        # Allow dialog close animation to complete (Done/Save just clicked).
        pre_save_delay = float(os.getenv("YT_SCHEDULER_PRE_SAVE_DELAY_SEC", "1.0"))
        time.sleep(pre_save_delay)

        # Best-effort: wait for the visibility dialog to disappear so it doesn't intercept clicks.
        try:
            WebDriverWait(self.driver, 6).until(
                lambda d: not d.find_elements(By.CSS_SELECTOR, "tp-yt-paper-dialog#dialog")
            )
        except Exception:
            pass

        candidates = [
            (By.CSS_SELECTOR, "ytcp-button#save-button button"),
            (By.CSS_SELECTOR, "ytcp-button#save-button"),
            (By.CSS_SELECTOR, "button#save-button"),
            (By.XPATH, "//ytcp-button[@id='save-button']//button"),
            (By.XPATH, "//button[@id='save-button']"),
            (By.XPATH, "//button[.//span[normalize-space(text())='Save']]"),
        ]

        last_err: Exception | None = None
        for by, sel in candidates:
            try:
                el = self.wait_for_clickable(sel, by, timeout=5)
                try:
                    self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
                except Exception:
                    pass
                self.safe_click(el)
                time.sleep(2.0)
                return
            except Exception as exc:
                last_err = exc
                continue

        # JS fallback: Studio sometimes renders Save as a custom element without stable ids,
        # or behind wrappers that Selenium "clickable" heuristics miss.
        try:
            clicked = self.driver.execute_script(
                """
                function isVisible(el) {
                  if (!el) return false;
                  if (el.offsetParent === null) return false;
                  const r = el.getBoundingClientRect();
                  return r.width > 0 && r.height > 0;
                }
                function textOf(el) {
                  return ((el && el.textContent) ? el.textContent : '').trim();
                }
                function clickBest(el) {
                  if (!el) return false;
                  // Prefer inner <button> when present.
                  try {
                    const inner = el.querySelector && el.querySelector('button');
                    if (inner && isVisible(inner)) { inner.click(); return true; }
                  } catch (e) {}
                  try { el.click(); return true; } catch (e) {}
                  return false;
                }

                const root = document;
                const all = Array.from(root.querySelectorAll('ytcp-button, button, tp-yt-paper-button, ytcp-button-shape'));
                const saveLike = all
                  .filter(isVisible)
                  .map(el => ({ el, t: textOf(el).toLowerCase(), id: (el.id||'') }))
                  .filter(x => x.t === 'save' || x.id === 'save-button');

                // Prefer explicit id, then visible text Save.
                const preferred = saveLike.find(x => x.id === 'save-button') || saveLike.find(x => x.t === 'save');
                if (preferred && clickBest(preferred.el)) return { clicked: true, id: preferred.id, text: preferred.t };

                return { clicked: false, found: saveLike.slice(0, 8).map(x => ({id:x.id, text:x.t})) };
                """
            )
            if isinstance(clicked, dict) and clicked.get("clicked"):
                time.sleep(2.0)
                return
        except Exception as exc:
            last_err = exc

        raise TimeoutException(f"Save button not found/clickable: {last_err}")

    # =========================================
    # RESCHEDULE (already-scheduled video) — edit-popup entry
    # =========================================

    def open_scheduled_edit_popup(self, video_id: Optional[str] = None) -> bool:
        """Open the visibility-edit popup for an already-Scheduled list row.

        Reschedule entry (Mode B Phase 2): on the videos/short *list* (filtered to
        Scheduled / "Has schedule"), each row's visibility cell shows a "Scheduled"
        ``span.label-span``. Clicking it opens ``ytcp-video-visibility-edit-popup
        tp-yt-paper-dialog#dialog`` which exposes the SAME ``ytcp-datetime-picker``
        date/time inputs the new-schedule flow uses — so the existing
        ``set_schedule_date`` / ``set_schedule_time`` / ``click_done`` / ``click_save``
        helpers drive it unchanged (WSP 84 reuse).

        Args:
            video_id: optional id to scope the click to a specific row (matches the
                row's ``a[href*='/video/<id>']``). When None, the FIRST Scheduled
                row's label is clicked.

        Returns:
            True if the edit popup opened (dialog present), False otherwise.

        NOTE: shadow_dom_finder.first_deep pierces Studio's shadow roots; a flat
        querySelector fallback covers light-DOM/mock drivers.
        """
        import time

        try:
            from modules.infrastructure.foundups_selenium.src.shadow_dom_finder import (
                first_deep,
            )
        except Exception:  # pragma: no cover - defensive import
            first_deep = None  # type: ignore

        # 1) Click the row's "Scheduled" label. Prefer a video-scoped row when an id
        #    is given so a batch never edits the wrong short.
        clicked = False
        if first_deep is not None:
            try:
                selectors: List[Any] = []
                if video_id:
                    # Row containing the id -> its visibility label span.
                    selectors.append(
                        [f"ytcp-video-row a[href*='/video/{video_id}']"],
                    )
                # Generic: any Scheduled label span on the list.
                selectors.append(["ytcp-video-row span.label-span"])
                anchor = first_deep(self.driver, selectors)
                if anchor is not None:
                    # If we matched the title link, hop to the row's label span.
                    target = self.driver.execute_script(
                        """
                        const el = arguments[0];
                        if (!el) return null;
                        const row = el.closest ? el.closest('ytcp-video-row') : null;
                        const scope = row || document;
                        const spans = scope.querySelectorAll('span.label-span');
                        for (const s of spans) {
                          const t = (s.textContent || '').trim().toLowerCase();
                          if (t.includes('scheduled')) return s;
                        }
                        return (scope.querySelector('span.label-span') || el);
                        """,
                        anchor,
                    )
                    self.safe_click(target or anchor)
                    clicked = True
            except Exception as exc:
                logger.debug(f"[RESCHED] shadow label click failed: {exc}")

        if not clicked:
            # Flat fallback (light-DOM / mocks): click the first Scheduled label.
            try:
                clicked = bool(self.driver.execute_script(
                    """
                    const vid = arguments[0];
                    let scope = document;
                    if (vid) {
                      const link = document.querySelector(
                        "ytcp-video-row a[href*='/video/" + vid + "']");
                      if (link && link.closest) scope = link.closest('ytcp-video-row') || document;
                    }
                    const spans = scope.querySelectorAll('span.label-span');
                    for (const s of spans) {
                      const t = (s.textContent || '').trim().toLowerCase();
                      if (t.includes('scheduled')) { s.click(); return true; }
                    }
                    return false;
                    """,
                    video_id,
                ))
            except Exception as exc:
                logger.warning(f"[RESCHED] flat label click failed: {exc}")
                clicked = False

        if not clicked:
            logger.warning("[RESCHED] Could not click a 'Scheduled' label to open edit popup")
            return False

        time.sleep(0.6)

        # 2) Confirm the edit popup dialog is present.
        try:
            WebDriverWait(self.driver, 8).until(lambda d: d.execute_script(
                """
                const popup = document.querySelector('ytcp-video-visibility-edit-popup');
                const dlg = document.querySelector('ytcp-video-visibility-edit-popup tp-yt-paper-dialog#dialog')
                          || document.querySelector('tp-yt-paper-dialog#dialog');
                return !!(popup || dlg);
                """
            ))
            return True
        except Exception:
            logger.warning("[RESCHED] Edit popup did not appear after clicking 'Scheduled'")
            return False

    def reschedule_open_set_save(self, date_str: str, time_str: str, video_id: Optional[str] = None) -> bool:
        """Full reschedule flow for one already-scheduled video (reuses the picker).

        open_scheduled_edit_popup -> set_schedule_date -> set_schedule_time ->
        click_done -> click_save. Mirrors ``schedule_video`` but enters via the list
        "Scheduled" label instead of the edit-page visibility dialog, and SKIPS
        select_schedule_option (the popup is already in scheduled state).

        Returns True only when every step succeeds.
        """
        import time as _t

        if not self.open_scheduled_edit_popup(video_id=video_id):
            return False
        steps = [
            ("set_schedule_date", lambda: self.set_schedule_date(date_str)),
            ("set_schedule_time", lambda: self.set_schedule_time(time_str)),
            ("click_done", lambda: self.click_done()),
            ("click_save", lambda: self.click_save()),
        ]
        for name, fn in steps:
            try:
                fn()
            except Exception as exc:
                logger.error(f"[RESCHED] reschedule failed at {name}: {type(exc).__name__}: {exc}")
                try:
                    ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()
                    _t.sleep(0.4)
                except Exception:
                    pass
                return False
        logger.info(f"[RESCHED] Rescheduled {video_id or '(first scheduled)'} -> {date_str} {time_str}")
        return True

    # =========================================
    # PAGE 3: SCHEDULING DIALOG METHODS
    # =========================================

    def open_visibility_dialog(self):
        """Open the visibility/scheduling dialog."""
        import time

        # YouTube Studio variants render this control as:
        # - <button aria-label="Edit video visibility status">
        # - <ytcp-icon-button id="select-button" aria-label="Edit video visibility status">
        # Prefer robust multi-selector approach.
        vis_btn = None

        # 1) Strict XPath for the known aria-label (button)
        try:
            vis_btn = self.wait_for_clickable(self.selectors.VISIBILITY_BTN_XPATH, By.XPATH, timeout=6)
        except Exception:
            vis_btn = None

        # 2) CSS for the icon button inside the visibility section
        if vis_btn is None:
            try:
                vis_btn = self.wait_for_clickable(
                    "ytcp-video-metadata-visibility #select-button",
                    By.CSS_SELECTOR,
                    timeout=6,
                )
            except Exception:
                vis_btn = None

        # 3) Final XPath fallback: any element with id=select-button and a visibility aria-label
        if vis_btn is None:
            try:
                vis_btn = self.wait_for_clickable(
                    "//*[@id='select-button' and contains(@aria-label,'visibility')]",
                    By.XPATH,
                    timeout=6,
                )
            except Exception:
                vis_btn = None

        if vis_btn is None:
            raise TimeoutException("Visibility button not found/clickable")

        self.safe_click(vis_btn)
        time.sleep(0.6)

        # Wait for the visibility dialog surface (tp-yt-paper-dialog variant is most common)
        try:
            self.wait_for_element(self.selectors.VISIBILITY_DIALOG_XPATH, By.XPATH, timeout=8)
            return
        except Exception:
            pass

        # Fallback: if dialog selector changes, wait for schedule/date/time inputs to exist
        WebDriverWait(self.driver, 8).until(lambda d: d.execute_script("""
            const hasSchedule =
              !!document.querySelector('tp-yt-paper-radio-button[name=\"SCHEDULE\"], tp-yt-paper-radio-button[name=\"SCHEDULED\"], tp-yt-paper-radio-button[name=\"SCHEDULE\"]');
            const hasDate = !!document.querySelector('input[aria-label*=\"Date\"]');
            const hasTime = !!document.querySelector('input[aria-label*=\"Time\"], input[aria-label*=\"time\"]');
            return hasSchedule || (hasDate && hasTime);
        """))

    def select_schedule_option(self):
        """Select the 'Schedule' radio button in visibility dialog."""
        import time

        # YouTube Studio has at least two variants:
        # - Variant A: explicit "Schedule" radio button
        # - Variant B: a "Schedule" section (often #second-container) that expands to show date/time inputs
        #
        # We treat "select schedule" as: ensure the schedule section is expanded and date/time inputs exist.

        # Variant A: try schedule radio if present
        # 2026-02-04: Live DOM confirms name="PUBLISH_FROM_PRIVATE" (no name="SCHEDULE" exists)
        radio_xpaths = [
            getattr(self.selectors, "SCHEDULE_RADIO_XPATH", "//tp-yt-paper-radio-button[@name='PUBLISH_FROM_PRIVATE']"),
            getattr(self.selectors, "RADIO_SCHEDULE", "//tp-yt-paper-radio-button[@name='PUBLISH_FROM_PRIVATE']"),
            "//tp-yt-paper-radio-button[contains(.,'private to public')]",
        ]
        for xp in radio_xpaths:
            try:
                schedule_radio = self.wait_for_clickable(xp, By.XPATH, timeout=3)
                self.safe_click(schedule_radio)
                time.sleep(0.3)
                break
            except Exception:
                continue

        # Variant B: expand schedule section (common in current Studio)
        expanded = False
        try:
            sched = self.driver.find_element(By.ID, "second-container")
            if sched and sched.is_displayed():
                self.driver.execute_script(
                    "arguments[0].scrollIntoView({behavior:'smooth', block:'center'});",
                    sched,
                )
                time.sleep(0.2)

                # Only click to expand if there is an explicit expanded state and it's currently collapsed.
                toggler = self.driver.execute_script("""
                    const root = document.querySelector('#second-container');
                    if (!root) return null;
                    const candidates = root.querySelectorAll('[aria-expanded]');
                    for (const el of candidates) {
                      if (el.offsetParent === null) continue;
                      const v = el.getAttribute('aria-expanded');
                      if (v === 'false' || v === 'true') return el;
                    }
                    return root;
                """)
                if toggler:
                    # If toggler has aria-expanded=true already, don't click (prevents open->close).
                    try:
                        state = self.driver.execute_script(
                            "return arguments[0].getAttribute('aria-expanded');",
                            toggler,
                        )
                    except Exception:
                        state = None

                    if state == "true":
                        expanded = True
                    else:
                        # 012-modeled click preferred; safe_click has JS fallback if needed.
                        self.safe_click(toggler)
                        time.sleep(0.5)
                        expanded = True
        except Exception:
            expanded = False

        if not expanded:
            # Fallback: legacy expand button selector
            try:
                expand_btn = self.driver.find_element(By.XPATH, self.selectors.SCHEDULE_EXPAND)
                if expand_btn and expand_btn.is_displayed():
                    self.safe_click(expand_btn)
                    time.sleep(0.5)
            except Exception:
                pass

        # Wait for a time input to exist (date may be text until clicked).
        WebDriverWait(self.driver, 8).until(lambda d: d.execute_script("""
            const inputs = Array.from(document.querySelectorAll('input'));
            const visible = inputs.filter(i => i && i.offsetParent !== null);
            // Most common: time input has a value like "12:00 AM" and no aria-label.
            const hasTimeLike = visible.some(i => {
              const v = (i.value || '').trim();
              return /\\d{1,2}:\\d{2}/.test(v);
            });
            // Alternative: aria-labeled time input exists.
            const hasAriaTime = !!document.querySelector('input[aria-label*="Time"], input[aria-label*="time"]');
            return hasTimeLike || hasAriaTime;
        """))

    def set_schedule_date(self, date_str: str):
        """
        Set the schedule date.

        Args:
            date_str: Date string like "Jan 5, 2026"
        """
        import time
        import os

        pre_type_delay = float(os.getenv("YT_SCHEDULER_PRE_TYPE_DELAY_SEC", "0.6"))
        key_delay = float(os.getenv("YT_SCHEDULER_KEY_DELAY_SEC", "0.06"))

        def slow_type(el, text: str):
            # Methodical per-char typing to avoid Studio dropping keystrokes.
            for ch in text:
                el.send_keys(ch)
                time.sleep(key_delay)

        def commit_input(el):
            """
            YouTube Studio sometimes doesn't "commit" until Enter/blur.
            Do Enter + Tab, then dispatch input/change/blur events.
            """
            try:
                el.send_keys(Keys.ENTER)
            except Exception:
                try:
                    ActionChains(self.driver).send_keys(Keys.ENTER).perform()
                except Exception:
                    pass
            time.sleep(pre_type_delay)
            try:
                el.send_keys(Keys.TAB)
            except Exception:
                try:
                    ActionChains(self.driver).send_keys(Keys.TAB).perform()
                except Exception:
                    pass
            time.sleep(pre_type_delay)
            try:
                self.driver.execute_script(
                    """
                    const el = arguments[0];
                    if (!el) return;
                    try { el.dispatchEvent(new Event('input', { bubbles: true })); } catch (e) {}
                    try { el.dispatchEvent(new Event('change', { bubbles: true })); } catch (e) {}
                    try { el.blur(); } catch (e) {}
                    """,
                    el,
                )
            except Exception:
                pass
            time.sleep(pre_type_delay)

        # In current Studio variants, date is often rendered as text (e.g. "Jan 19, 2026")
        # until you click it. We must click the *date field* first, then Ctrl+A replace.
        try:
            # Try an actual Date input first (when already expanded)
            date_input = self.wait_for_element(self.selectors.DATE_INPUT_XPATH, By.XPATH, timeout=3)
        except Exception:
            date_input = None

        if date_input is None:
            # Current Studio variant:
            # - The schedule section shows a date *text* ("Jan 19, 2026") inside
            #   `ytcp-text-dropdown-trigger#datepicker-trigger div.left-container`.
            # - Clicking that opens a `ytcp-date-picker` popup with an <input> we can Ctrl+A replace.
            try:
                date_trigger = self.wait_for_clickable(
                    self.selectors.DATE_TRIGGER_CSS,
                    By.CSS_SELECTOR,
                    timeout=6,
                )
                # Critical: click DATE first (not time/timezone).
                # Occam: deterministic click with slow delays.
                self.safe_click(date_trigger)
                time.sleep(pre_type_delay)
            except Exception:
                # Fallback: click the visible date text inside the schedule container to activate the picker/input.
                self.driver.execute_script("""
                    const root = document.querySelector('#second-container');
                    if (!root) return;
                    const candidates = Array.from(root.querySelectorAll('span, div'))
                      .filter(e => e.offsetParent !== null && e.children.length === 0)
                      .map(e => ({el: e, t: (e.textContent||'').trim()}))
                      .filter(x => /\\b\\w{3}\\b\\s+\\d{1,2},\\s+\\d{4}/.test(x.t));
                    if (candidates.length) candidates[0].el.click();
                """)
                time.sleep(pre_type_delay)

            # Try the date-picker popup input first
            for attempt in range(2):
                try:
                    picker_input = self.wait_for_clickable(
                        self.selectors.DATE_PICKER_INPUT_CSS,
                        By.CSS_SELECTOR,
                        timeout=8,
                    )
                    self._focus_and_select_all_input(picker_input)
                    time.sleep(pre_type_delay)

                    # Replace selected value by typing.
                    slow_type(picker_input, date_str)
                    time.sleep(0.15)
                    commit_input(picker_input)

                    # Verify the value "stuck" (some variants keep value in activeElement)
                    try:
                        val = (picker_input.get_attribute("value") or "").strip()
                        if val and val.lower() == date_str.strip().lower():
                            return
                    except Exception:
                        pass

                    # If verification failed, retry once after an extra delay.
                    if attempt == 0:
                        time.sleep(pre_type_delay)
                        continue
                    return
                except Exception:
                    picker_input = None

            # Alternate variant: aria-labeled Date input exists after clicking trigger
            try:
                date_input = self.wait_for_element(self.selectors.DATE_INPUT_XPATH, By.XPATH, timeout=3)
            except Exception:
                date_input = None

        if date_input is not None:
            self._focus_and_select_all_input(date_input)
            time.sleep(pre_type_delay)
            slow_type(date_input, date_str)
            time.sleep(0.15)
            commit_input(date_input)
            return

        # Fallback: legacy date picker trigger then input (older Studio variants)
        try:
            date_btn = self.wait_for_clickable(self.selectors.DATE_PICKER_BTN, By.XPATH, timeout=6)
            self.safe_click(date_btn)
            time.sleep(0.3)
            date_input = self.wait_for_element(self.selectors.DATE_INPUT, By.XPATH, timeout=6)
            self._focus_and_select_all_input(date_input)
            time.sleep(pre_type_delay)
            slow_type(date_input, date_str)
            time.sleep(0.15)
            commit_input(date_input)
        except Exception as exc:
            raise TimeoutException(f"Date input not found/usable: {exc}")

    def set_schedule_time(self, time_str: str):
        """
        Set the schedule time.

        Args:
            time_str: Time string like "5:00 AM"
        """
        import time
        import os

        pre_type_delay = float(os.getenv("YT_SCHEDULER_PRE_TYPE_DELAY_SEC", "0.5"))
        key_delay = float(os.getenv("YT_SCHEDULER_KEY_DELAY_SEC", "0.05"))

        def slow_type(el, text: str):
            for ch in text:
                el.send_keys(ch)
                time.sleep(key_delay)

        def commit_input(el):
            """
            YouTube Studio time field sometimes requires Enter/blur to stick.
            """
            try:
                el.send_keys(Keys.ENTER)
            except Exception:
                try:
                    ActionChains(self.driver).send_keys(Keys.ENTER).perform()
                except Exception:
                    pass
            time.sleep(pre_type_delay)
            try:
                el.send_keys(Keys.TAB)
            except Exception:
                try:
                    ActionChains(self.driver).send_keys(Keys.TAB).perform()
                except Exception:
                    pass
            time.sleep(pre_type_delay)
            try:
                self.driver.execute_script(
                    """
                    const el = arguments[0];
                    if (!el) return;
                    try { el.dispatchEvent(new Event('input', { bubbles: true })); } catch (e) {}
                    try { el.dispatchEvent(new Event('change', { bubbles: true })); } catch (e) {}
                    try { el.blur(); } catch (e) {}
                    """,
                    el,
                )
            except Exception:
                pass
            time.sleep(pre_type_delay)

        # Prefer direct input replacement (no dropdown selection).
        time_input = None

        # 0) Current Studio variant (explicit DOM path)
        try:
            time_input = self.wait_for_element(
                self.selectors.TIME_OF_DAY_INPUT_CSS,
                By.CSS_SELECTOR,
                timeout=3,
            )
        except Exception:
            time_input = None

        # 1) aria-labeled time inputs (some variants)
        if time_input is None:
            for xp in [self.selectors.TIME_INPUT_XPATH, self.selectors.TIME_INPUT_TEXTBOX]:
                try:
                    time_input = self.wait_for_element(xp, By.XPATH, timeout=2)
                    break
                except Exception:
                    time_input = None

        # 2) common variant: visible input with a value like "12:00 AM" and no aria-label
        if time_input is None:
            try:
                time_input = WebDriverWait(self.driver, 4).until(lambda d: d.execute_script("""
                    const inputs = Array.from(document.querySelectorAll('input'));
                    const visible = inputs.filter(i => i && i.offsetParent !== null);
                    for (const i of visible) {
                      const v = (i.value || '').trim();
                      if (/\\d{1,2}:\\d{2}/.test(v) && (v.toUpperCase().includes('AM') || v.toUpperCase().includes('PM'))) {
                        return i;
                      }
                    }
                    return null;
                """))
            except Exception:
                time_input = None

        if time_input is None:
            raise TimeoutException("Time input not found/usable")

        # Critical: click the actual input field first, then Ctrl+A replace.
        self._focus_and_select_all_input(time_input)
        time.sleep(pre_type_delay)
        slow_type(time_input, time_str)
        time.sleep(0.15)
        commit_input(time_input)

    def click_done(self):
        """Click Done button to confirm scheduling."""
        import time

        # YouTube Studio variants:
        # - native <button> with inner <span>Done</span>
        # - <ytcp-button id="done-button"> wrapper with an internal <button>
        # - dialog "Save" button (some variants replace Done with Save inside dialog)
        # - different DOM/shadow structures
        candidates = [
            (By.XPATH, self.selectors.DONE_BTN),
            (By.XPATH, "//button[.//span[normalize-space(text())='Done']]"),
            (By.XPATH, "//ytcp-button[.//span[normalize-space(text())='Done']]"),
            # Dialog Save button (observed path: tp-yt-paper-dialog#dialog div.button-area ... ytcp-button#save-button)
            # IMPORTANT: scope to button-area to avoid timezone-select-button misclicks.
            (By.CSS_SELECTOR, "tp-yt-paper-dialog#dialog div.button-area ytcp-button#save-button button"),
            (By.CSS_SELECTOR, "tp-yt-paper-dialog#dialog div.button-area ytcp-button#save-button"),
            (By.CSS_SELECTOR, "ytcp-button#done-button"),
            (By.CSS_SELECTOR, "ytcp-button#done-button button"),
            (By.CSS_SELECTOR, "button#done-button"),
        ]

        for by, sel in candidates:
            try:
                el = self.wait_for_clickable(sel, by, timeout=4)

                # Safety: never click timezone selector by accident.
                try:
                    is_timezone = self.driver.execute_script(
                        "return !!(arguments[0] && arguments[0].closest && arguments[0].closest('#timezone-select-button'));",
                        el,
                    )
                    if is_timezone:
                        continue
                except Exception:
                    pass

                # Prefer clicking the inner <button> when wrapped by ytcp-button.
                try:
                    if (el.tag_name or "").lower() == "ytcp-button":
                        inner = el.find_element(By.CSS_SELECTOR, "button")
                        el = inner
                except Exception:
                    pass

                try:
                    # Ensure it's in view (some Studio dialogs require scroll)
                    self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
                except Exception:
                    pass
                self.safe_click(el)
                time.sleep(1)
                return
            except Exception:
                continue

        # Last resort: JS click inside dialog (STRICT scope).
        try:
            clicked = self.driver.execute_script(
                """
                const root = document.querySelector('tp-yt-paper-dialog#dialog') || document;
                // Prefer explicit ids.
                const done = root.querySelector('ytcp-button#done-button button, ytcp-button#done-button, button#done-button');
                if (done) { done.click(); return true; }

                // Studio variant: dialog Save button is the "Done" equivalent.
                const save = root.querySelector('div.button-area ytcp-button#save-button button, div.button-area ytcp-button#save-button');
                if (save) { save.click(); return true; }

                return false;
                """
            )
            if clicked:
                time.sleep(1)
                return
        except Exception:
            pass

        raise TimeoutException("Done/Save button not found/clickable")

    def schedule_video(self, date_str: str, time_str: str) -> bool:
        """
        Full scheduling workflow for current video.

        Args:
            date_str: Date like "Jan 5, 2026"
            time_str: Time like "5:00 AM"

        Returns:
            True if successful
        """
        import time as time_module
        workflow_start = time_module.time()
        logger.info(f"[DOM] Scheduling for {date_str} at {time_str}")

        steps = [
            ("open_visibility_dialog", lambda: self.open_visibility_dialog()),
            ("select_schedule_option", lambda: self.select_schedule_option()),
            ("set_schedule_date", lambda: self.set_schedule_date(date_str)),
            ("set_schedule_time", lambda: self.set_schedule_time(time_str)),
            ("click_done", lambda: self.click_done()),
            ("click_save", lambda: self.click_save()),
        ]

        step_times = []
        for step_name, fn in steps:
            step_start = time_module.time()
            try:
                fn()
                elapsed = time_module.time() - step_start
                step_times.append((step_name, elapsed))
                logger.debug(f"[DOM] Step '{step_name}' completed in {elapsed:.1f}s")
            except Exception as e:
                elapsed = time_module.time() - step_start
                logger.error(f"[DOM] Scheduling failed at {step_name} ({elapsed:.1f}s): {type(e).__name__}: {e}")
                # Best-effort cleanup: close dialog so the next loop isn't blocked.
                try:
                    ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()
                    time_module.sleep(0.5)
                except Exception:
                    pass
                return False

        total_time = time_module.time() - workflow_start
        timing_summary = ", ".join(f"{n}:{t:.1f}s" for n, t in step_times)
        logger.info(f"[DOM] Scheduled {date_str} {time_str} in {total_time:.1f}s [{timing_summary}]")
        return True

    def update_video_tags(self, video_id: str, tags: List[str]) -> bool:
        """
        Append tags to a video's tag field in YouTube Studio edit page.

        Navigates to the video edit page, finds the tags input, appends new tags
        (without replacing existing ones), and saves.

        Gated by env var YT_AUTO_TAG_ENABLED (caller should check before calling).

        Args:
            video_id: YouTube video ID
            tags: List of tag strings (without # prefix)

        Returns:
            True if tags were successfully applied
        """
        import os
        import time as time_module

        if not tags:
            logger.info(f"[DOM] No tags to apply for {video_id}")
            return True

        # Navigate to video edit page
        edit_url = f"https://studio.youtube.com/video/{video_id}/edit"
        logger.info(f"[DOM] Navigating to edit page for tagging: {video_id}")

        try:
            self.driver.get(edit_url)
            time_module.sleep(3)

            if not self._wait_for_page_content(timeout=10):
                logger.warning(f"[DOM] Edit page did not load for {video_id}")
                return False

            # Click "Show more" to reveal tags field (it's hidden by default)
            show_more = self.driver.execute_script("""
                const buttons = document.querySelectorAll('button, ytcp-button');
                for (const btn of buttons) {
                    const text = (btn.textContent || '').trim().toUpperCase();
                    if (text === 'SHOW MORE') {
                        btn.click();
                        return true;
                    }
                }
                return false;
            """)

            if show_more:
                time_module.sleep(1)

            # Clean tags: remove # prefix, join with commas
            clean_tags = [t.lstrip("#").strip() for t in tags if t.strip()]
            tags_string = ", ".join(clean_tags)

            # Find tags input and append
            result = self.driver.execute_script(f"""
                // Tags field is an input inside the "Tags" section
                const inputs = document.querySelectorAll('input[aria-label*="Tag"], input.tags-input, input#tags-input');
                for (const input of inputs) {{
                    const existing = (input.value || '').trim();
                    const separator = existing ? ', ' : '';
                    const newValue = existing + separator + "{tags_string.replace('"', '\\"')}";
                    input.value = newValue;
                    input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    return {{success: true, tags_count: {len(clean_tags)}}};
                }}

                // Fallback: try text-input style
                const textInputs = document.querySelectorAll('ytcp-chip-bar input');
                for (const input of textInputs) {{
                    input.value = "{tags_string.replace('"', '\\"')}";
                    input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    return {{success: true, method: 'chip-bar'}};
                }}

                return {{success: false, error: 'tags_input_not_found'}};
            """)

            if not result or not result.get("success"):
                logger.warning(f"[DOM] Tags input not found for {video_id}")
                return False

            logger.info(f"[DOM] Applied {len(clean_tags)} tags to {video_id}")

            # Save
            time_module.sleep(0.5)
            self.click_save()
            time_module.sleep(2)
            return True

        except Exception as e:
            logger.error(f"[DOM] Tag update failed for {video_id}: {e}")
            return False
