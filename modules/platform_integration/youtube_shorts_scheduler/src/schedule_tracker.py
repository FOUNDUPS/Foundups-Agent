"""
Schedule Tracker for YouTube Shorts Scheduler

Persistent state management for tracking scheduled videos per date.
"""

import json
import logging
import random
from pathlib import Path
from typing import Dict, Optional, Tuple, List
from datetime import datetime, timedelta

# Pure ET-peak -> channel-account-tz conversion (DST-aware). The scheduler types
# a bare time that Studio interprets in the account's own tz, so an ET target
# must be converted to the channel-local wall-clock before typing.
from modules.platform_integration.youtube_shorts_scheduler.src.peak_window import (
    convert_et_to_channel_tz,
)

logger = logging.getLogger(__name__)

# Default storage location
TRACKER_DIR = Path(__file__).parent.parent / "memory"

# Authoritative per-channel daily cap on scheduled shorts.
# Belt-and-suspenders: the allocator clamps to this value even if a caller
# passes a larger max_per_day (e.g. a stale registry/config value of 8).
# Lowering this is the single load-bearing knob to stop over-scheduling.
HARD_CAP_PER_DAY = 3

# Time jitter: max number of 15-minute steps to shift from base time
# e.g. MAX_JITTER_STEPS=2 means ±30 min (±2 steps x 15 min)
MAX_JITTER_STEPS = 2


def _add_time_jitter(base_time: str, max_steps: int = MAX_JITTER_STEPS) -> str:
    """
    Add random jitter to a base time slot, snapped to :15 intervals.

    YouTube Studio only accepts times on 15-minute boundaries (:00, :15, :30, :45).
    This function shifts the base time by a random number of 15-minute steps.

    Example: base "3:00 PM" with max_steps=2 can produce:
      2:30 PM, 2:45 PM, 3:00 PM, 3:15 PM, or 3:30 PM

    Args:
        base_time: Time string like "5:00 AM", "11:00 AM", "5:00 PM"
        max_steps: Max 15-minute steps in either direction (default 2 = ±30 min)

    Returns:
        Jittered time string snapped to :15, e.g. "5:15 AM", "2:45 PM"
    """
    try:
        # Parse base time
        parsed = datetime.strptime(base_time.strip(), "%I:%M %p")

        # Pick a random number of 15-minute steps
        jitter_steps = random.randint(-max_steps, max_steps)
        jitter_minutes = jitter_steps * 15
        jittered = parsed + timedelta(minutes=jitter_minutes)

        # Format back — strip leading zero from hour for natural look
        # e.g. "5:15 AM" not "05:15 AM"
        hour = jittered.hour % 12 or 12
        minute = jittered.minute
        period = "AM" if jittered.hour < 12 else "PM"

        result = f"{hour}:{minute:02d} {period}"
        logger.info(f"[TRACKER] Time jitter: {base_time} -> {result} ({jitter_steps:+d} steps, {jitter_minutes:+d}min)")
        return result
    except (ValueError, TypeError) as e:
        logger.warning(f"[TRACKER] Time jitter parse error for '{base_time}': {e}, using as-is")
        return base_time


class ScheduleTracker:
    """
    Tracks scheduled videos per date with JSON persistence.

    Implements smart slot allocation:
    - Max 3 videos per day
    - Time slots separated by ~6 hours
    - Prioritizes empty dates over partially filled
    """

    def __init__(self, channel_id: str, storage_dir: Optional[Path] = None):
        """
        Initialize tracker for a channel.

        Args:
            channel_id: YouTube channel ID
            storage_dir: Optional custom storage directory
        """
        self.channel_id = channel_id
        self.storage_dir = storage_dir or TRACKER_DIR
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        self.tracker_file = self.storage_dir / f"schedule_{channel_id}.json"
        self.schedule: Dict[str, int] = {}  # {date_str: count}
        self.video_ids: Dict[str, List[str]] = {}  # {date_str: [video_ids]}

        self._load()

    def _load(self):
        """Load schedule from JSON file."""
        if self.tracker_file.exists():
            try:
                with open(self.tracker_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.schedule = data.get("schedule", {})
                    self.video_ids = data.get("video_ids", {})
                    logger.info(f"[TRACKER] Loaded {len(self.schedule)} dates for {self.channel_id}")
            except Exception as e:
                logger.error(f"[TRACKER] Error loading: {e}")
                self.schedule = {}
                self.video_ids = {}
        else:
            logger.info(f"[TRACKER] New tracker for {self.channel_id}")

    def save(self):
        """Persist schedule to JSON file."""
        try:
            data = {
                "channel_id": self.channel_id,
                "last_updated": datetime.now().isoformat(),
                "schedule": self.schedule,
                "video_ids": self.video_ids,
            }
            with open(self.tracker_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            logger.info(f"[TRACKER] Saved {len(self.schedule)} dates")
        except Exception as e:
            logger.error(f"[TRACKER] Error saving: {e}")

    def get_count(self, date_str: str) -> int:
        """
        Get video count for a date.

        Args:
            date_str: Date string like "Jan 5, 2026"

        Returns:
            Number of videos scheduled for that date
        """
        return self.schedule.get(date_str, 0)

    def increment(self, date_str: str, video_id: Optional[str] = None):
        """
        Record a scheduled video.

        Args:
            date_str: Date string like "Jan 5, 2026"
            video_id: Optional video ID to track
        """
        # Global dedup: check if video was already scheduled on ANY date
        if video_id and self.is_video_scheduled(video_id):
            existing_date = next(
                (d for d, ids in self.video_ids.items() if video_id in ids), "?"
            )
            logger.warning(
                f"[TRACKER] Video {video_id} already scheduled on {existing_date} "
                f"— incrementing count for {date_str} but NOT re-appending ID"
            )
            # Still increment count (DOM action happened) but don't duplicate the ID
            self.schedule[date_str] = self.schedule.get(date_str, 0) + 1
            self.save()
            return

        prev_count = self.schedule.get(date_str, 0)
        self.schedule[date_str] = prev_count + 1

        if video_id:
            if date_str not in self.video_ids:
                self.video_ids[date_str] = []
            self.video_ids[date_str].append(video_id)

        self.save()
        total = sum(self.schedule.values())
        logger.info(
            f"[TRACKER] Recorded: {video_id or '?'} on {date_str} "
            f"(day {prev_count + 1}/{self.schedule[date_str]}, total={total})"
        )

    def set_count(self, date_str: str, count: int):
        """
        Set video count for a date (used when scanning existing schedule).

        Args:
            date_str: Date string
            count: Number of videos
        """
        self.schedule[date_str] = count
        # Don't save immediately - batch updates expected

    def get_next_available_slot(
        self,
        time_slots: List[str],
        max_per_day: int = 3,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        channel_tz: Optional[str] = None,
    ) -> Optional[Tuple[str, str]]:
        """
        Find next available scheduling slot.

        Args:
            time_slots: Canonical ET peak slots, e.g. ["08:00", "12:00", "20:00"]
                (also accepts 12h "8:00 AM" form). These describe the desired
                US-audience publish time in US-Eastern.
            max_per_day: Maximum videos per day
            start_date: Start of scheduling window (default: tomorrow)
            end_date: End of scheduling window (default: 60 days out)
            channel_tz: IANA tz of the channel's Studio account
                (e.g. "Asia/Tokyo", "America/New_York"). When provided, the ET
                base slot is converted to that account's local wall-clock
                (DST-aware) BEFORE jitter, because the scheduler types a bare
                time string that Studio interprets in the account's own tz.
                When None, the slot is used as-is (backwards compatible).

        Returns:
            (date_str, time_str) tuple or None if all slots filled.
            time_str is the bare time to TYPE into Studio (channel-tz local
            when channel_tz is given).
        """
        if start_date is None:
            start_date = datetime.now() + timedelta(days=1)
        if end_date is None:
            end_date = start_date + timedelta(days=60)

        # Authoritative clamp: never schedule more than HARD_CAP_PER_DAY per day,
        # even if a caller passes a larger max_per_day from a stale registry/config.
        effective_cap = min(max_per_day, HARD_CAP_PER_DAY)

        current = start_date

        while current <= end_date:
            # Format date like YouTube Studio shows it: "Jan 5, 2026"
            # Windows-safe formatting (avoid %-d which is unsupported on Windows)
            date_str = f"{current.strftime('%b')} {current.day}, {current.year}"

            count = self.get_count(date_str)

            if count < effective_cap:
                # Determine canonical ET base slot for this slot index.
                et_base = time_slots[count] if count < len(time_slots) else time_slots[-1]

                # Convert ET -> channel Studio-account tz (DST-aware) when known,
                # so the bare time we type publishes at the intended US-audience
                # peak. Identity for ET-account channels; shifts for others.
                if channel_tz:
                    base_time = convert_et_to_channel_tz(et_base, channel_tz, current)
                else:
                    base_time = et_base

                # Add jitter for human-like variance (reused, unchanged).
                time_slot = _add_time_jitter(base_time)
                slot_label = f"slot {count + 1}/{effective_cap}"
                logger.info(
                    f"[TRACKER] Allocated: {date_str} at {time_slot} "
                    f"({slot_label}, et_base={et_base}, local_base={base_time}, tz={channel_tz or 'as-is'})"
                )
                return (date_str, time_slot)

            current += timedelta(days=1)

        logger.warning("[TRACKER] All slots filled in 60-day window — no available slots")
        return None

    def get_summary(self) -> Dict:
        """
        Get summary statistics.

        Returns:
            Dict with total_scheduled, dates_with_videos, full_days, partial_days,
            date_range, and the raw schedule.
        """
        total = sum(self.schedule.values())
        dates_with_videos = {d: c for d, c in self.schedule.items() if c > 0}
        full_days = sum(1 for c in dates_with_videos.values() if c >= HARD_CAP_PER_DAY)
        partial_days = sum(1 for c in dates_with_videos.values() if 0 < c < HARD_CAP_PER_DAY)

        # Date range
        sorted_dates = sorted(dates_with_videos.keys(), key=lambda d: self._parse_date(d))
        first_date = sorted_dates[0] if sorted_dates else None
        last_date = sorted_dates[-1] if sorted_dates else None

        return {
            "channel_id": self.channel_id,
            "total_scheduled": total,
            "dates_with_videos": len(dates_with_videos),
            "full_days": full_days,
            "partial_days": partial_days,
            "first_date": first_date,
            "last_date": last_date,
            "schedule": self.schedule,
        }

    @staticmethod
    def _parse_date(date_str: str) -> datetime:
        """Parse 'Jan 5, 2026' format to datetime for sorting."""
        try:
            return datetime.strptime(date_str, "%b %d, %Y")
        except ValueError:
            # Handle single-digit days without leading zero
            try:
                return datetime.strptime(date_str.replace("  ", " "), "%b %d, %Y")
            except ValueError:
                return datetime.min

    def has_sufficient_coverage(self, min_days_ahead: int = 14) -> Tuple[bool, int]:
        """
        Check if channel has sufficient scheduling coverage into the future.

        Used to skip channels that already have enough scheduled videos,
        avoiding wasted page navigation and DOM automation.

        Args:
            min_days_ahead: Minimum number of days with 3/3 videos scheduled

        Returns:
            Tuple of (has_coverage: bool, days_ahead: int)
        """
        today = datetime.now().date()
        future_full_days = 0

        for date_str, count in self.schedule.items():
            try:
                parsed_date = self._parse_date(date_str).date()
                if parsed_date > today and count >= HARD_CAP_PER_DAY:
                    future_full_days += 1
            except Exception:
                continue

        has_coverage = future_full_days >= min_days_ahead
        if has_coverage:
            logger.info(
                f"[TRACKER] {self.channel_id}: {future_full_days} full days ahead "
                f"(>= {min_days_ahead}) — sufficient coverage, can skip"
            )
        return has_coverage, future_full_days

    def log_schedule_report(self):
        """Log a human-readable schedule report."""
        summary = self.get_summary()
        total = summary["total_scheduled"]
        full = summary["full_days"]
        partial = summary["partial_days"]
        first = summary["first_date"] or "n/a"
        last = summary["last_date"] or "n/a"

        logger.info(f"[TRACKER] ╔══ SCHEDULE REPORT: {self.channel_id[:12]}... ══╗")
        logger.info(f"[TRACKER] ║ Total scheduled: {total:>4} videos")
        logger.info(f"[TRACKER] ║ Full days ({HARD_CAP_PER_DAY}/{HARD_CAP_PER_DAY}): {full:>4} days")
        logger.info(f"[TRACKER] ║ Partial days:    {partial:>4} days")
        logger.info(f"[TRACKER] ║ Date range:      {first} → {last}")
        logger.info(f"[TRACKER] ╚{'═' * 44}╝")

    def is_video_scheduled(self, video_id: str) -> bool:
        """
        Check if a video has already been scheduled.

        Enables resume capability - if system restarts, skip already-scheduled videos.

        Args:
            video_id: YouTube video ID to check

        Returns:
            True if video was already scheduled, False otherwise
        """
        for date_str, ids in self.video_ids.items():
            if video_id in ids:
                logger.debug(f"[TRACKER] Video {video_id} already scheduled on {date_str}")
                return True
        return False

    def remove_video(self, video_id: str) -> bool:
        """
        Remove a video from the tracker (purge false positive).

        Used when a video was recorded as scheduled but YouTube still shows it
        as unlisted — meaning the scheduling action failed silently.

        Decrements the date count and removes the video ID from that date's list.

        Args:
            video_id: YouTube video ID to remove

        Returns:
            True if video was found and removed, False if not found
        """
        for date_str in list(self.video_ids.keys()):
            ids = self.video_ids[date_str]
            if video_id in ids:
                ids.remove(video_id)
                # Decrement the count for that date
                if date_str in self.schedule:
                    self.schedule[date_str] = max(0, self.schedule[date_str] - 1)
                    # Clean up empty dates
                    if self.schedule[date_str] == 0:
                        del self.schedule[date_str]
                if not ids:
                    del self.video_ids[date_str]
                self.save()
                logger.info(
                    f"[TRACKER] Purged false-positive: {video_id} from {date_str} "
                    f"(scheduling failed silently)"
                )
                return True
        logger.debug(f"[TRACKER] Video {video_id} not found in tracker — nothing to purge")
        return False

    def get_all_scheduled_video_ids(self) -> List[str]:
        """
        Get all video IDs that have been scheduled.

        Returns:
            List of all scheduled video IDs across all dates
        """
        all_ids = []
        for ids in self.video_ids.values():
            all_ids.extend(ids)
        return all_ids

    def sync_from_youtube(self, scheduled_videos: List[Dict]):
        """
        Sync tracker with actual YouTube schedule.

        Args:
            scheduled_videos: List of dicts with date key from DOM scrape
        """
        # Reset current schedule
        self.schedule = {}
        self.video_ids = {}

        # Rebuild from YouTube data
        for video in scheduled_videos:
            date_str = video.get("date", "")
            video_id = video.get("video_id", "")

            if date_str:
                self.schedule[date_str] = self.schedule.get(date_str, 0) + 1

                if video_id:
                    if date_str not in self.video_ids:
                        self.video_ids[date_str] = []
                    self.video_ids[date_str].append(video_id)

        self.save()
        logger.info(f"[TRACKER] Synced {len(scheduled_videos)} videos from YouTube")
