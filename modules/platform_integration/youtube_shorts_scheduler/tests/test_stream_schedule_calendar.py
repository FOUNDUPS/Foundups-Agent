"""Frozen stream selection and mandatory calendar boundaries with synthetic DOMs."""
import asyncio
import copy
import threading
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from urllib.parse import parse_qs, urlsplit
import json

import pytest
from selenium.common.exceptions import TimeoutException

from modules.infrastructure.foundups_selenium.src.youtube_verification import VerificationHandoff
from modules.platform_integration.youtube_shorts_scheduler.src import schedule_inventory as inv
from modules.platform_integration.youtube_shorts_scheduler.src import schedule_tracker as tracker_owner
from modules.platform_integration.youtube_shorts_scheduler.src import video_policy as policy
from modules.platform_integration.youtube_shorts_scheduler.src.dom_automation import YouTubeStudioDOM, DOMSelectors
from modules.platform_integration.youtube_shorts_scheduler.src.scheduler import YouTubeShortsScheduler, scheduling_channel_lock
from modules.platform_integration.youtube_shorts_scheduler.src.content_page_scheduler import ContentPageScheduler

CHANNEL, VIDEO, OTHER = 'UC' + 'a' * 22, 'a' * 11, 'b' * 11
TITLE = 'Synthetic source stream'


@pytest.mark.parametrize('observed,expected,verified', [
    (TITLE, TITLE, True), (TITLE + ' changed', TITLE, False),
    (TITLE, '', False), (TITLE, 12, False)])
def test_recorded_parent_title_is_observed_not_assumed(observed, expected, verified):
    from modules.platform_integration.youtube_shorts_scheduler.src.channel_config import verify_schedule_target_access
    driver = SimpleNamespace(execute_script=lambda script: {
        'channel_id': CHANNEL, 'url': f'https://studio.youtube.com/video/{VIDEO}/edit',
        'title': observed, 'description': 'Synthetic description', 'permission': 'observed'})
    result = verify_schedule_target_access(driver, CHANNEL, VIDEO, expected_title=expected)
    assert result['verified'] is verified


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

    def click_next_page(self, *, expected_page=None):
        assert expected_page == self.pages[self.index]
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


def test_pagination_timeout_reports_stage_without_exposing_exception_text():
    source = page(); source['next_page'] = True
    dom = Pages(source)
    dom.click_next_page = Mock(side_effect=TimeoutException(TITLE))
    result = inv.collect_unlisted_title_inventory(dom, CHANNEL, TITLE)
    assert result['reason'] == 'pagination_failed' and result['video_ids'] == []
    assert result['diagnostics']['failure_type'] == 'TimeoutException'
    assert TITLE not in json.dumps(result['diagnostics'])


@pytest.mark.parametrize('case', ['advance', 'disabled', 'missing', 'unchanged', 'scope_changed', 'handoff',
    'drift_channel', 'drift_rows', 'drift_filter', 'drift_route'])
def test_native_pagination_clicks_observed_control_once_and_requires_changed_rows(monkeypatch, case):
    from modules.platform_integration.youtube_shorts_scheduler.src import dom_automation
    control = Mock()
    before = page(); before.update(next_page=True, next_control=control)
    witness = dict(before)
    if case == 'drift_channel': before['channel_id'] = 'UC' + 'b' * 22
    if case == 'drift_rows': before['rows'] = [row(OTHER)]
    if case == 'drift_filter': before['chip_texts'] = ['Has schedule']
    if case == 'drift_route': before['url'] = before['url'].replace('/short', '/upload')
    after = page([row(OTHER)]); after.update(previous_page=True)
    if case == 'disabled': before['next_page'] = False
    if case == 'missing': before['next_control'] = None
    if case == 'unchanged': after['rows'] = before['rows']
    if case == 'scope_changed': after['channel_id'] = 'UC' + 'b' * 22
    if case == 'handoff': control.click.side_effect = VerificationHandoff('verification_required')
    dom = object.__new__(YouTubeStudioDOM)
    dom.driver = SimpleNamespace(execute_script=Mock(side_effect=[before, after]))
    dom.wait_for_clickable = Mock(side_effect=AssertionError('legacy selector'))
    dom.safe_click = Mock(side_effect=AssertionError('retrying fallback'))
    class Wait:
        def __init__(self, *_args): pass
        def until(self, predicate):
            if not predicate(dom.driver): raise TimeoutException('rows unchanged')
    monkeypatch.setattr(dom_automation, 'WebDriverWait', Wait)
    if case == 'advance':
        dom.click_next_page(expected_page=witness)
    else:
        expected = VerificationHandoff if case == 'handoff' else TimeoutException if case == 'unchanged' else RuntimeError
        with pytest.raises(expected): dom.click_next_page(expected_page=witness)
    assert control.click.call_count == (0 if case in {'disabled', 'missing'} or case.startswith('drift_') else 1)
    dom.safe_click.assert_not_called()
    dom.wait_for_clickable.assert_not_called()


@pytest.mark.parametrize('changes,reason', [
    ({'channel_id': None}, 'receiving_channel_unverified'),
    ({'url': f'https://studio.youtube.com/channel/{CHANNEL}/videos/upload'}, 'shorts_route_unverified'),
    ({'loading': True}, 'page_loading'),
    ({'search_text': TITLE}, 'unexpected_search_filter'),
    ({'previous_page': None}, 'pagination_position_unverified'),
    ({'chip_texts': []}, 'unlisted_filter_unverified'),
    ({'rows': []}, 'page_rows_unqualified'),
    ({'rows': [{'video_id': VIDEO, 'title': TITLE, 'schedule_text': 'Private'}]}, 'unlisted_row_unqualified'),
    ({'next_page': None}, 'pagination_unverified'),
])
def test_inventory_diagnosis_is_specific_and_content_free(changes, reason):
    observed = page(); observed.update(changes)
    result = inv.collect_unlisted_title_inventory(Pages(observed), CHANNEL, TITLE)
    assert not result['complete'] and result['video_ids'] == []
    assert result['reason'] == reason
    diagnostic_text = json.dumps(result['diagnostics'])
    assert all(value not in diagnostic_text for value in (CHANNEL, VIDEO, TITLE, 'studio.youtube.com'))
    assert result['diagnostics']['pages_read'] == 1


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


def navigation_scheduler(monkeypatch, observed):
    owner = bound_scheduler()
    owner.channel_name = 'Synthetic channel'
    driver = SimpleNamespace(get=Mock(), execute_script=Mock(return_value=observed))
    dom = object.__new__(YouTubeStudioDOM)
    dom.selectors = DOMSelectors()
    dom.driver, dom.wait_for_element = driver, Mock(return_value=object())
    owner.driver = owner.request_driver = driver
    owner.dom = dom
    monkeypatch.setattr(ContentPageScheduler, 'navigate_to_content',
                        Mock(side_effect=AssertionError('obsolete sidebar route')))
    return owner


@pytest.mark.parametrize('empty', [False, True])
def test_stream_discovery_uses_unlisted_shorts_url_and_qualified_readback(monkeypatch, empty):
    observed = page()
    if empty:
        observed.update(rows=[], empty=True)
    owner = navigation_scheduler(monkeypatch, observed)
    if empty:
        owner.dom.wait_for_element.side_effect = TimeoutException('no row')
    result = owner.discover_stream_title_batch(TITLE)
    assert result['complete'] and result['video_ids'] == ([] if empty else [VIDEO])
    url = urlsplit(owner.driver.get.call_args.args[0])
    assert url.netloc == 'studio.youtube.com' and url.path == f'/channel/{CHANNEL}/videos/short'
    assert json.loads(parse_qs(url.query)['filter'][0]) == [{'name': 'VISIBILITY', 'value': ['UNLISTED']}]
    owner.driver.get.assert_called_once()


@pytest.mark.parametrize('changes', [
    {'chip_texts': []}, {'chip_texts': ['Has schedule']}, {'channel_id': 'UC'+'b'*22},
    {'url': f'https://studio.youtube.com/video/{OTHER}/edit'}, {'loading': True}, {'next_page': None}])
def test_stream_url_does_not_bless_unqualified_page(monkeypatch, changes):
    observed = page(); observed.update(changes)
    owner = navigation_scheduler(monkeypatch, observed)
    result = owner.discover_stream_title_batch(TITLE)
    assert not result['complete'] and result['video_ids'] == []


@pytest.mark.parametrize('stage', ['get', 'wait'])
def test_stream_url_preserves_verification_handoff_before_collection(monkeypatch, stage):
    owner = navigation_scheduler(monkeypatch, page())
    effect = owner.driver.get if stage == 'get' else owner.dom.wait_for_element
    effect.side_effect = VerificationHandoff('verification_required')
    with pytest.raises(VerificationHandoff):
        owner.discover_stream_title_batch(TITLE)
    owner.driver.execute_script.assert_not_called()


def test_stream_navigation_rechecks_stop_before_collection(monkeypatch):
    owner = navigation_scheduler(monkeypatch, page())
    owner.driver.get.side_effect = lambda _: owner.stop_event.set()
    with pytest.raises(policy.PreSaveAuditBlocked, match='stopped'):
        owner.discover_stream_title_batch(TITLE)
    owner.driver.execute_script.assert_not_called()


def test_selected_stream_navigation_never_uses_model_fallback(monkeypatch):
    owner = navigation_scheduler(monkeypatch, page([row(), row('c'*11)]))
    owner.dry_run = True
    owner.tracker = SimpleNamespace(reservations={VIDEO: {}})
    owner.dom.navigate_to_shorts_with_fallback = Mock(side_effect=AssertionError('model fallback'))
    owner.dom.read_visibility_filter_state = Mock(side_effect=AssertionError('legacy proof'))
    owner.dom.set_page_size = Mock(side_effect=AssertionError('legacy page sizing'))
    owner._collect_selected_rows = AsyncMock(side_effect=AssertionError('legacy scrape'))
    monkeypatch.setattr(asyncio, 'sleep', AsyncMock())
    result = {'errors': [], 'skipped': []}
    assert asyncio.run(owner._run_visibility_pass('UNLISTED', 1, False, result, [VIDEO])) is False
    assert result['skipped'] == [{'video_id': VIDEO, 'reason': 'schedule_outcome_unknown'}]
    owner.driver.get.assert_called_once()
    owner.dom.navigate_to_shorts_with_fallback.assert_not_called()


def test_selected_stream_navigation_refuses_other_visibility(monkeypatch):
    owner = navigation_scheduler(monkeypatch, page())
    with pytest.raises(policy.PreSaveAuditBlocked, match='visibility_changed'):
        asyncio.run(owner._run_visibility_pass('PRIVATE', 1, False, {'errors': []}, [VIDEO]))
    owner.driver.get.assert_not_called()


@pytest.mark.parametrize('problem', ['missing_chip', 'missing_selected', 'changed_title', 'outside_frozen'])
def test_selected_stream_reentry_requires_complete_frozen_identity(monkeypatch, problem):
    observed = page()
    if problem == 'missing_chip': observed['chip_texts'] = []
    if problem == 'missing_selected': observed['rows'] = [row('c'*11)]
    if problem == 'changed_title': observed['rows'] = [row(VIDEO, TITLE + ' changed')]
    if problem == 'outside_frozen': observed['rows'] = [row('c'*11)]
    owner = navigation_scheduler(monkeypatch, observed)
    selected = ['c'*11] if problem == 'outside_frozen' else [VIDEO]
    result = {'errors': []}
    assert asyncio.run(owner._run_visibility_pass('UNLISTED', 1, False, result, selected)) is True
    assert result['errors'] == [{'error': 'Frozen selection not completely observed'}]


def test_selected_stream_reentry_preserves_readback_verification_handoff(monkeypatch):
    owner = navigation_scheduler(monkeypatch, page())
    owner.driver.execute_script.side_effect = VerificationHandoff('verification_required')
    with pytest.raises(VerificationHandoff):
        asyncio.run(owner._run_visibility_pass('UNLISTED', 1, False, {'errors': []}, [VIDEO]))


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


@pytest.mark.parametrize('video,metadata,allowed', [(VIDEO, False, True),
    (OTHER, False, False), (VIDEO, True, False), (VIDEO, None, False)])
def test_first_test_guard_confines_effect_to_first_id_with_preserved_metadata(video, metadata, allowed):
    owner = bound_scheduler()
    owner.stream_schedule_request.update(first_test_only=True, video_ids=[VIDEO, OTHER])
    session = SimpleNamespace(channel_id=CHANNEL, video_id=video,
                              original={'title': TITLE}, allow_metadata=metadata)
    if allowed:
        owner._guard_stream_request(session)
    else:
        with pytest.raises(policy.PreSaveAuditBlocked):
            owner._guard_stream_request(session)


def test_parent_is_never_a_clip_target_even_if_selection_contains_it():
    owner = bound_scheduler()
    owner.stream_schedule_request.update(first_test_only=True, parent_video_id=VIDEO)
    session = SimpleNamespace(channel_id=CHANNEL, video_id=VIDEO,
                              original={'title': TITLE}, allow_metadata=False)
    with pytest.raises(policy.PreSaveAuditBlocked, match='child_changed'):
        owner._guard_stream_request(session)


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


# Native pending-request inspection: no intake, claims or real browser work.
@pytest.fixture
def native_request_inspection(tmp_path, monkeypatch):
    from contextlib import contextmanager
    from types import ModuleType
    import sys
    from modules.platform_integration.youtube_shorts_scheduler import cli
    from modules.communication.livechat.src import automation_gates, operator_command_queue
    from modules.communication.livechat.src import operator_stream_schedule_owner as stream_owner
    from modules.infrastructure.shared_utilities import youtube_channel_registry

    monkeypatch.setenv('YT_AUTOMATION_STOP_FILE', str(tmp_path / 'STOP'))
    monkeypatch.setenv('YT_AUTOMATION_ENABLED', 'true')
    monkeypatch.setenv('YT_SHORTS_SCHEDULING_ENABLED', 'true')
    queue = operator_command_queue.OperatorCommandQueue(None, tmp_path / 'inbox.json',
        tmp_path / 'ack.json', tmp_path / 'state.json')
    commands = [{'id': 'inspect-recorded', 'action': stream_owner.ACTION, 'payload': {
        'recorded_source': {'channel_id': CHANNEL, 'parent_video_id': OTHER, 'stream_title': TITLE},
        'first_test_only': True}},
        {'id': 'unrelated-announcement', 'action': 'announce', 'payload': {'message': 'Fixture only'}}]
    queue.command_path.write_text(json.dumps({'version': 1, 'commands': commands}))
    calls = []
    settings = SimpleNamespace(busy=False, registered=True, role=True, ports=[9222],
        native_result={'inspection_only': True, 'stream_schedule_requests': [
            {'status': 'inspected', 'reason': 'inventory_incomplete',
             'inventory_complete': False, 'matching_count': 0, 'diagnostics': {'pages_read': 1}}]})

    @contextmanager
    def lease():
        if settings.busy:
            raise TimeoutError('owner_busy')
        calls.append('lease')
        try:
            yield
        finally:
            calls.append('released')

    def launch(**kwargs):
        assert calls == ['lease']
        assert kwargs['stream_schedule_inspect_only'] is True
        assert kwargs['browser'] == 'chrome' and kwargs['mode'] == 'schedule'
        assert kwargs['max_per_channel'] == 1
        requests = kwargs['stream_schedule_requests']
        assert len(requests) == 1 and requests[0]['id'] == 'inspect-recorded'
        calls.append('native_inspection')
        return copy.deepcopy(settings.native_result)

    module_name = 'modules.platform_integration.youtube_shorts_scheduler.scripts.launch'
    native = ModuleType(module_name)
    native.run_multi_channel_scheduler = launch
    native.BROWSER_PORTS = {'chrome': 9222, 'edge': 9223}
    monkeypatch.setitem(sys.modules, module_name, native)
    monkeypatch.setattr(automation_gates, 'youtube_runtime_owner', lease)
    monkeypatch.setattr(operator_command_queue, 'OperatorCommandQueue', lambda _: queue)
    monkeypatch.setattr(youtube_channel_registry, 'get_channel_by_id', lambda channel: (
        {'roles': {'shorts': settings.role}, 'browser': {'available_ports': settings.ports}}
        if settings.registered and channel == CHANNEL else None))
    return cli, queue, calls, settings, stream_owner


def _inspection_bytes(queue):
    return [path.read_bytes() if path.exists() else None for path in
            (queue.command_path, queue.acknowledgement_path, queue.state_path)]


def _deny_inspection_mutators(queue, monkeypatch):
    refresh = AsyncMock(side_effect=AssertionError('inspection must not consume command'))
    claim = Mock(side_effect=AssertionError('inspection must not claim'))
    finish = Mock(side_effect=AssertionError('inspection must not finish'))
    monkeypatch.setattr(queue, 'refresh_stream_schedule_request', refresh)
    monkeypatch.setattr(queue, 'claim_stream_schedule_request', claim)
    monkeypatch.setattr(queue, 'finish_stream_schedule_request', finish)
    return refresh, claim, finish


def test_native_cli_inspection_reads_accepted_pending_request_without_queue_writes(native_request_inspection, monkeypatch):
    cli, queue, calls, _, _ = native_request_inspection
    assert asyncio.run(queue.refresh_stream_schedule_request('inspect-recorded', recorded_only=True))
    before = _inspection_bytes(queue)
    denied = _deny_inspection_mutators(queue, monkeypatch)
    result = cli.run_operator_request('inspect-recorded', 'chrome', inspect_only=True)
    assert calls == ['lease', 'native_inspection', 'released']
    assert result['status'] == 'request_inspected' and result['inspection_only'] is True
    assert result['scheduling_verified'] is False and result['success'] is False
    assert result['receipt']['execution_status'] == 'pending'
    assert queue.inspect_command('unrelated-announcement')['received'] is False
    assert _inspection_bytes(queue) == before
    for mock in denied:
        mock.assert_not_called()


@pytest.mark.parametrize('native_result', [
    {'inspection_only': True, 'stream_schedule_requests': [
        {'status': 'pending', 'reason': 'same_target_access_unverified'}]},
    {'error': 'browser_attachment_failed'},
])
def test_native_cli_inspection_does_not_claim_collector_ran_when_native_owner_blocked(
        native_request_inspection, monkeypatch, native_result):
    cli, queue, _, settings, _ = native_request_inspection
    assert asyncio.run(queue.refresh_stream_schedule_request('inspect-recorded', recorded_only=True))
    settings.native_result = native_result
    before = _inspection_bytes(queue)
    denied = _deny_inspection_mutators(queue, monkeypatch)
    result = cli.run_operator_request('inspect-recorded', 'chrome', inspect_only=True)
    assert result['status'] == 'inspection_blocked' and result['inspection_only'] is True
    assert result['scheduling_verified'] is False and result['success'] is False
    assert _inspection_bytes(queue) == before
    for mock in denied:
        mock.assert_not_called()


@pytest.mark.parametrize('state', ['unseen', 'expired'])
def test_native_cli_inspection_refuses_unseen_or_expired_without_consuming(native_request_inspection, monkeypatch, state):
    cli, queue, calls, _, stream_owner = native_request_inspection
    if state == 'expired':
        request = asyncio.run(queue.refresh_stream_schedule_request('inspect-recorded', recorded_only=True))
        monkeypatch.setattr(stream_owner.time, 'time', lambda: request['expires_at_unix'] + 1)
    before = _inspection_bytes(queue)
    denied = _deny_inspection_mutators(queue, monkeypatch)
    result = cli.run_operator_request('inspect-recorded', 'chrome', inspect_only=True)
    assert result['status'] == 'request_not_pending'
    assert calls == ['lease', 'released'] and _inspection_bytes(queue) == before
    for mock in denied:
        mock.assert_not_called()


@pytest.mark.parametrize('gate', ['busy', 'missing', 'role', 'port', 'stop', 'disabled'])
def test_native_cli_inspection_retains_owner_and_operational_gates(native_request_inspection, monkeypatch, gate):
    cli, queue, calls, settings, _ = native_request_inspection
    assert asyncio.run(queue.refresh_stream_schedule_request('inspect-recorded', recorded_only=True))
    before = _inspection_bytes(queue)
    _deny_inspection_mutators(queue, monkeypatch)
    if gate == 'busy': settings.busy = True
    if gate == 'missing': settings.registered = False
    if gate == 'role': settings.role = False
    if gate == 'port': settings.ports = [9223]
    if gate == 'stop': monkeypatch.setattr('modules.communication.livechat.src.automation_gates.stop_active', lambda _: True)
    if gate == 'disabled': monkeypatch.setenv('YT_SHORTS_SCHEDULING_ENABLED', 'false')
    if gate == 'busy':
        with pytest.raises(TimeoutError):
            cli.run_operator_request('inspect-recorded', 'chrome', inspect_only=True)
    else:
        assert cli.run_operator_request('inspect-recorded', 'chrome', inspect_only=True)['success'] is False
    assert 'native_inspection' not in calls and _inspection_bytes(queue) == before


def test_native_cli_inspection_flag_routes_to_read_only_request_owner(monkeypatch, capsys):
    from modules.platform_integration.youtube_shorts_scheduler import cli
    import dotenv
    monkeypatch.setattr(dotenv, 'load_dotenv', lambda *_args, **_kwargs: None)
    call = Mock(return_value={'status': 'request_inspected', 'inspection_only': True,
                              'scheduling_verified': False, 'success': False})
    monkeypatch.setattr(cli, 'run_operator_request', call)
    assert cli.main(['--request-id', 'synthetic', '--browser', 'chrome', '--inspect-request']) == 2
    call.assert_called_once_with('synthetic', 'chrome', inspect_only=True)
    assert json.loads(capsys.readouterr().out)['inspection_only'] is True


@pytest.mark.parametrize('arguments', [
    ['--inspect-request'], ['--inspect-request', '--browser', 'chrome'],
    ['--inspect-request', '--request-id', 'synthetic'],
    *[['--inspect-request', '--request-id', 'synthetic', '--browser', 'chrome', *extra]
      for extra in (['--dry-run'], ['--preflight'], ['--channel', 'fixture'],
                    ['--max-videos', '1'], ['--video-ids', VIDEO], ['--preserve-metadata'],
                    ['--list-channels'])],
])
def test_native_cli_inspection_rejects_missing_identity_or_conflicting_modes(monkeypatch, arguments):
    from modules.platform_integration.youtube_shorts_scheduler import cli
    invoked = Mock()
    monkeypatch.setattr(cli, 'run_operator_request', invoked)
    with pytest.raises(SystemExit) as caught:
        cli.main(arguments)
    assert caught.value.code == 2
    invoked.assert_not_called()
