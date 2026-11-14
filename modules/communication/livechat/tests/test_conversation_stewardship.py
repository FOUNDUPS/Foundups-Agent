"""Offline controls for quiet conversation selection and identity-scoped history."""
import ast
import asyncio
from datetime import datetime, timezone
import importlib.util
import json
import logging
import os
from pathlib import Path
import re
import sqlite3
import sys
import time
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

SRC = Path(__file__).resolve().parents[1] / 'src'


def methods(filename, classname, names):
    path = SRC / filename
    tree = ast.parse(path.read_text(encoding='utf-8'))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == classname)
    cls.bases = []
    cls.body = [n for n in cls.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name in names]
    helpers = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == '_env_truthy']
    ns = {'logger': logging.getLogger(__name__), 'os': os, 're': re, 'time': time,
          '_sanitize_username': lambda value: value}
    module = ast.Module(body=[ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')], level=0), *helpers, cls], type_ignores=[])
    exec(compile(ast.fix_missing_locations(module), str(path), 'exec'), ns)
    return ns[classname]


@pytest.fixture
def processor(monkeypatch):
    cls = methods('message_processor.py', 'MessageProcessor', {'generate_response', '_conversation_response'})
    obj = cls()
    obj.persona_config = {'display_name': 'FoundupsBot'}
    obj.memory_manager = SimpleNamespace(current_session='current', get_conversation_context=Mock(return_value={
        'session_id': 'current', 'participant_id': 'native-id', 'recent_messages': [], 'participant_messages': []}))
    obj.channel_id = 'receiving-channel'
    obj.stream_title = 'Current stream'
    obj.intelligent_reply = SimpleNamespace(channel_id=obj.channel_id, stream_title=obj.stream_title)
    obj._await_intelligent_reply = AsyncMock(return_value='reviewed fixture')
    obj.intelligent_throttle = None
    obj._check_pqn_command = Mock(return_value=False)
    obj.self_improvement = SimpleNamespace(observe_command=Mock())
    obj.agentic_engine = SimpleNamespace(generate_agentic_response=Mock(side_effect=AssertionError('legacy fallback')))
    queue = ModuleType('modules.communication.livechat.src.operator_command_queue')
    queue.load_active_theme = Mock(return_value=None)
    monkeypatch.setitem(sys.modules, queue.__name__, queue)
    monkeypatch.setenv('YT_COMMENT_REPLY_ENABLED', 'true')
    monkeypatch.setenv('YT_LIVECHAT_ENGAGE_MODS_ONLY', 'true')
    return obj


def message(text, role='USER', **flags):
    return dict(text=text, author_id='native-id', author_name='Stakeholder',
                published_at=datetime.now(timezone.utc).isoformat(),
                is_moderator=role == 'MOD', is_owner=role == 'OWNER', **flags)


@pytest.mark.parametrize('role', ['USER', 'MOD', 'OWNER'])
def test_question_eligibility_has_no_badge_preference(processor, role):
    data = message('What is the oversight site for?', role)
    assert asyncio.run(processor.generate_response(data)) == 'reviewed fixture'
    assert processor._await_intelligent_reply.await_args.kwargs['role'] == role
    assert processor._await_intelligent_reply.await_args.kwargs['conversation_context']['participant_id'] == 'native-id'


@pytest.mark.parametrize('text', ['hello', '✊✋🖐', 'MAGA', 'great song', '@Somebody hello'])
def test_idle_or_keyword_messages_remain_observation_only(processor, text):
    assert asyncio.run(processor.generate_response(message(text))) is None
    processor._await_intelligent_reply.assert_not_called()


@pytest.mark.parametrize('text', ['The oversight link returns a DNS error', '@FoundupsBot explain this', '✊✋🖐 このサイトについて説明して'])
def test_useful_candidates_reach_shared_reviewed_path(processor, text):
    assert asyncio.run(processor.generate_response(message(text))) == 'reviewed fixture'
    assert processor._await_intelligent_reply.await_args.kwargs['message'] == text


@pytest.mark.parametrize('flags', [{'is_rate_limited': True}, {'emoji_rate_denied': True}, {'skip': True}, {'published_at': 'bad'}, {'published_at': '2000-01-01T00:00:00Z'}])
def test_unusable_or_stale_message_never_calls_model(processor, flags):
    data = message('What is this site?')
    data.update(flags)
    assert asyncio.run(processor.generate_response(data)) is None
    processor._await_intelligent_reply.assert_not_called()


def test_failed_generation_consumes_attempt_budget_without_fallback(processor):
    processor._await_intelligent_reply.return_value = None
    assert asyncio.run(processor.generate_response(message('What is this site?'))) is None
    assert asyncio.run(processor.generate_response(message('What about this?'))) is None
    assert processor._await_intelligent_reply.await_count == 1
    processor.agentic_engine.generate_agentic_response.assert_not_called()


def test_missing_history_is_quiet(processor):
    processor.memory_manager.get_conversation_context.return_value = None
    assert asyncio.run(processor.generate_response(message('What is this site?'))) is None
    processor._await_intelligent_reply.assert_not_called()


@pytest.mark.parametrize('change', ['channel', 'title', 'session', 'generator'])
def test_changed_receiving_context_discards_reply(processor, change):
    async def changed(**kwargs):
        if change == 'channel':
            processor.channel_id = 'other-channel'
        elif change == 'title':
            processor.stream_title = 'other-title'
        elif change == 'session':
            processor.memory_manager.current_session = 'other-session'
        else:
            processor.intelligent_reply = object()
        return 'stale result'
    processor._await_intelligent_reply.side_effect = changed
    assert asyncio.run(processor.generate_response(message('What is this site?'))) is None


@pytest.mark.parametrize('kind', ['m2j', 'shorts'])
def test_existing_command_handler_retains_role_and_owns_result(processor, kind):
    handler = Mock(return_value='existing command result')
    setattr(processor, '_handle_' + kind + '_command', handler)
    data = message('!m2j' if kind == 'm2j' else '!createshort how does it work?', 'OWNER', **{'has_' + kind + '_command': True})
    assert asyncio.run(processor.generate_response(data)) == 'existing command result'
    handler.assert_called_once_with(data['text'], 'Stakeholder', 'native-id', 'OWNER')
    processor._await_intelligent_reply.assert_not_called()


def test_budget_limits_generation_across_participants(processor, monkeypatch):
    clock = [1000.0]
    monkeypatch.setattr(time, 'monotonic', lambda: clock[0])
    for index in range(3):
        data = message('What is this site?')
        data['author_id'] = str(index)
        processor.memory_manager.get_conversation_context.return_value['participant_id'] = str(index)
        assert asyncio.run(processor.generate_response(data)) == 'reviewed fixture'
        clock[0] += 121
    data['author_id'] = 'fourth'
    assert asyncio.run(processor.generate_response(data)) is None
    assert processor._await_intelligent_reply.await_count == 3


@pytest.mark.parametrize('decision', [False, None, 'true', 1, True])
def test_actual_assessment_requires_explicit_useful_reply_decision(decision):
    source = SRC.parents[1] / 'video_comments' / 'src'
    spec = importlib.util.spec_from_file_location('stewardship_reply_context', source / 'reply_context.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    path = source / 'intelligent_reply_generator.py'
    tree = ast.parse(path.read_text(encoding='utf-8'))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'IntelligentReplyGenerator')
    method = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == '_assess_comment')
    ns = {'parse_comment_assessment': module.parse_comment_assessment, 'logger': logging.getLogger(__name__)}
    exec(compile(ast.Module(body=[method], type_ignores=[]), str(path), 'exec'), ns)
    assessment = dict(intent='question', meaning='Asks about site', question='What is this site?',
                      stance='unclear', uncertainty='', evidence_quote='What is this site?',
                      strategy='answer', theme_relevant=False)
    if decision is not None:
        assessment['should_reply'] = decision
    obj = SimpleNamespace(_language_judgment=Mock(return_value=(json.dumps(assessment), 'fixture')))
    data = {'text': 'What is this site?', 'conversation': {'recent_messages': []}}
    result = ns['_assess_comment'](obj, data)
    assert (result is not None) is (decision is True)
    # Existing stored-comment contract does not require the livechat decision.
    assert ns['_assess_comment'](obj, {'text': data['text']}) is not None


def test_context_is_native_identity_and_session_scoped(tmp_path, monkeypatch):
    telemetry = ModuleType('modules.communication.livechat.src.chat_telemetry_store')
    telemetry.ChatTelemetryStore = lambda: SimpleNamespace(record_message=lambda **kw: None)
    monkeypatch.setitem(sys.modules, telemetry.__name__, telemetry)
    spec = importlib.util.spec_from_file_location('stewardship_memory', SRC / 'chat_memory_manager.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    manager = module.ChatMemoryManager(str(tmp_path))
    manager.current_session = 'old'
    manager.store_message('SameName', 'old session', author_id='native-id')
    manager.current_session = 'current'
    manager.store_message('SameName', 'other identity', author_id='other-id')
    manager.store_message('Renamed', 'current identity', author_id='native-id')
    context = manager.get_conversation_context('native-id')
    assert [row['text'] for row in context['participant_messages']] == ['current identity']
    assert [row['text'] for row in context['recent_messages']] == ['other identity', 'current identity']
    assert manager.get_conversation_context('') is None
    with sqlite3.connect(manager.db_path) as db:
        assert db.execute('SELECT COUNT(*) FROM chat_messages').fetchone()[0] == 3


@pytest.mark.parametrize('middle, expected', [
    ('What is this site?', ['first', 'second', 'third']),
    ('!unknown what is this site?', ['first', 'second', 'third']),
    ('/help', ['second', 'first', 'third']),
])
def test_batch_captures_all_before_generation_and_preserves_arrival_order(middle, expected):
    cls = methods('livechat_core.py', 'LiveChatCore', {'process_message_batch'})
    obj = cls()
    obj.processed_message_ids = set()
    obj.message_processor = methods('message_processor.py', 'MessageProcessor', {'_check_whack_command'})()
    captured, processed = [], []
    obj._log_to_user_file = lambda msg: captured.append(msg['id'])
    async def process(msg):
        assert captured == ['first', 'second', 'third']
        processed.append(msg['id'])
    obj.process_message = process
    batch = [{'id': ident, 'snippet': {'displayMessage': 'What is the site?'},
              'authorDetails': {'isChatOwner': role == 'OWNER', 'isChatModerator': role == 'MOD'}}
             for ident, role in [('first', 'USER'), ('second', 'OWNER'), ('third', 'MOD')]]
    batch[1]['snippet']['displayMessage'] = middle
    asyncio.run(obj.process_message_batch(batch))
    assert processed == expected


@pytest.mark.parametrize('changed', [False, True])
def test_sender_rechecks_destination_after_wait(changed, monkeypatch):
    cls = methods('chat_sender.py', 'ChatSender', {'__init__', 'send_message'})
    ns = cls.send_message.__globals__
    ns.update(asyncio=asyncio, random=SimpleNamespace(uniform=lambda *_: 0),
              stop_active=lambda *_: False, _convert_unicode_tags_to_emoji=lambda value: str(value))
    insert = Mock(return_value=SimpleNamespace(execute=lambda: {'id': 'fixture-receipt'}))
    sender = cls(SimpleNamespace(liveChatMessages=lambda: SimpleNamespace(insert=insert)), 'original-chat')
    sender.bot_channel_id = 'bot'
    sender._apply_global_throttling = AsyncMock()
    async def wait(_):
        if changed:
            sender.live_chat_id = 'new-chat'
    monkeypatch.setattr(asyncio, 'sleep', wait)
    queue = ModuleType('modules.communication.livechat.src.operator_command_queue')
    queue.load_active_theme = lambda *_: None
    monkeypatch.setitem(sys.modules, queue.__name__, queue)
    monkeypatch.setenv('YT_LIVECHAT_DRY_RUN', 'false')
    tree = ast.parse((SRC / 'intelligent_livechat_reply.py').read_text(encoding='utf-8'))
    node = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'ReviewedLivechatReply')
    namespace = {}
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(SRC / 'intelligent_livechat_reply.py'), 'exec'), namespace)
    reply = namespace['ReviewedLivechatReply']('A useful answer.', None)
    reply.destination_snapshot = ('original-chat', 'bot')
    assert asyncio.run(sender.send_message(reply, response_type='conversation')) is (not changed)
    assert insert.call_count == (0 if changed else 1)
    if not changed:
        assert insert.call_args.kwargs['body']['snippet']['liveChatId'] == 'original-chat'
