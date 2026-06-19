"""
YouTube Shorts Scheduler - Main Orchestrator

WSP 80 DAE pattern for automated Shorts scheduling.
Connects to Chrome (9222) or Edge (9223) debug sessions.
"""

import asyncio
import logging
import os
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.common.exceptions import WebDriverException

from .channel_config import get_channel_config, CHANNELS
from .dom_automation import YouTubeStudioDOM
from .schedule_tracker import ScheduleTracker
from .peak_window import get_peak_slots_et
from .schedule_dba import record_schedule_outcome
from .index_weave import (
    load_index_json,
    save_index_json,
    build_digital_twin_index_block,
    update_index_after_schedule,
    build_index_metadata_context,
)
from .content_generator import (
    generate_clickbait_title,
    get_standard_description,
    generate_description_with_context,
)

# Content-channel mismatch gate (WSP 97 truth signaling)
try:
    from modules.platform_integration.youtube_shorts_scheduler.skillz.gemma_content_type_classifier.executor import classify_content
    CLASSIFIER_AVAILABLE = True
except ImportError:
    CLASSIFIER_AVAILABLE = False
    classify_content = None

logger = logging.getLogger(__name__)


class YouTubeShortsScheduler:
    """
    Main orchestrator for YouTube Shorts scheduling automation.

    Supports:
    - Move2Japan (Chrome 9222)
    - UnDaoDu (Chrome 9222)
    - FoundUps (Edge 9223)
    - antifaFM (Edge 9223)

    Usage:
        scheduler = YouTubeShortsScheduler("move2japan")
        await scheduler.run_scheduling_cycle(max_videos=10)
    """

    def __init__(
        self,
        channel_key: str,
        storage_dir: Optional[Path] = None,
        dry_run: bool = False,
    ):
        """
        Initialize scheduler for a channel.

        Args:
            channel_key: "move2japan", "undaodu", "foundups", or "antifafm"
            storage_dir: Optional custom storage directory
            dry_run: If True, don't actually make changes
        """
        self.channel_key = channel_key.lower()
        self.config = get_channel_config(self.channel_key)

        if not self.config:
            raise ValueError(f"Unknown channel: {channel_key}")

        self.channel_id = self.config["id"]
        self.channel_name = self.config["name"]
        self.chrome_port = self.config["chrome_port"]
        # Canonical US-Eastern peak slots (morning/lunch/evening), env-configurable
        # via SHORTS_PEAK_SLOTS_ET. Defined ONCE in peak_window; these are ET and
        # get converted to the channel's Studio-account tz at allocation time.
        self.time_slots = get_peak_slots_et()
        # Channel Studio-account timezone (registry field). Used to convert the
        # ET peak slot to the local wall-clock the bare-time typer must enter.
        self.channel_tz = self.config.get("timezone")
        self.max_per_day = self.config["max_per_day"]
        self.dry_run = dry_run

        # Initialize tracker
        self.tracker = ScheduleTracker(self.channel_id, storage_dir)

        # Driver and DOM (initialized on connect)
        self.driver = None
        self.dom = None

        logger.info(f"[SCHEDULER] Initialized for {self.channel_name} (port {self.chrome_port})")

    # =========================================
    # OBSERVE-MODE acoustic music/talk label (SHORTS_MUSIC_LABEL_OBSERVE_PHASE1)
    # =========================================
    def _observe_audio_label_log(self, video_id: Optional[str]) -> None:
        """READ-ONLY: log the acoustic audio_label if PHASE 2 indexing wrote one.

        PHASE 2 indexing (flag YT_AUDIO_LABEL_OBSERVE) may store an acoustic
        audio_label as a SIBLING of content_category in the index artifact. This
        helper reads that artifact read-only and, if a label is present, emits a
        [MUSIC-OBSERVE] log so 012 can observe acoustic-vs-LLM agreement.

        OBSERVE CONTRACT: this method ALWAYS returns None and NEVER raises. It has
        no return value the scheduling loop can branch on, so it is structurally
        incapable of changing any scheduling decision. It only emits a log line.
        """
        if not video_id:
            return None
        try:
            observe_idx = load_index_json(channel_key=self.channel_key, video_id=video_id)
            if isinstance(observe_idx, dict):
                meta = observe_idx.get("metadata") or {}
                label = meta.get("audio_label")
                if label:
                    logger.info(
                        "[MUSIC-OBSERVE] %s audio_label=%s content_category=%s",
                        video_id,
                        label,
                        meta.get("content_category"),
                    )
        except Exception as exc:
            logger.debug(f"[SCHEDULER] [MUSIC-OBSERVE] read skipped (continuing): {exc}")
        return None

    # =========================================
    # BROWSER CONNECTION
    # =========================================

    def connect_browser(self) -> bool:
        """
        Connect to existing Chrome/Edge debug session.

        HARDENED (2026-02-22): Uses retry helpers with DevTools verification.

        Returns:
            True if connected successfully
        """
        try:
            from modules.infrastructure.dependency_launcher.src.dae_dependencies import (
                connect_chrome_with_retry,
                connect_edge_with_retry,
            )

            if self.chrome_port == 9223:
                # Edge browser for FoundUps
                logger.info("[SCHEDULER] Connecting to Edge with retry...")
                self.driver = connect_edge_with_retry(max_retries=3, retry_delay=2.0)
                if self.driver is None:
                    logger.error("[SCHEDULER] Edge connection failed after retries")
                    return False
                logger.info(f"[SCHEDULER] Connected to Edge on port {self.chrome_port} (with retry)")
            else:
                # Chrome browser for Move2Japan/UnDaoDu
                logger.info("[SCHEDULER] Connecting to Chrome with retry...")
                self.driver = connect_chrome_with_retry(max_retries=3, retry_delay=2.0)
                if self.driver is None:
                    logger.error("[SCHEDULER] Chrome connection failed after retries")
                    return False
                logger.info(f"[SCHEDULER] Connected to Chrome on port {self.chrome_port} (with retry)")

            # Initialize DOM automation layer
            self.dom = YouTubeStudioDOM(self.driver)
            return True

        except WebDriverException as e:
            logger.error(f"[SCHEDULER] Failed to connect: {e}")
            return False

    def disconnect(self):
        """Disconnect from browser (doesn't close it)."""
        if self.driver:
            try:
                # Don't quit - just disconnect
                self.driver = None
                self.dom = None
                logger.info("[SCHEDULER] Disconnected from browser")
            except Exception as e:
                logger.warning(f"[SCHEDULER] Disconnect error: {e}")

    def close(self):
        """
        Close browser and release for rotation.

        Unlike disconnect(), this actually quits the browser session
        so it can be reused by other DAEs (browser rotation).
        """
        if self.driver:
            try:
                # Actually quit the browser to release it
                self.driver.quit()
                logger.info("[SCHEDULER] Browser closed and released for rotation")
            except Exception as e:
                logger.warning(f"[SCHEDULER] Close error (browser may already be closed): {e}")
            finally:
                self.driver = None
                self.dom = None
        else:
            logger.debug("[SCHEDULER] No browser to close")

    def reconnect_browser(self, max_retries: int = 3) -> bool:
        """
        Reconnect to browser with retry logic.

        Used when WebDriver connection becomes stale or crashes.

        Args:
            max_retries: Maximum reconnection attempts

        Returns:
            True if reconnected successfully
        """
        import time

        for attempt in range(max_retries):
            logger.info(f"[SCHEDULER] Reconnection attempt {attempt + 1}/{max_retries}")

            # Clean up existing connection
            self.disconnect()
            time.sleep(1)  # Brief pause before reconnect

            # Try to connect
            if self.connect_browser():
                # Verify connection is healthy
                if self.dom and self.dom.check_driver_health(thorough=True):
                    logger.info("[SCHEDULER] Reconnection successful")
                    return True
                else:
                    logger.warning("[SCHEDULER] Reconnected but health check failed")

            time.sleep(2 * (attempt + 1))  # Exponential backoff

        logger.error(f"[SCHEDULER] Failed to reconnect after {max_retries} attempts")
        return False

    def ensure_healthy_connection(self) -> bool:
        """
        Ensure WebDriver connection is healthy, reconnect if needed.

        Returns:
            True if connection is healthy (or reconnected successfully)
        """
        if not self.driver or not self.dom:
            logger.warning("[SCHEDULER] No driver/DOM - attempting reconnect")
            return self.reconnect_browser()

        # Check health
        if not self.dom.check_driver_health(thorough=True):
            logger.warning("[SCHEDULER] Driver unhealthy - attempting reconnect")
            return self.reconnect_browser()

        return True

    # =========================================
    # SCHEDULING WORKFLOW
    # =========================================

    async def run_scheduling_cycle(
        self,
        max_videos: int = 0,
        update_metadata: bool = True,
    ) -> Dict[str, Any]:
        """
        Run a full scheduling cycle.

        1. Navigate to unlisted Shorts
        2. For each video:
           a. Update title/description if needed
           b. Schedule to next available slot
        3. Track all scheduled videos

        Args:
            max_videos: Maximum videos to process (0 = unlimited, process all)
            update_metadata: Whether to update titles/descriptions

        Returns:
            Summary dict with scheduled_count, errors, etc.
        """
        if not self.driver:
            raise RuntimeError("Not connected to browser. Call connect_browser() first.")

        # Ensure healthy connection before starting (reconnect if stale)
        if not self.ensure_healthy_connection():
            raise RuntimeError("WebDriver connection is unhealthy and reconnection failed")

        import time as _time
        cycle_start = _time.time()

        results = {
            "channel": self.channel_name,
            "channel_id": self.channel_id,
            "started_at": datetime.now().isoformat(),
            "scheduled": [],
            "errors": [],
            "skipped": [],
        }

        # Pre-cycle schedule report
        self.tracker.log_schedule_report()

        # SHORTS_SCHEDULE_INCLUDE_PRIVATE_PHASE1: resolve the visibility targets.
        # Default is UNLISTED-only. When YT_SCHEDULE_INCLUDE_PRIVATE=1 the cycle
        # ALSO makes a PRIVATE pass. Scheduling a PRIVATE video uses the
        # PUBLISH_FROM_PRIVATE schedule radio -> the video PUBLISHES PUBLIC at its
        # slot. This is an OUTWARD-FACING action, so it is DEFAULT-OFF and 012 must
        # opt in deliberately (each private schedule is logged with a
        # [PRIVATE->PUBLIC] breadcrumb below).
        visibility_targets = self._resolve_visibility_targets()
        results["visibility_targets"] = visibility_targets

        try:
            # Run the existing navigate + batch loop ONCE PER TARGET. The single
            # self.tracker is shared across passes, so the per-day cap (3), the
            # peak window/tz, and the rotation budget are shared: UNLISTED fills
            # the available slots first, then PRIVATE continues into whatever
            # remains (no per-channel budget doubling).
            for target in visibility_targets:
                aborted = await self._run_visibility_pass(
                    target=target,
                    max_videos=max_videos,
                    update_metadata=update_metadata,
                    results=results,
                )
                if aborted:
                    # Navigation/filter failure for this target — stop the cycle.
                    break

        except Exception as e:
            logger.error(f"[SCHEDULER] Cycle error: {e}")
            results["errors"].append({"error": str(e)})

        cycle_elapsed = _time.time() - cycle_start
        results["finished_at"] = datetime.now().isoformat()
        results["total_scheduled"] = len(results["scheduled"])
        results["total_errors"] = len(results["errors"])
        results["total_skipped"] = len(results["skipped"])
        results["cycle_seconds"] = round(cycle_elapsed, 1)

        # End-of-cycle report
        n_ok = results["total_scheduled"]
        n_err = results["total_errors"]
        n_skip = results["total_skipped"]
        logger.info(f"[SCHEDULER] ╔══ CYCLE COMPLETE: {self.channel_name} ══╗")
        logger.info(f"[SCHEDULER] ║ Scheduled: {n_ok:>4} videos")
        logger.info(f"[SCHEDULER] ║ Errors:    {n_err:>4}")
        logger.info(f"[SCHEDULER] ║ Skipped:   {n_skip:>4}")
        logger.info(f"[SCHEDULER] ║ Duration:  {cycle_elapsed:>7.1f}s")
        if n_ok > 0:
            avg = cycle_elapsed / n_ok
            logger.info(f"[SCHEDULER] ║ Avg/video: {avg:>7.1f}s")
            # Date spread
            dates_used = set(v["date"] for v in results["scheduled"])
            logger.info(f"[SCHEDULER] ║ Dates:     {len(dates_used):>4} unique days")
            for d in sorted(dates_used):
                vids_on_day = [v for v in results["scheduled"] if v["date"] == d]
                times = ", ".join(v["time"] for v in vids_on_day)
                logger.info(f"[SCHEDULER] ║   {d}: {times}")
        logger.info(f"[SCHEDULER] ╚{'═' * 42}╝")

        # Post-cycle schedule report (updated totals)
        self.tracker.log_schedule_report()

        # Post-cycle audit: verify scheduled state matches YouTube reality
        # Enable with YT_SCHEDULER_POST_AUDIT=true (default: false — opt-in)
        if os.getenv("YT_SCHEDULER_POST_AUDIT", "false").lower() in ("1", "true", "yes"):
            try:
                from .schedule_auditor import ScheduleAuditor
                auditor = ScheduleAuditor(self.channel_key, self.driver)
                auto_heal = os.getenv("YT_SCHEDULER_AUDIT_AUTO_HEAL", "true").lower() in ("1", "true", "yes")
                audit_report = auditor.run_audit(auto_heal=auto_heal)
                results["audit"] = {
                    "healthy": audit_report.get("healthy", False),
                    "false_positives": len(audit_report.get("false_positives", [])),
                    "time_collisions": len(audit_report.get("time_collisions", [])),
                    "healed": len(audit_report.get("healed", [])),
                }
                if not audit_report.get("healthy"):
                    logger.warning(
                        f"[SCHEDULER] Post-cycle audit found issues: "
                        f"{len(audit_report.get('false_positives', []))} false positives, "
                        f"{len(audit_report.get('time_collisions', []))} time collisions"
                    )
                    # G4: Emit breadcrumb for AI Overseer sentinel detection (Phase 3)
                    try:
                        from modules.communication.livechat.src.breadcrumb_telemetry import get_breadcrumb_telemetry
                        telemetry = get_breadcrumb_telemetry()
                        telemetry.store_breadcrumb(
                            source_dae="youtube_shorts_scheduler",
                            event_type="schedule_audit_unhealthy",
                            message=f"Schedule audit failed for {self.channel_key}",
                            phase="POST_AUDIT",
                            metadata={
                                "channel_key": self.channel_key,
                                "channel_id": self.channel_id,
                                "false_positives": len(audit_report.get("false_positives", [])),
                                "time_collisions": len(audit_report.get("time_collisions", [])),
                                "missing_from_tracker": len(audit_report.get("missing_from_tracker", [])),
                                "auto_heal": auto_heal,
                                "healed": len(audit_report.get("healed", [])),
                            },
                        )
                    except Exception as bc_err:
                        logger.debug(f"[SCHEDULER] Breadcrumb emission failed: {bc_err}")
            except Exception as e:
                logger.debug(f"[SCHEDULER] Post-cycle audit skipped: {e}")

        return results

    def _resolve_visibility_targets(self) -> List[str]:
        """Resolve which list-visibility filters the cycle should process.

        SHORTS_SCHEDULE_INCLUDE_PRIVATE_PHASE1.

        Default: ["UNLISTED"] (unchanged behaviour). When the OUTWARD-FACING flag
        YT_SCHEDULE_INCLUDE_PRIVATE is enabled (=="1"), a PRIVATE pass is appended:
        ["UNLISTED", "PRIVATE"]. UNLISTED is always processed first so it consumes
        the rotation budget before any private->public publishing occurs.

        Scheduling a PRIVATE video uses the PUBLISH_FROM_PRIVATE radio, which
        PUBLISHES it PUBLIC at the slot — hence default-OFF and deliberate opt-in.
        """
        if os.getenv("YT_SCHEDULE_INCLUDE_PRIVATE", "0") == "1":
            logger.warning(
                "[SCHEDULER] YT_SCHEDULE_INCLUDE_PRIVATE=1 — PRIVATE pass ENABLED. "
                "Scheduling a PRIVATE Short PUBLISHES it PUBLIC at its slot "
                "(PUBLISH_FROM_PRIVATE). Each one is logged [PRIVATE->PUBLIC]."
            )
            return ["UNLISTED", "PRIVATE"]
        return ["UNLISTED"]

    def _scrape_videos_for_visibility(self, target: str) -> List[Dict[str, str]]:
        """Scrape the Shorts row list under the ACTIVE visibility filter.

        SHORTS_SCHEDULE_INCLUDE_PRIVATE_PHASE1.

        UNLISTED delegates to the unchanged DOM helper
        ``self.dom.get_unlisted_videos()`` (which enforces the UNLISTED filter and
        rejects Scheduled rows). The DOM layer has no PRIVATE row-scraper (it is
        UNLISTED-hardcoded by design), so for the PRIVATE pass the scheduler scrapes
        the rows itself via the driver — mirroring the strict row scan but keyed on
        ``private`` — WITHOUT modifying the DOM/URL layer. The PRIVATE filter is
        navigated + enforced by the existing generic
        ``navigate_to_shorts_with_fallback(..., "PRIVATE")`` before this is called.
        """
        target = (target or "UNLISTED").upper()
        if target == "UNLISTED":
            return self.dom.get_unlisted_videos()

        # PRIVATE pass: scheduler-side scrape under the already-applied PRIVATE
        # filter. Pattern mirrors dom_automation.get_unlisted_videos but keyed on
        # 'private' and excludes any row that already shows a schedule.
        try:
            scraped = self.driver.execute_script(
                """
                const rows = document.querySelectorAll('ytcp-video-row');
                const out = [];
                for (const row of rows) {
                    const text = (row.textContent || '').toLowerCase();
                    const hasPrivate = /\\bprivate\\b/.test(text);
                    const hasScheduled = /\\bscheduled\\b/.test(text) || text.includes('has schedule');
                    if (!hasPrivate) continue;
                    if (hasScheduled) continue;
                    const link = row.querySelector("a[href*='/video/']");
                    if (!link) continue;
                    const href = link.getAttribute('href') || '';
                    const m = href.match(/\\/video\\/([^/?]+)/);
                    if (!m) continue;
                    out.push({
                        video_id: m[1],
                        title: (link.textContent || '').trim(),
                        href: href,
                    });
                }
                return out;
                """
            ) or []
        except Exception as exc:
            logger.error(f"[SCHEDULER] Private row scrape failed: {exc}")
            return []

        videos = [
            {
                "video_id": item.get("video_id"),
                "title": item.get("title", ""),
                "href": item.get("href", ""),
            }
            for item in scraped
            if item.get("video_id")
        ]
        logger.info(f"[SCHEDULER] Private scrape: {len(videos)} videos under PRIVATE filter")
        return videos

    async def _run_visibility_pass(
        self,
        target: str,
        max_videos: int,
        update_metadata: bool,
        results: Dict[str, Any],
    ) -> bool:
        """Run the navigate + continuous batch loop for ONE visibility target.

        SHORTS_SCHEDULE_INCLUDE_PRIVATE_PHASE1: extracted verbatim from the
        original UNLISTED-only cycle body, with the hard-coded "UNLISTED" literal
        replaced by ``target`` and the row scrape delegated to
        ``_scrape_videos_for_visibility(target)``. The per-day cap, peak window/tz,
        and rotation budget come from the shared ``self.tracker`` and are therefore
        shared across targets.

        Returns:
            True if the pass aborted on a navigation/filter failure (caller should
            stop the cycle), False otherwise.
        """
        is_private = (target or "").upper() == "PRIVATE"

        # Step 1: Navigate to the target-visibility Shorts (with fallback).
        logger.info(f"[SCHEDULER] Navigating to {target} Shorts for {self.channel_name}")
        if not self.dom.navigate_to_shorts_with_fallback(self.channel_id, target):
            logger.error(f"[SCHEDULER] Failed to navigate to {target} Shorts")
            results["errors"].append({"error": f"Navigation to {target} Shorts failed"})
            return True
        filter_state = self.dom.read_visibility_filter_state()
        logger.info(
            f"[SCHEDULER] List filter state: detected={filter_state.get('detected')} "
            f"chips={filter_state.get('chip_texts')}"
        )
        if filter_state.get("detected") == "SCHEDULED":
            logger.error(
                f"[SCHEDULER] Aborting {target} pass — Shorts list is on "
                f"Scheduled/Has schedule, not {target}"
            )
            results["errors"].append({"error": "Wrong visibility filter: SCHEDULED"})
            return True
        await asyncio.sleep(2)  # Wait for page load

        # Step 1.5: Set page size to 50 for larger batches (2026-01-28)
        self.dom.set_page_size(50)
        await asyncio.sleep(1)

        # Step 2-4: CONTINUOUS PROCESSING LOOP (2026-01-28: Added for true "until complete")
        # Process batches of videos until none remain under this filter.
        batch_num = 0
        total_processed = 0
        sync_enabled = os.getenv("YT_SCHEDULER_DO_SYNC", "false").lower() in ("1", "true", "yes")

        while True:
                batch_num += 1
                logger.info(f"[SCHEDULER] === BATCH {batch_num} ===")

                # Step 2: Get videos for this batch under the active filter.
                unlisted = self._scrape_videos_for_visibility(target)
                logger.info(f"[SCHEDULER] Found {len(unlisted)} {target} videos in batch {batch_num}")

                if not unlisted:
                    if batch_num == 1:
                        results["message"] = f"No {target} videos found"
                    else:
                        results["message"] = f"All {target} videos processed after {batch_num - 1} batches"
                    logger.info(f"[SCHEDULER] No more {target} videos - continuous processing complete")
                    break

                # Step 3: Sync existing scheduled videos (disabled by default)
                if batch_num == 1:  # Only sync on first batch
                    await self._sync_scheduled_videos()
                    if sync_enabled:
                        logger.info(f"[SCHEDULER] Returning to {target} Shorts after sync...")
                        if not self.dom.navigate_to_shorts_with_fallback(self.channel_id, target):
                            logger.warning(f"[SCHEDULER] Could not return to {target} Shorts, continuing with cached list")
                        await asyncio.sleep(2)
                        # Re-fetch after returning
                        unlisted = self._scrape_videos_for_visibility(target)

                # Step 4: Process each video in this batch
                processed = 0
                slots_exhausted = False  # 2026-01-29: Track if slots ran out (fixes infinite loop bug)
                # max_videos=0 means unlimited (process all)
                videos_to_process = unlisted if max_videos == 0 else unlisted[:max_videos]
                total_to_process = len(videos_to_process)
                logger.info(f"[SCHEDULER] Processing {total_to_process} videos (max_videos={max_videos}, batch={batch_num})")

                for video in videos_to_process:
                    if max_videos > 0 and processed >= max_videos:
                        break

                    video_id = video.get("video_id")
                    original_title = video.get("title", "")

                    # RESUME CAPABILITY: Skip already-scheduled videos
                    if video_id and self.tracker.is_video_scheduled(video_id):
                        logger.info(f"[SCHEDULER] Skipping (already scheduled): {video_id}")
                        results["skipped"].append({
                            "video_id": video_id,
                            "reason": "Already scheduled",
                        })
                        continue

                    # CONTENT-CHANNEL GATE: detect FFCPLN content on non-FFCPLN channels (WSP 97).
                    # PHASE 1 DECOUPLING: this gate is now READ-ONLY. It reads an EXISTING
                    # index artifact (produced outside the scheduler, #819) to refine the
                    # classification with transcript context. It no longer deletes the
                    # artifact or re-indexes via Gemini (no scheduler-owned indexing, no
                    # GeminiVideoAnalyzer coupling). If the artifact is absent, the gate
                    # falls back to the title-only classification result.
                    if CLASSIFIER_AVAILABLE and self.channel_key in ["undaodu", "foundups"]:
                        try:
                            classification = classify_content(title=original_title, channel=self.channel_key)
                            content_type = classification.get("content_type", "")
                            if content_type in ["ffcpln_music", "ffcpln_news"]:
                                # Title suggests FFCPLN - refine using the existing artifact (read-only).
                                logger.warning(
                                    f"[SCHEDULER] [GATE] FFCPLN classification on {self.channel_key} - checking index (read-only)"
                                )
                                existing_idx = load_index_json(channel_key=self.channel_key, video_id=video_id)
                                if isinstance(existing_idx, dict):
                                    audio = existing_idx.get("audio") or {}
                                    transcript = audio.get("transcript_summary", "")
                                    reclassification = classify_content(
                                        title=original_title,
                                        channel=self.channel_key,
                                        transcript=transcript,
                                    )
                                    new_content_type = reclassification.get("content_type", "")
                                    logger.info(f"[SCHEDULER] [GATE] Refined classification: {new_content_type}")
                                    if new_content_type in ["ffcpln_music", "ffcpln_news"]:
                                        # Still FFCPLN after reading the artifact - actually wrong channel.
                                        logger.warning(f"[SCHEDULER] [GATE] Still FFCPLN after artifact read - SKIPPING")
                                        results["skipped"].append({
                                            "video_id": video_id,
                                            "reason": f"Content mismatch confirmed: {new_content_type} on {self.channel_key}",
                                            "classification": reclassification,
                                        })
                                        continue
                                    # Reclassification passed - proceed with scheduling.
                                    logger.info(f"[SCHEDULER] [GATE] Reclassified as {new_content_type} - proceeding")
                                else:
                                    logger.debug(
                                        f"[SCHEDULER] [GATE] No index artifact for {video_id} - using title-only classification"
                                    )
                        except Exception as e:
                            logger.debug(f"[SCHEDULER] Classification gate error (continuing): {e}")

                    # OBSERVE-MODE acoustic music/talk label (SHORTS_MUSIC_LABEL_OBSERVE_PHASE1).
                    # READ-ONLY observation: emits a [MUSIC-OBSERVE] log iff PHASE 2 indexing
                    # wrote an acoustic audio_label sibling into the artifact metadata. The
                    # helper returns None ALWAYS -- it carries NO value the loop can branch on,
                    # so it is structurally incapable of changing any scheduling decision.
                    self._observe_audio_label_log(video_id)

                    import time as time_module
                    video_start = time_module.time()
                    logger.info(
                        f"[SCHEDULER] ▶ Video [{processed+1}/{total_to_process}] "
                        f"batch={batch_num} | {video_id} | {original_title[:50]}"
                    )

                    try:
                        # Get next available slot
                        slot = self.tracker.get_next_available_slot(
                            self.time_slots,
                            self.max_per_day,
                            channel_tz=self.channel_tz,
                        )

                        if not slot:
                            logger.warning("[SCHEDULER] No available slots in date range - slots exhausted")
                            results["skipped"].append({
                                "video_id": video_id,
                                "reason": "No available slots",
                            })
                            slots_exhausted = True  # 2026-01-29: Signal outer loop to exit
                            break

                        date_str, time_str = slot

                        if self.dry_run:
                            logger.info(f"[DRY RUN] Would schedule {video_id} for {date_str} at {time_str}")
                            # SHORTS_SCHEDULE_INCLUDE_PRIVATE_PHASE1: surface the
                            # outward private->public action in dry-run too.
                            if is_private:
                                logger.warning(
                                    f"[PRIVATE->PUBLIC] {video_id} scheduled to publish "
                                    f"{date_str} {time_str} (dry_run)"
                                )
                            results["scheduled"].append({
                                "video_id": video_id,
                                "date": date_str,
                                "time": time_str,
                                "dry_run": True,
                            })
                            self.tracker.increment(date_str, video_id)
                            processed += 1
                            total_processed += 1
                            continue

                        # Navigate to video edit page
                        self.dom.navigate_to_video(video_id)
                        await asyncio.sleep(1.5)

                        edit_vis = self.dom.read_edit_page_visibility()
                        if edit_vis == "scheduled":
                            logger.warning(
                                f"[SCHEDULER] SKIP {video_id}: edit page visibility is Scheduled "
                                f"(wrong Shorts filter or already published to schedule)"
                            )
                            results["skipped"].append({
                                "video_id": video_id,
                                "reason": "Already Scheduled on YouTube (not Unlisted)",
                            })
                            continue
                        # SHORTS_SCHEDULE_INCLUDE_PRIVATE_PHASE1: accept 'private' on
                        # the edit page when this is the PRIVATE pass, so a private
                        # video isn't rejected as "wrong visibility". Otherwise the
                        # guard is unchanged (unlisted/unknown only).
                        allowed_vis = ("unlisted", "unknown")
                        if is_private:
                            allowed_vis = ("unlisted", "unknown", "private")
                        if edit_vis not in allowed_vis:
                            expected = "Private" if is_private else "Unlisted"
                            logger.warning(
                                f"[SCHEDULER] SKIP {video_id}: visibility={edit_vis} (expected {expected})"
                            )
                            results["skipped"].append({
                                "video_id": video_id,
                                "reason": f"Wrong visibility on edit page: {edit_vis}",
                            })
                            continue

                        # Update metadata if requested
                        if update_metadata:
                            await self._update_video_metadata(
                                video_id=video_id,
                                original_title=original_title,
                                date_str=date_str,
                                time_str=time_str,
                            )

                        # Schedule the video
                        success = self.dom.schedule_video(date_str, time_str)

                        if success:
                            self.tracker.increment(date_str, video_id)

                            # SHORTS_SCHEDULE_INCLUDE_PRIVATE_PHASE1: per-private-video
                            # OUTWARD-FACING breadcrumb. Scheduling a PRIVATE Short via
                            # PUBLISH_FROM_PRIVATE PUBLISHES it PUBLIC at the slot, so 012
                            # gets one clear log line per private->public action to review.
                            if is_private:
                                logger.warning(
                                    f"[PRIVATE->PUBLIC] {video_id} scheduled to publish "
                                    f"{date_str} {time_str}"
                                )

                            # Update local index JSON with scheduling + description sync (best-effort)
                            try:
                                idx = load_index_json(channel_key=self.channel_key, video_id=video_id)
                                if isinstance(idx, dict):
                                    block = build_digital_twin_index_block(
                                        channel_key=self.channel_key,
                                        video_id=video_id,
                                        index_json=idx,
                                    )
                                    idx2 = update_index_after_schedule(
                                        index_json=idx,
                                        channel_key=self.channel_key,
                                        video_id=video_id,
                                        date_str=date_str,
                                        time_str=time_str,
                                        scheduled_by="0102",
                                        description_index_block=block,
                                    )
                                    save_index_json(channel_key=self.channel_key, video_id=video_id, data=idx2)
                            except Exception as exc:
                                logger.debug("[SCHEDULER] Index JSON update skipped: %s", exc)

                            # Record into DBA (PatternMemory) for 0102 recall.
                            record_schedule_outcome(
                                channel_id=self.channel_id,
                                video_id=video_id,
                                date_str=date_str,
                                time_str=time_str,
                                mode="schedule",
                                success=True,
                                agent="selenium",
                                details={"channel_key": self.channel_key},
                            )
                            video_elapsed = time_module.time() - video_start
                            n_done = len(results["scheduled"]) + 1
                            results["scheduled"].append({
                                "video_id": video_id,
                                "date": date_str,
                                "time": time_str,
                                "elapsed_sec": round(video_elapsed, 1),
                            })
                            logger.info(
                                f"[SCHEDULER] ✅ #{n_done} SCHEDULED: {video_id} → "
                                f"{date_str} @ {time_str} ({video_elapsed:.1f}s)"
                            )
                        else:
                            record_schedule_outcome(
                                channel_id=self.channel_id,
                                video_id=video_id,
                                date_str=date_str,
                                time_str=time_str,
                                mode="schedule",
                                success=False,
                                agent="selenium",
                                details={"channel_key": self.channel_key, "error": "Schedule failed"},
                            )
                            results["errors"].append({
                                "video_id": video_id,
                                "error": "Schedule failed",
                            })

                        processed += 1
                        total_processed += 1

                        # Human-like delay between videos
                        await asyncio.sleep(self.dom.human_delay(3.0, 1.0))

                    except Exception as e:
                        logger.error(f"[SCHEDULER] Error processing {video_id}: {e}")
                        results["errors"].append({
                            "video_id": video_id,
                            "error": str(e),
                        })

                # End of batch - navigate back to unlisted list for next batch (2026-01-28)
                logger.info(f"[SCHEDULER] Batch {batch_num} complete: {processed} videos processed")

                # 2026-01-31: Detect stale-unlisted videos (tracker says scheduled, YouTube says unlisted).
                # If ALL videos in a batch were skipped as "already scheduled" but YouTube still
                # shows them as unlisted, the prior scheduling action failed silently.
                # FIX: Purge false-positive IDs from tracker so the NEXT batch retries them.
                # Safety: only do this ONCE per cycle to prevent infinite purge-retry loops.
                batch_all_skipped = (processed == 0 and total_to_process > 0)
                if batch_all_skipped:
                    stale_ids = [
                        v.get("video_id") for v in videos_to_process
                        if v.get("video_id") and self.tracker.is_video_scheduled(v["video_id"])
                    ]
                    if stale_ids and not getattr(self, '_stale_purged', False):
                        logger.warning(
                            f"[SCHEDULER] All {total_to_process} videos in batch {batch_num} "
                            f"were already in tracker but STILL unlisted on YouTube — "
                            f"prior scheduling failed. Purging {len(stale_ids)} false positives "
                            f"from tracker: {stale_ids}"
                        )
                        # Purge each stale ID from the tracker so next iteration retries them
                        for stale_id in stale_ids:
                            self.tracker.remove_video(stale_id)
                        # Remove skipped entries for these IDs so they're re-processed
                        results["skipped"] = [
                            s for s in results["skipped"]
                            if s.get("video_id") not in stale_ids
                        ]
                        self._stale_purged = True  # One purge per cycle — prevent infinite loop
                        # DON'T break — let the loop retry these videos in the next batch
                        logger.info("[SCHEDULER] Tracker purged — retrying stale videos in next batch...")
                        # Navigate back so next iteration re-fetches
                    elif stale_ids and getattr(self, '_stale_purged', False):
                        # Already purged once this cycle, still stuck — break to avoid infinite loop
                        logger.error(
                            f"[SCHEDULER] Stale videos STILL failing after purge+retry: {stale_ids}. "
                            f"Breaking to prevent infinite loop."
                        )
                        results["message"] = (
                            f"Stopped: {len(stale_ids)} videos failed scheduling twice — "
                            f"possible DOM/YouTube issue"
                        )
                        break
                    else:
                        # All skipped but none are in tracker (shouldn't happen) — break safely
                        logger.warning(
                            f"[SCHEDULER] Batch {batch_num}: 0 processed, {total_to_process} videos, "
                            f"no stale IDs found — breaking"
                        )
                        break

                # 2026-01-29: Exit outer loop if slots exhausted (fixes infinite loop bug)
                if slots_exhausted:
                    results["message"] = f"All scheduling slots filled after {batch_num} batches ({total_processed} videos scheduled)"
                    logger.info(f"[SCHEDULER] Slots exhausted - stopping continuous processing")
                    break

                # If max_videos limit reached, stop
                if max_videos > 0 and total_processed >= max_videos:
                    logger.info(f"[SCHEDULER] Reached max_videos limit ({max_videos}), stopping")
                    break

                # Navigate back to the target-visibility Shorts list for next batch
                logger.info(f"[SCHEDULER] Navigating back to {target} Shorts for next batch...")
                if not self.dom.navigate_to_shorts_with_fallback(self.channel_id, target):
                    logger.warning("[SCHEDULER] Could not navigate back, attempting back button...")
                    self.dom.click_back_to_shorts_list()
                await asyncio.sleep(2)
                # Loop continues to get next batch

        # Pass completed normally (not aborted).
        return False

    async def _sync_scheduled_videos(self):
        """Sync tracker with actual YouTube scheduled videos.

        NOTE: "Scheduled" isn't a filterable visibility option in YouTube Studio.
        The local tracker with persistence is sufficient for resume capability.
        This sync is now opt-in only (default skip) since it was causing errors.

        Can be enabled with YT_SCHEDULER_DO_SYNC=true if SCHEDULED filter becomes available.
        """
        import os

        # Sync is disabled by default - "Scheduled" isn't a real filter option
        # Local tracker persistence is sufficient for resume capability
        if os.getenv("YT_SCHEDULER_DO_SYNC", "false").lower() not in ("1", "true", "yes"):
            logger.debug("[SCHEDULER] Sync skipped (local tracker sufficient for resume)")
            return

        try:
            # Quick timeout for sync navigation - don't block main scheduling
            logger.info("[SCHEDULER] Syncing with YouTube schedule (experimental)...")

            # Navigate to scheduled filter (with fallback for robustness)
            if not self.dom.navigate_to_shorts_with_fallback(self.channel_id, "SCHEDULED"):
                logger.debug("[SCHEDULER] SCHEDULED filter not available, using local tracker")
                return
            await asyncio.sleep(2)

            # Get all scheduled videos (paginate if needed)
            all_scheduled = []
            while True:
                scheduled = self.dom.get_scheduled_videos()
                all_scheduled.extend(scheduled)

                if self.dom.has_next_page():
                    self.dom.click_next_page()
                    await asyncio.sleep(1)
                else:
                    break

            # Sync to tracker
            self.tracker.sync_from_youtube(all_scheduled)
            logger.info(f"[SCHEDULER] Synced {len(all_scheduled)} scheduled videos")

        except Exception as e:
            logger.debug(f"[SCHEDULER] Sync skipped: {e}")

    async def _update_video_metadata(
        self,
        *,
        video_id: str,
        original_title: str,
        date_str: str,
        time_str: str,
    ):
        """Update video title and description (optionally weave index).

        CHANNEL-AWARE (2026-02-22):
        - FFCPLN channels (move2japan, antifafm): Generate clickbait titles
        - Non-FFCPLN channels (foundups, undaodu): PRESERVE original title
        """
        try:
            # Get description template for this channel
            description_template = self.config.get("description_template", "ffcpln")

            # CHANNEL-AWARE TITLE HANDLING
            # FFCPLN channels: Generate clickbait titles (anti-fascist music promo)
            # Non-FFCPLN channels: Generate channel-appropriate titles (don't just preserve bad titles)

            def _is_bad_title(title: str) -> bool:
                """Check if title is just a timestamp or placeholder."""
                if not title:
                    return True
                title = title.strip()
                # Match timestamp patterns like "0:50", "1:23", "12:34"
                import re
                if re.match(r"^\d{1,2}:\d{2}$", title):
                    return True
                # Match "Short #abc123" placeholder
                if title.lower().startswith("short #"):
                    return True
                # Too short to be meaningful
                if len(title) < 5:
                    return True
                return False

            if description_template == "ffcpln":
                # FFCPLN: Use clickbait title generation
                new_title = generate_clickbait_title(original_title=original_title)
                logger.info(f"[SCHEDULER] [FFCPLN] Generated clickbait title for {self.channel_key}")
            elif description_template == "foundups":
                # FOUNDUPS: Startup/pAVS/OpenClaw content - distinct branding
                if _is_bad_title(original_title):
                    import random
                    foundups_titles = [
                        "🚀 Building the Future with AI Agents #FoundUps #pAVS",
                        "💡 pAVS: Peer-to-Peer Autonomous Ventures #FoundUps",
                        "⚡ OpenClaw: Where AI Meets Entrepreneurship #FoundUps",
                        "🔥 Startup Wisdom in 60 Seconds #FoundUps #pAVS",
                        "🧠 AI + Humans = Better Startups #FoundUps #OpenClaw",
                        "🎯 The Future of Work is Autonomous #FoundUps #pAVS",
                        "✨ Innovation Never Sleeps #FoundUps #Startup #AI",
                        "🌟 From Idea to Launch with AI #FoundUps #pAVS",
                    ]
                    new_title = random.choice(foundups_titles)
                    logger.info(f"[SCHEDULER] [FOUNDUPS] Generated title (original was: '{original_title}')")
                else:
                    new_title = original_title.strip()
                    if "#" in new_title:
                        new_title = new_title.split("#")[0].strip()
                    new_title = f"{new_title} #FoundUps #pAVS"
                    logger.info(f"[SCHEDULER] [FOUNDUPS] Enhanced title for {self.channel_key}")
            elif description_template == "undaodu":
                # UNDAODU: Mindfulness/Education/Spirituality content - distinct branding
                if _is_bad_title(original_title):
                    import random
                    undaodu_titles = [
                        "🧘 Find Your Center Today #UnDaoDu #Mindfulness",
                        "☯️ Wu Wei: The Art of Non-Doing #UnDaoDu #Zen",
                        "🌸 A Moment of Peace #UnDaoDu #Meditation",
                        "✨ Breathe. Be. Become. #UnDaoDu #Mindful",
                        "🙏 Ancient Wisdom for Modern Times #UnDaoDu",
                        "💫 The Path to Inner Balance #UnDaoDu #Zen",
                        "🌿 Mindful Moments #UnDaoDu #Meditation #Peace",
                        "☮️ Finding Calm in Chaos #UnDaoDu #Mindfulness",
                    ]
                    new_title = random.choice(undaodu_titles)
                    logger.info(f"[SCHEDULER] [UNDAODU] Generated title (original was: '{original_title}')")
                else:
                    new_title = original_title.strip()
                    if "#" in new_title:
                        new_title = new_title.split("#")[0].strip()
                    new_title = f"{new_title} #UnDaoDu #Mindfulness"
                    logger.info(f"[SCHEDULER] [UNDAODU] Enhanced title for {self.channel_key}")
            else:
                # Other channels: Just clean up
                new_title = original_title.strip() if original_title else f"Short #{video_id[:8]}"
                if "#" in new_title:
                    new_title = new_title.split("#")[0].strip()
                logger.info(f"[SCHEDULER] [{description_template.upper()}] Preserved title for {self.channel_key}")

            # CHANNEL-AWARE DESCRIPTION HANDLING
            # FFCPLN: Replace with promotional description
            # Non-FFCPLN: READ original description, APPEND template as footer
            template_description = get_standard_description(description_template)

            if description_template == "ffcpln":
                # FFCPLN: Use template directly (replace original)
                base_description = template_description
                new_description = base_description
                logger.info(f"[SCHEDULER] [FFCPLN] Using promotional description")
            else:
                # NON-FFCPLN: Read original description and PRESERVE it
                original_description = None
                try:
                    original_description = self.dom.get_current_description()
                    if original_description:
                        logger.info(f"[SCHEDULER] [{description_template.upper()}] Read original: {original_description[:50]}...")
                except Exception as read_err:
                    logger.debug(f"[SCHEDULER] Could not read original description: {read_err}")

                if original_description and original_description.strip():
                    # ENHANCE: Original + divider + template footer
                    base_description = f"""{original_description.strip()}

---

{template_description}"""
                    logger.info(f"[SCHEDULER] [{description_template.upper()}] Enhanced description (preserved original)")
                else:
                    # No original - use template as base
                    base_description = template_description
                    logger.info(f"[SCHEDULER] [{description_template.upper()}] No original found, using template")

                new_description = base_description

            # Optional: weave Digital Twin index into description.
            # Default ON; disable with YT_SCHEDULER_INDEX_WEAVE_ENABLED=false
            #
            # PHASE 1 DECOUPLING (read-for-context only):
            # The scheduler is a READ-ONLY CONSUMER of the video index artifact
            # (produced OUTSIDE the scheduler by the Studio Ask / video_indexer
            # SKILLz action, #819). It no longer OWNS/creates the artifact here:
            # ensure_index_json / GeminiVideoAnalyzer have been removed from this
            # read path. If the artifact is ABSENT, build_index_metadata_context
            # returns None and we SKIP enhancement (keep base_description /
            # original title) -- we do NOT "index now".
            index_context = "disabled"
            if os.getenv("YT_SCHEDULER_INDEX_WEAVE_ENABLED", "true").lower() in ("1", "true", "yes"):
                inform_title = os.getenv(
                    "YT_SCHEDULER_INDEX_INFORM_TITLE", "false"
                ).lower() in ("1", "true", "yes")
                enhance_description = os.getenv(
                    "YT_SCHEDULER_INDEX_ENHANCE_DESCRIPTION", "true"
                ).lower() in ("1", "true", "yes")

                ctx = build_index_metadata_context(
                    channel_key=self.channel_key,
                    video_id=video_id,
                    original_title=original_title,
                    base_description=base_description,
                    inform_title=inform_title,
                    enhance_description=enhance_description,
                )
                if ctx is not None:
                    # Artifact present -> apply woven title/description.
                    index_context = "present"
                    new_title = ctx.new_title
                    new_description = ctx.new_description
                else:
                    # Artifact absent -> skip enhancement (NOT index now).
                    index_context = "missing"

            # Behaviour-neutral observability: which index-context branch ran
            # (no response body, no transcript, no secrets).
            logger.info("[SCHEDULER] index_context=%s for %s", index_context, video_id)

            # Update via DOM
            self.dom.edit_title(new_title)
            await asyncio.sleep(0.5)

            self.dom.edit_description(new_description)
            await asyncio.sleep(0.5)

            logger.info(f"[SCHEDULER] Updated metadata: {new_title[:50]}...")

        except Exception as e:
            logger.warning(f"[SCHEDULER] Metadata update failed: {e}")

    # =========================================
    # UTILITY METHODS
    # =========================================

    def get_schedule_summary(self) -> Dict:
        """Get current schedule summary."""
        return self.tracker.get_summary()

    async def preview_slots(self, count: int = 10) -> List[Dict]:
        """
        Preview next available slots without scheduling.

        Args:
            count: Number of slots to preview

        Returns:
            List of {date, time, slot_number} dicts
        """
        slots = []
        temp_tracker = ScheduleTracker(self.channel_id)

        for i in range(count):
            slot = temp_tracker.get_next_available_slot(
                self.time_slots,
                self.max_per_day,
                channel_tz=self.channel_tz,
            )
            if slot:
                date_str, time_str = slot
                slots.append({
                    "date": date_str,
                    "time": time_str,
                    "slot_number": i + 1,
                })
                temp_tracker.increment(date_str)
            else:
                break

        return slots

    # =========================================
    # INDEXING-ONLY MODE (Occam's Razor)
    # =========================================

    async def run_indexing_cycle(
        self,
        max_videos: int = 50,
        video_type: str = "all",  # "shorts", "videos", "all"
        sort_oldest: bool = True,
    ) -> Dict[str, Any]:
        """
        Run a READ-ONLY artifact/context VALIDATION pass (no live YouTube mutation).

        DEPRECATED / READ-ONLY (Phase 1 decoupling): historically this method wove
        metadata and called self.dom.edit_title / edit_description / save_video,
        which silently mutated production metadata under the guise of "indexing".
        That coupling is removed. The scheduler is a READ-ONLY CONSUMER of the
        video index artifact (produced OUTSIDE the scheduler by the Studio Ask /
        video_indexer SKILLz action, #819). The scheduler does NOT create/refresh
        the artifact and does NOT write live metadata here.

        This method now ONLY:
        - Navigates to the content list and the video edit page (read navigation).
        - Calls the PURE build_index_metadata_context() to confirm whether an index
          artifact is present and to compute the would-be context (no DOM, no write).
        - Records presence/absence per video in the results.

        It MUST NOT call self.dom.edit_title / edit_description / schedule_video /
        save_video. The live metadata WRITE happens ONLY on the explicit
        scheduling/publish path (run_scheduling_cycle).

        Args:
            max_videos: Maximum videos to validate
            video_type: "shorts", "videos", or "all"
            sort_oldest: If True, sort by oldest first

        Returns:
            Summary dict with indexed_count (artifact-present count), errors, etc.
        """
        if not self.driver:
            raise RuntimeError("Not connected to browser. Call connect_browser() first.")

        # Ensure healthy connection before starting (reconnect if stale)
        if not self.ensure_healthy_connection():
            raise RuntimeError("WebDriver connection is unhealthy and reconnection failed")

        results = {
            "channel": self.channel_name,
            "mode": "index_only",
            "started_at": datetime.now().isoformat(),
            "indexed": [],
            "errors": [],
            "skipped": [],
        }

        try:
            # Step 1: Navigate to channel videos (Content page)
            logger.info(f"[INDEXER] Navigating to {video_type} for {self.channel_name}")

            # Use /videos/upload for all videos, /videos/short for shorts
            if video_type == "shorts":
                content_url = f"https://studio.youtube.com/channel/{self.channel_id}/videos/short"
            else:
                content_url = f"https://studio.youtube.com/channel/{self.channel_id}/videos/upload"

            self.driver.get(content_url)
            await asyncio.sleep(3)

            # Step 2: Sort by oldest if requested
            if sort_oldest:
                logger.info("[INDEXER] Sorting by oldest first...")
                try:
                    sorted_ok = self.driver.execute_script("""
                        const sortButtons = document.querySelectorAll(
                            'ytcp-dropdown-trigger, button[aria-label*="Sort"], #sort-menu-button'
                        );
                        for (const btn of sortButtons) {
                            if (btn.textContent.toLowerCase().includes('date') ||
                                btn.getAttribute('aria-label')?.toLowerCase().includes('sort')) {
                                btn.click();
                                return 'clicked';
                            }
                        }
                        return 'not_found';
                    """)
                    if sorted_ok == 'clicked':
                        await asyncio.sleep(1)
                        self.driver.execute_script("""
                            const items = document.querySelectorAll('tp-yt-paper-item, ytcp-text-menu-item');
                            for (const item of items) {
                                if (item.textContent.toLowerCase().includes('oldest')) {
                                    item.click();
                                    return true;
                                }
                            }
                            return false;
                        """)
                        await asyncio.sleep(2)
                        logger.info("[INDEXER] ✓ Sorted by oldest")
                except Exception as e:
                    logger.warning(f"[INDEXER] Sort failed (using default): {e}")

            # Step 3: Get video list
            videos = self.dom.get_unlisted_videos() if video_type == "shorts" else self._get_all_videos()
            logger.info(f"[INDEXER] Found {len(videos)} videos to index")

            if not videos:
                results["message"] = "No videos found"
                return results

            # Step 4: Process each video (index only, NO scheduling)
            processed = 0
            for video in videos[:max_videos]:
                if processed >= max_videos:
                    break

                video_id = video.get("video_id")
                original_title = video.get("title", "")

                logger.info(f"[INDEXER] Processing: {video_id} - {original_title[:40]}...")

                try:
                    if self.dry_run:
                        logger.info(f"[DRY RUN] Would validate index for {video_id}")
                        results["indexed"].append({"video_id": video_id, "dry_run": True})
                        processed += 1
                        continue

                    # Navigate to video edit page (read navigation only).
                    self.dom.navigate_to_video(video_id)
                    await asyncio.sleep(1.5)

                    # READ-ONLY: confirm whether an index artifact exists for this
                    # video and compute the would-be context, WITHOUT touching the DOM
                    # (no edit_title/edit_description) and WITHOUT creating/refreshing
                    # the artifact (no ensure_index_json / Gemini / save_video).
                    description_template = self.config.get("description_template", "ffcpln")
                    base_description = get_standard_description(description_template)
                    ctx = build_index_metadata_context(
                        channel_key=self.channel_key,
                        video_id=video_id,
                        original_title=original_title,
                        base_description=base_description,
                        inform_title=False,
                        enhance_description=True,
                    )

                    if ctx is not None:
                        results["indexed"].append({
                            "video_id": video_id,
                            "title": original_title[:50],
                            "artifact_present": True,
                        })
                        logger.info(f"[INDEXER] Artifact present (read-only validated): {video_id}")
                    else:
                        # Artifact absent -> skip enhancement (NOT index now). No mutation.
                        results["skipped"].append({
                            "video_id": video_id,
                            "reason": "No index artifact (read-only validation; not indexing now)",
                        })
                        logger.info(f"[INDEXER] No artifact for {video_id} - skipped (read-only)")

                    processed += 1

                    # Return to list for next video (read navigation only).
                    self.driver.get(content_url)
                    await asyncio.sleep(2)

                except Exception as e:
                    logger.error(f"[INDEXER] Error processing {video_id}: {e}")
                    results["errors"].append({"video_id": video_id, "error": str(e)})

            results["indexed_count"] = len(results["indexed"])
            results["error_count"] = len(results["errors"])
            results["completed_at"] = datetime.now().isoformat()

        except Exception as e:
            logger.error(f"[INDEXER] Cycle failed: {e}")
            results["fatal_error"] = str(e)

        return results

    def _get_all_videos(self) -> List[Dict]:
        """Get all videos from current content page (not just unlisted)."""
        videos = []
        try:
            rows = self.driver.find_elements("css selector", "ytcp-video-row")
            for row in rows:
                try:
                    link = row.find_element("css selector", "a[href*='/video/']")
                    href = link.get_attribute("href") or ""
                    title_el = row.find_element("css selector", "#video-title")
                    title = title_el.text if title_el else ""

                    import re
                    match = re.search(r'/video/([^/?]+)', href)
                    if match:
                        videos.append({
                            "video_id": match.group(1),
                            "title": title,
                        })
                except Exception:
                    continue
        except Exception as e:
            logger.warning(f"[INDEXER] Failed to get videos: {e}")
        return videos


# =========================================
# DAE ENTRY POINT
# =========================================

async def run_scheduler_dae(
    channel_key: str,
    max_videos: int = 0,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    DAE entry point for YouTube Shorts scheduling.

    Args:
        channel_key: "move2japan", "undaodu", "foundups", or "antifafm"
        max_videos: Maximum videos to schedule (0 = unlimited)
        dry_run: Preview mode without actual changes

    Returns:
        Scheduling results dict
    """
    # Phase -2: Ensure Chrome/Edge is running (same as comment engagement)
    try:
        from modules.infrastructure.dependency_launcher.src.dae_dependencies import ensure_dependencies
        deps = await ensure_dependencies(require_lm_studio=False)
        if not deps.get('chrome') and not deps.get('edge'):
            logger.error("[SCHEDULER] Chrome/Edge not available after dependency check")
            return {
                "error": "Browser dependencies not available",
                "channel": channel_key,
            }
    except Exception as e:
        logger.warning(f"[SCHEDULER] Dependency launcher not available: {e}")
        # Continue anyway - might already be running

    scheduler = YouTubeShortsScheduler(channel_key, dry_run=dry_run)

    if not scheduler.connect_browser():
        return {
            "error": f"Failed to connect to browser for {channel_key}",
            "channel": channel_key,
        }

    try:
        results = await scheduler.run_scheduling_cycle(max_videos=max_videos)
        return results
    finally:
        # Use close() to actually quit browser and release for rotation
        scheduler.close()



async def run_indexer_dae(
    channel_key: str,
    max_videos: int = 50,
    video_type: str = "all",  # "shorts", "videos", "all"
    sort_oldest: bool = True,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    DAE entry point for a READ-ONLY artifact/context VALIDATION pass (Phase 1 decoupling).

    This delegates to run_indexing_cycle, which is a READ-ONLY CONSUMER of the
    video-index artifact produced OUTSIDE the scheduler (Studio Ask /
    video_indexer SKILLz action, #819). It does NOT write live metadata, does
    NOT weave into the live description, and does NOT schedule. Live metadata
    writes happen ONLY on the explicit scheduling path
    (run_scheduler_dae / run_scheduling_cycle).

    Args:
        channel_key: "move2japan", "undaodu", "foundups", or "antifafm"
        max_videos: Maximum videos to validate
        video_type: "shorts", "videos", or "all"
        sort_oldest: If True, process oldest videos first
        dry_run: Preview mode. Indexing makes no live changes regardless of
            this flag (it is read-only); the flag is passed through for parity
            with the scheduling path.

    Returns:
        Indexing results dict

    WSP Compliance:
        WSP 60: Memory artifacts in memory/video_index/{channel}/
        WSP 73: The Digital Twin block is applied on the explicit scheduling
            path (run_scheduling_cycle), NOT during indexing; indexing only
            reads/validates the artifact and never writes it to live metadata.
        WSP 80: DAE pattern for background indexing
    """
    scheduler = YouTubeShortsScheduler(channel_key, dry_run=dry_run)

    if not scheduler.connect_browser():
        return {
            "error": f"Failed to connect to browser for {channel_key}",
            "channel": channel_key,
        }

    try:
        results = await scheduler.run_indexing_cycle(
            max_videos=max_videos,
            video_type=video_type,
            sort_oldest=sort_oldest,
        )
        return results
    finally:
        # Use close() to actually quit browser and release for rotation
        scheduler.close()

# =========================================
# CLI INTERFACE
# =========================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="YouTube Shorts Scheduler")
    parser.add_argument(
        "channel",
        choices=["move2japan", "undaodu", "foundups", "antifafm"],
        help="Channel to schedule for",
    )
    parser.add_argument(
        "--max",
        type=int,
        default=0,
        help="Maximum videos to schedule (0 = unlimited, process all)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview mode without changes",
    )
    parser.add_argument(
        "--preview-slots",
        type=int,
        default=0,
        help="Preview N available slots",
    )

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    if args.preview_slots > 0:
        # Preview mode
        scheduler = YouTubeShortsScheduler(args.channel, dry_run=True)
        slots = asyncio.run(scheduler.preview_slots(args.preview_slots))
        print(f"\nNext {len(slots)} available slots for {args.channel}:")
        for slot in slots:
            print(f"  {slot['slot_number']}. {slot['date']} at {slot['time']}")
    else:
        # Run scheduling
        results = asyncio.run(run_scheduler_dae(
            args.channel,
            max_videos=args.max,
            dry_run=args.dry_run,
        ))

        print(f"\n=== Scheduling Results for {results.get('channel', args.channel)} ===")
        print(f"Scheduled: {results.get('total_scheduled', 0)}")
        print(f"Errors: {results.get('total_errors', 0)}")

        if results.get("scheduled"):
            print("\nScheduled videos:")
            for v in results["scheduled"]:
                dry = " [DRY RUN]" if v.get("dry_run") else ""
                print(f"  - {v['video_id']}: {v['date']} at {v['time']}{dry}")

        if results.get("errors"):
            print("\nErrors:")
            for e in results["errors"]:
                print(f"  - {e}")
