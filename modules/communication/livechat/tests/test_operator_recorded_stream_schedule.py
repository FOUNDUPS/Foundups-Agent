"""Recorded-source intake only, using real queue owners and disposable files."""
import asyncio
import json
import time
from types import SimpleNamespace

import pytest

from modules.communication.livechat.src import operator_stream_schedule_owner as owner
from modules.communication.livechat.src.operator_command_queue import (
    OperatorCommandQueue, enqueue_operator_command,
)

CHANNEL = 'UC' + 'a' * 22
PARENT = 'p' * 11
SHORT = 's' * 11
OTHER = 't' * 11
SOURCE = {'channel_id': CHANNEL, 'parent_video_id': PARENT,
          'stream_title': 'Fixture recorded stream exact title'}


@pytest.fixture(autouse=True)
def gates(tmp_path, monkeypatch):
    monkeypatch.setenv('YT_AUTOMATION_STOP_FILE', str(tmp_path / 'STOP'))
    monkeypatch.setenv('YT_AUTOMATION_ENABLED', 'true')
    monkeypatch.setenv('YT_SHORTS_SCHEDULING_ENABLED', 'true')


def command(identity='recorded-1', **payload):
    return {'id': identity, 'action': owner.ACTION, 'payload': payload or {
        'recorded_source': dict(SOURCE), 'first_test_only': True}}


def queue(tmp_path, commands):
    result = OperatorCommandQueue(None, tmp_path / 'inbox.json',
        tmp_path / 'ack.json', tmp_path / 'state.json', poll_interval_seconds=0)
    result.command_path.write_text(json.dumps({'version': 1, 'commands': commands}))
    return result


def refresh(result, identity='recorded-1', **kwargs):
    return asyncio.run(result.refresh_stream_schedule_request(identity, **kwargs))


def test_recorded_source_is_explicit_and_never_invents_live_session(tmp_path):
    result = queue(tmp_path, [command()])
    request = refresh(result, recorded_only=True)
    assert request['source_kind'] == 'recorded' and request['first_test_only'] is True
    assert request['session_id'] == request['live_chat_id'] == ''
    assert {key: request[key] for key in SOURCE} == SOURCE
    assert request['execution_status'] == 'pending'
    inspected = result.inspect_command(request['id'])
    assert inspected['delivery_verified'] is False and inspected['first_test_only'] is True
    assert inspected['withheld_count'] == inspected['submission_recorded_count'] == 0
    assert not set(SOURCE) & set(inspected)
    assert refresh(result) == request
    request['stream_title'] = 'Caller mutation'
    assert refresh(result)['stream_title'] == SOURCE['stream_title']


@pytest.mark.parametrize('payload', [
    {'recorded_source': SOURCE}, {'first_test_only': True},
    {'recorded_source': SOURCE, 'first_test_only': False},
    {'recorded_source': SOURCE, 'first_test_only': 1},
    {'recorded_source': None, 'first_test_only': True},
    {'recorded_source': {**SOURCE, 'session_id': 'invented'}, 'first_test_only': True},
    {'recorded_source': {**SOURCE, 'channel_id': 'name'}, 'first_test_only': True},
    {'recorded_source': {**SOURCE, 'parent_video_id': 'name'}, 'first_test_only': True},
    {'recorded_source': {**SOURCE, 'stream_title': ''}, 'first_test_only': True},
    {'recorded_source': {**SOURCE, 'stream_title': 'x' * 101}, 'first_test_only': True},
    {'recorded_source': SOURCE, 'first_test_only': True, 'video_ids': [SHORT]},
])
def test_recorded_source_contract_is_closed_at_producer_and_consumer(tmp_path, payload):
    with pytest.raises(ValueError):
        enqueue_operator_command(command(**payload), command_path=tmp_path / 'producer.json',
                                 acknowledgement_path=tmp_path / 'producer_ack.json')
    result = queue(tmp_path, [command(**payload)])
    assert refresh(result) is None
    assert result.inspect_command('recorded-1')['status'] == 'rejected'


def test_exact_refresh_leaves_all_other_actions_and_requests_unconsumed(tmp_path, monkeypatch):
    other_source = {**SOURCE, 'parent_video_id': OTHER}
    others = [
        {'id': 'announcement-before', 'action': 'announce', 'payload': {'message': 'fixture'}},
        {'id': 'context-before', 'action': 'set_context', 'payload': {'message': 'fixture'}},
        command('other-schedule', recorded_source=other_source, first_test_only=True),
        {'id': 'announcement-after', 'action': 'announce', 'payload': {'message': 'fixture'}},
    ]
    result = queue(tmp_path, [*others[:2], command(), *others[2:]])
    before = result.command_path.read_bytes()
    async def forbid_dispatch(*_args, **_kwargs):
        raise AssertionError('general dispatcher must not run')
    monkeypatch.setattr(result, '_dispatch', forbid_dispatch)
    assert refresh(result)['parent_video_id'] == PARENT
    assert result.command_path.read_bytes() == before
    rows = json.loads(result.acknowledgement_path.read_text())['acknowledgements']
    assert [row['id'] for row in rows] == ['recorded-1']
    assert json.loads(result.state_path.read_text()).get('active_context') is None
    assert all(not result.inspect_command(item['id'])['received'] for item in others)


@pytest.mark.parametrize('identity', ['missing', 'announcement'])
def test_refresh_missing_or_wrong_action_is_read_only(tmp_path, identity):
    result = queue(tmp_path, [command(), {'id': 'announcement', 'action': 'announce',
                                        'payload': {'message': 'fixture'}}])
    assert refresh(result, identity) is None
    assert not result.acknowledgement_path.exists() and not result.state_path.exists()


def test_recorded_expiry_does_not_wait_or_replay(tmp_path):
    result = queue(tmp_path, [command(recorded_source=SOURCE, first_test_only=True,
                                     expires_at_unix=time.time() - 1)])
    assert refresh(result) is None
    before = result.acknowledgement_path.read_bytes()
    assert refresh(result) is None
    assert result.acknowledgement_path.read_bytes() == before
    assert result.inspect_command('recorded-1')['status'] == 'expired'


@pytest.mark.parametrize('first_recorded', [False, True])
def test_live_and_recorded_forms_share_source_reservation(tmp_path, first_recorded):
    live = {'id': 'live-1', 'action': owner.ACTION, 'payload': {}}
    result = queue(tmp_path, [command(), live])
    result.dae = SimpleNamespace(livechat=SimpleNamespace(is_running=True,
        channel_id=CHANNEL, video_id=PARENT, stream_title=SOURCE['stream_title'],
        live_chat_id='fixture-chat', memory_manager=SimpleNamespace(current_session='fixture-session')))
    first, second = ('recorded-1', 'live-1') if first_recorded else ('live-1', 'recorded-1')
    assert refresh(result, first) is not None
    assert refresh(result, second) is None
    rows = json.loads(result.acknowledgement_path.read_text())['acknowledgements']
    assert next(row for row in rows if row['id'] == second)['reason'] == 'stream_source_already_reserved'
    assert len(result.get_pending_stream_schedule_requests()) == 1


def test_full_selection_freezes_but_only_first_submission_can_be_recorded(tmp_path):
    result = queue(tmp_path, [command()])
    request = refresh(result)
    claimed = result.claim_stream_schedule_request(request, [SHORT, OTHER])
    assert claimed['video_ids'] == [SHORT, OTHER]
    for invalid in ([OTHER], [SHORT, OTHER]):
        with pytest.raises(ValueError, match='out_of_scope'):
            result.finish_stream_schedule_request(request['id'], reason='attempted', submitted_ids=invalid)
    result.finish_stream_schedule_request(request['id'], reason='awaiting_saved_schedule_proof',
                                         submitted_ids=[SHORT])
    restarted = OperatorCommandQueue(None, result.command_path, result.acknowledgement_path, result.state_path)
    assert refresh(restarted) is None
    assert restarted.get_pending_stream_schedule_requests() == []
    stored = json.loads(result.state_path.read_text())[owner.STATE_KEY][0]
    assert stored['video_ids'] == [SHORT, OTHER] and stored['result']['submitted_ids'] == [SHORT]
    assert stored['execution_status'] == 'unknown'
    inspected = restarted.inspect_command(request['id'])
    assert inspected['first_test_only'] is True and inspected['selection_count'] == 2
    assert inspected['withheld_count'] == inspected['submission_recorded_count'] == 1
    assert inspected['delivery_verified'] is False and not set(SOURCE) & set(inspected)
    with pytest.raises(ValueError):
        restarted.claim_stream_schedule_request(claimed, [OTHER])


@pytest.mark.parametrize('field,value', [
    ('source_kind', 'live'), ('first_test_only', False), ('first_test_only', 1),
    ('session_id', 'invented'), ('live_chat_id', 'invented'),
])
def test_recorded_state_mode_is_closed_even_with_rebound_digest(tmp_path, field, value):
    result = queue(tmp_path, [command()])
    refresh(result)
    state = json.loads(result.state_path.read_text())
    state[owner.STATE_KEY][0][field] = value
    row = state[owner.STATE_KEY][0]
    row['request_digest'] = owner._digest({key: row[key] for key in owner._FROZEN | owner._RECORDED})
    result._atomic_write(result.state_path, state)
    with pytest.raises(ValueError):
        refresh(result)


def test_legacy_live_request_retains_exact_shape_and_digest(tmp_path):
    result = queue(tmp_path, [{'id': 'live-1', 'action': owner.ACTION, 'payload': {}}])
    result.dae = SimpleNamespace(livechat=SimpleNamespace(is_running=True,
        channel_id=CHANNEL, video_id=PARENT, stream_title=SOURCE['stream_title'],
        live_chat_id='fixture-chat', memory_manager=SimpleNamespace(current_session='fixture-session')))
    request = refresh(result, 'live-1')
    assert set(request) == owner._FROZEN | {'request_digest', 'execution_status', 'video_ids', 'result'}
    assert request['request_digest'] == owner._digest({key: request[key] for key in owner._FROZEN})
    assert not {'first_test_only', 'withheld_count', 'submission_recorded_count'} & set(result.inspect_command('live-1'))
    before = result.state_path.read_bytes()
    assert refresh(result, 'live-1') == request and result.state_path.read_bytes() == before


def test_unknown_intake_and_changed_payload_are_not_retried(tmp_path, monkeypatch):
    result = queue(tmp_path, [command()])
    def unavailable(*_args):
        raise OSError('fixture unavailable')
    monkeypatch.setattr(owner, 'dispatch', unavailable)
    with pytest.raises(ValueError, match='outcome_unknown'):
        refresh(result)
    before = result.acknowledgement_path.read_bytes()
    with pytest.raises(ValueError, match='outcome_unknown'):
        refresh(result)
    assert result.acknowledgement_path.read_bytes() == before
    changed = command(recorded_source={**SOURCE, 'stream_title': 'Changed'}, first_test_only=True)
    result.command_path.write_text(json.dumps({'version': 1, 'commands': [changed]}))
    with pytest.raises(ValueError, match='payload_changed'):
        refresh(result)


def _live_context(result):
    result.dae = SimpleNamespace(livechat=SimpleNamespace(is_running=True,
        channel_id=CHANNEL, video_id=PARENT, stream_title=SOURCE['stream_title'],
        live_chat_id='fixture-chat', memory_manager=SimpleNamespace(current_session='fixture-session')))


def _files(result):
    return [path.read_bytes() if path.exists() else None for path in
            (result.command_path, result.acknowledgement_path, result.state_path)]


@pytest.mark.parametrize('already_accepted', [False, True])
def test_recorded_only_refresh_does_not_consume_or_return_legacy_live(tmp_path, already_accepted):
    result = queue(tmp_path, [{'id': 'live-1', 'action': owner.ACTION, 'payload': {}}])
    _live_context(result)
    if already_accepted:
        assert refresh(result, 'live-1') is not None
    result.dae = None  # The bounded CLI deliberately has no live daemon context.
    before = _files(result)
    assert refresh(result, 'live-1', recorded_only=True) is None
    assert _files(result) == before
    assert result.inspect_command('live-1')['received'] is already_accepted


@pytest.mark.parametrize('payload', [
    {'recorded_source': SOURCE},
    {'recorded_source': SOURCE, 'first_test_only': False},
    {'first_test_only': True},
])
def test_recorded_only_refresh_requires_paired_mode_before_claim(tmp_path, payload):
    result = queue(tmp_path, [command(**payload)])
    before = _files(result)
    assert refresh(result, recorded_only=True) is None
    assert _files(result) == before


@pytest.mark.parametrize('recorded', [False, True])
def test_parent_video_cannot_be_claimed_as_short_in_either_source_mode(tmp_path, recorded):
    item = command() if recorded else {'id': 'recorded-1', 'action': owner.ACTION, 'payload': {}}
    result = queue(tmp_path, [item])
    _live_context(result)
    request = refresh(result)
    before = _files(result)
    for selected in ([PARENT], [SHORT, PARENT]):
        with pytest.raises(ValueError, match='stream_parent_not_a_short_target'):
            result.claim_stream_schedule_request(request, selected)
        assert _files(result) == before
    assert result.claim_stream_schedule_request(request, [SHORT])['video_ids'] == [SHORT]


@pytest.mark.parametrize('recorded', [False, True])
def test_parent_in_persisted_selection_blocks_reload_in_either_source_mode(tmp_path, recorded):
    item = command() if recorded else {'id': 'recorded-1', 'action': owner.ACTION, 'payload': {}}
    result = queue(tmp_path, [item])
    _live_context(result)
    request = refresh(result)
    result.claim_stream_schedule_request(request, [SHORT])
    state = json.loads(result.state_path.read_text())
    state[owner.STATE_KEY][0]['video_ids'] = [SHORT, PARENT]
    result._atomic_write(result.state_path, state)
    before = _files(result)
    with pytest.raises(ValueError, match='stream_parent_not_a_short_target'):
        refresh(result)
    assert _files(result) == before
