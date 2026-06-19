"""
Peak Window - US-audience peak publish slots for YouTube Shorts.

Canonical model
---------------
ALL shorts target the US audience, so the optimum publish times are defined
ONCE in US-Eastern (ET). Research-backed daily peaks for short-form watch time
on YouTube cluster around the morning commute, the lunch break, and the evening
prime-time window:

    morning ~08:00 ET  |  lunch ~12:00 ET  |  evening ~20:00 ET

The scheduler types a *bare* time string into YouTube Studio and never touches
Studio's timezone selector (verified: dom_automation.set_schedule_time types
the string directly; click_done guards against the timezone-select-button).
Studio therefore interprets the typed time in each ACCOUNT's own timezone.

So to publish at an ET target on a channel whose Studio account tz = X, we must
type the X-local wall-clock equivalent of the ET time. Example (DST-aware):

    08:00 ET on a Tokyo-Studio channel  -> type ~21:00 JST (summer) / ~22:00 (winter)
    08:00 ET on a New York-Studio channel -> type 08:00 (identity)

This module is the single, pure, unit-testable source of:
  1. the canonical ET peak slots (configurable via env SHORTS_PEAK_SLOTS_ET), and
  2. the ET -> channel-account-tz conversion (DST-aware via pytz).

Future WRE enhancement (extension seam)
---------------------------------------
The ET defaults below are RESEARCHED static defaults. A future WRE skill can
LEARN the optimum per-channel publish times from real engagement data
(impressions/CTR/retention by hour) and replace get_peak_slots_et() /
override the slots per channel. Keep that learner pure and feed it through the
same conversion path so the bare-time-in-account-tz contract is preserved.

WSP References:
- WSP 3: Functional Distribution (platform_integration owns publish-time policy)
- WSP 50/84: reuse pytz (already a repo dependency) instead of zoneinfo+tzdata
- WSP 22: ModLog documents the future-learns-optimum seam
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import List

import pytz

# Canonical US-Eastern peak slots, in 24h "HH:MM" ET. Defined ONCE here.
# Override via env: SHORTS_PEAK_SLOTS_ET="08:00,12:00,20:00"
_DEFAULT_PEAK_SLOTS_ET: List[str] = ["08:00", "12:00", "20:00"]

# Canonical timezone the slots are expressed in.
PEAK_SLOTS_TZ = "America/New_York"

# Env var name (single knob) for overriding the ET peak slots.
PEAK_SLOTS_ENV = "SHORTS_PEAK_SLOTS_ET"


def get_peak_slots_et() -> List[str]:
    """
    Return the canonical ET peak slots as 24h "HH:MM" strings.

    Reads the env override SHORTS_PEAK_SLOTS_ET if present (comma-separated,
    e.g. "08:00,12:00,20:00"); otherwise returns the researched defaults.
    Malformed env values fall back to the defaults (fail-safe).
    """
    raw = os.getenv(PEAK_SLOTS_ENV, "").strip()
    if not raw:
        return list(_DEFAULT_PEAK_SLOTS_ET)
    slots: List[str] = []
    for token in raw.split(","):
        token = token.strip()
        if not token:
            continue
        # Validate "HH:MM" before accepting.
        try:
            datetime.strptime(token, "%H:%M")
        except ValueError:
            return list(_DEFAULT_PEAK_SLOTS_ET)
        slots.append(token)
    return slots or list(_DEFAULT_PEAK_SLOTS_ET)


def _format_bare_time(dt: datetime) -> str:
    """
    Format a datetime as the bare 12h time string YouTube Studio accepts.

    e.g. "8:00 AM", "12:00 PM", "9:00 PM" (no leading zero on the hour),
    matching the existing jitter/typer convention in schedule_tracker.py.
    """
    hour = dt.hour % 12 or 12
    period = "AM" if dt.hour < 12 else "PM"
    return f"{hour}:{dt.minute:02d} {period}"


def convert_et_to_channel_tz(et_time: str, channel_tz: str, on_date: datetime) -> str:
    """
    Convert a canonical ET peak time to the channel account-tz wall-clock.

    DST-aware: the conversion uses ``on_date`` so summer/winter offsets are
    correct. The returned string is the *bare* 12h time to TYPE into Studio
    (Studio interprets it in the account's own tz).

    Args:
        et_time: ET slot as 24h "HH:MM" (e.g. "08:00") or 12h "8:00 AM".
        channel_tz: IANA tz of the channel's Studio account
                    (e.g. "America/New_York", "Asia/Tokyo").
        on_date: the calendar date the slot will publish on (for DST).

    Returns:
        Bare 12h time string in the channel account tz, e.g. "9:00 PM".

    Raises:
        pytz.UnknownTimeZoneError: if channel_tz is not a valid IANA zone.
        ValueError: if et_time cannot be parsed.
    """
    # Parse the ET time-of-day (accept "HH:MM" 24h or "I:MM AM/PM" 12h).
    parsed = None
    for fmt in ("%H:%M", "%I:%M %p"):
        try:
            parsed = datetime.strptime(et_time.strip(), fmt)
            break
        except ValueError:
            continue
    if parsed is None:
        raise ValueError(f"Unparseable ET time: {et_time!r}")

    src_tz = pytz.timezone(PEAK_SLOTS_TZ)
    dst_tz = pytz.timezone(channel_tz)

    # Anchor the ET time-of-day to the publish date, localized in ET (DST-aware).
    naive = datetime(
        on_date.year, on_date.month, on_date.day, parsed.hour, parsed.minute
    )
    et_dt = src_tz.localize(naive)

    # Convert to the channel account tz; the wall-clock there is what we type.
    local_dt = et_dt.astimezone(dst_tz)
    return _format_bare_time(local_dt)


def get_peak_slots_for_channel(channel_tz: str, on_date: datetime) -> List[str]:
    """
    Return the canonical ET peak slots converted to channel account-tz wall-clocks.

    Pure helper: maps each ET slot through convert_et_to_channel_tz for the given
    date (DST-aware). Order is preserved (morning/lunch/evening) so it lines up
    with the allocator's slot-index logic.
    """
    return [
        convert_et_to_channel_tz(et_time, channel_tz, on_date)
        for et_time in get_peak_slots_et()
    ]
