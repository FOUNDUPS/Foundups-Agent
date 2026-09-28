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
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import List, Optional
from unittest.mock import AsyncMock, Mock, patch


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
    with patch.dict(sys.modules, replacements):
        _load_producer_declarations(source / 'simple_posting_orchestrator.py', producer)
        spec.loader.exec_module(leaf)
    producer.SimplePostingOrchestrator.assert_not_called()
    return leaf, producer


def _load_producer_declarations(path, module):
    """Keep actual enum/dataclass contracts without running adapters or history IO."""
    tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
    names = ['Platform', 'PostResult', 'PostResponse']
    nodes = [n for n in tree.body if isinstance(n, ast.ClassDef) and n.name in names]
    if [n.name for n in nodes] != names:
        raise AssertionError('Producer declarations changed; requalify the fixture')
    declarations = ast.Module(body=nodes, type_ignores=[])
    exec(compile(declarations, str(path), 'exec'), module.__dict__)


_scheduler_leaf, _producer = _load_scheduler_leaf()
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
