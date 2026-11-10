"""Disposable manifest contracts and actual launcher/DAE AST, with no services."""
import ast
import asyncio
import copy
import io
import json
import logging
from pathlib import Path
import sys
import threading
import time
from types import ModuleType, SimpleNamespace

import pytest

from modules.communication.livechat.src.operator_command_queue import OperatorCommandQueue, enqueue_operator_command
from modules.communication.livechat.src import operator_stream_schedule_owner as owner
from modules.communication.livechat.src.engagement_lifecycle import _await_owned_completion

ROOT = Path(__file__).resolve().parents[4]
CHANNEL = 'UC' + 'a' * 22
PARENT = 'p' * 11
SHORT = 's' * 11
OTHER = 't' * 11
TITLE = 'Fixture stream exact title'


@pytest.fixture(autouse=True)
def gates(tmp_path, monkeypatch):
    monkeypatch.setenv('YT_AUTOMATION_STOP_FILE', str(tmp_path / 'STOP'))
    monkeypatch.setenv('YT_AUTOMATION_ENABLED', 'true')
    monkeypatch.setenv('YT_SHORTS_SCHEDULING_ENABLED', 'true')


def command(identity='request-1', **payload):
    return {'id': identity, 'action': owner.ACTION, 'payload': payload}


def queue(tmp_path, commands=None):
    live = SimpleNamespace(is_running=True, channel_id=CHANNEL, video_id=PARENT,
        stream_title=TITLE, live_chat_id='fixture-live-chat',
        memory_manager=SimpleNamespace(current_session='fixture-session'))
    result = OperatorCommandQueue(SimpleNamespace(livechat=live, current_video_id='x' * 11),
        tmp_path / 'inbox.json', tmp_path / 'ack.json', tmp_path / 'state.json', poll_interval_seconds=0)
    result.command_path.write_text(json.dumps({'version': 1, 'commands': commands or [command()]}))
    return result


def accept(result):
    assert asyncio.run(result.poll_once())['results'][0]['status'] == 'accepted'
    return result.get_pending_stream_schedule_requests()[0]


def test_acceptance_freezes_confirmed_source_and_survives_session_end(tmp_path):
    result = queue(tmp_path)
    request = accept(result)
    assert request['parent_video_id'] == PARENT and request['stream_title'] == TITLE
    assert request['session_id'] == 'fixture-session'
    result.dae.livechat.is_running = False
    result.dae.livechat.video_id = OTHER
    result.dae.livechat.stream_title = 'Changed'
    assert result.get_pending_stream_schedule_requests() == [request]
    assert asyncio.run(result.poll_once())['processed'] == 0
    inspected = result.inspect_command('request-1')
    assert inspected['status'] == 'accepted' and inspected['execution_status'] == 'pending'
    assert inspected['delivery_verified'] is False and 'stream_title' not in inspected


@pytest.mark.parametrize('field,value', [('is_running', False), ('video_id', None),
    ('channel_id', None), ('stream_title', ''), ('memory_manager', None), ('live_chat_id', None)])
def test_missing_confirmed_source_never_uses_speculative_dae_fields(tmp_path, field, value):
    result = queue(tmp_path)
    setattr(result.dae.livechat, field, value)
    assert asyncio.run(result.poll_once())['results'][0]['status'] == 'blocked'
    assert result.get_pending_stream_schedule_requests() == []


@pytest.mark.parametrize('payload', [{'title': 'alternate'}, {'channel_id': CHANNEL},
    {'video_ids': [SHORT]}, {'ttl_seconds': 1}, {'ttl_seconds': True}, {'expires_at_unix': float('nan')}])
def test_producer_rejects_scope_widening_and_invalid_expiry(tmp_path, payload):
    with pytest.raises(ValueError):
        enqueue_operator_command(command(**payload), command_path=tmp_path / 'in.json', acknowledgement_path=tmp_path / 'ack.json')


def test_cli_adds_enqueue_deadline():
    from modules.communication.livechat.scripts.operator_manifest import read_command
    before = time.time()
    item = read_command(stream=io.BytesIO(json.dumps(command()).encode()))
    assert before + 3600 <= item['payload']['expires_at_unix'] <= time.time() + 3600


def test_duplicate_source_new_id_is_not_a_second_attempt(tmp_path):
    result = queue(tmp_path, [command(), command('request-2')])
    rows = asyncio.run(result.poll_once())['results']
    assert [r['status'] for r in rows] == ['accepted', 'blocked']
    assert rows[1]['reason'] == 'stream_source_already_reserved'
    assert len(result.get_pending_stream_schedule_requests()) == 1


def test_expired_command_never_waits_for_future_stream(tmp_path):
    result = queue(tmp_path, [command(expires_at_unix=time.time() - 10)])
    assert asyncio.run(result.poll_once())['results'][0]['status'] == 'expired'
    assert result.get_pending_stream_schedule_requests() == []


def test_claim_freezes_selection_once_and_preserves_unknown(tmp_path):
    result = queue(tmp_path)
    request = accept(result)
    claim = result.claim_stream_schedule_request(request, [SHORT, OTHER])
    assert claim['execution_status'] == 'unknown'
    with pytest.raises(ValueError):
        result.claim_stream_schedule_request(request, [OTHER])
    restarted = OperatorCommandQueue(None, result.command_path, result.acknowledgement_path, result.state_path)
    with pytest.raises(ValueError):
        restarted.claim_stream_schedule_request(request, [SHORT])
    result.finish_stream_schedule_request(request['id'], reason='schedule_readback_unqualified', submitted_ids=[SHORT])
    with pytest.raises(ValueError):
        result.finish_stream_schedule_request(request['id'], reason='late_reclassification', no_submission=True)
    assert result.get_pending_stream_schedule_requests() == []
    inspection = result.inspect_command(request['id'])
    assert inspection['selection_count'] == 2 and inspection['execution_status'] == 'unknown'
    assert inspection['delivery_verified'] is False


@pytest.mark.parametrize('mutation', ['scope', 'receipt', 'missing_state', 'unknown_ack'])
def test_changed_or_uncertain_state_cannot_be_replayed(tmp_path, mutation):
    result = queue(tmp_path)
    accept(result)
    state = json.loads(result.state_path.read_text())
    ack = json.loads(result.acknowledgement_path.read_text())
    if mutation == 'scope':
        state[owner.STATE_KEY][0]['parent_video_id'] = OTHER
    elif mutation == 'receipt':
        ack['acknowledgements'][0]['result']['request_digest'] = '0' * 64
    elif mutation == 'missing_state':
        del state[owner.STATE_KEY]
    else:
        ack['acknowledgements'][0]['status'] = 'unknown'
    result._atomic_write(result.state_path, state)
    result._atomic_write(result.acknowledgement_path, ack)
    with pytest.raises(ValueError):
        result.get_pending_stream_schedule_requests()


def test_stop_before_claim_does_not_change_request(tmp_path):
    result = queue(tmp_path)
    request = accept(result)
    (tmp_path / 'STOP').write_text('operator stop')
    with pytest.raises(ValueError, match='gate_closed'):
        result.claim_stream_schedule_request(request, [SHORT])
    assert result.get_pending_stream_schedule_requests() == [request]


def test_selected_ids_and_reported_submissions_cannot_widen(tmp_path):
    result = queue(tmp_path)
    request = accept(result)
    with pytest.raises(ValueError):
        result.claim_stream_schedule_request(request, [SHORT, SHORT])
    result.claim_stream_schedule_request(request, [SHORT])
    with pytest.raises(ValueError):
        result.finish_stream_schedule_request(request['id'], reason='wrong_batch', submitted_ids=[OTHER])
    assert result.inspect_command(request['id'])['execution_status'] == 'unknown'


def test_request_expiring_during_discovery_cannot_claim(tmp_path, monkeypatch):
    result = queue(tmp_path)
    request = accept(result)
    monkeypatch.setattr(owner.time, 'time', lambda: request['expires_at_unix'] + 1)
    assert result.get_pending_stream_schedule_requests() == []
    with pytest.raises(ValueError, match='expired'):
        result.claim_stream_schedule_request(request, [SHORT])


def test_disabled_scheduler_switch_cannot_claim(tmp_path, monkeypatch):
    result = queue(tmp_path)
    request = accept(result)
    monkeypatch.setenv('YT_SHORTS_SCHEDULING_ENABLED', 'false')
    with pytest.raises(ValueError, match='gate_closed'):
        result.claim_stream_schedule_request(request, [SHORT])
    assert result.get_pending_stream_schedule_requests() == [request]


def test_unresolved_claim_reader_is_read_only_exact_and_copied(tmp_path):
    result = queue(tmp_path)
    state = {'version': 1, 'video_effect_claims': []}
    base = dict(kind='save', channel_id=CHANNEL, video_id=SHORT, content_sha256='a' * 64,
        policy_ids=[], fingerprints={'metadata': 'b' * 64, 'scheduling': 'c' * 64},
        outcome='unknown', claimed_at='2026-01-01T00:00:00+00:00')
    state['video_effect_claims'] = [base, {**base, 'video_id': OTHER, 'fingerprints': {'metadata': 'b' * 64}},
        {**base, 'channel_id': 'UC' + 'b' * 22}]
    result._atomic_write(result.state_path, state)
    before = result.state_path.read_bytes()
    claims = result.get_unresolved_scheduling_claims(CHANNEL)
    assert claims == [base] and not result.acknowledgement_path.exists()
    claims[0]['fingerprints']['scheduling'] = 'changed'
    assert result.get_unresolved_scheduling_claims(CHANNEL) == [base]
    assert result.state_path.read_bytes() == before
    result.state_path.write_text('{bad')
    with pytest.raises(ValueError):
        result.get_unresolved_scheduling_claims(CHANNEL)


@pytest.fixture
def launcher(monkeypatch):
    path = ROOT / 'modules/platform_integration/youtube_shorts_scheduler/scripts/launch.py'
    tree = ast.parse(path.read_text(encoding='utf-8'))
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == '_run_stream_schedule_requests')
    scope = {}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[fn], type_ignores=[])), str(path), 'exec'), scope)
    calls = []
    settings = SimpleNamespace(verified=True, complete=True, ids=[SHORT], exception=None,
                               result={'status': 'unknown', 'submitted_ids': [SHORT]})
    queue_ref = [None]

    class Scheduler:
        def __init__(self, key, dry_run):
            assert key == 'fixture' and dry_run is False
            self.channel_id = CHANNEL
            self.config = {'id': CHANNEL}
            self.tracker = SimpleNamespace(channel_id=CHANNEL)

        def discover_stream_title_batch(self, title):
            assert title == TITLE
            # No manifest lock may be held during browser work.
            with queue_ref[0]._locked():
                calls.append('discovery')
            return {'complete': settings.complete, 'video_ids': settings.ids}

        async def run_scheduling_cycle(self, video_ids, max_videos):
            with queue_ref[0]._locked():
                calls.append(('schedule', list(video_ids), max_videos))
            assert self.request_driver is self.driver
            assert self.stream_schedule_request['execution_status'] == 'unknown'
            assert queue_ref[0].get_pending_stream_schedule_requests() == []
            if settings.exception:
                raise settings.exception
            return settings.result

    def substitute(name, **attributes):
        module = ModuleType(name)
        module.__dict__.update(attributes)
        monkeypatch.setitem(sys.modules, name, module)

    from modules.infrastructure.foundups_selenium.src.youtube_verification import VerificationHandoff
    def access(driver, channel, parent):
        assert (channel, parent) == (CHANNEL, PARENT)
        calls.append('verify')
        if settings.exception == 'handoff':
            raise VerificationHandoff('fixture takeover')
        return {'verified': settings.verified}

    substitute('modules.infrastructure.shared_utilities.youtube_channel_registry', get_channel_by_id=lambda channel: {'key': 'fixture'} if channel == CHANNEL else None)
    substitute('modules.platform_integration.youtube_shorts_scheduler.src.channel_config', verify_schedule_target_access=access)
    substitute('modules.platform_integration.youtube_shorts_scheduler.src.scheduler', YouTubeShortsScheduler=Scheduler)
    substitute('modules.platform_integration.youtube_shorts_scheduler.src.dom_automation', YouTubeStudioDOM=lambda driver: object())
    driver = SimpleNamespace(get=lambda url: calls.append(url))
    def run(queue, requests):
        queue_ref[0] = queue
        return scope[fn.name](driver, requests, queue=queue)
    return run, settings, calls


def test_launcher_exact_batch_claim_precedes_writes_and_has_no_lock_during_effects(tmp_path, launcher):
    run, settings, calls = launcher
    result = queue(tmp_path)
    request = accept(result)
    out = run(result, [request])
    assert calls == [f'https://studio.youtube.com/video/{PARENT}/edit', 'verify', 'discovery', ('schedule', [SHORT], 0)]
    assert out['stream_schedule_requests'][0]['status'] == 'unknown'
    assert out['operator_handoff_required'] is True
    assert result.inspect_command(request['id'])['delivery_verified'] is False


@pytest.mark.parametrize('case', ['access', 'partial', 'empty', 'exception', 'handoff', 'blocked'])
def test_launcher_denials_and_uncertainty_never_rotate_or_retry(tmp_path, launcher, case):
    run, settings, calls = launcher
    result = queue(tmp_path)
    request = accept(result)
    if case == 'access': settings.verified = False
    if case == 'partial': settings.complete = False
    if case == 'empty': settings.ids = []
    if case == 'exception': settings.exception = RuntimeError('fixture failure')
    if case == 'handoff': settings.exception = 'handoff'
    if case == 'blocked': settings.result = {'status': 'blocked', 'submitted_ids': []}
    out = run(result, [request])
    status = result.inspect_command(request['id'])['execution_status']
    assert status == ('pending' if case in {'access', 'partial'} else 'unknown' if case == 'exception' else 'blocked')
    assert out['operator_handoff_required'] is (case not in {'access', 'partial'})
    assert sum(isinstance(c, tuple) for c in calls) == (1 if case in {'exception', 'blocked'} else 0)
    if status != 'pending':
        count = len(calls)
        run(result, [request])
        assert len(calls) == count


def test_launcher_rejects_forged_snapshot_before_navigation(tmp_path, launcher):
    run, _, calls = launcher
    result = queue(tmp_path)
    request = accept(result)
    request['parent_video_id'] = OTHER
    run(result, [request])
    assert calls == []


@pytest.mark.asyncio
@pytest.mark.parametrize('mode', ['timeout', 'cancel'])
async def test_actual_dae_request_block_retains_browser_lock_until_worker_settles(monkeypatch, mode):
    path = ROOT / 'modules/communication/livechat/src/auto_moderator_dae.py'
    tree = ast.parse(path.read_text(encoding='utf-8'))
    method = next(n for n in ast.walk(tree) if isinstance(n, ast.AsyncFunctionDef) and n.name == '_browser_engagement_loop')
    target = next(n for n in ast.walk(method) if isinstance(n, ast.Try) and any(
        isinstance(b, ast.If) and isinstance(b.test, ast.Name) and b.test.id == 'stream_requests' for b in n.body))
    isolated = ast.AsyncFunctionDef(name='exercise', args=ast.arguments(posonlyargs=[], args=[], kwonlyargs=[], kw_defaults=[], defaults=[]),
        body=[ast.Assign(targets=[ast.Name(id='request_worker', ctx=ast.Store())], value=ast.Constant(value=None)), target], decorator_list=[])
    started, release = asyncio.Event(), asyncio.Event()
    lock, stop = asyncio.Lock(), threading.Event()
    async def worker(**kwargs):
        assert kwargs['stream_schedule_requests'] == [{'frozen': True}]
        started.set()
        await release.wait()
        return {}
    async def fake_thread(fn, **kwargs):
        return await fn(**kwargs)
    monkeypatch.setattr(asyncio, 'to_thread', fake_thread)
    namespace = {'asyncio': asyncio, '_await_owned_completion': _await_owned_completion,
        'stream_requests': [{'frozen': True}], 'run_multi_channel_scheduler': worker,
        'browser_name': 'chrome', 'max_shorts': 3, 'scheduler_stop_event': stop,
        'phase3_timeout': .01 if mode == 'timeout' else 10, 'tag': 'TEST',
        'logger': logging.getLogger(__name__)}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[isolated], type_ignores=[])), str(path), 'exec'), namespace)
    async def owned():
        async with lock:
            await namespace['exercise']()
    task = asyncio.create_task(owned())
    await asyncio.wait_for(started.wait(), 1)
    if mode == 'cancel':
        task.cancel()
        await asyncio.sleep(0)
        task.cancel()
    else:
        await asyncio.sleep(.03)
    assert lock.locked() and not task.done() and stop.is_set()
    release.set()
    if mode == 'cancel':
        with pytest.raises(asyncio.CancelledError):
            await task
    else:
        await task
    assert not lock.locked()


@pytest.mark.parametrize('handoff', [True, False])
def test_actual_dae_handoff_returns_before_later_browser_phases(handoff):
    path = ROOT / 'modules/communication/livechat/src/auto_moderator_dae.py'
    tree = ast.parse(path.read_text(encoding='utf-8'))
    method = next(n for n in ast.walk(tree) if isinstance(n, ast.AsyncFunctionDef) and n.name == '_browser_engagement_loop')
    gate = next(n for n in ast.walk(method) if isinstance(n, ast.If)
                and 'operator_handoff_required' in ast.unparse(n.test))
    next_phase = next(n for n in ast.walk(method) if isinstance(n, ast.Assign)
                      and any(isinstance(t, ast.Name) and t.id == 'linkedin_enabled' for t in n.targets))
    assert gate.lineno < next_phase.lineno
    later = ast.Expr(value=ast.Call(func=ast.Name(id='later_browser_phase', ctx=ast.Load()), args=[], keywords=[]))
    isolated = ast.AsyncFunctionDef(name='exercise', args=ast.arguments(posonlyargs=[], args=[], kwonlyargs=[], kw_defaults=[], defaults=[]),
        body=[gate, later], decorator_list=[])
    calls = []
    namespace = {'results': {'operator_handoff_required': handoff}, 'tag': 'TEST',
                 'logger': logging.getLogger(__name__), 'later_browser_phase': lambda: calls.append('later')}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[isolated], type_ignores=[])), str(path), 'exec'), namespace)
    asyncio.run(namespace['exercise']())
    assert calls == ([] if handoff else ['later'])


@pytest.mark.parametrize('function', ['run_shorts_scheduler', 'run_multi_channel_scheduler'])
@pytest.mark.parametrize('browser', ['chrome', 'edge'])
def test_actual_launch_attachment_uses_connection_specific_cdp_guard(monkeypatch, function, browser):
    path = ROOT / 'modules/platform_integration/youtube_shorts_scheduler/scripts/launch.py'
    tree = ast.parse(path.read_text(encoding='utf-8'))
    method = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == function)
    attachment = next(n for n in ast.walk(method) if isinstance(n, ast.Try) and any(
        isinstance(b, ast.ImportFrom) and any(a.name == '_guard_attached_chromium_driver' for a in b.names)
        for b in n.body))
    isolated = ast.FunctionDef(name='exercise', args=ast.arguments(posonlyargs=[], args=[], kwonlyargs=[], kw_defaults=[], defaults=[]),
        body=[attachment, ast.Return(value=ast.Name(id='driver', ctx=ast.Load()))], decorator_list=[])
    calls = []
    port = 9223 if browser == 'edge' else 9222
    class Options:
        def add_experimental_option(self, name, value):
            assert (name, value) == ('debuggerAddress', f'127.0.0.1:{port}')
    def construct(kind, **kwargs):
        calls.append(('construct', kind))
        return SimpleNamespace(kind=kind)
    def guard(driver, received_port, vendor):
        calls.append(('guard', driver.kind, received_port, vendor))
        return SimpleNamespace(guarded=True, kind=driver.kind)
    module = ModuleType('modules.infrastructure.dependency_launcher.src.dae_dependencies')
    module._guard_attached_chromium_driver = guard
    monkeypatch.setitem(sys.modules, module.__name__, module)
    namespace = {'browser': browser, 'use_edge': browser == 'edge', 'port': port,
                 'chrome_port': port, 'browser_name': browser, 'ChromeOptions': Options,
                 'EdgeOptions': Options, 'print': lambda *_: None,
                 'webdriver': SimpleNamespace(Chrome=lambda **kw: construct('chrome', **kw),
                                              Edge=lambda **kw: construct('edge', **kw))}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[isolated], type_ignores=[])), str(path), 'exec'), namespace)
    assert namespace['exercise']().guarded is True
    assert calls == [('construct', browser), ('guard', browser, port, 'ms' if browser == 'edge' else 'goog')]


@pytest.mark.asyncio
@pytest.mark.parametrize('peer_state', ['running', 'normal', 'crash', 'cancelled'])
async def test_actual_supervisor_holds_operator_browser_and_still_supervises_peer(monkeypatch, peer_state):
    from unittest.mock import AsyncMock
    path = ROOT / 'modules/communication/livechat/src/auto_moderator_dae.py'
    tree = ast.parse(path.read_text(encoding='utf-8'))
    loop = next(n for n in ast.walk(tree) if isinstance(n, ast.For)
                and any(isinstance(c, ast.Assign) and any(isinstance(t, ast.Name) and t.id == '_task' for t in c.targets)
                        for c in n.body))
    isolated = ast.AsyncFunctionDef(name='exercise', args=ast.arguments(posonlyargs=[], args=[], kwonlyargs=[], kw_defaults=[], defaults=[]),
        body=[loop], decorator_list=[])
    held, peer = asyncio.Future(), asyncio.Future()
    held.set_result({'status': 'operator_handoff_required'})
    if peer_state == 'normal': peer.set_result(None)
    if peer_state == 'crash': peer.set_exception(RuntimeError('fixture crash'))
    if peer_state == 'cancelled': peer.cancel()
    tasks = {'chrome': held, 'edge': peer}
    created = []
    def create(browser):
        created.append(browser)
        return asyncio.Future()
    monkeypatch.setattr(asyncio, 'sleep', AsyncMock())
    namespace = {'asyncio': asyncio, '_browser_tasks': tasks, '_create_browser_task': create,
                 'self': SimpleNamespace(_ensure_multi_channel_coordinator=AsyncMock()),
                 'runner': object(), 'mode': 'fixture', '_RESTART_DELAY': 0,
                 'logger': logging.getLogger(__name__)}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[isolated], type_ignores=[])), str(path), 'exec'), namespace)
    await namespace['exercise']()
    await namespace['exercise']()  # The held browser must remain held on later health checks.
    assert tasks['chrome'] is held
    assert created == ([] if peer_state == 'running' else ['edge'])


@pytest.mark.parametrize('mode,dry_run,allowed', [('schedule', False, False), ('schedule', True, True), ('enhance', False, True)])
def test_legacy_live_scheduler_refuses_before_attachment(mode, dry_run, allowed):
    path = ROOT / 'modules/platform_integration/youtube_shorts_scheduler/scripts/launch.py'
    tree = ast.parse(path.read_text(encoding='utf-8'))
    method = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'run_shorts_scheduler')
    gate = method.body[1]
    assert isinstance(gate, ast.If) and isinstance(method.body[2], ast.Import)
    isolated = ast.FunctionDef(name='exercise', args=ast.arguments(posonlyargs=[], args=[], kwonlyargs=[], kw_defaults=[], defaults=[]),
        body=[gate, ast.Return(value=ast.Constant(value='continue'))], decorator_list=[])
    namespace = {'mode': mode, 'dry_run': dry_run, 'print': lambda *_: None}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[isolated], type_ignores=[])), str(path), 'exec'), namespace)
    assert namespace['exercise']() == ('continue' if allowed else None)
