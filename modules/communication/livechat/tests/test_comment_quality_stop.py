"""Private-file controls for the existing STOP owner's scoped quality incident.

No runtime STOP, provider, model or browser is used. Run through the fixed
credential-free owner guard; this qualifies cooperating writers, not OS CAS
against arbitrary out-of-band manual replacement.
"""
from concurrent.futures import ThreadPoolExecutor
import ast
import asyncio
import importlib.util
import inspect
import json
import logging
import os
from pathlib import Path
import sys
import time
from types import SimpleNamespace, ModuleType

import pytest


@pytest.fixture
def gates(tmp_path, monkeypatch):
    source = Path(__file__).resolve().parents[1] / 'src/automation_gates.py'
    spec = importlib.util.spec_from_file_location('_scoped_stop_owner', source)
    owner = importlib.util.module_from_spec(spec); spec.loader.exec_module(owner)
    monkeypatch.setenv('YT_AUTOMATION_STOP_FILE', str(tmp_path / 'STOP'))
    for name in ('YT_AUTOMATION_ENABLED', 'YT_LIVECHAT_SEND_ENABLED',
                 'YT_COMMENT_ENGAGEMENT_ENABLED', 'YT_COMMENT_REPLY_ENABLED'):
        monkeypatch.setenv(name, 'true')
    return owner


def api(owner, name):
    value = getattr(owner, name, None)
    assert callable(value), 'Scoped STOP owner API is required'
    return value


def stopped(owner, scope):
    assert 'scope' in inspect.signature(owner.stop_active).parameters
    return owner.stop_active(scope)


def incident(**changes):
    return dict(dict(version=1, kind='comment_reply_quality', scope='comments',
                     incident_id='1' * 32, reason='review_rejected', recorded_at_unix=123.0), **changes)


def test_missing_file_and_scoped_flags_do_not_enable_disabled_environment(gates, monkeypatch):
    assert gates.stop_active() is False
    assert not stopped(gates, 'global') and not stopped(gates, 'comments')
    monkeypatch.setenv('YT_COMMENT_REPLY_ENABLED', 'false')
    assert gates.gate_snapshot()['comment_reply'] is False


@pytest.mark.parametrize('raw', [b'', b'manual STOP', b'{}', b'[]', b'{invalid', b'x' * 4097,
    b'{"version":1,"kind":"manual","kind":"comment_reply_quality","scope":"global","scope":"comments","incident_id":"11111111111111111111111111111111","reason":"review_rejected","recorded_at_unix":123}'])
def test_every_untyped_or_unreadable_shape_remains_global(gates, raw):
    gates.stop_file_path().write_bytes(raw)
    assert gates.stop_active()
    assert all(stopped(gates, scope) for scope in ('global', 'comments', 'livechat', 'scheduling', 'shorts'))
    assert gates.gate_snapshot()['stop_active'] is True


@pytest.mark.parametrize('change', [
    {'version': True}, {'version': 2}, {'kind': 'manual'}, {'scope': 'livechat'},
    {'incident_id': 'not-a-token'}, {'reason': 'review_unavailable'},
    {'recorded_at_unix': True}, {'recorded_at_unix': 'nan'},
    {'recorded_at_unix': -1}, {'extra_field': 'unknown'},
])
def test_only_the_exact_closed_typed_incident_is_scoped(gates, change):
    if change.get('recorded_at_unix') == 'nan': change = dict(change, recorded_at_unix=float('nan'))
    gates.stop_file_path().write_text(json.dumps(incident(**change)), encoding='utf-8')
    assert stopped(gates, 'global') and stopped(gates, 'livechat')


def test_valid_comments_incident_preserves_livechat_scheduler_and_noarg_stop(gates):
    gates.stop_file_path().write_text(json.dumps(incident()), encoding='utf-8')
    assert gates.stop_active() and stopped(gates, 'comments')
    assert not any(stopped(gates, scope) for scope in ('global', 'livechat', 'scheduling', 'shorts'))
    snapshot = gates.gate_snapshot()
    assert snapshot['stop_active'] is False and snapshot['comments_stop_active'] is True
    assert snapshot['comment_engagement'] is False and snapshot['comment_reply'] is False
    assert snapshot['yt_automation'] is True and snapshot['livechat_send'] is True
    assert snapshot['comment_quality_incident_id'] == '1' * 32
    assert snapshot['comment_quality_reason'] == 'review_rejected'


@pytest.mark.parametrize('scope', ['', 'unknown', None, False])
def test_unknown_scope_never_silently_allows_actions(gates, scope):
    assert stopped(gates, scope) is True


def test_default_relative_and_absolute_paths_are_cwd_independent(gates, tmp_path, monkeypatch):
    monkeypatch.delenv('YT_AUTOMATION_STOP_FILE')
    monkeypatch.chdir(tmp_path)
    expected = Path(gates.__file__).resolve().parents[4] / 'memory/STOP_YT_AUTOMATION'
    assert gates.stop_file_path() == expected
    monkeypatch.setenv('YT_AUTOMATION_STOP_FILE', 'memory/relative_STOP')
    assert gates.stop_file_path() == expected.parent / 'relative_STOP'
    monkeypatch.setenv('YT_AUTOMATION_STOP_FILE', str(tmp_path / 'absolute_STOP'))
    assert gates.stop_file_path() == tmp_path / 'absolute_STOP'


def test_directory_and_read_failure_are_global_without_erasing_evidence(gates, monkeypatch):
    path = gates.stop_file_path(); path.mkdir()
    assert stopped(gates, 'livechat')
    path.rmdir(); path.write_bytes(b'private manual stop')
    original = Path.open
    def failed(self, *args, **kwargs):
        if self == path: raise PermissionError('synthetic private read failure')
        return original(self, *args, **kwargs)
    monkeypatch.setattr(Path, 'open', failed)
    assert stopped(gates, 'global') and stopped(gates, 'comments')


@pytest.mark.parametrize('reason', ['invalid_reply_text', 'review_rejected', 'review_unavailable_or_invalid'])
def test_recognized_rejection_latches_once_and_survives_fresh_owner(gates, reason):
    result = api(gates, 'latch_comment_quality_stop')(reason)
    assert result['created'] is True and result['persisted'] is True
    record = result['incident']
    assert record['reason'] == reason and record['scope'] == 'comments'
    assert len(record['incident_id']) == 32
    assert api(gates, 'read_comment_quality_stop')() == record
    spec = importlib.util.spec_from_file_location('_fresh_scoped_stop_owner', gates.__file__)
    fresh = importlib.util.module_from_spec(spec); spec.loader.exec_module(fresh)
    assert api(fresh, 'read_comment_quality_stop')() == record
    assert stopped(fresh, 'comments') and not stopped(fresh, 'livechat')
    again = gates.latch_comment_quality_stop(reason)
    assert again['created'] is False and again['incident'] == record
    assert stopped(gates, 'comments') and not stopped(gates, 'livechat')


@pytest.mark.parametrize('reason', ['review_unavailable', 'cancelled', 'theme_changed_or_expired', 'visual_unavailable'])
def test_unavailable_or_optional_visual_outcomes_cannot_create_quality_stop(gates, reason):
    with pytest.raises(ValueError): api(gates, 'latch_comment_quality_stop')(reason)
    assert not gates.stop_file_path().exists()


def test_latch_never_overwrites_manual_or_newer_stop(gates):
    path = gates.stop_file_path(); path.write_bytes(b'manual stop remains exact')
    original = path.read_bytes()
    result = api(gates, 'latch_comment_quality_stop')('review_rejected')
    assert not result['created'] and path.read_bytes() == original
    assert stopped(gates, 'global')


def test_exclusive_write_failure_does_not_claim_persistence(gates, monkeypatch):
    path = gates.stop_file_path()
    original = Path.open
    def failed(self, mode='r', *args, **kwargs):
        if self == path and 'x' in mode: raise PermissionError('synthetic private create failure')
        return original(self, mode, *args, **kwargs)
    monkeypatch.setattr(Path, 'open', failed)
    result = api(gates, 'latch_comment_quality_stop')('review_rejected')
    assert result['persisted'] is False and result['created'] is False
    assert not path.exists()


def test_explicit_clear_requires_whole_current_incident_and_preserves_other_flags(gates, monkeypatch):
    record = api(gates, 'latch_comment_quality_stop')('review_rejected')['incident']
    wrong = dict(record, incident_id='2' * 32)
    assert api(gates, 'clear_comment_quality_stop')(wrong)['cleared'] is False
    assert gates.read_comment_quality_stop() == record
    monkeypatch.setenv('YT_COMMENT_REPLY_ENABLED', 'false')
    assert gates.clear_comment_quality_stop(record)['cleared'] is True
    assert not gates.stop_active() and gates.gate_snapshot()['comment_reply'] is False


def test_stale_expected_record_never_clears_newer_or_manual_stop(gates):
    old = api(gates, 'latch_comment_quality_stop')('review_rejected')['incident']
    newer = dict(old, incident_id='3' * 32)
    gates.stop_file_path().write_text(json.dumps(newer), encoding='utf-8')
    before = gates.stop_file_path().read_bytes()
    assert api(gates, 'clear_comment_quality_stop')(old)['cleared'] is False
    assert gates.stop_file_path().read_bytes() == before
    gates.stop_file_path().write_bytes(b'manual')
    assert gates.clear_comment_quality_stop(newer)['cleared'] is False
    assert gates.stop_file_path().read_bytes() == b'manual'


def test_huge_numeric_expected_record_is_rejected_without_erasing_stop(gates):
    record = api(gates, 'latch_comment_quality_stop')('review_rejected')['incident']
    assert api(gates, 'clear_comment_quality_stop')(dict(record, recorded_at_unix=10 ** 1000))['cleared'] is False
    assert gates.read_comment_quality_stop() == record


def test_cooperating_latch_race_has_one_incident_and_one_creator(gates):
    latch = api(gates, 'latch_comment_quality_stop')
    with ThreadPoolExecutor(max_workers=4) as workers:
        results = list(workers.map(latch, ['review_rejected'] * 8))
    assert sum(result['created'] for result in results) == 1
    assert len({result['incident']['incident_id'] for result in results}) == 1
    assert gates.read_comment_quality_stop() == results[0]['incident']


def test_clear_does_not_release_actual_unknown_delivery_reservation(gates, tmp_path):
    from modules.communication.video_comments.src.commenter_history_store import CommenterHistoryStore
    store = CommenterHistoryStore(tmp_path / 'history.db')
    target = dict(_target_channel_id='RECEIVING', video_id='VIDEO', comment_id='UgxOriginal',
                  text='Question', author_name='Aki', channel_id='AUTHOR')
    attempt = store.begin_reply_attempt(target, 'Draft')
    assert attempt
    before = store.get_reply_attempts(target)
    record = api(gates, 'latch_comment_quality_stop')('review_rejected')['incident']
    assert api(gates, 'clear_comment_quality_stop')(record)['cleared']
    assert store.get_reply_attempts(target) == before
    assert store.begin_reply_attempt(target, 'New draft') is None


def processor_fixture(monkeypatch):
    root = Path(__file__).resolve().parents[4]
    directory = root / 'modules/communication/video_comments/tests'
    modules = []
    for name in ('test_chat_manifest_inspection', 'test_reply_quality_safety'):
        spec = importlib.util.spec_from_file_location('_stop_' + name, directory / (name + '.py'))
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        modules.append(module)
    helper, quality = modules
    helper.PROCESSOR.INTELLIGENT_REPLIES_AVAILABLE = True
    monkeypatch.setenv('YT_ALLOW_GENERIC_REPLY_FALLBACK', 'false')
    return helper, quality


def test_actual_processor_retains_typed_halt_when_stop_write_fails(gates, monkeypatch):
    helper, quality = processor_fixture(monkeypatch)
    item, posted = quality.processor(helper, text=None, reason='invalid_reply_text')
    path, original = gates.stop_file_path(), Path.open
    def failed(self, mode='r', *args, **kwargs):
        if self == path and 'x' in mode: raise PermissionError('synthetic private create failure')
        return original(self, mode, *args, **kwargs)
    monkeypatch.setattr(Path, 'open', failed)
    result = asyncio.run(item.engage_comment(1, do_like=False, do_heart=False))
    assert result['halted_for_reply_quality'] is True and result.get('quality_stop_persisted') is False
    assert result.get('state') == 'halted' and posted == [] and not path.exists()


def test_actual_meaningful_reviewed_positive_does_not_latch(gates, monkeypatch):
    helper, quality = processor_fixture(monkeypatch)
    item, posted = quality.processor(helper)
    result = asyncio.run(item.engage_comment(1, do_like=False, do_heart=False))
    assert result['reply'] is True and len(posted) == 1
    assert not gates.stop_file_path().exists()


@pytest.mark.parametrize('result,halted', [
    ({'halted_for_reply_quality': True, 'quality_stop_persisted': False}, True),
    ({'halted_for_comments_stop': True}, True), ({'stats': {'replies': 1}}, False),
])
def test_dedicated_cli_exit_preserves_halt_even_without_a_persisted_file(gates, result, halted):
    code = api(gates, 'comments_exit_code')(result)
    assert code == (78 if halted else 0)


@pytest.mark.parametrize('halted', [False, True])
def test_actual_cli_final_heartbeat_never_labels_halt_completed(gates, halted):
    source = Path(__file__).resolve().parents[4] / 'modules/communication/video_comments/skillz/tars_like_heart_reply/run_skill.py'
    tree = ast.parse(source.read_text(encoding='utf-8'))
    definitions = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == '_final_heartbeat']
    assert len(definitions) == 1, 'CLI requires complete typed final-heartbeat owner'
    namespace = {}
    exec(compile(ast.Module(body=definitions, type_ignores=[]), str(source), 'exec'), namespace)
    value = namespace['_final_heartbeat']({'halted_for_reply_quality': halted, 'stats': {'comments_processed': 2}})
    assert value['state'] == ('halted' if halted else 'completed')
    assert value['comments_processed'] == 2


def source_class(relative, name, methods):
    root = Path(__file__).resolve().parents[4]
    path = root / relative
    tree = ast.parse(path.read_text(encoding='utf-8'))
    selected = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == name)
    selected.body = [node for node in selected.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in methods]
    assert {node.name for node in selected.body} == set(methods), 'Complete owner methods required'
    selected.bases = []
    future = ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')], level=0)
    namespace = dict(asyncio=asyncio, os=os, time=time, logger=logging.getLogger(__name__))
    exec(compile(ast.fix_missing_locations(ast.Module(body=[future, selected], type_ignores=[])), str(path), 'exec'), namespace)
    return namespace[name]


def runner_module(monkeypatch):
    path = Path(__file__).with_name('test_engagement_runner_lifecycle.py')
    spec = importlib.util.spec_from_file_location('_stop_lifecycle_controls', path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module, module._load_runner_source(monkeypatch)


@pytest.mark.parametrize('name', ['SubprocessRunner', 'ThreadRunner', 'InProcessRunner'])
def test_actual_runner_modes_refuse_before_spawning_or_browser_entry(gates, monkeypatch, name):
    stop_path = gates.stop_file_path()
    _, module = runner_module(monkeypatch)
    monkeypatch.setenv('YT_AUTOMATION_STOP_FILE', str(stop_path))
    api(gates, 'latch_comment_quality_stop')('review_rejected')
    assert hasattr(module, name)
    runner = object.__new__(getattr(module, name))
    result = asyncio.run(runner.run_engagement('receiving-channel'))
    assert result.get('state') == 'halted' and result['halted_for_reply_quality'] is True


def test_actual_direct_processor_and_dae_refuse_before_extraction_or_generation(gates, monkeypatch, tmp_path):
    helper, quality = processor_fixture(monkeypatch)
    item, posted = quality.processor(helper)
    calls = []
    item.extract_comment_data = lambda *_a: calls.append('extract')
    gates.latch_comment_quality_stop('review_rejected')
    result = asyncio.run(item.engage_comment(1, do_like=True, do_heart=True))
    assert result['state'] == 'halted' and posted == calls == []
    dae = helper.definitions('_stop_direct_dae', 'modules/communication/video_comments/skillz/tars_like_heart_reply/comment_engagement_dae.py')
    result = asyncio.run(dae.execute_skill('receiving-channel'))
    assert result['state'] == 'halted'


@pytest.mark.parametrize('name', ['_run_edge_engagement', '_run_chrome_engagement'])
def test_both_coordinator_branches_refuse_before_any_channel_work(gates, name):
    relative = 'modules/communication/livechat/src/multi_channel_coordinator.py'
    owner = source_class(relative, 'MultiChannelCoordinator', ['_comments_halt', name])
    item = object.__new__(owner); statuses = []
    item.update_engagement_status = lambda *args: statuses.append(args)
    gates.latch_comment_quality_stop('review_rejected')
    result = asyncio.run(getattr(item, name)(None, [('One', 'receiving-channel')], 1, False))
    assert result == 0 and item._comments_halt_receipt['state'] == 'halted'


def test_typed_unpersisted_child_halt_blocks_coordinator_verification_and_retry(gates):
    relative = 'modules/communication/livechat/src/multi_channel_coordinator.py'
    owner = source_class(relative, 'MultiChannelCoordinator', ['_comments_halt', '_verify_and_retry_engagement'])
    item = object.__new__(owner); statuses = []
    item.update_engagement_status = lambda *args: statuses.append(args)
    assert item._comments_halt('receiving-channel', {'halted_for_reply_quality': True,
        'quality_halt_reason': 'review_rejected', 'quality_stop_persisted': False})
    result = asyncio.run(item._verify_and_retry_engagement(None, None, 'receiving-channel', 'One', 1, 9222, 3, False, None, False))
    assert result == 3 and statuses[0][1]['all_processed'] is False
    assert not gates.stop_file_path().exists()


@pytest.mark.parametrize('payload', [b'', b'{"stats":{"comments_processed":9,"all_processed":true}}\n'])
def test_actual_subprocess_reader_honors_exit78_without_trusting_stdout(gates, monkeypatch, tmp_path, payload):
    _, module = runner_module(monkeypatch)
    monkeypatch.setenv('COMMUNITY_DOM_ONLY', 'true')
    async def exercise():
        stdout, stderr = asyncio.StreamReader(), asyncio.StreamReader()
        stdout.feed_data(payload); stdout.feed_eof(); stderr.feed_eof()
        process = SimpleNamespace(pid=123, returncode=78, stdout=stdout, stderr=stderr)
        async def wait(): return 78
        process.wait = wait
        async def spawn(*_a, **_k): return process
        monkeypatch.setattr(asyncio, 'create_subprocess_exec', spawn)
        script = tmp_path / 'existing_child.py'; script.write_text('# not executed\n', encoding='utf-8')
        runner = module.SubprocessRunner(tmp_path); runner.engagement_script = script
        return await runner.run_engagement('receiving-channel')
    result = asyncio.run(exercise())
    assert result.get('state') == 'halted' and result.get('halted_for_comments_stop') is True
    assert result['stats']['all_processed'] is False


@pytest.mark.parametrize('state', ['quality', 'manual', 'unknown'])
def test_actual_chat_sender_continues_only_for_recognized_comments_stop(gates, monkeypatch, state):
    errors = ModuleType('googleapiclient.errors'); errors.HttpError = type('OfflineHttpError', (Exception,), {})
    google = ModuleType('googleapiclient'); google.errors = errors
    monkeypatch.setitem(sys.modules, 'googleapiclient', google)
    monkeypatch.setitem(sys.modules, 'googleapiclient.errors', errors)
    source = Path(gates.__file__).with_name('chat_sender.py')
    spec = importlib.util.spec_from_file_location('_stop_chat_sender', source)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    if state == 'quality': gates.latch_comment_quality_stop('review_rejected')
    else: gates.stop_file_path().write_bytes(b'manual' if state == 'manual' else b'{}')
    calls = []
    def insert(**kwargs):
        calls.append(True)
        return SimpleNamespace(execute=lambda: {'id': 'synthetic-message'})
    item = module.ChatSender(SimpleNamespace(liveChatMessages=lambda: SimpleNamespace(insert=insert)), 'synthetic-chat')
    item.bot_channel_id, item.random_delay_enabled = 'synthetic-channel', False
    async def no_delay(*_a): return None
    item._apply_global_throttling = no_delay
    monkeypatch.setenv('YT_LIVECHAT_DRY_RUN', 'false')
    result = asyncio.run(item.send_message('A useful answer', skip_delay=True))
    assert result is (state == 'quality') and len(calls) == int(state == 'quality')


def rotation_module(monkeypatch, tmp_path):
    cases, runner = runner_module(monkeypatch)
    return cases, cases.rotation_source.__wrapped__(runner, monkeypatch, tmp_path)


@pytest.mark.parametrize('operation,code,expected', [
    ('COMMENTS', 78, 'HALTED'), ('COMMENTS', 0, 'COMPLETED'), ('SHORTS', 78, 'FAILED'),
])
def test_actual_supervisor_exit_classification_is_comments_only(gates, monkeypatch, tmp_path, operation, code, expected):
    _, module = rotation_module(monkeypatch, tmp_path)
    assert hasattr(module.TaskState, 'HALTED')
    item = object.__new__(module.RotationSupervisor)
    heartbeat = module.TaskHeartbeat('synthetic', 'One', getattr(module.OperationType, operation))
    heartbeat._process = SimpleNamespace(returncode=code)
    result = asyncio.run(item._monitor_task(heartbeat))
    assert result == getattr(module.TaskState, expected)


def test_actual_supervisor_typed_child_halt_never_advances_or_clears_checkpoint(gates, monkeypatch, tmp_path):
    _, module = rotation_module(monkeypatch, tmp_path)
    assert hasattr(module.TaskState, 'HALTED')
    item = module.RotationSupervisor(get_confirmed_live_channel=lambda: None)
    dispatched = []
    async def dispatch(channel, operation, _limit):
        dispatched.append(channel)
        return module.TaskHeartbeat('synthetic', channel, operation, state=module.TaskState.HALTED), module.TaskState.HALTED
    item._dispatch_channel = dispatch
    result = asyncio.run(item.run_rotation(channels=['One', 'Two']))
    assert dispatched == ['One'] and result.halted is True
    assert result.channels_processed == [] and module._clears == []


def test_actual_supervisor_persisted_stop_and_useful_unstopped_rotation(gates, monkeypatch, tmp_path):
    stop_path = gates.stop_file_path()
    cases, module = rotation_module(monkeypatch, tmp_path)
    monkeypatch.setenv('YT_AUTOMATION_STOP_FILE', str(stop_path))
    item = module.RotationSupervisor(get_confirmed_live_channel=lambda: None)
    dispatched, *_ = cases._fake_rotation_work(module, item)
    good = asyncio.run(item.run_rotation(channels=['Live', 'Other']))
    assert good.channels_processed == dispatched == ['Live', 'Other'] and good.halted is False
    cleared_before = list(module._clears)
    gates.latch_comment_quality_stop('review_rejected')
    halted = asyncio.run(item.run_rotation(channels=['Live', 'Other']))
    assert halted.halted is True and halted.channels_processed == []
    assert module._clears == cleared_before
    empty = asyncio.run(item.run_rotation(channels=[]))
    assert empty.halted is True and module._clears == cleared_before


def test_private_context_intake_remains_available_and_cannot_clear_quality_stop(gates, tmp_path):
    from modules.communication.livechat.src.operator_command_queue import OperatorCommandQueue, enqueue_operator_command
    record = gates.latch_comment_quality_stop('review_rejected')['incident']
    inbox, ack, state = (tmp_path / name for name in ('manifest.json', 'acks.json', 'state.json'))
    queue = OperatorCommandQueue(None, inbox, ack, state, poll_interval_seconds=0)
    for command in (
        {'id': 'context', 'action': 'set_context', 'payload': {'message': 'Bounded private topic', 'surfaces': ['comments']}},
        {'id': 'clear', 'action': 'clear_context', 'payload': {}},
    ):
        enqueue_operator_command(command, command_path=inbox, acknowledgement_path=ack)
        result = asyncio.run(queue.poll_once())
        assert result['results'][-1]['status'] == 'accepted'
        assert gates.read_comment_quality_stop() == record


def test_actual_dae_retains_unpersisted_halt_before_a_fresh_dispatch(gates):
    relative = 'modules/communication/livechat/src/auto_moderator_dae.py'
    owner = source_class(relative, 'AutoModeratorDAE', ['_comments_halted', '_run_comment_engagement'])
    item = object.__new__(owner); item._comment_engagement_status = {}
    assert item._comments_halted() is None
    receipt = item._comments_halted({'halted_for_comments_stop': True, 'quality_stop_persisted': False})
    assert receipt['state'] == 'halted' and receipt['quality_stop_persisted'] is False
    assert not gates.stop_file_path().exists()
    asyncio.run(item._run_comment_engagement(None, 'receiving-channel', None, 1, 'subprocess'))
    assert item._comment_engagement_status['receiving-channel']['all_processed'] is False
    assert item._comments_halted() == receipt


def test_actual_owned_lifecycle_refuses_a_sticky_coordinator_halt(gates, monkeypatch):
    _, module = runner_module(monkeypatch)
    receipt = {'state': 'halted', 'halted_for_comments_stop': True,
               'quality_stop_persisted': False, 'stats': {'all_processed': False}}
    calls = []
    async def run(**_kwargs):
        calls.append(True)
        return {'stats': {'comments_processed': 1}}
    item = SimpleNamespace(_comments_halt=lambda: True, _comments_halt_receipt=receipt,
                           _active_engagements={}, _is_live_channel=lambda *_: False)
    result = asyncio.run(module._lifecycle.run_owned_engagement(item, SimpleNamespace(run_engagement=run),
        channel_id='receiving-channel', video_id=None, max_comments=1))
    assert result == receipt and calls == []


@pytest.mark.parametrize('active', [False, True])
def test_actual_inbox_wait_allows_halted_live_handoff_only_after_owned_work_settles(gates, active):
    relative = 'modules/communication/livechat/src/auto_moderator_dae.py'
    owner = source_class(relative, 'AutoModeratorDAE', ['_comments_halted', '_wait_for_inbox_clear'])
    item = object.__new__(owner)
    item._comment_engagement_active_channel = None
    item._comment_engagement_status = {}
    namespace = owner._wait_for_inbox_clear.__globals__
    namespace['group_channels_by_browser'] = lambda **_k: {'edge': [{'id': 'unattempted-edge'}]}
    gates.latch_comment_quality_stop('review_rejected')
    async def exercise():
        release, settled, sleeps = asyncio.Event(), [], []
        async def hold():
            await release.wait()
            settled.append(True)
        task = asyncio.create_task(hold()) if active else None
        item._comment_engagement_task = task
        async def wait_owned(_seconds):
            assert active and task is not None and not task.done(), 'Settled halt must not retry or wait for missing inbox evidence'
            sleeps.append(True)
            release.set()
            await asyncio.sleep(0)
        namespace['asyncio'] = SimpleNamespace(sleep=wait_owned)
        try:
            assert await item._wait_for_inbox_clear() is None
            assert sleeps == ([True] if active else [])
            assert settled == ([True] if active else [])
            assert not item._comment_engagement_status
        finally:
            release.set()
            if task is not None:
                await task
    asyncio.run(exercise())
