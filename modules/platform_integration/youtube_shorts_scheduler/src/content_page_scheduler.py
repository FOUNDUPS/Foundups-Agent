"""
Content Page Scheduler — Schedule/Reschedule videos from YouTube Studio Content table.

NAVIGATION: Standalone scheduler operating on the Studio Content page (video list view).
-> Uses: YouTubeStudioDOM (date/time picker reuse), channel_config, schedule_tracker
-> Called by: launch.py (as fallback), or standalone via CLI
-> Architecture: WSP 3 (platform_integration), WSP 49 (module structure)

WHY THIS EXISTS (vs. existing Video Edit Page scheduler):
1. FASTER: No per-video page navigation — stays on content table, clicks inline popup
2. RESCHEDULE: Can change dates on already-scheduled videos (calendar slot optimization)
3. CALENDAR AUDIT: Reads scheduled dates from table, detects conflicts and gaps
4. FALLBACK: When individual video page scheduling fails (click_save timeout etc.)

DOM Flow (Content Page):
1. Navigate to Studio Content page with filters (Shorts + Unlisted/Private)
2. Sort by date (oldest first)
3. For each row: click visibility edit triangle → popup opens
4. In popup: expand schedule section → set date → set time → click "Schedule"
5. F5 to refresh — scheduled video disappears from unlisted list

The popup uses the SAME ytcp-visibility-scheduler > ytcp-datetime-picker components
as the individual video edit page, so set_schedule_date/set_schedule_time reuse works.
"""

import asyncio
import logging
import os
import re
import time as time_module
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    StaleElementReferenceException,
    ElementClickInterceptedException,
)

logger = logging.getLogger(__name__)


# ============================================================
# CONTENT PAGE SELECTORS (specific to list-view popup)
# ============================================================

class ContentPageSelectors:
    """
    DOM selectors specific to the Content Page inline scheduling popup.

    These are DIFFERENT from DOMSelectors in dom_automation.py which target
    the full video edit page dialog. The content page uses a lighter popup
    (ytcp-video-visibility-edit-popup) that opens inline on the row.
    """

    # --- Row-level visibility edit trigger ---
    # Each ytcp-video-row has a visibility cell with an editable wrapper div.
    # 2026-02-04: Live DOM confirms the clickable element is the wrapper div itself
    # (div.icon-text-edit-triangle-wrap.editable), NOT a child ytcp-icon-button.
    # Clicking the wrapper opens the inline scheduling popup.
    VISIBILITY_EDIT_TRIANGLE_CSS = (
        "div.icon-text-edit-triangle-wrap.editable"
    )
    VISIBILITY_EDIT_TRIANGLE_XPATH = (
        ".//div[contains(@class,'icon-text-edit-triangle-wrap') and contains(@class,'editable')]"
    )
    # Fallback: target the cell itself
    VISIBILITY_CELL_CSS = "div.tablecell-visibility"

    # --- Inline scheduling popup ---
    POPUP_DIALOG_CSS = "ytcp-video-visibility-edit-popup tp-yt-paper-dialog#dialog"
    POPUP_DIALOG_XPATH = "//ytcp-video-visibility-edit-popup//tp-yt-paper-dialog[@id='dialog']"

    # Schedule expand button inside popup
    # (the dropdown arrow that opens the schedule date/time section)
    SCHEDULE_EXPAND_CSS = (
        "ytcp-video-visibility-edit-popup "
        "ytcp-icon-button#second-container-expand-button"
    )
    SCHEDULE_EXPAND_XPATH = (
        "//ytcp-video-visibility-edit-popup"
        "//ytcp-icon-button[@id='second-container-expand-button']"
    )

    # Schedule radio button in popup (select "From private to public")
    # 2026-02-04: Live DOM confirms name="PUBLISH_FROM_PRIVATE" (no name="SCHEDULE" exists)
    SCHEDULE_RADIO_XPATH = (
        "//ytcp-video-visibility-edit-popup"
        "//tp-yt-paper-radio-button[@name='PUBLISH_FROM_PRIVATE']"
    )

    # Date picker trigger inside popup
    POPUP_DATE_TRIGGER_CSS = (
        "ytcp-video-visibility-edit-popup "
        "ytcp-visibility-scheduler ytcp-text-dropdown-trigger#datepicker-trigger "
        "ytcp-dropdown-trigger div.left-container"
    )

    # Date picker input (shared with video edit page — same component)
    POPUP_DATE_INPUT_CSS = "ytcp-date-picker tp-yt-paper-dialog#dialog input.tp-yt-paper-input"

    # Time input inside popup
    POPUP_TIME_INPUT_CSS = (
        "ytcp-video-visibility-edit-popup "
        "ytcp-visibility-scheduler ytcp-datetime-picker form#form "
        "ytcp-form-input-container#time-of-day-container input.tp-yt-paper-input"
    )

    # "Schedule" / "Save" button in popup (NOT the page-level save button)
    POPUP_SAVE_BUTTON_CSS = (
        "ytcp-video-visibility-edit-popup ytcp-button#save-button"
    )
    POPUP_SAVE_BUTTON_XPATH = (
        "//ytcp-video-visibility-edit-popup//ytcp-button[@id='save-button']"
    )

    # "Cancel" button in popup
    POPUP_CANCEL_XPATH = (
        "//ytcp-video-visibility-edit-popup//ytcp-button[@id='cancel-button']"
    )

    # --- Video row data extraction ---
    # 2026-02-04: Live DOM confirms title is a#video-title (not a[href*='/edit'] which matches thumbnail)
    VIDEO_TITLE_LINK = "a#video-title"
    # 2026-02-04: Live DOM confirms date is in div.tablecell-date (not td)
    VIDEO_DATE_CELL_CSS = "div.tablecell-date"
    VIDEO_DATE_CELL_XPATH = ".//div[contains(@class,'tablecell-date')]"
    # 2026-02-04: Live DOM confirms visibility text is in span.label-span inside the edit-triangle-wrap
    VISIBILITY_SPAN_CSS = "div.icon-text-edit-triangle-wrap span.label-span"
    VISIBILITY_SPAN_XPATH = ".//div[contains(@class,'icon-text-edit-triangle-wrap')]//span[contains(@class,'label-span')]"

    # Scheduled date display in row (when visibility = Scheduled)
    SCHEDULED_DATE_TEXT_XPATH = (
        ".//div[contains(@class,'tablecell-date')]"
    )

    # --- Filter bar UI selectors ---
    # 2026-02-04: Live DOM confirmed. URL filter params cause blank screen;
    # must use the sidebar Filter UI instead.
    # Flow: click filter icon → dropdown shows categories → click "Visibility" →
    #       sub-panel with checkboxes (Public/Private/Unlisted/Members/Has schedule/Draft)
    #       → check desired option → click Apply
    FILTER_ICON_CSS = "#filter-icon"
    FILTER_ITEM_TAG = "tp-yt-paper-item"  # Menu items in filter dropdown
    FILTER_CHECKBOX_TAG = "tp-yt-paper-checkbox"  # Checkboxes in sub-panel
    FILTER_APPLY_BUTTON_XPATH = "//div[contains(@class,'filter')]//button[contains(.,'Apply')] | //ytcp-button[contains(.,'Apply')]"

    # Visibility filter option text → checkbox label mapping
    VISIBILITY_FILTER_MAP = {
        "UNLISTED": "Unlisted",
        "PRIVATE": "Private",
        "PUBLIC": "Public",
        "SCHEDULED": "Has schedule",
        "DRAFT": "Draft",
        "MEMBERS": "Members",
    }

    # --- Sidebar navigation selectors ---
    # 2026-02-04: Agentic navigation uses left sidebar + tab bar instead of URLs.
    # Flow: click "Content" in sidebar → click "Shorts" or "Videos" tab
    SIDEBAR_CONTENT_XPATH = "//a[contains(@href,'/videos')]//tp-yt-paper-item | //ytcp-ve[@ve-type='MENU_ITEM']//a[contains(.,'Content')]"
    CONTENT_TAB_SHORTS_XPATH = "//a[contains(@class,'tab') and contains(.,'Shorts')] | //tp-yt-paper-tab[contains(.,'Shorts')]"
    CONTENT_TAB_VIDEOS_XPATH = "//a[contains(@class,'tab') and contains(.,'Videos')] | //tp-yt-paper-tab[contains(.,'Videos')]"
    CONTENT_TAB_LIVE_XPATH = "//a[contains(@class,'tab') and contains(.,'Live')] | //tp-yt-paper-tab[contains(.,'Live')]"

    CONTENT_TAB_MAP = {
        "short": "Shorts",
        "upload": "Videos",
        "live": "Live",
    }


class ContentPageScheduler:
    """
    Schedule videos directly from the YouTube Studio Content page table.

    Operates on the video list view instead of navigating to individual
    video edit pages. Faster for bulk scheduling and supports rescheduling.

    Usage:
        cps = ContentPageScheduler(driver, dom)
        cps.navigate_to_content("move2japan", visibility="UNLISTED")
        results = await cps.schedule_all_visible(time_slots, max_per_day=3)

    Or for calendar audit:
        audit = cps.audit_calendar("move2japan")
        # Returns conflicts, gaps, recommendations
    """

    def __init__(self, driver, dom=None):
        """
        Args:
            driver: Selenium WebDriver instance (Chrome or Edge)
            dom: Optional YouTubeStudioDOM instance for date/time picker reuse.
                 If None, creates a new one.
        """
        self.driver = driver
        self.sel = ContentPageSelectors()

        # Reuse existing DOM automation for date/time pickers
        if dom is None:
            from .dom_automation import YouTubeStudioDOM
            self.dom = YouTubeStudioDOM(driver)
        else:
            self.dom = dom

        # Human behavior delays (configurable via env)
        self._pre_click_delay = float(os.getenv("YT_CPS_PRE_CLICK_DELAY", "0.3"))
        self._post_click_delay = float(os.getenv("YT_CPS_POST_CLICK_DELAY", "0.5"))

    # ============================================================
    # NAVIGATION
    # ============================================================

    def navigate_to_content(
        self,
        channel_key: str,
        content_type: str = "short",
        visibility: str = "UNLISTED",
        sort_oldest_first: bool = True,
    ) -> bool:
        """
        Navigate to Studio Content page and apply filter via sidebar UI.

        2026-02-04: URL filter params cause blank screen. Uses agentic navigation:
        1. Navigate to base Studio URL (no filter params)
        2. Click "Content" sidebar if not already on content page
        3. Click content type tab (Shorts/Videos/Live)
        4. Apply visibility filter via sidebar Filter dropdown UI

        Args:
            channel_key: "move2japan", "undaodu", "foundups", "antifafm"
            content_type: "short" (Shorts), "upload" (Videos), "live" (Live)
            visibility: "UNLISTED", "PRIVATE", "SCHEDULED", "PUBLIC", or None
            sort_oldest_first: If True, sorts by date ascending (oldest first)

        Returns:
            True if navigation successful
        """
        from .channel_config import get_channel_config

        config = get_channel_config(channel_key)
        if not config:
            logger.error(f"[CPS] Unknown channel: {channel_key}")
            return False

        # Navigate to base Studio URL (NO filter params — they cause blank screen)
        base_url = f"https://studio.youtube.com/channel/{config['id']}/videos/{content_type}"
        logger.info(f"[CPS] Navigating to {channel_key} content page ({content_type})")

        try:
            # Check if already on this channel's studio — avoid full reload
            current_url = self.driver.current_url or ""
            if config["id"] in current_url and "/videos" in current_url:
                logger.debug("[CPS] Already on Studio content — switching tab only")
                self._switch_content_tab(content_type)
            else:
                self.driver.get(base_url)
                time_module.sleep(3)

            # Wait for video table to load
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "ytcp-video-row"))
            )
            logger.info(f"[CPS] Content page loaded — video rows visible")

            # Apply visibility filter via sidebar UI (if specified)
            if visibility:
                if not self._apply_visibility_filter_via_ui(visibility):
                    logger.warning(f"[CPS] Filter '{visibility}' failed — continuing unfiltered")

            return True
        except TimeoutException:
            logger.warning(f"[CPS] Content page load timeout — no video rows found")
            return False
        except Exception as e:
            logger.error(f"[CPS] Navigation failed: {e}")
            return False

    def _switch_content_tab(self, content_type: str) -> bool:
        """
        Switch between content tabs (Shorts/Videos/Live) without page reload.

        Args:
            content_type: "short", "upload", or "live"

        Returns:
            True if tab switched
        """
        tab_label = self.sel.CONTENT_TAB_MAP.get(content_type, "Shorts")
        try:
            # Find tab by text content
            tabs = self.driver.find_elements(By.CSS_SELECTOR, "a[role='tab'], tp-yt-paper-tab")
            for tab in tabs:
                if tab.text.strip() == tab_label and tab.is_displayed():
                    self.dom.safe_click(tab)
                    time_module.sleep(2)
                    logger.debug(f"[CPS] Switched to {tab_label} tab")
                    return True

            logger.debug(f"[CPS] Tab '{tab_label}' not found — may already be active")
            return False
        except Exception as e:
            logger.debug(f"[CPS] Tab switch failed: {e}")
            return False

    def _apply_visibility_filter_via_ui(self, visibility: str) -> bool:
        """
        Apply a visibility filter using the sidebar Filter dropdown UI.

        2026-02-04: Live DOM confirmed flow:
        1. Click filter icon (#filter-icon) → dropdown with categories
        2. Click "Visibility" item → sub-panel with checkboxes
        3. Check the desired checkbox (e.g., "Unlisted", "Has schedule")
        4. Click "Apply" button

        Args:
            visibility: "UNLISTED", "PRIVATE", "SCHEDULED", "PUBLIC", "DRAFT"

        Returns:
            True if filter applied successfully
        """
        checkbox_label = self.sel.VISIBILITY_FILTER_MAP.get(visibility)
        if not checkbox_label:
            logger.warning(f"[CPS] Unknown visibility filter: {visibility}")
            return False

        try:
            # Step 1: Click filter icon to open dropdown
            filter_icon = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, self.sel.FILTER_ICON_CSS))
            )
            self.dom.safe_click(filter_icon)
            time_module.sleep(0.5)

            # Step 2: Click "Visibility" in the dropdown menu
            items = WebDriverWait(self.driver, 5).until(
                EC.presence_of_all_elements_located(
                    (By.TAG_NAME, self.sel.FILTER_ITEM_TAG)
                )
            )
            visibility_item = None
            for item in items:
                if item.text.strip() == "Visibility" and item.is_displayed():
                    visibility_item = item
                    break

            if not visibility_item:
                logger.warning("[CPS] 'Visibility' not found in filter dropdown")
                return False

            self.dom.safe_click(visibility_item)
            time_module.sleep(0.5)

            # Step 3: Check the desired checkbox
            checkboxes = WebDriverWait(self.driver, 5).until(
                EC.presence_of_all_elements_located(
                    (By.TAG_NAME, self.sel.FILTER_CHECKBOX_TAG)
                )
            )
            target_cb = None
            for cb in checkboxes:
                if cb.text.strip() == checkbox_label and cb.is_displayed():
                    target_cb = cb
                    break

            if not target_cb:
                logger.warning(f"[CPS] Checkbox '{checkbox_label}' not found in Visibility panel")
                return False

            # Only click if not already checked
            is_checked = (
                target_cb.get_attribute("checked") is not None
                or target_cb.get_attribute("aria-checked") == "true"
            )
            if not is_checked:
                self.dom.safe_click(target_cb)
                time_module.sleep(0.3)

            # Step 4: Click Apply
            try:
                apply_btn = WebDriverWait(self.driver, 3).until(
                    EC.element_to_be_clickable(
                        (By.XPATH, self.sel.FILTER_APPLY_BUTTON_XPATH)
                    )
                )
                self.dom.safe_click(apply_btn)
            except TimeoutException:
                # Some filter panels auto-apply without a button
                logger.debug("[CPS] No Apply button found — filter may auto-apply")

            time_module.sleep(2)

            # Verify rows reloaded
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "ytcp-video-row"))
            )
            logger.info(f"[CPS] Visibility filter '{visibility}' ({checkbox_label}) applied")
            return True

        except TimeoutException:
            logger.warning(f"[CPS] Timeout applying filter '{visibility}'")
            return False
        except Exception as e:
            logger.warning(f"[CPS] Filter application failed: {e}")
            return False

    def navigate_to_scheduled(self, channel_key: str) -> bool:
        """Navigate to Scheduled Shorts for calendar audit."""
        return self.navigate_to_content(
            channel_key,
            content_type="short",
            visibility="SCHEDULED",
            sort_oldest_first=True,
        )

    # ============================================================
    # ROW OPERATIONS
    # ============================================================

    def get_video_rows_with_data(self) -> List[Dict]:
        """
        Extract all video rows with metadata from the content table.

        Returns:
            List of dicts: {video_id, title, visibility, date_text, row_element}
        """
        rows = self.driver.find_elements(By.CSS_SELECTOR, "ytcp-video-row")
        results = []

        for row in rows:
            try:
                # Video ID from edit link
                link = row.find_element(By.CSS_SELECTOR, self.sel.VIDEO_TITLE_LINK)
                href = link.get_attribute("href") or ""
                video_id = ""
                if "/video/" in href:
                    video_id = href.split("/video/")[1].split("/")[0]
                title = link.text.strip()

                # Visibility text (2026-02-04: use label-span inside edit-triangle-wrap)
                visibility = ""
                try:
                    vis_span = row.find_element(By.CSS_SELECTOR, self.sel.VISIBILITY_SPAN_CSS)
                    visibility = vis_span.text.strip().capitalize()
                except Exception:
                    # Fallback: search all spans
                    try:
                        vis_spans = row.find_elements(By.XPATH, ".//span")
                        for span in vis_spans:
                            text = span.text.strip().lower()
                            if text in ("unlisted", "private", "public", "scheduled", "draft"):
                                visibility = text.capitalize()
                                break
                    except Exception:
                        pass

                # Date text (2026-02-04: use div.tablecell-date, not td)
                date_text = ""
                try:
                    date_el = row.find_element(By.CSS_SELECTOR, self.sel.VIDEO_DATE_CELL_CSS)
                    date_text = date_el.text.strip().split("\n")[0]  # First line is date, second is "Uploaded"
                except Exception:
                    pass

                results.append({
                    "video_id": video_id,
                    "title": title[:60],
                    "visibility": visibility,
                    "date_text": date_text,
                    "row_element": row,
                })
            except StaleElementReferenceException:
                continue
            except Exception as e:
                logger.debug(f"[CPS] Row parse error: {e}")

        logger.info(f"[CPS] Found {len(results)} video rows on content page")
        return results

    def _click_visibility_edit_on_row(self, row_element) -> bool:
        """
        Click the visibility edit triangle on a specific video row.
        Opens the inline scheduling popup.

        Args:
            row_element: Selenium WebElement for the ytcp-video-row

        Returns:
            True if popup opened
        """
        try:
            time_module.sleep(self._pre_click_delay)

            # Strategy 1: Find edit triangle icon within the row
            try:
                edit_btn = row_element.find_element(
                    By.XPATH, self.sel.VISIBILITY_EDIT_TRIANGLE_XPATH
                )
                self.dom.safe_click(edit_btn)
                time_module.sleep(self._post_click_delay)
            except NoSuchElementException:
                # Strategy 2: Click the visibility cell (hover may reveal triangle)
                from selenium.webdriver.common.action_chains import ActionChains
                vis_cell = row_element.find_element(
                    By.CSS_SELECTOR, self.sel.VISIBILITY_CELL_CSS
                )
                ActionChains(self.driver).move_to_element(vis_cell).perform()
                time_module.sleep(0.5)
                # Re-try finding the edit triangle after hover
                edit_btn = row_element.find_element(
                    By.XPATH, self.sel.VISIBILITY_EDIT_TRIANGLE_XPATH
                )
                self.dom.safe_click(edit_btn)
                time_module.sleep(self._post_click_delay)

            # Verify popup opened
            try:
                WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, self.sel.POPUP_DIALOG_CSS)
                    )
                )
                logger.debug("[CPS] Visibility popup opened")
                return True
            except TimeoutException:
                logger.warning("[CPS] Visibility popup did not open after click")
                return False

        except Exception as e:
            logger.warning(f"[CPS] Failed to click visibility edit: {e}")
            return False

    def _expand_schedule_in_popup(self) -> bool:
        """
        In the visibility popup, select/expand the Schedule option.

        Returns:
            True if schedule section is visible with date/time inputs
        """
        try:
            # Click the schedule radio button
            try:
                radio = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable(
                        (By.XPATH, self.sel.SCHEDULE_RADIO_XPATH)
                    )
                )
                self.dom.safe_click(radio)
                time_module.sleep(0.5)
            except TimeoutException:
                # Maybe schedule is already selected — try expand button
                pass

            # Click expand button to reveal date/time picker
            try:
                expand_btn = WebDriverWait(self.driver, 3).until(
                    EC.element_to_be_clickable(
                        (By.CSS_SELECTOR, self.sel.SCHEDULE_EXPAND_CSS)
                    )
                )
                self.dom.safe_click(expand_btn)
                time_module.sleep(0.5)
            except TimeoutException:
                # Date/time may already be visible (no expand needed)
                pass

            # Verify date picker is visible
            try:
                WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR,
                         "ytcp-video-visibility-edit-popup ytcp-datetime-picker")
                    )
                )
                logger.debug("[CPS] Schedule section expanded — date/time picker visible")
                return True
            except TimeoutException:
                logger.warning("[CPS] Schedule date/time picker not visible after expand")
                return False

        except Exception as e:
            logger.warning(f"[CPS] Failed to expand schedule in popup: {e}")
            return False

    def _set_date_in_popup(self, date_str: str) -> bool:
        """
        Set the schedule date in the content page popup.

        Reuses dom.set_schedule_date() since the popup uses the same
        ytcp-datetime-picker component.

        Args:
            date_str: Date like "Feb 5, 2026"
        """
        try:
            self.dom.set_schedule_date(date_str)
            return True
        except Exception as e:
            logger.warning(f"[CPS] Failed to set date '{date_str}': {e}")
            return False

    def _set_time_in_popup(self, time_str: str) -> bool:
        """
        Set the schedule time in the content page popup.

        Reuses dom.set_schedule_time() since the popup uses the same
        ytcp-datetime-picker component.

        Args:
            time_str: Time like "5:00 PM"
        """
        try:
            self.dom.set_schedule_time(time_str)
            return True
        except Exception as e:
            logger.warning(f"[CPS] Failed to set time '{time_str}': {e}")
            return False

    def _click_popup_schedule_button(self) -> bool:
        """
        Click the "Schedule" / "Save" button in the visibility popup.

        This is the popup-level save (NOT the page-level save button).

        Returns:
            True if button clicked
        """
        try:
            pre_save_delay = float(os.getenv("YT_CPS_PRE_SAVE_DELAY", "1.0"))
            time_module.sleep(pre_save_delay)

            # Strategy 1: CSS selector
            try:
                btn = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable(
                        (By.CSS_SELECTOR, self.sel.POPUP_SAVE_BUTTON_CSS)
                    )
                )
                self.dom.safe_click(btn)
                time_module.sleep(1.0)
                logger.debug("[CPS] Popup schedule button clicked (CSS)")
                return True
            except TimeoutException:
                pass

            # Strategy 2: XPath
            try:
                btn = WebDriverWait(self.driver, 3).until(
                    EC.element_to_be_clickable(
                        (By.XPATH, self.sel.POPUP_SAVE_BUTTON_XPATH)
                    )
                )
                self.dom.safe_click(btn)
                time_module.sleep(1.0)
                logger.debug("[CPS] Popup schedule button clicked (XPath)")
                return True
            except TimeoutException:
                pass

            # Strategy 3: JavaScript click on any button with "Schedule" text in popup
            try:
                btn = self.driver.find_element(
                    By.XPATH,
                    "//ytcp-video-visibility-edit-popup"
                    "//button[.//span[contains(text(),'Schedule') or contains(text(),'Save')]]"
                )
                self.driver.execute_script("arguments[0].click();", btn)
                time_module.sleep(1.0)
                logger.debug("[CPS] Popup schedule button clicked (JS fallback)")
                return True
            except Exception:
                pass

            logger.error("[CPS] Could not find/click popup schedule button")
            return False

        except Exception as e:
            logger.error(f"[CPS] Popup schedule click failed: {e}")
            return False

    def _dismiss_popup(self):
        """Dismiss the visibility popup if still open (ESC key)."""
        try:
            from selenium.webdriver.common.action_chains import ActionChains
            ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()
            time_module.sleep(0.3)
        except Exception:
            pass

    def reschedule_row_inline(self, row_element, new_date: str, new_time: str) -> bool:
        """
        Reschedule an already-scheduled video via the inline popup (no edit page nav).

        2026-02-04: For scheduled videos, the popup opens with the Schedule section
        already expanded showing current date/time. We just change the values and
        click Schedule.

        Flow:
        1. Click edit triangle on row → popup opens with schedule pre-expanded
        2. Click date picker → change date
        3. Clear time input → type new time
        4. Click "Schedule" button
        5. ESC to dismiss if needed

        Args:
            row_element: The ytcp-video-row Selenium element
            new_date: Target date like "Feb 5, 2026"
            new_time: Target time like "2:00 PM"

        Returns:
            True if rescheduled successfully
        """
        try:
            # Step 1: Open the popup
            if not self._click_visibility_edit_on_row(row_element):
                return False
            time_module.sleep(1.0)

            # Step 2: Set the new date (reuse dom's date picker)
            if not self._set_date_in_popup(new_date):
                logger.warning("[CPS-RESCHED] Failed to set date — dismissing popup")
                self._dismiss_popup()
                return False
            time_module.sleep(0.5)

            # Step 3: Set the new time (reuse dom's time setter)
            if not self._set_time_in_popup(new_time):
                logger.warning("[CPS-RESCHED] Failed to set time — dismissing popup")
                self._dismiss_popup()
                return False
            time_module.sleep(0.5)

            # Step 4: Click Schedule button
            if not self._click_popup_schedule_button():
                logger.warning("[CPS-RESCHED] Failed to click Schedule — dismissing popup")
                self._dismiss_popup()
                return False

            logger.info(f"[CPS-RESCHED] Rescheduled via inline popup → {new_date} {new_time}")
            return True

        except Exception as e:
            logger.error(f"[CPS-RESCHED] Inline reschedule failed: {e}")
            self._dismiss_popup()
            return False

    def refresh_page(self):
        """F5 refresh after scheduling. Scheduled videos disappear from unlisted list."""
        try:
            from selenium.webdriver.common.action_chains import ActionChains
            ActionChains(self.driver).send_keys(Keys.F5).perform()
            time_module.sleep(3)
            # Wait for table to reload
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "ytcp-video-row"))
            )
            logger.info("[CPS] Page refreshed — table reloaded")
        except TimeoutException:
            logger.info("[CPS] Page refreshed — no rows found (all scheduled?)")
        except Exception as e:
            logger.warning(f"[CPS] Refresh failed: {e}")

    # ============================================================
    # MAIN SCHEDULING METHOD
    # ============================================================

    async def schedule_video_from_row(
        self,
        row_element,
        date_str: str,
        time_str: str,
        video_id: str = "unknown",
    ) -> bool:
        """
        Schedule a single video from its content page row.

        Full flow:
        1. Click visibility edit triangle on the row
        2. Expand schedule section in popup
        3. Set date
        4. Set time
        5. Click "Schedule" button in popup

        Args:
            row_element: Selenium WebElement for the ytcp-video-row
            date_str: Date like "Feb 5, 2026"
            time_str: Time like "5:15 PM"
            video_id: For logging purposes

        Returns:
            True if all steps succeeded
        """
        workflow_start = time_module.time()
        logger.info(f"[CPS] Scheduling {video_id} → {date_str} @ {time_str}")

        steps = [
            ("click_visibility_edit", lambda: self._click_visibility_edit_on_row(row_element)),
            ("expand_schedule", lambda: self._expand_schedule_in_popup()),
            ("set_date", lambda: self._set_date_in_popup(date_str)),
            ("set_time", lambda: self._set_time_in_popup(time_str)),
            ("click_schedule", lambda: self._click_popup_schedule_button()),
        ]

        step_times = []
        for step_name, fn in steps:
            step_start = time_module.time()
            try:
                result = fn()
                elapsed = time_module.time() - step_start
                step_times.append((step_name, elapsed))

                if result is False:
                    logger.error(f"[CPS] Step '{step_name}' returned False for {video_id}")
                    self._dismiss_popup()
                    return False

                logger.debug(f"[CPS] Step '{step_name}' OK ({elapsed:.1f}s)")
            except Exception as e:
                elapsed = time_module.time() - step_start
                logger.error(
                    f"[CPS] Step '{step_name}' failed for {video_id}: "
                    f"{type(e).__name__}: {e} ({elapsed:.1f}s)"
                )
                self._dismiss_popup()
                return False

        total_time = time_module.time() - workflow_start
        timing = ", ".join(f"{n}:{t:.1f}s" for n, t in step_times)
        logger.info(f"[CPS] Scheduled {video_id} → {date_str} {time_str} in {total_time:.1f}s [{timing}]")
        return True

    async def schedule_all_visible(
        self,
        tracker,
        time_slots: List[str],
        max_per_day: int = 8,
        max_videos: int = 9999,
        stop_event=None,
        channel_tz: Optional[str] = None,
    ) -> Dict:
        """
        Schedule all visible unlisted videos on the current content page.

        Args:
            tracker: ScheduleTracker instance for slot management
            time_slots: Canonical US-Eastern (ET) peak slots, e.g.
                ["08:00", "12:00", "20:00"]. These describe the desired
                US-audience publish time in ET (also accepts 12h "8:00 AM").
            max_per_day: Max videos per day
            max_videos: Max total videos to schedule
            stop_event: Optional threading.Event for cooperative abort
            channel_tz: IANA tz of the channel's Studio account
                (e.g. "Asia/Tokyo", "America/New_York"). When provided, each ET
                base slot is converted (DST-aware) to that account's local
                wall-clock before the bare time is typed into Studio, so
                long-form publishes at the US-ET peak for EVERY channel -- the
                same contract the shorts path uses (#847). When None the slot is
                typed as-is (backwards compatible).

        Returns:
            Dict with scheduled count, errors, video details
        """
        results = {
            "total_scheduled": 0,
            "total_errors": 0,
            "total_skipped": 0,
            "scheduled": [],
            "errors": [],
        }

        rows = self.get_video_rows_with_data()
        unlisted_rows = [r for r in rows if r["visibility"].lower() in ("unlisted", "private")]

        if not unlisted_rows:
            logger.info("[CPS] No unlisted/private videos found on content page")
            return results

        logger.info(f"[CPS] Found {len(unlisted_rows)} schedulable videos")

        for i, row_data in enumerate(unlisted_rows):
            if i >= max_videos:
                logger.info(f"[CPS] Reached max_videos limit ({max_videos})")
                break

            if stop_event is not None and stop_event.is_set():
                logger.info("[CPS] Stop signal received — aborting")
                break

            video_id = row_data["video_id"]
            title = row_data["title"]

            # Skip if already tracked
            if tracker.is_video_scheduled(video_id):
                logger.debug(f"[CPS] Skipping {video_id} — already scheduled in tracker")
                results["total_skipped"] += 1
                continue

            # Get next available slot. Forward channel_tz so the canonical ET
            # peak slot is DST-converted to the channel account's local
            # wall-clock before typing (identity for ET-account channels;
            # shifts for Asia/Tokyo etc.). Mirrors the shorts path (#847).
            slot = tracker.get_next_available_slot(
                time_slots, max_per_day, channel_tz=channel_tz
            )
            if slot is None:
                logger.warning("[CPS] No more available slots — stopping")
                break

            date_str, time_str = slot

            # Schedule it
            try:
                success = await self.schedule_video_from_row(
                    row_element=row_data["row_element"],
                    date_str=date_str,
                    time_str=time_str,
                    video_id=video_id,
                )

                if success:
                    tracker.increment(date_str, video_id)
                    results["total_scheduled"] += 1
                    results["scheduled"].append({
                        "video_id": video_id,
                        "title": title,
                        "date": date_str,
                        "time": time_str,
                    })
                    logger.info(f"[CPS] [{i+1}/{len(unlisted_rows)}] {video_id} → {date_str} {time_str}")
                else:
                    results["total_errors"] += 1
                    results["errors"].append({"video_id": video_id, "reason": "step_failed"})

            except Exception as e:
                logger.error(f"[CPS] Error scheduling {video_id}: {e}")
                results["total_errors"] += 1
                results["errors"].append({"video_id": video_id, "reason": str(e)})

            # Human delay between videos
            delay = self.dom.human_delay(2.0, 1.0)
            await asyncio.sleep(delay)

            # Refresh page after each successful schedule (row disappears)
            if results["total_scheduled"] > 0 and results["total_scheduled"] % 3 == 0:
                self.refresh_page()
                # Re-fetch rows after refresh (stale elements)
                rows = self.get_video_rows_with_data()
                unlisted_rows = [r for r in rows if r["visibility"].lower() in ("unlisted", "private")]
                # Adjust index (rows changed after refresh)
                break  # Re-enter loop from schedule_all_visible caller if needed

        return results

    # ============================================================
    # CALENDAR AUDIT
    # ============================================================

    def audit_calendar(self, channel_key: str, max_per_day: int = 3) -> Dict:
        """
        Audit the scheduling calendar for a channel.

        Navigates to Scheduled Shorts, reads all scheduled dates/times,
        and detects:
        - Conflicts: Multiple videos at the same time slot
        - Gaps: Empty slots in the schedule
        - Clustering: Too many videos on one day

        Args:
            channel_key: "move2japan", "undaodu", etc.

        Returns:
            Dict with conflicts, gaps, recommendations
        """
        logger.info(f"[CPS-AUDIT] Auditing calendar for {channel_key}")

        # Navigate to scheduled shorts
        if not self.navigate_to_scheduled(channel_key):
            return {"error": "navigation_failed", "conflicts": [], "gaps": []}

        # Collect all scheduled videos across pages
        all_scheduled = []
        page = 1
        while True:
            try:
                self.dom.set_page_size(50)
            except Exception:
                pass

            videos = self.dom.get_scheduled_videos_detailed()
            all_scheduled.extend(videos)
            logger.info(f"[CPS-AUDIT] Page {page}: {len(videos)} scheduled videos")

            if self.dom.has_next_page():
                self.dom.click_next_page()
                time_module.sleep(2)
                page += 1
            else:
                break

        logger.info(f"[CPS-AUDIT] Total scheduled: {len(all_scheduled)} videos")

        # Analyze: group by date+time
        slot_map = defaultdict(list)  # "Feb 5, 2026 3:00 PM" -> [video1, video2]
        date_map = defaultdict(list)  # "Feb 5, 2026" -> [video1, video2, ...]

        for video in all_scheduled:
            date = video.get("date", "")
            time_val = video.get("time", "")
            if date:
                date_map[date].append(video)
                if time_val:
                    slot_key = f"{date} {time_val}"
                    slot_map[slot_key].append(video)

        # Detect conflicts (same slot, multiple videos)
        conflicts = []
        for slot_key, videos in slot_map.items():
            if len(videos) > 1:
                conflicts.append({
                    "slot": slot_key,
                    "count": len(videos),
                    "videos": [
                        {"video_id": v["video_id"], "title": v.get("title", "")}
                        for v in videos
                    ],
                })

        # Detect heavy days (more than max_per_day)
        heavy_days = []
        for date, videos in date_map.items():
            if len(videos) > max_per_day:
                heavy_days.append({
                    "date": date,
                    "count": len(videos),
                    "excess": len(videos) - max_per_day,
                })

        # Build recommendations
        recommendations = []
        if conflicts:
            recommendations.append(
                f"CONFLICT: {len(conflicts)} time slots have multiple videos. "
                "Reschedule to spread them out."
            )
        if heavy_days:
            total_excess = sum(d["excess"] for d in heavy_days)
            recommendations.append(
                f"CLUSTERING: {len(heavy_days)} days exceed {max_per_day}/day limit "
                f"({total_excess} excess videos need redistribution)."
            )
        if not conflicts and not heavy_days:
            recommendations.append("Calendar looks clean — no conflicts or clustering detected.")

        audit_result = {
            "channel": channel_key,
            "total_scheduled": len(all_scheduled),
            "unique_dates": len(date_map),
            "max_per_day": max_per_day,
            "conflicts": conflicts,
            "heavy_days": heavy_days,
            "recommendations": recommendations,
            "date_map": {d: len(v) for d, v in sorted(date_map.items())},
            "videos": all_scheduled,
        }

        # Log summary
        logger.info(f"[CPS-AUDIT] Results for {channel_key}:")
        logger.info(f"[CPS-AUDIT]   Total scheduled: {len(all_scheduled)}")
        logger.info(f"[CPS-AUDIT]   Unique dates: {len(date_map)}")
        logger.info(f"[CPS-AUDIT]   Conflicts: {len(conflicts)}")
        logger.info(f"[CPS-AUDIT]   Heavy days: {len(heavy_days)}")
        for rec in recommendations:
            logger.info(f"[CPS-AUDIT]   → {rec}")

        return audit_result

    async def resolve_conflicts(
        self,
        conflicts: List[Dict],
        tracker,
        time_slots: List[str],
        max_per_day: int = 3,
    ) -> Dict:
        """
        Resolve scheduling conflicts by rescheduling duplicate-slot videos.

        When multiple videos share the same time slot, keeps the first one
        and reschedules the rest to the next available slot.

        Args:
            conflicts: List from audit_calendar()["conflicts"]
            tracker: ScheduleTracker instance
            time_slots: Available time slots
            max_per_day: Max per day limit

        Returns:
            Dict with rescheduled count and details
        """
        results = {"rescheduled": 0, "failed": 0, "details": []}

        for conflict in conflicts:
            # Keep first video, reschedule the rest
            videos_to_move = conflict["videos"][1:]  # Skip first (keep it)

            for video_info in videos_to_move:
                video_id = video_info["video_id"]
                slot = tracker.get_next_available_slot(time_slots, max_per_day)
                if slot is None:
                    logger.warning(f"[CPS-RESOLVE] No slots available for {video_id}")
                    results["failed"] += 1
                    continue

                new_date, new_time = slot
                logger.info(
                    f"[CPS-RESOLVE] Rescheduling {video_id} from "
                    f"{conflict['slot']} → {new_date} {new_time}"
                )

                # Navigate to the video's edit page for rescheduling
                # (Content page popup can also do this, but edit page is more reliable
                # for changing already-scheduled videos)
                try:
                    self.dom.navigate_to_video(video_id)
                    time_module.sleep(2)
                    success = self.dom.schedule_video(new_date, new_time)

                    if success:
                        tracker.increment(new_date, video_id)
                        results["rescheduled"] += 1
                        results["details"].append({
                            "video_id": video_id,
                            "from": conflict["slot"],
                            "to": f"{new_date} {new_time}",
                        })
                    else:
                        results["failed"] += 1
                except Exception as e:
                    logger.error(f"[CPS-RESOLVE] Rescheduling failed for {video_id}: {e}")
                    results["failed"] += 1

                await asyncio.sleep(self.dom.human_delay(2.0, 1.0))

        logger.info(
            f"[CPS-RESOLVE] Done: {results['rescheduled']} rescheduled, "
            f"{results['failed']} failed"
        )
        return results

    async def thin_schedule(
        self,
        audit_result: Dict,
        tracker,
        time_slots: List[str],
        max_per_day: int = 3,
    ) -> Dict:
        """
        Thin out overcrowded days by redistributing excess videos to future dates.

        2026-02-04: Created for schedule conflict management. When too many videos
        are scheduled on the same day (e.g., 8 shorts on Apr 3), this spreads
        them across subsequent days respecting the max_per_day limit.

        Algorithm:
        1. Sort heavy days by date
        2. For each heavy day, keep first max_per_day videos, move the rest
        3. Assign excess videos to the next available date/time slot
        4. Time spacing: at least 4 hours between videos on same day

        Args:
            audit_result: Dict from audit_calendar() with heavy_days and videos
            tracker: ScheduleTracker instance
            time_slots: Available time slots (e.g., ["8:00 AM", "2:00 PM", "8:00 PM"])
            max_per_day: Max videos per day (default 3 for shorts)

        Returns:
            Dict with rescheduled count and details
        """
        results = {"rescheduled": 0, "failed": 0, "skipped": 0, "details": []}

        heavy_days = audit_result.get("heavy_days", [])
        if not heavy_days:
            logger.info("[CPS-THIN] No heavy days — schedule is balanced")
            return results

        # Group videos by date from the audit
        all_videos = audit_result.get("videos", [])
        date_videos = defaultdict(list)
        for v in all_videos:
            date = v.get("date", "")
            if date:
                date_videos[date].append(v)

        # Sort heavy days chronologically
        heavy_days_sorted = sorted(heavy_days, key=lambda d: d["date"])
        total_excess = sum(d["excess"] for d in heavy_days_sorted)
        logger.info(
            f"[CPS-THIN] Thinning {total_excess} excess videos "
            f"from {len(heavy_days_sorted)} overcrowded days"
        )

        for day_info in heavy_days_sorted:
            date = day_info["date"]
            excess_count = day_info["excess"]
            day_videos = date_videos.get(date, [])

            if len(day_videos) <= max_per_day:
                continue

            # Keep first max_per_day, move the rest
            videos_to_move = day_videos[max_per_day:]
            logger.info(
                f"[CPS-THIN] {date}: keeping {max_per_day}, "
                f"moving {len(videos_to_move)} excess videos"
            )

            # Get current row elements on the page for inline popup rescheduling
            rows = self.driver.find_elements(By.CSS_SELECTOR, "ytcp-video-row")

            for idx, video_info in enumerate(videos_to_move):
                video_id = video_info.get("video_id", "")
                if not video_id:
                    results["skipped"] += 1
                    continue

                slot = tracker.get_next_available_slot(time_slots, max_per_day)
                if slot is None:
                    logger.warning(f"[CPS-THIN] No slots available for {video_id}")
                    results["failed"] += 1
                    continue

                new_date, new_time = slot
                logger.info(
                    f"[CPS-THIN] Moving {video_id}: {date} → {new_date} {new_time}"
                )

                # Find the row element for this video
                row_element = None
                for row in rows:
                    try:
                        link = row.find_element(By.CSS_SELECTOR, self.sel.VIDEO_TITLE_LINK)
                        href = link.get_attribute("href") or ""
                        if video_id in href:
                            row_element = row
                            break
                    except Exception:
                        continue

                if row_element:
                    # Use inline popup rescheduling (fast, stays on content page)
                    success = self.reschedule_row_inline(row_element, new_date, new_time)
                else:
                    # Fallback: navigate to edit page
                    logger.debug(f"[CPS-THIN] Row not found for {video_id}, using edit page")
                    try:
                        self.dom.navigate_to_video(video_id)
                        time_module.sleep(2)
                        success = self.dom.schedule_video(new_date, new_time)
                    except Exception as e:
                        logger.error(f"[CPS-THIN] Edit page reschedule failed: {e}")
                        success = False

                if success:
                    tracker.increment(new_date, video_id)
                    results["rescheduled"] += 1
                    results["details"].append({
                        "video_id": video_id,
                        "title": video_info.get("title", ""),
                        "from_date": date,
                        "to": f"{new_date} {new_time}",
                    })
                else:
                    results["failed"] += 1

                await asyncio.sleep(self.dom.human_delay(2.0, 1.0))

        logger.info(
            f"[CPS-THIN] Done: {results['rescheduled']} moved, "
            f"{results['failed']} failed, {results['skipped']} skipped"
        )
        return results


# ============================================================
# STANDALONE ENTRY POINT
# ============================================================

def run_content_page_scheduler(
    browser: str = "edge",
    channel_key: str = "foundups",
    mode: str = "schedule",
    max_videos: int = 9999,
    audit_only: bool = False,
    stop_event=None,
) -> Dict:
    """
    Standalone entry point for Content Page Scheduler.

    Can be called from CLI or as fallback from launch.py.

    Args:
        browser: "chrome" or "edge"
        channel_key: Channel to process
        mode: "schedule" or "audit"
        max_videos: Max videos to schedule
        audit_only: If True, only audit calendar (no scheduling)
        stop_event: Optional threading.Event for cooperative abort

    Returns:
        Dict with results
    """
    import asyncio
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from selenium.webdriver.edge.options import Options as EdgeOptions

    BROWSER_PORTS = {"chrome": 9222, "edge": 9223}
    port = BROWSER_PORTS.get(browser.lower(), 9222)

    print(f"\n[CPS] Content Page Scheduler")
    print(f"[CPS] Browser: {browser.upper()} (port {port})")
    print(f"[CPS] Channel: {channel_key}")
    print(f"[CPS] Mode: {'AUDIT ONLY' if audit_only else mode.upper()}")
    print("=" * 50)

    # Connect to browser
    try:
        if browser.lower() == "edge":
            options = EdgeOptions()
            options.add_experimental_option("debuggerAddress", f"127.0.0.1:{port}")
            driver = webdriver.Edge(options=options)
        else:
            options = ChromeOptions()
            options.add_experimental_option("debuggerAddress", f"127.0.0.1:{port}")
            driver = webdriver.Chrome(options=options)
        print(f"[CPS] Connected to {browser.upper()}")
    except Exception as e:
        print(f"[CPS] Connection failed: {e}")
        return {"error": str(e)}

    cps = ContentPageScheduler(driver)

    if audit_only:
        # Calendar audit mode
        audit_result = cps.audit_calendar(channel_key)
        print(f"\n[CPS-AUDIT] Calendar Report for {channel_key}")
        print(f"  Total scheduled: {audit_result.get('total_scheduled', 0)}")
        print(f"  Conflicts: {len(audit_result.get('conflicts', []))}")
        print(f"  Heavy days: {len(audit_result.get('heavy_days', []))}")
        for rec in audit_result.get("recommendations", []):
            print(f"  → {rec}")
        return audit_result

    # Scheduling mode
    from .channel_config import get_channel_config
    from .schedule_tracker import ScheduleTracker

    config = get_channel_config(channel_key)
    if not config:
        print(f"[CPS] Unknown channel: {channel_key}")
        return {"error": f"Unknown channel: {channel_key}"}

    tracker = ScheduleTracker(channel_key)
    time_slots = config.get("time_slots", [
        "12:00 AM", "3:00 AM", "6:00 AM", "9:00 AM",
        "12:00 PM", "3:00 PM", "6:00 PM", "9:00 PM",
    ])
    max_per_day = config.get("max_per_day", 8)

    # Navigate to content page
    if not cps.navigate_to_content(channel_key, visibility="UNLISTED"):
        # Try PRIVATE as fallback
        if not cps.navigate_to_content(channel_key, visibility="PRIVATE"):
            print("[CPS] Navigation failed for both UNLISTED and PRIVATE")
            return {"error": "navigation_failed"}

    # Schedule
    results = asyncio.run(
        cps.schedule_all_visible(
            tracker=tracker,
            time_slots=time_slots,
            max_per_day=max_per_day,
            max_videos=max_videos,
            stop_event=stop_event,
        )
    )

    print(f"\n[CPS] Results: {results['total_scheduled']} scheduled, "
          f"{results['total_errors']} errors, {results['total_skipped']} skipped")
    return results
