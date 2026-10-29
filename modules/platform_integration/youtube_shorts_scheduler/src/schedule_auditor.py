"""
Schedule Auditor — Independent verification layer for YouTube Shorts Scheduler.

PURPOSE:
    Reads the ACTUAL scheduled state from YouTube Studio DOM and compares
    against the local tracker JSON to detect:
    - False positives: tracker says scheduled, YouTube says unlisted/private
    - Time conflicts: multiple videos at the same date+time
    - Missing entries: YouTube shows scheduled but tracker doesn't know
    - Stale tracker data: count mismatches

ARCHITECTURE:
    This is Layer 2 — independent of the scheduling layer (Layer 1).
    Layer 1: scheduler.py + schedule_tracker.py (writes schedule)
    Layer 2: schedule_auditor.py (reads + verifies schedule)

    The auditor NEVER modifies the YouTube schedule.
    It only reads and reports discrepancies.
    Optionally auto-heals the tracker JSON via ScheduleTracker.remove_video().

USAGE:
    auditor = ScheduleAuditor(channel_key="antifafm", driver=driver)
    report = auditor.run_audit()
    # report = {
    #   "conflicts": [...],
    #   "false_positives": [...],
    #   "missing_from_tracker": [...],
    #   "healthy": True/False,
    # }

WSP Compliance:
    WSP 50: Pre-action verification (reads before acting)
    WSP 80: DAE pattern (independent monitoring layer)
    WSP 22: ModLog documentation required after significant changes
"""

import logging
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .channel_config import get_channel_config
from .schedule_tracker import ScheduleTracker

logger = logging.getLogger(__name__)


class ScheduleAuditor:
    """
    Independent verification layer that reads YouTube Studio's scheduled
    state and compares against the local tracker JSON.
    """

    def __init__(
        self,
        channel_key: str,
        driver,
        storage_dir: Optional[Path] = None,
    ):
        """
        Initialize auditor.

        Args:
            channel_key: "move2japan", "undaodu", "foundups", "antifafm"
            driver: Selenium WebDriver instance (Chrome or Edge)
            storage_dir: Optional custom storage directory for tracker files
        """
        self.channel_key = channel_key.lower()
        self.config = get_channel_config(self.channel_key)
        if not self.config:
            raise ValueError(f"Unknown channel: {channel_key}")

        self.channel_id = self.config["id"]
        self.channel_name = self.config["name"]
        self.driver = driver
        self.tracker = ScheduleTracker(self.channel_id, storage_dir)

    # =========================================
    # CORE AUDIT
    # =========================================

    def run_audit(self, auto_heal: bool = False) -> Dict[str, Any]:
        """
        Run a full schedule audit.

        1. Navigate to SCHEDULED filter on YouTube Studio
        2. Scrape all scheduled video rows (video_id, date, time, title)
        3. Compare against tracker JSON
        4. Report discrepancies
        5. Optionally auto-heal tracker

        Args:
            auto_heal: If True, automatically purge false positives from tracker

        Returns:
            Audit report dict
        """
        report = {
            "channel": self.channel_name,
            "channel_id": self.channel_id,
            "audited_at": datetime.now().isoformat(),
            "youtube_scheduled": [],
            "tracker_scheduled": [],
            "conflicts": [],
            "false_positives": [],
            "missing_from_tracker": [],
            "time_collisions": [],
            "healed": [],
            "healthy": None,
            "status": "failed",
            "total_scheduled": None,
        }

        try:
            # Step 1: Read scheduled videos from YouTube Studio DOM
            from .schedule_inventory import qualified_inventory

            inventory = self._read_scheduled_inventory()
            youtube_videos = inventory["videos"]
            report["inventory"] = inventory
            report["status"] = inventory["status"]
            report["total_scheduled"] = inventory["total_scheduled"]
            report["observed_scheduled_count"] = len(youtube_videos)
            report["youtube_scheduled"] = youtube_videos
            logger.info(
                f"[AUDITOR] Observed {len(youtube_videos)} qualified scheduled slots on YouTube "
                f"for {self.channel_name}"
            )

            if not qualified_inventory(inventory, self.channel_id):
                report["status"] = inventory["status"] if inventory["status"] in {"partial", "failed"} else "failed"
                report["total_scheduled"] = None
                report["error"] = "scheduled_inventory_incomplete"
                logger.warning("[AUDITOR] Inventory %s; total unknown; absence checks and auto-heal refused", inventory["status"])
                return report
            report["healthy"] = True

            # Step 2: Read tracker data
            tracker_ids = set(self.tracker.get_all_scheduled_video_ids())
            report["tracker_scheduled_count"] = len(tracker_ids)

            youtube_ids = {v["video_id"] for v in youtube_videos if v.get("video_id")}

            # Step 3: Detect false positives (in tracker but NOT on YouTube)
            false_positives = tracker_ids - youtube_ids
            if false_positives:
                report["healthy"] = False
                for vid in false_positives:
                    entry = {"video_id": vid, "reason": "In tracker but not scheduled on YouTube"}
                    report["false_positives"].append(entry)
                    logger.warning(f"[AUDITOR] FALSE POSITIVE: {vid} (tracker says scheduled, YouTube disagrees)")

                    if auto_heal:
                        removed = self.tracker.remove_video(vid)
                        if removed:
                            report["healed"].append(vid)
                            logger.info(f"[AUDITOR] AUTO-HEALED: Purged {vid} from tracker")

            # Step 4: Detect missing from tracker (on YouTube but NOT in tracker)
            missing = youtube_ids - tracker_ids
            if missing:
                report["healthy"] = False
                for vid in missing:
                    yt_entry = next((v for v in youtube_videos if v["video_id"] == vid), {})
                    entry = {
                        "video_id": vid,
                        "youtube_date": yt_entry.get("date", "?"),
                        "youtube_time": yt_entry.get("time", "?"),
                        "reason": "On YouTube but not in tracker",
                    }
                    report["missing_from_tracker"].append(entry)
                    logger.warning(f"[AUDITOR] MISSING FROM TRACKER: {vid} (scheduled on YouTube but tracker doesn't know)")

            # Step 5: Detect time collisions (multiple videos at same date+time)
            time_map: Dict[str, List[str]] = {}  # "date @ time" -> [video_ids]
            for v in youtube_videos:
                key = f"{v.get('date', '?')} @ {v.get('time', '?')}"
                if key not in time_map:
                    time_map[key] = []
                time_map[key].append(v.get("video_id", "?"))

            for slot_key, vids in time_map.items():
                if len(vids) > 1:
                    report["healthy"] = False
                    collision = {
                        "slot": slot_key,
                        "video_ids": vids,
                        "count": len(vids),
                    }
                    report["time_collisions"].append(collision)
                    logger.warning(f"[AUDITOR] TIME COLLISION: {slot_key} has {len(vids)} videos: {vids}")

        except Exception as e:
            logger.error("[AUDITOR] Audit failed (%s)", type(e).__name__)
            report["error"] = "schedule_audit_failed"
            report["healthy"] = None
            report["status"] = "failed"

        # Log summary
        n_fp = len(report["false_positives"])
        n_miss = len(report["missing_from_tracker"])
        n_col = len(report["time_collisions"])
        n_healed = len(report["healed"])
        status = "UNKNOWN" if report["healthy"] is None else ("HEALTHY" if report["healthy"] else "ISSUES FOUND")

        logger.info(f"[AUDITOR] ╔══ AUDIT REPORT: {self.channel_name} ══╗")
        logger.info(f"[AUDITOR] ║ Status:           {status}")
        logger.info("[AUDITOR] YouTube scheduled total=%s observed=%s", report["total_scheduled"], len(report["youtube_scheduled"]))
        logger.info(f"[AUDITOR] ║ Tracker scheduled: {report.get('tracker_scheduled_count', 0):>4}")
        logger.info(f"[AUDITOR] ║ False positives:   {n_fp:>4}")
        logger.info(f"[AUDITOR] ║ Missing from trk:  {n_miss:>4}")
        logger.info(f"[AUDITOR] ║ Time collisions:   {n_col:>4}")
        if n_healed:
            logger.info(f"[AUDITOR] ║ Auto-healed:       {n_healed:>4}")
        logger.info(f"[AUDITOR] ╚{'═' * 42}╝")

        return report

    # =========================================
    # DOM SCRAPING
    # =========================================

    def _read_scheduled_inventory(self) -> Dict[str, Any]:
        """Use the existing content-list navigator and the qualified DOM owner."""
        from .content_page_scheduler import ContentPageScheduler
        from .dom_automation import YouTubeStudioDOM
        from .schedule_inventory import failed_inventory

        dom = YouTubeStudioDOM(self.driver, capture_diagnostics=False)
        if not ContentPageScheduler(self.driver, dom).navigate_to_scheduled(self.channel_key):
            return failed_inventory(self.channel_id, "navigation_failed")
        return dom.read_scheduled_inventory(self.channel_id)

    def _scrape_scheduled_videos(self) -> List[Dict[str, str]]:
        """Compatibility list: an incomplete scrape raises instead of becoming zero."""
        from .schedule_inventory import qualified_inventory

        inventory = self._read_scheduled_inventory()
        if not qualified_inventory(inventory, self.channel_id):
            raise RuntimeError("scheduled_inventory_incomplete")
        return inventory["videos"]

    def _scrape_from_current_page(self) -> List[Dict[str, str]]:
        """
        Scrape video rows from the current YouTube Studio page.

        Reads the video table rows and extracts:
        - video_id (from the edit link href)
        - title
        - visibility status text
        - scheduled date/time (from the Visibility column text)

        Returns:
            List of video info dicts
        """
        videos = []

        try:
            rows_data = self.driver.execute_script("""
                const rows = document.querySelectorAll('ytcp-video-row');
                const results = [];

                for (const row of rows) {
                    const data = {};

                    // Video ID from edit link
                    const link = row.querySelector('a[href*="/video/"]');
                    if (link) {
                        const match = link.href.match(/\\/video\\/([^/?]+)/);
                        if (match) data.video_id = match[1];
                    }

                    // Title
                    const titleEl = row.querySelector('#video-title');
                    if (titleEl) data.title = titleEl.textContent.trim();

                    // Visibility column — contains status and schedule date
                    const visCell = row.querySelector('.cell-body.tablecell-visibility');
                    if (visCell) {
                        data.visibility_text = visCell.textContent.trim();

                        // Extract "Scheduled" + date from text like "Scheduled Feb 1, 2026"
                        // or "Scheduled\\nFeb 1, 2026\\n5:00 PM"
                        const lines = visCell.innerText.split('\\n').map(l => l.trim()).filter(Boolean);
                        data.visibility_lines = lines;

                        // Parse date and time from visibility lines
                        for (const line of lines) {
                            // Date pattern: "Mon DD, YYYY" e.g., "Feb 1, 2026"
                            if (/^[A-Z][a-z]{2}\\s+\\d{1,2},\\s+\\d{4}$/.test(line)) {
                                data.date = line;
                            }
                            // Time pattern: "H:MM AM/PM" e.g., "5:00 PM"
                            if (/^\\d{1,2}:\\d{2}\\s+[AP]M$/i.test(line)) {
                                data.time = line;
                            }
                        }
                    }

                    if (data.video_id) results.push(data);
                }

                return results;
            """)

            if rows_data:
                for v in rows_data:
                    videos.append({
                        "video_id": v.get("video_id", ""),
                        "title": v.get("title", "")[:80],
                        "date": v.get("date", ""),
                        "time": v.get("time", ""),
                        "visibility_text": v.get("visibility_text", ""),
                    })

        except Exception as e:
            logger.error(f"[AUDITOR] Scrape error: {e}")

        return videos

    # =========================================
    # QUICK CHECKS (no navigation required)
    # =========================================

    def check_tracker_integrity(self) -> Dict[str, Any]:
        """
        Quick check of tracker JSON integrity without touching the browser.

        Detects:
        - Count mismatches (schedule count != video_ids count)
        - Duplicate video IDs across dates
        - Dates in the past

        Returns:
            Integrity report dict
        """
        report = {
            "channel": self.channel_name,
            "count_mismatches": [],
            "duplicate_ids": [],
            "past_dates": [],
            "healthy": True,
        }

        now = datetime.now()

        # Check count mismatches
        for date_str, count in self.tracker.schedule.items():
            ids = self.tracker.video_ids.get(date_str, [])
            if count != len(ids):
                report["healthy"] = False
                report["count_mismatches"].append({
                    "date": date_str,
                    "schedule_count": count,
                    "video_ids_count": len(ids),
                })

        # Check for duplicate IDs across dates
        all_ids = []
        for date_str, ids in self.tracker.video_ids.items():
            for vid in ids:
                if vid in all_ids:
                    report["healthy"] = False
                    report["duplicate_ids"].append({"video_id": vid, "date": date_str})
                all_ids.append(vid)

        # Check for past dates (videos that should have already published)
        for date_str in self.tracker.schedule:
            try:
                parsed = self.tracker._parse_date(date_str)
                if parsed < now and parsed != datetime.min:
                    report["past_dates"].append(date_str)
            except Exception:
                pass

        return report


# =========================================
# STANDALONE ENTRY POINT
# =========================================

def run_schedule_audit(
    channel_key: str,
    auto_heal: bool = False,
    browser: str = "chrome",
) -> Dict[str, Any]:
    """
    Run a schedule audit for a channel.

    Connects to an existing browser debug session, runs the audit,
    and returns the report.

    Args:
        channel_key: Channel to audit
        auto_heal: Auto-purge false positives from tracker
        browser: "chrome" or "edge"

    Returns:
        Audit report dict
    """
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from selenium.webdriver.edge.options import Options as EdgeOptions

    config = get_channel_config(channel_key)
    if not config:
        return {"error": f"Unknown channel: {channel_key}"}

    port = config.get("preferred_port", 9222)
    if browser == "edge":
        port = 9223

    try:
        if port == 9223:
            options = EdgeOptions()
            options.add_experimental_option("debuggerAddress", f"127.0.0.1:{port}")
            driver = webdriver.Edge(options=options)
        else:
            options = ChromeOptions()
            options.add_experimental_option("debuggerAddress", f"127.0.0.1:{port}")
            driver = webdriver.Chrome(options=options)

        auditor = ScheduleAuditor(channel_key, driver)
        report = auditor.run_audit(auto_heal=auto_heal)

        # Also run quick integrity check
        integrity = auditor.check_tracker_integrity()
        report["tracker_integrity"] = integrity

        return report

    except Exception as e:
        logger.error(f"[AUDITOR] Failed to connect: {e}")
        return {"error": str(e), "channel": channel_key}
