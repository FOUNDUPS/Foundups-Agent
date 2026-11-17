"""Exact calendar and durable reservation controls with synthetic local state."""
import asyncio
from contextlib import contextmanager
from datetime import datetime
import json
from types import SimpleNamespace

import pytest
import pytz

from modules.infrastructure.shared_utilities import runtime_artifact_safety as safety
from modules.platform_integration.youtube_shorts_scheduler.src import schedule_tracker as tracker_module
from modules.platform_integration.youtube_shorts_scheduler.src.peak_window import (
    convert_et_to_channel_datetime,
    convert_et_to_channel_tz,
)
from modules.platform_integration.youtube_shorts_scheduler.src.schedule_inventory import parse_scheduled_row
from modules.platform_integration.youtube_shorts_scheduler.src.schedule_tracker import (
    ScheduleTracker,
    channel_calendar_lock,
)


CHANNEL = 'UC' + 'a' * 22
FIRST, SECOND, THIRD = 'a' * 11, 'b' * 11, 'c' * 11
DATE = 'Jan 5, 2099'
ZONE = 'America/New_York'


def _row(video_id, date, time):
    return parse_scheduled_row({'video_id': video_id, 'schedule_text': f'Scheduled {date} {time}',
                                'title': 'Synthetic fixture title'})


def _inventory(rows):
    return dict(status='complete', channel_id=CHANNEL, channel_verified=True, filter_verified=True,
                start_verified=True, pagination_complete=True, pages_read=1,
                rows_seen=len(rows), rows_parsed=len(rows), total_scheduled=len(rows),
                issues=[], unparsed_rows=[], videos=rows)


def _qualify(tracker, rows=(), zone=ZONE):
    rows = list(rows)
    assert tracker.sync_from_youtube(rows, inventory=_inventory(rows))
    tracker.bind_calendar_timezone(zone)
    return tracker


def _allocate(tracker, slots, start=datetime(2099, 1, 5), *, zone=ZONE, cap=3):
    return tracker.get_next_available_slot(slots, cap, start, start, channel_tz=zone)


def test_exact_occupancy_uses_free_nonprefix_slot(tmp_path):
    tracker = _qualify(ScheduleTracker(CHANNEL, tmp_path), [_row(FIRST, DATE, '12:00 PM')])
    assert tracker.occupied_slots == [{'video_id': FIRST, 'date': DATE, 'time': '12:00 PM'}]
    assert _allocate(tracker, ['08:00', '12:00', '16:00']) == (DATE, '8:00 AM')


def test_spacing_blocks_nearby_slot_across_midnight(tmp_path):
    tracker = _qualify(ScheduleTracker(CHANNEL, tmp_path), [_row(FIRST, 'Jan 4, 2099', '11:30 PM')])
    assert _allocate(tracker, ['00:30', '06:30', '12:30']) == (DATE, '6:30 AM')


def test_local_date_rollover_uses_destination_day_for_occupancy(tmp_path):
    tracker = _qualify(ScheduleTracker(CHANNEL, tmp_path), zone='Asia/Tokyo')
    date, time = _allocate(tracker, ['20:00'], zone='Asia/Tokyo')
    assert (date, time) == ('Jan 6, 2099', '10:00 AM')
    tracker.reserve_slot(FIRST, date, time, 'Asia/Tokyo')
    assert _allocate(tracker, ['20:00'], zone='Asia/Tokyo') is None


def test_pending_and_observed_same_video_count_once_for_day_cap(tmp_path):
    tracker = _qualify(ScheduleTracker(CHANNEL, tmp_path))
    tracker.reserve_slot(FIRST, DATE, '8:00 AM', ZONE)
    _qualify(tracker, [_row(FIRST, DATE, '8:00 AM'), _row(SECOND, DATE, '12:00 PM')])
    assert _allocate(tracker, ['08:00', '12:00', '16:00'], cap=2) is None
    assert _allocate(tracker, ['08:00', '12:00', '16:00']) == (DATE, '4:00 PM')


@pytest.mark.parametrize('day,clock,error', [
    ((2030, 3, 10), '2:30 AM', pytz.NonExistentTimeError),
    ((2030, 11, 3), '1:30 AM', pytz.AmbiguousTimeError),
])
def test_strict_instant_rejects_et_dst_gap_and_fold(day, clock, error):
    with pytest.raises(error):
        convert_et_to_channel_datetime(clock, ZONE, datetime(*day))
    assert isinstance(convert_et_to_channel_tz(clock, ZONE, datetime(*day)), str)


@pytest.mark.parametrize('day,zone,slots,expected', [
    ((2030, 3, 10), 'America/New_York', ['02:30', '08:30'], ('Mar 10, 2030', '8:30 AM')),
    ((2030, 11, 3), 'America/Chicago', ['02:30', '08:30'], ('Nov 3, 2030', '7:30 AM')),
])
def test_allocation_skips_unrepresentable_new_dst_candidate(tmp_path, day, zone, slots, expected):
    tracker = _qualify(ScheduleTracker(CHANNEL, tmp_path), zone=zone)
    assert _allocate(tracker, slots, datetime(*day), zone=zone) == expected


@pytest.mark.parametrize('date,clock,error', [
    ('Mar 10, 2030', '2:30 AM', pytz.NonExistentTimeError),
    ('Nov 3, 2030', '1:30 AM', pytz.AmbiguousTimeError),
])
def test_observed_ambiguous_wall_time_blocks_calendar(tmp_path, date, clock, error):
    tracker = ScheduleTracker(CHANNEL, tmp_path)
    rows = [_row(FIRST, date, clock)]
    assert tracker.sync_from_youtube(rows, inventory=_inventory(rows))
    with pytest.raises(error):
        tracker.bind_calendar_timezone(ZONE)
    assert tracker.calendar_ready is False


def test_empty_inventory_still_requires_real_timezone(tmp_path):
    tracker = ScheduleTracker(CHANNEL, tmp_path)
    assert tracker.sync_from_youtube([], inventory=_inventory([]))
    with pytest.raises(pytz.UnknownTimeZoneError):
        tracker.bind_calendar_timezone('Invalid/Zone')
    assert not tracker.calendar_ready


def test_unknown_claim_survives_reload_empty_inventory_and_partial_read(tmp_path):
    tracker = _qualify(ScheduleTracker(CHANNEL, tmp_path))
    tracker.reserve_slot(FIRST, DATE, '8:00 AM', ZONE)
    reloaded = ScheduleTracker(CHANNEL, tmp_path)
    assert reloaded.reservations == tracker.reservations
    with pytest.raises(ValueError, match='calendar_inventory_unqualified'):
        reloaded.bind_calendar_timezone(ZONE)
    _qualify(reloaded)
    assert reloaded.reservations[FIRST]['outcome'] == 'unknown'
    before = reloaded.tracker_file.read_bytes()
    partial = {**_inventory([]), 'status': 'partial'}
    assert reloaded.sync_from_youtube([], inventory=partial) is False
    assert not reloaded.calendar_ready
    assert reloaded.tracker_file.read_bytes() == before


def test_nonpersistent_preview_cannot_reserve_a_live_slot(tmp_path):
    tracker = _qualify(ScheduleTracker(CHANNEL, tmp_path, persist=False))
    with pytest.raises(ValueError, match='calendar_reservation_blocked'):
        tracker.reserve_slot(FIRST, DATE, '8:00 AM', ZONE)
    assert tracker.reservations == {} and not tracker.tracker_file.exists()


@pytest.mark.parametrize('change', [
    {'channel_id': 'other'}, {'channel_id': None}, {'schedule': []},
    {'schedule': {'Jan 5, 2099': True}}, {'schedule': {'Jan 5, 2099': -1}},
    {'video_ids': {'Jan 5, 2099': [42]}}, {'schedule': {'invalid': 1}},
    {'occupied_slots': [{'video_id': 'aaaaaaaaaaa', 'date': 'Jan 5, 2099'}]},
    {'reservations': {'aaaaaaaaaaa': {'outcome': 'verified'}}}, {'unknown_field': {}},
])
def test_corrupt_state_rejected_without_rewriting(tmp_path, change):
    tracker = ScheduleTracker(CHANNEL, tmp_path)
    data = {'channel_id': CHANNEL, 'schedule': {}, **change}
    original = json.dumps(data)
    tracker.tracker_file.write_text(original, encoding='utf-8')
    with pytest.raises(ValueError, match='tracker_state_unreadable'):
        ScheduleTracker(CHANNEL, tmp_path)
    with pytest.raises(ValueError):
        tracker.save()
    assert tracker.tracker_file.read_text(encoding='utf-8') == original


@pytest.mark.parametrize('raw', [
    '{"channel_id":"CHANNEL","schedule":{},"reservations":{},"reservations":{}}',
    '{"channel_id":"CHANNEL","schedule":{"Jan 5, 2099":1,"Jan 5, 2099":0}}',
    '{"channel_id":"CHANNEL","schedule":{"Jan 5, 2099":NaN}}',
    '{"schedule":{}}',
])
def test_duplicate_or_unbound_json_cannot_be_read_as_empty(tmp_path, raw):
    tracker = ScheduleTracker(CHANNEL, tmp_path)
    original = raw.replace('CHANNEL', CHANNEL)
    tracker.tracker_file.write_text(original, encoding='utf-8')
    with pytest.raises(ValueError, match='tracker_state_unreadable'):
        tracker._load()
    assert tracker.tracker_file.read_text(encoding='utf-8') == original


def test_legacy_channel_bound_history_loads_without_qualifying_live_calendar(tmp_path):
    tracker = ScheduleTracker(CHANNEL, tmp_path)
    tracker.tracker_file.write_text(json.dumps({'channel_id': CHANNEL, 'schedule': {DATE: 1},
                                               'video_ids': {DATE: ['legacy_fixture']}}), encoding='utf-8')
    tracker._load()
    assert tracker.get_count(DATE) == 1
    assert tracker.is_video_scheduled('legacy_fixture')
    assert not tracker.calendar_ready


def test_failed_replace_cleans_only_created_temp_and_keeps_prior_claim(tmp_path, monkeypatch):
    tracker = _qualify(ScheduleTracker(CHANNEL, tmp_path))
    tracker.reserve_slot(FIRST, DATE, '8:00 AM', ZONE)
    original = tracker.tracker_file.read_bytes()
    unrelated = tmp_path / 'unrelated.tmp'
    unrelated.write_bytes(b'keep')
    attempted = []

    def refuse(source, destination):
        attempted.append(source)
        raise PermissionError('synthetic replace refusal')

    with monkeypatch.context() as patch:
        patch.setattr(tracker_module.os, 'replace', refuse)
        with pytest.raises(PermissionError, match='synthetic replace refusal'):
            tracker.reserve_slot(SECOND, DATE, '12:00 PM', ZONE)
    assert len(attempted) == 1 and not attempted[0].exists()
    assert unrelated.read_bytes() == b'keep'
    assert tracker.tracker_file.read_bytes() == original
    assert set(tracker.reservations) == {FIRST}


def test_exclusive_create_collision_preserves_unowned_temp(tmp_path, monkeypatch):
    tracker = _qualify(ScheduleTracker(CHANNEL, tmp_path))
    other = tracker.tracker_file.with_suffix('.fixture.tmp')
    other.write_bytes(b'other owner')
    monkeypatch.setattr(tracker_module.uuid, 'uuid4', lambda: SimpleNamespace(hex='fixture'))
    with pytest.raises(FileExistsError):
        tracker.reserve_slot(FIRST, DATE, '8:00 AM', ZONE)
    assert other.read_bytes() == b'other owner'
    assert tracker.reservations == {}


def test_lost_replace_acknowledgment_retains_the_new_unknown(tmp_path, monkeypatch):
    tracker = _qualify(ScheduleTracker(CHANNEL, tmp_path))
    replace = tracker_module.os.replace

    def replace_then_fail(source, destination):
        replace(source, destination)
        raise OSError('synthetic lost replace acknowledgment')

    with monkeypatch.context() as patch:
        patch.setattr(tracker_module.os, 'replace', replace_then_fail)
        with pytest.raises(OSError, match='synthetic lost replace acknowledgment'):
            tracker.reserve_slot(THIRD, DATE, '8:00 AM', ZONE)
    assert tracker.reservations == {}
    assert ScheduleTracker(CHANNEL, tmp_path).reservations[THIRD]['outcome'] == 'unknown'
    with pytest.raises(ValueError, match='calendar_reservation_blocked'):
        tracker.reserve_slot(THIRD, DATE, '12:00 PM', ZONE)


def test_stale_tracker_cannot_reuse_durable_slot_or_erase_claim(tmp_path):
    writer = _qualify(ScheduleTracker(CHANNEL, tmp_path))
    stale = _qualify(ScheduleTracker(CHANNEL, tmp_path))
    writer.reserve_slot(FIRST, DATE, '8:00 AM', ZONE)
    with pytest.raises(ValueError, match='calendar_slot_occupied'):
        stale.reserve_slot(SECOND, DATE, '8:00 AM', ZONE)
    stale.save()
    assert ScheduleTracker(CHANNEL, tmp_path).reservations == writer.reservations


def test_nested_tracker_persistence_does_not_reacquire_native_lock(tmp_path, monkeypatch):
    entries = []

    @contextmanager
    def exclusive(identity, **_kwargs):
        assert not entries, 'nested native lock would block POSIX flock'
        entries.append(identity)
        yield

    monkeypatch.setattr(safety, 'runtime_operation_lock', exclusive)
    tracker = ScheduleTracker(CHANNEL, tmp_path)
    with channel_calendar_lock(CHANNEL):
        _qualify(tracker)
        tracker.reserve_slot(FIRST, DATE, '8:00 AM', ZONE)
    assert entries == ['youtube-schedule-channel:' + CHANNEL]


def test_inherited_task_context_cannot_reenter_calendar_lock(monkeypatch):
    entries = []

    @contextmanager
    def recursive_native_lock(identity, **_kwargs):
        entries.append(identity)
        yield

    async def contender():
        with pytest.raises(TimeoutError, match='scheduling_channel_busy'):
            with channel_calendar_lock(CHANNEL):
                raise AssertionError('child acquired its parent task lock')

    async def after_parent_exit():
        with channel_calendar_lock(CHANNEL):
            assert len(entries) == 3

    async def exercise():
        with channel_calendar_lock(CHANNEL):
            await asyncio.create_task(contender())
        with channel_calendar_lock(CHANNEL):
            delayed = asyncio.create_task(after_parent_exit())
        await delayed

    monkeypatch.setattr(safety, 'runtime_operation_lock', recursive_native_lock)
    asyncio.run(exercise())
    assert len(entries) == 3
