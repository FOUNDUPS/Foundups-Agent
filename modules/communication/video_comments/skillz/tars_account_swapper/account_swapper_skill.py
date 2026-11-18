"""
Tars Account Swapper Skill
==========================

Autonomous account switching for Tars reinforcement training.
Enables swapping between Move2Japan, UnDaoDu, and FoundUps channels in YouTube Studio/Main.

WSP Compliance:
- WSP 27: DAE Architecture (Action -> Verify)
- WSP 87: Navigation Protocol
- WSP 49: Platform Integration Safety
"""

import asyncio
import logging
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlsplit

# Add project root to sys.path
project_root = Path(__file__).parent.parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from modules.infrastructure.foundups_selenium.src.human_behavior import get_human_behavior

# Orchestration switchboard for OOPS breadcrumb telemetry (optional, graceful degradation)
try:
    from modules.infrastructure.orchestration_switchboard.src.orchestration_switchboard import get_orchestration_switchboard
    _has_switchboard = True
except ImportError:
    _has_switchboard = False


def _emit_oops_signal(signal_type: str, source_dae: str = "tars_account_swapper", **metadata):
    """Emit OOPS breadcrumb to orchestration switchboard (fire-and-forget)."""
    if not _has_switchboard:
        return
    try:
        sb = get_orchestration_switchboard()
        sb.receive_signal(signal_type, source_dae, metadata=metadata)
    except Exception as e:
        logging.getLogger(__name__).debug(f"[TARS-SWAP] Switchboard signal failed: {e}")


# UI-TARS verification (optional, graceful degradation if unavailable)
try:
    from modules.infrastructure.foundups_vision.src.ui_tars_bridge import UITarsBridge
    UI_TARS_AVAILABLE = True
except ImportError:
    UI_TARS_AVAILABLE = False

logger = logging.getLogger(__name__)

class TarsAccountSwapper:
    """
    Handles channel/account swapping via YouTube's account picker.

    This is used for:
    - Switching between channels under the SAME signed-in browser session (brand channels / accounts list)
    - Recovering from "no permission" pages by triggering "Switch account" and selecting the correct channel

    Notes (WSP 50: never assume):
    - If two channels are under different Google accounts, you typically cannot switch between them
      via the picker unless both identities are present in the session. In that case, use separate
      browser profiles/ports (e.g., Chrome 9222 vs Edge 9223) and/or ensure both channels appear
      in the picker list.
    Uses text-based DOM search (not fixed indices) since account order varies.
    """

    # Channel Configuration (env-driven for ops ergonomics)
    @property
    def CHANNELS(self) -> Dict[str, Any]:
        m2j_id = os.getenv("MOVE2JAPAN_CHANNEL_ID", "UC-LSSlOZwpGIRIYihaz8zCw")
        undaodu_id = os.getenv("UNDAODU_CHANNEL_ID", "UCfHM9Fw9HD-NwiS0seD_oIA")
        foundups_id = os.getenv("FOUNDUPS_CHANNEL_ID", "UCSNTUXjAgpd4sgWYP0xoJgw")
        antifafm_id = os.getenv("ANTIFAFM_CHANNEL_ID", "UCVSmg5aOhP4tnQ9KFUg97qA")
        return {
            "Move2Japan": {
                "id": m2j_id,
                "url": f"https://studio.youtube.com/channel/{m2j_id}/comments/inbox",
                "match_terms": ["move2japan", "@move2japan", "move 2 japan"],
            },
            "UnDaoDu": {
                "id": undaodu_id,
                "url": f"https://studio.youtube.com/channel/{undaodu_id}/comments/inbox",
                "match_terms": ["undaodu", "@undaodu", "un dao du"],
            },
            "FoundUps": {
                "id": foundups_id,
                "url": f"https://studio.youtube.com/channel/{foundups_id}/comments/inbox",
                "match_terms": ["foundups", "@foundups", "found ups"],
            },
            "antifaFM": {
                "id": antifafm_id,
                "url": f"https://studio.youtube.com/channel/{antifafm_id}/comments/inbox",
                "match_terms": ["antifafm", "@antifafm", "antifa fm"],
            },
        }

    def __init__(self, driver, ui_tars_verify: bool = True):
        self.driver = driver
        self.human = get_human_behavior(driver)
        self.ui_tars_verify = ui_tars_verify and UI_TARS_AVAILABLE
        self._ui_tars = None

        # Initialize UI-TARS if available and verification requested
        if self.ui_tars_verify:
            try:
                self._ui_tars = UITarsBridge()
                logger.info("[TARS-SWAP] UI-TARS verification enabled")
            except Exception as e:
                logger.warning(f"[TARS-SWAP] UI-TARS unavailable: {e}")
                self.ui_tars_verify = False

        logger.info("[TARS-SWAP] Initialized Improved Account Swapper")

    async def sleep_human(self, base=1.0, std=0.2):
        """Human-like delay."""
        delay = self.human.human_delay(base, std)
        await asyncio.sleep(delay)

    async def _verify_step(self, step_name: str, expected_state: str) -> bool:
        """
        Use UI-TARS to verify a step completed successfully.

        Args:
            step_name: Name of the step for logging
            expected_state: Description of what we expect to see

        Returns:
            True if verified or verification skipped, False if verification failed
        """
        if not self.ui_tars_verify or not self._ui_tars:
            logger.debug(f"[TARS-SWAP] Skipping verification for {step_name} (UI-TARS not enabled)")
            return True

        try:
            # Capture screenshot for verification
            screenshot = await self._ui_tars.capture_screenshot()
            logger.info(f"[TARS-SWAP] Captured screenshot for {step_name}: {screenshot.path}")

            # Log expected state for manual review / training data
            logger.info(f"[TARS-SWAP] Verifying {step_name}: expecting '{expected_state}'")

            # For now, return True (screenshot captured for training)
            # Future: Use UI-TARS vision model to verify expected_state
            return True

        except Exception as e:
            logger.warning(f"[TARS-SWAP] Verification failed for {step_name}: {e}")
            # Don't block on verification failures
            return True

    async def navigate_to_comments(self, target: str):
        """Navigate directly to the channel's studio comments."""
        if target in self.CHANNELS:
            url = self.CHANNELS[target]["url"]
            logger.info(f"[TARS-SWAP] Navigating to {target} comments: {url}")
            self.driver.get(url)
            await asyncio.sleep(3) # Wait for initial load
        else:
            logger.warning(f"[TARS-SWAP] No URL mapped for {target}")

    async def _navigate_to_target_surface(self, target: str, comments: bool) -> None:
        if comments:
            await self.navigate_to_comments(target)
        else:
            target_id = self.CHANNELS[target]["id"]
            self.driver.get(f"https://studio.youtube.com/channel/{target_id}/videos/short")
            await asyncio.sleep(3)

    async def _detect_current_channel_id(self, *, require_native: bool = False) -> Optional[str]:
        """Robustly detect current channel ID from browser state."""
        try:
            # Try script execution first (most reliable in Studio)
            channel_id = self.driver.execute_script(
                "return (window.yt && window.yt.config_ && window.yt.config_.CHANNEL_ID) || "
                "(window.ytcfg && typeof window.ytcfg.get === 'function' && window.ytcfg.get('CHANNEL_ID')) || "
                "null;"
            )
            if isinstance(channel_id, str) and channel_id:
                return channel_id
        except Exception:
            pass

        if require_native:
            return None

        # Fallback to URL regex
        try:
            url = self.driver.current_url or ""
            match = re.search(r"(?:studio\.youtube\.com/channel/|youtube\.com/channel/)([^/?#]+)", url)
            return match.group(1) if match else None
        except Exception:
            return None

    def _current_channel_id(self) -> Optional[str]:
        """Deprecated - use await _detect_current_channel_id() for robustness."""
        try:
            url = self.driver.current_url or ""
            match = re.search(r"studio\.youtube\.com/channel/([^/?#]+)/comments", url)
            return match.group(1) if match else None
        except Exception:
            return None

    async def _detect_current_channel_name(self) -> Optional[str]:
        """
        Detect which channel we're currently on by checking URL/page state.

        Returns channel name (e.g., "FoundUps", "antifaFM") or None.
        Used after "Return to Studio" to know which account is active.

        2026-02-27: Added for smart OOPS recovery - detect before swap.
        """
        channel_id = await self._detect_current_channel_id()
        if not channel_id:
            # Fallback: Try URL pattern without async
            try:
                url = self.driver.current_url or ""
                # Match both /channel/ID and /channel/ID/anything
                match = re.search(r"studio\.youtube\.com/channel/([^/?#]+)", url)
                if match:
                    channel_id = match.group(1)
            except Exception:
                pass

        if not channel_id:
            logger.debug("[TARS-SWAP] Could not detect current channel ID")
            return None

        # Map ID back to channel name
        for name, config in self.CHANNELS.items():
            if config.get("id") == channel_id:
                logger.info(f"[TARS-SWAP] Detected current channel: {name} ({channel_id})")
                return name

        logger.warning(f"[TARS-SWAP] Unknown channel ID: {channel_id}")
        return None

    def _is_permission_error(self, *, require_observation: bool = False) -> bool:
        """Detect Studio permission error page."""
        try:
            observed = self.driver.execute_script(
                ("if (!document.body || !document.querySelector('ytcp-app')) return null;" if require_observation else "") +
                "const t=(document.body&&document.body.innerText)||'';"
                "const norm=t.toLowerCase().replace(/\\u2019/g, \"'\");"
                "return ("
                "norm.includes(\"don't have permission\") || "
                "norm.includes(\"dont have permission\") || "
                "norm.includes(\"do not have permission\") || "
                "norm.includes(\"permission to view this page\") || "
                "norm.includes(\"switch account\") || "
                "norm.includes(\"return to studio\")"
                ");"
            )
            if require_observation and type(observed) is not bool:
                return True
            return bool(observed)
        except Exception:
            return require_observation

    def _click_permission_switch(self) -> bool:
        """Click the Switch account button on permission error page.

        2026-02-03: Hardened with live DOM inspection results.
        2026-02-04: Fixed from live OOPS page inspection via --chrome:
          - Actual element: <a id="selectaccount-link" class="button filled" target="_blank" href="...channel_switcher...">
          - CRITICAL: target="_blank" opens new tab - must remove before click or navigate directly
          - Strategy: Remove target="_blank", then click to navigate in-place (keeps Selenium driver on same tab)
        """
        try:
            return bool(self.driver.execute_script("""
                // Strategy 1: Precise ID selector (confirmed via live DOM 2026-02-04)
                const switchLink = document.querySelector('#selectaccount-link');
                if (switchLink) {
                    // CRITICAL: Remove target="_blank" so click navigates in same tab
                    // Otherwise Selenium driver stays on OOPS page while switcher opens in new tab
                    switchLink.removeAttribute('target');
                    // 2026-02-04: CRITICAL FIX - Rewrite ?next= to Studio root to prevent
                    // redirect loop back to the OOPS-triggering channel URL.
                    // Without this fix, channel_switcher?next=<wrong_channel> redirects
                    // back to the wrong channel after switching, causing re-OOPS.
                    const href = switchLink.getAttribute('href') || '';
                    if (href.includes('channel_switcher')) {
                        const url = new URL(href, window.location.origin);
                        url.searchParams.set('next', 'https://studio.youtube.com/');
                        switchLink.setAttribute('href', url.toString());
                    }
                    switchLink.click();
                    return true;
                }
                // Strategy 2: Fallback text search across all clickable elements
                const candidates = [...document.querySelectorAll('a, button, [role="button"]')];
                for (const el of candidates) {
                    const text = (el.textContent || '').trim().toLowerCase();
                    if (text.includes('switch account')) {
                        el.removeAttribute('target');
                        const h = el.getAttribute('href') || '';
                        if (h.includes('channel_switcher')) {
                            const u = new URL(h, window.location.origin);
                            u.searchParams.set('next', 'https://studio.youtube.com/');
                            el.setAttribute('href', u.toString());
                        }
                        el.click();
                        return true;
                    }
                }
                // Strategy 3: href-based (channel_switcher URL)
                const csLinks = document.querySelectorAll('a[href*="channel_switcher"]');
                for (const link of csLinks) {
                    link.removeAttribute('target');
                    const h2 = link.getAttribute('href') || '';
                    const u2 = new URL(h2, window.location.origin);
                    u2.searchParams.set('next', 'https://studio.youtube.com/');
                    link.setAttribute('href', u2.toString());
                    link.click();
                    return true;
                }
                return false;
            """))
        except Exception:
            return False

    def _click_return_to_studio(self) -> bool:
        """Click the 'Return to Studio' button on permission error page.

        2026-02-03: New method - provides alternative OOPS resolution path.
        2026-02-04: Fixed from live OOPS page inspection via --chrome:
          - Actual element: <a class="button tonal" href="/">Return to Studio</a>
          - Links to Studio root "/" for whatever account is currently active
        """
        try:
            return bool(self.driver.execute_script("""
                // Strategy 1: Precise class selector (confirmed via live DOM 2026-02-04)
                const tonalBtn = document.querySelector('a.button.tonal');
                if (tonalBtn && tonalBtn.textContent.trim().toLowerCase().includes('return')) {
                    tonalBtn.click();
                    return true;
                }
                // Strategy 2: Text search fallback
                const candidates = [...document.querySelectorAll('a, button, [role="button"]')];
                for (const el of candidates) {
                    const text = (el.textContent || '').trim().toLowerCase();
                    if (text.includes('return to studio') || text.includes('go to studio') || text.includes('back to studio')) {
                        el.click();
                        return true;
                    }
                }
                return false;
            """))
        except Exception:
            return False

    async def _ui_tars_click_oops_button(self, button_description: str) -> bool:
        """
        Use UI-TARS vision model to click a button on the OOPS page.

        2026-02-03: Fallback when DOM-based button click fails.
        UI-TARS takes a screenshot and uses vision to locate + click the button.

        Args:
            button_description: Natural language description (e.g. "Switch Account button")

        Returns:
            True if UI-TARS successfully clicked the button
        """
        if not self.ui_tars_verify or not self._ui_tars:
            logger.debug("[TARS-SWAP] UI-TARS not available for OOPS button click")
            return False

        try:
            logger.info(f"[TARS-SWAP] 🔍 UI-TARS attempting to click: '{button_description}'")
            result = await self._ui_tars.execute_action(
                action="click",
                description=button_description,
                context={"page": "oops_permission_error"},
                driver=self.driver,
                timeout=60,
            )

            if result.success:
                logger.info(f"[TARS-SWAP] ✅ UI-TARS clicked '{button_description}' "
                            f"(confidence={result.confidence:.2f}, {result.duration_ms}ms)")
                return True
            else:
                logger.warning(f"[TARS-SWAP] UI-TARS failed to click '{button_description}': {result.error}")
                return False

        except Exception as e:
            logger.warning(f"[TARS-SWAP] UI-TARS OOPS click exception: {e}")
            return False

    async def swap_from_oops_page(self, target: str, *, navigate_to_comments: bool = True) -> bool:
        """
        Direct account switch from OOPS/permission error page.

        2026-02-03: Enhanced with:
        - UI-TARS vision fallback when DOM clicks fail
        - "Return to Studio" button as secondary resolution path
        - Direct URL navigation as final fallback

        Resolution cascade:
        1. DOM click "Switch account" -> select account from picker
        2. UI-TARS click "Switch Account" button -> select account from picker
        3. DOM click "Return to Studio" -> navigate to target URL
        4. UI-TARS click "Return to Studio" -> navigate to target URL
        5. Direct URL navigation to target (last resort)

        Args:
            target: Target channel name ('Move2Japan', 'UnDaoDu', 'FoundUps', 'antifaFM')
            navigate_to_comments: Whether to navigate to comments after switch

        Returns:
            True if switch successful, False otherwise
        """
        logger.info(f"[TARS-SWAP] 🔄 DIRECT OOPS PAGE SWITCH to {target}")

        if target not in self.CHANNELS:
            logger.error(f"[TARS-SWAP] Unknown target: {target}")
            return False

        # Verify we're on an OOPS page
        if not self._is_permission_error():
            logger.warning("[TARS-SWAP] Not on OOPS page - falling back to normal swap")
            # Avoid infinite recursion: swap_to now calls swap_from_oops_page, so navigate directly
            await self._navigate_to_target_surface(target, navigate_to_comments)
            await asyncio.sleep(3)
            return await self._ensure_target_access(target, navigate_to_comments=navigate_to_comments)

        # 2026-02-03: Emit OOPS breadcrumb to orchestration switchboard
        _emit_oops_signal("oops_page_detected", channel_name=target, browser="unknown", attempt_count=1)

        # === CASCADE 1: Try "Switch account" (DOM then UI-TARS) ===
        logger.info("[TARS-SWAP] Step 1: Clicking 'Switch account' on OOPS page...")

        switch_clicked = self._click_permission_switch()
        if not switch_clicked:
            logger.warning("[TARS-SWAP] DOM click failed for 'Switch account' - trying UI-TARS...")
            switch_clicked = await self._ui_tars_click_oops_button(
                "Switch Account button on the permission error page"
            )

        if switch_clicked:
            await self.sleep_human(2.0, 0.5)

            # UI-TARS verify: Account picker should now be visible
            await self._verify_step("oops_switch_clicked", "Account picker dropdown visible after clicking OOPS switch button")

            # Step 2: Select target account from picker
            logger.info(f"[TARS-SWAP] Step 2: Selecting {target} from account picker...")
            match_terms = (self.CHANNELS.get(target, {}) or {}).get("match_terms") or []
            if await self.select_account(target, match_terms=match_terms):
                await self.sleep_human(3.0, 0.5)

                # Step 3: Navigate to target comments (optional)
                if navigate_to_comments:
                    await self.navigate_to_comments(target)
                    await asyncio.sleep(3)

                # Verify we made it
                if await self._ensure_target_access(target, navigate_to_comments=navigate_to_comments):
                    try:
                        final_url = self.driver.current_url
                        logger.info(f"[TARS-SWAP] 🚀 OOPS page switch to {target} successful!")
                        logger.info(f"[TARS-SWAP] Final URL: {final_url}")
                    except Exception:
                        logger.info(f"[TARS-SWAP] 🚀 OOPS page switch to {target} successful!")
                    _emit_oops_signal("oops_page_recovered", channel_name=target, recovery_method="switch_account")
                    return True

                logger.warning(f"[TARS-SWAP] Account switch completed but {target} still inaccessible")
            else:
                logger.warning(f"[TARS-SWAP] Failed to select {target} from picker after Switch Account")

        # === CASCADE 2: Try "Return to Studio" (DOM then UI-TARS) ===
        # 2026-02-27: IMPROVED - Detect which account we land on, THEN decide if swap needed
        logger.info("[TARS-SWAP] Step 3: Trying 'Return to Studio' button...")

        return_clicked = self._click_return_to_studio()
        if not return_clicked:
            logger.warning("[TARS-SWAP] DOM click failed for 'Return to Studio' - trying UI-TARS...")
            return_clicked = await self._ui_tars_click_oops_button(
                "Return to Studio button on the permission error page"
            )

        if return_clicked:
            await self.sleep_human(3.0, 0.5)

            # DETECT which account we landed on
            current_channel = await self._detect_current_channel_name()
            logger.info(f"[TARS-SWAP] Returned to Studio - detected current account: {current_channel}")

            if current_channel == target:
                # Already on target account - just navigate to comments
                logger.info(f"[TARS-SWAP] Already on {target} - navigating directly to comments...")
                if navigate_to_comments:
                    await self.navigate_to_comments(target)
                    await asyncio.sleep(3)

                if await self._ensure_target_access(target, navigate_to_comments=navigate_to_comments):
                    logger.info(f"[TARS-SWAP] 🚀 Return to Studio + direct navigate to {target} successful!")
                    _emit_oops_signal("oops_page_recovered", channel_name=target, recovery_method="return_to_studio_direct")
                    return True
            else:
                # On different account - need to swap first
                logger.info(f"[TARS-SWAP] On {current_channel}, need {target} - initiating account swap...")

                # Click avatar to open account picker
                if await self.click_avatar():
                    await self.sleep_human(1.5, 0.3)
                    if await self.click_switch_account():
                        await self.sleep_human(2.0, 0.5)

                        # Select target account
                        match_terms = (self.CHANNELS.get(target, {}) or {}).get("match_terms") or []
                        if await self.select_account(target, match_terms=match_terms):
                            await self.sleep_human(3.0, 0.5)

                            # Now navigate to target comments
                            if navigate_to_comments:
                                await self.navigate_to_comments(target)
                                await asyncio.sleep(3)

                            if await self._ensure_target_access(target, navigate_to_comments=navigate_to_comments):
                                logger.info(f"[TARS-SWAP] 🚀 Return to Studio + smart swap to {target} successful!")
                                _emit_oops_signal("oops_page_recovered", channel_name=target, recovery_method="return_to_studio_swap")
                                return True

            logger.warning(f"[TARS-SWAP] Return to Studio cascade did not reach {target}")

        # === CASCADE 3: Direct URL navigation (last resort) ===
        logger.info(f"[TARS-SWAP] Step 4: LAST RESORT - Direct URL navigation to {target}...")
        await self._navigate_to_target_surface(target, navigate_to_comments)
        await asyncio.sleep(5)

        if await self._ensure_target_access(target, navigate_to_comments=navigate_to_comments):
            logger.info(f"[TARS-SWAP] 🚀 Direct URL navigation to {target} successful!")
            _emit_oops_signal("oops_page_recovered", channel_name=target, recovery_method="direct_url")
            return True

        logger.error(f"[TARS-SWAP] ❌ All OOPS resolution cascades failed for {target}")
        _emit_oops_signal("oops_page_detected", channel_name=target, browser="unknown",
                          attempt_count=2, recovery_failed=True)
        return False

    async def _ensure_target_access(self, target: str, *, navigate_to_comments: bool = True,
                                    expected_channel_id: Optional[str] = None) -> bool:
        """Require matching native identity and Studio URL on the requested surface."""
        target_id = self.CHANNELS.get(target, {}).get("id")
        if expected_channel_id is not None and target_id != expected_channel_id:
            return False
        if expected_channel_id is not None:
            target_id = expected_channel_id
        if not isinstance(target_id, str) or not target_id:
            return False
        try:
            page = urlsplit(self.driver.current_url or "")
            match = re.fullmatch(r"/channel/([^/]+)(/.*)?", page.path)
            if page.scheme != "https" or page.hostname != "studio.youtube.com" or not match:
                return False
            if match.group(1) != target_id:
                return False
            if navigate_to_comments and not re.match(r"/comments(?:/|$)", match.group(2) or ""):
                return False
            current_id = await self._detect_current_channel_id(require_native=True)
            return current_id == target_id and not self._is_permission_error(require_observation=True)
        except Exception:
            return False

    async def click_avatar(self) -> bool:
        """Step 1: Click the avatar button (works on both YouTube and Studio)."""
        logger.info("[TARS-SWAP] Clicking avatar...")
        try:
            # Using custom script for robust shadow-piercing click
            # This covers both ytd-masthead (YouTube) and ytcp-header (Studio)
            success = self.driver.execute_script("""
                const btn = 
                    document.querySelector('button#avatar-btn') || 
                    document.querySelector('ytcp-img-shadow#avatar') ||
                    document.querySelector('ytcp-header #avatar-btn') ||
                    document.querySelector('button#avatar-btn img#img');
                if (btn) {
                    btn.click();
                    return true;
                }
                return false;
            """)
            return success
        except Exception as e:
            logger.error(f"[TARS-SWAP] Failed to click avatar: {e}")
            return False

    async def click_switch_account(self) -> bool:
        """Step 2: Click 'Switch account' in the popup menu."""
        logger.info("[TARS-SWAP] Clicking 'Switch account'...")
        try:
            # 2026-01-28: Updated with precise DOM path from user inspection
            # Path: ytd-multi-page-menu-section-renderer[0] > #items > ytd-compact-link-renderer[2] > a#endpoint
            success = self.driver.execute_script("""
                // Strategy 1: Precise DOM path (most reliable)
                // The "Switch account" is the 3rd item (index 2) in the first menu section
                const sections = document.querySelectorAll('ytd-multi-page-menu-section-renderer');
                if (sections.length > 0) {
                    const firstSection = sections[0];
                    const links = firstSection.querySelectorAll('ytd-compact-link-renderer');
                    // Switch account is typically at index 2 (after Sign out and other items)
                    for (const link of links) {
                        const text = link.textContent || '';
                        if (text.includes('Switch account') || text.includes('Switch')) {
                            const endpoint = link.querySelector('a#endpoint') || link;
                            endpoint.click();
                            return true;
                        }
                    }
                }

                // Strategy 2: Direct selector for the right-icon (arrow) in Switch account row
                const switchIcon = document.querySelector('ytd-compact-link-renderer yt-icon#right-icon');
                if (switchIcon) {
                    const parent = switchIcon.closest('ytd-compact-link-renderer');
                    if (parent && parent.textContent.includes('Switch')) {
                        switchIcon.click();
                        return true;
                    }
                }

                // Strategy 3: Text search fallback
                const items = document.querySelectorAll('tp-yt-paper-item, ytcp-ve, ytd-compact-link-renderer, a#endpoint');
                for (const item of items) {
                    if (item.textContent.includes('Switch account')) {
                        item.click();
                        return true;
                    }
                }
                return false;
            """)
            return success
        except Exception as e:
            logger.error(f"[TARS-SWAP] Failed to click switch account: {e}")
            return False

    # 2026-01-29: FLUID DUAL-BROWSER ARCHITECTURE
    # Both Google accounts logged into BOTH browsers - picker structure identical on Chrome & Edge
    # Account picker mapping - TEXT MATCH IS PRIMARY (indices change based on active account)
    # 2026-02-27: DOM order depends on which Google account is logged in
    # - When UnDaoDu logged in: Section 0 = UnDaoDu[0], Move2Japan[1]; Section 1 = FoundUps[0], antifaFM[1]
    # - When FoundUps logged in: Section 0 = FoundUps[0], antifaFM[1]; Section 1 = UnDaoDu[0], Move2Japan[1]
    # SOLUTION: Use TEXT MATCHING primarily, indices as hint only
    ACCOUNT_PICKER_MAP = {
        "UnDaoDu": {"section": None, "index": None, "text_match": "undaodu"},
        "Move2Japan": {"section": None, "index": None, "text_match": "move2japan"},
        "FoundUps": {"section": None, "index": None, "text_match": "foundups"},
        "antifaFM": {"section": None, "index": None, "text_match": "antifafm"},
    }

    async def select_account(self, target_name: str, match_terms: Optional[list] = None) -> bool:
        """Step 3: Select the target account by name (Move2Japan, UnDaoDu, FoundUps, or antifaFM)."""
        logger.info(f"[TARS-SWAP] Selecting account: {target_name}...")
        try:
            # Debug: List all available accounts in the picker
            available_accounts = self.driver.execute_script("""
                const accounts = [];
                const items = document.querySelectorAll('ytd-account-item-renderer, ytcp-account-item-renderer, tp-yt-paper-icon-item');
                for (const item of items) {
                    const text = (item.textContent || '').trim().replace(/\\s+/g, ' ').substring(0, 60);
                    if (text) accounts.push(text);
                }
                return accounts;
            """)
            logger.info(f"[TARS-SWAP] Available accounts in picker: {available_accounts}")

            # Get picker map for index-based selection
            picker_info = self.ACCOUNT_PICKER_MAP.get(target_name, {})
            section_idx = picker_info.get("section")
            item_idx = picker_info.get("index")
            text_match = picker_info.get("text_match", target_name.lower())

            # 2026-01-28: Updated with precise DOM structure from user inspection
            # Structure: ytd-account-section-list-renderer[section] > ytd-account-item-section-renderer >
            #            div#contents > ytd-account-item-renderer[index] > tp-yt-paper-icon-item
            success = self.driver.execute_script("""
                const target = (arguments[0] || '').toLowerCase();
                const terms = (arguments[1] || []).map(t => (t || '').toLowerCase()).filter(Boolean);
                const wanted = [target, ...terms].filter(Boolean);
                const sectionIdx = arguments[2];
                const itemIdx = arguments[3];
                const textMatch = arguments[4];

                // Strategy 1: Index-based selection (most reliable when picker structure is known)
                if (sectionIdx !== null && sectionIdx !== undefined && itemIdx !== null && itemIdx !== undefined) {
                    const sectionLists = document.querySelectorAll('ytd-account-section-list-renderer');
                    if (sectionLists.length > sectionIdx) {
                        const sectionList = sectionLists[sectionIdx];
                        const itemSections = sectionList.querySelectorAll('ytd-account-item-section-renderer');
                        if (itemSections.length > 0) {
                            const items = itemSections[0].querySelectorAll('ytd-account-item-renderer');
                            if (items.length > itemIdx) {
                                const targetItem = items[itemIdx];
                                const paperItem = targetItem.querySelector('tp-yt-paper-icon-item');
                                if (paperItem) {
                                    // Verify it's the right account by text
                                    const itemText = paperItem.textContent.toLowerCase();
                                    if (itemText.includes(textMatch)) {
                                        paperItem.click();
                                        console.log('[TARS-SWAP] Selected via index:', textMatch);
                                        return true;
                                    }
                                }
                            }
                        }
                    }
                }

                // Strategy 2: Text-based search across all tp-yt-paper-icon-item (fallback)
                const allPaperItems = document.querySelectorAll('tp-yt-paper-icon-item');
                for (const item of allPaperItems) {
                    const text = item.textContent.toLowerCase();
                    if (wanted.some(w => text.includes(w))) {
                        item.click();
                        console.log('[TARS-SWAP] Selected via text match:', text.substring(0, 40));
                        return true;
                    }
                }

                // Strategy 3: Search ytd-account-item-renderer directly
                const items = document.querySelectorAll('ytd-account-item-renderer, ytcp-account-item-renderer');
                for (const item of items) {
                    const text = item.textContent.toLowerCase();
                    if (wanted.some(w => text.includes(w))) {
                        item.click();
                        return true;
                    }
                }

                return false;
            """, target_name, match_terms or [], section_idx, item_idx, text_match)
            return success
        except Exception as e:
            logger.error(f"[TARS-SWAP] Failed to select account {target_name}: {e}")
            return False

    async def swap_to(self, target: str, *, navigate_to_comments: bool = True) -> bool:
        """
        Improved swap sequence with direct Studio navigation.
        target: 'UnDaoDu', 'Move2Japan', 'FoundUps', or 'antifaFM'
        """
        # 2026-01-29: Enhanced logging for debugging swap failures
        try:
            start_url = self.driver.current_url
        except Exception:
            start_url = "<unknown>"
        logger.info(f"[TARS-SWAP] STARTING IMPROVED SWAP TO {target}")
        logger.info(f"[TARS-SWAP] Current URL: {start_url}")

        if target not in self.CHANNELS:
            logger.error(f"[TARS-SWAP] Unknown target account: {target}")
            return False

        # FAST PATH: Check ID from current state (no navigation needed)
        current_id = await self._detect_current_channel_id()
        target_id = self.CHANNELS[target]["id"]
        logger.debug(f"[TARS-SWAP] Channel IDs - current: {current_id}, target: {target_id}")

        if await self._ensure_target_access(target, navigate_to_comments=navigate_to_comments):
            logger.info(f"[TARS-SWAP] Already on the requested {target} Studio surface - skipping account switch")
            return True

        # 2026-02-03: OOPS PAGE PRE-CHECK - Route to swap_from_oops_page() BEFORE click_avatar
        # On OOPS pages, there's no avatar button - click_avatar will always fail.
        # Instead, use the "Switch account" / "Return to Studio" buttons on the OOPS page directly.
        if self._is_permission_error():
            logger.info(f"[TARS-SWAP] 🚨 OOPS page detected - routing to swap_from_oops_page() (skipping click_avatar)")
            return await self.swap_from_oops_page(target, navigate_to_comments=navigate_to_comments)

        # Ensure we are on a page where account switching is possible
        if "youtube.com" not in self.driver.current_url:
            self.driver.get("https://www.youtube.com")
            await asyncio.sleep(2)

        # Step 1: Click avatar button
        if not await self.click_avatar():
            logger.error("[TARS-SWAP] ❌ Step 1 FAILED - click_avatar")
            return False
        await self.sleep_human(1.5, 0.4)

        # UI-TARS verify: Account menu should be open
        await self._verify_step("step1_avatar_clicked", "Account menu dropdown visible with user profile")

        # Step 2: Click "Switch account"
        if not await self.click_switch_account():
            logger.error("[TARS-SWAP] ❌ Step 2 FAILED - click_switch_account")
            return False
        await self.sleep_human(2.0, 0.5)

        # UI-TARS verify: Account picker should show list of channels
        await self._verify_step("step2_switch_clicked", f"Account picker showing list including {target}")

        # Step 3: Select target account
        match_terms = (self.CHANNELS.get(target, {}) or {}).get("match_terms") or []
        if not await self.select_account(target, match_terms=match_terms):
            logger.error("[TARS-SWAP] ❌ Step 3 FAILED - select_account")
            return False

        # UI-TARS verify: Account should now be switching
        await self._verify_step("step3_account_selected", f"Page loading/redirecting to {target} channel")
        
        # Wait for global switch to settle
        logger.info(f"[TARS-SWAP] ✅ Account switch selected. Waiting for session update...")
        await asyncio.sleep(5) 

        # FINAL STEP: Optionally navigate directly to the target comments URL
        if navigate_to_comments:
            await self.navigate_to_comments(target)

        # Verify access; retry once if permission error detected
        if not await self._ensure_target_access(target, navigate_to_comments=navigate_to_comments):
            logger.warning(f"[TARS-SWAP] Access mismatch after switch; attempting recovery for {target}")
            if self._is_permission_error() and self._click_permission_switch():
                await self.sleep_human(2.0, 0.5)
                if await self.select_account(target, match_terms=match_terms):
                    await asyncio.sleep(3)
                    if navigate_to_comments:
                        await self.navigate_to_comments(target)

            if not await self._ensure_target_access(target, navigate_to_comments=navigate_to_comments):
                logger.error(f"[TARS-SWAP] Failed to reach {target} comments page with access")
                return False
        
        # UI-TARS verify: Final verification - should be on target channel comments page
        await self._verify_step("step4_swap_complete", f"YouTube Studio comments inbox for {target} channel")

        # 2026-01-29: Log final state for debugging
        try:
            final_url = self.driver.current_url
            final_id = await self._detect_current_channel_id()
            logger.info(f"[TARS-SWAP] 🚀 Successfully transitioned to {target} comments.")
            logger.info(f"[TARS-SWAP] Final URL: {final_url}")
            logger.info(f"[TARS-SWAP] Final channel ID: {final_id} (expected: {target_id})")
        except Exception as log_err:
            logger.info(f"[TARS-SWAP] 🚀 Successfully transitioned to {target} comments (final state logging failed: {log_err})")
        return True

async def main():
    # This is a placeholder for standalone testing
    print("Tars Account Swapper - Standalone Script")

if __name__ == "__main__":
    asyncio.run(main())
