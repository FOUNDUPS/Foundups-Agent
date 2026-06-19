"""
Long-form (Videos-tab) US-ET peak + per-channel Studio-tz conversion tests.

Slice: LONG_FORM_TZ_PEAK_WINDOW_PHASE1  (#847 follow-up)

Model under test
----------------
Long-form videos target the US audience exactly like shorts do, so their peak
publish times are the SAME canonical US-Eastern (ET) slots
(peak_window.get_peak_slots_et() -> ["08:00", "12:00", "20:00"]). The scheduler
types a BARE time string that YouTube Studio interprets in each channel's own
account timezone, so an ET target must be DST-converted to the channel-local
wall-clock before typing.

Before this slice the long-form path
(ContentPageScheduler.schedule_all_visible) called
tracker.get_next_available_slot(time_slots, max_per_day) WITHOUT channel_tz, so
the bare ET slot was typed AS-IS in the account tz. For an Asia/Tokyo channel
(Move2Japan / UnDaoDu) that means 08:00 ET was typed as 8:00 AM JST -- the WRONG
US wall-clock (off the US peak). This slice forwards channel_tz so the ET peak is
converted to the channel-local equivalent (DST-aware), identical to the shorts
path (scheduler.py self.channel_tz, #847).

These tests are MOCK-ONLY (no browser, no daemon, no network, no models) and
NON-VACUOUS. They drive the REAL ContentPageScheduler.schedule_all_visible with a
REAL ScheduleTracker; only the DOM row-read and the per-row Studio click flow are
stubbed (to capture the time string that WOULD be typed). They prove:
  * a Tokyo channel types the JST-equivalent of the ET peak (summer AND winter),
  * a NY channel types the ET peak as-is (identity),
  * DST is handled (summer != winter JST wall-clock),
  * MUST-FAIL: the OLD behavior (no channel_tz) types bare ET for Tokyo, which is
    the wrong wall-clock -- so the with-tz path MUST differ from it.
"""

import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from modules.platform_integration.youtube_shorts_scheduler.src.content_page_scheduler import (
    ContentPageScheduler,
)
from modules.platform_integration.youtube_shorts_scheduler.src.schedule_tracker import (
    ScheduleTracker,
    MAX_JITTER_STEPS,
)
from modules.platform_integration.youtube_shorts_scheduler.src.peak_window import (
    get_peak_slots_et,
)

# Channel Studio-account timezones (verified in registry youtube_channel_registry).
TOKYO_TZ = "Asia/Tokyo"           # Move2Japan, UnDaoDu
NY_TZ = "America/New_York"        # FoundUps, antifaFM

# DST probe dates: US Eastern observes DST roughly mid-Mar..early-Nov.
SUMMER = datetime(2026, 7, 15)    # EDT = UTC-4 -> JST(+9) = +13h
WINTER = datetime(2026, 1, 15)    # EST = UTC-5 -> JST(+9) = +14h


def _to_24h(bare: str) -> str:
    """Normalize a bare 12h time like '9:00 PM' to '21:00' for comparison."""
    return datetime.strptime(bare.strip(), "%I:%M %p").strftime("%H:%M")


def _hour24(bare: str) -> int:
    """
    Hour-of-day (0-23) from either a 12h '9:00 PM' string or a bare 24h '08:00'.
    The no-tz path types the canonical 24h ET slot as-is (no jitter), so the
    must-fail comparison must tolerate both forms.
    """
    s = bare.strip()
    for fmt in ("%I:%M %p", "%H:%M"):
        try:
            return datetime.strptime(s, fmt).hour
        except ValueError:
            continue
    raise ValueError(f"unparseable time: {bare!r}")


def _within_jitter(actual_bare: str, base_bare: str) -> bool:
    """True if actual is within +/- (MAX_JITTER_STEPS * 15min) of base."""
    a = datetime.strptime(actual_bare.strip(), "%I:%M %p")
    b = datetime.strptime(base_bare.strip(), "%I:%M %p")
    return abs((a - b).total_seconds()) / 60.0 <= MAX_JITTER_STEPS * 15


def _tracker():
    """Real ScheduleTracker in a throwaway temp dir (no shared state)."""
    return ScheduleTracker("UC_test_longform_tz", Path(tempfile.mkdtemp()))


class _StubDom:
    """Minimal DOM stand-in: only human_delay is exercised by schedule_all_visible."""

    def human_delay(self, *a, **k):
        return 0.0


class _CapturingScheduler(ContentPageScheduler):
    """
    REAL ContentPageScheduler with ONLY the browser-touching seams stubbed:
      * get_video_rows_with_data -> a fixed list of unlisted rows (no DOM),
      * schedule_video_from_row -> captures the (date_str, time_str) that WOULD
        be typed into Studio and returns True (no clicks).
    Everything else -- including the slot allocation / channel_tz conversion in
    schedule_all_visible + get_next_available_slot -- runs for real.
    """

    def __init__(self, n_rows: int):
        # Do NOT call super().__init__ (it builds a DOM against a real driver).
        self.driver = None
        # Minimal DOM stub: schedule_all_visible calls dom.human_delay() between
        # videos. Return 0 so the inter-video asyncio.sleep is a no-op.
        self.dom = _StubDom()
        self._n_rows = n_rows
        self.typed = []  # list of (date_str, time_str)

    def refresh_page(self):
        # schedule_all_visible refreshes every 3rd schedule; no real browser here.
        return None

    def get_video_rows_with_data(self):
        return [
            {
                "video_id": f"vid_{i}",
                "title": f"Long-form {i}",
                "visibility": "unlisted",
                "row_element": object(),
            }
            for i in range(self._n_rows)
        ]

    async def schedule_video_from_row(self, row_element, date_str, time_str, video_id="unknown"):
        self.typed.append((date_str, time_str))
        return True


async def _run(channel_tz, start_date, n_rows=1, max_per_day=4):
    """
    Drive the REAL schedule_all_visible with the ET peak slots + given channel_tz,
    forcing the tracker's scheduling window to begin on `start_date` so the DST
    branch under test is deterministic. Returns the list of typed time strings.
    """
    sched = _CapturingScheduler(n_rows=n_rows)
    tracker = _tracker()
    # Pin the allocation window so DST (summer/winter) is deterministic.
    orig = tracker.get_next_available_slot

    def pinned(time_slots, mpd=max_per_day, **kw):
        return orig(time_slots, mpd, start_date=start_date, **kw)

    tracker.get_next_available_slot = pinned  # type: ignore[assignment]

    await sched.schedule_all_visible(
        tracker=tracker,
        time_slots=get_peak_slots_et(),
        max_per_day=max_per_day,
        max_videos=n_rows,
        channel_tz=channel_tz,
    )
    return [t for _, t in sched.typed]


# ---------------------------------------------------------------------------
# 1. Tokyo channel: ET peak -> JST-equivalent (DST-aware).
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_tokyo_morning_slot_summer_is_jst_evening_not_bare_8am():
    # 08:00 ET (EDT, UTC-4) -> 21:00 JST. The long-form path MUST type ~9:00 PM,
    # NOT the bare ET "8:00 AM".
    typed = await _run(TOKYO_TZ, SUMMER, n_rows=1)
    assert typed, "no slot was allocated"
    t = typed[0]
    assert _to_24h(t) != "08:00", (
        f"REGRESSION: Tokyo 08:00 ET morning typed as bare ET time {t!r} "
        f"(channel_tz not consulted -> wrong US wall-clock)"
    )
    assert _within_jitter(t, "9:00 PM"), (
        f"Tokyo 08:00 ET (summer) expected ~9:00 PM JST, got {t!r}"
    )


@pytest.mark.asyncio
async def test_tokyo_morning_slot_winter_is_one_hour_later_dst_aware():
    # 08:00 ET (EST, UTC-5) -> 22:00 JST: one hour LATER than summer, proving the
    # conversion is DST-aware (not a fixed offset).
    typed = await _run(TOKYO_TZ, WINTER, n_rows=1)
    assert typed
    assert _within_jitter(typed[0], "10:00 PM"), (
        f"Tokyo 08:00 ET (winter) expected ~10:00 PM JST, got {typed[0]!r}"
    )


@pytest.mark.asyncio
async def test_tokyo_dst_summer_winter_diverge():
    # The SAME ET morning target yields a DIFFERENT JST wall-clock across the DST
    # boundary (21:00 summer vs 22:00 winter base). A naive/fixed-offset or
    # bare-ET path would make these equal. Jitter (+/-30min) is bounded, so each
    # output stays within jitter of its OWN base; the bases differ by 60min.
    summer = await _run(TOKYO_TZ, SUMMER, n_rows=1)
    winter = await _run(TOKYO_TZ, WINTER, n_rows=1)
    assert _within_jitter(summer[0], "9:00 PM"), (
        f"Tokyo summer expected ~21:00 JST base, got {summer[0]!r}"
    )
    assert _within_jitter(winter[0], "10:00 PM"), (
        f"Tokyo winter expected ~22:00 JST base, got {winter[0]!r}"
    )


# ---------------------------------------------------------------------------
# 2. NY channel: ET peak typed as-is (identity).
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_ny_morning_slot_is_typed_8am_identity():
    # America/New_York Studio account == the ET canonical, so 08:00 ET stays 8 AM.
    typed = await _run(NY_TZ, SUMMER, n_rows=1)
    assert typed
    assert _within_jitter(typed[0], "8:00 AM"), (
        f"NY 08:00 ET morning expected ~8:00 AM (identity), got {typed[0]!r}"
    )


# ---------------------------------------------------------------------------
# 3. Cross-channel + MUST-FAIL proofs.
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_tokyo_and_ny_diverge_for_same_et_morning_slot():
    # tz is actually consulted: the same ET morning slot produces materially
    # different typed times (PM in Tokyo, AM in NY).
    tokyo = await _run(TOKYO_TZ, SUMMER, n_rows=1)
    ny = await _run(NY_TZ, SUMMER, n_rows=1)
    assert tokyo[0].split()[-1] == "PM", f"tokyo not PM: {tokyo[0]!r}"
    assert ny[0].split()[-1] == "AM", f"ny not AM: {ny[0]!r}"


@pytest.mark.asyncio
async def test_must_fail_old_behavior_types_bare_et_for_tokyo():
    """
    MUST-FAIL proof. The OLD long-form path called get_next_available_slot
    WITHOUT channel_tz (channel_tz=None), which types the bare ET slot in the
    account tz. For a Tokyo channel that is 8:00 AM JST -- the WRONG US wall-clock.
    The new with-tz behavior MUST differ. This test pins that the two paths are
    NOT equal, so a regression that drops channel_tz forwarding re-collapses them
    and FAILS.
    """
    old = await _run(None, SUMMER, n_rows=1)         # no channel_tz -> bare ET
    new = await _run(TOKYO_TZ, SUMMER, n_rows=1)     # converted to JST

    # The bare-ET (no-tz) path types the canonical 24h ET morning slot "08:00"
    # as-is (it never reaches the 12h jitter path because convert is skipped),
    # i.e. an 08:xx ET-morning wall-clock. The with-tz path converts to JST
    # evening (~21:00 / 9 PM). An ET-morning vs JST-evening wall-clock can never
    # collide -> robust proof the tz conversion changed the typed time.
    assert _hour24(old[0]) == 8, (
        f"baseline drifted: bare-ET (no tz) path expected the 08:00 ET morning "
        f"slot, got {old[0]!r}"
    )
    assert _hour24(new[0]) != _hour24(old[0]) and 19 <= _hour24(new[0]) <= 23, (
        f"NO-OP BUG: bare-ET={old[0]!r} with-tz={new[0]!r} did not diverge to JST "
        f"evening -> channel_tz not forwarded through schedule_all_visible"
    )


@pytest.mark.asyncio
async def test_full_day_of_peaks_converted_in_order_for_tokyo():
    # Three ET peaks (08/12/20) -> three JST wall-clocks in order on one day
    # (summer): 08:00 ET->21:00, 12:00 ET->01:00, 20:00 ET->09:00 JST. Each
    # output is within bounded jitter (+/-30min) of its converted base, in order.
    typed = await _run(TOKYO_TZ, SUMMER, n_rows=3, max_per_day=3)
    assert len(typed) == 3, f"expected 3 slots, got {typed}"
    expected_bases = ["9:00 PM", "1:00 AM", "9:00 AM"]  # 21:00 / 01:00 / 09:00 JST
    for got, base in zip(typed, expected_bases):
        assert _within_jitter(got, base), (
            f"Tokyo ET peak did not convert to JST {base!r} (within jitter); got {got!r}"
        )
