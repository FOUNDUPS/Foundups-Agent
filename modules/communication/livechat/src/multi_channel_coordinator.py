"""
Multi-Channel Comment Engagement Coordinator

Extracted from AutoModeratorDAE per WSP 62 (Large File Refactoring).
Handles Chrome + Edge browser rotation for multi-channel comment engagement.

Architecture (2025-12-28, Hardened 2026-01-18):
- Chrome (port 9222): Registry-driven channel group (same Google account)
- Edge (port 9223): Registry-driven channel group (same Edge session)

Hardening Features (2026-01-18):
1. BIDIRECTIONAL FALLBACK:
   - Chrome: Registry-driven fallback within same account section
   - Edge: Registry-driven fallback within same account section
   - If target channel shows "Oops" page, try fallback before account switch

2. OOPS PAGE DETECTION:
   - Detects "don't have permission" / "Oops" / "access denied" pages
   - Triggers fallback logic automatically

3. BROWSER SESSION RECOVERY:
   - Handles NoSuchWindowException (window closed)
   - Step 1: Try reconnect to existing browser
   - Step 2: If reconnect fails, relaunch browser
   - Step 3: If relaunch fails, skip remaining channels

WSP References:
- WSP 62: Large File Refactoring Enforcement Protocol
- WSP 72: Module Independence (single responsibility)
- WSP 84: Code Reuse (delegates to existing browser infrastructure)
- WSP 73: Digital Twin Architecture (browser routing)
"""

import os
import time
import asyncio
import logging
from typing import Optional, Dict, Any, Callable, List, Tuple, Awaitable

from modules.communication.livechat.src.breadcrumb_telemetry import get_breadcrumb_telemetry
from modules.infrastructure.shared_utilities.youtube_channel_registry import (
    get_channels,
    get_rotation_order,
    build_fallbacks,
)

logger = logging.getLogger(__name__)


def _env_truthy(key: str, default: str = "false") -> bool:
    """Check if env var is truthy (true/1/yes)."""
    val = os.getenv(key, default).lower()
    return val in ("true", "1", "yes")


def _shorts_scheduled_count(result: Optional[Dict[str, Any]]) -> int:
    """Normalize scheduler result scheduled count (list vs int)."""
    if not result:
        return 0
    total = result.get("total_scheduled")
    if total is not None:
        return int(total)
    raw = result.get("scheduled", 0)
    return len(raw) if isinstance(raw, list) else int(raw or 0)

def _is_session_error(error_text: str) -> bool:
    """Check if error indicates a recoverable session error."""
    if not error_text:
        return False
    error_lower = error_text.lower()
    return any(phrase in error_lower for phrase in [
        "session",
        "disconnected",
        "target closed",
        "connection refused",
        "not connected",
        "no such window",  # NoSuchWindowException
        "window already closed",
        "web view not found",
    ])


def _is_oops_page(driver) -> bool:
    """
    Detect if current page is an 'Oops' permission error page.

    Returns True if page shows permission error (wrong account logged in).
    """
    try:
        page_text = driver.execute_script("return document.body?.innerText || '';")
        page_lower = page_text.lower()
        return (
            "don't have permission" in page_lower or
            "oops" in page_lower or
            "you need permission" in page_lower or
            "access denied" in page_lower
        )
    except Exception:
        return False


# Bidirectional fallback mapping (built from registry, per account section)
# When target channel shows Oops, try fallback first before account switch
CHANNEL_FALLBACKS = build_fallbacks(role="comments")

# Account Section Mapping (for "wrong Google account" detection)
ACCOUNT_SECTIONS = {}
SECTION_CHANNELS: Dict[int, List[str]] = {}
for _ch in get_channels(role="comments"):
    _name = _ch.get("name")
    _section = (_ch.get("browser") or {}).get("account_section", 0)
    if _name:
        section = int(_section)
        ACCOUNT_SECTIONS[_name] = section
        SECTION_CHANNELS.setdefault(section, []).append(_name)


def _format_section_label(section: int) -> str:
    names = SECTION_CHANNELS.get(section, [])
    suffix = f" ({', '.join(names)})" if names else ""
    if section == 0:
        return f"Google Account A{suffix}"
    if section == 1:
        return f"Google Account B{suffix}"
    return f"Google Account {section}{suffix}"

def _detect_wrong_account_scenario(target_channel: str, fallback_also_failed: bool) -> str:
    """
    Detect when browser is logged into wrong Google account entirely.

    Returns diagnostic message if wrong account detected, empty string otherwise.
    """
    if not fallback_also_failed:
        return ""

    section = ACCOUNT_SECTIONS.get(target_channel)
    if section is None:
        return ""

    # Both channels on same section failed = definitely wrong Google account
    section_name = _format_section_label(section)
    other_sections = sorted(s for s in SECTION_CHANNELS.keys() if s != section)
    wrong_section = _format_section_label(other_sections[0]) if other_sections else "another Google account"

    return (
        f"🔴 WRONG GOOGLE ACCOUNT: Browser appears to be on {wrong_section}, "
        f"but needs {section_name} (Section {section}). Account switch required."
    )

# Channel name to ID mapping (registry-driven)
CHANNEL_IDS = {}
for _ch in get_channels(role="comments"):
    _name = _ch.get("name")
    _cid = _ch.get("id")
    if _name and _cid:
        CHANNEL_IDS[_name] = _cid

# Reverse mapping
CHANNEL_NAMES = {v: k for k, v in CHANNEL_IDS.items()}


def _get_ordered_accounts_by_browser() -> Tuple[List[Tuple[str, str]], List[Tuple[str, str]]]:
    """Build ordered channel lists for Chrome and Edge based on registry rotation order."""
    ordered_keys = get_rotation_order(role="comments")
    channel_map = {ch.get("key"): ch for ch in get_channels(role="comments")}
    chrome_accounts: List[Tuple[str, str]] = []
    edge_accounts: List[Tuple[str, str]] = []
    for key in ordered_keys:
        ch = channel_map.get(key)
        if not ch:
            continue
        name = ch.get("name")
        cid = ch.get("id")
        browser = (ch.get("browser") or {}).get("comment_browser", "chrome")
        if not name or not cid:
            continue
        if browser == "edge":
            edge_accounts.append((name, cid))
        else:
            chrome_accounts.append((name, cid))
    return chrome_accounts, edge_accounts


class MultiChannelCoordinator:
    """
    Coordinates comment engagement across multiple YouTube channels.

    Uses Chrome for channels under the same Google account (account switching)
    and Edge for channels under different Google accounts (separate browser).
    """

    def __init__(
        self,
        # Callbacks for DAE integration
        log_studio_context: Callable[[str, str, Any], None],
        verify_studio_inbox_clear: Callable[[Any, str, str, float], Awaitable[Optional[bool]]],
        reconnect_chrome_driver: Callable[[int], Awaitable[Any]],
        reconnect_edge_driver: Callable[[int], Awaitable[Any]],
        detect_current_channel_id: Callable[[Any], Awaitable[Optional[str]]],
        # State callbacks
        update_engagement_status: Callable[[str, Dict[str, Any]], None],
        set_active_channel: Callable[[str], None],
        is_live_stream_pending: Callable[[], bool],
    ):
        """
        Initialize coordinator with callbacks to DAE.

        Args:
            log_studio_context: Callback to log Studio context
            verify_studio_inbox_clear: Callback to verify inbox is clear
            reconnect_chrome_driver: Callback to reconnect Chrome
            reconnect_edge_driver: Callback to reconnect Edge
            detect_current_channel_id: Callback to detect current channel
            update_engagement_status: Callback to update engagement status dict
            set_active_channel: Callback to set active channel ID
            is_live_stream_pending: Callback to check if live stream pending
        """
        self.log_studio_context = log_studio_context
        self.verify_studio_inbox_clear = verify_studio_inbox_clear
        self.reconnect_chrome_driver = reconnect_chrome_driver
        self.reconnect_edge_driver = reconnect_edge_driver
        self.detect_current_channel_id = detect_current_channel_id
        self.update_engagement_status = update_engagement_status
        self.set_active_channel = set_active_channel
        self.is_live_stream_pending = is_live_stream_pending
        self._oops_backoff: Dict[str, float] = {}

    def _oops_cooldown_seconds(self) -> int:
        return int(os.getenv("YT_OOPS_COOLDOWN_S", "300"))

    async def _driver_session_alive(self, driver: Any, browser_name: str) -> bool:
        """Lightweight health probe for Selenium driver session."""
        if driver is None:
            return False
        try:
            await asyncio.to_thread(driver.execute_script, "return document.readyState")
            await asyncio.to_thread(lambda: driver.current_url)
            return True
        except Exception as exc:
            logger.warning(f"[ROTATE] [{browser_name}] Session health check failed: {exc}")
            return False

    def _should_skip_oops(self, account_name: str) -> bool:
        last_ts = self._oops_backoff.get(account_name)
        if not last_ts:
            return False
        return (time.time() - last_ts) < self._oops_cooldown_seconds()

    def _record_oops(self, account_name: str) -> None:
        self._oops_backoff[account_name] = time.time()

    async def run_multi_channel_engagement(
        self,
        runner,
        max_comments: int,
        mode: str
    ) -> int:
        """
        Run comment engagement across ALL channels with account switching.

        Flow:
        1. Process Chrome channels (account switching)
        2. Process Edge channels (separate browser session)
        3. Check live stream signal before each channel
        4. If live detected -> pause rotation for that channel

        Args:
            runner: CommentEngagementRunner instance
            max_comments: Maximum comments per channel (0 = unlimited)
            mode: Execution mode string

        Returns:
            Total comments processed across all channels
        """
        strict_inbox = _env_truthy("YT_INBOX_STRICT", "true")
        edge_parallel = _env_truthy("YT_EDGE_PARALLEL", "true")
        edge_first = _env_truthy("YT_EDGE_FIRST", "true")

        # Channel groups (registry-driven)
        chrome_accounts, edge_accounts = _get_ordered_accounts_by_browser()

        total_channels = len(chrome_accounts) + len(edge_accounts)
        logger.info("=" * 70)
        logger.info("[ROTATE] MULTI-CHANNEL COMMENT ENGAGEMENT")
        logger.info(f"[ROTATE] Processing {total_channels} channels:")
        logger.info(f"[ROTATE]   Chrome (9222): {', '.join([a[0] for a in chrome_accounts])}")
        logger.info(f"[ROTATE]   Edge (9223): {', '.join([a[0] for a in edge_accounts])}")
        logger.info(f"[ROTATE] Mode: {mode} | Max per channel: {max_comments if max_comments > 0 else 'UNLIMITED'}")
        logger.info("=" * 70)

        total_processed = 0
        chrome_driver = None
        swapper = None
        rotation_halt = False
        edge_task = None

        # Start Edge in parallel if enabled
        if edge_parallel:
            try:
                edge_task = asyncio.create_task(
                    self._run_edge_engagement(runner, edge_accounts, max_comments, strict_inbox)
                )
                logger.info("[ROTATE] Edge scheduled in PARALLEL (YT_EDGE_PARALLEL=true)")
            except Exception as e:
                logger.warning(f"[ROTATE] Failed to schedule Edge task: {e}")
                edge_task = None

        # Optional ordering: run Edge FIRST when not parallel (matches ops expectation:
        # Edge channels are often the immediate targets before live chat handoff)
        if (not edge_parallel) and edge_first:
            total_processed += await self._run_edge_engagement(
                runner, edge_accounts, max_comments, strict_inbox
            )

        # Process Chrome channels
        skip_chrome = _env_truthy("YT_SKIP_CHROME", "false")
        if skip_chrome:
            logger.info("[ROTATE] SKIPPING CHROME (YT_SKIP_CHROME=true) - Testing Edge only")

        if not skip_chrome:
            chrome_result = await self._run_chrome_engagement(
                runner, chrome_accounts, max_comments, strict_inbox
            )
            total_processed += chrome_result

        # Handle Edge result
        if not edge_parallel:
            if not edge_first:
                total_processed += await self._run_edge_engagement(
                    runner, edge_accounts, max_comments, strict_inbox
                )
        elif edge_task:
            try:
                total_processed += await edge_task
            except Exception as e:
                logger.warning(f"[ROTATE] Edge task failed: {e}")

        logger.info("=" * 70)
        logger.info("[ROTATE] MULTI-CHANNEL ENGAGEMENT COMPLETE")
        logger.info(f"[ROTATE] Total comments processed: {total_processed}")
        logger.info(f"[ROTATE] Channels: Chrome ({len(chrome_accounts)}) + Edge ({len(edge_accounts)})")
        logger.info("=" * 70)

        # ACTIVITY ROUTING: Emit breadcrumb for activity router to pick up
        # This signals that all 4 channels have been processed
        try:
            telemetry = get_breadcrumb_telemetry()
            telemetry.store_breadcrumb(
                source_dae="multi_channel_coordinator",
                event_type="rotation_complete",
                message=f"All {total_channels} channels processed",
                phase="ACTIVITY-ROUTING",
                metadata={
                    "total_processed": total_processed,
                    "chrome_channels": len(chrome_accounts),
                    "edge_channels": len(edge_accounts),
                    "browser_chrome_available": True,
                    "browser_edge_available": True,
                }
            )
            logger.info("[ROTATE] [BREADCRUMB] rotation_complete emitted - browsers available for next activity")
        except Exception as e:
            logger.warning(f"[ROTATE] Failed to emit breadcrumb: {e}")

        # DAE CHAINING: After comment rotation completes, trigger Shorts scheduling
        # Toggle: YT_SHORTS_SCHEDULING_AFTER_COMMENTS (default: true as of 2026-01-28)
        if _env_truthy("YT_SHORTS_SCHEDULING_AFTER_COMMENTS", "true"):
            logger.info("=" * 70)
            logger.info("[CHAIN] SHORTS SCHEDULING - Triggered after comment rotation")
            logger.info("=" * 70)
            try:
                await self._run_shorts_scheduling_chain(chrome_accounts, edge_accounts)
            except Exception as sched_err:
                logger.error(f"[CHAIN] Shorts scheduling failed: {sched_err}")

        return total_processed

    async def run_browser_engagement(
        self,
        browser: str,
        runner,
        max_comments: int,
        mode: str,
    ) -> int:
        """
        Run comment engagement for a SINGLE browser only.

        2026-01-30: Created for per-browser parallel loop architecture.
        Each browser independently cycles comments → scheduling without
        blocking the other browser.

        Args:
            browser: "chrome" or "edge"
            runner: CommentEngagementRunner instance
            max_comments: Max comments per channel (0 = unlimited)
            mode: Execution mode string

        Returns:
            Total comments processed for this browser
        """
        strict_inbox = _env_truthy("YT_INBOX_STRICT", "true")
        chrome_accounts, edge_accounts = _get_ordered_accounts_by_browser()

        if browser == "chrome":
            skip_chrome = _env_truthy("YT_SKIP_CHROME", "false")
            if skip_chrome:
                logger.info("[ROTATE] SKIPPING CHROME (YT_SKIP_CHROME=true)")
                return 0

            if not chrome_accounts:
                logger.warning("[ROTATE] No Chrome channels configured - skipping Chrome engagement")
                return 0
            logger.info(f"[ROTATE] [Chrome] Processing {len(chrome_accounts)} channels: {', '.join(a[0] for a in chrome_accounts)}")
            return await self._run_chrome_engagement(
                runner, chrome_accounts, max_comments, strict_inbox
            )

        elif browser == "edge":
            if not edge_accounts:
                logger.warning("[ROTATE] No Edge channels configured - skipping Edge engagement")
                return 0
            logger.info(f"[ROTATE] [Edge] Processing {len(edge_accounts)} channels: {', '.join(a[0] for a in edge_accounts)}")
            return await self._run_edge_engagement(
                runner, edge_accounts, max_comments, strict_inbox
            )

        else:
            logger.error(f"[ROTATE] Unknown browser: {browser}")
            return 0

    async def _run_edge_engagement(
        self,
        runner,
        edge_accounts: List[Tuple[str, str]],
        max_comments: int,
        strict_inbox: bool
    ) -> int:
        """
        Run comment engagement via Edge (port 9223) for multiple accounts.

        IMPORTANT: Runs independently of Chrome - separate browser session.
        Processes accounts sequentially. If multiple channels share the same Edge session,
        we must explicitly switch the active channel in the YouTube account picker to avoid
        "no permission" pages when navigating directly to a channel inbox URL.
        
        Updated 2026-01-09: Now supports multiple Edge accounts.
        """
        total_processed = 0
        edge_driver = None
        edge_port = int(os.getenv("FOUNDUPS_EDGE_PORT", "9223"))
        edge_swapper = None

        try:
            from modules.infrastructure.dependency_launcher.src.dae_dependencies import (
                connect_edge_with_retry, STUDIO_FILTER, EDGE_DEBUG_PORT,
            )
            from modules.communication.video_comments.skillz.tars_account_swapper.account_swapper_skill import TarsAccountSwapper

            # HARDENED: Use retry helper with DevTools verification (2026-02-22)
            edge_driver = await asyncio.to_thread(
                connect_edge_with_retry,
                max_retries=3,
                retry_delay=2.0,
                relaunch_on_fail=True,
            )
            if edge_driver is None:
                logger.error("[ROTATE] Edge connection failed after retries - skipping Edge channels")
                return 0

            logger.info(f"[ROTATE] Connected to Edge on port {edge_port} (with retry)")
            edge_swapper = TarsAccountSwapper(edge_driver)

        except Exception as e:
            logger.warning(f"[ROTATE] Edge connection failed: {e}")
            logger.warning("[ROTATE] Edge channels will be skipped")
            logger.warning("[ROTATE] To enable: Launch Edge with --remote-debugging-port=9223")
            return 0

        # ============================================
        # AGENTIC PRE-AUDIT: Check which channels have work before processing
        # FIX 2026-03-21: Prioritize channels with pending comments, FoundUps first
        # ============================================
        audit_enabled = _env_truthy("YT_AGENTIC_AUDIT_ENABLED", "true")
        if audit_enabled and edge_swapper:
            try:
                logger.info("[ROTATE] [Edge] 🔍 Running agentic pre-audit...")
                audited_accounts = await self._audit_edge_channels(
                    edge_driver, edge_swapper, edge_accounts
                )
                if audited_accounts:
                    # Re-order: channels with work first, FoundUps prioritized
                    edge_accounts = audited_accounts
                    logger.info(f"[ROTATE] [Edge] ✅ Audit complete: {[a[0] for a in edge_accounts]}")
            except Exception as audit_err:
                logger.warning(f"[ROTATE] [Edge] Audit failed, using default order: {audit_err}")

        # Process each Edge account
        for idx, (account_name, channel_id) in enumerate(edge_accounts, 1):
            if self._should_skip_oops(account_name):
                logger.warning(f"[ROTATE] [Edge] Skipping {account_name}: OOPS cooldown active")
                continue
            # Check live stream signal
            try:
                from modules.platform_integration.stream_resolver.src.live_stream_signal import get_live_channel
                live_channel = get_live_channel()
            except ImportError:
                live_channel = None

            if live_channel == channel_id:
                logger.info(f"[SIGNAL] {account_name} has live stream - skipping comment processing")
                continue

            logger.info(f"\n[ROTATE] [Edge {idx}/{len(edge_accounts)}] Processing {account_name} comments...")

            try:
                from modules.infrastructure.dependency_launcher.src.dae_dependencies import STUDIO_FILTER

                # Navigate directly to Studio inbox for this channel
                # (Account picker swap is optional - direct URL navigation often works if both accounts signed in)
                studio_url = (
                    f"https://studio.youtube.com/channel/{channel_id}/comments/inbox?filter={STUDIO_FILTER}"
                )
                logger.info(f"[ROTATE] [Edge] Navigating directly to {account_name} Studio inbox...")
                logger.info(f"[ROTATE] [Edge] URL: {studio_url}")
                await asyncio.to_thread(edge_driver.get, studio_url)
                await asyncio.sleep(5)

                # Check for permission error (wrong account signed in)
                # HARDENED: Use bidirectional fallback before account switch
                try:
                    if _is_oops_page(edge_driver):
                        logger.warning(f"[ROTATE] [Edge] 🚨 OOPS PAGE detected for {account_name}")
                        self._record_oops(account_name)

                        # STEP 1: Try bidirectional fallback first (no account switch needed)
                        fallback_channel = CHANNEL_FALLBACKS.get(account_name)
                        if fallback_channel:
                            logger.info(f"[ROTATE] [Edge] 🔄 Trying fallback channel: {fallback_channel}")
                            fallback_id = CHANNEL_IDS.get(fallback_channel)
                            fallback_url = (
                                f"https://studio.youtube.com/channel/{fallback_id}/comments/inbox?filter={STUDIO_FILTER}"
                            )
                            await asyncio.to_thread(edge_driver.get, fallback_url)
                            await asyncio.sleep(5)

                            if not _is_oops_page(edge_driver):
                                # Fallback works! Process fallback channel instead
                                logger.info(f"[ROTATE] [Edge] ✅ Fallback to {fallback_channel} successful!")
                                # Update to process fallback channel
                                account_name = fallback_channel
                                channel_id = fallback_id
                                studio_url = fallback_url
                            else:
                                logger.warning(f"[ROTATE] [Edge] 🚨 Fallback {fallback_channel} also shows OOPS")
                                self._record_oops(fallback_channel)
                                # 2026-01-29: Detect wrong Google account scenario
                                wrong_account_msg = _detect_wrong_account_scenario(account_name, fallback_also_failed=True)
                                if wrong_account_msg:
                                    logger.warning(f"[ROTATE] [Edge] {wrong_account_msg}")

                        # STEP 2: If still on Oops (or no fallback), try DIRECT account switch from OOPS page
                        if _is_oops_page(edge_driver):
                            logger.warning(f"[ROTATE] [Edge] 🔄 Attempting DIRECT OOPS page switch for {account_name}...")
                            logger.info(f"[ROTATE] [Edge] Target section: {ACCOUNT_SECTIONS.get(account_name, '?')}")
                            if edge_swapper:
                                # 2026-01-29: Use swap_from_oops_page for direct OOPS page switch
                                # This clicks "Switch account" button on OOPS page directly
                                switched = await edge_swapper.swap_from_oops_page(account_name, navigate_to_comments=True)
                                if not switched:
                                    logger.error(f"[ROTATE] [Edge] Account swap failed for {account_name}; skipping")
                                    logger.warning(f"[ROTATE] [Edge] FIX: Sign into {account_name} in Edge browser")
                                    self._record_oops(account_name)
                                    continue
                                await asyncio.sleep(3)

                                # STEP 3: Verify after account switch
                                if _is_oops_page(edge_driver):
                                    logger.error(f"[ROTATE] [Edge] Still on OOPS after account switch; skipping {account_name}")
                                    self._record_oops(account_name)
                                    continue
                except Exception as perm_err:
                    # 2026-01-29: BUG FIX - Don't silently swallow swap errors
                    # Log at WARNING level and skip this channel
                    logger.warning(f"[ROTATE] [Edge] Permission check/swap error for {account_name}: {perm_err}")
                    continue  # Skip this channel on error

                self.log_studio_context(channel_id, f"{account_name} comment_engagement", edge_driver)
                self.set_active_channel(channel_id)

                logger.info(f"[ROTATE] [Edge] 🚀 Launching comment processor for {account_name}...")
                result = await runner.run_engagement(
                    channel_id=channel_id,
                    video_id=None,
                    max_comments=max_comments,
                    browser_port=9223,
                )

                result = result or {}
                stats = result.get("stats", {})
                processed = stats.get("comments_processed", 0)
                total_processed += processed

                self.update_engagement_status(channel_id, {
                    "all_processed": bool(stats.get("all_processed", False)),
                    "stats": stats,
                    "error": result.get("error"),
                    "updated_at": time.time(),
                })

                error_text = result.get("error")
                session_recovered = False

                if error_text:
                    logger.error(f"[ROTATE] {account_name} engagement failed: {error_text}")
                else:
                    logger.info(f"[ROTATE] {account_name} complete: {processed} comments processed")

                # Session recovery
                if error_text and _is_session_error(error_text) and _env_truthy("YT_RECONNECT_ON_SESSION_ERROR", "true"):
                    logger.warning(f"[ROTATE] Edge session error on {account_name}; attempting reconnect")
                    edge_driver = await self.reconnect_edge_driver(edge_port)
                    if edge_driver:
                        try:
                            await asyncio.to_thread(edge_driver.get, studio_url)
                            await asyncio.sleep(5)
                        except Exception as refresh_err:
                            logger.warning(f"[ROTATE] Edge navigation after reconnect failed: {refresh_err}")
                        session_recovered = True
                    else:
                        logger.warning(f"[ROTATE] Edge reconnect failed for {account_name}")

                # Inbox verification with retries
                processed = await self._verify_and_retry_engagement(
                    edge_driver, runner, channel_id, account_name,
                    max_comments, 9223, processed, strict_inbox, error_text, session_recovered
                )
                total_processed += processed - stats.get("comments_processed", 0)  # Add retry delta

                # FIX 2026-02-06: Check if comments STILL exist after verify/retry
                # User requirement: "stay on commenting till they're all commented"
                stay_on_channel = _env_truthy("YT_STAY_UNTIL_COMMENTS_CLEAR", "true")
                if stay_on_channel and edge_driver:
                    # Check DOM directly for comment count
                    try:
                        comment_count = edge_driver.execute_script(
                            "return document.querySelectorAll('ytcp-comment-thread').length || 0"
                        ) or 0
                        if comment_count > 0:
                            logger.info(f"[ROTATE] [Edge] {account_name} has {comment_count} comments REMAINING - re-running engagement")
                            # Re-run engagement for this channel
                            retry_result = await runner.run_engagement(
                                channel_id=channel_id,
                                video_id=None,
                                max_comments=max_comments
                            )
                            retry_result = retry_result or {}
                            retry_stats = retry_result.get('stats', {})
                            retry_processed = retry_stats.get('comments_processed', 0)
                            total_processed += retry_processed
                            self.update_engagement_status(channel_id, {
                                "all_processed": bool(retry_stats.get("all_processed", False)),
                                "stats": retry_stats,
                                "error": retry_result.get('error'),
                                "updated_at": time.time(),
                            })
                            logger.info(f"[ROTATE] [Edge] {account_name} re-run: {retry_processed} more comments processed")
                    except Exception as dom_err:
                        logger.debug(f"[ROTATE] [Edge] DOM comment check failed: {dom_err}")

                # ============================================
                # PER-CHANNEL SHORTS: Check unlisted shorts for THIS channel
                # Occam model: Comments → Shorts → Next Channel (not batch)
                # ============================================
                shorts_per_channel = _env_truthy("YT_SHORTS_PER_CHANNEL_ENABLED", "true")
                shorts_enabled = _env_truthy("YT_SHORTS_SCHEDULING_ENABLED", "true")

                if shorts_per_channel and shorts_enabled:
                    # Only run shorts if comments are done for this channel
                    # FIX 2026-02-18: Use local stats instead of non-existent attribute
                    all_comments_done = stats.get("all_processed", False)
                    if all_comments_done:
                        logger.info(f"[ROTATE] [Edge] {account_name} comments done → checking unlisted shorts...")
                        try:
                            from modules.platform_integration.youtube_shorts_scheduler.src.scheduler import YouTubeShortsScheduler
                            from modules.platform_integration.youtube_shorts_scheduler.src.schedule_tracker import ScheduleTracker

                            # Map account name to channel key
                            channel_key = account_name.lower().replace(" ", "")  # "FoundUps" -> "foundups"

                            # FIX 2026-03-19: Skip channels with sufficient coverage (14+ days ahead)
                            min_days = int(os.getenv("YT_SHORTS_MIN_DAYS_AHEAD", "14"))
                            tracker = ScheduleTracker(channel_id)
                            has_coverage, days_ahead = tracker.has_sufficient_coverage(min_days)
                            if has_coverage:
                                logger.info(f"[ROTATE] [Edge] {account_name}: {days_ahead} days scheduled ahead — SKIPPING shorts")
                                continue  # Skip to next channel

                            shorts_scheduler = YouTubeShortsScheduler(channel_key)
                            if shorts_scheduler.connect_browser():
                                max_shorts = int(os.getenv("YT_SHORTS_PER_CYCLE", "10"))
                                logger.info(f"[ROTATE] [Edge] Running shorts scheduler for {account_name} (max {max_shorts})...")

                                # Run scheduling cycle (sync, so wrap in thread)
                                shorts_result = await asyncio.to_thread(
                                    lambda: asyncio.run(shorts_scheduler.run_scheduling_cycle(max_videos=max_shorts))
                                )

                                scheduled = _shorts_scheduled_count(shorts_result)
                                logger.info(f"[ROTATE] [Edge] {account_name} shorts: {scheduled} scheduled")

                                shorts_scheduler.close()
                            else:
                                logger.warning(f"[ROTATE] [Edge] Could not connect to browser for {account_name} shorts")

                        except ImportError as ie:
                            logger.debug(f"[ROTATE] [Edge] Shorts scheduler not available: {ie}")
                        except Exception as shorts_err:
                            logger.warning(f"[ROTATE] [Edge] {account_name} shorts failed: {shorts_err}")
                    else:
                        logger.debug(f"[ROTATE] [Edge] {account_name} comments not done, skipping shorts")

            except Exception as e:
                error_str = str(e)
                logger.error(f"[ROTATE] {account_name} exception: {e}", exc_info=True)
                self.update_engagement_status(channel_id, {
                    "all_processed": False,
                    "stats": {},
                    "error": error_str,
                    "updated_at": time.time(),
                })

                # HARDENED: Try browser relaunch on window closed errors
                if _is_session_error(error_str):
                    logger.warning(f"[ROTATE] [Edge] 🔄 Session error detected - attempting browser recovery...")

                    # Step 1: Try reconnect first
                    edge_driver = await self.reconnect_edge_driver(edge_port)

                    # Step 2: If reconnect fails, try relaunch
                    if edge_driver is None:
                        logger.warning(f"[ROTATE] [Edge] Reconnect failed - attempting relaunch...")
                        try:
                            from modules.infrastructure.dependency_launcher.src.dae_dependencies import launch_edge
                            relaunch_ok, relaunch_msg = launch_edge(force=True)
                            if relaunch_ok:
                                await asyncio.sleep(5)  # Wait for browser to start
                                edge_opts = EdgeOptions()
                                edge_opts.add_experimental_option("debuggerAddress", f"127.0.0.1:{edge_port}")
                                edge_driver = await asyncio.to_thread(webdriver.Edge, options=edge_opts)
                                edge_swapper = TarsAccountSwapper(edge_driver)
                                logger.info(f"[ROTATE] [Edge] ✅ Browser relaunched successfully")

                                # 2026-01-29: WARMUP - Navigate to YouTube to load saved session
                                logger.info(f"[ROTATE] [Edge] 🔥 Warming up browser session...")
                                try:
                                    await asyncio.to_thread(edge_driver.get, "https://www.youtube.com")
                                    await asyncio.sleep(5)  # Wait for session/cookies to load
                                    logger.info(f"[ROTATE] [Edge] ✅ Browser session warmed up")
                                except Exception as warmup_err:
                                    logger.warning(f"[ROTATE] [Edge] Warmup navigation failed: {warmup_err}")
                            else:
                                logger.error(f"[ROTATE] [Edge] ❌ Browser relaunch failed: {relaunch_msg}")
                        except Exception as relaunch_err:
                            logger.error(f"[ROTATE] [Edge] ❌ Relaunch exception: {relaunch_err}")

                    if edge_driver is None:
                        logger.error(f"[ROTATE] [Edge] ❌ Cannot recover browser session - skipping remaining Edge channels")
                        break

            # Check live stream pending - only skip THIS channel's REMAINING work, continue rotation
            # Changed 2026-01-22: No longer breaks loop - continues to next channel
            if self.is_live_stream_pending():
                if _env_truthy("YT_STOP_ROTATION_ON_LIVE", "false"):  # Default OFF now
                    logger.info(f"[ROTATE] Live stream pending - stopping Edge rotation after {account_name}")
                    break
                else:
                    logger.info(f"[ROTATE] Live stream pending but YT_STOP_ROTATION_ON_LIVE=false - continuing to next channel")

            logger.info(f"[ROTATE] [Edge {idx}/{len(edge_accounts)}] ✅ {account_name} complete - continuing rotation...")

        return total_processed


    async def _run_chrome_engagement(
        self,
        runner,
        chrome_accounts: List[Tuple[str, str]],
        max_comments: int,
        strict_inbox: bool
    ) -> int:
        """
        Run comment engagement on Chrome channels (registry-driven).

        Uses TarsAccountSwapper for account switching within same Google account.
        """
        total_processed = 0
        total_shorts_scheduled = 0  # Track shorts for LinkedIn rotation trigger
        chrome_driver = None
        swapper = None
        rotation_halt = False

        try:
            from modules.communication.video_comments.skillz.tars_account_swapper.account_swapper_skill import TarsAccountSwapper
            from modules.infrastructure.dependency_launcher.src.dae_dependencies import (
                connect_chrome_with_retry,
                CHROME_DEBUG_PORT,
            )

            chrome_port = int(os.getenv("FOUNDUPS_LIVECHAT_CHROME_PORT", str(CHROME_DEBUG_PORT)))

            # HARDENED: Use retry helper with DevTools verification (2026-02-22)
            chrome_driver = await asyncio.to_thread(
                connect_chrome_with_retry,
                max_retries=3,
                retry_delay=2.0,
                relaunch_on_fail=True,
            )
            if chrome_driver is None:
                logger.error("[ROTATE] Chrome connection failed after retries - skipping Chrome channels")
                return 0

            swapper = TarsAccountSwapper(chrome_driver)
            logger.info(f"[ROTATE] Connected to Chrome on port {chrome_port} (with retry)")

            # 2026-01-29: WARMUP - Navigate to YouTube to ensure session is loaded
            try:
                current_url = chrome_driver.current_url
                if "youtube.com" not in current_url:
                    logger.info(f"[ROTATE] [Chrome] 🔥 Warming up browser session...")
                    await asyncio.to_thread(chrome_driver.get, "https://www.youtube.com")
                    await asyncio.sleep(3)  # Wait for session/cookies to load
                    logger.info(f"[ROTATE] [Chrome] ✅ Browser session warmed up")
            except Exception as warmup_err:
                logger.warning(f"[ROTATE] [Chrome] Warmup check failed: {warmup_err}")

            # Smart rotation: detect current account to minimize switching
            chrome_accounts = await self._optimize_rotation_order(chrome_driver, chrome_accounts)

            # ============================================
            # AGENTIC PRE-AUDIT: Check which Chrome channels have work
            # FIX 2026-03-21: Comments + Shorts + Indexing (Chrome handles indexing)
            # ============================================
            audit_enabled = _env_truthy("YT_AGENTIC_AUDIT_ENABLED", "true")
            if audit_enabled and swapper:
                try:
                    logger.info("[ROTATE] [Chrome] 🔍 Running agentic pre-audit...")
                    audited_accounts = await self._audit_chrome_channels(
                        chrome_driver, swapper, chrome_accounts
                    )
                    if audited_accounts:
                        chrome_accounts = audited_accounts
                        logger.info(f"[ROTATE] [Chrome] ✅ Audit complete: {[a[0] for a in chrome_accounts]}")
                except Exception as audit_err:
                    logger.warning(f"[ROTATE] [Chrome] Audit failed, using default order: {audit_err}")

            if not await self._driver_session_alive(chrome_driver, "Chrome"):
                logger.warning("[ROTATE] [Chrome] Session invalid after connect; attempting immediate reconnect")
                chrome_driver = await self.reconnect_chrome_driver(chrome_port)
                if chrome_driver is None:
                    logger.error("[ROTATE] [Chrome] Immediate reconnect failed - skipping Chrome channels")
                    return 0
                swapper = TarsAccountSwapper(chrome_driver)
                try:
                    await asyncio.to_thread(chrome_driver.get, "https://www.youtube.com")
                    await asyncio.sleep(3)
                except Exception as warmup_err:
                    logger.warning(f"[ROTATE] [Chrome] Warmup after reconnect failed: {warmup_err}")

        except Exception as e:
            logger.error(f"[ROTATE] Failed to connect to Chrome: {e}")
            names = ", ".join([a[0] for a in chrome_accounts]) or "none"
            logger.warning(f"[ROTATE] Chrome channels ({names}) will be skipped")
            return 0

        # Process each Chrome account
        for idx, (account_name, channel_id) in enumerate(chrome_accounts, 1):
            if self._should_skip_oops(account_name):
                logger.warning(f"[ROTATE] [Chrome] Skipping {account_name}: OOPS cooldown active")
                continue
            # Check live stream signal
            try:
                from modules.platform_integration.stream_resolver.src.live_stream_signal import get_live_channel
                live_channel = get_live_channel()
            except ImportError:
                live_channel = None

            if live_channel == channel_id:
                logger.info(f"[SIGNAL] {account_name} has live stream - prioritizing live chat over comments")
                continue

            logger.info(f"\n[ROTATE] [Chrome {idx}/{len(chrome_accounts)}] Processing {account_name} comments...")

            try:
                # Account switching
                logger.info(f"[ROTATE] Switching to {account_name}...")
                success = await swapper.swap_to(account_name)

                if not success:
                    logger.warning(f"[ROTATE] Failed to switch to {account_name}")
                    if idx == 1:
                        logger.info(f"[ROTATE] Assuming already on {account_name}, continuing...")
                    else:
                        logger.warning(f"[ROTATE] Skipping {account_name}")
                        continue
                else:
                    logger.info(f"[ROTATE] Switched to {account_name} successfully")

                # Refresh for fresh comments (async to not block event loop)
                logger.info(f"[ROTATE] Refreshing page for {account_name}...")
                await asyncio.to_thread(chrome_driver.refresh)
                await asyncio.sleep(5)

                # HARDENED: Check for Oops page after switch/refresh
                # 2026-02-03: Use swap_from_oops_page() which has full cascade:
                # DOM "Switch Account" -> UI-TARS "Switch Account" -> DOM "Return to Studio" -> UI-TARS "Return to Studio" -> Direct URL
                if _is_oops_page(chrome_driver):
                    logger.warning(f"[ROTATE] [Chrome] 🚨 OOPS PAGE detected for {account_name}")
                    self._record_oops(account_name)

                    # Try DIRECT OOPS page resolution first (with UI-TARS fallback)
                    logger.info(f"[ROTATE] [Chrome] 🔄 Attempting OOPS page resolution for {account_name}...")
                    oops_resolved = await swapper.swap_from_oops_page(account_name, navigate_to_comments=True)

                    if oops_resolved and not _is_oops_page(chrome_driver):
                        logger.info(f"[ROTATE] [Chrome] ✅ OOPS page resolved for {account_name}")
                    else:
                        # OOPS resolution failed for target - try bidirectional fallback
                        fallback_channel = CHANNEL_FALLBACKS.get(account_name)
                        if fallback_channel:
                            logger.info(f"[ROTATE] [Chrome] 🔄 Trying fallback channel: {fallback_channel}")
                            fallback_id = CHANNEL_IDS.get(fallback_channel)

                            # Use swap_from_oops_page for fallback too (handles OOPS cascade)
                            fallback_success = await swapper.swap_from_oops_page(fallback_channel, navigate_to_comments=True)
                            if fallback_success and not _is_oops_page(chrome_driver):
                                logger.info(f"[ROTATE] [Chrome] ✅ Fallback to {fallback_channel} successful!")
                                account_name = fallback_channel
                                channel_id = fallback_id
                            else:
                                logger.warning(f"[ROTATE] [Chrome] 🚨 Fallback {fallback_channel} also failed")
                                self._record_oops(fallback_channel)
                                # 2026-01-29: Detect wrong Google account scenario
                                wrong_account_msg = _detect_wrong_account_scenario(account_name, fallback_also_failed=True)
                                if wrong_account_msg:
                                    logger.warning(f"[ROTATE] [Chrome] {wrong_account_msg}")
                                logger.warning(f"[ROTATE] [Chrome] Skipping {account_name} - manual account fix needed")
                                continue
                        else:
                            logger.warning(f"[ROTATE] [Chrome] No fallback available - skipping {account_name}")
                            continue

            except Exception as e:
                error_text = str(e)
                logger.error(f"[ROTATE] Account switch error: {e}")

                recovered = False
                if _is_session_error(error_text) and _env_truthy("YT_RECONNECT_ON_SESSION_ERROR", "true"):
                    logger.warning(f"[ROTATE] [Chrome] Session error during switch to {account_name}; reconnecting")
                    chrome_driver = await self.reconnect_chrome_driver(chrome_port)
                    if chrome_driver:
                        swapper = TarsAccountSwapper(chrome_driver)
                        recovered = await self._driver_session_alive(chrome_driver, "Chrome")
                    else:
                        logger.warning("[ROTATE] [Chrome] Reconnect failed during account switch")

                if recovered:
                    try:
                        success = await swapper.swap_to(account_name)
                        if not success:
                            logger.warning(f"[ROTATE] [Chrome] Post-reconnect switch failed for {account_name}")
                            continue
                        logger.info(f"[ROTATE] [Chrome] Recovered and switched to {account_name}")
                    except Exception as retry_err:
                        logger.warning(f"[ROTATE] [Chrome] Post-reconnect switch exception: {retry_err}")
                        continue
                elif idx > 1 or _is_session_error(error_text):
                    continue

            # Process comments
            try:
                self.set_active_channel(channel_id)
                self.log_studio_context(channel_id, f"{account_name} comment_engagement", chrome_driver)

                logger.info(f"[ROTATE] [Chrome] 🚀 Launching comment processor for {account_name}...")
                result = await runner.run_engagement(
                    channel_id=channel_id,
                    video_id=None,
                    max_comments=max_comments
                )

                result = result or {}
                stats = result.get('stats', {})
                processed = stats.get('comments_processed', 0)
                total_processed += processed

                self.update_engagement_status(channel_id, {
                    "all_processed": bool(stats.get("all_processed", False)),
                    "stats": stats,
                    "error": result.get('error'),
                    "updated_at": time.time(),
                })

                error_text = result.get('error')
                session_recovered = False

                if error_text:
                    logger.error(f"[ROTATE] {account_name} engagement failed: {error_text}")
                else:
                    logger.info(f"[ROTATE] {account_name} complete: {processed} comments processed")

                # Session recovery
                if error_text and _is_session_error(error_text) and _env_truthy("YT_RECONNECT_ON_SESSION_ERROR", "true"):
                    logger.warning(f"[ROTATE] Chrome session error on {account_name}; attempting reconnect")
                    chrome_driver = await self.reconnect_chrome_driver(chrome_port)
                    if chrome_driver:
                        swapper = TarsAccountSwapper(chrome_driver)
                        try:
                            await swapper.swap_to(account_name)
                        except Exception as swap_err:
                            logger.warning(f"[ROTATE] Chrome reconnect swap failed: {swap_err}")
                        try:
                            await asyncio.to_thread(chrome_driver.refresh)
                            await asyncio.sleep(5)
                        except Exception as refresh_err:
                            logger.warning(f"[ROTATE] Chrome refresh after reconnect failed: {refresh_err}")
                        session_recovered = True
                    else:
                        logger.warning(f"[ROTATE] Chrome reconnect failed for {account_name}")

                # Verify and retry
                processed = await self._verify_and_retry_engagement(
                    chrome_driver, runner, channel_id, account_name,
                    max_comments, 9222, processed, strict_inbox, error_text, session_recovered
                )
                total_processed += processed - stats.get('comments_processed', 0)  # Add retry delta

                # FIX 2026-02-06: Check if comments STILL exist after verify/retry
                # User requirement: "stay on commenting till they're all commented"
                stay_on_channel = _env_truthy("YT_STAY_UNTIL_COMMENTS_CLEAR", "true")
                if stay_on_channel:
                    # FIX 2026-02-18: Use local stats instead of fragile callback access
                    all_done = stats.get("all_processed", True)
                    if not all_done:
                        # Check DOM directly for comment count
                        try:
                            comment_count = chrome_driver.execute_script(
                                "return document.querySelectorAll('ytcp-comment-thread').length || 0"
                            ) or 0
                            if comment_count > 0:
                                logger.info(f"[ROTATE] {account_name} has {comment_count} comments REMAINING - re-running engagement")
                                # Re-run engagement for this channel
                                retry_result = await runner.run_engagement(
                                    channel_id=channel_id,
                                    video_id=None,
                                    max_comments=max_comments
                                )
                                retry_result = retry_result or {}
                                retry_stats = retry_result.get('stats', {})
                                retry_processed = retry_stats.get('comments_processed', 0)
                                total_processed += retry_processed
                                self.update_engagement_status(channel_id, {
                                    "all_processed": bool(retry_stats.get("all_processed", False)),
                                    "stats": retry_stats,
                                    "error": retry_result.get('error'),
                                    "updated_at": time.time(),
                                })
                                logger.info(f"[ROTATE] {account_name} re-run: {retry_processed} more comments processed")
                        except Exception as dom_err:
                            logger.debug(f"[ROTATE] DOM comment check failed: {dom_err}")

                # ============================================
                # PER-CHANNEL SHORTS: Check unlisted shorts for THIS channel (Chrome)
                # Occam model: Comments → Shorts → Next Channel (not batch)
                # FIX 2026-02-24: Added per-channel shorts for Chrome (was Edge-only)
                # ============================================
                shorts_per_channel = _env_truthy("YT_SHORTS_PER_CHANNEL_ENABLED", "true")
                shorts_enabled = _env_truthy("YT_SHORTS_SCHEDULING_ENABLED", "true")

                if shorts_per_channel and shorts_enabled:
                    # Only run shorts if comments are done for this channel
                    all_comments_done = stats.get("all_processed", False)
                    if all_comments_done:
                        logger.info(f"[ROTATE] [Chrome] {account_name} comments done → checking unlisted shorts...")
                        try:
                            from modules.platform_integration.youtube_shorts_scheduler.src.scheduler import YouTubeShortsScheduler
                            from modules.platform_integration.youtube_shorts_scheduler.src.schedule_tracker import ScheduleTracker

                            # Map account name to channel key
                            channel_key = account_name.lower().replace(" ", "")  # "Move2Japan" -> "move2japan"

                            # FIX 2026-03-19: Skip channels with sufficient coverage (14+ days ahead)
                            min_days = int(os.getenv("YT_SHORTS_MIN_DAYS_AHEAD", "14"))
                            tracker = ScheduleTracker(channel_id)
                            has_coverage, days_ahead = tracker.has_sufficient_coverage(min_days)
                            if has_coverage:
                                logger.info(f"[ROTATE] [Chrome] {account_name}: {days_ahead} days scheduled ahead — SKIPPING shorts")
                                continue  # Skip to next channel

                            shorts_scheduler = YouTubeShortsScheduler(channel_key)
                            if shorts_scheduler.connect_browser():
                                max_shorts = int(os.getenv("YT_SHORTS_PER_CYCLE", "10"))
                                logger.info(f"[ROTATE] [Chrome] Running shorts scheduler for {account_name} (max {max_shorts})...")

                                # Run scheduling cycle (sync, so wrap in thread)
                                shorts_result = await asyncio.to_thread(
                                    lambda: asyncio.run(shorts_scheduler.run_scheduling_cycle(max_videos=max_shorts))
                                )

                                scheduled = _shorts_scheduled_count(shorts_result)
                                total_shorts_scheduled += scheduled  # Accumulate for LinkedIn trigger
                                logger.info(f"[ROTATE] [Chrome] {account_name} shorts: {scheduled} scheduled (total: {total_shorts_scheduled})")

                                shorts_scheduler.close()
                            else:
                                logger.warning(f"[ROTATE] [Chrome] Could not connect to browser for {account_name} shorts")

                        except ImportError as ie:
                            logger.debug(f"[ROTATE] [Chrome] Shorts scheduler not available: {ie}")
                        except Exception as shorts_err:
                            logger.warning(f"[ROTATE] [Chrome] {account_name} shorts failed: {shorts_err}")
                    else:
                        logger.debug(f"[ROTATE] [Chrome] {account_name} comments not done, skipping shorts")

                # Check halt conditions
                if strict_inbox:
                    if error_text and not session_recovered:
                        logger.warning(f"[VERIFY] Strict inbox mode: holding rotation on {account_name} (error)")
                        rotation_halt = True

            except Exception as e:
                logger.error(f"[ROTATE] {account_name} exception: {e}", exc_info=True)
                self.update_engagement_status(channel_id, {
                    "all_processed": False,
                    "stats": {},
                    "error": str(e),
                    "updated_at": time.time(),
                })
                if strict_inbox:
                    rotation_halt = True

            # Rotation halt check - only halt if explicitly enabled (default: continue)
            if rotation_halt:
                if _env_truthy("YT_ROTATION_HALT_ON_ERROR", "false"):  # Default OFF now
                    logger.warning(f"[ROTATE] Rotation halted after {account_name} (YT_ROTATION_HALT_ON_ERROR=true)")
                    break
                else:
                    logger.warning(f"[ROTATE] Error on {account_name} but YT_ROTATION_HALT_ON_ERROR=false - continuing rotation")
                    rotation_halt = False  # Reset for next channel

            # Check live stream pending - only skip THIS channel's REMAINING work, continue rotation
            # Changed 2026-01-22: No longer breaks loop - continues to next channel
            if self.is_live_stream_pending():
                if _env_truthy("YT_STOP_ROTATION_ON_LIVE", "false"):  # Default OFF now
                    logger.info(f"[ROTATE] Live stream pending - stopping Chrome rotation after {account_name}")
                    break
                else:
                    logger.info(f"[ROTATE] Live stream pending but YT_STOP_ROTATION_ON_LIVE=false - continuing to next channel")

            logger.info(f"[ROTATE] [Chrome {idx}/{len(chrome_accounts)}] ✅ {account_name} complete - continuing rotation...")

        # ============================================
        # LINKEDIN GROUP ROTATION (after Chrome YT loop)
        # Occam flow: Comments → Shorts → LN Group (approve + post) → Return
        # FIX 2026-02-24: Added LinkedIn rotation after YT shorts
        # ============================================
        ln_rotation_enabled = _env_truthy("LN_GROUP_ROTATION_ENABLED", "true")
        ln_shorts_threshold = int(os.getenv("LN_GROUP_SHORTS_THRESHOLD", "10"))

        if ln_rotation_enabled and total_shorts_scheduled >= ln_shorts_threshold:
            logger.info(f"[ROTATE] [LinkedIn] {total_shorts_scheduled} shorts scheduled >= {ln_shorts_threshold} threshold → running LinkedIn group rotation...")
            try:
                from modules.platform_integration.linkedin_agent.skillz.openclaw_group_news.executor import (
                    run_group_membership_cycle,
                    run_openclaw_news_flow,
                )

                # Check for dry-run mode (default: live)
                ln_dry_run = _env_truthy("LN_GROUP_DRY_RUN", "false")
                ln_max_members = int(os.getenv("LN_GROUP_MAX_MEMBERS", "10"))

                # Step 1: Approve pending members with welcome messages
                logger.info(f"[ROTATE] [LinkedIn] Step 1: Checking group membership requests (max={ln_max_members}, dry_run={ln_dry_run})...")
                membership_result = await asyncio.to_thread(
                    lambda: run_group_membership_cycle(
                        dry_run=ln_dry_run,
                        max_requests=ln_max_members,
                        send_welcome=True,
                        approve=True,
                        post_news_after=False  # We handle news separately
                    )
                )
                approved = membership_result.get("approved", 0)
                messaged = membership_result.get("messaged", 0)
                logger.info(f"[ROTATE] [LinkedIn] Membership: {approved} approved, {messaged} welcomed")

                # Step 2: Search, rate, and post OpenClaw news
                logger.info(f"[ROTATE] [LinkedIn] Step 2: Searching and posting OpenClaw news (dry_run={ln_dry_run})...")
                news_result = await asyncio.to_thread(
                    lambda: run_openclaw_news_flow(dry_run=ln_dry_run)
                )
                news_posted = news_result.get("posted", False)
                news_status = news_result.get("status", "unknown")
                logger.info(f"[ROTATE] [LinkedIn] News: status={news_status}, posted={news_posted}")

                logger.info(f"[ROTATE] [LinkedIn] ✅ Group rotation complete - returning to YT comments next cycle")

            except ImportError as ie:
                logger.debug(f"[ROTATE] [LinkedIn] Group executor not available: {ie}")
            except Exception as ln_err:
                logger.warning(f"[ROTATE] [LinkedIn] Group rotation failed: {ln_err}")
        elif ln_rotation_enabled:
            logger.debug(f"[ROTATE] [LinkedIn] {total_shorts_scheduled} shorts < {ln_shorts_threshold} threshold - skipping LinkedIn rotation")

        return total_processed

    async def _optimize_rotation_order(
        self,
        chrome_driver,
        chrome_accounts: List[Tuple[str, str]]
    ) -> List[Tuple[str, str]]:
        """
        Optimize rotation order based on current browser state.

        If already on a target channel, move it to front to minimize switching.
        """
        try:
            current_url = chrome_driver.current_url
            url_base = (current_url or "").split("#", 1)[0].split("?", 1)[0]
            logger.info(f"[ROTATE] Current Chrome URL: {url_base}")

            current_channel_id = await self.detect_current_channel_id(chrome_driver)

            if current_channel_id:
                current_account = next(
                    (acc for acc in chrome_accounts if acc[1] == current_channel_id), None
                )
                if current_account:
                    logger.info(f"[ROTATE] [SMART] Detected active session on {current_account[0]}")
                    logger.info(f"[ROTATE] [SMART] Reordering queue: {current_account[0]} -> Others")
                    chrome_accounts = list(chrome_accounts)  # Copy
                    chrome_accounts.remove(current_account)
                    chrome_accounts.insert(0, current_account)
                else:
                    logger.info(f"[ROTATE] [SMART] Current channel {current_channel_id} not in rotation list")
            else:
                logger.info("[ROTATE] [SMART] Not currently on a Studio channel page")

        except Exception as e:
            logger.warning(f"[ROTATE] [SMART] Failed to detect current state: {e}")

        return chrome_accounts

    async def _audit_edge_channels(
        self,
        edge_driver,
        edge_swapper,
        edge_accounts: List[Tuple[str, str]],
    ) -> List[Tuple[str, str]]:
        """
        Agentic pre-audit: Check which Edge channels have pending work.

        Checks THREE work types:
        1. Comments: DOM query for ytcp-comment-thread count
        2. Shorts: ScheduleTracker.has_sufficient_coverage() (needs scheduling?)
        3. Indexing: (Chrome-only, not checked here)

        Returns reordered list: FoundUps first, then channels with work, then rest.
        FIX 2026-03-21: Don't waste time on channels with no work.
        """
        from modules.infrastructure.dependency_launcher.src.dae_dependencies import STUDIO_FILTER

        # (name, id, comment_count, needs_shorts, is_foundups)
        channel_work: List[Tuple[str, str, int, bool, bool]] = []

        # Check shorts coverage (fast, no browser navigation)
        shorts_coverage_map: Dict[str, bool] = {}
        try:
            from modules.platform_integration.youtube_shorts_scheduler.src.schedule_tracker import ScheduleTracker
            min_days = int(os.getenv("YT_SHORTS_MIN_DAYS_AHEAD", "14"))
            for account_name, channel_id in edge_accounts:
                tracker = ScheduleTracker(channel_id)
                has_coverage, days_ahead = tracker.has_sufficient_coverage(min_days)
                shorts_coverage_map[channel_id] = not has_coverage  # needs_shorts = NOT has_coverage
                logger.debug(f"[AUDIT] {account_name} shorts: {'covered' if has_coverage else 'NEEDS WORK'} ({days_ahead} days)")
        except Exception as e:
            logger.warning(f"[AUDIT] Shorts coverage check failed: {e}")

        for account_name, channel_id in edge_accounts:
            is_foundups = account_name.lower() == "foundups"
            comment_count = 0
            needs_shorts = shorts_coverage_map.get(channel_id, True)  # Default: needs work

            try:
                # Quick navigate to inbox
                studio_url = f"https://studio.youtube.com/channel/{channel_id}/comments/inbox?filter={STUDIO_FILTER}"
                await asyncio.to_thread(edge_driver.get, studio_url)
                await asyncio.sleep(3)  # Wait for DOM

                # Count comments (same query as _verify_studio_inbox_clear)
                comment_count = edge_driver.execute_script(
                    "return document.querySelectorAll('ytcp-comment-thread').length || 0"
                ) or 0

                shorts_status = "📹 shorts needed" if needs_shorts else "✓ shorts covered"
                logger.info(f"[AUDIT] {account_name}: {comment_count} comments, {shorts_status}")

            except Exception as e:
                logger.warning(f"[AUDIT] {account_name} check failed: {e}")

            channel_work.append((account_name, channel_id, comment_count, needs_shorts, is_foundups))

        # Sort: FoundUps first, then by total work (comments + shorts)
        def sort_key(item):
            name, cid, comments, needs_shorts, is_foundups = item
            has_any_work = comments > 0 or needs_shorts
            # Lower = higher priority
            # FoundUps: 0, others with work: 1, others without work: 2
            if is_foundups:
                return (0, -comments)
            elif has_any_work:
                return (1, -comments, 0 if needs_shorts else 1)
            else:
                return (2, 0, 1)

        channel_work.sort(key=sort_key)

        # Log audit result
        for name, cid, comments, needs_shorts, is_fp in channel_work:
            work_items = []
            if comments > 0:
                work_items.append(f"{comments} comments")
            if needs_shorts:
                work_items.append("shorts")
            work_str = ", ".join(work_items) if work_items else "no work"
            status = "🐕 FOUNDUPS" if is_fp else ("✓ " + work_str if work_items else "○ " + work_str)
            logger.info(f"[AUDIT] Order: {name} - {status}")

        return [(name, cid) for name, cid, comments, needs_shorts, is_fp in channel_work]

    async def _audit_chrome_channels(
        self,
        chrome_driver,
        swapper,
        chrome_accounts: List[Tuple[str, str]],
    ) -> List[Tuple[str, str]]:
        """
        Agentic pre-audit: Check which Chrome channels have pending work.

        Checks THREE work types:
        1. Comments: DOM query for ytcp-comment-thread count
        2. Shorts: ScheduleTracker.has_sufficient_coverage()
        3. Indexing: Check VideoIndexStore for unindexed videos (Chrome-specific)

        Returns reordered list: FoundUps first, then channels with work, then rest.
        FIX 2026-03-21: Chrome handles indexing in addition to comments/shorts.
        """
        from modules.infrastructure.dependency_launcher.src.dae_dependencies import STUDIO_FILTER

        # (name, id, comment_count, needs_shorts, needs_indexing, is_foundups)
        channel_work: List[Tuple[str, str, int, bool, bool, bool]] = []

        # Check shorts coverage (fast, no browser navigation)
        shorts_coverage_map: Dict[str, bool] = {}
        try:
            from modules.platform_integration.youtube_shorts_scheduler.src.schedule_tracker import ScheduleTracker
            min_days = int(os.getenv("YT_SHORTS_MIN_DAYS_AHEAD", "14"))
            for account_name, channel_id in chrome_accounts:
                tracker = ScheduleTracker(channel_id)
                has_coverage, days_ahead = tracker.has_sufficient_coverage(min_days)
                shorts_coverage_map[channel_id] = not has_coverage
        except Exception as e:
            logger.warning(f"[AUDIT] [Chrome] Shorts coverage check failed: {e}")

        # Check indexing needs (fast, local file check)
        indexing_needed_map: Dict[str, bool] = {}
        if os.getenv("YT_VIDEO_INDEXING_ENABLED", "false").lower() in ("1", "true", "yes"):
            try:
                from modules.ai_intelligence.video_indexer.src.studio_ask_indexer import INDEX_ROOT, VideoIndexStore
                for account_name, channel_id in chrome_accounts:
                    channel_key = account_name.lower().replace(" ", "")
                    store = VideoIndexStore(base_path=str(INDEX_ROOT / channel_key))
                    # Check if any recent videos need indexing (simple heuristic)
                    # If index directory is empty or very small, needs indexing
                    index_count = len(list((INDEX_ROOT / channel_key).glob("*.json"))) if (INDEX_ROOT / channel_key).exists() else 0
                    needs_indexing = index_count < 10  # Arbitrary threshold
                    indexing_needed_map[channel_id] = needs_indexing
            except Exception as e:
                logger.debug(f"[AUDIT] [Chrome] Indexing check skipped: {e}")

        for account_name, channel_id in chrome_accounts:
            is_foundups = account_name.lower() == "foundups"
            comment_count = 0
            needs_shorts = shorts_coverage_map.get(channel_id, True)
            needs_indexing = indexing_needed_map.get(channel_id, False)

            try:
                # Quick navigate to inbox
                studio_url = f"https://studio.youtube.com/channel/{channel_id}/comments/inbox?filter={STUDIO_FILTER}"
                await asyncio.to_thread(chrome_driver.get, studio_url)
                await asyncio.sleep(3)

                comment_count = chrome_driver.execute_script(
                    "return document.querySelectorAll('ytcp-comment-thread').length || 0"
                ) or 0

                work_parts = []
                if comment_count > 0:
                    work_parts.append(f"{comment_count} comments")
                if needs_shorts:
                    work_parts.append("shorts")
                if needs_indexing:
                    work_parts.append("indexing")
                work_str = ", ".join(work_parts) if work_parts else "no work"
                logger.info(f"[AUDIT] [Chrome] {account_name}: {work_str}")

            except Exception as e:
                logger.warning(f"[AUDIT] [Chrome] {account_name} check failed: {e}")

            channel_work.append((account_name, channel_id, comment_count, needs_shorts, needs_indexing, is_foundups))

        # Sort: FoundUps first, then by total work
        def sort_key(item):
            name, cid, comments, needs_shorts, needs_indexing, is_foundups = item
            has_any_work = comments > 0 or needs_shorts or needs_indexing
            if is_foundups:
                return (0, -comments)
            elif has_any_work:
                work_score = comments + (10 if needs_shorts else 0) + (5 if needs_indexing else 0)
                return (1, -work_score)
            else:
                return (2, 0)

        channel_work.sort(key=sort_key)

        # Log audit result
        for name, cid, comments, needs_shorts, needs_indexing, is_fp in channel_work:
            work_items = []
            if comments > 0:
                work_items.append(f"{comments} comments")
            if needs_shorts:
                work_items.append("shorts")
            if needs_indexing:
                work_items.append("indexing")
            work_str = ", ".join(work_items) if work_items else "no work"
            status = "🐕 FOUNDUPS" if is_fp else ("✓ " + work_str if work_items else "○ " + work_str)
            logger.info(f"[AUDIT] [Chrome] Order: {name} - {status}")

        return [(name, cid) for name, cid, comments, needs_shorts, needs_indexing, is_fp in channel_work]

    async def _verify_and_retry_engagement(
        self,
        driver,
        runner,
        channel_id: str,
        account_name: str,
        max_comments: int,
        browser_port: int,
        processed: int,
        strict_inbox: bool,
        error_text: Optional[str],
        session_recovered: bool
    ) -> int:
        """
        Verify inbox is clear and retry engagement if needed.
        """
        verify_retries = int(os.getenv("YT_INBOX_VERIFY_RETRIES", "1"))
        verify_timeout = float(os.getenv("YT_INBOX_VERIFY_TIMEOUT", "15"))
        verify_result = None

        for attempt in range(1, verify_retries + 1):
            verify_result = await self.verify_studio_inbox_clear(
                driver, channel_id, account_name, verify_timeout
            )

            if verify_result is True:
                break

            if verify_result is False:
                logger.warning(
                    f"[VERIFY] {account_name} inbox not clear; re-running engagement "
                    f"(attempt {attempt}/{verify_retries})"
                )
                self.set_active_channel(channel_id)
                self.log_studio_context(channel_id, f"{account_name} comment_engagement_retry", driver)

                retry_result = await runner.run_engagement(
                    channel_id=channel_id,
                    video_id=None,
                    max_comments=max_comments,
                    browser_port=browser_port,
                )

                retry_result = retry_result or {}
                retry_stats = retry_result.get('stats', {})
                retry_processed = retry_stats.get('comments_processed', 0)

                self.update_engagement_status(channel_id, {
                    "all_processed": bool(retry_stats.get("all_processed", False)),
                    "stats": retry_stats,
                    "error": retry_result.get('error'),
                    "updated_at": time.time(),
                })

                if retry_result.get('error'):
                    logger.error(f"[ROTATE] {account_name} retry failed: {retry_result.get('error')}")
                else:
                    logger.info(f"[ROTATE] {account_name} retry complete: {retry_processed} comments processed")

                processed += retry_processed
                continue

            logger.warning(f"[VERIFY] {account_name} inbox verification inconclusive; will recheck next cycle")
            break

        # Handle strict inbox mode results
        if strict_inbox:
            if verify_result is False:
                logger.warning(f"[VERIFY] Strict inbox mode: holding rotation on {account_name} (unprocessed comments)")
            elif verify_result is None:
                logger.info(f"[VERIFY] {account_name} verification inconclusive; continuing to next channel")

        return processed

    async def _run_shorts_scheduling_chain(
        self,
        chrome_accounts: List[Tuple[str, str]],
        edge_accounts: List[Tuple[str, str]],
    ) -> int:
        """
        Run Shorts scheduling for all channels after comment engagement completes.

        DAE Chaining: Comments → Scheduling (same browser sessions)

        Flow:
        1. Schedule Chrome channels - port 9222
        2. Schedule Edge channels - port 9223

        Uses existing browser connections from comment engagement.

        Args:
            chrome_accounts: List of (name, channel_id) for Chrome
            edge_accounts: List of (name, channel_id) for Edge

        Returns:
            Total videos scheduled across all channels
        """
        total_scheduled = 0

        shorts_key_by_name: Dict[str, str] = {}
        for ch in get_channels(role="shorts"):
            key = ch.get("key")
            if not key:
                continue
            for name in (ch.get("name"), ch.get("key")):
                if name:
                    shorts_key_by_name[name.lower()] = key

        try:
            from modules.platform_integration.youtube_shorts_scheduler.src.scheduler import run_scheduler_dae
        except ImportError as e:
            logger.error(f"[CHAIN] Cannot import scheduler: {e}")
            return 0

        # Max videos per scheduling run (0 = unlimited, 2026-01-28)
        max_videos = int(os.getenv("YT_SHORTS_SCHEDULE_MAX_VIDEOS", "0"))
        dry_run = _env_truthy("YT_SHORTS_SCHEDULE_DRY_RUN", "false")

        # Schedule Chrome channels
        for account_name, channel_id in chrome_accounts:
            channel_key = shorts_key_by_name.get(account_name.lower())
            if not channel_key:
                logger.info(f"[CHAIN] [Chrome] {account_name}: shorts role disabled or missing; skipping")
                continue

            logger.info(f"[CHAIN] [Chrome] Scheduling Shorts for {account_name}...")
            try:
                result = await run_scheduler_dae(
                    channel_key=channel_key,
                    max_videos=max_videos,
                    dry_run=dry_run,
                )
                scheduled = len(result.get("scheduled", []))
                total_scheduled += scheduled
                logger.info(f"[CHAIN] [Chrome] {account_name}: {scheduled} videos scheduled")

                if result.get("errors"):
                    for err in result["errors"]:
                        logger.warning(f"[CHAIN] [Chrome] {account_name} error: {err}")
            except Exception as e:
                logger.error(f"[CHAIN] [Chrome] {account_name} scheduling failed: {e}")

        # Schedule Edge channels
        for account_name, channel_id in edge_accounts:
            channel_key = shorts_key_by_name.get(account_name.lower())
            if not channel_key:
                logger.info(f"[CHAIN] [Edge] {account_name}: shorts role disabled or missing; skipping")
                continue

            logger.info(f"[CHAIN] [Edge] Scheduling Shorts for {account_name}...")
            try:
                result = await run_scheduler_dae(
                    channel_key=channel_key,
                    max_videos=max_videos,
                    dry_run=dry_run,
                )
                scheduled = len(result.get("scheduled", []))
                total_scheduled += scheduled
                logger.info(f"[CHAIN] [Edge] {account_name}: {scheduled} videos scheduled")

                if result.get("errors"):
                    for err in result["errors"]:
                        logger.warning(f"[CHAIN] [Edge] {account_name} error: {err}")
            except Exception as e:
                logger.error(f"[CHAIN] [Edge] {account_name} scheduling failed: {e}")

        logger.info("=" * 70)
        logger.info(f"[CHAIN] SHORTS SCHEDULING COMPLETE - {total_scheduled} videos scheduled")
        logger.info("=" * 70)

        # Emit breadcrumb for activity router
        try:
            telemetry = get_breadcrumb_telemetry()
            telemetry.store_breadcrumb(
                source_dae="multi_channel_coordinator",
                event_type="shorts_scheduling_complete",
                message=f"Scheduled {total_scheduled} videos across all channels",
                phase="ACTIVITY-ROUTING",
                metadata={
                    "total_scheduled": total_scheduled,
                    "chrome_channels": len(chrome_accounts),
                    "edge_channels": len(edge_accounts),
                    "max_videos_per_channel": max_videos,
                    "dry_run": dry_run,
                }
            )
            logger.info("[CHAIN] [BREADCRUMB] shorts_scheduling_complete emitted")
        except Exception as e:
            logger.warning(f"[CHAIN] Failed to emit scheduling breadcrumb: {e}")

        return total_scheduled
