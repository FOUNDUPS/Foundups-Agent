#!/usr/bin/env python3
"""
Test suite for AutonomousActionScheduler
WSP Compliance: WSP 5 (Testing Coverage), WSP 6 (Test Audit)
"""

# === UTF-8 ENFORCEMENT (WSP 90) ===
import sys
import io
if __name__ == '__main__' and sys.platform.startswith('win'):
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except (OSError, ValueError):
        # Ignore if stdout/stderr already wrapped or closed
        pass
# === END UTF-8 ENFORCEMENT ===


import ast
import importlib.util
import types
import unittest
import asyncio
import hashlib
import json
from contextlib import ExitStack, chdir
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import List, Optional
from tempfile import TemporaryDirectory
from unittest.mock import AsyncMock, Mock, patch


def _load_atomic_leaf():
    """Load the unchanged stdlib writer without repository package initializers."""
    name = 'modules.infrastructure.shared_utilities.runtime_atomic_replace'
    path = Path(__file__).resolve().parents[4] / 'modules/infrastructure/shared_utilities/runtime_atomic_replace.py'
    spec = importlib.util.spec_from_file_location(name, path)
    writer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(writer)
    return writer


def _load_scheduler_leaf():
    """Load the real leaf with only inert producer declarations and a denied ctor."""
    source = Path(__file__).resolve().parents[1] / 'src'
    package_name = '_scheduler_execution_qualification'
    package = types.ModuleType(package_name)
    package.__path__ = []
    producer = types.ModuleType(package_name + '.simple_posting_orchestrator')
    producer.__dict__.update(dataclass=dataclass, Enum=Enum, datetime=datetime,
                             List=List, Optional=Optional)
    producer.SimplePostingOrchestrator = Mock(
        side_effect=AssertionError('Real posting constructor is not admitted'))
    path = source / 'autonomous_action_scheduler.py'
    spec = importlib.util.spec_from_file_location(
        package_name + '.autonomous_action_scheduler', path)
    leaf = importlib.util.module_from_spec(spec)
    replacements = {package_name: package, producer.__name__: producer,
                    leaf.__name__: leaf}
    writer = _load_atomic_leaf()
    for name in ('modules', 'modules.infrastructure', 'modules.infrastructure.shared_utilities'):
        namespace = types.ModuleType(name)
        namespace.__path__ = []
        replacements[name] = namespace
    replacements[writer.__name__] = writer
    with patch.dict(sys.modules, replacements):
        _load_producer_declarations(source / 'simple_posting_orchestrator.py', producer)
        spec.loader.exec_module(leaf)
    producer.SimplePostingOrchestrator.assert_not_called()
    return leaf, producer, writer


def _load_producer_declarations(path, module):
    """Keep actual enum/dataclass contracts without running adapters or history IO."""
    tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
    names = ['Platform', 'PostResult', 'PostResponse']
    nodes = [n for n in tree.body if isinstance(n, ast.ClassDef) and n.name in names]
    if [n.name for n in nodes] != names:
        raise AssertionError('Producer declarations changed; requalify the fixture')
    declarations = ast.Module(body=nodes, type_ignores=[])
    exec(compile(declarations, str(path), 'exec'), module.__dict__)


_scheduler_leaf, _producer, _atomic_writer = _load_scheduler_leaf()
AutonomousActionScheduler = _scheduler_leaf.AutonomousActionScheduler
ActionType = _scheduler_leaf.ActionType


class _FixedClock:
    @classmethod
    def now(cls):
        return datetime(2026, 9, 28, 12, 0, 0)


_INVALID_RESPONSE = 'Invalid posting response: expected nonempty typed results'
_INVALID_ITEM = 'Invalid posting response: malformed platform result'
_INVALID_COVERAGE = 'Invalid posting response: platform coverage mismatch'
_INVALID_COUNTS = 'Invalid posting response: inconsistent counts'
_INCOMPLETE = 'Posting did not succeed on all requested platforms'
_INVALID_TARGETS = ('Invalid posting platforms: expected a nonempty unique '
                    'list of supported values')


def _response(flags):
    results = [_producer.PostResult(success=success, platform=platform,
                                   message='synthetic result', timestamp=_FixedClock.now())
               for platform, success in zip(
                   [_producer.Platform.LINKEDIN, _producer.Platform.X_TWITTER], flags)]
    return _producer.PostResponse(request_id='fixture-response', results=results,
                                  success_count=sum(flags), failure_count=len(flags)-sum(flags),
                                  timestamp=_FixedClock.now())


def _assert_completion(test, action, error):
    test.assertIs(test.scheduler.scheduled_actions[action.id], action)
    test.assertEqual(action.status, 'failed' if error else 'executed')
    test.assertEqual(action.error, error)
    successes = [call for call in test.log.info.call_args_list if '[OK]' in call.args[0]]
    test.assertEqual(len(successes), 0 if error else 1)
    test.assertEqual(test.log.error.call_count, 1 if error else 0)
    test.scheduler.save_schedule.assert_called_once_with()


async def _stream_case(test, response, error=None, failure=None, targets=None, mutate=False):
    platforms = ([_producer.Platform.LINKEDIN, _producer.Platform.X_TWITTER]
                 if targets is None else targets)
    action = test._action(ActionType.POST_SOCIAL, {
        'platforms': [p.value for p in platforms], 'content': 'synthetic content',
        'metadata': {'stream_url': 'https://example.invalid/stream', 'stream_title': 'fixture'}})
    test.post.side_effect = failure
    if mutate:
        async def change_targets(**kwargs):
            action.parameters['platforms'][:] = ['x_twitter']
            return response
        test.post.side_effect = change_targets
    test.post.return_value = response
    results = await test.scheduler.execute_pending_actions()
    test.post.assert_awaited_once_with(stream_title='fixture',
                                      stream_url='https://example.invalid/stream',
                                      platforms=platforms)
    test.assertEqual(test.post.call_count, 1)
    test.assertEqual(len(results), 1)
    test.assertEqual(results[0][0], action.id)
    _assert_completion(test, action, str(failure) if failure else error)
    if failure:
        test.assertIsNone(action.result)
        test.assertEqual(results[0][1], {'error': str(failure)})
    else:
        test.assertIs(action.result, response)
        test.assertIs(results[0][1], response)
    test.assertEqual(await test.scheduler.execute_pending_actions(), [])
    test.assertEqual(test.post.call_count, 1)
    test.scheduler.save_schedule.assert_called_once_with()


async def _rejected_action(test, kind, error, parameters=None):
    action = test._action(kind, parameters)
    test.assertEqual(await test.scheduler.execute_pending_actions(),
                     [(action.id, {'error': error})])
    _assert_completion(test, action, error)
    test.assertIsNone(action.result)
    test.post.assert_not_called()
    test.post.assert_not_awaited()
    test.assertFalse(any('Would post:' in call.args[0] for call in test.log.info.call_args_list))
    test.assertEqual(await test.scheduler.execute_pending_actions(), [])
    test.post.assert_not_called()
    test.scheduler.save_schedule.assert_called_once_with()


class TestExecutionEvidence(unittest.IsolatedAsyncioTestCase):
    """Fixed in-memory completion contracts; no delivery, save or RSI claim."""

    def setUp(self):
        self.scheduler = AutonomousActionScheduler.__new__(AutonomousActionScheduler)
        self.post = AsyncMock(side_effect=AssertionError('Unexpected posting call'))
        self.scheduler.orchestrator = types.SimpleNamespace(post_stream_notification=self.post)
        self.scheduler.scheduled_actions = {}
        self.scheduler.save_schedule = Mock()
        self.log = Mock()
        for name, value in [('datetime', _FixedClock), ('logger', self.log)]:
            handle = patch.object(_scheduler_leaf, name, value)
            handle.start()
            self.addCleanup(handle.stop)

    def tearDown(self):
        _producer.SimplePostingOrchestrator.assert_not_called()

    def _action(self, kind, parameters=None, status='pending', delay=0):
        action = _scheduler_leaf.ScheduledAction(
            id='fixture-' + kind.value, action_type=kind,
            description='synthetic scheduler evidence', parameters=parameters or {},
            scheduled_time=_FixedClock.now() + timedelta(seconds=delay),
            requested_by='012', requested_at=_FixedClock.now(), status=status)
        self.scheduler.scheduled_actions[action.id] = action
        return action

    async def test_non_stream_post_rejects_unsupported(self):
        await _rejected_action(self, ActionType.POST_SOCIAL,
                               'Unsupported scheduled action: post_social',
                               {'platforms': ['linkedin'], 'content': 'synthetic content'})

    async def test_stream_check_rejects_unsupported(self):
        await _rejected_action(self, ActionType.CHECK_STREAM,
                               'Unsupported scheduled action: check_stream')

    async def test_custom_action_rejects_unsupported(self):
        await _rejected_action(self, ActionType.CUSTOM, 'Unsupported scheduled action: custom')

    async def test_message_rejects_unsupported(self):
        await _rejected_action(self, ActionType.SEND_MESSAGE,
                               'Unsupported scheduled action: send_message')

    async def test_code_action_rejects_unsupported(self):
        await _rejected_action(self, ActionType.EXECUTE_CODE,
                               'Unsupported scheduled action: execute_code')

    async def test_reminder_records_only_its_documented_local_log(self):
        expected = {'reminded': True, 'message': 'synthetic reminder'}
        action = self._action(ActionType.REMIND, {'message': 'synthetic reminder'})
        results = await self.scheduler.execute_pending_actions()
        self.assertEqual(results, [(action.id, expected)])
        self.assertIs(results[0][1], action.result)
        _assert_completion(self, action, None)
        self.post.assert_not_called()
        self.assertTrue(any('REMINDER: synthetic reminder' in call.args[0]
                            for call in self.log.info.call_args_list))

    async def test_stream_all_success_preserves_producer_response(self):
        await _stream_case(self, _response([True, True]))

    async def test_stream_all_failure_rejects_preserving_response(self):
        await _stream_case(self, _response([False, False]), _INCOMPLETE)

    async def test_stream_partial_rejects_preserving_response(self):
        await _stream_case(self, _response([True, False]), _INCOMPLETE)

    async def test_stream_empty_rejects_preserving_response(self):
        await _stream_case(self, _response([]), _INVALID_RESPONSE)

    async def test_stream_none_rejects(self):
        await _stream_case(self, None, _INVALID_RESPONSE)

    async def test_stream_exception_marks_failure(self):
        await _stream_case(self, None, failure=RuntimeError('synthetic failure'))

    async def test_stream_success_dictionary_rejects(self):
        await _stream_case(self, {'posted': True}, _INVALID_RESPONSE)

    async def test_stream_invalid_result_element_rejects(self):
        for shape in ('invalid_item', 'tuple', 'none'):
            with self.subTest(shape=shape):
                self._reset_case()
                response = _response([True, True])
                if shape == 'invalid_item':
                    response.results[0] = {'success': True, 'platform': 'linkedin'}
                else:
                    response.results = tuple(response.results) if shape == 'tuple' else None
                await _stream_case(self, response,
                                   _INVALID_ITEM if shape == 'invalid_item' else _INVALID_RESPONSE)

    async def test_stream_nonboolean_success_rejects(self):
        response = _response([True, True])
        response.results[0].success = 1
        await _stream_case(self, response, _INVALID_ITEM)

    async def test_stream_inconsistent_counts_rejects(self):
        variants = [('success_count', 1, False), ('success_count', 2.0, False),
                    ('failure_count', False, False), ('failure_count', 0.0, False),
                    ('success_count', True, True)]
        for field, value, single in variants:
            with self.subTest(field=field, value=repr(value), single=single):
                self._reset_case()
                response = _response([True] if single else [True, True])
                setattr(response, field, value)
                targets = [_producer.Platform.LINKEDIN] if single else None
                await _stream_case(self, response, _INVALID_COUNTS, targets=targets)

    def _reset_case(self):
        self.scheduler.scheduled_actions.clear()
        self.scheduler.save_schedule.reset_mock()
        self.post.reset_mock()
        self.log.reset_mock()

    async def test_stream_missing_target_rejects(self):
        await _stream_case(self, _response([True]), _INVALID_COVERAGE)

    async def test_stream_extra_target_rejects(self):
        await _stream_case(self, _response([True, True]), _INVALID_COVERAGE,
                           targets=[_producer.Platform.LINKEDIN])

    async def test_stream_duplicate_target_result_rejects(self):
        response = _response([True, True])
        response.results[1].platform = _producer.Platform.LINKEDIN
        await _stream_case(self, response, _INVALID_COVERAGE)

    async def test_stream_nonplatform_value_rejects(self):
        response = _response([True, True])
        response.results[0].platform = 'linkedin'
        await _stream_case(self, response, _INVALID_ITEM)

    async def _invalid_targets(self, targets):
        await _rejected_action(self, ActionType.POST_SOCIAL, _INVALID_TARGETS,
                               {'platforms': targets, 'content': 'synthetic',
                                'metadata': {'stream_url': 'https://example.invalid/stream'}})

    async def test_request_empty_targets_reject_before_effect(self):
        await self._invalid_targets([])

    async def test_request_duplicate_targets_reject_before_effect(self):
        await self._invalid_targets(['linkedin', 'linkedin'])

    async def test_request_unknown_target_reject_before_effect(self):
        await self._invalid_targets(['unknown'])

    async def test_request_nonlist_targets_reject_before_effect(self):
        await self._invalid_targets('linkedin')

    async def test_stream_target_snapshot_survives_action_mutation(self):
        await _stream_case(self, _response([True, True]), mutate=True)

    async def test_no_due_actions_have_no_calls_or_mutations(self):
        actions = [self._action(ActionType.POST_SOCIAL, delay=1),
                   self._action(ActionType.CUSTOM, status='cancelled'),
                   self._action(ActionType.REMIND, status='failed'),
                   self._action(ActionType.CHECK_STREAM, status='executed')]
        before = {a.id: vars(a).copy() for a in actions}
        self.assertEqual(await self.scheduler.execute_pending_actions(), [])
        self.assertEqual({a.id: vars(a) for a in actions}, before)
        for action in actions:
            self.assertIs(self.scheduler.scheduled_actions[action.id], action)
        self.post.assert_not_called()
        self.post.assert_not_awaited()
        self.scheduler.save_schedule.assert_not_called()
        self.log.info.assert_not_called()
        self.log.error.assert_not_called()

def _persistence_errors(test, operation):
    marker = 'Error ' + operation + ' schedule:'
    return [call.args[0] for call in test.log.error.call_args_list
            if marker in call.args[0]]


def _persistence_record(test, before, after, restored):
    """Preserve synthetic file bytes in hosted output before scratch cleanup."""
    print('PERSISTENCE_EVIDENCE ' + json.dumps({
        'case': test._testMethodName,
        'before_utf8': before.decode('utf-8') if before is not None else None,
        'after_utf8': after.decode('utf-8') if after is not None else None,
        'before_sha256': hashlib.sha256(before).hexdigest() if before is not None else None,
        'after_sha256': hashlib.sha256(after).hexdigest() if after is not None else None,
        'save_errors': _persistence_errors(test, 'saving'),
        'load_errors': _persistence_errors(test, 'loading'),
        'in_memory_status': {key: action.status for key, action in test.scheduler.scheduled_actions.items()},
        'restored_ids': sorted(restored.scheduled_actions),
    }, sort_keys=True))


def _expected_post(flags):
    return {'request_id': 'fixture-response', 'success_count': sum(flags),
            'failure_count': 2 - sum(flags), 'timestamp': '2026-09-28T12:00:00',
            'results': [{'success': flag, 'platform': platform, 'message': 'synthetic result',
                         'timestamp': '2026-09-28T12:00:00', 'url': url}
                        for flag, platform, url in zip(flags, ['linkedin', 'x_twitter'],
                                                     ['https://example.invalid/post/1', None])]}


def _stored_response(flags):
    response = _response(flags)
    response.results[0].url = 'https://example.invalid/post/1'
    return response


async def _typed_persistence_roundtrip(test, flags, mixed=False):
    future = test._action(ActionType.REMIND, {'message': 'future fixture'}, delay=3600) if mixed else None
    future_fields = deepcopy(vars(future)) if future else None
    action = test._action(ActionType.POST_SOCIAL, {
        'platforms': ['linkedin', 'x_twitter'], 'content': 'synthetic content',
        'metadata': {'stream_url': 'https://example.invalid/stream', 'stream_title': 'fixture'}})
    before = test._seed()
    test.assertEqual(set(json.loads(before)), {action.id, future.id} if mixed else {action.id})
    response = _stored_response(flags)
    response_fields = deepcopy(response)
    original_items = tuple(response.results)
    test.post.return_value = response
    test._contained()
    result = await test.scheduler.execute_pending_actions()
    test.assertEqual(len(result), 1)
    test.assertEqual(result[0][0], action.id)
    test.assertIs(result[0][1], response)
    test.assertIs(action.result, response)
    test.assertEqual([item.success for item in action.result.results], flags)
    test.assertEqual(action.status, 'executed' if all(flags) else 'failed')
    test.assertEqual(action.error, None if all(flags) else _INCOMPLETE)
    test.post.assert_awaited_once_with(stream_title='fixture', stream_url='https://example.invalid/stream',
                                      platforms=[_producer.Platform.LINKEDIN, _producer.Platform.X_TWITTER])
    test.assertEqual(test.post.call_count, 1)
    test.assertEqual(sum('[OK]' in call.args[0] for call in test.log.info.call_args_list), int(all(flags)))
    after = test.path.read_bytes()
    restored = test._reload()
    _persistence_record(test, before, after, restored)
    test.assertEqual(_persistence_errors(test, 'saving'), [])
    test.assertEqual(_persistence_errors(test, 'loading'), [])
    test.assertEqual(test.log.error.call_count, 0 if all(flags) else 1)
    test.assertNotEqual(after, before)
    test.assertEqual(json.loads(after)[action.id]['result'], _expected_post(flags))
    test.assertEqual(response, response_fields)
    test.assertEqual(len(response.results), len(original_items))
    test.assertTrue(all(a is b for a, b in zip(response.results, original_items)))
    test.assertEqual(vars(restored.scheduled_actions[action.id]), dict(vars(action), result=_expected_post(flags)))
    test.assertEqual(await test.scheduler.execute_pending_actions(), [])
    test.assertEqual(test.post.await_count, 1)
    test.assertEqual(test.path.read_bytes(), after)
    if future:
        test.assertIs(test.scheduler.scheduled_actions[future.id], future)
        test.assertEqual(vars(future), future_fields)
        test.assertEqual(vars(restored.scheduled_actions[future.id]), future_fields)
    test.assertEqual(await restored.execute_pending_actions(), [])
    test.assertEqual(test.path.read_bytes(), after)
    restored.orchestrator.post_stream_notification.assert_not_called()


class _PersistenceFixture(unittest.IsolatedAsyncioTestCase):
    """Sequential disposable-file effects shared by the two explicit selections."""

    _action = TestExecutionEvidence._action

    def setUp(self):
        self.initial_cwd, self.root = Path.cwd(), None
        self.addCleanup(self._released)
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.root = Path(self.stack.enter_context(TemporaryDirectory(prefix='scheduler-persistence-'))).resolve()
        self.stack.enter_context(chdir(self.root))
        self.path = Path('memory/schedule.json')
        self.expected_paths = {'memory', 'memory/schedule.json'}
        self.log = Mock()
        clock = types.SimpleNamespace(now=_FixedClock.now, fromisoformat=datetime.fromisoformat)
        self.stack.enter_context(patch.object(_scheduler_leaf, 'datetime', clock))
        self.stack.enter_context(patch.object(_scheduler_leaf, 'logger', self.log))
        self.scheduler = self._fresh()
        self.post = self.scheduler.orchestrator.post_stream_notification

    def _released(self):
        self.assertEqual(Path.cwd(), self.initial_cwd)
        if self.root is not None:
            self.assertFalse(self.root.exists())

    def tearDown(self):
        _producer.SimplePostingOrchestrator.assert_not_called()
        self.assertEqual({p.relative_to(self.root).as_posix() for p in self.root.rglob('*')},
                         self.expected_paths)

    def _fresh(self):
        scheduler = AutonomousActionScheduler.__new__(AutonomousActionScheduler)
        scheduler.schedule_file = str(self.path)
        scheduler.scheduled_actions = {}
        scheduler.orchestrator = types.SimpleNamespace(
            post_stream_notification=AsyncMock(side_effect=AssertionError('Unexpected posting call')))
        return scheduler

    def _contained(self):
        self.assertEqual(Path.cwd(), self.root)
        self.assertTrue(self.path.resolve().is_relative_to(self.root))
        self.assertEqual(self.scheduler.schedule_file, str(self.path))

    def _seed(self):
        self._contained()
        self.assertIsNone(self.scheduler.save_schedule())
        self.log.error.assert_not_called()
        before = self.path.read_bytes()
        data = json.loads(before)
        self.assertEqual(set(data), set(self.scheduler.scheduled_actions))
        self.assertTrue(all(row['status'] == 'pending' and row['result'] is None for row in data.values()))
        return before

    def _reload(self):
        self._contained()
        restored = self._fresh()
        self.assertEqual(restored.scheduled_actions, {})
        self.assertEqual(restored.schedule_file, self.scheduler.schedule_file)
        restored.load_schedule()
        return restored


class TestPersistenceEvidence(_PersistenceFixture):
    """Two original controls and four full-field typed round-trip requirements."""

    def test_pending_roundtrip_control(self):
        action = self._action(ActionType.REMIND, {'message': 'pending fixture'}, delay=3600)
        payload = self._seed()
        data = json.loads(payload)[action.id]
        expected = dict(vars(action), action_type=action.action_type.value,
                        scheduled_time=action.scheduled_time.isoformat(), requested_at=action.requested_at.isoformat())
        self.assertEqual(data, expected)
        restored = self._reload()
        loaded = restored.scheduled_actions[action.id]
        self.assertEqual(vars(loaded), vars(action))
        self.assertIsInstance(loaded.scheduled_time, datetime)
        self.assertIsInstance(loaded.requested_at, datetime)
        self.assertIs(loaded.action_type, action.action_type)
        self.log.error.assert_not_called()
        self.post.assert_not_called()
        restored.orchestrator.post_stream_notification.assert_not_called()
        _persistence_record(self, None, payload, restored)

    async def test_reminder_terminal_roundtrip_no_repeat_control(self):
        action = self._action(ActionType.REMIND, {'message': 'local fixture'})
        self._contained()
        result = await self.scheduler.execute_pending_actions()
        self.assertEqual(result, [(action.id, {'reminded': True, 'message': 'local fixture'})])
        self.assertIs(result[0][1], action.result)
        self.assertEqual(action.status, 'executed')
        self.assertIsNone(action.error)
        self.assertEqual(sum('REMINDER:' in call.args[0] for call in self.log.info.call_args_list), 1)
        payload = self.path.read_bytes()
        self.assertEqual(json.loads(payload)[action.id]['status'], 'executed')
        restored = self._reload()
        self.assertEqual(vars(restored.scheduled_actions[action.id]), vars(action))
        self.log.info.reset_mock()
        self.assertEqual(await restored.execute_pending_actions(), [])
        self.log.info.assert_not_called()
        self.log.error.assert_not_called()
        self.assertEqual(self.path.read_bytes(), payload)
        self.post.assert_not_called()
        restored.orchestrator.post_stream_notification.assert_not_called()
        _persistence_record(self, None, payload, restored)

    async def test_complete_typed_result_roundtrip(self):
        self.post.side_effect = None
        await _typed_persistence_roundtrip(self, [True, True])

    async def test_partial_typed_result_roundtrip(self):
        self.post.side_effect = None
        await _typed_persistence_roundtrip(self, [True, False])

    async def test_failed_typed_result_roundtrip(self):
        self.post.side_effect = None
        await _typed_persistence_roundtrip(self, [False, False])

    async def test_typed_result_preserves_future_schedule(self):
        self.post.side_effect = None
        await _typed_persistence_roundtrip(self, [True, True], mixed=True)


def _unsupported_save(test, member, seeded=True):
    action = test._action(ActionType.REMIND, {'message': 'old'})
    before = test._seed() if seeded else None
    if not seeded:
        test.expected_paths = set()
    setattr(action, member, {'unsupported': object()})
    fields = vars(action).copy()
    with patch.object(_scheduler_leaf, 'atomic_replace_runtime_text',
                      wraps=_atomic_writer.atomic_replace_runtime_text, create=True) as writer:
        test.assertIsNone(test.scheduler.save_schedule())
    after = test.path.read_bytes() if test.path.exists() else None
    restored = test._reload()
    _persistence_record(test, before, after, restored)
    writer.assert_not_called()
    test.assertEqual(after, before)
    test.assertEqual(vars(action), fields)
    test.assertEqual(len(_persistence_errors(test, 'saving')), 1)
    test.assertEqual(_persistence_errors(test, 'loading'), [])
    test.post.assert_not_called()


def _publication_failure(test, seam, published=False):
    action = test._action(ActionType.REMIND, {'message': 'old'})
    before, original = test._seed(), deepcopy(vars(action))
    action.status, action.description, action.result = 'executed', 'new', {'reminded': True}
    current = deepcopy(vars(action))
    owner, attribute = (_atomic_writer.os, 'fsync') if seam == 'file_sync' else (_atomic_writer, seam)
    error = OSError('injected ' + seam)
    def fail_write(descriptor, payload):
        _atomic_writer.os.write(descriptor, payload[:5])
        raise error
    effect = fail_write if seam == '_write_all' else error
    with patch.object(owner, attribute, side_effect=effect) as failure, patch.object(
            _scheduler_leaf, 'atomic_replace_runtime_text',
            wraps=_atomic_writer.atomic_replace_runtime_text, create=True) as writer:
        test.assertIsNone(test.scheduler.save_schedule())
    after, restored = test.path.read_bytes(), test._reload()
    _persistence_record(test, before, after, restored)
    writer.assert_called_once()
    failure.assert_called_once()
    test.assertEqual(writer.call_args.args[0], test.path)
    test.assertEqual(vars(action), current)
    test.assertEqual(vars(restored.scheduled_actions[action.id]), current if published else original)
    test.assertEqual(len(_persistence_errors(test, 'saving')), 1)
    test.assertIn(str(error), _persistence_errors(test, 'saving')[0])
    test.assertEqual(_persistence_errors(test, 'loading'), [])
    if published:
        test.assertNotEqual(after, before)
        test.assertEqual(json.loads(after)[action.id]['status'], 'executed')
    else:
        test.assertEqual(after, before)
    test.post.assert_not_called()


class TestPublicationEvidence(_PersistenceFixture):
    """Fixed serialization/publication boundaries; no crash or Windows proof."""

    def test_unsupported_parameter_preserves_prior(self):
        _unsupported_save(self, 'parameters')

    def test_unsupported_result_preserves_prior(self):
        _unsupported_save(self, 'result')

    def test_unsupported_first_save_remains_absent(self):
        _unsupported_save(self, 'result', seeded=False)

    def test_temporary_write_failure_preserves_prior(self):
        _publication_failure(self, '_write_all')

    def test_file_sync_failure_preserves_prior(self):
        _publication_failure(self, 'file_sync')

    def test_replace_failure_preserves_prior(self):
        _publication_failure(self, '_atomic_replace_path')

    def test_parent_sync_failure_retains_complete_publication(self):
        _publication_failure(self, '_fsync_parent_directory', published=True)

    async def test_legacy_json_result_compatibility(self):
        actions = [self._action(ActionType.REMIND, status='failed'),
                   self._action(ActionType.CUSTOM, status='cancelled'),
                   self._action(ActionType.CHECK_STREAM, delay=3600)]
        actions[0].result, actions[1].result = {'list': [1, None, 'old']}, [False, 2.5]
        expected = {a.id: deepcopy(vars(a)) for a in actions}
        data = {a.id: dict(vars(a), action_type=a.action_type.value,
                          scheduled_time=a.scheduled_time.isoformat(), requested_at=a.requested_at.isoformat()) for a in actions}
        self.path.parent.mkdir()
        self.path.write_text(json.dumps(data), encoding='utf-8')
        before, restored = self.path.read_bytes(), self._reload()
        self.assertEqual({key: vars(a) for key, a in restored.scheduled_actions.items()}, expected)
        self.assertIsNone(restored.save_schedule())
        self.assertEqual(json.loads(self.path.read_bytes()), data)
        self.assertEqual(await restored.execute_pending_actions(), [])
        self.log.error.assert_not_called()
        restored.orchestrator.post_stream_notification.assert_not_called()
        _persistence_record(self, before, self.path.read_bytes(), restored)

    def test_configured_parent_is_owned_destination(self):
        self.path = Path('alternate/deep/schedule.json')
        self.expected_paths = {'alternate', 'alternate/deep', 'alternate/deep/schedule.json'}
        self.scheduler.schedule_file = str(self.path)
        action = self._action(ActionType.REMIND, {'message': 'nested'}, delay=3600)
        self.assertIsNone(self.scheduler.save_schedule())
        self.log.error.assert_not_called()
        restored = self._reload()
        self.assertEqual(vars(restored.scheduled_actions[action.id]), vars(action))
        _persistence_record(self, None, self.path.read_bytes(), restored)

    def test_first_valid_typed_save_roundtrip(self):
        action = self._action(ActionType.POST_SOCIAL, status='executed')
        response = _stored_response([True, True])
        response_fields, original_items = deepcopy(response), tuple(response.results)
        action.result = response
        self.assertFalse(self.path.exists())
        self.assertIsNone(self.scheduler.save_schedule())
        after, restored = self.path.read_bytes(), self._reload()
        _persistence_record(self, None, after, restored)
        self.log.error.assert_not_called()
        self.assertIs(action.result, response)
        self.assertEqual(response, response_fields)
        self.assertEqual(len(response.results), len(original_items))
        self.assertTrue(all(a is b for a, b in zip(response.results, original_items)))
        self.assertEqual(json.loads(after)[action.id]['result'], _expected_post([True, True]))
        self.assertEqual(vars(restored.scheduled_actions[action.id]), dict(vars(action), result=_expected_post([True, True])))
        self.post.assert_not_called()


def _caller_seed(test, caller):
    future = test._action(ActionType.REMIND, {'message': 'unrelated future'}, delay=3600)
    del test.scheduler.scheduled_actions[future.id]
    future.id = 'fixture-future'
    test.scheduler.scheduled_actions[future.id] = future
    action = None
    if caller == 'execute':
        action = test._action(ActionType.POST_SOCIAL, {
            'platforms': ['linkedin', 'x_twitter'], 'content': 'synthetic content',
            'metadata': {'stream_url': 'https://example.invalid/stream', 'stream_title': 'fixture'}})
    elif caller == 'cancel':
        action = test._action(ActionType.REMIND, {'message': 'cancel fixture'})
    before = test._seed()
    test.log.reset_mock()
    return action, future, before


async def _call_mutator(test, caller, action):
    if caller == 'create':
        test.scheduler.time_patterns = {}
        with patch('uuid.uuid4', return_value=types.SimpleNamespace(hex='0123456789abcdef' * 2)):
            return test.scheduler.understand_command('remind me to review fixture')
    if caller == 'execute':
        return await test.scheduler.execute_pending_actions()
    return test.scheduler.cancel_action(action.id)


def _caller_return(test, caller, action, returned, response):
    test.assertIs(test.scheduler.scheduled_actions[action.id], action)
    test.assertIsNone(action.error)
    info = [call.args[0] for call in test.log.info.call_args_list]
    if caller == 'create':
        test.assertIs(returned, action)
        test.assertEqual(vars(action), dict(
            id='action_01234567', action_type=ActionType.REMIND,
            description='remind me to review fixture', parameters={'message': 'review fixture'},
            scheduled_time=_FixedClock.now() + timedelta(minutes=5), requested_by='012',
            requested_at=_FixedClock.now(), status='pending', result=None, error=None))
        test.assertEqual(sum('Scheduled as: ' + action.id in line for line in info), 1)
    elif caller == 'execute':
        test.assertEqual(len(returned), 1)
        test.assertEqual(returned[0][0], action.id)
        test.assertIs(returned[0][1], response)
        test.assertIs(action.result, response)
        test.assertEqual(action.status, 'executed')
        test.post.assert_awaited_once_with(stream_title='fixture',
            stream_url='https://example.invalid/stream',
            platforms=[_producer.Platform.LINKEDIN, _producer.Platform.X_TWITTER])
        test.assertEqual(sum('[OK] Completed scheduled operation ' + action.id in line for line in info), 1)
    else:
        test.assertIs(returned, True)
        test.assertEqual(action.status, 'cancelled')
        test.assertIsNone(action.result)
        test.assertEqual(sum('Cancelled action ' + action.id in line for line in info), 1)
    test.assertEqual(test.post.await_count, int(caller == 'execute'))
    test.assertEqual(test.post.call_count, int(caller == 'execute'))
    return info


async def _caller_reload_attempt(test, restored, action, caller, mode, primary_bytes):
    test.log.reset_mock()
    test.assertEqual(await test.scheduler.execute_pending_actions(), [])
    test.assertEqual(test.path.read_bytes(), primary_bytes)
    test.assertEqual(test.post.await_count, int(caller == 'execute'))
    test.log.info.assert_not_called()
    replay = mode == 'pre' and caller in ('execute', 'cancel')
    fresh_post = restored.orchestrator.post_stream_notification
    fresh_response = _stored_response([True, True])
    if replay and caller == 'execute':
        fresh_post.side_effect, fresh_post.return_value = None, fresh_response
    result = await restored.execute_pending_actions()
    test.assertEqual(len(result), int(replay))
    if replay:
        test.assertEqual(result[0][0], action.id)
        test.assertEqual(restored.scheduled_actions[action.id].status, 'executed')
        if caller == 'execute':
            test.assertIs(result[0][1], fresh_response)
            fresh_post.assert_awaited_once_with(stream_title='fixture',
                stream_url='https://example.invalid/stream',
                platforms=[_producer.Platform.LINKEDIN, _producer.Platform.X_TWITTER])
        else:
            test.assertEqual(result[0][1], {'reminded': True, 'message': 'cancel fixture'})
    else:
        test.assertEqual(test.path.read_bytes(), primary_bytes)
    test.assertEqual(fresh_post.await_count, int(replay and caller == 'execute'))
    test.assertEqual(fresh_post.call_count, int(replay and caller == 'execute'))
    reminders = sum('REMINDER: cancel fixture' in call.args[0] for call in test.log.info.call_args_list)
    test.assertEqual(reminders, int(replay and caller == 'cancel'))
    test.log.error.assert_not_called()
    return {'attempts': len(result), 'attempt_ids': [row[0] for row in result],
            'posting_awaits': fresh_post.await_count,
            'local_reminders': reminders, 'after_replay_sha256': hashlib.sha256(test.path.read_bytes()).hexdigest()}


async def _caller_case(test, caller, mode):
    action, future, before = _caller_seed(test, caller)
    future_fields = deepcopy(vars(future))
    response = _stored_response([True, True])
    if caller == 'execute':
        test.post.side_effect, test.post.return_value = None, response
    with ExitStack() as stack:
        fault = None
        if mode != 'normal':
            seam = '_atomic_replace_path' if mode == 'pre' else '_fsync_parent_directory'
            fault = stack.enter_context(patch.object(_atomic_writer, seam,
                side_effect=OSError('caller fixture ' + mode)))
        save = stack.enter_context(patch.object(test.scheduler, 'save_schedule', wraps=test.scheduler.save_schedule))
        returned = await _call_mutator(test, caller, action)
        save.assert_called_once_with()
        if fault is not None:
            fault.assert_called_once()
    action = returned if caller == 'create' else action
    info = _caller_return(test, caller, action, returned, response)
    after, restored = test.path.read_bytes(), test._reload()
    _persistence_record(test, before, after, restored)
    errors = _persistence_errors(test, 'saving')
    test.assertEqual(len(errors), int(mode != 'normal'))
    if errors:
        test.assertIn('caller fixture ' + mode, errors[0])
    test.assertEqual(_persistence_errors(test, 'loading'), [])
    expected = json.loads(before) if mode == 'pre' else {
        key: dict(vars(item), action_type=item.action_type.value,
                  scheduled_time=item.scheduled_time.isoformat(), requested_at=item.requested_at.isoformat(),
                  result=_expected_post([True, True]) if key == action.id and caller == 'execute' else item.result)
        for key, item in test.scheduler.scheduled_actions.items()}
    test.assertEqual(json.loads(after), expected)
    test.assertEqual(after == before, mode == 'pre')
    test.assertEqual(set(restored.scheduled_actions), set(expected))
    for key, row in expected.items():
        test.assertEqual(vars(restored.scheduled_actions[key]), dict(row,
            action_type=ActionType(row['action_type']), scheduled_time=datetime.fromisoformat(row['scheduled_time']),
            requested_at=datetime.fromisoformat(row['requested_at'])))
    test.assertIs(test.scheduler.scheduled_actions[future.id], future)
    test.assertEqual(vars(future), future_fields)
    primary = {'case': test._testMethodName, 'caller': caller, 'mode': mode,
               'returned_identity_verified': True, 'return_kind': type(returned).__name__,
               'memory_status': action.status, 'memory_error': action.error,
               'fault_call_count': 0 if fault is None else fault.call_count,
               'reloaded_status': {key: item.status for key, item in restored.scheduled_actions.items()},
               'primary_posting_awaits': test.post.await_count, 'primary_info': info, 'save_errors': errors}
    primary['reload_attempt'] = await _caller_reload_attempt(test, restored, action, caller, mode, after)
    print('CALLER_EVIDENCE ' + json.dumps(primary, sort_keys=True))


class TestCallerPersistenceEvidence(_PersistenceFixture):
    """Nine current-behavior witnesses, not durable acknowledgement acceptance."""

    async def test_create_normal(self):
        await _caller_case(self, 'create', 'normal')

    async def test_create_pre_replace_failure(self):
        await _caller_case(self, 'create', 'pre')

    async def test_create_post_replace_failure(self):
        await _caller_case(self, 'create', 'post')

    async def test_execute_normal(self):
        await _caller_case(self, 'execute', 'normal')

    async def test_execute_pre_replace_failure(self):
        await _caller_case(self, 'execute', 'pre')

    async def test_execute_post_replace_failure(self):
        await _caller_case(self, 'execute', 'post')

    async def test_cancel_normal(self):
        await _caller_case(self, 'cancel', 'normal')

    async def test_cancel_pre_replace_failure(self):
        await _caller_case(self, 'cancel', 'pre')

    async def test_cancel_post_replace_failure(self):
        await _caller_case(self, 'cancel', 'post')


class TestAutonomousActionScheduler(unittest.TestCase):
    """Test natural language understanding for 0102"""

    def setUp(self):
        self.scheduler = AutonomousActionScheduler()

    def test_time_parsing_minutes(self):
        """Test parsing 'in X minutes' format"""
        action = self.scheduler.understand_command("Post 'test' in 30 minutes")
        expected_time = datetime.now() + timedelta(minutes=30)

        # Allow 1 second tolerance for test execution time
        time_diff = abs((action.scheduled_time - expected_time).total_seconds())
        self.assertLess(time_diff, 2)

    def test_time_parsing_hours(self):
        """Test parsing 'in X hours' format"""
        action = self.scheduler.understand_command("Remind me in 2 hours")
        expected_time = datetime.now() + timedelta(hours=2)

        time_diff = abs((action.scheduled_time - expected_time).total_seconds())
        self.assertLess(time_diff, 2)

    def test_action_type_detection(self):
        """Test correct action type detection"""
        # Test post detection
        action = self.scheduler.understand_command("Post to LinkedIn")
        self.assertEqual(action.action_type, ActionType.POST_SOCIAL)

        # Test remind detection
        action = self.scheduler.understand_command("Remind me to check")
        self.assertEqual(action.action_type, ActionType.REMIND)

        # Test stream check detection
        action = self.scheduler.understand_command("Check the stream status")
        self.assertEqual(action.action_type, ActionType.CHECK_STREAM)

    def test_platform_detection(self):
        """Test platform extraction from command"""
        # LinkedIn detection
        action = self.scheduler.understand_command("Post to LinkedIn in 1 hour")
        self.assertIn('linkedin', action.parameters['platforms'])

        # X/Twitter detection
        action = self.scheduler.understand_command("Tweet this in 30 minutes")
        self.assertIn('x_twitter', action.parameters['platforms'])

        # Both platforms
        action = self.scheduler.understand_command("Post to both platforms now")
        self.assertIn('linkedin', action.parameters['platforms'])
        self.assertIn('x_twitter', action.parameters['platforms'])

    def test_content_extraction(self):
        """Test extracting quoted content from command"""
        action = self.scheduler.understand_command("Post 'Going live soon!' to LinkedIn")
        self.assertEqual(action.parameters['content'], "Going live soon!")

        # Test with double quotes
        action = self.scheduler.understand_command('Post "Hello World" to X')
        self.assertEqual(action.parameters['content'], "Hello World")

    def test_immediate_execution(self):
        """Test 'now' and 'immediately' parsing"""
        action = self.scheduler.understand_command("Post this now")
        time_diff = (action.scheduled_time - datetime.now()).total_seconds()
        self.assertLess(time_diff, 2)  # Should be within 2 seconds

        action = self.scheduler.understand_command("Post immediately")
        time_diff = (action.scheduled_time - datetime.now()).total_seconds()
        self.assertLess(time_diff, 2)

    def test_persistence(self):
        """Test schedule persistence"""
        # Create an action
        action = self.scheduler.understand_command("Post 'test' in 5 minutes")

        # Verify it's saved
        self.assertIn(action.id, self.scheduler.scheduled_actions)

        # Test cancellation
        result = self.scheduler.cancel_action(action.id)
        self.assertTrue(result)
        self.assertEqual(self.scheduler.scheduled_actions[action.id].status, "cancelled")

    async def test_pending_actions(self):
        """Test getting pending actions"""
        # Schedule multiple actions
        self.scheduler.understand_command("Post 'first' in 1 minute")
        self.scheduler.understand_command("Post 'second' in 2 minutes")
        self.scheduler.understand_command("Post 'third' in 3 minutes")

        pending = self.scheduler.get_pending_actions()
        self.assertEqual(len(pending), 3)

        # Verify they're sorted by time
        for i in range(len(pending) - 1):
            self.assertLess(pending[i].scheduled_time, pending[i+1].scheduled_time)

def run_tests():
    """Run only qualified evidence cases by default; legacy cases remain unqualified."""
    unittest.main(defaultTest='TestExecutionEvidence', verbosity=2)

if __name__ == "__main__":
    run_tests()
