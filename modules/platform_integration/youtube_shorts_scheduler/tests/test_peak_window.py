"""
Unit tests for US-ET peak slots + per-channel Studio-tz conversion.

Slice: SHORTS_SCHEDULE_US_PEAK_WINDOW_PHASE1

Model under test
----------------
ALL shorts target the US audience, so peak publish times are defined ONCE in
US-Eastern (ET): morning ~08:00, lunch ~12:00, evening ~20:00. The scheduler
types a BARE time string that YouTube Studio interprets in each channel's own
account timezone, so an ET target must be converted to the channel-local
wall-clock (DST-aware) before typing.

These tests are mock-only (no browser, no daemon, no models) and NON-VACUOUS:
they pin the ET peaks, prove the conversion produces channel-local wall-clocks,
prove DST is handled (summer vs winter), and guard against the old bare-time bug
(a Tokyo channel must NOT type 8:00 AM for an 08:00 ET morning slot).
"""

import os
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from modules.platform_integration.youtube_shorts_scheduler.src.peak_window import (
    get_peak_slots_et,
    convert_et_to_channel_tz,
    get_peak_slots_for_channel,
    _DEFAULT_PEAK_SLOTS_ET,
    PEAK_SLOTS_ENV,
)
from modules.platform_integration.youtube_shorts_scheduler.src.schedule_tracker import (
    ScheduleTracker,
    MAX_JITTER_STEPS,
)

# Channel Studio-account timezones (verified in registry / #844 commit body).
TOKYO_TZ = "Asia/Tokyo"
NY_TZ = "America/New_York"

# DST probe dates: US Eastern observes DST roughly mid-Mar..early-Nov.
SUMMER = datetime(2026, 7, 15)  # EDT = UTC-4
WINTER = datetime(2026, 1, 15)  # EST = UTC-5


def _to_24h(bare: str) -> str:
    """Normalize a bare 12h time like '9:00 PM' to '21:00' for comparison."""
    return datetime.strptime(bare.strip(), "%I:%M %p").strftime("%H:%M")


def _within_jitter(actual_bare: str, base_bare: str) -> bool:
    """True if actual is within +/- (MAX_JITTER_STEPS * 15min) of base."""
    a = datetime.strptime(actual_bare.strip(), "%I:%M %p")
    b = datetime.strptime(base_bare.strip(), "%I:%M %p")
    return abs((a - b).total_seconds()) / 60.0 <= MAX_JITTER_STEPS * 15


# ---------------------------------------------------------------------------
# 1. The canonical slots are the ET peaks (08 / 12 / 20 ET).
# ---------------------------------------------------------------------------

class TestCanonicalETPeaks:
    def test_defaults_are_the_three_us_et_peaks(self):
        assert get_peak_slots_et() == ["08:00", "12:00", "20:00"]
        assert _DEFAULT_PEAK_SLOTS_ET == ["08:00", "12:00", "20:00"]

    def test_three_slots_matching_the_daily_cap(self):
        # Default count must match the landed 3/day HARD_CAP_PER_DAY.
        assert len(get_peak_slots_et()) == 3

    def test_env_override_is_respected(self, monkeypatch):
        monkeypatch.setenv(PEAK_SLOTS_ENV, "07:30, 13:00, 19:00")
        assert get_peak_slots_et() == ["07:30", "13:00", "19:00"]

    def test_malformed_env_falls_back_to_defaults(self, monkeypatch):
        monkeypatch.setenv(PEAK_SLOTS_ENV, "not-a-time,99:99")
        assert get_peak_slots_et() == ["08:00", "12:00", "20:00"]


# ---------------------------------------------------------------------------
# 2. Conversion correctness per channel + DST.
# ---------------------------------------------------------------------------

class TestConversionPerChannel:
    def test_ny_channel_is_identity_with_et(self):
        # America/New_York Studio account == the ET canonical, so no shift.
        assert _to_24h(convert_et_to_channel_tz("08:00", NY_TZ, SUMMER)) == "08:00"
        assert _to_24h(convert_et_to_channel_tz("12:00", NY_TZ, WINTER)) == "12:00"
        assert _to_24h(convert_et_to_channel_tz("20:00", NY_TZ, SUMMER)) == "20:00"

    def test_tokyo_channel_summer_offset(self):
        # EDT (UTC-4) -> JST (UTC+9) = +13h. 08:00 ET -> 21:00 JST.
        assert _to_24h(convert_et_to_channel_tz("08:00", TOKYO_TZ, SUMMER)) == "21:00"
        assert _to_24h(convert_et_to_channel_tz("20:00", TOKYO_TZ, SUMMER)) == "09:00"

    def test_tokyo_channel_winter_offset_dst_aware(self):
        # EST (UTC-5) -> JST (UTC+9) = +14h. 08:00 ET -> 22:00 JST (one hour
        # later than summer => proves the conversion is DST-aware, not a fixed
        # offset).
        assert _to_24h(convert_et_to_channel_tz("08:00", TOKYO_TZ, WINTER)) == "22:00"

    def test_dst_changes_the_tokyo_wallclock(self):
        # The SAME ET target yields a DIFFERENT JST wall-clock across the DST
        # boundary. If this were a naive/fixed-offset conversion, these would be
        # equal -- so this asserts genuine DST handling.
        summer = _to_24h(convert_et_to_channel_tz("08:00", TOKYO_TZ, SUMMER))
        winter = _to_24h(convert_et_to_channel_tz("08:00", TOKYO_TZ, WINTER))
        assert summer != winter, "DST not handled: summer/winter JST identical"
        assert (summer, winter) == ("21:00", "22:00")

    def test_get_peak_slots_for_channel_preserves_order(self):
        ny = get_peak_slots_for_channel(NY_TZ, SUMMER)
        assert [_to_24h(t) for t in ny] == ["08:00", "12:00", "20:00"]
        tokyo = get_peak_slots_for_channel(TOKYO_TZ, SUMMER)
        assert [_to_24h(t) for t in tokyo] == ["21:00", "01:00", "09:00"]

    def test_conversion_is_not_a_no_op_for_tokyo(self):
        # NON-VACUITY GUARD: if convert_et_to_channel_tz ever degenerates to
        # identity (no-op), this fails. The Tokyo wall-clock MUST differ from
        # the ET input string for the morning slot.
        out = _to_24h(convert_et_to_channel_tz("08:00", TOKYO_TZ, SUMMER))
        assert out != "08:00", "Conversion is identity/no-op (bug reintroduced)"


# ---------------------------------------------------------------------------
# 3. Allocator regression guard: Tokyo 08:00 ET is NOT typed as 08:00.
# ---------------------------------------------------------------------------

class TestAllocatorTypesChannelLocal:
    def _tracker(self):
        return ScheduleTracker("UC_test_peak", Path(tempfile.mkdtemp()))

    def test_tokyo_morning_slot_is_jst_evening_not_bare_8am(self):
        t = self._tracker()
        slot = t.get_next_available_slot(
            get_peak_slots_et(),
            max_per_day=3,
            start_date=SUMMER,
            channel_tz=TOKYO_TZ,
        )
        assert slot is not None
        _, typed = slot
        # Old bug: typed the bare ET "8:00 AM" on a Tokyo Studio account, which
        # Studio reads as 8:00 AM JST -> wrong US wall-clock. New behavior types
        # the JST-local equivalent (~9:00 PM) so it publishes at 08:00 ET.
        assert "AM" not in typed or _to_24h(typed) != "08:00", (
            f"REGRESSION: Tokyo morning slot typed as bare ET time {typed!r}"
        )
        assert _within_jitter(typed, "9:00 PM"), (
            f"Tokyo 08:00 ET morning expected ~9:00 PM JST, got {typed!r}"
        )

    def test_ny_morning_slot_is_typed_8am(self):
        t = self._tracker()
        slot = t.get_next_available_slot(
            get_peak_slots_et(),
            max_per_day=3,
            start_date=SUMMER,
            channel_tz=NY_TZ,
        )
        assert slot is not None
        _, typed = slot
        # NY Studio account == ET, so the bare 8:00 AM is correct here.
        assert _within_jitter(typed, "8:00 AM"), (
            f"NY 08:00 ET morning expected ~8:00 AM, got {typed!r}"
        )

    def test_tokyo_and_ny_diverge_for_same_et_slot(self):
        # Cross-channel proof that tz is actually consulted: the same ET morning
        # slot produces materially different typed times for Tokyo vs NY.
        t_tokyo = self._tracker().get_next_available_slot(
            get_peak_slots_et(), max_per_day=3, start_date=SUMMER, channel_tz=TOKYO_TZ
        )
        t_ny = self._tracker().get_next_available_slot(
            get_peak_slots_et(), max_per_day=3, start_date=SUMMER, channel_tz=NY_TZ
        )
        assert t_tokyo is not None and t_ny is not None
        # Compare AM/PM period to be robust against jitter on the boundary.
        tokyo_period = t_tokyo[1].split()[-1]
        ny_period = t_ny[1].split()[-1]
        assert (tokyo_period, ny_period) == ("PM", "AM"), (
            f"tz not consulted: tokyo={t_tokyo[1]!r} ny={t_ny[1]!r}"
        )
