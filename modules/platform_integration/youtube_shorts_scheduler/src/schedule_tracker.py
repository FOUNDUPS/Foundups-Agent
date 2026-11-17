"""
Schedule Tracker for YouTube Shorts Scheduler

Persistent state management for tracking scheduled videos per date.
"""

import asyncio
import json
import copy
import logging
import random
import os
import re
import uuid
import threading
from contextvars import ContextVar
from contextlib import contextmanager
import pytz
from pathlib import Path
from typing import Dict, Optional, Tuple, List
from datetime import datetime, timedelta

# Pure ET-peak -> channel-account-tz conversion (DST-aware). The scheduler types
# a bare time that Studio interprets in the account's own tz, so an ET target
# must be converted to the channel-local wall-clock before typing.
from modules.platform_integration.youtube_shorts_scheduler.src.peak_window import (
    convert_et_to_channel_tz, get_peak_slots_et, is_move2japan, require_same_date_cadence,
    convert_et_to_channel_datetime, PEAK_SLOTS_TZ, _format_bare_time,
)

logger = logging.getLogger(__name__)
_HELD_CALENDAR_LOCKS = ContextVar('held_youtube_calendar_locks', default=())
_ACTIVE_CALENDAR_LOCKS = set()
_CALENDAR_LOCK_GUARD = threading.Lock()


@contextmanager
def channel_calendar_lock(channel_id):
    """Reuse a nested lock only in the same thread and asyncio task."""
    from modules.infrastructure.shared_utilities.runtime_artifact_safety import runtime_operation_lock
    try:
        task = asyncio.current_task()
    except RuntimeError:
        task = None
    lock_key = 'youtube-schedule-channel:' + channel_id
    local_key = os.path.normcase(lock_key)
    identity = (threading.get_ident(), task, local_key)
    held = _HELD_CALENDAR_LOCKS.get()
    if identity in held:
        yield
        return
    # Windows mutexes can reenter on the same OS thread from a different task.
    with _CALENDAR_LOCK_GUARD:
        if local_key in _ACTIVE_CALENDAR_LOCKS:
            raise TimeoutError('scheduling_channel_busy')
        _ACTIVE_CALENDAR_LOCKS.add(local_key)
    try:
        with runtime_operation_lock(lock_key, timeout_seconds=0.01):
            token = _HELD_CALENDAR_LOCKS.set((*held, identity))
            try:
                yield
            finally:
                _HELD_CALENDAR_LOCKS.reset(token)
    finally:
        with _CALENDAR_LOCK_GUARD:
            _ACTIVE_CALENDAR_LOCKS.discard(local_key)


def _unique_tracker_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate_tracker_key')
        result[key] = value
    return result


def _reject_tracker_constant(_value):
    raise ValueError('invalid_tracker_json_constant')

# Default storage location
TRACKER_DIR = Path(__file__).parent.parent / "memory"

# Authoritative per-channel daily cap on scheduled shorts.
# Belt-and-suspenders: the allocator clamps to this value even if a caller
# passes a larger max_per_day (e.g. a stale registry/config value of 8).
# Move2Japan has an explicit operator-approved override in channel_daily_cap.
HARD_CAP_PER_DAY = 3


def channel_daily_cap(channel_id: str, requested: Optional[int] = None) -> int:
    """Explicit Move2Japan cadence; all other channels retain the hard-three cap."""
    limit = 8 if is_move2japan(channel_id) else HARD_CAP_PER_DAY
    return limit if requested is None else max(0, min(requested, limit))

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

    def __init__(self, channel_id: str, storage_dir: Optional[Path] = None, *, persist: bool = True):
        """
        Initialize tracker for a channel.

        Args:
            channel_id: YouTube channel ID
            storage_dir: Optional custom storage directory
        """
        self.channel_id = channel_id
        self.storage_dir = storage_dir or TRACKER_DIR
        self.persist = persist
        if self.persist:
            self.storage_dir.mkdir(parents=True, exist_ok=True)

        self.tracker_file = self.storage_dir / f"schedule_{channel_id}.json"
        self.schedule: Dict[str, int] = {}  # {date_str: count}
        self.video_ids: Dict[str, List[str]] = {}  # {date_str: [video_ids]}
        self.occupied_slots: List[Dict] = []
        self.reservations: Dict[str, Dict] = {}
        # Persisted counts/slots are history, not a fresh live calendar receipt.
        self.calendar_ready = False
        self.calendar_timezone = None
        self._inventory_qualified = False

        self._load()

    def _load(self):
        """Refresh history while revoking any earlier in-memory calendar proof."""
        self.calendar_ready = self._inventory_qualified = False
        self.calendar_timezone = None
        try:
            data = self._read_state()
            reservations = self._merged_reservations(data.get('reservations', {}))
        except Exception as exc:
            logger.error('[TRACKER] Cannot load schedule state: %s', type(exc).__name__)
            raise ValueError('tracker_state_unreadable') from exc
        self.schedule = data['schedule']
        self.video_ids = data.get('video_ids', {})
        self.occupied_slots = data.get('occupied_slots', [])
        self.reservations = reservations

    def _read_state(self):
        if self.tracker_file.is_symlink():
            raise ValueError('tracker_state_link')
        try:
            handle = self.tracker_file.open('r', encoding='utf-8')
        except FileNotFoundError:
            return {'channel_id': self.channel_id, 'schedule': {}}
        with handle:
            data = json.load(handle, object_pairs_hook=_unique_tracker_keys,
                             parse_constant=_reject_tracker_constant)
        self._validate_state(data)
        return data

    def _validate_state(self, data):
        fields = {'channel_id', 'last_updated', 'schedule', 'video_ids', 'occupied_slots', 'reservations'}
        if not isinstance(data, dict) or set(data) - fields:
            raise ValueError('tracker_schema_invalid')
        if data.get('channel_id') != self.channel_id:
            raise ValueError('tracker_channel_mismatch')
        if 'last_updated' in data:
            datetime.fromisoformat(data['last_updated'])
        counts, video_ids = data.get('schedule'), data.get('video_ids', {})
        if not isinstance(counts, dict) or not isinstance(video_ids, dict):
            raise ValueError('tracker_history_invalid')
        if any(not isinstance(date, str) or self._parse_date(date) == datetime.min
               for date in set(counts) | set(video_ids)):
            raise ValueError('tracker_date_invalid')
        if any(type(count) is not int or count < 0 for count in counts.values()):
            raise ValueError('tracker_count_invalid')
        if any(not isinstance(ids, list) or any(not isinstance(vid, str) or not vid.strip() for vid in ids)
               for ids in video_ids.values()):
            raise ValueError('tracker_video_ids_invalid')
        slots = data.get('occupied_slots', [])
        if not isinstance(slots, list):
            raise ValueError('tracker_slots_invalid')
        seen = set()
        for row in slots:
            if (not isinstance(row, dict) or set(row) != {'video_id', 'date', 'time'}
                    or not isinstance(row['video_id'], str) or not re.fullmatch(r'[A-Za-z0-9_-]{11}', row['video_id'])
                    or row['video_id'] in seen):
                raise ValueError('tracker_slot_invalid')
            self._slot_wall_time(row['date'], row['time'])
            seen.add(row['video_id'])
        self._validate_reservations(data.get('reservations', {}))

    def _merged_reservations(self, retained):
        self._validate_reservations(self.reservations)
        merged = dict(self.reservations)
        for vid, reservation in retained.items():
            if vid in merged and merged[vid] != reservation:
                raise ValueError('reservation_changed')
            merged[vid] = reservation
        return merged

    def save(self):
        """Persist history and retain every existing unknown reservation."""
        if not self.persist:
            return
        with channel_calendar_lock(self.channel_id):
            retained = self._read_state().get('reservations', {})
            self._persist_state(self._merged_reservations(retained))

    def _persist_state(self, reservations):
        data = {'channel_id': self.channel_id, 'last_updated': datetime.now().isoformat(),
                'schedule': self.schedule, 'video_ids': self.video_ids,
                'occupied_slots': self.occupied_slots, 'reservations': reservations}
        self._validate_state(data)
        temporary = self.tracker_file.with_suffix('.' + uuid.uuid4().hex + '.tmp')
        owned = None
        try:
            with temporary.open('x', encoding='utf-8') as handle:
                owned = os.fstat(handle.fileno())
                json.dump(data, handle, indent=2)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.tracker_file)
            owned = None
            if os.name != 'nt':
                directory = os.open(self.tracker_file.parent, os.O_RDONLY | os.O_DIRECTORY)
                try:
                    os.fsync(directory)
                finally:
                    os.close(directory)
        finally:
            if owned is not None:
                try:
                    if os.path.samestat(owned, temporary.lstat()):
                        temporary.unlink()
                except FileNotFoundError:
                    pass
                except OSError:
                    logger.warning('[TRACKER] Could not clean owned temporary state')
        self.reservations = reservations

    def preview_copy(self):
        """Independent in-memory allocation state, retaining this storage scope."""
        preview = copy.deepcopy(self)
        preview.persist = False
        return preview

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
        max_per_day: Optional[int] = None,
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
        if self.calendar_ready:
            return self._next_unoccupied_slot(time_slots, max_per_day, start_date, end_date, channel_tz)

        if start_date is None:
            start_date = datetime.now() + timedelta(days=1)
        if end_date is None:
            end_date = start_date + timedelta(days=60)

        # Authoritative clamp: never schedule more than HARD_CAP_PER_DAY per day,
        # even if a caller passes a larger max_per_day from a stale registry/config.
        effective_cap = channel_daily_cap(self.channel_id, max_per_day)
        if is_move2japan(self.channel_id):
            time_slots = get_peak_slots_et(self.channel_id)

        current = start_date

        while current <= end_date:
            require_same_date_cadence(self.channel_id, channel_tz, current)
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
                time_slot = base_time if is_move2japan(self.channel_id) else _add_time_jitter(base_time)
                slot_label = f"slot {count + 1}/{effective_cap}"
                logger.info(
                    f"[TRACKER] Allocated: {date_str} at {time_slot} "
                    f"({slot_label}, et_base={et_base}, local_base={base_time}, tz={channel_tz or 'as-is'})"
                )
                return (date_str, time_slot)

            current += timedelta(days=1)

        logger.warning("[TRACKER] All slots filled in 60-day window — no available slots")
        return None

    @staticmethod
    def _slot_wall_time(date_str, time_str):
        if not isinstance(date_str, str) or not isinstance(time_str, str):
            raise ValueError('calendar_wall_time_invalid')
        value = datetime.strptime(f'{date_str} {time_str}', '%b %d, %Y %I:%M %p')
        if date_str != f'{value:%b} {value.day}, {value.year}' or time_str != _format_bare_time(value):
            raise ValueError('calendar_wall_time_noncanonical')
        return value

    @classmethod
    def _slot_instant(cls, date_str, time_str, timezone):
        if not isinstance(timezone, str) or not timezone:
            raise ValueError('calendar_timezone_required')
        return pytz.timezone(timezone).localize(cls._slot_wall_time(date_str, time_str), is_dst=None)

    @classmethod
    def _validate_reservations(cls, reservations):
        if not isinstance(reservations, dict):
            raise ValueError('invalid_reservations')
        for vid, row in reservations.items():
            if (not isinstance(vid, str) or not re.fullmatch(r'[A-Za-z0-9_-]{11}', vid)
                    or not isinstance(row, dict) or row.get('video_id') != vid
                    or row.get('outcome') != 'unknown'
                    or set(row) != {'video_id', 'date', 'time', 'timezone', 'outcome'}):
                raise ValueError('invalid_reservation')
            cls._slot_instant(row['date'], row['time'], row['timezone'])

    def _calendar_entries(self):
        return [*self.occupied_slots, *self.reservations.values()]

    def bind_calendar_timezone(self, timezone):
        """Validate every observed/pending wall time before enabling allocation."""
        self.calendar_ready = False
        self.calendar_timezone = None
        if not self._inventory_qualified:
            raise ValueError('calendar_inventory_unqualified')
        if not isinstance(timezone, str) or not timezone:
            raise ValueError("calendar_timezone_required")
        pytz.timezone(timezone)
        for row in self._calendar_entries():
            if row.get('timezone', timezone) != timezone:
                raise ValueError("calendar_timezone_changed")
            self._slot_instant(row['date'], row['time'], timezone)
        self._inventory_qualified = False
        self.calendar_timezone = timezone
        self.calendar_ready = True

    @staticmethod
    def _configured_spacing(time_slots):
        minutes = set()
        for time_slot in time_slots:
            clock = convert_et_to_channel_datetime(time_slot, PEAK_SLOTS_TZ, datetime(2000, 1, 15))
            minutes.add(clock.hour * 60 + clock.minute)
        clocks = sorted(minutes)
        return min(b - a for a, b in zip(clocks, clocks[1:] + [clocks[0] + 1440]))

    @classmethod
    def _valid_local_candidates(cls, time_slots, timezone, et_date):
        candidates = set()
        for slot in time_slots:
            try:
                instant = convert_et_to_channel_datetime(slot, timezone, et_date)
                date = f'{instant:%b} {instant.day}, {instant.year}'
                # Studio receives a wall time. A destination DST fold loses the
                # distinction even when the converted instant itself is exact.
                if cls._slot_instant(date, _format_bare_time(instant), timezone) == instant:
                    candidates.add(instant)
            except pytz.InvalidTimeError:
                continue
        return sorted(candidates)

    def _next_unoccupied_slot(self, time_slots, max_per_day, start_date, end_date, channel_tz):
        if channel_tz != self.calendar_timezone:
            raise ValueError("calendar_timezone_mismatch")
        source = pytz.timezone(PEAK_SLOTS_TZ)
        today = datetime.now(source)
        start_date = start_date or today + timedelta(days=1)
        end_date = end_date or start_date + timedelta(days=60)
        if is_move2japan(self.channel_id):
            time_slots = get_peak_slots_et(self.channel_id)
        if not time_slots:
            raise ValueError("calendar_slots_required")
        # Use configured cadence as the minimum separation, including midnight.
        spacing = self._configured_spacing(time_slots)
        entries = self._calendar_entries()
        occupied = {self._slot_instant(r['date'], r['time'], channel_tz) for r in entries}
        # Deduplicate one video observed in both inventory and its retained claim.
        day_ids = {}
        for r in entries:
            day_ids.setdefault(r['date'], set()).add(r['video_id'])
        cap = channel_daily_cap(self.channel_id, max_per_day)
        current = start_date
        while current.date() <= end_date.date():
            for candidate in self._valid_local_candidates(time_slots, channel_tz, current):
                date = f"{candidate:%b} {candidate.day}, {candidate.year}"
                if candidate <= today or len(day_ids.get(date, set())) >= cap:
                    continue
                if any(abs((candidate - old).total_seconds()) < spacing * 60 for old in occupied):
                    continue
                return date, _format_bare_time(candidate)
            current += timedelta(days=1)
        return None

    def reserve_slot(self, video_id, date, time, timezone):
        """Durably retain a proposed slot before a write; never retry a claim."""
        if (self.persist is not True or not self.calendar_ready or timezone != self.calendar_timezone
                or not isinstance(video_id, str) or not re.fullmatch(r'[A-Za-z0-9_-]{11}', video_id)
                or self.is_video_scheduled(video_id)):
            raise ValueError("calendar_reservation_blocked")
        instant = self._slot_instant(date, time, timezone)
        if instant <= datetime.now(pytz.UTC):
            raise ValueError('calendar_slot_in_past')
        with channel_calendar_lock(self.channel_id):
            stored = self._read_state()
            reservations = self._merged_reservations(stored.get('reservations', {}))
            entries = [*self.occupied_slots, *stored.get('occupied_slots', []), *reservations.values()]
            if any(row['video_id'] == video_id for row in entries):
                raise ValueError('calendar_reservation_blocked')
            for row in entries:
                if row.get('timezone', timezone) != timezone:
                    raise ValueError('calendar_timezone_changed')
                if self._slot_instant(row['date'], row['time'], timezone) == instant:
                    raise ValueError('calendar_slot_occupied')
            reservations[video_id] = {'video_id': video_id, 'date': date, 'time': time,
                                      'timezone': timezone, 'outcome': 'unknown'}
            self._persist_state(reservations)

    def get_summary(self) -> Dict:
        """
        Get summary statistics.

        Returns:
            Dict with total_scheduled, dates_with_videos, full_days, partial_days,
            date_range, and the raw schedule.
        """
        total = sum(self.schedule.values())
        dates_with_videos = {d: c for d, c in self.schedule.items() if c > 0}
        full_days = sum(1 for c in dates_with_videos.values() if c >= channel_daily_cap(self.channel_id))
        partial_days = sum(1 for c in dates_with_videos.values() if 0 < c < channel_daily_cap(self.channel_id))

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
                if parsed_date > today and count >= channel_daily_cap(self.channel_id):
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
        logger.info(f"[TRACKER] ║ Full days ({channel_daily_cap(self.channel_id)}/{channel_daily_cap(self.channel_id)}): {full:>4} days")
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

    def sync_from_youtube(self, scheduled_videos: List[Dict], *, inventory: Optional[Dict] = None) -> bool:
        """
        Sync tracker with actual YouTube schedule.

        Args:
            scheduled_videos: Qualified exact slots from the inventory receipt
            inventory: Complete channel/filter/pagination proof; required for reset
        """
        from .schedule_inventory import qualified_inventory

        self.calendar_ready = self._inventory_qualified = False
        self.calendar_timezone = None
        if not isinstance(scheduled_videos, list) or not qualified_inventory(inventory, self.channel_id, scheduled_videos):
            logger.warning("[TRACKER] Refusing sync without complete matching scheduled inventory")
            return False

        # Reset current schedule
        self.schedule = {}
        self.video_ids = {}
        self.occupied_slots = [{key: video[key] for key in ('video_id', 'date', 'time')}
                               for video in scheduled_videos]

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
        self._inventory_qualified = True
        logger.info(f"[TRACKER] Synced {len(scheduled_videos)} videos from YouTube")
        return True
