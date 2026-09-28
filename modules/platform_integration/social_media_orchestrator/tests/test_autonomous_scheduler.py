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


class TestExecutionEvidence(unittest.IsolatedAsyncioTestCase):
    """Current-behavior witnesses, NOT acceptance of truthful posting or delivery.

    A pass means the documented defect/control was reproduced against the real
    scheduler leaf. Save is a spy, so no persistence or external effect is proved.
    """

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

    async def _non_effect(self, kind, expected, parameters=None):
        action = self._action(kind, parameters)
        results = await self.scheduler.execute_pending_actions()
        self.assertEqual(results, [(action.id, expected)])
        self.assertEqual(action.status, 'executed')
        self.assertEqual(action.result, expected)
        self.assertIs(self.scheduler.scheduled_actions[action.id], action)
        self.assertIs(results[0][1], action.result)
        self.assertIsNone(action.error)
        self.post.assert_not_called()
        self.post.assert_not_awaited()
        self.scheduler.save_schedule.assert_called_once_with()
        self.log.info.assert_any_call('[0102 EXECUTOR] [OK] Successfully executed ' + action.id)
        self.log.error.assert_not_called()

    async def test_non_stream_post_claims_success_without_posting(self):
        await self._non_effect(
            ActionType.POST_SOCIAL, {'posted': True, 'platforms': ['linkedin']},
            {'platforms': ['linkedin'], 'content': 'synthetic content'})
        self.log.info.assert_any_call('[0102 EXECUTOR] Would post: synthetic content')

    async def test_stream_check_claims_success_without_resolver(self):
        await self._non_effect(ActionType.CHECK_STREAM, {'checked': True})
        self.log.info.assert_any_call('[0102 EXECUTOR] Checking stream status...')

    async def test_custom_action_claims_success_without_executor(self):
        await self._non_effect(ActionType.CUSTOM, {'executed': True})

    async def test_message_claims_success_without_sender(self):
        await self._non_effect(ActionType.SEND_MESSAGE, {'executed': True})

    async def test_code_action_claims_success_without_executor(self):
        await self._non_effect(ActionType.EXECUTE_CODE, {'executed': True})

    async def test_reminder_records_only_its_documented_local_log(self):
        await self._non_effect(ActionType.REMIND,
                               {'reminded': True, 'message': 'synthetic reminder'},
                               {'message': 'synthetic reminder'})
        self.assertTrue(any('REMINDER: synthetic reminder' in call.args[0]
                            for call in self.log.info.call_args_list))

    def _response(self, flags):
        results = [_producer.PostResult(success=success, platform=platform,
                                       message='synthetic result', timestamp=_FixedClock.now())
                   for platform, success in zip(
                       [_producer.Platform.LINKEDIN, _producer.Platform.X_TWITTER], flags)]
        return _producer.PostResponse(request_id='fixture-response', results=results,
                                      success_count=sum(flags), failure_count=len(flags)-sum(flags),
                                      timestamp=_FixedClock.now())

    async def _stream_result(self, response, failure=None):
        platforms = [_producer.Platform.LINKEDIN, _producer.Platform.X_TWITTER]
        action = self._action(ActionType.POST_SOCIAL, {
            'platforms': [p.value for p in platforms], 'content': 'synthetic content',
            'metadata': {'stream_url': 'https://example.invalid/stream', 'stream_title': 'fixture'}})
        self.post.side_effect = failure
        self.post.return_value = response
        results = await self.scheduler.execute_pending_actions()
        self.post.assert_awaited_once_with(stream_title='fixture',
                                          stream_url='https://example.invalid/stream',
                                          platforms=platforms)
        self.assertEqual(self.post.call_count, 1)
        self.scheduler.save_schedule.assert_called_once_with()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0][0], action.id)
        self.assertIs(self.scheduler.scheduled_actions[action.id], action)
        if failure:
            self.assertEqual(action.status, 'failed')
            self.assertEqual(action.error, str(failure))
            self.assertIsNone(action.result)
            self.assertEqual(results[0][1], {'error': str(failure)})
            self.log.error.assert_called_once()
            self.assertFalse(any('Successfully executed' in call.args[0]
                                 for call in self.log.info.call_args_list))
        else:
            self.assertEqual(action.status, 'executed')
            self.assertIs(action.result, response)
            self.assertIs(results[0][1], response)
            self.assertIsNone(action.error)
            self.log.info.assert_any_call('[0102 EXECUTOR] [OK] Successfully executed ' + action.id)
            self.log.error.assert_not_called()

    async def test_stream_all_success_preserves_producer_response(self):
        await self._stream_result(self._response([True, True]))

    async def test_stream_all_failure_still_claims_executed(self):
        await self._stream_result(self._response([False, False]))

    async def test_stream_partial_result_still_claims_executed(self):
        await self._stream_result(self._response([True, False]))

    async def test_stream_empty_result_still_claims_executed(self):
        await self._stream_result(self._response([]))

    async def test_stream_none_result_still_claims_executed(self):
        await self._stream_result(None)

    async def test_stream_exception_marks_failure(self):
        await self._stream_result(None, RuntimeError('synthetic failure'))

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
