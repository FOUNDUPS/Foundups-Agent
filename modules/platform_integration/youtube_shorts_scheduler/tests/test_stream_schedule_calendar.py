"""Frozen stream selection and mandatory calendar boundaries with synthetic DOMs."""
import asyncio
import copy
import threading
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from modules.infrastructure.foundups_selenium.src.youtube_verification import VerificationHandoff
from modules.platform_integration.youtube_shorts_scheduler.src import schedule_inventory as inv
from modules.platform_integration.youtube_shorts_scheduler.src import schedule_tracker as tracker_owner
from modules.platform_integration.youtube_shorts_scheduler.src import video_policy as policy
from modules.platform_integration.youtube_shorts_scheduler.src.dom_automation import YouTubeStudioDOM
from modules.platform_integration.youtube_shorts_scheduler.src.scheduler import YouTubeShortsScheduler, scheduling_channel_lock
from modules.platform_integration.youtube_shorts_scheduler.src.content_page_scheduler import ContentPageScheduler

CHANNEL, VIDEO, OTHER = 'UC' + 'a' * 22, 'a' * 11, 'b' * 11
TITLE = 'Synthetic source stream'


def page(rows=None, **changes):
    return dict(channel_id=CHANNEL, url=f'https://studio.youtube.com/channel/{CHANNEL}/videos/short',
                chip_texts=['Visibility: Unlisted'], search_text='', loading=False,
                empty=False, previous_page=False, next_page=False,
                rows=rows if rows is not None else [row()], **changes)


def row(vid=VIDEO, title=TITLE):
    return {'video_id': vid, 'title': title, 'schedule_text': 'Unlisted'}


class Pages:
    def __init__(self, *pages):
        self.pages, self.index, self.driver = pages, 0, self

    def execute_script(self, _):
        value = self.pages[self.index]
        if isinstance(value, Exception):
            raise value
        return copy.deepcopy(value)

    def click_next_page(self):
        self.index += 1


def test_all_exact_title_matches_across_pages_only():
    first, second = page([row(), row('c' * 11, TITLE + ' extra')]), page([row(OTHER)])
    first['next_page'], second['previous_page'] = True, True
    result = inv.collect_unlisted_title_inventory(Pages(first, second), CHANNEL, TITLE)
    assert result['complete'] and result['video_ids'] == [VIDEO, OTHER]
    assert result['selection_basis'] == 'operator_title_rule'


@pytest.mark.parametrize('changes', [
    {'channel_id': 'UC' + 'b' * 22}, {'loading': True}, {'search_text': TITLE},
    {'previous_page': True}, {'next_page': None}, {'chip_texts': ['Has schedule']},
    {'chip_texts': ['Unlisted', 'Title contains demo']}, {'problem': 'duplicate'},
    {'problem': 'private'}, {'rows': []},
    {'url': f'https://studio.youtube.com/channel/{CHANNEL}/videos/upload'},
])
def test_title_scan_never_executes_partial_or_changed_scope(changes):
    source = page(); source.update(changes)
    if changes.get('problem') == 'duplicate': source['rows'] = [row(), row()]
    if changes.get('problem') == 'private': source['rows'] = [{**row(), 'schedule_text': 'Private'}]
    result = inv.collect_unlisted_title_inventory(Pages(source), CHANNEL, TITLE)
    assert result['complete'] is False and result['video_ids'] == []


def test_second_page_failure_discards_first_page_selection():
    source = page(); source['next_page'] = True
    result = inv.collect_unlisted_title_inventory(Pages(source, RuntimeError('unavailable')), CHANNEL, TITLE)
    assert result['complete'] is False and result['video_ids'] == []


@pytest.mark.parametrize('collector', [inv.collect_unlisted_title_inventory, inv.collect_scheduled_inventory])
def test_inventory_preserves_verification_handoff(collector):
    args = (TITLE,) if collector is inv.collect_unlisted_title_inventory else ()
    with pytest.raises(VerificationHandoff):
        collector(Pages(VerificationHandoff('verification_required')), CHANNEL, *args)


def bound_scheduler():
    owner = object.__new__(YouTubeShortsScheduler)
    owner.channel_id = CHANNEL
    owner.driver = SimpleNamespace()
    owner.request_driver = owner.driver
    owner.dom = SimpleNamespace(driver=owner.driver, check_driver_health=Mock(return_value=True))
    owner.stop_event = threading.Event()
    owner.stream_schedule_request = {'channel_id': CHANNEL, 'parent_video_id': OTHER,
        'stream_title': TITLE, 'expires_at_unix': time.time() + 1000, 'video_ids': [VIDEO]}
    return owner


@pytest.mark.parametrize('problem', ['expiry', 'channel', 'driver', 'dom_driver', 'stop', 'title', 'child'])
def test_frozen_request_guard_stops_changed_scope(problem):
    owner = bound_scheduler()
    session = SimpleNamespace(channel_id=CHANNEL, video_id=VIDEO, original={'title': TITLE})
    if problem == 'expiry': owner.stream_schedule_request['expires_at_unix'] = 1
    if problem == 'channel': owner.channel_id = 'UC' + 'b' * 22
    if problem == 'driver': owner.driver = SimpleNamespace()
    if problem == 'dom_driver': owner.dom.driver = SimpleNamespace()
    if problem == 'stop': owner.stop_event.set()
    if problem == 'title': session.original['title'] += ' changed'
    if problem == 'child': session.video_id = OTHER
    with pytest.raises(policy.PreSaveAuditBlocked): owner._guard_stream_request(session)


def test_request_never_reconnects_or_widens_private_flag(monkeypatch):
    owner = bound_scheduler()
    owner.reconnect_browser = Mock(side_effect=AssertionError('competing attachment'))
    owner.dom.check_driver_health.return_value = False
    assert owner.ensure_healthy_connection() is False
    monkeypatch.setenv('YT_SCHEDULE_INCLUDE_PRIVATE', '1')
    assert owner._resolve_visibility_targets() == ['UNLISTED']
    owner.reconnect_browser.assert_not_called()


@pytest.mark.parametrize('gate', ['YT_SHORTS_SCHEDULING_ENABLED', 'YT_AUTOMATION_ENABLED', 'STOP'])
def test_frozen_request_rechecks_operational_gates(monkeypatch, gate):
    from modules.communication.livechat.src import automation_gates
    owner = bound_scheduler()
    if gate == 'STOP': monkeypatch.setattr(automation_gates, 'stop_active', lambda _: True)
    else: monkeypatch.setenv(gate, 'false')
    with pytest.raises(policy.PreSaveAuditBlocked, match='gate_closed'):
        owner._guard_stream_request()


@pytest.mark.parametrize('labels,expected', [(['Asia/Tokyo'], True),
    (['(GMT+09:00) Tokyo'], True), (['(GMT-05:00) Eastern Time (US & Canada)'], False),
    (['GMT+09:00'], False), ([], False), (['Tokyo', 'Tokyo'], False), (['unknown'], False),
    (['(GMT-05:00) Tokyo'], False), (['(GMT+10:00) Tokyo'], False), (['(GMT+09:90) Tokyo'], False)])
def test_timezone_requires_observed_identity(labels, expected):
    dom = object.__new__(YouTubeStudioDOM)
    dom._policy_calendar_required, dom._policy_timezone = True, 'Asia/Tokyo'
    dom.driver = SimpleNamespace(execute_script=lambda _: labels)
    if expected:
        dom.verify_schedule_timezone()
        assert dom._schedule_timezone_verified is True
    else:
        with pytest.raises(policy.PreSaveAuditBlocked): dom.verify_schedule_timezone()


def test_reservation_is_at_guarded_save_boundary(monkeypatch):
    dom = object.__new__(YouTubeStudioDOM)
    session, order = SimpleNamespace(submitted=lambda: order.append('submitted'), requested_schedule={}), []
    dom._guard_policy_save = lambda: session
    dom._policy_scheduling = dom._policy_calendar_required = dom._schedule_timezone_verified = True
    dom._schedule_picker_verified = {}
    dom._policy_before_schedule_submit = lambda s: order.append('reservation')
    dom._policy_on_schedule_submitting = lambda s: order.append('attempt')
    monkeypatch.setattr(policy, 'require_public_gate', lambda: order.append('gate'))
    monkeypatch.setattr(policy, 'claim_save', lambda s: order.append('claim'))
    dom._submit_policy_save(lambda: order.append('effect'))
    assert order == ['gate', 'reservation', 'claim', 'submitted', 'attempt', 'effect']


def test_refused_claim_keeps_reservation_but_does_not_report_submission(monkeypatch):
    dom = object.__new__(YouTubeStudioDOM)
    session, order = SimpleNamespace(submitted=lambda: order.append('submitted'), requested_schedule={}), []
    dom._guard_policy_save = lambda: session
    dom._policy_scheduling = dom._policy_calendar_required = dom._schedule_timezone_verified = True
    dom._schedule_picker_verified = {}
    dom._policy_before_schedule_submit = lambda s: order.append('reservation')
    dom._policy_on_schedule_submitting = lambda s: order.append('attempt')
    monkeypatch.setattr(policy, 'require_public_gate', lambda: None)
    monkeypatch.setattr(policy, 'claim_save', Mock(side_effect=policy.VideoPolicyBlocked('already_claimed')))
    with pytest.raises(policy.VideoPolicyBlocked):
        dom._submit_policy_save(lambda: order.append('effect'))
    assert order == ['reservation']


def test_failed_reservation_never_claims_or_submits(monkeypatch):
    dom = object.__new__(YouTubeStudioDOM)
    dom._guard_policy_save = lambda: SimpleNamespace(requested_schedule={})
    dom._policy_scheduling = dom._policy_calendar_required = dom._schedule_timezone_verified = True
    dom._schedule_picker_verified = {}
    dom._policy_before_schedule_submit = Mock(side_effect=OSError('durability unavailable'))
    monkeypatch.setattr(policy, 'require_public_gate', lambda: None)
    claim, effect = Mock(), Mock()
    monkeypatch.setattr(policy, 'claim_save', claim)
    with pytest.raises(OSError): dom._submit_policy_save(effect)
    claim.assert_not_called(); effect.assert_not_called()


def test_timezone_handoff_is_not_reclassified_as_generic_failure():
    dom = object.__new__(YouTubeStudioDOM)
    dom._policy_calendar_required, dom._policy_timezone = True, 'Asia/Tokyo'
    dom.driver = SimpleNamespace(execute_script=Mock(side_effect=VerificationHandoff('verification_required')))
    with pytest.raises(VerificationHandoff): dom.verify_schedule_timezone()


@pytest.mark.parametrize('changes,valid', [({}, True), ({'date': 'Nov 11, 2099'}, False),
    ({'time': '8:15 AM'}, False), ({'selected': False}, False), ({'invalid': True}, False),
    ({'date': ''}, False), ({'time': None}, False)])
def test_committed_picker_values_must_match_reserved_intent(changes, valid):
    dom = object.__new__(YouTubeStudioDOM)
    dom._policy_calendar_required = True
    wanted = {'date': 'Nov 10, 2099', 'time': '8:00 AM', 'timezone': 'Asia/Tokyo', 'visibility': 'scheduled'}
    dom._policy_edit = lambda: SimpleNamespace(requested_schedule=wanted)
    observed = {'date': wanted['date'], 'time': wanted['time'], 'selected': True, 'invalid': False}
    observed.update(changes)
    dom.driver = SimpleNamespace(execute_script=lambda _: observed)
    if valid:
        dom.verify_schedule_picker()
        assert dom._schedule_picker_verified == wanted
    else:
        with pytest.raises(policy.PreSaveAuditBlocked): dom.verify_schedule_picker()
        assert dom._schedule_picker_verified is None


@pytest.mark.parametrize('zone', ['pst', 'JST', 'UTC+09:00', 'America/New_York'])
@pytest.mark.parametrize('cell', ['schedule_text', 'date_text', 'date_label'])
def test_scheduled_row_timezone_is_never_silently_discarded(zone, cell):
    candidate = {'video_id': VIDEO, 'schedule_text': 'Scheduled'}
    candidate[cell] = 'Scheduled Nov 10, 2099 8:00 AM (' + zone + ')'
    assert inv.parse_scheduled_row(candidate) is None


@pytest.mark.parametrize('found', [True, False])
def test_calendar_done_never_falls_back_to_unguarded_dialog_save(found):
    dom = object.__new__(YouTubeStudioDOM)
    dom._policy_calendar_required = True
    dom._guard_policy_save = Mock()
    dom.verify_schedule_timezone = Mock()
    dom.verify_schedule_picker = Mock()
    done = object() if found else None
    dom.driver = SimpleNamespace(execute_script=Mock(return_value=done))
    dom.safe_click = Mock()
    dom.wait_for_clickable = Mock(side_effect=AssertionError('generic Save fallback'))
    if found:
        dom.click_done()
        dom.safe_click.assert_called_once_with(done)
    else:
        with pytest.raises(policy.PreSaveAuditBlocked): dom.click_done()
        dom.safe_click.assert_not_called()
    dom.wait_for_clickable.assert_not_called()


def test_save_handoff_never_falls_through_to_second_candidate(monkeypatch):
    dom = object.__new__(YouTubeStudioDOM)
    monkeypatch.setattr('time.sleep', lambda _: None)
    dom.driver = SimpleNamespace(find_elements=lambda *_: [], execute_script=lambda *_: None)
    button = SimpleNamespace(click=lambda: None)
    dom.wait_for_clickable = Mock(return_value=button)
    dom._submit_policy_save = Mock(side_effect=VerificationHandoff('verification_required'))
    with pytest.raises(VerificationHandoff): dom.click_save()
    dom.wait_for_clickable.assert_called_once()
    dom._submit_policy_save.assert_called_once()


@pytest.mark.parametrize('changes,clean', [({}, True), ({'save_disabled': False}, False),
    ({'prompt_open': True}, False), ({'title': 'Foreign edit'}, False)])
def test_clean_editor_allows_handoff_without_claiming_delivery(changes, clean):
    dom = object.__new__(YouTubeStudioDOM)
    snapshot = {'channel_id': CHANNEL, 'url': f'https://studio.youtube.com/video/{VIDEO}/edit',
                'title': TITLE, 'description': 'Synthetic description', 'permission': 'observed',
                'save_disabled': True, 'prompt_open': False}
    original = dict(snapshot)
    snapshot.update(changes)
    session = policy.EditSession.capture(original, CHANNEL, VIDEO)
    session.submitting, session.window_handle = True, 'same'
    dom._policy_edit = lambda: session
    dom.driver = SimpleNamespace(current_window_handle='same', execute_script=lambda _: snapshot)
    assert dom.schedule_editor_clean_after_submit() is clean


@pytest.mark.parametrize('sync_result', [False, 'handoff', True])
def test_live_selected_cycle_requires_calendar_and_clears_readiness(tmp_path, monkeypatch, sync_result):
    monkeypatch.setattr(tracker_owner, 'TRACKER_DIR', tmp_path)
    owner = bound_scheduler()
    owner.dry_run = False
    owner.tracker = tracker_owner.ScheduleTracker(CHANNEL, tmp_path)
    owner.dom.begin_policy_cycle = Mock()
    async def sync():
        owner.tracker.calendar_ready = True
        if sync_result == 'handoff': raise VerificationHandoff('verification_required')
        return sync_result
    owner._sync_scheduled_videos = AsyncMock(side_effect=sync)
    owner._run_scheduling_cycle = AsyncMock(return_value={'submitted_ids': [VIDEO]})
    if sync_result == 'handoff':
        with pytest.raises(VerificationHandoff): asyncio.run(owner.run_scheduling_cycle(video_ids=[VIDEO]))
    else:
        result = asyncio.run(owner.run_scheduling_cycle(video_ids=[VIDEO]))
        assert result['status'] == ('unknown' if sync_result else 'blocked')
        assert owner._run_scheduling_cycle.await_count == int(bool(sync_result))
    assert not owner.tracker.calendar_ready
    owner._sync_scheduled_videos.assert_awaited_once()


def test_concurrent_channel_cycle_is_refused_and_released():
    with scheduling_channel_lock(CHANNEL):
        with pytest.raises(TimeoutError):
            with scheduling_channel_lock(CHANNEL): pass
    with scheduling_channel_lock(CHANNEL): pass


def test_legacy_unknown_without_slot_blocks_allocation(monkeypatch):
    from modules.communication.livechat.src import operator_command_queue as queue
    owner = bound_scheduler()
    owner.channel_key, owner.channel_tz = 'synthetic', 'Asia/Tokyo'
    calendar_page = page([])
    calendar_page.update(chip_texts=['Has schedule'], empty=True)
    inventory = inv.collect_scheduled_inventory(Pages(calendar_page), CHANNEL)
    assert inv.qualified_inventory(inventory, CHANNEL)
    owner.dom.read_scheduled_inventory = Mock(return_value=inventory)
    owner.tracker = SimpleNamespace(reservations={}, sync_from_youtube=Mock())
    monkeypatch.setattr(ContentPageScheduler, 'navigate_to_scheduled', lambda *_: True)
    monkeypatch.setattr(queue, 'get_unresolved_scheduling_claims', lambda _: [{'video_id': VIDEO}])
    assert asyncio.run(owner._sync_scheduled_videos()) is False
    owner.tracker.sync_from_youtube.assert_not_called()
